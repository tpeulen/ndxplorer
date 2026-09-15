"""The histogram engine against NumPy, over the cases a happy path never reaches.

``test_fast_histogram.py`` checks the engine on well-behaved normal samples.
That is the case that was never going to break. Every histogram bug this program
has had lived somewhere else:

* a value sitting exactly on the **top edge**, which NumPy puts in the last bin
  and a half-open engine drops -- and bin edges are routinely taken from the
  data's own maximum, so this is the *normal* case on a pixel axis, not a corner;
* **non-uniform bins**, which is what a log-scaled axis is, and which takes a
  different code path (a binary search rather than a multiply);
* **out-of-range** points, which must be dropped rather than piled into the end
  bins;
* **NaN and infinity**, which a fill loop can quietly bin as zero;
* **density**, whose normalisation is over the in-range mass only.

So this file is a cross product rather than a list of cases: three bin kinds x
seven datasets x weighted/unweighted x density/counts, each compared against
``numpy.histogram``.

Unweighted counts are compared **exactly**: they are integers, the two engines
put the same points in the same bins, and a tolerance there would hide the very
off-by-one-bin errors this file exists to catch. Weighted sums are compared to
floating-point tolerance instead, because the two accumulate the same weights in
a different order -- a genuine difference of ~1e-15 relative, and not one any
answer depends on.
"""

from __future__ import annotations

import numpy as np
import pytest

from ndxplorer.utils.fast_histogram import fast_histogram_1d, fast_histogram_2d

SEED = 20260805

LINEAR = np.linspace(0.0, 10.0, 21)
LOG = np.logspace(-1.0, 1.0, 21)              # non-uniform: the binary-search path
IRREGULAR = np.array([0.0, 0.5, 3.0, 3.1, 7.0, 10.0])

BIN_SETS = {"linear": LINEAR, "log": LOG, "irregular": IRREGULAR}


def _datasets():
    """Seven columns, each hostile in one specific way."""
    rng = np.random.default_rng(SEED)
    spread = rng.uniform(-2.0, 12.0, 500)     # a third of it out of range

    non_finite = spread.copy()
    non_finite[:20] = np.nan
    non_finite[20:30] = np.inf
    non_finite[30:35] = -np.inf

    return {
        "spread": spread,
        "non_finite": non_finite,
        # The top edge, several times over: NumPy's last bin is closed there.
        "on_the_top_edge": np.concatenate([spread, np.full(7, 10.0)]),
        # Sitting exactly on every interior boundary of every bin set.
        "on_the_boundaries": np.array([0.0, 10.0, 0.5, 3.0, 3.1, 7.0, 0.1, 1.0]),
        "constant": np.full(50, 3.0),
        "single": np.array([5.0]),
        "empty": np.array([]),
    }


DATASETS = _datasets()


@pytest.mark.parametrize("bin_name", sorted(BIN_SETS))
@pytest.mark.parametrize("data_name", sorted(DATASETS))
@pytest.mark.parametrize("weighted", [False, True])
def test_1d_counts_are_numpys(data_name, bin_name, weighted):
    data, bins = DATASETS[data_name], BIN_SETS[bin_name]
    weights = (np.random.default_rng(SEED).uniform(0.1, 3.0, data.size)
               if weighted else None)

    edges, counts = fast_histogram_1d(data, bins, weights=weights)
    reference, reference_edges = np.histogram(data, bins=bins, weights=weights)

    np.testing.assert_array_equal(edges, reference_edges)
    # Exact for counts; summation order for weights -- see the module docstring.
    np.testing.assert_allclose(counts, reference,
                               rtol=1e-12 if weighted else 0, atol=0)


@pytest.mark.parametrize("bin_name", sorted(BIN_SETS))
@pytest.mark.parametrize("data_name", sorted(set(DATASETS) - {"empty"}))
def test_1d_density_is_exactly_numpys(data_name, bin_name):
    data, bins = DATASETS[data_name], BIN_SETS[bin_name]
    _, counts = fast_histogram_1d(data, bins, density=True)
    reference, _ = np.histogram(data, bins=bins, density=True)
    np.testing.assert_allclose(counts, reference, rtol=1e-12, atol=0)


def test_1d_negative_weights_are_not_clipped():
    """A weight column is whatever the user pointed at; the engine must not
    quietly decide a negative one means zero."""
    data = DATASETS["spread"]
    weights = np.full(data.size, -1.0)
    _, counts = fast_histogram_1d(data, LINEAR, weights=weights)
    reference, _ = np.histogram(data, bins=LINEAR, weights=weights)
    np.testing.assert_allclose(counts, reference)
    assert counts.sum() < 0


def test_1d_the_topmost_point_is_counted_not_dropped():
    """Stated on its own because it is the one place NumPy is not half-open, and
    because losing it is invisible: one count out of a bin holding hundreds."""
    data = np.array([0.0, 5.0, 10.0])
    _, counts = fast_histogram_1d(data, np.linspace(0.0, 10.0, 11))
    assert counts.sum() == 3
    assert counts[-1] == 1


def test_1d_an_out_of_range_point_is_dropped_not_clamped():
    data = np.array([-100.0, 5.0, 100.0])
    _, counts = fast_histogram_1d(data, np.linspace(0.0, 10.0, 11))
    assert counts.sum() == 1
    assert counts[0] == 0 and counts[-1] == 0


# --- 2-D --------------------------------------------------------------------


def _pairs():
    rng = np.random.default_rng(SEED + 1)
    x = rng.uniform(-2.0, 12.0, 800)
    y = rng.uniform(-2.0, 12.0, 800)

    non_finite_x, non_finite_y = x.copy(), y.copy()
    non_finite_x[:10] = np.nan
    non_finite_y[5:15] = np.inf

    return {
        "spread": (x, y),
        "non_finite": (non_finite_x, non_finite_y),
        # On the top edge of x only, of y only, of both, and out of range.
        "on_the_top_edge": (np.concatenate([x, [10.0, 5.0, 10.0, 10.0]]),
                            np.concatenate([y, [5.0, 10.0, 10.0, -5.0]])),
    }


PAIRS = _pairs()
BIN_PAIRS = {
    "linear": (LINEAR, LINEAR),
    "log": (LOG, LOG),
    # Different lengths per axis, so a transpose cannot hide.
    "mixed": (LINEAR, IRREGULAR),
}


@pytest.mark.parametrize("bin_name", sorted(BIN_PAIRS))
@pytest.mark.parametrize("pair_name", sorted(PAIRS))
@pytest.mark.parametrize("weighted", [False, True])
def test_2d_counts_are_numpys(pair_name, bin_name, weighted):
    x, y = PAIRS[pair_name]
    x_bins, y_bins = BIN_PAIRS[bin_name]
    weights = (np.random.default_rng(SEED).uniform(0.1, 3.0, x.size)
               if weighted else None)

    H, x_edges, y_edges = fast_histogram_2d(x, y, [x_bins, y_bins], weights=weights)
    reference, reference_x, reference_y = np.histogram2d(
        x, y, bins=[x_bins, y_bins], weights=weights)

    assert H.shape == (x_bins.size - 1, y_bins.size - 1)
    np.testing.assert_array_equal(x_edges, reference_x)
    np.testing.assert_array_equal(y_edges, reference_y)
    np.testing.assert_allclose(H, reference,
                               rtol=1e-12 if weighted else 0, atol=0)


@pytest.mark.parametrize("bin_name", sorted(BIN_PAIRS))
@pytest.mark.parametrize("pair_name", sorted(PAIRS))
def test_2d_density_is_exactly_numpys(pair_name, bin_name):
    x, y = PAIRS[pair_name]
    x_bins, y_bins = BIN_PAIRS[bin_name]
    H, _, _ = fast_histogram_2d(x, y, [x_bins, y_bins], density=True)
    reference, _, _ = np.histogram2d(x, y, bins=[x_bins, y_bins], density=True)
    np.testing.assert_allclose(H, reference, rtol=1e-12, atol=0)


def test_2d_a_corner_point_is_counted_once_not_twice():
    """A point on the top edge of BOTH axes is repaired by both repairs if the
    two are applied independently."""
    x = np.array([10.0, 10.0, 5.0])
    y = np.array([10.0, 5.0, 10.0])
    H, _, _ = fast_histogram_2d(x, y, [np.linspace(0, 10, 11), np.linspace(0, 10, 11)])
    assert H.sum() == 3
    assert H[-1, -1] == 1


def test_2d_the_marginals_of_the_map_are_the_1d_histograms():
    """The marginals are drawn beside the map and are expected to be its
    projections; if the two engines disagree the picture does not add up."""
    x, y = PAIRS["spread"]
    H, _, _ = fast_histogram_2d(x, y, [LINEAR, LINEAR])

    # Restricted to the rows the map can show -- a point off the y range is in
    # the x marginal but not in the map.
    inside = (y >= LINEAR[0]) & (y <= LINEAR[-1])
    _, x_counts = fast_histogram_1d(x[inside], LINEAR)
    np.testing.assert_allclose(H.sum(axis=1), x_counts)


def test_2d_an_empty_column_gives_an_empty_map_not_an_error():
    H, x_edges, y_edges = fast_histogram_2d(
        np.array([]), np.array([]), [LINEAR, LOG])
    assert H.shape == (LINEAR.size - 1, LOG.size - 1)
    assert H.sum() == 0
