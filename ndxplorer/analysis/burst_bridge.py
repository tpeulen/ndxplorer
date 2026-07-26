"""Hand a gated ndXplorer sub-population off to a ChiSurf burst analysis.

Exploring a burst parameter space tells you *where* the populations are; it does
not, on its own, resolve a shot-noise distance distribution, a multi-exponential
donor decay, or a diffusion time. Those need the **photons back** — a full
ChiSurf fit on the selected bursts' photon stream, not a histogram of a derived
column.

This module is the handoff ("bridge"). A gate in the explorer is a set of
:class:`~ndxplorer.core.data_source.DataSelection` objects; ChiSurf's burst
readers all consume the *same* representation of a burst set — per-file
``(first_photon, last_photon)`` index intervals (the ``.bst`` shape). So the
whole bridge is one pure transform, :func:`selection_to_burst_slices`, plus a
thin dispatcher, :class:`BurstAnalysisBridge`, that marshals those intervals into
a ChiSurf RPC call:

* **FCS / burst correlation** — ``burst_fcs.correlate_file`` (one call per file).
* **PDA** — ``pda.from_bursts`` (one call; the experimental S1/S2 histogram).
* **Lifetime (MLE)** and any future burst analysis — a configurable method name.

Qt-free and headless-testable. The RPC client is any object exposing
``call(method, params) -> {"ok": bool, "result"|"error": ...}`` — ndXplorer holds
one as ``self.chisurf_rpc`` when launched with ``--chisurf-rpc`` (or the
in-process client the ChiSurf ndX plugin injects).
"""

from __future__ import annotations

from collections import OrderedDict
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np

#: Default burst-provenance column names in an MFD table.
FILE_COL = "First File"
LAST_FILE_COL = "Last File"
FIRST_PHOTON_COL = "First Photon"
LAST_PHOTON_COL = "Last Photon"

BurstSlices = "OrderedDict[str, List[Tuple[int, int]]]"


class BurstBridgeError(RuntimeError):
    """Raised when a bridge cannot resolve a selection or reach ChiSurf."""


def selection_to_burst_slices(
    data_source: Any,
    selections: Sequence[Any] = (),
    *,
    file_col: str = FILE_COL,
    last_file_col: str = LAST_FILE_COL,
    first_col: str = FIRST_PHOTON_COL,
    last_col: str = LAST_PHOTON_COL,
) -> "OrderedDict[str, List[Tuple[int, int]]]":
    """Resolve a gated ndXplorer selection to per-file photon intervals.

    Applies the combined selection mask, keeps only bursts wholly contained in a
    single file, and groups the survivors by file into ``(first, last)`` photon
    index pairs — the representation ChiSurf's burst readers consume.

    Parameters
    ----------
    data_source
        The ndXplorer :class:`~ndxplorer.core.data_source.DataSource` holding the
        burst table (``.data`` and ``.get_mask``).
    selections
        The active gates; an empty sequence means "keep every burst".
    file_col, last_file_col, first_col, last_col
        Column names for the burst provenance (first/last file, first/last
        photon index).

    Returns
    -------
    OrderedDict
        ``{tttr_path: [(first, last), ...]}`` in file order. Empty if nothing is
        selected.

    Raises
    ------
    BurstBridgeError
        If the required provenance columns are absent from the table.
    """
    df = data_source.data
    if df is None or df.empty:
        return OrderedDict()
    missing = [c for c in (file_col, last_file_col, first_col, last_col) if c not in df.columns]
    if missing:
        raise BurstBridgeError(
            f"burst table lacks provenance column(s) {missing}; "
            "the selection cannot be resolved to TTTR photon intervals"
        )

    if selections:
        mask = data_source.get_mask(selections=list(selections))
        excluded = np.asarray(mask).sum(axis=0).astype(bool)  # True → dropped
        keep = ~excluded
        dm = df.loc[keep]
    else:
        dm = df

    # A burst that straddles two files has no single TTTR source — drop it.
    dm = dm.loc[dm[file_col] == dm[last_file_col]]

    slices: "OrderedDict[str, List[Tuple[int, int]]]" = OrderedDict()
    for filename, group in dm.groupby(file_col, sort=False):
        firsts = group[first_col].to_numpy(dtype=np.int64, copy=False)
        lasts = group[last_col].to_numpy(dtype=np.int64, copy=False)
        slices[str(filename)] = [(int(a), int(b)) for a, b in zip(firsts, lasts)]
    return slices


class BurstAnalysisBridge:
    """Route a gated ndXplorer sub-population into a ChiSurf burst analysis.

    Build once with the injected RPC client and the data source; call one of the
    ``send_to_*`` methods with the current selections. Each resolves the gate to
    :func:`selection_to_burst_slices` and issues the matching ChiSurf RPC call.

    Parameters
    ----------
    rpc_client
        Any object with ``call(method, params) -> dict``; ``None`` marks the
        bridge unavailable (:meth:`available` is False and every ``send_to_*``
        raises). This is ndXplorer's ``self.chisurf_rpc``.
    data_source
        The ndXplorer data source holding the burst table.
    file_col, last_file_col, first_col, last_col
        Burst-provenance column names (see :func:`selection_to_burst_slices`).
    """

    def __init__(
        self,
        rpc_client: Any,
        data_source: Any,
        *,
        file_col: str = FILE_COL,
        last_file_col: str = LAST_FILE_COL,
        first_col: str = FIRST_PHOTON_COL,
        last_col: str = LAST_PHOTON_COL,
    ) -> None:
        self._rpc = rpc_client
        self._data_source = data_source
        self._cols = dict(
            file_col=file_col,
            last_file_col=last_file_col,
            first_col=first_col,
            last_col=last_col,
        )

    def available(self) -> bool:
        """True when an RPC client capable of ``call`` is attached."""
        return self._rpc is not None and callable(getattr(self._rpc, "call", None))

    def burst_slices(self, selections: Sequence[Any]) -> "OrderedDict[str, List[Tuple[int, int]]]":
        """Resolve *selections* to ``{file: [(first, last), ...]}`` (see the module docstring)."""
        return selection_to_burst_slices(self._data_source, selections, **self._cols)

    # -- dispatch helpers ---------------------------------------------------

    def _require_rpc(self) -> None:
        if not self.available():
            raise BurstBridgeError(
                "no ChiSurf RPC connection — launch ndXplorer with --chisurf-rpc "
                "host:port, or open it from ChiSurf, to use analysis bridges"
            )

    def _call(self, method: str, params: Dict[str, Any]) -> Any:
        """Call one RPC method, unwrapping ``{ok, result|error}`` or raising."""
        self._require_rpc()
        reply = self._rpc.call(method, params)
        if not isinstance(reply, Mapping):
            return reply
        if reply.get("ok", True):
            return reply.get("result", reply)
        raise BurstBridgeError(f"{method} failed: {reply.get('error')}")

    # -- targets ------------------------------------------------------------

    def send_to_correlator(
        self,
        selections: Sequence[Any],
        pairs: Sequence[Mapping[str, Any]],
        settings: Optional[Mapping[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Correlate the selected bursts (per file) via ``burst_fcs.correlate_file``.

        Parameters
        ----------
        selections
            The active gates.
        pairs
            Correlation channel-pair configurations (``PairConfig`` dicts).
        settings
            Optional ``BurstFcsSettings`` dict.

        Returns
        -------
        list of dict
            One entry per file: ``{"file": path, "curves": ...}``.
        """
        slices = self.burst_slices(selections)
        if not slices:
            raise BurstBridgeError("selection is empty — nothing to correlate")
        out: List[Dict[str, Any]] = []
        for path, ranges in slices.items():
            result = self._call(
                "burst_fcs.correlate_file",
                {
                    "tttr_path": path,
                    "ranges": [[a, b] for a, b in ranges],
                    "pairs": list(pairs),
                    "settings": dict(settings or {}),
                },
            )
            out.append({"file": path, "curves": result})
        return out

    def send_to_pda(
        self,
        selections: Sequence[Any],
        *,
        method: str = "pda.from_bursts",
        **params: Any,
    ) -> Any:
        """Build a PDA experimental histogram from the selected bursts.

        Sends the whole ``burst_slices`` mapping in one call. The default
        *method* wraps ChiSurf's PDA burst reader; extra keyword arguments
        (channel routing, micro-time gating, number of bins…) pass through.
        """
        slices = self.burst_slices(selections)
        if not slices:
            raise BurstBridgeError("selection is empty — no bursts for PDA")
        return self._call(
            method,
            {"burst_slices": {p: [[a, b] for a, b in r] for p, r in slices.items()}, **params},
        )

    def send_to(
        self,
        method: str,
        selections: Sequence[Any],
        *,
        per_file: bool = False,
        **params: Any,
    ) -> Any:
        """Generic dispatch to any ChiSurf burst RPC (e.g. lifetime MLE).

        With ``per_file=False`` (default) issues one call carrying the whole
        ``burst_slices`` mapping; with ``per_file=True`` issues one call per file
        carrying ``tttr_path`` + ``ranges`` and returns a list. Extra keyword
        arguments pass through to the RPC.
        """
        slices = self.burst_slices(selections)
        if not slices:
            raise BurstBridgeError("selection is empty — nothing to send")
        if per_file:
            return [
                {
                    "file": path,
                    "result": self._call(
                        method, {"tttr_path": path, "ranges": [[a, b] for a, b in ranges], **params}
                    ),
                }
                for path, ranges in slices.items()
            ]
        return self._call(
            method,
            {"burst_slices": {p: [[a, b] for a, b in r] for p, r in slices.items()}, **params},
        )


__all__ = [
    "BurstAnalysisBridge",
    "BurstBridgeError",
    "selection_to_burst_slices",
    "FILE_COL",
    "LAST_FILE_COL",
    "FIRST_PHOTON_COL",
    "LAST_PHOTON_COL",
]
