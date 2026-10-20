"""The scores views are ranked by: correlation, k-NN class separation, the
shared sample, the column choice and the two rankers.

Numbers are worked by hand or by brute force; SciPy, where installed, is an
oracle for the correlation tests only (it is not a runtime dependency).
"""

from __future__ import annotations

import pathlib

import numpy as np
import pytest
from ndxplorer.analysis.projection_scores import (
    DERIVED_RHO,
    METHOD_HELP,
    METHODS,
    MIN_DISTINCT,
    MIN_K,
    NEGATIVE_BAR,
    POSITIVE_BAR,
    ClassLabels,
    ColumnSet,
    ColumnView,
    ParameterRanker,
    ProjectionRanker,
    RankingTable,
    average_ranks,
    chance_corrected_agreement,
    correlation,
    correlation_ratio,
    display_coordinates,
    is_clock,
    knn_separation,
    nearest_neighbours,
)

NAN, INF = np.nan, np.inf
TOL = 1e-9
IRIS = pathlib.Path(__file__).resolve().parent / "fixtures" / "iris.csv"
IRIS_NAMES = ["sepal length", "sepal width", "petal length", "petal width"]
X12 = np.array([0, 1, 3, 6, 10, 15, 21, 28, 36, 45, 55, 66], dtype=float)
HALVES = np.r_[np.zeros(6), np.ones(6)]


def iris():
    lines = [line for line in IRIS.read_text(encoding="utf-8").splitlines()
             if line and not line.startswith("#")]
    assert lines[0].split(",")[:4] == IRIS_NAMES
    data = np.array([[float(v) for v in line.split(",")] for line in lines[1:]])
    assert data.shape == (150, 5)
    return {name: data[:, i] for i, name in enumerate(IRIS_NAMES)}, data[:, 4]


# ---- correlation ---------------------------------------------------------------------------
@pytest.mark.parametrize("a, b, method, expected", [
    ([1, 2, 3, 4, 5], [2, 1, 4, 3, 5], "pearson", (-0.8, 0.8, 0.104088038662)),
    ([1, 2, 3, 4, 5], [2, 1, 4, 3, 5], "spearman", (-0.8, 0.8, 0.104088038662)),
    ([1, 1, 2, 3], [1, 2, 2, 3], "pearson", (-0.852802865422, 0.852802865422, 0.147197134578)),
    ([1, 1, 2, 3], [1, 2, 2, 3], "spearman", (-0.833333333333, 0.833333333333, 0.166666666667)),
    ([1, 2, 3, 4, 5, 6], [2, 4, 5, 4, 5, 7], "pearson",
     (-0.878310065654, 0.878310065654, 0.021311641129)),
    ([1, 2, 3, 4, 5, 6], [2, 4, 5, 4, 5, 7], "spearman",
     (-0.853310335188, 0.853310335188, 0.030698562973)),
    ([1, 2, NAN, 4, 5], [2, 1, 7, 3, INF], "pearson",
     (-0.654653670708, 0.654653670708, 0.545628948343)),
    ([1, 2], [3, 1], "pearson", (-1.0, -1.0, 1.0)),
    (np.arange(5), 2 * np.arange(5) + 1, "pearson", (-1.0, 1.0, 0.0)),
    (np.arange(5), -np.arange(5), "pearson", (-1.0, -1.0, 0.0)),
])
def test_correlation_values(a, b, method, expected):
    assert correlation(a, b, method) == pytest.approx(expected, abs=1e-9)


@pytest.mark.parametrize("a, b", [([1], [3]), (np.ones(5), np.arange(5))])
@pytest.mark.parametrize("method", ["pearson", "spearman"])
def test_undefined_correlation(a, b, method):
    key, r, p = correlation(a, b, method)
    assert key == INF and np.isnan(r) and np.isnan(p)


def test_iris_correlations():
    cols, _ = iris()
    sl, sw, pl, pw = (cols[n] for n in IRIS_NAMES)
    _, r, p = correlation(sl, sw)
    assert (r, p) == pytest.approx((-0.109369, 0.182765), abs=5e-5)
    assert correlation(pl, pw)[1] == pytest.approx(0.962757, abs=5e-6)
    _, rho, p = correlation(sl, sw, "spearman")
    assert (rho, p) == pytest.approx((-0.159457, 0.051285), abs=5e-6)
    assert correlation(pl, pw, "spearman")[1] == pytest.approx(0.936003, abs=5e-6)


def test_correlation_agrees_with_scipy():
    stats = pytest.importorskip("scipy.stats")
    rng = np.random.default_rng(0)
    for _ in range(300):
        n = int(rng.integers(3, 80))
        a = rng.integers(0, 6, n).astype(float)
        b = a * rng.uniform(-1, 1) + rng.integers(0, 4, n)
        if np.ptp(a) == 0 or np.ptp(b) == 0:
            continue
        for method, oracle in (("pearson", stats.pearsonr), ("spearman", stats.spearmanr)):
            _, r, p = correlation(a, b, method)
            expected = oracle(a, b)
            assert r == pytest.approx(expected[0], abs=1e-6)
            assert p == pytest.approx(expected[1], abs=1e-6)


def test_average_ranks_share_ties():
    assert average_ranks([3.0, 1.0, 3.0, 2.0, 3.0]).tolist() == [3.0, 0.0, 3.0, 1.0, 3.0]
    assert average_ranks([]).size == 0


# ---- nearest neighbours ---------------------------------------------------------------------
def test_neighbours_break_ties_by_index():
    assert nearest_neighbours([0, 1, 3, 6, 10], 2).tolist() == \
        [[1, 2], [0, 2], [1, 0], [2, 4], [3, 2]]


def test_a_point_is_never_its_own_neighbour_among_duplicates():
    points = np.array([[0, 0]] * 4 + [[5, 5]] * 3, dtype=float)
    out = nearest_neighbours(points, 3)
    assert all(i not in row for i, row in enumerate(out))
    assert out[0].tolist() == [1, 2, 3]
    assert out[4:].tolist() == [[5, 6, 0], [4, 6, 0], [4, 5, 0]]


@pytest.mark.parametrize("kind", ["continuous", "counts 1-D", "lattice", "clipped", "binary"])
def test_neighbours_are_exact(kind):
    rng = np.random.default_rng(3)
    points = {
        "continuous": rng.random((800, 2)),
        "counts 1-D": rng.poisson(30, 800).astype(float)[:, None],
        "lattice": rng.integers(0, 6, (800, 2)).astype(float),
        "clipped": np.clip(rng.normal(0.5, 0.5, (800, 2)), 0, 1),
        "binary": rng.integers(0, 2, (800, 1)).astype(float),
    }[kind]
    k = 10
    out = nearest_neighbours(points, k)
    index = np.arange(len(points))
    for i in range(len(points)):
        d = ((points - points[i]) ** 2).sum(axis=1)
        d[i] = INF
        assert out[i].tolist() == np.lexsort((index, d))[:k].tolist(), i


def test_neighbours_need_more_points_than_k():
    with pytest.raises(ValueError):
        nearest_neighbours(np.arange(3.0), 3)


# ---- k-NN class separation ------------------------------------------------------------------
@pytest.mark.parametrize("labels, share, kappa", [
    (HALVES, 0.888888888889, 0.796296296296),
    (np.array([0, 0, 1, 1, 2, 2, 0, 1, 2, 0, 1, 2], float), 0.194444444444, -0.107638888889),
])
def test_separation_of_a_column(labels, share, kappa):
    value = knn_separation(X12, labels, discrete=True, k=3)
    assert value == pytest.approx(-share, abs=TOL)
    assert chance_corrected_agreement(-value, labels) == pytest.approx(kappa, abs=TOL)


def test_a_missing_coordinate_drops_its_row():
    x = X12.copy()
    x[0] = NAN
    value = knn_separation(x, HALVES, discrete=True, k=3)
    assert value == pytest.approx(-0.878787878788, abs=TOL)
    kappa = chance_corrected_agreement(-value, HALVES[1:])
    assert kappa == pytest.approx(0.777777777778, abs=TOL)
    assert kappa * 11 / 12 == pytest.approx(0.712962962963, abs=TOL)


def test_every_point_needs_k_others():
    assert knn_separation(X12[:9], HALVES[:9], discrete=True, k=10) is None
    assert knn_separation(X12[:3], HALVES[:3], discrete=True, k=3) is None
    assert knn_separation(X12[:4], np.array([0, 0, 1, 1.]), discrete=True, k=3) is not None


def test_separation_in_two_dimensions():
    points = [(0.1, 0.2), (0.15, 0.22), (0.2, 0.15), (0.12, 0.3), (0.8, 0.7), (0.85, 0.75),
              (0.9, 0.66), (0.7, 0.8), (0.5, 0.5), (0.45, 0.55)]
    y = np.array([0, 0, 0, 0, 1, 1, 1, 1, 0, 1], float)
    value = knn_separation(points, y, discrete=True, k=3)
    assert value == pytest.approx(-0.866666666667, abs=TOL)
    assert chance_corrected_agreement(-value, y) == pytest.approx(0.76, abs=TOL)


def test_separation_of_a_quantity():
    y = np.arange(12.0)
    assert knn_separation(X12, y, discrete=False, k=3) == pytest.approx(-0.912975912975913,
                                                                        abs=TOL)
    x = X12.copy()
    x[0] = NAN
    assert knn_separation(x, y, discrete=False, k=3) == pytest.approx(-0.816666666667, abs=TOL)
    assert knn_separation(X12, np.ones(12), discrete=False, k=3) is None


def test_chance_agreement_draws_from_the_other_points():
    assert chance_corrected_agreement(1.0, np.zeros(5)) is None
    assert chance_corrected_agreement(0.5, []) is None
    assert chance_corrected_agreement(0.5, np.tile([0.0, 1.0], 5)) == pytest.approx(0.1, abs=TOL)
    unbalanced = np.r_[np.zeros(95), np.ones(5)]
    assert chance_corrected_agreement(0.9, unbalanced) == pytest.approx(-0.042105263158, abs=TOL)


def test_a_random_view_of_an_unbalanced_gate_scores_near_zero():
    rng = np.random.default_rng(5)
    points = rng.random((4000, 2))
    y = (rng.random(4000) < 0.05).astype(float)
    share = -knn_separation(points, y, discrete=True)
    assert share > 0.85 and abs(chance_corrected_agreement(share, y)) < 0.05


# ---- display coordinates ------------------------------------------------------------------------
V = np.array([-1, 0, 1, 10, 100, 1000, NAN, INF])


def test_display_coordinates_log():
    u = display_coordinates(V, ColumnView("v", "log", 1, 100))
    np.testing.assert_allclose(u, [NAN, NAN, 0, 0.5, 1, 1, NAN, NAN])
    assert u.dtype == np.float64 and u.shape == V.shape
    assert np.isnan(display_coordinates(V, ColumnView("v", "log", 0, 100))).all()


def test_display_coordinates_linear():
    np.testing.assert_allclose(display_coordinates(V, ColumnView("v", "lin", 0, 10)),
                               [0, 0, 0.1, 1, 1, 1, NAN, NAN])
    assert np.isnan(display_coordinates(V, ColumnView("v", "lin", 5, 5))).all()
    auto = display_coordinates(np.linspace(2, 4, 50), ColumnView("v"))
    assert auto[0] == 0 and auto[-1] == 1


# ---- correlation ratio, clock -----------------------------------------------------------------------
def test_correlation_ratio():
    rng = np.random.default_rng(2)
    x = rng.random(500)
    assert correlation_ratio(np.abs(x - 0.5) * 2, x) > 0.98, "a fold is a function"
    assert correlation_ratio(x, np.abs(x - 0.5) * 2) < 0.5
    assert correlation_ratio(rng.random(500), x) < 0.2
    assert correlation_ratio(x[:2 * MIN_K - 1], x[:2 * MIN_K - 1]) == 0.0
    assert correlation_ratio(np.full(100, 0.3), x[:100]) == 0.0


def test_the_clock_rises():
    t = np.cumsum(np.random.default_rng(1).exponential(1, 200))
    assert is_clock(t) and not is_clock(t[::-1]) and not is_clock(t[:2 * MIN_K])
    assert not is_clock(np.random.default_rng(2).random(200))


# ---- the shared sample ------------------------------------------------------------------------------
def test_the_sample_is_shared_drawn_once_and_ascending():
    rng = np.random.default_rng(0)
    n = 20000
    cols = {"a": rng.normal(size=n).astype(np.float32), "b": rng.normal(size=n),
            "flat": np.ones(n)}
    rows = rng.random(n) < 0.5
    table = RankingTable(cols, rows=rows, max_rows=1000, seed=3)
    assert table.n_rows == 0
    table.prepare()
    table.prepare()
    assert table.n_rows == 1000 and table.n_eligible == int(rows.sum())
    assert np.all(np.diff(table.index) > 0) and rows[table.index].all()
    assert table.names == ["a", "b"], "a constant column has no view"
    assert table.raw["a"].dtype == np.float64
    assert table.w is None and table.total_weight == 1000
    again = RankingTable(cols, rows=rows, max_rows=1000, seed=3)
    again.prepare()
    assert np.array_equal(again.index, table.index)


def test_labels_and_weights_choose_the_eligible_rows():
    x = np.arange(100.0)
    labels = np.where(x < 10, NAN, x % 2)
    weights = np.where(x % 5 == 0, 0.0, x)
    gate = x < 50
    table = RankingTable({"x": x}, rows=gate, labels=ClassLabels(labels, True, "c"),
                         weights=weights)
    table.prepare()
    keep = gate & np.isfinite(labels) & (weights > 0)
    assert table.index.tolist() == np.flatnonzero(keep).tolist()
    assert table.w.mean() == pytest.approx(1.0) and table.total_weight == pytest.approx(keep.sum())
    inside = RankingTable({"x": x}, rows=gate,
                          labels=ClassLabels(gate.astype(float), True, "g", use_all_rows=True))
    inside.prepare()
    assert inside.n_rows == 100


def test_derived_columns():
    rng = np.random.default_rng(4)
    gate = rng.normal(size=500)
    cols = {"g": gate, "g cubed": gate ** 3, "other": rng.normal(size=500)}
    table = RankingTable(cols)
    assert table.derived_from(["g"]) == ["g cubed"]
    assert table.derived_from(["missing"]) == []
    assert DERIVED_RHO == 0.98


# ---- the columns worth pairing ------------------------------------------------------------------------
def test_flags_clocks_aliases_and_folds_are_set_aside():
    rng = np.random.default_rng(6)
    n = 3000
    e = rng.beta(2, 2, n)
    cols = {
        "time": np.sort(rng.uniform(0, 100, n)),
        "flag": rng.integers(0, 3, n).astype(float),
        "E": e,
        "E again": 2 * e + 1,
        "fold": (1 - e) * e,
        "tau": rng.gamma(4, 1, n),
    }
    columns = ColumnSet(RankingTable(cols))
    assert columns.left_out["time"] == "the acquisition clock"
    assert columns.left_out["flag"] == "a flag (few distinct values)"
    assert MIN_DISTINCT == 20
    merged = [n for n in ("E", "E again") if n in columns.left_out]
    assert len(merged) == 1 and columns.left_out[merged[0]].startswith("the same as ")
    assert columns.left_out["fold"].startswith("a fold of ")
    assert "tau" in columns.names and len(columns.names) == 2
    head = next(n for n in ("E", "E again") if n in columns.names)
    assert columns.aliases[head] == merged
    assert columns.matrix(columns.names).shape == (n, 2)


def test_a_curve_is_not_a_cloud():
    rng = np.random.default_rng(7)
    x = rng.normal(size=2000)
    cols = {"x": x, "parabola": x ** 2 + rng.normal(0, 0.01, 2000), "y": rng.normal(size=2000)}
    columns = ColumnSet(RankingTable(cols))
    assert columns.is_curve("x", "parabola") and not columns.is_curve("x", "y")


# ---- the rankers ----------------------------------------------------------------------------------
def test_methods_and_their_help():
    assert list(METHODS) == ["populations", "correlation", "separation"]
    assert [m[0] for m in METHODS.values()] == ["Separation", "Correlation", "Classes"]
    assert METHODS["separation"][1] and not METHODS["correlation"][3]
    assert set(METHOD_HELP) == set(METHODS)
    assert "10 nearest neighbours" in METHOD_HELP["separation"] and MIN_K == 10


def test_construction_checks_and_reads_nothing():
    table = RankingTable({"a": np.arange(5.0)})
    with pytest.raises(ValueError):
        ProjectionRanker(table, "structure")
    with pytest.raises(ValueError):
        ProjectionRanker(table, "separation")
    with pytest.raises(ValueError):
        ParameterRanker(table, "correlation")
    ranker = ProjectionRanker(table, "populations")
    assert table.n_rows == 0 and ranker.attrs == [] and ranker.left_out() == {}


def _iris_ranker():
    cols, species = iris()
    table = RankingTable(cols, labels=ClassLabels(species, True, "species"))
    ranker = ProjectionRanker(table, "separation")
    ranker.prepare()
    return ranker


def test_iris_by_species():
    ranker = _iris_ranker()
    assert not ranker._columns_ready
    states = list(ranker.iterate_states())
    assert ranker._columns_ready and len(states) == ranker.state_count() == 6
    assert ranker.attrs == ["petal width", "petal length", "sepal length", "sepal width"]
    ranked = sorted((ranker.compute_score(s), s) for s in states)
    assert set(ranked[0][1]) == {"petal width", "petal length"}
    assert set(ranked[-1][1]) == {"sepal length", "sepal width"}
    row = ranker.row_for_state(*ranked[0])
    assert ranker.header == ("κ", "x", "y") and ranker.score_span == (0.0, 1.0)
    assert 0.9 < row.sort_value < 0.95 and row.cells[0] == f"{row.sort_value:.3f}"
    assert "nearest neighbours share its class (species)" in row.tooltip
    assert row.payload == {"x": "petal width", "y": "petal length",
                           "scale_x": "lin", "scale_y": "lin"}


def test_a_view_scores_the_same_with_its_axes_swapped():
    ranker = _iris_ranker()
    for state in ranker.iterate_states():
        assert ranker.compute_score(state) == ranker.compute_score(state[::-1])


def test_coverage_weights_the_class_score():
    rng = np.random.default_rng(8)
    n = 400
    y = (np.arange(n) < n // 2).astype(float)
    full = y + rng.normal(0, 0.05, n)
    half = full.copy()
    half[::2] = NAN                                 # the same separation on half the bursts
    table = RankingTable({"full": full, "half": half, "noise": rng.normal(size=n)},
                         labels=ClassLabels(y, True, "c"))
    ranker = ParameterRanker(table, "separation")
    ranker.prepare()
    scores = {s[0]: ranker.compute_score(s) for s in ranker.iterate_states()}
    assert scores["full"][0] < scores["half"][0] < scores["noise"][0]
    assert -scores["half"][0] == pytest.approx(-scores["full"][0] * 0.5, abs=0.02)


def test_a_quantity_is_ranked_by_r_squared():
    rng = np.random.default_rng(9)
    n = 600
    target = rng.normal(size=n)
    table = RankingTable({"target-ish": target + rng.normal(0, 0.1, n),
                          "noise": rng.normal(size=n)},
                         labels=ClassLabels(target, False, "lifetime"))
    ranker = ParameterRanker(table, "separation")
    ranker.prepare()
    assert ranker.header == ("R²", "Parameter")
    states = list(ranker.iterate_states())
    best = min((ranker.compute_score(s), s) for s in states)
    assert best[1] == ("target-ish",)
    row = ranker.row_for_state(*best)
    assert "predicts its own with R²" in row.tooltip and row.payload["z"] == "target-ish"


def test_the_correlation_ranker_uses_average_ranks():
    stats = pytest.importorskip("scipy.stats")
    rng = np.random.default_rng(10)
    n = 1500
    base = rng.normal(size=n)
    cols = {"steps": np.round(base * 10),
            "smooth": base + rng.normal(0, 0.5, n), "other": rng.normal(size=n)}
    table = RankingTable(cols)
    ranker = ProjectionRanker(table, "correlation")
    ranker.prepare()
    assert ranker.header == ("ρ", "x", "y") and ranker.score_span == (-1.0, 1.0)
    columns = None
    for state in ranker.iterate_states():
        columns = ranker.columns
        score = ranker.compute_score(state)
        a, b = columns.coords[state[0]], columns.coords[state[1]]
        ok = np.isfinite(a) & np.isfinite(b)
        rho = stats.spearmanr(a[ok], b[ok])[0]
        assert -score[0] == pytest.approx(abs(rho), abs=1e-9)
        row = ranker.row_for_state(score, state)
        assert row.value == pytest.approx(rho, abs=1e-9)
        assert row.bar_color == (POSITIVE_BAR if rho >= 0 else NEGATIVE_BAR)
        assert row.tooltip.startswith("Spearman ρ = ")
    assert POSITIVE_BAR != NEGATIVE_BAR


def test_population_rows_and_islands():
    rng = np.random.default_rng(11)
    n = 3000
    species = rng.random(n) < 0.5
    cols = {"E": np.where(species, rng.normal(0.2, 0.04, n), rng.normal(0.8, 0.04, n)),
            "S": rng.normal(0.5, 0.05, n), "Rate": rng.normal(20, 4, n)}
    table = RankingTable(cols, views={"Rate": ColumnView("Rate", "log")})
    ranker = ProjectionRanker(table, "populations")
    ranker.prepare()
    assert ranker.ranked_names(["E"]) is None, "columns not chosen yet"
    scored = sorted(((ranker.compute_score(s), s) for s in ranker.iterate_states()),
                    key=lambda item: item[0])
    best = ranker.row_for_state(*scored[0])
    assert "E" in scored[0][1] and best.cells[-1] == "2"
    assert ranker.header == ("Separation", "x", "y", "Islands")
    assert ranker.score_span == (0.0, 0.5) and 0 < best.bar <= 1
    assert "islands holding" in best.tooltip
    rate_rows = [ranker.row_for_state(sc, st) for sc, st in scored if "Rate" in st]
    assert all("Rate (log)" in row.cells for row in rate_rows)
    names = list(scored[0][1])
    labels = ranker.islands(names, [cols[n] for n in names])
    assert labels.shape == (n,) and set(np.unique(labels)) >= {0, 1}
    assigned, probability = ranker.assign_islands(names, [cols[n] for n in names])
    assert assigned.shape == probability.shape == (n,)
    assert ranker.ranked_names(["E", "unknown"]) is None
    single = ParameterRanker(RankingTable(cols), "populations")
    single.prepare()
    assert single.header == ("Separation", "Parameter", "Islands")
    assert single.matches({"z": "E"}, {"z": "E"}) and not single.matches({"z": "E"}, {"z": "S"})
    assert ranker.matches({"x": "E", "y": "S"}, {"x": "S", "y": "E"})


def test_pairs_are_ordered_by_their_columns_alone():
    rng = np.random.default_rng(12)
    n = 3000
    two = np.where(rng.random(n) < 0.5, rng.normal(0.2, 0.03, n), rng.normal(0.8, 0.03, n))
    cols = {"plain a": rng.normal(size=n), "plain b": rng.normal(size=n), "split": two}
    ranker = ProjectionRanker(RankingTable(cols), "populations")
    ranker.prepare()
    assert ranker.state_count() == 3
    assert ranker.attrs[0] == "split"
    first = next(iter(ranker.iterate_states()))
    assert "split" in first
