"""Publication-quality Matplotlib re-render of the NDXplorer plot view.

The interactive plots are pyqtgraph (screen-tuned). For print/publication we
re-draw the *same data* in Matplotlib: a 2D density panel with its X/Y marginal
histograms and a colorbar, with real axis labels, ticks and fonts, exported as
vector (PDF/SVG) or high-DPI raster.

The renderer core (:func:`render_publication_figure`) is pure and headless — it
takes arrays, not a GUI object — so it is unit-testable without Qt. The thin
:func:`render_current_view` adapter pulls those arrays off a live NDXplorer.
"""

from __future__ import annotations

from typing import Optional, Sequence, Tuple

import numpy as np

from ..logging_config import logging

# Non-interactive backend; safe to import without a display or running GUI.
import matplotlib
matplotlib.use("Agg", force=False)
from matplotlib.figure import Figure
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.colors import LogNorm, Normalize


Marginal = Optional[Tuple[np.ndarray, np.ndarray]]  # (edges, counts)

#: What the export offers: label -> (file suffix, is vector, media type). The
#: Qt dialog and the emtk app's dialog both list these.
EXPORT_FORMATS = {
    "PDF (vector)": (".pdf", True, "application/pdf"),
    "SVG (vector)": (".svg", True, "image/svg+xml"),
    "PNG (raster)": (".png", False, "image/png"),
}


def figure_bytes(fig: Figure, suffix: str, *, dpi: int = 300, transparent: bool = False) -> bytes:
    """The figure as the bytes of a file of type *suffix* (``".pdf"``, ``".svg"``, ``".png"``).

    In memory, so a browser (where a save is a download) gets the same file a
    desktop writes; ``bbox_inches="tight"`` as the file export does.
    """
    import io

    buffer = io.BytesIO()
    fig.savefig(buffer, format=suffix.lstrip(".").lower(), dpi=dpi, transparent=transparent,
                bbox_inches="tight")
    return buffer.getvalue()


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
        Matplotlib colormap name for the density panel.
    x_log, y_log : bool
        Log-scale the corresponding axes.
    z_log : bool
        Log-scale (LogNorm) the density colour mapping.
    title : str, optional
        Figure title.
    figsize : (float, float)
        Figure size in inches.
    dpi : int
        Raster resolution (ignored for vector formats but stored on the figure).
    with_marginals : bool
        When False, draw only the 2D density panel + colorbar.

    Returns
    -------
    matplotlib.figure.Figure
        A figure with an Agg canvas attached; call ``fig.savefig(path)`` for
        PNG/PDF/SVG, then close it.
    """
    H = np.asarray(H, dtype=float)
    x_edges = np.asarray(x_edges, dtype=float)
    y_edges = np.asarray(y_edges, dtype=float)

    fig = Figure(figsize=figsize, dpi=dpi)
    FigureCanvasAgg(fig)

    draw_marginals = bool(
        with_marginals and x_marginal is not None and y_marginal is not None
    )

    if draw_marginals:
        # 3x3 grid: [top marginal][.] , [density][right marginal][colorbar]
        gs = fig.add_gridspec(
            2, 3,
            width_ratios=[4.0, 1.0, 0.25],
            height_ratios=[1.0, 4.0],
            wspace=0.05, hspace=0.05,
        )
        ax_density = fig.add_subplot(gs[1, 0])
        ax_top = fig.add_subplot(gs[0, 0], sharex=ax_density)
        ax_right = fig.add_subplot(gs[1, 1], sharey=ax_density)
        ax_cbar = fig.add_subplot(gs[1, 2])
    else:
        gs = fig.add_gridspec(1, 2, width_ratios=[20.0, 1.0], wspace=0.05)
        ax_density = fig.add_subplot(gs[0, 0])
        ax_top = ax_right = None
        ax_cbar = fig.add_subplot(gs[0, 1])

    norm = _density_norm(H, z_log)
    mesh = ax_density.pcolormesh(x_edges, y_edges, H, cmap=cmap, norm=norm, shading="auto")
    ax_density.set_xlabel(x_label)
    ax_density.set_ylabel(y_label)
    if x_log:
        ax_density.set_xscale("log")
    if y_log:
        ax_density.set_yscale("log")
    ax_density.set_xlim(x_edges[0], x_edges[-1])
    ax_density.set_ylim(y_edges[0], y_edges[-1])

    cbar = fig.colorbar(mesh, cax=ax_cbar)
    cbar.set_label(colorbar_label)

    if draw_marginals:
        _draw_marginal(ax_top, x_marginal, orientation="vertical", log_axis=x_log)
        _draw_marginal(ax_right, y_marginal, orientation="horizontal", log_axis=y_log)
        # Hide the shared tick labels on the marginal edges facing the density.
        for lbl in ax_top.get_xticklabels():
            lbl.set_visible(False)
        for lbl in ax_right.get_yticklabels():
            lbl.set_visible(False)
        ax_top.set_ylabel("count")
        ax_right.set_xlabel("count")

    if title:
        fig.suptitle(title)

    return fig


def _density_norm(H: np.ndarray, z_log: bool) -> Normalize:
    if z_log:
        positive = H[H > 0]
        vmin = positive.min() if positive.size else 1.0
        vmax = H.max() if H.size else 1.0
        return LogNorm(vmin=vmin, vmax=max(vmax, vmin * 10))
    vmax = H.max() if H.size else 1.0
    return Normalize(vmin=0.0, vmax=max(vmax, 1.0))


def _draw_marginal(ax, marginal: Marginal, *, orientation: str, log_axis: bool) -> None:
    """Draw a stepped marginal histogram from an (edges, counts) tuple."""
    if marginal is None:
        return
    edges, counts = np.asarray(marginal[0], dtype=float), np.asarray(marginal[1], dtype=float)
    centers = 0.5 * (edges[:-1] + edges[1:])
    if orientation == "vertical":
        ax.fill_between(centers, counts, step="mid", alpha=0.85, linewidth=0)
        if log_axis:
            ax.set_xscale("log")
    else:
        ax.fill_betweenx(centers, counts, step="mid", alpha=0.85, linewidth=0)
        if log_axis:
            ax.set_yscale("log")


def render_current_view(ndxplorer, *, dpi: int = 300, with_marginals: bool = True,
                        figsize: Tuple[float, float] = (6.0, 6.0)) -> Figure:
    """Build a publication figure from a live NDXplorer's current view.

    Reads the already-computed histograms off ``ndxplorer._histogram`` (handling
    both the Histogram-object and the tuple storage forms) plus axis labels,
    colormap and log-scale settings from the plot control.
    """
    from ..plotting.histograms import _as_1d_arrays, _as_2d_arrays

    hist = getattr(ndxplorer, "_histogram", {}) or {}
    two_d = _as_2d_arrays(hist.get("2d"))
    if two_d is None:
        raise ValueError("No 2D histogram is available to export; update the plot first.")
    H, x_edges, y_edges = two_d

    def _marginal(key):
        arrs = _as_1d_arrays(hist.get(key))
        return (arrs[0], arrs[1]) if arrs is not None else None

    pc = getattr(ndxplorer, "plot_control", None)
    x_label = getattr(pc, "x_label", "") if pc is not None else ""
    y_label = getattr(pc, "y_label", "") if pc is not None else ""
    x_log = str(getattr(pc, "scale_x", "linear")) == "log"
    y_log = str(getattr(pc, "scale_y", "linear")) == "log"
    cmap = getattr(ndxplorer, "color_map_name", None) or getattr(ndxplorer, "cmap", None) or "viridis"

    logging.info("Rendering publication figure (%s vs %s, dpi=%s)", x_label, y_label, dpi)
    return render_publication_figure(
        H, x_edges, y_edges,
        x_marginal=_marginal("x"),
        y_marginal=_marginal("y"),
        x_label=x_label, y_label=y_label,
        cmap=str(cmap),
        x_log=x_log, y_log=y_log,
        dpi=dpi, with_marginals=with_marginals, figsize=figsize,
    )


__all__ = ["EXPORT_FORMATS", "figure_bytes", "render_publication_figure", "render_current_view"]
