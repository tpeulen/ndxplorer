"""A `.pto` measurement container, opened with tttrlib alone.

The container is tttrlib's (`tttrlib.PtoFile`) and so is its PTO.MFDB reading:
typed mmCIF tags (`tttrlib.pto_tag`), lineage (`pto_parents`), verified
payloads (`pto_read_blob`), described writes (`pto_add_blob`), the one-writer
lock (`PtoWriteLock`) and the legacy `.bur` interleave
(`deinterleave_burst_rows`). ChiSurf's `Measurement` uses the same functions,
so ndX reading a container and ChiSurf reading it agree, and ndX needs neither
ChiSurf nor IMP to open one -- in the desktop app or in the browser.

This module only adds the open/commit/close/lock bracket and the few lookups
every ndX reader of a container repeats.
"""

from __future__ import annotations

import contextlib
from typing import Iterator, List, Optional

import tttrlib

__all__ = ["open_container", "objects_named", "read_store", "software"]


@contextlib.contextmanager
def open_container(path, writable: bool = False) -> Iterator["tttrlib.PtoFile"]:
    """Open *path*; commit on a clean exit when *writable*; always close.

    A writable open takes the container's writer lock first, so ndX saving a
    calibration and ChiSurf writing an analysis cannot overwrite each other.

    Raises
    ------
    OSError
        When the file is not a container or cannot be opened.
    tttrlib.PtoLockedError
        When another process is writing it.
    """
    lock = tttrlib.PtoWriteLock(str(path)).acquire() if writable else None
    handle = tttrlib.PtoFile()
    try:
        if not handle.open(str(path), bool(writable)):
            raise OSError(f"could not open {path}: {handle.error()}")
        yield handle
        if writable and not handle.commit():
            raise OSError(f"could not commit {path}: {handle.error()}")
    finally:
        if handle.is_open():
            handle.close()
        if lock is not None:
            lock.release()


def objects_named(handle, name: str, kind: str = "") -> List:
    """The objects called *name* (of *kind*, when given), in container order."""
    return [obj for obj in handle.objects()
            if obj.name == name and (not kind or obj.kind == kind)]


def read_store(handle, uid: int) -> Optional["tttrlib.DataStore"]:
    """Object *uid* as a table, or ``None`` when it is not a readable store."""
    try:
        return tttrlib.pto_store(handle, int(uid))
    except Exception:  # noqa: BLE001 - a JSON blob, a photon stream, ...
        return None


def software() -> str:
    """``"ndxplorer <version>"``: what a write records as its software."""
    try:
        from importlib.metadata import version

        return f"ndxplorer {version('ndxplorer')}"
    except Exception:  # noqa: BLE001 - not installed as a distribution
        return "ndxplorer"

