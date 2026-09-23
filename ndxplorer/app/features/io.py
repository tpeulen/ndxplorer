"""Opening and saving: the io feature of the emtk app.

What it owns:

* File > Import (text files, analysis file, analysis folder, ChiSurf
  sampling): the merge question when data is already loaded, the file or
  folder dialog, the load on a worker thread with a progress window, and a
  "Data Load Error" box with the reader's reason when it fails;
* image mode: a table with ``X pixel``/``Y pixel`` columns is shown as the
  image it is -- one bin per pixel, weighted by photons, NaN/inf masks off
  (:func:`ndxplorer.utils.axis_helpers.image_axes`), however it was opened;
* the working path's *Browse*;
* Save > Burst IDs and the Selection panel's *BID*: a folder, the ``.bst``
  files, then the "Process Burst IDs" question;
* the Selection panel's *save* and *load* (``*.selection.json``);
* *Screenshot*: the window as PNG, JPEG or BMP.

Which reader, which dialog caption and filters, and what a merge does are
:mod:`ndxplorer.io.loading`'s, shared with the Qt window. The files go
through :class:`~.io_service.FileService`, attached as ``app.io_service`` so
every feature asks the same object -- drawn emtk file dialogs on a desktop;
the dropped files, the mounted folder and downloads in a browser.

The dialogs are ``view.json`` specs beside this module (``io/``), drawn by
:mod:`emtk.view_form`.
"""

from __future__ import annotations

import io as _stdio
import json
import logging
import pathlib
import re
import threading
from typing import Any, Callable, Dict, List, Optional

from . import Feature
from .io_service import FileService

__all__ = ["IoFeature", "create"]

logger = logging.getLogger(__name__)

SPECS = pathlib.Path(__file__).with_name("io")

#: The app actions of File > Import, and the importer (:data:`ndxplorer.io.loading.IMPORTERS`)
#: each one runs.
IMPORT_ACTIONS: Dict[str, str] = {
    "open_text": "csv",
    "open_analysis_file": "mfd_hdf5",
    "open_analysis_folder": "burst_dir",
    "open_sampling": "cs_sampling",
}

#: Qt buttons of the io scenarios -> the app's actions (``click`` steps).
BUTTONS: Dict[str, str] = {
    "pc.toolButton": "save_burst_ids",
    "pc.toolButtonSaveSelection": "save_gates",
    "pc.toolButtonLoadSelection": "load_gates",
    "win.toolButton_screenshot": "screenshot",
    "win.toolButtonChangePath": "browse",
}

#: Qt menu actions of the io scenarios -> the app's actions.
QT_ACTIONS: Dict[str, str] = {
    "actionSave_Burst_IDs": "save_burst_ids",
}

SELECTION_FILTERS = "All files (*.selection.json)"


def load_spec(name: str) -> dict:
    """One of this feature's dialog specs, parsed."""
    with open(SPECS / f"{name}.view.json", encoding="utf-8") as handle:
        return json.load(handle)


# --------------------------------------------------------------- dialog models
class _Dialog:
    """A small dialog: its spec, what its fields bind to, where it was drawn."""

    spec_name = ""
    width, height = 480.0, 170.0

    def __init__(self, title: str) -> None:
        from emtk.dialog_window import DialogWindow
        from emtk.view_form import FormState

        self.title = title
        self.spec = load_spec(self.spec_name)
        self.form = FormState()
        self.done = False
        self.window = DialogWindow(title, size=(self.width, self.height), key=self.spec_name)

    @property
    def box(self) -> Optional[tuple]:
        return self.window.box

    def enabled(self, _name: str) -> bool:
        return True

    def cancel(self) -> None:
        self.done = True

    def draw(self, frame: tuple) -> None:
        from emtk.view_form import draw_form

        pressed = self.window.begin(frame)
        draw_form(self.spec, self, self.form, titles=False)
        self.window.end()
        if pressed == "close":
            self.cancel()


class MergeQuestion(_Dialog):
    """"How do you want to merge the new data?": replace, or append columns or rows.

    ``then(append, merge_mode)`` runs on OK; Cancel aborts the import.
    """

    spec_name = "merge"
    width, height = 520.0, 190.0

    def __init__(self, title: str, then: Callable[[bool, str], None]) -> None:
        super().__init__(title)
        self.then = then
        self.choice = 0

    def prompt(self) -> str:
        from ...io.loading import MERGE_PROMPT

        return MERGE_PROMPT

    def choice_options(self) -> list:
        from ...io.loading import MERGE_CHOICES

        return [(i, label) for i, (_mode, label) in enumerate(MERGE_CHOICES)]

    def ok(self) -> None:
        from ...io.loading import merge_choice

        self.done = True
        self.then(*merge_choice(int(self.choice)))

    def cancel(self) -> None:
        self.done = True


class BurstIdQuestion(_Dialog):
    """"Process Burst IDs": what to do with the ``.bst`` files just written."""

    spec_name = "burst_ids"
    width, height = 470.0, 175.0

    def __init__(self, folder: str, then: Callable[["BurstIdQuestion"], None]) -> None:
        super().__init__("Process Burst IDs")
        self.folder = folder
        self.then = then
        self.microtime_histogram = True
        self.correlate = False

    def ok(self) -> None:
        self.done = True
        self.then(self)

    def cancel(self) -> None:
        self.done = True


class Task(_Dialog):
    """Work off the window's thread, with a progress window and Cancel.

    On a desktop *work* runs on a thread and the window keeps drawing (the
    feature says it is :meth:`IoFeature.animating`); in a browser there are no
    threads, and it runs on the next frame. ``work(task)`` may read
    :attr:`cancelled` and set :attr:`detail`; ``finish(result)`` or
    ``fail(exception)`` run on the window's thread afterwards.
    """

    spec_name = "progress"
    width, height = 440.0, 150.0

    def __init__(self, title: str, message: str, work: Callable[["Task"], Any],
                 finish: Callable[[Any], None], fail: Callable[[BaseException], None],
                 threaded: bool = True) -> None:
        super().__init__(title)
        self.text = message
        self.detail_text = ""
        self.work, self.finish_cb, self.fail_cb = work, finish, fail
        self.cancelled = False
        self.result: Any = None
        self.error: Optional[BaseException] = None
        self.finished = threading.Event()
        self.thread: Optional[threading.Thread] = None
        if threaded:
            self.thread = threading.Thread(target=self._run, name=f"ndx-{title}", daemon=True)
            self.thread.start()

    def message(self) -> str:
        return self.text

    def detail(self) -> str:
        return self.detail_text

    def cancel(self) -> None:
        self.cancelled = True
        self.detail_text = "Cancelling…"

    def _run(self) -> None:
        try:
            self.result = self.work(self)
        except BaseException as exc:  # noqa: BLE001 - handed to fail() on the window's thread
            self.error = exc
        finally:
            self.finished.set()

    def poll(self) -> bool:
        """Run (unthreaded) or collect (threaded) the work; ``True`` once handled."""
        if self.thread is None and not self.finished.is_set():
            self._run()
        if not self.finished.is_set():
            return False
        self.done = True
        if self.error is not None:
            self.fail_cb(self.error)
        else:
            self.finish_cb(self.result)
        return True

    def wait(self, timeout: Optional[float] = None) -> bool:
        """Block until the work is done (tests and scenario replays)."""
        if self.thread is not None:
            self.thread.join(timeout)
        return self.poll()


# -------------------------------------------------------------------- feature
class IoFeature(Feature):
    """Open, merge and save; owns ``app.io_service``."""

    name = "io"

    def __init__(self, app) -> None:
        super().__init__(app)
        self.service = FileService(working_path=lambda: app.model.working_path,
                                   report=self._report)
        app.io_service = self.service
        #: The dialog on screen that is not a file dialog (merge, BID, progress).
        self.dialog: Optional[_Dialog] = None
        self.task: Optional[Task] = None
        #: Messages still to show after the one on screen.
        self.messages: List[tuple] = []
        #: Answers a scenario queued for the next file dialogs (``h.file_answers``).
        self.file_answers: List[Any] = []
        self._image_for: Optional[int] = None
        self._screenshot_pending = False
        self._rendering = False

    # ------------------------------------------------------------ plumbing
    def _report(self, title: str, text: str) -> None:
        """A message box; one after another when several come at once."""
        if self.app.message is None:
            self.app.message = (title, text)
        else:
            self.messages.append((title, text))

    @property
    def threaded(self) -> bool:
        return not self.service.browser

    def _run(self, title: str, message: str, work, finish, fail) -> Task:
        self.task = Task(title, message, work, finish, fail, threaded=self.threaded)
        return self.task

    # --------------------------------------------------------------- hooks
    def actions(self) -> Dict[str, Callable[[], Any]]:
        actions = {name: (lambda kind=kind: self.import_data(kind))
                   for name, kind in IMPORT_ACTIONS.items()}
        actions.update(browse=self.browse, save_burst_ids=self.save_burst_ids,
                       save_gates=self.save_gates, load_gates=self.load_gates,
                       screenshot=self.screenshot)
        return actions

    def available(self, action: str) -> Optional[bool]:
        if self.task is not None and action in self.actions():
            return False
        if action in IMPORT_ACTIONS or action == "browse":
            return True
        if action == "save_burst_ids":
            return self.app.model.has_data and self._has_burst_columns()
        if action in ("save_gates", "load_gates", "screenshot"):
            return self.app.model.has_data if action != "screenshot" else True
        return None

    def animating(self) -> bool:
        return self.task is not None

    def draw_windows(self) -> bool:
        if self._rendering:
            return False
        if self._screenshot_pending:
            self._screenshot_pending = False
            self._take_screenshot()
        if self.app.message is None and self.messages:
            self.app.message = self.messages.pop(0)
        modal = False
        if self.task is not None:
            if self.task.poll():
                self.task = None
            else:
                self.task.draw(self.app.box)
                modal = True
        if self.dialog is not None and self.task is None:
            self.dialog.draw(self.app.box)
            if self.dialog is not None and self.dialog.done:
                self.dialog = None
            modal = True
        if self.service.draw(self.app.box):
            modal = True
        return modal

    def on_data_changed(self) -> None:
        self._apply_image_mode()

    # ---------------------------------------------------------------- open
    def import_data(self, kind: str) -> None:
        """A File > Import entry: the merge question first when data is loaded."""
        from ...io.loading import IMPORTERS

        importer = IMPORTERS[kind]
        if self.app.model.has_data:
            self.dialog = MergeQuestion(
                importer.merge_title,
                lambda append, mode: self._ask_paths(importer, append, mode))
        else:
            self._ask_paths(importer, False, "columns")

    def _ask_paths(self, importer, append: bool, mode: str) -> None:
        def chosen(paths) -> None:
            paths = [paths] if isinstance(paths, str) else list(paths)
            self.load(paths, importer.kind, append=append, merge_mode=mode)

        if importer.mode == "folder":
            self.service.ask_folder(importer.title, chosen)
        else:
            self.service.ask_open(importer.title, list(importer.filters), chosen,
                                  multiple=importer.multiple)
        self._answer_from_queue()

    def load(self, paths: List[str], kind: Optional[str] = None, append: bool = False,
             merge_mode: str = "columns") -> Task:
        """Read *paths* in the background; replace the table, or merge into it."""
        from ...io import loading

        manager = self.app.model.manager
        equations, constants = list(manager.equations or []), dict(manager.constants or {})
        names = ", ".join(pathlib.Path(p).name for p in paths[:3]) + \
            (f" (+{len(paths) - 3})" if len(paths) > 3 else "")

        def work(_task):
            return loading.load(paths, kind, merge_mode, equations=equations,
                                constants=constants)

        return self._run("Loading", f"Loading {names}…", work,
                         lambda source: self._loaded(paths, source, append, merge_mode),
                         lambda exc: self._load_failed(paths, exc))

    def _load_failed(self, paths, exc: BaseException) -> None:
        logger.error("Failed to load %s: %s", paths, exc)
        self.app.model.error = f"Failed to load data: {exc}"
        self._report("Data Load Error", self.app.model.error)

    def _loaded(self, paths: List[str], source, append: bool, merge_mode: str) -> None:
        from ...io import loading

        model = self.app.model
        if source is None or source.empty:
            model.error = f"No data in {', '.join(paths)}"
            self._report("Data Load Error", model.error)
            return
        model.error = ""
        if append and model.has_data:
            if not loading.merge(model.source, source, merge_mode, warn=self._report):
                return
            model.manager.data_source = model.source
            model.source = model.manager.data_source
            model.invalidate()
        else:
            model.set_source(source)
            model.path = paths[0]
        model.working_path = loading.working_path_for(paths)
        self.app.title = loading.window_title(paths) if not append else getattr(
            self.app, "title", "ndX")
        self.app.data_changed()

    # --------------------------------------------------------- image mode
    def _apply_image_mode(self) -> None:
        """Show a freshly opened image table as an image (once per table)."""
        from ...utils.axis_helpers import image_axes

        model = self.app.model
        if not model.has_data or self._image_for == id(model.source):
            return
        self._image_for = id(model.source)
        image = image_axes(model.source)
        if image is None:
            return
        for key, name, n in (("x", image.x, image.nx), ("y", image.y, image.ny)):
            model.set_parameter(key, name)
            axis = model.axis(key)
            axis.bins_1d = axis.bins_2d = int(n)
            axis.lo, axis.hi = 0.0, float(n)
            axis.log = False
        if image.weight:
            model.weight_name = image.weight
            model.weight_enabled = True
        # Pixel coordinates are always finite: a NaN/inf mask on them can only
        # remove real pixels.
        model.mask_nan = model.mask_inf = False
        model.invalidate()

    # -------------------------------------------------------- working path
    def browse(self) -> None:
        """*Browse*: choose the working folder."""
        def chosen(path: str) -> None:
            self.app.model.working_path = str(path)

        self.service.ask_folder("Select current path", chosen)
        self._answer_from_queue()

    # ----------------------------------------------------------- burst IDs
    def _has_burst_columns(self) -> bool:
        names = set(self.app.model.parameter_names)
        return {"First File", "Last File", "First Photon", "Last Photon"} <= names

    def _selections(self) -> list:
        return list(self.app.model.gates.selections())

    def save_burst_ids(self) -> None:
        """Save > Burst IDs / *BID*: a folder, the ``.bst`` files, then what next."""
        self.service.ask_folder("Folder for Burst IDs", self._write_burst_ids)
        self._answer_from_queue()

    def _write_burst_ids(self, folder: str) -> None:
        from ...io.writer import save_burst_ids_headless

        selections, source = self._selections(), self.app.model.source

        def work(task: Task):
            def progress(done: int, total: int) -> bool:
                task.detail_text = f"{done} / {total} files"
                return not task.cancelled

            return save_burst_ids_headless(folder, selections, source, progress=progress)

        def finish(written) -> None:
            logger.info("wrote %d burst-ID files to %s", len(written), folder)
            self.dialog = BurstIdQuestion(folder, self._process_burst_ids)

        def fail(exc: BaseException) -> None:
            self._report("Save Burst IDs", f"Could not save the burst IDs: {exc}")

        self._run("Saving Files", "Saving Burst ID files...", work, finish, fail)

    def _process_burst_ids(self, question: BurstIdQuestion) -> None:
        """The follow-ups the Qt window offers, with what this app can do about them."""
        from ...io.writer import find_bst_files

        if question.microtime_histogram:
            self._report("Plugin Not Available",
                         "The Microtime Histogram plugin (chisurf) is not available in this "
                         "standalone build.")
        if question.correlate:
            files = find_bst_files(question.folder)
            if not files:
                self._report("No BST Files Found",
                             "No .bst files were found in the selected folder.")
            else:
                self._report("Plugin Not Available",
                             "The FCS Correlator Wizard is a ChiSurf plugin and does not run in "
                             f"this window. Open the {len(files)} .bst file(s) in "
                             f"{question.folder} with ChiSurf's FCS correlator.")

    # --------------------------------------------------------- selections
    def _selection_axes(self) -> tuple:
        model = self.app.model
        return (max(model.index_of(model.x.name), 0), max(model.index_of(model.y.name), 0))

    def save_gates(self) -> None:
        """The Selection panel's *save*: the gates to a ``*.selection.json``."""
        from ...core.region_selection import save_selections

        def chosen(path: str) -> None:
            if not path.endswith(".selection.json"):
                path = re.sub(r"(\.selection)?(\.json)?$", "", path) + ".selection.json"
            save_selections(self._selections(), path, axes=self._selection_axes())
            logger.info("gates saved to %s", path)

        self.service.ask_save("Selection JSON", SELECTION_FILTERS, "", chosen)
        self._answer_from_queue()

    def load_gates(self) -> None:
        """The Selection panel's *load*: gates of any shape, added to the table."""
        from ...core.region_selection import load_selections

        def chosen(paths: List[str]) -> None:
            model = self.app.model
            for selection in load_selections(paths[0], axes=self._selection_axes()):
                if not getattr(selection, "name", ""):
                    index = getattr(selection, "parameter_idx", -1)
                    names = model.parameter_names
                    if 0 <= index < len(names):
                        selection.name = names[index]
                model.gates.add_selection(selection)
            model.invalidate()

        self.service.ask_open("Selection JSON", SELECTION_FILTERS, chosen)
        self._answer_from_queue()

    # ---------------------------------------------------------- screenshot
    def screenshot(self) -> None:
        """*Screenshot*: the window, saved as PNG, JPEG or BMP (a download in a page)."""
        self._screenshot_pending = True

    def render_window(self):
        """The window as a PIL image, drawn again without the dialogs over it."""
        import emtk
        from emtk.pil_painter import PilPainter

        app = self.app
        x, y, w, h = app.box
        painter = PilPainter(int(round(w)), int(round(h)))
        saved_io, saved_message = app.io, app.message
        app.io, app.message = emtk.IO(), None
        app.io.mouse_pos = (-1e6, -1e6)
        self._rendering = True
        try:
            app.draw(painter, 0.0, 0.0, float(w), float(h))
        finally:
            self._rendering = False
            app.io, app.message = saved_io, saved_message
        return painter.frame

    def _take_screenshot(self) -> None:
        from ...export.screenshots import (
            SCREENSHOT_FILTERS,
            SCREENSHOT_TITLE,
            default_screenshot_name,
            screenshot_format,
        )

        image = self.render_window()
        if self.service.browser:
            buffer = _stdio.BytesIO()
            image.convert("RGB").save(buffer, "PNG")
            self.service.save_bytes(default_screenshot_name(), buffer.getvalue(), "image/png")
            return

        def chosen(path: str) -> None:
            filename, fmt = screenshot_format(path)
            (image.convert("RGB") if fmt != "PNG" else image).save(filename, fmt)
            logger.info("Saved screenshot to %s", filename)

        self.service.ask_save(SCREENSHOT_TITLE, SCREENSHOT_FILTERS,
                              default_screenshot_name(), chosen)
        self._answer_from_queue()

    # ------------------------------------------------------------ capture
    def _answer_from_queue(self) -> None:
        """A scenario queued the answer to this dialog (``h.file_answers``)."""
        if self.file_answers and self.service.busy:
            self.service.answer(self.file_answers.pop(0))

    def capture_actions(self) -> Dict[str, str]:
        return dict(QT_ACTIONS)

    def capture_ops(self) -> Dict[str, Callable]:
        return {"open": self._op_open, "click": self._op_click, "call": self._op_call}

    def capture_targets(self) -> Dict[str, Callable]:
        return {"dialog:QFileDialog": lambda replay: self.service.box,
                "dialog": lambda replay: self._dialog_box()}

    def _dialog_box(self) -> Optional[tuple]:
        if self.app.message is not None:
            return None
        if self.service.busy:
            return self.service.box
        for dialog in (self.dialog, self.task):
            if dialog is not None and dialog.box is not None:
                return dialog.box
        return None

    def _op_open(self, replay, step: dict):
        """``open``: the File > Import entry, answered with the file, and the load awaited.

        ``via: "cli"`` (``ndx --file``, a drop) is the core's open.
        """
        action = replay.actions().get(step.get("action", ""))
        if step.get("via") == "cli" or action not in IMPORT_ACTIONS:
            return False
        path = replay.dataset(step["path"])
        replay.settle()
        if not self.app.run_action(action):
            from ..capture import Unsupported

            raise Unsupported(f"action {action!r} is not available")
        replay.draw()
        if isinstance(self.dialog, MergeQuestion):
            self.dialog.ok()           # the Qt harness answers Replace, the default
            self.dialog = None
        self.service.answer([path])
        if self.task is not None:
            self.task.wait(float(step.get("timeout", 180000)) / 1000.0)
            self.task = None
        replay.settle(3)
        from ..capture import Unsupported

        if step.get("expect_error"):
            if self.app.message is None:
                raise Unsupported("expected a load error, the file opened")
        elif self.app.message is not None and self.app.message[0] == "Data Load Error":
            raise Unsupported(f"could not open {step['path']}: {self.app.message[1]}")
        return True

    def _op_click(self, replay, step: dict):
        action = BUTTONS.get(step.get("widget", ""))
        if action is None:
            return False
        for form in self.app.forms.values():
            if action in form.rects:
                replay.click_rect(form.rects[action])
                break
        else:
            if not self.app.run_action(action):
                from ..capture import Unsupported

                raise Unsupported(f"button {step['widget']!r} ({action}) is not available")
        replay.settle(3)
        self._answer_from_queue()
        if self.task is not None:
            self.task.wait(60.0)
            self.task = None
        replay.settle(2)
        return True

    def _op_call(self, replay, step: dict):
        """``h.file_answers.append([...])``: the answer to the next file dialog."""
        code = step.get("code", "")
        if "h.file_answers.append" not in code:
            return False
        import tempfile

        if "tempfile.mkdtemp" in code:
            prefix = re.search(r"prefix=['\"]([^'\"]+)['\"]", code)
            self.file_answers.append(tempfile.mkdtemp(prefix=prefix.group(1) if prefix else "ndx-"))
            return True
        literal = re.search(r"h\.file_answers\.append\((.*)\)\s*$", code, re.S)
        if literal is None:
            return False
        import ast

        try:
            answer = ast.literal_eval(literal.group(1))
        except (ValueError, SyntaxError):
            return False
        self.file_answers.append(answer[0] if isinstance(answer, list) and answer else answer)
        return True


def create(app) -> IoFeature:
    return IoFeature(app)
