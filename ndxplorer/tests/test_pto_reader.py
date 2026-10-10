"""Reading `.pto` containers with tttrlib: bursts, companions, images, provenance."""
import numpy as np
import pytest
import tttrlib

from ndxplorer.io.pto_reader import read_container


def _table(**columns):
    store = tttrlib.DataStore()
    for name, values in columns.items():
        store.add(name, np.asarray(values, dtype=float))
    return store


def _add(handle, kind, name, store, *, grain, operation, parents=(), settings=None):
    uid = tttrlib.pto_add_store(handle, kind, name, store)
    tttrlib.pto_describe(handle, uid, data_format="dstore", row_grain=grain,
                         operation_type=operation, parameters=settings,
                         run=tttrlib.pto_settings_hash(settings), derived_from=parents,
                         software="test 1")
    return uid


@pytest.fixture()
def container(tmp_path):
    path = tmp_path / "m.pto"
    handle = tttrlib.PtoFile()
    assert handle.create(str(path), "test")
    yield path, handle
    if handle.is_open():
        handle.close()


def _close(handle):
    assert handle.commit()
    handle.close()


def test_an_interleaved_burst_table_and_its_companion(container):
    path, handle = container
    photons = handle.add("tttr_photon_stream", "ptu", "m.ptu", b"raw")
    # the legacy .bur layout: 2N+1 rows, zero rows between the bursts
    bursts = _table(**{"Number of Photons": [0, 50, 0, 70, 0],
                       "Mean Macro Time (ms)": [0, 1500.0, 0, 2500.0, 0]})
    search = _add(handle, "burst_table", "run/bi4_bur/m.bur", bursts, grain="burst",
                  operation="burst_selection", parents=[photons], settings={"L": 60})
    lifetimes = _add(handle, "burst_table", "run/bg4/m.bg4",
                     _table(**{"Tau (green)": [3.1, 3.9]}), grain="burst",
                     operation="burst_lifetime_fitting", parents=[search])
    _close(handle)

    source = read_container(path)
    assert source.size == 2
    store = source.store
    names = [store.column(i).name() for i in range(store.n_columns())]
    assert names == ["Number of Photons", "Tau (green)", "Mean Macro Time (s)"]
    assert list(store.column(2).numpy()) == [1.5, 2.5]
    provenance = source.provenance
    assert provenance["sources"][0]["name"] == "m.ptu"
    assert provenance["operations"]["burst_selection"] == {"L": 60}
    assert {"source": photons, "target": search, "type": "derived_from"} in provenance["edges"]
    assert {"source": search, "target": lifetimes, "type": "companion_of"} in provenance["edges"]


def test_a_measurement_without_bursts_opens_as_its_image(container):
    path, handle = container
    rng = np.random.default_rng(0)
    image = _table(**{"X pixel": np.repeat(np.arange(4.0), 3),
                      "Y pixel": np.tile(np.arange(3.0), 4), "Tau": rng.normal(3, 0.2, 12)})
    _add(handle, "pixel_map", "flim map", image, grain="pixel",
         operation="pixel_lifetime_fitting")
    _close(handle)

    source = read_container(path)
    assert source.size == 12
    assert source.provenance["artifacts"]
    (artifact,) = source.provenance["artifacts"].values()
    assert artifact["row_grain"] == "pixel" and artifact["name"] == "flim map"


def test_a_named_table_is_read_whatever_its_grain(container):
    path, handle = container
    _add(handle, "burst_table", "bursts", _table(n=[1.0, 2.0]), grain="burst",
         operation="burst_selection")
    _add(handle, "pixel_map", "map", _table(x=[1.0, 2.0, 3.0]), grain="pixel",
         operation="pixel_lifetime_fitting")
    _close(handle)
    assert read_container(path).size == 2
    assert read_container(path, table="map").size == 3


def test_an_empty_container_says_what_is_missing(container):
    path, handle = container
    _close(handle)
    with pytest.raises(FileNotFoundError, match="no burst or image table"):
        read_container(path)


def test_list_tables_offers_every_burst_search_and_read_takes_the_chosen_one(container):
    from ndxplorer.io.pto_reader import list_tables

    path, handle = container
    photons = handle.add("tttr_photon_stream", "ptu", "m.ptu", b"raw")
    for run, threshold, photons_per_burst in (("a#60", 60, [60.0, 61.0]),
                                              ("b#30", 30, [30.0, 31.0, 32.0])):
        _add(handle, "burst_table", f"{run}/bi4_bur/m.bur",
             _table(**{"Number of Photons": photons_per_burst}), grain="burst",
             operation="burst_selection", parents=[photons], settings={"L": threshold})
    # a per-burst result is a companion, not something to open on its own
    _add(handle, "burst_table", "bva", _table(**{"Proximity Ratio Mean": [0.1, 0.2, 0.3]}),
         grain="burst", operation="burst_variance_analysis", parents=[photons],
         settings={"w": 5})
    _close(handle)

    found = list_tables(path)
    assert [t["name"] for t in found] == ["a#60/bi4_bur/m.bur", "b#30/bi4_bur/m.bur"]
    assert [t["rows"] for t in found] == [2, 3]
    assert [t["run"] for t in found] == ["a#60", "b#30"]
    assert "Number of Photons" in found[0]["columns"]
    assert read_container(path, table=found[0]["name"]).size == 2
    assert read_container(path).size == 3          # no choice: the newest, as before
