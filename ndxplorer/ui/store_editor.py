"""StoreEditor — spreadsheet-style editor for the table of a :class:`DataSource`.

A :class:`chisurf.gui.widgets.chitable.ChiTableDialog` over a
:class:`~chisurf.gui.widgets.chitable.DataStoreSource`. The dialog edits a copy
of the source's store; edits are staged in the table model and written into the
copy on Apply, and :func:`ndxplorer.core.store_edits.apply_edits` writes the
accepted copy back into the source column by column.
"""

from __future__ import annotations

from typing import List, Optional

from qtpy import QtWidgets

from chisurf.gui.widgets.chitable import ChiTableDialog, DataStoreSource

from ..core.data_source import DataSource
from ..core.store_edits import apply_edits

__all__ = ["StoreEditor", "edit_source"]


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
