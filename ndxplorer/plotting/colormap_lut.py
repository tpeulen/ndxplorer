"""Colormaps as lookup tables, without Qt.

The colour tables are emtk's (:mod:`emtk.colormaps`, the one home for them in
the stack): pyqtgraph's maps -- viridis and friends, the CET maps, the
``PAL-*`` palettes -- and the classic ones (gray, hot, RdBu, ...). Licences
and sources travel with emtk (``licenses/colormaps.txt``). This module keeps
ndXplorer's lookup: stops evenly spaced over ``[0, 1]`` and linear in between,
exactly as ``pyqtgraph.ColorMap`` maps them, so a plot looks the same with or
without pyqtgraph installed. Neither pyqtgraph, matplotlib nor Qt is needed.
"""

from __future__ import annotations

import functools
from typing import List, Optional

import numpy as np
from emtk import colormaps as _tables

__all__ = ["available_colormaps", "colormap_stops", "lookup_table", "apply_colormap"]


@functools.lru_cache(maxsize=1)
def available_colormaps() -> List[str]:
    """The colormap names, sorted."""
    return sorted(_tables.names())


@functools.lru_cache(maxsize=64)
def colormap_stops(name: str) -> np.ndarray:
    """``(n, 3)`` RGB stops of the colormap *name*, 0..1.

    Raises
    ------
    KeyError
        When no such colormap exists.
    """
    return np.asarray(_tables.stops(name), dtype=np.float64)


def lookup_table(name: str, n_colors: int = 256, gamma: float = 1.0) -> np.ndarray:
    """``(n_colors, 4)`` uint8 RGBA table for *name*; grey when it does not exist."""
    try:
        stops = colormap_stops(name)
    except KeyError:
        ramp = np.linspace(0, 255, n_colors).astype(np.uint8)
        return np.stack([ramp, ramp, ramp, np.full_like(ramp, 255)], axis=1)
    positions = np.linspace(0.0, 1.0, len(stops))
    t = np.linspace(0.0, 1.0, int(n_colors))
    rgb = np.stack([np.interp(t, positions, stops[:, c]) for c in range(3)], axis=1)
    if gamma != 1.0:
        rgb = np.power(rgb, gamma)
    rgba = np.concatenate([rgb, np.ones((len(t), 1))], axis=1)
    return (np.clip(rgba, 0.0, 1.0) * 255).astype(np.uint8)


def apply_colormap(data: np.ndarray, name: str = "viridis", vmin: Optional[float] = None,
                   vmax: Optional[float] = None, gamma: float = 1.0,
                   n_colors: int = 256) -> np.ndarray:
    """Colour a 2-D array: ``(h, w, 4)`` uint8 RGBA.

    Values are clipped to ``[vmin, vmax]`` (the data's range when omitted); a
    NaN is drawn as the lowest colour.
    """
    data = np.asarray(data, dtype=np.float64)
    if data.ndim != 2:
        raise ValueError("Data must be 2-dimensional")
    finite = data[np.isfinite(data)]
    if vmin is None:
        vmin = float(finite.min()) if finite.size else 0.0
    if vmax is None:
        vmax = float(finite.max()) if finite.size else 1.0
    if vmin == vmax:
        vmin, vmax = vmin - 0.5, vmax + 0.5
    norm = np.clip((np.nan_to_num(data, nan=vmin) - vmin) / (vmax - vmin), 0.0, 1.0)
    if gamma != 1.0:
        norm = np.power(norm, gamma)
    lut = lookup_table(name, n_colors)
    return lut[np.minimum((norm * (n_colors - 1) + 0.5).astype(np.intp), n_colors - 1)]
