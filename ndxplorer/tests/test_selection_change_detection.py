"""Does the program notice when a gate changes?

Separate from ``test_selection_semantics.py``, which asks what a gate *means*.
This file asks the question one layer up: after the user edits a gate, does
anything downstream find out? The mask cache skips its work when a gate looks
unchanged, so a change token that misses an edit does not produce an error or a
stale-looking plot. It produces a plot of the **previous population** with the
new gate drawn on top of it, and a count under it that agrees, because both
came from the same skipped update.

Three things made that happen, and all three are pinned here:

* the token was built by dispatching on the class *name*, and mis-spelled
  ``Gaussian2DSelection`` as ``Gauss2DSelection``, so every ellipse fell through
  to ``str(sel)`` -- the object's memory address, which does not change when the
  object is edited in place;
* the bitmap branch of the same function used the construction-time uuid, while
  the brush paints into ``sel.mask`` in place;
* every selection class had a ``selection_id`` fast path in ``__eq__``, and that
  id is frozen at ``__init__`` and never mentioned ``cov`` or the log flags.

The tests below all **edit in place**, because that is what the selection table
does; a test that builds a second object instead cannot see any of this.
"""

from __future__ import annotations

import copy

import numpy as np
import pytest

from ndxplorer.core.data.mask_state import MaskState, gate_key
from ndxplorer.core.data_source import (Gaussian2DSelection, MaskDataSelection,
                                        RectangularDataSelection)


def _selection_token(selections):
    """What the mask cache compares: one key per gate, in order.

    This used to be ``plot_update_helpers._compute_selection_hash``, which
    hashed exactly this tuple for the histogram cache. That cache is gone and
    the function went with it; ``gate_key`` is the live thing, and comparing
    the keys themselves rather than a hash of them is what the mask cache does.
    """
    return tuple(gate_key(s) for s in selections)


@pytest.fixture
def interval():
    return RectangularDataSelection(0, 1.0, 5.0)


@pytest.fixture
def ellipse():
    return Gaussian2DSelection(0, 1, mu=[0.0, 0.0], cov=[[1.0, 0.0], [0.0, 1.0]],
                               sigma=2.0)


@pytest.fixture
def bitmap():
    edges = np.linspace(0.0, 1.0, 6)
    mask = np.zeros((5, 5), dtype=np.uint8)
    mask[0, 0] = 1
    return MaskDataSelection(0, 1, mask, edges, edges)


def _edits():
    """(fixture name, what the user did, the edit) for every gate kind."""
    return [
        ("interval", "moved the upper bound", lambda s: setattr(s, "upper", 9.0)),
        ("interval", "moved the lower bound", lambda s: setattr(s, "lower", -3.0)),
        ("interval", "inverted it", lambda s: setattr(s, "invert", True)),
        ("interval", "disabled it", lambda s: setattr(s, "enabled", False)),
        ("interval", "moved it to another parameter",
         lambda s: setattr(s, "parameter_idx", 4)),
        ("ellipse", "moved the centre", lambda s: setattr(s, "mu", np.array([3.0, 4.0]))),
        ("ellipse", "reshaped it",
         lambda s: setattr(s, "cov", np.array([[9.0, 0.0], [0.0, 0.25]]))),
        ("ellipse", "rotated it",
         lambda s: setattr(s, "cov", np.array([[1.0, 0.7], [0.7, 1.0]]))),
        ("ellipse", "resized it", lambda s: setattr(s, "sigma", 5.0)),
        ("ellipse", "inverted it", lambda s: setattr(s, "invert", True)),
        ("ellipse", "disabled it", lambda s: setattr(s, "enabled", False)),
        ("ellipse", "switched an axis to log", lambda s: setattr(s, "log_x", True)),
        ("bitmap", "painted more of it", lambda s: s.mask.__setitem__((3, 3), 1)),
        ("bitmap", "erased part of it", lambda s: s.mask.__setitem__((0, 0), 0)),
        ("bitmap", "inverted it", lambda s: setattr(s, "invert", True)),
        ("bitmap", "disabled it", lambda s: setattr(s, "enabled", False)),
        ("bitmap", "rebinned the axis",
         lambda s: setattr(s, "edges1", np.logspace(0.0, 2.0, 6))),
    ]


@pytest.mark.parametrize(
    "fixture_name, what, edit",
    _edits(),
    ids=[f"{name}-{what}" for name, what, _ in _edits()],
)
def test_an_edit_changes_the_gate_key(fixture_name, what, edit, request):
    """Every gate must announce every edit through ``gate_key``.

    A key that misses an edit is a gate that keeps evaluating as it was, so the
    plots go on showing a population the user has already changed.
    """
    selection = request.getfixturevalue(fixture_name)
    before = _selection_token([selection])
    edit(selection)
    assert _selection_token([selection]) != before, (
        f"the user {what} and the gate key did not notice")


@pytest.mark.parametrize(
    "fixture_name, what, edit",
    _edits(),
    ids=[f"{name}-{what}" for name, what, _ in _edits()],
)
def test_an_edit_changes_the_mask_cache_token(fixture_name, what, edit, request):
    selection = request.getfixturevalue(fixture_name)
    before = MaskState(selections=[selection]).key()
    edit(selection)
    assert MaskState(selections=[selection]).key() != before, (
        f"the user {what} and the mask cache did not notice")


@pytest.mark.parametrize(
    "fixture_name, what, edit",
    _edits(),
    ids=[f"{name}-{what}" for name, what, _ in _edits()],
)
def test_an_edited_gate_is_not_equal_to_its_pre_edit_self(fixture_name, what, edit,
                                                          request):
    selection = request.getfixturevalue(fixture_name)
    before = copy.deepcopy(selection)
    edit(selection)
    assert selection != before, f"the user {what} and the gate compared equal"


def test_an_untouched_gate_keeps_its_token(interval, ellipse, bitmap):
    """The other half of the contract: a token that changes every call is a
    cache that never hits, and the redraw cost was the reason for all of this."""
    for selection in (interval, ellipse, bitmap):
        assert _selection_token([selection]) == _selection_token([selection])
        assert gate_key(selection) == gate_key(selection)
        assert MaskState(selections=[selection]).key() == \
            MaskState(selections=[selection]).key()


def test_no_gates_has_a_token_too(interval):
    assert _selection_token([]) == _selection_token([])
    assert _selection_token([]) != _selection_token([interval])


def test_the_order_of_the_gates_is_part_of_the_token(interval, ellipse):
    """Not because AND cares about order, but because the table shows them in
    order and a reorder is an edit the user made."""
    assert _selection_token([interval, ellipse]) != \
        _selection_token([ellipse, interval])


def test_removing_a_gate_changes_the_token(interval, ellipse):
    assert _selection_token([interval, ellipse]) != \
        _selection_token([interval])


# --- the specific false-equalities that shipped ------------------------------


def test_two_differently_shaped_ellipses_are_not_the_same_gate():
    """``selection_id`` never mentioned ``cov``, so these compared equal."""
    round_one = Gaussian2DSelection(0, 1, mu=[0, 0], cov=[[1, 0], [0, 1]], sigma=2.0)
    elongated = Gaussian2DSelection(0, 1, mu=[0, 0], cov=[[9, 0], [0, 0.25]], sigma=2.0)
    assert round_one != elongated
    assert gate_key(round_one) != gate_key(elongated)


def test_a_log_scaled_ellipse_is_not_its_linear_twin():
    """``selection_id`` never mentioned ``log_x``/``log_y`` either, and the two
    are evaluated in different spaces."""
    linear = Gaussian2DSelection(0, 1, mu=[0, 0], cov=[[1, 0], [0, 1]], sigma=2.0)
    logged = Gaussian2DSelection(0, 1, mu=[0, 0], cov=[[1, 0], [0, 1]], sigma=2.0,
                                 log_x=True)
    assert linear != logged
    assert gate_key(linear) != gate_key(logged)


def test_a_painted_mask_on_a_log_axis_is_not_the_same_gate_as_on_a_linear_one():
    """The bitmap key used (count, first, last) of the bin edges, on which a
    linear and a log axis over the same range agree exactly -- while the gate
    they define selects different points."""
    linear_edges = np.linspace(1.0, 100.0, 6)
    log_edges = np.logspace(0.0, 2.0, 6)
    assert linear_edges.size == log_edges.size
    assert linear_edges[0] == log_edges[0] and linear_edges[-1] == log_edges[-1]

    painted = np.zeros((5, 5), dtype=np.uint8)
    painted[2, 2] = 1
    on_linear = MaskDataSelection(0, 1, painted.copy(), linear_edges, linear_edges)
    on_log = MaskDataSelection(0, 1, painted.copy(), log_edges, log_edges)

    # They really do gate differently ...
    probe = np.array([2.0, 20.0, 50.0])
    assert not np.array_equal(on_linear.inside(probe, probe),
                              on_log.inside(probe, probe))
    # ... so the key must say so.
    assert gate_key(on_linear) != gate_key(on_log)


def test_a_gate_with_no_gate_key_still_reduces_to_values():
    """The conservative fallback: an unrecognised selection is keyed by its type
    and flags, which recomputes too often rather than too rarely."""

    class Homemade:
        enabled = True
        invert = False

    one = Homemade()
    assert gate_key(one) == gate_key(one)
    one.invert = True
    assert gate_key(one)[2] is True
