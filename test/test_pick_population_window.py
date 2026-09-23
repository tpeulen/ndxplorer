"""The Qt window's half of picking: the click's mapping, the points fitted, the gate.

``pick_population_from_canvas`` maps a canvas click to data units. The 2-D
map's view box works in **bin indices** of the histogram image; comparing
those with the data ranges refused every pick. ``pick_population_at`` fits the
points as displayed and adds a named G2D gate. Both are driven here on a stand-in
window, so no plot has to be drawn.
"""

from __future__ import annotations

import numpy as np
import pytest

pytest.importorskip("qtpy")

from ndxplorer.core.gates import GateList  # noqa: E402
from ndxplorer.core.plot_main import NDXplorer  # noqa: E402


class _Combo:
    def __init__(self, text):
        self._text = text

    def currentText(self):
        return self._text


class _Control:
    def __init__(self, x_range, y_range, x="x", y="y"):
        self.x_range, self.y_range = x_range, y_range
        self.scale_x = self.scale_y = "lin"
        self.comboBoxSelX, self.comboBoxSelY = _Combo(x), _Combo(y)
        self.gates = GateList()

    def addGaussianSelection(self, idx1, idx2, mu, cov, sigma=1.0, invert=False,
                             enabled=True, name="", log_x=False, log_y=False):
        self.gates.add_gaussian(idx1, idx2, mu, cov, sigma, invert, enabled, name, log_x, log_y)


class _Source:
    parameter_names = ["x", "y"]


class _Status:
    def __init__(self):
        self.text = ""

    def showMessage(self, text, *_):
        self.text = text


class _Window:
    """What the two methods read of the window."""

    pick_population_at = NDXplorer.pick_population_at
    pick_population_from_canvas = NDXplorer.pick_population_from_canvas

    def __init__(self, values, x_range, y_range, **kw):
        self.values = values
        self.data_source = _Source()
        self.plot_control = _Control(x_range, y_range, **kw)
        self._status = _Status()
        self.updates = 0

    def request_plot_update(self, *_a, **_k):
        self.updates += 1

    def statusBar(self):
        return self._status


def _blob(mu, n=2000, seed=5):
    rng = np.random.default_rng(seed)
    return rng.multivariate_normal(mu, [[1.0, 0.0], [0.0, 1.0]], size=n).T


def test_a_gate_is_fitted_to_the_points_as_displayed():
    """Fitting the *visible* points: an earlier gate is not undone."""
    displayed = _blob([10.0, 4.0])      # as if a gate had removed a second cloud at x=30
    window = _Window(displayed, (0.0, 40.0), (0.0, 8.0))
    assert window.pick_population_at(12.0, 4.0) == ""
    (gate,) = window.plot_control.gates
    assert gate.kind == "G2D" and gate.meta["mu"][0] == pytest.approx(10.0, abs=0.3)
    assert window.updates == 1


def test_the_gates_are_named_and_counted():
    window = _Window(_blob([1.0, 2.0]), (-3.0, 5.0), (-2.0, 6.0))
    window.pick_population_at(1.0, 2.0)
    window.pick_population_at(1.0, 2.0, name="mine")
    assert [g.name for g in window.plot_control.gates] == ["Population 1", "mine"]


def test_refusals_come_back_as_reasons():
    window = _Window(_blob([1.0, 2.0]), (-3.0, 5.0), (-2.0, 6.0))
    assert "outside" in window.pick_population_at(9.0, 2.0)
    missing = _Window(_blob([1.0, 2.0]), (-3.0, 5.0), (-2.0, 6.0), x="nope")
    assert "could not find" in missing.pick_population_at(1.0, 2.0)
    assert len(window.plot_control.gates) == 0


class _Point:
    def __init__(self, x, y):
        self._x, self._y = x, y

    def x(self):
        return self._x

    def y(self):
        return self._y


class _View:
    """A view box in bin indices, as the 2-D image item's."""

    def __init__(self, bin_x, bin_y):
        self.point = _Point(bin_x, bin_y)

    def mapToScene(self, pos):
        return pos

    def getPlotItem(self):
        return self

    def getViewBox(self):
        return self

    def mapSceneToView(self, _scene):
        return self.point


def test_a_canvas_click_is_mapped_through_the_bin_edges():
    """Bin index 18.6 of 31 bins over 0..6 is 3.6 in data units, not 18.6."""
    window = _Window(_blob([3.3, 0.3], seed=7) * np.array([[0.3], [0.05]])
                     + np.array([[2.3], [0.285]]), (0.0, 6.0), (-0.05, 1.05))
    x_edges, y_edges = np.linspace(0.0, 6.0, 32), np.linspace(-0.05, 1.05, 32)
    window._histogram = {"2d": (np.zeros((31, 31)), x_edges, y_edges)}
    # The scenario's click: (18.59, 8.69) in the view box, (3.6, 0.258) in data.
    window.g_2dplot = type("P", (), {"plot_widget": _View(18.6, 8.69)})()
    window.pick_population_from_canvas(object())
    assert window.statusBar().text.startswith("Gate fitted to the population at (3.6, 0.258")
    (gate,) = window.plot_control.gates
    assert gate.kind == "G2D"
