"""Histogram data as text, for the clipboard ("Copy 1D/2D Histograms")."""

from __future__ import annotations

import io

import numpy as np


def _fmt_num(v: float) -> str:
    """Format numbers with high precision; use scientific for very small/large."""
    try:
        if isinstance(v, (int, np.integer)):
            return f"{int(v)}"
        if np.isfinite(v) and np.isclose(v, round(v), rtol=0.0, atol=1e-12):
            return f"{int(round(v))}"
        return f"{float(v):.8g}"
    except Exception:
        return str(v)


def histograms_1d_text(x_hist, y_hist) -> str:
    """The X and Y marginals as tab-separated text: histogram, bin centre, count.

    Each histogram is ``(bin_edges, counts)``. This is what "Copy 1D Histograms
    (CSV)" puts on the clipboard.
    """
    output = io.StringIO()
    output.write("Histogram\tBinCenter\tCount\n")
    for label, hist in (("X", x_hist), ("Y", y_hist)):
        bin_edges, counts = (np.asarray(v) for v in hist)
        bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
        for center, count in zip(bin_centers, counts):
            output.write(f"{label}\t{_fmt_num(center)}\t{_fmt_num(count)}\n")
    return output.getvalue()


def histogram_2d_text(H, x_edges, y_edges):
    """The 2-D histogram as tab-separated text, y rows by x columns.

    ``H`` is ``(n_y, n_x)``, row 0 at the lowest y. The first row holds the x
    bin centres, the first column the y bin centres. Returns ``None`` when *H*
    is not 2-D. This is what "Copy 2D Histogram (CSV)" puts on the clipboard.
    """
    H = np.asarray(H)
    if H.ndim != 2:
        return None
    x_edges, y_edges = np.asarray(x_edges), np.asarray(y_edges)
    x_centers = (x_edges[:-1] + x_edges[1:]) / 2
    y_centers = (y_edges[:-1] + y_edges[1:]) / 2
    output = io.StringIO()
    output.write("\t".join(["y/x"] + [_fmt_num(x) for x in x_centers]) + "\n")
    # ``H`` is (n_y, n_x): the row index is y and the column index is x.
    for j, y in enumerate(y_centers):
        cells = [_fmt_num(y)] + [_fmt_num(H[j, i]) for i in range(len(x_centers))]
        output.write("\t".join(cells) + "\n")
    return output.getvalue()
