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
    window = NDXplorer(data_source=DataSource.from_columns(
        {"x": data[:, 0], "y": data[:, 1], "truth": np.concatenate(truth)}))
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


def wait_for_2d_histogram(window, qt_app, timeout_ms=20_000):
    """Pump events until the 2-D histogram exists.

    Histograms are computed off the GUI thread, so a freshly built window has
    none for a while and ``update_2d_plot`` returns early against the 10x10
    placeholder. Without this wait the colour test is a race that passes alone
    and fails behind other tests.
    """
    from qtpy import QtCore

    deadline = QtCore.QElapsedTimer()
    deadline.start()
    while deadline.elapsed() < timeout_ms:
        if window._histogram.get("2d") is not None:
            return True
        qt_app.processEvents()
    return False


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
    truth = explorer.data_source.column_values("truth").astype(int)
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

    before = set(explorer.data_source.parameter_names)
    result = add_pca_columns(explorer, ["x", "y"], n_components=2)

    assert result is not None
    after = set(explorer.data_source.parameter_names)
    assert {"PC_1", "PC_2"} <= after - before
    assert np.isfinite(explorer.data_source.column_values("PC_1")).all()
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
    truth = explorer.data_source.column_values("truth").astype(int)
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

    source = explorer.data_source
    assert control.p2[1] == "truth"
    # p2's index must point at the column its name names.
    assert control.p2[0] == source.parameter_names.index("truth")
    assert float(np.asarray(explorer.y_values).mean()) == pytest.approx(
        float(source.column_values("truth").mean()), abs=1e-3
    ), "the y axis is labelled 'truth' but is plotting something else"


def test_axis_selection_by_index_still_works(explorer, qt_app):
    """The ordinary path — picking an item — must be unaffected by the fix."""
    control = explorer.plot_control
    control.update(update_comboboxes=True, update_plots=False)
    qt_app.processEvents()

    columns = list(explorer.data_source.parameter_names)
    control.comboBoxSelY.setCurrentIndex(columns.index("y"))
    qt_app.processEvents()

    assert control.p2 == (columns.index("y"), "y")
    assert float(np.asarray(explorer.y_values).mean()) == pytest.approx(
        float(explorer.data_source.column_values("y").mean()), abs=1e-3
    )


# ──────────────────────────────────────────────────────────────────────────────
# Colouring the map by cluster
# ──────────────────────────────────────────────────────────────────────────────
@pytest.fixture
def unit_explorer(qt_app):
    """A window whose data lies inside the default 0..1 axis range.

    The 2-D histogram is built over the axis *range* controls, which default to
    0..1. The main fixture's blobs sit at 0 and 8, so only the corner of the map
    is binned — fine for the clustering tests, useless for checking that every
    cluster gets its own colour.
    """
    from ndxplorer.core.plot_main import NDXplorer

    rng = np.random.default_rng(0)
    blocks, truth = [], []
    for i, (cx, cy) in enumerate([(0.2, 0.3), (0.8, 0.3), (0.5, 0.8)]):
        blocks.append(np.column_stack([rng.normal(cx, 0.03, 120),
                                       rng.normal(cy, 0.03, 120)]))
        truth.append(np.full(120, i))
    data = np.vstack(blocks)
    window = NDXplorer(data_source=DataSource.from_columns(
        {"x": data[:, 0], "y": data[:, 1], "truth": np.concatenate(truth)}))
    yield window
    window.close()


def test_the_colour_toggle_produces_a_cluster_image(unit_explorer, qt_app):
    """Ticking the box must yield a multi-coloured RGB image of the clusters.

    This asserts the two things the toggle controls -- the *decision* to colour,
    and the image that decision produces -- directly, rather than through the
    repaint. The repaint itself is deliberately not asserted here: histograms
    are computed off the GUI thread and clustering invalidates them, so the
    moment the new image lands depends on background timing, and a test that
    waits for it is a race that passes alone and fails behind other tests. That
    path is verified by rendering the window and looking at it.
    """
    control = unit_explorer.plot_control
    control.update(update_comboboxes=True, update_plots=True)
    assert wait_for_2d_histogram(unit_explorer, qt_app)
    control.comboBoxSelX.setCurrentText("x")
    control.comboBoxSelY.setCurrentText("y")
    control.update(update_comboboxes=False, update_plots=True)
    assert wait_for_2d_histogram(unit_explorer, qt_app)

    run_clustering(unit_explorer, qt_app, "kmeans", n_clusters=3)
    assert unit_explorer._cluster_labels is not None

    assert hasattr(control, "checkBoxColorClusters")
    assert unit_explorer._wants_cluster_colors() is False, "off by default"
    control.checkBoxColorClusters.setChecked(True)
    qt_app.processEvents()
    assert unit_explorer._wants_cluster_colors() is True

    edges = np.linspace(0.0, 1.0, 31)
    image = unit_explorer._cluster_color_image(edges, edges)
    assert image is not None and image.ndim == 3 and image.shape[-1] == 3
    hues = {tuple(c) for c in image.reshape(-1, 3) if int(c.sum()) > 0}
    assert len(hues) > 1, "every cluster was drawn in the same colour"

    control.checkBoxColorClusters.setChecked(False)
    qt_app.processEvents()
    assert unit_explorer._wants_cluster_colors() is False


def test_the_colour_toggle_sits_beside_the_cluster_spinner(unit_explorer):
    """The toggle must land next to the spinner, not in an unrelated corner.

    It is added in code rather than in the .ui file, and the first attempt put
    it at the top of the panel because ``indexOf`` was asked of the wrong
    (outer) layout.
    """
    control = unit_explorer.plot_control
    box = control.checkBoxColorClusters
    spinner = control.spinBoxCluster
    assert box.parentWidget() is not None
    shared = [
        layout for layout in control.findChildren(QtWidgets.QGridLayout)
        if layout.indexOf(spinner) >= 0 and layout.indexOf(box) >= 0
    ]
    assert shared, "the colour toggle is not in the same layout as the cluster spinner"

    layout = shared[0]
    spin_row, spin_col, _, _ = layout.getItemPosition(layout.indexOf(spinner))
    box_row, box_col, _, _ = layout.getItemPosition(layout.indexOf(box))
    assert box_row == spin_row and box_col == spin_col + 1, (
        f"toggle at ({box_row}, {box_col}) is not beside the spinner "
        f"at ({spin_row}, {spin_col})"
    )


def test_colouring_without_clusters_falls_back_to_density(explorer, qt_app):
    """Ticking the box before clustering must not blank or break the plot."""
    control = explorer.plot_control
    control.update(update_comboboxes=True, update_plots=True)
    wait_for_2d_histogram(explorer, qt_app)
    explorer._cluster_labels = None

    assert explorer._wants_cluster_colors() is False
    control.checkBoxColorClusters.setChecked(True)
    for _ in range(120):
        qt_app.processEvents()
    data = explorer.g_2dplot.data
    assert data is not None and data.ndim == 2
