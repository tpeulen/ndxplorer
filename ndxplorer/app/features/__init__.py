"""Feature modules: how a part of ndXplorer plugs into the emtk app.

The core (:mod:`ndxplorer.app.frame` and friends) draws the window, the main
view and the menus. Everything else -- opening and saving, settings, the
selection tools, clustering and the analyses, overlays, playback and export --
is a *feature module* in this package: ``ndxplorer/app/features/<name>.py``,
its view specs in ``ndxplorer/app/features/<name>/``, its tests beside the
others. A feature never edits the core; it registers.

A module listed in :data:`FEATURES` defines ``create(app) -> Feature``, called
once per :class:`~ndxplorer.app.frame.NdxApp`. A module that does not exist yet
is skipped, so the list can name what is still being written.

The hooks (all optional; the base class does nothing):

``actions()``
    ``{action name: callable}``. Menu entries (:data:`ndxplorer.app.menus.MENUS`)
    and ``button_row`` buttons in the core specs name actions; an action that a
    feature provides is enabled, one nobody provides is drawn disabled. A
    feature may also provide *attributes* the core specs bind to -- see
    ``fields()``.
``available(action)``
    ``True``/``False`` to say whether one of *its* actions can run now, or
    ``None`` for "the default" (usable once data is loaded).
``fields()``
    ``{attribute: (getter, setter)}`` -- values a core spec binds to that the
    feature owns (``selected_cluster``, ``cluster_colours``).
``menu_entries()``
    ``[(path, entry)]`` -- extra menu rows, ``path`` a tuple of menu titles
    (``("File", "Save")``), ``entry`` a MENUS dict (``label``, ``action``,
    ``shortcut``, ``checkable``, ``checked``). Rows already in MENUS need no
    entry here: providing the action is enough.
``custom_sections()``
    ``{key: draw(section, model, state, width)}`` -- ``custom`` sections a
    core spec may contain (``{"type": "custom", "key": "playback"}``), drawn
    by the feature in their place.
``windows()``
    ``[(region, title, draw(box))]`` or ``[(region, title, draw(box), options)]``
    -- the feature's own windows, asked once when the app starts: the
    Parameters, Overlays, Equations and Gaussian Fit windows. Each is a sticky
    window of ``app.docks`` (:mod:`ndxplorer.app.docks`), docked at first as a
    tab of the left (``"left"``) or right (``"right"``) region; *title* is its
    identity. *options* are :class:`emtk.docking.DockWindow` attributes --
    ``{"visible": False}`` for one the View menu opens. Whether it is shown is
    ``app.docks`` state from then on: ``app.docks.focus(title)`` brings it to
    the front, ``app.docks.is_shown(title)`` says whether it is on screen.
``draw_windows()``
    Called every frame after the main window, inside the emtk frame: dialogs
    and tool windows. Return ``True`` while one is modal (the main window
    then takes no input).
``draw_plot(plot)``
    Called inside ``begin_plot``/``end_plot`` of ``"map"``, ``"xmarginal"``,
    ``"ymarginal"`` and ``"zmarginal"``, after the core's items: overlays in
    data coordinates (curves, Gaussian ellipses).
``plot_input(plot)``
    Called inside a plot before the core handles the pointer; return ``True``
    to consume it (a point-picking mode, a context menu, mask painting) so no
    rubber band starts.
``mask_terms()``
    ``{MaskState field: value}`` merged into the model's mask state:
    ``cluster_label``, ``slice_mask``/``slice_key``, and ``selections`` (a
    list *appended* to the gate table's).
``map_image(values)``
    Return an ``(ny, nx, 4)`` uint8 image to draw instead of the coloured
    histogram (cluster colours), or ``None``.
``on_data_changed()``
    The table was replaced or merged.
``on_z_select()``
    The z panel's "select" just turned the z range into a gate.
``files_dropped(paths)``
    Files or folders dropped on the window; return ``True`` to keep them (a
    drop onto a feature's window) instead of opening the first one.
``capture_ops()``
    ``{op name: fn(replay, step)}`` -- scenario steps the capture replay
    (:mod:`ndxplorer.app.capture`) should understand, beyond the core's. A
    handler that returns ``False`` passes the step on to the next feature and
    then the core.
``capture_actions()``
    ``{Qt action name: app action}`` -- the Qt menu actions a scenario's
    ``trigger``/``open`` steps name (``actionLoad_settings``), merged into
    :data:`ndxplorer.app.capture.ACTIONS`.
``animating()``
    ``True`` while the feature needs frames without input (playback, a
    ranking that streams results); the host keeps drawing.
``capture_targets()``
    ``{target: fn(replay) -> (x, y, w, h)}`` -- ``capture`` targets it can
    photograph (``"dialog:QFileDialog"``, ``"widget:pc.widgetSelection"``).
    ``None`` from ``fn`` means "not on screen now": the next feature, then
    the core, is asked.
"""

from __future__ import annotations

import importlib
import logging
from typing import Any, Callable, Dict, List, Optional, Tuple

__all__ = ["FEATURES", "Feature", "load_features"]

logger = logging.getLogger(__name__)

#: Feature modules, in the order their hooks run.
FEATURES: List[str] = [
    "io",
    "settings",
    "selection",
    "accurate_fret",
    "analysis",
    "overlays",
    "playback_export",
    "window",
]


class Feature:
    """Base class of a feature: every hook, doing nothing.

    Parameters
    ----------
    app : ndxplorer.app.frame.NdxApp
        The window. ``app.model`` is the :class:`~ndxplorer.app.model.ExplorerModel`,
        ``app.panel`` the spec model, ``app.plots`` the plot area.
    """

    name = "feature"

    def __init__(self, app) -> None:
        self.app = app

    def actions(self) -> Dict[str, Callable[[], Any]]:
        return {}

    def available(self, action: str) -> Optional[bool]:
        return None

    def fields(self) -> Dict[str, Tuple[Callable[[], Any], Callable[[Any], None]]]:
        return {}

    def menu_entries(self) -> List[tuple]:
        return []

    def custom_sections(self) -> Dict[str, Callable]:
        return {}

    def windows(self) -> List[tuple]:
        return []

    def draw_windows(self) -> bool:
        return False

    def draw_plot(self, plot: str) -> None:
        pass

    def plot_input(self, plot: str) -> bool:
        return False

    def mask_terms(self) -> Dict[str, Any]:
        return {}

    def map_image(self, values):
        return None

    def on_data_changed(self) -> None:
        pass

    def on_z_select(self) -> None:
        pass

    def files_dropped(self, paths) -> bool:
        return False

    def capture_ops(self) -> Dict[str, Callable]:
        return {}

    def capture_targets(self) -> Dict[str, Callable]:
        return {}

    def capture_actions(self) -> Dict[str, str]:
        return {}

    def animating(self) -> bool:
        return False


def load_features(app, names: Optional[List[str]] = None) -> List[Feature]:
    """Create every feature of :data:`FEATURES` that exists, for *app*.

    A module that is missing is skipped silently (it is still being written);
    one that fails to import or to create is logged and skipped, so one broken
    feature cannot take the window down.
    """
    features: List[Feature] = []
    for name in FEATURES if names is None else names:
        try:
            module = importlib.import_module(f"{__name__}.{name}")
        except ModuleNotFoundError as exc:
            if exc.name == f"{__name__}.{name}":
                continue
            logger.exception("feature %s failed to import", name)
            continue
        except Exception:  # noqa: BLE001 - one feature must not stop the app
            logger.exception("feature %s failed to import", name)
            continue
        create = getattr(module, "create", None)
        if not callable(create):
            logger.warning("feature module %s has no create(app)", name)
            continue
        try:
            features.append(create(app))
        except Exception:  # noqa: BLE001
            logger.exception("feature %s failed to start", name)
    return features
