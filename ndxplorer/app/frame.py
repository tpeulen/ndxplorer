"""The ndXplorer window, as one emtk control.

:class:`NdxApp` draws the whole window through whatever painter it is handed
and takes input through the control contract every emtk host speaks
(``press``/``drag``/``release``/``hover``/``scroll``/``key``, and the richer
``pointer_*``/``wheel`` hooks :class:`emtk.app.ControlSurface` prefers). It
imports no toolkit: the same object runs in a native window
(:mod:`emtk.native`), a Tk window (:mod:`emtk.tk_host`), a browser page
(:mod:`emtk.web`) and a headless capture (:mod:`ndxplorer.app.capture`).

The layout starts as the Qt window's: the menu bar; on the left the *Plot
controls* dock (its panels a ``view.json`` drawn by :mod:`emtk.view_form`) with
the features' tabs beside it; on the right the *Plot* dock -- a toolbar (the
working path, the colours, the point counts and the actions), the x marginal
over the 2-D histogram and the y marginal beside it; the status line in the
menu bar's row. Every dock
is a sticky window (:mod:`.docks`, :mod:`emtk.docking`): the user can float
it, snap it, drop it back into a region, close it and reopen it from View.

What is hand-drawn is what a spec cannot say: the plots (:mod:`.plots`) and
the menu bar's placement.
"""

from __future__ import annotations

import json
import pathlib
from typing import Any, Callable, Dict, Optional

from . import plots, theme
from .menus import build_menu_bar, refresh as refresh_menus
from .model import ExplorerModel
from .view_model import PanelModel

__all__ = ["NdxApp", "make_app", "load_spec"]

VIEWS = pathlib.Path(__file__).with_name("views")

#: Height of the menu bar, in logical pixels. The status line shares its row,
#: right of the menus, so it costs the plots no height.
MENU_H = 24.0
#: Space between the last menu title and the status text.
STATUS_GAP = 24.0


#: The narrowest corner that holds its controls (two buttons side by side),
#: and how far they keep from its left edge.
CORNER_MIN_W = 110.0
CORNER_INSET = 4.0


def _toolbar_with_corner(header: dict, corner: dict) -> dict:
    """The toolbar spec with the corner's controls appended, each group
    starting a piece of its own where the line may wrap."""
    import copy

    spec = copy.deepcopy(header)
    row = spec["sections"][0]
    extra = []
    for section in copy.deepcopy(corner["sections"]):
        items = section.get("sections") if section.get("type") == "row" else [section]
        for i, item in enumerate(items):
            if i == 0:
                item["wrap_before"] = True
            extra.append(item)
    row["sections"] = list(row["sections"]) + extra
    row["n_col"] = len(row["sections"])
    return spec


def load_spec(name: str) -> dict:
    """One of the app's view specs, parsed."""
    with open(VIEWS / f"{name}.view.json", encoding="utf-8") as handle:
        return json.load(handle)


class NdxApp:
    """The ndXplorer window: menus, the plot-control dock and the plots.

    Parameters
    ----------
    model : ExplorerModel, optional
        The state to show; a fresh one reading the default settings otherwise.
    settings_file : str, optional
        Passed to a fresh model.
    on_exit : callable, optional
        What File > Exit does; the host's window close.
    features : list of str, optional
        The feature modules to load; all of :data:`~ndxplorer.app.features.FEATURES`
        by default, ``[]`` for the core alone (its tests).
    layout_store : emtk.docking.LayoutStore, optional
        Where the window layout is read from and saved to
        (:func:`.docks.layout_store`, the settings folder). ``None`` keeps it
        for this run only -- what tests want, so they never touch the user's.
    """

    def __init__(self, model: Optional[ExplorerModel] = None, settings_file=None,
                 on_exit: Optional[Callable[[], None]] = None,
                 features: Optional[list] = None, layout_store=None) -> None:
        import emtk
        from emtk.view_form import FormState

        self.model = model if model is not None else ExplorerModel(settings_file)
        self.on_exit = on_exit
        self.panel = PanelModel(self.model, actions={
            "exit": self.exit,
            "toggle_plot_controls": self.toggle_plot_controls,
            "toggle_plot": self.toggle_plot,
            "reset_layout": self.reset_layout,
        })
        self.io = emtk.IO()
        self.storage: Dict[Any, Any] = {}
        self.specs = {name: load_spec(name) for name in ("plot_controls", "plot_header",
                                                       "plot_corner")}
        #: The toolbar with the corner's controls at its end: drawn when the
        #: marginals are too small to hold the corner.
        self.specs["plot_toolbar_full"] = _toolbar_with_corner(self.specs["plot_header"],
                                                               self.specs["plot_corner"])
        self.forms = {name: FormState() for name in self.specs}
        self.forms["plot_controls"].custom["z_plot"] = self._draw_z_plot
        self.plots = plots.PlotArea(self.model)
        self.model.app = self
        from . import docks

        #: The docks, every one a window (:mod:`.docks`): features add theirs below.
        self.docks = docks.build(self, layout_store)
        for name, title in (("show_plot_controls", docks.PLOT_CONTROLS),
                            ("show_plot", docks.PLOT)):
            self.panel.fields[name] = self._visibility_field(title)
        #: The Plot window's parts, as last drawn (:func:`.docks.plot_boxes`).
        self.plot_boxes: Dict[str, tuple] = {}
        #: Height the toolbar took last frame, and ``(width, height)``: the
        #: height the corner's controls took when last drawn at that width.
        self._header_h = 0.0
        self._corner_need = (0.0, 0.0)
        #: Whether the corner's controls are on the toolbar (marginals too small).
        self.corner_in_toolbar = False
        #: Marginal sizes while a bar between a marginal and the map is dragged.
        self._marginal_drag: Dict[str, float] = {}
        self._layout_due = False
        from .features import load_features

        #: The feature modules (:mod:`ndxplorer.app.features`), created for this window.
        self.features = load_features(self, features)
        for feature in self.features:
            self.panel.actions.update(feature.actions())
            self.panel.fields.update(feature.fields())
            for form in self.forms.values():
                form.custom.update(feature.custom_sections())
        docks.add_feature_windows(self)
        self.panel.availability = self._feature_available
        self.menubar = build_menu_bar(self.panel.available, self._checked,
                                      extra=self._feature_menu_entries())
        self._menu_box = (0.0, 0.0, 1.0, MENU_H)
        self.popup = None
        self.box = (0.0, 0.0, 1.0, 1.0)
        self.frames = 0
        #: ``(title, text)`` of a message box on screen, or ``None``.
        self.message = None
        #: The ChiSurf RPC client (``--chisurf-rpc``), or ``None``: what "Send
        #: selection to" and the phasor features talk to.
        self.chisurf_rpc = None
        #: One line of non-modal feedback (Qt's status bar), in the menu bar's
        #: row; set it with :meth:`show_status`.
        self.status = ""

    # ------------------------------------------------------------ features
    def _feature_available(self, action: str):
        """What the feature that owns *action* says about it, or ``None``."""
        for feature in self.features:
            answer = feature.available(action)
            if answer is not None:
                return bool(answer)
        return None

    def _feature_menu_entries(self) -> list:
        return [entry for feature in self.features for entry in feature.menu_entries()]

    def _visibility_field(self, title: str) -> tuple:
        """A ``(getter, setter)`` field for whether the window *title* is shown."""
        def set_(value) -> None:
            if value:
                self.docks.focus(title)
            else:
                self.docks.hide(title)

        return (lambda: self.docks.is_visible(title), set_)

    def data_changed(self) -> None:
        """Tell the features the table was replaced or merged."""
        for feature in self.features:
            try:
                feature.on_data_changed()
            except Exception:  # noqa: BLE001 - logged, the window goes on
                import logging

                logging.getLogger(__name__).exception("%s.on_data_changed", feature.name)

    # ------------------------------------------------------------- actions
    def _checked(self, attr: str) -> bool:
        return bool(getattr(self.panel, attr, False))

    def open_path(self, path: str) -> bool:
        """Open a file or folder, as ``--file`` and a drop do.

        A file that cannot be read says why in a message box ("Data Load
        Error", as the Qt window's), and the data on screen stays.
        """
        ok = self.model.open(path)
        if not ok:
            self.message = ("Data Load Error", self.model.error)
        else:
            self.data_changed()
        return ok

    def toggle_plot_controls(self) -> None:
        """View > Plot controls: show the window (on top), or put it away."""
        from .docks import PLOT_CONTROLS

        self.docks.toggle(PLOT_CONTROLS)

    def toggle_plot(self) -> None:
        """View > Plot: show the plot window (on top), or put it away."""
        from .docks import PLOT

        self.docks.toggle(PLOT)

    def reset_layout(self) -> None:
        """View > Reset window layout: every window back where it started."""
        self.docks.reset()

    def exit(self) -> None:
        if self.on_exit is not None:
            self.on_exit()

    def close(self) -> None:
        """Release what the window holds (nothing global since it draws in the
        default style); kept for hosts, which call it when the window closes."""

    # ------------------------------------------------------------- drawing
    def draw(self, painter, x: float, y: float, w: float, h: float) -> None:
        """Draw one frame of the window into *painter*."""
        import emtk

        self.box = (x, y, w, h)
        self.model.update()
        refresh_menus(self.menubar, self.panel.available, self._checked)
        painter.fill_rect(x, y, w, h, theme.WINDOW_BG)
        self.plots.begin_frame()
        with emtk.frame(painter, (x, y, w, h), io=self.io, storage=self.storage) as ctx:
            emtk.begin("##ndx", (x, y + MENU_H, w, h - MENU_H))
            modal = self.message is not None or getattr(self, "_feature_modal", False)
            if modal:
                emtk.begin_disabled(True)
            self.docks.draw((x, y + MENU_H, w, max(h - MENU_H, 1.0)))
            if modal:
                emtk.end_disabled()
            emtk.end()
            self._feature_modal = False
            for feature in self.features:
                if feature.draw_windows():
                    self._feature_modal = True
            if self.message is not None:
                self._draw_message(x, y, w, h)
            # Inside the frame, so what emtk draws over it at the frame's end
            # -- a choice's list, a context menu -- lies over these too.
            self._draw_chrome(painter, x, y, w, h)
            self._keep_menu()
        self._spend_edges()
        self.frames += 1
        # A frame can change what it shows: a rectangle released on the map
        # becomes gates, and this frame drew the histograms from before them.
        # A host draws on demand, so without asking it the window would show
        # the old counts until the pointer next moved.
        self._frame_due = (bool(getattr(ctx, "frame_requested", False)) or self.model.stale
                           or self._layout_due)
        self._layout_due = False

    def _draw_chrome(self, painter, x, y, w, h) -> None:
        """The menu bar, and the status line in its row right of the menus."""
        self._menu_box = (x, y, w, MENU_H)
        self.menubar.set_viewport(x + w, y + h)
        self.menubar.draw(painter, *self._menu_box)
        if self.status:
            self._draw_status(painter, x, y, w)

    def _draw_status(self, painter, x, y, w) -> None:
        """The status text, right-aligned in the menu bar's row; a text too
        long for the room right of the menus shows its end after a "…"."""
        from emtk import style
        from emtk.painter import ALIGN_LEFT, ALIGN_VCENTER

        menus_w = sum(self.menubar.title_width(painter, menu) for menu in self.menubar.menus)
        left = x + menus_w + STATUS_GAP
        room = x + w - 6.0 - left
        if room < 20.0:
            return
        text = self.status
        if painter.text_width(text) > room:
            while text and painter.text_width("…" + text) > room:
                text = text[1:]
            text = "…" + text
        tw = painter.text_width(text)
        painter.text(x + w - 6.0 - tw, y, tw + 1.0, MENU_H, ALIGN_LEFT | ALIGN_VCENTER, text,
                     style.TEXT)

    def _keep_menu(self) -> None:
        """Keep the context menu (:meth:`open_menu`) up; what it picks runs
        at the end of the frame the click landed in."""
        if self.popup is not None and not self.popup[0].open:
            self.popup = None
        if self.popup is None:
            return
        from emtk import overlays

        popup, on_choose = self.popup
        overlays.popup("ndx.menu", popup, on_pick=on_choose)

    def _spend_edges(self) -> None:
        """One-frame input edges are used up by the frame that saw them."""
        io = self.io
        for i in range(3):
            io.mouse_clicked[i] = False
            io.mouse_released[i] = False
            io.mouse_double_clicked[i] = False
        io.mouse_wheel = 0.0
        io.key, io.text = 0, ""

    def _draw_plot_controls(self, _box) -> None:
        """The Plot controls window: the ``plot_controls`` spec."""
        from emtk.view_form import draw_form

        draw_form(self.specs["plot_controls"], self.panel, self.forms["plot_controls"],
                  titles=False)

    def _draw_plot(self, box) -> None:
        """The Plot window: the toolbar, the corner between the marginals, the
        plots and the bars that resize the marginals.

        The corner holds the counts, the inf/NaN masks and the window's
        actions. When the user drags the marginals too small for them, they
        go to the end of the toolbar instead (:attr:`corner_in_toolbar`).
        """
        import emtk
        from emtk.view_form import draw_form

        from .docks import XMARGINAL_KEY, YMARGINAL_KEY, plot_boxes

        docks = self.docks
        sizes = {
            "xmarginal_h": self._marginal_drag.get("xmarginal_h",
                                                   docks.extra(XMARGINAL_KEY)),
            "ymarginal_w": self._marginal_drag.get("ymarginal_w",
                                                   docks.extra(YMARGINAL_KEY)),
        }
        row_h = max(emtk.get_frame_height(), self._header_h)
        boxes = self.plot_boxes = plot_boxes(box, row_h, **sizes)
        corner = boxes["corner"]
        # The height the controls took at this width, when they were drawn at
        # it; at another width they are tried again.
        at_w, need_h = self._corner_need
        in_toolbar = corner[2] < CORNER_MIN_W or (abs(at_w - corner[2]) < 1.0
                                                   and corner[3] < need_h)
        for form in (self.forms["plot_header"], self.forms["plot_corner"]):
            form.rects.clear()
        emtk.begin_child(boxes["header"])
        draw_form(self.specs["plot_toolbar_full" if in_toolbar else "plot_header"], self.panel,
                  self.forms["plot_header"], titles=False)
        emtk.end_child()
        if not in_toolbar:
            # inset: the x marginal's last tick label reaches past its edge
            emtk.begin_child((corner[0] + CORNER_INSET, corner[1],
                              corner[2] - CORNER_INSET, corner[3]))
            draw_form(self.specs["plot_corner"], self.panel, self.forms["plot_corner"],
                      titles=False)
            emtk.end_child()
            self._corner_need = (corner[2], self._form_height("plot_corner", corner[1]) + 2.0)
        # The toolbar wraps in a narrow window, and the corner's controls may
        # not fit the corner: the next frame gives them the room they took,
        # and one is asked for now.
        header_h = self._form_height("plot_header", boxes["header"][1])
        moved = in_toolbar != self.corner_in_toolbar or (
            not in_toolbar and self._corner_need[1] > corner[3] + 0.5)
        self.corner_in_toolbar = in_toolbar
        if abs(header_h - self._header_h) > 0.5 or moved:
            again = plot_boxes(box, max(emtk.get_frame_height(), header_h), **sizes)
            # a frame is due only when the layout it gives differs
            self._layout_due = again != boxes or moved
            self._header_h = header_h
        self._draw_marginal_bars(boxes)
        self.plots.draw(boxes)

    def control_rect(self, name: str):
        """Where the toolbar or corner control *name* was drawn last frame, or ``None``."""
        for form in ("plot_corner", "plot_header"):
            rect = self.forms[form].rects.get(name)
            if rect is not None:
                return rect
        return None

    def _form_height(self, name: str, top: float) -> float:
        """How far below *top* the form *name* drew its controls last frame."""
        rects = self.forms[name].rects.values()
        return max((r[1] + r[3] - top for r in rects), default=0.0)

    def _draw_marginal_bars(self, boxes: dict) -> None:
        """The bars between the marginals and the map: drag one to resize its
        marginal. The size is kept with the window layout when it is let go."""
        import emtk

        from .docks import SPLIT, XMARGINAL_KEY, YMARGINAL_KEY

        io = emtk.get_io()
        grid_top = boxes["xmarginal"][1]
        right = boxes["ymarginal"][0] + boxes["ymarginal"][2]
        draw = emtk.get_window_draw_list()
        dragging = False
        for key, size_key, bar in (("hsplit", "xmarginal_h", boxes["hsplit"]),
                                   ("vsplit", "ymarginal_w", boxes["vsplit"])):
            emtk.set_cursor_screen_pos((bar[0], bar[1]))
            emtk.invisible_button(f"##ndx.{key}", (max(bar[2], 1.0), max(bar[3], 1.0)))
            active = emtk.is_item_active()
            if key == "hsplit":
                emtk.set_item_tooltip("Drag to resize the x marginal.")
            else:
                emtk.set_item_tooltip("Drag to resize the y marginal.")
            if active:
                dragging = True
                mx, my = io.mouse_pos
                self._marginal_drag[size_key] = (my - grid_top - SPLIT / 2.0 if key == "hsplit"
                                                 else right - mx - SPLIT / 2.0)
            if active or emtk.is_item_hovered():
                colour = emtk.get_color_u32(emtk.Col.SEPARATOR_ACTIVE if active
                                            else emtk.Col.SEPARATOR_HOVERED)
                draw.add_rect_filled((bar[0], bar[1]), (bar[0] + bar[2], bar[1] + bar[3]), colour)
        if self._marginal_drag and not dragging:
            # let go: keep the sizes the layout gave (clamped) with the layout
            self.docks.set_extra(XMARGINAL_KEY, round(boxes["xmarginal"][3], 1))
            self.docks.set_extra(YMARGINAL_KEY, round(boxes["ymarginal"][2], 1))
            self._marginal_drag = {}
            self._layout_due = True

    def _draw_z_plot(self, section, model, state, width: float) -> None:
        height = float((section.get("options") or {}).get("height", 90))
        self.plots.draw_z(width, height)

    def _draw_message(self, x, y, w, h) -> None:
        """A message box: the title, the text, OK."""
        import emtk

        from emtk import style

        title, text = self.message
        dw, dh = min(520.0, w - 40.0), 150.0
        box = (x + (w - dw) / 2.0, y + (h - dh) / 2.0, dw, dh)
        self.message_box = box
        # Modal: the window behind is dimmed, the box itself is opaque.
        emtk.get_window_draw_list().add_rect_filled((x, y), (x + w, y + h), style.MODAL_DIM_BG)
        emtk.begin(f"{title}##message", box)
        emtk.text(title)
        emtk.separator()
        emtk.text_wrapped(text)
        emtk.set_cursor_screen_pos((box[0] + dw - 100.0, box[1] + dh - 32.0))
        if emtk.button("OK", (90.0, 0.0)):
            self.message = None
        emtk.end()

    # --------------------------------------------------------------- input
    def _box(self):
        return self.box

    def _press_overlays(self, px: float, py: float) -> bool:
        """The menu bar takes a press first: its menus hang over the window."""
        result = self.menubar.press(px, py, *self._menu_box)
        if result.item is not None:
            action = getattr(result.item, "action", "")
            self.menubar.close()
            self.run_action(action)
            return True
        return bool(result.consumed)

    def show_status(self, text: str) -> None:
        """Say *text* in the status line, until the next one.

        The line shares the menu bar's row, right of the menus.

        Non-modal feedback ("Copied 2-D histogram"); a box the user must
        dismiss is :attr:`message`.
        """
        self.status = str(text or "")

    def open_menu(self, entries, x: float, y: float, on_choose, title: str = "") -> None:
        """A context menu at ``(x, y)``: *entries* are emtk menu entries
        (``MenuItem``, ``Menu`` for a submenu, ``None`` for a rule); choosing
        an item -- from a submenu too -- calls ``on_choose(item)``. A press
        anywhere else (either button) or Escape closes it. emtk draws it over
        the window (:func:`emtk.overlays.popup`): kept inside it, scrolled
        when it is taller, with the keyboard."""
        from emtk.widgets.menus import Popup

        popup = Popup(list(entries), title=title)
        popup.open_at(float(x), float(y))
        self.popup = (popup, on_choose)

    def run_action(self, action: str) -> bool:
        """Run a menu or button action by name; ``False`` when unavailable."""
        if not self.panel.available(action):
            return False
        fn = getattr(self.panel, action, None)
        if callable(fn):
            fn()
            return True
        return False

    def pointer_press(self, x, y, button, modifiers=0, clicks=1) -> None:
        from emtk.overlays import holding

        # While a list or context menu is up the press is the frame's: it
        # picks from it or closes it (emtk.overlays).
        if (button == 1 and not holding(self.storage)
                and self._press_overlays(float(x), float(y))):
            return
        index = {1: 0, 2: 1, 4: 2}.get(int(button), -1)
        io = self.io
        io.mouse_pos = (float(x), float(y))
        if index < 0:
            return
        io.mouse_down[index] = True
        io.mouse_clicked[index] = True
        io.mouse_double_clicked[index] = int(clicks) >= 2
        io.mouse_clicked_pos[index] = (float(x), float(y))

    def pointer_move(self, x, y, buttons=0, modifiers=0) -> None:
        self.io.mouse_pos = (float(x), float(y))

    def pointer_release(self, x, y, button, modifiers=0) -> None:
        index = {1: 0, 2: 1, 4: 2}.get(int(button), -1)
        self.io.mouse_pos = (float(x), float(y))
        if index >= 0 and self.io.mouse_down[index]:
            self.io.mouse_down[index] = False
            self.io.mouse_released[index] = True

    def wheel(self, x, y, steps, modifiers=0) -> None:
        self.io.mouse_pos = (float(x), float(y))
        self.io.mouse_wheel += float(steps)

    # The classic control contract (tk_host, qt_host): left button only.
    def press(self, px, py, *_box, **_kw) -> None:
        clicks = _box[5] if len(_box) > 5 else _kw.get("clicks", 1)
        self.pointer_press(px, py, 1, 0, clicks)

    def drag(self, px, py, *_box) -> None:
        self.pointer_move(px, py, 1)

    def hover(self, px, py, *_box) -> None:
        self.pointer_move(px, py, 0)

    def release(self, *_a, **_kw) -> None:
        self.pointer_release(*self.io.mouse_pos, 1)

    def scroll(self, rows: int) -> int:
        self.io.mouse_wheel += -float(rows) / 3.0
        return 0

    def shortcut_action(self, key: int, modifiers: int) -> Optional[str]:
        """The menu action whose shortcut (``"Ctrl+O"``) is *key* with *modifiers*.

        ``Ctrl`` is emtk's control modifier -- Command on macOS, as in Qt.
        """
        from emtk.events import ALT_MODIFIER, CONTROL_MODIFIER, SHIFT_MODIFIER

        from .menus import iter_entries, merged_menus

        wanted = int(modifiers) & (CONTROL_MODIFIER | SHIFT_MODIFIER | ALT_MODIFIER)
        for _path, entry in iter_entries(merged_menus(self._feature_menu_entries())):
            parts = [part.strip().lower() for part in entry.get("shortcut", "").split("+")]
            if not parts or not parts[-1]:
                continue
            mods = ((CONTROL_MODIFIER if "ctrl" in parts else 0)
                    | (SHIFT_MODIFIER if "shift" in parts else 0)
                    | (ALT_MODIFIER if "alt" in parts else 0))
            name = parts[-1]
            code = ord(name.upper()) if len(name) == 1 else None
            if mods and mods == wanted and code == int(key):
                return entry["action"]
        return None

    def key(self, key: int, text: str = "", modifiers: int = 0) -> bool:
        action = self.shortcut_action(key, modifiers) if modifiers else None
        if action is not None and self.run_action(action):
            return True
        self.io.key = int(key)
        # Appended: several keys can arrive before the frame that spends them
        # (a host draws on demand; a page's frame is slow) -- see _spend_edges.
        self.io.text += "".join(c for c in (text or "") if c >= " " and c != "\x7f")
        return True

    def files_dropped(self, paths) -> None:
        """A file or folder dropped on the window opens, as in the Qt window.

        A feature whose window takes drops (the report tool's folder list)
        answers first: ``files_dropped(paths)`` returning ``True`` keeps it.
        """
        if not paths:
            return
        for feature in self.features:
            hook = getattr(feature, "files_dropped", None)
            if callable(hook) and hook(list(paths)):
                return
        self.open_path(str(paths[0]))

    @property
    def window_title(self) -> str:
        """"ndX", plus the file name once data is loaded -- read by the host
        after each frame (:func:`emtk.app.window_title`), as the Qt window does."""
        from ..io.loading import window_title

        return window_title(self.model.path if self.model.has_data else [])

    def animating(self) -> bool:
        """Whether the host should keep drawing without input: a feature is
        playing back or streaming results -- or the last frame changed the data
        (or an emtk widget asked for a frame) and one more is due."""
        if getattr(self, "_frame_due", False):
            return True
        return any(feature.animating() for feature in self.features)


def make_app() -> NdxApp:
    """The factory :mod:`emtk.native` and :mod:`emtk.web` start (``ndxplorer.app.frame:make_app``).

    The window layout is remembered between runs (:func:`.docks.layout_store`).
    """
    from .docks import layout_store

    return NdxApp(layout_store=layout_store())
