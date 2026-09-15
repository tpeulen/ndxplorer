"""Histogram plotting functionality extracted from plot_main.py.

This module provides 2D/3D histogram plotting capabilities for NDXplorer,
including weighted histograms, normalization, and caching optimizations.
"""

from __future__ import annotations

from typing import Optional, Tuple, Union
import numpy as np

from ..logging_config import logging
from ..core.histograms import Histogram1D, Histogram2D
from ..utils.histogram_helpers import is_data_ready

if False:  # pragma: no cover - type checking hints without runtime import
    from ..core.plot_main import NDXplorer


def _as_1d_arrays(hist_data) -> Optional[Tuple[np.ndarray, np.ndarray]]:
    """Normalise a stored 1D histogram to ``(edges, counts)``.

    ``ndxplorer._histogram[dim]`` normally holds a :class:`Histogram1D`, but an
    ``(edges, counts)`` tuple -- the shape ``compute_histograms`` returns -- is
    accepted too. Returns ``None`` for anything unrecognised.
    """
    if isinstance(hist_data, Histogram1D):
        return hist_data.edges, hist_data.counts
    if isinstance(hist_data, (tuple, list)) and len(hist_data) == 2:
        return np.asarray(hist_data[0]), np.asarray(hist_data[1])
    return None


def _as_2d_arrays(hist_data) -> Optional[Tuple[np.ndarray, np.ndarray, np.ndarray]]:
    """Normalise a stored 2D histogram to ``(H, x_edges, y_edges)``.

    Accepts either a :class:`Histogram2D` or an ``(H, x_edges, y_edges)``
    tuple -- the shape ``compute_histograms`` returns, already transposed to
    ``H`` shaped ``(n_y, n_x)``. Returns ``None`` otherwise.
    """
    if isinstance(hist_data, Histogram2D):
        return hist_data.H, hist_data.x_edges, hist_data.y_edges
    if isinstance(hist_data, (tuple, list)) and len(hist_data) == 3:
        return np.asarray(hist_data[0]), np.asarray(hist_data[1]), np.asarray(hist_data[2])
    return None


def plot_histogram(
    ndxplorer: "NDXplorer",
    dimension: str = "2d",
    weights: Optional[np.ndarray] = None,
    normed: bool = False,
    **kwargs
) -> Tuple[np.ndarray, Union[np.ndarray, Tuple[np.ndarray, np.ndarray]]]:
    """
    Plot histogram data for specified dimension.
    
    Args:
        ndxplorer: NDXplorer instance
        dimension: One of 'x', 'y', 'z', '2d'
        weights: Optional weight array
        normed: Whether to normalize the histogram
        **kwargs: Additional plotting options
        
    Returns:
        For ``dimension='2d'``: ``(H, (x_edges, y_edges))`` with ``H`` shaped
        ``(n_y, n_x)``. For a marginal (``'x'``/``'y'``/``'z'``):
        ``(edges, counts)`` — edges **first**, matching how ``Histogram1D``
        unpacks, not the 2-D order.

    Raises:
        ValueError: If dimension is not supported
    """
    if not is_data_ready(ndxplorer):
        logging.warning("Data not ready for histogram plotting")
        return np.array([0, 1]), np.array([0])

    if dimension not in ndxplorer._histogram:
        logging.warning(f"No histogram data available for dimension '{dimension}'")
        return np.array([0, 1]), np.array([0])
    
    hist_data = ndxplorer._histogram[dimension]

    if dimension == "2d":
        arrs = _as_2d_arrays(hist_data)
        if arrs is not None:
            H, x_edges, y_edges = arrs
            return H, (x_edges, y_edges)
        logging.error("Invalid 2D histogram data format")
        return np.array([[0]]), (np.array([0, 1]), np.array([0, 1]))
    else:
        arrs = _as_1d_arrays(hist_data)
        if arrs is not None:
            edges, counts = arrs
            return edges, counts
        logging.error(f"Invalid {dimension} histogram data format")
        return np.array([0, 1]), np.array([0])


def compute_2d_histogram(
    ndxplorer: "NDXplorer",
    x_data: np.ndarray,
    y_data: np.ndarray,
    x_bins: Union[int, np.ndarray],
    y_bins: Union[int, np.ndarray],
    weights: Optional[np.ndarray] = None,
    density: bool = False
) -> Histogram2D:
    """A 2-D histogram of the arrays given.

    Straight to the engine. This used to go through a caching manager, which
    hashed the parameters, looked them up, and on a miss did exactly this --
    and the computation it was avoiding is now a few milliseconds, less than
    the bookkeeping.

    :param ndxplorer: unused; kept because callers pass it positionally
    """
    from ..utils.fast_histogram import fast_histogram_2d

    try:
        H, x_edges, y_edges = fast_histogram_2d(
            x_data, y_data, bins=[x_bins, y_bins], weights=weights,
            density=density)
        # (n_x, n_y) out, (n_y, n_x) in: Histogram2D holds the orientation the
        # image item draws.
        return Histogram2D(H=np.ascontiguousarray(H.T),
                           x_edges=x_edges, y_edges=y_edges)
    except Exception as e:
        logging.error(f"Failed to compute 2D histogram: {e}")
        return Histogram2D(
            H=np.array([[0, 0], [0, 0]]),
            x_edges=np.array([0, 1]),
            y_edges=np.array([0, 1])
        )


def compute_1d_histogram(
    ndxplorer: "NDXplorer",
    data: np.ndarray,
    bins: Union[int, np.ndarray],
    weights: Optional[np.ndarray] = None,
    normed: bool = False
) -> Histogram1D:
    """A 1-D histogram of the array given. \see compute_2d_histogram"""
    from ..utils.fast_histogram import fast_histogram_1d

    try:
        edges, counts = fast_histogram_1d(
            data, bins, weights=weights, density=normed)
        return Histogram1D(edges=edges, counts=counts)
    except Exception as e:
        logging.error(f"Failed to compute 1D histogram: {e}")
        return Histogram1D(
            edges=np.array([0.0, 1.0]),
            counts=np.array([0.0])
        )


def update_histogram_display(ndxplorer: "NDXplorer") -> None:
    """Recompute the histograms and put them on screen.

    The parameter comparison that used to stand here (extract the settings,
    ask ``should_recompute``, return early) guarded a cache that was removed:
    it could only ever skip work that had already been done again anyway, and
    it read ``len(ndxplorer.x_values)`` to fill the count box -- which
    re-derives the whole gating state, so the "cheap" path cost more than the
    fill it was avoiding. ``update_histograms`` sets the count from what it
    actually binned.
    """
    if not is_data_ready(ndxplorer):
        logging.debug("Skipping histogram update: data not ready")
        return

    from ..plotting.plot_update_helpers import update_histograms
    update_histograms(ndxplorer)


def get_histogram_statistics(
    ndxplorer: "NDXplorer",
    dimension: str = "2d"
) -> dict:
    """
    Compute basic statistics for histogram data.
    
    Args:
        ndxplorer: NDXplorer instance
        dimension: Histogram dimension ('x', 'y', 'z', '2d')
        
    Returns:
        Dictionary containing statistics (count, mean, std, min, max)
    """
    if dimension not in ndxplorer._histogram:
        return {}
    
    hist_data = ndxplorer._histogram[dimension]

    if dimension == "2d":
        arrs = _as_2d_arrays(hist_data)
        if arrs is not None:
            H = np.asarray(arrs[0])
            return {
                "count": np.sum(H),
                "mean": np.mean(H),
                "std": np.std(H),
                "min": np.min(H),
                "max": np.max(H),
                "shape": H.shape,
            }
    else:
        arrs = _as_1d_arrays(hist_data)
        if arrs is not None:
            counts = np.asarray(arrs[1])
            return {
                "count": np.sum(counts),
                "mean": np.mean(counts),
                "std": np.std(counts),
                "min": np.min(counts),
                "max": np.max(counts),
                "bins": len(counts),
            }

    return {}
