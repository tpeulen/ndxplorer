"""ValueTable — ChiSurf's table when ChiSurf is there, a plain one when it is not.

ndXplorer installs standalone and must not depend on ChiSurf, so it cannot simply
import the shared table. But when ChiSurf *is* present there is no reason to show
a bare ``QTableWidget``: ``chisurf.gui.widgets.chitable`` brings search, per-column
filters, sorting, a column picker, value colouring and CSV export that the local
version does not have. This is the same arrangement
:mod:`ndxplorer.ui.parameter_editor` already uses, applied to the ordinary item-based tables.

Both branches present the ``QTableWidget`` item API the call sites already use --
``item``, ``setItem``, ``rowCount``, ``insertRow`` and so on -- so a call site does
not care which one it got.

**The one thing a call site must care about.** With sorting and filtering, the row
you see is not the row the data is in. ``selectionModel().selectedRows()`` hands
back *view* rows; using one to index the underlying list reads the wrong record
the moment the user sorts a column. Hence :meth:`ValueTable.selected_source_rows`
and :meth:`ValueTable.source_row`, which are correct in both branches and are the
only supported way to get from a selection to a record. The plain branch maps
identity, so the call sites stay single-path.
"""

from __future__ import annotations

from typing import List, Optional

from qtpy import QtCore, QtGui, QtWidgets

__all__ = ["ValueTable", "TableItem", "HAS_CHITABLE"]

try:
    from chisurf.gui.widgets.chitable import ChiTableWidget, TableFeature

    HAS_CHITABLE = True
except ImportError:  # pragma: no cover - exercised only without ChiSurf
    HAS_CHITABLE = False


if HAS_CHITABLE:

    class ValueTable(ChiTableWidget):
        """An item table backed by ChiSurf's shared table widget.

        Wraps a :class:`~qtpy.QtGui.QStandardItemModel`, which keeps the item
        semantics the call sites are written against while the surrounding widget
        supplies the search, filter, sort, column-picker and export machinery.

        Parameters
        ----------
        rows, columns : int
            Initial model size.
        parent : qtpy.QtWidgets.QWidget, optional
            Parent widget.
        """

        #: Re-exposed so call sites can keep using the item-level signals.
        itemChanged = QtCore.Signal(object)
        itemSelectionChanged = QtCore.Signal()

        def __init__(self, rows: int = 0, columns: int = 0, parent=None):
            self._model = QtGui.QStandardItemModel(rows, columns)
            super().__init__(
                model=self._model,
                # Editing is driven by the call site's own item flags, and value
                # colouring would fight the explicit per-item formatting these
                # tables already do.
                features=(
                    TableFeature.SEARCH
                    | TableFeature.COLUMN_FILTERS
                    | TableFeature.SORT
                    | TableFeature.COLUMN_PICKER
                    | TableFeature.EXPORT
                    | TableFeature.STATUSBAR
                    | TableFeature.EDIT
                ),
                parent=parent,
            )
            self._model.itemChanged.connect(self.itemChanged.emit)
            selection = self.table_view.selectionModel()
            if selection is not None:
                selection.selectionChanged.connect(
                    lambda *_: self.itemSelectionChanged.emit()
                )

        # -- item API ----------------------------------------------------

        def item(self, row: int, column: int) -> Optional[QtGui.QStandardItem]:
            """Return the item at a **source** row and column."""
            return self._model.item(row, column)

        def setItem(self, row: int, column: int, item) -> None:
            """Place an item at a **source** row and column."""
            self._model.setItem(row, column, item)

        def rowCount(self) -> int:
            """Number of rows held, regardless of how many are filtered in."""
            return self._model.rowCount()

        def columnCount(self) -> int:
            """Number of columns held."""
            return self._model.columnCount()

        def setRowCount(self, rows: int) -> None:
            """Resize the model's rows."""
            self._model.setRowCount(rows)

        def setColumnCount(self, columns: int) -> None:
            """Resize the model's columns."""
            self._model.setColumnCount(columns)

        def insertRow(self, row: int) -> None:
            """Insert an empty row at a **source** position."""
            self._model.insertRow(row)

        def removeRow(self, row: int) -> None:
            """Remove a **source** row."""
            self._model.removeRow(row)

        def setHorizontalHeaderLabels(self, labels) -> None:
            """Set the column headers."""
            self._model.setHorizontalHeaderLabels(list(labels))

        # -- row mapping -------------------------------------------------

        def source_row(self, view_row: int) -> int:
            """Map a displayed row back to the row the data is in."""
            proxy = self.proxy
            if proxy is None:
                return view_row
            return proxy.mapToSource(proxy.index(view_row, 0)).row()

        def selected_source_rows(self) -> List[int]:
            """Rows of the selected records, in the model's own numbering.

            The only supported way to go from a selection to a record: the raw
            ``selectionModel().selectedRows()`` reports what is on screen, which
            stops matching the data as soon as anything is sorted or filtered.
            """
            selection = self.table_view.selectionModel()
            if selection is None:
                return []
            proxy = self.proxy
            rows = set()
            for index in selection.selectedIndexes():
                rows.add(
                    proxy.mapToSource(index).row() if proxy is not None else index.row()
                )
            return sorted(rows)

        # -- view passthroughs -------------------------------------------

        def setEditTriggers(self, triggers) -> None:
            """Forward to the inner view."""
            self.table_view.setEditTriggers(triggers)

        def setSelectionBehavior(self, behavior) -> None:
            """Forward to the inner view."""
            self.table_view.setSelectionBehavior(behavior)

        def setShowGrid(self, show: bool) -> None:
            """Forward to the inner view."""
            self.table_view.setShowGrid(show)

        def setWordWrap(self, wrap: bool) -> None:
            """Forward to the inner view."""
            self.table_view.setWordWrap(wrap)

        def setSizeAdjustPolicy(self, policy) -> None:
            """Forward to the inner view."""
            self.table_view.setSizeAdjustPolicy(policy)

        def selectionModel(self):
            """Return the inner view's selection model.

            Its indexes are *view* indexes. Prefer
            :meth:`selected_source_rows` unless you genuinely want what is on
            screen.
            """
            return self.table_view.selectionModel()

        def viewport(self):
            """Return the inner view's viewport, for context-menu positioning."""
            return self.table_view.viewport()

        def installEventFilter(self, filter_object) -> None:
            """Filter the inner view's events as well as this widget's.

            Key presses land on the focused view, not on the container, so a
            filter installed only on the container would never see them. Use
            :meth:`owns` to recognise either object in the filter.
            """
            super().installEventFilter(filter_object)
            self.table_view.installEventFilter(filter_object)

        def owns(self, obj) -> bool:
            """Whether *obj* is this table or the view inside it."""
            return obj is self or obj is self.table_view

        def horizontalHeader(self):
            """Return the inner view's horizontal header."""
            return self.table_view.horizontalHeader()

        def verticalHeader(self):
            """Return the inner view's vertical header."""
            return self.table_view.verticalHeader()

else:

    class ValueTable(QtWidgets.QTableWidget):  # type: ignore[no-redef]
        """Plain item table used when ChiSurf is not installed.

        Same surface as the ChiSurf-backed branch, so call sites are single-path.
        Without a proxy the row mapping is the identity, which is why
        :meth:`source_row` can be called unconditionally.
        """

        def __init__(self, rows: int = 0, columns: int = 0, parent=None):
            super().__init__(rows, columns, parent)

        def source_row(self, view_row: int) -> int:
            """Map a displayed row to the data row; identity without a proxy."""
            return view_row

        def selected_source_rows(self) -> List[int]:
            """Rows of the selected records."""
            selection = self.selectionModel()
            if selection is None:
                return []
            return sorted({index.row() for index in selection.selectedIndexes()})

        def owns(self, obj) -> bool:
            """Whether *obj* is this table; there is no separate inner view."""
            return obj is self


#: The item class the live :class:`ValueTable` branch expects. ``QStandardItem``
#: and ``QTableWidgetItem`` present the same surface for everything these tables
#: use -- text, flags, check state, alignment, data roles, brushes -- so call
#: sites construct ``TableItem`` and stay single-path.
TableItem = QtGui.QStandardItem if HAS_CHITABLE else QtWidgets.QTableWidgetItem
