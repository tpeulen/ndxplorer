"""The emtk app's io feature, headless: import, merge, image mode, gates, burst IDs, screenshot.

Driven the way a user drives it -- an action, then the dialog it opens is
answered through ``app.io_service`` -- and the result read off the model.
"""

from __future__ import annotations

import json
import pathlib

import numpy as np
import pytest

from ndxplorer.core.data_source import DataSource

REPO = pathlib.Path(__file__).resolve().parents[3]
IRIS = REPO / "ndxplorer" / "tests" / "fixtures" / "iris.csv"
MFD = REPO / "test" / "mfd" / "burstwise_All 0.1500#30"
SIZE = (1200, 800)


@pytest.fixture
def app():
    from ndxplorer.app.frame import NdxApp

    a = NdxApp()
    yield a
    a.close()


def draw(app, frames=1):
    from emtk.pil_painter import PilPainter

    for _ in range(frames):
        painter = PilPainter(*SIZE)
        app.draw(painter, 0.0, 0.0, float(SIZE[0]), float(SIZE[1]))
    return painter.frame


def io_feature(app):
    return next(f for f in app.features if f.name == "io")


def finish(app):
    """Let a load or save that is running finish, and draw the result."""
    feature = io_feature(app)
    if feature.task is not None:
        feature.task.wait(120.0)
        feature.task = None
    draw(app, 2)


def open_iris(app):
    app.run_action("open_text")
    request = app.io_service.current
    assert request.dialog.title == "Comma separated value files"
    assert request.multiple
    app.io_service.answer([str(IRIS)])
    finish(app)


def test_import_text_asks_for_files_then_loads_in_the_background(app):
    draw(app)
    open_iris(app)
    model = app.model
    assert model.has_data and model.count_total == 150
    assert "petal length" in model.parameter_names
    assert model.working_path == str(IRIS.parent)


def test_the_dialogs_captions_and_filters_are_the_importers(app):
    from ndxplorer.io.loading import IMPORTERS

    for action, kind in (("open_analysis_file", "mfd_hdf5"), ("open_analysis_folder", "burst_dir"),
                         ("open_sampling", "cs_sampling")):
        app.run_action(action)
        request = app.io_service.current
        assert request.dialog.title == IMPORTERS[kind].title
        assert request.kind == ("folder" if IMPORTERS[kind].mode == "folder" else "open")
        app.io_service.cancel()
    assert not app.model.has_data


def test_with_data_loaded_an_import_asks_how_to_merge_and_cancel_keeps_the_table(app):
    from ndxplorer.app.features.io import MergeQuestion

    open_iris(app)
    app.run_action("open_text")
    feature = io_feature(app)
    assert isinstance(feature.dialog, MergeQuestion)
    assert feature.dialog.title == "Open CSV Files"
    assert not app.io_service.busy
    draw(app)
    assert feature.dialog.box is not None
    feature.dialog.cancel()
    draw(app)
    assert feature.dialog is None and not app.io_service.busy
    assert app.model.count_total == 150


def test_append_as_rows_stacks_the_new_table_under_the_old(app):
    open_iris(app)
    app.run_action("open_text")
    question = io_feature(app).dialog
    question.choice = 2          # Append as rows
    question.ok()
    app.io_service.answer([str(IRIS)])
    finish(app)
    assert app.model.count_total == 300


def test_a_file_that_cannot_be_read_says_why_and_the_data_stays(app, tmp_path):
    open_iris(app)
    broken = tmp_path / "broken.h5"
    broken.write_bytes(b"not hdf5")
    feature = io_feature(app)
    feature.load([str(broken)], "mfd_hdf5")
    finish(app)
    assert app.message is not None and app.message[0] == "Data Load Error"
    assert app.model.count_total == 150


def test_an_image_table_is_shown_as_an_image(app):
    rng = np.random.default_rng(1)
    n = 5000
    source = DataSource.from_columns({
        "X pixel": rng.integers(0, 64, n).astype(float),
        "Y pixel": rng.integers(0, 48, n).astype(float),
        "Number of Photons (green)": rng.integers(1, 50, n).astype(float),
        "Tau": rng.normal(3, 0.3, n),
    })
    app.model.set_source(source)
    app.data_changed()
    model = app.model
    assert (model.x.name, model.y.name) == ("X pixel", "Y pixel")
    assert (model.x.bins_2d, model.y.bins_2d) == (64, 48)
    assert (model.x.lo, model.x.hi, model.y.hi) == (0.0, 64.0, 48.0)
    assert model.weight_enabled and model.weight_name == "Number of Photons (green)"
    assert not model.mask_nan and not model.mask_inf
    # Changed by the user afterwards, it stays changed.
    model.mask_nan = True
    app.data_changed()
    assert model.mask_nan


def test_browse_sets_the_working_path(app, tmp_path):
    app.run_action("browse")
    assert app.io_service.current.kind == "folder"
    app.io_service.answer(str(tmp_path))
    assert app.model.working_path == str(tmp_path)


def test_gates_are_saved_to_a_selection_file_and_read_back(app, tmp_path):
    pytest.importorskip("chisurf.core.roi")
    open_iris(app)
    model = app.model
    model.set_parameter("x", "petal length")
    model.set_parameter("y", "petal width")
    model.add_rectangle((1.0, 3.0), (0.1, 1.0))
    assert len(model.gates.rows) == 2
    app.run_action("save_gates")
    request = app.io_service.current
    assert request.dialog.title == "Selection JSON" and request.kind == "save"
    app.io_service.answer(str(tmp_path / "petals"))
    written = tmp_path / "petals.selection.json"
    assert written.exists() and json.loads(written.read_text())
    model.update()
    kept = model.count_current
    model.clear_gates()
    app.run_action("load_gates")
    app.io_service.answer([str(written)])
    assert len(model.gates.rows) >= 1
    model.update()
    assert model.count_current == kept


def test_burst_ids_are_written_and_what_next_is_asked(app, tmp_path):
    from ndxplorer.app.features.io import BurstIdQuestion

    assert app.open_path(str(MFD))
    draw(app)
    assert app.panel.available("save_burst_ids")
    app.run_action("save_burst_ids")
    assert app.io_service.current.dialog.title == "Folder for Burst IDs"
    app.io_service.answer(str(tmp_path))
    finish(app)
    assert list(tmp_path.glob("*.bst"))
    question = io_feature(app).dialog
    assert isinstance(question, BurstIdQuestion)
    assert question.microtime_histogram and not question.correlate
    question.correlate = True
    question.ok()
    draw(app)
    titles = [app.message[0]] + [m[0] for m in io_feature(app).messages]
    assert titles == ["Plugin Not Available", "Plugin Not Available"]


def test_screenshot_saves_the_window_as_png_or_jpeg(app, tmp_path):
    from PIL import Image

    open_iris(app)
    app.run_action("screenshot")
    draw(app)
    request = app.io_service.current
    assert request.dialog.title == "Save Screenshot"
    assert request.dialog.filename.startswith("ndxplorer_screenshot_")
    app.io_service.answer(str(tmp_path / "shot"))
    image = Image.open(tmp_path / "shot.png")
    assert image.size == SIZE
    app.run_action("screenshot")
    draw(app)
    app.io_service.answer(str(tmp_path / "shot.jpg"))
    assert Image.open(tmp_path / "shot.jpg").format == "JPEG"


def test_in_a_page_the_screenshot_is_a_download(app, monkeypatch):
    downloads = []
    monkeypatch.setattr("emtk.web.page.download",
                        lambda name, data, mime="": downloads.append((name, data[:8], mime)))
    app.io_service.browser = True
    app.run_action("screenshot")
    draw(app)
    assert downloads and downloads[0][0].endswith(".png")
    assert downloads[0][1] == b"\x89PNG\r\n\x1a\n" and downloads[0][2] == "image/png"


def test_nothing_under_the_app_imports_qt():
    import subprocess
    import sys

    code = ("import sys; import ndxplorer.app.features.io, ndxplorer.io.loading; "
            "print(any(m.split('.')[0] in ('PyQt5', 'PyQt6', 'PySide2', 'PySide6', 'qtpy') "
            "for m in sys.modules))")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True)
    assert out.stdout.strip() == "False"
