"""The gate the display used to ignore.

``DataManager.get_value_mask`` is what decides which points the plot shows. It
went through ``DataSource.get_mask_subset``, which dispatched over
``RectangularDataSelection``, ``Gaussian2DSelection`` and ``MaskDataSelection``
and then fell off the end of the chain with no ``else``. ``RegionDataSelection``
-- the class the UI creates whenever a user draws a lasso, at
``plot_control.py:1051`` -- matched none of them.

The result was a gate that looked like it worked from every direction except the
one that mattered: it appeared in the selection table, the export honoured it
(that path went through ``get_mask``, which had a different dispatch), and the
displayed population was unchanged.

Both tests here fail on the code as it stood before the selection path was
collapsed onto one implementation.
"""

import numpy as np
import pytest

from ndxplorer.core.data.data_manager import DataManager
from ndxplorer.core.data.mask_state import MaskState
from ndxplorer.core.data_source import DataSource
from ndxplorer.core.region_selection import RegionDataSelection

roi = pytest.importorskip("chisurf.core.roi", reason="chisurf is not importable")
RectangleROI = roi.RectangleROI


@pytest.fixture
def manager():
    rng = np.random.default_rng(5)
    n = 500
    frame = DataSource.from_columns({
        "a": rng.uniform(0.0, 10.0, n),
        "b": rng.uniform(0.0, 10.0, n),
        "c": rng.uniform(0.0, 10.0, n),
        "d": rng.uniform(0.0, 10.0, n),
        "e": rng.uniform(0.0, 10.0, n),
    })
    manager = DataManager()
    manager.data_source = frame
    return manager


def test_a_drawn_region_changes_the_displayed_population(manager):
    gate = RegionDataSelection(RectangleROI(2.0, 2.0, 5.0, 5.0), 0, 1)
    manager.mask_state = MaskState(selections=(gate,), axis_indices=(0, 1, 2))
    excluded = manager.get_value_mask()

    values = manager.data_source.values
    inside = ((values[0] >= 2.0) & (values[0] < 5.0) &
              (values[1] >= 2.0) & (values[1] < 5.0))
    assert inside.any() and not inside.all(), "the fixture stopped gating anything"
    np.testing.assert_array_equal(excluded, ~inside)


def test_a_region_on_parameters_that_are_not_the_axes_still_gates(manager):
    """The gate is on 3 and 4; the plot shows 0 and 1.

    A column-subset optimisation used to drop any gate whose parameters were not
    among the axes being drawn, on the reasoning that it did not need those
    columns. It does: the gate still decides which points are shown, it just
    decides it using columns that are off screen.
    """
    gate = RegionDataSelection(RectangleROI(2.0, 2.0, 5.0, 5.0), 3, 4)
    manager.mask_state = MaskState(selections=(gate,), axis_indices=(0, 1, 2))
    excluded = manager.get_value_mask()

    values = manager.data_source.values
    inside = ((values[3] >= 2.0) & (values[3] < 5.0) &
              (values[4] >= 2.0) & (values[4] < 5.0))
    assert inside.any() and not inside.all()
    np.testing.assert_array_equal(excluded, ~inside)


def test_toggling_a_region_gate_in_place_invalidates_the_cache(manager):
    """The selection table edits a gate rather than replacing it.

    The mask cache compares selections with ``==``, so without a real
    ``__eq__`` on the region a toggled ``enabled`` flag looked like no change at
    all and the plot kept the previous population.
    """
    gate = RegionDataSelection(RectangleROI(2.0, 2.0, 5.0, 5.0), 0, 1)
    manager.mask_state = MaskState(selections=(gate,), axis_indices=(0, 1, 2))
    gated = manager.get_value_mask().copy()
    assert gated.any()

    gate.enabled = False
    manager.mask_state = MaskState(selections=(gate,), axis_indices=(0, 1, 2))
    assert not manager.get_value_mask().any()

    gate.enabled = True
    manager.mask_state = MaskState(selections=(gate,), axis_indices=(0, 1, 2))
    np.testing.assert_array_equal(manager.get_value_mask(), gated)
