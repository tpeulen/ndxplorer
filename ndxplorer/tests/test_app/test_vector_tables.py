"""A vector parameter in every parameter table, driven the way a user edits it.

Every table of the app -- Gaussian Fit, Parameters, an overlay curve, the
curve fit -- is the shared :class:`~ndxplorer.app.parameter_table.ParameterTable`,
so any parameter of it can hold one value per population and shows as an
expandable row. Each test opens the vector with a click on its triangle, types
into an element's *Value* key by key, commits with Enter, and checks the
element parameter changed and stays changed over the next frames.

``NDX_VECTOR_SHOTS=<dir>`` saves each table's frame there, for looking at.
"""

from __future__ import annotations

import os
import pathlib

import pytest

from .test_overlays import pick
from .test_parameter_tables import GAUSS, KEY_BACKSPACE, KEY_RETURN, cell, replay, value_of

KEY_DOWN = 0x01000015


def _feature(run, name):
    return next(f for f in run.app.features if f.name == name)


def _shown(control):
    return [control.key_of(i) for i in control.order()]


def _open(run, control, key):
    """Click the triangle of parent row *key*, as the user opens a vector."""
    run.draw()
    if key + "[" in "".join(str(k) for k in _shown(control)):
        return
    _x, y = cell(control, key, "name")
    run.click_at(control._header_box[0] + 6.0, y)
    run.draw()


def _commit(run, control, key, text):
    """Select the row, double-click its value, clear it, type *text*, press Enter.

    A row a small table has scrolled away (a selected row's note is shown
    under the table) is reached with the Down key, as the user does.
    """
    shown = _shown(control)
    if control.selected_key in shown and shown.index(control.selected_key) < shown.index(key):
        while control.selected_key != key:
            run.app.key(KEY_DOWN, "")
            run.draw()
    else:
        run.click_at(*cell(control, key, "value"))
    assert control.selected_key == key
    run.click_at(*cell(control, key, "value"), clicks=2)
    assert control.editing is not None, "the cell did not open for typing"
    for _ in range(30):
        run.app.key(KEY_BACKSPACE, "")
        run.draw()
    for char in text:
        run.app.key(0, char)
        run.draw()
    run.app.key(KEY_RETURN, "")
    run.draw()
    assert control.editing is None


def _shot(run, name):
    folder = os.environ.get("NDX_VECTOR_SHOTS")
    if folder:
        pathlib.Path(folder).mkdir(parents=True, exist_ok=True)
        run.draw().save(pathlib.Path(folder) / f"{name}.png")


def test_a_gaussian_weight_made_a_vector_from_the_menu_is_edited_per_population():
    run = replay(GAUSS)
    try:
        panel = _feature(run, "analysis").gaussians
        overlays = _feature(run, "overlays")
        table = panel.table
        table.menu(next(r for r in table.rows() if r["key"] == "w_1"), "value", (200.0, 300.0))
        popup, _ = run.app.popup
        labels = [item.label for item in popup.entries]
        pick(run.app, popup, labels.index("Make vector…"))
        dialog = overlays.window
        dialog.populations = "HF, LF"
        dialog.ok()
        w_1 = panel.group.get("w_1")
        assert w_1.populations == ["HF", "LF"] and len(panel.components()) == 2
        control = panel.form.tables["table.rows"].control
        run.settle(2)
        assert _shown(control).index("w_1[LF]") == _shown(control).index("w_1[]") + 3
        _commit(run, control, "w_1[LF]", "0.35")
        assert w_1.element("LF").value == pytest.approx(0.35)
        run.settle(5)
        assert value_of(table, "w_1[LF]") == pytest.approx(0.35)
        assert value_of(table, "w_1[]") == "1, 0.35"
        # Fixed on the parent row holds every element.
        run.click_at(*cell(control, "w_1[]", "fixed"))
        assert all(e.fixed for e in w_1.elements)
        _shot(run, "gaussian")
    finally:
        run.app.close()


def test_a_curve_parameter_vector_opens_and_takes_a_typed_element(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    run = replay([])
    try:
        feature = _feature(run, "overlays")
        feature.overlays.equation_choice = "FD/FA vs tau (static line)"
        curve = feature.overlays.add_curve()
        curve.group.get("tauD0").set_vector([4.0, 3.2], ["HF", "LF"])
        run.app.docks.focus("Overlays")
        run.settle(3)
        panel = feature.overlays.panels[0]
        control = panel.form.tables["table.rows"].control
        assert "tauD0[HF]" not in _shown(control)             # closed until opened
        _open(run, control, "tauD0[]")
        assert "tauD0[HF]" in _shown(control)
        _commit(run, control, "tauD0[HF]", "3.9")
        assert curve.group.get("tauD0[HF]").value == pytest.approx(3.9)
        run.settle(5)
        assert value_of(panel.table, "tauD0[HF]") == pytest.approx(3.9)
        _shot(run, "curve")
    finally:
        run.app.close()


def test_a_vector_constant_in_the_curve_fit_opens_and_takes_a_typed_element(tmp_path,
                                                                             monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    run = replay([])
    try:
        feature = _feature(run, "overlays")
        feature.constants.set_vector("gG/gR", [0.6, 0.9], ["0", "1"], expand=False)
        feature.overlays.equation_choice = "FD/FA vs tau (static line)"
        curve = feature.overlays.add_curve()
        feature.open_fit(curve)
        dialog = feature.window
        run.settle(3)
        assert dialog.has_data_parameters, dialog.status_text()
        control = dialog.form.tables["data_table.rows"].control
        assert "gG/gR[]" in _shown(control)
        _open(run, control, "gG/gR[]")
        _commit(run, control, "gG/gR[1]", "0.85")
        assert feature.constants.group.get("gG/gR[1]").value == pytest.approx(0.85)
        run.settle(5)
        assert value_of(dialog.data_table, "gG/gR[1]") == pytest.approx(0.85)
        _shot(run, "curve_fit")
    finally:
        run.app.close()


def test_a_vector_constant_in_the_parameters_tab_takes_a_typed_element(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    run = replay([])
    try:
        feature = _feature(run, "overlays")
        feature.constants.set_vector("Bg", [1.5, 2.5], ["HF", "LF"])
        run.app.docks.focus("Parameters")
        run.settle(3)
        control = feature.constants.form.tables["table.rows"].control
        _commit(run, control, "Bg[HF]", "−1.25")
        assert feature.constants.values()["Bg[HF]"] == pytest.approx(-1.25)
        run.settle(5)
        assert value_of(feature.constants.table, "Bg[HF]") == pytest.approx(-1.25)
        _shot(run, "parameters")
    finally:
        run.app.close()
