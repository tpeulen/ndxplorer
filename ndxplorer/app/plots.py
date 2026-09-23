"""The plots: the 2-D histogram, its x and y marginals, and the z marginal.

Hand-written emtk, because a spec cannot say "a heatmap under a rubber band".
Drawn with :mod:`emtk.implot` in the Qt window's arrangement: the x marginal
over the map with its ticks and title on top, the y marginal to the right with
its ticks and title on the right, and no axes on the map itself -- the
marginals are its axes.

Speed: the map is one texture of bins, coloured with numpy
(:func:`ndxplorer.plotting.colormap_lut.apply_colormap`) and rebuilt only when
the histogram or the colour settings change; ImPlot draws it as one image. The
marginals are step outlines of a few hundred points. No per-point Python on the
data.

Interaction, as in the Qt window: dragging on the map draws a rectangle that
becomes two interval gates (x and y); the region on the z marginal is dragged
by its edges. The gate selected in the Selection table is shown, and can be
dragged: an x/y gate pair as a rectangle on the map, a single interval as a
pair of lines on its marginal.
"""

from __future__ import annotations

from typing import Optional

import numpy as np

from . import theme
from .model import ExplorerModel

__all__ = ["PlotArea", "step_outline"]

#: Pixels a drag must move before it is a rectangle rather than a click.
DRAG_THRESHOLD = 3.0
#: Height of the red axis title above the x marginal / width beside the y one.
TITLE_BAND = 22.0


def step_outline(edges, counts) -> tuple:
    """The outline of a histogram drawn in steps, closed down to zero.

    Returns ``(xs, ys)`` lists: ``(e0, 0), (e0, c0), (e1, c0), (e1, c1), ...,
    (en, 0)``.
    """
    edges = np.asarray(edges, dtype=np.float64)
    counts = np.asarray(counts, dtype=np.float64)
    n = min(len(counts), len(edges) - 1)
    if n <= 0:
        return [], []
    xs = np.empty(2 * n + 2)
    ys = np.empty(2 * n + 2)
    xs[0], ys[0] = edges[0], 0.0
    xs[1:-1:2], xs[2:-1:2] = edges[:n], edges[1:n + 1]
    ys[1:-1:2] = ys[2:-1:2] = np.nan_to_num(counts[:n])
    xs[-1], ys[-1] = edges[n], 0.0
    return xs.tolist(), ys.tolist()


class PlotArea:
    """Draws the plots of an :class:`ExplorerModel` and turns drags into gates."""

    def __init__(self, model: ExplorerModel) -> None:
        self.model = model
        self._texture = None
        self._texture_key = None
        #: Bump to redraw the map texture when a feature's ``map_image`` changes
        #: without the histogram changing (cluster colours switched on).
        self.image_revision = 0
        self._titles: list = []
        #: ``(x0, y0)`` in data units while a rectangle is being dragged.
        self.band_start: Optional[tuple] = None
        self.band_end: Optional[tuple] = None
        self._band_pixels: Optional[tuple] = None
        #: Plot rectangles of the last frame, in pixels, by name.
        self.rects: dict = {}

    # ---------------------------------------------------------------- data
    def texture(self):
        """The 2-D histogram as a texture, row 0 at the top (highest y)."""
        from emtk.texture import Texture

        from ..plotting.colormap_lut import apply_colormap

        hist = self.model.histograms
        if hist is None:
            return None
        key = (hist.revision, self.model.colormap, self.model.vmin, self.model.vmax,
               self.model.log_counts, self.image_revision)
        if key != self._texture_key:
            values = self.model.map_values()
            vmin, vmax = self.model.vmin, self.model.vmax
            if not vmax > vmin:
                vmax = vmin + 1.0
            rgba = None
            for feature in self._features():
                rgba = feature.map_image(values)
                if rgba is not None:
                    rgba = np.flipud(np.asarray(rgba, dtype=np.uint8))
                    break
            if rgba is None:
                rgba = apply_colormap(np.flipud(values), self.model.colormap, vmin, vmax)
            ny, nx = values.shape
            self._texture = Texture(max(nx, 1), max(ny, 1), np.ascontiguousarray(rgba).tobytes(),
                                    filter="nearest")
            self._texture_key = key
        return self._texture

    # ------------------------------------------------------------ drawing
    def begin_frame(self) -> None:
        """Forget last frame's plot boxes and titles; call before any plot draws."""
        self._titles = []
        self.rects = {}

    def draw(self, boxes: dict) -> None:
        """The x marginal, the map and the y marginal, in their boxes.

        The plots are drawn with no padding: the marginals are the map's axes,
        so their plot areas have to meet the map's edges exactly. The rest of
        ImPlot's default style is left as it is.
        """
        from emtk import implot

        implot.push_style_var(implot.STYLE_VAR_PLOT_PADDING, (0.0, 0.0))
        try:
            self._draw_xmarginal(boxes["xmarginal"])
            self._draw_map(boxes["map"])
            self._draw_ymarginal(boxes["ymarginal"])
        finally:
            implot.pop_style_var()

    def _begin(self, title: str, box, flags_extra: int = 0) -> None:
        import emtk
        from emtk import implot

        x, y, w, h = box
        emtk.set_cursor_screen_pos((x, y))
        flags = implot.FLAGS_CANVAS_ONLY | implot.FLAGS_NO_FRAME | flags_extra
        implot.begin_plot(title, (max(w, 20.0), max(h, 20.0)), flags)

    @staticmethod
    def _axis_flags(decorated: bool, opposite: bool = False) -> int:
        from emtk import implot

        flags = implot.AXIS_FLAGS_NO_GRID_LINES | implot.AXIS_FLAGS_LOCK | \
            implot.AXIS_FLAGS_NO_MENUS | implot.AXIS_FLAGS_NO_HIGHLIGHT
        if not decorated:
            flags |= implot.AXIS_FLAGS_NO_DECORATIONS
        if opposite:
            flags |= implot.AXIS_FLAGS_OPPOSITE
        return flags

    def _range(self, key: str):
        """The axis range and scale the model's histogram was filled with."""
        hist = self.model.histograms
        axis = self.model.axis(key)
        if hist is not None and key in ("x", "y"):
            edges = hist.x_edges if key == "x" else hist.y_edges
            lo, hi = float(edges[0]), float(edges[-1])
        else:
            lo, hi = float(axis.lo), float(axis.hi)
        if not hi > lo:
            hi = lo + 1.0
        log = axis.log and lo > 0
        return lo, hi, log

    def _setup_x(self, key: str, decorated: bool, opposite: bool = False) -> None:
        from emtk import implot

        lo, hi, log = self._range(key)
        implot.setup_axis(implot.AXIS_X1, None, self._axis_flags(decorated, opposite))
        if log:
            implot.setup_axis_scale(implot.AXIS_X1, implot.SCALE_LOG10)
        implot.setup_axis_limits(implot.AXIS_X1, lo, hi, implot.COND_ALWAYS)

    def _setup_y(self, key: str, decorated: bool, opposite: bool = False) -> None:
        from emtk import implot

        lo, hi, log = self._range(key)
        implot.setup_axis(implot.AXIS_Y1, None, self._axis_flags(decorated, opposite))
        if log:
            implot.setup_axis_scale(implot.AXIS_Y1, implot.SCALE_LOG10)
        implot.setup_axis_limits(implot.AXIS_Y1, lo, hi, implot.COND_ALWAYS)

    def _draw_xmarginal(self, box) -> None:
        from emtk import implot

        x, y, w, h = box
        self._titles.append(("h", x, y, w, TITLE_BAND, self.model.x.name))
        self._begin("##x-marginal", (x, y + TITLE_BAND, w, h - TITLE_BAND))
        self._setup_x("x", decorated=True, opposite=True)
        hist = self.model.histograms
        counts = hist.x[1] if hist is not None else np.zeros(1)
        top = float(np.nanmax(counts)) if np.size(counts) and np.nanmax(counts) > 0 else 1.0
        implot.setup_axis(implot.AXIS_Y1, None, self._axis_flags(False))
        implot.setup_axis_limits(implot.AXIS_Y1, 0.0, top * 1.05, implot.COND_ALWAYS)
        if hist is not None:
            xs, ys = step_outline(*hist.x)
            implot.plot_shaded("##x-fill", xs, ys, spec={"fill_color": theme.axis_colour("x", 110)})
            implot.plot_line("##x-line", xs, ys, spec={"line_color": theme.axis_colour("x"),
                                                       "line_weight": 1.5})
            self._gate_lines("x", vertical=True)
            self._feature_items("xmarginal")
        self.rects["xmarginal"] = self._plot_rect()
        implot.end_plot()

    def _draw_ymarginal(self, box) -> None:
        from emtk import implot

        x, y, w, h = box
        self._titles.append(("v", x + w - TITLE_BAND, y, TITLE_BAND, h, self.model.y.name))
        self._begin("##y-marginal", (x, y, w - TITLE_BAND, h))
        hist = self.model.histograms
        counts = hist.y[1] if hist is not None else np.zeros(1)
        top = float(np.nanmax(counts)) if np.size(counts) and np.nanmax(counts) > 0 else 1.0
        implot.setup_axis(implot.AXIS_X1, None, self._axis_flags(False))
        implot.setup_axis_limits(implot.AXIS_X1, 0.0, top * 1.05, implot.COND_ALWAYS)
        self._setup_y("y", decorated=True, opposite=True)
        if hist is not None:
            ys, xs = step_outline(*hist.y)
            implot.plot_line("##y-line", xs, ys, spec={"line_color": theme.axis_colour("y"),
                                                       "line_weight": 1.5})
            self._gate_lines("y", vertical=False)
            self._feature_items("ymarginal")
        self.rects["ymarginal"] = self._plot_rect()
        implot.end_plot()

    @staticmethod
    def _plot_rect() -> tuple:
        from emtk import implot

        px, py = implot.get_plot_pos()
        pw, ph = implot.get_plot_size()
        return (px, py, pw, ph)

    def _splash(self, w: float, h: float):
        """ndXplorer's splash picture, fitted into ``w x h``; ``(texture, size, bg)``."""
        import pathlib

        from emtk.texture import Texture

        key = (int(w), int(h))
        cached = getattr(self, "_splash_cache", None)
        if cached is not None and cached[0] == key:
            return cached[1]
        path = pathlib.Path(__file__).resolve().parents[1] / "ui" / "background.png"
        try:
            from PIL import Image

            with Image.open(path) as image:
                image = image.convert("RGBA")
                background = image.getpixel((2, 2))
                scale = min(w / image.width, h / image.height)
                size = (max(int(image.width * scale), 1), max(int(image.height * scale), 1))
                image = image.resize(size, Image.LANCZOS)
                result = (Texture(size[0], size[1], image.tobytes()), size, tuple(background))
        except (OSError, ImportError):
            result = None
        self._splash_cache = (key, result)
        return result

    def _draw_splash(self, box) -> None:
        """No data yet: the splash picture where the map will be, as in the Qt window."""
        import emtk

        x, y, w, h = box
        splash = self._splash(w, h)
        draw = emtk.get_window_draw_list()
        if splash is None:
            draw.add_rect_filled((x, y), (x + w, y + h), (255, 255, 255, 255))
            return
        texture, (sw, sh), background = splash
        draw.add_rect_filled((x, y), (x + w, y + h), background)
        left, top = x + (w - sw) / 2.0, y + (h - sh) / 2.0
        draw.add_image(texture, (left, top), (left + sw, top + sh))
        self.rects["map"] = box

    def _draw_map(self, box) -> None:
        from emtk import implot

        if self.model.histograms is None:
            self._draw_splash(box)
            return
        self._begin("##map", box)
        self._setup_x("x", decorated=False)
        self._setup_y("y", decorated=False)
        texture = self.texture()
        if texture is not None:
            (x0, x1, _), (y0, y1, _) = self._range("x"), self._range("y")
            implot.plot_image("##histogram", texture, (x0, y0), (x1, y1))
            consumed = any(f.plot_input("map") for f in self._features())
            if not consumed and not self._gate_rect():
                self._rubber_band()
            self._feature_items("map")
        self.rects["map"] = self._plot_rect()
        implot.end_plot()

    # ------------------------------------------------------- interaction
    def _rubber_band(self) -> None:
        """A drag on the map: a rectangle that becomes two gates on release."""
        import emtk
        from emtk import implot

        io = emtk.get_io()
        if implot.is_plot_hovered() and io.mouse_clicked[0] and self.band_start is None:
            point = implot.get_plot_mouse_pos()
            self.band_start = (point.x, point.y)
            self._band_pixels = tuple(io.mouse_pos)
            self.band_end = self.band_start
        if self.band_start is None:
            return
        point = implot.get_plot_mouse_pos()
        self.band_end = (point.x, point.y)
        limits = implot.get_plot_limits()
        (bx0, by0), (bx1, by1) = self.band_start, self.band_end
        clamp = lambda v, lo, hi: min(max(v, min(lo, hi)), max(lo, hi))  # noqa: E731
        bx1 = clamp(bx1, limits.x_min, limits.x_max)
        by1 = clamp(by1, limits.y_min, limits.y_max)
        moved = abs(io.mouse_pos[0] - self._band_pixels[0]) + \
            abs(io.mouse_pos[1] - self._band_pixels[1]) > DRAG_THRESHOLD
        if moved:
            implot.drag_rect(900, min(bx0, bx1), min(by0, by1), max(bx0, bx1), max(by0, by1),
                             theme.gate_colour(), implot.DRAG_TOOL_FLAGS_NO_INPUTS |
                             implot.DRAG_TOOL_FLAGS_NO_FIT)
        if not io.mouse_down[0]:
            if moved:
                self.model.add_rectangle((bx0, bx1), (by0, by1))
            self.band_start = self.band_end = self._band_pixels = None

    def _features(self):
        app = getattr(self.model, "app", None)
        return getattr(app, "features", ())

    def _feature_items(self, plot: str) -> None:
        """The features' overlays in *plot* (see :mod:`ndxplorer.app.features`)."""
        for feature in self._features():
            feature.draw_plot(plot)

    def _selected_pair(self):
        """The selected gate and its partner, when they are an x/y interval pair."""
        model = self.model
        index = model.selected_gate
        if index is None or not 0 <= index < len(model.gates):
            return None
        gate = model.gates[index]
        names = (model.x.name, model.y.name)
        if gate.meta is not None or gate.name not in names:
            return None
        for other in (index + 1, index - 1):
            if 0 <= other < len(model.gates):
                partner = model.gates[other]
                if partner.meta is None and {gate.name, partner.name} == set(names) \
                        and gate.name != partner.name:
                    return (index, other) if gate.name == names[0] else (other, index)
        return None

    def _gate_rect(self) -> bool:
        """The selected x/y gate pair as a rectangle that can be dragged."""
        from emtk import implot

        pair = self._selected_pair()
        if pair is None:
            return False
        gx, gy = (self.model.gates[i] for i in pair)
        result = implot.drag_rect(1, gx.lower, gy.lower, gx.upper, gy.upper, theme.gate_colour(),
                                  implot.DRAG_TOOL_FLAGS_NO_FIT)
        if result.modified:
            self.model.edit_gate(pair[0], "lower", min(result.x_min, result.x_max))
            self.model.edit_gate(pair[0], "upper", max(result.x_min, result.x_max))
            self.model.edit_gate(pair[1], "lower", min(result.y_min, result.y_max))
            self.model.edit_gate(pair[1], "upper", max(result.y_min, result.y_max))
        return bool(result.hovered or result.held)

    def _gate_lines(self, key: str, vertical: bool) -> None:
        """The selected single-axis gate on this marginal, as two draggable lines."""
        from emtk import implot

        model = self.model
        index = model.selected_gate
        if index is None or not 0 <= index < len(model.gates):
            return
        gate = model.gates[index]
        if gate.meta is not None or gate.name != model.axis(key).name:
            return
        drag = implot.drag_line_x if vertical else implot.drag_line_y
        for n, field in enumerate(("lower", "upper")):
            result = drag(10 + n, getattr(gate, field), theme.gate_colour(), 1.5,
                          implot.DRAG_TOOL_FLAGS_NO_FIT)
            if result.modified:
                model.edit_gate(index, field, result.value)

    # ------------------------------------------------------------------ z
    def draw_z(self, width: float, height: float) -> None:
        """The z marginal, inside the z panel, with its dragged range."""
        import emtk
        from emtk import implot

        model = self.model
        x, y = emtk.get_cursor_screen_pos()
        implot.begin_plot("##z-marginal", (max(width, 40.0), max(height, 40.0)),
                          implot.FLAGS_CANVAS_ONLY | implot.FLAGS_NO_FRAME)
        lo, hi, log = self._range("z")
        hist = model.histograms
        counts = hist.z[1] if hist is not None and hist.z is not None else np.zeros(1)
        top = float(np.nanmax(counts)) if np.size(counts) and np.nanmax(counts) > 0 else 1.0
        implot.setup_axis(implot.AXIS_X1, None, self._axis_flags(True))
        if log:
            implot.setup_axis_scale(implot.AXIS_X1, implot.SCALE_LOG10)
        implot.setup_axis_limits(implot.AXIS_X1, lo, hi, implot.COND_ALWAYS)
        implot.setup_axis(implot.AXIS_Y1, None, self._axis_flags(True))
        implot.setup_axis_limits(implot.AXIS_Y1, 0.0, top * 1.1, implot.COND_ALWAYS)
        if model.index_of(model.z.name) >= 0:
            zlo, zhi = model.z_range
            implot.plot_shaded("##z-region", [zlo, zhi], [top * 1.1, top * 1.1],
                               spec={"fill_color": theme.gate_colour(50)})
            if hist is not None and hist.z is not None:
                xs, ys = step_outline(*hist.z)
                implot.plot_shaded("##z-fill", xs, ys, spec={"fill_color": theme.axis_colour("z", 110)})
                implot.plot_line("##z-line", xs, ys, spec={"line_color": theme.axis_colour("z"),
                                                           "line_weight": 1.5})
            first = implot.drag_line_x(20, zlo, theme.gate_colour(), 1.5,
                                       implot.DRAG_TOOL_FLAGS_NO_FIT)
            second = implot.drag_line_x(21, zhi, theme.gate_colour(), 1.5,
                                        implot.DRAG_TOOL_FLAGS_NO_FIT)
            if first.modified or second.modified:
                model.set_z_range(first.value, second.value)
            self._feature_items("zmarginal")
        self.rects["zmarginal"] = self._plot_rect()
        implot.end_plot()

    # --------------------------------------------------------- the titles
    def draw_overlays(self, painter) -> None:
        """The red axis titles, over the frame (the rotated one needs the painter)."""
        from emtk.painter import ALIGN_HCENTER, ALIGN_VCENTER

        for kind, x, y, w, h, text in self._titles:
            if not text:
                continue
            if kind == "h":
                painter.text(x, y, w, h, ALIGN_HCENTER | ALIGN_VCENTER, text, theme.text_colour(),
                             True)
            else:
                rotate = getattr(painter, "text_rotated", None)
                if callable(rotate):
                    # The box is the text's own, unturned, centred on the band.
                    cx, cy = x + w / 2.0, y + h / 2.0
                    rotate(cx - h / 2.0, cy - w / 2.0, h, w, ALIGN_HCENTER | ALIGN_VCENTER,
                           text, theme.text_colour(), -90.0)
                else:
                    painter.text(x, y, w, h, ALIGN_HCENTER | ALIGN_VCENTER, text,
                                 theme.text_colour(), True)
