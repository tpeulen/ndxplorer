"""The accurate-FRET calibration of a burst table, computed by tttrlib.

This is ndX's own calibration backend (:func:`calibrate_columns`, the contract
of :func:`ndxplorer.analysis.fret_calibration.calibrate`): burst columns and the
window's constants in, the result dict out. The algorithm is
``tttrlib.auto_calibrate``; what is here is ndX's side of it -- which column is
which channel, ndX's constant names against the Hellenkamp factors, the
background choices, and the columns and vector constants the result adds.

ChiSurf is optional. When it imports, the static FRET line is ChiSurf's
(linker-broadened); without it the lifetime route uses the no-linker line
``E = 1 - tau/tau_D(0)`` and the report says so. ChiSurf's own windows call
this function too, adding their light-path priors through ``priors``.
"""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Mapping, Optional

import numpy as np
import tttrlib

from .fret_background import (ROLE_TO_BG, burst_durations_ms, fitted_background,
                              measured_background)

__all__ = ["calibrate_columns", "factors_from_constants", "constants_from_factors",
           "FACTOR_NAMES"]

#: The factors a calibration can write, in the paper's order (``r0`` travels along).
FACTOR_NAMES = ("alpha", "beta", "gamma", "delta", "r0")

_BOUNDS = {"gamma": (0.05, 20.0), "alpha": (0.0, 1.0), "beta": (0.01, 100.0),
           "delta": (0.0, 1.0), "bg_dd": (0.0, 1e6), "bg_da": (0.0, 1e6), "bg_aa": (0.0, 1e6),
           "r0": (1.0, 200.0), "phi_a": (0.0, 1.0), "phi_d": (0.0, 1.0)}


def _clamp(name: str, value: float) -> float:
    lo, hi = _BOUNDS[name]
    return float(min(hi, max(lo, float(value))))


def factors_from_constants(constants: Mapping[str, Any],
                           start: Optional[Mapping[str, float]] = None) -> Dict[str, float]:
    """ndX constants -> Hellenkamp factors.

    ndX's ``beta`` is the direct excitation (Hellenkamp ``delta``), its ``r`` is
    ``1/beta``, and its effective ``gamma = (PhiA/PhiD) / (gG/gR)``. A constant
    that is missing keeps its value in *start* (the uncorrected defaults when
    omitted); values are clamped to the factor bounds.
    """
    f = {"gamma": 1.0, "alpha": 0.0, "beta": 1.0, "delta": 0.0, "bg_dd": 0.0, "bg_da": 0.0,
         "bg_aa": 0.0, "r0": 52.0, "phi_a": 1.0, "phi_d": 1.0}
    f.update({k: float(v) for k, v in dict(start or {}).items() if k in f})

    def get(key):
        value = constants.get(key)
        try:
            value = float(value)
        except (TypeError, ValueError):
            return None
        return value if np.isfinite(value) else None

    for key, name in (("PhiA", "phi_a"), ("PhiD", "phi_d"), ("alpha", "alpha"), ("Bg", "bg_dd"),
                      ("Br", "bg_da"), ("By", "bg_aa"), ("forster_radius", "r0"),
                      ("beta", "delta")):
        if get(key) is not None:
            f[name] = _clamp(name, get(key))
    if get("r") is not None and get("r") > 0:
        f["beta"] = _clamp("beta", 1.0 / get("r"))
    if get("gG/gR") and f["phi_d"]:
        f["gamma"] = _clamp("gamma", (f["phi_a"] / f["phi_d"]) / get("gG/gR"))
    return f


def constants_from_factors(f: Mapping[str, float]) -> Dict[str, float]:
    """Hellenkamp factors -> ndX constants (the inverse of :func:`factors_from_constants`)."""
    gamma, beta = float(f["gamma"]), float(f["beta"])
    return {
        "gG/gR": (f["phi_a"] / f["phi_d"]) / gamma if gamma else 1.0,
        "alpha": float(f["alpha"]), "beta": float(f["delta"]), "r": 1.0 / beta if beta else 1.0,
        "Bg": float(f["bg_dd"]), "Br": float(f["bg_da"]), "By": float(f["bg_aa"]),
        "PhiA": float(f["phi_a"]), "PhiD": float(f["phi_d"]), "forster_radius": float(f["r0"]),
    }


def _options(options) -> Dict[str, Any]:
    if options is None:
        return {}
    if hasattr(options, "as_kwargs"):
        return dict(options.as_kwargs())
    return dict(options)


def _static_line(tau_d0: float, r0: float, linker_sigma: float):
    """ChiSurf's linker-broadened static FRET line, or ``None`` without ChiSurf."""
    try:
        from chisurf.core.fluorescence.fret.lines import static_fret_line
    except Exception:  # noqa: BLE001 - ChiSurf is optional
        return None
    return static_fret_line(float(tau_d0), r0=float(r0), sigma=float(linker_sigma))


def calibrate_columns(columns: Mapping[str, np.ndarray], constants: Mapping[str, Any],
                      options=None, *, container: str = "",
                      progress: Optional[Callable[[int, int, str], Any]] = None,
                      priors: Optional[Mapping[str, tuple]] = None) -> dict:
    """Determine ndX's correction constants from the loaded bursts.

    Parameters
    ----------
    columns : mapping of str to ndarray
        The burst table's numeric columns.
    constants : mapping
        The window's constants: the starting point, and what held factors keep.
    options : CalibrationOptions or mapping
        ``factors``, ``background`` ("fit", "measurement", "constants",
        "none"), ``min_population``, ``gamma_source``, ``use_priors``,
        ``n_bootstrap``, ``donor_lifetime``, ``linker_sigma``,
        ``inject_columns``; optionally ``columns`` (``{role: column}``
        overrides) and ``seed``.
    container : str
        The ``.pto`` the bursts came from (``background="measurement"``).
    progress : callable, optional
        ``progress(step, total, message)``; ``False`` stops the calibration.
    priors : mapping, optional
        ``{"gamma"|"alpha"|"delta": (mu, sigma)}`` light-path priors.

    Returns
    -------
    dict
        The contract's result (see :func:`ndxplorer.analysis.fret_calibration.calibrate`).
    """
    from .fret_result import finish

    opts = _options(options)
    table = {str(k): np.asarray(v, dtype=float) for k, v in dict(columns).items()}
    mapping = {**tttrlib.guess_burst_columns(list(table)),
               **{k: v for k, v in dict(opts.get("columns") or {}).items() if v}}
    for role in ("i_dd", "i_da"):
        if mapping.get(role) not in table:
            return {"ok": False, "error": f"could not identify the {role} column among "
                                          f"{', '.join(list(table)[:12])}…; pass it explicitly"}
    pick = lambda role: table.get(mapping.get(role, ""))  # noqa: E731
    background = str(opts.get("background", "constants"))
    notes: List[str] = []
    per_burst: Dict[str, np.ndarray] = {}
    rates: Dict[str, float] = {}
    if background == "measurement":
        per_burst, rates, note = measured_background(table, container)
        if note:
            notes.append(note)

    start = factors_from_constants(constants)
    if background in ("none", "fit") or per_burst:
        start.update(bg_dd=0.0, bg_da=0.0, bg_aa=0.0)  # subtracted per burst instead
    kept = {n: start[n] for n in FACTOR_NAMES}
    tau_d0 = opts.get("donor_lifetime")
    if tau_d0 is None:
        tau_d0 = float(constants.get("tauD0", 4.0) or 4.0)
    tau_f = pick("tau_f")
    line = None
    if tau_f is not None:
        line = _static_line(tau_d0, start["r0"], float(opts.get("linker_sigma", 6.0)))
        if line is None:
            notes.append(f"ChiSurf is not available: the lifetime route used the no-linker line "
                         f"E = 1 - tau/tau_D(0) instead of the static FRET line "
                         f"(tau_D(0) = {float(tau_d0):.2f} ns)")

    def counts(role):
        values = pick(role)
        if values is None or role not in per_burst:
            return values
        return np.clip(values - per_burst[role], 0.0, None)

    def run(n_bootstrap: int, prefix: str) -> dict:
        seed = int(opts.get("seed", 0))
        rng = np.random.default_rng(seed)  # the draws ChiSurf's calibration always used
        cal_options = {"gamma_source": opts.get("gamma_source", "auto"),
                       "n_bootstrap": int(n_bootstrap), "seed": seed,
                       "use_priors": bool(opts.get("use_priors", True)),
                       "donor_lifetime": float(tau_d0), "line": line,
                       "bootstrap_indices": lambda size: rng.integers(0, size, size)}
        consts = {k: start[k] for k in ("gamma", "alpha", "beta", "delta", "bg_dd", "bg_da",
                                        "bg_aa", "r0")}
        consts["priors"] = dict(priors or {})
        wrapped = None if progress is None else (
            lambda step, total, message: progress(step, total, prefix + message))
        result = tttrlib.auto_calibrate(
            {"i_dd": counts("i_dd"), "i_da": counts("i_da"), "i_aa": counts("i_aa"),
             "tau_f": tau_f}, consts, cal_options, wrapped)
        for name in ("gamma", "alpha", "beta", "delta"):
            start[name] = float(result["factors"][name])  # the next pass starts here
        return result

    fitted: Dict[str, float] = {}
    if background == "fit":
        first = run(0, "pass 1 of 2 (backgrounds): ")
        fitted = fitted_background(pick("i_dd"), pick("i_da"), pick("i_aa"), first["split"],
                                   durations=burst_durations_ms(table, "green"),
                                   min_population=int(opts.get("min_population", 20)))
        for role, detector in (("i_dd", "green"), ("i_da", "red"), ("i_aa", "yellow")):
            rate, durations = fitted.get(ROLE_TO_BG[role]), burst_durations_ms(table, detector)
            if rate is not None and durations is not None:
                per_burst[role] = np.clip(rate * durations, 0.0, None)
        rates = dict(fitted)
    result = run(int(opts.get("n_bootstrap", 50)), "pass 2 of 2: " if background == "fit" else "")
    return finish(result, start=start, kept=kept, constants=constants, opts=opts,
                  mapping=mapping, counts=counts, tau_f=tau_f, line=line, rates=rates,
                  per_burst=per_burst, fitted=fitted, notes=notes, background=background)
