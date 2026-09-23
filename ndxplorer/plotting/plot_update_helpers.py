"""Helper routines for updating histograms/plots/spinboxes in NDXplorer."""

from __future__ import annotations

import numpy as np

from ..logging_config import logging

from ..utils.histogram_helpers import z_axis_available

from ..utils.lazy_imports import get_hdbscan
from ..utils.performance import compute_percentile_range_optimized

def _as_edges_counts(hist):
    """Return ``(edges, counts)`` for either 1D histogram representation.

    ``_histogram[dim]`` normally holds a :class:`~..core.histograms.Histogram1D`,
    but a plain ``(edges, counts)`` tuple is still accepted: two paths used to
    write these and consumers that understood only one silently blanked the
    marginals whenever the other had produced them.

    Parameters
    ----------
    hist : Histogram1D or tuple or None
        The stored histogram, or ``None`` when nothing is computed yet.

    Returns
    -------
    tuple or None
        ``(edges, counts)``, or ``None`` when unusable.
    """
    if hist is None:
        return None
    edges = getattr(hist, "edges", None)
    counts = getattr(hist, "counts", None)
    if edges is None and isinstance(hist, tuple) and len(hist) == 2:
        edges, counts = hist
    if edges is None or counts is None:
        return None
    if len(edges) >= 2 and len(counts) >= 1:
        return edges, counts
    return None


def update_histograms(ndxplorer) -> None:
    """Compute the histograms and put them on screen.

    One way in. There were three -- this function, a near-identical
    ``_update_histograms_immediate``, and a QThread worker reached through
    ``compute_histograms_background`` -- so which of them ran decided what a
    redraw showed. The worker only took over above six million points, and a
    full redraw is about twenty milliseconds, so it was machinery guarding a
    case that no longer exists.
    """
    from ..core.histograms import Histogram1D, Histogram2D
    from ..utils.histogram_computation import compute_histograms
    from ..utils.histogram_helpers import histogram_axes, is_data_ready, keep_mask

    if getattr(ndxplorer.plot_control, '_loading_data', False) or \
            getattr(ndxplorer, '_loading_data', False):
        logging.debug("Skipping update_histograms: data is still loading")
        return

    if not is_data_ready(ndxplorer):
        logging.debug("Skipping update_histograms: data/axes not ready")
        return

    try:
        # No bin edges are built here. The axis is a count, a range and a
        # scale -- which is what the plot controls hold -- and handing those
        # over lets the fill bin with a multiply instead of a search through an
        # array of boundaries.
        result = compute_histograms(ndxplorer.data_source,
                                    histogram_axes(ndxplorer),
                                    keep=keep_mask(ndxplorer))
        count = int(result.get("_count", 0))
        ndxplorer.lineEditCountCurrent.setText(str(count))
        # The playback readout says which slice is on screen; how many points
        # survived it is the other half of that sentence, and it is only known
        # here, after the fill.
        model = getattr(ndxplorer.plot_control, "playback_model", None)
        if model is not None:
            model.set_count_text(f"{count:,} points")
            form = getattr(ndxplorer.plot_control, "playback_form", None)
            if form is not None:
                form.refresh_plots()

        ndxplorer._histogram["x"] = Histogram1D(*result["x"])
        ndxplorer._histogram["y"] = Histogram1D(*result["y"])
        if "z" in result:
            ndxplorer._histogram["z"] = Histogram1D(*result["z"])
        else:
            ndxplorer._histogram.pop("z", None)
        H, x_edges, y_edges = result["2d"]
        ndxplorer._histogram["2d"] = Histogram2D(H=H, x_edges=x_edges, y_edges=y_edges)

        _update_marginal_plots_from_cache(ndxplorer)
        if hasattr(ndxplorer, 'update_2d_plot'):
            ndxplorer.update_2d_plot()
        if hasattr(ndxplorer, 'g_2dplot'):
            ndxplorer.g_2dplot.replot()

    except Exception as e:
        logging.error(f"Histogram computation failed: {e}")
        ndxplorer._histogram["x"] = Histogram1D(edges=np.array([0.0, 1.0]), counts=np.array([0.0]))
        ndxplorer._histogram["y"] = Histogram1D(edges=np.array([0.0, 1.0]), counts=np.array([0.0]))
        ndxplorer._histogram["2d"] = Histogram2D(H=np.zeros((1, 1)), x_edges=np.array([0.0, 1.0]), y_edges=np.array([0.0, 1.0]))
        ndxplorer._histogram.pop("z", None)


def _update_marginal_plots_from_cache(ndxplorer) -> None:
    """Update marginal distribution plots from cached histogram data."""
    logging.debug("Starting marginal plot update")
    
    # Check if deferred init is done and plot objects exist
    if not getattr(ndxplorer, "_deferred_init_done", False):
        logging.debug("Skipping marginal plot update: deferred init not done yet")
        # Try to trigger deferred init if not done
        if hasattr(ndxplorer, '_deferred_init'):
            try:
                ndxplorer._deferred_init()
                logging.debug("Triggered deferred init from marginal plot update")
                # Retry the update after init
                if getattr(ndxplorer, "_deferred_init_done", False):
                    logging.debug("Deferred init completed, retrying marginal plot update")
                    return _update_marginal_plots_from_cache(ndxplorer)
            except Exception as e:
                logging.warning(f"Failed to trigger deferred init: {e}")
        return
    
    # Check if marginal plot objects exist
    has_x_plot = hasattr(ndxplorer, 'g_xplot') and ndxplorer.g_xplot is not None
    has_y_plot = hasattr(ndxplorer, 'g_yplot') and ndxplorer.g_yplot is not None
    has_z_plot = hasattr(ndxplorer, 'g_zplot') and ndxplorer.g_zplot is not None
    has_x_hist = hasattr(ndxplorer, 'g_xhist_m') and ndxplorer.g_xhist_m is not None
    has_y_hist = hasattr(ndxplorer, 'g_yhist_m') and ndxplorer.g_yhist_m is not None
    has_z_hist = hasattr(ndxplorer, 'g_zhist_m') and ndxplorer.g_zhist_m is not None
    
    logging.debug(f"Marginal plot objects: x_plot={has_x_plot}, y_plot={has_y_plot}, z_plot={has_z_plot}")
    logging.debug(f"Marginal hist objects: x_hist={has_x_hist}, y_hist={has_y_hist}, z_hist={has_z_hist}")
    
    if not has_x_hist or not has_y_hist:
        logging.warning("Missing marginal histogram objects - cannot update marginals")
        return
    
    try:
        # Update X marginal
        x_data = _as_edges_counts(ndxplorer._histogram.get("x"))
        if x_data is not None:
            x_bin_edges, x_counts = x_data
            
            # Ensure arrays have same length to prevent IndexError
            x_edges_for_plot = x_bin_edges[1:]
            if len(x_edges_for_plot) != len(x_counts):
                min_len = min(len(x_edges_for_plot), len(x_counts))
                x_edges_for_plot = x_edges_for_plot[:min_len]
                x_counts = x_counts[:min_len]
            
            # Additional validation for Steps curve style
            if len(x_edges_for_plot) == 0 or len(x_counts) == 0:
                logging.debug("Skipping X marginal update: empty data")
                # Set dummy data to prevent display issues
                ndxplorer.g_xhist_m.set_data([0, 1], [0, 0])
            else:
                # For Steps curves, ensure data is valid for current scale
                try:
                    ndxplorer.g_xhist_m.set_data(x_edges_for_plot, x_counts)
                except Exception as e:
                    logging.warning(f"Error setting X marginal data: {e}, using dummy data")
                    ndxplorer.g_xhist_m.set_data([0, 1], [0, 0])
            
            _autoscale_horizontal_hist(ndxplorer.g_xplot, x_bin_edges, x_counts)

        # Update Y marginal
        y_data = _as_edges_counts(ndxplorer._histogram.get("y"))
        if y_data is not None:
            y_bin_edges, y_counts = y_data
            
            # Ensure arrays have same length to prevent IndexError
            y_edges_for_plot = y_bin_edges[1:]
            if len(y_edges_for_plot) != len(y_counts):
                min_len = min(len(y_edges_for_plot), len(y_counts))
                y_edges_for_plot = y_edges_for_plot[:min_len]
                y_counts = y_counts[:min_len]
            
            # Additional validation for Steps curve style
            if len(y_edges_for_plot) == 0 or len(y_counts) == 0:
                logging.debug("Skipping Y marginal update: empty data")
                # Set dummy data to prevent display issues (swapped order for vertical)
                ndxplorer.g_yhist_m.set_data([0, 0], [0, 1])
            else:
                # For Steps curves, ensure data is valid for current scale
                try:
                    # For Y marginal: counts on X-axis (horizontal), edges on Y-axis (vertical)
                    ndxplorer.g_yhist_m.set_data(y_counts, y_edges_for_plot)
                except Exception as e:
                    logging.warning(f"Error setting Y marginal data: {e}, using dummy data")
                    ndxplorer.g_yhist_m.set_data([0, 0], [0, 1])
            
            _autoscale_vertical_hist(ndxplorer.g_yplot, y_bin_edges, y_counts)

        # Update Z marginal if enabled
        # Drawn and autoscaled whenever the marginal exists. Gating this on the
        # checkbox left the widget on screen with its view stuck at 0..1 -- the
        # "axis not computed" that a full-range selection box then filled.
        if "z" in ndxplorer._histogram:
            z_data = _as_edges_counts(ndxplorer._histogram.get("z"))
            if z_data is not None:
                z_bin_edges, z_counts = z_data
                
                # Ensure arrays have same length to prevent IndexError
                z_edges_for_plot = z_bin_edges[1:]
                if len(z_edges_for_plot) != len(z_counts):
                    min_len = min(len(z_edges_for_plot), len(z_counts))
                    z_edges_for_plot = z_edges_for_plot[:min_len]
                    z_counts = z_counts[:min_len]
                
                ndxplorer.g_zhist_m.set_data(z_edges_for_plot, z_counts)
                _autoscale_horizontal_hist(ndxplorer.g_zplot, z_bin_edges, z_counts)

        # Replot the marginal distributions
        ndxplorer.g_xplot.replot()
        ndxplorer.g_yplot.replot()
        if hasattr(ndxplorer, "g_zplot"):
            ndxplorer.g_zplot.replot()
        
        # Ensure marginal plots are visible
        try:
            if hasattr(ndxplorer, 'g_xplot') and ndxplorer.g_xplot:
                ndxplorer.g_xplot.setVisible(True)
            if hasattr(ndxplorer, 'g_yplot') and ndxplorer.g_yplot:
                ndxplorer.g_yplot.setVisible(True)
            if hasattr(ndxplorer, 'g_zplot') and ndxplorer.g_zplot:
                # Shown like the x and y marginals whenever a third parameter
                # is chosen. The "dynamic z-selection" box arms the *gate*;
                # hiding the distribution until the gate is armed asks for a
                # range to be chosen before it can be seen. With no parameter
                # there is nothing to draw, and an empty plot under a stale
                # label is worse than no plot.
                ndxplorer.g_zplot.setVisible(z_axis_available(ndxplorer))
            logging.debug("Ensured marginal plots are visible")
        except Exception as e:
            logging.warning(f"Failed to ensure marginal plots visibility: {e}")
            
    except Exception as e:
        logging.warning(f"Error updating marginal plots from cache: {e}")


def _compute_edge_range(edges: np.ndarray) -> tuple[float, float]:
    arr = np.asarray(edges, dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size < 2:
        return 0.0, 1.0
    start = float(arr[0])
    stop = float(arr[-1])
    if stop == start:
        stop = start + 1.0
    return start, stop


def _compute_count_upper(counts: np.ndarray) -> float:
    arr = np.asarray(counts, dtype=float)
    arr = arr[np.isfinite(arr)]
    if arr.size == 0:
        return 1.0
    max_val = float(np.max(arr))
    if max_val <= 0.0:
        return 1.0
    return max_val * 1.05


def _set_plot_axis_range(plot, axis, min_val: float, max_val: float) -> None:
    """Set a plot axis range for Qwt or compatibility-backed plots."""
    if plot is None or not hasattr(plot, "setAxisScale"):
        return
    try:
        plot.setAxisScale(axis, float(min_val), float(max_val))
    except Exception as exc:
        logging.debug("Could not autoscale axis %s: %s", axis, exc)


def _autoscale_horizontal_hist(plot, bin_edges: np.ndarray, counts: np.ndarray) -> None:
    xmin, xmax = _compute_edge_range(bin_edges)
    ymax = _compute_count_upper(counts)

    if not (np.isfinite(xmin) and np.isfinite(xmax)):
        logging.warning("Invalid X axis range (NaN/Inf detected), using default range")
        xmin, xmax = 0.0, 1.0
    if not np.isfinite(ymax):
        logging.warning("Invalid Y axis range (NaN/Inf detected), using default range")
        ymax = 1.0

    for axis in ("bottom", "top"):
        _set_plot_axis_range(plot, axis, xmin, xmax)
    for axis in ("left", "right"):
        _set_plot_axis_range(plot, axis, 0.0, ymax)


def _autoscale_vertical_hist(plot, bin_edges: np.ndarray, counts: np.ndarray) -> None:
    ymin, ymax = _compute_edge_range(bin_edges)
    xmax = _compute_count_upper(counts)

    if not (np.isfinite(ymin) and np.isfinite(ymax)):
        logging.warning("Invalid Y axis range (NaN/Inf detected), using default range")
        ymin, ymax = 0.0, 1.0
    if not np.isfinite(xmax):
        logging.warning("Invalid X axis range (NaN/Inf detected), using default range")
        xmax = 1.0

    for axis in ("left", "right"):
        _set_plot_axis_range(plot, axis, ymin, ymax)
    for axis in ("bottom", "top"):
        _set_plot_axis_range(plot, axis, 0.0, xmax)


def update_plots(ndxplorer, skip_clustering: bool = False, skip_cache_invalidation: bool = False) -> None:
    if not getattr(ndxplorer, "_deferred_init_done", False) or ndxplorer.g_2dplot is None:
        logging.info("update_plots: deferred_init not done or g_2dplot is None")
        return
    logging.debug("update_plots(skip_clustering=%s, skip_cache_invalidation=%s)", skip_clustering, skip_cache_invalidation)
    if not skip_cache_invalidation:
        # Selective invalidation: the value/mask/filtered/axis caches now self-guard
        # on data_source.data_version and on the full selection/view key, so a blanket
        # clear is only needed when the underlying data actually changed. View-only
        # updates (pan/zoom, colormap, axis toggles) reuse the caches instead of
        # recomputing the mask + filtered slice on every interaction.
        data_version = ndxplorer.data_source.data_version
        if getattr(ndxplorer, "_last_invalidated_data_version", None) != data_version:
            ndxplorer.invalidate_values_cache()
            ndxplorer._last_invalidated_data_version = data_version

    # Use the data_source property which handles both _data_source and data_manager
    data_source = ndxplorer.data_source
    is_empty = data_source.empty
    logging.debug("update_plots: data_source.empty=%s, n_parameters=%d",
                  is_empty, data_source.n_parameters)

    if is_empty:
        logging.info("update_plots: Data source is empty, showing empty plots")
        if hasattr(ndxplorer, "_set_data_loaded"):
            ndxplorer._set_data_loaded(False)
        _show_empty_plots(ndxplorer)
        return

    ndxplorer.update_parameter_names()
    ndxplorer.update_cmap()

    logging.debug("update_plots: Checking clustering: _use_clustering=%s, skip_clustering=%s", ndxplorer._use_clustering, skip_clustering)
    if ndxplorer._use_clustering and ndxplorer._cluster_labels is None and not skip_clustering:
        # The clusterer is loaded through the shared getter, which caches and
        # logs; a second private import here is how the two paths drifted into
        # disagreeing about whether clustering was available at all.
        if get_hdbscan() is not None:
            ndxplorer.on_apply_clustering()
            return

    data_ready = ndxplorer.is_data_ready()
    logging.debug("update_plots: data_ready=%s", data_ready)
    if data_ready:
        logging.debug("Calling update_histograms from update_plots")
        update_histograms(ndxplorer)
    else:
        logging.debug("update_plots: data/axes not ready, skipping histogram update")

    # Keep the NDxplorer background/logo visible whenever no usable data is present.
    # Use the public data_source accessor so data-manager-backed loads are handled correctly.
    try:
        ds_for_visibility = ndxplorer.data_source
    except Exception:
        ds_for_visibility = getattr(ndxplorer, "_data_source", None)
    if ds_for_visibility is None or getattr(ds_for_visibility, "empty", True):
        if hasattr(ndxplorer, "_set_data_loaded"):
            ndxplorer._set_data_loaded(False)
        _show_background(ndxplorer)
        # When there's no data, still refresh the empty plot scaffolding.
        _show_empty_plots(ndxplorer)
        return
    if not data_ready:
        # Data source exists but axes selections aren't ready yet (e.g., combos blank) —
        # keep the background visible until histograms can be computed.
        # BUT: if we already have data loaded, don't toggle background to avoid flicker during selection updates
        has_data_loaded = getattr(ndxplorer, "_has_real_data", False)
        if not has_data_loaded:
            if hasattr(ndxplorer, "_set_data_loaded"):
                ndxplorer._set_data_loaded(False)
            _show_background(ndxplorer)
        return

    _hide_background(ndxplorer)
    if hasattr(ndxplorer, "_set_data_loaded"):
        ndxplorer._set_data_loaded(True)
    
    # Ensure plot container is visible
    try:
        plot_container = getattr(ndxplorer, "_plot_container", None)
        if plot_container is not None:
            plot_container.setVisible(True)
            plot_container.raise_()
            logging.debug("Made plot container visible and raised to front")
    except Exception as e:
        logging.debug(f"Could not make plot container visible: {e}")

    # Force marginal plots to be visible after data is ready
    try:
        if hasattr(ndxplorer, 'g_xplot') and ndxplorer.g_xplot:
            ndxplorer.g_xplot.setVisible(True)
            ndxplorer.g_xplot.raise_()
            logging.debug("Forced X marginal plot to be visible")
        if hasattr(ndxplorer, 'g_yplot') and ndxplorer.g_yplot:
            ndxplorer.g_yplot.setVisible(True)
            ndxplorer.g_yplot.raise_()
            logging.debug("Forced Y marginal plot to be visible")
        if hasattr(ndxplorer, 'g_zplot') and ndxplorer.g_zplot:
            # Shown whenever a third parameter is chosen: see the note above.
            visible = z_axis_available(ndxplorer)
            ndxplorer.g_zplot.setVisible(visible)
            if visible:
                ndxplorer.g_zplot.raise_()
            logging.debug("Z marginal plot visibility: %s", visible)
    except Exception as e:
        logging.warning(f"Failed to force marginal plots visibility: {e}")

    # Check if histograms were successfully computed
    x_hist = ndxplorer._histogram.get("x")
    y_hist = ndxplorer._histogram.get("y")
    
    # ``None`` is the "nothing computed yet" state (startup, or a load in
    # progress), not a failure — only a histogram that exists and is unusable is
    # worth an error.
    def _report_missing(axis: str, hist) -> None:
        if hist is None:
            logging.debug("%s histogram not computed yet; showing empty plots", axis)
        else:
            logging.error("%s histogram computation failed or returned empty result", axis)

    x_data = _as_edges_counts(x_hist)
    if x_data is None:
        _report_missing("X", x_hist)
        _show_empty_plots(ndxplorer)
        return

    y_data = _as_edges_counts(y_hist)
    if y_data is None:
        _report_missing("Y", y_hist)
        _show_empty_plots(ndxplorer)
        return

    # Extract 1D histogram data (edges, counts)
    x_bin_edges, x_counts = x_data

    # Update X marginal
    ndxplorer.g_xhist_m.set_data(x_bin_edges, x_counts)
    _autoscale_horizontal_hist(ndxplorer.g_xplot, x_bin_edges, x_counts)
    ndxplorer.g_xplot.replot()

    # Extract Y histogram data (edges, counts)
    y_bin_edges, y_counts = y_data

    # Update Y marginal: counts on X-axis (horizontal), edges on Y-axis (vertical)
    ndxplorer.g_yhist_m.set_data(y_counts, y_bin_edges)
    _autoscale_vertical_hist(ndxplorer.g_yplot, y_bin_edges, y_counts)
    ndxplorer.g_yplot.replot()

    # Handle Z histogram if enabled
    z_hist = ndxplorer._histogram.get("z")
    z_data = _as_edges_counts(z_hist)
    # As above: the gate decides whether the z range *filters*, not whether the
    # marginal is drawn or its axis computed.
    if z_data is not None:
        z_bin_edges, z_counts = z_data
        ndxplorer.g_zhist_m.set_data(z_bin_edges, z_counts)
        _autoscale_horizontal_hist(ndxplorer.g_zplot, z_bin_edges, z_counts)
        ndxplorer.g_zplot.replot()

    # Histograms were just computed above; don't recompute them here (that
    # doubled the per-interaction histogram work).
    ndxplorer.update_spinbox_limits(recompute=False)
    ndxplorer.update_2d_plot()
    ndxplorer.g_2dplot.replot()

    # Final check: ensure marginal plots are still visible and updated
    try:
        if hasattr(ndxplorer, 'g_xplot') and ndxplorer.g_xplot:
            ndxplorer.g_xplot.setVisible(True)
            ndxplorer.g_xplot.raise_()
            ndxplorer.g_xplot.replot()
        if hasattr(ndxplorer, 'g_yplot') and ndxplorer.g_yplot:
            ndxplorer.g_yplot.setVisible(True)
            ndxplorer.g_yplot.raise_()
            ndxplorer.g_yplot.replot()
        if hasattr(ndxplorer, 'g_zplot') and ndxplorer.g_zplot:
            # The third of three places that decided this. Shown whenever a
            # third parameter is chosen: see the note in the first of them.
            visible = z_axis_available(ndxplorer)
            ndxplorer.g_zplot.setVisible(visible)
            if visible:
                ndxplorer.g_zplot.raise_()
                ndxplorer.g_zplot.replot()
        logging.debug("Final marginal plot visibility and replot completed")
    except Exception as e:
        logging.warning(f"Failed in final marginal plot update: {e}")


def _show_empty_plots(ndxplorer):
    """Show empty placeholder plots when no data is available."""
    ndxplorer.g_xhist_m.set_data([0, 1], [0, 0])
    ndxplorer.g_yhist_m.set_data([0, 0], [0, 1])
    ndxplorer.g_zhist_m.set_data([0, 1], [0, 0])
    ndxplorer.cax.set_data(np.zeros((1, 1)))
    _show_background(ndxplorer)
    
    ndxplorer.g_2dplot.set_axis_scale('xBottom', 0, 1)
    ndxplorer.g_2dplot.set_axis_scale('yLeft', 0, 1)
    ndxplorer.g_xplot.setAxisScale("bottom", 0, 1)
    ndxplorer.g_xplot.setAxisScale("top", 0, 1)
    ndxplorer.g_xplot.setAxisScale("left", 0, 1)
    ndxplorer.g_yplot.setAxisScale("left", 0, 1)
    ndxplorer.g_yplot.setAxisScale("right", 0, 1)
    ndxplorer.g_yplot.setAxisScale("bottom", 0, 1)
    ndxplorer.g_zplot.setAxisScale("bottom", 0, 1)
    ndxplorer.g_zplot.setAxisScale("left", 0, 1)
    ndxplorer.g_xplot.replot()
    ndxplorer.g_yplot.replot()
    ndxplorer.g_zplot.replot()
    ndxplorer.g_2dplot.replot()


def auto_contrast(ndxplorer: "NDXplorer", skip_if_preserve: bool = True):
    """Auto-adjust contrast based on 2D histogram percentiles."""
    # Skip contrast update if preserving contrast during selection operations
    if skip_if_preserve and getattr(ndxplorer, '_preserve_contrast', False):
        logging.debug("auto_contrast: preserving contrast, skipping auto contrast")
        return
        
    logging.debug("Auto contrast triggered")
    
    # Check if histogram exists before proceeding
    if not hasattr(ndxplorer, '_histogram') or not ndxplorer._histogram:
        logging.debug("No histogram dictionary available")
        return
    
    try:
        if "2d" not in ndxplorer._histogram:
            logging.debug("No 2D histogram data available")
            return

        # Extract data from 2D histogram (handle both old tuple and new clean formats)
        hist_2d = ndxplorer._histogram.get("2d")
        if hist_2d is None:
            logging.debug("No 2D histogram available yet")
            return
        
        if hasattr(hist_2d, 'H'):
            # New clean Histogram2D object
            hist = hist_2d.H
        elif isinstance(hist_2d, tuple) and len(hist_2d) == 3:
            # Old tuple format (H, x_edges, y_edges)
            hist, _, _ = hist_2d
        else:
            logging.debug("Histogram format not ready yet (expected during initialization)")
            return
            
        if (
            hist is None
            or hist.size == 0
            or np.all(hist == 0)
            or np.all(np.isnan(hist))
        ):
            logging.debug("Histogram empty/all zero/NaN – using defaults")
            ndxplorer.vmin = 0
            ndxplorer.vmax = 1
            ndxplorer.on_vmin_vmax_changed()
            return

        from ..core.histograms import auto_contrast_limits

        vmin, vmax = auto_contrast_limits(hist, ndxplorer.checkBoxLogCounts.isChecked())
        logging.debug("Setting auto contrast: vmin=%s vmax=%s", vmin, vmax)
        ndxplorer.vmin = vmin
        ndxplorer.vmax = vmax
        ndxplorer.on_vmin_vmax_changed()
    except (ValueError, KeyError, TypeError, IndexError) as exc:
        logging.warning("Error in auto contrast: %s", exc)
        ndxplorer.vmin = 0
        ndxplorer.vmax = 1
        ndxplorer.on_vmin_vmax_changed()


def update_spinbox_limits(ndxplorer, *, low_pct: float = 0.1, high_pct: float = 99) -> None:
    """Set ``vmin``/``vmax`` from percentiles of the current 2D histogram.

    Parameters
    ----------
    ndxplorer : object
        The plot window holding ``_histogram`` and the colour-limit spin boxes.
    low_pct, high_pct : float, optional
        Percentiles bounding the colour scale, in ``[0, 100]``. Keyword-only:
        a Qt signal argument reaching ``low_pct`` positionally is the bug this
        guards against.
    """
    # Skip contrast update if preserving contrast during selection operations
    if getattr(ndxplorer, '_preserve_contrast', False):
        logging.debug("update_spinbox_limits: preserving contrast, skipping update")
        return
        
    logging.debug(
        "update_spinbox_limits(low_pct=%s, high_pct=%s)", low_pct, high_pct
    )
    try:
        # Extract data from 2D histogram (handle both old tuple and new clean formats)
        hist_2d = ndxplorer._histogram.get("2d")
        if hist_2d is None:
            logging.debug("No 2D histogram available yet for marginal plot update")
            return
        
        if hasattr(hist_2d, 'H'):
            # New clean Histogram2D object
            H = hist_2d.H
        elif isinstance(hist_2d, tuple) and len(hist_2d) == 3:
            # Old tuple format (H, x_edges, y_edges)
            H, _, _ = hist_2d
        else:
            logging.debug("update_spinbox_limits: invalid histogram format")
            return
    except Exception:
        logging.debug("update_spinbox_limits: histogram missing")
        return

    if not np.any(np.isfinite(H)):
        logging.debug("update_spinbox_limits: no finite bins")
        return

    from ..core.histograms import colour_limits

    vmin, vmax = colour_limits(H, ndxplorer.checkBoxLogCounts.isChecked(), low_pct, high_pct)
    ndxplorer.vmin = vmin
    ndxplorer.vmax = vmax
    ndxplorer.on_vmin_vmax_changed()


def _show_background(ndxplorer):
    """Display the NDxplorer background/logo and hide the histogram image layer."""
    if hasattr(ndxplorer, "bg_image_item") and ndxplorer.bg_image_item is not None:
        ndxplorer.bg_image_item.setVisible(True)
    if getattr(ndxplorer, "cax", None) is not None:
        ndxplorer.cax.setVisible(False)


def _hide_background(ndxplorer):
    """Hide the background/logo so the histogram image is fully visible."""
    if hasattr(ndxplorer, "bg_image_item") and ndxplorer.bg_image_item is not None:
        ndxplorer.bg_image_item.setVisible(False)
    if getattr(ndxplorer, "cax", None) is not None:
        ndxplorer.cax.setVisible(True)


__all__ = [
    'update_histograms',
    'update_plots',
    'auto_contrast',
    'update_spinbox_limits',
]
