"""The four methods that answer "what structure is in here?" share one dialog.

PCA, UMAP, HDBSCAN and K-means differ in what they return but not in how they
are used: pick columns, run, get new columns. They used to be presented as three
unrelated things -- a two-entry clustering dropdown, a permanently expanded UMAP
group box, and PCA with no way in at all.

These tests hold the unification in place, and pin the two bugs found while
building it: a missing backend reached for a widget that never existed, and the
stacked parameter pages sized the dialog to the tallest method rather than the
chosen one.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from qtpy import QtWidgets

from ndxplorer.core.data_source import DataSource
from ndxplorer.ui.clustering_dialog import (
    LABELS,
    METHODS,
    METHODS_BY_KEY,
    PROJECTION,
)


@pytest.fixture(scope="module")
def qt_app():
    """A single QApplication for the module (offscreen)."""
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


@pytest.fixture
def explorer(qt_app):
    """A window holding two well-separated populations.

    They differ in tau and E and in nothing else, so every method has a real
    answer to find and a wrong answer is recognisable rather than merely
    different.
    """
    from ndxplorer.core.plot_main import NDXplorer

    rng = np.random.default_rng(3)
    n = 1500
    frame = pd.DataFrame({
        "Tau (green)": np.concatenate([
            rng.normal(4.1, 0.15, n), rng.normal(2.0, 0.15, n)]),
        "Proximity ratio": np.concatenate([
            rng.normal(0.15, 0.04, n), rng.normal(0.62, 0.04, n)]),
        "r Experimental (green)": rng.normal(0.10, 0.02, 2 * n),
    })
    window = NDXplorer(data_source=DataSource(list(frame.columns), frame))
    yield window
    window.close()


@pytest.fixture
def dialog(explorer, qt_app):
    """The dialog, shown, with all columns chosen.

    It has to be *shown*: a child widget reports ``isVisible()`` False while its
    parent is hidden, however it was configured, so visibility assertions on a
    never-shown dialog would pass for the wrong reason and fail for the right
    one.
    """
    from ndxplorer.analysis import clustering_helpers

    clustering_helpers.ensure_dialog(explorer)
    dlg = explorer.clustering_dialog
    dlg._cluster_columns = set(explorer.data_source.data.columns)
    dlg.show()
    qt_app.processEvents()
    return dlg


def test_all_four_methods_are_offered(dialog):
    """One dropdown, four methods -- PCA included."""
    offered = {
        dialog.comboBoxClusteringMethod.itemData(i)
        for i in range(dialog.comboBoxClusteringMethod.count())
    }
    assert offered == {"pca", "umap", "hdbscan", "kmeans"}


@pytest.mark.parametrize("key", [m.key for m in METHODS])
def test_selecting_a_method_shows_only_its_parameters(dialog, key, qt_app):
    """Switching method must swap the parameter page, not stack them."""
    dialog.on_clustering_method_changed(key)
    qt_app.processEvents()

    assert dialog._cluster_method == key
    assert dialog.stackParameters.currentIndex() == dialog._pages[key]
    assert dialog.labelBlurb.text() == METHODS_BY_KEY[key].blurb


def test_the_dialog_shrinks_to_the_chosen_method(dialog, qt_app):
    """A stacked widget reserves room for its tallest page unless told not to.

    K-means has one spin box and UMAP has nine; without the size-policy handling
    the K-means page sits under a block of empty space the height of UMAP's form.
    """
    heights = {}
    for key in ("kmeans", "umap"):
        dialog.on_clustering_method_changed(key)
        qt_app.processEvents()
        dialog.adjustSize()
        qt_app.processEvents()
        heights[key] = dialog.height()

    assert heights["kmeans"] < heights["umap"], (
        f"the dialog did not shrink for the smaller method: {heights}"
    )


def test_actions_follow_the_family(dialog, qt_app):
    """Save writes a cluster assignment; a projection has none to write."""
    for method in METHODS:
        dialog.on_clustering_method_changed(method.key)
        qt_app.processEvents()
        if method.family == LABELS:
            assert dialog.pushButtonSaveClustering.isVisible()
        else:
            assert not dialog.pushButtonSaveClustering.isVisible()
        # Only UMAP has a standalone plot window.
        assert dialog.pushButtonPlotUMAP.isVisible() == (method.key == "umap")


def test_a_missing_backend_declines_instead_of_crashing(explorer, dialog, monkeypatch):
    """The unavailable-backend path used to raise AttributeError.

    It set ``dialog.checkBoxClustering``, a widget that has never existed in this
    dialog, so a genuinely absent backend produced a traceback rather than a
    clean refusal.
    """
    from ndxplorer.analysis import clustering_helpers

    monkeypatch.setattr(clustering_helpers, "get_hdbscan", lambda: None)
    monkeypatch.setattr(
        clustering_helpers, "_ensure_algorithm_available", lambda *a, **k: False
    )
    dialog._cluster_method = "hdbscan"

    clustering_helpers.apply_clustering(explorer)  # must not raise

    assert explorer.clustering_worker is None or not explorer.clustering_worker.isRunning()


def test_pca_adds_columns_and_reports_its_loadings(explorer, dialog, qt_app):
    """PCA's answer is the loadings, not the columns.

    The ``PC_n`` columns are how the answer gets plotted; which parameters carry
    the separation is what was asked. Both must come back.
    """
    dialog.on_clustering_method_changed("pca")
    dialog._cluster_columns = {"Tau (green)", "Proximity ratio",
                               "r Experimental (green)"}
    qt_app.processEvents()

    dialog.on_apply_clustering()
    qt_app.processEvents()

    columns = list(explorer.data_source.data.columns)
    assert "PC_1" in columns and "PC_2" in columns

    # The populations differ in tau and E only, so the leading component must be
    # built from those two and not from the noise column.
    assert dialog.labelResult.isVisible()
    reported = dialog.labelResult.text()
    assert "PC_1" in reported and "% of variance" in reported
    leading = reported.split("PC_2")[0]
    assert "Tau (green)" in leading and "Proximity ratio" in leading


def test_pca_recovers_the_planted_separation(explorer, qt_app):
    """The first component must actually separate the two populations."""
    from ndxplorer.analysis.pca_helpers import add_pca_columns

    result = add_pca_columns(
        explorer,
        ["Tau (green)", "Proximity ratio", "r Experimental (green)"],
        n_components=2,
    )
    assert result is not None

    scores = result.projections[:, 0]
    first, second = scores[:1500], scores[1500:]
    separation = abs(np.nanmean(first) - np.nanmean(second))
    spread = np.nanstd(scores)
    assert separation > 2.0 * spread * 0.5, (
        f"PC_1 did not separate the populations: gap {separation:.2f}, spread {spread:.2f}"
    )

    # tau and E must outweigh the noise column on PC_1.
    weights = dict(zip(result.columns, np.abs(result.loadings[0])))
    assert weights["Tau (green)"] > weights["r Experimental (green)"]
    assert weights["Proximity ratio"] > weights["r Experimental (green)"]


def test_hdbscan_finds_the_two_populations(explorer, dialog, qt_app):
    """End-to-end through the worker, on data with a known answer."""
    from qtpy import QtCore
    from ndxplorer.utils.lazy_imports import get_hdbscan

    if get_hdbscan() is None:
        pytest.skip("hdbscan backend not available")

    dialog.on_clustering_method_changed("hdbscan")
    dialog._cluster_columns = {"Tau (green)", "Proximity ratio"}
    dialog.spinBoxMinClusterSize.setValue(200)
    qt_app.processEvents()

    dialog.on_apply_clustering()
    deadline = QtCore.QTime.currentTime().addSecs(120)
    worker = explorer.clustering_worker
    while worker is not None and worker.isRunning() and QtCore.QTime.currentTime() < deadline:
        qt_app.processEvents()
    for _ in range(50):
        qt_app.processEvents()

    labels = explorer.data_source.data.get("Cluster Label")
    assert labels is not None, "clustering produced no label column"
    found = {int(v) for v in set(labels) if int(v) >= 0}
    assert len(found) == 2, f"expected two populations, got {sorted(set(labels))}"


def test_every_method_declares_what_it_needs(dialog):
    """The descriptors are what removed three copies of the install dance.

    If a method is added without them, the shared backend check silently has
    nothing to check.
    """
    for method in METHODS:
        assert method.family in (PROJECTION, LABELS)
        assert callable(method.probe)
        assert method.package and method.import_name
        assert method.blurb.endswith("."), f"{method.key} blurb reads as a fragment"
        assert method.min_columns >= 1
