"""The legacy Qt tables with a vector parameter: an expandable, editable row.

The Qt window's parameter tables are ChiSurf's shared table over the ChiSurf
mirrors of nDXplorer's groups; a vector's elements are published as
``name[pop]`` and the table groups them under one row. Driven the way a user
does: a click on the vector's name opens it, a double-click on an element's
value opens its editor, the number is typed and Enter commits it.

``NDX_VECTOR_SHOTS=<dir>`` saves the tables there, for looking at.
"""
import os
import pathlib

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("chisurf.gui.autoform.sections.parameter_table",
                    reason="chisurf fitting table not importable")


@pytest.fixture(scope="module")
def qapp():
    from qtpy import QtWidgets

    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _names(table):
    model = table.table_model
    from qtpy import QtCore

    return [str(model.index(r, 0).data(QtCore.Qt.DisplayRole)).strip()
            for r in range(model.rowCount())]


def _row(table, name):
    return next(r for r, n in enumerate(_names(table)) if n.endswith(name))


def _click_name(qapp, table, row):
    from qtpy import QtCore
    from qtpy.QtTest import QTest

    view = table.table_view
    rect = view.visualRect(table.table_model.index(row, 0))
    QTest.mouseClick(view.viewport(), QtCore.Qt.LeftButton, pos=rect.center())
    qapp.processEvents()


def _type_value(qapp, table, row, text):
    """Double-click the Value cell, type *text*, press Enter."""
    from qtpy import QtCore, QtWidgets
    from qtpy.QtTest import QTest

    view = table.table_view
    index = table.table_model.index(row, 1)
    rect = view.visualRect(index)
    QTest.mouseClick(view.viewport(), QtCore.Qt.LeftButton, pos=rect.center())
    QTest.mouseDClick(view.viewport(), QtCore.Qt.LeftButton, pos=rect.center())
    qapp.processEvents()
    editor = view.findChild(QtWidgets.QLineEdit)
    assert editor is not None and editor.isVisible(), "the cell did not open for typing"
    editor.selectAll()
    QTest.keyClicks(editor, text)
    QTest.keyClick(editor, QtCore.Qt.Key_Return)
    qapp.processEvents()


def _shot(widget, name):
    folder = os.environ.get("NDX_VECTOR_SHOTS")
    if folder:
        pathlib.Path(folder).mkdir(parents=True, exist_ok=True)
        widget.grab().save(str(pathlib.Path(folder) / f"{name}.png"))


def test_a_vector_constant_opens_and_an_element_is_typed(qapp):
    from ndxplorer.ui.parameter_editor import ParameterEditor

    fired = []
    ed = ParameterEditor(callback=lambda *a: fired.append(1))
    try:
        ed.resize(460, 640)
        ed.show()
        rows = ed._table.table_model.rowCount()
        ed.set_vector("gG/gR", [0.61, 0.83], ["HF", "LF"])
        table = ed._table
        # One row for the vector, closed: no summary line under the table any more.
        assert table.table_model.rowCount() == rows
        assert not hasattr(ed, "_vectors")
        parent = _row(table, "gG/gR [2]")
        assert _names(table)[parent].startswith("▸")
        _click_name(qapp, table, parent)
        assert _names(table)[parent + 1:parent + 4] == ["(global)", "HF", "LF"]
        _type_value(qapp, table, parent + 3, "0.9")
        assert ed._group.get("gG/gR[LF]").value == pytest.approx(0.9)
        assert ed.dict["gG/gR[LF]"] == pytest.approx(0.9) and fired
        # The parent's Fixed frees every element.
        from qtpy import QtCore

        table.table_model.setData(table.table_model.index(parent, 2), False, QtCore.Qt.EditRole)
        assert not any(e.fixed for e in ed._group.get("gG/gR").elements)
        _shot(ed, "qt_constants")
    finally:
        ed.close()


def test_stored_vectors_are_applied_through_the_editor(qapp):
    from ndxplorer.ui.parameter_editor import ParameterEditor

    ed = ParameterEditor()
    try:
        done = ed.apply_vectors({"gG/gR": {"values": [0.5, 0.7], "populations": ["0", "1"],
                                           "uncertainties": {"1": 0.02},
                                           "column": "Population"},
                                 "skipped": {"values": []}})
        assert done == ["gG/gR"]
        assert ed.dict["gG/gR[1]"] == 0.7
        assert ed._cg.vector_uncertainty(ed._group, "gG/gR", "1") == 0.02
        assert ed._cg.vector_axis(ed._group, "gG/gR").column == "Population"
        assert "gG/gR [2]" in " ".join(_names(ed._table))
    finally:
        ed.close()


def test_a_curve_parameter_vector_opens_and_an_element_is_typed(qapp):
    from ndxplorer.plotting.curve_overlay import CurveWidget

    curve = CurveWidget("line", "a*x+b")
    try:
        curve.resize(460, 300)
        curve.show()
        curve._group.get("a").set_vector([2.0, 3.0], ["HF", "LF"])
        table = curve._table
        parent = _row(table, "a [2]")
        _click_name(qapp, table, parent)
        assert _names(table)[parent + 2] == "HF"
        _type_value(qapp, table, parent + 2, "2.5")
        assert curve._group.get("a[HF]").value == pytest.approx(2.5)
        _shot(curve, "qt_curve")
    finally:
        curve.close()
