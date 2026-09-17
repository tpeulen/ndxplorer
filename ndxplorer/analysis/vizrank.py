"""Rank candidate views of a table, best first, while the user watches.

A table with forty columns has 780 scatter plots in it, and ndX used to leave
the user to find the one that shows something. This module is the Qt-free half
of the answer: a *ranker* enumerates candidate configurations (a column, a pair
of columns), scores each one, and says how a scored configuration reads as a
table row. :class:`ndxplorer.ui.vizrank_panel.VizRankModel` runs a ranker in the
background and streams its rows into a table declared in a ``view.json`` and
drawn by emtk; clicking a row applies that configuration to the plot.

The design is Orange3's VizRank (Bioinformatics Lab, University of Ljubljana,
GPL-3.0; ``Orange/widgets/visualize/utils/vizrank.py``), reimplemented against
ndX's own seams. What crossed over:

* the subclass contract — :meth:`Ranker.state_count`,
  :meth:`Ranker.iterate_states`, :meth:`Ranker.compute_score` (**lower is
  better**, ``None`` skips the state) and :meth:`Ranker.row_for_state`;
* the run states and their button labels (:class:`RunState`), including the
  difference between *paused* and *hidden*;
* the worker loop (:func:`run_vizrank`): every state taken from the iterator is
  scored before the interruption check, so pausing and continuing loses none,
  and partial results are throttled so a cheap score cannot flood the GUI;
* the attribute and attribute-pair enumerations (:class:`AttrRanker`,
  :class:`AttrPairRanker`), in Orange's order.

Where it departs, and why:

* **The insert position is computed where the table lives, not in the worker.**
  Orange's worker bisects into a copy of the score list it was started with. A
  pause followed quickly by *Continue* can start the next run before the last
  batch of the previous one has arrived, so the copy is stale and rows land in
  the wrong place. Here the worker only produces ``(state, score)`` pairs and
  :class:`ScoreList` bisects on arrival, which cannot race.
* **Throttling is a clock comparison, not a ``threading.Timer`` per batch.**
* **Rows are plain values** (:class:`RankRow`), so every ranker — and its tests
  — is Qt-free; the panel turns them into the records its ``data_table``
  section reads.

The background-task machinery itself is **not** ported: ChiSurf already adopted
Orange's ``ConcurrentMixin`` as :func:`chisurf.gui.task.run_in_background`, and
the panel runs on that. :func:`run_vizrank` takes the handle that function
passes (``is_cancelled``, ``set_partial``, ``set_progress``).
"""

from __future__ import annotations

import logging
import time
from bisect import bisect_left
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Any, Callable, Iterable, Iterator, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

__all__ = [
    "RunState",
    "RankRow",
    "ScoreList",
    "Batch",
    "run_vizrank",
    "Ranker",
    "AttrRanker",
    "AttrPairRanker",
]


class RunState(IntEnum):
    """Where a ranking is in its life.

    ``Paused`` and ``Hidden`` both hold a half-finished ranking that can
    continue without starting over. They differ in what reopening the dialog
    does: a ranking the user *paused* stays paused, one that stopped because the
    dialog was *closed* resumes.
    """

    Invalid = 0      #: never valid for a live dialog; the initial value only
    Initialized = 1  #: has data; :meth:`VizRankDialog.prepare_run` not called yet
    Ready = 2        #: iterator built and the state count known; not started
    Running = 3      #: the worker is scoring
    Paused = 4       #: stopped by the user; Continue picks up where it was
    Hidden = 5       #: stopped because the dialog closed; reopening resumes
    Done = 6         #: every state scored

    def can_run(self) -> bool:
        """Whether *Start*/*Continue* may start a worker from this state."""
        return self in (RunState.Ready, RunState.Paused, RunState.Hidden)


#: The button caption for each state. ``Done`` disables the button.
BUTTON_LABELS = {
    RunState.Invalid: "Start",
    RunState.Initialized: "Start",
    RunState.Ready: "Start",
    RunState.Running: "Pause",
    RunState.Paused: "Continue",
    RunState.Hidden: "Continue",
    RunState.Done: "Finished",
}


@dataclass
class RankRow:
    """One scored configuration, as the table shows it.

    Attributes
    ----------
    cells : tuple of str
        Display text, one per column of :attr:`Ranker.header`.
    payload : object
        What applying the row means (column names, scales, …). Handed to the
        dialog's ``selectionChanged`` signal unchanged.
    bar : float or None
        Length of the in-cell bar drawn under the first cell, in ``[0, 1]``;
        ``None`` for no bar.
    sort_value : float
        Higher is better. What the table sorts the first column by, because the
        displayed text ("+0.41", "κ 0.83") does not sort numerically.
    tooltip : str
        Longer explanation shown on hover.
    bar_color : tuple or None
        ``(r, g, b)`` for the bar; ``None`` uses the default.
    value : float or None
        The number the score column shows (a signed ``r``, where
        :attr:`sort_value` is ``|r|``); ``sort_value`` when ``None``.
    """

    cells: Tuple[str, ...]
    payload: Any
    bar: Optional[float] = None
    sort_value: float = 0.0
    tooltip: str = ""
    bar_color: Optional[Tuple[int, int, int]] = None
    value: Optional[float] = None


class ScoreList:
    """Scores kept in ascending order; :meth:`insert` returns the row position.

    Orange keeps the same list inside its worker. It lives beside the table
    here — see the module docstring for the race that avoids.
    """

    def __init__(self, scores: Iterable = ()):
        self._scores: List[Any] = sorted(scores)

    def insert(self, score) -> int:
        """Add *score* and return the position it went to (ties go first)."""
        position = bisect_left(self._scores, score)
        self._scores.insert(position, score)
        return position

    def clear(self) -> None:
        """Forget every score."""
        self._scores.clear()

    def __len__(self) -> int:
        return len(self._scores)

    def __iter__(self):
        return iter(self._scores)

    def as_list(self) -> list:
        """A copy of the scores, ascending."""
        return list(self._scores)


@dataclass
class Batch:
    """What the worker hands the GUI thread in one partial result.

    Attributes
    ----------
    generation : int
        The run it belongs to. A batch from a superseded run is dropped on
        arrival instead of being inserted into the new run's table.
    items : list of (state, score)
        Every state scored since the previous batch, including the ones whose
        score was ``None`` — they are counted as completed, not shown.
    completed : int
        States scored so far in this ranking, across pauses.
    failed : int
        States in :attr:`items` whose scoring raised.
    """

    generation: int
    items: List[Tuple[Any, Any]] = field(default_factory=list)
    completed: int = 0
    failed: int = 0


def run_vizrank(
    compute_score: Callable[[Any], Any],
    states: Iterator,
    generation: int,
    completed: int,
    task,
    *,
    interval: float = 0.05,
    clock: Callable[[], float] = time.monotonic,
    progress: bool = True,
) -> Batch:
    """Score *states* one at a time, streaming batches through *task*.

    Runs in the worker thread. Every state taken from the iterator is scored
    before cancellation is checked, so the shared iterator stops exactly after
    the last state accounted for and *Continue* resumes with the next one.

    Parameters
    ----------
    compute_score : callable
        ``state -> score``; lower is better, ``None`` skips the state. A state
        whose scoring raises is skipped and counted in :attr:`Batch.failed` —
        one degenerate column pair must not end a ranking of seven hundred.
    states : iterator
        The states still to score. Consumed, not copied.
    generation : int
        Stamped on every batch; see :class:`Batch`.
    completed : int
        States already scored in earlier runs of this ranking, so progress
        continues rather than restarting at zero after a pause.
    task : object
        The handle :func:`chisurf.gui.task.run_in_background` passes:
        ``is_cancelled``, ``set_partial(value)``, ``set_progress(value)``.
    interval : float
        Minimum seconds between two partial results. Cheap scores (a
        correlation) would otherwise post one event per state and make the GUI
        less responsive than a frozen one.
    clock : callable
        Time source; injectable so the throttle is testable.
    progress : bool
        Report :attr:`Batch.completed` through ``task.set_progress``. The dialog
        passes ``False`` and counts on arrival instead, because a run continued
        after a pause may start before the previous run's last batch has been
        counted.

    Returns
    -------
    Batch
        The last batch (possibly empty), also delivered through
        ``set_partial`` so nothing scored is lost when the run was cancelled.
    """
    batch = Batch(generation=generation, completed=completed)
    last_emit = clock()
    for state in states:
        try:
            score = compute_score(state)
        except Exception:  # noqa: BLE001 - one bad state must not end the run
            logger.debug("vizrank: scoring %r failed", state, exc_info=True)
            score = None
            batch.failed += 1
        batch.items.append((state, score))
        batch.completed += 1
        now = clock()
        if now - last_emit >= interval:
            task.set_partial(batch)
            if progress:
                task.set_progress(batch.completed)
            batch = Batch(generation=generation, completed=batch.completed)
            last_emit = now
        if task.is_cancelled:
            break
    task.set_partial(batch)
    if progress:
        task.set_progress(batch.completed)
    return batch


class Ranker:
    """What a ranking needs to know; subclasses fill in the scoring.

    The constructor should only *store* what the ranking needs: a ranker is
    built whenever the data or the settings change, whether or not anyone runs
    it. The work belongs in :meth:`prepare`, which the dialog calls once before
    the first state is scored (and which may run in the worker thread).
    """

    #: Column captions, first one being the score.
    header: Tuple[str, ...] = ("Score",)

    def prepare(self) -> None:
        """Do the one-off work (subsampling, transforms) before scoring."""

    def state_count(self) -> int:
        """How many states :meth:`iterate_states` yields; for the progress bar."""
        return 1

    def iterate_states(self) -> Iterator:
        """Yield every candidate configuration."""
        raise NotImplementedError

    def compute_score(self, state) -> Any:
        """Score one state. Lower is better; ``None`` leaves it out of the table."""
        raise NotImplementedError

    def row_for_state(self, score, state) -> RankRow:
        """How a scored state reads in the table."""
        raise NotImplementedError

    def matches(self, payload, wanted) -> bool:
        """Whether a row's *payload* is the configuration *wanted*.

        Used to select the row that corresponds to what the user set by hand.
        """
        return payload == wanted


class AttrRanker(Ranker):
    """Rank single columns. A state is an index into :attr:`attr_order`."""

    header = ("Score", "Parameter")

    def __init__(self, attrs: Sequence[str]):
        self.attrs: List[str] = list(attrs)
        self._attr_order: Optional[List[str]] = None

    @property
    def attr_order(self) -> List[str]:
        """The columns in the order states refer to them (computed once)."""
        if self._attr_order is None:
            self._attr_order = list(self.score_attributes())
        return self._attr_order

    def score_attributes(self) -> Sequence[str]:
        """Order the columns so promising ones are scored first.

        States are indices into this order, so the table fills with good rows
        early. The default keeps the given order.
        """
        return self.attrs

    def state_count(self) -> int:
        return len(self.attrs)

    def iterate_states(self) -> Iterator[int]:
        return iter(range(len(self.attr_order)))


class AttrPairRanker(AttrRanker):
    """Rank pairs of columns. A state is ``(j, i)`` with ``j < i``.

    The order is Orange's: every pair among the first ``i + 1`` columns before
    any pair involving column ``i + 1``, which is what makes a good
    :meth:`score_attributes` order pay off early.
    """

    header = ("Score", "x", "y")

    def state_count(self) -> int:
        n = len(self.attrs)
        return n * (n - 1) // 2

    def iterate_states(self) -> Iterator[Tuple[int, int]]:
        n = len(self.attr_order)
        return ((j, i) for i in range(n) for j in range(i))
