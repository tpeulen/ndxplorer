"""Find structure, UMAP and the Gaussian Fit panel: a feature of the emtk app.

**Find structure** (the Selection panel's *Cluster* button) -- one non-modal
dialog for PCA, UMAP, HDBSCAN and K-means (``analysis/structure.view.json``):
pick a method and columns (``analysis/columns.view.json``), run. The work is
:mod:`ndxplorer.analysis.structure`, run through :mod:`emtk.tasks` -- a thread
on a desktop, steps between frames in a browser -- so the window stays live.
PCA reports its loadings in the dialog and adds ``PC_n`` columns; UMAP adds
``UMAP_n`` columns (with a progress window that shows UMAP's own log) and
*Plot* shows the embedding in a window of its own; HDBSCAN and K-means add
``Cluster Label``, which the Selection panel's spin box isolates and its
*colour* check paints on the map (:meth:`AnalysisFeature.map_image`).
View > UMAP opens the dialog on UMAP.

A method whose backend is missing says so: on a desktop an installable one
(UMAP, HDBSCAN) is offered to conda, run as a task too; in a browser UMAP
cannot run at all (numba), and the dialog says that in words.

**Gaussian Fit** (View > Fit Gaussians) -- a tab of the left dock
(``analysis/gaussian_fit.view.json``): clicks on the map seed Gaussians, *Fit*
runs the held-parameter EM of :mod:`ndxplorer.analysis.gaussian_mixture` on
the gated points, the Gaussians are drawn as 1/2/3σ ellipses on the map and as
curves on the marginals, *Select* turns one into an elliptical gate in the
gate list (``model.gates.add_gaussian``), and the parameter table
(Name/Value/Fixed/Lo/Hi/Bounds/Link) edits the chisurf parameter group of
:mod:`ndxplorer.core.gaussian_parameters`. *Settings* opens the GMM settings
(``analysis/gmm_settings.view.json``).

Nothing here imports Qt.
"""

from __future__ import annotations

import ast
import json
import logging
import pathlib
import re
import time
from typing import Any, Callable, Dict, List, Optional, Sequence

import numpy as np

from . import Feature
from ...analysis import gaussian_mixture as gm
from ...analysis import structure

__all__ = ["AnalysisFeature", "create", "load_spec"]

logger = logging.getLogger(__name__)

SPECS = pathlib.Path(__file__).with_name("analysis")

#: The left dock's tab.
GAUSSIAN_TAB = "Gaussian Fit"
#: Registry owner id of the Gaussians (the Qt panel's), so another table can link to them.
GAUSSIAN_OWNER_ID = "ndxplorer.gaussians"
#: Line widths of the 1σ/2σ/3σ ellipses, and of the selected Gaussian's.
ELLIPSE_WIDTHS = (2.5, 1.8, 1.2)
SELECTED_WIDTH = 4.0
#: Most points the UMAP projection window draws (a random subset beyond).
PROJECTION_POINTS = 20000


def load_spec(name: str) -> dict:
    """One of this feature's view specs, parsed."""
    with open(SPECS / f"{name}.view.json", encoding="utf-8") as handle:
        return json.load(handle)


# --------------------------------------------------------------------------- #
# Windows
# --------------------------------------------------------------------------- #
class SpecWindow:
    """A dialog: a spec drawn in an :class:`emtk.dialog_window.DialogWindow`.

    Subclasses are the spec's model. The window grows to what its form needs
    (the height of the last frame's content), as a Qt dialog's ``adjustSize``.
    """

    spec_name = ""
    title = ""
    size = (420.0, 300.0)
    modal = False
    fit_height = True

    def __init__(self, feature: "AnalysisFeature", pos=None) -> None:
        from emtk.dialog_window import DialogWindow
        from emtk.view_form import FormState

        self.feature = feature
        self.spec = load_spec(self.spec_name)
        self.form = FormState()
        feature.app.forms[f"analysis.{self.spec_name}.{id(self)}"] = self.form
        self.window = DialogWindow(self.title, size=self.size, pos=pos,
                                   key=f"analysis-{self.spec_name}")

    @property
    def open(self) -> bool:
        return self.window.open

    def show(self) -> None:
        self.window.show()

    def close(self) -> None:
        self.window.hide()

    def enabled(self, _name: str) -> bool:
        return True

    def draw(self, frame) -> None:
        import emtk
        from emtk.view_form import draw_form

        pressed = self.window.begin(frame)
        top = emtk.get_cursor_screen_pos()[1]
        draw_form(self.spec, self, self.form, titles=False)
        used = emtk.get_cursor_screen_pos()[1] - top
        self.window.end()
        if self.fit_height and used > 0:
            want = used + self.window.HEADER_H + 2.0 * self.window.PADDING + 4.0
            self.window.size = (self.window.size[0], max(want, 80.0))
        if pressed == "close":
            self.on_close()

    def on_close(self) -> None:
        self.close()


class Question(SpecWindow):
    """A question with two answers (Yes/No, Install/Cancel)."""

    spec_name = "question"
    size = (460.0, 150.0)
    modal = True

    def __init__(self, feature, title: str, text: str, on_yes: Callable[[], None],
                 on_no: Optional[Callable[[], None]] = None, yes: str = "Yes",
                 no: str = "No") -> None:
        self.title = title
        super().__init__(feature)
        self.text = text
        self.on_yes, self.on_no = on_yes, on_no
        self._labels = (yes, no)

    def body(self) -> str:
        return self.text

    def yes_label(self) -> str:
        return self._labels[0]

    def no_label(self) -> str:
        return self._labels[1]

    def yes(self) -> None:
        self.close()
        self.on_yes()

    def no(self) -> None:
        self.close()
        if self.on_no is not None:
            self.on_no()

    def on_close(self) -> None:
        self.no()


class ColumnChooser(SpecWindow):
    """*Select Columns for Clustering*: a filter, a check per column, all/none."""

    spec_name = "columns"
    title = "Select Columns for Clustering"
    size = (460.0, 470.0)
    modal = True

    def __init__(self, feature, names: Sequence[str], chosen, on_ok) -> None:
        super().__init__(feature)
        self.names = list(names)
        self.chosen = {n for n in chosen if n in self.names}
        self.filter = ""
        self.on_ok = on_ok
        self._rows: list = []
        self._token = None

    def column_rows(self) -> list:
        text = self.filter.strip().lower()
        token = (text, tuple(sorted(self.chosen)))
        if token != self._token:
            self._token = token
            self._rows = [{"name": n, "use": n in self.chosen} for n in self.names
                          if not text or text in n.lower()]
        return self._rows

    def toggle_column(self, record, key, value) -> None:
        if key != "use" or not isinstance(record, dict):
            return
        if value:
            self.chosen.add(record["name"])
        else:
            self.chosen.discard(record["name"])

    def select_all(self) -> None:
        self.chosen = set(self.names)

    def deselect_all(self) -> None:
        self.chosen = set()

    def ok(self) -> None:
        self.close()
        self.on_ok(set(self.chosen))

    def cancel(self) -> None:
        self.close()


class ProgressWindow(SpecWindow):
    """*UMAP Computation Progress* (and an install's): the task's log and status.

    Closes itself three seconds after the work succeeded; stays with *Close*
    when it failed.
    """

    spec_name = "umap_progress"
    size = (700.0, 500.0)
    fit_height = False
    AUTO_CLOSE = 3.0

    def __init__(self, feature, title: str, idle_status: str = "Initializing UMAP computation...") \
            -> None:
        self.title = title
        super().__init__(feature)
        self.task = None
        self.idle_status = idle_status
        self.closed_at: Optional[float] = None

    def attach(self, task) -> None:
        self.task = task
        self.show()

    @property
    def running(self) -> bool:
        return self.task is not None and self.task.running

    @property
    def progress_fraction(self):
        task = self.task
        if task is None or task.running:
            return None if task is None or task.progress is None or task.progress < 1 \
                else task.progress
        return 1.0 if task.succeeded else 0.0

    @property
    def log_text(self) -> str:
        return self.task.log_text() if self.task is not None else ""

    @log_text.setter
    def log_text(self, _value) -> None:
        pass

    def status(self) -> str:
        task = self.task
        if task is None:
            return self.idle_status
        if task.running:
            return task.message or self.idle_status
        if task.succeeded:
            return "Finished."
        if task.state == "cancelled":
            return "Cancelled."
        return f"Error: {task.error}"

    def cancel(self) -> None:
        if self.task is not None:
            self.task.cancel()

    def draw(self, frame) -> None:
        super().draw(frame)
        task = self.task
        if task is not None and task.succeeded and task.finished_at is not None:
            if time.monotonic() - task.finished_at > self.AUTO_CLOSE:
                self.close()


class GmmSettingsDialog(SpecWindow):
    """*GMM Settings*: the EM's settings and the seeding window, saved per user."""

    spec_name = "gmm_settings"
    title = "GMM Settings"
    size = (430.0, 330.0)
    modal = True

    def __init__(self, feature) -> None:
        super().__init__(feature)
        self.values = gm.load_gmm_settings()

    def __getattr__(self, name: str):
        values = self.__dict__.get("values")
        if values is not None and name in gm.GMM_DEFAULTS:
            return values[name]
        raise AttributeError(name)

    def __setattr__(self, name: str, value) -> None:
        if name in gm.GMM_DEFAULTS and "values" in self.__dict__:
            self.values[name] = value
            return
        object.__setattr__(self, name, value)

    def save(self) -> None:
        path = gm.save_gmm_settings(self.values)
        self.feature.settings_changed(self.values)
        if path:
            self.feature.app.show_status("GMM settings saved to your ndX user folder.")
        else:
            self.feature.message("GMM Settings", "The settings could not be saved.")

    def ok(self) -> None:
        self.save()
        self.close()

    def cancel(self) -> None:
        self.close()


class ProjectionWindow:
    """*UMAP Projection*: the embedding as a scatter, a colour per cluster."""

    def __init__(self, feature) -> None:
        from emtk.dialog_window import DialogWindow

        self.feature = feature
        self.window = DialogWindow("UMAP Projection", size=(620.0, 540.0), key="umap-projection")
        self.embedding: Optional[np.ndarray] = None
        self.labels: Optional[np.ndarray] = None

    @property
    def open(self) -> bool:
        return self.window.open

    def show(self, embedding: np.ndarray, labels: Optional[np.ndarray]) -> None:
        keep = np.all(np.isfinite(embedding), axis=1)
        embedding, labels = embedding[keep], (None if labels is None else
                                              np.asarray(labels)[keep])
        if len(embedding) > PROJECTION_POINTS:
            pick = np.random.default_rng(0).choice(len(embedding), PROJECTION_POINTS,
                                                   replace=False)
            embedding = embedding[pick]
            labels = None if labels is None else labels[pick]
        self.embedding, self.labels = embedding, labels
        self.window.title = "UMAP Projection (3D)" if embedding.shape[1] >= 3 else "UMAP Projection"
        self.window.show()

    def draw(self, frame) -> None:
        pressed = self.window.begin(frame)
        box = self.window.content_box
        if self.embedding is not None and self.embedding.shape[1] >= 3:
            self._draw_3d(box)
        elif self.embedding is not None:
            self._draw_2d(box)
        self.window.end()
        if pressed == "close":
            self.window.hide()

    def _groups(self):
        from ...plotting.cluster_overlay import cluster_color

        if self.labels is None:
            yield "Points", np.ones(len(self.embedding), dtype=bool), (90, 150, 220, 255)
            return
        for label in np.unique(self.labels):
            rgb = cluster_color(int(label))
            name = "Noise" if label < 0 else f"Cluster {int(label)}"
            yield name, self.labels == label, (int(rgb[0]), int(rgb[1]), int(rgb[2]), 255)

    def _draw_2d(self, box) -> None:
        from emtk import implot

        implot.begin_plot("##umap-projection", (box[2], box[3]))
        implot.setup_axes("UMAP 1", "UMAP 2")
        for name, rows, colour in self._groups():
            pts = self.embedding[rows]
            implot.plot_scatter(name, pts[:, 0], pts[:, 1],
                                spec={"marker_size": 2.0, "marker_fill_color": colour,
                                      "marker_line_color": colour})
        implot.end_plot()

    def _draw_3d(self, box) -> None:
        from emtk import implot3d

        if implot3d.begin_plot("##umap-projection-3d", (box[2], box[3])):
            implot3d.setup_axes("UMAP 1", "UMAP 2", "UMAP 3")
            for name, rows, colour in self._groups():
                pts = self.embedding[rows]
                rgba = tuple(c / 255.0 for c in colour)
                implot3d.plot_scatter(name, pts[:, 0], pts[:, 1], pts[:, 2],
                                      spec=implot3d.Spec(marker_size=2.0, marker_fill_color=rgba,
                                                         marker_line_color=rgba))
            implot3d.end_plot()


# --------------------------------------------------------------------------- #
# Find structure
# --------------------------------------------------------------------------- #
class StructureDialog(SpecWindow):
    """*Find structure*: method, columns, the method's parameters, run."""

    spec_name = "structure"
    title = "Find structure"
    size = (430.0, 300.0)

    def __init__(self, feature) -> None:
        super().__init__(feature)
        self.method = "kmeans"
        self.columns: set = set()
        # PCA
        self.pca_n_components = 2
        self.pca_standardize = True
        # UMAP
        self.umap_n_neighbors = 15
        self.umap_min_dist = 0.1
        self.umap_n_components = 2
        self.umap_metric = "euclidean"
        self.umap_advanced = False
        self.umap_n_jobs = -1
        self.umap_learning_rate = 1.0
        self.umap_init = "spectral"
        self.umap_spread = 1.0
        self.umap_n_epochs = 0          # 0 = Auto
        # HDBSCAN
        self.min_samples = 5
        self.min_cluster_size = 50
        # K-means
        self.n_clusters = 3
        #: ``[(head, text)], footer`` or a plain line, shown under the buttons.
        self.result: Optional[tuple] = None

    def place_beside(self, frame) -> None:
        """Open over the right edge of the plots, where it hides the least."""
        if self.window.pos is None:
            x, y, w, h = frame
            self.window.pos = (x + w - self.window.size[0] - 30.0, y + 250.0)

    # ------------------------------------------------------------- spec model
    @property
    def descriptor(self) -> structure.Method:
        return structure.METHODS_BY_KEY[self.method]

    def method_options(self) -> list:
        return [(m.key, m.title) for m in structure.METHODS]

    def metric_options(self) -> list:
        return list(structure.UMAP_METRICS)

    def init_options(self) -> list:
        return list(structure.UMAP_INITS)

    def blurb(self) -> str:
        return self.descriptor.blurb

    def columns_label(self) -> str:
        count = len(self.columns)
        return f"▦ Columns ({count})" if count else "▦ Columns"

    @property
    def umap_advanced_shown(self) -> bool:
        return self.method == "umap" and bool(self.umap_advanced)

    @property
    def running(self) -> bool:
        return self.feature.structure_task_running()

    @property
    def is_labelling(self) -> bool:
        return self.descriptor.family == structure.LABELS

    @property
    def has_result(self) -> bool:
        return self.result is not None

    def result_text(self) -> str:
        if self.result is None:
            return ""
        if isinstance(self.result, str):
            return self.result
        lines, footer = self.result
        return "\n".join(f"{head} — {text}" for head, text in lines) + f"\n{footer}"

    @property
    def show_progress(self) -> bool:
        return self.feature.label_task is not None

    @property
    def progress_fraction(self):
        task = self.feature.label_task
        if task is None:
            return 0.0
        if task.running:
            return None                  # the Qt pane's indeterminate bar
        return 1.0 if task.succeeded else 0.0

    def progress_text(self) -> str:
        task = self.feature.label_task
        if task is None:
            return ""
        if task.running:
            return "Cancelling…" if task.cancelled else f"Running {self.descriptor.title}…"
        return "Finished." if task.succeeded else "Cancelled or failed."

    def cancel_label(self) -> str:
        task = self.feature.label_task
        return "Cancelling…" if task is not None and task.cancelled else "■ Cancel"

    def enabled(self, name: str) -> bool:
        running = self.running
        if name in ("method", "choose_columns"):
            return not running
        if name == "cancel":
            task = self.feature.label_task
            return task is not None and task.running and not task.cancelled
        if name == "save":
            return self.feature.labels is not None and not running
        if name in ("run", "plot_umap"):
            return not running and self.feature.app.model.has_data
        return True

    def umap_params(self) -> dict:
        params = {
            "n_neighbors": int(self.umap_n_neighbors), "min_dist": float(self.umap_min_dist),
            "n_components": int(self.umap_n_components), "n_jobs": int(self.umap_n_jobs),
            "metric": self.umap_metric, "learning_rate": float(self.umap_learning_rate),
            "init": self.umap_init, "spread": float(self.umap_spread),
        }
        if int(self.umap_n_epochs) > 0:
            params["n_epochs"] = int(self.umap_n_epochs)
        return params

    def label_params(self) -> dict:
        if self.method == "hdbscan":
            return {"min_samples": int(self.min_samples),
                    "min_cluster_size": int(self.min_cluster_size)}
        return {"n_clusters": int(self.n_clusters)}

    # ---------------------------------------------------------------- actions
    def choose_columns(self, then: Optional[Callable[[], None]] = None) -> None:
        def chosen(columns) -> None:
            self.columns = columns
            if then is not None and columns:
                then()

        self.feature.open_modal(ColumnChooser(self.feature,
                                              self.feature.app.model.parameter_names,
                                              self.columns, chosen))

    def run(self) -> None:
        self.feature.run_structure(plot=False)

    def plot_umap(self) -> None:
        self.feature.run_structure(plot=True)

    def cancel(self) -> None:
        task = self.feature.label_task
        if task is not None:
            task.cancel()

    def save(self) -> None:
        self.feature.save_clustering()

    def on_close(self) -> None:
        self.close()


# --------------------------------------------------------------------------- #
# The Gaussian Fit panel
# --------------------------------------------------------------------------- #
_SUBSCRIPT = str.maketrans("0123456789,", "₀₁₂₃₄₅₆₇₈₉,")


def _plain_label(label_html: str) -> str:
    """``&sigma;<sub>x,1</sub>`` as ``σx,1`` -- the table cell has no rich text."""
    text = str(label_html).replace("&sigma;", "σ").replace("&rho;", "ρ")
    return re.sub(r"<sub>(.*?)</sub>", lambda m: m.group(1), text)


class GaussianPanel:
    """The *Gaussian Fit* tab's model: the Gaussians and what the panel does.

    Parameters
    ----------
    feature : AnalysisFeature
    """

    def __init__(self, feature: "AnalysisFeature") -> None:
        from emtk.view_form import FormState

        self.feature = feature
        self.spec = load_spec("gaussian_fit")
        self.form = FormState()
        feature.app.forms["analysis.gaussian_fit"] = self.form
        self.sigma = 1.0
        self.select_point = True
        self.show_marginals = True
        self.log_gauss = False
        self.selected: Optional[int] = None
        self.error = ""
        self.group = None
        self._rows: list = []
        self._token = None
        self._settings: Optional[dict] = None
        #: Components turned into gates: index -> (gate row, mu, cov). The gate
        #: list outlines an enabled Gaussian gate itself, so the component is
        #: not drawn again while it still is that gate.
        self.gated: Dict[int, tuple] = {}
        #: Components the table's Delete asked to remove (applied next frame,
        #: once, however many of their rows were selected).
        self._pending_delete: set = set()
        try:
            from ...core import gaussian_parameters as gp

            self.group = gp.build_gaussian_group()
            self.group.default_component = self._default_component
            self._register()
        except Exception as exc:  # noqa: BLE001 - said on the panel instead
            self.error = ("Gaussian fitting needs ChiSurf's fitting parameters and mixture "
                          f"model, which could not be loaded here: {exc}")
            logger.warning("Gaussian Fit unavailable: %s", exc)

    # ------------------------------------------------------------ settings
    def gmm_settings(self) -> dict:
        if self._settings is None:
            self._settings = gm.load_gmm_settings()
        return dict(self._settings)

    def set_settings(self, values: dict) -> None:
        self._settings = dict(values)

    # ---------------------------------------------------------------- axes
    @property
    def model(self):
        return self.feature.app.model

    def log_axes(self) -> tuple:
        model = self.model
        return (bool(model.x.log or self.log_gauss), bool(model.y.log or self.log_gauss))

    def axes_info(self) -> dict:
        model = self.model
        log_x, log_y = self.log_axes()
        return {"x": {"index": model.index_of(model.x.name), "name": model.x.name,
                      "scale": "log" if log_x else "linear"},
                "y": {"index": model.index_of(model.y.name), "name": model.y.name,
                      "scale": "log" if log_y else "linear"},
                "fit_in_log": bool(self.log_gauss)}

    def _default_component(self):
        hist = self.model.histograms
        if hist is None:
            return np.zeros(2), np.eye(2)
        x0, x1 = float(hist.x_edges[0]), float(hist.x_edges[-1])
        y0, y1 = float(hist.y_edges[0]), float(hist.y_edges[-1])
        return ((x0 + x1) / 2.0, (y0 + y1) / 2.0), \
            np.diag([((x1 - x0) / 10.0) ** 2, ((y1 - y0) / 10.0) ** 2])

    def _register(self) -> None:
        try:
            from chisurf.core.parameter_group_registry import register_parameter_group

            register_parameter_group(self.group, owner_id=GAUSSIAN_OWNER_ID, label="ndX Gaussians")
        except Exception as exc:  # noqa: BLE001 - linking into it is optional
            logger.debug("could not register the Gaussians: %s", exc)

    # --------------------------------------------------------- the Gaussians
    def components(self) -> list:
        return self.group.components() if self.group is not None else []

    def rows(self) -> List[tuple]:
        return [(c.mu, c.cov, c.w) for c in self.components()]

    def add(self, mu, cov, w: float = 1.0, fixed: Optional[dict] = None) -> int:
        index = self.group.append(mu, cov, w, fixed=fixed or {})
        self._register()
        return index

    def parameter_rows(self) -> list:
        """The table's rows: one per parameter, six per Gaussian."""
        if self.group is None:
            return []
        from ...core import gaussian_parameters as gp

        rows = []
        for index, param in enumerate(self.group.rows()):
            link = getattr(param, "link", None)
            rows.append({
                "key": f"{index // gp.WIDTH}.{gp.SLOTS[index % gp.WIDTH]}",
                "component": index // gp.WIDTH, "slot": gp.SLOTS[index % gp.WIDTH],
                "name": _plain_label(getattr(param, "label_text", "") or param.name),
                "value": float(param.value), "fixed": bool(param.fixed),
                "lo": float(param.lb) if param.lb is not None else float("-inf"),
                "hi": float(param.ub) if param.ub is not None else float("inf"),
                "bounds": bool(param.bounds_on),
                "link": getattr(link, "name", "") if link is not None else "",
            })
        token = tuple(tuple(sorted(r.items())) for r in rows)
        if token != self._token:
            self._token = token
            self._rows = rows
        return self._rows

    def _param(self, record):
        from ...core import gaussian_parameters as gp

        return self.group.parameters_of(int(record["component"]))[record["slot"]] \
            if record["slot"] in gp.SLOTS else None

    def select_parameter(self, record) -> None:
        self.selected = None if not record else int(record["component"])

    def edit_parameter(self, record, key: str, value) -> None:
        param = self._param(record)
        if param is None:
            return
        try:
            if key == "value":
                param.value = float(value)
            elif key == "fixed":
                param.fixed = bool(value)
            elif key == "lo":
                param.lb = float(value)
            elif key == "hi":
                param.ub = float(value)
            elif key == "bounds":
                param.bounds_on = bool(value)
            elif key == "link":
                self._link(param, str(value or "").strip())
        except (TypeError, ValueError) as exc:
            self.feature.message("Gaussian parameter", str(exc))

    def _link(self, param, target: str) -> None:
        """Follow the parameter called *target*, or unlink on an empty name.

        A bare name is looked up among the Gaussians; ``"Group: name"`` in any
        other registered parameter table.
        """
        if not target:
            param.link = None
            return
        groups = [("", self.group)]
        try:
            from chisurf.core.parameter_group_registry import iter_registered_parameter_groups

            groups += [(label, group) for _owner, label, group
                       in iter_registered_parameter_groups() if group is not self.group]
        except Exception:  # noqa: BLE001
            pass
        label, _, name = target.rpartition(":")
        label, name = label.strip(), name.strip()
        for group_label, group in groups:
            if label and label != group_label:
                continue
            for other in getattr(group, "parameters_all", ()):
                if other is not param and getattr(other, "name", None) == name:
                    param.link = other
                    return
        raise ValueError(f"No parameter called {target!r} to link to.")

    def delete_parameter(self, record) -> None:
        if record:
            self._pending_delete.add(int(record["component"]))

    def remove_components(self, indices) -> None:
        for index in sorted(set(indices), reverse=True):
            if 0 <= index < len(self.group):
                self.group.pop(index)
        self.selected = None
        self.gated = {}

    # ---------------------------------------------------------------- actions
    def enabled(self, name: str) -> bool:
        if self.group is None:
            return False
        if name in ("fit", "select", "add_component"):
            return self.model.histograms is not None
        return True

    def add_component(self) -> None:
        self.add(*self._default_component())

    def remove_component(self) -> None:
        count = len(self.group)
        if not count:
            return
        self.remove_components([self.selected if self.selected is not None
                                and self.selected < count else count - 1])

    def clear(self) -> None:
        self.group.clear()
        self.selected = None
        self.gated = {}

    def seed_at(self, x: float, y: float) -> Optional[int]:
        """A click on the map at value ``(x, y)``: a Gaussian there."""
        hist = self.model.histograms
        if hist is None:
            return None
        cfg = self.gmm_settings()
        seeded = gm.seed_component(hist.H, hist.x_edges, hist.y_edges, x, y,
                                   int(cfg.get("local_window_bins", 10)))
        if seeded is None:
            return None
        mu, cov = seeded
        hold = bool(cfg.get("fix_new_means", True))
        return self.add(mu, cov, fixed={"x": hold, "y": hold})

    def fit(self) -> None:
        model = self.model
        hist = model.histograms
        if hist is None:
            self.feature.message("No histogram", "No 2D histogram available. Fit is restricted "
                                 "to visible data; please update histogram first.")
            return
        x = model._visible_values(model.index_of(model.x.name))
        y = model._visible_values(model.index_of(model.y.name))
        log_x, log_y = self.log_axes()
        try:
            fitted = gm.fit_mixture(self.components(), x, y,
                                    (hist.x_edges[0], hist.x_edges[-1]),
                                    (hist.y_edges[0], hist.y_edges[-1]),
                                    log_x, log_y, self.gmm_settings())
        except gm.GaussianFitError as exc:
            self.feature.message(exc.title, exc.text)
            return
        except Exception as exc:  # noqa: BLE001 - the EM failed; say so
            self.feature.message("Fit failed", str(exc))
            return
        for index, (mu, cov, w) in enumerate(fitted):
            self.group.write(index, mu, cov, w)
        self.feature.app.show_status(f"Fitted {len(fitted)} Gaussian"
                                     + ("s" if len(fitted) != 1 else ""))

    def select(self) -> None:
        """The chosen Gaussian (or the only one) as an elliptical gate."""
        components = self.components()
        if not components:
            return
        chosen = self.selected
        if chosen is None or chosen >= len(components):
            if len(components) != 1:
                self.feature.message("Select Gaussian",
                                     "Please select one or more Gaussian rows in the table.")
                return
            chosen = 0
        model = self.model
        log_x, log_y = self.log_axes()
        sigma = float(self.sigma) if np.isfinite(self.sigma) and self.sigma > 0 else 1.0
        component = components[chosen]
        mu, cov = component.mu, component.cov
        if log_x or log_y:
            mu, cov = gm.to_fit_space(mu, cov, log_x, log_y)
        row = model.gates.add_gaussian(model.index_of(model.x.name),
                                       model.index_of(model.y.name), mu, cov, sigma=sigma,
                                       invert=False, enabled=True,
                                       name=f"G2D({model.x.name}, {model.y.name})",
                                       log_x=log_x, log_y=log_y)
        self.gated[chosen] = (row, component.mu.copy(), component.cov.copy())
        model.invalidate()

    def is_gate(self, index: int, component) -> bool:
        """Whether component *index* is drawn by the gate list (an enabled gate
        made from it, and it has not moved since)."""
        entry = self.gated.get(index)
        if entry is None:
            return False
        row, mu, cov = entry
        gates = self.model.gates
        if not any(g is row for g in gates) or not row.enabled:
            return False
        return bool(np.allclose(component.mu, mu) and np.allclose(component.cov, cov))

    def settings(self) -> None:
        """*Settings*: the GMM settings dialog."""
        self.feature.open_modal(GmmSettingsDialog(self.feature))

    def save(self) -> None:
        if not len(self.group):
            self.feature.message("Save Gaussians", "There are no Gaussian rows to save.")
            return
        service = self.feature.file_service()
        if service is None:
            return
        service.ask_save("Save Gaussian Fits", "Gaussian Files (*.json *.csv);;All Files (*)",
                         "gaussians.json", self._save_to)

    def _save_to(self, path: str) -> None:
        hist = self.model.histograms
        log_x, log_y = self.log_axes()
        try:
            written = gm.save_gaussians(path, self.group.records(), self.rows(), self.axes_info(),
                                        None if hist is None else hist.H,
                                        None if hist is None else hist.x_edges,
                                        None if hist is None else hist.y_edges, log_x, log_y)
        except OSError as exc:
            self.feature.message("Save Error", f"Failed to save:\n{exc}")
            return
        self.feature.message("Saved", "Saved files:\n" + "\n".join(
            pathlib.Path(p).name for p in written))

    def load(self) -> None:
        service = self.feature.file_service()
        if service is None:
            return
        service.ask_open("Load Gaussian Fits", "Gaussian Files (*.json *.csv);;All Files (*)",
                         lambda paths: self.load_from(paths[0]) if paths else None)

    def load_from(self, path: str) -> None:
        try:
            rows, axes = gm.load_gaussians(path)
        except Exception as exc:  # noqa: BLE001
            self.feature.message("Load Error", f"Failed to load file:\n{exc}")
            return
        if not rows:
            self.feature.message("Load Gaussians",
                                 "No valid Gaussian rows found in the selected file.")
            return
        self.group.clear()
        for mu, cov, w, fx, fy, fsx, frho, fsy in rows:
            self.add(mu, cov, w, fixed={"x": fx, "y": fy, "sd_x": fsx, "rho": frho, "sd_y": fsy})
        mismatch = gm.axis_mismatch(axes, self.axes_info())
        if mismatch:
            self.feature.message("Axis Mismatch", mismatch)

    # ------------------------------------------------------------- drawing
    def draw_tab(self, box) -> None:
        import emtk
        from emtk.view_form import draw_form

        if self.group is None:
            emtk.text_wrapped(self.error)
            return
        if self._pending_delete:
            pending, self._pending_delete = self._pending_delete, set()
            self.remove_components(pending)
        draw_form(self.spec, self, self.form, titles=False)

    def draw_plot(self, plot: str) -> None:
        from emtk import implot

        components = self.components()
        if not components or self.model.histograms is None:
            return
        log_x, log_y = self.log_axes()
        if plot == "map":
            for i, c in enumerate(components):
                if self.is_gate(i, c):
                    continue
                colour = gm.colour_of(i)
                for level, width in zip(gm.SIGMA_LEVELS, ELLIPSE_WIDTHS):
                    xs, ys = gm.ellipse(c.mu, c.cov, level, log_x, log_y, n=160)
                    if i == self.selected and level == 1.0:
                        width = SELECTED_WIDTH
                    implot.plot_line(f"##gauss{i}.{level}", xs, ys,
                                     spec={"line_color": colour, "line_weight": width})
            return
        if not self.show_marginals or plot not in ("xmarginal", "ymarginal"):
            return
        hist = self.model.histograms
        curves = gm.component_marginals(self.rows(), hist.x[0], hist.x[1], hist.y[0], hist.y[1],
                                        self.model.x.norm, self.model.y.norm, log_x, log_y)
        for i, curve in enumerate(curves):
            if curve is None:
                continue
            xc, gx, yc, gy = curve
            spec = {"line_color": gm.colour_of(i), "line_weight": 1.5}
            if plot == "xmarginal":
                implot.plot_line(f"##gauss-x{i}", xc, gx, spec=spec)
            else:
                implot.plot_line(f"##gauss-y{i}", gy, yc, spec=spec)


# --------------------------------------------------------------------------- #
# The feature
# --------------------------------------------------------------------------- #
class AnalysisFeature(Feature):
    """Find structure, UMAP and Gaussian Fit, on the emtk window."""

    name = "analysis"

    def __init__(self, app) -> None:
        super().__init__(app)
        self.structure = StructureDialog(self)
        self.progress = ProgressWindow(self, "UMAP Computation Progress")
        self.projection = ProjectionWindow(self)
        self.gaussians = GaussianPanel(self)
        self.modal: List[SpecWindow] = []
        #: The last labelling: labels/probabilities (table length) and how.
        self.labels: Optional[np.ndarray] = None
        self.probabilities: Optional[np.ndarray] = None
        self.label_run: Optional[dict] = None
        self.selected_cluster = -1
        self.cluster_colours = False
        #: The running labelling (its progress is shown in the dialog).
        self.label_task = None
        #: The running projection or install (shown in :attr:`progress`).
        self.work_task = None
        self._colour_key = None

    # ------------------------------------------------------------- the seam
    def actions(self) -> Dict[str, Callable[[], Any]]:
        return {"cluster": self.toggle_structure, "umap": self.open_umap,
                "toggle_fit_gaussians": self.toggle_fit_gaussians}

    def available(self, action: str) -> Optional[bool]:
        if action in ("cluster", "umap"):
            return self.app.model.has_data
        if action == "toggle_fit_gaussians":
            return self.app.model.has_data or self.show_fit_gaussians
        return None

    def fields(self) -> Dict[str, tuple]:
        return {
            "selected_cluster": (lambda: self.selected_cluster, self._set_selected_cluster),
            "cluster_colours": (lambda: self.cluster_colours, self._set_cluster_colours),
            "show_fit_gaussians": (lambda: self.show_fit_gaussians, self._set_show_gaussians),
        }

    def windows(self) -> list:
        return [("left", GAUSSIAN_TAB, self.gaussians.draw_tab, {"visible": False})]

    @property
    def show_fit_gaussians(self) -> bool:
        """Whether the Gaussian Fit window is open (View > Fit Gaussians)."""
        return self.app.docks.is_visible(GAUSSIAN_TAB)

    def capture_actions(self) -> Dict[str, str]:
        return {"actionFit_Gaussians": "toggle_fit_gaussians", "actionUMAP": "umap"}

    def mask_terms(self) -> Dict[str, Any]:
        if self.selected_cluster >= 0 and self.labels is not None:
            return {"cluster_label": int(self.selected_cluster)}
        return {}

    def map_image(self, values):
        """The map coloured by each bin's dominant cluster, when *colour* is on."""
        if not self.cluster_colours or self.labels is None:
            return None
        model = self.app.model
        hist = model.histograms
        index = model.index_of("Cluster Label")
        if hist is None or index < 0:
            return None
        from ...plotting.cluster_overlay import cluster_rgb_image

        try:
            rgb = cluster_rgb_image(model._visible_values(model.index_of(model.x.name)),
                                    model._visible_values(model.index_of(model.y.name)),
                                    model._visible_values(index).astype(np.int64),
                                    hist.x_edges, hist.y_edges, log_counts=model.log_counts)
        except Exception:  # noqa: BLE001 - the density map stands in
            logger.debug("cluster colouring failed", exc_info=True)
            return None
        if rgb is None or rgb.shape[:2] != np.shape(values):
            return None
        alpha = np.full(rgb.shape[:2] + (1,), 255, dtype=np.uint8)
        return np.concatenate([rgb, alpha], axis=2)

    def on_data_changed(self) -> None:
        """A new table: its rows are not the ones that were clustered."""
        self.labels = self.probabilities = self.label_run = None
        self.selected_cluster = -1
        self.structure.result = None
        self.label_task = None

    def animating(self) -> bool:
        tasks = (self.label_task, self.work_task)
        return any(t is not None and t.running for t in tasks) or self.progress.open

    @property
    def cluster_labels(self) -> Optional[np.ndarray]:
        """The last labelling, one label per table row (``-1`` noise), or ``None``.

        What *Find informative projections* offers as "Clusters" classes.
        """
        return self.labels

    # ------------------------------------------------------------- fields
    def _set_selected_cluster(self, value) -> None:
        value = int(value)
        if value != self.selected_cluster:
            self.selected_cluster = max(-1, value)
            self.app.model.invalidate()

    def _set_cluster_colours(self, value) -> None:
        if bool(value) != self.cluster_colours:
            self.cluster_colours = bool(value)
            self.app.plots.image_revision += 1

    def _set_show_gaussians(self, value) -> None:
        if value:
            self.app.docks.focus(GAUSSIAN_TAB)
            self.gaussians.select_point = True
        else:
            self.app.docks.hide(GAUSSIAN_TAB)

    # ------------------------------------------------------------ actions
    def toggle_structure(self) -> None:
        if self.structure.open:
            self.structure.close()
        else:
            self.structure.place_beside(self.app.box)
            self.structure.show()

    def open_umap(self) -> None:
        """View > UMAP: Find structure, on UMAP."""
        self.structure.method = "umap"
        self.structure.result = None
        self.structure.place_beside(self.app.box)
        self.structure.show()

    def toggle_fit_gaussians(self) -> None:
        """View > Fit Gaussians: open the window on top, or put it away."""
        if self.app.docks.toggle(GAUSSIAN_TAB):
            self.gaussians.select_point = True

    def settings_changed(self, values: dict) -> None:
        self.gaussians.set_settings(values)

    # ------------------------------------------------------------ helpers
    def message(self, title: str, text: str) -> None:
        self.app.message = (title, text)

    def open_modal(self, window: SpecWindow) -> None:
        window.show()
        self.modal.append(window)

    def ask(self, title: str, text: str, on_yes, on_no=None, yes="Yes", no="No") -> None:
        self.open_modal(Question(self, title, text, on_yes, on_no, yes, no))

    def file_service(self):
        service = getattr(self.app, "io_service", None)
        if service is None:
            self.message("Files", "No file service is available in this window.")
        return service

    def structure_task_running(self) -> bool:
        return any(t is not None and t.running for t in (self.label_task, self.work_task))

    # ------------------------------------------------------ Find structure
    def run_structure(self, plot: bool = False) -> None:
        """*Run* (or UMAP's *Plot*): backend, columns, then the work."""
        dialog = self.structure
        method = dialog.descriptor
        if not method.available():
            self._missing_backend(method)
            return
        if len(dialog.columns) < method.min_columns:
            if dialog.columns:
                self.message(f"{method.title} needs more columns",
                             f"Select at least {method.min_columns} columns.")
                return
            if method.family == structure.PROJECTION:
                self.message(f"Select columns for {method.title}",
                             f"Choose at least {method.min_columns} columns to project.")
                return
            self.ask("Select columns?",
                     "No columns are selected, so only the current X, Y and Z axes will be "
                     "used — which rarely groups the data well.\n\nChoose columns now?",
                     on_yes=lambda: dialog.choose_columns(then=lambda: self._start(plot)),
                     on_no=lambda: self._start(plot))
            return
        self._start(plot)

    def _data(self):
        """The matrix the method sees: the chosen columns, else the x/y/z axes."""
        model = self.app.model
        columns = sorted(self.structure.columns)
        if not columns:
            columns = [a.name for a in (model.x, model.y, model.z) if a.name]
        data, used = structure.column_matrix(model.source, columns)
        return data, used

    def _start(self, plot: bool) -> None:
        from emtk import tasks

        dialog = self.structure
        data, used = self._data()
        if data is None:
            self.message("No data", "None of the chosen columns is in the table.")
            return
        dialog.result = None
        method = dialog.method
        if method in ("kmeans", "hdbscan"):
            params = dialog.label_params()
            self.label_task = tasks.start(structure.label_points, data, method, params,
                                          name=f"cluster-{method}")
            run = {"method": method, "columns": set(used), "parameters": params}
            self.label_task.on_done(lambda task: self._labels_done(task, run))
        elif method == "pca":
            self.work_task = tasks.start(_pca_work, data, used, int(dialog.pca_n_components),
                                         bool(dialog.pca_standardize), name="pca")
            self.work_task.on_done(self._pca_done)
        else:
            self.work_task = tasks.start(structure.embed_umap, data, dialog.umap_params(),
                                         name="umap")
            self.progress.title = self.progress.window.title = "UMAP Computation Progress"
            self.progress.attach(self.work_task)
            self.work_task.on_done(lambda task: self._umap_done(task, plot))

    def _labels_done(self, task, run: dict) -> None:
        model = self.app.model
        if task.succeeded and task.result is not None and task.result[0] is not None \
                and model.has_data:
            labels, probabilities = task.result
            structure.store_labels(model.source, labels, probabilities)
            self.labels, self.probabilities, self.label_run = labels, probabilities, run
            model.invalidate()
            self.app.plots.image_revision += 1
            self.app.show_status(f"Clustering using {run['method'].upper()} completed "
                                 "successfully.")
        elif task.state == "failed":
            self.message(f"{structure.METHODS_BY_KEY[run['method']].title} failed", task.error)

    def _pca_done(self, task) -> None:
        model = self.app.model
        if task.state == "failed" or (task.succeeded and task.result is None):
            self.message("PCA failed", task.error or
                         "No components could be computed from the selected columns.")
            return
        if not task.succeeded or not model.has_data:
            return
        result = task.result
        structure.store_projection(model.source, "PC", result.projections)
        model.invalidate()
        self.structure.result = structure.pca_report(result)

    def _umap_done(self, task, plot: bool) -> None:
        model = self.app.model
        if not task.succeeded or task.result is None:
            if task.state == "failed":
                logger.error("UMAP failed: %s", task.error)
            return
        embedding = task.result
        if plot:
            labels = None
            if self.labels is not None and len(self.labels) == len(embedding):
                labels = self.labels
            self.projection.show(embedding, labels)
            return
        if not model.has_data:
            return
        names = structure.store_projection(model.source, "UMAP", embedding)
        model.invalidate()
        self.structure.result = (f"Added {names[0]}…{names[-1]}. "
                                 "Pick them in the axis controls to plot.")

    def _missing_backend(self, method: structure.Method) -> None:
        reason = method.unavailable()
        if structure.in_browser() or not method.installable:
            self.message(f"{method.title} unavailable", reason)
            return

        def refused() -> None:
            self.message(f"{method.title} not installed",
                         "Installation was cancelled or failed, so this method cannot run.")

        self.ask(f"{method.title} not installed",
                 f"{reason}\n\n{method.blurb}\n\nInstall {method.package} now "
                 "(conda, conda-forge)?",
                 on_yes=lambda: self._install(method, refused), on_no=refused,
                 yes="Install", no="Cancel")

    def _install(self, method: structure.Method, refused) -> None:
        from emtk import tasks

        from ...utils.package_install import install_task

        self.work_task = tasks.start(install_task, [method.package],
                                     ["conda-forge", "defaults"], method.import_name,
                                     name=f"install-{method.package}")
        self.progress.title = self.progress.window.title = f"Installing {method.package}"
        self.progress.attach(self.work_task)

        def done(task) -> None:
            if not task.succeeded or not task.result:
                refused()
            elif not method.available():
                self.message(f"{method.title} installed",
                             f"{method.package} was installed but could not be imported yet.\n"
                             "Please restart the application and try again.")

        self.work_task.on_done(done)

    def save_clustering(self) -> None:
        if self.labels is None or self.label_run is None:
            self.message("No Clustering Data",
                         "No clustering data available. Please apply clustering before saving.")
            return
        service = self.file_service()
        if service is None:
            return
        service.ask_folder("Folder for Clustering Data", self._save_clustering_to)

    def _save_clustering_to(self, folder: str) -> None:
        from ...io import writer

        run = self.label_run
        written = writer.save_clustering_data(folder, self.app.model.source, run["method"],
                                              self.labels, self.probabilities, run["columns"],
                                              run["parameters"])
        if written is None:
            self.message("Save Error", "The clustering data could not be written.")
        else:
            self.app.show_status(f"Clustering data saved to {written}")

    # --------------------------------------------------------------- frame
    def draw_windows(self) -> bool:
        box = self.app.box
        for task in (self.label_task, self.work_task):
            if task is not None:
                task.poll()
        if self.structure.open:
            self.structure.draw(box)
        if self.progress.open:
            self.progress.draw(box)
        if self.projection.open:
            self.projection.draw(box)
        self.modal = [w for w in self.modal if w.open]
        if self.modal:
            self.modal[-1].draw(box)
            self.modal = [w for w in self.modal if w.open]
        return bool(self.modal)

    def draw_plot(self, plot: str) -> None:
        if self.gaussians.group is not None:
            self.gaussians.draw_plot(plot)

    def plot_input(self, plot: str) -> bool:
        """A click on the map while the Gaussian Fit tab is up seeds a Gaussian."""
        if plot != "map" or not self._point_mode():
            return False
        import emtk
        from emtk import implot

        io = emtk.get_io()
        if not (implot.is_plot_hovered() and io.mouse_clicked[0]):
            return implot.is_plot_hovered()
        point = implot.get_plot_mouse_pos()
        self.gaussians.seed_at(point.x, point.y)
        return True

    def _point_mode(self) -> bool:
        return (self.app.docks.is_shown(GAUSSIAN_TAB)
                and self.gaussians.select_point and self.gaussians.group is not None
                and not self.modal)

    # ------------------------------------------------------------ capture
    def capture_ops(self) -> Dict[str, Callable]:
        return {"click": self._op_click, "call": self._op_call, "set": self._op_set,
                "canvas_click": self._op_canvas_click, "wait_until": self._op_wait_until,
                "tab": self._op_tab, "close_dialogs": self._op_close_dialogs}

    def capture_targets(self) -> Dict[str, Callable]:
        def box_of(window):
            return lambda _replay: window.window.box if window.open else None

        def modal_of(kind):
            def locate(_replay):
                for window in reversed(self.modal):
                    if isinstance(window, kind) and window.open:
                        return window.window.box
                return None
            return locate

        def message_box(replay):
            located = modal_of(Question)(replay)
            if located is None and self.app.message is not None:
                replay.draw()
                return getattr(self.app, "message_box", None)
            return located

        def fit_dock(_replay):
            if not self.app.docks.is_shown(GAUSSIAN_TAB):
                return None
            return self.app.docks.window(GAUSSIAN_TAB).frame

        return {
            "widget:win.clustering_dialog": box_of(self.structure),
            "dialog:ColumnSelectionDialog": modal_of(ColumnChooser),
            "dialog:QMessageBox": message_box,
            "dialog:UMAPProgressDialog": box_of(self.progress),
            "dialog:GaussianSettingsDialog": modal_of(GmmSettingsDialog),
            "widget:win.dockWidget_Fit": fit_dock,
        }

    def _press(self, replay, form, name: str) -> bool:
        replay.settle()
        rect = form.rects.get(name)
        if rect is None:
            return False
        replay.click_rect(rect)
        replay.settle()
        return True

    def _op_click(self, replay, step: dict):
        widget = step.get("widget", "")
        from ..capture import Unsupported

        if widget == "pc.pushButtonShowClusteringDialog":
            if not self._press(replay, replay.app.forms["plot_controls"], "cluster"):
                raise Unsupported("the Cluster button is not on screen")
            return None
        dialog = re.fullmatch(r"button\('([^']+)',\s*win\.clustering_dialog\)", widget)
        if dialog:
            action = {"Columns": "choose_columns", "Run": "run", "Plot": "plot_umap",
                      "Save": "save", "Cancel": "cancel"}.get(dialog.group(1))
            if action is None or not self._press(replay, self.structure.form, action):
                raise Unsupported(f"no {dialog.group(1)!r} on the Find structure dialog")
            return None
        panel = {"win.btnFit2DGauss": "fit", "win.btnSelectGaussian": "select",
                 "win.btnGMMSettings": "settings", "win.btnClearGaussians": "clear"}.get(widget)
        if panel is not None:
            if not self._press(replay, self.gaussians.form, panel):
                raise Unsupported(f"{widget} is not on screen")
            return None
        return False

    def _op_call(self, replay, step: dict):
        code = step.get("code", "")
        if "clustering_dialog" not in code and "_create_umap_progress_dialog" not in code \
                and "GaussianSettingsDialog" not in code:
            return False
        dialog = self.structure
        for line in code.splitlines():
            line = line.strip()
            method = re.search(r"findData\('(\w+)'\)", line)
            if method:
                dialog.method = method.group(1)
            elif "checkBoxUMAPAdvanced.setChecked(True)" in line:
                dialog.umap_advanced = True
            elif line.startswith("d._cluster_columns"):
                dialog.columns = set(ast.literal_eval(line.split("=", 1)[1].strip()))
            elif line.startswith("d._cluster_n_clusters"):
                dialog.n_clusters = int(line.split("=", 1)[1])
            elif "_create_umap_progress_dialog" in line:
                self.progress.task = None
                self.progress.title = self.progress.window.title = "UMAP Computation Progress"
                self.progress.show()
            elif "GaussianSettingsDialog" in line and not any(
                    isinstance(w, GmmSettingsDialog) for w in self.modal):
                self.gaussians.settings()
        replay.settle(3)
        return None

    def _op_set(self, replay, step: dict):
        attr = {"pc.checkBoxColorClusters": "cluster_colours",
                "pc.spinBoxCluster": "selected_cluster"}.get(step.get("widget", ""))
        if attr is not None:
            setattr(self.app.panel, attr, step["value"])
        elif step.get("widget") == "win.spinSelectionSigma":
            self.gaussians.sigma = float(step["value"])
        else:
            return False
        replay.settle()
        return None

    def _op_canvas_click(self, replay, step: dict):
        if step.get("button", "left") != "left" or not self._point_mode():
            return False
        replay.settle()
        rect = self.app.plots.rects.get("map")
        if rect is None:
            return False
        x, y, w, h = rect
        fx, fy = step["at"]
        replay.click_at(x + fx * w, y + fy * h)
        replay.settle()
        return None

    def _op_wait_until(self, replay, step: dict):
        expr = step.get("expr", "")
        if "_cluster_labels" not in expr and "clustering_dialog" not in expr:
            return False
        for task in (self.label_task, self.work_task):
            if task is not None:
                task.wait(timeout=float(step.get("timeout", 120000)) / 1000.0)
        replay.settle(3)
        return None

    def _op_tab(self, replay, step: dict):
        title = step.get("title")
        if self.app.docks.is_visible(title):
            self.app.docks.focus(title)
            replay.settle()
            return None
        return False

    def _op_close_dialogs(self, replay, _step: dict):
        for window in self.modal:
            window.close()
        self.modal = []
        self.app.message = None
        replay.settle()
        return None


def _pca_work(task, data, columns, n_components, standardize):
    """PCA as a task: one step (the decomposition is a single call)."""
    from ...analysis.pca_helpers import compute_pca

    yield None, "Decomposing"
    return compute_pca(data, columns, n_components=n_components, standardize=standardize)


def create(app) -> AnalysisFeature:
    return AnalysisFeature(app)
