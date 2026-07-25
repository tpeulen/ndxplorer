"""Fit a 1-D model ``y = f(x; params)`` to a burst-parameter marginal histogram.

An overlay curve in ndXplorer is a parameterised function of the current axis.
This module lets that curve be **fitted** to the axis's 1-D marginal histogram
(bin centres → counts): it wraps the model equation in a ChiSurf ``ParseModel``
and runs ChiSurf's least-squares ``Fit``, so the same safe formula that draws the
overlay also drives the fit.

The model's parameters *are* the fitting group. When ChiSurf is present they are
rendered in the fitting-parameter table (fix/free/bounds per parameter); the fit
optimises every **free** parameter and holds the **fixed** ones. Parameters that
name an ndXplorer constant are seeded from the constant table and **fixed by
default** — free them to fit them.

:class:`MarginalFit` is the persistent handle the GUI dialog drives (build once,
edit fix/free, ``run`` repeatedly). :func:`fit_equation_to_marginal` is the
one-shot convenience used by the no-dialog / no-ChiSurf path and the tests.

Qt-free and headless-testable; ChiSurf is imported lazily.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np


class MarginalFitError(RuntimeError):
    """Raised when a marginal-fit model cannot be built (bad equation, no params)."""


@dataclass
class MarginalFitResult:
    """Outcome of a marginal fit.

    Attributes
    ----------
    ok
        True when the fit ran and produced parameters.
    params
        Fitted ``{name: value}`` for every free/fixed model parameter.
    chi2r
        Reduced chi-square of the fit (``nan`` on failure).
    y_fit
        The fitted model evaluated at the input bin centres (for redraw/preview).
    message
        A short reason when ``ok`` is False.
    """

    ok: bool
    params: Dict[str, float] = field(default_factory=dict)
    chi2r: float = float("nan")
    y_fit: Optional[np.ndarray] = None
    message: Optional[str] = None

    def __bool__(self) -> bool:  # noqa: D105
        return self.ok


def bin_centers(edges: Sequence[float]) -> np.ndarray:
    """Return bin centres from an array of ``n+1`` bin edges."""
    e = np.asarray(edges, dtype=float)
    return 0.5 * (e[:-1] + e[1:])


class MarginalFit:
    """A built ChiSurf ``ParseModel`` fit of an equation to a marginal histogram.

    Build it with :func:`build_marginal_fit`, edit the parameters' fix/free/bounds
    (directly or through the fitting table), then call :meth:`run` — as often as
    you like. The parameters returned by :attr:`parameters` are the live
    ``FittingParameter`` objects, suitable for a ``ParameterGroupTableWidget``.
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

    def run(self) -> MarginalFitResult:
        """Optimise every free parameter (holding the fixed ones); return the result."""
        free = [p for p in self.parameters if not getattr(p, "fixed", False)]
        if not free:
            return MarginalFitResult(False, message="all parameters are fixed")
        try:
            self._model.update_model()
            self._fit.run()
        except Exception as exc:
            return MarginalFitResult(False, message=f"fit failed: {exc}")
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
        return MarginalFitResult(True, params=params, chi2r=chi2r, y_fit=y_fit)


def build_marginal_fit(
    equation: str,
    x: Sequence[float],
    counts: Sequence[float],
    *,
    initial: Optional[Dict[str, float]] = None,
    constant_names: Sequence[str] = (),
    fixed: Sequence[str] = (),
    reserved: Sequence[str] = ("x",),
    fit_range: Optional[Tuple[int, int]] = None,
) -> MarginalFit:
    """Build a :class:`MarginalFit` for ``equation`` over a marginal histogram.

    Parameters
    ----------
    equation
        A ``ParseModel`` formula in ``x`` and named parameters.
    x, counts
        The marginal histogram: bin centres and their counts (equal length).
    initial
        Starting ``{name: value}`` for the parameters.
    constant_names
        Parameter names that are ndXplorer constants — **fixed by default**
        (seed their value via ``initial``).
    fixed
        Additional names to hold fixed.
    reserved
        Names that are not parameters (the independent variable ``x``).
    fit_range
        ``(start, stop)`` index range to fit; defaults to the whole histogram.

    Raises
    ------
    MarginalFitError
        If ChiSurf is unavailable, the histogram is too small, the equation does
        not parse, or it has no free parameters.
    """
    try:
        import chisurf.core.fitting.fit as fit_mod
        from chisurf.core.data import DataCurve
        from chisurf.core.models.parse import ParseModel
    except Exception as exc:  # pragma: no cover - depends on environment
        raise MarginalFitError(f"ChiSurf fitting is not available: {exc}") from exc

    x = np.asarray(x, dtype=float)
    counts = np.asarray(counts, dtype=float)
    if x.size < 3 or counts.size != x.size:
        raise MarginalFitError("need at least 3 matching histogram points")

    data = DataCurve(x=x.copy(), y=counts.copy())
    try:  # Poisson counting weights so chi-square is meaningful (floor empty bins)
        data.ey = np.sqrt(np.maximum(counts, 1.0))
    except Exception:
        pass

    fit = fit_mod.Fit(model_class=ParseModel, data=data)
    model = fit.model
    try:
        model.func = str(equation)
    except Exception as exc:
        raise MarginalFitError(f"cannot parse equation: {exc}") from exc

    reserved_set = {str(r) for r in reserved}
    constant_set = {str(c) for c in constant_names}
    fixed_set = {str(f) for f in fixed}
    initial = initial or {}

    names = [n for n in getattr(model, "_keys", []) if n not in reserved_set]
    if not names:
        raise MarginalFitError("equation has no free parameters")

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
    return MarginalFit(fit, model, reserved_set)


def fit_equation_to_marginal(
    equation: str,
    initial: Dict[str, float],
    x: Sequence[float],
    counts: Sequence[float],
    *,
    fixed: Sequence[str] = (),
    constant_names: Sequence[str] = (),
    reserved: Sequence[str] = ("x",),
    fit_range: Optional[Tuple[int, int]] = None,
) -> MarginalFitResult:
    """One-shot fit of ``y = f(x; params)`` to a 1-D histogram (never raises).

    A thin wrapper over :func:`build_marginal_fit` + :meth:`MarginalFit.run` for
    callers that just want the result (the no-dialog / no-ChiSurf path and tests).
    """
    try:
        mf = build_marginal_fit(
            equation, x, counts, initial=initial, fixed=fixed,
            constant_names=constant_names, reserved=reserved, fit_range=fit_range,
        )
    except MarginalFitError as exc:
        return MarginalFitResult(False, message=str(exc))
    return mf.run()


__all__ = [
    "MarginalFit",
    "MarginalFitError",
    "MarginalFitResult",
    "build_marginal_fit",
    "fit_equation_to_marginal",
    "bin_centers",
]
