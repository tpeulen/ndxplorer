"""File reading and writing.

``__all__`` names only what actually exists here. It used to name four symbols
that did not (``read_data``, ``write_data``, ``FileOperations``,
``open_file_dialog``), which turns ``from ndxplorer.io import *`` into an
AttributeError rather than the convenience it looks like.
"""

from __future__ import annotations

#: Read by ``__getattr__``; not imported with the package.
_SUBMODULES = ("reader", "writer")

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
