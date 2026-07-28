"""Fitting an overlay equation to displayed data (ChiSurf least-squares)."""
import numpy as np
import pytest

from ndxplorer.analysis.curve_fit import bin_centers, fit_equation_to_marginal

pytest.importorskip("chisurf.core.models.parse", reason="ChiSurf not importable")


def _gauss_hist(a=1000.0, mu=0.6, sig=0.08, seed=0, n=80):
    x = np.linspace(0.0, 1.0, n)
    y = a * np.exp(-(x - mu) ** 2 / (2 * sig ** 2))
    y = np.random.default_rng(seed).poisson(np.maximum(y, 0)).astype(float)
    return x, y


def test_bin_centers():
    np.testing.assert_allclose(bin_centers([0.0, 1.0, 2.0, 3.0]), [0.5, 1.5, 2.5])


def test_fit_recovers_gaussian_peak():
    x, y = _gauss_hist(mu=0.6, sig=0.08)
    res = fit_equation_to_marginal(
        "a*exp(-(x-mu)**2/(2*sig**2))",
        initial={"a": 500.0, "mu": 0.5, "sig": 0.2},
        x=x, counts=y,
    )
    assert res.ok, res.message
    assert res.params["mu"] == pytest.approx(0.6, abs=0.02)
    assert res.params["sig"] == pytest.approx(0.08, abs=0.02)
    assert res.y_fit is not None and res.y_fit.shape == x.shape
    assert np.isfinite(res.chi2r)


def test_fixed_parameter_is_held():
    x, y = _gauss_hist(mu=0.6, sig=0.08)
    res = fit_equation_to_marginal(
        "a*exp(-(x-mu)**2/(2*sig**2))",
        initial={"a": 500.0, "mu": 0.42, "sig": 0.2},
        x=x, counts=y, fixed=["mu"],
    )
    assert res.ok
    assert res.params["mu"] == pytest.approx(0.42, abs=1e-6)  # held at its start


def test_bad_equation_reports_error():
    x, y = _gauss_hist()
    res = fit_equation_to_marginal("a*exp(", {"a": 1.0}, x, y)
    assert not res.ok and res.message


def test_mismatched_lengths_error():
    res = fit_equation_to_marginal("a*x", {"a": 1.0}, [0, 1, 2], [1, 2])
    assert not res.ok


def test_no_free_parameters_error():
    x, y = _gauss_hist()
    # only x -> no free parameter to fit
    res = fit_equation_to_marginal("x*1.0", {}, x, y)
    assert not res.ok


def test_build_marginal_fit_constant_is_fixed_by_default():
    from ndxplorer.analysis.curve_fit import build_marginal_fit

    x, y = _gauss_hist()
    mf = build_marginal_fit(
        "a*exp(-(x-mu)**2/(2*sig**2)) + Bg", x, y,
        initial={"a": 500.0, "mu": 0.5, "sig": 0.2, "Bg": 5.0},
        constant_names=["Bg"],
    )
    fixed = {p.name: bool(p.fixed) for p in mf.parameters}
    assert fixed["Bg"] is True
    assert fixed["a"] is False and fixed["mu"] is False and fixed["sig"] is False
    res = mf.run()
    assert res.ok
    assert res.params["Bg"] == pytest.approx(5.0, abs=1e-6)  # held during the fit


def _line_histogram(slope=0.5, intercept=0.2, width=0.05, nx=40, ny=60, seed=0):
    """A 2-D histogram of a cloud following ``y = slope*x + intercept``."""
    rng = np.random.default_rng(seed)
    x_edges = np.linspace(0.0, 1.0, nx + 1)
    y_edges = np.linspace(0.0, 1.0, ny + 1)
    xc = 0.5 * (x_edges[:-1] + x_edges[1:])
    yc = 0.5 * (y_edges[:-1] + y_edges[1:])
    ridge = slope * xc + intercept
    h = 400.0 * np.exp(-((yc[None, :] - ridge[:, None]) ** 2) / (2 * width ** 2))
    return rng.poisson(h).astype(float), x_edges, y_edges


# -- fitting a curve to the displayed two-dimensional distribution ----------
def test_ridge_follows_the_populated_columns():
    """Each x column contributes its count-weighted mean y, and its error."""
    from ndxplorer.analysis.curve_fit import ridge_from_histogram

    counts, xe, ye = _line_histogram(slope=0.5, intercept=0.2)
    x, y, ey = ridge_from_histogram(counts, xe, ye)
    assert x.size == y.size == ey.size
    np.testing.assert_allclose(y, 0.5 * x + 0.2, atol=0.02)
    assert np.all(ey > 0)  # a weight of zero would make chi-square infinite


def test_ridge_ignores_columns_with_almost_nothing_in_them():
    """One burst in a column is noise, not a point the curve should chase."""
    from ndxplorer.analysis.curve_fit import ridge_from_histogram

    counts, xe, ye = _line_histogram()
    counts[:5] = 0.0
    counts[0, -1] = 1.0  # a single event, far off the ridge
    x, _y, _ey = ridge_from_histogram(counts, xe, ye, min_counts=3.0)
    centers = 0.5 * (xe[:-1] + xe[1:])
    assert centers[0] not in x
    assert x.size == counts.shape[0] - 5


def test_ridge_accepts_a_transposed_histogram():
    """Producers differ on (nx, ny) vs (ny, nx); the fit must not silently skew."""
    from ndxplorer.analysis.curve_fit import ridge_from_histogram

    counts, xe, ye = _line_histogram(nx=40, ny=60)
    a = ridge_from_histogram(counts, xe, ye)
    b = ridge_from_histogram(counts.T, xe, ye)
    for lhs, rhs in zip(a, b):
        np.testing.assert_allclose(lhs, rhs)


def test_ridge_rejects_a_histogram_that_does_not_match_its_edges():
    from ndxplorer.analysis.curve_fit import CurveFitError, ridge_from_histogram

    counts, xe, ye = _line_histogram(nx=40, ny=60)
    with pytest.raises(CurveFitError):
        ridge_from_histogram(counts, xe[:-5], ye)


def test_fit_recovers_a_line_through_the_displayed_data():
    """The point of it: a y(x) curve fitted to the cloud it is drawn over."""
    from ndxplorer.analysis.curve_fit import fit_equation_to_histogram

    counts, xe, ye = _line_histogram(slope=0.5, intercept=0.2)
    res = fit_equation_to_histogram(
        "m*x + b", {"m": 0.1, "b": 0.0}, counts, xe, ye,
    )
    assert res.ok, res.message
    assert res.params["m"] == pytest.approx(0.5, abs=0.03)
    assert res.params["b"] == pytest.approx(0.2, abs=0.02)


def test_fit_to_an_empty_histogram_reports_instead_of_raising():
    from ndxplorer.analysis.curve_fit import fit_equation_to_histogram

    xe = np.linspace(0, 1, 41)
    ye = np.linspace(0, 1, 61)
    res = fit_equation_to_histogram(
        "m*x + b", {"m": 1.0, "b": 0.0}, np.zeros((40, 60)), xe, ye
    )
    assert not res.ok and res.message


# -- the curve's own parameters drive the fit ------------------------------
def test_the_curves_table_decides_what_is_fitted():
    """Fix/free and bounds are set on the curve, not a second time in the fit."""
    from ndxplorer.analysis.curve_fit import build_histogram_fit
    from ndxplorer.core.curve_parameters import build_curve_group

    counts, xe, ye = _line_histogram(slope=0.5, intercept=0.2)
    group = build_curve_group(["m", "b"], values={"m": 0.1, "b": 0.35})
    group.parameters_all_dict["b"].fixed = True  # held by the user

    cf = build_histogram_fit("m*x + b", counts, xe, ye)
    cf.seed_from_group(group)
    res = cf.run()
    assert res.ok, res.message
    assert res.params["b"] == pytest.approx(0.35, abs=1e-6)  # held

    cf.write_back(group)
    assert group.parameters_all_dict["m"].value == pytest.approx(res.params["m"])


def test_a_linked_parameter_is_held_and_not_written_back():
    """A linked value belongs to its master: fitting or overwriting it is wrong."""
    from chisurf.core.fitting.parameter import FittingParameter

    from ndxplorer.analysis.curve_fit import build_histogram_fit
    from ndxplorer.core.curve_parameters import build_curve_group

    counts, xe, ye = _line_histogram(slope=0.5, intercept=0.2)
    group = build_curve_group(["m", "b"], values={"m": 0.1, "b": 0.0})
    master = FittingParameter(name="master_b", value=0.42)
    group.parameters_all_dict["b"].link = master

    cf = build_histogram_fit("m*x + b", counts, xe, ye)
    cf.seed_from_group(group)
    assert {p.name: bool(p.fixed) for p in cf.parameters}["b"] is True
    res = cf.run()
    assert res.ok, res.message
    assert res.params["b"] == pytest.approx(0.42, abs=1e-6)  # the master's value

    cf.write_back(group)
    assert group.parameters_all_dict["b"].value == pytest.approx(0.42)
    assert master.value == pytest.approx(0.42)  # the master was not moved


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-q"])
