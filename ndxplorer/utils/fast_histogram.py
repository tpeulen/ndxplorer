"""Fast uniform-bin histograms for the interactive redraw path.

NumPy's :func:`numpy.histogram` / :func:`numpy.histogram2d` use a general
``searchsorted``-based algorithm that ignores the fact that the bins are
uniform. For the millions of bursts NDXplorer routinely displays this dominates
the per-interaction latency (a 2D histogram of ~2M points takes ~120 ms).

When the bins are uniform — which is the case for every histogram built from an
integer bin count plus an ``(lo, hi)`` range (the wired default path) — the bin
index of each point can be computed directly with a single multiply, letting
:func:`numpy.bincount` build the histogram in one O(n) pass. This is ~6x faster
for both 1D and 2D while producing bit-identical counts.

For non-uniform edges (e.g. log-spaced bins) the functions transparently fall
back to the corresponding NumPy routine, so callers get the fast path for free
without having to reason about bin spacing themselves.

The public functions ``fast_histogram_1d`` / ``fast_histogram_2d`` match the
signatures expected by :mod:`ndxplorer.utils.performance`. The ``use_cache``
keyword is accepted for API compatibility; the bincount path is already
vectorised and dependency-free, so it is currently a no-op. The companion
``use_numba`` keyword is gone with numba itself -- a parameter named for a
library the package no longer depends on is a claim, not a no-op.
"""

from __future__ import annotations

from typing import Optional, Sequence, Tuple, Union

import numpy as np

__all__ = ["fast_histogram_1d", "fast_histogram_2d"]

# Relative tolerance for deciding whether an array of edges is uniformly spaced.
_UNIFORM_RTOL = 1e-6

BinSpec = Union[int, np.integer, np.ndarray, Sequence[float]]


def _uniform_edges_range(edges: np.ndarray) -> Optional[Tuple[float, float, int]]:
    """Return ``(lo, hi, n_bins)`` if ``edges`` is uniformly spaced, else ``None``."""
    if edges.ndim != 1 or edges.size < 2:
        return None
    diffs = np.diff(edges)
    first = diffs[0]
    if first <= 0:
        return None
    if not np.all(np.abs(diffs - first) <= _UNIFORM_RTOL * first):
        return None
    return float(edges[0]), float(edges[-1]), int(edges.size - 1)


def _resolve_uniform(
    bins: BinSpec,
    data_range: Optional[Tuple[float, float]],
) -> Optional[Tuple[float, float, int, np.ndarray]]:
    """Resolve ``bins``/``data_range`` into ``(lo, hi, n_bins, edges)``.

    Returns ``None`` when the request cannot be served by the fast uniform path
    (non-uniform edges, or an integer bin count with no usable range).
    """
    if isinstance(bins, (int, np.integer)):
        if data_range is None:
            return None
        lo, hi = float(data_range[0]), float(data_range[1])
        n = int(bins)
        if n < 1 or not (np.isfinite(lo) and np.isfinite(hi)) or hi <= lo:
            return None
        return lo, hi, n, np.linspace(lo, hi, n + 1)

    edges = np.asarray(bins, dtype=np.float64)
    resolved = _uniform_edges_range(edges)
    if resolved is None:
        return None
    lo, hi, n = resolved
    return lo, hi, n, edges


def _digitize_uniform(
    data: np.ndarray, lo: float, hi: float, n_bins: int
) -> Tuple[np.ndarray, np.ndarray]:
    """Return ``(indices, in_range_mask)`` for uniform binning of ``data``.

    Points on the right edge (``data == hi``) fall into the last bin, matching
    NumPy's closed-on-the-right final bin. Points outside ``[lo, hi]`` and
    non-finite values are excluded via the returned boolean mask.
    """
    inv = n_bins / (hi - lo)
    # NaNs compare False in both comparisons, so they are excluded by in_range.
    in_range = (data >= lo) & (data <= hi)
    # NaN/Inf cast to an arbitrary int here but are dropped by in_range; silence
    # the "invalid value encountered in cast" warning they would otherwise raise.
    with np.errstate(invalid="ignore"):
        idx = ((data - lo) * inv).astype(np.intp)
    # Fold the closed right edge (and any float rounding to n_bins) into the last bin.
    np.clip(idx, 0, n_bins - 1, out=idx)
    return idx, in_range


def fast_histogram_1d(
    data: np.ndarray,
    bins: BinSpec,
    weights: Optional[np.ndarray] = None,
    density: bool = False,
    use_cache: bool = True,
    data_range: Optional[Tuple[float, float]] = None,
) -> Tuple[np.ndarray, np.ndarray]:
    """Compute a 1D histogram, using a fast uniform-bin path when possible.

    Parameters
    ----------
    data : np.ndarray
        Sample values (1D).
    bins : int or array-like
        Either a bin count (uniform; requires ``data_range``) or an array of
        bin edges.
    weights : np.ndarray, optional
        Per-sample weights.
    density : bool
        If True, normalise so the histogram integrates to 1 (as in NumPy).
    use_cache : bool
        Accepted for API compatibility; currently unused.
    data_range : tuple of float, optional
        ``(lo, hi)`` range, required when ``bins`` is an integer.

    Returns
    -------
    edges : np.ndarray
        Bin edges, length ``n_bins + 1``.
    counts : np.ndarray
        Histogram counts (float64), length ``n_bins``.
    """
    resolved = _resolve_uniform(bins, data_range)
    if resolved is None:
        counts, edges = np.histogram(
            data, bins=bins, range=data_range, weights=weights, density=density
        )
        return edges, counts.astype(np.float64, copy=False)

    lo, hi, n_bins, edges = resolved
    data = np.asarray(data)
    idx, in_range = _digitize_uniform(data, lo, hi, n_bins)

    if weights is None:
        counts = np.bincount(idx[in_range], minlength=n_bins)[:n_bins].astype(np.float64)
    else:
        weights = np.asarray(weights, dtype=np.float64)
        counts = np.bincount(
            idx[in_range], weights=weights[in_range], minlength=n_bins
        )[:n_bins]

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
    """Compute a 2D histogram, using a fast uniform-bin path when possible.

    Returns ``(H, x_edges, y_edges)`` with ``H`` shaped ``(n_x, n_y)`` exactly
    like :func:`numpy.histogram2d` (any transpose is the caller's concern).

    ``bins`` may be a scalar/edge-array applied to both axes, or a
    ``[x_bins, y_bins]`` pair.
    """
    if isinstance(bins, (list, tuple)) and len(bins) == 2:
        x_bins, y_bins = bins
    else:
        x_bins = y_bins = bins

    rx = _resolve_uniform(x_bins, x_range)
    ry = _resolve_uniform(y_bins, y_range)
    if rx is None or ry is None:
        _range = [x_range, y_range] if (x_range is not None and y_range is not None) else None
        H, xe, ye = np.histogram2d(
            x, y, bins=[x_bins, y_bins], range=_range, weights=weights, density=density
        )
        return H.astype(np.float64, copy=False), xe, ye

    x_lo, x_hi, nx, x_edges = rx
    y_lo, y_hi, ny, y_edges = ry
    x = np.asarray(x)
    y = np.asarray(y)

    ix, x_ok = _digitize_uniform(x, x_lo, x_hi, nx)
    iy, y_ok = _digitize_uniform(y, y_lo, y_hi, ny)
    good = x_ok & y_ok

    lin = ix[good] * ny + iy[good]
    if weights is None:
        flat = np.bincount(lin, minlength=nx * ny)
    else:
        weights = np.asarray(weights, dtype=np.float64)
        flat = np.bincount(lin, weights=weights[good], minlength=nx * ny)

    H = flat[: nx * ny].astype(np.float64, copy=False).reshape(nx, ny)

    if density:
        area = np.outer(np.diff(x_edges), np.diff(y_edges))
        total = H.sum()
        if total > 0:
            H = H / (total * area)

    return H, x_edges, y_edges
