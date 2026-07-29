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

Either way the equation is wrapped in a ChiSurf ``ParseModel`` and optimised by
ChiSurf's least-squares ``Fit``, so the same safe formula that draws the overlay
also drives the fit.

The model's parameters *are* the fitting group: the curve's own
:class:`FittingParameter` objects seed them (value, bounds and fix/free straight
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

Qt-free and headless-testable; ChiSurf is imported lazily.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np


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
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Reduce a displayed 2-D histogram to the ``y(x)`` points a curve fits to.

    Each x column of the histogram is summarised by the count-weighted mean of
    y and the standard error of that mean, which is what makes the fit weight a
    densely populated column more than a sparse one. Columns holding fewer than
    ``min_counts`` events are dropped: with one or two bursts in a column the
    mean is noise, and a point there would drag the curve as hard as a real one.

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

    Returns
    -------
    x, y, ey : ndarray
        Column centres, their mean y, and the standard error of that mean
        (floored at half a y-bin: a column can never be located better than the
        binning it is displayed with).

    Raises
    ------
    CurveFitError
        If the histogram is empty, does not match its edges, or too few columns
        survive to fit anything.
    """
    h, xe, ye = _oriented(counts, x_edges, y_edges)

    xc = bin_centers(xe)
    yc = bin_centers(ye)
    n = h.sum(axis=1)
    if keep is None:
        mask = n >= float(min_counts)
        if int(mask.sum()) < 3:
            raise CurveFitError("too few populated columns to fit (need 3)")
    else:
        mask = np.asarray(keep, dtype=bool)
        if mask.size != n.size:
            raise CurveFitError("column mask does not match the histogram")

    h = h[mask]
    n = n[mask]
    # A forced column may have run empty; report it as nan rather than dividing
    # by zero (the caller's residual skips the point).
    safe = np.where(n > 0, n, np.nan)
    mean = (h * yc).sum(axis=1) / safe
    var = (h * (yc - mean[:, None]) ** 2).sum(axis=1) / safe
    sem = np.sqrt(np.maximum(var, 0.0) / safe)
    floor = 0.5 * float(np.median(np.diff(yc))) if yc.size > 1 else 1.0
    return xc[mask], mean, np.maximum(sem, floor)


def ridge_from_values(
    x: Sequence[float],
    y: Sequence[float],
    x_edges: Sequence[float],
    *,
    weights: Optional[Sequence[float]] = None,
    y_edges: Optional[Sequence[float]] = None,
    keep: Optional[Sequence[bool]] = None,
    min_counts: float = 3.0,
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """The same reduction as :func:`ridge_from_histogram`, from unbinned values.

    One weighted mean of y per x column, with its standard error. Taking it over
    the values rather than over the displayed y bins matters as soon as a
    constant is being fitted: a *binned* mean moves in steps, as bursts cross
    bin edges, so the finite-difference derivative reads exactly zero and the
    optimiser stops before it starts.

    ``y_edges`` only supplies the error floor (half a displayed y bin); ``keep``
    pins the columns, as in :func:`ridge_from_histogram`.
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
    total = np.bincount(column, weights=w * values, minlength=n_cols)
    square = np.bincount(column, weights=w * values * values, minlength=n_cols)
    if keep is None:
        mask = n >= float(min_counts)
        if int(mask.sum()) < 3:
            raise CurveFitError("too few populated columns to fit (need 3)")
    else:
        mask = np.asarray(keep, dtype=bool)
        if mask.size != n_cols:
            raise CurveFitError("column mask does not match the bin edges")

    safe = np.where(n > 0, n, np.nan)
    mean = total / safe
    var = np.maximum(square / safe - mean ** 2, 0.0)
    sem = np.sqrt(var / safe)
    floor = 1.0
    if y_edges is not None:
        ye = np.asarray(y_edges, dtype=float)
        if ye.size > 2:
            floor = 0.5 * float(np.median(np.diff(ye)))
    centers = 0.5 * (edges[:-1] + edges[1:])
    return centers[mask], mean[mask], np.maximum(sem[mask], floor)


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


#: Finite-difference step for a fit that moves the data. Counting data changes
#: in steps — a burst crosses a bin edge, or it does not — so the default step
#: (~1e-8, relative) measures a derivative of exactly zero and the optimiser
#: stops before it has started. A step of a per-mille actually moves the
#: population, which is what the derivative has to be taken over.
DATA_PARAMETER_STEP = 1e-3


def _least_squares(
    variables: Sequence[Any],
    residuals: Callable[[np.ndarray], np.ndarray],
    diff_step: Optional[float] = None,
):
    """Run ``scipy.optimize.least_squares`` over parameters with armed bounds."""
    from scipy.optimize import least_squares

    start = np.array([float(p.value) for p in variables], dtype=float)
    lower, upper = [], []
    for p in variables:
        bounded = bool(getattr(p, "bounds_on", False))
        lower.append(float(p.lb) if bounded else -np.inf)
        upper.append(float(p.ub) if bounded else np.inf)
    lower, upper = np.array(lower), np.array(upper)
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
    parameters : list of FittingParameter
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

    def _refresh_data(self, names: Sequence[str]):
        """Recompute the data for the constants' current values."""
        return self._data.refresh(list(names))


class CurveFit(_DataParameterHost):
    """A built ChiSurf ``ParseModel`` fit of an equation to displayed data.

    Build it with :func:`build_curve_fit` (or one of the ``build_*_fit``
    helpers), edit the parameters' fix/free/bounds — directly, through the
    fitting table, or by seeding them from the overlay curve with
    :meth:`seed_from_group` — then call :meth:`run` as often as you like. The
    objects returned by :attr:`parameters` are live ``FittingParameter``s,
    suitable for a ``ParameterGroupTableWidget``.
    """

    def __init__(self, fit: Any, model: Any, reserved: Sequence[str]) -> None:
        self._fit = fit
        self._model = model
        self._reserved = {str(r) for r in reserved}

    @property
    def model(self) -> Any:
        """The underlying ``ParseModel``."""
        return self._model

    @property
    def parameters(self) -> List[Any]:
        """The free/fixed ``FittingParameter`` objects (excluding ``x``)."""
        return [
            p
            for p in getattr(self._model, "_parameters_equation", [])
            if getattr(p, "name", None) not in self._reserved
        ]

    def values(self) -> Dict[str, float]:
        """Return the current ``{name: value}`` for every parameter."""
        return {p.name: float(p.value) for p in self.parameters}

    def set_fixed(self, name: str, fixed: bool) -> None:
        """Fix or free a parameter by name."""
        for p in self.parameters:
            if p.name == name:
                p.fixed = bool(fixed)

    def seed_from_group(self, group: Any) -> None:
        """Take value, bounds and fix/free from the curve's own parameters.

        The overlay's table is then the one place those are set: what is fixed
        there is held here, and the bounds drawn there bound the optimiser. A
        *linked* parameter is additionally forced fixed — its value is its
        master's, and moving it would either be discarded or fight the link.
        """
        if group is None:
            return
        source = {p.name: p for p in group.parameters_all}
        for p in self.parameters:
            src = source.get(getattr(p, "name", None))
            if src is None:
                continue
            try:
                p.value = float(src.value)
                p.lb, p.ub = float(src.lb), float(src.ub)
                p.bounds_on = bool(getattr(src, "bounds_on", False))
                p.fixed = bool(getattr(src, "fixed", False)) or bool(
                    getattr(src, "is_linked", False)
                )
            except Exception:
                continue

    def write_back(self, group: Any) -> None:
        """Write the fitted values into the curve's own parameters.

        Linked parameters are skipped: their value is owned by the master they
        follow, so assigning here would be either discarded or a silent unlink.
        """
        if group is None:
            return
        target = {p.name: p for p in group.parameters_all}
        for name, value in self.values().items():
            param = target.get(name)
            if param is None or getattr(param, "is_linked", False):
                continue
            try:
                param.value = float(value)
            except (TypeError, ValueError):
                continue

    def run(self) -> CurveFitResult:
        """Optimise every free parameter (holding the fixed ones); return the result."""
        free = [p for p in self.parameters if not getattr(p, "fixed", False)]
        free_data = self.free_data_parameters()
        if not free and not free_data:
            return CurveFitResult(False, message="all parameters are fixed")
        if free_data:
            # A freed constant moves the *data*, which ChiSurf's optimiser knows
            # nothing about — equation and constants are optimised together here
            # instead, re-deriving the data at every step.
            return self._run_joint(free, free_data)
        try:
            self._model.update_model()
            self._fit.run()
        except Exception as exc:
            return CurveFitResult(False, message=f"fit failed: {exc}")
        params = self.values()
        y_fit = (
            np.asarray(self._model.y, dtype=float)
            if getattr(self._model, "y", None) is not None
            else None
        )
        try:
            chi2r = float(self._fit.chi2r)
        except Exception:
            chi2r = float("nan")
        return CurveFitResult(True, params=params, chi2r=chi2r, y_fit=y_fit)

    def _set_data(self, y: np.ndarray, ey: np.ndarray) -> None:
        """Put the re-derived data on the fit, so it holds what was fitted.

        Only y and its weights are written: the x grid is fixed for the life of
        a data-parameter fit (same bin edges, same columns), which is what keeps
        the residual vector's length constant.
        """
        try:
            self._fit.data.y = np.asarray(y, dtype=float)
            self._fit.data.ey = np.asarray(ey, dtype=float)
        except Exception:
            pass

    def _run_joint(self, free: List[Any], free_data: List[Any]) -> CurveFitResult:
        """Optimise equation parameters and freed constants in one vector."""
        variables = list(free) + list(free_data)
        names = [p.name for p in free_data]
        start = [float(p.value) for p in variables]

        def residuals(values: np.ndarray) -> np.ndarray:
            for param, value in zip(variables, values):
                param.value = float(value)
            self._note_step()
            x, y, ey = self._refresh_data(names)
            self._model.update_model()
            return _weighted_residual(y, np.asarray(self._model.y, dtype=float), ey)

        try:
            solution = _least_squares(
                variables, residuals, diff_step=DATA_PARAMETER_STEP
            )
        except CurveFitAborted:
            for param, value in zip(variables, start):
                param.value = float(value)
            self._refresh_data(names)
            return CurveFitResult(False, message="stopped")
        except Exception as exc:
            for param, value in zip(variables, start):  # leave the data as it was
                param.value = float(value)
            try:
                self._refresh_data(names)
            except Exception:
                pass
            return CurveFitResult(False, message=f"fit failed: {exc}")

        for param, value in zip(variables, solution.x):
            param.value = float(value)
        x, y, ey = self._refresh_data(names)
        self._set_data(y, ey)
        self._model.update_model()
        model = np.asarray(self._model.y, dtype=float)
        dof = max(1, int(np.isfinite(model).sum()) - len(variables))
        return CurveFitResult(
            True,
            params=self.values(),
            chi2r=float(2.0 * solution.cost / dof),
            y_fit=model,
            data_params=self.fitted_data_values(),
        )


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
    and return the pair of arrays they trace out. There is no ``ParseModel`` to
    build from that, so this class optimises the function directly: for a trial
    set of parameters it calls the function, sorts the traced curve by x, and
    interpolates it onto the x of the data, giving one residual per data point
    the curve actually spans.

    The parameters *are* the curve's own :class:`FittingParameter` objects — not
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
    ) -> None:
        self._function = function
        self._parameters = list(parameters)
        self._x = np.asarray(x, dtype=float)
        self._y = np.asarray(y, dtype=float)
        self._ey = None if ey is None else np.asarray(ey, dtype=float)
        self._chi2r = float("nan")

    @property
    def parameters(self) -> List[Any]:
        """The curve's free/fixed ``FittingParameter`` objects."""
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

    def _evaluate(self, values: Dict[str, float]) -> np.ndarray:
        """Trace the curve and interpolate it onto the data's x.

        Returns ``nan`` where the curve does not reach, so those points are
        dropped from the residual rather than pinned to an edge value.
        """
        traced = self._function(**values)
        xs, ys = (np.asarray(a, dtype=float) for a in traced)
        order = np.argsort(xs)
        xs, ys = xs[order], ys[order]
        inside = (self._x >= xs[0]) & (self._x <= xs[-1])
        out = np.full(self._x.shape, np.nan)
        out[inside] = np.interp(self._x[inside], xs, ys)
        return out

    def _residuals(
        self, free_values: np.ndarray, free: List[Any], data_names: Sequence[str]
    ) -> np.ndarray:
        for param, value in zip(free, free_values):
            param.value = float(value)
        self._note_step()
        if data_names:
            # A freed constant moved the population, not the curve: re-derive
            # the data before comparing anything to it.
            self._x, self._y, self._ey = self._refresh_data(data_names)
        model = self._evaluate(self.values())
        return _weighted_residual(self._y, model, self._ey)

    def run(self) -> CurveFitResult:
        """Optimise every free parameter (holding the fixed ones)."""
        free = [p for p in self._parameters if not getattr(p, "fixed", False)]
        free_data = self.free_data_parameters()
        if not free and not free_data:
            return CurveFitResult(False, message="all parameters are fixed")

        variables = free + free_data
        data_names = [p.name for p in free_data]
        start = [float(p.value) for p in variables]

        try:
            fit = _least_squares(
                variables,
                lambda v: self._residuals(v, variables, data_names),
                diff_step=DATA_PARAMETER_STEP if data_names else None,
            )
        except CurveFitAborted:
            for param, value in zip(variables, start):
                param.value = float(value)
            if data_names:
                self._x, self._y, self._ey = self._refresh_data(data_names)
            return CurveFitResult(False, message="stopped")
        except Exception as exc:
            for param, value in zip(variables, start):  # leave things as they were
                param.value = float(value)
            if data_names:
                try:
                    self._x, self._y, self._ey = self._refresh_data(data_names)
                except Exception:
                    pass
            return CurveFitResult(False, message=f"fit failed: {exc}")

        for param, value in zip(variables, fit.x):
            param.value = float(value)
        if data_names:
            self._x, self._y, self._ey = self._refresh_data(data_names)
        model = self._evaluate(self.values())
        good = np.isfinite(model)
        dof = max(1, int(good.sum()) - len(variables))
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
    fit_range: Optional[Tuple[int, int]] = None,
) -> CurveFit:
    """Build a :class:`CurveFit` of ``equation`` against ``(x, y[, ey])``.

    Parameters
    ----------
    equation
        A ``ParseModel`` formula in ``x`` and named parameters.
    x, y
        The data to fit: for a marginal, bin centres and counts; for the
        displayed 2-D distribution, the column centres and their mean y (see
        :func:`ridge_from_histogram`).
    ey
        Per-point uncertainties (the fit's weights). Defaults to unweighted.
    initial
        Starting ``{name: value}`` for the parameters.
    constant_names
        Parameter names that are nDXplorer constants — **fixed by default**
        (seed their value via ``initial``).
    fixed
        Additional names to hold fixed.
    reserved
        Names that are not parameters (the independent variable ``x``).
    fit_range
        ``(start, stop)`` index range to fit; defaults to all of the data.

    Raises
    ------
    CurveFitError
        If ChiSurf is unavailable, there is too little data, the equation does
        not parse, or it has no free parameters.
    """
    try:
        import chisurf.core.fitting.fit as fit_mod
        from chisurf.core.data import DataCurve
        from chisurf.core.models.parse import ParseModel
    except Exception as exc:  # pragma: no cover - depends on environment
        raise CurveFitError(f"ChiSurf fitting is not available: {exc}") from exc

    x = np.asarray(x, dtype=float)
    y = np.asarray(y, dtype=float)
    if x.size < 3 or y.size != x.size:
        raise CurveFitError("need at least 3 matching data points")

    data = DataCurve(x=x.copy(), y=y.copy())
    if ey is not None:
        try:
            data.ey = np.asarray(ey, dtype=float).copy()
        except Exception:
            pass

    fit = fit_mod.Fit(model_class=ParseModel, data=data)
    model = fit.model
    try:
        model.func = str(equation)
    except Exception as exc:
        raise CurveFitError(f"cannot parse equation: {exc}") from exc

    reserved_set = {str(r) for r in reserved}
    constant_set = {str(c) for c in constant_names}
    fixed_set = {str(f) for f in fixed}
    initial = initial or {}

    names = [n for n in getattr(model, "_keys", []) if n not in reserved_set]
    if not names:
        raise CurveFitError("equation has no free parameters")

    for p in getattr(model, "_parameters_equation", []):
        name = getattr(p, "name", None)
        if name is None or name in reserved_set:
            continue
        if name in initial:
            try:
                p.value = float(initial[name])
            except (TypeError, ValueError):
                pass
        # Constants join the fit fixed-by-default; explicit `fixed` also holds.
        p.fixed = (name in constant_set) or (name in fixed_set)

    fit.fit_range = fit_range or (0, len(x) - 1)
    return CurveFit(fit, model, reserved_set)


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
    callers that just want the result (the no-dialog / no-ChiSurf path and tests).
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
    "DataParameters",
    "ParametricCurveFit",
    "RESOLUTION_PARAMETERS",
    "build_function_fit",
    "build_function_histogram_fit",
    "CurveFitError",
    "CurveFitResult",
    "bin_centers",
    "populated_columns",
    "ridge_from_histogram",
    "ridge_from_values",
    "build_curve_fit",
    "build_marginal_fit",
    "build_histogram_fit",
    "fit_equation_to_marginal",
    "fit_equation_to_histogram",
]
