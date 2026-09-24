"""Find structure's HDBSCAN, K-means and PCA need neither scikit-learn nor hdbscan.

HDBSCAN and K-means are tttrlib's kernels and PCA is NumPy, so the browser page
ships without scikit-learn. A stray ``import sklearn`` anywhere on the path
would quietly bring the dependency back; this runs the whole path in a fresh
interpreter and looks at ``sys.modules`` afterwards -- and a second time with
both packages made unimportable, so no fallback can hide behind an installed
copy.
"""

from __future__ import annotations

import subprocess
import sys
import textwrap

import pytest

_SCRIPT = textwrap.dedent('''
    import sys
    BLOCK = {block!r}
    if BLOCK:
        for name in ("sklearn", "hdbscan"):
            sys.modules[name] = None  # ``import`` raises ImportError
    import numpy as np
    from ndxplorer.analysis import clustering, structure
    from ndxplorer.analysis.pca_helpers import compute_pca

    rng = np.random.default_rng(0)
    data = np.vstack([rng.normal(c, 0.3, (80, 2)) for c in (0.0, 5.0, 10.0)])
    for method, params in (("hdbscan", {{"min_samples": 5, "min_cluster_size": 20}}),
                           ("kmeans", {{"n_clusters": 3}})):
        assert structure.METHODS_BY_KEY[method].available(), method
        labels, _ = clustering.ClusteringManager().perform_clustering(
            method=method, data=data, **params)
        assert labels is not None and len(set(labels[labels >= 0])) == 3, (method, labels)
    assert compute_pca(data, ["a", "b"], n_components=2) is not None
    loaded = sorted(m for m in sys.modules
                    if m.split(".")[0] in ("sklearn", "hdbscan") and sys.modules[m] is not None)
    print("LOADED", loaded)
''')


@pytest.mark.parametrize("block", [False, True], ids=["installed", "blocked"])
def test_find_structure_imports_no_sklearn_or_hdbscan(block):
    pytest.importorskip("qtpy")  # ClusteringWorker is a QThread
    result = subprocess.run([sys.executable, "-c", _SCRIPT.format(block=block)],
                            capture_output=True, text=True, timeout=300)
    assert result.returncode == 0, result.stderr[-3000:]
    assert "LOADED []" in result.stdout, result.stdout[-2000:]
