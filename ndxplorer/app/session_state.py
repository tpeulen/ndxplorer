"""The window's analysis view as plain data: what a session state holds.

:func:`collect` asks the model for its part (axes, colours, masks, the z gate,
the gates) and every feature for its own (``Feature.session_state``);
:func:`apply` hands each part back (``Feature.restore_session_state``). The
core knows nothing of clusters or curves: a feature that has state says so.

Everything is stored **by column name**, never by index, so a state still
applies to a table whose columns moved; what refers to a column the table does
not have is skipped and noted (:class:`SessionContext`), and the caller shows
the notes in the status line.

The container side (bytes, history, lock) is :mod:`ndxplorer.io.session_io`.
"""

from __future__ import annotations

import base64
import logging
import zlib
from typing import Any, Dict, List, Optional, Sequence

import numpy as np

__all__ = ["SessionContext", "apply", "collect", "pack_array", "unpack_array"]

logger = logging.getLogger(__name__)

AXES = ("x", "y", "z")
AXIS_FIELDS = ("bins_1d", "bins_2d", "lo", "hi", "log", "norm", "auto_scale")
VIEW_FIELDS = ("colormap", "log_counts", "vmin", "vmax", "mask_inf", "mask_nan",
               "z_gate_enabled", "z_dynamic", "weight_enabled")


def pack_array(values) -> Dict[str, Any]:
    """An array as ``{"dtype", "shape", "zlib_b64"}``: compact inside the JSON."""
    a = np.ascontiguousarray(values)
    return {"dtype": a.dtype.str, "shape": list(a.shape),
            "zlib_b64": base64.b64encode(zlib.compress(a.tobytes(), 6)).decode("ascii")}


def unpack_array(entry: Dict[str, Any]) -> np.ndarray:
    raw = zlib.decompress(base64.b64decode(entry["zlib_b64"]))
    return np.frombuffer(raw, dtype=np.dtype(entry["dtype"])).reshape(entry["shape"]).copy()


class SessionContext:
    """What a feature restoring its part needs to know about the table now.

    Attributes
    ----------
    names : list of str
        The columns of the table now loaded.
    n_rows : int
        Its row count.
    same_table : bool
        Whether the state was saved on this very table (columns and rows).
    rows_match : bool
        Whether the row count is the saved one: per-row state (cluster
        labels) only applies then.
    saved_utc : str
        When the state was saved.
    newer_calibration : bool
        A calibration was stored after the state: the constants it holds win.
    notes : list of str
        What could not be restored, one short phrase each.
    """

    def __init__(self, names: Sequence[str], n_rows: int, saved: Dict[str, Any],
                 same_table: bool, newer_calibration: bool = False) -> None:
        self.names = list(names)
        self.n_rows = int(n_rows)
        table = dict(saved.get("table") or {})
        self.rows_match = int(table.get("n_rows", -1)) == self.n_rows
        self.same_table = bool(same_table)
        self.saved_utc = str(saved.get("saved_utc", ""))
        self.newer_calibration = bool(newer_calibration)
        self.notes: List[str] = []

    def has(self, name: str) -> bool:
        return name in self.names

    def index_of(self, name: str) -> int:
        return self.names.index(name) if name in self.names else -1

    def skip(self, note: str) -> None:
        if note not in self.notes:
            self.notes.append(note)

    def missing(self, what: str, columns) -> bool:
        """Note and say ``True`` when one of *columns* is not in the table."""
        gone = [c for c in columns if c and c not in self.names]
        if gone:
            self.skip(f"{what} (no column {', '.join(repr(c) for c in gone)})")
        return bool(gone)


# ------------------------------------------------------------------ gates
def gate_state(row, names: Sequence[str]) -> Optional[Dict[str, Any]]:
    """One gate row by column names; ``None`` for one that cannot be kept."""
    def name_of(index) -> str:
        index = int(index)
        return names[index] if 0 <= index < len(names) else ""

    entry = {"kind": row.kind, "name": row.name, "invert": bool(row.invert),
             "enabled": bool(row.enabled)}
    kind = row.kind
    if kind == "Interval":
        entry.update(column=name_of(row.parameter_idx), lower=float(row.lower),
                     upper=float(row.upper))
    elif kind == "G2D":
        meta = dict(row.meta or {})
        entry.update(columns=[name_of(meta.get("idx1", row.parameter_idx)),
                              name_of(meta.get("idx2", row.parameter_idx))],
                     mu=meta.get("mu"), cov=meta.get("cov"), sigma=meta.get("sigma", 1.0),
                     log_x=bool(meta.get("log_x")), log_y=bool(meta.get("log_y")))
    elif kind == "Mask":
        sel = row.selection
        entry.update(columns=[name_of(sel.idx1), name_of(sel.idx2)],
                     mask=pack_array(np.asarray(sel.mask)),
                     edges1=[float(v) for v in np.asarray(sel.edges1, dtype=float)],
                     edges2=[float(v) for v in np.asarray(sel.edges2, dtype=float)])
    elif kind == "Region":
        sel = row.selection
        to_dict = getattr(sel.roi, "to_dict", None)
        if not callable(to_dict):
            return None
        entry.update(columns=[name_of(sel.idx1), name_of(sel.idx2)], roi=to_dict())
    return entry


def restore_gate(gates, entry: Dict[str, Any], ctx: SessionContext) -> bool:
    """Add the gate *entry* describes to *gates*; ``False`` (noted) when it cannot."""
    from ..core.data_source import MaskDataSelection

    kind = entry.get("kind")
    label = f"gate {entry.get('name') or kind}"
    common = dict(invert=bool(entry.get("invert")), enabled=bool(entry.get("enabled", True)))
    if kind == "Interval":
        column = entry.get("column", "")
        if ctx.missing(label, [column]):
            return False
        gates.add_interval(ctx.index_of(column), entry.get("name") or column,
                           entry["lower"], entry["upper"], **common)
        return True
    columns = list(entry.get("columns") or ["", ""])
    if ctx.missing(label, columns):
        return False
    i1, i2 = ctx.index_of(columns[0]), ctx.index_of(columns[1])
    if kind == "G2D":
        gates.add_gaussian(i1, i2, entry["mu"], entry["cov"], float(entry.get("sigma", 1.0)),
                           name=entry.get("name", ""), log_x=bool(entry.get("log_x")),
                           log_y=bool(entry.get("log_y")), **common)
        return True
    if kind == "Mask":
        sel = MaskDataSelection(i1, i2, unpack_array(entry["mask"]),
                                np.asarray(entry["edges1"], dtype=float),
                                np.asarray(entry["edges2"], dtype=float),
                                name=entry.get("name") or "Mask", **common)
        gates.add_selection(sel)
        return True
    if kind == "Region":
        try:
            from chisurf.core.roi.roi import roi_from_dict

            from ..core.region_selection import RegionDataSelection
        except ImportError:
            ctx.skip(f"{label} (drawn regions need ChiSurf's region module)")
            return False
        gates.add_selection(RegionDataSelection(roi_from_dict(entry["roi"]), i1, i2,
                                                name=entry.get("name"), **common))
        return True
    ctx.skip(f"{label} (unknown kind {kind!r})")
    return False


# ------------------------------------------------------------------ model
def model_state(model) -> Dict[str, Any]:
    """The model's part: the axes, the colours and masks, the z gate, the gates."""
    names = model.parameter_names
    state: Dict[str, Any] = {
        "axes": {key: dict({"name": model.axis(key).name},
                           **{f: getattr(model.axis(key), f) for f in AXIS_FIELDS})
                 for key in AXES},
        "weight": model.weight_name,
        "z_range": [float(v) for v in model.z_range],
        "gates": [g for g in (gate_state(row, names) for row in model.gates) if g],
    }
    state.update({f: getattr(model, f) for f in VIEW_FIELDS})
    return state


def restore_model(model, state: Dict[str, Any], ctx: SessionContext) -> None:
    """Apply :func:`model_state`; the colour limits are handed back separately
    (:func:`colour_limits`) because a recompute sets them afresh."""
    for key in AXES:
        axis_state = dict((state.get("axes") or {}).get(key) or {})
        name = axis_state.get("name", "")
        if not name:
            continue
        if ctx.missing(f"{key} axis", [name]):
            continue
        axis = model.axis(key)
        model.set_parameter(key, name)
        for field in AXIS_FIELDS:
            if field in axis_state and not (key == "z" and field == "bins_2d"):
                setattr(axis, field, type(getattr(axis, field))(axis_state[field]))
    weight = state.get("weight", "")
    if weight and not ctx.missing("weight", [weight]):
        model.weight_name = weight
    for field in VIEW_FIELDS:
        if field in state and field not in ("vmin", "vmax"):
            setattr(model, field, type(getattr(model, field))(state[field]))
    if model.colormap not in model.colormap_options():
        model.colormap = "viridis"
    if state.get("z_range"):
        model.set_z_range(*state["z_range"][:2])
    model.gates.clear()
    for entry in state.get("gates") or []:
        try:
            restore_gate(model.gates, entry, ctx)
        except Exception as exc:  # noqa: BLE001 - one bad gate drops only itself
            ctx.skip(f"gate {entry.get('name', '')} ({exc})")
    model.selected_gate = None
    model.invalidate()


def colour_limits(state: Dict[str, Any]) -> Optional[tuple]:
    if "vmin" in state and "vmax" in state:
        return float(state["vmin"]), float(state["vmax"])
    return None


# ------------------------------------------------------------------ app
def collect(app) -> Dict[str, Any]:
    """The whole analysis view of *app*: ``{"view": …, "features": {key: …}}``."""
    features: Dict[str, Any] = {}
    for feature in app.features:
        try:
            part = feature.session_state()
        except Exception:  # noqa: BLE001 - one feature must not stop a save
            logger.exception("%s.session_state", feature.name)
            continue
        if part:
            features[getattr(feature, "session_key", feature.name)] = part
    return {"view": model_state(app.model), "features": features}


def apply(app, state: Dict[str, Any], ctx: SessionContext) -> SessionContext:
    """Restore *state* (:func:`collect`) into *app*; returns *ctx* with its notes.

    The features go first -- constants, equations and clusters make columns the
    axes and gates may name -- then the model's view.
    """
    parts = dict(state.get("features") or {})
    for feature in app.features:
        part = parts.get(getattr(feature, "session_key", feature.name))
        if not part:
            continue
        try:
            feature.restore_session_state(part, ctx)
        except Exception as exc:  # noqa: BLE001 - noted, the rest still applies
            logger.exception("%s.restore_session_state", feature.name)
            ctx.skip(f"{feature.name} ({exc})")
    ctx.names = list(app.model.parameter_names)
    restore_model(app.model, dict(state.get("view") or {}), ctx)
    return ctx
