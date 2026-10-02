"""What "Auto" ranges to.

A number on an axis is only meaningful together with the projection it was
written in; the auto-range had places where that pairing was dropped.
"""

from __future__ import annotations

import numpy as np
import pytest

from ndxplorer.utils import axis_helpers


def test_auto_range_leaves_out_a_runaway_tail():
    """One burst must not decide the axis for all the others.

    Measured on a real µs-ALEX burst table: photon counts with a 99.9th
    percentile of 1 108 and a single burst at 450 094. Auto-ranging to the
    maximum drew the whole distribution inside the first pixel.
    """
    rng = np.random.default_rng(0)
    values = np.concatenate([rng.gamma(3.0, 60.0, 20_000), [450_094.0]])

    low, high = axis_helpers.robust_axis_range(values)
    assert high < 0.05 * float(values.max()), "the outlier still sets the axis"
    assert high > float(np.percentile(values, 99.0))
    assert low <= float(np.percentile(values, 1.0))


def test_auto_range_does_not_trim_an_axis_that_has_no_outliers():
    """A clean axis auto-ranges to exactly its data, as it always did.

    Percentile-clipping unconditionally would quietly cut the ends off an
    efficiency running 0 to 1 — "Auto" would stop meaning "all of it" on the
    data where it was never broken.
    """
    values = np.linspace(0.0, 1.0, 5000)
    low, high = axis_helpers.robust_axis_range(values)
    assert (low, high) == (pytest.approx(0.0), pytest.approx(1.0))


def test_auto_range_survives_degenerate_input():
    """No data, one point, all-identical: a range, never an exception."""
    assert axis_helpers.robust_axis_range(np.array([])) == (0.0, 0.0)
    assert axis_helpers.robust_axis_range(np.array([7.0])) == (7.0, 7.0)
    assert axis_helpers.robust_axis_range(np.full(100, 3.0)) == (3.0, 3.0)


def test_auto_range_on_a_log_axis_ignores_non_positive_values():
    """Zeros cannot be shown on a log axis and must not set its minimum."""
    values = np.concatenate([np.zeros(500), np.geomspace(1.0, 1000.0, 5000)])
    low, _high = axis_helpers.robust_axis_range(values, scale="log")
    assert low > 0.0
