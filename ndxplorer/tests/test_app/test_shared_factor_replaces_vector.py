"""A calibration's shared factor replaces a population-wise one.

A window can hold a vector of a factor from before -- the cal1 container ships
a stored ``gamma`` (0.4536 / 0.8090) that is restored on open. A run whose
model selection kept one shared γ writes it as a scalar; the old vector must
not stay behind, or the equations go on reading its stale elements. The rule
lives in the constants API
(:func:`ndxplorer.core.constants_group.replace_shared_factors`), which both the
emtk app and the Qt window call.
"""

from __future__ import annotations

import pytest
from ndxplorer.core import constants_group as cg
from ndxplorer.core.equation_graph import constant_vectors

STORED = {"values": [0.4536, 0.8090], "populations": ["FRET 1", "FRET 2"],
          "uncertainties": {"FRET 1": 0.01, "FRET 2": 0.02}, "column": "Population"}


def _result(**extra):
    return {"ok": True, "constants": {"gG/gR": 0.9, "alpha": 0.05},
            "factors": {"alpha": 0.05, "beta": 1.1, "gamma": 0.62, "delta": 0.07,
                        "r0": 52.0},
            "applied_factors": ["alpha", "beta", "gamma", "delta"], "vectors": {},
            "report": "Automatic FRET calibration (test)", **extra}


def test_a_scalar_gamma_replaces_the_stored_vector():
    group = cg.build_constants_group({"gG/gR": 0.6, "alpha": 0.0})
    cg.apply_vector_entries(group, {"gamma": STORED})
    mapping = cg.ConstantsMapping(group)
    assert "gamma" in constant_vectors(mapping)
    result = _result()
    assert mapping.replace_shared_factors(result) == ["gamma"]
    assert not group.get("gamma").is_vector and mapping["gamma"] == pytest.approx(0.62)
    assert "gamma" not in constant_vectors(mapping) and "gamma[FRET 1]" not in mapping
    assert result["replaced_vectors"] == ["gamma"]
    assert "Replaced population-wise γ with shared γ = 0.6200" in result["report"]


def test_a_run_writing_gamma_per_population_keeps_it_a_vector():
    group = cg.build_constants_group({"gG/gR": 0.6})
    cg.apply_vector_entries(group, {"gamma": STORED})
    result = _result(vectors={"gamma": dict(STORED, values=[0.5, 0.9])})
    assert cg.replace_shared_factors(group, result) == []
    assert group.get("gamma").is_vector and "replaced_vectors" not in result


def test_a_held_gamma_leaves_the_vector_alone():
    group = cg.build_constants_group({"gG/gR": 0.6})
    cg.apply_vector_entries(group, {"gamma": STORED})
    result = _result(applied_factors=["alpha", "beta", "delta"])
    assert cg.replace_shared_factors(group, result) == []
    assert group.get("gamma").populations == ["FRET 1", "FRET 2"]


def test_the_emtk_app_applies_a_shared_run_over_a_restored_vector(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    from ndxplorer.app import capture

    run = capture.Replay({"id": "t", "setup": "mfd", "steps": []}, capture.load_catalogue())
    run.run()
    run.settle(3)
    try:
        fret = next(f for f in run.app.features if f.name == "accurate_fret")
        fret.write_vector("gamma", STORED)                   # as restored on open
        constants = run.app.model.manager.constants
        assert constants["gamma[FRET 2]"] == pytest.approx(0.8090)
        fret.finish(_result())
        run.settle(2)
        assert "gamma" not in constant_vectors(constants)
        assert constants["gamma"] == pytest.approx(0.62)
        assert constants["gG/gR"] == pytest.approx(0.9)
        assert "Replaced population-wise γ with shared γ" in fret.window.report_text
    finally:
        run.app.close()
