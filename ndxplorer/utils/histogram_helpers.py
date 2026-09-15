"""Reading the plot controls, and the odds and ends around a histogram.

The computation itself, and the description of an axis it takes, are in
:mod:`ndxplorer.utils.histogram_computation`. What is here is the part that
knows about the interface: turning the controls into that description, and the
row filter to go with it.
"""

from __future__ import annotations

import numpy as np
from typing import Optional

from ..logging_config import logging
from .histogram_computation import Axis, HistogramAxes

if False:  # pragma: no cover - type checking hints without runtime import
    from ..core.plot_main import NDXplorer


def bins_token(arr) -> str:
    """A compact cache-key token for an array of bin edges.

    ``str(numpy_array)`` is not usable here: it triggers a full ``array2string``
    formatting pass (~5-7 ms across the five arrays a redraw needs) and it
    *truncates* long arrays with ``"..."``, so distinct bin sets collide.

    The token is O(1) -- four numbers read out of the array, never a pass over
    it -- and it has to separate the bin sets that actually occur. Count, first
    and last do not: :func:`get_bins` builds a log axis with
    ``np.logspace(log10(lo), log10(hi), n + 1)`` and a linear one with
    ``np.linspace(lo, hi, n + 1)``, which agree on all three. Switching an axis
    to log therefore left the key unchanged, and the gate went on selecting the
    population the old edges covered -- with nothing in the interface saying so.

    Its caller is :meth:`BitmapSelection.gate_key`: a painted cell means "these
    data values", and the edges are what decides which.

    The middle edge is what separates them, and it separates any two monotone
    spacings over the same endpoints, which is the general form of the problem.
    """
    a = np.asarray(arr)
    if a.size == 0:
        return "0"
    mid = float(a[a.size // 2])
    return f"{a.size}:{float(a[0]):.8g}:{mid:.8g}:{float(a[-1]):.8g}"


def get_bins(plot_control, arange, scale, n_1d, n_2d):
    """Return 1D/2D bin edges for a given axis."""
    logging.debug("get_bins: arange=%s scale=%s n_1d=%s n_2d=%s", arange, scale, n_1d, n_2d)
    xmin, xmax = arange
    if scale == "log":
        if xmin <= 0:
            xmin = 1e-6
        if xmax <= 0:
            xmax = 1e-6
        x_func = np.logspace
        x_start = np.log10(xmin)
        x_stop = np.log10(xmax)
    else:
        x_func = np.linspace
        x_start = xmin
        x_stop = xmax
    # n + 1 EDGES for n BINS. These come from spin boxes labelled "Bin", and
    # this returned n: asking for 256 bins gave 255, each one 256/255 of the
    # width it should have been. On a pixel axis that is the difference between
    # one bin per pixel and a bin that slides across the image, which shows up
    # as a moire in the picture rather than as an obviously wrong number.
    #
    # These edges are for the PLOT -- ticks, and the gates that place a painted
    # mask. Nothing bins with them; see histogram_computation.Axis.
    x_bins_1d = x_func(x_start, x_stop, int(n_1d) + 1)
    x_bins_2d = x_func(x_start, x_stop, int(n_2d) + 1)
    return x_bins_1d, x_bins_2d


def joint_axis_mask(x: np.ndarray, y: np.ndarray) -> Optional[np.ndarray]:
    """Rows that carry a usable value on *both* plotted axes.

    The 2D map can only show a burst that has an x *and* a y value, but a 1D
    histogram silently drops only the NaNs of its own column. Computed
    independently, the marginals therefore describe a larger population than the
    image below them -- a column that is defined for every burst (a proximity
    ratio) shows its full distribution next to a map built from the handful of
    bursts that also have the other column (a per-state lifetime). Restricting
    every marginal to this mask makes them true projections of what is plotted.

    Parameters
    ----------
    x, y : np.ndarray
        The two plotted axis columns, row-aligned and equally long.

    Returns
    -------
    np.ndarray or None
        Boolean keep-mask, or ``None`` when every row already qualifies -- the
        common case, and worth skipping the copies for.
    """
    def _finite(a: np.ndarray) -> Optional[np.ndarray]:
        arr = np.asarray(a)
        # Only floating/complex columns can carry NaN or Inf; integer and
        # datetime columns are always usable and np.isfinite rejects some of them.
        if arr.dtype.kind not in "fc":
            return None
        return np.isfinite(arr)

    fx, fy = _finite(x), _finite(y)
    if fx is None and fy is None:
        return None
    if fx is None:
        keep = fy
    elif fy is None:
        keep = fx
    else:
        keep = fx & fy
    if keep.all():
        return None
    return keep


def apply_joint_axis_mask(x, y, z=None, weights=None):
    """Restrict axis columns (and weights) to :func:`joint_axis_mask`.

    Returns the arrays unchanged when nothing has to be dropped.
    """
    if x is None or y is None or len(x) != len(y):
        return x, y, z, weights
    keep = joint_axis_mask(x, y)
    if keep is None:
        return x, y, z, weights
    logging.debug(
        "joint axis mask: %d of %d rows have a value on both axes", int(keep.sum()), keep.size
    )
    x = x[keep]
    y = y[keep]
    if z is not None and len(z) == keep.size:
        z = z[keep]
    if weights is not None and len(weights) == keep.size:
        weights = weights[keep]
    return x, y, z, weights


def is_data_ready(ndxplorer: "NDXplorer") -> bool:
    """Whether there is data and the axes point at columns of it.

    A readiness check, and nothing else. It used to answer by *computing* the
    x, y and z values -- each of which re-derives the whole gating state -- so
    asking whether a redraw was possible cost most of a redraw, on every redraw.
    """
    try:
        data_source = ndxplorer.data_source
        if data_source is None or data_source.empty:
            return False
        n_parameters = data_source.n_parameters
        if n_parameters < 3:
            return False
        control = ndxplorer.plot_control
        return all(
            0 <= getattr(control, name, (default, ""))[0] < n_parameters
            for name, default in (("p1", 0), ("p2", 1), ("p3", 2))
        )
    except Exception:
        return False


def histogram_axes(ndxplorer: "NDXplorer") -> HistogramAxes:
    """What the plot controls are set to, as the axes a fill takes.

    One reading of the interface, producing one description. This used to
    return a dataclass *and* a dict of two dozen keys built from it, with five
    arrays of bin edges alongside; callers picked whichever of the three they
    happened to want, and the dict carried a second, disagreeing copy of the
    ranges (``z_range`` was hard-coded to ``(0, 50)`` here while the plot drew
    ``plot_control.z_range``).
    """
    control = ndxplorer.plot_control

    def axis(name: str, index: int, n_bins: int) -> Axis:
        lo, hi = getattr(control, name + "_range")
        return Axis(
            index=index,
            bins=n_bins,
            lo=lo,
            hi=hi,
            scale=getattr(control, "scale_" + name, "linear"),
            density=getattr(control, "normed_hist_" + name, False),
        )

    x_idx = getattr(control, "p1", (0, ""))[0]
    y_idx = getattr(control, "p2", (1, ""))[0]
    z_idx = getattr(control, "p3", (2, ""))[0]

    # The z marginal is computed whenever a third parameter is chosen, NOT only
    # when the dynamic gate is armed. Those are two different things and one
    # checkbox used to mean both: the box says "dynamic z-selection" -- whether
    # the z *range* gates the other plots -- and it also decided whether the z
    # histogram existed at all. Someone selecting bursts by a third parameter
    # therefore had to arm the gate before they could see the distribution they
    # were about to gate on, which is backwards: you look first, then choose the
    # range. One extra 1-D fill costs a few milliseconds.

    # The weight COLUMN, not a weight array. The fill reads it out of the store
    # like any other column, so it cannot end up describing a different set of
    # rows than the coordinates do -- which is what happened when it travelled
    # separately as an array.
    weight = None
    if hasattr(ndxplorer, "checkBoxWeight") and ndxplorer.checkBoxWeight.isChecked():
        name = ndxplorer.comboBoxWeight.currentText() if hasattr(ndxplorer, "comboBoxWeight") else ""
        try:
            weight = list(ndxplorer.data_source.parameter_names).index(name)
        except (ValueError, AttributeError):
            logging.warning("Weight parameter '%s' is not a column; not weighting.", name)

    return HistogramAxes(
        x=axis("x", x_idx, control.n_xhist_1d),
        y=axis("y", y_idx, control.n_yhist_1d),
        x2=axis("x", x_idx, control.n_xhist_2d),
        y2=axis("y", y_idx, control.n_yhist_2d),
        z=axis("z", z_idx, control.n_zhist_1d) if z_idx >= 0 else None,
        weight=weight,
    )


def keep_mask(ndxplorer: "NDXplorer") -> Optional[np.ndarray]:
    """The rows a redraw may use, or None for all of them.

    The mask itself, not the row numbers it contains. An index array only means
    anything alongside the array it indexes, and that is how a filtered weight
    array came to be indexed by a global row number.
    """
    mask = ndxplorer.value_mask
    return None if mask is None else ~mask

def z_axis_available(ndxplorer) -> bool:
    """Whether a usable third parameter is selected.

    The combo always answers with *something* — an editable combo box has a
    current index whatever the user has done — so "is a z parameter chosen" is
    really "does the chosen index address a column of this table". Without the
    second half a window whose data has fewer columns than the last one draws an
    empty marginal under a stale label.
    """
    control = getattr(ndxplorer, "plot_control", None)
    if control is None:
        return False
    try:
        index = control.p3[0]
    except Exception:
        return False
    if index is None or int(index) < 0:
        return False
    try:
        return int(index) < len(ndxplorer.data_source.parameter_names)
    except Exception:
        return True
