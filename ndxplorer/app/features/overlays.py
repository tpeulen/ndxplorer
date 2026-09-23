"""Overlays, constants, equations and the table editor, in the emtk app.

What this feature adds to the window:

* the **Parameters** tab -- nDXplorer's constants (``gG/gR``, ``Bg``, ``PhiA``…)
  as a chisurf :class:`FittingParameterGroup`: value, fixed, bounds, a link to
  another parameter (a fit's, a curve's). An edit re-derives only the columns
  that read the constant, once per frame however many edits arrived;
* the **Overlays** tab -- curves drawn over the 2-D map
  (:mod:`ndxplorer.core.overlay_curves`), each with its parameter table, a
  colour, *Fit* and *Delete*; *Save CSV* writes the visible ones;
* **Fit curve to data** -- a curve fitted to the displayed 2-D distribution or
  a marginal (:mod:`ndxplorer.analysis.curve_fit_setup`), with the constants
  the equations read offered as parameters that move the *data*;
* the **Equations** tab -- the derived-column equations, validated per row
  (:mod:`ndxplorer.core.equation_table`), with *Names & functions*; reachable
  from View > Equations (in the Qt window it is not reachable at all);
* the **Table Editor** behind the *Data* button -- every column of the data,
  edited on a copy and written back on Apply (:mod:`ndxplorer.core.store_edits`).

Every panel and dialog is a ``view.json`` in ``features/overlays/`` drawn by
:mod:`emtk.view_form`; tables are its ``data_table`` sections. The drawing
done by hand is the curves on the map.

chisurf (its Qt-free ``chisurf.core``) is what holds the parameters. Without it
the constants stay plain numbers and the curve tools say they cannot run.
"""

from __future__ import annotations

import copy
import json
import logging
import math
import pathlib
import sys
import threading
from collections import OrderedDict
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np

from . import Feature

__all__ = ["OverlaysFeature", "create", "parameter_records", "edit_parameter"]

logger = logging.getLogger(__name__)

VIEWS = pathlib.Path(__file__).with_name("overlays")
_SPECS: Dict[str, dict] = {}

#: The Qt widgets the parity scenarios name -> what stands for them here.
QT_WIDGETS = {
    "win.curve_overlay_widget.predefined_combo": "equation_choice",
    "win.curve_overlay_widget.add_button": "add_curve",
    "win.curve_overlay_widget.curves[-1].fit_button": "fit_last_curve",
    "win.toolButton_3": "show_data",
    "button('Add parameter')": "add_parameter",
    "win.equation_editor._btn_names": "show_names",
}


def load_spec(name: str) -> dict:
    """A spec of this feature, parsed once."""
    if name not in _SPECS:
        with open(VIEWS / f"{name}.view.json", encoding="utf-8") as handle:
            _SPECS[name] = json.load(handle)
    return _SPECS[name]


def _fill(spec: dict, **words: str) -> dict:
    """A copy of *spec* with ``{word}`` in its labels filled in."""
    spec = copy.deepcopy(spec)

    def walk(sections):
        for section in sections or ():
            label = section.get("label")
            if isinstance(label, str) and "{" in label:
                section["label"] = label.format(**words)
            walk(section.get("sections"))

    walk(spec.get("sections"))
    return spec


#: Whether chisurf's parameters can be built here, and why not.
_CHISURF: Dict[str, Any] = {}


def _has_chisurf() -> bool:
    """Whether a chisurf :class:`FittingParameter` can be made (checked once).

    Importing is not enough: a parameter needs chisurf's compiled port runtime,
    which a browser does not have and a half-rebuilt desktop may not load.
    """
    if "ok" not in _CHISURF:
        try:
            from chisurf.core.fitting.parameter import FittingParameter

            FittingParameter(name="probe", value=1.0)
            _CHISURF.update(ok=True, why="")
        except Exception as exc:  # noqa: BLE001 - any failure: no parameter groups
            _CHISURF.update(ok=False, why=str(exc).splitlines()[0][:300])
            logger.warning("chisurf parameters are not available: %s", _CHISURF["why"])
    return bool(_CHISURF["ok"])


def _no_chisurf_text() -> str:
    return ("chisurf's parameters are not available here, so the constants are plain "
            "numbers (no bounds, no links) and curves cannot be added"
            + (f": {_CHISURF.get('why')}" if _CHISURF.get("why") else "."))


def _in_browser() -> bool:
    return sys.platform == "emscripten"


# ------------------------------------------------------------ parameter rows
def parameter_records(parameters) -> List[dict]:
    """The rows of a parameter table: name, value, fixed, bounds and link.

    ``lo``/``hi`` are empty while the bounds are off, as the Qt table shows
    them; typing one switches them on.
    """
    rows = []
    for p in parameters:
        bounds = bool(getattr(p, "bounds_on", False))
        link = getattr(p, "link", None) if getattr(p, "is_linked", False) else None
        rows.append({
            "name": str(p.name),
            "value": float(p.value),
            "fixed": bool(p.fixed),
            "lo": float(p.lb) if bounds and p.lb is not None else None,
            "hi": float(p.ub) if bounds and p.ub is not None else None,
            "bounds": bounds,
            "link": str(getattr(link, "name", "")) if link is not None else "",
        })
    return rows


def _number(value) -> Optional[float]:
    try:
        number = float(str(value).strip())
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def edit_parameter(parameter, key: str, value) -> bool:
    """Write one cell of a parameter table into *parameter*; ``False`` if refused."""
    if key == "value":
        number = _number(value)
        if number is None or getattr(parameter, "is_linked", False):
            return False
        parameter.value = number
    elif key == "fixed":
        parameter.fixed = bool(value)
    elif key == "bounds":
        parameter.bounds_on = bool(value)
    elif key in ("lo", "hi"):
        from .constant_rows import is_unbounded_text

        if is_unbounded_text(value):
            # No bound on this side; the other side's decides enforcement.
            if not bool(getattr(parameter, "bounds_on", False)):
                return True
            other = parameter.ub if key == "lo" else parameter.lb
            if key == "lo":
                parameter.lb = float("-inf")
            else:
                parameter.ub = float("inf")
            parameter.bounds_on = math.isfinite(float(other))
            return True
        number = _number(value)
        if number is None:
            return False
        if key == "lo":
            if not bool(getattr(parameter, "bounds_on", False)):
                parameter.ub = float("inf")
            parameter.lb = number
        else:
            if not bool(getattr(parameter, "bounds_on", False)):
                parameter.lb = float("-inf")
            parameter.ub = number
        parameter.bounds_on = True
    else:
        return False
    return True


class _RowCache:
    """Hands a table the same list while its content is the same.

    A data table re-reads its source every frame and rebinds on a new list;
    building the rows afresh each frame would reset its order every frame.
    """

    def __init__(self) -> None:
        self._rows: List[dict] = []
        self._token: Any = None

    def get(self, rows: List[dict]) -> List[dict]:
        token = tuple(tuple(sorted(r.items(), key=lambda kv: kv[0])) for r in rows)
        if token != self._token:
            self._token = token
            self._rows = rows
        return self._rows


class _ParameterPanel:
    """The shared part of a panel with a parameter table: edit, copy, paste, link."""

    def __init__(self, feature: "OverlaysFeature") -> None:
        self.feature = feature
        self._cache = _RowCache()

    def parameters(self) -> list:
        raise NotImplementedError

    def changed(self) -> None:
        """A parameter changed (a subclass redraws or recomputes)."""

    def enabled(self, _name: str) -> bool:
        return True

    def parameter_rows(self) -> List[dict]:
        return self._cache.get(parameter_records(self.parameters()))

    def _parameter(self, record):
        name = record.get("name") if isinstance(record, dict) else None
        return next((p for p in self.parameters() if p.name == name), None)

    def edit_parameter(self, record, key, value) -> None:
        parameter = self._parameter(record)
        if parameter is not None and edit_parameter(parameter, key, value):
            self.changed()

    def parameter_menu(self, record, _key, where) -> None:
        parameter = self._parameter(record)
        if parameter is None:
            return
        entries = [("Copy", lambda: self.feature.copy_text(repr(float(parameter.value)))),
                   ("Paste", lambda: self._paste(parameter))]
        if _has_chisurf():
            entries.append(("Link…", lambda: self.feature.open_link(parameter, self)))
            if getattr(parameter, "is_linked", False):
                entries.append(("Unlink", lambda: self._unlink(parameter)))
        self.feature.open_menu(entries, where)

    def _paste(self, parameter) -> None:
        number = _number(self.feature.clipboard)
        if number is not None and not getattr(parameter, "is_linked", False):
            parameter.value = number
            self.changed()

    def _unlink(self, parameter) -> None:
        parameter.link = None
        self.changed()


# ---------------------------------------------------------------- constants
class ConstantsPanel(_ParameterPanel):
    """The Parameters tab: the constants, their group, saving them, adding one.

    The group is installed as the data manager's ``constants`` (a live mapping
    over it), so the equations read a linked constant's current value.
    """

    OWNER_ID = "ndxplorer"

    def __init__(self, feature: "OverlaysFeature") -> None:
        from emtk.view_form import FormState

        super().__init__(feature)
        self.form = FormState()
        self.group = None
        self.mapping: Any = None
        self._snapshot: Dict[str, float] = {}
        self._pending: set = set()
        #: Keys of the vector rows the table shows open (the table shares it).
        self.expanded: set = set()
        self._axis_token: Any = None
        self._axis_checked = 0.0
        self.build()

    # -- the group ----------------------------------------------------------
    def build(self) -> None:
        """The group from the settings' constants file (values, bounds, fixed)."""
        model = self.feature.app.model
        values = OrderedDict(model.bundle.constants)
        if not _has_chisurf():
            self.group, self.mapping = None, dict(values)
            return
        from ...core import constants_group as cg

        data = self._constants_file_data()
        self.group = cg.build_group_from_data(data if data else values)
        # Constants the settings name but the file lacks (a newer bundle).
        cg.apply_value_dict(self.group, {k: v for k, v in values.items()
                                         if k not in self.group.parameters_all_dict})
        self.mapping = cg.ConstantsMapping(self.group)
        self._snapshot = dict(self.values())
        try:
            from chisurf.core.parameter_group_registry import register_parameter_group

            register_parameter_group(self.group, owner_id=self.OWNER_ID, label="ndX")
        except Exception as exc:  # noqa: BLE001 - linking is optional
            logger.debug("Could not register the constants: %s", exc)

    def _constants_file_data(self) -> Optional[dict]:
        from ...settings.bundle import _named

        model = self.feature.app.model
        name = model.bundle.settings.get("constants")
        if not name:
            return None
        path = _named(pathlib.Path(model.bundle.path).parent, name)
        try:
            with open(path, "r", encoding="utf-8") as handle:
                return json.load(handle, object_pairs_hook=OrderedDict)
        except (OSError, ValueError):
            return None

    def values(self) -> Dict[str, float]:
        return {str(k): float(v) for k, v in dict(self.mapping).items()}

    @property
    def degraded(self) -> bool:
        return self.group is None

    def degraded_text(self) -> str:
        return _no_chisurf_text()

    def parameters(self) -> list:
        return list(self.group.parameters_all) if self.group is not None else []

    def parameter_rows(self) -> List[dict]:
        """Scalars one row each; a vector as a parent row over its populations."""
        from .constant_rows import constant_rows

        if self.group is None:
            return self._cache.get(constant_rows(self.values()))
        from ...core import constants_group as cg

        params = self.group.parameters_all_dict
        return self._cache.get(constant_rows(self.values(), params,
                                             cg.vectors_state(self.group)))

    def parameter_columns(self) -> List[dict]:
        """The spec's columns; *Link* only while some constant is linked (it is sparse)."""
        section = next(s for s in load_spec("parameters")["sections"]
                       if s.get("key") == "data_table")
        columns = section["options"]["columns"]
        if any(r.get("link") for r in self.parameter_rows()):
            return columns
        return [c for c in columns if c["key"] != "link"]

    def _parameter(self, record):
        if not isinstance(record, dict):
            return None
        name = record.get("param", record.get("name"))
        return self.group.parameters_all_dict.get(name) if self.group is not None and name \
            else None

    def _vector_of(self, record) -> str:
        """The vector a parent row stands for (``""`` for any other row)."""
        from .constant_rows import parent_key

        if not isinstance(record, dict) or record.get("param"):
            return ""
        key = str(record.get("key", ""))
        return key[:-2] if key.endswith("[]") and key == parent_key(key[:-2]) else ""

    def cell_editable(self, record, key) -> bool:
        """A vector's parent row takes only *Fixed* (for all its elements)."""
        if self._vector_of(record):
            return key == "fixed"
        if self.group is None:
            return key == "value"
        parameter = self._parameter(record)
        return not (key == "value" and getattr(parameter, "is_linked", False))

    def edit_parameter(self, record, key, value) -> None:
        vector = self._vector_of(record)
        if vector:
            if key == "fixed" and self.group is not None:
                from ...core import constants_group as cg

                for _label, parameter in cg.vector_elements(self.group, vector):
                    parameter.fixed = bool(value)
                self.changed()
            return
        if self.group is None:
            number = _number(value)
            if key == "value" and number is not None:
                self.mapping[record.get("param") or record["name"]] = number
                self.changed()
            return
        super().edit_parameter(record, key, value)

    # -- vectors --------------------------------------------------------------
    def parameter_menu(self, record, key, where) -> None:
        """A vector's own menu on its parent row; *Make vector…* on a scalar."""
        vector = self._vector_of(record)
        if vector:
            values = [r["value"] for r in self.parameter_rows()
                      if r.get("parent") == record.get("key") and r.get("name") != "(global)"]
            entries = [
                ("Copy values", lambda: self.feature.copy_text(
                    "\t".join(repr(float(v)) for v in values))),
                ("Paste values", lambda: self.paste_vector(vector)),
                ("Populations…", lambda: self.feature.open_window(
                    VectorDialog(self.feature, self, vector))),
                ("Make scalar", lambda: self.make_scalar(vector)),
            ]
            self.feature.open_menu(entries, where)
            return
        parameter = self._parameter(record)
        if parameter is None:
            return
        from ...core.vector_constants import split_element

        if self.group is None or record.get("parent"):
            super().parameter_menu(record, key, where)
            return
        name = parameter.name
        if split_element(name) is not None:
            super().parameter_menu(record, key, where)
            return
        entries = [("Copy", lambda: self.feature.copy_text(repr(float(parameter.value)))),
                   ("Paste", lambda: self._paste(parameter)),
                   ("Link…", lambda: self.feature.open_link(parameter, self))]
        if getattr(parameter, "is_linked", False):
            entries.append(("Unlink", lambda: self._unlink(parameter)))
        entries.append(("Make vector…", lambda: self.feature.open_window(
            VectorDialog(self.feature, self, name))))
        self.feature.open_menu(entries, where)

    def column_options(self) -> List[str]:
        """The burst columns a vector can pick its populations by."""
        from ...core.vector_constants import DEFAULT_COLUMN

        model = self.feature.app.model
        names = list(model.parameter_names) if model.has_data else []
        return [DEFAULT_COLUMN] + [n for n in names if n != DEFAULT_COLUMN]

    def set_vector(self, name: str, values: Sequence[float], populations: Sequence[str],
                   uncertainties: Optional[Sequence[float]] = None, *,
                   default: Optional[float] = None, column: Optional[str] = None,
                   probabilities: Optional[Dict[str, str]] = None,
                   codes: Optional[Dict[str, float]] = None, expand: bool = True) -> None:
        """Make *name* a per-population vector and re-derive what reads it.

        The API a calibration uses (see :func:`ndxplorer.core.constants_group.set_vector`):
        *values* and *uncertainties* one per population, *default* the global
        value (a burst in no population), *column* the burst column that picks
        the population, *probabilities* ``label -> column`` of per-burst
        assignment probabilities (then a burst gets the weighted mix), *codes*
        ``label -> value in column``.
        """
        from ...core.vector_constants import element_name

        if self.group is not None:
            from ...core import constants_group as cg

            cg.set_vector(self.group, name, values, populations, uncertainties=uncertainties,
                          default=default, column=column, probabilities=probabilities,
                          codes=codes)
        else:
            for label, value in zip(populations, values):
                self.mapping[element_name(name, str(label))] = float(value)
            if default is not None or name not in self.mapping:
                self.mapping[name] = float(default if default is not None else
                                           sum(values) / max(len(values), 1))
        if expand:
            from .constant_rows import parent_key

            self.expanded.add(parent_key(name))
        self.changed()

    def make_vector(self, name: str, populations: Sequence[str],
                    column: Optional[str] = None) -> None:
        """A scalar becomes a vector, every element at the scalar's value."""
        value = float(self.values()[name])
        self.set_vector(name, [value] * len(populations), populations, default=value,
                        column=column)

    def make_scalar(self, name: str) -> None:
        """A vector becomes its global value: the elements go."""
        from ...core.vector_constants import split_element

        if self.group is not None:
            from ...core import constants_group as cg

            cg.to_scalar(self.group, name)
        else:
            for key in [k for k in self.mapping if (split_element(k) or ("",))[0] == name]:
                del self.mapping[key]
        self.changed()

    def paste_vector(self, name: str) -> None:
        """Paste one number per population (tabs, commas or spaces between)."""
        from ...core.vector_constants import element_name

        text = str(self.feature.clipboard).replace(",", " ").split()
        numbers = [_number(t) for t in text]
        labels = [r["name"] for r in self.parameter_rows()
                  if r.get("parent") == f"{name}[]" and r.get("name") != "(global)"]
        if len(numbers) != len(labels) or any(n is None for n in numbers):
            self.feature.app.message = ("Paste values",
                                        f"{name} has {len(labels)} populations; the clipboard "
                                        f"holds {len(numbers)} number(s).")
            return
        for label, number in zip(labels, numbers):
            parameter = self._parameter({"param": element_name(name, label)})
            if parameter is not None and not getattr(parameter, "is_linked", False):
                parameter.value = number
            elif self.group is None:
                self.mapping[element_name(name, label)] = number
        self.changed()

    def _axes_token(self) -> Any:
        """What the vectors' label and probability columns hold (checked twice a second).

        Re-clustering rewrites ``Cluster Label``; what reads a vector must follow.
        """
        import time

        now = time.monotonic()
        if now - self._axis_checked < 0.5:
            return self._axis_token
        self._axis_checked = now
        from ...core.equation_graph import constant_vectors

        model = self.feature.app.model
        vectors = constant_vectors(self.mapping) if model.has_data else {}
        parts = []
        for name, vector in vectors.items():
            for column in vector.axis.columns():
                values = model.source.column_values(column)
                parts.append((name, column, None if values is None else
                              hash(np.ascontiguousarray(values).tobytes())))
        return tuple(parts)

    # -- following the data manager ------------------------------------------
    def install(self) -> None:
        """Make the data manager read these constants (again, after a Clear)."""
        manager = self.feature.app.model.manager
        if manager.constants is not self.mapping:
            if isinstance(manager.constants, dict) and manager.constants \
                    and self.group is not None:
                from ...core import constants_group as cg

                # Settings > Load settings wrote into the manager's dict.
                cg.apply_value_dict(self.group, {k: v for k, v in manager.constants.items()
                                                 if self.values().get(k) != float(v)})
            manager.constants = self.mapping

    def changed(self) -> None:
        self.poll()

    def poll(self) -> bool:
        """Re-derive what a changed constant feeds; ``True`` if anything moved.

        Called every frame: an edit here, a fit moving a linked master, a
        curve fit writing a value -- they all show up as a difference from the
        last snapshot, and all of a frame's changes cost one recompute.
        """
        values = self.values()
        changed = {k for k, v in values.items() if self._snapshot.get(k) != v}
        changed |= {k for k in self._snapshot if k not in values}
        axes = self._axes_token()
        if axes != self._axis_token:
            changed |= {name for name, _column, _hash in axes or ()}
            changed |= {name for name, _column, _hash in self._axis_token or ()}
            self._axis_token = axes
        if not changed:
            return False
        self._snapshot = dict(values)
        model = self.feature.app.model
        if model.has_data:
            from ...analysis.curve_fit_setup import recompute_for_constants

            try:
                recompute_for_constants(model.source, self.mapping, model.manager.equations,
                                        changed)
            except Exception as exc:  # noqa: BLE001 - shown, the window goes on
                self.feature.app.show_status(f"Recompute failed: {exc}") \
                    if hasattr(self.feature.app, "show_status") else None
                logger.warning("Recompute after a constant changed failed: %s", exc)
            model.invalidate()
        return True

    # -- actions ------------------------------------------------------------
    def save_parameters(self) -> None:
        """Save: the constants, with bounds and fixed, into the settings folder."""
        from ...settings import get_settings_path

        model = self.feature.app.model
        name = model.bundle.settings.get("constants") or "mfd.constants.json"
        path = get_settings_path() / pathlib.Path(name).name
        if self.group is not None:
            from ...core import constants_group as cg

            payload = cg.group_state(self.group)
        else:
            payload = dict(self.mapping)
        try:
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(payload, handle, indent=4)
        except OSError as exc:
            self.feature.app.message = ("Save parameters", f"Could not write {path}:\n{exc}")
            return
        self.feature.status(f"Parameters saved to {path}")

    def add_parameter(self) -> None:
        self.feature.open_window(AddParameterDialog(self.feature, self))

    def add(self, name: str, value: float, populations: Optional[Sequence[str]] = None,
            column: Optional[str] = None) -> Optional[str]:
        """Append a constant (a vector with *populations*); returns why not, or ``None``."""
        from ...core.vector_constants import split_element

        name = str(name).strip()
        if not name:
            return "A parameter needs a name."
        if name in dict(self.mapping):
            return f"A parameter named '{name}' already exists."
        if populations is not None:
            if not populations:
                return "A vector needs its populations: how many, or their names."
            if split_element(name) is not None:
                return "A vector's name cannot end in [...]."
            self.set_vector(name, [float(value)] * len(populations), list(populations),
                            default=float(value), column=column)
            return None
        if self.group is not None:
            from ...core import constants_group as cg

            cg.apply_value_dict(self.group, {name: float(value)})
        else:
            self.mapping[name] = float(value)
        self.changed()
        return None


# ------------------------------------------------------------------ dialogs
class Dialog:
    """A dialog of this feature: a spec drawn in an :class:`emtk.dialog_window.DialogWindow`."""

    spec_name = ""
    size = (460.0, 220.0)
    modal = True

    def __init__(self, feature: "OverlaysFeature", title: str) -> None:
        from emtk.dialog_window import DialogWindow
        from emtk.view_form import FormState

        self.feature = feature
        self.title = title
        self.window = DialogWindow(title, size=self.size, key=f"overlays-{self.spec_name}")
        self.window.show()
        self.form = FormState()
        self.done = False

    @property
    def box(self):
        return self.window.box

    def spec(self) -> dict:
        return load_spec(self.spec_name)

    def enabled(self, _name: str) -> bool:
        return True

    def draw(self, frame) -> None:
        from emtk.view_form import draw_form

        pressed = self.window.begin(frame)
        try:
            draw_form(self.spec(), self, self.form, titles=False)
        finally:
            self.window.end()
        if pressed == "close":
            self.close()

    def close(self) -> None:
        self.done = True
        self.window.hide()

    def cancel(self) -> None:
        self.close()


class AddParameterDialog(Dialog):
    """Parameters > Add parameter: a name, then a value."""

    spec_name = "add_parameter"
    size = (380.0, 200.0)

    def __init__(self, feature, panel: ConstantsPanel) -> None:
        super().__init__(feature, "Add parameter")
        self.panel = panel
        self.step = "name"
        self.name = ""
        self.value = 0.0
        #: "Scalar", or "Vector": one value per population.
        self.kind = "Scalar"
        self.populations = "2"
        self.column = panel.column_options()[0]

    @property
    def vector_hidden(self) -> bool:
        return self.step != "value" or self.kind != "Vector"

    def column_options(self) -> List[str]:
        return self.panel.column_options()

    def spec(self) -> dict:
        return _fill(load_spec(self.spec_name), value_label=f"Value for '{self.name}':")

    def ok(self) -> None:
        if self.step == "name":
            name = self.name.strip()
            if not name:
                self.close()          # Qt: an empty name is a cancel
                return
            if name in dict(self.panel.mapping):
                self.feature.app.message = ("Add parameter",
                                            f"A parameter named '{name}' already exists.")
                self.close()
                return
            self.name = name
            self.step = "value"
            return
        from .constant_rows import parse_populations

        populations = parse_populations(self.populations) if self.kind == "Vector" else None
        problem = self.panel.add(self.name, float(self.value), populations, self.column)
        if problem:
            self.feature.app.message = ("Add parameter", problem)
        self.close()


class VectorDialog(Dialog):
    """Make vector… / Populations…: a constant's populations and the column picking them."""

    spec_name = "vector"
    size = (400.0, 170.0)

    def __init__(self, feature, panel: ConstantsPanel, name: str) -> None:
        from ...core.vector_constants import DEFAULT_COLUMN

        self.panel = panel
        self.name = name
        self.is_vector = any(r.get("key") == f"{name}[]" for r in panel.parameter_rows())
        super().__init__(feature, f"Populations of {name}" if self.is_vector
                         else f"Make {name} a vector")
        labels = [r["name"] for r in panel.parameter_rows()
                  if r.get("parent") == f"{name}[]" and r.get("name") != "(global)"]
        self.populations = ", ".join(labels) if labels else "2"
        column = DEFAULT_COLUMN
        if self.is_vector and panel.group is not None:
            from ...core import constants_group as cg

            column = cg.vector_axis(panel.group, name).column
        self.column = column

    @property
    def hint(self) -> str:
        return (f"One value of {self.name} per population; a burst takes its population's "
                "value, and a burst in no population the global one.")

    def column_options(self) -> List[str]:
        options = self.panel.column_options()
        return options if self.column in options else [self.column] + options

    def ok(self) -> None:
        from .constant_rows import parse_populations

        labels = parse_populations(self.populations)
        if not labels:
            self.feature.app.message = ("Populations", "Give how many populations, or their "
                                                       "names (HF, LF).")
            return
        if not self.is_vector:
            self.panel.make_vector(self.name, labels, self.column)
        else:
            values = self.panel.values()
            from ...core.vector_constants import element_name

            default = values.get(self.name)
            numbers = [values.get(element_name(self.name, l), default) for l in labels]
            fallback = default if default is not None else sum(
                n for n in numbers if n is not None) / max(sum(n is not None for n in numbers), 1)
            self.panel.set_vector(self.name, [fallback if n is None else n for n in numbers],
                                  labels, column=self.column)
        self.close()


class PromptDialog(Dialog):
    """One line of text, then a callback (Filter this column…)."""

    spec_name = "prompt"
    size = (360.0, 130.0)

    def __init__(self, feature, title: str, label: str, text: str,
                 on_ok: Callable[[str], None]) -> None:
        super().__init__(feature, title)
        self.label = label
        self.text = text
        self.on_ok = on_ok

    def spec(self) -> dict:
        return _fill(load_spec(self.spec_name), label=self.label)

    def ok(self) -> None:
        self.on_ok(self.text)
        self.close()


class LinkDialog(Dialog):
    """Link a parameter to one of every registered group's parameters."""

    spec_name = "link"
    size = (520.0, 400.0)

    def __init__(self, feature, parameter, panel: _ParameterPanel) -> None:
        super().__init__(feature, f"Link {parameter.name}")
        self.parameter = parameter
        self.panel = panel
        self.picked: Optional[dict] = None
        self._targets = self._collect()

    def _collect(self) -> List[dict]:
        rows = []
        try:
            from chisurf.core.parameter_group_registry import iter_registered_parameter_groups
        except Exception:  # noqa: BLE001
            return rows
        for owner_id, label, group in iter_registered_parameter_groups():
            for p in getattr(group, "parameters_all", []):
                if p is self.parameter:
                    continue
                rows.append({"id": f"{owner_id}:{p.name}", "owner": str(label),
                             "name": str(p.name), "value": float(p.value), "_p": p})
        return rows

    @property
    def hint(self) -> str:
        if not self._targets:
            return "No other parameters are open to link to (a fit, a curve or the Gaussians)."
        return (f"{self.parameter.name} will follow the parameter you pick "
                "(double-click, or select and Link).")

    def targets(self) -> List[dict]:
        return self._targets

    def pick(self, record) -> None:
        self.picked = record if isinstance(record, dict) else None

    def link(self, record) -> None:
        self.pick(record)
        self.link_selected()

    def link_selected(self) -> None:
        if self.picked is None:
            return
        try:
            self.parameter.link = self.picked["_p"]
        except Exception as exc:  # noqa: BLE001 - a cycle, a type the link refuses
            self.feature.app.message = ("Link", f"Could not link: {exc}")
            return
        self.panel.changed()
        self.close()


# -------------------------------------------------------------------- curves
class CurvePanel(_ParameterPanel):
    """One overlay curve's group in the Overlays tab."""

    def __init__(self, feature: "OverlaysFeature", curve) -> None:
        from emtk.view_form import FormState

        super().__init__(feature)
        self.curve = curve
        self.form = FormState()

    # what the spec binds to
    @property
    def visible(self) -> bool:
        return self.curve.visible

    @visible.setter
    def visible(self, value: bool) -> None:
        self.curve.visible = bool(value)

    @property
    def text(self) -> str:
        return self.curve.text

    @text.setter
    def text(self, value: str) -> None:
        if str(value) != self.curve.text:
            self.curve.set_text(str(value))

    @property
    def filled(self) -> str:
        try:
            return self.curve.filled
        except Exception as exc:  # noqa: BLE001
            return f"Error: {exc}"

    @property
    def color(self) -> str:
        return self.curve.color

    @color.setter
    def color(self, value: str) -> None:
        self.curve.color = str(value)

    @property
    def has_error(self) -> bool:
        return bool(self.curve.error)

    def error_text(self) -> str:
        return self.curve.error

    def parameters(self) -> list:
        return list(self.curve.group.parameters_all)

    def fit(self) -> None:
        self.feature.open_fit(self.curve)

    def delete(self) -> None:
        self.feature.overlays.remove(self.curve)

    def spec(self) -> dict:
        curve = self.curve
        base = load_spec("curve")
        spec = _fill(base, title=curve.title,
                     filled_label="Filled Function:" if curve.is_function else "Filled: y =")
        marker = "function" if curve.is_function else "equation"
        other = "equation" if curve.is_function else "function"
        spec["sections"] = [s for s in spec["sections"] if not s.get(other)
                            or s.get(marker)]
        return spec


class OverlaysPanel:
    """The Overlays tab: the equation list, the curves, the point count, CSV."""

    def __init__(self, feature: "OverlaysFeature") -> None:
        from emtk.view_form import FormState

        from ...core.overlay_curves import CUSTOM_EQUATION, load_predefined_equations

        self.feature = feature
        self.form = FormState()
        self.form.custom["overlay_curves"] = self._draw_curves
        self.predefined = load_predefined_equations()
        self.equation_choice = CUSTOM_EQUATION
        self.num_points = 500
        self.panels: List[CurvePanel] = []

    def enabled(self, name: str) -> bool:
        if name in ("add_curve",):
            return _has_chisurf()
        if name == "save_csv":
            return any(p.curve.visible for p in self.panels)
        return True

    def equation_options(self) -> List[str]:
        from ...core.overlay_curves import CUSTOM_EQUATION

        return [CUSTOM_EQUATION] + [str(e["name"]) for e in self.predefined]

    @property
    def curves(self) -> list:
        return [p.curve for p in self.panels]

    def add_curve(self):
        """Add Curve: the chosen predefined curve, or a custom ``y = x``."""
        from ...core.overlay_curves import CUSTOM_EQUATION, OverlayCurve, next_curve_title

        titles = [c.title for c in self.curves]
        entry = next((e for e in self.predefined if e["name"] == self.equation_choice), None)
        if entry is None:
            curve = OverlayCurve(next_curve_title(CUSTOM_EQUATION, titles), "x")
        else:
            curve = OverlayCurve.from_entry(entry, next_curve_title(entry["name"], titles))
        curve.register()
        self.panels.append(CurvePanel(self.feature, curve))
        return curve

    def remove(self, curve) -> None:
        curve.unregister()
        for panel in self.panels:
            if panel.curve is curve:
                self.feature.unregister_form(panel.form)
        self.panels = [p for p in self.panels if p.curve is not curve]

    def clear(self) -> None:
        for panel in self.panels:
            panel.curve.unregister()
        self.panels = []

    def save_csv(self) -> None:
        """Save CSV: the visible curves, as drawn over the displayed axes."""
        from ...core.overlay_curves import write_curves_csv

        model = self.feature.app.model
        hist = model.histograms
        if hist is None:
            self.feature.app.message = ("Save Overlays",
                                        "No overlay data available yet. Create/update overlays first.")
            return
        visible = [c for c in self.curves if c.visible]
        if not visible:
            self.feature.app.message = ("Save Overlays", "No visible curves to save.")
            return
        data = [(c.title, *c.points(self.num_points, hist.x_edges, hist.y_edges, model.x.log,
                                     model.y.log)) for c in visible]

        def write(path: str) -> None:
            try:
                write_curves_csv(path, data)
            except OSError as exc:
                self.feature.app.message = ("Save Overlays", f"Failed to save CSV:\n{exc}")
                return
            self.feature.status(f"Saved overlay curves to {path}")

        self.feature.ask_save("Save Overlay Curves", [("CSV Files", ["*.csv"])],
                              "overlays.csv", write)

    def _draw_curves(self, _section, _model, _state, _width) -> None:
        import emtk
        from emtk.view_form import draw_form

        if not _has_chisurf():
            emtk.text_wrapped(_no_chisurf_text())
            return
        for panel in list(self.panels):
            emtk.separator()
            draw_form(panel.spec(), panel, panel.form, titles=False)
            self.feature.register_form(panel.form)


# ------------------------------------------------------------------ curve fit
class CurveFitDialog(Dialog):
    """Fit curve to data: target, reduction, scan, the parameters, Fit."""

    spec_name = "curve_fit"
    size = (520.0, 560.0)

    def __init__(self, feature, curve) -> None:
        from ...analysis.curve_fit_setup import REDUCTIONS, TARGETS

        super().__init__(feature, "Fit curve to data")
        self.curve = curve
        self._target = TARGETS[0][0]
        self._reduction = REDUCTIONS[0][0]
        self.scan = True
        self.cf = None
        self.status_text_value = ""
        self.running = False
        self.step_count = 0
        self._cancel = False
        self._thread: Optional[threading.Thread] = None
        self._result = None
        self._curve_cache, self._data_cache = _RowCache(), _RowCache()
        self.rebuild()

    # -- choices -------------------------------------------------------------
    def target_options(self):
        from ...analysis.curve_fit_setup import TARGETS

        return [list(t) for t in TARGETS]

    def reduction_options(self):
        from ...analysis.curve_fit_setup import REDUCTIONS

        return [list(r) for r in REDUCTIONS]

    @property
    def target(self) -> str:
        return self._target

    @target.setter
    def target(self, value) -> None:
        if value != self._target:
            self._target = str(value)
            self.rebuild()

    @property
    def reduction(self) -> str:
        return self._reduction

    @reduction.setter
    def reduction(self, value) -> None:
        if value != self._reduction:
            self._reduction = str(value)
            self.rebuild()

    def enabled(self, name: str) -> bool:
        if name == "run_fit":
            return self.cf is not None and not self.running
        if name in ("target", "reduction", "scan", "close"):
            return not self.running
        return True

    def rebuild(self) -> None:
        """Build the fit for the chosen target; say why when it cannot be."""
        from ...analysis.curve_fit import CurveFitError
        from ...analysis.curve_fit_setup import build_curve_fit_for

        try:
            self.cf = build_curve_fit_for(self.feature.fit_host, self.curve, self._target,
                                          self._reduction)
            self.status_text_value = ""
        except CurveFitError as exc:
            self.cf, self.status_text_value = None, str(exc)
        except Exception as exc:  # noqa: BLE001
            self.cf, self.status_text_value = None, f"cannot fit: {exc}"

    # -- tables ----------------------------------------------------------------
    def curve_rows(self):
        return self._curve_cache.get(parameter_records(self.cf.parameters if self.cf else []))

    def data_rows(self):
        return self._data_cache.get(parameter_records(
            getattr(self.cf, "data_parameters", []) if self.cf else []))

    @property
    def has_data_parameters(self) -> bool:
        return bool(self.cf is not None and getattr(self.cf, "data_parameters", []))

    def _edit(self, parameters, record, key, value) -> None:
        name = record.get("name") if isinstance(record, dict) else None
        parameter = next((p for p in parameters if p.name == name), None)
        if parameter is not None:
            edit_parameter(parameter, key, value)

    def edit_curve_parameter(self, record, key, value) -> None:
        if self.cf is not None:
            self._edit(self.cf.parameters, record, key, value)

    def edit_data_parameter(self, record, key, value) -> None:
        if self.cf is not None:
            self._edit(self.cf.data_parameters, record, key, value)

    # -- running ---------------------------------------------------------------
    def status_text(self) -> str:
        return self.status_text_value

    def progress_text(self) -> str:
        return f"fitting — the data is re-derived at every step… step {self.step_count}" \
            if self.cf is not None and self.cf.free_data_parameters() else \
            f"fitting… step {self.step_count}"

    def _step(self, index: int) -> bool:
        self.step_count = int(index)
        return not self._cancel

    def run_fit(self) -> None:
        """Fit: on a thread on a desktop, in the frame in a browser (no threads)."""
        if self.cf is None or self.running:
            return
        self.running, self._cancel, self.step_count, self._result = True, False, 0, None
        self.status_text_value = ""
        try:
            self.cf.set_progress(self._step)
        except AttributeError:
            pass

        def work():
            try:
                self._result = self.cf.run(scan=self.scan)
            except Exception as exc:  # noqa: BLE001 - reported in the status line
                self._result = exc

        if _in_browser():
            work()
            self._finish()
        else:
            self._thread = threading.Thread(target=work, name="ndx-curve-fit", daemon=True)
            self._thread.start()

    def cancel_fit(self) -> None:
        self._cancel = True

    def poll(self) -> None:
        if self.running and self._thread is not None and not self._thread.is_alive():
            self._thread = None
            self._finish()

    def wait(self, timeout: float = 60.0) -> None:
        """Block until a running fit ends (tests, the capture replay)."""
        if self._thread is not None:
            self._thread.join(timeout)
        self.poll()

    def _finish(self) -> None:
        from ...analysis.curve_fit_setup import result_text

        self.running = False
        try:
            self.cf.set_progress(None)
        except AttributeError:
            pass
        result = self._result
        if isinstance(result, Exception):
            self.status_text_value = f"fit failed: {result}"
            return
        if result is None:
            return
        message, failed = result_text(result)
        self.status_text_value = message
        if not failed:
            self.feature.fit_applied(self.curve, self.cf, result)

    def close(self) -> None:
        if self.running:
            self._cancel = True
            self.wait()
        super().close()

    def draw(self, frame) -> None:
        self.poll()
        super().draw(frame)


# ------------------------------------------------------------------ equations
class EquationsPanel:
    """The Equations tab: rows, validation, Apply, load and save, names."""

    def __init__(self, feature: "OverlaysFeature") -> None:
        from emtk.view_form import FormState

        from ...core.equation_table import EquationTable

        self.feature = feature
        self.form = FormState()
        self.table = EquationTable(feature.app.model.manager.equations)
        self._equations_id = id(feature.app.model.manager.equations)
        self.selected: Optional[int] = None
        self.validate()

    def enabled(self, name: str) -> bool:
        if name == "remove_equation":
            return self.selected is not None
        return True

    def _known(self) -> Tuple[List[str], List[str]]:
        model = self.feature.app.model
        return model.parameter_names, list(dict(model.manager.constants))

    def validate(self) -> int:
        columns, constants = self._known()
        return self.table.validate(columns, constants)

    def follow(self) -> None:
        """Settings > Load settings replaced the equations: show those."""
        equations = self.feature.app.model.manager.equations
        if id(equations) != self._equations_id:
            self._equations_id = id(equations)
            self.table.set_equations(equations)
            self.validate()

    # the table
    def rows(self) -> List[dict]:
        return self.table.rows

    def edit_row(self, record, key, value) -> None:
        index = self._index(record)
        if index is not None:
            self.table.edit(index, key, value)
            self.validate()

    def select_row(self, record) -> None:
        self.selected = self._index(record)

    def delete_row(self, record) -> None:
        index = self._index(record)
        if index is not None:
            self.table.remove(index)
            self.selected = None
            self.validate()

    def _index(self, record) -> Optional[int]:
        for i, row in enumerate(self.table.rows):
            if row is record:
                return i
        return None

    def preview_text(self) -> str:
        """The selected equation, written out."""
        if self.selected is None or not 0 <= self.selected < len(self.table.rows):
            return "Select an equation to see it here."
        row = self.table.rows[self.selected]
        return f"{row['output']} = {row['expression']}"

    def status_text(self) -> str:
        return self.table.status

    # the buttons
    def add_equation(self) -> None:
        self.selected = self.table.add()
        self.validate()

    def remove_equation(self) -> None:
        if self.selected is not None:
            self.table.remove(self.selected)
            self.selected = None
            self.validate()

    def show_names(self) -> None:
        self.feature.open_window(NamesDialog(self.feature, self))

    def insert(self, token: str) -> None:
        self.selected = self.table.insert(self.selected, token)
        self.validate()

    def apply_equations(self) -> None:
        """Apply: validate every row and recompute every derived column."""
        bad = self.validate()
        model = self.feature.app.model
        equations = self.table.equations()
        model.manager.equations = equations
        self._equations_id = id(equations)
        if model.has_data:
            try:
                model.source.compute_columns(constants=model.manager.constants,
                                             equations=equations)
            except Exception as exc:  # noqa: BLE001
                self.feature.app.message = ("Equations", f"Recompute failed:\n{exc}")
                return
            model.invalidate()
            self.feature.app.data_changed()
        self.feature.status(self.table.status if bad else "Equations applied")

    def load_equations(self) -> None:
        def load(paths) -> None:
            path = paths[0] if isinstance(paths, (list, tuple)) else paths
            try:
                self.table.load(path)
            except Exception as exc:  # noqa: BLE001
                self.feature.app.message = ("Equations", f"Could not load:\n{exc}")
                return
            self.selected = None
            self.validate()

        self.feature.ask_open("Open equations", [("YAML", ["*.yaml", "*.yml"])], load)

    def save_equations_file(self) -> None:
        def save(path: str) -> None:
            try:
                self.table.save(path)
            except OSError as exc:
                self.feature.app.message = ("Equations", f"Could not save:\n{exc}")
                return
            self.feature.status(f"Equations saved to {path}")

        self.feature.ask_save("Save equations", [("YAML", ["*.yaml", "*.yml"])],
                              "mfd.equations.yaml", save)


class NamesDialog(Dialog):
    """Names & functions: the constants, columns and functions an equation may use."""

    spec_name = "names"
    size = (400.0, 470.0)
    modal = False

    def __init__(self, feature, panel: EquationsPanel) -> None:
        super().__init__(feature, "Names & functions")
        self.panel = panel
        columns, constants = panel._known()
        outputs = [r["output"] for r in panel.table.rows if r.get("output")]
        self._rows = []
        for kind, name in panel.table.names(columns, constants, outputs):
            label = f"— {name} —" if kind == "header" else (
                f"{name}()" if kind == "function" else name)
            self._rows.append({"label": label, "kind": kind, "name": name})

    def rows(self) -> List[dict]:
        return self._rows

    def insert(self, record) -> None:
        if not isinstance(record, dict) or record["kind"] == "header":
            return
        token = f"{record['name']}(" if record["kind"] == "function" else f"'{record['name']}'"
        self.panel.insert(token)


# -------------------------------------------------------------- table editor
class StoreEditorDialog(Dialog):
    """The Table Editor: the data's columns on a copy; Apply writes them back."""

    spec_name = "store_editor"
    size = (900.0, 600.0)

    def __init__(self, feature) -> None:
        super().__init__(feature, "Table Editor")
        self.source = feature.app.model.source
        self.working = self.source.copy()
        self.hidden: set = set()
        self.hide_empty = False
        self.colour_cells = False
        self.colour_table = False
        self._arrays: Optional[dict] = None

    # -- the table -------------------------------------------------------------
    def arrays(self) -> dict:
        if self._arrays is None:
            self._arrays = {name: self.working.column_items(i)
                            for i, name in enumerate(self.working.parameter_names)}
        return self._arrays

    def _empty(self, name: str) -> bool:
        values = self.arrays()[name]
        if values.dtype.kind == "f":
            return not np.isfinite(values).any()
        if values.dtype.kind in "OUS":
            return all(v is None or str(v) == "" for v in values)
        return values.size == 0

    def columns(self) -> List[dict]:
        return [{"key": name, "title": name,
                 "visible": name not in self.hidden and not (self.hide_empty and self._empty(name))}
                for name in self.arrays()]

    def colour_mode(self) -> Optional[str]:
        if not self.colour_cells:
            return None
        return "table" if self.colour_table else "column"

    def status_text(self) -> str:
        """``"N rows × M columns"`` (``"n / N rows"`` while filtered)."""
        control = self._control()
        total = len(next(iter(self.arrays().values()), ()))
        shown_cols = sum(1 for c in self.columns() if c["visible"])
        if control is not None:
            shown = len(control.order())
            if shown != total:
                return f"{shown:,} / {total:,} rows × {shown_cols} columns"
        return f"{total:,} rows × {shown_cols} columns"

    def _control(self):
        binding = self.form.tables.get("arrays")
        return binding.control if binding is not None else None

    def edit_cell(self, index, key, value) -> None:
        """A cell changed: into the copy (staged until Apply)."""
        column = self.working.column_index(key)
        if column < 0 or not isinstance(index, int):
            return
        values = np.array(self.working.column_items(column), copy=True)
        try:
            values[index] = value
        except (TypeError, ValueError):
            return
        self.working.set_column(key, values)
        self._arrays = None

    # -- the menu --------------------------------------------------------------
    def cell_menu(self, index, key, where) -> None:
        entries = [
            ("Copy", lambda: self.copy(headers=False)),
            ("Copy with headers", lambda: self.copy(headers=True)),
            ("Paste", lambda: self.paste(index, key)),
            ("Export as CSV…", self.export_csv),
            ("Select all", self.select_all),
        ]
        if key is not None:
            entries += [
                ("Filter this column…", lambda: self.filter_column(key)),
                ("Hide this column", lambda: self.hidden.add(key)),
            ]
        entries.append(("Resize columns to contents", self.fit_columns))
        self.feature.open_menu(entries, where)

    def _selected_rows(self) -> List[int]:
        control = self._control()
        if control is None:
            return []
        return control.selected_indices()

    def _visible_names(self) -> List[str]:
        return [c["key"] for c in self.columns() if c["visible"]]

    def _csv(self, rows: Sequence[int], headers: bool, sep: str = "\t") -> str:
        names = self._visible_names()
        arrays = self.arrays()
        lines = [sep.join(names)] if headers else []
        for i in rows:
            lines.append(sep.join(_cell_text(arrays[n][i]) for n in names))
        return "\n".join(lines)

    def copy(self, headers: bool) -> None:
        self.feature.copy_text(self._csv(self._selected_rows(), headers))

    def paste(self, index, key) -> None:
        """Paste tab-separated values from the clipboard, from this cell rightwards and down."""
        text = self.feature.clipboard
        if not text or not isinstance(index, int) or key is None:
            return
        names = self._visible_names()
        control = self._control()
        order = control.order() if control is not None else list(range(index + 1))
        if key not in names or index not in order:
            return
        start_col, start_row = names.index(key), order.index(index)
        for r, line in enumerate(text.splitlines()):
            if start_row + r >= len(order):
                break
            for c, cell in enumerate(line.split("\t")):
                if start_col + c >= len(names):
                    break
                name = names[start_col + c]
                values = self.arrays()[name]
                value: Any = cell
                if values.dtype.kind in "fiu":
                    value = _number(cell)
                    if value is None:
                        continue
                self.edit_cell(order[start_row + r], name, value)

    def select_all(self) -> None:
        control = self._control()
        if control is not None:
            control.select_all()

    def filter_column(self, key: str) -> None:
        control = self._control()
        current = control.column_filters.get(key, "") if control is not None else ""

        def apply(text: str) -> None:
            if control is not None:
                if text.strip():
                    control.column_filters[key] = text
                else:
                    control.column_filters.pop(key, None)

        self.feature.open_window(PromptDialog(self.feature, "Filter this column",
                                              f"Rows whose '{key}' contains:", current, apply),
                                 stack=True)

    def fit_columns(self) -> None:
        control = self._control()
        if control is not None:
            control.fit_columns()

    def export_csv(self) -> None:
        control = self._control()
        order = control.order() if control is not None else range(
            len(next(iter(self.arrays().values()), ())))
        text = self._csv(list(order), headers=True, sep=",")

        def write(path: str) -> None:
            try:
                with open(path, "w", encoding="utf-8") as handle:
                    handle.write(text + "\n")
            except OSError as exc:
                self.feature.app.message = ("Export as CSV", f"Could not write {path}:\n{exc}")
                return
            self.feature.status(f"Exported to {path}")

        self.feature.ask_save("Export as CSV", [("CSV files", ["*.csv"])], "table.csv", write)

    def choose_columns(self) -> None:
        self.feature.open_window(ColumnsDialog(self.feature, self), stack=True)

    # -- the buttons -----------------------------------------------------------
    def reset(self) -> None:
        self.working = self.source.copy()
        self._arrays = None

    def apply(self) -> None:
        from ...core.store_edits import apply_edits

        written = apply_edits(self.source, self.working)
        self.close()
        if written:
            model = self.feature.app.model
            model.invalidate()
            self.feature.app.data_changed()
            self.feature.status(f"{len(written)} column(s) written")


def _cell_text(value) -> str:
    if isinstance(value, (float, np.floating)):
        return "" if not np.isfinite(value) else f"{float(value):.6g}"
    return str(value)


class ColumnsDialog(Dialog):
    """The Table Editor's column picker."""

    spec_name = "columns"
    size = (360.0, 440.0)

    def __init__(self, feature, editor: StoreEditorDialog) -> None:
        super().__init__(feature, "Columns")
        self.editor = editor
        self._cache = _RowCache()

    def rows(self) -> List[dict]:
        return self._cache.get([{"column": name, "shown": name not in self.editor.hidden}
                                for name in self.editor.arrays()])

    def edit(self, record, key, value) -> None:
        if key == "shown" and isinstance(record, dict):
            if value:
                self.editor.hidden.discard(record["column"])
            else:
                self.editor.hidden.add(record["column"])

    def show_all(self) -> None:
        self.editor.hidden.clear()

    def hide_all(self) -> None:
        self.editor.hidden = set(self.editor.arrays())


# ------------------------------------------------------------------ fit host
class ModelFitHost:
    """The emtk window as a :class:`~ndxplorer.analysis.curve_fit_setup.FitHost`."""

    def __init__(self, feature: "OverlaysFeature") -> None:
        self.feature = feature

    @property
    def model(self):
        return self.feature.app.model

    @property
    def constants(self):
        return self.feature.constants.mapping

    @property
    def constants_group(self):
        return self.feature.constants.group

    @property
    def equations(self):
        return self.model.manager.equations

    def histogram_2d(self):
        self.model.update()
        hist = self.model.histograms
        if hist is None:
            from ...analysis.curve_fit import CurveFitError

            raise CurveFitError("no 2-D histogram displayed")
        return hist.H, hist.x_edges, hist.y_edges

    def marginal(self, axis: str):
        self.model.update()
        hist = self.model.histograms
        if hist is None:
            raise ValueError("no histogram displayed")
        return hist.x if axis == "x" else hist.y

    def density(self, target: str) -> bool:
        return bool(self.model.axis(target).norm) if target in ("x", "y") else False

    def fit_data_reader(self):
        from ...analysis.curve_fit_setup import make_fit_data_reader

        model = self.model
        keep = model._keep_mask()
        rows = np.flatnonzero(keep) if keep is not None else np.arange(model.source.size)
        weight = model.weight_name if model.weight_enabled else None
        return make_fit_data_reader(model.source, rows, model.x.name, model.y.name, weight)

    def recompute_for_constants(self, changed, targets=None) -> None:
        from ...analysis.curve_fit_setup import recompute_for_constants

        recompute_for_constants(self.model.source, self.constants, self.equations, changed,
                                targets)


# ------------------------------------------------------------------- feature
class OverlaysFeature(Feature):
    """Parameters, Overlays and Equations tabs; the curve fit; the Table Editor."""

    name = "overlays"

    def __init__(self, app) -> None:
        super().__init__(app)
        self.constants = ConstantsPanel(self)
        self.overlays = OverlaysPanel(self)
        self.equations = EquationsPanel(self)
        self.fit_host = ModelFitHost(self)
        self.parameters_form = self.constants.form
        self.window: Optional[Dialog] = None
        #: A dialog over :attr:`window` (the column picker over the Table Editor).
        self.top: Optional[Dialog] = None
        self.clipboard = ""
        self._file_answers: List[str] = []
        self.constants.install()
        self.register_form(self.overlays.form)
        self.register_form(self.constants.form)
        self.register_form(self.equations.form)

    # -- the host's services ---------------------------------------------------
    def register_form(self, form) -> None:
        """Let the window find this form's fields by name (captures, tours)."""
        forms = self.app.forms
        if all(f is not form for f in forms.values()):
            forms[f"overlays:{id(form)}"] = form

    def unregister_form(self, form) -> None:
        self.app.forms.pop(f"overlays:{id(form)}", None)

    def status(self, text: str) -> None:
        show = getattr(self.app, "show_status", None)
        if callable(show):
            show(text)
        else:
            logger.info(text)

    def copy_text(self, text: str) -> None:
        """Copy: to this window's clipboard, and the system's where there is one."""
        self.clipboard = str(text)
        try:
            from emtk import clipboard

            clipboard.copy(self.clipboard)
        except Exception:  # noqa: BLE001 - the window's own copy still pastes
            pass

    def _file_service(self):
        return getattr(self.app, "io_service", None)

    def ask_save(self, title, filters, name, callback) -> None:
        if self._file_answers:
            callback(self._file_answers.pop(0))
            return
        service = self._file_service()
        if service is None:
            self.app.message = (title, "Saving files needs the io feature.")
            return
        service.ask_save(title, filters, name, callback)

    def ask_open(self, title, filters, callback) -> None:
        if self._file_answers:
            callback([self._file_answers.pop(0)])
            return
        service = self._file_service()
        if service is None:
            self.app.message = (title, "Opening files needs the io feature.")
            return
        service.ask_open(title, filters, callback)

    def open_window(self, dialog: Dialog, stack: bool = False) -> None:
        if stack and self.window is not None:
            self.top = dialog
        else:
            self.window = dialog
        self.register_form(dialog.form)

    def open_menu(self, entries: List[Tuple[str, Callable[[], Any]]], where) -> None:
        """A context menu at *where*: ``(label, action)`` rows, opened by the window."""
        from emtk.widgets.menus import MenuItem

        items = [MenuItem(label) for label, _ in entries]
        actions = {id(item): action for item, (_, action) in zip(items, entries)}
        self.app.open_menu(items, float(where[0]), float(where[1]),
                           lambda item: actions[id(item)]())

    # -- actions ---------------------------------------------------------------
    def actions(self) -> Dict[str, Callable[[], Any]]:
        return {
            "show_data": self.show_data,
            "toggle_parameters": lambda: self._toggle("Parameters"),
            "toggle_overlays": lambda: self._toggle("Overlays"),
            "toggle_equations": lambda: self._toggle("Equations"),
        }

    def available(self, action: str) -> Optional[bool]:
        if action in ("toggle_parameters", "toggle_overlays", "toggle_equations"):
            return True
        return None

    def fields(self):
        """``show_parameters`` / ``show_overlays`` / ``show_equations``: whether the
        window is open -- what the View menu's ticks read and a spec may set."""
        def field(title):
            def set_(value) -> None:
                if value:
                    self.app.docks.focus(title)
                else:
                    self.app.docks.hide(title)

            return (lambda: self.app.docks.is_visible(title), set_)

        return {f"show_{title.lower()}": field(title)
                for title in ("Parameters", "Overlays", "Equations")}

    def _toggle(self, title: str) -> None:
        """View > Parameters/Overlays/Equations: open the window on top, or put it away."""
        self.app.docks.toggle(title)

    def show_data(self) -> None:
        """The Data button: the Table Editor over a copy of the data."""
        model = self.app.model
        if not model.has_data:
            self.app.message = ("No Data", "No data loaded—nothing to show.")
            return
        self.open_window(StoreEditorDialog(self))

    def open_fit(self, curve) -> None:
        self.open_window(CurveFitDialog(self, curve))

    def open_link(self, parameter, panel) -> None:
        self.open_window(LinkDialog(self, parameter, panel), stack=True)

    def fit_last_curve(self) -> None:
        if self.overlays.panels:
            self.overlays.panels[-1].fit()

    def fit_applied(self, curve, cf, result) -> None:
        """A fit ended well: into the curve's own parameters, and the constants."""
        from ...analysis.curve_fit_setup import fitted_constants

        cf.write_back(curve.group)
        # A fitted curve parameter that names a constant moves the constant.
        fitted_constants(self.constants.group, result.params)
        self.constants.poll()
        logger.info("Curve fit: chi2r=%.4g, params=%s", result.chi2r, result.params)

    # -- tabs --------------------------------------------------------------------
    def windows(self) -> List[tuple]:
        # The Qt window's Equations dock exists but cannot be shown; here
        # View > Equations opens it.
        return [("left", "Parameters", self._draw_parameters),
                ("left", "Overlays", self._draw_overlays),
                ("left", "Equations", self._draw_equations, {"visible": False})]

    def _draw_parameters(self, _box) -> None:
        from emtk.view_form import draw_form

        draw_form(load_spec("parameters"), self.constants, self.constants.form, titles=False)

    def _draw_overlays(self, _box) -> None:
        from emtk.view_form import draw_form

        draw_form(load_spec("overlays"), self.overlays, self.overlays.form, titles=False)

    def _draw_equations(self, _box) -> None:
        from emtk.view_form import draw_form

        draw_form(load_spec("equations"), self.equations, self.equations.form, titles=False)

    # -- every frame ---------------------------------------------------------------
    def draw_windows(self) -> bool:
        self.constants.install()
        self.constants.poll()
        self.equations.follow()
        frame = self.app.box
        for attr in ("window", "top"):
            dialog = getattr(self, attr)
            if dialog is None:
                continue
            dialog.draw(frame)
            if dialog.done and getattr(self, attr) is dialog:
                setattr(self, attr, None)
                self.unregister_form(dialog.form)
        if self.window is None and self.top is not None:
            self.unregister_form(self.top.form)
            self.top = None
        return any(d is not None and d.modal for d in (self.window, self.top))

    def draw_plot(self, plot: str) -> None:
        if plot != "map":
            return
        model = self.app.model
        hist = model.histograms
        if hist is None or not self.overlays.panels:
            return
        from emtk import implot

        for i, panel in enumerate(self.overlays.panels):
            curve = panel.curve
            if not curve.visible:
                continue
            x, y = curve.points(self.overlays.num_points, hist.x_edges, hist.y_edges,
                                model.x.log, model.y.log)
            if x.size < 2:
                continue
            implot.plot_line(f"##overlay-curve-{i}", x, y,
                             spec={"line_color": _rgba(curve.color), "line_weight": 2.0})

    def on_data_changed(self) -> None:
        self.equations.validate()

    # -- capture replay ------------------------------------------------------------
    def capture_ops(self) -> Dict[str, Callable]:
        return {"tab": self._op_tab, "set": self._op_set, "click": self._op_click,
                "call": self._op_call, "trigger": self._op_trigger}

    def capture_targets(self) -> Dict[str, Callable]:
        return {
            "dialog": self._dialog_box,
            "widget:win.curve_overlay_widget.predefined_combo.view().window()": self._popup_box,
        }

    def _dialog_box(self, _replay):
        if self.app.message is not None:
            return None
        dialog = self.top or self.window
        return dialog.box if dialog is not None else None

    def _open_lists(self) -> list:
        """The choice lists emtk has up (a view_form combo draws its own)."""
        from emtk.overlays import open_panels

        return open_panels(self.app.storage)

    def _popup_box(self, _replay):
        popup = self.app.popup
        if popup is not None:
            return popup[0].panel_rect
        lists = self._open_lists()
        return lists[-1].panel_rect if lists else None

    def _op_tab(self, replay, step):
        title = step.get("title")
        if title not in ("Parameters", "Overlays", "Equations"):
            return False
        self.app.docks.focus(title)
        replay.settle()
        return True

    def _op_set(self, replay, step):
        attr = QT_WIDGETS.get(step.get("widget"))
        if attr != "equation_choice":
            return False
        replay.click_rect(self.overlays.form.rects["equation_choice"])
        replay.settle()
        popup = self.app.popup
        labels = self.overlays.equation_options()
        lists = self._open_lists()
        if popup is None and lists and step["value"] in labels:
            # the combo's own list (emtk.overlays): click the row
            rect = lists[-1].row_rect(labels.index(step["value"]))
            if rect is not None:
                replay.click_rect(rect)
            else:
                lists[-1].close()
                self.overlays.equation_choice = step["value"]
        elif popup is None or step["value"] not in labels:
            self.overlays.equation_choice = step["value"]
        else:
            items = popup[1]
            index = labels.index(step["value"])
            rows = dict((id(item), rect) for item, rect in getattr(popup[0], "_rows", []))
            rect = rows.get(id(items[index]))
            if rect is not None:
                replay.click_rect(rect)
            else:
                self.overlays.equation_choice = step["value"]
                self.app.popup = None
        replay.settle()
        return True

    def _op_click(self, replay, step):
        action = QT_WIDGETS.get(step.get("widget"))
        if action is None:
            return False
        forms = {"add_curve": self.overlays.form, "add_parameter": self.constants.form,
                 "show_names": self.equations.form}
        form = forms.get(action)
        if form is not None and action in form.rects:
            replay.click_rect(form.rects[action])
        elif action == "fit_last_curve" and self.overlays.panels:
            panel = self.overlays.panels[-1]
            if "fit" in panel.form.rects:
                replay.click_rect(panel.form.rects["fit"])
            else:
                panel.fit()
        elif action == "show_data":
            rect = self.app.control_rect("show_data")
            if rect is not None:
                replay.click_rect(rect)
            else:
                self.show_data()
        else:
            getattr(self, action, None) and getattr(self, action)()
        replay.settle(3)
        return True

    def _op_call(self, replay, step):
        code = str(step.get("code", ""))
        if "predefined_combo.showPopup()" in code:
            replay.click_rect(self.overlays.form.rects["equation_choice"])
            replay.settle()
            return True
        if "predefined_combo.hidePopup()" in code:
            if self.app.popup is not None:
                self.app.popup[0].close()
                self.app.popup = None
            for panel in self._open_lists():
                panel.close()
            replay.settle()
            return True
        if "dockWidget_Equations" in code:
            # The Qt harness forces the dead tab open; here View > Equations works.
            self.app.docks.focus("Equations")
            replay.settle()
            return True
        return False

    def _op_trigger(self, replay, step):
        if step.get("action") != "action_dock_Equations_view":
            return False
        replay.app.run_action("toggle_equations")
        replay.settle()
        return True


def _rgba(colour: str) -> tuple:
    text = str(colour).lstrip("#")
    try:
        r, g, b = (int(text[i:i + 2], 16) for i in (0, 2, 4))
    except ValueError:
        r, g, b = 255, 0, 0
    return (r, g, b, 255)


def create(app) -> OverlaysFeature:
    return OverlaysFeature(app)
