# reader.py — NDXplorer Reader Module (drop-in replacement)

from __future__ import annotations
from typing import List, Union, Optional, BinaryIO, TextIO, Dict, Tuple
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
import pandas as pd
from pandas.errors import EmptyDataError

try:
    from ..logging_config import logging
except Exception:  # pragma: no cover
    import logging  # type: ignore

from ..core.data_source import DataSource
from ..settings import get_settings_path, ensure_default_settings

import tttrlib

try:
    from qtpy.QtWidgets import QApplication, QMessageBox
    from qtpy.QtCore import QCoreApplication, QThread
    from ..ui.progress_window import ProgressWindow
    _HAS_QT = True
except Exception:
    _HAS_QT = False
    QApplication = None
    QMessageBox = None
    QCoreApplication = None
    QThread = None
    ProgressWindow = None

# Import async loading components
from .async_loader import DataLoadTask, DataLoadWorker, DataLoadResult, run_task_inline
from .file_metadata_cache import get_metadata_cache


"""
NDXplorer Reader Module (fixed)

Key improvements:
- Delimiter autodetection for text-like files (.bur/.csv/.txt/.dat) incl. zipped.
- MSVC NaN/Inf token normalization (e.g., 1.#INF, -1.#IND00e+000, 1.#QNAN).
- Robust handling of “selector zips” (loose .bur) and full MFD zips.
- Prefer HDF5 if present; fallback to BUR+extras merge.
- Concatenate macro time across files, convert to seconds, rename to "Mean Macro Time (s)".
- Deduplicate columns and select numeric for CSV/HDF5 readers.
"""

# ----------------------------- constants -------------------------------------

FILL_MISSING_VALUE = -1.0

# MSVC weird tokens as compiled regex (full-cell matches)
#  - 1.#INF, -1.#INF, 1.#IND, -1.#IND, 1.#QNAN, 1.#SNAN with optional trailing digits and exponent
_WIN_NAN_RE  = re.compile(r'^\s*[+-]?(?:\d*\.)?#(?:IND|QNAN|SNAN)\d*(?:e[+-]?\d+)?\s*$', re.IGNORECASE)
_WIN_PINF_RE = re.compile(r'^\s*\+?(?:\d*\.)?#INF\d*(?:e[+-]?\d+)?\s*$', re.IGNORECASE)
_WIN_NINF_RE = re.compile(r'^\s*-(?:\d*\.)?#INF\d*(?:e[+-]?\d+)?\s*$', re.IGNORECASE)

_TEXT_EXTS = (".bur", ".csv", ".txt", ".dat")
_HDF5_EXTS = (".h5", ".hdf5")

_DEFAULT_BURST_EXTRA_ENDINGS: List[str] = ["bg4", "br4", "by4", "bv4", "td4", "2c4"]


def _drop_trailing_empty_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Drop trailing empty/``Unnamed`` columns (companion writers append a blank).

    Unlike a blanket "drop the last column", this removes only placeholder columns,
    so a companion's real last column (a bv4 ``Proximity Ratio Std``, a 2c4
    ``FRET-2CDE``) survives the merge.
    """
    while df.shape[1] > 1:
        last = str(df.columns[-1]).strip()
        if last == "" or last.lower().startswith("unnamed"):
            df = df.iloc[:, :-1]
        else:
            break
    return df


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

def _in_gui_thread() -> bool:
    """Return True if we're running in the main GUI thread."""
    if not _HAS_QT or QApplication is None:
        return False
    app = QApplication.instance()
    if app is None:
        return False
    try:
        return app.thread() == QThread.currentThread()
    except Exception:
        return False


def _safe_warning(title: str, message: str) -> None:
    """Show a QMessageBox when in GUI thread, otherwise fall back to logging."""
    if _HAS_QT and QApplication is not None and _in_gui_thread():
        QMessageBox.warning(None, title, message)
    else:
        logging.warning("%s: %s", title, message)

def _zip_contains_any(zip_path: str, exts: tuple[str, ...]) -> bool:
    try:
        with zipfile.ZipFile(zip_path, 'r') as zf:
            names = [n.lower() for n in zf.namelist()]
        return any(n.endswith(ext) for ext in exts for n in names)
    except Exception as e:
        logging.debug("Zip inspect failed for '%s': %s", zip_path, e)
        return False


# ------------------------------- fast table read ------------------------------


def read_table_tttrlib(
    path: Union[str, pathlib.Path],
    delimiter: str = ",",
    has_header: bool = True,
) -> Optional[pd.DataFrame]:
    """Read a delimited text table with tttrlib's threaded CSV reader.

    Returns ``None`` when the file is not one this reader handles, which is the
    caller's signal to use pandas. That is not a fallback engine kept around in
    parallel -- it is the general reader for the files this one deliberately
    does not do: decimal commas, whitespace alignment, skipped preamble lines,
    embedded newlines. The point of the fast path is to be fast on the burst
    tables that actually get opened, and the point of naming its limits is that
    a caller can tell which one it got.

    The columns come back as views into the store rather than as copies, so the
    frame this returns costs the parse and nothing else.
    """
    try:
        store = tttrlib.read_csv(str(path), delimiter=delimiter,
                                 has_header=has_header, use_float32=True)
    except Exception as exc:
        logging.info("[read] tttrlib.read_csv declined %s (%s)",
                     pathlib.Path(path).name, exc)
        return None

    columns = {}
    for i in range(store.n_columns()):
        column = store[i]
        name = column.name()
        # A duplicate header name would silently drop a column here, so make it
        # unique the way pandas does rather than losing one.
        if name in columns:
            name = "%s.%d" % (name, i)
        columns[name] = column.numpy()
    return pd.DataFrame(columns, copy=False)


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
    # ensure a QApplication (skip when headless)
    if QApplication is not None:
        app = QApplication.instance() or QApplication([])

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
    
    if _in_gui_thread():
        worker = DataLoadWorker(task)
        worker.finished.connect(lambda result: on_success(result.data_source))
        worker.error.connect(on_error)
        worker.start()
    else:
        run_task_inline(task)


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

    progress = None
    if _in_gui_thread():
        progress = ProgressWindow(
            title="File Processing",
            message=f"Processing {n_files} burst files...",
            max_value=n_files,
            cancelable=True,
        )
        progress.show()

    pieces: List[pd.DataFrame] = []
    macro_time_offset_ms = 0.0
    macro_col_ms = "Mean Macro Time (ms)"
    macro_col_s  = "Mean Macro Time (s)"

    # Cache format detection from first file for speed (all .bur files share format)
    bur_format_cache: Optional[Dict] = None
    extra_format_cache: Dict[str, Dict] = {}  # ending -> kwargs

    for i, bur in enumerate(bur_files, start=1):
        # Check for cancellation
        if progress is not None and progress.was_cancelled():
            logging.info("Data loading cancelled by user")
            if progress is not None:
                progress.close()
            return DataSource()  # Return empty data source
        # Detect format from first file, reuse for rest
        if bur_format_cache is None:
            bur_format_cache = _detect_format(bur)
        df_main = _read_text_table_auto(bur, cached_kwargs=bur_format_cache)
        df_main.columns = [str(c).strip() for c in df_main.columns]
        # Same rule as the companions below: the trailing tab on the header line
        # is already resolved by the parser, so a blanket drop-last would delete
        # a real measurement column ("Red Count Rate (KHz)", "S delayed yellow
        # (kHz)") and with it every derived red/FRET quantity.
        if drop_last_column:
            df_main = _drop_trailing_empty_columns(df_main)

        dfs = [df_main]

        # extras beside this bur (by stem) in base_path/<ending>/*.ending
        stem = bur.stem
        for ending in additional_endings:
            extra = base_path / ending / f"{stem}.{ending}"
            if not extra.exists():
                continue
            # Cache format per extra file type
            if ending not in extra_format_cache:
                extra_format_cache[ending] = _detect_format(extra)
            df_extra = _read_text_table_auto(extra, cached_kwargs=extra_format_cache[ending])
            df_extra.columns = [str(c).strip() for c in df_extra.columns]
            if df_extra.shape[1] == 0:
                continue
            # For companions, drop only the trailing empty/placeholder column (the
            # writers append one so a blanket drop-last would remove real data,
            # e.g. a bv4's "Proximity Ratio Std" or a 2c4's "FRET-2CDE").
            if drop_last_column:
                df_extra = _drop_trailing_empty_columns(df_extra)
            dfs.append(df_extra)

        combined = pd.concat(dfs, axis=1)
        combined = combined.loc[:, ~combined.columns.duplicated()]

        # skip every Nth row
        if skip_nth_row > 1 and not combined.empty:
            combined = combined[combined.index % skip_nth_row != 0]

        # concatenate macro time (ms → s) and rename
        if macro_col_ms in combined.columns and not combined.empty:
            combined[macro_col_ms] = pd.to_numeric(combined[macro_col_ms], errors="coerce")
            combined[macro_col_ms] = combined[macro_col_ms] + macro_time_offset_ms
            combined.rename(columns={macro_col_ms: macro_col_s}, inplace=True)
            combined[macro_col_s] = combined[macro_col_s] / 1000.0

            # update offset (use last value from ORIGINAL df that had the macro column)
            last_ms = None
            for df in reversed(dfs):
                if macro_col_ms in df.columns and not df.empty:
                    last_ms = pd.to_numeric(df[macro_col_ms], errors="coerce").iloc[-1]
                    break
            if last_ms is None:
                last_ms = 0.0
            macro_time_offset_ms += float(last_ms)

        pieces.append(combined)

        if progress is not None:
            progress.set_value(i)
            QCoreApplication.processEvents()

    if progress is not None:
        progress.set_value(n_files)
        progress.close()

    t1 = _time.perf_counter()
    logging.info("Read %d files in %.2fs, concatenating...", n_files, t1 - t0)

    # Optimize memory usage during concatenation
    if pieces:
        # Pre-allocate list with estimated size to reduce memory reallocations
        total_rows = sum(len(df) for df in pieces if not df.empty)
        logging.info("Estimated total rows: %d", total_rows)
        
        # Use ignore_index=True and optimize dtypes before concatenation
        for i, df in enumerate(pieces):
            if not df.empty:
                # Downcast only non-filename columns to save memory
                cols_to_convert = [col for col in df.columns if not any(keyword in str(col).lower() for keyword in ['file', 'path', 'name', 'directory'])]
                if cols_to_convert:
                    converted = df[cols_to_convert].apply(pd.to_numeric, errors='coerce').convert_dtypes(convert_integer=False, convert_floating=True)
                    for col in cols_to_convert:
                        df[col] = converted[col]
                pieces[i] = df
        
        # Concatenate with optimized memory settings
        final_df = pd.concat(pieces, ignore_index=True, copy=False)
    else:
        final_df = pieces[0].iloc[0:0] if pieces else pd.DataFrame()

    t2 = _time.perf_counter()
    logging.info("Burst load complete: %d rows, %.2fs total (concat %.2fs)",
                 len(final_df), t2 - t0, t2 - t1)

    ds = DataSource()
    ds.data = final_df
    return ds


#: Suffixes a stored chain can carry: tab-separated text, or an HDF5 table.
#: A long run makes the difference matter -- a float64 costs ~25 characters as
#: text and 8 in HDF5, before compression.
_CHAIN_SUFFIXES = (".er4", ".h5", ".hdf5")


def _read_chain_frame(filename: str, sep: str = '\t') -> pd.DataFrame:
    """Load one chain file, text or HDF5, as a frame of draws.

    Parameters
    ----------
    filename : str
        Path to a ``.er4`` text chain or an HDF5 chain table.
    sep : str
        Column separator of the text format.

    Returns
    -------
    pandas.DataFrame
        One row per draw.
    """
    path = pathlib.Path(filename)
    if path.suffix.lower() in (".h5", ".hdf5"):
        if is_ensemble_sampling_hdf5(str(path)):
            source = read_ensemble_sampling_hdf5(str(path))
            if source.data is None:
                raise ValueError("no sampled states in the file")
            return source.data
        # ChiSurf writes the chain as a pandas table under 'results'.
        return pd.read_hdf(path, key="results")
    return pd.read_csv(path, sep=sep, header=0, comment=None)


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

    dfs = []
    skipped: List[str] = []
    expected_columns: Optional[set] = None
    for fn in filenames:
        try:
            df = _read_chain_frame(fn, sep)
            # Normalize column names (strip whitespace and leading #)
            df.columns = [str(c).strip().lstrip('#').strip() for c in df.columns]
        except Exception as e:
            logging.warning(f"Could not read sampling file {fn}: {e}")
            skipped.append(str(fn))
            continue

        if df.empty or df.shape[1] < 2:
            # Not a chain. Concatenated anyway it would contribute a column of
            # its own that every other chain is missing, and the missing values
            # are then filled -- inventing draws that were never sampled.
            logging.warning(f"Not a sampling chain, skipping: {fn}")
            skipped.append(str(fn))
            continue

        columns = set(df.columns) - {'chain', 'draw'}
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

        if 'chain' not in df.columns:
            df['chain'] = len(dfs)
        if 'draw' not in df.columns:
            df['draw'] = np.arange(len(df), dtype=np.int64)
        dfs.append(df)

    if skipped:
        # One line the user can actually notice: a chain silently missing from a
        # posterior is a posterior that is quietly wrong.
        logging.warning(
            "read %d of %d sampling chains; skipped: %s",
            len(dfs), len(filenames), ", ".join(pathlib.Path(f).name for f in skipped),
        )

    if not dfs:
        return DataSource()

    # Concatenate all chains by rows (stacking samples)
    combined_df = pd.concat(dfs, axis=0, ignore_index=True)
    
    # Ensure all columns are numeric (non-numeric become NaN)
    combined_df = _best_effort_numeric(combined_df)
    combined_df = _fill_missing(combined_df, FILL_MISSING_VALUE)
    
    return DataSource(data=combined_df)


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

    frames = []
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

        df = pd.DataFrame(chain.reshape(-1, n_dim), columns=list(names))
        df["log_prob"] = log_prob.reshape(-1)
        # ``reshape`` runs the walker axis fastest, so the walker index cycles
        # and the step index repeats.
        df["chain"] = np.tile(np.arange(n_walkers), n_steps) + chain_offset
        df["draw"] = np.repeat(np.arange(n_steps), n_walkers)
        chain_offset += n_walkers
        frames.append(df)

    if not frames:
        return DataSource()

    combined = pd.concat(frames, axis=0, ignore_index=True)
    combined = _best_effort_numeric(combined)
    combined = _fill_missing(combined, FILL_MISSING_VALUE)
    return DataSource(data=combined)


def read_hdf5_store(filename: Union[str, pathlib.Path], group: str = "/"):
    """A columnar HDF5 table as a :class:`tttrlib.DataStore`, or ``None``.

    The short path, and the one chisurf writes for: an HDF5 group holding one
    1-D dataset per column is the layout a DataStore already has, so the file
    becomes the store the gates are evaluated in and the histograms fill out of
    -- with no DataFrame in between, no conversion, and no second copy of the
    table at the moment it is largest. Types survive too: a float32 column stays
    float32 and an integer column stays an integer.

    ``None`` means the file is not that shape -- a pandas HDFStore table, a
    Photon-HDF5 measurement -- and the caller reads it the long way. Returning
    None rather than raising is what keeps the two readable side by side.
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
            return DataSource.from_store(store)

    if first.lower().endswith(".zip") and not _zip_contains_any(first, _HDF5_EXTS):
        logging.info("No HDF5 in zip; treating as burst analysis: %s", first)
        return read_burst_analysis(first)

    if is_ensemble_sampling_hdf5(first):
        logging.info("Sampling chain detected in %s", first)
        return read_ensemble_sampling_hdf5([str(f) for f in filenames])

    base_df = read_hdf5_file(first)
    row_count = len(base_df)

    if len(filenames) == 1:
        ds = DataSource()
        ds.data = base_df.select_dtypes(include=["number"])
        return ds

    combined = base_df.copy()
    for fn in filenames[1:]:
        df = read_hdf5_file(fn)
        if merge_mode == "rows":
            common = sorted(set(combined.columns).intersection(df.columns))
            if not common:
                _safe_warning("No Common Columns",
                              f"{fn} shares no columns with the first file. Skipping.")
                continue
            combined = pd.concat([combined[common], df[common]], axis=0,
                                 ignore_index=True)
            continue
        if len(df) != row_count:
            _safe_warning(
                "Row Count Mismatch",
                f"File {fn} has {len(df)} rows, expected {row_count}. Skipping."
            )
            continue
        dup = set(combined.columns).intersection(df.columns)
        combined = pd.concat([combined, df.drop(columns=list(dup))], axis=1) if dup else pd.concat([combined, df], axis=1)

    ds = DataSource()
    ds.data = combined.select_dtypes(include=["number"])
    return ds


def read_hdf5_file(filename: str) -> pd.DataFrame:
    """
    Read a single HDF5 (optionally inside a .zip).
    Tries '/results' first, else the first available key.
    """
    def _read_one(h5_path: pathlib.Path) -> pd.DataFrame:
        try:
            with pd.HDFStore(str(h5_path), mode="r") as st:
                keys = st.keys()
                key = "/results" if "/results" in keys else (keys[0] if keys else "/results")
            return pd.read_hdf(h5_path, key=key)
        except Exception as e:
            # final fallback to default key
            return pd.read_hdf(h5_path)

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
    - If same ncols: stack rows; elif same nrows: stack cols (drop dups); else fallback to col-wise merge.
    """
    if not filenames:
        return DataSource()

    dfs: List[pd.DataFrame] = []
    for fn in filenames:
        try:
            df = read_csv_file(fn)
            dfs.append(df)
        except Exception as e:
            _safe_warning("Open CSV", f"Could not read file {fn}: {e}")

    if not dfs:
        return DataSource()

    if len(dfs) == 1:
        dfn = dfs[0].select_dtypes(include=["number"])
        return DataSource(data=dfn)

    ncols = [d.shape[1] for d in dfs]
    nrows = [d.shape[0] for d in dfs]

    if len(set(ncols)) == 1:
        base_cols = list(dfs[0].columns)
        norm = []
        for d in dfs:
            dd = d.copy()
            dd.columns = base_cols
            norm.append(dd)
        combined = pd.concat(norm, axis=0, ignore_index=True)

    elif len(set(nrows)) == 1:
        combined = dfs[0].copy()
        for d in dfs[1:]:
            dup = set(combined.columns).intersection(d.columns)
            d2 = d.drop(columns=list(dup)) if dup else d
            combined = pd.concat([combined, d2], axis=1)
    else:
        _safe_warning(
            "Auto-merge CSV",
            "Files share neither column count nor row count. Using column-wise merge with duplicate-column removal."
        )
        combined = dfs[0].copy()
        for d in dfs[1:]:
            dup = set(combined.columns).intersection(d.columns)
            d2 = d.drop(columns=list(dup)) if dup else d
            combined = pd.concat([combined, d2], axis=1)

    dfn = combined.select_dtypes(include=["number"])
    dfn = _fill_missing(dfn, FILL_MISSING_VALUE)
    return DataSource(data=dfn)


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
    
    if _in_gui_thread():
        worker = DataLoadWorker(task)
        worker.finished.connect(lambda result: on_success(result.data_source))
        worker.error.connect(on_error)
        worker.start()
    else:
        run_task_inline(task)


# ----------------------------- helpers ---------------------------------------

def _fill_missing(df: pd.DataFrame, sentinel: float = FILL_MISSING_VALUE) -> pd.DataFrame:
    # If you also want to neutralize ±inf: df = df.replace([np.inf, -np.inf], np.nan)
    return df.fillna(sentinel)


def coerce_numeric_majority(df: pd.DataFrame, threshold: float = 0.55, verbose: bool = False) -> pd.DataFrame:
    """
    Try to coerce mostly-numeric string columns using several locale patterns.
    """
    out = df.copy()

    def _to_numeric_series(s: pd.Series):
        s_obj = s.astype("string", copy=False)

        a = pd.to_numeric(s_obj, errors="coerce")
        a_rate = float(a.notna().mean())

        sb = s_obj.copy()
        mb = sb.notna() & sb.str.contains(",", na=False) & ~sb.str.contains(r"\.", na=False)
        if mb.any():
            sb.loc[mb] = sb.loc[mb].str.replace(",", ".", regex=False)
        b = pd.to_numeric(sb, errors="coerce")
        b_rate = float(b.notna().mean())

        sc = s_obj.copy()
        mc = sc.notna() & sc.str.contains(",", na=False)
        if mc.any():
            sc.loc[mc] = sc.loc[mc].str.replace(",", "", regex=False)
        c = pd.to_numeric(sc, errors="coerce")
        c_rate = float(c.notna().mean())

        sd = s_obj.copy()
        md = sd.notna() & sd.str.contains(r",", na=False) & sd.str.contains(r"\.", na=False)
        if md.any():
            sd.loc[md] = (sd.loc[md].str.replace(".", "", regex=False)
                                   .str.replace(",", ".", regex=False))
        d = pd.to_numeric(sd, errors="coerce")
        d_rate = float(d.notna().mean())

        candidates = [("direct", a_rate, a), ("dec_comma", b_rate, b), ("us_thousands", c_rate, c), ("eu_thousands", d_rate, d)]
        how, rate, ser = max(candidates, key=lambda x: x[1])
        return ser, rate, how

    for col in out.columns:
        if pd.api.types.is_numeric_dtype(out[col]):
            if verbose:
                logging.info("[coerce_numeric_majority] %s: already numeric", col)
            continue
        ser, rate, how = _to_numeric_series(out[col])
        if rate >= threshold:
            if verbose:
                logging.info("[coerce_numeric_majority] %s → numeric (%.1f%%, %s)", col, 100*rate, how)
            out[col] = ser
        else:
            if verbose:
                logging.info("[coerce_numeric_majority] %s: keep as text (%.1f%% numeric)", col, 100*rate)
    return out


def _pandas_kwargs(kwargs: Dict) -> Dict:
    """Return *kwargs* without the private flags, for handing to pandas.

    `_detect_and_build_kwargs` mixes two things into one dict: arguments for the
    CSV reader, and decisions about WHICH reader to use (`_tttrlib`). The second
    kind is prefixed and has to be dropped before the dict is splatted, or pandas
    raises `unexpected keyword argument '_tttrlib'` -- and every caller catches
    that as "could not read the file", so a perfectly ordinary comma-delimited
    file with a header on line 1 reads as empty and reports nothing but a
    warning. One function, so a third call site cannot forget.
    """
    return {k: v for k, v in kwargs.items() if not k.startswith("_")}


def read_csv_file(filename: str) -> pd.DataFrame:
    """
    Read a CSV-like text file or a .zip containing exactly one CSV-like text file.
    - Autodetect delimiter (, \\t ; | or whitespace).
    - Choose the first full-width *texty* row as header when available.
    - Normalize MSVC NaN/Inf/IND/QNAN/SNAN tokens.
    - Force numeric columns (non-numeric → NaN) and fill NaNs with FILL_MISSING_VALUE.
    """
    p = pathlib.Path(filename)

    if p.suffix.lower() == ".zip":
        with zipfile.ZipFile(p, "r") as zf:
            inner = _find_first_member(zf, _TEXT_EXTS)
            if inner is None:
                raise ValueError(f"No CSV-like files found in zip: {filename}")
            with zf.open(inner) as bio:
                tio = io.TextIOWrapper(bio, encoding="utf-8", errors="ignore")
                head = _read_head_lines(tio)
            kwargs = _detect_and_build_kwargs(head)
            with zf.open(inner) as bio:
                tio = io.TextIOWrapper(bio, encoding="utf-8", errors="ignore")
                df = pd.read_csv(tio, **_pandas_kwargs(kwargs))
    else:
        with open(p, "r", encoding="utf-8", errors="ignore") as f:
            head = _read_head_lines(f)
            kwargs = _detect_and_build_kwargs(head)
            f.seek(0)
            df = pd.read_csv(f, **_pandas_kwargs(kwargs))

    logging.info("[read_csv_file] Read %d rows from %s", len(df), filename)
    logging.info("[read_csv_file] Columns: %s", ", ".join(map(str, df.columns)))

    # normalize MSVC tokens then coerce to numeric
    df = _normalize_msvc_tokens(df)
    df = df.apply(pd.to_numeric, errors="coerce")
    df = df.fillna(FILL_MISSING_VALUE)
    return df


# --------------------- low-level text-table helpers --------------------------

def _read_text_table_auto(path: pathlib.Path, cached_kwargs: Optional[Dict] = None) -> pd.DataFrame:
    """
    Read a single text-like file (.bur/.csv/.txt/.dat) with autodetection + MSVC normalization.

    Parameters
    ----------
    path : pathlib.Path
        File to read.
    cached_kwargs : Optional[Dict]
        If provided, skip detection and use these kwargs directly for pd.read_csv.
        This speeds up reading many files with the same format.

    This implementation avoids double-reading the file by rewinding the same handle after sampling.
    """
    import time as _time
    
    if cached_kwargs is not None:
        kwargs = cached_kwargs.copy()
    else:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            head = _read_head_lines(f)
            kwargs = _detect_and_build_kwargs(head)
    
    def _load_with_kwargs(read_kwargs: Dict) -> pd.DataFrame:
        # Read, not pop: the same kwargs dict is cached and reused for every
        # further file of this format, so consuming the flag here would send
        # all but the first through pandas.
        if read_kwargs.get("_tttrlib", False):
            frame = read_table_tttrlib(
                path,
                delimiter=read_kwargs.get("sep", ","),
                has_header=read_kwargs.get("header", 0) == 0,
            )
            if frame is not None:
                return frame
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return pd.read_csv(f, **_pandas_kwargs(read_kwargs))

    def _drop_trailing_empty_columns(frame: pd.DataFrame) -> pd.DataFrame:
        if frame.empty or frame.shape[1] == 0:
            return frame
        working = frame
        while working.shape[1] > 0:
            last_col_name = working.columns[-1]
            col = working[last_col_name]
            all_nan = col.isna().all()
            all_blank = False
            if not all_nan and (pd.api.types.is_object_dtype(col) or pd.api.types.is_string_dtype(col)):
                non_null = col.dropna()
                if non_null.empty:
                    all_blank = True
                else:
                    all_blank = non_null.astype(str).str.strip().eq("").all()
            if all_nan or all_blank:
                logging.debug("[read] Dropping trailing empty column '%s'", last_col_name)
                working = working.iloc[:, :-1]
                continue
            break
        return working

    def _update_cache(new_kwargs: Dict) -> None:
        if cached_kwargs is not None:
            cached_kwargs.clear()
            cached_kwargs.update(new_kwargs)

    t0 = _time.perf_counter()
    while True:
        try:
            df = _load_with_kwargs(kwargs)
            break
        except Exception as exc:
            if cached_kwargs is not None:
                logging.warning("[read] Cached format failed for %s (%s). Re-detecting format.",
                                path.name, exc)
                kwargs = _detect_format(path)
                _update_cache(kwargs)
                t0 = _time.perf_counter()
                continue
            raise
    t1 = _time.perf_counter()

    before_drop_cols = df.shape[1]
    df = _drop_trailing_empty_columns(df)
    if df.shape[1] != before_drop_cols:
        logging.debug("[read] Width reduced from %d to %d after dropping empty column(s)",
                     before_drop_cols, df.shape[1])

    object_cols = df.select_dtypes(include=['object']).columns
    has_object_cols = len(object_cols) > 0
    
    t2_start = _time.perf_counter()
    if has_object_cols:
        # Skip filename columns from post-processing too
        filename_cols = [col for col in object_cols
                       if any(keyword in str(col).lower() for keyword in ['file', 'path', 'name', 'directory'])]
        if filename_cols:
            logging.debug("[read] Skipping filename columns in post-processing: %s", filename_cols)
        
        # Only process non-filename columns
        cols_to_process = [col for col in object_cols if col not in filename_cols]
        if cols_to_process:
            logging.debug("[read] Running post-processing on %d object columns", len(cols_to_process))
            df = _normalize_msvc_tokens(df)
            df = _best_effort_numeric(df)
        else:
            logging.debug("[read] Skipping post-processing - only filename columns remain")
    else:
        logging.debug("[read] Skipping post-processing - no object columns")
    t2 = _time.perf_counter()
    
    logging.debug("[read] %d rows, parse=%.2fs, post_process=%.2fs, object_cols=%d",
                 len(df), t1 - t0, t2 - t2_start,
                 len(df.select_dtypes(include=['object']).columns))
    
    return df


def _detect_format(path: pathlib.Path) -> Dict:
    """
    Detect file format and return kwargs for pd.read_csv.
    Uses cache to avoid re-detection on subsequent loads.
    """
    # Try to get cached format first
    cache = get_metadata_cache()
    cached_format = cache.get_cached_format(path)
    if cached_format is not None:
        return cached_format
    
    # Detect format and cache it
    with open(path, "r", encoding="utf-8", errors="ignore") as f:
        head = _read_head_lines(f)
        format_kwargs = _detect_and_build_kwargs(head)
    
    # Cache the detected format
    cache.cache_format(path, format_kwargs)
    return format_kwargs


def _normalize_msvc_tokens(df: pd.DataFrame) -> pd.DataFrame:
    """
    Replace MSVC weird tokens with NaN/±Inf (full-cell matches).
    Optimized: only processes columns that actually contain MSVC tokens.
    """
    if df.empty:
        return df
    
    str_cols = df.select_dtypes(include=['object']).columns
    if len(str_cols) == 0:
        return df
    
    # Quick check: sample first 100 rows to see if any MSVC tokens exist
    # This avoids expensive regex on files that don't have MSVC tokens
    sample_size = min(100, len(df))
    has_msvc = False
    for col in str_cols:
        sample = df[col].head(sample_size).astype(str)
        if sample.str.contains(r'#(?:INF|IND|QNAN|SNAN)', case=False, na=False).any():
            has_msvc = True
            break
    
    if not has_msvc:
        return df
    
    # Only copy if we actually need to modify
    result = df.copy()
    
    for col in str_cols:
        # Use vectorized replace with regex - much faster than .apply()
        series = result[col].astype(str)
        
        # Single pass replacements using pd.Series.replace with regex
        result[col] = series.replace({
            _WIN_NAN_RE: np.nan,
            _WIN_PINF_RE: np.inf,
            _WIN_NINF_RE: -np.inf,
        }, regex=True)
    
    return result


def _best_effort_numeric(df: pd.DataFrame) -> pd.DataFrame:
    """
    Convert columns to numeric. Fast path: just convert, don't validate.
    """
    if df.empty:
        return df

    str_cols = df.select_dtypes(include=['object']).columns
    if len(str_cols) == 0:
        return df
    
    # Fast path: convert all object columns to numeric in one go
    # Use errors='coerce' - non-numeric strings become NaN
    for col in str_cols:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    return df

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


def _detect_and_build_kwargs(lines: List[str]) -> Dict:
    """
    Detect delimiter and header row from a sample of lines.
    Returns kwargs for pandas.read_csv.
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

    kwargs: Dict = dict(skipinitialspace=True)
    if use_header_idx is not None:
        kwargs["header"] = 0
        kwargs["skiprows"] = use_header_idx
        data_start = use_header_idx + 1
        header_where = f"line {use_header_idx}"
    else:
        kwargs["header"] = None
        kwargs["skiprows"] = first_idx
        data_start = first_idx
        header_where = "none"

    if delim is None:
        kwargs["delim_whitespace"] = True
        kwargs["engine"] = "python"
        sep_show = "<whitespace>"
    else:
        kwargs["sep"] = delim
        kwargs["engine"] = "c"
        # tttrlib's threaded reader handles a plain delimited file with its
        # header on the first line. Not a decimal comma, not a skipped preamble,
        # not whitespace alignment -- those go to pandas, which is the general
        # reader, and the flag is what says which one a file got.
        kwargs["_tttrlib"] = (
            not dec_comma
            and first_idx == 0
            and use_header_idx in (None, 0)
        )
        sep_show = repr(delim)

    if dec_comma:
        kwargs["decimal"] = ","

    # debug log (compact) - only shown once per file type due to caching
    logging.info("[detect] sep=%s, width=%d, engine=%s, header=%s, data_start=%d",
                 sep_show, complete_cols, kwargs.get("engine", "c"), header_where, data_start)
    return kwargs
