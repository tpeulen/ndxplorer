"""Validated table editor for derived-column equations.

Equations are ``{output_name: "expression"}`` mappings that derive columns
(Proximity ratio, FRET efficiency, Fd/Fa, …) from data columns and constants.
They used to be edited as raw YAML, which is fiddly (indentation, quoting) and
gives no feedback until a recompute silently drops a bad equation.

:class:`EquationEditor` presents them as a table — one row per equation, with
its output name, expression, and a live ✓/✗ validity indicator (parse + every
quoted name resolves to a known column / constant / earlier output). It is a
drop-in for the old ``CodeEditor``: it exposes the same ``text()`` / ``setText``
/ ``load_file`` / ``save_text`` / ``save_callback`` / ``filename`` surface, so
``text()`` still serialises to YAML for the existing save path.
"""

from __future__ import annotations

from collections import OrderedDict
from typing import Callable, List, Optional, Tuple

import yaml
from qtpy import QtCore, QtGui, QtWidgets

from ..core.equation_graph import validate_equation

_OK = "✓"    # ✓
_BAD = "✗"   # ✗


class EquationEditor(QtWidgets.QWidget):
    """Table editor for ``[{name: expression}, ...]`` equations."""

    #: Fired (no args) after Apply, so the host can recompute + redraw.
    applied = QtCore.Signal()

    def __init__(self, parent=None, names_provider: Optional[Callable[[], Tuple[list, list]]] = None):
        super().__init__(parent)
        #: ``() -> (column_names, constant_names)`` used to validate references.
        self._names_provider = names_provider
        #: CodeEditor-compatible attributes.
        self.save_callback: Optional[Callable[[], None]] = None
        self.filename: Optional[str] = None

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(4)

        bar = QtWidgets.QHBoxLayout()
        self._btn_add = QtWidgets.QToolButton()
        self._btn_add.setText("➕")  # heavy plus
        self._btn_add.setToolTip("Add an equation")
        self._btn_add.clicked.connect(self._add_row)
        self._btn_del = QtWidgets.QToolButton()
        self._btn_del.setText("➖")  # heavy minus
        self._btn_del.setToolTip("Remove the selected equation")
        self._btn_del.clicked.connect(self._remove_selected)
        self._btn_names = QtWidgets.QToolButton()
        self._btn_names.setText("\U0001f524 Names")  # input latin letters glyph
        self._btn_names.setToolTip("Show the column / constant names you can reference")
        self._btn_names.clicked.connect(self._show_names)
        self._btn_apply = QtWidgets.QPushButton("Apply")
        self._btn_apply.setToolTip("Validate all equations and recompute the derived columns")
        self._btn_apply.clicked.connect(self.apply)
        bar.addWidget(self._btn_add)
        bar.addWidget(self._btn_del)
        bar.addWidget(self._btn_names)
        bar.addStretch(1)
        bar.addWidget(self._btn_apply)
        layout.addLayout(bar)

        self._table = QtWidgets.QTableWidget(0, 3, self)
        self._table.setHorizontalHeaderLabels(["Output", "Expression", ""])
        hdr = self._table.horizontalHeader()
        hdr.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Interactive)
        hdr.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Stretch)
        hdr.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self._table.setColumnWidth(0, 150)
        self._table.verticalHeader().setVisible(False)
        self._table.itemChanged.connect(self._on_item_changed)
        layout.addWidget(self._table)

        self._status = QtWidgets.QLabel("")
        self._status.setStyleSheet("color: #666; font-size: 9pt;")
        layout.addWidget(self._status)

    # -- names provider ----------------------------------------------------
    def set_names_provider(self, fn: Callable[[], Tuple[list, list]]) -> None:
        self._names_provider = fn

    def _known(self) -> Tuple[list, list, list]:
        cols, consts = [], []
        if self._names_provider is not None:
            try:
                cols, consts = self._names_provider()
            except Exception:
                cols, consts = [], []
        outs = [self._name_at(r) for r in range(self._table.rowCount())]
        return list(cols), list(consts), [o for o in outs if o]

    # -- rows --------------------------------------------------------------
    def _name_at(self, row: int) -> str:
        it = self._table.item(row, 0)
        return it.text().strip() if it is not None else ""

    def _expr_at(self, row: int) -> str:
        it = self._table.item(row, 1)
        return it.text().strip() if it is not None else ""

    def _append_row(self, name: str = "", expr: str = "") -> int:
        row = self._table.rowCount()
        self._table.blockSignals(True)
        self._table.insertRow(row)
        self._table.setItem(row, 0, QtWidgets.QTableWidgetItem(name))
        self._table.setItem(row, 1, QtWidgets.QTableWidgetItem(expr))
        status = QtWidgets.QTableWidgetItem("")
        status.setFlags(QtCore.Qt.ItemIsEnabled)  # read-only
        status.setTextAlignment(QtCore.Qt.AlignCenter)
        self._table.setItem(row, 2, status)
        self._table.blockSignals(False)
        return row

    def _add_row(self):
        row = self._append_row()
        self._validate_all()
        self._table.setCurrentCell(row, 0)
        self._table.editItem(self._table.item(row, 0))

    def _remove_selected(self):
        rows = sorted({i.row() for i in self._table.selectedItems()}, reverse=True)
        if not rows:
            return
        self._table.blockSignals(True)
        for r in rows:
            self._table.removeRow(r)
        self._table.blockSignals(False)
        self._validate_all()

    def _on_item_changed(self, _item):
        self._validate_all()

    # -- validation --------------------------------------------------------
    def _validate_all(self):
        cols, consts, outs = self._known()
        n_bad = 0
        for row in range(self._table.rowCount()):
            expr = self._expr_at(row)
            name = self._name_at(row)
            # An output can reference earlier outputs; pass all output names (the
            # engine topologically orders, so forward refs are fine).
            ok, msg = validate_equation(expr, cols, consts, outs)
            if not name:
                ok, msg = False, "missing output name"
            self._set_status(row, ok, msg)
            if not ok:
                n_bad += 1
        total = self._table.rowCount()
        if n_bad:
            self._status.setText(f"{total} equation(s), {n_bad} with problems")
        else:
            self._status.setText(f"{total} equation(s), all valid")

    def _set_status(self, row: int, ok: bool, msg: Optional[str]):
        item = self._table.item(row, 2)
        if item is None:
            return
        item.setText(_OK if ok else _BAD)
        item.setForeground(QtGui.QBrush(QtGui.QColor("#2e7d32" if ok else "#c62828")))
        item.setToolTip("" if ok else (msg or "invalid"))

    # -- names reference ---------------------------------------------------
    def _show_names(self):
        cols, consts, outs = self._known()
        dlg = QtWidgets.QDialog(self)
        dlg.setWindowTitle("Available names")
        dlg.setMinimumSize(360, 420)
        lay = QtWidgets.QVBoxLayout(dlg)
        lay.addWidget(QtWidgets.QLabel(
            "Reference these in expressions as quoted names, e.g. 'Sg' - 'Bg'.\n"
            "Double-click to copy a name to the clipboard."))
        lst = QtWidgets.QListWidget()
        for label, group in (("Constants", consts), ("Columns / outputs", sorted(set(cols) | set(outs)))):
            hdr = QtWidgets.QListWidgetItem(f"— {label} —")
            hdr.setFlags(QtCore.Qt.ItemIsEnabled)
            hdr.setForeground(QtGui.QBrush(QtGui.QColor("#888")))
            lst.addItem(hdr)
            for n in group:
                lst.addItem(QtWidgets.QListWidgetItem(str(n)))
        lst.itemDoubleClicked.connect(
            lambda it: QtWidgets.QApplication.clipboard().setText(f"'{it.text()}'")
        )
        lay.addWidget(lst)
        btn = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Close)
        btn.rejected.connect(dlg.reject)
        btn.accepted.connect(dlg.accept)
        lay.addWidget(btn)
        dlg.exec_()

    # -- equations <-> table ----------------------------------------------
    def equations(self) -> List[dict]:
        """Return the current equations as ``[{name: expr}, ...]`` (valid rows)."""
        out = []
        for row in range(self._table.rowCount()):
            name, expr = self._name_at(row), self._expr_at(row)
            if name and expr:
                out.append({name: expr})
        return out

    def set_equations(self, equations) -> None:
        self._table.blockSignals(True)
        self._table.setRowCount(0)
        for mapping in (equations or []):
            for name, expr in mapping.items():
                self._append_row(str(name), str(expr))
        self._table.blockSignals(False)
        self._validate_all()

    # -- CodeEditor-compatible surface ------------------------------------
    def text(self) -> str:
        """Serialise the table to YAML (a list of one-key maps)."""
        return yaml.safe_dump(self.equations(), sort_keys=False, default_flow_style=False)

    def setText(self, text: str) -> None:  # noqa: N802 (Qt naming)
        try:
            data = yaml.safe_load(text) or []
        except Exception:
            data = []
        self.set_equations(data)

    def load_file(self, filename=None, **kwargs):
        if filename is None:
            filename, _ = QtWidgets.QFileDialog.getOpenFileName(self, "Open equations", "", "YAML (*.yaml *.yml)")
        if not filename:
            return
        try:
            with open(filename, encoding="utf-8") as fp:
                self.setText(fp.read())
            self.filename = filename
        except IOError as exc:  # pragma: no cover - UI path
            QtWidgets.QMessageBox.warning(self, "Equations", f"Could not load:\n{exc}")

    def save_text(self, event=None):
        if not self.filename:
            self.filename, _ = QtWidgets.QFileDialog.getSaveFileName(self, "Save equations", "", "YAML (*.yaml *.yml)")
            if not self.filename:
                return
        try:
            with open(self.filename, "w", encoding="utf-8") as fp:
                fp.write(self.text())
        except IOError as exc:  # pragma: no cover - UI path
            QtWidgets.QMessageBox.warning(self, "Equations", f"Could not save:\n{exc}")
            return
        if callable(self.save_callback):
            self.save_callback()

    def apply(self):
        """Validate, push to the host via save_callback, and request a recompute."""
        self._validate_all()
        if callable(self.save_callback):
            self.save_callback()
        self.applied.emit()


__all__ = ["EquationEditor"]
