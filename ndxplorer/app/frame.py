"""The ndXplorer window, as one emtk control.

:class:`NdxApp` draws the whole window through whatever painter it is handed
and takes input through the control contract every emtk host speaks
(``press``/``drag``/``release``/``hover``/``scroll``/``key``, and the richer
``pointer_*``/``wheel`` hooks :class:`emtk.app.ControlSurface` prefers). It
imports no toolkit: the same object runs in a native window
(:mod:`emtk.native`), a Tk window (:mod:`emtk.tk_host`), a browser page
(:mod:`emtk.web`) and a headless capture (:mod:`ndxplorer.app.capture`).

The layout is the Qt window's: the menu bar; on the left the *Plot controls*
dock (its panels a ``view.json`` drawn by :mod:`emtk.view_form`); on the right
the *Plot* dock -- the working-path row, the x marginal over the 2-D histogram,
the y marginal beside it and the display controls in the corner.

What is hand-drawn is what a spec cannot say: the plots (:mod:`.plots`), the
tab strips and the menu bar's placement.
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

#: Heights and widths of the fixed parts, in logical pixels (the Qt window's).
MENU_H = 24.0
TAB_H = 21.0
ROW_H = 26.0
CORNER_W = 258.0
LEFT_FRACTION = 0.357
LEFT_MIN = 360.0
XMARGINAL_FRACTION = 0.18
GAP = 4.0


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
    """

    def __init__(self, model: Optional[ExplorerModel] = None, settings_file=None,
                 on_exit: Optional[Callable[[], None]] = None,
                 features: Optional[list] = None) -> None:
        import emtk
        from emtk.view_form import FormState

        self.model = model if model is not None else ExplorerModel(settings_file)
        self.on_exit = on_exit
        self.panel = PanelModel(self.model, actions={
            "browse": self.browse,
            "open_text": self.open_text,
            "open_analysis_folder": self.open_analysis_folder,
            "open_analysis_file": self.open_analysis_file,
            "open_sampling": self.open_sampling,
            "exit": self.exit,
            "toggle_plot_controls": self.toggle_plot_controls,
        })
        self.io = emtk.IO()
        self.storage: Dict[Any, Any] = {}
        self.specs = {name: load_spec(name) for name in ("plot_controls", "plot_header",
                                                       "plot_corner")}
        self.forms = {name: FormState() for name in self.specs}
        self.forms["plot_controls"].custom["z_plot"] = self._draw_z_plot
        self.plots = plots.PlotArea(self.model)
        self.model.app = self
        from .features import load_features

        #: The feature modules (:mod:`ndxplorer.app.features`), created for this window.
        self.features = load_features(self, features)
        for feature in self.features:
            self.panel.actions.update(feature.actions())
            self.panel.fields.update(feature.fields())
            for form in self.forms.values():
                form.custom.update(feature.custom_sections())
        self.panel.availability = self._feature_available
        self.menubar = build_menu_bar(self.panel.available, self._checked,
                                      extra=self._feature_menu_entries())
        self._menu_box = (0.0, 0.0, 1.0, MENU_H)
        self.popup = None
        self.dialog = None
        self.left_tab = "Plot controls"
        self.right_tab = "Plot"
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

    def feature_tabs(self, dock: str) -> list:
        """``[(title, draw(box))]`` the features add to a dock."""
        return [(title, draw) for feature in self.features
                for side, title, draw in feature.tabs() if side == dock]

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

    def _open_dialog(self, title: str, mode: str, filters, purpose: str) -> None:
        from emtk.file_dialog import FileDialog

        start = self.model.working_path or str(pathlib.Path.home())
        self.dialog = (FileDialog(title, mode=mode, filters=filters, directory=start), purpose)

    def open_text(self) -> None:
        """File > Import > Import Text files."""
        self._open_dialog("Comma separated value files", "open",
                          [("Text files", ["*.csv", "*.dat", "*.er4", "*.txt", "*.bur"]),
                           ("All files", ["*"])], "open")

    def open_analysis_folder(self) -> None:
        """File > Import > Analysis-Folder: a burst-analysis folder."""
        self._open_dialog("Burst analysis folder", "folder", [("Folders", ["*"])], "open")

    def open_analysis_file(self) -> None:
        """File > Import > Analysis file: an MFD HDF5 (or a zip of one)."""
        self._open_dialog("MFD HDF5 files", "open",
                          [("HDF5 files", ["*.h5", "*.hdf5"]), ("ZIP files", ["*.zip"]),
                           ("All Files", ["*"])], "open")

    def open_sampling(self) -> None:
        """File > Import > ChiSurf-Sampling: a sampling folder."""
        self._open_dialog("Open sampling folder", "folder", [("Folders", ["*"])], "open")

    def browse(self) -> None:
        """The Browse button: choose the working folder."""
        self._open_dialog("Change working path", "folder", [("Folders", ["*"])], "working_path")

    def toggle_plot_controls(self) -> None:
        self.panel.show_plot_controls = not self.panel.show_plot_controls

    def exit(self) -> None:
        if self.on_exit is not None:
            self.on_exit()

    def close(self) -> None:
        """Release what the window holds (nothing global since it draws in the
        default style); kept for hosts, which call it when the window closes."""

    # -------------------------------------------------------------- layout
    def layout(self, x: float, y: float, w: float, h: float) -> dict:
        """Where everything goes, for a window of this size."""
        top = y + MENU_H
        left_w = max(LEFT_MIN, round(w * LEFT_FRACTION)) if self.panel.show_plot_controls else 0.0
        right_x = x + left_w + (GAP if left_w else 0.0)
        right_w = x + w - right_x
        body_top = top + TAB_H + 2.0
        header = (right_x, body_top, right_w, ROW_H)
        grid_top = body_top + ROW_H + 2.0
        grid_h = y + h - grid_top - 28.0
        corner_w = min(CORNER_W, max(right_w * 0.3, 120.0))
        xm_h = max(90.0, round((y + h) * XMARGINAL_FRACTION))
        map_w = right_w - corner_w
        return {
            "left_tabs": (x + 2.0, top + 1.0, left_w - 4.0, TAB_H),
            "left": (x + 2.0, body_top, left_w - 4.0, y + h - body_top - 4.0),
            "right_tabs": (right_x, top + 1.0, right_w, TAB_H),
            "header": header,
            "xmarginal": (right_x, grid_top, map_w, xm_h),
            "corner": (right_x + map_w, grid_top, corner_w, xm_h),
            "map": (right_x, grid_top + xm_h, map_w, grid_h - xm_h),
            "ymarginal": (right_x + map_w, grid_top + xm_h, corner_w, grid_h - xm_h),
            "status": (right_x, grid_top + grid_h, right_w, y + h - grid_top - grid_h),
        }

    # ------------------------------------------------------------- drawing
    def draw(self, painter, x: float, y: float, w: float, h: float) -> None:
        """Draw one frame of the window into *painter*."""
        import emtk

        self.box = (x, y, w, h)
        self.model.update()
        refresh_menus(self.menubar, self.panel.available, self._checked)
        painter.fill_rect(x, y, w, h, theme.WINDOW_BG)
        boxes = self.layout(x, y, w, h)
        self.plots.begin_frame()
        with emtk.frame(painter, (x, y, w, h), io=self.io, storage=self.storage):
            emtk.begin("##ndx", (x, y + MENU_H, w, h - MENU_H))
            modal = (self.dialog is not None or self.message is not None
                     or getattr(self, "_feature_modal", False))
            if modal:
                emtk.begin_disabled(True)
            if self.panel.show_plot_controls:
                self._draw_left(boxes)
            self._draw_right(boxes, painter)
            if modal:
                emtk.end_disabled()
            emtk.end()
            self._feature_modal = False
            for feature in self.features:
                if feature.draw_windows():
                    self._feature_modal = True
            if self.message is not None:
                self._draw_message(x, y, w, h)
            elif self.dialog is not None:
                self._draw_dialog(x, y, w, h)
        if self.status:
            from emtk import style
            from emtk.painter import ALIGN_LEFT, ALIGN_VCENTER

            bx, by, bw, bh = boxes["status"]
            painter.text(bx + 4.0, by, bw - 8.0, bh, ALIGN_LEFT | ALIGN_VCENTER,
                         self.status, style.TEXT)
        self._spend_edges()
        self._menu_box = (x, y, w, MENU_H)
        self.menubar.set_viewport(x + w, y + h)
        self.menubar.draw(painter, *self._menu_box)
        self._open_dropdowns()
        if self.popup is not None:
            self.popup[0].draw(painter, x, y, w, h)
        self.frames += 1

    def _spend_edges(self) -> None:
        """One-frame input edges are used up by the frame that saw them."""
        io = self.io
        for i in range(3):
            io.mouse_clicked[i] = False
            io.mouse_released[i] = False
            io.mouse_double_clicked[i] = False
        io.mouse_wheel = 0.0
        io.key, io.text = 0, ""

    def _tabs(self, box, titles, current: str, enabled=None) -> str:
        """A dock's tab strip: the current tab in the style's selected-tab colour."""
        import emtk
        from emtk.im_core import Col

        x, y, _w, h = box
        emtk.set_cursor_screen_pos((x, y))
        chosen = current
        for i, title in enumerate(titles):
            if i:
                emtk.same_line(0.0, 0.0)
            selected = title == current
            usable = enabled(title) if enabled else True
            style = emtk.get_style()
            emtk.push_style_color(Col.BUTTON, style.color(Col.TAB_SELECTED if selected
                                                          else Col.TAB))
            emtk.begin_disabled(not usable)
            if emtk.button(f"{title}##tab", (0.0, h)) and usable:
                chosen = title
            emtk.end_disabled()
            emtk.pop_style_color()
        return chosen

    def _draw_left(self, boxes: dict) -> None:
        import emtk
        from emtk.view_form import draw_form

        extra = dict(self.feature_tabs("left"))
        titles = ["Plot controls"] + [t for t in ("Parameters", "Overlays") if t not in extra] \
            + list(extra)
        order = ["Plot controls", "Parameters", "Overlays"]
        titles = sorted(dict.fromkeys(titles), key=lambda t: order.index(t) if t in order
                        else len(order))
        self.left_tab = self._tabs(boxes["left_tabs"], titles, self.left_tab,
                                   enabled=lambda t: t == "Plot controls" or t in extra)
        box = boxes["left"]
        if self.left_tab == "Plot controls":
            emtk.begin_child(box)
            draw_form(self.specs["plot_controls"], self.panel, self.forms["plot_controls"],
                      titles=False)
            emtk.end_child()
        elif self.left_tab in extra:
            emtk.begin_child(box)
            extra[self.left_tab](box)
            emtk.end_child()

    def _draw_right(self, boxes: dict, painter) -> None:
        import emtk
        from emtk.view_form import draw_form

        extra = dict(self.feature_tabs("right"))
        self.right_tab = self._tabs(boxes["right_tabs"], ["Plot"] + list(extra), self.right_tab)
        if self.right_tab in extra:
            box = (boxes["header"][0], boxes["header"][1],
                   boxes["header"][2], boxes["map"][1] + boxes["map"][3] - boxes["header"][1])
            emtk.begin_child(box)
            extra[self.right_tab](box)
            emtk.end_child()
            return
        for name, key in (("plot_header", "header"), ("plot_corner", "corner")):
            box = boxes[key]
            emtk.begin_child(box)
            draw_form(self.specs[name], self.panel, self.forms[name], titles=False)
            emtk.end_child()
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

    def _draw_dialog(self, x, y, w, h) -> None:
        import emtk

        dialog, purpose = self.dialog
        dw, dh = min(720.0, w - 40.0), min(460.0, h - 60.0)
        box = (x + (w - dw) / 2.0, y + (h - dh) / 2.0, dw, dh)
        self.dialog_box = box
        emtk.begin(f"{dialog.title}##dialog", box)
        emtk.text(dialog.title)
        emtk.separator()
        result = dialog.draw()
        emtk.end()
        if result is False:
            self.dialog = None
        elif result:
            self.dialog = None
            chosen = result[0] if isinstance(result, (list, tuple)) else result
            if purpose == "working_path":
                self.model.working_path = str(chosen)
            else:
                self.open_path(str(chosen))

    def _open_dropdowns(self) -> None:
        """A choice asked for its list: open it as a popup over everything."""
        from emtk.widgets.menus import MenuItem, Popup

        for form in self.forms.values():
            request, form.dropdown_request = form.dropdown_request, None
            if request is None:
                continue
            name, (rx, ry, rw, rh), labels, current = request
            items = [MenuItem(text, checked=(index == current)) for index, text in enumerate(labels)]
            popup = Popup(items)
            popup.open_at(rx, ry + rh)
            self.popup = (popup, items, form, name)

    # --------------------------------------------------------------- input
    def _box(self):
        return self.box

    def _press_overlays(self, px: float, py: float) -> bool:
        """Menus and popups take a press first: they are drawn over everything."""
        if self.popup is not None:
            popup, items, form, name = self.popup
            result = popup.press(px, py, *self.box)
            if not popup.open:
                self.popup = None
            if result.item is not None:
                if callable(name):                      # a menu from open_menu
                    name(result.item)
                else:
                    form.dropdown_result[name] = items.index(result.item)
            return True
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
        anywhere else (either button) closes it."""
        from emtk.widgets.menus import Popup

        popup = Popup(list(entries), title=title)
        popup.open_at(float(x), float(y))
        self.popup = (popup, None, None, on_choose)

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
        if (button == 1 or self.popup is not None) and self._press_overlays(float(x), float(y)):
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
        self.io.text = "".join(c for c in (text or "") if c >= " " and c != "\x7f")
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

    def animating(self) -> bool:
        """Whether the host should keep drawing without input: a feature is
        playing back or streaming results."""
        return any(feature.animating() for feature in self.features)


def make_app() -> NdxApp:
    """The factory :mod:`emtk.native` and :mod:`emtk.web` start (``ndxplorer.app.frame:make_app``)."""
    return NdxApp()
