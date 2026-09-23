"""Opening data, without a window: which reader, which dialog, and what then.

Both GUIs open files the same way, and this module is that way:

* :data:`IMPORTERS` -- the File > Import entries as data: what the file
  dialog is called, whether it asks for files or a folder, its filters, and the
  title of the merge question;
* :func:`kind_for_paths` -- the dispatch a drop and ``--file`` use;
* :func:`reader_for` / :func:`read` / :func:`load` -- the reader for a kind,
  and the load the Qt window runs on its worker thread (read, then compute the
  equation columns);
* :data:`MERGE_CHOICES` / :func:`merge` -- the merge question and what each
  answer does to the table on screen;
* :func:`working_path_for` / :func:`window_title` -- what the window shows
  about what was opened.

The Qt window (:mod:`ndxplorer.io.file_operations`) raises its dialogs and
runs the load on a thread; the emtk app (``ndxplorer.app.features.io``) draws
its own dialogs. Neither decides anything this module decides.
"""

from __future__ import annotations

import functools
import pathlib
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Sequence, Tuple, Union

from ..logging_config import logging

__all__ = [
    "IMPORTERS",
    "Importer",
    "MERGE_CHOICES",
    "MERGE_PROMPT",
    "filter_string",
    "kind_for_paths",
    "load",
    "merge",
    "merge_choice",
    "read",
    "reader_for",
    "window_title",
    "working_path_for",
]

Paths = Union[str, pathlib.Path, Sequence[Union[str, pathlib.Path]]]


@dataclass(frozen=True)
class Importer:
    """One way in: a File > Import entry.

    Attributes
    ----------
    kind : str
        What :func:`reader_for` dispatches on.
    title : str
        The file dialog's caption.
    mode : str
        ``"open"`` (files) or ``"folder"``.
    filters : tuple
        ``((label, (patterns...)), ...)``; see :func:`filter_string`.
    merge_title : str
        The caption of the merge question asked when data is already loaded.
    multiple : bool
        Whether several files can be chosen at once.
    """

    kind: str
    title: str
    mode: str
    filters: Tuple[Tuple[str, Tuple[str, ...]], ...]
    merge_title: str
    multiple: bool = False


#: The importers, by kind. The captions and filters are the Qt window's.
IMPORTERS: Dict[str, Importer] = {
    importer.kind: importer
    for importer in (
        Importer("csv", "Comma separated value files", "open",
                 (("Text files", ("*.csv", "*.dat", "*.er4", "*.txt")), ("All files", ("*.*",))),
                 "Open CSV Files", multiple=True),
        Importer("burst_dir", "Burst analysis folder", "folder", (), "Open SmFRET Files"),
        Importer("mfd_hdf5", "MFD HDF5 files", "open",
                 (("HDF5 files", ("*.h5", "*.hdf5")), ("ZIP files", ("*.zip",)),
                  ("All Files", ("*.*",))),
                 "Open MFD HDF5 Files", multiple=True),
        Importer("cs_sampling", "Open sampling folder", "folder", (), "Open Sampling Files"),
        Importer("er4", "ChiSurf sampling files", "open",
                 (("Sampling files", ("*.er4",)), ("All files", ("*.*",))),
                 "Open Sampling Files", multiple=True),
        Importer("pto", "PTO Measurement Containers", "open",
                 (("PTO files", ("*.pto",)), ("All Files", ("*.*",))), "Open PTO Container"),
    )
}

#: The merge question, as the Qt window asks it.
MERGE_PROMPT = "How do you want to merge the new data?"

#: ``(merge mode or None for replace, label)``, in the order they are offered;
#: the first is the default.
MERGE_CHOICES: Tuple[Tuple[Optional[str], str], ...] = (
    (None, "Replace existing data"),
    ("columns", "Append as columns (add new columns, rows must match)"),
    ("rows", "Append as rows (add new rows of existing columns)"),
)


def merge_choice(index: int) -> Tuple[bool, str]:
    """``(append, merge_mode)`` for the *index*-th of :data:`MERGE_CHOICES`."""
    mode = MERGE_CHOICES[int(index)][0]
    return (mode is not None, mode or "columns")


def filter_string(filters) -> str:
    """The filters as a Qt filter string: ``"Text files (*.csv *.dat);;All files (*.*)"``."""
    return ";;".join(f"{label} ({' '.join(patterns)})" for label, patterns in filters)


def _as_list(paths: Paths) -> List[str]:
    if paths is None or isinstance(paths, bool):
        return []
    if isinstance(paths, (str, pathlib.Path)):
        return [str(paths)]
    return [str(p) for p in paths]


def kind_for_paths(paths: Paths) -> str:
    """The importer a drop or ``--file`` uses for *paths*.

    A folder with a ``parameters.json`` is a sampling folder, any other folder
    a burst-analysis folder; then by the first file's extension: ``.er4``
    sampling, ``.h5``/``.hdf5``/``.zip`` an analysis file, ``.pto`` a
    measurement container, and anything else a text table (``.csv``, ``.dat``,
    ``.txt``, a single ``.bur``).
    """
    items = _as_list(paths)
    if not items:
        return "csv"
    first = pathlib.Path(items[0])
    if first.is_dir():
        return "cs_sampling" if (first / "parameters.json").exists() else "burst_dir"
    suffix = first.suffix.lower()
    if suffix == ".er4":
        return "er4"
    if suffix in (".h5", ".hdf5", ".zip"):
        return "mfd_hdf5"
    if suffix == ".pto":
        return "pto"
    return "csv"


def reader_for(kind: Optional[str], paths: Paths,
               merge_mode: str = "columns") -> Tuple[Callable, object]:
    """``(reader, argument)``: the reader for *kind* and what to hand it.

    A folder chosen for a burst analysis that turns out to hold a
    ``parameters.json`` is read as the sampling folder it is. A text import
    that picked ``.er4`` files reads them as sampling chains.
    """
    from . import reader

    items = _as_list(paths)
    kind = kind or kind_for_paths(items)
    if kind in ("burst_dir", "cs_sampling", "sampling_folder") and items:
        folder = pathlib.Path(items[0])
        if kind != "burst_dir" or (folder.is_dir() and (folder / "parameters.json").exists()):
            return reader.read_sampling_folder, str(folder)
        return reader.read_burst_analysis, str(folder)
    if kind == "er4":
        return reader.read_csv_sampling, items
    if kind == "mfd_hdf5":
        return functools.partial(reader.read_mfd_hdf5, merge_mode=merge_mode), items
    if kind == "pto":
        from .pto_reader import read_container

        return read_container, items[0]
    if any(p.lower().endswith(".er4") for p in items):
        return reader.read_csv_sampling, items
    return reader.read_csv, items


def read(paths: Paths, kind: Optional[str] = None, merge_mode: str = "columns"):
    """Read *paths* with the reader for *kind*; the raw table, no equation columns."""
    data_reader, argument = reader_for(kind, paths, merge_mode)
    return data_reader(argument)


def load(paths: Paths, kind: Optional[str] = None, merge_mode: str = "columns",
         equations=None, constants=None):
    """Read *paths* and compute the equation columns: a whole load.

    This is what the Qt window runs on its worker thread and what the emtk
    app runs on its own: the expensive part, with nothing on screen touched.

    Parameters
    ----------
    paths : str or sequence of str
        What was chosen.
    kind : str, optional
        The importer (:data:`IMPORTERS`); :func:`kind_for_paths` otherwise.
    merge_mode : str
        How several analysis files combine (``read_mfd_hdf5``).
    equations, constants
        The window's; the equation columns are computed when given.

    Returns
    -------
    DataSource
        Possibly empty (a folder with nothing readable in it).
    """
    source = read(paths, kind, merge_mode)
    if source is not None and not source.empty and (equations or constants):
        logging.info("Computing columns for %s rows", source.size)
        source.compute_columns(constants=constants or {}, equations=equations or [])
    return source


def merge(current, new, mode: str, warn: Optional[Callable[[str, str], None]] = None) -> bool:
    """Put *new* into *current* as the merge question's answer says.

    ``"columns"`` adds the new table's columns (the rows must match),
    ``"rows"`` appends its rows of the shared columns. *warn(title, text)* is
    told why something was left out or the merge refused.

    Returns
    -------
    bool
        Whether *current* changed (or holds *new* when it was empty).
    """
    if current is None or current.empty:
        return False
    return bool(current.merge(new, mode=mode, warn=warn))


def working_path_for(paths: Paths) -> str:
    """The working path after opening *paths*: the folder the first one is in.

    A burst-analysis folder's working path is the folder holding it -- the
    Qt window's rule, so a Browse after an open starts beside the data.
    """
    items = _as_list(paths)
    if not items:
        return ""
    return str(pathlib.Path(items[0]).parent)


def window_title(paths: Paths) -> str:
    """``"ndX - <name>"`` (``" (+n)"`` for more): what the window is titled after an open."""
    items = _as_list(paths)
    if not items:
        return "ndX"
    title = f"ndX - {pathlib.Path(items[0]).name}"
    if len(items) > 1:
        title += f" (+{len(items) - 1})"
    return title
