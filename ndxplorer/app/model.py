"""What the emtk app shows, as plain data, and the computation behind it.

:class:`ExplorerModel` holds the loaded table, the three axes, the gate list,
the colour settings and the histograms computed from them. It knows nothing
about drawing: the frame (:mod:`ndxplorer.app.frame`) reads it and calls its
methods, and a test drives it the same way without a window.

It is also the *model* the panels' ``view.json`` specs bind to, in AutoForm's
sense: a ``value`` section reads and writes an attribute (``x_bins_1d``), a
``choice`` reads ``options_source`` (``parameter_names``), a button calls a
method (``auto_x``), and :meth:`enabled` says which controls are usable.

Every computation is the one the Qt window uses -- the reader, the data
manager's mask, :func:`~ndxplorer.utils.histogram_computation.compute_histograms`,
:mod:`ndxplorer.core.gates`, the colour limits in
:mod:`ndxplorer.core.histograms`. The model only decides *when*: a change marks
it dirty, and the next frame recomputes once, however many changes arrived.
That is the Qt window's 40 ms request batching, without a timer.
"""

from __future__ import annotations

import math
import os
import pathlib
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

import numpy as np

from ..core.data import DataManager, MaskState
from ..core.data_source import DataSource
from ..core.gates import GateList
from ..core.histograms import auto_contrast_limits, colour_limits, display_counts
from ..logging_config import logging
from ..utils.axis_helpers import robust_axis_range, settings_for_axis
from ..utils.histogram_computation import Axis, HistogramAxes, compute_histograms

__all__ = ["AxisState", "ExplorerModel", "Histograms", "find_parameter", "read_path"]

#: What the Qt window's axis spin boxes start at.
DEFAULT_BINS_1D = 81
DEFAULT_BINS_2D = 31


@dataclass
class AxisState:
    """One axis of the plot: which parameter, and how it is binned and scaled.

    Attributes
    ----------
    name : str
        The parameter shown; ``""`` before data is loaded.
    bins_1d, bins_2d : int
        Bins of the marginal and of the 2-D map (z has no 2-D bins).
    lo, hi : float
        The range.
    log : bool
        Logarithmic axis.
    norm : bool
        Marginal drawn as a normalised density.
    auto_scale : bool
        Auto-range the axis when its parameter changes and the axis settings
        do not describe it (the Qt window's third check box).
    """

    name: str = ""
    bins_1d: int = DEFAULT_BINS_1D
    bins_2d: int = DEFAULT_BINS_2D
    lo: float = 0.0
    hi: float = 1.0
    log: bool = False
    norm: bool = False
    auto_scale: bool = True

    @property
    def scale(self) -> str:
        return "log" if self.log else "lin"


@dataclass
class Histograms:
    """The histograms one recompute produced.

    ``H`` is ``(n_y, n_x)``, row 0 at the *lowest* y -- the orientation
    :func:`compute_histograms` returns.
    """

    x: Tuple[np.ndarray, np.ndarray]
    y: Tuple[np.ndarray, np.ndarray]
    H: np.ndarray
    x_edges: np.ndarray
    y_edges: np.ndarray
    z: Optional[Tuple[np.ndarray, np.ndarray]] = None
    count: int = 0
    revision: int = 0


def find_parameter(names: Sequence[str], wanted: str, contains: bool = False) -> Optional[str]:
    """The parameter called *wanted* -- exactly (ignoring case), or containing it.

    The Qt window's ``set_axis_by_name``: an exact match first, a substring
    match when *contains*.
    """
    if not wanted:
        return None
    for name in names:
        if name == wanted:
            return name
    low = wanted.lower()
    for name in names:
        if name.lower() == low:
            return name
    if contains:
        for name in names:
            if low in name.lower():
                return name
    return None


def read_path(path: str) -> DataSource:
    """Read a file or folder the way the Qt window's ``--file`` and drop path do.

    A folder is a burst-analysis folder (or a sampling folder with a
    ``parameters.json``); ``.csv``/``.dat``/``.txt``/``.bur`` are text tables;
    ``.er4`` is ChiSurf sampling; ``.h5``/``.hdf5``/``.zip`` an analysis file;
    ``.pto`` a measurement container.
    """
    from ..io import reader

    p = pathlib.Path(path)
    if p.is_dir():
        if (p / "parameters.json").exists():
            return reader.read_sampling_folder(str(p))
        return reader.read_burst_analysis(str(p))
    suffix = p.suffix.lower()
    if suffix == ".er4":
        return reader.read_csv_sampling([str(p)])
    if suffix in (".h5", ".hdf5", ".zip"):
        return reader.read_mfd_hdf5([str(p)])
    if suffix == ".pto":
        return reader.read_burst_analysis(str(p))
    return reader.read_csv([str(p)])


class ExplorerModel:
    """The state of one ndXplorer window, and the histograms it implies.

    Parameters
    ----------
    settings_file : str or Path, optional
        The ``*.settings.json`` (default: the user's, seeded from the packaged
        one) -- axis settings, default axes, equations and constants.
    """

    def __init__(self, settings_file=None) -> None:
        from ..settings.bundle import read_settings

        self.bundle = read_settings(settings_file)
        self.axis_settings: Dict[str, dict] = dict(self.bundle.axis_settings)
        self.manager = DataManager()
        self.manager.constants = dict(self.bundle.constants)
        self.manager.equations = list(self.bundle.equations or [])
        self.source: Optional[DataSource] = None
        self.path: str = ""
        self.working_path: str = ""
        self.error: str = ""

        self.x = AxisState()
        self.y = AxisState()
        self.z = AxisState(bins_2d=0)
        self.weight_enabled = False
        self.weight_name = ""
        colormap = str(self.bundle.settings.get("colormap", "viridis"))
        from ..plotting.colormap_lut import available_colormaps

        # The Qt window falls back to viridis when the settings name a map it
        # does not have (the shipped settings say gist_earth).
        self.colormap = colormap if colormap in available_colormaps() else "viridis"
        self.log_counts = False
        self.vmin = 0.0
        self.vmax = 1.0
        self.mask_inf = True
        self.mask_nan = True
        #: "dynamic z-selection": the z range gates the other plots.
        self.z_gate_enabled = False
        #: The Qt window's second switch for the same gate ("dynamic").
        self.z_dynamic = False
        self.z_range: Tuple[float, float] = (0.0, 1.0)
        self._z_range_for: Optional[tuple] = None
        #: The Selection table: every gate, of every kind (intervals, 2-D
        #: Gaussians, drawn regions, painted masks).
        self.gates = GateList()
        self.selected_gate: Optional[int] = None
        #: The window, when there is one: its features take part in the mask.
        self.app = None

        self.histograms: Optional[Histograms] = None
        self._dirty = True
        self._revision = 0

    # ------------------------------------------------------------------ data
    @property
    def has_data(self) -> bool:
        return self.source is not None and not self.source.empty

    @property
    def parameter_names(self) -> List[str]:
        return list(self.source.parameter_names) if self.has_data else []

    def parameter_options(self) -> List[str]:
        """The axis choosers' entries."""
        return self.parameter_names

    def colormap_options(self) -> List[str]:
        from ..plotting.colormap_lut import available_colormaps

        return list(available_colormaps())

    def open(self, path: str) -> bool:
        """Read *path* and show it; ``False`` (and :attr:`error`) when it failed."""
        try:
            source = read_path(path)
        except Exception as exc:  # noqa: BLE001 - reported, not raised
            logging.error("Failed to load %s: %s", path, exc)
            self.error = f"Failed to load data: {exc}"
            return False
        if source is None or source.empty:
            self.error = f"No data in {path}"
            return False
        self.error = ""
        self.path = str(path)
        p = pathlib.Path(path)
        # The folder the data came from sits in, as the Qt window shows it:
        # the parent of an opened folder, the folder of an opened file.
        self.working_path = str(p.resolve().parent)
        self.set_source(source)
        return True

    def set_source(self, source: DataSource) -> None:
        """Show *source*: compute its equation columns, choose the axes, redraw."""
        self.manager.data_source = source          # computes the equation columns
        self.source = self.manager.data_source
        self.gates.clear()
        self.selected_gate = None
        self._apply_default_axes()
        self.invalidate()

    def clear(self) -> None:
        """The Clear button: no data, no gates, no working path."""
        self.source = None
        self.manager = DataManager()
        self.manager.constants = dict(self.bundle.constants)
        self.manager.equations = list(self.bundle.equations or [])
        self.path = ""
        self.working_path = ""
        self.gates.clear()
        self.selected_gate = None
        for axis in (self.x, self.y, self.z):
            axis.name = ""
        self.histograms = None
        self.invalidate()

    def _apply_default_axes(self) -> None:
        """Axes from the settings' ``default_axes``, else the first parameters."""
        names = self.parameter_names
        defaults = self.bundle.settings.get("default_axes") or {}
        for key, axis in (("x", self.x), ("y", self.y), ("z", self.z)):
            wanted = defaults.get(key)
            chosen = (find_parameter(names, wanted) or find_parameter(names, wanted, True)
                      if wanted else None)
            if chosen is None and axis.name not in names:
                chosen = names[0] if names else ""
            if chosen:
                axis.name = chosen
            self._setup_axis(axis, with_2d=key != "z")
        weight = defaults.get("weight")
        chosen = find_parameter(names, weight) or find_parameter(names, weight, True) \
            if weight else None
        self.weight_name = chosen or (self.weight_name if self.weight_name in names else
                                      (names[0] if names else ""))
        self._fit_z_range()

    def _setup_axis(self, axis: AxisState, with_2d: bool = True) -> None:
        """Bins, range and scale for the axis's parameter: settings, else auto."""
        setup = settings_for_axis(axis.name, self.axis_settings, with_2d=with_2d)
        if setup is None:
            axis.lo, axis.hi = self._auto_range(axis)
            return
        axis.bins_1d = int(setup["bins_1d"])
        if with_2d and setup["bins_2d"] is not None:
            axis.bins_2d = int(setup["bins_2d"])
        axis.log = str(setup["scale"]).lower().startswith("log")
        lo, hi = setup["min"], setup["max"]
        if lo is None or hi is None:
            auto = self._auto_range(axis)
            lo = auto[0] if lo is None else lo
            hi = auto[1] if hi is None else hi
        axis.lo, axis.hi = float(lo), float(hi)

    # ------------------------------------------------------------------ axes
    def axis(self, key: str) -> AxisState:
        return {"x": self.x, "y": self.y, "z": self.z}[key]

    def index_of(self, name: str) -> int:
        try:
            return self.parameter_names.index(name)
        except ValueError:
            return -1

    def _visible_values(self, index: int) -> np.ndarray:
        """Column *index* over the rows the gates keep (the Qt ``x_values``)."""
        if not self.has_data or index < 0:
            return np.empty(0)
        values = np.asarray(self.source.column_view(index), dtype=np.float64)
        keep = self._keep_mask()
        return values if keep is None else values[keep]

    def _auto_range(self, axis: AxisState) -> Tuple[float, float]:
        lo, hi = robust_axis_range(self._visible_values(self.index_of(axis.name)), axis.scale)
        return float(lo), float(hi)

    def set_parameter(self, key: str, name: str) -> None:
        """Show parameter *name* on axis *key*, set up as the Qt window does."""
        axis = self.axis(key)
        if name == axis.name:
            return
        axis.name = name
        self._setup_axis(axis, with_2d=key != "z")
        if key == "z":
            self._fit_z_range()
        self.invalidate()

    def auto_range(self, key: str) -> None:
        """The "Auto" button: the axis ranges to where its data is."""
        axis = self.axis(key)
        axis.lo, axis.hi = self._auto_range(axis)
        if key == "z":
            self._fit_z_range(force=True)
        self.invalidate()

    def remember_axis(self, key: str) -> None:
        """The "Set" button: this axis's settings become the parameter's default."""
        axis = self.axis(key)
        if not axis.name:
            return
        entry = {"n_bins_1d": float(axis.bins_1d), "min": float(axis.lo),
                 "max": float(axis.hi), "scale": axis.scale}
        if key != "z":
            entry["n_bins_2d"] = int(axis.bins_2d)
        self.axis_settings[axis.name] = entry

    def _fit_z_range(self, force: bool = False) -> None:
        """Put the z region over the whole z axis when it was set for another one."""
        token = (self.z.name, self.z.lo, self.z.hi)
        if force or self._z_range_for != token:
            self.z_range = (self.z.lo, self.z.hi)
            self._z_range_for = token

    def set_z_range(self, lo: float, hi: float) -> None:
        lo, hi = sorted((float(lo), float(hi)))
        self.z_range = (lo, hi)
        self._z_range_for = (self.z.name, self.z.lo, self.z.hi)
        if self.z_gate_active:
            self.invalidate()

    @property
    def z_gate_active(self) -> bool:
        return self.z_gate_enabled and self.z_dynamic and self.index_of(self.z.name) >= 0

    # ----------------------------------------------------------------- gates
    def add_rectangle(self, x_range, y_range) -> None:
        """A rectangle dragged on the map: an interval gate on x and one on y."""
        self.gates.add_rectangle(self.index_of(self.x.name), self.x.name, x_range,
                                 self.index_of(self.y.name), self.y.name, y_range)
        self.invalidate()

    def add_interval(self, name: str, lo: float, hi: float) -> None:
        self.gates.add_interval(self.index_of(name), name, lo, hi)
        self.invalidate()

    def z_select(self) -> None:
        """The z panel's "select": the z range becomes a gate."""
        if self.index_of(self.z.name) < 0:
            return
        self.add_interval(self.z.name, *self.z_range)

    def remove_gate(self, index: int) -> None:
        if self.gates.remove([index]):
            self.selected_gate = None
            self.invalidate()

    def clear_gates(self) -> None:
        self.gates.clear()
        self.selected_gate = None
        self.invalidate()

    def edit_gate(self, index: int, key: str, value: Any) -> None:
        """A cell of the gate table changed (see :meth:`GateList.edit`)."""
        if self.gates.edit(index, key, value):
            self.invalidate()

    def gate_records(self) -> List[dict]:
        """The gate table's rows, one record each, keyed by position."""
        return self.gates.records()

    # ------------------------------------------------------------ recompute
    def invalidate(self) -> None:
        """Something changed: recompute on the next :meth:`update`.

        Every recompute sets the colour limits afresh from the new map, as the
        Qt window's redraw does (its ``update_spinbox_limits``); Contrast and
        typed limits last until the next change.
        """
        self._dirty = True

    def mask_state(self) -> MaskState:
        """Every gating term, for the data manager (the Qt ``_collect_mask_state``)."""
        indices = (self.index_of(self.x.name), self.index_of(self.y.name),
                   self.index_of(self.z.name))
        state = MaskState(
            selections=self.gates.selections(),
            axis_indices=tuple(max(i, 0) for i in indices),
            mask_inf=self.mask_inf,
            mask_nan=self.mask_nan,
            z_range=tuple(self.z_range) if self.z_gate_active else None,
        )
        # The features' terms: a cluster to isolate, the playback slice, gates
        # of their own (see ndxplorer.app.features).
        for feature in getattr(getattr(self, "app", None), "features", ()):
            for key, value in feature.mask_terms().items():
                if key == "selections":
                    state.selections = list(state.selections) + list(value)
                else:
                    setattr(state, key, value)
        return state

    def _keep_mask(self) -> Optional[np.ndarray]:
        if not self.has_data:
            return None
        self.manager.mask_state = self.mask_state()
        mask = self.manager.get_value_mask()
        return None if mask is None else ~mask

    def histogram_axes(self) -> HistogramAxes:
        def axis(state: AxisState, bins: int) -> Axis:
            return Axis(index=self.index_of(state.name), bins=bins, lo=state.lo, hi=state.hi,
                        scale=state.scale, density=state.norm)

        weight = None
        if self.weight_enabled:
            index = self.index_of(self.weight_name)
            weight = index if index >= 0 else None
        z_index = self.index_of(self.z.name)
        return HistogramAxes(
            x=axis(self.x, self.x.bins_1d), y=axis(self.y, self.y.bins_1d),
            x2=axis(self.x, self.x.bins_2d), y2=axis(self.y, self.y.bins_2d),
            z=axis(self.z, self.z.bins_1d) if z_index >= 0 else None,
            weight=weight,
        )

    def ready(self) -> bool:
        return (self.has_data and self.index_of(self.x.name) >= 0
                and self.index_of(self.y.name) >= 0)

    def update(self) -> bool:
        """Recompute the histograms if anything changed. Returns whether it did."""
        if not self._dirty:
            return False
        self._dirty = False
        if not self.ready():
            self.histograms = None
            return True
        result = compute_histograms(self.source, self.histogram_axes(), keep=self._keep_mask())
        self._revision += 1
        H, x_edges, y_edges = result["2d"]
        self.histograms = Histograms(
            x=result["x"], y=result["y"], H=np.asarray(H), x_edges=np.asarray(x_edges),
            y_edges=np.asarray(y_edges), z=result.get("z"),
            count=int(result.get("_count", 0)), revision=self._revision)
        self.vmin, self.vmax = colour_limits(self.histograms.H, self.log_counts)
        return True

    def auto_contrast(self) -> None:
        """The Contrast button."""
        self.update()
        if self.histograms is not None:
            self.vmin, self.vmax = auto_contrast_limits(self.histograms.H, self.log_counts)

    def map_values(self) -> Optional[np.ndarray]:
        """What the 2-D map colours, ``(n_y, n_x)``, row 0 at the lowest y."""
        if self.histograms is None:
            return None
        return display_counts(self.histograms.H, self.log_counts)

    @property
    def count_total(self) -> int:
        return int(self.source.size) if self.has_data else 0

    @property
    def count_current(self) -> int:
        return self.histograms.count if self.histograms is not None else 0
