"""ndXplorer's item tables use ChiSurf's table when ChiSurf is importable.

ndXplorer installs standalone, so it cannot depend on ChiSurf — but when ChiSurf
is present there is no reason to show a bare ``QTableWidget`` instead of the
shared one, which brings search, per-column filters, sorting, a column picker and
CSV export. :mod:`ndxplorer.ui.table` is that seam.

The tests below concentrate on the hazard the seam introduces: **once a table can
be sorted, the row you see is not the row the data is in.** The Gaussian table
reads selections back to decide which Gaussian to highlight and which to delete,
so a view row used as a data row silently operates on the wrong record.
"""

from __future__ import annotations

import numpy as np
import pytest
from qtpy import QtCore, QtWidgets

from ndxplorer.ui.table import HAS_CHITABLE, TableItem, ValueTable


@pytest.fixture(scope="module")
def qt_app():
    """A single QApplication for the module (offscreen)."""
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


@pytest.fixture
def table(qt_app):
    """A three-row table whose rows are deliberately out of order."""
    widget = ValueTable(0, 3)
    widget.setHorizontalHeaderLabels(["x", "y", "w"])
    for row, values in enumerate([(3.0, 1.0, 0.5), (1.0, 2.0, 0.6), (2.0, 3.0, 0.7)]):
        widget.insertRow(row)
        for column, value in enumerate(values):
            widget.setItem(row, column, TableItem(f"{value:.2f}"))
    widget.show()
    qt_app.processEvents()
    yield widget
    widget.close()


def _view(table):
    """The widget that owns the selection, whichever branch is live."""
    return table.table_view if HAS_CHITABLE else table


def test_the_item_api_is_the_same_either_way(table):
    """Call sites are written against the item API and must not branch."""
    assert table.rowCount() == 3
    assert table.columnCount() == 3
    assert table.item(0, 0).text() == "3.00"
    assert table.item(2, 2).text() == "0.70"


def test_rows_are_addressed_by_source_position(table, qt_app):
    """``item(row, ...)`` always means the data row, never the displayed one."""
    if not HAS_CHITABLE:
        pytest.skip("sorting only exists on the shared-table branch")

    _view(table).sortByColumn(0, QtCore.Qt.AscendingOrder)
    qt_app.processEvents()

    # The view now shows 1.00, 2.00, 3.00 — but the model is untouched.
    assert table.item(0, 0).text() == "3.00"
    assert table.source_row(0) == 1, "the top displayed row is model row 1"


def test_a_selection_resolves_to_the_record_it_shows(table, qt_app):
    """The bug this closes: selecting a sorted row acted on a different one.

    The Gaussian table deletes and highlights by selected row. Reading the view
    row as a data row removes the wrong Gaussian the moment a column is sorted —
    silently, because both rows exist and both look plausible.
    """
    if not HAS_CHITABLE:
        pytest.skip("sorting only exists on the shared-table branch")

    _view(table).sortByColumn(0, QtCore.Qt.AscendingOrder)
    qt_app.processEvents()
    _view(table).selectRow(0)
    qt_app.processEvents()

    rows = table.selected_source_rows()
    assert rows == [1], f"selection resolved to {rows}, not the x=1.00 record"
    assert table.item(rows[0], 0).text() == "1.00"


def test_unsorted_selection_is_the_identity(table, qt_app):
    """Without sorting the two numberings coincide, so nothing is special-cased."""
    _view(table).selectRow(2)
    qt_app.processEvents()
    assert table.selected_source_rows() == [2]
    assert table.source_row(2) == 2


def test_removing_a_row_shrinks_the_model(table):
    """Row removal addresses the model, so it survives any view ordering."""
    table.removeRow(0)
    assert table.rowCount() == 2
    assert table.item(0, 0).text() == "1.00"


def test_the_status_line_counts_rows_added_after_construction(table, qt_app):
    """Rows inserted into a wrapped model must reach the status line.

    Only ``dataChanged`` was connected, which a foreign model does not emit on
    insertion — so a table filled after construction reported "0 rows" while
    plainly showing them.
    """
    if not HAS_CHITABLE:
        pytest.skip("the status line belongs to the shared table")

    qt_app.processEvents()
    assert table.total_row_count() == 3
    table.insertRow(3)
    qt_app.processEvents()
    assert table.total_row_count() == 4


def test_owns_recognises_the_inner_view(table):
    """Key presses arrive at the view, so a filter must recognise both."""
    assert table.owns(table)
    assert table.owns(_view(table))
    assert not table.owns(QtWidgets.QWidget())
