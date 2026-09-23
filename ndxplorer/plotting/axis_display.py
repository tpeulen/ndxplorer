"""Which axes and axis titles the plots show, and the title colour, without a window.

View > Axis Control edits this; ``axis_labels.yaml`` (named by the settings'
``axis_labels``) stores the label half of it. The plots read it:

``sides(plot)``
    ``{"bottom", "top", "left", "right": bool}`` -- the axes drawn on a plot
    (``"xmarginal"``, ``"ymarginal"``, ``"zmarginal"``, ``"map"``,
    ``"overlay"``).
``label(plot, side)``
    whether the axis title on that side is drawn: the x parameter's name over
    the x marginal (``"xmarginal", "top"``), the y parameter's beside the y
    marginal (``"ymarginal", "right"``), the z parameter's under or beside the
    z marginal. *Enable All Labels* turns every one of them on.
``title_colour``
    the titles' colour, an RGBA tuple.

The Qt dialog's names are kept in the file: ``x_plot``, ``y_plot``,
``z_plot``. The font sizes and weight it also stores are read and written back
unchanged, so a file shared with the Qt window keeps them, but the emtk app
draws its titles in its own font.
"""

from __future__ import annotations

import copy
import pathlib
from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional, Tuple, Union

__all__ = [
    "PLOTS",
    "SIDES",
    "LABELS",
    "DEFAULT_SIDES",
    "DEFAULT_LABEL_SETTINGS",
    "AxisDisplay",
    "parse_colour",
    "colour_hex",
    "label_settings_bytes",
    "write_label_settings",
]

#: The plots, by the names the emtk app draws them under.
PLOTS = ("xmarginal", "ymarginal", "zmarginal", "map", "overlay")
SIDES = ("bottom", "top", "left", "right")
#: The axis titles that can be switched, per plot (the Qt dialog's).
LABELS = {"xmarginal": ("top",), "ymarginal": ("top", "right"),
          "zmarginal": ("bottom", "left")}
#: The label settings' plot names (``axis_labels.yaml``).
FILE_NAMES = {"xmarginal": "x_plot", "ymarginal": "y_plot", "zmarginal": "z_plot"}

#: The axes a fresh window shows: the x marginal's ticks on top, the y
#: marginal's on the right, the z plot's at the bottom and left, none on the
#: map (the marginals are its axes).
DEFAULT_SIDES: Dict[str, Dict[str, bool]] = {
    "xmarginal": {"bottom": False, "top": True, "left": False, "right": False},
    "ymarginal": {"bottom": False, "top": False, "left": False, "right": True},
    "zmarginal": {"bottom": True, "top": False, "left": True, "right": False},
    "map": {"bottom": False, "top": False, "left": False, "right": False},
    "overlay": {"bottom": False, "top": False, "left": False, "right": False},
}

#: What the Qt window assumed when the settings name no label file.
DEFAULT_LABEL_SETTINGS: Dict[str, Any] = {
    "enable_all_labels": True,
    "axis_labels": {
        "y_plot": {"top": True, "right": True},
        "x_plot": {"top": True},
        "z_plot": {"bottom": True, "left": True},
    },
    "fonts": {"tick_size_pt": 8, "title_size_pt": 10, "title_weight": 700,
              "color": "#000000"},
}


def parse_colour(text: Any, default: Tuple[int, int, int, int] = (0, 0, 0, 255)) -> tuple:
    """``"#bb3838"`` (or ``"#bb3838ff"``, or an RGB(A) sequence) as an RGBA tuple."""
    if isinstance(text, (list, tuple)) and len(text) in (3, 4):
        values = [int(v) for v in text]
        return tuple(values + [255] * (4 - len(values)))
    value = str(text or "").strip().lstrip("#")
    if len(value) == 3:
        value = "".join(c * 2 for c in value)
    if len(value) not in (6, 8):
        return default
    try:
        channels = [int(value[i:i + 2], 16) for i in range(0, len(value), 2)]
    except ValueError:
        return default
    return tuple(channels + [255] * (4 - len(channels)))


def colour_hex(rgba) -> str:
    """An RGB(A) tuple as ``"#rrggbb"``."""
    r, g, b = (max(0, min(255, int(round(c)))) for c in tuple(rgba)[:3])
    return f"#{r:02x}{g:02x}{b:02x}"


@dataclass
class AxisDisplay:
    """The axes, axis titles and title colour of the plots.

    Attributes
    ----------
    axes : dict
        ``{plot: {side: bool}}`` -- which axes are drawn.
    label_settings : dict
        The ``axis_labels.yaml`` content: ``enable_all_labels``,
        ``axis_labels`` (per ``x_plot``/``y_plot``/``z_plot``) and ``fonts``.
    revision : int
        Bumped on every change, so a plot can tell.
    """

    axes: Dict[str, Dict[str, bool]] = field(default_factory=lambda: copy.deepcopy(DEFAULT_SIDES))
    label_settings: Dict[str, Any] = field(
        default_factory=lambda: copy.deepcopy(DEFAULT_LABEL_SETTINGS))
    revision: int = 0

    @classmethod
    def from_label_settings(cls, data: Optional[Mapping[str, Any]]) -> "AxisDisplay":
        """The default axes with the titles of an ``axis_labels.yaml`` (``None``: defaults)."""
        display = cls()
        if data:
            display.update_label_settings(data)
        return display

    # ---------------------------------------------------------------- reads
    def sides(self, plot: str) -> Dict[str, bool]:
        """``{side: bool}`` of the axes drawn on *plot*."""
        return dict(self.axes.get(plot) or DEFAULT_SIDES.get(plot) or {})

    def visible(self, plot: str, side: str) -> bool:
        return bool(self.sides(plot).get(side, False))

    @property
    def enable_all_labels(self) -> bool:
        return bool(self.label_settings.get("enable_all_labels", True))

    def label_switch(self, plot: str, side: str) -> bool:
        """The per-title switch, whatever *Enable All Labels* says."""
        name = FILE_NAMES.get(plot)
        if name is None or side not in LABELS.get(plot, ()):
            return False
        return bool(((self.label_settings.get("axis_labels") or {}).get(name) or {})
                    .get(side, True))

    def label(self, plot: str, side: str) -> bool:
        """Whether the axis title on *side* of *plot* is drawn."""
        if side not in LABELS.get(plot, ()):
            return False
        return self.enable_all_labels or self.label_switch(plot, side)

    @property
    def fonts(self) -> Dict[str, Any]:
        return dict(self.label_settings.get("fonts") or {})

    @property
    def title_colour(self) -> tuple:
        return parse_colour(self.fonts.get("color", "#000000"))

    # --------------------------------------------------------------- writes
    def _changed(self) -> None:
        self.revision += 1

    def set_visible(self, plot: str, side: str, on: bool) -> None:
        axes = self.axes.setdefault(plot, dict(DEFAULT_SIDES.get(plot, {})))
        if axes.get(side) != bool(on):
            axes[side] = bool(on)
            self._changed()

    def set_label(self, plot: str, side: str, on: bool) -> None:
        name = FILE_NAMES[plot]
        labels = self.label_settings.setdefault("axis_labels", {}).setdefault(name, {})
        if labels.get(side) != bool(on):
            labels[side] = bool(on)
            self._changed()

    def set_enable_all_labels(self, on: bool) -> None:
        if self.enable_all_labels != bool(on) or "enable_all_labels" not in self.label_settings:
            self.label_settings["enable_all_labels"] = bool(on)
            self._changed()

    def set_title_colour(self, colour) -> None:
        text = colour_hex(parse_colour(colour)) if not isinstance(colour, str) or \
            not colour.startswith("#") else colour_hex(parse_colour(colour))
        fonts = self.label_settings.setdefault("fonts", {})
        if fonts.get("color") != text:
            fonts["color"] = text
            self._changed()

    def update_label_settings(self, data: Mapping[str, Any]) -> None:
        """Take an ``axis_labels.yaml``'s content over the defaults (a shallow
        merge per key, as the Qt window's ``load_settings`` did)."""
        merged = copy.deepcopy(DEFAULT_LABEL_SETTINGS)
        for key, value in dict(data).items():
            if isinstance(value, Mapping) and isinstance(merged.get(key), dict):
                inner = dict(merged[key])
                inner.update(copy.deepcopy(dict(value)))
                merged[key] = inner
            else:
                merged[key] = copy.deepcopy(value)
        self.label_settings = merged
        self._changed()

    def copy(self) -> "AxisDisplay":
        return AxisDisplay(copy.deepcopy(self.axes), copy.deepcopy(self.label_settings),
                           self.revision)

    def assign(self, other: "AxisDisplay") -> None:
        """Take *other*'s axes and labels (Apply in the dialog)."""
        if other.axes != self.axes or other.label_settings != self.label_settings:
            self.axes = copy.deepcopy(other.axes)
            self.label_settings = copy.deepcopy(other.label_settings)
            self._changed()


def label_settings_bytes(label_settings: Mapping[str, Any]) -> bytes:
    """The content of an ``axis_labels.yaml``, with the Qt dialog's header."""
    import yaml

    data = {
        "enable_all_labels": bool(label_settings.get("enable_all_labels", True)),
        "axis_labels": copy.deepcopy(dict(label_settings.get("axis_labels") or {})),
        "fonts": copy.deepcopy(dict(label_settings.get("fonts") or {})),
    }
    header = ("# Configuration for axis labels and fonts in ndX\n"
              "# axis_labels: visibility of labels; fonts: family and sizes\n\n")
    return (header + yaml.safe_dump(data, default_flow_style=False, sort_keys=False)) \
        .encode("utf-8")


def write_label_settings(path: Union[str, pathlib.Path], label_settings: Mapping[str, Any]) -> None:
    """Write an ``axis_labels.yaml``."""
    path = pathlib.Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(label_settings_bytes(label_settings))
