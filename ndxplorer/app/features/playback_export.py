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

__all__ = ["PlaybackExportFeature", "PublicationExportModel", "ToolWindow", "frame_runner",
           "create"]

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


# --------------------------------------------------------------------------- #
# A floating tool window
# --------------------------------------------------------------------------- #
class ToolWindow:
    """A titled window over the main one: dragged by its title, closed by ✕.

    emtk windows carry no chrome of their own, so the title row is drawn here:
    the title, the caller's header buttons and ✕.
    """

    HEADER_H = 26.0

    def __init__(self, key: str, title: str, size=(520.0, 640.0)) -> None:
        self.key = key
        self.title = title
        self.size = size
        self.pos: Optional[tuple] = None
        self.open = False
        self.box = (0.0, 0.0, float(size[0]), float(size[1]))
        self._drag = None

    def place(self, frame_box) -> tuple:
        x0, y0, fw, fh = frame_box
        w, h = min(self.size[0], fw - 20.0), min(self.size[1], fh - 40.0)
        if self.pos is None:
            self.pos = (x0 + fw - w - 24.0, y0 + 40.0)
        x = min(max(self.pos[0], x0), x0 + fw - 40.0)
        y = min(max(self.pos[1], y0), y0 + fh - self.HEADER_H)
        self.box = (x, y, w, h)
        return self.box

    def begin(self, frame_box, buttons=()) -> Optional[str]:
        """Open the window and draw its title row; returns the header button
        pressed (``"close"`` for ✕), or ``None``."""
        import emtk

        from emtk.im_core import Col

        x, y, w, h = self.place(frame_box)
        emtk.begin(f"{self.title}##{self.key}", (x, y, w, h))
        # An emtk window has no background of its own; a window over the
        # plots needs one (the style's popup colour, and its border).
        style = emtk.get_style()
        draw = emtk.get_window_draw_list()
        r, g, b = style.color(Col.WINDOW_BG)[:3]
        draw.add_rect_filled((x, y), (x + w, y + h), (r, g, b, 255))
        draw.add_rect_filled((x, y), (x + w, y + self.HEADER_H), style.color(Col.TITLE_BG_ACTIVE))
        draw.add_rect((x, y), (x + w, y + h), style.color(Col.BORDER))
        io = emtk.get_io()
        header = (x, y, w, self.HEADER_H)
        mx, my = io.mouse_pos
        over = header[0] <= mx < header[0] + header[2] and header[1] <= my < header[1] + header[3]
        emtk.set_cursor_screen_pos((x + 8.0, y + 5.0))
        emtk.text(self.title)
        pressed = None
        labels = list(buttons) + ["✕"]
        widths = [emtk.calc_text_size(label)[0] + 16.0 for label in labels]
        bx = x + w - sum(widths) - 6.0 * len(labels) - 4.0
        for label, bw in zip(labels, widths):
            emtk.same_line()
            emtk.set_cursor_screen_pos((bx, y + 3.0))
            if emtk.button(f"{label}##{self.key}.{label}", (bw, 0.0)):
                pressed = "close" if label == "✕" else label
            bx += bw + 6.0
        on_button = emtk.is_any_item_hovered()
        if io.mouse_clicked[0] and over and not on_button and pressed is None:
            self._drag = (mx - x, my - y)
        if self._drag is not None:
            if io.mouse_down[0]:
                self.pos = (mx - self._drag[0], my - self._drag[1])
            else:
                self._drag = None
        emtk.begin_child((x + 8.0, y + self.HEADER_H + 6.0, w - 16.0, h - self.HEADER_H - 12.0))
        return pressed

    @staticmethod
    def end() -> None:
        import emtk

        emtk.end_child()
        emtk.end()


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
        from emtk.view_form import FormState

        from ...analysis.vizrank_model import load_spec as load_vizrank_spec

        self.feature = feature
        self.pairs = pairs
        self.spec = load_vizrank_spec()
        self.state = FormState(on_used=self._used)
        # The window's dropdowns open through the frame, like the dock's.
        feature.app.forms[f"playback_export.rank.{pairs}"] = self.state
        self.model = None
        title = "Find informative projections" if pairs else "Find informative z parameters"
        self.window = ToolWindow(f"rank{int(pairs)}", title)
        self.show_help = False
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
        if model is not None and model._run is not None and model._run.settings[3] != context.key:
            self.discard()
            model = None
        if model is None:
            self.model = ProjectionRankModel(
                self.feature.ranking_context, self.pairs, on_apply=self.feature.apply_view,
                runner=frame_runner(self.feature.tasks, self.feature.task_mode),
                defer=self.feature.defer)
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
        import emtk

        window = ToolWindow(f"rankhelp{int(self.pairs)}", "Find informative projections - help",
                            size=(560.0, 520.0))
        x, y, w, h = self.window.box
        window.pos = (max(frame_box[0], x - 570.0), y)
        if window.begin(frame_box) == "close":
            self.show_help = False
        try:
            text = VIZRANK_HELP.read_text(encoding="utf-8")
        except OSError:
            text = "The help text is not installed."
        emtk.text_wrapped(text.replace("**", "").replace("*", ""))
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
        window = ToolWindow(f"ranktour{int(self.pairs)}",
                            f"Guide {self.tour + 1}/{len(steps)}: {step.get('title', '')}",
                            size=(360.0, 220.0))
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
        self.export_model: Optional[PublicationExportModel] = None
        self.export_spec = load_spec("publication_export")
        self.export_state = FormState()
        app.forms["playback_export.export"] = self.export_state
        self.export_window = ToolWindow("export", "Publication export", size=(380.0, 210.0))
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
        x0, y0, w, h = box
        ew, eh = self.export_window.size
        if self.export_window.pos is None:
            self.export_window.pos = (x0 + (w - ew) / 2.0, y0 + (h - eh) / 2.0)
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
            rect = replay.app.forms["plot_corner"].rects.get("export_figure")
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
