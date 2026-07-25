"""compute_histograms_sync must honour log-spaced bin edges.

A log-scaled axis builds its bins with np.logspace (get_x_bins/get_y_bins). The
main histogram path used to ignore those edges and re-bin uniformly from a
count+range, which crushed the data into the lowest bins and made the log 2D
image disagree with its log marginal. It must now bin on the provided edges.
"""
import numpy as np
import pytest

from ndxplorer.utils.histogram_computation import compute_histograms_sync


class _DS:
    def __init__(self, values):
        self.values = values


def _params(x_edges, y_edges):
    return dict(
        x_idx=0, y_idx=1, z_idx=None,
        x_bins=len(x_edges) - 1, y_bins=len(y_edges) - 1,
        x_bins_2d=len(x_edges) - 1, y_bins_2d=len(y_edges) - 1,
        x_range=(float(x_edges[0]), float(x_edges[-1])),
        y_range=(float(y_edges[0]), float(y_edges[-1])),
        z_range=(0, 1),
        x_bins_1d_arr=x_edges, y_bins_1d_arr=y_edges,
        x_bins_2d_arr=x_edges, y_bins_2d_arr=y_edges,
        z_bins_1d_arr=None,
    )


def test_log_edges_are_used_and_match_numpy():
    rng = np.random.default_rng(1)
    # random (not exactly on edges: boost and numpy differ on boundary bins)
    x = rng.uniform(1.0, 5.0, 4000)
    y = 10 ** rng.uniform(-2, 2, 4000)  # spans decades -> needs log Y
    ds = _DS(np.vstack([x, y]))

    x_edges = np.linspace(1.0, 5.0, 26)
    y_edges = np.logspace(-2, 2, 21)     # log-spaced Y
    r = compute_histograms_sync(ds, _params(x_edges, y_edges))

    H, xo, yo = r["2d"]
    # The returned Y edges are the log-spaced ones (evenly spaced in log10).
    d = np.diff(np.log10(yo))
    assert np.allclose(d, d[0]), "Y binning is not log-spaced"
    # Counts match numpy on the same log edges (orientation is (n_y, n_x)).
    Href, _, _ = np.histogram2d(x, y, bins=[x_edges, y_edges])
    assert np.allclose(H, Href.T)


def test_log_binning_is_not_crushed_into_lowest_bin():
    """With log Y, a distribution spread over decades occupies many Y bins."""
    rng = np.random.default_rng(2)
    x = rng.uniform(1, 5, 4000)
    y = 10 ** rng.uniform(-2, 2, 4000)
    ds = _DS(np.vstack([x, y]))

    y_log = np.logspace(-2, 2, 21)
    y_lin = np.linspace(0.01, 100, 21)
    x_edges = np.linspace(1, 5, 11)

    r_log = compute_histograms_sync(ds, _params(x_edges, y_log))
    r_lin = compute_histograms_sync(ds, _params(x_edges, y_lin))

    # Fraction of Y-marginal counts sitting in the single lowest bin.
    def lowest_frac(res):
        _, counts = res["y"]
        counts = np.asarray(counts, float)
        return counts[0] / counts.sum()

    # Linear bins pile almost everything into the first bin; log bins spread it.
    assert lowest_frac(r_lin) > 0.4
    assert lowest_frac(r_log) < 0.15


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-q"])
