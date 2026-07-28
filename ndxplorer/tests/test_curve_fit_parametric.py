"""Fitting a *parametric* overlay curve — a FRET line — to the displayed data.

The predefined FRET lines are not ``y = f(x)``: they sweep a mean distance and
return the ``(tau, E)`` pair of arrays they trace. There is no ``ParseModel`` to
build from that, so they are optimised through the function itself, over the
parameters that are already in the curve's table.
"""
import numpy as np
import pytest

pytest.importorskip("chisurf.core.fitting.parameter", reason="ChiSurf not importable")

from ndxplorer.analysis.curve_fit import (  # noqa: E402
    CurveFitError,
    RESOLUTION_PARAMETERS,
    build_function_fit,
    build_function_histogram_fit,
)
from ndxplorer.core.curve_parameters import build_curve_group  # noqa: E402


def static_fret_line(tau_d0=4.0, offset=0.0, num_points=200):
    """``E = 1 - tau/tau_d0``, traced the way the predefined lines are."""
    num_points = int(num_points)
    tau = np.linspace(0.05, tau_d0, num_points)
    return tau, 1.0 - tau / tau_d0 + offset


def _line_histogram(tau_d0=4.0, offset=0.0, nx=40, ny=60, width=0.03, seed=0):
    """A 2-D histogram of bursts scattered around that line."""
    rng = np.random.default_rng(seed)
    x_edges = np.linspace(0.1, 3.9, nx + 1)
    y_edges = np.linspace(-0.2, 1.2, ny + 1)
    xc = 0.5 * (x_edges[:-1] + x_edges[1:])
    yc = 0.5 * (y_edges[:-1] + y_edges[1:])
    ridge = 1.0 - xc / tau_d0 + offset
    h = 300.0 * np.exp(-((yc[None, :] - ridge[:, None]) ** 2) / (2 * width ** 2))
    return rng.poisson(h).astype(float), x_edges, y_edges


def _group(**values):
    group = build_curve_group(sorted(values), values=values)
    return group, list(group.parameters_all)


def test_fit_recovers_the_lifetime_of_a_static_line():
    counts, xe, ye = _line_histogram(tau_d0=4.0)
    group, params = _group(tau_d0=2.5, offset=0.0, num_points=200)

    cf = build_function_histogram_fit(static_fret_line, params, counts, xe, ye)
    res = cf.run()

    assert res.ok, res.message
    assert res.params["tau_d0"] == pytest.approx(4.0, abs=0.1)
    # The parameters *are* the curve's own, so the table already shows the fit.
    assert group.parameters_all_dict["tau_d0"].value == pytest.approx(
        res.params["tau_d0"]
    )


def test_the_point_count_is_not_a_fitting_parameter():
    """It sets the curve's resolution; optimising it is meaningless."""
    _group_, params = _group(tau_d0=3.0, offset=0.0, num_points=200)
    cf = build_function_fit(static_fret_line, params, [1.0, 2.0, 3.0], [0.7, 0.5, 0.2])
    fixed = {p.name: bool(p.fixed) for p in cf.parameters}
    assert fixed["num_points"] is True
    assert "num_points" in RESOLUTION_PARAMETERS
    assert fixed["tau_d0"] is False


def test_a_fixed_parameter_is_held():
    counts, xe, ye = _line_histogram(tau_d0=4.0, offset=0.15)
    _group_, params = _group(tau_d0=4.0, offset=0.15, num_points=200)
    cf = build_function_histogram_fit(static_fret_line, params, counts, xe, ye)
    cf.set_fixed("offset", True)

    res = cf.run()

    assert res.ok, res.message
    assert res.params["offset"] == pytest.approx(0.15, abs=1e-9)


def test_bounds_from_the_table_constrain_the_optimiser():
    counts, xe, ye = _line_histogram(tau_d0=4.0)
    group, params = _group(tau_d0=2.5, offset=0.0, num_points=200)
    p = group.parameters_all_dict["tau_d0"]
    p.lb, p.ub, p.bounds_on = 1.0, 3.0, True   # deliberately excludes the truth

    res = build_function_histogram_fit(
        static_fret_line, params, counts, xe, ye
    ).run()

    assert res.ok, res.message
    assert res.params["tau_d0"] <= 3.0 + 1e-6  # held inside the bound


def test_all_fixed_reports_instead_of_running():
    _group_, params = _group(tau_d0=4.0, num_points=200)
    for p in params:
        p.fixed = True
    cf = build_function_fit(static_fret_line, params, [1.0, 2.0, 3.0], [0.7, 0.5, 0.2])
    res = cf.run()
    assert not res.ok and "fixed" in res.message


def test_a_curve_that_misses_the_data_still_reports():
    """The interpolation has nothing to say; it must not divide by an empty set."""
    _group_, params = _group(tau_d0=4.0, offset=0.0, num_points=200)
    # x far outside the curve's span (the curve only reaches tau = 4).
    cf = build_function_fit(static_fret_line, params,
                            [100.0, 200.0, 300.0], [0.5, 0.5, 0.5])
    res = cf.run()
    assert res.ok or res.message  # either way: a result, not an exception


def test_a_curve_without_parameters_cannot_be_fitted():
    with pytest.raises(CurveFitError):
        build_function_fit(static_fret_line, [], [1.0, 2.0, 3.0], [1.0, 2.0, 3.0])


def test_a_non_callable_is_rejected():
    _group_, params = _group(tau_d0=4.0)
    with pytest.raises(CurveFitError):
        build_function_fit("not a function", params, [1, 2, 3], [1, 2, 3])


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-q"])
