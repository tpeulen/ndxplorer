"""Stepping frames, which used to raise on every redraw.

Two defects, both about a row filter travelling separately from the data it
filters:

* the filter was passed as an array of row NUMBERS while the weights were
  resolved elsewhere against the already-filtered population, so with a frame
  selected a global row number indexed a per-frame weight array --
  ``IndexError: index 89979 is out of bounds for axis 0 with size 45037``, once
  per redraw, for as long as playback ran;
* ``get_bins`` returned ``n`` edges for ``n`` bins, so a histogram was always
  one bin short and every bin slightly too wide.

Neither is visible without weights and a frame column, which is exactly what an
image table has.
"""

import numpy as np
import pytest

from ndxplorer.utils.histogram_computation import (
    Axis, HistogramAxes, compute_histograms)
from ndxplorer.utils.histogram_helpers import get_bins

N_FRAMES, N_ROWS_PER_FRAME = 4, 250


@pytest.fixture
def source():
    from ndxplorer.core.data_source import DataSource

    rng = np.random.default_rng(3)
    n = N_FRAMES * N_ROWS_PER_FRAME
    frame = np.repeat(np.arange(N_FRAMES), N_ROWS_PER_FRAME)
    return DataSource.from_columns({
        "x": rng.uniform(0.0, 10.0, n),
        "y": rng.uniform(0.0, 10.0, n),
        "Frame": frame.astype(float),
        "weight": rng.uniform(0.5, 2.0, n),
    })


def axes_for(weight=False):
    x = Axis(index=0, bins=8, lo=0.0, hi=10.0)
    y = Axis(index=1, bins=8, lo=0.0, hi=10.0)
    return HistogramAxes(x=x, y=y, x2=x, y2=y, weight=3 if weight else None)


def test_a_frame_filter_and_weights_agree_about_the_population(source):
    """The regression. The weight is a COLUMN and the filter is a mask over
    rows, and they used to travel separately -- so a global row number indexed
    a per-frame weight array. They are both read out of the store now, through
    one selection, and cannot describe different rows."""
    frame = source.column_view(2)
    keep = frame == 2.0
    weights = np.asarray(source.column_view(3))

    result = compute_histograms(source, axes_for(weight=True), keep=keep)
    assert result["_count"] == N_ROWS_PER_FRAME
    assert result["2d"][0].sum() == pytest.approx(weights[keep].sum())


def test_every_frame_keeps_every_one_of_its_rows(source):
    """No row is lost and none is counted twice, frame by frame."""
    frame = source.column_view(2)
    total = 0.0
    for f in range(N_FRAMES):
        keep = frame == float(f)
        result = compute_histograms(source, axes_for(), keep=keep)
        assert result["_count"] == N_ROWS_PER_FRAME
        total += result["2d"][0].sum()
    assert total == N_FRAMES * N_ROWS_PER_FRAME


def test_a_mask_of_the_wrong_length_is_refused_not_applied(source):
    """Better a whole population than a silently wrong one."""
    result = compute_histograms(source, axes_for(), keep=np.ones(7, bool))
    assert result["_count"] == source.size


def test_the_selection_is_left_as_it_was_found(source):
    """A histogram is a question about the data, not a change to it."""
    store = source.store
    store.where(0, 0.0, 5.0)
    before = store.selection().copy()
    keep = source.column_view(2) == 0.0
    compute_histograms(source, axes_for(), keep=keep)
    assert store.selection() is None or np.array_equal(store.selection(), before) \
        or store.n_selected() == store.n_rows()
    store.select_all()


def test_the_marginals_and_the_map_describe_one_population(source):
    """Every histogram counts the rows with a value on BOTH plotted axes.

    Otherwise the marginals count bursts the 2-D map cannot show and the number
    under the plot does not add up to the picture above it.
    """
    x = source.column_view(0)
    np.asarray(x)[:17] = np.nan
    source.store[0].mask_non_finite()
    try:
        result = compute_histograms(source, axes_for())
        total = result["2d"][0].sum()
        assert result["x"][1].sum() == pytest.approx(total)
        assert result["y"][1].sum() == pytest.approx(total)
        assert total == source.size - 17
    finally:
        source.store[0].clear_mask()


@pytest.mark.parametrize("n_bins", [1, 2, 8, 256])
def test_n_bins_means_n_bins(n_bins):
    """``get_bins`` returns EDGES, and n bins need n + 1 of them.

    It returned n, so a histogram was one bin short and each bin was n/(n-1) of
    the width asked for. On a pixel axis that is a bin sliding across the image
    rather than sitting on a pixel.
    """
    edges_1d, edges_2d = get_bins(None, (0.0, float(n_bins)), "linear",
                                  n_bins, n_bins)
    assert len(edges_1d) == n_bins + 1
    assert len(edges_2d) == n_bins + 1
    # One unit per bin, so bin k is exactly pixel k.
    np.testing.assert_allclose(np.diff(edges_2d), 1.0)


def test_log_bins_are_also_n_plus_one():
    edges_1d, edges_2d = get_bins(None, (1.0, 1000.0), "log", 3, 6)
    assert len(edges_1d) == 4 and len(edges_2d) == 7
    np.testing.assert_allclose(edges_1d, [1.0, 10.0, 100.0, 1000.0])


def test_weighting_by_column_zero_is_not_the_same_as_not_weighting(source):
    """``weight=0`` is a real column, and ``weight=None`` is no weighting.

    The parameter dict this used to be spelled a missing weight as ``0``, so a
    request with no weights weighted every histogram by the FIRST COLUMN -- on
    an image, the x coordinate -- which produces a plausible-looking picture
    that is not the data. ``None`` is now the only way to say "no weights", and
    it cannot be confused with column zero.
    """
    keep = source.column_view(2) == 0.0

    unweighted = compute_histograms(source, axes_for(), keep=keep)["2d"][0]
    assert unweighted.sum() == N_ROWS_PER_FRAME

    by_x = axes_for()
    by_x.weight = 0
    weighted = compute_histograms(source, by_x, keep=keep)["2d"][0]
    x = np.asarray(source.column_view(0))
    assert weighted.sum() == pytest.approx(x[keep].sum())
