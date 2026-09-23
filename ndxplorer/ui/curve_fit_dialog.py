"""Dialog to fit an overlay curve to the displayed data via the fitting table.

The curve's parameters are the ChiSurf ``ParseModel``'s own ``FittingParameter``
objects, rendered in the shared fitting-parameter table (value / fixed / bounds),
seeded from the overlay's own parameter table so fix/free and bounds are set in
one place. The user presses **Fit** and ChiSurf's least-squares optimiser runs
over the free parameters, holding the fixed ones. Parameters that name an
nDXplorer constant — and parameters crosslinked to another parameter — arrive
fixed (see :mod:`ndxplorer.analysis.curve_fit`).

Below the curve's parameters sits a second table: nDXplorer's own constants,
the ones the equations read. Freeing one puts it in the same fit, where it moves
the **data** rather than the curve — the population is re-derived from the
equations at every step, which is how a detection-correction factor is
determined from a static FRET line.

What the curve is fitted *to* is chosen here: the displayed two-dimensional
distribution, or a one-dimensional marginal. Changing the target rebuilds the
fit from the values the user is looking at.

``HAS_FIT_TABLE`` reports whether the ChiSurf table is importable; the caller
falls back to a direct fit when it is not.
"""

from __future__ import annotations

import inspect
from typing import Callable, Optional, Sequence, Tuple

from qtpy import QtCore, QtWidgets

from ..analysis.curve_fit import CurveFit, CurveFitError, CurveFitResult
from ..analysis.curve_fit_setup import REDUCTIONS, TARGETS, result_text

try:
    from chisurf.gui.autoform.sections.parameter_table import ParameterGroupTableWidget

    HAS_FIT_TABLE = True
except Exception:  # pragma: no cover - depends on environment
    ParameterGroupTableWidget = None
    HAS_FIT_TABLE = False

try:
    from chisurf.gui.autoform.sections.progress_section import InlineProgressWidget
    from chisurf.gui.progress import ChiSurfProgress
except Exception:  # pragma: no cover - depends on environment
    InlineProgressWidget = None
    ChiSurfProgress = None


class _CompactColumns:
    """Column set for the fitting table: value + fixed flag + bounds (no error)."""

    columns = ("name", "value", "fixed", "bounds_lo", "bounds_hi", "bounds_on")


class CurveFitDialog(QtWidgets.QDialog):
    """Fit an overlay curve to the displayed data with per-parameter control."""

    def __init__(
        self,
        parent: Optional[QtWidgets.QWidget],
        build_fit: Callable[[str, str], CurveFit],
        targets: Sequence[Tuple[str, str]] = TARGETS,
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
            "(one point per populated x column); a marginal fits the curve to "
            "that axis's histogram of counts."
        )
        target_row.addWidget(self._target_combo, 1)
        layout.addLayout(target_row)

        # A burst plot is a mixture — a FRET population, donor-only at E≈0, a
        # scatter of singles — so the column *average* lies where nothing is,
        # and a line fitted through it misses the population it describes.
        reduction_row = QtWidgets.QHBoxLayout()
        reduction_row.addWidget(QtWidgets.QLabel("Fit through:"))
        self._reduction_combo = QtWidgets.QComboBox()
        for key, label in REDUCTIONS:
            self._reduction_combo.addItem(label, key)
        self._reduction_combo.setToolTip(
            "The cloud fits the curve to the distribution itself: every "
            "populated bin pulls on it, weighted by what it counted, and a bin "
            "more than a couple of bins away stops pulling — so the curve "
            "follows the populations and ignores the junk. Reducing each column "
            "to one point instead cannot describe a population: a blob reduces "
            "to a horizontal streak across its own columns."
        )
        reduction_row.addWidget(self._reduction_combo, 1)
        self._scan_box = QtWidgets.QCheckBox("Scan first")
        self._scan_box.setToolTip(
            "Evaluate a coarse grid over the free parameters before the fit "
            "and start it at the best point. A least-squares run only goes "
            "downhill from where it starts, so a degenerate pair — a constant "
            "that scales the data against a parameter that scales the curve — "
            "otherwise strands it in the first dip. Costs a fixed number of "
            "steps."
        )
        self._scan_box.setChecked(True)
        reduction_row.addWidget(self._scan_box)
        layout.addLayout(reduction_row)

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
        #: Second table: nDXplorer's constants, with its caption. Built only
        #: when the fit has some to offer.
        self._data_table = None
        self._data_label = None

        self._status = QtWidgets.QLabel("")
        # The result line lists every fitted parameter; without wrapping the
        # dialog's width simply cuts it off mid-number.
        self._status.setWordWrap(True)
        self._status.setStyleSheet("color: #555; font-size: 9pt;")
        layout.addWidget(self._status)

        # ChiSurf's inline progress bar, sitting in the dialog: a fit that
        # re-derives the data takes seconds, and ``ChiSurfProgress`` renders
        # into this widget (with its own Cancel) instead of stacking a modal
        # dialog on top of a modal dialog — or going silent headlessly.
        self._progress_bar = None
        if InlineProgressWidget is not None:
            self._progress_bar = InlineProgressWidget()
            layout.addWidget(self._progress_bar)

        buttons = QtWidgets.QHBoxLayout()
        self._btn_fit = QtWidgets.QPushButton("Fit")
        self._btn_fit.setToolTip("Optimise every free parameter against the selected data")
        self._btn_fit.clicked.connect(self._do_fit)
        buttons.addWidget(self._btn_fit)
        buttons.addStretch(1)
        self._btn_close = QtWidgets.QPushButton("Close")
        self._btn_close.clicked.connect(self.accept)
        buttons.addWidget(self._btn_close)
        layout.addLayout(buttons)

        self._target_combo.currentIndexChanged.connect(self._target_changed)
        self._reduction_combo.currentIndexChanged.connect(self._target_changed)
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

    @property
    def reduction(self) -> str:
        """How a column is reduced to the point the curve is fitted through."""
        return str(self._reduction_combo.currentData())

    def _target_changed(self) -> None:
        self._rebuild()

    def _rebuild(self) -> None:
        """Build the fit for the selected target/reduction and show its parameters.

        A failure here — no histogram, a selection with nothing in it — disables
        the Fit button and says why, rather than leaving a dialog that looks
        ready and does nothing.
        """
        try:
            self._cf = self._call_build()
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

    def _call_build(self) -> CurveFit:
        """Build the fit, telling the builder the reduction if it takes one.

        The reduction is a later addition, so a builder written against the
        original one-argument contract still works — asked, not assumed, so a
        ``TypeError` raised *inside* a builder is never mistaken for one.
        """
        try:
            takes_reduction = len(inspect.signature(self._build_fit).parameters) > 1
        except (TypeError, ValueError):  # builtins, C callables
            takes_reduction = False
        if takes_reduction:
            return self._build_fit(self.target, self.reduction)
        return self._build_fit(self.target)

    def _install_table(self) -> None:
        """Replace the parameter tables — a new target means new parameters."""
        for attr in ("_table", "_data_label", "_data_table"):
            widget = getattr(self, attr, None)
            if widget is not None:
                self._table_slot.removeWidget(widget)
                widget.setParent(None)
                widget.deleteLater()
                setattr(self, attr, None)
        if self._cf is None or not HAS_FIT_TABLE:
            return
        self._table = self._make_table(self._cf.parameters)
        self._table_slot.addWidget(self._table, 1)

        # nDXplorer's own constants, if this fit can offer any. They are the
        # live parameters of the Parameters tab, so a value fitted here is
        # already in that table when the fit returns.
        data_parameters = getattr(self._cf, "data_parameters", [])
        if data_parameters:
            self._data_label = QtWidgets.QLabel(
                "nDXplorer parameters — a freed one moves the <b>data</b>, "
                "which is re-derived from the equations at every step."
            )
            self._data_label.setWordWrap(True)
            self._data_label.setStyleSheet("color: #555; font-size: 9pt;")
            self._table_slot.addWidget(self._data_label)
            self._data_table = self._make_table(data_parameters, cap=240)
            self._table_slot.addWidget(self._data_table, 1)

    def _make_table(self, params, cap: int = 360):
        """Build one capped parameter table over ``params``."""
        table = ParameterGroupTableWidget(
            params,
            section=_CompactColumns(),
            parent=self,
            # These belong to a local throw-away fit the backend knows nothing
            # about; an edit sent there could only answer "fit not found".
            remote=False,
        )
        # The shared widget sizes itself to show every row; cap that here so a
        # twenty-parameter equation cannot make the dialog taller than a screen.
        inner = getattr(table, "_table", None)
        if inner is not None:
            capped = min(cap, inner.height())
            inner.setMinimumHeight(capped)
            inner.setMaximumHeight(capped)
            inner.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAsNeeded)
        return table

    # -- fitting -----------------------------------------------------------
    def _do_fit(self) -> None:
        if self._cf is None:
            return
        # Freeing a constant re-derives the plotted columns per step, so this is
        # seconds rather than milliseconds — show a heartbeat and a way out
        # instead of a frozen window.
        moves_data = bool(getattr(self._cf, "free_data_parameters", list)())
        self._btn_fit.setEnabled(False)
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        try:
            QtWidgets.QApplication.processEvents()
            if moves_data and ChiSurfProgress is not None:
                self._status.setText("fitting — the data is re-derived at every step…")
                self._status.setStyleSheet("color: #555; font-size: 9pt;")
                result = self._run_with_progress()
            else:
                result = self._cf.run(scan=self._scan_box.isChecked())
        finally:
            QtWidgets.QApplication.restoreOverrideCursor()
            self._btn_fit.setEnabled(True)
        self._refresh_table()
        message, failed = result_text(result)
        self._status.setText(message)
        self._status.setStyleSheet(
            "color: #c62828; font-size: 9pt;" if failed else "color: #2e7d32; font-size: 9pt;"
        )
        if self._on_applied is not None:
            try:
                self._on_applied(result)
            except Exception:
                pass

    def _run_with_progress(self):
        """Run the fit under ChiSurf's progress bar, cancellable.

        The step count is not known ahead of time (the optimiser decides), so
        the bar is a busy indicator that reports the evaluation it is on. The
        fit runs on the GUI thread — it drives the window's own data and
        parameters — so the event loop is pumped from the callback rather than
        from a worker, and Cancel is delivered by returning ``False`` there.
        """
        with ChiSurfProgress(
            self, "Fitting — re-deriving the data at every step…", 0,
            title="Curve fit",
        ) as bar:

            def step(index: int):
                bar.update_progress(index, f"step {index}")
                QtWidgets.QApplication.processEvents()
                return not bar.wasCanceled()

            try:
                self._cf.set_progress(step)
            except AttributeError:
                pass
            try:
                return self._cf.run(scan=self._scan_box.isChecked())
            finally:
                try:
                    self._cf.set_progress(None)
                except AttributeError:
                    pass

    def _refresh_table(self) -> None:
        for table, params in (
            (self._table, getattr(self._cf, "parameters", None)),
            (self._data_table, getattr(self._cf, "data_parameters", None)),
        ):
            if table is None:
                continue
            try:
                table.set_params(params)
            except Exception:
                try:
                    table.sync()
                except Exception:
                    pass


__all__ = ["CurveFitDialog", "HAS_FIT_TABLE"]
