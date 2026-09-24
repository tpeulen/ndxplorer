"""Vector parameters in the emtk app's Parameters tab: one value per population.

Driven headlessly on the MFD burst folder, the way ``parameters.view.json``
binds the panel (rows, edits, the right-click menu, the dialogs), and drawn.
"""

from __future__ import annotations

import json

import numpy as np
import pytest

from ndxplorer.app.features import overlays as _overlays

from .test_overlays import MFD, column, draw, feature, pick

@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    from ndxplorer.app.frame import NdxApp

    a = NdxApp(features=["io", "overlays"])
    assert a.open_path(str(MFD)), a.model.error
    a.model.set_parameter("y", "Fd/Fa")
    a.docks.focus("Parameters")
    draw(a)
    yield a
    a.close()


def _labels(app):
    """Two populations by burst index parity, and a few bursts in none."""
    n = app.model.source.size
    labels = (np.arange(n) % 2).astype(float)
    labels[::7] = np.nan
    app.model.source.set_column("Cluster Label", labels)
    return labels


def _row(panel, key):
    return next(r for r in panel.table.rows() if r["key"] == key)


def test_set_vector_recomputes_each_burst_with_its_populations_value(app):
    panel = feature(app).constants
    labels = _labels(app)
    before = column(app, "Fd/Fa")
    g = panel.values()["gG/gR"]
    panel.set_vector("gG/gR", [g * 2.0, g * 4.0], ["0", "1"], uncertainties=[0.01, 0.02])
    draw(app)
    after = column(app, "Fd/Fa")
    # Fd/Fa goes as 1/(gG/gR): each burst scales by its population's factor.
    scale = np.where(labels == 0, 2.0, np.where(labels == 1, 4.0, 1.0))
    good = np.isfinite(before) & np.isfinite(after)
    assert np.allclose(after[good] * scale[good], before[good])


def test_a_vector_is_an_expandable_row(app):
    panel = feature(app).constants
    panel.set_vector("gG/gR", [0.61, 0.83], ["HF", "LF"], uncertainties=[0.01, 0.02],
                     expand=False)
    parent = _row(panel, "gG/gR[]")
    assert parent["name"] == "gG/gR [2]" and parent["value"] == "0.61, 0.83"
    children = [r for r in panel.table.rows() if r["parent"] == "gG/gR[]"]
    assert [r["name"] for r in children] == ["(global)", "HF", "LF"]
    assert "± 0.02" in children[2]["note"]
    assert not panel.table.cell_editable(parent, "value") and panel.table.cell_editable(parent, "fixed")
    panel.table.edit(parent, "fixed", False)
    assert not panel.group.parameters_all_dict["gG/gR[LF]"].fixed
    panel.table.edit(children[1], "value", 0.7)
    assert panel.values()["gG/gR[HF]"] == 0.7
    panel.table.expanded.add("gG/gR[]")
    draw(app)
    binding = panel.form.tables["table.rows"]
    shown = [binding.control.value(i, "key") for i in binding.control.order()]
    assert shown.index("gG/gR[LF]") == shown.index("gG/gR[]") + 3


def test_make_vector_from_the_menu_and_back(app):
    f = feature(app)
    panel = f.constants
    f.constants.table.menu(_row(panel, "Bg"), "value", (100.0, 200.0))
    popup, _ = app.popup
    labels = [i.label for i in popup.entries]
    assert labels[-1] == "Make vector…"
    pick(app, popup, len(labels) - 1)
    dialog = f.window
    assert isinstance(dialog, _overlays.VectorDialog)
    dialog.populations = "3"
    dialog.ok()
    assert [r["name"] for r in panel.table.rows() if r["parent"] == "Bg[]"] == \
        ["(global)", "0", "1", "2"]
    f.clipboard = "1\t2\t3"
    panel.table.menu(_row(panel, "Bg[]"), "value", (100.0, 200.0))
    popup, _ = app.popup
    assert [i.label for i in popup.entries] == ["Copy values", "Paste values",
                                                "Populations…", "Make scalar"]
    pick(app, popup, 1)
    assert [panel.values()[f"Bg[{i}]"] for i in range(3)] == [1.0, 2.0, 3.0]
    panel.table.menu(_row(panel, "Bg[]"), "value", (100.0, 200.0))
    pick(app, app.popup[0], 3)
    assert "Bg[]" not in [r["key"] for r in panel.table.rows()]
    assert _row(panel, "Bg")["value"] == 1.2


def test_add_parameter_can_add_a_vector(app):
    f = feature(app)
    f.constants.add_parameter()
    dialog = f.window
    dialog.name = "kq"
    dialog.ok()
    assert dialog.vector_hidden
    dialog.kind = "Vector"
    assert not dialog.vector_hidden
    dialog.populations = "HF, LF"
    dialog.value = 0.5
    draw(app)
    dialog.ok()
    assert {k: v for k, v in f.constants.values().items() if k.startswith("kq")} == \
        {"kq": 0.5, "kq[HF]": 0.5, "kq[LF]": 0.5}


def test_lo_and_hi_show_infinity_until_a_bound_is_typed(app):
    panel = feature(app).constants
    bg = _row(panel, "Bg")
    assert (bg["lo"], bg["hi"]) == ("−∞", "∞")
    panel.table.edit(bg, "lo", "0.5")
    bg = _row(panel, "Bg")
    assert (bg["lo"], bg["hi"]) == ("0.5", "∞")
    panel.table.edit(bg, "lo", "")
    assert not panel.group.parameters_all_dict["Bg"].bounds_on
    assert _row(panel, "Bg")["lo"] == "−∞"


def test_save_keeps_the_vector_and_its_axis(app, tmp_path):
    panel = feature(app).constants
    panel.set_vector("gG/gR", [0.61, 0.83], ["HF", "LF"], column="Population",
                     probabilities={"HF": "P(HF)", "LF": "P(LF)"})
    panel.save_parameters()
    saved = json.loads((tmp_path / ".ndxplorer" / "mfd.constants.json").read_text())
    assert saved["parameters"]["gG/gR[LF]"]["value"] == 0.83
    assert saved["vectors"]["gG/gR"]["populations"] == ["HF", "LF"]
    assert saved["vectors"]["gG/gR"]["probabilities"]["LF"] == "P(LF)"


def test_relabelling_the_bursts_recomputes_what_reads_a_vector(app):
    panel = feature(app).constants
    labels = _labels(app)
    g = panel.values()["gG/gR"]
    panel.set_vector("gG/gR", [g, g * 2.0], ["0", "1"])
    draw(app)
    before = column(app, "Fd/Fa")
    app.model.source.set_column("Cluster Label", 1.0 - np.nan_to_num(labels, nan=5.0))
    panel._axis_checked = 0.0
    assert panel.poll()
    after = column(app, "Fd/Fa")
    was0 = labels == 0
    good = was0 & np.isfinite(before) & np.isfinite(after)
    assert np.allclose(after[good] * 2.0, before[good])
