"""*Find informative projections…* in the Qt window: the View-menu entries and
the panels' wiring.

Two View menu entries, directly below *UMAP*, rank every pair (*Find
informative projections…*) or every third parameter (*… (z axis)…*); clicking a
row sets the axes. The ranking, its context and the panel's model are Qt-free,
in :mod:`ndxplorer.analysis.projection_rank_model`; here is only what reads the
Qt window (:func:`collect_context`) and the controller that opens the panels.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from ..analysis.projection_rank_model import ProjectionRankModel, RankingContext, build_context
from .vizrank_panel import VizRankWindow

logger = logging.getLogger(__name__)

__all__ = [
    "collect_context",
    "ProjectionRankController",
    "install_projection_ranking",
]


def collect_context(window) -> Optional[RankingContext]:
    """Read the table, the axis settings, the gates and the classes from *window*.

    Returns ``None`` when there is no table to rank.
    """
    source = getattr(window, "data_source", None)
    if source is None or source.empty:
        return None
    control = window.plot_control
    try:
        selections = [s for s in control.get_selections() if getattr(s, "enabled", True)]
    except Exception:
        logger.debug("could not read the gates", exc_info=True)
        selections = []
    try:
        z_name = control.p3[1]
    except Exception:
        z_name = ""
    return build_context(source, getattr(control, "axis_settings", {}) or {}, selections,
                         getattr(window, "_cluster_labels", None), z_name)


def _qt_defer(fn) -> None:
    """Run *fn* from the Qt event loop, after the current callback."""
    from qtpy import QtCore

    QtCore.QTimer.singleShot(0, fn)


class ProjectionRankController:
    """Owns the two ranking panels of one ndX window and wires them in.

    Orange keeps this in a widget mixin (``VizRankMixin``); ndX's window is
    built from a ``.ui`` file and a dozen mixins already, so the same duties —
    the menu entries, one panel per data, apply on select, select on manual change —
    live in a plain object instead.
    """

    def __init__(self, window):
        self.window = window
        #: The panel windows, by ``pairs``; each carries its ``model``.
        self.dialogs: Dict[bool, Any] = {}
        self._applying = False

    # ---- menu entries --------------------------------------------------------------

    #: The View-menu actions (declared in ``plotting/plot_main.ui`` directly below
    #: *UMAP*), by ``pairs``. Their enabled state is the window's: like *UMAP*,
    #: they are disabled while no table is loaded (``update_ui_enabled_state``).
    ACTIONS = {True: "actionFindProjections", False: "actionFindZParameters"}

    def install(self) -> None:
        """Connect the View-menu entries and follow hand-picked axes."""
        for pairs, name in self.ACTIONS.items():
            action = getattr(self.window, name, None)
            if action is None:
                logger.debug("projection ranking: the window has no %s", name)
                continue
            action.triggered.connect(lambda _checked=False, p=pairs: self.open(p))
        control = self.window.plot_control
        for combo in (control.comboBoxSelX, control.comboBoxSelY, control.comboBoxSelZ):
            combo.currentIndexChanged.connect(self._on_axis_changed)

    def action(self, pairs: bool = True):
        """The View-menu action that opens the panel for *pairs*."""
        return getattr(self.window, self.ACTIONS[pairs], None)

    # ---- panels ----------------------------------------------------------------

    def model(self, pairs: bool = True) -> Optional[ProjectionRankModel]:
        """The ranking model for *pairs*, rebuilt if the table it ranked has changed."""
        context = collect_context(self.window)
        if context is None:
            self.shutdown()
            return None
        window = self.dialogs.get(pairs)
        model = window.model if window is not None else None
        if model is not None and model._run is not None and model._run.settings[3] != context.key:
            # New data, new panel (Orange does the same): the old rows name a
            # table that no longer exists.
            self._discard(pairs)
            model = None
        if model is None:
            model = ProjectionRankModel(lambda: collect_context(self.window), pairs,
                                        on_apply=self.apply, defer=_qt_defer)
            self.dialogs[pairs] = VizRankWindow(model, self.window)
        else:
            model.refresh_context()
        return model

    def open(self, pairs: bool = True) -> Optional[ProjectionRankModel]:
        """Show the panel and start (or resume) its ranking, as Orange's VizRank button does."""
        model = self.model(pairs)
        if model is None:
            return None
        window = self.dialogs[pairs]
        window.show()
        window.raise_()
        window.activateWindow()
        model.dialog_reopened()
        self._on_axis_changed()
        return model

    def _discard(self, pairs: bool) -> None:
        window = self.dialogs.pop(pairs, None)
        if window is not None:
            window.model.shutdown()
            window.close()
            window.deleteLater()

    def shutdown(self) -> None:
        """Close both panels (the table went away)."""
        for pairs in list(self.dialogs):
            self._discard(pairs)

    # ---- apply and follow ------------------------------------------------------

    def apply(self, payload) -> None:
        """Set the view a row describes."""
        control = self.window.plot_control
        self._applying = True
        try:
            if "z" in payload:
                self._set_axis(control, "z", payload["z"], payload.get("scale_z", "lin"))
                checkbox = getattr(self.window, "checkBoxEnableZ", None)
                if checkbox is not None and not checkbox.isChecked():
                    checkbox.setChecked(True)
            else:
                self._set_axis(control, "x", payload["x"], payload.get("scale_x", "lin"))
                self._set_axis(control, "y", payload["y"], payload.get("scale_y", "lin"))
        finally:
            self._applying = False

    @staticmethod
    def _set_axis(control, axis: str, name: str, scale: str) -> None:
        """Choose *name* on *axis*, drawn in the *scale* it was scored in.

        Choosing the parameter applies its saved axis settings (or auto-ranges);
        only when that leaves a different scale is the scale set and the axis
        auto-ranged again, so a saved range is not thrown away needlessly.
        """
        control.set_axis_by_name(axis, name, match_contains=False)
        current = getattr(control, f"scale_{axis}")
        if current != scale:
            setattr(control, f"scale_{axis}", scale)
            auto = getattr(control, f"on_auto_range_{axis}", None)
            if callable(auto):
                auto()
            request = getattr(control.parent, "request_plot_update", None)
            if callable(request):
                request()

    def _on_axis_changed(self, *_args) -> None:
        """Follow a hand-picked view in the open panel (Orange's auto-select)."""
        if self._applying:
            return
        control = self.window.plot_control
        pair_window = self.dialogs.get(True)
        if pair_window is not None and pair_window.isVisible():
            pair_window.model.auto_select({"x": control.p1[1], "y": control.p2[1]})
        z_window = self.dialogs.get(False)
        if z_window is not None and z_window.isVisible():
            z_window.model.auto_select({"z": control.p3[1]})


def install_projection_ranking(window) -> ProjectionRankController:
    """Connect *window*'s View-menu ranking entries; returns the controller (``window.projection_rank``)."""
    controller = ProjectionRankController(window)
    controller.install()
    window.projection_rank = controller
    return controller
