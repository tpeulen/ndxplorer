"""Scores for ranking burst-table projections, and the rankers that use them.

The panel's *Rank by* switch picks one of three questions. Each score is
vectorised over the rows of a subsample drawn once per ranking, so a view costs
about a millisecond whatever the table size.

**Separation** (the default) -- in which view do the bursts fall into clearly
separated islands? :func:`ndxplorer.analysis.separation.find_populations`,
unsupervised: the chance that two bursts drawn at random sit in two different
islands cut apart by a density valley, discounted by how shallow the valley is
and counting only the bursts inside an island's core (not on a bridge, in a
tail or in the noise). It is 0 for one population however elongated or
correlated, and highest where most bursts sit in well-separated populations --
donor-only, acceptor-only and FRET species in E vs S.

**Correlation** -- which parameters move together? Spearman ``|ρ|`` of the pair
(:func:`correlation`, Orange3's ``CorrelationRank.compute_score``,
``Orange/widgets/data/owcorrelations.py``). It finds related measurements, not
populations.

Both rank the same columns (:class:`ColumnSet`): flags, the acquisition clock
and folds (``(1-E)*E`` of ``E``) are set aside, and columns that are the same
quantity (``Proximity ratio`` and ``FRET efficiency``, a rate and its count)
are ranked once under one representative whose row names the others.

**Classes**, offered only when there are labels (gates, clusters, a label
column) -- do the bursts of one class sit together? :func:`knn_separation`,
transcribed from Orange3's scatter-plot VizRank (``ScatterPlotVizRank.
compute_score``, ``Orange/widgets/visualize/owscatterplot.py``; Bioinformatics
Lab, University of Ljubljana, GPL-3.0): the share of each point's ``k = 10``
nearest neighbours with its class. Two departures: neighbours are found in
**displayed** coordinates (each axis on ``[0, 1]`` over the range and scale ndX
draws it with), and the score is **chance-corrected**
(:func:`chance_corrected_agreement`).

The 2-means "population structure" score this module used to offer is gone: on
real burst tables it was carried by sentinel clumps (``-1`` for an unfitted
channel) and by deterministic curves between derived columns.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np

from ..utils.axis_helpers import robust_axis_range
from .vizrank import AttrPairRanker, AttrRanker, RankRow

__all__ = [
    "MIN_K",
    "DEFAULT_MAX_ROWS",
    "MIN_DISTINCT",
    "DERIVED_RHO",
    "ColumnView",
    "ClassLabels",
    "RankingTable",
    "display_coordinates",
    "nearest_neighbours",
    "knn_separation",
    "chance_corrected_agreement",
    "correlation",
    "correlation_ratio",
    "is_clock",
    "ColumnSet",
    "METHODS",
    "ProjectionRanker",
    "ParameterRanker",
]

#: Neighbours per point, and the fewest rows a view needs to be scored at all
#: (Orange's ``minK``).
MIN_K = 10

#: Rows scored per ranking. kNN on 5 000 points in 2-D is a few milliseconds, so
#: a 40-column table (780 pairs) ranks in seconds; the ranking of the top views
#: is stable well below this (see the tests).
DEFAULT_MAX_ROWS = 5000

#: Fewest distinct values a column needs to be scored for population structure.
#: A flag (a fit's "scatter?" switch, a 0/1 quality bit) splits into two groups
#: perfectly and says nothing about populations of molecules; on the real MFD
#: burst table three such columns took every top row until this was added.
MIN_DISTINCT = 20

#: Spearman ``|ρ|`` above which a column counts as derived from another (see
#: :meth:`RankingTable.derived_from`) or as the same quantity (:class:`ColumnSet`).
DERIVED_RHO = 0.98

#: Correlation ratio ``η²`` above which one column is a function of another
#: (:func:`correlation_ratio`): read off the other's bins, it leaves under 2 %
#: of its variance unexplained.
FUNCTION_ETA2 = 0.98

#: A pair in which one axis predicts the other this well is a curve, not a
#: cloud: its "populations" are stretches of one line, already ranked in 1-D.
CURVE_ETA2 = 0.95

#: Share of consecutive rows over which a column rises for it to be the
#: acquisition clock (burst tables are in time order, file by file).
CLOCK_RISE = 0.9

#: Orange's bar colours for a positive and a negative correlation.
POSITIVE_COLOR = (170, 242, 43)
NEGATIVE_COLOR = (70, 190, 250)


# ---------------------------------------------------------------------------
# the data a ranking reads
# ---------------------------------------------------------------------------


@dataclass
class ColumnView:
    """How ndX will draw a column: its scale and, if fixed, its range.

    Attributes
    ----------
    name : str
        Column name.
    scale : str
        ``"lin"`` or ``"log"``.
    lo, hi : float or None
        The axis range. ``None`` means what *Auto* would give, the robust range
        of the ranked rows (:func:`ndxplorer.utils.axis_helpers.robust_axis_range`).
    """

    name: str
    scale: str = "lin"
    lo: Optional[float] = None
    hi: Optional[float] = None


@dataclass
class ClassLabels:
    """What "separated" means: one label per row of the full table.

    Attributes
    ----------
    values : numpy.ndarray
        Full-length float array; ``NaN`` means the row has no class and is left
        out of the separation score.
    discrete : bool
        Class ids (neighbour agreement) or a quantity (neighbour R²).
    name : str
        Shown in the dialog and the tooltips.
    exclude : tuple of str
        Columns that must not be ranked against these labels because they
        define them — the gated parameter separates its own gate perfectly.
    use_all_rows : bool
        The labels need rows the gates remove (inside *and* outside a gate), so
        the ranked rows are not restricted to what the gates keep.
    """

    values: np.ndarray
    discrete: bool
    name: str
    exclude: Tuple[str, ...] = ()
    use_all_rows: bool = False


def display_coordinates(values, view: ColumnView) -> np.ndarray:
    """Map a column onto ``[0, 1]`` as the axis would draw it.

    A log axis takes ``log10``; values the axis cannot draw (non-positive on a
    log axis, non-finite anywhere) become ``NaN``; values beyond the range are
    clipped to its edge. Returns an all-``NaN`` array when the range is empty,
    which the caller treats as a constant column.
    """
    x = np.asarray(values, dtype=np.float64)
    lo, hi = view.lo, view.hi
    if lo is None or hi is None:
        auto_lo, auto_hi = robust_axis_range(x, view.scale)
        lo = auto_lo if lo is None else lo
        hi = auto_hi if hi is None else hi
    with np.errstate(invalid="ignore", divide="ignore"):
        if view.scale == "log":
            if not (lo > 0 and hi > 0):
                return np.full(x.shape, np.nan)
            x = np.where(x > 0, np.log10(np.where(x > 0, x, 1.0)), np.nan)
            lo, hi = math.log10(lo), math.log10(hi)
        span = float(hi) - float(lo)
        if not (np.isfinite(span) and span > 0):
            return np.full(x.shape, np.nan)
        u = (x - float(lo)) / span
    return np.clip(u, 0.0, 1.0)  # NaN passes through np.clip unchanged


class RankingTable:
    """The rows a ranking scores, drawn once and shared by every state.

    Parameters
    ----------
    columns : mapping of str to array
        Full-length columns by name.
    views : mapping of str to ColumnView, optional
        How each column is drawn; a missing one is linear with *Auto* range.
    rows : array of bool, optional
        Rows eligible for ranking (the gates' survivors). Ignored when the
        labels need every row (:attr:`ClassLabels.use_all_rows`).
    labels : ClassLabels, optional
        The classes to separate.
    max_rows : int
        Subsample size. The **same** rows serve every state, so two views are
        compared on identical bursts.
    seed : int
        Subsample seed; a ranking is reproducible.
    weights : array, optional
        Full-length burst weights for the population score (photon counts:
        a bright burst's shot-noise width is narrower). Rows without a
        finite, positive weight are left out of the sample.
    """

    def __init__(
        self,
        columns: Mapping[str, np.ndarray],
        views: Optional[Mapping[str, ColumnView]] = None,
        rows: Optional[np.ndarray] = None,
        labels: Optional[ClassLabels] = None,
        max_rows: int = DEFAULT_MAX_ROWS,
        seed: int = 0,
        weights: Optional[np.ndarray] = None,
    ):
        self.columns = dict(columns)
        self.weights = weights
        #: Sampled weights (mean 1), or ``None``; and their total, what shares are of.
        self.w: Optional[np.ndarray] = None
        self.total_weight = 0.0
        self.views = dict(views or {})
        self.rows = rows
        self.labels = labels
        self.max_rows = int(max_rows)
        self.seed = int(seed)
        self.n_eligible = 0
        self.coords: Dict[str, np.ndarray] = {}
        self.raw: Dict[str, np.ndarray] = {}
        #: Distinct drawable values per column, over the sample.
        self.distinct: Dict[str, int] = {}
        self.y: Optional[np.ndarray] = None
        self.prepared = False

    def view(self, name: str) -> ColumnView:
        """The view for *name* (linear, *Auto* range when none was given)."""
        return self.views.get(name) or ColumnView(name)

    def prepare(self) -> None:
        """Draw the subsample and transform every column once.

        A column that is constant (or has no drawable value) over the sampled
        rows is dropped here, as Orange's correlation widget drops constant
        features: it has no projection to rank.
        """
        if self.prepared:
            return
        n = len(next(iter(self.columns.values()))) if self.columns else 0
        eligible = np.ones(n, dtype=bool)
        if self.rows is not None and not (self.labels is not None and self.labels.use_all_rows):
            eligible &= np.asarray(self.rows, dtype=bool)
        if self.labels is not None:
            eligible &= np.isfinite(np.asarray(self.labels.values, dtype=np.float64))
        if self.weights is not None:
            weights = np.asarray(self.weights, dtype=np.float64)
            eligible &= np.isfinite(weights) & (weights > 0)
        index = np.flatnonzero(eligible)
        self.n_eligible = int(index.size)
        if index.size > self.max_rows > 0:
            rng = np.random.default_rng(self.seed)
            index = np.sort(rng.choice(index, self.max_rows, replace=False))
        self.index = index
        if self.weights is not None and index.size:
            w = np.asarray(self.weights, dtype=np.float64)[index]
            self.w = w / w.mean()
        self.total_weight = float(self.w.sum()) if self.w is not None else float(index.size)
        for name, values in self.columns.items():
            raw = np.asarray(values, dtype=np.float64)[index]
            coords = display_coordinates(raw, self.view(name))
            finite = coords[np.isfinite(coords)]
            if finite.size < 2 or np.ptp(finite) == 0:
                continue
            self.raw[name] = raw
            self.coords[name] = coords
            self.distinct[name] = int(np.unique(finite).size)
        if self.labels is not None:
            self.y = np.asarray(self.labels.values, dtype=np.float64)[index]
        self.prepared = True

    @property
    def names(self) -> List[str]:
        """Columns that survived :meth:`prepare`, in the order given."""
        return [n for n in self.columns if n in self.coords]

    @property
    def n_rows(self) -> int:
        """Rows in the subsample."""
        return int(self.index.size) if self.prepared else 0

    def derived_from(self, sources: Sequence[str], threshold: float = DERIVED_RHO) -> List[str]:
        """Columns that are (nearly) a monotone function of one of *sources*.

        ndX computes columns from others by equations: ``E_tau`` is a function
        of ``Tau (green)``, a rate is a count over a duration. Leaving out the
        parameter a gate is defined on is not enough when a transform of it is
        still in the table -- it separates the gate just as trivially. A
        Spearman ``|ρ|`` at or above *threshold* over the sample is the test,
        because ranks see through any monotone transform.
        """
        from scipy.stats import rankdata

        present = [n for n in sources if n in self.raw]
        if not present:
            return []
        out = []
        ranked = {}

        def ranks(name):
            if name not in ranked:
                values = self.raw[name]
                r = np.full(values.shape, np.nan)
                ok = np.isfinite(values)
                r[ok] = rankdata(values[ok])
                ranked[name] = r
            return ranked[name]

        for name in self.names:
            if name in sources:
                continue
            for source in present:
                a, b = ranks(name), ranks(source)
                ok = np.isfinite(a) & np.isfinite(b)
                if ok.sum() < MIN_K:
                    continue
                rho = np.corrcoef(a[ok], b[ok])[0, 1]
                if np.isfinite(rho) and abs(rho) >= threshold:
                    out.append(name)
                    break
        return out

    def matrix(self, names: Sequence[str]) -> np.ndarray:
        """Displayed coordinates of *names* as an ``(n_rows, len(names))`` array."""
        return np.column_stack([self.coords[n] for n in names])


# ---------------------------------------------------------------------------
# class separation (Orange's scatter-plot score)
# ---------------------------------------------------------------------------


def nearest_neighbours(points: np.ndarray, k: int) -> np.ndarray:
    """Indices of each point's *k* nearest other points, shape ``(n, k)``.

    The point itself is never among them — including when duplicates put
    another point at distance zero ahead of it, which is common in burst tables
    (integer photon counts). That matches ``NearestNeighbors.kneighbors()``
    called without query points, which is what Orange uses.
    """
    from scipy.spatial import cKDTree

    points = np.asarray(points, dtype=np.float64)
    if points.ndim == 1:
        points = points[:, None]
    n = points.shape[0]
    _, ind = cKDTree(points).query(points, k=k + 1)
    ind = np.asarray(ind).reshape(n, k + 1)
    is_self = ind == np.arange(n)[:, None]
    # Stable sort on "is it me" moves the self hit (if present) to the end and
    # keeps the distance order of the rest; without a self hit the last,
    # farthest neighbour is the one dropped.
    order = np.argsort(is_self, axis=1, kind="stable")
    return np.take_along_axis(ind, order, axis=1)[:, :k]


def knn_separation(
    points: np.ndarray,
    y: np.ndarray,
    *,
    discrete: bool,
    n_total: Optional[int] = None,
    k: int = MIN_K,
) -> Optional[float]:
    """Orange's scatter-plot VizRank score; lower is better.

    Parameters
    ----------
    points : array, shape (n,) or (n, d)
        The projection.
    y : array, shape (n,)
        Class ids (``discrete``) or values; ``NaN`` rows are dropped.
    discrete : bool
        Which of the two scores.
    n_total : int, optional
        Rows before dropping missing values; the continuous score is multiplied
        by the fraction that had values, so a projection that is defined for
        few bursts cannot win on those alone. Defaults to ``len(y)``.
    k : int
        Neighbours per point (Orange's ``minK``).

    Returns
    -------
    float or None
        Discrete: ``-mean(fraction of neighbours with the same class)``.
        Continuous: ``-R²(y, mean of neighbours' y) · n_valid / n_total``.
        ``None`` with fewer than *k* usable rows.
    """
    points = np.asarray(points, dtype=np.float64)
    if points.ndim == 1:
        points = points[:, None]
    y = np.asarray(y, dtype=np.float64)
    n_total = len(y) if n_total is None else int(n_total)
    valid = np.isfinite(points).all(axis=1) & np.isfinite(y)
    points, y = points[valid], y[valid]
    n = len(y)
    if n < k:
        return None
    n_neighbors = min(k, n - 1)
    ind = nearest_neighbours(points, n_neighbors)
    if discrete:
        return -float(np.sum(y[ind] == y[:, None])) / n_neighbors / n
    predicted = y[ind].mean(axis=1)
    total = float(np.sum((y - y.mean()) ** 2))
    if total == 0:
        return None
    r2 = 1.0 - float(np.sum((y - predicted) ** 2)) / total
    return -r2 * (n / n_total if n_total else 1.0)


def chance_corrected_agreement(same_fraction: float, y: np.ndarray) -> Optional[float]:
    """Neighbour agreement above what the class proportions give by chance.

    ``(p_o − p_e) / (1 − p_e)`` with ``p_e = Σ_c p_c²``, the agreement of a
    neighbour drawn at random. For one fixed set of rows it is a monotone
    function of Orange's score, so it ranks identically; it differs only across
    views whose missing values remove different rows — which is exactly where
    the raw fraction misleads, because a view that happens to drop the minority
    class scores perfect agreement.

    Returns ``None`` when only one class is left (nothing to separate).
    """
    y = np.asarray(y, dtype=np.float64)
    y = y[np.isfinite(y)]
    if y.size == 0:
        return None
    _, counts = np.unique(y, return_counts=True)
    p = counts / counts.sum()
    expected = float(np.sum(p * p))
    if expected >= 1.0:
        return None
    return (float(same_fraction) - expected) / (1.0 - expected)


# ---------------------------------------------------------------------------
# correlation (Orange's correlation score)
# ---------------------------------------------------------------------------


def correlation(a, b, method: str = "pearson") -> Tuple[float, float, float]:
    """Orange's correlation-rank score: ``(-|r|, r, p)``.

    Rows where either value is missing are dropped pairwise. Fewer than two
    rows give ``(inf, nan, nan)``; a constant column gives ``(inf, nan, nan)``
    too, which sorts it last. The p-value is the two-sided t-test of ``r = 0``
    (what ``scipy.stats.pearsonr`` reports); with exactly two rows it is 1.

    Parameters
    ----------
    a, b : array
        The two columns.
    method : str
        ``"pearson"``, or ``"spearman"`` (Pearson on average ranks).
    """
    from scipy.stats import rankdata, t as t_dist

    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    mask = np.isfinite(a) & np.isfinite(b)
    n = int(mask.sum())
    if n < 2:
        return math.inf, math.nan, math.nan
    a, b = a[mask], b[mask]
    if method == "spearman":
        a, b = rankdata(a), rankdata(b)
    a = a - a.mean()
    b = b - b.mean()
    denominator = math.sqrt(float(np.dot(a, a)) * float(np.dot(b, b)))
    if denominator == 0:
        return math.inf, math.nan, math.nan
    r = max(-1.0, min(1.0, float(np.dot(a, b)) / denominator))
    if n == 2:
        p = 1.0
    elif abs(r) >= 1.0:
        p = 0.0
    else:
        dof = n - 2
        t_stat = r * math.sqrt(dof / (1.0 - r * r))
        p = float(2.0 * t_dist.sf(abs(t_stat), dof))
    return -abs(r), r, p


# ---------------------------------------------------------------------------
# the columns worth ranking for populations and correlation
# ---------------------------------------------------------------------------


def correlation_ratio(y, x, bins: int = 32) -> float:
    """``η²`` of *y* given *x*: the share of y's variance its means in x's bins explain.

    Both in ``[0, 1]`` coordinates; rows missing either are left out. 1 when y
    is a function of x (monotone or not), 0 when x says nothing about y.
    """
    y = np.asarray(y, dtype=np.float64)
    x = np.asarray(x, dtype=np.float64)
    ok = np.isfinite(x) & np.isfinite(y)
    if ok.sum() < 2 * MIN_K:
        return 0.0
    x, y = x[ok], y[ok]
    total = float(np.sum((y - y.mean()) ** 2))
    if not total > 0:
        return 0.0
    b = np.clip((x * bins).astype(np.int64), 0, bins - 1)
    count = np.bincount(b, minlength=bins)
    means = np.bincount(b, y, bins) / np.maximum(count, 1)
    return 1.0 - float(np.sum((y - means[b]) ** 2)) / total


def is_clock(values) -> bool:
    """Whether a column rises from row to row: the acquisition clock.

    A burst table is in time order (file by file), so the first photon's index
    and the mean macrotime rise over nearly every pair of consecutive rows. A
    clock carries when a burst was seen, not what molecule it was, and its
    uneven file lengths would pass for "populations".
    """
    x = np.asarray(values, dtype=np.float64)
    x = x[np.isfinite(x)]
    return x.size > 2 * MIN_K and float(np.mean(np.diff(x) > 0)) >= CLOCK_RISE


class ColumnSet:
    """The columns of a :class:`RankingTable` worth ranking, prepared for density.

    Each column is fitted a :class:`~ndxplorer.analysis.separation.RobustAxis`
    in the scale ndX draws it with. Set aside, with the reason in
    :attr:`left_out`: flags (fewer than :data:`MIN_DISTINCT` values), the
    acquisition clock (:func:`is_clock`), columns with nothing left after
    outlier removal, and **folds** -- a column that is a many-to-one function of
    another (``(1-E)*E`` of ``E``, ``sigma_E = |Var(E)|^½``), which adds no
    information and piles density up where it folds. Columns that are the
    *same* quantity (Spearman ``|ρ| >= DERIVED_RHO``, or each a function of the
    other) are one :attr:`aliases` group, ranked once under the representative
    ndX has an axis range for, else the one computed last.
    """

    def __init__(self, table: RankingTable, exclude: Sequence[str] = ()):
        from .separation import RobustAxis

        table.prepare()
        self.axes: Dict[str, object] = {}
        self.coords: Dict[str, np.ndarray] = {}
        self.left_out: Dict[str, str] = {}
        ranks: Dict[str, np.ndarray] = {}
        for name in table.names:
            if name in exclude:
                continue
            raw = table.raw[name]
            if table.distinct.get(name, 0) < MIN_DISTINCT:
                self.left_out[name] = "a flag (few distinct values)"
                continue
            if is_clock(raw):
                self.left_out[name] = "the acquisition clock"
                continue
            axis, u = RobustAxis.fit(raw, table.view(name).scale)
            if axis is None or np.isfinite(u).sum() < 5 * MIN_K:
                self.left_out[name] = "nothing left after outliers"
                continue
            self.axes[name], self.coords[name] = axis, u
            # Ordinal ranks: the coordinates are continuous (counts are dithered),
            # and scipy.stats alone would cost a second to import.
            r = np.full(u.shape, np.nan)
            finite = np.isfinite(u)
            r[finite] = np.argsort(np.argsort(u[finite], kind="stable"), kind="stable")
            ranks[name] = r
        #: Ordinal ranks per column (Pearson on them is Spearman's ρ).
        self.ranks = ranks
        #: The ranks on [0, 1]. "Is one a function of the other" is asked of these,
        #: not of the coordinates: two species far apart on both axes explain most
        #: of each other's variance in coordinates (η² 0.95 on a planted pair), but
        #: within each species the ranks are independent, while a function stays
        #: a function of the other's ranks.
        self.uniform = {n: r / max(np.isfinite(r).sum() - 1, 1) for n, r in ranks.items()}
        eta2 = correlation_ratio
        u = self.uniform

        def rho(a: str, b: str) -> float:
            ok = np.isfinite(ranks[a]) & np.isfinite(ranks[b])
            if ok.sum() < 2 * MIN_K:
                return 0.0
            value = np.corrcoef(ranks[a][ok], ranks[b][ok])[0, 1]
            return abs(float(value)) if np.isfinite(value) else 0.0

        order = list(self.coords)
        def preference(name: str):
            view = table.view(name)
            return (view.lo is not None and view.hi is not None, order.index(name))

        groups: List[List[str]] = []
        for name in sorted(order, key=preference, reverse=True):
            for group in groups:
                head = group[0]
                if rho(head, name) >= DERIVED_RHO or (
                        eta2(u[head], u[name]) >= FUNCTION_ETA2
                        and eta2(u[name], u[head]) >= FUNCTION_ETA2):
                    group.append(name)
                    break
            else:
                groups.append([name])
        heads = [g[0] for g in groups]
        self.aliases: Dict[str, List[str]] = {g[0]: g[1:] for g in groups}
        for group in groups:
            for name in group[1:]:
                self.left_out[name] = f"the same as {group[0]}"
        for name in heads:
            for other in heads:
                if other != name and eta2(u[name], u[other]) >= FUNCTION_ETA2 \
                        and eta2(u[other], u[name]) < 0.9:
                    self.left_out[name] = f"a fold of {other}"
                    break
        #: The representatives, in table order.
        self.names: List[str] = [n for n in order if n in self.aliases and n not in self.left_out]

    def matrix(self, names: Sequence[str]) -> np.ndarray:
        """Density coordinates of *names* as an ``(n_rows, len(names))`` array."""
        return np.column_stack([self.coords[n] for n in names])

    def is_curve(self, a: str, b: str) -> bool:
        """Whether one of the two is (nearly) a function of the other in the sample."""
        u = self.uniform
        return max(correlation_ratio(u[a], u[b]), correlation_ratio(u[b], u[a])) >= CURVE_ETA2


# ---------------------------------------------------------------------------
# rankers
# ---------------------------------------------------------------------------


#: Score methods: key -> (caption, needs class labels, ranks pairs, ranks single columns).
METHODS: Dict[str, Tuple[str, bool, bool, bool]] = {
    "populations": ("Separation", False, True, True),
    "correlation": ("Correlation", False, True, False),
    "separation": ("Classes", True, True, True),
}

#: What each method means, for the panel's tooltip.
METHOD_HELP = {
    "populations": "How many bursts fall into clearly separated islands: donor-only, "
                   "acceptor-only and FRET species in E vs S, a dynamic population off the "
                   "static FRET line. 0: one population; 0.5: two equal islands with empty "
                   "space between; 0.67: three.",
    "correlation": "|Spearman rho| of the pair: parameters that measure related things (E and "
                   "a lifetime, a rate and its count), not populations. Parameters that are "
                   "the same quantity are ranked once.",
    "separation": "Do the bursts of one label (a gate, the clusters) sit together in this "
                  "view? Share of each burst's 10 nearest neighbours with its label, above "
                  "chance.",
}


def _label(view: ColumnView) -> str:
    return f"{view.name} (log)" if view.scale == "log" else view.name


def _rankable(table: RankingTable) -> List[str]:
    """Columns the class-separation score may use: not the class's own, nor derived from it."""
    excluded = set(table.labels.exclude) if table.labels is not None else set()
    if excluded:
        excluded.update(table.derived_from(sorted(excluded)))
    return [n for n in table.names if n not in excluded]


def _percent(shares) -> str:
    return ", ".join(f"{100 * s:.0f} %" for s in shares)


class _ScoredRanker:
    """Method dispatch shared by the pair and the single-column ranker."""

    table: RankingTable
    method: str
    columns: Optional[ColumnSet] = None
    #: The score column's bar range.
    score_span: Tuple[float, float] = (0.0, 1.0)

    def _init_scored(self, table: RankingTable, method: str) -> None:
        if method not in METHODS:
            raise ValueError(f"unknown ranking method {method!r}")
        if METHODS[method][1] and table.labels is None:
            raise ValueError(f"{METHODS[method][0]} needs class labels")
        self.table = table
        self.method = method
        self._sequence = 0
        self.score_span = {"populations": (0.0, 0.5), "correlation": (-1.0, 1.0)}.get(
            method, (0.0, 1.0))

    @property
    def header(self) -> Tuple[str, ...]:  # type: ignore[override]
        if self.method == "populations":
            return ("Separation",) + self._name_headers + ("Islands",)
        return ({"correlation": "ρ", "separation": "κ"}[self.method],) + self._name_headers

    def prepare(self) -> None:
        """Draw the sample (on the GUI thread: it reads the live table).

        Choosing the columns -- fitting axes, finding aliases and folds -- is
        left to the first :meth:`state_count`, which the panel calls in its
        worker, so a browser does not freeze on *Start*.
        """
        self.table.prepare()
        self.attrs = []
        self._attr_order = None
        self._columns_ready = False

    def _ensure_columns(self) -> None:
        if getattr(self, "_columns_ready", True):
            return
        self._columns_ready = True
        if self.method == "separation":
            self.attrs = _rankable(self.table)
        else:
            self.columns = ColumnSet(self.table)
            self.attrs = list(self.columns.names)
        self._attr_order = None

    def state_count(self) -> int:
        self._ensure_columns()
        return super().state_count()  # type: ignore[misc]

    def iterate_states(self):
        self._ensure_columns()
        return super().iterate_states()  # type: ignore[misc]

    def left_out(self) -> Dict[str, str]:
        """Columns set aside, with why (empty for the class-separation score)."""
        return dict(self.columns.left_out) if self.columns is not None else {}

    def _score(self, names: Sequence[str]):
        table = self.table
        if self.method == "correlation":
            ranks = self.columns.ranks
            return correlation(ranks[names[0]], ranks[names[1]])
        if self.method == "populations":
            from .separation import find_populations

            cols = self.columns
            if len(names) == 2 and cols.is_curve(*names):
                return None
            found = find_populations(cols.matrix(names), table.total_weight, table.w)
            if found is None:
                return None
            self._sequence += 1
            # (sort keys..., a tie-breaker so the Populations is never compared)
            return (-found.score, -found.count, self._sequence, found)
        points = table.matrix(names)
        y = table.y
        valid = np.isfinite(points).all(axis=1) & np.isfinite(y)
        raw = knn_separation(points, y, discrete=table.labels.discrete, n_total=len(y))
        if raw is None:
            return None
        if table.labels.discrete:
            kappa = chance_corrected_agreement(-raw, y[valid])
            return None if kappa is None else (-kappa, raw, int(valid.sum()))
        return (raw, raw, int(valid.sum()))

    def _aliases(self, names: Sequence[str]) -> str:
        if self.columns is None:
            return ""
        same = [a for n in names for a in self.columns.aliases.get(n, ())]
        return f" Also this view: {', '.join(same)}." if same else ""

    def _row(self, score, names: Sequence[str], payload) -> RankRow:
        views = [self.table.view(n) for n in names]
        labels = tuple(_label(v) for v in views)
        n = self.table.n_rows
        if self.method == "populations":
            found = score[3]
            value = found.score
            if found.count > 1:
                note = (f"{found.count} islands holding {_percent(found.shares)} of the "
                        f"{n} sampled bursts; {100 * found.in_islands:.0f} % sit clearly "
                        f"inside one (not on a bridge or in a tail). Score {value:.3f}: the "
                        f"chance that two bursts are in two different, clearly separated "
                        f"populations.")
            else:
                note = f"One population: no significant density valley over {n} sampled bursts."
            return RankRow((f"{value:.3f}",) + labels + (str(found.count),), payload,
                           min(1.0, value / 0.5), value, note + self._aliases(names))
        if self.method == "correlation":
            _, r, p = score
            if math.isnan(r):
                return RankRow(("N/A",) + labels, payload, None, -math.inf,
                               "No finite pairs, or a constant column.")
            return RankRow(
                (f"{r:+.3f}",) + labels, payload, abs(r), abs(r),
                f"Spearman ρ = {r:+.4f}, p = {p:.3g} over {n} sampled bursts: the two move "
                f"together, which says nothing about populations." + self._aliases(names),
                POSITIVE_COLOR if r >= 0 else NEGATIVE_COLOR, r)
        value, raw, n_valid = score
        classes = self.table.labels
        if classes.discrete:
            kappa = -value
            return RankRow(
                (f"{kappa:.3f}",) + labels, payload, min(1.0, max(0.0, kappa)), kappa,
                f"{-raw:.1%} of each burst's {MIN_K} nearest neighbours share its class "
                f"({classes.name}); κ = {kappa:.3f} above chance, over {n_valid} of {n} sampled rows.",
            )
        r2 = -raw
        return RankRow(
            (f"{r2:.3f}",) + labels, payload, min(1.0, max(0.0, r2)), r2,
            f"The mean {classes.name} of each burst's {MIN_K} nearest neighbours predicts its own "
            f"with R² = {r2 / (n_valid / n) if n_valid else 0:.3f}; weighted by the "
            f"{n_valid / n:.0%} of sampled rows that have values.",
        )

    def _order_by_single(self) -> List[str]:
        """Most promising columns first, by the same score in one dimension."""
        self._ensure_columns()
        if self.method == "correlation":
            return list(self.attrs)
        keyed = []
        for position, name in enumerate(self.attrs):
            score = self._score([name])
            keyed.append((math.inf if score is None else score[0], position, name))
        return [name for _, _, name in sorted(keyed)]

    def ranked_names(self, names: Sequence[str]) -> Optional[List[str]]:
        """The ranked columns that stand for *names*, or ``None``.

        A column merged into another as its alias (``Proximity ratio`` into
        ``FRET efficiency``) is represented by it: the same bursts in the same
        order, so the representative's islands label the alias' view too.
        """
        if self.method != "populations" or self.columns is None:
            return None
        axes, aliases = self.columns.axes, self.columns.aliases
        out = []
        for name in names:
            if name not in axes:
                name = next((r for r, same in aliases.items() if name in same), None)
                if name is None or name not in axes:
                    return None
            out.append(name)
        return out

    def islands(self, names: Sequence[str], values: Sequence[np.ndarray],
                core: bool = False) -> Optional[np.ndarray]:
        """The island of every row of *values* (full columns of *names*), -1 none.

        The islands are found again on the ranking's sample, as they were
        scored, and every burst of *values* is looked up in them through the
        axes' preparation (scale, sentinels, outlier fence, robust range).
        With *core* only bursts in an island's core are labelled; bridges,
        tails and outliers get -1. Islands are numbered largest first.
        """
        from .separation import find_populations

        if self.method != "populations" or self.columns is None:
            return None
        if any(n not in self.columns.axes for n in names):
            return None
        found = find_populations(self.columns.matrix(names), self.table.total_weight,
                                 self.table.w)
        if found is None:
            return None
        points = np.column_stack([self.columns.axes[n].transform(v)
                                  for n, v in zip(names, values)])
        return found.label(points, core=core)


class ProjectionRanker(_ScoredRanker, AttrPairRanker):
    """Rank x/y pairs of a burst table.

    The payload of a row is ``{"x", "y", "scale_x", "scale_y"}``: what ndX sets
    when the row is clicked, in the scales it was scored in.
    """

    dimension = 2
    _name_headers = ("x", "y")

    def __init__(self, table: RankingTable, method: str):
        self._init_scored(table, method)
        AttrPairRanker.__init__(self, [])

    def score_attributes(self) -> Sequence[str]:
        """Columns that split on their own first (Orange's ReliefF ordering), so
        the top of the table fills early."""
        return self._order_by_single()

    def compute_score(self, state):
        j, i = state
        order = self.attr_order
        return self._score([order[j], order[i]])

    def row_for_state(self, score, state) -> RankRow:
        j, i = state
        x, y = self.attr_order[j], self.attr_order[i]
        payload = {
            "x": x, "y": y,
            "scale_x": self.table.view(x).scale, "scale_y": self.table.view(y).scale,
        }
        return self._row(score, [x, y], payload)

    def matches(self, payload, wanted) -> bool:
        """The same two columns, in either order — a transposed view is the same view."""
        return {payload.get("x"), payload.get("y")} == {wanted.get("x"), wanted.get("y")}


class ParameterRanker(_ScoredRanker, AttrRanker):
    """Rank single columns — the z parameter. Payload ``{"z", "scale_z"}``."""

    dimension = 1
    _name_headers = ("Parameter",)

    def __init__(self, table: RankingTable, method: str):
        if not METHODS.get(method, ("", False, False, False))[3]:
            raise ValueError(f"{method!r} does not rank single columns")
        self._init_scored(table, method)
        AttrRanker.__init__(self, [])

    def score_attributes(self) -> Sequence[str]:
        self._ensure_columns()
        return self.attrs

    def compute_score(self, state):
        return self._score([self.attr_order[state]])

    def row_for_state(self, score, state) -> RankRow:
        name = self.attr_order[state]
        payload = {"z": name, "scale_z": self.table.view(name).scale}
        return self._row(score, [name], payload)

    def matches(self, payload, wanted) -> bool:
        return payload.get("z") == wanted.get("z")
