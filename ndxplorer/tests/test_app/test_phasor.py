"""The Phasor / FRET window: off without ChiSurf, and what it draws with it.

A fake RPC client stands in for ChiSurf (``call(method, params)``, the
contract ``ndxplorer.rpc`` speaks), so the feature is tested without chisurf.
"""

from __future__ import annotations

import numpy as np
import pytest


class FakeChiSurf:
    """Answers the phasor.* and fret_line.* calls the panel makes."""

    def __init__(self):
        self.calls = []

    def call(self, method, params):
        self.calls.append((method, params))
        if method == "phasor.overlays":
            t = np.linspace(0.0, np.pi, 20)
            return {"ok": True, "result": {"overlays": [
                {"name": "universal semicircle", "kind": "curve",
                 "x": list(0.5 + 0.5 * np.cos(t)), "y": list(0.5 * np.sin(t)),
                 "style": {"color": "w"}},
                {"name": "ticks", "kind": "scatter", "x": [0.8, 0.5], "y": [0.4, 0.5],
                 "labels": ["1 ns", "2 ns"], "style": {"color": "#ffd000"}}]}}
        if method == "fret_line.list_models":
            return {"ok": True, "result": ["FRET: FD (Gaussian)"]}
        if method == "fret_line.list_sweep_targets":
            return {"ok": True, "result": {"targets": [{"name": "distance.mean.0"}]}}
        if method == "fret_line.overlays":
            return {"ok": True, "result": {"overlays": [
                {"kind": "curve", "x": [0.1, 0.2, 0.3], "y": [0.3, 0.35, 0.4]}]}}
        if method == "phasor.apparent_lifetime":
            n = len(params["g"])
            return {"ok": True, "result": {"tau_phi": [1.0] * n, "tau_m": [2.0] * n}}
        return {"ok": False, "error": f"unknown {method}"}


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("NDXPLORER_SETTINGS_DIR", str(tmp_path))
    from ndxplorer.app.frame import NdxApp
    from ndxplorer.core.data_source import DataSource

    a = NdxApp(features=["phasor"])
    rng = np.random.default_rng(1)
    a.model.set_source(DataSource.from_columns({
        "g (green)": rng.uniform(0.2, 0.9, 200), "s (green)": rng.uniform(0.1, 0.5, 200)}))
    return a


def _frame(app):
    from emtk.testing import RecordingPainter

    app.draw(RecordingPainter(), 0.0, 0.0, 1400.0, 900.0)


def test_without_chisurf_the_panel_is_off_and_says_why(app):
    from ndxplorer.app.features.phasor import NO_RPC

    assert not app.panel.available("show_phasor_panel")
    feature = app.features[0]
    assert feature.panel.reason == NO_RPC and not feature.panel.usable
    _frame(app)


def test_with_chisurf_it_draws_overlays_and_a_fret_line(app):
    from ndxplorer.app.features.phasor import WINDOW

    app.chisurf_rpc = FakeChiSurf()
    assert app.panel.available("show_phasor_panel")
    assert app.run_action("show_phasor_panel")
    assert app.docks.is_visible(WINDOW)
    feature = app.features[0]
    app.model.set_parameter("x", "g (green)")
    app.model.set_parameter("y", "s (green)")
    feature.panel.draw_overlays()
    assert len(feature.line_sets["phasor"]) == 2
    assert feature.panel.fret_models() == ["FRET: FD (Gaussian)"]
    assert feature.panel.sweep_params() == ["distance.mean.0"]
    feature.panel.draw_fret_line()
    assert len(feature.line_sets["fret"]) == 1
    _frame(app)                     # drawn over the map, data coordinates
    assert app.panel.available("clear_phasor_overlays")
    app.run_action("clear_phasor_overlays")
    assert not feature.line_sets


def test_overlays_need_phasor_axes(app):
    app.chisurf_rpc = FakeChiSurf()
    feature = app.features[0]
    app.model.set_parameter("x", "s (green)")
    feature.draw_overlays()
    assert not feature.line_sets
    assert "(g, s)" in app.status


def test_apparent_lifetime_columns_are_added(app):
    app.chisurf_rpc = FakeChiSurf()
    app.features[0].panel.lifetime_columns()
    names = app.model.source.parameter_names
    assert "tau_phi" in names and "tau_m" in names
    np.testing.assert_allclose(app.model.source.column_values("tau_m"), 2.0)
