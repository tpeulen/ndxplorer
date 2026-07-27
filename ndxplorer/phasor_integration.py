"""Draw ChiSurf phasor / FRET *lines* on the ndXplorer 2-D plot (PRD-56).

Chisurf-free glue that turns the shared **LineSet** returned by ``phasor.overlays`` /
``fret_line.overlays`` (fetched through :mod:`ndxplorer.rpc`) into pyqtgraph items on
ndXplorer's ``overlay_plot``, and injects phasor-derived columns (τ_φ, τ_M) into the
``DataSource``. The 2-D histogram image lives in *bin-index* space, so overlay data
coordinates are mapped through ``ndx.value_to_bin`` against the current histogram edges
— exactly like the built-in curve overlays.

All functions take the ``NDXplorer`` instance (``ndx``) and use only its public surface
(``overlay_plot``, ``value_to_bin``, ``_histogram``, ``plot_control``, ``data_source``,
``phasor_service`` / ``lines_service``), so they are unit-testable with a light stand-in.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

import numpy as np

logger = logging.getLogger(__name__)

#: Column-name tokens that identify the phasor g / s axes (case-insensitive; also
#: matches the imaging HDF5 form ``"g (window)"`` / ``"s (window)"``).
_G_TOKENS = ("g", "phasor g", "g coordinate")
_S_TOKENS = ("s", "phasor s", "s coordinate")


# --------------------------------------------------------------------------------------
# Axis / column inspection
# --------------------------------------------------------------------------------------
def current_axes(ndx: Any) -> tuple[str, str]:
    """Return the ``(x_name, y_name)`` of the current 2-D plot axes (or ``("","")``)."""
    try:
        return str(ndx.plot_control.p1[1]), str(ndx.plot_control.p2[1])
    except Exception:
        return "", ""


def _axis_token(name: str) -> str:
    """Normalise a column name to its leading token (``"g (win)"`` → ``"g"``)."""
    return str(name).strip().lower().split(" ")[0].split("(")[0].strip()


def axes_look_like_phasor(ndx: Any) -> bool:
    """Return ``True`` when the current axes look like a phasor ``(g, s)`` plot."""
    x, y = current_axes(ndx)
    return _axis_token(x) == "g" and _axis_token(y) == "s"


def find_column(ndx: Any, token: str) -> Optional[np.ndarray]:
    """Return the first data column whose leading token equals ``token`` (or ``None``)."""
    try:
        df = ndx.data_source.data
    except Exception:
        return None
    if df is None or len(df.columns) == 0:
        return None
    token = token.lower()
    for col in df.columns:
        if _axis_token(col) == token:
            return np.asarray(df[col].values, dtype=float)
    return None


# --------------------------------------------------------------------------------------
# Overlay drawing
# --------------------------------------------------------------------------------------
def _hist_edges(ndx: Any) -> tuple[Optional[np.ndarray], Optional[np.ndarray]]:
    hist = getattr(ndx, "_histogram", {}).get("2d") if hasattr(ndx, "_histogram") else None
    if hist is None:
        return None, None
    if hasattr(hist, "x_edges"):
        return hist.x_edges, hist.y_edges
    if isinstance(hist, (tuple, list)) and len(hist) == 3:
        return hist[1], hist[2]
    return None, None


def _to_bins(ndx: Any, values, edges) -> np.ndarray:
    """Map data values to fractional bin positions; out-of-range → ``NaN`` (drawn as gap)."""
    if edges is None:
        return np.asarray(values, dtype=float)
    out = np.empty(len(values), dtype=float)
    for i, v in enumerate(values):
        b = ndx.value_to_bin(float(v), edges)
        out[i] = np.nan if b is None else float(b)
    return out


def draw_line_overlays(ndx: Any, overlays: list[dict], tag: str = "phasor") -> int:
    """Draw a LineSet on ``ndx.overlay_plot`` (mapped to bin space); return item count.

    Two overlay back-ends are supported: ndXplorer's painter-based
    ``DrawingOverlayWidget`` (``add_curve`` / ``clear_curves``, the one used by the real
    window and by the built-in equation overlays) and a plain pyqtgraph plot
    (``addItem`` — used in tests). Coordinates are mapped to histogram *bin* space so
    the LineSet lands on the same axes as the built-in curve overlays.
    """
    clear_line_overlays(ndx, tag)
    plot = getattr(ndx, "overlay_plot", None)
    if plot is None:
        return 0
    x_edges, y_edges = _hist_edges(ndx)
    store = _overlay_store(ndx)
    if hasattr(plot, "add_curve"):
        n = _draw_on_overlay_widget(plot, overlays, ndx, x_edges, y_edges, store, tag)
    else:
        n = _draw_on_pyqtgraph(plot, overlays, ndx, x_edges, y_edges, store, tag)
    return n


def _marker_polyline(x: float, y: float, half: float = 0.8) -> tuple[np.ndarray, np.ndarray]:
    """Small closed diamond around ``(x, y)`` (bin units) — a scatter stand-in for curves."""
    dx = np.array([0.0, half, 0.0, -half, 0.0])
    dy = np.array([half, 0.0, -half, 0.0, half])
    return x + dx, y + dy


def _draw_on_overlay_widget(plot, overlays, ndx, x_edges, y_edges, store, tag) -> int:
    """Draw a LineSet on the painter-based ``DrawingOverlayWidget`` (bin coordinates)."""
    if x_edges is not None:
        plot.set_axis_scale("xBottom", 0, len(x_edges) - 1)
    if y_edges is not None:
        plot.set_axis_scale("yLeft", 0, len(y_edges) - 1)
    added: list[Any] = []
    curves = getattr(plot, "_curves", None)

    def _add(xc, yc, color, width):
        mask = ~(np.isnan(xc) | np.isnan(yc))
        if mask.sum() < 2:
            return
        plot.add_curve(np.asarray(xc)[mask], np.asarray(yc)[mask], color=_qcolor(color), width=width)
        if curves is not None and curves:
            added.append(curves[-1])  # track our appended entry for surgical removal

    for ov in overlays or []:
        x = _to_bins(ndx, ov.get("x", []), x_edges)
        y = _to_bins(ndx, ov.get("y", []), y_edges)
        if len(x) == 0:
            continue
        style = ov.get("style", {}) or {}
        color = style.get("color", "w")
        if ov.get("kind") == "scatter":
            for xi, yi in zip(x, y):
                if np.isnan(xi) or np.isnan(yi):
                    continue
                mx, my = _marker_polyline(float(xi), float(yi))
                _add(mx, my, color, int(style.get("width", 2)))
        else:
            _add(x, y, color, int(style.get("width", 1)))
    store[tag] = {"widget": plot, "curves": added}
    plot.replot()
    return len(added)


def _qcolor(color: Any):
    """Best-effort convert a LineSet colour (name / #hex / rgb tuple) to a ``QColor``."""
    try:
        from qtpy.QtGui import QColor

        if isinstance(color, (tuple, list)):
            vals = [int(c * 255) if c <= 1 else int(c) for c in color]
            return QColor(*vals)
        return QColor(str(color))
    except Exception:
        return None


def _draw_on_pyqtgraph(plot, overlays, ndx, x_edges, y_edges, store, tag) -> int:
    """Draw a LineSet on a pyqtgraph plot (``addItem``); scatter gets symbols + labels."""
    import pyqtgraph as pg

    items: list[Any] = []
    for ov in overlays or []:
        x = _to_bins(ndx, ov.get("x", []), x_edges)
        y = _to_bins(ndx, ov.get("y", []), y_edges)
        if len(x) == 0:
            continue
        style = ov.get("style", {}) or {}
        color = style.get("color", "w")
        if ov.get("kind") == "scatter":
            item = pg.ScatterPlotItem(
                x=x, y=y, pen=pg.mkPen(color), brush=pg.mkBrush(color),
                size=style.get("size", 8), symbol=style.get("symbol", "o"),
            )
            plot.addItem(item)
            items.append(item)
            for xi, yi, label in zip(x, y, ov.get("labels", [])):
                if np.isnan(xi) or np.isnan(yi):
                    continue
                text = pg.TextItem(str(label), color=color, anchor=(0, 1))
                text.setPos(float(xi), float(yi))
                plot.addItem(text)
                items.append(text)
        else:
            pen = pg.mkPen(
                color, width=style.get("width", 1),
                style=pg.QtCore.Qt.DashLine if style.get("dash") else pg.QtCore.Qt.SolidLine,
            )
            item = pg.PlotCurveItem(x=x, y=y, pen=pen, connect="finite")
            plot.addItem(item)
            items.append(item)
    store[tag] = {"plot": plot, "items": items}
    return len(items)


def clear_line_overlays(ndx: Any, tag: str = "phasor") -> None:
    """Remove any previously drawn overlays for *tag* (both overlay back-ends)."""
    store = _overlay_store(ndx)
    entry = store.pop(tag, None)
    if not entry:
        return
    # painter-based DrawingOverlayWidget: remove only our tracked curve tuples
    if "widget" in entry:
        plot = entry["widget"]
        curves = getattr(plot, "_curves", None)
        if curves is not None:
            for c in entry.get("curves", []):
                try:
                    curves.remove(c)
                except ValueError:
                    pass
            plot.replot()
        return
    # pyqtgraph: remove each item
    plot = entry.get("plot")
    for item in entry.get("items", []):
        try:
            plot.removeItem(item)
        except Exception:
            pass


def _overlay_store(ndx: Any) -> dict:
    store = getattr(ndx, "_server_overlays", None)
    if store is None:
        store = {}
        ndx._server_overlays = store
    return store


# --------------------------------------------------------------------------------------
# High-level actions (used by the toolbar)
# --------------------------------------------------------------------------------------
def show_phasor_overlays(
    ndx: Any,
    sets: Optional[list[str]] = None,
    frequency_mhz: float = 80.0,
    harmonic: int = 1,
    taus: Optional[list[float]] = None,
    tau_d0: float = 4.0,
    tag: str = "phasor",
) -> int:
    """Fetch phasor reference geometry over RPC and draw it. Returns item count."""
    service = getattr(ndx, "phasor_service", None)
    if service is None:
        logger.info("No ChiSurf phasor service — skipping overlays")
        return 0
    overlays = service.overlays(
        frequency_mhz, sets=sets or ["semicircle", "lifetime_grid", "lifetime_ticks"],
        harmonic=harmonic, taus=taus, tau_d0=tau_d0,
    )
    return draw_line_overlays(ndx, overlays, tag=tag)


def show_fret_lines(ndx: Any, tag: str = "fret", **params: Any) -> int:
    """Fetch FRET lines over RPC and draw them. ``params`` → ``fret_line.overlays``."""
    service = getattr(ndx, "lines_service", None)
    if service is None:
        logger.info("No ChiSurf lines service — skipping FRET lines")
        return 0
    overlays = service.fret_line.overlays(**params)
    return draw_line_overlays(ndx, overlays, tag=tag)


def compute_apparent_lifetime_columns(ndx: Any, frequency_mhz: float = 80.0) -> list[str]:
    """Compute τ_φ / τ_M from the g,s columns and inject them; return added names."""
    service = getattr(ndx, "phasor_service", None)
    if service is None:
        return []
    g = find_column(ndx, "g")
    s = find_column(ndx, "s")
    if g is None or s is None:
        logger.warning("No g / s columns found — cannot compute apparent lifetimes")
        return []
    tau_phi, tau_m = service.apparent_lifetime(g, s, frequency_mhz)
    return inject_columns(ndx, {"tau_phi": tau_phi, "tau_m": tau_m})


def inject_columns(ndx: Any, columns: dict[str, Any]) -> list[str]:
    """Merge new named columns into the ndX ``DataSource`` and refresh the axis lists."""
    import pandas as pd

    from .core.data_source import DataSource

    df = pd.DataFrame({k: np.asarray(v, dtype=float) for k, v in columns.items()})
    new_ds = DataSource(data=df)
    if not ndx.data_source.merge(new_ds, mode="columns"):
        return []
    try:
        ndx.invalidate_values_cache()
    except Exception:
        pass
    try:
        ndx.update_parameter_names()
    except Exception:
        pass
    return list(df.columns)
