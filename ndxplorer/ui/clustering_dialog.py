"""One dialog for the four methods that all answer "what structure is in here?".

PCA, UMAP, HDBSCAN and K-means differ in what they return, but as *tools* they
are the same gesture: pick some columns, run, get new columns back. They were not
presented that way. Clustering had a method dropdown with two entries; UMAP sat
below it in a permanently expanded group box with nine parameters and its own two
buttons; PCA had no way in at all. So the dialog was tall enough to need
scrolling, three quarters of it irrelevant to whatever you were doing, and the
one method that reports *why* it grouped things was unreachable.

Here they are four entries in one dropdown, with only the active method's
parameters shown and one row of actions underneath. The two families differ where
they genuinely differ and nowhere else:

* **Projections** (PCA, UMAP) add ``PC_n`` / ``UMAP_n`` columns you then pick in
  the axis controls.
* **Labellings** (HDBSCAN, K-means) add ``Cluster Label``, run on a worker with
  progress and cancellation, and can be saved.

PCA also reports its loadings, which is the point of running it: "these two
parameters separate the populations" is the answer, and the component columns are
just how you plot it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, Optional, Tuple

from qtpy import QtCore, QtWidgets
from qtpy.QtCore import Signal

from ..logging_config import logging
from ..ui.column_selection_dialog import ColumnSelectionDialog
from ..utils.lazy_imports import get_hdbscan, get_kmeans, get_pca, get_umap
from .feedback import FriendlyErrorPresenter, ProgressPane
from .glyphs import Glyphs, label as glyph_label

#: Families. Projections add coordinate columns; labellings assign each point to
#: a group. The distinction drives which actions are offered, and nothing else.
PROJECTION = "projection"
LABELS = "labels"


@dataclass(frozen=True)
class Method:
    """Everything the dialog needs to know about one method.

    Collecting this per method is what removes the triplicated "is the backend
    importable, offer to install it, re-check, explain the restart" block that
    used to be pasted once per algorithm -- in two different files, having
    already drifted apart between them.
    """

    key: str
    title: str
    family: str
    #: Returns the backend, or ``None`` when it cannot be imported.
    probe: Callable[[], object]
    #: Distribution name to offer to install, and the module to import after.
    package: str
    import_name: str
    blurb: str
    #: Minimum columns the method needs to mean anything.
    min_columns: int = 1
    #: Offer installation on demand. Off for backends that ship with the app,
    #: where a failure means something is wrong rather than something is missing.
    installable: bool = True


METHODS: Tuple[Method, ...] = (
    Method(
        key="pca",
        title="PCA",
        family=PROJECTION,
        probe=get_pca,
        package="scikit-learn",
        import_name="sklearn",
        blurb="Linear decomposition. Reports which parameters carry the variance.",
        min_columns=2,
        installable=False,
    ),
    Method(
        key="umap",
        title="UMAP",
        family=PROJECTION,
        probe=get_umap,
        package="umap-learn",
        import_name="umap",
        blurb="Non-linear projection to 2-3 dimensions for visual inspection.",
        min_columns=2,
    ),
    Method(
        key="hdbscan",
        title="HDBSCAN",
        family=LABELS,
        probe=get_hdbscan,
        package="hdbscan",
        import_name="hdbscan",
        blurb="Density-based. Finds clusters of varying shape and leaves noise unlabelled.",
    ),
    Method(
        key="kmeans",
        title="K-means",
        family=LABELS,
        probe=get_kmeans,
        package="scikit-learn",
        import_name="sklearn",
        blurb="Partitions every point into exactly k groups of similar spread.",
        installable=False,
    ),
)

METHODS_BY_KEY: Dict[str, Method] = {m.key: m for m in METHODS}


class ClusteringDialog(QtWidgets.QDialog):
    """Pick a method, pick columns, run.

    Press Escape to hide. The dialog is hidden rather than destroyed on close, so
    the selected columns and parameters survive between uses.
    """

    clustering_done = Signal(tuple)
    clustering_error = Signal(str)
    progress_updated = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Find structure")
        self.setSizeGripEnabled(True)
        self.error_presenter = FriendlyErrorPresenter(self)

        self._cluster_method = "kmeans"

        # HDBSCAN
        self._cluster_min_samples = 5
        self._cluster_min_cluster_size = 50
        # K-means
        self._cluster_n_clusters = 3
        # PCA
        self._pca_n_components = 2
        self._pca_standardize = True
        # UMAP
        self._umap_n_neighbors = 15
        self._umap_min_dist = 0.1
        self._umap_n_components = 2
        self._umap_n_jobs = -1
        self._umap_metric = "euclidean"
        self._umap_learning_rate = 1.0
        self._umap_init = "spectral"
        self._umap_spread = 1.0
        self._umap_n_epochs = None  # None = let UMAP decide from the data size

        self._cluster_columns = set()
        self.clustering_worker = None

        self.setup_ui()

    # ------------------------------------------------------------------ setup

    def setup_ui(self) -> None:
        """Build the dialog: method, parameters, actions, feedback."""
        layout = QtWidgets.QVBoxLayout(self)
        layout.setSpacing(6)

        # -- method ---------------------------------------------------------
        top = QtWidgets.QHBoxLayout()
        self.comboBoxClusteringMethod = QtWidgets.QComboBox()
        for method in METHODS:
            self.comboBoxClusteringMethod.addItem(method.title, method.key)
        self.comboBoxClusteringMethod.setCurrentIndex(
            self.comboBoxClusteringMethod.findData(self._cluster_method)
        )
        self.comboBoxClusteringMethod.currentIndexChanged.connect(
            self._on_method_index_changed
        )
        top.addWidget(QtWidgets.QLabel("Method:"))
        top.addWidget(self.comboBoxClusteringMethod, 1)

        self.pushButtonSelectColumns = QtWidgets.QPushButton(
            glyph_label(Glyphs.GRID, "Columns")
        )
        self.pushButtonSelectColumns.setToolTip(
            "Choose which parameters the method sees. Strongly recommended: "
            "without a choice it falls back to the current x/y/z axes."
        )
        self.pushButtonSelectColumns.clicked.connect(self.on_select_columns)
        top.addWidget(self.pushButtonSelectColumns)
        layout.addLayout(top)

        # One-line reminder of what the selected method actually does, so the
        # choice does not depend on already knowing.
        self.labelBlurb = QtWidgets.QLabel()
        self.labelBlurb.setWordWrap(True)
        self.labelBlurb.setStyleSheet("color: #666666;")
        layout.addWidget(self.labelBlurb)

        # -- parameters, one page per method --------------------------------
        self.stackParameters = QtWidgets.QStackedWidget()
        self._pages: Dict[str, int] = {}
        for method in METHODS:
            page = QtWidgets.QWidget()
            form = QtWidgets.QFormLayout(page)
            form.setContentsMargins(0, 0, 0, 0)
            self._build_parameters(method.key, form)
            self._pages[method.key] = self.stackParameters.addWidget(page)
        layout.addWidget(self.stackParameters)

        # -- actions --------------------------------------------------------
        actions = QtWidgets.QHBoxLayout()
        self.pushButtonApplyClustering = QtWidgets.QPushButton(
            glyph_label(Glyphs.RUN, "Run")
        )
        self.pushButtonApplyClustering.clicked.connect(self.on_apply_clustering)

        self.pushButtonCancelClustering = QtWidgets.QPushButton(
            glyph_label(Glyphs.STOP, "Cancel")
        )
        self.pushButtonCancelClustering.clicked.connect(self.on_cancel_clustering)
        self.pushButtonCancelClustering.setVisible(False)

        self.pushButtonPlotUMAP = QtWidgets.QPushButton(
            glyph_label(Glyphs.CHART, "Plot")
        )
        self.pushButtonPlotUMAP.setToolTip("Show the projection in its own window.")
        self.pushButtonPlotUMAP.clicked.connect(self.on_plot_umap)

        self.pushButtonSaveClustering = QtWidgets.QPushButton(
            glyph_label(Glyphs.SAVE, "Save")
        )
        self.pushButtonSaveClustering.setToolTip("Write the cluster assignment to a folder.")
        self.pushButtonSaveClustering.clicked.connect(self.on_save_clustering_data)
        self.pushButtonSaveClustering.setEnabled(False)

        actions.addWidget(self.pushButtonApplyClustering)
        actions.addWidget(self.pushButtonCancelClustering)
        actions.addWidget(self.pushButtonPlotUMAP)
        actions.addWidget(self.pushButtonSaveClustering)
        actions.addStretch(1)
        layout.addLayout(actions)

        # -- feedback -------------------------------------------------------
        self.labelResult = QtWidgets.QLabel()
        self.labelResult.setWordWrap(True)
        self.labelResult.setTextFormat(QtCore.Qt.RichText)
        self.labelResult.setVisible(False)
        layout.addWidget(self.labelResult)

        self.progress_pane = ProgressPane(self, busy_text="Running…")
        self.progress_pane.setVisible(False)
        layout.addWidget(self.progress_pane)

        self.update_clustering_parameters_ui()

    def _build_parameters(self, key: str, form: QtWidgets.QFormLayout) -> None:
        """Populate one method's parameter page."""
        if key == "pca":
            self.spinBoxPCAComponents = QtWidgets.QSpinBox()
            self.spinBoxPCAComponents.setRange(2, 10)
            self.spinBoxPCAComponents.setValue(self._pca_n_components)
            self.spinBoxPCAComponents.setToolTip(
                "Components to keep. Two is usually enough to plot; more is useful "
                "when the first two explain little of the variance."
            )
            self.spinBoxPCAComponents.valueChanged.connect(
                lambda v: setattr(self, "_pca_n_components", v)
            )

            self.checkBoxPCAStandardize = QtWidgets.QCheckBox("Standardise columns")
            self.checkBoxPCAStandardize.setChecked(self._pca_standardize)
            self.checkBoxPCAStandardize.setToolTip(
                "Scale each column to unit variance first. Leave this on unless the "
                "columns genuinely share a scale: PCA maximises variance, so a "
                "column measured in thousands otherwise dominates one measured in "
                "units regardless of what either says."
            )
            self.checkBoxPCAStandardize.toggled.connect(
                lambda v: setattr(self, "_pca_standardize", v)
            )

            form.addRow("Components:", self.spinBoxPCAComponents)
            form.addRow("", self.checkBoxPCAStandardize)

        elif key == "umap":
            self.spinBoxUMAPNeighbors = QtWidgets.QSpinBox()
            self.spinBoxUMAPNeighbors.setRange(2, 100)
            self.spinBoxUMAPNeighbors.setValue(self._umap_n_neighbors)
            self.spinBoxUMAPNeighbors.setToolTip(
                "Size of the local neighbourhood. Larger = more global structure, "
                "smaller = more local detail."
            )
            self.spinBoxUMAPNeighbors.valueChanged.connect(
                lambda v: setattr(self, "_umap_n_neighbors", v)
            )

            self.doubleSpinBoxUMAPMinDist = QtWidgets.QDoubleSpinBox()
            self.doubleSpinBoxUMAPMinDist.setRange(0.0, 1.0)
            self.doubleSpinBoxUMAPMinDist.setSingleStep(0.01)
            self.doubleSpinBoxUMAPMinDist.setValue(self._umap_min_dist)
            self.doubleSpinBoxUMAPMinDist.setToolTip(
                "Minimum spacing of embedded points. Smaller = tighter clumps."
            )
            self.doubleSpinBoxUMAPMinDist.valueChanged.connect(
                lambda v: setattr(self, "_umap_min_dist", v)
            )

            self.spinBoxUMAPComponents = QtWidgets.QSpinBox()
            self.spinBoxUMAPComponents.setRange(2, 3)
            self.spinBoxUMAPComponents.setValue(self._umap_n_components)
            self.spinBoxUMAPComponents.setToolTip("2 to plot directly, 3 for more room.")
            self.spinBoxUMAPComponents.valueChanged.connect(
                lambda v: setattr(self, "_umap_n_components", v)
            )

            self.comboBoxUMAPMetric = QtWidgets.QComboBox()
            self.comboBoxUMAPMetric.addItems([
                "euclidean", "manhattan", "chebyshev", "minkowski", "canberra",
                "braycurtis", "cosine", "correlation", "hamming", "jaccard",
            ])
            self.comboBoxUMAPMetric.setCurrentText(self._umap_metric)
            self.comboBoxUMAPMetric.setToolTip("Distance in the original space.")
            self.comboBoxUMAPMetric.currentTextChanged.connect(
                lambda v: setattr(self, "_umap_metric", v)
            )

            form.addRow("Neighbours:", self.spinBoxUMAPNeighbors)
            form.addRow("Min. distance:", self.doubleSpinBoxUMAPMinDist)
            form.addRow("Components:", self.spinBoxUMAPComponents)
            form.addRow("Metric:", self.comboBoxUMAPMetric)

            # The rest steer convergence rather than the result's meaning, so
            # they are one fold away instead of nine rows of noise.
            advanced = QtWidgets.QWidget()
            advanced_form = QtWidgets.QFormLayout(advanced)
            advanced_form.setContentsMargins(0, 0, 0, 0)

            self.spinBoxUMAPNJobs = QtWidgets.QSpinBox()
            self.spinBoxUMAPNJobs.setRange(-1, 64)
            self.spinBoxUMAPNJobs.setValue(self._umap_n_jobs)
            self.spinBoxUMAPNJobs.setSpecialValueText("All cores")
            self.spinBoxUMAPNJobs.valueChanged.connect(
                lambda v: setattr(self, "_umap_n_jobs", v)
            )

            self.doubleSpinBoxUMAPLearningRate = QtWidgets.QDoubleSpinBox()
            self.doubleSpinBoxUMAPLearningRate.setRange(0.1, 10.0)
            self.doubleSpinBoxUMAPLearningRate.setSingleStep(0.1)
            self.doubleSpinBoxUMAPLearningRate.setValue(self._umap_learning_rate)
            self.doubleSpinBoxUMAPLearningRate.valueChanged.connect(
                lambda v: setattr(self, "_umap_learning_rate", v)
            )

            self.comboBoxUMAPInit = QtWidgets.QComboBox()
            self.comboBoxUMAPInit.addItems(["spectral", "random", "pca"])
            self.comboBoxUMAPInit.setCurrentText(self._umap_init)
            self.comboBoxUMAPInit.currentTextChanged.connect(
                lambda v: setattr(self, "_umap_init", v)
            )

            self.doubleSpinBoxUMAPSpread = QtWidgets.QDoubleSpinBox()
            self.doubleSpinBoxUMAPSpread.setRange(0.1, 5.0)
            self.doubleSpinBoxUMAPSpread.setSingleStep(0.1)
            self.doubleSpinBoxUMAPSpread.setValue(self._umap_spread)
            self.doubleSpinBoxUMAPSpread.valueChanged.connect(
                lambda v: setattr(self, "_umap_spread", v)
            )

            self.spinBoxUMAPEpochs = QtWidgets.QSpinBox()
            self.spinBoxUMAPEpochs.setRange(0, 2000)
            self.spinBoxUMAPEpochs.setValue(
                0 if self._umap_n_epochs is None else self._umap_n_epochs
            )
            self.spinBoxUMAPEpochs.setSpecialValueText("Auto")
            self.spinBoxUMAPEpochs.valueChanged.connect(self.on_umap_n_epochs_changed)

            advanced_form.addRow("Parallel jobs:", self.spinBoxUMAPNJobs)
            advanced_form.addRow("Learning rate:", self.doubleSpinBoxUMAPLearningRate)
            advanced_form.addRow("Initialisation:", self.comboBoxUMAPInit)
            advanced_form.addRow("Spread:", self.doubleSpinBoxUMAPSpread)
            advanced_form.addRow("Epochs:", self.spinBoxUMAPEpochs)

            self.checkBoxUMAPAdvanced = QtWidgets.QCheckBox("Advanced")
            advanced.setVisible(False)
            self.checkBoxUMAPAdvanced.toggled.connect(advanced.setVisible)
            form.addRow("", self.checkBoxUMAPAdvanced)
            form.addRow(advanced)

        elif key == "hdbscan":
            self.spinBoxMinSamples = QtWidgets.QSpinBox()
            self.spinBoxMinSamples.setRange(1, 99999)
            self.spinBoxMinSamples.setValue(self._cluster_min_samples)
            self.spinBoxMinSamples.setToolTip(
                "How conservative the density estimate is. Larger leaves more "
                "points unlabelled as noise."
            )
            self.spinBoxMinSamples.valueChanged.connect(self.on_min_samples_changed)

            self.spinBoxMinClusterSize = QtWidgets.QSpinBox()
            self.spinBoxMinClusterSize.setRange(1, 99999)
            self.spinBoxMinClusterSize.setValue(self._cluster_min_cluster_size)
            self.spinBoxMinClusterSize.setToolTip(
                "Smallest group that counts as a cluster rather than noise."
            )
            self.spinBoxMinClusterSize.valueChanged.connect(
                self.on_min_cluster_size_changed
            )

            form.addRow("Min. samples:", self.spinBoxMinSamples)
            form.addRow("Min. cluster size:", self.spinBoxMinClusterSize)

        elif key == "kmeans":
            self.spinBoxNClusters = QtWidgets.QSpinBox()
            self.spinBoxNClusters.setRange(1, 20)
            self.spinBoxNClusters.setValue(self._cluster_n_clusters)
            self.spinBoxNClusters.setToolTip(
                "Every point is assigned to one of exactly this many groups, "
                "whether or not that many populations exist."
            )
            self.spinBoxNClusters.valueChanged.connect(self.on_n_clusters_changed)
            form.addRow("Clusters:", self.spinBoxNClusters)

    # ------------------------------------------------------------- behaviour

    @property
    def method(self) -> Method:
        """The selected method's descriptor."""
        return METHODS_BY_KEY[self._cluster_method]

    def closeEvent(self, event):
        """Hide rather than destroy, so the settings survive."""
        event.ignore()
        self.hide()

    def keyPressEvent(self, event):
        """Escape hides the dialog."""
        if event.key() == QtCore.Qt.Key_Escape:
            self.hide()
            event.accept()
        else:
            super().keyPressEvent(event)

    def _on_method_index_changed(self, index: int) -> None:
        """Follow the combo box, which carries the method key as item data."""
        key = self.comboBoxClusteringMethod.itemData(index)
        if key:
            self._cluster_method = key
            self.update_clustering_parameters_ui()

    def on_clustering_method_changed(self, text: str) -> None:
        """Select a method by title or key."""
        for method in METHODS:
            if text in (method.key, method.title):
                self.comboBoxClusteringMethod.setCurrentIndex(
                    self.comboBoxClusteringMethod.findData(method.key)
                )
                return

    def update_clustering_parameters_ui(self) -> None:
        """Show the active method's parameters and only the actions it offers."""
        method = self.method
        self.stackParameters.setCurrentIndex(self._pages[method.key])
        # A stacked widget reserves room for its *tallest* page, so K-means'
        # single spin box would sit under a block of empty space the height of
        # UMAP's form. Letting the hidden pages be ignored for sizing makes the
        # dialog shrink to whichever method is actually showing.
        for key, index in self._pages.items():
            page = self.stackParameters.widget(index)
            policy = (
                QtWidgets.QSizePolicy.Preferred
                if key == method.key
                else QtWidgets.QSizePolicy.Ignored
            )
            page.setSizePolicy(policy, policy)
        self.stackParameters.adjustSize()
        self.labelBlurb.setText(method.blurb)
        # Saving writes a cluster assignment; a projection has none to write.
        self.pushButtonSaveClustering.setVisible(method.family == LABELS)
        # Only UMAP has a standalone plot window; PCA's answer is its loadings,
        # reported below, plus the PC columns in the ordinary axis controls.
        self.pushButtonPlotUMAP.setVisible(method.key == "umap")
        # Cancellation needs a worker, which only the labellings run on.
        self.labelResult.setVisible(False)
        self.adjustSize()

    def update_column_button(self) -> None:
        """Show the number of chosen columns on the button."""
        count = len(self._cluster_columns)
        self.pushButtonSelectColumns.setText(
            glyph_label(Glyphs.GRID, f"Columns ({count})" if count else "Columns")
        )

    # ---------------------------------------------------------------- columns

    def on_select_columns(self) -> None:
        """Choose the columns the method sees."""
        parent = self.parent()
        if parent is None or not hasattr(parent, "data_source"):
            return
        dialog = ColumnSelectionDialog(
            parent=self,
            column_names=parent.data_source.parameter_names,
            selected_columns=self._cluster_columns,
        )
        if dialog.exec_():
            self._cluster_columns = dialog.get_selected_columns()
            self.update_column_button()

    # --------------------------------------------------------------- backends

    def _ensure_backend(self) -> bool:
        """Make sure the selected method can actually run.

        One implementation for all four. Previously each algorithm carried its
        own copy of this -- and the copies in this dialog and in the clustering
        helper had already drifted, so the same missing backend produced
        different behaviour depending on which button reached it.
        """
        method = self.method
        if method.probe() is not None:
            return True

        if not method.installable:
            self.error_presenter.warn(
                f"{method.title} unavailable",
                f"{method.package} could not be imported, although it ships with "
                f"the application. The installation is likely broken.",
            )
            return False

        try:
            from ..deps_installer import ensure_package_gui

            installed = ensure_package_gui(
                parent=self,
                package=method.package,
                import_name=method.import_name,
                description=method.blurb,
                allow_pip=True,
                channels=["conda-forge", "defaults"],
            )
        except Exception as exc:
            logging.warning("Could not run the installer for %s: %s", method.package, exc)
            installed = False

        if not installed:
            self.error_presenter.warn(
                f"{method.title} not installed",
                "Installation was cancelled or failed, so this method cannot run.",
            )
            return False

        if method.probe() is None:
            self.error_presenter.info(
                f"{method.title} installed",
                f"{method.package} was installed but could not be imported yet.\n"
                "Please restart the application and try again.",
            )
            return False
        return True

    def _ensure_columns(self) -> bool:
        """Make sure enough columns are chosen, offering the picker if not."""
        method = self.method
        if len(self._cluster_columns) >= method.min_columns:
            return True

        if self._cluster_columns:
            self.error_presenter.warn(
                f"{method.title} needs more columns",
                f"Select at least {method.min_columns} columns.",
            )
            return False

        if method.family == PROJECTION:
            self.error_presenter.warn(
                f"Select columns for {method.title}",
                f"Choose at least {method.min_columns} columns to project.",
            )
            return False

        # Labellings can fall back to the plotted axes, which is worse but valid.
        reply = self.error_presenter.question(
            "Select columns?",
            "No columns are selected, so only the current X, Y and Z axes will be "
            "used — which rarely groups the data well.\n\nChoose columns now?",
        )
        if reply == QtWidgets.QMessageBox.Yes:
            self.on_select_columns()
            return bool(self._cluster_columns)
        return True

    # ----------------------------------------------------------------- actions

    def on_apply_clustering(self) -> None:
        """Run the selected method."""
        if not self._ensure_backend() or not self._ensure_columns():
            return
        if self.method.family == PROJECTION:
            self._run_projection()
        else:
            self._run_labelling()

    def _run_projection(self) -> None:
        """Add coordinate columns for PCA or UMAP."""
        parent = self.parent()
        if parent is None:
            return

        if self._cluster_method == "pca":
            result = parent.add_pca_columns_to_dataframe(
                self._cluster_columns,
                {
                    "n_components": self._pca_n_components,
                    "standardize": self._pca_standardize,
                },
            )
            if result is None:
                self.error_presenter.warn(
                    "PCA failed",
                    "No components could be computed from the selected columns.",
                )
                return
            self._show_pca_result(result)
            return

        params = self._umap_params()
        if parent.add_umap_columns_to_dataframe(self._cluster_columns, params):
            self._show_result(
                f"Added UMAP_1…UMAP_{self._umap_n_components}. "
                "Pick them in the axis controls to plot."
            )

    def _run_labelling(self) -> None:
        """Hand HDBSCAN or K-means to the worker."""
        parent = self.parent()
        if parent is None or not hasattr(parent, "start_clustering_from_dialog"):
            return

        self._set_running(True)
        if self._cluster_method == "hdbscan":
            params = {
                "min_samples": self._cluster_min_samples,
                "min_cluster_size": self._cluster_min_cluster_size,
            }
        else:
            params = {"n_clusters": self._cluster_n_clusters}

        parent.start_clustering_from_dialog(
            self._cluster_method, self._cluster_columns, params
        )

    def _umap_params(self) -> dict:
        """Collect the UMAP settings."""
        params = {
            "n_neighbors": self._umap_n_neighbors,
            "min_dist": self._umap_min_dist,
            "n_components": self._umap_n_components,
            "n_jobs": self._umap_n_jobs,
            "metric": self._umap_metric,
            "learning_rate": self._umap_learning_rate,
            "init": self._umap_init,
            "spread": self._umap_spread,
        }
        if self._umap_n_epochs is not None:
            params["n_epochs"] = self._umap_n_epochs
        return params

    def on_plot_umap(self) -> None:
        """Show the UMAP projection in its own window."""
        if not self._ensure_backend() or not self._ensure_columns():
            return
        parent = self.parent()
        if parent is not None and hasattr(parent, "create_umap_plot"):
            parent.create_umap_plot(self._cluster_columns, self._umap_params())

    def on_cancel_clustering(self) -> None:
        """Ask the worker to stop."""
        parent = self.parent()
        if parent is not None and hasattr(parent, "cancel_clustering"):
            parent.cancel_clustering()
        self.pushButtonCancelClustering.setText(
            glyph_label(Glyphs.PENDING, "Cancelling…")
        )
        self.pushButtonCancelClustering.setEnabled(False)

    def on_save_clustering_data(self) -> None:
        """Write the cluster assignment out."""
        parent = self.parent()
        if parent is not None and hasattr(parent, "onSaveClusteringData"):
            parent.onSaveClusteringData()

    # ---------------------------------------------------------------- feedback

    def _show_result(self, text: str) -> None:
        """Report an outcome in place, rather than in a box to dismiss."""
        self.labelResult.setText(text)
        self.labelResult.setVisible(True)
        # A word-wrapped rich-text label only knows its height once the layout
        # has been given the width to wrap into. Without the explicit activate,
        # adjustSize uses the pre-wrap hint and clips the last line.
        self.layout().activate()
        self.adjustSize()

    def _show_pca_result(self, result) -> None:
        """Report what PCA found, which is the reason to run it.

        The ``PC_n`` columns are how you plot the answer; the loadings *are* the
        answer -- which measured parameters carry the separation.
        """
        lines = []
        for component in range(result.n_components):
            share = 100.0 * float(result.explained_variance_ratio[component])
            drivers = ", ".join(
                f"{name} ({weight:+.2f})"
                for name, weight in result.top_contributors(component, n=3)
            )
            lines.append(f"<b>PC_{component + 1}</b> — {share:.0f}% of variance: {drivers}")
        total = 100.0 * float(result.explained_variance_ratio.sum())
        lines.append(
            f"<i>{result.n_samples} rows fitted"
            + (f", {result.n_dropped} dropped as non-finite" if result.n_dropped else "")
            + f"; {total:.0f}% of the variance retained.</i>"
        )
        self._show_result("<br>".join(lines))

    def _set_running(self, running: bool) -> None:
        """Lock the controls while a worker owns the data."""
        self.pushButtonApplyClustering.setVisible(not running)
        self.pushButtonSelectColumns.setEnabled(not running)
        self.comboBoxClusteringMethod.setEnabled(not running)
        self.pushButtonCancelClustering.setVisible(running)
        if running and self.progress_pane:
            self.progress_pane.start(
                f"Running {self.method.title}…", indeterminate=True
            )

    def update_progress(self, progress) -> None:
        """Move the progress bar."""
        if self.progress_pane:
            self.progress_pane.set_progress(progress)

    def clustering_completed(self, success: bool = True) -> None:
        """Unlock the controls once the worker is done."""
        self._set_running(False)
        self.pushButtonCancelClustering.setText(glyph_label(Glyphs.STOP, "Cancel"))
        self.pushButtonCancelClustering.setEnabled(True)
        if self.progress_pane:
            if success:
                self.progress_pane.finish("Finished.")
            else:
                self.progress_pane.fail("Cancelled or failed.")
        self.pushButtonSaveClustering.setEnabled(success)

    # ------------------------------------------------- parameter change hooks

    def on_min_samples_changed(self, value) -> None:
        """Track the HDBSCAN ``min_samples`` spin box."""
        self._cluster_min_samples = value

    def on_min_cluster_size_changed(self, value) -> None:
        """Track the HDBSCAN ``min_cluster_size`` spin box."""
        self._cluster_min_cluster_size = value

    def on_n_clusters_changed(self, value) -> None:
        """Track the K-means cluster-count spin box."""
        self._cluster_n_clusters = value

    def on_umap_n_epochs_changed(self, value) -> None:
        """Track the UMAP epoch count, where zero means "let UMAP decide"."""
        self._umap_n_epochs = None if value == 0 else value
