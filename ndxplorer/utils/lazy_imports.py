"""
Centralized lazy import helpers for heavy optional dependencies used by NDxplorer.
Each getter attempts to import on first use, caches the result, and returns
None if the package is unavailable. Minimal, concise logging is performed on
first successful import or when a dependency is missing.
"""
from __future__ import annotations

from typing import Optional, Any

from ..logging_config import logging

# Caches
__umap: Optional[Any] = None
__kmeans_cls: Optional[Any] = None
__hdbscan: Optional[Any] = None
__napari: Optional[Any] = None
__pca: Optional[Any] = None


def get_umap():
    global __umap
    if __umap is not None:
        return __umap
    try:
        import umap as _umap  # type: ignore
        __umap = _umap
        logging.debug("lazy_imports: umap imported on demand")
    except Exception:
        __umap = None
        logging.debug("UMAP not available")
    return __umap


def get_kmeans():
    global __kmeans_cls
    if __kmeans_cls is not None:
        return __kmeans_cls
    try:
        from chisurf.core.ml.cluster import KMeans as _KMeans  # type: ignore

        __kmeans_cls = _KMeans
        logging.debug("lazy_imports: chisurf.core.ml KMeans imported on demand")
    except Exception:
        __kmeans_cls = None
        logging.debug("chisurf.core.ml KMeans not available")
    return __kmeans_cls


class _HdbscanNamespace:
    """Expose a class under the module-with-a-``.HDBSCAN``-attribute interface.

    The call sites were written against the standalone ``hdbscan`` *package*,
    so they say ``backend.HDBSCAN(...)``. Keeping that spelling costs one
    wrapper and saves touching every caller.
    """

    def __init__(self, cls):
        self._cls = cls

    def HDBSCAN(self, *args, **kwargs):  # noqa: N802 - mirrors the upstream name
        """Construct a clusterer."""
        return self._cls(*args, **kwargs)


def get_hdbscan():
    """Return an object exposing ``.HDBSCAN``, or ``None`` if unavailable.

    The implementation is ChiSurf's own (``chisurf.core.ml.cluster.HDBSCAN``),
    which accepts the standalone package's keywords -- including
    ``prediction_data``, which it ignores -- and prefers a compiled k-d tree /
    Borůvka kernel from the photon library when that is importable.
    """
    global __hdbscan
    if __hdbscan is not None:
        return __hdbscan
    try:
        from chisurf.core.ml.cluster import HDBSCAN as _HDBSCAN  # type: ignore

        __hdbscan = _HdbscanNamespace(_HDBSCAN)
        logging.debug("lazy_imports: chisurf.core.ml HDBSCAN imported on demand")
    except Exception:
        __hdbscan = None
        logging.debug("chisurf.core.ml HDBSCAN not available")
    return __hdbscan


def get_pca():
    """Return ``(PCA, IncrementalPCA)`` from ``chisurf.core.ml``, or ``None``.

    Both are returned because the choice is a size question, not a modelling
    one: ``PCA`` decomposes the whole matrix at once, which is exact and fine up
    to a few hundred thousand rows; ``IncrementalPCA`` streams it in batches for
    the burst tables that do not fit comfortably in memory.
    """
    global __pca
    if __pca is not None:
        return __pca
    try:
        from chisurf.core.ml.decomposition import IncrementalPCA, PCA  # type: ignore

        __pca = (PCA, IncrementalPCA)
        logging.debug("lazy_imports: chisurf.core.ml PCA imported on demand")
    except Exception:
        __pca = None
        logging.debug("chisurf.core.ml PCA not available")
    return __pca


def get_napari():
    global __napari
    if __napari is not None:
        return __napari
    try:
        import napari as _napari  # type: ignore
        __napari = _napari
        logging.debug("lazy_imports: napari imported on demand")
    except Exception:
        __napari = None
        logging.debug("napari not available")
    return __napari
