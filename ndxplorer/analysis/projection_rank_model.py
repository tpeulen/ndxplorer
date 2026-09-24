"""Ranked x/y pairs and z parameters for ndX: the Qt-free half.

*Find informative projections…* ranks every pair of parameters (or every third
parameter) by how informative the view is; what "informative" means is chosen
in the panel (:data:`~ndxplorer.analysis.projection_scores.METHODS`). This
module says what a ranking may use (:func:`build_context`) and is the model the
panel binds to (:class:`ProjectionRankModel`). The Qt window wires it in
through :mod:`ndxplorer.ui.projection_rank`; the emtk app through
:mod:`ndxplorer.app.features.playback_export`.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np

from .projection_scores import (
    DEFAULT_MAX_ROWS,
    METHOD_HELP,
    METHODS,
    ClassLabels,
    ColumnView,
    ParameterRanker,
    ProjectionRanker,
    RankingTable,
)
from .vizrank_model import VizRankModel

logger = logging.getLogger(__name__)

__all__ = [
    "MAX_DISCRETE_VALUES",
    "Z_CLASS_PREFIX",
    "PHOTON_MODES",
    "RankingContext",
    "build_context",
    "photon_column",
    "ProjectionRankModel",
]

#: A column with at most this many distinct integer values is a class id when
#: it is used as the class; anything else is a quantity.
MAX_DISCRETE_VALUES = 10

#: Caption prefix of the class that is the z parameter's value.
Z_CLASS_PREFIX = "z parameter: "

#: How bursts count in the Separation score: key -> caption. Low-photon bursts
#: are wide (shot noise) and fill the valleys between populations.
PHOTON_MODES = {
    "all": "All bursts, equal weight",
    "weight": "Weight by photons",
    "min": "Only bursts with at least Min photons",
}


def photon_column(names) -> str:
    """The burst's total photon count column, or ``""`` when the table has none."""
    names = list(names)
    if "Number of Photons" in names:
        return "Number of Photons"
    return next((n for n in names if n.startswith("Number of Photons")), "")


@dataclass
class RankingContext:
    """What ndX offers a ranking at the moment a ranking is (re)built.

    Attributes
    ----------
    columns : dict
        Numeric columns by name, as views into the table (nothing is copied
        until the ranker draws its subsample).
    views : dict
        :class:`ColumnView` per column: the scale and range ndX draws it with.
    rows : numpy.ndarray
        Rows the gates keep.
    classes : dict
        Caption -> :class:`ClassLabels`, in the order offered.
    key : tuple
        Changes whenever the table, the axis settings or the gates change — any
        of which invalidates every ranked row.
    class_keys : dict
        Caption -> what that class additionally depends on (the clustering,
        the z parameter), so choosing another z invalidates only a ranking that
        separates by z.
    """

    columns: Dict[str, np.ndarray]
    views: Dict[str, ColumnView]
    rows: Optional[np.ndarray]
    classes: Dict[str, ClassLabels] = field(default_factory=dict)
    key: Tuple = ()
    class_keys: Dict[str, Tuple] = field(default_factory=dict)


def _selection_columns(selection, names: List[str]) -> Tuple[str, ...]:
    """The parameter names a gate reads."""
    indices = []
    for attr in ("parameter_idx", "idx1", "idx2"):
        value = getattr(selection, attr, None)
        if value is not None:
            indices.append(int(value))
    return tuple(names[i] for i in indices if 0 <= i < len(names))


def _column_labels(name: str, values: np.ndarray) -> ClassLabels:
    """A column as the class: ids when it looks like ids, a quantity otherwise."""
    values = np.asarray(values, dtype=np.float64)
    finite = values[np.isfinite(values)]
    unique = np.unique(finite) if finite.size else finite
    discrete = bool(
        unique.size <= MAX_DISCRETE_VALUES and unique.size > 1 and np.all(unique == np.round(unique))
    )
    return ClassLabels(values, discrete, name, exclude=(name,))

def build_context(source, axis_settings: Optional[Dict[str, dict]] = None,
                  selections: Sequence = (), clusters=None,
                  z_name: str = "") -> Optional[RankingContext]:
    """What a ranking can use: the table's numeric columns, how each is drawn,
    the rows the gates keep and the classes on offer.

    Both GUIs call this with what they hold -- the Qt window through
    :func:`ndxplorer.ui.projection_rank.collect_context`, the emtk app from its
    :class:`~ndxplorer.app.model.ExplorerModel`.

    Parameters
    ----------
    source : ndxplorer.core.data_source.DataSource or None
        The table.
    axis_settings : dict, optional
        Per-parameter axis settings (``scale``, ``min``, ``max``).
    selections : sequence
        The enabled gates, as selection objects.
    clusters : array-like, optional
        Cluster labels, one per row (negative: noise).
    z_name : str
        The z parameter, offered as a class.

    Returns
    -------
    RankingContext or None
        ``None`` when there is no table to rank.
    """
    if source is None or source.empty:
        return None
    selections = list(selections or ())
    all_names = list(source.parameter_names)
    columns: Dict[str, np.ndarray] = {}
    for index, name in enumerate(all_names):
        if source.is_text_column(index):
            continue
        view = source.column_view(index)
        if view is not None:
            columns[name] = view

    settings = axis_settings or {}
    views: Dict[str, ColumnView] = {}
    for name in columns:
        entry = settings.get(name)
        if entry:
            views[name] = ColumnView(
                name, str(entry.get("scale", "lin")), entry.get("min"), entry.get("max")
            )
        else:
            views[name] = ColumnView(name)

    rows = source.selection_mask(selections) if selections else None

    classes: Dict[str, ClassLabels] = {}
    class_keys: Dict[str, Tuple] = {}
    if selections:
        gated = tuple(sorted({n for s in selections for n in _selection_columns(s, all_names)}))
        inside = source.selection_mask(selections).astype(np.float64)
        classes["Gate: inside vs outside"] = ClassLabels(
            inside, True, "inside vs outside the gate", exclude=gated, use_all_rows=True
        )
        if len(selections) >= 2:
            masks = np.vstack([source.selection_mask([s]) for s in selections])
            hits = masks.sum(axis=0)
            labels = np.where(hits == 1, np.argmax(masks, axis=0).astype(np.float64), np.nan)
            classes["Gates: one population per gate"] = ClassLabels(
                labels, True, "the gate a burst falls in", exclude=gated, use_all_rows=True
            )
    if clusters is not None and len(clusters) == source.size:
        values = np.asarray(clusters, dtype=np.float64)
        # HDBSCAN's noise label is "no cluster", not a population of its own.
        values = np.where(values < 0, np.nan, values)
        classes["Clusters"] = ClassLabels(values, True, "cluster")
        class_keys["Clusters"] = (id(clusters),)
    if z_name in columns:
        # Only a z that holds labels (a population index, cluster ids): a
        # quantity is not a class to separate.
        z_labels = _column_labels(z_name, source.column_values(z_name))
        if z_labels.discrete:
            caption = f"{Z_CLASS_PREFIX}{z_name}"
            classes[caption] = z_labels
            class_keys[caption] = (z_name,)

    key = (
        id(source),
        source.data_version,
        tuple(columns),
        tuple(sorted((n, v.scale, v.lo, v.hi) for n, v in views.items())),
        tuple(repr(s.gate_key()) if hasattr(s, "gate_key") else repr(s) for s in selections),
    )
    return RankingContext(columns, views, rows, classes, key, class_keys)

class ProjectionRankModel(VizRankModel):
    """What the ranking panel binds to in ndX: pairs (x/y) or single parameters (z).

    Parameters
    ----------
    context_provider : callable
        Returns a fresh :class:`RankingContext`; called when a ranking starts
        and whenever the panel asks what classes exist, so a restart always sees
        the current table and gates.
    pairs : bool
        Rank x/y pairs (``True``) or z parameters.
    **kwargs
        Passed to :class:`~ndxplorer.analysis.vizrank_model.VizRankModel`.
    """

    def __init__(self, context_provider: Callable[[], Optional[RankingContext]],
                 pairs: bool = True, **kwargs):
        super().__init__(**kwargs)
        self.pairs = pairs
        self.title = "Find informative projections" if pairs else "Find informative z parameters"
        self._context_provider = context_provider
        self._context: Optional[RankingContext] = context_provider()
        self.sample_rows = DEFAULT_MAX_ROWS
        self.classes = ""
        self.method = "populations"
        self.photon_mode = "all"
        self.min_photons = 100
        #: The host can paint the islands of the selected row on its map.
        self.overlay_available = False
        #: Paint them (the host reads this).
        self.show_islands = False
        self._pick_defaults()

    # ---- what the spec's choices offer ---------------------------------------------

    def method_options(self) -> list:
        """``(key, label)`` of the scores this panel ranks by.

        Classes are offered only when there is something to separate, so the
        choice cannot land on a score that has no classes to read.
        """
        has_classes = bool(self.class_options())
        options = []
        for key, (caption, needs, for_pairs, for_single) in METHODS.items():
            if not ((self.pairs and for_pairs) or (not self.pairs and for_single)):
                continue
            if needs and not has_classes:
                continue
            options.append((key, caption))
        return options

    def method_text(self) -> str:
        """What the chosen score means, in FRET terms (the line under the choice)."""
        return METHOD_HELP.get(self.method, "")

    @property
    def min_photons_hidden(self) -> bool:
        """*Min photons* only matters for Separation with the threshold chosen."""
        return not (self.method == "populations" and self.photon_mode == "min")

    @property
    def islands_toggle_hidden(self) -> bool:
        """The islands toggle needs a host that paints them, and the Separation score."""
        return not (self.overlay_available and self.method == "populations" and self.pairs)

    def islands_changed(self, *_value) -> None:
        """*Show islands on the map* was switched: the host repaints."""
        self._changed()

    def class_options(self) -> list:
        """The classes ndX has now, by caption."""
        context = self._context
        if context is None:
            return []
        return [caption for caption in context.classes
                if self.pairs or not caption.startswith(Z_CLASS_PREFIX)]

    def photon_options(self) -> list:
        """``(key, label)`` of how bursts count; weighting needs a photon column."""
        context = self._context
        names = context.columns if context is not None else ()
        keys = ("all", "weight", "min") if photon_column(names) else ("all",)
        return [(key, PHOTON_MODES[key]) for key in keys]

    def _pick_defaults(self) -> None:
        """Separation always; the first class ready for when *Classes* is chosen."""
        options = self.class_options()
        made = [c for c in options if not c.startswith(Z_CLASS_PREFIX)]
        self.classes = made[0] if made else (options[0] if options else "")
        self.method = "populations"

    def refresh_context(self) -> None:
        """Re-read what ndX offers; keep the chosen classes if they still exist."""
        self._context = self._context_provider()
        options = self.class_options()
        if self.classes not in options:
            self.classes = options[0] if options else ""
            if not options and self.method == "separation":
                self.method = "populations"
        if self.photon_mode not in dict(self.photon_options()):
            self.photon_mode = "all"
        self._changed()

    # ---- the ranking -----------------------------------------------------------------

    def _check_method(self) -> None:
        """Fall back to Separation when the chosen score is not on offer (any more)."""
        if self.method not in dict(self.method_options()):
            self.method = "populations"

    def current_settings(self):
        """Method, classes, sample, photons -- and the table and gates they read."""
        self._check_method()
        context = self._context_provider()
        classes = self.classes if METHODS.get(self.method, ("", False))[1] else None
        photons = (self.photon_mode, int(self.min_photons) if self.photon_mode == "min" else 0) \
            if self.method == "populations" else None
        if context is None:
            return (self.method, classes, int(self.sample_rows), photons, None, None)
        return (self.method, classes, int(self.sample_rows), photons, context.key,
                context.class_keys.get(classes))

    def make_ranker(self):
        context = self._context_provider()
        self._context = context
        if context is None:
            raise RuntimeError("no table to rank")
        self._check_method()
        labels = None
        if METHODS[self.method][1]:
            labels = context.classes.get(self.classes)
            if labels is None:
                raise RuntimeError("the chosen classes are no longer available")
        rows, weights = context.rows, None
        photons = photon_column(context.columns)
        if self.method == "populations" and photons and self.photon_mode != "all":
            counts = np.asarray(context.columns[photons], dtype=np.float64)
            if self.photon_mode == "weight":
                weights = counts
            else:
                enough = counts >= float(self.min_photons)
                rows = enough if rows is None else (np.asarray(rows, dtype=bool) & enough)
        table = RankingTable(context.columns, context.views, rows=rows, labels=labels,
                             max_rows=int(self.sample_rows), weights=weights)
        return (ProjectionRanker if self.pairs else ParameterRanker)(table, self.method)

    def note(self) -> str:
        """What was sampled, and how many parameters were set aside (once known)."""
        if self._run is None:
            return ""
        ranker = self._run.ranker
        table = ranker.table
        note = f"{table.n_rows} of {table.n_eligible} bursts sampled"
        if getattr(ranker, "_columns_ready", True):
            left_out = len(table.columns) - len(ranker.attrs)
            if left_out:
                note += f" · {left_out} parameters left out or merged"
        return note

    def ranked_key(self):
        """The table/axes/gates key the current ranking was made from, or ``None``."""
        return self._run.settings[4] if self._run is not None else None

    def islands(self, names, values):
        """The island of every burst in *values* for the view *names*, or ``None``."""
        if self._run is None or not hasattr(self._run.ranker, "islands"):
            return None
        return self._run.ranker.islands(names, values)
