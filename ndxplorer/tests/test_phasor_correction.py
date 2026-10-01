"""The corrected phasor columns: IRF referencing and background removal (tttrlib's form).

Synthetic TCSPC: mono-exponential decays convolved with a shifted Gaussian IRF,
plus flat background, Poisson-sampled. Their raw phasor (tttrlib
``DecayPhasor``) lies off the universal circle; with ``g_irf``/``s_irf`` from
the IRF histogram and ``n_bg`` the background photons, the shipped equations
put ``g corr``/``s corr`` on the circle at the right lifetime.
"""

from __future__ import annotations

import json
import os
import pathlib

import numpy as np
import pytest
import yaml

tttrlib = pytest.importorskip("tttrlib")

from ndxplorer.analysis import phasor_reference as ref  # noqa: E402
from ndxplorer.core.data_source import compute_values  # noqa: E402
from ndxplorer.settings import defaults  # noqa: E402

F_MHZ = 80.0
N_CH = 1024
DT = 1e3 / F_MHZ / N_CH                  # ns per channel: one period
FREQ = F_MHZ * 1e6 * DT * 1e-9           # tttrlib's frequency: cycles per channel
OMEGA = 2 * np.pi * F_MHZ * 1e-3
TAUS = (0.5, 1.0, 2.0, 4.0, 8.0)
T = np.arange(N_CH) * DT


def irf_shape(t0=2.5, sigma=0.12):
    x = np.exp(-0.5 * ((T - t0) / sigma) ** 2)
    return x / x.sum()


def decay(tau, n=400_000, f_bg=0.08, rng=None):
    """Counts: the periodic convolution of IRF and exp(-t/tau), plus flat background."""
    rng = rng or np.random.default_rng(0)
    d = np.real(np.fft.ifft(np.fft.fft(irf_shape()) * np.fft.fft(np.exp(-T / tau))))
    d /= d.sum()
    return rng.poisson(n * ((1 - f_bg) * d + f_bg / N_CH)), n * f_bg


def table(rows):
    store = tttrlib.DataStore("t")
    store.set_n_rows(len(next(iter(rows.values()))))
    for name, values in rows.items():
        store.add(name, np.asarray(values, dtype=float))
    return store


def shipped():
    constants = json.loads((defaults.SHIPPED_DIR / "mfd.constants.json").read_text())
    equations = yaml.safe_load((defaults.SHIPPED_DIR / "mfd.equations.yaml").read_text())
    return constants, equations


def column(store, name):
    names = [store.column(i).name() for i in range(store.n_columns())]
    return np.asarray(store.column(names.index(name)).numpy(), dtype=float)


@pytest.fixture(scope="module")
def measured():
    rng = np.random.default_rng(7)
    irf_counts = rng.poisson(2e6 * irf_shape() + 30.0)       # a mirror with dark counts
    irf = ref.histogram_phasor(irf_counts, FREQ, ref.flat_level(irf_counts))
    rows = {"g": [], "s": [], "Number of Photons": [], "n_bg": []}
    for tau in TAUS:
        counts, n_bg = decay(tau, rng=rng)
        g, s = tttrlib.DecayPhasor.phasor_of_bincounts(counts.astype(np.int32), FREQ, 0, 1.0, 0.0)
        rows["g"].append(g)
        rows["s"].append(s)
        rows["Number of Photons"].append(counts.sum())
        rows["n_bg"].append(n_bg)
    return irf, rows


def test_the_raw_phasor_is_off_the_circle(measured):
    _irf, rows = measured
    g, s = np.asarray(rows["g"]), np.asarray(rows["s"])
    assert np.all(np.abs((g - 0.5) ** 2 + s ** 2 - 0.25) > 0.02)


def test_the_corrected_phasor_is_on_the_circle_at_tau(measured):
    irf, rows = measured
    rows = dict(rows)
    constants, equations = shipped()
    n_bg = float(np.mean(rows.pop("n_bg")))  # the same background in every row
    store = table(rows)
    constants.update({"f_rep": F_MHZ, "g_irf": irf["g"], "s_irf": irf["s"], "n_bg": n_bg})
    compute_values(store, constants, equations)
    g, s = column(store, "g corr"), column(store, "s corr")
    np.testing.assert_allclose((g - 0.5) ** 2 + s ** 2, 0.25, atol=4e-3)
    np.testing.assert_allclose(column(store, "tau_phi"), TAUS, rtol=0.03)
    np.testing.assert_allclose(column(store, "tau_m"), TAUS, rtol=0.03)


def test_the_equations_are_tttrlibs_complex_division(measured):
    irf, rows = measured
    rows = dict(rows)
    rows.pop("n_bg", None)
    constants, equations = shipped()
    constants.update({"g_irf (green)": irf["g"], "s_irf (green)": irf["s"]})
    store = table({"g (green)": rows["g"], "s (green)": rows["s"],
                   "Number of Photons (green)": rows["Number of Photons"]})
    compute_values(store, constants, equations)
    for i, (g, s) in enumerate(zip(rows["g"], rows["s"])):
        assert column(store, "g corr (green)")[i] == pytest.approx(
            tttrlib.DecayPhasor.g(irf["g"], irf["s"], g, s), abs=1e-12)
        assert column(store, "s corr (green)")[i] == pytest.approx(
            tttrlib.DecayPhasor.s(irf["g"], irf["s"], g, s), abs=1e-12)


def test_the_defaults_change_nothing():
    constants, equations = shipped()
    g, s = np.array([0.3, 0.7]), np.array([0.4, 0.2])
    store = table({"g": g, "s": s, "Number of Photons": [10, 20]})
    compute_values(store, constants, equations)
    np.testing.assert_array_equal(column(store, "g corr"), g)
    np.testing.assert_array_equal(column(store, "s corr"), s)


def test_a_reference_of_known_lifetime_is_an_irf():
    """The reference dye's phasor divided by its place on the circle is the IRF phasor."""
    rng = np.random.default_rng(3)
    dye, _ = decay(4.0, n=2_000_000, f_bg=0.0, rng=rng)
    z = ref.histogram_phasor(dye, FREQ)
    z_ref = complex(z["g"], z["s"]) * complex(1.0, -OMEGA * 4.0)
    irf = ref.histogram_phasor(rng.poisson(2e6 * irf_shape()), FREQ)
    assert abs(z_ref - complex(irf["g"], irf["s"])) < 0.01


def test_the_background_level_of_a_histogram():
    rng = np.random.default_rng(1)
    counts = rng.poisson(1e6 * irf_shape() + 50.0)
    assert ref.flat_level(counts) == pytest.approx(50.0, rel=0.03)


MIRROR = pathlib.Path("/Users/tpeulen/dev/tttr-data/imaging/pq/ht3/crn_clv_mirror.ht3")


@pytest.mark.skipif(not MIRROR.exists(), reason="tttr-data mirror measurement not here")
def test_the_mirror_of_the_clsm_data_is_an_irf():
    r = ref.reference_phasor(str(MIRROR), [0, 1], 32.0, 1.0)
    assert abs(complex(r["g_irf"], r["s_irf"])) == pytest.approx(1.0, abs=0.01)
    assert r["f_rep_header"] == pytest.approx(32.0, rel=1e-3)
    with pytest.raises(ValueError, match="no instrument response"):
        ref.reference_phasor(str(MIRROR), [4, 5], 32.0, 1.0)   # the red detectors saw none
