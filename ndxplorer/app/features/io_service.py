"""Where the emtk app's files come from and go to: one object, two backends.

Every feature that opens or saves a file asks :class:`FileService` (the
window's ``app.io_service``) and gets its answer in a callback, a frame or
several later -- there is no blocking dialog in an immediate-mode frame, and
none at all in a browser:

.. code-block:: python

    app.io_service.ask_open("Load settings", "Settings (*.settings.json);;All files (*)",
                            lambda paths: load(paths[0]))
    app.io_service.save_bytes("histograms.csv", data, "text/csv")

On a desktop the dialogs are :class:`emtk.file_dialog.FileDialog`, drawn over
the window by :meth:`FileService.draw` (the io feature calls it from its
``draw_windows``), and ``save_bytes`` asks for a path and writes there.

In a browser (Pyodide, :func:`emtk.web.page.in_browser`) the user's files are
not a file system: they arrive by drop (``/mnt/dropped``) or through the page's
*Mount folder* (``/mnt/local``). The dialogs open there. What is saved inside
the mounted folder reaches the disk (``boot.js`` syncs the mount after input);
anything saved elsewhere -- and everything ``save_bytes`` writes -- is handed
to the browser as a download (:func:`emtk.web.page.download`), which is the
one way out of a page that always works.

Nothing here imports Qt, and nothing needs a window: the dialogs are plain
objects a test can press (:meth:`FileService.answer`).
"""

from __future__ import annotations

import logging
import mimetypes
import os
import pathlib
from dataclasses import dataclass, field
from typing import Any, Callable, List, Optional, Sequence, Union

__all__ = ["FileService", "Request"]

logger = logging.getLogger(__name__)

Filters = Union[str, Sequence]


@dataclass
class Request:
    """One question on screen: a file dialog and what to do with its answer.

    Attributes
    ----------
    dialog : emtk.file_dialog.FileDialog
        The dialog drawn for it.
    callback : callable
        Called with the answer: a list of paths (``ask_open``) or one path.
    kind : str
        ``"open"``, ``"save"`` or ``"folder"``.
    multiple : bool
        ``ask_open`` with several files.
    """

    dialog: Any
    callback: Callable[[Any], None]
    kind: str
    multiple: bool = False
    box: Optional[tuple] = field(default=None, repr=False)
    window: Any = field(default=None, repr=False)


class FileService:
    """Open, save and choose folders for the app, on a desktop or in a page.

    Parameters
    ----------
    working_path : callable, optional
        ``() -> str``: where a dialog starts (the window's working path); see
        :meth:`start_directory` when it returns nothing.
    report : callable, optional
        ``report(title, text)``: how a failure is shown (the window's message
        box). Logged otherwise.
    browser : bool, optional
        Force the backend; :func:`emtk.web.page.in_browser` decides by default.

    Attributes
    ----------
    requests : list of Request
        The questions waiting for an answer, oldest first; the first is on
        screen.
    """

    def __init__(self, working_path: Optional[Callable[[], str]] = None,
                 report: Optional[Callable[[str, str], None]] = None,
                 browser: Optional[bool] = None) -> None:
        if browser is None:
            from emtk.web.page import in_browser

            browser = in_browser()
        self.browser = bool(browser)
        self.working_path = working_path or (lambda: "")
        self.report = report
        self.requests: List[Request] = []

    # ------------------------------------------------------------ questions
    def start_directory(self) -> str:
        """Where a dialog opens: the working path, else the user's files.

        On a desktop that is the current folder (where the Qt window's dialogs
        open too); in a page the mounted folder, else the dropped files, else
        ``/``. A working path only counts when it is still there.
        """
        path = str(self.working_path() or "")
        if path and os.path.isdir(path):
            return path
        if self.browser:
            from emtk.web.page import user_files_dir

            return user_files_dir("/")
        return os.getcwd()

    def _ask(self, kind: str, title: str, filters: Filters, callback, multiple=False,
             filename: str = "", action: Optional[str] = None) -> Request:
        from emtk.file_dialog import FileDialog

        dialog = FileDialog(title, mode=kind, filters=filters or (("All files", ("*",)),),
                            directory=self.start_directory(), filename=filename,
                            multiselect=bool(multiple), action=action)
        request = Request(dialog, callback, kind, bool(multiple))
        self.requests.append(request)
        return request

    def ask_open(self, title: str, filters: Filters, callback: Callable[[List[str]], None],
                 multiple: bool = False) -> Request:
        """Ask for files to open; ``callback(paths)`` unless cancelled.

        Parameters
        ----------
        title : str
            The dialog's title (the Qt dialog's caption).
        filters : str or sequence
            ``"Text files (*.csv *.dat);;All files (*)"`` or ``[(label, [patterns])]``.
        callback : callable
            Called with the chosen paths, a list even for one file.
        multiple : bool
            Allow several files.
        """
        return self._ask("open", title, filters, callback, multiple)

    def ask_save(self, title: str, filters: Filters, default_name: str,
                 callback: Callable[[str], None]) -> Request:
        """Ask where to save; ``callback(path)`` unless cancelled.

        The callback writes the file. In a page, a file written outside the
        mounted folder is then handed to the browser as a download.
        """
        return self._ask("save", title, filters, callback, filename=default_name)

    def ask_folder(self, title: str, callback: Callable[[str], None]) -> Request:
        """Ask for a folder; ``callback(path)`` unless cancelled."""
        return self._ask("folder", title, [("Folders", ["*"])], callback)

    def save_bytes(self, name: str, data: bytes, mime: str = "application/octet-stream",
                   title: str = "Save", filters: Filters = "") -> Optional[Request]:
        """Save *data* as a file the user gets: a path on a desktop, a download in a page.

        Parameters
        ----------
        name : str
            The suggested file name.
        data : bytes
            The content.
        mime : str
            Its media type (only a page uses it).
        title, filters : str
            The desktop dialog's caption and filters; by default the name's
            extension.

        Returns
        -------
        Request or None
            The dialog asked on a desktop; ``None`` in a page (downloaded now).
        """
        data = bytes(data)
        if self.browser:
            self.download(name, data, mime)
            return None
        if not filters:
            suffix = pathlib.Path(name).suffix
            filters = ([(f"{suffix[1:].upper()} files", [f"*{suffix}"]), ("All files", ["*"])]
                       if suffix else [("All files", ["*"])])

        def write(path: str) -> None:
            with open(path, "wb") as handle:
                handle.write(data)
            logger.info("saved %s", path)

        return self._ask("save", title, filters, write, filename=name)

    def download(self, name: str, data: bytes, mime: Optional[str] = None) -> None:
        """Hand *data* to the browser (a page only)."""
        from emtk.web.page import download

        mime = mime or mimetypes.guess_type(name)[0] or "application/octet-stream"
        download(os.path.basename(name), data, mime)

    # --------------------------------------------------------------- answers
    @property
    def current(self) -> Optional[Request]:
        """The question on screen, or ``None``."""
        return self.requests[0] if self.requests else None

    @property
    def busy(self) -> bool:
        return bool(self.requests)

    def cancel(self) -> None:
        """Close the question on screen without an answer."""
        if self.requests:
            self.requests.pop(0)

    def answer(self, paths: Union[str, Sequence[str], None]) -> None:
        """Answer the question on screen, as pressing its action button does.

        ``None`` (or an empty answer) cancels. A test, or a scenario replay,
        answers the dialog this way.
        """
        request = self.current
        if request is None:
            return
        self.requests.pop(0)
        if not paths:
            return
        paths = [str(paths)] if isinstance(paths, (str, os.PathLike)) else [str(p) for p in paths]
        self._deliver(request, paths)

    def _deliver(self, request: Request, paths: List[str]) -> None:
        try:
            if request.kind == "open":
                request.callback(paths if request.multiple else paths[:1])
            else:
                request.callback(paths[0])
        except Exception as exc:  # noqa: BLE001 - shown, the window goes on
            logger.exception("%s failed", request.dialog.title)
            if self.report is not None:
                self.report(request.dialog.title, f"{type(exc).__name__}: {exc}")
            return
        if request.kind == "save" and self.browser:
            self._hand_out(paths[0])

    def _hand_out(self, path: str) -> None:
        """In a page: a file saved outside the mounted folder becomes a download."""
        from emtk.web.page import MOUNT_DIR

        try:
            inside = os.path.commonpath([os.path.abspath(path), MOUNT_DIR]) == MOUNT_DIR
        except ValueError:
            inside = False
        if inside or not os.path.isfile(path):
            return
        with open(path, "rb") as handle:
            self.download(os.path.basename(path), handle.read())

    # --------------------------------------------------------------- drawing
    def draw(self, box: tuple) -> bool:
        """Draw the question on screen over the window *box*; returns whether one is.

        Called inside the app's emtk frame (the io feature's ``draw_windows``).
        """
        request = self.current
        if request is None:
            return False
        from emtk.dialog_window import DialogWindow

        if request.window is None:
            request.window = DialogWindow(request.dialog.title, size=(720.0, 460.0),
                                          key=f"io-{id(request)}")
        pressed = request.window.begin(box)
        result = request.dialog.draw()
        request.window.end()
        request.box = request.window.box
        if result is False or pressed == "close":
            self.cancel()
        elif result:
            self.answer(result)
        return True

    @property
    def box(self) -> Optional[tuple]:
        """Where the question on screen was drawn last, or ``None``."""
        request = self.current
        return request.box if request is not None else None

