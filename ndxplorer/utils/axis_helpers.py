"""Axis-related helpers extracted from plot_main."""

from __future__ import annotations

from dataclasses import dataclass
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


@dataclass(frozen=True)
class ImageAxes:
    """What makes a table an image, and how to show it as one.

    Attributes
    ----------
    x, y : str
        The pixel columns (``"X pixel"``/``"Y pixel"``, any case).
    nx, ny : int
        Pixels across: the largest index plus one (256 for an empty column).
    weight : str or None
        The photon-count column the histogram is weighted by.
    frame : str or None
        The column that indexes the frames of a stack.
    """

    x: str
    y: str
    nx: int
    ny: int
    weight: Optional[str] = None
    frame: Optional[str] = None

    @property
    def x_range(self):
        """``(0, nx)``: one bin per pixel, bin *k* holding pixel *k*."""
        return (0.0, float(self.nx))

    @property
    def y_range(self):
        return (0.0, float(self.ny))


def _pixels(values) -> int:
    values = np.asarray(values)
    return int(np.max(values)) + 1 if values.size else 256


def image_axes(data_source) -> Optional[ImageAxes]:
    """The image a table holds, or ``None`` when it is not one.

    A table with an ``X pixel`` and a ``Y pixel`` column is an image: those are
    the axes, one bin per pixel over ``[0, n)`` (over ``[0, n-1]`` each bin is
    ``(n-1)/n`` of a pixel and the picture picks up a moire that is not in the
    data), weighted by the photon count, and played back along its frame
    column. Both GUIs show an image this way.
    """
    if data_source is None or data_source.empty:
        return None
    names = list(data_source.parameter_names)
    x = next((n for n in names if "x pixel" in n.lower()), None)
    y = next((n for n in names if "y pixel" in n.lower()), None)
    if x is None or y is None:
        return None
    weight = next((n for n in names if "number of photons" in n.lower()), None)
    return ImageAxes(
        x=x, y=y,
        nx=_pixels(data_source.column_view(names.index(x))),
        ny=_pixels(data_source.column_view(names.index(y))),
        weight=weight, frame=frame_column(names),
    )


def check_and_set_image_axes(ndxplorer: "NDXplorer") -> bool:
    """Show an image table as an image in the Qt window (see :func:`image_axes`)."""
    logging.debug("check_and_set_image_axes()")
    try:
        image = image_axes(ndxplorer.data_source)
    except Exception as exc:
        logging.debug(f"Could not get data_source: {exc}")
        return False
    if image is None:
        logging.info("Image detection: no X pixel / Y pixel columns")
        return False
    logging.info("Image data detected: %sx%s pixels on %s, %s", image.nx, image.ny,
                 image.x, image.y)

    # Exact matching, so "X pixel" does not find "T pixel". Even if setting an
    # axis fails the image setup goes on (and returns True), so the settings'
    # default axes do not override it.
    for key, name in (("x", image.x), ("y", image.y)):
        if not ndxplorer.plot_control.set_axis_by_name(key, name, match_contains=False,
                                                        block_signals=True):
            logging.warning("Failed to set %s axis to %s", key.upper(), name)

    if image.weight and ndxplorer.plot_control.set_axis_by_name(
            "weight", image.weight, match_contains=True, block_signals=True):
        try:
            ndxplorer.weight_param = image.weight
            ndxplorer.weight_enabled = True
            ndxplorer.checkBoxWeight.setChecked(True)
            logging.info("Automatically enabled weight checkbox for %s", image.weight)
        except Exception as exc:  # pragma: no cover - defensive
            logging.debug("Failed to enable weight parameter: %s", exc)

    pc = ndxplorer.plot_control
    pc.n_xhist_1d = pc.n_xhist_2d = image.nx
    pc.n_yhist_1d = pc.n_yhist_2d = image.ny
    for name, value in (("spinBoxNXHist1D", image.nx), ("spinBoxNYHist1D", image.ny),
                        ("spinBoxNXHist2D", image.nx), ("spinBoxNYHist2D", image.ny)):
        if hasattr(pc, name):
            getattr(pc, name).setValue(value)
    pc.xmin, pc.xmax = image.x_range
    pc.ymin, pc.ymax = image.y_range
    # The frame selector is set up for every load by ``plot_control.setup_playback``.
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
