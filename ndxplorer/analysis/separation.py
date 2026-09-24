"""Where does a burst cloud split into populations? The density-valley score.

In smFRET the informative view is not the one where two parameters co-vary but
the one where the molecules fall apart into species: donor-only, acceptor-only
and FRET populations in E vs S, a dynamic population off the static FRET line in
E vs τ. This module scores that, unsupervised, for one axis or a pair.

The score reads the **density's topology**. The bursts are binned on a
``GRID``-cell raster (per axis, ``GRID ** d`` cells) and smoothed with a Gaussian
of Scott-like width; every cell climbs to its highest neighbour, so each local
maximum collects a basin. Two basins meet at a *saddle*, and merging them from
the highest saddle down -- the elder rule of 0-dimensional persistent homology
-- pairs every population but the largest with the valley that separates it
from a denser one. A split counts -- and the two sides become separate *islands*
-- when

* its valley is significant against the shot noise of the histogram, ``z =
  (peak - saddle) / sqrt(var_peak + var_saddle) >= Z_MIN`` (Poisson variances of
  the smoothed counts, so a thin sample's bumps do not count);
* the smaller side holds at least ``MIN_POPULATION`` of the sampled bursts (a
  tail or a clump of outliers is not a species).

The score asks how much of the burst cloud falls into clearly separable
islands::

    score = sum over island pairs i != j of  p_i * p_j * sep_ij

``p_i`` is the share of the sampled bursts in island *i*'s **core** -- above
its highest valley to any other island, so bursts on a bridge between two
populations, in a tail or in the noise do not count -- and ``sep_ij = 1 -
saddle_ij / min(peak_i, peak_j)`` is how deep the valley between the two is (the
gap against the widths: 1 with empty space between them, 0 when they touch).
It is the chance that two bursts drawn at random sit in two different, clearly
separated populations: 0 for one population however elongated, correlated or
skewed; 0.5 for two equal islands with empty space between them, 0.18 for a 10 %
island off a 90 % blob, 0.67 for three equal islands (donor-only, FRET and
acceptor-only in E vs S).

Each axis is prepared the way the calibration prepares its gating dimensions
(:class:`RobustAxis`): values an axis cannot draw become missing, a single value
holding a sizeable share of the column (a fit's bound or sentinel, ``-1`` for
"not fitted") is missing too, counted or rounded columns are spread over their step,
outliers are removed with :func:`tttrlib.flag_dimension_outliers`, and only
then is the axis mapped onto ``[0, 1]`` by its robust range. So the score is
invariant to each axis' units and offset and is not stretched by one wild burst.

Why a density valley rather than the alternatives (measured on the MFD and
ALEX test tables; see the OKF concept ``plugins/ndxplorer-emtk-port``): HDBSCAN
per pair (``tttrlib.hdbscan``) agreed on synthetic splits but was 8x slower and
noisier on real tables, where it cut uniform acquisition-time columns and
photon counts into "clusters"; a Gaussian-mixture BIC gain rewards any skewed
or curved single population (log-normal count rates, a banana) as "three
components". The valley is ~1 ms per pair in NumPy, so it stays here rather
than in tttrlib: the work is a histogram, a filter and a few vector passes.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import List, Optional, Sequence, Tuple

import numpy as np

__all__ = [
    "GRID",
    "MIN_POPULATION",
    "Z_MIN",
    "SPIKE_SHARE",
    "RobustAxis",
    "Populations",
    "find_populations",
]

#: Raster cells per axis.
GRID = 64
#: Smallest share of the sampled bursts the smaller side of a split must hold.
MIN_POPULATION = 0.03
#: Valley significance against the histogram's shot noise, in standard deviations.
Z_MIN = 3.0
#: A single exact value holding at least this share of a continuous column is
#: a bound or a sentinel (``gamma = 0`` for two thirds of the MFD bursts, ``-1``
#: where the red channel was not fitted), not a population of molecules.
SPIKE_SHARE = 0.02
#: ...and at least this many times the typical count of a distinct value, so the
#: steps of a rounded column are not mistaken for spikes.
SPIKE_RATIO = 10.0
#: The raster spans the robust range plus this margin on either side.
MARGIN = 0.05
#: Kernel width in units of the robust range, before the ``n ** (-1 / (d + 4))``
#: of Scott's rule: about 0.6 Scott widths of a single Gaussian cloud, since
#: Scott's rule oversmooths the multimodal clouds this is looking for.
BANDWIDTH = 0.125


@dataclass
class RobustAxis:
    """An axis prepared for density scoring: scale, sentinels, outliers, range.

    Fitted on a sample (:meth:`fit`) and applicable to any rows of the same
    column (:meth:`transform`), which is how the populations found on the
    sample label every burst of the table.
    """

    scale: str = "lin"
    lo: float = 0.0
    hi: float = 1.0
    fence_lo: float = -math.inf
    fence_hi: float = math.inf
    atoms: Tuple[float, ...] = ()
    quantum: float = 0.0  #: the step of a counted or rounded column, 0 for continuous

    def _drawable(self, values) -> np.ndarray:
        x = np.asarray(values, dtype=np.float64)
        if self.scale == "log":
            with np.errstate(invalid="ignore", divide="ignore"):
                x = np.where(x > 0, np.log10(np.where(x > 0, x, 1.0)), np.nan)
        return np.where(np.isfinite(x), x, np.nan)

    @classmethod
    def fit(cls, values, scale: str = "lin", seed: int = 1) -> Tuple[Optional["RobustAxis"], np.ndarray]:
        """Fit an axis on *values*; returns ``(axis, coordinates)``.

        ``(None, all-NaN)`` for a column with nothing left to score.
        """
        import tttrlib

        axis = cls(scale=scale)
        raw = np.asarray(values, dtype=np.float64)
        nothing = (None, np.full(raw.shape, np.nan))
        finite = raw[np.isfinite(raw)]
        if finite.size < 20:
            return nothing
        unique, counts = np.unique(finite, return_counts=True)
        axis.quantum = _quantum(unique, finite.size)
        if axis.quantum > 0:
            # Counts, or values rounded to a step: spread each over its step, or
            # the raster sees a comb of "populations" one step apart.
            raw = raw + np.random.default_rng(seed).uniform(-0.5, 0.5, raw.shape) * axis.quantum
        else:
            spikes = (counts >= SPIKE_SHARE * finite.size) & (counts >= SPIKE_RATIO * np.median(counts))
            axis.atoms = tuple(float(v) for v in unique[spikes])
            if axis.atoms:
                raw = np.where(np.isin(raw, axis.atoms), np.nan, raw)
        x = axis._drawable(raw)
        if np.isfinite(x).sum() < 20:
            return nothing
        # Named "x" so no gating rule of the calibration (S, E, tau, r) applies:
        # only the quantile fence does.
        flags = tttrlib.flag_dimension_outliers(x[:, None], ["x"])
        fence = flags["by_dimension"]["x"]
        axis.fence_lo = fence["lo"] if np.isfinite(fence["lo"]) else -math.inf
        axis.fence_hi = fence["hi"] if np.isfinite(fence["hi"]) else math.inf
        x = np.where(flags["mask"], np.nan, x)
        kept = x[np.isfinite(x)]
        if kept.size < 20:
            return nothing
        lo, hi = np.percentile(kept, [0.5, 99.5])
        if not hi > lo:
            return nothing
        axis.lo, axis.hi = float(lo), float(hi)
        return axis, axis._unit(x)

    def _unit(self, x: np.ndarray) -> np.ndarray:
        u = (x - self.lo) / (self.hi - self.lo)
        return np.where((u >= -MARGIN) & (u <= 1.0 + MARGIN), u, np.nan)

    def transform(self, values) -> np.ndarray:
        """Coordinates of any rows of the column (no dither: a label lookup)."""
        raw = np.asarray(values, dtype=np.float64)
        if self.atoms:
            raw = np.where(np.isin(raw, self.atoms), np.nan, raw)
        x = self._drawable(raw)
        x = np.where((x < self.fence_lo) | (x > self.fence_hi), np.nan, x)
        return self._unit(x)


def _quantum(unique: np.ndarray, n: int) -> float:
    """The step every distinct value sits on (1 for counts), or 0 when continuous.

    Only for columns with far fewer distinct values than rows, whose gaps are
    all whole multiples of the smallest one.
    """
    if unique.size < 3 or unique.size > n // 3:
        return 0.0
    gaps = np.diff(unique)
    step = float(gaps.min())
    if not step > 0:
        return 0.0
    multiples = gaps / step
    if np.all(np.abs(multiples - np.round(multiples)) < 1e-3):
        return step
    return 0.0


@dataclass
class Populations:
    """What :func:`find_populations` found in one view: its islands.

    An *island* is a population cut off from the others by a density valley
    that is significant against the shot noise.
    """

    score: float
    shares: List[float] = field(default_factory=list)  #: bursts per island, largest first
    cores: List[float] = field(default_factory=list)   #: bursts above the island's valleys
    separability: Optional[np.ndarray] = None  #: 1 - saddle / lower peak, per island pair
    n_used: int = 0
    cells: Optional[np.ndarray] = None  #: island per raster cell, -1 none

    @property
    def count(self) -> int:
        """How many islands (1: one population)."""
        return len(self.shares)

    @property
    def in_islands(self) -> float:
        """Share of the sampled bursts in island cores: not bridge, tail or noise."""
        return float(sum(self.cores)) if len(self.shares) > 1 else 0.0

    def label(self, points) -> np.ndarray:
        """The population of each row of *points* (``(n, d)`` coordinates), -1 none."""
        points = np.asarray(points, dtype=np.float64)
        points = points[:, None] if points.ndim == 1 else points
        out = np.full(points.shape[0], -1, dtype=np.int64)
        if self.cells is None:
            return out
        ok = np.isfinite(points).all(axis=1)
        index = _cell_index(points[ok], self.cells.shape[0])
        out[ok] = self.cells[tuple(index.T)]
        return out


def _cell_index(points: np.ndarray, grid: int) -> np.ndarray:
    scaled = (points + MARGIN) / (1.0 + 2.0 * MARGIN) * grid
    return np.clip(scaled.astype(np.int64), 0, grid - 1)


def _shifted(array: np.ndarray, offset: Sequence[int], fill) -> np.ndarray:
    """*array* read at ``index + offset`` (``fill`` beyond the edge)."""
    out = np.full(array.shape, fill, dtype=array.dtype)
    src, dst = [], []
    for size, o in zip(array.shape, offset):
        src.append(slice(max(0, o), size + min(0, o)))
        dst.append(slice(max(0, -o), size + min(0, -o)))
    out[tuple(dst)] = array[tuple(src)]
    return out


def find_populations(points, n_total: Optional[float] = None, weights=None,
                     grid: int = GRID, z_min: float = Z_MIN,
                     min_population: float = MIN_POPULATION) -> Optional[Populations]:
    """Find the populations of a 1-D or 2-D point cloud in ``[0, 1]`` coordinates.

    Parameters
    ----------
    points : array, shape (n,) or (n, d), d in {1, 2}
        :class:`RobustAxis` coordinates; rows with a missing value are left out
        but still count in *n_total*.
    n_total : float, optional
        What shares are shares of: the sample's total weight (its row count
        without *weights*). Defaults to the total over every row of *points*.
    weights : array, optional
        Per-row weights, e.g. photon counts (bright bursts have narrower
        shot-noise widths); the significance uses their squares.

    Returns
    -------
    Populations or None
        ``None`` with fewer than 50 usable rows.
    """
    from scipy import ndimage

    p = np.asarray(points, dtype=np.float64)
    p = p[:, None] if p.ndim == 1 else p
    w_all = None if weights is None else np.asarray(weights, dtype=np.float64)
    ok = np.isfinite(p).all(axis=1)
    if w_all is not None:
        ok &= np.isfinite(w_all) & (w_all >= 0)
    if n_total is None:
        n_total = float(np.nansum(w_all)) if w_all is not None else float(len(p))
    p, w = p[ok], (None if w_all is None else w_all[ok])
    n, d = p.shape
    if n < 50 or d not in (1, 2) or not n_total > 0:
        return None
    n_eff = n if w is None else float(w.sum() ** 2 / max(np.sum(w * w), 1e-300))
    sigma = max(1.0, BANDWIDTH * n_eff ** (-1.0 / (d + 4)) * grid / (1.0 + 2.0 * MARGIN))

    flat_index = np.ravel_multi_index(tuple(_cell_index(p, grid).T), (grid,) * d)
    size = grid ** d
    h = np.bincount(flat_index, weights=w, minlength=size).astype(np.float64).reshape((grid,) * d)
    h2 = h if w is None else np.bincount(flat_index, weights=w * w, minlength=size).reshape(h.shape)
    f = ndimage.gaussian_filter(h, sigma, mode="constant")
    # Var of a Gaussian-smoothed count: sum(w^2 K^2) = (K/sqrt2 * h2) / (4 pi s^2)^(d/2)
    var = ndimage.gaussian_filter(h2, sigma / math.sqrt(2.0), mode="constant") \
        / (4.0 * math.pi * sigma * sigma) ** (d / 2.0)

    valid = f > f.max() * 1e-4
    cell_ids = np.arange(size).reshape(f.shape)
    offsets = [tuple(o) for o in np.ndindex(*(3,) * d)]
    offsets = [tuple(c - 1 for c in o) for o in offsets]
    # Steepest ascent: every cell points at its highest neighbour (itself at a peak).
    values = np.stack([_shifted(f, o, -np.inf) for o in offsets])
    ids = np.stack([_shifted(cell_ids, o, -1) for o in offsets])
    parent = np.take_along_axis(ids, np.argmax(values, axis=0)[None], 0)[0].ravel()
    parent = np.where(valid.ravel(), parent, -1)
    for _ in range(2 * grid * d):
        nxt = np.where(parent >= 0, parent[np.maximum(parent, 0)], -1)
        if np.array_equal(nxt, parent):
            break
        parent = nxt
    peaks, basin = np.unique(parent[parent >= 0], return_inverse=True)
    basin_of = np.full(size, -1, dtype=np.int64)
    basin_of[parent >= 0] = basin
    k = peaks.size
    mass = np.bincount(basin, weights=h.ravel()[parent >= 0], minlength=k)
    peak = f.ravel()[peaks]
    peak_var = var.ravel()[peaks]

    # Saddles: the highest crossing between each pair of touching basins.
    grid_basin = basin_of.reshape(f.shape)
    saddle = {}
    for o in offsets[len(offsets) // 2 + 1:]:  # half the neighbourhood
        a, b = grid_basin, _shifted(grid_basin, o, -1)
        m = (a >= 0) & (b >= 0) & (a != b)
        if not m.any():
            continue
        level = np.minimum(f[m], _shifted(f, o, 0.0)[m])
        key = np.minimum(a[m], b[m]) * k + np.maximum(a[m], b[m])
        keys, inverse = np.unique(key, return_inverse=True)
        top = np.full(keys.size, -np.inf)
        np.maximum.at(top, inverse, level)
        for kk, vv in zip(keys.tolist(), top.tolist()):
            if vv > saddle.get(kk, -np.inf):
                saddle[kk] = vv

    # Elder rule: from the highest saddle down, the lower peak dies into the higher.
    root = list(range(k))

    def find(i: int) -> int:
        while root[i] != i:
            root[i] = root[root[i]]
            i = root[i]
        return i

    comp_mass, comp_peak = mass.tolist(), peak.tolist()
    merges = []
    edges = [(level, divmod(key, k)) for key, level in saddle.items()]
    edges.sort(key=lambda e: -e[0])
    for level, (a, b) in edges:
        ra, rb = find(a), find(b)
        if ra == rb:
            continue
        if comp_peak[ra] < comp_peak[rb]:
            ra, rb = rb, ra
        merges.append((rb, ra, level, min(comp_mass[rb], comp_mass[ra])))
        root[rb] = ra
        comp_mass[ra] += comp_mass[rb]
    alive = sorted({find(i) for i in range(k)}, key=lambda i: -comp_peak[i])
    for rb in alive[1:]:  # islands: empty space all round
        merges.append((rb, alive[0], 0.0, min(comp_mass[rb], comp_mass[alive[0]])))
        root[rb] = alive[0]
        comp_mass[alive[0]] += comp_mass[rb]

    kept = []  # the merges that separate two islands, in falling saddle order
    for dying, into, level, smaller in merges:
        top, v = comp_peak[dying], peak_var[dying]
        z = (top - level) / math.sqrt(max(v * (1.0 + level / top), 1e-300)) if top > 0 else 0.0
        if z >= z_min and smaller / n_total >= min_population:
            kept.append((dying, into, level))
    apart = {m[0] for m in kept}

    # Islands: the basins joined by every merge that did not count.
    root = list(range(k))
    for dying, into, _level, _smaller in merges:
        if dying not in apart:
            root[find(dying)] = find(into)
    final = [find(i) for i in range(k)]
    island_roots = sorted(set(final), key=lambda r: -sum(m for f_, m in zip(final, mass) if f_ == r))
    number = {r: i for i, r in enumerate(island_roots)}
    island_of_basin = np.array([number[r] for r in final], dtype=np.int64)
    n_islands = len(island_roots)
    top = np.array([peak[[b for b in range(k) if final[b] == r]].max() for r in island_roots])

    # The saddle between two islands: the level at which the merge tree joins them.
    between = np.zeros((n_islands, n_islands))
    group = {i: {i} for i in range(n_islands)}
    owner = list(range(n_islands))
    for dying, into, level in kept:
        a, b = owner[number[find(dying)]], owner[number[find(into)]]
        if a == b:
            continue
        for i in group[a]:
            for j in group[b]:
                between[i, j] = between[j, i] = level
        group[b] |= group.pop(a)
        for i in group[b]:
            owner[i] = b

    cells = np.where(basin_of >= 0, island_of_basin[np.maximum(basin_of, 0)], -1).reshape(f.shape)
    separability = np.zeros((n_islands, n_islands))
    core = np.zeros(n_islands)
    shares = np.bincount(island_of_basin, weights=mass, minlength=n_islands) / n_total
    if n_islands > 1:
        lowest = np.minimum.outer(top, top)
        separability = np.where(lowest > 0, 1.0 - between / np.where(lowest > 0, lowest, 1.0), 0.0)
        np.fill_diagonal(separability, 0.0)
        # An island's core: its bursts above its highest valley to any other
        # island. What lies at or below that level is bridge or tail.
        rim = between.max(axis=1)
        flat_cells = cells.ravel()
        inside = flat_cells >= 0
        above = inside & (f.ravel() > rim[np.maximum(flat_cells, 0)])
        core = np.bincount(flat_cells[above], weights=h.ravel()[above],
                           minlength=n_islands) / n_total
    score = float(core @ separability @ core)  # = sum over i != j of p_i p_j sep_ij
    return Populations(score, shares.tolist(), core.tolist(), separability, n, cells)
