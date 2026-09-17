"""The ranking framework, without Qt: the worker loop, the ordering, the states.

Where a test carries Orange3's own expectation it says so; those numbers were
read from ``Orange/widgets/visualize/utils/tests/test_vizrank.py`` and
``Orange/widgets/visualize/tests/test_vizrankdialog.py`` and must not drift.
"""

from __future__ import annotations

import itertools

import pytest

from ndxplorer.analysis.vizrank import (
    BUTTON_LABELS,
    AttrPairRanker,
    AttrRanker,
    Batch,
    RunState,
    ScoreList,
    run_vizrank,
)


class FakeTask:
    """The handle ``run_in_background`` passes, recording what it is told."""

    def __init__(self, interrupt_after=None):
        self.partials = []
        self.progress = []
        self.checks = 0
        self.interrupt_after = interrupt_after

    @property
    def is_cancelled(self):
        self.checks += 1
        return self.interrupt_after is not None and self.checks > self.interrupt_after

    def set_partial(self, value):
        self.partials.append(value)

    def set_progress(self, value):
        self.progress.append(value)


def orange_score(state):
    """Orange's MockDialog.compute_score: state 3 is skipped."""
    return 10 * (state % 2) + state // 2 if state != 3 else None


def insert_all(task):
    """What the dialog does with the batches: bisect every score in on arrival."""
    scores = ScoreList()
    positions = []
    completed = 0
    for batch in task.partials:
        for _state, score in batch.items:
            completed += 1
            if score is not None:
                positions.append(scores.insert(score))
    return scores, positions, completed


def test_running_orders_every_score_and_counts_the_skipped_state():
    """Orange ``test_running``: scores [0,1,2,3,4,10,12,13,14], 10 completed."""
    task = FakeTask()
    run_vizrank(orange_score, iter(range(10)), generation=1, completed=0, task=task)
    scores, _, completed = insert_all(task)
    assert scores.as_list() == [0, 1, 2, 3, 4, 10, 12, 13, 14]
    assert completed == 10
    assert task.progress[-1] == 10


def test_interruption_scores_the_state_it_took_first():
    """Orange ``test_interruption``: cancelled at once still scores one state."""
    task = FakeTask(interrupt_after=0)
    states = iter(range(10))
    run_vizrank(orange_score, states, generation=1, completed=0, task=task)
    scores, _, completed = insert_all(task)
    assert scores.as_list() == [0]
    assert completed == 1
    # The shared iterator resumes exactly after the scored state.
    assert next(states) == 1


def test_pause_and_continue_lose_no_state_and_order_matches_one_run():
    """Orange ``test_run_vizrank_interrupt``: two runs over one iterator equal one run."""

    def score(pair):
        return (pair[0] + 1) / (pair[1] + 1)

    pairs = [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)]
    iterator = iter(pairs)
    first = FakeTask(interrupt_after=2)
    run_vizrank(score, iterator, generation=1, completed=0, task=first)
    second = FakeTask()
    run_vizrank(score, iterator, generation=1, completed=3, task=second)

    scores = ScoreList()
    seen = []
    for batch in first.partials + second.partials:
        for state, value in batch.items:
            seen.append(state)
            scores.insert(value)
    assert seen == pairs
    assert scores.as_list() == sorted(score(p) for p in pairs)
    assert second.progress[-1] == 6


def test_positions_are_where_the_rows_go():
    """Orange ``test_run_vizrank``: insert positions [0, 0, 0, 3, 2, 5]."""

    def score(pair):
        return (pair[0] + 1) / (pair[1] + 1)

    pairs = [(0, 1), (0, 2), (0, 3), (1, 2), (1, 3), (2, 3)]
    task = FakeTask()
    run_vizrank(score, iter(pairs), generation=1, completed=0, task=task)
    _, positions, _ = insert_all(task)
    assert positions == [0, 0, 0, 3, 2, 5]


def test_partial_results_are_throttled_by_the_clock():
    """A cheap score must not post one event per state."""
    ticks = itertools.count()
    clock = lambda: next(ticks) * 0.01  # noqa: E731 - 10 ms per state
    task = FakeTask()
    run_vizrank(lambda s: s, iter(range(100)), 1, 0, task, interval=0.05, clock=clock)
    assert 15 <= len(task.partials) <= 25
    assert sum(len(b.items) for b in task.partials) == 100
    assert all(isinstance(b, Batch) and b.generation == 1 for b in task.partials)


def test_a_state_that_raises_is_skipped_and_counted():
    def score(state):
        if state == 2:
            raise ZeroDivisionError("degenerate pair")
        return state

    task = FakeTask()
    run_vizrank(score, iter(range(5)), 1, 0, task)
    scores, _, completed = insert_all(task)
    assert scores.as_list() == [0, 1, 3, 4]
    assert completed == 5
    assert sum(b.failed for b in task.partials) == 1


def test_progress_can_be_left_to_the_receiver():
    task = FakeTask()
    run_vizrank(lambda s: s, iter(range(3)), 1, 0, task, progress=False)
    assert task.progress == []


def test_run_states_and_labels():
    assert [s for s in RunState if s.can_run()] == [RunState.Ready, RunState.Paused, RunState.Hidden]
    assert BUTTON_LABELS[RunState.Running] == "Pause"
    assert BUTTON_LABELS[RunState.Paused] == BUTTON_LABELS[RunState.Hidden] == "Continue"
    assert BUTTON_LABELS[RunState.Done] == "Finished"


def test_pair_states_follow_orange_order():
    """Orange ``TestVizRankDialogAttrPair.test_count_and_generator``."""
    ranker = AttrPairRanker(list("abcde"))
    assert ranker.state_count() == 5 * 4 // 2
    assert list(ranker.iterate_states()) == [
        (0, 1), (0, 2), (1, 2), (0, 3), (1, 3), (2, 3), (0, 4), (1, 4), (2, 4), (3, 4)]


def test_attr_order_is_computed_once():
    """Orange ``test_attr_order``: the heuristic runs once and is cached."""

    class Reversed(AttrRanker):
        calls = 0

        def score_attributes(self):
            Reversed.calls += 1
            return self.attrs[::-1]

    ranker = Reversed(list("abc"))
    assert ranker.attr_order == ["c", "b", "a"]
    assert ranker.attr_order == ["c", "b", "a"]
    assert Reversed.calls == 1
    assert list(ranker.iterate_states()) == [0, 1, 2]


def test_ties_go_first_like_bisect_left():
    scores = ScoreList([1, 2, 2, 3])
    assert scores.insert(2) == 1
    assert len(scores) == 5


@pytest.mark.parametrize("n", [0, 1])
def test_too_few_columns_have_no_pairs(n):
    ranker = AttrPairRanker(list("ab")[:n])
    assert ranker.state_count() == 0
    assert list(ranker.iterate_states()) == []
