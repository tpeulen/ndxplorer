"""Screenshot-related utilities for NDxplorer."""

from __future__ import annotations

import os

from qtpy import QtWidgets

from ..export.screenshots import (
    SCREENSHOT_FILTERS,
    SCREENSHOT_TITLE,
    default_screenshot_name,
    screenshot_format,
)

from ..logging_config import logging


def take_screenshot(ndxplorer: "NDXplorer") -> None:
    """Capture the window, copy to clipboard, and prompt for save location."""
    logging.debug("on_take_screenshot")
    try:
        pixmap = ndxplorer.grab()
        _copy_pixmap_to_clipboard(pixmap)
        default_path = _default_screenshot_path(ndxplorer)
        filename, selected_filter = QtWidgets.QFileDialog.getSaveFileName(
            ndxplorer,
            SCREENSHOT_TITLE,
            default_path,
            SCREENSHOT_FILTERS,
        )
        if not filename:
            return

        filename, img_format = screenshot_format(filename)

        if not pixmap.save(filename, img_format):
            QtWidgets.QMessageBox.warning(
                ndxplorer, "Save Screenshot", f"Failed to save screenshot to:\n{filename}"
            )
        else:
            logging.info("Saved screenshot to %s", filename)
    except Exception as exc:  # pragma: no cover - UI path
        logging.error("Error while taking screenshot: %s", exc)
        QtWidgets.QMessageBox.critical(
            ndxplorer,
            "Save Screenshot",
            f"An error occurred while saving the screenshot:\n{exc}",
        )


def _default_screenshot_path(ndxplorer) -> str:
    try:
        base_dir = ndxplorer.working_path if getattr(ndxplorer, "working_path", None) else os.getcwd()
    except Exception:
        base_dir = os.getcwd()
    return default_screenshot_name(base_dir)


def _copy_pixmap_to_clipboard(pixmap) -> None:
    try:
        app = QtWidgets.QApplication.instance()
        if app is None:
            return
        clipboard = app.clipboard()
        if clipboard is not None:
            clipboard.setPixmap(pixmap)
    except Exception as exc:
        logging.debug("Failed to copy screenshot to clipboard: %s", exc)
