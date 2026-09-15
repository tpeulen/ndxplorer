"""HDF5 export helpers for NDXplorer selections."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import tttrlib

from ..logging_config import logging
from ..utils.performance_optimizations import get_performance_monitor
from .models import SelectionExportPayload

#: Attribute of the table's first column holding the payload metadata as JSON.
METADATA_ATTRIBUTE = "ndxplorer_metadata_json"
#: Attribute of the table's first column holding ``values.shape`` as JSON.
VALUES_SHAPE_ATTRIBUTE = "ndxplorer_values_shape"


class HDFBackendUnavailable(RuntimeError):
    """Raised when tttrlib was built without HDF5 support."""


def export_hdf5(
    payload: SelectionExportPayload,
    path: Path,
    *,
    compression_level: int = 4,
    group: str = "/",
) -> None:
    """
    Persist selection data + metadata as a columnar HDF5 table.

    One 1-D dataset per column, written by :func:`tttrlib.write_hdf5`, so
    :func:`tttrlib.read_hdf5` (and ndXplorer) reads the file straight back into
    a store. The payload metadata and, for a values payload, the shape of
    ``values`` are stored as JSON attributes of the first column.

    Parameters
    ----------
    payload:
        SelectionExportPayload containing a table or values.
    path:
        Destination file. An existing file is replaced.
    compression_level:
        gzip level 0-9 (0 for none).
    group:
        HDF5 group the table is written to; the root by default, so the file is
        read back without naming one.
    """

    if not payload.has_tabular_data():
        raise ValueError("export_hdf5 requires payload.table or payload.values.")
    if not tttrlib.hdf5_table_available():
        raise HDFBackendUnavailable("tttrlib was built without HDF5 support.")

    path.parent.mkdir(parents=True, exist_ok=True)
    table = payload.as_store().copy()
    table.clear_row_mask()
    if table.n_columns():
        first = table.column(0)
        first.set_attribute(METADATA_ATTRIBUTE, payload.to_json_metadata())
        if payload.values is not None:
            first.set_attribute(VALUES_SHAPE_ATTRIBUTE,
                                json.dumps(list(np.asarray(payload.values).shape)))

    logging.info("Exporting selection to %s via tttrlib.write_hdf5", path)

    perf = get_performance_monitor()
    op_name = f"export_hdf5[{group}]"
    perf.start_timer(op_name)
    try:
        written = tttrlib.write_hdf5(str(path), table, group=group,
                                     compression=int(compression_level),
                                     mode=tttrlib.Hdf5WriteMode_Truncate)
        if not written:
            raise OSError(f"tttrlib could not write {path}")
    finally:
        perf.end_timer(op_name)
        perf.log_memory_usage(op_name)


__all__ = ["export_hdf5", "HDFBackendUnavailable", "METADATA_ATTRIBUTE",
           "VALUES_SHAPE_ATTRIBUTE"]
