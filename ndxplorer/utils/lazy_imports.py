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
