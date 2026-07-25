"""Tests for the DataFrameEditor widget.

The editor has two implementations — one delegating to ChiSurf's shared table
widget, one standalone — so the assertions here go through the public surface
(``dataframe``, the dialog's model/view) rather than a particular widget's
internals, and the standalone branch gets its own regression tests for two
defects it used to carry.
"""

from __future__ import annotations

import importlib

import numpy as np
import pandas as pd
import pytest
from qtpy import QtCore, QtWidgets

from ndxplorer.ui import dataframe_editor as dfe
from ndxplorer.ui.dataframe_editor import HAS_CHISURF, DataFrameEditor


@pytest.fixture
def sample_df():
    return pd.DataFrame(
        {
            "float_col": [1.0, 2.5, np.nan, 4.2],
            "int_col": [10, 20, 30, 40],
            "str_col": ["a", "b", "c", "d"],
        }
    )


def _model(dlg):
    """Return the dialog's table model whichever implementation is live.

    Parameters
    ----------
    dlg : DataFrameEditor
        The open editor.

    Returns
    -------
    qtpy.QtCore.QAbstractItemModel
    """
    if HAS_CHISURF:
        return dlg.table.table_model
    return dlg._table.model()


def _text(dlg, row, col):
    """Return the display text of one cell.

    Parameters
    ----------
    dlg : DataFrameEditor
        The open editor.
    row : int
        View row index.
    col : int
        Column index.

    Returns
    -------
    str
    """
    model = _model(dlg)
    value = model.data(model.index(row, col), QtCore.Qt.DisplayRole)
    return "" if value is None else str(value)


# ── shared surface ───────────────────────────────────────────────────────


def test_create_and_title(qapp: QtWidgets.QApplication, sample_df: pd.DataFrame):
    dlg = DataFrameEditor(sample_df, None)
    assert dlg.windowTitle() == "DataFrame Editor"
    assert dlg.dataframe.shape == (4, 3)


def test_shape_matches_the_frame(qapp: QtWidgets.QApplication, sample_df: pd.DataFrame):
    dlg = DataFrameEditor(sample_df, None)
    model = _model(dlg)
    assert model.rowCount() == 4
    assert model.columnCount() == 3


def test_numeric_cell_is_formatted(qapp: QtWidgets.QApplication, sample_df: pd.DataFrame):
    dlg = DataFrameEditor(sample_df, None)
    assert "1" in _text(dlg, 0, 0)


def test_nan_shown_as_empty(qapp: QtWidgets.QApplication, sample_df: pd.DataFrame):
    dlg = DataFrameEditor(sample_df, None)
    assert _text(dlg, 2, 0) == ""


def test_extension_dtypes_do_not_raise(qapp: QtWidgets.QApplication):
    """Regression: nullable pandas dtypes must render, not crash.

    Numeric-ness used to be tested with ``np.issubdtype``, which raises
    ``TypeError`` on ``Float64``/``Int64`` — the dtypes the pyarrow burst reader
    produces.
    """
    df = pd.DataFrame(
        {
            "a": pd.array([1.5, None, 3.5], dtype="Float64"),
            "b": pd.array([1, 2, None], dtype="Int64"),
            "c": pd.array(["x", None, "z"], dtype="string"),
        }
    )
    dlg = DataFrameEditor(df, None)
    assert _model(dlg).rowCount() == 3
    assert "1.5" in _text(dlg, 0, 0)
    assert _text(dlg, 1, 0) == ""


def test_edit_dataframe_returns_none_on_cancel(
    qapp: QtWidgets.QApplication, sample_df: pd.DataFrame, monkeypatch
):
    monkeypatch.setattr(
        QtWidgets.QDialog, "exec_", lambda self: QtWidgets.QDialog.Rejected, raising=False
    )
    assert dfe.edit_dataframe(sample_df) is None
    assert sample_df.iloc[0, 0] == 1.0


# ── standalone implementation ────────────────────────────────────────────

standalone = pytest.mark.skipif(
    HAS_CHISURF, reason="ChiSurf is installed; the standalone branch is not live"
)


@standalone
def test_search_filters_rows(qapp: QtWidgets.QApplication, sample_df: pd.DataFrame):
    dlg = DataFrameEditor(sample_df, None)
    assert dlg._table.rowCount() == 4
    dlg._search_edit.setText("2.5")
    assert dlg._table.rowCount() == 1


@standalone
def test_edit_while_filtered_writes_the_right_row(
    qapp: QtWidgets.QApplication, sample_df: pd.DataFrame
):
    """Regression: a filtered view must not write through the view row.

    The table was repopulated from a filtered frame but edits were applied with
    ``df.iloc[view_row, col]``, silently corrupting an unrelated row.
    """
    dlg = DataFrameEditor(sample_df, None)
    dlg._search_edit.setText("4.2")
    assert dlg._table.rowCount() == 1

    item = dlg._table.item(0, 0)
    item.setText("99")
    assert sample_df.iloc[3, 0] == 99.0
    assert sample_df.iloc[0, 0] == 1.0


@standalone
def test_edit_after_sorting_writes_the_right_row(
    qapp: QtWidgets.QApplication, sample_df: pd.DataFrame
):
    """Sorting reorders items, so the source row must travel with the item."""
    dlg = DataFrameEditor(sample_df, None)
    dlg._table.sortItems(1, QtCore.Qt.DescendingOrder)
    # Top row is now int_col == 40, i.e. frame row 3.
    item = dlg._table.item(0, 0)
    item.setText("77")
    assert sample_df.iloc[3, 0] == 77.0
    assert sample_df.iloc[0, 0] == 1.0


# ── ChiSurf-backed implementation ────────────────────────────────────────

with_chisurf = pytest.mark.skipif(
    not HAS_CHISURF, reason="ChiSurf is not installed; the shared branch is not live"
)


@with_chisurf
def test_uses_the_shared_chitable_dialog(qapp: QtWidgets.QApplication, sample_df):
    from chisurf.gui.widgets.chitable import ChiTableDialog

    assert issubclass(DataFrameEditor, ChiTableDialog)
    dlg = DataFrameEditor(sample_df, None)
    assert dlg.table.visible_row_count() == 4


@with_chisurf
def test_search_narrows_the_shared_table(qapp: QtWidgets.QApplication, sample_df):
    dlg = DataFrameEditor(sample_df, None)
    dlg.table.set_search_text("2.5")
    assert dlg.table.visible_row_count() == 1
    dlg.table.set_search_text("")
    assert dlg.table.visible_row_count() == 4


@with_chisurf
def test_edits_are_staged_until_accept(qapp: QtWidgets.QApplication, sample_df):
    dlg = DataFrameEditor(sample_df, None)
    model = _model(dlg)
    assert model.setData(model.index(0, 0), "42", QtCore.Qt.EditRole)
    assert sample_df.iloc[0, 0] == 1.0  # staged, not written through
    dlg.accept()
    assert sample_df.iloc[0, 0] == 42.0


def test_module_exposes_the_expected_surface():
    module = importlib.reload(dfe)
    assert hasattr(module, "DataFrameEditor")
    assert hasattr(module, "edit_dataframe")
    assert hasattr(module.DataFrameEditor, "edit_dataframe")
