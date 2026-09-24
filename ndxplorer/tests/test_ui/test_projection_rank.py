"""*Find informative projections…*: the ranking model, and the panel inside ndX.

The model is driven first with an inline runner that behaves like
``run_in_background`` (callbacks in order, cancellation seen by the worker), so
the state machine -- streaming, pause/continue, restart on a settings change,
closing and reopening -- is tested without threads. Then the real thing: an ndX
window with a table whose informative view is planted, the ranking run on
ChiSurf's background task, the emtk panel clicked, the axes applied.
"""

from __future__ import annotations

import time

import numpy as np
import pytest
from qtpy import QtWidgets

from ndxplorer.analysis.vizrank import AttrPairRanker, RankRow, RunState
from ndxplorer.analysis.vizrank_model import VizRankModel, load_spec


# ---- the model, without threads --------------------------------------------------------


class InlineTask:
    """What ``run_in_background`` returns and passes, run synchronously."""

    def __init__(self, cancel_after=None):
        self.cancelled = False
        self.cancel_after = cancel_after
        self.is_running = False
        self.progress = None
        self.checks = 0

    # the handle side
    @property
    def is_cancelled(self):
        self.checks += 1
        if self.cancel_after is not None and self.checks > self.cancel_after:
            self.cancelled = True
        return self.cancelled

    def set_text(self, _text):
        pass

    def set_progress(self, _value):
        pass

    def set_partial(self, value):
        self.on_partial(value)

    # the task side
    def cancel(self):
        self.cancelled = True


def inline_runner(cancel_after=None):
    tasks = []

    def run(parent, text, func, *, args=(), on_partial=None, on_result=None, on_error=None,
            on_done=None, **_kw):
        task = InlineTask(cancel_after)
        task.on_partial = on_partial
        tasks.append(task)
        try:
            result = func(*args, task)
        except Exception as exc:  # noqa: BLE001
            on_error(exc)
        else:
            if not task.cancelled:
                on_result(result)
        on_done()
        return task

    run.tasks = tasks
    return run


class PairModel(VizRankModel):
    """Ranks pairs of five names; the score is planted."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.bonus = 0.0

    def current_settings(self):
        return self.bonus

    def make_ranker(self):
        bonus = self.bonus

        class Ranker(AttrPairRanker):
            def compute_score(self, state):
                j, i = state
                return -(10 * j + i) - bonus if (j, i) != (0, 3) else None

            def row_for_state(self, score, state):
                x, y = self.attr_order[state[0]], self.attr_order[state[1]]
                return RankRow((f"{-score:.1f}", x, y), {"x": x, "y": y}, sort_value=-score)

            def matches(self, payload, wanted):
                return {payload["x"], payload["y"]} == {wanted["x"], wanted["y"]}

        return Ranker(list("abcde"))


def test_a_finished_ranking_is_ordered_counts_skips_and_applies_the_best():
    applied = []
    model = PairModel(on_apply=applied.append, runner=inline_runner())
    model.start()
    assert model.run_state == RunState.Done
    assert model.completed == 10 and len(model.rows) == 9
    scores = [row["score"] for row in model.rows]
    assert scores == sorted(scores, reverse=True)
    assert (model.rows[0]["name0"], model.rows[0]["name1"]) == ("d", "e")
    assert applied == [{"x": "d", "y": "e"}]
    assert model.select_request == model.rows[0]["key"]
    assert model.ranked_columns()[0]["display"] == "bar"


def test_pause_and_continue_lose_no_view():
    runner = inline_runner(cancel_after=3)
    model = PairModel(runner=runner)
    model.start()
    # The inline worker saw the cancellation it asked for; that is a pause.
    model.run_state = RunState.Paused
    assert model.completed == 4
    assert model.enabled("start") and not model.enabled("pause")
    runner.tasks.clear()
    model._runner = inline_runner()
    model.start()
    assert model.run_state == RunState.Done
    assert model.completed == 10 and len(model.rows) == 9


def test_a_settings_change_offers_a_restart_and_the_restart_starts_over():
    model = PairModel(runner=inline_runner())
    model.start()
    assert not model.restart_offered()
    model.bonus = 100.0
    model.settings_changed(100.0)
    assert model.restart_offered() and model.enabled("start")
    assert model.start_label == "Restart with new settings"
    model.start()
    assert model.run_state == RunState.Done and model.rows[0]["score"] > 100


def test_closing_pauses_as_hidden_and_reopening_resumes_but_a_user_pause_stays():
    model = PairModel(runner=inline_runner())
    model.run_state = RunState.Running
    model._run = None
    model.pause_computation(RunState.Hidden)
    assert model.run_state == RunState.Hidden
    model.run_state = RunState.Paused
    model.dialog_reopened()
    assert model.run_state == RunState.Paused


def test_a_batch_from_a_replaced_ranking_is_dropped():
    from ndxplorer.analysis.vizrank import Batch

    model = PairModel(runner=inline_runner())
    model.start()
    rows = len(model.rows)
    model.on_partial_result(Batch(generation=model._run.generation - 1, items=[((0, 1), -99.0)]))
    assert len(model.rows) == rows


def test_a_hand_picked_view_is_marked_not_applied():
    applied = []
    model = PairModel(on_apply=applied.append, runner=inline_runner())
    model.start()
    applied.clear()
    model.auto_select({"x": "c", "y": "a"})
    assert model.select_request == next(r["key"] for r in model.rows
                                        if {r["name0"], r["name1"]} == {"a", "c"})
    assert applied == []


def test_the_spec_names_only_what_the_model_has():
    from emtk.widgets.view_spec import unsupported_sections

    from ndxplorer.analysis.projection_rank_model import ProjectionRankModel

    model = ProjectionRankModel(lambda: None, pairs=True)
    missing = [m for m in unsupported_sections(load_spec(), model)
               if "button_row" not in m and "info" not in m]
    assert missing == []


# ---- inside ndX, on the real background task ---------------------------------------------


@pytest.fixture(scope="module")
def qapp():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


N = 3000


@pytest.fixture
def window(qapp):
    """An ndX window whose informative view is (Tau, r): two species, planted."""
    from ndxplorer.core.data_source import DataSource
    from ndxplorer.core.plot_main import NDXplorer

    rng = np.random.default_rng(21)
    species = rng.random(N) < 0.4
    frame = DataSource.from_columns({
        "Number of Photons": rng.normal(300, 60, N).astype(np.float32),
        "Tau": np.where(species, rng.normal(1.5, 0.2, N), rng.normal(3.8, 0.3, N)).astype(np.float32),
        "r": np.where(species, rng.normal(0.3, 0.03, N), rng.normal(0.1, 0.03, N)).astype(np.float32),
        "Duration": rng.gamma(2.0, 2.0, N).astype(np.float32),
        "Rate": rng.normal(20, 5, N).astype(np.float32),
    })
    window = NDXplorer()
    window.show()
    deadline = time.monotonic() + 20
    while getattr(window, "projection_rank", None) is None and time.monotonic() < deadline:
        qapp.processEvents()
        time.sleep(0.01)
    window.data_source = frame
    window.plot_control.update()
    window.update()
    qapp.processEvents()
    yield window
    window.projection_rank.shutdown()
    window.close()


def wait_done(qapp, model, timeout=60):
    deadline = time.monotonic() + timeout
    while model.run_state != RunState.Done and time.monotonic() < deadline:
        qapp.processEvents()
        time.sleep(0.01)
    qapp.processEvents()
    assert model.run_state == RunState.Done, model.status_text()


def test_the_entries_sit_in_the_view_menu_right_below_umap(window):
    """Where the user looks for a view tool, and nothing left under the axis pickers."""
    names = [a.objectName() for a in window.menuView.actions()]
    at = names.index("actionUMAP")
    assert names[at + 1:at + 3] == ["actionFindProjections", "actionFindZParameters"]
    assert window.actionFindProjections.isEnabled() and window.actionFindZParameters.isEnabled()
    assert not window.plot_control.findChildren(QtWidgets.QPushButton, "buttonFindProjections")
    assert not window.plot_control.findChildren(QtWidgets.QPushButton, "buttonFindZParameters")


def test_the_entries_are_disabled_without_data_like_umap(qapp, monkeypatch):
    from ndxplorer.core.data_source import DataSource
    from ndxplorer.core.plot_main import NDXplorer

    empty = NDXplorer()
    try:
        # A new window holds a placeholder table and the data manager keeps it
        # when handed an empty one, so "no data" is what the window reports.
        monkeypatch.setattr(NDXplorer, "data_source", property(lambda self: DataSource()))
        empty.update_ui_enabled_state()
        assert not empty.actionUMAP.isEnabled()
        assert not empty.actionFindProjections.isEnabled()
        assert not empty.actionFindZParameters.isEnabled()
    finally:
        empty.close()


def test_the_menu_entry_opens_the_panel(window, qapp):
    window.update_ui_enabled_state()
    window.actionFindProjections.trigger()
    qapp.processEvents()
    controller = window.projection_rank
    assert True in controller.dialogs and controller.dialogs[True].isVisible()
    controller.dialogs[True].model.pause_computation()


def test_ranking_finds_the_planted_view_and_clicking_a_row_applies_it(window, qapp):
    controller = window.projection_rank
    model = controller.open(True)
    assert model.method == "populations", "Separation is the default"
    wait_done(qapp, model)
    assert {model.rows[0]["name0"], model.rows[0]["name1"]} == {"Tau", "r"}
    control = window.plot_control
    assert {control.p1[1], control.p2[1]} == {"Tau", "r"}, "the best view is applied at the end"

    panel = controller.dialogs[True]
    panel.host.repaint()
    qapp.processEvents()
    surface = panel.surface
    table = surface.table().control
    bx, by, _bw, _bh = table._body_box
    target = table.order()[2]
    wanted = surface.table().record(target)["payload"]
    surface.press(bx + 60.0, by + table._row_h * 2.5, 0, 0, 0, 0, 0, 1)
    panel.host.repaint()
    surface.release()
    qapp.processEvents()
    assert (control.p1[1], control.p2[1]) == (wanted["x"], wanted["y"])


def test_a_gate_becomes_the_class_and_its_parameter_is_left_out(window, qapp):
    control = window.plot_control
    control.addSelection(window.data_source.column_index("Tau"), 0.5, 2.5, False, True, "Tau")
    model = window.projection_rank.open(True)
    assert model.method == "populations", "Separation stays the default with a gate"
    assert "separation" in dict(model.method_options())
    assert model.classes == "Gate: inside vs outside"
    model.method = "separation"
    model.settings_changed()
    model.start()
    wait_done(qapp, model)
    names = {row[key] for row in model.rows for key in ("name0", "name1")}
    assert "Tau" not in names
    assert "r" in (model.rows[0]["name0"], model.rows[0]["name1"])


def test_the_z_ranking_sets_and_enables_z(window, qapp):
    model = window.projection_rank.open(False)
    wait_done(qapp, model)
    assert model.rows[0]["name0"] in {"Tau", "r"}
    assert window.plot_control.p3[1] == model.rows[0]["name0"]
    assert window.checkBoxEnableZ.isChecked()


def test_the_islands_of_the_view_become_the_window_clusters(window, qapp):
    """*Use islands as clusters* in the Qt window: Cluster Label, the spin box
    range and an Island Label column, as a Find structure run leaves them."""
    model = window.projection_rank.open(True)
    wait_done(qapp, model)
    control = window.plot_control
    names = (control.p1[1], control.p2[1])
    assert set(names) == {"Tau", "r"}
    assert not model.use_islands_hidden
    model.use_islands()
    qapp.processEvents()
    source = window.data_source
    labels = np.asarray(source.column_values("Cluster Label"))
    assert np.array_equal(labels, window._cluster_labels)
    assert set(np.unique(labels)) <= {-1, 0, 1} and {0, 1} <= set(np.unique(labels))
    assert np.sum(labels == 0) > np.sum(labels == 1), "numbered by size"
    island = np.asarray(source.column_values(f"Island Label ({names[0]} vs {names[1]})"))
    assert np.array_equal(island, labels)
    assert control.spinBoxCluster.maximum() == 1
    assert control.checkBoxColorClusters.isChecked()
    assert window.statusBar().currentMessage().startswith(
        f"2 islands of {names[0]} vs {names[1]} written as clusters 0\u20131")
