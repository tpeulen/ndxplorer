"""The ranking panel: a ``view.json`` drawn by emtk, over a model that runs the ranking.

The Qt-free half of :mod:`ndxplorer.analysis.vizrank` says what a ranking *is*;
this is what the user works: the settings, *Start* / *Pause*, a status line and
the table of ranked views, clicking a row to apply it. None of it is widget
code. The layout is ``vizrank.view.json`` -- AutoForm's dialect, drawn by
``emtk.view_form`` with the table as a ``data_table`` section -- and the
behaviour is :class:`VizRankModel`, the object that spec reads and writes.
:class:`VizRankWindow` only *hosts* the emtk surface in a Qt window, as ChiSurf's
emtk tools do.

What :class:`VizRankModel` keeps from Orange3's ``VizRankDialog``
(``Orange/widgets/visualize/utils/vizrank.py``, GPL-3.0): the run states and
what each allows, pausing when the window closes and resuming when it reopens
(but not when the user paused), the paused percentage, selecting the best row
when a ranking finishes, a settings change that pauses the run and offers a
restart, and selecting the row of a view the user set by hand without
re-applying it. The worker runs on :func:`chisurf.gui.task.run_in_background`,
ChiSurf's adoption of Orange's ``ConcurrentMixin``.
"""

from __future__ import annotations

import json
import logging
import pathlib
from typing import Any, Callable, Optional

from ..analysis.vizrank import Batch, Ranker, RunState, ScoreList, run_vizrank

logger = logging.getLogger(__name__)

__all__ = ["VIEW_SPEC", "VizRankModel", "VizRankWindow", "load_spec"]

#: The panel's layout.
VIEW_SPEC = pathlib.Path(__file__).with_name("vizrank.view.json")


def load_spec() -> dict:
    """The parsed ``vizrank.view.json``."""
    return json.loads(VIEW_SPEC.read_text(encoding="utf-8"))


class _Run:
    """One ranking: its ranker, the shared state iterator, and its generation."""

    def __init__(self, ranker: Ranker, generation: int, settings: Any):
        self.ranker = ranker
        self.generation = generation
        self.settings = settings
        self.iterator = None
        self.total = 0


class _Progress:
    """The progress handle :class:`~chisurf.gui.progress.ChiSurfProgress` drives.

    The panel is its own progress host (``begin_task``), so a run reports in the
    status line instead of in a modal dialog over the window it keeps usable.
    """

    def __init__(self, model: "VizRankModel", message: str, maximum: int, cancel):
        self.model = model
        self._cancel = cancel
        self._value = 0
        self._maximum = int(maximum)
        self.model.progress_text = message

    def setLabelText(self, text: str) -> None:  # noqa: N802 - Qt-shaped handle
        self.model.progress_text = str(text)

    def setRange(self, minimum: int, maximum: int) -> None:  # noqa: N802
        self._maximum = int(maximum)

    def setValue(self, value: int) -> None:  # noqa: N802
        self._value = int(value)

    def value(self) -> int:
        return self._value

    def maximum(self) -> int:
        return self._maximum

    def update_progress(self, value: int, text: Optional[str] = None) -> None:
        self.setValue(value)
        if text is not None:
            self.setLabelText(text)

    def wasCanceled(self) -> bool:  # noqa: N802
        return False

    def cancel(self) -> None:
        if callable(self._cancel):
            self._cancel()

    def finish(self, *args, **kwargs) -> None:
        self.close()

    def close(self) -> None:
        self.model.progress_text = ""


class VizRankModel:
    """What ``vizrank.view.json`` binds to: settings, actions, rows, status.

    Subclasses implement :meth:`make_ranker` and, when they have settings,
    :meth:`current_settings`, and call :meth:`settings_changed` when one moves.

    Parameters
    ----------
    on_apply : callable, optional
        ``on_apply(payload)`` when the user selects a row.
    on_change : callable, optional
        Called after anything the panel shows changed, so a host can repaint.
    runner : callable, optional
        :func:`chisurf.gui.task.run_in_background` by default; injectable so
        the state machine is testable without threads.

    Attributes
    ----------
    rows : list of dict
        The ranked views, best first -- the ``data_table`` source. Each record
        holds ``score``, the name cells, ``key`` (its identity), ``note`` (what
        the score means, in numbers) and ``payload`` (what applying it sets).
    select_request : object
        A row key the host should mark as selected without applying it (set by
        :meth:`auto_select`), or ``None``.
    """

    title = "Score views"

    def __init__(self, on_apply: Optional[Callable[[Any], None]] = None,
                 on_change: Optional[Callable[[], None]] = None,
                 runner: Optional[Callable[..., Any]] = None):
        self.on_apply = on_apply
        self.on_change = on_change
        self._runner = runner
        self.run_state = RunState.Initialized
        self.rows: list = []
        self.scores = ScoreList()
        self.completed = 0
        self.failed = 0
        self.progress_text = ""
        self.error = ""
        self.select_request: Any = None
        self._generation = 0
        self._run: Optional[_Run] = None
        self._task = None
        self._start_when_idle = False
        self._auto_selecting = False

    # ---- hooks for subclasses ------------------------------------------------

    def make_ranker(self) -> Ranker:
        """Build the ranker for the current data and settings."""
        raise NotImplementedError

    def current_settings(self) -> Any:
        """What the ranking depends on; a change offers a restart."""
        return None

    def note(self) -> str:
        """A line about the data ranked, appended to the status (optional)."""
        return ""

    # ---- what the spec reads -------------------------------------------------

    def ranked_rows(self) -> list:
        """The ``data_table`` source."""
        return self.rows

    def ranked_columns(self) -> list:
        """The ``data_table`` columns: the score (as a bar) and the names."""
        header = ("Score",)
        correlation = False
        if self._run is not None:
            header = tuple(self._run.ranker.header)
            correlation = getattr(self._run.ranker, "method", "") in ("pearson", "spearman")
        span, fmt = ([-1.0, 1.0], "%+.3f") if correlation else ([0.0, 1.0], "%.3f")
        columns = [{"key": "score", "title": header[0], "display": "bar", "range": span,
                    "format": fmt, "width": 90,
                    "tooltip": "The score; the bar is its share of the range."}]
        for index, title in enumerate(header[1:]):
            columns.append({"key": f"name{index}", "title": title})
        return columns

    def status_text(self) -> str:
        """Progress, counts and what was sampled -- the status line."""
        if self.error:
            return self.error
        total = self._run.total if self._run is not None else 0
        if self.run_state == RunState.Initialized:
            text = "Press Start to rank every view."
        elif total:
            text = f"{self.completed}/{total} scored ({self.progress} %)"
        else:
            text = f"{self.completed} scored"
        if self.run_state == RunState.Paused:
            text += " · paused"
        elif self.run_state == RunState.Done:
            text += " · finished"
        if self.failed:
            text += f" · {self.failed} failed"
        return text

    def sample_text(self) -> str:
        """What was ranked (the second status line); empty before a run."""
        return self.note()

    def enabled(self, name: str) -> bool:
        """Which action is usable now (``emtk.view_form``'s hook)."""
        if name == "start":
            return self.run_state != RunState.Running and (
                self.run_state.can_run() or self.run_state == RunState.Initialized
                or self.restart_offered())
        if name == "pause":
            return self.run_state == RunState.Running
        return True

    def restart_offered(self) -> bool:
        """The settings differ from the ones the current ranking ran with."""
        return self._run is not None and self.current_settings() != self._run.settings

    @property
    def start_label(self) -> str:
        """What *Start* means right now (for a host that shows it)."""
        if self.restart_offered():
            return "Restart with new settings"
        return {RunState.Paused: "Continue", RunState.Hidden: "Continue",
                RunState.Done: "Finished"}.get(self.run_state, "Start")

    @property
    def progress(self) -> int:
        """Percent of the states scored."""
        total = self._run.total if self._run is not None else 0
        return int(round(self.completed * 100 / total)) if total else 0

    # ---- actions ------------------------------------------------------------------

    def start(self) -> None:
        """*Start* / *Continue* / *Restart with new settings*."""
        self.start_computation()

    def pause(self) -> None:
        """*Pause*."""
        self.pause_computation()

    def settings_changed(self, *_value) -> None:
        """A setting moved: a running ranking pauses, since its rows are about to mean something else."""
        if self.run_state == RunState.Running:
            self.pause_computation()
        self._changed()

    def apply_row(self, record) -> None:
        """The ``data_table``'s ``selected_call``: apply the row's view."""
        if record is None or self._auto_selecting:
            return
        if self.on_apply is not None:
            self.on_apply(record["payload"])

    def auto_select(self, wanted) -> None:
        """Mark the row showing *wanted* (set by hand in the plot), without applying it."""
        run = self._run
        self.select_request = None
        if run is None:
            return
        for record in self.rows:
            if run.ranker.matches(record["payload"], wanted):
                self.select_request = record["key"]
                break
        self._changed()

    # ---- the state machine -----------------------------------------------------------

    def _changed(self) -> None:
        if self.on_change is not None:
            try:
                self.on_change()
            except Exception:  # noqa: BLE001 - a repaint must not break a run
                logger.debug("vizrank: on_change failed", exc_info=True)

    def set_run_state(self, state: RunState) -> None:
        """Change the run state."""
        self.run_state = RunState(state)
        self._changed()

    def prepare_run(self) -> None:
        """Clear the rows and build a fresh ranker from the current settings.

        On the GUI thread: the ranker gathers its subsample from the table,
        which must not be read from a worker while the GUI may rewrite it.
        Scoring -- including ordering the columns -- happens in the worker.
        """
        if self._task is not None:
            self._task.cancel()
        self._generation += 1
        self.scores.clear()
        self.rows = []
        self.completed = 0
        self.failed = 0
        self.error = ""
        settings = self.current_settings()
        ranker = self.make_ranker()
        ranker.prepare()
        self._run = _Run(ranker, self._generation, settings)
        self.set_run_state(RunState.Ready)

    def start_computation(self) -> None:
        """Start, continue or restart, whichever the state calls for."""
        if self.restart_offered():
            self.run_state = RunState.Initialized
        if self.run_state == RunState.Initialized:
            try:
                self.prepare_run()
            except Exception as exc:  # noqa: BLE001 - say why, do not crash the host
                logger.debug("vizrank: prepare failed", exc_info=True)
                self.error = f"Cannot rank: {exc}"
                self._changed()
                return
        if not self.run_state.can_run():
            return
        self.set_run_state(RunState.Running)
        if self._task is not None and self._task.is_running:
            # The previous run is still scoring its last state. Its last batch
            # is valid and has to land, so wait rather than supersede it -- a
            # superseded task's partial results are disconnected.
            self._start_when_idle = True
            return
        self._launch()

    def _launch(self) -> None:
        runner = self._runner
        if runner is None:
            from chisurf.gui.task import run_in_background as runner
        run = self._run
        self._task = runner(
            self, "Scoring views…", self._work, args=(run,), maximum=run.total or 0,
            on_partial=self.on_partial_result, on_result=self.on_done, on_error=self.on_error,
            on_done=self._on_task_finished, owner=self, cancellable=True,
        )

    @staticmethod
    def _work(run: _Run, task) -> Batch:
        """The worker: order the states once, then score them."""
        if run.iterator is None:
            task.set_text("ordering parameters")
            run.total = run.ranker.state_count()
            run.iterator = run.ranker.iterate_states()
            task.set_partial(("prepared", run.generation, run.total))
        task.set_text("scoring")
        return run_vizrank(run.ranker.compute_score, run.iterator, run.generation, 0, task,
                           progress=False)

    def pause_computation(self, new_state: RunState = RunState.Paused) -> None:
        """Stop scoring; *Continue* resumes from here."""
        if self.run_state != RunState.Running:
            return
        self._start_when_idle = False
        self.set_run_state(new_state)
        if self._task is not None:
            self._task.cancel()

    def dialog_reopened(self) -> None:
        """Resume a ranking the window's closing stopped; a paused one stays paused."""
        if self.run_state != RunState.Paused:
            self.start_computation()

    def shutdown(self) -> None:
        """Stop for good (the data went away)."""
        self._start_when_idle = False
        if self._task is not None:
            self._task.cancel()

    # ---- the progress host ---------------------------------------------------------

    def begin_task(self, message: str = "", maximum: int = 0, cancel=None) -> _Progress:
        """Report a run in the status line (the ChiSurf progress-host contract)."""
        return _Progress(self, message, maximum, cancel)

    # ---- results ---------------------------------------------------------------------

    def on_partial_result(self, value) -> None:
        """Insert a batch of scored states where they belong."""
        run = self._run
        if run is None:
            return
        if isinstance(value, tuple) and value and value[0] == "prepared":
            _, generation, total = value
            if generation == run.generation:
                run.total = int(total)
                self._changed()
            return
        if not isinstance(value, Batch) or value.generation != run.generation:
            return  # a batch from a ranking that has since been replaced
        ranker = run.ranker
        # In place: a table renderer notices the list growing and re-reads it
        # without rebinding, so its scroll position and selection stay. A new
        # ranking starts a new list (prepare_run), which it rebinds to.
        rows = self.rows
        for state, score in value.items:
            self.completed += 1
            if score is None:
                continue
            position = self.scores.insert(score)
            rows.insert(position, self._record(ranker.row_for_state(score, state)))
        self.failed += value.failed
        self._changed()

    @staticmethod
    def _record(row) -> dict:
        payload = row.payload
        key = "|".join(f"{k}={payload[k]}" for k in sorted(payload)) \
            if isinstance(payload, dict) else repr(payload)
        record = {
            "score": float(row.value if row.value is not None else row.sort_value),
            "key": key,
            "note": row.tooltip,
            "payload": payload,
        }
        for index, cell in enumerate(row.cells[1:]):
            record[f"name{index}"] = cell
        return record

    def on_done(self, _result) -> None:
        """Every state is scored: finish, and ask for the best row to be selected."""
        if self.run_state != RunState.Running or self._start_when_idle:
            return
        if self._run is not None and self.completed < self._run.total:
            return  # stopped early without being cancelled
        self.set_run_state(RunState.Done)
        if self.rows and self.select_request is None:
            self.select_request = self.rows[0]["key"]
            self.apply_row(self.rows[0])

    def on_error(self, exc: BaseException) -> None:
        """The ranking itself failed (not one state): say so and stop."""
        logger.error("vizrank failed: %s", exc, exc_info=exc)
        self.error = f"Ranking failed: {exc}"
        self.set_run_state(RunState.Paused)

    def _on_task_finished(self) -> None:
        self._task = None
        if self._start_when_idle:
            self._start_when_idle = False
            try:
                from qtpy import QtCore

                # Not from inside the completion callback: see run_in_background.
                QtCore.QTimer.singleShot(0, self._launch_if_running)
            except Exception:  # pragma: no cover - no Qt: run inline
                self._launch_if_running()
        self._changed()

    def _launch_if_running(self) -> None:
        if self.run_state == RunState.Running and self._task is None:
            self._launch()


def _window_base():
    from chisurf.gui.widgets.tools.help_guide import HelpGuideMixin
    from qtpy import QtWidgets

    return HelpGuideMixin, QtWidgets.QMainWindow


class _Surface:
    """Adapts ``draw_form`` over the model to ``ControlHost``'s control contract."""

    BACKGROUND = (30, 32, 38, 255)

    def __init__(self, spec: dict, model: VizRankModel):
        import emtk
        from emtk.view_form import FormState

        self.spec = spec
        self.model = model
        self.io = emtk.IO()
        self.storage: dict = {}
        self.state = FormState()
        self.popup = None
        self.box = (0.0, 0.0, 1.0, 1.0)

    def table(self):
        """The ranked-views table binding, once drawn."""
        return self.state.tables.get("ranked_rows")

    def draw(self, painter, x: float, y: float, w: float, h: float) -> None:
        import emtk
        from emtk.view_form import draw_form

        self.box = (x, y, w, h)
        painter.fill_rect(x, y, w, h, self.BACKGROUND)
        with emtk.frame(painter, (x, y, w, h), io=self.io, storage=self.storage):
            emtk.begin("##vizrank", (x + 6.0, y + 6.0, w - 12.0, h - 12.0),
                       emtk.WindowFlags.NO_TITLE_BAR)
            draw_form(self.spec, self.model, self.state, titles=False)
            emtk.end()
        binding = self.table()
        request = self.model.select_request
        if binding is not None and request is not None:
            binding.refresh()
            if binding.control.select_key(request):
                self.model.select_request = None
        self.io.mouse_clicked[0] = False
        self.io.mouse_released[0] = False
        self.io.mouse_double_clicked[0] = False
        self.io.mouse_wheel = 0.0
        self.io.key, self.io.text = 0, ""
        self._open_dropdown()
        if self.popup is not None:
            self.popup[0].draw(painter, x, y, w, h)

    def _open_dropdown(self) -> None:
        from emtk.widgets.menus import MenuItem, Popup

        request, self.state.dropdown_request = self.state.dropdown_request, None
        if request is None:
            return
        name, (rx, ry, _rw, rh), labels, current = request
        items = [MenuItem(text, checked=(index == current)) for index, text in enumerate(labels)]
        popup = Popup(items)
        popup.open_at(rx, ry + rh)
        self.popup = (popup, items, name)

    # -- input ----------------------------------------------------------------------
    def hover(self, px: float, py: float, *_box) -> None:
        self.io.mouse_pos = (px, py)

    def drag(self, px: float, py: float, *_box) -> None:
        self.io.mouse_pos = (px, py)

    def press(self, px: float, py: float, *extra, **_kw) -> None:
        if self.popup is not None:
            popup, items, name = self.popup
            x, y, w, h = self.box
            result = popup.press(px, py, x, y, w, h)
            if result.item is not None:
                self.state.dropdown_result[name] = items.index(result.item)
            if not popup.open:
                self.popup = None
            return
        clicks = extra[5] if len(extra) > 5 else 1
        io = self.io
        io.mouse_pos = io.mouse_clicked_pos[0] = (px, py)
        io.mouse_clicked[0] = io.mouse_down[0] = True
        io.mouse_double_clicked[0] = clicks >= 2

    def release(self, *_args, **_kw) -> None:
        if self.io.mouse_down[0]:
            self.io.mouse_down[0] = False
            self.io.mouse_released[0] = True

    def scroll(self, rows: int) -> None:
        self.io.mouse_wheel = -1.0 if rows > 0 else 1.0

    def key(self, key: int, text: str = "", modifiers: int = 0) -> bool:
        self.io.key = int(key)
        self.io.text = "".join(c for c in (text or "") if c >= " " and c != "\x7f")
        return True


#: Tour anchors: object name -> the ``FormState.rects`` name of an emtk control.
ANCHORS = {
    "vizrank_method": "method",
    "vizrank_classes": "classes",
    "vizrank_sample": "sample_rows",
    "vizrank_start": "start",
    "vizrank_pause": "pause",
    "vizrank_table": "ranked_rows",
}


def VizRankWindow(model: VizRankModel, parent=None, spec: Optional[dict] = None):  # noqa: N802
    """A Qt window hosting the emtk panel for *model* (built on first call)."""
    HelpGuideMixin, QMainWindow = _window_base()
    global _WINDOW_CLASS
    if _WINDOW_CLASS is None:
        from qtpy import QtCore, QtWidgets

        class _Anchor(QtWidgets.QWidget):
            """An invisible stand-in for one emtk control, for the guided tour."""

            clicked = QtCore.Signal()

            def __init__(self, name: str, parent) -> None:
                super().__init__(parent)
                self.setObjectName(name)
                self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
                self.setAttribute(QtCore.Qt.WA_NoSystemBackground, True)
                self.resize(1, 1)

        class _VizRankWindow(HelpGuideMixin, QMainWindow):
            """The emtk ranking panel as a tool window beside ndX.

            Qt does two things here: host the surface, and give the guided tour
            something to point at (one invisible anchor per named control, kept
            over the control's last drawn rectangle).
            """

            help_title = "Find informative projections"

            def __init__(self, model: VizRankModel, parent=None, spec=None) -> None:
                super().__init__(parent)
                from emtk.qt_host import ControlHost

                self.model = model
                self.setWindowTitle(model.title)
                self.setWindowFlag(QtCore.Qt.Tool, True)
                self.surface = _Surface(spec or load_spec(), model)
                self.host = ControlHost(self.surface, background=_Surface.BACKGROUND[:3])
                self.host.setObjectName("vizrank_surface")
                self.host.setMinimumSize(460, 520)
                self.setCentralWidget(self.host)
                toolbar = QtWidgets.QToolBar("Ranking", self)
                toolbar.setMovable(False)
                self.addToolBar(toolbar)
                self.ensure_help_toolbar(toolbar=toolbar, help_resource="vizrank_help.md",
                                         guide_resource="vizrank_guide.json")
                self.anchors = {name: _Anchor(name, self.host) for name in ANCHORS}
                model.on_change = self.host.update
                self.surface.state.on_used = self._used
                self.timer = QtCore.QTimer(self)
                self.timer.timeout.connect(self._tick)
                self.timer.start(60)
                self.resize(520, 640)

            def _used(self, name: str) -> None:
                for anchor, key in ANCHORS.items():
                    if key == name:
                        self.anchors[anchor].clicked.emit()

            def _tick(self) -> None:
                self.host.update()
                for anchor, key in ANCHORS.items():
                    rect = self.surface.state.rects.get(key)
                    if rect:
                        x, y, w, h = rect
                        self.anchors[anchor].setGeometry(int(x), int(y), max(int(w), 1),
                                                         max(int(h), 1))

            def hideEvent(self, event) -> None:  # noqa: N802 - Qt's spelling
                self.model.pause_computation(RunState.Hidden)
                super().hideEvent(event)

            def closeEvent(self, event) -> None:  # noqa: N802
                self.timer.stop()
                super().closeEvent(event)

        _WINDOW_CLASS = _VizRankWindow
    return _WINDOW_CLASS(model, parent, spec)


_WINDOW_CLASS = None
