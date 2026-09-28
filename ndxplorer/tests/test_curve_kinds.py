"""Parametric curves and point sets: the overlay-curve kinds beside y = f(x).

A parametric curve is ``(x(t), y(t))`` for ``t`` in ``[t0, t1]``; a point set
is markers (and labels) at listed ``t``. Both are declared as specs and share
what every curve has: parameters, links, vectors, the fit's traced contract.
"""

from __future__ import annotations

import numpy as np

from ndxplorer.core.overlay_curves import (
    OverlayCurve, compile_spec, parse_where, spec_function_source, spec_parameter_names)

CIRCLE = {"where": "omega = 2*pi*f*harmonic*1e-3\ntau = tan(t)/omega",
          "x": "1/(1+(omega*tau)**2)", "y": "omega*tau/(1+(omega*tau)**2)",
          "t": [0.0, np.pi / 2]}
POINTS = {"where": "omega = 2*pi*f*harmonic*1e-3", "x": "1/(1+(omega*t)**2)",
          "y": "omega*t/(1+(omega*t)**2)", "t": [0.5, 1, 2, 4], "labels": "{t:g} ns"}


def test_where_is_ordered_definitions():
    assert parse_where("a = 1; b = a*2\nc=b") == [("a", "1"), ("b", "a*2"), ("c", "b")]
    assert parse_where({"a": "1"}) == [("a", "1")]


def test_parameters_are_the_free_names_in_order():
    assert spec_parameter_names(CIRCLE) == ["f", "harmonic"]
    assert spec_parameter_names({"x": "a*cos(t)+x0", "y": "b*sin(t)"}) == ["a", "x0", "b"]


def test_parametric_curve_traces_the_circle():
    curve = OverlayCurve("c", kind="parametric", spec=CIRCLE)
    curve.set_parameters({"f": 80.0, "harmonic": 2})
    x, y = curve.points(200, [0.0, 1.0], [0.0, 0.6])
    assert x.size == 200
    np.testing.assert_allclose((x - 0.5) ** 2 + y ** 2, 0.25, atol=1e-12)
    assert x[0] == 1.0 and abs(x[-1]) < 1e-12  # tau from 0 to infinity


def test_point_set_markers_and_labels():
    curve = OverlayCurve("p", kind="points", spec=POINTS, color="#ffd000")
    curve.set_parameters({"f": 80.0, "harmonic": 1})
    ((name, colour, x, y, labels),) = curve.drawn_points([0.0, 1.0], [0.0, 0.6])
    wt = 2 * np.pi * 80e-3 * np.array([0.5, 1, 2, 4])
    np.testing.assert_allclose(x, 1 / (1 + wt ** 2))
    np.testing.assert_allclose(y, wt / (1 + wt ** 2))
    assert labels == ["0.5 ns", "1 ns", "2 ns", "4 ns"] and colour == "#ffd000"
    # cut to the axes: the label goes with its marker
    ((_, _, x, _, labels),) = curve.drawn_points([0.3, 1.0], [0.0, 0.6])
    assert labels == ["0.5 ns", "1 ns", "2 ns"] and x.size == 3


def test_spec_edits_keep_parameter_state_and_links():
    from ndxplorer.core.parameters import Parameter, ParameterGroup

    constants = ParameterGroup("ndX", [Parameter("f_rep", 40.0)])
    curve = OverlayCurve("c", kind="parametric", spec=CIRCLE)
    curve.links = {"f": "f_rep", "harmonic": "harmonic"}
    assert curve.link_to(constants) == ["f"]  # no 'harmonic' constant: stays free
    assert curve.get_parameters()["f"] == 40.0
    curve.set_spec(t=[0.0, 1.0])
    assert curve.group.parameters_all_dict["f"].link is constants.parameters_all_dict["f_rep"]


def test_vector_parameter_gives_one_curve_per_population():
    curve = OverlayCurve("p", kind="points", spec=POINTS)
    curve.set_parameters({"f": 80.0, "harmonic": 1})
    curve.group.get("f").set_vector([40.0, 80.0], ["A", "B"])
    assert curve.populations() == ["A", "B"]
    drawn = curve.drawn_points([0.0, 1.0], [0.0, 0.6])
    assert [d[0] for d in drawn] == ["p [A]", "p [B]"]


def test_compiled_spec_is_the_traced_function_contract():
    traced = compile_spec(dict(CIRCLE, kind="parametric"), lambda: 5)
    x, y = traced(f=80.0, harmonic=1)
    assert x.shape == y.shape == (5,)


def test_function_source_matches_the_spec():
    from ndxplorer.core.overlay_curves import CurveEvaluator

    source = spec_function_source(CIRCLE, {"f": 80.0, "harmonic": 1}, samples=50)
    function = CurveEvaluator().compile_function(source)
    x, y = function(f=80.0, harmonic=1)
    ref = compile_spec(dict(CIRCLE, kind="parametric"), lambda: 50)(f=80.0, harmonic=1)
    np.testing.assert_allclose(x, ref[0])
    np.testing.assert_allclose(y, ref[1])


def test_equation_namespace_has_the_maths_names():
    curve = OverlayCurve("e", "a*arctan(x)")
    assert list(curve.get_parameters()) == ["a"]
    x, y = curve.points(10, [0.0, 1.0], [-10.0, 10.0])
    np.testing.assert_allclose(y, np.arctan(x))
