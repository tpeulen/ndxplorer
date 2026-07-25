"""The overlay 'Fit' button fits a curve's parameters to the X marginal."""
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


def test_overlay_has_fit_button(qapp):
    from ndxplorer.plotting.curve_overlay import CurveWidget

    cw = CurveWidget(name="c", equation_or_function="a*x+b", is_function=False)
    assert cw.fit_button.text() == "🎯 Fit"


def test_function_names_are_not_parameters(qapp):
    from ndxplorer.plotting.curve_overlay import CurveWidget

    cw = CurveWidget(name="c", equation_or_function="a*exp(-(x-mu)**2/(2*sig**2))",
                     is_function=False)
    assert set(cw.get_parameters().keys()) == {"a", "mu", "sig"}  # no 'exp'/'x'


def test_fit_button_fits_to_marginal(qapp, monkeypatch):
    import ndxplorer.plotting.histograms as H
    import ndxplorer.ui.marginal_fit_dialog as D
    from ndxplorer.core.plot_main import NDXplorer

    y, edges = _gauss_marginal(mu=0.6, sig=0.08)
    monkeypatch.setattr(H, "plot_histogram", lambda nd, dim="2d", **k: (y, edges))
    # The handler opens a modal dialog; auto-run the fit and return instead of
    # blocking on exec_() in the headless test.
    monkeypatch.setattr(D.MarginalFitDialog, "exec_",
                        lambda self: (self._do_fit(), 1)[1])

    ndx = NDXplorer()
    cw = ndx.curve_overlay_widget.add_curve(
        "a*exp(-(x-mu)**2/(2*sig**2))", use_sliders=False)
    cw.set_parameters({"a": 500.0, "mu": 0.4, "sig": 0.2},
                      {"a": [0, 5000], "mu": [0, 1], "sig": [0, 1]})

    ndx.on_fit_curve_to_marginal(cw)

    p = cw.get_parameters()
    assert p["mu"] == pytest.approx(0.6, abs=0.03)
    assert p["sig"] == pytest.approx(0.08, abs=0.03)


def test_fit_on_function_curve_is_ignored(qapp):
    from ndxplorer.core.plot_main import NDXplorer

    ndx = NDXplorer()

    class _F:
        is_function = True

    # Must not raise for a function curve (unsupported in v1).
    ndx.on_fit_curve_to_marginal(_F())


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-q"])
