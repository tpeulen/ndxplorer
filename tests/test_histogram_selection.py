"""Gating a :class:`DataSource` with a 1-D interval.

This file used to be module-level statements: it built its data, gated it and
asserted, all at import time, with no test function. pytest ran it during
*collection*, so a failure was reported as a collection error rather than a
failing test — and it had been failing, because the data was passed in the
wrong orientation.

A :class:`DataSource` holds one **column per parameter**;
:meth:`DataSource.get_mask` answers ``(n_parameters, n_points)``, the shape a
:class:`DataSelection` works in.
"""

from __future__ import annotations

import numpy as np
import pytest

from ndxplorer.core.data_source import DataSource, RectangularDataSelection

#: Two parameters, five points, both clustered tightly around 4.
N_POINTS = 5


@pytest.fixture
def source():
    rng = np.random.default_rng(0)
    return DataSource.from_columns({
        "x": rng.normal(4.0, 0.1, N_POINTS),
        "y": rng.normal(4.0, 0.1, N_POINTS),
    })


def test_the_mask_is_parameter_major(source):
    selection = RectangularDataSelection(0, 3.95, 4.05, False, True)
    mask = source.get_mask([selection])

    assert mask.shape == (2, N_POINTS)
    assert mask.dtype == bool


def test_an_interval_keeps_the_points_inside_it(source):
    inside = source.get_mask([RectangularDataSelection(0, 3.0, 5.0, False, True)])
    assert not inside.any(), "a wide interval excludes nothing"

    outside = source.get_mask([RectangularDataSelection(0, 100.0, 200.0, False, True)])
    assert outside.all(), "an interval far from the data excludes everything"


def test_a_disabled_selection_excludes_nothing(source):
    mask = source.get_mask([RectangularDataSelection(0, 100.0, 200.0, False, False)])
    assert not mask.any()
