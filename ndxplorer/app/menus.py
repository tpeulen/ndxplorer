"""The main menu, as data.

The same four menus and entries as the Qt window's menu bar
(``plotting/plot_main.ui``), in the same order with the same shortcuts. An
entry names the *action* the app runs; an action the app does not have yet is
shown disabled rather than left out, so what is still to be ported is visible
in the app itself.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

__all__ = ["MENUS", "build_menu_bar", "iter_entries"]

#: ``(title, entries)``; an entry is a dict (``label``, ``action``, optional
#: ``shortcut``, ``checkable``, ``checked``), ``None`` for a separator, or a
#: nested ``(title, entries)`` submenu.
MENUS: List[tuple] = [
    ("File", [
        ("Import", [
            {"label": "Import Text files (*.csv,*.dat)", "action": "open_text", "shortcut": "Ctrl+O"},
            None,
            {"label": "Analysis file (*.zip, *.hdf)", "action": "open_analysis_file"},
            {"label": "Analysis-Folder", "action": "open_analysis_folder", "shortcut": "Ctrl+I"},
            {"label": "ChiSurf-Sampling", "action": "open_sampling"},
        ]),
        ("Save", [
            {"label": "Burst IDs", "action": "save_burst_ids"},
            {"label": "Histograms", "action": "save_histograms"},
        ]),
        None,
        {"label": "Make Report", "action": "make_report"},
        {"label": "Print window", "action": "print_window"},
        None,
        {"label": "Exit", "action": "exit"},
    ]),
    ("Settings", [
        {"label": "Performance Settings", "action": "performance_settings"},
        {"label": "Load settings", "action": "load_settings"},
        ("Save settings", [
            {"label": "Axis settings", "action": "save_axis_settings"},
            {"label": "Constants", "action": "save_constants"},
            {"label": "Equations", "action": "save_equations"},
        ]),
        {"label": "Set default axis", "action": "set_default_axis"},
    ]),
    ("View", [
        {"label": "Plot controls", "action": "toggle_plot_controls", "checkable": True,
         "checked": "show_plot_controls"},
        {"label": "Plot", "action": "toggle_plot", "checkable": True, "checked": "show_plot"},
        {"label": "Parameters", "action": "toggle_parameters", "checkable": True,
         "checked": "show_parameters"},
        {"label": "Overlays", "action": "toggle_overlays", "checkable": True,
         "checked": "show_overlays"},
        {"label": "Fit Gaussians", "action": "toggle_fit_gaussians", "checkable": True,
         "checked": "show_fit_gaussians"},
        {"label": "Equations", "action": "toggle_equations", "checkable": True,
         "checked": "show_equations"},
        {"label": "UMAP", "action": "umap"},
        {"label": "Find informative projections…", "action": "find_projections"},
        {"label": "Find informative projections (z axis)…", "action": "find_z_projections"},
        None,
        {"label": "Axis Control", "action": "axis_control"},
        {"label": "Reset window layout", "action": "reset_layout"},
    ]),
    ("Help", [
        {"label": "Help", "action": "help"},
        None,
        {"label": "About", "action": "about"},
        {"label": "Update", "action": "update_app"},
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
                out.append(Menu(item[0], build(item[1])))
            else:
                row = MenuItem(item["label"], shortcut=item.get("shortcut", ""),
                               checkable=bool(item.get("checkable")),
                               checked=bool(item.get("checked") and checked(item["checked"])),
                               enabled=available(item["action"]))
                row.action = item["action"]
                out.append(row)
        return out

    return MenuBar([Menu(title, build(entries)) for title, entries in merged_menus(extra)])


def refresh(bar, available: Callable[[str], bool], checked: Callable[[str], bool]) -> None:
    """Bring each item's enabled/checked state up to date with the app."""
    from emtk.widgets.menus import Menu

    def walk(entries):
        for entry in entries:
            if isinstance(entry, Menu):
                walk(entry.entries)
            elif entry is not None:
                entry.enabled = available(entry.action)
                spec = _spec_for(entry.action)
                if spec and spec.get("checked"):
                    entry.checked = checked(spec["checked"])

    for menu in bar.menus:
        walk(menu.entries)


def _spec_for(action: str) -> Optional[Dict[str, Any]]:
    for _path, item in iter_entries():
        if item["action"] == action:
            return item
    return None
