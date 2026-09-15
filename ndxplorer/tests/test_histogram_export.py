"""What lands on the clipboard is what is on the screen.

A copied histogram leaves the program: it goes into a spreadsheet, a paper
figure, another analysis. There is no later stage that can notice it came out
transposed, so the orientation is checked here with a **non-square** histogram
whose every cell is identifiable -- ``10 * x_bin + y_bin`` -- because a square
one cannot show a transpose and a constant one cannot show anything at all.

``H`` is stored as ``(n_y, n_x)``: the orientation the image item draws, and the
one ``Histogram2D.validate`` enforces. The TSV writer indexed it x-first, which
exported the transpose on the square default binning and raised an uncaught
IndexError on an image histogram, where the two axes have a bin per pixel and
are rarely the same size.
"""

from __future__ import annotations

import numpy as np
import pytest

from ndxplorer.core.histograms import Histogram1D, Histogram2D
from ndxplorer.utils.histogram_export import (copy_1d_histograms,
                                              copy_2d_hist_csv,
                                              copy_2d_hist_json)

pytest.importorskip("qtpy.QtWidgets")


@pytest.fixture(scope="module")
def app():
    from qtpy import QtWidgets

    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


@pytest.fixture
def clipboard(app):
    from qtpy import QtWidgets

    return QtWidgets.QApplication.clipboard()


class _Explorer:
    """The one attribute the exporters read."""

    def __init__(self, histogram):
        self._histogram = histogram


def _identifiable_map(n_x: int, n_y: int) -> Histogram2D:
    """A map whose every cell says which bin it is: ``10 * x + y``."""
    H = np.array([[10 * i + j for i in range(n_x)] for j in range(n_y)], dtype=float)
    hist = Histogram2D(H=H,
                       x_edges=np.arange(n_x + 1, dtype=float),
                       y_edges=np.arange(n_y + 1, dtype=float))
    assert hist.validate(), "the fixture itself has to be the (n_y, n_x) layout"
    return hist


@pytest.mark.parametrize("n_x, n_y", [(4, 3), (3, 4), (5, 5), (1, 6), (6, 1)])
def test_the_2d_tsv_is_not_transposed(clipboard, n_x, n_y):
    explorer = _Explorer({"2d": _identifiable_map(n_x, n_y)})
    copy_2d_hist_csv(explorer)

    rows = [line.split("\t") for line in clipboard.text().strip().split("\n")]
    header, body = rows[0], rows[1:]

    assert header[0] == "y/x"
    assert len(header) == n_x + 1, "one column per x bin, plus the row label"
    assert len(body) == n_y, "one row per y bin"

    for j, row in enumerate(body):
        for i, cell in enumerate(row[1:]):
            assert float(cell) == 10 * i + j, (
                f"cell (x={i}, y={j}) holds {cell}; the table is transposed")


def test_the_2d_tsv_labels_the_bin_centres(clipboard):
    explorer = _Explorer({"2d": _identifiable_map(3, 2)})
    copy_2d_hist_csv(explorer)

    rows = [line.split("\t") for line in clipboard.text().strip().split("\n")]
    assert [float(c) for c in rows[0][1:]] == [0.5, 1.5, 2.5]
    assert [float(r[0]) for r in rows[1:]] == [0.5, 1.5]


def test_a_non_square_map_copies_at_all(clipboard):
    """An image histogram is one bin per pixel and the two axes differ; the
    x-first indexing raised IndexError here and the clipboard stayed stale."""
    clipboard.setText("previous contents")
    explorer = _Explorer({"2d": _identifiable_map(64, 32)})
    copy_2d_hist_csv(explorer)
    assert clipboard.text() != "previous contents"


def test_the_2d_json_keeps_the_stored_layout(clipboard):
    import json

    hist = _identifiable_map(4, 3)
    copy_2d_hist_json(_Explorer({"2d": hist}))
    payload = json.loads(clipboard.text())

    np.testing.assert_array_equal(np.asarray(payload["H"]), hist.H)
    assert len(payload["x_edges"]) == 5
    assert len(payload["y_edges"]) == 4


def test_the_1d_tsv_holds_both_marginals_at_their_bin_centres(clipboard):
    explorer = _Explorer({
        "x": Histogram1D(edges=np.array([0.0, 1.0, 2.0]), counts=np.array([7.0, 8.0])),
        "y": Histogram1D(edges=np.array([0.0, 2.0, 4.0]), counts=np.array([1.0, 2.0])),
    })
    copy_1d_histograms(explorer)

    rows = [line.split("\t") for line in clipboard.text().strip().split("\n")]
    assert rows[0] == ["Histogram", "BinCenter", "Count"]
    assert rows[1:] == [
        ["X", "0.5", "7"],
        ["X", "1.5", "8"],
        ["Y", "1", "1"],
        ["Y", "3", "2"],
    ]


def test_a_missing_histogram_is_reported_not_raised(clipboard):
    """These are menu actions; a copy with nothing computed yet must not take
    the window down."""
    empty = _Explorer({})
    copy_1d_histograms(empty)
    copy_2d_hist_csv(empty)
    copy_2d_hist_json(empty)
