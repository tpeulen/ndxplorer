"""GUI test: the publication-export button wires into the screenshot grid."""
import types

import pytest

from qtpy import QtWidgets

from ndxplorer.ui.publication_export_dialog import (
    add_publication_export_button,
    PublicationExportDialog,
)


@pytest.fixture(scope="module")
def qapp():
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])
    yield app


def test_button_added_next_to_screenshot(qapp):
    host = QtWidgets.QWidget()
    grid = QtWidgets.QGridLayout(host)
    screenshot = QtWidgets.QToolButton(host)
    grid.addWidget(screenshot, 0, 0)

    ndx = types.SimpleNamespace(toolButton_screenshot=screenshot)
    btn = add_publication_export_button(ndx)

    assert btn is not None
    assert btn.objectName() == "toolButton_publication_export"
    # It joined the same grid layout as the screenshot button.
    assert grid.indexOf(btn) != -1
    assert ndx.toolButton_publication_export is btn


def test_button_noop_without_anchor(qapp):
    ndx = types.SimpleNamespace(toolButton_screenshot=None)
    assert add_publication_export_button(ndx) is None


def test_dialog_options_defaults(qapp):
    dlg = PublicationExportDialog()
    opts = dlg.options()
    assert opts["suffix"] == ".pdf"
    assert opts["is_vector"] is True
    assert opts["with_marginals"] is True
    # DPI is disabled for the default vector format.
    assert dlg.spin_dpi.isEnabled() is False


def test_dialog_dpi_enabled_for_png(qapp):
    dlg = PublicationExportDialog()
    idx = dlg.combo_format.findText("PNG (raster)")
    dlg.combo_format.setCurrentIndex(idx)
    assert dlg.spin_dpi.isEnabled() is True
    assert dlg.options()["suffix"] == ".png"


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-q"])
