"""The one parameter table of the app: records, edits and the right-click menu.

The Parameters tab, the Gaussian Fit tab, every overlay curve and the curve-fit
dialog show :class:`~ndxplorer.core.parameters.Parameter` objects the same way:
a ``data_table`` section declared once (``views/parameter_table.view.json``)
over a :class:`ParameterTable`. A feature's spec says
``{"type": "parameter_table", "table": "<attribute>"}`` and :func:`expand`
puts the section there, its model names prefixed with the attribute
(``"gaussian_table.rows"``), so one form can hold several tables.

What every table does:

* columns sized to their contents; a shortened cell shows its whole text as a
  tooltip;
* **Lo**/**Hi** show a bound, or ``−∞``/``∞`` where there is none -- a bound
  exists exactly where it is finite, so there is no separate *Bounds* switch;
  typing a number sets that side, ``∞``/``inf``/nothing removes it;
* **Fixed** is a check box; **Value** takes ``-`` and the typographic ``−``;
* **Link** is shown only while some parameter of the table is linked;
* right-click: *Copy*, *Paste*, *Link…* and *Unlink*.

Toolkit-free: the menu is the app's, the link dialog the overlays feature's.
"""

from __future__ import annotations

import copy
import json
import math
import pathlib
import re
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

__all__ = [
    "LOW",
    "HIGH",
    "ParameterTable",
    "bound_text",
    "copy_text",
    "clipboard_text",
    "edit_parameter",
    "expand",
    "is_unbounded_text",
    "parameter_record",
    "parse_number",
    "plain_label",
]

#: What an unbounded side shows.
LOW, HIGH = "−∞", "∞"

_TEMPLATE = pathlib.Path(__file__).with_name("views") / "parameter_table.view.json"
_SECTION: Dict[str, Any] = {}
#: The app's clipboard for numbers (the system's has no paste here).
_CLIPBOARD = [""]


# ------------------------------------------------------------------- the spec
def _template() -> dict:
    if not _SECTION:
        with open(_TEMPLATE, "r", encoding="utf-8") as handle:
            _SECTION.update(json.load(handle)["section"])
    return copy.deepcopy(_SECTION)


#: The template's options that name something of the model.
_NAMES = ("source", "columns_source", "edited_call", "editable_call", "context_call",
          "selected_call", "delete_call", "expanded_attr")


def section(table: str, **overrides: Any) -> dict:
    """The data_table section for the :class:`ParameterTable` at attribute *table*."""
    out = _template()
    options = out["options"]
    for key in _NAMES:
        options[key] = f"{table}.{options[key]}"
    for key, value in overrides.items():
        if key in ("hidden_when", "title", "visible_when"):
            out[key] = value
        else:
            options[key] = value
    return out


def expand(spec: dict) -> dict:
    """*spec* with every ``{"type": "parameter_table", ...}`` made the shared section."""
    def walk(sections):
        out = []
        for item in sections or ():
            if isinstance(item, dict) and item.get("type") == "parameter_table":
                extra = {k: v for k, v in item.items() if k not in ("type", "table")}
                out.append(section(str(item["table"]), **extra))
                continue
            if isinstance(item, dict) and isinstance(item.get("sections"), list):
                item = dict(item, sections=walk(item["sections"]))
            out.append(item)
        return out

    return dict(spec, sections=walk(spec.get("sections")))


def base_columns() -> List[dict]:
    return _template()["options"]["columns"]


# ------------------------------------------------------------------ the cells
def parse_number(text: Any) -> Optional[float]:
    """A typed number (``-``, ``−``, ``∞``, ``inf``), or ``None``."""
    from emtk.widgets.data_table import parse_number as parse

    if isinstance(text, (int, float)) and not isinstance(text, bool):
        return float(text)
    try:
        return parse(str(text))
    except (TypeError, ValueError):
        return None


def is_unbounded_text(value: Any) -> bool:
    """Whether a typed bound means "no bound": empty, ``∞``, ``inf``, ``none``."""
    if isinstance(value, float):
        return math.isinf(value)
    text = str(value if value is not None else "").strip().lower().lstrip("+-−")
    return text in ("", "∞", "inf", "infinity", "none")


def bound_text(parameter: Any) -> Tuple[str, str]:
    """``(lo, hi)`` as the table shows them: the bound, or ``−∞``/``∞``."""
    if parameter is None or not bool(getattr(parameter, "bounds_on", False)):
        return LOW, HIGH
    lo, hi = float(parameter.lb), float(parameter.ub)
    return (f"{lo:.6g}" if math.isfinite(lo) else LOW), (f"{hi:.6g}" if math.isfinite(hi) else HIGH)


def plain_label(text: str) -> str:
    """``&sigma;<sub>x,1</sub>`` -> ``σx,1``: rich text as a table cell shows it."""
    import html

    return html.unescape(re.sub(r"</?sub>|</?sup>", "", str(text)))


def parameter_record(parameter: Any, key: Optional[str] = None, name: Optional[str] = None,
                     parent: str = "", note: str = "") -> dict:
    """One row: name, value, fixed, Lo/Hi, link; ``param`` names the parameter."""
    lo, hi = bound_text(parameter)
    link = getattr(parameter, "link", None) if getattr(parameter, "is_linked", False) else None
    pname = str(parameter.name)
    return {
        "key": pname if key is None else key,
        "param": pname,
        "name": pname if name is None else name,
        "value": float(parameter.value),
        "fixed": bool(parameter.fixed),
        "lo": lo,
        "hi": hi,
        "link": str(getattr(link, "name", "")) if link is not None else "",
        "parent": parent,
        "note": note,
    }


def edit_parameter(parameter: Any, key: str, value: Any) -> bool:
    """Write one cell into *parameter*; ``False`` when refused (a typo, a link)."""
    if key == "value":
        number = parse_number(value)
        if number is None or not math.isfinite(number) or getattr(parameter, "is_linked", False):
            return False
        parameter.value = number
        return True
    if key == "fixed":
        parameter.fixed = bool(value)
        return True
    if key not in ("lo", "hi"):
        return False
    bounded = bool(parameter.bounds_on)
    if is_unbounded_text(value) or (parse_number(value) is not None
                                    and math.isinf(parse_number(value))):
        if not bounded:
            return True
        if key == "lo":
            parameter.lb = float("-inf")
        else:
            parameter.ub = float("inf")
        parameter.bounds_on = math.isfinite(float(parameter.ub if key == "lo" else parameter.lb))
        return True
    number = parse_number(value)
    if number is None:
        return False
    if not bounded:
        # The side not typed has no bound yet, whatever was stored for it.
        parameter.lb, parameter.ub = float("-inf"), float("inf")
    if key == "lo":
        parameter.lb = number
    else:
        parameter.ub = number
    parameter.bounds_on = True
    return True


# ---------------------------------------------------------------- clipboard
def copy_text(text: str) -> None:
    """Copy *text*: to the app's clipboard, and the system's where there is one."""
    _CLIPBOARD[0] = str(text)
    try:
        from emtk import clipboard

        clipboard.copy(_CLIPBOARD[0])
    except Exception:  # noqa: BLE001 - the app's own copy still pastes
        pass


def clipboard_text() -> str:
    return _CLIPBOARD[0]


# -------------------------------------------------------------------- tables
class ParameterTable:
    """The model of one parameter table (see the module).

    Parameters
    ----------
    app : NdxApp
        For the context menu and the link dialog.
    parameters : callable
        ``() -> [Parameter, ...]``, read every frame.
    changed : callable, optional
        Called after the user changed a parameter here.
    label : callable, optional
        ``parameter -> str``: the *Name* shown (default: the plain label, else the name).
    name_tooltip : str, optional
        The *Name* column's tooltip.
    on_select, on_delete : callable, optional
        ``(parameter or None)`` when a row is selected, and on Delete.
    """

    def __init__(self, app: Any, parameters: Callable[[], Sequence[Any]], *,
                 changed: Optional[Callable[[], None]] = None,
                 label: Optional[Callable[[Any], str]] = None, name_tooltip: str = "",
                 on_select: Optional[Callable[[Any], None]] = None,
                 on_delete: Optional[Callable[[Any], None]] = None) -> None:
        self.app = app
        self.parameters = parameters
        self._changed = changed
        self.label = label or (lambda p: plain_label(getattr(p, "label_text", "") or p.name))
        self.name_tooltip = str(name_tooltip)
        self.on_select = on_select
        self.on_delete = on_delete
        #: Row keys the table shows open (a tree's parents); the table shares it.
        self.expanded: set = set()
        self._rows: List[dict] = []
        self._token: Any = None

    # -- what the spec reads ------------------------------------------------------
    def records(self) -> List[dict]:
        """The rows, built afresh (a subclass shapes them: a vector's tree)."""
        return [parameter_record(p, name=self.label(p)) for p in self.parameters()]

    def rows(self) -> List[dict]:
        """:meth:`records`, as the same list while their content is the same.

        A data table rebinds on a new list, which would reset its order and an
        open edit every frame.
        """
        rows = self.records()
        token = tuple(tuple(sorted(r.items(), key=lambda kv: kv[0])) for r in rows)
        if token != self._token:
            self._token, self._rows = token, rows
        return self._rows

    def columns(self) -> List[dict]:
        """The shared columns; *Link* only while some parameter is linked."""
        columns = base_columns()
        if self.name_tooltip:
            columns[0]["tooltip"] = self.name_tooltip
        if any(r.get("link") for r in self.rows()):
            return columns
        return [c for c in columns if c["key"] != "link"]

    def parameter(self, record: Any) -> Any:
        """The parameter a row stands for (``None`` for a row that is not one)."""
        if not isinstance(record, dict) or not record.get("param"):
            return None
        name = record["param"]
        return next((p for p in self.parameters() if p.name == name), None)

    def cell_editable(self, record: Any, key: str) -> bool:
        parameter = self.parameter(record)
        if parameter is None:
            return False
        return not (key == "value" and getattr(parameter, "is_linked", False))

    def edit(self, record: Any, key: str, value: Any) -> None:
        parameter = self.parameter(record)
        if parameter is not None and edit_parameter(parameter, key, value):
            self.changed()

    def select(self, record: Any) -> None:
        if self.on_select is not None:
            self.on_select(self.parameter(record))

    def delete(self, record: Any) -> None:
        parameter = self.parameter(record)
        if self.on_delete is not None and parameter is not None:
            self.on_delete(parameter)

    def changed(self) -> None:
        if self._changed is not None:
            self._changed()

    # -- the menu -------------------------------------------------------------------
    def menu_entries(self, record: Any, key: str) -> List[Tuple[str, Callable[[], Any]]]:
        """Copy, Paste, Link…, Unlink (a subclass adds its own)."""
        parameter = self.parameter(record)
        if parameter is None:
            return []
        entries = [("Copy", lambda: copy_text(repr(float(parameter.value)))),
                   ("Paste", lambda: self.paste(parameter))]
        if self._linker() is not None:
            entries.append(("Link…", lambda: self._linker()(parameter, self)))
        if getattr(parameter, "is_linked", False):
            entries.append(("Unlink", lambda: self.unlink(parameter)))
        return entries

    def menu(self, record: Any, key: str, where) -> None:
        entries = self.menu_entries(record, key)
        if entries:
            open_menu(self.app, entries, where)

    def paste(self, parameter: Any) -> None:
        number = parse_number(clipboard_text())
        if number is not None and math.isfinite(number) \
                and not getattr(parameter, "is_linked", False):
            parameter.value = number
            self.changed()

    def unlink(self, parameter: Any) -> None:
        parameter.link = None
        self.changed()

    def _linker(self) -> Optional[Callable[[Any, "ParameterTable"], None]]:
        """The overlays feature's link dialog, when that feature is loaded."""
        for feature in getattr(self.app, "features", ()):
            opener = getattr(feature, "open_link", None)
            if callable(opener):
                return opener
        return None


def open_menu(app: Any, entries: Sequence[Tuple[str, Callable[[], Any]]], where) -> None:
    """A context menu of ``(label, action)`` rows at *where*, opened by the app."""
    from emtk.widgets.menus import MenuItem

    items = [MenuItem(label) for label, _ in entries]
    actions = {id(item): action for item, (_, action) in zip(items, entries)}
    app.open_menu(items, float(where[0]), float(where[1]), lambda item: actions[id(item)]())
