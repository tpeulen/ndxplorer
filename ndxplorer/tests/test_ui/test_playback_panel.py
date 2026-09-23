"""The Playback panel, driven through its real widgets.

:mod:`ndxplorer.tests.test_playback_controller` covers the gate. This covers the
wiring: that the panel AutoForm builds from ``playback.view.json`` has the
controls the spec asks for, that clicking them moves the controller, and that the
axis a data set is played back along is chosen from its columns.

The buttons are *clicked* rather than the model methods called, because the
failure this guards against is a control that renders and is connected to
nothing -- which no test that calls the method itself can see.
"""

from __future__ import annotations

import numpy as np
import pytest
from qtpy import QtWidgets

from ndxplorer.core.data_source import DataSource
from ndxplorer.core.playback import MODE_INTEGRATE, MODE_STACK, MODE_WINDOW


@pytest.fixture(scope="module")
def qapp():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


@pytest.fixture
def control(qapp):
    from ndxplorer.plotting.plot_control import SurfacePlotWidget

    widget = SurfacePlotWidget()
    if widget.playback_form is None:
        pytest.skip("chisurf AutoForm unavailable")
    yield widget
    widget.close()


def _source(**columns) -> DataSource:
    return DataSource.from_columns(columns)


def _burst_source(n=201) -> DataSource:
    return _source(**{
        "Mean Macro Time (s)": np.linspace(0.0, 60.0, n),
        "Proximity ratio": np.linspace(0.0, 1.0, n),
        "Number of Photons": np.full(n, 50.0),
    })


class _FakeParent:
    """Stands in for the NDXplorer window: the data, and "redraw please"."""

    def __init__(self, source):
        self.data_source = source
        self.redraws = 0

    def request_plot_update(self, *args, **kwargs):
        self.redraws += 1


def _button(control, action: str) -> QtWidgets.QToolButton:
    """The transport button bound to `action`, as AutoForm named it."""
    for btn in control.playback_form.findChildren(QtWidgets.QToolButton):
        if getattr(btn, "_autoform_action", "") == action:
            return btn
    raise AssertionError(f"no button for {action!r}")


# ------------------------------------------------------------------ the panel

def test_the_panel_has_the_controls_the_spec_declares(control):
    form = control.playback_form
    assert [b.text() for b in form.findChildren(QtWidgets.QToolButton)
            if getattr(b, "_autoform_action", "")] == ["◀◀", "◀", "■", "▶", "▶▶"]
    # Step and speed: both sliders, both integer-valued. The int branch of the
    # value renderer used to be tested before the slider branch, so an int
    # slider rendered as a bare spin box.
    assert len(form.findChildren(QtWidgets.QSlider)) == 2
    radios = {r.text() for r in form.findChildren(QtWidgets.QRadioButton)}
    assert radios == {"Window", "Integrate", "Stack"}


def _fold_header(form, title):
    return next(b for b in form.findChildren(QtWidgets.QAbstractButton)
                if b.isCheckable() and title in b.text())


def test_folding_a_panel_gives_the_space_back(control, qapp):
    """A fold that leaves a panel-sized hole is worse than no fold.

    An AutoForm ends its layout with a stretch, so at the default Preferred
    policy it keeps any spare vertical space the dock gives it -- and collapsing
    then shrinks only the box inside it. The group boxes these replaced were
    Fixed for exactly this reason.
    """
    control.setup_playback(_burst_source())
    control.resize(460, 900)
    control.show()
    qapp.processEvents()

    form = control.playback_form
    header = _fold_header(form, "Playback")
    header.click()                            # it opens folded
    qapp.processEvents()
    expanded = form.height()
    assert expanded == form.sizeHint().height()

    header.click()
    qapp.processEvents()
    assert form.height() < expanded / 2
    assert form.height() == form.sizeHint().height()


def test_the_playback_panel_opens_folded(control, qapp):
    """It is the block you set up once and then want out of the way."""
    control.setup_playback(_burst_source())
    control.show()
    qapp.processEvents()
    assert not _fold_header(control.playback_form, "Playback").isChecked()
    assert control.playback_model.collapsed


def test_the_fold_survives_a_rebuild(control, qapp):
    """Changing the step count rebuilds the form; it must not re-fold it.

    The spec's ``collapsed`` is the *opening* state. Re-reading it on every
    rebuild folds the panel under the hands of a user who just opened it and
    reached for the step count.
    """
    control.setup_playback(_burst_source())
    control.show()
    qapp.processEvents()

    _fold_header(control.playback_form, "Playback").click()
    qapp.processEvents()
    assert not control.playback_model.collapsed

    control.playback_model.n_steps = 25
    qapp.processEvents()
    qapp.processEvents()
    assert _fold_header(control.playback_form, "Playback").isChecked()


def test_every_block_of_the_dock_is_a_foldable_panel(control, qapp):
    """Five blocks, five headers. The group boxes had titles and no folds."""
    from chisurf.gui.widgets.collapsible_box import CollapsibleBox

    control.setup_playback(_burst_source())
    control.resize(460, 900)
    control.show()
    qapp.processEvents()

    titles = [b.title() for b in control.playback_form.findChildren(CollapsibleBox)]
    titles += [b.title() for b in control.panels_form.findChildren(CollapsibleBox)]
    assert titles == ["Playback", "Histogram", "z axis", "Draw Mask", "Selection"]
    assert not control.findChildren(QtWidgets.QGroupBox)


def test_folding_a_panel_collapses_it_to_its_header(control, qapp):
    """Folding gives the space back here too, one panel at a time.

    The *form* does not shrink: the Selection panel is the expanding one, so it
    takes whatever the others give up. What has to shrink is the folded panel.
    """
    from chisurf.gui.widgets.collapsible_box import CollapsibleBox

    control.resize(460, 900)
    control.show()
    qapp.processEvents()

    boxes = control.panels_form.findChildren(CollapsibleBox)
    histogram = next(b for b in boxes if b.title() == "Histogram")
    selection = next(b for b in boxes if b.title() == "Selection")
    assert histogram.is_expanded()

    before, selection_before = histogram.height(), selection.height()
    histogram._btn.click()
    qapp.processEvents()

    assert not histogram.is_expanded()
    assert histogram.height() < before / 2
    # ...and the space went to the panel that wanted it.
    assert selection.height() > selection_before


def test_the_gating_check_boxes_replaced_the_checkable_group_boxes(control):
    """A fold is not a disable, and the two must not be the same control.

    The z block and the mask block were *checkable* group boxes whose check
    state gated the z plot and mask drawing. A collapsible box has no such
    state, so conflating them would mean a panel someone tidied away silently
    stopped gating.
    """
    assert control.checkBoxEnableZ is not None
    assert control.checkBoxEnableDrawing is not None
    # ...and the mask widget reads the new one.
    assert control.mask_widget.enable_drawing_checkbox is control.checkBoxEnableDrawing


# ---------------------------------------------------------- adopted controls

def test_the_histogram_controls_survived_the_move(control):
    """The panel adopts the widgets ``uic`` built; it does not rebuild them.

    Everything reaches them by ``objectName`` -- the axis, scale and histogram
    mixins, and a dozen tests. A port that re-declared them as ``value`` and
    ``choice`` sections would break all of it, which is why this one does not.
    """
    for name in ("comboBoxSelX", "comboBoxSelY", "spinBoxBin1DX", "spinBoxBin2DX",
                 "checkBoxLogX", "checkBoxNormY", "checkBoxAutoScaleX",
                 "spinBoxXmin", "spinBoxXmax", "checkBoxWeight", "comboBoxWeight"):
        widget = getattr(control, name, None)
        assert widget is not None, f"{name} is gone"
        assert widget.parent() is not None, f"{name} was orphaned"
    # ...and the properties the mixins expose over them still answer.
    assert isinstance(control.n_xhist_2d, int)
    assert isinstance(control.xmin, float)


def test_no_control_is_left_outside_a_layout(control, qapp):
    """A child no layout positions draws at (0, 0), over whatever is there.

    Four of them were: ``replaceWidget`` takes the old spin box out of the
    layout but leaves it a child, and ``deleteLater`` does not reap it until the
    event loop unwinds past the level it was created at. They sat stacked in the
    corner as one spin box reading 0, on top of the x-axis row.
    """
    control.resize(460, 900)
    control.show()
    qapp.processEvents()

    def in_layout(widget, parent):
        layout = parent.layout()
        stack = [layout] if layout is not None else []
        while stack:
            current = stack.pop()
            for i in range(current.count()):
                item = current.itemAt(i)
                if item.widget() is widget:
                    return True
                if item.layout() is not None:
                    stack.append(item.layout())
        return False

    host = control.widgetHistogram
    orphans = [w for w in host.findChildren(QtWidgets.QWidget)
               if w.parent() is host and not in_layout(w, host)]
    assert orphans == [], [w.objectName() for w in orphans]


def test_the_panel_starts_hidden_and_idle(control):
    assert control.playback_form.isHidden()
    assert control.playback.axis_name is None
    assert control.playback.mask(_burst_source()) is None


# ------------------------------------------------------------- axis detection

def test_a_burst_table_is_played_back_along_its_macro_time(control):
    control.setup_playback(_burst_source())
    assert control.playback.axis_name == "Mean Macro Time (s)"
    assert control.playback.n_steps == 100
    assert not control.playback.is_index
    assert not control.playback_form.isHidden()


def test_a_frame_index_wins_over_a_macro_time(control):
    """An image stack whose bursts also carry a time is still played by frame."""
    n = 40
    control.setup_playback(_source(**{
        "X pixel": np.tile(np.arange(4.0), 10),
        "Y pixel": np.repeat(np.arange(10.0), 4),
        "Frame": np.repeat(np.arange(4.0), 10),
        "Mean Macro Time (s)": np.linspace(0.0, 1.0, n),
    }))
    assert control.playback.axis_name == "Frame"
    assert control.playback.is_index and control.playback.n_steps == 4


def test_a_table_with_nothing_to_play_back_leaves_the_panel_idle(control):
    control.setup_playback(_source(**{
        "Tau (green)": np.linspace(1.0, 4.0, 20),
        "Proximity ratio": np.linspace(0.0, 1.0, 20),
    }))
    assert control.playback.axis_name is None
    # Still offered, so any column can be picked by hand.
    assert "Tau (green)" in control.playback_model.axis_options()


def test_an_empty_source_hides_the_panel(control):
    control.setup_playback(_burst_source())
    control.setup_playback(DataSource())
    assert control.playback.axis_name is None
    assert control.playback_form.isHidden()


def test_picking_an_axis_by_hand_rebinds_the_controller(control, monkeypatch):
    source = _burst_source()
    control.setup_playback(source)
    # The host reads the column off the parent window, which these tests do not
    # have; the panel is what is under test, not the window.
    monkeypatch.setattr(control, "parent", _FakeParent(source))
    control.playback_model.axis_name = "Number of Photons"
    assert control.playback.axis_name == "Number of Photons"


# ---------------------------------------------------------------- the buttons

def test_the_step_buttons_move_the_playback(control, qapp):
    control.setup_playback(_burst_source())
    control.playback_model.mode = MODE_WINDOW

    _button(control, "step_forward").click()
    assert control.playback.position == 1
    _button(control, "step_forward").click()
    assert control.playback.position == 2
    _button(control, "step_backward").click()
    assert control.playback.position == 1


def test_stepping_backward_from_the_start_wraps(control):
    control.setup_playback(_burst_source())
    control.playback_model.mode = MODE_WINDOW
    _button(control, "step_backward").click()
    assert control.playback.position == control.playback.n_steps - 1


def test_play_starts_the_timer_and_pause_stops_it(control):
    control.setup_playback(_burst_source())
    control.playback_model.mode = MODE_WINDOW

    _button(control, "play_forward").click()
    assert control.playback_model.playing
    assert control._playback_timer.isActive()
    assert control.playback.direction == 1

    _button(control, "pause").click()
    assert not control.playback_model.playing
    assert not control._playback_timer.isActive()


def test_pressing_play_again_stops_it(control):
    """The two play buttons behave like the checkable pair they replace."""
    control.setup_playback(_burst_source())
    control.playback_model.mode = MODE_WINDOW
    _button(control, "play_forward").click()
    _button(control, "play_forward").click()
    assert not control.playback_model.playing


def test_playing_backward_reverses_a_forward_playback(control):
    control.setup_playback(_burst_source())
    control.playback_model.mode = MODE_WINDOW
    _button(control, "play_forward").click()
    _button(control, "play_backward").click()
    assert control.playback_model.playing
    assert control.playback.direction == -1


def test_pressing_play_in_stack_mode_starts_playing(control):
    """Stack is the one mode where there is nothing to watch change.

    Doing nothing would look like a dead button, so the request is taken at face
    value: play means play, from the start of the measurement.
    """
    control.setup_playback(_burst_source())
    assert control.playback.mode == MODE_STACK
    _button(control, "play_forward").click()
    assert control.playback.mode == MODE_WINDOW
    assert control.playback_model.playing
    assert control.playback.position == 0


def test_a_timer_tick_advances_one_step(control):
    control.setup_playback(_burst_source())
    control.playback_model.mode = MODE_WINDOW
    _button(control, "play_forward").click()
    model = control.playback_model
    model.tick(model._next_due)
    assert control.playback.position == 1


# ------------------------------------------------------------------- settings

def test_the_speed_control_sets_the_timer_interval(control):
    control.setup_playback(_burst_source())
    _button(control, "play_forward").click()
    control.playback_model.fps = 20
    assert control._playback_timer.interval() == 50
    control.update_playback_settings(fps=5)
    assert control._playback_timer.interval() == 200
    assert control.playback.fps == 5


def test_changing_the_step_count_keeps_the_position_proportional(control):
    control.setup_playback(_burst_source())
    control.playback_model.mode = MODE_WINDOW
    control.playback_model.position = 50
    control.playback_model.n_steps = 20
    assert control.playback.position == 10


def test_the_readout_follows_the_mode(control):
    control.setup_playback(_burst_source())
    assert control.playback_model.status_text().startswith("All of")
    control.playback_model.mode = MODE_INTEGRATE
    assert "1/100" in control.playback_model.status_text()


def test_the_point_count_is_appended_to_the_readout(control):
    control.setup_playback(_burst_source())
    control.playback_model.set_count_text("42 shown")
    assert control.playback_model.status_text().endswith("42 shown")


def test_the_readout_is_a_hover_not_a_row(control):
    """The 50/100-style line was a persistent info row under the transport --
    always visible, rarely needed. It now answers on hover of the Step row,
    and no info widget renders it permanently (BUGS: slider display polish)."""
    control.setup_playback(_burst_source())
    control.playback_model.mode = MODE_INTEGRATE
    control._on_playback_changed()

    text = control.playback_model.status_text()
    assert text, "no readout to show"
    found = None
    for section, w in getattr(control.playback_form, "_section_widgets", []):
        if getattr(section, "attr", "") == "position":
            found = w
            break
    assert found is not None, "no Step row in the playback form"
    assert found.toolTip() == text
    assert found.slider.toolTip() == text
    assert found.editor.toolTip() == text

    # And the persistent row is gone from the spec.
    import json as _json
    from ndxplorer.plotting.playback_view_model import VIEW_SPEC_PATH
    spec = _json.load(open(VIEW_SPEC_PATH, encoding="utf-8"))
    kinds = [s.get("type") for s in spec["sections"][0]["sections"]]
    assert "info" not in kinds


# ----------------------------------------------------------------- selections

def test_a_selection_added_during_playback_carries_the_slice(control, monkeypatch):
    """A gate drawn on one slice has to say which slice, or it widens silently."""
    source = _burst_source()
    control.setup_playback(source)
    control.playback_model.mode = MODE_WINDOW
    control.playback_model.position = 3
    monkeypatch.setattr(control, "parent", _FakeParent(source))

    added = []
    monkeypatch.setattr(control, "addSelection",
                        lambda *a, **k: added.append(a))
    monkeypatch.setattr(control, "get_selections", lambda: [])
    control._add_playback_selection_if_needed()

    assert len(added) == 1
    idx, lower, upper = added[0][:3]
    assert source.parameter_names[idx] == "Mean Macro Time (s)"
    assert (lower, upper) == pytest.approx((1.8, 2.4))


def test_no_selection_is_added_while_stacked(control, monkeypatch):
    source = _burst_source()
    control.setup_playback(source)
    monkeypatch.setattr(control, "parent", _FakeParent(source))
    monkeypatch.setattr(control, "addSelection",
                        lambda *a, **k: pytest.fail("added a gate in stack mode"))
    control._add_playback_selection_if_needed()
