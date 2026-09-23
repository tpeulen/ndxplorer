"""Find structure: PCA, UMAP, HDBSCAN and K-means over chosen columns, Qt-free.

The four methods answer the same question -- "what structure is in here?" --
and, as tools, are the same gesture: pick some columns, run, get new columns
back. They differ where they genuinely differ:

* **Projections** (PCA, UMAP) add ``PC_n`` / ``UMAP_n`` columns you then pick in
  the axis controls. PCA also reports its *loadings* -- which measured
  parameters carry the variance -- which is the reason to run it.
* **Labellings** (HDBSCAN, K-means) add ``Cluster Label`` and ``Cluster
  Probability``, and can be saved.

Everything here is what both GUIs call: the method table (:data:`METHODS`),
reading the columns (:func:`column_matrix`), the work itself as generators that
yield ``(fraction, message)`` checkpoints (:func:`label_points`,
:func:`embed_umap`) -- so a desktop runs them on a thread and a browser, which
has no threads, steps them between frames (:mod:`emtk.tasks`) -- and writing
the result back (:func:`store_labels`, :func:`store_projection`).

Backends come from :mod:`ndxplorer.utils.lazy_imports`: ChiSurf's in-tree
estimators where ChiSurf is installed, scikit-learn otherwise (the browser's
path). UMAP needs ``umap-learn``, which needs numba and so cannot run in a
browser at all; :meth:`Method.unavailable` says so in words.
"""

from __future__ import annotations

import contextlib
import sys
from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple

import numpy as np

from ..logging_config import logging
from ..utils.lazy_imports import get_hdbscan, get_kmeans, get_pca, get_umap

__all__ = [
    "LABELS",
    "METHODS",
    "METHODS_BY_KEY",
    "Method",
    "PROJECTION",
    "UMAP_INITS",
    "UMAP_METRICS",
    "column_matrix",
    "embed_umap",
    "in_browser",
    "label_points",
    "pca_report",
    "prepare_umap_params",
    "store_labels",
    "store_projection",
]

#: Families. Projections add coordinate columns; labellings assign each point to
#: a group. The distinction drives which actions are offered, and nothing else.
PROJECTION = "projection"
LABELS = "labels"

#: UMAP's distance metrics, in the order the dialog offers them.
UMAP_METRICS: Tuple[str, ...] = (
    "euclidean", "manhattan", "chebyshev", "minkowski", "canberra",
    "braycurtis", "cosine", "correlation", "hamming", "jaccard",
)
#: UMAP's initialisations.
UMAP_INITS: Tuple[str, ...] = ("spectral", "random", "pca")


def in_browser() -> bool:
    """Whether this is Pyodide: no threads, no subprocesses, no numba."""
    return sys.platform == "emscripten" or "pyodide" in sys.modules


@dataclass(frozen=True)
class Method:
    """Everything a dialog needs to know about one method.

    Collecting this per method is what removes the per-algorithm "is the
    backend importable, offer to install it, re-check, explain the restart"
    block.
    """

    key: str
    title: str
    family: str
    #: Returns the backend, or ``None`` when it cannot be imported.
    probe: Callable[[], object]
    #: Distribution name to offer to install, and the module to import after.
    package: str
    import_name: str
    blurb: str
    #: Minimum columns the method needs to mean anything.
    min_columns: int = 1
    #: Offer installation on demand. Off for backends that ship with the app,
    #: where a failure means something is wrong rather than something is missing.
    installable: bool = True
    #: Can run in a browser (Pyodide) at all.
    browser: bool = True

    def available(self) -> bool:
        """Whether the backend can be imported now."""
        return self.probe() is not None

    def unavailable(self) -> str:
        """Why the method cannot run, in words; ``""`` when it can."""
        if self.available():
            return ""
        if in_browser() and not self.browser:
            return (f"{self.title} is not available in the browser: {self.package} needs "
                    "numba's compiled code, which the browser cannot run. Use PCA for a "
                    "projection here, or the desktop app for " + self.title + ".")
        if in_browser():
            return (f"{self.title} needs {self.package}, which this page did not load.")
        if not self.installable:
            return (f"{self.package} could not be imported, although it ships with the "
                    "application. The installation is likely broken.")
        return f"{self.title} needs {self.package}, which is not installed."


METHODS: Tuple[Method, ...] = (
    Method(
        key="pca",
        title="PCA",
        family=PROJECTION,
        probe=get_pca,
        package="scikit-learn",
        import_name="sklearn",
        blurb="Linear decomposition. Reports which parameters carry the variance.",
        min_columns=2,
        installable=False,
    ),
    Method(
        key="umap",
        title="UMAP",
        family=PROJECTION,
        probe=get_umap,
        package="umap-learn",
        import_name="umap",
        blurb="Non-linear projection to 2-3 dimensions for visual inspection.",
        min_columns=2,
        browser=False,
    ),
    Method(
        key="hdbscan",
        title="HDBSCAN",
        family=LABELS,
        probe=get_hdbscan,
        package="hdbscan",
        import_name="hdbscan",
        blurb="Density-based. Finds clusters of varying shape and leaves noise unlabelled.",
    ),
    Method(
        key="kmeans",
        title="K-means",
        family=LABELS,
        probe=get_kmeans,
        package="scikit-learn",
        import_name="sklearn",
        blurb="Partitions every point into exactly k groups of similar spread.",
        installable=False,
    ),
)

METHODS_BY_KEY: Dict[str, Method] = {m.key: m for m in METHODS}


# ------------------------------------------------------------------- columns
def column_matrix(source, columns: Iterable[str]) -> Tuple[Optional[np.ndarray], List[str]]:
    """The chosen columns of *source* side by side, ``(n_rows, n_columns)``.

    Names absent from the table are skipped (and logged). Returns
    ``(None, [])`` when none is present.
    """
    used: List[str] = []
    stacked: List[np.ndarray] = []
    if source is None or getattr(source, "empty", True):
        return None, used
    for name in columns:
        values = source.column_values(name)
        if values is None:
            logging.warning("column '%s' is not in the table; skipping", name)
            continue
        stacked.append(np.asarray(values, dtype=np.float64))
        used.append(name)
    if not stacked:
        return None, used
    return np.column_stack(stacked), used


def finite_rows(data: np.ndarray) -> np.ndarray:
    """Rows with no NaN or Inf in any column."""
    return ~np.any(~np.isfinite(np.asarray(data, dtype=np.float64)), axis=1)


# ----------------------------------------------------------------- labelling
def label_points(task, data: np.ndarray, method: str, params: Dict[str, Any]):
    """Assign every row of *data* to a cluster; a generator of checkpoints.

    Parameters
    ----------
    task : emtk.tasks.Task or None
        Checked for cancellation at every checkpoint (``task.cancelled``).
    data : numpy.ndarray
        ``(n_rows, n_columns)``. Rows with a non-finite value are left out of
        the fit and labelled ``-1``.
    method : str
        ``"hdbscan"`` or ``"kmeans"``.
    params : dict
        ``min_samples`` / ``min_cluster_size`` (HDBSCAN) or ``n_clusters``
        (K-means).

    Yields
    ------
    tuple
        ``(fraction, message)``.

    Returns
    -------
    tuple
        ``(labels, probabilities)``, full length, or ``(None, None)`` when there
        was nothing to cluster or it was cancelled. K-means has no membership
        probability; the inverted, normalised distance to the centre stands in.

    Raises
    ------
    RuntimeError
        The backend is missing, or there are fewer rows than the method needs.
    """
    def stop() -> bool:
        return task is not None and getattr(task, "cancelled", False)

    data = np.asarray(data, dtype=np.float64)
    if data.ndim != 2 or len(data) == 0:
        raise RuntimeError("No data available for clustering.")
    yield 0.1, "Preparing the data"
    if stop():
        return None, None
    mask = finite_rows(data)
    clean = data[mask]
    yield 0.3, f"{int(mask.sum())} finite rows"
    if stop():
        return None, None

    full_labels = np.full(len(data), -1, dtype=np.int32)
    full_probabilities = np.zeros(len(data))
    if method == "hdbscan":
        min_samples = int(params.get("min_samples", 5))
        min_cluster_size = int(params.get("min_cluster_size", 5))
        if len(clean) < min_cluster_size:
            raise RuntimeError(f"Not enough data points for HDBSCAN: need at least "
                               f"{min_cluster_size}.")
        backend = get_hdbscan()
        if backend is None:
            raise RuntimeError(METHODS_BY_KEY["hdbscan"].unavailable())
        yield 0.4, "Running HDBSCAN"
        clusterer = backend.HDBSCAN(min_samples=min_samples, min_cluster_size=min_cluster_size)
        clusterer.fit(clean)
        yield 0.8, "HDBSCAN finished"
        if stop():
            return None, None
        full_labels[mask] = np.asarray(clusterer.labels_, dtype=np.int32)
        full_probabilities[mask] = np.asarray(clusterer.probabilities_, dtype=np.float64)
    elif method == "kmeans":
        n_clusters = int(params.get("n_clusters", 2))
        if len(clean) < n_clusters:
            raise RuntimeError(f"Not enough data points for K-means: need at least "
                               f"{n_clusters} (one per cluster).")
        backend = get_kmeans()
        if backend is None:
            raise RuntimeError(METHODS_BY_KEY["kmeans"].unavailable())
        yield 0.4, "Running K-means"
        clusterer = backend(n_clusters=n_clusters, random_state=42)
        clusterer.fit(clean)
        yield 0.7, "K-means finished"
        if stop():
            return None, None
        labels = np.asarray(clusterer.labels_, dtype=np.int32)
        centres = np.asarray(clusterer.cluster_centers_, dtype=np.float64)
        distances = np.zeros(len(clean))
        batch = 100_000
        for start in range(0, len(clean), batch):
            end = min(start + batch, len(clean))
            chunk = labels[start:end]
            ok = chunk >= 0
            diff = clean[start:end][ok] - centres[chunk[ok]]
            distances[start:end][ok] = np.sqrt(np.einsum("ij,ij->i", diff, diff))
            yield 0.7 + 0.2 * end / len(clean), "Distances to the centres"
            if stop():
                return None, None
        top = float(distances.max()) if distances.size and distances.max() > 0 else 1.0
        full_labels[mask] = labels
        full_probabilities[mask] = 1.0 - distances / top
    else:
        raise RuntimeError(f"Unsupported clustering method: {method}")
    yield 1.0, "Finished"
    return full_labels, full_probabilities


def store_labels(source, labels, probabilities) -> None:
    """Write ``Cluster Label`` and ``Cluster Probability`` into the table."""
    source.set_column("Cluster Label", np.asarray(labels))
    source.set_column("Cluster Probability", np.asarray(probabilities, dtype=np.float64))


def store_projection(source, prefix: str, projections: np.ndarray) -> List[str]:
    """Add ``<prefix>_1 … <prefix>_n`` from the columns of *projections*.

    Returns the column names written.
    """
    projections = np.asarray(projections, dtype=np.float64)
    names = []
    for i in range(projections.shape[1]):
        name = f"{prefix}_{i + 1}"
        source.set_column(name, projections[:, i])
        names.append(name)
    return names


# ---------------------------------------------------------------------- UMAP
def prepare_umap_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """The keyword arguments for ``umap.UMAP`` from the dialog's settings."""
    umap_params: Dict[str, Any] = {
        "n_neighbors": params.get("n_neighbors", 15),
        "min_dist": params.get("min_dist", 0.1),
        "n_components": params.get("n_components", 2),
        "n_jobs": params.get("n_jobs", -1),
        "verbose": True,
        "tqdm_kwds": {"desc": "UMAP Embedding", "unit": "epoch"},
    }
    for name in ("metric", "learning_rate", "init", "spread", "low_memory",
                 "set_op_mix_ratio", "local_connectivity", "repulsion_strength",
                 "negative_sample_rate", "n_epochs"):
        if name in params and params[name] is not None:
            umap_params[name] = params[name]
    if umap_params["n_jobs"] == 1:
        umap_params["random_state"] = 42
    return umap_params


def embed_umap(task, data: np.ndarray, params: Dict[str, Any]):
    """Embed *data* with UMAP; a generator of checkpoints.

    UMAP's own progress (its verbose log and tqdm bar) is written to
    ``task.write`` when the task has one -- the progress window's log.

    Returns
    -------
    numpy.ndarray or None
        ``(n_rows, n_components)`` with ``NaN`` in rows that had a non-finite
        value, so it aligns with the table row for row. ``None`` when
        cancelled.

    Raises
    ------
    RuntimeError
        umap-learn is missing, or there are fewer rows than neighbours.
    """
    backend = get_umap()
    if backend is None:
        raise RuntimeError(METHODS_BY_KEY["umap"].unavailable())
    data = np.asarray(data, dtype=np.float64)
    mask = finite_rows(data)
    clean = data[mask]
    umap_params = prepare_umap_params(params)
    if len(clean) < umap_params["n_neighbors"]:
        raise RuntimeError(f"Not enough data points for UMAP: need at least "
                           f"{umap_params['n_neighbors']}.")
    yield None, f"Embedding {len(clean)} rows in {umap_params['n_components']} dimensions"
    if task is not None and task.cancelled:
        return None
    reducer = backend.UMAP(**umap_params)
    sink = task if task is not None and hasattr(task, "write") else None
    with (contextlib.redirect_stdout(sink) if sink else contextlib.nullcontext()), \
            (contextlib.redirect_stderr(sink) if sink else contextlib.nullcontext()):
        embedding = reducer.fit_transform(clean)
    out = np.full((len(data), embedding.shape[1]), np.nan)
    out[mask] = embedding
    yield 1.0, "UMAP finished"
    return out


# ----------------------------------------------------------------------- PCA
def pca_report(result) -> Tuple[List[Tuple[str, str]], str]:
    """What PCA found, as text: ``([(head, drivers)], footer)``.

    One line per component -- ``("PC_1", "29% of variance: Duration (ms)
    (-0.70), …")`` -- and a footer on rows fitted and dropped. The ``PC_n``
    columns are how the answer is plotted; the loadings *are* the answer.
    """
    lines = []
    for component in range(result.n_components):
        share = 100.0 * float(result.explained_variance_ratio[component])
        drivers = ", ".join(f"{name} ({weight:+.2f})"
                            for name, weight in result.top_contributors(component, n=3))
        lines.append((f"PC_{component + 1}", f"{share:.0f}% of variance: {drivers}"))
    total = 100.0 * float(np.sum(result.explained_variance_ratio))
    footer = (f"{result.n_samples} rows fitted"
              + (f", {result.n_dropped} dropped as non-finite" if result.n_dropped else "")
              + f"; {total:.0f}% of the variance retained.")
    return lines, footer
