"""nDXplorer's parameter model, and its optional ChiSurf mirror.

The model (:mod:`ndxplorer.core.parameters`) is plain Python and always there.
The mirror (:mod:`ndxplorer.core.chisurf_binding`) is tested only where chisurf
and IMP.bff import; everything the app needs is covered by the first half.
"""

from __future__ import annotations

import pytest

from ndxplorer.core import chisurf_binding
from ndxplorer.core.parameters import (
    Parameter,
    ParameterGroup,
    is_held,
    link_targets,
    register_group,
    unregister_group,
)


def test_a_value_is_clipped_into_enforced_bounds_only():
    p = Parameter("a", 5.0, lb=0.0, ub=2.0)
    assert p.value == 5.0
    p.bounds_on = True
    assert p.value == 2.0
    assert p.raw[0] == 5.0                      # stored as typed


def test_a_link_follows_its_master_and_refuses_a_cycle():
    a, b = Parameter("a", 1.0), Parameter("b", 2.0)
    b.link = a
    a.value = 7.0
    assert b.value == 7.0 and b.is_linked and is_held(b) and not is_held(a)
    with pytest.raises(ValueError):
        a.link = b
    with pytest.raises(ValueError):
        a.link = a
    b.link = None
    assert b.value == 2.0


def test_state_round_trips_in_chisurfs_format():
    group = ParameterGroup("g", [Parameter("a", 1.5, fixed=True, lb=0.0, ub=3.0,
                                           bounds_on=True)])
    state = group.get_state()
    assert state == {"parameters": {"a": {"value": 1.5, "bounds_on": True,
                                          "bounds": [0.0, 3.0], "fixed": True}}}
    other = ParameterGroup("h", [Parameter("a", 0.0)])
    other.set_state(state)
    assert other.get("a").get_state() == state["parameters"]["a"]


def test_removing_a_parameter_unlinks_its_followers():
    master_group = ParameterGroup("m", [Parameter("m", 3.0)])
    follower = Parameter("f", 1.0)
    follower_group = ParameterGroup("f", [follower])
    register_group(master_group, "test.m", "M")
    register_group(follower_group, "test.f", "F")
    try:
        follower.link = master_group.get("m")
        assert ("M", "m", master_group.get("m")) in link_targets(follower)
        master_group.remove_parameter(master_group.get("m"))
        assert not follower.is_linked
    finally:
        unregister_group("test.m")
        unregister_group("test.f")


def test_a_group_tells_its_listeners_when_its_members_change():
    group = ParameterGroup("g")
    seen = []
    group.listen(lambda g: seen.append(len(g)))
    group.add("a")
    group.replace_parameters([])
    assert seen == [1, 0] and group.revision == 2


# ----------------------------------------------------------------- the mirror
needs_chisurf = pytest.mark.skipif(not chisurf_binding.available(),
                                   reason=f"chisurf: {chisurf_binding.why_unavailable()}")


@needs_chisurf
def test_the_mirror_follows_the_model_both_ways():
    from chisurf.core.fitting.parameter import FittingParameter

    group = ParameterGroup("g", [Parameter("a", 1.0), Parameter("b", 2.0, lb=0.0, ub=3.0,
                                                                bounds_on=True)])
    register_group(group, "test.mirror", "Mirror")
    try:
        cs = chisurf_binding.chisurf_group(group)
        a, b = group.get("a"), group.get("b")
        ca, cb = cs.parameters_all
        a.value = 5.0
        assert ca.value == 5.0                    # the model's write reaches ChiSurf
        ca.value = 6.0                            # the Global View edits the mirror
        assert a.value == 6.0
        cb.fixed = True
        assert b.fixed
        fit = FittingParameter(name="fit_tau", value=4.2)
        cb.link = fit                             # linked on ChiSurf's side
        assert b.link is fit and b.value == pytest.approx(4.2)
        b.link = None
        a.link = b                                # linked on ours: ChiSurf follows
        assert ca.is_linked
        group.add("c", 9.0)
        assert [p.name for p in cs.parameters_all] == ["a", "b", "c"]
        from chisurf.core.parameter_group_registry import iter_registered_parameter_groups

        assert any(g is cs for _o, _l, g in iter_registered_parameter_groups())
    finally:
        unregister_group("test.mirror")


@needs_chisurf
def test_a_parameter_can_follow_a_chisurf_fit_parameter():
    from chisurf.core.fitting.parameter import FittingParameter

    fit = FittingParameter(name="tauD0", value=3.9)
    p = Parameter("tauD0", 4.0)
    p.link = fit
    fit.value = 4.1
    assert p.value == pytest.approx(4.1)
