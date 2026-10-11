"""Read the tables a ChiSurf project (``.cs.pto``) carries, without ChiSurf.

A ChiSurf project is a PTO container: one ``chisurf.project`` object (the
project state) and a set of ``chisurf.project-entry`` objects -- named byte
entries the project embeds. A fit's sampling run is kept as such entries, named
``sampling/<fit uid>/chain.er4`` (the draws, one row per draw, as the
tab-separated table ChiSurf's sampler writes beside a run) and
``sampling/<fit uid>/diagnostics.json`` (its convergence report).

The chain tables are the *stores* this module lists and reads: plain text, so
tttrlib's container reader and its CSV reader are all that is needed.
"""

from __future__ import annotations

import os
import pathlib
import tempfile
from typing import Dict, List, Optional, Union

from ndxplorer.core.data_source import DataSource
from ndxplorer.i18n import tr

__all__ = ["ENTRY_KIND", "SUFFIX", "is_project", "list_stores", "read_store"]

#: The PTO object kind of a project's embedded entries (ChiSurf's
#: ``chisurf.core.project.pto``).
ENTRY_KIND = "chisurf.project-entry"

#: What a ChiSurf project is called on disk.
SUFFIX = (".cs", ".pto")

#: Entry names of the stores: sampling chains.
_STORE_PREFIX = "sampling/"
_STORE_SUFFIX = ".er4"

PathLike = Union[str, pathlib.Path]


def is_project(path: PathLike) -> bool:
    """Whether *path* names a ChiSurf project (``*.cs.pto``)."""
    suffixes = [s.lower() for s in pathlib.Path(path).suffixes[-2:]]
    return suffixes == list(SUFFIX)


def _entries(path: PathLike) -> Dict[str, bytes]:
    """The project's store entries, by name: what :func:`list_stores` lists.

    The same container calls ChiSurf's own reader makes; only entries of
    :data:`ENTRY_KIND` naming a sampling chain are read.
    """
    import tttrlib

    source = pathlib.Path(path)
    if not source.is_file():
        raise FileNotFoundError(tr("No such project: {path}").format(path=source))
    handle = tttrlib.PtoFile()
    if not handle.open(str(source)):
        raise OSError(tr("Could not open {path}: {error}").format(path=source,
                                                              error=handle.error()))
    try:
        found: Dict[str, bytes] = {}
        for obj in handle.objects():
            name = str(obj.name)
            if (obj.kind == ENTRY_KIND and name.startswith(_STORE_PREFIX)
                    and name.endswith(_STORE_SUFFIX)):
                found[name] = bytes(handle.read(obj.uid))
        return found
    finally:
        handle.close()


def _store(data: bytes):
    """A chain entry's bytes as a ``tttrlib.DataStore`` (tttrlib reads files)."""
    import tttrlib

    handle, scratch = tempfile.mkstemp(suffix=_STORE_SUFFIX)
    try:
        with os.fdopen(handle, "wb") as out:
            out.write(data)
        return tttrlib.read_csv(scratch, delimiter="\t", has_header=True)
    finally:
        os.unlink(scratch)


def list_stores(path: PathLike) -> List[dict]:
    """The tables a project carries: one per stored sampling chain.

    Parameters
    ----------
    path : str or pathlib.Path
        A ``.cs.pto`` file.

    Returns
    -------
    list of dict
        ``{"name", "rows", "columns"}`` per store, by name: the entry name, the
        number of draws, the column names (parameters, ``chain``, ``draw``).
    """
    stores = []
    for name, data in sorted(_entries(path).items()):
        store = _store(data)
        stores.append({
            "name": name,
            "rows": int(store.n_rows()),
            "columns": [str(store.column(i).name()) for i in range(store.n_columns())],
        })
    return stores


def read_store(path: PathLike, store: Optional[str] = None) -> DataSource:
    """Read one stored table of a project as a data source.

    Parameters
    ----------
    path : str or pathlib.Path
        A ``.cs.pto`` file.
    store : str, optional
        The entry name (:func:`list_stores`); may be left out when the project
        holds exactly one.

    Returns
    -------
    DataSource
        One row per draw, with ``chain`` and ``draw`` columns.

    Raises
    ------
    ValueError
        When the project holds no store, *store* is not one of them, or *store*
        is left out and there are several (the message lists them).
    """
    entries = _entries(path)
    if not entries:
        raise ValueError(tr("{name} holds no stored sampling chain").format(
            name=pathlib.Path(path).name))
    if store is None:
        if len(entries) > 1:
            raise ValueError(tr("Several stored tables; choose one of: {names}").format(
                names=", ".join(sorted(entries))))
        store = next(iter(entries))
    if store not in entries:
        raise ValueError(tr("No stored table {name}; the project holds: {names}").format(
            name=repr(store), names=", ".join(sorted(entries))))
    return DataSource(_store(entries[store]))
