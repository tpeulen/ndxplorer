"""Fit a 1-D model ``y = f(x; params)`` to a burst-parameter marginal histogram.

An overlay curve in ndXplorer is a parameterised function of the current axis.
This module lets that curve be **fitted** to the axis's 1-D marginal histogram
(bin centres → counts) instead of being dialled in by hand: it wraps the model
equation in a ChiSurf ``ParseModel`` and runs ChiSurf's least-squares ``Fit``,
so the same safe formula that draws the overlay also drives the fit.

It is Qt-free and headless-testable. ChiSurf is imported lazily so ndXplorer
still starts (without fitting) when ChiSurf is not on the path.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Optional, Sequence, Tuple

import numpy as np


@dataclass
class MarginalFitResult:
    """Outcome of :func:`fit_equation_to_marginal`.

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


def fit_equation_to_marginal(
    equation: str,
    initial: Dict[str, float],
    x: Sequence[float],
    counts: Sequence[float],
    *,
    fixed: Sequence[str] = (),
    reserved: Sequence[str] = ("x",),
    fit_range: Optional[Tuple[int, int]] = None,
) -> MarginalFitResult:
    """Fit ``y = f(x; params)`` to a 1-D histogram via ChiSurf least-squares.

    Parameters
    ----------
    equation
        A ``ParseModel`` formula in ``x`` and named parameters, e.g.
        ``"a*exp(-(x-mu)**2/(2*sig**2))"``.
    initial
        Starting ``{name: value}`` for the parameters (missing names keep the
        model default).
    x, counts
        The marginal histogram: bin centres and their counts (equal length).
    fixed
        Names held constant during the fit.
    reserved
        Names that are not parameters (the independent variable ``x``).
    fit_range
        ``(start, stop)`` index range to fit; defaults to the whole histogram.

    Returns
    -------
    MarginalFitResult
        Fitted parameters, reduced chi-square and the fitted curve, or an error.
    """
    try:
        import chisurf.core.fitting.fit as fit_mod
        from chisurf.core.data import DataCurve
        from chisurf.core.models.parse import ParseModel
    except Exception as exc:  # pragma: no cover - depends on environment
        return MarginalFitResult(False, message=f"ChiSurf fitting is not available: {exc}")

    x = np.asarray(x, dtype=float)
    counts = np.asarray(counts, dtype=float)
    if x.size < 3 or counts.size != x.size:
        return MarginalFitResult(False, message="need at least 3 matching histogram points")

    data = DataCurve(x=x.copy(), y=counts.copy())
    # Poisson counting weights so chi-square is meaningful (floor empty bins).
    try:
        data.ey = np.sqrt(np.maximum(counts, 1.0))
    except Exception:
        pass

    fit = fit_mod.Fit(model_class=ParseModel, data=data)
    model = fit.model
    try:
        model.func = str(equation)
    except Exception as exc:
        return MarginalFitResult(False, message=f"cannot parse equation: {exc}")

    keys = list(getattr(model, "_keys", []))
    reserved_set = {str(r) for r in reserved}
    keys = [k for k in keys if k not in reserved_set]
    if not keys:
        return MarginalFitResult(False, message="equation has no free parameters")

    fixed_set = {str(f) for f in fixed}
    for k in keys:
        p = model.parameter_dict.get(k)
        if p is None:
            continue
        if k in initial:
            try:
                p.value = float(initial[k])
            except (TypeError, ValueError):
                pass
        p.fixed = k in fixed_set

    fit.fit_range = fit_range or (0, len(x) - 1)
    try:
        model.update_model()
        fit.run()
    except Exception as exc:
        return MarginalFitResult(False, message=f"fit failed: {exc}")

    # Read back from the equation's parameter objects (parameter_dict may expose
    # only the free parameters, dropping the ones we fixed).
    params: Dict[str, float] = {}
    for p in getattr(model, "_parameters_equation", []):
        name = getattr(p, "name", None)
        if name and name not in reserved_set:
            params[name] = float(p.value)
    for k in keys:  # fall back to parameter_dict for anything not seen
        if k not in params and k in model.parameter_dict:
            params[k] = float(model.parameter_dict[k].value)
    y_fit = np.asarray(model.y, dtype=float) if getattr(model, "y", None) is not None else None
    try:
        chi2r = float(fit.chi2r)
    except Exception:
        chi2r = float("nan")
    return MarginalFitResult(True, params=params, chi2r=chi2r, y_fit=y_fit)


__all__ = ["MarginalFitResult", "fit_equation_to_marginal", "bin_centers"]
