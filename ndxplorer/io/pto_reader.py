"""Read a burst analysis straight out of a `.pto` measurement container.

The analysis writes its results into the measurement's own container: the
photons and every table computed from them in one file. Each table is a plain
columnar store, so there is no merge by counting rows and no interleaved
padding to strip -- both were artefacts of the old text folders (containers
written from such tables still carry the row interleave; it is dropped on
read). The burst
search tables that share the latest settings are read and stacked by rows; a
companion analysis (.bg4, .br4, .by4, .bv4, .2c4, .kc4, .td4) is another table,
joined on its declared key; MMFDB provenance tags are carried onto the result.
A container with no bursts is read as its newest image (pixel-grain) table.

tttrlib reads the container (:mod:`ndxplorer.io.container`); ChiSurf and IMP are
not needed, so a `.pto` opens in ndX -- desktop or browser -- without them.
"""

from __future__ import annotations

import json
import logging
import pathlib
from typing import Any, Dict, Optional

import tttrlib

from ndxplorer.core.data_source import DataSource, float_column
from ndxplorer.io import tables
from ndxplorer.io.container import open_container, read_store

__all__ = ["is_container", "read_container"]

#: What ChiSurf's measurement container is called on disk.
SUFFIX = ".pto"

#: Tables holding one row per burst.
_BURST_GRAIN = "burst"

#: Tables holding one row per pixel: an image, read when there are no bursts.
_PIXEL_GRAIN = "pixel"

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
            f"{path.name} holds no burst or image table: convert the photons with a "
            "burst search first, or point ndX at the analysis folder if one was written."
        )

    logging.info("Reading %d burst table(s) from %s: %s", len(frames), path, names)
    combined = tables.concat_columns(frames)

    # Apply ChiSurf unit conventions (convert ms to s). The seconds column goes
    # at the end, where the milliseconds column is removed from.
    for milliseconds in (_MACRO_MS, "Mean Macrotime (ms)"):
        index = combined.find(milliseconds)
        if index < 0:
            continue
        seconds = float_column(combined, index) / 1000.0
        combined.remove_column(index)
        existing = combined.find(_MACRO_S)
        if existing >= 0:
            combined.remove_column(existing)
        combined.add(_MACRO_S, seconds)
        break

    ds = DataSource(combined)

    # Attach mapped MMFDB provenance metadata
    setattr(ds, "provenance", provenance)
    if hasattr(ds, "metadata") and isinstance(ds.metadata, dict):
        ds.metadata["provenance"] = provenance
        ds.metadata["settings_hash"] = provenance.get("settings_hash", "")

    logging.info("Burst load complete: %d rows from %s with provenance mapped.", ds.size, path.name)
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
) -> tuple[list["tttrlib.DataStore"], list[str], Dict[str, Any]]:
    """Return the current burst (or image) table, companions, and mapped MMFDB provenance.

    tttrlib alone reads the container (:mod:`ndxplorer.io.container`), so a
    `.pto` opens without ChiSurf or IMP.
    """
    file_frames: list["tttrlib.DataStore"] = []
    all_names: list[str] = []
    provenance: Dict[str, Any] = {
        "container_path": str(path),
        "artifacts": {},
        "operations": {},
        "edges": [],
        "sources": [],
    }

    with open_container(path) as handle:
        objects = list(handle.objects())

        def tag(uid: int, item: str):
            return tttrlib.pto_tag(handle, uid, item)

        def _grain(uid: int) -> str:
            return tag(uid, "_mmfdb_artifact.row_grain") or ""

        def _frame(obj) -> Optional["tttrlib.DataStore"]:
            store = read_store(handle, obj.uid)
            if store is None:
                logging.debug("could not read %r from %s", obj.name, path)
                return None
            store = tttrlib.deinterleave_burst_rows(store)
            return None if store.n_rows() == 0 or store.n_columns() == 0 else store

        # Read file-level container profile tags
        provenance["container_profile"] = tag(0, "_mmfdb_container.profile") or "PTO.MFDB"
        provenance["profile_version"] = tag(0, "_mmfdb_container.profile_version") or "1.1"
        provenance["profile_read_version"] = tag(0, "_mmfdb_container.profile_read_version") or "1"

        # Populate source TTTR streams in provenance
        for obj in objects:
            if obj.kind in ("tttr_photon_stream", "photons", "instrument_file"):
                file_p = tag(obj.uid, "_mmfdb_artifact.file_path") or obj.name
                provenance["sources"].append({
                    "uid": obj.uid,
                    "name": obj.name,
                    "kind": obj.kind,
                    "encoding": obj.encoding,
                    "file_path": file_p,
                })

        def _is_search(obj) -> bool:
            return (_grain(obj.uid) == _BURST_GRAIN
                    and tag(obj.uid, "_mmfdb_operation.operation_type") == _SEARCH)

        if table is not None:
            candidates = [obj for obj in objects if obj.name == table]
        else:
            # The bursts; a measurement without any is read as its newest image
            # table (a pixel-grain map), which ndX shows as an image.
            candidates = [obj for obj in objects if _is_search(obj)] or \
                [obj for obj in objects if _grain(obj.uid) == _PIXEL_GRAIN][-1:]
        if not candidates:
            return [], [], provenance

        # Find search settings hash of the latest run
        latest = candidates[-1]
        target_hash = tag(latest.uid, "_mmfdb_operation.settings_hash") or ""
        provenance["settings_hash"] = target_hash

        primaries = [
            obj for obj in candidates
            if (tag(obj.uid, "_mmfdb_operation.settings_hash") or "") == target_hash
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
            src_uid = tag(primary.uid, "_mmfdb_edge.source_uid") or tag(primary.uid, "_mmfdb_edge.source_node_id")
            primary_settings = _parse_json(tag(primary.uid, "_mmfdb_operation.settings_json"))
            grain = _grain(primary.uid) or _BURST_GRAIN
            operation = tag(primary.uid, "_mmfdb_operation.operation_type") or _SEARCH

            provenance["artifacts"][primary.uid] = {
                "name": primary.name,
                "row_grain": grain,
                "data_format": tag(primary.uid, "_mmfdb_artifact.data_format") or "bur",
                "operation_type": operation,
                "source_uid": src_uid,
                "settings_hash": target_hash,
                "settings": primary_settings,
            }
            provenance["operations"][operation] = primary_settings

            if src_uid:
                provenance["edges"].append({"source": src_uid, "target": primary.uid, "type": "derived_from"})

            # Discover companion tables (.bg4, .br4, .by4, .bv4, .kc4, etc.) for this primary
            # (An image table has none: maps of one grain are not joined by row.)
            for obj in objects if grain == _BURST_GRAIN else ():
                if obj.uid == primary.uid or _grain(obj.uid) != _BURST_GRAIN:
                    continue
                op_type = str(tag(obj.uid, "_mmfdb_operation.operation_type") or "").lower()
                fmt = str(tag(obj.uid, "_mmfdb_artifact.data_format") or "").lower()
                c_src = tag(obj.uid, "_mmfdb_edge.source_uid") or tag(obj.uid, "_mmfdb_edge.source_node_id")
                parent_op = tag(obj.uid, "_mmfdb_operation.parent_operation")

                is_linked = (
                    primary.uid in tttrlib.pto_parents(handle, obj.uid)
                    or c_src == primary.uid
                    or parent_op == primary.uid
                    or op_type in _COMPANION_TYPES
                    or fmt in _COMPANION_TYPES
                )
                if not is_linked:
                    continue

                companion = _frame(obj)
                if companion is None or companion.n_rows() != built.n_rows():
                    continue
                current_frames.append(companion)
                all_names.append(obj.name)

                comp_settings = _parse_json(tag(obj.uid, "_mmfdb_operation.settings_json"))

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

            file_frames.append(tables.concat_columns(current_frames))

    if not file_frames:
        return [], [], provenance

    if len(file_frames) == 1:
        return [file_frames[0]], all_names, provenance

    # Multiple ingested files: stack rows vertically across files
    return [tables.concat_rows(file_frames)], all_names, provenance
