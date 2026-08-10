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

def pick_population(
    data: np.ndarray,
    axes: Tuple[int, int],
    x: float,
    y: float,
    *,
    radius: float,
    sigma: float = 2.0,
    name: str = "",
) -> Tuple[Optional["RegionDataSelection"], str]:
    """Return the gate around the population clicked at ``(x, y)``.

    The third way a gate gets made, beside dragging a shape and fitting a
    mixture over the whole plane: click the population you mean, and the fit
    decides where it is and how wide it is. It is the same gesture the imaging
    side offers on a frame, and deliberately the same code —
    :func:`chisurf.core.roi.fit_gaussian_cluster` re-centres on the points and
    :func:`chisurf.core.roi.ellipse_from_covariance` turns the covariance into
    the ellipse — so a gate picked here and a region picked there are the same
    object with the same conventions.

    **The click is a seed, not the answer.** A click on the shoulder of a
    population returns a centre on the shoulder unless the estimate re-centres,
    and a covariance inflated by the empty half of the disc it sampled.

    **Everything is in the parameters' own units**, including the click. A
    region gates raw values (:meth:`RegionDataSelection.get_mask` asks the ROI
    whether a point is inside), so a plane drawn on a logarithmic axis has to
    convert the click back before calling — fitting in log space and gating in
    linear space produces an ellipse that is wrong everywhere except its centre,
    and says nothing about it.

    Parameters
    ----------
    data : numpy.ndarray
        ``(n_parameters, n_points)``, as the rest of ndXplorer holds it.
    axes : tuple of int
        The two parameter indices the plane shows.
    x, y : float
        Where the user clicked, in the parameters' units.
    radius : float
        Capture radius in those units. A *setting*, not something fitted: a
        density has no edge, and the same cloud is one population or three
        depending on how far one is willing to look.
    sigma : float, optional
        Mahalanobis radius of the resulting gate.
    name : str, optional
        Gate name.

    Returns
    -------
    selection : RegionDataSelection or None
        ``None`` when the pick was refused.
    reason : str
        Why it was refused; empty on success.
    """
    from chisurf.core.roi import cluster_roi, fit_gaussian_cluster

    idx1, idx2 = int(axes[0]), int(axes[1])
    values = np.asarray(data, dtype=float)
    if idx1 >= values.shape[0] or idx2 >= values.shape[0]:
        return None, f"no parameters {idx1} and {idx2} on this plane"

    plane = np.stack([values[idx1, :], values[idx2, :]], axis=1)
    cluster = fit_gaussian_cluster(plane, x, y, radius=radius)
    if not cluster.success:
        return None, cluster.reason

    roi = cluster_roi(cluster, name or "picked", sigma=sigma)
    return RegionDataSelection(roi, idx1, idx2, name=name or "picked"), ""
