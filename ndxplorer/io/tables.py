"""Table operations the readers share, on :class:`tttrlib.DataStore`.

Text read out of a file arrives as whatever types tttrlib inferred per column:
a column holding a Windows ``1.#INF`` or a stray word is a text column, and an
empty field is a row marked not measured. These helpers turn such a store into
the numeric table ndXplorer plots, and put several tables side by side or one
under another.
"""

from __future__ import annotations

import re
from typing import Callable, List, Optional, Sequence

import numpy as np
import tttrlib

from ..core.data_source import float_column
from ..logging_config import logging

__all__ = [
    "FILENAME_KEYWORDS",
    "is_filename_column",
    "label_to_float",
    "text_column_as_float",
    "as_numeric",
    "numeric_columns_only",
    "drop_trailing_empty_columns",
    "concat_columns",
    "concat_rows",
    "rename_columns",
]

#: A column whose name contains one of these holds text that is data (the file
#: a burst came from), not a number that failed to parse.
FILENAME_KEYWORDS = ("file", "path", "name", "directory")

# Windows C runtime spellings of non-finite numbers (full-cell matches):
# 1.#INF, -1.#INF, 1.#IND, -1.#IND00e+000, 1.#QNAN, 1.#SNAN.
_WIN_NAN_RE = re.compile(r'^\s*[+-]?(?:\d*\.)?#(?:IND|QNAN|SNAN)\d*(?:e[+-]?\d+)?\s*$', re.IGNORECASE)
_WIN_PINF_RE = re.compile(r'^\s*\+?(?:\d*\.)?#INF\d*(?:e[+-]?\d+)?\s*$', re.IGNORECASE)
_WIN_NINF_RE = re.compile(r'^\s*-(?:\d*\.)?#INF\d*(?:e[+-]?\d+)?\s*$', re.IGNORECASE)


def is_filename_column(name: str) -> bool:
    lowered = str(name).lower()
    return any(keyword in lowered for keyword in FILENAME_KEYWORDS)


def label_to_float(label: str) -> float:
    """The number a text cell spells, or NaN when it spells none."""
    text = str(label).strip()
    if _WIN_NAN_RE.match(text):
        return float("nan")
    if _WIN_PINF_RE.match(text):
        return float("inf")
    if _WIN_NINF_RE.match(text):
        return float("-inf")
    try:
        return float(text)
    except ValueError:
        return float("nan")


def text_column_as_float(column) -> np.ndarray:
    """A text column's values as float64, converted once per distinct label."""
    labels = column.labels()
    lookup = np.array([label_to_float(label) for label in labels], dtype=np.float64)
    codes = np.asarray(column.codes())
    values = lookup[codes] if lookup.size else np.full(len(codes), np.nan)
    mask = column.mask_numpy()
    if mask is not None:
        values[~mask[:len(values)]] = np.nan
    return values


def as_numeric(store: "tttrlib.DataStore",
               keep_text: Callable[[str], bool] = lambda name: False,
               fill: Optional[float] = None) -> "tttrlib.DataStore":
    """Make every column of `store` numeric, in place, and return it.

    A text column becomes float64 label by label unless `keep_text` names it.
    A row marked not measured becomes NaN; with `fill`, every NaN becomes
    `fill`. A column with nothing to change keeps its dtype and its buffer.
    """
    for index in range(store.n_columns()):
        column = store.column(index)
        if column.type() == tttrlib.ColumnType_String:
            if keep_text(column.name()):
                continue
            values = text_column_as_float(column)
        elif column.has_missing():
            values = float_column(store, index)
        elif fill is not None and column.dtype in ("float32", "float64"):
            view = column.numpy()
            if not np.isnan(view).any():
                continue
            values = np.array(view, dtype=np.float64)
        else:
            continue
        if fill is not None:
            values[np.isnan(values)] = fill
        if column.dtype == "float32":
            values = values.astype(np.float32)
        column.clear_mask()
        column.set_numpy(values)
    return store


def numeric_columns_only(store: "tttrlib.DataStore") -> "tttrlib.DataStore":
    """Remove the text columns of `store`, in place, and return it."""
    for index in range(store.n_columns() - 1, -1, -1):
        if store.column(index).type() == tttrlib.ColumnType_String:
            store.remove_column(index)
    return store


def _is_blank_column(column) -> bool:
    mask = column.mask_numpy()
    if mask is not None and not mask.any():
        return True
    if column.type() == tttrlib.ColumnType_String:
        return all(not str(label).strip() for label in column.labels())
    if column.dtype in ("float32", "float64"):
        return bool(np.isnan(column.numpy()).all()) if column.size() else True
    return False


def drop_trailing_empty_columns(store: "tttrlib.DataStore") -> "tttrlib.DataStore":
    """Remove trailing placeholder columns, in place, and return `store`.

    Burst writers end every line with a delimiter, which reads as one more
    column with an empty name and no values. Only such a column goes -- a
    trailing column named empty or ``Unnamed``, or holding no value at all -- so
    a companion's real last column (a bv4 ``Proximity Ratio Std``, a 2c4
    ``FRET-2CDE``) stays.
    """
    while store.n_columns() > 1:
        column = store.column(store.n_columns() - 1)
        name = column.name().strip()
        if name == "" or name.lower().startswith("unnamed") or _is_blank_column(column):
            logging.debug("[read] dropping trailing empty column %r", column.name())
            store.remove_column(store.n_columns() - 1)
            continue
        break
    return store


def rename_columns(store: "tttrlib.DataStore", names: Sequence[str]) -> "tttrlib.DataStore":
    """A new store holding the columns of `store` under `names`, position by position."""
    out = tttrlib.DataStore()
    for index, name in enumerate(names):
        column = store[index]
        out.add(str(name), column.numpy())
        mask = column.mask_numpy()
        if mask is not None:
            out[out.n_columns() - 1].set_mask(np.ascontiguousarray(mask, dtype=np.uint8))
    out.set_n_rows(int(store.n_rows()))
    return out


def concat_columns(stores: Sequence["tttrlib.DataStore"]) -> "tttrlib.DataStore":
    """Put tables describing the same rows side by side.

    A column name already present keeps the earlier table's column. A table
    with a different row count describes different rows and is left out, with
    a warning.
    """
    stores = [s for s in stores if s is not None]
    if not stores:
        return tttrlib.DataStore()
    n_rows = int(stores[0].n_rows())
    matching = [stores[0]]
    for store in stores[1:]:
        if int(store.n_rows()) != n_rows:
            logging.warning("a table with %d rows does not describe the %d rows beside it; "
                            "leaving it out", store.n_rows(), n_rows)
            continue
        matching.append(store)
    if len(matching) == 1:
        return matching[0]
    return tttrlib.concat(matching, axis="columns", on_duplicate="keep-first")


def concat_rows(stores: Sequence["tttrlib.DataStore"],
                join: str = "outer") -> "tttrlib.DataStore":
    """Stack tables row-wise, lining columns up by name.

    Where one column has two numeric types in two tables both become float64;
    where it is text in one and numeric in another, the text is read as numbers.
    A column missing from a table marks those rows not measured.
    """
    stores = [s for s in stores if s is not None]
    if not stores:
        return tttrlib.DataStore()
    if len(stores) == 1:
        return stores[0]
    types = {}
    for store in stores:
        for index in range(store.n_columns()):
            column = store.column(index)
            types.setdefault(column.name(), set()).add(column.type())
    for name, kinds in types.items():
        if len(kinds) < 2:
            continue
        for store in stores:
            index = store.find(name)
            if index < 0:
                continue
            column = store.column(index)
            if column.type() == tttrlib.ColumnType_String:
                values = text_column_as_float(column)
            else:
                values = float_column(store, index)
            column.clear_mask()
            column.set_numpy(values)
    return tttrlib.concat(stores, axis="rows", join=join)
