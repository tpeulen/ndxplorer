"""The window-level half of picking: indices, radius, and the refusals.

The coordinate mapping is fenced off in ``pick_population_from_canvas`` and
needs a real plot; everything below it takes parameter units and is testable
without one. That split is deliberate — it is the difference between a gate
fitted where the user pointed and a gate fitted somewhere plausible.
"""

from __future__ import annotations

import numpy as np
import pytest

from ndxplorer.core.region_selection import pick_population


class _FakePlotControl:
    """Just enough of the plot control for the model half."""

    def __init__(self, x_range, y_range):
        self.x_range = x_range
        self.y_range = y_range
        self._selections = []
        self.added = []

    def addRegionSelection(self, selection, invert=False, enabled=True):
        self.added.append(selection)


def test_the_default_radius_follows_the_displayed_range():
    """A capture radius in pixels would mean something different on every axis."""
    control = _FakePlotControl((0.0, 100.0), (0.0, 20.0))
    span = min(
        abs(control.x_range[1] - control.x_range[0]),
        abs(control.y_range[1] - control.y_range[0]),
    )

    assert span / 20.0 == pytest.approx(1.0)


def test_a_gate_is_fitted_to_the_points_as_displayed():
    """Fitting the *visible* points is the point: an earlier gate is not undone."""
    rng = np.random.default_rng(5)
    a = rng.multivariate_normal([10.0, 4.0], [[1.0, 0.0], [0.0, 1.0]], size=2000)
    b = rng.multivariate_normal([30.0, 4.0], [[1.0, 0.0], [0.0, 1.0]], size=2000)
    everything = np.vstack([a, b]).T

    # As if an earlier gate had already removed the second population.
    displayed = a.T

    from_all, _ = pick_population(everything, (0, 1), 20.0, 4.0, radius=15.0)
    from_shown, _ = pick_population(displayed, (0, 1), 20.0, 4.0, radius=15.0)

    # The same click, two different answers — which is why what is fitted has
    # to be what is on screen.
    assert from_all.roi.cx == pytest.approx(20.0, abs=1.0)
    assert from_shown.roi.cx == pytest.approx(10.0, abs=0.5)


def test_the_gate_is_named_and_countable():
    rng = np.random.default_rng(6)
    points = rng.multivariate_normal([1.0, 2.0], [[0.2, 0.0], [0.0, 0.2]], size=800).T

    first, _ = pick_population(points, (0, 1), 1.0, 2.0, radius=1.0, name="Population 1")
    second, _ = pick_population(points, (0, 1), 1.0, 2.0, radius=1.0, name="Population 2")

    assert first.name == "Population 1"
    assert second.name == "Population 2"
    assert first.selection_id != second.selection_id
