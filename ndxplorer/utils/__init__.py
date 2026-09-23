"""Utility helpers. Submodules load on first use; see ``__getattr__``."""

from __future__ import annotations

_SUBMODULES = (
    "axis_helpers", "histogram_helpers", "histogram_export", "napari_helpers",
    "screenshot_helpers", "ui_helpers", "working_path_helpers", "lazy_imports",
    "performance_optimizations", "mouse_event_filter", "colormap_helpers",
)

__all__ = ["MouseEventFilter"]


def __getattr__(name: str):
    """Resolve a name on first use: a submodule, or a name one of them defines.

    Nothing is imported with the package: several submodules build Qt
    widgets, and importing one of those to reach a Qt-free helper put Qt into
    every process that read a file -- the emtk app, a batch script, a browser.
    """
    import importlib
    import importlib.util

    if name.startswith("__"):
        raise AttributeError(name)
    if name == "settings_helpers":
        # The package-level module, which this package has long re-exported.
        return importlib.import_module("ndxplorer.settings_helpers")
    if importlib.util.find_spec(f"{__name__}.{name}") is not None:
        return importlib.import_module(f"{__name__}.{name}")
    for module in _SUBMODULES:
        loaded = importlib.import_module(f"{__name__}.{module}")
        if hasattr(loaded, name):
            value = getattr(loaded, name)
            globals()[name] = value
            return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
