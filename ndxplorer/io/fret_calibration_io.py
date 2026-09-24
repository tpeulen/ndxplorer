"""Save and load an accurate-FRET calibration.

A calibration is a handful of numbers — gamma, alpha, beta, delta, R0, the
backgrounds — that took a measurement and a fit to obtain. Losing them means
running the calibration again on data that may no longer be open, and typing
them into another window by hand is how a factor ends up transcribed wrong.

**The default place to keep them is the measurement itself.** A `.pto`
container already holds the photon stream, the burst table and the background
estimate; a calibration determined *from* that measurement belongs beside them,
not in a stray file next to it that a later copy will leave behind. So
:func:`save_calibration` writes into the container when the window has one, and
falls back to a JSON file only when it does not, or when the caller asks.

Both routes write the same JSON payload, so a calibration read out of a
container and one read out of a file are the same object.

The payload carries more than the numbers: the report text the calibration
printed, the uncertainties, which factors were actually written and which were
held fixed, and where it came from. A bare set of factors cannot answer "was
this gamma fitted here, or carried in from a reference sample?", and that is the
question a reader has a year later.

Both windows use this module: the Qt window through ChiSurf's ndX plugin and
the emtk app's Accurate FRET feature. A "window" here is anything with a
``data_source`` whose ``provenance`` names the container (the `.pto` reader
sets it). The container route is tttrlib's (:mod:`ndxplorer.io.container`,
as the `.pto` reader is); neither route needs ChiSurf.
"""

from __future__ import annotations

import datetime
import json
import logging
import pathlib
from typing import Any

import tttrlib

from .container import open_container, software

__all__ = [
    "CALIBRATION_ARTIFACT",
    "FORMAT",
    "SUFFIX",
    "container_of",
    "payload",
    "read_payload",
    "save_calibration",
    "load_calibration",
    "restorable",
    "saved_constants",
    "stored_calibrations",
]

#: Object name inside a `.pto` container. One name, so a later save is found
#: as another version of the same thing rather than as an unrelated object.
CALIBRATION_ARTIFACT = "fret_calibration"

#: Suffix for the file fallback. Plain JSON, deliberately: a calibration a
#: person may need to read, diff or mail should not need this program to open.
SUFFIX = ".fretcal.json"

#: What a calibration file says it is.
FORMAT = "chisurf.fret_calibration"

#: Payload version. Bumped when a field changes meaning, never when one is
#: added — a reader that does not know a key ignores it.
VERSION = 1


def container_of(ndx) -> str:
    """The `.pto` file the window's data came from, or ``""``.

    The same provenance lookup the background step uses: the burst table
    records the container it was read from, so the calibration can be written
    back to it without asking the user where the measurement lives.
    """
    data_source = getattr(ndx, "data_source", None)
    provenance = getattr(data_source, "provenance", None) or {}
    container = provenance.get("container_path") or ""
    if not container:
        metadata = getattr(data_source, "metadata", None) or {}
        container = (metadata.get("provenance") or {}).get("container_path", "")
    return str(container or "")


def payload(constants: dict, *, result: dict | None = None, note: str = "",
            vectors: dict | None = None) -> bytes:
    """The bytes written by either route (and by a window that saves them itself).

    Parameters
    ----------
    constants : dict
        The ndX constants as they now stand.
    result : dict, optional
        The calibration's result, for the report and uncertainties.
    note : str, optional
        A line saying what this calibration is of.
    vectors : dict, optional
        The window's vector constants, ``{name: {"populations": [...], "values":
        [...], "column", "probabilities", "uncertainties"}}``. Stored as lists,
        so population order and the per-burst axis survive the key-sorted JSON
        that the flat ``"gamma[FRET 1]"`` constants alone did not.

    Returns
    -------
    bytes
        UTF-8 JSON.
    """
    result = result or {}
    doc: dict[str, Any] = {
        "format": FORMAT,
        "version": VERSION,
        "saved_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(
            timespec="microseconds"
        ),
        "constants": {
            str(k): (float(v) if isinstance(v, (int, float)) else v)
            for k, v in dict(constants or {}).items()
        },
    }
    if note:
        doc["note"] = str(note)
    vectors = vectors if vectors is not None else result.get("vectors")
    if vectors:
        doc["vectors"] = json.loads(json.dumps(vectors, default=float))
    for key in (
        "factors",
        "uncertainties",
        "held",
        "determined",
        "report",
        "background",
        "background_fitted",
        "columns",
    ):
        if key in result and result[key] not in (None, {}, []):
            doc[key] = result[key]
    return json.dumps(doc, indent=2, sort_keys=True).encode("utf-8")


#: How many saved calibrations a measurement keeps. A FIFO rather than a single
#: slot: the previous one is what you compare against when a new calibration
#: comes out differently, and the one before that is what you go back to when it
#: turns out worse. Unbounded is not the alternative -- a container reached
#: thirteen of these in one session, and every reader then walks them all.
CALIBRATION_HISTORY = 5


def _saved_at(handle, uid) -> str:
    """The ``saved_utc`` recorded in one calibration, or ``""``.

    Sorting on this rather than on the object's position is what makes the
    history reliable once anything has been removed.
    """
    try:
        return str(json.loads(tttrlib.pto_read_blob(handle, uid).decode("utf-8"))
                   .get("saved_utc", ""))
    except Exception:
        return ""


def _prune_calibrations(handle, keep: int = CALIBRATION_HISTORY) -> int:
    """Drop all but the newest *keep* saved calibrations. Returns how many went.

    The container appends, so saving is what makes the history grow; pruning
    here means the bound holds however the window is used, rather than depending
    on somebody remembering to tidy up.
    """
    try:
        entries = [
            (_saved_at(handle, obj.uid), index, obj.uid)
            for index, obj in enumerate(handle.objects())
            if getattr(obj, "name", "") == CALIBRATION_ARTIFACT
        ]
    except Exception:
        return 0
    # By the timestamp *in the payload*, not by position. Removing an object
    # frees its slot and the next write reuses it, so after the very first prune
    # the order of ``objects()`` no longer tells you which calibration is newer
    # -- and a FIFO that drops the wrong end is worse than no FIFO at all.
    entries.sort()
    uids = [uid for _, _, uid in entries]
    dropped = 0
    for uid in uids[: max(0, len(uids) - int(keep))]:
        try:
            if handle.remove(uid):
                dropped += 1
        except Exception:
            continue
    return dropped


def _dictionary() -> dict:
    """The MMFDB dictionary a write names, when the ``mmfdb`` package is there."""
    try:
        from mmfdb.schema.pdbx_metadata import (
            extension_dictionary_hash,
            extension_dictionary_version,
        )

        return {"dictionary_version": extension_dictionary_version(),
                "dictionary_hash": extension_dictionary_hash()}
    except Exception:  # noqa: BLE001 - optional: the calibration is written without it
        return {}


def save_calibration(
    constants: dict,
    *,
    ndx=None,
    path: str | None = None,
    result: dict | None = None,
    note: str = "",
    embed: bool = True,
    vectors: dict | None = None,
) -> dict:
    """Write a calibration to the measurement container, or to a file.

    Parameters
    ----------
    constants : dict
        The ndX constants as they now stand — what the window will use.
    ndx : object, optional
        The window, used to find its `.pto` container.
    path : str, optional
        Write here instead. Given a path, the file route is always taken.
    result : dict, optional
        The optimizer's return value, for the report and uncertainties.
    note : str, optional
        A line from the user saying what this calibration is of.
    embed : bool, optional
        Prefer the container (default). ``False`` forces the file route.
    vectors : dict, optional
        The window's vector constants (see :func:`payload`).

    Returns
    -------
    dict
        ``{"ok", "where", "target"}``; ``{"ok": False, "error": …}`` on failure.
        ``where`` is ``"container"`` or ``"file"`` — the caller should say which
        happened rather than claim "saved".
    """
    data = payload(constants, result=result, note=note, vectors=vectors)

    if path is None and embed:
        container = container_of(ndx)
        if container:
            try:
                with open_container(container, writable=True) as handle:
                    tttrlib.pto_add_blob(
                        handle,
                        "calibration_data",
                        "json",
                        CALIBRATION_ARTIFACT,
                        data,
                        operation_type="calibration",
                        mime_type="application/json",
                        software=software(),
                        **_dictionary(),
                    )
                    dropped = _prune_calibrations(handle)
                if dropped:
                    logging.info(
                        "calibration saved; dropped %d older one(s), keeping the last %d",
                        dropped,
                        CALIBRATION_HISTORY,
                    )
                return {"ok": True, "where": "container", "target": container}
            except Exception as exc:  # noqa: BLE001
                # Fall through to the file route rather than lose the numbers:
                # a read-only container or a lock held by another window is a
                # reason to write elsewhere, not a reason to write nothing.
                fallback = str(exc)
                if path is None:
                    stem = pathlib.Path(container).with_suffix("")
                    path = str(stem) + SUFFIX
                pathlib.Path(path).write_bytes(data)
                return {
                    "ok": True,
                    "where": "file",
                    "target": path,
                    "warning": f"could not write into the container ({fallback})",
                }

    if path is None:
        return {"ok": False, "error": "no container for this window and no path given"}
    try:
        pathlib.Path(path).write_bytes(data)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}
    return {"ok": True, "where": "file", "target": path}


def stored_calibrations(ndx=None, container: str | None = None) -> list[dict]:
    """Every calibration stored in the container, **oldest first**.

    Returns a list of ``{"uid", "saved_utc", "note", "constants", …}``. The
    container keeps each save as its own object, so an earlier calibration is
    still there after a later one is written — which is the point of putting
    them in the measurement rather than overwriting a file.

    The order is taken from each payload's own ``saved_utc``, not from the
    order the container lists objects in. Two separate things make position
    unusable: the container was observed to list objects newest-first, which
    silently made "the latest calibration" the oldest one, and removing an
    object (which :func:`_prune_calibrations` does) frees a slot that the next
    save reuses, so from the first prune onwards position is not even a
    permutation of write order. The timestamp is recorded to the microsecond
    so that two saves in one second still order; the uid only breaks a tie.
    """
    target = container or container_of(ndx)
    if not target:
        return []
    try:
        out = []
        with open_container(target) as handle:
            for obj in handle.objects():
                # By name, as the pruning is: a container written by an older
                # ChiSurf filed some as `analysis_result`.
                if obj.name != CALIBRATION_ARTIFACT:
                    continue
                try:
                    doc = json.loads(tttrlib.pto_read_blob(handle, obj.uid).decode("utf-8"))
                except Exception:  # noqa: BLE001
                    continue
                doc["uid"] = int(obj.uid)
                out.append(doc)
        out.sort(key=lambda d: (str(d.get("saved_utc", "")), int(d.get("uid", 0))))
        return out
    except Exception:  # noqa: BLE001
        return []


def saved_constants(container: str) -> dict:
    """The newest stored calibration's constants: the numeric, finite ones.

    ``{}`` when the measurement carries none.
    """
    stored = stored_calibrations(container=container)
    return _numeric(stored[-1].get("constants")) if stored else {}


def _numeric(constants) -> dict:
    import math

    return {str(k): float(v) for k, v in dict(constants or {}).items()
            if isinstance(v, (int, float)) and math.isfinite(float(v))}


def restorable(container: str) -> dict:
    """What a measurement stores for ndX's constants, to restore when it is opened.

    Returns
    -------
    dict
        ``{"saved": {...}, "background": {...}, "vectors": {...}}``: the newest
        saved calibration (its constants as :func:`saved_constants` reads
        them, and its vector constants) and the background step's rates as
        ``Bg``/``Br``/``By``. Both name Bg/Br/By, so one has to win: the
        *newer* of the two objects. A background re-measured after the
        calibration was saved is the ordinary order of work, and then the saved
        values for those constants are dropped. Applied, ``saved`` goes over
        ``background``.
    """
    from ..analysis.fret_background import stored_background_constants

    stored = stored_calibrations(container=container)
    saved = _numeric(stored[-1].get("constants")) if stored else {}
    vectors = dict(stored[-1].get("vectors") or {}) if stored else {}
    background = stored_background_constants(container)
    if saved and background:
        try:
            with open_container(container) as handle:
                names = [obj.name for obj in handle.objects()]
        except Exception:  # noqa: BLE001
            names = []

        def last(name: str) -> int:
            return max((i for i, n in enumerate(names) if n == name), default=-1)

        if last("background") > last(CALIBRATION_ARTIFACT) >= 0:
            saved = {k: v for k, v in saved.items() if k not in background}
    return {"saved": saved, "background": background, "vectors": vectors}


def read_payload(data, *, target: str = "") -> dict:
    """A calibration file's content, read back.

    Parameters
    ----------
    data : bytes or str
        What :func:`payload` wrote.
    target : str, optional
        Where it came from, for the messages and the result.

    Returns
    -------
    dict
        As :func:`load_calibration` with a path: ``where`` is ``"file"``.
    """
    try:
        if isinstance(data, (bytes, bytearray)):
            data = bytes(data).decode("utf-8")
        doc = json.loads(data)
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "error": str(exc)}
    if not isinstance(doc, dict) or doc.get("format") != FORMAT:
        return {"ok": False, "error": f"{target or 'this file'} is not a ChiSurf FRET calibration"}
    return {
        "ok": True,
        "where": "file",
        "target": target,
        "constants": doc.get("constants") or {},
        "saved_utc": doc.get("saved_utc", ""),
        "note": doc.get("note", ""),
        "report": doc.get("report", ""),
        "vectors": doc.get("vectors") or {},
        "document": doc,
    }


def load_calibration(*, ndx=None, path: str | None = None, uid: int | None = None) -> dict:
    """Read a calibration back.

    With *path*, reads that file. Otherwise reads the newest calibration stored
    in the window's container, or the one named by *uid*.

    Returns
    -------
    dict
        ``{"ok", "constants", "where", "target", "saved_utc", "note", "report"}``
        or ``{"ok": False, "error": …}``. Nothing is applied — the caller
        decides whether to write these into the window, because replacing a
        calibration is a decision and this function is a reader.
    """
    if path:
        try:
            data = pathlib.Path(path).read_bytes()
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}
        return read_payload(data, target=str(path))

    stored = stored_calibrations(ndx)
    if not stored:
        return {"ok": False, "error": "this measurement carries no stored calibration"}
    if uid is not None:
        stored = [d for d in stored if d.get("uid") == int(uid)] or stored
    doc = stored[-1]
    return {
        "ok": True,
        "where": "container",
        "target": container_of(ndx),
        "constants": doc.get("constants") or {},
        "saved_utc": doc.get("saved_utc", ""),
        "note": doc.get("note", ""),
        "report": doc.get("report", ""),
        "vectors": doc.get("vectors") or {},
        "document": doc,
    }
