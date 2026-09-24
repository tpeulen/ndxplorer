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
