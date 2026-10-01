"""FRET > Phasor reference from IRF…: the constants of the corrected phasor from TTTR files."""

from __future__ import annotations

import pathlib

import numpy as np
import pytest

DATA = pathlib.Path("/Users/tpeulen/dev/tttr-data/imaging/pq/ht3")
MIRROR, CLSM = DATA / "crn_clv_mirror.ht3", DATA / "pq_ht3_clsm.ht3"


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("NDXPLORER_SETTINGS_DIR", str(tmp_path))
    from ndxplorer.app.frame import NdxApp
    from ndxplorer.core.data_source import DataSource

    a = NdxApp(features=["accurate_fret", "phasor_reference", "overlays"])
    y, x = np.indices((256, 256))
    # the median pixel phasor of the image test table (made from pq_ht3_clsm)
    g, s = np.full(x.size, 0.69), np.full(x.size, 0.47)
    a.model.set_source(DataSource.from_columns({
        "x pixel": x.ravel().astype(float), "y pixel": y.ravel().astype(float),
        "Frame": np.zeros(x.size), "g (green)": g, "s (green)": s,
        "Number of Photons (green)": np.full(x.size, 5.0)}))
    _frame(a)
    yield a
    a.close()


def _frame(app):
    from emtk.testing import RecordingPainter

    app.draw(RecordingPainter(), 0.0, 0.0, 1400.0, 900.0)


def feature(app):
    return next(f for f in app.features if f.name == "phasor_reference")


def test_the_fret_menu_has_the_entry(app):
    from ndxplorer.app.menus import iter_entries, merged_menus

    extra = [row for f in app.features for row in f.menu_entries()]
    rows = [(path, e["action"]) for path, e in iter_entries(merged_menus(extra))]
    assert (("FRET",), "phasor_reference") in rows
    assert feature(app).available("phasor_reference")


def test_a_pixel_table_knows_its_pixels_and_frames(app):
    assert feature(app).image_rows() == 256 * 256


@pytest.mark.skipif(not (MIRROR.exists() and CLSM.exists()), reason="tttr-data not here")
def test_compute_and_apply_move_the_green_phasor_inside_the_circle(app):
    f = feature(app)
    f.write_constants({"f_rep": 32.0})   # the clsm data: 32 MHz
    dialog = f.open_dialog()
    f._file_answers = [str(MIRROR), str(CLSM)]
    dialog.choose_irf()
    dialog.choose_measurement()
    _frame(app)
    dialog.compute()
    assert set(dialog.values) == {"g_irf (green)", "s_irf (green)", "n_bg (green)"}, dialog.notes
    assert 0.1 < dialog.values["n_bg (green)"] < 0.5
    dialog.apply()
    _frame(app)
    source = app.model.source
    g = np.asarray(source.column_values("g corr (green)"), dtype=float)
    s = np.asarray(source.column_values("s corr (green)"), dtype=float)
    assert (0.69 - 0.5) ** 2 + 0.47 ** 2 > 0.25         # the raw phasor: outside
    assert np.all((g - 0.5) ** 2 + s ** 2 < 0.25)       # corrected: inside
    assert dialog.done and f.window is None
