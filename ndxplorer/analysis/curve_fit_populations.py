"""Fitting an overlay curve whose parameters differ between populations.

A curve parameter that is a **vector** (one value per population, see
:mod:`ndxplorer.core.parameters`) -- or that follows a vector constant -- makes
the curve one curve per population (:func:`~ndxplorer.core.overlay_curves.population_parameter_sets`).
Fitting such a curve is a **joint fit**:

* the data is split by the vector's population axis
  (:meth:`~ndxplorer.analysis.curve_fit_setup.FitDataReader.by_population`):
  every population sees the same displayed points, weighted by its membership
  -- 1/0 from the label column, or the burst's probability column;
* each population gets the same kind of fit the curve would get alone (cloud,
  column ridge or marginal histogram, on the displayed bins);
* the optimiser moves one vector of numbers: the **shared** parameters once,
  and each vector's **elements** once per population. The residuals of all
  populations are concatenated, so a shared parameter is fitted to every
  population at once and an element only to its own.

Held parameters (fixed, or linked) stay where they are, element by element; a
parameter linked to a vector constant supplies each population its element and
is not fitted. The result writes the elements and the shared values back
(:meth:`PopulationCurveFit.write_back`) and reports the reduced chi-square of
each population (``CurveFitResult.population_chi2r``) beside the overall one.

The nDXplorer constants that shape the *data* (``DataParameters``) are not
offered to a population-wise fit: re-deriving the data per step for every
population is a different problem (a population-wise ``gamma`` is what the FRET
calibration determines).

Toolkit-free (numpy, scipy).
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Sequence

import numpy as np

from ..core.parameters import Parameter, is_held
from .curve_fit import (
    FINITE_DIFFERENCE_STEP,
    RESOLUTION_PARAMETERS,
    CurveFit,
    CurveFitAborted,
    CurveFitError,
    CurveFitResult,
    ParametricCurveFit,
    _fit_from_best_start,
    _weighted_residual,
    bin_centers,
    ridge_from_values,
)

__all__ = ["PopulationCurveFit", "build_population_fit"]


class _Alias:
    """A curve parameter as one population's fit sees it: its name, a proxy's value."""

    def __init__(self, name: str, target: Parameter) -> None:
        self.name = name
        self.target = target

    @property
    def value(self) -> float:
        return self.target.value

    @value.setter
    def value(self, value: float) -> None:
        self.target.value = value

    @property
    def fixed(self) -> bool:
        return self.target.fixed

    @fixed.setter
    def fixed(self, value: bool) -> None:
        self.target.fixed = value


def _proxy(name: str, source: Any, held: bool) -> Parameter:
    return Parameter(name, float(source.value), fixed=bool(held), lb=float(source.lb),
                     ub=float(source.ub), bounds_on=bool(source.bounds_on))


class PopulationCurveFit:
    """One joint fit of a curve over its populations (see the module docstring).

    Parameters
    ----------
    labels : sequence of str
        The populations, in order.
    parameters : list of Parameter
        The fit's own parameters: shared ones by their name, elements as
        ``name[population]``. The dialog's table edits these.
    shared : dict
        ``name -> proxy`` of the shared parameters.
    elements : dict
        ``population -> {name: proxy}`` of the population-wise ones.
    fits : list
        One :class:`CurveFit` / :class:`ParametricCurveFit` per population, over
        aliases of the proxies.
    """

    def __init__(self, labels, parameters, shared, elements, fits) -> None:
        self.labels = [str(l) for l in labels]
        self._parameters = list(parameters)
        self._shared = dict(shared)
        self._elements = {k: dict(v) for k, v in elements.items()}
        self._fits = list(fits)
        self._progress: Optional[Callable[[int], Any]] = None
        self._steps = 0

    # -- what the dialogs use --------------------------------------------------
    @property
    def parameters(self) -> List[Parameter]:
        return self._parameters

    @property
    def data_parameters(self) -> list:
        return []

    def free_data_parameters(self) -> list:
        return []

    def attach_data_parameters(self, _data_parameters) -> None:
        """Not offered to a population-wise fit (see the module docstring)."""

    def set_progress(self, callback: Optional[Callable[[int], Any]]) -> None:
        self._progress = callback

    def values(self) -> Dict[str, float]:
        return {p.name: float(p.value) for p in self._parameters}

    def set_fixed(self, name: str, fixed: bool) -> None:
        for p in self._parameters:
            if p.name == name:
                p.fixed = bool(fixed)

    def seed_from_group(self, _group) -> None:
        """No-op: the proxies were seeded from the curve when the fit was built."""

    def write_back(self, group) -> None:
        """Write the fitted elements and shared values into the curve's parameters."""
        if group is None:
            return
        for p in group.parameters_all:
            if p.name in self._shared:
                if not p.is_linked:
                    p.value = float(self._shared[p.name].value)
                continue
            for label in self.labels:
                proxy = self._elements.get(label, {}).get(p.name)
                element = p.element(label) if p.is_vector else None
                if proxy is not None and element is not None and not element.is_linked:
                    element.value = float(proxy.value)

    # -- fitting ---------------------------------------------------------------
    @staticmethod
    def _residual_of(fit) -> np.ndarray:
        if isinstance(fit, CurveFit):
            return _weighted_residual(fit._y, fit.evaluate(), fit._ey)
        return fit._distance_residual(fit.values())

    @staticmethod
    def _points_of(fit) -> int:
        return int(np.isfinite(fit._y).sum())

    def _residuals(self, variables: Sequence[Parameter]):
        def residuals(values: np.ndarray) -> np.ndarray:
            for p, v in zip(variables, values):
                p.value = float(v)
            self._steps += 1
            if self._progress is not None and self._progress(self._steps) is False:
                raise CurveFitAborted("stopped")
            return np.concatenate([self._residual_of(f) for f in self._fits])

        return residuals

    def _free_of(self, label: str) -> int:
        own = sum(1 for p in self._elements.get(label, {}).values() if not p.fixed)
        return own + sum(1 for p in self._shared.values() if not p.fixed)

    def run(self, scan: Optional[bool] = None) -> CurveFitResult:
        """Optimise every free shared parameter and element together."""
        free = [p for p in self._parameters if not p.fixed]
        if not free:
            return CurveFitResult(False, message="all parameters are fixed")
        start = [float(p.value) for p in free]
        try:
            solution = _fit_from_best_start(free, self._residuals(free),
                                            diff_step=FINITE_DIFFERENCE_STEP, scan=bool(scan))
        except Exception as exc:  # noqa: BLE001 - reported, the start restored
            for p, v in zip(free, start):
                p.value = v
            message = "stopped" if isinstance(exc, CurveFitAborted) else f"fit failed: {exc}"
            return CurveFitResult(False, message=message)
        for p, v in zip(free, solution.x):
            p.value = float(v)
        per, total, points = {}, 0.0, 0
        for label, fit in zip(self.labels, self._fits):
            r = self._residual_of(fit)
            n = self._points_of(fit)
            cost = float(np.sum(r * r))
            per[label] = cost / max(1, n - self._free_of(label))
            total, points = total + cost, points + n
        return CurveFitResult(True, params=self.values(),
                              chi2r=total / max(1, points - len(free)),
                              population_chi2r=per)


def _vector_axis(vector):
    from ..core.vector_constants import PopulationAxis

    state = vector.vector_state() if hasattr(vector, "vector_state") else {}
    return PopulationAxis.from_dict(state)


def build_population_fit(host, curve, target: str = "2d", reduction: str = "cloud",
                         min_counts: float = 3.0) -> PopulationCurveFit:
    """The joint fit of a curve with population-wise parameters against *host*.

    The first vector's axis (label column / probability columns) splits the
    data. Raises :class:`CurveFitError` when the host cannot split its data, a
    population has too little data, or nothing is displayed.
    """
    from ..core.overlay_curves import population_labels, population_sources
    from ..utils.fast_histogram import fast_histogram_1d
    from .curve_fit_setup import cloud_for_fit, curve_tracer, histogram_on_edges, marginal_points

    group = curve.parameter_group
    sources = population_sources(group)
    labels = population_labels(group)
    read, _targets = host.fit_data_reader()
    if not hasattr(read, "by_population"):
        raise CurveFitError("this window cannot split its data by population")
    parts = read.by_population(_vector_axis(next(iter(sources.values()))), labels)

    constants = dict(host.constants) if hasattr(host.constants, "keys") else {}
    shared: Dict[str, Parameter] = {}
    elements: Dict[str, Dict[str, Parameter]] = {label: {} for label in labels}
    parameters: List[Parameter] = []
    for p in group.parameters_all:
        vector = sources.get(p.name)
        if vector is None:
            proxy = _proxy(p.name, p, is_held(p) or p.name in RESOLUTION_PARAMETERS)
            if p.name in constants:        # a curve parameter named like a constant
                proxy.value, proxy.fixed = float(constants[p.name]), True
            shared[p.name] = proxy
            parameters.append(proxy)
            continue
        own = vector is p
        for label in labels:
            element = vector.element(label)
            source = element if element is not None else vector
            proxy = _proxy(f"{p.name}[{label}]", source,
                           not own or element is None or is_held(element))
            elements[label][p.name] = proxy
            parameters.append(proxy)

    parametric = bool(getattr(curve, "is_function", False))
    equation = curve.get_equation()
    fits = []
    for label, (d1, d2, weights) in zip(labels, parts):
        aliases = [_Alias(p.name, elements[label].get(p.name) or shared[p.name])
                   for p in group.parameters_all]
        if float(np.sum(weights)) <= 0.0:
            raise CurveFitError(f"population {label} has no displayed data")
        if target == "2d":
            _h, x_edges, y_edges = host.histogram_2d()
            x_edges, y_edges = np.asarray(x_edges, float), np.asarray(y_edges, float)
            if reduction == "cloud":
                counts = histogram_on_edges(d1, d2, x_edges, y_edges, weights)
                px, py, w = cloud_for_fit(host, x_edges, y_edges, counts=counts)
                if np.count_nonzero(w) < 3:
                    raise CurveFitError(f"too little displayed data in population {label}")
                fits.append(ParametricCurveFit(
                    curve_tracer(curve, x_edges), aliases, px, py,
                    ey=np.full(py.shape, float(np.median(np.diff(y_edges)))),
                    ex=float(np.median(np.diff(x_edges))), weights=w))
                continue
            x, y, ey = ridge_from_values(d1, d2, x_edges, weights=weights, y_edges=y_edges,
                                         min_counts=min_counts, reduction=reduction)
        else:
            _centers, _counts, edges = marginal_points(*host.marginal(target))
            _e, counts = fast_histogram_1d(d1 if target == "x" else d2, edges,
                                           weights=weights, density=bool(host.density(target)))
            y = np.asarray(counts, dtype=float)
            x = bin_centers(edges) if edges.size == y.size + 1 else edges
            ey = np.sqrt(np.maximum(y, 1.0))
        if int(np.isfinite(y).sum()) < 3:
            raise CurveFitError(f"too few points to fit in population {label} (need 3)")
        if parametric:
            fits.append(ParametricCurveFit(curve.function, aliases, x, y, ey))
        else:
            fits.append(CurveFit(str(equation), x, y, ey, aliases))
    return PopulationCurveFit(labels, parameters, shared, elements, fits)
