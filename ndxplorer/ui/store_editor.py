"""StoreEditor — spreadsheet-style editor for the table of a :class:`DataSource`.

A :class:`chisurf.gui.widgets.chitable.ChiTableDialog` over a
:class:`~chisurf.gui.widgets.chitable.DataStoreSource`. The dialog edits a copy
of the source's store; edits are staged in the table model and written into the
copy on Apply, and :func:`apply_edits` writes the accepted copy back into the
source column by column, so the source keeps its identity and its column order.
"""

from __future__ import annotations

from typing import List, Optional

import numpy as np
from qtpy import QtWidgets

from chisurf.gui.widgets.chitable import ChiTableDialog, DataStoreSource

from ..core.data_source import DataSource

__all__ = ["StoreEditor", "apply_edits", "edit_source"]


class StoreEditor(ChiTableDialog):
    """Modal editor on a copy of a :class:`DataSource`'s store.

    Parameters
    ----------
    source : DataSource
        The table to edit. Never modified by the dialog itself.
    parent : qtpy.QtWidgets.QWidget, optional
        Parent widget.
    """

    def __init__(self, source: DataSource, parent=None):
        self._working = source.copy()
        super().__init__(
            source=DataStoreSource(self._working.store, editable=True),
            title="Table Editor",
            parent=parent,
        )

    @property
    def edited(self) -> DataSource:
        """The edited copy; holds the accepted edits once the dialog is accepted."""
        return self._working


def apply_edits(source: DataSource, edited: DataSource) -> List[str]:
    """Write every column of `edited` that differs from `source` into `source`.

    Columns only `edited` has are appended; columns only `source` has stay.

    Returns
    -------
    list of str
        The names of the columns written.
    """
    written: List[str] = []
    for index, name in enumerate(edited.parameter_names):
        new = edited.column_items(index)
        mine = source.column_index(name)
        if mine >= 0 and source.parameter_names[mine] == name:
            old = source.column_items(mine)
            if old.dtype == new.dtype and old.shape == new.shape and (
                    np.array_equal(old, new, equal_nan=new.dtype.kind == "f")):
                continue
        source.set_column(name, new)
        written.append(name)
    return written


def edit_source(source: DataSource, parent=None) -> Optional[List[str]]:
    """Show the editor; on Apply write the edits into `source`.

    Returns
    -------
    list of str or None
        The columns written, or ``None`` when the dialog was cancelled.
    """
    dlg = StoreEditor(source, parent)
    if dlg.exec_() == QtWidgets.QDialog.Accepted:
        return apply_edits(source, dlg.edited)
    return None
