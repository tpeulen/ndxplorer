"""The analysis feature of the emtk app: Find structure, UMAP, Gaussian Fit.

Driven through the scenario replay of :mod:`ndxplorer.app.capture` -- the
clicks and the capture ops the parity shots use -- and then asserted on the
app's state. Headless, no Qt; clustering runs as an :mod:`emtk.tasks` task.
"""

from __future__ import annotations

import sys

import numpy as np
import pytest

from ndxplorer.analysis import structure


def replay(steps, setup="iris_petals"):
    from ndxplorer.app import capture

    catalogue = capture.load_catalogue()
    run = capture.Replay({"id": "test", "setup": setup, "steps": steps}, catalogue)
    run.run()
    return run


def feature_of(run):
    return next(f for f in run.app.features if f.name == "analysis")


@pytest.fixture
def closing():
    runs = []
    yield runs.append
    for run in runs:
        run.app.close()


OPEN = {"op": "click", "widget": "pc.pushButtonShowClusteringDialog"}


def test_no_qt_is_imported():
    import subprocess

    code = ("import sys; import ndxplorer.app.features.analysis as a; "
            "print(any(m.split('.')[0] in ('PyQt5', 'PyQt6', 'PySide2', 'PySide6', 'qtpy') "
            "for m in sys.modules))")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert out.stdout.strip() == "False", out.stderr


def test_kmeans_labels_colour_and_isolate(closing):
    run = replay([OPEN, {"op": "call", "code": "d = win.clustering_dialog\n"
                         "d._cluster_columns = {'petal length', 'petal width'}\n"
                         "d._cluster_n_clusters = 3"},
                  {"op": "click", "widget": "button('Run', win.clustering_dialog)"},
                  {"op": "wait_until", "expr": "win._cluster_labels is not None"}])
    closing(run)
    feature, model = feature_of(run), run.app.model
    assert feature.structure.open
    assert feature.labels is not None and set(np.unique(feature.labels)) == {0, 1, 2}
    assert feature.cluster_labels is feature.labels      # the ranking's "Clusters" classes
    assert "Cluster Label" in model.parameter_names
    assert feature.structure.progress_text() == "Finished."
    assert feature.structure.enabled("save")
    # colour: the map is the cluster image
    run.app.panel.cluster_colours = True
    rgba = feature.map_image(model.map_values())
    assert rgba is not None and rgba.shape[2] == 4 and rgba[..., :3].any()
    # isolate one cluster
    total = model.count_current
    run.app.panel.selected_cluster = 1
    run.settle()
    assert 0 < model.count_current < total
    run.app.panel.selected_cluster = -1
    run.settle()
    assert model.count_current == total


def test_pca_reports_loadings_and_adds_columns(closing):
    run = replay([OPEN, {"op": "call", "code": "d = win.clustering_dialog\n"
                         "d.comboBoxClusteringMethod.setCurrentIndex("
                         "d.comboBoxClusteringMethod.findData('pca'))\n"
                         "d._cluster_columns = {'petal length', 'petal width', 'sepal length'}"},
                  {"op": "click", "widget": "button('Run', win.clustering_dialog)"},
                  {"op": "wait_until", "expr": "win.clustering_dialog.labelResult.isVisible()"}])
    closing(run)
    feature = feature_of(run)
    text = feature.structure.result_text()
    assert text.startswith("PC_1 — ") and "of variance" in text and "rows fitted" in text
    assert {"PC_1", "PC_2"} <= set(run.app.model.parameter_names)


def test_column_chooser_filters_selects_and_answers(closing):
    run = replay([OPEN, {"op": "click", "widget": "button('Columns', win.clustering_dialog)"}])
    closing(run)
    feature = feature_of(run)
    chooser = feature.modal[-1]
    chooser.filter = "petal"
    assert [r["name"] for r in chooser.column_rows()] == ["petal length", "petal width"]
    chooser.toggle_column(chooser.column_rows()[0], "use", True)
    chooser.select_all()
    assert chooser.chosen == set(run.app.model.parameter_names)
    chooser.deselect_all()
    chooser.toggle_column({"name": "petal width"}, "use", True)
    chooser.ok()
    assert feature.structure.columns == {"petal width"}
    assert feature.structure.columns_label() == "▦ Columns (1)"


def test_a_labelling_without_columns_asks_first(closing):
    run = replay([OPEN, {"op": "click", "widget": "button('Run', win.clustering_dialog)"}])
    closing(run)
    feature = feature_of(run)
    question = feature.modal[-1]
    assert question.title == "Select columns?"
    question.no()                    # use the axes
    feature.label_task.wait(60)
    run.settle()
    assert feature.labels is not None


def test_view_umap_opens_find_structure_on_umap(closing):
    run = replay([{"op": "trigger", "action": "actionUMAP"}])
    closing(run)
    feature = feature_of(run)
    assert feature.structure.open and feature.structure.method == "umap"


def test_missing_umap_offers_to_install_or_says_why(closing, monkeypatch):
    run = replay([OPEN])
    closing(run)
    feature = feature_of(run)
    umap = structure.METHODS_BY_KEY["umap"]
    object.__setattr__(umap, "probe", lambda: None)
    try:
        feature.structure.method = "umap"
        feature.structure.columns = {"petal length", "petal width"}
        feature.structure.run()
        question = feature.modal[-1]
        assert "not installed" in question.title and question.yes_label() == "Install"
        question.no()
        assert run.app.message[1] == ("Installation was cancelled or failed, so this method "
                                      "cannot run.")
        run.app.message = None
        monkeypatch.setattr(structure.sys, "platform", "emscripten")
        feature.structure.run()
        title, text = run.app.message
        assert "not available in the browser" in text and "numba" in text
    finally:
        from ndxplorer.utils.lazy_imports import get_umap

        object.__setattr__(umap, "probe", get_umap)


def test_umap_adds_columns_and_plots(closing, monkeypatch):
    """With a stand-in UMAP backend: the columns, the result line, the plot window."""
    import types

    class FakeUMAP:
        def __init__(self, n_components=2, **_kw):
            self.n = n_components

        def fit_transform(self, data):
            print("UMAP(fake)")
            return np.asarray(data)[:, :self.n] * 2.0

    fake = types.SimpleNamespace(UMAP=FakeUMAP)
    monkeypatch.setattr(structure, "get_umap", lambda: fake)
    umap = structure.METHODS_BY_KEY["umap"]
    object.__setattr__(umap, "probe", lambda: fake)
    try:
        run = replay([OPEN])
        closing(run)
        feature = feature_of(run)
        feature.structure.method = "umap"
        feature.structure.columns = {"petal length", "petal width", "sepal length"}
        feature.structure.run()
        feature.work_task.wait(30)
        run.settle(3)
        assert {"UMAP_1", "UMAP_2"} <= set(run.app.model.parameter_names)
        assert feature.structure.result_text().startswith("Added UMAP_1…UMAP_2")
        assert "UMAP(fake)" in feature.progress.log_text
        feature.structure.plot_umap()
        feature.work_task.wait(30)
        run.settle(3)
        assert feature.projection.open and feature.projection.embedding.shape[1] == 2
    finally:
        from ndxplorer.utils.lazy_imports import get_umap

        object.__setattr__(umap, "probe", get_umap)


def test_save_clustering_writes_the_folder(closing, tmp_path):
    run = replay([OPEN, {"op": "call", "code": "d = win.clustering_dialog\n"
                         "d._cluster_columns = {'petal length', 'petal width'}"},
                  {"op": "click", "widget": "button('Run', win.clustering_dialog)"},
                  {"op": "wait_until", "expr": "win._cluster_labels is not None"}])
    closing(run)
    feature = feature_of(run)
    feature.structure.save()
    run.app.io_service.answer(str(tmp_path))
    run.settle()
    written = {p.name for p in (tmp_path / "clustering").iterdir()}
    assert {"clustering_parameters.json", "cluster_labels.csv", "clustering_full_data.csv"} \
        <= written
    assert any(n.startswith("cluster_0") for n in written)


# ---------------------------------------------------------------- Gaussian Fit
GAUSS = [{"op": "trigger", "action": "actionFit_Gaussians", "checked": True},
         {"op": "canvas_click", "at": [0.62, 0.74]},
         {"op": "canvas_click", "at": [0.75, 0.92]}]


def test_gaussians_seed_fit_select_and_draw(closing):
    run = replay(GAUSS + [{"op": "click", "widget": "win.btnFit2DGauss"}], setup="mfd")
    closing(run)
    feature, model = feature_of(run), run.app.model
    panel = feature.gaussians
    assert run.app.docks.is_shown("Gaussian Fit") and run.app.panel.show_fit_gaussians
    components = panel.components()
    assert len(components) == 2
    assert components[0].fix_mu.all()              # a click holds the centre
    rows = panel.table.rows()
    assert len(rows) == 12 and rows[0]["name"] == "x1" and rows[2]["name"] == "σx,1"
    # select the first as a gate at 2 sigma
    panel.table.select(rows[0])
    panel.sigma = 2.0
    before = len(model.gates)
    panel.select()
    assert len(model.gates) == before + 1
    gate = model.gates[len(model.gates) - 1]
    assert gate.meta["sigma"] == 2.0 and gate.name.startswith("G2D(")
    assert panel.is_gate(0, panel.components()[0])
    run.settle()
    assert model.count_current < model.count_total


def test_gaussian_table_edits_links_and_deletes(closing):
    run = replay(GAUSS, setup="mfd")
    closing(run)
    panel = feature_of(run).gaussians
    table = panel.table

    def row(key):
        return next(r for r in table.rows() if r["key"] == key)

    table.edit(row("sd_x_1"), "value", "0.5")
    table.edit(row("sd_x_1"), "fixed", True)
    assert panel.components()[0].cov[0, 0] == pytest.approx(0.25)
    assert panel.components()[0].fix_cov[0, 0]
    table.edit(row("sd_x_1"), "hi", "0.4")          # a bound: Lo stays open
    assert (row("sd_x_1")["lo"], row("sd_x_1")["hi"]) == ("0", "0.4")
    assert panel.components()[0].cov[0, 0] == pytest.approx(0.16)
    table.edit(row("sd_x_1"), "hi", "∞")
    assert row("sd_x_1")["hi"] == "∞"
    assert "link" not in [c["key"] for c in table.columns()]
    table.parameter(row("sd_x_2")).link = table.parameter(row("sd_x_1"))
    assert panel.components()[1].cov[0, 0] == pytest.approx(0.25)
    assert row("sd_x_2")["link"] == "sd_x_1"
    assert "link" in [c["key"] for c in table.columns()]
    assert not table.cell_editable(row("sd_x_2"), "value")
    table.unlink(table.parameter(row("sd_x_2")))
    table.delete(row("sd_x_2"))
    table.delete(row("y_2"))
    run.settle()
    assert len(panel.components()) == 1          # one component, however many rows
    panel.add_component()
    assert len(panel.components()) == 2
    panel.clear()
    assert panel.components() == []


def test_gaussian_warnings(closing):
    run = replay([{"op": "trigger", "action": "actionFit_Gaussians"}], setup="mfd")
    closing(run)
    panel = feature_of(run).gaussians
    panel.fit()
    assert run.app.message[0] == "No Gaussians"


def test_gaussians_save_and_load(closing, tmp_path):
    run = replay(GAUSS, setup="mfd")
    closing(run)
    feature = feature_of(run)
    panel = feature.gaussians
    panel.save()
    run.app.io_service.answer(str(tmp_path / "mix.json"))
    run.settle()
    assert (tmp_path / "mix.json").exists() and (tmp_path / "mix_marginal_x.csv").exists()
    panel.clear()
    run.app.message = None
    panel.load_from(str(tmp_path / "mix_gaussians.csv"))
    assert len(panel.components()) == 2 and run.app.message is None
    run.app.panel.x_name = "Number of Photons"
    panel.load_from(str(tmp_path / "mix.json"))
    assert run.app.message[0] == "Axis Mismatch"


def test_gmm_settings_dialog_saves(closing, tmp_path, monkeypatch):
    import pathlib

    monkeypatch.setattr(pathlib.Path, "home", classmethod(lambda cls: tmp_path))
    run = replay([{"op": "trigger", "action": "actionFit_Gaussians"},
                  {"op": "click", "widget": "win.btnGMMSettings"}], setup="mfd")
    closing(run)
    feature = feature_of(run)
    dialog = feature.modal[-1]
    assert dialog.title == "GMM Settings" and dialog.max_iter == 200
    dialog.max_iter = 17
    dialog.ok()
    from ndxplorer.analysis import gaussian_mixture as gm

    assert gm.load_gmm_settings()["max_iter"] == 17
    assert feature.gaussians.gmm_settings()["max_iter"] == 17
