"""The window's docks: every panel is a sticky window (:mod:`emtk.docking`).

ndXplorer's Qt window has two dock areas: *Plot controls* on the left (with
the Parameters, Overlays, Equations and Gaussian Fit tabs beside it) and the
*Plot* on the right. Here each of those is a window of one
:class:`emtk.docking.DockManager` over two regions, ``"left"`` and
``"right"``, and the first start looks exactly like the Qt window: the left
region holds the tabs, the Plot fills the right. From there the user can float
a window by dragging its tab off the strip, snap floating windows to the
edges and to each other, drop one back into a region (it fills it, as a tab
beside what is there), drag the bar between the regions, and close a window
-- the View menu shows it again.

The layout is remembered in the settings directory
(``~/.ndxplorer/ndxplorer_layout.json``; ``localStorage`` in a page) when the
app is given :func:`layout_store` -- the shipped entry points do, tests do not.

A feature adds windows through ``Feature.windows()`` (see
:mod:`ndxplorer.app.features`); the Plot window's own contents -- the path
row, the marginals, the map and the display corner -- are laid out by
:func:`plot_boxes`.
"""

from __future__ import annotations

from typing import Dict, Tuple

__all__ = ["LEFT", "RIGHT", "PLOT_CONTROLS", "PLOT", "LAYOUT_FILE", "LEFT_ORDER",
           "layout_store", "build", "add_feature_windows", "plot_boxes"]

Rect = Tuple[float, float, float, float]

#: The two regions, named as ``Feature.windows()`` names them.
LEFT = "left"
RIGHT = "right"
#: The core's two windows.
PLOT_CONTROLS = "Plot controls"
PLOT = "Plot"
#: The left region's tab order at first start, as the Qt window's.
LEFT_ORDER = [PLOT_CONTROLS, "Parameters", "Overlays"]
#: Where the layout is kept, in the settings directory.
LAYOUT_FILE = "ndxplorer_layout.json"

#: The left region's share and its floor (the Qt window's dock widths).
LEFT_FRACTION = 0.357
LEFT_MIN = 360.0
#: The Plot window's fixed parts, in logical pixels.
ROW_H = 26.0
CORNER_W = 258.0
XMARGINAL_FRACTION = 0.2
#: Space between a window's frame and its content: the Qt docks' margins.
PADDING = 2.0


def layout_store():
    """The layout's :class:`emtk.docking.LayoutStore`, in ndXplorer's settings folder."""
    from emtk.docking import LayoutStore

    from ..settings import get_settings_path

    return LayoutStore("ndxplorer", path=get_settings_path() / LAYOUT_FILE)


def build(app, store=None):
    """The dock manager with the core's windows: Plot controls left, Plot right."""
    from emtk.docking import DockManager, Region, Split

    docks = DockManager(Split("h", LEFT_FRACTION, Region(LEFT), Region(RIGHT),
                              min_size=LEFT_MIN),
                        store=store, name="ndx")
    docks.add_window(PLOT_CONTROLS, PLOT_CONTROLS, app._draw_plot_controls, dock=LEFT,
                     padding=PADDING, min_size=(260.0, 160.0))
    docks.add_window(PLOT, PLOT, app._draw_plot, dock=RIGHT, padding=PADDING,
                     min_size=(360.0, 280.0))
    return docks


def add_feature_windows(app) -> None:
    """Add every feature's windows, order the left tabs, then read the saved layout.

    ``Feature.windows()`` entries are ``(region, title, draw)`` or
    ``(region, title, draw, options)``, *options* any
    :class:`emtk.docking.DockWindow` attribute (``visible=False`` for a window
    the View menu opens).
    """
    docks = app.docks
    for feature in app.features:
        for entry in feature.windows():
            region, title, draw = entry[:3]
            options = dict(entry[3]) if len(entry) > 3 else {}
            options.setdefault("padding", PADDING)
            docks.add_window(title, title, draw, dock=region, **options)
    rank = {title: i for i, title in enumerate(LEFT_ORDER)}
    docks.tabs[LEFT].sort(key=lambda title: rank.get(title, len(rank)))
    docks.load()


def plot_boxes(box: Rect) -> Dict[str, Rect]:
    """The Plot window's parts, in its content *box*.

    The path row on top; under it the x marginal over the map, the display
    corner beside the x marginal and the y marginal beside the map -- the Qt
    window's grid.
    """
    x, y, w, h = box
    header = (x, y, w, ROW_H)
    grid_top = y + ROW_H + 2.0
    grid_h = max(y + h - grid_top, 1.0)
    corner_w = min(CORNER_W, max(w * 0.3, 120.0))
    xm_h = min(max(90.0, round(h * XMARGINAL_FRACTION)), grid_h * 0.5)
    map_w = max(w - corner_w, 1.0)
    return {
        "header": header,
        "xmarginal": (x, grid_top, map_w, xm_h),
        "corner": (x + map_w, grid_top, corner_w, xm_h),
        "map": (x, grid_top + xm_h, map_w, grid_h - xm_h),
        "ymarginal": (x + map_w, grid_top + xm_h, corner_w, grid_h - xm_h),
    }
