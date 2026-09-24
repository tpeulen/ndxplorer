"""Turn a ``tttrlib.auto_calibrate`` result into ndX's calibration contract.

The second half of :func:`ndxplorer.analysis.fret_backend.calibrate_columns`:
which factors are written and which are held, the accurate per-burst columns,
the species-specific factors as vector constants, and the report.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping

import numpy as np
import tttrlib

__all__ = ["finish", "species_vectors", "force_species", "vector_labels"]


def species_vectors(species, new_columns: Dict[str, np.ndarray],
                    injected: List[str]) -> Dict[str, dict]:
    """Per-population factors as ndX vector constants (``set_vector`` arguments).

    Only factors that are not pooled become vectors -- gamma, when the species
    model lowered the BIC. Their axis is the ``Population`` column (FRET
    population ``s`` coded ``s``) and one ``P(<name>)`` column per population
    holding each burst's assignment probability; both are added here.
    """
    if not species:
        return {}
    names = list(species["names"])
    vectors: Dict[str, dict] = {}
    for factor, entry in species["factors"].items():
        if entry.get("pooled", True):
            continue
        if not vectors:
            assignment = np.asarray(species["assignment"], dtype=float)
            for s, name in enumerate(names):
                new_columns[f"P({name})"] = assignment[:, s]
                injected.append(f"P({name})")
        vectors[factor] = {
            "values": [float(v) for v in entry["values"]],
            "populations": names,
            "uncertainties": [float(v) for v in entry["sigma"]],
            "default": float(entry["global"]),
            "column": "Population",
            "codes": {name: float(s) for s, name in enumerate(names)},
            "probabilities": {name: f"P({name})" for name in names},
        }
    return vectors


def force_species(species: Mapping[str, Any], counts, factors: Mapping[str, float]) -> dict:
    """*species* with the per-population gamma adopted although the BIC kept the shared one.

    What "population-wise factors: on" means: whenever the species model was
    fitted (it is identifiable), its gammas and beta are used. The per-burst
    ``E``/``S`` are recomputed as tttrlib does for an adopted species model --
    each FRET burst corrected with its populations' gammas weighted by its
    assignment probabilities, every other burst with the global factors.
    A species model that was not fitted (not identifiable) is returned as it is.
    """
    ms = dict(species.get("model_selection") or {})
    gammas = [float(g) for g in ms.get("gamma_species") or []]
    if not ms.get("identifiable") or not gammas or ms.get("selected") == "species":
        return dict(species)
    beta = float(ms.get("beta_species", factors["beta"]))
    sigmas = [float(v) for v in ms.get("sigma_gamma_species") or [float("nan")] * len(gammas)]
    f_dd = counts("i_dd") - factors.get("bg_dd", 0.0)
    f_aa = counts("i_aa") - factors.get("bg_aa", 0.0)
    f_da = (counts("i_da") - factors.get("bg_da", 0.0)) - factors["alpha"] * f_dd \
        - factors["delta"] * f_aa

    def e_of(g):
        den = f_da + g * f_dd
        return np.where(den > 0, f_da / np.where(den > 0, den, 1.0), 0.0)

    def s_of(g):
        num = g * f_dd + f_da
        den = num + f_aa / beta
        return np.where(den != 0, num / np.where(den != 0, den, 1.0), 0.0)

    p = np.asarray(species["assignment"], dtype=float)
    rest = np.clip(1.0 - p.sum(axis=1), 0.0, None)
    g0 = float(factors["gamma"])
    e = rest * e_of(g0) + sum(p[:, s] * e_of(g) for s, g in enumerate(gammas))
    s_ = rest * s_of(g0) + sum(p[:, s] * s_of(g) for s, g in enumerate(gammas))
    out = dict(species)
    out["factors"] = dict(species["factors"])
    out["factors"]["gamma"] = dict(species["factors"]["gamma"], values=gammas, sigma=sigmas,
                                   pooled=False)
    out["factors"]["beta"] = dict(species["factors"]["beta"], values=[beta] * len(gammas))
    out["E"], out["S"] = e, s_
    out["model_selection"] = dict(ms, forced=True)
    return out


def vector_labels(vectors: Mapping[str, Mapping[str, Any]]) -> List[str]:
    """``gamma[FRET 1]``… -- the vector constants' elements as the Parameters tab lists them."""
    return [f"{name}[{population}]" for name, vector in dict(vectors or {}).items()
            for population in vector.get("populations") or []]


def finish(result: Mapping[str, Any], *, start, kept, constants, opts, mapping, counts,
           tau_f, line, rates, per_burst, fitted, notes, background,
           species_mode: str = "auto", dimensions=(), population_method: str = "gmm") -> dict:
    """Assemble the contract's result dict (see ``fret_calibration.calibrate``)."""
    from .fret_backend import FACTOR_NAMES, constants_from_factors

    factors = opts.get("factors")
    selected = list(FACTOR_NAMES) if factors is None else \
        [n for n in FACTOR_NAMES if n in set(factors)]
    determined = {n: float(start[n]) for n in FACTOR_NAMES}
    final = dict(start)
    for name in FACTOR_NAMES:
        if name not in selected:
            final[name] = kept[name]

    new_columns: Dict[str, np.ndarray] = {}
    injected: List[str] = []
    vectors: Dict[str, dict] = {}
    species = None if species_mode == "off" else result.get("species")
    if species and species_mode == "on":
        species = force_species(species, counts, start)
    if species and "gamma" not in selected:
        # gamma is held at the window's value: population-wise gammas would
        # replace it in every FRET burst, so none are written either
        species = dict(species, model_selection=dict(species.get("model_selection") or {},
                                                      held=True))
    write_vectors = bool(species) and "gamma" in selected
    if opts.get("inject_columns", True):
        split = result["split"]
        labels = np.where(split["fret"], split["fret_labels"], -1)
        labels = np.where(split["acceptor_only"], -2, labels)
        accurate = tttrlib.accurate_fret(
            counts("i_dd"), counts("i_da"), counts("i_aa"), factors=final,
            uncertainties=result["uncertainties"], tau_f=tau_f, line=line, labels=labels)
        new_columns["FRET efficiency (accurate)"] = np.asarray(accurate["E"], dtype=float)
        if accurate["S"] is not None:
            new_columns["Stoichiometry (accurate)"] = np.asarray(accurate["S"], dtype=float)
        new_columns["R_DA (accurate)"] = np.asarray(accurate["distance"], dtype=float)
        new_columns["Population"] = labels.astype(float)
        if accurate["deviation"] is not None:
            new_columns["Off static FRET line"] = np.asarray(accurate["deviation"], dtype=float)
        injected = list(new_columns)
        vectors = species_vectors(species, new_columns, injected) if write_vectors else {}
        if "gamma" in vectors:
            # the species model won: the accurate columns use each burst's gamma
            new_columns["FRET efficiency (accurate)"] = np.asarray(species["E"], dtype=float)
            if accurate["S"] is not None:
                new_columns["Stoichiometry (accurate)"] = np.asarray(species["S"], dtype=float)

    # ndX's Bg/Br/By are rates: push the ones the per-burst subtraction used
    for attribute, value in rates.items():
        final[attribute] = float(value)
    applied = constants_from_factors(final)
    report = tttrlib.calibration_report(result)
    if notes:
        report += "\n" + "\n".join(f"  ! {note}" for note in notes)
    return {
        "ok": True,
        "constants": applied,
        "before": {k: constants.get(k) for k in applied},
        "factors": dict(result["factors"]),
        "uncertainties": dict(result["uncertainties"]),
        "report": report,
        "notes": list(notes),
        "columns": dict(mapping),
        "injected": injected,
        "new_columns": new_columns,
        "populations": list(result["populations"]),
        "species": None if not species else {
            k: species[k] for k in ("labels", "names", "populations", "factors",
                                    "model_selection")},
        "vectors": vectors,
        "vector_labels": vector_labels(vectors),
        "species_mode": species_mode,
        "dimensions": list(dimensions),
        "population_method": str(population_method),
        "model_selection": None if not species else dict(species.get("model_selection") or {}),
        "determined": determined,
        "applied_factors": selected,
        "background": background,
        "background_per_burst": sorted(per_burst),
        "background_fitted": dict(fitted),
        "held": {n: kept[n] for n in FACTOR_NAMES if n not in selected},
    }
