"""Settings, View > Axis Control, File > Make Report and Help: the settings feature.

What it owns:

* Settings > Performance Settings, Load settings, Save settings > (Axis
  settings, Constants, Equations), Set default axis;
* View > Axis Control: which axes and axis titles the plots show and the
  titles' colour (``app.model.axis_display``, a
  :class:`~ndxplorer.plotting.axis_display.AxisDisplay` the plots read);
* File > Make Report: the report tool over analysis folders
  (:mod:`ndxplorer.export.report` does the work);
* Help > Help, About and Update.

Reading and writing settings is :mod:`ndxplorer.settings.bundle` and
:mod:`ndxplorer.settings.persist`, shared with the Qt window; the files are
asked for through ``app.io_service`` (the io feature's), so the same code
saves to disk on a desktop and to a download in a browser.

The dialogs are ``view.json`` specs beside this module (``settings/``), drawn
by :mod:`emtk.view_form`; only the report's image preview and progress bar
are drawn by hand.
"""

from __future__ import annotations

import json
import logging
import os
import pathlib
from typing import Any, Callable, Dict, List, Optional

from . import Feature

__all__ = ["SettingsFeature", "create", "HELP_TEXT"]

logger = logging.getLogger(__name__)

SPECS = pathlib.Path(__file__).with_name("settings")
DOCS_URL = "https://github.com/Fluorescence-Tools/ndxplorer"

#: Qt menu actions of this feature's scenarios -> the app's actions.
QT_ACTIONS: Dict[str, str] = {
    "actionPerformanceSettings": "performance_settings",
    "actionLoad_settings": "load_settings",
    "actionSave_axis_settings": "save_axis_settings",
    "actionConstants": "save_constants",
    "actionEquations": "save_equations",
    "actionSet_default_axis": "set_default_axis",
    "actionAxisControl": "axis_control",
    "actionMake_Report": "make_report",
    "actionHelp": "help",
    "actionAbout": "about",
    "actionUpdate": "update_app",
}

#: Actions that work without data.
WITHOUT_DATA = frozenset({"performance_settings", "load_settings", "save_constants",
                          "save_equations", "axis_control", "make_report", "help", "about",
                          "update_app"})

HELP_TEXT = (
    "ndXplorer shows a table of measurements -- bursts, pixels, samples -- as "
    "histograms you can gate.\n\n"
    "1. Open data: File > Import (a burst-analysis folder, text files, an "
    "analysis file or a ChiSurf sampling), or drop a file or folder on the window.\n"
    "2. Choose the x, y and z parameters in Plot controls; each has bins, a "
    "range (Auto), log and norm. Set stores a parameter's axis; Settings > Save "
    "settings > Axis settings writes them to a file.\n"
    "3. Drag a rectangle on the 2-D map to gate: the Selection table lists the "
    "gates, which can be inverted, disabled and edited.\n"
    "4. Parameters, Overlays, Equations and the analyses (clustering, Gaussian "
    "fit, informative projections) are in the tabs and the View menu.\n"
    "5. File > Make Report makes PNG/CSV/DOCX reports over many analysis "
    "folders from a report.yaml.\n\n"
    f"Documentation and source: {DOCS_URL}"
)


def load_spec(name: str) -> dict:
    """One of this feature's dialog specs, parsed."""
    with open(SPECS / f"{name}.view.json", encoding="utf-8") as handle:
        return json.load(handle)


def _versions() -> List[tuple]:
    """``(package, version)`` of ndXplorer and what it runs on."""
    import platform
    from importlib import metadata

    rows = []
    for name in ("ndxplorer", "tttrlib", "emtk", "numpy", "matplotlib"):
        try:
            rows.append((name, metadata.version(name)))
        except metadata.PackageNotFoundError:
            module = __import__(name) if name != "ndxplorer" else None
            version = getattr(module, "__version__", None) if module else None
            rows.append((name, str(version) if version else "not installed"))
        except Exception:  # noqa: BLE001 - a broken distribution is not a crash
            rows.append((name, "unknown"))
    rows.append(("Python", platform.python_version()))
    return rows


def _in_browser() -> bool:
    try:
        from emtk.web.page import in_browser
    except ImportError:
        return False
    return bool(in_browser())


# ------------------------------------------------------------------- dialogs
class Dialog:
    """A dialog of this feature: its spec, the model its fields bind to, its box.

    Subclasses are the model; :meth:`draw` lays the spec out in a centred
    window of :attr:`width` x :attr:`height` (a scenario may resize it).
    """

    spec_name = ""
    width, height = 480.0, 200.0

    def __init__(self, feature: "SettingsFeature", title: str) -> None:
        from emtk.dialog_window import DialogWindow
        from emtk.view_form import FormState

        self.feature = feature
        self.title = title
        self.spec = load_spec(self.spec_name)
        self.form = FormState()
        self.form.custom.update(self.custom_sections())
        self.done = False
        self.frame = DialogWindow(title, size=(self.width, self.height),
                                  key=f"settings-{self.spec_name}")
        self.frame.show()

    def custom_sections(self) -> Dict[str, Callable]:
        return {}

    def enabled(self, _name: str) -> bool:
        return True

    @property
    def box(self) -> Optional[tuple]:
        """Where the dialog was drawn last (header included)."""
        return self.frame.box

    def resize(self, width: float, height: float) -> None:
        """Take a new size, centred again."""
        self.width, self.height = float(width), float(height)
        self.frame.size = (self.width, self.height)
        self.frame.pos = None

    def begin(self, window: tuple) -> None:
        """The dialog's window; its content region is open until :meth:`end`."""
        if self.frame.begin(window) == "close":
            self.dismiss()

    def end(self) -> None:
        self.frame.end()

    def dismiss(self) -> None:
        """The header's ✕ or Escape: as the dialog's own Cancel/No/OK would."""
        self.close()

    def draw(self, window: tuple) -> None:
        from emtk.view_form import draw_form

        self.begin(window)
        draw_form(self.spec, self, self.form, titles=True)
        self.end()

    def close(self) -> None:
        self.done = True


class TextWindow(Dialog):
    """A titled text with OK: Help, About, Update."""

    spec_name = "text"
    width, height = 620.0, 420.0

    def __init__(self, feature, title: str, text: str, height: float = 420.0) -> None:
        super().__init__(feature, title)
        self.text = text
        self.height = height

    def body(self) -> str:
        return self.text

    def ok(self) -> None:
        self.close()


class Confirm(Dialog):
    """A Yes/No question; ``on_yes()`` runs on Yes."""

    spec_name = "confirm"
    width, height = 460.0, 170.0

    def __init__(self, feature, title: str, text: str, on_yes: Callable[[], None]) -> None:
        super().__init__(feature, title)
        self.text = text
        self.on_yes = on_yes

    def body(self) -> str:
        return self.text

    def yes(self) -> None:
        self.close()
        self.on_yes()

    def no(self) -> None:
        self.close()


_SIDES = ("bottom", "top", "left", "right")
#: Dialog prefixes -> the plots of :class:`AxisDisplay`.
_PLOT_OF = {"x": "xmarginal", "y": "ymarginal", "z": "zmarginal", "map": "map",
            "overlay": "overlay"}
_LABELS = {"y_label_top": ("ymarginal", "top"), "y_label_right": ("ymarginal", "right"),
           "x_label_top": ("xmarginal", "top"), "z_label_bottom": ("zmarginal", "bottom"),
           "z_label_left": ("zmarginal", "left")}


class AxisControl(Dialog):
    """View > Axis Control, on a copy of the plots' :class:`AxisDisplay` until Apply."""

    spec_name = "axis_control"
    width, height = 560.0, 560.0

    def __init__(self, feature) -> None:
        object.__setattr__(self, "_ready", False)
        super().__init__(feature, "Axis Control")
        self.edit = feature.display.copy()
        self.z_enable = bool(feature.app.panel.z_gate_enabled)
        self._ready = True

    # The toggles bind to ``<plot>_<side>`` and ``<axis>_label_<side>``.
    def __getattr__(self, name: str):
        plot, _, side = name.rpartition("_")
        if plot in _PLOT_OF and side in _SIDES:
            return self.edit.visible(_PLOT_OF[plot], side)
        if name in _LABELS:
            return self.edit.label_switch(*_LABELS[name])
        raise AttributeError(name)

    def __setattr__(self, name: str, value) -> None:
        if self.__dict__.get("_ready"):
            plot, _, side = name.rpartition("_")
            if plot in _PLOT_OF and side in _SIDES:
                self.edit.set_visible(_PLOT_OF[plot], side, bool(value))
                return
            if name in _LABELS:
                self.edit.set_label(*_LABELS[name], bool(value))
                return
        object.__setattr__(self, name, value)

    @property
    def enable_all_labels(self) -> bool:
        return self.edit.enable_all_labels

    @enable_all_labels.setter
    def enable_all_labels(self, value: bool) -> None:
        self.edit.set_enable_all_labels(bool(value))

    @property
    def title_color(self) -> str:
        from ...plotting.axis_display import colour_hex

        return colour_hex(self.edit.title_colour)

    @title_color.setter
    def title_color(self, value: str) -> None:
        self.edit.set_title_colour(value)

    def enabled(self, name: str) -> bool:
        if name.startswith("overlay_"):
            # The Qt overlay is a drawing surface without axes, and so is the
            # emtk one: its axis switches are there and disabled, as in Qt.
            return False
        if name in ("z_bottom", "z_left"):
            return self.z_enable
        if name in _LABELS:
            return not self.edit.enable_all_labels
        return True

    # ------------------------------------------------------------- buttons
    def apply(self) -> None:
        self.feature.display.assign(self.edit)
        panel = self.feature.app.panel
        if bool(panel.z_gate_enabled) != bool(self.z_enable):
            panel.z_gate_enabled = bool(self.z_enable)

    def ok(self) -> None:
        self.apply()
        self.close()

    def cancel(self) -> None:
        self.close()

    def save(self) -> None:
        self.apply()
        self.feature.save_label_settings()


class PerformanceDialog(Dialog):
    """Settings > Performance Settings."""

    spec_name = "performance"
    width, height = 580.0, 460.0

    def __init__(self, feature) -> None:
        super().__init__(feature, "Performance Settings")
        from ...utils.performance_config import get_performance_config

        self.show(get_performance_config())

    def show(self, config) -> None:
        self.use_fast_histogram = bool(config.use_fast_histogram)
        self.parallel_histogram = bool(config.parallel_histogram)
        self.histogram_threads = int(config.histogram_threads)
        self.aggressive_caching = bool(config.aggressive_caching)
        self.general_cache_mb = int(config.general_cache_memory_mb)
        self.plot_backend = str(config.plot_backend)

    def config(self):
        from ...utils.performance_config import PerformanceConfig

        return PerformanceConfig(
            use_fast_histogram=bool(self.use_fast_histogram),
            general_cache_memory_mb=float(self.general_cache_mb),
            parallel_histogram=bool(self.parallel_histogram),
            aggressive_caching=bool(self.aggressive_caching),
            histogram_threads=int(self.histogram_threads),
            plot_backend=self.plot_backend,
        )

    def heading(self) -> str:
        return "Performance Configuration"

    def backend_note(self) -> str:
        return ("Plots are drawn by emtk here; the Qt window's plot backend "
                f"({self.plot_backend}) is kept in the settings for it.")

    def settings_note(self) -> str:
        from ...utils.performance_config import default_settings_file

        path = str(default_settings_file())
        home = os.path.expanduser("~")
        if path.startswith(home):
            path = "~" + path[len(home):]
        return f"Settings are saved to: {path}"

    def apply(self) -> bool:
        from ...utils.performance_config import save_performance_config

        try:
            save_performance_config(self.config())
        except (OSError, ValueError) as exc:
            self.feature.message("Error", f"Failed to save settings: {exc}")
            return False
        self.feature.message("Settings Applied", "Performance settings have been saved.\n\n"
                             "Some changes may require restarting ndX to take full effect.")
        return True

    def ok(self) -> None:
        if self.apply():
            self.close()

    def cancel(self) -> None:
        self.close()

    def reset(self) -> None:
        from ...utils.performance_config import PerformanceConfig

        def yes() -> None:
            self.show(PerformanceConfig())
            self.feature.message("Reset", "Settings reset to defaults. Apply or OK saves them.")

        self.feature.ask("Reset Settings", "Reset all performance settings to their default "
                         "values?\n\nThis will clear your custom configuration.", yes)


class ReportTool(Dialog):
    """File > Make Report: folders, report.yaml, generated images, Generate."""

    spec_name = "report"
    width, height = 1000.0, 700.0

    def __init__(self, feature) -> None:
        super().__init__(feature, "ndX Report Tool")
        from ...export.report import default_config_text
        from ...settings import get_settings_path

        self.folders: List[str] = []
        self._rows: List[dict] = []
        self._rows_token = None
        self.selected: Optional[str] = None
        self.config_text = default_config_text(get_settings_path())
        self.image_name = ""
        self._images: List[pathlib.Path] = []
        self._images_for = None
        self._preview = None
        self._preview_key = None
        #: The batch being generated: ``{"targets", "index", "results", "generator", ...}``.
        self.job: Optional[Dict[str, Any]] = None
        self.last_status = ""

    def custom_sections(self) -> Dict[str, Callable]:
        return {"report_image": self._draw_image, "report_progress": self._draw_progress}

    # ------------------------------------------------------------ folders
    def folder_rows(self) -> List[dict]:
        from ...export.report import is_folder_processed

        token = (tuple(self.folders), self.job is not None and self.job["index"],
                 self.feature.app.frames // 30)
        if token != self._rows_token:
            self._rows_token = token
            self._rows = [{"path": p, "processed": is_folder_processed(p)} for p in self.folders]
        return self._rows

    def select_folder(self, record) -> None:
        self.selected = None if record is None else str(record["path"])
        self._images_for = None

    def add_paths(self, paths) -> None:
        for path in paths:
            path = str(path)
            if path and os.path.isdir(path) and path not in self.folders:
                self.folders.append(path)
                self.selected = path
                self._images_for = None

    def add_dropped(self, paths) -> None:
        """A drop adds the analysis folders in what was dropped, as the Qt list did."""
        from ...export.report import discover_analysis_folders

        roots = [p for p in paths if os.path.isdir(str(p))]
        found = [str(p) for p in discover_analysis_folders(roots)]
        if not found:
            self.feature.message("No analysis folders found", "No analysis folders were found "
                                 "in the dropped directory/directories.")
            return
        self.add_paths(found)

    def folder_menu(self, record, _key, where) -> None:
        """Right click on a folder: Copy Path."""
        from emtk.widgets.menus import MenuItem

        if record is None:
            return
        path = str(record["path"])
        self.feature.app.open_menu([MenuItem("Copy Path(s)")], where[0], where[1],
                                   lambda _item: _copy(path))

    def add_folder(self) -> None:
        self.feature.app.io_service.ask_folder("Select analysis folder",
                                               lambda path: self.add_paths([path]))

    def remove_folder(self) -> None:
        if self.selected in self.folders:
            self.folders.remove(self.selected)
        self.selected = self.folders[-1] if self.folders else None
        self._images_for = None

    def clear_folders(self) -> None:
        if not self.folders:
            return

        def yes() -> None:
            self.folders = []
            self.selected = None
            self._images_for = None

        self.feature.ask("Clear list", "Remove all folders from the list?", yes)

    # ------------------------------------------------------------- config
    def load_config(self) -> None:
        def chosen(paths) -> None:
            from ...export.report import ConfigError, parse_config

            path = paths[0]
            with open(path, "r", encoding="utf-8") as handle:
                text = handle.read()
            try:
                parse_config(text, json_text=path.lower().endswith(".json"))
            except ConfigError as exc:
                def keep() -> None:
                    self.config_text = text

                self.feature.ask("Parse warning", "File read, but failed to parse config "
                                 f"(will still load text):\n{exc}\n\nLoad as-is?", keep)
                return
            self.config_text = text

        self.feature.app.io_service.ask_open(
            "Open config", [("YAML/JSON", ["*.yaml", "*.yml", "*.json"]), ("All files", ["*"])],
            chosen)

    def save_config(self) -> None:
        from ...export.report import ConfigError, config_text, parse_config

        try:
            data = parse_config(self.config_text)
        except ConfigError as exc:
            self.feature.message("Save error", str(exc))
            return

        def chosen(path: str) -> None:
            if path.lower().endswith(".json"):
                payload = json.dumps(data, indent=2)
            else:
                if not path.lower().endswith((".yaml", ".yml")):
                    path += ".yaml"
                payload = config_text(data)
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(payload)

        self.feature.app.io_service.ask_save(
            "Save config", [("YAML", ["*.yaml"]), ("JSON", ["*.json"])], "report.yaml", chosen)

    # ------------------------------------------------------------- images
    @property
    def selected_path(self) -> str:
        if not self.selected:
            return ""
        try:
            return str(pathlib.Path(self.selected).resolve())
        except OSError:
            return self.selected

    @selected_path.setter
    def selected_path(self, _value) -> None:
        pass

    def _refresh_images(self) -> None:
        from ...export.report import report_images

        token = (self.selected, self.job is not None and self.job["index"])
        if token == self._images_for:
            return
        self._images_for = token
        self._images = report_images(self.selected) if self.selected else []
        names = [p.name for p in self._images]
        if self.image_name not in names:
            self.image_name = names[0] if names else ""

    def image_options(self) -> List[str]:
        self._refresh_images()
        return [p.name for p in self._images] or [""]

    def _image_path(self) -> Optional[pathlib.Path]:
        self._refresh_images()
        return next((p for p in self._images if p.name == self.image_name), None)

    def _draw_image(self, section, model, state, width: float) -> None:
        """The chosen image, fitted into what is left of the panel."""
        import emtk

        avail = emtk.get_content_region_avail()
        height = max(float(avail[1]) - 4.0, 120.0)
        x, y = emtk.get_cursor_screen_pos()
        emtk.dummy(width, height)
        draw = emtk.get_window_draw_list()
        draw.add_rect_filled((x, y), (x + width, y + height), (34, 34, 34, 255))
        path = self._image_path()
        if path is None:
            draw.add_text((x + 8.0, y + 8.0), (200, 200, 200, 255), "No images found")
            return
        picture = self._picture(path)
        if picture is None:
            draw.add_text((x + 8.0, y + 8.0), (200, 200, 200, 255), f"Cannot show {path.name}")
            return
        io = emtk.get_io()
        mx, my = io.mouse_pos
        if io.mouse_clicked[1] and x <= mx < x + width and y <= my < y + height:
            from emtk.widgets.menus import MenuItem

            self.feature.app.open_menu([MenuItem("Copy Image Path")], mx, my,
                                       lambda _item: _copy(str(path)))
        texture, (iw, ih) = picture
        scale = min(width / iw, height / ih)
        pw, ph = iw * scale, ih * scale
        left, top = x + (width - pw) / 2.0, y + (height - ph) / 2.0
        draw.add_image(texture, (left, top), (left + pw, top + ph))

    def _picture(self, path: pathlib.Path):
        """The PNG as a texture, read once per file version."""
        try:
            key = (str(path), path.stat().st_mtime)
        except OSError:
            return None
        if key != self._preview_key:
            from emtk.texture import Texture
            from PIL import Image

            try:
                with Image.open(path) as image:
                    image = image.convert("RGBA")
                    image.thumbnail((1200, 1200))
                    self._preview = (Texture(image.width, image.height, image.tobytes()),
                                     (image.width, image.height))
            except OSError:
                self._preview = None
            self._preview_key = key
        return self._preview

    # ---------------------------------------------------------- generating
    def status(self) -> str:
        job = self.job
        if job is None:
            return self.last_status
        total = len(job["targets"])
        if job["index"] < total:
            return f"Generating reports... {job['index'] + 1}/{total}: {job['targets'][job['index']]}"
        return "Generating reports..."

    def _draw_progress(self, section, model, state, width: float) -> None:
        import emtk

        if self.job is None:
            return
        total = max(len(self.job["targets"]), 1)
        emtk.progress_bar(self.job["index"] / total, (width, 0.0),
                          f"{self.job['index']}/{total}")

    def enabled(self, name: str) -> bool:
        running = self.job is not None
        if name == "cancel_generation":
            return running
        if name in ("generate", "clear_reports", "add_folder", "remove_folder", "clear_folders"):
            if running:
                return False
            if name == "remove_folder":
                return self.selected in self.folders
            if name in ("generate", "clear_reports", "clear_folders"):
                return bool(self.folders)
        return True

    def generate(self) -> None:
        from ...export.report import (ConfigError, discover_analysis_folders,
                                      is_folder_processed, parse_config)

        try:
            config = parse_config(self.config_text)
        except ConfigError as exc:
            self.feature.message("Invalid config", str(exc))
            return
        if not self.folders:
            self.feature.message("No folders", "Please add analysis folders.")
            return
        targets = discover_analysis_folders(self.folders)
        if not targets:
            self.feature.message("No analysis folders found", "No valid analysis subfolders "
                                 "were found. Please check your selection.")
            return
        targets = [t for t in targets if not is_folder_processed(t)]
        if not targets:
            self.feature.message("Nothing to do", "All selected analysis folders already have a "
                                 "report. Nothing to generate.")
            return
        self.job = {"config": config, "targets": targets, "index": 0, "results": [],
                    "errors": [], "cancelled": False, "generator": None}

    def cancel_generation(self) -> None:
        if self.job is not None:
            self.job["cancelled"] = True

    def step(self) -> None:
        """One folder of the running batch; the window draws between folders."""
        job = self.job
        if job is None:
            return
        if job["cancelled"] or job["index"] >= len(job["targets"]):
            self._finish()
            return
        folder = job["targets"][job["index"]]
        try:
            from ...export.report import ReportGenerator, write_folder_report

            if job["generator"] is None:
                model = self.feature.app.model
                job["generator"] = ReportGenerator(settings_file=self.feature.settings_file,
                                                   axis_settings=model.axis_settings)
            report = job["generator"].build(folder, job["config"])
            job["results"].append(write_folder_report(report))
            job["errors"].extend(f"{folder}: {w}" for w in report.warnings)
        except Exception as exc:  # noqa: BLE001 - one folder's error, reported, the rest go on
            logger.exception("report for %s", folder)
            job["errors"].append(f"Error for {folder}: {exc}")
        job["index"] += 1
        self._images_for = None

    def _finish(self) -> None:
        from ...export.report import combined_docx_bytes, docx_available

        job, self.job = self.job, None
        self._images_for = None
        results = job["results"]
        done = "Generation canceled." if job["cancelled"] else "Reports generated."
        self.last_status = f"{done} {len(results)} folder(s)."
        text = done
        if not docx_available():
            text += ("\n\npython-docx is not installed: PNGs and CSVs were written, no DOCX.")
        if job["errors"]:
            text += "\n\n" + "\n".join(job["errors"][:8])
        self.feature.message("Canceled" if job["cancelled"] else "Done", text)
        if len(results) > 1 and docx_available():
            data = combined_docx_bytes(results)
            if data:
                self.feature.app.io_service.save_bytes(
                    "ndX_Batch_Report.docx", data,
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    title="Save Final Combined Report", filters=[("DOCX", ["*.docx"])])

    def clear_reports(self) -> None:
        from ...export.report import clear_reports, discover_analysis_folders

        roots = [self.selected] if self.selected in self.folders else list(self.folders)
        # The listed folders and the analysis folders under them, as Generate finds them.
        targets = list(dict.fromkeys(
            [pathlib.Path(r) for r in roots] + discover_analysis_folders(roots)))
        if not roots:
            self.feature.message("No folders", "No analysis folders to clear.")
            return

        def yes() -> None:
            cleared = clear_reports(targets)
            self._images_for = None
            self._rows_token = None
            if cleared:
                self.feature.message("Reports cleared", f"Cleared reports for {cleared} folder(s).")
            else:
                self.feature.message("Nothing to clear", "No report folders were found to delete.")

        count = len(targets) - len(roots) or len(roots)
        self.feature.ask("Clear Reports", "This will permanently delete report folders for "
                         f"{count} analysis folder(s). Continue?", yes)

    def close(self) -> None:
        if self.job is not None:
            self.job["cancelled"] = True
            return
        super().close()

    # ------------------------------------------------------------- layout
    def draw(self, window: tuple) -> None:
        """Folders on the left; report.yaml, images and Generate on the right."""
        import emtk
        from emtk.view_form import draw_sections

        self.begin(window)
        x, top, w, h = self.frame.content_box
        sections = {s["title"]: s for s in self.spec["sections"]}
        footer = 92.0 if self.job is None else 118.0
        body_h = h - footer - 6.0
        y = top
        left_w = max(260.0, w * 0.34)
        pad = 10.0
        columns = (
            ((x, top, left_w - pad, body_h), ["Analysis folders (drop here):"]),
            ((x + left_w, top, w - left_w, body_h),
             ["Report YAML (report.yaml):", "Browse generated images"]),
            ((x, y + h - footer, w, footer), ["Generate"]),
        )
        for child, titles in columns:
            emtk.begin_child(child)
            draw_sections([sections[t] for t in titles], self, self.form, titles=True)
            emtk.end_child()
        self.end()


# ------------------------------------------------------------------- feature
class SettingsFeature(Feature):
    """Settings, Axis Control, the report tool and Help."""

    name = "settings"

    def __init__(self, app) -> None:
        super().__init__(app)
        from ...plotting.axis_display import AxisDisplay

        model = app.model
        labels = model.bundle.axis_labels if model.bundle.settings.get("axis_labels") else None
        #: What the plots show of their axes (View > Axis Control).
        self.display = AxisDisplay.from_label_settings(labels)
        model.axis_display = self.display
        #: The settings file in use: the one loaded last (Settings > Load settings).
        self.settings_file = pathlib.Path(model.bundle.path)
        self.window: Optional[Dialog] = None
        self.question: Optional[Confirm] = None
        self._file_answers: List[str] = []

    # --------------------------------------------------------------- hooks
    def actions(self) -> Dict[str, Callable[[], Any]]:
        return {
            "performance_settings": self.performance_settings,
            "load_settings": self.load_settings,
            "save_axis_settings": self.save_axis_settings,
            "save_constants": self.save_constants,
            "save_equations": self.save_equations,
            "set_default_axis": self.set_default_axis,
            "axis_control": self.axis_control,
            "make_report": self.make_report,
            "help": self.help,
            "about": self.about,
            "update_app": self.update_app,
        }

    def available(self, action: str) -> Optional[bool]:
        if action not in self.actions():
            return None
        if action in WITHOUT_DATA:
            return True
        return self.app.model.has_data

    def animating(self) -> bool:
        return isinstance(self.window, ReportTool) and self.window.job is not None

    def draw_windows(self) -> bool:
        box = self.app.box
        window = self.window
        if window is not None:
            if isinstance(window, ReportTool) and window.job is not None \
                    and self.question is None and self.app.message is None:
                window.step()
            window.draw(box)
            if window.done and self.window is window:
                self.window = None
        if self.question is not None:
            self.question.draw(box)
            if self.question.done:
                self.question = None
        return self.window is not None or self.question is not None

    def files_dropped(self, paths) -> bool:
        if isinstance(self.window, ReportTool) and self.window.job is None:
            self.window.add_dropped(paths)
            return True
        return False

    # ------------------------------------------------------------- helpers
    def message(self, title: str, text: str) -> None:
        self.app.message = (title, text)

    def ask(self, title: str, text: str, on_yes: Callable[[], None]) -> None:
        self.question = Confirm(self, title, text, on_yes)

    def _io(self):
        return self.app.io_service

    def _axis_names(self) -> List[str]:
        model = self.app.model
        return [a.name for a in (model.x, model.y, model.z) if a.name]

    def _settings_dir(self) -> pathlib.Path:
        from ...settings import get_settings_path

        return get_settings_path()

    # ------------------------------------------------------------ Settings
    def performance_settings(self) -> None:
        self.window = PerformanceDialog(self)

    def load_settings(self) -> None:
        """Settings > Load settings: a ``*.settings.json`` and the files it names."""
        self._io().ask_open("ndX settings file",
                            [("ndX settings", ["*.settings.json"]), ("All files", ["*"])],
                            lambda paths: self.apply_settings(paths[0]))

    def apply_settings(self, path) -> None:
        """Take a settings file: colormap, axis settings, labels, equations, constants."""
        from ...plotting.colormap_lut import available_colormaps
        from ...settings.bundle import read_settings

        model = self.app.model
        bundle = read_settings(path)
        model.bundle.settings.update(bundle.settings)
        model.bundle.path = bundle.path
        self.settings_file = pathlib.Path(bundle.path)
        colormap = bundle.settings.get("colormap")
        if colormap and colormap in available_colormaps():
            model.colormap = str(colormap)
        model.axis_settings.update(bundle.axis_settings)
        if bundle.settings.get("axis_labels"):
            self.display.update_label_settings(bundle.axis_labels or {})
        if bundle.equations_path is not None:
            model.bundle.equations = bundle.equations
            model.bundle.equations_path = bundle.equations_path
            model.manager.equations = list(bundle.equations)
        model.bundle.constants.update(bundle.constants)
        # A plain dict: whoever keeps the constants live (the Parameters tab's
        # group) takes the values over from it on its next frame.
        constants = dict(model.manager.constants or {})
        constants.update(bundle.constants)
        model.manager.constants = constants
        if model.has_data:
            model.manager.compute_columns()
            model.source = model.manager.data_source
            model.invalidate()
            self.app.data_changed()

    def save_axis_settings(self) -> None:
        """Settings > Save settings > Axis settings: the axes in use, into an ``*.axis.json``."""
        from ...settings.persist import write_axis_settings

        model = self.app.model
        for key in ("x", "y", "z"):
            model.remember_axis(key)
        names = self._axis_names()
        self._io().ask_save("Axis settings file", [("Axis file", ["*.axis.json"])],
                            "mfd.axis.json",
                            lambda path: write_axis_settings(path, model.axis_settings, names))

    def _owner(self, attr: str, method: str):
        """``feature.<attr>.<method>`` of the feature that keeps that panel, or ``None``."""
        for other in self.app.features:
            panel = getattr(other, attr, None)
            if other is not self and callable(getattr(panel, method, None)):
                return getattr(panel, method)
        return None

    def save_constants(self) -> None:
        """Settings > Save settings > Constants: ``mfd.constants.json`` in the settings folder.

        The Parameters tab's own Save when it is there (values, bounds and
        fixed flags), as the Qt entry did; the values otherwise.
        """
        from ...settings.persist import constants_payload, read_json, write_constants

        owner = self._owner("constants", "save_parameters")
        if owner is not None:
            owner()
            return
        name = self.app.model.bundle.settings.get("constants") or "mfd.constants.json"
        path = self._settings_dir() / name
        values = dict(self.app.model.manager.constants)
        try:
            write_constants(path, constants_payload(values, read_json(path)))
        except OSError as exc:
            self.message("Save constants", f"Could not write {path}:\n{exc}")
            return
        self.message("Save constants", f"Constants saved to {path}.")

    def save_equations(self) -> None:
        """Settings > Save settings > Equations: the equations into a YAML (Qt: not connected)."""
        from ...settings.persist import write_equations

        owner = self._owner("equations", "save_equations_file")
        if owner is not None:
            owner()
            return
        equations = list(self.app.model.manager.equations or [])
        name = self.app.model.bundle.settings.get("equations") or "mfd.equations.yaml"
        self._io().ask_save("Equations file", [("Equations", ["*.yaml", "*.yml"])],
                            pathlib.Path(name).name,
                            lambda path: write_equations(path, equations))

    def set_default_axis(self) -> None:
        """Settings > Set default axis: x, y, z, weight and colormap into the settings file."""
        from ...settings.persist import write_default_axes

        model = self.app.model
        try:
            data = write_default_axes(self.settings_file, model.x.name, model.y.name,
                                      model.z.name, weight=model.weight_name or None,
                                      colormap=model.colormap,
                                      fallback=model.bundle.settings)
        except OSError as exc:
            self.message("Set default axis", f"Failed to save default axis settings:\n{exc}")
            return
        model.bundle.settings.update(data)
        self.message("Set default axis", "Default axis settings have been updated.")

    def save_label_settings(self) -> None:
        """Axis Control's Save: the axis titles and colour into the settings folder."""
        from ...plotting.axis_display import write_label_settings

        name = self.app.model.bundle.settings.get("axis_labels") or "axis_labels.yaml"
        path = self._settings_dir() / name
        try:
            write_label_settings(path, self.display.label_settings)
        except OSError as exc:
            self.message("Axis Control", f"Error saving axis label settings.\nDetails: {exc}")
            return
        self.message("Axis Control", "Axis label and font settings saved and applied "
                     "successfully.")

    # --------------------------------------------------------------- View
    def axis_control(self) -> None:
        self.window = AxisControl(self)

    # --------------------------------------------------------------- File
    def make_report(self) -> None:
        self.window = ReportTool(self)

    # --------------------------------------------------------------- Help
    def help(self) -> None:
        self.window = TextWindow(self, "ndXplorer Help", HELP_TEXT, height=440.0)

    def about(self) -> None:
        rows = "\n".join(f"{name}: {version}" for name, version in _versions())
        text = ("ndXplorer -- interactive exploration of multidimensional data "
                "(single-molecule fluorescence, sampling, any table).\n\n"
                f"{rows}\n\nAuthor: Thomas-Otavio Peulen. License: GPL-2.1.\n{DOCS_URL}")
        self.window = TextWindow(self, "About ndXplorer", text, height=380.0)

    def update_app(self) -> None:
        version = dict(_versions()).get("ndxplorer", "unknown")
        if _in_browser():
            how = "In the browser the page loads the newest published build: reload the page."
        else:
            how = ("Update with the package manager that installed ndXplorer:\n"
                   "  conda update -c tpeulen ndxplorer\n"
                   "  pip install --upgrade ndxplorer\n"
                   "Then restart ndXplorer.")
        self.window = TextWindow(self, "Update", f"Installed: ndXplorer {version}\n\n{how}",
                                 height=260.0)

    # ------------------------------------------------------------- capture
    def capture_actions(self) -> Dict[str, str]:
        return dict(QT_ACTIONS)

    def capture_ops(self) -> Dict[str, Callable]:
        return {"resize_dialog": self._op_resize, "click": self._op_click,
                "file_answer": self._op_file_answer}

    def capture_targets(self) -> Dict[str, Callable]:
        return {"dialog": self._dialog_box, "dialog:Report": self._report_box}

    def _dialog_box(self, _replay) -> Optional[tuple]:
        if self.app.message is not None:
            return None
        if self.question is not None:
            return self.question.box
        if self.app.io_service.busy:
            return None
        return self.window.box if self.window is not None else None

    def _report_box(self, _replay) -> Optional[tuple]:
        return self.window.box if isinstance(self.window, ReportTool) else None

    def _op_resize(self, replay, step: dict):
        """``resize_dialog``: the Qt dialog had to be enlarged to show every control;
        these dialogs are sized to hold theirs, so the step changes nothing."""
        if self.window is None:
            return False
        replay.settle()
        return True

    def _op_file_answer(self, replay, step: dict):
        """``file_answer``: the answer to the next file dialog this feature opens."""
        if self.window is None:
            return False
        self._file_answers.append(replay.dataset(step["path"]))
        self._answer_pending()
        return True

    def _answer_pending(self) -> None:
        service = self.app.io_service
        if self._file_answers and service.busy:
            service.answer(self._file_answers.pop(0))

    def _op_click(self, replay, step: dict):
        """``click`` on a button of this feature's dialog, found by its label."""
        import re

        match = re.fullmatch(r"button\('([^']+)'\)", step.get("widget", ""))
        window = self.window
        if match is None or window is None:
            return False
        label = match.group(1)
        for section in _buttons(window.spec):
            if section.get("label") == label:
                action = section["action"]
                replay.settle()
                rect = window.form.rects.get(action)
                if rect is not None:
                    replay.click_rect(rect)
                else:
                    getattr(window, action)()
                self._answer_pending()
                replay.settle(3)
                return True
        return False


def _copy(text: str) -> None:
    """Put *text* on the clipboard (the system's, or the page's in a browser)."""
    from emtk import clipboard

    clipboard.copy(text)


def _buttons(spec) -> List[dict]:
    """Every button of a spec, depth first."""
    found = []
    for section in spec.get("sections") or []:
        if section.get("type") == "button_row":
            found.extend(section.get("buttons") or [])
        found.extend(_buttons(section))
    return found


def create(app) -> SettingsFeature:
    return SettingsFeature(app)
