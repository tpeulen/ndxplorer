"""The Qt-free logic behind the settings feature: settings files and batch reports."""

from __future__ import annotations

import json

import numpy as np
import pytest


def test_axis_settings_merge_only_the_axes_in_use():
    from ndxplorer.settings.persist import merge_axis_settings

    baseline = {"A": {"min": 0}, "B": {"min": 1}}
    current = {"A": {"min": 5}, "B": {"min": 9}, "C": {"min": 2}}
    merged, changed = merge_axis_settings(baseline, current, ["A", "C", ""])
    assert merged == {"A": {"min": 5}, "B": {"min": 1}, "C": {"min": 2}}
    assert set(changed) == {"A", "C"}


def test_axis_settings_bytes_start_from_the_packaged_file():
    from ndxplorer.settings.persist import axis_settings_bytes

    data = json.loads(axis_settings_bytes({"Fd/Fa": {"min": 1.0}}, ["Fd/Fa"]))
    assert data["Fd/Fa"] == {"min": 1.0} and "r Experimental (green)" in data


def test_default_axes_keep_the_rest_of_the_file(tmp_path):
    from ndxplorer.settings.persist import write_default_axes

    path = tmp_path / "s.settings.json"
    path.write_text(json.dumps({"axis": "a.json", "default_axes": {"weight": "N"}}))
    data = write_default_axes(path, "E", "S", "T", colormap="magma")
    assert data == {"axis": "a.json", "colormap": "magma",
                    "default_axes": {"weight": "N", "x": "E", "y": "S", "z": "T"}}
    assert json.loads(path.read_text()) == data
    broken = tmp_path / "broken.settings.json"
    broken.write_text("{not json")
    assert write_default_axes(broken, "E", "S", "T", fallback={"k": 1})["k"] == 1


def test_constants_keep_their_rich_format():
    from ndxplorer.settings.persist import constants_payload

    rich = {"version": 1, "parameters": {"a": {"value": 1.0, "fixed": False, "lb": 0}}}
    out = constants_payload({"a": 2.0, "b": 3.0}, rich)
    assert out["parameters"]["a"] == {"value": 2.0, "fixed": False, "lb": 0}
    assert out["parameters"]["b"] == {"value": 3.0}
    assert rich["parameters"]["a"]["value"] == 1.0                   # not modified
    assert constants_payload({"a": 2}, {"a": 1.0}) == {"a": 2.0}


def test_equations_round_trip_through_the_settings_reader(tmp_path):
    from ndxplorer.settings.bundle import read_settings
    from ndxplorer.settings.persist import write_equations

    equations = [{"Sg/Sr": "'Sg' / 'Sr'"}, {"Quoted": "\"a\" + 'b'"}]
    write_equations(tmp_path / "e.yaml", equations)
    (tmp_path / "x.settings.json").write_text(json.dumps({"equations": "e.yaml"}))
    assert read_settings(tmp_path / "x.settings.json").equations == equations


def test_axis_display_reads_and_writes_label_settings(tmp_path):
    import yaml

    from ndxplorer.plotting.axis_display import AxisDisplay, write_label_settings

    display = AxisDisplay.from_label_settings(
        {"enable_all_labels": False, "axis_labels": {"x_plot": {"top": False}},
         "fonts": {"color": "#bb3838", "title_size_pt": 12}})
    assert not display.label("xmarginal", "top") and display.label("ymarginal", "right")
    assert display.title_colour == (187, 56, 56, 255)
    assert display.fonts["title_size_pt"] == 12                    # kept for the Qt window
    path = tmp_path / "labels.yaml"
    write_label_settings(path, display.label_settings)
    again = AxisDisplay.from_label_settings(yaml.safe_load(path.read_text()))
    assert again.label_settings == display.label_settings


# ------------------------------------------------------------------ reports
def test_a_report_config_needs_a_plot_list():
    from ndxplorer.export.report import ConfigError, parse_config

    assert parse_config("plots: []") == {"plots": []}
    assert parse_config('{"plots": [{"type": "1d"}]}', json_text=True)["plots"][0]["type"] == "1d"
    for bad in ("plots: 3", "- a", "a: [", ""):
        with pytest.raises(ConfigError):
            parse_config(bad)


def test_the_2d_csv_is_x_across_y_down():
    from ndxplorer.export.report import hist_2d_csv

    H = np.array([[1, 2, 3], [4, 5, 6]], dtype=float)       # (n_x=2, n_y=3)
    text = hist_2d_csv(H, [0, 1, 2], [0, 1, 2, 3], "X", "Y").decode().splitlines()
    assert text[0] == "Y/X,0.5,1.5"
    assert text[1:] == ["0.5,1.0,4.0", "1.5,2.0,5.0", "2.5,3.0,6.0"]


def test_analysis_folders_are_found_below_a_root(tmp_path):
    from ndxplorer.export.report import (clear_reports, discover_analysis_folders,
                                         is_folder_processed)

    a = tmp_path / "s1" / "run"
    b = tmp_path / "s2" / "run"
    for folder in (a, b):
        (folder / "bi4_bur").mkdir(parents=True)
        (folder / "bi4_bur" / "m.bur").write_text("x")
    (tmp_path / ".hidden" / "bur").mkdir(parents=True)
    (tmp_path / ".hidden" / "bur" / "m.bur").write_text("x")
    assert discover_analysis_folders([tmp_path]) == [a, b]
    assert discover_analysis_folders([a, a]) == [a]
    (a / "report").mkdir()
    assert not is_folder_processed(a)
    (a / "report" / "01.png").write_bytes(b"png")
    assert is_folder_processed(a)
    assert clear_reports([a, b]) == 1 and not (a / "report").exists()


def test_the_figures_render_to_png_bytes():
    from ndxplorer.export.report import render_1d_png, render_2d_marginals_png, render_2d_png

    edges = np.linspace(0, 1, 11)
    H = np.random.default_rng(0).random((10, 8))
    for data in (render_1d_png(edges, np.arange(10), "t", "x"),
                 render_2d_png(H, edges, np.linspace(0, 1, 9), "t", "x", "y"),
                 render_2d_marginals_png(H, edges, np.linspace(0, 1, 9), "t", "x", "y")):
        assert data[:8] == b"\x89PNG\r\n\x1a\n"


def test_the_report_module_imports_no_qt():
    import subprocess
    import sys

    code = ("import sys; import ndxplorer.export.report, ndxplorer.settings.persist, "
            "ndxplorer.plotting.axis_display, ndxplorer.utils.performance_config; "
            "sys.exit(any(m.split('.')[0] in ('PyQt5', 'PyQt6', 'PySide2', 'PySide6', 'qtpy', "
            "'pyqtgraph') for m in sys.modules))")
    assert subprocess.run([sys.executable, "-c", code]).returncode == 0
