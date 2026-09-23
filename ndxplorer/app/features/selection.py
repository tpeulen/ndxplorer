"""The selection tools of the emtk app: gate menus, picking, and mask painting.

The Selection table itself is core: a ``data_table`` over
``app.model.gates`` (:class:`ndxplorer.core.gates.GateList`, the one gate list
both GUIs gate by). The rectangle drag, the z-range gate, weights and the
NaN/inf switches are core as well. This feature adds what acts *on* gates:

* **The gate table's context menu.** Select All, Clear, Delete, and "Send
  selection to ▸" (ChiSurf's burst analyses, over its RPC).
* **The 2-D map's context menu.** Copy 2D Histogram (CSV), Copy 1D
  Histograms (CSV), Send to Napari, Fit gate to the population here, and
  "Send selection to ▸".
* **Fit gate to the population here.** The right-click position, in data
  units, seeds :func:`ndxplorer.core.population_pick.fit_population`, and
  the fitted ellipse becomes a 2-D Gaussian gate. In the Qt window this was
  broken: it compared bin indices against data ranges, so every pick was
  refused.
* **The Draw Mask panel** (``selection/draw_mask.view.json``). A round brush
  paints categories onto the map's bins
  (:class:`ndxplorer.core.mask_paint.MaskCanvas`), and Apply turns a category
  into a mask gate. In the Qt window this was broken too: strokes never
  registered.

Whatever cannot work where the app runs is shown disabled with the reason in
its label, never left out. The ChiSurf RPC and napari both need a native
process, so in the browser they say so.
"""

from __future__ import annotations

import json
import os
import pathlib
import subprocess
import sys
import tempfile
from typing import Callable, Dict, List, Optional

import numpy as np

from . import Feature

__all__ = ["SelectionFeature", "DrawMaskModel", "create", "ellipse_outline", "in_browser"]

SPECS = pathlib.Path(__file__).with_name("selection")

#: Overlay colours of painted categories 1, 2, 3, ... (half transparent).
MASK_COLOURS = [(255, 64, 64, 140), (64, 160, 255, 140), (64, 200, 64, 140),
                (255, 200, 0, 140), (200, 64, 255, 140), (0, 220, 220, 140)]

TABLE_MENU = ("Select All", "Clear", "Delete")
CANVAS_MENU = ("Copy 2D Histogram (CSV)", "Copy 1D Histograms (CSV)", "Send to Napari",
               "Fit gate to the population here")
SEND = "Send selection to"


#: Outline of a 2-D Gaussian gate on the map.
GATE_OUTLINE = (255, 255, 255, 230)


def ellipse_outline(mu, cov, sigma: float, log_x: bool = False, log_y: bool = False,
                    n: int = 96) -> tuple:
    """The ``sigma`` contour of a 2-D Gaussian, in data units: ``(xs, ys)`` lists.

    *mu* and *cov* are in gate space (the natural log of a log axis, as
    :class:`~ndxplorer.core.data_source.Gaussian2DSelection` measures).
    """
    values, vectors = np.linalg.eigh(np.asarray(cov, dtype=float))
    radii = sigma * np.sqrt(np.clip(values, 0.0, None))
    t = np.linspace(0.0, 2.0 * np.pi, n)
    circle = np.stack([np.cos(t) * radii[0], np.sin(t) * radii[1]])
    points = vectors @ circle + np.asarray(mu, dtype=float).reshape(2, 1)
    xs = np.exp(points[0]) if log_x else points[0]
    ys = np.exp(points[1]) if log_y else points[1]
    return xs.tolist(), ys.tolist()


def in_browser() -> bool:
    """Whether the app runs in a page (Pyodide)."""
    return sys.platform == "emscripten"


def _load_spec(name: str) -> dict:
    with open(SPECS / f"{name}.view.json", encoding="utf-8") as handle:
        return json.load(handle)


class DrawMaskModel:
    """What the Draw Mask panel's spec binds to."""

    def __init__(self, feature: "SelectionFeature") -> None:
        self.feature = feature
        self.drawing = False
        self.mode = "draw"
        self.category = 1
        self.brush = 5

    def enabled(self, name: str) -> bool:
        model = self.feature.app.model
        if not model.has_data or model.histograms is None:
            return False
        if name in ("save_mask", "clear_mask", "apply_mask"):
            return bool(self.feature.canvas.categories())
        return True

    def clear_mask(self) -> None:
        self.feature.canvas.clear()

    def load_mask(self) -> None:
        self.feature.open_mask_dialog("open")

    def save_mask(self) -> None:
        self.feature.open_mask_dialog("save")

    def _draw_gaussian_gates(self) -> None:
        """Outline every enabled 2-D Gaussian gate on the map's own axes."""
        from emtk import implot

        model = self.app.model
        ix, iy = model.index_of(model.x.name), model.index_of(model.y.name)
        for n, gate in enumerate(model.gates):
            meta = gate.meta if gate.kind == "G2D" else None
            if not meta or not gate.enabled:
                continue
            if (int(meta["idx1"]), int(meta["idx2"])) != (ix, iy):
                continue
            xs, ys = ellipse_outline(meta["mu"], meta["cov"], float(meta.get("sigma", 1.0)),
                                     bool(meta.get("log_x")), bool(meta.get("log_y")))
            implot.plot_line(f"##g2d-{n}", xs, ys,
                             spec={"line_color": GATE_OUTLINE, "line_weight": 2.0})

    def apply_mask(self) -> None:
        self.feature.apply_mask()


class SelectionFeature(Feature):
    """Gate menus, population picking and mask painting (see the module)."""

    name = "selection"

    def __init__(self, app) -> None:
        super().__init__(app)
        from emtk.view_form import FormState

        from ...core.mask_paint import MaskCanvas

        self.canvas = MaskCanvas()
        self.mask_model = DrawMaskModel(self)
        self.mask_spec = _load_spec("draw_mask")
        self.mask_form = FormState()
        self._stroke_last: Optional[tuple] = None
        self._fitted_once = False
        self._overlay = None
        self._overlay_key = None
        #: Menu choices wait here for the next frame: they need a running frame
        #: (the clipboard, the implot state) and a recompute.
        self._pending: List[Callable[[], None]] = []
        #: ``(FileDialog, mode)`` of an open Load/Save Mask dialog.
        self.dialog = None
        self.dialog_box = None
        #: ``(x, y)`` in data units of the last right-click on the map.
        self.pick_seed: Optional[tuple] = None
        #: Set by a capture step: choose this menu row as soon as a menu opens.
        self.auto_choice: Optional[str] = None
        #: The menu this feature has open: ``"table"`` or ``"canvas"``.
        self.menu_open: Optional[str] = None
        #: The gate table's screen box in the last frame, ``None`` when folded.
        self.table_rect: Optional[tuple] = None

    # ------------------------------------------------------------- status
    def status(self, text: str) -> None:
        """Say *text* on the window's status line."""
        self.app.show_status(text)

    # ------------------------------------------------------------- hooks
    def custom_sections(self) -> Dict[str, Callable]:
        return {"draw_mask": self._draw_mask_panel}

    def on_data_changed(self) -> None:
        self.canvas = type(self.canvas)()
        self._overlay_key = None

    def _draw_mask_panel(self, section, model, state, width: float) -> None:
        from emtk.view_form import draw_sections

        draw_sections(self.mask_spec["sections"], self.mask_model, self.mask_form)

    # ----------------------------------------------------- the 2-D canvas
    def _fit_canvas(self) -> bool:
        model = self.app.model
        hist = model.histograms
        if hist is None:
            return False
        fresh = self.canvas.fit(hist.x_edges, hist.y_edges, (model.x.name, model.y.name))
        if fresh and self._fitted_once and self.mask_model.drawing:
            # New bins or axes: the mask is gone, and drawing stops (as in Qt).
            self.mask_model.drawing = False
            self._stroke_last = None
            self.status("The map changed: the painted mask was cleared and drawing stopped.")
            return False
        self._fitted_once = True
        return True

    def plot_input(self, plot: str) -> bool:
        if plot != "map":
            return False
        import emtk
        from emtk import implot

        io = emtk.get_io()
        hovered = implot.is_plot_hovered()
        if hovered and io.mouse_clicked[1]:
            point = implot.get_plot_mouse_pos()
            self.pick_seed = (float(point.x), float(point.y))
            self.open_canvas_menu(*io.mouse_pos)
            return True
        if not self.mask_model.drawing or not self._fit_canvas():
            self._stroke_last = None
            return False
        point = implot.get_plot_mouse_pos()
        here = (float(point.x), float(point.y))
        width, height = implot.get_plot_size()
        ny, nx = self.canvas.shape
        px_per_bin = (max(width, 1.0) / max(nx, 1), max(height, 1.0) / max(ny, 1))
        erase = self.mask_model.mode == "erase"
        category = max(1, int(self.mask_model.category))
        if hovered and io.mouse_clicked[0]:
            self._stroke_last = here
            self.canvas.dab(here[0], here[1], self.mask_model.brush, px_per_bin, category, erase)
        elif self._stroke_last is not None and io.mouse_down[0]:
            self.canvas.stroke(self._stroke_last, here, self.mask_model.brush, px_per_bin,
                               category, erase)
            self._stroke_last = here
        active = self._stroke_last is not None
        if not io.mouse_down[0]:
            self._stroke_last = None
        return hovered or active

    def draw_plot(self, plot: str) -> None:
        if plot != "map":
            return
        self._draw_gaussian_gates()
        if self.canvas.mask is None or not self.canvas.categories():
            return
        if self.canvas.key != (self.app.model.x.name, self.app.model.y.name):
            return
        from emtk import implot
        from emtk.texture import Texture

        key = (self.canvas.revision, self.canvas.key)
        if key != self._overlay_key:
            rgba = np.flipud(self.canvas.rgba(MASK_COLOURS))
            ny, nx = self.canvas.shape
            self._overlay = Texture(nx, ny, np.ascontiguousarray(rgba).tobytes(),
                                    filter="nearest")
            self._overlay_key = key
        xe, ye = self.canvas.x_edges, self.canvas.y_edges
        implot.plot_image("##painted-mask", self._overlay, (float(xe[0]), float(ye[0])),
                          (float(xe[-1]), float(ye[-1])))

    def _draw_gaussian_gates(self) -> None:
        """Outline every enabled 2-D Gaussian gate on the map's own axes."""
        from emtk import implot

        model = self.app.model
        ix, iy = model.index_of(model.x.name), model.index_of(model.y.name)
        for n, gate in enumerate(model.gates):
            meta = gate.meta if gate.kind == "G2D" else None
            if not meta or not gate.enabled:
                continue
            if (int(meta["idx1"]), int(meta["idx2"])) != (ix, iy):
                continue
            xs, ys = ellipse_outline(meta["mu"], meta["cov"], float(meta.get("sigma", 1.0)),
                                     bool(meta.get("log_x")), bool(meta.get("log_y")))
            implot.plot_line(f"##g2d-{n}", xs, ys,
                             spec={"line_color": GATE_OUTLINE, "line_weight": 2.0})

    def apply_mask(self) -> None:
        """Apply: the painted category becomes a mask gate."""
        model = self.app.model
        category = max(1, int(self.mask_model.category))
        count = model.gates.count("Mask") + 1
        name = f"Bitmap {count} ({model.x.name}, {model.y.name})"
        selection, reason = self.canvas.selection(model.index_of(model.x.name),
                                                  model.index_of(model.y.name), category, name)
        if selection is None:
            self.status(reason)
            return
        model.gates.add_selection(selection)
        model.invalidate()
        self.status(f"Mask gate added: category {category}, "
                    f"{int(selection.mask.sum())} bins")

    # --------------------------------------------------- Load / Save Mask
    def open_mask_dialog(self, mode: str) -> None:
        from emtk.file_dialog import FileDialog

        start = self.app.model.working_path or str(pathlib.Path.home())
        title = "Load Mask" if mode == "open" else "Save Mask"
        self.dialog = (FileDialog(title, mode=mode, filters=[("TIFF files", ["*.tif", "*.tiff"])],
                                  directory=start, filename="mask.tif"), mode)

    def _draw_dialog(self) -> bool:
        import emtk

        dialog, mode = self.dialog
        x, y, w, h = self.app.box
        dw, dh = min(720.0, w - 40.0), min(460.0, h - 60.0)
        box = (x + (w - dw) / 2.0, y + (h - dh) / 2.0, dw, dh)
        self.dialog_box = box
        emtk.begin(f"{dialog.title}##mask-dialog", box)
        emtk.text(dialog.title)
        emtk.separator()
        result = dialog.draw()
        emtk.end()
        if result is False:
            self.dialog = None
        elif result:
            self.dialog = None
            path = str(result[0] if isinstance(result, (list, tuple)) else result)
            try:
                if mode == "open":
                    self._fit_canvas()
                    reason = self.canvas.load(path)
                    self.status(reason or f"Mask loaded from {path}")
                else:
                    self.canvas.save(path)
                    self.status(f"Mask saved to {path}")
            except Exception as exc:  # noqa: BLE001 - reported, not raised
                self.status(f"Mask file failed: {exc}")
        return self.dialog is not None

    # --------------------------------------------------------- the menus
    def _send_menu(self):
        """The "Send selection to ▸" submenu: ChiSurf's analyses, or why not."""
        from emtk.widgets.menus import Menu, MenuItem

        reason, targets = self.send_state()
        items = [MenuItem(t.title, enabled=reason is None) for t in targets]
        for item, target in zip(items, targets):
            item.action = ("send", target.key)
        label = SEND if reason is None else f"{SEND} — {reason.split('.')[0]}"
        menu = Menu(label, items, enabled=reason is None)
        menu.reason = reason
        return menu

    def send_state(self):
        """``(reason or None, targets)`` for the send submenu."""
        if in_browser():
            return ("Not in the browser. ChiSurf's RPC needs a native socket; run ndX on "
                    "the desktop to send a selection"), []
        from ...analysis.burst_bridge import BurstAnalysisBridge, unavailable_reason

        model = self.app.model
        rpc = getattr(self.app, "chisurf_rpc", None)
        bridge = BurstAnalysisBridge(rpc, model.source) if rpc is not None else None
        reason = unavailable_reason(rpc, model.source if model.has_data else None,
                                    model.gates.selections(), bridge)
        targets = list(bridge.discover().values()) if bridge is not None else []
        return reason, targets

    def napari_reason(self) -> Optional[str]:
        """Why Send to Napari cannot run here, or ``None``."""
        if in_browser():
            return "not in the browser"
        import importlib.util

        if importlib.util.find_spec("napari") is None:
            return "napari is not installed"
        if self.app.model.histograms is None:
            return "no histogram"
        return None

    def _open(self, kind: str, entries, x: float, y: float) -> None:
        open_menu = getattr(self.app, "open_menu", None)
        if not callable(open_menu):
            self.status("This window cannot show context menus yet.")
            return
        self.menu_open = kind
        open_menu(entries, x, y, self._chosen)

    def open_table_menu(self, x: float, y: float) -> None:
        from emtk.widgets.menus import MenuItem

        has_rows = len(self.app.model.gates) > 0
        entries = [MenuItem(label, enabled=has_rows) for label in TABLE_MENU]
        for item in entries:
            item.action = ("table", item.label)
        self._open("table", entries + [None, self._send_menu()], x, y)

    def open_canvas_menu(self, x: float, y: float) -> None:
        from emtk.widgets.menus import MenuItem

        has_map = self.app.model.histograms is not None
        entries = []
        for label in CANVAS_MENU:
            enabled, text = has_map, label
            if label == "Send to Napari":
                reason = self.napari_reason()
                enabled = reason is None
                text = label if reason is None else f"{label} — {reason}"
            item = MenuItem(text, enabled=enabled)
            item.action = ("canvas", label)
            entries.append(item)
        entries = entries[:3] + [None, entries[3], None, self._send_menu()]
        self._open("canvas", entries, x, y)

    def _chosen(self, item) -> None:
        self.menu_open = None
        action = getattr(item, "action", None)
        if action is not None:
            self._pending.append(lambda: self.run(action))

    def run(self, action: tuple) -> None:
        """Do a menu row's action: ``("table"|"canvas"|"send", name)``."""
        kind, name = action
        if kind == "send":
            self.send(name)
        elif name == "Select All":
            control = self._table_control()
            if control is not None:
                control.select_all()
        elif name == "Clear":
            self.app.model.clear_gates()
        elif name == "Delete":
            self.delete_selected_rows()
        elif name == "Copy 2D Histogram (CSV)":
            self.copy_2d()
        elif name == "Copy 1D Histograms (CSV)":
            self.copy_1d()
        elif name == "Send to Napari":
            self.send_to_napari()
        elif name == "Fit gate to the population here":
            if self.pick_seed is not None:
                self.pick_population_at(*self.pick_seed)

    # ------------------------------------------------------ table actions
    def _table_control(self):
        binding = self.app.forms["plot_controls"].tables.get("gate_rows")
        return None if binding is None else binding.control

    def delete_selected_rows(self) -> None:
        """Delete: every row Select All marked, else the selected row."""
        control = self._table_control()
        model = self.app.model
        indices = control.selected_indices() if control is not None else []
        if not indices and model.selected_gate is not None:
            indices = [model.selected_gate]
        if not indices:
            self.status("No row selected.")
            return
        # The table's rows are keyed by position, so its selection is.
        rows = [int(control.value(i, "row")) if control is not None else i for i in indices]
        model.gates.remove(rows)
        model.selected_gate = None
        if control is not None:
            control.selected_key = None
            control.also_selected = set()
        model.invalidate()

    # ----------------------------------------------------- canvas actions
    def copy_2d(self) -> None:
        from emtk import clipboard

        from ...utils.histogram_export import histogram_2d_text

        hist = self.app.model.histograms
        text = histogram_2d_text(hist.H, hist.x_edges, hist.y_edges)
        ok = clipboard.copy(text)
        self.status("2-D histogram copied to the clipboard (tab separated)." if ok else
                    "No clipboard to copy to here.")

    def copy_1d(self) -> None:
        from emtk import clipboard

        from ...utils.histogram_export import histograms_1d_text

        hist = self.app.model.histograms
        ok = clipboard.copy(histograms_1d_text(hist.x, hist.y))
        self.status("1-D histograms copied to the clipboard (tab separated)." if ok else
                    "No clipboard to copy to here.")

    def send_to_napari(self) -> None:
        """Open the 2-D histogram in napari, in its own process.

        napari runs its own Qt event loop, which cannot share this window's
        loop, so it gets a process of its own and the histogram through a
        temporary ``.npy``.
        """
        reason = self.napari_reason()
        if reason:
            self.status(f"Send to Napari: {reason}.")
            return
        model = self.app.model
        handle, path = tempfile.mkstemp(suffix=".npy", prefix="ndx-hist-")
        os.close(handle)
        np.save(path, np.flipud(model.histograms.H))
        name = f"ndX: {model.x.name} vs {model.y.name}"
        code = ("import sys, numpy, napari; "
                "napari.view_image(numpy.load(sys.argv[1]), name=sys.argv[2], "
                "colormap='viridis'); napari.run()")
        subprocess.Popen([sys.executable, "-c", code, path, name])  # noqa: S603
        self.status(f"Opening {name} in napari...")

    def pick_population_at(self, x: float, y: float, name: str = "") -> str:
        """Fit a 2-D Gaussian gate to the population at ``(x, y)`` (data units).

        Returns ``""`` on success, or why the pick was refused (also shown on
        the status line).
        """
        from ...core.population_pick import fit_population

        model = self.app.model
        hist = model.histograms
        if hist is None:
            self.status("No gate: no data on the plot.")
            return "no data"
        ix, iy = model.index_of(model.x.name), model.index_of(model.y.name)
        fit = fit_population(model._visible_values(ix), model._visible_values(iy), (x, y),
                             (hist.x_edges[0], hist.x_edges[-1]),
                             (hist.y_edges[0], hist.y_edges[-1]),
                             log_x=model.x.log, log_y=model.y.log)
        if not fit.success:
            self.status(f"No gate: {fit.reason}")
            return fit.reason
        count = model.gates.count("G2D") + 1
        model.gates.add_gaussian(ix, iy, fit.mu, fit.cov, sigma=2.0,
                                 name=name or f"Population {count}",
                                 log_x=fit.log_x, log_y=fit.log_y)
        model.invalidate()
        self.status(f"Gate fitted to the population at ({x:.4g}, {y:.4g}): "
                    f"{fit.n_points} points")
        return ""

    def send(self, target: str) -> None:
        """Send the gated bursts to ChiSurf analysis *target*."""
        from ...analysis.burst_bridge import (
            BurstAnalysisBridge,
            BurstBridgeError,
            outcome_message,
        )

        reason, _targets = self.send_state()
        if reason:
            self.status(reason)
            return
        model = self.app.model
        bridge = BurstAnalysisBridge(getattr(self.app, "chisurf_rpc", None), model.source)
        try:
            reply = bridge.send(target, model.gates.selections())
        except (BurstBridgeError, Exception) as exc:  # noqa: BLE001 - reported
            self.status(f"Could not send to {target}: {exc}")
            return
        self.status(outcome_message(reply, target))

    # ------------------------------------------------------------ frames
    def draw_windows(self) -> bool:
        import emtk

        io = emtk.get_io()
        form = self.app.forms["plot_controls"]
        # Popped, so a folded Selection panel leaves no stale box behind.
        rect = self.table_rect = form.rects.pop("gate_rows", None)
        if rect is not None and io.mouse_clicked[1] and self.dialog is None:
            x, y, w, h = rect
            mx, my = io.mouse_pos
            if x <= mx <= x + w and y <= my <= y + h:
                self.open_table_menu(mx, my)
        pending, self._pending = self._pending, []
        for action in pending:
            action()
        if self.dialog is not None:
            return self._draw_dialog()
        return False

    # ----------------------------------------------------------- capture
    def capture_ops(self) -> Dict[str, Callable]:
        from . import selection_capture

        return selection_capture.ops(self)

    def capture_targets(self) -> Dict[str, Callable]:
        from . import selection_capture

        return selection_capture.targets(self)


def create(app) -> SelectionFeature:
    return SelectionFeature(app)
