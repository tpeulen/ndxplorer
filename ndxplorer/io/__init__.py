"""File reading and writing.

``__all__`` names only what actually exists here. It used to name four symbols
that did not (``read_data``, ``write_data``, ``FileOperations``,
``open_file_dialog``), which turns ``from ndxplorer.io import *`` into an
AttributeError rather than the convenience it looks like.
"""

from __future__ import annotations

#: Read by ``__getattr__``. Not imported with the package: two of them raise
#: Qt file dialogs, and reading a file must not need Qt.
_SUBMODULES = ("reader", "writer", "file_operations", "file_open_helpers")

#: Nothing is re-exported: the two names that used to be here,
#: ``save_burst_ids`` and ``save_clustering_data``, are GUI actions -- they
#: take the main window and raise file dialogs -- and live in
#: :mod:`ndxplorer.ui.export_actions`. Their headless counterparts are in
#: :mod:`ndxplorer.io.writer`.
__all__: list[str] = []


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
    if importlib.util.find_spec(f"{__name__}.{name}") is not None:
        return importlib.import_module(f"{__name__}.{name}")
    for module in _SUBMODULES:
        loaded = importlib.import_module(f"{__name__}.{module}")
        if hasattr(loaded, name):
            value = getattr(loaded, name)
            globals()[name] = value
            return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
