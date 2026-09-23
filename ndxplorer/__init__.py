"""ndXplorer: multi-parameter fluorescence data exploration.

Nothing is imported with the package. The Qt window (:class:`NDXplorer`) and
its image item load on first use of their names, so reading data, the
analysis helpers and the emtk app (:mod:`ndxplorer.app`) run in a process
that has no Qt -- a batch job, a test, a browser.
"""

from __future__ import annotations


def __getattr__(name: str):
    if name == "NDXplorer":
        from .core.plot_main import NDXplorer

        return NDXplorer
    if name == "FixedImageItem":
        from .plotting.image_items import FixedImageItem

        return FixedImageItem
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["NDXplorer", "FixedImageItem"]
