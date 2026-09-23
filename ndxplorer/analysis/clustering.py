from ..logging_config import logging
from typing import Dict, List, Optional, Tuple
import numpy as np

from .structure import column_matrix, label_points

from qtpy.QtCore import QThread, Signal


class ClusteringWorker(QThread):
    """Worker class for performing clustering in a separate thread"""
    # Signal emitted when clustering is done
    clustering_done = Signal(tuple)
    # Signal emitted when an error occurs
    clustering_error = Signal(str)
    # Signal emitted to report progress
    progress_updated = Signal(int)

    def __init__(self, parent, method, params):
        super().__init__(parent)
        self.parent = parent
        self.method = method
        self.params = params
        self._stop_requested = False

    def stop(self):
        """Request the worker to stop processing"""
        self._stop_requested = True
        logging.info("Clustering stop requested")

    def run(self):
        try:
            # Perform clustering in the worker thread
            result = self.parent.perform_clustering(
                method=self.method,
                **self.params,
                worker=self  # Pass the worker instance to allow progress updates and cancellation
            )
            # Emit signal with the result only if not stopped
            if not self._stop_requested:
                self.clustering_done.emit(result)
        except Exception as e:
            # Log the error
            logging.error(f"Error in clustering worker thread: {str(e)}")
            # Emit error signal only if not stopped
            if not self._stop_requested:
                self.clustering_error.emit(str(e))
                # Emit done signal with None values to ensure the UI is updated
                self.clustering_done.emit((None, None))


class ClusteringManager:
    """Class to manage clustering operations"""

    def __init__(self, data_source=None):
        """
        Initialize the clustering manager.

        Args:
            data_source: The data source to use for clustering
        """
        self._data_source = data_source
        self._cluster_data_shape = None
        self._clustering_worker = None

    def perform_clustering(self, method=None, worker=None, **kwargs) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        """Cluster the chosen columns (or ``data``) and return the labels.

        The work is :func:`ndxplorer.analysis.structure.label_points`, the one
        both GUIs run; this drives its checkpoints on the Qt worker, turning
        each into a ``progress_updated`` signal and honouring ``stop()``.

        Args:
            method: ``"hdbscan"`` or ``"kmeans"``.
            worker: The ClusteringWorker running this, for progress and cancellation.
            **kwargs: ``min_samples``/``min_cluster_size`` (HDBSCAN),
                ``n_clusters`` (K-means); ``data`` (an array), or ``columns``
                read from the data source, or ``x_values``/``y_values``/``z_values``.

        Returns:
            ``(labels, probabilities)``, or ``(None, None)`` when nothing could
            be clustered or it was cancelled.
        """
        if method is None:
            method = kwargs.get("method", "hdbscan")
        data = kwargs.get("data", None)
        if data is None and self._data_source is not None and not self._data_source.empty:
            columns = kwargs.get("columns", [])
            if columns:
                data, _used = column_matrix(self._data_source, columns)
            if data is None:
                x_values = kwargs.get("x_values", None)
                y_values = kwargs.get("y_values", None)
                z_values = kwargs.get("z_values", None)
                if x_values is not None and y_values is not None and z_values is not None:
                    data = np.column_stack((x_values, y_values, z_values))
        if data is None or len(data) == 0:
            logging.error("No data available for clustering.")
            return None, None

        params = {k: kwargs[k] for k in ("min_samples", "min_cluster_size", "n_clusters")
                  if k in kwargs}
        work = label_points(_WorkerTask(worker), data, method, params)
        try:
            while True:
                fraction, _message = next(work)
                if worker:
                    worker.progress_updated.emit(int(round(100 * fraction)))
                    if worker._stop_requested:
                        logging.info("Clustering cancelled")
                        return None, None
        except StopIteration as done:
            result = done.value
        except Exception as e:
            logging.error(f"Error during {method} clustering: {str(e)}")
            return None, None
        if result is None or result[0] is None:
            return None, None
        self._cluster_data_shape = len(data)
        return result


class _WorkerTask:
    """The worker seen as the task :func:`label_points` checks for cancellation."""

    def __init__(self, worker) -> None:
        self._worker = worker

    @property
    def cancelled(self) -> bool:
        return bool(self._worker is not None and self._worker._stop_requested)
