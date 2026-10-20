"""The ranking machinery: enumeration, the scoring loop and the panel model.

Expectations come from the behaviour ndX specifies for a ranking -- a
prefix-complete pair order, stable insertion, nothing lost across a pause --
checked with small rankers whose scores are known.
"""

from __future__ import annotations

import itertools
import random

import pytest
from ndxplorer.analysis.vizrank import (
    PairRanker,
    RankRow,
    RunState,
    ScoreBatch,
    StateTotal,
    insertion_index,
    pair_indices,
    score_states,
)
from ndxplorer.analysis.vizrank_model import VizRankModel, load_spec


# ---- helpers ------------------------------------------------------------------------------
class Handle:
    """A runner handle that collects partials; cancels after *stop_after* polls."""

    def __init__(self, stop_after=None):
        self.partials = []
        self.polls = 0
        self.stop_after = stop_after

    @property
    def is_cancelled(self):
        self.polls += 1
        return self.stop_after is not None and self.polls >= self.stop_after

    def set_partial(self, value):
        self.partials.append(value)

    def set_progress(self, _value):
        pass

    def set_text(self, _text):
        pass


class Counting(PairRanker):
    """Pairs of ``c0 .. c{m-1}``; the score is a fixed function of the pair."""

    def __init__(self, m=5, score=None, fail=()):
        super().__init__()
        self.m = m
        self.fail = set(fail)
        self.score = score or (lambda a, b: (abs(hash((a, b))) % 97) / 97.0)
        self.prepared = 0

    def prepare(self):
        super().prepare()
        self.prepared += 1

    def select_columns(self):
        return [f"c{i}" for i in range(self.m)]

    def compute_score(self, state):
        if state in self.fail:
            raise RuntimeError("bad view")
        value = self.score(*state)
        return None if value is None else (value,)

    def row_for_state(self, score, state):
        return RankRow((f"{score[0]:.3f}",) + tuple(state), {"x": state[0], "y": state[1]},
                       bar=score[0], sort_value=-score[0])

    @property
    def header(self):
        return ("Score", "x", "y")


class Model(VizRankModel):
    def __init__(self, ranker_factory, settings=lambda: 1, **kw):
        super().__init__(**kw)
        self.factory = ranker_factory
        self.settings = settings

    def make_ranker(self):
        return self.factory()

    def current_settings(self):
        return self.settings()


class SlicedRunner:
    """Calls the work in slices of *n* states (the handle cancels after n polls),
    like the frame loop's time slices, pumped by hand."""

    def __init__(self, n=3):
        self.n = n
        self.tasks = []

    def __call__(self, _owner, _text, func, *, args=(), on_partial=None, on_result=None,
                 on_error=None, on_done=None, **_kw):
        runner = self

        class Task:
            cancelled = False
            is_running = True

            def cancel(self):
                self.cancelled = True

            def pump(self):
                if self.cancelled:                   # a cancelled task runs no more slices
                    self.is_running = False
                    on_done()
                    return True
                handle = Handle(stop_after=runner.n)
                result = func(*args, handle)
                for value in handle.partials:
                    on_partial(value)
                sliced = handle.polls >= runner.n
                if self.cancelled or not sliced:
                    self.is_running = False
                    if not self.cancelled:
                        on_result(result)
                    on_done()
                    return True
                return False

        task = Task()
        self.tasks.append(task)
        return task

    def run_all(self, limit=10000):
        for _ in range(limit):
            if not self.tasks:
                return
            task = self.tasks[0]
            if task.pump():
                self.tasks.pop(0)


# ---- enumeration ----------------------------------------------------------------------------
def test_pairs_are_prefix_complete():
    assert list(pair_indices(4)) == [(0, 1), (0, 2), (1, 2), (0, 3), (1, 3), (2, 3)]
    assert list(pair_indices(0)) == [] and list(pair_indices(1)) == []
    for m in range(2, 12):
        pairs = list(pair_indices(m))
        assert len(pairs) == m * (m - 1) // 2 == len(set(pairs))
        for p in range(2, m + 1):
            first = p * (p - 1) // 2
            assert all(max(pair) < p for pair in pairs[:first])


def test_run_states_that_may_run():
    assert {s for s in RunState if s.can_run()} == {RunState.Ready, RunState.Paused,
                                                    RunState.Hidden}


def test_equal_scores_keep_their_arrival_order():
    keys, positions = [], []
    for score in [0.5, 1 / 3, 0.25, 2 / 3, 0.5, 0.75]:
        position = insertion_index(keys, score)
        keys.insert(position, score)
        positions.append(position)
    assert positions == [0, 0, 0, 3, 3, 5]


# ---- the scoring loop -------------------------------------------------------------------------
def test_a_state_without_a_view_is_counted_but_has_no_row():
    handle = Handle()
    count = score_states(iter(range(10)), lambda s: None if s == 3 else s, handle, 7)
    items = [item for batch in handle.partials for item in batch.items]
    assert count == 10 and len(items) == 10
    assert sum(score is not None for _state, score in items) == 9
    assert all(batch.generation == 7 for batch in handle.partials)


def test_cancelling_never_loses_or_repeats_a_state():
    states = iter(range(10))
    handle = Handle(stop_after=1)
    assert score_states(states, lambda s: s, handle, 0) == 1
    assert [i for b in handle.partials for i in b.items] == [(0, 0)]
    assert next(states) == 1


def test_a_failing_state_is_skipped_and_counted():
    def score(state):
        if state == 2:
            raise ValueError("no")
        return state

    handle = Handle()
    score_states(iter(range(5)), score, handle, 0)
    assert sum(b.failed for b in handle.partials) == 1
    assert [s for b in handle.partials for s, v in b.items if v is not None] == [0, 1, 3, 4]


def test_batches_are_throttled_and_complete():
    now = [0.0]

    def clock():
        return now[0]

    def slow(state):
        now[0] += 0.010
        return state

    handle = Handle()
    score_states(iter(range(100)), slow, handle, 0, interval=0.05, clock=clock)
    assert 15 <= len(handle.partials) <= 25
    assert sum(len(b.items) for b in handle.partials) == 100


# ---- the panel model ---------------------------------------------------------------------------
def test_without_a_runner_the_model_ranks_inline():
    applied = []
    model = Model(lambda: Counting(5), on_apply=applied.append)
    assert model.run_state == RunState.Initialized and model.rows == []
    assert model.status_text() == "Press Start to rank every view."
    model.start()
    assert model.run_state == RunState.Done and model.completed == 10 and len(model.rows) == 10
    assert model.start_label == "Finished"
    assert model.status_text() == "10/10 scored (100 %) · finished"
    scores = [r["score"] for r in model.rows]
    assert scores == sorted(scores, reverse=True), "best first"
    assert applied == [model.rows[0]["payload"]]
    assert model.select_request == model.rows[0]["key"]


def test_records_carry_the_cells_and_a_key_per_payload():
    model = Model(lambda: Counting(4))
    model.start()
    row = model.rows[0]
    assert set(row) >= {"score", "key", "note", "payload", "name0", "name1"}
    assert row["key"] == "|".join(f"{k}={row['payload'][k]}" for k in sorted(row["payload"]))
    assert len({r["key"] for r in model.rows}) == len(model.rows)
    columns = model.ranked_columns()
    assert [c["key"] for c in columns] == ["score", "name0", "name1"]
    assert columns[0]["display"] == "bar" and columns[0]["format"] == "%.3f"


def test_the_default_columns_before_a_run():
    columns = VizRankModel().ranked_columns()
    assert len(columns) == 1 and columns[0]["title"] == "Score" and columns[0]["range"] == [0, 1]


def test_failures_are_reported_in_the_status():
    model = Model(lambda: Counting(4, fail={("c0", "c2")}))
    model.start()
    assert model.failed == 1 and model.completed == 6 and len(model.rows) == 5
    assert model.status_text().endswith("· 1 failed")


def test_a_ranker_that_cannot_be_made_shows_why():
    def broken():
        raise RuntimeError("no table")

    model = Model(broken)
    model.start()
    assert model.error == "Cannot rank: no table" and model.status_text() == model.error
    assert model._run is None


@pytest.mark.parametrize("seed", range(5))
def test_pausing_anywhere_gives_the_uninterrupted_ranking(seed):
    reference = Model(lambda: Counting(7))
    reference.start()
    rng = random.Random(seed)
    runner = SlicedRunner(n=rng.randint(1, 4))
    deferred = []
    model = Model(lambda: Counting(7), runner=runner, defer=deferred.append)
    model.start()
    for _ in range(200):
        if model.run_state == RunState.Done:
            break
        if rng.random() < 0.3 and model.run_state == RunState.Running:
            model.pause()
            assert model.start_label == "Continue"
            model.start()                            # previous slice still running: deferred
        if runner.tasks:
            runner.tasks[0].pump() and runner.tasks.pop(0)
        while deferred:
            deferred.pop(0)()
    assert model.run_state == RunState.Done
    assert [(r["key"], r["score"]) for r in model.rows] == \
        [(r["key"], r["score"]) for r in reference.rows]
    assert model.completed == 21


def test_closing_hides_and_reopening_resumes_but_a_pause_stays():
    runner = SlicedRunner(n=2)
    model = Model(lambda: Counting(6), runner=runner)
    model.start()
    runner.tasks[0].pump()
    model.pause_computation(RunState.Hidden)
    assert model.run_state == RunState.Hidden
    runner.run_all()
    model.dialog_reopened()
    assert model.run_state == RunState.Running
    runner.tasks[0].pump()
    model.pause()
    runner.run_all()
    model.dialog_reopened()
    assert model.run_state == RunState.Paused
    model.start()
    runner.run_all()
    assert model.run_state == RunState.Done
    model.dialog_reopened()
    assert model.run_state == RunState.Done


def test_a_settings_change_pauses_and_offers_a_restart():
    value = [1]
    runner = SlicedRunner(n=2)
    model = Model(lambda: Counting(5), settings=lambda: value[0], runner=runner)
    model.start()
    runner.tasks[0].pump()
    value[0] = 2
    model.settings_changed()
    assert model.run_state == RunState.Paused
    assert model.restart_offered() and model.start_label == "Restart with new settings"
    generation = model._run.generation
    model.start()
    assert model._run.generation == generation + 1 and model._run.settings == 2
    runner.run_all()
    assert model.run_state == RunState.Done and model.completed == 10


def test_batches_of_a_superseded_ranking_are_dropped():
    model = Model(lambda: Counting(4))
    model.start()
    old = model._run.generation
    model._receive(old - 1, ScoreBatch(old - 1, [(("c0", "c1"), (0.1,))]))
    model._receive(old - 1, StateTotal(old - 1, 99))
    assert model.completed == 6 and model._run.total == 6


def test_auto_select_marks_without_applying():
    applied = []
    model = Model(lambda: Counting(4), on_apply=applied.append)
    model.start()
    applied.clear()
    model.auto_select({"x": "c3", "y": "c1"})          # transposed: the same view
    record = next(r for r in model.rows if r["key"] == model.select_request)
    assert {record["payload"]["x"], record["payload"]["y"]} == {"c1", "c3"}
    assert applied == []
    model.auto_select({"x": "c0", "y": "nothing"})
    assert model.select_request is None
    model.apply_row(None)
    model.apply_row(model.rows[1])
    assert applied == [model.rows[1]["payload"]]


def test_a_failing_listener_never_breaks_a_run():
    def bad():
        raise RuntimeError("listener")

    model = Model(lambda: Counting(4), on_change=bad)
    model.start()
    assert model.run_state == RunState.Done


def test_a_whole_ranking_failing_pauses_with_the_reason():
    class Broken(Counting):
        def state_count(self):
            raise RuntimeError("columns")

    model = Model(lambda: Broken(4))
    model.start()
    assert model.error == "Ranking failed: columns" and model.run_state == RunState.Paused


def test_enabled_buttons_follow_the_state():
    runner = SlicedRunner(n=1)
    model = Model(lambda: Counting(4), runner=runner)
    assert model.enabled("start") and not model.enabled("pause")
    model.start()
    assert not model.enabled("start") and model.enabled("pause") and model.progress == 0
    runner.tasks[0].pump()
    assert model._run.total == 6 and model.progress == round(100 / 6)
    model.shutdown()
    runner.run_all()
    assert model.enabled("anything")


def test_the_progress_host_sets_the_text():
    model = VizRankModel()
    progress = model.begin_task("ordering parameters")
    assert model.progress_text == "ordering parameters"
    progress.finish()
    assert model.progress_text == ""


def test_the_spec_loads():
    spec = load_spec()
    keys = [s.get("key") for s in spec["sections"]]
    assert "data_table" in keys


def test_scores_are_compared_only_as_far_as_needed():
    """Keys that tie on their leading numbers never compare their payload objects."""
    arrival = itertools.count()

    class Opaque:
        def __lt__(self, other):
            raise AssertionError("compared")

    keys = []
    for value in [0.2, 0.1, 0.2, 0.2]:
        key = (value, next(arrival), Opaque())
        keys.insert(insertion_index(keys, key), key)
    assert [k[1] for k in keys] == [1, 0, 2, 3]
