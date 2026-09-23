"""Utilities for exporting histogram data to clipboard."""

from __future__ import annotations

import io
import json
from typing import TYPE_CHECKING

import numpy as np

from ..logging_config import logging

if TYPE_CHECKING:  # pragma: no cover
    from ..core.plot_main import NDXplorer


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


def _set_clipboard(text: str) -> None:
    from qtpy import QtWidgets

    QtWidgets.QApplication.clipboard().setText(text)


def histograms_1d_text(x_hist, y_hist) -> str:
    """The X and Y marginals as tab-separated text: histogram, bin centre, count.

    Each histogram is ``(bin_edges, counts)``. This is what "Copy 1D Histograms
    (CSV)" puts on the clipboard, in both GUIs.
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


def copy_1d_histograms(ndxplorer: "NDXplorer") -> None:
    """Copy X/Y 1D histogram data as TSV to clipboard."""
    logging.debug("copy_1d_hists_to_clipboard_csv")
    try:
        x_hist = ndxplorer._histogram["x"]
        y_hist = ndxplorer._histogram["y"]
    except KeyError as exc:
        logging.error("Histogram data missing: %s", exc)
        return

    _set_clipboard(histograms_1d_text(x_hist, y_hist))
    logging.info("1D histograms copied to clipboard as TSV.")


def copy_2d_hist_json(ndxplorer: "NDXplorer") -> None:
    """Copy 2D histogram data as JSON."""
    logging.debug("copy_2d_hist_to_clipboard_json")
    try:
        H, x_edges, y_edges = ndxplorer._histogram["2d"]
    except KeyError as exc:
        logging.error("No 2D histogram data available: %s", exc)
        return

    data_dict = {
        "H": H.tolist(),
        "x_edges": x_edges.tolist(),
        "y_edges": y_edges.tolist(),
    }
    _set_clipboard(json.dumps(data_dict, indent=2))
    logging.info("2D histogram data copied to clipboard (JSON).")


def copy_2d_hist_csv(ndxplorer: "NDXplorer") -> None:
    """Copy 2D histogram data as TSV."""
    logging.debug("copy_2d_hist_to_clipboard_csv: %s", ndxplorer._histogram)
    try:
        H, x_edges, y_edges = ndxplorer._histogram["2d"]
    except KeyError as exc:
        logging.error("No 2D histogram data available: %s", exc)
        return

    text = histogram_2d_text(H, x_edges, y_edges)
    if text is None:
        logging.error("H is not 2D! Shape: %s, Type: %s",
                      getattr(H, 'shape', 'no shape'), type(H))
        return
    _set_clipboard(text)
    logging.info("2D histogram data copied to clipboard as TSV.")
