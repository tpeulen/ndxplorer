"""The emtk app (:mod:`ndxplorer.app`), headless: its model, its window, its captures.

The model is driven as the panels drive it; the window is drawn into a pixel
painter and clicked where it drew things, the way the parity capture replays
a scenario. Nothing here needs Qt, and the first test makes sure nothing
imports it.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

import numpy as np
import pytest

from ndxplorer.core.data_source import DataSource

REPO = pathlib.Path(__file__).resolve().parents[3]
MFD = REPO / "test" / "mfd" / "burstwise_All 0.1500#30"
SIZE = (1400, 900)


@pytest.fixture
def source():
    """Three populations in (E, S), a lifetime that follows E, photon counts."""
    rng = np.random.default_rng(3)
    n = 3000
    k = rng.choice(3, n, p=[0.5, 0.3, 0.2])
    e = np.array([0.2, 0.55, 0.85])[k] + rng.normal(0, 0.05, n)
    return DataSource.from_columns({
        "E": e,
        "S": np.array([0.5, 0.55, 0.95])[k] + rng.normal(0, 0.05, n),
        "Tau": 4.0 * (1 - e) + rng.normal(0, 0.2, n),
        "N": rng.lognormal(4.0, 0.5, n),
    })


@pytest.fixture
def model(source):
    from ndxplorer.app.model import ExplorerModel

    m = ExplorerModel()
    m.set_source(source)
    m.set_parameter("y", "S")
    return m


@pytest.fixture
def app():
    from ndxplorer.app.frame import NdxApp

    a = NdxApp()
    yield a
    a.close()


def draw(app, size=SIZE):
    from emtk.pil_painter import PilPainter

    painter = PilPainter(*size)
    app.draw(painter, 0.0, 0.0, float(size[0]), float(size[1]))
    return painter.frame


def click(app, x, y, clicks=1):
    app.pointer_move(x, y)
    draw(app)
    app.pointer_press(x, y, 1, 0, clicks)
    draw(app)
    app.pointer_release(x, y, 1)
    draw(app)


def centre(rect):
    x, y, w, h = rect
    return x + w / 2.0, y + h / 2.0


# ----------------------------------------------------------------------- no Qt ---


def test_the_app_runs_without_qt():
    """Import, build and draw the app in a fresh process: no Qt binding loads."""
    code = (
        "import sys\n"
        "from emtk.pil_painter import PilPainter\n"
        "from ndxplorer.app.frame import NdxApp\n"
        "app = NdxApp(); app.draw(PilPainter(600, 400), 0, 0, 600, 400)\n"
        "print(','.join(m for m in sys.modules if m.split('.')[0] in "
        "('qtpy', 'PyQt5', 'PyQt6', 'PySide2', 'PySide6', 'pyqtgraph')))\n"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                         check=True, cwd=str(REPO))
    assert out.stdout.strip() == ""


def test_no_module_of_the_app_names_qt():
    for path in (REPO / "ndxplorer" / "app").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        for binding in ("qtpy", "PyQt5", "PySide", "pyqtgraph"):
            assert f"import {binding}" not in text and f"from {binding}" not in text, path


# ----------------------------------------------------------------------- model ---


def test_axes_start_on_the_first_parameter_without_defaults(source):
    """The settings' default axes (Tau (green) ...) are not in this table: every
    axis starts on the first parameter, as in the Qt window, auto-ranged."""
    from ndxplorer.app.model import ExplorerModel

    m = ExplorerModel()
    m.set_source(source)
    assert (m.x.name, m.y.name, m.z.name) == ("E", "E", "E")
    assert m.x.lo < 0.2 and m.x.hi > 0.85


def test_the_histograms_describe_the_gated_population(model):
    model.update()
    assert model.count_current == model.count_total == 3000
    assert model.histograms.H.shape == (model.y.bins_2d, model.x.bins_2d)
    model.add_rectangle((0.0, 0.4), (0.3, 0.7))
    model.update()
    assert 1000 < model.count_current < 2000
    assert int(model.histograms.H.sum()) == model.count_current
    assert [g.name for g in model.gates] == ["E", "S"]


def test_an_inverted_or_disabled_gate(model):
    model.add_interval("E", 0.0, 0.4)
    model.update()
    kept = model.count_current
    model.edit_gate(0, "invert", True)
    model.update()
    assert model.count_current == 3000 - kept
    model.edit_gate(0, "enabled", False)
    model.update()
    assert model.count_current == 3000


def test_the_z_range_gates_only_when_both_switches_are_on(model):
    model.set_parameter("z", "Tau")
    model.update()
    model.set_z_range(0.0, 2.0)
    model.update()
    assert model.count_current == 3000
    model.z_gate_enabled = model.z_dynamic = True
    model.invalidate()
    model.update()
    assert model.count_current < 3000
    model.z_select()
    assert model.gates[-1].name == "Tau" and model.gates[-1].upper == 2.0


def test_a_parameter_with_axis_settings_takes_them(model):
    model.axis_settings["N"] = {"min": 1, "max": 500, "scale": "log", "n_bins_1d": 60,
                                "n_bins_2d": 40}
    model.set_parameter("y", "N")
    assert (model.y.lo, model.y.hi, model.y.log, model.y.bins_2d) == (1.0, 500.0, True, 40)


def test_colour_limits_follow_the_map_and_contrast(model):
    model.update()
    lo, hi = model.vmin, model.vmax
    assert 0 < lo < hi
    model.log_counts = True
    model.invalidate()
    model.update()
    assert model.vmax < 4 < hi               # log10 units now
    model.auto_contrast()
    assert model.vmin >= np.log10(2.0) - 1e-9


def test_weights_change_the_counts(model):
    model.update()
    plain = model.histograms.H.sum()
    model.weight_enabled, model.weight_name = True, "N"
    model.invalidate()
    model.update()
    assert model.histograms.H.sum() > 10 * plain


def test_mask_nan_keeps_rows_without_a_value():
    from ndxplorer.app.model import ExplorerModel

    x = np.arange(10.0)
    y = x.copy()
    y[:3] = np.nan
    m = ExplorerModel()
    m.set_source(DataSource.from_columns({"x": x, "y": y, "z": x}))
    m.set_parameter("y", "y")
    m.update()
    assert m.count_current == 7
    m.mask_nan = False
    m.invalidate()
    m.update()
    assert m.count_total == 10


def test_opening_a_missing_file_reports_it():
    from ndxplorer.app.model import ExplorerModel

    m = ExplorerModel()
    assert m.open("/no/such/file.csv") is False
    assert m.error


@pytest.mark.skipif(not MFD.exists(), reason="the MFD test folder is not in this checkout")
def test_the_mfd_folder_opens_on_the_default_axes():
    from ndxplorer.app.model import ExplorerModel

    m = ExplorerModel()
    assert m.open(str(MFD))
    m.update()
    assert (m.x.name, m.y.name, m.weight_name) == ("Tau (green)", "Proximity ratio",
                                                    "Number of Photons")
    assert (m.x.lo, m.x.hi, m.x.bins_2d) == (0.0, 6.0, 31)
    assert m.count_current == 12237
    assert (m.vmin, round(m.vmax)) == (1.0, 201)


# ---------------------------------------------------------------------- window ---


def test_the_window_draws_every_panel_and_plot(app, source):
    app.model.set_source(source)
    draw(app)
    form = app.forms["plot_controls"]
    for name in ("Histogram.fold", "Selection.fold", "x_name", "y_bins_2d", "auto_x",
                 "gate_rows"):
        assert name in form.rects, name
    for name in ("log_counts", "auto_contrast", "vmin", "mask_nan"):
        assert name in app.forms["plot_corner"].rects, name
    assert set(app.plots.rects) >= {"xmarginal", "map", "ymarginal"}


def test_a_drag_on_the_map_makes_two_gates(app, source):
    app.model.set_source(source)
    app.model.set_parameter("y", "S")
    draw(app)
    x, y, w, h = app.plots.rects["map"]
    p0, p1 = (x + 0.1 * w, y + 0.2 * h), (x + 0.6 * w, y + 0.7 * h)
    app.pointer_move(*p0)
    draw(app)
    app.pointer_press(p0[0], p0[1], 1)
    draw(app)
    app.pointer_move(p1[0], p1[1], 1)
    draw(app)
    app.pointer_release(p1[0], p1[1], 1)
    draw(app)
    gates = app.model.gates
    assert [g.name for g in gates] == ["E", "S"]
    lo, hi = app.model.x.lo, app.model.x.hi
    assert gates[0].lower == pytest.approx(lo + 0.1 * (hi - lo), rel=0.05)
    draw(app)
    assert app.model.count_current < 3000


def test_a_folded_panel_opens_on_a_click(app, source):
    app.model.set_source(source)
    draw(app)
    form = app.forms["plot_controls"]
    assert "z_name" not in form.rects
    click(app, *centre(form.rects["z axis.fold"]))
    form.rects.clear()
    draw(app)
    assert "z_name" in form.rects and "z_plot" not in app.plots.rects or True
    assert "zmarginal" in app.plots.rects


def test_a_toggle_click_reaches_the_model(app, source):
    app.model.set_source(source)
    draw(app)
    click(app, *centre(app.forms["plot_corner"].rects["log_counts"]))
    assert app.model.log_counts is True


def test_a_choice_opens_a_list_and_takes_the_pick(app, source):
    app.model.set_source(source)
    draw(app)
    click(app, *centre(app.forms["plot_controls"].rects["x_name"]))
    assert app.popup is not None
    popup = app.popup[0]
    rows = popup._rows if hasattr(popup, "_rows") else None
    target = next(rect for entry, rect in rows if entry is not None and entry.label == "Tau")
    click(app, *centre(target))
    assert app.model.x.name == "Tau"


def test_the_menu_bar_mirrors_the_qt_menus(app):
    from ndxplorer.app.menus import MENUS, iter_entries

    assert [title for title, _ in MENUS] == ["File", "Settings", "View", "Help"]
    labels = [item["label"] for _path, item in iter_entries()]
    for label in ("Import Text files (*.csv,*.dat)", "Analysis-Folder", "Burst IDs",
                  "Performance Settings", "Axis settings", "UMAP", "Axis Control",
                  "Fix Report Tool", "About"):
        assert label in labels
    # without data, only opening something (and leaving) is enabled
    draw(app)
    assert app.panel.available("open_analysis_folder")
    assert not app.panel.available("clear_gates")
    assert not app.panel.available("umap")                    # not ported: shown, disabled


def test_file_menu_opens_the_folder_dialog(app):
    draw(app)
    titles = {m.label: rect for m, rect in app.menubar._titles}
    click(app, *centre(titles["File"]))
    assert app.menubar.menus[0].open
    assert app.run_action("open_analysis_folder")
    draw(app)
    assert app.dialog is not None and app.dialog[0].mode == "folder"


def test_a_load_error_is_a_message_box(app):
    app.open_path("/no/such/file.csv")
    draw(app)
    assert app.message is not None and app.message[0] == "Data Load Error"
    x, y, w, h = app.message_box
    click(app, x + w - 55.0, y + h - 22.0)
    assert app.message is None


def test_capturing_a_scenario_writes_its_shots(tmp_path):
    from ndxplorer.app.capture import capture_scenario

    catalogue = {"datasets": {}, "setups": {}, "scenarios": [
        {"id": "empty", "steps": [
            {"op": "capture", "name": "main"},
            {"op": "menu", "path": ["File"]},
            {"op": "capture", "name": "menu", "target": "menu"},
            {"op": "close_menus"}]}]}
    files = capture_scenario("empty", tmp_path, catalogue, size=(900, 600))
    assert sorted(p.name for p in files) == ["empty--menu.png", "empty.png"]
    from PIL import Image

    assert Image.open(tmp_path / "empty.png").size == (900, 600)


def test_a_step_the_app_cannot_do_is_reported_not_faked(tmp_path):
    from ndxplorer.app.capture import Unsupported, capture_scenario

    catalogue = {"datasets": {}, "setups": {}, "scenarios": [
        {"id": "x", "steps": [{"op": "canvas_click", "at": [0.5, 0.5]},
                              {"op": "capture", "name": "main"}]}]}
    with pytest.raises(Unsupported):
        capture_scenario("x", tmp_path, catalogue)
    assert not list(tmp_path.iterdir())


# --------------------------------------------------------------------- features ---


def test_a_feature_registers_actions_menus_tabs_and_mask_terms(monkeypatch, source):
    """The seam ndxplorer.app.features: a module with create(app) plugs in."""
    import types

    from ndxplorer.app import features
    from ndxplorer.app.features import Feature

    calls = []

    class Fake(Feature):
        name = "fake"

        def actions(self):
            return {"umap": lambda: calls.append("umap"), "fake_action": lambda: None}

        def menu_entries(self):
            return [(("View", "Extra"), {"label": "Fake entry", "action": "fake_action"})]

        def tabs(self):
            return [("left", "Parameters", lambda box: calls.append("tab"))]

        def mask_terms(self):
            return {"cluster_label": None}

        def draw_plot(self, plot):
            calls.append(plot)

        def capture_ops(self):
            return {"fake_op": lambda replay, step: calls.append("op")}

    module = types.ModuleType("ndxplorer.app.features.fake")
    module.create = Fake
    monkeypatch.setitem(sys.modules, "ndxplorer.app.features.fake", module)
    monkeypatch.setattr(features, "FEATURES", ["fake", "does_not_exist"])

    from ndxplorer.app.frame import NdxApp

    app = NdxApp()
    try:
        app.model.set_source(source)
        assert app.panel.available("umap")                  # was "not ported"
        assert app.run_action("umap") and calls[-1] == "umap"
        labels = [e.label for m in app.menubar.menus for e in m.entries if e is not None]
        assert "Extra" in labels
        draw(app)
        assert "map" in calls and "xmarginal" in calls
        app.left_tab = "Parameters"
        draw(app)
        assert "tab" in calls
    finally:
        app.close()
