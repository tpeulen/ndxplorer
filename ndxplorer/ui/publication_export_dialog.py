"""Publication-quality export: options dialog, toolbar button, headless entry.

The heavy lifting (composing the Matplotlib figure) lives in
:mod:`ndxplorer.export.publication_figure`; this module is the GUI glue plus a
Qt-free :func:`export_publication_figure` entry point so the feature can be
driven from tests/scripts without opening a dialog.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from qtpy import QtCore, QtWidgets

from ..logging_config import logging


# Format -> (file suffix, is_vector)
_FORMATS = {
    "PDF (vector)": (".pdf", True),
    "SVG (vector)": (".svg", True),
    "PNG (raster)": (".png", False),
}


def export_publication_figure(
    ndxplorer,
    path: os.PathLike | str,
    *,
    dpi: int = 300,
    with_marginals: bool = True,
    transparent: bool = False,
) -> Path:
    """Render the current view and write it to ``path`` (headless entry point).

    The output format follows the file suffix (``.pdf`` / ``.svg`` are vector,
    ``.png``/``.jpg`` raster at ``dpi``). Returns the written path.
    """
    from ..export.publication_figure import render_current_view
    from ..export.image_export import export_image
    from ..export.models import SelectionExportPayload

    target = Path(path)
    fig = render_current_view(ndxplorer, dpi=dpi, with_marginals=with_marginals)
    try:
        export_image(
            SelectionExportPayload(figure=fig, name="ndxplorer_publication"),
            target,
            dpi=dpi,
            transparent=transparent,
        )
    finally:
        # Matplotlib Figures created with an explicit canvas are not tracked by
        # pyplot, but close defensively in case a backend registered it.
        try:
            import matplotlib.pyplot as plt
            plt.close(fig)
        except Exception:
            pass
    logging.info("Publication figure exported to %s", target)
    return target


class PublicationExportDialog(QtWidgets.QDialog):
    """Small options dialog: format, DPI, marginals, transparency."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Publication export")
        self.setMinimumWidth(320)

        form = QtWidgets.QFormLayout()

        self.combo_format = QtWidgets.QComboBox()
        self.combo_format.addItems(list(_FORMATS.keys()))
        self.combo_format.setToolTip(
            "Vector (PDF/SVG) is resolution-independent and best for print; "
            "PNG is a high-resolution raster."
        )
        form.addRow("Format:", self.combo_format)

        self.spin_dpi = QtWidgets.QSpinBox()
        self.spin_dpi.setRange(72, 1200)
        self.spin_dpi.setValue(300)
        self.spin_dpi.setSingleStep(50)
        self.spin_dpi.setToolTip("Raster resolution. Ignored for vector formats.")
        form.addRow("DPI (raster):", self.spin_dpi)

        self.check_marginals = QtWidgets.QCheckBox("Include X/Y marginal histograms")
        self.check_marginals.setChecked(True)
        form.addRow(self.check_marginals)

        self.check_transparent = QtWidgets.QCheckBox("Transparent background")
        self.check_transparent.setChecked(False)
        form.addRow(self.check_transparent)

        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Cancel
        )
        buttons.button(QtWidgets.QDialogButtonBox.Save).setText("Export…")
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout = QtWidgets.QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(buttons)

        # Grey out DPI for vector formats.
        self.combo_format.currentTextChanged.connect(self._sync_dpi_enabled)
        self._sync_dpi_enabled(self.combo_format.currentText())

    def _sync_dpi_enabled(self, format_label: str) -> None:
        _suffix, is_vector = _FORMATS.get(format_label, (".png", False))
        self.spin_dpi.setEnabled(not is_vector)

    def options(self) -> dict:
        label = self.combo_format.currentText()
        suffix, is_vector = _FORMATS[label]
        return {
            "suffix": suffix,
            "is_vector": is_vector,
            "dpi": int(self.spin_dpi.value()),
            "with_marginals": self.check_marginals.isChecked(),
            "transparent": self.check_transparent.isChecked(),
        }


def open_publication_export(ndxplorer) -> None:
    """Show the options dialog + save prompt, then export the current view."""
    # Fail early with a friendly message if there's nothing to export.
    hist = getattr(ndxplorer, "_histogram", {}) or {}
    if "2d" not in hist:
        QtWidgets.QMessageBox.information(
            ndxplorer, "Publication export",
            "No 2D histogram is available yet — load data and update the plot first.",
        )
        return

    dialog = PublicationExportDialog(ndxplorer)
    if dialog.exec_() != QtWidgets.QDialog.Accepted:
        return
    opts = dialog.options()

    default_path = _default_export_path(ndxplorer, opts["suffix"])
    label = next(k for k, v in _FORMATS.items() if v[0] == opts["suffix"])
    filter_str = f"{label} (*{opts['suffix']})"
    filename, _ = QtWidgets.QFileDialog.getSaveFileName(
        ndxplorer, "Export publication figure", default_path, filter_str
    )
    if not filename:
        return
    if not Path(filename).suffix:
        filename = f"{filename}{opts['suffix']}"

    try:
        export_publication_figure(
            ndxplorer, filename,
            dpi=opts["dpi"],
            with_marginals=opts["with_marginals"],
            transparent=opts["transparent"],
        )
    except Exception as exc:  # pragma: no cover - UI path
        logging.error("Publication export failed: %s", exc)
        QtWidgets.QMessageBox.critical(
            ndxplorer, "Publication export", f"Export failed:\n{exc}"
        )
        return
    logging.info("Publication figure saved to %s", filename)


def _default_export_path(ndxplorer, suffix: str) -> str:
    try:
        base = ndxplorer.working_path if getattr(ndxplorer, "working_path", None) else os.getcwd()
    except Exception:
        base = os.getcwd()
    return os.path.join(base, f"ndxplorer_figure{suffix}")


def _find_managing_layout(widget) -> Optional[QtWidgets.QLayout]:
    """Return the (possibly nested) layout that directly manages ``widget``.

    ``widget.parentWidget().layout()`` only gives the parent's *top* layout; the
    anchor button can sit in a grid nested several box-layouts deep, so search.
    """
    parent = widget.parentWidget()
    if parent is None:
        return None
    stack = [parent.layout()] if parent.layout() is not None else []
    while stack:
        lay = stack.pop()
        if lay is None:
            continue
        if lay.indexOf(widget) != -1:
            return lay
        for i in range(lay.count()):
            child = lay.itemAt(i).layout()
            if child is not None:
                stack.append(child)
    return None


def add_publication_export_button(ndxplorer) -> Optional[QtWidgets.QToolButton]:
    """Add a 'Publication export…' tool button next to the screenshot button.

    Returns the created button, or None if the screenshot button (our anchor)
    or its managing layout cannot be found.
    """
    anchor = getattr(ndxplorer, "toolButton_screenshot", None)
    if anchor is None:
        return None
    layout = _find_managing_layout(anchor)
    if layout is None:
        return None

    btn = QtWidgets.QToolButton(anchor.parentWidget())
    btn.setText("Export…")
    btn.setToolTip("Publication export… (vector PDF/SVG or high-DPI PNG)")
    btn.setObjectName("toolButton_publication_export")
    btn.setMinimumSize(QtCore.QSize(28, 18))
    btn.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Fixed)
    btn.clicked.connect(lambda: open_publication_export(ndxplorer))

    # Insert right after the screenshot button in whatever layout owns it.
    if isinstance(layout, QtWidgets.QGridLayout):
        idx = layout.indexOf(anchor)
        row, col, _rs, _cs = layout.getItemPosition(idx)
        layout.addWidget(btn, layout.rowCount(), col)
    elif isinstance(layout, QtWidgets.QBoxLayout):
        layout.insertWidget(layout.indexOf(anchor) + 1, btn)
    else:
        layout.addWidget(btn)
    ndxplorer.toolButton_publication_export = btn
    return btn


__all__ = [
    "export_publication_figure",
    "open_publication_export",
    "add_publication_export_button",
    "PublicationExportDialog",
]
