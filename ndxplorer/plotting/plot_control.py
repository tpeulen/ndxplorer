from __future__ import print_function
from typing import Dict
import json
import pathlib
import math

from qtpy import QtGui, uic, QtCore, QtWidgets

try:
    from pyqtgraph.widgets.SpinBox import SpinBox
    PYQTGRAPH_AVAILABLE = True
except ImportError:
    PYQTGRAPH_AVAILABLE = False
    SpinBox = None

from ..logging_config import logging
from ..widgets.mask_drawing_widget import MaskDrawingWidget
from .controls import ScaleControlMixin, AxisControlMixin, HistogramControlMixin


class SurfacePlotWidget(ScaleControlMixin, AxisControlMixin, HistogramControlMixin, QtWidgets.QWidget):
    """
    Surface plot control widget with modular control mixins.
    
    Architecture:
    - ScaleControlMixin: Log/linear scale controls
    - AxisControlMixin: X/Y/Z/Weight parameter selection
    - HistogramControlMixin: Bins and normalization settings
    """

    axis_settings = dict()  # type: Dict[str, Dict[str, float]]

    @property
    def p2(self):
        return self._axis_selection(self.comboBoxSelY)
        
    @p2.setter
    def p2(self, value, block_signals=False):
        """
        Set the Y axis parameter.
        
        Args:
            value: Either an index (int) or parameter name (str) or tuple (idx, name)
            block_signals: If True, signals will be blocked during the change
        """
        self._set_combobox_from_tuple_or_value(self.comboBoxSelY, value, block_signals)

    @property
    def p3(self):
        return self._axis_selection(self.comboBoxSelZ)
        
    @property
    def x_label(self):
        """
        Get the X axis label.
        
        Returns:
            str: The name of the parameter selected for the X axis
        """
        return str(self.comboBoxSelX.currentText())
        
    @property
    def y_label(self):
        """
        Get the Y axis label.
        
        Returns:
            str: The name of the parameter selected for the Y axis
        """
        return str(self.comboBoxSelY.currentText())
        
    @property
    def z_label(self):
        """
        Get the Z axis label.
        
        Returns:
            str: The name of the parameter selected for the Z axis
        """
        return str(self.comboBoxSelZ.currentText())
        
    @p3.setter
    def p3(self, value, block_signals=False):
        """
        Set the Z axis parameter.
        
        Args:
            value: Either an index (int) or parameter name (str) or tuple (idx, name)
            block_signals: If True, signals will be blocked during the change
        """
        self._set_combobox_from_tuple_or_value(self.comboBoxSelZ, value, block_signals)
    
    # Note: set_axis_by_name is now provided by AxisControlMixin

    @property
    def binsX(self):
        return int(self.spinBoxBin1DX.value())

    @property
    def binsY(self):
        return int(self.spinBoxBin1DY.value())

    @property
    def binsZ(self):
        return int(self.spinBoxBin1DZ.value())

    @property
    def bins2X(self):
        return int(self.spinBoxBin2DX.value())

    @property
    def bins2Y(self):
        return int(self.spinBoxBin2DY.value())

    @property
    def n_xhist_1d(self):
        return int(self.spinBoxBin1DX.value())

    @n_xhist_1d.setter
    def n_xhist_1d(self, v):
        self.spinBoxBin1DX.setValue(int(v))

    @property
    def n_yhist_1d(self):
        return int(self.spinBoxBin1DY.value())

    @n_yhist_1d.setter
    def n_yhist_1d(self, v):
        self.spinBoxBin1DY.setValue(int(v))

    @property
    def n_zhist_1d(self):
        return int(self.spinBoxBin1DZ.value())

    @n_zhist_1d.setter
    def n_zhist_1d(self, v):
        self.spinBoxBin1DZ.setValue(int(v))

    @property
    def n_xhist_2d(self):
        return int(self.spinBoxBin2DX.value())

    @n_xhist_2d.setter
    def n_xhist_2d(self, v):
        self.spinBoxBin2DX.setValue(int(v))

    @property
    def n_yhist_2d(self):
        return int(self.spinBoxBin2DY.value())

    @n_yhist_2d.setter
    def n_yhist_2d(self, v):
        self.spinBoxBin2DY.setValue(int(v))

    @property
    def selected_cluster(self):
        """
        Returns the currently selected cluster from spinBoxCluster.
        A value of -1 means all clusters should be displayed.
        """
        return int(self.spinBoxCluster.value())

    @property
    def x_range(self):
        return float(self.spinBoxXmin.value()), \
               float(self.spinBoxXmax.value())

    @property
    def xmin(self):
        return self.x_range[0]

    @xmin.setter
    def xmin(self, v):
        self.spinBoxXmin.setValue(v)

    @property
    def xmax(self):
        return self.x_range[1]

    @xmax.setter
    def xmax(self, v):
        self.spinBoxXmax.setValue(v)

    @property
    def y_range(self):
        return float(self.spinBoxYmin.value()), \
               float(self.spinBoxYmax.value())

    @property
    def ymin(self):
        return float(self.spinBoxYmin.value())

    @ymin.setter
    def ymin(self, v):
        self.spinBoxYmin.setValue(v)

    @property
    def ymax(self):
        return float(self.spinBoxYmax.value())

    @ymax.setter
    def ymax(self, v):
        self.spinBoxYmax.setValue(v)

    @property
    def z_range(self):
        return float(self.spinBoxZmin.value()), \
               float(self.spinBoxZmax.value())

    @property
    def zmin(self):
        return float(self.spinBoxZmin.value())

    @zmin.setter
    def zmin(self, v):
        self.spinBoxZmin.setValue(v)

    @property
    def zmax(self):
        return float(self.spinBoxZmax.value())

    @zmax.setter
    def zmax(self, v):
        self.spinBoxZmax.setValue(v)

    def __init__(self, parent=None):
        super(SurfacePlotWidget, self).__init__()
        self.parent = parent
        from ..core.gates import GateList

        #: The Selection table's rows; the widget is a view of them.
        self.gates = GateList()
        self.axis_settings = dict()  # Instance-level axis settings
        logging.log(0, "Initializing SurfacePlotWidget")
        #########################
        # GUI
        #########################
        ui_file = pathlib.Path(__file__).parent / 'plot_control.ui'

        uic.loadUi(str(ui_file.as_posix()), self)

        self.actionUpdate_x_axis_settings.setText("Set X")
        self.actionAuto_range_x.setText("Auto X")
        self.actionUpdate_y_axis_settings.setText("Set Y")
        self.actionAuto_range_y.setText("Auto Y")
        self.actionUpdate_z_axis_settings.setText("Set Z")
        self.actionAuto_range_z.setText("Auto Z")

        # Keep the per-axis Set/Auto buttons next to their corresponding axis
        # controls (they are wired in the .ui to the same axis actions). They were
        # previously hidden in favour of a single consolidated "Axis" toolbar row;
        # restoring them here puts the controls back beside each axis as before.
        for widget_name in (
            "toolButtonSetXAxis",
            "toolButtonAutoX",
            "toolButtonSetYAxis",
            "toolButtonAutoY",
            "toolButtonSetZAxis",
            "toolButtonAutoZ",
        ):
            widget = getattr(self, widget_name, None)
            if widget is not None:
                widget.setVisible(True)

        # Expose the clustering button on the parent (NDXplorer) for legacy wiring.
        clustering_btn = getattr(self, "pushButtonShowClusteringDialog", None)
        if clustering_btn is not None and self.parent is not None:
            self.parent.pushButtonShowClusteringDialog = clustering_btn
        
        # Handle pyqtgraph SpinBox replacement if available
        if PYQTGRAPH_AVAILABLE and SpinBox is not None:
            # Replace QSpinBox widgets with pyqtgraph SpinBox for better functionality
            logging.log(0, "Replacing QSpinBox with pyqtgraph SpinBox widgets")
            
            # Get the current layout positions and widget properties
            x_min_widget = self.spinBoxXmin
            x_max_widget = self.spinBoxXmax
            y_min_widget = self.spinBoxYmin
            y_max_widget = self.spinBoxYmax
            z_min_widget = self.spinBoxZmin
            z_max_widget = self.spinBoxZmax
            
            # Create pyqtgraph SpinBox widgets
            self.spinBoxXmin = SpinBox()
            self.spinBoxXmax = SpinBox()
            self.spinBoxYmin = SpinBox()
            self.spinBoxYmax = SpinBox()
            self.spinBoxZmin = SpinBox()
            self.spinBoxZmax = SpinBox()
            
            # Copy properties from original widgets
            for new_widget, old_widget in [
                (self.spinBoxXmin, x_min_widget),
                (self.spinBoxXmax, x_max_widget),
                (self.spinBoxYmin, y_min_widget),
                (self.spinBoxYmax, y_max_widget),
                (self.spinBoxZmin, z_min_widget),
                (self.spinBoxZmax, z_max_widget)
            ]:
                # Copy size policy
                new_widget.setSizePolicy(old_widget.sizePolicy())
                # Copy tooltip
                new_widget.setToolTip(old_widget.toolTip())
                # Set reasonable range
                new_widget.setRange(-1000000, 1000000)
            
            # Get the grid layout and replace widgets in their positions
            grid_layout = self.gridLayout_6  # This is the main histogram grid layout
            
            # Replace widgets in the grid layout
            # X axis widgets are at row 6
            grid_layout.replaceWidget(x_min_widget, self.spinBoxXmin)
            grid_layout.replaceWidget(x_max_widget, self.spinBoxXmax)
            # Y axis widgets are at row 8
            grid_layout.replaceWidget(y_min_widget, self.spinBoxYmin)
            grid_layout.replaceWidget(y_max_widget, self.spinBoxYmax)
            # Z axis widgets are in a different grid (gridLayout_2)
            z_grid_layout = self.gridLayout_2
            z_grid_layout.replaceWidget(z_min_widget, self.spinBoxZmin)
            z_grid_layout.replaceWidget(z_max_widget, self.spinBoxZmax)
            
            # Reparented out FIRST, then deleted. ``replaceWidget`` takes the
            # old widget out of the layout but leaves it a child of the panel,
            # and a child that no layout positions draws at (0, 0) -- so all
            # four of these sat stacked in the top-left corner, over the x-axis
            # row, as one spin box reading 0 that belonged to nothing.
            # ``deleteLater`` alone does not clear that: the deferred-delete
            # event is only processed when the event loop unwinds past the level
            # the widget was created at, which never happens for a panel built
            # headlessly, and had not happened yet whenever the panel was
            # painted early.
            for old_widget in (x_min_widget, x_max_widget,
                               y_min_widget, y_max_widget,
                               z_min_widget, z_max_widget):
                old_widget.setParent(None)
                old_widget.deleteLater()
        else:
            # Use QSpinBox widgets from UI file
            logging.log(0, "Using QSpinBox widgets from UI file")
        
        # Initialize mask drawing widget - use UI elements directly
        self.mask_widget = MaskDrawingWidget(self)
        # Store reference to NDXplorer parent for easy access
        self.mask_widget._ndxplorer_parent = self.parent
        
        # Connect UI elements from the .ui file to the mask widget
        self.categorySpinBox.valueChanged.connect(self.mask_widget._on_category_changed)
        self.brushSpinBox.valueChanged.connect(self.mask_widget._on_brush_size_changed)
        self.drawRadio.toggled.connect(self.mask_widget._on_mode_changed)
        self.loadMaskBtn.clicked.connect(self.mask_widget.load_mask)
        self.saveMaskBtn.clicked.connect(self.mask_widget.save_mask)
        self.clearMaskBtn.clicked.connect(self.mask_widget.clear_mask)
        self.applyMaskBtn.clicked.connect(self.mask_widget._on_apply_mask)
        self.checkBoxEnableDrawing.toggled.connect(self.mask_widget._on_drawing_enabled_changed)
        
        # Set up references to UI elements for the mask widget
        self.mask_widget.category_spinbox = self.categorySpinBox
        self.mask_widget.brush_spinbox = self.brushSpinBox
        self.mask_widget.draw_radio = self.drawRadio
        self.mask_widget.erase_radio = self.eraseRadio
        self.mask_widget.load_mask_btn = self.loadMaskBtn
        self.mask_widget.save_mask_btn = self.saveMaskBtn
        self.mask_widget.clear_mask_btn = self.clearMaskBtn
        self.mask_widget.apply_mask_btn = self.applyMaskBtn
        self.mask_widget.enable_drawing_checkbox = self.checkBoxEnableDrawing
        # maskStatsLabel has been removed from UI - set to None
        self.mask_widget.stats_label = None
        
        # Initialize spinbox values to prevent empty fields
        if PYQTGRAPH_AVAILABLE and SpinBox is not None:
            # For pyqtgraph SpinBox, set default values
            self.spinBoxXmin.setValue(0.0)
            self.spinBoxXmax.setValue(1.0)
            self.spinBoxYmin.setValue(0.0)
            self.spinBoxYmax.setValue(1.0)
            self.spinBoxZmin.setValue(0.0)
            self.spinBoxZmax.setValue(1.0)
        else:
            # For QSpinBox fallback, set default values
            # The UI file already has these values, but we set them again for consistency
            self.spinBoxXmin.setValue(0)
            self.spinBoxXmax.setValue(100)
            self.spinBoxYmin.setValue(0)
            self.spinBoxYmax.setValue(100)
            self.spinBoxZmin.setValue(0)
            self.spinBoxZmax.setValue(100)

        # Allow inline editing of selection numeric bounds in the table with single-click
        # Keep double-click deletion as defined in the .ui (cellDoubleClicked -> actionSelectionTableClicked)
        # React to edits in the selection table
        try:
            self.tableWidget.itemChanged.disconnect()
        except Exception:
            pass
        self.tableWidget.itemChanged.connect(self.onSelectionItemChanged)
        # Guard flag to prevent recursive updates during programmatic edits
        self._block_selection_item_changed = False

        # Use our own single-click edit behavior and preserve double-click for delete
        self.tableWidget.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self._single_click_edit_timer = QtCore.QTimer(self)
        self._single_click_edit_timer.setSingleShot(True)
        self._single_click_edit_timer.timeout.connect(self._perform_pending_single_click_edit)
        self._pending_edit_index = None
        self.tableWidget.cellClicked.connect(self.onSelectionCellClicked)
        self.tableWidget.cellDoubleClicked.connect(self.onSelectionCellDoubleClicked)

        # Delete key removes selected selection rows
        try:
            shortcut_delete = QtWidgets.QShortcut(QtGui.QKeySequence(QtCore.Qt.Key_Delete), self.tableWidget)
            shortcut_delete.activated.connect(self.onDeleteSelectionRows)
        except Exception:
            pass

        # Set up context menu for selection table
        self.tableWidget.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.tableWidget.customContextMenuRequested.connect(self.onSelectionTableContextMenu)

        # Auto complete for selectors
        self.comboBoxSelX.completer().setCompletionMode(QtWidgets.QCompleter.PopupCompletion)
        self.comboBoxSelX.setInsertPolicy(QtWidgets.QComboBox.NoInsert)
        self.comboBoxSelY.completer().setCompletionMode(QtWidgets.QCompleter.PopupCompletion)
        self.comboBoxSelY.setInsertPolicy(QtWidgets.QComboBox.NoInsert)
        self.comboBoxSelZ.completer().setCompletionMode(QtWidgets.QCompleter.PopupCompletion)
        self.comboBoxSelZ.setInsertPolicy(QtWidgets.QComboBox.NoInsert)
        #########################
        # Actions
        #########################
        # Generic action
        self.actionUpdatePlots.triggered.connect(self._on_normalize_changed)

        # Auto range
        self.actionAuto_range_x.triggered.connect(self.on_auto_range_x)
        self.actionAuto_range_x.triggered.connect(self.update_axis_scales)
        self.actionAuto_range_y.triggered.connect(self.on_auto_range_y)
        self.actionAuto_range_y.triggered.connect(self.update_axis_scales)
        self.actionAuto_range_z.triggered.connect(self.on_auto_range_z)
        self.actionAuto_range_z.triggered.connect(self.update_axis_scales)
        self.actionAuto_range_z.triggered.connect(self.auto_selection_range)
        self.actionUpdate_axis_scales.triggered.connect(self.update_axis_scales)
        self.actionAuto_range_x.triggered.connect(self.update_axis_scales)

        # Selection table
        self.actionSelectionTableClicked.triggered.connect(self.onSelectionTableClicked)
        self.actionSave_selection.triggered.connect(self.onSave_selection)
        self.actionLoad_selection.triggered.connect(self.onLoad_selection)
        self.actionClear_Selection.triggered.connect(self.onClearSelection)
        self.actionAdd_Selection.triggered.connect(self.onAddSelection)
        if self.parent is not None and hasattr(self.parent, "onSaveBurstIDs"):
            self.actionSave_Burst_IDs.triggered.connect(self.parent.onSaveBurstIDs)
        
        # Connect toolButtonClearSelection to clear selection action
        if hasattr(self, 'toolButtonClearSelection'):
            self.toolButtonClearSelection.clicked.connect(self.onClearSelection)

        # Change axis range
        if PYQTGRAPH_AVAILABLE and SpinBox is not None:
            # pyqtgraph SpinBox signals
            self.spinBoxXmin.sigValueChanged.connect(self.actionUpdate_axis_scales.trigger)
            self.spinBoxXmax.sigValueChanged.connect(self.actionUpdate_axis_scales.trigger)
            self.spinBoxYmin.sigValueChanged.connect(self.actionUpdate_axis_scales.trigger)
            self.spinBoxYmax.sigValueChanged.connect(self.actionUpdate_axis_scales.trigger)
            self.spinBoxZmin.sigValueChanged.connect(self.actionUpdate_axis_scales.trigger)
            self.spinBoxZmax.sigValueChanged.connect(self.actionUpdate_axis_scales.trigger)
        else:
            # QSpinBox signals
            self.spinBoxXmin.valueChanged.connect(self.actionUpdate_axis_scales.trigger)
            self.spinBoxXmax.valueChanged.connect(self.actionUpdate_axis_scales.trigger)
            self.spinBoxYmin.valueChanged.connect(self.actionUpdate_axis_scales.trigger)
            self.spinBoxYmax.valueChanged.connect(self.actionUpdate_axis_scales.trigger)
            self.spinBoxZmin.valueChanged.connect(self.actionUpdate_axis_scales.trigger)
            self.spinBoxZmax.valueChanged.connect(self.actionUpdate_axis_scales.trigger)

        # Change parameter plotted on axis
        self.actionX_axis_changed.triggered.connect(self.on_x_axis_changed)
        self.actionY_axis_changed.triggered.connect(self.on_y_axis_changed)
        self.actionZ_axis_changed.triggered.connect(self.on_z_axis_changed)

        # Update axis settings
        self.actionUpdate_x_axis_settings.triggered.connect(self.update_x_axis_settings)
        self.actionUpdate_y_axis_settings.triggered.connect(self.update_y_axis_settings)
        self.actionUpdate_z_axis_settings.triggered.connect(self.update_z_axis_settings)

        # Connect spinBoxCluster to update plots when value changes
        self.spinBoxCluster.valueChanged.connect(self.onClusterSelectionChanged)

        # "Colour by cluster": draw every cluster at once in its own colour,
        # rather than isolating one at a time with the spinner beside it. The
        # two answer different questions -- where the populations sit relative
        # to one another, versus what one of them looks like alone -- so both
        # stay available. Added in code rather than the .ui so the layout the
        # spinner already lives in is reused.
        self.checkBoxColorClusters = QtWidgets.QCheckBox("colour", self)
        self.checkBoxColorClusters.setToolTip(
            "Colour the 2-D map by cluster instead of by density.\n"
            "Each bin takes the colour of the cluster contributing most points, "
            "with brightness still carrying the count."
        )
        self.checkBoxColorClusters.setChecked(False)
        try:
            # Find the layout that actually holds the spinner. Taking the parent
            # widget's top-level layout is not enough: the spinner sits in a
            # nested grid, so indexOf() on the outer layout returns -1 and the
            # checkbox lands in an unrelated corner of the panel.
            placed = False
            for layout in self.findChildren(QtWidgets.QGridLayout):
                index = layout.indexOf(self.spinBoxCluster)
                if index < 0:
                    continue
                row, column, _, _ = layout.getItemPosition(index)
                layout.addWidget(self.checkBoxColorClusters, row, column + 1)
                placed = True
                break
            if not placed:
                logging.debug("cluster colour toggle: spinner layout not found")
        except Exception:
            logging.debug("could not place the cluster colour toggle", exc_info=True)
        self.checkBoxColorClusters.toggled.connect(self.onClusterColorsToggled)
        
        # Connect bin count spinboxes to clear mask when bins change
        self.spinBoxBin2DX.valueChanged.connect(self.on_bin_count_changed)
        self.spinBoxBin2DY.valueChanged.connect(self.on_bin_count_changed)
        
        # Connect 1D bin count spinboxes as well
        self.spinBoxBin1DX.valueChanged.connect(self.on_bin_count_changed)
        self.spinBoxBin1DY.valueChanged.connect(self.on_bin_count_changed)
        self.spinBoxBin1DZ.valueChanged.connect(self.on_bin_count_changed)
        
        self._build_playback_panel()
        self._build_panels()

    def set_axis_settings(self, name, amin, amax, scale, bins_1d, bins_2d):
        self.axis_settings[str(name)] = {
            "n_bins_1d": float(bins_1d),
            "min": float(amin),
            "max": float(amax),
            "scale": str(scale)
        }
        if bins_2d is not None:
            self.axis_settings[str(name)].update(
                {
                    "n_bins_2d": int(bins_2d)
                }
            )
        logging.log(0, f"Axis settings updated for {name}: {self.axis_settings[str(name)]}")

    def update_axis_settings(self, axis):
        """
        Update settings for the specified axis.

        Args:
            axis (str): The axis to update ('x', 'y', or 'z')
        """
        axis = axis.lower()
        logging.log(0, f"update_axis_settings for {axis} axis")

        if axis == 'x':
            self.set_axis_settings(
                self.p1[1],
                self.xmin, self.xmax,
                self.scale_x,
                self.n_xhist_1d,
                self.n_xhist_2d
            )
        elif axis == 'y':
            self.set_axis_settings(
                self.p2[1],
                self.ymin, self.ymax,
                self.scale_y,
                self.n_yhist_1d,
                self.n_yhist_2d
            )
        elif axis == 'z':
            self.set_axis_settings(
                self.p3[1],
                self.zmin, self.zmax,
                self.scale_z,
                self.n_zhist_1d,
                None
            )
        else:
            logging.log(0, f"Invalid axis: {axis}")

    def update_x_axis_settings(self):
        """Update settings for the X axis"""
        self.update_axis_settings('x')

    # Keep the old method name for backward compatibility
    onUpdate_x_axis_settings = update_x_axis_settings

    def update_y_axis_settings(self):
        """Update settings for the Y axis"""
        self.update_axis_settings('y')

    # Keep the old method name for backward compatibility
    onUpdate_y_axis_settings = update_y_axis_settings

    def update_z_axis_settings(self):
        """Update settings for the Z axis"""
        self.update_axis_settings('z')

    # Keep the old method name for backward compatibility
    onUpdate_z_axis_settings = update_z_axis_settings

    def onClusterColorsToggled(self, checked: bool) -> None:
        """Redraw the 2-D map when the cluster-colour toggle changes.

        This is a *display* change: the histogram behind the image is identical
        either way. Going through the ordinary plot-update path would therefore
        do nothing, because that path skips the redraw when nothing it caches
        has changed -- the toggle would appear dead until something else forced
        a repaint. Repainting the image directly is both correct and cheaper
        than invalidating the histogram to provoke it.
        """
        logging.debug("Cluster colouring toggled: %s", checked)
        try:
            if self.parent._histogram.get("2d") is None:
                # Nothing to recolour yet — a run of clustering invalidates the
                # histogram, so the toggle can land while it is being recomputed.
                # The ordinary update path will draw it, and will pick up the
                # new setting when it does.
                self.parent.request_plot_update(skip_clustering=True)
            else:
                # A histogram exists and does not change with this setting, so
                # repaint the image directly. Going through the update path
                # would skip the redraw — nothing it caches has changed — and
                # the toggle would look dead.
                self.parent.update_2d_plot()
        except Exception:
            logging.debug("could not redraw the 2-D plot", exc_info=True)

    def onClusterSelectionChanged(self, value):
        """
        Handle changes to the cluster selection spinbox.

        Args:
            value: The new value of the spinbox
        """
        logging.log(0, f"Cluster selection changed to {value}")
        # Update plots with skip_clustering=True to avoid re-clustering the data
        self.parent.request_plot_update(skip_clustering=True)

    def on_axis_changed(self, axis):
        """
        Handle changes to any axis (X, Y, or Z).

        This method updates the histogram bins, range, and scale settings for the specified axis
        based on the currently selected parameter. If settings for the parameter exist in 
        axis_settings, those are used; otherwise, auto-range is applied.

        Args:
            axis (str): The axis to update ('x', 'y', or 'z')
        """
        axis = axis.lower()

        # Define mappings for each axis to its properties
        axis_properties = {
            'x': {
                'property': self.p1,
                'hist_1d': 'n_xhist_1d',
                'hist_2d': 'n_xhist_2d',
                'min': 'xmin',
                'max': 'xmax',
                'scale': 'scale_x',
                'auto_range': self.on_auto_range_x,
                'parent_min': 'xmin',
                'parent_max': 'xmax'
            },
            'y': {
                'property': self.p2,
                'hist_1d': 'n_yhist_1d',
                'hist_2d': 'n_yhist_2d',
                'min': 'ymin',
                'max': 'ymax',
                'scale': 'scale_y',
                'auto_range': self.on_auto_range_y,
                'parent_min': 'ymin',
                'parent_max': 'ymax'
            },
            'z': {
                'property': self.p3,
                'hist_1d': 'n_zhist_1d',
                'hist_2d': None,  # Z axis doesn't have 2D histogram bins
                'min': 'zmin',
                'max': 'zmax',
                'scale': 'scale_z',
                'auto_range': self.on_auto_range_z,
                'parent_min': 'zmin',
                'parent_max': 'zmax'
            }
        }

        # Check if the axis is valid
        if axis not in axis_properties:
            logging.log(0, f"Invalid axis: {axis}")
            return

        # Get the properties for this axis
        props = axis_properties[axis]
        _, name = props['property']

        from ..utils.axis_helpers import settings_for_axis

        setup = settings_for_axis(name, self.axis_settings, with_2d=props['hist_2d'] is not None)
        if setup is not None:
            setattr(self, props['hist_1d'], setup["bins_1d"])
            if props['hist_2d'] is not None:
                setattr(self, props['hist_2d'], setup["bins_2d"])
            lo, hi = setup["min"], setup["max"]
            setattr(self, props['min'], lo if lo is not None else getattr(self.parent, props['parent_min']))
            setattr(self, props['max'], hi if hi is not None else getattr(self.parent, props['parent_max']))
            setattr(self, props['scale'], setup["scale"])
            logging.log(0, f"{axis.upper()} axis changed to settings: {setup}")
        else:
            logging.log(0, f"{axis.upper()} axis settings for {name} not found. Using auto range.")
            props['auto_range']()

        # When X or Y axis changes, disable drawing mode and clear current drawing
        # but keep existing bitmap selections (they will be automatically updated)
        if axis in ['x', 'y']:
            logging.log(0, f"{axis.upper()} axis changed - disabling drawing mode and clearing current drawing")
            # Disable drawing mode and clear current drawing only
            if hasattr(self, 'mask_widget') and self.mask_widget is not None:
                self.mask_widget.set_drawing_enabled(False)
                self.mask_widget.clear_mask()
            
            # Note: Existing bitmap selections are kept - they will be automatically
            # updated when the histogram is recomputed with new axis/bin settings

        if axis == 'z':
            # The dynamic-z region is in axis units, so a new axis or a new
            # range leaves it pointing at values that no longer exist.
            fit = getattr(self.parent, "fit_z_selection_to_axis", None)
            if callable(fit):
                fit()

        self.parent.request_plot_update()

    def on_x_axis_changed(self):
        """Call the combined axis change method for X axis"""
        self.on_axis_changed('x')

    # Keep the old method name for backward compatibility
    onX_axis_changed = on_x_axis_changed

    def on_y_axis_changed(self):
        """Call the combined axis change method for Y axis"""
        self.on_axis_changed('y')

    # Keep the old method name for backward compatibility
    onY_axis_changed = on_y_axis_changed

    def on_z_axis_changed(self):
        """Call the combined axis change method for Z axis"""
        self.on_axis_changed('z')

    # Keep the old method name for backward compatibility
    onZ_axis_changed = on_z_axis_changed

    def on_bin_count_changed(self):
        """
        Handle changes to 2D histogram bin counts.
        
        When bin counts change, disable drawing mode, clear current drawing,
        and force immediate histogram recomputation with new bin sizes.
        Bypasses all caching and background computation for immediate response.
        """
        logging.log(0, "Bin count changed - forcing immediate recomputation with no cache")
        
        # Disable drawing mode and clear current drawing only
        if hasattr(self, 'mask_widget') and self.mask_widget is not None:
            self.mask_widget.set_drawing_enabled(False)
            self.mask_widget.clear_mask()
        
        try:
            from .plot_update_helpers import update_histograms
            update_histograms(self.parent)
            logging.log(0, "Bin count change - immediate histogram computation completed")
        except Exception as e:
            logging.error(f"Failed to compute histograms immediately after bin count change: {e}")
            # Fallback to regular update
            self.parent.request_plot_update(skip_clustering=True)
        
        logging.log(0, "Bin count change handled - forced immediate recomputation")

    def _on_normalize_changed(self):
        """Handle normalization (density) checkbox changes."""
        logging.log(0, "Normalization changed - clearing all caches and triggering full plot update")
        
        # Clear all caches to force fresh computation with new normalization settings
        
        # Trigger full update like the main update button
        self.parent.update_plots()
        
        logging.log(0, "Normalization change handled - full plot update triggered")

    def update_axis_scales(self):
        """Update all axis scales based on current settings and refresh plots"""
        # Set y-plot axes
        self.parent.g_yplot.set_axis_scale("left", self.scale_y)
        self.parent.g_yplot.set_axis_scale("right", self.scale_y)

        # Set x-plot axes
        self.parent.g_xplot.set_axis_scale("bottom", self.scale_x)
        self.parent.g_xplot.set_axis_scale("top", self.scale_x)

        # Set z-plot axes
        self.parent.g_zplot.set_axis_scale("bottom", self.scale_z)

        # CRITICAL: Log scale changes require full plot update like the main update button
        # because the binning, data representation, and axes all change with scale
        logging.log(0, "Axis scales updated - clearing all caches and triggering full plot update for log scale changes")
        
        # Clear all caches to force fresh computation with new scale settings
        
        # Trigger full update like the main update button
        self.parent.update_plots()
        
        logging.log(0, "Axis scales updated and full plot update triggered")

    # Keep the old method name for backward compatibility
    onUpdate_axis_scales = update_axis_scales

    def auto_selection_range(self):
        z = self.parent.z_values
        m = z.mean()
        sd = z.std()
        self.parent.selection_z.set_range(m - 2 * sd, m + 2 * sd)
        logging.log(0, f"Auto selection range set to: {(m - 2 * sd, m + 2 * sd)}")

    def update(self, update_comboboxes=True, update_plots=True, skip_clustering=True):
        """
        Update the plot control widget.
        
        Args:
            update_comboboxes (bool): Whether to refresh the axis selection comboboxes
            update_plots (bool): Whether to trigger plot updates
            skip_clustering (bool): Whether to skip clustering when updating plots
        """
        super(SurfacePlotWidget, self).update()
        
        if update_comboboxes:
            self.actionUpdatePlots.blockSignals(True)
            self.actionUpdate_axis_scales.blockSignals(True)
            
            # Save current selections before updating
            current_x = self.comboBoxSelX.currentText()
            current_y = self.comboBoxSelY.currentText()
            current_z = self.comboBoxSelZ.currentText()
            current_w = self.comboBoxWeight.currentText() if hasattr(self, 'comboBoxWeight') else ''
            
            # Block combobox signals to prevent triggering replots during updates
            self.comboBoxSelX.blockSignals(True)
            self.comboBoxSelY.blockSignals(True)
            self.comboBoxSelZ.blockSignals(True)
            
            try:
                try:
                    pn = [str(c) for c in list(self.parent.data_source.parameter_names)]
                except Exception:
                    pn = []
                self.comboBoxSelX.clear()
                self.comboBoxSelY.clear()
                self.comboBoxSelZ.clear()
                if hasattr(self, 'comboBoxWeight'):
                    self.comboBoxWeight.clear()
                self.comboBoxSelX.addItems(pn)
                self.comboBoxSelY.addItems(pn)
                self.comboBoxSelZ.addItems(pn)
                if hasattr(self, 'comboBoxWeight'):
                    self.comboBoxWeight.addItems(pn)
                
                # Restore previous selections if they still exist in the updated list
                if current_x in pn:
                    self.comboBoxSelX.setCurrentText(current_x)
                else:
                    if pn:
                        self.comboBoxSelX.setCurrentIndex(0)
                    logging.info(f"X selection '{current_x}' not available; keeping default")
                if current_y in pn:
                    self.comboBoxSelY.setCurrentText(current_y)
                else:
                    if pn:
                        self.comboBoxSelY.setCurrentIndex(0)
                    logging.info(f"Y selection '{current_y}' not available; keeping default")
                if current_z in pn:
                    self.comboBoxSelZ.setCurrentText(current_z)
                else:
                    if pn:
                        self.comboBoxSelZ.setCurrentIndex(0)
                    logging.info(f"Z selection '{current_z}' not available; keeping default")
                # Restore weight selection
                if hasattr(self, 'comboBoxWeight'):
                    if current_w in pn:
                        self.comboBoxWeight.setCurrentText(current_w)
                    else:
                        if pn:
                            self.comboBoxWeight.setCurrentIndex(0)
                        logging.info(f"Weight selection '{current_w}' not available; keeping default")
            finally:
                # Unblock combobox signals after updates
                self.comboBoxSelX.blockSignals(False)
                self.comboBoxSelY.blockSignals(False)
                self.comboBoxSelZ.blockSignals(False)
                self.actionUpdatePlots.blockSignals(False)
                self.actionUpdate_axis_scales.blockSignals(False)
            logging.log(0, "Updated parameter selectors (preserved existing selections, no replot triggered)")

        if update_plots:
            # Instead of triggering the action, call update_plots (batched) with skip_clustering
            self.parent.request_plot_update(skip_clustering=skip_clustering)
            logging.log(0, f"Triggered plot update with clustering {'skipped' if skip_clustering else 'enabled'}")

    def onClearSelection(self):
        logging.log(0, "onClearSelection")
        self.gates.clear()
        self._refresh_gate_table()
        # Preserve contrast during selection operations
        self.parent._preserve_contrast = True
        self.parent.request_plot_update(skip_clustering=True)
        self.parent._preserve_contrast = False

        # Add delayed marginal plot update to ensure proper rendering
        QtCore.QTimer.singleShot(100, self._delayed_marginal_update_after_clear)

    def _delayed_marginal_update_after_clear(self):
        """Delayed update of marginal plots after clearing selections."""
        try:
            # Import the marginal update function
            from .plot_update_helpers import _update_marginal_plots_from_cache
            _update_marginal_plots_from_cache(self.parent)
            logging.log(0, "Delayed marginal plot update completed after clear selection")
        except Exception as e:
            logging.warning(f"Failed to update marginal plots after clear selection: {e}")

    def _selection_axes(self):
        """The two parameter indices the current plane is drawn from."""
        return (int(getattr(self.parent, "x_parameter_index", 0)),
                int(getattr(self.parent, "y_parameter_index", 1)))

    def onSave_selection(self):
        """Save every selection, whatever shape it is.

        This used to dump ``selection.__dict__`` straight to JSON, which raises
        ``TypeError: Object of type ndarray is not JSON serializable`` as soon as
        a Gaussian or a painted selection is in the list — after the file has
        already been truncated. Going through a ChiSurf region collection lets
        each shape serialise itself.
        """
        from ..core.region_selection import save_selections

        logging.log(0, "onSave_selection")
        fn = QtWidgets.QFileDialog.getSaveFileName(
            None,
            "Selection JSON",
            self.parent.working_path,
            'All files (*.selection.json)'
        )[0]
        if not fn:
            return
        save_selections(self.get_selections(), fn, axes=self._selection_axes())
        logging.log(0, f"Selection saved to file: {fn}")

    def onLoad_selection(self):
        """Load selections of any shape, and files written by the old saver.

        The previous reader took ``parameter_idx``/``lower``/``upper`` off every
        entry, so an ellipse or a painted population was dropped — silently, and
        the analysis afterwards ran over a different set of points than the one
        the file described.
        """
        from ..core.region_selection import load_selections

        fn = QtWidgets.QFileDialog.getOpenFileName(
            None,
            "Selection JSON",
            self.parent.working_path,
            'All files (*.selection.json)'
        )[0]
        if not fn:
            return
        for selection in load_selections(fn, axes=self._selection_axes()):
            self.gates.add_selection(selection)
        self._gates_changed()
        logging.log(0, f"Selections loaded from file: {fn}")

    def on_auto_range_x(self):
        """Set X axis range to auto values from parent"""
        logging.log(0, "on_auto_range_x")
        self.spinBoxXmin.blockSignals(True)
        self.spinBoxXmax.blockSignals(True)
        self.spinBoxXmin.setValue(self.parent.xmin)
        self.spinBoxXmax.setValue(self.parent.xmax)
        self.spinBoxXmin.blockSignals(False)
        self.spinBoxXmax.blockSignals(False)

    # Keep the old method name for backward compatibility
    onAutoRangeX = on_auto_range_x

    def on_auto_range_y(self):
        """Set Y axis range to auto values from parent"""
        logging.log(0, "on_auto_range_y")
        self.spinBoxYmin.blockSignals(True)
        self.spinBoxYmax.blockSignals(True)
        self.spinBoxYmin.setValue(self.parent.ymin)
        self.spinBoxYmax.setValue(self.parent.ymax)
        self.spinBoxYmin.blockSignals(False)
        self.spinBoxYmax.blockSignals(False)

    # Keep the old method name for backward compatibility
    onAutoRangeY = on_auto_range_y

    def on_auto_range_z(self):
        """Set Z axis range to auto values from parent"""
        logging.log(0, "on_auto_range_z")
        self.spinBoxZmin.blockSignals(True)
        self.spinBoxZmax.blockSignals(True)
        self.spinBoxZmin.setValue(self.parent.zmin)
        self.spinBoxZmax.setValue(self.parent.zmax)
        self.spinBoxZmin.blockSignals(False)
        self.spinBoxZmax.blockSignals(False)

    # Keep the old method name for backward compatibility
    onAutoRangeZ = on_auto_range_z

    # ==================== The gate table ====================
    #
    # ``self.gates`` (:class:`ndxplorer.core.gates.GateList`) is the Selection
    # table; the emtk app keeps the same list. The QTableWidget is a view of
    # it, rebuilt whenever rows come or go, and every edit in it is written
    # back through ``GateList.edit`` -- nothing reads the widget to find out
    # which points are shown.

    def _gates_changed(self, immediate: bool = False) -> None:
        """Rows came or went: rebuild the table and redraw."""
        self._refresh_gate_table()
        self.parent._preserve_contrast = True
        try:
            if immediate:
                self.parent.update_plots(skip_clustering=True)
            else:
                self.parent.request_plot_update(skip_clustering=True)
        finally:
            self.parent._preserve_contrast = False

    def _refresh_gate_table(self) -> None:
        """Rebuild the QTableWidget from :attr:`gates`."""
        table = self.tableWidget
        editable = QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable
        fixed = QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled
        self._block_selection_item_changed = True
        try:
            table.setRowCount(0)
            table.setRowCount(len(self.gates))
            for r, gate in enumerate(self.gates):
                item0 = QtWidgets.QTableWidgetItem(str(gate.name))
                item0.setFlags(fixed if gate.kind == "G2D" else editable)
                table.setItem(r, 0, item0)
                for column, value in ((1, gate.bound_texts()[0]), (2, gate.bound_texts()[1])):
                    cell = QtWidgets.QTableWidgetItem(str(value))
                    cell.setFlags(editable if gate.is_interval else QtCore.Qt.ItemIsEnabled)
                    cell.setTextAlignment(QtCore.Qt.AlignCenter)
                    table.setItem(r, column, cell)
                for column, key in ((3, "invert"), (4, "enabled")):
                    box = QtWidgets.QCheckBox(table)
                    box.setChecked(bool(getattr(gate, key)))
                    box.stateChanged.connect(
                        lambda state, r=r, key=key: self._on_gate_flag(r, key, state))
                    table.setCellWidget(r, column, box)
        finally:
            self._block_selection_item_changed = False

    def _on_gate_flag(self, row: int, key: str, state) -> None:
        """An Invert or Enable check box was toggled."""
        if self.gates.edit(row, key, bool(state)):
            self.actionUpdatePlots.trigger()

    def onSelectionTableClicked(self):
        """A double click on a row removes it."""
        logging.log(0, "onSelectionTableClicked")
        row = self.tableWidget.currentRow()
        if row < 0:
            return
        if self.gates.remove([row]):
            # Redraw immediately so the removed gate is not shown a moment longer.
            self._gates_changed(immediate=True)

    def addSelection(self, idx, xmin, xmax, invert=False, enabled=True, name=""):
        """Add an interval gate on column *idx* (bounds are ordered)."""
        self.gates.add_interval(idx, name, xmin, xmax, invert, enabled)
        self._gates_changed()
        logging.log(0, f"Added selection for parameter index {idx} with range ({xmin}, {xmax}), invert={invert}, enabled={enabled}")

    def addGaussianSelection(self, idx1, idx2, mu, cov, sigma=1.0, invert=False, enabled=True, name="", log_x=False, log_y=False):
        """Add a 2-D Gaussian (elliptical) gate."""
        self.gates.add_gaussian(idx1, idx2, mu, cov, sigma, invert, enabled, name, log_x, log_y)
        self._gates_changed()
        logging.log(0, f"Added G2D selection for idxs ({idx1}, {idx2}) with sigma={sigma}")

    def add_selection_object(self, selection):
        """Add a gate of any kind from its selection object.

        A painted mask (:class:`~ndxplorer.core.data_source.MaskDataSelection`)
        or a drawn region (:class:`~ndxplorer.core.region_selection.RegionDataSelection`)
        is kept by its row, since no cell can hold a bitmap or a polygon.
        """
        self.gates.add_selection(selection)
        self._gates_changed()
        logging.info(f"Added selection row: {getattr(selection, 'name', '')}")

    def onAddSelection(self):
        idx, name = self.p3
        xsel = self.parent.selection_z.get_range()
        xmin = float(min(xsel))
        xmax = float(max(xsel))
        self.gates.add_interval(idx, name, xmin, xmax)
        self._refresh_gate_table()
        logging.log(0, f"onAddSelection: Added selection for {name} with range ({xmin}, {xmax})")

        # A selection drawn during playback describes the slice it was drawn on.
        self._add_playback_selection_if_needed()

        # Preserve contrast during selection operations
        self.parent._preserve_contrast = True
        self.parent.update_plots()
        self.parent._preserve_contrast = False

    def get_selections(self):
        """The gates as selections, read from :attr:`gates` (not from the widget)."""
        return self.gates.selections()

    def onSelectionItemChanged(self, item: QtWidgets.QTableWidgetItem):
        """A name or a bound was typed into the table: write it into the gate.

        Column 0 is the name; columns 1 and 2 are the bounds, which only an
        interval has. An edit the gate refuses (not a number, a bound on a mask)
        is put back; one typed past its partner moves the partner, as
        :meth:`GateList.edit` does.
        """
        if getattr(self, "_block_selection_item_changed", False):
            return
        row, col = item.row(), item.column()
        key = {0: "name", 1: "lower", 2: "upper"}.get(col)
        if key is None or not 0 <= row < len(self.gates):
            return
        if key != "name" and hasattr(self.parent, 'is_data_ready') and not self.parent.is_data_ready():
            logging.info("Selection edit ignored: load data before editing selections.")
            self._refresh_gate_table()
            return
        changed = self.gates.edit(row, key, item.text().strip())
        # Show what the gate holds now: the refused text reverts, a moved
        # partner bound appears.
        self._refresh_gate_table()
        if changed:
            self.parent._preserve_contrast = True
            self.parent.update_plots()
            self.parent._preserve_contrast = False

    def onDeleteSelectionRows(self):
        """Delete selected selection rows using the Delete key."""
        sel_model = self.tableWidget.selectionModel()
        if sel_model is None:
            return
        rows = {idx.row() for idx in sel_model.selectedIndexes()}
        if self.gates.remove(rows):
            self._refresh_gate_table()
            self.parent._preserve_contrast = True
            self.parent.update_plots()
            self.parent._preserve_contrast = False

    def onSelectionTableContextMenu(self, position):
        """Show context menu for selection table."""
        table = self.tableWidget
        # Create context menu
        menu = QtWidgets.QMenu(self)
        
        # Add actions
        select_all_action = menu.addAction("Select All")
        clear_action = menu.addAction("Clear")
        delete_action = menu.addAction("Delete")

        # Hand the gated bursts to a real analysis. This is the natural place
        # for it: the gate is what is being right-clicked.
        menu.addSeparator()
        try:
            from ..analysis.send_menu import add_send_menu

            add_send_menu(menu, self.parent)
        except Exception:
            logging.debug("could not build the send menu", exc_info=True)

        # Show menu and get action
        action = menu.exec_(table.mapToGlobal(position))
        
        # Handle action
        if action == select_all_action:
            self.onSelectAllSelections()
        elif action == clear_action:
            self.onClearSelection()
        elif action == delete_action:
            self.onDeleteSelectionRows()

    def onSelectAllSelections(self):
        """Select all rows in the selection table."""
        table = self.tableWidget
        table.selectAll()
        logging.log(0, "All selection rows selected")

    def onSelectionCellClicked(self, row: int, col: int):
        """Handle single-click on a cell to start inline editing after the
        double-click interval has elapsed (so double-click can still delete).
        """
        # Store pending index for single-click editing
        try:
            model = self.tableWidget.model()
            if model is None:
                return
            self._pending_edit_index = model.index(row, col)
            # Start a timer equal to the system double-click interval
            app = QtWidgets.QApplication.instance()
            dci = app.doubleClickInterval() if app is not None else 250
            self._single_click_edit_timer.start(int(dci))
        except Exception:
            # Fallback: start soon
            self._single_click_edit_timer.start(200)

    def onSelectionCellDoubleClicked(self, row: int, col: int):
        """Cancel pending single-click edit when a double-click occurs.
        The actual deletion is handled by the .ui connection to
        actionSelectionTableClicked.
        """
        try:
            if self._single_click_edit_timer.isActive():
                self._single_click_edit_timer.stop()
        except Exception:
            pass
        self._pending_edit_index = None

    def _perform_pending_single_click_edit(self):
        """If there is a pending single-click index, start editing it.

        The name can be edited on every gate but a Gaussian; the bounds only on
        an interval (the cell flags say so, set by ``_refresh_gate_table``).
        """
        index = getattr(self, "_pending_edit_index", None)
        self._pending_edit_index = None
        if index is None or not index.isValid():
            return
        it = self.tableWidget.item(index.row(), index.column())
        if it is not None and index.column() in (0, 1, 2) and (it.flags() & QtCore.Qt.ItemIsEditable):
            self.tableWidget.edit(index)

    # ==================== Playback ====================
    #
    # The transport, the mode and the speed live in ``playback.view.json`` and
    # are rendered by chisurf's AutoForm; what is left here is the wiring
    # between that panel, the :class:`~ndxplorer.core.playback.PlaybackController`
    # that owns the state, and the plot that has to redraw.

    def _build_playback_panel(self):
        """Create the playback controller, its view model and its panel."""
        from ..core.playback import PlaybackController

        self.playback = PlaybackController(fps=self._load_playback_fps())
        self.playback_form = None
        self.playback_model = None

        try:
            from .playback_view_model import PlaybackViewModel
            from chisurf.gui.autoform import AutoForm
        except ImportError as exc:
            # chisurf is a declared dependency, so this is a broken environment
            # rather than a supported one -- but a missing panel must not take
            # the whole plot control down with it.
            logging.error("Playback panel unavailable (chisurf missing?): %s", exc)
            return

        self.playback_model = PlaybackViewModel(
            self.playback,
            on_change=self._on_playback_changed,
            on_axis_change=self._on_playback_axis_changed,
            on_rebuild=self._rebuild_playback_panel,
            on_timing=self._sync_playback_timer,
        )
        # The model owns *when* a step is due; the Qt window only has to wake
        # it up, at the step interval, while it plays.
        self._playback_timer = QtCore.QTimer(self)
        self._playback_timer.timeout.connect(self.playback_model.tick)
        self.playback_form = AutoForm(self.playback_model, parent=self)
        # Maximum, not the default Preferred: an AutoForm ends its layout with a
        # stretch, so given spare vertical space it keeps it -- and folding the
        # panel then leaves a panel-sized hole instead of giving the space back
        # to the group boxes below. The group box this replaces was Fixed for
        # the same reason.
        self.playback_form.setSizePolicy(QtWidgets.QSizePolicy.Preferred,
                                         QtWidgets.QSizePolicy.Maximum)
        # First in the dock, where the Image group box was: it is what the user
        # scrubs while watching the plot, and a control you drive continuously
        # does not belong below four panels of settings.
        self.verticalLayout_3.insertWidget(0, self.playback_form)
        self.playback_form.setVisible(False)
        self.playback_form.rebuilt.connect(self._wire_playback_fold)
        self._wire_playback_fold()

    def _sync_playback_timer(self):
        """Start, stop or re-time the timer that drives the playback's ticks."""
        model = self.playback_model
        timer = getattr(self, "_playback_timer", None)
        if model is None or timer is None:
            return
        timer.setInterval(max(1, int(round(model.interval * 1000.0))))
        if model.playing and not timer.isActive():
            timer.start()
        elif not model.playing and timer.isActive():
            timer.stop()

    def _wire_playback_fold(self):
        """Remember whether the user left the panel open, across rebuilds.

        The step slider's range is the step count, which is itself editable, so
        changing it rebuilds the form. Without this the panel would fold itself
        every time -- the spec's ``collapsed`` is the *opening* state, not a
        standing instruction.
        """
        try:
            from chisurf.gui.widgets.collapsible_box import CollapsibleBox
        except ImportError:  # pragma: no cover - chisurf is a hard dependency
            return
        for box in self.playback_form.findChildren(CollapsibleBox):
            box.toggled.connect(self._on_playback_fold)
        # A rebuild makes fresh widgets, which start without the hover status.
        self._update_playback_tooltip()

    def _on_playback_fold(self, expanded: bool):
        if self.playback_model is not None:
            self.playback_model.collapsed = not expanded

    def _build_panels(self):
        """Wrap the dock's blocks in foldable AutoForm panels.

        The widgets are the ones ``uic`` built; the form supplies the headers,
        the folds and the order. Each is re-parented into the form, so it has to
        come out of the dock's layout first -- leaving it there gives the layout
        an item pointing at a widget that now lives somewhere else, and the space
        it used to occupy stays reserved.

        The panels take the position of the *first* block they replace, so
        Playback (inserted before this runs) stays on top.
        """
        self.panels_form = None
        self.panels_model = None

        try:
            from .plot_panels_view_model import PlotPanelsViewModel
            from chisurf.gui.autoform import AutoForm
        except ImportError as exc:
            logging.error("Plot-control panels unavailable (chisurf missing?): %s", exc)
            return

        self.panels_model = PlotPanelsViewModel(self, parent=self)
        widgets = [self.panels_model.widget_for(attr)
                   for attr in PlotPanelsViewModel.WIDGETS]
        widgets = [w for w in widgets if w is not None]
        if not widgets:
            return

        index = min((self.verticalLayout_3.indexOf(w) for w in widgets
                     if self.verticalLayout_3.indexOf(w) >= 0), default=-1)
        for widget in widgets:
            self.verticalLayout_3.removeWidget(widget)

        self.panels_form = AutoForm(self.panels_model, parent=self)
        self.verticalLayout_3.insertWidget(
            index if index >= 0 else self.verticalLayout_3.count(), self.panels_form)
        self.panels_form.rebuilt.connect(self._wire_panel_folds)
        self._wire_panel_folds()

    def _wire_panel_folds(self):
        """Remember which blocks the user left open, across rebuilds."""
        try:
            from chisurf.gui.widgets.collapsible_box import CollapsibleBox
        except ImportError:  # pragma: no cover - chisurf is a hard dependency
            return
        for box in self.panels_form.findChildren(CollapsibleBox):
            box.toggled.connect(
                lambda expanded, b=box: self.panels_model.collapsed.__setitem__(
                    b.title(), not expanded))

    def _load_playback_fps(self) -> int:
        """Playback rate from the settings file, in steps per second."""
        from ..core.playback import DEFAULT_FPS, fps_from_settings

        try:
            settings_path = pathlib.Path(__file__).parent.parent / 'settings' / 'mfd.settings.json'
            if not settings_path.exists():
                return DEFAULT_FPS
            with open(settings_path, 'r') as f:
                return fps_from_settings(json.load(f))
        except Exception as exc:
            logging.warning("Failed to read playback settings: %s", exc)
        return DEFAULT_FPS

    def setup_playback(self, data_source):
        """Point the playback at whatever the loaded data can be played back along.

        Called after every load. An image stack is played back along its frame
        index and a burst table along its macro time; anything else leaves the
        panel present but idle, with every numeric column offered in the combo
        so the user can pick one.

        Parameters
        ----------
        data_source : ndxplorer.core.data_source.DataSource
            The freshly loaded table.
        """
        from ..core.playback import macro_time_column
        from ..utils.axis_helpers import frame_column

        if self.playback_model is None:
            return
        if data_source is None or getattr(data_source, "empty", True):
            self.playback.set_axis(None)
            self._rebuild_playback_panel(immediate=True)
            self.playback_form.setVisible(False)
            return

        names = list(data_source.parameter_names)
        # "" first, so the combo can express "play nothing back".
        self.playback_model.set_axis_options([""] + names)

        axis = frame_column(names) or macro_time_column(names)
        self._set_playback_axis(axis, data_source)
        self.playback_form.setVisible(True)
        self._rebuild_playback_panel(immediate=True)
        logging.info("Playback axis after load: %r", axis)

    def _set_playback_axis(self, name, data_source=None):
        """Bind the controller to `name`, taking its bounds from the data."""
        if data_source is None:
            data_source = getattr(self.parent, "data_source", None)
        values = None
        if name and data_source is not None:
            try:
                values = data_source.column_values(name)
            except Exception as exc:
                logging.warning("Playback column %r unreadable: %s", name, exc)
                name = None
        self.playback.set_axis(name, values)

    def _on_playback_axis_changed(self, name):
        """The user picked a different column in the panel."""
        self._set_playback_axis(name)

    def _on_playback_changed(self):
        """Anything that changes what is on screen: redraw, then re-read the panel."""
        if self.parent is not None:
            self.parent.request_plot_update()
        if self.playback_form is not None:
            self.playback_form.sync_fields()
        self._update_playback_tooltip()

    def _update_playback_tooltip(self):
        """The old always-on status line, folded into hover.

        The slice on screen and how many points survive it used to be a
        persistent info row under the transport -- always visible, rarely
        needed. It now lives on the Step row: the slider, its value box and
        the row itself all answer on hover.
        """
        model, form = self.playback_model, self.playback_form
        if model is None or form is None:
            return
        try:
            text = model.status_text()
            for section, w in getattr(form, "_section_widgets", []):
                if getattr(section, "attr", "") != "position":
                    continue
                w.setToolTip(text)
                for part in (getattr(w, "slider", None), getattr(w, "editor", None)):
                    if part is not None:
                        part.setToolTip(text)
                break
        except Exception:  # pragma: no cover - defensive
            logging.debug("could not update the playback tooltip", exc_info=True)

    def _rebuild_playback_panel(self, immediate: bool = False):
        """Re-read the view spec, because the step slider's range moved.

        Deferred by default: the request arrives from inside the signal of a
        widget that the rebuild destroys.
        """
        if self.playback_form is None:
            return
        if immediate:
            self.playback_form.rebuild()
        else:
            QtCore.QTimer.singleShot(0, self.playback_form.rebuild)

    def update_playback_settings(self, fps: int = None):
        """Set the playback rate, in steps per second.

        Parameters
        ----------
        fps : int, optional
            New rate; ``None`` leaves it alone.
        """
        if fps is not None and self.playback_model is not None:
            self.playback_model.fps = int(fps)
            if self.playback_form is not None:
                self.playback_form.sync_fields()
        logging.info("Playback rate: %s fps", self.playback.fps)

    def _add_playback_selection_if_needed(self):
        """Add the slice on screen to the selection table.

        A selection drawn while one slice is shown describes points in *that*
        slice, so the gate has to say so as well -- otherwise it silently means
        something wider as soon as the playback moves on. Reached from the
        add-selection path only, never from a playback step.
        """
        playback = getattr(self, "playback", None)
        if playback is None or not playback.gating:
            return
        try:
            param_names = self.parent.data_source.parameter_names
            if playback.axis_name not in param_names:
                return
            idx = param_names.index(playback.axis_name)
            lower, upper = playback.bounds
            for sel in self.get_selections():
                if getattr(sel, "idx", None) == idx:
                    if getattr(sel, "lower", None) == lower and getattr(sel, "upper", None) == upper:
                        return
            self.addSelection(idx, lower, upper, False, True, playback.axis_name)
            logging.info("Added playback selection: %s in [%g, %g]",
                         playback.axis_name, lower, upper)
        except Exception as e:
            logging.warning(f"Failed to add playback selection: {e}")

    # The background histogram worker stood here: a QThread, a manager, four
    # progress signals, and a 6,000,000-point threshold below which none of it
    # ran. A full redraw is about twenty milliseconds, so nothing reached the
    # threshold, and the two paths could return differently shaped results for
    # the same data. ``plot_update_helpers.update_histograms`` is the one path.

    # clear_histogram_cache and clear_frame_histogram_cache used to live here,
    # and eight places called them in pairs. Neither cache was ever written to:
    # they were constructed, cleared and reconfigured, and nothing ever put a
    # histogram in either one. A fill costs a few milliseconds now, less than
    # deciding whether a cached one is still valid -- and a stale histogram is
    # the one bug that shows a wrong picture with every number under it
    # agreeing, because they came from the same stale object.
