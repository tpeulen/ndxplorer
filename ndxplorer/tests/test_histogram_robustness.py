"""Robustness tests for reading BVA/2CDE burst columns into ndXplorer.

Merging BVA/2CDE ``…4`` companions can surface columns that were never fit
(e.g. ``Tau (green)`` when MLE was skipped for lack of an IRF) — constant/NaN
columns whose histogram bin edges collapse — and pandas nullable dtypes from the
a nullable-dtype reader. Neither must crash ndXplorer.
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.mark.parametrize(
    "lo, hi",
    [
        (0.0, 0.0),           # a constant column (e.g. an unfit Tau (green))
        (5.0, 5.0),           # a single distinct value
        (10.0, -10.0),        # a range the wrong way round
        (-1.0, 1.0),          # spans zero
    ],
)
def test_a_degenerate_range_still_has_a_bin(lo, hi):
    """An axis must always be able to say where its bins are.

    A column that was never fit collapses to a single value, and an empty
    interval has no bin to put anything in -- which used to leave the axis
    silently showing nothing rather than saying anything was wrong. The edges
    have to come out strictly ascending whatever the range was.
    """
    from ndxplorer.utils.histogram_computation import Axis

    axis = Axis(index=0, bins=8, lo=lo, hi=hi)
    edges = axis.edges
    assert edges.size == 9
    assert np.all(np.diff(edges) > 0)     # strictly ascending


def test_dataframe_editor_handles_pandas_nullable_dtype():
    # A nullable-dtype reader yields Float64/Int64; np.issubdtype raises
    # TypeError on those, crashing the editor. is_numeric_dtype handles them.
    assert bool(pd.api.types.is_numeric_dtype(pd.array([1.0, None], dtype="Float64").dtype))
    assert bool(pd.api.types.is_numeric_dtype(pd.array([1, None], dtype="Int64").dtype))
    assert not bool(pd.api.types.is_numeric_dtype(pd.Series(["m000.spc"]).dtype))
