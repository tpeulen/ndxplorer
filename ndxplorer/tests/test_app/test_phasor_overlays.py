"""Phasor analysis is overlays and equations: a map of the g, s columns.

The universal circle, the lifetime points and the FRET trajectory are entries
of the overlay list; the apparent lifetimes are equations. They share the
constants ``f_rep`` and ``harmonic``, and need no ChiSurf.
"""

from __future__ import annotations

import subprocess
import sys

import numpy as np
import pytest

F_MHZ = 80.0
OMEGA = 2 * np.pi * F_MHZ * 1e-3
TAUS = np.random.default_rng(1).uniform(0.5, 8.0, 500)


def mono(tau, omega=OMEGA):
    wt = omega * np.asarray(tau, dtype=float)
    return 1 / (1 + wt ** 2), wt / (1 + wt ** 2)


@pytest.fixture
def app(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("NDXPLORER_SETTINGS_DIR", str(tmp_path))
    from ndxplorer.app.frame import NdxApp
    from ndxplorer.core.data_source import DataSource

    a = NdxApp(features=["overlays"])
    g, s = mono(TAUS)
    a.model.set_source(DataSource.from_columns({"g": g, "s": s, "g (green)": g,
                                                "s (green)": s}))
    a.model.set_parameter("x", "g")
    a.model.set_parameter("y", "s")
    _frame(a)
    yield a
    a.close()


def _frame(app):
    from emtk.testing import RecordingPainter

    app.draw(RecordingPainter(), 0.0, 0.0, 1400.0, 900.0)


def overlays(app):
    return next(f for f in app.features if f.name == "overlays")


def add(app, name):
    panel = overlays(app).overlays
    assert name in panel.equation_options()
    panel.equation_choice = name
    curve = panel.add_curve()
    _frame(app)
    return curve


def test_there_is_no_phasor_feature_or_menu_entry(app):
    from ndxplorer.app.features import FEATURES

    assert "phasor" not in FEATURES
    assert not app.panel.available("show_phasor_panel")


def test_the_three_phasor_overlays_draw_where_numpy_says(app):
    circle = add(app, "Universal circle")
    points = add(app, "Lifetime points")
    fret = add(app, "FRET trajectory")
    hist = app.model.histograms
    # f and harmonic follow the constants of the Parameters tab
    constants = overlays(app).constants.group.parameters_all_dict
    for curve in (circle, points, fret):
        assert curve.group.get("f").link is constants["f_rep"]
        assert curve.group.get("harmonic").link is constants["harmonic"]
    assert fret.group.get("tau0").link is constants["tauD0"]

    # single-exponential data lie on the circle, which is the (0.5, 0) r=0.5 one
    x, y = circle.points(400, [0.0, 1.0], [0.0, 0.6])
    np.testing.assert_allclose((x - 0.5) ** 2 + y ** 2, 0.25, atol=1e-12)
    g, s = mono(TAUS)
    np.testing.assert_allclose((g - 0.5) ** 2 + s ** 2, 0.25, atol=1e-12)

    # the lifetime points are at the numpy phasors of their lifetimes, labelled
    ((_, _, px, py, labels),) = points.drawn_points(hist.x_edges, hist.y_edges)
    shown = [float(label.split()[0]) for label in labels]
    np.testing.assert_allclose(np.c_[px, py], np.c_[mono(shown)], atol=1e-12)
    assert labels and all(label.endswith(" ns") for label in labels)

    # the FRET trajectory runs from the donor-only point (tauD0) to (1, 0)
    fx, fy = fret.points(200, [0.0, 1.0], [0.0, 0.6])
    tau0 = float(constants["tauD0"].value)
    np.testing.assert_allclose([fx[0], fy[0]], mono(tau0), atol=1e-12)
    assert abs(fx[-1] - 1.0) < 1e-9 and abs(fy[-1]) < 1e-9
    e = np.linspace(0.0, 1.0, 200)
    np.testing.assert_allclose(np.c_[fx, fy], np.c_[mono(tau0 * (1 - e))], atol=1e-12)


def test_donor_only_fraction_and_background_move_the_trajectory_inside(app):
    fret = add(app, "FRET trajectory")
    fret.set_parameters({"x_DOnly": 0.3, "bg": 0.1})
    fx, fy = fret.points(50, [0.0, 1.0], [0.0, 0.6])
    tau0 = float(fret.get_parameters()["tau0"])
    e = np.linspace(0.0, 1.0, 50)
    gD, sD = mono(tau0)
    gA, sA = mono(tau0 * (1 - e))
    fD = 0.3 * tau0 / (0.3 * tau0 + 0.7 * tau0 * (1 - e))  # intensity fraction
    np.testing.assert_allclose(fx, 0.9 * (fD * gD + (1 - fD) * gA), atol=1e-12)
    np.testing.assert_allclose(fy, 0.9 * (fD * sD + (1 - fD) * sA), atol=1e-12)
    assert np.all((fx - 0.5) ** 2 + fy ** 2 <= 0.25 + 1e-12)


def test_tau_phi_and_tau_m_are_equations_that_match_numpy(app):
    source = app.model.source
    for suffix in ("", " (green)"):
        tau_phi = np.asarray(source.column_values(f"tau_phi{suffix}"), dtype=float)
        tau_m = np.asarray(source.column_values(f"tau_m{suffix}"), dtype=float)
        np.testing.assert_allclose(tau_phi, TAUS, rtol=1e-9)
        np.testing.assert_allclose(tau_m, TAUS, rtol=1e-9)
    # no red phasor columns: no red lifetimes
    assert "tau_phi (red)" not in app.model.parameter_names


def test_one_frequency_constant_moves_the_curves_and_the_columns(app):
    points = add(app, "Lifetime points")
    feature = overlays(app)
    feature.constants.group.parameters_all_dict["f_rep"].value = 40.0
    feature.constants.poll()
    _frame(app)
    x, y = points.function(**points.get_parameters())
    np.testing.assert_allclose(x, mono([0.5, 1, 2, 4, 8], 2 * np.pi * 40e-3)[0])
    tau_phi = np.asarray(app.model.source.column_values("tau_phi"), dtype=float)
    np.testing.assert_allclose(tau_phi, TAUS * 2.0, rtol=1e-9)  # same g, s at half f


def test_phasor_overlays_survive_the_session(app):
    feature = overlays(app)
    add(app, "Universal circle")
    points = add(app, "Lifetime points")
    points.set_spec(t=[1.0, 3.0])
    state = feature.session_state()
    assert [c["kind"] for c in state["curves"]] == ["parametric", "points"]
    assert state["curves"][1]["links"] == {"f": "f_rep", "harmonic": "harmonic"}
    feature.overlays.clear()
    feature.restore_session_state(state, _Context())
    circle, points = feature.overlays.curves
    assert circle.kind == "parametric" and points.spec["t"] == [1.0, 3.0]
    assert points.group.get("f").link is feature.constants.group.parameters_all_dict["f_rep"]
    assert points.labels() == ["1 ns", "3 ns"]


class _Context:
    newer_calibration = False

    def skip(self, _what):
        pass


def test_the_curve_panel_shows_the_fields_of_its_kind(app):
    feature = overlays(app)
    add(app, "Universal circle")
    add(app, "Lifetime points")
    circle, points = feature.overlays.panels
    attrs = lambda panel: {s.get("attr") for s in _walk(panel.spec()["sections"])}
    assert {"x_expr", "y_expr", "where", "t0", "t1"} <= attrs(circle)
    assert "t_values" not in attrs(circle) and "text" not in attrs(circle)
    assert {"x_expr", "t_values", "label_format"} <= attrs(points)
    points.t_values = "2, 4"
    assert points.curve.labels() == ["2 ns", "4 ns"]


def _walk(sections):
    for s in sections:
        yield s
        yield from _walk(s.get("sections") or [])


def test_works_with_chisurf_blocked(tmp_path):
    code = (
        "import sys, importlib.abc\n"
        "class Block(importlib.abc.MetaPathFinder):\n"
        "    def find_spec(self, name, path, target=None):\n"
        "        if name.split('.')[0] == 'chisurf':\n"
        "            raise ImportError('blocked ' + name)\n"
        "sys.meta_path.insert(0, Block())\n"
        "import numpy as np\n"
        "from ndxplorer.app.frame import NdxApp\n"
        "from ndxplorer.core.data_source import DataSource\n"
        "a = NdxApp(features=['overlays'])\n"
        "assert a.chisurf_rpc is None\n"
        "w = 2*np.pi*80e-3; tau = np.array([1.0, 2.0, 4.0])\n"
        "g = 1/(1+(w*tau)**2); s = w*tau*g\n"
        "a.model.set_source(DataSource.from_columns({'g': g, 's': s}))\n"
        "assert np.allclose(a.model.source.column_values('tau_m'), tau)\n"
        "o = next(f for f in a.features if f.name == 'overlays').overlays\n"
        "o.equation_choice = 'FRET trajectory'; c = o.add_curve()\n"
        "x, y = c.points(10, [0, 1], [0, 1]); assert abs(x[-1] - 1) < 1e-9\n"
        "print('ok')\n"
    )
    env = {"HOME": str(tmp_path), "NDXPLORER_SETTINGS_DIR": str(tmp_path),
           "QT_QPA_PLATFORM": "offscreen", "PATH": "/usr/bin:/bin"}
    done = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                          env=env, cwd=str(tmp_path), timeout=300)
    assert done.returncode == 0 and "ok" in done.stdout, done.stderr[-2000:]
