"""Text tables in the layouts the reader detects, read through tttrlib.

tttrlib's CSV reader takes a file delimited by one character with its header on
the first line. Every other layout the detector recognises -- whitespace
alignment, a decimal comma, lines before the header, no header -- is rewritten
as tab-delimited text first, so each one has to come back with its columns and
its numbers.
"""

from __future__ import annotations

import zipfile

import numpy as np
import pytest

from ndxplorer.io import reader


def _write(path, text: str):
    path.write_text(text, encoding="utf-8")
    return str(path)


def _column(store, name):
    return np.asarray(store[name].numpy(), dtype=float)


def test_a_plain_comma_file_with_a_header_reads(tmp_path):
    path = _write(tmp_path / "plain.csv", "a,b,c\n1,2,3\n4,5,6\n")
    store = reader.read_csv_file(path)
    assert list(store.column_names()) == ["a", "b", "c"]
    assert store.n_rows() == 2
    np.testing.assert_array_equal(_column(store, "c"), [3.0, 6.0])


def test_the_plain_layout_is_detected_as_plain():
    layout = reader._detect_table_format(["a,b,c\n", "1,2,3\n"])
    assert layout["delimiter"] == ","
    assert layout["header_line"] == 0
    assert reader._is_plain_layout(layout)


def test_a_zipped_csv_reads_too(tmp_path):
    inner = tmp_path / "inner.csv"
    _write(inner, "x,y\n1,2\n3,4\n")
    archive = tmp_path / "bundle.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.write(inner, "inner.csv")

    store = reader.read_csv_file(str(archive))
    assert list(store.column_names()) == ["x", "y"]
    assert store.n_rows() == 2


def test_lines_before_the_header_are_skipped(tmp_path):
    path = _write(tmp_path / "preamble.txt",
                  "exported by something\n\nalpha\tbeta\n1.5\t2.5\n3.5\t4.5\n")
    store = reader.read_csv_file(path)
    assert list(store.column_names()) == ["alpha", "beta"]
    np.testing.assert_allclose(_column(store, "beta"), [2.5, 4.5])


def test_a_single_column_without_a_delimiter(tmp_path):
    path = _write(tmp_path / "single.dat", "  FRET-2CDE\n  10.0\n  20.0\n")
    layout = reader._detect_format(tmp_path / "single.dat", use_cache=False)
    assert layout["delimiter"] is None
    store = reader.read_csv_file(path)
    assert list(store.column_names()) == ["FRET-2CDE"]
    np.testing.assert_allclose(_column(store, "FRET-2CDE"), [10.0, 20.0])


def test_a_decimal_comma(tmp_path):
    path = _write(tmp_path / "comma.csv", "a;b;c\n1,5;2,25;3\n3,5;4,75;5\n")
    layout = reader._detect_format(tmp_path / "comma.csv", use_cache=False)
    assert layout["delimiter"] == ";" and layout["decimal_comma"]
    store = reader.read_csv_file(path)
    np.testing.assert_allclose(_column(store, "b"), [2.25, 4.75])


def test_a_file_without_a_header_is_named_by_position(tmp_path):
    path = _write(tmp_path / "bare.csv", "1,2\n3,4\n")
    store = reader.read_csv_file(path)
    assert list(store.column_names()) == ["0", "1"]
    np.testing.assert_array_equal(_column(store, "1"), [2.0, 4.0])


def test_msvc_spellings_and_empty_fields(tmp_path):
    path = _write(tmp_path / "msvc.csv", "a,b\n1.#INF,1\n-1.#IND00e+000,\nword,3\n")
    store = reader.read_csv_file(path)
    a = _column(store, "a")
    assert a[0] == np.inf
    # A NaN and a word are no number; the table fills them.
    assert a[1] == reader.FILL_MISSING_VALUE and a[2] == reader.FILL_MISSING_VALUE
    np.testing.assert_array_equal(_column(store, "b"), [1.0, reader.FILL_MISSING_VALUE, 3.0])


@pytest.mark.parametrize("n_files", [2])
def test_files_of_one_width_stack(tmp_path, n_files):
    paths = [_write(tmp_path / f"f{i}.csv", f"x,y\n{i},1\n{i},2\n") for i in range(n_files)]
    source = reader.read_csv(paths)
    assert source.size == 4
    np.testing.assert_array_equal(source.column_values("x"), [0, 0, 1, 1])
