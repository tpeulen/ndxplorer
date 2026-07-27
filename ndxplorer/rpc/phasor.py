"""Typed facade over the ChiSurf ``phasor.*`` RPC methods (PRD-56).

Keeps ndXplorer call sites readable and mockable. Chisurf-free — it only speaks the
:class:`~ndxplorer.rpc.client.RpcClient` contract and marshals numpy arrays to/from
JSON-friendly lists.
"""

from __future__ import annotations

from typing import Any, Optional, Sequence

from .client import RpcClient, RpcError


def _as_list(a: Any) -> Any:
    """Convert numpy arrays (and array-likes) to nested lists for JSON transport."""
    if a is None:
        return None
    tolist = getattr(a, "tolist", None)
    return tolist() if callable(tolist) else a


class PhasorService:
    """Facade over ``phasor.*``. Each method raises :class:`RpcError` on a failed call."""

    def __init__(self, client: RpcClient) -> None:
        self._client = client

    # -- low level --------------------------------------------------------------------
    def _call(self, method: str, params: dict) -> dict:
        res = self._client.call(method, params) or {}
        if not res.get("ok", False):
            raise RpcError(res.get("error", f"{method} failed"))
        return res.get("result", {})

    # -- capabilities -----------------------------------------------------------------
    def describe(self) -> dict:
        """Server capabilities and defaults (frequency, harmonic, overlay sets, filters)."""
        return self._call("phasor.describe", {})

    # -- derived maps -----------------------------------------------------------------
    def apparent_lifetime(self, g, s, frequency_mhz: float) -> tuple[list, list]:
        """Return ``(tau_phi, tau_m)`` for the given ``g``, ``s`` at ``frequency_mhz``."""
        r = self._call(
            "phasor.apparent_lifetime",
            {"g": _as_list(g), "s": _as_list(s), "frequency_mhz": float(frequency_mhz)},
        )
        return r["tau_phi"], r["tau_m"]

    def filter(self, g, s, kind: str = "median", size: int = 3, repeat: int = 1, sigma: float = 1.0):
        """Return NaN-safe filtered ``(g, s)`` (``kind`` = ``"median"`` or ``"gaussian"``)."""
        r = self._call(
            "phasor.filter",
            {"g": _as_list(g), "s": _as_list(s), "kind": kind, "size": int(size),
             "repeat": int(repeat), "sigma": float(sigma)},
        )
        return r["g"], r["s"]

    def component_fraction(self, g, s, c1: Sequence[float], c2: Sequence[float]) -> list:
        """Fraction map of component 1 by projection onto the ``c1``–``c2`` line."""
        r = self._call(
            "phasor.component_fraction",
            {"g": _as_list(g), "s": _as_list(s), "c1": list(c1), "c2": list(c2)},
        )
        return r["fraction"]

    def unmix(self, g, s, components: Sequence[Sequence[float]]) -> list:
        """List of fraction maps for ``N >= 2`` component phasors (sum-to-one)."""
        r = self._call(
            "phasor.unmix",
            {"g": _as_list(g), "s": _as_list(s), "components": [list(c) for c in components]},
        )
        return r["fractions"]

    # -- cursors ----------------------------------------------------------------------
    def cursor_mask(
        self,
        g,
        s,
        center: Sequence[float],
        radius: float = 0.05,
        kind: str = "circular",
        radii: Optional[Sequence[float]] = None,
        angle: float = 0.0,
    ) -> dict:
        """Boolean mask (+ ``n_selected``) for a circular/elliptic phasor cursor."""
        params: dict[str, Any] = {
            "g": _as_list(g), "s": _as_list(s), "center": list(center),
            "kind": kind, "radius": float(radius), "angle": float(angle),
        }
        if radii is not None:
            params["radii"] = list(radii)
        return self._call("phasor.cursor_mask", params)

    def pseudo_color(self, masks, colors=None, intensity=None) -> dict:
        """RGB label image (+ ``shape``) from a stack of boolean masks."""
        return self._call(
            "phasor.pseudo_color",
            {"masks": [_as_list(m) for m in masks], "colors": colors, "intensity": _as_list(intensity)},
        )

    # -- reference geometry -----------------------------------------------------------
    def overlays(
        self,
        frequency_mhz: float,
        sets: Optional[Sequence[str]] = None,
        taus: Optional[Sequence[float]] = None,
        harmonic: int = 1,
        c1: Optional[Sequence[float]] = None,
        c2: Optional[Sequence[float]] = None,
        tau_d0: float = 4.0,
        e_range: Optional[Sequence[float]] = None,
    ) -> list[dict]:
        """Return reference-geometry polylines as ``[{name, kind, x, y, style}, ...]``."""
        params: dict[str, Any] = {"frequency_mhz": float(frequency_mhz), "harmonic": int(harmonic)}
        if sets is not None:
            params["sets"] = list(sets)
        if taus is not None:
            params["taus"] = list(taus)
        if c1 is not None:
            params["c1"] = list(c1)
        if c2 is not None:
            params["c2"] = list(c2)
        if e_range is not None:
            params["e_range"] = list(e_range)
        params["tau_d0"] = float(tau_d0)
        return self._call("phasor.overlays", params)["overlays"]
