"""Pyqtgraph-backed plotting widgets for ndXplorer."""

from __future__ import annotations

from typing import Optional

import numpy as np
import pyqtgraph as pg
from qtpy import QtCore, QtGui, QtWidgets
from qtpy.QtGui import QFont, QImage

from ..logging_config import logging


def _axis_name(axis: object) -> str:
    if axis in ("xBottom", "bottom", 2):
        return "bottom"
    if axis in ("xTop", "top", 3):
        return "top"
    if axis in ("yLeft", "left", 0):
        return "left"
    if axis in ("yRight", "right", 1):
        return "right"
    return str(axis)


def _as_log_view_range(min_val: float, max_val: float) -> tuple[float, float]:
    """Convert a raw positive data range to pyqtgraph log-view coordinates."""
    high = float(max_val)
    if not np.isfinite(high) or high <= 0.0:
        return 0.0, 1.0

    low = float(min_val)
    if not np.isfinite(low) or low <= 0.0:
        low = min(high, max(high / 1.0e6, np.finfo(float).tiny))

    low = min(low, high)
    return float(np.log10(low)), float(np.log10(high))


class PGHistogramItem:
    """Small compatibility wrapper around ``PlotDataItem``."""

    def __init__(
        self,
        plot_item: pg.PlotItem,
        *,
        color: str,
        fill: float = 0.2,
        orientation: str = "horizontal",
    ) -> None:
        self._plot_item = plot_item
        self._orientation = orientation
        fill_brush = pg.mkBrush(QtGui.QColor(color).lighter(130).getRgb()[:3] + (int(255 * fill),))
        fill_level = None if orientation == "vertical" else 0
        item_kwargs = {
            "pen": pg.mkPen(color, width=2),
            "stepMode": False,
        }
        if fill_level is not None:
            item_kwargs["fillLevel"] = fill_level
            item_kwargs["fillBrush"] = fill_brush
        self._item = pg.PlotDataItem(
            **item_kwargs,
        )
        self._plot_item.addItem(self._item)
        self._baseline_item = None
        self._fill_item = None
        if orientation == "vertical" and fill > 0:
            self._baseline_item = pg.PlotDataItem(pen=None)
            self._plot_item.addItem(self._baseline_item)
            self._fill_item = pg.FillBetweenItem(
                curve1=self._item,
                curve2=self._baseline_item,
                brush=fill_brush,
            )
            self._plot_item.addItem(self._fill_item)

    def set_data(self, x_data, y_data) -> None:
        """Update curve data using the guiqwt-compatible method name."""
        x_values, y_values = self._as_step_data(np.asarray(x_data), np.asarray(y_data))
        self._item.setData(x_values, y_values)
        if self._baseline_item is not None:
            self._baseline_item.setData(np.zeros_like(x_values), y_values)

    @staticmethod
    def _as_step_data(x_data: np.ndarray, y_data: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Expand histogram edges/counts into step coordinates when possible."""
        x_values = np.asarray(x_data, dtype=float)
        y_values = np.asarray(y_data, dtype=float)
        if x_values.ndim != 1 or y_values.ndim != 1:
            return x_values, y_values

        if x_values.size == y_values.size + 1:
            return np.repeat(x_values, 2)[1:-1], np.repeat(y_values, 2)
        if y_values.size == x_values.size + 1:
            return np.repeat(x_values, 2), np.repeat(y_values, 2)[1:-1]
        return x_values, y_values


class PGRangeSelection:
    """Compatibility wrapper for an editable 1D range selection.

    Speaks **data** coordinates on the outside and *view* coordinates to
    pyqtgraph, because on a log axis those are not the same thing: the region
    item lives at ``log10(value)``. Handing it a raw range put a selection over
    photon counts of 60 to 450 094 at view-x 60 to 450 094 — that is 10**60 to
    10**450094, so the region left the plot entirely — and reading it back gave
    log10 values that the range spin boxes then displayed as counts. "Auto"
    looked broken for the same reason: it fits the region to the data range, and
    the fit was being written in the wrong units.
    """

    def __init__(self, min_val: float, max_val: float, is_log=None) -> None:
        """``is_log`` is a callable, not a flag: the axis can be toggled later."""
        self._is_log = is_log if callable(is_log) else (lambda: False)
        #: Which projection the item's stored numbers are currently in. The item
        #: holds *view* coordinates and does not know the axis changed under it,
        #: so this is what :meth:`reproject` compares against.
        self._drawn_log = bool(self._is_log())
        low, high = self._to_view(float(min_val), float(max_val))
        self.item = pg.LinearRegionItem(
            values=(low, high),
            orientation="vertical",
            movable=True,
        )

    def _to_view(self, low: float, high: float) -> tuple[float, float]:
        """Data coordinates to the ones the region item is drawn in."""
        if not self._is_log():
            return float(low), float(high)
        return _as_log_view_range(low, high)

    def _from_view(self, low: float, high: float, log=None) -> tuple[float, float]:
        """The inverse, guarded against the overflow a stale range can hold.

        *log* names the projection to invert; it defaults to the axis's current
        one, but :meth:`reproject` has to undo the *previous* one.
        """
        if not (self._is_log() if log is None else log):
            return float(low), float(high)
        out = []
        for value in (low, high):
            try:
                out.append(float(10.0 ** float(value)))
            except OverflowError:
                out.append(float("inf"))
        return out[0], out[1]

    @property
    def changed(self):
        """Emitted continuously while the range is dragged.

        Exposed because the region *says* when it moves, and a caller that does
        not listen is left asking. The one here polled ``get_range`` twice a
        second, which is neither the rate the region moves at nor the rate the
        plot could be redrawn at.
        """
        return self.item.sigRegionChanged

    @property
    def change_finished(self):
        """Emitted once, when the drag ends."""
        return self.item.sigRegionChangeFinished

    def get_range(self) -> tuple[float, float]:
        """Return the current selected range, in **data** coordinates."""
        low, high = self.item.getRegion()
        return self._from_view(float(low), float(high), log=self._drawn_log)

    def set_range(self, min_val: float, max_val: float) -> None:
        """Set the selected range, given in **data** coordinates."""
        self._drawn_log = bool(self._is_log())
        low, high = self._to_view(float(min_val), float(max_val))
        self.item.setRegion((low, high))

    def reproject(self) -> None:
        """Redraw the same *data* range after the axis scale changed.

        The region item stores view coordinates and nothing tells it the axis
        was toggled, so its numbers silently change meaning: a range set on a
        log axis (view 1.78 to 5.65 for counts of 60 to 450 094) becomes, the
        moment the axis goes linear, a selection of 1.78 to 5.65 *counts* —
        a sliver at the left edge that gates away the whole measurement while
        the range boxes still read 60 and 450 094. The other direction is the
        one that leaves the plot entirely, at 10**60.

        So the range is read back through the projection it was *written* in and
        written again in the current one. A no-op when the scale has not moved.
        """
        now = bool(self._is_log())
        if now == self._drawn_log:
            return
        low, high = self.item.getRegion()
        data_low, data_high = self._from_view(float(low), float(high),
                                              log=self._drawn_log)
        self.set_range(data_low, data_high)


class PGHistogramPlot(pg.PlotWidget):
    """PlotWidget with the subset of Qwt/guiqwt API ndXplorer uses."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent=parent)
        self.setBackground("w")
        self.showGrid(x=False, y=False)
        self._axis_enabled = {
            "bottom": True,
            "top": False,
            "left": True,
            "right": False,
        }
        self._axis_scales = {
            "bottom": "linear",
            "top": "linear",
            "left": "linear",
            "right": "linear",
        }
        #: Range selections drawn on this plot, so a scale change can re-project
        #: them: they store view coordinates and would otherwise keep the
        #: numbers while losing the meaning.
        self._range_selections: list[PGRangeSelection] = []

    def add_histogram(
        self,
        *,
        color: str,
        fill: float = 0.2,
        orientation: str = "horizontal",
    ) -> PGHistogramItem:
        """Create and attach a marginal histogram item."""
        return PGHistogramItem(
            self.getPlotItem(),
            color=color,
            fill=fill,
            orientation=orientation,
        )

    def add_range_selection(self, min_val: float, max_val: float) -> PGRangeSelection:
        """Create and attach a guiqwt-compatible range selection.

        The selection is told how to ask whether its axis is logarithmic, rather
        than being given the answer once: the user can toggle the scale at any
        time and the region has to keep meaning the same data range.
        """
        selection = PGRangeSelection(
            min_val, max_val,
            is_log=lambda: self._axis_scales.get("bottom") == "log",
        )
        self.getPlotItem().addItem(selection.item)
        self._range_selections.append(selection)
        return selection

    def enableAxis(self, axis, enabled: bool) -> None:
        """Enable or disable an axis using Qwt-compatible naming."""
        name = _axis_name(axis)
        self._axis_enabled[name] = enabled
        self.getPlotItem().showAxis(name, show=enabled)

    def axisEnabled(self, axis) -> bool:
        """Return whether an axis is visible."""
        return self._axis_enabled.get(_axis_name(axis), False)

    def setAxisScale(self, axis, min_val: float, max_val: float) -> None:
        """Set a view range using Qwt-compatible naming.

        Whether to convert to log coordinates is decided by the axis
        *direction*, not by the name asked for. Qwt has four independent axes;
        pyqtgraph has two, so "bottom" and "top" are one x axis and setting
        either one sets both. Reading the scale per name meant a caller looping
        over ``("bottom", "top")`` -- which is what the marginal autoscaling
        does -- converted the range for "bottom" and then overwrote it with the
        raw values for "top", whose entry still said linear. On a log axis that
        put the view at 10**60 to 10**450094, clamped to the float limits: the
        axis read -307 to 308 and the histogram was an unreadable block.
        """
        name = _axis_name(axis)
        direction = "bottom" if name in {"bottom", "top"} else "left"
        if self._axis_scales.get(direction) == "log":
            min_val, max_val = _as_log_view_range(min_val, max_val)
        if name in {"bottom", "top"}:
            self.setXRange(float(min_val), float(max_val), padding=0)
        elif name in {"left", "right"}:
            self.setYRange(float(min_val), float(max_val), padding=0)

    def set_axis_scale(self, axis: str, scale: str) -> None:
        """Set linear or logarithmic scaling for the requested axis.

        Recorded for *both* names of the same direction, so the two cannot
        disagree about an axis they share.
        """
        name = _axis_name(axis)
        for shared in (("bottom", "top") if name in {"bottom", "top"}
                       else ("left", "right")):
            self._axis_scales[shared] = scale
        if name in {"bottom", "top"}:
            self.getPlotItem().setLogMode(x=scale == "log")
        elif name in {"left", "right"}:
            self.getPlotItem().setLogMode(y=scale == "log")
        # The regions are drawn against the x axis, so only that direction
        # moves them -- but re-projecting is a no-op when the scale is
        # unchanged, so there is nothing to guard.
        for selection in self._range_selections:
            selection.reproject()

    def set_axis_font(self, axis: str, font: QFont) -> None:
        """Apply a tick font to a visible axis."""
        self.getPlotItem().getAxis(_axis_name(axis)).setTickFont(font)

    def set_axis_title(self, axis: str, title: str) -> None:
        """Set an axis label using the guiqwt-compatible method name."""
        self.getPlotItem().getAxis(_axis_name(axis)).setLabel(text=title or "")

    def canvas(self):
        """Return the underlying viewport for event filter compatibility."""
        return self.getPlotItem().getViewBox().scene().views()[0].viewport()

    def replot(self) -> None:
        """Refresh the widget."""
        self.update()


class PGImageWidget(QtWidgets.QWidget):
    """Pyqtgraph image widget with the existing ndXplorer image API."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._data: Optional[np.ndarray] = None
        self._is_rgb = False
        self._colormap_name = "viridis"
        self._vmin = 0.0
        self._vmax = 1.0
        self._axis_enabled = {
            "bottom": False,
            "top": False,
            "left": False,
            "right": False,
        }

        self.plot_widget = pg.PlotWidget(parent=self)
        self.plot_widget.setBackground("w")
        self.plot_widget.setAspectLocked(False)
        self.plot_widget.showGrid(x=False, y=False)
        self.image_item = pg.ImageItem(axisOrder="row-major")
        self.plot_widget.addItem(self.image_item)

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.plot_widget)

    def set_data(self, data: np.ndarray) -> None:
        """Set the image data: a 2-D scalar map, or an ``(ny, nx, 3|4)`` RGB(A).

        RGB is how the cluster overlay is drawn — every cluster in its own
        colour at once. Such an image carries its colours directly, so the
        colormap and the contrast levels must not be applied to it: doing so
        would remap the red channel through viridis and produce something that
        is neither the clusters nor the density.
        """
        if data is None or data.size == 0:
            data = np.zeros((1, 1))
        self._data = np.ascontiguousarray(data)
        self._is_rgb = self._data.ndim == 3 and self._data.shape[-1] in (3, 4)
        self.image_item.setImage(self._data, autoLevels=False)
        if self._is_rgb:
            # RGB carries absolute channel values. The contrast levels left over
            # from the density view (e.g. 1..33 counts) would clip every channel
            # to full scale and render every cluster white, so the levels must be
            # reset to the channel range rather than merely left alone.
            top = 255.0 if self._data.dtype == np.uint8 else 1.0
            self.image_item.setLevels((0.0, top))
        else:
            self.image_item.setLevels((self._vmin, self._vmax))
        self.set_axis_scale("xBottom", 0, self._data.shape[1] - 1)
        self.set_axis_scale("yLeft", 0, self._data.shape[0] - 1)

    @property
    def data(self) -> Optional[np.ndarray]:
        """Return the current image data."""
        return self._data

    def set_background_image(self, image_path: str) -> None:
        """Load a fallback background image for compatibility."""
        image = QImage(image_path)
        if image.isNull():
            logging.warning("Failed to load pyqtgraph background image: %s", image_path)
            return
        self._background_image = image

    def set_colormap(
        self,
        colormap_name: str,
        vmin: Optional[float] = None,
        vmax: Optional[float] = None,
    ) -> None:
        """Set the pyqtgraph colormap and optional levels."""
        self._colormap_name = colormap_name
        if vmin is not None:
            self._vmin = float(vmin)
        if vmax is not None:
            self._vmax = float(vmax)
        if getattr(self, "_is_rgb", False):
            # An RGB image already carries its colours; applying a lookup table
            # would remap them into the colormap and destroy the cluster identity.
            return
        cmap = pg.colormap.get(colormap_name)
        self.image_item.setLookupTable(cmap.getLookupTable(0.0, 1.0, 256))
        self.image_item.setLevels((self._vmin, self._vmax))

    def set_lut_range(self, range_values) -> None:
        """Set display levels using the guiqwt-compatible method name."""
        if len(range_values) >= 2:
            self.set_colormap(self._colormap_name, range_values[0], range_values[1])

    def set_axis_scale(self, axis: str, min_val: float, max_val: float) -> None:
        """Set visible data range for one axis."""
        if axis in ("xBottom", "x", "bottom"):
            self.plot_widget.setXRange(float(min_val), float(max_val), padding=0)
        elif axis in ("yLeft", "y", "left"):
            self.plot_widget.setYRange(float(min_val), float(max_val), padding=0)

    def enable_axis(self, axis: str, enabled: bool) -> None:
        """Enable or disable an axis."""
        name = _axis_name(axis)
        self._axis_enabled[name] = enabled
        self.plot_widget.getPlotItem().showAxis(name, show=enabled)

    def enableAxis(self, axis, enabled: bool) -> None:
        """Qwt-compatible axis visibility wrapper."""
        self.enable_axis(_axis_name(axis), enabled)

    def axis_enabled(self, axis: str) -> bool:
        """Return whether an axis is visible."""
        return self._axis_enabled.get(_axis_name(axis), False)

    def axisEnabled(self, axis) -> bool:
        """Qwt-compatible axis visibility query."""
        return self.axis_enabled(_axis_name(axis))

    def set_axis_font(self, axis: str, font: QFont) -> None:
        """Apply a tick font to a plot axis."""
        self.plot_widget.getPlotItem().getAxis(_axis_name(axis)).setTickFont(font)

    def set_axis_title(self, axis: str, title: str) -> None:
        """Set an axis label using the guiqwt-compatible method name."""
        self.plot_widget.getPlotItem().getAxis(_axis_name(axis)).setLabel(text=title or "")

    def canvas(self):
        """Return the viewport used for mouse event filters."""
        return self.plot_widget.getPlotItem().getViewBox().scene().views()[0].viewport()

    def replot(self) -> None:
        """Refresh the widget."""
        self.plot_widget.update()
        self.update()

    def invTransform(self, axis_id, pixel_pos):
        """Convert a pixel position to a data coordinate."""
        if self._data is None:
            return 0.0
        view_box = self.plot_widget.getPlotItem().getViewBox()
        point = view_box.mapSceneToView(QtCore.QPointF(float(pixel_pos), float(pixel_pos)))
        return point.x() if axis_id in (0, _QWT_X_BOTTOM) else point.y()

    @property
    def xBottom(self):
        """Return the x-bottom axis identifier."""
        return 0

    @property
    def yLeft(self):
        """Return the y-left axis identifier."""
        return 1
