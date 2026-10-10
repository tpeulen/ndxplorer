"""The end-to-end distance distribution of a worm-like chain (numpy only).

The exact spectral solution of the Kratky-Porod chain (Saito, Takahashi and
Yunoki 1967; Spakowitz and Wang 2005): the tangent diffuses on the sphere with
rate ``1/(2 lp)`` per unit contour while the chain's end-to-end vector
accumulates, so the Fourier transform of the end-to-end vector distribution is

    G(k, L) = [exp(L M(k))]_00,   M = -diag(l(l+1)/(2 lp)) - i k C

in the orthonormal Legendre basis, with ``C`` the tridiagonal matrix of
``cos(theta)``. The radial distribution follows from the inverse transform,

    P(R) = (2 R / pi) * integral_0^inf k sin(k R) G(k, L) dk.

Its second moment is the Kratky-Porod ``<R^2> = 2 lp L (1 - lp/L (1 - exp(-L/lp)))``
(checked in the tests), it tends to the Gaussian chain for ``L >> lp`` and to a
rod, ``R = L``, for ``L << lp``. nDXplorer's curve equations call it as
``wlc_pdf(R, L, lp)`` for the phasor FRET trajectory of a worm-like linker.
"""

from __future__ import annotations

import numpy as np

__all__ = ["wlc_pdf", "kratky_porod_r2"]

_CACHE: dict[tuple, tuple] = {}
_CHUNK = 24
KMAX = 30.0
NMAX = 48


def kratky_porod_r2(contour, persistence):
    """Mean-square end-to-end distance of a worm-like chain (the Kratky-Porod result)."""
    contour = np.asarray(contour, dtype=float)
    return 2.0 * persistence * contour * (
        1.0 - persistence / contour * (1.0 - np.exp(-contour / persistence)))


def _spectrum(lp: float, kmax: float, nk: int, nmax: int) -> tuple[np.ndarray, ...]:
    """The wave numbers, eigenvalues and the weights ``V[0, j] (V^-1)[j, 0]`` of ``M(k)``."""
    key = (round(lp, 9), round(kmax, 9), nk, nmax)
    hit = _CACHE.get(key)
    if hit is not None:
        return hit
    k = (np.arange(nk) + 0.5) * (kmax / nk)
    ell = np.arange(nmax, dtype=float)
    c = (ell[:-1] + 1.0) / np.sqrt((2.0 * ell[:-1] + 1.0) * (2.0 * ell[:-1] + 3.0))
    coupling = np.diag(c, 1) + np.diag(c, -1)
    matrices = -np.diag(ell * (ell + 1.0) / (2.0 * lp))[None] - 1j * k[:, None, None] * coupling[None]
    values, vectors = np.linalg.eig(matrices)
    weights = vectors[:, 0, :] * np.linalg.inv(vectors)[:, :, 0]
    if len(_CACHE) > 8:
        _CACHE.clear()
    _CACHE[key] = (k, values, weights)
    return _CACHE[key]


def wlc_pdf(r, contour, persistence, nmax=None):
    """Radial end-to-end distribution of a worm-like chain, one row per contour length.

    Parameters
    ----------
    r : array_like, shape (n,)
        The distances (any length unit, uniform grid, ``0 < r <= max(contour)``).
    contour : float or array_like, shape (m,)
        Contour length(s) of the chain, in the unit of *r*.
    persistence : float
        Persistence length, in the same unit.
    nmax : int, optional
        Legendre basis size (default: from the stiffest chain asked for).

    Returns
    -------
    numpy.ndarray, shape (m, n)
        ``P(r)`` of every contour length, each row non-negative and summing to 1
        (the weight of a distance bin, ready to average a decay over).
    """
    r = np.asarray(r, dtype=float).ravel()
    lengths = np.atleast_1d(np.asarray(contour, dtype=float)).ravel()
    lp = float(persistence)
    shortest, longest = float(lengths.min()), float(lengths.max())
    kmax = KMAX /  min(shortest, 4.0 * lp)
    nk = int(np.clip(kmax * float(r.max()) / np.pi * 2.5, 256, 2000))
    nmax = int(nmax or np.clip(0.8 * kmax * longest + 10.0, 24, NMAX))
    k, values, weights = _spectrum(lp, kmax, nk, nmax)
    window = np.exp(-0.5 * (k / (0.8 * kmax)) ** 2) * k
    transform = np.sin(np.outer(k, r))
    rows = []
    for start in range(0, lengths.size, _CHUNK):
        chunk = lengths[start:start + _CHUNK]
        modes = np.exp(values[None] * chunk[:, None, None])
        g = np.einsum("kj,tkj->tk", weights, modes).real
        rows.append((g * window[None]) @ transform)
    p = np.clip(np.vstack(rows) * (2.0 * r / np.pi)[None], 0.0, None)
    # A chain never reaches past its contour length; the transform's smoothing (one standard
    # deviation 1/(0.8 kmax)) spreads a rod's peak symmetrically over it, so the cut sits that far out.
    p[r[None, :] > lengths[:, None] + 2.5 / (0.8 * kmax)] = 0.0
    total = p.sum(axis=1, keepdims=True)
    return p / np.where(total > 0.0, total, 1.0)
