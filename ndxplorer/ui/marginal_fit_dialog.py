"""Dialog to fit an overlay curve to a marginal histogram via the fitting table.

When ChiSurf is available the marginal fit's parameters are the ChiSurf
``ParseModel``'s own ``FittingParameter`` objects, rendered in the shared
fitting-parameter table (value / fixed / bounds columns). The user frees or
fixes parameters there and presses **Fit**; ChiSurf's least-squares optimiser
runs over the free parameters and holds the fixed ones. Parameters that name an
ndXplorer constant arrive **fixed by default** (see
:func:`ndxplorer.analysis.marginal_fit.build_marginal_fit`).

``HAS_FIT_TABLE`` reports whether the ChiSurf table is importable; the caller
falls back to a direct fit when it is not.
"""

from __future__ import annotations

from typing import Callable, Optional

from qtpy import QtCore, QtWidgets

from ..analysis.marginal_fit import MarginalFit, MarginalFitResult

try:
    from chisurf.gui.autoform.sections.parameter_table import ParameterGroupTableWidget

    HAS_FIT_TABLE = True
except Exception:  # pragma: no cover - depends on environment
    ParameterGroupTableWidget = None
    HAS_FIT_TABLE = False


class _CompactColumns:
    """Column set for the fitting table: value + fixed flag + bounds (no error)."""

    columns = ("name", "value", "fixed", "bounds_lo", "bounds_hi", "bounds_on")


class MarginalFitDialog(QtWidgets.QDialog):
    """Fit an overlay equation to the current axis marginal with per-parameter control."""

    def __init__(
        self,
        parent: Optional[QtWidgets.QWidget],
        marginal_fit: MarginalFit,
        on_applied: Optional[Callable[[MarginalFitResult], None]] = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Fit to marginal")
        self.setMinimumWidth(420)
        self._mf = marginal_fit
        self._on_applied = on_applied

        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel(
            "Free parameters are optimised; fixed ones are held.\n"
            "Constants from the parameter table start fixed — free them to fit them."
        ))

        self._table = None
        if HAS_FIT_TABLE:
            self._table = ParameterGroupTableWidget(
                self._mf.parameters, section=_CompactColumns(), parent=self,
            )
            # The shared widget fixes its height from a row-height estimate that
            # under-counts the real rows and clips the last parameter. Let the
            # inner view grow to fit every parameter (scroll past a sensible cap).
            inner = getattr(self._table, "_table", None)
            if inner is not None:
                n = inner.model().rowCount()
                inner.setMaximumHeight(16777215)
                inner.setMinimumHeight(min(360, 30 * n + 32))
                inner.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
            layout.addWidget(self._table, 1)
        else:  # pragma: no cover - fallback, caller normally avoids this
            layout.addWidget(QtWidgets.QLabel("ChiSurf fitting table unavailable."))

        self._status = QtWidgets.QLabel("")
        self._status.setStyleSheet("color: #555; font-size: 9pt;")
        layout.addWidget(self._status)

        buttons = QtWidgets.QHBoxLayout()
        self._btn_fit = QtWidgets.QPushButton("🎯 Fit")
        self._btn_fit.setToolTip("Optimise every free parameter against the marginal")
        self._btn_fit.clicked.connect(self._do_fit)
        buttons.addWidget(self._btn_fit)
        buttons.addStretch(1)
        self._btn_close = QtWidgets.QPushButton("Close")
        self._btn_close.clicked.connect(self.accept)
        buttons.addWidget(self._btn_close)
        layout.addLayout(buttons)

    def _do_fit(self) -> None:
        result = self._mf.run()
        self._refresh_table()
        if result.ok:
            self._status.setText(
                f"χ²ᵣ = {result.chi2r:.4g}   ·   "
                + ", ".join(f"{k}={v:.4g}" for k, v in result.params.items())
            )
            self._status.setStyleSheet("color: #2e7d32; font-size: 9pt;")
        else:
            self._status.setText(result.message or "fit failed")
            self._status.setStyleSheet("color: #c62828; font-size: 9pt;")
        if self._on_applied is not None:
            try:
                self._on_applied(result)
            except Exception:
                pass

    def _refresh_table(self) -> None:
        if self._table is None:
            return
        try:
            self._table.set_params(self._mf.parameters)
        except Exception:
            try:
                self._table.sync()
            except Exception:
                pass


__all__ = ["MarginalFitDialog", "HAS_FIT_TABLE"]
