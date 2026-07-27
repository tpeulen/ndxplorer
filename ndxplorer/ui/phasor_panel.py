"""Dockable phasor / FRET-line control panel for ndXplorer (PRD-56).

The toolbar button surfaces *this* panel, so the phasor reference geometry and the
FRET lines are fully configurable — overlay sets, frequency/harmonic, reference
lifetimes, the FRET model + swept parameter and its range — instead of firing a
single hard-coded action. The panel drives the chisurf-free
:mod:`ndxplorer.phasor_integration` helpers over the RPC ``phasor_service`` /
``lines_service`` and never imports chisurf.
"""

from __future__ import annotations

import logging
from typing import Optional

from qtpy import QtCore, QtWidgets

from .. import phasor_integration as pi

logger = logging.getLogger(__name__)

#: Overlay sets offered as checkboxes → (set key, label).
_OVERLAY_SETS = (
    ("semicircle", "Universal semicircle"),
    ("lifetime_grid", "Iso-lifetime grid"),
    ("lifetime_ticks", "Lifetime ticks"),
    ("polar_grid", "Polar grid"),
    ("fret", "FRET trajectory"),
)


class PhasorControlPanel(QtWidgets.QDockWidget):
    """Dock widget exposing every phasor-overlay and FRET-line control."""

    def __init__(self, ndx) -> None:
        super().__init__("ChiSurf Phasor / FRET", ndx)
        self.setObjectName("chisurfPhasorPanel")
        self._ndx = ndx

        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        body = QtWidgets.QWidget()
        scroll.setWidget(body)
        self.setWidget(scroll)
        root = QtWidgets.QVBoxLayout(body)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(8)

        root.addWidget(self._build_overlay_group())
        root.addWidget(self._build_fret_group())
        root.addWidget(self._build_columns_group())
        root.addStretch(1)
        self._populate_fret_models()

    # -- overlays -------------------------------------------------------------------
    def _build_overlay_group(self) -> QtWidgets.QGroupBox:
        box = QtWidgets.QGroupBox("Phasor overlays")
        form = QtWidgets.QFormLayout(box)

        self._freq = QtWidgets.QDoubleSpinBox()
        self._freq.setRange(0.001, 10000.0)
        self._freq.setDecimals(3)
        self._freq.setValue(80.0)
        self._freq.setSuffix(" MHz")
        self._freq.setToolTip("Modulation frequency for the phasor geometry and lifetimes.")
        form.addRow("Frequency", self._freq)

        self._harmonic = QtWidgets.QSpinBox()
        self._harmonic.setRange(1, 16)
        self._harmonic.setToolTip("Harmonic number; effective frequency = frequency × harmonic.")
        form.addRow("Harmonic", self._harmonic)

        self._taus = QtWidgets.QLineEdit("0.5, 1, 2, 4, 8")
        self._taus.setToolTip("Comma-separated reference lifetimes (ns) for the grid and ticks.")
        form.addRow("Lifetimes (ns)", self._taus)

        self._tau_d0 = QtWidgets.QDoubleSpinBox()
        self._tau_d0.setRange(0.001, 1000.0)
        self._tau_d0.setDecimals(3)
        self._tau_d0.setValue(4.0)
        self._tau_d0.setSuffix(" ns")
        self._tau_d0.setToolTip("Donor-only lifetime for the FRET trajectory (τ_DA = τ_D0·(1−E)).")
        form.addRow("Donor τ0", self._tau_d0)

        self._set_checks: dict[str, QtWidgets.QCheckBox] = {}
        checks = QtWidgets.QVBoxLayout()
        for key, label in _OVERLAY_SETS:
            cb = QtWidgets.QCheckBox(label)
            cb.setChecked(key in ("semicircle", "lifetime_grid", "lifetime_ticks"))
            self._set_checks[key] = cb
            checks.addWidget(cb)
        holder = QtWidgets.QWidget()
        holder.setLayout(checks)
        form.addRow("Show", holder)

        buttons = QtWidgets.QHBoxLayout()
        draw = QtWidgets.QToolButton()
        draw.setText("◐ Draw overlays")
        draw.setToolButtonStyle(QtCore.Qt.ToolButtonTextOnly)
        draw.clicked.connect(self._on_draw_overlays)
        buttons.addWidget(draw)
        clear = QtWidgets.QToolButton()
        clear.setText("✕ Clear")
        clear.clicked.connect(self._on_clear)
        buttons.addWidget(clear)
        buttons.addStretch(1)
        wrap = QtWidgets.QWidget()
        wrap.setLayout(buttons)
        form.addRow(wrap)
        return box

    # -- FRET line ------------------------------------------------------------------
    def _build_fret_group(self) -> QtWidgets.QGroupBox:
        box = QtWidgets.QGroupBox("FRET line")
        form = QtWidgets.QFormLayout(box)

        self._fret_model = QtWidgets.QComboBox()
        self._fret_model.setToolTip("FRET component model.")
        self._fret_model.currentTextChanged.connect(self._on_fret_model_changed)
        form.addRow("Model", self._fret_model)

        self._fret_sweep = QtWidgets.QComboBox()
        self._fret_sweep.setToolTip("Parameter swept along the FRET line.")
        form.addRow("Sweep param", self._fret_sweep)

        self._fret_min = QtWidgets.QDoubleSpinBox()
        self._fret_min.setRange(-1e6, 1e6)
        self._fret_min.setDecimals(3)
        self._fret_min.setValue(20.0)
        form.addRow("Min", self._fret_min)

        self._fret_max = QtWidgets.QDoubleSpinBox()
        self._fret_max.setRange(-1e6, 1e6)
        self._fret_max.setDecimals(3)
        self._fret_max.setValue(90.0)
        form.addRow("Max", self._fret_max)

        self._fret_n = QtWidgets.QSpinBox()
        self._fret_n.setRange(2, 2000)
        self._fret_n.setValue(50)
        form.addRow("Points", self._fret_n)

        draw = QtWidgets.QToolButton()
        draw.setText("📈 Draw FRET line")
        draw.setToolButtonStyle(QtCore.Qt.ToolButtonTextOnly)
        draw.clicked.connect(self._on_draw_fret)
        form.addRow(draw)
        return box

    # -- derived columns ------------------------------------------------------------
    def _build_columns_group(self) -> QtWidgets.QGroupBox:
        box = QtWidgets.QGroupBox("Derived columns")
        lay = QtWidgets.QVBoxLayout(box)
        btn = QtWidgets.QToolButton()
        btn.setText("τ φ/M columns")
        btn.setToolButtonStyle(QtCore.Qt.ToolButtonTextOnly)
        btn.setToolTip("Compute τ_φ and τ_M from the g, s axes and add them as columns.")
        btn.clicked.connect(self._on_compute_lifetime)
        lay.addWidget(btn)
        return box

    # -- helpers --------------------------------------------------------------------
    def _status(self, msg: str) -> None:
        try:
            self._ndx.statusBar().showMessage(msg, 5000)
        except Exception:
            logger.info(msg)

    def _tau_list(self) -> Optional[list[float]]:
        out: list[float] = []
        for tok in self._taus.text().replace(";", ",").split(","):
            tok = tok.strip()
            if not tok:
                continue
            try:
                out.append(float(tok))
            except ValueError:
                pass
        return out or None

    def _components(self) -> list[dict]:
        return [{"model_name": self._fret_model.currentText(), "n_components": 1, "params": {}}]

    def _populate_fret_models(self) -> None:
        service = getattr(self._ndx, "lines_service", None)
        if service is None:
            return
        try:
            models = service.fret_line.list_models()
        except Exception as exc:
            logger.info("Could not list FRET models: %s", exc)
            return
        self._fret_model.blockSignals(True)
        self._fret_model.clear()
        self._fret_model.addItems([str(m) for m in models])
        self._fret_model.blockSignals(False)
        self._on_fret_model_changed(self._fret_model.currentText())

    def _on_fret_model_changed(self, _text: str) -> None:
        service = getattr(self._ndx, "lines_service", None)
        if service is None or not self._fret_model.currentText():
            return
        try:
            targets = service.fret_line.list_sweep_targets(self._components())
        except Exception as exc:
            logger.info("Could not list sweep targets: %s", exc)
            return
        names = [str(t.get("name", t) if isinstance(t, dict) else t) for t in targets]
        self._fret_sweep.clear()
        self._fret_sweep.addItems(names)

    # -- actions --------------------------------------------------------------------
    def _selected_sets(self) -> list[str]:
        return [key for key, cb in self._set_checks.items() if cb.isChecked()]

    def _on_draw_overlays(self) -> None:
        if not pi.axes_look_like_phasor(self._ndx):
            self._status("Set the plot axes to (g, s) to show phasor overlays")
            return
        sets = self._selected_sets()
        if not sets:
            self._status("Select at least one overlay set")
            return
        try:
            n = pi.show_phasor_overlays(
                self._ndx, sets=sets, frequency_mhz=self._freq.value(),
                harmonic=self._harmonic.value(), taus=self._tau_list(),
                tau_d0=self._tau_d0.value(),
            )
            self._status(f"Drew {n} phasor overlay item(s)")
        except Exception as exc:
            logger.warning("phasor overlays failed", exc_info=True)
            self._status(f"Phasor overlays failed: {exc}")

    def _on_draw_fret(self) -> None:
        sweep_name = self._fret_sweep.currentText()
        if not sweep_name:
            self._status("Pick a sweep parameter for the FRET line")
            return
        try:
            n = pi.show_fret_lines(
                self._ndx,
                components=self._components(),
                sweep={"kind": "param", "component": 0, "name": sweep_name},
                param_min=self._fret_min.value(),
                param_max=self._fret_max.value(),
                n_points=self._fret_n.value(),
            )
            self._status(f"Drew FRET line ({n} item)")
        except Exception as exc:
            logger.warning("FRET line failed", exc_info=True)
            self._status(f"FRET line failed: {exc}")

    def _on_compute_lifetime(self) -> None:
        try:
            added = pi.compute_apparent_lifetime_columns(
                self._ndx, frequency_mhz=self._freq.value()
            )
            self._status(f"Added columns: {', '.join(added)}" if added
                         else "No g / s columns found for τ_φ / τ_M")
        except Exception as exc:
            logger.warning("apparent lifetime failed", exc_info=True)
            self._status(f"τ φ/M failed: {exc}")

    def _on_clear(self) -> None:
        pi.clear_line_overlays(self._ndx, tag="phasor")
        pi.clear_line_overlays(self._ndx, tag="fret")
        self._status("Cleared ChiSurf overlays")


def install_phasor_panel(ndx) -> Optional[PhasorControlPanel]:
    """Create the phasor/FRET control dock (hidden until the toolbar shows it)."""
    if getattr(ndx, "phasor_service", None) is None:
        return None
    panel = PhasorControlPanel(ndx)
    try:
        ndx.addDockWidget(QtCore.Qt.RightDockWidgetArea, panel)
        panel.hide()
    except Exception:
        logger.warning("Could not add phasor control panel", exc_info=True)
        return None
    return panel
