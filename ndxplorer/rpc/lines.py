"""Unified overlay-lines interface for ndXplorer (PRD-56).

ChiSurf exposes several *line* providers that all return the same **LineSet** shape
— a list of ``{"name", "kind", "x", "y", "style", ...}`` polylines/markers:

- ``phasor.overlays`` — semicircle, iso-lifetime grid/ticks, FRET trajectory, mixing line
- ``fret_line.overlays`` — static/dynamic/WLC/mixture FRET lines for smFRET histograms

:class:`OverlayProvider` is the shared client-side interface; :class:`PhasorLines` and
:class:`FretLines` are the two providers, so ndXplorer draws phasor lines and FRET
lines through one uniform path (its ``CurveOverlayWidget``). Chisurf-free: only the
:class:`~ndxplorer.rpc.client.RpcClient` contract.
"""

from __future__ import annotations

from typing import Any

from .client import RpcClient, RpcError


class OverlayProvider:
    """Base client for any ChiSurf ``*.overlays`` method returning a LineSet.

    Subclasses set :attr:`method`; :meth:`overlays` forwards keyword params and returns
    the ``overlays`` list. Raises :class:`RpcError` on a failed call.
    """

    #: The RPC method name (e.g. ``"phasor.overlays"``).
    method: str = ""

    def __init__(self, client: RpcClient) -> None:
        self._client = client

    def overlays(self, **params: Any) -> list[dict]:
        """Return the provider's overlay LineSet for the given parameters."""
        if not self.method:
            raise NotImplementedError("OverlayProvider subclasses must set `method`")
        res = self._client.call(self.method, params) or {}
        if not res.get("ok", False):
            raise RpcError(res.get("error", f"{self.method} failed"))
        return res.get("result", {}).get("overlays", [])


class PhasorLines(OverlayProvider):
    """Phasor reference geometry (``phasor.overlays``)."""

    method = "phasor.overlays"


class FretLines(OverlayProvider):
    """FRET lines for smFRET histograms (``fret_line.overlays``)."""

    method = "fret_line.overlays"

    def _result(self, method: str, params: dict) -> Any:
        res = self._client.call(method, params) or {}
        if not res.get("ok", False):
            raise RpcError(res.get("error", f"{method} failed"))
        return res.get("result", {})

    def list_models(self) -> list[str]:
        """Return the display names of the available FRET component models."""
        return list(self._result("fret_line.list_models", {}) or [])

    def list_sweep_targets(self, components: list[dict]) -> list[dict]:
        """Return the sweepable parameters ``[{name, ...}]`` for *components*."""
        res = self._result("fret_line.list_sweep_targets", {"components": components})
        return list(res.get("targets", res) if isinstance(res, dict) else res)

    def list_projections(self) -> list[str]:
        """Return the available line projections (axis pairs) for FRET lines."""
        res = self._result("fret_line.list_projections", {})
        return list(res.get("projections", []) if isinstance(res, dict) else res)


class LinesService:
    """Aggregate facade exposing every overlay-line provider off one RPC client."""

    def __init__(self, client: RpcClient) -> None:
        self._client = client
        self.phasor = PhasorLines(client)
        self.fret_line = FretLines(client)

    def providers(self) -> dict[str, OverlayProvider]:
        """Return provider name → provider, for generic UI enumeration."""
        return {"phasor": self.phasor, "fret_line": self.fret_line}
