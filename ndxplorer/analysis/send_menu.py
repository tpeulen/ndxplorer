"""The "Send selection to …" menu: a gated population, handed to an analysis.

Gating a burst parameter space answers *where* the populations are. The next
question is always what that population looks like under a real analysis — its
decay, its correlation, its shot-noise distance distribution, its counting
statistics — and answering it needs the population's photons back.

:mod:`ndxplorer.analysis.burst_bridge` does the handoff; this module is the way
in. The submenu is built from **what ChiSurf advertises** — this module contains
no list of analyses, and no ChiSurf method names. ChiSurf answers
``bursts.consumers`` with its burst-consuming analyses (including any a plugin
declares in its manifest), and the menu renders that. A new analysis therefore
appears here with no ndXplorer release, and an older ChiSurf simply advertises
fewer entries instead of producing a menu with dead ones.

Two behaviours worth stating, because both are deliberate:

**The menu explains why it is disabled rather than disappearing.** A send needs
four things — a ChiSurf connection, something advertised on the other end, a
gate, and burst-provenance columns in the table — and any of them can be
missing. A greyed-out entry that names the missing one is far more useful than
an entry that is simply not there, which reads as "this feature does not
exist".

**Provenance failure is reported, not raised.** The bridge records every handoff
to the metadata store. If that write fails the analysis has still succeeded, so
the result is kept and the status line says the provenance is missing — losing
the record is bad, and discarding a completed computation over it is worse.
"""

from __future__ import annotations

from typing import Any, Optional

from qtpy import QtCore, QtWidgets

from ..logging_config import logging
from .burst_bridge import (
    BurstAnalysisBridge,
    BurstBridgeError,
    outcome_message,
    unavailable_reason,
)

__all__ = ["make_bridge", "add_send_menu", "send_selection", "why_unavailable"]


def make_bridge(ndxplorer: Any) -> BurstAnalysisBridge:
    """Build a bridge bound to the explorer's RPC client and data."""
    return BurstAnalysisBridge(
        getattr(ndxplorer, "chisurf_rpc", None),
        ndxplorer.data_source,
        owner=ndxplorer,
    )


def why_unavailable(ndxplorer: Any, bridge: Optional[BurstAnalysisBridge] = None) -> Optional[str]:
    """Return why sending is impossible right now, or ``None`` when it is not.

    Checked in the order the user can act on: connect ChiSurf, load a burst
    table, then draw a gate.
    """
    try:
        selections = ndxplorer.plot_control.get_selections()
    except Exception:  # pragma: no cover - control may not exist headlessly
        selections = []
    return unavailable_reason(getattr(ndxplorer, "chisurf_rpc", None),
                              getattr(ndxplorer, "data_source", None), selections, bridge)


def add_send_menu(menu: QtWidgets.QMenu, ndxplorer: Any) -> QtWidgets.QMenu:
    """Append a "Send selection to" submenu to *menu*.

    Parameters
    ----------
    menu : qtpy.QtWidgets.QMenu
        The context menu being built.
    ndxplorer : NDXplorer
        The explorer window.

    Returns
    -------
    qtpy.QtWidgets.QMenu
        The submenu, so a caller can inspect it in a test.
    """
    bridge = make_bridge(ndxplorer)
    reason = why_unavailable(ndxplorer, bridge)
    submenu = menu.addMenu("Send selection to")
    submenu.setObjectName("menuSendSelectionTo")
    if reason:
        submenu.setEnabled(False)
        submenu.setToolTip(reason)
        # Menus do not show tooltips by default, and a disabled item with no
        # explanation is the least helpful thing a UI can do.
        submenu.setTitle(f"Send selection to — {reason.split('.')[0]}")

    for target in bridge.discover().values():
        action = submenu.addAction(target.title)
        action.setObjectName(f"actionSendTo_{target.key}")
        # The caveat, where the analysis advertises one, belongs where the user
        # decides — not only in the result they have already committed to.
        action.setToolTip(
            f"{target.summary}\n\n⚠ {target.caveat}" if target.caveat else target.summary
        )
        action.setEnabled(reason is None)
        action.triggered.connect(
            lambda _checked=False, key=target.key: send_selection(ndxplorer, key)
        )
    return submenu


def send_selection(ndxplorer: Any, target: str, **params: Any) -> Optional[dict]:
    """Send the current gate to *target* and report the outcome.

    Runs on the GUI thread behind a wait cursor: reading the photons of a gated
    population is bounded by the gate, not by the file, so it is usually quick —
    but a gate covering most of a large measurement is not, which is why the
    status line names the analysis while it runs.

    Returns
    -------
    dict or None
        The bridge's reply, or ``None`` if the send was refused or failed.
    """
    bridge = make_bridge(ndxplorer)
    reason = why_unavailable(ndxplorer, bridge)
    if reason:
        _status(ndxplorer, reason)
        return None

    selections = ndxplorer.plot_control.get_selections()
    _status(ndxplorer, f"Sending the selection to {target}…", timeout=0)
    QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
    try:
        reply = bridge.send(target, selections, **params)
    except BurstBridgeError as exc:
        logging.error("send to %s failed: %s", target, exc)
        _status(ndxplorer, f"Could not send to {target}: {exc}")
        return None
    except Exception as exc:
        logging.exception("send to %s failed", target)
        _status(ndxplorer, f"Could not send to {target}: {exc}")
        return None
    finally:
        QtWidgets.QApplication.restoreOverrideCursor()

    message = outcome_message(reply, target)
    _status(ndxplorer, message)
    return reply


def _status(ndxplorer: Any, message: str, timeout: int = 8000) -> None:
    """Put *message* on the status bar, falling back to the log."""
    try:
        ndxplorer.statusBar().showMessage(message, timeout)
    except Exception:  # pragma: no cover - headless windows may have no bar
        logging.info(message)
