"""The overlays feature of the emtk app: constants, curves, the curve fit,
equations and the Table Editor, driven headlessly on the MFD burst folder.

Each test drives the panels the way their specs do (the attributes and
methods a ``view.json`` binds to) and draws the window, so a panel that
raises while drawing fails here too.
"""

from __future__ import annotations

import pathlib
import subprocess
import sys

import numpy as np
import pytest

REPO = pathlib.Path(__file__).resolve().parents[3]
MFD = REPO / "test" / "mfd" / "burstwise_All 0.1500#30"
SIZE = (1400, 900)


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    from ndxplorer.app.frame import NdxApp

    a = NdxApp(features=["io", "overlays"])
    assert a.open_path(str(MFD)), a.model.error
    a.model.set_parameter("y", "Fd/Fa")
    draw(a)
    yield a
    a.close()


def feature(app):
    return next(f for f in app.features if f.name == "overlays")


def draw(app, size=SIZE):
    from emtk.pil_painter import PilPainter

    painter = PilPainter(*size)
    app.draw(painter, 0.0, 0.0, float(size[0]), float(size[1]))
    return painter.frame


def pick(app, popup, index):
    """Click row *index* of the context menu *popup*, as the user does."""
    draw(app)
    x, y, w, h = popup.row_rect(index)
    app.pointer_press(x + w / 2.0, y + h / 2.0, 1)
    draw(app)
    app.pointer_release(x + w / 2.0, y + h / 2.0, 1)
    draw(app)
    assert app.popup is None


def column(app, name):
    return np.asarray(app.model.source.column_values(name), dtype=float).copy()


def test_nothing_in_the_feature_imports_qt_or_chimol():
    """The browser build imports this; chimol was only ever Qt's (chisurf.gui) need."""
    code = (
        "import sys, importlib.abc\n"
        "class Block(importlib.abc.MetaPathFinder):\n"
        "    def find_spec(self, name, path, target=None):\n"
        "        if name.split('.')[0] in ('chimol', 'PyQt5', 'qtpy', 'PySide2', 'pyqtgraph'):\n"
        "            raise ImportError('blocked ' + name)\n"
        "sys.meta_path.insert(0, Block())\n"
        "import ndxplorer.app.features.overlays as o\n"
        "import ndxplorer.core.overlay_curves, ndxplorer.analysis.curve_fit_setup\n"
        "import ndxplorer.core.equation_table, ndxplorer.core.store_edits\n"
        "from ndxplorer.app.model import ExplorerModel\n"
        f"m = ExplorerModel(); assert m.open({str(MFD)!r}), m.error\n"
        "assert 'Proximity ratio' in m.parameter_names\n"
        "from ndxplorer.core.overlay_curves import OverlayCurve\n"
        "c = OverlayCurve('c', 'a*x+b'); assert list(c.get_parameters()) == ['a', 'b']\n"
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                            cwd=str(REPO))
    assert result.returncode == 0, result.stderr[-2000:]


# ---------------------------------------------------------------- constants
def test_the_constants_are_the_data_managers_and_an_edit_recomputes_the_columns(app):
    f = feature(app)
    assert app.model.manager.constants is f.constants.mapping
    rows = f.constants.table.rows()
    assert [r["name"] for r in rows][:3] == ["gG/gR", "Bg", "Br"]
    before = column(app, "Fd/Fa")
    gamma = next(r for r in rows if r["name"] == "gG/gR")
    f.constants.table.edit(gamma, "value", gamma["value"] * 2.0)
    draw(app)
    after = column(app, "Fd/Fa")
    good = np.isfinite(before) & np.isfinite(after)
    assert np.allclose(after[good] * 2.0, before[good])
    assert app.model.histograms is not None


def test_add_parameter_asks_for_a_name_then_a_value_and_refuses_a_duplicate(app):
    f = feature(app)
    f.constants.add_parameter()
    dialog = f.window
    draw(app)
    assert dialog.step == "name"
    dialog.name = "k_new"
    dialog.ok()
    assert dialog.step == "value"
    dialog.value = 2.5
    dialog.ok()
    draw(app)
    assert f.window is None and dict(f.constants.mapping)["k_new"] == 2.5
    f.constants.add_parameter()
    f.window.name = "Bg"
    f.window.ok()
    assert app.message == ("Add parameter", "A parameter named 'Bg' already exists.")


def test_save_writes_value_bounds_and_fixed(app, tmp_path):
    import json

    f = feature(app)
    f.constants.save_parameters()
    saved = json.loads((tmp_path / ".ndxplorer" / "mfd.constants.json").read_text())
    assert saved["parameters"]["gG/gR"]["fixed"] is True


# ----------------------------------------------------------------- overlays
def add_static_line(app):
    f = feature(app)
    f.overlays.equation_choice = "FD/FA vs tau (static line)"
    curve = f.overlays.add_curve()
    draw(app)
    return f, curve


def test_the_equation_list_is_custom_plus_the_predefined_curves(app):
    options = feature(app).overlays.equation_options()
    assert options[0] == "Custom Equation"
    assert "FD/FA vs tau (static line)" in options and "Circle" in options


def test_a_static_line_is_drawn_over_the_map_and_follows_its_parameters(app):
    f, curve = add_static_line(app)
    assert curve.title == "FD/FA vs tau (static line) 1"
    assert set(curve.get_parameters()) == {"PhiA", "kf", "tauD0"}
    hist = app.model.histograms
    x, y = curve.points(500, hist.x_edges, hist.y_edges, app.model.x.log, app.model.y.log)
    assert x.size > 100
    panel = f.overlays.panels[0]
    assert panel.filled.startswith("x*4.0000e+00*2.0000e-01")
    record = next(r for r in panel.table.rows() if r["name"] == "kf")
    panel.table.edit(record, "value", "0.4")
    assert curve.get_parameters()["kf"] == 0.4
    x2, y2 = curve.points(500, hist.x_edges, hist.y_edges)
    assert not np.allclose(y2[:10], y[:10])
    panel.visible = False
    draw(app)
    panel.delete()
    assert f.overlays.panels == []


def test_save_csv_writes_the_visible_curves(app, tmp_path):
    f, curve = add_static_line(app)
    out = tmp_path / "curves.csv"
    f._file_answers.append(str(out))
    f.overlays.save_csv()
    lines = out.read_text().splitlines()
    assert lines[0].startswith(curve.title) and lines[1] == "x,y" and len(lines) > 100


def test_a_curve_parameter_linked_to_a_constant_follows_it(app):
    f, curve = add_static_line(app)
    tau = curve.group.parameters_all_dict["tauD0"]
    panel = f.overlays.panels[0]
    f.open_link(tau, panel.table)
    dialog = f.top or f.window
    target = next(r for r in dialog.targets() if r["owner"] == "ndX" and r["name"] == "tauD0")
    dialog.link(target)
    f.constants.group.parameters_all_dict["tauD0"].value = 3.3
    assert curve.get_parameters()["tauD0"] == pytest.approx(3.3)
    assert next(r for r in panel.table.rows() if r["name"] == "tauD0")["link"] == "tauD0"
    assert "link" in [c["key"] for c in panel.table.columns()]


# ---------------------------------------------------------------- curve fit
def test_fit_moves_the_curve_onto_the_data(app):
    f, curve = add_static_line(app)
    f.open_fit(curve)
    dialog = f.window
    draw(app)
    assert dialog.cf is not None, dialog.status_text()
    assert [p.name for p in dialog.cf.parameters] == ["PhiA", "kf", "tauD0"]
    assert dialog.has_data_parameters            # the equations read the constants
    before = dict(curve.get_parameters())
    dialog.run_fit()
    dialog.wait()
    draw(app)
    assert dialog.status_text().startswith("reduced χ²"), dialog.status_text()
    assert curve.get_parameters() != before


def test_every_target_and_reduction_builds_a_fit(app):
    f, curve = add_static_line(app)
    f.open_fit(curve)
    dialog = f.window
    for target in ("x", "y", "2d"):
        dialog.target = target
        assert dialog.cf is not None, (target, dialog.status_text())
    for reduction in ("population", "mean", "cloud"):
        dialog.reduction = reduction
        assert dialog.cf is not None, (reduction, dialog.status_text())


# ---------------------------------------------------------------- equations
def test_view_equations_reaches_the_equations_tab(app):
    f = feature(app)
    assert not app.docks.is_visible("Equations")
    assert app.run_action("toggle_equations")
    assert app.docks.is_shown("Equations") and app.panel.show_equations
    draw(app)
    assert f.equations.status_text() == "59 equation(s), all valid"


def test_a_bad_equation_is_marked_and_apply_recomputes(app):
    f = feature(app)
    panel = f.equations
    row = next(r for r in panel.rows() if r["output"] == "Proximity ratio")
    panel.edit_row(row, "expression", "'Sr' / 'nope'")
    assert row["status"] == "✗" and "nope" in row["message"]
    panel.edit_row(row, "expression", "2 * 'Sr' / ('Sg' + 'Sr')")
    panel.apply_equations()
    pr, sg, sr = column(app, "Proximity ratio"), column(app, "Sg"), column(app, "Sr")
    good = np.isfinite(pr) & (sg + sr != 0)
    assert np.allclose(pr[good], 2 * sr[good] / (sg[good] + sr[good]))


def test_names_insert_a_quoted_name_and_list_only_the_engines_functions(app):
    f = feature(app)
    panel = f.equations
    panel.add_equation()
    panel.show_names()
    dialog = f.window
    labels = [r["label"] for r in dialog.rows()]
    assert labels[0] == "— Constants —" and "— Columns —" in labels
    assert labels[labels.index("— Functions —") + 1:] == ["abs()"]
    dialog.insert(next(r for r in dialog.rows() if r["label"] == "Bg"))
    assert panel.table.rows[panel.selected]["expression"] == "'Bg'"


# ------------------------------------------------------------- table editor
def test_the_table_editor_stages_edits_and_apply_writes_them(app):
    f = feature(app)
    app.run_action("show_data")
    editor = f.window
    draw(app)
    assert editor.status_text() == "12,237 rows × 58 columns"
    first = app.model.source.column_values("Number of Photons")[0]
    editor.edit_cell(0, "Number of Photons", first + 1000)
    assert app.model.source.column_values("Number of Photons")[0] == first   # staged
    editor.reset()
    assert editor.arrays()["Number of Photons"][0] == first
    editor.edit_cell(0, "Number of Photons", first + 1000)
    editor.apply()
    assert app.model.source.column_values("Number of Photons")[0] == first + 1000
    draw(app)
    assert f.window is None


def test_the_table_editor_hides_colours_filters_and_exports(app, tmp_path):
    f = feature(app)
    app.run_action("show_data")
    editor = f.window
    draw(app)
    editor.hidden.add("First File")
    assert not next(c for c in editor.columns() if c["key"] == "First File")["visible"]
    editor.colour_cells = True
    assert editor.colour_mode() == "column"
    editor.colour_table = True
    assert editor.colour_mode() == "table"
    editor.filter_column("Number of Photons")
    prompt = f.top
    prompt.text = "252"
    prompt.ok()
    draw(app)
    control = editor._control()
    assert 0 < len(control.order()) < 12237
    out = tmp_path / "table.csv"
    f._file_answers.append(str(out))
    editor.export_csv()
    lines = out.read_text().splitlines()
    assert "First File" not in lines[0] and len(lines) == len(control.order()) + 1
    control.select_all()
    editor.copy(headers=True)
    assert f.clipboard.splitlines()[0].startswith("First Photon")
    editor.cancel()
    draw(app)
    assert f.window is None


def test_a_right_click_menu_copies_and_pastes_a_value(app):
    f = feature(app)
    rows = f.constants.table.rows()
    bg = next(r for r in rows if r["name"] == "Bg")
    f.constants.table.menu(bg, "value", (100.0, 200.0))
    popup, _on_choose = app.popup
    assert [i.label for i in popup.entries][:3] == ["Copy", "Paste", "Link…"]
    pick(app, popup, 0)                          # Copy
    assert float(f.clipboard) == bg["value"]
    f.clipboard = "7.5"
    phia = next(r for r in rows if r["name"] == "PhiA")
    f.constants.table.menu(phia, "value", (100.0, 200.0))
    pick(app, app.popup[0], 1)                   # Paste
    assert dict(f.constants.mapping)["PhiA"] == 7.5
