"""Playback, *Find informative projections…* and *Export…*: a feature of the emtk app.

Three parts of ndXplorer that watch or leave the current view rather than
change the data:

**Playback** -- the *Playback* panel of the plot controls (the core spec's
``{"type": "custom", "key": "playback"}``). The controls are
``plotting/playback.view.json``, the same spec the Qt window renders, bound to
the same :class:`~ndxplorer.plotting.playback_view_model.PlaybackViewModel`
over a :class:`~ndxplorer.core.playback.PlaybackController`. The slice reaches
the histograms as the ``slice_mask`` term of the mask (:meth:`mask_terms`).
Timing is the frame loop's: :meth:`draw_windows` calls ``tick`` every frame and
:meth:`animating` keeps the host drawing while it plays -- no timer, so it plays
in a browser too.

**Find informative projections** (View menu, pairs and z) -- the ranking
panel, ``analysis/vizrank.view.json`` over
:class:`~ndxplorer.analysis.projection_rank_model.ProjectionRankModel`, drawn
natively in a tool window. The scoring runs through :mod:`emtk.tasks` in short
slices (a thread on a desktop, steps between frames in a browser), streaming
rows into the table as the Qt window's worker does.

**Export…** -- the publication figure: a small form
(``playback_export/publication_export.view.json``), the figure composed by
:mod:`ndxplorer.export.publication_figure` (Matplotlib, Agg -- there is a
Pyodide build) and its bytes handed to ``app.io_service.save_bytes``: a path on
a desktop, a download in a browser.
"""

from __future__ import annotations

import json
import logging
import pathlib
import re
import threading
import time
from typing import Any, Callable, Dict, List, Optional

from . import Feature

__all__ = ["PlaybackExportFeature", "PublicationExportModel", "frame_runner", "create"]

logger = logging.getLogger(__name__)

SPECS = pathlib.Path(__file__).with_name("playback_export")
_UI = pathlib.Path(__file__).resolve().parents[2] / "ui"
#: The ranking panel's long help and guided tour, shared with the Qt window
#: (read as files: importing ``ndxplorer.ui`` builds Qt dialogs).
VIZRANK_HELP = _UI / "vizrank_help.md"
VIZRANK_GUIDE = _UI / "vizrank_guide.json"

#: Tour anchors: the guide's target name -> the ``FormState.rects`` name.
ANCHORS = {
    "vizrank_method": "method",
    "vizrank_classes": "classes",
    "vizrank_sample": "sample_rows",
    "vizrank_start": "start",
    "vizrank_pause": "pause",
    "vizrank_table": "ranked_rows",
}


def load_spec(name: str) -> dict:
    """One of this feature's view specs."""
    with open(SPECS / f"{name}.view.json", encoding="utf-8") as handle:
        return json.load(handle)


# --------------------------------------------------------------------------- #
# Running a ranking beside the frame
# --------------------------------------------------------------------------- #
class _Handle:
    """What the ranking's worker reports through (the ``run_in_background``
    handle): cancellation, partial batches, progress, a status text.

    ``is_cancelled`` also turns true when the current *slice* is spent, which
    makes :func:`~ndxplorer.analysis.vizrank.run_vizrank` hand back its batch
    and return; the next slice continues from the shared state iterator.
    """

    def __init__(self, task, budget: float) -> None:
        self.task = task
        self.budget = budget
        self.deadline = 0.0
        self.sliced = False
        self.cancelled = False
        self._lock = threading.Lock()
        self._partials: List[Any] = []

    @property
    def is_cancelled(self) -> bool:
        if self.cancelled or self.task.cancelled:
            return True
        if time.monotonic() >= self.deadline:
            self.sliced = True
            return True
        return False

    def set_partial(self, value) -> None:
        with self._lock:
            self._partials.append(value)

    def take_partials(self) -> list:
        with self._lock:
            out, self._partials = self._partials, []
        return out

    def set_progress(self, *_args) -> None:
        pass

    def set_text(self, text: str) -> None:
        self.task.report(None, str(text))


class FrameTask:
    """One ranking run on :mod:`emtk.tasks`, delivered on the frame's thread.

    :meth:`pump` (once per frame) advances a cooperative task and hands the
    batches, the result and the end of the run to the model's callbacks, in
    that order -- the contract ``run_in_background`` keeps in the Qt window.
    """

    def __init__(self, func, args, on_partial, on_result, on_error, on_done,
                 mode: Optional[str] = None, budget: float = 0.01) -> None:
        import emtk.tasks

        self.on_partial, self.on_result = on_partial, on_result
        self.on_error, self.on_done = on_error, on_done
        self._finished = False
        self.handle = None

        def work(task):
            handle = self.handle
            while True:
                handle.deadline = time.monotonic() + handle.budget
                handle.sliced = False
                result = func(*args, handle)
                if handle.cancelled or task.cancelled or not handle.sliced:
                    return result
                yield None

        self.task = emtk.tasks.Task(work, mode=mode, name="vizrank")
        self.handle = _Handle(self.task, budget)
        self.task.start()

    @property
    def is_running(self) -> bool:
        return not self._finished

    def cancel(self) -> None:
        self.handle.cancelled = True
        self.task.cancel()

    def pump(self) -> bool:
        """Deliver what arrived; ``True`` once the run is over."""
        if self._finished:
            return True
        self.task.poll()
        for value in self.handle.take_partials():
            if self.on_partial is not None:
                self.on_partial(value)
        if not self.task.done:
            return False
        for value in self.handle.take_partials():
            if self.on_partial is not None:
                self.on_partial(value)
        self._finished = True
        if self.task.state == "done" and not self.handle.cancelled:
            if self.on_result is not None:
                self.on_result(self.task.result)
        elif self.task.state == "failed" and self.on_error is not None:
            self.on_error(RuntimeError(self.task.error))
        if self.on_done is not None:
            self.on_done()
        return True


def frame_runner(tasks: list, mode: Optional[str] = None):
    """A ``runner`` for :class:`~ndxplorer.analysis.vizrank_model.VizRankModel`
    whose runs are pumped by the frame: each started run is appended to *tasks*."""

    def run(_parent, _text, func, *, args=(), maximum=0, on_partial=None, on_result=None,
            on_error=None, on_done=None, owner=None, cancellable=True, **_kw):
        task = FrameTask(func, args, on_partial, on_result, on_error, on_done, mode=mode)
        tasks.append(task)
        return task

    return run


def help_lines(columns: int) -> List[str]:
    """``vizrank_help.md`` as plain lines of at most *columns* characters:
    paragraphs and list items wrapped, emphasis marks dropped."""
    import textwrap

    try:
        text = VIZRANK_HELP.read_text(encoding="utf-8")
    except OSError:
        return ["The help text is not installed."]
    lines: List[str] = []
    for block in re.split(r"\n\s*\n", text):
        items = re.split(r"\n(?=\s*[-*] |\s*\d+\. )", block.strip())
        for item in items:
            item = re.sub(r"\s*\n\s*", " ", item)
            item = re.sub(r"\*\*|`|(?<!\w)\*(?=\S)|(?<=\S)\*(?!\w)", "", item)
            item = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", item)
            if item.startswith("#"):
                item = item.lstrip("#").strip().upper()
            indent = "  " if re.match(r"[-*] |\d+\. ", item) else ""
            lines.extend(textwrap.wrap(item, columns, subsequent_indent=indent) or [""])
        lines.append("")
    return lines


def _plain(text: str) -> str:
    """The guide's rich text as plain lines."""
    text = re.sub(r"<br\s*/?>", "\n", str(text))
    return re.sub(r"<[^>]+>", "", text)


# --------------------------------------------------------------------------- #
# The ranking panel
# --------------------------------------------------------------------------- #
class RankingPanel:
    """One *Find informative …* window: its model, form, help and tour."""

    def __init__(self, feature: "PlaybackExportFeature", pairs: bool) -> None:
        from emtk.dialog_window import DialogWindow
        from emtk.view_form import FormState

        from ...analysis.vizrank_model import load_spec as load_vizrank_spec

        self.feature = feature
        self.pairs = pairs
        self.spec = load_vizrank_spec()
        self.state = FormState(on_used=self._used)
        feature.app.forms[f"playback_export.rank.{pairs}"] = self.state
        self.model = None
        title = "Find informative projections" if pairs else "Find informative z parameters"
        self.window = DialogWindow(title, size=(520.0, 640.0), key=f"rank{int(pairs)}")
        self.show_help = False
        self._help_window = DialogWindow("Find informative projections - help",
                                         size=(560.0, 520.0), key=f"rankhelp{int(pairs)}")
        self._help_top = 0
        self.tour: Optional[int] = None
        self._tour_steps: Optional[list] = None
        self._awaited = False

    # ---- the model -------------------------------------------------------------
    def ensure_model(self) -> bool:
        """The model for the current table; a new one when the table changed."""
        from ...analysis.projection_rank_model import ProjectionRankModel

        context = self.feature.ranking_context()
        if context is None:
            self.discard()
            return False
        model = self.model
        if model is not None and model._run is not None and model.ranked_key() != context.key:
            self.discard()
            model = None
        if model is None:
            self.model = ProjectionRankModel(
                self.feature.ranking_context, self.pairs, on_apply=self.feature.apply_view,
                on_change=self.feature.islands_maybe_changed,
                runner=frame_runner(self.feature.tasks, self.feature.task_mode),
                defer=self.feature.defer)
            # This app paints the islands of the view on the map (map_image).
            self.model.overlay_available = self.pairs
        else:
            model.refresh_context()
        return True

    def discard(self) -> None:
        if self.model is not None:
            self.model.shutdown()
        self.model = None
        self.window.open = False

    def open(self) -> None:
        """Show the window and start (or resume) the ranking, as the Qt window does."""
        if not self.ensure_model():
            return
        self.window.open = True
        self.model.dialog_reopened()
        self.feature.follow_axes(force=True)

    def close(self) -> None:
        from ...analysis.vizrank import RunState

        self.window.open = False
        if self.model is not None:
            self.model.pause_computation(RunState.Hidden)

    # ---- drawing ------------------------------------------------------------
    def draw(self, frame_box) -> None:
        from emtk.view_form import draw_form

        if not self.window.open or self.model is None:
            return
        if self.window.pos is None:
            fx, fy, fw, _fh = frame_box
            self.window.pos = (fx + fw - min(self.window.size[0], fw - 20.0) - 24.0, fy + 40.0)
        pressed = self.window.begin(frame_box, buttons=("Guide", "?"))
        draw_form(self.spec, self.model, self.state, titles=False)
        self._draw_note()
        self.window.end()
        binding = self.state.tables.get("ranked_rows")
        request = self.model.select_request
        if binding is not None and request is not None:
            binding.refresh()
            if binding.control.select_key(request):
                self.model.select_request = None
        if pressed == "close":
            self.close()
        elif pressed == "?":
            self.show_help = not self.show_help
        elif pressed == "Guide":
            self.tour = 0
            self._awaited = False
        if self.show_help:
            self._draw_help(frame_box)
        if self.tour is not None:
            self._draw_tour(frame_box)

    def _draw_note(self) -> None:
        """What the selected row's score means (the Qt window's line under the table)."""
        import emtk

        binding = self.state.tables.get("ranked_rows")
        record = None
        if binding is not None:
            record = binding.record(binding.control.selected_index())
        if isinstance(record, dict) and record.get("note"):
            emtk.text_wrapped(str(record["note"]))

    def _draw_help(self, frame_box) -> None:
        """The panel's long help (``vizrank_help.md``), wrapped and scrolled by the wheel."""
        import emtk

        window = self._help_window
        x, y, w, h = self.window.box
        if window.pos is None:
            window.pos = (max(frame_box[0], x - 570.0), y)
        if window.begin(frame_box) == "close":
            self.show_help = False
        width = max(emtk.get_content_region_avail()[0], 100.0)
        columns = max(20, int(width // max(emtk.calc_text_size("M")[0], 1.0)) - 1)
        lines = help_lines(columns)
        row = emtk.get_text_line_height_with_spacing()
        visible = max(1, int((window.box[3] - window.HEADER_H - 16.0) // row))
        io = emtk.get_io()
        bx, by, bw, bh = window.box
        if io.mouse_wheel and bx <= io.mouse_pos[0] < bx + bw and by <= io.mouse_pos[1] < by + bh:
            self._help_top -= int(round(io.mouse_wheel * 3))
        self._help_top = min(max(self._help_top, 0), max(0, len(lines) - visible))
        for line in lines[self._help_top:self._help_top + visible]:
            emtk.text(line)
        window.end()

    def _steps(self) -> list:
        if self._tour_steps is None:
            try:
                self._tour_steps = json.loads(VIZRANK_GUIDE.read_text(encoding="utf-8"))["steps"]
            except (OSError, ValueError, KeyError):
                self._tour_steps = []
        return self._tour_steps

    def _used(self, name: str) -> None:
        steps = self._steps()
        if self.tour is not None and self.tour < len(steps):
            wanted = ANCHORS.get((steps[self.tour].get("target") or {}).get("name", ""))
            if wanted == name and steps[self.tour].get("await"):
                self._awaited = True

    def _draw_tour(self, frame_box) -> None:
        """The guided tour: each step outlines its control; an ``await`` step
        waits for the user to press it."""
        import emtk
        from emtk.dialog_window import DialogWindow

        steps = self._steps()
        if not steps or self.tour >= len(steps):
            self.tour = None
            return
        step = steps[self.tour]
        target = ANCHORS.get((step.get("target") or {}).get("name", ""))
        rect = self.state.rects.get(target) if target else None
        if rect is not None:
            rx, ry, rw, rh = rect
            emtk.get_foreground_draw_list().add_rect((rx - 3, ry - 3), (rx + rw + 3, ry + rh + 3),
                                                     (255, 200, 0, 255), 3.0, 0, 2.5)
        window = DialogWindow(f"Guide {self.tour + 1}/{len(steps)}: {step.get('title', '')}",
                              size=(360.0, 220.0), key=f"ranktour{int(self.pairs)}")
        x, y, w, h = self.window.box
        window.pos = (max(frame_box[0], x - 370.0), y + h - 230.0)
        if window.begin(frame_box) == "close":
            self.tour = None
            window.end()
            return
        emtk.text_wrapped(_plain(step.get("text", "")))
        waiting = bool(step.get("await")) and not self._awaited
        if waiting:
            emtk.text_wrapped(_plain(step["await"].get("hint", "")))
        if self.tour > 0 and emtk.button("Back##tour"):
            self.tour -= 1
            self._awaited = False
        emtk.same_line()
        last = self.tour == len(steps) - 1
        emtk.begin_disabled(waiting)
        if emtk.button(("Done" if last else "Next") + "##tour"):
            self.tour = None if last else self.tour + 1
            self._awaited = False
        emtk.end_disabled()
        window.end()


# --------------------------------------------------------------------------- #
# Export…
# --------------------------------------------------------------------------- #
class PublicationExportModel:
    """What ``publication_export.view.json`` binds to: format, DPI, marginals,
    transparency, *Export…* and *Cancel*."""

    def __init__(self, on_export: Callable[["PublicationExportModel"], None],
                 on_cancel: Callable[[], None]) -> None:
        from ...export.publication_figure import EXPORT_FORMATS

        self._formats = EXPORT_FORMATS
        self.format = next(iter(EXPORT_FORMATS))
        self.dpi = 300
        self.with_marginals = True
        self.transparent = False
        self._on_export = on_export
        self._on_cancel = on_cancel

    def format_options(self) -> list:
        return list(self._formats)

    @property
    def suffix(self) -> str:
        return self._formats[self.format][0]

    @property
    def is_vector(self) -> bool:
        return bool(self._formats[self.format][1])

    @property
    def mime(self) -> str:
        return self._formats[self.format][2]

    def enabled(self, name: str) -> bool:
        """DPI counts only for the raster format."""
        return not (name == "dpi" and self.is_vector)

    def export(self) -> None:
        self._on_export(self)

    def cancel(self) -> None:
        self._on_cancel()


def export_figure_bytes(model, options: PublicationExportModel) -> bytes:
    """The publication figure of *model*'s current view, as file bytes.

    Parameters
    ----------
    model : ndxplorer.app.model.ExplorerModel
        What is on screen: its last histograms, axis names and scales, colour map.
    options : PublicationExportModel
        Format, DPI, marginals, transparency.
    """
    from ...export.publication_figure import figure_bytes, render_publication_figure

    model.update()
    hist = model.histograms
    if hist is None:
        raise ValueError("No 2D histogram is available yet — load data and update the plot first.")
    fig = render_publication_figure(
        hist.H, hist.x_edges, hist.y_edges,
        x_marginal=hist.x, y_marginal=hist.y,
        x_label=model.x.name, y_label=model.y.name,
        cmap=str(model.colormap), x_log=model.x.log, y_log=model.y.log,
        z_log=bool(model.log_counts), dpi=int(options.dpi),
        with_marginals=bool(options.with_marginals))
    return figure_bytes(fig, options.suffix, dpi=int(options.dpi),
                        transparent=bool(options.transparent))


# --------------------------------------------------------------------------- #
# The feature
# --------------------------------------------------------------------------- #
class PlaybackExportFeature(Feature):
    """Playback, the two ranking windows and the publication export."""

    name = "playback_export"

    def __init__(self, app, task_mode: Optional[str] = None) -> None:
        super().__init__(app)
        from emtk.dialog_window import DialogWindow
        from emtk.view_form import FormState

        from ...core.playback import PlaybackController, fps_from_settings
        from ...plotting.playback_view_model import PlaybackViewModel
        from ...plotting.playback_view_model import load_spec as load_playback_spec

        self.controller = PlaybackController(fps=fps_from_settings(app.model.bundle.settings))
        self.playback = PlaybackViewModel(self.controller, on_change=self._playback_changed,
                                          on_axis_change=self._set_playback_axis)
        panel = load_playback_spec()["sections"][0]
        self.playback_sections = panel["sections"]
        #: Ranking runs to pump, and calls deferred to the next frame.
        self.tasks: List[FrameTask] = []
        self.task_mode = task_mode
        self._deferred: List[Callable[[], None]] = []
        self.rankings = {True: RankingPanel(self, True), False: RankingPanel(self, False)}
        self._axes_seen = None
        self._applying = False
        #: What the islands overlay was last drawn for, and its labels.
        self._islands_key = None
        self._islands_labels = None
        self.export_model: Optional[PublicationExportModel] = None
        self.export_spec = load_spec("publication_export")
        self.export_state = FormState()
        app.forms["playback_export.export"] = self.export_state
        self.export_window = DialogWindow("Publication export", size=(380.0, 210.0), key="export")
        self.on_data_changed()

    # ----------------------------------------------------------------- hooks
    def actions(self) -> Dict[str, Callable[[], Any]]:
        return {
            "find_projections": lambda: self.rankings[True].open(),
            "find_z_projections": lambda: self.rankings[False].open(),
            "export_figure": self.open_export,
        }

    def available(self, action: str) -> Optional[bool]:
        if action == "export_figure":
            return self.app.model.ready()
        return None

    def custom_sections(self) -> Dict[str, Callable]:
        return {"playback": self._draw_playback}

    def mask_terms(self) -> Dict[str, Any]:
        source = self.app.model.source
        if source is None or not self.controller.gating:
            return {}
        mask = self.controller.mask(source)
        if mask is None:
            return {}
        return {"slice_mask": mask, "slice_key": self.controller.slice_key()}

    def _islands_request(self):
        """``(key, model)`` of the islands the map should show, or ``(None, None)``."""
        panel = self.rankings[True]
        model = panel.model
        app_model = self.app.model
        if model is None or not model.show_islands or model.method != "populations" \
                or model._run is None or not app_model.has_data:
            return None, None
        hist = app_model.histograms
        key = (model._run.generation, app_model.x.name, app_model.y.name,
               None if hist is None else hist.revision)
        return key, model

    def islands_maybe_changed(self) -> None:
        """The ranking model changed: repaint the map if the islands overlay did."""
        key, _model = self._islands_request()
        if key != self._islands_key:
            self.app.plots.image_revision += 1

    def map_image(self, values):
        """The map coloured by the islands the Separation score found in this view,
        when *Show islands on the map* is on (each bin takes its main island's colour)."""
        import numpy as np

        from ...plotting.cluster_overlay import cluster_rgb_image

        key, model = self._islands_request()
        self._islands_key = key
        if key is None:
            return None
        app_model = self.app.model
        names = [app_model.x.name, app_model.y.name]
        if key != getattr(self, "_islands_for", None):
            source = app_model.source
            try:
                self._islands_labels = model.islands(
                    names, [source.column_values(n) for n in names])
            except Exception:  # noqa: BLE001 - the density map stands in
                logger.debug("islands overlay failed", exc_info=True)
                self._islands_labels = None
            self._islands_for = key
        labels = self._islands_labels
        hist = app_model.histograms
        if labels is None or hist is None:
            return None
        keep = app_model._keep_mask()
        if keep is not None:
            labels = labels[keep]
        rgb = cluster_rgb_image(app_model._visible_values(app_model.index_of(names[0])),
                                app_model._visible_values(app_model.index_of(names[1])),
                                labels, hist.x_edges, hist.y_edges,
                                log_counts=app_model.log_counts, include_noise=False)
        if rgb is None or rgb.shape[:2] != np.shape(values):
            return None
        alpha = np.full(rgb.shape[:2] + (1,), 255, dtype=np.uint8)
        return np.concatenate([rgb, alpha], axis=2)

    def on_data_changed(self) -> None:
        """Point the playback at the frame index or the macro time, as the Qt window does."""
        from ...core.playback import macro_time_column
        from ...utils.axis_helpers import frame_column

        model = self.app.model
        self.playback.stop()
        if not model.has_data:
            self.playback.set_axis_options([])
            self.controller.set_axis(None)
            return
        names = list(model.parameter_names)
        self.playback.set_axis_options([""] + names)
        self._set_playback_axis(frame_column(names) or macro_time_column(names))
        for panel in self.rankings.values():
            if panel.model is not None and panel.window.open:
                panel.ensure_model()

    def animating(self) -> bool:
        from ...analysis.vizrank import RunState

        return (self.playback.playing or bool(self.tasks) or bool(self._deferred)
                or any(p.model is not None and p.model.run_state == RunState.Running
                       for p in self.rankings.values()))

    def draw_windows(self) -> bool:
        self.playback.tick()
        self.pump()
        self.follow_axes()
        box = self.app.box
        for panel in self.rankings.values():
            panel.draw(box)
        return self._draw_export(box)

    # -------------------------------------------------------------- playback
    def _set_playback_axis(self, name: Optional[str]) -> None:
        source = self.app.model.source
        values = None
        if name and source is not None:
            try:
                values = source.column_values(name)
            except Exception as exc:  # noqa: BLE001 - the column went away
                logger.warning("Playback column %r unreadable: %s", name, exc)
                name = None
        self.controller.set_axis(name, values)
        self.app.model.invalidate()

    def _playback_changed(self) -> None:
        self.app.model.invalidate()

    def _draw_playback(self, section, _model, state, width: float) -> None:
        """The Playback panel's controls, over the playback view model."""
        import emtk
        from emtk.view_form import draw_sections

        draw_sections(self.playback_sections, self.playback, state, 1, titles=False)
        # The slice on screen and how many points survive it, on hover of the
        # Step row (the Qt window's tooltip there).
        for key in ("position.slider", "position.edit"):
            rect = state.rects.get(key)
            if rect is not None and emtk.is_mouse_hovering_rect(
                    (rect[0], rect[1]), (rect[0] + rect[2], rect[1] + rect[3])):
                emtk.set_tooltip(self.playback_status())

    def on_z_select(self) -> None:
        """The z panel's *select* during playback: the slice on screen becomes a
        gate too, since the gate drawn on it describes that slice (the Qt
        window's ``_add_playback_selection_if_needed``). Not twice."""
        model = self.app.model
        name = self.controller.axis_name
        if not self.controller.gating or not name or model.index_of(name) < 0:
            return
        lower, upper = self.controller.bounds
        for row in model.gates:
            if row.name == name and row.lower == lower and row.upper == upper:
                return
        model.add_interval(name, lower, upper)

    def playback_status(self) -> str:
        model = self.app.model
        if model.has_data and self.controller.gating:
            self.playback.set_count_text(f"{model.count_current} of {model.count_total} points")
        else:
            self.playback.set_count_text("")
        return self.playback.status_text()

    # --------------------------------------------------------------- ranking
    def defer(self, fn: Callable[[], None]) -> None:
        """Run *fn* next frame (a continued ranking's launch)."""
        self._deferred.append(fn)

    def pump(self) -> None:
        """Advance the ranking runs and run what was deferred."""
        deferred, self._deferred = self._deferred, []
        for fn in deferred:
            fn()
        for task in list(self.tasks):
            if task.pump():
                self.tasks.remove(task)

    def ranking_context(self):
        """What a ranking may use, from the emtk model: table, axis settings,
        enabled gates, clusters (when the analysis feature has them) and z."""
        from ...analysis.projection_rank_model import build_context

        model = self.app.model
        if not model.has_data:
            return None
        selections = [s for s in model.gates.selections() if getattr(s, "enabled", True)]
        clusters = None
        for feature in self.app.features:
            labels = getattr(feature, "cluster_labels", None)
            if labels is not None:
                clusters = labels
                break
        return build_context(model.source, model.axis_settings, selections, clusters,
                             model.z.name)

    def apply_view(self, payload: dict) -> None:
        """Show the view a ranked row describes, drawn in the scale it was scored in."""
        model = self.app.model
        self._applying = True
        try:
            keys = ("z",) if "z" in payload else ("x", "y")
            for key in keys:
                model.set_parameter(key, str(payload[key]))
                log = str(payload.get(f"scale_{key}", "lin")) == "log"
                axis = model.axis(key)
                if axis.log != log:
                    axis.log = log
                    model.auto_range(key)
            if "z" in payload and not model.z_gate_enabled:
                self.app.panel.z_gate_enabled = True
            self._axes_seen = (model.x.name, model.y.name, model.z.name)
        finally:
            self._applying = False

    def follow_axes(self, force: bool = False) -> None:
        """Select the row of a view picked by hand (Orange's auto-select)."""
        model = self.app.model
        seen = (model.x.name, model.y.name, model.z.name)
        if not force and (seen == self._axes_seen or self._applying):
            return
        self._axes_seen = seen
        pairs, single = self.rankings[True], self.rankings[False]
        if pairs.window.open and pairs.model is not None:
            pairs.model.auto_select({"x": seen[0], "y": seen[1]})
        if single.window.open and single.model is not None:
            single.model.auto_select({"z": seen[2]})

    # ---------------------------------------------------------------- export
    def open_export(self) -> None:
        if not self.app.model.ready():
            self.app.message = ("Publication export", "No 2D histogram is available yet — "
                                "load data and update the plot first.")
            return
        if self.export_model is None:
            self.export_model = PublicationExportModel(self._export, self._close_export)
        self.export_window.open = True

    def _close_export(self) -> None:
        self.export_window.open = False

    def _export(self, options: PublicationExportModel) -> None:
        self.export_window.open = False
        try:
            data = export_figure_bytes(self.app.model, options)
        except Exception as exc:  # noqa: BLE001 - shown, the window goes on
            logger.exception("publication export failed")
            self.app.message = ("Publication export", f"Export failed:\n{exc}")
            return
        service = getattr(self.app, "io_service", None)
        name = f"ndxplorer_figure{options.suffix}"
        if service is None:
            self.app.message = ("Publication export", "No file service to save with.")
            return
        service.save_bytes(name, data, options.mime, title="Export publication figure",
                           filters=[(options.format, [f"*{options.suffix}"])])

    def _draw_export(self, box) -> bool:
        from emtk.view_form import draw_form

        if not self.export_window.open or self.export_model is None:
            return False
        if self.export_window.begin(box) == "close":
            self.export_window.open = False
        draw_form(self.export_spec, self.export_model, self.export_state, titles=False)
        self.export_window.end()
        return True

    # --------------------------------------------------------------- capture
    def capture_actions(self) -> Dict[str, str]:
        return {"actionFindProjections": "find_projections",
                "actionFindZParameters": "find_z_projections"}

    def capture_ops(self) -> Dict[str, Callable]:
        return {"call": self._op_call, "wait_until": self._op_wait_until,
                "click": self._op_click}

    def capture_targets(self) -> Dict[str, Callable]:
        targets = {
            "widget:pc.playback_form": lambda replay: replay.panel_rect("Playback"),
            "widget:win.projection_rank.dialogs[True]": lambda replay: self._window_box(True),
            "widget:win.projection_rank.dialogs[False]": lambda replay: self._window_box(False),
        }
        if self.export_window.open:
            targets["dialog"] = lambda replay: self.export_window.box
        return targets

    def _window_box(self, pairs: bool):
        panel = self.rankings[pairs]
        return panel.window.box if panel.window.open else None

    def _ranking_model(self, pairs: bool):
        model = self.rankings[pairs].model
        if model is None:
            from ..capture import Unsupported

            raise Unsupported("the ranking window is not open")
        return model

    def _op_call(self, replay, step: dict) -> None:
        """The scenario's Python calls on the Qt window, spoken to this feature."""
        code = step["code"].strip()
        if "pc.playback_model" in code:
            for line in code.splitlines():
                line = line.strip()
                steps = re.fullmatch(r"\[pc\.playback_model\.(step_forward|step_backward)\(\)"
                                     r" for _ in range\((\d+)\)\]", line)
                assign = re.fullmatch(r"pc\.playback_model\.(\w+)\s*=\s*(.+)", line)
                if steps:
                    for _ in range(int(steps.group(2))):
                        getattr(self.playback, steps.group(1))()
                elif assign:
                    setattr(self.playback, assign.group(1), eval(assign.group(2), {}))  # noqa: S307
                else:
                    from ..capture import Unsupported

                    raise Unsupported(f"call {line!r}")
            replay.settle()
            return
        rank = re.search(r"win\.projection_rank\.dialogs\[(True|False)\]\.model", code)
        if rank:
            pairs = rank.group(1) == "True"
            model = self._ranking_model(pairs)
            namespace = {"win": _QtWindowShim(self), "m": model}
            exec(code, namespace)  # noqa: S102 - the scenario's own replay code
            replay.settle()
            return
        replay.op_call(step)

    def _op_wait_until(self, replay, step: dict) -> None:
        """Draw frames until the scenario's condition holds (the ranking finished)."""
        expr = step["expr"]
        namespace = {"win": _QtWindowShim(self)}
        deadline = time.monotonic() + float(step.get("timeout", 60000)) / 1000.0
        while time.monotonic() < deadline:
            replay.draw()
            if eval(expr, namespace):  # noqa: S307 - the scenario's own condition
                replay.settle()
                return
            time.sleep(0.005)
        from ..capture import Unsupported

        raise Unsupported(f"timed out waiting for {expr!r}")

    def _op_click(self, replay, step: dict) -> None:
        if step.get("widget") == "win.toolButton_publication_export":
            rect = replay.app.control_rect("export_figure")
            if rect is not None:
                replay.click_rect(rect)
            else:
                self.app.run_action("export_figure")
            replay.settle()
            return
        replay.op_click(step)


class _QtWindowShim:
    """``win.projection_rank.dialogs[pairs].model`` for a scenario's replay code."""

    class _Dialog:
        def __init__(self, model) -> None:
            self.model = model

    def __init__(self, feature: PlaybackExportFeature) -> None:
        self.projection_rank = self
        self.dialogs = {pairs: self._Dialog(panel.model)
                        for pairs, panel in feature.rankings.items()}


def create(app) -> PlaybackExportFeature:
    return PlaybackExportFeature(app)
