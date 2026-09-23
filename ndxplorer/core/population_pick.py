"""Fit a gate to the population under a click on the 2-D map.

"Fit gate to the population here" takes a click on the map as a *seed*. It
finds the cloud of points the click sits in, fits a 2-D Gaussian to that cloud,
and returns it as an elliptical gate. The result is a
:class:`~ndxplorer.core.data_source.Gaussian2DSelection`, one of the Selection
table's four gate kinds.

Two things the Qt window's version got wrong, and this one does not:

* **The click is in data units.** In the Qt window the map's view box works in
  bin indices, so ``(18.6, 8.7)`` was compared against a Tau range of 0–6 and
  every pick was refused. Here the caller passes the data coordinates the plot
  reports.
* **The population is found in display units, not raw units.** Its capture
  radius, "a twentieth of the shorter axis", meant 0.05 ns on a 0–6 ns
  lifetime axis next to a 0–1 FRET axis. That sliced a sliver out of the
  population, and the fitted gate kept 105 of 3000 bursts. Here both axes are
  first scaled to the plotted range (the log of it on a log axis), so the
  result does not depend on the units.

How the population is found. The points are binned on a grid over the plotted
range, and the grid is smoothed. From the clicked bin the search climbs to the
local maximum: the population's mode, wherever on its shoulder the click
landed. The population is then the bins reachable from the mode that are still
at least ``level`` of the peak height, going only downhill. A neighbouring
population, even a much denser one, lies across a valley, and the downhill
rule stops at the valley. A distance cut cannot do that: a radius that holds a
diffuse cloud also holds the dense cloud next to it.

The mean and covariance of the points in those bins are the gate. A Gaussian
cut at ``level`` of its peak is cut at Mahalanobis radius
``c = sqrt(-2 ln level)``. The kept points' covariance is the full one times
``1 - (c²/2)·e^(-c²/2) / (1 - e^(-c²/2))``, and this is divided back out, so
the ellipse is the population's own width and not the cut's.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional, Tuple

import numpy as np

__all__ = ["PopulationFit", "fit_population", "truncation_factor"]


@dataclass
class PopulationFit:
    """The outcome of a pick.

    Attributes
    ----------
    success : bool
    reason : str
        Why the pick was refused; empty on success.
    mu : ndarray, shape (2,)
        Centre, in gate space: the data units, or their natural log on a log
        axis (the space :class:`Gaussian2DSelection` measures in).
    cov : ndarray, shape (2, 2)
        Covariance in the same space.
    n_points : int
        Points the final estimate was made from.
    log_x, log_y : bool
        Whether that axis is fitted (and gated) in log space.
    """

    success: bool = False
    reason: str = ""
    mu: np.ndarray = field(default_factory=lambda: np.zeros(2))
    cov: np.ndarray = field(default_factory=lambda: np.zeros((2, 2)))
    n_points: int = 0
    log_x: bool = False
    log_y: bool = False


def truncation_factor(c: float) -> float:
    """How much a 2-D Gaussian's covariance shrinks when cut at Mahalanobis radius *c*."""
    c2 = float(c) ** 2
    tail = math.exp(-c2 / 2.0)
    if tail >= 1.0:
        return 1.0
    return 1.0 - (c2 / 2.0) * tail / (1.0 - tail)


def _to_space(values: np.ndarray, log: bool) -> np.ndarray:
    values = np.asarray(values, dtype=np.float64)
    if not log:
        return values
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.where(values > 0.0, np.log(values), np.nan)


def fit_population(
    x: np.ndarray,
    y: np.ndarray,
    seed: Tuple[float, float],
    x_range: Tuple[float, float],
    y_range: Tuple[float, float],
    *,
    log_x: bool = False,
    log_y: bool = False,
    grid: int = 48,
    level: float = 0.25,
    slack: float = 0.05,
    min_points: int = 10,
) -> PopulationFit:
    """Fit a 2-D Gaussian to the cloud of points around *seed*.

    Parameters
    ----------
    x, y : array-like
        The points on the map, as shown (every other gate already applied).
    seed : (float, float)
        The click, in data units.
    x_range, y_range : (float, float)
        The plotted ranges; the population is searched for on a grid over them.
    log_x, log_y : bool
        Logarithmic axes. The fit, and the gate, work in the log.
    grid : int
        Bins per axis of the grid the population is found on.
    level : float
        The population reaches down to this fraction of its peak density.
    slack : float
        How much a bin may rise above its uphill neighbour and still count as
        downhill (counting noise).
    min_points : int
        Fewer points than this refuses the pick.

    Returns
    -------
    PopulationFit
    """
    fit = PopulationFit(log_x=bool(log_x), log_y=bool(log_y))
    sx, sy = float(seed[0]), float(seed[1])
    x_lo, x_hi = sorted(float(v) for v in x_range)
    y_lo, y_hi = sorted(float(v) for v in y_range)
    if not (x_lo <= sx <= x_hi and y_lo <= sy <= y_hi):
        fit.reason = f"({sx:.4g}, {sy:.4g}) is outside the plotted range"
        return fit

    # Scale both axes to the plotted range, in the space the gate measures in.
    lo = np.array([_to_space(x_lo, log_x), _to_space(y_lo, log_y)], dtype=float)
    hi = np.array([_to_space(x_hi, log_x), _to_space(y_hi, log_y)], dtype=float)
    span = hi - lo
    if not (np.isfinite(span).all() and (span > 0).all()):
        fit.reason = "the plotted range is empty (or not positive on a log axis)"
        return fit
    points = np.stack([_to_space(x, log_x), _to_space(y, log_y)], axis=1)
    points = (points[np.isfinite(points).all(axis=1)] - lo) / span
    centre = (np.array([_to_space(sx, log_x), _to_space(sy, log_y)], dtype=float) - lo) / span
    if not np.isfinite(centre).all():
        fit.reason = "the click is not on a log axis's positive range"
        return fit
    if len(points) == 0:
        fit.reason = "no points on this plane"
        return fit

    # Bin the points over the plotted range, and smooth: a noisy grid has a
    # local maximum in every other bin.
    bins = int(grid)
    inside_plot = ((points >= 0.0) & (points <= 1.0)).all(axis=1)
    cells = np.minimum((points[inside_plot] * bins).astype(np.int64), bins - 1)
    counts = np.zeros((bins, bins), dtype=np.float64)
    np.add.at(counts, (cells[:, 0], cells[:, 1]), 1.0)
    padded = np.pad(counts, 1)
    smooth = sum(padded[1 + dx:bins + 1 + dx, 1 + dy:bins + 1 + dy] * w
                 for dx, dy, w in ((-1, -1, 1), (-1, 0, 2), (-1, 1, 1), (0, -1, 2), (0, 0, 4),
                                   (0, 1, 2), (1, -1, 1), (1, 0, 2), (1, 1, 1))) / 16.0
    neighbours = [(dx, dy) for dx in (-1, 0, 1) for dy in (-1, 0, 1) if dx or dy]

    # Climb from the clicked bin to the population's mode.
    here = tuple(int(v) for v in np.minimum((centre * bins).astype(int), bins - 1))
    for _ in range(4 * bins):
        best = max(((here[0] + dx, here[1] + dy) for dx, dy in neighbours
                    if 0 <= here[0] + dx < bins and 0 <= here[1] + dy < bins),
                   key=lambda b: smooth[b])
        if smooth[best] <= smooth[here]:
            break
        here = best
    peak = smooth[here]
    if peak <= 0.0:
        fit.reason = "no points near the click; click where the population is"
        return fit

    # The population: downhill from the mode, down to `level` of the peak.
    region = np.zeros((bins, bins), dtype=bool)
    region[here] = True
    todo = [here]
    floor = level * peak
    while todo:
        cx, cy = todo.pop()
        for dx, dy in neighbours:
            nx, ny = cx + dx, cy + dy
            if not (0 <= nx < bins and 0 <= ny < bins) or region[nx, ny]:
                continue
            value = smooth[nx, ny]
            if value >= floor and value <= smooth[cx, cy] * (1.0 + slack):
                region[nx, ny] = True
                todo.append((nx, ny))

    members = points[inside_plot][region[cells[:, 0], cells[:, 1]]]
    n = int(len(members))
    if n < min_points:
        fit.n_points = n
        fit.reason = f"only {n} point(s) in the population at the click"
        return fit
    centre = members.mean(axis=0)
    cut = math.sqrt(-2.0 * math.log(level))
    cov = np.cov(members.T) / truncation_factor(cut)
    if not np.isfinite(cov).all() or np.linalg.det(cov) <= 0:
        fit.n_points = n
        fit.reason = "the points are collinear: no ellipse describes them"
        return fit

    scale = np.diag(span)
    fit.mu = centre * span + lo
    fit.cov = scale @ cov @ scale
    fit.n_points = n
    fit.success = True
    return fit
