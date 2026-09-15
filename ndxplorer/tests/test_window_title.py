"""The window is titled by WHAT was opened, not where it lives.

A title is identification: the filename is what a user scans window lists by,
and a full path pushes it off screen. The full path stays reachable as the
header Path field's tooltip.
"""

from __future__ import annotations

import pytest
from qtpy import QtWidgets

from ndxplorer.io.file_operations import _update_window_title


@pytest.fixture(scope="module")
def qapp():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


@pytest.fixture
def window(qapp):
    win = QtWidgets.QMainWindow()
    win.lineEditWorkingPath = QtWidgets.QLineEdit(win)
    yield win
    win.close()


def test_a_single_file_titles_by_its_name(window):
    _update_window_title(window, ("/home/user/data/tes_chisurf_mfd.pto",), False)
    assert window.windowTitle() == "ndX - tes_chisurf_mfd.pto"
    assert window.lineEditWorkingPath.toolTip() == "/home/user/data/tes_chisurf_mfd.pto"


def test_many_files_title_by_the_first_and_count_the_rest(window):
    files = ("/a/b/one.csv", "/a/b/two.csv", "/a/b/three.csv")
    _update_window_title(window, files, False)
    assert window.windowTitle() == "ndX - one.csv (+2)"
    assert window.lineEditWorkingPath.toolTip().splitlines() == list(files)


def test_appending_keeps_the_title(window):
    _update_window_title(window, ("/a/first.pto",), False)
    _update_window_title(window, ("/a/second.pto",), True)
    assert window.windowTitle() == "ndX - first.pto"


def test_a_folder_titles_by_its_basename(window):
    _update_window_title(window, ("/data/run_03",), False)
    assert window.windowTitle() == "ndX - run_03"


def test_nothing_selected_changes_nothing(window):
    window.setWindowTitle("ndX")
    _update_window_title(window, (), False)
    assert window.windowTitle() == "ndX"
