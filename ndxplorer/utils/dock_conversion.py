"""Move ndX's panels out of Qt's dock widgets and into ChiSurf's dock area.

``QMainWindow``'s docks are the framework's, not the application's. They tab and
they float, but the tab bar is the platform's, the arrangement is not
rearrangeable beyond the four dock zones, and nothing about it matches the rest
of ChiSurf -- where every panel that can be moved lives in a
:class:`~chisurf.gui.widgets.dock_area.DockArea`: styled draggable tabs, drop to
split in any direction, a context menu, and an arrangement that can be persisted.

The panels themselves are untouched. Each ``QDockWidget`` is a *container*: its
contents are the widget ``uic`` built and everything else is wired to, so the
conversion lifts that widget out, hands it to the dock area, and disposes of the
container. What the window keeps is the plot; what it loses is
``tabifyDockWidget`` and the four fixed zones.
"""

from __future__ import annotations

import typing

from qtpy import QtCore, QtWidgets

from ..logging_config import logging

__all__ = ["PANELS", "convert_docks"]

#: ``objectName`` of each dock, its tab title, and whether it starts hidden.
#: Order is the tab order. The first three were tabified together by hand
#: (``arrange_docks_preserving_geometry``) and the last two were hidden; the
#: dock area does both by construction.
PANELS: tuple[tuple[str, str, bool], ...] = (
    ("dockWidget_PlotControl", "Plot controls", False),
    ("dockWidget_Parameters", "Parameters", False),
    ("dockWidget_Overlays", "Overlays", False),
    ("dockWidget_Equations", "Equations", True),
    ("dockWidget_Fit", "Gaussian Fit", True),
)


def convert_docks(window, plot_share: int = 3) -> typing.Optional[QtWidgets.QWidget]:
    """Replace `window`'s dock widgets with one ChiSurf dock area.

    Parameters
    ----------
    window : QtWidgets.QMainWindow
        The ndX main window, after its panels have been put into the dock
        contents. Running this earlier would move empty containers.
    plot_share : int
        Width of the plot against the panel column, as a weight.

    Returns
    -------
    QtWidgets.QWidget or None
        The dock area, also stored on the window as ``dock_area``; ``None`` when
        ChiSurf's dock area is unavailable, in which case the Qt docks are left
        exactly as they were.
    """
    try:
        from chisurf.gui.widgets.dock_area import DockArea
    except ImportError as exc:  # pragma: no cover - chisurf is a hard dependency
        logging.error("ChiSurf dock area unavailable, keeping the Qt docks: %s", exc)
        return None

    panels = []
    for name, title, hidden in PANELS:
        dock = getattr(window, name, None)
        if dock is None:
            continue
        contents = dock.widget()
        if contents is None:
            continue
        # Taken out of the dock before the dock is removed: ``removeDockWidget``
        # on a dock that still owns its contents takes the contents with it.
        dock.setWidget(None)
        contents.setParent(None)
        panels.append((contents, title, hidden))
        window.removeDockWidget(dock)
        dock.setParent(None)
        dock.deleteLater()
        # The attribute is what the rest of the window enabled and hid; it now
        # names the panel rather than a container that no longer exists, so a
        # ``setEnabled`` or a ``setVisible`` still lands on the right widget.
        setattr(window, name, contents)

    if not panels:
        return None

    plot = window.centralWidget()
    area = DockArea()
    for setup in (
        lambda: area.setNewTabButtonVisible(False),
        lambda: area.setContextMenuEnabled(True),
        lambda: area.setContextMenuMode("basic"),
    ):
        try:
            setup()
        except Exception:  # pragma: no cover - defensive
            pass

    if plot is not None:
        # Panels first, plot split off to the right: the dock they came from was
        # the *left* one, and moving a column someone reaches for without
        # looking is a change with no upside.
        first, first_title, _ = panels[0]
        area.addTab(first, first_title)
        target = area.find_main_tab_widget()
        for contents, title, _ in panels[1:]:
            target.addTab(contents, title)
            area._all_widgets.append(contents)
            area._tab_names[contents] = title
            try:
                area.setTabCloseMode(contents, "hide")
            except Exception:  # pragma: no cover - defensive
                pass
        plot.setParent(None)
        side = area._create_tab_widget()
        side.addTab(plot, "Plot")
        area._all_widgets.append(plot)
        area._tab_names[plot] = "Plot"
        area.split_tab_widget(target, side, "right")
    else:  # pragma: no cover - the .ui always has a central widget
        for contents, title, _ in panels:
            area.addTab(contents, title)

    window.setCentralWidget(area)
    window.dock_area = area

    for contents, _, hidden in panels:
        if hidden:
            index = area.indexOf(contents)
            if index >= 0:
                area.hideTab(index)
    # The first panel is the one to land on, not whichever was added last.
    area.setCurrentWidget(panels[0][0])

    # Twice, for the same reason the declarative dock areas do it: applied now
    # the splitter is a hundred pixels wide, so every share clamps to a child's
    # minimum and the ratio is silently lost. The deferred pass lands on real
    # geometry.
    _apply_share(area, plot_share)
    # On a timer the area owns: a window deleted before the loop turns takes it
    # along, instead of the pass running on a deleted area.
    later = QtCore.QTimer(area)
    later.setSingleShot(True)
    later.timeout.connect(lambda: _apply_share(area, plot_share))
    later.start(0)
    logging.info("Converted %d Qt docks to a ChiSurf dock area", len(panels))
    return area


def _apply_share(area, plot_share: int) -> None:
    """Give the plot `plot_share` of the width against the panel column.

    The panel column is the splitter's *first* half, so the plot's share is the
    second one.
    """
    for splitter in area.findChildren(QtWidgets.QSplitter):
        if splitter.count() == 2 and splitter.orientation() == QtCore.Qt.Horizontal:
            total = max(splitter.width(), 1)
            panels = int(total / (plot_share + 1))
            splitter.setSizes([panels, total - panels])
            return
