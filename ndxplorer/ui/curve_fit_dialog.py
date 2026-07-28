"""Dialog to fit an overlay curve to the displayed data via the fitting table.

The curve's parameters are the ChiSurf ``ParseModel``'s own ``FittingParameter``
objects, rendered in the shared fitting-parameter table (value / fixed / bounds),
seeded from the overlay's own parameter table so fix/free and bounds are set in
one place. The user presses **Fit** and ChiSurf's least-squares optimiser runs
over the free parameters, holding the fixed ones. Parameters that name an
nDXplorer constant — and parameters crosslinked to another parameter — arrive
fixed (see :mod:`ndxplorer.analysis.curve_fit`).

What the curve is fitted *to* is chosen here: the displayed two-dimensional
distribution, or a one-dimensional marginal. Changing the target rebuilds the
fit from the values the user is looking at.

``HAS_FIT_TABLE`` reports whether the ChiSurf table is importable; the caller
falls back to a direct fit when it is not.
"""

from __future__ import annotations

from typing import Callable, Optional, Sequence, Tuple

from qtpy import QtCore, QtWidgets

from ..analysis.curve_fit import CurveFit, CurveFitError, CurveFitResult

try:
    from chisurf.gui.autoform.sections.parameter_table import ParameterGroupTableWidget

    HAS_FIT_TABLE = True
except Exception:  # pragma: no cover - depends on environment
    ParameterGroupTableWidget = None
    HAS_FIT_TABLE = False


class _CompactColumns:
    """Column set for the fitting table: value + fixed flag + bounds (no error)."""

    columns = ("name", "value", "fixed", "bounds_lo", "bounds_hi", "bounds_on")


#: The things a curve can be fitted to, in the order the dialog offers them.
DEFAULT_TARGETS: Tuple[Tuple[str, str], ...] = (
    ("2d", "Displayed data (y vs x)"),
    ("x", "X marginal histogram"),
    ("y", "Y marginal histogram"),
)


class CurveFitDialog(QtWidgets.QDialog):
    """Fit an overlay curve to the displayed data with per-parameter control."""

    def __init__(
        self,
        parent: Optional[QtWidgets.QWidget],
        build_fit: Callable[[str], CurveFit],
        targets: Sequence[Tuple[str, str]] = DEFAULT_TARGETS,
        on_applied: Optional[Callable[[CurveFitResult], None]] = None,
        target: str = "2d",
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Fit curve to data")
        self.setMinimumWidth(460)
        self._build_fit = build_fit
        self._on_applied = on_applied
        self._targets = list(targets)
        self._cf: Optional[CurveFit] = None

        layout = QtWidgets.QVBoxLayout(self)

        target_row = QtWidgets.QHBoxLayout()
        target_row.addWidget(QtWidgets.QLabel("Fit to:"))
        self._target_combo = QtWidgets.QComboBox()
        for key, label in self._targets:
            self._target_combo.addItem(label, key)
        self._target_combo.setCurrentIndex(max(0, self._target_combo.findData(target)))
        self._target_combo.setToolTip(
            "The displayed data fits y(x) to the two-dimensional distribution "
            "(one weighted point per populated x column); a marginal fits the "
            "curve to that axis's histogram of counts."
        )
        target_row.addWidget(self._target_combo, 1)
        layout.addLayout(target_row)

        hint = QtWidgets.QLabel(
            "Free parameters are optimised, fixed ones held. Constants and "
            "crosslinked parameters start fixed — free them to fit them."
        )
        # Without wrapping, the second half of the sentence is simply cut off at
        # the dialog's edge.
        hint.setWordWrap(True)
        layout.addWidget(hint)

        self._table_slot = QtWidgets.QVBoxLayout()
        layout.addLayout(self._table_slot)
        layout.addStretch(1)
        self._table = None

        self._status = QtWidgets.QLabel("")
        self._status.setStyleSheet("color: #555; font-size: 9pt;")
        layout.addWidget(self._status)

        buttons = QtWidgets.QHBoxLayout()
        self._btn_fit = QtWidgets.QPushButton("🎯 Fit")
        self._btn_fit.setToolTip("Optimise every free parameter against the selected data")
        self._btn_fit.clicked.connect(self._do_fit)
        buttons.addWidget(self._btn_fit)
        buttons.addStretch(1)
        self._btn_close = QtWidgets.QPushButton("Close")
        self._btn_close.clicked.connect(self.accept)
        buttons.addWidget(self._btn_close)
        layout.addLayout(buttons)

        self._target_combo.currentIndexChanged.connect(self._target_changed)
        self._rebuild()

    # -- target ------------------------------------------------------------
    @property
    def current_fit(self) -> Optional[CurveFit]:
        """The fit built for the selected target (``None`` if it could not be).

        The caller needs it to write results back into the curve's *own*
        parameters, which knows about links; the plain result is only names and
        numbers.
        """
        return self._cf

    @property
    def target(self) -> str:
        """The key of the data the curve is currently fitted to."""
        return str(self._target_combo.currentData())

    def _target_changed(self) -> None:
        self._rebuild()

    def _rebuild(self) -> None:
        """Build the fit for the selected target and show its parameters.

        A failure here — no histogram, a selection with nothing in it — disables
        the Fit button and says why, rather than leaving a dialog that looks
        ready and does nothing.
        """
        try:
            self._cf = self._build_fit(self.target)
            message = ""
        except CurveFitError as exc:
            self._cf = None
            message = str(exc)
        except Exception as exc:  # pragma: no cover - defensive
            self._cf = None
            message = f"cannot fit: {exc}"

        self._btn_fit.setEnabled(self._cf is not None)
        self._status.setText(message)
        self._status.setStyleSheet(
            "color: #c62828; font-size: 9pt;" if message else "color: #555; font-size: 9pt;"
        )
        self._install_table()

    def _install_table(self) -> None:
        """Replace the parameter table — a new target means new parameters."""
        if self._table is not None:
            self._table_slot.removeWidget(self._table)
            self._table.setParent(None)
            self._table.deleteLater()
            self._table = None
        if self._cf is None or not HAS_FIT_TABLE:
            return
        self._table = ParameterGroupTableWidget(
            self._cf.parameters,
            section=_CompactColumns(),
            parent=self,
            # These belong to a local throw-away fit the backend knows nothing
            # about; an edit sent there could only answer "fit not found".
            remote=False,
        )
        # The shared widget sizes itself to show every row; cap that here so a
        # twenty-parameter equation cannot make the dialog taller than a screen.
        inner = getattr(self._table, "_table", None)
        if inner is not None:
            capped = min(360, inner.height())
            inner.setMinimumHeight(capped)
            inner.setMaximumHeight(capped)
            inner.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        self._table_slot.addWidget(self._table, 1)

    # -- fitting -----------------------------------------------------------
    def _do_fit(self) -> None:
        if self._cf is None:
            return
        result = self._cf.run()
        self._refresh_table()
        if result.ok:
            self._status.setText(
                f"reduced χ² = {result.chi2r:.4g}   ·   "
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
            self._table.set_params(self._cf.parameters)
        except Exception:
            try:
                self._table.sync()
            except Exception:
                pass


__all__ = ["CurveFitDialog", "HAS_FIT_TABLE", "DEFAULT_TARGETS"]
