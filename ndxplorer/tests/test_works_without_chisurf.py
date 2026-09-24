"""nDXplorer's own features work with chisurf and IMP.bff blocked.

The parameters (:mod:`ndxplorer.core.parameters`), the Gaussian EM, the curve
fit and the constants are nDXplorer's; ChiSurf only mirrors them when it is
there. Each test runs in a fresh interpreter where ``import chisurf`` and
``import IMP`` fail -- exactly what a browser page, a standalone install or a
half-rebuilt IMP.bff looks like -- and drives the emtk app through the feature.
"""

from __future__ import annotations

import os
import subprocess
import sys
import textwrap

PRELUDE = textwrap.dedent("""
    import sys
    for name in ("chisurf", "IMP", "IMP.bff"):
        sys.modules[name] = None          # import chisurf / IMP raises ImportError
    import numpy as np
    from ndxplorer.app import capture
    from ndxplorer.core import chisurf_binding
    assert not chisurf_binding.available()

    def replay(steps):
        run = capture.Replay({"id": "t", "setup": "mfd", "steps": steps},
                             capture.load_catalogue())
        run.run()
        run.settle(3)
        return run

    def feature(run, name):
        return next(f for f in run.app.features if f.name == name)
""")


def run_blocked(body: str) -> None:
    code = PRELUDE + textwrap.dedent(body) + \
        "\nassert sys.modules['chisurf'] is None and sys.modules['IMP'] is None\nprint('OK')\n"
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                            cwd="/tmp", env=dict(os.environ, QT_QPA_PLATFORM="offscreen"))
    assert result.returncode == 0 and "OK" in result.stdout, \
        (result.stdout[-1500:] + result.stderr[-3000:])


def test_gaussian_fit_adds_fits_edits_and_selects():
    run_blocked("""
        run = replay([{"op": "trigger", "action": "actionFit_Gaussians", "checked": True},
                      {"op": "canvas_click", "at": [0.62, 0.74]},
                      {"op": "canvas_click", "at": [0.75, 0.92]}])
        panel = feature(run, "analysis").gaussians
        assert len(panel.components()) == 2
        panel.add_component()
        assert len(panel.components()) == 3
        panel.remove_component()
        table = panel.table
        rho = next(r for r in table.rows() if r["key"] == "rho_1")
        table.edit(rho, "value", "\\u22120.2")
        assert panel.group.parameters_all_dict["rho_1"].value == -0.2
        panel.fit()
        run.settle(3)
        assert run.app.message is None, run.app.message
        after = [c.mu for c in panel.components()]
        assert all(np.all(np.isfinite(m)) for m in after)
        panel.selected = 0
        gates = len(run.app.model.gates)
        panel.select()
        assert len(run.app.model.gates) == gates + 1
        run.app.close()
    """)


def test_overlay_curves_and_the_curve_fit():
    run_blocked("""
        run = replay([])
        f = feature(run, "overlays")
        assert f.overlays.enabled("add_curve")
        f.overlays.equation_choice = "FD/FA vs tau (static line)"
        curve = f.overlays.add_curve()
        panel = f.overlays.panels[0]
        kf = next(r for r in panel.table.rows() if r["key"] == "kf")
        panel.table.edit(kf, "value", "0.3")
        assert curve.get_parameters()["kf"] == 0.3
        f.open_fit(curve)
        dialog = f.window
        run.settle(2)
        assert dialog.cf is not None, dialog.status_text()
        dialog.target = "y"
        assert dialog.cf is not None, dialog.status_text()
        before = dict(curve.get_parameters())
        dialog.run_fit()
        dialog.wait()
        run.settle(2)
        assert dialog.status_text().startswith("reduced"), dialog.status_text()
        assert dict(curve.get_parameters()) != before
        run.app.close()
    """)


def test_the_parameters_tab_edits_links_and_recomputes():
    run_blocked("""
        run = replay([])
        f = feature(run, "overlays")
        table = f.constants.table
        gamma = next(r for r in table.rows() if r["key"] == "gG/gR")
        before = np.asarray(run.app.model.source.column_values("Fd/Fa"), float).copy()
        table.edit(gamma, "value", gamma["value"] * 2.0)
        run.settle(2)
        after = np.asarray(run.app.model.source.column_values("Fd/Fa"), float)
        good = np.isfinite(before) & np.isfinite(after)
        assert np.allclose(after[good] * 2.0, before[good])
        f.constants.set_vector("Bg", [1.0, 2.0], ["0", "1"])
        assert "Bg[]" in [r["key"] for r in table.rows()]
        entries = [label for label, _ in table.menu_entries(
            next(r for r in table.rows() if r["key"] == "Br"), "value")]
        assert entries[:3] == ["Copy", "Paste", "Link…"]
        f.overlays.equation_choice = "FD/FA vs tau (static line)"
        curve = f.overlays.add_curve()
        f.open_link(curve.group.parameters_all_dict["tauD0"], f.overlays.panels[0].table)
        dialog = f.top or f.window
        assert "ChiSurf is not available" in dialog.hint
        target = next(r for r in dialog.targets() if r["owner"] == "ndX" and r["name"] == "tauD0")
        dialog.link(target)
        f.constants.group.parameters_all_dict["tauD0"].value = 3.3
        assert curve.get_parameters()["tauD0"] == 3.3
        run.app.close()
    """)
