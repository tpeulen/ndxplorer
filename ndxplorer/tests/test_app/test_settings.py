"""The settings feature of the emtk app: Settings, Axis Control, the report tool, Help.

Driven headlessly, through the actions, the dialogs' models and the io
service's file dialogs (answered as a user would), with a scratch HOME so the
user's own ``~/.ndxplorer`` is never touched.
"""

from __future__ import annotations

import json
import pathlib
import shutil

import pytest

REPO = pathlib.Path(__file__).resolve().parents[3]
MFD = REPO / "test" / "mfd" / "burstwise_All 0.1500#30"
SIZE = (1400, 900)


@pytest.fixture
def home(tmp_path, monkeypatch):
    """A scratch HOME: the settings folder is ``<tmp>/home/.ndxplorer``."""
    path = tmp_path / "home"
    path.mkdir()
    monkeypatch.setenv("HOME", str(path))
    from ndxplorer.utils import performance_config

    performance_config.reset_performance_config()
    yield path
    performance_config.reset_performance_config()


@pytest.fixture
def app(home):
    from ndxplorer.app.frame import NdxApp

    a = NdxApp()
    yield a
    a.close()


def draw(app, frames: int = 1):
    from emtk.pil_painter import PilPainter

    for _ in range(frames):
        painter = PilPainter(*SIZE)
        app.draw(painter, 0.0, 0.0, float(SIZE[0]), float(SIZE[1]))
    return painter.frame


def feature(app):
    return next(f for f in app.features if f.name == "settings")


def open_mfd(app):
    assert app.open_path(str(MFD)), app.model.error
    draw(app, 2)


# ------------------------------------------------------------------ menus
def test_every_settings_view_and_help_entry_is_provided(app):
    for action in ("performance_settings", "load_settings", "save_axis_settings",
                   "save_constants", "save_equations", "set_default_axis", "axis_control",
                   "make_report", "help", "about", "update_app"):
        assert action in app.panel.actions, action
    # Without data: only what needs the axes waits.
    assert app.panel.available("load_settings") and app.panel.available("make_report")
    assert app.panel.available("help") and app.panel.available("axis_control")
    assert not app.panel.available("set_default_axis")
    assert not app.panel.available("save_axis_settings")


def test_help_about_and_update_open_a_window(app):
    for action, title in (("help", "ndXplorer Help"), ("about", "About ndXplorer"),
                          ("update_app", "Update")):
        assert app.run_action(action)
        window = feature(app).window
        assert window.title == title and window.text
        draw(app)
        window.ok()
        draw(app)
        assert feature(app).window is None



# --------------------------------------------------------- axis settings
def test_a_parameter_with_stored_axis_settings_takes_them(app):
    """mfd.axis.json says Fd/Fa is log, 0.1..500: choosing it on x says so too."""
    open_mfd(app)
    names = app.model.parameter_names
    assert "Fd/Fa" in names
    app.panel.x_name = "Fd/Fa"
    x = app.model.x
    assert x.log and (x.lo, x.hi) == (0.1, 500.0) and x.bins_2d == 31


def test_save_axis_settings_writes_the_axes_in_use(app, tmp_path):
    open_mfd(app)
    app.panel.x_name = "Fd/Fa"
    app.panel.x_min = 0.2
    assert app.run_action("save_axis_settings")
    service = app.io_service
    assert service.busy and service.current.kind == "save"
    target = tmp_path / "mine.axis.json"
    service.answer(str(target))
    data = json.loads(target.read_text())
    assert data["Fd/Fa"]["min"] == 0.2 and data["Fd/Fa"]["scale"] == "log"
    assert "r Experimental (green)" in data          # the packaged entries stay


def test_set_default_axis_stores_the_axes_and_says_so(app, home):
    open_mfd(app)
    app.panel.x_name = "Fd/Fa"
    app.panel.weight_name = app.model.parameter_names[1]
    assert app.run_action("set_default_axis")
    assert app.message == ("Set default axis", "Default axis settings have been updated.")
    data = json.loads((home / ".ndxplorer" / "mfd.settings.json").read_text())
    assert data["default_axes"]["x"] == "Fd/Fa"
    assert data["default_axes"]["weight"] == app.model.parameter_names[1]
    assert data["colormap"] == app.model.colormap
    assert data["equations"] == "mfd.equations.yaml"      # the rest of the file stays


def test_load_settings_applies_colormap_axes_and_equations(app, tmp_path):
    from ndxplorer.settings.bundle import PACKAGED_SETTINGS

    folder = tmp_path / "other"
    folder.mkdir()
    for name in ("mfd.axis.json", "mfd.constants.json", "axis_labels.yaml"):
        shutil.copy(PACKAGED_SETTINGS.parent / name, folder / name)
    (folder / "extra.equations.yaml").write_text("- Double S: >-\n    'Sg' * 2\n")
    settings = json.loads(PACKAGED_SETTINGS.read_text())
    settings.update(colormap="magma", equations="extra.equations.yaml")
    axis = json.loads((folder / "mfd.axis.json").read_text())
    axis["Tau (green)"] = {"n_bins_1d": 50, "n_bins_2d": 20, "min": 1.0, "max": 3.0,
                           "scale": "lin"}
    (folder / "mfd.axis.json").write_text(json.dumps(axis))
    path = folder / "mine.settings.json"
    path.write_text(json.dumps(settings))

    open_mfd(app)
    assert app.run_action("load_settings")
    app.io_service.answer(str(path))
    model = app.model
    assert model.colormap == "magma"
    assert model.axis_settings["Tau (green)"]["max"] == 3.0
    assert model.manager.equations == [{"Double S": "'Sg' * 2"}]
    assert "Double S" in model.parameter_names
    assert feature(app).settings_file == path


def test_save_constants_and_equations(app, home, tmp_path):
    open_mfd(app)
    constants = dict(app.model.manager.constants)
    constants["gG/gR"] = 0.77
    app.model.manager.constants = constants              # as Load settings hands them over
    draw(app)
    assert app.run_action("save_constants")
    written = json.loads((home / ".ndxplorer" / "mfd.constants.json").read_text())
    from ndxplorer.core.constants_group import values_from_data

    assert values_from_data(written)["gG/gR"] == 0.77
    assert app.run_action("save_equations")
    target = tmp_path / "eq.yaml"
    app.io_service.answer(str(target))
    from ndxplorer.settings.bundle import read_settings

    settings = tmp_path / "t.settings.json"
    settings.write_text(json.dumps({"equations": "eq.yaml"}))
    assert read_settings(settings).equations == list(app.model.manager.equations)


# ------------------------------------------------------------ axis control
def test_axis_control_applies_axes_titles_and_colour(app, home):
    open_mfd(app)
    assert app.run_action("axis_control")
    dialog = feature(app).window
    display = app.model.axis_display
    assert dialog.x_top and not dialog.x_bottom and dialog.y_right
    assert not dialog.enabled("overlay_top")               # the overlay has no axes
    assert not dialog.enabled("z_bottom")                  # until Enable Z Plot
    dialog.z_enable = True
    assert dialog.enabled("z_bottom")
    dialog.map_bottom = True
    dialog.enable_all_labels = False
    assert dialog.enabled("x_label_top")
    dialog.x_label_top = False
    dialog.title_color = "#00ff00"
    assert display.visible("map", "bottom") is False       # not until Apply
    dialog.apply()
    assert display.visible("map", "bottom") and not display.label("xmarginal", "top")
    assert display.title_colour[:3] == (0, 255, 0)
    assert app.panel.z_gate_enabled
    dialog.save()
    text = (home / ".ndxplorer" / "axis_labels.yaml").read_text()
    assert "'#00ff00'" in text and "enable_all_labels: false" in text
    dialog.ok()
    draw(app)
    assert feature(app).window is None


def test_axis_control_cancel_changes_nothing(app):
    assert app.run_action("axis_control")
    dialog = feature(app).window
    dialog.map_left = True
    dialog.cancel()
    assert not app.model.axis_display.visible("map", "left")


def test_the_dialog_is_drawn_with_every_control(app):
    open_mfd(app)
    assert app.run_action("axis_control")
    draw(app)
    rects = feature(app).window.form.rects
    for name in ("x_bottom", "x_top", "y_right", "z_enable", "z_left", "map_bottom",
                 "overlay_right", "enable_all_labels", "y_label_top", "y_label_right",
                 "x_label_top", "z_label_bottom", "z_label_left", "title_color",
                 "title_color.swatch", "ok", "save", "cancel", "apply"):
        assert name in rects, name


# ------------------------------------------------------------- performance
def test_performance_settings_apply_saves_and_reset_shows_defaults(app, home):
    from ndxplorer.utils.performance_config import get_performance_config

    assert app.run_action("performance_settings")
    dialog = feature(app).window
    draw(app)
    for name in ("use_fast_histogram", "parallel_histogram", "histogram_threads",
                 "aggressive_caching", "general_cache_mb", "reset", "cancel", "apply", "ok"):
        assert name in dialog.form.rects, name
    dialog.histogram_threads = 3
    dialog.aggressive_caching = False
    dialog.apply()
    assert app.message[0] == "Settings Applied"
    env = json.loads((home / ".ndxplorer" / "mfd.settings.json").read_text())["environment"]
    assert env["NDXPLORER_HISTOGRAM_THREADS"] == 3
    assert env["NDXPLORER_AGGRESSIVE_CACHING"] is False
    assert get_performance_config().histogram_threads == 3
    dialog.reset()
    feature(app).question.yes()
    assert dialog.histogram_threads == -1 and dialog.aggressive_caching


# ------------------------------------------------------------- report tool
@pytest.fixture
def analysis(tmp_path):
    target = tmp_path / "sample" / "burstwise"
    shutil.copytree(MFD, target)
    return target


def test_the_report_tool_generates_clears_and_browses(app, analysis):
    assert app.run_action("make_report")
    tool = feature(app).window
    assert "plots:" in tool.config_text
    tool.add_folder()
    app.io_service.answer(str(analysis.parent))            # a folder above the analysis
    assert tool.folders == [str(analysis.parent)]
    draw(app)
    assert not tool.folder_rows()[0]["processed"]
    tool.generate()
    assert tool.job is not None and tool.job["targets"] == [analysis]
    for _ in range(10):
        draw(app)
        if tool.job is None:
            break
    assert tool.job is None and tool.last_status.startswith("Reports generated. 1 folder")
    report = analysis / "report"
    pngs = sorted(p.name for p in report.glob("*.png"))
    assert len(pngs) == 3 and (report / "axes_info.yaml").exists()
    assert len(list(report.glob("*.csv"))) == 3
    app.message = None
    tool.select_folder({"path": str(analysis)})
    assert tool.image_options() == pngs
    draw(app)
    assert tool._preview is not None                       # the PNG is shown
    tool.generate()                                        # nothing left to do
    assert tool.job is None and app.message[0] == "Nothing to do"
    app.message = None
    tool.clear_reports()
    feature(app).question.yes()
    assert not report.exists() and app.message[0] == "Reports cleared"


def test_the_report_config_is_validated_and_saved(app, tmp_path):
    assert app.run_action("make_report")
    tool = feature(app).window
    tool.config_text = "not: a report"
    tool.folders = [str(tmp_path)]
    tool.generate()
    assert app.message[0] == "Invalid config"
    tool.config_text = "plots:\n- type: 1d\n  x: E\n"
    tool.save_config()
    target = tmp_path / "r.json"
    app.io_service.answer(str(target))
    assert json.loads(target.read_text()) == {"plots": [{"type": "1d", "x": "E"}]}


def test_a_folder_dropped_on_the_report_tool_is_listed(app, analysis):
    assert app.run_action("make_report")
    opened = []
    app.open_path = lambda path: opened.append(path) or True
    app.files_dropped([str(analysis.parent)])            # a folder above: its analyses
    assert feature(app).window.folders == [str(analysis)] and not opened
    app.files_dropped([str(analysis / "bi4_bur")])       # no analysis folder in it
    assert app.message[0] == "No analysis folders found"


def test_report_capture_scenario_adds_the_folder(home, tmp_path):
    from ndxplorer.app.capture import capture_scenario, load_catalogue

    files = capture_scenario("report_tool", tmp_path / "shots", load_catalogue(),
                             size=SIZE)
    assert "report_tool--dialog.png" in [p.name for p in files]
