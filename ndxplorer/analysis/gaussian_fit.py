"""
Gaussian fitting UI attachment and logic for ndxplorer.

This module encapsulates the construction of the Gaussian Fit controls and
attaches them to the main NDXplorer window, keeping plot_main.py cleaner.
It wires all Gaussian-related signal handlers here and implements the logic
(fitting, overlays, table I/O, marginals, and Delete-key row removal).

The Gaussians themselves are **fitting parameters**, not table text: they live
in a :class:`FittingParameterGroup` (:mod:`ndxplorer.core.gaussian_parameters`)
rendered by chisurf's paired parameter table, one component per row. So a
Gaussian's centre or width can be crosslinked to a parameter of an actual fit —
or to another Gaussian — and "hold this one" is the same *fixed* flag every
other parameter in chisurf has, rather than a checkbox in the corner of a cell.
"""
from __future__ import annotations

from ..logging_config import logging
from typing import Any, Dict, Optional, Tuple, List

import os

import numpy as np
from qtpy import QtCore, QtWidgets

from ..core import gaussian_parameters as gp
from . import gaussian_mixture as gm
from ..ui.glyphs import Glyphs, label as glyph_label

#: Layer of the shared 2-D overlay the Gaussian ellipses own. The equation
#: overlays and the server line sets share that surface, so clearing is per
#: layer -- an unqualified clear on either side wipes the others.
GAUSSIAN_LAYER = "gaussian"

#: Registry owner id under which the Gaussians are published, so another
#: parameter table can link *to* a population's centre or width.
GAUSSIAN_OWNER_ID = "ndxplorer.gaussians"

#: How many table rows the panel asks room for — one Gaussian's six parameters.
#: The dock has a fixed height, so a table sized to *all* its rows would push
#: the ones past it off the bottom; past this many it scrolls, and a taller dock
#: shows more.
MIN_VISIBLE_ROWS = 6


class GaussianFit(QtCore.QObject):
    """
    Helper that constructs and wires the Gaussian Fit UI into the provided
    main window (NDXplorer instance). It creates the widgets directly in
    verticalLayout_18 as requested and owns all Gaussian-related logic.

    UI elements are stored on `main` for consistency with existing code.
    Plot/marginal state lists (gaussian_items, etc.) and palette are also
    initialized on `main` to minimize changes elsewhere.
    """

    #: Emitted on the GUI thread when a Gaussian moved because something
    #: *outside* this panel moved -- a fit stepping a parameter one of them is
    #: crosslinked to. Marshalled through a queued signal because the fit
    #: client's callbacks arrive on an RPC thread.
    _externalEvent = QtCore.Signal()

    @property
    def is_log_x(self) -> bool:
        """True if current x-axis is in log scale.
        Uses main.plot_control.scale_x if available; defaults to False on error."""
        try:
            m = self.main
            return str(m.plot_control.scale_x).lower() == "log"
        except Exception:
            return False

    @property
    def is_log_y(self) -> bool:
        """True if current y-axis is in log scale.
        Uses main.plot_control.scale_y if available; defaults to False on error."""
        try:
            m = self.main
            return str(m.plot_control.scale_y).lower() == "log"
        except Exception:
            return False

    @property
    def fit_in_log(self):
        try:
            m = self.main
            fit_in_log = bool(m.checkBoxGaussFitLog.isChecked())
        except Exception:
            fit_in_log = False
        return fit_in_log

    @property
    def log_axes(self) -> (bool, bool):
        # Determine log fitting mode from the UI checkbox (overrides axis scales)
        return np.array([self.is_log_x, self.is_log_y], dtype=bool)

    def __init__(self, main: QtWidgets.QMainWindow):
        super().__init__(main)
        self.main = main
        #: The Gaussians, as fitting parameters (six per component).
        self.group = gp.build_gaussian_group()
        self._table = None
        self._registered = False
        self._reg_cb = None
        self._fc_cb = None
        self._externalEvent.connect(self._on_external_gui, QtCore.Qt.QueuedConnection)
        self._build_ui()
        self._connect_signals()
        self._register_group()
        self._subscribe_external()

    # ------------------------------ UI ---------------------------------
    def _build_ui(self):
        m = self.main
        # Button row: Fit + Clear + Select + Selection σ + Settings
        btn_row = QtWidgets.QHBoxLayout()
        m.btnFit2DGauss = QtWidgets.QToolButton(m); m.btnFit2DGauss.setText(glyph_label(Glyphs.TARGET, "Fit"))
        m.btnClearGaussians = QtWidgets.QToolButton(m); m.btnClearGaussians.setText(glyph_label(Glyphs.CLEAR, "Clear"))
        m.btnSelectGaussian = QtWidgets.QToolButton(m); m.btnSelectGaussian.setText(glyph_label(Glyphs.SEARCH, "Select"))
        # Selection height (number of sigmas) next to Select button
        lblSigma = QtWidgets.QLabel("Selection σ:", m)
        m.spinSelectionSigma = QtWidgets.QDoubleSpinBox(m)
        m.spinSelectionSigma.setRange(0.1, 4.0)
        m.spinSelectionSigma.setSingleStep(0.2)
        m.spinSelectionSigma.setDecimals(2)
        m.spinSelectionSigma.setValue(1.0)
        m.spinSelectionSigma.setToolTip("Number of sigmas used for Gaussian burst selection (1.0 = 1σ).")
        m.btnSelectPoint = QtWidgets.QCheckBox("Select point", m)
        m.checkBoxShowMarginals = QtWidgets.QCheckBox("Marginals", m)
        m.checkBoxShowMarginals.setChecked(True)
        # New: toggle to choose fitting in log-space vs normal
        m.checkBoxGaussFitLog = QtWidgets.QCheckBox("Log Gauss", m)
        m.checkBoxGaussFitLog.setChecked(False)
        m.checkBoxGaussFitLog.setToolTip("Log Gauss: when enabled, fit Gaussians in log scale (both X and Y; positive values only). When disabled, fit in linear scale.")
        # New: GMM Settings button
        m.btnGMMSettings = QtWidgets.QToolButton(m); m.btnGMMSettings.setText(glyph_label(Glyphs.SETTINGS, "Settings"))
        m.btnGMMSettings.setToolTip("Configure built-in GMM (EM) parameters and save them to your user settings.")
        btn_row.addWidget(m.btnFit2DGauss)
        btn_row.addWidget(m.btnClearGaussians)
        btn_row.addWidget(m.btnSelectGaussian)
        btn_row.addWidget(lblSigma)
        btn_row.addWidget(m.spinSelectionSigma)
        btn_row.addWidget(m.btnGMMSettings)
        # Place the button row directly into the target layout
        m.verticalLayout_18.addLayout(btn_row)

        # The Gaussians themselves. They are a parameter group with append/pop,
        # so the panel does not build a table: chisurf's ``dynamic_group``
        # section renders it -- the same component table, add/remove buttons and
        # columns a model editor uses for lifetimes and rotations.
        self.form = self._build_form()
        m.verticalLayout_18.addWidget(self.form)

        # Options row placed below the table: checkboxes + Save/Load
        options_row = QtWidgets.QHBoxLayout()
        options_row.addWidget(m.btnSelectPoint)
        options_row.addWidget(m.checkBoxShowMarginals)
        options_row.addWidget(m.checkBoxGaussFitLog)
        # Save/Load in same row as checkboxes
        m.btnSaveGaussians = QtWidgets.QToolButton(m); m.btnSaveGaussians.setText(glyph_label(Glyphs.SAVE, "Save"))
        m.btnLoadGaussians = QtWidgets.QToolButton(m); m.btnLoadGaussians.setText(glyph_label(Glyphs.OPEN, "Load"))
        options_row.addWidget(m.btnSaveGaussians)
        options_row.addWidget(m.btnLoadGaussians)
        options_row.addStretch(1)
        m.verticalLayout_18.addLayout(options_row)

        # Guard flag to avoid recursive redraws during programmatic updates
        m._updating_gaussian_table = False

        # Storage for gaussian overlay items and color cycle
        m.gaussian_items = []
        # Stable palette and legacy cycle (kept for compatibility)
        m._gaussian_palette = ["#ff0000", "#00aa00", "#0000ff", "#aa00aa", "#00aaaa", "#ffaa00"]
        m._gaussian_color_cycle = iter(m._gaussian_palette)
        # Storage for marginal overlay curve items
        m.gaussian_marginal_items_x = []
        m.gaussian_marginal_items_y = []

    def _default_component(self):
        """Where a Gaussian added from the table's "add" button starts.

        The middle of the displayed map, a tenth of it wide — a component added
        with no coordinates has to land somewhere the user can see it, and the
        panel is what knows where the axes currently are.
        """
        H, x_edges, y_edges = self.main._histogram["2d"]
        x0, x1 = float(x_edges[0]), float(x_edges[-1])
        y0, y1 = float(y_edges[0]), float(y_edges[-1])
        mu = ((x0 + x1) / 2.0, (y0 + y1) / 2.0)
        cov = np.diag([((x1 - x0) / 10.0) ** 2, ((y1 - y0) / 10.0) ** 2])
        return mu, cov

    def _build_form(self) -> QtWidgets.QWidget:
        """Render the mixture through AutoForm's ``dynamic_group`` section."""
        from chisurf.gui.autoform.auto_form import AutoForm

        self.group.default_component = self._default_component
        self.view = gp.GaussianMixtureView(self.group, on_changed=self._on_parameters_edited)
        form = AutoForm(self.view, parent=self.main)
        self._table = self._find_table(form)
        if self._table is not None:
            # The dock has a fixed height, so a table that grows with its
            # content would drop the last Gaussians off the bottom of it.
            self._table.set_scrollable(MIN_VISIBLE_ROWS)
            view = self._table.table_view
            # A row is a Gaussian: selecting one highlights its ellipse, "del"
            # removes that one, and so does the Delete key.
            view.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
            view.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
            view.installEventFilter(self)
            selection = view.selectionModel()
            if selection is not None:
                selection.selectionChanged.connect(self.on_gaussian_table_selection_changed)
        return form

    @staticmethod
    def _find_table(form):
        """Return the parameter table AutoForm built for the section.

        Either layout the section can be given — one row per parameter or one
        per component — is a table with the same public surface, so the panel
        asks for whichever is there rather than for a particular class.
        """
        from chisurf.gui.autoform.sections.parameter_table import (
            PairedParameterTableWidget,
            ParameterGroupTableWidget,
        )

        for widget in form.findChildren(QtWidgets.QWidget):
            if isinstance(widget, (ParameterGroupTableWidget, PairedParameterTableWidget)):
                return widget
        return None

    def _rebuild_table_rows(self) -> None:
        """Show the group's current components (after an add / remove / load).

        The section's own add/remove buttons do this for themselves; this is for
        the panel's other routes into the group -- a click on the map, a loaded
        file, "Clear".
        """
        if self._table is not None:
            self._table.set_params(self.group.rows())
        self._register_group()

    def _register_group(self) -> None:
        """Publish the Gaussians so another parameter table can link to them."""
        try:
            from chisurf.core.parameter_group_registry import register_parameter_group

            register_parameter_group(
                self.group, owner_id=GAUSSIAN_OWNER_ID, label="ndX Gaussians"
            )
            self._registered = True
        except Exception as exc:
            logging.debug("Could not register Gaussian parameter group: %s", exc)

    def _unregister_group(self) -> None:
        """Drop the registry entry, and with it any link into these parameters."""
        if not self._registered:
            return
        try:
            from chisurf.core.parameter_group_registry import unregister_parameter_group

            unregister_parameter_group(GAUSSIAN_OWNER_ID)
        except Exception:
            pass
        self._registered = False

    # -- links from outside -------------------------------------------------
    def _subscribe_external(self) -> None:
        """Redraw when a fit moves a parameter a Gaussian is crosslinked to.

        Without this a link is only half-live: the value is right the next time
        something happens to redraw, and the ellipse on screen is stale until
        then.
        """
        try:
            from chisurf.core import parameter_group_registry as reg

            reg.subscribe(self._on_external_event)
            self._reg_cb = self._on_external_event
        except Exception:
            self._reg_cb = None
        try:
            from chisurf.gui.widgets.fitting.fitting_client import get_fitting_client

            client = get_fitting_client()
            if client is not None:
                cb = lambda *a, **k: self._on_external_event()  # noqa: E731
                client.subscribe("parameter.", cb)
                client.subscribe("fit.", cb)
                self._fc_cb = (client, cb)
        except Exception:
            self._fc_cb = None

    def _unsubscribe_external(self) -> None:
        try:
            if self._reg_cb is not None:
                from chisurf.core import parameter_group_registry as reg

                reg.unsubscribe(self._reg_cb)
        except Exception:
            pass
        try:
            if self._fc_cb is not None:
                client, cb = self._fc_cb
                client.unsubscribe("parameter.", cb)
                client.unsubscribe("fit.", cb)
        except Exception:
            pass
        self._reg_cb = self._fc_cb = None

    def _on_external_event(self, *args, **kwargs) -> None:
        # May arrive on an RPC thread; hop to the GUI thread before touching
        # widgets.
        try:
            self._externalEvent.emit()
        except Exception:
            pass

    def _on_external_gui(self) -> None:
        if self._table is not None:
            try:
                self._table.sync()
            except Exception:
                pass
        self._redraw_gaussian_overlays_from_table()

    def _on_parameters_edited(self) -> None:
        """A cell was edited: redraw the ellipses from the parameters."""
        if getattr(self.main, "_updating_gaussian_table", False):
            return
        self._redraw_gaussian_overlays_from_table()

    def _connect_signals(self):
        m = self.main
        # Wire actions to handlers in this class
        m.btnFit2DGauss.clicked.connect(self.on_fit_2d_gaussian)
        m.btnSelectPoint.toggled.connect(self.on_select_point_toggled)
        m.btnClearGaussians.clicked.connect(self.on_clear_gaussians)
        m.btnSelectGaussian.clicked.connect(self.on_select_gaussian)
        # Open GMM settings dialog
        try:
            m.btnGMMSettings.clicked.connect(self.on_open_gmm_settings)
        except Exception:
            pass
        # Marginals toggle
        m.checkBoxShowMarginals.toggled.connect(self.on_toggle_gaussian_marginals)
        # Save/Load buttons
        m.btnSaveGaussians.clicked.connect(self.on_save_gaussians)
        m.btnLoadGaussians.clicked.connect(self.on_load_gaussians)

    # ---------------------------- Handlers ------------------------------
    def selected_component_rows(self) -> List[int]:
        """Indices of the selected Gaussians (empty when nothing is picked).

        The table shows one *parameter* per row, so a selected row names the
        Gaussian it belongs to — six rows at a time.
        """
        if self._table is None:
            return []
        selection = self._table.table_view.selectionModel()
        if selection is None:
            return []
        return sorted({index.row() // gp.WIDTH for index in selection.selectedIndexes()})

    def on_gaussian_table_selection_changed(self, selected=None, deselected=None):
        """Highlight selected Gaussian overlays by increasing line width."""
        m = self.main
        items = getattr(m, 'gaussian_items', [])
        if not items:
            return
        sel = set(self.selected_component_rows())

        # Update line widths
        for i, it in enumerate(items):
            # Skip tuple placeholders from simple backend - they don't have pen() method
            if isinstance(it, tuple):
                continue
            pen = it.pen()
            pen.setWidth(8 if i in sel else 2)
            it.setPen(pen)
        m.overlay_plot.replot()

    def on_select_gaussian(self):
        """Add a Gaussian 2D selection (1σ) for the selected Gaussian rows.
        The selection is created for the currently selected X/Y parameters
        and labeled as G2D(ParamX, ParamY).
        """
        m = self.main
        components = self.group.components()
        if not components:
            return
        # Determine current X/Y parameter indices and names
        try:
            idx1, name1 = m.plot_control.p1
            idx2, name2 = m.plot_control.p2
        except Exception:
            QtWidgets.QMessageBox.warning(m, "No Parameters", "Could not determine current X/Y parameters.")
            return
        label = f"G2D({name1}, {name2})"
        # Determine axis log state for selection parameters
        is_log_x = self.is_log_x
        is_log_y = self.is_log_y
        # Collect selected rows; if none selected, use all rows if exactly one exists
        selected = self.selected_component_rows()
        if not selected:
            if len(components) == 1:
                selected = [0]
            else:
                QtWidgets.QMessageBox.information(m, "Select Gaussian", "Please select one or more Gaussian rows in the table.")
                return
        try:
            sigma_val = float(m.spinSelectionSigma.value())
        except Exception:
            sigma_val = 1.0
        if not np.isfinite(sigma_val) or sigma_val <= 0:
            sigma_val = 1.0
        for r in selected:
            if r < 0 or r >= len(components):
                continue
            component = components[r]
            mu_v, cov_v = component.mu, component.cov
            # Transform to log space for axes that are log so that the selection
            # matches the displayed Gaussian
            mu_s, cov_s = mu_v.copy(), cov_v.copy()
            if is_log_x or is_log_y:
                mu_s, cov_s = gm.to_fit_space(mu_v, cov_v, is_log_x, is_log_y)
            try:
                m.plot_control.addGaussianSelection(
                    idx1, idx2, mu_s, cov_s, sigma=sigma_val, invert=False,
                    enabled=True, name=label, log_x=is_log_x, log_y=is_log_y,
                )
            except Exception:
                QtWidgets.QMessageBox.warning(m, "Selection Error", "Could not add Gaussian selection to the selection table.")
                return

    def on_open_gmm_settings(self):
        """Open the GMM settings dialog and refresh cached settings if accepted."""
        from ..ui.gaussian_settings_dialog import GaussianSettingsDialog

        dlg = GaussianSettingsDialog(parent=self.main)
        if dlg.exec_():
            # Reload settings into cache and refresh UI elements relying on settings
            try:
                cfg = gm.load_gmm_settings()
                self._gmm_settings = cfg
                m = self.main
                if hasattr(m, 'spinLocalWindow') and m.spinLocalWindow is not None:
                    lw = int(cfg.get("local_window_bins", 10))
                    lw = max(1, min(lw, 200))
                    try:
                        m.spinLocalWindow.blockSignals(True)
                        m.spinLocalWindow.setValue(lw)
                    finally:
                        m.spinLocalWindow.blockSignals(False)
            except Exception:
                pass

    def _get_gmm_settings(self):
        """Load or return cached GMM settings dict."""
        if not hasattr(self, "_gmm_settings") or not isinstance(self._gmm_settings, dict):
            self._gmm_settings = gm.load_gmm_settings()
        return dict(self._gmm_settings)

    def on_fit_2d_gaussian(self):
        """
        Optimize the parameters (means, covariances, weights) of the Gaussians listed
        in the table directly against the currently selected raw data points
        (not the histogram) using a Gaussian Mixture fit.

        A parameter the table holds — *fixed*, or **crosslinked** to another
        parameter, whose value belongs to its master — is kept where it is and
        is not written back.
        """
        m = self.main
        rows_full = self.group.components()
        try:
            H, x_edges, y_edges = m._histogram["2d"]
        except Exception:
            QtWidgets.QMessageBox.warning(m, "No histogram", "No 2D histogram available. Fit is restricted to visible data; please update histogram first.")
            return
        try:
            fitted = gm.fit_mixture(
                rows_full, m.x_values, m.y_values,
                (float(x_edges[0]), float(x_edges[-1])), (float(y_edges[0]), float(y_edges[-1])),
                log_x=bool(self.is_log_x), log_y=bool(self.is_log_y),
                settings=self._get_gmm_settings(),
            )
        except gm.GaussianFitError as exc:
            QtWidgets.QMessageBox.warning(m, exc.title, exc.text)
            return
        for i, (mu_v, cov_v, weight) in enumerate(fitted):
            self._update_gaussian_row(i, mu_v, cov_v, weight)
        self._redraw_gaussian_overlays_from_table()

    def on_select_point_toggled(self, checked: bool):
        """Toggle point selection mode for clicking on the histogram."""
        m = self.main
        if hasattr(m, 'mouse_event_filter') and m.mouse_event_filter is not None:
            m.mouse_event_filter.set_point_mode(checked, callback=self.on_point_selected if checked else None)

    def on_point_selected(self, pos):
        """Handle a point click on the overlay canvas; compute a local Gaussian around the clicked bin.
        Also append it to the Gaussians table.
        """
        m = self.main
        try:
            H, x_edges, y_edges = m._histogram["2d"]
        except Exception:
            return
        if H is None or H.size == 0:
            return
        # Convert canvas position to normalized coordinates [0,1]
        canvas = m.overlay_plot.canvas()
        w = max(1, canvas.width())
        h = max(1, canvas.height())
        x_norm = pos.x() / w
        y_norm = 1.0 - (pos.y() / h)  # invert Y
        # Clamp
        x_norm = max(0.0, min(1.0, x_norm))
        y_norm = max(0.0, min(1.0, y_norm))
        # Convert to bin indices
        ix = int(x_norm * (len(x_edges) - 1))
        iy = int(y_norm * (len(y_edges) - 1))
        # The centre is the clicked bin's, the width the histogram's local spread.
        try:
            window_size = int(m.spinLocalWindow.value())
        except Exception:
            window_size = int(self._get_gmm_settings().get("local_window_bins", 10))
        seeded = gm.seed_component(H, x_edges, y_edges, m.bin_to_x_value(ix, x_edges),
                                   m.bin_to_y_value(iy, y_edges), window_size)
        if seeded is None:
            return
        mu, cov = seeded
        # Append to table first to get stable row index, honoring default fix flags
        try:
            cfg = self._get_gmm_settings()
            fix_new = bool(cfg.get("fix_new_means", True))
        except Exception:
            fix_new = True
        row_index = self._append_gaussian_row(mu, cov, fix_x=fix_new, fix_y=fix_new)
        # Determine stable color by row index
        try:
            palette = getattr(m, '_gaussian_palette', ["#ff0000", "#00aa00", "#0000ff", "#aa00aa", "#00aaaa", "#ffaa00"])
            color = palette[row_index % len(palette)] if row_index >= 0 and len(palette) else None
        except Exception:
            color = None
        # Draw overlay with stable color
        self._add_gaussian_overlay(mu, cov, label=f"({mu[0]:.3g},{mu[1]:.3g})", color=color)
        # If marginals are enabled, redraw overlays and marginals immediately
        try:
            if hasattr(m, 'checkBoxShowMarginals') and m.checkBoxShowMarginals.isChecked():
                self._redraw_gaussian_overlays_from_table()
        except Exception:
            pass

    def on_clear_gaussians(self):
        """Remove all Gaussian overlays and clear the table and marginals."""
        m = self.main
        
        # Handle simple backend (DrawingOverlayWidget); the ellipses only, the
        # equation curves on the same surface are not ours to remove.
        try:
            m.overlay_plot.clear_curves(GAUSSIAN_LAYER)
        except Exception:
            pass
        
        # Clear marginal items too
        try:
            self._clear_gaussian_marginal_items()
        except Exception:
            pass
        try:
            m._updating_gaussian_table = True
            self.group.clear()
            self._rebuild_table_rows()
        finally:
            m._updating_gaussian_table = False

        # Update display
        try:
            if hasattr(m, '_use_simple_backend') and m._use_simple_backend:
                m.overlay_plot.update()
            else:
                m.overlay_plot.replot()
        except Exception:
            pass

    # ---------------------------- Helpers -------------------------------
    def _add_gaussian_overlay(self, mu: Tuple[float, float], cov: np.ndarray, label: str = "", color: Optional[str] = None):
        self._add_gaussian_overlay_simple(mu, cov, label, color)

    def _add_gaussian_overlay_simple(self, mu: Tuple[float, float], cov: np.ndarray, label: str = "", color: Optional[str] = None):
        """Add Gaussian ellipse overlay for simple backend using DrawingOverlayWidget."""
        m = self.main
        try:
            from qtpy.QtGui import QColor
        except Exception:
            return
        
        # Get histogram data for coordinate conversion
        try:
            H, x_edges, y_edges = m._histogram["2d"]
        except Exception:
            return
        
        # Detect log axes
        is_log_x = self.is_log_x
        is_log_y = self.is_log_y
        
        for sigma_idx, sigma_level in enumerate(gm.SIGMA_LEVELS):
            xs_v, ys_v = gm.ellipse((float(mu[0]), float(mu[1])), cov, sigma_level,
                                    is_log_x, is_log_y)

            # Convert value-space coordinates to bin/pixel coordinates
            x_coords = []
            y_coords = []
            for xv, yv in zip(xs_v, ys_v):
                xb = m.value_to_bin(xv, x_edges)
                yb = m.value_to_bin(yv, y_edges)
                if xb is None or yb is None:
                    continue
                x_coords.append(xb)
                y_coords.append(yb)
            if not x_coords:
                continue

            # Determine color (only once for the first sigma level)
            if sigma_idx == 0:
                if color is None:
                    try:
                        color = next(m._gaussian_color_cycle)
                    except Exception:
                        palette = getattr(m, '_gaussian_palette', ["#ff0000", "#00aa00", "#0000ff", "#aa00aa", "#00aaaa", "#ffaa00"])
                        m._gaussian_color_cycle = iter(palette)
                        color = next(m._gaussian_color_cycle)
                # If collecting colors for marginals, store this color in order
                try:
                    if getattr(m, '_collect_gaussian_colors', False):
                        if not hasattr(m, '_last_gaussian_draw_colors'):
                            m._last_gaussian_draw_colors = []
                        m._last_gaussian_draw_colors.append(color)
                except Exception:
                    pass

            # Convert color string to QColor
            if isinstance(color, str):
                qcolor = QColor(color)
            else:
                qcolor = color

            # Make 1σ thickest, 2σ medium, 3σ thinnest
            line_width = int(4.0 - sigma_idx)  # 4, 3, 2 for 1σ, 2σ, 3σ
            line_width = max(1, line_width)

            # Add curve to overlay widget
            try:
                m.overlay_plot.add_curve(
                    np.array(x_coords), np.array(y_coords),
                    color=qcolor, width=line_width, layer=GAUSSIAN_LAYER,
                )
                if not hasattr(m, 'gaussian_items'):
                    m.gaussian_items = []
                m.gaussian_items.append(('curve', len(x_coords), len(y_coords)))
            except Exception:
                pass
        
        # Trigger overlay update
        try:
            m.overlay_plot.update()
        except Exception:
            pass

    def _append_gaussian_row(self, mu, cov, w: float = 1.0,
                             fix_x=False, fix_y=False, fix_cxx=False, fix_cxy=False, fix_cyy=False):
        """Add one Gaussian and show it as a new row of the parameter table.

        Parameters
        ----------
        mu : sequence of float
            Centre ``(x, y)`` in value space.
        cov : array_like, shape (2, 2)
            Covariance; stored as ``sd_x``, ``sd_y`` and ``rho``.
        w : float, optional
            Mixture weight.
        fix_x, fix_y, fix_cxx, fix_cxy, fix_cyy : bool, optional
            Which of the component's parameters start held. ``cxx``/``cyy`` are
            the widths and ``cxy`` the correlation, named for the covariance
            elements they came from.

        Returns
        -------
        int
            The new component's row index.
        """
        m = self.main
        try:
            m._updating_gaussian_table = True
            row = self.group.append(
                mu, cov, w,
                fixed={
                    "x": bool(fix_x), "y": bool(fix_y),
                    "sd_x": bool(fix_cxx), "sd_y": bool(fix_cyy), "rho": bool(fix_cxy),
                },
            )
            self._rebuild_table_rows()
            return row
        finally:
            m._updating_gaussian_table = False

    def _update_gaussian_row(self, row: int, mu: np.ndarray, cov: np.ndarray, w: float = None):
        """Write a fitted component back into its parameters (skipping links)."""
        m = self.main
        try:
            m._updating_gaussian_table = True
            self.group.write(row, mu, cov, w)
        except IndexError:
            return
        finally:
            m._updating_gaussian_table = False
        if self._table is not None:
            try:
                self._table.sync()
            except Exception:
                pass

    def _read_gaussian_table(self) -> List[Tuple[np.ndarray, np.ndarray, float]]:
        """Return ``(mu, cov, w)`` for every Gaussian, following crosslinks."""
        return [(c.mu, c.cov, c.w) for c in self.group.components()]

    def _redraw_gaussian_overlays_from_table(self):
        """Clear and redraw Gaussian overlays from the current table rows."""
        m = self.main
        try:
            m.overlay_plot.clear_curves(GAUSSIAN_LAYER)
        except Exception:
            pass
        # Also clear marginals prior to redraw
        try:
            self._clear_gaussian_marginal_items()
        except Exception:
            pass
        # Draw again
        try:
            H, x_edges, y_edges = m._histogram["2d"]
        except Exception:
            return
        rows = self._read_gaussian_table()
        # Collect overlay colors in the same order with stable mapping by row index
        m._last_gaussian_draw_colors = []
        m._collect_gaussian_colors = True
        palette = getattr(m, '_gaussian_palette', ["#ff0000", "#00aa00", "#0000ff", "#aa00aa", "#00aaaa", "#ffaa00"])
        for idx, (mu, cov, w) in enumerate(rows):
            color = palette[idx % len(palette)] if len(palette) else "#ff0000"
            self._add_gaussian_overlay((float(mu[0]), float(mu[1])), np.array(cov, dtype=float), color=color)
        m._collect_gaussian_colors = False
        # Re-apply selection highlighting after redraw
        try:
            self.on_gaussian_table_selection_changed(None, None)
        except Exception:
            pass
        # Draw marginals if toggled on
        try:
            if hasattr(m, 'checkBoxShowMarginals') and m.checkBoxShowMarginals.isChecked():
                self._draw_gaussian_marginals_from_table(rows, getattr(m, '_last_gaussian_draw_colors', None))
        except Exception:
            pass

        # A repaint, not a replot. This used to schedule a full ``update_plots``
        # a millisecond later, because the overlay froze its curves into pixels
        # at add time and needed a resize to pick the axes up; the overlay now
        # maps at paint time. That deferred update was also what made the
        # ellipses vanish a moment after appearing -- it redrew the equation
        # overlays, which cleared the whole shared surface.
        try:
            m.overlay_plot.replot()
        except Exception:
            pass

    def _clear_gaussian_marginal_items(self):
        m = self.main
        try:
            if hasattr(m, 'gaussian_marginal_items_x') and hasattr(m, 'g_xplot'):
                for item in m.gaussian_marginal_items_x:
                    try:
                        m.g_xplot.getPlotItem().removeItem(item)
                    except Exception:
                        pass
                m.gaussian_marginal_items_x.clear()
                m.g_xplot.replot()
        except Exception:
            pass
        try:
            if hasattr(m, 'gaussian_marginal_items_y') and hasattr(m, 'g_yplot'):
                for item in m.gaussian_marginal_items_y:
                    try:
                        m.g_yplot.getPlotItem().removeItem(item)
                    except Exception:
                        pass
                m.gaussian_marginal_items_y.clear()
                m.g_yplot.replot()
        except Exception:
            pass

    def _draw_gaussian_marginals_from_table(self, rows, colors=None):
        m = self.main
        self._clear_gaussian_marginal_items()
        try:
            x_edges, x_vals = m._histogram["x"]
            y_edges, y_vals = m._histogram["y"]
        except Exception:
            return
        norm_x = bool(getattr(m.plot_control, 'normed_hist_x', False)) if hasattr(m, 'plot_control') else False
        norm_y = bool(getattr(m.plot_control, 'normed_hist_y', False)) if hasattr(m, 'plot_control') else False
        if not hasattr(m, 'gaussian_marginal_items_x'):
            m.gaussian_marginal_items_x = []
        if not hasattr(m, 'gaussian_marginal_items_y'):
            m.gaussian_marginal_items_y = []
        curves = gm.component_marginals(rows, x_edges, x_vals, y_edges, y_vals,
                                        norm_x, norm_y, self.is_log_x, self.is_log_y)
        for idx, curve in enumerate(curves):
            if curve is None:
                continue
            xc, gx_plot, yc, gy_plot = curve
            color = colors[idx] if colors is not None and idx < len(colors) else \
                gm.PALETTE[idx % len(gm.PALETTE)]
            try:
                item_x = m.g_xplot.getPlotItem().plot(list(xc), list(gx_plot), pen=color)
                m.gaussian_marginal_items_x.append(item_x)
            except Exception:
                pass
            try:
                item_y = m.g_yplot.getPlotItem().plot(list(gy_plot), list(yc), pen=color)
                m.gaussian_marginal_items_y.append(item_y)
            except Exception:
                pass
        m.g_xplot.replot()
        m.g_yplot.replot()

    def on_toggle_gaussian_marginals(self, checked: bool):
        """Handle toggling of marginal plots visibility."""
        m = self.main
        try:
            if checked:
                rows = self._read_gaussian_table()
                self._draw_gaussian_marginals_from_table(rows, getattr(m, '_last_gaussian_draw_colors', None))
            else:
                self._clear_gaussian_marginal_items()
        except Exception:
            pass

    # ----------------------------- Save/Load -----------------------------
    def _rows_to_dicts(self) -> List[Dict[str, Any]]:
        """One flat record per Gaussian, in the saved file's column order."""
        return self.group.records()

    def _current_axes_info(self):
        """Return a dict with axis info: index, name, and scale (linear/log) for x and y.
        Falls back gracefully if plot_control does not provide expected attributes.
        """
        m = self.main
        try:
            idx1, name1 = m.plot_control.p1
        except Exception:
            idx1, name1 = None, None
        try:
            idx2, name2 = m.plot_control.p2
        except Exception:
            idx2, name2 = None, None
        scale_x = "log" if self.is_log_x else "linear"
        scale_y = "log" if self.is_log_y else "linear"
        return {
            "x": {"index": idx1, "name": name1, "scale": scale_x},
            "y": {"index": idx2, "name": name2, "scale": scale_y},
            "fit_in_log": bool(getattr(self, "fit_in_log", False)),
        }

    def on_save_gaussians(self):
        m = self.main
        rows = self._rows_to_dicts()
        if not rows:
            QtWidgets.QMessageBox.information(m, "Save Gaussians", "There are no Gaussian rows to save.")
            return
        base_path, _ = QtWidgets.QFileDialog.getSaveFileName(m, "Save Gaussian Fits", os.path.expanduser("~"), "Gaussian Files (*.json *.csv);;All Files (*.*)")
        if not base_path:
            return
        try:
            H, x_edges, y_edges = m._histogram["2d"]
        except Exception:
            H = x_edges = y_edges = None
        try:
            written = gm.save_gaussians(base_path, rows, self._read_gaussian_table(),
                                        self._current_axes_info(), H, x_edges, y_edges,
                                        self.is_log_x, self.is_log_y)
        except OSError as e:
            QtWidgets.QMessageBox.critical(m, "Save Error", f"Failed to save:\n{e}")
            return
        QtWidgets.QMessageBox.information(
            m, "Saved", "Saved files:\n" + "\n".join(os.path.basename(p) for p in written))

    def on_load_gaussians(self):
        m = self.main
        start_dir = os.path.expanduser("~")
        path, _ = QtWidgets.QFileDialog.getOpenFileName(m, "Load Gaussian Fits", start_dir, "Gaussian Files (*.json *.csv);;All Files (*.*)")
        if not path:
            return
        try:
            rows, axes_meta = gm.load_gaussians(path)
        except Exception as e:
            QtWidgets.QMessageBox.critical(m, "Load Error", f"Failed to load file:\n{e}")
            return
        if not rows:
            QtWidgets.QMessageBox.warning(m, "Load Gaussians", "No valid Gaussian rows found in the selected file.")
            return
        mismatch = gm.axis_mismatch(axes_meta, self._current_axes_info())
        if mismatch:
            QtWidgets.QMessageBox.information(m, "Axis Mismatch", mismatch)

        # Clear existing and populate
        try:
            m._updating_gaussian_table = True
            self.group.clear()
            for mu, cov, w, fx, fy, fcx, fcy, fcyy in rows:
                self.group.append(
                    (float(mu[0]), float(mu[1])),
                    np.array(cov, dtype=float),
                    float(w),
                    fixed={"x": fx, "y": fy, "sd_x": fcx, "rho": fcy, "sd_y": fcyy},
                )
            self._rebuild_table_rows()
        finally:
            m._updating_gaussian_table = False

        # Redraw overlays from the table
        try:
            self._redraw_gaussian_overlays_from_table()
        except Exception:
            pass

    # ------------------------- Event filtering ---------------------------
    def eventFilter(self, obj, event):
        """Intercept Delete key presses on the Gaussians table to delete selected rows.

        The section's own "del" button removes the selected component too; this
        is the keyboard route to the same thing.
        """
        try:
            if (
                self._table is not None
                and obj is self._table.table_view
                and event.type() == QtCore.QEvent.KeyPress
                and event.key() == QtCore.Qt.Key_Delete
            ):
                rows = self.selected_component_rows()
                if rows:
                    self._delete_selected_gaussian_rows(rows)
                    return True
        except Exception:
            pass
        return super().eventFilter(obj, event)

    def _delete_selected_gaussian_rows(self, rows: List[int]):
        """Remove the given Gaussians and refresh the overlays."""
        m = self.main
        if not rows:
            return
        try:
            m._updating_gaussian_table = True
            for row in sorted(set(rows), reverse=True):
                self.group.pop(row)
            self._rebuild_table_rows()
        finally:
            m._updating_gaussian_table = False
        try:
            self._redraw_gaussian_overlays_from_table()
        except Exception:
            pass

    # ----------------------- Optional visibility hook --------------------
    def on_fit_dock_visibility_changed(self, visible: bool = False):
        """When the Fit dock visibility changes, keep UX consistent:
        - If becoming visible, automatically enable 'Select point' for seamless interaction.
        - If becoming hidden, disable select mode and clear point mode in the mouse filter.
        """
        m = self.main
        m.btnSelectPoint.setChecked(visible)
        if visible:
            m.mouse_event_filter.set_point_mode(visible, callback=self.on_point_selected)
        else:
            m.mouse_event_filter.set_point_mode(False, callback=None)

    # ----------------------------- Teardown ------------------------------
    def close(self) -> None:
        """Drop the registry entry and the external subscriptions.

        Called when the window goes away: a registered group whose window is
        gone is a link target that can no longer be edited, and a live
        subscription would keep calling into destroyed widgets.
        """
        self._unsubscribe_external()
        self._unregister_group()
