"""The 2-D overlay is one surface with several producers.

The equation curves, the Gaussian ellipses and the server-driven line sets all
paint onto ``overlay_plot``. Only the equation curves used to clear it, and
they cleared *everything*: fitting a Gaussian drew its 1σ/2σ/3σ ellipses, the
redraw scheduled a plot update a millisecond later, that update redrew the
equation overlays — and the ellipses were gone before the user let go of the
mouse. Curves therefore carry a layer, and each producer clears only its own.

The second half of the same bug is geometric: the overlay used to freeze a
curve into pixel coordinates when it was handed over, so a resize (or the
margins arriving later) left it describing a viewport that no longer existed.
That is what the deferred plot update was papering over. Mapping happens at
paint time now, which is what the resize test pins.
"""

from __future__ import annotations

import numpy as np
import pytest
from qtpy import QtCore, QtWidgets

from ndxplorer.widgets.drawing_overlay_widget import DEFAULT_LAYER, DrawingOverlayWidget


@pytest.fixture(scope="module")
def qt_app():
    """A single QApplication for the module (offscreen)."""
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


@pytest.fixture
def overlay(qt_app):
    """An overlay carrying one curve on each of two layers."""
    widget = DrawingOverlayWidget()
    widget.resize(200, 100)
    widget.set_axis_scale("xBottom", 0, 10)
    widget.set_axis_scale("yLeft", 0, 10)
    widget.add_curve(np.array([0.0, 10.0]), np.array([0.0, 10.0]), layer="equations")
    widget.add_curve(np.array([0.0, 5.0, 10.0]), np.array([5.0, 5.0, 5.0]), layer="gaussian")
    return widget


def test_clearing_one_layer_leaves_the_others(overlay):
    """The bug: an equation redraw must not take the ellipses with it."""
    overlay.clear_curves("equations")

    assert overlay.layers() == ["gaussian"]
    assert len(overlay._curves) == 1


def test_clearing_without_a_layer_still_clears_everything(overlay):
    """``clear_plots`` wants the whole surface gone, and says so by naming none."""
    overlay.clear_curves()

    assert overlay._curves == []
    assert overlay.layers() == []


def test_an_unnamed_curve_lands_on_the_default_layer(qt_app):
    widget = DrawingOverlayWidget()
    widget.add_curve(np.array([0.0, 1.0]), np.array([0.0, 1.0]))

    assert widget.layers() == [DEFAULT_LAYER]


def test_clearing_an_empty_layer_is_harmless(overlay):
    overlay.clear_curves("nothing-drawn-here")

    assert sorted(overlay.layers()) == ["equations", "gaussian"]


def test_a_curve_follows_the_widget_it_is_drawn_on(overlay):
    """Geometry is derived at paint time, not frozen at ``add_curve`` time.

    Pinned because a curve frozen into pixels survives a resize looking fine —
    it is drawn, just over the wrong part of the map, which no assertion on
    "is it there" would catch.
    """
    before = overlay._polyline(overlay._curves[0])
    overlay.resize(400, 300)
    after = overlay._polyline(overlay._curves[0])

    assert before.at(1).x() == pytest.approx(200.0)
    assert after.at(1).x() == pytest.approx(400.0)
    assert after.at(1).y() == pytest.approx(0.0)


def test_margins_arriving_late_still_shift_the_curve(overlay):
    """Margins are set by the 2-D plot after the curve is handed over."""
    before = overlay._polyline(overlay._curves[1])
    overlay.set_margins(50, 0, 0, 0)
    after = overlay._polyline(overlay._curves[1])

    assert before.at(0).x() == pytest.approx(0.0)
    assert after.at(0).x() == pytest.approx(50.0)


def test_painting_a_layered_curve_raises_nothing(overlay):
    """A full paint round-trip over the stored data coordinates."""
    overlay.grab()
