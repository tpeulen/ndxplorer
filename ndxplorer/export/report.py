"""Batch reports over analysis folders, without a window.

File > Make Report opens the report tool: a list of analysis folders, a
``report.yaml`` that names the plots, and *Generate Reports*. For each folder
the plots are histogrammed the way the window would show them -- the same
reader, equation columns, per-parameter axis settings and binning (through
:class:`ndxplorer.app.model.ExplorerModel`, which imports no GUI) -- and
written into ``<folder>/report/``: a PNG and a CSV per plot, an
``axes_info.yaml`` describing the axes, and a DOCX when python-docx is there.

The figures are drawn by matplotlib into bytes (Agg, no pyplot), so the same
code runs in a browser: :func:`build_folder_report` returns the files as
``{name: bytes}``, and :func:`write_folder_report` is the one step that
touches the disk.

``report.yaml``::

    plots:
    - type: 2d               # or 1d
      title: Proximity ratio vs. Tg-Tr(ms)
      x: Proximity ratio     # a parameter name (exact, else a substring)
      y: Tg-Tr(ms)
      template: 2d_marginals # a file in <settings>/templates: the look only
    - type: 1d
      axis: x                # which of x / y a 1-D plot histograms
      x: Proximity ratio
      template: 1d_basic
"""

from __future__ import annotations

import io
import json
import os
import pathlib
import re
import shutil
import stat
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Union

import numpy as np

from ..logging_config import logging

__all__ = [
    "REPORT_DIR_NAMES",
    "DEFAULT_CONFIG",
    "PACKAGED_REPORT_CONFIG",
    "ConfigError",
    "FolderReport",
    "safe_token",
    "parse_config",
    "config_text",
    "default_config_text",
    "load_templates",
    "is_analysis_folder",
    "discover_analysis_folders",
    "report_dir",
    "is_folder_processed",
    "report_images",
    "clear_reports",
    "hist_1d_csv",
    "hist_2d_csv",
    "render_1d_png",
    "render_2d_png",
    "render_2d_marginals_png",
    "ReportGenerator",
    "build_folder_report",
    "write_folder_report",
    "combined_docx_bytes",
    "docx_available",
]

PathLike = Union[str, pathlib.Path]

#: Where a folder's report lives (the first that exists; ``report`` is written).
REPORT_DIR_NAMES = ("report", "Report", "REPORT")
PACKAGED_REPORT_CONFIG = pathlib.Path(__file__).resolve().parents[1] / "settings" / "report.yaml"

DEFAULT_CONFIG: Dict[str, Any] = {
    "plots": [
        {"type": "2d", "title": "2D Histogram (basic)", "template": "2d_basic"},
        {"type": "2d", "title": "2D Histogram with Marginals", "template": "2d_marginals"},
        {"type": "1d", "title": "1D Histogram", "axis": "x", "template": "1d_basic"},
    ]
}


class ConfigError(ValueError):
    """A report configuration that cannot be used, with the reason."""


def safe_token(text: Any) -> str:
    """*text* as a file-name piece: spaces to ``_``, anything odd to ``-``, 80 characters."""
    token = str(text if text is not None else "").strip()
    if not token:
        return "unknown"
    token = re.sub(r"[^A-Za-z0-9._-]+", "-", token.replace(" ", "_"))
    return token[:80]


# ------------------------------------------------------------ configuration
def parse_config(text: str, json_text: bool = False) -> Dict[str, Any]:
    """The report configuration in *text* (YAML, or JSON when *json_text*).

    Raises
    ------
    ConfigError
        When it does not parse or has no top-level ``plots`` list.
    """
    import yaml

    try:
        data = json.loads(text) if json_text else (yaml.safe_load(text) if text.strip() else {})
    except Exception as exc:  # noqa: BLE001 - both parsers, one message
        raise ConfigError(f"Could not parse the configuration: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("plots"), list):
        raise ConfigError("The configuration must define a top-level 'plots' list.")
    return data


def config_text(config: Mapping[str, Any]) -> str:
    """A configuration as YAML text."""
    import yaml

    return yaml.safe_dump(dict(config), sort_keys=False, allow_unicode=True)


def default_config_text(settings_dir: Optional[PathLike] = None) -> str:
    """The ``report.yaml`` the tool starts with.

    The user's (``<settings>/report.yaml``) when it is valid, else the
    packaged one, else :data:`DEFAULT_CONFIG`. Nothing is written.
    """
    candidates = []
    if settings_dir is not None:
        candidates.append(pathlib.Path(settings_dir) / "report.yaml")
    candidates.append(PACKAGED_REPORT_CONFIG)
    for path in candidates:
        try:
            text = path.read_text(encoding="utf-8")
            return config_text(parse_config(text))
        except (OSError, ConfigError):
            continue
    return config_text(DEFAULT_CONFIG)


def load_templates(base: Optional[PathLike] = None) -> Dict[str, Dict[str, Any]]:
    """Plot templates by name: the YAML/JSON files with a ``renderer`` in *base*.

    *base* defaults to the user's ``<settings>/templates``, falling back to the
    packaged templates when that folder does not exist.
    """
    import yaml

    if base is None:
        from ..settings import get_settings_path

        base = get_settings_path() / "templates"
        if not base.is_dir():
            base = PACKAGED_REPORT_CONFIG.parent / "templates"
    base = pathlib.Path(base)
    templates: Dict[str, Dict[str, Any]] = {}
    if not base.is_dir():
        return templates
    for path in sorted(base.iterdir()):
        suffix = path.suffix.lower()
        if not path.is_file() or suffix not in (".yaml", ".yml", ".json"):
            continue
        try:
            with open(path, "r", encoding="utf-8") as handle:
                data = json.load(handle) if suffix == ".json" else yaml.safe_load(handle)
        except Exception as exc:  # noqa: BLE001 - a broken template is skipped, said so
            logging.warning("Report template %s unreadable: %s", path, exc)
            continue
        if isinstance(data, dict) and data.get("renderer"):
            templates[path.stem.lower()] = data
    return templates


# ------------------------------------------------------------------ folders
def is_analysis_folder(path: PathLike) -> bool:
    """Whether *path* is an analysis folder: ``hdf5/*.h5`` or ``bi4_bur``/``bur`` with ``.bur`` files."""
    path = pathlib.Path(path)
    try:
        if not path.is_dir():
            return False
        hdf5 = path / "hdf5"
        if hdf5.is_dir() and any(f.is_file() and f.suffix.lower() in (".h5", ".hdf5")
                                 for f in hdf5.iterdir()):
            return True
        for sub in ("bi4_bur", "bur"):
            folder = path / sub
            if folder.is_dir() and any(f.is_file() and f.suffix.lower() == ".bur"
                                       for f in folder.iterdir()):
                return True
    except OSError:
        return False
    return False


def discover_analysis_folders(roots: Iterable[PathLike]) -> List[pathlib.Path]:
    """The analysis folders at or below *roots*, in discovery order, each once.

    A root that is an analysis folder is taken as it is; otherwise its tree is
    walked (hidden and version-control folders skipped) and the walk does not
    descend into an analysis folder it found.
    """
    found: List[pathlib.Path] = []
    seen = set()
    skip = {".git", ".hg", ".svn", "__pycache__", ".idea", ".vscode"}

    def take(path: pathlib.Path) -> None:
        key = str(path.resolve())
        if key not in seen:
            seen.add(key)
            found.append(path)

    for root in roots:
        root = pathlib.Path(root)
        if is_analysis_folder(root):
            take(root)
            continue
        for current, dirnames, _files in os.walk(str(root)):
            dirnames[:] = sorted(d for d in dirnames if d not in skip and not d.startswith("."))
            here = pathlib.Path(current)
            if is_analysis_folder(here):
                take(here)
                dirnames[:] = []
    return found


def report_dir(folder: PathLike) -> Optional[pathlib.Path]:
    """The folder's existing report directory, or ``None``."""
    folder = pathlib.Path(folder)
    for name in REPORT_DIR_NAMES:
        candidate = folder / name
        if candidate.is_dir():
            return candidate
    return None


def is_folder_processed(folder: PathLike) -> bool:
    """Whether the folder already has a report: PNGs, an ``axes_info.yaml`` or a DOCX."""
    directory = report_dir(folder)
    if directory is None:
        return False
    try:
        for name in os.listdir(directory):
            low = name.lower()
            if low.endswith((".png", ".docx")) or low == "axes_info.yaml":
                return True
    except OSError:
        return False
    return False


def report_images(folder: PathLike) -> List[pathlib.Path]:
    """The PNGs of a folder's report (the folder itself when it has no report), by name."""
    folder = pathlib.Path(folder)
    directory = report_dir(folder) or folder
    try:
        names = [n for n in os.listdir(directory) if n.lower().endswith(".png")]
    except OSError:
        return []
    return [directory / n for n in sorted(names, key=str.lower)]


def _remove_tree(path: pathlib.Path, retries: int = 3) -> bool:
    """Delete a directory tree, making read-only files writable (Windows); ``True`` when gone."""
    def writable(func, target, _exc_info):
        try:
            os.chmod(target, stat.S_IWRITE)
            func(target)
        except OSError:
            pass

    for _ in range(retries):
        shutil.rmtree(str(path), onerror=writable)
        if not path.exists():
            return True
        time.sleep(0.05)
    return not path.exists()


def clear_reports(folders: Iterable[PathLike]) -> int:
    """Delete the report directories of *folders*; returns how many folders had one."""
    cleared = 0
    for folder in folders:
        folder = pathlib.Path(folder)
        removed = False
        for name in REPORT_DIR_NAMES:
            directory = folder / name
            if directory.is_dir() and _remove_tree(directory):
                removed = True
        cleared += int(removed)
    return cleared


# -------------------------------------------------------------- the outputs
def _clean(values) -> np.ndarray:
    return np.nan_to_num(np.asarray(values, dtype=float), nan=0.0, posinf=0.0, neginf=0.0)


def hist_1d_csv(edges, counts, xlabel: str = "X") -> bytes:
    """A 1-D histogram as CSV: ``<label>Start,<label>End,Count`` per bin."""
    edges, counts = _clean(edges), _clean(counts)
    label = str(xlabel) if xlabel else "X"
    lines = [f"{label}Start,{label}End,Count"]
    lines += [f"{edges[i]},{edges[i + 1]},{counts[i]}" for i in range(len(counts))]
    return ("\n".join(lines) + "\n").encode("utf-8")


def hist_2d_csv(H, x_edges, y_edges, xlabel: str = "X", ylabel: str = "Y") -> bytes:
    """A 2-D histogram as CSV: x centres across, one row per y centre.

    *H* is ``(n_x, n_y)``: ``H[i, j]`` counts x bin *i* and y bin *j*.
    """
    H = _clean(H)
    x_edges, y_edges = _clean(x_edges), _clean(y_edges)
    x_centres = (x_edges[:-1] + x_edges[1:]) / 2.0
    y_centres = (y_edges[:-1] + y_edges[1:]) / 2.0
    lines = [f"{ylabel or 'Y'}/{xlabel or 'X'}," + ",".join(str(v) for v in x_centres)]
    for j, y in enumerate(y_centres):
        lines.append(",".join([str(y)] + [str(H[i, j]) for i in range(len(x_centres))]))
    return ("\n".join(lines) + "\n").encode("utf-8")


def _figure(figsize, dpi):
    from matplotlib.figure import Figure

    size = tuple(figsize) if isinstance(figsize, (list, tuple)) and len(figsize) == 2 else None
    return Figure(figsize=size, dpi=int(dpi) if dpi else 150)


def _png(fig) -> bytes:
    from matplotlib.backends.backend_agg import FigureCanvasAgg

    FigureCanvasAgg(fig)
    buffer = io.BytesIO()
    fig.savefig(buffer, format="png", bbox_inches="tight", facecolor="white")
    return buffer.getvalue()


def _widths(edges: np.ndarray) -> np.ndarray:
    widths = _clean(np.diff(edges))
    if widths.size:
        positive = widths[widths > 0]
        widths = np.where(widths > 0, widths, positive.min() if positive.size else 1e-9)
    return widths


def render_1d_png(edges, counts, title: str, xlabel: str, ylabel: str = "Count",
                  color: Optional[str] = None, edgecolor: Optional[str] = None,
                  linewidth: Optional[float] = None, figsize=None, dpi=None) -> bytes:
    """A 1-D histogram as bars, as PNG bytes (the ``1d_basic`` renderer)."""
    edges, counts = _clean(edges), _clean(counts)
    fig = _figure(figsize or (6, 4), dpi)
    ax = fig.add_subplot(111)
    ax.bar((edges[:-1] + edges[1:]) / 2.0, counts, width=_widths(edges), align="center",
           edgecolor=edgecolor or "black", linewidth=float(linewidth if linewidth is not None
                                                            else 0.2),
           color=color or "#4477aa")
    ax.set_title(title)
    ax.set_xlabel(xlabel or "")
    ax.set_ylabel(ylabel)
    ax.grid(True, linestyle=":", alpha=0.5)
    fig.tight_layout()
    return _png(fig)


def _extent(x_edges, y_edges) -> list:
    if x_edges.size and y_edges.size:
        return [x_edges[0], x_edges[-1], y_edges[0], y_edges[-1]]
    return [0, 1, 0, 1]


def render_2d_png(H, x_edges, y_edges, title: str, xlabel: str, ylabel: str,
                  cmap: str = "viridis", figsize=None, dpi=None) -> bytes:
    """A 2-D histogram (``H`` is ``(n_x, n_y)``) with a colour bar, as PNG bytes."""
    H, x_edges, y_edges = _clean(H), _clean(x_edges), _clean(y_edges)
    fig = _figure(figsize or (6, 5), dpi)
    ax = fig.add_subplot(111)
    image = ax.imshow(H.T, origin="lower", aspect="auto", extent=_extent(x_edges, y_edges),
                      cmap=cmap)
    fig.colorbar(image, ax=ax).set_label("Density")
    ax.set_title(title)
    ax.set_xlabel(xlabel or "")
    ax.set_ylabel(ylabel or "")
    fig.tight_layout()
    return _png(fig)


def render_2d_marginals_png(H, x_edges, y_edges, title: str, xlabel: str, ylabel: str,
                            cmap_2d: str = "Greys", color_x: str = "dimgrey",
                            color_y: str = "darkorange", figsize=None, dpi=None) -> bytes:
    """A 2-D histogram with its x marginal on top and y marginal on the right, as PNG bytes."""
    from matplotlib.gridspec import GridSpec

    H, x_edges, y_edges = _clean(H), _clean(x_edges), _clean(y_edges)
    x_centres = (x_edges[:-1] + x_edges[1:]) / 2.0 if x_edges.size > 1 else np.array([0.5])
    y_centres = (y_edges[:-1] + y_edges[1:]) / 2.0 if y_edges.size > 1 else np.array([0.5])
    fig = _figure(figsize or (8, 8), dpi)
    grid = GridSpec(2, 2, figure=fig, width_ratios=[4, 1.2], height_ratios=[1.2, 4],
                    hspace=0.05, wspace=0.05)
    ax_map = fig.add_subplot(grid[1, 0])
    ax_x = fig.add_subplot(grid[0, 0], sharex=ax_map)
    ax_y = fig.add_subplot(grid[1, 1], sharey=ax_map)
    image = ax_map.imshow(H.T, origin="lower", aspect="auto", extent=_extent(x_edges, y_edges),
                          cmap=cmap_2d)
    ax_x.bar(x_centres, H.sum(axis=1) if H.size else [0.0], width=_widths(x_edges),
             color=color_x, edgecolor="black", linewidth=0.2)
    ax_y.barh(y_centres, H.sum(axis=0) if H.size else [0.0], height=_widths(y_edges),
              color=color_y, edgecolor="black", linewidth=0.2)
    ax_map.set_xlabel(xlabel or "")
    ax_map.set_ylabel(ylabel or "")
    ax_x.tick_params(axis="x", labelbottom=False)
    ax_y.tick_params(axis="y", labelleft=False)
    colour_bar = fig.add_axes([0.92, 0.1, 0.02, 0.55])
    fig.colorbar(image, cax=colour_bar).set_label("Counts")
    fig.suptitle(title, y=0.98)
    fig.subplots_adjust(left=0.10, bottom=0.08, right=0.88, top=0.94)
    return _png(fig)


def docx_available() -> bool:
    """Whether python-docx is installed (the DOCX reports need it)."""
    try:
        import docx  # noqa: F401
    except ImportError:
        return False
    return True


# ---------------------------------------------------------------- one folder
@dataclass
class FolderReport:
    """What one folder's report consists of, before it is written.

    Attributes
    ----------
    folder : pathlib.Path
        The analysis folder.
    files : dict
        ``{file name: bytes}``: the PNGs, the CSVs and ``axes_info.yaml``.
    entries : list of dict
        ``{"title", "img", "csv"}`` per plot, the names in :attr:`files`.
    axes : list of dict
        Per plot: its axes' labels, ranges, bins and the settings used.
    warnings : list of str
        Plots that could not be drawn, and why.
    """

    folder: pathlib.Path
    files: Dict[str, bytes] = field(default_factory=dict)
    entries: List[Dict[str, str]] = field(default_factory=list)
    axes: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class ReportGenerator:
    """Histograms report plots the way the window does; one per batch of folders.

    Parameters
    ----------
    settings_file : path, optional
        The ``*.settings.json`` whose equations, constants and axis settings
        apply (default: the user's).
    axis_settings : mapping, optional
        Per-parameter axis settings laid over the file's -- the ones the
        window holds now, including axes set but not saved.
    templates : dict, optional
        From :func:`load_templates` (loaded when omitted).
    constants, equations : optional
        Constants and equations to use instead of the settings file's.
    """

    def __init__(self, settings_file: Optional[PathLike] = None,
                 axis_settings: Optional[Mapping[str, Any]] = None,
                 templates: Optional[Dict[str, Dict[str, Any]]] = None,
                 constants: Optional[Mapping[str, float]] = None,
                 equations: Optional[List[Mapping[str, str]]] = None) -> None:
        from ..app.model import ExplorerModel

        self.model = ExplorerModel(settings_file)
        if axis_settings:
            self.model.axis_settings.update(dict(axis_settings))
        if constants is not None:
            self.model.manager.constants = dict(constants)
        if equations is not None:
            self.model.manager.equations = list(equations)
        self.templates = templates if templates is not None else load_templates()

    def _choose(self, key: str, wanted: Any) -> None:
        from ..app.model import find_parameter

        if not isinstance(wanted, str) or not wanted:
            return
        names = self.model.parameter_names
        name = find_parameter(names, wanted) or find_parameter(names, wanted, contains=True)
        if name is None:
            raise KeyError(f"no parameter {wanted!r}")
        self.model.set_parameter(key, name)

    def _style(self, plot: Mapping[str, Any], default: str) -> tuple:
        name = str(plot.get("template") or default).lower()
        template = self.templates.get(name) or {}
        renderer = str(template.get("renderer") or name).lower()
        return renderer, dict(template.get("style") or {})

    def build(self, folder: PathLike, config: Mapping[str, Any]) -> FolderReport:
        """Read *folder* and histogram every plot of *config* into a :class:`FolderReport`.

        Raises
        ------
        FileNotFoundError
            When the folder is not there.
        ValueError
            When it holds no data.
        """
        from ..io import reader

        folder = pathlib.Path(folder)
        if not folder.exists():
            raise FileNotFoundError(str(folder))
        source = reader.read_burst_analysis(str(folder))
        if source is None or source.empty:
            raise ValueError(f"No data found in folder: {folder}")
        model = self.model
        model.set_source(source)
        report = FolderReport(folder=folder)
        for index, plot in enumerate(config.get("plots") or [], start=1):
            kind = str(plot.get("type", "1d")).lower()
            title = str(plot.get("title") or f"Plot {index}")
            try:
                self._choose("x", plot.get("x"))
                if kind == "2d" or str(plot.get("axis", "x")).lower() == "y":
                    self._choose("y", plot.get("y"))
                model.update()
                hist = model.histograms
                if hist is None:
                    raise ValueError("nothing to histogram")
                if kind == "2d":
                    self._add_2d(report, index, title, plot, hist)
                else:
                    self._add_1d(report, index, title, plot, hist)
            except Exception as exc:  # noqa: BLE001 - one bad plot does not stop the folder
                logging.warning("Report plot %r in %s: %s", title, folder, exc)
                report.warnings.append(f"{title}: {exc}")
        info = {"analysis_folder": str(folder.resolve()), "plots": report.axes}
        import yaml

        report.files["axes_info.yaml"] = yaml.safe_dump(
            info, sort_keys=False, allow_unicode=True).encode("utf-8")
        return report

    def _axis_info(self, label: str, edges) -> Dict[str, Any]:
        edges = np.asarray(edges)
        return {"label": label,
                "min": float(edges[0]) if edges.size else None,
                "max": float(edges[-1]) if edges.size else None,
                "bins": int(edges.size - 1) if edges.size else None,
                "settings": self.model.axis_settings.get(label)}

    def _add_2d(self, report: FolderReport, index: int, title: str, plot, hist) -> None:
        x_label, y_label = self.model.x.name, self.model.y.name
        # The model's map is (n_y, n_x); the files are written x-major.
        H = np.asarray(hist.H).T
        stem = f"{index:02d}_2d_{safe_token(x_label)}_{safe_token(y_label)}"
        report.files[f"{stem}.csv"] = hist_2d_csv(H, hist.x_edges, hist.y_edges, x_label,
                                                  y_label)
        renderer, style = self._style(plot, "2d_basic")
        if renderer in ("2d_marginals", "hist2d_marginals", "2d_with_marginals"):
            png = render_2d_marginals_png(
                H, hist.x_edges, hist.y_edges, title, x_label, y_label,
                cmap_2d=style.get("cmap_2d", "Greys"), color_x=style.get("color_x", "dimgrey"),
                color_y=style.get("color_y", "darkorange"), figsize=style.get("figsize"),
                dpi=style.get("dpi"))
        else:
            png = render_2d_png(H, hist.x_edges, hist.y_edges, title, x_label, y_label,
                                cmap=style.get("cmap", "viridis"), figsize=style.get("figsize"),
                                dpi=style.get("dpi"))
        report.files[f"{stem}.png"] = png
        report.entries.append({"title": title, "img": f"{stem}.png", "csv": f"{stem}.csv"})
        report.axes.append({"index": index, "type": "2d", "title": title,
                            "x": self._axis_info(x_label, hist.x_edges),
                            "y": self._axis_info(y_label, hist.y_edges)})

    def _add_1d(self, report: FolderReport, index: int, title: str, plot, hist) -> None:
        axis = str(plot.get("axis", "x")).lower()
        axis = "y" if axis == "y" else "x"
        edges, counts = hist.y if axis == "y" else hist.x
        label = self.model.axis(axis).name
        token = safe_token(label)
        csv_name = f"{index:02d}_{axis}-{token}.csv"
        png_name = f"{index:02d}_1d_{axis}-{token}.png"
        report.files[csv_name] = hist_1d_csv(edges, counts, label)
        _renderer, style = self._style(plot, "1d_basic")
        report.files[png_name] = render_1d_png(
            edges, counts, title, label, ylabel=style.get("ylabel", "Count"),
            color=style.get("color"), edgecolor=style.get("edgecolor"),
            linewidth=style.get("linewidth"), figsize=style.get("figsize"), dpi=style.get("dpi"))
        report.entries.append({"title": title, "img": png_name, "csv": csv_name})
        info = {"index": index, "type": "1d", "title": title, "axis": axis}
        info.update(self._axis_info(label, edges))
        report.axes.append(info)


def build_folder_report(folder: PathLike, config: Mapping[str, Any],
                        **generator_options) -> FolderReport:
    """One folder's report, in memory (see :class:`ReportGenerator`)."""
    return ReportGenerator(**generator_options).build(folder, config)


def _docx_tables(document, entries: Sequence[Mapping[str, str]]) -> None:
    """Plots two to a table: title, picture, the CSV's path."""
    from docx.shared import Inches

    for start in range(0, len(entries), 2):
        table = document.add_table(rows=3, cols=2)
        for column in range(2):
            top, middle, bottom = (table.cell(r, column) for r in range(3))
            if start + column >= len(entries):
                continue
            entry = entries[start + column]
            top.text = entry.get("title", "")
            run = middle.paragraphs[0].add_run()
            try:
                run.add_picture(entry["img"], width=Inches(3.0))
            except Exception:  # noqa: BLE001 - the path stands in for a picture that fails
                middle.paragraphs[0].add_run(entry.get("img", ""))
            bottom.text = f"CSV:   {entry['csv']}" if entry.get("csv") else ""
        document.add_paragraph("")


def write_folder_report(report: FolderReport, docx: bool = True) -> Dict[str, Any]:
    """Write a report into ``<folder>/report/``; returns ``{"folder", "entries", "docx"}``.

    The entries' ``img``/``csv`` become absolute paths. The DOCX
    (``<folder name>_report.docx``) is written when *docx* is set and
    python-docx is installed; ``"docx"`` is its path or ``None``.
    """
    folder = pathlib.Path(report.folder)
    directory = folder / "report"
    directory.mkdir(parents=True, exist_ok=True)
    for name, data in report.files.items():
        (directory / name).write_bytes(data)
    entries = [{"title": e["title"], "img": str((directory / e["img"]).resolve()),
                "csv": str((directory / e["csv"]).resolve())} for e in report.entries]
    docx_path = None
    if docx and docx_available():
        from docx import Document

        document = Document()
        sample = folder.parent.name if folder.parent else folder.name
        document.add_heading(f"ndX Report: {sample}", level=1)
        document.add_paragraph(str(folder.resolve()))
        _docx_tables(document, entries)
        docx_path = directory / f"{folder.name}_report.docx"
        document.save(str(docx_path))
    return {"folder": str(folder.resolve()), "entries": entries,
            "docx": str(docx_path) if docx_path else None}


def combined_docx_bytes(results: Sequence[Mapping[str, Any]]) -> Optional[bytes]:
    """One DOCX over several folders' written reports; ``None`` without python-docx."""
    if not docx_available():
        return None
    from docx import Document

    document = Document()
    document.add_heading("ndX Batch Report", level=1)
    for result in results:
        folder = pathlib.Path(result["folder"])
        document.add_heading(f"Sample: {folder.parent.name or folder.name}", level=2)
        document.add_paragraph(str(folder))
        _docx_tables(document, result.get("entries") or [])
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()
