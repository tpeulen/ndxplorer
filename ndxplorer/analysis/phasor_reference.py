"""The phasor of an instrument response (reference) and of a background, with tttrlib.

ndX corrects the phasor columns of a table by equations (``g corr``, ``s corr``
in ``settings/mfd.equations.yaml``) in tttrlib's form: the background is
taken out, then the phasor is divided by the instrument response phasor
(``DecayPhasor::g`` / ``DecayPhasor::s``). The constants those equations read
are determined here from measurements:

* :func:`reference_phasor` -- ``g_irf``, ``s_irf`` from an IRF (scatter,
  mirror) measurement, or from a reference dye of known lifetime ``tau_ref``;
* :func:`background_per_row` -- ``n_bg``: the background photons of the
  measurement a pixel table was made from, per pixel and frame.

The phasor is tttrlib's: ``DecayPhasor.phasor_of_bincounts`` of the micro-time
histogram at ``frequency`` = f_rep * harmonic * micro-time resolution (cycles
per channel, the phase of channel *k* is 2 pi frequency k), which is what
``CLSMImage.get_phasor`` computes the pixel phasors at. A flat background is
subtracted from a histogram as tttrlib subtracts one (``compute_phasor_bincounts``
takes background-subtracted counts); by linearity that is
``(N z - N_bg z_flat) / (N - N_bg)``, computed from the two phasors so the
fractional background level is not rounded to integer counts.

Nothing here imports Qt or ChiSurf.
"""
from __future__ import annotations

from typing import Dict, Iterable, Optional, Sequence

import numpy as np

__all__ = ["phasor_frequency", "flat_level", "histogram_phasor", "microtime_histogram",
           "reference_phasor", "background_per_row", "image_rows"]


def phasor_frequency(f_rep_mhz: float, harmonic: float, micro_time_resolution_s: float) -> float:
    """tttrlib's ``frequency`` argument: cycles per micro-time channel."""
    return float(f_rep_mhz) * 1e6 * float(harmonic) * float(micro_time_resolution_s)


def flat_level(counts: np.ndarray, n_coarse: int = 64) -> float:
    """The flat (background) level of a decay histogram, in counts per channel.

    The histogram is summed into *n_coarse* wide bins; the level is the mean of
    the bins between the 10th and the 40th percentile. An IRF or a decay covers
    few of them, the dark counts, afterpulsing and scattered light all of them.
    """
    counts = np.asarray(counts, dtype=float)
    width = max(1, counts.size // n_coarse)
    n = (counts.size // width) * width
    coarse = np.sort(counts[:n].reshape(-1, width).sum(axis=1))
    lo, hi = int(0.1 * coarse.size), max(int(0.4 * coarse.size), int(0.1 * coarse.size) + 1)
    return float(coarse[lo:hi].mean() / width)


def histogram_phasor(counts: np.ndarray, frequency: float,
                     background: float = 0.0) -> Dict[str, float]:
    """The phasor of a micro-time histogram, a flat *background* (counts per channel) removed.

    Returns ``{"g", "s", "n", "n_bg"}``.
    """
    import tttrlib

    counts = np.asarray(counts)
    phasor = tttrlib.DecayPhasor.phasor_of_bincounts
    g, s = phasor(np.ascontiguousarray(counts, dtype=np.int32), float(frequency), 0, 1.0, 0.0)
    n = float(counts.sum())
    n_bg = float(background) * counts.size
    if n_bg > 0.0:
        gu, su = phasor(np.ones(counts.size, dtype=np.int32), float(frequency), 0, 1.0, 0.0)
        g = (n * g - n_bg * gu) / (n - n_bg)
        s = (n * s - n_bg * su) / (n - n_bg)
    return {"g": float(g), "s": float(s), "n": n, "n_bg": n_bg}


def microtime_histogram(tttr, channels: Iterable[int]) -> np.ndarray:
    """Counts per micro-time channel of the photons of the routing *channels*.

    The histogram spans the channels that are used (up to the last photon), so a
    flat background is flat over the whole of it.
    """
    micro = np.asarray(tttr.micro_times)
    keep = np.isin(np.asarray(tttr.routing_channels), list(channels))
    micro = micro[keep]
    if micro.size == 0:
        return np.zeros(0, dtype=np.int64)
    return np.bincount(micro, minlength=int(micro.max()) + 1)


def reference_phasor(path: str, channels: Sequence[int], f_rep_mhz: float, harmonic: float = 1.0,
                     tau_ref: float = 0.0, subtract_background: bool = True) -> Dict[str, float]:
    """``g_irf``, ``s_irf`` of the photons of *channels* in the TTTR file *path*.

    Parameters
    ----------
    tau_ref : float
        0 for an instrument response (scatter, mirror). A reference dye of
        known lifetime (ns) instead: its phasor on the universal circle is
        divided out, z_irf = z_ref (1 - i omega tau_ref) (the phasorpy
        calibration tttrlib's phasor is validated against).
    subtract_background : bool
        Remove the reference's flat background (dark counts, afterpulsing)
        before the phasor: it pulls the reference toward (0, 0) and would scale
        every corrected phasor up.

    Returns
    -------
    dict
        ``g_irf``, ``s_irf``, ``g_raw``, ``s_raw`` (no background removed),
        ``n`` photons, ``f_bg`` (the reference's background fraction),
        ``frequency`` (cycles per channel) and ``f_rep_header`` (MHz, from the
        file's macro-time resolution, to compare with the constant).
    """
    import tttrlib

    tttr = tttrlib.TTTR(str(path))
    header = tttr.header
    frequency = phasor_frequency(f_rep_mhz, harmonic, header.micro_time_resolution)
    counts = microtime_histogram(tttr, channels)
    if counts.sum() < 10:
        raise ValueError(f"{path}: fewer than 10 photons in channels {list(channels)}")
    raw = histogram_phasor(counts, frequency)
    level = flat_level(counts) if subtract_background else 0.0
    ref = histogram_phasor(counts, frequency, level)
    if ref["n_bg"] > 0.5 * ref["n"]:
        # A detector that saw no reflection: what is left is dark counts, and
        # its "phasor" is noise divided by a small number.
        raise ValueError(f"{path}: channels {list(channels)} hold no instrument response "
                         f"({100 * ref['n_bg'] / ref['n']:.0f} % of the photons are flat "
                         "background)")
    z = complex(ref["g"], ref["s"])
    if tau_ref:
        z *= complex(1.0, -2.0 * np.pi * f_rep_mhz * harmonic * 1e-3 * float(tau_ref))
    macro = float(header.macro_time_resolution)
    return {"g_irf": z.real, "s_irf": z.imag, "g_raw": raw["g"], "s_raw": raw["s"],
            "n": ref["n"], "f_bg": ref["n_bg"] / ref["n"], "frequency": frequency,
            "f_rep_header": (1e-6 / macro) if macro > 0 else float("nan")}


def image_rows(columns: Sequence[str], column_values) -> Optional[int]:
    """Pixels x lines x frames of a pixel table, or ``None`` when it is not one.

    *column_values(name)* returns a column. A pixel table has ``x pixel``,
    ``y pixel`` and (optionally) ``Frame`` columns.
    """
    lower = {str(c).lower(): c for c in columns}
    if "x pixel" not in lower or "y pixel" not in lower:
        return None
    n = 1
    for name in ("x pixel", "y pixel", "frame"):
        if name in lower:
            values = np.asarray(column_values(lower[name]), dtype=float)
            values = values[np.isfinite(values)]
            n *= int(values.max()) + 1 if values.size else 1
    return n


def background_per_row(path: str, channels: Sequence[int], n_rows: int,
                       table_photons: float) -> Dict[str, float]:
    """``n_bg``: the flat background photons of a measurement per table row.

    The background *fraction* of the micro-time histogram of *channels* (its
    flat level times the channels, over all photons) applied to the photons
    the table holds (*table_photons*, the sum of its count column) and spread
    evenly over its *n_rows* pixels x frames -- what a pixel collects in dark
    counts and uncorrelated background at a constant dwell time. Taking the
    fraction rather than the count keeps it right for a table made from some
    of the frames. Returns ``{"n_bg", "f_bg", "n"}``.
    """
    import tttrlib

    counts = microtime_histogram(tttrlib.TTTR(str(path)), channels)
    n = float(counts.sum())
    f_bg = flat_level(counts) * counts.size / n if n else float("nan")
    return {"n_bg": f_bg * float(table_photons) / max(int(n_rows), 1), "f_bg": f_bg, "n": n}
