"""The panels live in a ChiSurf dock area, not in Qt's dock widgets.

``QMainWindow``'s docks tab and float, but the tab bar is the platform's, the
arrangement is limited to four zones, and none of it matches the rest of ChiSurf.
What matters for these tests is that the *contents* came through: every panel is
still there, still reachable by the attribute the window enabled and hid it by,
and the two that used to open hidden still do.
"""

from __future__ import annotations

import pytest
from qtpy import QtWidgets

from ndxplorer.utils.dock_conversion import PANELS


@pytest.fixture(scope="module")
def qapp():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


@pytest.fixture
def window(qapp):
    from ndxplorer.core.plot_main import NDXplorer

    win = NDXplorer()
    win.resize(1200, 800)
    win.show()
    qapp.processEvents()
    if getattr(win, "dock_area", None) is None:
        win.close()
        pytest.skip("ChiSurf dock area unavailable")
    yield win
    win.close()


def test_no_qt_dock_widget_survives(window):
    assert window.findChildren(QtWidgets.QDockWidget) == []


def test_every_panel_became_a_tab(window):
    area = window.dock_area
    tabs = [area.tabText(i) for i in range(area.count())]
    assert tabs == [title for _, title, _ in PANELS] + ["Plot"]


def test_the_attribute_now_names_the_panel_itself(window):
    """The window enabled and hid these by name; the name must still resolve.

    ``_update_action_states`` calls ``setEnabled`` on each of them when data
    arrives, and the Fit action shows and hides one. Left pointing at a deleted
    container, every one of those is a silent no-op.
    """
    area = window.dock_area
    for name, title, _ in PANELS:
        panel = getattr(window, name, None)
        assert panel is not None, f"{name} is gone"
        assert area.indexOf(panel) >= 0, f"{name} is not in the dock area"
        assert area.tabText(area.indexOf(panel)) == title


def test_the_panels_that_opened_hidden_still_do(window):
    area = window.dock_area
    for name, _, hidden in PANELS:
        index = area.indexOf(getattr(window, name))
        assert area.isTabVisible(index) is not hidden


def test_the_plot_is_the_other_half_of_the_split(window):
    """Panels on the left, plot on the right -- where the Qt dock had them."""
    area = window.dock_area
    splitters = [s for s in area.findChildren(QtWidgets.QSplitter)
                 if s.count() == 2]
    assert splitters, "the dock area did not split"
    sizes = splitters[0].sizes()
    assert sizes[1] > sizes[0], "the plot got the smaller half"


def test_the_fit_action_shows_and_hides_its_tab(window, qapp):
    """It drove ``QDockWidget.setVisible``; a dock tab is not shown that way.

    Hiding the *widget* of a tab that is still in the bar leaves the tab there
    with nothing behind it, which looks like a panel that broke rather than one
    that was closed.
    """
    area = window.dock_area
    panel = window.dockWidget_Fit
    index = area.indexOf(panel)
    assert not area.isTabVisible(index)

    window.actionFit_Gaussians.setChecked(True)
    qapp.processEvents()
    assert area.isTabVisible(index)

    window.actionFit_Gaussians.setChecked(False)
    qapp.processEvents()
    assert not area.isTabVisible(index)


def test_the_plot_control_still_works_after_the_move(window):
    """The move is a re-parenting, not a rebuild."""
    control = window.plot_control
    assert control.comboBoxSelX is not None
    assert control.playback is not None
    assert control.panels_form is not None
    assert isinstance(control.n_xhist_2d, int)


def test_switching_to_the_fit_tab_arms_point_mode(window, qapp):
    """A user on the Gaussian Fit tab is "in the fit dock": a click on the 2D
    histogram must add a local Gaussian there, not start a rubber-band
    selection. Only the menu action used to arm point mode, so reaching the
    tab directly left clicks selecting."""
    area = window.dock_area
    panel = window.dockWidget_Fit

    # Bring the tab into the bar the way the action does, then leave it.
    window.actionFit_Gaussians.setChecked(True)
    qapp.processEvents()
    area.setCurrentWidget(window.dockWidget_Parameters)
    qapp.processEvents()

    # Activating the tab directly must arm point mode...
    area.setCurrentWidget(panel)
    qapp.processEvents()
    assert window.mouse_event_filter.mode == "point"
    assert window.btnSelectPoint.isChecked()

    # ...activating any other tab must disarm it (visible beside the plot is
    # not being worked in)...
    area.setCurrentWidget(window.dockWidget_Parameters)
    qapp.processEvents()
    assert window.mouse_event_filter.mode == "rectangle"

    # ...and back, then hiding the tab through the action disarms too.
    area.setCurrentWidget(panel)
    qapp.processEvents()
    assert window.mouse_event_filter.mode == "point"
    window.actionFit_Gaussians.setChecked(False)
    qapp.processEvents()
    assert window.mouse_event_filter.mode == "rectangle"
