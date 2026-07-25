"""Parity tests for the immediate histogram path's engine swap.

``_update_histograms_immediate`` was rewritten to compute on the shared
``fast_histogram_1d`` / ``fast_histogram_2d`` engine (the same one the
background ``compute_histograms_sync`` path uses) instead of a separate
NumPy-only ``HistogramManager``. These tests pin that the swap is
behaviour-preserving: for every case the immediate path builds — uniform bins,
log-spaced bins, weights, density — the new engine matches the old manager
output exactly, including the 2D (n_y, n_x) orientation Histogram2D stores.
"""

import numpy as np
import pytest

from ndxplorer.core.histograms import Histogram1D, Histogram2D
from ndxplorer.utils.fast_histogram import fast_histogram_1d, fast_histogram_2d
from ndxplorer.utils.histogram_manager import get_histogram_manager


@pytest.fixture
def rng():
    return np.random.default_rng(1234)


def _wrap_1d(data, edges, weights=None, density=False):
    """Reproduce the immediate path's new 1D wiring."""
    e, counts = fast_histogram_1d(data, edges, weights=weights, density=density)
    return Histogram1D(edges=e, counts=counts)


def _wrap_2d(x, y, x_edges, y_edges, weights=None):
    """Reproduce the immediate path's new 2D wiring (note the transpose)."""
    H, xe, ye = fast_histogram_2d(x, y, [x_edges, y_edges], weights=weights)
    return Histogram2D(H=H.T, x_edges=xe, y_edges=ye)


@pytest.mark.parametrize("density", [False, True])
@pytest.mark.parametrize("use_weights", [False, True])
def test_1d_uniform_matches_manager(rng, density, use_weights):
    data = rng.normal(5.0, 2.0, size=10_000)
    edges = np.linspace(-2.0, 12.0, 41)  # uniform → bincount fast path
    weights = rng.uniform(0.1, 2.0, size=data.size) if use_weights else None

    manager = get_histogram_manager()
    ref = manager.compute_histogram_1d(data, edges, weights=weights, density=density)
    got = _wrap_1d(data, edges, weights=weights, density=density)

    np.testing.assert_allclose(got.counts, ref.counts, rtol=0, atol=1e-9)
    np.testing.assert_allclose(got.edges, ref.edges)


def test_1d_log_bins_matches_manager(rng):
    data = rng.uniform(1.0, 1000.0, size=8_000)
    edges = np.logspace(0, 3, 31)  # non-uniform → NumPy fallback in both paths

    manager = get_histogram_manager()
    ref = manager.compute_histogram_1d(data, edges)
    got = _wrap_1d(data, edges)

    np.testing.assert_allclose(got.counts, ref.counts)
    np.testing.assert_allclose(got.edges, ref.edges)


@pytest.mark.parametrize("use_weights", [False, True])
def test_2d_orientation_and_counts_match_manager(rng, use_weights):
    x = rng.normal(0.0, 1.0, size=12_000)
    y = rng.normal(3.0, 0.5, size=12_000)
    x_edges = np.linspace(-4.0, 4.0, 25)
    y_edges = np.linspace(1.0, 5.0, 17)
    weights = rng.uniform(0.1, 2.0, size=x.size) if use_weights else None

    manager = get_histogram_manager()
    ref = manager.compute_histogram_2d(x, y, x_edges, y_edges, weights=weights)
    got = _wrap_2d(x, y, x_edges, y_edges, weights=weights)

    # Same (n_y, n_x) orientation and identical counts.
    assert got.H.shape == ref.H.shape
    np.testing.assert_allclose(got.H, ref.H, rtol=0, atol=1e-9)
    np.testing.assert_allclose(got.x_edges, ref.x_edges)
    np.testing.assert_allclose(got.y_edges, ref.y_edges)


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-q"])
