"""ChiSurf phasor / FRET-lines toolbar for the ndXplorer window (PRD-56).

Appears only when ndXplorer holds a ChiSurf RPC client (``ndx.phasor_service``). Its
button **surfaces the dockable control panel** (:class:`ndxplorer.ui.phasor_panel.
PhasorControlPanel`) where the phasor overlays and FRET lines are configured — so the
features are driven from a real GUI, not a single hard-coded toolbar action. A ``Clear``
button is kept for convenience. All actions fail soft (a status message, never a crash).
"""

from __future__ import annotations

import logging

from qtpy import QtWidgets

from .. import phasor_integration as pi
from .phasor_panel import install_phasor_panel

logger = logging.getLogger(__name__)


class PhasorToolbar(QtWidgets.QToolBar):
    """Toolbar whose button opens the ChiSurf phasor / FRET-line control panel."""

    def __init__(self, ndx) -> None:
        super().__init__("ChiSurf Phasor", ndx)
        self.setObjectName("chisurfPhasorToolbar")
        self._ndx = ndx
        self._panel = install_phasor_panel(ndx)

        self._panel_action = self.addAction("◐ Phasor / FRET…")
        self._panel_action.setToolTip(
            "Open the phasor / FRET-line control panel (overlay sets, frequency, "
            "reference lifetimes, FRET model + sweep, apparent-lifetime columns)."
        )
        self._panel_action.triggered.connect(self._on_open_panel)

        self._clear_action = self.addAction("✕ Clear")
        self._clear_action.setToolTip("Remove ChiSurf overlays from the plot.")
        self._clear_action.triggered.connect(self._on_clear)

    # -- helpers ----------------------------------------------------------------------
    def _status(self, msg: str) -> None:
        try:
            self._ndx.statusBar().showMessage(msg, 5000)
        except Exception:
            logger.info(msg)

    # -- actions ----------------------------------------------------------------------
    def _on_open_panel(self) -> None:
        if self._panel is None:
            self._status("Phasor control panel unavailable (no ChiSurf service)")
            return
        self._panel.show()
        self._panel.raise_()

    def _on_clear(self) -> None:
        pi.clear_line_overlays(self._ndx, tag="phasor")
        pi.clear_line_overlays(self._ndx, tag="fret")
        self._status("Cleared ChiSurf overlays")


def install_phasor_toolbar(ndx) -> PhasorToolbar | None:
    """Add a :class:`PhasorToolbar` to *ndx* when a ChiSurf phasor service is present."""
    if getattr(ndx, "phasor_service", None) is None:
        return None
    try:
        toolbar = PhasorToolbar(ndx)
        ndx.addToolBar(toolbar)
        return toolbar
    except Exception:  # pragma: no cover - defensive
        logger.warning("Could not install phasor toolbar", exc_info=True)
        return None
