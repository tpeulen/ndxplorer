"""The marginals describe the population the 2D map shows — and nothing wider.

A column that is defined for every burst (a proximity ratio) plotted against one
defined for a few (a per-state lifetime) used to draw a full-height marginal next
to a nearly empty map: each 1D histogram dropped only the NaNs of its own column.
:func:`~ndxplorer.utils.histogram_helpers.apply_joint_axis_mask` is the one seam
that keeps every histogram on the same rows.

The percentile test pins the crash this was found with: ``currentIndexChanged``
delivers the combo box index, and bound straight to ``update_spinbox_limits`` it
arrived as ``low_pct`` — silently skewing the contrast below index 100 and
raising ``Percentiles must be in the range [0, 100]`` above it.
"""

from __future__ import annotations

import inspect

import numpy as np
import pytest

from ndxplorer.utils.histogram_helpers import (
    apply_joint_axis_mask,
    joint_axis_mask,
)


@pytest.fixture
def columns():
    """x defined for the last 4 of 10 rows, y defined throughout."""
    x = np.full(10, np.nan)
    x[6:] = [1.0, 2.0, 3.0, 4.0]
    y = np.arange(10, dtype=float)
    return x, y


def test_the_mask_keeps_only_rows_with_both_axes(columns):
    x, y = columns
    keep = joint_axis_mask(x, y)

    assert keep is not None
    assert keep.tolist() == [False] * 6 + [True] * 4


def test_a_fully_defined_pair_costs_nothing(columns):
    _, y = columns
    assert joint_axis_mask(y, y) is None, "no mask means no copies on the hot path"


def test_infinities_count_as_missing():
    x = np.array([1.0, np.inf, 3.0])
    y = np.array([1.0, 2.0, -np.inf])
    assert joint_axis_mask(x, y).tolist() == [True, False, False]


def test_integer_columns_are_always_usable():
    x = np.arange(5)
    y = np.arange(5)
    assert joint_axis_mask(x, y) is None


def test_the_y_marginal_loses_the_bursts_the_map_cannot_show(columns):
    x, y = columns
    weights = np.ones(10)

    xs, ys, zs, ws = apply_joint_axis_mask(x, y, None, weights)

    assert len(xs) == len(ys) == len(ws) == 4
    assert zs is None
    # The y values that survive are exactly those of rows with an x value.
    assert ys.tolist() == [6.0, 7.0, 8.0, 9.0]

    # And that is precisely what the 2D histogram of the unfiltered pair holds.
    joint, _, _ = np.histogram2d(x[6:], y[6:], bins=[4, 4])
    assert joint.sum() == len(xs)


def test_z_travels_with_x_and_y(columns):
    x, y = columns
    z = np.arange(10, dtype=float) * 2

    _, _, zs, _ = apply_joint_axis_mask(x, y, z, None)
    assert zs.tolist() == [12.0, 14.0, 16.0, 18.0]


def test_mismatched_lengths_are_left_alone():
    x = np.array([1.0, np.nan, 3.0])
    y = np.array([1.0, 2.0])
    assert apply_joint_axis_mask(x, y) == (x, y, None, None)


def test_percentile_bounds_cannot_be_bound_positionally():
    """A Qt signal argument must not be able to land in ``low_pct``."""
    from ndxplorer.core.plot_main import NDXplorer
    from ndxplorer.plotting import plot_update_helpers

    for func in (NDXplorer.update_spinbox_limits, plot_update_helpers.update_spinbox_limits):
        params = inspect.signature(func).parameters
        for name in ("low_pct", "high_pct"):
            assert params[name].kind is inspect.Parameter.KEYWORD_ONLY, (
                f"{func.__qualname__}.{name} must be keyword-only"
            )

    # The slot the combo boxes are connected to takes (and drops) the index.
    slot = inspect.signature(NDXplorer.on_axis_selection_changed).parameters
    assert "_index" in slot


def test_both_1d_histogram_representations_are_understood():
    """The immediate path stores a dataclass, the worker a tuple."""
    from ndxplorer.core.histograms import Histogram1D
    from ndxplorer.plotting.plot_update_helpers import _as_edges_counts

    edges = np.array([0.0, 1.0, 2.0])
    counts = np.array([3.0, 4.0])

    for stored in (Histogram1D(edges=edges, counts=counts), (edges, counts)):
        got = _as_edges_counts(stored)
        assert got is not None
        assert np.array_equal(got[0], edges) and np.array_equal(got[1], counts)

    assert _as_edges_counts(None) is None
    assert _as_edges_counts(()) is None
