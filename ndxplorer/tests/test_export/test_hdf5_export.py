"""
Tests for HDF5 export functionality (tttrlib columnar tables).
"""

from __future__ import annotations

import json
from pathlib import Path
import tempfile

import numpy as np
import pytest
import tttrlib

from ndxplorer.core.data_source import store_from_columns
from ndxplorer.export import hdf5_export
from ndxplorer.export.hdf5_export import (
    METADATA_ATTRIBUTE,
    VALUES_SHAPE_ATTRIBUTE,
    HDFBackendUnavailable,
    export_hdf5,
)
from ndxplorer.export.models import SelectionExportPayload

pytestmark = pytest.mark.skipif(not tttrlib.hdf5_table_available(),
                                reason="tttrlib built without HDF5")


class TestHDF5Export:
    """Test the columnar HDF5 export."""

    @pytest.fixture
    def payload(self) -> SelectionExportPayload:
        table = store_from_columns(
            {
                "x": np.arange(10, dtype=float),
                "y": np.random.random(10),
                "category": ["A", "B"] * 5,
            }
        )
        return SelectionExportPayload(
            selections=[{"name": "test"}],
            table=table,
            metadata={"experiment": "test"},
            name="sample",
        )

    def test_basic_export(self, payload: SelectionExportPayload) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "basic.h5"
            export_hdf5(payload, path)

            assert path.exists()
            loaded = tttrlib.read_hdf5(str(path))
            assert list(loaded.column_names()) == ["x", "y", "category"]
            np.testing.assert_array_equal(loaded["x"].numpy(), payload.table["x"].numpy())
            np.testing.assert_array_equal(loaded["y"].numpy(), payload.table["y"].numpy())
            assert list(loaded["category"].numpy()) == ["A", "B"] * 5

    def test_metadata_persisted(self, payload: SelectionExportPayload) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "meta.h5"
            export_hdf5(payload, path)

            loaded = tttrlib.read_hdf5(str(path))
            metadata = json.loads(loaded.column(0).attribute(METADATA_ATTRIBUTE))
            assert metadata["metadata"]["experiment"] == "test"

    def test_values_shape_attribute(self) -> None:
        values = np.random.random((3, 20))
        payload = SelectionExportPayload(values=values, columns=["a", "b", "c"])

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "values.h5"
            export_hdf5(payload, path)

            loaded = tttrlib.read_hdf5(str(path))
            shape = json.loads(loaded.column(0).attribute(VALUES_SHAPE_ATTRIBUTE))
            assert tuple(shape) == values.shape

    def test_compression_options(self, payload: SelectionExportPayload) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "compressed.h5"
            export_hdf5(payload, path, compression_level=5)
            assert path.exists()
            assert tttrlib.read_hdf5(str(path)).n_rows() == 10

    def test_an_existing_file_is_replaced(self, payload: SelectionExportPayload) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "twice.h5"
            export_hdf5(payload, path)
            export_hdf5(SelectionExportPayload(values=np.ones((1, 4)), columns=["q"]), path)
            assert list(tttrlib.read_hdf5(str(path)).column_names()) == ["q"]

    def test_missing_tabular_data_raises(self) -> None:
        payload = SelectionExportPayload()
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "invalid.h5"
            with pytest.raises(ValueError):
                export_hdf5(payload, path)

    def test_backend_error_wrapped(self, monkeypatch, payload: SelectionExportPayload) -> None:
        monkeypatch.setattr(hdf5_export.tttrlib, "hdf5_table_available", lambda: False)

        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "broken.h5"
            with pytest.raises(HDFBackendUnavailable):
                export_hdf5(payload, path)


def test_export_is_readable_without_naming_a_group(tmp_path):
    """The table is written at the root: ``read_hdf5(path)`` opens it as it is."""
    from ndxplorer.export.api import save_selection
    from ndxplorer.tests.fixtures.dataset_fixtures import (
        create_synthetic_selection_payload,
    )

    payload = create_synthetic_selection_payload(
        n_points=200, seed=11, include_figure=False
    )
    path = tmp_path / "roundtrip.h5"
    save_selection(payload, path, format="hdf5")

    loaded = tttrlib.read_hdf5(str(path))
    assert loaded.n_groups() == 0
    assert list(loaded.column_names()) == list(payload.columns)
    assert loaded.n_rows() == payload.values.shape[1]
