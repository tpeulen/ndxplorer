"""Ranking candidate views: enumerate, score, keep the best first.

A *ranking* walks through candidate configurations of a plot -- one column,
or a pair of columns -- gives each a score and keeps the scored candidates
sorted while scoring runs, so a table of views fills from the top while the
rest is still being computed. The idea of ranking projections of a data set by
a quality measure and showing the best first is that of VizRank (Leban, Zupan,
Vidmar & Bratko 2006, doi:10.1007/s10618-005-0031-5); what makes a view good
is decided by the concrete rankers in
:mod:`ndxplorer.analysis.projection_scores`.

This module is the GUI-free half of the machinery:

* :class:`RunState` -- where a ranking stands (prepared, running, paused by
  the user, stopped because its window closed, finished);
* :class:`RankRow` -- how one scored candidate appears in the table;
* :class:`Ranker`, :class:`ColumnRanker`, :class:`PairRanker` -- the contract
  a concrete ranker fulfils, with the enumeration of single columns and of
  column pairs;
* :func:`score_states` -- the cooperative scoring loop that hands its results
  over in throttled batches, and :func:`insertion_index` -- where a newly
  scored row goes on the receiving side.

Conventions: a *state* is a tuple of column names; a *score* is any totally
ordered value (usually a tuple compared lexicographically) where **lower is
better**; ``None`` means "no view to show" -- the state is counted as scored
but gets no row.
"""

from __future__ import annotations

import bisect
import enum
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterator, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)

__all__ = [
    "RunState",
    "RankRow",
    "ScoreBatch",
    "StateTotal",
    "Ranker",
    "ColumnRanker",
    "PairRanker",
    "pair_indices",
    "score_states",
    "insertion_index",
    "BATCH_INTERVAL",
]

#: Seconds between two batches handed to the GUI side.
BATCH_INTERVAL = 0.05


class RunState(enum.IntEnum):
    """Where a ranking stands.

    ``Initialized``
        There is data, and no ranking has been prepared yet.
    ``Ready``
        A ranking is prepared and has not started.
    ``Running``
        Scoring is in progress.
    ``Paused``
        The user stopped it; reopening the window does not resume it.
    ``Hidden``
        It stopped because its window closed; reopening resumes it.
    ``Done``
        Every state has been scored.
    ``NoData``
        Nothing to rank.
    """

    NoData = 0
    Initialized = 1
    Ready = 2
    Running = 3
    Paused = 4
    Hidden = 5
    Done = 6

    def can_run(self) -> bool:
        """Whether scoring may (re)start from here: a prepared, paused or hidden ranking."""
        return self in (RunState.Ready, RunState.Paused, RunState.Hidden)


@dataclass(frozen=True)
class RankRow:
    """One scored state as the ranking table shows it.

    Attributes
    ----------
    cells : tuple of str
        Display text: the score first, then the column labels, then any extra
        cells (an island count).
    payload : dict
        What choosing the row sets (axis names and scales).
    bar : float or None
        Bar length in ``[0, 1]``.
    sort_value : float
        The row's number, higher is better.
    tooltip : str
        What the score means for this row, in words.
    bar_color : tuple of int or None
        RGB of the bar, when the row has its own.
    value : float or None
        The number the score column shows when it differs from
        :attr:`sort_value` (a signed correlation whose magnitude ranks).
    """

    cells: Tuple[str, ...]
    payload: Dict[str, Any] = field(default_factory=dict)
    bar: Optional[float] = None
    sort_value: float = 0.0
    tooltip: str = ""
    bar_color: Optional[Tuple[int, int, int]] = None
    value: Optional[float] = None


@dataclass
class ScoreBatch:
    """Scored states on their way to the GUI side.

    ``items`` holds ``(state, score)`` pairs in scoring order; a state whose
    scoring raised appears with score ``None`` and is also counted in
    ``failed``. ``generation`` names the ranking the batch belongs to, so a
    batch of a superseded ranking can be dropped.
    """

    generation: int
    items: List[Tuple[Tuple[str, ...], Any]] = field(default_factory=list)
    failed: int = 0


@dataclass
class StateTotal:
    """How many states the ranking ``generation`` will score (known once its
    columns are chosen)."""

    generation: int
    total: int


def pair_indices(m: int) -> Iterator[Tuple[int, int]]:
    """Every unordered pair of ``m`` positions once, as ``(j, i)`` with ``j < i``.

    The order is *prefix-complete*: all pairs among the first ``p`` positions
    come before any pair that involves position ``p``, so when the most
    promising columns are put first the top of the ranking fills early. For
    ``m = 4``: ``(0,1), (0,2), (1,2), (0,3), (1,3), (2,3)``. There are
    ``m (m - 1) / 2`` pairs, none for ``m < 2``.
    """
    for i in range(1, m):
        for j in range(i):
            yield (j, i)


def insertion_index(keys: Sequence[Any], key: Any) -> int:
    """Where *key* goes in the ascending list *keys* so that equal keys keep
    the order they arrived in (after every key equal to it)."""
    return bisect.bisect_right(keys, key)


def score_states(states: Iterator, score: Callable[[Any], Any], handle, generation: int,
                 interval: float = BATCH_INTERVAL,
                 clock: Callable[[], float] = time.monotonic) -> int:
    """Score states from the shared iterator *states* until it ends or the run is cancelled.

    Each state is scored and accounted for **before** ``handle.is_cancelled``
    is polled, so stopping never loses or repeats a state: a later call with
    the same iterator continues with the next one. A state whose scoring
    raises is passed on with score ``None`` and counted as failed; the
    ranking goes on. Results reach ``handle.set_partial`` as
    :class:`ScoreBatch` objects at most once per *interval* seconds of
    *clock*, and whatever is still held is delivered before returning.

    Parameters
    ----------
    states : iterator
        The ranking's enumeration, shared across calls.
    score : callable
        ``score(state)`` -> score or ``None``.
    handle : object
        The runner's handle (``is_cancelled``, ``set_partial``).
    generation : int
        The ranking the batches belong to.
    interval : float
        Minimum seconds between two batches.
    clock : callable
        Monotonic time source.

    Returns
    -------
    int
        States scored by this call.
    """
    batch = ScoreBatch(generation)
    last = clock()
    count = 0
    try:
        for state in states:
            try:
                value = score(state)
            except Exception:  # noqa: BLE001 - one bad view must not end the ranking
                logger.debug("scoring %r failed", state, exc_info=True)
                value = None
                batch.failed += 1
            batch.items.append((state, value))
            count += 1
            now = clock()
            if now - last >= interval:
                handle.set_partial(batch)
                batch = ScoreBatch(generation)
                last = now
            if handle.is_cancelled:
                break
    finally:
        if batch.items or batch.failed:
            handle.set_partial(batch)
    return count


class Ranker:
    """What a concrete ranking provides to the panel model.

    The life cycle: :meth:`prepare` on the GUI thread (it may read the live
    table); then, in the worker, :meth:`state_count` and
    :meth:`iterate_states` (the first of them chooses the columns, once),
    :meth:`compute_score` per state; back on the GUI side
    :meth:`row_for_state` turns a score into a :class:`RankRow`.

    Subclasses implement :meth:`select_columns` and :meth:`compute_score`,
    :meth:`row_for_state`, and set :attr:`header` and :attr:`score_span`.
    """

    #: Columns per state.
    dimension = 1

    def __init__(self) -> None:
        self.attrs: List[str] = []
        self._columns_ready = False

    # ---- hooks -------------------------------------------------------------------------
    def prepare(self) -> None:
        """Get ready for a run on the GUI thread; forget any earlier column choice."""
        self.attrs = []
        self._columns_ready = False

    def select_columns(self) -> List[str]:
        """The columns to rank, in enumeration order (called once per run, in the worker)."""
        raise NotImplementedError

    def compute_score(self, state: Tuple[str, ...]) -> Any:
        """The score of *state* (lower is better), or ``None`` to leave it out."""
        raise NotImplementedError

    def row_for_state(self, score: Any, state: Tuple[str, ...]) -> RankRow:
        """How the scored *state* appears in the table."""
        raise NotImplementedError

    def matches(self, payload: dict, wanted: dict) -> bool:
        """Whether a row's *payload* shows the view *wanted* (a hand-picked one)."""
        return all(payload.get(k) == v for k, v in wanted.items())

    @property
    def header(self) -> Tuple[str, ...]:
        """Column titles of the table: the score's name, then one per cell."""
        return ("Score",)

    @property
    def score_span(self) -> Tuple[float, float]:
        """The range the score column's bar spans."""
        return (0.0, 1.0)

    # ---- enumeration -------------------------------------------------------------------
    def _ensure_columns(self) -> None:
        if not self._columns_ready:
            self.attrs = list(self.select_columns())
            self._columns_ready = True

    def state_count(self) -> int:
        """How many states the ranking scores."""
        raise NotImplementedError

    def iterate_states(self) -> Iterator[Tuple[str, ...]]:
        """The states in scoring order."""
        raise NotImplementedError


class ColumnRanker(Ranker):
    """A ranker of single columns: one state per selected column, in selection order."""

    dimension = 1

    def state_count(self) -> int:
        self._ensure_columns()
        return len(self.attrs)

    def iterate_states(self) -> Iterator[Tuple[str, ...]]:
        self._ensure_columns()
        return iter([(name,) for name in self.attrs])

    def matches(self, payload: dict, wanted: dict) -> bool:
        return payload.get("z") == wanted.get("z")


class PairRanker(Ranker):
    """A ranker of column pairs, enumerated prefix-complete (:func:`pair_indices`)
    over the selected columns in the order :meth:`select_columns` returns."""

    dimension = 2

    def state_count(self) -> int:
        self._ensure_columns()
        m = len(self.attrs)
        return m * (m - 1) // 2

    def iterate_states(self) -> Iterator[Tuple[str, ...]]:
        self._ensure_columns()
        names = list(self.attrs)
        return ((names[j], names[i]) for j, i in pair_indices(len(names)))

    def matches(self, payload: dict, wanted: dict) -> bool:
        """A transposed view is the same view: compare the sets of axis names."""
        return {payload.get("x"), payload.get("y")} == {wanted.get("x"), wanted.get("y")}

