"""The selection feature of the emtk app, headless: menus, picking, mask painting.

The window is drawn into a pixel painter and driven with the pointer, the way
the parity capture replays a scenario: a right-click opens a context menu, a
click on a row runs it, and a drag with drawing enabled paints. Nothing here
needs Qt.
"""

from __future__ import annotations

import numpy as np
import pytest

from ndxplorer.core.data_source import DataSource, MaskDataSelection
from ndxplorer.core.mask_paint import MaskCanvas
from ndxplorer.core.population_pick import fit_population, truncation_factor

SIZE = (1400, 900)


# -- the Qt-free parts -------------------------------------------------------------


def test_the_selection_code_imports_without_qt():
    """What the browser build imports: no Qt binding, no pyqtgraph, no chisurf."""
    import subprocess
    import sys

    code = (
        "import sys\n"
        "import ndxplorer.app.features.selection, ndxplorer.core.population_pick\n"
        "import ndxplorer.core.mask_paint, ndxplorer.utils.histogram_export\n"
        "import ndxplorer.analysis.burst_bridge, emtk.clipboard\n"
        "bad = [m for m in sys.modules if m.split('.')[0] in "
        "('qtpy', 'PyQt5', 'PyQt6', 'PySide2', 'PySide6', 'pyqtgraph', 'chisurf')]\n"
        "print(','.join(bad))\n"
    )
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                         check=True)
    assert out.stdout.strip() == ""


def two_populations(n=4000, seed=0):
    """A diffuse population at (3.2, 0.35) beside a dense one at (4.0, 0.05)."""
    rng = np.random.default_rng(seed)
    a = rng.multivariate_normal([3.2, 0.35], [[0.09, 0.004], [0.004, 0.0025]], n)
    b = rng.multivariate_normal([4.0, 0.05], [[0.16, 0.0], [0.0, 0.0004]], 3 * n)
    return np.vstack([a, b])


def test_a_pick_finds_the_population_it_is_on_not_the_denser_neighbour():
    points = two_populations()
    fit = fit_population(points[:, 0], points[:, 1], (3.5, 0.28), (0, 6), (-0.05, 1.05))
    assert fit.success, fit.reason
    assert fit.mu == pytest.approx([3.2, 0.35], abs=0.05)
    # Its own width: not the sliver a raw-unit radius cuts, not both clouds.
    assert fit.cov[0, 0] == pytest.approx(0.09, rel=0.3)
    assert fit.cov[1, 1] == pytest.approx(0.0025, rel=0.3)


def test_a_pick_on_a_log_axis_fits_in_the_log():
    rng = np.random.default_rng(1)
    x = np.exp(rng.normal(np.log(30.0), 0.2, 5000))
    y = rng.normal(0.5, 0.05, 5000)
    fit = fit_population(x, y, (32.0, 0.5), (1.0, 1000.0), (0.0, 1.0), log_x=True)
    assert fit.success and fit.log_x and not fit.log_y
    assert fit.mu[0] == pytest.approx(np.log(30.0), abs=0.05)
    assert fit.cov[0, 0] == pytest.approx(0.04, rel=0.3)


def test_a_pick_outside_the_plot_or_on_nothing_is_refused_with_a_reason():
    points = two_populations()
    fit = fit_population(points[:, 0], points[:, 1], (7.0, 0.3), (0, 6), (0, 1))
    assert not fit.success and "outside" in fit.reason
    fit = fit_population(np.array([1.0]), np.array([0.5]), (1.0, 0.5), (0, 6), (0, 1))
    assert not fit.success and fit.reason


def test_the_truncation_factor_of_a_gaussian():
    rng = np.random.default_rng(2)
    z = rng.normal(size=(200000, 2))
    kept = z[(z ** 2).sum(axis=1) <= 1.5 ** 2]
    assert kept.var(axis=0).mean() == pytest.approx(truncation_factor(1.5), rel=0.02)


def test_painted_bins_become_a_mask_gate_on_exactly_those_bins():
    canvas = MaskCanvas()
    assert canvas.fit(np.linspace(0, 10, 11), np.linspace(0, 1, 11), ("a", "b"))
    assert not canvas.fit(np.linspace(0, 10, 11), np.linspace(0, 1, 11), ("a", "b"))
    # A one-bin brush (1 px on 20 px bins) along a stroke from (0.5, 0.05) to (4.5, 0.05).
    canvas.stroke((0.5, 0.05), (4.5, 0.05), 1, (20.0, 20.0), category=2)
    assert canvas.categories() == [2]
    assert canvas.mask[0, :5].tolist() == [2] * 5 and canvas.mask.sum() == 10
    selection, reason = canvas.selection(0, 1, 2, "painted")
    assert isinstance(selection, MaskDataSelection) and reason == ""
    inside = selection.inside(np.array([2.5, 2.5, 7.5]), np.array([0.05, 0.55, 0.05]))
    assert inside.tolist() == [True, False, False]
    canvas.dab(2.5, 0.05, 1, (20.0, 20.0), category=2, erase=True)
    assert canvas.mask[0, 2] == 0
    assert canvas.selection(0, 1, 7)[0] is None
    # A different binning starts afresh.
    assert canvas.fit(np.linspace(0, 10, 21), np.linspace(0, 1, 11), ("a", "b"))
    assert canvas.categories() == []


def test_a_mask_saves_and_loads_back(tmp_path):
    canvas = MaskCanvas()
    canvas.fit(np.linspace(0, 1, 6), np.linspace(0, 1, 4), ())
    canvas.dab(0.1, 0.1, 1, (20.0, 20.0), 3)
    path = str(tmp_path / "mask.tif")
    canvas.save(path)
    saved = canvas.mask.copy()
    canvas.clear()
    assert canvas.load(path) == ""
    assert np.array_equal(canvas.mask, saved)


# -- the window ----------------------------------------------------------------------


@pytest.fixture
def app():
    from ndxplorer.app.frame import NdxApp

    rng = np.random.default_rng(5)
    points = two_populations(1500, 5)
    a = NdxApp(features=["selection"])
    a.model.set_source(DataSource.from_columns({
        "Tau": points[:, 0], "PR": points[:, 1], "N": rng.lognormal(4, 0.5, len(points)),
    }))
    a.model.set_parameter("x", "Tau")
    a.model.set_parameter("y", "PR")
    a.model.x.lo, a.model.x.hi = 0.0, 6.0
    a.model.y.lo, a.model.y.hi = -0.05, 1.05
    a.model.invalidate()
    draw(a)
    draw(a)
    yield a
    a.close()


def draw(app):
    from emtk.pil_painter import PilPainter

    painter = PilPainter(*SIZE)
    app.draw(painter, 0.0, 0.0, float(SIZE[0]), float(SIZE[1]))
    return painter.frame


def press(app, x, y, button=1):
    app.pointer_move(x, y)
    draw(app)
    app.pointer_press(x, y, button)
    draw(app)
    app.pointer_release(x, y, button)
    draw(app)


def feature(app):
    return next(f for f in app.features if f.name == "selection")


def map_point(app, x, y):
    """Screen position of data point (x, y) on the map."""
    px, py, pw, ph = app.plots.rects["map"]
    (x0, x1), (y0, y1) = (app.model.x.lo, app.model.x.hi), (app.model.y.lo, app.model.y.hi)
    return px + (x - x0) / (x1 - x0) * pw, py + (1.0 - (y - y0) / (y1 - y0)) * ph


def menu_labels(app):
    popup = app.popup[0]
    return [getattr(e, "label", None) for e in popup.entries]


def choose(app, label):
    popup = app.popup[0]
    rect = next(r for e, r in popup._rows if e is not None and e.label.startswith(label))
    press(app, rect[0] + 10, rect[1] + rect[3] / 2)
    draw(app)


def test_the_map_menu_has_every_row_and_fits_a_gate_where_clicked(app):
    press(app, *map_point(app, 3.3, 0.33), button=2)
    labels = menu_labels(app)
    assert labels[:3] == ["Copy 2D Histogram (CSV)", "Copy 1D Histograms (CSV)",
                          labels[2]] and labels[2].startswith("Send to Napari")
    assert "Fit gate to the population here" in labels
    send = app.popup[0].entries[-1]
    # No ChiSurf connection here: the submenu is there, disabled, and says why.
    assert send.label.startswith("Send selection to — No ChiSurf connection")
    assert not send.enabled
    choose(app, "Fit gate to the population here")
    gates = app.model.gates
    assert [g.kind for g in gates] == ["G2D"]
    assert gates[0].meta["mu"][0] == pytest.approx(3.2, abs=0.1)
    assert app.model.count_current < app.model.count_total
    assert app.status.startswith("Gate fitted")


def test_copying_the_histograms_reaches_the_clipboard(app, monkeypatch):
    from emtk import clipboard

    copied = []
    monkeypatch.setattr(clipboard, "copy", lambda text: copied.append(text) or True)
    press(app, *map_point(app, 3.0, 0.5), button=2)
    choose(app, "Copy 2D Histogram (CSV)")
    press(app, *map_point(app, 3.0, 0.5), button=2)
    choose(app, "Copy 1D Histograms (CSV)")
    assert copied[0].startswith("y/x\t") and copied[1].startswith("Histogram\tBinCenter")
    ny, nx = app.model.histograms.H.shape
    assert len(copied[0].splitlines()) == ny + 1


def test_the_table_menu_selects_all_and_deletes_them(app):
    model = app.model
    model.add_rectangle((2.5, 4.0), (0.2, 0.5))
    model.add_interval("N", 10, 100)
    draw(app)
    draw(app)
    rect = feature(app).table_rect
    press(app, rect[0] + 40, rect[1] + 30, button=2)
    assert menu_labels(app)[:3] == ["Select All", "Clear", "Delete"]
    choose(app, "Select All")
    press(app, rect[0] + 40, rect[1] + 30, button=2)
    choose(app, "Delete")
    assert len(model.gates) == 0


def test_painting_and_apply_make_a_mask_gate(app):
    f = feature(app)
    f.mask_model.drawing = True
    f.mask_model.brush = 12
    start, end = map_point(app, 2.8, 0.3), map_point(app, 3.6, 0.4)
    app.pointer_move(*start)
    draw(app)
    app.pointer_press(*start, 1)
    draw(app)
    for t in (0.25, 0.5, 0.75, 1.0):
        app.pointer_move(start[0] + t * (end[0] - start[0]), start[1] + t * (end[1] - start[1]), 1)
        draw(app)
    app.pointer_release(*end, 1)
    draw(app)
    assert len(app.model.gates) == 0          # painting is not a rectangle gate
    assert f.canvas.categories() == [1]
    f.mask_model.apply_mask()
    draw(app)
    (gate,) = app.model.gates
    assert gate.kind == "Mask" and gate.record()["lower"] == "Bitmap"
    assert 0 < app.model.count_current < app.model.count_total


def test_in_the_browser_the_rpc_and_napari_say_why_not(app, monkeypatch):
    from ndxplorer.app.features import selection

    monkeypatch.setattr(selection.sys, "platform", "emscripten")
    f = feature(app)
    reason, targets = f.send_state()
    assert "browser" in reason and targets == []
    assert f.napari_reason() == "not in the browser"
