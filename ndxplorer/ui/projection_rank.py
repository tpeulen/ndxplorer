"""*Find informative projections…*: ranked x/y pairs and z parameters for ndX.

ndX asks the user to pick two axes out of forty-odd burst parameters. Two View
menu entries, directly below *UMAP*, rank every pair instead (*Find informative
projections…*) or every third parameter (*… (z axis)…*); clicking a row sets the
axes. What
"informative" means is chosen in the panel (:data:`~ndxplorer.analysis.projection_scores.METHODS`):

* **Class separation** — how well a view separates classes ndX already has:
  the gate (inside vs outside), each gate as its own population, the
  clusters, or the z parameter's value;
* **Population structure** — whether the view splits into more than one
  population, with no classes at all;
* **Correlation** — how strongly two parameters co-vary (pairs only).

Everything here is ndX wiring: which rows and classes exist, how an axis is
drawn, and what applying a row changes. The scores are in
:mod:`ndxplorer.analysis.projection_scores`, the ranking machinery in
:mod:`ndxplorer.ui.vizrank_panel` (the panel is ``vizrank.view.json``, drawn by
emtk).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

from ..analysis.projection_scores import (
    DEFAULT_MAX_ROWS,
    METHODS,
    ClassLabels,
    ColumnView,
    ParameterRanker,
    ProjectionRanker,
    RankingTable,
)
from .vizrank_panel import VizRankModel, VizRankWindow

logger = logging.getLogger(__name__)

__all__ = [
    "RankingContext",
    "collect_context",
    "ProjectionRankModel",
    "ProjectionRankController",
    "install_projection_ranking",
]

#: A column with at most this many distinct integer values is a class id when
#: it is used as the class; anything else is a quantity.
MAX_DISCRETE_VALUES = 10

#: Caption prefix of the class that is the z parameter's value.
Z_CLASS_PREFIX = "z parameter: "


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


def collect_context(window) -> Optional[RankingContext]:
    """Read the table, the axis settings, the gates and the classes from *window*.

    Returns ``None`` when there is no table to rank.
    """
    source = getattr(window, "data_source", None)
    if source is None or source.empty:
        return None
    control = window.plot_control
    all_names = list(source.parameter_names)
    columns: Dict[str, np.ndarray] = {}
    for index, name in enumerate(all_names):
        if source.is_text_column(index):
            continue
        view = source.column_view(index)
        if view is not None:
            columns[name] = view

    settings = getattr(control, "axis_settings", {}) or {}
    views: Dict[str, ColumnView] = {}
    for name in columns:
        entry = settings.get(name)
        if entry:
            views[name] = ColumnView(
                name, str(entry.get("scale", "lin")), entry.get("min"), entry.get("max")
            )
        else:
            views[name] = ColumnView(name)

    try:
        selections = [s for s in control.get_selections() if getattr(s, "enabled", True)]
    except Exception:
        logger.debug("could not read the gates", exc_info=True)
        selections = []
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
    clusters = getattr(window, "_cluster_labels", None)
    if clusters is not None and len(clusters) == source.size:
        values = np.asarray(clusters, dtype=np.float64)
        # HDBSCAN's noise label is "no cluster", not a population of its own.
        values = np.where(values < 0, np.nan, values)
        classes["Clusters"] = ClassLabels(values, True, "cluster")
        class_keys["Clusters"] = (id(clusters),)
    try:
        z_name = control.p3[1]
    except Exception:
        z_name = ""
    if z_name in columns:
        caption = f"{Z_CLASS_PREFIX}{z_name}"
        classes[caption] = _column_labels(z_name, source.column_values(z_name))
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
        Passed to :class:`~ndxplorer.ui.vizrank_panel.VizRankModel`.
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
        self.method = "structure"
        self.sample_note = ""
        self._pick_defaults()

    # ---- what the spec's choices offer ---------------------------------------------

    def method_options(self) -> list:
        """``(key, label)`` of the scores this panel ranks by.

        Class separation is offered only when there is something to separate,
        so the choice cannot land on a score that has no classes to read.
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

    def class_options(self) -> list:
        """The classes ndX has now, by caption."""
        context = self._context
        if context is None:
            return []
        return [caption for caption in context.classes
                if self.pairs or not caption.startswith(Z_CLASS_PREFIX)]

    def _pick_defaults(self) -> None:
        """Separation when the user has made classes, else structure.

        The z parameter is always there, so it is always *offered* as a class,
        but it is not a sign that the user wants views separated by it: only a
        gate or a clustering is. Without one, the question is whether a view
        shows populations at all.
        """
        made = [c for c in self.class_options() if not c.startswith(Z_CLASS_PREFIX)]
        options = self.class_options()
        self.classes = made[0] if made else (options[0] if options else "")
        self.method = "separation" if made else "structure"

    def refresh_context(self) -> None:
        """Re-read what ndX offers; keep the chosen classes if they still exist."""
        self._context = self._context_provider()
        options = self.class_options()
        if self.classes not in options:
            self.classes = options[0] if options else ""
            if not options and self.method == "separation":
                self.method = "structure"
        self._changed()

    # ---- the ranking -----------------------------------------------------------------

    def current_settings(self):
        """Method, classes, sample size -- and the table and gates they read."""
        context = self._context_provider()
        classes = self.classes if METHODS.get(self.method, ("", False))[1] else None
        if context is None:
            return (self.method, classes, int(self.sample_rows), None, None)
        return (self.method, classes, int(self.sample_rows), context.key,
                context.class_keys.get(classes))

    def make_ranker(self):
        context = self._context_provider()
        self._context = context
        if context is None:
            raise RuntimeError("no table to rank")
        labels = None
        if METHODS[self.method][1]:
            labels = context.classes.get(self.classes)
            if labels is None:
                raise RuntimeError("the chosen classes are no longer available")
        table = RankingTable(context.columns, context.views, rows=context.rows, labels=labels,
                             max_rows=int(self.sample_rows))
        ranker = (ProjectionRanker if self.pairs else ParameterRanker)(table, self.method)
        return ranker

    def prepare_run(self) -> None:
        super().prepare_run()
        table = self._run.ranker.table
        dropped = len(table.columns) - len(table.names)
        left_out = len(table.names) - len(self._run.ranker.attrs) + dropped
        note = f"{table.n_rows} of {table.n_eligible} bursts sampled"
        if left_out:
            note += f" · {left_out} parameters left out"
        self.sample_note = note

    def note(self) -> str:
        return self.sample_note if self._run is not None else ""


class ProjectionRankController:
    """Owns the two ranking panels of one ndX window and wires them in.

    Orange keeps this in a widget mixin (``VizRankMixin``); ndX's window is
    built from a ``.ui`` file and a dozen mixins already, so the same duties —
    the menu entries, one panel per data, apply on select, select on manual change —
    live in a plain object instead.
    """

    def __init__(self, window):
        self.window = window
        #: The panel windows, by ``pairs``; each carries its ``model``.
        self.dialogs: Dict[bool, Any] = {}
        self._applying = False

    # ---- menu entries --------------------------------------------------------------

    #: The View-menu actions (declared in ``plotting/plot_main.ui`` directly below
    #: *UMAP*), by ``pairs``. Their enabled state is the window's: like *UMAP*,
    #: they are disabled while no table is loaded (``update_ui_enabled_state``).
    ACTIONS = {True: "actionFindProjections", False: "actionFindZParameters"}

    def install(self) -> None:
        """Connect the View-menu entries and follow hand-picked axes."""
        for pairs, name in self.ACTIONS.items():
            action = getattr(self.window, name, None)
            if action is None:
                logger.debug("projection ranking: the window has no %s", name)
                continue
            action.triggered.connect(lambda _checked=False, p=pairs: self.open(p))
        control = self.window.plot_control
        for combo in (control.comboBoxSelX, control.comboBoxSelY, control.comboBoxSelZ):
            combo.currentIndexChanged.connect(self._on_axis_changed)

    def action(self, pairs: bool = True):
        """The View-menu action that opens the panel for *pairs*."""
        return getattr(self.window, self.ACTIONS[pairs], None)

    # ---- panels ----------------------------------------------------------------

    def model(self, pairs: bool = True) -> Optional[ProjectionRankModel]:
        """The ranking model for *pairs*, rebuilt if the table it ranked has changed."""
        context = collect_context(self.window)
        if context is None:
            self.shutdown()
            return None
        window = self.dialogs.get(pairs)
        model = window.model if window is not None else None
        if model is not None and model._run is not None and model._run.settings[3] != context.key:
            # New data, new panel (Orange does the same): the old rows name a
            # table that no longer exists.
            self._discard(pairs)
            model = None
        if model is None:
            model = ProjectionRankModel(lambda: collect_context(self.window), pairs,
                                        on_apply=self.apply)
            self.dialogs[pairs] = VizRankWindow(model, self.window)
        else:
            model.refresh_context()
        return model

    def open(self, pairs: bool = True) -> Optional[ProjectionRankModel]:
        """Show the panel and start (or resume) its ranking, as Orange's VizRank button does."""
        model = self.model(pairs)
        if model is None:
            return None
        window = self.dialogs[pairs]
        window.show()
        window.raise_()
        window.activateWindow()
        model.dialog_reopened()
        self._on_axis_changed()
        return model

    def _discard(self, pairs: bool) -> None:
        window = self.dialogs.pop(pairs, None)
        if window is not None:
            window.model.shutdown()
            window.close()
            window.deleteLater()

    def shutdown(self) -> None:
        """Close both panels (the table went away)."""
        for pairs in list(self.dialogs):
            self._discard(pairs)

    # ---- apply and follow ------------------------------------------------------

    def apply(self, payload) -> None:
        """Set the view a row describes."""
        control = self.window.plot_control
        self._applying = True
        try:
            if "z" in payload:
                self._set_axis(control, "z", payload["z"], payload.get("scale_z", "lin"))
                checkbox = getattr(self.window, "checkBoxEnableZ", None)
                if checkbox is not None and not checkbox.isChecked():
                    checkbox.setChecked(True)
            else:
                self._set_axis(control, "x", payload["x"], payload.get("scale_x", "lin"))
                self._set_axis(control, "y", payload["y"], payload.get("scale_y", "lin"))
        finally:
            self._applying = False

    @staticmethod
    def _set_axis(control, axis: str, name: str, scale: str) -> None:
        """Choose *name* on *axis*, drawn in the *scale* it was scored in.

        Choosing the parameter applies its saved axis settings (or auto-ranges);
        only when that leaves a different scale is the scale set and the axis
        auto-ranged again, so a saved range is not thrown away needlessly.
        """
        control.set_axis_by_name(axis, name, match_contains=False)
        current = getattr(control, f"scale_{axis}")
        if current != scale:
            setattr(control, f"scale_{axis}", scale)
            auto = getattr(control, f"on_auto_range_{axis}", None)
            if callable(auto):
                auto()
            request = getattr(control.parent, "request_plot_update", None)
            if callable(request):
                request()

    def _on_axis_changed(self, *_args) -> None:
        """Follow a hand-picked view in the open panel (Orange's auto-select)."""
        if self._applying:
            return
        control = self.window.plot_control
        pair_window = self.dialogs.get(True)
        if pair_window is not None and pair_window.isVisible():
            pair_window.model.auto_select({"x": control.p1[1], "y": control.p2[1]})
        z_window = self.dialogs.get(False)
        if z_window is not None and z_window.isVisible():
            z_window.model.auto_select({"z": control.p3[1]})


def install_projection_ranking(window) -> ProjectionRankController:
    """Connect *window*'s View-menu ranking entries; returns the controller (``window.projection_rank``)."""
    controller = ProjectionRankController(window)
    controller.install()
    window.projection_rank = controller
    return controller
