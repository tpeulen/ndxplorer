"""ndXplorer ↔ ChiSurf RPC subsystem (PRD-56).

A first-class, chisurf-free RPC client so ndXplorer can borrow ChiSurf's domain math
(phasor analysis, …) over JSON-RPC. It depends only on ``pyzmq`` + the stdlib and
*defines* the transport contract — it never imports chisurf.

Two ways to obtain a client:

- **Injected** — the in-process ChiSurf GUI passes any object satisfying
  :class:`RpcClient` (e.g. ChiSurf's ``InProcessClient``) to
  ``NDXplorer(chisurf_rpc=...)``; no socket hop.
- **Own transport** — headless/external callers use :class:`ZmqRpcClient` (or
  :func:`connect` / :func:`client_from_config`), pointing at a loopback ChiSurf server.

The :class:`~ndxplorer.rpc.phasor.PhasorService` facade wraps the ``phasor.*`` methods.
"""

from __future__ import annotations

from .client import (
    DEFAULT_CMD_PORT,
    DEFAULT_HOST,
    RpcClient,
    RpcError,
    ZmqRpcClient,
    client_from_config,
    connect,
    parse_endpoint,
)
from .lines import FretLines, LinesService, OverlayProvider, PhasorLines
from .phasor import PhasorService

__all__ = [
    "RpcClient",
    "RpcError",
    "ZmqRpcClient",
    "PhasorService",
    "LinesService",
    "OverlayProvider",
    "PhasorLines",
    "FretLines",
    "connect",
    "client_from_config",
    "parse_endpoint",
    "DEFAULT_HOST",
    "DEFAULT_CMD_PORT",
]
