"""The dynamic-z region, which used to empty the plot.

The region is created at a hardcoded 0.25 to 0.5 and nothing moved it
afterwards. Choosing a third axis whose values live anywhere else -- a lifetime
in nanoseconds, a photon count, a pixel index -- gated everything to a window
containing no data, and the whole plot went blank with nothing on screen to say
that a selection was responsible.

The subtlety, and why the first fix was not enough: 0.25 to 0.5 IS inside an
axis running to 6. "Is the region on the axis" is not the question. "Has the
region been positioned for THIS axis" is.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from qtpy import QtWidgets

N = 400


@pytest.fixture(scope="session")
def qapp() -> QtWidgets.QApplication:
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    return app


@pytest.fixture
def window(qapp):
    """A window whose z parameter lives nowhere near the default region."""
    from ndxplorer.core.data_source import DataSource
    from ndxplorer.core.plot_main import NDXplorer

    rng = np.random.default_rng(5)
    frame = pd.DataFrame({
        "x": rng.uniform(0.0, 10.0, N),
        "y": rng.uniform(0.0, 10.0, N),
        # Nowhere near 0.25 to 0.5 -- a lifetime in nanoseconds.
        "Tau": rng.uniform(2.0, 6.0, N),
    })
    window = NDXplorer()
    window.data_source = DataSource(data=frame)
    # What the open path does after loading: fill the axis choosers.
    window.plot_control.update()
    window.update()
    qapp.processEvents()
    yield window
    window.close()


def enable_z(window, qapp, parameter="Tau"):
    control = window.plot_control
    index = control.comboBoxSelZ.findText(parameter)
    assert index >= 0, f"{parameter} is not in the z combo"
    control.comboBoxSelZ.setCurrentIndex(index)
    window.checkBoxEnableZ.setChecked(True)
    window._dynamic_selection = True
    qapp.processEvents()


def test_selecting_a_third_axis_does_not_empty_the_plot(window, qapp):
    """The regression, in the form the user meets it."""
    enable_z(window, qapp)
    state = window._collect_mask_state()
    window.data_manager.mask_state = state
    kept = int((~window.data_manager.get_value_mask()).sum())
    assert kept == N, "enabling a z axis gated away every point"


def test_the_region_is_put_over_the_whole_axis(window, qapp):
    """"No selection yet" means everything, not an arbitrary window."""
    enable_z(window, qapp)
    window._collect_mask_state()
    low, high = window.selection_z.get_range()
    assert (low, high) == (window.plot_control.zmin, window.plot_control.zmax)


def test_a_region_the_user_dragged_is_left_alone(window, qapp):
    """Refitting on every read would make the region impossible to move."""
    enable_z(window, qapp)
    window._collect_mask_state()
    window.selection_z.set_range(3.0, 4.0)

    state = window._collect_mask_state()
    assert tuple(window.selection_z.get_range()) == (3.0, 4.0)
    assert state.z_range == (3.0, 4.0)

    window.data_manager.mask_state = state
    kept = ~window.data_manager.get_value_mask()
    tau = window.data_source.column_view(window.data_source.column_index("Tau"))
    np.testing.assert_array_equal(kept, (tau >= 3.0) & (tau <= 4.0))


def test_changing_the_z_parameter_refits_the_region(window, qapp):
    """A region dragged on one axis means nothing on the next."""
    enable_z(window, qapp)
    window._collect_mask_state()
    window.selection_z.set_range(3.0, 4.0)
    window._collect_mask_state()

    enable_z(window, qapp, parameter="x")
    window.plot_control.on_axis_changed("z")
    window._collect_mask_state()
    low, high = window.selection_z.get_range()
    assert (low, high) == (window.plot_control.zmin, window.plot_control.zmax)

    # The region spans the axis, so it excludes nothing the AXIS does not --
    # a range narrower than the data is the axis's business, not the region's.
    state = window._collect_mask_state()
    window.data_manager.mask_state = state
    kept = ~window.data_manager.get_value_mask()
    values = window.data_source.column_view(window.data_source.column_index("x"))
    np.testing.assert_array_equal(
        kept, (values >= window.plot_control.zmin) & (values <= window.plot_control.zmax))
