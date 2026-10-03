"""Tabulated lines from another tool (ChiSurf's FRET lines) as overlay curves.

A host pushes a LineSet (``{"name", "x", "y", "style"}`` per line) with
``NdxApp.add_overlay_lines``; each line is a *data* curve of the Overlays tab:
named, coloured, drawn on the map, removable and kept in the session.
"""

from __future__ import annotations

import numpy as np
import pytest

TAU = np.linspace(0.2, 4.0, 40)
E = 1 - TAU / 4.0


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("NDXPLORER_SETTINGS_DIR", str(tmp_path))
    from ndxplorer.app.frame import NdxApp
    from ndxplorer.core.data_source import DataSource

    a = NdxApp(features=["overlays"])
    rng = np.random.default_rng(3)
    tau = rng.uniform(0.2, 4.0, 400)
    a.model.set_source(DataSource.from_columns({"tau": tau, "E": 1 - tau / 4.0
                                                + rng.normal(0, 0.05, tau.size)}))
    a.model.set_parameter("x", "tau")
    a.model.set_parameter("y", "E")
    _frame(a)
    yield a
    a.close()


def _frame(app):
    from emtk.testing import RecordingPainter

    painter = RecordingPainter()
    app.draw(painter, 0.0, 0.0, 1400.0, 900.0)
    return painter


def feature(app):
    return next(f for f in app.features if f.name == "overlays")


LINE = {"name": "FRET line — static", "kind": "curve", "x": TAU.tolist(), "y": E.tolist(),
        "style": {"color": "#00aa55", "width": 2}}


def test_a_pushed_line_is_a_named_coloured_data_curve_drawn_as_given(app):
    titles = app.add_overlay_lines([LINE], source="ChiSurf FRET lines")
    _frame(app)
    assert titles == ["FRET line — static"]
    (curve,) = feature(app).overlays.curves
    assert curve.kind == "data" and curve.color == "#00aa55"
    assert curve.group.parameters_all == []
    assert curve.filled == "40 tabulated points from ChiSurf FRET lines"
    hist = app.model.histograms
    ((name, colour, x, y),) = curve.drawn_curves(500, hist.x_edges, hist.y_edges)
    keep = (E >= hist.y_edges[0]) & (E <= hist.y_edges[-1])
    np.testing.assert_allclose(x, TAU[keep])
    np.testing.assert_allclose(y, E[keep])
    assert "Added 1 line(s)" in app.status


def test_pushing_again_updates_the_line_and_remove_deletes_it(app):
    app.add_overlay_lines([LINE])
    feature(app).overlays.curves[0].visible = False
    app.add_overlay_lines([dict(LINE, y=(E / 2).tolist())])
    (curve,) = feature(app).overlays.curves
    assert not curve.visible
    np.testing.assert_allclose(curve.function()[1], E / 2)
    assert app.remove_overlay_line("FRET line — static")
    assert not app.remove_overlay_line("FRET line — static")
    assert feature(app).overlays.curves == []


def test_a_data_line_cannot_be_fitted_and_shows_no_equation(app):
    app.add_overlay_lines([LINE])
    _frame(app)
    (panel,) = feature(app).overlays.panels
    assert not panel.enabled("fit") and panel.enabled("delete")
    attrs = {s.get("attr") for s in _walk(panel.spec()["sections"])}
    assert "text" not in attrs and "x_expr" not in attrs and "filled" in attrs


def test_a_data_line_survives_the_session(app):
    app.add_overlay_lines([LINE], source="ChiSurf FRET lines")
    state = feature(app).session_state()
    assert state["curves"][0]["kind"] == "data"
    feature(app).overlays.clear()
    feature(app).restore_session_state(state, _Context())
    (curve,) = feature(app).overlays.curves
    assert curve.kind == "data" and curve.title == "FRET line — static"
    np.testing.assert_allclose(curve.function()[0], TAU)


def test_live_apps_lists_an_app_until_it_closes(app):
    from ndxplorer.app.frame import live_apps

    assert app in live_apps()
    app.close()
    assert app not in live_apps()


def test_bad_lines_are_refused():
    from ndxplorer.core.overlay_curves import data_spec

    with pytest.raises(ValueError):
        data_spec([1, 2], [1])
    with pytest.raises(ValueError):
        data_spec([1], [1])


def test_rpc_lines_push_draws_a_provider_lineset(app):
    from ndxplorer.rpc.lines import LinesService

    class Client:
        def call(self, method, params):
            assert method == "fret_line.overlays"
            return {"ok": True, "result": {"overlays": [LINE]}}

    assert LinesService(Client()).push(app, "fret_line", line="static") == [LINE["name"]]
    assert feature(app).overlays.curves[0].kind == "data"


class _Context:
    newer_calibration = False

    def skip(self, _what):
        pass


def _walk(sections):
    for s in sections:
        yield s
        yield from _walk(s.get("sections") or [])
