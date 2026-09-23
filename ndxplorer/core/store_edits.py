"""Writing an edited copy of a table back into the table it was copied from.

The Table Editor (Qt: ``ndxplorer/ui/store_editor.py``; emtk: the Data button
of ``ndxplorer/app/features/overlays.py``) edits a copy of a
:class:`~ndxplorer.core.data_source.DataSource`; on Apply the copy is written
back here, column by column, so the source keeps its identity and its column
order. Toolkit-free.
"""

from __future__ import annotations

from typing import List

import numpy as np

from .data_source import DataSource

__all__ = ["apply_edits"]


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
