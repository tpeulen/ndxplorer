"""The app's one parameter table, driven the way a user edits it.

Every parameter table (Gaussian Fit, Parameters, an overlay curve, the curve
fit) is the shared ``views/parameter_table.view.json`` over a
:class:`~ndxplorer.app.parameter_table.ParameterTable`. These tests press and
type into the real window -- a double-click on a cell, keys, then Enter or a
click somewhere else -- and check that the *parameter* changed and stays
changed over the next frames.

The user's report was a Gaussian's ρ typed as ``-0.1571`` that did not take:
a click outside the table never committed the cell, and the typographic minus
(U+2212, what a table shows) did not parse.
"""

from __future__ import annotations

import pathlib

import pytest

from ndxplorer.app.parameter_table import expand

KEY_RETURN, KEY_BACKSPACE = 0x01000004, 0x01000003
GAUSS = [{"op": "trigger", "action": "actionFit_Gaussians", "checked": True},
         {"op": "canvas_click", "at": [0.62, 0.74]},
         {"op": "canvas_click", "at": [0.75, 0.92]}]


def replay(steps, setup="mfd"):
    from ndxplorer.app import capture

    run = capture.Replay({"id": "test", "setup": setup, "steps": steps},
                         capture.load_catalogue())
    run.run()
    run.settle(3)
    return run


@pytest.fixture
def gaussians():
    run = replay(GAUSS)
    panel = next(f for f in run.app.features if f.name == "analysis").gaussians
    yield run, panel
    run.app.close()


def cell(control, key, column):
    """The centre of the cell of row *key*, column *column*, as last drawn."""
    order = control.order()
    index = next(i for i in range(control.row_count()) if control.key_of(i) == key)
    shown = [c.key for c in control._shown]
    k = shown.index(column)
    x = control._header_box[0] + sum(control._widths[:k]) + control._widths[k] / 2.0
    y = control._body_box[1] + (order.index(index) - control.bar.top + 0.5) * control._row_h
    return x, y


def type_into(run, control, key, column, text):
    """Double-click the cell, clear it and type *text* key by key."""
    x, y = cell(control, key, column)
    run.click_at(x, y)
    run.click_at(x, y, clicks=2)
    assert control.editing is not None, "the cell did not open for typing"
    for _ in range(30):
        run.app.key(KEY_BACKSPACE, "")
        run.draw()
    for char in text:
        run.app.key(0, char)
        run.draw()


def value_of(table, key, field="value"):
    return next(r for r in table.rows() if r["key"] == key)[field]


@pytest.mark.parametrize("typed", ["-0.1571", "−0.1571"])
def test_a_gaussian_value_typed_then_enter_is_the_parameter(gaussians, typed):
    run, panel = gaussians
    control = panel.form.tables["table.rows"].control
    type_into(run, control, "rho_1", "value", typed)
    run.app.key(KEY_RETURN, "")
    run.draw()
    assert control.editing is None
    assert panel.group.parameters_all_dict["rho_1"].value == pytest.approx(-0.1571)
    run.settle(5)                                   # not overwritten by the next frames
    assert value_of(panel.table, "rho_1") == pytest.approx(-0.1571)
    component = panel.components()[0]
    sx, sy = component.cov[0, 0] ** 0.5, component.cov[1, 1] ** 0.5
    assert component.cov[0, 1] / (sx * sy) == pytest.approx(-0.1571)


def test_a_gaussian_value_typed_then_a_click_elsewhere_is_the_parameter(gaussians):
    run, panel = gaussians
    control = panel.form.tables["table.rows"].control
    type_into(run, control, "w_1", "value", "0.25")
    x, y, w, h = control._body_box
    run.click_at(x + 20.0, y + h + 60.0)            # in the dock, under the table
    assert control.editing is None
    assert panel.group.parameters_all_dict["w_1"].value == pytest.approx(0.25)
    run.settle(5)
    assert value_of(panel.table, "w_1") == pytest.approx(0.25)


def test_a_click_on_the_menu_bar_commits_too(gaussians):
    run, panel = gaussians
    control = panel.form.tables["table.rows"].control
    type_into(run, control, "x_2", "value", "3.5")
    run.click_at(700.0, 10.0)                       # the menu bar takes this press
    assert control.editing is None
    assert panel.group.parameters_all_dict["x_2"].value == pytest.approx(3.5)


def test_lo_and_hi_are_typed_as_bounds_and_infinity_removes_one(gaussians):
    run, panel = gaussians
    table = panel.table
    control = panel.form.tables["table.rows"].control
    x_1 = panel.group.parameters_all_dict["x_1"]
    assert (value_of(table, "x_1", "lo"), value_of(table, "x_1", "hi")) == ("−∞", "∞")
    type_into(run, control, "x_1", "lo", "−1.5")
    run.app.key(KEY_RETURN, "")
    run.draw()
    assert x_1.bounds_on and x_1.lb == -1.5 and x_1.ub == float("inf")
    type_into(run, control, "x_1", "hi", "9")
    run.app.key(KEY_RETURN, "")
    run.draw()
    run.settle(3)
    assert (value_of(table, "x_1", "lo"), value_of(table, "x_1", "hi")) == ("-1.5", "9")
    type_into(run, control, "x_1", "lo", "∞")
    run.app.key(KEY_RETURN, "")
    run.draw()
    assert x_1.lb == float("-inf") and x_1.bounds_on          # Hi is still a bound
    type_into(run, control, "x_1", "hi", "inf")
    run.app.key(KEY_RETURN, "")
    run.draw()
    assert not x_1.bounds_on
    assert value_of(table, "x_1", "lo") == "−∞"


def test_the_gaussian_table_has_the_shared_columns(gaussians):
    run, panel = gaussians
    control = panel.form.tables["table.rows"].control
    assert [c.key for c in control._shown] == ["name", "value", "fixed", "lo", "hi"]
    fixed = cell(control, "sd_y_2", "fixed")
    run.click_at(*fixed)
    assert panel.group.parameters_all_dict["sd_y_2"].fixed
    panel.group.parameters_all_dict["x_2"].link = panel.group.parameters_all_dict["x_1"]
    run.settle(2)
    assert [c.key for c in control._shown][-1] == "link"
    assert not panel.table.cell_editable(
        next(r for r in panel.table.rows() if r["key"] == "x_2"), "value")


def test_the_right_click_menu_copies_pastes_and_links(gaussians):
    run, panel = gaussians
    table = panel.table
    record = next(r for r in table.rows() if r["key"] == "sd_x_1")
    labels = [label for label, _ in table.menu_entries(record, "value")]
    assert labels == ["Copy", "Paste", "Link…", "Make vector…"]
    dict(table.menu_entries(record, "value"))["Copy"]()
    other = next(r for r in table.rows() if r["key"] == "sd_x_2")
    dict(table.menu_entries(other, "value"))["Paste"]()
    group = panel.group.parameters_all_dict
    assert group["sd_x_2"].value == pytest.approx(group["sd_x_1"].value)
    dict(table.menu_entries(other, "value"))["Link…"]()
    feature = next(f for f in run.app.features if f.name == "overlays")
    dialog = feature.top or feature.window
    target = next(r for r in dialog.targets() if r["name"] == "sd_y_1")
    dialog.link(target)
    assert group["sd_x_2"].link is group["sd_y_1"]
    assert "Unlink" in [label for label, _ in table.menu_entries(other, "value")]


def test_a_curve_parameter_is_edited_in_the_same_table(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    run = replay([])
    try:
        feature = next(f for f in run.app.features if f.name == "overlays")
        feature.overlays.equation_choice = "FD/FA vs tau (static line)"
        curve = feature.overlays.add_curve()
        run.app.docks.focus("Overlays")
        run.settle(3)
        panel = feature.overlays.panels[0]
        control = panel.form.tables["table.rows"].control
        type_into(run, control, "kf", "value", "0.45")
        run.app.key(KEY_RETURN, "")
        run.draw()
        assert curve.get_parameters()["kf"] == pytest.approx(0.45)
        tau = curve.group.parameters_all_dict["tauD0"]
        upper = tau.ub                                  # the predefined curve's range
        type_into(run, control, "tauD0", "lo", "1")
        run.app.key(KEY_RETURN, "")
        run.settle(3)
        assert tau.bounds_on and tau.lb == 1.0 and tau.ub == upper
        assert value_of(panel.table, "kf") == pytest.approx(0.45)
    finally:
        run.app.close()


def test_every_parameter_table_is_the_shared_section():
    """The Gaussian, Parameters, curve and curve-fit specs name the one template."""
    root = pathlib.Path(__file__).resolve().parents[2] / "app" / "features"
    import json

    found = []
    for path in list((root / "analysis").glob("*.view.json")) + \
            list((root / "overlays").glob("*.view.json")):
        spec = json.loads(path.read_text())
        text = json.dumps(spec)
        if '"parameter_table"' in text:
            found.append(path.name)
        expanded = json.dumps(expand(spec))
        assert '"Bounds"' not in expanded, path.name
    assert sorted(found) == ["curve.view.json", "curve_fit.view.json",
                             "gaussian_fit.view.json", "parameters.view.json"]
