"""Colormaps as lookup tables, without Qt.

The colormaps ndXplorer offers are pyqtgraph's: CSV files of RGB stops
(viridis, the CET maps, ...) and ``.hex`` palettes shipped in
``pyqtgraph/colors/maps``. Asking ``pyqtgraph.colormap`` for them imports
pyqtgraph and therefore Qt. The files themselves are plain text, so they are
read here directly -- located through the package spec, which does not import
it -- and interpolated exactly as ``pyqtgraph.ColorMap`` does: stops evenly
spaced over ``[0, 1]``, linear in between.

Where pyqtgraph is not installed at all (a browser), the maps matplotlib also
ships -- viridis, plasma, inferno, magma, cividis, turbo -- come from there.
"""

from __future__ import annotations

import functools
import importlib.util
import pathlib
from typing import List, Optional

import numpy as np

__all__ = ["available_colormaps", "colormap_stops", "lookup_table", "apply_colormap"]

#: Maps matplotlib provides under the same name, for a process without pyqtgraph.
_MATPLOTLIB_MAPS = ("cividis", "inferno", "magma", "plasma", "turbo", "viridis")


@functools.lru_cache(maxsize=1)
def _maps_dir() -> Optional[pathlib.Path]:
    """pyqtgraph's colormap data folder, found without importing pyqtgraph."""
    try:
        spec = importlib.util.find_spec("pyqtgraph")
    except (ImportError, ValueError):
        return None
    if spec is None or not spec.submodule_search_locations:
        return None
    for location in spec.submodule_search_locations:
        folder = pathlib.Path(location) / "colors" / "maps"
        if folder.is_dir():
            return folder
    return None


@functools.lru_cache(maxsize=1)
def available_colormaps() -> List[str]:
    """The colormap names, sorted."""
    folder = _maps_dir()
    if folder is not None:
        names = {p.stem for p in folder.iterdir() if p.suffix.lower() in (".csv", ".hex")}
        if names:
            return sorted(names)
    try:
        import matplotlib

        return sorted(n for n in _MATPLOTLIB_MAPS if n in matplotlib.colormaps)
    except ImportError:
        return ["viridis"]


def _parse(path: pathlib.Path) -> np.ndarray:
    """RGB stops of one pyqtgraph map file, 0..1, as ``pyqtgraph.colormap`` reads it."""
    csv = path.suffix.lower() != ".hex"
    stops = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith(";"):
            continue
        colour = line.split(";", 1)[0].strip()
        if not colour:
            continue
        if csv:
            parts = colour.split(",")
            if len(parts) < 3:
                continue
            stops.append([int(255 * float(c) + 0.5) for c in parts[:3]])
        else:
            text = colour.lstrip("#")
            if len(text) == 3:
                text = "".join(2 * c for c in text)
            if len(text) < 6:
                continue
            stops.append([int(text[i:i + 2], 16) for i in (0, 2, 4)])
    return np.asarray(stops, dtype=np.float64) / 255.0


@functools.lru_cache(maxsize=64)
def colormap_stops(name: str) -> np.ndarray:
    """``(n, 3)`` RGB stops of the colormap *name*, 0..1.

    Raises
    ------
    KeyError
        When no such colormap exists.
    """
    folder = _maps_dir()
    if folder is not None:
        for suffix in (".csv", ".hex"):
            path = folder / f"{name}{suffix}"
            if path.exists():
                return _parse(path)
    try:
        import matplotlib

        if name in matplotlib.colormaps:
            return np.asarray(matplotlib.colormaps[name](np.linspace(0.0, 1.0, 256)))[:, :3]
    except ImportError:
        pass
    raise KeyError(f"no colormap named {name!r}")


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
