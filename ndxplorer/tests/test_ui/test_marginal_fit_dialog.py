"""The marginal-fit dialog: fitting table, constants fixed by default, fit runs."""
import os

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("chisurf.gui.autoform.sections.parameter_table",
                    reason="ChiSurf fitting table not importable")


@pytest.fixture(scope="module")
def qapp():
    from qtpy import QtWidgets

    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _marginal(mu=0.6, sig=0.08, bg=5.0, n=80, seed=0):
    x = np.linspace(0.0, 1.0, n)
    y = bg + 1000.0 * np.exp(-(x - mu) ** 2 / (2 * sig ** 2))
    return x, np.random.default_rng(seed).poisson(np.maximum(y, 0)).astype(float)


def _build(qapp, const_values):
    from ndxplorer.analysis.marginal_fit import build_marginal_fit
    from ndxplorer.ui.marginal_fit_dialog import MarginalFitDialog

    x, y = _marginal()
    mf = build_marginal_fit(
        "a*exp(-(x-mu)**2/(2*sig**2)) + Bg", x, y,
        initial={"a": 500.0, "mu": 0.5, "sig": 0.2, "Bg": 0.0},
    )
    for p in mf.parameters:
        if p.name in const_values:
            p.value = float(const_values[p.name])
            p.fixed = True
    return mf, MarginalFitDialog(None, mf, None)


def test_table_lists_every_parameter(qapp):
    mf, dlg = _build(qapp, {"Bg": 5.0})
    names = [dlg._table._model._params[i].name
             for i in range(dlg._table._model.rowCount())]
    assert names == ["a", "mu", "sig", "Bg"]


def test_constant_is_fixed_by_default(qapp):
    mf, dlg = _build(qapp, {"Bg": 5.0})
    fixed = {p.name: bool(p.fixed) for p in mf.parameters}
    assert fixed == {"a": False, "mu": False, "sig": False, "Bg": True}


def test_fit_optimizes_free_holds_fixed(qapp):
    mf, dlg = _build(qapp, {"Bg": 5.0})
    dlg._do_fit()
    v = mf.values()
    assert v["Bg"] == pytest.approx(5.0, abs=1e-6)      # held
    assert v["mu"] == pytest.approx(0.6, abs=0.03)      # optimized
    assert v["sig"] == pytest.approx(0.08, abs=0.03)


def test_freeing_a_constant_lets_it_optimize(qapp):
    mf, dlg = _build(qapp, {"Bg": 50.0})  # deliberately wrong start
    mf.set_fixed("Bg", False)
    dlg._do_fit()
    assert mf.values()["Bg"] == pytest.approx(5.0, abs=5.0)  # moved toward truth


def test_all_fixed_reports_error(qapp):
    mf, dlg = _build(qapp, {"Bg": 5.0})
    for p in mf.parameters:
        p.fixed = True
    res = mf.run()
    assert not res.ok and "fixed" in res.message


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-q"])
