"""What "Auto" ranges to, and what a range means after the scale changes.

Both are about the same confusion: a number on an axis is only meaningful
together with the projection it was written in, and both the auto-range and the
draggable region had places where that pairing was dropped.
"""

from __future__ import annotations

import numpy as np
import pytest

from ndxplorer.utils import axis_helpers


def test_auto_range_leaves_out_a_runaway_tail():
    """One burst must not decide the axis for all the others.

    Measured on a real µs-ALEX burst table: photon counts with a 99.9th
    percentile of 1 108 and a single burst at 450 094. Auto-ranging to the
    maximum drew the whole distribution inside the first pixel.
    """
    rng = np.random.default_rng(0)
    values = np.concatenate([rng.gamma(3.0, 60.0, 20_000), [450_094.0]])

    low, high = axis_helpers.robust_axis_range(values)
    assert high < 0.05 * float(values.max()), "the outlier still sets the axis"
    assert high > float(np.percentile(values, 99.0))
    assert low <= float(np.percentile(values, 1.0))


def test_auto_range_does_not_trim_an_axis_that_has_no_outliers():
    """A clean axis auto-ranges to exactly its data, as it always did.

    Percentile-clipping unconditionally would quietly cut the ends off an
    efficiency running 0 to 1 — "Auto" would stop meaning "all of it" on the
    data where it was never broken.
    """
    values = np.linspace(0.0, 1.0, 5000)
    low, high = axis_helpers.robust_axis_range(values)
    assert (low, high) == (pytest.approx(0.0), pytest.approx(1.0))


def test_auto_range_survives_degenerate_input():
    """No data, one point, all-identical: a range, never an exception."""
    assert axis_helpers.robust_axis_range(np.array([])) == (0.0, 0.0)
    assert axis_helpers.robust_axis_range(np.array([7.0])) == (7.0, 7.0)
    assert axis_helpers.robust_axis_range(np.full(100, 3.0)) == (3.0, 3.0)


def test_auto_range_on_a_log_axis_ignores_non_positive_values():
    """Zeros cannot be shown on a log axis and must not set its minimum."""
    values = np.concatenate([np.zeros(500), np.geomspace(1.0, 1000.0, 5000)])
    low, _high = axis_helpers.robust_axis_range(values, scale="log")
    assert low > 0.0


@pytest.fixture
def region(qapp):
    """A range selection on a plot whose x scale can be switched."""
    from ndxplorer.plotting.pg_image_widget import PGHistogramPlot

    plot = PGHistogramPlot()
    selection = plot.add_range_selection(60.0, 450_094.0)
    return plot, selection


def test_a_region_keeps_its_data_range_when_the_axis_goes_log(region):
    """Switching to log must move the drawing, not the meaning."""
    plot, selection = region
    assert selection.get_range() == (pytest.approx(60.0), pytest.approx(450_094.0))

    plot.set_axis_scale("bottom", "log")

    low, high = selection.get_range()
    assert low == pytest.approx(60.0, rel=1e-6)
    assert high == pytest.approx(450_094.0, rel=1e-6)
    # And it is *drawn* in log coordinates, which is the half that was missing.
    view_low, view_high = selection.item.getRegion()
    assert view_low == pytest.approx(np.log10(60.0), abs=1e-6)
    assert view_high == pytest.approx(np.log10(450_094.0), abs=1e-6)


def test_a_region_keeps_its_data_range_when_the_axis_goes_back_to_linear(region):
    """The direction that produced the reported symptom.

    A region set on a log axis holds view coordinates like 1.78 to 5.65. Going
    linear without re-projecting turns that into a selection of 1.78 to 5.65
    *counts* — a sliver at the left edge that gates away the measurement while
    the range boxes still read 60 and 450 094.
    """
    plot, selection = region
    plot.set_axis_scale("bottom", "log")
    # What ``fit_z_selection_to_axis`` does on the log axis: write the data
    # range. Without this the item still holds the linear numbers and the test
    # passes for the wrong reason.
    selection.set_range(60.0, 450_094.0)
    plot.set_axis_scale("bottom", "linear")

    low, high = selection.get_range()
    assert low == pytest.approx(60.0, rel=1e-6)
    assert high == pytest.approx(450_094.0, rel=1e-6)
    assert selection.item.getRegion()[1] == pytest.approx(450_094.0, rel=1e-6)


def test_the_z_range_boxes_are_the_same_size(qapp):
    """Min and max sit in one horizontal layout, so neither is clipped.

    They used to live in two cells of a grid whose column widths are set by the
    *other* rows: the minimum inherited the width of the parameter combo above
    it and the maximum inherited the width of a bin-count spin box, so the
    maximum was cut off mid-number.
    """
    from qtpy import QtWidgets

    from ndxplorer.core.plot_main import NDXplorer

    window = NDXplorer()
    control = window.plot_control
    for button in control.findChildren(QtWidgets.QPushButton):
        if button.objectName() == "CollapsibleBoxHeader" and "z axis" in button.text():
            button.setChecked(True)
            button.click()
    control.resize(1000, 600)
    qapp.processEvents()

    assert control.spinBoxZmin.parentWidget() is control.spinBoxZmax.parentWidget()
    assert control.spinBoxZmin.width() == control.spinBoxZmax.width()
    window.close()
