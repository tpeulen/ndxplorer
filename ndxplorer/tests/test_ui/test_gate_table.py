"""The Qt Selection table is a view of the gate list, and edits go back into it.

``plot_control.gates`` (:class:`ndxplorer.core.gates.GateList`) is what the
window gates by. These drive the QTableWidget the way a user does -- tick a
check box, type into a cell -- and check that the list, not the widget, is
what changed and what ``get_selections`` answers from.
"""

from __future__ import annotations

import time

import numpy as np
import pytest
from qtpy import QtWidgets

from ndxplorer.core.data_source import MaskDataSelection, RectangularDataSelection


@pytest.fixture(scope="module")
def qapp():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


@pytest.fixture
def window(qapp):
    from ndxplorer.core.data_source import DataSource
    from ndxplorer.core.plot_main import NDXplorer

    rng = np.random.default_rng(3)
    window = NDXplorer()
    window.show()
    window.data_source = DataSource.from_columns({
        "Tau": rng.normal(3.0, 0.5, 2000).astype(np.float32),
        "r": rng.normal(0.3, 0.05, 2000).astype(np.float32),
    })
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        qapp.processEvents()
        if window.plot_control.comboBoxSelX.count():
            break
    yield window
    window.close()


def test_rows_come_from_the_list_and_flags_go_back(window, qapp):
    control = window.plot_control
    control.addSelection(0, 3.5, 2.5, False, True, "Tau")
    table = control.tableWidget
    assert table.rowCount() == 1 and table.item(0, 1).text() == "2.5"
    table.cellWidget(0, 3).setChecked(True)
    qapp.processEvents()
    assert control.gates[0].invert
    (sel,) = control.get_selections()
    assert isinstance(sel, RectangularDataSelection) and sel.invert
    assert (sel.lower, sel.upper) == (2.5, 3.5)


def test_a_typed_bound_is_written_and_a_bad_one_reverts(window, qapp, monkeypatch):
    monkeypatch.setattr(window, "is_data_ready", lambda: True)
    monkeypatch.setattr(window, "update_plots", lambda *a, **k: None)
    control = window.plot_control
    control.addSelection(0, 1.0, 2.0, False, True, "Tau")
    table = control.tableWidget
    table.item(0, 2).setText("4.5")
    assert control.gates[0].upper == 4.5
    table.item(0, 1).setText("junk")
    assert control.gates[0].lower == 1.0 and table.item(0, 1).text() == "1.0"


def test_a_mask_row_keeps_its_object_and_deletes_by_the_list(window, qapp):
    control = window.plot_control
    mask = MaskDataSelection(0, 1, np.ones((3, 3), bool), np.linspace(0, 6, 4),
                             np.linspace(0, 1, 4), name="Bitmap 1")
    control.add_selection_object(mask)
    control.addGaussianSelection(0, 1, (3, 0.3), [[0.1, 0], [0, 0.01]], name="G2D 1")
    assert control.tableWidget.item(0, 1).text() == "Bitmap"
    assert [g.kind for g in control.gates] == ["Mask", "G2D"]
    assert control.get_selections()[0] is mask
    control.tableWidget.setCurrentCell(0, 0)
    control.onSelectionTableClicked()
    assert [g.kind for g in control.gates] == ["G2D"]
    assert control.tableWidget.rowCount() == 1
    control.onClearSelection()
    assert len(control.gates) == 0 and control.tableWidget.rowCount() == 0


def test_a_pick_adds_a_gaussian_gate_on_the_population(window, qapp, monkeypatch):
    """The Qt window's pick uses the shared fit and adds a G2D row."""
    monkeypatch.setattr(window, "request_plot_update", lambda *a, **k: None)
    control = window.plot_control
    names = list(window.data_source.parameter_names)
    control.comboBoxSelX.setCurrentText("Tau")
    control.comboBoxSelY.setCurrentText("r")
    control.spinBoxXmin.setValue(0.0)
    control.spinBoxXmax.setValue(6.0)
    control.spinBoxYmin.setValue(0.0)
    control.spinBoxYmax.setValue(0.6)
    monkeypatch.setattr(type(window), "values",
                        property(lambda self: np.stack([self.data_source.column_view(i)
                                                        for i in range(len(names))])))
    assert window.pick_population_at(3.0, 0.3) == ""
    (gate,) = control.gates
    assert gate.kind == "G2D" and gate.meta["mu"][0] == pytest.approx(3.0, abs=0.1)
    assert control.tableWidget.item(0, 1).text() == "G2D"
