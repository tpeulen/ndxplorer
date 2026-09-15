"""What every gate means, written out as a truth table.

The selection path used to have five implementations of one predicate, and they
did not agree: the numba kernels excluded a NaN inside a rectangle, the
selection classes kept it, ``vectorized_ops`` excluded it under both polarities,
and ``get_mask_subset`` did not handle a drawn region at all -- so a lasso showed
in the table, was honoured by the export, and changed nothing on the plot.

There is one implementation now, in the store. This file is what keeps it
honest, and it is deliberately built the awkward way round:

* the **reference** is each selection class's own ``get_mask``, in numpy, which
  predates every optimisation and is what the published results were produced
  with;
* the comparison is **exact**. Not "within a few points" -- the one place a
  tolerance is defensible is a polygon against a different polygon algorithm,
  and there is no such comparison here;
* the coverage is a **cross product**, not a happy path. Every earlier bug hid
  in a case the fixtures happened to avoid: a square mask cannot show a
  transpose, coordinates in ``[0, 1)`` cannot show a truncation, a single gate
  cannot show a bad combination, and a fixture with no NaN cannot show any of
  the three non-finite conventions.
"""

import numpy as np
import pandas as pd
import pytest

from ndxplorer.core.data_source import (DataSource, Gaussian2DSelection,
                                        MaskDataSelection,
                                        RectangularDataSelection)
from ndxplorer.core.region_selection import RegionDataSelection

roi = pytest.importorskip("chisurf.core.roi", reason="chisurf is not importable")
EllipseROI, MaskROI = roi.EllipseROI, roi.MaskROI
PolygonROI, RectangleROI = roi.PolygonROI, roi.RectangleROI


N = 4000


@pytest.fixture(scope="module")
def source():
    """A table carrying every value a gate has to have an opinion about."""
    rng = np.random.default_rng(20260805)
    a = rng.uniform(-1.0, 2.0, N)
    b = rng.uniform(-1.0, 2.0, N)
    c = rng.uniform(0.001, 5.0, N)          # strictly positive, for a log gate
    # Values exactly on the bounds the gates below use, so the open/closed
    # question is actually asked.
    a[:8] = [0.0, 1.0, 0.0, 1.0, -1.0, 2.0, 0.5, 0.5]
    b[:8] = [0.0, 1.0, 1.0, 0.0, 0.5, 0.5, 0.0, 1.0]
    # ... and every kind of missing.
    a[10:20] = np.nan
    b[20:30] = np.inf
    a[30:35] = -np.inf
    c[35:40] = 0.0                           # no logarithm
    c[40:45] = np.nan
    return DataSource(data=pd.DataFrame({"a": a, "b": b, "c": c}))


def reference(source, selections, idxs=None, mask_nan=True, mask_inf=True):
    """The answer the numpy selection classes give. True means EXCLUDED."""
    values = source.values
    n_param, n_points = values.shape
    mask = np.zeros((n_param, n_points), dtype=bool)
    for sel in selections:
        mask |= sel.get_mask(values)
    if idxs:
        valid = np.array([i for i in idxs if 0 <= i < n_param], dtype=int)
        if valid.size:
            cols = values[valid, :]
            bad = np.zeros(n_points, dtype=bool)
            if mask_nan:
                bad |= np.any(np.isnan(cols), axis=0)
            if mask_inf:
                bad |= np.any(np.isinf(cols), axis=0)
            mask[:, bad] = True
    return mask


def assert_agrees(source, selections, idxs=None, mask_nan=True, mask_inf=True):
    """``get_mask``, ``get_mask_subset`` and the reference, all three the same."""
    expected = reference(source, selections, idxs, mask_nan, mask_inf)[0]

    got = np.asarray(source.get_mask(selections, idxs=idxs,
                                     mask_nan=mask_nan, mask_inf=mask_inf))
    assert got.shape == (source.n_parameters, N)
    np.testing.assert_array_equal(got[0], expected)
    # Every parameter row holds the same answer; that is the contract the export
    # callers read, and it is a broadcast rather than a copy.
    np.testing.assert_array_equal(got[-1], expected)

    subset = source.get_mask_subset(selections, list(idxs or []),
                                    mask_nan=mask_nan, mask_inf=mask_inf)
    assert subset.shape == (N,)
    np.testing.assert_array_equal(subset, expected)

    np.testing.assert_array_equal(
        source.selection_mask(selections, idxs=idxs,
                              mask_nan=mask_nan, mask_inf=mask_inf),
        ~expected)


COV = np.array([[0.30, 0.12], [0.12, 0.55]])


def gates(kind, invert):
    """One gate of each kind, on the same plane, so they can be compared."""
    if kind == "interval":
        return RectangularDataSelection(0, 0.0, 1.0, invert=invert)
    if kind == "interval-open":
        return RectangularDataSelection(0, -np.inf, np.inf, invert=invert)
    if kind == "gaussian":
        return Gaussian2DSelection(0, 1, [0.5, 0.5], COV, 1.5, invert=invert)
    if kind == "gaussian-log":
        return Gaussian2DSelection(2, 1, [0.0, 0.5], COV, 1.5, invert=invert,
                                   log_x=True)
    if kind == "roi-rectangle":
        return RegionDataSelection(RectangleROI(0.0, 0.0, 1.0, 1.0), 0, 1,
                                   invert=invert)
    if kind == "roi-ellipse":
        return RegionDataSelection(EllipseROI(0.5, 0.5, 0.4, 0.2), 0, 1,
                                   invert=invert)
    if kind == "roi-ellipse-rotated":
        return RegionDataSelection(EllipseROI(0.5, 0.5, 0.4, 0.2, 0.7), 0, 1,
                                   invert=invert)
    if kind == "roi-polygon":
        t = np.linspace(0.0, 2.0 * np.pi, 40, endpoint=False)
        v = np.column_stack([0.5 + 0.6 * np.cos(t) + 0.1 * np.cos(5 * t),
                             0.5 + 0.5 * np.sin(t) + 0.1 * np.sin(4 * t)])
        return RegionDataSelection(PolygonROI(v), 0, 1, invert=invert)
    if kind == "roi-mask":
        # NOT square, and on an extent that starts left of and below zero: a
        # square mask cannot show a transposed lookup, and an extent at the
        # origin cannot show an index truncated towards zero instead of floored.
        rng = np.random.default_rng(7)
        image = rng.random((17, 43)) < 0.35
        return RegionDataSelection(
            MaskROI(image, extent=(-1.0, 2.0, -1.0, 2.0)), 0, 1, invert=invert)
    if kind == "bitmap":
        rng = np.random.default_rng(8)
        return MaskDataSelection(0, 1, rng.random((24, 32)) < 0.4,
                                 np.linspace(-1.0, 2.0, 33),
                                 np.linspace(-1.0, 2.0, 25), invert=invert)
    if kind == "bitmap-log-edges":
        # The bin edges come from the plot, and a log axis makes them geometric.
        rng = np.random.default_rng(9)
        return MaskDataSelection(2, 1, rng.random((24, 32)) < 0.4,
                                 np.geomspace(0.001, 5.0, 33),
                                 np.linspace(-1.0, 2.0, 25), invert=invert)
    raise AssertionError(kind)


ALL_KINDS = [
    "interval", "interval-open", "gaussian", "gaussian-log",
    "roi-rectangle", "roi-ellipse", "roi-ellipse-rotated", "roi-polygon",
    "roi-mask", "bitmap", "bitmap-log-edges",
]


@pytest.mark.parametrize("kind", ALL_KINDS)
@pytest.mark.parametrize("invert", [False, True])
def test_one_gate(source, kind, invert):
    assert_agrees(source, [gates(kind, invert)])


@pytest.mark.parametrize("kind", ALL_KINDS)
@pytest.mark.parametrize("invert", [False, True])
def test_one_gate_with_axis_finiteness(source, kind, invert):
    """The gate and the "these axes must have a value" rule are separate
    questions, which is how a NaN can pass a rectangle and still not be drawn."""
    assert_agrees(source, [gates(kind, invert)], idxs=[0, 1])


@pytest.mark.parametrize("kind", ALL_KINDS)
def test_a_disabled_gate_constrains_nothing(source, kind):
    sel = gates(kind, False)
    sel.enabled = False
    assert_agrees(source, [sel])


@pytest.mark.parametrize("first", ALL_KINDS)
def test_three_gates_of_mixed_kinds(source, first):
    """A second gate is where a "combine" bug lives, and a third is where an
    inverted one that is not first lives."""
    assert_agrees(source, [
        gates(first, False),
        gates("gaussian", False),
        gates("roi-rectangle", True),
    ], idxs=[0, 1])


def test_no_gates_at_all(source):
    assert_agrees(source, [])
    assert np.all(source.selection_mask([]))


def test_no_gates_but_axes_must_be_finite(source):
    assert_agrees(source, [], idxs=[0, 1, 2])


@pytest.mark.parametrize("mask_nan,mask_inf", [(True, False), (False, True),
                                               (False, False)])
def test_nan_and_inf_are_separate_switches(source, mask_nan, mask_inf):
    assert_agrees(source, [gates("interval", False)], idxs=[0, 1],
                  mask_nan=mask_nan, mask_inf=mask_inf)


def test_a_gate_on_a_column_the_table_does_not_have(source):
    """Ignored, not fatal, and not an empty selection: a gate saved against a
    wider table has to survive being reloaded against a narrower one."""
    assert_agrees(source, [RectangularDataSelection(99, 0.0, 1.0)])


def test_an_empty_table():
    empty = DataSource(data=pd.DataFrame({"a": [], "b": []}))
    assert empty.selection_mask([gates("interval", False)]).shape == (0,)


def test_a_single_row():
    one = DataSource(data=pd.DataFrame({"a": [0.5], "b": [0.5]}))
    keep = one.selection_mask([RectangularDataSelection(0, 0.0, 1.0)])
    assert keep.tolist() == [True]


# --- the specific things that were wrong ------------------------------------


def test_an_inverted_interval_keeps_the_points_on_its_bounds(source):
    """``invert`` masks the OPEN interval, so a point exactly on a bound is kept
    under both polarities. Mapping this onto a half-open range would drop it."""
    sel = RectangularDataSelection(0, 0.0, 1.0, invert=True)
    keep = source.selection_mask([sel])
    values = source.values[0]
    on_bound = (values == 0.0) | (values == 1.0)
    assert on_bound.any(), "the fixture stopped exercising the bounds"
    assert np.all(keep[on_bound])


def test_an_interval_keeps_a_nan_and_a_region_does_not(source):
    """The two conventions that coexist, pinned so a later change to either is a
    decision rather than a side effect.

    NaN specifically, not "non-finite": an infinity is a real comparison and
    ``-inf < -1e9`` puts it outside the gate, exactly as the arithmetic says.
    Only a NaN makes both comparisons false and so passes through untouched.
    """
    nan = np.isnan(source.values[0])
    infinite = np.isinf(source.values[0])
    assert nan.any() and infinite.any()

    kept_by_interval = source.selection_mask(
        [RectangularDataSelection(0, -1e9, 1e9)])
    assert np.all(kept_by_interval[nan])
    assert not np.any(kept_by_interval[infinite])

    for invert in (False, True):
        kept_by_region = source.selection_mask(
            [RegionDataSelection(RectangleROI(-1e9, -1e9, 1e9, 1e9), 0, 1,
                                 invert=invert)])
        assert not np.any(kept_by_region[nan | infinite])


def test_an_inverted_gaussian_keeps_a_missing_value(source):
    """A point with no position has infinite Mahalanobis distance, which IS
    outside the ellipse -- the reference says so and this has to match it."""
    missing = ~np.isfinite(source.values[0])
    keep = source.selection_mask([gates("gaussian", True)])
    assert np.all(keep[missing])


def test_a_log_gate_drops_a_non_positive_value(source):
    """There is no logarithm of zero, and the gate is defined in log space."""
    zeros = source.values[2] == 0.0
    assert zeros.any()
    assert not np.any(source.selection_mask([gates("gaussian-log", False)])[zeros])


def test_a_failed_gate_does_not_leave_a_half_applied_selection(source):
    """A gate that raises must not leave the store holding an answer nobody
    asked for -- a caller that catches the exception has no way to know."""
    before = source.selection_mask([gates("interval", False)])

    class Broken(RectangularDataSelection):
        @property
        def lower(self):
            raise RuntimeError("boom")

        @lower.setter
        def lower(self, value):
            pass

    with pytest.raises(RuntimeError):
        source.selection_mask([gates("interval", False), Broken(0, 0.0, 1.0)])
    np.testing.assert_array_equal(
        source.selection_mask([gates("interval", False)]), before)


def test_the_store_is_not_left_holding_scratch_columns(source):
    """A log gate needs a transformed column. It is computed once and reused,
    not appended again on every redraw, and it never becomes a parameter."""
    before = source.n_parameters
    for _ in range(5):
        source.selection_mask([gates("gaussian-log", False)])
    assert source.n_parameters == before
    assert source.values.shape[0] == before


def test_the_mask_is_a_view_not_a_copy(source):
    mask = source.get_mask([gates("interval", False)])
    assert mask.base is not None, "get_mask should broadcast, not tile"
