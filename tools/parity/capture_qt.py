#!/usr/bin/env python
"""Capture the Qt ndXplorer baseline screenshots for the emtk parity check.

Every scenario in ``tools/parity/scenarios.json`` is replayed against the real
``NDXplorer`` main window: files are opened through the File menu actions (the
file dialog answers are queued, not bypassed), axes are chosen in the real
combo boxes, gates are dragged onto the 2-D canvas with real mouse events, and
dialogs are opened by triggering the actions and buttons a user would press.

Only the *blocking* parts of Qt are swapped out, because a harness cannot sit in
a nested event loop waiting for a click:

* ``QDialog.exec_`` / ``QMenu.exec_`` / ``QMessageBox.exec_`` show the widget
  non-modally and return immediately (the result is configurable per step);
* the static ``QFileDialog.get*`` / ``QMessageBox.*`` / ``QInputDialog.get*``
  helpers answer from a queue the scenario fills, or -- if nothing is queued --
  show a real (non-native) dialog so it can be photographed, and return
  "cancelled".

Each scenario runs in its own subprocess (fresh window, fresh ``$HOME`` with
the shipped default settings), so one scenario can neither leak state into the
next nor take the whole run down when it crashes.

Output (the contract ``compare.py`` and the emtk capture side rely on, see
``tools/parity/README.md``)::

    parity/qt/<scenario-id>.png            the main window at the end of the scenario
    parity/qt/<scenario-id>--<shot>.png    every extra capture (dialog, menu, panel)
    parity/qt/<scenario-id>.log.json       steps run, captures, errors, blank checks
    parity/qt/index.json                   summary of the whole run

Usage::

    python tools/parity/capture_qt.py                 # every scenario
    python tools/parity/capture_qt.py -s main_mfd_loaded -s gate_rectangle
    python tools/parity/capture_qt.py --list

Run it with the arm64 conda env's interpreter, ``~/mambaforge/envs/arm64/bin/python``
(ndXplorer imports ``chisurf``, ``tttrlib`` and friends); the sibling source trees
ChiSurf needs on ``PYTHONPATH`` are added automatically.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]  # modules/ndxplorer
SCENARIOS = HERE / "scenarios.json"
DEFAULT_OUT = REPO / "parity" / "qt"

WINDOW_SIZE = (1400, 900)


# ─────────────────────────────────────────────────────────────────────────────
# Environment
# ─────────────────────────────────────────────────────────────────────────────
def _python_path() -> list[str]:
    """Source trees ndXplorer needs importable, when they exist on this machine."""
    chisurf = REPO.parents[1]  # modules/ndxplorer -> modules -> chisurf
    dev = chisurf.parent
    app_root = Path(os.environ.get("NDX_PARITY_APP_ROOT") or REPO)
    candidates = [
        app_root,
        chisurf,
        chisurf / "modules" / "mmfdb" / "src",
        chisurf / "modules" / "chinet",
        chisurf / "modules" / "imp-tricks" / "src",
        dev / "chimol",  # chisurf.core.fio.structure imports chimol
    ]
    return [str(p) for p in candidates if p.exists()]


def child_env(home: Path) -> dict:
    env = dict(os.environ)
    env.setdefault("QT_QPA_PLATFORM", "offscreen")
    parts = _python_path() + [p for p in env.get("PYTHONPATH", "").split(os.pathsep) if p]
    env["PYTHONPATH"] = os.pathsep.join(dict.fromkeys(parts))
    # ~/.ndxplorer is where ndX keeps its settings; a scratch HOME gives every
    # scenario the shipped defaults instead of whatever the user last saved.
    env["NDX_PARITY_REAL_HOME"] = os.environ.get("NDX_PARITY_REAL_HOME", str(Path.home()))
    env["HOME"] = str(home)
    cache = REPO / "parity" / ".cache"
    cache.mkdir(parents=True, exist_ok=True)
    env.setdefault("MPLCONFIGDIR", str(cache / "mpl"))
    env.setdefault("NUMBA_CACHE_DIR", str(cache / "numba"))
    env["PYTHONHASHSEED"] = "0"
    env["NDX_PARITY_REPO"] = str(REPO)
    return env


def load_scenarios() -> list[dict]:
    with open(SCENARIOS, encoding="utf-8") as fh:
        doc = json.load(fh)
    return doc["scenarios"]


def expand(value, datasets: dict):
    """Resolve ``@dataset`` references and ``~`` / ``$REPO`` in paths."""
    if isinstance(value, str):
        if value.startswith("@"):
            value = datasets[value[1:]]["path"]
        value = value.replace("$REPO", str(REPO))
        # $HOME is the scenario's scratch home (files a scenario writes);
        # "~" below is the real one (data a scenario reads).
        value = value.replace("$HOME", os.environ.get("HOME", ""))
        if value.startswith("~"):
            # The scenario subprocess runs with a scratch $HOME; data paths
            # mean the real one.
            real_home = os.environ.get("NDX_PARITY_REAL_HOME") or str(Path.home())
            value = real_home + value[1:]
        return value
    if isinstance(value, list):
        return [expand(v, datasets) for v in value]
    if isinstance(value, dict):
        return {k: expand(v, datasets) for k, v in value.items()}
    return value


# ─────────────────────────────────────────────────────────────────────────────
# Parent: one subprocess per scenario
# ─────────────────────────────────────────────────────────────────────────────
def prepare_datasets(python: str) -> None:
    """Build the datasets that are generated rather than shipped (``generate``)."""
    with open(SCENARIOS, encoding="utf-8") as fh:
        datasets = json.load(fh).get("datasets", {})
    for name, spec in datasets.items():
        cmd = spec.get("generate")
        if not cmd:
            continue
        path = Path(expand(spec["path"], datasets))
        if path.exists():
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        argv = [python] + [str(path) if a == "$PATH" else expand(a, datasets) for a in cmd]
        print(f"generating dataset {name!r}: {' '.join(argv[1:])}")
        home = Path(tempfile.mkdtemp(prefix="ndx-parity-gen-"))
        try:
            subprocess.run(argv, cwd=REPO, env=child_env(home), check=True,
                           capture_output=True, text=True)
        finally:
            shutil.rmtree(home, ignore_errors=True)


def _app_revision(app_root: Path) -> str:
    """Which ndXplorer source the baseline was taken from (commit, +dirty)."""
    stamp = app_root / ".parity-revision"
    if stamp.exists():
        return stamp.read_text().strip()
    try:
        rev = subprocess.run(["git", "rev-parse", "--short", "HEAD"], cwd=app_root,
                             capture_output=True, text=True, check=True).stdout.strip()
        dirty = subprocess.run(["git", "status", "--porcelain", "--", "ndxplorer"],
                               cwd=app_root, capture_output=True, text=True).stdout.strip()
        return rev + ("+dirty" if dirty else "")
    except Exception:
        return "unknown"


def run_all(ids: list[str], out: Path, timeout: int, python: str) -> int:
    scenarios = load_scenarios()
    wanted = [s for s in scenarios if not ids or s["id"] in ids]
    unknown = set(ids) - {s["id"] for s in scenarios}
    if unknown:
        print("unknown scenario ids:", ", ".join(sorted(unknown)), file=sys.stderr)
        return 2
    out.mkdir(parents=True, exist_ok=True)
    index_path = out / "index.json"
    index = {}
    if index_path.exists() and ids:
        index = json.loads(index_path.read_text()).get("scenarios", {})

    prepare_datasets(python)
    failures = 0
    for n, sc in enumerate(wanted, 1):
        sid = sc["id"]
        for old in out.glob(f"{sid}.png"):
            old.unlink()
        for old in out.glob(f"{sid}--*.png"):
            old.unlink()
        home = Path(tempfile.mkdtemp(prefix=f"ndx-parity-{sid}-"))
        t0 = time.time()
        cmd = [python, str(Path(__file__).resolve()), "--run-one", sid, "--out", str(out)]
        try:
            proc = subprocess.run(cmd, env=child_env(home), timeout=timeout,
                                  capture_output=True, text=True)
            rc = proc.returncode
            tail = (proc.stderr or "")[-4000:]
        except subprocess.TimeoutExpired as exc:
            rc = -999
            tail = f"TIMEOUT after {timeout}s\n" + str((exc.stderr or b"")[-2000:])
        finally:
            shutil.rmtree(home, ignore_errors=True)
        log_path = out / f"{sid}.log.json"
        log = json.loads(log_path.read_text()) if log_path.exists() else {}
        status = log.get("status", "crashed")
        if rc != 0 and status == "ok":
            status = "crashed"
        if status != "ok":
            failures += 1
            log.setdefault("stderr_tail", tail)
            log["status"] = status
            log_path.write_text(json.dumps(log, indent=2))
        index[sid] = {
            "status": status,
            "captures": log.get("captures", []),
            "errors": log.get("errors", []),
            "seconds": round(time.time() - t0, 1),
        }
        print(f"[{n}/{len(wanted)}] {sid}: {status} "
              f"({len(log.get('captures', []))} captures, {index[sid]['seconds']}s)"
              + (f"  {log.get('errors', [])[:1]}" if status != "ok" else ""))
    app_root = Path(os.environ.get("NDX_PARITY_APP_ROOT") or REPO)
    index_path.write_text(json.dumps(
        {"generated": time.strftime("%Y-%m-%d %H:%M:%S"), "window_size": WINDOW_SIZE,
         "app_revision": _app_revision(app_root), "platform": os.environ.get(
             "QT_QPA_PLATFORM", "offscreen"), "scenarios": index}, indent=2))
    return 1 if failures else 0


# ─────────────────────────────────────────────────────────────────────────────
# Child: drive one scenario in-process
# ─────────────────────────────────────────────────────────────────────────────
class Harness:
    """Owns the QApplication, the patched blocking calls and the window."""

    def __init__(self, scenario: dict, datasets: dict, out: Path):
        from qtpy import QtCore, QtGui, QtWidgets

        self.QtCore, self.QtGui, self.QtWidgets = QtCore, QtGui, QtWidgets
        self.sc = scenario
        self.datasets = datasets
        self.out = out
        self.app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(
            ["ndx-parity"])
        self.app.setApplicationName("ndX")
        self.opened: list = []          # dialogs / menus / message boxes, oldest first
        self.file_answers: list = []    # queued answers for QFileDialog.get*
        self.dialog_result = 0          # what a patched exec_() returns
        self.dialog_results: list = []  # queued results, used before dialog_result
        self.question_answer = QtWidgets.QMessageBox.No
        self.question_answers: list = []  # queued answers, used before question_answer
        #: The plugin globals when the window is hosted by ChiSurf (host "chisurf").
        self.host_context: dict = {}
        self.messages: list = []        # text of every message box shown
        self.menu_choice = None         # entry a patched QMenu.exec_ returns
        self._menu_chain: list = []
        self.log = {"id": scenario["id"], "status": "ok", "steps": [], "captures": [],
                    "errors": [], "messages": self.messages}
        self.win = None
        self._install_patches()

    # ── event pumping ────────────────────────────────────────────────────────
    def pump(self, ms: int = 50):
        timer = self.QtCore.QElapsedTimer()
        timer.start()
        while timer.elapsed() < ms:
            self.app.processEvents(self.QtCore.QEventLoop.AllEvents, 20)
            time.sleep(0.005)

    def wait_until(self, predicate, timeout_ms: int = 30000, settle_ms: int = 300) -> bool:
        timer = self.QtCore.QElapsedTimer()
        timer.start()
        while timer.elapsed() < timeout_ms:
            try:
                if predicate():
                    self.pump(settle_ms)
                    return True
            except Exception:
                pass
            self.pump(40)
        return False

    # ── blocking-call patches ────────────────────────────────────────────────
    def _register(self, widget):
        if widget is not None and widget not in self.opened:
            self.opened.append(widget)

    def _install_patches(self):
        QtWidgets, QtCore = self.QtWidgets, self.QtCore
        h = self

        def dialog_exec(self_, *a, **k):
            self_.setWindowModality(QtCore.Qt.NonModal)
            self_.show()
            h._register(self_)
            h.pump(150)
            if isinstance(self_, QtWidgets.QMessageBox):
                # A box built and exec'd directly (chisurf.gui.dialogs does this)
                # rather than through the static helpers: stays on screen to be
                # photographed, and a question takes the queued answer.
                h.messages.append({"title": self_.windowTitle(), "text": self_.text()})
                if int(self_.standardButtons()) & int(QtWidgets.QMessageBox.Yes):
                    if h.question_answers:
                        return h.question_answers.pop(0)
                    return h.question_answer
                return QtWidgets.QMessageBox.Ok
            result = h.dialog_results.pop(0) if h.dialog_results else h.dialog_result
            if result:
                # An accepted dialog closes, as it would after pressing OK.
                self_.hide()
                h.pump(50)
            return result

        for cls in (QtWidgets.QDialog, QtWidgets.QMessageBox, QtWidgets.QFileDialog,
                    QtWidgets.QInputDialog, QtWidgets.QProgressDialog):
            for name in ("exec_", "exec"):
                if hasattr(cls, name):
                    setattr(cls, name, dialog_exec)

        def menu_exec(self_, *a, **k):
            pos = None
            for arg in a:
                if isinstance(arg, QtCore.QPoint):
                    pos = arg
            if isinstance(self_, QtWidgets.QMenu):
                if h.menu_choice:
                    # Pick an entry, as a click on it would.
                    want, h.menu_choice = h.menu_choice, None
                    for act in self_.actions():
                        if act.text().replace("&", "").strip() == want:
                            return act
                    raise RuntimeError(f"context menu has no entry {want!r}")
                self_.popup(pos or QtCore.QPoint(200, 200))
                h._register(self_)
                h._menu_chain = [self_]
                h.pump(100)
            return None

        QtWidgets.QMenu.exec_ = menu_exec
        QtWidgets.QMenu.exec = menu_exec

        # QMessageBox static helpers -> a real, non-modal box that can be grabbed.
        def make_box(icon):
            def box(parent, title, text, *a, **k):
                mb = QtWidgets.QMessageBox(icon, str(title), str(text),
                                           QtWidgets.QMessageBox.Ok, parent)
                mb.setWindowModality(QtCore.Qt.NonModal)
                mb.show()
                h._register(mb)
                h.messages.append({"title": str(title), "text": str(text)})
                h.pump(100)
                if icon == QtWidgets.QMessageBox.Question:
                    if h.question_answers:
                        return h.question_answers.pop(0)
                    return h.question_answer
                return QtWidgets.QMessageBox.Ok
            return staticmethod(box)

        QtWidgets.QMessageBox.information = make_box(QtWidgets.QMessageBox.Information)
        QtWidgets.QMessageBox.warning = make_box(QtWidgets.QMessageBox.Warning)
        QtWidgets.QMessageBox.critical = make_box(QtWidgets.QMessageBox.Critical)
        QtWidgets.QMessageBox.question = make_box(QtWidgets.QMessageBox.Question)
        QtWidgets.QMessageBox.about = make_box(QtWidgets.QMessageBox.NoIcon)

        # QFileDialog static helpers -> queued answer, or a visible dialog + cancel.
        def file_dialog(kind):
            def get(parent=None, caption="", directory="", filter="", *a, **k):
                caption = k.get("caption", caption)
                directory = k.get("directory", directory)
                filter = k.get("filter", filter)
                if h.file_answers:
                    ans = h.file_answers.pop(0)
                    paths = ans if isinstance(ans, list) else [ans]
                    if kind == "names":
                        return (paths, "")
                    if kind == "dir":
                        return paths[0]
                    return (paths[0], "")
                dlg = QtWidgets.QFileDialog(parent, str(caption), str(directory or ""),
                                            str(filter or ""))
                dlg.setOption(QtWidgets.QFileDialog.DontUseNativeDialog, True)
                if kind == "dir":
                    dlg.setFileMode(QtWidgets.QFileDialog.Directory)
                elif kind == "names":
                    dlg.setFileMode(QtWidgets.QFileDialog.ExistingFiles)
                elif kind == "save":
                    dlg.setAcceptMode(QtWidgets.QFileDialog.AcceptSave)
                dlg.resize(760, 460)
                dlg.show()
                h._register(dlg)
                h.pump(300)
                if kind == "names":
                    return ([], "")
                if kind == "dir":
                    return ""
                return ("", "")
            return staticmethod(get)

        QtWidgets.QFileDialog.getOpenFileNames = file_dialog("names")
        QtWidgets.QFileDialog.getOpenFileName = file_dialog("name")
        QtWidgets.QFileDialog.getSaveFileName = file_dialog("save")
        QtWidgets.QFileDialog.getExistingDirectory = file_dialog("dir")

        def input_dialog(default_index):
            def get(parent, title, label, *a, **k):
                dlg = QtWidgets.QInputDialog(parent)
                dlg.setWindowTitle(str(title))
                dlg.setLabelText(str(label))
                dlg.show()
                h._register(dlg)
                h.pump(100)
                return (a[default_index] if len(a) > default_index else "", False)
            return staticmethod(get)

        QtWidgets.QInputDialog.getText = input_dialog(1)
        QtWidgets.QInputDialog.getItem = input_dialog(0)
        QtWidgets.QInputDialog.getInt = input_dialog(0)
        QtWidgets.QInputDialog.getDouble = input_dialog(0)

    # ── window ───────────────────────────────────────────────────────────────
    def build_window(self):
        import numpy as np

        np.random.seed(0)
        from ndxplorer.core.plot_main import NDXplorer

        import ndxplorer

        self.log["ndxplorer"] = str(Path(ndxplorer.__file__).parent)
        if self.sc.get("host") == "chisurf":
            self.win = self.build_chisurf_hosted()
        else:
            self.win = NDXplorer()
        self.win.resize(*WINDOW_SIZE)
        self.win.move(0, 0)
        self.win.show()
        ok = self.wait_until(lambda: self.win._deferred_init_done
                             and self.win.parameter_control is not None, 20000)
        self.pump(500)
        if not ok:
            raise RuntimeError("deferred init did not finish")

    def build_chisurf_hosted(self):
        """The window as ChiSurf's ribbon opens it: the plugin run as a macro.

        ChiSurf executes ``chisurf/plugins/ndxplorer/__init__.py`` with
        ``__name__ == "plugin"`` (``ribbon_plugins``: ``onRunMacro(...,
        globals={"__name__": "plugin"})``). That builds the window through
        ``rpc_bridge.make_ndxplorer`` (in-process ChiSurf client: the ChiSurf
        Phasor toolbar, the burst bridges, the calibration restore on open) and
        then adds the Accurate FRET and MMFDB toolbars and the Global View
        parameters. Running the same file the same way is the only honest
        baseline: nothing here re-implements the decoration.

        ``chisurf.gui.dialogs`` shows nothing on the offscreen platform (it
        answers with the default instead), so it is told the session is
        interactive; its boxes then reach the patched ``exec_`` like any other.
        """
        import chisurf.gui.dialogs as chisurf_dialogs

        chisurf_dialogs.is_interactive = lambda: True
        init = REPO.parents[1] / "chisurf" / "plugins" / "ndxplorer" / "__init__.py"
        self.log["chisurf_plugin"] = str(init)
        context = {"__name__": "plugin", "__file__": str(init)}
        exec(compile(init.read_text(encoding="utf-8"), str(init), "exec"), context)
        self.host_context = context
        return context["ndx"]

    def toolbar_action(self, label: str, toolbar: str = ""):
        """The toolbar action whose text (glyph ignored) is *label*."""
        W = self.QtWidgets
        for bar in self.win.findChildren(W.QToolBar):
            if toolbar and toolbar not in (bar.objectName(), bar.windowTitle()):
                continue
            for act in bar.actions():
                text = act.text().replace("&", "").strip()
                if text == label or text.endswith(" " + label):
                    return act
        raise RuntimeError(f"no toolbar action {label!r}")

    def toolbars(self) -> list:
        """``[{"name", "title", "visible", "actions"}]`` of the window's toolbars."""
        return [{"name": bar.objectName(), "title": bar.windowTitle(),
                 "visible": bar.isVisible(),
                 "actions": [a.text() for a in bar.actions() if a.text()]}
                for bar in self.win.findChildren(self.QtWidgets.QToolBar)]

    def ns(self) -> dict:
        import numpy as np

        return {"win": self.win, "pc": getattr(self.win, "plot_control", None),
                "host": self.host_context, "tool": self.toolbar_action,
                "app": self.app, "h": self, "np": np, "QtCore": self.QtCore,
                "QtGui": self.QtGui, "QtWidgets": self.QtWidgets,
                "last": self.opened[-1] if self.opened else None,
                "button": self.find_button, "child": self.find_child}

    def find_button(self, text: str, root=None):
        """The visible button whose label (glyphs and '&' ignored) is ``text``."""
        W = self.QtWidgets
        roots = [root] if root is not None else (
            [w for w in reversed(self.opened) if _alive(w) and w.isVisible()] + [self.win])
        for r in roots:
            for b in r.findChildren(W.QAbstractButton):
                label = b.text().replace("&", "").strip()
                if (label == text or label.endswith(" " + text)) and b.isVisible():
                    return b
        raise RuntimeError(f"no visible button labelled {text!r}")

    def find_child(self, cls_name: str, root=None, index: int = 0):
        W = self.QtWidgets
        cls = getattr(W, cls_name)
        found = [c for c in (root or self.win).findChildren(cls) if c.isVisible()]
        if len(found) <= index:
            raise RuntimeError(f"no visible {cls_name} #{index}")
        return found[index]

    def resolve(self, expr: str):
        return eval(expr, self.ns())

    # ── data readiness ───────────────────────────────────────────────────────
    def data_ready(self) -> bool:
        w = self.win
        ds = w.data_source
        return (ds is not None and not ds.empty and getattr(w, "_has_real_data", False)
                and w._histogram.get("2d") is not None
                and not getattr(w.plot_control, "_loading_data", False))

    def load_errors(self) -> list:
        return [m for m in self.messages if "Load Error" in m["title"]]

    def wait_data(self, timeout_ms=60000, expect_error=False):
        if expect_error:
            if not self.wait_until(lambda: bool(self.load_errors()), timeout_ms, settle_ms=300):
                raise RuntimeError("expected a load error, got none")
            return
        ok = self.wait_until(lambda: self.data_ready() or bool(self.load_errors()),
                             timeout_ms, settle_ms=800)
        if self.load_errors():
            raise RuntimeError("load failed: " + self.load_errors()[-1]["text"].strip()
                               .splitlines()[-1][:300])
        if not ok:
            raise RuntimeError("data did not finish loading / histogramming")
        self.wait_idle()

    def wait_idle(self, timeout_ms=30000):
        w = self.win

        def idle():
            timer = getattr(w, "_plot_update_timer", None)
            pending = getattr(w, "_plot_update_pending", False)
            return not pending and (timer is None or not timer.isActive())

        self.wait_until(idle, timeout_ms, settle_ms=400)

    # ── dock tabs ────────────────────────────────────────────────────────────
    def show_tab(self, title: str):
        area = self.win.dock_area
        for tw in area.findChildren(self.QtWidgets.QTabWidget):
            for i in range(tw.count()):
                if tw.tabText(i).strip() == title:
                    tw.setCurrentIndex(i)
                    self.pump(200)
                    return
        raise RuntimeError(f"no dock tab titled {title!r}")

    # ── menus ────────────────────────────────────────────────────────────────
    def open_menu(self, path: list[str]):
        """Pop up a menu-bar menu (and submenus) the way hovering would."""
        QtCore = self.QtCore
        bar = self.win.menuBar()
        actions = bar.actions()
        chain = []
        pos = QtCore.QPoint(0, 0)
        menu = None
        for depth, title in enumerate(path):
            act = next((a for a in actions if a.text().replace("&", "") == title), None)
            if act is None or act.menu() is None:
                raise RuntimeError(f"no menu {title!r} in {path}")
            menu = act.menu()
            if depth == 0:
                geo = bar.actionGeometry(act)
                pos = bar.mapToGlobal(geo.bottomLeft())
            else:
                parent = chain[-1]
                geo = parent.actionGeometry(act)
                parent.setActiveAction(act)
                pos = parent.mapToGlobal(geo.topRight())
            menu.popup(pos)
            self.pump(150)
            chain.append(menu)
            actions = menu.actions()
        self._menu_chain = chain
        for m in chain:
            self._register(m)

    # ── mouse on the 2-D canvas ──────────────────────────────────────────────
    def _canvas_point(self, widget, fx, fy):
        return self.QtCore.QPoint(int(fx * widget.width()), int(fy * widget.height()))

    def send_mouse(self, widget, etype, pos, button, buttons):
        QtGui, QtCore = self.QtGui, self.QtCore
        ev = QtGui.QMouseEvent(etype, QtCore.QPointF(pos), widget.mapToGlobal(pos),
                               button, buttons, QtCore.Qt.NoModifier)
        self.app.sendEvent(widget, ev)

    def drag(self, widget, start, end, steps=8):
        QtCore = self.QtCore
        p0 = self._canvas_point(widget, *start)
        p1 = self._canvas_point(widget, *end)
        L = QtCore.Qt.LeftButton
        self.send_mouse(widget, QtCore.QEvent.MouseButtonPress, p0, L, L)
        for i in range(1, steps + 1):
            p = QtCore.QPoint(p0.x() + (p1.x() - p0.x()) * i // steps,
                              p0.y() + (p1.y() - p0.y()) * i // steps)
            self.send_mouse(widget, QtCore.QEvent.MouseMove, p, QtCore.Qt.NoButton, L)
            self.pump(20)
        self.send_mouse(widget, QtCore.QEvent.MouseButtonRelease, p1, L, QtCore.Qt.NoButton)
        self.pump(200)

    def click_at(self, widget, at, button="left"):
        QtCore = self.QtCore
        b = QtCore.Qt.LeftButton if button == "left" else QtCore.Qt.RightButton
        p = self._canvas_point(widget, *at)
        self.send_mouse(widget, QtCore.QEvent.MouseButtonPress, p, b, b)
        self.send_mouse(widget, QtCore.QEvent.MouseButtonRelease, p, b, QtCore.Qt.NoButton)
        if button == "right":
            ev = self.QtGui.QContextMenuEvent(self.QtGui.QContextMenuEvent.Mouse, p,
                                              widget.mapToGlobal(p))
            self.app.sendEvent(widget, ev)
        self.pump(200)

    # ── widget setters ───────────────────────────────────────────────────────
    def set_value(self, widget, value):
        W = self.QtWidgets
        if isinstance(widget, W.QComboBox):
            i = widget.findText(str(value))
            if i < 0:
                raise RuntimeError(f"{value!r} not in combo ({widget.count()} items)")
            widget.setCurrentIndex(i)
        elif isinstance(widget, (W.QCheckBox, W.QRadioButton, W.QAction)) or (
                hasattr(widget, "setChecked") and isinstance(value, bool)):
            widget.setChecked(bool(value))
        elif isinstance(widget, W.QLineEdit):
            widget.setText(str(value))
            widget.editingFinished.emit()
        elif hasattr(widget, "setValue"):
            widget.setValue(value)
        elif hasattr(widget, "setText"):
            widget.setText(str(value))
        else:
            raise RuntimeError(f"do not know how to set {type(widget).__name__}")
        self.pump(100)

    # ── captures ─────────────────────────────────────────────────────────────
    def _target_widget(self, target: str):
        W = self.QtWidgets
        if target in ("window", "main"):
            return self.win
        if target == "dialog" or target.startswith("dialog:"):
            live = [w for w in self.opened
                    if not isinstance(w, W.QMenu) and _alive(w) and w.isVisible()]
            if target.startswith("dialog:"):
                key = target.split(":", 1)[1]
                # A message box is found by its text too: macOS ignores (and
                # reports empty) a QMessageBox's window title.
                live = [w for w in live if key in type(w).__name__ or key in w.windowTitle()
                        or (isinstance(w, W.QMessageBox) and key in w.text())]
            if not live:
                raise RuntimeError(f"no open dialog for capture target {target!r}")
            return live[-1]
        if target == "menu":
            return "menu"
        if target.startswith("widget:"):
            return self.resolve(target.split(":", 1)[1])
        raise RuntimeError(f"unknown capture target {target!r}")

    def grab_menus(self):
        """All open menus of the current chain, painted side by side."""
        QtGui, QtCore = self.QtGui, self.QtCore
        menus = [m for m in getattr(self, "_menu_chain", []) if m.isVisible()]
        if not menus:
            menus = [m for m in self.opened
                     if isinstance(m, self.QtWidgets.QMenu) and _alive(m) and m.isVisible()]
            menus = menus[-1:]
        if not menus:
            raise RuntimeError("no open menu to capture")
        pix = [m.grab() for m in menus]
        width = sum(p.width() for p in pix) + 8 * (len(pix) - 1)
        height = max(p.height() for p in pix)
        canvas = QtGui.QPixmap(width, height)
        canvas.fill(QtGui.QColor("white"))
        painter = QtGui.QPainter(canvas)
        x = 0
        for p in pix:
            painter.drawPixmap(x, 0, p)
            x += p.width() + 8
        painter.end()
        return canvas

    def capture(self, name: str, target: str = "window"):
        self.pump(250)
        widget = self._target_widget(target)
        if widget == "menu":
            pix = self.grab_menus()
        else:
            if hasattr(widget, "raise_"):
                widget.raise_()
            self.pump(100)
            pix = widget.grab()
        sid = self.sc["id"]
        fname = f"{sid}.png" if name == "main" else f"{sid}--{name}.png"
        path = self.out / fname
        pix.save(str(path), "PNG")
        blank = _looks_blank(pix.toImage())
        entry = {"name": name, "file": fname, "target": target,
                 "size": [pix.width(), pix.height()], "blank": blank}
        self.log["captures"].append(entry)
        if blank:
            self.log["errors"].append(f"capture {name!r} looks blank")

    # ── the step interpreter ─────────────────────────────────────────────────
    def run_step(self, step: dict):
        op = step["op"]
        a = expand(step, self.datasets)
        QtWidgets = self.QtWidgets
        if op == "open":
            # Through the File menu: queue what the file dialog will answer, then
            # trigger the action (or the CLI path for "cli").
            via = a.get("via", "action")
            path = a["path"]
            if a.get("copy"):
                # Open a copy in the scratch $HOME: the scenario writes into the
                # container (a calibration is stored in the .pto), and the
                # user's measurement is never the one written.
                copy = Path(os.environ["HOME"]) / Path(path).name
                if not copy.exists():
                    shutil.copyfile(path, copy)
                path = str(copy)
                self.log["opened_copy"] = path
            if via == "cli":
                from ndxplorer.__main__ import open_path_like_drop
                open_path_like_drop(self.win, path)
            else:
                self.file_answers.append(path if isinstance(path, list) else [path])
                # A window that already holds data asks how to merge; answer it
                # with its default (replace) unless the step says otherwise.
                previous, self.dialog_result = self.dialog_result, int(a.get("dialog_result", 1))
                try:
                    getattr(self.win, a["action"]).trigger()
                finally:
                    self.dialog_result = previous
            if a.get("wait", True):
                self.wait_data(a.get("timeout", 90000), a.get("expect_error", False))
        elif op == "file_answer":
            self.file_answers.append(a["path"] if isinstance(a["path"], list) else [a["path"]])
        elif op == "menu_choice":
            self.menu_choice = a["text"]
        elif op == "dialog_result":
            self.dialog_result = int(a["value"])
        elif op == "dialog_results":
            self.dialog_results = [int(v) for v in a["values"]]
        elif op == "question_answer":
            self.question_answer = (QtWidgets.QMessageBox.Yes if a["value"] == "yes"
                                    else QtWidgets.QMessageBox.No)
        elif op == "question_answers":
            buttons = {"yes": QtWidgets.QMessageBox.Yes, "no": QtWidgets.QMessageBox.No,
                       "cancel": QtWidgets.QMessageBox.Cancel}
            self.question_answers = [buttons[v] for v in a["values"]]
        elif op == "set":
            self.set_value(self.resolve(a["widget"]), a["value"])
        elif op == "axis":
            combo = getattr(self.win.plot_control,
                            {"x": "comboBoxSelX", "y": "comboBoxSelY", "z": "comboBoxSelZ",
                             "weight": "comboBoxWeight"}[a["axis"]])
            self.set_value(combo, a["name"])
        elif op == "click":
            self.resolve(a["widget"]).click()
            self.pump(200)
        elif op == "trigger":
            act = getattr(self.win, a["action"]) if not a["action"].startswith(
                ("win.", "pc.", "last", "tool(")) else self.resolve(a["action"])
            if a.get("checked") is not None:
                act.setChecked(bool(a["checked"]))
            else:
                act.trigger()
            self.pump(300)
        elif op == "tab":
            self.show_tab(a["title"])
        elif op == "menu":
            self.open_menu(a["path"])
        elif op == "close_menus":
            for m in self.opened:
                if isinstance(m, QtWidgets.QMenu) and _alive(m):
                    m.hide()
            self._menu_chain = []
            self.pump(100)
        elif op == "close_dialogs":
            for d in self.opened:
                if _alive(d) and not isinstance(d, QtWidgets.QMenu):
                    d.hide()
            self.pump(100)
        elif op == "drag":
            self.drag(self.resolve(a.get("widget", "win.overlay_plot")),
                      a["start"], a["end"])
        elif op == "canvas_click":
            self.click_at(self.resolve(a.get("widget", "win.overlay_plot")), a["at"],
                          a.get("button", "left"))
        elif op == "call":
            exec(a["code"], self.ns())
            self.pump(200)
        elif op == "wait":
            self.pump(int(a.get("ms", 500)))
        elif op == "wait_until":
            ok = self.wait_until(lambda: bool(self.resolve(a["expr"])),
                                 int(a.get("timeout", 60000)))
            if not ok:
                raise RuntimeError(f"timed out waiting for {a['expr']}")
        elif op == "wait_plot":
            self.wait_idle()
        elif op == "resize_dialog":
            d = self._target_widget(a.get("target", "dialog"))
            d.resize(*a["size"])
            self.pump(200)
        elif op == "capture":
            self.capture(a.get("name", "main"), a.get("target", "window"))
        else:
            raise RuntimeError(f"unknown op {op!r}")

    def run(self):
        t0 = time.time()
        try:
            self.build_window()
            for i, step in enumerate(self.sc["steps"]):
                entry = {"i": i, "op": step["op"]}
                try:
                    self.run_step(step)
                    entry["ok"] = True
                except Exception as exc:
                    entry["ok"] = False
                    entry["error"] = f"{type(exc).__name__}: {exc}"
                    self.log["errors"].append(f"step {i} ({step['op']}): {entry['error']}")
                    self.log["traceback"] = traceback.format_exc()
                    if step.get("optional"):
                        self.log["steps"].append(entry)
                        continue
                    self.log["steps"].append(entry)
                    self.log["status"] = "failed"
                    break
                self.log["steps"].append(entry)
            if self.sc.get("host") == "chisurf":
                # What the host added, in words: the report and the emtk side
                # compare this inventory, not only the pictures.
                self.log["toolbars"] = self.toolbars()
                self.log["constants"] = {k: float(v) for k, v in dict(
                    getattr(self.win, "constants", {}) or {}).items()
                    if isinstance(v, (int, float))}
            # Every scenario ends with the main window, unless it captured it itself.
            if not any(c["name"] == "main" for c in self.log["captures"]):
                try:
                    self.capture("main", "window")
                except Exception as exc:
                    self.log["errors"].append(f"final capture: {exc}")
        except Exception as exc:
            self.log["status"] = "failed"
            self.log["errors"].append(f"{type(exc).__name__}: {exc}")
            self.log["traceback"] = traceback.format_exc()
        if self.log["status"] == "ok" and any(c["blank"] for c in self.log["captures"]):
            self.log["status"] = "blank"
        self.log["seconds"] = round(time.time() - t0, 1)
        (self.out / f"{self.sc['id']}.log.json").write_text(json.dumps(self.log, indent=2))
        return 0 if self.log["status"] == "ok" else 1


def _alive(widget) -> bool:
    try:
        from qtpy import sip  # type: ignore
        return not sip.isdeleted(widget)
    except Exception:
        try:
            widget.objectName()
            return True
        except RuntimeError:
            return False


def _looks_blank(image) -> bool:
    """A capture with (almost) a single colour is a failed render, not a UI."""
    w, h = image.width(), image.height()
    if w < 8 or h < 8:
        return True
    colours = set()
    step_x, step_y = max(1, w // 64), max(1, h // 64)
    for y in range(0, h, step_y):
        for x in range(0, w, step_x):
            colours.add(image.pixel(x, y))
            if len(colours) > 4:
                return False
    return True


def run_one(sid: str, out: Path) -> int:
    with open(SCENARIOS, encoding="utf-8") as fh:
        doc = json.load(fh)
    sc = dict(next(s for s in doc["scenarios"] if s["id"] == sid))
    setups = doc.get("setups", {})
    prefix = []
    for name in ([sc["setup"]] if isinstance(sc.get("setup"), str) else sc.get("setup", [])):
        prefix += setups[name]
    sc["steps"] = prefix + sc.get("steps", [])
    out.mkdir(parents=True, exist_ok=True)
    h = Harness(sc, doc.get("datasets", {}), out)
    rc = h.run()
    # Tear down hard: some worker threads (UMAP, clustering) do not stop politely,
    # and the log is already written.
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(rc)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("-s", "--scenario", action="append", default=[],
                    help="scenario id to run (repeatable; default: all)")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    ap.add_argument("--timeout", type=int, default=300, help="seconds per scenario")
    ap.add_argument("--python", default=sys.executable,
                    help="interpreter for the scenario subprocesses")
    ap.add_argument("--app-root", type=Path, default=None,
                    help="import ndxplorer from this source tree instead of this checkout "
                         "(e.g. a `git archive HEAD` export, so concurrent edits in the "
                         "working tree do not leak into the baseline)")
    ap.add_argument("--list", action="store_true")
    ap.add_argument("--run-one", help=argparse.SUPPRESS)
    args = ap.parse_args(argv)
    if args.list:
        for s in load_scenarios():
            print(f"{s['id']:34s} {s['title']}")
        return 0
    if args.app_root:
        os.environ["NDX_PARITY_APP_ROOT"] = str(args.app_root.resolve())
    if args.run_one:
        return run_one(args.run_one, args.out)
    return run_all(args.scenario, args.out, args.timeout, args.python)


if __name__ == "__main__":
    sys.exit(main())
