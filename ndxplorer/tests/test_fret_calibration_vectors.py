"""Species-specific calibration factors reach ndX as vector constants, and survive saving."""

import json

import pytest

pytest.importorskip("chisurf")

from ndxplorer.analysis.fret_calibration import apply_result  # noqa: E402
from ndxplorer.core import constants_group as cg  # noqa: E402
from ndxplorer.io.fret_calibration_io import payload, read_payload  # noqa: E402

VECTOR = {
    "values": [0.6, 1.2],
    "populations": ["FRET 2", "FRET 1"],  # deliberately not in sorted order
    "uncertainties": [0.02, 0.05],
    "default": 0.8,
    "column": "Population",
    "codes": {"FRET 2": 1.0, "FRET 1": 0.0},
    "probabilities": {"FRET 2": "P(FRET 2)", "FRET 1": "P(FRET 1)"},
}


def _mapping():
    return cg.ConstantsMapping(cg.build_constants_group({"gamma": 1.0, "alpha": 0.0}))


def test_apply_result_writes_vectors_after_the_scalars():
    mapping = _mapping()
    order = []
    apply_result({"constants": {"gamma": 0.8}, "vectors": {"gamma": VECTOR}},
                 write_constants=lambda values: (order.append("scalars"), mapping.update(values)),
                 write_vector=lambda name, v: (order.append(name),
                                               mapping.set_vector(name, v["values"],
                                                                  v["populations"],
                                                                  default=v["default"],
                                                                  column=v["column"],
                                                                  codes=v["codes"])))
    assert order == ["scalars", "gamma"]
    assert cg.vector_labels(mapping.group, "gamma") == ["FRET 2", "FRET 1"]
    assert mapping["gamma"] == 0.8


def test_payload_keeps_vector_order_and_axis():
    data = payload({"gamma": 0.8}, vectors={"gamma": VECTOR})
    back = read_payload(data)
    assert back["vectors"]["gamma"]["populations"] == ["FRET 2", "FRET 1"]
    assert back["vectors"]["gamma"]["values"] == [0.6, 1.2]
    assert back["vectors"]["gamma"]["probabilities"]["FRET 1"] == "P(FRET 1)"
    assert json.loads(data)["vectors"]["gamma"]["column"] == "Population"
