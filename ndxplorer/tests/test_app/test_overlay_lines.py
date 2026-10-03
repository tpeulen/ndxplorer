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


def test_axis_hints_select_the_projection_before_drawing(app):
    app.model.set_parameter("x", "E")
    app.model.set_parameter("y", "tau")
    _frame(app)

    app.add_overlay_lines([dict(LINE, axes={"x": "tau", "y": "E"})])
    _frame(app)

    assert (app.model.x.name, app.model.y.name) == ("tau", "E")
    assert feature(app).overlays.curves[0].kind == "data"


@pytest.mark.parametrize(
    "columns, expected",
    [
        ({"Tau (green)": TAU, "FRET efficiency": E},
         ("Tau (green)", "FRET efficiency")),
        ({"tau_f (ns)": TAU, "E": E}, ("tau_f (ns)", "E")),
        ({"tau_x (ns)": TAU, "FRET efficiency(PIE)": E},
         ("tau_x (ns)", "FRET efficiency(PIE)")),
    ],
)
def test_provider_quantity_names_resolve_to_table_columns(app, columns, expected):
    from ndxplorer.core.data_source import DataSource

    app.model.set_source(DataSource.from_columns(columns))
    app.model.set_parameter("x", expected[1])
    app.model.set_parameter("y", expected[0])
    quantity = "tau_x" if expected[0].startswith("tau_x") else "tau_f"

    app.add_overlay_lines([dict(LINE, axes={"x": quantity, "y": "e_fret"})])

    assert (app.model.x.name, app.model.y.name) == expected


@pytest.mark.parametrize(
    "axes, extra",
    [
        ({"x": "tau", "y": "missing"}, {}),
        ({"x": "tau", "y": "tau"}, {}),
        ({"x": "tau_f", "y": "E"}, {"Tau (green)": TAU, "tau_f (ns)": TAU}),
        ({"x": "tau", "y": "e_fret"}, {"Proximity ratio": E}),
        ({"x": "tau"}, {}),
    ],
)
def test_unusable_axis_hints_are_refused_without_changing_the_view(app, axes, extra):
    from ndxplorer.core.data_source import DataSource

    columns = {"tau": TAU, "E": E}
    if axes.get("y") == "e_fret":
        columns.pop("E")
    columns.update(extra)
    app.model.set_source(DataSource.from_columns(columns))
    before = (app.model.x.name, app.model.y.name)

    with pytest.raises(ValueError, match="overlay axes"):
        app.add_overlay_lines([dict(LINE, axes=axes)])

    assert (app.model.x.name, app.model.y.name) == before
    assert feature(app).overlays.curves == []


@pytest.mark.parametrize(
    "second",
    [
        dict(LINE, name="other projection", axes={"x": "E", "y": "tau"}),
        dict(LINE, name="bad data", x=[1, 2], y=[1]),
    ],
)
def test_a_bad_batch_does_not_add_lines_or_switch_axes(app, second):
    app.model.set_parameter("x", "E")
    app.model.set_parameter("y", "tau")
    before = (app.model.x.name, app.model.y.name)
    first = dict(LINE, axes={"x": "tau", "y": "E"})

    with pytest.raises(ValueError):
        app.add_overlay_lines([first, second])

    assert (app.model.x.name, app.model.y.name) == before
    assert feature(app).overlays.curves == []


def test_a_hinted_line_keeps_its_projection_in_the_session_and_draws_only_there(app, monkeypatch):
    from emtk import implot

    app.add_overlay_lines([dict(LINE, axes={"x": "tau", "y": "E"})])
    state = feature(app).session_state()
    assert state["curves"][0]["spec"]["axes"] == {"x": "tau", "y": "E"}
    feature(app).restore_session_state(state, _Context())
    calls = []
    monkeypatch.setattr(implot, "plot_line", lambda title, *a, **kw: calls.append(title))
    _frame(app)
    assert any(title.startswith("##overlay-curve") for title in calls)

    calls.clear()
    app.model.set_parameter("x", "E")
    app.model.set_parameter("y", "tau")
    _frame(app)
    assert not any(title.startswith("##overlay-curve") for title in calls)
    assert feature(app).overlays.curves[0].visible

    calls.clear()
    app.model.set_parameter("x", "tau")
    app.model.set_parameter("y", "E")
    _frame(app)
    assert any(title.startswith("##overlay-curve") for title in calls)


def test_overlay_export_omits_lines_from_another_projection(app, monkeypatch, tmp_path):
    app.add_overlay_lines([dict(LINE, axes={"x": "tau", "y": "E"})])
    app.model.set_parameter("x", "E")
    app.model.set_parameter("y", "tau")
    _frame(app)
    output = tmp_path / "wrong_projection.csv"
    monkeypatch.setattr(feature(app), "ask_save", lambda *a: a[-1](str(output)))

    feature(app).overlays.save_csv()

    assert not output.exists()
    assert app.message == ("Save Overlays", "No visible curves to save.")


@pytest.mark.parametrize("factory", [np.asarray, iter])
def test_coordinate_arrays_and_iterators_are_materialized_before_switching_axes(app, factory):
    app.model.set_parameter("x", "E")
    app.model.set_parameter("y", "tau")
    line = dict(LINE, x=factory(TAU), y=factory(E), axes={"x": "tau", "y": "E"})

    assert app.add_overlay_lines([line]) == [LINE["name"]]

    np.testing.assert_allclose(feature(app).overlays.curves[0].function()[0], TAU)
    assert (app.model.x.name, app.model.y.name) == ("tau", "E")


@pytest.mark.parametrize(
    "names, quantity, expected",
    [(["E", "e"], "e", "e"), (["Tau", "tau"], "TAU", None)],
)
def test_literal_names_take_precedence_and_casefolded_ambiguity_is_refused(names, quantity, expected):
    from ndxplorer.app.overlay_axes import resolve_axis

    assert resolve_axis(names, quantity) == expected


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
    tables = [s for s in _walk(panel.spec()["sections"]) if s.get("key") == "data_table"]
    assert tables == []  # no parameters to list
    feature(app).overlays.equation_choice = "Universal circle"
    feature(app).overlays.add_curve()
    circle = feature(app).overlays.panels[-1]
    assert [s for s in _walk(circle.spec()["sections"]) if s.get("key") == "data_table"]


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
