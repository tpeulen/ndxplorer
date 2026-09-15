"""Tests for the CSV/TSV export path."""
import tempfile
from pathlib import Path

import numpy as np
import pytest
import tttrlib

from ndxplorer.core.data_source import store_from_columns
from ndxplorer.export.csv_export import export_table
from ndxplorer.export.models import SelectionExportPayload


@pytest.fixture
def sample_data():
    return store_from_columns(
        {
            "x": np.arange(10),
            "y": np.linspace(0.0, 1.0, 10),
            "category": ["A", "B"] * 5,
        }
    )


def _assert_same_table(loaded, expected):
    names = [expected.column(i).name() for i in range(expected.n_columns())]
    assert [loaded.column(i).name() for i in range(loaded.n_columns())] == names
    assert loaded.n_rows() == expected.n_rows()
    for name in names:
        want = expected[name].numpy()
        got = loaded[name].numpy()
        if want.dtype == object:
            assert list(got) == list(want)
        else:
            np.testing.assert_array_equal(np.asarray(got, dtype=want.dtype), want)


def test_export_basic_csv(sample_data):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "test.csv"
        export_table(SelectionExportPayload(table=sample_data), path, include_metadata=False)
        assert path.exists()
        _assert_same_table(tttrlib.read_csv(str(path)), sample_data)


def test_export_tsv_delimiter_inferred(sample_data):
    """A .tsv suffix selects a tab delimiter without asking."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "test.tsv"
        export_table(SelectionExportPayload(table=sample_data), path, include_metadata=False)
        assert path.exists()
        _assert_same_table(tttrlib.read_csv(str(path), delimiter="\t"), sample_data)


def test_export_writes_metadata_sidecar(sample_data):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "test.csv"
        export_table(
            SelectionExportPayload(table=sample_data, name="demo", metadata={"experiment": "x"}),
            path,
            include_metadata=True,
        )
        assert path.exists()
        assert path.with_suffix(".csv.meta.json").exists()


def test_export_from_values_and_columns():
    """A payload backed by (values, columns) is materialised to a table."""
    values = np.vstack([np.arange(5), np.arange(5) * 2.0])  # (n_params, n_points)
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "vals.csv"
        export_table(
            SelectionExportPayload(values=values, columns=["a", "b"]),
            path,
            include_metadata=False,
        )
        loaded = tttrlib.read_csv(str(path))
        assert list(loaded.column_names()) == ["a", "b"]
        assert loaded.n_rows() == 5
        np.testing.assert_allclose(np.asarray(loaded["b"].numpy(), dtype=float),
                                   np.arange(5) * 2.0)


def test_export_requires_tabular_data():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "nope.csv"
        with pytest.raises(ValueError):
            export_table(SelectionExportPayload(), path)


def test_export_large_dataset():
    large = store_from_columns(
        {"x": np.arange(10000), "y": np.random.random(10000), "z": np.random.random(10000)}
    )
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "large.csv"
        export_table(SelectionExportPayload(table=large), path, include_metadata=False)
        _assert_same_table(tttrlib.read_csv(str(path)), large)


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-q"])
