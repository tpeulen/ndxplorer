"""Turn a ``tttrlib.auto_calibrate`` result into ndX's calibration contract.

The second half of :func:`ndxplorer.analysis.fret_backend.calibrate_columns`:
which factors are written and which are held, the accurate per-burst columns,
the species-specific factors as vector constants, and the report.
"""
from __future__ import annotations

from typing import Any, Dict, List, Mapping

import numpy as np
import tttrlib

__all__ = ["finish", "species_vectors"]


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


def finish(result: Mapping[str, Any], *, start, kept, constants, opts, mapping, counts,
           tau_f, line, rates, per_burst, fitted, notes, background) -> dict:
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
    species = result.get("species")
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
        vectors = species_vectors(species, new_columns, injected)
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
        "determined": determined,
        "applied_factors": selected,
        "background": background,
        "background_per_burst": sorted(per_burst),
        "background_fitted": dict(fitted),
        "held": {n: kept[n] for n in FACTOR_NAMES if n not in selected},
    }
