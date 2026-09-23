"""Photograph the emtk app in the parity scenarios, headlessly.

The parity harness (``tools/parity``) replays the scenarios of
``tools/parity/scenarios.json`` on the Qt window and writes
``parity/qt/<id>.png``; this replays them on :class:`~ndxplorer.app.frame.NdxApp`
and writes ``parity/emtk/<id>.png`` and ``parity/emtk/<id>--<shot>.png`` -- the
file names are the contract (``tools/parity/README.md``).

A step is replayed through the app the way a user would do it: a drag on the
map is a pointer press, moves and a release at those fractions of the map; a
menu is opened by pressing its title; a check box is the panel attribute its
Qt widget stands for. A scenario with a step the app cannot do yet is skipped
and says which step: the report then shows the shot as MISSING, which is the
truth, rather than a picture of something else.

Rendering is :class:`emtk.pil_painter.PilPainter` -- no window, no GPU, no Qt.

    python -m ndxplorer.app.capture                  # every scenario it can do
    python -m ndxplorer.app.capture -s gate_rectangle -s weights
    python -m ndxplorer.app.capture --list
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import re
import sys
from typing import Callable, Dict, List, Optional

__all__ = ["REPO", "SCENARIOS", "Unsupported", "Replay", "capture_scenario", "main"]

REPO = pathlib.Path(__file__).resolve().parents[2]
SCENARIOS = REPO / "tools" / "parity" / "scenarios.json"
DEFAULT_OUT = REPO / "parity" / "emtk"
WINDOW = (1400, 900)


class Unsupported(Exception):
    """A step the emtk app cannot replay yet."""


#: Qt widget expressions -> the panel attribute that replaced them.
WIDGETS: Dict[str, str] = {
    "pc.spinBoxBin1DX": "x_bins_1d", "pc.spinBoxBin2DX": "x_bins_2d",
    "pc.spinBoxBin1DY": "y_bins_1d", "pc.spinBoxBin2DY": "y_bins_2d",
    "pc.spinBoxBin1DZ": "z_bins_1d",
    "pc.checkBoxLogX": "x_log", "pc.checkBoxLogY": "y_log", "pc.checkBoxLogZ": "z_log",
    "pc.checkBoxNormX": "x_norm", "pc.checkBoxNormY": "y_norm", "pc.checkBoxNormZ": "z_norm",
    "pc.spinBoxXmin": "x_min", "pc.spinBoxXmax": "x_max",
    "pc.spinBoxYmin": "y_min", "pc.spinBoxYmax": "y_max",
    "pc.spinBoxZmin": "z_min", "pc.spinBoxZmax": "z_max",
    "pc.checkBoxWeight": "weight_enabled", "pc.comboBoxWeight": "weight_name",
    "pc.comboBoxSelX": "x_name", "pc.comboBoxSelY": "y_name", "pc.comboBoxSelZ": "z_name",
    "pc.checkBoxEnableZ": "z_gate_enabled", "pc.checkBoxDynamicSelection": "z_dynamic",
    "win.checkBoxEnableZ": "z_gate_enabled",
    "win.comboBoxCmap": "colormap", "win.checkBoxLogCounts": "log_counts",
    "win.checkBoxMaskNaN": "mask_nan", "win.checkBoxMaskInf": "mask_inf",
    "win.doubleSpinBox_vmin": "vmin", "win.doubleSpinBox_vmax": "vmax",
}

#: Qt buttons -> the panel action behind the same button.
BUTTONS: Dict[str, str] = {
    "win.toolButton_AutoContrast": "auto_contrast", "win.toolButtonClearPlot": "clear_plot",
    "pc.toolButtonAutoX": "auto_x", "pc.toolButtonAutoY": "auto_y", "pc.toolButtonAutoZ": "auto_z",
    "pc.toolButtonSetXAxis": "set_x_axis", "pc.toolButtonSetYAxis": "set_y_axis",
    "pc.toolButtonSetZAxis": "set_z_axis", "pc.toolButtonAddSelection": "z_select",
    "win.toolButtonChangePath": "browse",
}

#: Qt menu actions -> the app's actions.
ACTIONS: Dict[str, str] = {
    "actionOpenCsv": "open_text", "actionOpenParisDataset": "open_analysis_folder",
    "actionOpenMfdHdf5": "open_analysis_file", "actionOpenChiSurfSampling": "open_sampling",
}

#: Qt widgets photographed on their own -> the box of the app's counterpart.
TARGETS: Dict[str, str] = {
    "widget:win.dockWidget_PlotControl": "left_dock",
    "widget:pc.widgetSelection": "panel:Selection",
    "widget:pc.widgetZ": "panel:z axis",
    # widget_6's controls are on the toolbar and in the marginals' corner now
    "widget:win.widget_6": "display_controls",
}


class Replay:
    """One scenario, played on a fresh app.

    Parameters
    ----------
    scenario : dict
        The scenario from ``scenarios.json``.
    catalogue : dict
        The whole file (datasets and setups).
    size : tuple of int
        Window size.
    """

    def __init__(self, scenario: dict, catalogue: dict, size=WINDOW,
                 layout_store=None) -> None:
        from .frame import NdxApp

        self.scenario = scenario
        self.catalogue = catalogue
        self.size = size
        # A window layout is kept only when asked for: capture_scenario keeps
        # it as the shipped app does, in the settings folder of its scratch
        # $HOME. A Replay made anywhere else must never read or write the
        # user's own layout.
        self.app = NdxApp(layout_store=layout_store)
        self.shots: Dict[str, object] = {}
        self.frame = None

    # ------------------------------------------------------------ drawing
    def draw(self):
        """Draw a frame; returns the PIL image."""
        from emtk.pil_painter import PilPainter

        from . import theme

        w, h = self.size
        painter = PilPainter(w, h, background=theme.WINDOW_BG)
        self.app.draw(painter, 0.0, 0.0, float(w), float(h))
        self.frame = painter.frame
        return self.frame

    def settle(self, frames: int = 2) -> None:
        """Draw until the app is idle: a recompute, then the frame showing it."""
        for _ in range(frames):
            self.draw()

    # -------------------------------------------------------------- input
    def click_at(self, x: float, y: float, clicks: int = 1) -> None:
        self.app.pointer_move(x, y)
        self.draw()
        self.app.pointer_press(x, y, 1, 0, clicks)
        self.draw()
        self.app.pointer_release(x, y, 1)
        self.draw()

    def click_rect(self, rect) -> None:
        x, y, w, h = rect
        self.click_at(x + min(w / 2.0, 12.0), y + h / 2.0)

    def drag(self, start, end, rect) -> None:
        """A pointer drag from and to fractions of *rect*."""
        x, y, w, h = rect
        (fx0, fy0), (fx1, fy1) = start, end
        p0 = (x + fx0 * w, y + fy0 * h)
        p1 = (x + fx1 * w, y + fy1 * h)
        self.app.pointer_move(*p0)
        self.draw()
        self.app.pointer_press(p0[0], p0[1], 1)
        self.draw()
        for t in (0.25, 0.5, 0.75, 1.0):
            self.app.pointer_move(p0[0] + t * (p1[0] - p0[0]), p0[1] + t * (p1[1] - p0[1]), 1)
            self.draw()
        self.app.pointer_release(p1[0], p1[1], 1)
        self.settle(3)

    # ------------------------------------------------------------ helpers
    def dataset(self, ref: str) -> str:
        if ref.startswith("@"):
            ref = self.catalogue["datasets"][ref[1:]]["path"]
        ref = ref.replace("$REPO", str(REPO))
        return os.path.expanduser(ref)

    def panel_rect(self, title: str):
        """The screen box of a panel of the plot-control dock, header to end."""
        form = self.app.forms["plot_controls"]
        start = form.rects.get(f"{title}.fold")
        if start is None:
            raise Unsupported(f"no panel {title!r}")
        titles = [s.get("title") for s in self.app.specs["plot_controls"]["sections"]]
        below = [form.rects[f"{t}.fold"][1] for t in titles[titles.index(title) + 1:]
                 if f"{t}.fold" in form.rects]
        from .docks import PLOT_CONTROLS

        left = self.app.docks.window(PLOT_CONTROLS).content
        if left is None:
            raise Unsupported(f"{PLOT_CONTROLS} is not on screen")
        bottom = min(below) if below else left[1] + left[3]
        return (start[0], start[1], start[2], bottom - start[1])

    def feature_box(self, target: str):
        """The box a feature locates *target* at; ``None`` when none has it on screen.

        A locator that returns ``None`` means "not mine now", so two features
        can both answer ``"dialog"``.
        """
        for feature in self.app.features:
            locate = feature.capture_targets().get(target)
            if locate is not None:
                box = locate(self)
                if box is not None:
                    return box
        return None

    def box_of(self, target: str):
        box = self.feature_box(target)
        if box is not None:
            return box
        kind = TARGETS.get(target)
        if kind is None:
            raise Unsupported(f"capture target {target!r}")
        if kind == "left_dock":
            from .docks import PLOT_CONTROLS

            frame = self.app.docks.window(PLOT_CONTROLS).frame
            if frame is None:
                raise Unsupported(f"{PLOT_CONTROLS} is not on screen")
            return frame
        if kind.startswith("panel:"):
            return self.panel_rect(kind[len("panel:"):])
        if kind == "display_controls" and "header" in self.app.plot_boxes:
            # the toolbar and the corner under its right end, as one picture
            hx, hy, hw, hh = self.app.plot_boxes["header"]
            cx, cy, cw, ch = self.app.plot_boxes["corner"]
            return (hx, hy, hw, cy + ch - hy)
        if kind not in self.app.plot_boxes:
            raise Unsupported(f"the Plot window is not on screen for {target!r}")
        return self.app.plot_boxes[kind]

    def menu_box(self):
        """The union of the menu panels that are open."""
        from emtk.widgets.menus import Menu

        rects = []

        def walk(menu):
            if menu.open and menu.panel_rect is not None:
                rects.append(menu.panel_rect)
                for entry in menu.entries:
                    if isinstance(entry, Menu):
                        walk(entry)

        for menu in self.app.menubar.menus:
            walk(menu)
        if not rects:
            raise Unsupported("no menu is open")
        x0 = min(r[0] for r in rects)
        y0 = min(r[1] for r in rects)
        x1 = max(r[0] + r[2] for r in rects)
        y1 = max(r[1] + r[3] for r in rects)
        return (x0, y0, x1 - x0, y1 - y0)

    # --------------------------------------------------------------- steps
    def run(self) -> Dict[str, object]:
        """Play the setup and the steps; returns ``{shot name: PIL image}``."""
        self.settle()
        setup = self.scenario.get("setup")
        for step in (self.catalogue.get("setups", {}).get(setup, []) if setup else []):
            self.step(step)
        for step in self.scenario.get("steps", []):
            self.step(step)
        if "main" not in self.shots:
            # The Qt harness photographs the window at the end of every
            # scenario that names no "main" shot; so does this.
            self.shots["main"] = self.draw().copy()
        return self.shots

    def step(self, step: dict) -> None:
        """Replay one step: a feature's op first (they extend the vocabulary),
        then the core's. A feature handler that returns ``False`` passes the
        step on, so several features can share an op name (``click``)."""
        op = step.get("op")
        for feature in self.app.features:
            handler = feature.capture_ops().get(op)
            if handler is not None and handler(self, step) is not False:
                return
        handler: Optional[Callable[[dict], None]] = getattr(self, f"op_{op}", None)
        if handler is None:
            raise Unsupported(f"op {op!r}")
        handler(step)

    def actions(self) -> Dict[str, str]:
        """Qt action -> app action: the core's and every feature's."""
        merged = dict(ACTIONS)
        for feature in self.app.features:
            merged.update(feature.capture_actions())
        return merged

    def op_open(self, step: dict) -> None:
        if step.get("expect_error"):
            ok = self.app.open_path(self.dataset(step["path"]))
            if ok:
                raise Unsupported("expected a load error, the file opened")
        else:
            if step.get("action") and step["action"] not in self.actions():
                raise Unsupported(f"action {step['action']!r}")
            if not self.app.open_path(self.dataset(step["path"])):
                raise Unsupported(f"could not open {step['path']}: {self.app.model.error}")
        self.settle()

    def op_axis(self, step: dict) -> None:
        attr = {"x": "x_name", "y": "y_name", "z": "z_name", "weight": "weight_name"}[step["axis"]]
        name = step["name"]
        if name not in self.app.model.parameter_names:
            raise Unsupported(f"no parameter {name!r}")
        setattr(self.app.panel, attr, name)
        self.settle()

    def op_set(self, step: dict) -> None:
        widget, value = step["widget"], step["value"]
        cell = re.fullmatch(r"pc\.tableWidget\.cellWidget\((\d+),\s*(\d+)\)", widget)
        if cell:
            row, column = int(cell.group(1)), int(cell.group(2))
            key = {3: "invert", 4: "enabled"}.get(column)
            if key is None or row >= len(self.app.model.gates):
                raise Unsupported(f"table cell {widget}")
            self.app.model.edit_gate(row, key, bool(value))
        elif widget in WIDGETS:
            setattr(self.app.panel, WIDGETS[widget], value)
        else:
            raise Unsupported(f"widget {widget!r}")
        self.settle()

    def op_click(self, step: dict) -> None:
        widget = step["widget"]
        fold = re.fullmatch(r"button\('([^']+)'\)", widget)
        if fold:
            rect = self.app.forms["plot_controls"].rects.get(f"{fold.group(1)}.fold")
            if rect is None:
                raise Unsupported(f"button {widget}")
            self.click_rect(rect)
            return
        action = BUTTONS.get(widget)
        if action is None:
            raise Unsupported(f"button {widget!r}")
        for form in self.app.forms.values():
            if action in form.rects:
                self.click_rect(form.rects[action])
                self.settle()
                return
        if not self.app.run_action(action):
            raise Unsupported(f"button {widget!r} ({action}) is not available")
        self.settle()

    def op_trigger(self, step: dict) -> None:
        action = self.actions().get(step.get("action", ""))
        if action is None or not self.app.run_action(action):
            raise Unsupported(f"action {step.get('action')!r}")
        self.settle()

    def op_call(self, step: dict) -> None:
        code = step["code"]
        z = re.fullmatch(r"win\.selection_z\.set_range\(([-\d.e]+),\s*([-\d.e]+)\)", code.strip())
        if z:
            self.app.model.set_z_range(float(z.group(1)), float(z.group(2)))
            self.settle()
            return
        raise Unsupported(f"call {code!r}")

    def op_drag(self, step: dict) -> None:
        if step.get("widget"):
            raise Unsupported(f"drag on {step['widget']!r}")
        self.settle()
        rect = self.app.plots.rects.get("map")
        if rect is None:
            raise Unsupported("no map on screen")
        self.drag(step["start"], step["end"], rect)

    def op_menu(self, step: dict) -> None:
        from emtk.widgets.menus import Menu

        self.app.menubar.close()
        self.draw()
        path = list(step["path"])
        titles = {m.label: rect for m, rect in self.app.menubar._titles}
        if path[0] not in titles:
            raise Unsupported(f"menu {path[0]!r}")
        self.click_rect(titles[path[0]])
        menu = next(m for m in self.app.menubar.menus if m.label == path[0])
        for label in path[1:]:
            sub = next((e for e in menu.entries if isinstance(e, Menu) and e.label == label), None)
            row = next((rect for entry, rect in menu._rows if entry is sub), None)
            if sub is None or row is None:
                raise Unsupported(f"submenu {label!r}")
            self.click_rect(row)
            menu = sub
        self.draw()

    def op_close_menus(self, _step: dict) -> None:
        self.app.menubar.close()
        self.draw()

    def op_wait_plot(self, _step: dict) -> None:
        self.settle()

    def op_wait(self, step: dict) -> None:
        """Let the app settle; with ``seconds``, let that much time pass
        first (a tooltip shows once the pointer has rested on its item)."""
        seconds = float(step.get("seconds", 0) or 0)
        if seconds > 0:
            import time

            time.sleep(seconds)
        self.settle()

    def op_hover(self, step: dict) -> None:
        """Rest the pointer on a control: ``widget`` is a Qt name this module
        maps (``pc.comboBoxSelX``, ``win.toolButton_AutoContrast``) or a form
        item's own name (``x_name``, ``set_x_axis``)."""
        widget = step["widget"]
        name = WIDGETS.get(widget) or BUTTONS.get(widget) or widget
        for form in self.app.forms.values():
            rect = form.rects.get(name)
            if rect is not None:
                x, y, w, h = rect
                self.app.pointer_move(x + w / 2.0, y + h / 2.0)
                self.draw()
                return
        raise Unsupported(f"hover on {widget!r}")

    def op_dialog_result(self, _step: dict) -> None:
        """The answer to Qt's merge question; the app has no merge question
        (a load replaces the table), so there is nothing to answer."""

    def op_capture(self, step: dict) -> None:
        target = step.get("target", "window")
        name = step.get("name", "main")
        image = self.draw()
        if target in (None, "window"):
            shot = image.copy()
        elif target == "menu":
            shot = image.crop(_ints(self.menu_box(), pad=2))
        elif target.startswith("dialog"):
            box = self.feature_box(target)
            if box is None:
                box = getattr(self.app, "message_box", None) if self.app.message is not None \
                    else None
            if box is None:
                raise Unsupported("no dialog is open")
            shot = image.crop(_ints(box, pad=2))
        else:
            shot = image.crop(_ints(self.box_of(target)))
        self.shots[name] = shot


def _ints(box, pad: int = 0) -> tuple:
    x, y, w, h = box
    return (int(x) - pad, int(y) - pad, int(round(x + w)) + pad, int(round(y + h)) + pad)


def _with_real_home(catalogue: dict) -> dict:
    """The catalogue with ``~`` in dataset paths expanded against the real home,
    before ``$HOME`` is moved to the scratch folder."""
    import copy

    catalogue = copy.deepcopy(catalogue)
    for entry in catalogue.get("datasets", {}).values():
        if isinstance(entry.get("path"), str):
            entry["path"] = os.path.expanduser(entry["path"])
    steps = [step for scenario in catalogue.get("scenarios", [])
             for step in scenario.get("steps", [])]
    steps += [step for setup in catalogue.get("setups", {}).values() for step in setup]
    for step in steps:
        if isinstance(step.get("path"), str) and step["path"].startswith("~"):
            step["path"] = os.path.expanduser(step["path"])
    return catalogue


def load_catalogue(path: pathlib.Path = SCENARIOS) -> dict:
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


class scratch_home:
    """Run with ``$HOME`` pointing at an empty folder, restored afterwards.

    ndXplorer keeps its settings in ``~/.ndxplorer`` and several scenarios write
    there (Set default axis, Save constants, Performance Settings). A scenario
    has to start from the shipped defaults -- as ``capture_qt.py`` arranges --
    and must never touch the user's own settings. The scratch folder is seeded
    with the shipped defaults on first use, by the app itself.
    """

    def __enter__(self):
        import tempfile

        self._previous = os.environ.get("HOME")
        self._dir = tempfile.TemporaryDirectory(prefix="ndx-capture-home-")
        os.environ["HOME"] = self._dir.name
        return pathlib.Path(self._dir.name)

    def __exit__(self, *exc):
        if self._previous is None:
            os.environ.pop("HOME", None)
        else:
            os.environ["HOME"] = self._previous
        self._dir.cleanup()
        return False


def capture_scenario(scenario_id: str, out_dir=DEFAULT_OUT, catalogue: Optional[dict] = None,
                     size=WINDOW) -> List[pathlib.Path]:
    """Replay one scenario and write its shots; returns the files written.

    Always in a scratch ``$HOME`` (:class:`scratch_home`): the shipped settings,
    and the user's ``~/.ndxplorer`` untouched.

    Raises
    ------
    Unsupported
        When a step cannot be replayed; nothing is written for the scenario.
    """
    catalogue = catalogue if catalogue is not None else load_catalogue()
    scenario = next((s for s in catalogue["scenarios"] if s["id"] == scenario_id), None)
    if scenario is None:
        raise KeyError(f"no scenario {scenario_id!r}")
    out_dir = pathlib.Path(out_dir).resolve()
    catalogue = _with_real_home(catalogue)
    with scratch_home():
        from .docks import layout_store

        replay = Replay(scenario, catalogue, size, layout_store=layout_store())
        try:
            shots = replay.run()
        finally:
            replay.app.close()
    out = pathlib.Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    written = []
    for name, image in shots.items():
        filename = f"{scenario_id}.png" if name == "main" else f"{scenario_id}--{name}.png"
        path = out / filename
        image.save(path)
        written.append(path)
    return written


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="python -m ndxplorer.app.capture",
                                     description=__doc__.splitlines()[0])
    parser.add_argument("-s", "--scenario", action="append", default=[],
                        help="scenario id (repeat); default: all")
    parser.add_argument("--out", type=pathlib.Path, default=DEFAULT_OUT)
    parser.add_argument("--scenarios", type=pathlib.Path, default=SCENARIOS)
    parser.add_argument("--list", action="store_true")
    args = parser.parse_args(argv)
    catalogue = load_catalogue(args.scenarios)
    ids = args.scenario or [s["id"] for s in catalogue["scenarios"]]
    if args.list:
        for s in catalogue["scenarios"]:
            print(f"{s['id']:32s} {s.get('title', '')}")
        return 0
    done, skipped = 0, 0
    for scenario_id in ids:
        try:
            files = capture_scenario(scenario_id, args.out, catalogue)
        except Unsupported as exc:
            skipped += 1
            print(f"skip  {scenario_id}: {exc}")
            continue
        done += 1
        print(f"ok    {scenario_id}: " + ", ".join(p.name for p in files))
    print(f"{done} captured, {skipped} skipped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
