"""Population-wise factors and gating dimensions of the FRET calibration.

The options dialog's "Populations" panel: *Population-wise factors* (off /
auto / on -- tttrlib's species-specific gamma never, when the BIC prefers it,
or whenever it is identifiable), the *Population finder*, and the *Gating
dimensions* this measurement has. Checked against synthetic two-species bursts
whose gammas (0.6, 1.2) and lifetimes are known, and against the cal1
measurement, whose pinned numbers must not move.
"""
from __future__ import annotations

import os
import types

import numpy as np
import pytest

tttrlib = pytest.importorskip("tttrlib")
if not hasattr(tttrlib, "auto_calibrate"):
    pytest.skip("tttrlib without auto_calibrate", allow_module_level=True)

from ndxplorer.analysis import fret_calibration as fc  # noqa: E402
from ndxplorer.analysis.fret_backend import dimension_columns  # noqa: E402

TAU_D0, TAU_A0 = 4.0, 3.0
ALPHA, DELTA, BETA = 0.07, 0.05, 0.9
SPECIES = ((0.3, 0.6, 2000), (0.7, 1.2, 2000))
SHARED = ((0.3, 1.0, 2000), (0.7, 1.0, 2000))
ZERO = {"Bg": 0.0, "Br": 0.0, "By": 0.0, "alpha": 0.0, "beta": 0.0, "gG/gR": 1.0, "r": 1.0,
        "PhiA": 1.0, "PhiD": 1.0, "forster_radius": 52.0, "tauD0": TAU_D0}
DATA = os.environ.get("TTTRLIB_DATA", "/Users/tpeulen/dev/tttr-data")
CAL1 = os.path.join(DATA, "sm", "cal1", "001_60g_25r_cal1_cy3b_8_18_33bp_atto647n_alex.pto")
CAL1_CONSTANTS = {"Bg": 1.2, "Br": 0.6, "By": 0.6, "PhiA": 0.32, "PhiD": 0.8, "alpha": 0.015,
                  "beta": 0.005, "forster_radius": 52.0, "gG/gR": 0.6, "r": 1.0, "tauD0": 4.0}


def bursts(fret=SPECIES, seed=5, n_do=500, n_ao=400):
    """ALEX/PIE bursts with donor and acceptor lifetimes, as a burst table names them.

    ``fret`` holds ``(E, gamma_s, n)`` per FRET species; a species' gamma is
    its acceptor quantum yield, so its acceptor lifetime scales with it. The
    donor lifetime lies on the no-linker static line ``tau_D(0) (1 - E)``.
    """
    rng = np.random.default_rng(seed)
    cols = {k: [] for k in ("dd", "da", "aa", "tau_d", "tau_a")}

    def add(dd, da, aa, tau_d, tau_a):
        n = len(dd)
        cols["dd"].append(rng.poisson(dd)), cols["da"].append(rng.poisson(da))
        cols["aa"].append(rng.poisson(aa))
        cols["tau_d"].append(tau_d + rng.normal(0, 0.15, n))
        cols["tau_a"].append(tau_a + rng.normal(0, 0.15, n))

    tot = rng.uniform(60, 200, n_do)
    add(tot, ALPHA * tot, np.full(n_do, 0.3), np.full(n_do, TAU_D0), np.full(n_do, np.nan))
    tot = rng.uniform(60, 200, n_ao)
    add(np.full(n_ao, 0.3), DELTA * tot * BETA, tot * BETA, np.full(n_ao, np.nan),
        np.full(n_ao, TAU_A0))
    for e, g, n in fret:
        tot = rng.uniform(60, 200, n)
        f_dd, f_da, f_aa = tot * (1 - e) / g, tot * e, tot * BETA
        add(f_dd, f_da + ALPHA * f_dd + DELTA * f_aa, f_aa, np.full(n, TAU_D0 * (1 - e)),
            np.full(n, TAU_A0 * g))
    cat = {k: np.concatenate(v).astype(float) for k, v in cols.items()}
    return {"Number of Photons (green)": cat["dd"], "Number of Photons (red)": cat["da"],
            "Number of Photons (yellow)": cat["aa"], "Tau (green)": cat["tau_d"],
            "Tau (yellow)": cat["tau_a"]}


def options(mode="auto", **settings):
    opts = fc.CalibrationOptions(donor_lifetime=TAU_D0)
    opts.background, opts.n_bootstrap, opts.linker_sigma = "none", 0, 0.0
    opts.species_factors = mode
    for key, value in settings.items():
        setattr(opts, key, value)
    return opts


def run(columns, mode="auto", **settings):
    result = fc.calibrate(columns, ZERO, options(mode, **settings))
    assert result["ok"], result.get("error")
    return result


# ------------------------------------------------------------------ options
def test_the_options_round_trip_through_the_form_and_the_run():
    opts = fc.CalibrationOptions()
    kwargs = opts.as_kwargs()
    # the defaults are what the calibration always did
    assert kwargs["species_factors"] == "auto" and kwargs["dimensions"] == []
    assert kwargs["population_method"] == "hdbscan"
    opts.species_factors, opts.gate_E, opts.gate_tau_d = "On", True, True
    opts.population_method = "hdbscan"
    kwargs = opts.as_kwargs()
    assert kwargs["species_factors"] == "on"
    assert kwargs["dimensions"] == ["S", "E", "tau_d"]
    assert kwargs["population_method"] == "hdbscan"
    opts.gate_E = opts.gate_tau_d = False
    assert opts.dimensions() == []           # S alone is the stoichiometry gating
    opts.species_factors = "nonsense"
    assert opts.as_kwargs()["species_factors"] == "auto"
    # every attribute of the options is a field of the form, and back
    attrs = set()

    def walk(sections):
        for section in sections:
            if section.get("attr"):
                attrs.add(section["attr"])
            walk(section.get("sections") or [])

    walk(fc.CalibrationOptions.spec()["sections"])
    assert {"species_factors", "population_method", *fc.DIMENSION_ATTRS.values()} <= attrs
    panel = next(s for s in fc.CalibrationOptions.spec()["sections"]
                 if s.get("title") == "Populations")
    text = str(panel)
    assert "Make scalar" in text and "25 s" in text and "lifetime" in text


def test_off_writes_scalar_factors_only():
    columns = bursts()
    off, auto = run(columns, "off"), run(columns, "auto")
    assert off["vectors"] == {} and off["model_selection"] is None
    assert "P(FRET 1)" not in off["new_columns"]
    # the scalar constants are the calibration's either way
    assert off["constants"] == auto["constants"]
    written = []
    fc.apply_result(off, write_constants=lambda values: None,
                    write_vector=lambda name, vector: written.append(name))
    assert written == []
    assert "Model selection: not run" in fc.report_text(off)


@pytest.mark.parametrize("mode", ["auto", "on"])
def test_two_species_get_their_own_gamma(mode):
    result = run(bursts(), mode)
    ms = result["model_selection"]
    assert ms["identifiable"] and ms["selected"] == "species"
    vector = result["vectors"]["gamma"]
    assert vector["populations"] == ["FRET 1", "FRET 2"]
    np.testing.assert_allclose(vector["values"], [0.6, 1.2], rtol=0.08)
    assert result["vector_labels"] == ["gamma[FRET 1]", "gamma[FRET 2]"]
    assert {"Population", "P(FRET 1)", "P(FRET 2)"} <= set(result["new_columns"])
    report = fc.report_text(result)
    assert "per population — BIC shared" in report and "gamma[FRET 1] = 0.6" in report
    assert "Identifiable: yes" in report


def test_on_writes_per_population_gamma_the_bic_would_not_choose():
    columns = bursts(SHARED)
    auto, on = run(columns, "auto"), run(columns, "on")
    assert auto["model_selection"]["selected"] == "shared" and auto["vectors"] == {}
    assert on["model_selection"]["forced"]
    np.testing.assert_allclose(on["vectors"]["gamma"]["values"], [1.0, 1.0], rtol=0.08)
    assert "forced; the BIC preferred shared" in fc.report_text(on)
    # the accurate efficiency of each species is still right
    e = on["new_columns"]["FRET efficiency (accurate)"]
    labels = on["new_columns"]["Population"]
    assert np.nanmean(e[labels == 0]) == pytest.approx(0.3, abs=0.03)
    assert np.nanmean(e[labels == 1]) == pytest.approx(0.7, abs=0.03)


def test_without_lifetimes_every_mode_is_scalar():
    columns = bursts()
    del columns["Tau (green)"], columns["Tau (yellow)"]
    results = {mode: run(columns, mode) for mode in ("off", "auto", "on")}
    assert all(r["vectors"] == {} for r in results.values())
    assert results["on"]["model_selection"]["identifiable"] is False
    assert results["off"]["constants"] == results["on"]["constants"]


def test_a_held_gamma_writes_no_gamma_vector():
    result = run(bursts(), "on", fit_gamma=False)
    assert result["vectors"] == {} and result["model_selection"]["held"]


# ------------------------------------------------------------- dimensions
def test_the_dimensions_a_table_has():
    names = list(bursts())
    found = dimension_columns(names)
    assert found == {"S": "", "E": "", "tau_d": "Tau (green)", "tau_a": "Tau (yellow)",
                     "r_d": None, "r_a": None}
    assert dimension_columns(["Number of Photons (green)"])["S"] is None
    mfd = dimension_columns(["Green Count Rate (KHz)", "Red Count Rate (KHz)", "Tau (green)",
                             "Tau (red)", "r Scatter (green)", "r Scatter (red)"])
    assert mfd["tau_a"] == "Tau (red)" and mfd["r_d"] == "r Scatter (green)"
    assert mfd["r_a"] == "r Scatter (red)"


def test_an_unavailable_dimension_is_left_out_and_said():
    result = run(bursts(), "auto", gate_E=True, gate_r_d=True)
    assert result["dimensions"] == ["S", "E"]
    assert any("r_d left out" in note for note in result["notes"])


def _dialog(names):
    pytest.importorskip("emtk.dialog_window")
    from ndxplorer.app.features.accurate_fret import OptionsDialog

    app = types.SimpleNamespace(model=types.SimpleNamespace(
        source=types.SimpleNamespace(parameter_names=names),
        manager=types.SimpleNamespace(constants={"tauD0": 4.0})))
    return OptionsDialog(types.SimpleNamespace(app=app))


def _described(spec, attr):
    found = []

    def walk(sections):
        for section in sections:
            if section.get("attr") == attr:
                found.append(section.get("description", ""))
            walk(section.get("sections") or [])

    walk(spec["sections"])
    return found[0]


def test_dimensions_the_measurement_lacks_are_disabled_with_the_reason():
    names = ["Number of Photons (green)", "Number of Photons (red)",
             "Number of Photons (yellow)"]
    dialog = _dialog(names)
    assert dialog.enabled("gate_S") and dialog.enabled("gate_E")
    for attr in ("gate_tau_d", "gate_tau_a", "gate_r_d", "gate_r_a"):
        assert not dialog.enabled(attr), attr
        assert "Unavailable: this measurement has no" in _described(dialog.spec, attr)
    assert "donor lifetime column" in _described(dialog.spec, "gate_tau_d")
    assert dialog.options.gate_tau_d is False
    with_lifetimes = _dialog(names + ["Tau (green)"])
    assert with_lifetimes.enabled("gate_tau_d") and not with_lifetimes.enabled("gate_tau_a")
    assert "Read from the column 'Tau (green)'" in _described(with_lifetimes.spec, "gate_tau_d")
    # the form writes the options the run gets
    with_lifetimes.species_factors = "off"
    with_lifetimes.gate_tau_d = True
    assert with_lifetimes.options.as_kwargs()["dimensions"] == ["S", "tau_d"]
    assert with_lifetimes.options.as_kwargs()["species_factors"] == "off"


def test_the_population_finder_says_when_tttrlib_lacks_it():
    from ndxplorer.analysis.fret_backend import population_method_reason

    dialog = _dialog(["Number of Photons (green)", "Number of Photons (red)"])
    reason = population_method_reason()
    assert dialog.enabled("population_method") == (not reason)
    if reason:
        assert "Unavailable" in _described(dialog.spec, "population_method")
        result = run(bursts(), "off", population_method="hdbscan")
        assert result["population_method"] == "gmm"
        assert any("population finder" in note for note in result["notes"])


# ------------------------------------------------------------------- cal1
@pytest.mark.parametrize("mode", ["off", "auto", "on"])
def test_cal1_keeps_its_numbers_in_every_mode(mode):
    """cal1's burst table has no donor lifetime column: the per-population model
    is not identifiable, and every mode gives the pinned global factors."""
    if not os.path.exists(CAL1):
        pytest.skip("cal1 measurement not present")
    from ndxplorer.io.fret_calibration_io import container_of
    from ndxplorer.io.loading import read

    table = read(CAL1)
    opts = fc.CalibrationOptions(donor_lifetime=4.0)
    opts.n_bootstrap, opts.species_factors = 10, mode
    result = fc.calibrate(fc.burst_columns(table), CAL1_CONSTANTS, opts,
                          container=container_of(types.SimpleNamespace(data_source=table)))
    assert result["ok"], result.get("error")
    factors = result["factors"]
    assert factors["gamma"] == pytest.approx(0.7502, abs=5e-4)
    assert factors["alpha"] == pytest.approx(0.1570, abs=5e-4)
    assert factors["beta"] == pytest.approx(1.0599, abs=5e-4)
    assert factors["delta"] == pytest.approx(0.0674, abs=5e-4)
    assert result["vectors"] == {}
    if mode != "off":
        assert result["model_selection"]["selected"] == "shared"
        assert not result["model_selection"]["identifiable"]
