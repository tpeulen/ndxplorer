"""The projection scores and rankers, on tables whose answer is known.

Orange3's own expectations are ported where Orange has them (correlation on iris
and on its ``mock_data`` with missing values); the rest are synthetic burst
tables where the informative view is planted.
"""

from __future__ import annotations

import math
import pathlib

import numpy as np
import numpy.testing as npt
import pytest
from scipy.stats import pearsonr, spearmanr

from ndxplorer.analysis.projection_scores import (
    GAUSSIAN_CLUSTER_INDEX,
    ClassLabels,
    ColumnView,
    ParameterRanker,
    ProjectionRanker,
    RankingTable,
    chance_corrected_agreement,
    cluster_index,
    correlation,
    display_coordinates,
    knn_separation,
    nearest_neighbours,
    structure_from_index,
)

IRIS = pathlib.Path(__file__).parent / "fixtures" / "iris.csv"
IRIS_NAMES = ["sepal length", "sepal width", "petal length", "petal width"]


@pytest.fixture(scope="module")
def iris():
    data = np.loadtxt(IRIS, delimiter=",", comments="#", skiprows=3)
    return data[:, :4], data[:, 4]


def rank_all(ranker):
    """Score every state and return the rows best first."""
    ranker.prepare()
    scored = [(ranker.compute_score(s), s) for s in ranker.iterate_states()]
    scored = [(score, s) for score, s in scored if score is not None]
    scored.sort(key=lambda item: item[0])
    return [ranker.row_for_state(score, s) for score, s in scored]


# ---- correlation: Orange's CorrelationRank expectations ---------------------------------


def test_correlation_on_iris_matches_orange(iris):
    """Orange ``test_compute_score_iris``: (1, 0) -> [-0.1094, -0.1094, 0.1828]."""
    x, _ = iris
    npt.assert_almost_equal(correlation(x[:, 1], x[:, 0]), [-0.1094, -0.1094, 0.1828], 4)


def test_correlation_agrees_with_scipy(iris):
    x, _ = iris
    r, p = pearsonr(x[:, 2], x[:, 0])
    npt.assert_allclose(correlation(x[:, 2], x[:, 0])[1:], [r, p], rtol=1e-10, atol=1e-300)
    rho, p_s = spearmanr(x[:, 1], x[:, 0])
    npt.assert_allclose(correlation(x[:, 1], x[:, 0], "spearman")[1:], [rho, p_s], rtol=1e-6)


def test_correlation_with_missing_values_matches_orange():
    """Orange ``test_compute_score_nans`` on its ``mock_data`` (columns d..j)."""
    n, s = np.nan, 0.5
    columns = np.array([
        [1, 0, 0, 1, 0, 0],  # d 0
        [0, 1, 1, 0, 1, 1],  # e 1
        [1, 0, 0, 1, 0, 0],  # f 2
        [1, 0, s, 1, 0, s],  # g 3
        [1, 0, n, 1, 0, n],  # h 4
        [n, 0, n, 1, 0, n],  # i 5
        [0, n, n, n, n, 1],  # j 6
    ])

    def score(i, j):
        return correlation(columns[i], columns[j])

    npt.assert_almost_equal(score(1, 0), [-1, -1, 0])
    npt.assert_almost_equal(score(2, 0), [-1, 1, 0])
    r, p = pearsonr(columns[3], columns[0])
    npt.assert_almost_equal(score(3, 0), [-abs(r), r, p])
    npt.assert_almost_equal(score(4, 0), [-1, 1, 0])
    npt.assert_almost_equal(score(5, 4), [-1, 1, 0])
    assert score(6, 4)[0] == math.inf and math.isnan(score(6, 4)[1])
    assert score(6, 5)[0] == math.inf and math.isnan(score(6, 5)[2])
    # Two samples: r = -1 with p = 1, which tells it apart from the case above.
    npt.assert_almost_equal(score(6, 0), [-1, -1, 1])


def test_a_constant_column_sorts_last():
    assert correlation(np.ones(10), np.arange(10.0))[0] == math.inf


# ---- class separation: Orange's scatter-plot score --------------------------------------


def test_neighbours_never_include_the_point_itself_even_among_duplicates():
    points = np.array([[0.0, 0.0]] * 4 + [[5.0, 5.0]] * 3)
    ind = nearest_neighbours(points, 3)
    assert not np.any(ind == np.arange(len(points))[:, None])
    assert set(ind[0]) == {1, 2, 3}


def test_knn_separation_matches_orange_definition(iris):
    """``-sum(same class) / k / n`` over the neighbours, brute force for reference."""
    x, y = iris
    points = x[:, [2, 3]]
    k = 10
    distances = np.linalg.norm(points[:, None] - points[None], axis=2)
    np.fill_diagonal(distances, np.inf)
    same = 0
    for i in range(len(points)):
        # Ties at the k-th distance make the neighbour set ambiguous; use the
        # score's own neighbours for those and check the rest independently.
        order = np.argsort(distances[i], kind="stable")[:k]
        same += np.sum(y[order] == y[i])
    brute = -same / k / len(y)
    assert knn_separation(points, y, discrete=True) == pytest.approx(brute, abs=0.01)


def test_iris_petal_pair_separates_best(iris):
    """The projection Orange's scatter plot finds on iris: petal length × petal width."""
    x, y = iris
    table = RankingTable({n: x[:, i] for i, n in enumerate(IRIS_NAMES)},
                         labels=ClassLabels(y, True, "iris"))
    rows = rank_all(ProjectionRanker(table, "separation"))
    assert {rows[0].payload["x"], rows[0].payload["y"]} == {"petal length", "petal width"}
    assert {rows[-1].payload["x"], rows[-1].payload["y"]} == {"sepal length", "sepal width"}
    assert rows[0].sort_value > 0.9


def test_chance_correction_is_zero_for_a_random_view():
    rng = np.random.default_rng(3)
    y = (rng.random(4000) < 0.05).astype(float)  # a small gate
    points = rng.random((4000, 2))
    raw = -knn_separation(points, y, discrete=True)
    assert raw > 0.85, "the majority class alone makes the raw score look good"
    assert abs(chance_corrected_agreement(raw, y)) < 0.05


def test_continuous_class_uses_neighbour_r2_weighted_by_valid_rows():
    rng = np.random.default_rng(4)
    x = rng.random((2000, 2))
    y = x[:, 0] * 3.0
    full = knn_separation(x, y, discrete=False)
    assert full == pytest.approx(-1.0, abs=0.01)
    y_half = y.copy()
    y_half[:1000] = np.nan
    assert knn_separation(x, y_half, discrete=False) == pytest.approx(full / 2, abs=0.01)


def burst_table(n=6000, seed=11):
    """A burst-like table: one pair separates two species, the rest is noise."""
    rng = np.random.default_rng(seed)
    species = (rng.random(n) < 0.3).astype(float)
    columns = {
        "Number of Photons": rng.lognormal(4.5, 0.6, n),
        "Tau (green)": np.where(species == 1, rng.normal(1.6, 0.25, n), rng.normal(3.6, 0.3, n)),
        "r Experimental (green)": np.where(species == 1, rng.normal(0.30, 0.03, n),
                                           rng.normal(0.12, 0.03, n)),
        "Duration (ms)": rng.gamma(2.0, 2.0, n),
        "Count Rate (KHz)": rng.normal(25, 6, n),
        "Mean Macro Time (s)": np.sort(rng.random(n)) * 3000,
    }
    return columns, species


def test_the_planted_pair_separates_best_on_a_burst_table():
    columns, species = burst_table()
    table = RankingTable(columns, labels=ClassLabels(species, True, "species"))
    rows = rank_all(ProjectionRanker(table, "separation"))
    assert {rows[0].payload["x"], rows[0].payload["y"]} == {"Tau (green)", "r Experimental (green)"}


def test_scaling_is_by_the_displayed_range_not_raw_units():
    """In raw units the photon count (hundreds) would swamp tau (a few ns)."""
    rng = np.random.default_rng(12)
    n = 4000
    species = (rng.random(n) < 0.5).astype(float)
    columns = {
        "Tau (green)": np.where(species == 1, rng.normal(3.0, 0.15, n), rng.normal(3.6, 0.15, n)),
        "Number of Photons": rng.normal(400, 120, n),
    }
    raw_pair = np.column_stack([columns["Tau (green)"], columns["Number of Photons"]])
    raw = chance_corrected_agreement(-knn_separation(raw_pair, species, discrete=True), species)
    table = RankingTable(columns, labels=ClassLabels(species, True, "species"))
    table.prepare()
    shown_score = knn_separation(table.matrix(["Tau (green)", "Number of Photons"]), table.y,
                                 discrete=True)
    shown = chance_corrected_agreement(-shown_score, table.y)
    # In raw units the neighbours are chosen almost entirely by photon count.
    assert shown > raw + 0.4


def test_gate_columns_are_not_ranked_against_their_own_gate():
    columns, _ = burst_table()
    inside = ((columns["Tau (green)"] > 1.0) & (columns["Tau (green)"] < 2.2)).astype(float)
    labels = ClassLabels(inside, True, "gate", exclude=("Tau (green)",), use_all_rows=True)
    ranker = ProjectionRanker(RankingTable(columns, rows=inside > 0, labels=labels), "separation")
    rows = rank_all(ranker)
    assert all("Tau (green)" not in (r.payload["x"], r.payload["y"]) for r in rows)
    # The gate captured the short-lifetime species, so the anisotropy finds it.
    assert "r Experimental (green)" in (rows[0].payload["x"], rows[0].payload["y"])
    # use_all_rows: both sides of the gate were ranked, not only the kept bursts.
    assert ranker.table.n_eligible == len(inside)


# ---- population structure -------------------------------------------------------------


@pytest.mark.parametrize("dimension", [1, 2])
def test_a_gaussian_scores_the_reference_index(dimension):
    rng = np.random.default_rng(7)
    points = rng.normal(size=(6000, dimension)) @ (np.array([[2.0, 1.5], [0.0, 0.3]])[:dimension, :dimension])
    assert cluster_index(points) == pytest.approx(GAUSSIAN_CLUSTER_INDEX, abs=0.015)


@pytest.mark.parametrize("delta", [4.0, 6.0])
def test_two_populations_score_the_closed_form_index(delta):
    """Equal populations delta sigmas apart: CI = 4 / (delta^2 + 4) along the split."""
    rng = np.random.default_rng(8)
    half = 3000
    along = np.r_[rng.normal(-delta / 2, 1, half), rng.normal(delta / 2, 1, half)]
    across = rng.normal(0, 1, 2 * half)
    # Correlated and on different units: whitening must see through both.
    points = np.column_stack([along, across]) @ np.array([[3.0, 0.8], [0.4, 0.05]])
    assert cluster_index(points) == pytest.approx(4 / (delta ** 2 + 4), abs=0.02)
    assert structure_from_index(cluster_index(points)) > 0.4


def test_duplicated_columns_are_refused_not_scored_as_structure():
    x = np.random.default_rng(1).normal(size=500)
    assert cluster_index(np.column_stack([x, 2 * x + 1])) is None


def test_the_bimodal_pair_ranks_first_without_classes():
    columns, _ = burst_table()
    rows = rank_all(ProjectionRanker(RankingTable(columns), "structure"))
    assert {rows[0].payload["x"], rows[0].payload["y"]} == {"Tau (green)", "r Experimental (green)"}
    assert rows[0].sort_value > 0.3
    singles = rank_all(ParameterRanker(RankingTable(columns), "structure"))
    assert singles[0].payload["z"] in {"Tau (green)", "r Experimental (green)"}
    # A uniform ramp and a unimodal normal are not populations.
    assert singles[-1].payload["z"] in {"Count Rate (KHz)", "Number of Photons", "Duration (ms)"}


# ---- the table ---------------------------------------------------------------------------


def test_display_coordinates_follow_scale_and_range():
    values = np.array([-1.0, 0.0, 1.0, 10.0, 100.0, 1000.0, np.nan])
    log = display_coordinates(values, ColumnView("n", "log", 1.0, 100.0))
    npt.assert_allclose(log[2:6], [0.0, 0.5, 1.0, 1.0])
    assert np.isnan(log[[0, 1, 6]]).all()
    lin = display_coordinates(values, ColumnView("n", "lin", 0.0, 10.0))
    npt.assert_allclose(lin[:5], [0.0, 0.0, 0.1, 1.0, 1.0])


def test_constant_and_empty_columns_are_dropped_and_the_sample_is_shared():
    rng = np.random.default_rng(2)
    columns = {"a": rng.normal(size=20000), "constant": np.ones(20000),
               "empty": np.full(20000, np.nan), "b": rng.normal(size=20000)}
    table = RankingTable(columns, max_rows=1500)
    table.prepare()
    assert table.names == ["a", "b"]
    assert table.n_rows == 1500 and table.n_eligible == 20000
    ranker = ProjectionRanker(table, "pearson")
    ranker.prepare()
    assert ranker.state_count() == 1


def test_a_float32_view_is_not_widened_before_sampling():
    """The sample is gathered first; only those rows become float64."""
    big = np.arange(50000, dtype=np.float32)
    table = RankingTable({"a": big, "b": big[::-1].copy()}, max_rows=100)
    table.prepare()
    assert table.raw["a"].dtype == np.float64 and table.raw["a"].size == 100


def test_separation_needs_classes():
    with pytest.raises(ValueError):
        ProjectionRanker(RankingTable({"a": np.arange(3.0)}), "separation")
    with pytest.raises(ValueError):
        ParameterRanker(RankingTable({"a": np.arange(3.0)}), "pearson")


def test_rows_read_like_the_table():
    columns, species = burst_table(n=1500)
    table = RankingTable(columns, views={"Number of Photons": ColumnView("Number of Photons", "log")})
    ranker = ProjectionRanker(table, "pearson")
    rows = rank_all(ranker)
    assert ranker.header == ("r", "x", "y")
    row = next(r for r in rows if "Number of Photons" in (r.payload["x"], r.payload["y"]))
    assert "Number of Photons (log)" in row.cells
    assert row.cells[0].startswith(("+", "-"))
    assert 0 <= row.bar <= 1 and row.bar_color is not None
    assert ranker.matches(row.payload, {"x": row.payload["y"], "y": row.payload["x"]})


# ---- what real burst tables needed ---------------------------------------------------------


def test_a_flag_column_is_not_population_structure():
    """A 0/1 fit switch splits perfectly and names no population (MFD: 'BIFL scatter?')."""
    rng = np.random.default_rng(5)
    n = 4000
    columns = {
        "flag": (rng.random(n) < 0.3).astype(float),
        "Tau": rng.normal(3.5, 0.3, n),
        "r": rng.normal(0.1, 0.03, n),
    }
    ranker = ProjectionRanker(RankingTable(columns), "structure")
    ranker.prepare()
    assert "flag" not in ranker.attrs
    correlation = ProjectionRanker(RankingTable(columns), "pearson")
    correlation.prepare()
    assert "flag" in correlation.attrs, "only structure leaves flags out"


def test_a_clump_of_a_few_percent_is_not_a_population():
    """A fit bound or sentinel (rho = 1e4 in 2.7 % of the MFD bursts) is not a split."""
    rng = np.random.default_rng(6)
    values = rng.normal(1.0, 0.3, 5000)
    values[:130] = 1e4
    assert cluster_index(values) > 0.3
    values[:1500] = 1e4  # 30 %: now it is a second population
    assert cluster_index(values) < 0.05


def test_columns_derived_from_the_gated_parameter_are_left_out_too():
    """E_tau is a function of Tau; excluding Tau alone would let it separate the gate."""
    columns, _ = burst_table()
    columns["E_tau"] = 1.0 - columns["Tau (green)"] / 4.0
    inside = ((columns["Tau (green)"] > 1.0) & (columns["Tau (green)"] < 2.2)).astype(float)
    labels = ClassLabels(inside, True, "gate", exclude=("Tau (green)",), use_all_rows=True)
    ranker = ProjectionRanker(RankingTable(columns, labels=labels), "separation")
    ranker.prepare()
    assert "E_tau" not in ranker.attrs and "Tau (green)" not in ranker.attrs
    assert "r Experimental (green)" in ranker.attrs
