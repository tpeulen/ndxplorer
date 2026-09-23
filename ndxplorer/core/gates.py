"""The gate list as plain data, and the selections it stands for.

The Selection table is a list of rows. Each row has a name, a column, two
bounds, an *invert* flag and an *enable* flag. A gate that is not an interval
also carries what it is: the Gaussian's parameters in ``meta``, or the painted
mask or drawn region object itself in ``selection``.

:class:`GateList` is that list, and the one source of truth for both GUIs. The
emtk app's gate table is a view spec over :meth:`GateList.records`. The Qt
window's ``QTableWidget`` is rebuilt from the list, and it writes its edits
back through :meth:`GateList.edit`. Which points are shown is then
:meth:`GateList.selections`, and no widget is read to answer it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, Iterator, List, Optional, Sequence

from ..logging_config import logging
from .data_source import (
    DataSelection,
    Gaussian2DSelection,
    MaskDataSelection,
    RectangularDataSelection,
)

__all__ = ["GateRow", "GateList", "interval_rows", "selections_from_rows", "KINDS"]

#: The four kinds of gate the table holds.
KINDS = ("Interval", "G2D", "Region", "Mask")


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
        ``{"type": "G2D", "idx1", "idx2", "mu", "cov", "sigma", "log_x",
        "log_y"}`` for a 2-D Gaussian; ``None`` otherwise.
    selection : DataSelection or None
        The painted mask (:class:`MaskDataSelection`) or drawn region
        (``RegionDataSelection``) a row of that kind *is*. No cell can hold a
        bitmap or a polygon, so the row keeps the object.
    """

    parameter_idx: int
    name: str = ""
    lower: float = 0.0
    upper: float = 0.0
    invert: bool = False
    enabled: bool = True
    meta: Optional[Dict[str, Any]] = None
    selection: Optional[DataSelection] = None

    @property
    def kind(self) -> str:
        """``"Interval"``, ``"G2D"``, ``"Region"`` or ``"Mask"``."""
        if isinstance(self.selection, MaskDataSelection):
            return "Mask"
        if self.selection is not None and hasattr(self.selection, "roi"):
            return "Region"
        if isinstance(self.meta, dict) and self.meta.get("type"):
            return str(self.meta["type"])
        return "Interval"

    @property
    def is_interval(self) -> bool:
        return self.kind == "Interval"

    def bound_texts(self) -> tuple:
        """What the Min and Max cells show for a gate without bounds."""
        kind = self.kind
        if kind == "Mask":
            return ("Bitmap", "Bitmap")
        if kind == "Region":
            return (str(getattr(self.selection, "shape", "region")), "shape")
        if kind == "G2D":
            sigma = float((self.meta or {}).get("sigma", 1.0))
            return ("G2D", f"{sigma:g} σ")
        return (self.lower, self.upper)

    def record(self) -> dict:
        """The row as a table record: the fields a gate table shows."""
        lower, upper = self.bound_texts()
        return {
            "name": self.name,
            "lower": lower,
            "upper": upper,
            "invert": self.invert,
            "enabled": self.enabled,
            "kind": self.kind,
        }


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


def gaussian_meta(idx1: int, idx2: int, mu, cov, sigma: float = 1.0, log_x: bool = False,
                  log_y: bool = False) -> dict:
    """The metadata record of a 2-D Gaussian gate."""
    return {
        "type": "G2D",
        "idx1": int(idx1),
        "idx2": int(idx2),
        "mu": [float(mu[0]), float(mu[1])],
        "cov": [[float(cov[0][0]), float(cov[0][1])], [float(cov[1][0]), float(cov[1][1])]],
        "sigma": float(sigma),
        "log_x": bool(log_x),
        "log_y": bool(log_y),
    }


def selections_from_rows(rows: Iterable[GateRow]) -> List[DataSelection]:
    """The selections a list of gate rows stands for, one per row.

    A mask or region row returns its own object with the row's flags and name
    applied. A Gaussian row is rebuilt from its metadata.
    """
    selections: List[DataSelection] = []
    for row in rows:
        kind = row.kind
        if kind in ("Mask", "Region"):
            sel = row.selection
            sel.enabled, sel.invert, sel.name = row.enabled, row.invert, row.name
            selections.append(sel)
            continue
        if kind == "G2D":
            meta = row.meta
            try:
                selections.append(Gaussian2DSelection(
                    parameter_idx1=int(meta.get("idx1", row.parameter_idx)),
                    parameter_idx2=int(meta.get("idx2", row.parameter_idx)),
                    mu=meta.get("mu", [0.0, 0.0]),
                    cov=meta.get("cov", [[1.0, 0.0], [0.0, 1.0]]),
                    sigma=float(meta.get("sigma", 1.0)),
                    invert=row.invert,
                    enabled=row.enabled,
                    name=row.name,
                    log_x=bool(meta.get("log_x", False)),
                    log_y=bool(meta.get("log_y", False)),
                ))
            except Exception as exc:  # noqa: BLE001 - a bad record drops only its row
                logging.error("Error recreating G2D selection '%s': %s", row.name, exc)
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


class GateList:
    """The Selection table's rows: what both GUIs show and gate by.

    It behaves as a sequence of :class:`GateRow` (``len``, indexing, iteration,
    ``del``). Every change goes through a method, which bumps
    :attr:`revision`. A view redraws when the revision moves, and a plot
    recomputes when it does.

    Parameters
    ----------
    rows : iterable of GateRow, optional
    """

    def __init__(self, rows: Iterable[GateRow] = ()) -> None:
        self.rows: List[GateRow] = list(rows)
        self.revision = 0

    # ------------------------------------------------------------ sequence
    def __len__(self) -> int:
        return len(self.rows)

    def __iter__(self) -> Iterator[GateRow]:
        return iter(self.rows)

    def __getitem__(self, index):
        return self.rows[index]

    def __delitem__(self, index: int) -> None:
        self.remove([index])

    def __bool__(self) -> bool:
        return bool(self.rows)

    def _changed(self) -> None:
        self.revision += 1

    # ---------------------------------------------------------------- adding
    def append(self, row: GateRow) -> GateRow:
        self.rows.append(row)
        self._changed()
        return row

    def extend(self, rows: Iterable[GateRow]) -> None:
        self.rows.extend(rows)
        self._changed()

    def add_interval(self, idx: int, name: str, lower: float, upper: float,
                     invert: bool = False, enabled: bool = True) -> GateRow:
        """An interval gate on one column, its bounds ordered."""
        lo, hi = sorted((float(lower), float(upper)))
        return self.append(GateRow(int(idx), str(name), lo, hi, bool(invert), bool(enabled)))

    def add_rectangle(self, x_idx: int, x_name: str, x_range, y_idx: int, y_name: str,
                      y_range) -> List[GateRow]:
        """A rectangle on the 2-D map: an interval on x and one on y."""
        rows = interval_rows(x_idx, x_name, x_range, y_idx, y_name, y_range)
        self.extend(rows)
        return rows

    def add_gaussian(self, idx1: int, idx2: int, mu, cov, sigma: float = 1.0,
                     invert: bool = False, enabled: bool = True, name: str = "",
                     log_x: bool = False, log_y: bool = False) -> GateRow:
        """A 2-D Gaussian (elliptical) gate."""
        meta = gaussian_meta(idx1, idx2, mu, cov, sigma, log_x, log_y)
        return self.append(GateRow(int(idx1), str(name) or "G2D", invert=bool(invert),
                                   enabled=bool(enabled), meta=meta))

    def add_selection(self, selection: DataSelection) -> GateRow:
        """A row for a selection object of any kind.

        A mask or region is kept as the row's :attr:`GateRow.selection`. An
        interval or Gaussian object becomes the plain row it stands for.
        """
        invert = bool(getattr(selection, "invert", False))
        enabled = bool(getattr(selection, "enabled", True))
        name = str(getattr(selection, "name", "") or "")
        if isinstance(selection, MaskDataSelection) or hasattr(selection, "roi"):
            return self.append(GateRow(int(selection.idx1), name or "Mask", invert=invert,
                                       enabled=enabled, selection=selection))
        if isinstance(selection, Gaussian2DSelection):
            return self.add_gaussian(selection.parameter_idx1, selection.parameter_idx2,
                                     selection.mu, selection.cov, selection.sigma, invert,
                                     enabled, name, getattr(selection, "log_x", False),
                                     getattr(selection, "log_y", False))
        return self.add_interval(selection.parameter_idx, name, selection.lower,
                                 selection.upper, invert, enabled)

    # -------------------------------------------------------------- changing
    def remove(self, indices: Iterable[int]) -> int:
        """Remove the rows at *indices*; returns how many went."""
        drop = {int(i) for i in indices if 0 <= int(i) < len(self.rows)}
        if not drop:
            return 0
        self.rows = [row for i, row in enumerate(self.rows) if i not in drop]
        self._changed()
        return len(drop)

    def clear(self) -> None:
        if self.rows:
            self.rows = []
        self._changed()

    def edit(self, index: int, key: str, value: Any) -> bool:
        """A cell of the table changed; returns whether the gate did.

        ``invert``/``enabled`` take a bool and ``name`` a string. ``lower``/``upper``
        take a number, and only on an interval. As in the Qt table, a bound
        typed past its partner moves the partner along. Anything else is
        refused, and the row is left as it was.
        """
        if not 0 <= index < len(self.rows):
            return False
        row = self.rows[index]
        if key in ("invert", "enabled"):
            value = bool(value)
            if getattr(row, key) == value:
                return False
            setattr(row, key, value)
        elif key == "name":
            if row.name == str(value):
                return False
            row.name = str(value)
        elif key in ("lower", "upper"):
            if not row.is_interval:
                return False
            try:
                value = float(value)
            except (TypeError, ValueError):
                return False
            if value != value:  # NaN
                return False
            if getattr(row, key) == value:
                return False
            setattr(row, key, value)
            if key == "lower" and value > row.upper:
                row.upper = value
            elif key == "upper" and value < row.lower:
                row.lower = value
        else:
            return False
        self._changed()
        return True

    # ---------------------------------------------------------------- reading
    def selections(self) -> List[DataSelection]:
        """The selections the rows stand for, top to bottom."""
        return selections_from_rows(self.rows)

    def records(self) -> List[dict]:
        """The table's rows as records, each keyed by its position (``row``)."""
        return [dict(r.record(), row=i) for i, r in enumerate(self.rows)]

    def count(self, kind: str) -> int:
        """How many rows of *kind* there are (for numbering new ones)."""
        return sum(1 for r in self.rows if r.kind == kind)

