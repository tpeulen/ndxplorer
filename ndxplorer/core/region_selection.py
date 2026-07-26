"""Gates backed by ChiSurf regions, and selection files that keep every shape.

ndXplorer grew three selection kinds — a 1-D interval, a Mahalanobis ellipse and
a painted histogram bitmap — each with its own class, its own mask arithmetic and
its own idea of how to be stored. ChiSurf's ``chisurf.core.roi`` already has that
vocabulary and more (rectangle, ellipse, **polygon**, mask, threshold, boolean
composites), plus one ordered, named collection type carrying exactly the
``enabled``/``invert`` flags a selection row shows.

:class:`RegionDataSelection` makes a region usable as an ndXplorer gate, so the
two stop being parallel implementations of one idea. Two things it buys
immediately:

* **Polygon gates**, which ndXplorer had no way to express at all — a population
  in a scatter is rarely an ellipse.
* **Selection files that survive a reload.** The old ``onSave_selection`` dumped
  ``selection.__dict__`` straight to JSON, which raises ``TypeError: Object of
  type ndarray is not JSON serializable`` the moment a Gaussian or painted
  selection is present — *after* truncating the target file. ``onLoad_selection``
  then read ``parameter_idx``/``lower``/``upper`` off every entry, so it could
  only ever rebuild rectangles. Saving through
  :class:`~chisurf.core.roi.RegionCollection` keeps every shape and flag,
  because the region types serialise themselves.

The mask convention is the one thing to keep straight: ``get_mask`` returns
``True`` where a point is *excluded*, while a region answers where a point is
*inside*.
"""

from __future__ import annotations

from typing import Iterable, Optional, Sequence, Tuple

import numpy as np

from .data_source import DataSelection


class RegionDataSelection(DataSelection):
    """A ChiSurf region used as a gate on two parameters.

    Parameters
    ----------
    roi : chisurf.core.roi.ROI
        Any region — rectangle, ellipse, polygon, painted mask, or a boolean
        composite of them.
    idx1, idx2 : int
        The parameter indices forming the plane the region was drawn on.
    invert : bool
        Exclude the points *inside* the region instead of those outside.
    enabled : bool
        Whether the gate takes part at all.
    name : str, optional
        Row label; defaults to the region's own name.
    """

    def __init__(
        self,
        roi,
        idx1: int,
        idx2: int,
        invert: bool = False,
        enabled: bool = True,
        name: Optional[str] = None,
    ):
        import uuid

        self.roi = roi
        self.idx1 = int(idx1)
        self.idx2 = int(idx2)
        self.invert = bool(invert)
        self.enabled = bool(enabled)
        self.name = name or getattr(roi, "name", "") or "region"
        self.selection_id = str(uuid.uuid4())

    @property
    def shape(self) -> str:
        """The kind of region, for the selection table."""
        return type(self.roi).__name__.replace("ROI", "").lower()

    def get_mask(self, data: np.ndarray) -> np.ndarray:
        """Return ``True`` where a point is excluded, ``(n_parameters, n_points)``.

        Non-finite coordinates are excluded rather than admitted: a point whose
        position on this plane is unknown cannot be shown to be inside the gate,
        and admitting it would quietly widen every selection.
        """
        values = np.asarray(data, dtype=float)
        n_parameters, n_points = values.shape
        out = np.zeros((n_parameters, n_points), dtype=bool)
        if not self.enabled:
            return out
        if self.idx1 >= n_parameters or self.idx2 >= n_parameters:
            return out

        x = values[self.idx1, :]
        y = values[self.idx2, :]
        finite = np.isfinite(x) & np.isfinite(y)
        inside = np.zeros(n_points, dtype=bool)
        if finite.any():
            points = np.column_stack([x[finite], y[finite]])
            inside[finite] = np.asarray(self.roi.contains(points), dtype=bool)
        if self.invert:
            inside = ~inside & finite
        out[:] = ~inside
        return out

    def __str__(self) -> str:  # pragma: no cover - display only
        return f"RegionDataSelection({self.shape}: {self.name})"


def to_collection(
    selections: Iterable[DataSelection], axes: Tuple[int, int] = (0, 1), name: str = "selection"
):
    """Return the selections as a :class:`chisurf.core.roi.RegionCollection`.

    Selections already backed by a region are taken as they are; the older kinds
    are converted by ChiSurf's bridge. One that constrains a parameter outside
    *axes* is skipped, since it has no shape on this plane.
    """
    from chisurf.core.roi import RegionCollection, RegionEntry, roi_from_selection

    collection = RegionCollection(combine="and", name=name)
    for selection in selections or []:
        roi = getattr(selection, "roi", None)
        if roi is None:
            roi = roi_from_selection(selection, axes=axes)
        if roi is None:
            continue
        collection.add(
            RegionEntry(
                roi=roi,
                enabled=bool(getattr(selection, "enabled", True)),
                invert=bool(getattr(selection, "invert", False)),
            )
        )
    return collection


def from_collection(collection, axes: Tuple[int, int] = (0, 1)) -> list:
    """Return a region collection as ndXplorer selections, flags kept."""
    return [
        RegionDataSelection(
            entry.roi, axes[0], axes[1],
            invert=entry.invert, enabled=entry.enabled, name=entry.name,
        )
        for entry in collection
    ]


def save_selections(
    selections: Iterable[DataSelection], path: str, axes: Tuple[int, int] = (0, 1)
) -> str:
    """Write selections to a file that can hold every shape.

    Parameters
    ----------
    selections : iterable of DataSelection
    path : str
        Destination.
    axes : tuple of int
        The plane the selections were drawn on.

    Returns
    -------
    str
        The path written.
    """
    return to_collection(selections, axes=axes).save(path)


def load_selections(path: str, axes: Tuple[int, int] = (0, 1)) -> list:
    """Read a selection file, whatever shapes it holds.

    Also reads the legacy ``[{parameter_idx, lower, upper, …}, …]`` list the old
    saver produced, so files written before this change still open.
    """
    import json

    from chisurf.core.roi import RegionCollection

    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)

    if isinstance(data, list):
        from .data_source import RectangularDataSelection

        return [
            RectangularDataSelection(
                int(entry["parameter_idx"]), float(entry["lower"]), float(entry["upper"]),
                bool(entry.get("invert", False)), bool(entry.get("enabled", True)),
                entry.get("name"),
            )
            for entry in data
            if "parameter_idx" in entry
        ]

    return from_collection(RegionCollection.from_dict(data), axes=axes)


__all__ = [
    "RegionDataSelection",
    "to_collection",
    "from_collection",
    "save_selections",
    "load_selections",
]
