"""Screenshots of the window, without a window toolkit: the name, the formats.

The *Screenshot* button of both GUIs asks for a file and saves the window.
What the dialog offers, the name it suggests and the format a name implies
are decided here; grabbing the pixels is the toolkit's (``QWidget.grab`` in
the Qt window, a redraw into a :class:`emtk.pil_painter.PilPainter` in the
emtk app).
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Optional, Tuple

__all__ = ["SCREENSHOT_FILTERS", "SCREENSHOT_TITLE", "default_screenshot_name",
           "screenshot_format"]

#: The save dialog's caption.
SCREENSHOT_TITLE = "Save Screenshot"

#: The save dialog's filters: PNG, JPEG, BMP.
SCREENSHOT_FILTERS = "PNG Image (*.png);;JPEG Image (*.jpg *.jpeg);;BMP Image (*.bmp)"


def default_screenshot_name(folder: Optional[str] = None, now: Optional[datetime] = None) -> str:
    """``ndxplorer_screenshot_<date>_<time>.png``, in *folder* when one is given."""
    stamp = (now or datetime.now()).strftime("%Y-%m-%d_%H-%M-%S")
    name = f"ndxplorer_screenshot_{stamp}.png"
    return os.path.join(folder, name) if folder else name


def screenshot_format(filename: str) -> Tuple[str, str]:
    """``(filename, format)``: JPEG for ``.jpg``/``.jpeg``, BMP for ``.bmp``, else PNG.

    A name without an extension gets ``.png``.
    """
    ext = os.path.splitext(filename)[1].lower()
    if ext in (".jpg", ".jpeg"):
        return filename, "JPEG"
    if ext == ".bmp":
        return filename, "BMP"
    if not ext:
        filename = f"{filename}.png"
    return filename, "PNG"
