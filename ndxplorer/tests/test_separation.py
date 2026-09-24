"""The Separation score: bursts in clearly separated islands.

Synthetic clouds whose answer is known (separated vs unimodal vs correlated),
the axis preparation (sentinels, counts, outliers), every *Rank by* option run
end to end through the panel's model, and the ranking on the two real test
tables: the MFD burst folder and the cal1 ALEX ``.pto``.
"""

from __future__ import annotations

import json
import pathlib

import numpy as np
import pytest

from ndxplorer.analysis.separation import RobustAxis, find_populations

N = 5000


def unit(points):
    """Each column through a RobustAxis, as a ranking prepares it."""
    points = np.asarray(points, dtype=np.float64)
    return np.column_stack([RobustAxis.fit(points[:, j])[1] for j in range(points.shape[1])])


def two(delta, share=0.5, seed=1):
    rng = np.random.default_rng(seed)
    k = int(N * share)
    a = rng.normal(0, 1, (N - k, 2))
    b = rng.normal(0, 1, (k, 2))
    b[:, 0] += delta
    return np.vstack([a, b])


# ---- the score ------------------------------------------------------------------------


@pytest.mark.parametrize("name, cloud", [
    ("gaussian", np.random.default_rng(2).normal(size=(N, 2))),
    ("correlated", np.random.default_rng(3).multivariate_normal([0, 0], [[1, .95], [.95, 1]], N)),
    ("skewed", np.column_stack([np.random.default_rng(4).lognormal(0, .8, N),
                                np.random.default_rng(5).normal(size=N)])),
    ("banana", (lambda t: np.column_stack([t, t ** 2 + np.random.default_rng(6).normal(0, .3, N)]))(
        np.random.default_rng(7).normal(size=N))),
    ("uniform", np.random.default_rng(8).uniform(size=(N, 2))),
    ("heavy tails", np.random.default_rng(9).standard_t(2, (N, 2))),
])
def test_one_population_scores_zero_however_it_is_shaped(name, cloud):
    found = find_populations(unit(cloud))
    assert found.count == 1 and found.score == 0.0, name


def test_two_equal_islands_score_the_chance_two_bursts_are_apart():
    far = find_populations(unit(two(10.0)))
    assert far.count == 2 and far.score == pytest.approx(0.5, abs=0.01)
    assert far.shares == pytest.approx([0.5, 0.5], abs=0.02)


def test_the_score_grows_with_the_gap_and_with_the_share_in_islands():
    scores = [find_populations(unit(two(d))).score for d in (3.0, 4.0, 6.0)]
    assert scores[0] < scores[1] < scores[2]
    small = find_populations(unit(two(6.0, share=0.1)))
    assert small.count == 2 and small.score == pytest.approx(0.18 * 0.9, abs=0.03), \
        "a 10 % island off a 90 % blob"


def test_a_clump_under_the_minimum_share_is_not_an_island():
    assert find_populations(unit(two(6.0, share=0.02))).count == 1


def test_three_fret_species_in_e_vs_s():
    """Donor-only (S~0.9), FRET (E~0.6) and acceptor-only (S~0.15) apart."""
    rng = np.random.default_rng(10)
    es = np.vstack([rng.normal([0.05, .9], [.05, .05], (1000, 2)),
                    rng.normal([.6, .55], [.1, .05], (3000, 2)),
                    rng.normal([.95, .15], [.05, .05], (1000, 2))])
    found = find_populations(unit(es))
    assert found.count == 3 and found.shares == pytest.approx([0.6, 0.2, 0.2], abs=0.02)
    assert found.score == pytest.approx(1 - (0.6 ** 2 + 2 * 0.2 ** 2), abs=0.03)
    labels = found.label(unit(es))
    assert (labels[:1000] == labels[0]).mean() > 0.99 and len(set(labels[[0, 1500, 4500]])) == 3


def test_weights_count_bright_bursts_more():
    """A wide low-photon population fills the valley; weighting by photons empties it."""
    rng = np.random.default_rng(11)
    bright = np.r_[rng.normal(0.3, 0.04, 2000), rng.normal(0.7, 0.04, 2000)]
    dim = rng.uniform(0.2, 0.8, 3000)
    x = unit(np.r_[bright, dim][:, None])[:, 0]
    photons = np.r_[np.full(4000, 400.0), np.full(3000, 40.0)]
    plain = find_populations(x)
    weighted = find_populations(x, weights=photons)
    assert weighted.score > plain.score


# ---- the axes ----------------------------------------------------------------------------


def test_a_sentinel_spike_is_missing_not_a_population():
    """The MFD red-channel fit writes -1 where it did not run (22 % of the bursts)."""
    rng = np.random.default_rng(12)
    tau = rng.normal(3.0, 0.4, N)
    tau[: N // 5] = -1.0
    axis, u = RobustAxis.fit(tau)
    assert axis.atoms == (-1.0,) and np.isnan(u[: N // 5]).all()
    assert find_populations(u).count == 1
    assert np.isnan(axis.transform(np.array([-1.0])))[0]


def test_counts_and_rounded_values_are_spread_over_their_step():
    rng = np.random.default_rng(13)
    counts = rng.poisson(20, N).astype(float)
    axis, u = RobustAxis.fit(counts)
    assert axis.quantum == 1.0 and not axis.atoms
    assert find_populations(u).count == 1, "a comb of integers is not populations"
    rounded = np.round(rng.normal(5, 1, 150), 1)  # iris-like
    axis, u = RobustAxis.fit(rounded)
    assert axis.quantum == pytest.approx(0.1) and np.isfinite(u).sum() > 140


def test_outliers_do_not_stretch_the_axis():
    rng = np.random.default_rng(14)
    x = np.r_[rng.normal(0, 1, N - 5), [1e6] * 5]
    axis, u = RobustAxis.fit(x)
    assert axis.hi < 10 and np.isnan(u[-5:]).all()


def test_the_axis_is_scale_invariant():
    cloud = two(6.0)
    a = find_populations(unit(cloud)).score
    b = find_populations(unit(cloud * [1e4, 1e-3] + [5e5, -7])).score
    assert a == pytest.approx(b, abs=1e-9)


# ---- every Rank-by option, end to end through the panel's model -------------------------------


def inline_runner(parent, text, func, *, args=(), on_partial=None, on_result=None,
                  on_error=None, on_done=None, **_kw):
    """``run_in_background`` run synchronously."""

    class Task:
        is_cancelled = False
        is_running = False

        def set_partial(self, value):
            on_partial(value)

        def set_progress(self, _value):
            pass

        def set_text(self, _text):
            pass

        def cancel(self):
            self.is_cancelled = True

    task = Task()
    try:
        result = func(*args, task)
    except Exception as exc:  # noqa: BLE001
        on_error(exc)
    else:
        on_result(result)
    on_done()
    return task


@pytest.fixture
def small_table():
    from ndxplorer.core.data_source import DataSource

    rng = np.random.default_rng(15)
    n = 1500
    species = rng.random(n) < 0.4
    tau = np.where(species, rng.normal(1.5, 0.2, n), rng.normal(3.8, 0.3, n))
    source = DataSource.from_columns({
        "Number of Photons": rng.poisson(150, n).astype(float),
        "Tau": tau,
        "r": np.where(species, rng.normal(0.3, 0.03, n), rng.normal(0.1, 0.03, n)),
        "Rate": rng.normal(20, 5, n),
        "Rate x2": 2 * rng.normal(20, 5, n),
    })
    return source, species.astype(float)


@pytest.mark.parametrize("pairs", [True, False])
def test_every_rank_by_option_ranks_end_to_end(small_table, pairs):
    """Each option the *Rank by* switch offers maps to an implemented score and ranks."""
    from ndxplorer.analysis.projection_rank_model import ProjectionRankModel, build_context
    from ndxplorer.analysis.vizrank import RunState

    source, species = small_table
    model = ProjectionRankModel(lambda: build_context(source, clusters=species), pairs,
                                runner=inline_runner)
    offered = [key for key, _ in model.method_options()]
    assert offered[0] == "populations" and model.method == "populations"
    assert ("correlation" in offered) == pairs and "separation" in offered
    for key in offered:
        model.method = key
        model.settings_changed()
        model.start()
        assert not model.error, (key, model.error)
        assert model.run_state == RunState.Done and model.rows, key
        best = model.rows[0]
        names = {best["name0"], best.get("name1")} if pairs else {best["name0"]}
        assert names & {"Tau", "r"}, (key, best)


def test_an_unknown_method_falls_back_to_separation(small_table):
    """A stale choice ('structure' from an older ndX) must not end in a KeyError."""
    from ndxplorer.analysis.projection_rank_model import ProjectionRankModel, build_context

    source, _ = small_table
    model = ProjectionRankModel(lambda: build_context(source), True, runner=inline_runner)
    model.method = "structure"
    model.start()
    assert not model.error and model.method == "populations" and model.rows


def test_photon_options_follow_the_photon_column(small_table):
    from ndxplorer.analysis.projection_rank_model import ProjectionRankModel, build_context

    source, _ = small_table
    model = ProjectionRankModel(lambda: build_context(source), True, runner=inline_runner)
    assert [k for k, _ in model.photon_options()] == ["all", "weight", "min"]
    for mode in ("weight", "min"):
        model.photon_mode = mode
        model.min_photons = 140
        model.settings_changed()
        model.start()
        assert not model.error and model.rows
    assert model._run.ranker.table.n_eligible < source.size, "the threshold removed bursts"
    assert model.min_photons_hidden is False
    model.method = "correlation"
    assert model.min_photons_hidden is True


def test_the_view_spec_names_only_what_the_model_has(small_table):
    from ndxplorer.analysis.projection_rank_model import ProjectionRankModel, build_context
    from ndxplorer.analysis.vizrank_model import load_spec

    source, _ = small_table
    model = ProjectionRankModel(lambda: build_context(source), True, runner=inline_runner)

    def walk(sections):
        for section in sections:
            yield section
            yield from walk(section.get("sections", []))

    for section in walk(load_spec()["sections"]):
        for key in ("attr", "options_source", "source", "call"):
            if key in section:
                assert hasattr(model, section[key]), (key, section[key])
        cond = section.get("hidden_when")
        if cond:
            assert hasattr(model, cond["attr"])


# ---- the real tables ---------------------------------------------------------------------------

HERE = pathlib.Path(__file__).resolve()
MFD = HERE.parents[2] / "test" / "mfd" / "burstwise_All 0.1500#30"
ALEX = pathlib.Path.home() / "dev/tttr-data/sm/cal1/001_60g_25r_cal1_cy3b_8_18_33bp_atto647n_alex.pto"


def real_context(path):
    from ndxplorer.analysis.projection_rank_model import build_context
    from ndxplorer.cli import _load_settings_and_equations
    from ndxplorer.io import loading
    from ndxplorer.settings import get_settings_path

    source = loading.read([str(path)])
    constants, equations = _load_settings_and_equations()
    source.compute_columns(constants=constants, equations=equations)
    axes = json.loads((get_settings_path() / "mfd.axis.json").read_text(encoding="utf-8"))
    return build_context(source, axes)


def top_pairs(path, n):
    from ndxplorer.analysis.projection_scores import ProjectionRanker, RankingTable

    context = real_context(path)
    ranker = ProjectionRanker(RankingTable(context.columns, context.views), "populations")
    ranker.prepare()
    scored = [(ranker.compute_score(s), s) for s in ranker.iterate_states()]
    scored = sorted((x for x in scored if x[0] is not None), key=lambda x: x[0])
    return [ranker.row_for_state(score, state) for score, state in scored[:n]]


@pytest.mark.skipif(not MFD.is_dir(), reason="MFD burst test data not present")
def test_mfd_top_views_split_fret_populations():
    """E against a lifetime/variance indicator: donor-only and two FRET species apart."""
    rows = top_pairs(MFD, 5)
    pairs = [{r.payload["x"], r.payload["y"]} for r in rows]
    fret = {"FRET efficiency", "Proximity ratio", "Sg/Sr"}
    assert all(p & fret for p in pairs), pairs
    assert {"FRET efficiency", "Tau (green)"} in pairs or \
        any({"Tau (green)", "Var(E)", "(1-E)*E_tau"} & p for p in pairs)
    assert all(int(r.cells[-1]) >= 2 for r in rows)
    clocks = {"First Photon", "Mean Macro Time (s)"}
    assert not any(p & clocks for p in pairs)


@pytest.mark.skipif(not ALEX.is_file(), reason="cal1 ALEX .pto not present")
def test_alex_top_view_is_e_vs_s():
    rows = top_pairs(ALEX, 3)
    best = {rows[0].payload["x"], rows[0].payload["y"]}
    assert best == {"Stoichiometry (PIE)", "FRET efficiency(PIE)"}, best
    assert int(rows[0].cells[-1]) >= 3, "donor-only, FRET and acceptor-only"
    assert all("Stoichiometry (PIE)" in {r.payload["x"], r.payload["y"]} for r in rows)
