"""The Qt window's settings actions: file dialogs and message boxes.

What is read and written, and how, is Qt-free: :mod:`.settings.bundle` reads,
:mod:`.settings.persist` writes. This module only asks the user.
"""

from __future__ import annotations

import copy
from typing import Optional

from qtpy import QtWidgets

from .logging_config import logging
from .plotting.axis_display import DEFAULT_LABEL_SETTINGS
from .settings import get_settings_path
from .settings.persist import write_axis_settings, write_default_axes

if False:  # pragma: no cover - only for type checking without runtime import
    from .plot_main import NDXplorer


def save_axis_settings(
    ndxplorer: "NDXplorer", settings_json_fn: Optional[str] = None
) -> None:
    """Persist current axis configuration to a JSON file."""
    logging.debug("save_axis_settings")
    if isinstance(settings_json_fn, bool):
        settings_json_fn = None

    if not settings_json_fn:
        settings_path = get_settings_path()
        default_filename = str(settings_path / "mfd.axis.json")
        filename, _ = QtWidgets.QFileDialog.getSaveFileName(
            ndxplorer,
            "Axis settings file",
            default_filename,
            "Axis file (*.axis.json)",
        )
        if not filename:
            return
        settings_json_fn = filename

    try:
        if hasattr(ndxplorer, "plot_control") and ndxplorer.plot_control is not None:
            ndxplorer.plot_control.update_x_axis_settings()
            ndxplorer.plot_control.update_y_axis_settings()
            ndxplorer.plot_control.update_z_axis_settings()
    except Exception as exc:  # pragma: no cover - defensive
        logging.debug("Could not refresh axis settings from UI before saving: %s", exc)

    in_use_names = []
    try:
        in_use_names = [
            getattr(ndxplorer.plot_control, "x_label", "") or "",
            getattr(ndxplorer.plot_control, "y_label", "") or "",
            getattr(ndxplorer.plot_control, "z_label", "") or "",
        ]
    except Exception as exc:  # pragma: no cover - defensive
        logging.debug("Could not determine in-use axis names: %s", exc)

    current = getattr(ndxplorer.plot_control, "axis_settings", {}) or {}
    try:
        write_axis_settings(settings_json_fn, current, in_use_names)
    except Exception as exc:
        logging.error("Failed to save axis settings to %s: %s", settings_json_fn, exc)


def set_default_axis(ndxplorer: "NDXplorer") -> None:
    """Persist the currently selected axes/weight/colormap as defaults."""
    logging.debug("set_default_axis")
    settings_path = getattr(ndxplorer, "_settings_json_path", None)
    if not settings_path:
        try:
            settings_path = str(get_settings_path() / "mfd.settings.json")
        except Exception:  # pragma: no cover - defensive
            settings_path = None
    if not settings_path:
        QtWidgets.QMessageBox.warning(
            ndxplorer, "Set default axis", "Could not determine settings file path."
        )
        return

    try:
        x_name = ndxplorer.plot_control.p1[1]
        y_name = ndxplorer.plot_control.p2[1]
        z_name = ndxplorer.plot_control.p3[1]
    except Exception as exc:
        QtWidgets.QMessageBox.warning(
            ndxplorer, "Set default axis", f"Unable to read current axis selections: {exc}"
        )
        return

    weight_name = None
    try:
        if hasattr(ndxplorer, "comboBoxWeight") and ndxplorer.comboBoxWeight is not None:
            weight_name = str(ndxplorer.comboBoxWeight.currentText())
    except Exception:  # pragma: no cover - defensive
        weight_name = None

    fallback = (
        dict(ndxplorer.settings)
        if hasattr(ndxplorer, "settings") and isinstance(ndxplorer.settings, dict)
        else {}
    )
    try:
        settings_data = write_default_axes(
            settings_path, x_name, y_name, z_name, weight=weight_name,
            colormap=getattr(ndxplorer, "current_cmap", None), fallback=fallback,
        )
        try:
            ndxplorer.settings.update(settings_data)
        except Exception:
            pass
        QtWidgets.QMessageBox.information(
            ndxplorer, "Set default axis", "Default axis settings have been updated."
        )
    except Exception as exc:
        logging.error("Failed to save default axes to '%s': %s", settings_path, exc)
        QtWidgets.QMessageBox.critical(
            ndxplorer,
            "Set default axis",
            f"Failed to save default axis settings:\n{exc}",
        )


def load_settings(
    ndxplorer: "NDXplorer", settings_json_fn: Optional[str] = None
) -> None:
    """Load settings JSON plus referenced axis/label/equation files."""
    logging.debug("onLoad_settings")
    if isinstance(settings_json_fn, bool):
        settings_json_fn = None
    if settings_json_fn is None:
        file_sel = QtWidgets.QFileDialog.getOpenFileName(
            None,
            "ndX settings file",
            ndxplorer.working_path,
            "ndX settings (*.settings.json)",
        )
        if isinstance(file_sel, (tuple, list)):
            settings_json_fn = file_sel[0]
        else:
            settings_json_fn = file_sel
    if not settings_json_fn:
        return

    try:
        ndxplorer._settings_json_path = str(settings_json_fn)
    except Exception:
        ndxplorer._settings_json_path = None

    from .settings.bundle import read_settings

    bundle = read_settings(settings_json_fn)
    ndxplorer.settings.update(bundle.settings)

    if "colormap" in ndxplorer.settings:
        ndxplorer.set_default_colormap(ndxplorer.settings["colormap"])

    ndxplorer.plot_control.axis_settings.update(bundle.axis_settings)

    if "axis_labels" in ndxplorer.settings:
        ndxplorer.axis_label_settings = copy.deepcopy(DEFAULT_LABEL_SETTINGS)
        if bundle.axis_labels:
            ndxplorer.axis_label_settings.update(bundle.axis_labels)
        try:
            fonts = ndxplorer.axis_label_settings.get("fonts", {})
            if not hasattr(ndxplorer, "font_settings"):
                ndxplorer.font_settings = {}
            ndxplorer.font_settings.update(fonts)
            ndxplorer.apply_fonts()
        except Exception as exc:
            logging.debug("Could not apply font settings: %s", exc)

    if bundle.equations_path is not None:
        ndxplorer.equations = bundle.equations
    ndxplorer.constants.update(bundle.constants)

    if bundle.equations_path is not None:
        ndxplorer.equation_editor.load_file(str(bundle.equations_path))
