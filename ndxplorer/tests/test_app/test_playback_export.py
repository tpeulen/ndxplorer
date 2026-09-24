"""The emtk app's playback, ranking windows and publication export (headless, no Qt).

Playback is timed by whoever calls ``tick`` -- here a fake clock, in the app
the frame loop. The ranking runs through :mod:`emtk.tasks`; the cooperative
mode is the browser's, so it is the one tested end to end.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

import numpy as np
import pytest

from ndxplorer.core.data_source import DataSource

REPO = pathlib.Path(__file__).resolve().parents[3]
IRIS = REPO / "ndxplorer" / "tests" / "fixtures" / "iris.csv"
SIZE = (1400, 900)


class Clock:
    def __init__(self) -> None:
        self.now = 100.0

    def __call__(self) -> float:
        return self.now


def _view_model(fps=10, clock=None):
    from ndxplorer.core.playback import MODE_WINDOW, PlaybackController
    from ndxplorer.plotting.playback_view_model import PlaybackViewModel

    controller = PlaybackController(fps=fps)
    timing = []
    model = PlaybackViewModel(controller, on_timing=lambda: timing.append(model.playing),
                              clock=clock)
    model.set_axis_options(["", "t"])
    controller.set_axis("t", np.linspace(0.0, 1.0, 101), n_steps=10)
    controller.set_mode(MODE_WINDOW)
    return model, controller, timing


# ------------------------------------------------------------------ playback timing
def test_a_tick_steps_only_when_a_step_is_due():
    clock = Clock()
    model, controller, timing = _view_model(fps=10, clock=clock)
    model.play_forward()
    assert model.playing and timing == [True]
    assert not model.tick(clock.now + 0.05)          # half an interval: not yet
    assert controller.position == 0
    assert model.tick(clock.now + 0.1)               # due
    assert controller.position == 1
    assert not model.tick(clock.now + 0.12)          # the next is 0.1 s later
    assert model.tick(clock.now + 0.2)
    assert controller.position == 2


def test_a_display_that_falls_behind_drops_steps_rather_than_bursting():
    clock = Clock()
    model, controller, _ = _view_model(fps=10, clock=clock)
    model.play_forward()
    assert model.tick(clock.now + 1.0)               # ten intervals late: one step
    assert controller.position == 1
    assert not model.tick(clock.now + 1.01)


def test_pause_and_speed_tell_the_host_and_stop_the_ticks():
    clock = Clock()
    model, controller, timing = _view_model(fps=10, clock=clock)
    model.play_forward()
    model.fps = 20
    assert model.interval == pytest.approx(0.05)
    model.pause()
    assert not model.playing and timing[-1] is False
    assert not model.tick(clock.now + 5.0)
    assert controller.position == 0


def test_the_step_slider_runs_over_the_steps_and_needs_an_axis():
    model, controller, _ = _view_model()
    assert model.bounds("position") == (0, 9)
    assert model.enabled("play_forward")
    controller.set_axis(None)
    assert not model.enabled("play_forward")


# -------------------------------------------------------------------- the feature
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


def feature(app):
    return next(f for f in app.features if f.name == "playback_export")


def _bursts():
    rng = np.random.default_rng(1)
    n = 2000
    t = np.sort(rng.uniform(0.0, 100.0, n))
    return DataSource.from_columns({
        "Mean Macro Time (s)": t,
        "E": np.where(t < 50.0, 0.2, 0.8) + rng.normal(0, 0.05, n),
        "S": rng.normal(0.5, 0.05, n),
    })


def _load(app, source):
    app.model.set_source(source)
    app.data_changed()
    draw(app)


def test_loading_points_the_playback_at_the_macro_time(app):
    _load(app, _bursts())
    f = feature(app)
    assert f.controller.axis_name == "Mean Macro Time (s)"
    assert f.playback.axis_options()[0] == ""


def test_window_mode_gates_the_plots_to_the_slice_and_stack_does_not(app):
    _load(app, _bursts())
    f = feature(app)
    total = app.model.count_total
    f.playback.mode = "window"
    f.playback.n_steps = 4
    draw(app)
    first = app.model.count_current
    assert 0 < first < total
    f.playback.step_forward()
    draw(app)
    assert app.model.count_current != first or f.controller.position == 1
    f.playback.mode = "integrate"
    draw(app)
    assert app.model.count_current >= first
    f.playback.mode = "stack"
    draw(app)
    assert app.model.count_current == total


def test_playing_keeps_the_app_animating_and_the_frame_loop_steps_it(app):
    _load(app, _bursts())
    f = feature(app)
    f.playback.play_forward()
    assert app.animating()
    f.playback._next_due = 0.0                       # due now
    draw(app)
    assert f.controller.position == 1
    f.playback.pause()
    assert not f.playback.playing


def test_the_playback_panel_is_drawn_in_the_plot_controls(app):
    _load(app, _bursts())
    form = app.forms["plot_controls"]
    form.folds["Playback"] = True
    draw(app)
    for name in ("axis_name", "n_steps", "position.slider", "step_backward", "play_backward",
                 "pause", "play_forward", "step_forward", "mode", "fps.slider"):
        assert name in form.rects, name


def test_selecting_the_z_range_during_playback_gates_the_slice_too(app):
    _load(app, _bursts())
    f = feature(app)
    f.playback.mode = "window"
    f.playback.n_steps = 4
    before = len(app.model.gates)
    f.on_z_select()
    f.on_z_select()
    assert len(app.model.gates) == before + 1
    row = list(app.model.gates)[-1]
    assert row.name == "Mean Macro Time (s)"
    assert (row.lower, row.upper) == f.controller.bounds


# ------------------------------------------------------------------------ ranking
def test_ranking_iris_by_class_finds_the_petals_and_applies_them(app):
    from ndxplorer.analysis.vizrank import RunState

    assert app.open_path(str(IRIS))
    app.panel.z_name = "class"
    f = feature(app)
    f.task_mode = "cooperative"                      # the browser's way: slices per frame
    draw(app)
    assert app.run_action("find_projections")
    panel = f.rankings[True]
    model = panel.model
    # Opening starts the ranking; switch it to separation by class and restart.
    model.refresh_context()
    model.method = "separation"
    model.classes = "z parameter: class"
    model.settings_changed()
    model.start()
    for _ in range(2000):
        draw(app)
        if model.run_state == RunState.Done:
            break
    assert model.run_state == RunState.Done
    best = model.rows[0]
    assert {best["name0"], best["name1"]} == {"petal width", "petal length"}
    assert {app.model.x.name, app.model.y.name} == {"petal width", "petal length"}
    assert panel.window.open


def test_separation_is_the_default_and_its_islands_colour_the_map(app):
    """The best view is the one where the bursts split; its islands paint the map."""
    from ndxplorer.analysis.vizrank import RunState

    rng = np.random.default_rng(3)
    n = 3000
    species = rng.random(n) < 0.4
    _load(app, DataSource.from_columns({
        "E": np.where(species, rng.normal(0.2, 0.05, n), rng.normal(0.8, 0.05, n)),
        "S": np.where(species, rng.normal(0.3, 0.04, n), rng.normal(0.6, 0.04, n)),
        "Rate": rng.normal(20.0, 4.0, n),
    }))
    f = feature(app)
    f.task_mode = "inline"
    draw(app)
    assert app.run_action("find_projections")
    model = f.rankings[True].model
    assert model.method == "populations" and model.overlay_available
    for _ in range(200):
        draw(app)
        if model.run_state == RunState.Done:
            break
    assert model.run_state == RunState.Done
    assert {model.rows[0]["name0"], model.rows[0]["name1"]} == {"E", "S"}
    assert model.rows[0]["name2"] == "2"
    assert {app.model.x.name, app.model.y.name} == {"E", "S"}
    values = app.model.map_values()
    assert f.map_image(values) is None, "off until asked for"
    model.show_islands = True
    model.islands_changed()
    rgba = f.map_image(values)
    assert rgba is not None and rgba.shape[:2] == np.shape(values)
    colours = {tuple(c) for c in rgba[..., :3].reshape(-1, 3) if c.any()}
    assert len(colours) > 10, "two island hues, shaded by density"


def test_the_z_ranking_sets_the_z_parameter(app):
    from ndxplorer.analysis.vizrank import RunState

    assert app.open_path(str(IRIS))
    f = feature(app)
    f.task_mode = "inline"
    draw(app)
    assert app.run_action("find_z_projections")
    model = f.rankings[False].model
    for _ in range(200):
        draw(app)
        if model.run_state == RunState.Done:
            break
    assert model.run_state == RunState.Done
    assert app.model.z.name == model.rows[0]["payload"]["z"]


def test_a_cooperative_run_streams_several_batches():
    from ndxplorer.app.features.playback_export import FrameTask

    seen = []
    states = iter(range(2000))

    def slow(handle):
        import time

        count = 0
        for state in states:
            time.sleep(0.0005)
            count += 1
            if handle.is_cancelled:
                break
        handle.set_partial(count)
        return count

    done = []
    task = FrameTask(slow, (), seen.append, None, None, lambda: done.append(True),
                     mode="cooperative", budget=0.005)
    for _ in range(5000):
        if task.pump():
            break
    assert done and sum(seen) == 2000 and len(seen) > 1


# ------------------------------------------------------------------------- export
def test_the_export_figure_is_pdf_svg_or_png_bytes(app):
    from ndxplorer.app.features.playback_export import (PublicationExportModel,
                                                        export_figure_bytes)

    _load(app, _bursts())
    options = PublicationExportModel(lambda m: None, lambda: None)
    assert not options.enabled("dpi")                # vector
    assert export_figure_bytes(app.model, options)[:4] == b"%PDF"
    options.format = "SVG (vector)"
    assert b"<svg" in export_figure_bytes(app.model, options)[:500]
    options.format = "PNG (raster)"
    options.dpi = 72
    assert options.enabled("dpi")
    assert export_figure_bytes(app.model, options)[:8] == b"\x89PNG\r\n\x1a\n"


def test_export_hands_the_bytes_to_the_file_service(app):
    _load(app, _bursts())
    saved = []

    class Service:
        def save_bytes(self, name, data, mime, **kwargs):
            saved.append((name, data[:4], mime))

        def draw(self, box):
            return False

    app.io_service = Service()
    f = feature(app)
    assert app.run_action("export_figure")
    draw(app)
    assert f.export_window.open
    f.export_model.export()
    assert saved == [("ndxplorer_figure.pdf", b"%PDF", "application/pdf")]
    assert not f.export_window.open


def test_export_without_data_says_so(app):
    f = feature(app)
    f.open_export()
    assert app.message is not None and not f.export_window.open


# ------------------------------------------------------------------------ browser
def test_the_feature_imports_without_qt():
    code = ("import sys; import ndxplorer.app.features.playback_export, "
            "ndxplorer.analysis.projection_rank_model, ndxplorer.plotting.playback_view_model; "
            "bad = [m for m in ('qtpy', 'PyQt5', 'PyQt6', 'PySide6', 'pyqtgraph') "
            "if m in sys.modules]; print(bad); sys.exit(1 if bad else 0)")
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
