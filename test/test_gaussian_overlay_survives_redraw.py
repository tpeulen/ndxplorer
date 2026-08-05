"""Fitted Gaussian ellipses stay on the 2-D map.

The reported symptom was "they are there just for a short time and then
disappear". The redraw drew its ellipses and then scheduled a full
``update_plots`` one millisecond later; that update redrew the equation
overlays, which cleared the whole shared overlay surface. So the curve count
straight after the redraw proves nothing — the event loop has to be given a
turn before it is read, which is what these tests do.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from qtpy import QtCore, QtWidgets

from ndxplorer.core.data_source import DataSource

GAUSSIAN_CURVES_PER_COMPONENT = 3  # 1σ, 2σ, 3σ


@pytest.fixture(scope="module")
def qt_app():
    """A single QApplication for the module (offscreen)."""
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _settle(app, ms: int = 50) -> None:
    """Give queued timers a turn — the deferred wipe lived here."""
    loop = QtCore.QEventLoop()
    QtCore.QTimer.singleShot(ms, loop.quit)
    loop.exec_()
    app.processEvents()


@pytest.fixture
def window(qt_app):
    """A window showing two well-separated blobs, axes selected."""
    from ndxplorer.core.plot_main import NDXplorer

    rng = np.random.default_rng(0)
    blocks = [
        np.column_stack([rng.normal(cx, 0.04, 2000), rng.normal(cy, 0.05, 2000)])
        for cx, cy in [(0.25, 0.35), (0.70, 0.70)]
    ]
    data = np.vstack(blocks)
    frame = pd.DataFrame({"x": data[:, 0], "y": data[:, 1], "z": rng.normal(0, 1, len(data))})
    columns = list(frame.columns)

    win = NDXplorer(data_source=DataSource(columns, frame))
    win.resize(900, 700)
    win.show()
    qt_app.processEvents()
    control = win.plot_control
    control.update(update_comboboxes=True, update_plots=False)
    control.comboBoxSelX.setCurrentIndex(columns.index("x"))
    control.comboBoxSelY.setCurrentIndex(columns.index("y"))
    control.comboBoxSelZ.setCurrentIndex(columns.index("z"))
    win.update_plots()
    for _ in range(10):
        _settle(qt_app, 100)
        if win._histogram.get("2d") is not None:
            break
    yield win
    win.close()


def _draw_two_gaussians(window) -> None:
    gaussian_fit = window.gaussian_fit
    for mu in [(0.25, 0.35), (0.70, 0.70)]:
        gaussian_fit._append_gaussian_row(mu, np.diag([0.04**2, 0.05**2]))
    gaussian_fit._redraw_gaussian_overlays_from_table()


def test_the_histogram_is_ready(window):
    """Without a 2-D histogram every overlay silently draws nothing."""
    assert window._histogram.get("2d") is not None


def test_the_ellipses_are_still_there_after_the_event_loop_turns(window, qt_app):
    """The reported bug, end to end."""
    _draw_two_gaussians(window)
    drawn = len(window.overlay_plot._curves)
    assert drawn == 2 * GAUSSIAN_CURVES_PER_COMPONENT

    _settle(qt_app)

    assert len(window.overlay_plot._curves) == drawn, (
        "the ellipses vanished a moment after being drawn — something on a "
        "queued redraw cleared the shared overlay surface"
    )


def test_a_full_plot_update_keeps_them(window, qt_app):
    """A new histogram redraws the ellipses in the new bin coordinates."""
    _draw_two_gaussians(window)

    window.update_plots()
    _settle(qt_app)

    assert window.overlay_plot.layers() == ["gaussian"]


def test_an_equation_curve_and_the_ellipses_share_the_map(window, qt_app):
    """Both producers survive each other's redraws."""
    _draw_two_gaussians(window)
    window.curve_overlay_widget.add_curve("0.15 + 0.8 * x")
    _settle(qt_app)

    window.update_plots()
    _settle(qt_app)

    assert sorted(window.overlay_plot.layers()) == ["equations", "gaussian"]


def test_clearing_the_gaussians_leaves_the_equation_curve(window, qt_app):
    _draw_two_gaussians(window)
    window.curve_overlay_widget.add_curve("0.15 + 0.8 * x")
    _settle(qt_app)

    window.on_clear_gaussians()
    _settle(qt_app)

    assert window.overlay_plot.layers() == ["equations"]
