"""The axes a table opens on (``ndxplorer.app.default_view``).

Images open on the phasor plot, MFD bursts on lifetime vs FRET, ALEX/PIE
bursts on E vs S, cw bursts on E vs FRET-2CDE; what the user saved wins for
its own kind of table only; the last resort skips index columns and
constants; x, y and z are three different parameters.
"""
import json

import numpy as np
import pytest

from ndxplorer.app.default_view import choose_axes, data_kind, saved_axes_key
from ndxplorer.settings.persist import write_default_axes

SHIPPED = {"default_axes": {"x": "Tau (green)", "y": "Proximity ratio",
                            "z": "r Experimental (green)", "weight": "Number of Photons"}}

BURST_COMMON = ["First Photon", "Last Photon", "Duration (ms)", "Number of Photons",
                "Count Rate (KHz)", "Number of Photons (green)", "Number of Photons (red)"]
MFD = BURST_COMMON + ["Proximity ratio", "Tau (green)", "Tau (red)", "r Experimental (green)",
                      "r Experimental (red)", "FRET-2CDE"]
ALEX = BURST_COMMON + ["Number of Photons (yellow)", "Proximity ratio", "Stoichiometry",
                       "FRET-2CDE", "ALEX-2CDE", "TGX-TRR"]
CW = BURST_COMMON + ["Proximity ratio", "FRET-2CDE"]
IMAGE = ["x pixel", "y pixel", "Frame", "Number of Photons (green)", "Number of Photons (red)",
         "Number of Photons", "Tau (green)", "Tau (red)", "g (green)", "s (green)",
         "Proximity Ratio", "Sg/Sr", "Frame Time (s)"]


def _axes(names, settings=SHIPPED, **kw):
    a = choose_axes(names, settings, **kw)
    return a["x"], a["y"], a["z"], a["weight"]


def test_kinds():
    assert data_kind(IMAGE) == "image"
    for names in (MFD, ALEX, CW):
        assert data_kind(names) == "bursts"
    assert saved_axes_key("bursts") == "default_axes"
    assert saved_axes_key("image") == "default_axes_image"


def test_mfd_bursts_keep_the_shipped_view():
    assert _axes(MFD) == ("Tau (green)", "Proximity ratio", "r Experimental (green)", "Number of Photons")


def test_alex_bursts_open_on_e_vs_s():
    x, y, z, w = _axes(ALEX)
    assert (x, y, z, w) == ("Proximity ratio", "Stoichiometry", "ALEX-2CDE", "Number of Photons")


def test_corrected_values_are_preferred():
    x, y, _, _ = _axes(ALEX + ["FRET Efficiency", "Stoichiometry (corrected)"])
    assert (x, y) == ("FRET Efficiency", "Stoichiometry (corrected)")


def test_cw_bursts_open_on_e_vs_fret_2cde():
    assert _axes(CW)[:2] == ("Proximity ratio", "FRET-2CDE")


def test_images_open_on_the_phasor_not_the_burst_default():
    # Tau (green) and Proximity Ratio both exist, so the old rule opened the
    # image on the bursts' default, coloured by "x pixel".
    x, y, z, w = _axes(IMAGE)
    assert (x, y, z, w) == ("g (green)", "s (green)", "Tau (green)", "Number of Photons")


def test_images_prefer_the_corrected_phasor():
    x, y, _, _ = _axes(IMAGE + ["g corr (green)", "s corr (green)"])
    assert (x, y) == ("g corr (green)", "s corr (green)")


def test_presets_never_match_a_substring():
    # "s (green)" is a substring of "Number of Photons (green)".
    names = ["x pixel", "y pixel", "Number of Photons (green)", "g (green) raw", "Tau (green)"]
    x, y, z, _ = _axes(names)
    assert "Number of Photons (green)" not in (x, y) or x != "g (green)"
    assert len({x, y, z}) == 3


def test_saved_axes_win_for_their_kind_only():
    settings = dict(SHIPPED, default_axes={"x": "Duration (ms)", "y": "Number of Photons"},
                    default_axes_image={"x": "Tau (green)", "y": "Proximity Ratio"})
    assert _axes(ALEX, settings)[:2] == ("Duration (ms)", "Number of Photons")
    assert _axes(IMAGE, settings)[:2] == ("Tau (green)", "Proximity Ratio")
    # A saved default naming columns the table lacks falls through to the views.
    assert _axes(ALEX, {"default_axes": {"x": "Tau (green)", "y": "nope"}})[:2] == \
        ("Proximity ratio", "Stoichiometry")


def test_settings_can_replace_the_views():
    settings = {"default_views": {"bursts": [{"name": "mine", "x": ["TGX-TRR"], "y": ["Duration (ms)"]}]}}
    a = choose_axes(ALEX, settings)
    assert (a["x"], a["y"], a["view"]) == ("TGX-TRR", "Duration (ms)", "mine")


def test_unknown_table_skips_index_and_constant_columns():
    names = ["First Photon", "Last Photon", "flag", "a", "b", "c"]
    constant = {"flag"}
    x, y, z, _ = _axes(names, {}, varies=lambda n: n not in constant)
    assert (x, y, z) == ("a", "b", "c")


def test_three_distinct_axes_whenever_possible():
    for names in (MFD, ALEX, CW, IMAGE, ["a", "b", "c"]):
        x, y, z, _ = _axes(names)
        assert len({x, y, z}) == 3, names


def test_saving_default_axes_per_kind(tmp_path):
    path = tmp_path / "s.settings.json"
    path.write_text(json.dumps(SHIPPED))
    write_default_axes(path, "g (green)", "s (green)", "Tau (green)", kind="image")
    data = json.loads(path.read_text())
    assert data["default_axes"] == SHIPPED["default_axes"]          # bursts untouched
    assert data["default_axes_image"]["x"] == "g (green)"


def test_model_opens_tables_on_their_view():
    pytest.importorskip("tttrlib")
    from ndxplorer.app.model import ExplorerModel
    from ndxplorer.core.data_source import DataSource

    rng = np.random.default_rng(0)

    def table(names):
        return DataSource.from_columns({n: rng.random(50) for n in names})

    model = ExplorerModel()
    model.set_source(table(ALEX))
    assert (model.x.name, model.y.name) == ("Proximity ratio", "Stoichiometry")
    model.set_source(table(IMAGE))
    assert model.data_kind == "image"
    # ndX's equations add the IRF-corrected phasor, which is preferred.
    assert (model.x.name, model.y.name, model.z.name) == ("g corr (green)", "s corr (green)", "Tau (green)")


def test_an_axis_without_settings_drops_the_previous_bins():
    """Opening a burst table after an image: S must not keep the image's 256
    pixel bins (the E-S map turned into stripes), nor its scale."""
    pytest.importorskip("tttrlib")
    from ndxplorer.app.model import DEFAULT_BINS_1D, DEFAULT_BINS_2D, ExplorerModel
    from ndxplorer.core.data_source import DataSource

    rng = np.random.default_rng(1)
    model = ExplorerModel()
    model.set_source(DataSource.from_columns({n: rng.random(50) for n in IMAGE}))
    model.y.bins_1d = model.y.bins_2d = 256
    model.y.log = True
    model.set_source(DataSource.from_columns({n: rng.random(50) for n in ALEX}))
    assert model.y.name == "Stoichiometry"
    assert (model.y.bins_1d, model.y.bins_2d, model.y.log) == (DEFAULT_BINS_1D, DEFAULT_BINS_2D, False)
