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


def islands_bridge_clump(seed):
    """Three islands (2500/1500/900 bursts), a bridge from island 0 to 1 that
    thins toward its middle (``along`` 0..1 on it), a 60-burst clump (1.2 %,
    under MIN_POPULATION) and 20 far outliers; ``(points, truth, along, axes)``
    with truth 0-2 islands, 3 bridge, 4 clump, 5 outlier."""
    rng = np.random.default_rng(seed)
    parts, truth, along = [], [], []
    for k, (c, n) in enumerate([((0.2, 0.3), 2500), ((0.8, 0.6), 1500), ((0.5, 0.9), 900)]):
        parts.append(rng.normal(c, 0.04, (n, 2)))
        truth.append(np.full(n, k))
    d = np.where(rng.random(600) < 0.8, 0.5 * np.sqrt(rng.random(600)), 0.5 * rng.random(600))
    t = 0.5 + np.where(rng.random(600) < 0.5, -d, d)
    parts.append(np.column_stack([0.2 + 0.6 * t, 0.3 + 0.3 * t]) + rng.normal(0, 0.015, (600, 2)))
    truth.append(np.full(600, 3))
    parts.append(rng.normal((0.85, 0.12), 0.02, (60, 2)))
    truth.append(np.full(60, 4))
    parts.append(rng.uniform((30, -40), (40, -30), (20, 2)))
    truth.append(np.full(20, 5))
    points, truth = np.vstack(parts), np.concatenate(truth)
    along = np.full(truth.size, np.nan)
    along[truth == 3] = t
    axes = [RobustAxis.fit(points[:, j])[0] for j in range(2)]
    return points, truth, along, axes


def _coords(axes, points):
    return np.column_stack([a.transform(points[:, j]) for j, a in enumerate(axes)])


@pytest.mark.parametrize("seed", [1, 2, 3])
def test_whole_islands_label_every_basin_but_ridges_clumps_and_outliers(seed):
    points, truth, along, axes = islands_bridge_clump(seed)
    u = _coords(axes, points)
    found = find_populations(u)
    assert found.count == 3
    labels, probability = found.assign(u)  # "whole" is the default
    for k in range(3):
        mine = labels[truth == k]
        assert np.mean(mine == k) >= 0.95, k
        assert np.all((mine == k) | (mine == -1)), "never the wrong island"
    assert np.all(labels[truth == 4] == -1), "a clump under 3 % is -1, not merged"
    assert np.all(labels[truth == 5] == -1), "outliers"
    bridge = truth == 3
    t, lb = along[bridge], labels[bridge]
    # the bridge's halves go to the islands at their ends; -1 and any switch
    # between the two islands only in the ridge band around its dip
    assert np.all(lb[t < 0.4] == 0) and np.all(lb[t > 0.6] == 1)
    assert np.all(np.abs(t[lb == -1] - 0.5) < 0.1)
    # along the bridge's midline: island 0, the ridge (-1), island 1
    tt = np.linspace(0.0, 1.0, 2001)
    line = _coords(axes, np.column_stack([0.2 + 0.6 * tt, 0.3 + 0.3 * tt]))
    on_line = found.assign(line)[0]
    runs = [on_line[0]] + [b for a, b in zip(on_line[:-1], on_line[1:]) if b != a]
    assert runs == [0, -1, 1]
    ridge = tt[on_line == -1]
    assert abs(ridge.mean() - 0.5) < 0.06 and np.ptp(ridge) < 0.06, "a thin band"
    # probabilities: 1 deep inside, falling toward the ridge, 0 for -1
    assert np.all(probability[labels == -1] == 0.0)
    assert np.all(probability[labels >= 0] >= 2.0 / 3.0 - 1e-9)
    assert np.median(probability[truth == 0]) > 0.99
    near = bridge & (np.abs(along - 0.5) < 0.1) & (labels >= 0)
    assert np.min(probability[near]) < 0.8 < np.median(probability[near])


def test_cores_only_labels_as_before():
    """Cores: the labels label(core=True) gives; the bridge's middle is -1."""
    points, truth, along, axes = islands_bridge_clump(1)
    u = _coords(axes, points)
    found = find_populations(u)
    labels, probability = found.assign(u, "cores")
    assert np.array_equal(labels, found.label(u, core=True))
    for k in range(3):
        mine = labels[truth == k]
        assert np.mean(mine == k) > 0.9 and np.all((mine == k) | (mine == -1))
    assert np.mean(labels[(truth == 3) & (np.abs(along - 0.5) < 0.05)] == -1) > 0.9
    whole = found.assign(u)[0]
    assert np.mean(whole >= 0) > np.mean(labels >= 0)
    assert np.all(probability[labels == -1] == 0.0)
    with pytest.raises(ValueError):
        found.assign(u, "everything")


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


def real_source(path):
    from ndxplorer.cli import _load_settings_and_equations
    from ndxplorer.io import loading
    from ndxplorer.settings import get_settings_path

    source = loading.read([str(path)])
    constants, equations = _load_settings_and_equations()
    source.compute_columns(constants=constants, equations=equations)
    axes = json.loads((get_settings_path() / "mfd.axis.json").read_text(encoding="utf-8"))
    return source, axes


def real_context(path):
    from ndxplorer.analysis.projection_rank_model import build_context

    return build_context(*real_source(path))


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


@pytest.mark.skipif(not ALEX.is_file(), reason="cal1 ALEX .pto not present")
def test_alex_s_vs_pr_islands_are_four_clusters():
    """S vs PR (an alias of E, looked up through it): donor-only, two FRET
    species and acceptor-only as clusters 0-3 of every burst."""
    from ndxplorer.analysis.projection_rank_model import ProjectionRankModel, build_context

    source, axes = real_source(ALEX)
    model = ProjectionRankModel(lambda: build_context(source, axes), True, runner=inline_runner)
    model.start()
    assert not model.error and model.rows
    names = ("Stoichiometry (PIE)", "Proximity ratio(PIE)")
    assert model.label_mode == "whole"
    found = model.island_clusters(names, source.column_values)
    cores = model.island_clusters(names, source.column_values, "cores")
    for f in (found, cores):
        assert f is not None and f.count == 4
        assert f.labels.size == source.size
        sizes = [int(np.sum(f.labels == k)) for k in range(4)]
        assert sizes == sorted(sizes, reverse=True) and min(sizes) > 0
    # whole islands: all but the ridges and the outliers/missing (~6 %)
    assert found.coverage > 0.9
    assert found.status() == (
        "4 islands of Stoichiometry (PIE) vs Proximity ratio(PIE) written as clusters "
        f"0\u20133; {round(100 * found.coverage)} % of bursts labelled, "
        f"{100 - round(100 * found.coverage)} % on ridges/outliers (\u22121)")
    p = found.probabilities
    assert np.all(p[found.labels < 0] == 0) and np.all(p[found.labels >= 0] >= 2 / 3 - 1e-9)
    assert np.quantile(p[found.labels >= 0], 0.05) < 0.95, "falls toward the ridges"
    # cores: the low-photon smear between the species is unassigned; every
    # core burst keeps its island in the whole labelling (numbered by size in
    # each, so up to a renumbering)
    assert 0.3 < cores.coverage < 0.7
    assert "outside the cores" in cores.status()
    both = cores.labels >= 0
    table = np.zeros((4, 4), dtype=int)
    np.add.at(table, (cores.labels[both], found.labels[both]), 1)
    assert np.count_nonzero(table) == 4 and np.all(table.max(axis=1) == table.sum(axis=1))
