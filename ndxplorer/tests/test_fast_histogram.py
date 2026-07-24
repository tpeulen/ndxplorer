"""Tests for the uniform-bin fast histogram helpers.

The fast path must produce counts bit-identical to NumPy across integer bins,
uniform edge arrays, weights, density normalisation, and the non-uniform
(log-spaced) fallback — otherwise the interactive display would silently diverge
from the reference implementation.
"""

from __future__ import annotations

import numpy as np
import pytest
from ndxplorer.utils.fast_histogram import fast_histogram_1d, fast_histogram_2d


@pytest.fixture
def rng():
    return np.random.default_rng(1234)


@pytest.mark.parametrize("n_bins", [2, 17, 50, 200])
@pytest.mark.parametrize("use_weights", [False, True])
def test_1d_int_bins_match_numpy(rng, n_bins, use_weights):
    data = rng.normal(size=50_000)
    # include exact edge points and out-of-range values
    data[:4] = [-4.0, 4.0, np.nan, np.inf]
    weights = rng.random(data.size) if use_weights else None
    lo, hi = -4.0, 4.0

    edges, counts = fast_histogram_1d(data, n_bins, weights=weights, data_range=(lo, hi))
    ref_counts, ref_edges = np.histogram(data, bins=n_bins, range=(lo, hi), weights=weights)

    np.testing.assert_allclose(edges, ref_edges)
    np.testing.assert_allclose(counts, ref_counts)


def test_1d_uniform_edge_array_match_numpy(rng):
    data = rng.normal(size=20_000)
    edges_in = np.linspace(-3, 3, 41)
    edges, counts = fast_histogram_1d(data, edges_in)
    ref_counts, _ = np.histogram(data, bins=edges_in)
    np.testing.assert_allclose(counts, ref_counts)


def test_1d_density_match_numpy(rng):
    data = rng.normal(size=20_000)
    edges, counts = fast_histogram_1d(data, 30, density=True, data_range=(-3, 3))
    ref_counts, _ = np.histogram(data, bins=30, range=(-3, 3), density=True)
    np.testing.assert_allclose(counts, ref_counts, rtol=1e-6)
    # A density histogram integrates to 1 over the in-range mass.
    assert np.isclose((counts * np.diff(edges)).sum(), 1.0, atol=1e-6)


def test_1d_log_bins_fall_back_to_numpy(rng):
    data = np.abs(rng.normal(size=10_000)) + 0.01
    log_edges = np.logspace(-1, 1, 25)
    _, counts = fast_histogram_1d(data, log_edges)
    ref_counts, _ = np.histogram(data, bins=log_edges)
    np.testing.assert_array_equal(counts, ref_counts)


@pytest.mark.parametrize("use_weights", [False, True])
def test_2d_match_numpy_and_orientation(rng, use_weights):
    x = rng.normal(size=40_000)
    y = rng.normal(size=40_000)
    x[:2] = [-3.0, 3.0]
    y[:2] = [-3.0, 3.0]
    weights = rng.random(x.size) if use_weights else None
    nx, ny = 60, 70  # deliberately different so orientation bugs surface

    H, xe, ye = fast_histogram_2d(
        x, y, [nx, ny], weights=weights, x_range=(-3, 3), y_range=(-3, 3)
    )
    ref_H, ref_xe, ref_ye = np.histogram2d(
        x, y, bins=[nx, ny], range=[(-3, 3), (-3, 3)], weights=weights
    )
    # fast_histogram_2d matches numpy's (nx, ny) orientation before any caller transpose.
    assert H.shape == (nx, ny)
    np.testing.assert_allclose(H, ref_H)
    np.testing.assert_allclose(xe, ref_xe)
    np.testing.assert_allclose(ye, ref_ye)


def test_2d_scalar_bins_applied_to_both_axes(rng):
    x = rng.normal(size=5_000)
    y = rng.normal(size=5_000)
    H, xe, ye = fast_histogram_2d(x, y, 20, x_range=(-3, 3), y_range=(-3, 3))
    assert H.shape == (20, 20)


def test_empty_input_is_safe():
    edges, counts = fast_histogram_1d(np.array([]), 10, data_range=(0, 1))
    assert counts.shape == (10,)
    assert counts.sum() == 0
    H, _, _ = fast_histogram_2d(
        np.array([]), np.array([]), [5, 5], x_range=(0, 1), y_range=(0, 1)
    )
    assert H.shape == (5, 5)
    assert H.sum() == 0
