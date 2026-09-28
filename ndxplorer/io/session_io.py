"""The analysis view of a measurement, kept in the measurement.

What a person set up to look at a measurement -- the axes, the gates, the
clusters, the curves, the Gaussians, the colours -- took work, and it belongs
to *that* measurement. So ndX writes it into the `.pto` container, beside the
bursts and the calibrations, as one JSON object: opening the file again brings
the window back to where it was left.

The object is named :data:`SESSION_ARTIFACT` and is an
``_mmfdb_artifact.artifact_kind`` :data:`ARTIFACT_KIND` (a term of mmfdb's
``mmfdb_flr_ext.dic``). Like the calibrations (:mod:`.fret_calibration_io`)
the last :data:`SESSION_HISTORY` are kept, ordered by their own ``saved_utc``,
and every write takes the container's writer lock.

The payload records the table it was made on (:func:`table_identity`), so a
state saved on another table -- a re-run burst search, different columns --
is recognised and applied only where it still fits.

This module reads and writes bytes; what the state *contains* is the app's
(:mod:`ndxplorer.app.session_state`). tttrlib alone, no ChiSurf.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import logging
from typing import Any, Dict, List, Optional, Sequence

import tttrlib

from .container import open_container, software

__all__ = [
    "ARTIFACT_KIND",
    "FORMAT",
    "SCHEMA_VERSION",
    "SESSION_ARTIFACT",
    "SESSION_HISTORY",
    "forget_sessions",
    "latest_session",
    "payload",
    "save_session",
    "stored_sessions",
    "table_identity",
]

logger = logging.getLogger(__name__)

#: Object name inside the container: one name, so a later save is another
#: version of the same thing.
SESSION_ARTIFACT = "ndx_session"
#: The artifact kind (mmfdb dictionary term, software-agnostic).
ARTIFACT_KIND = "analysis_view_state"
#: The operation that wrote it (an existing mmfdb term).
OPERATION_TYPE = "project_snapshot"
#: What the payload says it is.
FORMAT = "ndx.analysis_view_state"
#: Bumped when a field changes meaning; a reader ignores keys it does not know.
SCHEMA_VERSION = 1
#: How many saved states a measurement keeps (as the calibrations: the last
#: few, not all -- every open reads them).
SESSION_HISTORY = 5


def table_identity(names: Sequence[str], n_rows: int) -> Dict[str, Any]:
    """What identifies the table a state was made on: its columns and row count.

    ``columns_sha256`` hashes the column names in order; two tables with the
    same columns and rows are taken to be the same table.
    """
    blob = json.dumps([str(n) for n in names], separators=(",", ":")).encode("utf-8")
    return {"columns_sha256": hashlib.sha256(blob).hexdigest(), "n_rows": int(n_rows),
            "n_columns": len(names)}


def _app_version() -> str:
    return software().partition(" ")[2] or "unknown"


def payload(state: Dict[str, Any], identity: Dict[str, Any], columns: Sequence[str] = ()
            ) -> bytes:
    """The bytes written: the state wrapped with format, versions and the table."""
    doc = {
        "format": FORMAT,
        "schema_version": SCHEMA_VERSION,
        "app_version": _app_version(),
        "saved_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(
            timespec="microseconds"),
        "table": dict(identity, columns=[str(c) for c in columns]),
        "state": state,
    }
    return json.dumps(doc, sort_keys=True, default=_jsonable).encode("utf-8")


def _jsonable(value):
    try:
        import numpy as np

        if isinstance(value, np.generic):
            return value.item()
        if isinstance(value, np.ndarray):
            return value.tolist()
    except ImportError:  # pragma: no cover
        pass
    if isinstance(value, (set, frozenset, tuple)):
        return list(value)
    raise TypeError(f"not JSON serialisable: {type(value).__name__}")


def _dictionary() -> dict:
    try:
        from mmfdb.schema.pdbx_metadata import (
            extension_dictionary_hash,
            extension_dictionary_version,
        )

        return {"dictionary_version": extension_dictionary_version(),
                "dictionary_hash": extension_dictionary_hash()}
    except Exception:  # noqa: BLE001 - optional
        return {}


def _read(handle, uid) -> Optional[dict]:
    try:
        doc = json.loads(tttrlib.pto_read_blob(handle, uid).decode("utf-8"))
    except Exception:  # noqa: BLE001 - a damaged one is skipped, not fatal
        return None
    return doc if isinstance(doc, dict) and doc.get("format") == FORMAT else None


def _entries(handle) -> List[tuple]:
    """``(saved_utc, uid, doc)`` of every stored state, oldest first."""
    out = []
    for obj in handle.objects():
        if obj.name != SESSION_ARTIFACT:
            continue
        doc = _read(handle, obj.uid)
        out.append((str((doc or {}).get("saved_utc", "")), int(obj.uid), doc))
    out.sort(key=lambda e: (e[0], e[1]))
    return out


def save_session(container: str, data: bytes, keep: int = SESSION_HISTORY) -> Dict[str, Any]:
    """Write *data* (:func:`payload`) into *container*; keep the newest *keep*.

    Returns
    -------
    dict
        ``{"ok": True, "uid", "dropped"}``, or ``{"ok": False, "error",
        "locked"}`` -- ``locked`` when another program holds the writer lock,
        which the caller says in words rather than failing.
    """
    try:
        with open_container(container, writable=True) as handle:
            uid = tttrlib.pto_add_blob(
                handle, ARTIFACT_KIND, "json", SESSION_ARTIFACT, bytes(data),
                operation_type=OPERATION_TYPE, mime_type="application/json",
                software=software(), **_dictionary())
            dropped = 0
            entries = _entries(handle)
            for _saved, old, _doc in entries[: max(0, len(entries) - int(keep))]:
                if handle.remove(old):
                    dropped += 1
        return {"ok": True, "uid": int(uid), "dropped": dropped}
    except tttrlib.PtoLockedError as exc:
        return {"ok": False, "locked": True, "error": str(exc)}
    except Exception as exc:  # noqa: BLE001 - reported by the caller
        return {"ok": False, "locked": False, "error": str(exc)}


def stored_sessions(container: str) -> List[dict]:
    """Every readable stored state, **oldest first**, each with its ``uid``."""
    try:
        with open_container(container) as handle:
            return [dict(doc, uid=uid) for _s, uid, doc in _entries(handle) if doc]
    except Exception:  # noqa: BLE001 - not a container: nothing stored
        return []


def latest_session(container: str) -> Optional[dict]:
    """The newest stored state of *container*, or ``None``."""
    stored = stored_sessions(container)
    return stored[-1] if stored else None


def forget_sessions(container: str) -> Dict[str, Any]:
    """Remove every stored state; ``{"ok", "removed"}`` or ``{"ok": False, …}``."""
    try:
        with open_container(container, writable=True) as handle:
            removed = sum(1 for _s, uid, _d in _entries(handle) if handle.remove(uid))
        return {"ok": True, "removed": removed}
    except tttrlib.PtoLockedError as exc:
        return {"ok": False, "locked": True, "error": str(exc)}
    except Exception as exc:  # noqa: BLE001
        return {"ok": False, "locked": False, "error": str(exc)}
