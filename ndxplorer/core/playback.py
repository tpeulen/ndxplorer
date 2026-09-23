"""Playing a data set back along one of its own columns.

A burst table is a time series. Every burst carries the macro time at which it
happened, monotonic across all the files of a measurement, and a sample that
photobleaches, aggregates or drifts produces a *moving* population that a single
static histogram over the whole acquisition averages away. An image stack has the
same shape with a different column: the frame index.

Those were two features here. The frame index had a spin box, five transport
buttons and a timer; macro time had nothing, and the frame-column detector
explicitly rejected any column whose name contains "time". They are one feature:
gate the plot on an interval of one column and step the interval.

The three modes answer three different questions:

``window``
    One slice at a time -- what the sample looked like *then*. This is normal
    playback, and for a frame column it reduces exactly to ``column == frame``
    (see :func:`axis_geometry`), which is what the frame selector did.
``integrate``
    Everything up to now, accumulating. What the static plot is built from, but
    watching it fill in: a population that arrives late is invisible in the final
    histogram and obvious here.
``stack``
    No gating at all -- the whole measurement, which is the plot ndX has always
    drawn.

Nothing in this module imports Qt. The widget that drives it lives in
:mod:`ndxplorer.plotting.playback_view_model`; the mask it produces reaches the
data layer through :class:`~ndxplorer.core.data.mask_state.MaskState`.
"""

from __future__ import annotations

import dataclasses
import re
import typing

import numpy as np

from ..logging_config import logging

__all__ = [
    "MODES",
    "MODE_INTEGRATE",
    "MODE_STACK",
    "MODE_WINDOW",
    "PlaybackController",
    "axis_geometry",
    "fps_from_settings",
    "macro_time_column",
]

#: Steps per second when the settings say nothing.
DEFAULT_FPS = 10


#: One slice at a time: ``edges[i] <= v < edges[i + 1]``.
MODE_WINDOW = "window"
#: Everything from the start up to the current edge: ``v < edges[i + 1]``.
MODE_INTEGRATE = "integrate"
#: No gating -- the whole measurement at once.
MODE_STACK = "stack"

MODES = (MODE_WINDOW, MODE_INTEGRATE, MODE_STACK)

#: Steps a continuous axis is cut into when nothing says otherwise. Chosen so a
#: playback at the default rate lasts a handful of seconds whatever the length of
#: the measurement -- the alternative, a fixed window width in seconds, runs for
#: three minutes on a one-hour acquisition and is over instantly on a short one.
DEFAULT_N_STEPS = 100

#: An integral column is played back one value per step, but only up to this
#: span. "Number of Photons" is integral too, and a step per photon count is a
#: playback thousands of frames long that no one asked for.
MAX_INDEX_STEPS = 1024

#: What the macro time is called, best first. The ``.bur`` reader rebases the
#: column to seconds and offsets it across files; the HDF5 and CSV readers do
#: neither, so a table loaded that way still carries the millisecond spelling and
#: restarts at zero on every file it was concatenated from.
_MACRO_TIME_NAMES = ("mean macro time (s)", "mean macro time (ms)", "mean macro time")


def macro_time_column(param_names: typing.Sequence[str]) -> typing.Optional[str]:
    """The per-burst macro-time column, or ``None``.

    Parameters
    ----------
    param_names : sequence of str
        Column names of the loaded table.

    Returns
    -------
    str or None
        The matching column name as spelled in the data, preferring seconds over
        milliseconds when a table carries both.
    """
    lowered = {str(name).lower(): name for name in param_names}
    for wanted in _MACRO_TIME_NAMES:
        if wanted in lowered:
            return lowered[wanted]
    # A per-detector "Mean Macrotime (green) (ms)" is a macro time as well, and
    # it is all a table written by some other exporter may have. Taken only when
    # the un-suffixed column is absent, so the whole-burst time wins.
    for name in param_names:
        text = str(name).lower()
        if "macro" in text and "time" in text:
            return name
    return None


def fps_from_settings(settings: typing.Optional[dict]) -> int:
    """The playback rate a settings mapping asks for, in steps per second.

    Parameters
    ----------
    settings : dict or None
        The parsed ``*.settings.json``; its ``playback`` entry is read.

    Returns
    -------
    int
        ``playback.fps``; else the older ``playback.frame_duration_ms`` turned
        into a rate (a settings file from before the change keeps working, and
        there is no migration to run); else :data:`DEFAULT_FPS`.
    """
    playback = (settings or {}).get("playback") or {}
    try:
        if "fps" in playback:
            return max(1, int(playback["fps"]))
        duration = playback.get("frame_duration_ms")
        if duration:
            return max(1, int(round(1000.0 / float(duration))))
    except (TypeError, ValueError) as exc:
        logging.warning("Unreadable playback settings %r: %s", playback, exc)
    return DEFAULT_FPS


def unit_of(name: str) -> str:
    """The unit in a column name, as written.

    Parameters
    ----------
    name : str
        A column name such as ``"Mean Macro Time (s)"``.

    Returns
    -------
    str
        ``"s"`` for the example above, ``""`` when the name carries no
        parenthesised unit.
    """
    found = re.findall(r"\(([^()]*)\)", str(name))
    return found[-1].strip() if found else ""


def axis_geometry(
    values: np.ndarray,
    n_steps: typing.Optional[int] = None,
) -> typing.Tuple[float, float, int, bool]:
    """Bounds and a step count for playing a column back.

    An integral column of modest span is an *index*: frames, or anything else
    counted. Its bounds are pushed half a step outwards so that with one step per
    value the interval test is exact -- ``-0.5 <= v < 0.5`` selects frame 0 and
    nothing else, which is the ``column == frame`` the frame selector used to do.
    Anything else is continuous and is cut into `n_steps` equal parts.

    Parameters
    ----------
    values : numpy.ndarray
        The column, as floats. Non-finite entries are ignored.
    n_steps : int, optional
        Requested number of steps. Ignored for an index axis, which always gets
        one step per value; defaults to :data:`DEFAULT_N_STEPS` otherwise.

    Returns
    -------
    lo, hi : float
        Outer edges of the playback range.
    n_steps : int
        Number of steps between them, at least 1.
    is_index : bool
        Whether the axis was recognised as an index.
    """
    finite = np.asarray(values, dtype=np.float64)
    finite = finite[np.isfinite(finite)]
    if finite.size == 0:
        return 0.0, 1.0, max(1, int(n_steps or DEFAULT_N_STEPS)), False

    lo, hi = float(finite.min()), float(finite.max())
    integral = bool(np.all(finite == np.round(finite)))
    span = hi - lo
    if integral and span <= MAX_INDEX_STEPS:
        return lo - 0.5, hi + 0.5, int(round(span)) + 1, True

    if hi <= lo:  # a constant column: one step covering it
        return lo, lo + 1.0, 1, False
    return lo, hi, max(1, int(n_steps or DEFAULT_N_STEPS)), False


@dataclasses.dataclass
class PlaybackController:
    """Which slice of which column is on screen.

    Qt-free on purpose: the widget reads and writes these fields, and the data
    layer is handed the mask they produce. Neither knows about the other.

    Attributes
    ----------
    axis_name : str or None
        Column being played back; ``None`` when the data carries nothing to play
        back and the transport is idle.
    mode : str
        One of :data:`MODES`.
    position : int
        Current step, ``0 <= position < n_steps``.
    n_steps : int
        How many slices the range is cut into.
    lo, hi : float
        Outer edges of the range, in the column's own units.
    is_index : bool
        Whether the axis is an integer index (see :func:`axis_geometry`).
    fps : int
        Steps per second while playing.
    direction : int
        ``+1`` playing forward, ``-1`` backward, ``0`` stopped.
    """

    axis_name: typing.Optional[str] = None
    mode: str = MODE_STACK
    position: int = 0
    n_steps: int = DEFAULT_N_STEPS
    lo: float = 0.0
    hi: float = 1.0
    is_index: bool = False
    fps: int = 10
    direction: int = 0

    #: ``(key, mask)`` of the last mask built. The mask is asked for about five
    #: times per redraw -- once each for the x, y and z values, once for the
    #: value mask and once for the histograms -- so building it per call means
    #: five passes over the column for one frame of playback.
    _cache: typing.Optional[typing.Tuple[tuple, np.ndarray]] = dataclasses.field(
        default=None, repr=False
    )

    # ---------------------------------------------------------------- setup

    @property
    def enabled(self) -> bool:
        """Whether an axis is set at all."""
        return self.axis_name is not None

    @property
    def gating(self) -> bool:
        """Whether the current state removes any points."""
        return self.enabled and self.mode in (MODE_WINDOW, MODE_INTEGRATE)

    def set_axis(
        self,
        name: typing.Optional[str],
        values: typing.Optional[np.ndarray] = None,
        n_steps: typing.Optional[int] = None,
    ) -> None:
        """Play back along `name`, taking its geometry from `values`.

        Parameters
        ----------
        name : str or None
            Column to play back; ``None`` disables playback.
        values : numpy.ndarray, optional
            The column's data, used for the bounds and to tell an index axis
            from a continuous one.
        n_steps : int, optional
            Requested step count for a continuous axis.
        """
        self._cache = None
        self.axis_name = name
        self.direction = 0
        self.position = 0
        if name is None:
            self.is_index = False
            self.lo, self.hi, self.n_steps = 0.0, 1.0, DEFAULT_N_STEPS
            return
        if values is None:
            self.lo, self.hi, self.is_index = 0.0, 1.0, False
            self.n_steps = max(1, int(n_steps or DEFAULT_N_STEPS))
            return
        self.lo, self.hi, self.n_steps, self.is_index = axis_geometry(values, n_steps)
        logging.info(
            "Playback axis %r: %s steps over [%g, %g]%s",
            name, self.n_steps, self.lo, self.hi, " (index)" if self.is_index else "",
        )

    def set_n_steps(self, n_steps: int) -> None:
        """Recut the range, keeping the current position proportional."""
        n_steps = max(1, int(n_steps))
        if n_steps == self.n_steps:
            return
        fraction = self.position / self.n_steps if self.n_steps else 0.0
        self.n_steps = n_steps
        self.position = min(n_steps - 1, max(0, int(fraction * n_steps)))
        self._cache = None

    def set_mode(self, mode: str) -> None:
        """Switch between window / integrate / stack."""
        if mode not in MODES:
            raise ValueError(f"mode must be one of {MODES}, got {mode!r}")
        if mode != self.mode:
            self.mode = mode
            self._cache = None
        if mode == MODE_STACK:
            self.direction = 0

    def set_position(self, position: int) -> None:
        """Jump to a step, clamped to the range."""
        position = min(self.n_steps - 1, max(0, int(position)))
        if position != self.position:
            self.position = position
            self._cache = None

    def step(self, delta: int) -> int:
        """Move `delta` steps, wrapping at both ends.

        Returns
        -------
        int
            The new position.
        """
        if self.n_steps > 0:
            self.set_position((self.position + delta) % self.n_steps)
        return self.position

    # ---------------------------------------------------------------- slice

    @property
    def edges(self) -> np.ndarray:
        """The ``n_steps + 1`` edges cutting the range."""
        return np.linspace(self.lo, self.hi, self.n_steps + 1)

    @property
    def bounds(self) -> typing.Tuple[float, float]:
        """``(start, end)`` of the current slice in the column's units.

        In ``integrate`` mode the slice starts at the beginning of the range,
        because that is what is being shown.
        """
        edges = self.edges
        upper = edges[min(self.position + 1, self.n_steps)]
        lower = self.lo if self.mode == MODE_INTEGRATE else edges[self.position]
        return float(lower), float(upper)

    @property
    def window(self) -> float:
        """Width of one step, in the column's units."""
        return (self.hi - self.lo) / self.n_steps if self.n_steps else 0.0

    def slice_key(self) -> typing.Optional[tuple]:
        """A comparable token that changes exactly when the mask would.

        ``None`` when nothing is gated. The mask itself never goes in a cache
        key -- an array-valued term makes the key expensive and, compared by
        identity, wrong -- so this carries the scalars it was built from.
        """
        if not self.gating:
            return None
        return (self.axis_name, self.mode, self.position, self.n_steps,
                self.lo, self.hi)

    def mask(self, data_source) -> typing.Optional[np.ndarray]:
        """Rows kept by the current slice, or ``None`` when nothing is gated.

        Parameters
        ----------
        data_source : ndxplorer.core.data_source.DataSource
            The table to gate.

        Returns
        -------
        numpy.ndarray or None
            Boolean array over the full table, ``True`` = **keep**. ``None``
            means "no gating", which every caller must handle -- it is the
            answer in ``stack`` mode and whenever the axis is missing from the
            data, which happens on the redraw between two files being loaded.
        """
        if not self.gating or data_source is None:
            return None
        try:
            index = data_source.column_index(self.axis_name)
        except Exception as exc:  # pragma: no cover - defensive
            logging.warning("Playback axis %r not found: %s", self.axis_name, exc)
            return None
        if index is None or index < 0:
            return None

        key = (index, self.mode, self.position, self.n_steps, self.lo, self.hi,
               getattr(data_source, "data_version", None))
        if self._cache is not None and self._cache[0] == key:
            return self._cache[1]

        values = data_source.column_view(index)
        if values is None:
            return None

        lower, upper = self.bounds
        last = self.position == self.n_steps - 1
        # The final step has to include the top edge, or the largest value in
        # the data -- the last frame, the last burst -- is in no step at all and
        # playing to the end shows an empty plot.
        above = values <= upper if last else values < upper
        mask = above if self.mode == MODE_INTEGRATE else (values >= lower) & above

        self._cache = (key, mask)
        return mask

    # ---------------------------------------------------------------- text

    def status_text(self) -> str:
        """One line describing what is on screen, for the panel's readout."""
        if not self.enabled:
            return "No column to play back"
        unit = unit_of(self.axis_name)
        unit = f" {unit}" if unit else ""
        # An index axis is reported as the integers it actually holds; its lo/hi
        # sit half a step outside them, which is what makes the interval test
        # exact and would read as "-0.5 to 5.5 frames".
        indexed = self.is_index and abs(self.window - 1.0) < 1e-9
        if self.mode == MODE_STACK:
            if indexed:
                first, last = int(round(self.lo + 0.5)), int(round(self.hi - 0.5))
                return f"All {self.n_steps} · {first}–{last}"
            return f"All of {self.lo:.4g}–{self.hi:.4g}{unit}"
        lower, upper = self.bounds
        step = f"{self.position + 1}/{self.n_steps}"
        if indexed:
            first = int(round(self.lo + 0.5))
            if self.mode == MODE_INTEGRATE:
                return f"{step} · {first}–{first + self.position}"
            return f"{step} · index {first + self.position}"
        width = "" if self.mode == MODE_INTEGRATE else f" · Δ {self.window:.4g}{unit}"
        return f"{step} · {lower:.4g}–{upper:.4g}{unit}{width}"
