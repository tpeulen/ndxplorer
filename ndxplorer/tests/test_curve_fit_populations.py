"""A curve with population-wise parameters is fitted jointly over its populations.

Synthetic bursts of two populations, told apart by a label column (or by
probability columns), each following the same curve with its own value of one
parameter and a shared value of the other. The joint fit must recover every
population's element, the shared value, and report one reduced chi-square per
population; the fitted values land in the curve's elements.
"""

from __future__ import annotations

import numpy as np
import pytest
from ndxplorer.analysis.curve_fit import CurveFitError
from ndxplorer.analysis.curve_fit_populations import PopulationCurveFit
from ndxplorer.analysis.curve_fit_setup import (
    build_curve_fit_for,
    make_fit_data_reader,
    result_text,
)
from ndxplorer.core.overlay_curves import OverlayCurve


class Source:
    def __init__(self, columns):
        self.columns = {k: np.asarray(v, dtype=float) for k, v in columns.items()}

    def column_values(self, name):
        return self.columns.get(name)


class Host:
    """A window showing columns ``x`` and ``y`` of *source*."""

    constants: dict = {}
    constants_group = None
    equations = ()

    def __init__(self, source, x_edges, y_edges):
        self.source, self.x_edges, self.y_edges = source, x_edges, y_edges

    def fit_data_reader(self):
        return make_fit_data_reader(self.source, np.arange(self.source.columns["x"].size),
                                    "x", "y")

    def histogram_2d(self):
        x, y = self.source.columns["x"], self.source.columns["y"]
        h, _, _ = np.histogram2d(x, y, [self.x_edges, self.y_edges])
        return h.T, self.x_edges, self.y_edges

    def marginal(self, axis):
        values = self.source.columns[axis]
        edges = self.x_edges if axis == "x" else self.y_edges
        return edges, np.histogram(values, edges)[0].astype(float)

    def density(self, _target):
        return False

    def recompute_for_constants(self, changed, targets=None):
        pass


def _lines(seed=1, n=4000):
    """Two populations on y = a*x + b: a = 1.0 / 3.0, b = 2.0 shared."""
    rng = np.random.default_rng(seed)
    x = rng.uniform(0.5, 9.5, 2 * n)
    label = np.repeat([0.0, 1.0], n)
    a = np.where(label == 0, 1.0, 3.0)
    y = a * x + 2.0 + rng.normal(0.0, 0.3, 2 * n)
    return Source({"x": x, "y": y, "Cluster Label": label,
                   "P0": (label == 0).astype(float), "P1": (label == 1).astype(float)})


def _line_curve():
    curve = OverlayCurve("line", "a*x + b")
    curve.set_parameters({"a": 2.0, "b": 1.0})
    curve.group.get("a").set_vector([2.0, 2.0], ["HF", "LF"])
    return curve


@pytest.mark.parametrize("reduction", ["mean", "population"])
def test_the_joint_fit_recovers_each_population_and_the_shared_value(reduction):
    host = Host(_lines(), np.linspace(0.0, 10.0, 41), np.linspace(0.0, 35.0, 71))
    curve = _line_curve()
    cf = build_curve_fit_for(host, curve, "2d", reduction)
    assert isinstance(cf, PopulationCurveFit)
    assert [p.name for p in cf.parameters] == ["a[HF]", "a[LF]", "b"]
    result = cf.run(scan=False)
    assert result.ok, result.message
    assert result.params["a[HF]"] == pytest.approx(1.0, abs=0.05)
    assert result.params["a[LF]"] == pytest.approx(3.0, abs=0.05)
    assert result.params["b"] == pytest.approx(2.0, abs=0.25)
    assert set(result.population_chi2r) == {"HF", "LF"}
    assert all(np.isfinite(v) and v > 0 for v in result.population_chi2r.values())
    cf.write_back(curve.group)
    assert curve.group.get("a[HF]").value == pytest.approx(1.0, abs=0.05)
    assert curve.group.get("a[LF]").value == pytest.approx(3.0, abs=0.05)
    assert curve.group.get("b").value == pytest.approx(2.0, abs=0.25)
    text, failed = result_text(result)
    assert not failed and "χ²ᵣ[HF]=" in text and "χ²ᵣ[LF]=" in text


def test_the_cloud_fit_moves_each_population_towards_its_own_line():
    host = Host(_lines(), np.linspace(0.0, 10.0, 41), np.linspace(0.0, 35.0, 71))
    curve = _line_curve()
    curve.group.get("b").fixed = True
    curve.group.get("b").value = 2.0
    cf = build_curve_fit_for(host, curve, "2d", "cloud")
    result = cf.run(scan=False)
    assert result.ok, result.message
    assert result.params["a[HF]"] == pytest.approx(1.0, abs=0.1)
    assert result.params["a[LF]"] == pytest.approx(3.0, abs=0.1)


def test_probability_columns_split_the_populations():
    host = Host(_lines(), np.linspace(0.0, 10.0, 41), np.linspace(0.0, 35.0, 71))
    curve = _line_curve()
    curve.group.get("a").set_vector([2.0, 2.0], ["HF", "LF"], column="missing",
                                    probabilities={"HF": "P0", "LF": "P1"})
    result = build_curve_fit_for(host, curve, "2d", "mean").run(scan=False)
    assert result.params["a[HF]"] == pytest.approx(1.0, abs=0.05)
    assert result.params["a[LF]"] == pytest.approx(3.0, abs=0.05)


def test_a_marginal_fit_recovers_each_populations_centre():
    rng = np.random.default_rng(3)
    x = np.concatenate([rng.normal(2.0, 0.5, 5000), rng.normal(6.0, 0.5, 5000)])
    source = Source({"x": x, "y": np.zeros_like(x),
                     "Cluster Label": np.repeat([0.0, 1.0], 5000)})
    host = Host(source, np.linspace(0.0, 8.0, 81), np.linspace(-1.0, 1.0, 5))
    curve = OverlayCurve("gauss", "A*exp(-(x-mu)**2/(2*s**2))")
    curve.set_parameters({"A": 400.0, "mu": 4.0, "s": 0.8})
    curve.group.get("mu").set_vector([3.0, 5.0], ["0", "1"])
    result = build_curve_fit_for(host, curve, "x").run(scan=False)
    assert result.ok, result.message
    assert result.params["mu[0]"] == pytest.approx(2.0, abs=0.05)
    assert result.params["mu[1]"] == pytest.approx(6.0, abs=0.05)
    assert result.params["s"] == pytest.approx(0.5, abs=0.05)       # shared width


def test_a_held_element_stays_and_a_missing_column_is_reported():
    host = Host(_lines(), np.linspace(0.0, 10.0, 41), np.linspace(0.0, 35.0, 71))
    curve = _line_curve()
    curve.group.get("a[LF]").fixed = True
    result = build_curve_fit_for(host, curve, "2d", "mean").run(scan=False)
    assert result.params["a[LF]"] == pytest.approx(2.0)
    assert result.params["a[HF]"] != pytest.approx(2.0)
    curve.group.get("a").set_vector([2.0, 2.0], ["HF", "LF"], column="nowhere")
    with pytest.raises(CurveFitError, match="nowhere"):
        build_curve_fit_for(host, curve, "2d", "mean")
