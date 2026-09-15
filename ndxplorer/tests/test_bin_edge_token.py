"""What a bin-edge token has to separate, and what it must not.

:func:`bins_token` fingerprints an array of bin edges. Its one remaining caller
is :meth:`BitmapSelection.gate_key`: a painted cell means "these data values",
and which values it covers is decided by the edges, so a gate key that cannot
tell two edge arrays apart keeps selecting a population the mask no longer
covers -- a wrong picture with no error anywhere, and every number under the
plot agreeing with it.

The collision covered here shipped. ``get_bins`` builds a log axis with
``logspace(log10(lo), log10(hi), n+1)`` and a linear one with
``linspace(lo, hi, n+1)``. Those agree on count, first edge and last edge --
which were the whole key -- so switching an axis to log changed nothing the key
could see. The middle edge separates them, and it separates any two monotone
spacings over the same endpoints, which is the general form of the problem.

The histogram *cache* this file was originally written for is gone: a fill
costs a few milliseconds, less than deciding whether a cached one is still
valid, and for a picture the only cache worth having is one that cannot be
wrong. The recompute-gate tests went with it; what a redraw depends on is now
one :class:`~ndxplorer.utils.histogram_computation.Axis` per axis, covered in
``test_log_binning``.
"""

from __future__ import annotations

import numpy as np
import pytest

from ndxplorer.utils.histogram_helpers import bins_token, get_bins


def test_a_log_axis_and_a_linear_one_are_not_the_same_bins():
    """The collision that left a log plot gated against linear bins."""
    linear, _ = get_bins(None, (1.0, 100.0), "linear", 50, 60)
    logarithmic, _ = get_bins(None, (1.0, 100.0), "log", 50, 60)

    # Same count, same endpoints -- which is exactly why (count, first, last)
    # could not tell them apart.
    assert linear.size == logarithmic.size
    assert linear[0] == logarithmic[0] and linear[-1] == logarithmic[-1]
    assert not np.allclose(linear, logarithmic)

    assert bins_token(linear) != bins_token(logarithmic)


def test_the_same_bins_always_give_the_same_token():
    """Otherwise a gate is rebuilt on every redraw."""
    first, _ = get_bins(None, (0.0, 5.0), "linear", 128, 128)
    second, _ = get_bins(None, (0.0, 5.0), "linear", 128, 128)
    assert bins_token(first) == bins_token(second)
    assert bins_token(first) == bins_token(first.copy())


@pytest.mark.parametrize(
    "left, right",
    [
        # more bins over the same range
        (np.linspace(0.0, 1.0, 11), np.linspace(0.0, 1.0, 21)),
        # same count, shifted range
        (np.linspace(0.0, 1.0, 11), np.linspace(0.5, 1.5, 11)),
        # same endpoints and count, different interior spacing
        (np.linspace(1.0, 100.0, 51), np.logspace(0.0, 2.0, 51)),
        # a hand-built axis that only differs in the middle
        (np.array([0.0, 1.0, 2.0, 9.0]), np.array([0.0, 1.0, 5.0, 9.0])),
    ],
)
def test_different_bins_give_different_tokens(left, right):
    assert bins_token(left) != bins_token(right)


def test_an_empty_axis_has_a_token_rather_than_raising():
    assert bins_token(np.array([])) == "0"


def test_the_token_never_truncates():
    """``str(numpy_array)`` was the obvious spelling and the wrong one.

    It costs a full ``array2string`` pass and it *truncates* long arrays with
    ``"..."``, so distinct bin sets collide. The token reads four numbers out
    of the array and never walks it.
    """
    big = np.linspace(0.0, 1.0, 1_000_001)
    token = bins_token(big)
    assert "..." not in token
    assert token == bins_token(np.linspace(0.0, 1.0, 1_000_001))
    assert token != bins_token(np.linspace(0.0, 1.0, 1_000_000))


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-q"])
