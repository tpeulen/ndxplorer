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

    def gate_key(self) -> tuple:
        """See :func:`ndxplorer.core.data.mask_state.gate_key`."""
        try:
            shape = self.roi.to_dict()
        except Exception:
            shape = id(self.roi)
        return ("region", self.idx1, self.idx2, self.invert, self.enabled, shape)

    def __eq__(self, other) -> bool:
        """Equal when the same shape gates the same plane the same way.

        Not identity, which is what the default would give. The selection table
        edits a gate *in place* -- toggling ``enabled`` or ``invert`` on the very
        object the cache already holds -- so an identity comparison says nothing
        changed and the plot keeps showing the previous population. Comparing
        the serialised geometry costs a dict per gate per redraw and is the
        difference between the checkbox working and not.
        """
        if not isinstance(other, RegionDataSelection):
            return False
        if (self.idx1, self.idx2, self.invert, self.enabled) != \
                (other.idx1, other.idx2, other.invert, other.enabled):
            return False
        try:
            return self.roi.to_dict() == other.roi.to_dict()
        except Exception:
            return self.roi is other.roi

    __hash__ = None  # mutable, and compared by value: not hashable

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
    selections = list(selections or [])
    try:
        import chisurf.core.roi  # noqa: F401 - the region file format
    except ImportError:
        # Without ChiSurf (a browser page) the interval gates still go out,
        # in the list format load_selections reads without it.
        from .data_source import RectangularDataSelection

        if not all(isinstance(s, RectangularDataSelection) for s in selections):
            raise RuntimeError(
                "Saving drawn regions, masks or Gaussian gates needs ChiSurf's region "
                "module (chisurf.core.roi), which is not installed here; interval "
                "gates alone can be saved.") from None
        import json

        with open(path, "w", encoding="utf-8") as handle:
            json.dump([{"parameter_idx": int(s.parameter_idx), "lower": float(s.lower),
                        "upper": float(s.upper), "invert": bool(s.invert),
                        "enabled": bool(s.enabled), "name": s.name} for s in selections],
                      handle, indent=2)
        return str(path)
    return to_collection(selections, axes=axes).save(path)


def load_selections(path: str, axes: Tuple[int, int] = (0, 1)) -> list:
    """Read a selection file, whatever shapes it holds.

    Also reads the legacy ``[{parameter_idx, lower, upper, …}, …]`` list the old
    saver produced, so files written before this change still open.
    """
    import json

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

    from chisurf.core.roi import RegionCollection

    return from_collection(RegionCollection.from_dict(data), axes=axes)


def selections_from_label_mask(
    mask: np.ndarray,
    edges1: Sequence[float],
    edges2: Sequence[float],
    idx1: int = 0,
    idx2: int = 1,
    names: Optional[dict] = None,
) -> list:
    """Split a painted **multi-class** mask into one gate per class.

    The mask brush paints integer class ids, not a yes/no bitmap, so one painted
    image can carry several populations at once. Until now that whole image was
    a single :class:`MaskDataSelection`: the classes had no names, could not be
    measured or inverted separately, and could not be combined — the multi-label
    information existed and nothing downstream could reach it.

    One region per class fixes that. Each becomes an ordinary gate, so a painted
    population is on the same footing as a drawn ellipse.

    Parameters
    ----------
    mask : numpy.ndarray
        Integer label image over the histogram bins, indexed ``[y_bin, x_bin]``
        as the brush stores it (transposed to match the displayed image). Zero
        is background.
    edges1, edges2 : sequence of float
        Bin edges of the two axes.
    idx1, idx2 : int
        The parameter indices the plane is drawn from.
    names : dict, optional
        Class id to label; unnamed classes become ``"class <id>"``.

    Returns
    -------
    list of RegionDataSelection
        One per non-zero class, in class order.
    """
    from chisurf.core.roi import MaskROI

    labels = np.asarray(mask)
    out = []
    for value in sorted(int(v) for v in np.unique(labels) if int(v) != 0):
        label = (names or {}).get(value, f"class {value}")
        roi = MaskROI.from_histogram(
            labels == value, np.asarray(edges1), np.asarray(edges2), name=label
        )
        out.append(RegionDataSelection(roi, idx1, idx2, name=label))
    return out


def label_mask_from_selections(
    selections: Iterable[DataSelection],
    shape: Tuple[int, int],
    edges1: Sequence[float],
    edges2: Sequence[float],
) -> np.ndarray:
    """Rasterise region gates back into a multi-class mask.

    The inverse of :func:`selections_from_label_mask`, so a set of regions can
    be handed back to the brush. Later selections overwrite earlier ones where
    they overlap, since a pixel carries one class.

    Parameters
    ----------
    selections : iterable of DataSelection
        Those backed by a region contribute; others are skipped.
    shape : tuple of int
        ``(n_y_bins, n_x_bins)`` of the mask to fill.
    edges1, edges2 : sequence of float
        Bin edges of the two axes.

    Returns
    -------
    numpy.ndarray
        Integer label image, ``0`` where nothing is selected.
    """
    labels = np.zeros(tuple(shape), dtype=np.int32)
    extent = (
        float(edges1[0]), float(edges1[-1]), float(edges2[0]), float(edges2[-1])
    )
    for value, selection in enumerate(selections or [], start=1):
        roi = getattr(selection, "roi", None)
        if roi is None:
            continue
        labels[roi.to_mask(labels.shape, extent=extent)] = value
    return labels


__all__ = [
    "RegionDataSelection",
    "to_collection",
    "from_collection",
    "save_selections",
    "load_selections",
    "selections_from_label_mask",
    "label_mask_from_selections",
]

