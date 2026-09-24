"""The ranking panel's model: what ``vizrank.view.json`` reads, writes and calls.

The Qt-free half of :mod:`ndxplorer.analysis.vizrank` says what a ranking *is*;
this is what the user works: the settings, *Start* / *Pause*, a status line and
the table of ranked views, clicking a row to apply it. None of it is widget
code. The layout is ``vizrank.view.json`` -- AutoForm's dialect, drawn by
``emtk.view_form`` with the table as a ``data_table`` section -- and the
behaviour is :class:`VizRankModel`, the object that spec reads and writes. Both
ndX GUIs host it: the Qt window through :mod:`ndxplorer.ui.vizrank_panel`, the
emtk app natively (:mod:`ndxplorer.app.features.playback_export`).

What :class:`VizRankModel` keeps from Orange3's ``VizRankDialog``
(``Orange/widgets/visualize/utils/vizrank.py``, GPL-3.0): the run states and
what each allows, pausing when the window closes and resuming when it reopens
(but not when the user paused), the paused percentage, selecting the best row
when a ranking finishes, a settings change that pauses the run and offers a
restart, and selecting the row of a view the user set by hand without
re-applying it. The worker runs on whatever *runner* the host injects: ChiSurf's
:func:`chisurf.gui.task.run_in_background` (Orange's ``ConcurrentMixin``) in the
Qt window, time slices of the frame loop in the emtk app.
"""

from __future__ import annotations

import json
import logging
import pathlib
from typing import Any, Callable, Optional

from .vizrank import Batch, Ranker, RunState, ScoreList, run_vizrank

logger = logging.getLogger(__name__)

__all__ = ["VIEW_SPEC", "VizRankModel", "load_spec"]

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
        the state machine is testable without threads, and so the emtk app can
        score in time slices of its frame loop (no threads in a browser).
    defer : callable, optional
        ``defer(fn)`` runs *fn* soon, but not now: how a run continued while
        the previous one was finishing is launched once that one has let go.
        The Qt window passes a zero-timer, the emtk app its next frame; without
        one it runs inline.

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
                 runner: Optional[Callable[..., Any]] = None,
                 defer: Optional[Callable[[Callable[[], None]], None]] = None):
        self.on_apply = on_apply
        self.on_change = on_change
        self._runner = runner
        self._defer = defer
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
        span = (0.0, 1.0)
        if self._run is not None:
            header = tuple(self._run.ranker.header)
            span = tuple(getattr(self._run.ranker, "score_span", span))
        fmt = "%+.3f" if span[0] < 0 else "%.3f"
        columns = [{"key": "score", "title": header[0], "display": "bar", "range": list(span),
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
            # Not from inside the completion callback: see run_in_background.
            if self._defer is not None:
                self._defer(self._launch_if_running)
            else:
                self._launch_if_running()
        self._changed()

    def _launch_if_running(self) -> None:
        if self.run_state == RunState.Running and self._task is None:
            self._launch()
