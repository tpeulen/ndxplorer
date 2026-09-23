"""The gate list as plain data, and the selections it stands for.

The Selection table is a list of rows -- a name, a column, two bounds, an
*invert* and an *enable* flag, and for the gates that are not intervals a
small metadata record saying what they are. Which :class:`DataSelection` a row
means used to be decided inside the Qt table's ``get_selections``, reading cell
widgets, item roles and JSON stashed in ``Qt.UserRole``. That made the answer
to "which points are shown" depend on a ``QTableWidget``.

Here it is decided from a :class:`GateRow`: the Qt table reads its cells into
rows and hands them over, and the emtk app keeps its gates as rows to begin
with. Both then get their selections from :func:`selections_from_rows`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Sequence

from ..logging_config import logging
from .data_source import (
    DataSelection,
    Gaussian2DSelection,
    MaskDataSelection,
    RectangularDataSelection,
)

__all__ = ["GateRow", "interval_rows", "selections_from_rows"]

#: Cell texts that stand for "no number" in the bound columns of a gate that is
#: not an interval (a painted mask, a 2-D Gaussian).
_PLACEHOLDERS = ("Bitmap", "Mask", "G2D", "---")


@dataclass
class GateRow:
    """One row of the Selection table.

    Attributes
    ----------
    parameter_idx : int
        Column the gate is on (the first of two for a 2-D gate).
    name : str
        What the table shows; the column name for an interval.
    lower, upper : float
        Bounds of an interval gate; unused by the other kinds.
    invert : bool
        Keep the points *outside* the gate instead.
    enabled : bool
        Whether the gate takes part at all.
    meta : dict or None
        ``{"type": "G2D" | "Region" | "Mask", ...}`` for a gate that is not an
        interval; ``None`` for an interval.
    """

    parameter_idx: int
    name: str = ""
    lower: float = 0.0
    upper: float = 0.0
    invert: bool = False
    enabled: bool = True
    meta: Optional[Dict[str, Any]] = None

    @property
    def kind(self) -> str:
        """``"Interval"``, or the ``type`` of the metadata."""
        if isinstance(self.meta, dict) and self.meta.get("type"):
            return str(self.meta["type"])
        return "Interval"

    def record(self) -> dict:
        """The row as a table record: the fields a gate table shows."""
        return {
            "name": self.name,
            "lower": self.lower,
            "upper": self.upper,
            "invert": self.invert,
            "enabled": self.enabled,
        }


def parse_bound(text) -> float:
    """A bound cell's value; ``0.0`` for a placeholder or anything unreadable."""
    if text is None:
        return 0.0
    if isinstance(text, (int, float)):
        return float(text)
    text = str(text).strip()
    if text in _PLACEHOLDERS:
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def interval_rows(x_idx: int, x_name: str, x_range, y_idx: int, y_name: str,
                  y_range) -> List[GateRow]:
    """The two interval rows a rectangle dragged on the 2-D map stands for.

    Each range is ordered low to high, whichever way the rectangle was drawn.
    """
    rows = []
    for idx, name, bounds in ((x_idx, x_name, x_range), (y_idx, y_name, y_range)):
        lo, hi = sorted(float(v) for v in bounds)
        rows.append(GateRow(int(idx), str(name), lo, hi))
    return rows


def _kind_from_text(row: GateRow, bound_texts: Sequence[str]) -> Optional[str]:
    """The kind of a row whose metadata was lost, from what its cells say."""
    if any("Bitmap" in str(t) for t in bound_texts) or "Mask" in row.name:
        return "Mask"
    if "G2D" in row.name:
        return "G2D"
    return None


def selections_from_rows(
    rows: Iterable[GateRow],
    stored: Sequence[DataSelection] = (),
    bound_texts: Optional[Sequence[Sequence[str]]] = None,
) -> List[DataSelection]:
    """The selections a list of gate rows stands for.

    Parameters
    ----------
    rows : iterable of GateRow
        The table, top to bottom.
    stored : sequence of DataSelection
        Selections that cannot be rebuilt from a row -- painted masks and drawn
        regions carry their shape, which no cell holds. A row of that kind is
        matched to one of these (by ``selection_id``, then by columns and
        name) and the stored object is returned with the row's flags applied.
    bound_texts : sequence of (str, str), optional
        The bound cells' text per row, used only to recognise a mask or a
        Gaussian row whose metadata is missing.

    Returns
    -------
    list of DataSelection
        One per row that could be resolved. A mask, region or Gaussian row that
        cannot be resolved is left out -- never reinterpreted as an interval,
        which would gate on bounds nobody set.
    """
    selections: List[DataSelection] = []
    for position, row in enumerate(rows):
        meta = row.meta if isinstance(row.meta, dict) else None
        kind = meta.get("type") if meta else None
        if kind is None and bound_texts is not None and position < len(bound_texts):
            kind = _kind_from_text(row, bound_texts[position])

        if kind == "G2D":
            try:
                selections.append(Gaussian2DSelection(
                    parameter_idx1=int(meta.get("idx1", row.parameter_idx)) if meta else row.parameter_idx,
                    parameter_idx2=int(meta.get("idx2", row.parameter_idx)) if meta else row.parameter_idx,
                    mu=meta.get("mu", [0.0, 0.0]) if meta else [0.0, 0.0],
                    cov=meta.get("cov", [[1.0, 0.0], [0.0, 1.0]]) if meta else [[1.0, 0.0], [0.0, 1.0]],
                    sigma=float(meta.get("sigma", 1.0)) if meta else 1.0,
                    invert=row.invert,
                    enabled=row.enabled,
                    name=row.name,
                    log_x=bool(meta.get("log_x", False)) if meta else False,
                    log_y=bool(meta.get("log_y", False)) if meta else False,
                ))
            except Exception as exc:
                logging.error("Error recreating G2D selection '%s': %s", row.name, exc)
            continue

        if kind == "Region":
            sel_id = meta.get("selection_id") if meta else None
            recovered = next((s for s in stored
                              if getattr(s, "selection_id", None) == sel_id and hasattr(s, "roi")),
                             None)
            if recovered is None:
                logging.warning("Region selection '%s' has no stored region", row.name)
                continue
            recovered.enabled, recovered.invert, recovered.name = row.enabled, row.invert, row.name
            selections.append(recovered)
            continue

        if kind == "Mask":
            recovered = _stored_mask(row, meta, stored)
            if recovered is None:
                logging.warning("MaskDataSelection object NOT FOUND for '%s'", row.name)
                continue
            recovered.enabled, recovered.invert, recovered.name = row.enabled, row.invert, row.name
            selections.append(recovered)
            continue

        selections.append(RectangularDataSelection(
            parameter_idx=row.parameter_idx,
            lower=row.lower,
            upper=row.upper,
            invert=row.invert,
            enabled=row.enabled,
            name=row.name,
        ))
    return selections


def _stored_mask(row: GateRow, meta: Optional[dict],
                 stored: Sequence[DataSelection]) -> Optional[MaskDataSelection]:
    """The stored mask a row refers to: by id, else by columns and name."""
    masks = [s for s in stored if isinstance(s, MaskDataSelection)]
    sel_id = meta.get("selection_id") if meta else None
    if sel_id:
        for mask in masks:
            if getattr(mask, "selection_id", None) == sel_id:
                return mask
    idx1 = int(meta.get("idx1", -1)) if meta else -1
    idx2 = int(meta.get("idx2", -1)) if meta else -1
    name = row.name
    for mask in masks:
        idx_match = (mask.idx1 == idx1 and mask.idx2 == idx2) or meta is None
        name_match = mask.name == name or name.startswith(mask.name) or mask.name.startswith(name)
        if idx_match and (name_match or len(masks) == 1):
            return mask
    return None
