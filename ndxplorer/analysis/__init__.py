"""Analysis. Submodules load on first use; see ``__getattr__``."""

from __future__ import annotations

_SUBMODULES = (
    "clustering", "clustering_helpers", "gaussian_fit", "umap_helpers", "umap_progress",
)

__all__ = [
    'ClusteringManager',
    'ClusteringWorker',
    'UMAPProgressDialog'
]


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
