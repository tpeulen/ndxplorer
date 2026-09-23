"""File > Save > Histograms, File > Print window and File > Exit.

Three File-menu rows the Qt window shows and never connected. Here:

* **Save > Histograms** writes what is on screen -- the x and y marginals and
  the 2-D map -- as one tab-separated text file, through ``app.io_service``
  (a save dialog on a desktop, a download in a page). The text is the one
  both GUIs put on the clipboard (:mod:`ndxplorer.utils.histogram_export`).
* **Print window** saves a picture of the window (the Screenshot action): a
  file the user prints, rather than a printing system emtk does not have.
* **Exit** closes the window through its host; a browser page has no window
  to close, so there it is disabled.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Optional

from . import Feature

__all__ = ["WindowFeature", "create", "histograms_text"]


def histograms_text(hist) -> str:
    """The marginals and the 2-D map of *hist* (a model's ``Histograms``) as text."""
    from ...utils.histogram_export import histogram_2d_text, histograms_1d_text

    return ("# marginals\n" + histograms_1d_text(hist.x, hist.y)
            + "\n# 2-D histogram\n" + (histogram_2d_text(hist.H, hist.x_edges, hist.y_edges)
                                       or ""))


class WindowFeature(Feature):
    """The window-level File rows: save the histograms, print, exit."""

    name = "window"

    def actions(self) -> Dict[str, Callable[[], Any]]:
        return {"save_histograms": self.save_histograms, "print_window": self.print_window}

    def available(self, action: str) -> Optional[bool]:
        app = self.app
        if action == "save_histograms":
            return app.model.histograms is not None and hasattr(app, "io_service")
        if action == "print_window":
            return app.model.has_data and app.panel.available("screenshot")
        if action == "exit":
            return app.on_exit is not None       # no window to close in a page
        return None

    def save_histograms(self) -> None:
        hist = self.app.model.histograms
        if hist is None:
            return
        data = histograms_text(hist).encode("utf-8")
        self.app.io_service.save_bytes("histograms.txt", data, "text/tab-separated-values",
                                       title="Save histograms",
                                       filters="Text files (*.txt *.tsv)")

    def print_window(self) -> None:
        self.app.run_action("screenshot")


def create(app) -> WindowFeature:
    return WindowFeature(app)
