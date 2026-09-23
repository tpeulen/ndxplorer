"""The emtk app's file service (``app.io_service``): desktop dialogs and the page's downloads."""

from __future__ import annotations

import pytest

from ndxplorer.app.features.io_service import FileService


def test_ask_open_answers_through_the_callback_and_cancel_calls_nothing(tmp_path):
    got = []
    service = FileService(working_path=lambda: str(tmp_path), browser=False)
    service.ask_open("Open", "Text files (*.csv);;All files (*)", got.append)
    assert service.busy and service.current.dialog.directory == str(tmp_path)
    assert service.current.dialog.filters[0] == ("Text files", ["*.csv"])
    service.answer([str(tmp_path / "a.csv")])
    assert got == [[str(tmp_path / "a.csv")]] and not service.busy
    service.ask_folder("Folder", got.append)
    service.answer(None)
    assert len(got) == 1 and not service.busy


def test_single_answers_for_save_and_folder_and_a_queue(tmp_path):
    got = []
    service = FileService(working_path=lambda: "", browser=False)
    service.ask_save("Save", "", "x.json", lambda p: got.append(("save", p)))
    service.ask_folder("Folder", lambda p: got.append(("folder", p)))
    assert service.current.dialog.filename == "x.json"
    service.answer(str(tmp_path / "x.json"))
    assert service.current.kind == "folder"
    service.answer(str(tmp_path))
    assert got == [("save", str(tmp_path / "x.json")), ("folder", str(tmp_path))]


def test_save_bytes_on_a_desktop_asks_then_writes(tmp_path):
    service = FileService(working_path=lambda: str(tmp_path), browser=False)
    request = service.save_bytes("hist.csv", b"1,2\n", "text/csv")
    assert request.dialog.mode == "save" and request.dialog.filters[0][1] == ["*.csv"]
    service.answer(str(tmp_path / "hist.csv"))
    assert (tmp_path / "hist.csv").read_bytes() == b"1,2\n"


def test_in_a_page_save_bytes_downloads_and_a_save_outside_the_mount_is_handed_out(
        tmp_path, monkeypatch):
    downloads = []
    monkeypatch.setattr("emtk.web.page.download",
                        lambda name, data, mime="": downloads.append((name, data, mime)))
    service = FileService(working_path=lambda: "", browser=True)
    assert service.save_bytes("shot.png", b"PNG", "image/png") is None
    assert downloads == [("shot.png", b"PNG", "image/png")]

    def write(path):
        with open(path, "w") as handle:
            handle.write("{}")

    service.ask_save("Save", "", "g.selection.json", write)
    service.answer(str(tmp_path / "g.selection.json"))
    assert downloads[-1][0] == "g.selection.json" and downloads[-1][1] == b"{}"


def test_a_failing_callback_is_reported_not_raised(tmp_path):
    reports = []
    service = FileService(working_path=lambda: "", report=lambda t, m: reports.append((t, m)),
                          browser=False)

    def boom(_paths):
        raise ValueError("bad file")

    service.ask_open("Open CSV", "", boom)
    service.answer([str(tmp_path / "x")])
    assert reports == [("Open CSV", "ValueError: bad file")]


def test_the_window_has_one_service_and_draws_its_dialog():
    from emtk.pil_painter import PilPainter

    from ndxplorer.app.frame import NdxApp

    app = NdxApp()
    try:
        assert isinstance(app.io_service, FileService)
        app.io_service.ask_folder("Pick a folder", lambda p: None)
        painter = PilPainter(1000, 700)
        app.draw(painter, 0.0, 0.0, 1000.0, 700.0)
        assert app.io_service.box is not None
    finally:
        app.close()
