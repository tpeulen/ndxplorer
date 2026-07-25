"""Fitting an overlay equation to a marginal histogram (ChiSurf least-squares)."""
import numpy as np
import pytest

from ndxplorer.analysis.marginal_fit import bin_centers, fit_equation_to_marginal

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
    from ndxplorer.analysis.marginal_fit import build_marginal_fit

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


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-q"])
