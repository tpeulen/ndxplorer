"""GUI smoke test: ndXplorer constants render as a fitting-parameter table."""
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


def _constants_json():
    import ndxplorer

    return str(pathlib.Path(ndxplorer.__file__).parent / "settings" / "mfd.constants.json")


def test_renders_fitting_table_with_flat_dict(qapp):
    from ndxplorer.ui.parameter_editor import ParameterEditor

    ed = ParameterEditor(json_file=_constants_json())
    try:
        # It built the fitting table (not the legacy dict fallback).
        assert ed._group is not None
        assert ed._table is not None
        d = ed.dict
        assert d.get("Bg") == 1.2 and d.get("forster_radius") == 52.0
        # Rich state exposes bounds/fixed for persistence.
        st = ed.get_state()
        assert "parameters" in st and "Bg" in st["parameters"]
        assert st["parameters"]["Bg"]["fixed"] is True
    finally:
        ed._unregister_group()


def test_edit_fires_callback(qapp):
    from qtpy import QtCore
    from ndxplorer.ui.parameter_editor import ParameterEditor

    fired = {"n": 0}
    ed = ParameterEditor(json_file=_constants_json(), callback=lambda: fired.__setitem__("n", fired["n"] + 1))
    try:
        model = ed._table._model
        # value column index
        from chisurf.gui.autoform.sections import parameter_table as pt
        col_ids = [c[0] for c in pt.COLUMN_META]
        vcol = col_ids.index("value")
        idx = model.index(0, vcol)
        assert model.setData(idx, 3.21, QtCore.Qt.EditRole)
        qapp.processEvents()
        assert fired["n"] >= 1
        # the edit reached the parameter / .dict snapshot
        assert list(ed.dict.values())[0] == pytest.approx(3.21)
    finally:
        ed._unregister_group()


def test_persistence_roundtrip_rich_state(qapp, tmp_path):
    import json
    from ndxplorer.ui.parameter_editor import ParameterEditor

    ed = ParameterEditor(json_file=_constants_json())
    try:
        p = ed._group.parameters_all_dict["tauD0"]
        p.bounds_on = True
        p.lb, p.ub = 1.0, 8.0
        p.fixed = False
        out = tmp_path / "mfd.constants.json"
        out.write_text(json.dumps(ed.get_state(), indent=4))
    finally:
        ed._unregister_group()

    ed2 = ParameterEditor(json_file=str(out))
    try:
        p2 = ed2._group.parameters_all_dict["tauD0"]
        assert p2.value == 4.0 and p2.fixed is False
        assert tuple(p2.bounds) == (1.0, 8.0) and p2.bounds_on is True
        # legacy flat consumers still get plain values from the rich file
        from ndxplorer.core.constants_group import values_from_data
        assert values_from_data(json.loads(out.read_text()))["tauD0"] == 4.0
    finally:
        ed2._unregister_group()


def test_group_registered_then_unregistered(qapp):
    from ndxplorer.ui.parameter_editor import ParameterEditor
    from chisurf.core import parameter_group_registry as reg

    ed = ParameterEditor(json_file=_constants_json())
    owners = {oid for oid, _label, _grp in reg.iter_registered_parameter_groups()}
    assert "ndxplorer" in owners
    ed._unregister_group()
    owners2 = {oid for oid, _label, _grp in reg.iter_registered_parameter_groups()}
    assert "ndxplorer" not in owners2


def test_live_crosslink_follows_and_signals_recompute(qapp):
    """self.constants follows a crosslink live; a fit event signals a recompute."""
    from ndxplorer.core.plot_main import NDXplorer
    from chisurf.core.fitting.parameter import FittingParameter

    ndx = NDXplorer()
    ndx._deferred_init()
    pc = ndx.parameter_control
    try:
        # self.constants is the live mapping over the group.
        assert ndx.constants["Bg"] == 1.2

        fired = {"n": 0}
        pc.constantsChangedExternally.connect(lambda: fired.__setitem__("n", fired["n"] + 1))

        master = FittingParameter(name="fit_bg", value=5.0)
        pc._group.parameters_all_dict["Bg"].link = master
        assert ndx.constants["Bg"] == 5.0  # linked value read live

        master.value = 2.5
        assert ndx.constants["Bg"] == 2.5

        # A fit-driven event (arriving on any thread) is marshalled to the GUI
        # thread and re-emitted as constantsChangedExternally -> recompute.
        pc._on_external_event()
        for _ in range(20):
            qapp.processEvents()
        assert fired["n"] >= 1
    finally:
        pc._unsubscribe_external()
        pc._unregister_group()


def test_add_parameter_appends_constant_and_fires_callback(qapp, monkeypatch):
    """The ➕ button adds a new constant without hand-editing JSON."""
    from qtpy import QtWidgets

    from ndxplorer.ui.parameter_editor import ParameterEditor

    ed = ParameterEditor(json_file=_constants_json())
    try:
        assert ed._group is not None
        fired = {"n": 0}
        ed.set_callback(lambda: fired.__setitem__("n", fired["n"] + 1))

        # Simulate the two input dialogs the button opens.
        monkeypatch.setattr(
            QtWidgets.QInputDialog, "getText",
            staticmethod(lambda *a, **k: ("my_new_const", True)),
        )
        monkeypatch.setattr(
            QtWidgets.QInputDialog, "getDouble",
            staticmethod(lambda *a, **k: (3.14, True)),
        )
        ed._add_parameter()

        assert "my_new_const" in ed._group.parameters_all_dict
        assert ed.dict["my_new_const"] == pytest.approx(3.14)
        assert fired["n"] >= 1  # host recomputes / picks up the new constant

        # A duplicate name is rejected (no second row, no crash).
        monkeypatch.setattr(
            QtWidgets.QInputDialog, "getText",
            staticmethod(lambda *a, **k: ("my_new_const", True)),
        )
        monkeypatch.setattr(
            QtWidgets.QMessageBox, "information",
            staticmethod(lambda *a, **k: None),
        )
        n_before = len(ed._group.parameters_all)
        ed._add_parameter()
        assert len(ed._group.parameters_all) == n_before
    finally:
        ed._unregister_group()


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-q"])
