"""The few colours that carry meaning; everything else is emtk's default look.

The app draws with emtk's and ImPlot's default style -- colours, font, sizes,
spacing -- as chimol does, and adds nothing on top. What is left here is data
semantics: which colour stands for which axis, and what a gate looks like.
Even those come from ImPlot's default colormap (Deep), so they follow the
style rather than fighting it.
"""

from __future__ import annotations

__all__ = ["WINDOW_BG", "gate_colour", "axis_colour", "text_colour"]

#: The window background: emtk's window colour, opaque.
WINDOW_BG = (15, 15, 15, 255)


def axis_colour(key: str, alpha: int = 255) -> tuple:
    """The colour of axis *key*'s marginal: ImPlot's default colormap, x, y, z in
    turn; ``"gate"`` is the fourth colour, for gates drawn on a plot."""
    from emtk import implot

    index = {"x": 0, "y": 1, "z": 2, "gate": 3}.get(key, 0)
    colour = implot.get_colormap_color(index)
    rgba = tuple(int(round(c * 255)) if isinstance(c, float) else int(c) for c in colour)
    return rgba[:3] + (int(alpha),)


def gate_colour(alpha: int = 255) -> tuple:
    """A gate drawn on a plot (a dragged rectangle, the selected gate's edges)."""
    return axis_colour("gate", alpha)


def text_colour() -> tuple:
    """emtk's default text colour, for text drawn straight onto the painter."""
    from emtk import style

    return tuple(style.TEXT)[:3] + (255,)
