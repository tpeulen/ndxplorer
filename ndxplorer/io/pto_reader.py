"""Read a burst analysis straight out of a `.pto` measurement container.

Until now ndX could open exactly one thing: a *folder* whose name encodes the
analysis parameters, holding a `.bur` in ``bi4_bur`` plus companions merged with
it by counting rows. That folder is a file-format workaround, and the analysis
that writes it now writes its results into the measurement's own container
instead -- the photons and every table computed from them in one file. Handed
one of those, :func:`ndxplorer.io.reader.read_burst_analysis` reported "No .bur
files in 'bi4_bur' or 'bur'", which is true and unhelpful: the bursts were
right there, in the file it was given.

The container is a plain columnar store per table, so there is no merge-by-row-
counting to redo here and no interleaved padding to strip -- both are artefacts
of the text layout. A companion analysis is another *table* in the same file,
joined on a declared key, so the several-tables case is a join rather than a
column-wise concatenation that silently misaligns when one analysis skipped a
burst.
"""

from __future__ import annotations

import logging
import pathlib
from typing import Any, Optional

import pandas as pd

from ndxplorer.core.data_source import DataSource

__all__ = ["is_container", "read_container"]

#: What ChiSurf's measurement container is called on disk.
SUFFIX = ".pto"

#: Tables holding one row per burst. A container may also hold a photon stream,
#: a decay, a fit -- none of which is what a burst view is asking for.
_BURST_GRAIN = "burst"

#: The operation that produces the burst list itself, as opposed to the
#: per-burst results computed from it (a 2CDE, a BVA, an MLE fit), which are
#: also at burst grain and are the container's answer to the `…4` companions.
_SEARCH = "burst_selection"

#: Columns the `.bur` reader renames on the way in, so a container-loaded set
#: reaches the rest of ndX under the same names as a folder-loaded one.
_MACRO_MS = "Mean Macro Time (ms)"
_MACRO_S = "Mean Macro Time (s)"


def is_container(path: str | pathlib.Path) -> bool:
    """Return whether *path* is a measurement container ndX can read bursts from.

    Cheap: a suffix check on a file, never a parse. Used to decide which reader
    a dropped path goes to.

    Parameters
    ----------
    path : str or pathlib.Path

    Returns
    -------
    bool
    """
    p = pathlib.Path(path)
    return p.is_file() and p.suffix.lower() == SUFFIX


def read_container(
    path: str | pathlib.Path, *, table: Optional[str] = None
) -> DataSource:
    """Return the burst table (and every per-burst result beside it) as a DataSource.

    Parameters
    ----------
    path : str or pathlib.Path
        The container.
    table : str, optional
        Name of a specific burst-grain table. Omitted, every table at burst
        grain is joined side by side, which is the container's equivalent of the
        folder's ``…4`` companions -- with the difference that the join is on
        row position *within one measurement*, where the row counts are equal by
        contract, rather than across files where they are not.

    Returns
    -------
    ndxplorer.core.data_source.DataSource

    Raises
    ------
    FileNotFoundError
        If the container holds no burst table at all -- the photons are there
        but nothing has been searched yet, which is a different problem from a
        missing file and says so.
    """
    path = pathlib.Path(path)
    frames, names = _burst_frames(path, table)
    if not frames:
        raise FileNotFoundError(
            f"{path.name} holds no burst table: convert the photons with a burst "
            "search first, or point ndX at the analysis folder if one was written."
        )

    logging.info("Reading %d burst table(s) from %s: %s", len(frames), path, names)
    combined = pd.concat(frames, axis=1)
    combined = combined.loc[:, ~combined.columns.duplicated()]

    # The same unit convention the `.bur` reader applies, so a plot axis does
    # not depend on which of the two a set came from.
    if _MACRO_MS in combined.columns:
        combined[_MACRO_MS] = pd.to_numeric(combined[_MACRO_MS], errors="coerce")
        combined.rename(columns={_MACRO_MS: _MACRO_S}, inplace=True)
        combined[_MACRO_S] = combined[_MACRO_S] / 1000.0

    ds = DataSource()
    ds.data = combined.reset_index(drop=True)
    logging.info("Burst load complete: %d rows from %s", len(ds.data), path.name)
    return ds


def _burst_frames(
    path: pathlib.Path, table: Optional[str]
) -> tuple[list[pd.DataFrame], list[str]]:
    """Return the current burst table and its per-burst companions, as frames.

    "Current" has to be decided, not assumed. Re-running a search with a
    *changed* setting adds an object rather than replacing one -- that is the
    point, the old result stays reachable -- so a container analysed three ways
    holds three objects all called ``bursts``, distinguished only by their
    settings hash. Reading every one of them and concatenating side by side
    lines up three unrelated analyses of different lengths against each other,
    which pandas will happily do, padding with NaN. The newest is taken instead
    (objects come back in write order), and only the tables *derived from that
    one* join it.
    """
    from chisurf.core.datastore import column_names
    from chisurf.core.fio.pto import Measurement

    frames: list[pd.DataFrame] = []
    names: list[str] = []
    with Measurement.open(path, writable=False) as measurement:

        def _grain(uid: int) -> str:
            return measurement.tag(uid, "_mmfdb_artifact.row_grain")

        def _frame(obj) -> Optional[pd.DataFrame]:
            try:
                store = measurement.get_store(obj.uid)
            except Exception:  # noqa: BLE001
                logging.debug("could not read %r from %s", obj.name, path, exc_info=True)
                return None
            built = pd.DataFrame(
                {name: _column(store, name) for name in column_names(store)}
            )
            return None if built.empty else built

        def _is_candidate(obj) -> bool:
            if table is not None:
                return obj.name == table
            return (
                _grain(obj.uid) == _BURST_GRAIN
                and measurement.tag(obj.uid, "_mmfdb_operation.operation_type") == _SEARCH
            )

        candidates = [obj for obj in measurement.artifacts() if _is_candidate(obj)]
        if not candidates:
            return [], []
        primary = candidates[-1]
        if len(candidates) > 1:
            logging.info(
                "%s holds %d burst searches; using the most recent (settings %s)",
                path.name,
                len(candidates),
                measurement.tag(primary.uid, "_mmfdb_operation.settings_hash")[:8],
            )
        built = _frame(primary)
        if built is None:
            return [], []
        frames.append(built)
        names.append(primary.name)

        for obj in measurement.artifacts():
            if obj.uid == primary.uid or _grain(obj.uid) != _BURST_GRAIN:
                continue
            if primary.uid not in measurement.parents(obj.uid):
                continue
            companion = _frame(obj)
            if companion is None or len(companion) != len(built):
                continue
            frames.append(companion)
            names.append(obj.name)
    return frames, names


def _column(store: Any, name: str):
    """Return one column as something pandas can hold, numbers stayed numbers."""
    import numpy as np

    return np.asarray(store[name])
