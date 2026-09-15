"""A log-scaled axis must bin logarithmically.

The main histogram path used to bin uniformly whatever the axis was set to,
which crushed the data into the lowest bins and made the log 2D image disagree
with its log marginal.

An axis now says how it is spaced -- ``Axis(scale="log")`` -- rather than the
caller handing over an array of edges it built. The array form used to be
honoured as well, and working out which of the two a call meant is what the
fill spent its branches on. A log axis is a formula; saying so is also what
lets the fill bin with a multiply and a logarithm instead of a binary search.
"""
import numpy as np
import pytest

import pandas as pd

from ndxplorer.core.data_source import DataSource
from ndxplorer.utils.histogram_computation import (
    Axis, HistogramAxes, compute_histograms)


def _DS(values):
    """A real DataSource, not a stub with a ``values`` attribute.

    The histogram path reads single columns out of the store rather than the
    whole table, so a double that only has ``values`` no longer stands in for
    one -- and a double that diverges from the thing it doubles is how a test
    keeps passing after the code it covers has changed underneath it.
    """
    return DataSource(data=pd.DataFrame(
        {f"p{i}": row for i, row in enumerate(np.asarray(values, dtype=float))}))


def _axes(x_bins, x_range, y_bins, y_range, y_scale="linear"):
    x = Axis(index=0, bins=x_bins, lo=x_range[0], hi=x_range[1])
    y = Axis(index=1, bins=y_bins, lo=y_range[0], hi=y_range[1], scale=y_scale)
    return HistogramAxes(x=x, y=y, x2=x, y2=y)


def test_log_edges_are_used_and_match_numpy():
    rng = np.random.default_rng(1)
    # random (not exactly on edges: boost and numpy differ on boundary bins)
    x = rng.uniform(1.0, 5.0, 4000)
    y = 10 ** rng.uniform(-2, 2, 4000)  # spans decades -> needs log Y
    ds = _DS(np.vstack([x, y]))

    r = compute_histograms(ds, _axes(25, (1.0, 5.0), 20, (1e-2, 1e2), "log"))

    H, xo, yo = r["2d"]
    # The Y edges are log-spaced (evenly spaced in log10).
    d = np.diff(np.log10(yo))
    assert np.allclose(d, d[0]), "Y binning is not log-spaced"
    # Counts match numpy on the same log edges (orientation is (n_y, n_x)).
    Href, _, _ = np.histogram2d(
        x, y, bins=[np.linspace(1.0, 5.0, 26), np.logspace(-2, 2, 21)])
    assert np.allclose(H, Href.T)


def test_log_binning_is_not_crushed_into_lowest_bin():
    """With log Y, a distribution spread over decades occupies many Y bins."""
    rng = np.random.default_rng(2)
    x = rng.uniform(1, 5, 4000)
    y = 10 ** rng.uniform(-2, 2, 4000)
    ds = _DS(np.vstack([x, y]))

    r_log = compute_histograms(ds, _axes(10, (1, 5), 20, (1e-2, 1e2), "log"))
    r_lin = compute_histograms(ds, _axes(10, (1, 5), 20, (0.01, 100), "linear"))

    # Fraction of Y-marginal counts sitting in the single lowest bin.
    def lowest_frac(res):
        _, counts = res["y"]
        counts = np.asarray(counts, float)
        return counts[0] / counts.sum()

    # Linear bins pile almost everything into the first bin; log bins spread it.
    assert lowest_frac(r_lin) > 0.4
    assert lowest_frac(r_log) < 0.15


def test_a_log_axis_below_zero_bins_the_way_it_is_drawn():
    """``scale="log"`` with a non-positive lower bound falls back to linear.

    A geometric axis has no bin below zero to put anything in. The plot draws
    such an axis linear, so the fill has to bin it linear too -- binning
    against a different picture than the one on screen is the failure this
    whole module is about.
    """
    axis = Axis(index=0, bins=10, lo=-1.0, hi=10.0, scale="log")
    assert axis.scale == "linear"
    assert np.allclose(axis.edges, np.linspace(-1.0, 10.0, 11))


def test_an_axis_is_bins_plus_one_edges():
    """n bins need n + 1 edges, on both spacings."""
    assert Axis(index=0, bins=256, lo=0.0, hi=256.0).edges.size == 257
    assert Axis(index=0, bins=6, lo=1.0, hi=1000.0, scale="log").edges.size == 7


def test_a_constant_column_still_has_a_bin():
    """An empty interval -- a parameter that was never fit -- gets widened."""
    axis = Axis(index=0, bins=10, lo=3.0, hi=3.0)
    assert axis.lo < axis.hi
    assert np.all(np.diff(axis.edges) > 0)


def test_the_marginal_is_the_map_only_when_the_bins_agree():
    """``same_bins_as`` is what decides whether a marginal is summed out.

    It compares four numbers rather than two edge arrays, and it has to say
    "no" whenever the 1-D and 2-D settings differ -- otherwise a marginal is
    summed from a map binned differently from it.
    """
    a = Axis(index=0, bins=50, lo=0.0, hi=1.0)
    assert a.same_bins_as(Axis(index=0, bins=50, lo=0.0, hi=1.0))
    assert not a.same_bins_as(Axis(index=0, bins=51, lo=0.0, hi=1.0))
    assert not a.same_bins_as(Axis(index=0, bins=50, lo=0.0, hi=2.0))
    # The case a (count, first, last) key used to miss entirely.
    b = Axis(index=0, bins=50, lo=1.0, hi=100.0)
    assert not b.same_bins_as(Axis(index=0, bins=50, lo=1.0, hi=100.0, scale="log"))


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-q"])
