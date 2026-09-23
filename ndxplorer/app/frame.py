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
the features' tabs beside it; on the right the *Plot* dock -- the working-path
row, the x marginal over the 2-D histogram, the y marginal beside it and the
display controls in the corner; the status line along the bottom. Every dock
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

#: Heights of the fixed parts, in logical pixels: the menu bar and the status line.
MENU_H = 24.0
STATUS_H = 22.0


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
        #: Height the display corner's controls took last frame.
        self._corner_h = 0.0
        self._corner_due = False
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
        #: One line of non-modal feedback under the plots (Qt's status bar);
        #: set it with :meth:`show_status`.
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
            self.docks.draw((x, y + MENU_H, w, max(h - MENU_H - STATUS_H, 1.0)))
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
                           or self._corner_due)
        self._corner_due = False

    def _draw_chrome(self, painter, x, y, w, h) -> None:
        """The status line and the menu bar, drawn with the painter."""
        if self.status:
            from emtk import style
            from emtk.painter import ALIGN_LEFT, ALIGN_VCENTER

            painter.text(x + 4.0, y + h - STATUS_H, w - 8.0, STATUS_H,
                         ALIGN_LEFT | ALIGN_VCENTER, self.status, style.TEXT)
        self._menu_box = (x, y, w, MENU_H)
        self.menubar.set_viewport(x + w, y + h)
        self.menubar.draw(painter, *self._menu_box)

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
        """The Plot window: the path row, the display corner and the plots."""
        import emtk
        from emtk.view_form import draw_form

        from .docks import plot_boxes

        boxes = self.plot_boxes = plot_boxes(box, self._corner_h)
        for name, key in (("plot_header", "header"), ("plot_corner", "corner")):
            emtk.begin_child(boxes[key])
            draw_form(self.specs[name], self.panel, self.forms[name], titles=False)
            emtk.end_child()
        # The corner's controls wrap in a narrow window; the next frame gives
        # them the height they took (plot_boxes), and one is asked for now.
        rects = self.forms["plot_corner"].rects.values()
        top = boxes["corner"][1]
        need = max((r[1] + r[3] - top for r in rects), default=0.0) + 4.0
        if abs(need - self._corner_h) > 0.5:
            # a frame is due only when the layout it gives differs
            self._corner_due = plot_boxes(box, need) != boxes
            self._corner_h = need
        self.plots.draw(boxes)

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
        """Say *text* in the status line under the plots, until the next one.

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
