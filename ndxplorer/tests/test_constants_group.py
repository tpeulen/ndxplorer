"""Qt-free tests for the constants FittingParameterGroup adapter."""
from collections import OrderedDict

import numpy as np
import pandas as pd
import pytest

pytest.importorskip("chisurf.core.fitting.parameter", reason="chisurf not importable")

from ndxplorer.core import constants_group as cg  # noqa: E402
from ndxplorer.core.equation_graph import compute_values_ast  # noqa: E402


CONSTANTS = OrderedDict([
    ("gG/gR", 0.6), ("Bg", 1.2), ("Br", 0.6), ("PhiA", 0.32), ("PhiD", 0.8),
    ("alpha", 0.015), ("tauD0", 4.0), ("forster_radius", 52.0),
])


def test_build_group_defaults_fixed():
    g = cg.build_constants_group(CONSTANTS)
    assert [p.name for p in g.parameters_all] == list(CONSTANTS)
    assert [float(p.value) for p in g.parameters_all] == list(CONSTANTS.values())
    assert all(p.fixed for p in g.parameters_all)


def test_mapping_contract():
    g = cg.build_constants_group(CONSTANTS)
    m = cg.ConstantsMapping(g)
    assert m["forster_radius"] == 52.0
    assert isinstance(m["forster_radius"], float)
    assert set(m.keys()) == set(CONSTANTS)
    assert len(m) == len(CONSTANTS)
    assert m.get("nope", 7.0) == 7.0
    assert bool(m) is True
    m.update({"Bg": 2.0})
    assert g.parameters_all_dict["Bg"].value == 2.0
    m.update({"NEW": 9.0})  # unknown name is appended
    assert m["NEW"] == 9.0


def test_engine_reads_live_values():
    g = cg.build_constants_group(CONSTANTS)
    m = cg.ConstantsMapping(g)
    df = pd.DataFrame({"Sg": np.array([10.0, 20.0, 30.0])})
    eqs = [{"Fg": "'Sg' - 'Bg'"}]

    compute_values_ast(df, m, eqs)
    np.testing.assert_allclose(df["Fg"].to_numpy(), [10 - 1.2, 20 - 1.2, 30 - 1.2])

    g.parameters_all_dict["Bg"].value = 5.0
    compute_values_ast(df, m, eqs)
    np.testing.assert_allclose(df["Fg"].to_numpy(), [10 - 5, 20 - 5, 30 - 5])


def test_linked_constant_follows_master_in_engine():
    from chisurf.core.fitting.parameter import FittingParameter

    g = cg.build_constants_group(CONSTANTS)
    m = cg.ConstantsMapping(g)
    master = FittingParameter(name="master_bg", value=3.0)
    g.parameters_all_dict["Bg"].link = master

    assert m["Bg"] == 3.0  # follows the master immediately
    df = pd.DataFrame({"Sg": np.array([10.0])})
    compute_values_ast(df, m, [{"Fg": "'Sg' - 'Bg'"}])
    assert df["Fg"].iloc[0] == 7.0

    master.value = 1.0
    compute_values_ast(df, m, [{"Fg": "'Sg' - 'Bg'"}])
    assert df["Fg"].iloc[0] == 9.0


def test_state_roundtrip_with_bounds_and_fixed():
    g = cg.build_constants_group(CONSTANTS)
    p = g.parameters_all_dict["tauD0"]
    p.bounds_on = True
    p.lb, p.ub = 1.0, 8.0
    p.fixed = False
    state = cg.group_state(g)

    g2 = cg.build_constants_group(CONSTANTS)
    cg.apply_group_state(g2, state)
    p2 = g2.parameters_all_dict["tauD0"]
    assert p2.value == 4.0
    assert p2.fixed is False
    assert tuple(p2.bounds) == (1.0, 8.0)
    assert p2.bounds_on is True


def test_format_detection_and_build_from_data():
    flat = dict(CONSTANTS)
    nested = cg.group_state(cg.build_constants_group(CONSTANTS))
    assert cg.is_state_format(nested) is True
    assert cg.is_state_format(flat) is False
    assert cg.values_from_data(nested) == cg.values_from_data(flat)

    g_flat = cg.build_group_from_data(flat)
    g_nested = cg.build_group_from_data(nested)
    assert cg.group_to_value_dict(g_flat) == cg.group_to_value_dict(g_nested)


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-q"])
