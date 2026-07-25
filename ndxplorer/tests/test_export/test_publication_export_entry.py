"""Headless tests for the publication-export entry point (no dialog/Qt needed)."""
import tempfile
import types
from pathlib import Path

import numpy as np
import pytest

from ndxplorer.core.histograms import Histogram1D, Histogram2D
from ndxplorer.ui.publication_export_dialog import export_publication_figure


def _stub_ndxplorer(object_form: bool = True):
    """A minimal duck-typed NDXplorer carrying a computed 2D + marginals."""
    rng = np.random.default_rng(3)
    x = rng.normal(3.5, 0.4, 4000)
    y = np.clip(rng.normal(0.4, 0.15, 4000), 0, 1)
    x_edges = np.linspace(2.0, 5.0, 41)
    y_edges = np.linspace(0.0, 1.0, 31)
    H, _, _ = np.histogram2d(x, y, bins=[x_edges, y_edges])
    H = H.T  # (n_y, n_x) like Histogram2D
    xcnt = np.histogram(x, bins=x_edges)[0]
    ycnt = np.histogram(y, bins=y_edges)[0]

    if object_form:
        hist = {
            "2d": Histogram2D(H=H, x_edges=x_edges, y_edges=y_edges),
            "x": Histogram1D(edges=x_edges, counts=xcnt),
            "y": Histogram1D(edges=y_edges, counts=ycnt),
        }
    else:
        hist = {
            "2d": (H, x_edges, y_edges),
            "x": (x_edges, xcnt),
            "y": (y_edges, ycnt),
        }

    pc = types.SimpleNamespace(
        x_label="Tau (green)", y_label="Proximity ratio",
        scale_x="linear", scale_y="linear",
    )
    return types.SimpleNamespace(_histogram=hist, plot_control=pc, working_path=None)


def test_export_pdf_vector():
    ndx = _stub_ndxplorer(object_form=True)
    with tempfile.TemporaryDirectory() as tmp:
        out = export_publication_figure(ndx, Path(tmp) / "fig.pdf")
        assert out.read_bytes()[:4] == b"%PDF"


def test_export_png_high_dpi():
    from PIL import Image

    ndx = _stub_ndxplorer(object_form=True)
    with tempfile.TemporaryDirectory() as tmp:
        out = export_publication_figure(ndx, Path(tmp) / "fig.png", dpi=300)
        assert Image.open(out).size[0] >= 1000


def test_export_works_from_tuple_storage():
    """The entry must handle the tuple _histogram form as well as objects."""
    ndx = _stub_ndxplorer(object_form=False)
    with tempfile.TemporaryDirectory() as tmp:
        out = export_publication_figure(ndx, Path(tmp) / "fig.svg")
        assert "<svg" in out.read_text(errors="ignore")[:512]


def test_export_without_marginals():
    ndx = _stub_ndxplorer(object_form=True)
    with tempfile.TemporaryDirectory() as tmp:
        out = export_publication_figure(ndx, Path(tmp) / "fig.pdf", with_marginals=False)
        assert out.exists()


def test_export_raises_without_2d():
    ndx = types.SimpleNamespace(_histogram={}, plot_control=types.SimpleNamespace(), working_path=None)
    with tempfile.TemporaryDirectory() as tmp:
        with pytest.raises(ValueError):
            export_publication_figure(ndx, Path(tmp) / "fig.pdf")


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-q"])
