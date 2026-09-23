"""Opening and saving: the io feature of the emtk app.

File > Import, the working path's *Browse*, the merge question, Save > Burst
IDs and the Selection panel's *BID*, *save* and *load*, and *Screenshot*.

The files themselves go through :class:`~.io_service.FileService`, attached
to the window as ``app.io_service`` so every feature asks the same object --
on a desktop a drawn :class:`emtk.file_dialog.FileDialog`, in a browser the
dropped files, the mounted folder and downloads.
"""

from __future__ import annotations

from typing import Callable, Dict

from . import Feature
from .io_service import FileService

__all__ = ["IoFeature", "create"]


class IoFeature(Feature):
    """Open, merge and save; owns ``app.io_service``."""

    name = "io"

    def __init__(self, app) -> None:
        super().__init__(app)
        self.service = FileService(working_path=lambda: app.model.working_path,
                                   report=self._report)
        app.io_service = self.service

    def _report(self, title: str, text: str) -> None:
        self.app.message = (title, text)

    # ----------------------------------------------------------------- hooks
    def draw_windows(self) -> bool:
        return self.service.draw(self.app.box)

    def capture_targets(self) -> Dict[str, Callable]:
        return {"dialog:QFileDialog": lambda replay: self.service.box}


def create(app) -> IoFeature:
    return IoFeature(app)
