"""Vector constants: one value per population, evaluated burst by burst."""
import json
from collections import OrderedDict

import numpy as np
import pytest

from ndxplorer.core.data_source import float_column, store_from_columns
from ndxplorer.core.equation_graph import compute_values_ast
from ndxplorer.core.vector_constants import (
    PopulationAxis,
    PopulationVector,
    split_element,
    summary_text,
    vectors_from_values,
)

# Green/red signals of four bursts; the first two are population HF (code 0),
# the third LF (code 1), the fourth in no population (NaN label).
FD = np.array([100.0, 50.0, 80.0, 60.0])
FA = np.array([40.0, 90.0, 20.0, 30.0])
LABEL = np.array([0.0, 0.0, 1.0, np.nan])
E_EQ = [{"E": "'FA' / ('gamma' * 'FD' + 'FA')"}]


def _column(store, name):
    return float_column(store, store.find(name))


def _store(**extra):
    return store_from_columns({"FD": FD, "FA": FA, "Cluster Label": LABEL, **extra})


def test_element_names():
    assert split_element("gamma[HF]") == ("gamma", "HF")
    assert split_element("gG/gR[0]") == ("gG/gR", "0")
    assert split_element("gamma") is None
    assert split_element("[x]") is None


def test_two_population_gamma_matches_a_hand_computation():
    """A flat constants dict carries the vector by its element names."""
    store = _store()
    constants = {"gamma": 0.7, "gamma[0]": 0.61, "gamma[1]": 0.83}
    assert compute_values_ast(store, constants, E_EQ) == ["E"]
    gamma = np.array([0.61, 0.61, 0.83, 0.7])  # the unlabelled burst: global
    np.testing.assert_allclose(_column(store, "E"), FA / (gamma * FD + FA))


def test_scalar_equations_are_unchanged():
    store = _store()
    compute_values_ast(store, {"gamma": 0.7}, E_EQ)
    np.testing.assert_allclose(_column(store, "E"), FA / (0.7 * FD + FA))


def test_one_element_reads_as_a_scalar():
    store = _store()
    constants = {"gamma": 0.7, "gamma[0]": 0.61, "gamma[1]": 0.83}
    compute_values_ast(store, constants, [{"E1": "'FA' / ('gamma[1]' * 'FD' + 'FA')"}])
    np.testing.assert_allclose(_column(store, "E1"), FA / (0.83 * FD + FA))


def test_probabilities_mix_the_elements():
    p_hf = np.array([1.0, 0.25, 0.0, 0.0])
    p_lf = np.array([0.0, 0.75, 1.0, 0.0])
    store = _store(**{"P(HF)": p_hf, "P(LF)": p_lf})
    axis = {"gamma": {"column": "Cluster Label",
                      "probabilities": {"HF": "P(HF)", "LF": "P(LF)"}}}
    vectors = vectors_from_values({"gamma": 0.7, "gamma[HF]": 0.6, "gamma[LF]": 0.8}, axes=axis)
    gamma = vectors["gamma"].per_burst(lambda n: _column(store, n) if store.find(n) >= 0
                                       else None, 4)
    np.testing.assert_allclose(gamma, [0.6, 0.25 * 0.6 + 0.75 * 0.8, 0.8, 0.7])


def test_named_labels_select_by_position_or_code():
    vector = PopulationVector("g", ["HF", "LF"], np.array([1.0, 2.0]), 9.0,
                              PopulationAxis(column="Pop", codes={"LF": 5}))
    labels = {"Pop": np.array([0.0, 5.0, 1.0])}
    np.testing.assert_allclose(vector.per_burst(labels.get, 3), [1.0, 2.0, 9.0])
    # No label column in the data: every burst gets the global value.
    assert vector.per_burst(lambda _n: None, 3) == 9.0


def test_vector_without_a_global_falls_back_to_the_mean():
    vectors = vectors_from_values({"b[0]": 1.0, "b[1]": 3.0})
    assert vectors["b"].default == 2.0
    assert summary_text([0.61, 0.83]) == "0.61, 0.83"


def test_changed_element_recomputes_what_reads_the_vector():
    store = _store()
    constants = {"gamma": 0.7, "gamma[0]": 0.61, "gamma[1]": 0.83, "k": 1.0}
    eqs = E_EQ + [{"K": "'FD' * 'k'"}]
    compute_values_ast(store, constants, eqs)
    constants["gamma[1]"] = 1.0
    assert compute_values_ast(store, constants, eqs, changed_constants={"gamma[1]"}) == ["E"]
    assert _column(store, "E")[2] == pytest.approx(FA[2] / (FD[2] + FA[2]))


# ------------------------------------------------------------ the group
cg = pytest.importorskip("ndxplorer.core.constants_group")


@pytest.fixture
def group():
    return cg.build_constants_group(OrderedDict([("gamma", 0.7), ("Bg", 1.2)]))


def test_set_vector_on_the_group_drives_the_engine(group):
    mapping = cg.ConstantsMapping(group)
    mapping.set_vector("gamma", [0.61, 0.83], ["HF", "LF"], uncertainties=[0.01, 0.02])
    assert cg.vector_names(group) == ["gamma"]
    assert cg.vector_labels(group, "gamma") == ["HF", "LF"]
    assert mapping["gamma"] == 0.7 and mapping["gamma[LF]"] == 0.83
    assert group.parameters_all_dict["gamma[HF]"].error_estimate == 0.01
    store = _store()
    compute_values_ast(store, mapping, E_EQ)
    gamma = np.array([0.61, 0.61, 0.83, 0.7])
    np.testing.assert_allclose(_column(store, "E"), FA / (gamma * FD + FA))


def test_an_element_keeps_fixed_bounds_and_link_when_the_vector_is_set_again(group):
    cg.set_vector(group, "gamma", [0.6, 0.8, 0.9], ["a", "b", "c"])
    element = group.parameters_all_dict["gamma[a]"]
    element.fixed = False
    element.lb, element.ub = 0.1, 2.0
    element.bounds_on = True
    cg.set_vector(group, "gamma", [0.5, 0.7], ["a", "b"])
    assert group.parameters_all_dict["gamma[a]"] is element
    assert element.value == 0.5 and not element.fixed and element.bounds_on
    assert "gamma[c]" not in group.parameters_all_dict


def test_linked_element_follows_its_master(group):
    from chisurf.core.fitting.parameter import FittingParameter

    cg.set_vector(group, "gamma", [0.6, 0.8], ["0", "1"])
    master = FittingParameter(name="fit_gamma", value=1.5)
    group.parameters_all_dict["gamma[1]"].link = master
    store = _store()
    compute_values_ast(store, cg.ConstantsMapping(group), E_EQ)
    assert _column(store, "E")[2] == pytest.approx(FA[2] / (1.5 * FD[2] + FA[2]))


def test_scalar_to_vector_and_back(group):
    cg.to_vector(group, "Bg", ["0", "1"])
    assert [p.value for _l, p in cg.vector_elements(group, "Bg")] == [1.2, 1.2]
    cg.to_scalar(group, "Bg")
    assert not cg.is_vector(group, "Bg")
    assert [p.name for p in group.parameters_all] == ["gamma", "Bg"]


def test_rich_file_round_trip_keeps_order_and_axis(group):
    cg.set_vector(group, "gamma", [0.83, 0.61], ["LF", "HF"], column="Population",
                  probabilities={"LF": "P(LF)", "HF": "P(HF)"})
    data = json.loads(json.dumps(cg.group_state(group)))
    again = cg.build_group_from_data(data)
    assert cg.vector_labels(again, "gamma") == ["LF", "HF"]
    axis = cg.vector_axis(again, "gamma")
    assert axis.column == "Population" and axis.probabilities["HF"] == "P(HF)"


def test_flat_file_carries_a_vector_and_old_files_still_read(group):
    cg.set_vector(group, "gamma", [0.61, 0.83], ["0", "1"])
    flat = json.loads(json.dumps(dict(cg.group_to_value_dict(group))))
    again = cg.build_group_from_data(flat)
    assert cg.vector_labels(again, "gamma") == ["0", "1"]
    old = cg.build_group_from_data({"gamma": 0.7, "Bg": 1.2})
    assert cg.vector_names(old) == []


def test_settings_persist_writes_elements_in_either_format(tmp_path):
    from ndxplorer.settings.persist import constants_payload, read_json, write_constants
    from ndxplorer.core.constants_group import values_from_data

    values = {"gamma": 0.7, "gamma[HF]": 0.61, "gamma[LF]": 0.83}
    flat = constants_payload(values)
    assert flat == values                            # the old flat format, unchanged
    rich = {"parameters": {"gamma": {"value": 0.5, "fixed": True}},
            "vectors": {"gamma": {"populations": ["HF", "LF"], "column": "Population"}}}
    path = tmp_path / "c.json"
    write_constants(path, constants_payload(values, rich))
    data = read_json(path)
    assert data["vectors"]["gamma"]["column"] == "Population"
    assert values_from_data(data) == values
