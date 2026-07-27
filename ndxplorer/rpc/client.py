"""Transport-level RPC client for talking to a ChiSurf JSON-RPC server (PRD-56).

Chisurf-free: only ``pyzmq`` + stdlib. Defines the :class:`RpcClient` contract shared
with ChiSurf's own ``InProcessClient`` / ``ChisurfClient`` (all expose
``call(method, params) -> dict`` returning the *service result* dict,
``{"ok": bool, "result": ...}`` or ``{"ok": False, "error": ...}``).
"""

from __future__ import annotations

import logging
import os
from typing import Any, Optional, Protocol, runtime_checkable

logger = logging.getLogger(__name__)

DEFAULT_HOST = "127.0.0.1"
DEFAULT_CMD_PORT = 8765
DEFAULT_TIMEOUT_MS = 5000
#: Environment variable read by :func:`client_from_config` when no explicit endpoint
#: is given (e.g. ``CHISURF_RPC=127.0.0.1:8765``).
ENV_VAR = "CHISURF_RPC"


class RpcError(RuntimeError):
    """A remote call failed (transport error, timeout, or ``ok: False`` result)."""


@runtime_checkable
class RpcClient(Protocol):
    """Anything that can dispatch a ChiSurf RPC call.

    Satisfied by :class:`ZmqRpcClient` and by ChiSurf's in-process client, so the GUI
    can inject the latter with no socket hop.
    """

    def call(self, method: str, params: Optional[dict] = None) -> dict:  # pragma: no cover - protocol
        ...


def parse_endpoint(endpoint: str) -> tuple[str, int]:
    """Parse ``"host:port"`` / ``":port"`` / ``"port"`` into ``(host, port)``.

    Missing host defaults to :data:`DEFAULT_HOST`, missing port to
    :data:`DEFAULT_CMD_PORT`.
    """
    endpoint = str(endpoint).strip()
    if not endpoint:
        return DEFAULT_HOST, DEFAULT_CMD_PORT
    if ":" in endpoint:
        host, _, port = endpoint.rpartition(":")
        host = host.strip() or DEFAULT_HOST
        return host, int(port) if port.strip() else DEFAULT_CMD_PORT
    # bare token: a port if numeric, otherwise a host
    if endpoint.isdigit():
        return DEFAULT_HOST, int(endpoint)
    return endpoint, DEFAULT_CMD_PORT


class ZmqRpcClient:
    """JSON-RPC 2.0 over a ZeroMQ ``REQ`` socket, with timeout + reconnect.

    A lazily-connected client: the socket is (re)created on first use and reset after a
    timeout (a strict ``REQ`` socket cannot be reused after a missed reply). All calls
    return the *service result* dict; transport failures raise :class:`RpcError`.
    """

    def __init__(
        self,
        host: str = DEFAULT_HOST,
        cmd_port: int = DEFAULT_CMD_PORT,
        timeout_ms: int = DEFAULT_TIMEOUT_MS,
    ) -> None:
        self.host = host
        self.cmd_port = int(cmd_port)
        self.timeout_ms = int(timeout_ms)
        self._ctx = None
        self._socket = None
        self._request_id = 0

    # -- connection lifecycle ---------------------------------------------------------
    def _ensure_socket(self) -> None:
        if self._socket is not None:
            return
        import zmq

        if self._ctx is None:
            self._ctx = zmq.Context.instance()
        socket = self._ctx.socket(zmq.REQ)
        socket.setsockopt(zmq.LINGER, 0)
        socket.connect(f"tcp://{self.host}:{self.cmd_port}")
        self._socket = socket

    def _reset_socket(self) -> None:
        if self._socket is not None:
            try:
                self._socket.close(0)
            except Exception:  # pragma: no cover - best effort
                pass
        self._socket = None

    def close(self) -> None:
        """Close the underlying socket (safe to call repeatedly)."""
        self._reset_socket()

    # -- calls ------------------------------------------------------------------------
    def call(self, method: str, params: Optional[dict] = None) -> dict:
        """Send a JSON-RPC request and return the unwrapped service-result dict."""
        import zmq

        self._ensure_socket()
        self._request_id += 1
        msg = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params or {},
            "id": self._request_id,
        }
        try:
            self._socket.send_json(msg)
        except Exception as exc:  # socket wedged — reset and surface
            self._reset_socket()
            raise RpcError(f"failed to send {method!r}: {exc}") from exc

        poller = zmq.Poller()
        poller.register(self._socket, zmq.POLLIN)
        if dict(poller.poll(self.timeout_ms)).get(self._socket) != zmq.POLLIN:
            self._reset_socket()
            raise RpcError(f"timeout: no response to {method!r} within {self.timeout_ms} ms")

        envelope = self._socket.recv_json()
        if isinstance(envelope, dict) and "error" in envelope and "result" not in envelope:
            err = envelope["error"]
            message = err.get("message", str(err)) if isinstance(err, dict) else str(err)
            return {"ok": False, "error": message}
        # JSON-RPC envelope -> the service result dict lives under "result".
        result = envelope.get("result", envelope) if isinstance(envelope, dict) else envelope
        return result if isinstance(result, dict) else {"ok": True, "result": result}

    def health(self) -> bool:
        """Best-effort connectivity probe; ``True`` if the server answers."""
        try:
            res = self.call("list_methods", {})
            return bool(res)
        except Exception:
            return False


def connect(
    endpoint: str | None = None,
    *,
    host: str | None = None,
    cmd_port: int | None = None,
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
    require: bool = False,
) -> Optional[ZmqRpcClient]:
    """Create a :class:`ZmqRpcClient`, degrading gracefully when no server is reachable.

    Parameters
    ----------
    endpoint : str, optional
        ``"host:port"`` string; overrides ``host``/``cmd_port`` when given.
    host, cmd_port : optional
        Explicit host/port (used when ``endpoint`` is not given).
    timeout_ms : int
        Per-call timeout.
    require : bool
        If ``True``, raise :class:`RpcError` when the server does not answer; otherwise
        return ``None`` (ndXplorer then runs exactly as it does with no ChiSurf).
    """
    if endpoint:
        host, cmd_port = parse_endpoint(endpoint)
    client = ZmqRpcClient(
        host=host or DEFAULT_HOST,
        cmd_port=cmd_port or DEFAULT_CMD_PORT,
        timeout_ms=timeout_ms,
    )
    if client.health():
        logger.info("Connected to ChiSurf RPC at %s:%s", client.host, client.cmd_port)
        return client
    client.close()
    msg = f"no ChiSurf RPC server at {client.host}:{client.cmd_port}"
    if require:
        raise RpcError(msg)
    logger.warning("%s — ndXplorer phasor features disabled", msg)
    return None


def client_from_config(
    endpoint: str | None = None,
    *,
    require: bool = False,
    timeout_ms: int = DEFAULT_TIMEOUT_MS,
) -> Optional[ZmqRpcClient]:
    """Resolve an endpoint from ``endpoint`` or the :data:`ENV_VAR` env var, then connect."""
    endpoint = endpoint or os.environ.get(ENV_VAR)
    if not endpoint:
        return None
    return connect(endpoint, require=require, timeout_ms=timeout_ms)
