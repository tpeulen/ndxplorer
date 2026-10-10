"""The worm-like-chain FRET trajectory is an entry of the overlay list: added from the panel, drawn on the phasor.

The physics (Kratky-Porod moment, Monte-Carlo chain, Gaussian and rod limits) is
``tests/test_wlc_phasor_trajectory.py``; this is the user path to it.
"""

from __future__ import annotations

import numpy as np

from .test_phasor_overlays import add, app, mono, overlays  # noqa: F401  (the fixture and the helpers)

NAME = "FRET trajectory (WLC distance)"


def test_the_wlc_trajectory_is_listed_added_linked_and_drawn(app):  # noqa: F811
    panel = overlays(app).overlays
    assert NAME in panel.equation_options()
    curve = add(app, NAME)
    constants = overlays(app).constants.group.parameters_all_dict
    assert curve.group.get("f").link is constants["f_rep"]
    assert curve.group.get("tau0").link is constants["tauD0"]
    assert curve.group.get("R0").link is constants["forster_radius"]
    assert float(curve.group.get("lp").value) == 40.0

    x, y = curve.points(120, [0.0, 1.0], [0.0, 0.6])
    assert x.size == 120 and np.all(np.isfinite(x)) and np.all(np.isfinite(y))
    assert np.all((x - 0.5) ** 2 + y ** 2 <= 0.25 + 1e-9)  # a mixture lies inside the circle
    # a longer linker transfers less: the trajectory runs toward the donor-only point (tauD0)
    assert np.all(np.diff(np.arctan2(y, x)) > 0)
    donor = mono(float(constants["tauD0"].value))
    assert np.hypot(x[-1] - donor[0], y[-1] - donor[1]) < np.hypot(x[0] - donor[0], y[0] - donor[1])

    # a stiffer chain is longer on average: less quenched, closer to the donor-only point
    curve.set_parameters({"lp": 400.0})
    sx, sy = curve.points(120, [0.0, 1.0], [0.0, 0.6])
    assert np.all(np.hypot(sx - donor[0], sy - donor[1]) <= np.hypot(x - donor[0], y - donor[1]) + 1e-9)
    assert not np.allclose(sx, x)
    assert curve.error in ("", None)
