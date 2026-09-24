"""Any nDXplorer parameter can be a vector: one value per population.

The Gaussians and the overlay curves are groups of ordinary parameters, so a
Gaussian's weight or a curve's ``tauD0`` can hold one value per population
exactly as a constant does (:meth:`~ndxplorer.core.parameters.Parameter.set_vector`).
The elements belong to their parameter: a group's layout -- six parameters per
Gaussian, a curve's names -- does not move, and what does not know about
populations reads the global value.
"""

from __future__ import annotations

import pytest
from ndxplorer.core import constants_group as cg
from ndxplorer.core import curve_parameters as cp
from ndxplorer.core import gaussian_parameters as gp
from ndxplorer.core.overlay_curves import OverlayCurve
from ndxplorer.core.parameters import Parameter, ParameterGroup, is_held


def _mixture():
    group = gp.build_gaussian_group()
    group.append((1.0, 2.0), [[0.04, 0.0], [0.0, 0.09]], 1.0)
    group.append((3.0, 4.0), [[0.01, 0.0], [0.0, 0.01]], 2.0)
    return group


def test_a_gaussian_weight_holds_one_value_per_population():
    group = _mixture()
    w_1 = group.get("w_1")
    elements = w_1.set_vector([0.4, 0.6], ["HF", "LF"])
    assert [e.name for e in elements] == ["w_1[HF]", "w_1[LF]"]
    # The component layout does not move: still two Gaussians, six parameters each.
    assert len(group) == 2 and len(group.parameters_all) == 2 * gp.WIDTH
    assert group.parameters_of(1)["w"].name == "w_2"
    assert [c.w for c in group.components()] == [1.0, 2.0]       # the global values
    # A new element starts with the parameter's bounds and fixed flag.
    assert elements[0].bounds_on and elements[0].lb == 0.0
    assert group.get("w_1[LF]") is elements[1]
    assert "w_1[LF]" in group.parameters_all_dict


def test_removing_a_gaussian_renames_the_vectors_that_follow_it():
    group = _mixture()
    group.get("w_2").set_vector([1.0, 3.0], ["0", "1"])
    group.pop(0)
    assert group.get("w_1").populations == ["0", "1"]
    assert group.get("w_1[1]").value == 3.0 and group.get("w_2[1]") is None


def test_a_gaussian_vector_round_trips_through_the_group_state():
    group = _mixture()
    group.get("sd_x_1").set_vector([0.1, 0.3], ["HF", "LF"], column="Population")
    group.get("sd_x_1[LF]").fixed = True
    state = group.get_state()
    assert state["vectors"]["sd_x_1"] == {"populations": ["HF", "LF"], "column": "Population"}
    again = _mixture()
    again.set_state(state)
    assert again.get("sd_x_1").populations == ["HF", "LF"]
    assert again.get("sd_x_1[LF]").fixed and again.get("sd_x_1[LF]").value == 0.3
    assert again.get("sd_x_1").vector_state()["column"] == "Population"


def test_a_curve_parameter_vector_keeps_its_elements_when_the_equation_changes():
    curve = OverlayCurve("c", "a*x+b")
    a = curve.group.get("a")
    a.set_vector([2.0, 3.0], ["HF", "LF"])
    curve.set_text("a*x+b+c")
    assert curve.group.get("a") is a and a.populations == ["HF", "LF"]
    assert list(curve.get_parameters()) == ["a", "b", "c"]       # the curve reads the global
    cp.sync_curve_group(curve.group, ["b", "c"])
    assert curve.group.get("a[HF]") is None


def test_an_element_links_and_is_held():
    constants = cg.build_constants_group({"tauD0": 4.0})
    curve = cp.build_curve_group(["tauD0"])
    element = curve.get("tauD0").set_vector([4.0, 3.0], ["HF", "LF"])[1]
    element.link = constants.get("tauD0")
    assert is_held(element) and element.value == 4.0
    curve.get("tauD0").to_scalar()
    assert element.link is None                   # a removed element lets go
    assert curve.get("tauD0[LF]") is None


def test_the_constants_api_is_the_group_vector_api():
    group = cg.build_constants_group({"gamma": 0.7, "gamma[HF]": 0.6, "gamma[LF]": 0.8})
    assert [p.name for p in group.parameters_all] == ["gamma"]
    assert cg.vector_labels(group, "gamma") == ["HF", "LF"]
    cg.set_vector(group, "beta", [1.0, 3.0], ["HF", "LF"], uncertainties=[0.1, None])
    assert group.get("beta").fixed and group.get("beta").value == 2.0
    assert cg.vector_uncertainty(group, "beta", "HF") == 0.1
    assert cg.group_to_value_dict(group) == {
        "gamma": 0.7, "gamma[HF]": 0.6, "gamma[LF]": 0.8,
        "beta": 2.0, "beta[HF]": 1.0, "beta[LF]": 3.0}
    assert cg.remove_parameter(group, "beta[HF]") and cg.vector_labels(group, "beta") == ["LF"]


def test_a_vector_needs_distinct_populations_and_an_element_is_not_one():
    p = Parameter("g", 1.0)
    with pytest.raises(ValueError):
        p.set_vector([1.0, 2.0], ["a", "a"])
    element = p.set_vector([1.0], ["a"])[0]
    with pytest.raises(ValueError):
        element.set_vector([1.0], ["b"])
    with pytest.raises(AttributeError):
        element.name = "other"


def test_membership_changes_of_a_vector_tell_the_group():
    group = ParameterGroup("g", [Parameter("a", 1.0)])
    seen = []
    group.listen(lambda g: seen.append(g.revision))
    group.get("a").set_vector([1.0, 2.0], ["0", "1"])
    group.get("a").to_scalar()
    assert seen == [1, 2]
