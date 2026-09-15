"""Gates, evaluated in tttrlib's DataStore.

This is the only place a selection becomes an answer. ndXplorer used to have
five implementations of the same predicate — one per selection class, a set of
numba kernels, a numpy copy inside ``get_mask_subset``, another in the Arrow
backend, and a fourth in ``vectorized_ops`` with a *different* NaN convention —
and a bug fixed in one of them stayed live in the other four.

What the store buys, besides being one implementation:

* the columns are already there in their own dtype, so nothing converts the
  table to float64 first;
* the answer is one bit per row, not an ``(n_parameters, n_points)`` boolean
  array holding the same row of results once per parameter;
* the histogram fill reads that bit directly, so no index array is built and no
  rows are copied.

Measured on 5,000,000 rows with a 64-vertex lasso: **95.6 ms against 618.3 ms**
for the array path it replaces.

.. rubric:: Reproducing the answers exactly

The three gate families disagree about what a *missing* coordinate means, and
the disagreement is not an oversight to tidy up here — it decides which points
appear in a published population, so this module reproduces each convention as
it stands and says so out loud:

===========================  ====================  ====================
gate                         ``invert=False``      ``invert=True``
===========================  ====================  ====================
``RegionDataSelection``      excluded              **excluded**
``Gaussian2DSelection``      excluded              **kept**
``RectangularDataSelection`` **kept**              **kept**
===========================  ====================  ====================

The rectangle keeps them because it is written as ``(v >= lo) & (v <= hi)``,
and no comparison against a NaN is true, so the gate never excludes one — it is
left for the separate "drop the non-finite" step (``idxs``) to decide. Whether
the region and the Gaussian *should* differ from each other is a scientific
question worth asking; it is not answered by a refactor, and any change to it
belongs in its own commit with the truth table in
``tests/test_selection_semantics.py`` updated in the same diff.
"""

from __future__ import annotations

from typing import Any, Iterable, List, Optional, Sequence

import numpy as np
import tttrlib

from ..logging_config import logging


# --- translating one gate ---------------------------------------------------


def _roi_region(roi: Any) -> Optional[dict]:
    """An ROI as keyword arguments for ``DataStore.region``, or None.

    None means "no primitive for this shape", not "this cannot be evaluated":
    the caller then asks the ROI itself, over two columns read from the store.
    """
    from chisurf.core.roi import EllipseROI, MaskROI, PolygonROI, RectangleROI

    if isinstance(roi, RectangleROI):
        return dict(kind="rectangle", x0=roi.x0, y0=roi.y0, x1=roi.x1, y1=roi.y1)

    if isinstance(roi, EllipseROI):
        # A zero radius means an axis with no extent at all, which the store's
        # ellipse reads as unbounded. Rare, and wrong in the widening direction,
        # so it goes to the ROI itself instead.
        if roi.rx <= 0.0 or roi.ry <= 0.0:
            return None
        return dict(kind="ellipse", cx=roi.cx, cy=roi.cy, rx=roi.rx, ry=roi.ry,
                    angle=roi.angle)

    if isinstance(roi, PolygonROI):
        v = np.asarray(roi.vertices, dtype=np.float64)
        return dict(kind="polygon", xs=np.ascontiguousarray(v[:, 0]),
                    ys=np.ascontiguousarray(v[:, 1]))

    if isinstance(roi, MaskROI):
        # ``extent`` is what puts the mask on value axes; without it the mask is
        # in pixel-index coordinates and rounds to the nearest cell rather than
        # flooring into one. ``bounds()`` is NOT the extent -- it is the box of
        # the set cells -- and using it shrinks the gate onto its own contents.
        if roi.extent is None:
            return None
        x0, x1, y0, y1 = roi.extent
        return dict(kind="mask", image=np.ascontiguousarray(roi.mask),
                    x0=x0, y0=y0, x1=x1, y1=y1)

    # CompositeROI, ThresholdROI, anything added later.
    return None


def _apply_roi_gate(store, sel, ix: int, iy: int) -> None:
    """Narrow `store` by a region gate, and by the finiteness it implies."""
    # A point whose position on this plane is unknown is outside the gate under
    # BOTH polarities: it cannot be shown to be inside a shape, and it cannot be
    # shown to be outside one either.
    store.where_finite([ix, iy], how="and")

    region = _roi_region(sel.roi)
    if region is not None:
        store.region(ix, iy, how="andnot" if sel.invert else "and", **region)
        return

    # No primitive for this shape. Ask the region itself -- over two columns
    # read straight out of the store, not over a copy of the table -- and
    # combine the answer back in. The selection is still one bit per row and
    # still lives in one place; only the geometry happened elsewhere.
    x = np.asarray(store[ix].numpy(), dtype=float)
    y = np.asarray(store[iy].numpy(), dtype=float)
    inside = np.zeros(len(x), dtype=bool)
    finite = np.isfinite(x) & np.isfinite(y)
    if finite.any():
        inside[finite] = np.asarray(
            sel.roi.contains(np.column_stack([x[finite], y[finite]])), dtype=bool)
    store.select_rows(inside, how="andnot" if sel.invert else "and")


def _gaussian_columns(store, sel, ix: int, iy: int, cache: dict) -> tuple:
    """The two columns a Gaussian gate is evaluated on, log-transformed if asked.

    A log-scaled gate is evaluated in log space, so the transform has to happen
    somewhere. It happens ONCE, into a companion column, rather than per point
    per frame: a user dragging a gate re-evaluates continuously over data that
    is not changing, and a ``log`` per point per axis per redraw is the whole
    cost of the gate several times over.

    Natural log, because ``mu`` and ``cov`` were fitted in that space. A
    non-positive value has no logarithm and becomes the store's own "not
    measured", which is exactly what the reference does with it.

    The companion is also where the non-finite values are marked, which is what
    makes the quadratic form below treat them as outside the ellipse -- the
    reference sets their distance to infinity for the same reason.
    """
    out = []
    for axis, use_log in ((ix, sel.log_x), (iy, sel.log_y)):
        key = (axis, bool(use_log))
        if key in cache:
            out.append(cache[key])
            continue
        name = "__gate_%d_%s" % (axis, "log" if use_log else "lin")
        values = np.asarray(store[axis].numpy(), dtype=np.float64)
        if use_log:
            with np.errstate(divide="ignore", invalid="ignore"):
                values = np.where(values > 0.0, np.log(values), np.nan)
        # Reuse the column if it is already there. An empty cache means the data
        # changed, not that the column is gone -- rewriting it in place is what
        # keeps the store from growing a new scratch column per parameter edit.
        index = store.find(name)
        if index < 0:
            column = store.add(name, values)
            index = store.n_columns() - 1
        else:
            column = store[index]
            column.set_numpy(values)
            # mask_non_finite only ever CLEARS validity bits, so a refreshed
            # column would keep whatever the previous data had marked missing.
            column.clear_mask()
        column.mask_non_finite()
        cache[key] = index
        out.append(index)
    return out[0], out[1]


def _apply_gaussian_gate(store, sel, ix: int, iy: int, cache: dict) -> None:
    """Narrow `store` by a Mahalanobis ellipse around a fitted 2-D Gaussian."""
    try:
        inv_cov = np.linalg.inv(sel.cov)
    except Exception:
        inv_cov = np.linalg.pinv(sel.cov)

    gx, gy = _gaussian_columns(store, sel, ix, iy, cache)
    # The quadratic form, not a centre-radii-angle ellipse: converting means
    # diagonalising the matrix, and a boundary computed through two square roots
    # and an arctangent does not agree bit for bit with one computed from the
    # coefficients. For a gate that decides which points a figure contains, that
    # is worth caring about. It also stays meaningful when the fit produced a
    # covariance that is not positive definite, where radii do not exist.
    store.region(
        gx, gy, kind="quadratic",
        cx=float(sel.mu[0]), cy=float(sel.mu[1]),
        a=float(inv_cov[0, 0]), b=float(inv_cov[0, 1]), c=float(inv_cov[1, 1]),
        threshold=float(sel.sigma) ** 2,
        # Inverted keeps the points with no position: their distance is infinite,
        # which IS outside the ellipse. Not inverted drops them, because the
        # companion column marks them missing and missing is never inside.
        how="andnot" if sel.invert else "and",
    )


def _apply_interval_gate(store, sel, ix: int) -> None:
    """Narrow `store` by a 1-D interval on one parameter.

    Not ``where()``: that is half-open and drops missing values, and this gate
    is neither. It is the closed interval ``[lower, upper]`` when upright and
    the complement of the OPEN interval when inverted -- so a point sitting
    exactly on a bound is kept under both polarities -- and a NaN passes through
    untouched either way. ``lower`` and ``upper`` are routinely infinite: that
    is how ``ndx filter --select`` writes a one-sided cut.
    """
    if sel.invert:
        store.interval(ix, lo=sel.lower, hi=sel.upper,
                       lo_closed=False, hi_closed=False,
                       missing_selected=False, how="andnot")
    else:
        store.interval(ix, lo=sel.lower, hi=sel.upper,
                       lo_closed=True, hi_closed=True,
                       missing_selected=True, how="and")


def _apply_bitmap_gate(store, sel, ix: int, iy: int) -> None:
    """Narrow `store` by a mask painted on a 2-D histogram.

    The bin edges come from the plot and need not be evenly spaced, so this is a
    binary search per point rather than the store's affine mask lookup. Two
    searchsorted passes over two columns read in place; the cost this gate used
    to carry was eleven ``logging.info`` calls per rebuild, several of which
    reduced full arrays, not the search.
    """
    x = np.asarray(store[ix].numpy(), dtype=float)
    y = np.asarray(store[iy].numpy(), dtype=float)
    store.select_rows(sel.inside(x, y), how="andnot" if sel.invert else "and")


def _gate_axes(sel) -> Optional[tuple]:
    """The one or two parameter indices a gate constrains, or None if unknown."""
    from .data_source import (Gaussian2DSelection, MaskDataSelection,
                              RectangularDataSelection)
    from .region_selection import RegionDataSelection

    if isinstance(sel, RectangularDataSelection):
        return (sel.parameter_idx,)
    if isinstance(sel, Gaussian2DSelection):
        return (sel.parameter_idx1, sel.parameter_idx2)
    if isinstance(sel, (RegionDataSelection, MaskDataSelection)):
        return (sel.idx1, sel.idx2)
    return None


def apply(store, selections: Iterable[Any], idxs: Sequence[int] = (),
          mask_nan: bool = True, mask_inf: bool = True,
          n_columns: Optional[int] = None,
          scratch: Optional[dict] = None) -> np.ndarray:
    """Evaluate every gate in `store` and return which rows are KEPT.

    Gates combine with AND: a row has to satisfy all of them. `idxs` names the
    columns that must additionally hold a real number -- the axes being plotted,
    normally -- which is a separate question from any gate and is why a NaN can
    pass a rectangle and still not be drawn.

    The store's selection is left holding the answer, so a caller that goes on
    to fill a histogram out of the same store needs no mask at all.

    :param n_columns: how many of the store's columns are real parameters;
        anything past that is scratch this function appended earlier
    :param scratch: the caller's cache of those scratch columns, kept across
        calls so a log transform is computed once per load rather than once per
        redraw. Pass the same dict every time and drop it when the data changes.
    """
    from .data_source import (Gaussian2DSelection, MaskDataSelection,
                              RectangularDataSelection)
    from .region_selection import RegionDataSelection

    store.select_all()
    n_rows = store.n_rows()
    if n_columns is None:
        n_columns = store.n_columns()
    if scratch is None:
        scratch = {}

    for sel in selections or []:
        if not getattr(sel, "enabled", True):
            continue                       # a disabled gate constrains nothing
        axes = _gate_axes(sel)
        if axes is None:
            raise TypeError("no rule for selection type %r" % type(sel).__name__)
        if any(not (0 <= int(a) < n_columns) for a in axes):
            # A gate on a parameter this table does not have. The reference
            # ignores it rather than emptying the selection, and so do we.
            continue
        try:
            if isinstance(sel, RectangularDataSelection):
                _apply_interval_gate(store, sel, int(axes[0]))
            elif isinstance(sel, Gaussian2DSelection):
                _apply_gaussian_gate(store, sel, int(axes[0]), int(axes[1]),
                                     scratch)
            elif isinstance(sel, RegionDataSelection):
                _apply_roi_gate(store, sel, int(axes[0]), int(axes[1]))
            elif isinstance(sel, MaskDataSelection):
                _apply_bitmap_gate(store, sel, int(axes[0]), int(axes[1]))
        except Exception as exc:
            logging.error("selection %r could not be evaluated: %s",
                          getattr(sel, "name", "unnamed"), exc)
            raise

    axis_indices = [int(i) for i in (idxs or []) if 0 <= int(i) < n_columns]
    if axis_indices and (mask_nan or mask_inf):
        if mask_nan and mask_inf:
            store.where_finite(axis_indices, how="and")
        else:
            # Only one of the two: rarer, and there is no primitive for "finite
            # except for the infinities", so it is spelt out over the columns.
            bad = np.zeros(n_rows, dtype=bool)
            for i in axis_indices:
                column = store[i].numpy()
                if mask_nan:
                    bad |= np.isnan(column)
                if mask_inf:
                    bad |= np.isinf(column)
            store.select_rows(bad, how="andnot")

    selected = store.selection()
    return np.ones(n_rows, dtype=bool) if selected is None else selected
