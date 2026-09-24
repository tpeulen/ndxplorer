"""2-D Gaussian mixtures on the map: the fit, the ellipses, the files. Qt-free.

The Gaussian Fit panel seeds Gaussians by clicking on the 2-D histogram, fits
them to the gated points with an EM that can hold any centre or width (and
leaves crosslinked parameters to their master), draws each as 1σ/2σ/3σ
ellipses on the map and as curves on the marginals, turns one into an
elliptical gate, and saves or loads the mixture. Both GUIs call this module
for all of it; they differ only in how they draw.

Conventions
-----------
* A 2-D histogram ``H`` is ``(n_y, n_x)``, row 0 at the lowest y -- what
  :func:`ndxplorer.utils.histogram_computation.compute_histograms` returns.
* ``log_x``/``log_y`` say that an axis is fitted and drawn in log space. The
  Gaussian lives in that space; means and covariances are stored in value
  space, mapped through the linearisation ``J = diag(1/mu)`` of ``log``.
* The Gaussians themselves are the parameter group of
  :mod:`ndxplorer.core.gaussian_parameters`; functions here take the
  components it reads out (:class:`~ndxplorer.core.gaussian_parameters.GaussianComponent`)
  or plain ``(mu, cov, w)`` rows.
"""

from __future__ import annotations

import csv
import json
import os
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from ..logging_config import logging

__all__ = [
    "GMM_DEFAULTS",
    "GaussianFitError",
    "GaussianMixtureFixedEM",
    "PALETTE",
    "axis_mismatch",
    "colour_of",
    "component_marginals",
    "ellipse",
    "fit_mixture",
    "load_gaussians",
    "load_gmm_settings",
    "local_moments",
    "marginal_pdf",
    "model_grid_2d",
    "model_marginals",
    "moments",
    "save_gaussians",
    "save_gmm_settings",
    "seed_component",
    "to_fit_space",
    "to_value_space",
]

#: Colour of Gaussian ``i`` is ``PALETTE[i % len]`` -- on the map, the
#: marginals and wherever else it is drawn.
PALETTE: Tuple[str, ...] = ("#ff0000", "#00aa00", "#0000ff", "#aa00aa", "#00aaaa", "#ffaa00")

#: The ellipses drawn per Gaussian, and their line widths.
SIGMA_LEVELS: Tuple[float, ...] = (1.0, 2.0, 3.0)

_EPS = 1e-12


def colour_of(index: int) -> Tuple[int, int, int, int]:
    """The RGBA colour of Gaussian *index*."""
    hexa = PALETTE[int(index) % len(PALETTE)].lstrip("#")
    return (int(hexa[0:2], 16), int(hexa[2:4], 16), int(hexa[4:6], 16), 255)


class GaussianFitError(Exception):
    """A fit that cannot run, with the message box's title and text."""

    def __init__(self, title: str, text: str) -> None:
        super().__init__(text)
        self.title = title
        self.text = text


# ------------------------------------------------------------------ settings
#: The EM's settings and the panel's seeding window, as saved in
#: ``gmm_settings.json`` in the user folder.
GMM_DEFAULTS: Dict[str, Any] = {
    "tol": 1e-3,                         # float > 0
    "reg_covar": 1e-6,                   # float >= 0
    "max_iter": 200,                     # int > 0
    "verbose": 0,                        # int >= 0
    "local_window_bins": 10,             # int >= 1, half-window in bins for a seed's width
    "weight_floor": 0.0,                 # float >= 0, minimum component weight (0 disables)
    "fix_new_means": True,               # bool, hold the centre of a Gaussian seeded by a click
}

GMM_SETTINGS_FILENAME = "gmm_settings.json"


def _settings_file():
    from ..settings import ensure_default_settings, get_settings_path

    ensure_default_settings()
    return get_settings_path() / GMM_SETTINGS_FILENAME


def load_gmm_settings() -> Dict[str, Any]:
    """The user's GMM settings, or the defaults when missing or unreadable.

    A missing file is written with the defaults, so the user has one to edit.
    """
    try:
        path = _settings_file()
    except Exception:  # noqa: BLE001 - no settings folder: defaults
        return dict(GMM_DEFAULTS)
    if not path.exists():
        try:
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(GMM_DEFAULTS, handle, indent=2)
        except OSError:
            pass
        return dict(GMM_DEFAULTS)
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return dict(GMM_DEFAULTS)
    merged = dict(GMM_DEFAULTS)
    merged.update({k: data.get(k, v) for k, v in GMM_DEFAULTS.items()})
    return merged


def save_gmm_settings(cfg: Dict[str, Any]) -> Optional[str]:
    """Write the GMM settings to the user folder; returns the path, or ``None``."""
    out = dict(GMM_DEFAULTS)
    out.update({k: cfg.get(k, v) for k, v in GMM_DEFAULTS.items()})
    try:
        path = _settings_file()
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(out, handle, indent=2)
        return str(path)
    except Exception as exc:  # noqa: BLE001
        logging.warning("could not save GMM settings: %s", exc)
        return None


# ------------------------------------------------------------------------ EM
class GaussianMixtureFixedEM:
    """2D GMM EM with per-component mean/covariance locking.

    Full-covariance EM (numpy only) that holds the masked mean and covariance
    elements at their starting values -- the same contract as ChiSurf's
    ``GaussianMixture(fix_means=..., fix_covariances=...)``. Works in the
    caller's "fit space" (log-transformed axes as needed).
    """

    def __init__(self, means_init, covs_init, weights_init=None,
                 reg_covar=1e-6, max_iter=200, tol=1e-3, verbose=0, weight_floor=0.0):
        self.means_init = np.array(means_init, dtype=float)
        self.covs_init = np.array(covs_init, dtype=float)
        K = self.means_init.shape[0]
        if weights_init is None:
            self.weights_init = np.ones(K, dtype=float) / K
        else:
            w = np.array(weights_init, dtype=float)
            s = float(np.sum(w))
            self.weights_init = (w / s) if s > 0 else (np.ones(K) / K)
        self.reg_covar = float(reg_covar)
        self.max_iter = int(max_iter)
        self.tol = float(tol)
        self.verbose = int(verbose)
        self.weight_floor = float(max(0.0, weight_floor))
        self.means_ = None
        self.covs_ = None
        self.weights_ = None
        self.converged_ = False
        self.n_iter_ = 0
        self.lower_bound_ = -np.inf
        self._em = None

    def fit(self, X, fix_mu_mask, fix_cov_mask, mu_fixed_vals, cov_fixed_vals):
        """Fit the mixture with component locks and return ``self``.

        Parameters
        ----------
        X : numpy.ndarray
            ``(N, 2)`` fit-space coordinates.
        fix_mu_mask : numpy.ndarray (K, 2) bool
            ``True`` holds that mean element at ``mu_fixed_vals``.
        fix_cov_mask : numpy.ndarray (K, 2, 2) bool
            ``True`` holds that covariance element (its mate mirrored for
            symmetry) at ``cov_fixed_vals``.
        mu_fixed_vals, cov_fixed_vals : numpy.ndarray
            Anchor values for the locked parameters.
        """
        means, covs, weights, n_iter, lower = _fixed_em(
            np.asarray(X, dtype=float), np.asarray(mu_fixed_vals, dtype=float),
            np.asarray(cov_fixed_vals, dtype=float), self.weights_init,
            np.asarray(fix_mu_mask, dtype=bool), np.asarray(fix_cov_mask, dtype=bool),
            self.reg_covar, self.max_iter, self.tol)
        self._em = None
        self.means_, self.covs_, self.weights_ = means, covs, weights
        if self.weight_floor > 0:
            w = np.maximum(np.asarray(self.weights_, dtype=float), self.weight_floor)
            self.weights_ = w / w.sum()
        self.converged_ = n_iter < self.max_iter
        self.n_iter_ = n_iter
        self.lower_bound_ = lower
        return self


def _log_densities(X: np.ndarray, means: np.ndarray, covs: np.ndarray) -> np.ndarray:
    """``(N, K)`` log densities of *X* under each full-covariance Gaussian."""
    out = np.empty((X.shape[0], means.shape[0]))
    d = X.shape[1]
    for k in range(means.shape[0]):
        try:
            chol = np.linalg.cholesky(covs[k])
        except np.linalg.LinAlgError:  # a held element broke positive definiteness
            chol = np.linalg.cholesky(_floored(covs[k], 1e-9))
        z = np.linalg.solve(chol, (X - means[k]).T)
        out[:, k] = -0.5 * np.sum(z * z, axis=0) - np.log(np.diag(chol)).sum() \
            - 0.5 * d * np.log(2.0 * np.pi)
    return out


def _floored(cov: np.ndarray, reg: float) -> np.ndarray:
    """*cov* symmetric, its eigenvalues floored, plus the ridge *reg*."""
    cov = 0.5 * (cov + cov.T)
    vals, vecs = np.linalg.eigh(cov)
    vals = np.maximum(vals, np.finfo(float).tiny)
    return (vecs * vals) @ vecs.T + reg * np.eye(cov.shape[0])


def _fixed_em(X, means, covs, weights, fix_mu, fix_cov, reg, max_iter, tol):
    """EM for a full-covariance mixture holding the masked elements.

    A held mean element keeps its starting value; a held covariance element is
    stamped back after each M-step, its off-diagonal mate mirrored. Returns
    ``(means, covs, weights, iterations, log-likelihood)``.
    """
    means, covs = means.copy(), np.array([_floored(c, 0.0) for c in covs])
    weights = np.asarray(weights, dtype=float).copy()
    anchor_mu, anchor_cov = means.copy(), covs.copy()
    n, k = X.shape[0], means.shape[0]
    tiny = np.finfo(float).tiny
    previous, iteration, lower = -np.inf, 0, -np.inf
    for iteration in range(1, int(max_iter) + 1):
        log_p = _log_densities(X, means, covs) + np.log(np.maximum(weights, tiny))[None, :]
        top = log_p.max(axis=1, keepdims=True)
        top[~np.isfinite(top)] = 0.0
        log_norm = top[:, 0] + np.log(np.exp(log_p - top).sum(axis=1))
        lower = float(np.mean(log_norm))
        resp = np.exp(log_p - log_norm[:, None])
        resp[~np.isfinite(resp)] = 1.0 / k
        nk = np.maximum(resp.sum(axis=0), tiny)
        weights = nk / n
        new_means = (resp.T @ X) / nk[:, None]
        new_means[fix_mu] = anchor_mu[fix_mu]
        means = new_means
        for c in range(k):
            diff = X - means[c]
            cov = _floored((resp[:, c][:, None] * diff).T @ diff / nk[c], reg)
            mask = np.array(fix_cov[c], dtype=bool)
            if mask.any():
                mask[0, 1] = mask[1, 0] = bool(mask[0, 1] or mask[1, 0])
                cov[mask] = anchor_cov[c][mask]
                cov = 0.5 * (cov + cov.T)
            covs[c] = cov
        if lower - previous < tol:
            break
        previous = lower
    return means, covs, weights, iteration, lower


# ---------------------------------------------------------------- transforms
def _positive_definite(cov: np.ndarray) -> np.ndarray:
    try:
        if np.any(np.linalg.eigvalsh(cov) <= 0):
            cov = cov + 1e-9 * np.eye(2)
    except np.linalg.LinAlgError:
        cov = cov + 1e-9 * np.eye(2)
    return cov


def to_fit_space(mu, cov, log_x: bool, log_y: bool) -> Tuple[np.ndarray, np.ndarray]:
    """``(mu, cov)`` from value space to fit space.

    A log axis takes ``log(mu)`` and the covariance through ``J = diag(1/mu)``.
    """
    mu_v = np.asarray(mu, dtype=float).reshape(2)
    cov_v = np.asarray(cov, dtype=float).reshape(2, 2)
    mu_z = mu_v.copy()
    J = np.eye(2)
    if log_x:
        mx = mu_v[0] if mu_v[0] > _EPS else _EPS
        mu_z[0] = np.log(mx)
        J[0, 0] = 1.0 / mx
    if log_y:
        my = mu_v[1] if mu_v[1] > _EPS else _EPS
        mu_z[1] = np.log(my)
        J[1, 1] = 1.0 / my
    return mu_z, _positive_definite(J @ cov_v @ J.T)


def to_value_space(mu, cov, log_x: bool, log_y: bool) -> Tuple[np.ndarray, np.ndarray]:
    """The inverse of :func:`to_fit_space`."""
    mu_z = np.asarray(mu, dtype=float).reshape(2)
    cov_z = np.asarray(cov, dtype=float).reshape(2, 2)
    mu_v = mu_z.copy()
    G = np.eye(2)
    if log_x:
        mu_v[0] = np.exp(mu_z[0])
        G[0, 0] = mu_v[0]
    if log_y:
        mu_v[1] = np.exp(mu_z[1])
        G[1, 1] = mu_v[1]
    return mu_v, _positive_definite(G @ cov_z @ G.T)


# ------------------------------------------------------------------ geometry
def ellipse(mu, cov, sigma: float = 1.0, log_x: bool = False, log_y: bool = False,
            n: int = 200) -> Tuple[np.ndarray, np.ndarray]:
    """The *sigma* contour of a Gaussian, as ``(xs, ys)`` in value space.

    Built in fit space (a log axis's Gaussian is an ellipse in log) and mapped
    back, so on a log axis it is drawn where the fit put it.
    """
    mu_s, cov_s = to_fit_space(mu, cov, log_x, log_y)
    vals, vecs = np.linalg.eigh(cov_s)
    vals = np.maximum(vals, _EPS)
    t = np.linspace(0.0, 2.0 * np.pi, int(n))
    circle = np.vstack([np.cos(t), np.sin(t)])
    pts = vecs @ np.diag(np.sqrt(vals) * float(sigma)) @ circle
    xs = pts[0] + mu_s[0]
    ys = pts[1] + mu_s[1]
    if log_x:
        xs = np.exp(xs)
    if log_y:
        ys = np.exp(ys)
    return xs, ys


def marginal_pdf(centers, mean: float, var: float, log_axis: bool) -> np.ndarray:
    """One Gaussian's 1-D marginal density at *centers*.

    A log axis gets the log-normal whose log-space width is the linearised
    ``var / mean^2``.
    """
    centers = np.asarray(centers, dtype=float)
    var = float(var)
    if not np.isfinite(var) or var <= 0:
        return np.zeros_like(centers)
    if log_axis:
        m = mean if mean > _EPS else _EPS
        s_log = np.sqrt(max(var / (m * m), 1e-12))
        out = np.zeros_like(centers)
        pos = centers > 0.0
        z = (np.log(centers[pos]) - np.log(m)) / s_log
        out[pos] = np.exp(-0.5 * z * z) / (centers[pos] * s_log * np.sqrt(2 * np.pi))
        return out
    s = np.sqrt(var)
    z = (centers - mean) / s
    return np.exp(-0.5 * z * z) / (s * np.sqrt(2 * np.pi))


def _centres(edges) -> np.ndarray:
    edges = np.asarray(edges, dtype=float)
    return 0.5 * (edges[:-1] + edges[1:])


def moments(H, x_edges, y_edges):
    """Weighted mean and covariance of a histogram ``H`` (``(n_y, n_x)``).

    Returns ``((mx, my), cov)``, or ``(None, None)`` for an empty one.
    """
    W = np.asarray(H, dtype=float)
    S = float(np.sum(W))
    if not np.isfinite(S) or S <= 0:
        return None, None
    X, Y = np.meshgrid(_centres(x_edges), _centres(y_edges), indexing="xy")
    mx = float(np.sum(W * X) / S)
    my = float(np.sum(W * Y) / S)
    dx, dy = X - mx, Y - my
    cov = np.array([[np.sum(W * dx * dx), np.sum(W * dx * dy)],
                    [np.sum(W * dx * dy), np.sum(W * dy * dy)]], dtype=float) / S
    if not np.all(np.isfinite(cov)):
        return None, None
    return (mx, my), cov


def local_moments(H, x_edges, y_edges, ix: int, iy: int, window: int = 5):
    """:func:`moments` in the ``(2*window+1)^2`` bins around bin ``(ix, iy)``."""
    H = np.asarray(H, dtype=float)
    ny, nx = H.shape
    x0, x1 = max(0, ix - window), min(nx, ix + window + 1)
    y0, y1 = max(0, iy - window), min(ny, iy + window + 1)
    sub = H[y0:y1, x0:x1]
    if sub.size == 0 or np.sum(sub) <= 0:
        return None, None
    return moments(sub, np.asarray(x_edges)[x0:x1 + 1], np.asarray(y_edges)[y0:y1 + 1])


def seed_component(H, x_edges, y_edges, x: float, y: float, window: int = 10):
    """A Gaussian seeded by a click at value ``(x, y)`` on the map.

    The centre is the clicked bin's centre; the width is the local spread of
    the histogram in a window around it, or a twentieth of the map where the
    window is empty.

    Returns
    -------
    tuple
        ``(mu, cov)``, or ``None`` when ``(x, y)`` is off the map.
    """
    x_edges = np.asarray(x_edges, dtype=float)
    y_edges = np.asarray(y_edges, dtype=float)
    ix = int(np.searchsorted(x_edges, x, side="right") - 1)
    iy = int(np.searchsorted(y_edges, y, side="right") - 1)
    if not (0 <= ix < len(x_edges) - 1 and 0 <= iy < len(y_edges) - 1):
        return None
    window = max(1, min(int(window), 200))
    _mu, cov = local_moments(H, x_edges, y_edges, ix, iy, window)
    if cov is None:
        cov = np.diag([((x_edges[-1] - x_edges[0]) / 20.0) ** 2,
                       ((y_edges[-1] - y_edges[0]) / 20.0) ** 2])
    mu = (float(0.5 * (x_edges[ix] + x_edges[ix + 1])),
          float(0.5 * (y_edges[iy] + y_edges[iy + 1])))
    return mu, cov


# ----------------------------------------------------------------------- fit
def fit_mixture(components: Sequence[Any], x, y, x_range, y_range, log_x: bool = False,
                log_y: bool = False, settings: Optional[Dict[str, Any]] = None) -> List[tuple]:
    """Fit the Gaussians to the points ``(x, y)`` inside the displayed ranges.

    Parameters
    ----------
    components : sequence of GaussianComponent
        The current Gaussians (value space), with their held flags.
    x, y : array_like
        The gated points.
    x_range, y_range : tuple of float
        The map's extent; points outside are not fitted.
    log_x, log_y : bool
        Fit in log space on that axis (positive values only).
    settings : dict, optional
        GMM settings (:data:`GMM_DEFAULTS`).

    Returns
    -------
    list of tuple
        ``(mu, cov, w)`` per component in value space; ``w`` is ``None`` for a
        held weight (the user's share stands).

    Raises
    ------
    GaussianFitError
        No Gaussians, no data, no data in range.
    """
    if not components:
        raise GaussianFitError("No Gaussians",
                               "Add one or more Gaussians (click on the histogram) before fitting.")
    x = np.asarray(x, dtype=float).ravel()
    y = np.asarray(y, dtype=float).ravel()
    if x.size == 0 or y.size == 0 or x.size != y.size:
        raise GaussianFitError("No data", "No data available for fitting.")
    X = np.column_stack([x, y])
    (x0, x1), (y0, y1) = sorted(map(float, x_range)), sorted(map(float, y_range))
    X = X[(X[:, 0] >= x0) & (X[:, 0] <= x1) & (X[:, 1] >= y0) & (X[:, 1] <= y1)]
    if not len(X):
        raise GaussianFitError("No data", "No data within the visible histogram range to fit.")
    X = X[np.all(np.isfinite(X), axis=1)]
    if not len(X):
        raise GaussianFitError("No data", "Selected data contains no finite values for fitting.")
    if log_x or log_y:
        keep = np.ones(len(X), dtype=bool)
        if log_x:
            keep &= X[:, 0] > 0.0
        if log_y:
            keep &= X[:, 1] > 0.0
        if not np.any(keep):
            raise GaussianFitError("No data",
                                   "No positive data available on log-scaled axis for fitting.")
        X = X[keep].copy()
        if log_x:
            X[:, 0] = np.log(X[:, 0])
        if log_y:
            X[:, 1] = np.log(X[:, 1])

    k = len(components)
    means = np.zeros((k, 2))
    covs = np.zeros((k, 2, 2))
    weights = np.zeros(k)
    fix_mu = np.zeros((k, 2), dtype=bool)
    fix_cov = np.zeros((k, 2, 2), dtype=bool)
    for i, c in enumerate(components):
        means[i], covs[i] = to_fit_space(c.mu, c.cov, log_x, log_y)
        weights[i] = max(0.0, float(c.w))
        fix_mu[i] = c.fix_mu
        fix_cov[i] = c.fix_cov
    total = float(np.sum(weights))
    weights = weights / total if np.isfinite(total) and total > 0 else np.full(k, 1.0 / k)

    cfg = dict(GMM_DEFAULTS)
    cfg.update(settings or {})
    em = GaussianMixtureFixedEM(means, covs, weights, reg_covar=float(cfg["reg_covar"]),
                                max_iter=int(cfg["max_iter"]), tol=float(cfg["tol"]),
                                verbose=int(cfg["verbose"]),
                                weight_floor=float(cfg["weight_floor"]))
    em.fit(X, fix_mu, fix_cov, means, covs)
    out = []
    for i, c in enumerate(components):
        mu_v, cov_v = to_value_space(em.means_[i], em.covs_[i], log_x, log_y)
        out.append((mu_v, cov_v, None if c.fix_w else float(em.weights_[i])))
    return out


# ------------------------------------------------------------------ marginals
def _normalised_weights(rows) -> List[float]:
    w = [max(0.0, float(r[2])) for r in rows]
    total = float(np.sum(w)) if w else 0.0
    if np.isfinite(total) and total > 0:
        return [v / total for v in w]
    return [1.0 / len(rows)] * len(rows) if rows else []


def component_marginals(rows, x_edges, x_counts, y_edges, y_counts, norm_x: bool = False,
                        norm_y: bool = False, log_x: bool = False, log_y: bool = False):
    """Each Gaussian's curve on the x and y marginals, scaled like the histogram.

    Parameters
    ----------
    rows : sequence of (mu, cov, w)
    x_edges, x_counts, y_edges, y_counts : array_like
        The marginal histograms the curves are drawn over.
    norm_x, norm_y : bool
        The marginal is a density (its area is one), not counts.

    Returns
    -------
    list of tuple
        ``(x_centers, gx, y_centers, gy)`` per Gaussian; a Gaussian with a
        degenerate width gets ``None``.
    """
    xc, yc = _centres(x_edges), _centres(y_edges)
    x_bw, y_bw = np.diff(np.asarray(x_edges, float)), np.diff(np.asarray(y_edges, float))
    nx_total = 1.0 if norm_x else float(np.nansum(x_counts)) if len(x_counts) else 1.0
    ny_total = 1.0 if norm_y else float(np.nansum(y_counts)) if len(y_counts) else 1.0
    out = []
    for (mu, cov, _w), wn in zip(rows, _normalised_weights(rows)):
        varx, vary = float(cov[0][0]), float(cov[1][1])
        if not (np.isfinite(varx) and varx > 0 and np.isfinite(vary) and vary > 0):
            out.append(None)
            continue
        gx = wn * marginal_pdf(xc, float(mu[0]), varx, log_x)
        gy = wn * marginal_pdf(yc, float(mu[1]), vary, log_y)
        if not norm_x:
            gx = gx * x_bw * nx_total
        if not norm_y:
            gy = gy * y_bw * ny_total
        out.append((xc, gx, yc, gy))
    return out


def model_marginals(rows, x_edges, y_edges, total_counts: float, log_x: bool = False,
                    log_y: bool = False):
    """The whole mixture's x and y marginals in counts: ``(xc, yc, mx, my)``."""
    xc, yc = _centres(x_edges), _centres(y_edges)
    dx = float(np.mean(np.diff(xc))) if len(xc) > 1 else 1.0
    dy = float(np.mean(np.diff(yc))) if len(yc) > 1 else 1.0
    mx, my = np.zeros_like(xc), np.zeros_like(yc)
    for (mu, cov, _w), wn in zip(rows, _normalised_weights(rows)):
        varx, vary = float(cov[0][0]), float(cov[1][1])
        if not (np.isfinite(varx) and varx > 0 and np.isfinite(vary) and vary > 0):
            continue
        mx += wn * marginal_pdf(xc, float(mu[0]), varx, log_x)
        my += wn * marginal_pdf(yc, float(mu[1]), vary, log_y)
    return xc, yc, mx * dx * total_counts, my * dy * total_counts


def model_grid_2d(rows, x_edges, y_edges, total_counts: float, log_x: bool = False,
                  log_y: bool = False):
    """The mixture in counts per bin of the map: ``(xc, yc, M)``, ``M`` ``(n_x, n_y)``.

    The density is evaluated at the bin centres in fit space, with the
    Jacobian of the log axes, and multiplied by the bin areas.
    """
    x_edges = np.asarray(x_edges, dtype=float)
    y_edges = np.asarray(y_edges, dtype=float)
    xc, yc = _centres(x_edges), _centres(y_edges)
    if xc.size == 0 or yc.size == 0 or not rows:
        return xc, yc, None
    Xc, Yc = np.meshgrid(xc, yc, indexing="ij")
    valid = np.ones_like(Xc, dtype=bool)
    if log_x:
        valid &= Xc > 0.0
    if log_y:
        valid &= Yc > 0.0
    Sx = np.log(Xc, where=Xc > 0.0, out=np.zeros_like(Xc)) if log_x else Xc
    Sy = np.log(Yc, where=Yc > 0.0, out=np.zeros_like(Yc)) if log_y else Yc
    jac = np.ones_like(Xc)
    if log_x:
        jac = jac / np.maximum(Xc, 1e-300)
    if log_y:
        jac = jac / np.maximum(Yc, 1e-300)
    density = np.zeros_like(Xc)
    for (mu, cov, _w), wn in zip(rows, _normalised_weights(rows)):
        mu_s, cov_s = to_fit_space(mu, cov, log_x, log_y)
        det = float(np.linalg.det(cov_s))
        if not np.isfinite(det) or det <= 0:
            continue
        inv = np.linalg.inv(cov_s)
        dxs, dys = Sx - mu_s[0], Sy - mu_s[1]
        Q = inv[0, 0] * dxs * dxs + 2.0 * inv[0, 1] * dxs * dys + inv[1, 1] * dys * dys
        comp = np.exp(-0.5 * Q) / (2.0 * np.pi * np.sqrt(det)) * jac
        comp[~valid] = 0.0
        density += wn * comp
    return xc, yc, density * np.outer(np.diff(x_edges), np.diff(y_edges)) * float(total_counts)


# --------------------------------------------------------------------- files
RECORD_COLUMNS = ["x", "y", "sd_x", "sd_y", "rho", "w",
                  "fix_x", "fix_y", "fix_sd_x", "fix_sd_y", "fix_rho"]


def _header(handle, kind: str, version: int, axes_info: dict, extra: Sequence[str] = ()) -> None:
    xinfo, yinfo = axes_info.get("x", {}), axes_info.get("y", {})
    handle.write(f"# ndxplorer.{kind} version={version}\n")
    handle.write(f"# created={datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    handle.write(f"# x_axis index={xinfo.get('index')} name={xinfo.get('name')} "
                 f"scale={xinfo.get('scale')}\n")
    handle.write(f"# y_axis index={yinfo.get('index')} name={yinfo.get('name')} "
                 f"scale={yinfo.get('scale')}\n")
    for line in extra:
        handle.write(f"# {line}\n")


def _grid_rows(writer, xc, yc, grid) -> None:
    """A grid with x down the rows and y across the columns."""
    writer.writerow(["x\\y"] + [float(v) for v in yc])
    for i, xv in enumerate(xc):
        writer.writerow([float(xv)] + [float(v) for v in grid[i, :]])


def save_gaussians(path: str, records: Sequence[dict], rows: Sequence[tuple], axes_info: dict,
                   H=None, x_edges=None, y_edges=None, log_x: bool = False,
                   log_y: bool = False) -> List[str]:
    """Write a mixture: the Gaussians and the histogram and model they explain.

    ``<base>.json`` (Gaussians, axes and marginals), ``<base>_gaussians.csv``,
    ``<base>_hist2d.csv``, ``<base>_model2d.csv`` (mixture and each
    component), ``<base>_marginal_x.csv`` and ``<base>_marginal_y.csv``, where
    *base* is *path* without a ``.json``/``.csv`` extension.

    Parameters
    ----------
    records : sequence of dict
        One flat record per Gaussian (``GaussianMixture.records()``).
    rows : sequence of (mu, cov, w)
        The same Gaussians, for the model.
    axes_info : dict
        ``{"x": {"index", "name", "scale"}, "y": {...}, "fit_in_log": bool}``.
    H, x_edges, y_edges : array_like, optional
        The map (``(n_y, n_x)``) the model is compared with.

    Returns
    -------
    list of str
        The files written.

    Raises
    ------
    OSError
        A file could not be written.
    """
    root, ext = os.path.splitext(path)
    base = root if ext.lower() in (".json", ".csv") else path
    paths = {key: base + suffix for key, suffix in (
        ("json", ".json"), ("gaussians", "_gaussians.csv"), ("hist", "_hist2d.csv"),
        ("model", "_model2d.csv"), ("mx", "_marginal_x.csv"), ("my", "_marginal_y.csv"))}
    have_map = H is not None and np.size(H) and x_edges is not None and y_edges is not None
    marginals: dict = {}
    Hx = None
    if have_map:
        Hx = np.asarray(H, dtype=float).T                       # (n_x, n_y)
        total = float(np.sum(Hx)) if np.isfinite(np.sum(Hx)) else 0.0
        xc, yc = _centres(x_edges), _centres(y_edges)
        _, _, model_x, model_y = model_marginals(rows, x_edges, y_edges, total, log_x, log_y)
        dxw = float(np.mean(np.diff(xc))) if len(xc) > 1 else 1.0
        dyw = float(np.mean(np.diff(yc))) if len(yc) > 1 else 1.0
        comps_x, comps_y = [], []
        for (mu, cov, _w), wn in zip(rows, _normalised_weights(rows)):
            comps_x.append((wn * marginal_pdf(xc, float(mu[0]), float(cov[0][0]), log_x)
                            * dxw * total).tolist())
            comps_y.append((wn * marginal_pdf(yc, float(mu[1]), float(cov[1][1]), log_y)
                            * dyw * total).tolist())
        marginals = {
            "x": {"centers": xc.tolist(), "data": Hx.sum(axis=1).tolist(),
                  "model": model_x.tolist(), "components": comps_x},
            "y": {"centers": yc.tolist(), "data": Hx.sum(axis=0).tolist(),
                  "model": model_y.tolist(), "components": comps_y},
        }
    payload = {
        "type": "ndxplorer.gaussians", "version": 4,
        "created": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "columns": RECORD_COLUMNS, "axes": axes_info, "rows": list(records),
        "marginals": marginals,
    }
    with open(paths["json"], "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
    with open(paths["gaussians"], "w", newline="", encoding="utf-8") as handle:
        _header(handle, "gaussians", 4, axes_info,
                [f"fit_in_log={axes_info.get('fit_in_log', False)}"])
        writer = csv.DictWriter(handle, fieldnames=RECORD_COLUMNS)
        writer.writeheader()
        for record in records:
            writer.writerow({k: record.get(k) for k in RECORD_COLUMNS})
    with open(paths["hist"], "w", newline="", encoding="utf-8") as handle:
        _header(handle, "hist2d", 1, axes_info,
                [f"shape={list(Hx.shape) if Hx is not None else None}"])
        if have_map:
            _grid_rows(csv.writer(handle), _centres(x_edges), _centres(y_edges), Hx)
        else:
            handle.write("# No histogram available\n")
    with open(paths["model"], "w", newline="", encoding="utf-8") as handle:
        _header(handle, "model2d", 2, axes_info)
        if have_map:
            writer = csv.writer(handle)
            total = float(np.sum(Hx))
            xc, yc, M = model_grid_2d(rows, x_edges, y_edges, total, log_x, log_y)
            if M is not None:
                handle.write("# section=mixture\n")
                _grid_rows(writer, xc, yc, M)
            else:
                handle.write("# No model available\n")
            for idx, row in enumerate(rows):
                xc1, yc1, M1 = model_grid_2d([row], x_edges, y_edges, total, log_x, log_y)
                handle.write(f"# section=component index={idx}\n")
                if M1 is not None:
                    _grid_rows(writer, xc1, yc1, M1)
                else:
                    handle.write("# component empty\n")
        else:
            handle.write("# No histogram available (cannot compute model grid)\n")
    for key, axis in (("mx", "x"), ("my", "y")):
        with open(paths[key], "w", newline="", encoding="utf-8") as handle:
            _header(handle, f"marginal_{axis}", 1, axes_info)
            writer = csv.writer(handle)
            part = marginals.get(axis) or {}
            comps = part.get("components") or []
            writer.writerow(["center", "data", "model"] + [f"comp_{i}" for i in range(len(comps))])
            centers, data, model = (part.get("centers") or [], part.get("data") or [],
                                    part.get("model") or [])
            for i in range(min(len(centers), len(data), len(model))):
                writer.writerow([float(centers[i]), float(data[i]), float(model[i])]
                                + [float(c[i]) if i < len(c) else 0.0 for c in comps])
    return list(paths.values())


def _flag(value) -> bool:
    if isinstance(value, str):
        return value.strip().lower() in ("1", "true", "yes", "y")
    return bool(value)


def _row_from_record(r: dict) -> Optional[tuple]:
    """``(mu, cov, w, fix_x, fix_y, fix_sd_x, fix_rho, fix_sd_y)`` of a record."""
    try:
        x, y = float(r["x"]), float(r["y"])
        if any(r.get(k) not in (None, "") for k in ("sd_x", "sd_y", "rho")):
            sd_x = float(r.get("sd_x") or 0.0)
            sd_y = float(r.get("sd_y") or 0.0)
            rho = float(np.clip(float(r.get("rho") or 0.0), -1.0, 1.0))
            cxx, cyy, cxy = sd_x * sd_x, sd_y * sd_y, rho * sd_x * sd_y
            flags = (r.get("fix_x"), r.get("fix_y"), r.get("fix_sd_x"), r.get("fix_rho"),
                     r.get("fix_sd_y"))
        else:
            cxx, cxy, cyy = float(r["cov_xx"]), float(r["cov_xy"]), float(r["cov_yy"])
            flags = (r.get("fix_x"), r.get("fix_y"), r.get("fix_cxx"), r.get("fix_cxy"),
                     r.get("fix_cyy"))
        w = float(r.get("w", 1.0) if r.get("w") not in (None, "") else 1.0)
    except (KeyError, TypeError, ValueError):
        return None
    return (np.array([x, y]), np.array([[cxx, cxy], [cxy, cyy]]), w) + \
        tuple(_flag(f) for f in flags)


def load_gaussians(path: str) -> Tuple[List[tuple], Optional[dict]]:
    """Read Gaussians saved by :func:`save_gaussians` (``.json`` or ``.csv``).

    Old files with ``cov_xx``/``cov_xy``/``cov_yy`` load too.

    Returns
    -------
    tuple
        ``(rows, axes)``: rows are ``(mu, cov, w, fix_x, fix_y, fix_sd_x,
        fix_rho, fix_sd_y)``; *axes* the file's axis record (JSON only).
    """
    ext = os.path.splitext(path)[1].lower()
    if ext == ".csv":
        return _load_csv(path), None
    try:
        return _load_json(path)
    except (ValueError, UnicodeDecodeError):
        if ext == ".json":
            raise
        return _load_csv(path), None


def _load_json(path: str):
    with open(path, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    records = data.get("rows", []) if isinstance(data, dict) else data
    rows = [row for row in (_row_from_record(r) for r in records) if row is not None]
    return rows, (data.get("axes") if isinstance(data, dict) else None)


def _load_csv(path: str) -> List[tuple]:
    with open(path, "r", encoding="utf-8") as handle:
        lines = [line for line in handle if not line.startswith("#")]
    rows = [_row_from_record(r) for r in csv.DictReader(lines)]
    return [row for row in rows if row is not None]


def axis_mismatch(file_axes: Optional[dict], current: dict) -> Optional[str]:
    """The "Axis Mismatch" message when a loaded file's axes are not the map's."""
    if not file_axes:
        return None

    def describe(info: dict, axis: str) -> str:
        part = info.get(axis, {}) or {}
        return f"{part.get('name')} ({part.get('scale')})"

    old = describe(file_axes, "x"), describe(file_axes, "y")
    now = describe(current, "x"), describe(current, "y")
    if old == now:
        return None
    return (f"File axes:\nX: {old[0]}\nY: {old[1]}\nCurrent axes:\nX: {now[0]}\nY: {now[1]}"
            "\n\nGaussians were loaded regardless.")
