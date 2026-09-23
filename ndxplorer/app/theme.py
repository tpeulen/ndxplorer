"""The light desktop look of the Qt window, as emtk colours.

ndXplorer's Qt window is a light desktop application: grey chrome, white
fields, black text, white plot backgrounds. emtk's defaults are a dark chrome
meant to float over a 3-D scene. These are the Qt window's colours, installed
once: the painter-level palette (menus, the gate table), an immediate-mode
:class:`~emtk.im_core.Style` for the panels, and ImPlot's colours for the plots.
"""

from __future__ import annotations

__all__ = [
    "WINDOW_BG", "PALETTE", "PLOT_COLOURS", "X_FILL", "X_LINE", "Y_LINE", "Z_FILL", "Z_LINE",
    "Z_REGION", "LABEL_RED", "GATE", "install_palette", "make_style", "apply_plot_style",
]

#: The window background (Qt's Fusion/macOS light grey).
WINDOW_BG = (239, 239, 239, 255)
_TEXT = (0, 0, 0, 255)
_FIELD = (255, 255, 255, 255)
_BORDER = (180, 180, 180, 255)
_BUTTON = (250, 250, 250, 255)
_BUTTON_HOVER = (229, 241, 251, 255)
_BUTTON_DOWN = (204, 228, 247, 255)
_ACCENT = (0, 120, 215, 255)
_SELECTED = (205, 232, 255, 255)
_HEADER = (222, 222, 222, 255)

#: Painter-level palette (:func:`emtk.style.use_palette`): menus, popups, tables.
PALETTE = {
    "TEXT": _TEXT,
    "DIM": (110, 110, 110, 255),
    "TEXT_DISABLED": (150, 150, 150, 255),
    "WINDOW_BG": WINDOW_BG,
    "POPUP_BG": (252, 252, 252, 255),
    "BORDER": _BORDER,
    "SEPARATOR": (210, 210, 210, 255),
    "FRAME_BG": _FIELD,
    "FRAME_BG_HOVERED": _FIELD,
    "FRAME_BG_ACTIVE": _FIELD,
    "MENU_BAR_BG": (240, 240, 240, 255),
    "CHECK_MARK": (30, 30, 30, 255),
    "HEADER": _BUTTON_HOVER,
    "HEADER_HOVERED": _SELECTED,
    "HEADER_ACTIVE": _SELECTED,
    "HEADER_BG": (246, 246, 246, 255),
    "TABLE_HEADER_TEXT": _TEXT,
    "TABLE_ROW_BG": _FIELD,
    "TABLE_ROW_BG_ALT": _FIELD,
    "ROW_SEL": (204, 228, 247, 255),
    "TRACK_BG": _FIELD,
    "SCROLLBAR_BG": (240, 240, 240, 255),
    "SCROLLBAR_GRAB": (190, 190, 190, 255),
    "SCROLLBAR_GRAB_HOVERED": (160, 160, 160, 255),
    "SCROLLBAR_GRAB_ACTIVE": (130, 130, 130, 255),
    "THUMB": (190, 190, 190, 255),
    "GOLD": _ACCENT,
}

#: The x marginal: pale blue fill under a blue outline, as pyqtgraph draws it.
X_FILL = (135, 195, 255, 255)
X_LINE = (21, 101, 192, 255)
#: The y marginal: a green step line.
Y_LINE = (0, 170, 0, 255)
#: The z marginal: magenta, over a pale blue selection region.
Z_FILL = (220, 130, 255, 255)
Z_LINE = (200, 0, 220, 255)
Z_REGION = (200, 200, 255, 255)
#: Axis titles: red, bold, as ndXplorer's axis label settings say.
LABEL_RED = (200, 40, 40, 255)
#: A gate drawn on a plot.
GATE = (255, 90, 0, 255)


def install_palette() -> dict:
    """Install :data:`PALETTE`; returns what it replaced."""
    from emtk import style

    return style.use_palette({k: v for k, v in PALETTE.items() if hasattr(style, k)})


def make_style():
    """An immediate-mode style in the Qt window's colours and spacing."""
    from emtk.im_core import Col, Style

    s = Style()
    s.frame_padding = (4.0, 3.0)
    s.item_spacing = (4.0, 3.0)
    s.item_inner_spacing = (4.0, 3.0)
    s.frame_rounding = 2.0
    s.frame_border_size = 1.0
    c = s.colors
    c[Col.TEXT] = _TEXT
    c[Col.TEXT_DISABLED] = (150, 150, 150, 255)
    c[Col.WINDOW_BG] = WINDOW_BG
    c[Col.POPUP_BG] = (252, 252, 252, 255)
    c[Col.BORDER] = _BORDER
    c[Col.FRAME_BG] = _FIELD
    c[Col.FRAME_BG_HOVERED] = _FIELD
    c[Col.FRAME_BG_ACTIVE] = _FIELD
    c[Col.TITLE_BG] = WINDOW_BG
    c[Col.TITLE_BG_ACTIVE] = WINDOW_BG
    c[Col.MENU_BAR_BG] = (240, 240, 240, 255)
    c[Col.SCROLLBAR_BG] = (240, 240, 240, 255)
    c[Col.SCROLLBAR_GRAB] = (190, 190, 190, 255)
    c[Col.CHECK_MARK] = (30, 30, 30, 255)
    c[Col.SLIDER_GRAB] = (160, 160, 160, 255)
    c[Col.SLIDER_GRAB_ACTIVE] = _ACCENT
    c[Col.BUTTON] = _BUTTON
    c[Col.BUTTON_HOVERED] = _BUTTON_HOVER
    c[Col.BUTTON_ACTIVE] = _BUTTON_DOWN
    c[Col.HEADER] = _HEADER
    c[Col.HEADER_HOVERED] = _BUTTON_HOVER
    c[Col.HEADER_ACTIVE] = _SELECTED
    c[Col.SEPARATOR] = (210, 210, 210, 255)
    c[Col.SEPARATOR_HOVERED] = _ACCENT
    c[Col.SEPARATOR_ACTIVE] = _ACCENT
    c[Col.TAB] = (230, 230, 230, 255)
    c[Col.TAB_SELECTED] = _SELECTED
    c[Col.PLOT_LINES] = X_LINE
    c[Col.PLOT_HISTOGRAM] = X_FILL
    return s


#: ImPlot colours: white plots, black ticks, no grid.
PLOT_COLOURS = {
    "FRAME_BG": (1.0, 1.0, 1.0, 1.0),
    "PLOT_BG": (1.0, 1.0, 1.0, 1.0),
    "PLOT_BORDER": (0.0, 0.0, 0.0, 0.0),
    "AXIS_TEXT": (0.35, 0.35, 0.35, 1.0),
    "AXIS_TICK": (0.35, 0.35, 0.35, 1.0),
    "AXIS_GRID": (0.0, 0.0, 0.0, 0.0),
    "TITLE_TEXT": (0.0, 0.0, 0.0, 1.0),
    "INLAY_TEXT": (0.0, 0.0, 0.0, 1.0),
    "SELECTION": (0.0, 0.47, 0.84, 1.0),
}


def apply_plot_style() -> None:
    """ImPlot's style for ndXplorer's plots: white, tight, no grid."""
    from emtk import implot
    from emtk import implot_internal as I

    style = implot.get_style()
    style.plot_padding = (0.0, 0.0)
    style.label_padding = (3.0, 2.0)
    style.plot_border_size = 0.0
    style.plot_min_size = (20.0, 20.0)
    style.major_tick_len = (4.0, 4.0)
    style.minor_tick_len = (2.0, 2.0)
    style.fit_padding = (0.0, 0.0)
    for name, colour in PLOT_COLOURS.items():
        style.colors[getattr(I, "COL_" + name)] = I.rgba(colour)
