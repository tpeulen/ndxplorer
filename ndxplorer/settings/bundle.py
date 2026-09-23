"""Reading a settings file and the files it names, without a window.

A ``*.settings.json`` names four more files: the per-parameter axis settings,
the axis-label styling, the equations and the constants. Reading them used to
happen inside ``settings_helpers.load_settings``, interleaved with writing the
results into the Qt window's widgets. The reading is here now, so the emtk app
and the Qt window load the same settings the same way.
"""

from __future__ import annotations

import json
import pathlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

from ..logging_config import logging
from . import get_settings_path

__all__ = ["SettingsBundle", "PACKAGED_SETTINGS", "default_settings_file", "read_settings"]

#: The settings shipped with ndXplorer.
PACKAGED_SETTINGS = pathlib.Path(__file__).parent / "mfd.settings.json"


@dataclass
class SettingsBundle:
    """A settings file and everything it refers to.

    Attributes
    ----------
    path : pathlib.Path
        The settings file that was read.
    settings : dict
        Its contents (``default_axes``, ``colormap``, the file names, ...).
    axis_settings : dict
        Parameter name -> ``{"min", "max", "scale", "n_bins_1d", "n_bins_2d"}``.
    axis_labels : dict or None
        The axis-label styling, when the settings name a file for it.
    equations : list
        ``[{column: expression}, ...]``.
    equations_path : pathlib.Path or None
        The equation file, for an editor that shows it.
    constants : dict
        Constant name -> value.
    """

    path: pathlib.Path
    settings: Dict[str, Any] = field(default_factory=dict)
    axis_settings: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    axis_labels: Optional[Dict[str, Any]] = None
    equations: List[Dict[str, str]] = field(default_factory=list)
    equations_path: Optional[pathlib.Path] = None
    constants: Dict[str, float] = field(default_factory=dict)


def default_settings_file() -> pathlib.Path:
    """The user's ``mfd.settings.json``, seeded from the packaged defaults."""
    from . import ensure_default_settings

    ensure_default_settings()
    return get_settings_path() / "mfd.settings.json"


def _named(settings_dir: pathlib.Path, name: str) -> pathlib.Path:
    """A file the settings name: beside the settings, else the packaged one."""
    candidate = settings_dir / name
    if candidate.exists():
        return candidate
    return PACKAGED_SETTINGS.parent / name


def read_settings(path: Union[str, pathlib.Path, None] = None) -> SettingsBundle:
    """Read a settings file and the axis, label, equation and constant files it names.

    Parameters
    ----------
    path : str or Path, optional
        The ``*.settings.json``. ``None`` reads the user's default; a file that
        does not exist falls back to the packaged settings.
    """
    import yaml

    path = pathlib.Path(path) if path else default_settings_file()
    if not path.exists():
        logging.warning("Settings file not found: %s. Falling back to defaults.", path)
        path = PACKAGED_SETTINGS
    with open(path, "r", encoding="utf-8") as handle:
        settings = json.load(handle)
    bundle = SettingsBundle(path=path, settings=settings)
    settings_dir = path.parent

    if settings.get("axis"):
        fn_axis = _named(settings_dir, settings["axis"])
        if fn_axis.exists():
            with open(fn_axis, "r", encoding="utf-8") as handle:
                bundle.axis_settings.update(json.load(handle))
        else:
            logging.warning("Axis settings file not found: %s", fn_axis)

    if settings.get("axis_labels"):
        fn_labels = _named(settings_dir, settings["axis_labels"])
        if fn_labels.exists():
            try:
                with open(fn_labels, "r", encoding="utf-8") as handle:
                    bundle.axis_labels = yaml.load(handle, Loader=yaml.FullLoader) or {}
            except Exception as exc:
                logging.warning("Error loading axis label settings: %s", exc)
        else:
            logging.warning("Axis label settings file not found: %s", fn_labels)

    if settings.get("equations"):
        fn_equations = _named(settings_dir, settings["equations"])
        if fn_equations.exists():
            with open(fn_equations, "r", encoding="utf-8") as handle:
                bundle.equations = yaml.load(handle, Loader=yaml.FullLoader) or []
            bundle.equations_path = fn_equations
        else:
            logging.warning("Equations file not found: %s", fn_equations)

    if settings.get("constants"):
        fn_constants = _named(settings_dir, settings["constants"])
        if fn_constants.exists():
            from ..core.constants_group import values_from_data

            with open(fn_constants, "r", encoding="utf-8") as handle:
                # Accept both legacy flat and rich per-parameter state formats.
                bundle.constants.update(values_from_data(json.load(handle)))
        else:
            logging.warning("Constants file not found: %s", fn_constants)
    return bundle
