"""Clicking a population is a third way to make a gate, beside dragging one
and fitting a mixture over the whole plane.

The fit is :func:`ndxplorer.core.population_pick.fit_population`, shared by the
Qt window and the emtk app. It finds the population on a density grid in
display-scaled units (climb to the local maximum, grow downhill to a fraction
of the peak) and returns a 2-D Gaussian in gate space, which becomes a
:class:`Gaussian2DSelection` gate.
"""

from __future__ import annotations

import numpy as np
import pytest

from ndxplorer.core.data_source import Gaussian2DSelection
from ndxplorer.core.population_pick import fit_population

A_MU, A_COV = (10.0, 4.0), [[1.0, 0.6], [0.6, 0.5]]
B_MU, B_COV = (20.0, 9.0), [[2.0, 0.0], [0.0, 0.4]]
X_RANGE, Y_RANGE = (0.0, 30.0), (0.0, 14.0)


def _two_populations(n=3000, seed=3):
    """Return ``(2, N)`` points from two well-separated populations."""
    rng = np.random.default_rng(seed)
    a = rng.multivariate_normal(A_MU, A_COV, size=n)
    b = rng.multivariate_normal(B_MU, B_COV, size=n)
    return np.vstack([a, b]).T


def _pick(data, x, y, **kw):
    return fit_population(data[0], data[1], (x, y), X_RANGE, Y_RANGE, **kw)


def _gate(fit):
    return Gaussian2DSelection(0, 1, fit.mu, fit.cov, sigma=2.0, name="picked")


def test_a_click_on_the_shoulder_still_gates_the_population():
    """The whole point of fitting rather than dropping a circle on the cursor."""
    fit = _pick(_two_populations(), 11.0, 4.5)
    assert fit.success, fit.reason
    assert fit.mu == pytest.approx(A_MU, abs=0.3)


def test_the_gate_is_tilted_the_way_the_population_is():
    """A correlated population gated by an axis-aligned ellipse is a different gate."""
    fit = _pick(_two_populations(), 10.0, 4.0)
    assert fit.cov[0, 1] > 0.3                      # the positive correlation of A_COV
    assert fit.cov == pytest.approx(np.array(A_COV), rel=0.3, abs=0.1)


def test_picking_one_population_excludes_the_other():
    """A gate that keeps everything is not a gate."""
    data = _two_populations()
    excluded = _gate(_pick(data, 10.0, 4.0)).get_mask(data)[0]
    # Half the points are the other population, and a 2-sigma ellipse gives up
    # the tails of this one: a little over half excluded, nowhere near all.
    assert 0.5 < excluded.mean() < 0.7
    kept = data[:, ~excluded]
    assert kept[0].mean() == pytest.approx(A_MU[0], abs=0.3)


def test_clicking_the_other_population_gates_the_other_one():
    fit = _pick(_two_populations(), 20.5, 9.2)
    assert fit.success, fit.reason
    assert fit.mu == pytest.approx(B_MU, abs=0.3)


def test_a_click_on_empty_space_is_refused_with_a_reason():
    """A gate fitted to nothing would silently keep or drop everything."""
    data = _two_populations()
    fit = fit_population(data[0], data[1], (45.0, 45.0), (0.0, 50.0), (0.0, 50.0))
    assert not fit.success and "point" in fit.reason


def test_a_click_outside_the_plotted_range_is_refused():
    fit = _pick(_two_populations(), 40.0, 4.0)
    assert not fit.success and "outside" in fit.reason


def test_how_far_down_the_peak_reaches_decides_how_many_points_it_is_fitted_from():
    """A density has no edge: the cut is a setting. The width is corrected for it,
    so a tight and a loose pick describe the same population."""
    data = _two_populations()
    tight = _pick(data, 10.0, 4.0, level=0.6)
    loose = _pick(data, 10.0, 4.0, level=0.15)
    assert tight.success and loose.success
    assert loose.n_points > tight.n_points
    assert tight.cov[0, 0] == pytest.approx(loose.cov[0, 0], rel=0.3)
