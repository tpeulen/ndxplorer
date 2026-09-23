"""The logic both GUIs share, tested without Qt.

The Qt window and the emtk app (:mod:`ndxplorer.app`) decide the same things --
which rows a gate list keeps, the colour limits of the 2-D map, how an axis
is set up for a parameter, which colours a colormap has, what a settings file
says -- through these functions. They are exercised here with plain data, and
the first test makes sure none of them drags Qt in.
"""

from __future__ import annotations

import json
import subprocess
import sys

import numpy as np
import pytest

from ndxplorer.core.data_source import (
    DataSource,
    Gaussian2DSelection,
    MaskDataSelection,
    RectangularDataSelection,
)
from ndxplorer.core.gates import GateList, GateRow, interval_rows, selections_from_rows
from ndxplorer.core.histograms import auto_contrast_limits, colour_limits, display_counts
from ndxplorer.plotting import colormap_lut
from ndxplorer.utils.axis_helpers import settings_for_axis


def test_the_shared_logic_imports_without_qt():
    """Importing it leaves every Qt binding, pyqtgraph and chisurf out."""
    code = (
        "import sys\n"
        "import ndxplorer.core.gates, ndxplorer.core.histograms, ndxplorer.core.data\n"
        "import ndxplorer.plotting.colormap_lut, ndxplorer.settings.bundle\n"
        "import ndxplorer.utils.axis_helpers, ndxplorer.utils.histogram_computation\n"
        "import ndxplorer.io.reader\n"
        "bad = [m for m in sys.modules if m.split('.')[0] in "
        "('qtpy', 'PyQt5', 'PyQt6', 'PySide2', 'PySide6', 'pyqtgraph', 'chisurf')]\n"
        "print(','.join(bad))\n"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                         check=True)
    assert out.stdout.strip() == ""


# -- gates ---------------------------------------------------------------------------


def test_an_interval_row_is_a_rectangular_selection():
    rows = [GateRow(2, "Tau", 1.0, 3.0, invert=True, enabled=False)]
    (sel,) = selections_from_rows(rows)
    assert isinstance(sel, RectangularDataSelection)
    assert (sel.parameter_idx, sel.lower, sel.upper) == (2, 1.0, 3.0)
    assert sel.invert and not sel.enabled


def test_a_dragged_rectangle_is_two_ordered_intervals():
    x, y = interval_rows(0, "x", (5.0, 1.0), 3, "y", (0.2, -0.4))
    assert (x.parameter_idx, x.lower, x.upper, x.name) == (0, 1.0, 5.0, "x")
    assert (y.parameter_idx, y.lower, y.upper, y.name) == (3, -0.4, 0.2, "y")


def test_a_gaussian_row_is_rebuilt_from_its_metadata():
    meta = {"type": "G2D", "idx1": 0, "idx2": 1, "mu": [1, 2], "cov": [[1, 0], [0, 2]],
            "sigma": 2.0}
    (sel,) = selections_from_rows([GateRow(0, "G2D 1", meta=meta)])
    assert isinstance(sel, Gaussian2DSelection)
    assert sel.sigma == 2.0 and sel.parameter_idx2 == 1


def _mask():
    return MaskDataSelection(0, 1, np.ones((2, 2), bool), np.array([0.0, 1, 2]),
                             np.array([0.0, 1, 2]), name="Mask")


def test_a_mask_row_is_its_mask_with_the_rows_flags():
    mask = _mask()
    gates = GateList()
    row = gates.add_selection(mask)
    assert row.kind == "Mask" and row.record()["lower"] == "Bitmap"
    gates.edit(0, "invert", True)
    gates.edit(0, "name", "Mask 1")
    (sel,) = gates.selections()
    assert sel is mask and mask.invert and mask.name == "Mask 1"


def test_the_list_holds_all_four_kinds():
    class Region:  # a drawn region: anything with a roi
        roi, idx1, idx2, shape, name = object(), 0, 1, "polygon", "poly"
        invert, enabled = False, True

    gates = GateList()
    gates.add_interval(0, "a", 3.0, 1.0)
    gates.add_gaussian(0, 1, (1, 2), [[1, 0], [0, 1]], sigma=2.0, name="G2D 1")
    gates.add_selection(Region())
    gates.add_selection(_mask())
    assert [r.kind for r in gates] == ["Interval", "G2D", "Region", "Mask"]
    assert (gates[0].lower, gates[0].upper) == (1.0, 3.0)
    assert [r["row"] for r in gates.records()] == [0, 1, 2, 3]
    assert len(gates.selections()) == 4


def test_edits_follow_the_qt_tables_rules():
    gates = GateList()
    gates.add_interval(0, "a", 1.0, 2.0)
    gates.add_gaussian(0, 1, (0, 0), [[1, 0], [0, 1]])
    revision = gates.revision
    assert gates.edit(0, "lower", 5.0)            # typed past the upper bound
    assert (gates[0].lower, gates[0].upper) == (5.0, 5.0)
    assert not gates.edit(0, "upper", "junk")     # not a number: refused
    assert not gates.edit(1, "lower", 1.0)        # a Gaussian has no bounds
    assert not gates.edit(7, "invert", True)
    assert gates.revision == revision + 1
    assert gates.remove([0, 1]) == 2 and len(gates) == 0


def test_the_rows_gate_the_data():
    source = DataSource.from_columns({"a": np.arange(10.0), "b": np.arange(10.0) * 2})
    rows = [GateRow(0, "a", 2.0, 5.0)]
    keep = source.selection_mask(selections_from_rows(rows))
    assert keep.tolist() == [False, False, True, True, True, True] + [False] * 4


# -- the 2-D map's colours -------------------------------------------------------------


def test_log_counts_keep_empty_bins_below_the_filled_ones():
    H = np.array([[0.0, 1.0], [10.0, 100.0]])
    shown = display_counts(H, log_counts=True)
    assert shown[0, 0] == pytest.approx(-1.0)
    assert shown[1, 1] == pytest.approx(2.0)
    assert np.array_equal(display_counts(H), H)


def test_colour_limits_are_in_the_units_drawn():
    rng = np.random.default_rng(0)
    H = rng.poisson(50, (40, 40)).astype(float)
    lo, hi = colour_limits(H, log_counts=False)
    llo, lhi = colour_limits(H, log_counts=True)
    assert lo < hi and llo < lhi
    assert 10 ** lhi == pytest.approx(hi, rel=1e-6)


def test_an_empty_map_has_unit_limits():
    assert auto_contrast_limits(np.zeros((4, 4))) == (0.0, 1.0)
    assert colour_limits(np.zeros((4, 4))) == (0.0, 0.0)


def test_auto_contrast_ignores_single_count_bins_in_log():
    """The Contrast button percentiles the drawn values above zero: a bin of one
    burst draws as 0 in log and is left out, as in the Qt window."""
    H = np.array([[1.0, 2.0, 4.0, 8.0]] * 4)
    lo, hi = auto_contrast_limits(H, log_counts=True)
    assert lo >= np.log10(2.0) - 1e-9 and hi <= np.log10(8.0) + 1e-9


# -- axes ---------------------------------------------------------------------------------


def test_an_axis_with_settings_takes_them():
    settings = {"Tau (green)": {"min": 0, "max": 6, "scale": "lin", "n_bins_1d": 81,
                                "n_bins_2d": 31}}
    setup = settings_for_axis("Tau (green)", settings)
    assert setup == {"bins_1d": 81, "bins_2d": 31, "min": 0, "max": 6, "scale": "lin"}
    assert settings_for_axis("Tau (green)", settings, with_2d=False)["bins_2d"] is None
    assert settings_for_axis("unknown", settings) is None


def test_a_pixel_axis_gets_a_bin_per_pixel():
    setup = settings_for_axis("X pixel", {"X pixel": {"max": 128}})
    assert setup["bins_2d"] == 128
    assert setup["min"] is None


# -- colormaps --------------------------------------------------------------------------


def test_colormaps_are_listed_and_have_rgba_tables():
    names = colormap_lut.available_colormaps()
    assert "viridis" in names
    lut = colormap_lut.lookup_table("viridis", 16)
    assert lut.shape == (16, 4) and lut.dtype == np.uint8
    assert tuple(lut[0, :3]) == (68, 1, 84)          # viridis starts dark purple


def test_an_unknown_colormap_is_grey():
    lut = colormap_lut.lookup_table("no such map", 3)
    assert lut[:, 0].tolist() == lut[:, 1].tolist() == [0, 127, 255]


def test_the_luts_match_pyqtgraph():
    """Same stops, same interpolation: the Qt image and the emtk texture agree."""
    pg = pytest.importorskip("pyqtgraph")
    for name in ("viridis", "inferno", "CET-L9", "PAL-relaxed"):
        ours = colormap_lut.lookup_table(name)
        theirs = (np.clip(pg.colormap.get(name).map(np.linspace(0, 1, 256), mode="float"),
                          0, 1) * 255).astype(np.uint8)
        assert np.array_equal(ours, theirs), name


def test_applying_a_colormap_clips_to_the_limits():
    rgba = colormap_lut.apply_colormap(np.array([[-5.0, 0.0], [1.0, 9.0]]), "viridis", 0.0, 1.0)
    lut = colormap_lut.lookup_table("viridis")
    assert tuple(rgba[0, 0]) == tuple(lut[0]) == tuple(rgba[0, 1])
    assert tuple(rgba[1, 1]) == tuple(lut[-1]) == tuple(rgba[1, 0])


# -- settings -----------------------------------------------------------------------------


def test_the_packaged_settings_read_whole():
    from ndxplorer.settings.bundle import PACKAGED_SETTINGS, read_settings

    bundle = read_settings(PACKAGED_SETTINGS)
    assert bundle.settings["default_axes"]["x"] == "Tau (green)"
    assert "Tau (green)" in bundle.axis_settings
    assert bundle.equations and bundle.equations_path is not None
    assert bundle.constants


def test_a_settings_file_names_its_neighbours(tmp_path):
    from ndxplorer.settings.bundle import read_settings

    (tmp_path / "my.axis.json").write_text(json.dumps({"q": {"min": 1, "max": 2}}))
    (tmp_path / "my.settings.json").write_text(json.dumps({"axis": "my.axis.json"}))
    bundle = read_settings(tmp_path / "my.settings.json")
    assert bundle.axis_settings == {"q": {"min": 1, "max": 2}}
    assert bundle.equations == [] and bundle.equations_path is None


def test_a_missing_settings_file_falls_back_to_the_packaged_one(tmp_path):
    from ndxplorer.settings.bundle import PACKAGED_SETTINGS, read_settings

    assert read_settings(tmp_path / "nope.settings.json").path == PACKAGED_SETTINGS


# -- merging --------------------------------------------------------------------------------


def test_a_refused_merge_says_why_through_the_callback():
    a = DataSource.from_columns({"x": np.arange(3.0)})
    b = DataSource.from_columns({"y": np.arange(4.0)})
    told = []
    assert a.merge(b, mode="columns", warn=lambda t, m: told.append(t)) is False
    assert told == ["Row Count Mismatch"]
