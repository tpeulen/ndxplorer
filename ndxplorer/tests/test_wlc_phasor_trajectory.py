"""The worm-like-chain phasor trajectory, against answers that do not come from its own code.

* the Kratky-Porod mean-square end-to-end distance, an exact closed form;
* a Monte-Carlo of a discrete (freely rotating) chain with the same persistence length;
* the Gaussian-chain and rod limits;
* the phasor of the same Monte-Carlo distances averaged by brute force.
"""

from __future__ import annotations

import pathlib

import numpy as np
import pytest
import yaml
from ndxplorer.core.overlay_curves import compile_spec, spec_parameter_names
from ndxplorer.core.wlc import kratky_porod_r2, wlc_pdf

R = np.linspace(0.5, 200.0, 400)


def monte_carlo_distances(contour, persistence, segments=200, chains=20000, seed=3):
    """End-to-end distances of a freely rotating chain whose tangents correlate as exp(-ds/lp)."""
    rng = np.random.default_rng(seed)
    ds = contour / segments
    cos_theta = np.exp(-ds / persistence)
    sin_theta = np.sqrt(1.0 - cos_theta ** 2)
    tangent = np.zeros((chains, 3))
    tangent[:, 2] = 1.0
    position = tangent * ds
    for _ in range(segments - 1):
        a = rng.normal(size=(chains, 3))
        a -= tangent * np.sum(a * tangent, 1, keepdims=True)
        a /= np.linalg.norm(a, axis=1, keepdims=True)
        # a uniform azimuth about the old tangent: a random perpendicular, rotated by a random angle
        phi = rng.uniform(0.0, 2.0 * np.pi, size=chains)[:, None]
        b = np.cross(tangent, a)
        perpendicular = np.cos(phi) * a + np.sin(phi) * b
        tangent = cos_theta * tangent + sin_theta * perpendicular
        position += tangent * ds
    return np.linalg.norm(position, axis=1)


@pytest.mark.parametrize("persistence", [5.0, 20.0, 60.0, 150.0])
def test_second_moment_is_kratky_porod(persistence):
    lengths = np.linspace(40.0, 200.0, 17)
    p = wlc_pdf(R, lengths, persistence)
    assert np.all(p >= 0) and np.allclose(p.sum(axis=1), 1.0)
    measured = (p * R ** 2).sum(axis=1)
    np.testing.assert_allclose(measured, kratky_porod_r2(lengths, persistence), rtol=0.02)


@pytest.mark.parametrize("contour, persistence", [(100.0, 20.0), (100.0, 60.0), (150.0, 40.0)])
def test_the_distribution_matches_a_monte_carlo_chain(contour, persistence):
    mc = monte_carlo_distances(contour, persistence)
    p = wlc_pdf(R, contour, persistence)[0]
    assert abs((p * R).sum() / mc.mean() - 1) < 0.03
    assert abs(np.sqrt((p * R ** 2).sum()) / np.sqrt((mc ** 2).mean()) - 1) < 0.03
    # the whole shape: the cumulative distributions stay within 6 percentage points
    cdf = np.cumsum(p)
    sample_cdf = np.searchsorted(np.sort(mc), R) / mc.size
    assert np.max(np.abs(cdf - sample_cdf)) < 0.06


def test_flexible_chain_is_gaussian_and_stiff_chain_is_a_rod():
    r = np.linspace(0.5, 400, 800)
    p = wlc_pdf(r, 400.0, 3.0)[0]
    mean_square = kratky_porod_r2(400.0, 3.0)
    assert abs((p * r).sum() / np.sqrt(8 * mean_square / (3 * np.pi)) - 1) < 0.03  # <R> of a Gaussian chain
    stiff = wlc_pdf(R, 25.0, 4000.0)[0]
    assert abs((stiff * R).sum() - 25.0) < 1.0  # R = L


# -- the phasor trajectory -------------------------------------------------------------------------------------------

ENTRIES = yaml.safe_load(
    (pathlib.Path(__file__).parents[1] / "settings" / "curve_equations.yaml").read_text())
SPEC = next(e for e in ENTRIES if e["name"] == "FRET trajectory (WLC distance)")["parametric"]
GAUSSIAN = next(e for e in ENTRIES if e["name"] == "FRET trajectory (Gaussian distance)")["parametric"]


def phasor(spec, lengths, **parameters):
    points = dict(spec, kind="points", t=list(map(float, lengths)))
    values = dict(f=80.0, harmonic=1, tau0=4.0, R0=52.0)
    values.update(parameters)
    x, y = compile_spec(points)(**values)
    return np.asarray(x), np.asarray(y)


def brute_force_phasor(distances, f=80.0, tau0=4.0, R0=52.0):
    omega = 2 * np.pi * f * 1e-3
    tau = tau0 * (1 - 1 / (1 + (distances / R0) ** 6))
    g = 1 / (1 + (omega * tau) ** 2)
    return np.sum(tau * g) / np.sum(tau), np.sum(tau * omega * tau * g) / np.sum(tau)


def test_the_entry_declares_its_parameters():
    assert spec_parameter_names(SPEC) == ["f", "harmonic", "lp", "tau0", "R0"]


@pytest.mark.parametrize("contour, persistence", [(60.0, 20.0), (100.0, 40.0), (150.0, 60.0)])
def test_the_trajectory_point_is_the_phasor_of_a_monte_carlo_chain(contour, persistence):
    mc = monte_carlo_distances(contour, persistence, seed=7)
    g, s = brute_force_phasor(mc)
    x, y = phasor(SPEC, [contour], lp=persistence)
    assert abs(x[0] - g) < 0.02 and abs(y[0] - s) < 0.02


def test_trajectory_lies_inside_the_circle_and_follows_the_fret_limits():
    lengths = np.linspace(20.0, 200.0, 19)
    x, y = phasor(SPEC, lengths, lp=40.0)
    assert np.all(y > 0) and np.all((x - 0.5) ** 2 + y ** 2 <= 0.25 + 1e-9)
    # the mean distance grows with the contour length: less transfer, so the donor lifetime
    # (phase) rises monotonically toward the donor-only point
    phase = np.arctan2(y, x)
    assert np.all(np.diff(phase) > 0)
    # a rod-like chain is the fixed-distance trajectory at RDA = L (lp >> L)
    stiff = phasor(SPEC, [30.0, 60.0], lp=2000.0)
    omega = 2 * np.pi * 80.0 * 1e-3
    for index, distance in enumerate((30.0, 60.0)):
        tau = 4.0 * (1 - 1 / (1 + (distance / 52.0) ** 6))
        assert abs(stiff[0][index] - 1 / (1 + (omega * tau) ** 2)) < 0.015
        assert abs(stiff[1][index] - omega * tau / (1 + (omega * tau) ** 2)) < 0.01


def test_a_flexible_chain_is_the_gaussian_chain_trajectory():
    """L >> lp: the Maxwell distribution of a Gaussian chain, P(R) ~ R^2 exp(-3 R^2 / (2 <R^2>))."""
    contour, persistence = 600.0, 3.0
    x, y = phasor(SPEC, [contour], lp=persistence)
    mean_square = kratky_porod_r2(contour, persistence)
    r = np.linspace(0.05, 12 * np.sqrt(mean_square), 20000)
    weight = r ** 2 * np.exp(-3 * r ** 2 / (2 * mean_square))
    omega = 2 * np.pi * 80.0 * 1e-3
    tau = 4.0 * (1 - 1 / (1 + (r / 52.0) ** 6))
    g = 1 / (1 + (omega * tau) ** 2)
    a = weight * tau
    assert abs(x[0] - np.sum(a * g) / np.sum(a)) < 0.015
    assert abs(y[0] - np.sum(a * omega * tau * g) / np.sum(a)) < 0.015
