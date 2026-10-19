"""The main menu, as data.

The same four menus and entries as the retired Qt window's menu bar, in the
same order with the same shortcuts. An
entry names the *action* the app runs; an action the app does not have yet is
shown disabled rather than left out, so what is still to be ported is visible
in the app itself.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from ..i18n import mark, tr

__all__ = ["MENUS", "build_menu_bar", "iter_entries"]

#: ``(title, entries)``; an entry is a dict (``label``, ``action``, optional
#: ``shortcut``, ``checkable``, ``checked``), ``None`` for a separator, or a
#: nested ``(title, entries)`` submenu.
MENUS: List[tuple] = [
    (mark("File"), [
        (mark("Import"), [
            {"label": mark("Import Text files (*.csv,*.dat)"), "action": "open_text",
             "shortcut": "Ctrl+O"},
            None,
            {"label": mark("Analysis file (*.zip, *.hdf)"), "action": "open_analysis_file"},
            {"label": mark("Analysis-Folder"), "action": "open_analysis_folder",
             "shortcut": "Ctrl+I"},
            {"label": mark("ChiSurf-Sampling"), "action": "open_sampling"},
            {"label": mark("ChiSurf project (*.cs.pto)"), "action": "open_cs_project",
             "description": mark("Open a sampling chain stored in a ChiSurf project; asks "
                                 "which one when the project holds several.")},
        ]),
        (mark("Save"), [
            {"label": mark("Burst IDs"), "action": "save_burst_ids"},
            {"label": mark("Histograms"), "action": "save_histograms"},
        ]),
        None,
        # the analysis view kept in the .pto (features/session.py)
        {"label": mark("Save session"), "action": "save_session", "shortcut": "Ctrl+S"},
        {"label": mark("Revert to saved session"), "action": "revert_session"},
        {"label": mark("Forget session"), "action": "forget_session"},
        {"label": mark("Download .pto with session…"), "action": "download_session_pto"},
        None,
        {"label": mark("Make Report"), "action": "make_report"},
        {"label": mark("Print window"), "action": "print_window"},
        None,
        {"label": mark("Exit"), "action": "exit"},
    ]),
    (mark("Settings"), [
        {"label": mark("Performance Settings"), "action": "performance_settings"},
        {"label": mark("Load settings"), "action": "load_settings"},
        (mark("Save settings"), [
            {"label": mark("Axis settings"), "action": "save_axis_settings"},
            {"label": mark("Constants"), "action": "save_constants"},
            {"label": mark("Equations"), "action": "save_equations"},
        ]),
        {"label": mark("Set default axis"), "action": "set_default_axis"},
    ]),
    (mark("View"), [
        {"label": mark("Plot controls"), "action": "toggle_plot_controls", "checkable": True,
         "checked": "show_plot_controls"},
        {"label": mark("Plot"), "action": "toggle_plot", "checkable": True, "checked": "show_plot"},
        {"label": mark("Parameters"), "action": "toggle_parameters", "checkable": True,
         "checked": "show_parameters"},
        {"label": mark("Overlays"), "action": "toggle_overlays", "checkable": True,
         "checked": "show_overlays"},
        {"label": mark("Fit Gaussians"), "action": "toggle_fit_gaussians", "checkable": True,
         "checked": "show_fit_gaussians"},
        {"label": mark("Equations"), "action": "toggle_equations", "checkable": True,
         "checked": "show_equations"},
        {"label": mark("UMAP"), "action": "umap"},
        {"label": mark("Find informative projections…"), "action": "find_projections"},
        {"label": mark("Find informative projections (z axis)…"), "action": "find_z_projections"},
        None,
        {"label": mark("Axis Control"), "action": "axis_control"},
        {"label": mark("Reset window layout"), "action": "reset_layout"},
    ]),
    (mark("Help"), [
        {"label": mark("Help"), "action": "help"},
        None,
        {"label": mark("About"), "action": "about"},
        {"label": mark("Update"), "action": "update_app"},
    ]),
]


def iter_entries(entries=None, path=()):
    """Every entry dict with its menu path, depth first."""
    for item in MENUS if entries is None else entries:
        if item is None:
            continue
        if isinstance(item, tuple):
            yield from iter_entries(item[1], path + (item[0],))
        else:
            yield path, item


def merged_menus(extra=()) -> List[tuple]:
    """:data:`MENUS` with the features' rows added: ``extra`` is
    ``[(path, entry)]``, *path* a tuple of menu titles. A missing submenu on
    the path is created at the end of its parent; a missing top-level menu
    goes before Help, which stays last."""
    import copy

    menus = copy.deepcopy(MENUS)
    for path, entry in extra:
        entries = None
        level = menus
        for title in path:
            found = next((item for item in level if isinstance(item, tuple) and item[0] == title),
                         None)
            if found is None:
                found = (title, [])
                last = level[-1] if level else None
                if level is menus and isinstance(last, tuple) and last[0] == "Help":
                    level.insert(len(level) - 1, found)
                else:
                    level.append(found)
            entries = found[1]
            level = entries
        if entries is not None:
            entries.append(entry)
    return menus


def build_menu_bar(available: Callable[[str], bool], checked: Callable[[str], bool],
                   extra=()):
    """The menus as emtk controls, each item tagged with its action.

    Parameters
    ----------
    available : callable
        ``available(action) -> bool``: whether the app can run it now. An
        action that cannot is drawn disabled.
    checked : callable
        ``checked(attr) -> bool`` for checkable entries.

    Returns
    -------
    emtk.widgets.menus.MenuBar
        Items carry ``.action`` (the action name).
    """
    from emtk.widgets.menus import Menu, MenuBar, MenuItem

    def build(entries) -> list:
        out = []
        for item in entries:
            if item is None:
                out.append(None)
            elif isinstance(item, tuple):
                out.append(Menu(tr(item[0]), build(item[1])))
            else:
                row = MenuItem(tr(item["label"]), shortcut=item.get("shortcut", ""),
                               checkable=bool(item.get("checkable")),
                               checked=bool(item.get("checked") and checked(item["checked"])),
                               enabled=available(item["action"]),
                               tooltip=tr(item.get("description") or item.get("tooltip")
                                          or tr("Run {label} in the current ndX session.")
                                          .format(label=tr(item["label"]))))
                row.action = item["action"]
                out.append(row)
        return out

    return MenuBar([Menu(tr(title), build(entries)) for title, entries in merged_menus(extra)])


def menu_specs(extra=()) -> Dict[str, Dict[str, Any]]:
    """Every entry by its action: :data:`MENUS` and the features' rows *extra*."""
    return {item["action"]: item for _path, item in iter_entries(merged_menus(extra))}


def refresh(bar, available: Callable[[str], bool], checked: Callable[[str], bool],
            specs: Optional[Dict[str, Dict[str, Any]]] = None) -> None:
    """Bring each item's enabled/checked state up to date with the app.

    *specs* (:func:`menu_specs`) are the entries the bar was built from, the
    features' rows included, so a feature's checkable row (Settings > Language)
    follows its state too; :data:`MENUS` alone by default.
    """
    from emtk.widgets.menus import Menu

    if specs is None:
        specs = menu_specs()

    def walk(entries):
        for entry in entries:
            if isinstance(entry, Menu):
                walk(entry.entries)
            elif entry is not None:
                entry.enabled = available(entry.action)
                spec = specs.get(entry.action)
                if spec and spec.get("checked"):
                    entry.checked = checked(spec["checked"])

    for menu in bar.menus:
        walk(menu.entries)
