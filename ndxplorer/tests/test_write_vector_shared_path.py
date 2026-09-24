"""The emtk FRET calibration writes a vector through the stored-vector path.

``AccurateFretFeature.write_vector`` used to repeat the handling of
uncertainties keyed by population that
:func:`ndxplorer.core.constants_group.apply_vector_entries` already does. It now
calls that function (through ``ConstantsMapping.apply_vectors``), so there is
one place that reads a stored or calibrated vector.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from ndxplorer.app.features.accurate_fret import AccurateFretFeature
from ndxplorer.core import constants_group as cg

VECTOR = {"values": [0.6, 1.2], "populations": ["FRET 1", "FRET 2"],
          "uncertainties": {"FRET 2": 0.03, "FRET 1": 0.01}, "default": 0.8,
          "column": "Population", "codes": {"FRET 1": 1, "FRET 2": 2}}


def _feature(mapping):
    app = SimpleNamespace(model=SimpleNamespace(manager=SimpleNamespace(constants=mapping)))
    return SimpleNamespace(app=app)


def test_write_vector_goes_through_apply_vector_entries(monkeypatch):
    mapping = cg.ConstantsMapping(cg.build_constants_group({"gG/gR": 0.6}))
    calls = []
    shared = cg.apply_vector_entries
    monkeypatch.setattr(cg, "apply_vector_entries",
                        lambda group, vectors: calls.append(vectors) or shared(group, vectors))
    AccurateFretFeature.write_vector(_feature(mapping), "gamma", VECTOR)
    assert calls == [{"gamma": VECTOR}]
    gamma = mapping.group.get("gamma")
    assert gamma.populations == ["FRET 1", "FRET 2"] and gamma.value == pytest.approx(0.8)
    # uncertainties by population land on the right elements
    assert gamma.element("FRET 1").error_estimate == pytest.approx(0.01)
    assert gamma.element("FRET 2").error_estimate == pytest.approx(0.03)
    assert gamma.vector_state()["codes"] == {"FRET 1": 1.0, "FRET 2": 2.0}


def test_write_vector_ignores_constants_without_vectors():
    AccurateFretFeature.write_vector(_feature({"gamma": 1.0}), "gamma", VECTOR)
