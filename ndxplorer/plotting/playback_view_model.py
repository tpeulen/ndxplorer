"""The Playback panel: what a ``view.json`` binds to, and when the step changes.

:class:`~ndxplorer.core.playback.PlaybackController` decides *which points are
shown*; this decides *when the step changes*. Keeping the two apart is what lets
the gating be tested without an event loop, which is where the interesting
cases live -- the edges of the range, the last step, the frame-index equivalence.

The panel itself is declared in ``playback.view.json``. The Qt window renders it
with chisurf's AutoForm and the emtk app (:mod:`ndxplorer.app.features.playback_export`)
with :mod:`emtk.view_form`; both bind the same :class:`PlaybackViewModel`.

No toolkit is imported here and nothing here owns a timer. Playing is a flag
and a due time: whoever drives the display calls :meth:`PlaybackViewModel.tick`
-- the emtk app from its frame loop (so it plays in the browser, where there is
no timer thread), the Qt window from a ``QTimer`` it starts and stops when
``on_timing`` says the model started, stopped or changed speed.
"""

from __future__ import annotations

import json
import pathlib
import time
import typing

from ..core import playback as pb
from ..logging_config import logging

__all__ = ["PlaybackViewModel", "VIEW_SPEC_PATH", "load_spec"]

VIEW_SPEC_PATH = pathlib.Path(__file__).parent / "playback.view.json"


def load_spec() -> dict:
    """The parsed ``playback.view.json``, as a plain mapping."""
    with open(VIEW_SPEC_PATH, encoding="utf-8") as fh:
        return json.load(fh)


class PlaybackViewModel:
    """AutoForm binding for a :class:`~ndxplorer.core.playback.PlaybackController`.

    Every field AutoForm writes is a property that forwards to the controller and
    then calls `on_change`, so there is one place that knows a redraw is needed
    and the controller stays free of both Qt and the plot.

    Parameters
    ----------
    controller : ndxplorer.core.playback.PlaybackController
        The state being edited.
    on_change : callable, optional
        Called with no arguments after any edit that changes what is on screen.
    on_axis_change : callable, optional
        Called with the new axis name when the user picks a different column;
        the host owns the data and so is the only thing that can supply the
        column's values.
    on_rebuild : callable, optional
        Called when the *shape* of the form changed rather than a value in it --
        the step slider's range is the step count, which is itself editable, so
        a retained form (the Qt AutoForm) has to re-read the spec. An immediate
        form reads :meth:`bounds` every frame and needs no rebuild.
    on_timing : callable, optional
        Called with no arguments when playing started or stopped or the speed
        changed -- for a host that drives :meth:`tick` from a timer of its own
        and has to start, stop or re-time it.
    clock : callable, optional
        Seconds, monotonic; :func:`time.monotonic` by default. Injectable so the
        timing is testable without waiting.
    """

    #: A tick this close to its due time (as a fraction of the step interval)
    #: already counts: a timer set to the interval fires a millisecond early as
    #: often as late, and a frame loop is only ever near the due time.
    TOLERANCE = 0.25

    def __init__(self, controller, on_change=None, on_axis_change=None,
                 on_rebuild=None, on_timing=None, clock=None):
        self.playback = controller
        self._on_change = on_change
        self._on_axis_change = on_axis_change
        self._on_rebuild = on_rebuild
        self._options: typing.List[str] = []
        self._count_text = ""
        # Folded on opening: the panel is the one block a user sets up once and
        # then wants out of the way. Remembered here rather than read from the
        # spec each time, because the step slider's range is rebuilt whenever
        # the step count changes -- and a rebuild that re-reads a hard-coded
        # ``collapsed: true`` folds the panel under the user's hands.
        self.collapsed = True

        self._on_timing = on_timing
        self._clock = clock or time.monotonic
        self._playing = False
        self._next_due: typing.Optional[float] = None

    # ------------------------------------------------------------- plumbing

    def view_spec(self):
        """The parsed ``playback.view.json``, with the step slider's range set.

        The slider runs over the steps, and how many there are is itself a field
        of this form, so that one bound cannot be authored in the JSON. It is
        patched into the mapping before parsing rather than after: the section
        dataclasses are frozen, which is what keeps a spec from being edited by
        the widgets it built.
        """
        from chisurf.core.dataspec import load_view_spec

        spec = load_spec()
        panel = spec["sections"][0]
        panel["collapsed"] = bool(self.collapsed)
        for section in panel["sections"]:
            if section.get("attr") == "position":
                section["maximum"] = max(0, int(self.playback.n_steps) - 1)
        return load_view_spec(spec)

    def _changed(self) -> None:
        if callable(self._on_change):
            self._on_change()

    def _rebuild(self) -> None:
        if callable(self._on_rebuild):
            self._on_rebuild()

    def _timing_changed(self) -> None:
        if callable(self._on_timing):
            self._on_timing()

    @property
    def interval(self) -> float:
        """Seconds between two steps while playing."""
        return 1.0 / max(1, int(self.playback.fps))

    def bounds(self, name: str):
        """Run-time limits of a field (:mod:`emtk.view_form`'s hook): the step
        slider runs over the steps there are."""
        if name == "position":
            return (0, max(0, int(self.playback.n_steps) - 1))
        return None

    def enabled(self, name: str) -> bool:
        """Which control is usable now: all of them once there is a column to
        offer, the transport and the step only with an axis chosen."""
        if not self._options:
            return False
        if name in ("position", "step_backward", "step_forward", "play_backward",
                    "play_forward", "pause", "n_steps", "mode"):
            return self.playback.enabled
        return True

    def set_axis_options(self, names: typing.Sequence[str]) -> None:
        """Set the columns offered in the axis combo."""
        self._options = [str(n) for n in names]

    def axis_options(self) -> typing.List[str]:
        """Columns the playback can run along (the combo's option source)."""
        return list(self._options)

    def set_count_text(self, text: str) -> None:
        """Set the point count shown beside the slice, supplied by the plot."""
        self._count_text = str(text)

    def status_text(self) -> str:
        """The panel's live readout: which slice, and how many points survive."""
        text = self.playback.status_text()
        if self._count_text:
            text = f"{text} · {self._count_text}"
        return text

    # --------------------------------------------------------------- fields

    @property
    def axis_name(self) -> str:
        # AutoForm shows a combo, which has no concept of "unset"; the empty
        # string is the option the caller sees for "do not play anything back".
        return self.playback.axis_name or ""

    @axis_name.setter
    def axis_name(self, value: str) -> None:
        name = str(value) or None
        if name == self.playback.axis_name:
            return
        self.stop()
        if callable(self._on_axis_change):
            self._on_axis_change(name)
        else:  # pragma: no cover - host always supplies one
            self.playback.set_axis(name)
        self._rebuild()
        self._changed()

    @property
    def n_steps(self) -> int:
        return int(self.playback.n_steps)

    @n_steps.setter
    def n_steps(self, value: int) -> None:
        if int(value) == self.playback.n_steps:
            return
        self.playback.set_n_steps(int(value))
        self._rebuild()
        self._changed()

    @property
    def position(self) -> int:
        return int(self.playback.position)

    @position.setter
    def position(self, value: int) -> None:
        if int(value) == self.playback.position:
            return
        self.playback.set_position(int(value))
        self._changed()

    @property
    def mode(self) -> str:
        return self.playback.mode

    @mode.setter
    def mode(self, value: str) -> None:
        if value == self.playback.mode:
            return
        try:
            self.playback.set_mode(str(value))
        except ValueError as exc:
            logging.warning("%s", exc)
            return
        if self.playback.mode == pb.MODE_STACK:
            self.stop()
        self._changed()

    @property
    def fps(self) -> int:
        return int(self.playback.fps)

    @fps.setter
    def fps(self, value: int) -> None:
        fps = max(1, int(value))
        if fps == self.playback.fps:
            return
        self.playback.fps = fps
        if self._playing:
            self._next_due = self._clock() + self.interval
        self._timing_changed()

    # ------------------------------------------------------------ transport

    @property
    def playing(self) -> bool:
        """Whether the playback is running."""
        return self._playing

    def _can_step(self) -> bool:
        """Stepping needs an axis and a mode that has steps to move between."""
        return self.playback.gating

    def stop(self) -> None:
        """Stop playing without changing the step."""
        was = self._playing
        self._playing = False
        self._next_due = None
        self.playback.direction = 0
        if was:
            self._timing_changed()

    def pause(self) -> None:
        """Transport: stop."""
        self.stop()
        self._changed()

    def step_forward(self) -> None:
        """Transport: one step forward, wrapping at the end."""
        self._step(1)

    def step_backward(self) -> None:
        """Transport: one step backward, wrapping at the start."""
        self._step(-1)

    def _step(self, delta: int) -> None:
        if not self._can_step():
            return
        self.playback.step(delta)
        self._changed()

    def play_forward(self) -> None:
        """Transport: run forward until stopped."""
        self._play(1)

    def play_backward(self) -> None:
        """Transport: run backward until stopped."""
        self._play(-1)

    def _play(self, direction: int) -> None:
        # Pressing the direction already playing stops it, so the two play
        # buttons behave like the checkable pair they replace without needing
        # a checkable button (a button_row has none).
        if self.playing and self.playback.direction == direction:
            self.pause()
            return
        if not self._can_step():
            # Playing in stack mode is a request to watch the data change, and
            # stack mode is the one where it cannot. Start from the beginning of
            # the measurement in window mode rather than doing nothing.
            if not self.playback.enabled:
                return
            self.playback.set_mode(pb.MODE_WINDOW)
            self.playback.set_position(0 if direction > 0 else self.playback.n_steps - 1)
        self.playback.direction = direction
        self._playing = True
        self._next_due = self._clock() + self.interval
        self._timing_changed()
        self._changed()

    def seconds_to_next_step(self, now: typing.Optional[float] = None) -> typing.Optional[float]:
        """How long until :meth:`tick` steps; ``None`` while stopped."""
        if not self._playing or self._next_due is None:
            return None
        now = self._clock() if now is None else float(now)
        return max(0.0, self._next_due - now)

    def tick(self, now: typing.Optional[float] = None) -> bool:
        """Advance one step if one is due; returns whether it stepped.

        Called as often as the host likes -- every frame, or from a timer at
        the step interval. At most one step is taken per call: a display that
        cannot keep up drops steps rather than showing a burst of them, so the
        playback keeps its speed and loses frames instead.
        """
        if not self._playing:
            return False
        now = self._clock() if now is None else float(now)
        interval = self.interval
        if self._next_due is None:
            self._next_due = now + interval
            return False
        if now < self._next_due - self.TOLERANCE * interval:
            return False
        if not self._can_step():
            self.stop()
            self._changed()
            return False
        self.playback.step(self.playback.direction)
        self._next_due += interval
        if self._next_due <= now:
            self._next_due = now + interval
        self._changed()
        return True
