"""Clustering and PCA: does any of it actually work?

The clustering machinery has been here for a while with no test of any kind, and
the first thing this suite found is that it was **switched off**: its getter
only tried an optional third-party package, so on the environments that did not
happen to carry it — most of them — HDBSCAN reported itself missing and the
whole path silently did nothing. HDBSCAN and K-means are tttrlib's kernels now
and PCA is NumPy, so there is nothing optional left to be missing, but the
reachability tests stay: a probe that returns ``None`` is exactly the failure
that hides.

Three levels, deliberately:

1. **backends** — is the algorithm reachable at all;
2. **API** — planted clusters must come back out;
3. **GUI integration** — the dialog, the worker thread and the write-back into
   the table, which is where an analysis that computes correctly can still fail
   to arrive anywhere.
"""

from __future__ import annotations

import numpy as np
import pytest

from ndxplorer.analysis.clustering import ClusteringManager
from ndxplorer.analysis.pca_helpers import add_pca_columns, compute_pca, pca_available
from ndxplorer.core.data_source import DataSource
from ndxplorer.analysis import structure


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────
def three_blobs(n=120, seed=0):
    """Three well-separated blobs in 2-D, with the true label of every point."""
    rng = np.random.default_rng(seed)
    centres = [(0.0, 0.0), (8.0, 0.0), (0.0, 8.0)]
    points, truth = [], []
    for i, (cx, cy) in enumerate(centres):
        points.append(np.column_stack([rng.normal(cx, 0.35, n), rng.normal(cy, 0.35, n)]))
        truth.append(np.full(n, i))
    return np.vstack(points), np.concatenate(truth)


@pytest.fixture
def blob_source():
    """A DataSource holding three blobs plus a pure-noise column."""
    data, truth = three_blobs()
    rng = np.random.default_rng(7)
    return DataSource.from_columns({
        "x": data[:, 0],
        "y": data[:, 1],
        "noise": rng.normal(0.0, 1.0, data.shape[0]),
        "truth": truth,
    })


def purity(labels, truth):
    """Fraction of points whose cluster is that cluster's majority true label."""
    labels = np.asarray(labels)
    correct = 0
    for c in np.unique(labels):
        if c < 0:
            continue  # noise, not a cluster
        members = truth[labels == c]
        if members.size:
            correct += int(np.bincount(members).max())
    return correct / len(truth)


# ──────────────────────────────────────────────────────────────────────────────
# 1. Are the backends reachable?
# ──────────────────────────────────────────────────────────────────────────────
def test_every_labelling_and_pca_is_reachable():
    """HDBSCAN and K-means come from tttrlib, PCA from NumPy: all installed.

    This is the regression that motivated the suite: the getter used to try only
    ``import hdbscan``, an optional package, so the clustering path was dead on
    environments that had everything it needed.
    """
    for key in ("hdbscan", "kmeans", "pca"):
        method = structure.METHODS_BY_KEY[key]
        assert method.available(), method.unavailable()
        assert not method.installable, f"{key} ships with the app; nothing to install"
    assert pca_available()


def _labels(method, data, params):
    work = structure.label_points(None, data, method, params)
    try:
        while True:
            next(work)
    except StopIteration as done:
        return done.value


def test_hdbscan_recovers_planted_blobs():
    """The backend must find the structure, not merely return arrays."""
    data, truth = three_blobs()
    labels, probabilities = _labels("hdbscan", data, {"min_samples": 5, "min_cluster_size": 20})
    assert purity(labels, truth) > 0.95
    assert probabilities.shape == labels.shape
    assert np.all((probabilities >= 0) & (probabilities <= 1))


def test_kmeans_is_reproducible():
    """K-means draws its k-means++ stream from a fixed seed: same data, same labels."""
    data, truth = three_blobs()
    first, _ = _labels("kmeans", data, {"n_clusters": 3})
    second, _ = _labels("kmeans", data, {"n_clusters": 3})
    assert np.array_equal(first, second)
    assert purity(first, truth) == 1.0


# ──────────────────────────────────────────────────────────────────────────────
# 2. Does clustering recover planted structure?
# ──────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize("method,params", [
    ("hdbscan", {"min_samples": 5, "min_cluster_size": 20}),
    ("kmeans", {"n_clusters": 3}),
])
def test_clustering_recovers_three_planted_blobs(method, params):
    """Both algorithms must find the three groups that were put in."""
    data, truth = three_blobs()
    manager = ClusteringManager()
    labels, _ = manager.perform_clustering(method=method, data=data, **params)

    assert labels is not None, f"{method} returned nothing"
    assert len(labels) == len(data)
    found = {int(c) for c in np.unique(labels) if c >= 0}
    assert len(found) == 3, f"{method} found {len(found)} clusters, planted 3"
    assert purity(labels, truth) > 0.95


def test_labels_align_with_the_input_rows_when_some_are_not_finite():
    """Rows dropped for NaN must come back as noise, not shift the labels.

    The manager fits on the finite subset and scatters the labels back; getting
    that wrong would misalign every label after the first bad row, which is the
    kind of error that still produces a plausible-looking picture.
    """
    data, truth = three_blobs(n=60)
    data = data.copy()
    data[10] = np.nan
    data[150] = np.inf

    labels, _ = ClusteringManager().perform_clustering(
        method="kmeans", data=data, n_clusters=3
    )
    assert labels is not None and len(labels) == len(data)
    assert labels[10] == -1 and labels[150] == -1
    finite = np.ones(len(data), dtype=bool)
    finite[[10, 150]] = False
    assert purity(labels[finite], truth[finite]) > 0.95


def test_too_few_points_is_refused_rather_than_guessed():
    """Fewer points than clusters cannot be clustered, and must not pretend."""
    manager = ClusteringManager()
    labels, _ = manager.perform_clustering(
        method="kmeans", data=np.zeros((2, 2)), n_clusters=5
    )
    assert labels is None


def test_no_data_is_refused():
    """An empty request returns nothing rather than raising across the UI."""
    labels, _ = ClusteringManager().perform_clustering(method="kmeans",
                                                       data=np.zeros((0, 2)))
    assert labels is None


# ──────────────────────────────────────────────────────────────────────────────
# 3. PCA
# ──────────────────────────────────────────────────────────────────────────────
def test_pca_finds_the_direction_the_variance_is_in():
    """A planted correlation must show up as one dominant component."""
    rng = np.random.default_rng(1)
    t = rng.normal(0.0, 1.0, 500)
    data = np.column_stack([t, 2.0 * t + rng.normal(0.0, 0.05, 500),
                            rng.normal(0.0, 1.0, 500)])
    result = compute_pca(data, ["a", "b", "noise"], n_components=3)

    assert result is not None
    # Two of the three columns are the same signal, so one component should take
    # most of the variance of that pair.
    assert result.explained_variance_ratio[0] > 0.55
    top = dict(result.top_contributors(0, 3))
    assert abs(top["a"]) > 0.4 and abs(top["b"]) > 0.4, top
    assert abs(top["noise"]) < abs(top["a"]), "the noise column must not lead PC_1"


def test_standardising_is_what_stops_one_unit_dominating():
    """Without scaling, the column measured in thousands wins regardless.

    This is the trap the default guards against: PCA maximises variance, and
    variance carries units, so a photon count beside an efficiency produces a
    first component that is simply the photon count.
    """
    rng = np.random.default_rng(2)
    signal = rng.normal(0.0, 1.0, 400)
    data = np.column_stack([
        1000.0 * rng.normal(0.0, 1.0, 400),   # big units, pure noise
        signal,                                # small units, real structure
        signal + rng.normal(0.0, 0.05, 400),
    ])
    names = ["big_noise", "small_a", "small_b"]

    raw = compute_pca(data, names, n_components=2, standardize=False)
    scaled = compute_pca(data, names, n_components=2, standardize=True)

    assert dict(raw.top_contributors(0, 1)) .keys() == {"big_noise"}
    leader = scaled.top_contributors(0, 1)[0][0]
    assert leader in {"small_a", "small_b"}, f"standardised PC_1 led by {leader}"


def test_a_constant_column_does_not_poison_the_decomposition():
    """Zero variance would divide by zero when standardising."""
    rng = np.random.default_rng(3)
    data = np.column_stack([rng.normal(0, 1, 200), np.full(200, 5.0),
                            rng.normal(0, 1, 200)])
    result = compute_pca(data, ["a", "flat", "b"], n_components=2)
    assert result is not None
    assert np.all(np.isfinite(result.loadings))
    assert np.all(np.isfinite(result.explained_variance_ratio))


def test_non_finite_rows_are_dropped_and_written_back_as_nan():
    """Projections must stay aligned with the source table, row for row."""
    rng = np.random.default_rng(4)
    data = rng.normal(0.0, 1.0, (100, 3))
    data[7, 1] = np.nan
    result = compute_pca(data, ["a", "b", "c"], n_components=2)

    assert result.n_dropped == 1
    assert result.n_samples == 99
    assert np.all(np.isnan(result.projections[7]))
    assert np.isfinite(result.projections[np.arange(100) != 7]).all()


def test_pca_reports_rather_than_only_projects():
    """The loadings are the answer PCA was asked for, so they must be returned."""
    rng = np.random.default_rng(5)
    t = rng.normal(0, 1, 300)
    result = compute_pca(np.column_stack([t, t + rng.normal(0, .1, 300), rng.normal(0, 1, 300)]),
                         ["a", "b", "c"], n_components=2)
    text = result.report()
    assert "PC_1" in text and "%" in text
    payload = result.to_dict()
    assert len(payload["loadings"]) == 2 and len(payload["loadings"][0]) == 3
    import json
    json.loads(json.dumps(payload))


def test_pca_needs_at_least_two_columns():
    """One column has no components to find; say so rather than return garbage."""

    class _Explorer:
        def __init__(self, source):
            self.data_source = source

    source = DataSource.from_columns({"only": np.arange(10.0)})
    assert add_pca_columns(_Explorer(source), ["only", "missing"]) is None


# ──────────────────────────────────────────────────────────────────────────────
# 4. Integration: does the result reach the table?
# ──────────────────────────────────────────────────────────────────────────────
def test_pca_columns_land_in_the_data_source(blob_source):
    """``PC_1``/``PC_2`` must appear in the frame and be usable as axes."""

    class _Explorer:
        def __init__(self, source):
            self.data_source = source
            self.refreshed = False

        def refresh_axis_comboboxes_preserving_selection(self):
            self.refreshed = True

    explorer = _Explorer(blob_source)
    result = add_pca_columns(explorer, ["x", "y", "noise"], n_components=2)

    assert result is not None
    source = explorer.data_source
    assert "PC_1" in source.parameter_names and "PC_2" in source.parameter_names
    assert len(source.column_values("PC_1")) == len(source.column_values("x"))
    assert np.isfinite(source.column_values("PC_1")).all()
    assert explorer.refreshed, "the axis combo boxes were never refreshed"


def test_pca_separates_the_blobs_it_was_given(blob_source):
    """The projection has to preserve the structure, not merely run."""
    data = np.column_stack([blob_source.column_values("x"), blob_source.column_values("y")])
    result = compute_pca(data, ["x", "y"], n_components=2)
    truth = blob_source.column_values("truth").astype(int)

    # Cluster the projection: the three blobs must survive the transform.
    labels, _ = ClusteringManager().perform_clustering(
        method="kmeans", data=result.projections, n_clusters=3
    )
    assert purity(labels, truth) > 0.95
