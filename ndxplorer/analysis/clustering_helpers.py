"""Utilities for managing the clustering dialog, column selection, and worker lifecycle."""

from __future__ import annotations

from typing import Optional, Set, Dict, Any, Tuple

import numpy as np
from qtpy import QtWidgets

from ..logging_config import logging
from ..ui.clustering_dialog import ClusteringDialog
from ..ui.column_selection_dialog import ColumnSelectionDialog
from ..analysis.clustering import ClusteringManager, ClusteringWorker
from .structure import METHODS_BY_KEY

if False:  # pragma: no cover
    from ..core.plot_main import NDXplorer


def setup_button(ndxplorer: "NDXplorer") -> None:
    """Wire the Clustering button to show the dialog."""
    ndxplorer.pushButtonShowClusteringDialog.clicked.connect(
        lambda: toggle_dialog(ndxplorer)
    )


def ensure_dialog(ndxplorer: "NDXplorer") -> None:
    """Create the clustering dialog if missing and wire signals."""
    if getattr(ndxplorer, "clustering_dialog", None) is not None:
        return

    dialog = ClusteringDialog(parent=ndxplorer)
    ndxplorer.clustering_dialog = dialog
    update_dialog(ndxplorer, force=True)
    dialog.clustering_done.connect(ndxplorer.on_clustering_done)
    dialog.clustering_error.connect(ndxplorer.on_clustering_error)
    dialog.progress_updated.connect(ndxplorer.on_clustering_progress)


def toggle_dialog(ndxplorer: "NDXplorer") -> None:
    """Show or hide the clustering dialog."""
    ensure_dialog(ndxplorer)
    dialog = ndxplorer.clustering_dialog
    if dialog.isVisible():
        dialog.hide()
    else:
        update_dialog(ndxplorer)
        dialog.show()


def update_dialog(ndxplorer: "NDXplorer", force: bool = False) -> None:
    """Update dialog labels/buttons with latest state."""
    dialog = getattr(ndxplorer, "clustering_dialog", None)
    if dialog is None:
        return
    if not force and not dialog.isVisible():
        return
    try:
        num_selected = len(dialog._cluster_columns)
        if num_selected > 0:
            dialog.pushButtonSelectColumns.setText(
                f"Select Columns (Recommended) ({num_selected})"
            )
        else:
            dialog.pushButtonSelectColumns.setText("Select Columns (Recommended)")
        dialog.pushButtonSaveClustering.setEnabled(
            getattr(ndxplorer, "_cluster_labels", None) is not None
        )
    except RuntimeError:
        logging.warning("Clustering dialog widgets unavailable; recreating dialog.")
        ndxplorer.clustering_dialog = None
        ensure_dialog(ndxplorer)


def select_columns(ndxplorer: "NDXplorer") -> None:
    """Open the column selection dialog (from either parent or embedded dialog)."""
    ensure_dialog(ndxplorer)
    dialog = ndxplorer.clustering_dialog
    if dialog.isVisible():
        dialog.on_select_columns()
        return

    parameter_names = ndxplorer.data_source.parameter_names
    selection_dialog = ColumnSelectionDialog(
        parent=ndxplorer,
        column_names=parameter_names,
        selected_columns=dialog._cluster_columns,
    )
    if selection_dialog.exec_():
        dialog._cluster_columns = selection_dialog.get_selected_columns()
        update_dialog(ndxplorer, force=True)


def start_clustering_from_dialog(
    ndxplorer: "NDXplorer", method: str, columns: Set[str], params: Dict[str, Any]
) -> None:
    """Apply dialog-driven settings then defer to apply_clustering."""
    ensure_dialog(ndxplorer)
    dialog = ndxplorer.clustering_dialog
    dialog._cluster_method = method
    dialog._cluster_columns = columns
    apply_clustering(ndxplorer)


def _ensure_algorithm_available(ndxplorer: "NDXplorer", method: str) -> bool:
    """Whether *method* can run; says why not in a message box when it cannot.

    HDBSCAN and K-means are tttrlib's kernels, a dependency that ships with the
    application, so there is nothing to offer to install: a failure here means a
    broken or too-old installation.
    """
    entry = METHODS_BY_KEY.get(method)
    if entry is None or entry.available():
        return True
    QtWidgets.QMessageBox.warning(ndxplorer, f"{entry.title} Not Available", entry.unavailable())
    return False


def apply_clustering(ndxplorer: "NDXplorer") -> None:
    """Start clustering worker using current dialog selections."""
    ensure_dialog(ndxplorer)
    ndxplorer._use_clustering = True
    dialog = ndxplorer.clustering_dialog
    method = dialog._cluster_method
    columns = dialog._cluster_columns

    if not _ensure_algorithm_available(ndxplorer, method):
        # No checkbox to untick: this used to set ``dialog.checkBoxClustering``,
        # a widget that has never existed, so a genuinely missing backend raised
        # AttributeError here instead of declining cleanly.
        dialog.clustering_completed(success=False)
        return

    params: Dict[str, Any]
    if method == "hdbscan":
        params = {
            "min_samples": dialog._cluster_min_samples,
            "min_cluster_size": dialog._cluster_min_cluster_size,
        }
    elif method == "kmeans":
        params = {"n_clusters": dialog._cluster_n_clusters}
    else:
        params = {}

    worker = getattr(ndxplorer, "clustering_worker", None)
    if worker is not None:
        try:
            worker.clustering_done.disconnect(ndxplorer.on_clustering_done)
            worker.clustering_error.disconnect(ndxplorer.on_clustering_error)
            worker.progress_updated.disconnect(ndxplorer.on_clustering_progress)
        except (TypeError, RuntimeError):
            pass
        if worker.isRunning():
            worker.wait()
        worker.deleteLater()

    ndxplorer.clustering_worker = ClusteringWorker(ndxplorer, method, params)
    ndxplorer.clustering_worker.clustering_done.connect(ndxplorer.on_clustering_done)
    ndxplorer.clustering_worker.clustering_error.connect(
        ndxplorer.on_clustering_error
    )
    ndxplorer.clustering_worker.progress_updated.connect(
        ndxplorer.on_clustering_progress
    )
    ndxplorer.clustering_worker.start()


def store_clustering_result(ndxplorer: "NDXplorer", labels, probabilities) -> None:
    """Write cluster columns into the table and refresh the axis combo boxes.

    **GUI thread only.** It changes the table the plots are drawn from and then
    updates the plot control, neither of which is safe from a worker thread.
    """
    source = ndxplorer.data_source
    source.set_column("Cluster Label", np.asarray(labels))
    source.set_column("Cluster Probability", np.asarray(probabilities, dtype=np.float64))
    try:
        ndxplorer.plot_control.update(update_comboboxes=True, update_plots=False)
    except Exception:  # pragma: no cover - headless use may have no plot control
        logging.debug("could not refresh the plot control", exc_info=True)
    logging.info("Cluster columns added and axis combo boxes refreshed")


def cancel_clustering(ndxplorer: "NDXplorer") -> None:
    """Request the worker to stop and update dialog state."""
    worker = getattr(ndxplorer, "clustering_worker", None)
    if worker is not None and worker.isRunning():
        worker.stop()
        dialog = getattr(ndxplorer, "clustering_dialog", None)
        if dialog is not None and dialog.isVisible():
            dialog.pushButtonCancelClustering.setText("Cancelling...")
            dialog.pushButtonCancelClustering.setEnabled(False)


def perform_clustering(
    ndxplorer: "NDXplorer",
    method: Optional[str] = None,
    worker=None,
    **kwargs,
) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
    """
    Execute clustering via ClusteringManager and update ndxplorer state.
    """
    if not hasattr(ndxplorer, "_clustering_manager"):
        ndxplorer._clustering_manager = ClusteringManager(ndxplorer.data_source)
    else:
        ndxplorer._clustering_manager._data_source = ndxplorer.data_source

    if method is None:
        method = ndxplorer.clustering_dialog._cluster_method

    if method == "hdbscan":
        min_samples = kwargs.get(
            "min_samples", ndxplorer.clustering_dialog._cluster_min_samples
        )
        min_cluster_size = kwargs.get(
            "min_cluster_size", ndxplorer.clustering_dialog._cluster_min_cluster_size
        )
        kwargs["min_samples"] = min_samples
        kwargs["min_cluster_size"] = min_cluster_size
    elif method == "kmeans":
        n_clusters = kwargs.get(
            "n_clusters", ndxplorer.clustering_dialog._cluster_n_clusters
        )
        kwargs["n_clusters"] = n_clusters

    if ndxplorer.clustering_dialog._cluster_columns:
        kwargs["columns"] = ndxplorer.clustering_dialog._cluster_columns
    else:
        kwargs["x_values"] = ndxplorer.x_values
        kwargs["y_values"] = ndxplorer.y_values
        kwargs["z_values"] = ndxplorer.z_values

    result = ndxplorer._clustering_manager.perform_clustering(
        method=method, worker=worker, **kwargs
    )

    if result[0] is not None and result[1] is not None:
        full_labels, full_probabilities = result
        ndxplorer._cluster_labels = full_labels
        ndxplorer._cluster_probabilities = full_probabilities
        ndxplorer._cluster_data_shape = (
            ndxplorer._clustering_manager._cluster_data_shape
        )
        # Writing the columns back and refreshing the combo boxes touches the
        # data source and Qt widgets, so it must happen on the GUI thread. When
        # a worker ran the fit, ``on_clustering_done`` does it after the queued
        # signal lands; doing it here would be a cross-thread widget call.
        if worker is None:
            store_clustering_result(ndxplorer, full_labels, full_probabilities)
        logging.info("Stored cluster data shape: %s", ndxplorer._cluster_data_shape)

    return result

