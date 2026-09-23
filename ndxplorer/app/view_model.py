"""The panels' model: what the ``view.json`` specs read, write and call.

AutoForm binds a spec to flat attributes and methods -- ``x_bins_1d``,
``auto_x``, ``enabled(name)``. :class:`PanelModel` is that surface over
:class:`~ndxplorer.app.model.ExplorerModel`, whose state is grouped (three
:class:`~ndxplorer.app.model.AxisState` objects, a gate list). Every write goes
through the explorer model, which marks itself for a recompute.

Actions the app has not ported yet exist as names in :data:`NOT_PORTED`, so a
button for them is drawn and disabled rather than missing.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from .model import ExplorerModel

__all__ = ["PanelModel", "NOT_PORTED"]

#: Buttons and menu entries whose feature the emtk app does not have yet.
NOT_PORTED = frozenset({
    "screenshot", "show_data", "export_figure", "cluster", "save_burst_ids", "load_gates",
    "save_gates", "selected_cluster", "cluster_colours",
    "save_histograms", "make_report", "print_window", "performance_settings", "load_settings",
    "save_axis_settings", "save_constants", "save_equations", "set_default_axis",
    "toggle_parameters", "toggle_overlays", "toggle_fit_gaussians", "toggle_equations", "umap",
    "find_projections", "find_z_projections", "axis_control", "help",
    "about", "update_app", "z_bins_2d",
})

#: What a field a feature owns shows until the feature is there (the Qt
#: window's initial values): the cluster spin box reads -1, "all clusters".
FIELD_DEFAULTS = {"selected_cluster": -1, "cluster_colours": False}

#: What stays usable without data: opening something, and leaving.
WITHOUT_DATA = frozenset({"open_text", "open_analysis_folder", "open_analysis_file",
                          "open_sampling", "browse", "working_path", "colormap", "exit",
                          "toggle_plot_controls"})


def _axis_property(key: str, field: str, cast: Callable[[Any], Any]):
    def get(self):
        return getattr(self.model.axis(key), field)

    def set_(self, value):
        axis = self.model.axis(key)
        value = cast(value)
        if getattr(axis, field) == value:
            return
        setattr(axis, field, value)
        if key == "z" and field in ("lo", "hi"):
            self.model._fit_z_range()
        self.model.invalidate()

    return property(get, set_)


class PanelModel:
    """AutoForm's view of an :class:`ExplorerModel`.

    Parameters
    ----------
    model : ExplorerModel
    actions : dict, optional
        Extra actions the host provides (``browse`` opens its file dialog,
        ``exit`` closes its window), by name.
    """

    def __init__(self, model: ExplorerModel, actions: Optional[Dict[str, Callable]] = None) -> None:
        self.model = model
        self.actions: Dict[str, Callable] = dict(actions or {})
        #: ``{attribute: (getter, setter)}`` the features own (see ``features``).
        self.fields: Dict[str, tuple] = {}
        #: ``availability(action) -> bool | None``: what a feature says first.
        self.availability: Optional[Callable[[str], Optional[bool]]] = None
        self.show_plot_controls = True

    # ------------------------------------------------------------- enabling
    def available(self, name: str) -> bool:
        """Whether *name* (a field, a button, a menu action) can be used now.

        A feature that provides *name* answers first; an action that no one
        provides is drawn disabled.
        """
        if self.availability is not None and (name in self.actions or name in self.fields):
            answer = self.availability(name)
            if answer is not None:
                return answer
        if name in self.actions or name in self.fields:
            return name in WITHOUT_DATA or self.model.has_data
        if name in NOT_PORTED:
            return False
        if name in WITHOUT_DATA:
            return True
        if name in self.actions or hasattr(self, name) or hasattr(type(self), name):
            return self.model.has_data
        return False

    def enabled(self, name: str) -> bool:
        """AutoForm's hook: a field or action that cannot be used is drawn disabled."""
        if name in self.actions or name in self.fields:
            return self.available(name)
        if name.startswith(("x_", "y_", "z_", "weight")) or name in NOT_PORTED:
            if name in NOT_PORTED:
                return False
            return self.model.has_data
        return self.available(name)

    # ----------------------------------------------------------------- axes
    def parameter_options(self) -> List[str]:
        return self.model.parameter_options()

    def colormap_options(self) -> List[str]:
        return self.model.colormap_options()

    @property
    def x_name(self) -> str:
        return self.model.x.name

    @x_name.setter
    def x_name(self, name: str) -> None:
        self.model.set_parameter("x", str(name))

    @property
    def y_name(self) -> str:
        return self.model.y.name

    @y_name.setter
    def y_name(self, name: str) -> None:
        self.model.set_parameter("y", str(name))

    @property
    def z_name(self) -> str:
        return self.model.z.name

    @z_name.setter
    def z_name(self, name: str) -> None:
        self.model.set_parameter("z", str(name))

    x_bins_1d = _axis_property("x", "bins_1d", lambda v: max(1, int(v)))
    x_bins_2d = _axis_property("x", "bins_2d", lambda v: max(1, int(v)))
    y_bins_1d = _axis_property("y", "bins_1d", lambda v: max(1, int(v)))
    y_bins_2d = _axis_property("y", "bins_2d", lambda v: max(1, int(v)))
    z_bins_1d = _axis_property("z", "bins_1d", lambda v: max(1, int(v)))
    z_bins_2d = _axis_property("z", "bins_2d", lambda v: int(v))
    x_log = _axis_property("x", "log", bool)
    y_log = _axis_property("y", "log", bool)
    z_log = _axis_property("z", "log", bool)
    x_norm = _axis_property("x", "norm", bool)
    y_norm = _axis_property("y", "norm", bool)
    z_norm = _axis_property("z", "norm", bool)
    x_auto_scale = _axis_property("x", "auto_scale", bool)
    y_auto_scale = _axis_property("y", "auto_scale", bool)
    z_auto_scale = _axis_property("z", "auto_scale", bool)
    x_min = _axis_property("x", "lo", float)
    x_max = _axis_property("x", "hi", float)
    y_min = _axis_property("y", "lo", float)
    y_max = _axis_property("y", "hi", float)
    z_min = _axis_property("z", "lo", float)
    z_max = _axis_property("z", "hi", float)

    def auto_x(self) -> None:
        self.model.auto_range("x")

    def auto_y(self) -> None:
        self.model.auto_range("y")

    def auto_z(self) -> None:
        self.model.auto_range("z")

    def set_x_axis(self) -> None:
        self.model.remember_axis("x")

    def set_y_axis(self) -> None:
        self.model.remember_axis("y")

    def set_z_axis(self) -> None:
        self.model.remember_axis("z")

    # --------------------------------------------------------------- weight
    @property
    def weight_enabled(self) -> bool:
        return self.model.weight_enabled

    @weight_enabled.setter
    def weight_enabled(self, value: bool) -> None:
        if bool(value) != self.model.weight_enabled:
            self.model.weight_enabled = bool(value)
            self.model.invalidate()

    @property
    def weight_name(self) -> str:
        return self.model.weight_name

    @weight_name.setter
    def weight_name(self, value: str) -> None:
        if value != self.model.weight_name:
            self.model.weight_name = str(value)
            if self.model.weight_enabled:
                self.model.invalidate()

    # -------------------------------------------------------------------- z
    @property
    def z_gate_enabled(self) -> bool:
        return self.model.z_gate_enabled

    @z_gate_enabled.setter
    def z_gate_enabled(self, value: bool) -> None:
        self.model.z_gate_enabled = bool(value)
        self.model.invalidate()

    @property
    def z_dynamic(self) -> bool:
        return self.model.z_dynamic

    @z_dynamic.setter
    def z_dynamic(self, value: bool) -> None:
        self.model.z_dynamic = bool(value)
        self.model.invalidate()

    def z_select(self) -> None:
        self.model.z_select()

    # ---------------------------------------------------------------- gates
    def gate_rows(self) -> List[dict]:
        rows = self.model.gate_records()
        # The table is refreshed when the source object changes: hand it a new
        # list only when the gates did.
        token = tuple(tuple(sorted(r.items())) for r in rows)
        if getattr(self, "_gate_token", None) != token:
            self._gate_token = token
            self._gate_rows = rows
        return self._gate_rows

    def edit_gate(self, record, key: str, value) -> None:
        self.model.edit_gate(int(record["row"]), key, value)

    def delete_gate(self, record) -> None:
        self.model.remove_gate(int(record["row"]))

    def select_gate(self, record) -> None:
        self.model.selected_gate = None if record is None else int(record["row"])

    def clear_gates(self) -> None:
        self.model.clear_gates()

    # ------------------------------------------------------- colour and mask
    @property
    def colormap(self) -> str:
        return self.model.colormap

    @colormap.setter
    def colormap(self, name: str) -> None:
        self.model.colormap = str(name)

    @property
    def log_counts(self) -> bool:
        return self.model.log_counts

    @log_counts.setter
    def log_counts(self, value: bool) -> None:
        self.model.log_counts = bool(value)
        self.model.invalidate()

    @property
    def vmin(self) -> float:
        return self.model.vmin

    @vmin.setter
    def vmin(self, value: float) -> None:
        self.model.vmin = float(value)

    @property
    def vmax(self) -> float:
        return self.model.vmax

    @vmax.setter
    def vmax(self, value: float) -> None:
        self.model.vmax = float(value)

    @property
    def mask_inf(self) -> bool:
        return self.model.mask_inf

    @mask_inf.setter
    def mask_inf(self, value: bool) -> None:
        self.model.mask_inf = bool(value)
        self.model.invalidate()

    @property
    def mask_nan(self) -> bool:
        return self.model.mask_nan

    @mask_nan.setter
    def mask_nan(self, value: bool) -> None:
        self.model.mask_nan = bool(value)
        self.model.invalidate()

    @property
    def count_current(self) -> int:
        return self.model.count_current if self.model.has_data else ""

    @count_current.setter
    def count_current(self, _value) -> None:
        pass

    @property
    def count_total(self) -> int:
        return self.model.count_total if self.model.has_data else ""

    @count_total.setter
    def count_total(self, _value) -> None:
        pass

    def update_plots(self) -> None:
        self.model.invalidate()

    def auto_contrast(self) -> None:
        self.model.auto_contrast()

    def clear_plot(self) -> None:
        self.model.clear()

    # ------------------------------------------------------------- the path
    @property
    def working_path(self) -> str:
        return self.model.working_path

    @working_path.setter
    def working_path(self, value: str) -> None:
        self.model.working_path = str(value)

    # ------------------------------------------------ actions the host owns
    def __getattr__(self, name: str):
        fields = self.__dict__.get("fields", {})
        if name in fields:
            return fields[name][0]()
        if name in FIELD_DEFAULTS:
            return FIELD_DEFAULTS[name]
        actions = self.__dict__.get("actions", {})
        if name in actions:
            return actions[name]
        raise AttributeError(name)

    def __setattr__(self, name: str, value) -> None:
        fields = self.__dict__.get("fields")
        if fields and name in fields:
            fields[name][1](value)
            return
        object.__setattr__(self, name, value)
