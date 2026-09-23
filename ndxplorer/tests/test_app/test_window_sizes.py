"""ndX at the window sizes a user really gets: nothing clips.

A window manager tiles the window (Magnet, macOS tiling): half the screen,
two thirds, whatever it had. At each size every control of the Plot
controls, the path row and the display corner must lie inside its window,
every button must show its label whole, and the axis combo boxes must show
at least a dozen characters. The offscreen painter draws the atlas 1:1, as
the native window does, so its text widths are the window's.
"""
from __future__ import annotations

import pathlib

import pytest

pytest.importorskip("emtk.docking")
pytest.importorskip("PIL")

DATA = pathlib.Path(__file__).resolve().parents[3] / "test" / "mfd" / "burstwise_All 0.1500#30"

#: Half a 1470x949 screen, a Magnet two-thirds tile, what a window manager
#: left one window at, the default, and the whole work area.
SIZES = [(735, 949), (980, 949), (992, 593), (1400, 900), (1470, 949)]


@pytest.fixture(scope="module")
def data_path():
    if not DATA.exists():
        pytest.skip("test data not present")
    return str(DATA)


def _replay(size, path, monkeypatch):
    from ndxplorer.app.capture import Replay

    replay = Replay({"id": "sizes"}, {}, size)
    assert replay.app.open_path(path)
    replay.settle(4)
    return replay


def _text_width(text: str) -> float:
    from emtk.pil_painter import PilPainter

    painter = PilPainter(1, 1)
    return painter.text_width(text)


def _buttons(spec):
    """``action -> label`` of every button in a spec."""
    found = {}

    def walk(node):
        if isinstance(node, dict):
            for item in node.get("buttons") or []:
                found[item["action"]] = item.get("label", item["action"])
            for value in node.values():
                walk(value)
        elif isinstance(node, list):
            for value in node:
                walk(value)

    walk(spec)
    return found


def _inside(rect, box, slack=1.0):
    x, y, w, h = rect
    bx, by, bw, bh = box
    return x >= bx - slack and x + w <= bx + bw + slack


@pytest.mark.parametrize("size", SIZES, ids=[f"{w}x{h}" for w, h in SIZES])
def test_no_control_clips_at_a_real_window_size(size, data_path, tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    replay = _replay(size, data_path, monkeypatch)
    app = replay.app
    from ndxplorer.app.docks import PLOT_CONTROLS

    boxes = {
        "plot_controls": app.docks.window(PLOT_CONTROLS).content,
        "plot_header": app.plot_boxes["header"],
        "plot_corner": app.plot_boxes["corner"],
    }
    pad = 8.0  # a button's frame padding, both sides, at the native scale
    problems = []
    for name, box in boxes.items():
        form = app.forms[name]
        labels = _buttons(app.specs[name])
        for key, rect in form.rects.items():
            if key.endswith(".fold") or rect[2] <= 0:
                continue
            if not _inside(rect, box):
                problems.append(f"{name}:{key} {rect} leaves {box}")
            if key in labels and _text_width(labels[key]) + pad > rect[2] + 0.5:
                problems.append(f"{name}:{key} cuts its label {labels[key]!r} ({rect[2]:.0f} px)")
    assert not problems, "\n".join(problems)


@pytest.mark.parametrize("size", SIZES, ids=[f"{w}x{h}" for w, h in SIZES])
def test_the_axis_combos_show_a_dozen_characters(size, data_path, tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    app = _replay(size, data_path, monkeypatch).app
    rects = app.forms["plot_controls"].rects
    # padding, text, a gap, the arrow, padding -- as view_form's combo draws it
    need = _text_width("0" * 12) + 16.0
    for name in ("x_name", "y_name"):
        assert rects[name][2] >= need, f"{name} is {rects[name][2]:.0f} px at {size}"


@pytest.mark.parametrize("size", [(980, 949), (1400, 900)])
def test_a_wide_enough_window_keeps_each_axis_on_one_line(size, data_path, tmp_path,
                                                          monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    rects = _replay(size, data_path, monkeypatch).app.forms["plot_controls"].rects
    assert abs(rects["x_name"][1] - rects["set_x_axis"][1]) < 1.0
    assert abs(rects["y_name"][1] - rects["set_y_axis"][1]) < 1.0


def test_the_left_dock_gets_its_minimum_and_the_plot_the_rest(data_path, tmp_path, monkeypatch):
    from ndxplorer.app.docks import LEFT_MIN

    monkeypatch.setenv("HOME", str(tmp_path))
    for size in SIZES:
        docks = _replay(size, data_path, monkeypatch).app.docks
        left, right = docks.region_boxes["left"], docks.region_boxes["right"]
        assert left[2] >= min(LEFT_MIN, (size[0] - 4) / 2.0) - 1.0
        assert right[2] >= left[2] * 0.8 or size[0] < 800


def test_size_option_is_parsed():
    from ndxplorer.app.launch import parse_size

    assert parse_size("992x593") == (992, 593)
    assert parse_size(None) is None and parse_size("") is None
    for bad in ("992", "axb", "0x10", "10x-3"):
        with pytest.raises(ValueError):
            parse_size(bad)
