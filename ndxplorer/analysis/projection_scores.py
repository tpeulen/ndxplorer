"""What makes a view of the burst table informative: the scores ndX ranks by.

Three scores, chosen in the ranking panel (:data:`METHODS`):

``populations`` (*Separation*, the default)
    How much of the burst cloud falls into clearly separated islands --
    ndX's density-valley score, :func:`ndxplorer.analysis.separation.find_populations`.
``correlation``
    Spearman's rank correlation of the two parameters (Spearman 1904,
    doi:10.2307/1412159), with ties given average ranks (Kendall & Gibbons
    1990).
``separation`` (*Classes*)
    How well the view keeps labelled bursts apart. VizRank (Leban, Zupan,
    Vidmar & Bratko 2006, doi:10.1007/s10618-005-0031-5) measures a
    projection by how well a k-nearest-neighbour classifier (Cover & Hart
    1967, doi:10.1109/TIT.1967.1053964), trained on the projected
    coordinates alone and evaluated leave-one-out, predicts each point's
    class. With uniform votes the probability it gives the true class is
    the share of a point's neighbours that share its class; ndX reports
    that share above chance as a chance-corrected agreement (Scott 1955,
    doi:10.1086/266577; Cohen 1960, doi:10.1177/001316446002000104).

Every view of one ranking is scored on the same random subsample of the table
(:class:`RankingTable`), so views compare on identical bursts. Columns that
cannot carry populations -- flags, the acquisition clock, columns that are the
same quantity as another, folds of another -- are set aside before pairs are
formed (:class:`ColumnSet`). The rankers (:class:`ProjectionRanker`,
:class:`ParameterRanker`) enumerate the views with
:mod:`ndxplorer.analysis.vizrank`.
"""

from __future__ import annotations

import itertools
import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from ..i18n import mark, tr
from .vizrank import ColumnRanker, PairRanker, RankRow

__all__ = [
    "MIN_K",
    "DEFAULT_MAX_ROWS",
    "MIN_DISTINCT",
    "DERIVED_RHO",
    "FUNCTION_ETA",
    "CURVE_ETA",
    "CLOCK_SHARE",
    "ETA_BINS",
    "METHODS",
    "METHOD_HELP",
    "ColumnView",
    "ClassLabels",
    "RankingTable",
    "display_coordinates",
    "average_ranks",
    "nearest_neighbours",
    "knn_separation",
    "chance_corrected_agreement",
    "correlation",
    "correlation_ratio",
    "is_clock",
    "ColumnSet",
    "ProjectionRanker",
    "ParameterRanker",
]

#: Neighbours per burst in the class-separation score. VizRank's published
#: choice is k = sqrt(N) (71 at a 5000-burst sample); on the test tables it
#: gave the same top views at about six times the cost, so ndX keeps 10.
MIN_K = 10
#: Bursts drawn for one ranking.
DEFAULT_MAX_ROWS = 5000
#: Fewer distinct display values than this make a column a flag.
MIN_DISTINCT = 20
#: Spearman |rho| at which two columns are taken for the same quantity.
DERIVED_RHO = 0.98
#: Correlation ratio at which one column is a function of another.
FUNCTION_ETA = 0.98
#: ... at which a pair is a single curve rather than a 2-D cloud.
CURVE_ETA = 0.95
#: Share of increasing steps that makes a column the acquisition clock.
CLOCK_SHARE = 0.9
#: Bins of the conditioning variable in :func:`correlation_ratio`.
ETA_BINS = 32
#: A fold's inverse dependence stays below this.
_FOLD_INVERSE = 0.9

#: key -> (caption, needs class labels, ranks pairs, ranks single columns).
#: The panel offers them in this order; the first is the default.
METHODS: Dict[str, Tuple[str, bool, bool, bool]] = {
    "populations": (mark("Separation"), False, True, True),
    "correlation": (mark("Correlation"), False, True, False),
    "separation": (mark("Classes"), True, True, True),
}

#: What each score means, in FRET terms (the line under the choice).
METHOD_HELP: Dict[str, str] = {
    "populations": mark(
        "How many bursts fall into clearly separated islands: donor-only, acceptor-only "
        "and FRET species in E vs S, a dynamic population off the static FRET line. "
        "0: one population; 0.5: two equal islands with empty space between; 0.67: three."),
    "correlation": mark(
        "|Spearman rho| of the pair: parameters that measure related things (E and a "
        "lifetime, a rate and its count), not populations. Parameters that are the same "
        "quantity are ranked once."),
    "separation": mark(
        "Do the bursts of one label (a gate, the clusters) sit together in this view? "
        "Share of each burst's 10 nearest neighbours with its label, above chance."),
}

#: Bar colours of a positive and a negative correlation (ndX's blue and red).
POSITIVE_BAR = (52, 120, 190)
NEGATIVE_BAR = (205, 70, 60)


# ---------------------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------------------
@dataclass
class ColumnView:
    """How ndX draws a column: linear or logarithmic, and its range.

    A bound of ``None`` is the automatic range.
    """

    name: str
    scale: str = "lin"
    lo: Optional[float] = None
    hi: Optional[float] = None


@dataclass
class ClassLabels:
    """Labels a view should keep apart.

    Attributes
    ----------
    values : numpy.ndarray
        One value per table row; NaN is "no class" (the row is not used).
    discrete : bool
        Class ids (``True``) or a quantity to predict (``False``).
    name : str
        What the labels are, for the tooltips (translated where shown).
    exclude : tuple of str
        Columns the labels are made from (a gate's parameters): not ranked.
    use_all_rows : bool
        Rows the gates remove still count -- the labels contrast inside
        with outside.
    """

    values: np.ndarray
    discrete: bool
    name: str
    exclude: Tuple[str, ...] = ()
    use_all_rows: bool = False


def display_coordinates(values, view: ColumnView) -> np.ndarray:
    """A column on ``[0, 1]`` as its axis draws it.

    Missing bounds come from
    :func:`~ndxplorer.utils.axis_helpers.robust_axis_range`. On a log axis
    the values and bounds are mapped by ``log10`` (values <= 0 cannot be
    drawn). Values the axis cannot draw -- non-finite, or <= 0 on a log axis
    -- are NaN; the rest are clipped to the range. An empty or non-finite
    range gives all-NaN.

    Parameters
    ----------
    values : array-like
        The column.
    view : ColumnView
        Its scale and range.

    Returns
    -------
    numpy.ndarray
        float64 coordinates, the shape of *values*.
    """
    from ..utils.axis_helpers import robust_axis_range

    x = np.asarray(values, dtype=np.float64)
    nothing = np.full(x.shape, np.nan)
    lo, hi = view.lo, view.hi
    if lo is None or hi is None:
        auto_lo, auto_hi = robust_axis_range(x, view.scale)
        lo = auto_lo if lo is None else lo
        hi = auto_hi if hi is None else hi
    lo, hi = float(lo), float(hi)
    with np.errstate(invalid="ignore", divide="ignore"):
        if view.scale == "log":
            if not (lo > 0 and hi > 0):
                return nothing
            x = np.where(x > 0, np.log10(np.where(x > 0, x, 1.0)), np.nan)
            lo, hi = math.log10(lo), math.log10(hi)
        x = np.where(np.isfinite(x), x, np.nan)
        span = hi - lo
        if not (math.isfinite(span) and span > 0):
            return nothing
        return np.clip((x - lo) / span, 0.0, 1.0)


def average_ranks(values) -> np.ndarray:
    """Ranks 0 .. n-1 of *values*, tied values sharing the mean of the ranks they span.

    The tie rule of Spearman's coefficient (Kendall & Gibbons 1990). NaN in
    the input must be removed beforehand.
    """
    x = np.asarray(values, dtype=np.float64).ravel()
    n = x.size
    if n == 0:
        return np.empty(0)
    order = np.argsort(x, kind="mergesort")
    sorted_x = x[order]
    starts = np.flatnonzero(np.r_[True, sorted_x[1:] != sorted_x[:-1]])
    ends = np.r_[starts[1:], n]  # exclusive
    mean_rank = 0.5 * (starts + ends - 1)
    group = np.repeat(np.arange(starts.size), ends - starts)
    ranks = np.empty(n)
    ranks[order] = mean_rank[group]
    return ranks


def _subset_ranks(order: np.ndarray, values: np.ndarray, keep: np.ndarray) -> np.ndarray:
    """:func:`average_ranks` of ``values[keep]``, from the argsort *order* of all *values*.

    Dropping rows from a sorted order leaves it sorted, so the ranks of any
    subset take one pass instead of a sort. Returned in row order of the
    kept rows.
    """
    idx = order[keep[order]]
    v = values[idx]
    n = idx.size
    starts = np.flatnonzero(np.r_[True, v[1:] != v[:-1]]) if n else np.empty(0, np.int64)
    ends = np.r_[starts[1:], n]
    ranks = np.empty(values.shape)
    ranks[idx] = np.repeat(0.5 * (starts + ends - 1), ends - starts)
    return ranks[keep]


def _abs_spearman(a: np.ndarray, b: np.ndarray, min_rows: int) -> Optional[float]:
    """|rho| over the rows finite in both, ``None`` with fewer than *min_rows* or a constant."""
    ok = np.isfinite(a) & np.isfinite(b)
    if int(ok.sum()) < max(min_rows, 2):
        return None
    _key, r, _p = correlation(a[ok], b[ok], "spearman")
    return None if math.isnan(r) else abs(r)


class RankingTable:
    """The subsample every view of one ranking is scored on.

    Parameters
    ----------
    columns : mapping
        Column name -> full-length array (views into the table; only the
        sampled rows are ever converted).
    views : mapping, optional
        Column name -> :class:`ColumnView`.
    rows : array of bool, optional
        Rows the gates keep (ignored when the labels use all rows).
    labels : ClassLabels, optional
        Classes for the class-separation score.
    max_rows : int
        Sample size; 0 or less keeps every eligible row.
    seed : int
        Seed of the draw.
    weights : array, optional
        Per-row weights (photon counts) for the population score.
    """

    def __init__(self, columns, views=None, rows=None, labels: Optional[ClassLabels] = None,
                 max_rows: int = DEFAULT_MAX_ROWS, seed: int = 0, weights=None) -> None:
        self.columns = dict(columns)
        self.views = dict(views or {})
        self.labels = labels
        self.max_rows = int(max_rows)
        self.seed = seed
        self._rows = rows
        self._weights = weights
        self._prepared = False
        self.n_eligible = 0
        self.index = np.empty(0, dtype=np.int64)
        self.raw: Dict[str, np.ndarray] = {}
        self.coords: Dict[str, np.ndarray] = {}
        self.distinct: Dict[str, int] = {}
        self._names: List[str] = []
        self.y: Optional[np.ndarray] = None
        self.w: Optional[np.ndarray] = None
        self.total_weight = 0.0

    @property
    def n_rows(self) -> int:
        """The sample size (0 before :meth:`prepare`)."""
        return int(self.index.size)

    @property
    def names(self) -> List[str]:
        """The columns that have a view to rank, in the given order."""
        return list(self._names)

    def view(self, name: str) -> ColumnView:
        """How *name* is drawn (a linear automatic axis when nothing was given)."""
        return self.views.get(name) or ColumnView(name)

    def _length(self) -> int:
        for column in self.columns.values():
            return len(column)
        if self.labels is not None:
            return len(self.labels.values)
        return 0

    def prepare(self) -> None:
        """Draw the sample and convert the sampled rows (once; later calls do nothing).

        Eligible rows pass the gates (unless the labels use all rows), have a
        finite label and a finite positive weight, when those are given. At
        most ``max_rows`` of them are drawn uniformly without replacement.
        """
        if self._prepared:
            return
        self._prepared = True
        n = self._length()
        keep = np.ones(n, dtype=bool)
        labels = self.labels
        if self._rows is not None and not (labels is not None and labels.use_all_rows):
            keep &= np.asarray(self._rows, dtype=bool)
        label_values = None
        if labels is not None:
            label_values = np.asarray(labels.values, dtype=np.float64)
            keep &= np.isfinite(label_values)
        weights = None
        if self._weights is not None:
            weights = np.asarray(self._weights, dtype=np.float64)
            with np.errstate(invalid="ignore"):
                keep &= np.isfinite(weights) & (weights > 0)
        eligible = np.flatnonzero(keep)
        self.n_eligible = int(eligible.size)
        if self.max_rows > 0 and eligible.size > self.max_rows:
            rng = np.random.default_rng(self.seed)
            eligible = np.sort(rng.choice(eligible, size=self.max_rows, replace=False))
        self.index = eligible.astype(np.int64)

        self._all_raw: Dict[str, np.ndarray] = {}
        for name, column in self.columns.items():
            # Gather first, then widen: a float32 view of a large table stays as it is.
            raw = np.asarray(np.asarray(column)[self.index], dtype=np.float64)
            self._all_raw[name] = raw
            coords = display_coordinates(raw, self.view(name))
            finite = coords[np.isfinite(coords)]
            if finite.size < 2 or np.all(finite == finite[0]):
                continue
            self.raw[name] = raw
            self.coords[name] = coords
            self.distinct[name] = int(np.unique(finite).size)
            self._names.append(name)
        self.y = label_values[self.index] if label_values is not None else None
        if weights is not None and self.index.size:
            w = weights[self.index]
            self.w = w / w.mean()
            self.total_weight = float(self.w.sum())
        else:
            self.w = None
            self.total_weight = float(self.index.size)

    def derived_from(self, sources: Sequence[str], threshold: float = DERIVED_RHO) -> List[str]:
        """Columns (other than *sources*) that are, rank for rank, a source.

        A surviving column is derived when its Spearman |rho| with any
        source present in the sample is at least *threshold*, over rows
        finite in both and only with at least :data:`MIN_K` of them.
        """
        self.prepare()
        present = [s for s in sources if s in getattr(self, "_all_raw", {})]
        out = []
        for name in self._names:
            if name in sources:
                continue
            for source in present:
                rho = _abs_spearman(self.raw[name], self._all_raw[source], MIN_K)
                if rho is not None and rho >= threshold:
                    out.append(name)
                    break
        return out

    def matrix(self, names: Sequence[str]) -> np.ndarray:
        """Display coordinates of *names*, ``(n_rows, len(names))``."""
        return np.column_stack([self.coords[n] for n in names]) if names \
            else np.empty((self.n_rows, 0))


# ---------------------------------------------------------------------------------------
# Class separation by nearest neighbours
# ---------------------------------------------------------------------------------------
def _as_points(points) -> np.ndarray:
    p = np.asarray(points, dtype=np.float64)
    return p[:, None] if p.ndim == 1 else p


#: Relative slack on squared distances below which two distances count as tied.
_TIE = 1e-9


def nearest_neighbours(points, k: int) -> np.ndarray:
    """The *k* nearest other points of every point, exactly.

    Euclidean distance; a point is never its own neighbour, even when
    duplicates sit at distance 0; ties at the k-th distance go to the lower
    row index. Each row is in ascending (distance, index) order, so the
    answer does not depend on the order of the columns.

    A k-d tree proposes ``k + 2`` candidates per point. A row is settled when
    the candidate after its k-th neighbour is clearly farther (everything
    outside the candidates is at least as far). The rest -- a tie at the
    k-th distance, typical of counts and of values clipped to an axis edge
    -- are settled on the distinct coordinates (:func:`_settle_ties`), where
    a stack of duplicates is one site with a multiplicity.

    Parameters
    ----------
    points : array, shape (n,) or (n, d)
        Finite coordinates.
    k : int
        Neighbours per point, ``k < n``.

    Returns
    -------
    numpy.ndarray of int64, shape (n, k)
    """
    import tttrlib

    p = np.ascontiguousarray(_as_points(points))
    n = p.shape[0]
    k = int(k)
    if k <= 0:
        return np.empty((n, 0), dtype=np.int64)
    if n <= k:
        raise ValueError(f"{k} neighbours need more than {n} points")
    width = min(k + 2, n)
    tree = tttrlib.KDTree(p)
    _dist, idx = tree.query(p, k=width)
    idx = np.asarray(idx, dtype=np.int64).reshape(n, width)
    # The distances ties are judged by are the ones computed here.
    sq = ((p[idx] - p[:, None, :]) ** 2).sum(axis=2)
    sq[idx == np.arange(n)[:, None]] = np.inf  # never oneself
    order = np.lexsort((idx, sq), axis=1)
    idx = np.take_along_axis(idx, order, axis=1)
    sq = np.take_along_axis(sq, order, axis=1)
    out = idx[:, :k].copy()
    if width < n:
        tied = np.flatnonzero(~(sq[:, k] > sq[:, k - 1] * (1.0 + _TIE)))
        if tied.size:
            _settle_ties(p, tied, k, out)
    return out


def _settle_ties(p: np.ndarray, rows: np.ndarray, k: int, out: np.ndarray) -> None:
    """Exact neighbours of the points *rows* whose k-th distance is tied, into *out*.

    Identical points form one *site*. For a site, the first ``k + 1`` points
    in (distance, index) order -- its own members first, at distance 0 --
    serve every member: a member drops itself from them, or, when it is not
    among them, takes the first ``k``. Sites are drawn from a k-d tree of
    the distinct coordinates, widening until the multiplicities reach
    ``k + 1`` and the boundary distance is closed.
    """
    import tttrlib

    sites, inverse, counts = np.unique(p, axis=0, return_inverse=True, return_counts=True)
    inverse = np.asarray(inverse).ravel()
    grouped = np.argsort(inverse, kind="stable")  # members of each site, ascending index
    bounds = np.r_[0, np.cumsum(counts)]
    u = sites.shape[0]
    tree = tttrlib.KDTree(np.ascontiguousarray(sites))
    want = k + 1
    row_site = inverse[rows]
    for site in np.unique(row_site):
        width = min(want + 1, u)
        while True:
            _dist, near = tree.query(sites[site:site + 1], k=width)
            near = np.asarray(near, dtype=np.int64).reshape(-1)
            d2 = ((sites[near] - sites[site]) ** 2).sum(axis=1)
            o = np.argsort(d2, kind="stable")
            near, d2 = near[o], d2[o]
            reach = int(np.searchsorted(np.cumsum(counts[near]), want))
            boundary = d2[min(reach, d2.size - 1)]
            if width >= u or (reach < d2.size and d2[-1] > boundary * (1.0 + _TIE)):
                break
            width = min(2 * width, u)
        chosen = near[d2 <= boundary * (1.0 + _TIE)]
        members = np.concatenate([grouped[bounds[t]:bounds[t + 1]] for t in chosen])
        member_d2 = np.repeat(d2[:chosen.size], counts[chosen])
        first = members[np.lexsort((members, member_d2))][:want]
        mine = rows[row_site == site]
        keep = first[None, :] != mine[:, None]
        keep[keep.all(axis=1), want - 1] = False  # not among them: take the first k
        out[mine] = np.broadcast_to(first, keep.shape)[keep].reshape(mine.size, k)


def _knn_details(points, y, discrete: bool, k: int):
    """``(statistic, n_valid, valid labels)``: the share of neighbours of the
    same class (discrete) or R^2 of the neighbour mean (continuous); ``None``
    when undefined."""
    p = _as_points(points)
    y = np.asarray(y, dtype=np.float64).ravel()
    ok = np.isfinite(p).all(axis=1) & np.isfinite(y)
    n_valid = int(ok.sum())
    if n_valid < k + 1:
        return None
    yv = y[ok]
    neighbours = nearest_neighbours(p[ok], k)
    if discrete:
        return float(np.mean(yv[neighbours] == yv[:, None])), n_valid, yv
    predicted = yv[neighbours].mean(axis=1)
    total = float(np.sum((yv - yv.mean()) ** 2))
    if not total > 0:
        return None
    return 1.0 - float(np.sum((yv - predicted) ** 2)) / total, n_valid, yv


def knn_separation(points, y, *, discrete: bool, n_total: Optional[int] = None,
                   k: int = MIN_K) -> Optional[float]:
    """How well a view's k nearest neighbours predict each point's class (lower is better).

    Leave-one-out k-nearest-neighbour prediction on the view's coordinates,
    the projection quality of VizRank (Leban et al. 2006,
    doi:10.1007/s10618-005-0031-5) with uniform votes. Rows with a missing
    coordinate or label are dropped (``n_v`` remain).

    * Discrete labels: ``-p_o``, where ``p_o`` is the share of the
      neighbours that share the point's class, averaged over the points --
      the mean leave-one-out probability of the correct class.
    * Continuous labels: ``-R^2 * n_v / n_total``, where ``R^2`` is the
      variance of *y* explained by the mean of the neighbours' *y*; the
      factor is the share of rows the view can draw (a row it cannot draw
      has none of its variance explained).

    Parameters
    ----------
    points : array, shape (n,) or (n, d)
        Display coordinates.
    y : array, shape (n,)
        Labels; NaN is "no label".
    discrete : bool
        Class ids or a quantity.
    n_total : int, optional
        Rows the coverage is a share of (default ``len(y)``).
    k : int
        Neighbours per point (:data:`MIN_K`).

    Returns
    -------
    float or None
        ``None`` with ``n_v <= k`` (every point needs k others) or, for a
        quantity, with no variance to explain.
    """
    y = np.asarray(y, dtype=np.float64).ravel()
    found = _knn_details(points, y, discrete, k)
    if found is None:
        return None
    statistic, n_valid, _labels = found
    if discrete:
        return -statistic
    total = int(n_total) if n_total is not None else y.size
    return -statistic * n_valid / total


def chance_corrected_agreement(same_fraction: float, y) -> Optional[float]:
    """The share of same-class neighbours above what chance gives.

    ``kappa = (p_o - p_e) / (1 - p_e)``. ``p_e`` is the share expected when
    the labels have nothing to do with position: a neighbour drawn uniformly
    from the *other* ``n - 1`` points has the same class with probability
    ``sum_c n_c (n_c - 1) / (n (n - 1))``, so kappa is 0 on average for a
    random view, 1 for perfect separation, negative for a view that mixes
    classes more than chance. One marginal for both "raters", as in Scott's
    pi (Scott 1955, doi:10.1086/266577); the chance correction is Cohen's
    (1960, doi:10.1177/001316446002000104). The correction matters with
    unbalanced classes: with a 95 % / 5 % gate a random view already has
    ``p_o`` near 0.9.

    Parameters
    ----------
    same_fraction : float
        ``p_o``.
    y : array
        The labels it was measured on (non-finite entries ignored).

    Returns
    -------
    float or None
        ``None`` without labels or with a single class.
    """
    y = np.asarray(y, dtype=np.float64).ravel()
    y = y[np.isfinite(y)]
    if y.size < 2:
        return None
    _values, counts = np.unique(y, return_counts=True)
    if counts.size < 2:
        return None
    n = float(y.size)
    counts = counts.astype(np.float64)
    expected = float(np.sum(counts * (counts - 1.0)) / (n * (n - 1.0)))
    return (float(same_fraction) - expected) / (1.0 - expected)


# ---------------------------------------------------------------------------------------
# Correlation
# ---------------------------------------------------------------------------------------
def _beta_continued_fraction(a: float, b: float, x: float) -> float:
    """The continued fraction of the incomplete beta function (modified Lentz).

    DLMF 8.17.22; converges quickly for ``x < (a + 1) / (a + b + 2)``.
    """
    tiny = 1e-300
    c, d = 1.0, 1.0 - (a + b) * x / (a + 1.0)
    d = 1.0 / (d if abs(d) > tiny else tiny)
    f = d
    for m in range(1, 1000):
        # even step
        num = m * (b - m) * x / ((a + 2 * m - 1) * (a + 2 * m))
        d = 1.0 + num * d
        d = 1.0 / (d if abs(d) > tiny else tiny)
        c = 1.0 + num / c
        c = c if abs(c) > tiny else tiny
        f *= d * c
        # odd step
        num = -(a + m) * (a + b + m) * x / ((a + 2 * m) * (a + 2 * m + 1))
        d = 1.0 + num * d
        d = 1.0 / (d if abs(d) > tiny else tiny)
        c = 1.0 + num / c
        c = c if abs(c) > tiny else tiny
        delta = d * c
        f *= delta
        if abs(delta - 1.0) < 1e-15:
            break
    return f


def _regularized_beta(a: float, b: float, x: float) -> float:
    """``I_x(a, b)``, the regularised incomplete beta function."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 1.0
    log_front = (math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
                 + a * math.log(x) + b * math.log1p(-x))
    if x < (a + 1.0) / (a + b + 2.0):
        return math.exp(log_front) * _beta_continued_fraction(a, b, x) / a
    return 1.0 - math.exp(log_front) * _beta_continued_fraction(b, a, 1.0 - x) / b


def _t_test_p(r: float, n: int) -> float:
    """Two-sided p of ``t = r sqrt((n-2)/(1-r^2))`` under Student's t with ``n - 2``
    degrees of freedom (Student 1908, doi:10.1093/biomet/6.1.1).

    ``P(|T| > t) = I_{df/(df+t^2)}(df/2, 1/2)`` and ``df/(df+t^2) = 1 - r^2``.
    """
    df = n - 2
    return _regularized_beta(0.5 * df, 0.5, 1.0 - r * r)


def correlation(a, b, method: str = "pearson") -> Tuple[float, float, float]:
    """Correlation of two columns over the rows where both are finite.

    Pearson's product-moment r (Pearson 1895, doi:10.1098/rspl.1895.0041),
    or Spearman's rho -- Pearson's r of the average ranks (Spearman 1904,
    doi:10.2307/1412159). The p value is the two-sided t test of
    ``rho = 0`` with ``n - 2`` degrees of freedom: exact for Pearson under
    bivariate normality, the usual large-sample approximation for Spearman.

    Parameters
    ----------
    a, b : array-like
        The columns; NaN and +-inf are missing (pairwise deletion).
    method : str
        ``"pearson"`` or ``"spearman"``.

    Returns
    -------
    tuple
        ``(key, r, p)`` with ``key = -|r|`` (lower is better). ``(inf, nan,
        nan)`` with fewer than two rows or a constant column; ``p = 1`` with
        two rows (no degrees of freedom), ``p = 0`` when ``|r| = 1``.
    """
    x = np.asarray(a, dtype=np.float64).ravel()
    y = np.asarray(b, dtype=np.float64).ravel()
    ok = np.isfinite(x) & np.isfinite(y)
    x, y = x[ok], y[ok]
    n = int(x.size)
    undefined = (math.inf, math.nan, math.nan)
    if n < 2:
        return undefined
    if method == "spearman":
        x, y = average_ranks(x), average_ranks(y)
    elif method != "pearson":
        raise ValueError(f"unknown correlation method {method!r}")
    return _product_moment(x, y)


def _product_moment(x: np.ndarray, y: np.ndarray) -> Tuple[float, float, float]:
    """``(key, r, p)`` of two complete columns (see :func:`correlation`)."""
    n = int(x.size)
    x = x - x.mean()
    y = y - y.mean()
    sxx, syy = float(np.dot(x, x)), float(np.dot(y, y))
    if n < 2 or not (sxx > 0 and syy > 0):
        return (math.inf, math.nan, math.nan)
    r = float(np.dot(x, y)) / math.sqrt(sxx * syy)
    r = max(-1.0, min(1.0, r))
    if n == 2:
        p = 1.0
    elif abs(r) == 1.0:
        p = 0.0
    else:
        p = _t_test_p(r, n)
    return -abs(r), r, p


def correlation_ratio(y, x, bins: int = ETA_BINS) -> float:
    """eta^2 of *y* given *x*: the share of y's variance explained by x's bins.

    Pearson's correlation ratio (1903; Kendall & Stuart, *The Advanced
    Theory of Statistics*, vol. 2): 1 when y is any function of x, monotone
    or not; 0 when the bin means of y do not move. Both values are in
    ``[0, 1]``; x is binned by ``floor(x * bins)``.

    Returns 0 with fewer than ``2 * MIN_K`` rows finite in both, or when y
    is constant.
    """
    y = np.asarray(y, dtype=np.float64).ravel()
    x = np.asarray(x, dtype=np.float64).ravel()
    ok = np.isfinite(x) & np.isfinite(y)
    if int(ok.sum()) < 2 * MIN_K:
        return 0.0
    return _binned_eta(y[ok], _cells(x[ok], bins), bins)


def _cells(x: np.ndarray, bins: int) -> np.ndarray:
    """The bin of each value of *x* in ``[0, 1]``: ``floor(x * bins)``, clipped."""
    with np.errstate(invalid="ignore"):
        return np.clip(np.floor(np.nan_to_num(x) * bins).astype(np.int64), 0, bins - 1)


def _binned_eta(y: np.ndarray, cell: np.ndarray, bins: int) -> float:
    """eta^2 of complete *y* given the bin of each row."""
    centred = y - y.mean()
    total = float(np.dot(centred, centred))
    if not total > 0:
        return 0.0
    counts = np.bincount(cell, minlength=bins)
    sums = np.bincount(cell, weights=y, minlength=bins)
    means = np.divide(sums, counts, out=np.zeros(bins), where=counts > 0)
    within = float(np.sum((y - means[cell]) ** 2))
    return 1.0 - within / total


def is_clock(values) -> bool:
    """Whether a column counts time along the acquisition (it rises row after row).

    True when more than ``2 * MIN_K`` finite values remain and at least
    :data:`CLOCK_SHARE` of the steps between consecutive ones are increases.
    """
    x = np.asarray(values, dtype=np.float64).ravel()
    x = x[np.isfinite(x)]
    if x.size <= 2 * MIN_K:
        return False
    return float(np.mean(np.diff(x) > 0)) >= CLOCK_SHARE


# ---------------------------------------------------------------------------------------
# The columns worth pairing
# ---------------------------------------------------------------------------------------
class ColumnSet:
    """The columns a population or correlation ranking pairs, and why the rest are not.

    Each surviving column of *table* (outside *exclude*) is set aside with a
    reason in :attr:`left_out` when it is a flag (few distinct values), the
    acquisition clock, or has nothing left once its axis is prepared
    (:class:`~ndxplorer.analysis.separation.RobustAxis`). Of the rest,
    columns that are the same quantity -- Spearman |rho| of at least
    :data:`DERIVED_RHO`, or each a function of the other -- form one alias
    group, ranked once under its head; a column that is a many-to-one
    function of another (a *fold*, (1-E)E of E) is set aside too.

    Attributes
    ----------
    names : list of str
        The ranked columns (alias heads), in table order.
    axes, coords : dict
        Per kept column, its robust axis and coordinates on it.
    ranks, uniform : dict
        Average ranks of the coordinates (NaN where missing), and the ranks
        scaled onto ``[0, 1]``.
    aliases : dict
        Head -> the columns merged into it.
    left_out : dict
        Column -> why it is not ranked.
    """

    def __init__(self, table: RankingTable, exclude: Sequence[str] = ()) -> None:
        from .separation import RobustAxis

        table.prepare()
        self.table = table
        exclude = set(exclude)
        self.left_out: Dict[str, str] = {}
        self.axes: Dict[str, object] = {}
        self.coords: Dict[str, np.ndarray] = {}
        self.ranks: Dict[str, np.ndarray] = {}
        self.uniform: Dict[str, np.ndarray] = {}
        self.aliases: Dict[str, List[str]] = {}
        self._order: Dict[str, np.ndarray] = {}
        self._finite: Dict[str, np.ndarray] = {}
        self._cells: Dict[str, np.ndarray] = {}
        kept: List[str] = []
        for name in table.names:
            if name in exclude:
                continue
            raw = table.raw[name]
            if table.distinct[name] < MIN_DISTINCT:
                self.left_out[name] = "a flag (few distinct values)"
                continue
            if is_clock(raw):
                self.left_out[name] = "the acquisition clock"
                continue
            axis, u = RobustAxis.fit(raw, table.view(name).scale)
            if axis is None or int(np.isfinite(u).sum()) < 5 * MIN_K:
                self.left_out[name] = "nothing left after outliers"
                continue
            self.axes[name] = axis
            self.coords[name] = u
            finite = np.isfinite(u)
            # One sort per column: the order serves every later rank of any
            # subset of its rows (_subset_ranks) without sorting again.
            self._order[name] = np.argsort(u, kind="mergesort")
            self._finite[name] = finite
            ranks = np.full(u.shape, np.nan)
            ranks[finite] = _subset_ranks(self._order[name], u, finite)
            self.ranks[name] = ranks
            self.uniform[name] = ranks / max(int(finite.sum()) - 1, 1)
            self._cells[name] = _cells(self.uniform[name], ETA_BINS)
            kept.append(name)

        heads = self._group(kept)
        self._fold_out(heads)
        position = {name: i for i, name in enumerate(table.names)}
        self.names = sorted((h for h in heads if h not in self.left_out), key=position.get)

    def spearman(self, a: str, b: str, min_rows: int = 2) -> Tuple[float, float]:
        """``(rho, p)`` of two kept columns over the rows finite in both
        (:func:`correlation` with ``"spearman"``, reusing each column's sort).

        ``(nan, nan)`` with fewer than *min_rows* such rows or a constant.
        """
        ok = self._finite[a] & self._finite[b]
        if int(ok.sum()) < max(min_rows, 2):
            return math.nan, math.nan
        ra = _subset_ranks(self._order[a], self.coords[a], ok)
        rb = _subset_ranks(self._order[b], self.coords[b], ok)
        _key, r, p = _product_moment(ra, rb)
        return r, p

    def eta(self, y: str, x: str) -> float:
        """:func:`correlation_ratio` of the rank-uniform values of *y* given *x*."""
        ok = self._finite[y] & self._finite[x]
        if int(ok.sum()) < 2 * MIN_K:
            return 0.0
        return _binned_eta(self.uniform[y][ok], self._cells[x][ok], ETA_BINS)

    def _same_quantity(self, head: str, name: str) -> bool:
        rho, _p = self.spearman(head, name, 2 * MIN_K)
        if not math.isnan(rho) and abs(rho) >= DERIVED_RHO:
            return True
        return self.eta(head, name) >= FUNCTION_ETA and self.eta(name, head) >= FUNCTION_ETA

    def _group(self, kept: List[str]) -> List[str]:
        """Merge columns that are one quantity; the heads, in the order they were made.

        Columns drawn with a fixed range come first (they are the ones the
        user set up), later table positions before earlier ones.
        """
        def fixed(name: str) -> bool:
            view = self.table.view(name)
            return view.lo is not None and view.hi is not None

        position = {name: i for i, name in enumerate(kept)}
        visit = sorted(kept, key=lambda n: (not fixed(n), -position[n]))
        heads: List[str] = []
        for name in visit:
            for head in heads:
                if self._same_quantity(head, name):
                    self.aliases.setdefault(head, []).append(name)
                    self.left_out[name] = f"the same as {head}"
                    break
            else:
                heads.append(name)
        return heads

    def _fold_out(self, heads: List[str]) -> None:
        """Set aside heads that are a many-to-one function of another head."""
        for name in heads:
            for other in heads:
                if other == name:
                    continue
                if self.eta(name, other) >= FUNCTION_ETA and \
                        self.eta(other, name) < _FOLD_INVERSE:
                    self.left_out[name] = f"a fold of {other}"
                    break

    def matrix(self, names: Sequence[str]) -> np.ndarray:
        """Robust-axis coordinates of *names*, ``(n, len(names))``."""
        return np.column_stack([self.coords[n] for n in names])

    def is_curve(self, a: str, b: str) -> bool:
        """Whether one of the two is (nearly) a function of the other: a line, not a cloud."""
        return max(self.eta(a, b), self.eta(b, a)) >= CURVE_ETA


# ---------------------------------------------------------------------------------------
# The rankers
# ---------------------------------------------------------------------------------------
class _ScoredViews:
    """What the pair and the single-column ranker share: the table, the
    method, the column choice and the scores.

    Scores (lower is better):

    * populations: ``(-score, -islands, arrival, found)`` -- *arrival*
      keeps equal scores in scoring order and keeps two ``found`` objects
      from ever being compared;
    * correlation: ``(-|rho|, p, arrival, rho)``;
    * separation, class ids: ``(-kappa, -p_o, n_valid)`` with kappa weighted
      by the share of rows the view draws;
    * separation, a quantity: ``(-R2c, -R2c, n_valid)``, R2c the
      coverage-weighted R^2.
    """

    def _setup(self, table: RankingTable, method: str, single: bool) -> None:
        if method not in METHODS:
            raise ValueError(f"unknown ranking method {method!r}")
        _caption, needs_labels, pairs, singles = METHODS[method]
        if needs_labels and table.labels is None:
            raise ValueError(f"ranking by {method!r} needs class labels")
        if single and not singles:
            raise ValueError(f"{method!r} does not rank single parameters")
        if not single and not pairs:
            raise ValueError(f"{method!r} does not rank pairs")
        self.table = table
        self.method = method
        self.columns: Optional[ColumnSet] = None
        self._arrival = itertools.count()

    def prepare(self) -> None:
        """Draw the sample (GUI thread); the columns are chosen later, in the worker."""
        self.table.prepare()
        self.columns = None
        self._arrival = itertools.count()
        super().prepare()

    def left_out(self) -> Dict[str, str]:
        """Columns not ranked, with the reason."""
        return dict(self.columns.left_out) if self.columns is not None else {}

    # ---- columns -----------------------------------------------------------------------
    def _candidates(self) -> List[str]:
        table = self.table
        table.prepare()
        if self.method == "separation":
            exclude = tuple(table.labels.exclude) if table.labels is not None else ()
            derived = set(table.derived_from(sorted(exclude)))
            return [n for n in table.names if n not in exclude and n not in derived]
        exclude = tuple(table.labels.exclude) if table.labels is not None else ()
        self.columns = ColumnSet(table, exclude=exclude)
        return list(self.columns.names)

    def _single_primary(self, name: str) -> float:
        score = self._score((name,))
        return math.inf if score is None else float(score[0])

    # ---- scores ------------------------------------------------------------------------
    def _score(self, state: Tuple[str, ...]):
        method = self.method
        if method == "populations":
            from .separation import find_populations

            columns = self.columns
            if len(state) == 2 and columns.is_curve(*state):
                return None
            found = find_populations(columns.matrix(state), self.table.total_weight, self.table.w)
            if found is None:
                return None
            return (-float(found.score), -int(found.count), next(self._arrival), found)
        if method == "correlation":
            rho, p = self.columns.spearman(*state)
            if math.isnan(rho):
                return None
            return (-abs(rho), p, next(self._arrival), rho)
        table = self.table
        labels = table.labels
        found = _knn_details(table.matrix(state), table.y, labels.discrete, MIN_K)
        if found is None:
            return None
        statistic, n_valid, valid_labels = found
        coverage = n_valid / max(table.n_rows, 1)
        if labels.discrete:
            kappa = chance_corrected_agreement(statistic, valid_labels)
            if kappa is None:
                return None
            return (-kappa * coverage, -statistic, n_valid)
        weighted = statistic * coverage
        return (-weighted, -weighted, n_valid)

    def compute_score(self, state: Tuple[str, ...]):
        """The score of the view *state* (lower is better), ``None`` to leave it out."""
        self._ensure_columns()
        return self._score(tuple(state))

    # ---- rows --------------------------------------------------------------------------
    def _label(self, name: str) -> str:
        return f"{name} (log)" if self.table.view(name).scale == "log" else name

    def _payload(self, state: Tuple[str, ...]) -> dict:
        if len(state) == 1:
            return {"z": state[0], "scale_z": self.table.view(state[0]).scale}
        x, y = state
        return {"x": x, "y": y, "scale_x": self.table.view(x).scale,
                "scale_y": self.table.view(y).scale}

    def _also(self, state: Tuple[str, ...]) -> str:
        if self.columns is None:
            return ""
        merged = [m for name in state for m in self.columns.aliases.get(name, [])]
        if not merged:
            return ""
        return " " + tr("Also this view: {names}.").format(names=", ".join(merged))

    def row_for_state(self, score, state: Tuple[str, ...]) -> RankRow:
        """The table row of a scored view."""
        state = tuple(state)
        labels = tuple(self._label(n) for n in state)
        payload = self._payload(state)
        n = self.table.n_rows
        if self.method == "populations":
            found = score[3]
            value = float(found.score)
            count = int(found.count)
            if count > 1:
                tooltip = tr(
                    "{count} islands holding {shares} of the {n} sampled bursts; {inside} % sit "
                    "clearly inside one (not on a bridge or in a tail). Score {score}: the chance "
                    "that two bursts are in two different, clearly separated populations."
                ).format(count=count, n=n,
                         shares=", ".join(f"{100.0 * s:.0f} %" for s in found.shares),
                         inside=int(round(100.0 * found.in_islands)), score=f"{value:.3f}")
            else:
                tooltip = tr("One population: no significant density valley over {n} sampled "
                             "bursts.").format(n=n)
            return RankRow((f"{value:.3f}",) + labels + (str(count),), payload,
                           bar=min(1.0, value / 0.5), sort_value=value,
                           tooltip=tooltip + self._also(state))
        if self.method == "correlation":
            rho, p = float(score[3]), float(score[1])
            tooltip = tr("Spearman ρ = {rho}, p = {p} over {n} sampled bursts: the two move "
                         "together, which says nothing about populations.").format(
                rho=f"{rho:+.4f}", p=f"{p:.3g}", n=n)
            return RankRow((f"{rho:+.3f}",) + labels, payload, bar=abs(rho),
                           sort_value=abs(rho), tooltip=tooltip + self._also(state),
                           bar_color=POSITIVE_BAR if rho >= 0 else NEGATIVE_BAR, value=rho)
        table_labels = self.table.labels
        classes = tr(table_labels.name)
        n_valid = int(score[2])
        coverage = n_valid / max(n, 1)
        if table_labels.discrete:
            weighted = -float(score[0])
            share = -float(score[1])
            kappa = weighted / coverage if coverage > 0 else 0.0
            tooltip = tr("{share} of each burst's {k} nearest neighbours share its class "
                         "({classes}); κ = {kappa} above chance, over {valid} of {n} sampled "
                         "rows.").format(share=f"{share:.1%}", k=MIN_K, classes=classes,
                                         kappa=f"{kappa:.3f}", valid=n_valid, n=n)
        else:
            weighted = -float(score[0])
            r2 = weighted / coverage if coverage > 0 else 0.0
            tooltip = tr("The mean {classes} of each burst's {k} nearest neighbours predicts its "
                         "own with R² = {r2}; weighted by the {share} of sampled rows that "
                         "have values.").format(classes=classes, k=MIN_K, r2=f"{r2:.3f}",
                                                share=f"{coverage:.0%}")
        return RankRow((f"{weighted:.3f}",) + labels, payload,
                       bar=min(1.0, max(0.0, weighted)), sort_value=weighted, tooltip=tooltip)

    # ---- table layout --------------------------------------------------------------------
    def _name_headers(self) -> Tuple[str, ...]:
        raise NotImplementedError

    @property
    def header(self) -> Tuple[str, ...]:
        if self.method == "populations":
            return (mark("Separation"),) + self._name_headers() + ("Islands",)
        if self.method == "correlation":
            return ("ρ",) + self._name_headers()
        discrete = self.table.labels is None or self.table.labels.discrete
        return ("κ" if discrete else "R²",) + self._name_headers()

    @property
    def score_span(self) -> Tuple[float, float]:
        if self.method == "populations":
            return (0.0, 0.5)
        if self.method == "correlation":
            return (-1.0, 1.0)
        return (0.0, 1.0)

    # ---- the islands of a view (populations only) ----------------------------------------
    def ranked_names(self, names: Sequence[str]) -> Optional[List[str]]:
        """Each name as ranked: itself, or the head it was merged into; ``None`` if any is neither."""
        if self.method != "populations" or self.columns is None:
            return None
        out = []
        for name in names:
            if name in self.columns.names:
                out.append(name)
                continue
            head = next((h for h, members in self.columns.aliases.items()
                         if name in members and h in self.columns.names), None)
            if head is None:
                return None
            out.append(head)
        return out

    def _refound(self, names: Sequence[str], values: Sequence):
        from .separation import find_populations

        if self.method != "populations" or self.columns is None:
            return None
        if any(n not in self.columns.coords for n in names):
            return None
        found = find_populations(self.columns.matrix(list(names)), self.table.total_weight,
                                 self.table.w)
        if found is None:
            return None
        points = np.column_stack([self.columns.axes[n].transform(v)
                                  for n, v in zip(names, values)])
        return found, points

    def islands(self, names: Sequence[str], values: Sequence, core: bool = False):
        """The island of every row of *values* (full columns of *names*), -1 none.

        The view's populations are found again on the ranking's sample, as
        scored, and every row is mapped through each column's robust axis.
        ``None`` unless ranked by populations and the columns are known.
        """
        refound = self._refound(names, values)
        if refound is None:
            return None
        found, points = refound
        return found.label(points, core=core)

    def assign_islands(self, names: Sequence[str], values: Sequence, mode: str = "whole"):
        """``(labels, probabilities)`` of every row of *values*; ``None`` as :meth:`islands`."""
        refound = self._refound(names, values)
        if refound is None:
            return None
        found, points = refound
        return found.assign(points, mode)


class ProjectionRanker(_ScoredViews, PairRanker):
    """Ranks the x/y views of a table.

    Parameters
    ----------
    table : RankingTable
        The sample (read only by :meth:`prepare`).
    method : str
        A key of :data:`METHODS`.

    Pairs are enumerated over the selected columns put in order of their
    own one-column score (populations and separation), so promising pairs
    are scored first -- the role a univariate attribute estimate (ReliefF;
    Kononenko 1994, doi:10.1007/3-540-57868-4_57) plays in VizRank.
    """

    def __init__(self, table: RankingTable, method: str) -> None:
        PairRanker.__init__(self)
        self._setup(table, method, single=False)

    def _name_headers(self) -> Tuple[str, ...]:
        return ("x", "y")

    def select_columns(self) -> List[str]:
        names = self._candidates()
        if self.method == "correlation":
            return names
        primary = {name: self._single_primary(name) for name in names}
        position = {name: i for i, name in enumerate(names)}
        return sorted(names, key=lambda n: (primary[n], position[n]))


class ParameterRanker(_ScoredViews, ColumnRanker):
    """Ranks single parameters (the z axis), in selection order.

    Parameters
    ----------
    table : RankingTable
        The sample.
    method : str
        A key of :data:`METHODS` that ranks single columns.
    """

    def __init__(self, table: RankingTable, method: str) -> None:
        ColumnRanker.__init__(self)
        self._setup(table, method, single=True)

    def _name_headers(self) -> Tuple[str, ...]:
        return (mark("Parameter"),)

    def select_columns(self) -> List[str]:
        return self._candidates()
