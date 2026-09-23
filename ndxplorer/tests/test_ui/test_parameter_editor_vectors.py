"""The legacy Qt constants table with a vector constant present: shown, not broken."""
import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

pytest.importorskip("chisurf.gui.autoform.sections.parameter_table",
                    reason="chisurf fitting table not importable")


@pytest.fixture(scope="module")
def qapp():
    from qtpy import QtWidgets

    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def test_a_vector_is_summed_up_under_the_table_and_its_values_still_flow(qapp):
    from ndxplorer.ui.parameter_editor import ParameterEditor

    ed = ParameterEditor()
    try:
        rows = ed._table._model.rowCount()
        ed.apply_values({"gG/gR[HF]": 0.61, "gG/gR[LF]": 0.83})
        # The elements and the global leave the editable table ...
        names = [p.name for p in ed._table._params]
        assert "gG/gR" not in names and not any("[" in n for n in names)
        assert ed._table._model.rowCount() == rows - 1
        # ... are summed up, read-only, below it ...
        assert "gG/gR [2]: 0.61, 0.83" in ed._vectors.text()
        assert not ed._vectors.isHidden()
        # ... and reach the window's constants (the equations, the Global View).
        assert ed.dict["gG/gR[LF]"] == 0.83
    finally:
        ed.close()
