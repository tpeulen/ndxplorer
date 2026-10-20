"""The ranking panel's model: settings, Start/Pause, progress and the ranked rows.

:class:`VizRankModel` is what ``vizrank.view.json`` binds to. It owns one
*run* at a time -- a prepared ranker with the settings it was prepared with --
and drives it through a runner (a worker thread, time slices of the frame
loop, or, without one, synchronously inline). Rows arrive in batches on the
GUI side and are inserted at their sorted place there, so the table fills best
first while scoring goes on. Ranking projections by a quality score and
listing the best first follows VizRank (Leban et al. 2006,
doi:10.1007/s10618-005-0031-5).

Subclasses say what is ranked: :meth:`VizRankModel.make_ranker`,
:meth:`VizRankModel.current_settings` and :meth:`VizRankModel.note`
(:class:`~ndxplorer.analysis.projection_rank_model.ProjectionRankModel`).
"""

from __future__ import annotations

import json
import logging
import pathlib
from typing import Any, Callable, List, Optional

from ..i18n import mark, tr
from .vizrank import RunState, ScoreBatch, StateTotal, insertion_index, score_states

logger = logging.getLogger(__name__)

__all__ = ["VIEW_SPEC", "load_spec", "VizRankModel"]

#: The panel's view spec, beside this module.
VIEW_SPEC = pathlib.Path(__file__).resolve().with_name("vizrank.view.json")


def load_spec() -> dict:
    """The parsed panel spec (``vizrank.view.json``)."""
    with open(VIEW_SPEC, encoding="utf-8") as handle:
        return json.load(handle)


def payload_key(payload: dict) -> str:
    """A row's identity: its payload's sorted ``k=v`` pairs joined by ``|``."""
    return "|".join(f"{k}={payload[k]}" for k in sorted(payload))


class _Run:
    """One prepared ranking: the ranker, the settings it was made for and its progress.

    ``states`` is the enumeration shared by every call of the work function,
    so a paused or time-sliced run continues where it stopped.
    """

    def __init__(self, ranker, settings, generation: int) -> None:
        self.ranker = ranker
        self.settings = settings
        self.generation = generation
        self.total = 0
        self.states = None
        self.keys: List[Any] = []


class _Launch:
    """Book-keeping of one runner call: whether it has reported done."""

    def __init__(self) -> None:
        self.task = None
        self.done = False


class _InlineHandle:
    """The handle of the synchronous default runner."""

    def __init__(self, on_partial) -> None:
        self._on_partial = on_partial
        self.cancelled = False
        self.is_running = False

    @property
    def is_cancelled(self) -> bool:
        return self.cancelled

    def set_partial(self, value) -> None:
        if self._on_partial is not None:
            self._on_partial(value)

    def set_progress(self, _value) -> None:
        pass

    def set_text(self, _text) -> None:
        pass

    def cancel(self) -> None:
        self.cancelled = True


def _inline_runner(_owner, _text, func, *, args=(), on_partial=None, on_result=None,
                   on_error=None, on_done=None, **_ignored):
    """Run *func* here and now, with the callbacks in the runner's order."""
    handle = _InlineHandle(on_partial)
    try:
        result = func(*args, handle)
    except Exception as exc:  # noqa: BLE001 - reported through on_error
        if on_error is not None:
            on_error(exc)
    else:
        if on_result is not None and not handle.cancelled:
            on_result(result)
    if on_done is not None:
        on_done()
    return handle


class _Progress:
    """What :meth:`VizRankModel.begin_task` hands a runner that reports progress."""

    def __init__(self, model: "VizRankModel", message: str) -> None:
        self._model = model
        self.set_text(message)

    def set_text(self, text: str) -> None:
        self._model.progress_text = str(text or "")
        self._model._changed()

    def set_value(self, _value) -> None:
        pass

    def finish(self) -> None:
        self.set_text("")

    close = finish


class VizRankModel:
    """Model of a ranking panel.

    Parameters
    ----------
    on_apply : callable, optional
        ``on_apply(payload)`` shows the view a row describes; called when the
        user picks a row and for the best row when a ranking finishes.
    on_change : callable, optional
        Told after anything visible changed. Its exceptions are logged, never
        raised into a run.
    runner : callable, optional
        Starts the work (worker thread or time slices). ``None`` runs it
        synchronously inline.
    defer : callable, optional
        ``defer(fn)`` runs *fn* soon but not now (a continued run's launch);
        ``None`` calls it at once.
    """

    title = mark("Score views")

    def __init__(self, on_apply: Optional[Callable[[dict], None]] = None,
                 on_change: Optional[Callable[[], None]] = None,
                 runner: Optional[Callable] = None,
                 defer: Optional[Callable[[Callable[[], None]], None]] = None) -> None:
        self._on_apply = on_apply
        self._on_change = on_change
        self._runner = runner if runner is not None else _inline_runner
        self._defer = defer if defer is not None else (lambda fn: fn())
        self.run_state = RunState.Initialized
        self.rows: List[dict] = []
        self.completed = 0
        self.failed = 0
        self.progress_text = ""
        self.error = ""
        self.select_request: Optional[str] = None
        self._run: Optional[_Run] = None
        self._generation = 0
        self._launch: Optional[_Launch] = None
        self._launch_when_idle = False
        self._auto_selecting = False
        self._closed = False

    # ---- hooks for subclasses ----------------------------------------------------------
    def make_ranker(self):
        """A new ranker for the current settings (may raise; the message is shown)."""
        raise NotImplementedError

    def current_settings(self):
        """What the ranking depends on; a change offers a restart."""
        return None

    def note(self) -> str:
        """A line about the sample (the panel's second info line)."""
        return ""

    # ---- notifications -----------------------------------------------------------------
    def _changed(self) -> None:
        if self._on_change is None:
            return
        try:
            self._on_change()
        except Exception:  # noqa: BLE001 - a listener must not break a run
            logger.debug("ranking on_change failed", exc_info=True)

    def set_run_state(self, state: RunState) -> None:
        """Move to *state* and tell the listener."""
        self.run_state = RunState(state)
        self._changed()

    # ---- what the spec binds -----------------------------------------------------------
    def ranked_rows(self) -> list:
        """The ranked records, best first (the table's source)."""
        return self.rows

    def ranked_columns(self) -> list:
        """The table's columns: the score with its bar, then one per name cell."""
        if self._run is not None:
            header = tuple(self._run.ranker.header)
            lo, hi = self._run.ranker.score_span
            names = int(getattr(self._run.ranker, "dimension", len(header) - 1))
        else:
            header, (lo, hi), names = ("Score",), (0.0, 1.0), 0
        columns = [{
            "key": "score",
            "title": tr(header[0]),
            "display": "bar",
            "range": [lo, hi],
            "format": "%+.3f" if lo < 0 else "%.3f",
            "width": 90,
            "tooltip": tr("The score; the bar is its share of the range."),
        }]
        axis_tip = tr("The {axis} parameter of the view; hover a shortened name for the whole of it.")
        for index, title in enumerate(header[1:]):
            # The name cells explain themselves as axes; an extra cell (the
            # island count) is explained by the row's tooltip.
            tip = axis_tip.format(axis=tr(title)) if index < names else ""
            columns.append({"key": f"name{index}", "title": tr(title), "tooltip": tip})
        return columns

    def status_text(self) -> str:
        """Progress in words: scored states, paused/finished, failures."""
        if self.error:
            return self.error
        if self.run_state == RunState.Initialized:
            return tr("Press Start to rank every view.")
        total = self._run.total if self._run is not None else 0
        if total:
            text = tr("{done}/{total} scored ({percent} %)").format(
                done=self.completed, total=total, percent=self.progress)
        else:
            text = tr("{done} scored").format(done=self.completed)
        if self.run_state == RunState.Paused:
            text += " · " + tr("paused")
        elif self.run_state == RunState.Done:
            text += " · " + tr("finished")
        if self.failed:
            text += " · " + tr("{n} failed").format(n=self.failed)
        return text

    def sample_text(self) -> str:
        return self.note()

    def enabled(self, name: str) -> bool:
        if name == "start":
            return self.run_state != RunState.Running and (
                self.run_state.can_run() or self.run_state == RunState.Initialized
                or self.restart_offered())
        if name == "pause":
            return self.run_state == RunState.Running
        return True

    def restart_offered(self) -> bool:
        """A ranking exists and the settings moved away from the ones it was made for."""
        if self._run is None:
            return False
        try:
            return self.current_settings() != self._run.settings
        except Exception:  # noqa: BLE001 - a broken context cannot offer anything
            logger.debug("current_settings failed", exc_info=True)
            return False

    @property
    def start_label(self) -> str:
        if self.restart_offered():
            return tr("Restart with new settings")
        if self.run_state in (RunState.Paused, RunState.Hidden):
            return tr("Continue")
        if self.run_state == RunState.Done:
            return tr("Finished")
        return tr("Start")

    @property
    def progress(self) -> int:
        total = self._run.total if self._run is not None else 0
        return int(round(100.0 * self.completed / total)) if total else 0

    # ---- actions -------------------------------------------------------------------------
    def start(self) -> None:
        """Start, continue, or restart with the current settings."""
        if self._closed:
            return
        if self.restart_offered():
            self.run_state = RunState.Initialized
        if self.run_state == RunState.Initialized:
            if not self._prepare():
                return
        if self.run_state.can_run():
            self.run_state = RunState.Running
            if self._busy():
                # The previous run has not let go yet (a fast Pause -> Continue):
                # it must finish delivering before this one takes the states.
                self._launch_when_idle = True
            else:
                self._start_task()
        self._changed()

    def pause(self) -> None:
        self.pause_computation(RunState.Paused)

    def settings_changed(self, *_args) -> None:
        if self.run_state == RunState.Running:
            self.pause_computation(RunState.Paused)
        self._changed()

    def apply_row(self, record) -> None:
        """A row was picked in the table: show its view."""
        if record is None or self._auto_selecting:
            return
        if self._on_apply is not None:
            self._on_apply(record["payload"])

    def auto_select(self, wanted: dict) -> None:
        """Mark the row that shows *wanted* (a view picked by hand) without applying it."""
        self._auto_selecting = True
        try:
            ranker = self._run.ranker if self._run is not None else None
            self.select_request = None
            if ranker is not None:
                for record in self.rows:
                    if ranker.matches(record["payload"], wanted):
                        self.select_request = record["key"]
                        break
        finally:
            self._auto_selecting = False
        self._changed()

    def pause_computation(self, new_state: RunState = RunState.Paused) -> None:
        """Stop a running ranking; *new_state* ``Hidden`` when its window closed."""
        if self.run_state != RunState.Running:
            return
        self._launch_when_idle = False
        self.run_state = RunState(new_state)
        self._cancel_task()
        self._changed()

    def dialog_reopened(self) -> None:
        """The window opened again: resume unless the user paused."""
        if self.run_state != RunState.Paused:
            self.start()

    def shutdown(self) -> None:
        """Stop for good: cancel the task and any pending launch."""
        self._closed = True
        self._launch_when_idle = False
        self._cancel_task()

    def begin_task(self, message: str = "", maximum: int = 0, cancel=None) -> _Progress:
        """A progress host for runners that look for one; its text is :attr:`progress_text`."""
        return _Progress(self, message)

    # ---- running -------------------------------------------------------------------------
    def _busy(self) -> bool:
        launch = self._launch
        return launch is not None and not launch.done and launch.task is not None \
            and bool(getattr(launch.task, "is_running", False))

    def _cancel_task(self) -> None:
        launch = self._launch
        if launch is not None and launch.task is not None and not launch.done:
            try:
                launch.task.cancel()
            except Exception:  # noqa: BLE001
                logger.debug("cancelling the ranking task failed", exc_info=True)

    def _prepare(self) -> bool:
        """Make a fresh run for the current settings (on this, the GUI, thread)."""
        self._cancel_task()
        self._launch_when_idle = False
        self._generation += 1
        self.rows = []
        self.completed = 0
        self.failed = 0
        self.error = ""
        self.select_request = None
        self._run = None
        try:
            settings = self.current_settings()
            ranker = self.make_ranker()
            ranker.prepare()
        except Exception as exc:  # noqa: BLE001 - shown in the panel
            logger.debug("preparing the ranking failed", exc_info=True)
            self.error = tr("Cannot rank: {error}").format(error=exc)
            self._changed()
            return False
        self._run = _Run(ranker, settings, self._generation)
        self.run_state = RunState.Ready
        return True

    def _start_task(self) -> None:
        run = self._run
        if run is None:
            return
        launch = _Launch()
        self._launch = launch
        generation = run.generation

        def on_partial(value) -> None:
            self._receive(generation, value)

        def on_result(_result) -> None:
            self._finished(generation)

        def on_error(exc) -> None:
            self._failed(generation, exc)

        def on_done() -> None:
            launch.done = True
            self._task_done(launch)

        task = self._runner(self, tr("Scoring views…"), self._work, args=(run,),
                            maximum=0, on_partial=on_partial, on_result=on_result,
                            on_error=on_error, on_done=on_done, owner=self, cancellable=True)
        launch.task = task

    def _launch_if_running(self) -> None:
        if self._closed or self.run_state != RunState.Running or self._busy():
            return
        self._start_task()

    @staticmethod
    def _work(run: _Run, handle) -> int:
        """The runner's function: choose and order the columns once, then score.

        Called again after a pause or at each time slice; it continues the
        run's shared enumeration.
        """
        if run.states is None:
            handle.set_text(tr("ordering parameters"))
            total = int(run.ranker.state_count())
            run.states = iter(run.ranker.iterate_states())
            handle.set_partial(StateTotal(run.generation, total))
        handle.set_text(tr("Scoring views…"))
        return score_states(run.states, run.ranker.compute_score, handle, run.generation)

    def _receive(self, generation: int, value) -> None:
        run = self._run
        if run is None or generation != run.generation:
            return
        if isinstance(value, StateTotal):
            if value.generation == run.generation:
                run.total = value.total
                self._changed()
            return
        if not isinstance(value, ScoreBatch) or value.generation != run.generation:
            return
        for state, score in value.items:
            self.completed += 1
            if score is None:
                continue
            row = run.ranker.row_for_state(score, state)
            position = insertion_index(run.keys, score)
            run.keys.insert(position, score)
            self.rows.insert(position, self._record(row))
        self.failed += value.failed
        self._changed()

    @staticmethod
    def _record(row) -> dict:
        record = {
            "score": row.value if row.value is not None else row.sort_value,
            "key": payload_key(row.payload),
            "note": row.tooltip,
            "payload": dict(row.payload),
        }
        for index, cell in enumerate(row.cells[1:]):
            record[f"name{index}"] = cell
        return record

    def _finished(self, generation: int) -> None:
        run = self._run
        if run is None or generation != run.generation:
            return
        if self.run_state != RunState.Running or self._launch_when_idle \
                or self.completed < run.total:
            return
        self.run_state = RunState.Done
        if self.rows and self.select_request is None:
            best = self.rows[0]
            self.select_request = best["key"]
            if self._on_apply is not None:
                self._on_apply(best["payload"])
        self._changed()

    def _failed(self, generation: int, exc) -> None:
        logger.warning("ranking failed: %s", exc)
        if self._run is None or generation != self._run.generation:
            return
        self.error = tr("Ranking failed: {error}").format(error=exc)
        self.run_state = RunState.Paused
        self._changed()

    def _task_done(self, launch: _Launch) -> None:
        if self._launch is launch:
            self._launch = None
        if self._launch_when_idle:
            self._launch_when_idle = False
            self._defer(self._launch_if_running)
        self._changed()
