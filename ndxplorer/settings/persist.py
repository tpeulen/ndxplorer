"""Writing settings back, without a window.

:mod:`.bundle` reads a ``*.settings.json`` and the files it names. This is the
other direction: the per-parameter axis settings, the default axes, the
constants and the equations, each turned into the bytes of its file and
written. Both GUIs call these; the Qt window asks for file names with
``QFileDialog``, the emtk app with its io service.

Every writer has a ``*_bytes`` twin that returns the file's content instead of
writing it, so a browser build can hand it to a download.
"""

from __future__ import annotations

import json
import pathlib
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple, Union

from ..logging_config import logging

__all__ = [
    "PACKAGED_AXIS_SETTINGS",
    "merge_axis_settings",
    "axis_settings_bytes",
    "write_axis_settings",
    "with_default_axes",
    "write_default_axes",
    "constants_payload",
    "write_constants",
    "equations_bytes",
    "write_equations",
    "read_json",
]

PathLike = Union[str, pathlib.Path]

#: The per-parameter axis settings shipped with ndXplorer.
PACKAGED_AXIS_SETTINGS = pathlib.Path(__file__).parent / "mfd.axis.json"


def read_json(path: Optional[PathLike], default: Any = None) -> Any:
    """A JSON file's content, or *default* when it is missing or unreadable."""
    if not path:
        return default
    path = pathlib.Path(path)
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError) as exc:
        logging.debug("Could not read %s: %s", path, exc)
        return default
    return default if data is None else data


# ------------------------------------------------------------ axis settings
def merge_axis_settings(baseline: Mapping[str, Any], axis_settings: Mapping[str, Any],
                        names: Iterable[str]) -> Tuple[Dict[str, Any], Dict[str, dict]]:
    """The axis settings of the parameters in use, written over *baseline*.

    Only the parameters on screen (*names*) are taken from *axis_settings*:
    the file keeps every other parameter's entry as it was, so saving while
    looking at two axes does not rewrite forty.

    Returns
    -------
    merged : dict
        What the file should hold.
    changed : dict
        ``{name: {"from": old, "to": new}}`` for the entries that changed.
    """
    merged = dict(baseline or {})
    changed: Dict[str, dict] = {}
    for name in names:
        if not name:
            continue
        current = axis_settings.get(name)
        if not isinstance(current, dict):
            continue
        before = merged.get(name)
        if before != current:
            merged[name] = dict(current)
            changed[name] = {"from": before, "to": current}
    return merged, changed


def _axis_baseline(target: Optional[PathLike]) -> Dict[str, Any]:
    """The file being overwritten, else the packaged axis settings."""
    if target is not None and pathlib.Path(target).exists():
        return read_json(target, {}) or {}
    return read_json(PACKAGED_AXIS_SETTINGS, {}) or {}


def axis_settings_bytes(axis_settings: Mapping[str, Any], names: Iterable[str],
                        target: Optional[PathLike] = None) -> bytes:
    """The content of an ``*.axis.json`` holding the axes in use.

    Parameters
    ----------
    axis_settings : mapping
        Parameter name -> ``{"min", "max", "scale", "n_bins_1d", "n_bins_2d"}``.
    names : iterable of str
        The parameters on the axes now.
    target : path, optional
        The file it will replace; its other entries are kept. Without one (or
        when it does not exist) the packaged axis settings are the baseline.
    """
    merged, _changed = merge_axis_settings(_axis_baseline(target), axis_settings, names)
    return json.dumps(merged, indent=4).encode("utf-8")


def write_axis_settings(path: PathLike, axis_settings: Mapping[str, Any],
                        names: Iterable[str]) -> Dict[str, dict]:
    """Write the axes in use into *path*; returns what changed (see :func:`merge_axis_settings`)."""
    path = pathlib.Path(path)
    merged, changed = merge_axis_settings(_axis_baseline(path), axis_settings, names)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(merged, handle, indent=4)
    if changed:
        logging.info("Updated axis settings for: %s", ", ".join(changed))
    else:
        logging.info("No changes detected for current axes; saved file unchanged")
    return changed


# ------------------------------------------------------------- default axes
def with_default_axes(settings: Mapping[str, Any], x: str, y: str, z: str,
                      weight: Optional[str] = None,
                      colormap: Optional[str] = None) -> Dict[str, Any]:
    """*settings* with ``default_axes`` (and ``colormap``) set to these."""
    data = dict(settings or {})
    axes = dict(data.get("default_axes") or {})
    axes.update({"x": x, "y": y, "z": z})
    if weight:
        axes["weight"] = weight
    data["default_axes"] = axes
    if colormap:
        data["colormap"] = colormap
    return data


def write_default_axes(settings_path: PathLike, x: str, y: str, z: str,
                       weight: Optional[str] = None, colormap: Optional[str] = None,
                       fallback: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    """Settings > Set default axis: store the axes in the settings file.

    The file is read first so nothing else in it changes; an unreadable file
    is replaced by *fallback* (the settings in memory) plus the new axes.
    Returns what was written. Raises ``OSError`` when it cannot be written.
    """
    path = pathlib.Path(settings_path)
    current = read_json(path, None)
    if not isinstance(current, dict):
        current = dict(fallback or {})
    data = with_default_axes(current, x, y, z, weight, colormap)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=4)
    logging.info("Updated default_axes in '%s' to %s", path, data.get("default_axes"))
    return data


# ---------------------------------------------------------------- constants
def constants_payload(values: Mapping[str, float],
                      existing: Optional[Mapping[str, Any]] = None) -> Dict[str, Any]:
    """What an ``mfd.constants.json`` should hold for these constant values.

    A file in the rich per-parameter format (value, bounds, fixed) keeps its
    format and its bounds; only the values change and new constants are
    added. A flat file (or none) is written flat.
    """
    from ..core.constants_group import is_state_format

    if existing is not None and is_state_format(existing):
        data = json.loads(json.dumps(existing))
        params = data["parameters"]
        for name, value in values.items():
            entry = params.setdefault(str(name), {})
            entry["value"] = float(value)
        return data
    return {str(k): float(v) for k, v in values.items()}


def write_constants(path: PathLike, payload: Mapping[str, Any]) -> None:
    """Write a constants file (either format)."""
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(dict(payload), handle, indent=4)
    logging.info("Parameters saved to %s", path)


# ---------------------------------------------------------------- equations
def equations_bytes(equations: List[Mapping[str, str]]) -> bytes:
    """The content of an equations YAML: ``- name: expression`` per line.

    The format :func:`.bundle.read_settings` reads back, with each expression
    as a folded block so quotes inside it survive.
    """
    import yaml

    rows = [{str(k): str(v) for k, v in dict(item).items()} for item in equations or []]
    header = "# ndXplorer equations: one '- column: expression' per entry\n"
    body = yaml.safe_dump(rows, default_flow_style=False, sort_keys=False, allow_unicode=True)
    return (header + body).encode("utf-8")


def write_equations(path: PathLike, equations: List[Mapping[str, str]]) -> None:
    """Write the equations to *path*."""
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(equations_bytes(equations))
    logging.info("Equations saved to %s", path)
