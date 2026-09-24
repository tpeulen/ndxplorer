"""Channel backgrounds for the accurate-FRET calibration: fitted or measured.

A background only ever enters the correction as ``counts - background``, and a
burst's background is a **rate** times its **duration** -- a 4 ms burst carries
four times the background of a 1 ms one. Both routes here therefore return
rates (kHz, what ndX's ``Bg``/``Br``/``By`` hold) and per-burst counts derived
from the burst durations.

* :func:`fitted_background` -- from the measurement's own reference
  populations, when nobody knows the background (most of the time);
* :func:`measured_background` -- the rates the background step stored in the
  ``.pto`` container. Reading the container needs ChiSurf's measurement
  reader; without ChiSurf this route returns nothing and says why.

Nothing here imports Qt, and ChiSurf only inside :func:`measured_background`.
"""
from __future__ import annotations

import logging
from typing import Dict, Mapping, Optional, Tuple

import numpy as np

__all__ = ["burst_durations_ms", "fitted_background", "measured_background",
           "BACKGROUND_ROLES", "ROLE_TO_BG"]

#: Detector name in a measurement's background artifact -> the channel role.
BACKGROUND_ROLES = {"green": "i_dd", "red": "i_da", "yellow": "i_aa"}

#: Channel role -> the calibration's background factor.
ROLE_TO_BG = {"i_dd": "bg_dd", "i_da": "bg_da", "i_aa": "bg_aa"}


def burst_durations_ms(table: Mapping[str, np.ndarray], detector: str):
    """That detector's per-burst durations in ms, else the burst's, else ``None``."""
    for name in (f"Duration ({detector}) (ms)", "Duration (ms)"):
        if name in table:
            return np.asarray(table[name], dtype=float)
    return None


def fitted_background(i_dd, i_da, i_aa, split, *, durations=None,
                      min_population: int = 20) -> Dict[str, float]:
    """Channel background **rates** (kHz) estimated from the reference populations.

    In an acceptor-only burst the donor channel measures only background
    (``bg_dd``); in a donor-only burst the acceptor-excitation channel does
    (``bg_aa``). ``bg_da`` comes from fitting ``I_DA = alpha I_DD + bg_da T``
    over the donor-only bursts: the duration is a regressor, which is what
    separates background from leakage. Medians of per-burst rates, because
    these populations are the ones the mixture is least sure of.

    Parameters
    ----------
    i_dd, i_da, i_aa : array_like
        Channel counts; ``i_aa`` may be ``None``.
    split : mapping
        The population split of a calibration (``donor_only``/``acceptor_only``
        boolean masks).
    durations : array_like, optional
        Per-burst durations in ms; without them nothing can be estimated.
    min_population : int
        Smallest population accepted; below it the channel is left out.

    Returns
    -------
    dict
        ``{"bg_dd", "bg_da", "bg_aa"}`` for the channels that could be
        estimated, never negative.
    """
    out: Dict[str, float] = {}
    if split is None or durations is None:
        return out
    get = (lambda k: split.get(k, [])) if isinstance(split, Mapping) else \
        (lambda k: getattr(split, k, []))
    dt = np.asarray(durations, dtype=float)
    donor_only = np.asarray(get("donor_only"), dtype=bool)
    acceptor_only = np.asarray(get("acceptor_only"), dtype=bool)
    dd = np.asarray(i_dd, dtype=float)
    da = np.asarray(i_da, dtype=float)
    aa = None if i_aa is None else np.asarray(i_aa, dtype=float)
    if dt.size != dd.size:
        return out

    def rate(counts, mask):
        good = mask & np.isfinite(counts) & np.isfinite(dt) & (dt > 0)
        if int(good.sum()) < min_population:
            return None
        return float(max(0.0, np.median(counts[good] / dt[good])))

    if acceptor_only.size == dd.size:
        value = rate(dd, acceptor_only)
        if value is not None:
            out["bg_dd"] = value
    if aa is not None and donor_only.size == aa.size:
        value = rate(aa, donor_only)
        if value is not None:
            out["bg_aa"] = value
    if donor_only.size == dd.size and int(donor_only.sum()) >= min_population:
        x, y, t = dd[donor_only], da[donor_only], dt[donor_only]
        finite = np.isfinite(x) & np.isfinite(y) & np.isfinite(t) & (t > 0)
        if int(finite.sum()) >= min_population and np.ptp(x[finite]) > 0 and np.ptp(t[finite]) > 0:
            design = np.column_stack([x[finite], t[finite]])
            solution, *_ = np.linalg.lstsq(design, y[finite], rcond=None)
            out["bg_da"] = float(max(0.0, solution[1]))
    return out


def measured_background(table: Mapping[str, np.ndarray],
                        container: str) -> Tuple[Dict[str, np.ndarray], Dict[str, float], str]:
    """Per-burst background counts from the rates stored in the measurement.

    Returns
    -------
    tuple
        ``(counts, rates, note)``: ``{role: per-burst counts}``,
        ``{"bg_dd"|"bg_da"|"bg_aa": kHz}``, and a note saying why nothing was
        read (empty when something was).
    """
    if not container:
        return {}, {}, "the bursts carry no container, so no measured background"
    try:
        from chisurf.core.fio.pto import Measurement
    except Exception:  # noqa: BLE001 - ChiSurf is optional here
        return {}, {}, ("the measured background needs ChiSurf's container reader, "
                        "which is not available; no background was subtracted")
    rates: Dict[str, float] = {}
    try:
        with Measurement.open(container, writable=False) as measurement:
            for obj in reversed(list(measurement.artifacts())):
                if getattr(obj, "name", "") != "background":
                    continue
                try:
                    store = measurement.get_store(obj.uid)
                except Exception:  # noqa: BLE001 - not a dstore artifact
                    continue
                names = [store.column(i).name() for i in range(store.n_columns())]
                if "Detector" not in names or "Rate" not in names:
                    continue
                detectors = store.column(names.index("Detector"))
                values = np.asarray(store.column(names.index("Rate")).numpy(), dtype=float)
                for row in range(store.n_rows()):
                    rates[str(detectors.string_at(row)).lower()] = float(values[row])
                break
    except Exception:  # noqa: BLE001
        logging.debug("could not read a background from %s", container, exc_info=True)
        return {}, {}, f"could not read a background from {container}"
    if not rates:
        return {}, {}, "the measurement stores no background"
    counts: Dict[str, np.ndarray] = {}
    out_rates: Dict[str, float] = {}
    for detector, role in BACKGROUND_ROLES.items():
        value: Optional[float] = rates.get(detector)
        durations = burst_durations_ms(table, detector)
        if value is None or durations is None or not np.isfinite(value):
            continue
        counts[role] = np.clip(value * durations, 0.0, None)  # kHz x ms = counts
        out_rates[ROLE_TO_BG[role]] = float(value)
    return counts, out_rates, ""
