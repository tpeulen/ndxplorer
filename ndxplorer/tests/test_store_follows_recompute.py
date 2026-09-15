"""A constant edit reaches the store, which is what the picture is made of.

Gates are evaluated in the store and histograms fill out of it, so a derived
column has to be rewritten there -- in place, at its position -- whenever a
constant it depends on changes.
"""

from __future__ import annotations

import numpy as np

from ndxplorer.core.data_source import DataSource, RectangularDataSelection

EQUATIONS = [
    {"Fg": "'Sg' - 'Bg'"},
    {"E": "'Fg' / ('Fg' + 'Sr')"},
]
CONSTANTS = {"Bg": 1.0}
N = 64


def _source(offset: float = 0.0) -> DataSource:
    return DataSource.from_columns({
        "Sg": np.linspace(10.0, 110.0, N) + offset,
        "Sr": np.full(N, 50.0),
    })


def _store_column(source: DataSource, name: str) -> np.ndarray:
    store = source.store
    for i in range(store.n_columns()):
        if store.column(i).name() == name:
            return np.asarray(store.column(i).numpy(), dtype=float)
    raise AssertionError(f"{name} is not in the store")


def _expected_e(bg: float, offset: float = 0.0) -> np.ndarray:
    fg = np.linspace(10.0, 110.0, N) + offset - bg
    return fg / (fg + 50.0)


def test_a_changed_constant_reaches_the_store():
    """The regression, in the shape the user meets it."""
    ds = _source()
    ds.compute_columns(constants=CONSTANTS, equations=EQUATIONS)
    before = _store_column(ds, "E").copy()

    ds.compute_columns(constants={"Bg": 40.0}, equations=EQUATIONS,
                       changed_constants={"Bg"})

    after = _store_column(ds, "E")
    assert not np.allclose(before, after), "the store kept the old values"
    np.testing.assert_allclose(after, _expected_e(40.0), rtol=1e-12)


def test_the_store_follows_every_edit():
    ds = _source()
    ds.compute_columns(constants=CONSTANTS, equations=EQUATIONS)
    positions = list(ds.parameter_names)
    for bg in (2.0, 15.0, 40.0, 0.5):
        ds.compute_columns(constants={"Bg": bg}, equations=EQUATIONS,
                           changed_constants={"Bg"})
        np.testing.assert_allclose(
            _store_column(ds, "E"), _expected_e(bg), rtol=1e-12,
            err_msg=f"store is stale at Bg={bg}",
        )
        assert ds.parameter_names == positions, "a recompute moved a column"


def test_replacing_the_store_replaces_the_table():
    ds = _source()
    ds.compute_columns(constants=CONSTANTS, equations=EQUATIONS)
    version = ds.data_version

    ds.replace_store(_source(offset=1000.0).store)
    np.testing.assert_allclose(
        _store_column(ds, "Sg"), np.linspace(10.0, 110.0, N) + 1000.0)
    assert ds.parameter_names == ["Sg", "Sr"]
    assert ds.data_version > version


def test_a_new_column_is_appended_after_the_gate_scratch_is_dropped():
    """A gate may append scratch columns; an equation output still lands at
    the next parameter position, not after the scratch."""
    ds = _source()
    ds.compute_columns(constants=CONSTANTS, equations=EQUATIONS[:1])
    from ndxplorer.core.data_source import Gaussian2DSelection
    ds.selection_mask([Gaussian2DSelection(0, 1, mu=[50.0, 50.0],
                                           cov=[[100.0, 0.0], [0.0, 100.0]],
                                           log_x=True)])
    assert ds.store.n_columns() > ds.n_parameters

    ds.compute_columns(constants=CONSTANTS, equations=EQUATIONS,
                       changed_constants={"Bg"})
    assert ds.parameter_names == ["Sg", "Sr", "Fg", "E"]
    np.testing.assert_allclose(ds.column_view(3), _expected_e(1.0), rtol=1e-12)


def test_a_gate_sees_the_recomputed_column():
    ds = _source()
    ds.compute_columns(constants=CONSTANTS, equations=EQUATIONS)
    index = ds.column_index("E")
    gate = RectangularDataSelection(index, 0.0, 0.5)
    kept_before = int(ds.selection_mask([gate]).sum())

    ds.compute_columns(constants={"Bg": 40.0}, equations=EQUATIONS,
                       changed_constants={"Bg"})
    kept_after = int(ds.selection_mask([gate]).sum())
    e = _expected_e(40.0)
    assert kept_after == int(np.count_nonzero((e >= 0.0) & (e <= 0.5)))
    assert kept_after != kept_before
