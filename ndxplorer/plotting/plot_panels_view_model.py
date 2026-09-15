"""The plot-control blocks as foldable AutoForm panels.

Every block of the dock was a ``QGroupBox``: a title, a frame, and no way to put
it away. In a column five blocks tall that is the difference between a control
panel and a wall, and Playback -- which arrived as an AutoForm panel and got a
fold for free -- made the asymmetry the obvious thing to fix.

The controls are **not** rebuilt. They are the widgets ``plot_control.ui``
declares: about fifty of them, wired to the axis/scale/histogram mixins and to
the mask-drawing widget by ``objectName``, and read from a dozen tests as
``control.comboBoxSelX``, ``control.n_xhist_2d``, ``control.xmin``. Rebuilding
those as ``value`` and ``choice`` sections is a real port with a real payoff --
tooltips, generated documentation, state save/restore -- but it is a different
change from giving the blocks a fold, and doing both at once would leave neither
reviewable. Each panel therefore *adopts* the widget that is already there,
through the ``embed`` section's ``attr`` option.

What the fold cost: two of these were **checkable** group boxes, and their check
state was not decoration -- it gated the z plot and mask drawing. A collapsible
box has no such state (folding is not disabling, and conflating them is how a
panel someone tidied away silently stops gating). So each got an explicit check
box inside the panel: ``checkBoxEnableZ`` and ``checkBoxEnableDrawing``, which
every existing call site now names instead.
"""

from __future__ import annotations

import json
import pathlib

from qtpy import QtCore

__all__ = ["PlotPanelsViewModel", "VIEW_SPEC_PATH"]

VIEW_SPEC_PATH = pathlib.Path(__file__).parent / "plot_panels.view.json"


class PlotPanelsViewModel(QtCore.QObject):
    """Binding for the dock's blocks: a title and a fold for each existing widget.

    Parameters
    ----------
    control : ndxplorer.plotting.plot_control.SurfacePlotWidget
        The panel whose ``uic``-built widgets are adopted.
    parent : QtCore.QObject, optional
        Qt parent.
    """

    #: Spec ``attr`` -> ``objectName`` in ``plot_control.ui``.
    WIDGETS = {
        "histogram_widget": "widgetHistogram",
        "z_widget": "widgetZ",
        "mask_panel_widget": "widgetMaskDrawing",
        "selection_widget": "widgetSelection",
    }

    def __init__(self, control, parent=None):
        super().__init__(parent)
        self._control = control
        #: Panel title -> folded, so a rebuild cannot undo what the user opened.
        self.collapsed: dict[str, bool] = {}

    def view_spec(self):
        """The parsed ``plot_panels.view.json``, with remembered fold states.

        A panel whose widget is missing is dropped rather than rendered empty:
        an ``embed`` that finds nothing leaves a titled box with a fold and no
        contents, which reads as a feature that broke rather than one that is
        not there.
        """
        from chisurf.core.dataspec import load_view_spec

        with open(VIEW_SPEC_PATH, encoding="utf-8") as fh:
            spec = json.load(fh)
        panels = []
        for panel in spec["sections"]:
            attr = panel["sections"][0]["options"]["attr"]
            if self.widget_for(attr) is None:
                continue
            title = panel.get("title", "")
            if title in self.collapsed:
                panel["collapsed"] = self.collapsed[title]
            panels.append(panel)
        spec["sections"] = panels
        return load_view_spec(spec)

    def widget_for(self, attr: str):
        """The widget an ``embed`` section's `attr` names, or ``None``."""
        name = self.WIDGETS.get(attr)
        return getattr(self._control, name, None) if name else None

    # The spec addresses these by name; one accessor each, because ``embed``
    # resolves an attribute on the model rather than calling it with a key.
    def histogram_widget(self):
        """The histogram block built by ``uic``."""
        return self.widget_for("histogram_widget")

    def z_widget(self):
        """The z-axis block built by ``uic``."""
        return self.widget_for("z_widget")

    def mask_panel_widget(self):
        """The mask-drawing block built by ``uic``."""
        return self.widget_for("mask_panel_widget")

    def selection_widget(self):
        """The selection table block built by ``uic``."""
        return self.widget_for("selection_widget")
