"""Colour a 2-D histogram by cluster membership.

The ordinary 2-D view is a density map: one number per bin, rendered through a
continuous colormap. That answers "where are the points" and says nothing about
*which* population they belong to, so after clustering the only way to see a
cluster was to isolate it with the spinner and look at one at a time.

This builds the other view — every cluster at once, each in its own colour — as
an RGB image the same image item can draw.

Two choices worth stating, because both are lossy in a way the viewer should
know about:

**Each bin takes one colour: its dominant cluster.** A bin where two clusters
overlap is drawn as whichever contributed more points, so a boundary looks
crisper than it is. That is unavoidable for one pixel and one colour; the
per-cluster spinner view remains the honest way to inspect an overlap.

**Brightness still carries density.** A bin holding two points and a bin holding
two hundred would otherwise look identical, which would turn a scatter of noise
into something that reads like a population. Saturation is scaled by count so
the density information survives the recolouring.
"""

from __future__ import annotations

from typing import Optional, Sequence

import numpy as np

__all__ = [
    "CLUSTER_COLORS",
    "NOISE_COLOR",
    "cluster_color",
    "cluster_rgb_image",
]

#: Qualitative palette, chosen to stay distinguishable in order. Cluster ``n``
#: takes entry ``n % len``, so the first ten clusters are always distinct.
CLUSTER_COLORS: tuple = (
    (31, 119, 180), (255, 127, 14), (44, 160, 44), (214, 39, 40),
    (148, 103, 189), (140, 86, 75), (227, 119, 194), (127, 127, 127),
    (188, 189, 34), (23, 190, 207),
)

#: Unclustered points (label ``-1``). Deliberately dark and desaturated: noise
#: should recede rather than compete with the populations.
NOISE_COLOR: tuple = (90, 90, 90)


def cluster_color(label: int) -> tuple:
    """Return the ``(r, g, b)`` colour for a cluster label.

    Parameters
    ----------
    label : int
        Cluster label; ``-1`` (noise) returns :data:`NOISE_COLOR`.

    Returns
    -------
    tuple of int
        ``(r, g, b)`` in ``0..255``.
    """
    label = int(label)
    if label < 0:
        return NOISE_COLOR
    return CLUSTER_COLORS[label % len(CLUSTER_COLORS)]


def cluster_rgb_image(
    x: np.ndarray,
    y: np.ndarray,
    labels: np.ndarray,
    x_edges: np.ndarray,
    y_edges: np.ndarray,
    log_counts: bool = False,
    include_noise: bool = True,
    background: Sequence[int] = (0, 0, 0),
) -> Optional[np.ndarray]:
    """Build an RGB image of a 2-D histogram coloured by dominant cluster.

    Parameters
    ----------
    x, y : numpy.ndarray
        Point coordinates, aligned with *labels*. Non-finite entries are
        dropped (the filtered value arrays carry ``NaN`` where a point was
        masked out, rather than being shortened).
    labels : numpy.ndarray
        Cluster label per point; ``-1`` is noise.
    x_edges, y_edges : numpy.ndarray
        Bin edges of the histogram being coloured, so the result lines up with
        the density view exactly.
    log_counts : bool
        Scale saturation by ``log10`` of the count, matching the density view's
        log option — without it a single very dense bin flattens everything
        else to near-black.
    include_noise : bool
        Draw ``-1`` points in the noise colour. ``False`` leaves those bins at
        the background, which is the clearer read when noise dominates.
    background : sequence of int
        Colour of bins holding no points.

    Returns
    -------
    numpy.ndarray or None
        ``(ny, nx, 3)`` uint8 image, or ``None`` if there is nothing to draw.
    """
    x = np.asarray(x, dtype=float).ravel()
    y = np.asarray(y, dtype=float).ravel()
    labels = np.asarray(labels).ravel()
    if x.size == 0 or x.size != y.size or labels.size != x.size:
        return None

    finite = np.isfinite(x) & np.isfinite(y)
    if not include_noise:
        finite &= labels >= 0
    if not finite.any():
        return None
    x, y, labels = x[finite], y[finite], labels[finite]

    x_edges = np.asarray(x_edges, dtype=float)
    y_edges = np.asarray(y_edges, dtype=float)
    n_y, n_x = y_edges.size - 1, x_edges.size - 1
    if n_y < 1 or n_x < 1:
        return None

    present = np.unique(labels)
    # One histogram per cluster, stacked so the dominant cluster of each bin is
    # an argmax rather than a per-bin mode over the raw points.
    stack = np.zeros((present.size, n_y, n_x), dtype=np.float64)
    for i, label in enumerate(present):
        mask = labels == label
        counts, _, _ = np.histogram2d(
            y[mask], x[mask], bins=(y_edges, x_edges)
        )
        stack[i] = counts

    total = stack.sum(axis=0)
    occupied = total > 0
    image = np.zeros((n_y, n_x, 3), dtype=np.uint8)
    image[..., :] = np.asarray(background, dtype=np.uint8)
    if not occupied.any():
        return image

    dominant = np.argmax(stack, axis=0)

    # Saturation from the count, so density is not thrown away by recolouring.
    weight = np.log10(total, out=np.zeros_like(total), where=occupied) if log_counts else total
    if log_counts:
        weight = weight - weight[occupied].min() + 1.0 if occupied.any() else weight
    top = float(weight[occupied].max()) if occupied.any() else 1.0
    if top <= 0:
        top = 1.0
    # A floor keeps a single-point bin visible instead of black.
    scale = np.clip(weight / top, 0.0, 1.0)
    scale = np.where(occupied, 0.35 + 0.65 * scale, 0.0)

    palette = np.array([cluster_color(label) for label in present], dtype=np.float64)
    coloured = palette[dominant] * scale[..., None]
    image[occupied] = coloured[occupied].astype(np.uint8)
    return image
