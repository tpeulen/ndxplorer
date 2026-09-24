"""Building the fit of an overlay curve against what a window displays.

:mod:`ndxplorer.analysis.curve_fit` is the engine: given points, it fits. This
module decides *which* points -- the displayed 2-D distribution (as a cloud of
bins, or one point per column), or a marginal histogram -- and which of
nDXplorer's constants may join the fit. It used to live in the Qt window
(``plot_main.build_curve_fit_for``); now both windows call it, each through a
:class:`FitHost` that says what it displays.

A **host** provides:

``histogram_2d() -> (H, x_edges, y_edges)``
    the displayed 2-D histogram, ``H`` shaped ``(n_y, n_x)``;
``marginal(axis) -> (edges, counts)``
    a displayed 1-D histogram, edges first;
``fit_data_reader() -> (read, targets)``
    ``read()`` gives ``(x, y, weights)`` of the visible points, ``targets``
    the columns a recompute must produce (:func:`make_fit_data_reader`);
``recompute_for_constants(changed, targets=None)``
    re-derive the columns that depend on the named constants;
``density(target) -> bool``
    whether that marginal is drawn normalised;
``constants`` / ``constants_group`` / ``equations``
    the live constants, their :class:`ParameterGroup` and
    the equation list.

Toolkit-free.
"""

from __future__ import annotations

import collections.abc
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

import numpy as np

from .curve_fit import (
    RESOLUTION_PARAMETERS,
    CurveFitError,
    DataParameters,
    ParametricCurveFit,
    bin_centers,
    build_curve_fit,
    build_function_fit,
    build_marginal_fit,
    populated_columns,
    ridge_from_histogram,
    ridge_from_values,
)
from .curve_fit import _oriented as _oriented_histogram

__all__ = [
    "TARGETS",
    "REDUCTIONS",
    "FitHost",
    "read_fit_columns",
    "FitDataReader",
    "make_fit_data_reader",
    "curve_tracer",
    "histogram_on_edges",
    "cloud_for_fit",
    "marginal_points",
    "constants_shaping_data",
    "recompute_for_constants",
    "build_data_parameters",
    "build_curve_fit_for",
    "build_cloud_fit",
    "fitted_constants",
    "result_text",
]

#: What a curve can be fitted to, in the order the dialog offers them.
TARGETS: Tuple[Tuple[str, str], ...] = (
    ("2d", "Displayed data (y vs x)"),
    ("x", "X marginal histogram"),
    ("y", "Y marginal histogram"),
)

#: How a column of the displayed distribution is reduced to the point the curve
#: is fitted through.
REDUCTIONS: Tuple[Tuple[str, str], ...] = (
    ("cloud", "the cloud (every populated bin)"),
    ("population", "the population of each column"),
    ("mean", "the mean of each column"),
)


class FitHost:
    """The interface a window offers the fit builder (see the module docstring).

    A base class only for its documentation and defaults: any object with these
    attributes is a host.
    """

    constants: Mapping[str, float] = {}
    constants_group: Any = None
    equations: Sequence[Any] = ()

    def histogram_2d(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        raise NotImplementedError

    def marginal(self, axis: str) -> Tuple[np.ndarray, np.ndarray]:
        raise NotImplementedError

    def fit_data_reader(self):
        raise NotImplementedError

    def recompute_for_constants(self, changed, targets=None) -> None:
        raise NotImplementedError

    def density(self, target: str) -> bool:
        return False


# ------------------------------------------------------------------ reading
def read_fit_columns(source, x_name: str, y_name: str, weight_name: Optional[str],
                     rows: np.ndarray):
    """``(x, y, weights)`` for *rows*, from the two named columns only.

    Pairs where either value is not finite are dropped: a recompute can turn a
    value into nan (a background subtraction crossing zero, say).
    """
    d1 = source.column_values(x_name)
    d2 = source.column_values(y_name)
    if d1 is None or d2 is None:
        return np.empty(0), np.empty(0), None
    d1, d2 = d1[rows], d2[rows]
    weights = None
    if weight_name:
        column = source.column_values(weight_name)
        if column is not None:
            weights = column[rows]
    good = np.isfinite(d1) & np.isfinite(d2)
    if not good.all():
        d1, d2 = d1[good], d2[good]
        weights = None if weights is None else weights[good]
    return d1, d2, weights


class FitDataReader:
    """The plotted values of a frozen set of rows: what a curve fit reads.

    Calling it gives ``(x, y, weights)`` (:func:`read_fit_columns`);
    :meth:`by_population` splits the same points by a vector's population axis.
    """

    def __init__(self, source, rows, x_name: str, y_name: str,
                 weight_name: Optional[str] = None) -> None:
        self.source = source
        self.rows = np.asarray(rows)
        self.x_name, self.y_name, self.weight_name = x_name, y_name, weight_name

    def __call__(self):
        return read_fit_columns(self.source, self.x_name, self.y_name, self.weight_name,
                                self.rows)

    def by_population(self, axis, labels: Sequence[str]):
        """``[(x, y, weights)]``, one per population of *axis* (a ``PopulationAxis``).

        A burst's weight in population *k* is its probability column when the
        axis names one for every label and the data has them all, else 1 where
        the label column holds the population's code and 0 elsewhere; the
        display's weight column multiplies in. Every population gets the same
        points, so only the weights differ.

        Raises
        ------
        CurveFitError
            The data has no column to tell the populations apart by.
        """
        source, rows = self.source, self.rows
        d1, d2 = source.column_values(self.x_name), source.column_values(self.y_name)
        if d1 is None or d2 is None:
            return [(np.empty(0), np.empty(0), np.empty(0)) for _ in labels]
        d1, d2 = d1[rows], d2[rows]
        good = np.isfinite(d1) & np.isfinite(d2)
        base = np.ones(int(good.sum()))
        if self.weight_name:
            column = source.column_values(self.weight_name)
            if column is not None:
                base = np.asarray(column[rows][good], dtype=float)

        def column_of(name):
            values = source.column_values(name) if name else None
            return None if values is None else np.asarray(values[rows][good], dtype=float)

        probs = dict(getattr(axis, "probabilities", {}) or {})
        members = None
        if probs and all(label in probs for label in labels):
            stack = [column_of(probs[label]) for label in labels]
            if all(p is not None for p in stack):
                members = [np.nan_to_num(p, nan=0.0) for p in stack]
        if members is None:
            codes = column_of(axis.column)
            if codes is None:
                raise CurveFitError(f"the data has no population column '{axis.column}' "
                                    "to fit the populations by")
            members = [(codes == axis.code_of(label, i)).astype(float)
                       for i, label in enumerate(labels)]
        return [(d1[good], d2[good], base * m) for m in members]


def make_fit_data_reader(source, rows, x_name: str, y_name: str,
                         weight_name: Optional[str] = None):
    """Freeze how a fit reads the plotted values, and what it recomputes.

    Returns ``(read, targets)``: *read* a :class:`FitDataReader`. The gate is
    **frozen** to *rows* -- re-deriving it per step would cost a full mask and
    let the fitted population change under the fit -- and only the two plotted
    columns are read.
    """
    targets = [n for n in (x_name, y_name) if n]
    return FitDataReader(source, rows, x_name, y_name, weight_name), targets


def histogram_on_edges(d1, d2, x_edges, y_edges, weights=None) -> np.ndarray:
    """Bin values on given edges, x-first ``(nx, ny)``."""
    from ..utils.fast_histogram import fast_histogram_2d

    counts, _, _ = fast_histogram_2d(
        np.asarray(d1, dtype=float), np.asarray(d2, dtype=float),
        [np.asarray(x_edges, dtype=float), np.asarray(y_edges, dtype=float)],
        weights=weights,
    )
    return np.asarray(counts, dtype=float)


def cloud_for_fit(host, x_edges, y_edges, values=None, counts=None):
    """The displayed distribution as weighted points: one per **bin**.

    Every bin is returned, empty ones with weight zero, so the point set does
    not change while a fitted constant slides the population between bins.
    """
    if counts is None:
        if values is None:
            read, _ = host.fit_data_reader()
            values = read()
        d1, d2, weights = values
        counts = histogram_on_edges(d1, d2, x_edges, y_edges, weights)
    counts = np.asarray(counts, dtype=float)
    xc = bin_centers(x_edges)
    yc = bin_centers(y_edges)
    gx, gy = np.meshgrid(xc, yc, indexing="ij")
    return gx.ravel(), gy.ravel(), counts.ravel()


def marginal_points(edges, counts):
    """``(centers, counts, edges)`` of a 1-D histogram handed back edges first."""
    edges = np.asarray(edges, dtype=float)
    counts = np.asarray(counts, dtype=float)
    centers = bin_centers(edges) if edges.size == counts.size + 1 else edges
    return centers, counts, edges


# ---------------------------------------------------------------- constants
def constants_shaping_data(group, equations) -> List[Any]:
    """The constants the equations actually read, as live parameters.

    Equations name a constant quoted -- ``'gG/gR'`` -- which is what makes this
    an exact match rather than a substring hunt. A constant no equation reads
    cannot move the data and would only add a flat direction to the fit.
    """
    if group is None:
        return []
    blob = []
    for equation in (equations or []):
        if isinstance(equation, dict):
            for key, expression in equation.items():
                blob.append(f"{key} {expression}")
        else:
            blob.append(str(equation))
    text = " ".join(blob)
    return [p for p in group.parameters_all if f"'{p.name}'" in text]


def recompute_for_constants(source, constants, equations, changed,
                            targets=None) -> None:
    """Re-derive the columns that depend on the named constants.

    *targets* narrows that to the columns those names need -- inside a fit, the
    two plotted axes; one constant can feed forty derived columns.
    """
    changed = {str(c) for c in changed}
    source.compute_columns(constants=constants, equations=equations,
                           changed_constants=changed or None, targets=targets)


def build_data_parameters(host, target, x_edges, y_edges=None, keep=None,
                          min_counts=3.0, reduction="cloud") -> Optional[DataParameters]:
    """Offer the data-shaping constants to a curve fit (fixed until freed).

    Returns ``None`` when there are none (no parameter group, or no equation
    reads a constant).
    """
    from ..utils.fast_histogram import fast_histogram_1d

    parameters = constants_shaping_data(host.constants_group, host.equations)
    if not parameters:
        return None
    read, targets = host.fit_data_reader()
    edges = np.asarray(x_edges, dtype=float)
    density = bool(host.density(target))

    def refresh(changed):
        host.recompute_for_constants(changed, targets=targets)
        values = read()
        d1, d2, weights = values
        if target == "2d" and reduction == "cloud":
            px, py, w = cloud_for_fit(host, edges, y_edges, values)
            return px, py, np.full(py.shape, float(np.median(np.diff(y_edges)))), w
        if target == "2d":
            return ridge_from_values(d1, d2, edges, weights=weights, y_edges=y_edges,
                                     keep=keep, min_counts=min_counts, reduction=reduction)
        _, counts = fast_histogram_1d(d1 if target == "x" else d2, edges, weights=weights,
                                      density=density)
        counts = np.asarray(counts, dtype=float)
        centers = bin_centers(edges) if edges.size == counts.size + 1 else edges
        return centers, counts, np.sqrt(np.maximum(counts, 1.0))

    return DataParameters(parameters=parameters, refresh=refresh)


# ---------------------------------------------------------------- the fit
def build_curve_fit_for(host, curve, target="2d", reduction="cloud", min_counts=3.0):
    """Build the fit of *curve* against what *host* displays.

    Parameters
    ----------
    host : FitHost
    curve : object
        An overlay curve: ``get_equation()``, ``get_parameters()``,
        ``parameter_group``, ``is_function``, ``function``,
        ``curve_evaluator`` (:class:`~ndxplorer.core.overlay_curves.OverlayCurve`,
        or the Qt window's curve widget). Its group seeds value, bounds and
        fix/free, so those are set in one place.
    target : {'2d', 'x', 'y'}
        The displayed 2-D distribution, or that axis's marginal.
    reduction : {'cloud', 'population', 'mean'}
        For ``'2d'``: fit through every populated bin, or through one point per
        column (the densest population's centre, or the column average).
    min_counts : float
        Minimum events for a column to be fitted.

    Returns
    -------
    CurveFit or ParametricCurveFit
        With nDXplorer's data-shaping constants attached, fixed.

    Raises
    ------
    CurveFitError
        If the curve cannot be fitted, or nothing is displayed to fit it to.
    """
    equation = curve.get_equation()
    parametric = bool(getattr(curve, "is_function", False))
    if not parametric and (not isinstance(equation, str) or not equation.strip()):
        raise CurveFitError("curve has no equation to fit")
    from ..core.overlay_curves import population_labels

    group = getattr(curve, "parameter_group", None)
    if group is not None and population_labels(group):
        # A population-wise parameter: one joint fit over the populations.
        from .curve_fit_populations import build_population_fit

        return build_population_fit(host, curve, target, reduction, min_counts)
    initial = dict(curve.get_parameters())
    constants = host.constants
    # A live Mapping over the parameter group, not a dict.
    const_values = dict(constants) if isinstance(constants, collections.abc.Mapping) else {}
    text = equation if isinstance(equation, str) else ""
    constant_names = [k for k in const_values if k in text]
    for name in constant_names:
        try:
            initial[name] = float(const_values[name])
        except (TypeError, ValueError):
            pass

    group = getattr(curve, "parameter_group", None)
    params = None
    if parametric:
        if group is None:
            raise CurveFitError("the curve has no parameters to fit")
        params = list(group.parameters_all)

    if target == "2d":
        try:
            counts, x_edges, y_edges = host.histogram_2d()
        except CurveFitError:
            raise
        except Exception as exc:  # noqa: BLE001
            raise CurveFitError(f"no 2-D histogram displayed ({exc})") from exc
        keep = populated_columns(counts, x_edges, y_edges, min_counts=min_counts)
        if reduction == "cloud":
            cf = build_cloud_fit(host, curve, x_edges, y_edges, params,
                                 counts=_oriented_histogram(counts, x_edges, y_edges)[0])
        else:
            if int(keep.sum()) < 3:
                raise CurveFitError("too few populated columns to fit (need 3)")
            x, y, ey = ridge_from_histogram(counts, x_edges, y_edges, keep=keep,
                                            reduction=reduction)
            if parametric:
                cf = build_function_fit(curve.function, params, x, y, ey)
            else:
                cf = build_curve_fit(equation, x, y, ey, initial=initial,
                                     constant_names=constant_names)
        data_parameters = build_data_parameters(host, "2d", x_edges, y_edges, keep=keep,
                                                min_counts=min_counts, reduction=reduction)
    else:
        try:
            centers, counts, edges = marginal_points(*host.marginal(target))
        except Exception as exc:  # noqa: BLE001
            raise CurveFitError(f"no {target} histogram displayed ({exc})") from exc
        if parametric:
            cf = build_function_fit(curve.function, params, centers, counts)
        else:
            cf = build_marginal_fit(equation, centers, counts, initial=initial,
                                    constant_names=constant_names)
        data_parameters = build_data_parameters(host, target, edges)
    cf.attach_data_parameters(data_parameters)
    if not parametric:
        # The curve's own table has the last word on fix/free and bounds.
        cf.seed_from_group(group)
        for p in cf.parameters:
            if p.name in const_values:
                p.fixed = True
    return cf


def build_cloud_fit(host, curve, x_edges, y_edges, params=None, counts=None):
    """A fit of *curve* against every occupied bin of the displayed distribution.

    An equation curve is *traced* on a dense grid over the displayed x range, so
    both kinds of curve are compared with the cloud the same way: by distance,
    in displayed bins.
    """
    group = getattr(curve, "parameter_group", None)
    if group is None:
        raise CurveFitError("the curve has no parameters to fit")
    parameters = list(params) if params is not None else list(group.parameters_all)
    px, py, weights = cloud_for_fit(host, x_edges, y_edges, counts=counts)
    if float(np.count_nonzero(weights)) < 3:
        raise CurveFitError("too little displayed data to fit")
    x_edges = np.asarray(x_edges, dtype=float)
    y_edges = np.asarray(y_edges, dtype=float)
    x_bin = float(np.median(np.diff(x_edges)))
    y_bin = float(np.median(np.diff(y_edges)))

    function = curve_tracer(curve, x_edges)
    for p in parameters:
        if p.name in RESOLUTION_PARAMETERS:
            p.fixed = True
    return ParametricCurveFit(function, parameters, px, py, ey=np.full(py.shape, y_bin),
                              ex=x_bin, weights=weights)


def curve_tracer(curve, x_edges):
    """``f(**values) -> (x, y)``: the curve as a traced line over the displayed x range.

    A function curve traces itself; an equation is evaluated on a dense grid,
    so both kinds are compared with a cloud the same way (by distance).
    """
    function = curve.function if getattr(curve, "is_function", False) else None
    if function is not None:
        return function
    equation = curve.get_equation()
    evaluator = curve.curve_evaluator
    grid = np.linspace(float(x_edges[0]), float(x_edges[-1]), 400)

    def trace(**values):
        with np.errstate(all="ignore"):
            y = evaluator.evaluate(equation, grid, values)
        if isinstance(y, tuple):
            return y
        y = np.asarray(y, dtype=float)
        return grid, (np.full(grid.shape, float(y)) if y.ndim == 0 else y)

    return trace


def fitted_constants(group, params: Mapping[str, float]) -> Set[str]:
    """Write fitted curve parameters that name a constant into the constants.

    Returns the names written; the caller recomputes what they feed.
    """
    if group is None:
        return set()
    pdict = group.parameters_all_dict
    changed = set()
    for name, value in params.items():
        p = pdict.get(name)
        if p is not None:
            p.value = float(value)
            changed.add(name)
    return changed


def result_text(result) -> Tuple[str, bool]:
    """The dialog's status line for a fit result, and whether it is an error."""
    if result.ok:
        fitted = dict(result.params)
        fitted.update(result.data_params)
        per = dict(getattr(result, "population_chi2r", None) or {})
        pops = ("   ·   " + ", ".join(f"χ²ᵣ[{k}]={v:.4g}" for k, v in per.items())) if per else ""
        return (f"reduced χ² = {result.chi2r:.4g}{pops}   ·   "
                + ", ".join(f"{k}={v:.4g}" for k, v in fitted.items())), False
    return (result.message or "fit failed"), True
