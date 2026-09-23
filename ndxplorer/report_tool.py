"""File > Make Report in the Qt window: the report tool's dialog.

What a report is -- which folders qualify, how each plot is histogrammed and
drawn, the files it writes, the combined DOCX -- is
:mod:`ndxplorer.export.report`, shared with the emtk app. This module is the
Qt dialog over it: the folder list (with drops), the ``report.yaml`` editor,
the image browser and the batch with its progress dialog.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional

import yaml
from qtpy import QtCore, QtWidgets
from qtpy.QtGui import QBrush, QColor, QPixmap

from .export import report as rep
from .logging_config import logging
from .settings import ensure_default_settings, get_settings_path


class FolderDropList(QtWidgets.QListWidget):
    """The analysis-folder list: multi-select, folder drops, "Copy Path(s)"."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.setAcceptDrops(True)
        self.setDragDropMode(QtWidgets.QAbstractItemView.DropOnly)
        self.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self._on_context_menu)

    def _copy_selected_paths(self) -> None:
        items = self.selectedItems()
        if not items and self.currentRow() >= 0:
            items = [self.item(self.currentRow())]
        if items:
            QtWidgets.QApplication.clipboard().setText("\n".join(it.text() for it in items))

    def _on_context_menu(self, pos):
        menu = QtWidgets.QMenu(self)
        act_copy = menu.addAction("Copy Path(s)")
        if menu.exec_(self.mapToGlobal(pos)) == act_copy:
            self._copy_selected_paths()

    @staticmethod
    def _dropped_dirs(event) -> List[Path]:
        md = event.mimeData()
        if not md or not md.hasUrls():
            return []
        return [p for p in (Path(u.toLocalFile()) for u in md.urls()) if p.is_dir()]

    def dragEnterEvent(self, event):
        if self._dropped_dirs(event):
            event.acceptProposedAction()
        else:
            event.ignore()

    dragMoveEvent = dragEnterEvent

    def dropEvent(self, event):
        roots = self._dropped_dirs(event)
        if not roots:
            event.ignore()
            return
        added = False
        for folder in rep.discover_analysis_folders(roots):
            if str(folder) not in self.filenames():
                self.addItem(str(folder))
                added = True
        if not added:
            QtWidgets.QMessageBox.information(
                self, "No analysis folders found",
                "No analysis folders were found in the dropped directory/directories.")
        wizard = self.window()
        if hasattr(wizard, "_refresh_folder_highlights"):
            wizard._refresh_folder_highlights()
        event.acceptProposedAction()

    def filenames(self) -> List[str]:
        return [self.item(i).text() for i in range(self.count())]


class ReportWizard(QtWidgets.QDialog):
    """The "ndX Report Tool" dialog."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("ndX Report Tool")
        self.resize(900, 600)

        main_layout = QtWidgets.QVBoxLayout(self)
        split = QtWidgets.QSplitter(self)
        split.setOrientation(QtCore.Qt.Horizontal)
        main_layout.addWidget(split)

        # Left: folders and their buttons
        left = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left)
        self.folder_list = FolderDropList(self)
        left_layout.addWidget(QtWidgets.QLabel("Analysis folders (drop here):"))
        left_layout.addWidget(self.folder_list)
        btns_left = QtWidgets.QHBoxLayout()
        self.btn_add_folder = QtWidgets.QPushButton("Add…")
        self.btn_remove_folder = QtWidgets.QPushButton("Remove")
        self.btn_clear_folders = QtWidgets.QPushButton("Clear")
        for button in (self.btn_add_folder, self.btn_remove_folder, self.btn_clear_folders):
            btns_left.addWidget(button)
        left_layout.addLayout(btns_left)
        split.addWidget(left)

        # Right: the report.yaml editor, then the image browser
        right = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right)
        right_layout.addWidget(QtWidgets.QLabel("Report YAML (report.yaml):"))
        self.editor = QtWidgets.QPlainTextEdit()
        font = self.editor.font()
        font.setFamily("Courier New")
        font.setPointSize(10)
        self.editor.setFont(font)
        right_layout.addWidget(self.editor)
        btns_right = QtWidgets.QHBoxLayout()
        self.btn_load = QtWidgets.QPushButton("Load…")
        self.btn_save = QtWidgets.QPushButton("Save…")
        btns_right.addStretch(1)
        btns_right.addWidget(self.btn_load)
        btns_right.addWidget(self.btn_save)
        right_layout.addLayout(btns_right)

        images_box = QtWidgets.QGroupBox("Browse generated images")
        images_layout = QtWidgets.QVBoxLayout(images_box)
        self.selected_path_edit = QtWidgets.QLineEdit()
        self.selected_path_edit.setReadOnly(True)
        self.selected_path_edit.setPlaceholderText("No folder selected")
        self.selected_path_edit.setToolTip("Shows the full path of the currently selected dataset")
        images_layout.addWidget(self.selected_path_edit)
        combo_row = QtWidgets.QHBoxLayout()
        combo_row.addWidget(QtWidgets.QLabel("Plot:"))
        self.image_combo = QtWidgets.QComboBox()
        combo_row.addWidget(self.image_combo, 1)
        images_layout.addLayout(combo_row)
        self.image_preview = QtWidgets.QLabel()
        self.image_preview.setAlignment(QtCore.Qt.AlignCenter)
        self.image_preview.setMinimumSize(200, 200)
        self.image_preview.setStyleSheet(
            "QLabel { background: #222; color: #ccc; border: 1px solid #444; }")
        images_layout.addWidget(self.image_preview, 1)
        right_layout.addWidget(images_box, 1)
        split.addWidget(right)
        split.setStretchFactor(1, 2)

        bottom = QtWidgets.QHBoxLayout()
        bottom.addStretch(1)
        self.btn_clear_reports = QtWidgets.QPushButton("Clear Reports")
        self.btn_generate = QtWidgets.QPushButton("Generate Reports")
        bottom.addWidget(self.btn_clear_reports)
        bottom.addWidget(self.btn_generate)
        main_layout.addLayout(bottom)

        self.btn_add_folder.clicked.connect(self._on_add_folder)
        self.btn_remove_folder.clicked.connect(self._on_remove_folder)
        self.btn_clear_folders.clicked.connect(self._on_clear_folders)
        self.btn_load.clicked.connect(self._on_load_cfg)
        self.btn_save.clicked.connect(self._on_save_cfg)
        self.btn_generate.clicked.connect(self._on_generate)
        self.btn_clear_reports.clicked.connect(self._on_clear_reports)
        self.image_combo.currentIndexChanged.connect(self._on_image_combo_changed)
        self.image_combo.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.image_combo.customContextMenuRequested.connect(self._on_image_combo_context_menu)
        self.folder_list.itemClicked.connect(lambda _item: self._on_folder_selection_changed())
        self.folder_list.itemSelectionChanged.connect(self._on_folder_selection_changed)

        # The configuration: the user's report.yaml, seeded from the packaged one.
        self._default_cfg_path = get_settings_path() / "report.yaml"
        try:
            ensure_default_settings()
            if not self._default_cfg_path.exists():
                self._default_cfg_path.write_text(rep.default_config_text(), encoding="utf-8")
        except OSError as exc:
            logging.debug("Could not seed %s: %s", self._default_cfg_path, exc)
        self.editor.setPlainText(rep.default_config_text(get_settings_path()))

        self._image_paths: List[Path] = []
        self._current_image_path: Optional[Path] = None
        self._gen: Optional[Dict] = None
        self._refresh_folder_highlights()

    # ------------------------------------------------------------- folders
    def _on_add_folder(self):
        d = QtWidgets.QFileDialog.getExistingDirectory(self, "Select analysis folder")
        if d and d not in self.folder_list.filenames():
            self.folder_list.addItem(d)
            self.folder_list.setCurrentRow(self.folder_list.count() - 1)
            self.selected_path_edit.setText(str(Path(d).resolve()))
            self._refresh_folder_highlights()

    def _on_remove_folder(self):
        for it in self.folder_list.selectedItems():
            self.folder_list.takeItem(self.folder_list.row(it))
        item = self.folder_list.currentItem()
        self.selected_path_edit.setText(str(Path(item.text()).resolve()) if item else "")
        self._refresh_folder_highlights()

    def _on_clear_folders(self):
        if self.folder_list.count() == 0:
            return
        res = QtWidgets.QMessageBox.question(
            self, "Clear list", "Remove all folders from the list?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.Yes)
        if res != QtWidgets.QMessageBox.Yes:
            return
        self.folder_list.clear()
        self.selected_path_edit.clear()

    def _refresh_folder_highlights(self) -> None:
        for i in range(self.folder_list.count()):
            item = self.folder_list.item(i)
            processed = rep.is_folder_processed(item.text())
            item.setBackground(QBrush(QColor(212, 237, 218)) if processed else QBrush())
            item.setForeground(QBrush(QColor(33, 37, 41)) if processed else QBrush())
            item.setToolTip(f"Processed: {'Yes' if processed else 'No'}\n{item.text()}")

    def _on_clear_reports(self):
        selected = self.folder_list.selectedItems()
        roots = [it.text() for it in selected] if selected else self.folder_list.filenames()
        if not roots:
            QtWidgets.QMessageBox.information(self, "No folders", "No analysis folders to clear.")
            return
        targets = list(dict.fromkeys([Path(r) for r in roots]
                                     + rep.discover_analysis_folders(roots)))
        count = len(targets) - len(roots) or len(roots)
        res = QtWidgets.QMessageBox.question(
            self, "Clear Reports",
            f"This will permanently delete report folders for {count} analysis folder(s). "
            "Continue?",
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.No)
        if res != QtWidgets.QMessageBox.Yes:
            return
        cleared = rep.clear_reports(targets)
        self._on_folder_selection_changed()
        if cleared:
            QtWidgets.QMessageBox.information(self, "Reports cleared",
                                              f"Cleared reports for {cleared} folder(s).")
        else:
            QtWidgets.QMessageBox.information(self, "Nothing to clear",
                                              "No report folders were found to delete.")
        self._refresh_folder_highlights()

    # -------------------------------------------------------------- config
    def _on_load_cfg(self):
        fn, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Open config", str(self._default_cfg_path), "YAML/JSON (*.yaml *.yml *.json)")
        if not fn:
            return
        try:
            text = Path(fn).read_text(encoding="utf-8")
        except OSError as e:
            QtWidgets.QMessageBox.critical(self, "Load error", str(e))
            return
        try:
            rep.parse_config(text, json_text=fn.lower().endswith(".json"))
        except rep.ConfigError as ve:
            res = QtWidgets.QMessageBox.question(
                self, "Parse warning",
                f"File read, but failed to parse config (will still load text):\n{ve}\n\n"
                "Load as-is?",
                QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, QtWidgets.QMessageBox.Yes)
            if res != QtWidgets.QMessageBox.Yes:
                return
        self.editor.setPlainText(text)

    def _on_save_cfg(self):
        fn, _ = QtWidgets.QFileDialog.getSaveFileName(
            self, "Save config", str(self._default_cfg_path), "YAML (*.yaml);;JSON (*.json)")
        if not fn:
            return
        try:
            data = rep.parse_config(self.editor.toPlainText())
            if fn.lower().endswith(".json"):
                Path(fn).write_text(json.dumps(data, indent=2), encoding="utf-8")
            else:
                if not fn.lower().endswith((".yaml", ".yml")):
                    fn += ".yaml"
                Path(fn).write_text(rep.config_text(data), encoding="utf-8")
        except (OSError, rep.ConfigError) as e:
            QtWidgets.QMessageBox.critical(self, "Save error", str(e))

    # -------------------------------------------------------------- images
    def _on_folder_selection_changed(self):
        item = self.folder_list.currentItem()
        if item is None:
            self.selected_path_edit.clear()
            return
        self.selected_path_edit.setText(str(Path(item.text()).resolve()))
        self._load_images(rep.report_images(item.text()))

    def _load_images(self, paths: List[Path]) -> None:
        self._image_paths = list(paths)
        previous = self.image_combo.currentIndex()
        self.image_combo.blockSignals(True)
        self.image_combo.clear()
        for p in self._image_paths:
            self.image_combo.addItem(p.name, str(p))
        self.image_combo.blockSignals(False)
        if self._image_paths:
            index = previous if 0 <= previous < len(self._image_paths) else 0
            self.image_combo.setCurrentIndex(index)
            self._show_image(index)
        else:
            self._current_image_path = None
            self.image_preview.setText("No images found")
            self.image_preview.setPixmap(QPixmap())

    def _on_image_combo_changed(self, idx: int):
        if idx is not None and idx >= 0:
            self._show_image(idx)

    def _on_image_combo_context_menu(self, pos):
        idx = self.image_combo.currentIndex()
        if idx < 0:
            return
        path_str = self.image_combo.itemData(idx) or self.image_combo.itemText(idx)
        menu = QtWidgets.QMenu(self.image_combo)
        act_copy = menu.addAction("Copy Image Path")
        if menu.exec_(self.image_combo.mapToGlobal(pos)) == act_copy and path_str:
            QtWidgets.QApplication.clipboard().setText(str(path_str))

    def _show_image(self, index: int):
        if 0 <= index < len(self._image_paths):
            self._current_image_path = self._image_paths[index]
            self._update_image_preview()

    def _update_image_preview(self):
        if not self._current_image_path:
            self.image_preview.setText("No image selected")
            self.image_preview.setPixmap(QPixmap())
            return
        pix = QPixmap(str(self._current_image_path))
        if pix.isNull():
            self.image_preview.setText(f"Cannot load image\n{self._current_image_path}")
            self.image_preview.setPixmap(QPixmap())
            return
        size = self.image_preview.size()
        self.image_preview.setPixmap(pix.scaled(size.width() - 8, size.height() - 8,
                                                QtCore.Qt.KeepAspectRatio,
                                                QtCore.Qt.SmoothTransformation))
        self.image_preview.setText("")

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_image_preview()

    # ---------------------------------------------------------- generating
    def _on_generate(self):
        try:
            cfg = rep.parse_config(self.editor.toPlainText())
        except rep.ConfigError as e:
            QtWidgets.QMessageBox.critical(self, "YAML error", str(e))
            return
        roots = self.folder_list.filenames()
        if not roots:
            QtWidgets.QMessageBox.warning(self, "No folders", "Please add analysis folders.")
            return
        targets = rep.discover_analysis_folders(roots)
        if not targets:
            QtWidgets.QMessageBox.warning(self, "No analysis folders found",
                                          "No valid analysis subfolders were found. "
                                          "Please check your selection.")
            return
        targets = [t for t in targets if not rep.is_folder_processed(t)]
        if not targets:
            QtWidgets.QMessageBox.information(self, "Nothing to do",
                                              "All selected analysis folders already have a "
                                              "report. Nothing to generate.")
            return
        self._start_generation(cfg, targets)

    def _start_generation(self, cfg: Dict, targets: List[Path]) -> None:
        if self._gen is not None:
            return
        progress = QtWidgets.QProgressDialog("Generating reports...", "Cancel", 0,
                                             len(targets), self)
        progress.setWindowTitle("Generating")
        progress.setWindowModality(QtCore.Qt.WindowModal)
        progress.setAutoClose(False)
        progress.setAutoReset(False)
        progress.show()
        axis_settings = getattr(getattr(self.parent(), "plot_control", None),
                                "axis_settings", None)
        self._gen = {"cfg": cfg, "targets": list(targets), "index": 0, "results": [],
                     "progress": progress, "generator": rep.ReportGenerator(
                         axis_settings=axis_settings)}
        for button in (self.btn_generate, self.btn_clear_reports, self.btn_add_folder,
                       self.btn_remove_folder, self.btn_clear_folders):
            button.setEnabled(False)
        QtCore.QTimer.singleShot(0, self._process_next_target)

    def _process_next_target(self) -> None:
        gen = self._gen
        cancelled = gen["progress"].wasCanceled()
        if cancelled or gen["index"] >= len(gen["targets"]):
            self._finish_generation(cancelled)
            return
        folder = gen["targets"][gen["index"]]
        gen["progress"].setLabelText(f"Processing: {folder}")
        gen["progress"].setValue(gen["index"])
        QtWidgets.QApplication.processEvents()
        try:
            report = gen["generator"].build(folder, gen["cfg"])
            gen["results"].append(rep.write_folder_report(report))
            for warning in report.warnings:
                QtWidgets.QMessageBox.warning(self, "Plot error", warning)
            if not rep.docx_available() and gen["index"] == 0:
                QtWidgets.QMessageBox.warning(self, "python-docx missing",
                                              "python-docx is not installed. PNGs and CSVs "
                                              "were created; no DOCX.")
        except Exception as e:  # noqa: BLE001 - one folder's error, the batch goes on
            QtWidgets.QMessageBox.critical(self, "Error", f"Error for {folder}: {e}")
        gen["index"] += 1
        gen["progress"].setValue(gen["index"])
        self._refresh_folder_highlights()
        QtCore.QTimer.singleShot(0, self._process_next_target)

    def _finish_generation(self, cancelled: bool) -> None:
        gen, self._gen = self._gen, None
        gen["progress"].close()
        for button in (self.btn_generate, self.btn_clear_reports, self.btn_add_folder,
                       self.btn_remove_folder, self.btn_clear_folders):
            button.setEnabled(True)
        results = gen["results"]
        if len(results) > 1:
            if not rep.docx_available():
                QtWidgets.QMessageBox.warning(self, "python-docx missing",
                                              "python-docx is not installed. Skipping combined "
                                              "final report.")
            else:
                suggested = str(Path(results[0]["folder"]).parent / "ndX_Batch_Report.docx")
                fn, _ = QtWidgets.QFileDialog.getSaveFileName(
                    self, "Save Final Combined Report", suggested, "DOCX (*.docx)")
                if fn:
                    try:
                        out = fn if fn.lower().endswith(".docx") else fn + ".docx"
                        Path(out).write_bytes(rep.combined_docx_bytes(results))
                    except Exception as e:  # noqa: BLE001
                        QtWidgets.QMessageBox.critical(self, "Final Report Error", str(e))
        self._refresh_folder_highlights()
        if cancelled:
            QtWidgets.QMessageBox.information(self, "Canceled", "Generation canceled.")
        else:
            QtWidgets.QMessageBox.information(self, "Done", "Reports generated.")


def open_report_wizard(parent=None):
    """Show the report tool, modal."""
    ReportWizard(parent=parent).exec_()
