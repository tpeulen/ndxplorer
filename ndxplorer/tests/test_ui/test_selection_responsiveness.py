"""Dragging the z selector redraws once per frame, not twice per second.

The region emits when it moves. Nothing listened: a 500 ms ``QTimer`` compared
``get_range()`` against the last value it had seen, so the plot followed a drag
at two frames a second and lagged up to half a second behind the mouse -- on data
where the redraw itself costs tens of milliseconds.

Four handlers also called ``update_histograms()`` and then ``update_plots()``,
and ``update_plots`` fills the histograms itself, so every one of those computed
the whole set twice.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from qtpy import QtWidgets

from ndxplorer.core.data_source import DataSource


@pytest.fixture(scope="module")
def qapp():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


@pytest.fixture
def window(qapp):
    from ndxplorer.core.plot_main import NDXplorer

    rng = np.random.default_rng(5)
    n = 2000
    data = pd.DataFrame({
        "Tau (green)": rng.normal(2.0, 0.4, n),
        "Proximity ratio": rng.normal(0.6, 0.1, n),
        "Number of Photons": rng.integers(30, 400, n).astype(float),
    })
    win = NDXplorer()
    win.data_source = DataSource(list(data.columns), data)
    win.resize(1000, 700)
    win.show()
    qapp.processEvents()
    yield win
    win.close()


def _count_updates(monkeypatch, window):
    """Count the histogram fills a redraw performs."""
    import ndxplorer.plotting.plot_update_helpers as puh

    calls = []
    original = puh.update_histograms

    def counting(nd):
        calls.append(1)
        return original(nd)

    monkeypatch.setattr(puh, "update_histograms", counting)
    return calls


def test_nothing_polls_the_selection(window):
    """A poll is a wakeup on a schedule unrelated to what the user is doing."""
    assert not hasattr(window, "z_range_check_timer")
    assert not hasattr(window, "check_z_range_changes")

    timers = [t for t in window.findChildren(QtWidgets.QWidget)]  # noqa: F841
    from qtpy import QtCore

    periodic = [t for t in window.findChildren(QtCore.QTimer)
                if t.isActive() and not t.isSingleShot()]
    assert periodic == [], [t.objectName() or repr(t) for t in periodic]


def test_the_region_is_connected_to_the_redraw(window, qapp):
    """Moving the region asks for a redraw, without anything having to notice."""
    if not hasattr(window, "selection_z"):
        pytest.skip("plots not built")
    window.checkBoxEnableZ.setChecked(True)
    window._dynamic_selection = True
    qapp.processEvents()

    window._cancel_scheduled_plot_update()
    lo, hi = window.selection_z.get_range()
    window.selection_z.set_range(lo, (lo + hi) / 2.0)
    assert window._plot_update_pending, "the region moved and nothing was scheduled"


def test_a_drag_is_batched_into_frames(window, qapp, monkeypatch):
    """Twenty moves inside one batching window are one redraw, not twenty.

    This is what makes listening to the *live* signal cheaper than polling
    rather than more expensive.
    """
    if not hasattr(window, "selection_z"):
        pytest.skip("plots not built")
    window.checkBoxEnableZ.setChecked(True)
    window._dynamic_selection = True
    qapp.processEvents()

    calls = _count_updates(monkeypatch, window)
    lo, hi = float(window.plot_control.zmin), float(window.plot_control.zmax)
    span = (hi - lo) / 4.0
    for i in range(20):
        window.selection_z.set_range(lo + i * span / 20, lo + i * span / 20 + span)
    assert calls == [], "a redraw ran per move instead of per frame"

    window._execute_scheduled_plot_update()
    assert len(calls) <= 1


def test_dynamic_selection_off_ignores_the_drag(window, qapp):
    if not hasattr(window, "selection_z"):
        pytest.skip("plots not built")
    window.checkBoxEnableZ.setChecked(True)
    window._dynamic_selection = False
    qapp.processEvents()

    window._cancel_scheduled_plot_update()
    lo, hi = window.selection_z.get_range()
    window.selection_z.set_range(lo, (lo + hi) / 2.0)
    assert not window._plot_update_pending


def test_a_toggle_fills_the_histograms_once(window, qapp, monkeypatch):
    """``update_histograms()`` then ``update_plots()`` filled them twice.

    Four handlers did it -- the z-axis toggle, the weight check box, the weight
    column and dynamic selection -- so every one of those interactions paid for
    the whole set of histograms twice over.
    """
    if not hasattr(window, "selection_z"):
        pytest.skip("plots not built")
    calls = _count_updates(monkeypatch, window)

    window.on_enable_z_changed(True)
    qapp.processEvents()
    window._execute_scheduled_plot_update()
    assert len(calls) <= 1, f"{len(calls)} histogram fills for one toggle"
