"""
Performance Settings Dialog for ndxplorer.

Provides a user-friendly interface for configuring performance-related
environment variables and settings with detailed tooltips.
"""

from typing import Dict, Any
from qtpy import QtWidgets, QtCore

from .glyphs import Glyphs, label as glyph_label
from pathlib import Path

from ..logging_config import logging
from ..utils.performance_config import (
    PerformanceConfig,
    get_performance_config,
    save_performance_config,
)


class PerformanceSettingsDialog(QtWidgets.QDialog):
    """Dialog for configuring performance settings with tooltips."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Performance Settings")
        self.setModal(True)
        self.resize(600, 700)
        
        # Store original config for reset functionality
        self._original_config = get_performance_config()
        
        self._setup_ui()
        self._load_current_settings()
        
    def _setup_ui(self):
        """Setup the user interface."""
        layout = QtWidgets.QVBoxLayout(self)
        
        # Create scroll area for settings
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QtWidgets.QWidget()
        scroll_layout = QtWidgets.QVBoxLayout(scroll_widget)
        
        # Add title
        title = QtWidgets.QLabel("Performance Configuration")
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px;")
        scroll_layout.addWidget(title)
        
        # Add description
        desc = QtWidgets.QLabel(
            "Configure performance settings for ndxplorer. These settings control histogram computation, "
            "memory usage, and optimization features. Changes take effect after restarting ndxplorer."
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("margin: 0px 10px 20px 10px; color: #666;")
        scroll_layout.addWidget(desc)
        
        # Create settings groups
        self._create_computation_group(scroll_layout)
        self._create_memory_group(scroll_layout)
        self._create_optimization_group(scroll_layout)
        
        # Add stretch
        scroll_layout.addStretch()
        
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)
        
        # Add buttons
        button_layout = QtWidgets.QHBoxLayout()
        
        self.reset_btn = QtWidgets.QPushButton(glyph_label(Glyphs.RESET, "Reset to Defaults"))
        self.reset_btn.clicked.connect(self._reset_to_defaults)
        self.reset_btn.setToolTip("Reset all performance settings to their default values")

        self.cancel_btn = QtWidgets.QPushButton(glyph_label(Glyphs.CLOSE, "Cancel"))
        self.cancel_btn.clicked.connect(self.reject)

        self.apply_btn = QtWidgets.QPushButton(glyph_label(Glyphs.CHECK, "Apply"))
        self.apply_btn.clicked.connect(self._apply_settings)

        self.ok_btn = QtWidgets.QPushButton(glyph_label(Glyphs.CHECK, "OK"))
        self.ok_btn.clicked.connect(self._ok_clicked)
        self.ok_btn.setDefault(True)
        
        button_layout.addWidget(self.reset_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.cancel_btn)
        button_layout.addWidget(self.apply_btn)
        button_layout.addWidget(self.ok_btn)
        
        layout.addLayout(button_layout)
        
    # The "Background Computation" group stood here, offering an "Enable
    # Background Worker" checkbox. There is no background worker: histograms
    # are filled synchronously in about twenty milliseconds. A switch that
    # switches nothing is worse than no switch, because it is read as an
    # explanation when something is slow.

    def _create_computation_group(self, layout):
        """Create histogram computation settings group."""
        group = QtWidgets.QGroupBox("Histogram Computation")
        group.setToolTip("Configure histogram computation engine and threading")
        group_layout = QtWidgets.QVBoxLayout(group)
        
        # No engine switch: histograms are filled in tttrlib, always. The
        # boost-histogram checkbox chose between three implementations that were
        # supposed to agree and did not have to, and a picture whose engine
        # depended on a settings flag is a picture that cannot be reproduced
        # from the file alone.
        # Fast histogram checkbox
        self.fast_hist_cb = QtWidgets.QCheckBox("Use Fast Histogram Optimizations")
        self.fast_hist_cb.setToolTip(
            "Enables the caching and pre-binning around the fill.\n"
            "The fill itself is always tttrlib and is not affected.\n"
            "Keep enabled for best performance."
        )
        group_layout.addWidget(self.fast_hist_cb)
        
        # Parallel histogram checkbox
        self.parallel_cb = QtWidgets.QCheckBox("Use Parallel Computation")
        self.parallel_cb.setToolTip(
            "Use multiple CPU cores for histogram computation when available.\n"
            "Provides significant speedup for large datasets.\n"
            "Disable on single-core systems or if threading causes issues."
        )
        group_layout.addWidget(self.parallel_cb)
        
        # Threads setting
        threads_layout = QtWidgets.QHBoxLayout()
        threads_label = QtWidgets.QLabel("Histogram Threads:")
        threads_label.setToolTip(
            "Number of threads to use for histogram computation.\n"
            "-1: Auto-detect and use all available cores\n"
            "0 or 1: Disable parallelism\n"
            "2+: Use specified number of threads"
        )
        self.threads_spin = QtWidgets.QSpinBox()
        self.threads_spin.setRange(-1, 64)
        self.threads_spin.setValue(-1)
        self.threads_spin.setToolTip(
            "Number of threads for histogram computation.\n"
            "-1 uses all available cores, 0/1 disables parallelism."
        )
        threads_layout.addWidget(threads_label)
        threads_layout.addWidget(self.threads_spin)
        threads_layout.addStretch()
        group_layout.addLayout(threads_layout)
        
        # Plot backend selection
        backend_layout = QtWidgets.QHBoxLayout()
        backend_label = QtWidgets.QLabel("Plot Backend:")
        backend_label.setToolTip(
            "Choose the plotting backend for 2D plots and visualizations:\n"
            "• pyqtgraph: Fast interactive plots (default)\n"
            "• matplotlib: Feature-rich, widely used\n"
            "Changes require restarting ndX to take effect."
        )
        self.backend_combo = QtWidgets.QComboBox()
        self.backend_combo.addItems(["pyqtgraph", "matplotlib"])
        self.backend_combo.setToolTip(
            "Select plotting backend. pyqtgraph is recommended for best performance."
        )
        backend_layout.addWidget(backend_label)
        backend_layout.addWidget(self.backend_combo)
        backend_layout.addStretch()
        group_layout.addLayout(backend_layout)
        
        layout.addWidget(group)
        
    def _create_memory_group(self, layout):
        """Create memory and caching settings group."""
        group = QtWidgets.QGroupBox("Memory & Caching")
        group.setToolTip("Configure memory usage and caching strategies")
        group_layout = QtWidgets.QVBoxLayout(group)
        
        # There is no histogram-cache switch any more. Histograms are recomputed
        # from the store on every redraw, in a few milliseconds -- less than
        # deciding whether a cached one is still valid -- so the setting offered
        # a memory-for-speed trade that no longer exists in either direction.
        #
        # There is no bitfield-mask switch any more. The selection IS bit-packed
        # now, in the store, always -- so the setting had nothing left to turn
        # off and its checkbox promised a saving the user was already getting.
        # Aggressive caching checkbox
        self.aggressive_cb = QtWidgets.QCheckBox("Aggressive Caching")
        self.aggressive_cb.setToolTip(
            "Cache more intermediate results for better performance at the cost of\n"
            "higher memory usage. Improves responsiveness for complex operations.\n"
            "Disable on memory-constrained systems."
        )
        group_layout.addWidget(self.aggressive_cb)
        
        # Memory limits
        memory_layout = QtWidgets.QGridLayout()
        
        # Histogram cache memory
        # No "Histogram Cache (MB)" here either -- there is nothing to size.
        # General cache memory
        gen_cache_label = QtWidgets.QLabel("General Cache (MB):")
        gen_cache_label.setToolTip(
            "Memory limit for general-purpose caching (selections, computations, etc.).\n"
            "Affects various UI operations and data processing.\n"
            "Recommended range: 10-500 MB"
        )
        self.gen_cache_spin = QtWidgets.QSpinBox()
        self.gen_cache_spin.setRange(5, 1000)
        self.gen_cache_spin.setValue(50)
        self.gen_cache_spin.setToolTip("General cache memory limit in MB")
        memory_layout.addWidget(gen_cache_label, 1, 0)
        memory_layout.addWidget(self.gen_cache_spin, 1, 1)
        
        group_layout.addLayout(memory_layout)
        layout.addWidget(group)
        
    def _create_optimization_group(self, layout):
        """Create additional optimization settings group."""
        group = QtWidgets.QGroupBox("Advanced Options")
        group.setToolTip("Advanced performance optimization options")
        group_layout = QtWidgets.QVBoxLayout(group)
        
        # Info label
        info = QtWidgets.QLabel(
            "For most users, the default settings provide optimal performance. "
            "Advanced users can fine-tune these settings for specific workloads."
        )
        info.setWordWrap(True)
        info.setStyleSheet("color: #666; font-style: italic; margin: 5px;")
        group_layout.addWidget(info)
        
        # Settings file info
        settings_info = QtWidgets.QLabel(
            "Settings are saved to: ~/.ndxplorer/mfd.settings.json\n"
            "Values in settings file override environment variables."
        )
        settings_info.setWordWrap(True)
        settings_info.setStyleSheet("color: #666; font-size: 11px; margin: 5px;")
        group_layout.addWidget(settings_info)
        
        layout.addWidget(group)
        
    def _load_current_settings(self):
        """Load current settings into the UI."""
        self._show_config(get_performance_config())

    def _show_config(self, config: PerformanceConfig):
        """Put *config* into the controls."""

        # Computation settings
        self.fast_hist_cb.setChecked(config.use_fast_histogram)
        self.parallel_cb.setChecked(config.parallel_histogram)
        self.threads_spin.setValue(config.histogram_threads)
        
        # Plot backend
        backend_index = self.backend_combo.findText(config.plot_backend)
        if backend_index >= 0:
            self.backend_combo.setCurrentIndex(backend_index)
        else:
            logging.warning(f"Unknown plot backend '{config.plot_backend}', using default")
        
        # Memory settings
        self.aggressive_cb.setChecked(config.aggressive_caching)
        self.gen_cache_spin.setValue(int(config.general_cache_memory_mb))
        
    def _apply_settings(self):
        """Apply settings and save to settings file."""
        try:
            new_config = PerformanceConfig(
                use_fast_histogram=self.fast_hist_cb.isChecked(),
                general_cache_memory_mb=float(self.gen_cache_spin.value()),
                parallel_histogram=self.parallel_cb.isChecked(),
                aggressive_caching=self.aggressive_cb.isChecked(),
                histogram_threads=self.threads_spin.value(),
                plot_backend=self.backend_combo.currentText(),
            )
            save_performance_config(new_config)
            QtWidgets.QMessageBox.information(
                self,
                "Settings Applied",
                "Performance settings have been saved.\n\n"
                "Some changes may require restarting ndX to take full effect."
            )
            logging.info("Performance settings updated and saved")
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to save settings: {e}")
            logging.error(f"Failed to save performance settings: {e}")

    def _reset_to_defaults(self):
        """Reset all settings to defaults."""
        reply = QtWidgets.QMessageBox.question(
            self, 
            "Reset Settings", 
            "Reset all performance settings to their default values?\n\n"
            "This will clear your custom configuration.",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No,
            QtWidgets.QMessageBox.No
        )
        
        if reply == QtWidgets.QMessageBox.Yes:
            # The defaults are shown; Apply saves them. (Resetting the cached
            # config alone re-read the saved file and changed nothing.)
            self._show_config(PerformanceConfig())
            QtWidgets.QMessageBox.information(self, "Reset", "Settings reset to defaults")
            
    def _ok_clicked(self):
        """Handle OK button click."""
        self._apply_settings()
        self.accept()
