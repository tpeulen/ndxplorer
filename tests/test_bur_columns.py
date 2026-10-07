"""The last column of a ``.bur`` is real data, not the writer's trailing tab.

The Paris burst writers terminate the header line with a tab, which used to be
"corrected" by dropping the last column of every main table outright. The
parser already resolves the trailing tab, so that blanket drop deleted a
measured column instead: ``Red Count Rate (KHz)`` in the MFD burst tables,
``S delayed yellow (kHz) | 2048-4095`` in a PIE one. Losing it is silent and
expensive -- every derived red/FRET quantity (``Sr``, ``Fr``, the proximity
ratio, the FRET efficiency) is computed from that column, so the axis combo
simply comes up without them.

The companion (``bg4``/``br4``/``bv4``/``2c4``) branch had this right already:
strip only trailing *placeholder* columns. These tests keep the main table on
the same rule.
"""

from __future__ import annotations

import pathlib

import numpy as np
import pytest
from ndxplorer.core.data_source import store_from_columns
from ndxplorer.io.reader import (
    _process_burst_analysis_dir,
    read_burst_analysis,
)
from ndxplorer.io.tables import drop_trailing_empty_columns

HERE = pathlib.Path(__file__).parent
MFD_DIR = HERE / "mfd" / "burstwise_All 0.1500#30"


def test_drop_trailing_empty_columns_keeps_real_data() -> None:
    """Only empty/``Unnamed`` trailing columns go; a named one stays."""
    names = ["a", "b", "Red Count Rate (KHz)"]
    columns = {"a": [1], "b": [2], "Red Count Rate (KHz)": [3.0]}
    assert list(drop_trailing_empty_columns(store_from_columns(columns)).column_names()) == names

    padded = store_from_columns({**columns, "": [np.nan], "Unnamed: 4": [np.nan]})
    assert list(drop_trailing_empty_columns(padded).column_names()) == names


def test_bur_trailing_tab_does_not_cost_a_column(tmp_path: pathlib.Path) -> None:
    """A header line ending in a tab must not shorten the table."""
    bur_dir = tmp_path / "bi4_bur"
    bur_dir.mkdir()
    header = "First Photon\tLast Photon\tNumber of Photons\tRed Count Rate (KHz)\t\n"
    rows = "".join(f"{i}\t{i + 10}\t{100 + i}\t{i / 4.0}\n" for i in range(6))
    (bur_dir / "m000.bur").write_text(header + rows)

    ds = _process_burst_analysis_dir(tmp_path, skip_nth_row=1)

    assert "Red Count Rate (KHz)" in ds.parameter_names
    assert np.nanmax(ds.column_values("Red Count Rate (KHz)")) == pytest.approx(1.25)


@pytest.mark.skipif(not MFD_DIR.is_dir(), reason="MFD burst test data not present")
def test_mfd_burst_folder_keeps_the_red_count_rate() -> None:
    """The shipped MFD folder carries all 16 ``.bur`` columns into the table."""
    source = read_burst_analysis(MFD_DIR)

    assert "Red Count Rate (KHz)" in source.parameter_names
    # A dropped column would read as all-zero/NaN rather than a real rate.
    assert float(np.nanmax(source.column_values("Red Count Rate (KHz)"))) > 0.0
