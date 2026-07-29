"""Fitting nDXplorer constants: parameters that move the data, not the curve.

A constant feeds the equations that build the plotted axes, so freeing one and
fitting it moves the burst population under the curve — the way a detection
correction factor is read off a static FRET line. The fit re-derives the data at
every step through :attr:`DataParameters.refresh`.
"""
import numpy as np
import pytest

from ndxplorer.analysis.curve_fit import (
    DataParameters,
    ParametricCurveFit,
    build_curve_fit,
    ridge_from_histogram,
)

pytest.importorskip("chisurf.core.models.parse", reason="ChiSurf not importable")

from chisurf.core.fitting.parameter import FittingParameter  # noqa: E402


X = np.linspace(0.0, 1.0, 40)
#: What the detector measured; the plotted axis is this divided by the constant.
Y_RAW = 2.0 * (0.5 * X + 0.1)
GAMMA_TRUE = 2.0


def _data_parameters(gamma, seen=None):
    """A constant that scales the plotted y axis, with its recompute."""

    def refresh(changed):
        if seen is not None:
            seen.append(list(changed))
        y = Y_RAW / float(gamma.value)
        return X, y, np.full(X.shape, 0.01)

    return DataParameters(parameters=[gamma], refresh=refresh)


def test_a_freed_constant_is_fitted_through_the_data():
    """The curve is fixed; the constant moves the data onto it."""
    gamma = FittingParameter(name="gG/gR", value=1.0, fixed=False)
    cf = build_curve_fit("m*x + b", X, Y_RAW / 1.0, initial={"m": 0.5, "b": 0.1})
    for p in cf.parameters:
        p.fixed = True
    cf.attach_data_parameters(_data_parameters(gamma))

    result = cf.run()

    assert result.ok, result.message
    assert gamma.value == pytest.approx(GAMMA_TRUE, abs=1e-3)
    assert result.data_params["gG/gR"] == pytest.approx(GAMMA_TRUE, abs=1e-3)


def test_curve_and_constant_are_fitted_together():
    """One optimisation over both vectors: the line's slope and the constant.

    Scaling the data trades off against the slope, so the intercept is what
    pins the constant down — held at the value the data has at ``gamma = 1``.
    """
    gamma = FittingParameter(name="gG/gR", value=1.2, fixed=False)
    cf = build_curve_fit("m*x + b", X, Y_RAW, initial={"m": 0.2, "b": 0.2})
    for p in cf.parameters:
        p.fixed = p.name == "b"
    cf.attach_data_parameters(_data_parameters(gamma))

    result = cf.run()

    assert result.ok, result.message
    assert gamma.value == pytest.approx(1.0, abs=1e-3)
    assert result.params["m"] == pytest.approx(1.0, abs=1e-3)


def test_a_fixed_constant_is_left_alone():
    """Constants arrive fixed; an untouched one must not be optimised."""
    gamma = FittingParameter(name="gG/gR", value=1.0, fixed=True)
    seen = []
    cf = build_curve_fit("m*x + b", X, Y_RAW, initial={"m": 0.5, "b": 0.1})
    cf.attach_data_parameters(_data_parameters(gamma, seen))

    result = cf.run()

    assert result.ok, result.message
    assert gamma.value == 1.0
    assert seen == []  # the data was never re-derived
    assert result.data_params == {}


def test_only_the_freed_constants_are_named_to_the_recompute():
    """``refresh`` is told what moved, so only those columns are recomputed."""
    gamma = FittingParameter(name="gG/gR", value=1.0, fixed=False)
    seen = []
    cf = build_curve_fit("m*x + b", X, Y_RAW, initial={"m": 0.5, "b": 0.1})
    for p in cf.parameters:
        p.fixed = True
    cf.attach_data_parameters(_data_parameters(gamma, seen))

    cf.run()

    assert seen and all(names == ["gG/gR"] for names in seen)


def test_a_parametric_curve_also_fits_a_constant():
    """The same for a traced (x, y) curve — the FRET lines."""

    def line(slope=0.5, num_points=40):
        x = np.linspace(0.0, 1.0, int(num_points))
        return x, slope * x + 0.1

    slope = FittingParameter(name="slope", value=0.5, fixed=True)
    points = FittingParameter(name="num_points", value=40, fixed=True)
    gamma = FittingParameter(name="gG/gR", value=1.0, fixed=False)

    fit = ParametricCurveFit(line, [slope, points], X, Y_RAW, np.full(X.shape, 0.01))
    fit.attach_data_parameters(_data_parameters(gamma))

    result = fit.run()

    assert result.ok, result.message
    assert gamma.value == pytest.approx(GAMMA_TRUE, abs=1e-3)


def test_everything_fixed_is_not_a_fit():
    gamma = FittingParameter(name="gG/gR", value=1.0, fixed=True)
    cf = build_curve_fit("m*x + b", X, Y_RAW, initial={"m": 0.5, "b": 0.1})
    for p in cf.parameters:
        p.fixed = True
    cf.attach_data_parameters(_data_parameters(gamma))

    assert not cf.run().ok


def test_the_reduction_is_smooth_in_the_data():
    """The trap: a binned column mean is a staircase, and has no derivative.

    The finite-difference step the optimiser takes is small. If the reduction
    only moves when a burst crosses a y bin edge, the Jacobian comes back
    exactly zero and the fit returns instantly without having moved anything.
    """
    from ndxplorer.analysis.curve_fit import ridge_from_values

    rng = np.random.default_rng(0)
    x = rng.uniform(0.0, 1.0, 2000)
    y = 0.5 * x + 0.2
    x_edges = np.linspace(0.0, 1.0, 11)
    y_edges = np.linspace(0.0, 1.0, 21)
    eps = 1e-6

    _, y0, _ = ridge_from_values(x, y, x_edges, y_edges=y_edges)
    _, y1, _ = ridge_from_values(x, y + eps, x_edges, y_edges=y_edges)

    np.testing.assert_allclose(y1 - y0, eps, rtol=1e-6)


def test_the_fit_reports_its_steps():
    """It takes seconds, so the caller gets a heartbeat to show."""
    gamma = FittingParameter(name="gG/gR", value=1.0, fixed=False)
    steps = []
    cf = build_curve_fit("m*x + b", X, Y_RAW, initial={"m": 0.5, "b": 0.1})
    for p in cf.parameters:
        p.fixed = True
    cf.attach_data_parameters(_data_parameters(gamma))
    cf.set_progress(steps.append)

    assert cf.run().ok
    assert steps == list(range(1, len(steps) + 1))


def test_a_stopped_fit_puts_everything_back():
    """Returning False from the progress callback aborts, without side effects."""
    gamma = FittingParameter(name="gG/gR", value=1.0, fixed=False)
    refreshed = []
    cf = build_curve_fit("m*x + b", X, Y_RAW, initial={"m": 0.5, "b": 0.1})
    for p in cf.parameters:
        p.fixed = True
    cf.attach_data_parameters(_data_parameters(gamma, refreshed))
    cf.set_progress(lambda step: step < 3)

    result = cf.run()

    assert not result.ok and result.message == "stopped"
    assert gamma.value == 1.0          # back where it started
    assert refreshed                   # and the data was put back with it


def test_forced_columns_keep_the_residual_length():
    """A column that empties comes back as nan, not as a shorter array."""
    counts = np.zeros((5, 4))
    counts[1:4, 1] = 10.0  # three populated columns (x-first, then transposed)
    x_edges = np.linspace(0.0, 1.0, 6)
    y_edges = np.linspace(0.0, 1.0, 5)
    keep = np.array([False, True, True, True, False])

    x, y, ey = ridge_from_histogram(counts.T, x_edges, y_edges, keep=keep)
    assert x.size == y.size == ey.size == 3
    assert np.isfinite(y).all()

    counts[2, 1] = 0.0  # the middle column ran empty
    x2, y2, _ = ridge_from_histogram(counts.T, x_edges, y_edges, keep=keep)
    assert x2.size == 3
    assert np.isnan(y2[1]) and np.isfinite(y2[[0, 2]]).all()
