"""Accurate FRET in the emtk app: calibrate, keep and restore the correction constants.

The Qt window has this only when ChiSurf opens it (ChiSurf's ndX plugin adds an
"Accurate FRET" toolbar). Here it is part of the app, in a **FRET** menu:

* *FRET calibration…* -- the options (``ndxplorer/analysis/fret_calibration_options.view.json``,
  the same form the Qt window shows), then the run with a progress bar and
  Cancel, then the report: the factors with their uncertainties, the FRET
  populations, the constants before -> after and the calibration's whole text,
  with *Save calibration…* / *Save report…* beside it;
* *Save calibration…* / *Load calibration…* -- into or out of the `.pto` the
  bursts came from, or a ``*.fretcal.json`` file through ``app.io_service``
  (a dialog on a desktop, a download or a dropped file in a page);
  :mod:`ndxplorer.io.fret_calibration_io` is the format, shared with the Qt
  window.

File > Import > *From MMFDB…* is listed, disabled: it needs ChiSurf's MMFDB
client, and the emtk app does not run inside ChiSurf.

The calibration itself is :func:`ndxplorer.analysis.fret_calibration.calibrate`:
columns and constants in, a result out, applied here. The algorithm behind it
is being moved into a compiled library shared with ChiSurf; until it is wired
in, the options say why *Calibrate* is off.
"""

from __future__ import annotations

import json
import logging
import pathlib
from typing import Any, Callable, Dict, List, Optional

from . import Feature

__all__ = ["AccurateFretFeature", "create"]

logger = logging.getLogger(__name__)

SPECS = pathlib.Path(__file__).with_name("accurate_fret")

#: The Qt toolbar labels a hosted scenario triggers -> this feature's actions.
TOOL_ACTIONS: Dict[str, str] = {
    "tool('FRET calibration')": "fret_calibration",
    "tool('Save calibration')": "save_fret_calibration",
    "tool('Load calibration')": "load_fret_calibration",
}

#: The Qt toolbar a hosted scenario photographs; the FRET menu stands for it.
TOOLBAR_TARGET = "widget:win.findChild(QtWidgets.QToolBar, 'ndxplorerAccurateFretToolbar')"

#: Why File > Import > From MMFDB is off here.
MMFDB_REASON = "only inside ChiSurf"

CALIBRATION_FILTERS = "FRET calibration (*.fretcal.json);;All files (*)"


def load_spec(name: str) -> dict:
    """One of this feature's dialog specs, parsed."""
    with open(SPECS / f"{name}.view.json", encoding="utf-8") as handle:
        return json.load(handle)


def _annotate(sections, notes: Dict[str, str]) -> list:
    """*sections* with ``notes[attr]`` appended to the matching fields' descriptions."""
    out = []
    for section in sections:
        section = dict(section)
        if section.get("sections"):
            section["sections"] = _annotate(section["sections"], notes)
        note = notes.get(str(section.get("attr", "")))
        if note:
            section["description"] = (str(section.get("description") or "") + "\n\n" + note).strip()
        out.append(section)
    return out


def options_spec(notes: Optional[Dict[str, str]] = None) -> dict:
    """The options form with the dialog's own lines under it.

    The form is ndX's (shared with the Qt window's AutoForm dialog); what a
    dialog adds -- why it cannot run, and Calibrate / Cancel -- is appended
    here rather than copied into a second spec. *notes* (``{attr: text}``)
    are added to those fields' tooltips: which column a gating dimension is
    read from, or which column it lacks.
    """
    from ...analysis.fret_calibration import CalibrationOptions

    spec = CalibrationOptions.spec()
    sections = _annotate(list(spec.get("sections") or []), dict(notes or {}))
    sections.append({"type": "info", "source": "unavailable_text",
                     "hidden_when": {"attr": "runnable", "equals": "true"}})
    sections.append({"type": "button_row", "buttons": [
        {"label": "Calibrate", "action": "calibrate",
         "description": "Find the donor-only / acceptor-only / FRET populations in the loaded "
                        "bursts and determine the correction factors from them."},
        {"label": "Cancel", "action": "cancel"}]})
    return {"title": "FRET calibration", "sections": sections}


# ------------------------------------------------------------------ dialogs
class Dialog:
    """A dialog of this feature: a spec drawn in a :class:`emtk.dialog_window.DialogWindow`."""

    width, height = 480.0, 200.0
    #: Size to the drawn content (emtk DialogWindow ``fit_height``); a dialog
    #: whose tables fill the window sizes itself instead.
    fit_height = False

    def __init__(self, feature: "AccurateFretFeature", title: str, spec: dict,
                 key: str) -> None:
        from emtk.dialog_window import DialogWindow
        from emtk.view_form import FormState

        self.feature = feature
        self.title = title
        self.spec = spec
        self.form = FormState()
        self.done = False
        self.frame = DialogWindow(title, size=(self.width, self.height), key=f"afret-{key}",
                                  fit_height=self.fit_height)
        self.frame.show()

    @property
    def box(self) -> Optional[tuple]:
        return self.frame.box

    def enabled(self, _name: str) -> bool:
        return True

    def draw(self, window: tuple) -> None:
        from emtk.view_form import draw_form

        if self.frame.begin(window) == "close":
            self.dismiss()
        draw_form(self.spec, self, self.form, titles=True)
        self.frame.end()

    def dismiss(self) -> None:
        self.close()

    def close(self) -> None:
        self.done = True

    def press(self, action: str) -> None:
        """Press a button of this dialog, as a click on it would."""
        fn = getattr(self, action, None)
        if callable(fn) and self.enabled(action):
            fn()


class OptionsDialog(Dialog):
    """What the calibration may write, before it runs."""

    width, height = 560.0, 470.0
    fit_height = True

    def __init__(self, feature: "AccurateFretFeature") -> None:
        from ...analysis.fret_calibration import CalibrationOptions

        constants = dict(feature.app.model.manager.constants or {})
        object.__setattr__(self, "options", CalibrationOptions(
            donor_lifetime=float(constants.get("tauD0", 4.0) or 4.0)))
        #: gating dimension -> why it cannot be ticked here ("" when it can)
        object.__setattr__(self, "missing", {})
        object.__setattr__(self, "method_reason", "")
        object.__setattr__(self, "feature", feature)
        notes = self._availability()
        super().__init__(feature, "FRET calibration", options_spec(notes), "options")

    def _availability(self) -> Dict[str, str]:
        """Which gating dimensions the loaded table has, and the finder's state.

        A dimension without a column is unticked and disabled; the tooltip
        notes say which column it would need, or which one it is read from.
        """
        from ...analysis.fret_calibration import DIMENSION_ATTRS

        notes: Dict[str, str] = {}
        source = self.feature.app.model.source
        names = list(getattr(source, "parameter_names", None) or [])
        try:
            from ...analysis.fret_backend import (DIMENSION_NEEDS, dimension_columns,
                                                  population_method_reason)
        except Exception:  # noqa: BLE001 - no tttrlib calibration: the form says why
            return notes
        found = dimension_columns(names)
        for dim, attr in DIMENSION_ATTRS.items():
            column = found.get(dim)
            if column is None:
                need = DIMENSION_NEEDS.get(dim, "donor-excitation channel counts")
                self.missing[dim] = f"Unavailable: this measurement has no {need}."
                setattr(self.options, attr, False)
                notes[attr] = self.missing[dim]
            elif column:
                notes[attr] = f"Read from the column '{column}'."
        object.__setattr__(self, "method_reason", population_method_reason())
        if self.method_reason:
            self.options.population_method = "gmm"
            notes["population_method"] = f"Unavailable: {self.method_reason}."
        return notes

    # The form's fields are the options' attributes.
    def __getattr__(self, name: str):
        options = self.__dict__.get("options")
        if options is not None and hasattr(options, name):
            return getattr(options, name)
        raise AttributeError(name)

    def __setattr__(self, name: str, value) -> None:
        options = self.__dict__.get("options")
        if options is not None and hasattr(options, name):
            setattr(options, name, value)
        else:
            object.__setattr__(self, name, value)

    @property
    def runnable(self) -> bool:
        return not self.unavailable_text()

    def unavailable_text(self) -> str:
        from ...analysis.fret_calibration import unavailable_reason

        return unavailable_reason()

    def enabled(self, name: str) -> bool:
        from ...analysis.fret_calibration import DIMENSION_ATTRS

        if name == "calibrate":
            return self.runnable
        if name == "population_method":
            return not self.method_reason
        dim = next((d for d, attr in DIMENSION_ATTRS.items() if attr == name), None)
        if dim is not None:
            return dim not in self.missing
        return True

    def calibrate(self) -> None:
        self.close()
        self.feature.run(self.options)

    def cancel(self) -> None:
        self.close()


class ProgressDialog(Dialog):
    """The run: a bar, what it is doing, Cancel."""

    width, height = 420.0, 130.0

    def __init__(self, feature: "AccurateFretFeature") -> None:
        super().__init__(feature, "FRET calibration…", load_spec("progress"), "progress")

    def _task(self):
        return self.feature.task

    def message_text(self) -> str:
        task = self._task()
        return (task.message if task is not None and task.message else "Starting…")

    def fraction(self) -> Optional[float]:
        task = self._task()
        return None if task is None or not task.progress else float(task.progress)

    def fraction_text(self) -> str:
        value = self.fraction()
        return "" if value is None else f"{100.0 * value:.0f} %"

    def dismiss(self) -> None:
        self.cancel()

    def cancel(self) -> None:
        task = self._task()
        if task is not None:
            task.cancel()


class Question(Dialog):
    """Yes / No (/ Cancel): ``on_answer("yes" | "no" | "cancel")``."""

    width, height = 640.0, 200.0
    fit_height = True

    def __init__(self, feature, title: str, text: str, on_answer: Callable[[str], None],
                 three_way: bool = True) -> None:
        super().__init__(feature, title, load_spec("question"), f"question-{id(self)}")
        self.text = text
        self.two_way = not three_way
        self.on_answer = on_answer
        self.answer: Optional[str] = None

    def body(self) -> str:
        return self.text

    def _answered(self, answer: str) -> None:
        self.answer = answer
        self.close()
        self.on_answer(answer)

    def yes(self) -> None:
        self._answered("yes")

    def no(self) -> None:
        self._answered("no")

    def cancel(self) -> None:
        self._answered("cancel")

    def dismiss(self) -> None:
        # Nobody at the keyboard writes nothing: the safe answer.
        self._answered("no" if self.two_way else "cancel")


def _float(value) -> Optional[float]:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


class ReportWindow(Dialog):
    """A finished (or loaded) calibration, and keeping it."""

    width, height = 720.0, 640.0
    fit_height = True

    def __init__(self, feature, title: str, text: str, *, result: Optional[dict] = None,
                 saved: Optional[dict] = None, header: str = "") -> None:
        super().__init__(feature, title, load_spec("report"), "report")
        result = dict(result or {})
        self.result = result
        self.report_text = text
        self.header = header or (
            "The correction factors were optimized against the loaded data." if result
            else "A stored calibration.")
        self.status = ""
        if saved and saved.get("ok"):
            self.status = (f"Stored in the measurement: {saved.get('target', '')}"
                           if saved.get("where") == "container"
                           else f"Saved to {saved.get('target', '')}"
                           + (f" — {saved['warning']}" if saved.get("warning") else ""))
        elif saved and saved.get("error"):
            self.status = f"Not stored automatically: {saved['error']}"
        # Built once: a table rebinds (and loses its scroll) on a new list.
        self._factors = self._factor_rows()
        self._populations = self._population_rows()
        self._constants = self._constant_rows()
        from ...analysis.fret_calibration import population_summary

        self._population_summary = population_summary(result)

    def _factor_rows(self) -> List[dict]:
        from ...analysis.fret_calibration import FACTOR_NAMES

        factors = dict(self.result.get("factors") or {})
        errors = dict(self.result.get("uncertainties") or {})
        applied = set(self.result.get("applied_factors") or FACTOR_NAMES)
        held = dict(self.result.get("held") or {})
        symbols = {"alpha": "α", "beta": "β", "gamma": "γ", "delta": "δ", "r0": "R₀"}
        rows = []
        for name in FACTOR_NAMES:
            if name not in factors:
                continue
            rows.append({"factor": symbols.get(name, name), "value": _float(factors[name]),
                         "error": _float(errors.get(name)),
                         "written": "written" if name in applied and name not in held
                         else f"held at {float(held[name]):.4g}" if name in held
                         else "held"})
        return rows

    def _population_rows(self) -> List[dict]:
        return [{"label": int(p.get("label", i)), "n": int(p.get("n", 0)),
                 "E": _float(p.get("E")), "sigma_E": _float(p.get("sigma_E")),
                 "S": _float(p.get("S")), "distance": _float(p.get("distance")),
                 "tau_f": _float(p.get("tau_f"))}
                for i, p in enumerate(self.result.get("populations") or [])]

    def _constant_rows(self) -> List[dict]:
        before = dict(self.result.get("before") or {})
        return [{"name": str(name), "before": _float(before.get(name)), "after": _float(value)}
                for name, value in dict(self.result.get("constants") or {}).items()]

    # -- what the spec reads --------------------------------------------------
    def header_text(self) -> str:
        return self.header

    @property
    def has_factors(self) -> bool:
        return bool(self._factors)

    @property
    def has_populations(self) -> bool:
        return bool(self._populations)

    @property
    def has_constants(self) -> bool:
        return bool(self._constants)

    def factor_rows(self) -> List[dict]:
        return self._factors

    def population_rows(self) -> List[dict]:
        return self._populations

    def constant_rows(self) -> List[dict]:
        return self._constants

    @property
    def has_population_summary(self) -> bool:
        return bool(self._population_summary)

    def population_text(self) -> str:
        return "\n".join(self._population_summary)

    def notes_text(self) -> str:
        lines = []
        source = self.result.get("background")
        fitted = dict(self.result.get("background_fitted") or {})
        if source == "fit" and fitted:
            lines.append("Background, fitted from the reference populations: "
                         + ", ".join(f"{k} = {float(v):.2f} kHz" for k, v in fitted.items()))
        elif source:
            lines.append(f"Background: {source}")
        if self.result.get("injected"):
            lines.append("New columns: " + ", ".join(self.result["injected"]))
        return "\n".join(lines)

    def status_text(self) -> str:
        return self.status

    # -- buttons --------------------------------------------------------------
    def save_calibration(self) -> None:
        self.feature.save_calibration(result=self.result or None, report=self)

    def save_report(self) -> None:
        data = (self.report_text + "\n").encode("utf-8")
        service = self.feature.app.io_service
        if service.browser:
            service.save_bytes("fret_calibration.txt", data, "text/plain")
            self.status = "Report downloaded as fret_calibration.txt"
            return

        def write(path: str) -> None:
            with open(path, "wb") as handle:
                handle.write(data)
            self.status = f"Report written to {path}"

        service.ask_save("Save report", "Text (*.txt);;All files (*)", "fret_calibration.txt",
                         write)


# ------------------------------------------------------------------ feature
class AccurateFretFeature(Feature):
    """The FRET menu: calibrate, save and load the correction constants."""

    name = "accurate_fret"

    def __init__(self, app) -> None:
        super().__init__(app)
        self.window: Optional[Dialog] = None
        self.questions: List[Question] = []
        self.task = None
        self._options = None
        #: ``None`` (the default runner: a thread on a desktop, slices in a
        #: page) or ``"inline"`` (a scripted capture).
        self.task_mode: Optional[str] = None
        # Capture replay: queued answers, and answered questions left on
        # screen as the Qt harness leaves them, until close_dialogs.
        self._dialog_results: List[int] = []
        self._question_answers: List[str] = []
        self._file_answers: List[str] = []
        self._answered: List[Question] = []
        self._front: Optional[Question] = None
        #: container -> the stored constants last restored from it.
        self._restored: Dict[str, dict] = {}

    # -------------------------------------------------------- the window
    @property
    def data_source(self):
        """The loaded table: what :mod:`ndxplorer.io.fret_calibration_io` reads the
        container from (its ``provenance``)."""
        return self.app.model.source

    @property
    def constants(self) -> dict:
        return {str(k): float(v) for k, v in dict(self.app.model.manager.constants or {}).items()
                if _float(v) is not None}

    def container(self) -> str:
        """The `.pto` the bursts came from (tttrlib reads and writes it), or ``""``."""
        from ...io.fret_calibration_io import container_of

        return container_of(self)

    def write_vector(self, name: str, vector: dict) -> None:
        """Make constant *name* a per-population vector (species-specific factor).

        *vector* holds the arguments of the constants' ``set_vector``:
        ``values``, ``populations`` and optionally ``uncertainties``,
        ``default`` (the global value), ``column`` (per-burst population label),
        ``codes`` (``{population: value in that column}``) and
        ``probabilities`` (``{population: probability column}``).
        """
        constants = self.app.model.manager.constants
        set_vector = getattr(constants, "set_vector", None)
        if not callable(set_vector):
            return
        populations = [str(p) for p in vector["populations"]]
        uncertainties = vector.get("uncertainties")
        if isinstance(uncertainties, dict):
            # as :meth:`vectors` saves them: by population, not by position
            uncertainties = [uncertainties.get(p) for p in populations]
        set_vector(name, list(vector["values"]), populations,
                   uncertainties=uncertainties, default=vector.get("default"),
                   column=vector.get("column"), probabilities=vector.get("probabilities"),
                   codes=vector.get("codes"))

    def vectors(self) -> dict:
        """The window's vector constants as saved (order, axis, uncertainties)."""
        group = getattr(self.app.model.manager.constants, "group", None)
        if group is None:
            return {}
        from ...core.constants_group import vector_elements, vectors_state

        state = vectors_state(group)
        for name, entry in state.items():
            entry["values"] = [float(p.value) for _, p in vector_elements(group, name)]
        return state

    def write_constants(self, values: Dict[str, float]) -> None:
        """Write *values* into the window's constants and re-derive what they feed.

        The constants mapping is the Parameters tab's group when there is one:
        writing through it keeps Global View links, and the tab's poll
        recomputes the equation columns once for all of them.
        """
        model = self.app.model
        constants = model.manager.constants
        update = getattr(constants, "update", None)
        if callable(update):
            update(dict(values))
        else:
            merged = dict(constants or {})
            merged.update(values)
            model.manager.constants = merged
        panel = next((getattr(f, "constants", None) for f in self.app.features
                      if callable(getattr(getattr(f, "constants", None), "poll", None))), None)
        if panel is not None:
            panel.poll()
        elif model.has_data:
            try:
                model.source.compute_columns(constants=model.manager.constants,
                                             equations=model.manager.equations)
            except Exception as exc:  # noqa: BLE001 - shown, the window goes on
                logger.warning("Recompute after the calibration failed: %s", exc)
        model.invalidate()

    def restore_stored(self) -> dict:
        """Apply the constants the opened measurement stores (as the Qt window does).

        The newest saved calibration (constants and vector constants, as Load
        applies them) and the background step's rates
        (:func:`~ndxplorer.io.fret_calibration_io.restorable`), so the window
        holds the constants determined on the data now loaded. Once per
        *value*: a container whose stored constants have not moved since they
        were last restored leaves the window as it is, so anything tuned since
        stays; a newly stored background or calibration is followed.
        """
        from ...io.fret_calibration_io import container_of, restorable

        container = container_of(self)
        if not container:
            return {}
        try:
            stored = restorable(container)
        except Exception:  # noqa: BLE001 - a window that cannot restore keeps its constants
            logger.debug("could not read the stored constants of %s", container, exc_info=True)
            return {}
        values = {**stored["background"], **stored["saved"]}
        if not values or self._restored.get(container) == values:
            return {}
        self._restored[container] = values
        self.write_constants(values)
        for name, vector in stored["vectors"].items():
            if vector.get("values") and vector.get("populations"):
                self.write_vector(name, vector)
        self.app.show_status(f"Restored {len(values)} constants stored in "
                             f"{pathlib.Path(container).name}")
        return values

    # --------------------------------------------------------------- hooks
    def on_data_changed(self) -> None:
        self.restore_stored()

    def actions(self) -> Dict[str, Callable[[], Any]]:
        return {"fret_calibration": self.fret_calibration,
                "save_fret_calibration": self.save_calibration,
                "load_fret_calibration": self.load_calibration,
                "open_from_mmfdb": self.open_from_mmfdb}

    def available(self, action: str) -> Optional[bool]:
        if action == "open_from_mmfdb":
            return False
        if action in ("fret_calibration", "save_fret_calibration", "load_fret_calibration"):
            return self.app.model.has_data and self.task is None
        return None

    def menu_entries(self) -> List[tuple]:
        return [
            (("FRET",), {"label": "FRET calibration…", "action": "fret_calibration"}),
            (("FRET",), None),
            (("FRET",), {"label": "Save calibration…", "action": "save_fret_calibration"}),
            (("FRET",), {"label": "Load calibration…", "action": "load_fret_calibration"}),
            (("File", "Import"),
             {"label": f"From MMFDB… ({MMFDB_REASON})", "action": "open_from_mmfdb"}),
        ]

    def animating(self) -> bool:
        return self.task is not None

    def draw_windows(self) -> bool:
        box = self.app.box
        self._poll_task()
        for question in list(self._answered):
            if question is not self._front:
                question.draw(box)
        window = self.window
        if window is not None:
            window.draw(box)
            if window.done and self.window is window:
                self.window = None
        if self.questions:
            question = self.questions[0]
            question.draw(box)
            if question.done and question in self.questions:
                self.questions.remove(question)
        if self._front is not None:
            self._front.draw(box)
        return self.window is not None or bool(self.questions) or self.task is not None

    # ------------------------------------------------------------- helpers
    def message(self, title: str, text: str) -> None:
        self.app.message = (title, text)

    def ask(self, title: str, text: str, on_answer: Callable[[str], None],
            three_way: bool = True) -> None:
        """A question; a capture's queued answer answers it at once."""
        question = Question(self, title, text, on_answer, three_way)
        if self._question_answers:
            answer = self._question_answers.pop(0)
            self._answered.append(question)
            question.frame.show()
            question.done = False
            question.answer = answer
            on_answer(answer)
            return
        self.questions.append(question)

    def _ask_file(self, kind: str, title: str, default: str, callback) -> None:
        service = self.app.io_service
        if kind == "save":
            service.ask_save(title, CALIBRATION_FILTERS, default, callback)
        else:
            service.ask_open(title, CALIBRATION_FILTERS, lambda paths: callback(paths[0]))
        if self._file_answers:
            service.answer(self._file_answers.pop(0))

    # --------------------------------------------------------- calibration
    def fret_calibration(self) -> None:
        """FRET > FRET calibration…: the options first."""
        self.window = OptionsDialog(self)

    def run(self, options) -> None:
        """Calibrate the loaded bursts with *options*, beside the frames."""
        from emtk import tasks

        from ...analysis.fret_calibration import burst_columns, calibrate
        from ...io.fret_calibration_io import container_of

        columns = burst_columns(self.app.model.source)
        constants = self.constants
        container = container_of(self)
        self._options = options

        def work(task):
            def progress(step, total, message) -> bool:
                task.report(float(step) / float(total) if total else None, str(message))
                return not task.cancelled

            return calibrate(columns, constants, options, container=container,
                             progress=progress)

        self.window = ProgressDialog(self)
        self.task = tasks.start(work, mode=self.task_mode, name="fret-calibration")
        self._poll_task()

    def _poll_task(self) -> None:
        task = self.task
        if task is None:
            return
        task.poll()
        if not task.done:
            return
        self.task = None
        if isinstance(self.window, ProgressDialog):
            self.window = None
        if task.cancelled:
            self.app.show_status("FRET calibration cancelled; the constants are unchanged")
            return
        result = task.result if task.succeeded else {"ok": False, "error": task.error}
        self.finish(dict(result or {}), self._options)

    def finish(self, result: dict, options=None) -> None:
        """Apply a calibration's result and show its report."""
        from ...analysis.fret_calibration import apply_result, report_text

        if not result.get("ok"):
            self.message("Accurate FRET", str(result.get("error") or "calibration failed"))
            return
        model = self.app.model
        apply_result(result, write_constants=self.write_constants, data_source=model.source,
                     write_vector=self.write_vector)
        model.invalidate()
        for feature in self.app.features:
            if feature is not self:
                feature.on_data_changed()
        saved = None
        # Stored before the report is shown: the numbers are worth more than
        # the window, and closing the report must not discard them.
        if options is not None and options.save_requested() and self.container():
            from ...io.fret_calibration_io import save_calibration

            saved = save_calibration(self.constants, ndx=self, result=result, embed=True,
                                     vectors=self.vectors())
        self.window = ReportWindow(self, "FRET calibration — applied", report_text(result),
                                   result=result, saved=saved)

    # ------------------------------------------------------------- saving
    def save_calibration(self, result: Optional[dict] = None,
                         report: Optional[ReportWindow] = None) -> None:
        """Into the measurement by default; a ``*.fretcal.json`` file otherwise."""
        from ...io.fret_calibration_io import SUFFIX, payload, save_calibration

        constants = self.constants
        if not constants:
            self.message("FRET calibration", "This window carries no constants to save.")
            return

        def say(text: str) -> None:
            if report is not None:
                report.status = text
            else:
                self.message("FRET calibration", text)

        def to_file() -> None:
            container = container_of_window()
            start = (pathlib.Path(container).stem if container else "calibration") + SUFFIX
            data = payload(constants, result=result, vectors=self.vectors())
            service = self.app.io_service
            if service.browser:
                service.save_bytes(start, data, "application/json")
                say(f"Downloaded {start}")
                return

            def write(path: str) -> None:
                out = save_calibration(constants, ndx=self, path=path, result=result,
                                       embed=False, vectors=self.vectors())
                say(f"Saved to {out.get('target', '')}" if out.get("ok")
                    else f"Could not save: {out.get('error')}")

            self._ask_file("save", "Save calibration", start, write)

        def container_of_window() -> str:
            from ...io.fret_calibration_io import container_of

            return container_of(self)

        container = self.container()
        if not container:
            to_file()
            return

        def answered(answer: str) -> None:
            if answer == "yes":
                out = save_calibration(constants, ndx=self, result=result, embed=True,
                                       vectors=self.vectors())
                say(f"Stored in {out.get('target', '')}" if out.get("ok")
                    else f"Could not store: {out.get('error')}")
            elif answer == "no":
                to_file()

        self.ask("Save calibration",
                 "Store the calibration in the measurement?\n\n"
                 f"{container}\n\n"
                 "Yes keeps it beside the photons and the burst table. "
                 "No writes a separate file instead.", answered)

    # ------------------------------------------------------------ loading
    def load_calibration(self) -> None:
        """The measurement's newest stored calibration, or a file; asked before applied."""
        from ...io.fret_calibration_io import load_calibration, stored_calibrations

        def from_file() -> None:
            self._ask_file("open", "Load calibration", "",
                           lambda path: self._offer(load_calibration(path=path)))

        stored = stored_calibrations(self) if self.container() else []
        if not stored:
            from_file()
            return

        def answered(answer: str) -> None:
            if answer == "yes":
                self._offer(load_calibration(ndx=self))
            elif answer == "no":
                from_file()

        self.ask("Load calibration",
                 f"This measurement carries {len(stored)} stored calibration(s).\n\n"
                 "Load the most recent one? No opens a file instead.", answered)

    def _offer(self, loaded: dict) -> None:
        """Show what a loaded calibration would change, and apply it on Yes."""
        if not loaded.get("ok"):
            self.message("FRET calibration", str(loaded.get("error")))
            return
        values = {str(k): float(v) for k, v in dict(loaded.get("constants") or {}).items()
                  if _float(v) is not None}
        before = self.constants
        # What would change is shown BEFORE anything changes: applying a
        # calibration replaces numbers the user may have determined elsewhere.
        changes = [f"  {name}: {before.get(name, '—')!s} → {value}"
                   for name, value in sorted(values.items()) if before.get(name) != value]
        detail = "\n".join(
            [f"Saved {loaded.get('saved_utc', '')} ({loaded.get('where')}: "
             f"{loaded.get('target', '')})"]
            + ([f"Note: {loaded['note']}"] if loaded.get("note") else [])
            + ["", ("Changes:" if changes else "Nothing would change.")] + changes)

        def answered(answer: str) -> None:
            if answer != "yes":
                return
            self.write_constants(values)
            for name, vector in dict(loaded.get("vectors") or {}).items():
                if vector.get("values") and vector.get("populations"):
                    self.write_vector(name, vector)
            if loaded.get("report"):
                document = dict(loaded.get("document") or {})
                result = {k: document[k] for k in ("factors", "uncertainties", "held",
                                                   "determined", "background",
                                                   "background_fitted") if k in document}
                self.window = ReportWindow(self, "FRET calibration — loaded", loaded["report"],
                                           result=result, header="A stored calibration.")

        self.ask("Load calibration", "Apply this calibration to the window?\n\n" + detail,
                 answered, three_way=False)

    # --------------------------------------------------------------- MMFDB
    def open_from_mmfdb(self) -> None:
        self.message("Open from MMFDB", "Opening a burst selection registered in MMFDB needs "
                     "ChiSurf's MMFDB client: it works when ndX runs inside ChiSurf.")

    # ------------------------------------------------------------- capture
    def capture_actions(self) -> Dict[str, str]:
        return dict(TOOL_ACTIONS)

    def capture_ops(self) -> Dict[str, Callable]:
        return {"trigger": self._op_trigger, "dialog_results": self._op_dialog_results,
                "question_answers": self._op_question_answers,
                "file_answer": self._op_file_answer, "wait_until": self._op_wait_until,
                "call": self._op_call, "resize_dialog": self._op_resize,
                "capture": self._op_capture,
                "close_dialogs": self._op_close_dialogs}

    def capture_targets(self) -> Dict[str, Callable]:
        return {
            "dialog": self._dialog_box,
            "dialog:FRET calibration": lambda _r: (self.window.box if isinstance(
                self.window, ReportWindow) else None),
            "dialog:loaded": lambda _r: (self.window.box if isinstance(self.window, ReportWindow)
                                         and "loaded" in self.window.title else None),
        }

    def _dialog_box(self, _replay) -> Optional[tuple]:
        if self.app.message is not None:
            return None
        if self.questions:
            return self.questions[0].box
        if self.window is not None:
            return self.window.box
        if self._answered:
            return self._answered[-1].box
        return None

    def _op_trigger(self, replay, step: dict):
        action = TOOL_ACTIONS.get(step.get("action", ""))
        if action is None:
            return False
        from ..capture import Unsupported

        self.task_mode = "inline"
        replay.settle()
        if not self.app.run_action(action):
            raise Unsupported(f"{action} is not available")
        replay.settle()
        if action == "fret_calibration" and self._dialog_results:
            # The Qt harness: the options dialog returns the queued result;
            # 1 is Calibrate, 0 leaves it on screen (as a cancelled one is).
            if self._dialog_results.pop(0) == 1 and isinstance(self.window, OptionsDialog):
                self.window.press("calibrate")
                if self._dialog_results:
                    self._dialog_results.pop(0)      # the report stays open
        replay.settle(3)
        return True

    def _op_capture(self, replay, step: dict):
        """Two shots this feature takes itself.

        The Qt window's Accurate FRET toolbar is the FRET menu here: open it,
        photograph it, close it. And a question found by its text
        (``dialog:<text>``, as the Qt harness finds a message box) is brought
        to the front for its picture: the Qt harness leaves every answered box
        on screen as its own window, where here they would lie under what
        followed them.
        """
        from ..capture import _ints

        target = str(step.get("target", ""))
        name = step.get("name", "main")
        if target.startswith("dialog:") and target[len("dialog:"):] not in (
                "FRET calibration", "loaded", "QFileDialog"):
            needle = target[len("dialog:"):]
            question = next((q for q in reversed(self.questions + self._answered)
                             if needle in q.text), None)
            if question is None:
                return False
            message, self.app.message = self.app.message, None
            self._front = question
            try:
                image = replay.draw()
                replay.shots[name] = image.crop(_ints(question.box, pad=2))
            finally:
                self._front = None
                self.app.message = message
            replay.draw()
            return True
        if target != TOOLBAR_TARGET:
            return False
        replay.op_menu({"path": ["FRET"]})
        image = replay.draw()
        replay.shots[step.get("name", "main")] = image.crop(_ints(replay.menu_box(), pad=2))
        replay.op_close_menus({})
        return True

    def _op_dialog_results(self, _replay, step: dict):
        self._dialog_results = [int(v) for v in step.get("values") or []]
        return True

    def _op_question_answers(self, _replay, step: dict):
        self._question_answers = [str(v) for v in step.get("values") or []]
        return True

    def _op_file_answer(self, replay, step: dict):
        if self.window is not None and not isinstance(self.window, ReportWindow):
            return False
        path = step["path"] if isinstance(step["path"], str) else step["path"][0]
        self._file_answers.append(replay.dataset(path))
        return True

    def _op_wait_until(self, replay, step: dict):
        if "FRET calibration" not in str(step.get("expr", "")):
            return False
        if self.task is not None:
            self.task.wait(float(step.get("timeout", 240000)) / 1000.0)
        replay.settle(3)
        return True

    def _op_call(self, replay, step: dict):
        code = str(step.get("code", ""))
        if "QPlainTextEdit" in code or "mmfdb_toolbar" in code:
            return True                      # a record for the Qt log only
        if "'How'" in code and isinstance(self.window, OptionsDialog):
            self.window.form.folds["How"] = True
            replay.settle()
            return True
        return False

    def _op_resize(self, replay, step: dict):
        if not isinstance(self.window, OptionsDialog):
            return False
        replay.settle()                      # the dialog is sized to what is open
        return True

    def _op_close_dialogs(self, replay, _step: dict):
        self._answered.clear()
        self.questions.clear()
        self.window = None
        replay.settle()
        return False                         # other features close theirs too


def create(app) -> AccurateFretFeature:
    return AccurateFretFeature(app)
