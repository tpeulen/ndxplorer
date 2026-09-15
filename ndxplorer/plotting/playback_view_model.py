"""The Playback panel: what AutoForm binds to, and the timer that drives it.

:class:`~ndxplorer.core.playback.PlaybackController` decides *which points are
shown*; this decides *when the step changes*. Keeping the two apart is what lets
the gating be tested without a Qt event loop, which is where the interesting
cases live -- the edges of the range, the last step, the frame-index equivalence.

The panel itself is declared in ``playback.view.json`` and rendered by chisurf's
AutoForm, so the controls, their tooltips and the fold state are data rather than
another two hundred lines of widget construction.
"""

from __future__ import annotations

import json
import pathlib
import typing

from qtpy import QtCore

from ..core import playback as pb
from ..logging_config import logging

__all__ = ["PlaybackViewModel", "VIEW_SPEC_PATH"]

VIEW_SPEC_PATH = pathlib.Path(__file__).parent / "playback.view.json"


class PlaybackViewModel(QtCore.QObject):
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
        the spec has to be re-read. The host defers the rebuild, because it
        arrives from inside a signal of a widget the rebuild destroys.
    parent : QtCore.QObject, optional
        Qt parent for the playback timer.
    """

    def __init__(self, controller, on_change=None, on_axis_change=None,
                 on_rebuild=None, parent=None):
        super().__init__(parent)
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

        self._timer = QtCore.QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._apply_interval()

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

        with open(VIEW_SPEC_PATH, encoding="utf-8") as fh:
            spec = json.load(fh)
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

    def _apply_interval(self) -> None:
        self._timer.setInterval(max(1, int(1000 / max(1, self.playback.fps))))

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
        self.playback.fps = max(1, int(value))
        self._apply_interval()

    # ------------------------------------------------------------ transport

    @property
    def playing(self) -> bool:
        """Whether the timer is running."""
        return self._timer.isActive()

    def _can_step(self) -> bool:
        """Stepping needs an axis and a mode that has steps to move between."""
        return self.playback.gating

    def stop(self) -> None:
        """Stop the timer without changing the step."""
        self._timer.stop()
        self.playback.direction = 0

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
        self._apply_interval()
        self._timer.start()
        self._changed()

    def _tick(self) -> None:
        if not self._can_step():
            self.stop()
            return
        self.playback.step(self.playback.direction)
        self._changed()
