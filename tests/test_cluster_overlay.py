"""Colouring the 2-D map by cluster.

The density view answers "where are the points"; this answers "which population
is which". Both are lossy in their own way, and the tests below pin the two
choices that make the colour view honest: one colour per bin (its dominant
cluster) and brightness that still carries the count.
"""

from __future__ import annotations

import numpy as np
import pytest

from ndxplorer.plotting.cluster_overlay import (
    CLUSTER_COLORS,
    NOISE_COLOR,
    cluster_color,
    cluster_rgb_image,
)

EDGES = np.linspace(0.0, 1.0, 21)


def two_clusters(n=300, seed=0):
    """Two well-separated groups, plus their labels."""
    rng = np.random.default_rng(seed)
    x = np.concatenate([rng.normal(0.25, 0.03, n), rng.normal(0.75, 0.03, n)])
    y = np.concatenate([rng.normal(0.30, 0.03, n), rng.normal(0.70, 0.03, n)])
    labels = np.concatenate([np.zeros(n, int), np.ones(n, int)])
    return x, y, labels


def test_each_cluster_gets_its_own_colour():
    """The whole point: two populations must be drawn in two different hues."""
    x, y, labels = two_clusters()
    image = cluster_rgb_image(x, y, labels, EDGES, EDGES)

    assert image is not None and image.shape == (20, 20, 3)
    # Sample the centre of each blob and compare hue, ignoring brightness.
    a = image[int(0.30 * 20), int(0.25 * 20)].astype(float)
    b = image[int(0.70 * 20), int(0.75 * 20)].astype(float)
    assert a.sum() > 0 and b.sum() > 0
    assert not np.allclose(a / a.sum(), b / b.sum(), atol=0.05), (
        "the two clusters were drawn in the same colour"
    )


def test_brightness_still_carries_density():
    """Recolouring must not throw the counts away.

    A bin holding two points and one holding two hundred would otherwise look
    identical, turning a scatter of noise into something that reads as a
    population.
    """
    rng = np.random.default_rng(1)
    dense = np.full(400, 0.25)
    sparse = np.array([0.75] * 3)
    x = np.concatenate([dense, sparse])
    y = np.concatenate([np.full(400, 0.25), np.full(3, 0.75)])
    labels = np.zeros(x.size, dtype=int)

    image = cluster_rgb_image(x, y, labels, EDGES, EDGES)
    bright = image[int(0.25 * 20), int(0.25 * 20)].astype(float).sum()
    faint = image[int(0.75 * 20), int(0.75 * 20)].astype(float).sum()
    assert bright > faint, "the dense bin is not brighter than the sparse one"
    assert faint > 0, "a sparsely populated bin must still be visible"
    del rng


def test_an_overlapping_bin_takes_the_dominant_cluster():
    """One bin, one colour — the majority contributor wins."""
    # Nine points of cluster 0 and one of cluster 1 in the same bin.
    x = np.full(10, 0.52)
    y = np.full(10, 0.52)
    labels = np.array([0] * 9 + [1])
    image = cluster_rgb_image(x, y, labels, EDGES, EDGES)
    bin_colour = image[int(0.52 * 20), int(0.52 * 20)].astype(float)
    expected = np.array(cluster_color(0), dtype=float)
    assert np.allclose(bin_colour / bin_colour.sum(), expected / expected.sum(), atol=0.02)


def test_noise_is_drawn_apart_from_the_clusters():
    """Label -1 gets the desaturated noise colour, and can be hidden."""
    x = np.array([0.25, 0.75])
    y = np.array([0.25, 0.75])
    labels = np.array([0, -1])

    shown = cluster_rgb_image(x, y, labels, EDGES, EDGES, include_noise=True)
    noise_bin = shown[int(0.75 * 20), int(0.75 * 20)]
    assert noise_bin.sum() > 0
    expected = np.array(NOISE_COLOR, dtype=float)
    assert np.allclose(
        noise_bin / noise_bin.sum(), expected / expected.sum(), atol=0.02
    )

    hidden = cluster_rgb_image(x, y, labels, EDGES, EDGES, include_noise=False)
    assert hidden[int(0.75 * 20), int(0.75 * 20)].sum() == 0
    assert hidden[int(0.25 * 20), int(0.25 * 20)].sum() > 0


def test_empty_bins_stay_at_the_background():
    """Only occupied bins are painted."""
    x, y, labels = two_clusters(n=50)
    image = cluster_rgb_image(x, y, labels, EDGES, EDGES)
    assert image[0, -1].sum() == 0


def test_non_finite_points_are_dropped():
    """Filtered values arrive as NaN rather than being removed from the array."""
    x = np.array([0.25, np.nan, 0.75, np.inf])
    y = np.array([0.25, 0.5, 0.75, 0.5])
    labels = np.array([0, 0, 1, 1])
    image = cluster_rgb_image(x, y, labels, EDGES, EDGES)
    assert image is not None
    assert image[int(0.25 * 20), int(0.25 * 20)].sum() > 0
    assert image[int(0.75 * 20), int(0.75 * 20)].sum() > 0


def test_nothing_to_draw_returns_none():
    """A caller can fall back to the density map instead of showing a blank."""
    assert cluster_rgb_image(np.array([]), np.array([]), np.array([]), EDGES, EDGES) is None
    assert cluster_rgb_image(
        np.array([np.nan]), np.array([np.nan]), np.array([0]), EDGES, EDGES
    ) is None
    # Mismatched lengths: labels from a different dataset than the points.
    assert cluster_rgb_image(
        np.array([0.5, 0.5]), np.array([0.5, 0.5]), np.array([0]), EDGES, EDGES
    ) is None


def test_the_palette_repeats_predictably():
    """More clusters than palette entries must still get distinct neighbours."""
    assert cluster_color(0) == CLUSTER_COLORS[0]
    assert cluster_color(len(CLUSTER_COLORS)) == CLUSTER_COLORS[0]
    assert cluster_color(-1) == NOISE_COLOR
    assert cluster_color(1) != cluster_color(2)
