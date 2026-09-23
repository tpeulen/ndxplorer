from typing import Dict, List, Optional, Tuple
from pathlib import Path

from ..logging_config import logging

import os
import json
import yaml
import typing
import pathlib
import importlib.util

import numpy as np

# Delay imports of heavy libraries
hdbscan = None  # For clustering
KMeans = None   # For clustering
GaussianMixture = None  # For Gaussian Mixture Modeling
umap = None     # For dimensionality reduction
napari = None   # For image visualization in external viewer

from ..plotting.plot_control import SurfacePlotWidget
from ..ui.parameter_editor import ParameterEditor
from ..plotting.curve_overlay import CurveOverlayWidget, CurveEvaluator
from ..io import reader
from ..io import writer
from ..utils import axis_helpers
from ..utils import colormap_helpers
from ..utils import napari_helpers
from ..utils import screenshot_helpers
from ..utils import ui_helpers
from ..utils import working_path_helpers
from ..io import file_operations
from ..utils import histogram_helpers
from ..analysis import clustering_helpers
from ..analysis import pca_helpers, umap_helpers
from ..utils import settings_helpers
from ..settings import get_settings_path
from ..ui.clustering_dialog import ClusteringDialog
from ..ui.column_selection_dialog import ColumnSelectionDialog
from ..plotting import plot_umap
from ..analysis.clustering import ClusteringManager, ClusteringWorker
from ..widgets import ScientificSpinBox
from ..utils.mouse_event_filter import MouseEventFilter
from ..ui.axis_control_dialog import AxisControlDialog

# Import new modular plotting components
from ..plotting import api as plotting_api
from ..plotting import histograms as plot_histograms


from ..rpc import LinesService, PhasorService, RpcError, ZmqRpcClient

#: Backwards-compatible alias — the ad-hoc client was folded into the first-class
#: ``ndxplorer.rpc`` subsystem (PRD-56). Existing callers keep working.
StandaloneZmqClient = ZmqRpcClient

from ..plotting import scatter as plot_scatter
from ..plotting import colormaps as plot_colormaps
from ..analysis.umap_progress import UMAPProgressDialog

from ndxplorer.widgets.code_editor import CodeEditor
from ndxplorer.widgets.equation_editor import EquationEditor

from .data_source import DataSource, RectangularDataSelection, MaskDataSelection
from .data import DataManager

from qtpy import QtCore, uic
from qtpy import QtGui, QtWidgets
from qtpy.QtGui import QFont, QImage

from ..plotting.plot_helpers import (
    configure_dynamic_selection_controls,
    setup_histogram_plots,
    setup_histogram_spinboxes,
    setup_overlay_plot,
    setup_2d_histogram_plot,
    setup_plot_placeholders,
)
from ..core.data.mask_state import MaskState
from ..utils.histogram_export import (
    copy_1d_histograms,
    copy_2d_hist_csv,
    copy_2d_hist_json,
)
from ..ui.export_actions import save_burst_ids, save_clustering_data
from ..io.file_open_helpers import (
    open_sampling,
    open_csv,
    open_files,
    open_mfd_hdf5,
    open_pto,
    open_smfret,
    show_merge_dialog,
)
from ..plotting import plot_update_helpers
from ..utils.mask_drawing_integration import MaskDrawingIntegration


class NDXplorer(QtWidgets.QMainWindow):

    def invalidate_values_cache(self) -> None:
        """
        Manually clear the cached 'values'. Call this whenever something
        changes that would invalidate the mask or the data.
        """
        logging.debug("Invalidating values cache")
        self.data_manager.cache.invalidate_all()
        self._cached_hist_params = None

    @property
    def data_source(self) -> DataSource:
        """The data currently loaded, owned by the data manager.

        There is exactly one of these. An earlier refactor left a second,
        private ``_data_source`` field behind as a "backward compatible" copy;
        because the manager took over, that copy stayed permanently empty while
        several call sites still read and wrote it. Clustering and UMAP saw zero
        rows, and appending a file wrote the new data into the dead copy and
        silently changed nothing. The field is gone -- this property is the only
        way in or out.
        """
        return self.data_manager.data_source

    @data_source.setter
    def data_source(self, v: DataSource) -> None:
        logging.info(f"Setting data_source with {v.values.shape[1] if not v.empty else 0} data points")
        self.data_manager.constants = self.constants
        self.data_manager.equations = self.equations
        self.data_manager.data_source = v
        
        self._set_data_loaded(not v.empty)

    def _set_data_loaded(self, has_data: bool) -> None:
        has_data = bool(has_data)
        self._has_real_data = has_data
        stack = getattr(self, "_plot_stack_widget", None)
        bg_label = getattr(self, "_background_label", None)
        plot_container = getattr(self, "_plot_container", None)
        if stack is not None and bg_label is not None and plot_container is not None:
            target = plot_container if has_data else bg_label
            other = bg_label if has_data else plot_container
            try:
                stack.setCurrentWidget(target)
                target.setVisible(True)
                other.setVisible(False)
            except Exception:
                pass
        try:
            if has_data:
                plot_update_helpers._hide_background(self)
            else:
                plot_update_helpers._show_background(self)
        except Exception:
            pass

    def _setup_axis_toolbar_actions(self) -> None:
        """Hide the consolidated axis toolbar row.

        The Set/Auto axis controls now live as per-axis buttons next to each axis
        (restored in ``PlotControl``), so the single consolidated "Axis | Set X |
        Auto X | …" toolbar row is no longer needed. Hide the toolbar rather than
        populate it.
        """
        toolbar = getattr(self, "toolBar", None)
        if toolbar is None:
            return
        toolbar.setObjectName("ndxplorerMainToolbar")
        toolbar.clear()
        toolbar.setVisible(False)

    @property
    def x_values(self) -> np.ndarray:
        """The x-axis values of the visible points, gating applied."""
        self.data_manager.mask_state = self._collect_mask_state()
        return self.data_manager.get_axis_values(
            'x', self.plot_control.p1[0], use_filtered=True
        )

    @property
    def y_values(self) -> np.ndarray:
        """The y-axis values of the visible points, gating applied."""
        self.data_manager.mask_state = self._collect_mask_state()
        return self.data_manager.get_axis_values(
            'y', self.plot_control.p2[0], use_filtered=True
        )

    @property
    def z_values(self) -> np.ndarray:
        """The z-axis values of the visible points, gating applied."""
        self.data_manager.mask_state = self._collect_mask_state()
        return self.data_manager.get_axis_values(
            'z', self.plot_control.p3[0], use_filtered=True
        )

    @property
    def weight_enabled(self) -> bool:
        """
        Get the current weight enabled status.
        
        Returns:
            bool: True if weighting is enabled, False otherwise
        """
        return self.current_weight_enabled
        
    @weight_enabled.setter
    def weight_enabled(self, value: bool) -> None:
        """
        Set the weight enabled status.
        
        Args:
            value: Boolean indicating whether weighting should be enabled
        """
        self.current_weight_enabled = bool(value)
        # Update the UI to match
        self.checkBoxWeight.setChecked(self.current_weight_enabled)
        
    @property
    def weight_param(self) -> str:
        """
        Get the current weight parameter.
        
        Returns:
            str: The name of the current weight parameter, or "None" if weighting is disabled
        """
        return self.current_weight_param
        
    @weight_param.setter
    def weight_param(self, value: str) -> None:
        """
        Set the weight parameter.
        
        Args:
            value: The name of the parameter to use for weighting
        """
        if not isinstance(value, str):
            return
            
        self.current_weight_param = value
        
        # Update the UI to match if the parameter exists
        if self.current_weight_param != "None":
            index = self.comboBoxWeight.findText(self.current_weight_param)
            if index >= 0:
                self.comboBoxWeight.setCurrentIndex(index)
    
    def _collect_mask_state(self) -> MaskState:
        """Gather every gating term the widgets hold into one Qt-free value.

        This is the *only* place that reads the GUI to decide which points are
        visible. Everything downstream -- the mask, the filtered values, the axis
        slices, the histograms -- works from the object returned here, so there
        is exactly one answer to "what is shown" instead of one per consumer.
        """
        control = self.plot_control

        # Dynamic z-selection only applies while the z axis is actually on; the
        # slider keeps its last range when the group box is unchecked, and
        # honouring it then would silently delete points along an axis the user
        # cannot see.
        z_enabled = hasattr(self, "checkBoxEnableZ") and self.checkBoxEnableZ.isChecked()
        z_range = None
        if self._dynamic_selection and z_enabled and hasattr(self, "selection_z"):
            # Here, at the point of use, because this is the one place the
            # region is read and it can be stale from any number of routes: a
            # new z parameter chosen without pressing update, a restored
            # session, a reloaded file with different units.
            self.fit_z_selection_to_axis()
            z_range = tuple(self.selection_z.get_range())
            self._last_z_range = z_range

        selected_cluster = control.selected_cluster
        cluster_label = (
            selected_cluster if self._use_clustering and selected_cluster >= 0 else None
        )

        # The playback slice: which column and which step are chosen in the
        # control, so the mask is built there and travels as a plain array
        # alongside the scalars it was built from.
        playback = getattr(control, "playback", None)
        slice_mask = playback.mask(self.data_source) if playback is not None else None
        slice_key = playback.slice_key() if playback is not None else None

        return MaskState(
            selections=control.get_selections(),
            axis_indices=(control.p1[0], control.p2[0], control.p3[0]),
            mask_inf=self._mask_inf,
            mask_nan=self._mask_nan,
            z_range=z_range,
            cluster_label=cluster_label,
            slice_mask=slice_mask,
            slice_key=slice_key,
        )

    @property
    def value_mask(self) -> np.ndarray:
        """Points excluded by the current gating, over the full-length data.

        ``True`` means excluded. Length always matches the raw data, so callers
        can turn it into row indices -- the background histogram path does
        exactly that.
        """
        self.data_manager.mask_state = self._collect_mask_state()
        return self.data_manager.get_value_mask()

    @property
    def values(self) -> np.ndarray:
        """The visible points as ``(n_params, n_visible)``.

        Everything gating implies has already been applied: Inf/NaN on the
        plotted axes, drawn selections, the z-range, cluster isolation and
        single-frame mode. The second axis is *shorter* than the raw data, so
        positions here are not original row numbers; use :attr:`value_mask` to
        map back.
        """
        self.data_manager.mask_state = self._collect_mask_state()
        return self.data_manager.get_filtered_values()

    @property
    def ymax(self) -> float:
        logging.debug("Getting ymax")
        scale = getattr(self.plot_control, 'scale_y', 'lin')
        result = axis_helpers.compute_axis_max(self.y_values, scale)
        logging.debug(f"ymax = {result}")
        return result

    @property
    def zmin(self):
        logging.debug("Getting zmin")
        scale = getattr(self.plot_control, 'scale_z', 'lin')
        result = axis_helpers.compute_axis_min(self.z_values, scale)
        logging.debug(f"zmin = {result}")
        return result

    @property
    def zmax(self) -> float:
        logging.debug("Getting zmax")
        scale = getattr(self.plot_control, 'scale_z', 'lin')
        result = axis_helpers.compute_axis_max(self.z_values, scale)
        logging.debug(f"zmax = {result}")
        return result

    @property
    def xmin(self) -> float:
        logging.debug("Getting xmin")
        scale = getattr(self.plot_control, 'scale_x', 'lin')
        result = axis_helpers.compute_axis_min(self.x_values, scale)
        logging.debug(f"xmin = {result}")
        return result

    @property
    def xmax(self) -> float:
        logging.debug("Getting xmax")
        scale = getattr(self.plot_control, 'scale_x', 'lin')
        result = axis_helpers.compute_axis_max(self.x_values, scale)
        logging.debug(f"xmax = {result}")
        return result

    @property
    def ymin(self) -> float:
        logging.debug("Getting ymin")
        scale = getattr(self.plot_control, 'scale_y', 'lin')
        result = axis_helpers.compute_axis_min(self.y_values, scale)
        logging.debug(f"ymin = {result}")
        return result

    @property
    def working_path(self):
        logging.debug("Getting working_path")
        path = self.lineEditWorkingPath.text()
        logging.debug(f"working_path = {path}")
        return path

    @working_path.setter
    def working_path(self, v):
        logging.info(f"Setting working_path to {v}")
        if pathlib.Path(v).is_dir():
            logging.debug(f"Path {v} is a valid directory, updating working path")
            self.lineEditWorkingPath.setText(v)
        else:
            logging.warning(f"Path {v} is not a valid directory, working path not updated")

    @property
    def vmin(self):
        logging.debug("Getting vmin")
        result = self.doubleSpinBox_vmin.value()
        logging.debug("vmin = %s", result)
        return result

    @vmin.setter
    def vmin(self, v):
        logging.debug(f"Setting vmin to {v}")
        self.doubleSpinBox_vmin.blockSignals(True)
        self.doubleSpinBox_vmin.setValue(v)
        self.doubleSpinBox_vmin.blockSignals(False)

    @property
    def vmax(self):
        logging.debug("Getting vmax")
        result = self.doubleSpinBox_vmax.value()
        logging.debug("vmax = %s", result)
        return result

    @vmax.setter
    def vmax(self, v):
        logging.debug(f"Setting vmax to {v}")
        self.doubleSpinBox_vmax.blockSignals(True)
        self.doubleSpinBox_vmax.setValue(v)
        self.doubleSpinBox_vmax.blockSignals(False)

    @property
    def current_cmap(self) -> str:
        """Get current colormap name."""
        return plot_colormaps.current_cmap(self)

    def update_cmap(self, cmap_name=None):
        """Update colormap using new colormaps module."""
        plot_colormaps.update_colormap(self, cmap_name)

    def populate_colormap_combobox(self):
        """Populate colormap combobox using new colormaps module."""
        plot_colormaps.populate_colormap_combobox(self)

    def on_vmin_vmax_changed(self):
        if not getattr(self, '_deferred_init_done', False) or self.g_2dplot is None:
            return
        
        # Debounce: schedule update instead of executing immediately
        if not hasattr(self, '_vmin_vmax_timer'):
            from qtpy import QtCore
            self._vmin_vmax_timer = QtCore.QTimer()
            self._vmin_vmax_timer.setSingleShot(True)
            self._vmin_vmax_timer.timeout.connect(self._apply_vmin_vmax_change)
        
        # Cancel any pending update and schedule a new one
        self._vmin_vmax_timer.stop()
        self._vmin_vmax_timer.start(50)  # 50ms debounce
    
    def _apply_vmin_vmax_change(self):
        """Actually apply the vmin/vmax change (called after debounce)."""
        if not getattr(self, '_deferred_init_done', False) or self.g_2dplot is None:
            return
        
        logging.info("vmin/vmax values changed")
        current_vmin = self.vmin
        current_vmax = self.vmax
        logging.info(f"Setting colormap limits to vmin={current_vmin}, vmax={current_vmax}")

        # Update the colormap limits for the 2D histogram image
        self.cax.set_lut_range([current_vmin, current_vmax])
        self.g_2dplot.replot()
        logging.info("Colormap limits updated")

    def set_default_colormap(self, default_cmap):
        """Set default colormap using new colormaps module."""
        plot_colormaps.set_default_colormap(self, default_cmap)

    # New unified plotting API methods
    def create_scatter_plot(self, **kwargs):
        """Create scatter plot using unified API."""
        return plotting_api.plot_scatter(self, **kwargs)

    def apply_colormap_to_data(self, data=None, **kwargs):
        """Apply colormap to data using unified API."""
        return plotting_api.apply_colormap(self, data, **kwargs)

    def get_plot_statistics(self, plot_type="histogram", **kwargs):
        """Get plot statistics using unified API."""
        return plotting_api.get_plot_statistics(self, plot_type, **kwargs)

    def export_plot_data(self, plot_type="histogram", **kwargs):
        """Export plot data using unified API."""
        return plotting_api.export_plot_data(self, plot_type, **kwargs)

    def refresh_all_plots(self):
        """Refresh all plots using unified API."""
        plotting_api.refresh_all_plots(self)

    def __init__(
            self,
            data_source=None,  # type: DataSource
            settings_json_fn=None,  # type: str
            parent=None,
            cmap: str = 'gist_earth',
            zmq_cmd_port: Optional[int] = None,
            processed_data_id: Optional[str] = None,
            experiment_id: Optional[str] = None,
            chisurf_rpc=None,
    ) -> None:
        super(NDXplorer, self).__init__(parent=parent)

        self.zmq_cmd_port = zmq_cmd_port
        self.processed_data_id = processed_data_id
        self.experiment_id = experiment_id
        # ChiSurf RPC (PRD-56): either an injected client (any object exposing
        # ``call(method, params)`` — e.g. ChiSurf's in-process client) or, for
        # headless/external use, a ``ZmqRpcClient`` built from ``zmq_cmd_port``.
        self.chisurf_rpc = chisurf_rpc
        self.zmq_client = chisurf_rpc  # backwards-compat attribute name
        self.phasor_service = None
        self.lines_service = None

        # Set default window size
        self.resize(900, 630)
        

        # Store init params for deferred initialization
        self._init_cmap = cmap
        self._init_settings_json_fn = settings_json_fn
        self._deferred_init_done = False

        # Initialize data manager (new architecture)
        self.data_manager = DataManager()

        self.settings = dict()  # type: Dict
        self.equations = list()  # type: List[Dict[str, str]]
        self.constants = dict()  # type: Dict[str, float]
        # ``None`` means "not computed yet" -- the state every consumer already
        # tests for. An empty tuple looked like a *corrupt* histogram instead, so
        # startup logged format errors for a window that simply had no data, and
        # the "is there a histogram to recolour?" checks answered yes.
        self._histogram = {
            "x": None,
            "y": None,
            "z": None,
            "2d": None,
        }
        
        # Backward compatibility: delegate to data_manager
        self._mask_inf = True  # type: bool
        self._mask_nan = True  # type: bool
        self._dynamic_selection = False  # type: bool
        
        self._preserve_contrast = False  # type: bool
        self._has_real_data = False
        self._plot_stack_widget = None
        self._background_label = None
        self._plot_container = None
        
        # Track active background load threads to prevent premature deletion
        
        if isinstance(data_source, DataSource):
            self.data_source = data_source

        # Clustering settings
        self._use_clustering = False

        # Common clustering variables
        self._cluster_labels = None  # type: Optional[np.ndarray]
        self._cluster_probabilities = None  # type: Optional[np.ndarray]
        self.clustering_worker = None  # Initialize the worker instance

        # Create clustering dialog early to use its parameters
        self.clustering_dialog = ClusteringDialog(parent=self)

        # Initialize weight tracking attributes
        self.current_weight_enabled = False
        self.current_weight_param = "None"

        self.plot_control = SurfacePlotWidget(self)

        def _equation_names():
            """(column names, constant names) the equation editor can reference."""
            ds = getattr(self, "data_source", None)
            cols = list(getattr(ds, "parameter_names", []) or [])
            consts = list(self.constants.keys()) if getattr(self, "constants", None) else []
            return cols, consts

        self.equation_editor = EquationEditor(parent=self, names_provider=_equation_names)
        self.curve_overlay_widget = CurveOverlayWidget(self)
        self.curve_evaluator = CurveEvaluator()

        ui_candidates = [
            Path(__file__).resolve().with_name("plot_main.ui"),
            Path(__file__).resolve().parents[1] / "plotting" / "plot_main.ui",
        ]
        ui_path = next((path for path in ui_candidates if path.exists()), None)
        if ui_path is None:
            raise FileNotFoundError(
                f"ndX UI definition not found. Tried: {', '.join(str(p) for p in ui_candidates)}"
            )
        uic.loadUi(str(ui_path), self)
        self.verticalLayout_3.addWidget(self.plot_control)
        self.verticalLayout_15.addWidget(self.equation_editor)
        self.verticalLayout_10.addWidget(self.curve_overlay_widget)
        self._setup_axis_toolbar_actions()

        # Connect screenshot tool button if present
        try:
            if hasattr(self, 'toolButton_screenshot') and self.toolButton_screenshot is not None:
                self.toolButton_screenshot.clicked.connect(self.on_take_screenshot)
        except Exception as e:
            logging.debug(f"Could not connect screenshot button: {e}")

        # Add the publication-quality export button next to the screenshot one.
        try:
            from ..ui.publication_export_dialog import add_publication_export_button
            add_publication_export_button(self)
        except Exception as e:
            logging.debug(f"Could not add publication export button: {e}")

        # Make Fit action checkable and wire it to the Fit panel's visibility.
        # A dock-area tab is shown and hidden through the area, not by the
        # widget's own ``setVisible`` -- hiding the widget of a tab that is still
        # in the bar leaves the tab there with nothing behind it.
        self.actionFit_Gaussians.toggled.connect(self._set_fit_panel_visible)

        # Report tool
        self.actionMake_Report.triggered.connect(self.onShowReportWizard)

        # Enable drag & drop on working path line edit
        try:
            self._install_working_path_drop()
        except Exception as e:
            logging.debug(f"Failed to enable working path drop: {e}")

        setup_histogram_spinboxes(self)

        # Connect curve overlay signals
        self.curve_overlay_widget.curvesChanged.connect(self.update_curve_overlays)
        self.curve_overlay_widget.curveFitRequested.connect(self.on_fit_curve_to_data)

        def save_cb():
            logging.info("Save CB")
            # Prefer the structured rows (no YAML round-trip); fall back to the
            # serialised text for the legacy CodeEditor surface.
            if hasattr(self.equation_editor, "equations"):
                self.equations = self.equation_editor.equations()
            else:
                self.equations = yaml.load(self.equation_editor.text())
            # Equations changed wholesale -> recompute every derived column, redraw.
            try:
                self.data_source.compute_columns(
                    constants=self.constants,
                    equations=self.equations,
                )
            except Exception as exc:
                logging.warning("Equation recompute failed: %s", exc)
            self.update_plots()
        self.equation_editor.save_callback = save_cb

        self.populate_colormap_combobox()

        # Add clustering button to show/hide dialog
        self.setup_clustering_button()

        configure_dynamic_selection_controls(self)

        # Placeholder attributes for plots (created in _deferred_init)
        self.g_zplot = None
        self.g_xplot = None
        self.g_yplot = None
        self.g_2dplot = None
        self.overlay_plot = None
        self.cax = None
        self.bg_image_item = None
        self.gaussian_fit = None
        self.parameter_control = None

        # Create placeholder widgets to maintain correct layout while plots load
        setup_plot_placeholders(self)

        # Plot update batching timer (debounces repeated UI-triggered updates)
        self._plot_update_timer: Optional[QtCore.QTimer] = None
        self._plot_update_pending = False
        self._plot_update_requires_clustering = False
        self._initialize_plot_update_timer()

        # The panels move out of Qt's dock widgets and into ChiSurf's dock area
        # here, once they have been put into the dock contents -- earlier would
        # move empty containers. Immediately rather than deferred, so the window
        # is never briefly drawn in the arrangement it is about to leave.
        from ..utils.dock_conversion import convert_docks

        convert_docks(self)

        # Schedule deferred initialization after window is shown
        # This makes the window appear faster
        QtCore.QTimer.singleShot(0, self._deferred_init)

    def _run_data_load_task(self, description: str, load_callable, append: bool, merge_mode: str) -> None:
        """
        Run data loading task asynchronously using the async loader framework.
        
        Parameters
        ----------
        description : str
            Description of the loading task for progress display.
        load_callable : callable
            Function that performs the actual data loading and returns a DataSource.
        append : bool
            Whether to append data or replace.
        merge_mode : str
            How to merge data if appending.
        """
        from ..io import file_operations
        
        def on_success(data_source):
            file_operations._finalize_loaded_data(self, data_source, append, merge_mode)
        
        def on_error(msg):
            logging.error(f"Async data load failed: {msg}")
            # Could show error dialog here
            QtWidgets.QMessageBox.critical(
                self, "Data Load Error", 
                f"Failed to load data: {msg}"
            )
        
        # The loader decides whether the read can go to a worker thread
        # (``io.async_loader.run_task``); the callbacks arrive on this thread.
        # This used to build its own QThread around ``reader.DataLoadWorker``,
        # which the reader stopped re-exporting when it became Qt-free -- so
        # every GUI load raised AttributeError before reading a byte.
        reader.run_task(reader.DataLoadTask(
            description=description,
            load_callable=load_callable,
            on_success=on_success,
            on_error=on_error,
        ))

    def _deferred_init(self):
        """Deferred initialization of heavy plot widgets for faster window appearance."""
        logging.info("Starting deferred initialization")
        if self._deferred_init_done:
            logging.info("Deferred init already done, skipping")
            return
        self._deferred_init_done = True
        logging.info("Set deferred_init_done = True")

        cmap = self._init_cmap
        settings_json_fn = self._init_settings_json_fn

        logging.info("Setting up histogram plots")
        setup_histogram_plots(self)
        logging.info("Setting up 2D histogram plot")
        setup_2d_histogram_plot(self, cmap)
        logging.info("Setting up overlay plot")
        setup_overlay_plot(self)
        # Keep the NDxplorer splash/background visible until real data arrives
        plot_update_helpers._show_background(self)

        # -----------------------------------------------------------------
        # Gaussian Fit controls: attach from a separate module for cleanliness
        # -----------------------------------------------------------------
        from ..analysis.gaussian_fit import GaussianFit
        self.gaussian_fit = GaussianFit(self)

        # Point mode has to follow the TAB, not only the menu action: a user
        # who switches to the Gaussian Fit tab is "in the fit dock" and a click
        # on the 2D histogram should add a local Gaussian there, not start a
        # rubber-band selection. The action path already routes through
        # _on_fit_dock_visibility_changed; this makes tab switches do the same.
        area = getattr(self, "dock_area", None)
        if area is not None and hasattr(area, "currentChanged"):
            area.currentChanged.connect(self._on_dock_tab_changed)

        self.g_xplot.setMinimumHeight(40)
        self.g_yplot.setMinimumWidth(40)
        self.g_zplot.setMinimumHeight(100)

        # Load settings
        ###############
        if settings_json_fn is None:
            # Ensure default settings exist in the user's settings folder
            from ..settings import ensure_default_settings
            from .. import settings_helpers
            ensure_default_settings()
            # Get the path to the settings folder
            settings_path = settings_helpers.get_settings_path()
            settings_json_fn = settings_path / "mfd.settings.json"
        self.onLoad_settings(settings_json_fn=str(settings_json_fn))

        # Parameter control
        ######################
        # Track constants so a parameter edit can recompute only the derived
        # columns that actually depend on the changed constant(s), and debounce
        # rapid edits (e.g. mouse-wheel ticks) into a single recompute.
        self._prev_constants = dict(self.parameter_control.dict) if getattr(self, "parameter_control", None) else {}
        self._pending_changed_constants = set()
        self._parameter_recompute_timer = None

        def parameter_update():
            self._schedule_parameter_recompute()
        # Get the settings path
        settings_path = get_settings_path()
        self.parameter_control = ParameterEditor(
            parent=self,
            json_file=str(settings_path / "mfd.constants.json"),
            callback=parameter_update
        )
        # Seed self.constants from the parameter table NOW, so the initial
        # (background) column computation derives Bg/gamma/PhiA-dependent columns
        # — FRET efficiency, Fg, ... — with the SAME constants the table shows.
        # Previously self.constants stayed empty until the first edit, so the
        # initial plot was computed with no constants (those columns missing or
        # default) and the first edit applied the whole table at once, producing
        # a large jump for what looked like a 1% parameter tweak.
        self._prev_constants = dict(self.parameter_control.dict)
        # self.constants is a LIVE mapping over the fitting-parameter group when
        # available, so a constant crosslinked to a fit parameter reads the
        # linked value at recompute time. Falls back to a plain snapshot.
        mapping = getattr(self.parameter_control, "constants_mapping", None)
        self.constants = mapping if mapping is not None else dict(self.parameter_control.dict)
        # A fit-driven change to a linked constant asks for a targeted recompute.
        sig = getattr(self.parameter_control, "constantsChangedExternally", None)
        if sig is not None:
            try:
                sig.connect(self._schedule_parameter_recompute)
            except Exception:
                pass
        self.verticalLayout_4.addWidget(self.parameter_control)

        # Actions
        #############
        # Working path
        self.actionSelect_working_path.triggered.connect(self.onSelectWorkingPath)

        # Load / Save
        self.actionOpenChiSurfSampling.triggered.connect(self.onOpenChiSurfSampling)
        self.actionOpenParisDataset.triggered.connect(self.onOpenSmFRET)
        self.actionOpenCsv.triggered.connect(self.onOpenCsv)
        self.actionOpenMfdHdf5.triggered.connect(self.onOpenMfdHdf5)
        self.actionBurst_IDs.triggered.connect(self.onSaveBurstIDs)

        # Settings
        self.actionLoad_settings.triggered.connect(self.onLoad_settings)
        self.actionSave_axis_settings.triggered.connect(self.onSaveAxisSettings)
        self.actionSet_default_axis.triggered.connect(self.onSetDefaultAxis)
        self.actionPerformanceSettings.triggered.connect(self.onPerformanceSettings)
        # GUI updates
        self.actionUpdate_plot.triggered.connect(lambda: self.update_plots())
        self.actionClear_plot.triggered.connect(self.clear_plots)
        self.actionMask_toggle_changed.triggered.connect(self.onMaskChanged)
        # UMAP
        self.actionUMAP.triggered.connect(self.onShowUMAP)
        # View > "Find informative projections…" (and its z-axis entry), right
        # below UMAP: rank the views instead of hunting for them
        # (ndxplorer.ui.projection_rank). Disabled without data, like UMAP.
        try:
            from ..ui.projection_rank import install_projection_ranking

            install_projection_ranking(self)
        except Exception:
            logging.warning("Could not install projection ranking", exc_info=True)
        self.actionAxisControl.triggered.connect(self.onShowAxisControl)

        # toolButton_3 opens the table editor
        self.toolButton_3.clicked.connect(self.show_store_editor)

        # Connect toolButton_AutoContrast to auto contrast function
        self.toolButton_AutoContrast.clicked.connect(self.on_auto_contrast)
        self.toolButton_3.setEnabled(True)  # Enable the button
        
        # Connect to save parameters
        self.toolButton_parameter_save.clicked.connect(self.save_parameters)
        self.actionConstants.triggered.connect(self.save_parameters)
        # Axis range

        self.overlay_plot.canvas().setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.overlay_plot.canvas().customContextMenuRequested.connect(self.on_canvas_context_menu)

        # These combo boxes control the parameter selections for the 2D plot.
        # They must go through the argument-dropping slot: ``currentIndexChanged``
        # carries the new index, which would otherwise land in ``low_pct``.
        self.plot_control.comboBoxSelX.currentIndexChanged.connect(self.on_axis_selection_changed)
        self.plot_control.comboBoxSelY.currentIndexChanged.connect(self.on_axis_selection_changed)
        self.plot_control.comboBoxSelZ.currentIndexChanged.connect(self.on_axis_selection_changed)

        # Connections for spin boxes are already set up above
        
        # Initialize mask drawing integration
        self._setup_mask_drawing()

        # Initialize UI enabled state based on current dataset
        try:
            self.update_ui_enabled_state()
        except Exception:
            pass
        
        # After deferred init completes, render any pending histograms
        # This handles the case where file loading computed histograms before plot objects existed
        try:
            if self._histogram and any(self._histogram.values()):
                from ..plotting.plot_update_helpers import _update_marginal_plots_from_cache
                _update_marginal_plots_from_cache(self)
                logging.info("Rendered pending histograms after deferred init completion")
        except Exception as e:
            logging.debug(f"Could not render pending histograms: {e}")

        # Establish the ChiSurf RPC link (PRD-56): use an injected client if given,
        # otherwise build a ZMQ client from ``zmq_cmd_port``. Then load a database
        # product if one was requested.
        self._init_chisurf_rpc()
        if self.chisurf_rpc is not None and self.processed_data_id:
            self._load_burst_product()

    def _init_chisurf_rpc(self) -> None:
        """Attach the phasor facade to an injected or port-derived RPC client."""
        if self.chisurf_rpc is None and self.zmq_cmd_port is not None:
            try:
                logging.info("Connecting to ChiSurf RPC on port %s...", self.zmq_cmd_port)
                self.chisurf_rpc = ZmqRpcClient(cmd_port=self.zmq_cmd_port)
            except Exception as exc:
                logging.error("Could not create ChiSurf RPC client: %s", exc)
                self.chisurf_rpc = None
        self.zmq_client = self.chisurf_rpc  # keep the legacy attribute in sync
        if self.chisurf_rpc is not None:
            self.phasor_service = PhasorService(self.chisurf_rpc)
            self.lines_service = LinesService(self.chisurf_rpc)
            try:
                from ..ui.phasor_toolbar import install_phasor_toolbar

                install_phasor_toolbar(self)
            except Exception:
                logging.warning("Could not install ChiSurf phasor toolbar", exc_info=True)

    def _load_burst_product(self) -> None:
        try:
            if self.processed_data_id:
                logging.info(f"Loading database product {self.processed_data_id} via ZMQ RPC...")
                res = self.zmq_client.call("ndxplorer.load_burst_product", {"processed_data_id": self.processed_data_id})
                
                # Unpack response
                if res.get("ok") or (isinstance(res.get("result"), dict) and res["result"].get("ok")):
                    result_data = res.get("result", res)
                    param_names = result_data.get("parameter_names", [])
                    raw_values = result_data.get("values")
                    
                    import numpy as np
                    from ..core.data_source import DataSource
                    from ..io.file_operations import _finalize_loaded_data
                    
                    if isinstance(raw_values, dict) and raw_values.get("__ndarray__"):
                        values = np.array(raw_values["data"], dtype=raw_values["dtype"])
                    else:
                        values = np.array(raw_values, dtype=np.float32)
                    
                    ds = DataSource.from_columns(
                        {str(name): values[i] for i, name in enumerate(param_names)})
                    _finalize_loaded_data(self, ds, append=False, merge_mode="columns")
                    logging.info(f"Successfully loaded database product {self.processed_data_id} via ZMQ.")
                    self.statusBar().showMessage(f"Loaded database product {self.processed_data_id} via ZMQ")
                else:
                    err = res.get("error", "Unknown error")
                    logging.error(f"Failed to load database product: {err}")
                    QtWidgets.QMessageBox.critical(self, "ZMQ Load Error", f"Failed to load database product:\n{err}")
        except Exception as e:
            logging.error(f"Error in ZMQ client initialization or loading: {e}")
            QtWidgets.QMessageBox.critical(self, "ZMQ Connection Error", f"Failed to establish ZMQ connection:\n{e}")

    def _setup_mask_drawing(self):
        """Setup mask drawing integration with the 2D plot."""
        logging.debug("Starting mask drawing setup...")
        try:
            # Initialize mask drawing integration
            logging.debug("Creating MaskDrawingIntegration instance...")
            self.mask_drawing = MaskDrawingIntegration(self)
            logging.debug("MaskDrawingIntegration instance created")
            
            # Connect mask widget signals
            logging.debug("Getting mask widget...")
            mask_widget = self.plot_control.mask_widget
            logging.debug(f"Mask widget: {mask_widget}")
            
            logging.debug("Connecting mask_changed signal...")
            mask_widget.mask_changed.connect(self._on_mask_changed)
            logging.debug("Signal connected")
            
            # Setup mask overlay on 2D plot
            logging.debug("Setting up mask overlay...")
            self.mask_drawing.setup_mask_overlay()
            logging.debug("Mask overlay setup complete")
            
            logging.info("Mask drawing integration initialized successfully")
        except Exception as e:
            logging.error(f"Could not setup mask drawing: {e}", exc_info=True)
            # Still set mask_drawing to None so we know it failed
            self.mask_drawing = None
    
    def _on_mask_changed(self, mask):
        """Handle mask changes from the mask widget."""
        try:
            # Update the mask overlay visualization
            if hasattr(self, 'mask_drawing'):
                self.mask_drawing.update_mask_overlay(mask)
            
            # No histogram cache to invalidate: the redraw below recomputes.
            # Request plot update to recompute histograms with new mask
            # Use skip_clustering=True for faster response (mask changes don't affect clustering)
            self.request_plot_update(skip_clustering=True)
            
        except Exception as e:
            logging.warning(f"Error handling mask change: {e}")
    
    def apply_mask_to_selection(self, category: Optional[int] = None):
        """
        Apply the current mask to create a selection.
        
        Parameters
        ----------
        category : Optional[int]
            If specified, only select pixels with this category.
            If None, select all non-zero pixels.
        """
        try:
            from ..utils import mask_helpers
            
            mask = self.plot_control.mask_widget.get_mask()
            if mask is None:
                QtWidgets.QMessageBox.warning(
                    self,
                    "No Mask",
                    "No mask to apply. Draw or load a mask first."
                )
                return
            
            # Get current histogram bounds
            if not hasattr(self, '_histogram') or self._histogram is None:
                return
            
            hist_data = self._histogram.get('2d')
            if hist_data is None:
                return
            
            H, xedges, yedges = hist_data
            
            # Get parameter names
            x_param = self.plot_control.comboBoxSelX.currentText()
            y_param = self.plot_control.comboBoxSelY.currentText()

            # Get parameter indices
            x_idx_param = -1
            y_idx_param = -1
            
            for i, name in enumerate(self.data_source.parameter_names):
                if name == x_param:
                    x_idx_param = i
                if name == y_param:
                    y_idx_param = i
            
            if x_idx_param == -1 or y_idx_param == -1:
                logging.error(f"Could not find parameter indices for {x_param} or {y_param}")
                return

            # Extract the specific category if requested
            if category is not None:
                binary_mask = (mask == category)
            else:
                binary_mask = (mask > 0)

            if not np.any(binary_mask):
                QtWidgets.QMessageBox.information(
                    self,
                    "Empty Selection",
                    "The mask does not contain any pixels for the specified category."
                )
                return
            
            # Log mask and histogram details
            logging.info(f"Applying mask to selection:")
            logging.info(f"  Mask shape: {mask.shape}, binary_mask shape: {binary_mask.shape}")
            logging.info(f"  Histogram H shape: {H.shape}")
            logging.info(f"  X edges: len={len(xedges)}, range=[{xedges[0]:.2f}, {xedges[-1]:.2f}]")
            logging.info(f"  Y edges: len={len(yedges)}, range=[{yedges[0]:.2f}, {yedges[-1]:.2f}]")
            logging.info(f"  X param: {x_param} (idx={x_idx_param})")
            logging.info(f"  Y param: {y_param} (idx={y_idx_param})")
            logging.info(f"  Mask pixels set: {np.count_nonzero(binary_mask)}/{binary_mask.size}")

            # Note: We now support multiple bitmap selections, so we don't remove existing ones
            # Each bitmap selection will be added as a separate selection item

            # 1. Create the actual selection object first
            # Generate a unique name for multiple bitmap selections
            existing_mask_count = sum(1 for sel in self.plot_control._selections 
                                    if isinstance(sel, MaskDataSelection) and sel.idx1 == x_idx_param and sel.idx2 == y_idx_param)
            mask_number = existing_mask_count + 1
            selection_name = f"Bitmap {mask_number} ({x_param}, {y_param})"
            
            selection = MaskDataSelection(
                idx1=x_idx_param,
                idx2=y_idx_param,
                mask=binary_mask,
                edges1=xedges,
                edges2=yedges,
                name=selection_name
            )
            
            logging.info(f"  Created MaskDataSelection with id={selection.selection_id}")
            
            # 2. Add it to the internal selections list
            self.plot_control._selections.append(selection)
            
            # 3. Add the UI representation (which triggers the update)
            self.plot_control.addMaskSelection(
                name=selection.name,
                mask=binary_mask,
                edges1=xedges,
                edges2=yedges,
                idx1=x_idx_param,
                idx2=y_idx_param,
                selection_id=selection.selection_id
            )
            
            # Request update
            self.request_plot_update()
            
        except Exception as e:
            logging.error(f"Error applying mask to selection: {e}")
            QtWidgets.QMessageBox.critical(
                self,
                "Error",
                f"Failed to apply mask: {str(e)}"
            )

    def show_store_editor(self):
        """Open the table editor on the current data source."""
        logging.debug("show_store_editor")
        data_source = self.data_source
        if data_source.empty:
            QtWidgets.QMessageBox.warning(
                self, "No Data", "No data loaded—nothing to show."
            )
            return

        from ..ui.store_editor import edit_source

        if edit_source(data_source, self):
            self.update_parameter_names()
            self.update_plots()

    def clear_plots(self):
        logging.debug(f"clear_plots")
        # 0. Also clear the working path line edit (global clear should reset path)
        try:
            self.lineEditWorkingPath.blockSignals(True)
            try:
                self.lineEditWorkingPath.clear()
            except Exception:
                # Fallback in case clear() is not available
                self.lineEditWorkingPath.setText("")
        except Exception:
            pass
        finally:
            try:
                self.lineEditWorkingPath.blockSignals(False)
            except Exception:
                pass

        # 1. Clear the user data, so the default (logo) source takes over again.
        source = self.data_source
        if source is not None:
            source.clear()

        # 2. Clear the selection table so no old mask references remain
        #    (But remember, this does NOT fix comboBoxSelX/Y/Z)
        self.plot_control.onClearSelection()

        # 2.5. Clear all overlays (curve overlays and Gaussian overlays)
        try:
            # Remove any drawn curves from the overlay plot. It owns the curves
            # it was handed and hands back no per-item handles, so clearing goes
            # through the plot rather than through a list kept on this side.
            if getattr(self, 'overlay_plot', None) is not None:
                self.overlay_plot.clear_curves()
            # Clear curve overlay widgets (also resets internal state and emits signal)
            if hasattr(self, 'curve_overlay_widget') and self.curve_overlay_widget is not None:
                self.curve_overlay_widget.clear_curves()
            # Clear Gaussian overlays (ellipses, marginals, and table)
            try:
                self.on_clear_gaussians()
            except Exception:
                # If GaussianFit not initialized, ignore
                pass
            # Ensure overlay canvas is refreshed
            if hasattr(self, 'overlay_plot') and self.overlay_plot is not None:
                try:
                    self.overlay_plot.replot()
                except Exception:
                    pass
        except Exception:
            pass

        # 2.6. Clear clustering data
        if hasattr(self, '_cluster_labels'):
            self._cluster_labels = None

        # 2.7. Clear cluster probabilities if they exist
        if hasattr(self, '_cluster_probabilities'):
            self._cluster_probabilities = None

        # 2.8. Hide clustering dialog if it's visible
        if hasattr(self, 'clustering_dialog') and self.clustering_dialog is not None and self.clustering_dialog.isVisible():
            self.clustering_dialog.hide()

        # 3. Update once so 'plot_control.update()' sees an empty data source =>
        #    repopulates combo boxes with the default dataset columns
        self.plot_control.update()

        # 4. Force combo box indices to match the default columns.
        #    Example: we want [ "Tau (green)", "Proximity ratio", "r Experimental (green)" ]
        if hasattr(self, 'data_manager') and self.data_manager is not None:
            default_data = self.data_manager.data_source
            if default_data is not None and not default_data.empty:
                default_names = default_data.parameter_names
                try:
                    ix_tau = default_names.index("Tau (green)")
                    ix_prox = default_names.index("Proximity ratio")
                    ix_r = default_names.index("r Experimental (green)")

                    self.plot_control.comboBoxSelX.setCurrentIndex(ix_tau)
                    self.plot_control.comboBoxSelY.setCurrentIndex(ix_prox)
                    self.plot_control.comboBoxSelZ.setCurrentIndex(ix_r)
                except ValueError as e:
                    logging.warning(f"Could not set default combo box indices: {e}")
            else:
                logging.warning("Default data source is empty or None")
        else:
            logging.warning("Data manager not available, cannot set default combo box indices")

        # 5. Directly call update_plots to ensure all graphs are cleared
        self.update_plots()

    def is_napari_available(self):
        return napari_helpers.is_napari_available(self)

    def prompt_install_napari(self) -> bool:
        return napari_helpers.prompt_install_napari(self)

    def install_napari_via_conda(self) -> Tuple[bool, Optional[str]]:
        return napari_helpers.install_napari_via_conda(self)
        
    def send_to_napari(self):
        napari_helpers.send_to_napari(self)
    
    def on_canvas_context_menu(self, pos):
        """
        Display a context menu when right-clicking on the 2D plot canvas.
        
        This method creates a context menu with options to:
        - Copy the 2D histogram data as CSV
        - Copy the 1D histograms data as CSV
        - Send the current 2D histogram to Napari (if installed)
        
        Args:
            pos: The position where the context menu should be displayed
        """
        logging.debug(f"on_canvas_context_menu")
        menu = QtWidgets.QMenu(self.g_2dplot.canvas())
        action_csv = menu.addAction("Copy 2D Histogram (CSV)")
        #action_json = menu.addAction("Copy 2D Histogram (JSON)")
        action_csv1d = menu.addAction("Copy 1D Histograms (CSV)")
        
        # Add napari option - allows sending the current 2D histogram to Napari
        action_napari = menu.addAction("Send to Napari")

        # Picking, offered here rather than on left-click: that button already
        # pans and paints masks, and stealing it would break two gestures to
        # add a third.
        menu.addSeparator()
        action_pick = menu.addAction("Fit gate to the population here")
        action_pick.setToolTip(
            "Fit a 2-D Gaussian to the points around the cursor and add the "
            "ellipse as a gate. The click is a seed: the fit re-centres on the "
            "population."
        )

        # Hand the gated bursts to a real analysis (FCS, TCSPC, PDA, PCH).
        # Offered here as well as on the selection table because the gate is
        # usually drawn on this canvas, and going hunting for the table to act
        # on what you just drew is a detour.
        menu.addSeparator()
        try:
            from ..analysis.send_menu import add_send_menu

            add_send_menu(menu, self)
        except Exception:
            logging.debug("could not build the send menu", exc_info=True)
        
        action = menu.exec_(self.g_2dplot.canvas().mapToGlobal(pos))
        if action == action_csv:
            self.copy_2d_hist_to_clipboard_csv()
        #elif action == action_json:
        #    self.copy_2d_hist_to_clipboard_json()
        elif action == action_csv1d:
            self.copy_1d_hists_to_clipboard_csv()
        elif action == action_napari:
            self.send_to_napari()
        elif action == action_pick:
            self.pick_population_from_canvas(pos)

    # ── picking a population off the 2-D plane ──────────────────────────
    def pick_population_at(self, x: float, y: float, *, radius: float = 0.0,
                           name: str = "") -> str:
        """Fit a gate to the population at ``(x, y)`` and add it.

        The model half of the gesture, in the **parameters' own units**, so it
        is testable without a plot and so the coordinate mapping is somebody
        else's problem exactly once.

        Parameters
        ----------
        x, y : float
            Where the user clicked, in parameter units.
        radius : float, optional
            Capture radius. Zero takes a twentieth of the shorter displayed
            axis, which is a starting point rather than an answer: a density
            has no edge, so how much of a cloud is "one population" is a
            decision, and this one is merely a reasonable default to adjust
            from.
        name : str, optional
            Gate name; a numbered default otherwise.

        Returns
        -------
        str
            Empty on success, or why the pick was refused.
        """
        from ..core.region_selection import pick_population

        data = self.values
        if data is None or not len(data):
            return "no data loaded"

        # The points as displayed: every gate already applied. Fitting to what
        # is on screen is the point — a population that is half hidden by an
        # earlier gate is not the population the user is looking at.
        names = list(self.data_source.parameter_names)
        x_param = self.plot_control.comboBoxSelX.currentText()
        y_param = self.plot_control.comboBoxSelY.currentText()
        idx1 = names.index(x_param) if x_param in names else -1
        idx2 = names.index(y_param) if y_param in names else -1
        if idx1 < 0 or idx2 < 0:
            return f"could not find the parameters {x_param!r} and {y_param!r}"
        if not radius:
            x_range = self.plot_control.x_range
            y_range = self.plot_control.y_range
            span_x = abs(float(x_range[1]) - float(x_range[0]))
            span_y = abs(float(y_range[1]) - float(y_range[0]))
            radius = max(min(span_x, span_y) / 20.0, 1e-12)

        count = sum(1 for sel in self.plot_control._selections
                    if getattr(sel, "roi", None) is not None)
        selection, reason = pick_population(
            np.asarray(data), (idx1, idx2), float(x), float(y),
            radius=float(radius), name=name or f"Population {count + 1}",
        )
        if selection is None:
            return reason

        self.plot_control._selections.append(selection)
        self.plot_control.addRegionSelection(selection)
        self.request_plot_update()
        return ""

    def pick_population_from_canvas(self, pos) -> None:
        """Fit a gate to the population under the cursor, from a canvas click.

        The coordinate half. ``pos`` is in the canvas viewport's own pixels, so
        it goes through the scene to the view box, which is the only mapping
        that respects pan, zoom and whatever transform the image item carries.
        A point that lands outside the displayed ranges is **refused**: it means
        the mapping did not do what this code thinks it did, and fitting
        somewhere arbitrary would produce a gate that is merely plausible.
        """
        try:
            view = self.g_2dplot.plot_widget
            box = view.getPlotItem().getViewBox()
            point = box.mapSceneToView(view.mapToScene(pos))
            x, y = float(point.x()), float(point.y())
        except Exception as exc:
            logging.debug("could not map the click to data coordinates", exc_info=True)
            self.statusBar().showMessage(f"Could not read the click position: {exc}")
            return

        x_range = self.plot_control.x_range
        y_range = self.plot_control.y_range
        inside = (min(x_range) <= x <= max(x_range)
                  and min(y_range) <= y <= max(y_range))
        if not inside:
            self.statusBar().showMessage(
                f"That click maps to ({x:.4g}, {y:.4g}), outside the plotted "
                "range — not fitting a gate there"
            )
            return

        reason = self.pick_population_at(x, y)
        self.statusBar().showMessage(
            f"No gate: {reason}" if reason
            else f"Gate fitted to the population at ({x:.4g}, {y:.4g})"
        )

    def onMaskChanged(self) -> None:
        """
        Whenever the user toggles the Inf/NaN masks,
        invalidate the cache and re-plot.
        """
        logging.debug(f"onMaskChanged")
        self._mask_inf = self.checkBoxMaskInf.isChecked()
        self._mask_nan = self.checkBoxMaskNaN.isChecked()
        self.invalidate_values_cache()
        self.request_plot_update()

    def onShowAxisControl(self) -> None:
        """
        Show the Axis Control dialog.
        This method is triggered when the user clicks the Axis Control action in the View menu.
        """
        logging.debug(f"onShowAxisControl")
        # Create and show the axis control dialog
        dialog = AxisControlDialog(parent=self)
        dialog.exec_()
        
    def onShowUMAP(self) -> None:
        umap_helpers.on_show_umap(self)

    def onShowReportWizard(self):
        """Open the Report Tool dialog."""
        logging.debug(f"onShowReportWizard")
        try:
            from ndxplorer.report_tool import ReportWizard
            dlg = ReportWizard(parent=self)
            dlg.exec_()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Report Tool Error", str(e))
            
    def on_take_screenshot(self):
        screenshot_helpers.take_screenshot(self)

    def onSelectWorkingPath(self):
        logging.debug(f"onSelectWorkingPath")
        working_path = QtWidgets.QFileDialog.getExistingDirectory(None, 'Select current path', self.working_path)
        # If user cancels the dialog, do not change the working path
        if not working_path:
            return
        self.lineEditWorkingPath.blockSignals(True)
        self.lineEditWorkingPath.setText(working_path)
        self.lineEditWorkingPath.blockSignals(False)

    def _install_working_path_drop(self):
        working_path_helpers.install_working_path_drop(self)

    def on_save_burst_ids(self, evt=None, folder=None):
        save_burst_ids(self, folder)

    def onSaveBurstIDs(self, evt=None, folder=None):
        """Backward-compatible alias used by older macros."""
        self.on_save_burst_ids(evt=evt, folder=folder)

    def onSaveClusteringData(self, evt=None, folder=None):
        save_clustering_data(self, folder)

    def save_parameters(self):
        """
        Save the current parameters to a JSON file in the user's settings folder.
        """
        logging.debug(f"save_parameters")
        # Get the settings path
        settings_path = get_settings_path()
        
        # Create the filename for the parameters
        param_filename = str(settings_path / "mfd.constants.json")
        
        # Save the parameters. Persist the rich per-parameter state (value +
        # bounds + fixed) when the editor is the fitting-parameter table; the
        # loader accepts both this and the legacy flat {name: value} format.
        payload = (
            self.parameter_control.get_state()
            if hasattr(self.parameter_control, "get_state")
            else self.parameter_control.dict
        )
        with open(param_filename, "w") as fp:
            json.dump(payload, fp, indent=4)
        
        logging.info( f"Parameters saved to {param_filename}")
    
    def onSaveAxisSettings(
            self,
            event,
            settings_json_fn=None  # type: str
    ):
        settings_helpers.save_axis_settings(self, settings_json_fn=settings_json_fn)

    def onSetDefaultAxis(self):
        """
        Set the current axis selections (and weight, if available) as the new defaults
        in the active ndxplorer settings JSON under the 'default_axes' key.
        """
        settings_helpers.set_default_axis(self)

    def onLoad_settings(
            self,
            settings_json_fn=None  # type: str
    ) -> None:
        settings_helpers.load_settings(self, settings_json_fn=settings_json_fn)

    def onPerformanceSettings(self) -> None:
        """Show the performance settings dialog."""
        try:
            from ..ui.performance_settings_dialog import PerformanceSettingsDialog
            dlg = PerformanceSettingsDialog(parent=self)
            dlg.exec_()
        except Exception as e:
            logging.error(f"Failed to open performance settings dialog: {e}")
            QtWidgets.QMessageBox.critical(
                self, 
                "Error", 
                f"Failed to open performance settings dialog: {e}"
            )

    def open_files(
        self,
        file_handles: typing.List[str] = None,
        file_type: str = None,
        append: bool = False,
        merge_mode: str = "columns",
    ):
        open_files(
            self,
            file_handles=file_handles,
            file_type=file_type,
            append=append,
            merge_mode=merge_mode,
        )

    def show_merge_dialog(self, title):
        return show_merge_dialog(self, title)

    def onOpenCsv(
        self,
        event,
        filenames: List[str] = None,
        append: bool = False,
        merge_mode: str = "columns",
    ):
        open_csv(self, filenames, append, merge_mode)

    def onOpenChiSurfSampling(
        self,
        filenames=None,
        append: bool = False,
        merge_mode: str = "columns",
    ):
        open_sampling(self, filenames, append, merge_mode)

    def onOpenMfdHdf5(
        self,
        event,
        filenames=None,
        append: bool = False,
        merge_mode: str = "columns",
    ):
        open_mfd_hdf5(self, filenames, append, merge_mode)

    def onOpenSmFRET(self, merge_mode: str = "columns"):
        open_smfret(self, merge_mode=merge_mode)

    def onOpenPto(
        self,
        event=None,
        filenames=None,
        append: bool = False,
        merge_mode: str = "columns",
    ):
        open_pto(self, filenames, append, merge_mode)

    def update_ui_data(self, *args, **kwargs):
        """
        Refresh UI elements based on current data source, constants, and equations.
        This includes re-computing columns and updating plots.
        """
        logging.debug(f"update_ui_data")
        ds = self.data_source
        if not getattr(ds, "is_computed", False):
            ds.compute_columns(
                constants=self.constants,
                equations=self.equations
            )
        self.lineEditCountTotal.setText(str(ds.size))
        self.plot_control.update()  # plot_control.update() - also updates plots
        # Keep UI enabled/disabled state in sync
        try:
            self.update_ui_enabled_state()
        except Exception:
            pass

    def update_ui_enabled_state(self) -> None:
        """
        Enable/disable most of the UI when there is no dataset loaded.
        Only data-loading actions remain enabled in the disabled state.
        Rules:
        - When no dataset: disable docks, plots, analysis actions and tool buttons.
          Keep only file-open actions (CSV, ChiSurf sampling, MFD HDF5, Paris dataset)
          and working path selection enabled so the user can load data.
        - When dataset present: enable everything.
        """
        try:
            # Important: use public property to check BOTH internal field AND data_manager
            ds = self.data_source
            has_data = bool(ds is not None and not ds.empty)
        except Exception:
            has_data = False

        # Whitelist of actions that are allowed even when no data is loaded
        allowed_when_empty = {
            "actionSelect_working_path",
            "actionOpenCsv",
            "actionOpenChiSurfSampling",
            "actionOpenMfdHdf5",
            "actionOpenParisDataset",
        }

        # Toggle all QAction members
        for name in dir(self):
            if not name.startswith("action"):
                continue
            try:
                act = getattr(self, name)
                # QAction has setEnabled; use duck typing
                if hasattr(act, "setEnabled"):
                    enable = has_data or (name in allowed_when_empty)
                    act.setEnabled(bool(enable))
            except Exception:
                pass

        # Toggle key dock widgets (disable content interactions when no data)
        for dock_name in [
            "dockWidget_PlotControl",
            "dockWidget_Parameters",
            "dockWidget_Overlays",
            "dockWidget_Fit",
            "dockWidget_Equations",
        ]:
            try:
                dock = getattr(self, dock_name, None)
                if dock is not None and hasattr(dock, "setEnabled"):
                    dock.setEnabled(bool(has_data))
            except Exception:
                pass

        # Toggle commonly used tool buttons and widgets
        for w_name in [
            "toolButton_screenshot",
            "toolButton_AutoContrast",
            "toolButton_3",  # table editor
            "toolButton_parameter_save",
            "comboBoxWeight",
            "checkBoxWeight",
            "checkBoxEnableZ",
        ]:
            try:
                w = getattr(self, w_name, None)
                if w is not None and hasattr(w, "setEnabled"):
                    w.setEnabled(bool(has_data))
            except Exception:
                pass

        # Keep the file/working-path widgets usable without data
        try:
            if hasattr(self, "lineEditWorkingPath") and self.lineEditWorkingPath is not None:
                self.lineEditWorkingPath.setEnabled(True)
        except Exception:
            pass

    def apply_fonts(self):
        ui_helpers.apply_fonts(self)

    def update_parameter_names(self):
        ui_helpers.update_parameter_names(self)

    def get_bins(self, arange, scale, n_1d, n_2d):
        return histogram_helpers.get_bins(self.plot_control, arange, scale, n_1d, n_2d)

    def get_x_bins(self):
        logging.debug(f"get_x_bins")
        return self.get_bins(
            self.plot_control.x_range,
            self.plot_control.scale_x,
            self.plot_control.n_xhist_1d,
            self.plot_control.n_xhist_2d
        )

    def get_y_bins(self):
        logging.debug(f"get_y_bins")
        return self.get_bins(
            self.plot_control.y_range,
            self.plot_control.scale_y,
            self.plot_control.n_yhist_1d,
            self.plot_control.n_yhist_2d
        )

    def get_z_bins(self):
        logging.debug(f"get_z_bins")
        bins = self.get_bins(
            self.plot_control.z_range,
            self.plot_control.scale_z,
            self.plot_control.n_zhist_1d,
            10
        )
        return bins

    def is_data_ready(self) -> bool:
        """Return True if data and axes are ready for histogram computation."""
        return histogram_helpers.is_data_ready(self)

    def update_histograms(self):
        """Update histograms using new histograms module."""
        plot_histograms.update_histogram_display(self)

    def copy_1d_hists_to_clipboard_csv(self):
        copy_1d_histograms(self)

    def copy_2d_hist_to_clipboard_json(self):
        copy_2d_hist_json(self)

    def copy_2d_hist_to_clipboard_csv(self):
        copy_2d_hist_csv(self)

    def update_plots(self, skip_clustering=False, skip_cache_invalidation=False):
        self._cancel_scheduled_plot_update()
        plot_update_helpers.update_plots(self, skip_clustering=skip_clustering, skip_cache_invalidation=skip_cache_invalidation)

    def request_plot_update(self, skip_clustering=False):
        """Ask for a redraw. **This is how a control says "something changed".**

        Requests inside one 40 ms window are *grouped* and *dispatched* once, so
        a control that fires continuously -- a dragged region, a spun value, a
        toggled check box -- costs one redraw per frame rather than one per
        signal. ``skip_clustering`` is OR-ed across the batch: if any request in
        it needed clustering, the dispatched update does it.

        Call :meth:`update_plots` directly only when the redraw must have
        happened before the next line runs: a load that has just replaced the
        data, an explicit "Update plot" action, or the parameter throttle, which
        times its own redraw to size its next window. Every *interactive* path
        belongs here. Handlers that called ``update_histograms()`` and then
        ``update_plots()`` computed every histogram twice, because
        ``update_plots`` fills them itself.

        Falls back to an immediate update before deferred init, when there is no
        event loop to batch with.
        """
        if not getattr(self, "_deferred_init_done", False):
            # Before full init we can't rely on timers—update immediately.
            return self.update_plots(skip_clustering=skip_clustering)

        timer = self._plot_update_timer
        if timer is None:
            self._initialize_plot_update_timer()
            timer = self._plot_update_timer
        if timer is None:
            # If timer creation still fails, run update immediately.
            return self.update_plots(skip_clustering=skip_clustering)

        self._plot_update_requires_clustering |= not skip_clustering
        self._plot_update_pending = True
        if not timer.isActive():
            timer.start()

    def _cancel_scheduled_plot_update(self):
        timer = self._plot_update_timer
        if timer is not None and timer.isActive():
            timer.stop()
        self._plot_update_pending = False
        self._plot_update_requires_clustering = False

    def _initialize_plot_update_timer(self) -> bool:
        """Create (or confirm) the batching timer used for plot updates."""
        if self._plot_update_timer is not None:
            return True
        try:
            timer = QtCore.QTimer(self)
            timer.setSingleShot(True)
            timer.setInterval(40)  # ms, batches rapid UI signals
            timer.timeout.connect(self._execute_scheduled_plot_update)
            self._plot_update_timer = timer
        except Exception as exc:
            logging.warning("Failed to create plot update timer: %s", exc)
            self._plot_update_timer = None
            return False
        self._plot_update_pending = False
        self._plot_update_requires_clustering = False
        return True

    def _execute_scheduled_plot_update(self):
        if not self._plot_update_pending:
            return
        skip_clustering = not self._plot_update_requires_clustering
        self._cancel_scheduled_plot_update()
        self.update_plots(skip_clustering=skip_clustering)

    def _schedule_parameter_recompute(self):
        """Throttle parameter-table edits into live, targeted recomputes.

        Diffs the current constants against the previous snapshot to learn which
        constant(s) changed and accumulates them. Rather than debouncing (which
        only updates after the user stops), this *throttles*: while a value keeps
        changing — mouse-wheel scrolling or dragging — the plot is refreshed
        periodically so it tracks the parameter live. The interval adapts to the
        measured recompute+redraw cost (``_recompute_interval_ms``), so it stays
        live on small data and does not thrash on very large data.
        """
        try:
            new_constants = dict(self.parameter_control.dict)
        except Exception:
            new_constants = {}
        prev = getattr(self, "_prev_constants", {})
        changed = {
            k for k in set(new_constants) | set(prev)
            if new_constants.get(k) != prev.get(k)
        }
        self._prev_constants = new_constants
        # When self.constants is the live mapping over the fitting-parameter group
        # leave it alone (it already reflects edits and crosslinks); only the
        # snapshot-dict fallback needs refreshing.
        if getattr(self.parameter_control, "constants_mapping", None) is None:
            self.constants = new_constants
        if changed:
            self._pending_changed_constants |= changed
        elif not self._pending_changed_constants:
            # Nothing changed and nothing pending (e.g. an unrelated fit event) —
            # don't arm a recompute+redraw for a no-op.
            return

        if self._parameter_recompute_timer is None:
            from qtpy import QtCore
            self._parameter_recompute_timer = QtCore.QTimer(self)
            self._parameter_recompute_timer.setSingleShot(True)
            self._parameter_recompute_timer.timeout.connect(self._flush_parameter_recompute)
        # Throttle, not debounce: only (re)arm when idle, so a continuous stream
        # of edits fires the update every interval instead of resetting the wait.
        if not self._parameter_recompute_timer.isActive():
            self._parameter_recompute_timer.start(getattr(self, "_recompute_interval_ms", 33))

    def _flush_parameter_recompute(self):
        """Run one targeted recompute for accumulated constant edits, live."""
        import time
        changed = self._pending_changed_constants
        self._pending_changed_constants = set()
        t0 = time.perf_counter()
        if changed:
            try:
                self.data_source.compute_columns(
                    constants=self.constants,
                    equations=self.equations,
                    changed_constants=changed,
                )
            except Exception as exc:
                logging.warning("Parameter recompute failed: %s", exc)
        self.update_plots()
        # Size the next throttle window to one update's cost, clamped to a live
        # range: ~30 fps on cheap data, backing off (never below ~6 fps) so a
        # slow redraw on huge data doesn't monopolise the event loop.
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        self._recompute_interval_ms = int(min(160.0, max(16.0, elapsed_ms)))
        # A change may have arrived while this update ran; keep tracking live.
        if self._pending_changed_constants and not self._parameter_recompute_timer.isActive():
            self._parameter_recompute_timer.start(self._recompute_interval_ms)

    def on_axis_selection_changed(self, _index: int = 0) -> None:
        """Re-derive the colour limits after an axis combo box changed.

        ``currentIndexChanged`` delivers the newly selected index. It is dropped
        here on purpose: bound to :meth:`update_spinbox_limits` directly it would
        arrive as ``low_pct``, which silently skews the contrast for any index
        below 100 and raises for any index above it.

        Parameters
        ----------
        _index : int, optional
            The combo box index Qt sends along; unused.
        """
        # A new third parameter needs its own range. ``fit_z_selection_to_axis``
        # was reached only from the gate's toggle, so choosing a different z
        # parameter left the region — and the axis it is drawn on — fitted to
        # the *previous* one: a marginal with 0 to 0 for its range under limits
        # belonging to a column that is no longer selected. It remembers which
        # axis it last fitted, so this is a no-op when z has not changed and it
        # never moves a region the user dragged.
        self.fit_z_selection_to_axis()
        self.update_spinbox_limits()

    def update_spinbox_limits(self, *, low_pct=0.1, high_pct=99, recompute=True):
        """Set the colour limits from robust percentiles of the 2D histogram.

        Parameters
        ----------
        low_pct, high_pct : float, optional
            Percentiles bounding the colour scale; both must lie in ``[0, 100]``.
            Keyword-only so a Qt signal argument can never bind to them.
        recompute : bool, optional
            Recompute the histograms first. Callers that just computed them pass
            ``False`` to avoid doing the work twice.
        """
        plot_update_helpers.update_spinbox_limits(self, low_pct=low_pct, high_pct=high_pct)

        # --- 2) Guard: are our selected column indices valid? ---
        p1_idx, p2_idx, p3_idx = self.plot_control.p1[0], self.plot_control.p2[0], self.plot_control.p3[0]
        try:
            # make sure values array has at least p1, p2, p3 rows
            n_rows, _ = self.values.shape
        except Exception:
            # values property may raise if data not ready
            return

        if not (0 <= p1_idx < n_rows and 0 <= p2_idx < n_rows and 0 <= p3_idx < n_rows):
            return

        # 1) Ensure a 2D histogram is available. When called from update_plots the
        #    histograms were just computed, so skip the (expensive) recompute --
        #    this previously doubled the histogram work on every interaction.
        h2 = self._histogram.get("2d")
        has_hist = hasattr(h2, "H") or (isinstance(h2, tuple) and len(h2) == 3)
        if recompute or not has_hist:
            self.update_histograms()
        hist_2d = self._histogram.get("2d")
        if hasattr(hist_2d, 'H'):
            H = hist_2d.H
        elif isinstance(hist_2d, tuple) and len(hist_2d) == 3:
            H = hist_2d[0]
        else:
            return

        # 2) Robust limits, in the units the map is drawn in.
        from .histograms import colour_limits

        vmin, vmax = colour_limits(H, self.checkBoxLogCounts.isChecked(), low_pct, high_pct)

        # 3) Push to spin-boxes and the image
        self.vmin, self.vmax = vmin, vmax
        self.cax.set_lut_range([vmin, vmax])
        self.g_2dplot.replot()

    def setup_clustering_button(self):
        """
        Set up a button to show/hide the clustering dialog.
        """
        logging.debug("setup_clustering_button()")
        clustering_helpers.setup_button(self)

    def toggle_clustering_dialog(self):
        """
        Show or hide the clustering dialog.
        """
        logging.debug("toggle_clustering_dialog()")
        clustering_helpers.toggle_dialog(self)

    def create_clustering_dialog(self):
        """
        Create the clustering dialog if it doesn't exist.
        """
        logging.debug("create_clustering_dialog()")
        clustering_helpers.ensure_dialog(self)

    def update_clustering_dialog(self):
        """
        Update the clustering dialog UI elements.
        """
        logging.debug("update_clustering_dialog()")
        clustering_helpers.update_dialog(self)


    def start_clustering_from_dialog(self, method, columns, params):
        """
        Start clustering with parameters from the dialog.

        Args:
            method: The clustering method to use (e.g., 'kmeans', 'hdbscan')
            columns: Set of column names to use for clustering
            params: Dictionary of parameters for the clustering method
        """
        logging.debug(f"start_clustering_from_dialog(method={method}, columns={columns}, params={params})")
        clustering_helpers.start_clustering_from_dialog(self, method, columns, params)

    def cancel_clustering(self):
        """
        Cancel the current clustering operation.
        """
        logging.debug("cancel_clustering()")
        clustering_helpers.cancel_clustering(self)

    def on_select_columns(self):
        """
        Open a dialog to select columns for clustering.
        """
        logging.debug("on_select_columns()")
        clustering_helpers.select_columns(self)


    def on_apply_clustering(self):
        """
        Apply clustering with current parameters and update plots.
        """
        logging.info("Applying clustering with current parameters")
        self._use_clustering = True
        logging.debug("Set _use_clustering flag to True")
        clustering_helpers.apply_clustering(self)

    def on_cancel_clustering(self):
        """
        Cancel the current clustering operation.
        """
        logging.info("Cancelling clustering operation")
        clustering_helpers.cancel_clustering(self)

    def on_clustering_progress(self, progress):
        """
        Update the progress bar with the current clustering progress.

        Args:
            progress: Integer value between 0 and 100 representing the progress percentage
        """
        logging.debug(f"Clustering progress: {progress}%")

        # Update progress in dialog if it exists
        if self.clustering_dialog is not None and self.clustering_dialog.isVisible():
            self.clustering_dialog.update_progress(progress)
            logging.debug(f"Updated clustering dialog progress bar to {progress}%")

    def on_clustering_error(self, error_message):
        """
        Handle errors that occur during clustering.

        Args:
            error_message: String containing the error message
        """
        logging.warning(f"Clustering error: {error_message}")

        # Clear any partial clustering results
        self._cluster_labels = None
        self._cluster_probabilities = None

        # Set the _use_clustering flag to False
        self._use_clustering = False
        logging.debug("Set _use_clustering flag to False due to error")

        # Update dialog if it exists
        if self.clustering_dialog is not None and self.clustering_dialog.isVisible():
            self.clustering_dialog.clustering_completed(success=False)

        # Display an error message to the user
        QtWidgets.QMessageBox.critical(
            self,
            "Clustering Error",
            f"An error occurred during clustering:\n\n{error_message}\n\nPlease try again with different parameters."
        )

    def on_clustering_done(self, result):
        """
        Handle the completion of clustering.

        Args:
            result: Tuple containing cluster labels and probabilities
        """
        logging.info("Clustering completed")

        # Update the cluster labels and probabilities
        self._cluster_labels, self._cluster_probabilities = result

        # Initialize the cluster data shape if it doesn't exist
        if not hasattr(self, '_cluster_data_shape'):
            self._cluster_data_shape = len(self._cluster_labels) if self._cluster_labels is not None else 0
            logging.debug(f"Initialized cluster data shape: {self._cluster_data_shape}")

        # If result is None, it means clustering was cancelled or failed
        if result[0] is None:
            logging.info("Clustering was cancelled or failed")

            # Set the _use_clustering flag to False
            self._use_clustering = False
            logging.debug("Set _use_clustering flag to False due to cancellation or failure")

            # Update dialog if it exists
            if self.clustering_dialog is not None and self.clustering_dialog.isVisible():
                self.clustering_dialog.clustering_completed(success=False)

            return

        # Write the cluster columns into the table now that we are back on the
        # GUI thread. The worker deliberately does not do this: assigning to
        # data_source touches widgets, and doing that from a QThread deadlocks.
        if self._cluster_probabilities is not None:
            try:
                clustering_helpers.store_clustering_result(
                    self, self._cluster_labels, self._cluster_probabilities
                )
            except Exception:
                logging.error("Could not store the clustering result", exc_info=True)

        # Adjust the spinBoxCluster range based on the number of clusters
        if self._cluster_labels is not None:
            # Get the unique cluster labels
            unique_clusters = np.unique(self._cluster_labels)
            # Count the number of clusters (excluding noise points with label -1)
            n_clusters = len([c for c in unique_clusters if c >= 0])
            # Set the maximum value of spinBoxCluster to (n_clusters - 1)
            self.plot_control.spinBoxCluster.setMaximum(n_clusters - 1)
            logging.debug(f"Adjusted spinBoxCluster range to (-1, {n_clusters - 1})")

        # Update dialog if it exists
        if self.clustering_dialog is not None and self.clustering_dialog.isVisible():
            self.clustering_dialog.clustering_completed(success=True)

        # Report completion without a modal dialog. A QMessageBox here blocks on
        # its own event loop until someone clicks it, so any headless or
        # automated run -- a test, a batch script, an offscreen render -- hangs
        # here forever with no indication why.
        method = getattr(self.clustering_dialog, "_cluster_method", "clustering")
        message = f"Clustering using {str(method).upper()} completed successfully."
        logging.info(message)
        try:
            self.statusBar().showMessage(message, 8000)
        except Exception:  # pragma: no cover - no status bar in some hosts
            logging.debug("no status bar to report clustering completion on")


    def perform_clustering(self, method=None, worker=None, **kwargs) -> Tuple[Optional[np.ndarray], Optional[np.ndarray]]:
        return clustering_helpers.perform_clustering(self, method=method, worker=worker, **kwargs)

    def keyPressEvent(self, event):
        """
        Handle key press events.

        Args:
            event: The key event
        """
        logging.debug("keyPressEvent: event.key() = {}".format(event.key()))
        # Check if Ctrl+L was pressed to toggle clustering dialog
        if (event.modifiers() & QtCore.Qt.ControlModifier) and event.key() == QtCore.Qt.Key_L:
            # Open the clustering dialog
            self.toggle_clustering_dialog()
        else:
            # For other keys, call the parent class implementation
            super(NDXplorer, self).keyPressEvent(event)

    def closeEvent(self, event):
        """
        Handle the window close event.
        Clean up resources before closing.
        """
        logging.debug("closeEvent()")
        # Clean up any existing worker thread
        if hasattr(self, 'clustering_worker') and self.clustering_worker is not None:
            # Disconnect any existing connections
            try:
                self.clustering_worker.clustering_done.disconnect(self.on_clustering_done)
                self.clustering_worker.clustering_error.disconnect(self.on_clustering_error)
                self.clustering_worker.progress_updated.disconnect(self.on_clustering_progress)
            except (TypeError, RuntimeError):
                # No connections exist, or the signal was not connected to this slot
                pass

            # Stop the worker if it's running
            if self.clustering_worker.isRunning():
                self.clustering_worker.stop()
                self.clustering_worker.wait()

            # Delete the worker
            self.clustering_worker.deleteLater()
            self.clustering_worker = None

        # The Gaussians are published as a crosslinkable parameter group; a
        # registered group whose window is gone is a link target nothing can
        # edit any more.
        if getattr(self, "gaussian_fit", None) is not None:
            try:
                self.gaussian_fit.close()
            except Exception:
                logging.debug("Gaussian parameter group teardown failed", exc_info=True)

        # Call the base class implementation
        super(NDXplorer, self).closeEvent(event)

    def fit_z_selection_to_axis(self) -> None:
        """Put the dynamic-z region over the whole axis when the axis changes.

        The region is created at a hardcoded 0.25 to 0.5 and nothing moved it
        afterwards, so choosing a third axis whose values live anywhere else --
        a lifetime in nanoseconds, a photon count -- gated the plot to a window
        containing no data. Everything went empty, with nothing on screen to say
        that a selection was responsible.

        The test is whether the region has been positioned for THIS axis, not
        whether it happens to lie inside it: 0.25 to 0.5 is inside an axis
        running to 6, and still selects nothing. So the axis it was last fitted
        to is remembered, and a different one -- a different parameter, or the
        same parameter rescaled -- puts it back over the full range, which is
        what "no selection yet" means. A region the user has dragged on the
        axis it belongs to is never touched.
        """
        if not hasattr(self, "selection_z"):
            return
        try:
            control = self.plot_control
            lo, hi = float(control.zmin), float(control.zmax)
            if not (np.isfinite(lo) and np.isfinite(hi)) or hi <= lo:
                return
            # The scale is part of the axis's identity, not a detail of how it
            # is drawn: the region item stores *view* coordinates, so switching
            # between linear and log leaves it holding numbers that mean
            # something else entirely (60 becomes 10**60). Without the scale in
            # this key the refit is skipped exactly when it is needed most.
            axis = (control.p3[0], lo, hi, getattr(control, "scale_z", "lin"))
            if getattr(self, "_z_selection_axis", None) == axis:
                return
            self._z_selection_axis = axis
            self.selection_z.set_range(lo, hi)
            self._last_z_range = (lo, hi)
            logging.info("Z axis is now %s over %g..%g; the selection spans it",
                         control.p3[1], lo, hi)
        except Exception as exc:            # pragma: no cover - GUI defensive
            logging.debug("Could not fit the z selection to the axis: %s", exc)

    def on_z_selection_changed(self):
        """Redraw for the range the user is dragging.

        Connected to the region's own change signal. It used to be a 500 ms
        timer comparing ``get_range()`` against the last value it saw, which
        made the plot follow a drag at two frames a second and lag up to half a
        second behind the mouse -- on data where the redraw itself costs about
        forty milliseconds.

        ``request_plot_update`` is debounced, so this can be connected to the
        *live* signal: a burst of mouse moves coalesces into one redraw per
        frame instead of one per move. Clustering is skipped, as it was: the
        labels do not depend on the z range.
        """
        if not self._dynamic_selection:
            return
        if not (hasattr(self, "checkBoxEnableZ") and self.checkBoxEnableZ.isChecked()):
            return
        self.request_plot_update(skip_clustering=True)

    def on_enable_z_changed(self, state):
        """
        Handle changes to the Z-axis groupbox toggle.

        Args:
            state: The new state of the groupbox (True for checked, False for unchecked)
        """
        logging.debug(f"on_enable_z_changed(state={state})")
        # The plot stays visible: this box arms the *gate*, not the picture.
        # Its range still has to be put somewhere sensible the first time the
        # gate is armed, which is what fit_z_selection_to_axis does below.
        # Turning the axis on is the other moment the region can be off it.
        if state:
            self.fit_z_selection_to_axis()
        
        # Enable/disable the Z axis update button based on the checkbox state
        if hasattr(self, 'plot_control') and hasattr(self.plot_control, 'toolButtonSetZAxis'):
            self.plot_control.toolButtonSetZAxis.setEnabled(bool(state))
            logging.debug(f"Z axis update button enabled: {bool(state)}")

        self.request_plot_update(skip_clustering=True)

    def on_weight_param_changed(self, index):
        """
        Handle changes to the selected weight parameter.

        Args:
            index: The index of the newly selected item in the combobox
        """
        logging.debug(f"on_weight_param_changed(index={index})")
        # Only update if weight is enabled
        if self.checkBoxWeight.isChecked():
            self.request_plot_update(skip_clustering=True)

    def on_weight_changed(self, state):
        """
        Handle changes to the weight checkbox.

        Args:
            state: The new state of the checkbox (Qt.Checked or Qt.Unchecked)
        """
        logging.debug(f"on_weight_changed(state={state})")
        # Enable/disable comboBoxWeight based on checkbox state
        is_checked = bool(state)
        self.comboBoxWeight.setEnabled(is_checked)

        # If weight is checked, populate the comboBoxWeight with available parameters
        if is_checked:
            # Save current selection if any
            current_text = self.comboBoxWeight.currentText()

            # Clear and populate the combobox
            self.comboBoxWeight.clear()

            # Get parameter names from data source
            if self.data_source is not None and hasattr(self.data_source, 'parameter_names'):
                param_names = self.data_source.parameter_names
                for name in param_names:
                    self.comboBoxWeight.addItem(name)

                # Restore previous selection if it exists in the new list
                if current_text and current_text in param_names:
                    index = self.comboBoxWeight.findText(current_text)
                    if index >= 0:
                        self.comboBoxWeight.setCurrentIndex(index)
                # Otherwise, default to z-axis parameter for backward compatibility
                elif self.plot_control.z_label in param_names:
                    index = self.comboBoxWeight.findText(self.plot_control.z_label)
                    if index >= 0:
                        self.comboBoxWeight.setCurrentIndex(index)

        self.request_plot_update(skip_clustering=True)

    def on_dynamic_selection_changed(self, state):
        """
        Handle changes to the dynamic selection checkbox.
        Applies dynamic selection for X/Y histograms regardless of Z axis state,
        but Z-range filtering only applies when Z axis is enabled.

        Args:
            state: The new state of the checkbox (Qt.Checked or Qt.Unchecked)
        """
        logging.debug(f"on_dynamic_selection_changed(state={state})")
        
        self._dynamic_selection = bool(state)
        self.request_plot_update(skip_clustering=True)

    def add_umap_columns(self, columns, params):
        """
        Add UMAP projection columns to the table via helper utilities.
        """
        logging.info("Adding UMAP columns to the table")
        return umap_helpers.add_umap_columns(
            ndxplorer=self,
            columns=columns,
            params=params,
            progress_dialog_factory=self._create_umap_progress_dialog,
        )

    def add_pca_columns(self, columns, params):
        """Add ``PC_n`` columns to the table and return the decomposition.

        The result is handed back rather than discarded because the loadings are
        what PCA was asked for -- which measured parameters carry the separation
        -- and the dialog reports them. The columns are only how you plot it.
        """
        logging.info("Adding PCA columns to the table")
        return pca_helpers.add_pca_columns(
            ndxplorer=self,
            columns=list(columns),
            n_components=int(params.get("n_components", 2)),
            standardize=bool(params.get("standardize", True)),
        )

    def _create_umap_progress_dialog(self, title: str) -> UMAPProgressDialog:
        """Factory used by umap_helpers to create/show the worker dialog."""
        dialog = UMAPProgressDialog(self, title)
        dialog.show()
        return dialog

    def refresh_axis_comboboxes_preserving_selection(self) -> None:
        """Reload axis combobox contents while keeping current selections."""
        if (
            not hasattr(self, "plot_control")
            or self.data_source is None
            or getattr(self.data_source, "parameter_names", None) is None
        ):
            return

        pn = self.data_source.parameter_names
        combos = [
            getattr(self.plot_control, "comboBoxSelX", None),
            getattr(self.plot_control, "comboBoxSelY", None),
            getattr(self.plot_control, "comboBoxSelZ", None),
        ]
        current_texts = [combo.currentText() if combo is not None else "" for combo in combos]

        for combo in combos:
            if combo is not None:
                combo.blockSignals(True)

        try:
            for idx, combo in enumerate(combos):
                if combo is None:
                    continue
                combo.clear()
                combo.addItems(pn)
                previous = current_texts[idx]
                if previous in pn:
                    combo.setCurrentText(previous)
        finally:
            for combo in combos:
                if combo is not None:
                    combo.blockSignals(False)

    def create_umap_plot(self, columns, params):
        """
        Create a UMAP plot in a separate window using existing data.
        Note: This function does not add UMAP columns to the table.
        Use add_umap_columns() first if needed.

        Args:
            columns: Set of column names to use for UMAP
            params: Dictionary of parameters for UMAP
                n_neighbors: Number of neighbors to consider for each point
                min_dist: Minimum distance between points in the embedding
                n_components: Number of components (dimensions) for the embedding
                n_jobs: Number of parallel jobs for UMAP computation
        """
        logging.debug(f"create_umap_plot(columns={columns}, params={params})")

        # Get cluster labels if available
        cluster_labels = None
        if hasattr(self, '_cluster_labels') and self._cluster_labels is not None:
            cluster_labels = self._cluster_labels

        # Call the UMAP plot function from the plot_umap module
        plot_umap.create_umap_plot(
            parent=self,
            columns=columns,
            params=params,
            data_source=self.data_source,
            x_values=self.x_values,
            y_values=self.y_values,
            z_values=self.z_values,
            cluster_labels=cluster_labels
        )

    def _wants_cluster_colors(self) -> bool:
        """Whether the 2-D map should be coloured by cluster rather than density."""
        box = getattr(getattr(self, "plot_control", None), "checkBoxColorClusters", None)
        if box is None or not box.isChecked():
            return False
        return getattr(self, "_cluster_labels", None) is not None

    def _cluster_color_image(self, x_edges, y_edges):
        """Return the cluster-coloured RGB image for the current axes, or None.

        Returns ``None`` rather than raising whenever the overlay cannot be
        built -- no labels, a length mismatch after a data change, an empty
        selection -- so a stale or impossible overlay degrades to the ordinary
        density map instead of taking the plot down.
        """
        from ..plotting.cluster_overlay import cluster_rgb_image

        labels = getattr(self, "_cluster_labels", None)
        if labels is None:
            return None
        try:
            x_values = np.asarray(self.x_values).ravel()
            y_values = np.asarray(self.y_values).ravel()
        except Exception:
            logging.debug("cluster colouring: axis values unavailable", exc_info=True)
            return None
        labels = np.asarray(labels).ravel()
        if labels.size != x_values.size:
            # The labels belong to a different dataset than the one on screen.
            logging.debug(
                "cluster colouring skipped: %d labels for %d points",
                labels.size, x_values.size,
            )
            return None
        try:
            return cluster_rgb_image(
                x_values, y_values, labels, x_edges, y_edges,
                log_counts=self.checkBoxLogCounts.isChecked(),
            )
        except Exception:
            logging.debug("cluster colouring failed", exc_info=True)
            return None

    def update_2d_plot(self):
        """
        Update the 2D histogram plot using clean histogram objects.
        """
        logging.debug("[DISPLAY] update_2d_plot() called")
        try:
            hist_2d = self._histogram.get("2d")
            if hist_2d is None:
                logging.debug("[DISPLAY] No 2D histogram available yet")
                return
            
            logging.debug(f"[DISPLAY] Retrieved hist_2d type={type(hist_2d)}, has H attr={hasattr(hist_2d, 'H')}")
            
            # Extract data from 2D histogram (handle both old tuple and new clean formats)
            if hasattr(hist_2d, 'H'):
                # New clean Histogram2D object
                H = hist_2d.H
                x_edges = hist_2d.x_edges
                y_edges = hist_2d.y_edges
                logging.debug(f"[DISPLAY] Extracted from Histogram2D: H shape={H.shape}, dtype={H.dtype}")
                logging.debug(f"[DISPLAY] H contiguous={H.flags['C_CONTIGUOUS']}, min={np.min(H)}, max={np.max(H)}, sum={np.sum(H)}")
            elif isinstance(hist_2d, tuple) and len(hist_2d) == 3:
                # Old tuple format (H, x_edges, y_edges)
                H, x_edges, y_edges = hist_2d
                logging.debug(f"[DISPLAY] Extracted from tuple: H shape={H.shape}, dtype={H.dtype}")
                logging.debug(f"[DISPLAY] H contiguous={H.flags['C_CONTIGUOUS']}, min={np.min(H)}, max={np.max(H)}, sum={np.sum(H)}")
                logging.debug(f"[DISPLAY] x_edges length={len(x_edges)}, y_edges length={len(y_edges)}")
            else:
                logging.error("[DISPLAY] Invalid 2D histogram format")
                return
                
        except (ValueError, TypeError) as e:
            logging.warning(f"No 2D histogram data available: {e}")
            return

        # Guard for empty/invalid
        if H is None or H.size == 0 or np.all(np.isnan(H)):
            H = np.zeros((1, 1))
            x_edges = np.array([0.0, 1.0])
            y_edges = np.array([0.0, 1.0])

        # Initialize mask shape when histogram is updated
        if hasattr(self, 'plot_control') and hasattr(self.plot_control, 'mask_widget'):
            # Calculate bin counts from edges
            nx_bins = len(x_edges) - 1
            ny_bins = len(y_edges) - 1
            # Set mask shape to match TRANSPOSED/DISPLAYED image: (ny_bins, nx_bins)
            mask_shape = (ny_bins, nx_bins)
            self.plot_control.mask_widget.set_mask_shape(mask_shape)
            logging.debug(f"Set mask shape to {mask_shape} (ny={ny_bins}, nx={nx_bins}) for TRANSPOSED display, histogram shape {H.shape}, edges: x={len(x_edges)}, y={len(y_edges)}")
        
        # Optional log counts (safe for zeros)
        from .histograms import display_counts

        data = display_counts(H, self.checkBoxLogCounts.isChecked())

        # H is already in (ny, nx) shape, no transpose needed for display
        img = np.ascontiguousarray(data)

        # Cluster colouring replaces the density map with an RGB image in which
        # every cluster carries its own colour. It shares the same bin edges, so
        # the two views are directly comparable, and it falls back silently to
        # the density map whenever there is nothing to colour by.
        if self._wants_cluster_colors():
            rgb = self._cluster_color_image(x_edges, y_edges)
            if rgb is not None:
                img = rgb
        
        logging.debug(f"[DISPLAY] Final image data before set_data():")
        logging.debug(f"[DISPLAY]   Original H shape: {H.shape}, data shape: {data.shape}, img shape: {img.shape}")
        logging.debug(f"[DISPLAY]   Expected img shape: ({len(y_edges)-1}, {len(x_edges)-1})")
        logging.debug(f"[DISPLAY]   Shape match: {img.shape == (len(y_edges)-1, len(x_edges)-1)}")
        logging.debug(f"[DISPLAY]   img dtype: {img.dtype}, contiguous: {img.flags['C_CONTIGUOUS']}")
        logging.debug(f"update_2d_plot: H min={np.min(H)}, max={np.max(H)}, data min={np.min(data)}, max={np.max(data)}")
        try:
            self.cax.set_data(img)
            logging.debug(f"[DISPLAY] Successfully set image data to cax widget")
        except Exception as e:
            # Fallback to a trivial image if anything goes wrong
            logging.error(f"[DISPLAY] Failed to set image data: {e}")
            self.cax.set_data(np.zeros((1, 1)))

        # Apply colormap/contrast
        try:
            self.cax.set_colormap(self.cax._colormap_name, self.vmin, self.vmax)
        except Exception:
            pass

        # Set axis scales
        self.g_2dplot.set_axis_scale('xBottom', 0, len(x_edges)-1)
        self.g_2dplot.set_axis_scale('yLeft', 0, len(y_edges)-1)

        # Synchronize overlay plot axis scales
        if hasattr(self, 'overlay_plot') and self.overlay_plot is not None:
            self.overlay_plot.setAxisScale(0, 0, len(x_edges)-1)
            self.overlay_plot.setAxisScale(1, 0, len(y_edges)-1)

            margin_left = 50 if self.g_2dplot.axis_enabled('yLeft') else 0
            margin_right = 50 if self.g_2dplot.axis_enabled('yRight') else 0
            margin_top = 30 if self.g_2dplot.axis_enabled('xTop') else 0
            margin_bottom = 30 if self.g_2dplot.axis_enabled('xBottom') else 0
            self.overlay_plot.set_margins(margin_left, margin_right, margin_top, margin_bottom)

            self.overlay_plot.replot()

        # Replot
        logging.debug(f"[DISPLAY] Calling g_2dplot.replot()")
        self.g_2dplot.replot()
        if hasattr(self.g_2dplot, 'show'):
            self.g_2dplot.show()
        if hasattr(self.g_2dplot, 'update'):
            self.g_2dplot.update()

        # An overlay curve is drawn in *bin* coordinates against these very
        # edges, so a new histogram leaves it describing the old one -- drawn
        # over data it no longer matches, which is worse than not drawn at all.
        # This is the one place a new histogram becomes the displayed image, so
        # it is the one place the overlays have to follow.
        self._refresh_curve_overlays()

        logging.debug(f"[DISPLAY] Completed 2D plot update: H shape={H.shape}, edges: x={len(x_edges)}, y={len(y_edges)}")

    def _refresh_curve_overlays(self) -> None:
        """Redraw every overlay layer for the histogram now on screen.

        The 2-D overlay is one painting surface with three producers -- the
        equation curves, the Gaussian ellipses and the server-driven line sets
        -- and all three are drawn in *bin* coordinates. A new histogram
        therefore invalidates all of them, so all of them are redrawn here;
        each producer clears only its own layer.
        """
        if getattr(self, "_refreshing_overlays", False):
            return
        self._refreshing_overlays = True
        try:
            self.update_curve_overlays()
        except Exception as exc:
            logging.warning("Could not update the curve overlays: %s", exc)
        try:
            if getattr(self, "gaussian_fit", None) is not None:
                self.gaussian_fit._redraw_gaussian_overlays_from_table()
        except Exception as exc:
            logging.warning("Could not update the Gaussian overlays: %s", exc)
        try:
            from ..phasor_integration import redraw_line_overlays

            redraw_line_overlays(self)
        except Exception as exc:
            logging.warning("Could not update the server line overlays: %s", exc)
        finally:
            self._refreshing_overlays = False

    def bin_to_value(self, bin_idx, edges):
        """Convert a bin index to a value (center of the bin).

        Args:
            bin_idx: The bin index
            edges: The bin edges array

        Returns:
            The center value of the bin, or None if the bin index is invalid
        """
        logging.debug(f"bin_to_value(bin_idx={bin_idx}, edges={edges})")
        if bin_idx < 0 or bin_idx >= len(edges) - 1:
            return None
        return (edges[bin_idx] + edges[bin_idx + 1]) / 2

    def value_to_bin(self, value, edges):
        """Convert a value to a bin index with linear interpolation.

        Args:
            value: The value to convert
            edges: The bin edges array

        Returns:
            The bin index (as a float for interpolation), or None if the value is outside the range
        """
        logging.debug(f"value_to_bin(value={value}, edges={edges})")
        for i in range(len(edges) - 1):
            if edges[i] <= value <= edges[i + 1]:
                # Calculate the relative position within the bin (0.0 to 1.0)
                bin_width = edges[i + 1] - edges[i]
                if bin_width == 0:  # Avoid division by zero
                    return float(i)
                relative_pos = (value - edges[i]) / bin_width
                # Return the bin index plus the relative position
                return float(i) + relative_pos
        return None

    def bin_to_x_value(self, bin_idx, x_edges):
        """Convert a bin index to an x value (center of the bin)."""
        return self.bin_to_value(bin_idx, x_edges)

    def bin_to_y_value(self, bin_idx, y_edges):
        """Convert a bin index to a y value (center of the bin)."""
        return self.bin_to_value(bin_idx, y_edges)

    def x_value_to_bin(self, x_value, x_edges):
        """Convert an x value to a bin index with linear interpolation."""
        return self.value_to_bin(x_value, x_edges)

    def y_value_to_bin(self, y_value, y_edges):
        """Convert a y value to a bin index with linear interpolation."""
        return self.value_to_bin(y_value, y_edges)

    def on_auto_contrast(self):
        """Delegate auto-contrast adjustment to helper module."""
        plot_update_helpers.auto_contrast(self)

    def marginal_for_fit(self, axis="x"):
        """Return ``(centers, counts, edges)`` of a displayed 1-D marginal.

        ``plot_histogram`` hands a 1-D histogram back as ``(edges, counts)`` --
        reading it the other way round left the fit with counts as its x and
        edges as its y, and every marginal fit refused with "need at least 3
        matching data points" (the two differ in length by one).
        """
        from ..analysis.curve_fit import bin_centers
        from ..plotting.histograms import plot_histogram

        edges, counts = plot_histogram(self, axis)
        edges = np.asarray(edges, dtype=float)
        counts = np.asarray(counts, dtype=float)
        centers = bin_centers(edges) if edges.size == counts.size + 1 else edges
        return centers, counts, edges

    # -- data parameters (constants that move the population) ---------------
    def fit_data_reader(self):
        """Freeze how a fit reads the plotted values, and what it recomputes.

        Returns ``(read, targets)``: ``read()`` gives ``(x, y, weights)`` of the
        visible points, ``targets`` names the columns a recompute has to produce.

        Everything expensive is done once, here, because the fit calls ``read``
        once per model evaluation:

        * the **gate is frozen** to the rows visible now. Re-deriving it per step
          would cost a full mask over every column, and would also let the fitted
          population change under the fit, which is not a fit of anything.
        * only the **two plotted columns** are read, straight from the numeric
          frame. ``data_source.values`` rebuilds a copy of the whole table on
          every change, which is exactly what a fit does thousands of times.
        """
        rows = np.flatnonzero(~np.asarray(self.value_mask, dtype=bool))
        x_name = self.plot_control.x_label
        y_name = self.plot_control.y_label
        box = getattr(self, "checkBoxWeight", None)
        weight_name = (
            self.comboBoxWeight.currentText()
            if box is not None and box.isChecked() and hasattr(self, "comboBoxWeight")
            else None
        )
        targets = [n for n in (x_name, y_name) if n]

        def read():
            return self.read_fit_columns(x_name, y_name, weight_name, rows)

        return read, targets

    def read_fit_columns(self, x_name, y_name, weight_name, rows):
        """``(x, y, weights)`` for ``rows``, from the two named columns only."""
        source = self.data_source
        d1 = source.column_values(x_name)
        d2 = source.column_values(y_name)
        if d1 is None or d2 is None:
            return np.empty(0), np.empty(0), None
        d1, d2 = d1[rows], d2[rows]
        weights = None
        if weight_name:
            column = source.column_values(weight_name)
            if column is not None:
                weights = column[rows]
        # The joint-axis gate, cheap and re-applied because a recompute can turn
        # a value into nan (a background subtraction crossing zero, say).
        good = np.isfinite(d1) & np.isfinite(d2)
        if not good.all():
            d1, d2 = d1[good], d2[good]
            weights = None if weights is None else weights[good]
        return d1, d2, weights

    def cloud_for_fit(self, x_edges, y_edges, values=None, counts=None):
        """The displayed distribution as weighted points: one per **bin**.

        What a curve is fitted to when "Fit through the cloud" is chosen. A
        reduction to one point per column cannot describe a *population*: a blob
        reduces to a horizontal streak across its own columns, and no line
        through those streaks passes through the blob and the next population as
        well — which is what a person means by "the population is on the line".

        Every bin is returned, empty ones included with a weight of zero, so
        that the point set does not change while a fitted constant slides the
        population from one bin into another: the optimiser's residual vector
        has to keep its length, and a population that moves must be able to
        arrive somewhere.
        """
        if counts is None:
            if values is None:
                read, _ = self.fit_data_reader()
                values = read()
            d1, d2, weights = values
            counts = self.histogram_on_edges(d1, d2, x_edges, y_edges, weights)
        counts = np.asarray(counts, dtype=float)
        xc = 0.5 * (np.asarray(x_edges, float)[:-1] + np.asarray(x_edges, float)[1:])
        yc = 0.5 * (np.asarray(y_edges, float)[:-1] + np.asarray(y_edges, float)[1:])
        gx, gy = np.meshgrid(xc, yc, indexing="ij")
        return gx.ravel(), gy.ravel(), counts.ravel()

    def histogram_on_edges(self, d1, d2, x_edges, y_edges, weights=None):
        """Bin values on given edges, x-first ``(nx, ny)``, without drawing."""
        from ..utils.fast_histogram import fast_histogram_2d

        counts, _, _ = fast_histogram_2d(
            np.asarray(d1, dtype=float), np.asarray(d2, dtype=float),
            [np.asarray(x_edges, dtype=float), np.asarray(y_edges, dtype=float)],
            weights=weights,
        )
        return np.asarray(counts, dtype=float)

    def _constants_shaping_data(self):
        """The constants the equations actually use, as live parameters.

        A constant that no equation reads (``KB``, ``T_K`` on a plot that does
        not use them) cannot move the data, so offering it to the fit would only
        add a flat direction to the optimiser. Equations name a constant quoted
        -- ``'gG/gR'`` -- which is what makes this an exact match rather than a
        substring hunt.
        """
        group = getattr(self.parameter_control, "parameter_group", None)
        if group is None:
            return []
        blob = []
        for equation in (self.equations or []):
            if isinstance(equation, dict):
                for key, expression in equation.items():
                    blob.append(f"{key} {expression}")
            else:
                blob.append(str(equation))
        text = " ".join(blob)
        return [p for p in group.parameters_all if f"'{p.name}'" in text]

    def recompute_for_constants(self, changed, targets=None) -> None:
        """Re-derive the columns that depend on the named constants.

        ``targets`` narrows that to the columns those names need — inside a fit,
        the two plotted axes. One constant can feed forty derived columns (every
        PIE variant, every distance), and a fit that recomputes all of them per
        step spends nearly all its time on columns nobody is looking at.
        """
        changed = {str(c) for c in changed}
        self.data_source.compute_columns(
            constants=self.constants,
            equations=self.equations,
            changed_constants=changed or None,
            targets=targets,
        )

    def build_data_parameters(self, target, x_edges, y_edges=None, keep=None,
                              min_counts=3.0, reduction="cloud"):
        """Offer the data-shaping constants to a curve fit.

        Parameters
        ----------
        target : {'2d', 'x', 'y'}
            What the curve is fitted to; decides how the data is re-derived.
        x_edges : array_like
            Bin edges of the fitted axis (for a marginal, its own edges).
        y_edges : array_like, optional
            The second axis's edges, for ``target='2d'``.
        keep : array_like of bool, optional
            The columns the fit started with; held fixed so the residual keeps
            its length while the population moves.
        min_counts : float, optional
            Passed through to the reduction.
        reduction : {'population', 'mean'}, optional
            How a column is reduced to one point (see
            :func:`~ndxplorer.analysis.curve_fit.ridge_from_values`).

        Returns
        -------
        DataParameters or None
            ``None`` when there are no constants to offer (no chisurf parameter
            table, or no equation reads one).
        """
        from ..analysis.curve_fit import DataParameters, bin_centers, ridge_from_values
        from ..utils.fast_histogram import fast_histogram_1d

        parameters = self._constants_shaping_data()
        if not parameters:
            return None
        read, targets = self.fit_data_reader()
        edges = np.asarray(x_edges, dtype=float)
        density = getattr(self.plot_control, f"normed_hist_{target}", False)

        def refresh(changed):
            self.recompute_for_constants(changed, targets=targets)
            values = read()
            d1, d2, weights = values
            if target == "2d" and reduction == "cloud":
                px, py, w = self.cloud_for_fit(edges, y_edges, values)
                return px, py, np.full(py.shape, float(np.median(np.diff(y_edges)))), w
            if target == "2d":
                return ridge_from_values(
                    d1, d2, edges, weights=weights, y_edges=y_edges,
                    keep=keep, min_counts=min_counts, reduction=reduction,
                )
            _, counts = fast_histogram_1d(
                d1 if target == "x" else d2, edges, weights=weights, density=density
            )
            counts = np.asarray(counts, dtype=float)
            centers = bin_centers(edges) if edges.size == counts.size + 1 else edges
            return centers, counts, np.sqrt(np.maximum(counts, 1.0))

        return DataParameters(parameters=parameters, refresh=refresh)

    def build_curve_fit_for(self, curve, target="2d", reduction="cloud",
                            min_counts=3.0):
        """Build the fit of ``curve`` against what is displayed.

        Parameters
        ----------
        curve : CurveWidget
            The overlay curve. Its parameter group seeds the fit — value,
            bounds and fix/free come from the curve's own table, so those are
            set in one place.
        target : {'2d', 'x', 'y'}
            ``'2d'`` fits ``y = f(x)`` to the displayed two-dimensional
            distribution (one point per populated x column); ``'x'`` / ``'y'``
            fit the curve to that axis's marginal histogram of counts.
        reduction : {'population', 'mean'}, optional
            Which point of a column the curve is fitted through: the densest
            population's centre (default) or the column's average. A burst plot
            is a mixture, and the average of a mixture lies where nothing is.
        min_counts : float, optional
            Minimum number of bursts for a column to be fitted.

        Returns
        -------
        CurveFit
            Ready to ``run()``. nDXplorer's data-shaping constants are attached
            as :class:`~ndxplorer.analysis.curve_fit.DataParameters`, fixed
            until the user frees one.

        Raises
        ------
        CurveFitError
            If the equation cannot be fitted, or there is nothing displayed to
            fit it to.
        """
        import collections.abc

        from ..analysis.curve_fit import (
            CurveFitError,
            build_curve_fit,
            build_function_fit,
            build_marginal_fit,
            populated_columns,
            ridge_from_histogram,
        )
        from ..analysis.curve_fit import _oriented as _oriented_histogram

        def _oriented_counts(h, xe, ye):
            """The displayed histogram, x-first, as the cloud builder wants it."""
            return _oriented_histogram(h, xe, ye)[0]
        from ..plotting.histograms import plot_histogram

        equation = curve.get_equation()
        parametric = getattr(curve, "is_function", False)
        if not parametric and (not isinstance(equation, str) or not equation.strip()):
            raise CurveFitError("curve has no equation to fit")
        initial = curve.get_parameters()
        # ``self.constants`` is a live Mapping over the parameter group, not a
        # dict -- an isinstance(dict) test read it as empty, so no constant was
        # ever seeded into an equation fit or held fixed there.
        const_values = (
            dict(self.constants)
            if isinstance(self.constants, collections.abc.Mapping)
            else {}
        )
        text = equation if isinstance(equation, str) else ""
        constant_names = [k for k in const_values if k in text]
        # Constants are seeded from the constants table and start fixed.
        initial = dict(initial)
        for name in constant_names:
            try:
                initial[name] = float(const_values[name])
            except (TypeError, ValueError):
                pass

        # A parametric curve (a FRET line traced from a mean distance) is not
        # y = f(x), so it has no ParseModel; it is optimised through its own
        # function, over the parameters already in the curve's table.
        group = getattr(curve, "parameter_group", None)
        if parametric:
            if group is None:
                raise CurveFitError(
                    "fitting a function curve needs the chisurf parameter table"
                )
            params = list(group.parameters_all)

        if target == "2d":
            try:
                counts, edges = plot_histogram(self, "2d")
                x_edges, y_edges = edges
            except CurveFitError:
                raise
            except Exception as exc:
                raise CurveFitError(f"no 2-D histogram displayed ({exc})") from exc
            keep = populated_columns(counts, x_edges, y_edges, min_counts=min_counts)
            if reduction == "cloud":
                cf = self._build_cloud_fit(
                    curve, x_edges, y_edges,
                    params if parametric else None,
                    counts=_oriented_counts(counts, x_edges, y_edges),
                )
            else:
                if int(keep.sum()) < 3:
                    raise CurveFitError("too few populated columns to fit (need 3)")
                x, y, ey = ridge_from_histogram(
                    counts, x_edges, y_edges, keep=keep, reduction=reduction
                )
                if parametric:
                    cf = build_function_fit(curve.function, params, x, y, ey)
                else:
                    cf = build_curve_fit(
                        equation, x, y, ey,
                        initial=initial, constant_names=constant_names,
                    )
            data_parameters = self.build_data_parameters(
                "2d", x_edges, y_edges, keep=keep, min_counts=min_counts,
                reduction=reduction,
            )
        else:
            try:
                centers, counts, edges = self.marginal_for_fit(target)
            except Exception as exc:
                raise CurveFitError(f"no {target} histogram displayed ({exc})") from exc
            if parametric:
                cf = build_function_fit(curve.function, params, centers, counts)
            else:
                cf = build_marginal_fit(
                    equation, centers, counts,
                    initial=initial, constant_names=constant_names,
                )
            data_parameters = self.build_data_parameters(target, edges)
        # The constants are offered fixed; freeing one makes the fit re-derive
        # the data at every step (see DataParameters).
        cf.attach_data_parameters(data_parameters)
        if not parametric:
            # The curve's own table has the last word on fix/free and bounds.
            # (A parametric curve's parameters *are* that table, so there is
            # nothing to seed -- and nothing of the user's to overwrite.)
            cf.seed_from_group(getattr(curve, "parameter_group", None))
            for p in cf.parameters:
                if p.name in const_values:
                    p.fixed = True
        return cf

    def _build_cloud_fit(self, curve, x_edges, y_edges, params=None, counts=None):
        """A fit of ``curve`` against every occupied bin of the distribution.

        An equation curve is *traced* for this — evaluated on a dense grid over
        the displayed x range — so that both kinds of curve are compared with
        the cloud the same way: by distance, in displayed bins.
        """
        from ..analysis.curve_fit import (
            RESOLUTION_PARAMETERS,
            CurveFitError,
            ParametricCurveFit,
        )

        group = getattr(curve, "parameter_group", None)
        if group is None:
            raise CurveFitError("fitting the cloud needs the chisurf parameter table")
        parameters = list(params) if params is not None else list(group.parameters_all)
        px, py, weights = self.cloud_for_fit(x_edges, y_edges, counts=counts)
        if float(np.count_nonzero(weights)) < 3:
            raise CurveFitError("too little displayed data to fit")

        x_edges = np.asarray(x_edges, dtype=float)
        y_edges = np.asarray(y_edges, dtype=float)
        x_bin = float(np.median(np.diff(x_edges)))
        y_bin = float(np.median(np.diff(y_edges)))

        function = curve.function if getattr(curve, "is_function", False) else None
        if function is None:
            equation = curve.get_equation()
            evaluator = curve.curve_evaluator
            grid = np.linspace(x_edges[0], x_edges[-1], 400)

            def function(**values):
                y = evaluator.evaluate(equation, grid, values)
                if isinstance(y, tuple):
                    return y
                return grid, np.asarray(y, dtype=float)

        for p in parameters:
            if p.name in RESOLUTION_PARAMETERS:
                p.fixed = True
        return ParametricCurveFit(
            function, parameters, px, py,
            ey=np.full(py.shape, y_bin), ex=x_bin, weights=weights,
        )

    def on_fit_curve_to_data(self, curve):
        """Fit an overlay curve's parameters to the data that is displayed.

        Reuses ChiSurf's least-squares engine (via a ``ParseModel`` built from
        the curve's equation). The dialog chooses what to fit against — the
        displayed 2-D distribution or a marginal histogram — and the fitted
        parameters are written back into the curve (so the overlay redraws as
        the fitted curve) and into any matching entry of the constants table.
        """
        from ..analysis.curve_fit import CurveFitError

        def _write_back(result):
            if not result.ok:
                return
            # Write into the curve's own parameters, leaving linked ones to
            # their master, then redraw and push through to the constants.
            group = getattr(curve, "parameter_group", None)
            if group is not None:
                cf = dlg.current_fit if dlg is not None else None
                if cf is not None:
                    cf.write_back(group)
                curve.refresh_parameter_display()
                curve._update_filled_equation()
            else:
                curve.set_parameters(result.params)
            self.update_curve_overlays()
            self._apply_fitted_params_to_constants(result.params)
            if result.data_params:
                # A constant was fitted: the data itself moved, so the whole
                # plot -- not just the overlay -- is out of date.
                self._after_constants_fitted(result.data_params)
            logging.info(
                "Curve fit: chi2r=%.4g, params=%s%s",
                result.chi2r,
                result.params,
                f", constants={result.data_params}" if result.data_params else "",
            )

        dlg = None
        try:
            from ..ui.curve_fit_dialog import HAS_FIT_TABLE, CurveFitDialog
        except Exception:
            HAS_FIT_TABLE = False

        if HAS_FIT_TABLE:
            dlg = CurveFitDialog(
                self,
                build_fit=lambda target, reduction="cloud": (
                    self.build_curve_fit_for(curve, target, reduction)
                ),
                on_applied=_write_back,
            )
            dlg.exec_()
            # The dialog's tables held these parameters' controllers; the
            # curve's own table and the constants table take them back now that
            # it is gone.
            curve.refresh_parameter_display()
            try:
                self.parameter_control.claim_table_controllers()
            except AttributeError:
                pass
            return

        # No fitting table (ChiSurf absent): direct one-shot fit of the 2-D data.
        try:
            cf = self.build_curve_fit_for(curve, "2d")
        except CurveFitError as exc:
            logging.warning("Curve fit: %s", exc)
            return
        res = cf.run()
        if not res.ok:
            logging.warning("Curve fit failed: %s", res.message)
            return
        curve.set_parameters(res.params)
        self.update_curve_overlays()
        self._apply_fitted_params_to_constants(res.params)

    def _after_constants_fitted(self, changed) -> None:
        """Show the world a fit moved a constant.

        The fit recomputed **only the plotted columns** at every step, so every
        other column the constant feeds is still on its pre-fit value: the
        full recompute happens once, here. Then the constants table is
        repainted, the new values become the throttle's baseline (or the next
        parameter event diffs against the pre-fit ones and recomputes for
        nothing), and the plots — including the histograms, which is what the
        moved population actually changes — are rebuilt.
        """
        try:
            self.recompute_for_constants(changed)  # every dependent column now
        except Exception as exc:
            logging.warning("Full recompute after a fitted constant failed: %s", exc)
        pc = getattr(self, "parameter_control", None)
        if pc is not None:
            try:
                pc.claim_table_controllers()
            except AttributeError:
                pass
        try:
            self._prev_constants = dict(self.parameter_control.dict)
        except Exception:
            pass
        # Nothing may be left pending that would recompute over this again.
        self._pending_changed_constants = set()
        # The fit changed the numbers in the plotted columns without touching
        # the axis choice, the gate or the bins -- every key the value cache is
        # keyed on -- so without this the plots would redraw the population the
        # fit started from. (The histograms need no such nudge: they are refilled
        # from the store on every redraw.)
        self.invalidate_values_cache()
        self.update_plots()   # redraws the overlays with the moved population

    def _apply_fitted_params_to_constants(self, params: "dict") -> None:
        """Push any fitted *curve* parameter that names an ndX constant into the table.

        The constant it lands on may be one the equations read, in which case
        the derived columns no longer match the constants they were computed
        from — recompute them and redraw, exactly as if the constant had been
        fitted directly.
        """
        pc = getattr(self, "parameter_control", None)
        group = getattr(pc, "parameter_group", None)
        if group is None:
            return
        try:
            pdict = group.parameters_all_dict
        except Exception:
            return
        shaping = {p.name for p in self._constants_shaping_data()}
        changed = set()
        for name, value in params.items():
            p = pdict.get(name)
            if p is not None:
                p.value = float(value)
                if isinstance(self.constants, dict):
                    self.constants[name] = float(value)
                changed.add(name)
        if not changed:
            return
        moved_data = changed & shaping
        if moved_data:
            self._after_constants_fitted(moved_data)  # recomputes and redraws
        else:
            try:
                pc.claim_table_controllers()
            except AttributeError:
                pass

    def update_curve_overlays(self):
        """Update the curve overlays on the 2D histogram."""
        logging.debug("update_curve_overlays()")
        try:
            # Initialize histogram metadata cache
            self._histogram_metadata = {}

            # Get the 2D histogram data and edges (handle both old tuple and new clean formats)
            hist_2d = self._histogram.get("2d")
            if hist_2d is None:
                logging.debug("No 2D histogram available yet for curve overlays")
                return
            if hasattr(hist_2d, 'H'):
                # New clean Histogram2D object
                H = hist_2d.H
                x_edges = hist_2d.x_edges
                y_edges = hist_2d.y_edges
            elif isinstance(hist_2d, tuple) and len(hist_2d) == 3:
                # Old tuple format (H, x_edges, y_edges)
                H, x_edges, y_edges = hist_2d
            else:
                logging.error("Invalid 2D histogram format in curve overlays")
                return
                
            histogram_data = (H, x_edges, y_edges)
            
            # Check if histogram data is valid
            if H is None or H.size == 0:
                logging.debug("Empty histogram data, skipping curve overlay update")
                return
                
            # Call the update_curve_overlays method in the CurveOverlayWidget class
            self.curve_overlay_widget.update_curve_overlays(
                overlay_plot=self.overlay_plot,
                histogram_data=histogram_data,
                plot_control=self.plot_control,
                curve_evaluator=self.curve_evaluator,
                value_to_bin_func=self.value_to_bin
            )

        except (ValueError, KeyError, IndexError, AttributeError) as e:
            logging.warning(f"Error updating curve overlays: {str(e)}")
            return

    # ========================= GAUSSIAN FITTING ==============================
    def on_fit_2d_gaussian(self):
        """Delegate to GaussianFit."""
        if hasattr(self, 'gaussian_fit') and self.gaussian_fit is not None:
            return self.gaussian_fit.on_fit_2d_gaussian()

    def on_select_point_toggled(self, checked: bool):
        """Delegate to GaussianFit."""
        if hasattr(self, 'gaussian_fit') and self.gaussian_fit is not None:
            return self.gaussian_fit.on_select_point_toggled(checked)

    def _on_point_selected(self, pos):
        """Delegate to GaussianFit."""
        if hasattr(self, 'gaussian_fit') and self.gaussian_fit is not None:
            return self.gaussian_fit.on_point_selected(pos)

    def on_clear_gaussians(self):
        """Delegate to GaussianFit."""
        if hasattr(self, 'gaussian_fit') and self.gaussian_fit is not None:
            return self.gaussian_fit.on_clear_gaussians()

    def _compute_moments(self, H: np.ndarray, x_edges: np.ndarray, y_edges: np.ndarray):
        """Delegate to GaussianFit."""
        if hasattr(self, 'gaussian_fit') and self.gaussian_fit is not None:
            return self.gaussian_fit._compute_moments(H, x_edges, y_edges)
        return None, None

    def _compute_local_moments(self, H: np.ndarray, x_edges: np.ndarray, y_edges: np.ndarray, ix: int, iy: int, window: int = 5):
        """Delegate to GaussianFit."""
        if hasattr(self, 'gaussian_fit') and self.gaussian_fit is not None:
            return self.gaussian_fit._compute_local_moments(H, x_edges, y_edges, ix, iy, window)
        return None, None

    def _add_gaussian_overlay(self, mu: Tuple[float, float], cov: np.ndarray, label: str = "", color: Optional[str] = None):
        """Delegate to GaussianFit."""
        if hasattr(self, 'gaussian_fit') and self.gaussian_fit is not None:
            return self.gaussian_fit._add_gaussian_overlay(mu, cov, label, color)
        return None

    def _append_gaussian_row(self, mu: Tuple[float, float], cov: np.ndarray, w: float = 1.0):
        """Delegate to GaussianFit."""
        if hasattr(self, 'gaussian_fit') and self.gaussian_fit is not None:
            return self.gaussian_fit._append_gaussian_row(mu, cov, w)
        return -1

    def _update_gaussian_row(self, row: int, mu: np.ndarray, cov: np.ndarray, w: float = None):
        """Delegate to GaussianFit."""
        if hasattr(self, 'gaussian_fit') and self.gaussian_fit is not None:
            return self.gaussian_fit._update_gaussian_row(row, mu, cov, w)
        return None

    def _read_gaussian_table(self) -> List[Tuple[np.ndarray, np.ndarray, float]]:
        """Delegate to GaussianFit."""
        if hasattr(self, 'gaussian_fit') and self.gaussian_fit is not None:
            return self.gaussian_fit._read_gaussian_table()
        return []

    def _redraw_gaussian_overlays_from_table(self):
        """Delegate to GaussianFit."""
        if hasattr(self, 'gaussian_fit') and self.gaussian_fit is not None:
            return self.gaussian_fit._redraw_gaussian_overlays_from_table()

    def _clear_gaussian_marginal_items(self):
        """Delegate to GaussianFit."""
        if hasattr(self, 'gaussian_fit') and self.gaussian_fit is not None:
            return self.gaussian_fit._clear_gaussian_marginal_items()

    def _draw_gaussian_marginals_from_table(self, rows, colors=None):
        """Delegate to GaussianFit."""
        if hasattr(self, 'gaussian_fit') and self.gaussian_fit is not None:
            return self.gaussian_fit._draw_gaussian_marginals_from_table(rows, colors)

    def on_toggle_gaussian_marginals(self, checked: bool):
        """Delegate to GaussianFit."""
        if hasattr(self, 'gaussian_fit') and self.gaussian_fit is not None:
            return self.gaussian_fit.on_toggle_gaussian_marginals(checked)

    # ======================= END GAUSSIAN FITTING ===========================

    def check_and_set_image_axes(self) -> bool:
        """Delegate image-axis detection to axis_helpers."""
        return axis_helpers.check_and_set_image_axes(self)

    def apply_default_axes_from_settings(self):
        """
        Apply default axis selections from settings via axis_helpers.
        This is used after a dataset is loaded to preselect X/Y/Z/weight axes.
        It will not override image axes (the caller should check first).
        """
        return axis_helpers.apply_default_axes_from_settings(self)

    def on_gaussian_table_item_changed(self, item: QtWidgets.QTableWidgetItem):
        """Delegate to GaussianFit."""
        logging.debug(f"on_gaussian_table_item_changed(item={item})")
        if hasattr(self, 'gaussian_fit') and self.gaussian_fit is not None:
            return self.gaussian_fit.on_gaussian_table_item_changed(item)

    def eventFilter(self, obj, event):
        """
        Delegate table/overlay events to GaussianFit; do not trigger 2D updates
        from canvas-resize here to avoid race conditions with resizeEvent().
        """
        logging.debug(f"eventFilter(obj={obj}, event={event})")
        handled_by_gaussian = False
        if hasattr(self, 'gaussian_fit') and self.gaussian_fit is not None:
            try:
                handled_by_gaussian = bool(self.gaussian_fit.eventFilter(obj, event))
            except Exception:
                handled_by_gaussian = False

        if handled_by_gaussian:
            return True
        return super(NDXplorer, self).eventFilter(obj, event)

    def _delete_selected_gaussian_rows(self, rows: List[int]):
        """Delegate to GaussianFit."""
        logging.debug(f"_delete_selected_gaussian_rows(rows={rows})")
        if hasattr(self, 'gaussian_fit') and self.gaussian_fit is not None:
            return self.gaussian_fit._delete_selected_gaussian_rows(rows)

    def _set_fit_panel_visible(self, visible: bool):
        """Show or hide the Gaussian-Fit panel's dock tab.

        Parameters
        ----------
        visible : bool
            Whether the panel should be on screen.
        """
        logging.debug(f"_set_fit_panel_visible(visible={visible})")
        panel = getattr(self, "dockWidget_Fit", None)
        area = getattr(self, "dock_area", None)
        if panel is not None and area is not None:
            index = area.indexOf(panel)
            if index >= 0:
                area.showTab(index) if visible else area.hideTab(index)
                if visible:
                    area.setCurrentWidget(panel)
        elif panel is not None:  # pragma: no cover - no dock area available
            panel.setVisible(visible)
        return self._on_fit_dock_visibility_changed(visible)

    def _on_fit_dock_visibility_changed(self, visible: bool):
        """Delegate to GaussianFit."""
        logging.debug(f"_on_fit_dock_visibility_changed(visible={visible})")
        return self.gaussian_fit.on_fit_dock_visibility_changed(visible)

    def _on_dock_tab_changed(self, _index: int) -> None:
        """Keep point-selection mode in step with the ACTIVATED tab.

        The Gaussian Fit panel is a dock-area tab, and switching tabs emits no
        visibility signal of its own -- only the menu action used to arm point
        mode. Armed exactly while the Fit tab is the dock area's current one:
        merely being on screen beside the plot is not being worked in, and a
        click on the histogram then still means a selection.
        """
        panel = getattr(self, "dockWidget_Fit", None)
        area = getattr(self, "dock_area", None)
        if panel is None or area is None or getattr(self, "gaussian_fit", None) is None:
            return
        try:
            active = area.currentWidget() is panel
        except Exception:
            active = bool(panel.isVisible())
        self._on_fit_dock_visibility_changed(active)

    def resizeEvent(self, event):
        """
        Rescale/redraw the 2D plot on window resize.

        Resize must NOT recompute the histograms (BUGS #14): re-binning/re-counting
        on every resize event caused heavy CPU load and laggy interaction. The
        histogram data is computed once and cached in ``self._histogram``; on
        resize we only redraw that cached data (``update_2d_plot``), which fixes
        orientation issues without any recomputation. A zero-timeout singleShot
        runs the redraw after layout has applied the new sizes.
        """
        logging.debug("resizeEvent()")
        # First perform the default resize handling
        super(NDXplorer, self).resizeEvent(event)

        # Debounce: coalesce bursts of resize events into a single redraw.
        if getattr(self, "_resize_redraw_pending", False):
            return
        self._resize_redraw_pending = True

        def _do_redraw():
            self._resize_redraw_pending = False
            try:
                # Redraw the cached histogram only — no recompute.
                self.update_2d_plot()
            except Exception:
                logging.debug("resize redraw via update_2d_plot failed", exc_info=True)

        QtCore.QTimer.singleShot(0, _do_redraw)
