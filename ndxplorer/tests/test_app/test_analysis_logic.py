"""The Qt-free logic behind Find structure and the Gaussian Fit panel.

Both GUIs call :mod:`ndxplorer.analysis.structure` and
:mod:`ndxplorer.analysis.gaussian_mixture`; these tests pin the behaviour the
emtk port relies on, headless and without Qt.
"""
from __future__ import annotations

import json

import numpy as np
import pytest

from ndxplorer.analysis import gaussian_mixture as gm
from ndxplorer.analysis import structure


def three_blobs(n=200, seed=1):
    rng = np.random.default_rng(seed)
    centres = np.array([[0.0, 0.0], [5.0, 5.0], [0.0, 6.0]])
    data = np.vstack([rng.normal(c, 0.4, size=(n, 2)) for c in centres])
    return data, np.repeat(np.arange(3), n)


# --------------------------------------------------------------- structure
@pytest.mark.parametrize("method,params", [("kmeans", {"n_clusters": 3}),
                                           ("hdbscan", {"min_samples": 5,
                                                        "min_cluster_size": 30})])
def test_label_points_runs_as_an_emtk_task(method, params):
    from emtk import tasks

    data, _truth = three_blobs()
    data[7] = np.nan
    task = tasks.start(structure.label_points, data, method, params, mode="cooperative")
    task.wait(timeout=60)
    assert task.state == "done", task.error
    labels, probabilities = task.result
    assert len(labels) == len(data) == len(probabilities)
    assert labels[7] == -1
    assert len({int(v) for v in labels if v >= 0}) == 3
    assert task.progress == 1.0


def test_label_points_refuses_too_few_rows():
    from emtk import tasks

    task = tasks.start(structure.label_points, np.zeros((2, 2)), "kmeans", {"n_clusters": 5},
                       mode="inline")
    assert task.state == "failed" and "Not enough data" in task.error


def test_a_cancelled_labelling_returns_nothing():
    from emtk import tasks

    data, _ = three_blobs()
    task = tasks.start(structure.label_points, data, "kmeans", {"n_clusters": 3},
                       mode="cooperative")
    task.cancel()
    task.poll()
    assert task.state == "cancelled" and task.result is None


def test_methods_say_why_they_cannot_run(monkeypatch):
    umap = structure.METHODS_BY_KEY["umap"]
    monkeypatch.setattr(structure.sys, "platform", "emscripten")
    object.__setattr__(umap, "probe", lambda: None)
    try:
        assert "not available in the browser" in umap.unavailable()
        assert "numba" in umap.unavailable()
    finally:
        from ndxplorer.utils.lazy_imports import get_umap

        object.__setattr__(umap, "probe", get_umap)


def test_pca_report_names_the_loadings():
    from ndxplorer.analysis.pca_helpers import compute_pca

    rng = np.random.default_rng(0)
    a = rng.normal(size=500)
    data = np.column_stack([a, 2 * a + 0.01 * rng.normal(size=500), rng.normal(size=500)])
    result = compute_pca(data, ["a", "b", "c"], n_components=2)
    lines, footer = structure.pca_report(result)
    assert [head for head, _ in lines] == ["PC_1", "PC_2"]
    assert "of variance" in lines[0][1] and "a (" in lines[0][1]
    assert "500 rows fitted" in footer


def test_umap_params_drop_unset_epochs():
    params = structure.prepare_umap_params({"n_neighbors": 7, "n_epochs": None, "n_jobs": 1})
    assert params["n_neighbors"] == 7 and "n_epochs" not in params
    assert params["random_state"] == 42


# ---------------------------------------------------------- gaussian mixture
def test_seed_reads_the_histogram_the_right_way_round():
    """H is (n_y, n_x); a click seeds a Gaussian whose width is the local spread
    there, not at the transposed bin."""
    x_edges = np.linspace(0, 10, 21)
    y_edges = np.linspace(0, 1, 11)
    H = np.zeros((10, 20))
    H[2, 15] = 10.0          # y bin 2, x bin 15 (x ~ 7.75, y ~ 0.25)
    H[2, 16] = 10.0
    mu, cov = gm.seed_component(H, x_edges, y_edges, 7.7, 0.23, window=2)
    assert mu == pytest.approx((7.75, 0.25))
    assert cov[0, 0] == pytest.approx(0.0625)     # two x bins 0.5 apart
    assert cov[1, 1] == pytest.approx(0.0, abs=1e-12)
    assert gm.seed_component(H, x_edges, y_edges, 11.0, 0.5) is None


def test_fit_recovers_two_populations_and_holds_what_is_fixed():
    from ndxplorer.core import gaussian_parameters as gp

    rng = np.random.default_rng(3)
    a = rng.multivariate_normal([2.0, 0.3], [[0.1, 0.0], [0.0, 0.002]], 3000)
    b = rng.multivariate_normal([4.0, 0.7], [[0.2, -0.01], [-0.01, 0.004]], 1000)
    pts = np.vstack([a, b])
    group = gp.build_gaussian_group()
    group.append((2.2, 0.35), np.diag([0.2, 0.004]), fixed={"x": True})
    group.append((3.8, 0.65), np.diag([0.2, 0.004]))
    fitted = gm.fit_mixture(group.components(), pts[:, 0], pts[:, 1], (0, 6), (0, 1))
    (mu1, _c1, w1), (mu2, _c2, w2) = fitted
    assert mu1[0] == pytest.approx(2.2)                  # held
    assert mu2 == pytest.approx([4.0, 0.7], abs=0.05)
    assert w1 > w2


def test_fit_says_what_is_missing():
    with pytest.raises(gm.GaussianFitError) as err:
        gm.fit_mixture([], [1.0], [1.0], (0, 1), (0, 1))
    assert err.value.title == "No Gaussians"

    class C:
        mu, cov, w = np.zeros(2), np.eye(2), 1.0
        fix_mu, fix_cov, fix_w = np.zeros(2, bool), np.zeros((2, 2), bool), False

    with pytest.raises(gm.GaussianFitError) as err:
        gm.fit_mixture([C()], [5.0], [5.0], (0, 1), (0, 1))
    assert err.value.title == "No data"


def test_ellipse_is_the_sigma_contour():
    xs, ys = gm.ellipse((1.0, 2.0), np.diag([4.0, 1.0]), sigma=2.0)
    r = ((xs - 1.0) / 2.0) ** 2 + (ys - 2.0) ** 2
    assert np.allclose(r, 4.0)
    xs, ys = gm.ellipse((10.0, 2.0), np.diag([1.0, 1.0]), log_x=True)
    assert np.all(xs > 0)


def test_marginal_curves_integrate_to_the_counts():
    edges = np.linspace(-5, 5, 101)
    counts = np.full(100, 10.0)
    (xc, gx, yc, gy), = gm.component_marginals([((0.0, 0.0), np.eye(2), 1.0)],
                                               edges, counts, edges, counts)
    assert gx.sum() == pytest.approx(1000.0, rel=1e-3)


def test_save_and_load_round_trip(tmp_path):
    from ndxplorer.core import gaussian_parameters as gp

    group = gp.build_gaussian_group()
    group.append((1.0, 2.0), np.array([[0.25, 0.05], [0.05, 0.16]]), 0.7, fixed={"x": True})
    group.append((3.0, 1.0), np.diag([0.5, 0.2]), 0.3)
    rows = [(c.mu, c.cov, c.w) for c in group.components()]
    axes = {"x": {"index": 0, "name": "A", "scale": "linear"},
            "y": {"index": 1, "name": "B", "scale": "linear"}, "fit_in_log": False}
    H = np.ones((4, 5))
    written = gm.save_gaussians(str(tmp_path / "mix.json"), group.records(), rows, axes, H,
                                np.linspace(0, 5, 6), np.linspace(0, 4, 5))
    assert len(written) == 6
    data = json.loads((tmp_path / "mix.json").read_text())
    assert data["marginals"]["x"]["data"] == [4.0] * 5          # summed over y
    for name in ("mix.json", "mix_gaussians.csv"):
        loaded, meta = gm.load_gaussians(str(tmp_path / name))
        assert len(loaded) == 2
        mu, cov, w, fx, fy, *_ = loaded[0]
        assert mu == pytest.approx([1.0, 2.0]) and cov[0, 1] == pytest.approx(0.05)
        assert fx and not fy and w == pytest.approx(0.7)
    loaded, meta = gm.load_gaussians(str(tmp_path / "mix.json"))
    assert gm.axis_mismatch(meta, axes) is None
    other = dict(axes, x={"index": 3, "name": "C", "scale": "log"})
    assert "Gaussians were loaded regardless" in gm.axis_mismatch(meta, other)


def test_gmm_settings_round_trip(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    import pathlib

    monkeypatch.setattr(pathlib.Path, "home", classmethod(lambda cls: tmp_path))
    cfg = gm.load_gmm_settings()
    assert cfg == gm.GMM_DEFAULTS
    cfg["max_iter"] = 55
    cfg["fix_new_means"] = False
    assert gm.save_gmm_settings(cfg)
    again = gm.load_gmm_settings()
    assert again["max_iter"] == 55 and again["fix_new_means"] is False
