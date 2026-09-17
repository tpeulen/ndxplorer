"""Scores for ranking burst-table projections, and the rankers that use them.

Three questions, three scores. Every one is vectorised over the rows of a
subsample drawn once per ranking, so a pair costs milliseconds whatever the
table size.

**Does this view separate the classes?** — :func:`knn_separation`. Transcribed
from Orange3's scatter-plot VizRank (``ScatterPlotVizRank.compute_score``,
``Orange/widgets/visualize/owscatterplot.py``; Bioinformatics Lab, University of
Ljubljana, GPL-3.0): for every point take its ``k = 10`` nearest neighbours in
the projection; with a discrete class the score is the fraction of neighbours
sharing the point's class, with a continuous one it is the R² of predicting the
value by the neighbours' mean, down-weighted by the fraction of rows with a
value. The class is whatever ndX has: the gate (inside vs outside), each gate as
its own population, the clusters, or a column.

Two deliberate departures, both argued where they are made:

* the neighbours are found in **displayed** coordinates — each axis mapped to
  ``[0, 1]`` over the range and scale ndX will draw it with — rather than in raw
  units, where a photon count (thousands) swamps a lifetime (nanoseconds) and
  the "separating" projection is simply the one with the largest numbers;
* the discrete score is reported **chance-corrected**
  (:func:`chance_corrected_agreement`): a gate holding 5 % of the bursts makes
  every projection score ≥ 0.9 by the majority class alone.

**How strongly do two columns co-vary?** — :func:`correlation`, Orange3's
``CorrelationRank.compute_score`` (``Orange/widgets/data/owcorrelations.py``):
Pearson or Spearman over the rows where both are finite, ``-|r|`` as the score
and ``inf`` below two rows.

**Is there more than one population in this view?** — :func:`cluster_index`.
Not from Orange: its unsupervised rankers (sieve, mosaic) test independence of
*discrete* variables, which says nothing about whether a burst cloud splits into
populations — two independent bimodal axes give four blobs and a χ² of zero. The
score is the **2-means cluster index** of SigClust (Liu, Hayes, Nobel & Marron,
*J. Am. Stat. Assoc.* 103, 1281 (2008), doi:10.1198/016214508000000454): the
within-cluster sum of squares of the best split into two, over the total. The
points are first whitened, which makes the index affine-invariant and gives it a
closed-form Gaussian reference — ``1 − 2/π`` along the split direction — so a
population that is merely elongated, correlated or on different units
scores like a single Gaussian, and only a real split scores below it. See
:func:`cluster_index` for why the split is found exactly rather than by k-means
restarts.
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
    "GAUSSIAN_CLUSTER_INDEX",
    "ColumnView",
    "ClassLabels",
    "RankingTable",
    "display_coordinates",
    "nearest_neighbours",
    "knn_separation",
    "chance_corrected_agreement",
    "correlation",
    "cluster_index",
    "structure_from_index",
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

#: Smallest share of the sampled bursts the smaller of two populations must hold
#: for a split to count (see :func:`cluster_index`).
MIN_POPULATION = 0.05

#: Spearman ``|ρ|`` above which a column counts as derived from another (see
#: :meth:`RankingTable.derived_from`).
DERIVED_RHO = 0.98

#: The 2-means cluster index of a Gaussian along its split direction: the
#: optimal split is at the mean, and the between-cluster share of the variance
#: is ``(E|x|)² / var = 2/π``.
GAUSSIAN_CLUSTER_INDEX = 1.0 - 2.0 / math.pi

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
    """

    def __init__(
        self,
        columns: Mapping[str, np.ndarray],
        views: Optional[Mapping[str, ColumnView]] = None,
        rows: Optional[np.ndarray] = None,
        labels: Optional[ClassLabels] = None,
        max_rows: int = DEFAULT_MAX_ROWS,
        seed: int = 0,
    ):
        self.columns = dict(columns)
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
        index = np.flatnonzero(eligible)
        self.n_eligible = int(index.size)
        if index.size > self.max_rows > 0:
            rng = np.random.default_rng(self.seed)
            index = np.sort(rng.choice(index, self.max_rows, replace=False))
        self.index = index
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
# cluster structure (the unsupervised score)
# ---------------------------------------------------------------------------


def _whiten(points: np.ndarray, condition: float = 1e-6) -> Optional[np.ndarray]:
    """Centre and whiten; ``None`` for a degenerate cloud.

    A pair whose covariance is (nearly) singular — two columns that are the
    same quantity — has no second dimension to whiten, and its index would be
    compared against the wrong Gaussian reference. It is refused rather than
    scored as spectacularly "structured".
    """
    centred = points - points.mean(axis=0)
    cov = centred.T @ centred / len(centred)
    evals, evecs = np.linalg.eigh(cov)
    if not (evals[-1] > 0) or evals[0] <= condition * evals[-1]:
        return None
    return centred @ (evecs / np.sqrt(evals))


def cluster_index(
    points: np.ndarray,
    n_directions: int = 18,
    refine: int = 5,
    min_rows: int = 2 * MIN_K,
    min_fraction: float = MIN_POPULATION,
) -> Optional[float]:
    """SigClust's 2-means cluster index of the whitened cloud; lower = more split.

    ``CI = W / T``: the within-cluster sum of squares of the best partition into
    two, over the total sum of squares. In two dimensions it is reported along
    the split direction (``2·CI₂ − 1``; see the end of the function), so a
    Gaussian gives :data:`GAUSSIAN_CLUSTER_INDEX` = 0.363 in one dimension and in
    two, and two well-separated populations drive it towards 0.

    The partition is found **exactly along each of** *n_directions*
    **directions** rather than by k-means from random starts. In one dimension
    the optimal 2-means split is a threshold, and with the points sorted the
    within-cluster sums of squares for *every* threshold follow from two prefix
    sums — one ``argsort`` and a few ``cumsum``\\ s, no iteration. In two
    dimensions the same holds along any direction (the perpendicular coordinate
    contributes its own prefix sums), and the optimal 2-means boundary is a line,
    so scanning directions every 10° finds it to within the angular step; a few
    Lloyd iterations from that partition close the gap. Deterministic, and
    vectorised over directions × thresholds.

    Parameters
    ----------
    points : array, shape (n,) or (n, d) with d in {1, 2}
        Rows with a missing coordinate are dropped.
    n_directions : int
        Directions scanned in 2-D (half-circle).
    refine : int
        Lloyd iterations after the scan.
    min_rows : int
        Fewer usable rows than this give ``None``.
    min_fraction : float
        The smaller group must hold at least this share of the rows. Without
        it the best "split" of a burst table is routinely a clump of a few
        per cent at a fit's bound or sentinel (``rho = 10⁴`` in 2.7 % of the MFD
        test bursts): a perfect split, and not a population.
    """
    points = np.asarray(points, dtype=np.float64)
    if points.ndim == 1:
        points = points[:, None]
    points = points[np.isfinite(points).all(axis=1)]
    n, d = points.shape
    if n < min_rows or d not in (1, 2):
        return None
    z = _whiten(points)
    if z is None:
        return None
    total = float(np.sum(z * z))
    if d == 1:
        along = z
        across = None
        directions = np.ones((1, 1))
    else:
        angles = np.linspace(0.0, math.pi, n_directions, endpoint=False)
        directions = np.column_stack([np.cos(angles), np.sin(angles)])
        normals = np.column_stack([-np.sin(angles), np.cos(angles)])
        along = z @ directions.T
        across = z @ normals.T

    order = np.argsort(along, axis=0, kind="stable")
    counts = np.arange(1, n, dtype=np.float64)[:, None]

    def split_ss(coordinate: np.ndarray) -> np.ndarray:
        """Within SS of both sides for every threshold, shape (n-1, directions)."""
        s = np.take_along_axis(coordinate, order, axis=0)
        c1 = np.cumsum(s, axis=0)[:-1]
        c2 = np.cumsum(s * s, axis=0)[:-1]
        t1 = c1[-1] + s[-1]
        t2 = c2[-1] + s[-1] ** 2
        left = c2 - c1 * c1 / counts
        right = (t2 - c2) - (t1 - c1) ** 2 / (n - counts)
        return left + right

    within = split_ss(along)
    if across is not None:
        within = within + split_ss(across)
    smallest = max(1, int(np.ceil(min_fraction * n)))
    too_small = (counts[:, 0] < smallest) | (n - counts[:, 0] < smallest)
    within[too_small] = np.inf
    if not np.isfinite(within).any():
        return None
    best = np.unravel_index(int(np.argmin(within)), within.shape)
    threshold_rank, direction = int(best[0]), int(best[1])
    labels = np.zeros(n, dtype=bool)
    labels[order[: threshold_rank + 1, direction]] = True

    best_within = float(within[best])
    for _ in range(refine):
        if labels.all() or not labels.any():
            break
        c_true = z[labels].mean(axis=0)
        c_false = z[~labels].mean(axis=0)
        new = np.sum((z - c_true) ** 2, axis=1) < np.sum((z - c_false) ** 2, axis=1)
        if np.array_equal(new, labels) or min(new.sum(), n - new.sum()) < smallest:
            break
        w_new = float(
            np.sum((z[new] - z[new].mean(axis=0)) ** 2)
            + np.sum((z[~new] - z[~new].mean(axis=0)) ** 2)
        )
        if w_new >= best_within:
            break
        labels, best_within = new, w_new
    if not total > 0:
        return None
    # Expressed per split direction: whitening leaves every other direction
    # with its full variance inside both clusters, so ``CI_2d = (CI + 1) / 2``
    # where ``CI`` is the index along the split. Reporting that ``CI`` puts a
    # pair and a single column on one scale with one Gaussian reference.
    return d * best_within / total - (d - 1)


def structure_from_index(index: float) -> float:
    """``1 − CI / CI_gauss``: 0 for a Gaussian, towards 1 for a clean split.

    Two equal populations ``Δ`` standard deviations apart give
    ``CI = 4 / (Δ² + 4)`` along the split: 0.45 at ``Δ = 4``, 0.72 at ``Δ = 6``.
    Negative for clouds *less* splittable than a Gaussian (heavy tails, a
    uniform disc); positive values are what is worth looking at.
    """
    return 1.0 - float(index) / GAUSSIAN_CLUSTER_INDEX


# ---------------------------------------------------------------------------
# rankers
# ---------------------------------------------------------------------------


#: Score methods: key -> (caption, needs class labels, available for pairs,
#: available for single columns).
METHODS: Dict[str, Tuple[str, bool, bool, bool]] = {
    "separation": ("Class separation (k-NN)", True, True, True),
    "structure": ("Population structure (2-means)", False, True, True),
    "pearson": ("Correlation (Pearson)", False, True, False),
    "spearman": ("Correlation (Spearman)", False, True, False),
}


def _label(view: ColumnView) -> str:
    return f"{view.name} (log)" if view.scale == "log" else view.name


def _rankable(table: RankingTable, method: str) -> List[str]:
    """The columns a ranking may use: not the class's own, nor derived from it.

    For population structure, flags with fewer than :data:`MIN_DISTINCT`
    values are left out too.
    """
    excluded = set(table.labels.exclude) if table.labels is not None else set()
    if excluded:
        excluded.update(table.derived_from(sorted(excluded)))
    names = [n for n in table.names if n not in excluded]
    if method == "structure":
        names = [n for n in names if table.distinct.get(n, 0) >= MIN_DISTINCT]
    return names


class _ScoredRanker:
    """Method dispatch shared by the pair and the single-column ranker."""

    table: RankingTable
    method: str
    dimension: int

    def _init_scored(self, table: RankingTable, method: str) -> None:
        if method not in METHODS:
            raise ValueError(f"unknown ranking method {method!r}")
        if METHODS[method][1] and table.labels is None:
            raise ValueError(f"{METHODS[method][0]} needs class labels")
        self.table = table
        self.method = method

    @property
    def header(self) -> Tuple[str, ...]:  # type: ignore[override]
        caption = {
            "separation": "Separation",
            "structure": "Structure",
            "pearson": "r",
            "spearman": "ρ",
        }[self.method]
        return (caption,) + self._name_headers

    def _score(self, names: Sequence[str]):
        table = self.table
        method = self.method
        if method in ("pearson", "spearman"):
            return correlation(table.raw[names[0]], table.raw[names[1]], method)
        points = table.matrix(names)
        if method == "structure":
            index = cluster_index(points)
            return None if index is None else (index,)
        labels = table.labels
        y = table.y
        valid = np.isfinite(points).all(axis=1) & np.isfinite(y)
        raw = knn_separation(points, y, discrete=labels.discrete, n_total=len(y))
        if raw is None:
            return None
        if labels.discrete:
            kappa = chance_corrected_agreement(-raw, y[valid])
            return None if kappa is None else (-kappa, raw, int(valid.sum()))
        return (raw, raw, int(valid.sum()))

    def _row(self, score, names: Sequence[str], payload) -> RankRow:
        views = [self.table.view(n) for n in names]
        labels = tuple(_label(v) for v in views)
        method = self.method
        n = self.table.n_rows
        if method in ("pearson", "spearman"):
            _, r, p = score
            symbol = "r" if method == "pearson" else "ρ"
            if math.isnan(r):
                return RankRow(("N/A",) + labels, payload, None, -math.inf,
                               "No finite pairs, or a constant column.")
            return RankRow(
                (f"{r:+.3f}",) + labels, payload, abs(r), abs(r),
                f"{symbol} = {r:+.4f}, p = {p:.3g} over {n} sampled rows "
                f"(missing values dropped pairwise).",
                POSITIVE_COLOR if r >= 0 else NEGATIVE_COLOR,
                r,
            )
        if method == "structure":
            index = score[0]
            structure = structure_from_index(index)
            return RankRow(
                (f"{structure:.3f}",) + labels, payload,
                min(1.0, max(0.0, structure)), structure,
                f"2-means cluster index {index:.3f} against {GAUSSIAN_CLUSTER_INDEX:.3f} "
                f"for one Gaussian population ({n} bursts); above 0 splits better than one.",
            )
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

    def prepare(self) -> None:
        self.table.prepare()
        self.attrs = _rankable(self.table, self.method)
        self._attr_order = None

    def score_attributes(self) -> Sequence[str]:
        """Most promising columns first, by the same score in one dimension.

        Plays the part of Orange's ReliefF ordering — pairs among the columns
        that already separate (or split) on their own are scored first, so the
        top of the table is filled early. Correlation has no one-column form and
        keeps the table order.
        """
        if self.method not in ("separation", "structure"):
            return self.attrs
        single = ParameterRanker(self.table, self.method)
        single.attrs = list(self.attrs)
        keyed = []
        for position, name in enumerate(self.attrs):
            score = single._score([name])
            keyed.append((math.inf if score is None else score[0], position, name))
        return [name for _, _, name in sorted(keyed)]

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

    def prepare(self) -> None:
        self.table.prepare()
        self.attrs = _rankable(self.table, self.method)
        self._attr_order = None

    def compute_score(self, state):
        return self._score([self.attr_order[state]])

    def row_for_state(self, score, state) -> RankRow:
        name = self.attr_order[state]
        payload = {"z": name, "scale_z": self.table.view(name).scale}
        return self._row(score, [name], payload)

    def matches(self, payload, wanted) -> bool:
        return payload.get("z") == wanted.get("z")
