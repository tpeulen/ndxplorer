"""The array helpers behind the display ranges.

``fast_percentile_range`` sets the contrast of the 2-D map and the limits of the
axes. It trades ``np.percentile``'s interpolation for a partition, which is a
legitimate trade -- an order statistic is a percentile, just not an interpolated
one -- but it has to remain an order statistic. One branch did not: when both
percentiles landed on the same rank it read ``valid_data[index]`` out of the
**unsorted** array, returning whichever value happened to sit at that position.
That is not a percentile of anything, and it moves when the rows are reordered.
"""

from __future__ import annotations

import numpy as np
import pytest

from ndxplorer.utils.vectorized_ops import (batch_percentile, combine_masks_fast,
                                            compress_array,
                                            fast_minmax, fast_percentile_range,
                                            fast_sum_of_squares,
                                            fast_weighted_mean)


@pytest.fixture
def rng():
    return np.random.default_rng(20260805)


# --- percentile range --------------------------------------------------------


@pytest.mark.parametrize("n", [100, 1_000, 10_000])
@pytest.mark.parametrize("low, high", [(1.0, 99.0), (0.0, 100.0), (25.0, 75.0),
                                       (5.0, 95.0)])
def test_the_range_is_close_to_numpys_percentile(rng, n, low, high):
    """Not exact -- NumPy interpolates between ranks and this does not -- but
    the difference has to be a rank, not a bug."""
    data = rng.uniform(-10.0, 10.0, n)
    ours = fast_percentile_range(data, low, high)
    reference = (float(np.percentile(data, low)), float(np.percentile(data, high)))

    spread = data.max() - data.min()
    assert abs(ours[0] - reference[0]) < 0.01 * spread
    assert abs(ours[1] - reference[1]) < 0.01 * spread


@pytest.mark.parametrize("low, high", [(1.0, 1.9), (49.9, 50.1), (0.0, 0.4)])
def test_a_narrow_window_still_returns_an_order_statistic(rng, low, high):
    """When both percentiles round to the same rank, the answer must still be a
    ranked value -- so it cannot depend on the order of the rows."""
    data = rng.uniform(-10.0, 10.0, 7)
    forward = fast_percentile_range(data, low, high)
    reversed_rows = fast_percentile_range(data[::-1].copy(), low, high)
    shuffled = data.copy()
    rng.shuffle(shuffled)

    assert forward == reversed_rows
    assert forward == fast_percentile_range(shuffled, low, high)
    assert forward[0] in data


def test_the_range_is_ordered_and_inside_the_data(rng):
    data = rng.uniform(-10.0, 10.0, 500)
    low, high = fast_percentile_range(data, 1.0, 99.0)
    assert low <= high
    assert data.min() <= low and high <= data.max()


def test_the_full_range_is_the_extremes(rng):
    data = rng.uniform(-10.0, 10.0, 500)
    assert fast_percentile_range(data, 0.0, 100.0) == (float(data.min()),
                                                       float(data.max()))


def test_non_finite_values_do_not_reach_the_range():
    data = np.array([np.nan, -np.inf, 1.0, 2.0, 3.0, np.inf, np.nan])
    assert fast_percentile_range(data, 0.0, 100.0) == (1.0, 3.0)


def test_a_column_with_nothing_finite_falls_back(rng):
    assert fast_percentile_range(np.full(10, np.nan), 1.0, 99.0) == (0.0, 1.0)
    assert fast_percentile_range(np.array([]), 1.0, 99.0) == (0.0, 1.0)


def test_a_single_value_is_its_own_range():
    assert fast_percentile_range(np.array([4.0]), 1.0, 99.0) == (4.0, 4.0)


def test_a_constant_column_is_its_own_range():
    assert fast_percentile_range(np.full(200, 2.5), 1.0, 99.0) == (2.5, 2.5)


def test_the_mask_excludes_rather_than_keeps(rng):
    """ndXplorer's polarity throughout: ``True`` means the point is out."""
    data = np.array([0.0, 1.0, 2.0, 100.0, 200.0])
    excluded = np.array([False, False, False, True, True])
    assert fast_percentile_range(data, 0.0, 100.0, mask=excluded) == (0.0, 2.0)


# --- min/max -----------------------------------------------------------------


def test_minmax_skips_the_non_finite_values():
    data = np.array([np.nan, 5.0, -np.inf, -2.0, np.inf])
    assert fast_minmax(data) == (-2.0, 5.0)


def test_minmax_falls_back_on_an_unusable_column():
    assert fast_minmax(np.full(4, np.nan)) == (0.0, 1.0)
    assert fast_minmax(np.array([])) == (0.0, 1.0)


def test_minmax_honours_the_exclusion_mask():
    data = np.array([-100.0, 1.0, 2.0, 100.0])
    excluded = np.array([True, False, False, True])
    assert fast_minmax(data, mask=excluded) == (1.0, 2.0)




# --- masks -------------------------------------------------------------------


@pytest.mark.parametrize("operation, expected",
                         [("or", [True, True, True, False]),
                          ("and", [True, False, False, False]),
                          ("xor", [False, True, True, False])])
def test_masks_combine_by_the_named_operation(operation, expected):
    masks = [np.array([True, True, False, False]),
             np.array([True, False, True, False])]
    np.testing.assert_array_equal(combine_masks_fast(masks, operation), expected)


def test_combining_does_not_write_into_the_caller_s_mask():
    first = np.array([True, False])
    combine_masks_fast([first, np.array([False, True])], "or")
    np.testing.assert_array_equal(first, [True, False])


def test_combining_one_mask_returns_a_copy():
    only = np.array([True, False])
    result = combine_masks_fast([only], "or")
    result[0] = False
    assert only[0] is np.True_ or only[0] == True  # noqa: E712 - the point is it is unchanged


def test_combining_nothing_is_an_error():
    with pytest.raises(ValueError):
        combine_masks_fast([])
    with pytest.raises(ValueError):
        combine_masks_fast([np.array([True]), np.array([False])], "nand")


# --- the small reductions ----------------------------------------------------


def test_compressing_keeps_where_the_mask_is_true():
    data = np.arange(5.0)
    keep = np.array([True, False, True, False, True])
    np.testing.assert_array_equal(compress_array(data, keep), [0.0, 2.0, 4.0])


def test_compressing_a_parameter_table_works_along_the_points_axis():
    """A ``(n_parameters, n_points)`` table is narrowed in points, never in
    parameters."""
    table = np.arange(12.0).reshape(3, 4)
    keep = np.array([True, False, True, False])
    narrowed = compress_array(table, keep)
    assert narrowed.shape == (3, 2)
    np.testing.assert_array_equal(narrowed[0], [0.0, 2.0])


def test_the_sum_of_squares_is_the_sum_of_squares():
    data = np.array([[1.0, 2.0], [3.0, 4.0]])
    assert fast_sum_of_squares(data) == pytest.approx(30.0)


def test_a_weighted_mean_ignores_the_pairs_it_cannot_use():
    data = np.array([1.0, 2.0, np.nan, 4.0])
    weights = np.array([1.0, 1.0, 5.0, np.nan])
    assert fast_weighted_mean(data, weights) == pytest.approx(1.5)


def test_a_weighted_mean_of_nothing_is_zero_not_a_nan():
    assert fast_weighted_mean(np.array([np.nan]), np.array([1.0])) == 0.0
    assert fast_weighted_mean(np.array([1.0, 2.0]), np.zeros(2)) == 0.0


def test_batch_percentile_matches_numpy_per_array(rng):
    arrays = [rng.uniform(0, 1, 100), rng.uniform(-5, 5, 50), np.full(3, np.nan)]
    results = batch_percentile(arrays, 50.0)
    assert results[0] == pytest.approx(float(np.percentile(arrays[0], 50)))
    assert results[1] == pytest.approx(float(np.percentile(arrays[1], 50)))
    assert results[2] == 0.0
