"""Reader tests for the ``…4`` burst companions (bg4/bv4/2c4 …) merge."""
from __future__ import annotations

import os

import numpy as np
import pytest

from ndxplorer.core.data_source import store_from_columns

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from ndxplorer.io import reader as R  # noqa: E402
from ndxplorer.io import tables  # noqa: E402


def _write_interleaved(path, header, values):
    """Write a Seidel-style 2n+1 companion: header, then zero/value rows.

    ``header`` is the column names; ``values`` is an (n, k) array whose rows land
    on the odd (1,3,…) rows, a trailing empty placeholder column mimicking the
    writers.
    """
    values = np.asarray(values, dtype=float)
    n, k = values.shape
    rows = np.zeros((2 * n + 1, k))
    rows[1::2] = values
    lines = ["\t".join(list(header) + [""])]
    lines += ["\t".join([repr(float(v)) for v in row] + [""]) for row in rows]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_2c4_in_default_endings_and_union_with_settings():
    assert "2c4" in R._DEFAULT_BURST_EXTRA_ENDINGS
    # A stale settings list is unioned with the defaults, never shadows them.
    endings = R._get_burst_additional_endings()
    for expected in ("bv4", "2c4"):
        assert expected in endings


def test_discover_extra_endings_picks_up_4_folders(tmp_path):
    for name in ("bi4_bur", "bv4", "2c4", "notes"):
        (tmp_path / name).mkdir()
    endings = R._discover_burst_extra_endings(tmp_path)
    assert "2c4" in endings and "bv4" in endings
    assert "notes" not in endings  # does not end in 4
    assert "bi4_bur" not in endings  # base burst dir, not a companion


def test_single_column_tab_file_gets_a_header():
    # A one-column companion (e.g. a 2c4 whose only column is FRET-2CDE) must be
    # detected with its header, not read headerless with an integer column name.
    lines = ["FRET-2CDE\t\n", "0.0\t\n", "10.0\t\n", "0.0\t\n", "20.0\t\n"]
    layout = R._detect_table_format(lines)
    assert layout["header_line"] == 0
    assert layout["delimiter"] == "\t"


def test_drop_trailing_empty_keeps_real_last_column():
    store = store_from_columns({"FRET-2CDE": [1.0, 2.0], "": ["", ""]})
    out = tables.drop_trailing_empty_columns(store)
    assert list(out.column_names()) == ["FRET-2CDE"]


def test_read_burst_analysis_merges_bv4_and_2c4(tmp_path):
    n = 5
    (tmp_path / "bi4_bur").mkdir()
    (tmp_path / "bv4").mkdir()
    (tmp_path / "2c4").mkdir()

    # .bur (interleaved) with two burst columns
    photons = np.stack([np.arange(n), np.arange(1, n + 1)], axis=1).astype(float)
    _write_interleaved(tmp_path / "bi4_bur" / "m000.bur",
                       ["First Photon", "Last Photon"], photons)
    # bv4: two columns; 2c4: single column
    _write_interleaved(tmp_path / "bv4" / "m000.bv4",
                       ["Proximity Ratio Mean", "Proximity Ratio Std"],
                       np.stack([np.linspace(0.1, 0.9, n), np.linspace(0.01, 0.05, n)], axis=1))
    _write_interleaved(tmp_path / "2c4" / "m000.2c4",
                       ["FRET-2CDE"], np.linspace(10.0, 40.0, n).reshape(-1, 1))

    # Fresh format cache so a prior run's detection can't leak in.
    try:
        from ndxplorer.io.file_metadata_cache import clear_metadata_cache
        clear_metadata_cache()
    except Exception:
        pass

    ds = R.read_burst_analysis(str(tmp_path), skip_nth_row=2)
    cols = ds.parameter_names
    assert "Proximity Ratio Std" in cols  # bv4
    assert "FRET-2CDE" in cols            # 2c4
