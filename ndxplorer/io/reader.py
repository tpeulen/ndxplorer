# reader.py — NDXplorer Reader Module

from __future__ import annotations
from typing import Callable, List, Union, Optional, TextIO, Dict, Tuple
import pathlib
import os
import tempfile
import zipfile
import io
import shutil
import re
import json
import pickle

import numpy as np

try:
    from ..logging_config import logging
except Exception:  # pragma: no cover
    import logging  # type: ignore

from ..core.data_source import DataSource, float_column, store_from_columns, store_with_columns
from ..settings import get_settings_path, ensure_default_settings
from . import tables

import tttrlib

# No Qt here. Reading is library work: this module used to raise modal
# message boxes, build its own QApplication and pump the event loop from
# inside a read, which wedges any headless run the moment one of those
# dialogs appears and has nowhere to be clicked. Problems are logged, and
# the GUI reports progress through ``start_read_burst_analysis_async``,
# which already hands it ``on_success`` / ``on_error``.

# Import async loading components
from .async_loader import DataLoadTask, DataLoadResult, run_task
from .file_metadata_cache import get_metadata_cache


"""
NDXplorer Reader Module

Every table is read by tttrlib into a :class:`tttrlib.DataStore`:

- Delimiter and header autodetection for text-like files (.bur/.csv/.txt/.dat),
  zipped or not. A layout tttrlib's CSV reader does not take directly --
  whitespace alignment, a decimal comma, lines before the header, no header --
  is rewritten as a tab-delimited text with a header first.
- MSVC NaN/Inf spellings (e.g., 1.#INF, -1.#IND00e+000, 1.#QNAN) read as numbers.
- "Selector zips" (loose .bur) and full MFD zips.
- HDF5 preferred when present; otherwise BUR plus companions, side by side.
- Macro time concatenated across files, converted to seconds and named
  "Mean Macro Time (s)".
"""

# ----------------------------- constants -------------------------------------

FILL_MISSING_VALUE = -1.0

_TEXT_EXTS = (".bur", ".csv", ".txt", ".dat")
_HDF5_EXTS = (".h5", ".hdf5")

_DEFAULT_BURST_EXTRA_ENDINGS: List[str] = ["bg4", "br4", "by4", "bv4", "td4", "2c4"]

#: Keys of a detected text layout; a cached layout lacking one is detected again.
_FORMAT_KEYS = ("delimiter", "header_line", "data_start", "decimal_comma", "width")

def _discover_burst_extra_endings(base_path: pathlib.Path) -> List[str]:
    """Companion endings to merge beside each ``.bur`` in *base_path*.

    The known ``…4`` family unioned with any sibling directory whose name ends in
    ``4`` (so new ``…4`` companions like ``2c4`` merge with no code change). The
    base burst directories (``bi4_bur`` / ``bur``) do not end in ``4`` and so are
    never mistaken for a companion.
    """
    endings = list(_DEFAULT_BURST_EXTRA_ENDINGS)
    try:
        for child in base_path.iterdir():
            name = child.name.lower()
            if child.is_dir() and name.endswith("4") and name not in endings:
                endings.append(name)
    except Exception:
        pass
    return endings

# ----------------------------- utils -----------------------------------------

def _zip_contains_any(zip_path: str, exts: tuple[str, ...]) -> bool:
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            names = [n.lower() for n in zf.namelist()]
        return any(n.endswith(ext) for ext in exts for n in names)
    except Exception as e:
        logging.debug("Zip inspect failed for '%s': %s", zip_path, e)
        return False


def _get_burst_additional_endings() -> List[str]:
    """Return extra burst-result endings from settings, with a safe default.

    Reads ``burst_additional_endings`` from ``mfd.settings.json`` in the
    ndxplorer settings folder. Falls back to ``_DEFAULT_BURST_EXTRA_ENDINGS``
    on any error or if the key is missing/invalid.
    """

    endings: Optional[List[str]] = None

    try:
        # Ensure default settings exist and resolve the settings path
        try:
            ensure_default_settings()
        except Exception:
            pass

        settings_path = None
        try:
            settings_path = get_settings_path()
        except Exception:
            settings_path = None

        if settings_path is not None:
            cfg_path = settings_path / "mfd.settings.json"
            if cfg_path.is_file():
                with cfg_path.open("r", encoding="utf-8") as f:
                    cfg = json.load(f)
                raw = cfg.get("burst_additional_endings")
                if isinstance(raw, list):
                    cleaned: List[str] = []
                    for item in raw:
                        s = str(item).strip().lower()
                        if not s:
                            continue
                        cleaned.append(s)
                    if cleaned:
                        endings = cleaned
    except Exception as e:  # pragma: no cover - robust against config issues
        try:
            logging.debug("Failed to load burst_additional_endings from settings: %s", e)
        except Exception:
            pass

    # Union the built-in defaults with any user-configured endings, so a stale
    # settings file (e.g. one predating a newly-added companion like ``2c4``)
    # still picks up the new default rather than shadowing it.
    result = list(_DEFAULT_BURST_EXTRA_ENDINGS)
    for ending in endings or []:
        if ending not in result:
            result.append(ending)
    return result


# ----------------------------- core API --------------------------------------

def read_burst_analysis(
    base_path: Union[str, pathlib.Path],
    skip_nth_row: int = 2,
    additional_endings: Optional[List[str]] = None,
    drop_last_column: bool = True
) -> DataSource:
    """
    Read burst analysis from folder or zip.

    Supports:
      1) Regular dirs with bi4_bur / bur (+ …4 companions: bg4/br4/by4/bv4/td4/2c4).
      2) Zipped MFD folders with the standard directory structure.
      3) "Selector zip" with loose .bur files (will be normalized to temp/bi4_bur).

    - Auto-detects delimiters for .bur and extras (no hardcoded tab).
    - Concatenates macro time across files → seconds; column renamed to "Mean Macro Time (s)".
    """
    base_path = pathlib.Path(base_path)

    # A measurement container holds the bursts *and* the photons they were found
    # in, so there is no folder to look inside. Dispatched before anything else
    # because everything below is about the text layout.
    from ndxplorer.io import pto_reader

    if pto_reader.is_container(base_path):
        return pto_reader.read_container(base_path)

    if additional_endings is None:
        # Settings *and* whatever the folder actually contains. The configured
        # list was the only source, so a companion nobody had thought to add to
        # mfd.settings.json was silently dropped even though the folder was
        # sitting right there — a burst folder should load everything it holds.
        # Union, so a user's configured ending is never lost either.
        configured = _get_burst_additional_endings()
        discovered = _discover_burst_extra_endings(base_path)
        additional_endings = list(dict.fromkeys([*configured, *discovered]))

    if base_path.is_file() and base_path.suffix.lower() == ".zip":
        # Try "selector zip" path first (loose .bur files)
        try:
            with zipfile.ZipFile(base_path, "r") as zf:
                all_files = zf.namelist()
                logging.info("Zip contains %d entries", len(all_files))
                bur_files = [f for f in all_files if f.lower().endswith(".bur")]
                if bur_files:
                    with tempfile.TemporaryDirectory() as tdir:
                        tpath = pathlib.Path(tdir)
                        bur_dir = tpath / "bi4_bur"
                        bur_dir.mkdir(parents=True, exist_ok=True)

                        # Extract .bur to /bi4_bur
                        for f in bur_files:
                            zf.extract(f, tpath)
                            src = tpath / f
                            dst = bur_dir / src.name
                            if src != dst:
                                dst.parent.mkdir(parents=True, exist_ok=True)
                                shutil.move(str(src), str(dst))

                        # Extract extras into /<ending>
                        for ending in additional_endings:
                            extra = [f for f in all_files if f.lower().endswith(f".{ending}")]
                            if not extra:
                                continue
                            ed = tpath / ending
                            ed.mkdir(parents=True, exist_ok=True)
                            for f in extra:
                                zf.extract(f, tpath)
                                src = tpath / f
                                dst = ed / src.name
                                if src != dst:
                                    shutil.move(str(src), str(dst))

                        return _process_burst_analysis_dir(
                            tpath, skip_nth_row, additional_endings, drop_last_column
                        )
        except Exception as e:
            logging.info("Direct selector-zip processing failed: %s. Falling back.", e)

        # Fallback: extract entire zip and search for MFD structure
        with tempfile.TemporaryDirectory() as tdir:
            tpath = pathlib.Path(tdir)
            with zipfile.ZipFile(base_path, "r") as zf:
                zf.extractall(tpath)

            candidates = [d for d in tpath.iterdir() if d.is_dir()]
            if len(candidates) == 1:
                mfd_dir = candidates[0]
            else:
                mfd_dir = None
                for d in candidates:
                    if (d / "hdf5").exists() or (d / "bi4_bur").exists() or (d / "bur").exists():
                        mfd_dir = d
                        break
                if mfd_dir is None:
                    mfd_dir = tpath

            return _process_burst_analysis_dir(
                mfd_dir, skip_nth_row, additional_endings, drop_last_column
            )

    # Regular dir
    return _process_burst_analysis_dir(
        base_path, skip_nth_row, additional_endings, drop_last_column
    )


def start_read_burst_analysis_async(
    base_path: Union[str, pathlib.Path],
    skip_nth_row: int = 2,
    additional_endings: Optional[List[str]] = None,
    drop_last_column: bool = True,
    on_success: Callable[["DataSource"], None] = None,
    on_error: Optional[Callable[[str], None]] = None,
) -> None:
    """
    Start asynchronous loading of burst analysis data.
    
    In GUI mode, runs in background thread to prevent UI blocking.
    In CLI mode, runs synchronously.
    
    Parameters
    ----------
    base_path : Union[str, pathlib.Path]
        Path to burst analysis directory or zip.
    skip_nth_row : int, optional
        Skip every Nth row, by default 2.
    additional_endings : Optional[List[str]], optional
        Extra file endings to process, by default None (uses settings).
    drop_last_column : bool, optional
        Trim the trailing placeholder column the writers append to the burst
        tables (only empty/``Unnamed`` columns are removed, never real data),
        by default True.
    on_success : Callable[[DataSource], None], optional
        Callback when loading succeeds, by default None.
    on_error : Optional[Callable[[str], None]], optional
        Callback when loading fails, by default None.
    """
    if on_success is None:
        on_success = lambda ds: None
    if on_error is None:
        on_error = lambda msg: logging.error("Async load failed: %s", msg)
    
    task = DataLoadTask(
        description=f"Loading burst analysis from {base_path}",
        load_callable=lambda: read_burst_analysis(
            base_path, skip_nth_row, additional_endings, drop_last_column
        ),
        on_success=on_success,
        on_error=on_error,
    )
    
    run_task(task)


def _process_burst_analysis_dir(
    base_path: pathlib.Path,
    skip_nth_row: int = 2,
    additional_endings: Optional[List[str]] = None,
    drop_last_column: bool = True
) -> DataSource:
    """
    Process a burst analysis directory. Prefer HDF5 (hdf5/*.h5|*.hdf5), else read BUR files.
    """
    import time as _time
    t0 = _time.perf_counter()

    if additional_endings is None:
        additional_endings = _discover_burst_extra_endings(base_path)

    # Prefer HDF5
    hdf5_dir = base_path / "hdf5"
    if hdf5_dir.is_dir():
        h5 = sorted([p for p in hdf5_dir.iterdir() if p.suffix.lower() in _HDF5_EXTS])
        if h5:
            logging.info("Found HDF5: %s", h5[0])
            return read_mfd_hdf5([str(h5[0])])

    # BUR path
    dir_main = base_path / "bi4_bur"
    dir_fallback = base_path / "bur"
    if dir_main.is_dir():
        bur_files = sorted(dir_main.glob("*.bur")) or sorted(dir_fallback.glob("*.bur"))
    else:
        bur_files = sorted(dir_fallback.glob("*.bur"))

    if not bur_files:
        raise FileNotFoundError("No .bur files in 'bi4_bur' or 'bur'.")

    n_files = len(bur_files)
    logging.info("Processing %d .bur files from %s", n_files, base_path)

    pieces: List["tttrlib.DataStore"] = []
    macro_time_offset_ms = 0.0
    macro_col_ms = "Mean Macro Time (ms)"
    macro_col_s  = "Mean Macro Time (s)"

    # Cache format detection from first file for speed (all .bur files share format)
    bur_format_cache: Optional[Dict] = None
    extra_format_cache: Dict[str, Dict] = {}  # ending -> layout

    for i, bur in enumerate(bur_files, start=1):
        # Detect format from first file, reuse for rest
        if bur_format_cache is None:
            bur_format_cache = _detect_format(bur)
        main = _read_text_table_auto(bur, cached_format=bur_format_cache)
        # Same rule as the companions below: the trailing tab on the header line
        # is already resolved by the parser, so a blanket drop-last would delete
        # a real measurement column ("Red Count Rate (KHz)", "S delayed yellow
        # (kHz)") and with it every derived red/FRET quantity.
        if drop_last_column:
            tables.drop_trailing_empty_columns(main)

        parts = [main]

        # extras beside this bur (by stem) in base_path/<ending>/*.ending
        stem = bur.stem
        for ending in additional_endings:
            extra = base_path / ending / f"{stem}.{ending}"
            if not extra.exists():
                continue
            # Cache format per extra file type
            if ending not in extra_format_cache:
                extra_format_cache[ending] = _detect_format(extra)
            companion = _read_text_table_auto(extra, cached_format=extra_format_cache[ending])
            if companion.n_columns() == 0:
                continue
            # For companions, drop only the trailing empty/placeholder column (the
            # writers append one so a blanket drop-last would remove real data,
            # e.g. a bv4's "Proximity Ratio Std" or a 2c4's "FRET-2CDE").
            if drop_last_column:
                tables.drop_trailing_empty_columns(companion)
            parts.append(companion)

        # The macro time of the file's last burst, before any row is skipped:
        # the next file's macro times continue from it.
        last_ms = None
        for part in reversed(parts):
            index = part.find(macro_col_ms)
            if index >= 0 and part.n_rows() > 0:
                last_ms = float(float_column(part, index)[-1])
                break

        combined = tables.concat_columns(parts)

        # skip every Nth row
        n_rows = int(combined.n_rows())
        if skip_nth_row > 1 and n_rows and combined.n_columns():
            keep = np.flatnonzero(np.arange(n_rows) % skip_nth_row != 0)
            combined = combined.take(keep)

        # Every column numeric except the ones naming a file.
        tables.as_numeric(combined, keep_text=tables.is_filename_column)

        # concatenate macro time (ms → s) and rename
        index = combined.find(macro_col_ms)
        if index >= 0 and combined.n_rows() > 0:
            seconds = (float_column(combined, index) + macro_time_offset_ms) / 1000.0
            existing = combined.find(macro_col_s)
            if existing >= 0:
                combined.remove_column(existing)
                index = combined.find(macro_col_ms)
            column = combined.column(index)
            column.clear_mask()
            column.set_numpy(seconds)
            column.set_name(macro_col_s)
            macro_time_offset_ms += 0.0 if last_ms is None else last_ms

        pieces.append(combined)

    t1 = _time.perf_counter()
    logging.info("Read %d files in %.2fs, concatenating...", n_files, t1 - t0)

    final = tables.concat_rows(pieces)
    tables.as_numeric(final, keep_text=tables.is_filename_column)

    t2 = _time.perf_counter()
    logging.info("Burst load complete: %d rows, %.2fs total (concat %.2fs)",
                 final.n_rows(), t2 - t0, t2 - t1)

    return DataSource(final)


#: Suffixes a stored chain can carry: tab-separated text, or an HDF5 table.
#: A long run makes the difference matter -- a float64 costs ~25 characters as
#: text and 8 in HDF5, before compression.
_CHAIN_SUFFIXES = (".er4", ".h5", ".hdf5")


def _read_chain_store(filename: str, sep: str = '\t') -> "tttrlib.DataStore":
    """Load one chain file, text or HDF5, as a store of draws.

    Parameters
    ----------
    filename : str
        Path to a ``.er4`` text chain or a columnar HDF5 chain table.
    sep : str
        Column separator of the text format.

    Returns
    -------
    tttrlib.DataStore
        One row per draw.
    """
    path = pathlib.Path(filename)
    if path.suffix.lower() in (".h5", ".hdf5"):
        if is_ensemble_sampling_hdf5(str(path)):
            source = read_ensemble_sampling_hdf5(str(path))
            if source.empty:
                raise ValueError("no sampled states in the file")
            return source.store
        store = read_hdf5_store(path)
        if store is None:
            store = read_hdf5_store(path, "/results")
        if store is None:
            raise ValueError("no columnar HDF5 table in the file")
        return store
    return tttrlib.read_csv(str(path), delimiter=sep, has_header=True)


def read_csv_sampling(filenames: List[str], sep: str = '\t') -> DataSource:
    """
    Read ChiSurf sampling files (.er4).
    Multiple files (chains) are concatenated by rows to form a single distribution.

    Each file is one chain of the same posterior, so the rows are stacked. Two
    columns are added alongside the parameters: ``chain``, the index of the file
    a draw came from, and ``draw``, its position within that chain. Without them
    the stack is a bag of numbers -- the draws cannot be put back in order, the
    chains cannot be told apart, and neither a trace nor a per-chain comparison
    (the thing that says whether the runs agree) can be plotted.
    """
    if not filenames:
        return DataSource()

    chains: List["tttrlib.DataStore"] = []
    skipped: List[str] = []
    expected_columns: Optional[set] = None
    for fn in filenames:
        try:
            raw = _read_chain_store(fn, sep)
            # Normalize column names (strip whitespace and leading #)
            names = [str(raw.column(i).name()).strip().lstrip('#').strip()
                     for i in range(raw.n_columns())]
            store = tables.rename_columns(raw, names)
        except Exception as e:
            logging.warning(f"Could not read sampling file {fn}: {e}")
            skipped.append(str(fn))
            continue

        if store.n_rows() == 0 or store.n_columns() < 2:
            # Not a chain. Concatenated anyway it would contribute a column of
            # its own that every other chain is missing, and the missing values
            # are then filled -- inventing draws that were never sampled.
            logging.warning(f"Not a sampling chain, skipping: {fn}")
            skipped.append(str(fn))
            continue

        columns = set(names) - {'chain', 'draw'}
        if expected_columns is None:
            expected_columns = columns
        elif columns != expected_columns:
            logging.warning(
                "%s samples %s, the other chains sample %s -- skipping it "
                "rather than filling in the difference",
                fn, sorted(columns - expected_columns) or "fewer parameters",
                sorted(expected_columns),
            )
            skipped.append(str(fn))
            continue

        n_draws = int(store.n_rows())
        if store.find('chain') < 0:
            store.add('chain', np.full(n_draws, len(chains), dtype=np.int64))
        if store.find('draw') < 0:
            store.add('draw', np.arange(n_draws, dtype=np.int64))
        chains.append(store)

    if skipped:
        # One line the user can actually notice: a chain silently missing from a
        # posterior is a posterior that is quietly wrong.
        logging.warning(
            "read %d of %d sampling chains; skipped: %s",
            len(chains), len(filenames), ", ".join(pathlib.Path(f).name for f in skipped),
        )

    if not chains:
        return DataSource()

    combined = tables.concat_rows(chains)
    tables.as_numeric(combined, fill=FILL_MISSING_VALUE)
    return DataSource(combined)


def _sampling_chain_files(folder: pathlib.Path) -> List[pathlib.Path]:
    """Return the ``.er4`` chain files directly inside a sampling run folder.

    A run folder holds its chains in a ``chains/`` subdirectory; a folder of
    loose ``.er4`` files is accepted too.

    A run writes ``<name>.partial.er4`` while it is going and deletes it once
    ``<name>.er4`` is complete. A partial is a *prefix* of its final chain, so
    reading both counts those draws twice and shows them as two chains that
    agree suspiciously well. The partial is therefore dropped whenever its final
    exists, and kept when it does not -- a cancelled run leaves nothing else.
    """
    def _chains_in(directory: pathlib.Path) -> List[pathlib.Path]:
        """Return the chain files of one directory, of either format."""
        return sorted(
            f for f in directory.glob("*")
            if f.suffix.lower() in _CHAIN_SUFFIXES or f.name.endswith(".partial.er4")
        )

    files = _chains_in(folder / "chains") or _chains_in(folder)
    def _is_partial(f: pathlib.Path) -> bool:
        """Whether a chain file is the in-progress copy of another."""
        return ".partial." in f.name

    finished = {f.name for f in files if not _is_partial(f)}
    superseded = {
        f for f in files
        if _is_partial(f) and f.name.replace(".partial.", ".", 1) in finished
    }
    for f in sorted(superseded):
        logging.info("ignoring %s: its finished chain is present", f.name)
    return [f for f in files if f not in superseded]


def read_sampling_folder(path: str) -> DataSource:
    """
    Read a ChiSurf sampling folder.

    ``sample_fit`` writes ``<target>/<timestamp>/chains/*.er4``, so the folder
    the user chose when starting the run holds *runs*, not chains. Both are
    accepted: a run folder is read directly, and a folder of runs resolves to
    its most recent one (the timestamps sort chronologically) with the choice
    logged. Runs are deliberately **not** merged -- separate timestamps are
    separate sampling sessions, possibly of different fits, and stacking them
    would silently pool two different posteriors into one cloud.
    """
    p = pathlib.Path(path)

    er4_files = _sampling_chain_files(p)
    if not er4_files:
        runs = sorted(
            d for d in p.iterdir() if d.is_dir() and _sampling_chain_files(d)
        ) if p.is_dir() else []
        if runs:
            chosen = runs[-1]
            if len(runs) > 1:
                logging.info(
                    "%d sampling runs in %s; opening the most recent (%s)",
                    len(runs), p, chosen.name,
                )
            er4_files = _sampling_chain_files(chosen)

    if not er4_files:
        logging.warning(f"No .er4 files found in {p}")
        return DataSource()

    return read_csv_sampling([str(f) for f in er4_files])


class _NamesOnlyUnpickler(pickle.Unpickler):
    """Unpickler that decodes plain data and refuses everything else.

    Sampling metadata is stored pickled inside the HDF5 attributes. Opening a
    file must never run code that the file chose, so no class -- not one --
    may be resolved: a list of strings needs none, and anything that does need
    one is not metadata we are willing to read.
    """

    def find_class(self, module, name):
        """Refuse every global lookup, which is what makes this safe."""
        raise pickle.UnpicklingError(
            f"refusing to load {module}.{name} out of a data file"
        )


def _unpickle_plain(value):
    """Decode a pickled HDF5 attribute, or return ``None`` if it is not plain data.

    Parameters
    ----------
    value
        Raw attribute value as h5py returns it.

    Returns
    -------
    object or None
        The decoded value, or ``None`` when it is absent, not a pickle, or
        contains anything beyond plain data.
    """
    if value is None:
        return None
    raw = value.tobytes() if hasattr(value, "tobytes") else value
    if not isinstance(raw, (bytes, bytearray)):
        return raw
    try:
        return _NamesOnlyUnpickler(io.BytesIO(raw)).load()
    except Exception as e:
        logging.debug("could not decode a pickled attribute: %s", e)
        return None


def is_ensemble_sampling_hdf5(filename: str) -> bool:
    """Return ``True`` for an HDF5 file holding an ensemble-sampler chain.

    Parameters
    ----------
    filename : str
        Path to test.

    Returns
    -------
    bool
        Whether the file carries an ``mcmc/chain`` dataset.
    """
    try:
        import h5py
    except ImportError:
        return False
    try:
        with h5py.File(filename, "r") as f:
            return "mcmc" in f and "chain" in f["mcmc"]
    except Exception:
        return False


def read_ensemble_sampling_hdf5(filenames: Union[str, List[str]]) -> DataSource:
    """Read an ensemble-sampler chain written to HDF5 (ucfret's sampling output).

    The chain is stored as ``mcmc/chain`` with shape ``(n_steps, n_walkers,
    n_dim)`` and ``mcmc/log_prob`` with ``(n_steps, n_walkers)``. Walkers are
    the chains of an ensemble sampler, so every draw becomes a row carrying the
    walker it came from (``chain``) and its step (``draw``) -- without those the
    stack cannot be put back in order or compared walker by walker.

    Only the steps actually written are read: the storage is grown in whole
    chunks and, when the run thins, its tail is left unwritten. Those rows are
    zeros, and a zero is not a draw.

    Parameters
    ----------
    filenames : str or list of str
        One or more sampling files. Several files are stacked, with the walker
        index offset per file so the chains stay distinguishable.

    Returns
    -------
    DataSource
        Columns: one per parameter (named from the file where possible),
        ``log_prob``, ``chain`` and ``draw``.
    """
    try:
        import h5py
    except ImportError:
        logging.warning("h5py is required to read sampling HDF5 files")
        return DataSource()

    if isinstance(filenames, (str, pathlib.Path)):
        filenames = [str(filenames)]
    if not filenames:
        return DataSource()

    chains = []
    chain_offset = 0
    for fn in filenames:
        try:
            with h5py.File(str(fn), "r") as f:
                group = f["mcmc"]
                n_written = int(group.attrs.get("iteration", len(group["chain"])))
                chain = np.asarray(group["chain"][:n_written])
                log_prob = np.asarray(group["log_prob"][:n_written])
                names = _unpickle_plain(f["blobs"].attrs.get("parameter_names")) \
                    if "blobs" in f else None
        except Exception as e:
            logging.warning(f"Could not read sampling file {fn}: {e}")
            continue

        if chain.ndim != 3 or chain.size == 0:
            logging.warning(f"{fn} holds no sampled states")
            continue

        n_steps, n_walkers, n_dim = chain.shape
        if not (isinstance(names, (list, tuple)) and len(names) == n_dim
                and all(isinstance(n, str) for n in names)):
            names = [f"p{i}" for i in range(n_dim)]

        draws = chain.reshape(-1, n_dim)
        columns = {name: np.ascontiguousarray(draws[:, i]) for i, name in enumerate(names)}
        columns["log_prob"] = log_prob.reshape(-1)
        # ``reshape`` runs the walker axis fastest, so the walker index cycles
        # and the step index repeats.
        columns["chain"] = np.tile(np.arange(n_walkers), n_steps) + chain_offset
        columns["draw"] = np.repeat(np.arange(n_steps), n_walkers)
        chain_offset += n_walkers
        chains.append(store_from_columns(columns))

    if not chains:
        return DataSource()

    combined = tables.concat_rows(chains)
    tables.as_numeric(combined, fill=FILL_MISSING_VALUE)
    return DataSource(combined)


def read_hdf5_store(filename: Union[str, pathlib.Path], group: str = "/"):
    """A columnar HDF5 table as a :class:`tttrlib.DataStore`, or ``None``.

    The short path, and the one chisurf writes for: an HDF5 group holding one
    1-D dataset per column is the layout a DataStore already has, so the file
    becomes the store the gates are evaluated in and the histograms fill out of
    -- with no conversion, and no second copy of the
    table at the moment it is largest. Types survive too: a float32 column stays
    float32 and an integer column stays an integer.

    ``None`` means the file is not that shape -- a PyTables table written by
    a data-frame library, a Photon-HDF5 measurement -- and the caller decides
    what else the file may be.
    """
    try:
        columns = tttrlib.read_hdf5_table_columns(str(filename), group)
    except Exception as exc:
        logging.debug("[read] not a columnar HDF5 table (%s)", exc)
        return None
    if len(columns) < 1:
        return None
    try:
        store = tttrlib.read_hdf5(str(filename), group)
    except Exception as exc:
        logging.info("[read] tttrlib declined %s (%s)",
                     pathlib.Path(filename).name, exc)
        return None
    return store if store.n_rows() > 0 else None


def read_mfd_hdf5(filenames: List[str], merge_mode: str = "columns") -> DataSource:
    """
    Read MFD HDF5 files (supports zipped HDF5).
    If a .zip has no .h5/.hdf5, fallback to read_burst_analysis(zip).

    :param merge_mode: how several files combine -- "columns" puts them
        side by side (they describe the same bursts), "rows" stacks them (they
        are separate measurements). Same meaning as everywhere else.
    """
    if not filenames:
        return DataSource()

    first = str(filenames[0])

    # One file, written column per column: it IS a store, so take it as one.
    if len(filenames) == 1 and not first.lower().endswith(".zip"):
        store = read_hdf5_store(first)
        if store is not None:
            logging.info("[read] %s: %d rows x %d columns straight into a store",
                         pathlib.Path(first).name, store.n_rows(), store.n_columns())
            return DataSource(store)

    if first.lower().endswith(".zip") and not _zip_contains_any(first, _HDF5_EXTS):
        logging.info("No HDF5 in zip; treating as burst analysis: %s", first)
        return read_burst_analysis(first)

    if is_ensemble_sampling_hdf5(first):
        logging.info("Sampling chain detected in %s", first)
        return read_ensemble_sampling_hdf5([str(f) for f in filenames])

    base = read_hdf5_file(first)
    row_count = int(base.n_rows())

    if len(filenames) == 1:
        return DataSource(tables.numeric_columns_only(base))

    combined = base
    for fn in filenames[1:]:
        store = read_hdf5_file(fn)
        own = [combined.column(i).name() for i in range(combined.n_columns())]
        other = [store.column(i).name() for i in range(store.n_columns())]
        if merge_mode == "rows":
            common = sorted(set(own).intersection(other))
            if not common:
                logging.warning(
                    "%s shares no columns with the first file. Skipping.", fn)
                continue
            combined = tables.concat_rows([store_with_columns(combined, common),
                                           store_with_columns(store, common)],
                                          join="inner")
            continue
        if int(store.n_rows()) != row_count:
            logging.warning(
                "File %s has %d rows, expected %d. Skipping.",
                fn, store.n_rows(), row_count,
            )
            continue
        combined = tables.concat_columns([combined, store])

    return DataSource(tables.numeric_columns_only(combined))


def read_hdf5_file(filename: str) -> "tttrlib.DataStore":
    """
    Read a single columnar HDF5 table (optionally inside a .zip).
    Tries the group '/results' first, else the file root.

    Raises
    ------
    ValueError
        When the file holds no columnar table. A PyTables table written by a
        data-frame library is not one; it has to be rewritten as columns.
    """
    def _read_one(h5_path: pathlib.Path) -> "tttrlib.DataStore":
        store = read_hdf5_store(h5_path, "/results")
        if store is None:
            store = read_hdf5_store(h5_path, "/")
        if store is None:
            raise ValueError(
                f"{h5_path.name} holds no columnar HDF5 table (one 1-D dataset "
                "per column, at the root or under /results)")
        return store

    p = pathlib.Path(filename)
    if p.suffix.lower() == ".zip":
        with zipfile.ZipFile(p, "r") as zf:
            members = [f for f in zf.namelist() if f.lower().endswith(_HDF5_EXTS)]
            if not members:
                raise FileNotFoundError(f"No HDF5 files in zip: {filename}")
            target = members[0]
            with tempfile.TemporaryDirectory() as tdir:
                tpath = pathlib.Path(tdir)
                zf.extract(target, tpath)
                return _read_one(tpath / target)
    return _read_one(p)


def read_csv(filenames: List[str]) -> DataSource:
    """
    Read one or multiple CSV-like files.
    - Per-file autodetection + normalization (MSVC NaN/Inf)
    - Same number of columns: stack rows under the first file's names; same
      number of rows: put the columns side by side (a repeated name keeps the
      first); otherwise only files with the first file's row count are merged
      side by side.
    """
    if not filenames:
        return DataSource()

    stores: List["tttrlib.DataStore"] = []
    for fn in filenames:
        try:
            stores.append(read_csv_file(fn))
        except Exception as e:
            logging.warning("Could not read file %s: %s", fn, e)

    if not stores:
        return DataSource()

    if len(stores) == 1:
        return DataSource(tables.numeric_columns_only(stores[0]))

    ncols = [s.n_columns() for s in stores]
    nrows = [s.n_rows() for s in stores]

    if len(set(ncols)) == 1:
        base_cols = [stores[0].column(i).name() for i in range(stores[0].n_columns())]
        combined = tables.concat_rows([tables.rename_columns(s, base_cols) for s in stores])
    else:
        if len(set(nrows)) != 1:
            logging.warning(
                "Files share neither column count nor row count; merging "
                "column-wise the files with the first file's row count."
            )
        combined = tables.concat_columns(stores)

    combined = tables.numeric_columns_only(combined)
    tables.as_numeric(combined, fill=FILL_MISSING_VALUE)
    return DataSource(combined)


def start_read_csv_async(
    filenames: List[str],
    on_success: Callable[["DataSource"], None] = None,
    on_error: Optional[Callable[[str], None]] = None,
) -> None:
    """
    Start asynchronous loading of CSV data.
    
    In GUI mode, runs in background thread to prevent UI blocking.
    In CLI mode, runs synchronously.
    
    Parameters
    ----------
    filenames : List[str]
        List of CSV file paths to read.
    on_success : Callable[[DataSource], None], optional
        Callback when loading succeeds, by default None.
    on_error : Optional[Callable[[str], None]], optional
        Callback when loading fails, by default None.
    """
    if on_success is None:
        on_success = lambda ds: None
    if on_error is None:
        on_error = lambda msg: logging.error("Async load failed: %s", msg)
    
    task = DataLoadTask(
        description=f"Loading CSV files: {filenames}",
        load_callable=lambda: read_csv(filenames),
        on_success=on_success,
        on_error=on_error,
    )
    
    run_task(task)


# ----------------------------- helpers ---------------------------------------

def read_csv_file(filename: str) -> "tttrlib.DataStore":
    """
    Read a CSV-like text file or a .zip containing exactly one CSV-like text file.
    - Autodetect delimiter (, \\t ; or whitespace).
    - Choose the first full-width *texty* row as header when available.
    - MSVC NaN/Inf/IND/QNAN/SNAN spellings read as numbers.
    - Every column numeric (text that is not a number → NaN), NaNs filled
      with FILL_MISSING_VALUE.
    """
    p = pathlib.Path(filename)

    if p.suffix.lower() == ".zip":
        with zipfile.ZipFile(p, "r") as zf:
            inner = _find_first_member(zf, _TEXT_EXTS)
            if inner is None:
                raise ValueError(f"No CSV-like files found in zip: {filename}")
            with tempfile.TemporaryDirectory() as tdir:
                extracted = pathlib.Path(zf.extract(inner, tdir))
                store = _read_text_store(extracted, _detect_format(extracted, use_cache=False))
    else:
        store = _read_text_store(p, _detect_format(p))

    # A burst file's lines end in a delimiter: one more column, nameless and
    # empty. Kept, it filled with FILL_MISSING_VALUE and became a parameter
    # called "" -- which the axis choosers then offered and picked.
    tables.drop_trailing_empty_columns(store)
    names = [store.column(i).name() for i in range(store.n_columns())]
    logging.info("[read_csv_file] Read %d rows from %s", store.n_rows(), filename)
    logging.info("[read_csv_file] Columns: %s", ", ".join(names))

    tables.as_numeric(store, fill=FILL_MISSING_VALUE)
    return store


# --------------------- low-level text-table helpers --------------------------

def _is_plain_layout(layout: Dict) -> bool:
    """Whether tttrlib's CSV reader takes the file as it is.

    A plain layout is delimited by one character, uses a decimal point, and
    starts with its header (or with data, when there is no header).
    """
    header_line = layout["header_line"]
    return (
        layout["delimiter"] is not None
        and not layout["decimal_comma"]
        and (header_line == 0 or (header_line is None and layout["data_start"] == 0))
    )


def _normalised_text(path: pathlib.Path, layout: Dict) -> str:
    """The table in `path` as tab-delimited text with a header line.

    Lines before the header or data are dropped, whitespace alignment and the
    detected delimiter become tabs, a decimal comma becomes a point, and a file
    without a header gets the column positions as names.
    """
    delimiter = layout["delimiter"]
    width = int(layout["width"])
    header_line = layout["header_line"]
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        lines = f.read().splitlines()
    if header_line is not None:
        header = [t.strip() for t in _tokenize(lines[header_line], delimiter)]
        first = header_line + 1
    else:
        header = [str(i) for i in range(width)]
        first = int(layout["data_start"])
    width = len(header)
    out = ["\t".join(header)]
    for line in lines[first:]:
        tokens = [t.strip() for t in _tokenize(line, delimiter)]
        if not tokens:
            continue
        if layout["decimal_comma"]:
            tokens = [t.replace(",", ".") for t in tokens]
        tokens = (tokens + [""] * width)[:width]
        out.append("\t".join(tokens))
    return "\n".join(out) + "\n"


def _read_text_store(path: pathlib.Path, layout: Dict) -> "tttrlib.DataStore":
    """Read one text table with tttrlib, rewriting its layout first when it is not plain."""
    if _is_plain_layout(layout):
        has_header = layout["header_line"] == 0
        store = tttrlib.read_csv(str(path), delimiter=layout["delimiter"],
                                 has_header=has_header, use_float32=True)
        if not has_header:
            store = tables.rename_columns(store, [str(i) for i in range(store.n_columns())])
    else:
        with tempfile.TemporaryDirectory() as tdir:
            normalised = pathlib.Path(tdir) / (path.stem + ".tsv")
            normalised.write_text(_normalised_text(path, layout), encoding="utf-8")
            store = tttrlib.read_csv(str(normalised), delimiter="\t",
                                     has_header=True, use_float32=True)
    stripped = [store.column(i).name().strip() for i in range(store.n_columns())]
    if stripped != [store.column(i).name() for i in range(store.n_columns())]:
        store = tables.rename_columns(store, stripped)
    return store


def _read_text_table_auto(path: pathlib.Path, cached_format: Optional[Dict] = None) -> "tttrlib.DataStore":
    """
    Read a single text-like file (.bur/.csv/.txt/.dat) with layout autodetection.

    Parameters
    ----------
    path : pathlib.Path
        File to read.
    cached_format : Optional[Dict]
        A layout detected on an earlier file of the same kind. When reading with
        it fails, the layout is detected again and the dict updated in place, so
        the next file of that kind uses the new one.

    Trailing blank columns are dropped, and every column whose name does not
    name a file is made numeric.
    """
    import time as _time

    layout = dict(cached_format) if cached_format is not None else _detect_format(path)

    t0 = _time.perf_counter()
    while True:
        try:
            store = _read_text_store(path, layout)
            break
        except Exception as exc:
            if cached_format is not None:
                logging.warning("[read] Cached format failed for %s (%s). Re-detecting format.",
                                path.name, exc)
                layout = _detect_format(path, use_cache=False)
                cached_format.clear()
                cached_format.update(layout)
                cached_format = None
                continue
            raise
    t1 = _time.perf_counter()

    tables.drop_trailing_empty_columns(store)
    tables.as_numeric(store, keep_text=tables.is_filename_column)

    logging.debug("[read] %d rows, parse+convert=%.2fs", store.n_rows(), t1 - t0)
    return store


def _detect_format(path: pathlib.Path, use_cache: bool = True) -> Dict:
    """
    Detect the text layout of `path` (see :func:`_detect_table_format`).
    Uses the file metadata cache to avoid re-detection on subsequent loads.
    """
    cache = get_metadata_cache()
    if use_cache:
        cached_format = cache.get_cached_format(path)
        if cached_format is not None and all(k in cached_format for k in _FORMAT_KEYS):
            return cached_format

    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        head = _read_head_lines(f)
    layout = _detect_table_format(head)

    if use_cache:
        cache.cache_format(path, layout)
    return layout


def _find_first_member(zf: zipfile.ZipFile, exts: Tuple[str, ...]) -> Optional[str]:
    for name in zf.namelist():
        if name.lower().endswith(exts):
            return name
    return None


def _read_head_lines(file_like: TextIO, max_lines: int = 5000) -> List[str]:
    lines: List[str] = []
    for _ in range(max_lines):
        ln = file_like.readline()
        if not ln:
            break
        if isinstance(ln, bytes):
            try:
                ln = ln.decode("utf-8", errors="ignore")
            except Exception:
                ln = ln.decode("latin-1", errors="ignore")
        lines.append(str(ln))
    return lines


def _tokenize(s: str, delim: Optional[str]) -> List[str]:
    s = s.rstrip("\n")
    if not s.strip():
        return []
    return s.strip().split() if delim is None else s.strip().split(delim)


def _has_alpha(tokens: List[str]) -> bool:
    return any(any(c.isalpha() for c in t) for t in tokens)


def _detect_table_format(lines: List[str]) -> Dict:
    """
    Detect delimiter and header row from a sample of lines.

    Returns
    -------
    dict
        ``delimiter`` (a character, or None for whitespace alignment),
        ``header_line`` (index of the header line, or None), ``data_start``
        (index of the first data line), ``decimal_comma`` and ``width``
        (the number of columns).
    """
    N = min(len(lines), 5000)
    candidates = [",", "\t", ";"]
    has_comma_digits = any(re.search(r"\d,\d", ln) for ln in lines[:N])

    best = dict(score=-1.0, delim=None, complete_cols=0, first_idx=0, header_prev_idx=None, dec_comma=False)

    for delim in candidates:
        ncols: List[int] = []
        for i in range(N):
            toks = _tokenize(lines[i], delim)
            ncols.append(len(toks) if len(toks) >= 2 else 0)

        counts: Dict[int, int] = {}
        for c in ncols:
            if c >= 2:
                counts[c] = counts.get(c, 0) + 1
        if not counts:
            continue

        # pick most frequent width; tie → larger width
        complete_cols = max(sorted(counts.keys()), key=lambda c: (counts[c], c))
        try:
            first_complete = next(i for i, c in enumerate(ncols) if c == complete_cols)
        except StopIteration:
            continue

        header_prev_idx = None
        if first_complete > 0:
            prev = first_complete - 1
            prev_cols = ncols[prev]
            enough = max(2, complete_cols // 2)
            if prev_cols == 0:
                header_prev_idx = prev
            elif 2 <= prev_cols < complete_cols and prev_cols >= enough:
                header_prev_idx = prev
            if header_prev_idx is None and prev_cols == 0 and prev - 1 >= 0 and ncols[prev - 1] >= enough:
                header_prev_idx = prev - 1

        # score: run length of consistent rows * log(width)
        run_len = 0
        j = first_complete
        while j < N and ncols[j] == complete_cols:
            run_len += 1
            j += 1
        score = run_len * float(np.log(max(complete_cols, 2)))
        dec_flag = bool(has_comma_digits and (delim in (";", "\t", "|", None)))

        if score > best["score"]:
            best.update(score=score, delim=delim, complete_cols=complete_cols,
                        first_idx=first_complete, header_prev_idx=header_prev_idx, dec_comma=dec_flag)

    if best["complete_cols"] == 0:
        # Single-column fallback: the scan above requires >=2 columns, so a
        # legitimate one-column table (e.g. a 2c4 companion whose only column is
        # 'FRET-2CDE') would otherwise be read headerless with an integer column
        # name. Prefer tab when present, else whitespace; header detection below
        # then picks up the alpha first line.
        first_nonempty = next((i for i, ln in enumerate(lines[:N]) if ln.strip()), 0)
        delim1 = "\t" if any("\t" in ln for ln in lines[:N]) else None
        best.update(score=0.0, delim=delim1, complete_cols=1,
                    first_idx=first_nonempty, header_prev_idx=None)

    first_idx = best["first_idx"]
    header_prev_idx = best["header_prev_idx"]
    delim = best["delim"]
    complete_cols = best["complete_cols"]
    dec_comma = best["dec_comma"]

    # pick header: prefer first full-width *texty* row
    use_header_idx = None
    first_toks = _tokenize(lines[first_idx], delim)
    if len(first_toks) == complete_cols and _has_alpha(first_toks):
        use_header_idx = first_idx
    elif header_prev_idx is not None:
        prev_toks = _tokenize(lines[header_prev_idx], delim)
        if len(prev_toks) == complete_cols and _has_alpha(prev_toks):
            use_header_idx = header_prev_idx

    if use_header_idx is not None:
        data_start = use_header_idx + 1
        header_where = f"line {use_header_idx}"
    else:
        data_start = first_idx
        header_where = "none"

    layout: Dict = dict(
        delimiter=delim,
        header_line=use_header_idx,
        data_start=data_start,
        decimal_comma=bool(dec_comma),
        width=int(complete_cols),
    )
    sep_show = "<whitespace>" if delim is None else repr(delim)

    # debug log (compact) - only shown once per file type due to caching
    logging.info("[detect] sep=%s, width=%d, plain=%s, header=%s, data_start=%d",
                 sep_show, complete_cols, _is_plain_layout(layout), header_where, data_start)
    return layout
