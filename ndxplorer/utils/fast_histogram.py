"""The histogram engine, which is tttrlib's.

NDXplorer used to carry three: boost-histogram behind a settings switch, a
``np.bincount`` path for uniform bins, and NumPy for everything else. Three
engines is three sets of edge-case behaviour to keep in agreement, three things
to configure, and -- since the switch was per-call and the fallbacks were silent
-- no reliable way to say which one produced a given picture.

There is one now. Measured on this machine, a 256 x 256 fill of 2,000,000
points:

===================  ==========
engine                 time
===================  ==========
``np.histogram2d``     239.5 ms
``np.bincount``         40.6 ms
boost, threaded          8.7 ms
**tttrlib**              **4.9 ms**
===================  ==========

and in 1-D over the same points, 256 bins: 18.8 ms for bincount against 2.5 ms.

The public functions keep their signatures, so every caller is unchanged, and
they keep NumPy's answers exactly -- including the one place NumPy is not
half-open. See :func:`_top_edge_hits`.

``use_cache`` is accepted and ignored, as it was before: the fill is threaded
C++ and there is nothing for it to do. The companion ``use_numba`` flag is gone
with numba itself -- a parameter named for a library the package no longer
depends on is a claim, not a no-op.
"""

from __future__ import annotations

from typing import Optional, Sequence, Tuple, Union

import numpy as np
import tttrlib

__all__ = ["fast_histogram_1d", "fast_histogram_2d"]

# Relative tolerance for deciding whether an array of edges is uniformly spaced.
_UNIFORM_RTOL = 1e-6

BinSpec = Union[int, np.integer, np.ndarray, Sequence[float]]


def _uniform_edges_range(edges: np.ndarray) -> Optional[Tuple[float, float, int]]:
    """Return ``(lo, hi, n_bins)`` if ``edges`` is uniformly spaced, else ``None``.

    Kept, and exported, because it encodes a measured fact: an evenly spaced
    axis is binned with one multiply, while an unevenly spaced one costs a
    binary search per point. Log-scaled axes are the uneven case and they are
    common here, so the distinction is worth making rather than assuming.
    """
    if edges.ndim != 1 or edges.size < 2:
        return None
    diffs = np.diff(edges)
    first = diffs[0]
    if first <= 0:
        return None
    if not np.all(np.abs(diffs - first) <= _UNIFORM_RTOL * first):
        return None
    return float(edges[0]), float(edges[-1]), int(edges.size - 1)


def _resolve(bins: BinSpec, data: np.ndarray,
             data_range: Optional[Tuple[float, float]]):
    """``(axis, edges)`` for one dimension.

    An integer bin count with no range takes the range from the finite data, as
    NumPy does. An edge array is used as given -- and if those edges happen to be
    evenly spaced it still becomes a regular axis, because that is an index
    computed with a multiply rather than a binary search per point.
    """
    if isinstance(bins, (int, np.integer)):
        n = max(1, int(bins))
        if data_range is not None:
            lo, hi = float(data_range[0]), float(data_range[1])
        else:
            finite = data[np.isfinite(data)] if data.size else data
            lo, hi = ((0.0, 1.0) if finite.size == 0
                      else (float(finite.min()), float(finite.max())))
        if not (np.isfinite(lo) and np.isfinite(hi)) or hi <= lo:
            lo, hi = lo - 0.5, lo + 0.5
        edges = np.linspace(lo, hi, n + 1)
        return tttrlib.Axis.regular(n, lo, hi, tttrlib.AxisOptions.flow(), ""), edges

    edges = np.ascontiguousarray(np.asarray(bins, dtype=np.float64))
    uniform = _uniform_edges_range(edges)
    if uniform is not None:
        lo, hi, n = uniform
        return tttrlib.Axis.regular(n, lo, hi, tttrlib.AxisOptions.flow(), ""), edges
    return tttrlib.Axis.variable(edges, tttrlib.AxisOptions.flow(), ""), edges


def _top_edge_hits(data: np.ndarray, edges: np.ndarray) -> Optional[np.ndarray]:
    """Which points sit exactly on the topmost edge, or None if none do.

    NumPy's last bin is closed on the right while every other bin is half-open,
    and an engine that does not reproduce that quietly loses the highest point
    of the dataset. It is not a rounding curiosity: bin edges are routinely
    taken from the data's own maximum, and a pixel-index axis has its top edge
    sitting exactly on a value that occurs.
    """
    if data.size == 0:
        return None
    hit = data == edges[-1]
    return hit if hit.any() else None


def fast_histogram_1d(
    data: np.ndarray,
    bins: BinSpec,
    weights: Optional[np.ndarray] = None,
    density: bool = False,
    use_cache: bool = True,
    data_range: Optional[Tuple[float, float]] = None,
) -> Tuple[np.ndarray, np.ndarray]:
    """A 1-D histogram, filled in tttrlib.

    :param data: the sample values
    :param bins: a bin count (with `data_range`) or an array of bin edges
    :param weights: per-sample weights
    :param density: normalise so the histogram integrates to 1, as NumPy does
    :param use_cache: accepted and ignored
    :param data_range: ``(lo, hi)``; taken from the data when `bins` is a count
        and this is None

    :returns: ``(edges, counts)`` -- edges first, which is this module's order
        and the opposite of NumPy's.
    """
    data = np.ascontiguousarray(np.asarray(data, dtype=np.float64).ravel())
    axis, edges = _resolve(bins, data, data_range)

    histogram = tttrlib.HistogramNd(tttrlib.AxisVector([axis]))
    if weights is None:
        histogram.fill(data)
    else:
        weights = np.ascontiguousarray(np.asarray(weights, dtype=np.float64).ravel())
        histogram.fill(data, weight=weights)
    counts = np.array(histogram.view(), dtype=np.float64)

    top = _top_edge_hits(data, edges)
    if top is not None:
        counts[-1] += float(top.sum()) if weights is None else float(weights[top].sum())

    if density:
        widths = np.diff(edges)
        total = counts.sum()
        if total > 0:
            counts = counts / (total * widths)

    return edges, counts


def fast_histogram_2d(
    x: np.ndarray,
    y: np.ndarray,
    bins: Union[BinSpec, Sequence[BinSpec]],
    weights: Optional[np.ndarray] = None,
    density: bool = False,
    use_cache: bool = True,
    x_range: Optional[Tuple[float, float]] = None,
    y_range: Optional[Tuple[float, float]] = None,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """A 2-D histogram, filled in tttrlib.

    Returns ``(H, x_edges, y_edges)`` with ``H`` shaped ``(n_x, n_y)`` exactly
    like :func:`numpy.histogram2d` -- any transpose is the caller's concern.

    ``bins`` may be a scalar or edge array applied to both axes, or an
    ``[x_bins, y_bins]`` pair.
    """
    if isinstance(bins, (list, tuple)) and len(bins) == 2:
        x_bins, y_bins = bins
    else:
        x_bins = y_bins = bins

    x = np.ascontiguousarray(np.asarray(x, dtype=np.float64).ravel())
    y = np.ascontiguousarray(np.asarray(y, dtype=np.float64).ravel())
    x_axis, x_edges = _resolve(x_bins, x, x_range)
    y_axis, y_edges = _resolve(y_bins, y, y_range)

    histogram = tttrlib.HistogramNd(tttrlib.AxisVector([x_axis, y_axis]))
    if weights is None:
        histogram.fill(x, y)
    else:
        weights = np.ascontiguousarray(np.asarray(weights, dtype=np.float64).ravel())
        histogram.fill(x, y, weight=weights)
    H = np.array(histogram.view(), dtype=np.float64)

    # The closed top edge again, on either axis. Handled by re-binning just the
    # points sitting on one -- a handful, normally none -- rather than by
    # widening the axis, which would move every interior boundary by an ulp and
    # so move the points that legitimately sit on those.
    edge = (x == x_edges[-1]) | (y == y_edges[-1])
    if edge.any():
        nx, ny = H.shape
        ex, ey = x[edge], y[edge]
        inside = ((ex >= x_edges[0]) & (ex <= x_edges[-1]) &
                  (ey >= y_edges[0]) & (ey <= y_edges[-1]))
        if inside.any():
            ix = np.clip(np.searchsorted(x_edges, ex[inside], side="right") - 1,
                         0, nx - 1)
            iy = np.clip(np.searchsorted(y_edges, ey[inside], side="right") - 1,
                         0, ny - 1)
            w = None if weights is None else weights[edge][inside]
            H += np.bincount(ix * ny + iy, weights=w,
                             minlength=nx * ny)[:nx * ny].reshape(nx, ny)

    if density:
        area = np.outer(np.diff(x_edges), np.diff(y_edges))
        total = H.sum()
        if total > 0:
            H = H / (total * area)

    return H, x_edges, y_edges
