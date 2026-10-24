"""Headless tests for the publication-quality figure renderer."""
import tempfile
from pathlib import Path

import numpy as np
import pytest

from ndxplorer.export.publication_figure import render_publication_figure
from ndxplorer.export.image_export import export_image
from ndxplorer.export.models import SelectionExportPayload


@pytest.fixture
def hist_2d():
    rng = np.random.default_rng(0)
    x = rng.normal(3.5, 0.4, 5000)
    y = np.clip(rng.normal(0.4, 0.15, 5000), 0, 1)
    x_edges = np.linspace(2.0, 5.0, 41)
    y_edges = np.linspace(0.0, 1.0, 31)
    H, xe, ye = np.histogram2d(x, y, bins=[x_edges, y_edges])
    # Store as (n_y, n_x) like Histogram2D.
    xc, xcnt = x_edges, np.histogram(x, bins=x_edges)[0]
    yc, ycnt = y_edges, np.histogram(y, bins=y_edges)[0]
    return H.T, x_edges, y_edges, (xc, xcnt), (yc, ycnt)


def test_render_returns_figure_with_expected_axes(hist_2d):
    H, xe, ye, xm, ym = hist_2d
    fig = render_publication_figure(
        H, xe, ye, x_marginal=xm, y_marginal=ym,
        x_label="Tau (green)", y_label="Proximity ratio",
    )
    # top marginal, (empty corner), density, right marginal -- the colour bar
    # sits beside the right marginal, in its cell.
    from emtk.figure import Figure

    assert isinstance(fig, Figure)
    assert (fig.rows, fig.cols) == (2, 2)
    assert fig.ax(0, 1).hidden and fig.ax(1, 1).colorbar["label"] == "counts"


def test_render_without_marginals(hist_2d):
    H, xe, ye, _, _ = hist_2d
    fig = render_publication_figure(H, xe, ye, with_marginals=False)
    # density only, its colour bar beside it.
    assert len(fig.axes) == 1 and fig.ax().colorbar is not None


def test_render_exports_vector_pdf_and_svg(hist_2d):
    H, xe, ye, xm, ym = hist_2d
    fig = render_publication_figure(H, xe, ye, x_marginal=xm, y_marginal=ym)
    with tempfile.TemporaryDirectory() as tmp:
        pdf = Path(tmp) / "fig.pdf"
        svg = Path(tmp) / "fig.svg"
        export_image(SelectionExportPayload(figure=fig), pdf)
        export_image(SelectionExportPayload(figure=fig), svg)
        assert pdf.read_bytes()[:4] == b"%PDF"
        assert "<svg" in svg.read_text(errors="ignore")[:512]


def test_render_high_dpi_png(hist_2d):
    from PIL import Image

    H, xe, ye, xm, ym = hist_2d
    fig = render_publication_figure(H, xe, ye, x_marginal=xm, y_marginal=ym, figsize=(6, 6))
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "fig.png"
        export_image(SelectionExportPayload(figure=fig), path, dpi=300)
        img = Image.open(path)
        # 6in @ 300dpi ~= 1800px (minus tight bbox); must be clearly hi-res.
        assert img.size[0] >= 1500


def test_render_log_scales_do_not_crash(hist_2d):
    H, xe, ye, xm, ym = hist_2d
    fig = render_publication_figure(
        H, xe, ye, x_marginal=xm, y_marginal=ym, z_log=True,
    )
    assert fig.ax(1, 1).colorbar["log"]
    assert fig.png_bytes()[:8] == b"\x89PNG\r\n\x1a\n"


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-q"])


def test_density_panel_draws_into_a_callers_grid(hist_2d):
    """The extractor: ndX's panel composes into another page's grid."""
    from emtk.figure import Figure
    from ndxplorer.export.publication_figure import draw_density_with_marginals

    H, xe, ye, xm, ym = hist_2d
    fig = Figure(rows=2, cols=2, size=(560, 420), height_ratios=[1.0, 4.0],
                 width_ratios=[440.0, 120.0])
    draw_density_with_marginals(fig, fig.ax(1, 0), fig.ax(0, 0), fig.ax(1, 1),
                                H, xe, ye, x_marginal=xm, y_marginal=ym,
                                x_label="E", y_label="S")
    fig.ax(0, 1).hide()
    pdf = fig.pdf_bytes()
    assert pdf[:4] == b"%PDF" and b"%%EOF" in pdf[-32:]
