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

from ..core.data_source import RectangularDataSelection, Gaussian2DSelection, MaskDataSelection
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
        self._selections = list()  # Instance-level selections list
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

        if name in self.axis_settings:
            d = self.axis_settings[name]

            # Set the 1D histogram bins
            setattr(self, props['hist_1d'], d.get('n_bins_1d', 50))

            # Set the 2D histogram bins if applicable
            if props['hist_2d'] is not None:
                # Special handling for pixel - adjust 2d hist bins to max value
                if "pixel" in name.lower():
                    setattr(self, props['hist_2d'], int(d.get('max', 256)))
                    logging.log(0, f"{name} selected: Setting {props['hist_2d']} to {getattr(self, props['hist_2d'])}")
                else:
                    setattr(self, props['hist_2d'], d.get('n_bins_2d', 50))

            # Set the min, max, and scale
            setattr(self, props['min'], d.get('min', getattr(self.parent, props['parent_min'])))
            setattr(self, props['max'], d.get('max', getattr(self.parent, props['parent_max'])))
            setattr(self, props['scale'], d.get('scale', "lin"))

            logging.log(0, f"{axis.upper()} axis changed to settings: {d}")
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
        self.tableWidget.setRowCount(0)
        self._selections.clear()  # Clear instance-level selections
        # Clear frame histogram cache when selections change
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
        from ..core.region_selection import RegionDataSelection, load_selections

        fn = QtWidgets.QFileDialog.getOpenFileName(
            None,
            "Selection JSON",
            self.parent.working_path,
            'All files (*.selection.json)'
        )[0]
        if not fn:
            return
        for selection in load_selections(fn, axes=self._selection_axes()):
            if isinstance(selection, RegionDataSelection):
                self.add_region_selection(selection)
            else:
                self.addSelection(
                    selection.parameter_idx, selection.lower, selection.upper,
                    selection.invert, selection.enabled, selection.name,
                )
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

    def onSelectionTableClicked(self):
        logging.log(0, "onSelectionTableClicked")
        row = self.tableWidget.currentRow()
        if row < 0:
            return
        self.tableWidget.removeRow(row)
        # Clear frame histogram cache when selections change
        # Redraw immediately (matching the selection-edit path) so removing a
        # selection updates the plot right away. The debounced request_plot_update
        # could leave the plot showing the removed selection until the next event.
        try:
            self.parent._preserve_contrast = True
            self.parent.update_plots(skip_clustering=True)
        finally:
            self.parent._preserve_contrast = False

    def addSelection(self, idx, xmin, xmax, invert=False, enabled=True, name=""):
        # Clear frame histogram cache when selections change
        
        # Ensure xmin < xmax
        if xmin > xmax:
            xmin, xmax = xmax, xmin
            logging.log(0, f"Swapped xmin and xmax to ensure min-max ordering: ({xmin}, {xmax})")

        table = self.tableWidget
        row = table.rowCount()
        table.setRowCount(row + 1)

        tmp = QtWidgets.QTableWidgetItem("%s" % name)
        tmp.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable)
        tmp.setData(1, idx)
        table.setItem(row, 0, tmp)

        tmp = QtWidgets.QTableWidgetItem()
        tmp.setText(str(xmin))
        tmp.setData(0, float(xmin))
        tmp.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable)
        font = QtGui.QFont()
        font.setPointSize(10)
        tmp.setFont(font)
        tmp.setTextAlignment(QtCore.Qt.AlignCenter)
        table.setItem(row, 1, tmp)

        tmp = QtWidgets.QTableWidgetItem()
        tmp.setText(str(xmax))
        tmp.setData(0, float(xmax))
        tmp.setFlags(QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsEditable)
        font = QtGui.QFont()
        font.setPointSize(10)
        tmp.setFont(font)
        tmp.setTextAlignment(QtCore.Qt.AlignCenter)
        table.setItem(row, 2, tmp)

        cb_invert_x = QtWidgets.QCheckBox(table)
        table.setCellWidget(row, 3, cb_invert_x)
        cb_invert_x.setChecked(invert)

        cb_enable_x = QtWidgets.QCheckBox(table)
        table.setCellWidget(row, 4, cb_enable_x)
        cb_enable_x.setChecked(enabled)
        # Fast path for 2D rectangle selection: use batched update to keep UI snappy
        # - request_plot_update() batches rapid selections (40ms timer)
        # - skip_clustering=True avoids expensive clustering recomputation
        # - Cache system naturally detects selection changes and recomputes only when needed
        self.parent.request_plot_update(skip_clustering=True)

        # Actions for selection checkbox
        cb_enable_x.stateChanged.connect(self.actionUpdatePlots.trigger)
        cb_invert_x.stateChanged.connect(self.actionUpdatePlots.trigger)
        logging.log(0, f"Added selection for parameter index {idx} with range ({xmin}, {xmax}), invert={invert}, enabled={enabled}")

    def addGaussianSelection(self, idx1, idx2, mu, cov, sigma=1.0, invert=False, enabled=True, name="", log_x=False, log_y=False):
        table = self.tableWidget
        row = table.rowCount()
        table.setRowCount(row + 1)

        # Column 0: name with metadata
        meta = {
            "type": "G2D",
            "idx1": int(idx1),
            "idx2": int(idx2),
            "mu": [float(mu[0]), float(mu[1])],
            "cov": [
                [float(cov[0][0]), float(cov[0][1])],
                [float(cov[1][0]), float(cov[1][1])]
            ],
            "sigma": float(sigma),
            "log_x": bool(log_x),
            "log_y": bool(log_y)
        }
        item0 = QtWidgets.QTableWidgetItem("%s" % name)
        item0.setFlags(QtCore.Qt.ItemIsEnabled)
        # Keep legacy index role for compatibility (store idx1)
        item0.setData(1, int(idx1))
        try:
            item0.setData(32, json.dumps(meta))  # Qt.UserRole
        except Exception:
            item0.setData(1, int(idx1))
        table.setItem(row, 0, item0)

        # Columns 1 and 2: placeholders (not used by G2D), keep numeric values to avoid parsing errors
        it1 = QtWidgets.QTableWidgetItem()
        it1.setText(str(0.0))
        it1.setData(0, float(0.0))
        it1.setFlags(QtCore.Qt.ItemIsEnabled)
        it1.setTextAlignment(QtCore.Qt.AlignCenter)
        table.setItem(row, 1, it1)

        it2 = QtWidgets.QTableWidgetItem()
        it2.setText(str(0.0))
        it2.setData(0, float(0.0))
        it2.setFlags(QtCore.Qt.ItemIsEnabled)
        it2.setTextAlignment(QtCore.Qt.AlignCenter)
        table.setItem(row, 2, it2)

        # Invert and Enabled checkboxes
        cb_invert = QtWidgets.QCheckBox(table)
        table.setCellWidget(row, 3, cb_invert)
        cb_invert.setChecked(bool(invert))

        cb_enable = QtWidgets.QCheckBox(table)
        table.setCellWidget(row, 4, cb_enable)
        cb_enable.setChecked(bool(enabled))

        # Fast path for 2D Gaussian selection: use batched update to keep UI snappy
        # - request_plot_update() batches rapid selections (40ms timer)
        # - skip_clustering=True avoids expensive clustering recomputation
        # - Cache system naturally detects selection changes and recomputes only when needed
        self.parent.request_plot_update(skip_clustering=True)
        cb_enable.stateChanged.connect(self.actionUpdatePlots.trigger)
        cb_invert.stateChanged.connect(self.actionUpdatePlots.trigger)
        logging.log(0, f"Added G2D selection for idxs ({idx1}, {idx2}) with sigma={sigma}, invert={invert}, enabled={enabled}, log_x={log_x}, log_y={log_y}")

    def addRegionSelection(self, selection, invert: bool = False, enabled: bool = True):
        """Add a region-backed gate to the table.

        The row carries only the ``selection_id``; the gate itself stays in
        ``_selections``. That is deliberate and matches how the table already
        rebuilds a ``Region`` row — a region can be a polygon or a composite,
        and round-tripping one through table metadata would flatten it to
        whatever the metadata schema happened to cover.

        Parameters
        ----------
        selection : RegionDataSelection
            Already appended to ``_selections`` by the caller.
        invert, enabled : bool
            Initial flag states.
        """
        table = self.tableWidget
        row = table.rowCount()
        table.setRowCount(row + 1)

        meta = {
            "type": "Region",
            "idx1": int(selection.idx1),
            "idx2": int(selection.idx2),
            "selection_id": selection.selection_id,
        }
        item0 = QtWidgets.QTableWidgetItem(str(selection.name))
        item0.setFlags(QtCore.Qt.ItemIsEnabled)
        item0.setData(1, int(selection.idx1))
        try:
            item0.setData(32, json.dumps(meta))  # Qt.UserRole
        except Exception:
            item0.setData(1, int(selection.idx1))
        table.setItem(row, 0, item0)

        for column in (1, 2):
            placeholder = QtWidgets.QTableWidgetItem()
            placeholder.setText(str(0.0))
            placeholder.setData(0, float(0.0))
            placeholder.setFlags(QtCore.Qt.ItemIsEnabled)
            placeholder.setTextAlignment(QtCore.Qt.AlignCenter)
            table.setItem(row, column, placeholder)

        cb_invert = QtWidgets.QCheckBox(table)
        table.setCellWidget(row, 3, cb_invert)
        cb_invert.setChecked(bool(invert))

        cb_enable = QtWidgets.QCheckBox(table)
        table.setCellWidget(row, 4, cb_enable)
        cb_enable.setChecked(bool(enabled))

        self.parent.request_plot_update(skip_clustering=True)
        cb_enable.stateChanged.connect(self.actionUpdatePlots.trigger)
        cb_invert.stateChanged.connect(self.actionUpdatePlots.trigger)
        logging.log(0, f"Added region selection {selection.name!r} for idxs "
                       f"({selection.idx1}, {selection.idx2})")

    def addMaskSelection(self, name, mask, edges1, edges2, idx1, idx2, invert=False, enabled=True, selection_id=None):
        """Add a mask-based selection to the table."""
        table = self.tableWidget
        row = table.rowCount()
        
        try:
            self._block_selection_item_changed = True
            table.setRowCount(row + 1)

            # Metadata for MaskDataSelection
            meta = {
                "type": "Mask",
                "name": str(name),
                "idx1": int(idx1),
                "idx2": int(idx2),
                "invert": bool(invert),
                "enabled": bool(enabled),
                "selection_id": str(selection_id) if selection_id else None
            }

            item0 = QtWidgets.QTableWidgetItem(str(name))
            item0.setFlags(QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEditable)
            # Store index for compatibility
            item0.setData(1, int(idx1))
            try:
                # Store metadata redundantly in UserRole AND role 32
                meta_json = json.dumps(meta)
                item0.setData(QtCore.Qt.UserRole, meta_json)
                item0.setData(32, meta_json)
            except Exception as e:
                logging.debug(f"Failed to set metadata for mask selection: {e}")
            table.setItem(row, 0, item0)

            # Placeholders for columns 1 and 2
            for col in [1, 2]:
                tmp = QtWidgets.QTableWidgetItem("Bitmap")
                # Do NOT set data role 0 to 0.0, so onSelectionItemChanged knows it's text
                tmp.setFlags(QtCore.Qt.ItemIsEnabled)
                tmp.setTextAlignment(QtCore.Qt.AlignCenter)
                table.setItem(row, col, tmp)

            # Invert and Enabled checkboxes
            cb_invert = QtWidgets.QCheckBox(table)
            table.setCellWidget(row, 3, cb_invert)
            cb_invert.setChecked(bool(invert))

            cb_enable = QtWidgets.QCheckBox(table)
            table.setCellWidget(row, 4, cb_enable)
            cb_enable.setChecked(bool(enabled))

            # Re-trigger plot update
            self.parent.request_plot_update(skip_clustering=True)
            cb_enable.stateChanged.connect(self.actionUpdatePlots.trigger)
            cb_invert.stateChanged.connect(self.actionUpdatePlots.trigger)
            logging.info(f"Added mask selection UI row: {name} (id={selection_id})")
        finally:
            self._block_selection_item_changed = False

    def add_region_selection(self, selection):
        """Add a ChiSurf-region gate as a row in the selection table.

        The region itself is kept in ``self._selections`` and the row carries its
        ``selection_id``, the same way a painted mask is handled: a table cell
        cannot hold a polygon, so the row is a handle and the object is the
        truth.

        Parameters
        ----------
        selection : ndxplorer.core.region_selection.RegionDataSelection
        """
        table = self.tableWidget
        row = table.rowCount()
        try:
            self._block_selection_item_changed = True
            table.setRowCount(row + 1)
            self._selections.append(selection)

            meta = {
                "type": "Region",
                "name": str(selection.name),
                "idx1": int(selection.idx1),
                "idx2": int(selection.idx2),
                "invert": bool(selection.invert),
                "enabled": bool(selection.enabled),
                "selection_id": str(selection.selection_id),
            }
            item0 = QtWidgets.QTableWidgetItem(str(selection.name))
            item0.setFlags(
                QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsEditable
            )
            item0.setData(1, int(selection.idx1))
            meta_json = json.dumps(meta)
            item0.setData(QtCore.Qt.UserRole, meta_json)
            item0.setData(32, meta_json)
            table.setItem(row, 0, item0)

            # The bounds columns describe the shape rather than a range: a
            # polygon has no "lower" and "upper" to type into.
            for col, text in ((1, selection.shape), (2, "shape")):
                cell = QtWidgets.QTableWidgetItem(text)
                cell.setFlags(QtCore.Qt.ItemIsEnabled)
                cell.setTextAlignment(QtCore.Qt.AlignCenter)
                table.setItem(row, col, cell)

            cb_invert = QtWidgets.QCheckBox(table)
            table.setCellWidget(row, 3, cb_invert)
            cb_invert.setChecked(bool(selection.invert))
            cb_enable = QtWidgets.QCheckBox(table)
            table.setCellWidget(row, 4, cb_enable)
            cb_enable.setChecked(bool(selection.enabled))
            cb_enable.stateChanged.connect(self.actionUpdatePlots.trigger)
            cb_invert.stateChanged.connect(self.actionUpdatePlots.trigger)

            self.parent.request_plot_update(skip_clustering=True)
            logging.info(f"Added region selection row: {selection.name} ({selection.shape})")
        finally:
            self._block_selection_item_changed = False

    def onAddSelection(self):
        idx, name = self.p3
        xsel = self.parent.selection_z.get_range()
        xmin = float(min(xsel))
        xmax = float(max(xsel))
        self.addSelection(idx, xmin, xmax, False, True, name)
        logging.log(0, f"onAddSelection: Added selection for {name} with range ({xmin}, {xmax})")
        
        # A selection drawn during playback describes the slice it was drawn on.
        self._add_playback_selection_if_needed()
        
        # Preserve contrast during selection operations
        self.parent._preserve_contrast = True
        self.parent.update_plots()
        self.parent._preserve_contrast = False
    def get_selections(self):
        selections = list()
        table = self.tableWidget
        n_rows = int(table.rowCount())
        
        # Log the internal selections list state for debugging
        logging.debug(f"get_selections: table_rows={n_rows}, internal_list_size={len(self._selections)}")
        
        for r in range(n_rows):
            item0 = table.item(r, 0)
            if item0 is None:
                continue
                
            idx = int(item0.data(1))
            name = str(item0.text()) # Use text() directly for comparison
            lower_item = table.item(r, 1)
            upper_item = table.item(r, 2)
            
            # Use safe conversion for lower/upper bounds
            def safe_float(item):
                if item is None:
                    return 0.0
                try:
                    # Try data role 0 first (stored numeric value)
                    data_val = item.data(0)
                    if data_val is not None:
                        try:
                            return float(data_val)
                        except (ValueError, TypeError):
                            pass
                    
                    # Fallback to display text
                    txt = item.text().strip()
                    if txt in ("Bitmap", "Mask", "G2D", "---"):
                        return 0.0
                    return float(txt)
                except (ValueError, TypeError):
                    return 0.0

            lower = safe_float(lower_item)
            upper = safe_float(upper_item)
            
            # Get invert and enabled states from checkboxes
            cb_invert = table.cellWidget(r, 3)
            cb_enable = table.cellWidget(r, 4)
            invert = cb_invert.isChecked() if cb_invert else False
            enabled = cb_enable.isChecked() if cb_enable else True
            logging.debug(f"Row {r} ({name}): invert={invert}, enabled={enabled}")
            
            # Try to decode metadata
            meta = None
            try:
                # Try multiple roles for metadata
                # Use a larger set of roles to be safe
                for role in [QtCore.Qt.UserRole, 32, QtCore.Qt.UserRole + 10, QtCore.Qt.UserRole + 100]:
                    meta_raw = item0.data(role)
                    if meta_raw:
                        try:
                            if isinstance(meta_raw, dict):
                                meta = meta_raw
                            else:
                                meta = json.loads(str(meta_raw))
                            if meta and isinstance(meta, dict) and "type" in meta: 
                                break
                        except Exception:
                            continue
            except Exception:
                meta = None
            
            # Identify selection type with heavy fallback
            sel_type = None
            if isinstance(meta, dict):
                sel_type = meta.get("type")
            
            # Fallback identification based on cell text if metadata missing or corrupted
            if sel_type is None:
                txt1 = lower_item.text() if lower_item else ""
                txt2 = upper_item.text() if upper_item else ""
                if "Bitmap" in txt1 or "Bitmap" in txt2 or "Mask" in name:
                    sel_type = "Mask"
                    logging.info(f"Row {r}: Identified as 'Mask' via text fallback (name='{name}')")
                elif "G2D" in name:
                    sel_type = "G2D"
                    logging.info(f"Row {r}: Identified as 'G2D' via text fallback (name='{name}')")

            # RECONSTRUCTION
            if sel_type == "G2D":
                try:
                    idx1 = int(meta.get("idx1", idx)) if meta else idx
                    idx2 = int(meta.get("idx2", idx)) if meta else idx
                    mu = meta.get("mu", [0.0, 0.0]) if meta else [0.0, 0.0]
                    cov = meta.get("cov", [[1.0, 0.0], [0.0, 1.0]]) if meta else [[1.0, 0.0], [0.0, 1.0]]
                    sigma = float(meta.get("sigma", 1.0)) if meta else 1.0
                    log_x = bool(meta.get("log_x", False)) if meta else False
                    log_y = bool(meta.get("log_y", False)) if meta else False
                    
                    selections.append(
                        Gaussian2DSelection(
                            parameter_idx1=idx1,
                            parameter_idx2=idx2,
                            mu=mu,
                            cov=cov,
                            sigma=sigma,
                            invert=invert,
                            enabled=enabled,
                            name=name,
                            log_x=log_x,
                            log_y=log_y
                        )
                    )
                    continue # Success
                except Exception as e:
                    logging.error(f"Error recreating G2D selection '{name}': {e}")
                    # NEVER fall through to rectangular for suspected G2D
                    continue

            elif sel_type == "Region":
                sel_id = meta.get('selection_id') if meta else None
                recovered = next(
                    (
                        x for x in self._selections
                        if getattr(x, 'selection_id', None) == sel_id
                        and hasattr(x, 'roi')
                    ),
                    None,
                )
                if recovered is not None:
                    recovered.enabled = enabled
                    recovered.invert = invert
                    recovered.name = name
                    selections.append(recovered)
                else:
                    logging.warning(f"Region selection '{name}' has no stored region")
                continue

            elif sel_type == "Mask":
                try:
                    mask_found = False
                    meta_idx1 = int(meta.get('idx1', -1)) if meta else -1
                    meta_idx2 = int(meta.get('idx2', -1)) if meta else -1
                    sel_id = meta.get('selection_id') if meta else None
                    
                    # Recover the MaskDataSelection object from the internal list
                    for s in self._selections:
                        if isinstance(s, MaskDataSelection):
                            # 1. Try matching by selection_id
                            if sel_id and hasattr(s, 'selection_id') and s.selection_id == sel_id:
                                mask_found = True
                            
                            # 2. Fallback to indices and name matching
                            if not mask_found:
                                # If meta is missing, idx matching will use -1, so we rely on name or single-mask assumption
                                idx_match = (s.idx1 == meta_idx1 and s.idx2 == meta_idx2) or (meta is None)
                                # Compare against current table text 'name' and original 'meta_name'
                                name_match = (s.name == name or name.startswith(s.name) or s.name.startswith(name))
                                
                                if idx_match and (name_match or len([x for x in self._selections if isinstance(x, MaskDataSelection)]) == 1):
                                    mask_found = True
                            
                            if mask_found:
                                s.enabled = enabled
                                s.invert = invert
                                s.name = name # Keep in sync with UI
                                selections.append(s)
                                logging.debug(f"Recovered MaskDataSelection object for '{name}' (id={getattr(s, 'selection_id', 'None')[:8]})")
                                break
                    
                    if not mask_found:
                        available = [f"{x.name}(id={getattr(x, 'selection_id', 'None')[:8]}, idxs={x.idx1},{x.idx2})" for x in self._selections if isinstance(x, MaskDataSelection)]
                        logging.warning(f"MaskDataSelection object NOT FOUND for '{name}' (id={sel_id}, idxs={meta_idx1},{meta_idx2}). Available: {available}")
                    
                    continue # CRITICAL: never fall through to rectangular for Mask type
                except Exception as e:
                    logging.error(f"Error retrieving MaskDataSelection '{name}': {e}")
                    continue

            # Default rectangular selection
            selections.append(
                RectangularDataSelection(
                    parameter_idx=idx,
                    lower=lower,
                    upper=upper,
                    invert=invert,
                    enabled=enabled,
                    name=name
                )
            )
        
        logging.debug(f"get_selections: Returning {len(selections)} valid selection objects")
        return selections

    def onSelectionItemChanged(self, item: QtWidgets.QTableWidgetItem):
        """Allow inline editing of rectangular selection bounds and names.
        - Column 0: name (editable)
        - Column 1: lower bound (editable for rectangular selections)
        - Column 2: upper bound (editable for rectangular selections)
        Changing values triggers plot updates.
        """
        if getattr(self, "_block_selection_item_changed", False):
            return
        table = self.tableWidget
        row = item.row()
        col = item.column()
        
        # Guard against invalid row/col or missing items
        if row < 0 or col < 0:
            return
            
        # Get metadata from column 0 to check if this is a special selection type
        item0 = table.item(row, 0)
        if item0 is None:
            return
            
        name = item0.text()
        meta = None
        try:
            # Try multiple roles for metadata
            for role in [QtCore.Qt.UserRole, 32, QtCore.Qt.UserRole + 10]:
                meta_raw = item0.data(role)
                if meta_raw:
                    try:
                        if isinstance(meta_raw, dict):
                            meta = meta_raw
                        else:
                            meta = json.loads(str(meta_raw))
                        if meta and isinstance(meta, dict) and "type" in meta: 
                            break
                    except Exception:
                        continue
        except Exception:
            meta = None
        
        sel_type = meta.get("type") if isinstance(meta, dict) else None
        
        # Fallback identification based on name if metadata missing
        if sel_type is None:
            if name.startswith("Mask") or "Bitmap" in name:
                sel_type = "Mask"
            elif name.startswith("G2D"):
                sel_type = "G2D"
                
        is_special = sel_type in ("G2D", "Mask")

        # Name edits: trigger update only
        if col == 0:
            # Preserve contrast during selection operations
            self.parent._preserve_contrast = True
            self.parent.update_plots()
            self.parent._preserve_contrast = False
            return

        # Only columns 1 and 2 are numeric bounds for rectangular selections
        if col not in (1, 2):
            return
            
        if is_special:
            # Revert to stored value or placeholder if accidentally made editable
            try:
                self._block_selection_item_changed = True
                if sel_type == "Mask":
                    item.setText("Bitmap")
                    item.setData(0, None) # Clear any accidental numeric data
                elif sel_type == "G2D":
                    # For G2D, we typically show 0.0 as placeholder
                    val_data = item.data(0)
                    try:
                        val = float(val_data) if val_data is not None else 0.0
                        item.setText(str(val))
                    except (ValueError, TypeError):
                        item.setText("0.0")
                else:
                    item.setText(str(item.data(0) or "---"))
            finally:
                self._block_selection_item_changed = False
            return

        # Parse the edited text as float for normal rectangular selections
        txt = item.text().strip()
        try:
            val = float(txt)
        except Exception:
            # Revert to previous value stored in data role 0
            try:
                self._block_selection_item_changed = True
                prev_data = item.data(0)
                if prev_data is not None:
                    try:
                        prev = float(prev_data)
                        item.setText(str(prev))
                    except (ValueError, TypeError):
                        item.setText(str(prev_data))
                else:
                    item.setText("0.0")
            finally:
                self._block_selection_item_changed = False
            return

        # Commit the numeric value
        try:
            self._block_selection_item_changed = True
            item.setData(0, float(val))
            # Enforce ordering lower <= upper by adjusting the sibling cell
            lower_item = table.item(row, 1)
            upper_item = table.item(row, 2)
            try:
                lower = float(lower_item.data(0)) if lower_item is not None else float("nan")
            except Exception:
                lower = float("nan")
            try:
                upper = float(upper_item.data(0)) if upper_item is not None else float("nan")
            except Exception:
                upper = float("nan")

            if col == 1 and not math.isnan(upper) and val > upper:
                upper_item.setData(0, float(val))
                upper_item.setText(str(float(val)))
            elif col == 2 and not math.isnan(lower) and val < lower:
                lower_item.setData(0, float(val))
                lower_item.setText(str(float(val)))
        finally:
            self._block_selection_item_changed = False

        # Trigger plot update (only when data is ready)
        if hasattr(self.parent, 'is_data_ready') and not self.parent.is_data_ready():
            # If data isn't ready, revert numeric edits and skip replot
            if col in (1, 2):
                try:
                    self._block_selection_item_changed = True
                    prev = float(item.data(0)) if item.data(0) is not None else 0.0
                    item.setText(str(prev))
                finally:
                    self._block_selection_item_changed = False
                logging.info("Selection edit ignored: load data before editing selections.")
            # For name edits (col 0), accept but skip replot
            return
        # Preserve contrast during selection operations
        self.parent._preserve_contrast = True
        self.parent.update_plots()
        self.parent._preserve_contrast = False

    def onDeleteSelectionRows(self):
        """Delete selected selection rows using the Delete key."""
        table = self.tableWidget
        sel_model = table.selectionModel()
        if sel_model is None:
            return
        rows = sorted({idx.row() for idx in sel_model.selectedIndexes()}, reverse=True)
        if not rows:
            return
        for r in rows:
            if 0 <= r < table.rowCount():
                table.removeRow(r)
        # Invalidate cached histograms so the redraw reflects the removed selection.
        # Preserve contrast during selection operations
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
        Only allow editing of rectangular selection fields:
        - Column 0 (name) editable
        - Columns 1 and 2 (lower/upper) editable
        - For Gaussian2D rows, columns 1 and 2 are not editable.
        """
        index = getattr(self, "_pending_edit_index", None)
        self._pending_edit_index = None
        if index is None or not index.isValid():
            return
        row = index.row()
        col = index.column()

        # Determine if this row is G2D
        item0 = self.tableWidget.item(row, 0)
        meta = None
        try:
            meta_raw = item0.data(32)
            if meta_raw:
                meta = json.loads(meta_raw)
        except Exception:
            meta = None
        is_g2d = isinstance(meta, dict) and meta.get("type") == "G2D"

        # Permissions: name (col 0) always allowed for rectangular; G2D name not editable per flags
        if col == 0:
            # Try to edit if the item is editable by flags
            it = self.tableWidget.item(row, col)
            if it is not None and (it.flags() & QtCore.Qt.ItemIsEditable):
                self.tableWidget.edit(index)
            return

        # Bounds columns 1 and 2: only for rectangular selections
        if col in (1, 2) and not is_g2d:
            it = self.tableWidget.item(row, col)
            if it is not None and (it.flags() & QtCore.Qt.ItemIsEditable):
                self.tableWidget.edit(index)
            return
        # Otherwise, do nothing (non-editable)
        return

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
            parent=self,
        )
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
        default_fps = 10
        try:
            settings_path = pathlib.Path(__file__).parent.parent / 'settings' / 'mfd.settings.json'
            if not settings_path.exists():
                return default_fps
            with open(settings_path, 'r') as f:
                settings = json.load(f)
            playback = settings.get('playback', {})
            if 'fps' in playback:
                return max(1, int(playback['fps']))
            # The rate used to be written as a frame duration. Reading both
            # keeps a settings file from before this change working, and there
            # is no migration to run.
            duration = playback.get('frame_duration_ms')
            if duration:
                return max(1, int(round(1000.0 / float(duration))))
        except Exception as exc:
            logging.warning("Failed to read playback settings: %s", exc)
        return default_fps

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
