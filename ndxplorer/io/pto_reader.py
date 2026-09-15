"""Read a burst analysis straight out of a `.pto` measurement container.

The analysis writes its results into the measurement's own container: the
photons and every table computed from them in one file. Each table is a plain
columnar store, so there is no merge by counting rows and no interleaved
padding to strip -- both were artefacts of the old text folders. The burst
search tables that share the latest settings are read and stacked by rows; a
companion analysis (.bg4, .br4, .by4, .bv4, .2c4, .kc4, .td4) is another table,
joined on its declared key; MMFDB provenance tags are carried onto the result.
"""

from __future__ import annotations

import json
import logging
import pathlib
from typing import Any, Dict, Optional

import pandas as pd

from ndxplorer.core.data_source import DataSource

__all__ = ["is_container", "read_container"]

#: What ChiSurf's measurement container is called on disk.
SUFFIX = ".pto"

#: Tables holding one row per burst.
_BURST_GRAIN = "burst"

#: The operation that produces the burst list itself.
_SEARCH = "burst_selection"

#: Companion operation types and data-format extensions this recognises.
#:
#: The `_mmfdb_operation.operation_type` values are **dictionary terms**. The
#: informal spellings that used to be here — `mle_green`, `bva`, `kde_cde` — are
#: not in the MMFDB vocabulary and no writer emits them any more; ChiSurf's own
#: writer would refuse to, and the compiled `tttr` CLI was corrected to
#: `burst_lifetime_fitting` / `burst_variance_analysis` / `burst_2cde`. They are
#: kept below only so a container written before that still opens.
#:
#: This list is a *fallback*. A companion is normally recognised by its parent
#: edge, which is why the rename did not break anything — but a container whose
#: edge is missing is exactly the case this catches, so it has to name the terms
#: writers actually use.
_COMPANION_TYPES = {
    # current, from the dictionary
    "burst_lifetime_fitting", "burst_variance_analysis", "burst_2cde",
    "burst_correlation", "burst_fusion", "photon_hmm",
    # legacy, for containers written before the vocabulary was enforced
    "mle_green", "mle_red", "mle_yellow", "bva", "kde_cde", "time_delay",
    # data_format extensions, unchanged
    "2c4", "kc4", "bg4", "br4", "by4", "bv4", "td4",
}

#: Columns the `.bur` reader renames on the way in.
_MACRO_MS = "Mean Macro Time (ms)"
_MACRO_S = "Mean Macro Time (s)"


def is_container(path: str | pathlib.Path) -> bool:
    """Return whether *path* is a measurement container ndX can read bursts from."""
    p = pathlib.Path(path)
    return p.is_file() and p.suffix.lower() == SUFFIX


def read_container(
    path: str | pathlib.Path, *, table: Optional[str] = None
) -> DataSource:
    """Return the burst table (and every per-burst result beside it) as a DataSource.

    Maps container provenance metadata onto DataSource.provenance / DataSource.metadata.
    """
    path = pathlib.Path(path)
    frames, names, provenance = _burst_frames(path, table)
    if not frames:
        raise FileNotFoundError(
            f"{path.name} holds no burst table: convert the photons with a burst "
            "search first, or point ndX at the analysis folder if one was written."
        )

    logging.info("Reading %d burst table(s) from %s: %s", len(frames), path, names)
    combined = pd.concat(frames, axis=1) if len(frames) > 1 else frames[0]
    combined = combined.loc[:, ~combined.columns.duplicated()]

    # Apply ChiSurf unit conventions (convert ms to s)
    if _MACRO_MS in combined.columns:
        combined = combined.assign(**{_MACRO_S: pd.to_numeric(combined[_MACRO_MS], errors="coerce") / 1000.0}).drop(columns=[_MACRO_MS])
    elif "Mean Macrotime (ms)" in combined.columns:
        combined = combined.assign(**{_MACRO_S: pd.to_numeric(combined["Mean Macrotime (ms)"], errors="coerce") / 1000.0}).drop(columns=["Mean Macrotime (ms)"])

    ds = DataSource()
    ds.data = combined.reset_index(drop=True)

    # Attach mapped MMFDB provenance metadata
    setattr(ds, "provenance", provenance)
    if hasattr(ds, "metadata") and isinstance(ds.metadata, dict):
        ds.metadata["provenance"] = provenance
        ds.metadata["settings_hash"] = provenance.get("settings_hash", "")

    logging.info("Burst load complete: %d rows from %s with provenance mapped.", len(ds.data), path.name)
    return ds


def _parse_json(val: Any) -> Dict[str, Any]:
    if isinstance(val, dict):
        return val
    if not val:
        return {}
    try:
        data = json.loads(val)
        if isinstance(data, str):
            data = json.loads(data)
        return data if isinstance(data, dict) else {"_value": data}
    except Exception:
        return {"_raw": str(val)}

def _burst_frames(
    path: pathlib.Path, table: Optional[str]
) -> tuple[list[pd.DataFrame], list[str], Dict[str, Any]]:
    """Return the current burst table, companions, and mapped MMFDB provenance."""
    from chisurf.core.datastore import column_names
    from chisurf.core.fio.pto import Measurement

    file_frames: list[pd.DataFrame] = []
    all_names: list[str] = []
    provenance: Dict[str, Any] = {
        "container_path": str(path),
        "artifacts": {},
        "operations": {},
        "edges": [],
        "sources": [],
    }

    with Measurement.open(path, writable=False) as measurement:

        def _grain(uid: int) -> str:
            return measurement.tag(uid, "_mmfdb_artifact.row_grain") or ""

        def _frame(obj) -> Optional[pd.DataFrame]:
            try:
                store = measurement.get_store(obj.uid)
            except Exception:  # noqa: BLE001
                logging.debug("could not read %r from %s", obj.name, path, exc_info=True)
                return None
            from chisurf.core.fio.fluorescence.burst_container import (
                deinterleave_bursts,
            )

            store = deinterleave_bursts(store)
            built = pd.DataFrame(
                {name: _column(store, name) for name in column_names(store)}
            )
            return None if built.empty else built

        # Read file-level container profile tags
        provenance["container_profile"] = measurement.tag(0, "_mmfdb_container.profile") or "PTO.MFDB"
        provenance["profile_version"] = measurement.tag(0, "_mmfdb_container.profile_version") or "1.1"
        provenance["profile_read_version"] = measurement.tag(0, "_mmfdb_container.profile_read_version") or "1"

        # Populate source TTTR streams in provenance
        for obj in measurement.artifacts():
            if obj.kind in ("tttr_photon_stream", "photons", "instrument_file"):
                file_p = measurement.tag(obj.uid, "_mmfdb_artifact.file_path") or obj.name
                provenance["sources"].append({
                    "uid": obj.uid,
                    "name": obj.name,
                    "kind": obj.kind,
                    "encoding": obj.encoding,
                    "file_path": file_p,
                })

        def _is_candidate(obj) -> bool:
            if table is not None:
                return obj.name == table
            return (
                _grain(obj.uid) == _BURST_GRAIN
                and measurement.tag(obj.uid, "_mmfdb_operation.operation_type") == _SEARCH
            )

        candidates = [obj for obj in measurement.artifacts() if _is_candidate(obj)]
        if not candidates:
            return [], [], provenance

        # Find search settings hash of the latest run
        latest = candidates[-1]
        target_hash = measurement.tag(latest.uid, "_mmfdb_operation.settings_hash") or ""
        provenance["settings_hash"] = target_hash

        primaries = [
            obj for obj in candidates
            if (measurement.tag(obj.uid, "_mmfdb_operation.settings_hash") or "") == target_hash
        ]
        if not primaries:
            primaries = [latest]

        for primary in primaries:
            built = _frame(primary)
            if built is None:
                continue

            current_frames = [built]
            all_names.append(primary.name)

            # Map primary provenance node
            src_uid = measurement.tag(primary.uid, "_mmfdb_edge.source_uid") or measurement.tag(primary.uid, "_mmfdb_edge.source_node_id")
            primary_settings = _parse_json(measurement.tag(primary.uid, "_mmfdb_operation.settings_json"))

            provenance["artifacts"][primary.uid] = {
                "name": primary.name,
                "row_grain": "burst",
                "data_format": measurement.tag(primary.uid, "_mmfdb_artifact.data_format") or "bur",
                "operation_type": "burst_selection",
                "source_uid": src_uid,
                "settings_hash": target_hash,
                "settings": primary_settings,
            }
            provenance["operations"]["burst_selection"] = primary_settings

            if src_uid:
                provenance["edges"].append({"source": src_uid, "target": primary.uid, "type": "derived_from"})

            # Discover companion tables (.bg4, .br4, .by4, .bv4, .kc4, etc.) for this primary
            for obj in measurement.artifacts():
                if obj.uid == primary.uid or _grain(obj.uid) != _BURST_GRAIN:
                    continue
                op_type = str(measurement.tag(obj.uid, "_mmfdb_operation.operation_type") or "").lower()
                fmt = str(measurement.tag(obj.uid, "_mmfdb_artifact.data_format") or "").lower()
                c_src = measurement.tag(obj.uid, "_mmfdb_edge.source_uid") or measurement.tag(obj.uid, "_mmfdb_edge.source_node_id")
                parent_op = measurement.tag(obj.uid, "_mmfdb_operation.parent_operation")

                is_linked = (
                    primary.uid in measurement.parents(obj.uid)
                    or c_src == primary.uid
                    or parent_op == primary.uid
                    or op_type in _COMPANION_TYPES
                    or fmt in _COMPANION_TYPES
                )
                if not is_linked:
                    continue

                companion = _frame(obj)
                if companion is None or len(companion) != len(built):
                    continue
                current_frames.append(companion)
                all_names.append(obj.name)

                comp_settings = _parse_json(measurement.tag(obj.uid, "_mmfdb_operation.settings_json"))

                provenance["artifacts"][obj.uid] = {
                    "name": obj.name,
                    "row_grain": "burst",
                    "data_format": fmt,
                    "operation_type": op_type,
                    "parent_operation": parent_op or primary.uid,
                    "settings": comp_settings,
                }
                if op_type:
                    provenance["operations"][op_type] = comp_settings

                provenance["edges"].append({"source": primary.uid, "target": obj.uid, "type": "companion_of"})

            file_frame = pd.concat(current_frames, axis=1) if len(current_frames) > 1 else current_frames[0]
            file_frames.append(file_frame)

    if not file_frames:
        return [], [], provenance

    if len(file_frames) == 1:
        return [file_frames[0]], all_names, provenance

    # Multiple ingested files: stack rows vertically across files
    stacked = pd.concat(file_frames, axis=0, ignore_index=True)
    return [stacked], all_names, provenance


def _column(store: Any, name: str):
    """Return one column as something pandas can hold, numbers stayed numbers."""
    import numpy as np

    return np.asarray(store[name])
