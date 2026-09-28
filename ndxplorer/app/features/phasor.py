"""The Phasor / FRET panel: ChiSurf's phasor geometry and FRET lines on the map.

The Qt window had it as the "ChiSurf Phasor" toolbar (*Phasor / FRET…*,
*Clear*) and a dock (``ndxplorer/ui/phasor_panel.py``). Here it is the
*Phasor / FRET* window (View > Phasor / FRET…), a ``view.json`` form:

* **Phasor overlays** -- frequency, harmonic, reference lifetimes, donor τ0 and
  which sets to draw (universal semicircle, iso-lifetime grid, lifetime ticks,
  polar grid, FRET trajectory); *Draw overlays* / *Clear*;
* **FRET line** -- the FRET model, the swept parameter, its range and the
  number of points; *Draw FRET line*;
* **Derived columns** -- *τ φ/M columns* adds the apparent lifetimes computed
  from the g, s columns.

The geometry is computed by ChiSurf, over its RPC (``app.chisurf_rpc``, through
the chisurf-free :class:`ndxplorer.rpc.PhasorService` / ``LinesService``): the
window a ChiSurf host builds has an in-process client, ``--chisurf-rpc`` gives
a standalone one. Without a client the entries are disabled and the panel says
why. Line sets are kept in data coordinates and drawn over the map every frame,
so they follow a new histogram, zoom or bin count.
"""

from __future__ import annotations

import json
import logging
import pathlib
from typing import Any, Callable, Dict, List, Optional

import numpy as np

from . import Feature

__all__ = ["PhasorFeature", "PhasorPanel", "create", "WINDOW", "NO_RPC"]

logger = logging.getLogger(__name__)

SPEC = pathlib.Path(__file__).with_name("phasor") / "phasor.view.json"
#: The window's title (its identity in the docks and the View menu).
WINDOW = "Phasor / FRET"
#: Why the panel is off without ChiSurf.
NO_RPC = ("Needs ChiSurf, which computes the phasor geometry and the FRET lines: "
          "open ndX from ChiSurf, or start it with --chisurf-rpc HOST:PORT.")
#: Overlay sets: (panel attribute, ``phasor.overlays`` set name).
SETS = (("show_semicircle", "semicircle"), ("show_lifetime_grid", "lifetime_grid"),
        ("show_lifetime_ticks", "lifetime_ticks"), ("show_polar_grid", "polar_grid"),
        ("show_fret", "fret"))


def _axis_token(name: str) -> str:
    """A column name's leading token (``"g (win)"`` -> ``"g"``)."""
    return str(name).strip().lower().split(" ")[0].split("(")[0].strip()


class PhasorPanel:
    """What the form reads and writes, and its buttons."""

    def __init__(self, feature: "PhasorFeature") -> None:
        from emtk.view_form import FormState

        self.feature = feature
        self.form = FormState()
        self.frequency = 80.0
        self.harmonic = 1
        self.lifetimes = "0.5, 1, 2, 4, 8"
        self.tau_d0 = 4.0
        self.show_semicircle = True
        self.show_lifetime_grid = True
        self.show_lifetime_ticks = True
        self.show_polar_grid = False
        self.show_fret = False
        self.fret_model = ""
        self.sweep_param = ""
        self.sweep_min = 20.0
        self.sweep_max = 90.0
        self.points = 50
        self._models: Optional[List[str]] = None
        self._targets: Dict[str, List[str]] = {}

    # -- what the form asks ----------------------------------------------------
    @property
    def reason(self) -> str:
        return self.feature.reason()

    @property
    def usable(self) -> bool:
        return not self.feature.reason()

    def enabled(self, _name: str) -> bool:
        return self.usable

    def fret_models(self) -> List[str]:
        """The FRET models ChiSurf offers (asked once)."""
        if self._models is None and self.usable:
            try:
                self._models = [str(m) for m in self.feature.lines().fret_line.list_models()]
            except Exception as exc:  # noqa: BLE001 - said in the status line
                self._models = []
                self.feature.app.show_status(f"Could not list the FRET models: {exc}")
            if self._models and not self.fret_model:
                self.fret_model = self._models[0]
        return list(self._models or [])

    def sweep_params(self) -> List[str]:
        """The parameters of the chosen model that a FRET line can sweep."""
        model = self.fret_model or (self.fret_models() or [""])[0]
        if not model or not self.usable:
            return []
        if model not in self._targets:
            try:
                targets = self.feature.lines().fret_line.list_sweep_targets(self._components())
            except Exception as exc:  # noqa: BLE001
                targets = []
                self.feature.app.show_status(f"Could not list the sweep parameters: {exc}")
            self._targets[model] = [str(t.get("name", t) if isinstance(t, dict) else t)
                                    for t in targets]
        names = self._targets[model]
        if names and self.sweep_param not in names:
            self.sweep_param = names[0]
        return list(names)

    def fret_model_changed(self, _value) -> None:
        self.sweep_param = ""

    def _components(self) -> List[dict]:
        return [{"model_name": self.fret_model, "n_components": 1, "params": {}}]

    def taus(self) -> Optional[List[float]]:
        out = []
        for token in str(self.lifetimes).replace(";", ",").split(","):
            try:
                out.append(float(token))
            except ValueError:
                continue
        return out or None

    # -- buttons ---------------------------------------------------------------
    def draw_overlays(self) -> None:
        self.feature.draw_overlays()

    def clear_overlays(self) -> None:
        self.feature.clear()

    def draw_fret_line(self) -> None:
        self.feature.draw_fret_line()

    def lifetime_columns(self) -> None:
        self.feature.lifetime_columns()


class PhasorFeature(Feature):
    """The Phasor / FRET window and the line sets it draws on the map."""

    name = "phasor"

    def __init__(self, app) -> None:
        super().__init__(app)
        self.panel = PhasorPanel(self)
        #: tag ("phasor", "fret") -> LineSet (``[{kind, x, y, style, labels}]``).
        self.line_sets: Dict[str, List[dict]] = {}
        self._services: tuple = (None, None, None)
        with open(SPEC, encoding="utf-8") as handle:
            self.spec = json.load(handle)

    # -- ChiSurf ----------------------------------------------------------------
    def reason(self) -> str:
        """Why the panel cannot work here (``""`` when it can)."""
        return "" if getattr(self.app, "chisurf_rpc", None) is not None else NO_RPC

    def _clients(self):
        rpc = getattr(self.app, "chisurf_rpc", None)
        if self._services[0] is not rpc:
            from ...rpc import LinesService, PhasorService

            self._services = (rpc, PhasorService(rpc), LinesService(rpc))
            self.panel._models, self.panel._targets = None, {}
        return self._services

    def phasor(self):
        return self._clients()[1]

    def lines(self):
        return self._clients()[2]

    # -- actions ---------------------------------------------------------------
    def show_panel(self) -> None:
        self.app.docks.focus(WINDOW)

    def draw_overlays(self) -> None:
        p = self.panel
        x, y = self.app.model.x.name, self.app.model.y.name
        if (_axis_token(x), _axis_token(y)) != ("g", "s"):
            self.app.show_status("Set the plot axes to (g, s) to show phasor overlays")
            return
        sets = [name for attr, name in SETS if getattr(p, attr)]
        if not sets:
            self.app.show_status("Select at least one overlay set")
            return
        self._fetch("phasor", "Phasor overlays", lambda: self.phasor().overlays(
            float(p.frequency), sets=sets, harmonic=int(p.harmonic), taus=p.taus(),
            tau_d0=float(p.tau_d0)))

    def draw_fret_line(self) -> None:
        p = self.panel
        if not p.sweep_param:
            self.app.show_status("Pick a sweep parameter for the FRET line")
            return
        self._fetch("fret", "FRET line", lambda: self.lines().fret_line.overlays(
            components=p._components(),
            sweep={"kind": "param", "component": 0, "name": p.sweep_param},
            param_min=float(p.sweep_min), param_max=float(p.sweep_max),
            n_points=int(p.points)))

    def _fetch(self, tag: str, what: str, call: Callable[[], list]) -> None:
        try:
            overlays = list(call() or [])
        except Exception as exc:  # noqa: BLE001 - said, not raised
            logger.warning("%s failed", what, exc_info=True)
            self.app.show_status(f"{what} failed: {exc}")
            return
        self.line_sets[tag] = overlays
        self.app.show_status(f"{what}: {len(overlays)} item(s)")

    def clear(self) -> None:
        self.line_sets.clear()
        self.app.show_status("Cleared the ChiSurf overlays")

    def lifetime_columns(self) -> None:
        """Add τ_φ and τ_M, computed by ChiSurf from the g and s columns."""
        model = self.app.model
        if not model.has_data:
            return
        columns = {_axis_token(n): n for n in reversed(model.source.parameter_names)}
        if "g" not in columns or "s" not in columns:
            self.app.show_status("No g / s columns for τ_φ / τ_M")
            return
        source = model.source
        try:
            tau_phi, tau_m = self.phasor().apparent_lifetime(
                source.column_values(columns["g"]), source.column_values(columns["s"]),
                float(self.panel.frequency))
        except Exception as exc:  # noqa: BLE001
            self.app.show_status(f"τ φ/M failed: {exc}")
            return
        for name, values in (("tau_phi", tau_phi), ("tau_m", tau_m)):
            source.set_column(name, np.asarray(values, dtype=float))
        model.invalidate()
        for feature in self.app.features:
            if feature is not self:
                feature.on_data_changed()
        self.app.show_status("Added columns: tau_phi, tau_m")

    # -- hooks -----------------------------------------------------------------
    def actions(self) -> Dict[str, Callable[[], Any]]:
        return {"show_phasor_panel": self.show_panel,
                "clear_phasor_overlays": self.clear}

    def available(self, action: str) -> Optional[bool]:
        if action == "show_phasor_panel":
            return not self.reason()
        if action == "clear_phasor_overlays":
            return bool(self.line_sets)
        return None

    def menu_entries(self) -> List[tuple]:
        return [(("View",), None),
                (("View",), {"label": "Phasor / FRET…", "action": "show_phasor_panel",
                             "description": "Phasor overlays, FRET lines and apparent-"
                                            "lifetime columns, computed by ChiSurf."}),
                (("View",), {"label": "Clear phasor overlays",
                             "action": "clear_phasor_overlays",
                             "description": "Remove the phasor overlays and FRET lines "
                                            "from the map."})]

    def windows(self) -> List[tuple]:
        # Beside Parameters and Overlays, so the map it draws on stays in view.
        return [("left", WINDOW, self._draw_panel, {"visible": False})]

    def _draw_panel(self, _box) -> None:
        from emtk.view_form import draw_form

        draw_form(self.spec, self.panel, self.panel.form, titles=False)

    def draw_plot(self, plot: str) -> None:
        if plot != "map" or not self.line_sets:
            return
        from emtk import implot

        model = self.app.model
        for tag, overlays in self.line_sets.items():
            for i, overlay in enumerate(overlays):
                x = _plotted(overlay.get("x"), model.x.log)
                y = _plotted(overlay.get("y"), model.y.log)
                if x.size == 0 or x.size != y.size:
                    continue
                style = overlay.get("style") or {}
                colour = _rgba(style.get("color", "w"))
                if overlay.get("kind") == "scatter":
                    implot.plot_scatter(f"##{tag}-{i}", x, y, spec={
                        "marker_fill_color": colour, "marker_line_color": colour,
                        "marker_size": float(style.get("size", 4))})
                    implot.push_style_color(implot.COL_INLAY_TEXT, colour)
                    try:
                        for label, xi, yi in zip(overlay.get("labels") or [], x, y):
                            if np.isfinite(xi) and np.isfinite(yi):
                                implot.plot_text(str(label), float(xi), float(yi),
                                                 pix_offset=(10.0, -8.0))
                    finally:
                        implot.pop_style_color()
                else:
                    implot.plot_line(f"##{tag}-{i}", x, y, spec={
                        "line_color": colour, "line_weight": float(style.get("width", 1))})


def _plotted(values, log: bool) -> np.ndarray:
    """Data values as the map's axis shows them (log10 on a log axis)."""
    out = np.asarray(values if values is not None else [], dtype=float)
    if log:
        with np.errstate(divide="ignore", invalid="ignore"):
            out = np.where(out > 0, np.log10(out), np.nan)
    return out


def _rgba(colour: Any) -> tuple:
    """A LineSet colour (name, ``#hex`` or an rgb tuple) as 0..1 RGBA."""
    names = {"w": "#ffffff", "white": "#ffffff", "k": "#000000", "black": "#000000",
             "r": "#ff0000", "red": "#ff0000", "g": "#00c000", "green": "#00c000",
             "b": "#3080ff", "blue": "#3080ff", "y": "#ffd000", "yellow": "#ffd000",
             "c": "#00d0d0", "cyan": "#00d0d0", "m": "#d000d0", "magenta": "#d000d0",
             "orange": "#ff8c00", "gray": "#a0a0a0", "grey": "#a0a0a0"}
    if isinstance(colour, (tuple, list)):
        values = [float(c) / (255.0 if any(float(v) > 1 for v in colour) else 1.0)
                  for c in colour]
        return tuple((values + [1.0])[:4])
    text = names.get(str(colour).lower(), str(colour))
    if text.startswith("#") and len(text) in (7, 9):
        parts = [int(text[i:i + 2], 16) / 255.0 for i in range(1, len(text), 2)]
        return tuple((parts + [1.0])[:4])
    return (1.0, 1.0, 1.0, 1.0)


def create(app) -> PhasorFeature:
    return PhasorFeature(app)
