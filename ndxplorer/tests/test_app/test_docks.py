"""ndX's docks are sticky windows (ndxplorer.app.docks over emtk.docking).

The first start is the Qt window's layout; the View menu shows and hides each
window (in the Qt window those toggles did nothing); the layout is kept in
the settings folder -- and only when the app is asked to keep it.
"""
from __future__ import annotations

import json
import pathlib

import pytest

pytest.importorskip("emtk.docking")

SIZE = (1400.0, 900.0)


def draw(app, frames: int = 2):
    from emtk.testing import RecordingPainter

    for _ in range(frames):
        app.draw(RecordingPainter(), 0.0, 0.0, *SIZE)


@pytest.fixture()
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    return tmp_path


def make(**kwargs):
    from ndxplorer.app.frame import NdxApp

    return NdxApp(**kwargs)


def test_the_first_start_is_the_qt_windows_layout(home):
    app = make()
    draw(app)
    docks = app.docks
    assert docks.docked("left")[:3] == ["Plot controls", "Parameters", "Overlays"]
    assert docks.docked("right") == ["Plot"]
    assert docks.active_tab("left") == "Plot controls"
    # The windows View opens are there, hidden: no tab until asked for.
    assert {"Equations", "Gaussian Fit"} <= set(docks.docked("left"))
    assert not docks.is_visible("Equations") and not docks.is_visible("Gaussian Fit")
    shown = [k for k, _r in docks._tab_rects["left"]]
    assert shown == ["Plot controls", "Parameters", "Overlays"]
    left, right = docks.region_boxes["left"], docks.region_boxes["right"]
    assert left[0] == 0.0 and right[0] + right[2] == SIZE[0]
    assert set(app.plot_boxes) >= {"header", "map", "xmarginal", "ymarginal", "corner"}


def test_the_view_menu_toggles_every_window(home):
    app = make()
    draw(app)
    for action, title in (("toggle_plot_controls", "Plot controls"), ("toggle_plot", "Plot"),
                          ("toggle_parameters", "Parameters"), ("toggle_overlays", "Overlays"),
                          ("toggle_equations", "Equations")):
        app.docks.focus(title)
        draw(app)
        assert app.docks.is_shown(title)
        assert app.run_action(action)            # shown and on top: put away
        draw(app)
        assert not app.docks.is_visible(title), title
        assert app.run_action(action)            # and back, on top
        draw(app)
        assert app.docks.is_shown(title), title


def test_a_tab_under_another_is_brought_up_not_hidden(home):
    app = make()
    draw(app)
    assert app.docks.active_tab("left") == "Plot controls"
    assert app.run_action("toggle_parameters")
    assert app.docks.is_shown("Parameters")


def test_the_view_ticks_follow_the_windows(home):
    app = make()
    draw(app)
    assert app.panel.show_plot_controls and app.panel.show_plot and app.panel.show_parameters
    app.docks.hide("Parameters")
    assert not app.panel.show_parameters
    app.panel.show_equations = True
    assert app.docks.is_shown("Equations")


def test_closing_with_the_cross_hides_and_view_reopens(home):
    app = make()
    draw(app)
    x, y, w, _h = app.docks.region_boxes["left"]
    th = app.docks._title_h
    app.pointer_press(x + w - th / 2.0, y + th / 2.0, 1, 0, 1)
    draw(app, 1)
    app.pointer_release(x + w - th / 2.0, y + th / 2.0, 1, 0)
    draw(app)
    assert not app.docks.is_visible("Plot controls")
    assert app.run_action("toggle_plot_controls")
    draw(app)
    assert app.docks.is_shown("Plot controls")


def test_the_layout_is_kept_in_the_settings_folder(home):
    from ndxplorer.app.docks import LAYOUT_FILE, layout_store

    app = make(layout_store=layout_store())
    draw(app)
    app.docks.undock("Overlays", (600.0, 200.0, 300.0, 250.0))
    app.docks.hide("Parameters")
    draw(app)
    path = home / ".ndxplorer" / LAYOUT_FILE
    saved = json.loads(path.read_text())
    assert saved["windows"]["Overlays"]["dock"] is None
    again = make(layout_store=layout_store())
    draw(again)
    assert again.docks.region_of("Overlays") is None
    assert not again.docks.is_visible("Parameters")
    assert again.run_action("reset_layout")
    draw(again)
    assert again.docks.region_of("Overlays") == "left" and again.docks.is_visible("Parameters")


def test_without_a_store_nothing_is_read_or_written(home):
    """Tests and a bare Replay must never touch the user's layout."""
    from ndxplorer.app.capture import Replay

    folder = home / ".ndxplorer"
    folder.mkdir()
    (folder / "ndxplorer_layout.json").write_text(json.dumps(
        {"windows": {"Plot controls": {"visible": False}}}))
    replay = Replay({"id": "x", "steps": []}, {"scenarios": []}, size=(600, 400))
    replay.draw()
    assert replay.app.docks.is_visible("Plot controls")
    replay.app.docks.hide("Parameters")
    replay.draw()
    assert "Parameters" not in json.loads((folder / "ndxplorer_layout.json").read_text())["windows"]
    assert [p.name for p in pathlib.Path(folder).glob("*layout*")] == ["ndxplorer_layout.json"]
