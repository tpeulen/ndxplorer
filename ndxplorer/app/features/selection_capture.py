"""The selection feature's words in the parity scenarios (``tools/parity``).

The Qt scenarios name Qt things: ``pc.checkBoxEnableDrawing``,
``pc.tableWidget.customContextMenuRequested.emit(...)``,
``win.pick_population_at(3.2, 0.35)``. Each is replayed here the way a user
would do it in the emtk app: a toggle in the Draw Mask panel, a right-click
on the gate table, a pick at those data coordinates. A step that is not about
selection returns ``False`` and goes on to the core replay.
"""

from __future__ import annotations

import re
from typing import Callable, Dict

__all__ = ["ops", "targets"]

#: Qt widgets of the Draw Mask panel -> the panel model's attributes.
MASK_WIDGETS = {"pc.checkBoxEnableDrawing": "drawing", "pc.categorySpinBox": "category",
                "pc.brushSpinBox": "brush"}
#: Qt buttons of the Draw Mask panel -> its actions.
MASK_BUTTONS = {"pc.applyMaskBtn": "apply_mask", "pc.clearMaskBtn": "clear_mask",
                "pc.loadMaskBtn": "load_mask", "pc.saveMaskBtn": "save_mask"}


def _popup_rows(replay):
    popup = replay.app.popup
    if popup is None:
        return None
    return popup[0]


def _choose(replay, label: str) -> bool:
    """Click the row of the open context menu whose label starts with *label*."""
    replay.draw()
    popup = _popup_rows(replay)
    if popup is None:
        return False
    for entry, rect in popup._rows:
        if entry is not None and getattr(entry, "label", "").startswith(label):
            replay.click_rect(rect)
            replay.settle()
            return True
    return False


def ops(feature) -> Dict[str, Callable]:
    def canvas_click(replay, step):
        rect = replay.app.plots.rects.get("map")
        if rect is None:
            return False
        x, y, w, h = rect
        fx, fy = step["at"]
        px, py = x + fx * w, y + fy * h
        button = 2 if step.get("button") == "right" else 1
        replay.app.pointer_move(px, py)
        replay.draw()
        replay.app.pointer_press(px, py, button)
        replay.draw()
        replay.app.pointer_release(px, py, button)
        replay.draw()
        if feature.auto_choice and replay.app.popup is not None:
            label, feature.auto_choice = feature.auto_choice, None
            if not _choose(replay, label):
                from ..capture import Unsupported

                raise Unsupported(f"no menu row {label!r}")
        return True

    def menu_choice(replay, step):
        feature.auto_choice = step["text"]
        return True

    def call(replay, step):
        code = step["code"].strip()
        if "tableWidget.customContextMenuRequested" in code:
            match = re.search(r"QPoint\((\d+),\s*(\d+)\)", code)
            dx, dy = (int(match.group(1)), int(match.group(2))) if match else (40, 20)
            replay.settle()
            rect = feature.table_rect
            if rect is None:
                return False
            px, py = rect[0] + dx, rect[1] + dy
            replay.app.pointer_move(px, py)
            replay.draw()
            replay.app.pointer_press(px, py, 2)
            replay.draw()
            replay.app.pointer_release(px, py, 2)
            replay.draw()
            return True
        pick = re.search(r"pick_population_at\(([-\d.e]+),\s*([-\d.e]+)\)", code)
        if pick:
            x, y = float(pick.group(1)), float(pick.group(2))
            reason = feature.pick_population_at(x, y)
            replay.app.show_status(f"pick_population_at({x:g}, {y:g}): "
                                   + (reason or "gate fitted"))
            replay.settle()
            return True
        return False

    def set_(replay, step):
        attr = MASK_WIDGETS.get(step["widget"])
        if attr is None:
            return False
        setattr(feature.mask_model, attr, step["value"])
        replay.settle()
        return True

    def click(replay, step):
        action = MASK_BUTTONS.get(step["widget"])
        if action is None:
            return False
        rect = feature.mask_form.rects.get(action)
        if rect is not None:
            replay.click_rect(rect)
        else:
            getattr(feature.mask_model, action)()
        replay.settle()
        return True

    def capture(replay, step):
        # A context menu of this feature is the app's popup, not a menu-bar menu.
        if step.get("target") != "menu" or replay.app.popup is None:
            return False
        image = replay.draw()
        popup = replay.app.popup[0]
        x, y, w, h = popup.panel_rect
        for entry in popup.entries:
            if getattr(entry, "open", False) and entry.panel_rect is not None:
                sx, sy, sw, sh = entry.panel_rect
                x1, y1 = max(x + w, sx + sw), max(y + h, sy + sh)
                x, y = min(x, sx), min(y, sy)
                w, h = x1 - x, y1 - y
        pad = 2
        replay.shots[step.get("name", "menu")] = image.crop(
            (int(x) - pad, int(y) - pad, int(round(x + w)) + pad, int(round(y + h)) + pad))
        return True

    return {"canvas_click": canvas_click, "menu_choice": menu_choice, "call": call,
            "set": set_, "click": click, "capture": capture}


def targets(feature) -> Dict[str, Callable]:
    def mask_panel(replay):
        try:
            return replay.panel_rect("Draw Mask")
        except Exception:  # noqa: BLE001 - the panel is folded or absent
            return None

    return {"widget:pc.widgetMaskDrawing": mask_panel}
