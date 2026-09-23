"""Axis-related helpers extracted from plot_main."""

from __future__ import annotations

from typing import Optional, Sequence

import numpy as np

from ..logging_config import logging


#: What a frame axis can be called. "T pixel" and "Z pixel" are what the older
#: burst exporters wrote; "Frame" is what a stack of images is actually called,
#: and what the CLI and the image writer here use. Recognising only the first
#: two meant a frame stack opened with no frame selector and every frame drawn
#: on top of the others -- which looks like one noisy image rather than like a
#: missing control.
_FRAME_COLUMN_NAMES = ("t pixel", "z pixel", "frame")


#: Words that turn a frame-ish column name into something else entirely. A
#: "Frame Time (s)" is a timestamp: taking it for the frame index builds a
#: selector with one entry per second of acquisition and shows one frame's worth
#: of bursts as if it were the whole stack.
_NOT_A_FRAME_INDEX = ("time", "duration", "rate", "period", "interval")


def frame_column(param_names: Sequence[str]) -> Optional[str]:
    """The column that indexes the frames, or None.

    In the order above, so a file carrying both a "T pixel" and a "Frame"
    resolves the way it always did.

    Two passes over the whole name list, not two passes per candidate name: an
    exact match on a *later* candidate beats a loose match on an earlier one,
    because "Frame" naming a frame index is a better answer than "T pixel (µs)"
    happening to contain "t pixel".
    """
    def _rejected(text: str) -> bool:
        return any(word in text for word in _NOT_A_FRAME_INDEX)

    # Exact, or exact followed by a unit -- "Frame (index)" is still a frame.
    for wanted in _FRAME_COLUMN_NAMES:
        for name in param_names:
            text = str(name).lower()
            if text == wanted or text.startswith(wanted + " ("):
                if not _rejected(text):
                    return name

    # Loose: the candidate appears somewhere in the name. This is what finds a
    # "Frame Nbr" or an "img T pixel", and it is also what used to re-admit the
    # "Frame Time (s)" the exact pass had just rejected -- so it applies the
    # same rejection.
    for wanted in _FRAME_COLUMN_NAMES:
        for name in param_names:
            text = str(name).lower()
            if wanted in text and not _rejected(text):
                return name
    return None


def check_and_set_image_axes(ndxplorer: "NDXplorer") -> bool:
    logging.debug("check_and_set_image_axes()")
    # Use the data_source property which handles both _data_source and data_manager
    try:
        data_source = ndxplorer.data_source
    except Exception as exc:
        logging.debug(f"Could not get data_source: {exc}")
        return False
    
    if data_source is None or data_source.empty:
        logging.info("Image detection skipped: data_source is None or empty")
        return False

    param_names = data_source.parameter_names
    logging.info(f"Image detection: checking parameter names: {list(param_names)}")

    has_x_pixel = any("x pixel" in name.lower() for name in param_names)
    has_y_pixel = any("y pixel" in name.lower() for name in param_names)
    
    logging.info(f"Image detection: has_x_pixel={has_x_pixel}, has_y_pixel={has_y_pixel}")

    if not (has_x_pixel and has_y_pixel):
        logging.info("Image detection failed: X pixel or Y pixel columns not found")
        return False

    logging.info("Image data detected (X pixel and Y pixel columns found)")
    x_pixel_param = next((name for name in param_names if "x pixel" in name.lower()), None)
    y_pixel_param = next((name for name in param_names if "y pixel" in name.lower()), None)
    
    frame_param = frame_column(param_names)

    # Set X and Y axes to the pixel parameters
    # Use match_contains=False for exact matching to avoid matching "T pixel" 
    x_success = ndxplorer.plot_control.set_axis_by_name("x", x_pixel_param, match_contains=False, block_signals=True)
    y_success = ndxplorer.plot_control.set_axis_by_name("y", y_pixel_param, match_contains=False, block_signals=True)
    
    if not x_success:
        logging.warning("Failed to set X axis to %s", x_pixel_param)
    if not y_success:
        logging.warning("Failed to set Y axis to %s", y_pixel_param)
    
    # Even if setting axes failed, continue with image setup (return True at end)
    # This prevents apply_default_axes_from_settings from overriding

    photon_param = next((name for name in param_names if "number of photons" in name.lower() or "Number of Photons" in name), None)
    logging.debug("Weight parameter: %s", photon_param)
    weight_success = ndxplorer.plot_control.set_axis_by_name(
        "weight", photon_param, match_contains=True, block_signals=True
    )
    if weight_success:
        logging.debug("Set weighting to %s", photon_param)
        try:
            ndxplorer.weight_param = photon_param
            ndxplorer.weight_enabled = True
            # Automatically check the weight checkbox when weight parameter is detected
            ndxplorer.checkBoxWeight.setChecked(True)
            logging.info("Automatically enabled weight checkbox for %s", photon_param)
        except Exception as exc:  # pragma: no cover - defensive
            logging.debug("Failed to enable weight parameter: %s", exc)
    else:
        logging.debug("No matching weight parameter found, using default")

    x_values = data_source.column_view(param_names.index(x_pixel_param))
    y_values = data_source.column_view(param_names.index(y_pixel_param))
    logging.debug("x_pixel_param: %s, x_values: %s", x_pixel_param, x_values)
    logging.debug("y_pixel_param: %s, y_values: %s", y_pixel_param, y_values)

    # Handle empty data arrays safely
    if len(x_values) > 0:
        x_pixels = int(np.max(x_values)) + 1
    else:
        x_pixels = 256  # Default size
    if len(y_values) > 0:
        y_pixels = int(np.max(y_values)) + 1
    else:
        y_pixels = 256  # Default size
    logging.info("Image dimensions: %sx%s pixels", x_pixels, y_pixels)

    logging.info(f"Setting histogram bins to match image dimensions: {x_pixels}x{y_pixels}")
    ndxplorer.plot_control.n_xhist_1d = x_pixels
    ndxplorer.plot_control.n_yhist_1d = y_pixels
    ndxplorer.plot_control.n_xhist_2d = x_pixels
    ndxplorer.plot_control.n_yhist_2d = y_pixels
    
    # Also update UI spinboxes so bins are read correctly
    if hasattr(ndxplorer.plot_control, 'spinBoxNXHist1D'):
        ndxplorer.plot_control.spinBoxNXHist1D.setValue(x_pixels)
    if hasattr(ndxplorer.plot_control, 'spinBoxNYHist1D'):
        ndxplorer.plot_control.spinBoxNYHist1D.setValue(y_pixels)
    if hasattr(ndxplorer.plot_control, 'spinBoxNXHist2D'):
        ndxplorer.plot_control.spinBoxNXHist2D.setValue(x_pixels)
    if hasattr(ndxplorer.plot_control, 'spinBoxNYHist2D'):
        ndxplorer.plot_control.spinBoxNYHist2D.setValue(y_pixels)
    
    logging.info(f"Bins set: n_xhist_2d={ndxplorer.plot_control.n_xhist_2d}, n_yhist_2d={ndxplorer.plot_control.n_yhist_2d}")
    # The range spans the PIXELS, not the largest pixel INDEX. With n bins over
    # [0, n) each bin is exactly one pixel: bin k covers [k, k+1) and holds
    # pixel k. Over [0, n-1] -- the largest index -- each bin is (n-1)/n of a
    # pixel wide, so pixel and bin drift apart across the image and the picture
    # picks up a moire that is not in the data.
    ndxplorer.plot_control.xmin = 0
    ndxplorer.plot_control.ymin = 0
    ndxplorer.plot_control.xmax = x_pixels
    ndxplorer.plot_control.ymax = y_pixels

    if frame_param:
        logging.info("Frame stack detected (%s)", frame_param)
    # The frame selector itself is not set up here any more. It is one case of
    # playing a data set back along one of its columns, which every data set can
    # do -- a burst table has a macro time -- so it is set up for every load, by
    # ``plot_control.setup_playback``, and not only for the images that happen to
    # come through this function.

    logging.debug("Set binning and ranges to match pixel dimensions")
    # Don't call update_plots here - it will be called by _apply_axes_and_refresh
    # after this function returns True
    return True


def apply_default_axes_from_settings(ndxplorer: "NDXplorer") -> bool:
    logging.debug("apply_default_axes_from_settings()")
    try:
        defaults = ndxplorer.settings.get("default_axes", {}) if hasattr(ndxplorer, "settings") else {}
    except Exception:
        defaults = {}
    if not isinstance(defaults, dict) or not defaults:
        logging.debug("No default_axes configured in settings; skipping.")
        return False

    try:
        param_names = list(ndxplorer.data_source.parameter_names)
    except Exception:
        param_names = []

    changed = False

    def _set_axis(ax_key, axis_name):
        if not axis_name or not isinstance(axis_name, str):
            return False
        if axis_name in param_names:
            ok = ndxplorer.plot_control.set_axis_by_name(ax_key, axis_name, match_contains=False, block_signals=True)
            return bool(ok)
        ok = ndxplorer.plot_control.set_axis_by_name(ax_key, axis_name, match_contains=True, block_signals=True)
        return bool(ok)

    for ax_key in ("x", "y", "z"):
        name = defaults.get(ax_key)
        if _set_axis(ax_key, name):
            changed = True

    wname = defaults.get("weight")
    if wname and _set_axis("weight", wname):
        changed = True

    if changed:
        try:
            ndxplorer.plot_control.on_x_axis_changed()
        except Exception:
            pass
        try:
            ndxplorer.plot_control.on_y_axis_changed()
        except Exception:
            pass
        try:
            ndxplorer.plot_control.on_z_axis_changed()
        except Exception:
            pass
        logging.info("Applied default axes from settings.")
        return True

    logging.debug("No default axes were applied (names may not match current dataset).")
    return False


def _filtered_values(values, scale: str):
    arr = np.asarray(values)
    finite_mask = np.isfinite(arr)
    filtered = arr[finite_mask]
    if scale == "log":
        filtered = filtered[filtered > 0]
    return filtered


#: Percentiles "Auto" ranges to, instead of the extremes. A burst table's
#: photon count is the case that forces this: on a real measurement the largest
#: burst held 450 094 photons against a 99.9th percentile of 1 108 -- four
#: hundred times the bulk of the distribution -- so auto-ranging to the maximum
#: drew every burst in the first pixel of the axis and called it a histogram.
AUTO_RANGE_PERCENTILES = (0.1, 99.9)

#: How close an extreme has to be, as a fraction of the robust span, to be taken
#: instead of the percentile. Without this an axis with no outliers at all --
#: an efficiency running 0 to 1 -- would still lose a sliver off each end for no
#: reason, and "Auto" would stop meaning "all of it" on exactly the data where
#: it already worked.
AUTO_RANGE_SNAP = 0.05


def robust_axis_range(values, scale: str = "lin") -> tuple[float, float]:
    """``(min, max)`` for "Auto": the data's range, less its outliers.

    Percentiles rather than extremes, then each end snapped back out to the true
    extreme when that extreme is close anyway. So a clean axis auto-ranges to
    exactly its data, and one with a runaway tail auto-ranges to where the data
    actually is.
    """
    filtered = _filtered_values(values, scale)
    if filtered.size == 0:
        return 0.0, 0.0
    low = float(np.min(filtered))
    high = float(np.max(filtered))
    if filtered.size < 3 or not (high > low):
        return low, high
    q_low, q_high = (float(v) for v in
                     np.percentile(filtered, AUTO_RANGE_PERCENTILES))
    span = q_high - q_low
    if not (span > 0):
        return low, high
    if q_low - low <= AUTO_RANGE_SNAP * span:
        q_low = low
    if high - q_high <= AUTO_RANGE_SNAP * span:
        q_high = high
    return q_low, q_high


def compute_axis_min(values, scale: str = "lin") -> float:
    return robust_axis_range(values, scale)[0]


def compute_axis_max(values, scale: str = "lin") -> float:
    return robust_axis_range(values, scale)[1]


def settings_for_axis(name: str, axis_settings, with_2d: bool = True) -> Optional[dict]:
    """How an axis showing parameter *name* is set up, from the axis settings.

    Parameters
    ----------
    name : str
        The parameter the axis now shows.
    axis_settings : mapping
        Parameter name -> ``{"min", "max", "scale", "n_bins_1d", "n_bins_2d"}``
        (``mfd.axis.json``).
    with_2d : bool
        Whether the axis has a 2-D bin count (x and y do, z does not).

    Returns
    -------
    dict or None
        ``{"bins_1d", "bins_2d", "min", "max", "scale"}``; ``min``/``max`` are
        ``None`` where the settings do not say (the caller auto-ranges those),
        ``bins_2d`` is ``None`` without a 2-D axis. ``None`` altogether when the
        parameter has no settings: the axis is auto-ranged.

    A pixel axis gets one 2-D bin per pixel -- as many bins as its maximum.
    """
    d = axis_settings.get(name) if axis_settings else None
    if not isinstance(d, dict):
        return None
    bins_2d = None
    if with_2d:
        bins_2d = int(d.get("max", 256)) if "pixel" in name.lower() else d.get("n_bins_2d", 50)
    return {
        "bins_1d": d.get("n_bins_1d", 50),
        "bins_2d": bins_2d,
        "min": d.get("min"),
        "max": d.get("max"),
        "scale": d.get("scale", "lin"),
    }
