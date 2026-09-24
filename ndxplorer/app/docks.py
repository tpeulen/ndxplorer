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
:mod:`ndxplorer.app.features`); the Plot window's own contents -- the
toolbar, the marginals, the map and the corner between the marginals -- are
laid out by :func:`plot_boxes`. The user resizes the marginals by the bars
between them and the map; the sizes are kept with the layout
(:meth:`emtk.docking.DockManager.set_extra`).
"""

from __future__ import annotations

from typing import Dict, Optional, Tuple

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

#: The left region's share, and its floor: an axis row (combo, bins, toggles,
#: Set) on one line. A split never gives either side more than half as floor.
LEFT_FRACTION = 0.29
LEFT_MIN = 405.0
#: The Plot window's fixed parts, in logical pixels. The toolbar over the
#: plots is one field tall when it fits on a line (emtk's frame height, passed
#: by the app; this is its fallback), and a small gap parts it from the plots.
ROW_H = 17.0
ROW_GAP = 2.0
#: The marginals' default thickness -- the x marginal's height, the y
#: marginal's width -- and the least and most the user may drag them to
#: (the most a share of the plot grid).
XMARGINAL_H = 96.0
YMARGINAL_W = 132.0
MARGINAL_MIN = 60.0
MARGINAL_MAX_FRACTION = 0.45
#: The bars between the marginals and the map, dragged to resize the marginals.
SPLIT = 4.0
#: The layout values (:meth:`emtk.docking.DockManager.extra`) the marginal sizes
#: are kept under.
XMARGINAL_KEY = "plot.xmarginal_h"
YMARGINAL_KEY = "plot.ymarginal_w"
#: The z marginal (Plot controls > z axis): its default height, the least and
#: most its bottom edge may be dragged to, and the layout value it is kept under.
ZMARGINAL_H = 100.0
ZMARGINAL_MIN = 60.0
ZMARGINAL_MAX = 320.0
ZMARGINAL_KEY = "plot_controls.zmarginal_h"
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


def plot_boxes(box: Rect, row_h: float = ROW_H, xmarginal_h: Optional[float] = None,
               ymarginal_w: Optional[float] = None) -> Dict[str, Rect]:
    """The Plot window's parts, in its content *box*.

    The toolbar on top (the path, the colours, the counts and the actions);
    under it the x marginal over the map, the y marginal beside the map and
    the empty corner between the marginals -- the Qt window's grid. A bar parts the
    marginals from the map (``"hsplit"`` under the x marginal, ``"vsplit"``
    left of the y marginal): dragging it resizes the marginal.

    *row_h* is the toolbar's height: one field (:func:`emtk.get_frame_height`),
    more when its controls wrap in a narrow window. The marginals are
    *xmarginal_h* tall and *ymarginal_w* wide (:data:`XMARGINAL_H`,
    :data:`YMARGINAL_W` by default), within :data:`MARGINAL_MIN` and a share
    of the grid. The corner between the marginals holds nothing.
    """
    x, y, w, h = box
    header = (x, y, w, row_h)
    grid_top = y + row_h + ROW_GAP
    grid_h = max(y + h - grid_top, 1.0)
    xm_h = XMARGINAL_H if xmarginal_h is None else float(xmarginal_h)
    ym_w = YMARGINAL_W if ymarginal_w is None else float(ymarginal_w)
    xm_h = min(max(xm_h, MARGINAL_MIN), grid_h * MARGINAL_MAX_FRACTION)
    ym_w = min(max(ym_w, MARGINAL_MIN), w * MARGINAL_MAX_FRACTION)
    map_w = max(w - ym_w - SPLIT, 1.0)
    map_top = grid_top + xm_h + SPLIT
    map_h = max(y + h - map_top, 1.0)
    right = x + map_w + SPLIT
    return {
        "header": header,
        "xmarginal": (x, grid_top, map_w, xm_h),
        "corner": (right, grid_top, ym_w, xm_h),
        "map": (x, map_top, map_w, map_h),
        "ymarginal": (right, map_top, ym_w, map_h),
        "hsplit": (x, grid_top + xm_h, w, SPLIT),
        "vsplit": (x + map_w, grid_top, SPLIT, grid_h),
    }
