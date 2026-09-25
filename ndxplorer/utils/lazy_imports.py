"""
Centralized lazy import helpers for heavy optional dependencies used by NDxplorer.
Each getter attempts to import on first use, caches the result, and returns
None if the package is unavailable. Minimal, concise logging is performed on
first successful import or when a dependency is missing.

Clustering and PCA are not here: HDBSCAN and K-means are tttrlib's kernels and
PCA is NumPy (:mod:`ndxplorer.analysis.structure`), all always installed.
"""
from __future__ import annotations

from typing import Optional, Any

from ..logging_config import logging

# Caches
__umap: Optional[Any] = None
__napari: Optional[Any] = None


def _umap_learn():
    try:
        import umap as _umap  # type: ignore
        return _umap
    except Exception:
        return None


class _TttrlibUMAP:
    """``umap.UMAP``'s constructor / ``fit_transform`` surface over
    ``tttrlib.umap``, which follows umap-learn step for step (A/B-tested in
    tttrlib's test_embedding.py) and needs no numba, so it runs in the browser.

    tttrlib's UMAP is Euclidean. Another metric is handed to umap-learn when
    that is installed, and refused in words when it is not. Options that only
    steer umap-learn's machinery (``n_jobs``, ``verbose``, ``tqdm_kwds``,
    ``low_memory``) have nothing to steer here and are dropped.
    """

    _PASSED = ("n_components", "n_neighbors", "min_dist", "spread", "n_epochs",
               "learning_rate", "negative_sample_rate", "repulsion_strength",
               "local_connectivity", "set_op_mix_ratio", "init", "random_state")

    def __init__(self, **params):
        self._metric = params.get("metric", "euclidean") or "euclidean"
        self._all = dict(params)
        self._params = {k: params[k] for k in self._PASSED if params.get(k) is not None}
        self.embedding_ = None

    def fit_transform(self, X, y=None):
        if self._metric != "euclidean":
            learn = _umap_learn()
            if learn is None:
                raise ValueError(
                    f"UMAP with the {self._metric!r} metric needs umap-learn; tttrlib's "
                    "UMAP is Euclidean. Choose 'euclidean' or install umap-learn.")
            self.embedding_ = learn.UMAP(**self._all).fit_transform(X)
            return self.embedding_
        import tttrlib
        params = dict(self._params)
        if params.get("random_state") is not None:
            params["random_state"] = int(params["random_state"]) & 0x7FFFFFFF
        print(f"UMAP (tttrlib): {len(X)} rows, {params.get('n_components', 2)} dimensions")
        self.embedding_ = tttrlib.umap(X, **params)
        return self.embedding_

    def fit(self, X, y=None):
        self.fit_transform(X)
        return self


class _TttrlibUMAPBackend:
    """What ``get_umap()`` returns when tttrlib has UMAP: a stand-in for the
    ``umap`` module, so every ``get_umap().UMAP(**params)`` call site works."""
    __name__ = "tttrlib.umap"
    UMAP = _TttrlibUMAP


def get_umap():
    """The UMAP backend: tttrlib's (``tttrlib.umap``) when the installed
    tttrlib has it, else umap-learn, else None."""
    global __umap
    if __umap is not None:
        return __umap
    try:
        import tttrlib  # type: ignore
        if hasattr(tttrlib, "umap"):
            __umap = _TttrlibUMAPBackend()
            logging.debug("lazy_imports: UMAP from tttrlib")
            return __umap
    except Exception:
        pass
    __umap = _umap_learn()
    if __umap is not None:
        logging.debug("lazy_imports: UMAP from umap-learn (tttrlib has none)")
    else:
        logging.debug("UMAP not available")
    return __umap


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
