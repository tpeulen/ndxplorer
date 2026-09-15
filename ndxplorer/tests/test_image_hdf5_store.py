"""An image table written by chisurf, loaded as a store.

The short path, and the one the imaging work is for: chisurf writes a columnar
HDF5 -- one dataset per column -- and ndXplorer reads it straight into the
``tttrlib.DataStore`` it evaluates gates in and fills histograms out of. No
DataFrame is built on the way, so nothing is copied and no column is widened.

The realistic file is made by ``tools/make_image_hdf5.py`` from a CLSM
measurement; this builds a small one of the same shape so the path is tested
without needing the data.
"""

import numpy as np
import pytest
import tttrlib

from ndxplorer.core.data_source import DataSource, RectangularDataSelection
from ndxplorer.io.reader import read_hdf5_store, read_mfd_hdf5

pytestmark = pytest.mark.skipif(not tttrlib.hdf5_table_available(),
                                reason="tttrlib built without HDF5")

NX = NY = 16
N_FRAMES = 3


@pytest.fixture
def image_file(tmp_path):
    """A miniature of what ``make_image_hdf5.py`` writes."""
    rng = np.random.default_rng(2)
    frame, y, x = np.indices((N_FRAMES, NY, NX))
    n = frame.size
    counts = rng.integers(0, 40, n).astype(np.int32)
    tau = rng.uniform(1.0, 5.0, n)
    # A parameter map is full of holes: a pixel with too few photons has no
    # lifetime, and the file has to be able to say so.
    tau[counts < 5] = np.nan

    store = tttrlib.DataStore("image")
    store.set_n_rows(n)
    store.add("x pixel", x.ravel().astype(np.int32))
    store.add("y pixel", y.ravel().astype(np.int32))
    store.add("Frame", frame.ravel().astype(np.int32))
    store.add("Number of Photons", counts)
    store.add("Tau (green)", tau).mask_non_finite()
    store.add("Sg/Sr", rng.uniform(0.1, 9.0, n).astype(np.float32))

    path = tmp_path / "image.h5"
    assert tttrlib.write_hdf5(str(path), store)
    return path


def test_the_file_becomes_a_store_with_no_frame_built(image_file):
    source = read_mfd_hdf5([str(image_file)])
    assert source.size == N_FRAMES * NY * NX
    assert source.n_parameters == 6
    # The DataFrame is what the equation engine and the table editor need. The
    # load path does not, and building one would be a full copy of the table.
    assert source._data is None


def test_the_column_types_are_the_ones_that_were_written(image_file):
    store = read_hdf5_store(image_file)
    assert [store.column(i).dtype for i in range(4)] == \
        ["int32", "int32", "int32", "int32"]
    assert store["Tau (green)"].dtype == "float64"
    assert store["Sg/Sr"].dtype == "float32"


def test_a_pixel_with_no_lifetime_says_so(image_file):
    """NaN is not a lifetime of zero at the bottom of the axis -- it is a pixel
    that was not measured, and the store carries that as a validity bit."""
    source = read_mfd_hdf5([str(image_file)])
    tau = source.store["Tau (green)"]
    valid = tau.mask_numpy()
    assert valid is not None
    assert not valid.all() and valid.any()
    assert np.all(np.isnan(tau.numpy()[~valid]))


def test_gating_and_histogramming_the_loaded_store(image_file):
    """What the file is for: the store it becomes is the one the plot uses."""
    source = read_mfd_hdf5([str(image_file)])
    counts_idx = source.column_index("Number of Photons")
    keep = source.selection_mask(
        [RectangularDataSelection(counts_idx, 10.0, 30.0)])
    counts = source.column_view(counts_idx)
    np.testing.assert_array_equal(keep, (counts >= 10) & (counts <= 30))

    source.store.select(keep)
    image = source.store.profile(
        source.column_index("x pixel"), source.column_index("y pixel"),
        sample=source.column_index("Tau (green)"),
        bins=[NX, NY], range=[(0.0, NX), (0.0, NY)])
    mean = np.asarray(image.mean())
    assert mean.shape == (NX, NY)
    # A NaN sample must not poison its pixel: Welford's update is recursive, so
    # one bad row would leave the bin NaN for every row after it.
    assert np.all(np.isfinite(mean))
    source.store.select_all()


def test_a_pandas_table_is_not_mistaken_for_a_columnar_one(tmp_path):
    """``read_hdf5_store`` says None rather than raising, so the caller can read
    the file the long way without catching anything."""
    pd = pytest.importorskip("pandas")
    path = tmp_path / "pandas.h5"
    pd.DataFrame({"a": [1.0, 2.0], "b": [3.0, 4.0]}).to_hdf(path, key="results")
    store = read_hdf5_store(path)
    assert store is None or store.n_columns() == 0


def test_a_slashed_column_name_survives(image_file):
    source = read_mfd_hdf5([str(image_file)])
    assert "Sg/Sr" in source.parameter_names
    assert source.column_index("Sg/Sr") >= 0
    assert source.column_view(source.column_index("Sg/Sr")) is not None


def test_the_frame_is_materialised_only_when_asked_for(image_file):
    source = read_mfd_hdf5([str(image_file)])
    assert source._data is None
    frame = source.data
    assert list(frame.columns) == source.parameter_names
    assert len(frame) == source.size
