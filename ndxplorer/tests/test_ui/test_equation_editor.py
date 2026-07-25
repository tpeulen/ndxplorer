"""GUI tests for the validated equation-table editor.

Equations used to be edited as raw YAML; the EquationEditor renders them as a
table with a live validity indicator and serialises back to the same YAML the
existing save path expects. These tests exercise that round-trip and the
validation feedback without hand-editing text.
"""
from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="session")
def qapp():
    from qtpy import QtWidgets

    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _names():
    return (["Sg", "Sr"], ["Bg", "Br"])


def test_set_and_get_equations_round_trip(qapp):
    from ndxplorer.widgets.equation_editor import EquationEditor

    ed = EquationEditor(names_provider=_names)
    ed.set_equations([{"Fg": "'Sg' - 'Bg'"}, {"Fr": "'Sr' - 'Br'"}])
    assert ed.equations() == [{"Fg": "'Sg' - 'Bg'"}, {"Fr": "'Sr' - 'Br'"}]


def test_text_serialises_to_yaml_list(qapp):
    import yaml

    from ndxplorer.widgets.equation_editor import EquationEditor

    ed = EquationEditor(names_provider=_names)
    ed.set_equations([{"Fg": "'Sg' - 'Bg'"}])
    parsed = yaml.safe_load(ed.text())
    assert parsed == [{"Fg": "'Sg' - 'Bg'"}]


def test_settext_parses_yaml(qapp):
    from ndxplorer.widgets.equation_editor import EquationEditor

    ed = EquationEditor(names_provider=_names)
    ed.setText("- Fg: \"'Sg' - 'Bg'\"\n")
    assert ed.equations() == [{"Fg": "'Sg' - 'Bg'"}]


def test_invalid_row_is_flagged(qapp):
    from ndxplorer.widgets.equation_editor import EquationEditor

    ed = EquationEditor(names_provider=_names)
    # 'nope' is neither a column nor a constant -> must show as invalid.
    ed.set_equations([{"Bad": "'nope' + 1"}])
    status = ed._table.item(0, 2)
    assert status.text() == "✗"          # ✗
    assert "nope" in status.toolTip()


def test_valid_row_is_marked_ok(qapp):
    from ndxplorer.widgets.equation_editor import EquationEditor

    ed = EquationEditor(names_provider=_names)
    ed.set_equations([{"Fg": "'Sg' - 'Bg'"}])
    assert ed._table.item(0, 2).text() == "✓"   # ✓


def test_apply_calls_callback_and_emits(qapp):
    from ndxplorer.widgets.equation_editor import EquationEditor

    ed = EquationEditor(names_provider=_names)
    ed.set_equations([{"Fg": "'Sg' - 'Bg'"}])
    fired = {"cb": 0, "sig": 0}
    ed.save_callback = lambda: fired.__setitem__("cb", fired["cb"] + 1)
    ed.applied.connect(lambda: fired.__setitem__("sig", fired["sig"] + 1))
    ed.apply()
    assert fired == {"cb": 1, "sig": 1}


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-q"])
