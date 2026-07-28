"""The overlay 'Fit' button fits a curve's parameters to the displayed data.

Its parameters are a chisurf fitting-parameter group, so what the table says —
values, fix/free, and any crosslink — is what the fit uses, and the fitted
values land back in the same table.
"""
import os

import numpy as np
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("chisurf.core.models.parse", reason="ChiSurf not importable")


@pytest.fixture(scope="module")
def qapp():
    from qtpy import QtWidgets

    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _gauss_marginal(mu=0.6, sig=0.08, n=80, seed=0):
    xc = np.linspace(0.0, 1.0, n)
    y = 1000.0 * np.exp(-(xc - mu) ** 2 / (2 * sig ** 2))
    y = np.random.default_rng(seed).poisson(np.maximum(y, 0)).astype(float)
    edges = np.linspace(0.0, 1.0, n + 1)
    return y, edges


def _line_histogram(slope=0.5, intercept=0.2, nx=40, ny=60, seed=0):
    """A displayed 2-D distribution whose ridge is ``y = slope*x + intercept``."""
    rng = np.random.default_rng(seed)
    x_edges = np.linspace(0.0, 1.0, nx + 1)
    y_edges = np.linspace(0.0, 1.0, ny + 1)
    xc = 0.5 * (x_edges[:-1] + x_edges[1:])
    yc = 0.5 * (y_edges[:-1] + y_edges[1:])
    ridge = slope * xc + intercept
    h = 400.0 * np.exp(-((yc[None, :] - ridge[:, None]) ** 2) / (2 * 0.05 ** 2))
    return rng.poisson(h).astype(float), x_edges, y_edges


def _patch_histograms(monkeypatch, marginal=None, histogram2d=None):
    """Serve both what the 2-D plot shows and what the marginals show."""
    import ndxplorer.plotting.histograms as H

    marginal = marginal if marginal is not None else _gauss_marginal()
    histogram2d = histogram2d if histogram2d is not None else _line_histogram()
    counts, xe, ye = histogram2d
    y_marg, edges_marg = marginal

    def _plot_histogram(nd, dim="2d", **kwargs):
        if dim == "2d":
            return counts, (xe, ye)
        return y_marg, edges_marg

    monkeypatch.setattr(H, "plot_histogram", _plot_histogram)


def _autofit_dialog(monkeypatch, target="2d"):
    """The handler opens a modal dialog; run its fit instead of blocking."""
    import ndxplorer.ui.curve_fit_dialog as D

    def _exec(self):
        index = self._target_combo.findData(target)
        if index >= 0:
            self._target_combo.setCurrentIndex(index)
        self._do_fit()
        return 1

    monkeypatch.setattr(D.CurveFitDialog, "exec_", _exec)


def test_overlay_has_fit_button(qapp):
    from ndxplorer.plotting.curve_overlay import CurveWidget

    cw = CurveWidget(name="c", equation_or_function="a*x+b", is_function=False)
    assert cw.fit_button.text() == "🎯 Fit"


def test_function_names_are_not_parameters(qapp):
    from ndxplorer.plotting.curve_overlay import CurveWidget

    cw = CurveWidget(name="c", equation_or_function="a*exp(-(x-mu)**2/(2*sig**2))",
                     is_function=False)
    assert set(cw.get_parameters().keys()) == {"a", "mu", "sig"}  # no 'exp'/'x'


def test_fit_button_fits_the_curve_to_the_displayed_data(qapp, monkeypatch):
    """The point of it: a y(x) curve fitted to the cloud it is drawn over."""
    from ndxplorer.core.plot_main import NDXplorer

    _patch_histograms(monkeypatch, histogram2d=_line_histogram(slope=0.5, intercept=0.2))
    _autofit_dialog(monkeypatch, target="2d")

    ndx = NDXplorer()
    cw = ndx.curve_overlay_widget.add_curve("m*x + b")
    cw.set_parameters({"m": 0.1, "b": 0.0}, {"m": [-5, 5], "b": [-5, 5]})

    ndx.on_fit_curve_to_data(cw)

    p = cw.get_parameters()
    assert p["m"] == pytest.approx(0.5, abs=0.05)
    assert p["b"] == pytest.approx(0.2, abs=0.03)


def test_fit_button_still_fits_a_marginal_when_asked(qapp, monkeypatch):
    """A curve that is a *distribution* of one axis fits that axis's histogram."""
    from ndxplorer.core.plot_main import NDXplorer

    _patch_histograms(monkeypatch, marginal=_gauss_marginal(mu=0.6, sig=0.08))
    _autofit_dialog(monkeypatch, target="x")

    ndx = NDXplorer()
    cw = ndx.curve_overlay_widget.add_curve("a*exp(-(x-mu)**2/(2*sig**2))")
    cw.set_parameters({"a": 500.0, "mu": 0.4, "sig": 0.2},
                      {"a": [0, 5000], "mu": [0, 1], "sig": [0, 1]})

    ndx.on_fit_curve_to_data(cw)

    p = cw.get_parameters()
    assert p["mu"] == pytest.approx(0.6, abs=0.03)
    assert p["sig"] == pytest.approx(0.08, abs=0.03)


def test_a_parameter_fixed_in_the_curves_table_is_held_by_the_fit(qapp, monkeypatch):
    """One place to fix a parameter — the table the user is looking at."""
    from ndxplorer.core.plot_main import NDXplorer

    _patch_histograms(monkeypatch, histogram2d=_line_histogram(slope=0.5, intercept=0.2))
    _autofit_dialog(monkeypatch, target="2d")

    ndx = NDXplorer()
    cw = ndx.curve_overlay_widget.add_curve("m*x + b")
    cw.set_parameters({"m": 0.1, "b": 0.35})
    cw.parameter_group.parameters_all_dict["b"].fixed = True

    ndx.on_fit_curve_to_data(cw)

    p = cw.get_parameters()
    assert p["b"] == pytest.approx(0.35, abs=1e-6)   # held
    assert p["m"] != pytest.approx(0.1, abs=1e-6)    # optimised


def test_the_curve_keeps_its_rows_after_the_fit_dialog_closes(qapp, monkeypatch):
    """Two tables show the same parameters; the survivor must keep the wiring.

    The dialog's table claims each ``parameter.controller`` and clears it when
    it is destroyed, which would leave the curve's own table unable to repaint
    itself from a later change.
    """
    from ndxplorer.core.plot_main import NDXplorer

    _patch_histograms(monkeypatch)
    _autofit_dialog(monkeypatch, target="2d")

    ndx = NDXplorer()
    cw = ndx.curve_overlay_widget.add_curve("m*x + b")
    cw.set_parameters({"m": 0.1, "b": 0.0}, {"m": [-5, 5], "b": [-5, 5]})

    ndx.on_fit_curve_to_data(cw)

    table = cw._table
    for param in cw.parameter_group.parameters_all:
        assert param.controller is not None
        assert param.controller.parent() is table


def test_a_parametric_curve_is_fitted_through_its_function(qapp, monkeypatch):
    """A FRET line traces (x, y); there is no equation, so it fits differently."""
    from ndxplorer.core.plot_main import NDXplorer

    def static_line(tau_d0=4.0, num_points=200):
        tau = np.linspace(0.05, tau_d0, int(num_points))
        return tau, 1.0 - tau / tau_d0

    xe = np.linspace(0.1, 3.4, 41)
    ye = np.linspace(-0.2, 1.2, 61)
    xc, yc = 0.5 * (xe[:-1] + xe[1:]), 0.5 * (ye[:-1] + ye[1:])
    ridge = 1.0 - xc / 3.5
    counts = np.random.default_rng(0).poisson(
        300.0 * np.exp(-((yc[None, :] - ridge[:, None]) ** 2) / (2 * 0.02 ** 2))
    ).astype(float)

    _patch_histograms(monkeypatch, histogram2d=(counts, xe, ye))
    _autofit_dialog(monkeypatch, target="2d")

    ndx = NDXplorer()
    cw = ndx.curve_overlay_widget.add_curve(
        "def static_line(tau_d0=4.0, num_points=200):\n"
        "    import numpy as np\n"
        "    tau = np.linspace(0.05, tau_d0, int(num_points))\n"
        "    return tau, 1.0 - tau / tau_d0\n",
        is_function=True,
    )
    assert cw.is_function
    cw.parameter_group.parameters_all_dict["tau_d0"].value = 2.5

    ndx.on_fit_curve_to_data(cw)

    p = cw.get_parameters()
    assert p["tau_d0"] == pytest.approx(3.5, abs=0.1)
    assert p["num_points"] == 200          # resolution, not a fitting parameter


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-q"])
