"""Publication-quality re-render of the ndX plot view.

The interactive plots are emtk (screen-tuned). For print/publication the
*same data* is re-drawn with :mod:`emtk.figure`: a 2D density panel with its
X/Y marginal histograms and a colour bar, with real axis labels and ticks,
exported as vector (PDF/SVG) or high-DPI raster. No plotting library is
involved -- emtk's own painters write the PNG, the SVG and the PDF.

The renderer (:func:`render_publication_figure`) is pure and headless -- it
takes arrays, not a GUI object -- so the app, a script and a test call it alike.
"""

from __future__ import annotations

from typing import Optional, Tuple

import numpy as np
from emtk.figure import Axes, Figure, colorbar_space

from ..i18n import mark

Marginal = Optional[Tuple[np.ndarray, np.ndarray]]  # (edges, counts)

#: What the export offers: label -> (file suffix, is vector, media type). The
#: Qt dialog and the emtk app's dialog both list these. The labels are the
#: keys; whoever lists them translates them where they are shown.
EXPORT_FORMATS = {
    mark("PDF (vector)"): (".pdf", True, "application/pdf"),
    mark("SVG (vector)"): (".svg", True, "image/svg+xml"),
    mark("PNG (raster)"): (".png", False, "image/png"),
}

#: Logical pixels per inch of ``figsize`` (the CSS pixel; emtk's vector files
#: use the same, so a 6-inch figure is 6 inches in the PDF).
_PX_PER_INCH = 96.0


def figure_bytes(fig: Figure, suffix: str, *, dpi: int = 300, transparent: bool = False) -> bytes:
    """The figure as the bytes of a file of type *suffix* (``".pdf"``, ``".svg"``, ``".png"``).

    In memory, so a browser (where a save is a download) gets the same file a
    desktop writes. ``dpi`` sets the PNG resolution (vector files are sized in
    inches). ``transparent`` is accepted for the export dialog and has no
    effect: the figure is drawn on white paper.
    """
    del transparent
    return fig.to_bytes(suffix, dpi=dpi)


def draw_density_with_marginals(
    fig: Figure,
    density: Axes,
    top: Optional[Axes],
    right: Optional[Axes],
    H: np.ndarray,
    x_edges: np.ndarray,
    y_edges: np.ndarray,
    *,
    x_marginal: Marginal = None,
    y_marginal: Marginal = None,
    x_label: str = "",
    y_label: str = "",
    colorbar_label: str = "counts",
    cmap: str = "viridis",
    x_log: bool = False,
    y_log: bool = False,
    z_log: bool = False,
) -> None:
    """Draw ndX's density panel -- 2D histogram, X/Y marginals, colour bar --
    into *density* and the marginal panels *top* / *right* of the caller's
    figure (either marginal panel ``None``: that marginal is skipped).

    The panels come from the caller's grid, so a report page composes this
    block beside its own panels instead of re-drawing it: one composer, the
    interactive view and the print view stay the same picture.
    """
    H = np.asarray(H, dtype=float)
    x_edges = np.asarray(x_edges, dtype=float)
    y_edges = np.asarray(y_edges, dtype=float)
    xlim = (float(x_edges[0]), float(x_edges[-1]))
    ylim = (float(y_edges[0]), float(y_edges[-1]))
    low, high = _density_levels(H, z_log)
    density.mesh(x_edges, y_edges, H, colormap=cmap, levels=(low, high), log=z_log)
    density.set_labels(x=x_label, y=y_label)
    density.set_log(x=x_log, y=y_log)
    density.set_xlim(*xlim)
    density.set_ylim(*ylim)
    # The colour bar goes beside the right-most panel of the density's row.
    (right or density).add_colorbar(colorbar_label, low, high, colormap=cmap, log=z_log)

    if top is not None and x_marginal is not None:
        _draw_marginal(top, x_marginal, horizontal=False)
        top.set_log(x=x_log)
        top.set_xlim(*xlim)
        top.hide_tick_labels(x=True)
        top.set_labels(y="count")
    if right is not None and y_marginal is not None:
        _draw_marginal(right, y_marginal, horizontal=True)
        right.set_log(y=y_log)
        right.set_ylim(*ylim)
        right.hide_tick_labels(y=True)
        right.set_labels(x="count")
    del fig  # the panels carry the drawing; kept for a stable call signature


def render_publication_figure(
    H: np.ndarray,
    x_edges: np.ndarray,
    y_edges: np.ndarray,
    *,
    x_marginal: Marginal = None,
    y_marginal: Marginal = None,
    x_label: str = "",
    y_label: str = "",
    colorbar_label: str = "counts",
    cmap: str = "viridis",
    x_log: bool = False,
    y_log: bool = False,
    z_log: bool = False,
    title: Optional[str] = None,
    figsize: Tuple[float, float] = (6.0, 6.0),
    dpi: int = 300,
    with_marginals: bool = True,
) -> Figure:
    """Compose a publication-quality figure from histogram arrays.

    Parameters
    ----------
    H : np.ndarray
        2D histogram shaped ``(n_y, n_x)`` (the layout Histogram2D stores).
    x_edges, y_edges : np.ndarray
        Bin edges for the X and Y axes (length ``n_x+1`` / ``n_y+1``).
    x_marginal, y_marginal : (edges, counts) tuple, optional
        Marginal histograms drawn above / to the right of the density panel.
    x_label, y_label, colorbar_label : str
        Axis and colorbar labels.
    cmap : str
        Colormap name for the density panel (:mod:`emtk.colormaps`).
    x_log, y_log : bool
        Log-scale the corresponding axes.
    z_log : bool
        Log-scale (LogNorm) the density colour mapping.
    title : str, optional
        Figure title.
    figsize : (float, float)
        Figure size in inches.
    dpi : int
        Kept for callers; the raster resolution is chosen when the figure is
        written (:func:`figure_bytes`).
    with_marginals : bool
        When False, draw only the 2D density panel + colorbar.

    Returns
    -------
    emtk.figure.Figure
        Write it with :func:`figure_bytes` or ``fig.save(path, dpi=...)``
        (``.png``, ``.svg``, ``.pdf``).
    """
    H = np.asarray(H, dtype=float)
    x_edges = np.asarray(x_edges, dtype=float)
    y_edges = np.asarray(y_edges, dtype=float)
    size = (int(round(figsize[0] * _PX_PER_INCH)), int(round(figsize[1] * _PX_PER_INCH)))
    del dpi  # a raster export's resolution, chosen when the figure is written

    draw_marginals = bool(
        with_marginals and x_marginal is not None and y_marginal is not None
    )
    if draw_marginals:
        # [top marginal][ -- ]
        # [density     ][right marginal | colour bar]
        side = size[0] * 1.0 / 5.0 + colorbar_space(z_log)
        fig = Figure(rows=2, cols=2, size=size, title=title or "",
                     width_ratios=[size[0] - side, side], height_ratios=[1.0, 4.0])
        density, top, right = fig.ax(1, 0), fig.ax(0, 0), fig.ax(1, 1)
        fig.ax(0, 1).hide()
    else:
        fig = Figure(rows=1, cols=1, size=size, title=title or "")
        density, top, right = fig.ax(), None, None

    draw_density_with_marginals(
        fig, density, top if draw_marginals else None, right if draw_marginals else None,
        H, x_edges, y_edges,
        x_marginal=x_marginal, y_marginal=y_marginal,
        x_label=x_label, y_label=y_label, colorbar_label=colorbar_label,
        cmap=cmap, x_log=x_log, y_log=y_log, z_log=z_log,
    )
    return fig


def _density_levels(H: np.ndarray, z_log: bool) -> Tuple[float, float]:
    """Colour range: the data's, from the smallest positive count on a log scale."""
    if z_log:
        positive = H[H > 0]
        vmin = float(positive.min()) if positive.size else 1.0
        vmax = float(H.max()) if H.size else 1.0
        return vmin, max(vmax, vmin * 10)
    vmax = float(H.max()) if H.size else 1.0
    return 0.0, max(vmax, 1.0)


def _draw_marginal(ax, marginal: Marginal, *, horizontal: bool) -> None:
    """A marginal histogram from an ``(edges, counts)`` tuple: one filled bar per bin."""
    if marginal is None:
        return
    edges, counts = np.asarray(marginal[0], dtype=float), np.asarray(marginal[1], dtype=float)
    centers = 0.5 * (edges[:-1] + edges[1:])
    ax.bars(centers, counts, width=np.diff(edges), color="C0", alpha=0.85,
            horizontal=horizontal)


__all__ = ["EXPORT_FORMATS", "figure_bytes", "render_publication_figure",
           "draw_density_with_marginals"]
