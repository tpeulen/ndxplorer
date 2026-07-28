"""Helper functions for histogram computation and caching.

This module provides synchronous histogram computation functions that work
with both the background worker and immediate computation paths.
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple, Any
import numpy as np

from ..logging_config import logging


def compute_histograms_sync(
    data_source,
    histogram_params: Dict[str, Any],
    weights: Optional[np.ndarray] = None
) -> Dict[str, Tuple]:
    """
    Compute histograms synchronously (for immediate computation or background worker).
    
    Args:
        data_source: Data source containing values array
        histogram_params: Dictionary containing histogram computation parameters
        weights: Optional weight array
        
    Returns:
        Dictionary containing computed histogram data
    """
    import time
    start_time = time.time()
    
    try:
        # Extract data arrays
        x_data = data_source.values[histogram_params['x_idx'], :]
        y_data = data_source.values[histogram_params['y_idx'], :]
        z_data = data_source.values[histogram_params['z_idx'], :] if histogram_params.get('z_idx') is not None else None

        valid_indices = histogram_params.get('valid_indices')
        if valid_indices is not None:
            x_data = x_data[valid_indices]
            y_data = y_data[valid_indices]
            if z_data is not None:
                z_data = z_data[valid_indices]
            if weights is not None:
                weights = weights[valid_indices]

        # Every histogram here describes the same population: the rows that have
        # a value on both plotted axes. Without this the marginals count bursts
        # the 2D map cannot show.
        from .histogram_helpers import apply_joint_axis_mask

        x_data, y_data, z_data, weights = apply_joint_axis_mask(
            x_data, y_data, z_data, weights
        )

        result = {}

        # Prefer the precomputed bin EDGES over a uniform count+range. get_x_bins/
        # get_y_bins build these via np.logspace for a log-scaled axis, so binning
        # on them is what makes a log plot actually log-resolved. A uniform Regular
        # axis silently ignored the scale, binned linearly and crushed the data
        # into the lowest bins (and the log marginal / image then disagreed).
        def _edges(key):
            arr = histogram_params.get(key)
            if arr is None:
                return None
            arr = np.asarray(arr, dtype=float)
            return arr if arr.size > 1 else None
        x_edges_1d = _edges('x_bins_1d_arr')
        y_edges_1d = _edges('y_bins_1d_arr')
        z_edges_1d = _edges('z_bins_1d_arr')
        x_edges_2d = _edges('x_bins_2d_arr')
        y_edges_2d = _edges('y_bins_2d_arr')

        # Check performance configuration for histogram backend
        from .performance_config import get_performance_config
        config = get_performance_config()
        
        if config.use_boost_histogram:
            # Use boost-histogram for maximum performance
            try:
                import boost_histogram as bh

                # Resolve the fill thread count once. boost's multi-threaded fill
                # is ~3x faster on the multi-million-point arrays NDXplorer shows;
                # only worth it above a point threshold (thread setup dominates for
                # small data). histogram_threads <= 0 means "use all cores".
                cfg_threads = getattr(config, "histogram_threads", -1)
                if x_data.size >= 200_000:
                    import os
                    threads = cfg_threads if cfg_threads and cfg_threads > 0 else (os.cpu_count() or 1)
                else:
                    threads = 1

                def _fill(hist, *cols):
                    if weights is not None:
                        hist.fill(*cols, weight=weights, threads=threads)
                    else:
                        hist.fill(*cols, threads=threads)
                    return hist

                from .fast_histogram import _uniform_edges_range

                def _axis(edges, count, rng):
                    # A Regular axis bins with O(1) arithmetic; a Variable axis
                    # binary-searches every point (~6x slower at millions of
                    # points). So use Variable ONLY for genuinely non-uniform
                    # (log-spaced) edges; uniform edges — the common linear case —
                    # collapse back to a fast Regular axis.
                    if edges is not None:
                        uniform = _uniform_edges_range(edges)
                        if uniform is not None:
                            lo, hi, n_bins = uniform
                            return bh.axis.Regular(n_bins, lo, hi)
                        return bh.axis.Variable(edges)
                    return bh.axis.Regular(count, *rng)

                # Compute 1D histograms using boost-histogram
                x_hist = _fill(bh.Histogram(_axis(x_edges_1d, histogram_params['x_bins'], histogram_params['x_range'])), x_data)
                result['x'] = (x_hist.axes[0].edges, x_hist.values())

                y_hist = _fill(bh.Histogram(_axis(y_edges_1d, histogram_params['y_bins'], histogram_params['y_range'])), y_data)
                result['y'] = (y_hist.axes[0].edges, y_hist.values())

                # Compute Z histogram only when a Z axis is active (lazy)
                if z_data is not None:
                    z_hist = _fill(bh.Histogram(_axis(z_edges_1d, histogram_params['z_bins'], histogram_params['z_range'])), z_data)
                    result['z'] = (z_hist.axes[0].edges, z_hist.values())

                # Compute 2D histogram using boost-histogram
                h2d = _fill(
                    bh.Histogram(
                        _axis(x_edges_2d, histogram_params['x_bins_2d'], histogram_params['x_range']),
                        _axis(y_edges_2d, histogram_params['y_bins_2d'], histogram_params['y_range']),
                    ),
                    x_data, y_data,
                )
                # boost returns values shaped (nx, ny); downstream Histogram2D
                # expects (ny, nx) — transpose to match the numpy/fast branches.
                result['2d'] = (h2d.values().T, h2d.axes[0].edges, h2d.axes[1].edges)

            except ImportError:
                logging.warning("boost-histogram not available, falling back to numpy")
                config.use_boost_histogram = False
        
        if not config.use_boost_histogram:
            # Uniform-bin fast path (bincount) when enabled, else NumPy. The fast
            # helpers fall back to NumPy internally for any non-uniform bins.
            if getattr(config, "use_fast_histogram", True):
                from .fast_histogram import fast_histogram_1d, fast_histogram_2d
                hist1d = fast_histogram_1d
                hist2d = fast_histogram_2d
                logging.debug("Using fast (bincount) histogram computation")
            else:
                def hist1d(data, bins, weights=None, density=False, data_range=None):
                    counts, edges = np.histogram(data, bins=bins, range=data_range, weights=weights)
                    return edges, counts

                def hist2d(x, y, bins, weights=None, x_range=None, y_range=None):
                    H, xe, ye = np.histogram2d(x, y, bins=bins, range=[x_range, y_range], weights=weights)
                    return H, xe, ye
                logging.debug("Using numpy histogram computation")

            # Compute 1D histograms
            x_range = histogram_params['x_range']
            y_range = histogram_params['y_range']

            # Handle zero range data for 1D histograms
            if x_range[0] == x_range[1]:
                x_range = (x_range[0] - 0.5, x_range[1] + 0.5)

            if y_range[0] == y_range[1]:
                y_range = (y_range[0] - 0.5, y_range[1] + 0.5)

            # Explicit edges (log-spaced when the axis is log) take precedence over
            # a uniform bin count; the fast/NumPy helpers accept an edge array as
            # ``bins`` and ignore the range in that case.
            x_bins_arg = x_edges_1d if x_edges_1d is not None else histogram_params['x_bins']
            y_bins_arg = y_edges_1d if y_edges_1d is not None else histogram_params['y_bins']

            x_edges, x_hist = hist1d(x_data, x_bins_arg, weights=weights, data_range=x_range)
            result['x'] = (x_edges, x_hist)  # Store as (edges, counts)

            y_edges, y_hist = hist1d(y_data, y_bins_arg, weights=weights, data_range=y_range)
            result['y'] = (y_edges, y_hist)  # Store as (edges, counts)

            # Compute Z histogram only when a Z axis is active (lazy: skip otherwise)
            if z_data is not None:
                z_range = histogram_params['z_range']
                if z_range[0] == z_range[1]:
                    z_range = (z_range[0] - 0.5, z_range[1] + 0.5)

                z_bins_arg = z_edges_1d if z_edges_1d is not None else histogram_params['z_bins']
                z_edges, z_hist = hist1d(z_data, z_bins_arg, weights=weights, data_range=z_range)
                result['z'] = (z_edges, z_hist)  # Store as (edges, counts)

            # Compute 2D histogram (reuses the same expanded x/y ranges)
            H, x_edges, y_edges = hist2d(
                x_data, y_data,
                bins=[
                    x_edges_2d if x_edges_2d is not None else histogram_params['x_bins_2d'],
                    y_edges_2d if y_edges_2d is not None else histogram_params['y_bins_2d'],
                ],
                weights=weights,
                x_range=x_range,
                y_range=y_range,
            )
            # CRITICAL: histogram2d returns H with shape (nx, ny) but Histogram2D expects (ny, nx)
            result['2d'] = (H.T, x_edges, y_edges)
        
        # Add metadata
        result['_count'] = len(x_data)
        result['_computation_time'] = time.time() - start_time
        params_copy = histogram_params.copy()
        # Do not persist large index arrays inside cache metadata
        params_copy.pop('valid_indices', None)
        result['_params'] = params_copy
        if weights is not None:
            result['_has_weights'] = True
        
        logging.debug(f"Synchronous histogram computation completed in {result['_computation_time']:.3f}s")
        return result
        
    except Exception as e:
        logging.error(f"Histogram computation failed: {e}")
        raise


def extract_histogram_params_from_plot_control(plot_control) -> Dict[str, Any]:
    """
    Extract histogram computation parameters from plot control widget.
    
    Args:
        plot_control: SurfacePlotWidget instance
        
    Returns:
        Dictionary of histogram parameters
    """
    try:
        params = {
            'x_idx': plot_control.p1[0],
            'y_idx': plot_control.p2[0],
            'z_idx': plot_control.p3[0] if plot_control.p3[0] >= 0 else None,
            'x_bins': plot_control.n_xhist_1d,
            'y_bins': plot_control.n_yhist_1d,
            'z_bins': plot_control.n_zhist_1d,
            'x_bins_2d': plot_control.n_xhist_2d,
            'y_bins_2d': plot_control.n_yhist_2d,
            'x_range': (plot_control.xmin, plot_control.xmax),
            'y_range': (plot_control.ymin, plot_control.ymax),
            'z_range': (plot_control.zmin, plot_control.zmax),
        }
        
        # Add weight information if enabled
        if plot_control.weight_enabled:
            params['weight_parameter'] = plot_control.weight_parameter
            params['has_weights'] = True
        
        return params
    except Exception as e:
        logging.error(f"Failed to extract histogram params: {e}")
        return {}


def should_recompute_histograms(plot_control, current_params: Dict[str, Any]) -> bool:
    """
    Check if histograms need to be recomputed based on parameter changes.
    
    Args:
        plot_control: SurfacePlotWidget instance
        current_params: Current histogram parameters
        
    Returns:
        True if recomputation is needed
    """
    try:
        # Check if we have cached data with matching parameters
        if hasattr(plot_control.parent, '_histogram') and plot_control.parent._histogram:
            cached_params = plot_control.parent._histogram.get('_params', {})
            
            # Compare key parameters
            key_params = [
                'x_idx', 'y_idx', 'z_idx',
                'x_bins', 'y_bins', 'z_bins',
                'x_bins_2d', 'y_bins_2d',
                'x_range', 'y_range', 'z_range',
                # Filtering/selections (may be injected by caller)
                'valid_idx_hash', 'valid_idx_count', 'selection_hash',
            ]
            
            for param in key_params:
                if cached_params.get(param) != current_params.get(param):
                    logging.debug(f"Parameter {param} changed: {cached_params.get(param)} -> {current_params.get(param)}")
                    return True
            
            # Check weight changes
            if plot_control.weight_enabled != cached_params.get('has_weights', False):
                logging.debug("Weight setting changed")
                return True
            
            if (plot_control.weight_enabled and 
                plot_control.weight_parameter != cached_params.get('weight_parameter')):
                logging.debug("Weight parameter changed")
                return True
            
            return False
        
        return True  # No cached data, need to compute
        
    except Exception as e:
        logging.error(f"Error checking recompute condition: {e}")
        return True  # Safer to recompute


def resolve_weights(plot_control, data_source) -> Optional[np.ndarray]:
    """
    Resolve weight array based on plot control settings.
    
    Args:
        plot_control: SurfacePlotWidget instance
        data_source: Data source containing parameter values
        
    Returns:
        Weight array or None if weighting is disabled
    """
    try:
        if not plot_control.weight_enabled:
            return None
        
        weight_param_name = plot_control.weight_parameter
        if not weight_param_name or weight_param_name == "None":
            return None
        
        # Find weight parameter index
        param_names = data_source.parameter_names
        if weight_param_name not in param_names:
            logging.warning(f"Weight parameter '{weight_param_name}' not found")
            return None
        
        weight_idx = param_names.index(weight_param_name)
        weights = data_source.values[weight_idx, :]
        
        # Handle negative or zero weights
        weights = np.where(weights <= 0, 0, weights)
        
        logging.debug(f"Using weights from parameter '{weight_param_name}'")
        return weights
        
    except Exception as e:
        logging.error(f"Failed to resolve weights: {e}")
        return None
