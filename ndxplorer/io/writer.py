from __future__ import print_function
from datetime import datetime
from typing import Callable, List, Dict, Optional, Set
from pathlib import Path
from ..logging_config import logging
import numpy as np
import json
import tttrlib
try:
    from qtpy.QtWidgets import QApplication
    from qtpy.QtCore import QCoreApplication
    from ..ui.progress_window import ProgressWindow
    _HAS_QT = True
except Exception:
    QApplication = None
    QCoreApplication = None
    ProgressWindow = None
    _HAS_QT = False
from ..core.data_source import DataSource, DataSelection, float_column


def _burst_id_groups(selections: List[DataSelection], data_source: DataSource):
    """``(file name, first photons, last photons)`` per file, for the kept bursts
    that start and end in the same file, in file-name order."""
    store = data_source.store
    keep = data_source.selection_mask(selections)
    first_file = store.find("First File")
    last_file = store.find("Last File")
    first = store.column(first_file)
    last = store.column(last_file)
    first_names = np.asarray(first.labels(), dtype=object)
    first_codes = np.asarray(first.codes())
    last_names = np.asarray(last.labels(), dtype=object)[np.asarray(last.codes())]
    rows = keep & (first_names[first_codes] == last_names)
    for mask in (first.mask_numpy(), last.mask_numpy()):
        if mask is not None:
            rows &= mask
    first_photon = float_column(store, store.find("First Photon"))
    last_photon = float_column(store, store.find("Last Photon"))
    for code in sorted(np.unique(first_codes[rows]), key=lambda c: first_names[c]):
        in_file = rows & (first_codes == code)
        ids = np.vstack([first_photon[in_file], last_photon[in_file]]).astype(int)
        yield str(first_names[code]), ids


def save_burst_ids(
        folder_name: str,
        selections: List[DataSelection],
        data_source: DataSource
):
    """:func:`save_burst_ids_headless` with the Qt progress window."""
    if not _HAS_QT or QApplication is None:
        raise RuntimeError("save_burst_ids requires Qt (not available in headless mode)")
    QApplication.instance() or QApplication([])
    progress_window = None

    def progress(done: int, total: int) -> bool:
        nonlocal progress_window
        if progress_window is None:
            progress_window = ProgressWindow(title="Saving Files",
                                             message="Saving Burst ID files...",
                                             max_value=total)
            progress_window.show()
        progress_window.set_value(done)
        QCoreApplication.processEvents()
        return True

    try:
        return save_burst_ids_headless(folder_name, selections, data_source, progress=progress)
    finally:
        if progress_window is not None:
            progress_window.close()


def save_burst_ids_headless(
        folder_name: str,
        selections: List[DataSelection],
        data_source: DataSource,
        progress=None,
) -> List[Path]:
    """Write one ``<measurement>.bst`` of first/last photon per kept burst and file.

    Parameters
    ----------
    folder_name : str
        Where the files go (created).
    selections : list of DataSelection
        The gates; the bursts they keep are written.
    data_source : DataSource
        A burst table with ``First File``/``Last File``/``First Photon``/``Last Photon``.
    progress : callable, optional
        ``progress(done, total) -> bool``, called before the first file and
        after each; returning ``False`` stops (the files written so far stay).

    Returns
    -------
    list of Path
        The files written.
    """
    folder_path = Path(folder_name)
    folder_path.mkdir(parents=True, exist_ok=True)
    logging.info(f"Saving burst IDs to {folder_path}")

    groups = list(_burst_id_groups(selections, data_source))
    written: List[Path] = []
    if progress is not None and progress(0, len(groups)) is False:
        return written
    for i, (filename, ids) in enumerate(groups, start=1):
        bst_file = folder_path / f"{Path(filename).name}.bst"
        np.savetxt(bst_file, ids.T, fmt='%i', delimiter='\t')
        logging.info(f"Saved burst ID file: {bst_file}")
        written.append(bst_file)
        if progress is not None and progress(i, len(groups)) is False:
            break
    return written


def find_setup_name(folder: str) -> Optional[str]:
    """The measurement setup a burst-ID folder belongs to, or ``None``.

    Read from ``Info/photon_selection_parameters.json`` (``selected_setup``)
    beside the folder or one level up.
    """
    bid_folder = Path(folder)
    for info in (bid_folder.parent / "Info", bid_folder.parent.parent / "Info"):
        params_file = info / "photon_selection_parameters.json"
        if params_file.exists():
            try:
                with open(params_file, "r", encoding="utf-8") as handle:
                    return json.load(handle).get("selected_setup") or None
            except (OSError, ValueError) as exc:
                logging.error("Error reading setup information: %s", exc)
                return None
    return None


def find_bst_files(folder: str) -> List[str]:
    """The ``.bst`` files of a burst-ID folder, sorted, as absolute paths.

    The folder itself, its ``BID``, ``BID/ALL`` and ``ALL`` subfolders, and
    -- when those hold none -- anywhere below it.
    """
    root = Path(folder)
    found: Set[str] = {str(p.resolve()) for p in root.glob("*.bst")}
    for sub in (root / "BID", root / "BID" / "ALL", root / "ALL"):
        if sub.is_dir():
            found.update(str(p.resolve()) for p in sub.glob("*.bst"))
    if not found:
        found.update(str(p.resolve()) for p in root.rglob("*.bst"))
    return sorted(found)


def save_clustering_data(
        folder_name: str,
        data_source: DataSource,
        cluster_method: str,
        cluster_labels: Optional[np.ndarray],
        cluster_probabilities: Optional[np.ndarray],
        cluster_columns: Set[str],
        parameters: Dict,
        progress: Optional[Callable[[int, str], None]] = None,
) -> Optional[Path]:
    """
    Save clustering data to ``<folder>/clustering``.

    Writes ``clustering_parameters.json``, ``clustering_full_data.csv`` (the
    table with the cluster columns), ``cluster_labels.csv`` (ID, label,
    probability) and one ``cluster_<n>.csv`` per cluster (noise, ``-1``, is
    not written on its own).

    Args:
        folder_name: Path to the folder where clustering data will be saved
        data_source: DataSource object containing the data
        cluster_method: Clustering method used (e.g., 'kmeans', 'hdbscan')
        cluster_labels: Array of cluster labels for each data point
        cluster_probabilities: Array of cluster membership probabilities
        cluster_columns: Set of column names used for clustering
        parameters: Dictionary of clustering parameters
        progress: ``progress(step, message)`` for steps 1..3, for a GUI's
            progress display.

    Returns:
        The ``clustering`` folder, or ``None`` when writing failed.
    """
    def report(step: int, message: str) -> None:
        if progress is not None:
            progress(step, message)

    folder_path = Path(folder_name)
    clustering_folder = folder_path / "clustering"
    clustering_folder.mkdir(parents=True, exist_ok=True)
    logging.info(f"Saving clustering data to {clustering_folder}")

    try:
        report(1, "Saving clustering parameters...")
        clustering_info = {
            "method": cluster_method,
            "columns": sorted(cluster_columns),
            "parameters": parameters,
            "timestamp": datetime.now().isoformat()
        }
        params_file = clustering_folder / "clustering_parameters.json"
        with open(params_file, 'w') as f:
            json.dump(clustering_info, f, indent=4)
        logging.info(f"Saved clustering parameters to {params_file}")

        report(2, "Saving cluster labels...")
        if cluster_labels is not None:
            table = data_source.copy()
            labels = np.asarray(cluster_labels)
            if not table.has_column('Cluster Label'):
                table.set_column('Cluster Label', labels)
            if cluster_probabilities is not None and not table.has_column('Cluster Probability'):
                table.set_column('Cluster Probability', np.asarray(cluster_probabilities))

            full_data_file = clustering_folder / "clustering_full_data.csv"
            tttrlib.write_csv(str(full_data_file), table.store)
            logging.info(f"Saved full data with cluster labels to {full_data_file}")

            info_columns = {
                'ID': np.arange(len(labels)),
                'Cluster Label': labels,
            }
            if cluster_probabilities is not None:
                info_columns['Cluster Probability'] = np.asarray(cluster_probabilities)
            cluster_info_file = clustering_folder / "cluster_labels.csv"
            tttrlib.write_csv(str(cluster_info_file), DataSource.from_columns(info_columns).store)
            logging.info(f"Saved cluster labels to {cluster_info_file}")

            for label in np.unique(labels):
                if label >= 0:  # Skip noise points (label -1)
                    cluster_file = clustering_folder / f"cluster_{label}.csv"
                    tttrlib.write_csv(str(cluster_file), table.take(labels == label).store)
                    logging.info(f"Saved data for cluster {label} to {cluster_file}")
        else:
            logging.warning("No cluster labels to save")

        report(3, "Clustering data saved successfully!")
        logging.info("Clustering data saved successfully")
        return clustering_folder
    except Exception as e:
        logging.error(f"Error saving clustering data: {str(e)}")
        return None
