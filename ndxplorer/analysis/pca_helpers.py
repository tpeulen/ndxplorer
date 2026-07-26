"""Principal component analysis over selected parameter columns.

UMAP answers "are there groups?"; PCA answers a different and often more useful
question: **which of my parameters actually distinguish anything?** It is linear,
so every component is an interpretable weighted sum of the original columns, and
those weights — the *loadings* — are the part worth reading. A component that
loads almost entirely on one column says that column carries the variation on its
own; a component spreading evenly across five says those five are redundant.

That is why :func:`compute_pca` returns loadings and explained variance rather
than only the projected columns. Adding ``PC_1``/``PC_2`` to the table and
throwing the decomposition away discards the answer and keeps the picture.

Two things are easy to get wrong and are handled here:

**Scaling.** PCA maximises variance, and variance has units. A table holding a
photon count in the thousands beside an efficiency in ``[0, 1]`` yields a first
component that is simply the photon count, whatever the data say. Standardising
each column to zero mean and unit variance is the default for that reason;
``standardize=False`` exists for the case where the columns genuinely share a
scale and their relative magnitudes are the signal.

**Missing values.** Rows with a NaN or Inf in any selected column cannot be
projected. They are dropped for the fit and written back as NaN, so the added
columns stay aligned with the table row for row.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

import numpy as np
import pandas as pd

from ..logging_config import logging
from ..utils.lazy_imports import get_pca

if False:  # pragma: no cover
    from ..core.plot_main import NDXplorer

__all__ = [
    "PcaResult",
    "add_pca_columns",
    "compute_pca",
    "pca_available",
]

#: Above this many rows the batched estimator is used instead of the exact one.
INCREMENTAL_THRESHOLD = 1_000_000


def pca_available() -> bool:
    """Whether scikit-learn's PCA can be imported."""
    return get_pca() is not None


@dataclass
class PcaResult:
    """A fitted decomposition and everything needed to interpret it.

    Attributes
    ----------
    projections : numpy.ndarray
        ``(n_rows, n_components)`` scores, with ``NaN`` in rows that were
        dropped, so it aligns with the source table row for row.
    explained_variance_ratio : numpy.ndarray
        ``(n_components,)`` fraction of the total variance each component
        carries.
    loadings : numpy.ndarray
        ``(n_components, n_columns)`` weight of each input column in each
        component — the interpretable part.
    columns : list of str
        Input column names, in the order the loadings index them.
    n_samples : int
        Rows that survived the finite-value filter and were fitted.
    n_dropped : int
        Rows dropped for holding a NaN or Inf.
    standardized : bool
        Whether each column was scaled to unit variance before fitting.
    """

    projections: np.ndarray
    explained_variance_ratio: np.ndarray
    loadings: np.ndarray
    columns: List[str]
    n_samples: int = 0
    n_dropped: int = 0
    standardized: bool = True
    incremental: bool = False

    @property
    def n_components(self) -> int:
        """Number of components retained."""
        return int(self.loadings.shape[0])

    def top_contributors(self, component: int = 0, n: int = 3) -> List[tuple]:
        """Return the ``n`` columns weighing most on *component*.

        Parameters
        ----------
        component : int
            Zero-based component index.
        n : int
            How many columns to return.

        Returns
        -------
        list of (str, float)
            ``(column, loading)`` ordered by descending absolute loading. The
            sign is kept: two columns loading with opposite signs are being
            *contrasted* by that component, which is usually the interesting
            reading.
        """
        weights = np.asarray(self.loadings[int(component)], dtype=float)
        order = np.argsort(np.abs(weights))[::-1][: int(n)]
        return [(self.columns[i], float(weights[i])) for i in order]

    def report(self) -> str:
        """Return a human-readable summary of the decomposition."""
        lines = [
            f"PCA over {len(self.columns)} columns, {self.n_samples:,} rows"
            + (f" ({self.n_dropped:,} dropped for non-finite values)" if self.n_dropped else "")
        ]
        if not self.standardized:
            lines.append("columns NOT standardised — components follow the largest-scale column")
        total = 0.0
        for i, share in enumerate(self.explained_variance_ratio):
            total += float(share)
            top = ", ".join(f"{c} {w:+.2f}" for c, w in self.top_contributors(i, 3))
            lines.append(f"  PC_{i + 1}: {100 * share:5.1f} % (cumulative {100 * total:5.1f} %)"
                         f"   {top}")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        """Return a JSON-compatible summary (projections excluded — they are bulk)."""
        return {
            "columns": list(self.columns),
            "explained_variance_ratio": np.asarray(
                self.explained_variance_ratio, dtype=float
            ).tolist(),
            "loadings": np.asarray(self.loadings, dtype=float).tolist(),
            "n_samples": int(self.n_samples),
            "n_dropped": int(self.n_dropped),
            "standardized": bool(self.standardized),
            "incremental": bool(self.incremental),
        }


def compute_pca(
    data: np.ndarray,
    columns: Sequence[str],
    n_components: int = 2,
    standardize: bool = True,
    batch_size: int = 10_000,
) -> Optional[PcaResult]:
    """Fit a principal component analysis to *data*.

    Parameters
    ----------
    data : numpy.ndarray
        ``(n_rows, n_columns)``; non-finite rows are dropped for the fit and
        written back as ``NaN``.
    columns : sequence of str
        Column names, in the same order as the data columns.
    n_components : int
        Components to retain. Clamped to the number of usable columns and rows.
    standardize : bool
        Scale each column to unit variance first. **Leave this on** unless the
        columns genuinely share a scale: PCA maximises variance, so without it a
        column measured in thousands dominates one measured in units regardless
        of what either says.
    batch_size : int
        Batch size for the incremental estimator, used above
        :data:`INCREMENTAL_THRESHOLD` rows.

    Returns
    -------
    PcaResult or None
        ``None`` when scikit-learn is unavailable, or no row survives.
    """
    backend = get_pca()
    if backend is None:
        logging.error("scikit-learn is not available; cannot compute PCA.")
        return None
    pca_cls, incremental_cls = backend

    data = np.asarray(data, dtype=float)
    if data.ndim != 2 or data.shape[1] == 0:
        logging.error("PCA needs a 2-D array with at least one column.")
        return None

    finite = ~np.any(~np.isfinite(data), axis=1)
    clean = data[finite]
    n_dropped = int(data.shape[0] - clean.shape[0])
    if clean.shape[0] < 2:
        logging.warning("Not enough finite rows for PCA (need at least 2).")
        return None

    if standardize:
        centre = clean.mean(axis=0)
        scale = clean.std(axis=0)
        # A constant column has zero variance and carries no information; scaling
        # it by zero would produce NaN and poison every component.
        scale[scale == 0.0] = 1.0
        prepared = (clean - centre) / scale
    else:
        prepared = clean - clean.mean(axis=0)

    n_components = max(1, min(int(n_components), prepared.shape[1], prepared.shape[0]))
    use_incremental = prepared.shape[0] > INCREMENTAL_THRESHOLD
    if use_incremental:
        model = incremental_cls(n_components=n_components,
                                batch_size=max(int(batch_size), n_components))
    else:
        model = pca_cls(n_components=n_components, svd_solver="auto", random_state=0)

    scores = model.fit_transform(prepared)

    projections = np.full((data.shape[0], n_components), np.nan)
    projections[finite] = scores
    return PcaResult(
        projections=projections,
        explained_variance_ratio=np.asarray(model.explained_variance_ratio_, dtype=float),
        loadings=np.asarray(model.components_, dtype=float),
        columns=list(columns),
        n_samples=int(clean.shape[0]),
        n_dropped=n_dropped,
        standardized=bool(standardize),
        incremental=bool(use_incremental),
    )


def add_pca_columns(
    ndxplorer: "NDXplorer",
    columns: Sequence[str],
    n_components: int = 2,
    standardize: bool = True,
) -> Optional[PcaResult]:
    """Compute PCA over *columns* and add ``PC_n`` columns to the data source.

    Mirrors :func:`~ndxplorer.analysis.umap_helpers.add_umap_columns`, including
    the single write-back: the ``data`` setter reconverts the whole frame, so
    every component is assigned before it is touched once.

    Parameters
    ----------
    ndxplorer : NDXplorer
        The explorer whose data source is read and extended.
    columns : sequence of str
        Columns to decompose. Names absent from the table are skipped.
    n_components : int
        Components to retain and add as columns.
    standardize : bool
        See :func:`compute_pca`.

    Returns
    -------
    PcaResult or None
        The decomposition, so the caller can show the loadings — which are the
        answer PCA was asked for. ``None`` if nothing could be computed.
    """
    if ndxplorer.data_source is None or ndxplorer.data_source.empty:
        logging.error("No data available for PCA.")
        return None

    df = ndxplorer.data_source.data
    used: List[str] = []
    selected: List[np.ndarray] = []
    for column in columns:
        if column in df.columns:
            selected.append(pd.to_numeric(df[column], errors="coerce").values)
            used.append(column)
        else:
            logging.warning("PCA: column '%s' is not in the table; skipping.", column)
    if len(selected) < 2:
        logging.error("PCA needs at least two valid columns, got %d.", len(selected))
        return None

    result = compute_pca(
        np.column_stack(selected), used,
        n_components=n_components, standardize=standardize,
    )
    if result is None:
        return None

    for i in range(result.n_components):
        df[f"PC_{i + 1}"] = result.projections[:, i]
    # One assignment: the setter reconverts the frame, so doing it per column
    # would pay that cost n times over.
    ndxplorer.data_source.data = df
    try:
        ndxplorer.refresh_axis_comboboxes_preserving_selection()
    except Exception:  # pragma: no cover - headless use has no combo boxes
        logging.debug("PCA: could not refresh axis combo boxes", exc_info=True)
    logging.info("PCA added %d columns\n%s", result.n_components, result.report())
    return result
