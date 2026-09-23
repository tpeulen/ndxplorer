"""The curve-fit dialog: fitting table, constants fixed by default, fit runs.

The dialog also chooses *what* the curve is fitted to — the displayed 2-D
distribution or a marginal — and switching target must rebuild the fit and the
table with it.
"""
import os

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("chisurf.gui.autoform.sections.parameter_table",
                    reason="ChiSurf fitting table not importable")

EQUATION = "a*exp(-(x-mu)**2/(2*sig**2)) + Bg"


@pytest.fixture(scope="module")
def qapp():
    from qtpy import QtWidgets

    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _marginal(mu=0.6, sig=0.08, bg=5.0, n=80, seed=0):
    x = np.linspace(0.0, 1.0, n)
    y = bg + 1000.0 * np.exp(-(x - mu) ** 2 / (2 * sig ** 2))
    return x, np.random.default_rng(seed).poisson(np.maximum(y, 0)).astype(float)


def _line_histogram(slope=0.5, intercept=0.2, nx=40, ny=60, seed=0):
    """A 2-D histogram whose ridge follows ``y = slope*x + intercept``."""
    rng = np.random.default_rng(seed)
    x_edges = np.linspace(0.0, 1.0, nx + 1)
    y_edges = np.linspace(0.0, 1.0, ny + 1)
    xc = 0.5 * (x_edges[:-1] + x_edges[1:])
    yc = 0.5 * (y_edges[:-1] + y_edges[1:])
    ridge = slope * xc + intercept
    h = 200.0 * np.exp(-((yc[None, :] - ridge[:, None]) ** 2) / (2 * 0.05 ** 2))
    return rng.poisson(h).astype(float), x_edges, y_edges


def _build(qapp, const_values, target="x"):
    """A dialog over a builder that serves both targets, as plot_main's does."""
    from ndxplorer.analysis.curve_fit import build_histogram_fit, build_marginal_fit
    from ndxplorer.ui.curve_fit_dialog import CurveFitDialog

    x, y = _marginal()
    counts, x_edges, y_edges = _line_histogram()
    initial = {"a": 500.0, "mu": 0.5, "sig": 0.2, "Bg": 0.0}

    def build(t):
        if t == "2d":
            cf = build_histogram_fit(
                EQUATION, counts, x_edges, y_edges, initial=initial,
                constant_names=list(const_values),
            )
        else:
            cf = build_marginal_fit(
                EQUATION, x, y, initial=initial, constant_names=list(const_values),
            )
        for p in cf.parameters:
            if p.name in const_values:
                p.value = float(const_values[p.name])
        return cf

    dlg = CurveFitDialog(None, build_fit=build, target=target)
    return dlg.current_fit, dlg


def test_table_lists_every_parameter(qapp):
    _cf, dlg = _build(qapp, {"Bg": 5.0})
    names = [dlg._table._model._params[i].name
             for i in range(dlg._table._model.rowCount())]
    assert names == ["a", "mu", "sig", "Bg"]


def test_constant_is_fixed_by_default(qapp):
    cf, _dlg = _build(qapp, {"Bg": 5.0})
    fixed = {p.name: bool(p.fixed) for p in cf.parameters}
    assert fixed == {"a": False, "mu": False, "sig": False, "Bg": True}


def test_fit_optimizes_free_holds_fixed(qapp):
    cf, dlg = _build(qapp, {"Bg": 5.0})
    dlg._do_fit()
    v = cf.values()
    assert v["Bg"] == pytest.approx(5.0, abs=1e-6)      # held
    assert v["mu"] == pytest.approx(0.6, abs=0.03)      # optimized
    assert v["sig"] == pytest.approx(0.08, abs=0.03)


def test_freeing_a_constant_lets_it_optimize(qapp):
    cf, dlg = _build(qapp, {"Bg": 50.0})  # deliberately wrong start
    cf.set_fixed("Bg", False)
    dlg._do_fit()
    assert cf.values()["Bg"] == pytest.approx(5.0, abs=5.0)  # moved toward truth


def test_all_fixed_reports_error(qapp):
    cf, _dlg = _build(qapp, {"Bg": 5.0})
    for p in cf.parameters:
        p.fixed = True
    res = cf.run()
    assert not res.ok and "fixed" in res.message


def test_the_default_target_is_the_displayed_data(qapp):
    """A curve is drawn over the 2-D distribution, so that is what it fits."""
    from ndxplorer.analysis.curve_fit_setup import TARGETS

    assert TARGETS[0][0] == "2d"
    _cf, dlg = _build(qapp, {}, target="2d")
    assert dlg.target == "2d"


def test_switching_target_rebuilds_the_fit(qapp):
    """Another target is another dataset — and another fit over it."""
    first, dlg = _build(qapp, {"Bg": 5.0}, target="x")
    dlg._target_combo.setCurrentIndex(dlg._target_combo.findData("2d"))
    assert dlg.target == "2d"
    assert dlg.current_fit is not None
    assert dlg.current_fit is not first
    # ...and the table follows it, rather than showing the old fit's parameters.
    shown = [dlg._table._model._params[i]
             for i in range(dlg._table._model.rowCount())]
    assert shown == dlg.current_fit.parameters


def test_a_target_with_no_data_disables_the_fit_button(qapp):
    """Say why, rather than offering a button that quietly does nothing."""
    from ndxplorer.analysis.curve_fit import CurveFitError
    from ndxplorer.ui.curve_fit_dialog import CurveFitDialog

    def build(_target):
        raise CurveFitError("no 2-D histogram to fit")

    dlg = CurveFitDialog(None, build_fit=build)
    assert dlg.current_fit is None
    assert not dlg._btn_fit.isEnabled()
    assert "no 2-D histogram" in dlg._status.text()
    dlg._do_fit()  # must not raise


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-q"])
