"""Accurate-FRET calibration of the loaded bursts: options, backend contract, report.

The calibration determines ndX's correction constants (γ, α, β, δ, the
backgrounds) from the measurement in the window rather than from typed-in
guesses, and adds the accurate per-burst columns. What is here is what both
windows need and neither should hold twice:

* :class:`CalibrationOptions` -- what the calibration may write, and how
  (``fret_calibration_options.view.json`` beside this module is its form, drawn
  by AutoForm in the Qt window and by :mod:`emtk.view_form` in the emtk app);
* the **backend contract**, :func:`calibrate`: burst columns and constants in,
  a result dict out. The window does the applying (see :func:`apply_result`),
  the backend only computes, so a window never hands its internals to the
  algorithm;
* :func:`report_text`, the report a finished calibration is read in.

The algorithm itself is not here. It lives in a compiled library shared with
ChiSurf; until that library is wired in, :func:`backend` returns ``None`` and
the windows say why the calibration cannot run. :func:`set_backend` installs
one (a test's, or the library's).

Nothing here imports Qt or chisurf.
"""

from __future__ import annotations

import json
import logging
import pathlib
from typing import Any, Callable, Dict, List, Mapping, Optional

import numpy as np

__all__ = [
    "CalibrationOptions",
    "FACTOR_ATTRS",
    "FACTOR_NAMES",
    "OPTIONS_SPEC",
    "Backend",
    "backend",
    "set_backend",
    "unavailable_reason",
    "calibrate",
    "burst_columns",
    "apply_result",
    "report_text",
]

logger = logging.getLogger(__name__)

#: The options' form (an AutoForm view spec).
OPTIONS_SPEC = pathlib.Path(__file__).with_name("fret_calibration_options.view.json")

#: The Hellenkamp correction factors a calibration can write, in the order the
#: paper introduces them. ``r0`` is not a correction but travels with them,
#: because the distances depend on it.
FACTOR_NAMES = ("alpha", "beta", "gamma", "delta", "r0")

#: Factor name -> the option attribute holding whether it is applied.
FACTOR_ATTRS = {
    "alpha": "fit_alpha",
    "delta": "fit_delta",
    "gamma": "fit_gamma",
    "beta": "fit_beta",
    "r0": "fit_r0",
}


class CalibrationOptions:
    """The settings of one calibration run.

    The factors are a choice, and so is the route γ comes from. γ from a
    measurement's own populations is only as good as those populations, and
    somebody who determined γ properly on a reference sample wants α and δ
    fitted *around* it rather than replaced by a worse estimate. The
    calibration is still run in full whatever is chosen -- the report says
    what every factor came out as -- but only the selected ones are written.

    Parameters
    ----------
    donor_lifetime : float
        τ_D(0) in ns, normally the window's ``tauD0``.
    """

    def __init__(self, donor_lifetime: float = 4.0) -> None:
        #: Leakage of donor emission into the acceptor channel.
        self.fit_alpha: bool = True
        #: Direct excitation of the acceptor by the donor laser.
        self.fit_delta: bool = True
        #: Detection efficiency x quantum yield ratio.
        self.fit_gamma: bool = True
        #: Excitation flux / cross-section ratio of the two lasers.
        self.fit_beta: bool = True
        #: Förster radius. Not a correction factor; the distances depend on it.
        self.fit_r0: bool = False
        #: Where the channel backgrounds come from -- including fitting them.
        self.background: str = "fit"
        #: Smallest reference population accepted when fitting a background.
        self.min_population: int = 20
        #: Which route γ comes from.
        self.gamma_source: str = "auto"
        #: Combine the data estimates with the light-path priors.
        self.use_priors: bool = True
        #: Bootstrap resamples for the factor uncertainties (0 skips them).
        self.n_bootstrap: int = 50
        #: Donor-only lifetime τ_D(0), ns -- shapes the static FRET line.
        self.donor_lifetime: float = float(donor_lifetime)
        #: Linker width, Å.
        self.linker_sigma: float = 6.0
        #: Also add the accurate per-burst E / S / R_DA columns.
        self.inject_columns: bool = True
        #: Store the result in the measurement when it finishes. On by default
        #: and into the `.pto` container by default: a calibration determined
        #: from a measurement belongs beside that measurement's photons and
        #: burst table, not in a file next to it that a later copy leaves
        #: behind. Off writes nothing; the report window can still save.
        self.save_when_done: bool = True

    @staticmethod
    def spec() -> dict:
        """The options' view spec, parsed."""
        with open(OPTIONS_SPEC, encoding="utf-8") as handle:
            return json.load(handle)

    def factors(self) -> List[str]:
        """The factors the calibration may write, in the paper's order."""
        return [name for name, attr in FACTOR_ATTRS.items() if getattr(self, attr)]

    def as_kwargs(self) -> dict:
        """The options as keyword arguments of a calibration run."""
        return {
            "factors": self.factors(),
            "background": str(self.background),
            "min_population": int(self.min_population),
            "gamma_source": str(self.gamma_source),
            "use_priors": bool(self.use_priors),
            "n_bootstrap": int(self.n_bootstrap),
            "donor_lifetime": float(self.donor_lifetime),
            "linker_sigma": float(self.linker_sigma),
            "inject_columns": bool(self.inject_columns),
        }

    def save_requested(self) -> bool:
        """Whether the finished calibration should be stored automatically."""
        return bool(self.save_when_done)


# ------------------------------------------------------------------ backend
#: ``backend(columns, constants, options, *, container="", progress=None) -> dict``.
Backend = Callable[..., dict]

_BACKEND: Dict[str, Any] = {"fn": None}

#: Why no calibration can run, when no backend is installed.
NO_BACKEND = ("Accurate FRET needs ChiSurf's FRET calibration, which could not be "
              "imported here.")


def set_backend(fn: Optional[Backend]) -> None:
    """Install the function that computes a calibration (``None`` removes it)."""
    _BACKEND["fn"] = fn


def backend() -> Optional[Backend]:
    """The installed backend: the one :func:`set_backend` put in, else ChiSurf's
    calibration when ChiSurf is importable, else ``None``."""
    if _BACKEND["fn"] is None:
        try:
            from chisurf.plugins.ndxplorer.calibration_bridge import calibrate_columns
        except Exception:  # noqa: BLE001 - no ChiSurf: the windows say why
            logger.warning("no FRET calibration backend: ChiSurf's calibration "
                           "could not be imported", exc_info=True)
            return None
        _BACKEND["fn"] = calibrate_columns
    return _BACKEND["fn"]


def unavailable_reason() -> str:
    """Why a calibration cannot run here, or ``""`` when it can."""
    return "" if backend() is not None else NO_BACKEND


def calibrate(columns: Mapping[str, np.ndarray], constants: Mapping[str, float],
              options: CalibrationOptions, *, container: str = "",
              progress: Optional[Callable[[int, int, str], bool]] = None) -> dict:
    """Determine the correction constants from the loaded bursts.

    The contract every backend keeps, and the only thing a window calls.

    Parameters
    ----------
    columns : mapping of str to ndarray
        The burst table's numeric columns (:func:`burst_columns`). The
        backend recognises the channels itself (``Number of Photons
        (green)``…).
    constants : mapping of str to float
        The window's constants as they stand: the starting point, and what
        every factor the options hold keeps.
    options : CalibrationOptions
        What may be written, and how.
    container : str, optional
        The `.pto` the bursts came from, for ``background="measurement"``.
    progress : callable, optional
        ``progress(step, total, message) -> bool``; ``False`` stops the run.

    Returns
    -------
    dict
        ``{"ok": False, "error": str}``, or ``{"ok": True, ...}`` with

        ``constants``
            ndX constant name -> value, what the window is to hold;
        ``before``
            the same names -> the value the window held;
        ``new_columns``
            column name -> per-burst array, the accurate columns to add
            (empty when ``options.inject_columns`` is off);
        ``injected``
            their names, in order;
        ``factors``, ``uncertainties``
            every factor as determined, and its standard error;
        ``determined``, ``held``, ``applied_factors``
            what each factor came out as, which ones were held at the
            window's value, and which were written;
        ``populations``
            one dict per FRET population (``label``, ``n``, ``E``,
            ``sigma_E``, ``S``, ``distance``…);
        ``background``, ``background_fitted``, ``background_per_burst``
            where the backgrounds came from;
        ``columns``
            which burst column each channel role was read from;
        ``report``
            the calibration's own text.
    """
    fn = backend()
    if fn is None:
        return {"ok": False, "error": NO_BACKEND}
    try:
        result = fn(dict(columns), dict(constants), options, container=container,
                    progress=progress)
    except Exception as exc:  # noqa: BLE001 - reported, the window goes on
        logger.exception("the FRET calibration failed")
        return {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
    result = dict(result or {})
    result.setdefault("ok", False)
    if result["ok"]:
        result.setdefault("new_columns", {})
        result.setdefault("injected", list(result["new_columns"]))
    return result


def burst_columns(data_source) -> Dict[str, np.ndarray]:
    """The numeric columns of a data source, as ``{name: float array}``.

    A column holding no finite value (a text column reads as all NaN) is left
    out.
    """
    if data_source is None:
        return {}
    columns: Dict[str, np.ndarray] = {}
    for name in data_source.parameter_names:
        values = data_source.column_values(name)
        if values is not None and values.size and np.any(np.isfinite(values)):
            columns[str(name)] = np.asarray(values, dtype=float)
    return columns


def apply_result(result: Mapping[str, Any], *, write_constants: Callable[[dict], None],
                 data_source=None) -> List[str]:
    """Write a successful result into a window: constants, then the new columns.

    The window says how its constants are written (*write_constants*: the Qt
    window's parameter table, the emtk app's constants mapping); the columns
    go into its :class:`~ndxplorer.core.data_source.DataSource`.

    Returns
    -------
    list of str
        The columns added.
    """
    added: List[str] = []
    if data_source is not None:
        for name, values in dict(result.get("new_columns") or {}).items():
            data_source.set_column(str(name), np.asarray(values, dtype=float))
            added.append(str(name))
    constants = {str(k): float(v) for k, v in dict(result.get("constants") or {}).items()}
    if constants:
        write_constants(constants)
    return added


# ------------------------------------------------------------------- report
def report_text(result: Mapping[str, Any]) -> str:
    """The whole report of a finished calibration, as the report window shows it.

    The calibration's own text, then the constants before -> after, what was
    held fixed (and what this measurement would have given), where the
    backgrounds came from, and the columns added.
    """
    before = dict(result.get("before") or {})
    lines = [str(result.get("report") or ""), "", "ndX constants:"]
    lines += [
        f"  {name}: {before.get(name)!s} → {float(value):.4f}"
        for name, value in dict(result.get("constants") or {}).items()
    ]
    # What was deliberately not written, and what it would have been. A factor
    # held fixed is a decision, and the number it was held against is the only
    # way to judge whether it was a good one.
    held = dict(result.get("held") or {})
    if held:
        determined = dict(result.get("determined") or {})
        lines += ["", "Held fixed (not calibrated):"]
        lines += [
            f"  {name}: kept {float(value):.4f}"
            + (f" — this measurement would have given {float(determined[name]):.4f}"
               if name in determined else "")
            for name, value in held.items()
        ]
    per_burst = list(result.get("background_per_burst") or [])
    fitted = dict(result.get("background_fitted") or {})
    source = result.get("background")
    if source == "fit":
        lines += [
            "",
            ("Background, fitted from the reference populations: "
             + ", ".join(f"{k} = {float(v):.2f}" for k, v in fitted.items()))
            if fitted else
            ("Background: the reference populations were too small to fit one — the "
             "window's constants were used"),
        ]
    elif source == "measurement":
        lines += [
            "",
            (f"Background: per burst, from this measurement's own estimate "
             f"({', '.join(per_burst)})")
            if per_burst else
            ("Background: the container has no stored estimate — the window's own "
             "constants were used"),
        ]
    elif source == "none":
        lines += ["", "Background: none (set to zero)"]
    if result.get("injected"):
        lines += ["", "New columns: " + ", ".join(result["injected"])]
    return "\n".join(lines)
