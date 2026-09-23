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

**What a gate can be sent to is not decided here.** ndXplorer does not know, and
must not know, that a method called ``pda.from_bursts`` exists: it asks ChiSurf
what consumes bursts (``bursts.consumers``) and renders what it is told. Each
advertised consumer carries its own label, RPC name, call shape, default
parameters, provenance vocabulary and — where the analysis does not simply mean
what it appears to mean — a caveat to show the user.

That inversion is what keeps the two sides independent. A new burst analysis,
including one living in a ChiSurf plugin that declares ``burst_consumers`` in its
manifest, appears in this menu with no ndXplorer release. Conversely an older
ChiSurf that advertises three analyses gets a three-entry menu rather than a
menu with a dead fourth entry.

:meth:`BurstAnalysisBridge.send_to` remains open to any other burst RPC.

**Every handoff is recorded.** A gated population is a scientific claim about a
subset of the data — "these bursts are the high-FRET species" — and a decay or a
correlation curve computed from it is meaningless without the gate that produced
it. So each send writes an operation to the metadata store, linking the input
product to the output artifact and carrying the gate definition and the analysis
settings, via :meth:`BurstAnalysisBridge.record_operation`. Recording never
breaks a send: an unreachable store is logged and reported in the return value,
because losing the provenance is bad and losing the analysis is worse.

Qt-free and headless-testable. The RPC client is any object exposing
``call(method, params) -> {"ok": bool, "result"|"error": ...}`` — ndXplorer holds
one as ``self.chisurf_rpc`` when launched with ``--chisurf-rpc`` (or the
in-process client the ChiSurf ndX plugin injects).
"""

from __future__ import annotations

from collections import OrderedDict
from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

import numpy as np

from ..logging_config import logging

#: Default burst-provenance column names in an MFD table.
FILE_COL = "First File"
LAST_FILE_COL = "Last File"
FIRST_PHOTON_COL = "First Photon"
LAST_PHOTON_COL = "Last Photon"

BurstSlices = "OrderedDict[str, List[Tuple[int, int]]]"


@dataclass(frozen=True)
class Target:
    """One analysis a gated burst population can be handed to.

    Built from what ChiSurf advertises, never hard-coded here — see
    :meth:`BurstAnalysisBridge.discover`. One object drives the menu entry, the
    dispatch and the provenance record, so the three cannot disagree.

    Attributes
    ----------
    key : str
        Stable identifier used by the UI and by :meth:`BurstAnalysisBridge.send`.
    title : str
        Menu label.
    rpc : str
        ChiSurf RPC method name.
    summary : str
        One line on what comes back, for the menu's tooltip.
    operation_type, product_type : str
        Metadata-store vocabulary terms for the recorded operation and the
        artifact it produces. Both come from the mmCIF dictionary, which is the
        schema authority -- a term that is not in it will be rejected on write.
    per_file : bool
        ``True`` issues one call per file with ``tttr_path`` + ``ranges``;
        ``False`` sends the whole ``burst_slices`` mapping in one call.
    defaults : dict
        Parameters sent when the caller supplies none.
    caveat : str, optional
        A qualification the user must see before trusting the result — PCH from
        bursts is the motivating case. Advertised by the analysis itself,
        because only it knows when its own answer needs one.
    """

    key: str
    title: str
    rpc: str
    summary: str = ""
    operation_type: str = "analysis"
    product_type: str = "analysis_result"
    per_file: bool = False
    defaults: Optional[Dict[str, Any]] = None
    caveat: Optional[str] = None

    @classmethod
    def from_dict(cls, entry: Mapping[str, Any]) -> "Target":
        """Build a target from one advertised consumer.

        Unknown fields are ignored rather than raising: a newer ChiSurf may
        advertise things this client has no use for yet, and refusing the whole
        menu over one unrecognised key would be the worst possible trade.
        """
        return cls(
            key=str(entry["key"]),
            title=str(entry.get("title") or entry["key"]),
            rpc=str(entry["rpc"]),
            summary=str(entry.get("summary") or ""),
            operation_type=str(entry.get("operation_type") or "analysis"),
            product_type=str(entry.get("product_type") or "analysis_result"),
            per_file=bool(entry.get("per_file", False)),
            defaults=dict(entry.get("defaults") or {}),
            caveat=entry.get("caveat") or None,
        )


#: RPC that asks ChiSurf what consumes bursts.
CONSUMERS_RPC = "bursts.consumers"


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
        burst table.
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
    if data_source is None or data_source.empty:
        return OrderedDict()
    names = data_source.parameter_names
    missing = [c for c in (file_col, last_file_col, first_col, last_col) if c not in names]
    if missing:
        raise BurstBridgeError(
            f"burst table lacks provenance column(s) {missing}; "
            "the selection cannot be resolved to TTTR photon intervals"
        )

    if selections:
        keep = data_source.selection_mask(list(selections))
    else:
        keep = np.ones(data_source.size, dtype=bool)

    first_files = data_source.column_items(names.index(file_col))
    last_files = data_source.column_items(names.index(last_file_col))
    # A burst that straddles two files has no single TTTR source — drop it.
    keep &= first_files == last_files

    rows = np.flatnonzero(keep)
    firsts = np.asarray(data_source.column_items(names.index(first_col))[rows], dtype=np.int64)
    lasts = np.asarray(data_source.column_items(names.index(last_col))[rows], dtype=np.int64)
    slices: "OrderedDict[str, List[Tuple[int, int]]]" = OrderedDict()
    for filename, a, b in zip(first_files[rows], firsts, lasts):
        slices.setdefault(str(filename), []).append((int(a), int(b)))
    return slices



def _software_version() -> str:
    """ndXplorer's version, or ``"unknown"`` when it cannot be determined."""
    try:
        from ndxplorer import __version__

        return str(__version__)
    except Exception:
        return "unknown"


def describe_selections(selections: Sequence[Any]) -> List[Dict[str, Any]]:
    """Render the gates as plain JSON, for storing beside a derived analysis.

    A decay or a correlation curve computed from a sub-population cannot be
    interpreted without knowing which sub-population, so the gate is recorded
    with it. Selection classes differ (interval, rectangle, 2-D Gaussian, bitmap
    mask) and not all are describable by bounds, so this reads whatever
    attributes each carries rather than assuming one shape -- an unrecognised
    selection still records its type and name instead of vanishing.
    """
    described: List[Dict[str, Any]] = []
    for selection in selections or ():
        entry: Dict[str, Any] = {
            "type": type(selection).__name__,
            "name": getattr(selection, "name", None),
            "enabled": bool(getattr(selection, "enabled", True)),
        }
        for attribute in (
            "parameter_idx", "lower", "upper", "invert",
            "p1", "p2", "x_min", "x_max", "y_min", "y_max", "selection_id",
        ):
            if hasattr(selection, attribute):
                value = getattr(selection, attribute)
                if isinstance(value, (bool, int, float, str)) or value is None:
                    entry[attribute] = value
                else:
                    entry[attribute] = str(value)
        described.append(entry)
    return described


def summarise_result(spec: "Target", result: Any) -> Dict[str, Any]:
    """Describe what came back, small enough to embed in a provenance record.

    The store indexes provenance; it is not a results archive. A PDA S1/S2
    histogram or a set of correlation curves can be megabytes, and embedding
    them would make every provenance query drag the data with it. What is kept
    is the shape of the answer -- enough to confirm the operation produced what
    it claims and to recognise it later.
    """
    summary: Dict[str, Any] = {"analysis": spec.key, "rpc": spec.rpc}
    if isinstance(result, Mapping):
        for key in (
            "n_files", "n_photons", "n_bins", "mode", "bin_time_us",
            "burst_duty_cycle", "selection_bias", "coarsening",
        ):
            if key in result:
                summary[key] = result[key]
        if isinstance(result.get("decays"), list):
            summary["decays"] = [
                {"name": d.get("name"), "n_photons": d.get("n_photons"),
                 "n_bins": len(d.get("counts", []))}
                for d in result["decays"]
            ]
        if isinstance(result.get("curves"), list):
            summary["curves"] = [
                {"name": c.get("name"), "shape": c.get("shape"),
                 "n_photons": c.get("n_photons")}
                for c in result["curves"]
            ]
    elif isinstance(result, list):
        summary["n_files"] = len(result)
        summary["files"] = [
            r.get("file") for r in result if isinstance(r, Mapping)
        ]
    return summary


class BurstAnalysisBridge:
    """Route a gated ndXplorer sub-population into a ChiSurf burst analysis.

    Build once with the injected RPC client and the data source; call one of the
    ``send_to_*`` methods with the current selections. Each resolves the gate to
    :func:`selection_to_burst_slices` and issues the matching ChiSurf RPC call.

    Parameters
    ----------
    rpc_client
        Any object with ``call(method, params) -> dict``; ``None`` marks the
        bridge unavailable (:meth:`available` is False and every send raises).
        This is ndXplorer's ``self.chisurf_rpc``.
    data_source
        The ndXplorer data source holding the burst table.
    owner
        The explorer window, read only for the identifiers provenance needs
        (``processed_data_id``, ``experiment_id``). ``None`` disables recording
        rather than failing -- a bridge driven from a script has no product to
        attribute the operation to.
    file_col, last_file_col, first_col, last_col
        Burst-provenance column names (see :func:`selection_to_burst_slices`).
    """

    def __init__(
        self,
        rpc_client: Any,
        data_source: Any,
        *,
        owner: Any = None,
        file_col: str = FILE_COL,
        last_file_col: str = LAST_FILE_COL,
        first_col: str = FIRST_PHOTON_COL,
        last_col: str = LAST_PHOTON_COL,
    ) -> None:
        self._rpc = rpc_client
        self._data_source = data_source
        self._owner = owner
        self._targets: Optional["OrderedDict[str, Target]"] = None
        self._cols = dict(
            file_col=file_col,
            last_file_col=last_file_col,
            first_col=first_col,
            last_col=last_col,
        )

    def discover(self, refresh: bool = False) -> "OrderedDict[str, Target]":
        """Ask ChiSurf which analyses consume bursts.

        The answer is what the menu is built from, so this is the only place
        that decides what a gate can be sent to. Cached for the session: the
        advertised set changes when ChiSurf changes, not while the user works.

        Parameters
        ----------
        refresh : bool
            Re-ask even if the answer is already cached.

        Returns
        -------
        OrderedDict
            ``{key: Target}`` in the order ChiSurf advertised them. Empty when
            no client is attached or the call failed — an empty menu that says
            why is the honest outcome, and better than a menu of guesses that
            may not exist on the other side.
        """
        if self._targets is not None and not refresh:
            return self._targets

        targets: "OrderedDict[str, Target]" = OrderedDict()
        if self.available():
            try:
                reply = self._call(CONSUMERS_RPC, {})
                for entry in (reply or {}).get("consumers", []):
                    try:
                        target = Target.from_dict(entry)
                    except (KeyError, TypeError, ValueError) as exc:
                        logging.warning("ignoring a malformed consumer %r: %s", entry, exc)
                        continue
                    targets[target.key] = target
            except BurstBridgeError as exc:
                # An older ChiSurf without the advertisement RPC: no menu rather
                # than a menu of methods that may not be there.
                logging.info("ChiSurf advertises no burst consumers: %s", exc)
        self._targets = targets
        return targets

    def target(self, key: str) -> "Target":
        """Return one advertised target, or raise with what is on offer."""
        targets = self.discover()
        if key not in targets:
            raise BurstBridgeError(
                f"ChiSurf does not advertise a burst consumer named {key!r}; "
                f"it offers {sorted(targets) or 'none'}"
            )
        return targets[key]

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
                "no ChiSurf RPC connection — launch ndX with --chisurf-rpc "
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

    def send(
        self,
        target: str,
        selections: Sequence[Any],
        *,
        record: bool = True,
        **params: Any,
    ) -> Dict[str, Any]:
        """Hand the gated bursts to an advertised consumer and record it.

        Parameters
        ----------
        target : str
            A key ChiSurf advertised — see :meth:`discover`.
        selections : sequence
            The active gates.
        record : bool
            Write the operation to the metadata store. Recording failures never
            fail the send; they are reported in ``provenance``.
        **params
            Overrides for the target's defaults, passed to the RPC.

        Returns
        -------
        dict
            ``{"target", "result", "n_files", "n_bursts", "provenance"}``.
            ``provenance`` is the store's reply, ``None`` when *record* is false
            or no store is attached, or ``{"ok": False, "error": ...}`` when the
            write failed.
        """
        # Before anything else: with no connection there is nothing to discover
        # and nothing to send to, and "connect ChiSurf" is the actionable
        # message rather than "nothing is advertised".
        self._require_rpc()
        spec = self.target(target)
        slices = self.burst_slices(selections)
        if not slices:
            raise BurstBridgeError(
                f"selection is empty — no bursts to send to {spec.title}"
            )

        call_params = dict(spec.defaults or {})
        call_params.update(params)

        if spec.per_file:
            result: Any = [
                {
                    "file": path,
                    "result": self._call(
                        spec.rpc,
                        {
                            "tttr_path": path,
                            "ranges": [[a, b] for a, b in ranges],
                            **call_params,
                        },
                    ),
                }
                for path, ranges in slices.items()
            ]
        else:
            result = self._call(
                spec.rpc,
                {
                    "burst_slices": {
                        p: [[a, b] for a, b in r] for p, r in slices.items()
                    },
                    **call_params,
                },
            )

        n_bursts = sum(len(r) for r in slices.values())
        out: Dict[str, Any] = {
            "target": spec.key,
            "result": result,
            "n_files": len(slices),
            "n_bursts": n_bursts,
            "provenance": None,
        }
        if record:
            out["provenance"] = self.record_operation(
                spec, selections, slices, call_params, result
            )
        return out

    def record_operation(
        self,
        spec: "Target",
        selections: Sequence[Any],
        slices: Mapping[str, Sequence[Tuple[int, int]]],
        params: Mapping[str, Any],
        result: Any,
    ) -> Optional[Dict[str, Any]]:
        """Write the handoff to the metadata store as an operation + artifact.

        A decay computed from a gated population is uninterpretable without the
        gate, so the gate travels with it: the recorded settings carry each
        selection's parameters and bounds, the per-file burst counts, and the
        analysis parameters actually used.

        The result payload itself is **not** embedded — a PDA histogram or a
        correlation curve set is large, and the store is a provenance index, not
        a results archive. What is stored is enough to find and re-derive it:
        which files, which bursts, which settings.

        Returns
        -------
        dict or None
            The store's reply, ``None`` when no store is attached, or a
            ``{"ok": False, "error": ...}`` dict when the write failed. Never
            raises: losing provenance must not lose the analysis.
        """
        client = self._rpc
        product_id = getattr(self._owner, "processed_data_id", None)
        if client is None or product_id is None:
            return None

        try:
            payload = {
                "experiment_id": getattr(self._owner, "experiment_id", None) or "exp_1",
                "input_processed_data_ids": [product_id],
                "analysis_type": spec.key,
                "settings": {
                    "operation_type": spec.operation_type,
                    "rpc": spec.rpc,
                    "parameters": dict(params),
                    "gate": describe_selections(selections),
                    "bursts_per_file": {p: len(r) for p, r in slices.items()},
                    "n_bursts": sum(len(r) for r in slices.values()),
                },
                "products": [
                    {
                        "product_type": spec.product_type,
                        "storage_mode": "embedded_json",
                        "data": summarise_result(spec, result),
                        "validation_status": "valid",
                    }
                ],
                "software_version": _software_version(),
            }
            reply = client.call("ndxplorer.record_analysis", payload)
            if isinstance(reply, Mapping) and not (
                reply.get("ok") or (isinstance(reply.get("result"), Mapping)
                                    and reply["result"].get("ok"))
            ):
                logging.error("provenance write refused: %s", reply.get("error"))
                return {"ok": False, "error": reply.get("error")}
            return reply
        except Exception as exc:
            # Deliberately swallowed: the analysis succeeded, and failing it now
            # would discard a completed computation over a bookkeeping problem.
            logging.error("could not record the %s handoff: %s", spec.key, exc)
            return {"ok": False, "error": str(exc)}

    def send_to_correlator(
        self,
        selections: Sequence[Any],
        pairs: Sequence[Mapping[str, Any]],
        settings: Optional[Mapping[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Correlate the gated bursts. Thin wrapper over :meth:`send`."""
        return self.send(
            "fcs", selections, pairs=list(pairs), settings=dict(settings or {})
        )["result"]

    def send_to_pda(self, selections: Sequence[Any], **params: Any) -> Any:
        """Build a PDA histogram from the gate. Thin wrapper over :meth:`send`."""
        return self.send("pda", selections, **params)["result"]

    def send_to_tcspc(self, selections: Sequence[Any], **params: Any) -> Any:
        """Build micro-time decays from the gate. Thin wrapper over :meth:`send`."""
        return self.send("tcspc", selections, **params)["result"]

    def send_to_pch(self, selections: Sequence[Any], **params: Any) -> Any:
        """Build a counting histogram from the gate. Thin wrapper over :meth:`send`."""
        return self.send("pch", selections, **params)["result"]

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


def unavailable_reason(rpc_client: Any, data_source: Any, selections: Sequence[Any],
                       bridge: Optional["BurstAnalysisBridge"] = None) -> Optional[str]:
    """Why a selection cannot be sent right now, or ``None`` when it can.

    Checked in the order the user can act on: connect ChiSurf, load a burst
    table, then draw a gate. Both GUIs show the answer on their disabled "Send
    selection to" submenu, because a greyed-out entry that names what is
    missing says more than a missing entry.
    """
    if rpc_client is None:
        return (
            "No ChiSurf connection. Open ndX from ChiSurf, or start it with "
            "--chisurf-rpc host:port."
        )
    if data_source is None or data_source.empty:
        return "No data loaded."
    missing = {FILE_COL, FIRST_PHOTON_COL, LAST_PHOTON_COL} - set(data_source.parameter_names)
    if missing:
        return (
            "This table has no burst provenance: "
            f"{', '.join(sorted(missing))} missing. Sending needs the photon "
            "intervals each burst came from."
        )
    if not selections:
        return "No selection. Draw a gate first — the whole table would be sent."
    if not (bridge or BurstAnalysisBridge(rpc_client, data_source)).discover():
        return (
            "This ChiSurf advertises no burst analyses. It may be an older "
            "version, or the burst services are not loaded."
        )
    return None


def outcome_message(reply: Mapping[str, Any], target: str) -> str:
    """The status line after a send: how much went, and whether it was recorded."""
    message = f"Sent {reply['n_bursts']} bursts from {reply['n_files']} file(s) to {target}"
    provenance = reply.get("provenance")
    if provenance is None:
        message += " (not recorded: no database product attached)"
    elif isinstance(provenance, dict) and provenance.get("ok") is False:
        message += f" — but the provenance record failed: {provenance.get('error')}"
    else:
        message += " and recorded it"
    return message



__all__ = [
    "BurstAnalysisBridge",
    "Target",
    "CONSUMERS_RPC",
    "describe_selections",
    "summarise_result",
    "BurstBridgeError",
    "selection_to_burst_slices",
    "unavailable_reason",
    "outcome_message",
    "FILE_COL",
    "LAST_FILE_COL",
    "FIRST_PHOTON_COL",
    "LAST_PHOTON_COL",
]
