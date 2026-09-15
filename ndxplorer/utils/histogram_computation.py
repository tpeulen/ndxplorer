"""The histograms a redraw needs, and the description of the axes they fill.

There used to be three ways to say what a histogram axis was set to -- a
dataclass whose bin fields were strings, a flat dict of two dozen keys, and five
arrays of bin edges -- and one function that had to work out which of them it
had been handed. :class:`Axis` is the one way.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np

from ..logging_config import logging


@dataclass
class Axis:
    """One histogram axis: which column, and how to bin it.

    An axis is a column, a bin count, a range and a scale -- a formula. Saying
    so is worth more than any amount of tuning: the bin index becomes a
    multiply (and a logarithm) rather than a binary search through an array of
    boundaries, which on a few million points is most of the cost of a redraw.

    The edge array is still built, but only for the plot -- to place ticks and
    to draw the steps. Nothing bins with it.
    """

    index: int
    bins: int
    lo: float
    hi: float
    scale: str = "linear"
    density: bool = False

    def __post_init__(self):
        self.index = int(self.index)
        self.bins = max(1, int(self.bins))
        self.lo, self.hi = float(self.lo), float(self.hi)
        if self.lo > self.hi:
            self.lo, self.hi = self.hi, self.lo
        if self.lo == self.hi:
            # All-equal data -- a parameter that was never fit. An empty
            # interval has no bins to put anything in.
            self.lo, self.hi = self.lo - 0.5, self.hi + 0.5
        # A logarithmic axis needs a positive lower bound. Below one the plot
        # draws linear whatever the control says, so bin it the way it is drawn
        # rather than silently binning against a different picture.
        self.scale = ("log" if str(self.scale).lower().startswith("log")
                      and self.lo > 0.0 else "linear")

    @property
    def edges(self) -> np.ndarray:
        """Where the bins fall -- ``bins + 1`` of them, for the plot."""
        space = np.geomspace if self.scale == "log" else np.linspace
        return space(self.lo, self.hi, self.bins + 1)

    def same_bins_as(self, other: "Axis") -> bool:
        """Whether two axes put their points in the same places.

        Four fields rather than a comparison of two edge arrays: this is asked
        on every redraw, to decide whether a marginal can be summed out of the
        map instead of filled again.
        """
        return (self.bins == other.bins and self.lo == other.lo
                and self.hi == other.hi and self.scale == other.scale)

    def normalise(self, counts: np.ndarray) -> np.ndarray:
        """``counts`` as a density, when this axis asks for one."""
        if not self.density:
            return counts
        total = counts.sum()
        return counts / (total * np.diff(self.edges)) if total > 0 else counts


@dataclass
class HistogramAxes:
    """The axes one redraw fills, and the column that weights them.

    ``x``/``y`` are the marginals and ``x2``/``y2`` the map. They are four axes
    rather than two because the 1-D and 2-D bin counts are separate settings in
    the interface.
    """

    x: Axis
    y: Axis
    x2: Axis
    y2: Axis
    z: Optional[Axis] = None
    weight: Optional[int] = None


def _spec(*axes: Axis) -> dict:
    """The keyword arguments :meth:`DataStore.histogram` takes for these axes."""
    return dict(bins=[a.bins for a in axes],
                range=[(a.lo, a.hi) for a in axes],
                scale=[a.scale for a in axes])


def compute_histograms(source, axes: HistogramAxes, keep=None, is_cancelled=None):
    """The histograms a redraw needs: x, y, optional z, and the 2-D map.

    Filled straight out of the :class:`tttrlib.DataStore`, from the columns in
    the dtypes they are stored in, with the row filter carried by the store's
    own selection -- one bit per row.

    What that removes, measured on this file (1.8M rows, 256 x 256, weighted):

    ==================================  ========
    step                                 time
    ==================================  ========
    gathering the columns into arrays     25 ms
    filling from those arrays            115 ms
    **filling from the store**           **33 ms**
    ==================================  ========

    The 115 ms was almost all memory: the arrays are float32 and the array fill
    takes float64, so every redraw copied about 80 MB to widen values that were
    then binned and thrown away. The store fill reads a float32 column as
    float32. The gather goes too -- a selection the fill already honours does
    not need the rows extracted first.

    :param source: the :class:`~ndxplorer.core.data_source.DataSource`
    :param axes: the :class:`HistogramAxes` to fill
    :param keep: optional per-row boolean filter, one entry per row of the table
    :param is_cancelled: called between histograms; return True to stop early

    :returns: ``{"x": (edges, counts), "y": ..., "z": ..., "2d": (H, xe, ye)}``
        with ``H`` shaped ``(n_y, n_x)``, which is the orientation the image
        item draws.
    """
    store = source.store

    def cancelled():
        return is_cancelled is not None and is_cancelled()

    # The population, once, in the store: the caller's row filter AND the rows
    # that carry a value on both plotted axes. Every histogram below reads the
    # same selection, which is what makes the marginals describe the population
    # the 2-D map shows rather than a larger one.
    if keep is not None:
        keep = np.asarray(keep, dtype=bool)
        if keep.shape[0] != store.n_rows():
            logging.warning("keep mask is %d rows, the table is %d; ignoring it",
                            keep.shape[0], store.n_rows())
            keep = None
    store.select(keep)
    store.where_finite([axes.x.index, axes.y.index], how="and")

    result = {}
    try:
        def fill(name, axis, weight):
            if axis is None or cancelled():
                return
            histogram = store.histogram(axis.index, weight=weight, **_spec(axis))
            counts = np.asarray(histogram.view(), dtype=np.float64)
            result[name] = (axis.edges, axis.normalise(counts))

        # A marginal of the map IS the map summed along the other axis, and
        # summing a 256 x 256 array is free next to another pass over two
        # million rows. It is only the same histogram when the 1-D and 2-D bins
        # agree -- they are separate settings -- so that is checked rather than
        # assumed, and the flow bins are included in the sum, because a row
        # whose y fell off the map still belongs in the x marginal.
        if not cancelled():
            histogram = store.histogram(axes.x2.index, axes.y2.index,
                                        weight=axes.weight,
                                        **_spec(axes.x2, axes.y2))
            H = np.asarray(histogram.view(), dtype=np.float64)
            share_x = axes.x.same_bins_as(axes.x2)
            share_y = axes.y.same_bins_as(axes.y2)
            if share_x or share_y:
                with_flow = np.asarray(histogram.view(True), dtype=np.float64)
                if share_x:
                    counts = with_flow.sum(axis=1)[1:-1]
                    result["x"] = (axes.x.edges, axes.x.normalise(counts))
                if share_y:
                    counts = with_flow.sum(axis=0)[1:-1]
                    result["y"] = (axes.y.edges, axes.y.normalise(counts))
            # (n_x, n_y) out, (n_y, n_x) in: the image item draws the transpose.
            result["2d"] = (H.T, axes.x2.edges, axes.y2.edges)

        if "x" not in result:
            fill("x", axes.x, axes.weight)
        if "y" not in result:
            fill("y", axes.y, axes.weight)
        # The z marginal is not weighted by itself: weighting an axis by the
        # quantity it plots turns its own distribution into that quantity's.
        if axes.z is not None:
            fill("z", axes.z,
                 None if axes.weight == axes.z.index else axes.weight)

        result["_count"] = int(store.n_selected())
    finally:
        # The selection belongs to whoever set it; a histogram is a question
        # about the data, not a change to it.
        store.select_all()

    return result
