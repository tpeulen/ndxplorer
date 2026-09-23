"""Tests for the StoreEditor dialog."""

from __future__ import annotations

import numpy as np
import pytest
from qtpy import QtCore, QtWidgets

from chisurf.gui.widgets.chitable import ChiTableDialog

from ndxplorer.core.data_source import DataSource
from ndxplorer.ui import store_editor
from ndxplorer.core.store_edits import apply_edits
from ndxplorer.ui.store_editor import StoreEditor, edit_source


@pytest.fixture
def source():
    return DataSource.from_columns(
        {
            "float_col": np.array([1.0, 2.5, np.nan, 4.2]),
            "int_col": np.array([10, 20, 30, 40], dtype=np.int64),
            "str_col": ["a", "b", "c", "d"],
        }
    )


def _text(dlg, row, col):
    model = dlg.table.table_model
    value = model.data(model.index(row, col), QtCore.Qt.DisplayRole)
    return "" if value is None else str(value)


def test_is_the_shared_chitable_dialog(qapp: QtWidgets.QApplication, source):
    assert issubclass(StoreEditor, ChiTableDialog)
    dlg = StoreEditor(source, None)
    assert dlg.windowTitle() == "Table Editor"
    assert dlg.table.visible_row_count() == 4


def test_shape_matches_the_table(qapp: QtWidgets.QApplication, source):
    dlg = StoreEditor(source, None)
    model = dlg.table.table_model
    assert model.rowCount() == 4
    assert model.columnCount() == 3


def test_numeric_cell_is_formatted(qapp: QtWidgets.QApplication, source):
    dlg = StoreEditor(source, None)
    assert "1" in _text(dlg, 0, 0)


def test_search_narrows_the_table(qapp: QtWidgets.QApplication, source):
    dlg = StoreEditor(source, None)
    dlg.table.set_search_text("2.5")
    assert dlg.table.visible_row_count() == 1
    dlg.table.set_search_text("")
    assert dlg.table.visible_row_count() == 4


def test_edits_are_staged_until_accept(qapp: QtWidgets.QApplication, source):
    dlg = StoreEditor(source, None)
    model = dlg.table.table_model
    assert model.setData(model.index(0, 0), "42", QtCore.Qt.EditRole)
    assert dlg.edited.column_values("float_col")[0] == 1.0
    dlg.accept()
    assert dlg.edited.column_values("float_col")[0] == 42.0
    # The source itself is untouched until the edits are applied.
    assert source.column_values("float_col")[0] == 1.0


def test_apply_edits_writes_changed_columns_in_place(qapp, source):
    dlg = StoreEditor(source, None)
    src = dlg.table.table_model.source
    assert src.set_value(2, 1, 99)
    written = apply_edits(source, dlg.edited)
    assert written == ["int_col"]
    assert source.parameter_names == ["float_col", "int_col", "str_col"]
    np.testing.assert_array_equal(source.column_view(1), [10, 20, 99, 40])


def test_edit_source_returns_none_on_cancel(qapp, source, monkeypatch):
    monkeypatch.setattr(
        QtWidgets.QDialog, "exec_", lambda self: QtWidgets.QDialog.Rejected, raising=False
    )
    version = source.data_version
    assert edit_source(source) is None
    assert source.data_version == version
    assert source.column_values("float_col")[0] == 1.0


def test_module_surface():
    assert hasattr(store_editor, "StoreEditor")
    assert hasattr(store_editor, "edit_source")
    assert not hasattr(store_editor, "pd")
