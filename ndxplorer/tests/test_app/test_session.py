"""The analysis view kept in the measurement: save, reopen, partial restore, lock, browser."""

from __future__ import annotations

import subprocess
import sys

import numpy as np
import pytest
import tttrlib

SIZE = (1400, 900)
COLUMNS = ("Number of Photons", "Duration (ms)", "Tau (green)", "FRET efficiency")


@pytest.fixture(autouse=True)
def home(tmp_path, monkeypatch):
    path = tmp_path / "home"
    path.mkdir()
    monkeypatch.setenv("HOME", str(path))
    return path


def make_pto(path, columns=COLUMNS, n=600, seed=0):
    """A small measurement: one burst table, as a burst search writes it."""
    rng = np.random.default_rng(seed)
    handle = tttrlib.PtoFile()
    assert handle.create(str(path), "test")
    store = tttrlib.DataStore()
    for name in columns:
        store.add(name, rng.uniform(1.0, 100.0, n))
    uid = tttrlib.pto_add_store(handle, "burst_table", "run/bi4_bur/m.bur", store)
    tttrlib.pto_describe(handle, uid, data_format="dstore", row_grain="burst",
                         operation_type="burst_selection", software="test 1")
    assert handle.commit()
    handle.close()
    return path


def draw(app, frames=2):
    from emtk.pil_painter import PilPainter

    painter = None
    for _ in range(frames):
        painter = PilPainter(*SIZE)
        app.draw(painter, 0.0, 0.0, float(SIZE[0]), float(SIZE[1]))
    return painter.frame


def open_app(path):
    from ndxplorer.app.frame import NdxApp

    app = NdxApp(layout_store=None)
    assert app.open_path(str(path)), app.model.error
    draw(app, 3)
    return app


def feature(app, name):
    return next(f for f in app.features if f.name == name)


def names_in(path):
    from ndxplorer.io.container import open_container

    with open_container(path) as handle:
        return [obj.name for obj in handle.objects()]


def set_up_view(app):
    """Axes, colours, gates of three kinds, clusters, a vector curve, a Gaussian."""
    model = app.model
    model.set_parameter("x", "Tau (green)")
    model.set_parameter("y", "FRET efficiency")
    model.x.bins_2d, model.x.lo, model.x.hi, model.x.log = 23, 2.0, 90.0, True
    model.y.norm = True
    model.colormap, model.log_counts, model.mask_nan = "magma", True, False
    model.add_interval("Duration (ms)", 10.0, 60.0)
    model.gates.add_gaussian(model.index_of("Tau (green)"), model.index_of("FRET efficiency"),
                             [40.0, 50.0], [[30.0, 2.0], [2.0, 40.0]], sigma=2.0, name="G")
    from ndxplorer.core.data_source import MaskDataSelection

    mask = np.zeros((5, 4), dtype=np.uint8)
    mask[1:3, 1:3] = 1
    model.gates.add_selection(MaskDataSelection(
        model.index_of("Tau (green)"), model.index_of("Number of Photons"), mask,
        np.linspace(0, 100, 5), np.linspace(0, 100, 6), name="painted"))
    model.invalidate()
    analysis = feature(app, "analysis")
    labels = (model.source.column_values("FRET efficiency") > 50).astype(np.int64)
    analysis.set_clusters(labels, np.full(len(labels), 0.9), {"method": "kmeans",
                                                               "columns": {"Tau (green)"}})
    analysis.selected_cluster, analysis.cluster_colours = 1, True
    analysis.gaussians.add((30.0, 40.0), np.diag([25.0, 16.0]), 0.7)
    overlays = feature(app, "overlays")
    curve = overlays.overlays.add_curve()
    curve.set_text("a*x + b")
    curve.color = "#00ff00"
    curve.group.set_vector("a", [0.5, 1.5], ["low", "high"], column="Cluster Label")
    feature(app, "playback_export").playback.n_steps = 7
    draw(app, 2)
    return labels


# ------------------------------------------------------------------ round trip
def test_the_view_survives_save_and_reopen(tmp_path):
    path = make_pto(tmp_path / "m.pto")
    app = open_app(path)
    labels = set_up_view(app)
    vmin, vmax = app.model.vmin, app.model.vmax
    app.run_action("save_session")
    assert "Session saved" in app.status
    assert names_in(path).count("ndx_session") == 1
    app.close()
    assert names_in(path).count("ndx_session") == 1, "an unchanged view was written again"

    again = open_app(path)
    model = again.model
    assert "Restored the session" in again.status and "not restored" not in again.status
    assert (model.x.name, model.y.name) == ("Tau (green)", "FRET efficiency")
    assert (model.x.bins_2d, model.x.lo, model.x.hi, model.x.log) == (23, 2.0, 90.0, True)
    assert model.y.norm and model.log_counts and not model.mask_nan
    assert model.colormap == "magma"
    assert [g["kind"] for g in model.gate_records()] == ["Interval", "G2D", "Mask"]
    assert model.gates[0].name == "Duration (ms)" and model.gates[0].lower == 10.0
    assert model.gates[1].meta["sigma"] == 2.0
    assert model.gates[2].selection.mask.sum() == 4
    analysis = feature(again, "analysis")
    assert np.array_equal(analysis.labels, labels)
    assert analysis.selected_cluster == 1 and analysis.cluster_colours
    assert np.array_equal(model.source.column_values("Cluster Label"), labels)
    [curve] = feature(again, "overlays").overlays.curves
    assert curve.text == "a*x + b" and curve.color == "#00ff00"
    assert curve.populations() == ["low", "high"]
    assert [p.value for p in curve.group.get("a").flat()[1:]] == pytest.approx([0.5, 1.5])
    [gauss] = analysis.gaussians.components()
    assert gauss.mu == pytest.approx([30.0, 40.0]) and gauss.w == pytest.approx(0.7)
    assert feature(again, "playback_export").playback.n_steps == 7
    assert (model.vmin, model.vmax) == pytest.approx((vmin, vmax))
    again.close()


def test_leaving_a_file_saves_its_view_and_history_is_bounded(tmp_path):
    from ndxplorer.io.session_io import SESSION_HISTORY

    first, second = make_pto(tmp_path / "a.pto"), make_pto(tmp_path / "b.pto", seed=1)
    app = open_app(first)
    app.model.set_parameter("x", "Duration (ms)")
    assert app.open_path(str(second))                    # switching saves the first
    assert names_in(first).count("ndx_session") == 1
    for i in range(SESSION_HISTORY + 2):
        app.model.x.bins_1d = 40 + i
        app.run_action("save_session")
    assert names_in(second).count("ndx_session") == SESSION_HISTORY
    app.close()


# ------------------------------------------------------------ partial restore
def test_a_state_from_another_table_applies_what_still_fits(tmp_path):
    from ndxplorer.io.session_io import latest_session, payload, save_session

    source = make_pto(tmp_path / "a.pto")
    app = open_app(source)
    set_up_view(app)
    app.run_action("save_session")
    saved = latest_session(str(source))
    app.close()

    other = make_pto(tmp_path / "b.pto", columns=("Number of Photons", "Duration (ms)",
                                                  "FRET efficiency"), n=300)
    assert save_session(str(other), payload(saved["state"], saved["table"],
                                            saved["table"]["columns"]))["ok"]
    again = open_app(other)
    model = again.model
    status = again.status
    assert "not restored" in status and "Tau (green)" in status
    assert "cluster labels" in status
    assert model.y.name == "FRET efficiency" and model.colormap == "magma"
    assert [g["kind"] for g in model.gate_records()] == ["Interval"]     # 2-D gates need Tau
    assert feature(again, "analysis").labels is None
    again.close()


def test_a_measurement_without_a_state_opens_as_before(tmp_path):
    path = make_pto(tmp_path / "m.pto")
    app = open_app(path)
    assert "session" not in app.status.lower()
    assert app.model.gate_records() == []
    app.close()
    assert "ndx_session" not in names_in(path), "opening and closing wrote into the file"


def test_the_reader_and_so_the_qt_window_ignore_a_stored_state(tmp_path):
    from ndxplorer.io.pto_reader import read_container

    path = make_pto(tmp_path / "m.pto")
    before = read_container(path)
    app = open_app(path)
    app.run_action("save_session")
    app.close()
    after = read_container(path)
    assert list(after.parameter_names) == list(before.parameter_names)
    assert after.size == before.size


# ------------------------------------------------------------------- the lock
def test_a_lock_held_by_another_writer_is_said_not_raised(tmp_path):
    path = make_pto(tmp_path / "m.pto")
    app = open_app(path)
    holder = subprocess.Popen(
        [sys.executable, "-c", "import sys, time, tttrlib\n"
         f"lock = tttrlib.PtoWriteLock({str(path)!r}).acquire()\n"
         "print('held', flush=True)\nsys.stdin.readline()\n"],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
    try:
        assert holder.stdout.readline().strip() == "held"
        app.model.set_parameter("x", "Duration (ms)")
        app.run_action("save_session")
        assert "open for writing in another program" in app.status
        assert app.message is not None and "open for writing" in app.message[1]
        app.message = None
        app.close()                                     # quiet: no exception, a status
        assert "not saved" in app.status
    finally:
        holder.stdin.write("\n")
        holder.stdin.flush()
        holder.wait(10)
    assert "ndx_session" not in names_in(path)


# ------------------------------------------------------------------- browser
def test_the_browser_writes_into_its_copy_and_downloads_it(tmp_path, monkeypatch):
    from ndxplorer.app.features.io_service import FileService
    from ndxplorer.io.session_io import latest_session

    dropped = make_pto(tmp_path / "dropped.pto")        # the page's in-memory copy
    app = open_app(dropped)
    got = {}
    service = FileService(browser=True)
    monkeypatch.setattr(service, "download",
                        lambda name, data, mime=None: got.update(name=name, data=data))
    app.io_service = service
    app.model.set_parameter("x", "Duration (ms)")
    assert app.run_action("download_session_pto")
    assert got["name"] == "dropped.pto"
    downloaded = tmp_path / "downloaded.pto"
    downloaded.write_bytes(got["data"])
    state = latest_session(str(downloaded))
    assert state["state"]["view"]["axes"]["x"]["name"] == "Duration (ms)"
    app.close()
