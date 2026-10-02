"""``python -m ndxplorer`` opens the emtk app; there is no other GUI to choose.

The ``ndxplorer`` / ``ndxplorer-gui`` scripts point at the same ``main``.
"""

from __future__ import annotations

from click.testing import CliRunner

from ndxplorer import __main__ as entry


def test_main_opens_the_emtk_app_with_the_path_and_window_options(monkeypatch, tmp_path):
    calls = []

    def run(**kwargs):
        calls.append(kwargs)
        return 0

    monkeypatch.setattr("ndxplorer.app.launch.run", run)
    result = CliRunner().invoke(entry.main, ["--folder", str(tmp_path), "--host", "tk",
                                             "--size", "992x593",
                                             "--chisurf-rpc", "127.0.0.1:1"])
    assert result.exit_code == 0, result.output
    assert calls == [{"path": str(tmp_path), "host": "tk", "chisurf_rpc": "127.0.0.1:1",
                      "size": (992, 593)}]


def test_no_gui_switch_is_left():
    text = CliRunner().invoke(entry.main, ["--help"]).output
    assert "--emtk" not in text
    for option in ("--file", "--folder", "--host", "--size", "--chisurf-rpc"):
        assert option in text
    assert "filter" in text and "image" in text


def test_a_bad_size_is_a_usage_error(tmp_path):
    result = CliRunner().invoke(entry.main, ["--size", "big"])
    assert result.exit_code == 2
    assert "WIDTHxHEIGHT" in result.output
