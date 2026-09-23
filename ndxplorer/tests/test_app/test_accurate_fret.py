"""Accurate FRET in the emtk app: the FRET menu, the host interface, save and load.

The calibration algorithm is a backend behind
:func:`ndxplorer.analysis.fret_calibration.calibrate` (it is moving into a
compiled library). These tests install a small deterministic backend, so what
is checked is the window's side of the contract: what it hands over, how it
applies the result, the report, and keeping the calibration.
"""

from __future__ import annotations

import json

import numpy as np
import pytest

SIZE = (1400, 900)


@pytest.fixture
def home(tmp_path, monkeypatch):
    path = tmp_path / "home"
    path.mkdir()
    monkeypatch.setenv("HOME", str(path))
    return path


@pytest.fixture
def backend():
    """A deterministic backend: records what it was given, returns known numbers."""
    from ndxplorer.analysis import fret_calibration as fc

    seen = {}

    def fake(columns, constants, options, *, container="", progress=None):
        seen.update(columns=columns, constants=constants, options=options,
                    container=container)
        if progress is not None:
            progress(1, 2, "half way")
        green = columns["Number of Photons (green)"]
        red = columns["Number of Photons (red)"]
        return {
            "ok": True,
            "constants": {"gG/gR": 0.9, "alpha": 0.05},
            "before": {k: constants.get(k) for k in ("gG/gR", "alpha")},
            "new_columns": {"FRET efficiency (accurate)": red / (green + red)},
            "factors": {"alpha": 0.05, "beta": 1.1, "gamma": 0.9, "delta": 0.07, "r0": 52.0},
            "uncertainties": {"alpha": 0.001, "beta": 0.01, "gamma": 0.02, "delta": 0.001},
            "populations": [{"label": 0, "n": 100, "E": 0.5, "sigma_E": 0.01, "S": 0.5,
                             "distance": 52.0, "tau_f": 2.0}],
            "held": {"r0": 52.0},
            "determined": {"r0": 52.0},
            "applied_factors": ["alpha", "beta", "gamma", "delta"],
            "background": "fit",
            "background_fitted": {"bg_dd": 1.0},
            "report": "Automatic FRET calibration (test)",
        }

    fc.set_backend(fake)
    yield seen
    fc.set_backend(None)


def _columns(n=400, seed=0):
    rng = np.random.default_rng(seed)
    return {
        "Number of Photons (green)": rng.uniform(20, 200, n),
        "Number of Photons (red)": rng.uniform(20, 200, n),
        "Number of Photons (yellow)": rng.uniform(20, 200, n),
        "Duration (ms)": rng.uniform(0.5, 3.0, n),
    }


@pytest.fixture
def app(home):
    from ndxplorer.app.frame import NdxApp
    from ndxplorer.core.data_source import DataSource

    a = NdxApp(layout_store=None)
    a.model.set_source(DataSource.from_columns(_columns()))
    draw(a, 2)
    yield a
    a.close()


def draw(app, frames: int = 1):
    from emtk.pil_painter import PilPainter

    for _ in range(frames):
        painter = PilPainter(*SIZE)
        app.draw(painter, 0.0, 0.0, float(SIZE[0]), float(SIZE[1]))
    return painter.frame


def feature(app):
    return next(f for f in app.features if f.name == "accurate_fret")


# ------------------------------------------------------------ host interface
def test_burst_columns_and_apply_result_write_into_a_data_source():
    """The contract's window side: numeric columns out; constants and columns in."""
    from ndxplorer.analysis.fret_calibration import apply_result, burst_columns
    from ndxplorer.core.data_source import DataSource

    source = DataSource.from_columns(_columns(50))
    columns = burst_columns(source)
    assert set(columns) >= {"Number of Photons (green)", "Duration (ms)"}
    written = {}
    added = apply_result({"constants": {"alpha": 0.1}, "new_columns": {"E acc": np.ones(50)}},
                         write_constants=written.update, data_source=source)
    assert added == ["E acc"] and written == {"alpha": 0.1}
    assert np.allclose(source.column_values("E acc"), 1.0)


def test_with_chisurf_the_calibration_runs_on_chisurfs_code(app):
    """No backend installed: ChiSurf's calibration is the one used, and Calibrate is on."""
    pytest.importorskip("chisurf.plugins.ndxplorer.calibration_bridge")
    from chisurf.plugins.ndxplorer.calibration_bridge import calibrate_columns
    from ndxplorer.analysis import fret_calibration as fc

    fc.set_backend(None)
    assert fc.backend() is calibrate_columns
    assert fc.unavailable_reason() == ""


def test_without_a_backend_the_options_say_why_and_calibrate_is_off(app, monkeypatch):
    import sys

    from ndxplorer.analysis import fret_calibration as fc

    fc.set_backend(None)
    # no ChiSurf: its calibration cannot be imported
    monkeypatch.setitem(sys.modules, "chisurf.plugins.ndxplorer.calibration_bridge", None)
    assert app.run_action("fret_calibration")
    draw(app)
    dialog = feature(app).window
    assert dialog.unavailable_text() == fc.NO_BACKEND
    assert not dialog.enabled("calibrate")
    assert fc.calibrate({}, {}, fc.CalibrationOptions())["ok"] is False


def test_a_calibration_run_applies_constants_and_columns_and_reports(app, backend):
    f = feature(app)
    f.task_mode = "inline"
    assert app.run_action("fret_calibration")
    draw(app)
    options = f.window
    options.fit_gamma = False            # the form writes the options
    options.press("calibrate")
    draw(app, 2)
    # what the backend got: the table's columns, the window's constants, the options
    assert "Number of Photons (red)" in backend["columns"]
    assert backend["constants"]["gG/gR"] == pytest.approx(
        float(app.model.bundle.constants["gG/gR"]))
    assert backend["options"].factors() == ["alpha", "delta", "beta"]
    # applied
    assert f.constants["gG/gR"] == pytest.approx(0.9)
    assert f.constants["alpha"] == pytest.approx(0.05)
    assert "FRET efficiency (accurate)" in app.model.parameter_names
    # reported
    from ndxplorer.app.features.accurate_fret import ReportWindow

    report = f.window
    assert isinstance(report, ReportWindow)
    assert [r["factor"] for r in report.factor_rows()] == ["α", "β", "γ", "δ", "R₀"]
    assert report.factor_rows()[-1]["written"].startswith("held")
    assert "New columns: FRET efficiency (accurate)" in report.report_text
    assert "Automatic FRET calibration (test)" in report.report_text


def test_a_failed_run_says_why_and_changes_nothing(app, backend):
    from ndxplorer.analysis import fret_calibration as fc

    fc.set_backend(lambda *a, **k: {"ok": False, "error": "no donor-only population"})
    f = feature(app)
    f.task_mode = "inline"
    before = dict(f.constants)
    app.run_action("fret_calibration")
    draw(app)
    f.window.press("calibrate")
    draw(app, 2)
    assert app.message == ("Accurate FRET", "no donor-only population")
    assert f.constants == before


# ---------------------------------------------------------------- save/load
def test_save_and_load_round_trip_through_a_file(app, backend, home):
    """No container: the file route, through the io service, both ways."""
    f = feature(app)
    f.write_constants({"alpha": 0.123, "gG/gR": 0.77})
    path = home / "cal.fretcal.json"
    app.run_action("save_fret_calibration")
    draw(app)
    app.io_service.answer(str(path))
    doc = json.loads(path.read_text())
    assert doc["format"] == "chisurf.fret_calibration"
    assert doc["constants"]["alpha"] == pytest.approx(0.123)

    f.write_constants({"alpha": 0.5})
    app.message = None
    app.run_action("load_fret_calibration")
    draw(app)
    app.io_service.answer([str(path)])
    draw(app)
    question = f.questions[0]
    assert "alpha: 0.5 → 0.123" in question.text
    question.press("yes")
    draw(app)
    assert f.constants["alpha"] == pytest.approx(0.123)


def test_save_and_load_round_trip_through_the_container(app, backend, tmp_path):
    """With a `.pto` behind the bursts, Yes stores into it and Load offers it back."""
    pto = pytest.importorskip("chisurf.core.fio.pto")
    container = tmp_path / "measurement.pto"
    with pto.Measurement.create_empty(container, title="test"):
        pass
    app.model.source.provenance = {"container_path": str(container)}
    f = feature(app)
    f.write_constants({"alpha": 0.321})
    app.run_action("save_fret_calibration")
    draw(app)
    f.questions[0].press("yes")
    draw(app)
    assert app.message[1].startswith("Stored in")
    from ndxplorer.io.fret_calibration_io import stored_calibrations

    assert stored_calibrations(container=str(container))[-1]["constants"]["alpha"] == \
        pytest.approx(0.321)

    app.message = None
    f.write_constants({"alpha": 0.9})
    app.run_action("load_fret_calibration")
    draw(app)
    assert "1 stored calibration" in f.questions[0].text
    f.questions[0].press("yes")          # the newest stored one
    draw(app)
    f.questions[0].press("yes")          # apply it
    draw(app)
    assert f.constants["alpha"] == pytest.approx(0.321)


# --------------------------------------------------------------------- menus
def test_the_fret_menu_sits_before_help_and_mmfdb_says_why_it_is_off(app):
    from ndxplorer.app.menus import iter_entries, merged_menus

    extra = [e for feat in app.features for e in feat.menu_entries()]
    menus = merged_menus(extra)
    titles = [title for title, _ in menus]
    assert titles[-2:] == ["FRET", "Help"]
    rows = {entry["action"]: (path, entry["label"]) for path, entry in iter_entries(
        [m for m in menus]) if entry}
    assert rows["fret_calibration"][0] == ("FRET",)
    path, label = rows["open_from_mmfdb"]
    assert path == ("File", "Import") and "only inside ChiSurf" in label
    assert not app.panel.available("open_from_mmfdb")
    assert app.panel.available("fret_calibration")


def test_report_text_lists_what_was_written_and_held():
    from ndxplorer.analysis.fret_calibration import report_text

    text = report_text({"report": "R", "constants": {"alpha": 0.2}, "before": {"alpha": 0.1},
                        "held": {"gamma": 1.0}, "determined": {"gamma": 0.9},
                        "background": "none", "injected": ["E"]})
    assert "alpha: 0.1 → 0.2000" in text
    assert "gamma: kept 1.0000 — this measurement would have given 0.9000" in text
    assert "Background: none (set to zero)" in text and "New columns: E" in text


def test_nothing_here_imports_qt():
    import subprocess
    import sys

    code = ("import sys, ndxplorer.app.features.accurate_fret, "
            "ndxplorer.analysis.fret_calibration, ndxplorer.io.fret_calibration_io; "
            "print([m for m in sys.modules if m.startswith(('PyQt', 'qtpy', 'PySide'))])")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "[]"
