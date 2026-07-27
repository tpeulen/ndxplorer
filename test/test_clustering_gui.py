"""Clustering through the GUI: dialog, worker thread, and write-back.

The API tests in ``test_clustering_and_pca.py`` prove the algorithms recover
planted structure. That is not the same as the tool working: between the
algorithm and the user sit a dialog that holds the parameters, a ``QThread``
that runs the fit, and a completion handler that puts the labels somewhere the
plot can find them. An analysis can be perfectly correct and still never arrive.

These tests drive that path with a real ``NDXplorer`` window under the offscreen
Qt platform — including HDBSCAN, which was unreachable until ``get_hdbscan``
learned to fall back to scikit-learn.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from qtpy import QtWidgets

from ndxplorer.analysis import clustering_helpers as helpers
from ndxplorer.core.data_source import DataSource


@pytest.fixture(scope="module")
def qt_app():
    """A single QApplication for the module (offscreen)."""
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    yield app


@pytest.fixture
def explorer(qt_app):
    """A real NDXplorer window holding three well-separated blobs."""
    from ndxplorer.core.plot_main import NDXplorer

    rng = np.random.default_rng(0)
    blocks, truth = [], []
    for i, (cx, cy) in enumerate([(0.0, 0.0), (8.0, 0.0), (0.0, 8.0)]):
        blocks.append(np.column_stack([rng.normal(cx, 0.3, 100), rng.normal(cy, 0.3, 100)]))
        truth.append(np.full(100, i))
    data = np.vstack(blocks)
    frame = pd.DataFrame({"x": data[:, 0], "y": data[:, 1],
                          "truth": np.concatenate(truth)})
    window = NDXplorer(data_source=DataSource(list(frame.columns), frame))
    yield window
    window.close()


def run_clustering(window, qt_app, method, columns=("x", "y"),
                   timeout_ms=30_000, **params):
    """Drive the dialog exactly as a click would, and wait for the worker.

    Returns the labels the *completion handler* stored on the window — the thing
    the plot reads — not the worker's return value, so a break anywhere in the
    signal chain shows up here.
    """
    from qtpy import QtCore

    helpers.ensure_dialog(window)
    dialog = window.clustering_dialog
    dialog._cluster_method = method
    dialog._cluster_columns = set(columns)
    for key, value in params.items():
        setattr(dialog, f"_cluster_{key}", value)

    window._cluster_labels = None
    helpers.apply_clustering(window)

    worker = getattr(window, "clustering_worker", None)
    assert worker is not None, "apply_clustering did not create a worker"

    deadline = QtCore.QElapsedTimer()
    deadline.start()
    while worker.isRunning() and deadline.elapsed() < timeout_ms:
        qt_app.processEvents()
    worker.wait(timeout_ms)
    # Let the queued completion signal be delivered on this thread.
    for _ in range(50):
        qt_app.processEvents()
    return getattr(window, "_cluster_labels", None)


def purity(labels, truth):
    """Fraction of points whose cluster is that cluster's majority true label."""
    labels = np.asarray(labels)
    correct = 0
    for c in np.unique(labels):
        if c < 0:
            continue
        members = truth[labels == c]
        if members.size:
            correct += int(np.bincount(members).max())
    return correct / len(truth)


# ──────────────────────────────────────────────────────────────────────────────
# The dialog exists and is wired
# ──────────────────────────────────────────────────────────────────────────────
def test_the_clustering_dialog_can_be_opened(explorer):
    """``ensure_dialog`` must build a dialog with the parameters the worker reads."""
    helpers.ensure_dialog(explorer)
    dialog = explorer.clustering_dialog
    assert dialog is not None
    for attribute in ("_cluster_method", "_cluster_columns", "_cluster_min_samples",
                      "_cluster_min_cluster_size", "_cluster_n_clusters"):
        assert hasattr(dialog, attribute), f"dialog is missing {attribute}"


def test_the_algorithm_availability_check_passes_for_both_methods(explorer):
    """The guard in front of the worker must not reject an installed backend.

    This is the GUI face of the HDBSCAN regression: ``_ensure_algorithm_available``
    is what turned the checkbox back off and abandoned the run.
    """
    assert helpers._ensure_algorithm_available(explorer, "kmeans")
    assert helpers._ensure_algorithm_available(explorer, "hdbscan"), (
        "the GUI still believes HDBSCAN is unavailable"
    )


# ──────────────────────────────────────────────────────────────────────────────
# End to end through the worker thread
# ──────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("method,params", [
    ("kmeans", {"n_clusters": 3}),
    ("hdbscan", {"min_samples": 5, "min_cluster_size": 20}),
])
def test_clustering_through_the_gui_reaches_the_window(explorer, qt_app, method, params):
    """Click to labels: the whole chain, with the planted answer as the check."""
    labels = run_clustering(explorer, qt_app, method, **params)

    assert labels is not None, f"{method}: no labels reached the window"
    truth = explorer.data_source.data["truth"].values.astype(int)
    assert len(labels) == len(truth)
    found = {int(c) for c in np.unique(labels) if c >= 0}
    assert len(found) == 3, f"{method} found {len(found)} clusters, planted 3"
    assert purity(labels, truth) > 0.95


def test_the_clustering_flag_is_set_so_the_plot_uses_the_labels(explorer, qt_app):
    """Labels that nothing consumes are labels nobody sees."""
    run_clustering(explorer, qt_app, "kmeans", n_clusters=3)
    assert explorer._use_clustering is True
    assert getattr(explorer, "_cluster_probabilities", None) is not None


def test_a_second_run_replaces_the_first(explorer, qt_app):
    """Re-running must not leave the previous worker connected.

    ``apply_clustering`` disconnects and deletes the old worker; if that broke,
    the completion signal would fire twice and the second result could be
    overwritten by the first.
    """
    two = run_clustering(explorer, qt_app, "kmeans", n_clusters=2)
    assert len({int(c) for c in np.unique(two) if c >= 0}) == 2

    three = run_clustering(explorer, qt_app, "kmeans", n_clusters=3)
    assert len({int(c) for c in np.unique(three) if c >= 0}) == 3


def test_clustering_can_be_cancelled(explorer, qt_app):
    """Cancelling must stop the worker without wedging the window."""
    helpers.ensure_dialog(explorer)
    explorer.clustering_dialog._cluster_method = "kmeans"
    explorer.clustering_dialog._cluster_columns = {"x", "y"}
    explorer.clustering_dialog._cluster_n_clusters = 3
    helpers.apply_clustering(explorer)
    helpers.cancel_clustering(explorer)

    worker = explorer.clustering_worker
    worker.wait(30_000)
    for _ in range(50):
        qt_app.processEvents()
    assert not worker.isRunning()


# ──────────────────────────────────────────────────────────────────────────────
# PCA through the same window
# ──────────────────────────────────────────────────────────────────────────────
def test_pca_columns_appear_on_a_real_window(explorer):
    """``add_pca_columns`` must extend the live table and refresh the axes."""
    from ndxplorer.analysis.pca_helpers import add_pca_columns

    before = set(explorer.data_source.data.columns)
    result = add_pca_columns(explorer, ["x", "y"], n_components=2)

    assert result is not None
    after = set(explorer.data_source.data.columns)
    assert {"PC_1", "PC_2"} <= after - before
    frame = explorer.data_source.data
    assert np.isfinite(frame["PC_1"].values).all()
    assert result.explained_variance_ratio.sum() <= 1.0 + 1e-9


def test_pca_then_clustering_composes(explorer, qt_app):
    """Cluster the projection, which is the reason to compute it in the table.

    PCA earns its place by making the structure easier to separate, so the two
    have to work on the same table: the components must be present as columns
    the clustering dialog can select.
    """
    from ndxplorer.analysis.pca_helpers import add_pca_columns

    assert add_pca_columns(explorer, ["x", "y"], n_components=2) is not None
    labels = run_clustering(explorer, qt_app, "kmeans",
                            columns=("PC_1", "PC_2"), n_clusters=3)

    assert labels is not None, "clustering could not use the PCA columns"
    truth = explorer.data_source.data["truth"].values.astype(int)
    assert purity(labels, truth) > 0.95


# ──────────────────────────────────────────────────────────────────────────────
# Axis selection: the label and the data must agree
# ──────────────────────────────────────────────────────────────────────────────
def test_choosing_an_axis_by_name_plots_that_parameter(explorer, qt_app):
    """The plotted values must follow the axis *name*, not a stale index.

    The axis combo boxes are editable, and Qt's ``setCurrentText`` on an
    editable combo changes the line-edit text without moving ``currentIndex``
    when the insert policy forbids inserting. The plotted values are taken from
    the index and the axis label from the text, so before this was fixed a user
    typing a valid parameter name got **another parameter's data under the
    right label** — a wrong plot with nothing visibly wrong about it.
    """
    control = explorer.plot_control
    control.update(update_comboboxes=True, update_plots=False)
    qt_app.processEvents()

    control.comboBoxSelX.setCurrentText("x")
    control.comboBoxSelY.setCurrentText("truth")
    qt_app.processEvents()

    frame = explorer.data_source.data
    assert control.p2[1] == "truth"
    # p2's index must point at the column its name names.
    assert control.p2[0] == list(frame.columns).index("truth")
    assert float(np.asarray(explorer.y_values).mean()) == pytest.approx(
        float(frame["truth"].mean()), abs=1e-3
    ), "the y axis is labelled 'truth' but is plotting something else"


def test_axis_selection_by_index_still_works(explorer, qt_app):
    """The ordinary path — picking an item — must be unaffected by the fix."""
    control = explorer.plot_control
    control.update(update_comboboxes=True, update_plots=False)
    qt_app.processEvents()

    columns = list(explorer.data_source.data.columns)
    control.comboBoxSelY.setCurrentIndex(columns.index("y"))
    qt_app.processEvents()

    assert control.p2 == (columns.index("y"), "y")
    assert float(np.asarray(explorer.y_values).mean()) == pytest.approx(
        float(explorer.data_source.data["y"].mean()), abs=1e-3
    )
