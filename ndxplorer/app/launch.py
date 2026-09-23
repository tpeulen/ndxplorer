"""Put the emtk app in a window: ``python -m ndxplorer --emtk [--file PATH]``.

The app itself (:class:`~ndxplorer.app.frame.NdxApp`) is a control and knows
no window. This picks one:

``native``
    :class:`emtk.native.NativeHost` -- rendercanvas + wgpu + glfw, no toolkit.
    The default when those are installed.
``tk``
    :class:`emtk.tk_host.TkHost` -- the standard library's Tk window, drawn by
    Pillow. Slower, but needs nothing that is not already there.

A browser runs the same app through ``python -m emtk.web.serve --app
ndxplorer.app.frame:make_app``. No Qt is imported on any of these paths.
"""

from __future__ import annotations

import importlib.util
from typing import Optional

__all__ = ["run", "available_host"]

#: The window size the Qt window opens at in the parity scenarios.
SIZE = (1400, 900)
TITLE = "ndX"


def available_host() -> str:
    """``"native"`` when wgpu, rendercanvas and glfw are installed, else ``"tk"``."""
    if all(importlib.util.find_spec(name) is not None for name in ("wgpu", "rendercanvas", "glfw")):
        return "native"
    return "tk"


def run(path: Optional[str] = None, host: Optional[str] = None,
        chisurf_rpc: Optional[str] = None) -> int:
    """Open the app, optionally with *path* loaded, and run until the window closes.

    *chisurf_rpc* is ``host:port`` of a ChiSurf RPC server (``--chisurf-rpc``):
    the connection "Send selection to" and the phasor features use. A desktop
    option -- a browser page has no socket to open.
    """
    import logging

    from .frame import NdxApp
    from . import theme

    host = host or available_host()
    app = NdxApp()
    if chisurf_rpc:
        from ..rpc import connect

        app.chisurf_rpc = connect(chisurf_rpc, require=False)
        if app.chisurf_rpc is None:
            logging.warning("No ChiSurf RPC server at %s; ChiSurf features disabled",
                            chisurf_rpc)
    if path:
        app.open_path(str(path))
    try:
        if host == "native":
            from emtk.native import NativeHost

            window = NativeHost(app, size=SIZE, title=TITLE)
            app.on_exit = window.close
            window.run()
        else:
            from emtk.tk_host import TkHost

            window = TkHost(app, title=TITLE, size=SIZE, background=theme.WINDOW_BG)
            app.on_exit = window.close
            window.run()
    finally:
        app.close()
    return 0
