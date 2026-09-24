"""An overlay curve with a population-wise parameter is one curve per population.

A curve parameter made a vector (or linked to a vector constant) gives each
population its own curve: the population's element where the vector has one,
the shared value for every other parameter. With no population-wise parameter
the curve is the one global curve it always was.
"""

from __future__ import annotations

import numpy as np
import pytest
from ndxplorer.core.overlay_curves import (
    OverlayCurve,
    population_colour,
    population_labels,
    population_parameter_sets,
)
from ndxplorer.core.parameters import Parameter

X_EDGES = np.linspace(0.0, 10.0, 11)
Y_EDGES = np.linspace(-100.0, 100.0, 11)


def test_a_curve_without_vectors_is_one_global_curve():
    curve = OverlayCurve("line", "a*x + b")
    curve.set_parameters({"a": 2.0, "b": 1.0})
    assert curve.populations() == [] and population_parameter_sets(curve.group) == []
    drawn = curve.drawn_curves(50, X_EDGES, Y_EDGES)
    assert [(name, colour) for name, colour, _x, _y in drawn] == [("line", curve.color)]
    np.testing.assert_allclose(drawn[0][3], 2.0 * drawn[0][2] + 1.0)


def test_a_vector_parameter_draws_one_curve_per_population():
    curve = OverlayCurve("line", "a*x + b", color="#2060c0")
    curve.set_parameters({"a": 2.0, "b": 1.0})
    curve.group.get("a").set_vector([1.0, 3.0], ["HF", "LF"])
    assert curve.populations() == ["HF", "LF"]
    drawn = curve.drawn_curves(50, X_EDGES, Y_EDGES)
    assert [name for name, *_ in drawn] == ["line [HF]", "line [LF]"]
    for (_name, _colour, x, y), slope in zip(drawn, (1.0, 3.0)):
        np.testing.assert_allclose(y, slope * x + 1.0)       # b is shared
    colours = {colour for _name, colour, *_ in drawn}
    assert len(colours) == 2 and curve.color not in colours  # tinted per population


def test_populations_are_the_union_over_the_vectors():
    curve = OverlayCurve("line", "a*x + b")
    curve.group.get("a").set_vector([1.0, 3.0], ["HF", "LF"])
    curve.group.get("b").value = 5.0
    curve.group.get("b").set_vector([7.0], ["MF"])
    assert population_labels(curve.group) == ["HF", "LF", "MF"]
    sets = dict(population_parameter_sets(curve.group))
    # a vector without that population reads its global value
    assert sets["MF"]["a"] == pytest.approx(curve.group.get("a").value)
    assert sets["HF"]["b"] == pytest.approx(5.0) and sets["MF"]["b"] == pytest.approx(7.0)


def test_a_parameter_linked_to_a_vector_constant_follows_its_elements():
    gamma = Parameter("gamma", 0.8)
    gamma.set_vector([0.5, 1.1], ["FRET 1", "FRET 2"])
    curve = OverlayCurve("line", "g*x")
    curve.group.get("g").link = gamma
    sets = population_parameter_sets(curve.group)
    assert [(label, values["g"]) for label, values in sets] == [("FRET 1", 0.5),
                                                                 ("FRET 2", 1.1)]


def test_population_colour_keeps_the_hue_and_steps_the_lightness():
    import colorsys

    tints = [population_colour("#ff0000", i, 3) for i in range(3)]
    assert len(set(tints)) == 3
    hls = [colorsys.rgb_to_hls(*(int(t[i:i + 2], 16) / 255 for i in (1, 3, 5))) for t in tints]
    assert all(h == pytest.approx(0.0, abs=0.02) for h, _l, _s in hls)
    assert hls[0][1] < hls[1][1] < hls[2][1]
    assert population_colour("#123456", 0, 1) == "#123456"


def test_the_emtk_map_draws_one_line_per_population(tmp_path, monkeypatch):
    """The Overlays feature draws N lines (and N labels) for an N-population curve."""
    monkeypatch.setenv("HOME", str(tmp_path))
    from emtk import implot

    from ndxplorer.tests.test_app.test_parameter_tables import replay

    run = replay([])
    try:
        feature = next(f for f in run.app.features if f.name == "overlays")
        feature.overlays.equation_choice = "FD/FA vs tau (static line)"
        curve = feature.overlays.add_curve()
        lines, labels = [], []
        real_line, real_text = implot.plot_line, implot.plot_text
        monkeypatch.setattr(implot, "plot_line",
                            lambda label, *a, **k: (lines.append(label),
                                                    real_line(label, *a, **k))[1])
        monkeypatch.setattr(implot, "plot_text",
                            lambda text, *a, **k: (labels.append(text),
                                                   real_text(text, *a, **k))[1])
        run.settle(2)
        assert [l for l in lines if l.startswith("##overlay-curve-")]
        assert not labels                                   # one global curve, unlabelled
        lines.clear()
        curve.group.get("tauD0").set_vector([4.0, 2.5], ["HF", "LF"])
        run.settle(2)
        drawn = [l for l in lines if l.startswith("##overlay-curve-0-")]
        assert sorted(set(drawn)) == ["##overlay-curve-0-0", "##overlay-curve-0-1"]
        assert {"[HF]", "[LF]"} <= set(labels)
    finally:
        run.app.close()
