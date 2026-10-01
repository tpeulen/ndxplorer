"""FRET > Phasor reference from IRF…: the constants of the corrected phasor, from measurements.

The phasor columns of a table (``g``, ``s`` per channel) are referenced to the
instrument and cleared of background by the equations ``g corr`` / ``s corr``
(``settings/mfd.equations.yaml``, tttrlib's ``DecayPhasor`` form). This dialog
fills their constants from TTTR files with tttrlib
(:mod:`ndxplorer.analysis.phasor_reference`):

* ``g_irf``, ``s_irf`` per channel from an IRF (scatter, mirror) measurement,
  or from a reference dye of known lifetime;
* ``n_bg`` per channel from the measurement a *pixel* table was made from: its
  flat background spread over pixels x lines x frames.

Nothing is written until Apply; the values then go into the window's
constants, and every equation reading them recomputes.
"""

from __future__ import annotations

import json
import logging
import pathlib
from typing import Any, Callable, Dict, List, Optional

from . import Feature

__all__ = ["PhasorReferenceFeature", "create"]

logger = logging.getLogger(__name__)

SPEC = pathlib.Path(__file__).with_name("phasor_reference") / "reference.view.json"
TTTR_FILTERS = [("TTTR files", ["*.ptu", "*.ht3", "*.spc", "*.hdf5", "*.h5", "*.bin"]),
                ("All files", ["*"])]
#: dialog attribute -> the constants' channel suffix.
CHANNELS = {"green_channels": " (green)", "red_channels": " (red)", "plain_channels": ""}


def parse_channels(text: str) -> List[int]:
    return [int(t) for t in str(text).replace(",", " ").split()]


class ReferenceDialog:
    """The dialog: files, channels, tau_ref; Compute shows the constants, Apply writes them."""

    modal = False

    def __init__(self, feature: "PhasorReferenceFeature") -> None:
        from emtk.dialog_window import DialogWindow
        from emtk.view_form import FormState

        self.feature = feature
        self.window = DialogWindow("Phasor reference from IRF", size=(560.0, 470.0),
                                   key="phasor-reference")
        self.window.show()
        self.form = FormState()
        self.done = False
        self.irf_file = ""
        self.measurement_file = ""
        self.green_channels = "0 1"
        self.red_channels = ""
        self.plain_channels = ""
        self.tau_ref = 0.0
        self.subtract_background = True
        self.values: Dict[str, float] = {}
        self.notes: List[str] = []

    def spec(self) -> dict:
        return json.loads(SPEC.read_text(encoding="utf-8"))

    def enabled(self, name: str) -> bool:
        if name == "apply":
            return bool(self.values)
        if name == "compute":
            return bool(self.irf_file.strip() or self.measurement_file.strip())
        return True

    def draw(self, frame) -> None:
        from emtk.view_form import draw_form

        pressed = self.window.begin(frame)
        try:
            draw_form(self.spec(), self, self.form, titles=False)
        finally:
            self.window.end()
        if pressed == "close":
            self.cancel()

    @property
    def result_text(self) -> str:
        rows = [f"{name} = {value:.6g}" for name, value in self.values.items()]
        return "\n".join(rows + self.notes) or "Choose an IRF (and a measurement), then Compute."

    def choose_irf(self) -> None:
        self.feature.ask_open("IRF / reference measurement", lambda p: setattr(self, "irf_file", p))

    def choose_measurement(self) -> None:
        self.feature.ask_open("Measurement", lambda p: setattr(self, "measurement_file", p))

    def compute(self) -> None:
        from ...analysis import phasor_reference as ref

        constants = self.feature.constants()
        f_rep = float(constants.get("f_rep", 80.0))
        harmonic = float(constants.get("harmonic", 1.0))
        rows = self.feature.image_rows()
        self.values, self.notes = {}, []
        for attr, suffix in CHANNELS.items():
            try:
                channels = parse_channels(getattr(self, attr))
            except ValueError:
                self.notes.append(f"{attr.split('_')[0]}: channels are numbers, e.g. 0 1")
                continue
            if not channels:
                continue
            try:
                if self.irf_file.strip():
                    r = ref.reference_phasor(self.irf_file.strip(), channels, f_rep, harmonic,
                                             float(self.tau_ref or 0.0),
                                             bool(self.subtract_background))
                    self.values[f"g_irf{suffix}"] = r["g_irf"]
                    self.values[f"s_irf{suffix}"] = r["s_irf"]
                    self.notes.append(
                        f"IRF{suffix or ''}: {r['n']:.0f} photons, {100 * r['f_bg']:.1f} % flat "
                        f"background removed; the file's f_rep is {r['f_rep_header']:.3f} MHz "
                        f"(constant f_rep {f_rep:g})")
                if self.measurement_file.strip():
                    if rows is None:
                        self.notes.append("n_bg: the table is not a pixel table (no x pixel, "
                                          "y pixel); set n_bg or edit the f_bg equation")
                    else:
                        photons = self.feature.table_photons(f"Number of Photons{suffix}")
                        b = ref.background_per_row(self.measurement_file.strip(), channels,
                                                   rows, photons)
                        self.values[f"n_bg{suffix}"] = b["n_bg"]
                        self.notes.append(f"background{suffix}: {100 * b['f_bg']:.1f} % of the "
                                          f"photons, over {rows} pixels x frames")
            except Exception as exc:  # noqa: BLE001 - shown in the dialog
                self.notes.append(str(exc))

    def apply(self) -> None:
        if self.values:
            self.feature.write_constants(dict(self.values))
            self.feature.app.show_status("Phasor reference: set " + ", ".join(self.values))
        self.cancel()

    def cancel(self) -> None:
        self.done = True
        self.window.hide()


class PhasorReferenceFeature(Feature):
    """FRET > Phasor reference from IRF…"""

    name = "phasor_reference"

    def __init__(self, app) -> None:
        super().__init__(app)
        self.window: Optional[ReferenceDialog] = None
        #: capture replay: file answers given before the dialog asks.
        self._file_answers: List[str] = []

    def constants(self) -> dict:
        return dict(self.app.model.manager.constants or {})

    def image_rows(self) -> Optional[int]:
        from ...analysis.phasor_reference import image_rows

        model = self.app.model
        if not model.has_data:
            return None
        return image_rows(list(model.parameter_names), model.source.column_values)

    def table_photons(self, column: str) -> float:
        """The sum of the count *column* of the table (0 when it has none)."""
        import numpy as np

        if column not in self.app.model.parameter_names:
            return 0.0
        values = np.asarray(self.app.model.source.column_values(column), dtype=float)
        return float(np.nansum(values))

    def write_constants(self, values: Dict[str, float]) -> None:
        """Into the window's constants (the Parameters tab's group when there is one)."""
        model = self.app.model
        constants = model.manager.constants
        update = getattr(constants, "update", None)
        if callable(update):
            update(dict(values))
        else:
            model.manager.constants = {**dict(constants or {}), **values}
        panel = next((getattr(f, "constants", None) for f in self.app.features
                      if callable(getattr(getattr(f, "constants", None), "poll", None))), None)
        if panel is not None:
            panel.poll()
        elif model.has_data:
            model.source.compute_columns(constants=model.manager.constants,
                                         equations=model.manager.equations)
        model.invalidate()

    def ask_open(self, title: str, callback: Callable[[str], None]) -> None:
        if self._file_answers:
            callback(self._file_answers.pop(0))
            return
        service = getattr(self.app, "io_service", None)
        if service is None:
            self.app.message = (title, "Opening files needs the io feature.")
            return
        service.ask_open(title, TTTR_FILTERS, lambda paths: callback(paths[0]))

    def open_dialog(self) -> ReferenceDialog:
        self.window = ReferenceDialog(self)
        return self.window

    # --------------------------------------------------------------- hooks
    def actions(self) -> Dict[str, Callable[[], Any]]:
        return {"phasor_reference": self.open_dialog}

    def available(self, action: str) -> Optional[bool]:
        if action == "phasor_reference":
            return self.app.model.has_data
        return None

    def menu_entries(self) -> List[tuple]:
        return [(("FRET",), None),
                (("FRET",), {"label": "Phasor reference from IRF…", "action": "phasor_reference",
                             "description": "Set g_irf, s_irf (and n_bg) of the corrected phasor "
                                            "columns from an IRF and the measurement."})]

    def draw_windows(self) -> bool:
        dialog = self.window
        if dialog is None:
            return False
        dialog.draw(self.app.box)
        if dialog.done and self.window is dialog:
            self.window = None
        return False


def create(app) -> PhasorReferenceFeature:
    return PhasorReferenceFeature(app)
