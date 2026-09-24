"""Fit an overlay curve ``y = f(x; params)`` to the data nDXplorer is showing.

An overlay curve is a parameterised function of the current axes. This module
lets that curve be **fitted**, against either of the two things on screen:

``"2d"``
    the displayed two-dimensional distribution — for every x column of the
    histogram, the count-weighted mean y and its standard error. This is what
    fits a FRET line, a static line or any ``y(x)`` relation to the cloud of
    bursts it is drawn over.
``"x"`` / ``"y"``
    a one-dimensional marginal histogram (bin centres → counts), for curves that
    are a *distribution* of one axis, such as a Gaussian on E.

Either way the equation is evaluated exactly as the overlay draws it and
optimised by ``scipy.optimize.least_squares``, so the same safe formula that
draws the overlay also drives the fit.

The fit's parameters are seeded from the curve's own
:class:`~ndxplorer.core.parameters.Parameter` objects (value, bounds and fix/free straight
from the overlay's parameter table), the fit optimises every **free** one, and
the result is written back into the curve. Parameters that name an nDXplorer
constant, and parameters that are *crosslinked* to another parameter, arrive
fixed — a linked value belongs to its master, so fitting it would be meaningless.

nDXplorer's **constants** can join the fit as :class:`DataParameters`. They are
not curve parameters: they are the inputs of the equations that build the
plotted axes, so freeing one moves the burst population rather than the line —
which is how ``gamma`` and ``beta`` are determined in the first place. A fit
carrying them re-derives the data at every step, on the bin edges and columns it
started with.

:class:`CurveFit` is the persistent handle the GUI dialog drives (build once,
edit fix/free, ``run`` repeatedly). :func:`fit_equation_to_marginal` and
:func:`fit_equation_to_histogram` are the one-shot conveniences used by the
no-dialog path and the tests.

Qt-free, chisurf-free and headless-testable (numpy and scipy).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np

from ..core.parameters import is_held


class CurveFitError(RuntimeError):
    """Raised when a curve-fit model cannot be built (bad equation, no params)."""


@dataclass
class CurveFitResult:
    """Outcome of a curve fit.

    Attributes
    ----------
    ok
        True when the fit ran and produced parameters.
    params
        Fitted ``{name: value}`` for every free/fixed model parameter.
    chi2r
        Reduced chi-square of the fit (``nan`` on failure).
    y_fit
        The fitted model evaluated at the input x (for redraw/preview).
    message
        A short reason when ``ok`` is False.
    data_params
        Fitted ``{name: value}`` for the *data* parameters (nDXplorer constants)
        that took part — empty when the fit only moved the curve.
    """

    ok: bool
    params: Dict[str, float] = field(default_factory=dict)
    chi2r: float = float("nan")
    y_fit: Optional[np.ndarray] = None
    message: Optional[str] = None
    data_params: Dict[str, float] = field(default_factory=dict)

    def __bool__(self) -> bool:  # noqa: D105
        return self.ok


def bin_centers(edges: Sequence[float]) -> np.ndarray:
    """Return bin centres from an array of ``n+1`` bin edges."""
    e = np.asarray(edges, dtype=float)
    return 0.5 * (e[:-1] + e[1:])


def _oriented(
    counts: Sequence[Sequence[float]],
    x_edges: Sequence[float],
    y_edges: Sequence[float],
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Return the histogram x-first ``(nx, ny)`` with its two edge arrays."""
    h = np.asarray(counts, dtype=float)
    xe = np.asarray(x_edges, dtype=float)
    ye = np.asarray(y_edges, dtype=float)
    if h.ndim != 2 or h.size == 0:
        raise CurveFitError("no 2-D histogram to fit")
    if h.shape[0] == ye.size - 1 and h.shape[1] == xe.size - 1:
        # Producers hand back (ny, nx) — ndX's own ``Histogram2D.H`` does — so
        # orient it x-first. Note this branch also matches a square histogram
        # that is *already* x-first, which is why every caller must pass the
        # (ny, nx) orientation ``plot_histogram`` returns.
        h = h.T
    if h.shape[0] != xe.size - 1 or h.shape[1] != ye.size - 1:
        raise CurveFitError("histogram does not match its bin edges")
    return h, xe, ye


def populated_columns(
    counts: Sequence[Sequence[float]],
    x_edges: Sequence[float],
    y_edges: Sequence[float],
    *,
    min_counts: float = 3.0,
) -> np.ndarray:
    """Boolean mask of the x columns holding at least ``min_counts`` events."""
    h, _, _ = _oriented(counts, x_edges, y_edges)
    return h.sum(axis=1) >= float(min_counts)


def ridge_from_histogram(
    counts: Sequence[Sequence[float]],
    x_edges: Sequence[float],
    y_edges: Sequence[float],
    *,
    min_counts: float = 3.0,
    keep: Optional[Sequence[bool]] = None,
    reduction: str = "population",
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Reduce a displayed 2-D histogram to the ``y(x)`` points a curve fits to.

    One point per x column: with ``reduction='population'`` (the default) the
    centre of the column's densest population, and with ``'mean'`` its
    count-weighted average. See :func:`ridge_from_values`, which this defers to
    — a histogram is just its bin centres carrying the counts as weights — for
    why the two differ and when it matters.

    Parameters
    ----------
    counts : array_like, shape (nx, ny)
        The displayed 2-D histogram, x along the first axis (as returned by
        ``plot_histogram(ndx, "2d")``).
    x_edges, y_edges : array_like
        Bin edges of the two axes (``nx + 1`` and ``ny + 1`` long).
    min_counts : float, optional
        Minimum number of events for a column to be used.
    keep : array_like of bool, optional
        Use exactly these columns instead of re-deciding from ``min_counts``.
        A fit that moves the *data* (see :class:`DataParameters`) re-reduces the
        histogram at every step and must return the same number of points every
        time, or the optimiser's residual vector changes length underneath it.
        A forced column that has emptied comes back as ``nan``, which the
        residual drops.
    reduction : {'population', 'mean'}, optional
        Which point of a column the curve is fitted through.

    Returns
    -------
    x, y, ey : ndarray
        Column centres, the reduced y, and its standard error (floored at half
        a y bin: a column can never be located better than the binning it is
        displayed with).

    Raises
    ------
    CurveFitError
        If the histogram is empty, does not match its edges, or too few columns
        survive to fit anything.
    """
    h, xe, ye = _oriented(counts, x_edges, y_edges)
    yc = bin_centers(ye)
    n_cols = h.shape[0]

    # A histogram *is* a weighted set of points: one per bin, at its centre,
    # weighing what it counted. Reducing it is then the same operation as
    # reducing the values, and there is one implementation of that.
    x_of_bin = np.repeat(0.5 * (xe[:-1] + xe[1:]), yc.size)
    y_of_bin = np.tile(yc, n_cols)
    weights = h.ravel()
    return ridge_from_values(
        x_of_bin, y_of_bin, xe,
        weights=weights, y_edges=ye, keep=keep, min_counts=min_counts,
        reduction=reduction,
    )


#: How a column of the distribution is reduced to the one point a curve is
#: fitted through.
REDUCTIONS = ("population", "mean")


def column_counts(
    x: Sequence[float],
    x_edges: Sequence[float],
    weights: Optional[Sequence[float]] = None,
) -> np.ndarray:
    """Number of points (or their weight) in each x column."""
    edges = np.asarray(x_edges, dtype=float)
    n_cols = edges.size - 1
    column = np.searchsorted(edges, np.asarray(x, dtype=float), side="right") - 1
    inside = (column >= 0) & (column < n_cols)
    w = None if weights is None else np.asarray(weights, dtype=float)[inside]
    return np.bincount(column[inside], weights=w, minlength=n_cols)


def ridge_from_values(
    x: Sequence[float],
    y: Sequence[float],
    x_edges: Sequence[float],
    *,
    weights: Optional[Sequence[float]] = None,
    y_edges: Optional[Sequence[float]] = None,
    keep: Optional[Sequence[bool]] = None,
    min_counts: float = 3.0,
    reduction: str = "population",
    bandwidth: Optional[float] = None,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Reduce each x column of the distribution to the point a curve fits through.

    ``reduction='population'`` (the default) follows the **densest population**
    in the column: the local mode, found by mean-shifting from the column's
    kernel-density peak. ``reduction='mean'`` takes the plain weighted average
    of the column instead.

    The difference is the whole point. A burst plot is a *mixture* — a FRET
    population, a donor-only population at E≈0, and a scatter of singles — and
    the average of a mixture lies where nothing is. On real data the column mean
    ran ~0.1 in E below the FRET population's ridge, so a static FRET line
    fitted through it missed the population it was supposed to describe. The
    local mode ignores whatever is not in the peak the column is made of.

    Both are taken over the **unbinned** values, which is what keeps the
    objective smooth while a fitted constant slides the population (a binned
    mean moves in steps, and its derivative reads zero).

    Parameters
    ----------
    x, y : array_like
        The plotted values, one entry per point.
    x_edges : array_like
        Column edges (the displayed x bins).
    weights : array_like, optional
        Per-point weights.
    y_edges : array_like, optional
        The displayed y bins. Supplies the error floor (half a bin) and the
        default kernel bandwidth.
    keep : array_like of bool, optional
        Use exactly these columns, as in :func:`ridge_from_histogram` — a fit
        that moves the data must return the same number of points every step.
    min_counts : float, optional
        Minimum weight in a column for it to be used (when ``keep`` is None).
    reduction : {'population', 'mean'}, optional
        Which point the column is reduced to.
    bandwidth : float, optional
        Kernel width for the population mode. Defaults to three displayed y
        bins, or a Silverman estimate when there are no ``y_edges``.

    Returns
    -------
    x, y, ey : ndarray
        Column centres, the reduced y, and its standard error (floored at half
        a displayed y bin — a population cannot be located better than the
        binning it is shown with).
    """
    edges = np.asarray(x_edges, dtype=float)
    n_cols = edges.size - 1
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)

    column = np.searchsorted(edges, x, side="right") - 1
    inside = (column >= 0) & (column < n_cols) & np.isfinite(y)
    column, values = column[inside], y[inside]
    w = (
        np.ones(values.shape)
        if weights is None
        else np.asarray(weights, dtype=float)[inside]
    )

    n = np.bincount(column, weights=w, minlength=n_cols)
    if keep is None:
        mask = n >= float(min_counts)
        if int(mask.sum()) < 3:
            raise CurveFitError("too few populated columns to fit (need 3)")
    else:
        mask = np.asarray(keep, dtype=bool)
        if mask.size != n_cols:
            raise CurveFitError("column mask does not match the bin edges")

    floor = 1.0
    ye = None if y_edges is None else np.asarray(y_edges, dtype=float)
    if ye is not None and ye.size > 2:
        floor = 0.5 * float(np.median(np.diff(ye)))

    if str(reduction) == "mean":
        centre, sem = _column_mean(column, values, w, n, n_cols)
    else:
        centre, sem = _column_mode(
            column, values, w, n, n_cols, ye, bandwidth
        )

    centers = 0.5 * (edges[:-1] + edges[1:])
    return centers[mask], centre[mask], np.maximum(sem[mask], floor)


def _column_mean(column, values, w, n, n_cols):
    """Weighted mean of each column and the standard error of that mean."""
    total = np.bincount(column, weights=w * values, minlength=n_cols)
    square = np.bincount(column, weights=w * values * values, minlength=n_cols)
    safe = np.where(n > 0, n, np.nan)
    mean = total / safe
    var = np.maximum(square / safe - mean ** 2, 0.0)
    return mean, np.sqrt(var / safe)


def _column_mode(column, values, w, n, n_cols, y_edges, bandwidth, iterations: int = 8):
    """Local mode of each column: the centre of its densest population.

    Seeded at the column's smoothed density peak and refined by mean shift, so
    the estimate is a smooth function of the values (a fitted constant slides
    the population continuously) while a second population in the same column —
    donor-only bursts at E≈0, say — is left where it is instead of being
    averaged in.
    """
    if values.size == 0:
        empty = np.full(n_cols, np.nan)
        return empty, empty

    grid = (
        np.asarray(y_edges, dtype=float)
        if y_edges is not None and np.size(y_edges) > 2
        else np.linspace(float(values.min()), float(values.max()), 61)
    )
    grid_centres = 0.5 * (grid[:-1] + grid[1:])
    n_bins = grid_centres.size
    step = float(np.median(np.diff(grid))) if n_bins > 1 else 1.0
    if bandwidth is None:
        spread = float(np.std(values)) or step
        bandwidth = max(3.0 * step, 0.0) or 1.06 * spread * values.size ** -0.2
    h = float(bandwidth) or step

    # Seed: the peak of each column's density, on the displayed y grid smoothed
    # with the same kernel (an unsmoothed histogram's argmax is noise).
    ybin = np.clip(np.searchsorted(grid, values, side="right") - 1, 0, n_bins - 1)
    counts = np.bincount(column * n_bins + ybin, weights=w,
                         minlength=n_cols * n_bins).reshape(n_cols, n_bins)
    radius = max(1, int(round(h / step)))
    kernel = np.exp(-0.5 * (np.arange(-2 * radius, 2 * radius + 1) / radius) ** 2)
    kernel /= kernel.sum()
    # Centre-slice the full convolution rather than asking for mode="same":
    # with few y bins the kernel is longer than the row, and numpy then returns
    # the *kernel's* length -- the argmax of which indexes past the grid.
    offset = kernel.size // 2
    smooth = np.apply_along_axis(
        lambda row: np.convolve(row, kernel)[offset:offset + n_bins], 1, counts
    )
    centre = grid_centres[np.argmax(smooth, axis=1)]
    centre = np.where(n > 0, centre, np.nan)

    # Mean shift onto the local mode of the unbinned values.
    for _ in range(iterations):
        seed = centre[column]
        weight = w * np.exp(-0.5 * ((values - seed) / h) ** 2)
        num = np.bincount(column, weights=weight * values, minlength=n_cols)
        den = np.bincount(column, weights=weight, minlength=n_cols)
        moved = np.divide(num, den, out=np.full(n_cols, np.nan), where=den > 0)
        centre = np.where(np.isfinite(moved), moved, centre)

    # Spread of the population that was actually used, over its effective size.
    seed = centre[column]
    weight = w * np.exp(-0.5 * ((values - seed) / h) ** 2)
    den = np.bincount(column, weights=weight, minlength=n_cols)
    den2 = np.bincount(column, weights=weight * weight, minlength=n_cols)
    dev = values - seed
    var_num = np.bincount(column, weights=weight * dev * dev, minlength=n_cols)
    safe = np.where(den > 0, den, np.nan)
    var = np.maximum(var_num / safe, 0.0)
    n_eff = np.divide(den * den, den2, out=np.full(n_cols, np.nan), where=den2 > 0)
    return centre, np.sqrt(var / np.where(n_eff > 0, n_eff, np.nan))


class CurveFitAborted(RuntimeError):
    """Raised inside a fit when the caller's progress callback says to stop."""


def _weighted_residual(
    y: np.ndarray, model: np.ndarray, ey: Optional[np.ndarray]
) -> np.ndarray:
    """Weighted residual of ``model`` against ``y``, skipping absent points.

    A point is skipped (residual zero) where the model does not reach, where
    the data column ran empty, or where its weight is not usable — never
    dropped, because a residual vector that changes length between steps is not
    something the optimiser can work with.
    """
    y = np.asarray(y, dtype=float)
    resid = np.zeros(y.shape, dtype=float)
    good = np.isfinite(model) & np.isfinite(y)
    if ey is not None:
        ey = np.asarray(ey, dtype=float)
        good &= np.isfinite(ey) & (ey > 0)
    if not good.any():
        # Nothing overlaps: a large flat residual, so the optimiser walks back
        # towards the data instead of reading a perfect fit off an empty set.
        return np.full(y.shape, 1e6)
    weights = ey[good] if ey is not None else 1.0
    resid[good] = (y[good] - model[good]) / weights
    return resid


#: Finite-difference step for the fits in this module. Their objectives are not
#: smooth at the 1e-8 scale the optimiser probes by default: counting data moves
#: in steps (a burst crosses a bin edge, or it does not), and the distance to a
#: *traced* curve is a minimum over discrete points. Probed that finely, the
#: derivative reads zero or noise, and the fit terminates on ``xtol`` having
#: moved nothing — a static FRET line stayed exactly where it was put while
#: reporting success. A per-mille step is over the roughness. (ChiSurf's own
#: optimiser default moved from machine epsilon to 1e-6 for the same reason.)
FINITE_DIFFERENCE_STEP = 1e-3

#: How far, in displayed bins, a bin of the cloud still pulls on the curve. A
#: burst plot is a mixture — populations plus junk — so a curve that describes
#: the populations must not be dragged by everything else on the plot; beyond a
#: couple of bins the pull flattens off instead of growing.
CLOUD_SCALE = 2.0


#: How many model evaluations the pre-fit scan may spend.
SCAN_BUDGET = 240


def _bounds_of(variables: Sequence[Any]) -> Tuple[np.ndarray, np.ndarray]:
    """Lower/upper bounds of ``variables``, ``inf`` where none are armed."""
    lower, upper = [], []
    for p in variables:
        bounded = bool(getattr(p, "bounds_on", False))
        lower.append(float(p.lb) if bounded else -np.inf)
        upper.append(float(p.ub) if bounded else np.inf)
    return np.array(lower), np.array(upper)


#: Most parameters a grid is tried for; beyond it the grid says nothing.
SCAN_MAX_PARAMETERS = 4

#: Factor either side of an unbounded parameter's value that the grid spans.
SCAN_SPAN = 4.0


def _scan_axis(parameter: Any, points: int) -> np.ndarray:
    """Values to try for one parameter: within its bounds, else a factor either side.

    Geometric where unbounded -- a lifetime, a correction factor, an amplitude
    is a scale, searched in ratios. The current value is always one of them, so
    a scan never returns a point worse than the start.
    """
    value = float(parameter.value)
    lo, hi = (float(parameter.lb), float(parameter.ub)) if getattr(parameter, "bounds_on", False) \
        else (-np.inf, np.inf)
    if np.isfinite(lo) and np.isfinite(hi) and hi > lo:
        grid = np.linspace(lo, hi, points)
    elif value > 0:
        grid = np.geomspace(value / SCAN_SPAN, value * SCAN_SPAN, points)
    elif value < 0:
        grid = -np.geomspace(-value / SCAN_SPAN, -value * SCAN_SPAN, points)
    else:
        grid = np.linspace(-1.0, 1.0, points)
    return np.unique(np.append(grid, value))


def _coarse_scan(
    variables: Sequence[Any],
    cost: Callable[[np.ndarray], float],
    budget: int = SCAN_BUDGET,
) -> bool:
    """Move ``variables`` to the best point of a coarse grid over them.

    A fit that moves the data has a rough, often degenerate landscape -- a
    detection-correction factor scales the population while a lifetime scales
    the line, so the two trade off along a valley and a purely local optimiser
    slides a little way down it and reports that as the answer. Scanning first
    costs a fixed number of evaluations (``budget``) and starts the fit in the
    right basin. Returns whether the best point beats the start.
    """
    import itertools

    variables = list(variables)
    if not variables or len(variables) > SCAN_MAX_PARAMETERS:
        return False
    per_axis = max(3, int(budget ** (1.0 / len(variables))))
    axes = [_scan_axis(p, per_axis) for p in variables]
    start = np.array([float(p.value) for p in variables], dtype=float)
    start_cost = best_cost = np.inf
    best = None
    try:
        for point in itertools.product(*axes):
            values = np.array(point, dtype=float)
            try:
                current = float(cost(values))
            except CurveFitAborted:
                raise
            except Exception:  # noqa: BLE001 - a point the model cannot reach
                continue
            if np.allclose(values, start):
                start_cost = current
            if np.isfinite(current) and current < best_cost:
                best, best_cost = values, current
    finally:
        _apply(variables, start if best is None else best)
    return bool(best is not None and best_cost < start_cost)


def _fit_from_best_start(
    variables: Sequence[Any],
    residuals: Callable[[np.ndarray], np.ndarray],
    diff_step: Optional[float] = None,
    scan: bool = False,
):
    """Local fit, from the scan's best point *and* from where the user left it.

    A coarse grid finds the deepest **grid point**, which is not the same thing
    as the deepest basin: on a smooth objective the start the user chose often
    descends further than any grid point does (observed — a Gaussian on a
    marginal, where the grid's best point ran downhill into a corner and
    returned ``mu = 0``). So when the scan moves the start, the local fit is run
    from both and the better result kept. Only the scan's own budget is at risk,
    never the answer.
    """
    start = np.array([float(p.value) for p in variables], dtype=float)
    moved = _coarse_scan(variables, lambda v: float(np.sum(residuals(v) ** 2))) if scan else False

    first = _least_squares(variables, residuals, diff_step=diff_step)
    if not moved:
        _apply(variables, first.x)
        return first

    _apply(variables, start)
    second = _least_squares(variables, residuals, diff_step=diff_step)
    best = first if first.cost <= second.cost else second
    _apply(variables, best.x)
    return best


def _apply(variables: Sequence[Any], values: Sequence[float]) -> None:
    """Write a solution vector back into its parameters."""
    for parameter, value in zip(variables, values):
        parameter.value = float(value)


def _least_squares(
    variables: Sequence[Any],
    residuals: Callable[[np.ndarray], np.ndarray],
    diff_step: Optional[float] = None,
):
    """Run ``scipy.optimize.least_squares`` over parameters with armed bounds."""
    from scipy.optimize import least_squares

    start = np.array([float(p.value) for p in variables], dtype=float)
    lower, upper = _bounds_of(variables)
    # least_squares rejects a start that sits on the wrong side of a bound.
    return least_squares(
        residuals,
        np.clip(start, lower, upper),
        bounds=(lower, upper),
        diff_step=diff_step,
    )


@dataclass
class DataParameters:
    """Parameters that move the **data**, not the curve.

    nDXplorer's constants (the detection-correction factor ``gG/gR``, the
    background rates, ``alpha``, ``PhiA``/``PhiD``, ``tauD0`` …) are the inputs
    of the equations that build the plotted axes, so freeing one does not
    reshape the curve — it moves the burst population under it. That is exactly
    how ``gamma`` and ``beta`` are determined: by requiring that the measured
    population sits on the static FRET line.

    Fitting them therefore means re-deriving the data at every step:
    :attr:`refresh` is called with the names that moved, recomputes the derived
    columns and re-bins them **on the bin edges the fit started with**, and
    returns the new ``(x, y, ey)``. The x grid is fixed for the life of the fit
    (same edges, same columns), so only y and its weights move and the
    optimiser's residual vector keeps its length.

    Attributes
    ----------
    parameters : list of Parameter
        The constants offered to the fit. They are the *live* objects of the
        constants table, so a fitted value is already in the table when the fit
        returns. Fixed ones are left alone.
    refresh : callable
        ``refresh(changed_names) -> (x, y, ey)``; recomputes the data for the
        parameters' current values.
    """

    parameters: List[Any] = field(default_factory=list)
    refresh: Optional[Callable[[Sequence[str]], Tuple[np.ndarray, np.ndarray, np.ndarray]]] = None

    def free(self) -> List[Any]:
        """The parameters the user has freed for the fit."""
        return [p for p in self.parameters if not getattr(p, "fixed", True)]

    def values(self) -> Dict[str, float]:
        """Current ``{name: value}`` of every offered parameter."""
        return {p.name: float(p.value) for p in self.parameters}


class _DataParameterHost:
    """Mixin: a fit that may also optimise :class:`DataParameters`.

    Both fit flavours (equation and parametric) can carry them, and both have
    to do the same three things — expose them to the dialog, add the free ones
    to the optimiser's vector, and re-read the data whenever one moves.
    """

    _data: Optional[DataParameters] = None
    _progress: Optional[Callable[[int], Any]] = None
    _steps: int = 0
    _frozen_ey: Optional[np.ndarray] = None

    def attach_data_parameters(self, data_parameters: Optional[DataParameters]) -> None:
        """Offer nDXplorer's constants to this fit (``None`` to offer none)."""
        self._data = data_parameters

    def set_progress(self, callback: Optional[Callable[[int], Any]]) -> None:
        """Report every step to ``callback(step)``; return ``False`` there to stop.

        A fit that re-derives the data is seconds rather than milliseconds, so
        the caller needs both a heartbeat to show and a way out of it.
        """
        self._progress = callback

    def _note_step(self) -> None:
        """Count one model evaluation and honour a stop request."""
        self._steps += 1
        if self._progress is not None and self._progress(self._steps) is False:
            raise CurveFitAborted("stopped")

    @property
    def data_parameters(self) -> List[Any]:
        """The constants offered to this fit (empty when there are none)."""
        return list(self._data.parameters) if self._data is not None else []

    def free_data_parameters(self) -> List[Any]:
        """The offered constants the user has freed."""
        if self._data is None or self._data.refresh is None:
            return []
        return self._data.free()

    def fitted_data_values(self) -> Dict[str, float]:
        """``{name: value}`` of the constants that actually took part.

        The fixed ones are not reported: nothing moved them, and the caller
        uses this list to decide which columns to recompute and redraw.
        """
        return {p.name: float(p.value) for p in self.free_data_parameters()}

    def freeze_weights(self, ey: Optional[np.ndarray]) -> None:
        """Hold the fit's weights at ``ey`` while the data moves.

        The uncertainty of a reduced point is estimated **from the data**, so
        letting it move with the fit hands the optimiser a way to lower chi2
        that has nothing to do with the curve: blur the population, and every
        residual shrinks. Observed on real bursts — the fit walked the
        detection-correction factor to a quarter of its value and reported a
        happier chi2 for a visibly worse line. The weights are the data's, so
        they are taken once, at the start, and held.
        """
        self._frozen_ey = None if ey is None else np.asarray(ey, dtype=float).copy()

    def _refresh_data(self, names: Sequence[str]):
        """Recompute the data for the constants' current values.

        ``refresh`` hands back ``(x, y, ey)`` for reduced points, or
        ``(x, y, ey, weights)`` for a cloud — passed through as it came, with
        only the (estimated, and therefore frozen) errors substituted.
        """
        refreshed = tuple(self._data.refresh(list(names)))
        x, y, ey = refreshed[0], refreshed[1], refreshed[2]
        frozen = self._frozen_ey
        if frozen is not None and ey is not None and np.shape(frozen) == np.shape(ey):
            ey = frozen
        return (x, y, ey) + refreshed[3:]


class CurveFit(_DataParameterHost):
    """An equation ``y = f(x; p)`` fitted to displayed data by least squares.

    Build it with :func:`build_curve_fit` (or one of the ``build_*_fit``
    helpers), edit the parameters' fix/free/bounds -- directly, through the
    parameter table, or by seeding them from the overlay curve with
    :meth:`seed_from_group` -- then call :meth:`run` as often as you like. The
    equation is evaluated exactly as the overlay draws it
    (:class:`~ndxplorer.core.overlay_curves.CurveEvaluator`) and optimised by
    ``scipy.optimize.least_squares`` within the armed bounds.
    """

    def __init__(self, equation: str, x: np.ndarray, y: np.ndarray,
                 ey: Optional[np.ndarray], parameters: Sequence[Any]) -> None:
        from ..core.overlay_curves import CurveEvaluator

        self.equation = str(equation)
        self._x = np.asarray(x, dtype=float)
        self._y = np.asarray(y, dtype=float)
        self._ey = None if ey is None else np.asarray(ey, dtype=float)
        self._parameters = list(parameters)
        self._evaluator = CurveEvaluator()

    @property
    def parameters(self) -> List[Any]:
        """The fit's own parameters (``x`` is not one)."""
        return self._parameters

    def values(self) -> Dict[str, float]:
        """Return the current ``{name: value}`` for every parameter."""
        return {p.name: float(p.value) for p in self._parameters}

    def set_fixed(self, name: str, fixed: bool) -> None:
        """Fix or free a parameter by name."""
        for p in self._parameters:
            if p.name == name:
                p.fixed = bool(fixed)

    def seed_from_group(self, group: Any) -> None:
        """Take value, bounds and fix/free from the curve's own parameters.

        The overlay's table is then the one place those are set: what is fixed
        there is held here, and the bounds drawn there bound the optimiser. A
        *linked* parameter is additionally forced fixed -- its value is its
        master's, and moving it would either be discarded or fight the link.
        """
        if group is None:
            return
        source = {p.name: p for p in group.parameters_all}
        for p in self._parameters:
            src = source.get(p.name)
            if src is None:
                continue
            p.value = float(src.value)
            p.lb, p.ub = float(src.lb), float(src.ub)
            p.bounds_on = bool(src.bounds_on)
            p.fixed = is_held(src)

    def write_back(self, group: Any) -> None:
        """Write the fitted values into the curve's own parameters (not over a link)."""
        if group is None:
            return
        target = {p.name: p for p in group.parameters_all}
        for name, value in self.values().items():
            param = target.get(name)
            if param is not None and not is_held_by_link(param):
                param.value = float(value)

    def evaluate(self) -> np.ndarray:
        """The equation at the data's x, for the current values."""
        y = self._evaluator.evaluate(self.equation, self._x, self.values())
        return np.broadcast_to(np.asarray(y, dtype=float), self._x.shape).astype(float)

    def _set_data(self, y: np.ndarray, ey: np.ndarray) -> None:
        """Hold the re-derived data (the x grid is fixed for the life of a fit)."""
        self._y = np.asarray(y, dtype=float)
        self._ey = None if ey is None else np.asarray(ey, dtype=float)

    def _residuals(self, variables: List[Any], names: Sequence[str]):
        def residuals(values: np.ndarray) -> np.ndarray:
            _apply(variables, values)
            self._note_step()
            if names:
                _x, y, ey = self._refresh_data(names)
                self._set_data(y, ey)
            return _weighted_residual(self._y, self.evaluate(), self._ey)

        return residuals

    def run(self, scan: Optional[bool] = None) -> CurveFitResult:
        """Optimise every free parameter (holding the fixed ones); return the result.

        ``scan`` runs a coarse grid over the free parameters first and starts
        the local fit at its best point (:func:`grid_scan`). ``None`` scans when
        a constant is free -- the case whose landscape is degenerate enough to
        strand a local optimiser. A freed constant moves the *data*, which is
        re-derived at every step.
        """
        free = [p for p in self._parameters if not getattr(p, "fixed", False)]
        free_data = self.free_data_parameters()
        if not free and not free_data:
            return CurveFitResult(False, message="all parameters are fixed")
        if scan is None:
            scan = bool(free_data)
        variables = list(free) + list(free_data)
        names = [p.name for p in free_data]
        start = [float(p.value) for p in variables]
        if free_data:
            self.freeze_weights(self._ey)
        try:
            solution = _fit_from_best_start(
                variables, self._residuals(variables, names),
                diff_step=FINITE_DIFFERENCE_STEP if free_data else None, scan=scan)
        except Exception as exc:
            _apply(variables, start)  # leave the data as it was
            if names:
                try:
                    self._set_data(*self._refresh_data(names)[1:3])
                except Exception:  # noqa: BLE001
                    pass
            message = "stopped" if isinstance(exc, CurveFitAborted) else f"fit failed: {exc}"
            return CurveFitResult(False, message=message)
        _apply(variables, solution.x)
        if names:
            self._set_data(*self._refresh_data(names)[1:3])
        model = self.evaluate()
        good = int(np.sum(np.isfinite(model) & np.isfinite(self._y)))
        dof = max(1, good - len(variables))
        return CurveFitResult(True, params=self.values(), chi2r=float(2.0 * solution.cost / dof),
                              y_fit=model, data_params=self.fitted_data_values())


def is_held_by_link(parameter: Any) -> bool:
    """Whether *parameter* follows another one (its value is not its own)."""
    return bool(getattr(parameter, "is_linked", False))


#: Parameters that set a curve's *resolution*, not its shape. They come from the
#: function's signature like any other, but optimising the number of points a
#: line is drawn with is meaningless (and its objective is a staircase), so they
#: start fixed. Free them in the table if you really mean to.
RESOLUTION_PARAMETERS = frozenset(
    {"num_points", "n_points", "npoints", "points", "n", "steps"}
)


class ParametricCurveFit(_DataParameterHost):
    """Fit a curve that returns ``(x, y)`` — a FRET line — to displayed data.

    The predefined FRET lines are not ``y = f(x)``: they sweep a mean distance
    and return the pair of arrays they trace out, so this class optimises the
    function directly against a distance, not a vertical offset.

    A point's residual is its **distance to the traced curve**, in units of the
    point's own uncertainties (``ex`` across, ``ey`` up). The obvious
    alternative — interpolate the curve onto the data's x and take the vertical
    offset — has two failure modes that a real fit walks straight into: a point
    the curve does not span has *no* vertical offset, so the optimiser is
    rewarded for making the curve **shorter** until it covers only the points it
    already fits (observed: a static FRET line collapsing to ``tau_d0`` ≈ 1 ns
    with a third of the columns and a "better" chi2); and where the curve runs
    steeply the vertical offset is arbitrarily large for a point that is
    perfectly close to it. A distance is defined everywhere and is what "the
    population lies on the line" means.

    The parameters *are* the curve's own :class:`Parameter` objects — not
    copies — so the table the user is looking at is what is optimised, and the
    fitted values are already in it when the fit returns.
    """

    def __init__(
        self,
        function: Any,
        parameters: List[Any],
        x: np.ndarray,
        y: np.ndarray,
        ey: Optional[np.ndarray] = None,
        ex: Optional[float] = None,
        weights: Optional[np.ndarray] = None,
        f_scale: float = CLOUD_SCALE,
    ) -> None:
        self._function = function
        self._parameters = list(parameters)
        self._x = np.asarray(x, dtype=float)
        self._y = np.asarray(y, dtype=float)
        self._ey = None if ey is None else np.asarray(ey, dtype=float)
        #: How far along x counts as "as far as one ey" — the width of the
        #: column a point was reduced from. Without it the distance would
        #: compare nanoseconds with efficiencies.
        self._ex = float(ex) if ex else self._default_ex()
        #: Per-point weight. Set (to bin counts) the fit is against the **cloud**
        #: — every occupied bin of the distribution, not one reduced point per
        #: column. ``None`` keeps the reduced-point fit.
        self._weights = None if weights is None else np.asarray(weights, dtype=float)
        self._f_scale = float(f_scale)
        #: What the cloud weighed when the fit was built, and what a point that
        #: has left the plotted range costs. Without them a fit with a free
        #: constant has a trivial way out: push the population off the axes,
        #: and a cloud with nothing in it matches every curve perfectly.
        self._total_weight = (
            None if self._weights is None else float(np.sum(self._weights))
        )
        self._outside_penalty = (
            None if self._weights is None
            else float(np.log1p((self._grid_extent() / self._f_scale) ** 2))
        )
        self._chi2r = float("nan")

    def _grid_extent(self) -> float:
        """How many bins across the displayed range is, at its widest."""
        try:
            return float(max(np.unique(self._x).size, np.unique(self._y).size))
        except Exception:  # pragma: no cover - degenerate input
            return 10.0

    def _set_data(self, refreshed) -> None:
        """Take what ``refresh`` handed back: reduced points, or a cloud.

        A cloud carries a fourth array — what each of its bins counted — because
        the population it weighs moves with the constant being fitted.
        """
        if len(refreshed) == 4:
            self._x, self._y, self._ey, self._weights = (
                np.asarray(a, dtype=float) if a is not None else None
                for a in refreshed
            )
        else:
            self._x, self._y, self._ey = refreshed

    def _default_ex(self) -> float:
        """Half the spacing of the data's x, when the caller did not say."""
        if self._x.size > 1:
            spacing = float(np.median(np.diff(np.sort(self._x))))
            if spacing > 0:
                return 0.5 * spacing
        return 1.0

    @property
    def parameters(self) -> List[Any]:
        """The curve's free/fixed parameters."""
        return self._parameters

    def values(self) -> Dict[str, float]:
        """Return the current ``{name: value}`` for every parameter."""
        return {p.name: float(p.value) for p in self._parameters}

    def set_fixed(self, name: str, fixed: bool) -> None:
        """Fix or free a parameter by name."""
        for p in self._parameters:
            if p.name == name:
                p.fixed = bool(fixed)

    def seed_from_group(self, group: Any) -> None:
        """No-op: these *are* the group's parameters, not a copy of them."""

    def write_back(self, group: Any) -> None:
        """No-op: the optimiser wrote straight into the group's parameters."""

    def _trace(self, values: Dict[str, float]) -> Tuple[np.ndarray, np.ndarray]:
        """Call the curve's function; return its ``(x, y)`` sorted by x."""
        traced = self._function(**values)
        xs, ys = (np.asarray(a, dtype=float) for a in traced)
        order = np.argsort(xs)
        return xs[order], ys[order]

    def _evaluate(self, values: Dict[str, float]) -> np.ndarray:
        """The curve interpolated onto the data's x (``nan`` where it does not reach).

        Only for reporting the fitted curve back to the caller — the fit itself
        uses distances (:meth:`_distance_residual`), which are defined for every
        point.
        """
        xs, ys = self._trace(values)
        inside = (self._x >= xs[0]) & (self._x <= xs[-1])
        out = np.full(self._x.shape, np.nan)
        out[inside] = np.interp(self._x[inside], xs, ys)
        return out

    def _distance_residual(self, values: Dict[str, float]) -> np.ndarray:
        """Signed distance from each point to the curve, in units of its errors.

        The sign is the point's offset in y from the nearest bit of curve, so
        the residual passes smoothly through zero as the curve crosses a point
        rather than bouncing off it.
        """
        xs, ys = self._trace(values)
        if xs.size == 0:
            return np.full(self._y.shape, 1e6)
        ey = self._ey
        if ey is None:
            ey = np.ones(self._y.shape)
        ey = np.where(np.isfinite(ey) & (ey > 0), ey, np.nan)
        good = np.isfinite(self._x) & np.isfinite(self._y) & np.isfinite(ey)
        if not good.any():
            return np.full(self._y.shape, 1e6)

        dx = (self._x[good, None] - xs[None, :]) / self._ex
        dy = (self._y[good, None] - ys[None, :]) / ey[good, None]
        square = dx * dx + dy * dy
        nearest = np.argmin(square, axis=1)
        distance = np.sqrt(square[np.arange(nearest.size), nearest])
        sign = np.sign(self._y[good] - ys[nearest])
        sign[sign == 0] = 1.0

        out = np.zeros(self._y.shape)
        if self._weights is None:
            out[good] = sign * distance
            return out
        # Fitting the cloud:each bin weighs what it counted, and a bin further
        # than a few scales away stops pulling — the plot is a mixture and a
        # curve does not have to describe the junk to describe the populations.
        out[good] = np.sqrt(
            self._weights[good] * np.log1p((distance / self._f_scale) ** 2)
        )
        # ...and one more component for everything that has left the plot: it
        # cannot be described by a curve that is not there, so it costs what
        # the furthest visible point would.
        lost = max(float(self._total_weight) - float(np.sum(self._weights)), 0.0)
        return np.append(out, np.sqrt(lost * self._outside_penalty))

    def _residuals(
        self, free_values: np.ndarray, free: List[Any], data_names: Sequence[str]
    ) -> np.ndarray:
        for param, value in zip(free, free_values):
            param.value = float(value)
        self._note_step()
        if data_names:
            # A freed constant moved the population, not the curve: re-derive
            # the data before comparing anything to it.
            self._set_data(self._refresh_data(data_names))
        return self._distance_residual(self.values())

    def run(self, scan: Optional[bool] = None) -> CurveFitResult:
        """Optimise every free parameter (holding the fixed ones).

        ``scan`` runs a coarse grid first; ``None`` scans when a constant is
        free (see :meth:`CurveFit.run`).
        """
        free = [p for p in self._parameters if not getattr(p, "fixed", False)]
        free_data = self.free_data_parameters()
        if not free and not free_data:
            return CurveFitResult(False, message="all parameters are fixed")
        if scan is None:
            scan = bool(free_data)

        variables = free + free_data
        data_names = [p.name for p in free_data]
        start = [float(p.value) for p in variables]
        if data_names and self._weights is None:
            # Reduced points carry an estimated error; a cloud carries counts,
            # which are not something the fit could inflate.
            self.freeze_weights(self._ey)

        try:
            fit = _fit_from_best_start(
                variables,
                lambda v: self._residuals(v, variables, data_names),
                diff_step=FINITE_DIFFERENCE_STEP,
                scan=scan,
            )
        except CurveFitAborted:
            for param, value in zip(variables, start):
                param.value = float(value)
            if data_names:
                self._set_data(self._refresh_data(data_names))
            return CurveFitResult(False, message="stopped")
        except Exception as exc:
            for param, value in zip(variables, start):  # leave things as they were
                param.value = float(value)
            if data_names:
                try:
                    self._set_data(self._refresh_data(data_names))
                except Exception:
                    pass
            return CurveFitResult(False, message=f"fit failed: {exc}")

        for param, value in zip(variables, fit.x):
            param.value = float(value)
        if data_names:
            self._set_data(self._refresh_data(data_names))
        model = self._evaluate(self.values())
        dof = max(1, int(np.isfinite(self._y).sum()) - len(variables))
        self._chi2r = float(2.0 * fit.cost / dof)
        return CurveFitResult(
            True,
            params=self.values(),
            chi2r=self._chi2r,
            y_fit=model,
            data_params=self.fitted_data_values(),
        )


def build_function_fit(
    function: Any,
    parameters: List[Any],
    x: Sequence[float],
    y: Sequence[float],
    ey: Optional[Sequence[float]] = None,
) -> ParametricCurveFit:
    """Build a :class:`ParametricCurveFit` over a curve's own parameters.

    Parameters named in :data:`RESOLUTION_PARAMETERS` start fixed.

    Raises
    ------
    CurveFitError
        If the function has no parameters to fit or the data is too short.
    """
    if not callable(function):
        raise CurveFitError("curve has no function to fit")
    if len(parameters) == 0:
        raise CurveFitError("curve has no parameters to fit")
    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if x.size < 3 or y.size != x.size:
        raise CurveFitError("need at least 3 matching data points")
    for p in parameters:
        if getattr(p, "name", None) in RESOLUTION_PARAMETERS:
            p.fixed = True
    return ParametricCurveFit(function, parameters, x, y, ey)


def build_function_histogram_fit(
    function: Any,
    parameters: List[Any],
    counts: Sequence[Sequence[float]],
    x_edges: Sequence[float],
    y_edges: Sequence[float],
    *,
    min_counts: float = 3.0,
) -> ParametricCurveFit:
    """Build a :class:`ParametricCurveFit` against the displayed 2-D data."""
    x, y, ey = ridge_from_histogram(counts, x_edges, y_edges, min_counts=min_counts)
    return build_function_fit(function, parameters, x, y, ey)


def build_curve_fit(
    equation: str,
    x: Sequence[float],
    y: Sequence[float],
    ey: Optional[Sequence[float]] = None,
    *,
    initial: Optional[Dict[str, float]] = None,
    constant_names: Sequence[str] = (),
    fixed: Sequence[str] = (),
    reserved: Sequence[str] = ("x",),
) -> CurveFit:
    """Build a :class:`CurveFit` of ``equation`` against ``(x, y[, ey])``.

    Parameters
    ----------
    equation
        ``y = f(x; params)`` as the overlay writes it: ``x`` and named parameters.
    x, y
        The data to fit: for a marginal, bin centres and counts; for the
        displayed 2-D distribution, the column centres and their mean y (see
        :func:`ridge_from_histogram`).
    ey
        Per-point uncertainties (the fit's weights). Defaults to unweighted.
    initial
        Starting ``{name: value}`` for the parameters.
    constant_names
        Parameter names that are nDXplorer constants -- **fixed by default**
        (seed their value via ``initial``).
    fixed
        Additional names to hold fixed.
    reserved
        Names that are not parameters (the independent variable ``x``).

    Raises
    ------
    CurveFitError
        If there is too little data, the equation does not evaluate, or it has
        no parameters.
    """
    from ..core.overlay_curves import equation_parameter_names
    from ..core.parameters import Parameter

    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if x.size < 3 or y.size != x.size:
        raise CurveFitError("need at least 3 matching data points")
    reserved_set = {str(r) for r in reserved}
    held = {str(c) for c in constant_names} | {str(f) for f in fixed}
    initial = initial or {}
    # In the order the equation names them, as it is read.
    first: Dict[str, int] = {}
    for match in re.finditer(r"[A-Za-z_]\w*", str(equation)):
        first.setdefault(match.group(0), match.start())
    names = sorted((n for n in equation_parameter_names(str(equation)) if n not in reserved_set),
                   key=lambda n: first.get(n, 0))
    if not names:
        raise CurveFitError("equation has no free parameters")
    parameters = [Parameter(n, float(initial.get(n, 1.0)), fixed=n in held) for n in names]
    cf = CurveFit(str(equation), x, y, None if ey is None else np.asarray(ey, dtype=float),
                  parameters)
    try:
        cf.evaluate()
    except Exception as exc:
        raise CurveFitError(f"cannot evaluate equation: {exc}") from exc
    return cf


def build_marginal_fit(
    equation: str,
    x: Sequence[float],
    counts: Sequence[float],
    **kwargs: Any,
) -> CurveFit:
    """Build a :class:`CurveFit` against a 1-D marginal histogram.

    Counting data, so the weights are Poisson (``sqrt(N)``, empty bins floored
    at one) and chi-square is meaningful.
    """
    counts = np.asarray(counts, dtype=float)
    ey = np.sqrt(np.maximum(counts, 1.0))
    return build_curve_fit(equation, x, counts, ey, **kwargs)


def build_histogram_fit(
    equation: str,
    counts: Sequence[Sequence[float]],
    x_edges: Sequence[float],
    y_edges: Sequence[float],
    *,
    min_counts: float = 3.0,
    **kwargs: Any,
) -> CurveFit:
    """Build a :class:`CurveFit` of ``y = f(x)`` against the displayed 2-D data.

    The histogram is reduced by :func:`ridge_from_histogram` to one weighted
    point per populated x column.
    """
    x, y, ey = ridge_from_histogram(counts, x_edges, y_edges, min_counts=min_counts)
    return build_curve_fit(equation, x, y, ey, **kwargs)


def fit_equation_to_marginal(
    equation: str,
    initial: Dict[str, float],
    x: Sequence[float],
    counts: Sequence[float],
    **kwargs: Any,
) -> CurveFitResult:
    """One-shot fit of ``y = f(x; params)`` to a 1-D histogram (never raises).

    A thin wrapper over :func:`build_marginal_fit` + :meth:`CurveFit.run` for
    callers that just want the result (the no-dialog path and tests).
    """
    try:
        cf = build_marginal_fit(equation, x, counts, initial=initial, **kwargs)
    except CurveFitError as exc:
        return CurveFitResult(False, message=str(exc))
    return cf.run()


def fit_equation_to_histogram(
    equation: str,
    initial: Dict[str, float],
    counts: Sequence[Sequence[float]],
    x_edges: Sequence[float],
    y_edges: Sequence[float],
    **kwargs: Any,
) -> CurveFitResult:
    """One-shot fit of ``y = f(x; params)`` to the displayed 2-D data (never raises)."""
    try:
        cf = build_histogram_fit(
            equation, counts, x_edges, y_edges, initial=initial, **kwargs
        )
    except CurveFitError as exc:
        return CurveFitResult(False, message=str(exc))
    return cf.run()


__all__ = [
    "CurveFit",
    "CurveFitAborted",
    "SCAN_BUDGET",
    "DataParameters",
    "CLOUD_SCALE",
    "FINITE_DIFFERENCE_STEP",
    "ParametricCurveFit",
    "RESOLUTION_PARAMETERS",
    "build_function_fit",
    "build_function_histogram_fit",
    "CurveFitError",
    "CurveFitResult",
    "bin_centers",
    "column_counts",
    "populated_columns",
    "REDUCTIONS",
    "ridge_from_histogram",
    "ridge_from_values",
    "build_curve_fit",
    "build_marginal_fit",
    "build_histogram_fit",
    "fit_equation_to_marginal",
    "fit_equation_to_histogram",
]
