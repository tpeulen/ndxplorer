"""Analysis. Submodules load on first use."""

from __future__ import annotations

__all__: list[str] = []


def __getattr__(name: str):
    """A submodule, imported on first use of its name."""
    import importlib
    import importlib.util

    if not name.startswith("__") and importlib.util.find_spec(f"{__name__}.{name}") is not None:
        return importlib.import_module(f"{__name__}.{name}")
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
