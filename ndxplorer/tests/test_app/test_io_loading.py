"""``ndxplorer.io.loading``: the opening rules both GUIs share, without a window."""

from __future__ import annotations

import pathlib

import numpy as np
import pytest

from ndxplorer.core.data_source import DataSource
from ndxplorer.io import loading
from ndxplorer.io.reader import read_burst_analysis, read_csv, read_sampling_folder

REPO = pathlib.Path(__file__).resolve().parents[3]
IRIS = REPO / "ndxplorer" / "tests" / "fixtures" / "iris.csv"
MFD = REPO / "test" / "mfd" / "burstwise_All 0.1500#30"


def test_a_drop_dispatches_by_folder_and_extension(tmp_path):
    sampling = tmp_path / "run"
    sampling.mkdir()
    (sampling / "parameters.json").write_text("{}")
    assert loading.kind_for_paths(str(sampling)) == "cs_sampling"
    assert loading.kind_for_paths(str(tmp_path)) == "burst_dir"
    for name, kind in (("a.er4", "er4"), ("a.h5", "mfd_hdf5"), ("a.HDF5", "mfd_hdf5"),
                       ("a.zip", "mfd_hdf5"), ("a.pto", "pto"), ("a.csv", "csv"),
                       ("m000.bur", "csv"), ("a.txt", "csv")):
        assert loading.kind_for_paths([str(tmp_path / name)]) == kind, name


def test_the_reader_for_each_importer(tmp_path):
    assert loading.reader_for("csv", [str(IRIS)]) == (read_csv, [str(IRIS)])
    assert loading.reader_for("burst_dir", str(MFD)) == (read_burst_analysis, str(MFD))
    assert loading.reader_for("cs_sampling", str(tmp_path))[0] is read_sampling_folder
    # A folder chosen as a burst folder that is a sampling folder reads as one.
    (tmp_path / "parameters.json").write_text("{}")
    assert loading.reader_for("burst_dir", str(tmp_path))[0] is read_sampling_folder
    reader, argument = loading.reader_for("mfd_hdf5", ["x.h5"], merge_mode="rows")
    assert reader.keywords == {"merge_mode": "rows"} and argument == ["x.h5"]


def test_load_reads_and_computes_the_equation_columns():
    source = loading.load([str(IRIS)], "csv", equations=[
        {"name": "petal area", "equation": "petal length * petal width"}], constants={})
    assert source.size == 150
    assert source.is_computed


def test_the_merge_question_and_its_answers():
    assert loading.MERGE_PROMPT == "How do you want to merge the new data?"
    assert [label for _mode, label in loading.MERGE_CHOICES][0] == "Replace existing data"
    assert loading.merge_choice(0) == (False, "columns")
    assert loading.merge_choice(1) == (True, "columns")
    assert loading.merge_choice(2) == (True, "rows")


def test_merge_by_rows_and_columns_and_the_refusal_is_reported():
    a = DataSource.from_columns({"E": np.arange(3.0), "S": np.ones(3)})
    b = DataSource.from_columns({"E": np.arange(2.0), "T": np.zeros(2)})
    warned = []
    assert not loading.merge(a, b, "columns", warn=lambda t, m: warned.append(t))
    assert warned == ["Row Count Mismatch"]
    assert loading.merge(a, b, "rows", warn=lambda t, m: warned.append(t))
    assert a.size == 5 and warned[-1] == "New Columns Found"
    assert not loading.merge(DataSource(), b, "rows")


def test_what_the_window_shows_about_what_was_opened():
    assert loading.working_path_for([str(IRIS)]) == str(IRIS.parent)
    assert loading.working_path_for(str(MFD)) == str(MFD.parent)
    assert loading.window_title(["/a/b.csv"]) == "ndX - b.csv"
    assert loading.window_title(["/a/b.csv", "/a/c.csv", "/a/d.csv"]) == "ndX - b.csv (+2)"


def test_the_qt_filter_strings_are_the_qt_windows():
    assert loading.filter_string(loading.IMPORTERS["csv"].filters) == \
        "Text files (*.csv *.dat *.er4 *.txt);;All files (*.*)"
    assert loading.filter_string(loading.IMPORTERS["mfd_hdf5"].filters) == \
        "HDF5 files (*.h5 *.hdf5);;ZIP files (*.zip);;All Files (*.*)"


def test_image_axes_are_the_pixel_columns_one_bin_per_pixel():
    from ndxplorer.utils.axis_helpers import image_axes

    source = DataSource.from_columns({
        "X pixel": np.array([0.0, 9.0, 3.0]), "Y pixel": np.array([0.0, 1.0, 4.0]),
        "Number of Photons (red)": np.ones(3), "Frame": np.zeros(3)})
    image = image_axes(source)
    assert (image.x, image.y, image.nx, image.ny) == ("X pixel", "Y pixel", 10, 5)
    assert image.x_range == (0.0, 10.0) and image.weight == "Number of Photons (red)"
    assert image.frame == "Frame"
    assert image_axes(DataSource.from_columns({"E": np.ones(2)})) is None


def test_the_screenshot_name_and_format():
    from datetime import datetime

    from ndxplorer.export.screenshots import default_screenshot_name, screenshot_format

    assert default_screenshot_name("/w", datetime(2026, 9, 23, 10, 1, 2)) == \
        "/w/ndxplorer_screenshot_2026-09-23_10-01-02.png"
    assert screenshot_format("a") == ("a.png", "PNG")
    assert screenshot_format("a.JPG") == ("a.JPG", "JPEG")
    assert screenshot_format("a.bmp") == ("a.bmp", "BMP")


def test_burst_id_files_are_found_where_the_writer_and_the_old_layouts_put_them(tmp_path):
    from ndxplorer.io.writer import find_bst_files, find_setup_name

    (tmp_path / "BID").mkdir()
    (tmp_path / "BID" / "m1.bst").write_text("")
    (tmp_path / "m0.bst").write_text("")
    assert sorted(pathlib.Path(p).name for p in find_bst_files(str(tmp_path))) == ["m0.bst", "m1.bst"]
    info = tmp_path / "Info"
    info.mkdir()
    (info / "photon_selection_parameters.json").write_text('{"selected_setup": "PQ"}')
    assert find_setup_name(str(tmp_path / "BID")) == "PQ"
    assert find_setup_name(str(tmp_path / "nowhere" / "deeper" / "x")) is None


@pytest.mark.parametrize("stop_after", [None, 1])
def test_burst_ids_written_headless_report_progress_and_can_stop(tmp_path, stop_after):
    from ndxplorer.io.writer import save_burst_ids_headless

    source = read_burst_analysis(str(MFD))
    seen = []

    def progress(done, total):
        seen.append((done, total))
        return stop_after is None or done < stop_after

    written = save_burst_ids_headless(str(tmp_path), [], source, progress=progress)
    total = seen[0][1]
    assert total >= 1 and seen[0][0] == 0
    assert len(written) == (total if stop_after is None else min(stop_after, total))
    assert sorted(tmp_path.glob("*.bst")) == sorted(written)
