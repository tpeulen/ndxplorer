"""A constant edit has to reach the *picture*, not only the table.

The store is a second copy of every column: gates are evaluated in it and
histograms fill out of it. ``compute_columns`` used to refresh the DataFrame and
``_data_numeric`` and leave the store on the previous values, so editing a
correction factor moved every derived FRET column and left the histogram
bit-identical — a plot disagreeing with its own numbers, with nothing anywhere
saying so.

The same hole swallowed a whole-table replacement: the store is derived from the
table and addresses its columns by *position*, so a new table has to drop it.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ndxplorer.core.data_source import DataSource

EQUATIONS = [
    {"Fg": "'Sg' - 'Bg'"},
    {"E": "'Fg' / ('Fg' + 'Sr')"},
]
CONSTANTS = {"Bg": 1.0}
N = 64


def _frame(offset: float = 0.0) -> pd.DataFrame:
    return pd.DataFrame({
        "Sg": np.linspace(10.0, 110.0, N) + offset,
        "Sr": np.full(N, 50.0),
    })


def _store_column(source: DataSource, name: str) -> np.ndarray:
    store = source.store
    for i in range(store.n_columns()):
        if store.column(i).name() == name:
            return np.asarray(store.column(i).numpy(), dtype=float)
    raise AssertionError(f"{name} is not in the store")


def test_a_changed_constant_reaches_the_store():
    """The regression, in the shape the user meets it."""
    ds = DataSource(data=_frame())
    ds.compute_columns(constants=CONSTANTS, equations=EQUATIONS)
    before = _store_column(ds, "E").copy()

    ds.compute_columns(constants={"Bg": 40.0}, equations=EQUATIONS,
                       changed_constants={"Bg"})

    table = np.asarray(ds.data["E"], dtype=float)
    after = _store_column(ds, "E")
    assert not np.allclose(before, after), "the store kept the old values"
    np.testing.assert_allclose(after, table, rtol=1e-5)


def test_the_store_agrees_with_the_table_after_every_edit():
    ds = DataSource(data=_frame())
    ds.compute_columns(constants=CONSTANTS, equations=EQUATIONS)
    for bg in (2.0, 15.0, 40.0, 0.5):
        ds.compute_columns(constants={"Bg": bg}, equations=EQUATIONS,
                           changed_constants={"Bg"})
        np.testing.assert_allclose(
            _store_column(ds, "E"),
            np.asarray(ds.data["E"], dtype=float),
            rtol=1e-5,
            err_msg=f"store and table disagree at Bg={bg}",
        )


def test_replacing_the_table_drops_the_store():
    """Positional addressing: a new table cannot reuse the old store."""
    ds = DataSource(data=_frame())
    ds.compute_columns(constants=CONSTANTS, equations=EQUATIONS)
    first = _store_column(ds, "Sg").copy()

    ds.data = _frame(offset=1000.0)
    second = _store_column(ds, "Sg")
    assert not np.allclose(first, second), "the store survived a table replacement"
    np.testing.assert_allclose(
        second, np.asarray(ds.data["Sg"], dtype=float), rtol=1e-5)


def test_a_new_column_rebuilds_rather_than_patches():
    """A recompute that *adds* a column cannot be written in by position."""
    ds = DataSource(data=_frame())
    ds.compute_columns(constants=CONSTANTS, equations=EQUATIONS[:1])
    ds.store  # materialise a store that has no "E" column
    ds.compute_columns(constants=CONSTANTS, equations=EQUATIONS,
                       changed_constants={"Bg"})
    np.testing.assert_allclose(
        _store_column(ds, "E"), np.asarray(ds.data["E"], dtype=float), rtol=1e-5)
