"""UMAP runs on tttrlib, not umap-learn.

``tttrlib.umap`` follows umap-learn step for step (A/B-tested in tttrlib's
``test_embedding.py``) and needs no numba, so ndXplorer's UMAP runs the same
on the desktop and in the browser. These check the switch itself: that the
backend is tttrlib's whenever the installed tttrlib has UMAP, that the step
generator the desktop thread and the browser both drive returns an embedding
aligned with the table, and that a metric tttrlib does not do is handed on or
refused in words -- never silently computed as Euclidean.
"""

from __future__ import annotations

import numpy as np
import pytest

tttrlib = pytest.importorskip("tttrlib")
if not hasattr(tttrlib, "umap"):
    pytest.skip("this tttrlib predates UMAP", allow_module_level=True)

from ndxplorer.analysis import structure
from ndxplorer.utils import lazy_imports


def _drain(work):
    try:
        while True:
            next(work)
    except StopIteration as done:
        return done.value


def _two_blobs():
    rng = np.random.default_rng(5)
    data = np.vstack([rng.normal(0, 0.3, (80, 3)), rng.normal(3, 0.3, (80, 3))])
    return data


def test_the_backend_is_tttrlib():
    backend = lazy_imports.get_umap()
    assert backend is not None
    assert backend.__name__ == "tttrlib.umap"
    assert structure.METHODS_BY_KEY["umap"].available()
    assert structure.METHODS_BY_KEY["umap"].browser


def test_embed_umap_keeps_rows_aligned_and_separates_planted_clusters():
    data = _two_blobs()
    data[7, 1] = np.nan                                   # a row with a missing value
    params = {"n_neighbors": 15, "min_dist": 0.1, "n_components": 2, "n_jobs": 1}
    out = _drain(structure.embed_umap(None, data, params))
    assert out.shape == (len(data), 2)
    assert np.all(np.isnan(out[7])) and np.isfinite(np.delete(out, 7, axis=0)).all()
    a, b = np.delete(out[:80], 7, axis=0), out[80:]
    gap = np.linalg.norm(a.mean(0) - b.mean(0))
    assert gap > 3 * max(a.std(0).max(), b.std(0).max())


def test_umap_learn_style_parameters_are_accepted():
    """Everything prepare_umap_params hands over, including umap-learn-only
    machinery options, must not break the tttrlib backend."""
    params = structure.prepare_umap_params({"n_neighbors": 10, "n_components": 3,
                                            "n_epochs": 60, "spread": 1.0,
                                            "low_memory": True, "init": "spectral"})
    y = lazy_imports.get_umap().UMAP(**params).fit_transform(_two_blobs())
    assert y.shape == (160, 3)


def test_a_non_euclidean_metric_is_not_computed_as_euclidean():
    reducer = lazy_imports.get_umap().UMAP(n_neighbors=10, metric="cosine")
    if lazy_imports._umap_learn() is None:
        with pytest.raises(ValueError, match="umap-learn"):
            reducer.fit_transform(_two_blobs())
    else:
        assert reducer.fit_transform(_two_blobs()).shape == (160, 2)
