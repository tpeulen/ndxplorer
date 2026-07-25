"""Regression tests: parameter-table constants are used from the first compute.

Derived burst columns (FRET efficiency, Fg, ...) are computed from equations
that need constants (Bg, gG/gR, PhiA, ...). NDXplorer.constants used to start
empty and only get populated from the parameter table on the *first* edit, so
the initial (background) column computation ran with no constants — leaving
those columns missing/default — and the first edit then applied the whole table
at once, producing a large jump for what looked like a 1% tweak. NDXplorer now
seeds self.constants from the parameter table at construction.
"""
from __future__ import annotations

import json
import os
import pathlib

import numpy as np
import pytest
import yaml

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="session")
def qapp():
    from qtpy import QtWidgets

    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def test_constants_seeded_from_parameter_table_at_construction(qapp):
    """self.constants must equal the parameter table before any edit."""
    from ndxplorer.core.plot_main import NDXplorer

    ndx = NDXplorer()
    if hasattr(ndx, "_deferred_init"):
        ndx._deferred_init()

    table = dict(ndx.parameter_control.dict)
    assert table, "parameter table should load default constants"
    assert ndx.constants == table, "self.constants must be seeded from the table"


def _settings_dir() -> pathlib.Path:
    import ndxplorer

    return pathlib.Path(ndxplorer.__file__).parent / "settings"


_BURST_DIR = pathlib.Path(
    "/Users/tpeulen/dev/tttr-data/bh/bh_spc132_sm_dna/sliding_window_All 0.1500#60_1"
)


@pytest.mark.skipif(not _BURST_DIR.exists(), reason="local burst dataset not present")
def test_empty_constants_drop_constant_dependent_columns():
    """Reproduces the failure mode on the real dataset.

    Computing derived columns with an empty constant set silently drops the
    constant-dependent ones (FRET efficiency, Fg, ...), so the pre-edit plot
    (empty constants) and the post-edit plot (table constants) disagree by far
    more than the edited parameter warrants. Seeding self.constants makes the
    initial compute use the table, so the two agree.
    """
    from ndxplorer.io.reader import read_burst_analysis

    sett = _settings_dir()
    constants = json.load(open(sett / "mfd.constants.json"))
    equations = yaml.safe_load(open(sett / "mfd.equations.yaml"))

    empty_ds = read_burst_analysis(str(_BURST_DIR))
    empty_ds.compute_columns(constants={}, equations=equations)
    full_ds = read_burst_analysis(str(_BURST_DIR))
    full_ds.compute_columns(constants=constants, equations=equations)

    empty_cols = set(empty_ds.data.columns)
    full_cols = set(full_ds.data.columns)

    # Table constants derive a strict superset — the dropped ones are the bug.
    assert empty_cols < full_cols
    assert "FRET efficiency" in full_cols
    assert "FRET efficiency" not in empty_cols

    # And a 1% Bg tweak, with constants applied, is a tiny change (not a jump).
    tweaked = dict(constants)
    tweaked["Bg"] = float(constants["Bg"]) * 1.01
    twk_ds = read_burst_analysis(str(_BURST_DIR))
    twk_ds.compute_columns(constants=tweaked, equations=equations)
    fe_full = np.asarray(full_ds.data["FRET efficiency"], dtype=float)
    fe_twk = np.asarray(twk_ds.data["FRET efficiency"], dtype=float)
    m = np.isfinite(fe_full) & np.isfinite(fe_twk)
    assert abs(fe_full[m].mean() - fe_twk[m].mean()) < 0.01


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-q"])
