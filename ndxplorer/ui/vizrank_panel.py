"""The ranking panel hosted in a Qt window.

The panel is ``vizrank.view.json`` drawn by ``emtk.view_form`` over
:class:`~ndxplorer.analysis.vizrank_model.VizRankModel` (both Qt-free, in
:mod:`ndxplorer.analysis`); this module only *hosts* that emtk surface in a Qt
tool window, as ChiSurf's emtk tools do, and gives the guided tour invisible
anchors to point at. The emtk app draws the same spec over the same model
natively.
"""

from __future__ import annotations

import logging
from typing import Optional

from ..analysis.vizrank import RunState
from ..analysis.vizrank_model import VizRankModel, load_spec

logger = logging.getLogger(__name__)

__all__ = ["VizRankWindow"]


def _window_base():
    from chisurf.gui.widgets.tools.help_guide import HelpGuideMixin
    from qtpy import QtWidgets

    return HelpGuideMixin, QtWidgets.QMainWindow


class _Surface:
    """Adapts ``draw_form`` over the model to ``ControlHost``'s control contract."""

    BACKGROUND = (30, 32, 38, 255)

    def __init__(self, spec: dict, model: VizRankModel):
        import emtk
        from emtk.view_form import FormState

        self.spec = spec
        self.model = model
        self.io = emtk.IO()
        self.storage: dict = {}
        self.state = FormState()
        self.popup = None
        self.box = (0.0, 0.0, 1.0, 1.0)

    def table(self):
        """The ranked-views table binding, once drawn."""
        return self.state.tables.get("ranked_rows")

    def draw(self, painter, x: float, y: float, w: float, h: float) -> None:
        import emtk
        from emtk.view_form import draw_form

        self.box = (x, y, w, h)
        painter.fill_rect(x, y, w, h, self.BACKGROUND)
        with emtk.frame(painter, (x, y, w, h), io=self.io, storage=self.storage):
            emtk.begin("##vizrank", (x + 6.0, y + 6.0, w - 12.0, h - 12.0),
                       emtk.WindowFlags.NO_TITLE_BAR)
            draw_form(self.spec, self.model, self.state, titles=False)
            emtk.end()
        binding = self.table()
        request = self.model.select_request
        if binding is not None and request is not None:
            binding.refresh()
            if binding.control.select_key(request):
                self.model.select_request = None
        self.io.mouse_clicked[0] = False
        self.io.mouse_released[0] = False
        self.io.mouse_double_clicked[0] = False
        self.io.mouse_wheel = 0.0
        self.io.key, self.io.text = 0, ""
        self._open_dropdown()
        if self.popup is not None:
            self.popup[0].draw(painter, x, y, w, h)

    def _open_dropdown(self) -> None:
        from emtk.widgets.menus import MenuItem, Popup

        request, self.state.dropdown_request = self.state.dropdown_request, None
        if request is None:
            return
        name, (rx, ry, _rw, rh), labels, current = request
        items = [MenuItem(text, checked=(index == current)) for index, text in enumerate(labels)]
        popup = Popup(items)
        popup.open_at(rx, ry + rh)
        self.popup = (popup, items, name)

    # -- input ----------------------------------------------------------------------
    def hover(self, px: float, py: float, *_box) -> None:
        self.io.mouse_pos = (px, py)

    def drag(self, px: float, py: float, *_box) -> None:
        self.io.mouse_pos = (px, py)

    def press(self, px: float, py: float, *extra, **_kw) -> None:
        if self.popup is not None:
            popup, items, name = self.popup
            x, y, w, h = self.box
            result = popup.press(px, py, x, y, w, h)
            if result.item is not None:
                self.state.dropdown_result[name] = items.index(result.item)
            if not popup.open:
                self.popup = None
            return
        clicks = extra[5] if len(extra) > 5 else 1
        io = self.io
        io.mouse_pos = io.mouse_clicked_pos[0] = (px, py)
        io.mouse_clicked[0] = io.mouse_down[0] = True
        io.mouse_double_clicked[0] = clicks >= 2

    def release(self, *_args, **_kw) -> None:
        if self.io.mouse_down[0]:
            self.io.mouse_down[0] = False
            self.io.mouse_released[0] = True

    def scroll(self, rows: int) -> None:
        self.io.mouse_wheel = -1.0 if rows > 0 else 1.0

    def key(self, key: int, text: str = "", modifiers: int = 0) -> bool:
        self.io.key = int(key)
        self.io.text = "".join(c for c in (text or "") if c >= " " and c != "\x7f")
        return True


#: Tour anchors: object name -> the ``FormState.rects`` name of an emtk control.
ANCHORS = {
    "vizrank_method": "method",
    "vizrank_classes": "classes",
    "vizrank_sample": "sample_rows",
    "vizrank_start": "start",
    "vizrank_pause": "pause",
    "vizrank_table": "ranked_rows",
}


def VizRankWindow(model: VizRankModel, parent=None, spec: Optional[dict] = None):  # noqa: N802
    """A Qt window hosting the emtk panel for *model* (built on first call)."""
    HelpGuideMixin, QMainWindow = _window_base()
    global _WINDOW_CLASS
    if _WINDOW_CLASS is None:
        from qtpy import QtCore, QtWidgets

        class _Anchor(QtWidgets.QWidget):
            """An invisible stand-in for one emtk control, for the guided tour."""

            clicked = QtCore.Signal()

            def __init__(self, name: str, parent) -> None:
                super().__init__(parent)
                self.setObjectName(name)
                self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
                self.setAttribute(QtCore.Qt.WA_NoSystemBackground, True)
                self.resize(1, 1)

        class _VizRankWindow(HelpGuideMixin, QMainWindow):
            """The emtk ranking panel as a tool window beside ndX.

            Qt does two things here: host the surface, and give the guided tour
            something to point at (one invisible anchor per named control, kept
            over the control's last drawn rectangle).
            """

            help_title = "Find informative projections"

            def __init__(self, model: VizRankModel, parent=None, spec=None) -> None:
                super().__init__(parent)
                from emtk.qt_host import ControlHost

                self.model = model
                self.setWindowTitle(model.title)
                self.setWindowFlag(QtCore.Qt.Tool, True)
                self.surface = _Surface(spec or load_spec(), model)
                self.host = ControlHost(self.surface, background=_Surface.BACKGROUND[:3])
                self.host.setObjectName("vizrank_surface")
                self.host.setMinimumSize(460, 520)
                self.setCentralWidget(self.host)
                toolbar = QtWidgets.QToolBar("Ranking", self)
                toolbar.setMovable(False)
                self.addToolBar(toolbar)
                self.ensure_help_toolbar(toolbar=toolbar, help_resource="vizrank_help.md",
                                         guide_resource="vizrank_guide.json")
                self.anchors = {name: _Anchor(name, self.host) for name in ANCHORS}
                model.on_change = self.host.update
                self.surface.state.on_used = self._used
                self.timer = QtCore.QTimer(self)
                self.timer.timeout.connect(self._tick)
                self.timer.start(60)
                self.resize(520, 640)

            def _used(self, name: str) -> None:
                for anchor, key in ANCHORS.items():
                    if key == name:
                        self.anchors[anchor].clicked.emit()

            def _tick(self) -> None:
                self.host.update()
                for anchor, key in ANCHORS.items():
                    rect = self.surface.state.rects.get(key)
                    if rect:
                        x, y, w, h = rect
                        self.anchors[anchor].setGeometry(int(x), int(y), max(int(w), 1),
                                                         max(int(h), 1))

            def hideEvent(self, event) -> None:  # noqa: N802 - Qt's spelling
                self.model.pause_computation(RunState.Hidden)
                super().hideEvent(event)

            def closeEvent(self, event) -> None:  # noqa: N802
                self.timer.stop()
                super().closeEvent(event)

        _WINDOW_CLASS = _VizRankWindow
    return _WINDOW_CLASS(model, parent, spec)


_WINDOW_CLASS = None
