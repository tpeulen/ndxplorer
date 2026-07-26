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
__gmm_cls: Optional[Any] = None
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
        from sklearn.cluster import KMeans as _KMeans  # type: ignore
        __kmeans_cls = _KMeans
        logging.debug("lazy_imports: sklearn KMeans imported on demand")
    except Exception:
        __kmeans_cls = None
        logging.debug("scikit-learn not available")
    return __kmeans_cls


def get_gmm():
    global __gmm_cls
    if __gmm_cls is not None:
        return __gmm_cls
    try:
        from sklearn.mixture import GaussianMixture as _GMM  # type: ignore
        __gmm_cls = _GMM
        logging.debug("lazy_imports: sklearn GaussianMixture imported on demand")
    except Exception:
        __gmm_cls = None
        logging.debug("scikit-learn not available")
    return __gmm_cls


class _SklearnHdbscanShim:
    """Expose scikit-learn's HDBSCAN under the standalone package's interface.

    The two implementations agree on everything this codebase uses -- ``fit``,
    ``labels_``, ``probabilities_`` -- but differ in construction: the
    standalone package takes ``prediction_data``, which scikit-learn has no
    equivalent for and would reject. Dropping that one keyword is the whole
    adaptation, and it lets the clustering path work on a plain scikit-learn
    install instead of silently reporting "HDBSCAN is not installed".
    """

    def __init__(self, cls):
        self._cls = cls

    def HDBSCAN(self, *args, **kwargs):  # noqa: N802 - mirrors the upstream name
        """Construct a clusterer, ignoring keywords scikit-learn does not take."""
        kwargs.pop("prediction_data", None)
        return self._cls(*args, **kwargs)


def get_hdbscan():
    """Return an object exposing ``.HDBSCAN``, or ``None`` if unavailable.

    Prefers the standalone ``hdbscan`` package and falls back to
    ``sklearn.cluster.HDBSCAN`` (scikit-learn >= 1.3). Without the fallback,
    HDBSCAN is reported as missing on any environment that has scikit-learn but
    not the standalone package -- which is most of them, since scikit-learn is
    already a dependency and the standalone package is not.
    """
    global __hdbscan
    if __hdbscan is not None:
        return __hdbscan
    try:
        import hdbscan as _hdbscan  # type: ignore
        __hdbscan = _hdbscan
        logging.debug("lazy_imports: hdbscan imported on demand")
        return __hdbscan
    except Exception:
        logging.debug("standalone hdbscan not available; trying scikit-learn")
    try:
        from sklearn.cluster import HDBSCAN as _SkHdbscan  # type: ignore
        __hdbscan = _SklearnHdbscanShim(_SkHdbscan)
        logging.debug("lazy_imports: using sklearn.cluster.HDBSCAN")
    except Exception:
        __hdbscan = None
        logging.debug("HDBSCAN not available")
    return __hdbscan


def get_pca():
    """Return ``(PCA, IncrementalPCA)`` from scikit-learn, or ``None``.

    Both are returned because the choice is a size question, not a modelling
    one: ``PCA`` decomposes the whole matrix at once, which is exact and fine up
    to a few hundred thousand rows; ``IncrementalPCA`` streams it in batches for
    the burst tables that do not fit comfortably in memory.
    """
    global __pca
    if __pca is not None:
        return __pca
    try:
        from sklearn.decomposition import IncrementalPCA, PCA  # type: ignore

        __pca = (PCA, IncrementalPCA)
        logging.debug("lazy_imports: sklearn PCA imported on demand")
    except Exception:
        __pca = None
        logging.debug("scikit-learn PCA not available")
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
