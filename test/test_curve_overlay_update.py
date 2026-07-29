"""Drawing the overlay curves onto the 2-D map.

The update path is wrapped in ``except (…, AttributeError)``, so a stale
attribute on either side does not surface as a crash — it turns every redraw
into a status-bar warning ("Error updating curve overlays: …") and leaves the
overlays out. That is exactly how a vestigial ``curve_items`` list survived
here: its only writer raised, every redraw logged, and nothing failed.
"""

from __future__ import annotations

import numpy as np
import pytest
from qtpy import QtWidgets

from ndxplorer.plotting.curve_overlay import CurveOverlayWidget
from ndxplorer.widgets.drawing_overlay_widget import DrawingOverlayWidget


@pytest.fixture(scope="module")
def qt_app():
    """A single QApplication for the module (offscreen)."""
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    yield app


@pytest.fixture
def histogram():
    """A small 2-D histogram with its bin edges."""
    counts = np.zeros((20, 20), dtype=float)
    counts[5:8, 5:8] = 10.0
    edges = np.linspace(0.0, 1.0, 21)
    return counts, edges, edges


def test_update_leaves_nothing_stale_behind(qt_app, histogram):
    """A full update round-trip raises nothing — no attribute has gone missing."""
    widget = CurveOverlayWidget()
    overlay = DrawingOverlayWidget()

    widget.update_curve_overlays(
        overlay_plot=overlay,
        histogram_data=histogram,
        plot_control=None,
        curve_evaluator=None,
        value_to_bin_func=lambda value, edges: 0,
    )


def test_the_widget_keeps_no_item_list(qt_app):
    """The overlay plot owns the drawn curves; this widget hands back no handles.

    Pinned because the caller used to mirror a ``curve_items`` list from here,
    which raised on every redraw once that attribute went away.
    """
    assert not hasattr(CurveOverlayWidget, "curve_items")
    assert not hasattr(CurveOverlayWidget(), "curve_items")


def test_clearing_goes_through_the_plot(qt_app):
    """``clear_curves`` on the plot is what removes drawn curves."""
    overlay = DrawingOverlayWidget()
    overlay.add_curve(np.array([0.0, 1.0]), np.array([0.0, 1.0]))
    assert overlay._curves

    overlay.clear_curves()

    assert not overlay._curves
