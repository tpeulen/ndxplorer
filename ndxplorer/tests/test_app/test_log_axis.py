"""The log check boxes of the Histogram panel.

A log axis cannot start at or below zero, and the plot draws log only above it. Ticking log
over such a range used to leave a ticked box over an unchanged linear plot and linear bins.
"""
import numpy as np
import pytest

pytest.importorskip("tttrlib")

from ndxplorer.app.model import ExplorerModel  # noqa: E402
from ndxplorer.app.view_model import PanelModel  # noqa: E402
from ndxplorer.core.data_source import DataSource  # noqa: E402


class _Status:
    def __init__(self):
        self.lines = []

    def show_status(self, text):
        self.lines.append(text)

    def data_leaving(self):
        pass


def _model():
    rng = np.random.default_rng(3)
    n = 4000
    model = ExplorerModel()
    model.set_source(DataSource.from_columns({
        "Count Rate (KHz)": rng.lognormal(4.0, 1.0, n),
        "Tg-Tr(ms)": rng.normal(0.4, 0.3, n),
        "Offset": -rng.random(n),
        "Number of Photons": rng.random(n),
    }))
    model.set_parameter("x", "Count Rate (KHz)")
    model.set_parameter("y", "Tg-Tr(ms)")
    model.app = _Status()
    return model


def test_log_over_a_positive_range_bins_logarithmically():
    model = _model()
    PanelModel(model).x_log = True
    model.update()
    steps = np.diff(np.log(model.histograms.x_edges))
    assert model.x.log and np.allclose(steps, steps[0])


def test_log_over_a_range_through_zero_moves_to_the_positive_values():
    model = _model()
    model.y.lo, model.y.hi = -1.0, 1.0
    PanelModel(model).y_log = True
    model.update()
    assert model.y.log and model.y.lo > 0.0
    edges = model.histograms.y_edges
    assert edges[0] > 0 and np.allclose(np.diff(np.log(edges)), np.log(edges[1] / edges[0]))
    assert "positive values" in model.app.lines[-1]


def test_log_on_a_parameter_without_positive_values_is_refused_and_said():
    model = _model()
    model.set_parameter("y", "Offset")
    PanelModel(model).y_log = True
    assert model.y.log is False
    assert "no positive values" in model.app.lines[-1]
