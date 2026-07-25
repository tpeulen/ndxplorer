"""Tests for the image export path (publication-quality figures).

Exercises the current API — ``export_image(payload, path, ...)`` and the
``save_selection(..., format='image')`` facade — covering the two things that
make an export "publication quality": high-DPI raster output and true vector
output (SVG/PDF via Matplotlib ``savefig``).
"""
import tempfile
from pathlib import Path

import numpy as np
import pytest

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from ndxplorer.export import api as export_api
from ndxplorer.export.image_export import export_image
from ndxplorer.export.models import SelectionExportPayload, ExportValidationError


@pytest.fixture
def figure():
    """A small Matplotlib figure with a known size for DPI assertions."""
    fig, ax = plt.subplots(figsize=(4, 3))
    ax.plot(np.arange(10), np.arange(10) ** 2)
    ax.set_xlabel("x")
    ax.set_ylabel("y")
    yield fig
    plt.close(fig)


def test_export_png_high_dpi(figure):
    """A 4x3in figure at 300 dpi yields a 1200x900 raster (bbox may pad)."""
    from PIL import Image

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "fig.png"
        # bbox_inches='tight' is applied inside; disable padding effect by not
        # asserting exact size, only that dpi scaling clearly took effect.
        export_image(SelectionExportPayload(figure=figure), path, dpi=300)
        assert path.exists()
        img = Image.open(path)
        assert img.format == "PNG"
        # At 300 dpi the raster must be far larger than a 100 dpi one.
        assert img.size[0] >= 1000 and img.size[1] >= 700


def test_export_png_dpi_scales_resolution(figure):
    """Higher dpi must produce more pixels for the same figure."""
    from PIL import Image

    with tempfile.TemporaryDirectory() as tmp:
        low = Path(tmp) / "low.png"
        high = Path(tmp) / "high.png"
        export_image(SelectionExportPayload(figure=figure), low, dpi=100)
        export_image(SelectionExportPayload(figure=figure), high, dpi=300)
        w_low = Image.open(low).size[0]
        w_high = Image.open(high).size[0]
        assert w_high > 2 * w_low


def test_export_svg_is_vector(figure):
    """SVG export must be real vector XML, not a rasterised blob."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "fig.svg"
        export_image(SelectionExportPayload(figure=figure), path)
        assert path.exists()
        head = path.read_text(errors="ignore")[:512]
        assert "<svg" in head
        # Vector plots carry <path> geometry rather than an <image> bitmap.
        assert "<path" in path.read_text(errors="ignore")


def test_export_pdf_is_vector(figure):
    """PDF export must be a real PDF document."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "fig.pdf"
        export_image(SelectionExportPayload(figure=figure), path)
        assert path.exists()
        assert path.read_bytes()[:4] == b"%PDF"


def test_export_transparent(figure):
    """Transparent background is honoured for raster output."""
    from PIL import Image

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "fig.png"
        export_image(SelectionExportPayload(figure=figure), path, dpi=150, transparent=True)
        img = Image.open(path)
        assert img.mode in ("RGBA", "LA", "P")


def test_save_selection_image_facade(figure):
    """The public save_selection facade routes image exports with options."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "fig.png"
        out = export_api.save_selection(
            SelectionExportPayload(figure=figure, name="demo"),
            path,
            options={"dpi": 200},
            write_manifest_file=False,
        )
        assert Path(out).exists()


def test_export_requires_drawable():
    """A payload with no figure/image/pixmap is rejected, not silently empty."""
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "fig.png"
        with pytest.raises((ExportValidationError, ValueError)):
            export_api.save_selection(SelectionExportPayload(), path, write_manifest_file=False)


def test_export_qimage_png():
    """A QImage payload is saved via its .save() method when Qt is available."""
    qtgui = pytest.importorskip("qtpy.QtGui")
    qtwidgets = pytest.importorskip("qtpy.QtWidgets")
    app = qtwidgets.QApplication.instance() or qtwidgets.QApplication([])
    img = qtgui.QImage(64, 48, qtgui.QImage.Format_RGB32)
    img.fill(0xFF3366)

    from PIL import Image

    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "qimg.png"
        export_image(SelectionExportPayload(image=img), path)
        assert path.exists()
        assert Image.open(path).size == (64, 48)


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-q"])
