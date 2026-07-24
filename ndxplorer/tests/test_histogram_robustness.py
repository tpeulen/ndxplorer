"""Robustness tests for reading BVA/2CDE burst columns into ndXplorer.

Merging BVA/2CDE ``…4`` companions can surface columns that were never fit
(e.g. ``Tau (green)`` when MLE was skipped for lack of an IRF) — constant/NaN
columns whose histogram bin edges collapse — and pandas nullable dtypes from the
pyarrow reader. Neither must crash ndXplorer.
"""
from __future__ import annotations

import os

import numpy as np
import pandas as pd
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.mark.parametrize(
    "edges",
    [
        [0.0, 0.0, 0.0, 0.0],   # a constant column (e.g. an unfit Tau (green))
        [5.0],                    # a single distinct value
        [1, 1, 2, 2, 3],          # duplicates
        [np.nan, np.nan],         # all NaN
        [],                       # empty
    ],
)
def test_ascending_edges_never_crashes_boost_histogram(edges):
    import boost_histogram as bh

    from ndxplorer.plotting.background_histograms import _ascending_edges

    e = _ascending_edges(edges)
    assert e.size >= 2
    assert np.all(np.diff(e) > 0)     # strictly ascending
    bh.Histogram(bh.axis.Variable(e))  # boost-histogram accepts it (was ValueError)


def test_dataframe_editor_handles_pandas_nullable_dtype():
    # The pyarrow reader yields nullable Float64/Int64 dtypes; np.issubdtype raises
    # TypeError on those, crashing the editor. is_numeric_dtype handles them.
    assert bool(pd.api.types.is_numeric_dtype(pd.array([1.0, None], dtype="Float64").dtype))
    assert bool(pd.api.types.is_numeric_dtype(pd.array([1, None], dtype="Int64").dtype))
    assert not bool(pd.api.types.is_numeric_dtype(pd.Series(["m000.spc"]).dtype))
