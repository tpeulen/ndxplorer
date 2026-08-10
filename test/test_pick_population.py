"""Clicking a population is a third way to make a gate, and it is the shared one.

ndXplorer could draw a gate by hand or fit a mixture over the whole plane.
Neither is what someone does when they can see the population they mean. This
covers the gesture — and, more importantly, that it is the *same* gesture the
imaging side offers: one re-centring fit, one covariance-to-ellipse conversion,
one region type, so a gate picked here and a region picked on a frame agree
about what an ellipse is.
"""

from __future__ import annotations

import numpy as np
import pytest

from ndxplorer.core.region_selection import RegionDataSelection, pick_population

A_MU, A_COV = (10.0, 4.0), [[1.0, 0.6], [0.6, 0.5]]
B_MU, B_COV = (20.0, 9.0), [[2.0, 0.0], [0.0, 0.4]]


def _two_populations(n=3000, seed=3):
    """Return ``(2, N)`` points from two well-separated populations."""
    rng = np.random.default_rng(seed)
    a = rng.multivariate_normal(A_MU, A_COV, size=n)
    b = rng.multivariate_normal(B_MU, B_COV, size=n)
    return np.vstack([a, b]).T


def test_a_click_on_the_shoulder_still_gates_the_population():
    """The whole point of fitting rather than dropping a circle on the cursor."""
    data = _two_populations()

    selection, reason = pick_population(data, (0, 1), 11.0, 4.5, radius=3.0)

    assert selection is not None, reason
    assert selection.roi.cx == pytest.approx(A_MU[0], abs=0.3)
    assert selection.roi.cy == pytest.approx(A_MU[1], abs=0.3)


def test_the_gate_is_tilted_the_way_the_population_is():
    """A correlated population gated by an axis-aligned ellipse is a different gate."""
    data = _two_populations()

    selection, _ = pick_population(data, (0, 1), 10.0, 4.0, radius=3.0)

    assert selection.roi.angle != 0.0
    # The long axis follows the positive correlation of A_COV.
    assert selection.roi.rx > selection.roi.ry


def test_picking_one_population_excludes_the_other():
    """A gate that keeps everything is not a gate."""
    data = _two_populations()

    selection, _ = pick_population(data, (0, 1), 10.0, 4.0, radius=3.0)
    excluded = selection.get_mask(data)[0]

    # Half the points are the other population, and a 2-sigma ellipse gives up
    # the tails of this one: a little over half excluded, nowhere near all.
    assert 0.5 < excluded.mean() < 0.7
    # And the points it keeps are the ones near A.
    kept = data[:, ~excluded]
    assert kept[0].mean() == pytest.approx(A_MU[0], abs=0.3)


def test_clicking_the_other_population_gates_the_other_one():
    data = _two_populations()

    selection, reason = pick_population(data, (0, 1), 20.5, 9.2, radius=3.0)

    assert selection is not None, reason
    assert selection.roi.cx == pytest.approx(B_MU[0], abs=0.3)
    assert selection.roi.cy == pytest.approx(B_MU[1], abs=0.3)


def test_a_click_on_empty_space_is_refused_with_a_reason():
    """A gate fitted to nothing would silently keep or drop everything."""
    data = _two_populations()

    selection, reason = pick_population(data, (0, 1), 40.0, 40.0, radius=1.0)

    assert selection is None
    assert "point" in reason


def test_a_plane_that_does_not_exist_is_refused():
    data = _two_populations()

    selection, reason = pick_population(data, (0, 9), 10.0, 4.0, radius=3.0)

    assert selection is None
    assert "no parameters" in reason


def test_the_result_is_an_ordinary_region_gate():
    """Picked, drawn or loaded from a file, a gate is one kind of object."""
    data = _two_populations()

    selection, _ = pick_population(data, (0, 1), 10.0, 4.0, radius=3.0, name="A")

    assert isinstance(selection, RegionDataSelection)
    assert selection.name == "A"
    assert selection.shape == "ellipse"
    # And it survives the round trip every other selection takes.
    from chisurf.core.roi import RegionCollection

    collection = RegionCollection(combine="and", name="gates")
    collection.add(selection.roi)
    rebuilt = RegionCollection.from_dict(collection.to_dict())
    assert len(rebuilt) == 1
    assert rebuilt[0].roi.cx == pytest.approx(selection.roi.cx)


def test_the_radius_decides_how_much_of_the_cloud_is_one_population():
    """A density has no edge; the capture radius is a setting and says so."""
    data = _two_populations()

    tight, _ = pick_population(data, (0, 1), 10.0, 4.0, radius=1.0)
    loose, _ = pick_population(data, (0, 1), 10.0, 4.0, radius=4.0)

    assert tight is not None and loose is not None
    assert loose.roi.rx > tight.roi.rx
