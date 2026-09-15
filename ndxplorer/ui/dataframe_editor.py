"""DataFrameEditor — spreadsheet-style editor for pandas DataFrames.

Uses ChiSurf's ``chitable`` widget family when ChiSurf is importable, and falls
back to a self-contained local implementation otherwise, the same arrangement
:mod:`ndxplorer.ui.parameter_editor` uses. ndXplorer installs standalone (it does
not depend on ChiSurf), so the fallback has to stay; when ChiSurf *is* present
the shared widget brings sorting, per-column filters, value colouring, a column
picker and CSV export that the local version does not have.

Either way the public surface is identical — ``DataFrameEditor(df, parent)``,
``.dataframe``, ``.exec_()`` and ``edit_dataframe()`` — so call sites do not care
which branch is live.
"""

from __future__ import annotations

from typing import Any, List, Optional

import numpy as np
import pandas as pd
from qtpy import QtCore, QtGui, QtWidgets

from .glyphs import Glyphs, label as glyph_label

try:
    from chisurf.gui.widgets.chitable import ArraySource, ChiTableDialog

    HAS_CHISURF = True
except ImportError:  # pragma: no cover - exercised only without ChiSurf
    HAS_CHISURF = False


if HAS_CHISURF:

    class DataFrameEditor(ChiTableDialog):
        """Modal editor backed by ChiSurf's chitable dialog.

        chitable is deliberately pandas-free (its ``DataFrameSource`` was
        retired), so the frame is adapted through ``ArraySource``: one array
        per column, edits written back into ``df`` as they happen. Importing
        the retired name made this whole branch an ImportError, and ndX then
        fell back silently to the per-cell ``QTableWidget`` editor -- the
        "several seconds to open a burst table" one.

        Both call sites hand in a *copy* and commit it on accept, so the
        immediate write-back keeps the staged-edit contract they rely on.

        Parameters
        ----------
        df : pandas.DataFrame
            The frame to edit. Mutated in place as cells are changed.
        parent : qtpy.QtWidgets.QWidget, optional
            Parent widget.
        """

        def __init__(self, df: pd.DataFrame, parent=None):
            self._df = df
            columns = {str(c): df[c].to_numpy() for c in df.columns}

            def _write_back(key: str, row: int, value: Any) -> bool:
                try:
                    df.iloc[row, df.columns.get_loc(key)] = value
                    return True
                except Exception:
                    return False

            super().__init__(
                source=ArraySource(
                    columns,
                    on_set=_write_back,
                    editable_keys=list(columns),
                ),
                title="DataFrame Editor",
                parent=parent,
            )

        @property
        def dataframe(self) -> pd.DataFrame:
            """The edited frame, same object that was passed in."""
            return self._df

        @staticmethod
        def edit_dataframe(
            df: pd.DataFrame, parent=None
        ) -> Optional[pd.DataFrame]:
            """Show the editor and return the edited copy, or ``None``.

            Parameters
            ----------
            df : pandas.DataFrame
                The frame to edit; never mutated.
            parent : qtpy.QtWidgets.QWidget, optional
                Parent widget.

            Returns
            -------
            pandas.DataFrame or None
            """
            working = df.copy()
            dlg = DataFrameEditor(working, parent)
            if dlg.exec_() == QtWidgets.QDialog.Accepted:
                return working
            return None

else:

    class DataFrameEditor(QtWidgets.QDialog):  # type: ignore[no-redef]
        """Standalone editor used when ChiSurf is not installed.

        Provides sortable columns, type-aware editing, search, copy/paste and
        keyboard navigation over a ``QTableWidget``.

        Parameters
        ----------
        df : pandas.DataFrame
            The frame to edit. Mutated in place as cells are changed.
        parent : qtpy.QtWidgets.QWidget, optional
            Parent widget.
        """

        def __init__(self, df: pd.DataFrame, parent=None):
            super().__init__(parent)
            self._original = df.copy()
            self._df = df
            #: Source row index of each displayed row, indexed by view row. The
            #: table is filtered and sorted independently of ``_df``, so an edit
            #: must never use the view row as a frame position.
            self._source_rows: List[int] = list(range(len(df.index)))
            self._setup_ui()
            self._populate()

        # ------------------------------------------------------------ UI

        def _setup_ui(self):
            """Build the search bar, table, statistics line and buttons."""
            self.setWindowTitle("DataFrame Editor")
            self.resize(900, 600)
            self.setMinimumSize(500, 300)

            layout = QtWidgets.QVBoxLayout(self)
            layout.setSpacing(4)
            layout.setContentsMargins(6, 6, 6, 6)

            search_layout = QtWidgets.QHBoxLayout()
            search_layout.setSpacing(4)
            self._search_edit = QtWidgets.QLineEdit()
            self._search_edit.setPlaceholderText("Search...")
            self._search_edit.setClearButtonEnabled(True)
            self._search_edit.textChanged.connect(self._on_search)
            search_layout.addWidget(self._search_edit)

            self._search_label = QtWidgets.QLabel()
            search_layout.addWidget(self._search_label)
            layout.addLayout(search_layout)

            self._table = QtWidgets.QTableWidget()
            self._table.setAlternatingRowColors(True)
            self._table.setSortingEnabled(True)
            self._table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectItems)
            self._table.setSelectionMode(QtWidgets.QAbstractItemView.ContiguousSelection)
            self._table.horizontalHeader().setSectionsMovable(True)
            self._table.horizontalHeader().setStretchLastSection(True)
            self._table.verticalHeader().setDefaultSectionSize(24)
            self._table.horizontalHeader().setDefaultSectionSize(100)
            self._table.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
            self._table.customContextMenuRequested.connect(self._on_context_menu)
            self._table.cellChanged.connect(self._on_cell_changed)
            self._table.installEventFilter(self)
            layout.addWidget(self._table)

            stats_layout = QtWidgets.QHBoxLayout()
            stats_layout.setSpacing(12)
            self._stats_label = QtWidgets.QLabel()
            stats_layout.addWidget(self._stats_label)
            stats_layout.addStretch()
            self._modified_label = QtWidgets.QLabel()
            self._modified_label.setStyleSheet("color: #cc7000;")
            self._modified_label.setVisible(False)
            stats_layout.addWidget(self._modified_label)
            layout.addLayout(stats_layout)

            btn_layout = QtWidgets.QHBoxLayout()
            btn_layout.addStretch()
            self._btn_reset = QtWidgets.QPushButton(glyph_label(Glyphs.RESET, "Reset"))
            self._btn_reset.clicked.connect(self._on_reset)
            btn_layout.addWidget(self._btn_reset)
            self._btn_apply = QtWidgets.QPushButton(glyph_label(Glyphs.CHECK, "Apply"))
            self._btn_apply.clicked.connect(self.accept)
            self._btn_apply.setDefault(True)
            btn_layout.addWidget(self._btn_apply)
            self._btn_cancel = QtWidgets.QPushButton(glyph_label(Glyphs.CLOSE, "Cancel"))
            self._btn_cancel.clicked.connect(self.reject)
            btn_layout.addWidget(self._btn_cancel)
            layout.addLayout(btn_layout)

            self._update_stats()

        # ------------------------------------------------------- Populate

        @staticmethod
        def _is_numeric(dtype) -> bool:
            """Return whether a column dtype holds numbers.

            ``pandas.api.types.is_numeric_dtype`` understands extension dtypes
            (the nullable ``Float64`` a nullable-dtype reader produces);
            ``numpy.issubdtype`` raises ``TypeError`` on them.

            Parameters
            ----------
            dtype : object
                A numpy or pandas dtype.

            Returns
            -------
            bool
            """
            try:
                return bool(pd.api.types.is_numeric_dtype(dtype))
            except (TypeError, ValueError):
                return False

        def _populate(self, df: Optional[pd.DataFrame] = None, source_rows=None):
            """Fill the table widget from a frame.

            Parameters
            ----------
            df : pandas.DataFrame, optional
                Frame to display; defaults to the full edited frame.
            source_rows : sequence of int, optional
                Positional index in ``self._df`` of each displayed row. Defaults
                to the identity mapping.
            """
            df = df if df is not None else self._df
            self._source_rows = (
                list(source_rows) if source_rows is not None else list(range(len(df.index)))
            )
            self._table.blockSignals(True)
            self._table.setSortingEnabled(False)

            nrows, ncols = df.shape
            self._table.setRowCount(nrows)
            self._table.setColumnCount(ncols)
            self._table.setHorizontalHeaderLabels([str(c) for c in df.columns])
            self._table.setVerticalHeaderLabels([str(i) for i in df.index])

            self._col_dtypes = [df.iloc[:, j].dtype for j in range(ncols)]

            # Per COLUMN, not per cell: scalar ``df.iloc[i, j]`` costs a frame
            # lookup each call, and at bursts-table size (5k rows x 20 columns)
            # that alone was seconds of the "editor takes forever to open".
            na_color = QtGui.QColor("#999999")
            right = QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter
            for j in range(ncols):
                is_numeric = self._is_numeric(self._col_dtypes[j])
                vals = df.iloc[:, j].to_numpy()
                nas = pd.isna(vals)
                for i in range(nrows):
                    val = vals[i]
                    item = QtWidgets.QTableWidgetItem()
                    # The source row travels with the item, so an edit stays
                    # correct after the table has been filtered *or* sorted.
                    item.setData(QtCore.Qt.UserRole, int(self._source_rows[i]))
                    if nas[i]:
                        item.setText("")
                        item.setForeground(na_color)
                        item.setToolTip("NaN")
                    elif is_numeric:
                        if isinstance(val, (float, np.floating)):
                            item.setText(f"{val:.6g}")
                        else:
                            item.setText(str(val))
                        item.setTextAlignment(right)
                    else:
                        item.setText(str(val))
                    item.setFlags(item.flags() | QtCore.Qt.ItemIsEditable)
                    self._table.setItem(i, j, item)

            self._table.setSortingEnabled(True)
            self._table.blockSignals(False)
            self._resize_columns()
            self._update_stats()

        def _resize_columns(self):
            """Size columns to their content, clamped to sane bounds."""
            header = self._table.horizontalHeader()
            # Measure a sample, not every row: ResizeToContents otherwise
            # lays out all 100k+ cells a burst table brings.
            header.setResizeContentsPrecision(100)
            header.resizeSections(QtWidgets.QHeaderView.ResizeToContents)
            for j in range(self._table.columnCount()):
                w = self._table.columnWidth(j)
                self._table.setColumnWidth(j, max(60, min(w + 20, 350)))
            header.setStretchLastSection(True)

        # --------------------------------------------------------- Search

        def _on_search(self, text: str):
            """Show only rows containing ``text`` in any column.

            Parameters
            ----------
            text : str
                Case-insensitive search string.
            """
            if not text:
                self._search_label.setText("")
                self._populate()
                return

            needle = text.lower()
            df = self._df
            mask = df.map(
                lambda v: needle in str(v).lower() if pd.notna(v) else False
            ).any(axis=1)
            positions = np.flatnonzero(mask.to_numpy())
            self._search_label.setText(
                f"{len(positions)} / {len(df)} rows" if len(positions) < len(df) else ""
            )
            self._populate(df.iloc[positions], source_rows=positions)

        # -------------------------------------------------------- Editing

        def _source_row_of(self, row: int, col: int) -> int:
            """Return the frame row a displayed cell belongs to.

            Parameters
            ----------
            row : int
                View row index.
            col : int
                Column index.

            Returns
            -------
            int
                ``-1`` when the cell carries no source mapping.
            """
            item = self._table.item(row, col)
            if item is None:
                return -1
            stored = item.data(QtCore.Qt.UserRole)
            return int(stored) if stored is not None else -1

        def _on_cell_changed(self, row: int, col: int):
            """Validate an edited cell and write it to the frame.

            Parameters
            ----------
            row : int
                View row index.
            col : int
                Column index.
            """
            item = self._table.item(row, col)
            src = self._source_row_of(row, col)
            if item is None or src < 0:
                return

            raw = item.text().strip()
            dtype = self._col_dtypes[col]

            if self._is_numeric(dtype):
                try:
                    value = self._parse_cell(raw, dtype)
                except (ValueError, TypeError):
                    QtWidgets.QMessageBox.warning(
                        self,
                        "Invalid Value",
                        f"Column '{self._df.columns[col]}' expects a numeric value.",
                    )
                    orig = self._df.iloc[src, col]
                    self._table.blockSignals(True)
                    item.setText(
                        f"{orig:.6g}" if isinstance(orig, (float, np.floating)) else str(orig)
                    )
                    self._table.blockSignals(False)
                    return
                self._table.blockSignals(True)
                item.setText(
                    f"{value:.6g}" if isinstance(value, (float, np.floating)) else str(value)
                )
                self._table.blockSignals(False)
            else:
                value = raw

            self._df.iloc[src, col] = value
            self._mark_modified()

        @staticmethod
        def _parse_cell(raw: str, dtype) -> Any:
            """Convert a cell string to the column's type.

            Parameters
            ----------
            raw : str
                Text as typed.
            dtype : object
                The column's dtype.

            Returns
            -------
            object

            Raises
            ------
            ValueError
                If a numeric column receives non-numeric text.
            """
            raw = raw.strip()
            if raw == "" or raw.lower() in ("nan", "none"):
                return np.nan
            try:
                numeric = bool(pd.api.types.is_numeric_dtype(dtype))
            except (TypeError, ValueError):
                numeric = False
            if not numeric:
                return raw
            if "." in raw or "e" in raw.lower():
                return float(raw)
            return int(raw)

        def _mark_modified(self):
            """Show the "Modified" marker."""
            self._modified_label.setText("Modified")
            self._modified_label.setVisible(True)

        def _on_reset(self):
            """Restore the frame to its state when the dialog opened."""
            self._df = self._original.copy()
            self._modified_label.setVisible(False)
            self._search_edit.clear()
            self._populate()

        # --------------------------------------------------- Context menu

        def _on_context_menu(self, pos: QtCore.QPoint):
            """Show the cell context menu.

            Parameters
            ----------
            pos : qtpy.QtCore.QPoint
                Position in viewport coordinates.
            """
            menu = QtWidgets.QMenu(self)
            copy_action = menu.addAction(glyph_label(Glyphs.COPY, "Copy"))
            copy_action.setShortcut(QtGui.QKeySequence.Copy)
            copy_action.triggered.connect(self._copy_selection)
            paste_action = menu.addAction("Paste")
            paste_action.setShortcut(QtGui.QKeySequence.Paste)
            paste_action.triggered.connect(self._paste_selection)
            menu.addSeparator()
            select_all_action = menu.addAction(glyph_label(Glyphs.CHECKBOX_ON, "Select All"))
            select_all_action.setShortcut(QtGui.QKeySequence.SelectAll)
            select_all_action.triggered.connect(self._table.selectAll)
            menu.exec_(self._table.viewport().mapToGlobal(pos))

        def _copy_selection(self):
            """Copy the selected cells to the clipboard as TSV."""
            selected = self._table.selectedRanges()
            if not selected:
                return
            rng = selected[0]
            rows = []
            for i in range(rng.topRow(), rng.bottomRow() + 1):
                cells = []
                for j in range(rng.leftColumn(), rng.rightColumn() + 1):
                    item = self._table.item(i, j)
                    cells.append(item.text() if item else "")
                rows.append("\t".join(cells))
            QtWidgets.QApplication.clipboard().setText("\n".join(rows))

        def _paste_selection(self):
            """Paste tab-separated clipboard text into the selection."""
            text = QtWidgets.QApplication.clipboard().text()
            selected = self._table.selectedRanges()
            if not text or not selected:
                return
            rows_data = [line.split("\t") for line in text.splitlines()]
            rng = selected[0]
            for i, row_vals in enumerate(rows_data):
                for j, val in enumerate(row_vals):
                    row, col = rng.topRow() + i, rng.leftColumn() + j
                    if row >= self._table.rowCount() or col >= self._table.columnCount():
                        break
                    item = self._table.item(row, col)
                    if item is not None and item.flags() & QtCore.Qt.ItemIsEditable:
                        item.setText(val.strip())

        # -------------------------------------------------- Event filter

        def eventFilter(self, obj, event):  # noqa: N802 (Qt override)
            """Handle clipboard and reset shortcuts on the table.

            Parameters
            ----------
            obj : qtpy.QtCore.QObject
                Object the event was sent to.
            event : qtpy.QtCore.QEvent
                The event.

            Returns
            -------
            bool
                ``True`` when the event was consumed.
            """
            if obj is self._table and event.type() == QtCore.QEvent.KeyPress:
                key, mod = event.key(), event.modifiers()
                if mod == QtCore.Qt.ControlModifier:
                    if key == QtCore.Qt.Key_C:
                        self._copy_selection()
                        return True
                    if key == QtCore.Qt.Key_V:
                        self._paste_selection()
                        return True
                    if key == QtCore.Qt.Key_A:
                        self._table.selectAll()
                        return True
                    if key == QtCore.Qt.Key_Z:
                        self._on_reset()
                        return True
                if key in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
                    self._table.edit(self._table.currentIndex())
                    return True
            return super().eventFilter(obj, event)

        # ---------------------------------------------------------- Stats

        def _update_stats(self):
            """Refresh the row/column count line."""
            self._stats_label.setText(
                f"{self._table.rowCount()} rows × {self._table.columnCount()} columns"
            )

        # --------------------------------------------------------- Access

        @property
        def dataframe(self) -> pd.DataFrame:
            """Return the edited frame.

            Returns
            -------
            pandas.DataFrame
            """
            return self._df

        @staticmethod
        def edit_dataframe(df: pd.DataFrame, parent=None) -> Optional[pd.DataFrame]:
            """Show the editor and return the edited copy, or ``None``.

            Parameters
            ----------
            df : pandas.DataFrame
                The frame to edit; never mutated.
            parent : qtpy.QtWidgets.QWidget, optional
                Parent widget.

            Returns
            -------
            pandas.DataFrame or None
            """
            dlg = DataFrameEditor(df.copy(), parent)
            if dlg.exec_() == QtWidgets.QDialog.Accepted:
                return dlg.dataframe
            return None


def edit_dataframe(df: pd.DataFrame, parent=None) -> Optional[pd.DataFrame]:
    """Show the editor and return the edited copy, or ``None`` if cancelled.

    Parameters
    ----------
    df : pandas.DataFrame
        The frame to edit; never mutated.
    parent : qtpy.QtWidgets.QWidget, optional
        Parent widget.

    Returns
    -------
    pandas.DataFrame or None
    """
    return DataFrameEditor.edit_dataframe(df, parent)
