"""A mask painted onto the bins of the 2-D map, and the gate it becomes.

The Draw Mask panel lets the user paint categories onto the 2-D histogram with
a round brush, erase them, and Apply a category as a gate. :class:`MaskCanvas`
does all of that on plain arrays, so any GUI can use it. It has one integer
label per map bin, ``(n_y, n_x)``, with row 0 at the lowest y (the
histogram's own orientation, and the one
:class:`~ndxplorer.core.data_source.MaskDataSelection` reads as "transposed").

The brush is round **on screen**: its radius is in pixels, and the caller says
how many pixels a bin is along x and along y. So a brush of 5 covers the same
patch of the picture however the axes are binned. That is
:func:`ndxplorer.utils.mask_helpers.create_pixel_radius_brush_kernel`, the Qt
window's kernel.

A drag paints a *stroke*. Dabs are laid along the segment between successive
pointer positions, so a fast drag leaves no gaps.

The canvas belongs to one map: the parameter pair and the bin edges. When
either changes, :meth:`MaskCanvas.fit` starts it afresh, because a label means
nothing on bins it was not painted on.
"""

from __future__ import annotations

from typing import Optional, Sequence, Tuple

import numpy as np

from ..utils import mask_helpers
from .data_source import MaskDataSelection

__all__ = ["MaskCanvas"]


class MaskCanvas:
    """Category labels painted onto the map's bins.

    Attributes
    ----------
    mask : ndarray of int32 or None
        ``(n_y, n_x)`` labels, 0 = unpainted.
    x_edges, y_edges : ndarray or None
        The bins the labels belong to.
    key : tuple or None
        What the canvas was fitted to (the columns shown).
    revision : int
        Bumped by every change, so an overlay knows when to redraw.
    """

    def __init__(self) -> None:
        self.mask: Optional[np.ndarray] = None
        self.x_edges: Optional[np.ndarray] = None
        self.y_edges: Optional[np.ndarray] = None
        self.key: Optional[tuple] = None
        self.revision = 0

    # ------------------------------------------------------------ the map
    def fit(self, x_edges: Sequence[float], y_edges: Sequence[float], key: tuple = ()) -> bool:
        """Attach to a map; returns whether the canvas was started afresh."""
        x_edges = np.asarray(x_edges, dtype=np.float64)
        y_edges = np.asarray(y_edges, dtype=np.float64)
        same = (self.mask is not None and self.key == tuple(key)
                and self.x_edges is not None and np.array_equal(self.x_edges, x_edges)
                and self.y_edges is not None and np.array_equal(self.y_edges, y_edges))
        if same:
            return False
        self.x_edges, self.y_edges, self.key = x_edges, y_edges, tuple(key)
        self.mask = mask_helpers.create_empty_mask((len(y_edges) - 1, len(x_edges) - 1))
        self.revision += 1
        return True

    @property
    def shape(self) -> Tuple[int, int]:
        return tuple(self.mask.shape) if self.mask is not None else (0, 0)

    def bin_of(self, x: float, y: float) -> Optional[Tuple[int, int]]:
        """``(row, column)`` of the bin under a point in data units, or ``None``."""
        if self.mask is None:
            return None
        ix = int(np.searchsorted(self.x_edges, x, side="right")) - 1
        iy = int(np.searchsorted(self.y_edges, y, side="right")) - 1
        ny, nx = self.mask.shape
        if not (0 <= ix < nx and 0 <= iy < ny):
            return None
        return iy, ix

    # ----------------------------------------------------------- painting
    def dab(self, x: float, y: float, radius_px: float, px_per_bin: Tuple[float, float],
            category: int, erase: bool = False) -> bool:
        """One brush dab centred on the data point ``(x, y)``."""
        at = self.bin_of(x, y)
        if at is None:
            return False
        kernel = mask_helpers.create_pixel_radius_brush_kernel(
            int(max(1, round(radius_px))), float(px_per_bin[0]), float(px_per_bin[1]))
        mask_helpers.apply_brush_to_mask(self.mask, at, kernel, int(category),
                                         "erase" if erase else "add")
        self.revision += 1
        return True

    def stroke(self, start: Tuple[float, float], end: Tuple[float, float], radius_px: float,
               px_per_bin: Tuple[float, float], category: int, erase: bool = False) -> bool:
        """Dabs along the segment from *start* to *end* (data units), a bin apart."""
        if self.mask is None:
            return False
        (x0, y0), (x1, y1) = start, end
        # Steps in bins along the longer axis of the segment: no gaps, no waste.
        bx = abs(x1 - x0) / max(np.min(np.diff(self.x_edges)), 1e-300)
        by = abs(y1 - y0) / max(np.min(np.diff(self.y_edges)), 1e-300)
        steps = int(min(max(bx, by), 10000)) + 1
        painted = False
        for t in np.linspace(0.0, 1.0, steps + 1):
            painted |= self.dab(x0 + t * (x1 - x0), y0 + t * (y1 - y0), radius_px, px_per_bin,
                                category, erase)
        return painted

    def clear(self) -> None:
        if self.mask is not None:
            self.mask[:] = 0
            self.revision += 1

    # ------------------------------------------------------------ reading
    def categories(self) -> list:
        """The categories painted, in order."""
        if self.mask is None:
            return []
        return [int(c) for c in np.unique(self.mask) if c > 0]

    def selection(self, idx1: int, idx2: int, category: Optional[int] = None,
                  name: str = "") -> Tuple[Optional[MaskDataSelection], str]:
        """The gate for *category* (every painted bin when ``None``).

        Returns ``(selection, "")`` or ``(None, why)``.
        """
        if self.mask is None:
            return None, "Nothing is painted. Enable drawing and paint on the 2-D plot first."
        binary = self.mask > 0 if category is None else self.mask == int(category)
        if not binary.any():
            which = "any category" if category is None else f"category {int(category)}"
            return None, f"The mask has no bins of {which}."
        selection = MaskDataSelection(int(idx1), int(idx2), binary.copy(), self.x_edges.copy(),
                                      self.y_edges.copy(), name=name or "Bitmap")
        return selection, ""

    def rgba(self, colours: Sequence[Tuple[int, int, int, int]]) -> np.ndarray:
        """The labels coloured for an overlay: ``(n_y, n_x, 4)`` uint8, unpainted clear."""
        out = np.zeros(self.shape + (4,), dtype=np.uint8)
        if self.mask is None:
            return out
        for category in self.categories():
            out[self.mask == category] = colours[(category - 1) % len(colours)]
        return out

    # ------------------------------------------------------------- files
    def save(self, path: str) -> None:
        """Save the labels as an integer TIFF (row 0 at the top, as a picture)."""
        if self.mask is None:
            raise ValueError("no mask to save")
        mask_helpers.save_mask_as_bitmap(np.flipud(self.mask), path, binary=False)

    def load(self, path: str) -> str:
        """Load labels from an integer TIFF; returns why not, or ``""``.

        The file must have the map's own shape (a mask saved from this map, or
        from the Qt window at the same binning).
        """
        if self.mask is None:
            return "Show a 2-D map first: the mask is loaded onto its bins."
        labels, _classes = mask_helpers.load_mask_from_tiff(path)
        labels = np.flipud(np.asarray(labels))
        if labels.shape != self.mask.shape:
            return (f"The mask is {labels.shape[1]} x {labels.shape[0]} bins; the map is "
                    f"{self.mask.shape[1]} x {self.mask.shape[0]}.")
        self.mask[:] = labels.astype(self.mask.dtype)
        self.revision += 1
        return ""
