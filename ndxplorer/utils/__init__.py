"""Utility helpers. Submodules load on first use; see ``__getattr__``."""

from __future__ import annotations

_SUBMODULES = (
    "axis_helpers", "histogram_helpers", "histogram_export", "lazy_imports",
    "performance_optimizations",
)

__all__: list[str] = []


def __getattr__(name: str):
    """Resolve a name on first use: a submodule, or a name one of them defines.

    Nothing is imported with the package, so importing it costs nothing.
    """
    import importlib
    import importlib.util

    if name.startswith("__"):
        raise AttributeError(name)
    if importlib.util.find_spec(f"{__name__}.{name}") is not None:
        return importlib.import_module(f"{__name__}.{name}")
    for module in _SUBMODULES:
        loaded = importlib.import_module(f"{__name__}.{module}")
        if hasattr(loaded, name):
            value = getattr(loaded, name)
            globals()[name] = value
            return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
