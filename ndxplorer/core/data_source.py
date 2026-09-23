#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
The table ndXplorer shows, its computed columns, and the gates on it.

:class:`DataSource` holds exactly one :class:`tttrlib.DataStore`. Readers
produce the store, gates and histograms are evaluated in it, equations write
their outputs into it and writers save it; there is no second representation
of the table. Column names resolve case-insensitively and on the part left of
``|``.
"""

from __future__ import annotations

import abc
import json
import sys
from typing import Dict, List, Mapping, Optional, Iterable, Any, Sequence, Set, Tuple
from collections import OrderedDict

import numpy as np
import tttrlib

from ..logging_config import logging

try:
    import yaml  # optional
except Exception:  # pragma: no cover
    yaml = None  # type: ignore


# ---------------------------
# Equation application
# ---------------------------

def _load_equations_file(path: str) -> List[Dict[str, str]]:
    """
    Load equations from a YAML or JSON file. The file is expected to contain a list
    of mappings like: [{"Fg": "'Sg' - 'Bg'"}, {"Proximity ratio": "'Sr' / ('Sg' + 'Sr')"}]
    """
    with open(path, "r", encoding="utf-8") as fp:
        text = fp.read()

    # Decide by extension first, fallback to a safe YAML if available, else JSON
    lower = path.lower()
    if lower.endswith(".json"):
        return json.loads(text, object_pairs_hook=OrderedDict)
    if yaml is not None:
        return yaml.safe_load(text)  # type: ignore
    # As a last resort, try JSON
    return json.loads(text, object_pairs_hook=OrderedDict)


def compute_values(
    store: "tttrlib.DataStore",
    constants: Dict[str, float],
    equations: Optional[List[Dict[str, str]]] = None,
    equation_json_fn: Optional[str] = None,
    changed_constants: Optional[Set[str]] = None,
    targets: Optional[Sequence[str]] = None,
) -> List[str]:
    """
    Compute columns of `store` from `equations`, using case-insensitive column
    lookup for the quoted data and constant references.

    Parameters
    ----------
    store : tttrlib.DataStore
        The table to augment; output columns are added, or replaced in place.
    constants : Dict[str, float]
        Name → value constants.
    equations : Optional[List[Dict[str, str]]]
        List of {new_column_name: "expression"} dicts. If None, taken from file.
    equation_json_fn : Optional[str]
        Path to YAML/JSON file with equations (detected by extension).

    Notes
    -----
    Expressions refer to columns or constants using *quoted* names:
    ``'Sg' / 'Sr'`` reads two columns, ``'Bg'`` reads a constant when
    `constants` has one of that name.
    """
    equations = equations or []
    if not equations and equation_json_fn:
        try:
            equations = _load_equations_file(equation_json_fn)
        except Exception as e:
            logging.warning(f"compute_values: Failed to load equations from {equation_json_fn}: {e}")
            equations = []

    # Quoted names resolve by exact (case-insensitive / left-of-pipe) match,
    # equations evaluate in topological order, and a changed constant recomputes
    # exactly its transitive dependents.
    from .equation_graph import compute_values_ast

    return compute_values_ast(
        store, constants or {}, equations,
        changed_constants=changed_constants, targets=targets,
    )


# ---------------------------
# Selection API
# ---------------------------

def _array_digest(values) -> tuple:
    """An array reduced to comparable values: shape, dtype and a content hash."""
    import hashlib
    arr = np.ascontiguousarray(values)
    return (arr.shape, arr.dtype.str, hashlib.blake2b(arr.tobytes(), digest_size=16).digest())


class DataSelection(abc.ABC):
    """A gate on the data.

    ``gate_key`` names everything that decides the gate's answer, by value, so
    an edit made in place (the selection table edits the object the mask cache
    already holds) changes the key; ``__eq__`` compares those keys.
    """

    def gate_key(self) -> tuple:
        raise NotImplementedError

    def __eq__(self, other):
        return type(self) is type(other) and self.gate_key() == other.gate_key()

    __hash__ = None  # mutable, and compared by value: not hashable

    @abc.abstractmethod
    def get_mask(self, data: np.ndarray) -> np.ndarray:
        """
        Parameters
        ----------
        data : np.ndarray, shape (n_parameters, n_points)

        Returns
        -------
        mask : np.ndarray (bool), same shape as data
            True means "masked out" (excluded).
        """
        raise NotImplementedError


class Gaussian2DSelection(DataSelection):
    """
    Elliptical selection in 2D using Mahalanobis distance around mean `mu`
    with covariance `cov`. Supports optional per-axis log transforms.

    If invert=False (default): mask points OUTSIDE the ellipse (d2 > sigma^2).
    If invert=True:  mask points INSIDE the ellipse (d2 <= sigma^2).
    """

    def __init__(
        self,
        parameter_idx1: int,
        parameter_idx2: int,
        mu: Iterable[float],
        cov: Iterable[Iterable[float]],
        sigma: float = 1.0,
        invert: bool = False,
        enabled: bool = True,
        name: Optional[str] = None,
        log_x: bool = False,
        log_y: bool = False,
    ):
        self.parameter_idx1 = int(parameter_idx1)
        self.parameter_idx2 = int(parameter_idx2)
        self.mu = np.asarray(mu, dtype=float).reshape(2)
        self.cov = np.asarray(cov, dtype=float).reshape(2, 2)
        self.sigma = float(sigma)
        self.invert = bool(invert)
        self.enabled = bool(enabled)
        self.name = name
        self.log_x = bool(log_x)
        self.log_y = bool(log_y)
        # Deterministic ID for cache stability
        self.selection_id = f"g2d_{self.parameter_idx1}_{self.parameter_idx2}_{self.mu.tolist()}_{self.sigma}_{self.invert}_{self.enabled}"

    def gate_key(self) -> tuple:
        """See :func:`ndxplorer.core.data.mask_state.gate_key`."""
        return ("gaussian", self.parameter_idx1, self.parameter_idx2,
                tuple(np.asarray(self.mu, dtype=float).ravel().tolist()),
                tuple(np.asarray(self.cov, dtype=float).ravel().tolist()),
                float(self.sigma), bool(self.invert), bool(self.enabled),
                bool(self.log_x), bool(self.log_y))

    def get_mask(self, data: np.ndarray) -> np.ndarray:
        n_param, n_pts = data.shape
        mask = np.zeros((n_param, n_pts), dtype=bool)
        if not self.enabled:
            return mask
        if self.parameter_idx1 >= n_param or self.parameter_idx2 >= n_param:
            return mask

        x = data[self.parameter_idx1, :]
        y = data[self.parameter_idx2, :]

        with np.errstate(divide='ignore', invalid='ignore'):
            zx = np.where(x > 0.0, np.log(x), np.nan) if self.log_x else x.astype(float)
            zy = np.where(y > 0.0, np.log(y), np.nan) if self.log_y else y.astype(float)

        try:
            inv_cov = np.linalg.inv(self.cov)
        except Exception:
            inv_cov = np.linalg.pinv(self.cov)

        dx = zx - self.mu[0]
        dy = zy - self.mu[1]
        invalid = ~np.isfinite(dx) | ~np.isfinite(dy)
        dx = np.nan_to_num(dx, nan=np.inf)
        dy = np.nan_to_num(dy, nan=np.inf)

        a = inv_cov[0, 0]
        b = inv_cov[0, 1]
        c = inv_cov[1, 1]
        d2 = a * dx * dx + 2.0 * b * dx * dy + c * dy * dy
        d2[invalid] = np.inf

        if self.invert:
            out_of_bounds = d2 <= (self.sigma * self.sigma)
        else:
            out_of_bounds = d2 > (self.sigma * self.sigma)

        mask[:, out_of_bounds] = True
        return mask


class RectangularDataSelection(DataSelection):
    """
    Simple 1D interval selection on a chosen parameter index.

    If invert=False (default): mask values outside [lower, upper].
    If invert=True:  mask values inside (lower, upper) (open interval).
    """

    def __init__(
        self,
        parameter_idx: int,
        lower: float,
        upper: float,
        invert: bool = False,
        enabled: bool = True,
        name: Optional[str] = None,
    ):
        self.parameter_idx = int(parameter_idx)
        self.lower = float(lower)
        self.upper = float(upper)
        self.invert = bool(invert)
        self.enabled = bool(enabled)
        self.name = name
        # Deterministic ID for cache stability when reconstructed from UI
        self.selection_id = f"rect_{self.parameter_idx}_{self.lower:.6f}_{self.upper:.6f}_{self.invert}_{self.enabled}"

    def gate_key(self) -> tuple:
        """See :func:`ndxplorer.core.data.mask_state.gate_key`."""
        return ("interval", int(self.parameter_idx), float(self.lower), float(self.upper),
                bool(self.invert), bool(self.enabled))

    def __str__(self) -> str:  # pragma: no cover
        return (f"RectangularDataSelection:\nBounds: {self.lower}, {self.upper}\n"
                f"Invert: {self.invert}\nEnabled: {self.enabled}\n")

    def get_mask(self, data: np.ndarray) -> np.ndarray:
        n_param, n_pts = data.shape
        mask = np.zeros((n_param, n_pts), dtype=bool)
        if not self.enabled:
            return mask
        if self.parameter_idx >= n_param:
            print(f"Parameter idx {self.parameter_idx} exceeds dimension {n_param}.", file=sys.stderr)
            return mask

        vals = data[self.parameter_idx, :]
        if self.invert:
            bad = (vals > self.lower) & (vals < self.upper)  # mask inside
        else:
            bad = (vals < self.lower) | (vals > self.upper)  # mask outside
        mask[:, bad] = True
        return mask


class MaskDataSelection(DataSelection):
    """
    Selection based on a 2D bitmap mask applied to two parameters.
    """

    def __init__(
        self,
        idx1: int,
        idx2: int,
        mask: np.ndarray,
        edges1: np.ndarray,
        edges2: np.ndarray,
        invert: bool = False,
        enabled: bool = True,
        name: Optional[str] = None,
    ):
        import uuid
        self.selection_id = str(uuid.uuid4())
        self.idx1 = int(idx1)
        self.idx2 = int(idx2)
        self.mask = mask  # The 2D bitmap (H, W) or (ny, nx)
        self.edges1 = edges1  # x-edges
        self.edges2 = edges2  # y-edges
        self.invert = bool(invert)
        self.enabled = bool(enabled)
        self.name = name

    def gate_key(self) -> tuple:
        """See :func:`ndxplorer.core.data.mask_state.gate_key`.

        The brush paints into ``mask`` in place, so the key hashes its content;
        the construction-time ``selection_id`` would never change.
        """
        return ("bitmap", int(self.idx1), int(self.idx2), bool(self.invert), bool(self.enabled),
                _array_digest(self.mask), _array_digest(np.asarray(self.edges1, dtype=float)),
                _array_digest(np.asarray(self.edges2, dtype=float)))

    def inside(self, x: np.ndarray, y: np.ndarray) -> np.ndarray:
        """Which points fall in a painted bin. Points outside the edges, or with a
        missing coordinate, are not inside.

        The mask is stored transposed, as displayed: ``(len(edges2)-1, len(edges1)-1)``.
        A mask in the histogram's own ``(nx, ny)`` orientation is read that way; one
        of another shape is padded or trimmed to the edges, as the brush's off-by-one
        results used to be.
        """
        x = np.asarray(x, dtype=float)
        y = np.asarray(y, dtype=float)
        edges1 = np.asarray(self.edges1, dtype=float)
        edges2 = np.asarray(self.edges2, dtype=float)
        nx_bins = len(edges1) - 1
        ny_bins = len(edges2) - 1
        mask = np.asarray(self.mask)
        transposed = mask.shape == (ny_bins, nx_bins)
        if not transposed and mask.shape != (nx_bins, ny_bins):
            fitted = np.zeros((ny_bins, nx_bins), dtype=mask.dtype)
            m_ny = min(mask.shape[0], ny_bins)
            m_nx = min(mask.shape[1], nx_bins)
            fitted[:m_ny, :m_nx] = mask[:m_ny, :m_nx]
            mask = fitted
            transposed = True
        ix = np.searchsorted(edges1, x, side='right') - 1
        iy = np.searchsorted(edges2, y, side='right') - 1
        ix = np.where(x == edges1[-1], nx_bins - 1, ix)
        iy = np.where(y == edges2[-1], ny_bins - 1, iy)
        valid = (ix >= 0) & (ix < nx_bins) & (iy >= 0) & (iy < ny_bins)
        result = np.zeros(x.shape[0], dtype=bool)
        if transposed:
            result[valid] = mask[iy[valid], ix[valid]] > 0
        else:
            result[valid] = mask[ix[valid], iy[valid]] > 0
        return result

    def get_mask(self, data: np.ndarray) -> np.ndarray:
        from ..logging_config import logging
        logging.info(f"=== MaskDataSelection.get_mask called for '{self.name}' ===")
        n_param, n_pts = data.shape
        logging.info(f"  Data shape: ({n_param}, {n_pts})")
        logging.info(f"  Enabled: {self.enabled}, Invert: {self.invert}")
        
        bool_mask = np.zeros((n_param, n_pts), dtype=bool)
        if not self.enabled:
            logging.warning(f"  Selection is DISABLED - returning empty mask")
            return bool_mask
        
        if self.idx1 >= n_param or self.idx2 >= n_param:
            logging.warning(f"MaskDataSelection indices {self.idx1}, {self.idx2} out of bounds for data with {n_param} parameters")
            return bool_mask

        x_vals = data[self.idx1, :]
        y_vals = data[self.idx2, :]
        
        # Log mask and edges dimensions for debugging
        logging.info(f"  Mask shape: {self.mask.shape}, edges1_len={len(self.edges1)}, edges2_len={len(self.edges2)}")
        
        # The mask is stored in TRANSPOSED form to match the displayed image
        # Display uses img = H.T, so mask has shape (ny_bins, nx_bins)
        # where ny_bins = len(edges2)-1 and nx_bins = len(edges1)-1
        logging.info(f"  Expected TRANSPOSED mask: mask.shape[0] should match len(edges2)-1={len(self.edges2)-1}, mask.shape[1] should match len(edges1)-1={len(self.edges1)-1}")
        logging.info(f"  Mask has {np.count_nonzero(self.mask)} non-zero pixels out of {self.mask.size} total")
        
        # Handle mask shape mismatch by resizing if needed (off-by-one errors in histogram computation)
        # Expected shape is TRANSPOSED: (ny_bins, nx_bins)
        expected_shape = (len(self.edges2) - 1, len(self.edges1) - 1)
        if self.mask.shape != expected_shape:
            logging.warning(f"  Mask shape {self.mask.shape} doesn't match expected TRANSPOSED shape {expected_shape}, attempting to resize")
            # Pad or trim the mask to match expected shape
            new_mask = np.zeros(expected_shape, dtype=self.mask.dtype)
            min_ny = min(self.mask.shape[0], expected_shape[0])
            min_nx = min(self.mask.shape[1], expected_shape[1])
            new_mask[:min_ny, :min_nx] = self.mask[:min_ny, :min_nx]
            self.mask = new_mask
            logging.info(f"  Resized mask to {self.mask.shape}")

        # Find bin indices for all data points
        # Use side='right' to ensure edges[i] <= x < edges[i+1] maps to i
        ix = np.searchsorted(self.edges1, x_vals, side='right') - 1
        iy = np.searchsorted(self.edges2, y_vals, side='right') - 1

        # Clip points exactly on the upper boundary to the last bin
        # (Since bins are usually [e_i, e_i+1), the very last bin is [e_n-1, e_n])
        # Note: mask should have shape (len(edges2)-1, len(edges1)-1) = (ny, nx)
        # where mask[iy, ix] accesses the bin for point (x_vals, y_vals)
        ix = np.where(x_vals == self.edges1[-1], len(self.edges1) - 2, ix)
        iy = np.where(y_vals == self.edges2[-1], len(self.edges2) - 2, iy)

        # Check which points fall within the histogram range
        # Use edges to determine valid range, not mask.shape which may be transposed
        nx_bins = len(self.edges1) - 1
        ny_bins = len(self.edges2) - 1
        valid = (ix >= 0) & (ix < nx_bins) & \
                (iy >= 0) & (iy < ny_bins)
        
        logging.info(f"  Bin index ranges: ix=[{np.min(ix[valid]) if np.any(valid) else 'N/A'}, {np.max(ix[valid]) if np.any(valid) else 'N/A'}], iy=[{np.min(iy[valid]) if np.any(valid) else 'N/A'}, {np.max(iy[valid]) if np.any(valid) else 'N/A'}]")
        
        # If invert=False: mask points OUTSIDE the orange area (keep inside)
        # If invert=True: mask points INSIDE the orange area (exclude inside)
        
        # Start with all points masked out (excluded)
        bad = np.ones(n_pts, dtype=bool)
        
        if np.any(valid):
            # For points within histogram range, check the mask
            # points are bad if mask value is 0 (not selected)
            in_selection = np.zeros(n_pts, dtype=bool)
            
            # The mask is stored in TRANSPOSED form: (ny_bins, nx_bins)
            # This matches the displayed image which is H.T
            # So we use mask[iy, ix] indexing to access the correct bins
            if self.mask.shape[0] == ny_bins and self.mask.shape[1] == nx_bins:
                # Mask is in transposed form (matches display): mask[iy, ix]
                in_selection[valid] = self.mask[iy[valid], ix[valid]] > 0
                logging.info(f"  Using mask[iy, ix] indexing (TRANSPOSED form, matches display)")
            elif self.mask.shape[0] == nx_bins and self.mask.shape[1] == ny_bins:
                # Mask is in original histogram2d form: mask[ix, iy]
                in_selection[valid] = self.mask[ix[valid], iy[valid]] > 0
                logging.warning(f"  Mask in original histogram2d form! Using mask[ix, iy] indexing")
            else:
                logging.error(f"  Mask shape {self.mask.shape} doesn't match expected bins (ny={ny_bins}, nx={nx_bins})")
                return bool_mask
            
            if not self.invert:
                # Keep points in selection, mask everything else
                bad = ~in_selection
            else:
                # Mask points in selection, keep everything else
                bad = in_selection
            
            # Diagnostic statistics
            n_valid = np.count_nonzero(valid)
            n_kept = np.count_nonzero(~bad)
            x_min, x_max = np.min(x_vals), np.max(x_vals)
            y_min, y_max = np.min(y_vals), np.max(y_vals)
            logging.info(f"MaskDataSelection '{self.name}': {n_valid}/{n_pts} points in range, {n_kept} points kept (invert={self.invert})")
            logging.info(f"  Data Range: X=[{x_min:.2f}, {x_max:.2f}], Y=[{y_min:.2f}, {y_max:.2f}]")
            logging.info(f"  Edges Range: X=[{self.edges1[0]:.2f}, {self.edges1[-1]:.2f}], Y=[{self.edges2[0]:.2f}, {self.edges2[-1]:.2f}]")
        else:
            # No points in range, if invert=False, everything is bad
            if self.invert:
                bad = np.zeros(n_pts, dtype=bool)
            else:
                bad = np.ones(n_pts, dtype=bool)
            
            x_min, x_max = (np.min(x_vals), np.max(x_vals)) if n_pts > 0 else (0, 0)
            y_min, y_max = (np.min(y_vals), np.max(y_vals)) if n_pts > 0 else (0, 0)
            logging.info(f"MaskDataSelection '{self.name}': NO valid points in range. {np.count_nonzero(~bad)} points kept (invert={self.invert})")
            logging.info(f"  Data Range: X=[{x_min:.2f}, {x_max:.2f}], Y=[{y_min:.2f}, {y_max:.2f}]")
            logging.info(f"  Edges Range: X=[{self.edges1[0]:.2f}, {self.edges1[-1]:.2f}], Y=[{self.edges2[0]:.2f}, {self.edges2[-1]:.2f}]")

        bool_mask[:, bad] = True
        return bool_mask


# ---------------------------
# DataSource
# ---------------------------

#: Prefix of the scratch columns :mod:`tttrlib_selection` appends to the store.
GATE_SCRATCH_PREFIX = "__gate_"


def _left_of_pipe(name) -> str:
    return str(name).split("|", 1)[0].strip().lower()


def float_column(store: "tttrlib.DataStore", index: int,
                 dtype=np.float64) -> np.ndarray:
    """One column of `store` as a new float array.

    A row the column marks as not measured reads as NaN, and so does every row
    of a text column: neither holds a number.
    """
    column = store[int(index)]
    if column.type() == tttrlib.ColumnType_String:
        return np.full(int(store.n_rows()), np.nan, dtype=dtype)
    values = np.array(column.numpy(), dtype=dtype, copy=True)
    if column.has_missing():
        values[~column.mask_numpy()[:len(values)]] = np.nan
    return values


def store_from_columns(columns: Mapping[str, Any]) -> "tttrlib.DataStore":
    """A :class:`tttrlib.DataStore` holding `columns`, in mapping order.

    Numeric arrays keep their dtype; a sequence of strings becomes a
    dictionary-encoded text column.
    """
    store = tttrlib.DataStore()
    n_rows = None
    for name, values in columns.items():
        array = np.asarray(values)
        if array.ndim == 0:
            array = array.reshape(1)
        store.add(str(name), array)
        n_rows = len(array) if n_rows is None else n_rows
    if n_rows is not None:
        store.set_n_rows(int(n_rows))
    return store


def store_with_columns(store: "tttrlib.DataStore",
                       names: Sequence[str]) -> "tttrlib.DataStore":
    """A new store holding copies of the columns `names` of `store`, in that order."""
    out = tttrlib.DataStore()
    for name in names:
        index = store.find(str(name))
        if index < 0:
            raise KeyError(name)
        column = store[index]
        out.add(str(name), column.numpy())
        if column.has_missing():
            out[out.n_columns() - 1].set_mask(
                np.ascontiguousarray(column.mask_numpy(), dtype=np.uint8))
    out.set_n_rows(int(store.n_rows()))
    return out


class DataSource:
    """
    The table: one :class:`tttrlib.DataStore`, and what the program asks of it.

    - column access by name or position (:meth:`column_view` without a copy,
      :meth:`column_values` as a float copy),
    - column edits that keep every other column where it is,
    - computed columns from equations and constants,
    - gates evaluated in the store (:meth:`selection_mask`),
    - row subsets (:meth:`take`) and merges by columns or rows.

    Columns are addressed by position throughout the program; a store refuses
    two columns of one name, so position and name always agree.
    """

    def __init__(self, store: Optional["tttrlib.DataStore"] = None,
                 is_computed: bool = False):
        self._store = store if store is not None else tttrlib.DataStore()
        self.is_computed = is_computed
        self._data_version = 0
        self._parameter_names: Optional[List[str]] = None
        self._cached_values_array: Optional[np.ndarray] = None
        self._relevant_columns_cache = None
        self._gate_scratch: Dict[Any, int] = {}

    @classmethod
    def from_columns(cls, columns: Mapping[str, Any],
                     is_computed: bool = False) -> "DataSource":
        """A source holding `columns` (name → array), in mapping order."""
        return cls(store_from_columns(columns), is_computed=is_computed)

    def __str__(self) -> str:  # pragma: no cover
        return repr(self._store)

    def __len__(self) -> int:
        return self.size

    # ---- the store ----

    @property
    def store(self) -> "tttrlib.DataStore":
        """The :class:`tttrlib.DataStore` holding the table.

        Gates leave their answer in its row selection and may append scratch
        columns past :attr:`n_parameters`; everything else goes through the
        methods of this class so the caches stay right.
        """
        return self._store

    def replace_store(self, store: "tttrlib.DataStore") -> None:
        """Make `store` the table, dropping everything derived from the old one."""
        self._store = store
        self._gate_scratch = {}
        self._structure_changed()

    def _drop_gate_scratch(self) -> None:
        """Remove the gate scratch columns, so new columns land at the next position."""
        store = self._store
        for index in range(store.n_columns() - 1, -1, -1):
            if store.column(index).name().startswith(GATE_SCRATCH_PREFIX):
                store.remove_column(index)
        self._gate_scratch = {}

    def _structure_changed(self) -> None:
        self._parameter_names = None
        self._values_changed()

    def _values_changed(self) -> None:
        """Drop everything derived from the numbers and bump :attr:`data_version`."""
        self._cached_values_array = None
        self._relevant_columns_cache = None
        # The scratch columns stay where they are and are rewritten in place on
        # the next gate evaluation.
        self._gate_scratch = {}
        self._data_version += 1

    # ---- shape ----

    @property
    def parameter_names(self) -> List[str]:
        if self._parameter_names is None:
            store = self._store
            names = [store.column(i).name() for i in range(store.n_columns())]
            self._parameter_names = [n for n in names
                                     if not n.startswith(GATE_SCRATCH_PREFIX)]
        return self._parameter_names

    @property
    def n_parameters(self) -> int:
        """How many parameter columns the table has."""
        return len(self.parameter_names)

    @property
    def size(self) -> int:
        """How many rows the table has."""
        return int(self._store.n_rows()) if self.n_parameters else 0

    @property
    def empty(self) -> bool:
        return self._store.n_rows() == 0 or self.n_parameters == 0

    @property
    def data_version(self) -> int:
        """Monotonic counter bumped whenever the table changes.

        Lets caches detect a change with an integer compare instead of hashing
        the columns on every access.
        """
        return self._data_version

    # ---- reading columns ----

    def column_index(self, name: str) -> int:
        """The position of `name`, or -1.

        An exact match first, then case-insensitive on the part left of ``|``.
        """
        names = self.parameter_names
        if name in names:
            return names.index(name)
        wanted = _left_of_pipe(name)
        for i, candidate in enumerate(names):
            if _left_of_pipe(candidate) == wanted:
                return i
        return -1

    def has_column(self, name: str) -> bool:
        return self.column_index(name) >= 0

    def is_text_column(self, index: int) -> bool:
        return self._store.column(int(index)).type() == tttrlib.ColumnType_String

    def column_view(self, index: int) -> Optional[np.ndarray]:
        """One column as a view INTO the store, in its own dtype -- no copy.

        The view keeps the store alive. Write to it and you have written to the
        table; :meth:`column_values` is the copying form. A text column holds no
        numbers and reads as a new all-NaN float32 array.
        """
        if not (0 <= int(index) < self.n_parameters):
            return None
        if self.is_text_column(index):
            return np.full(int(self._store.n_rows()), np.nan, dtype=np.float32)
        return self._store[int(index)].numpy()

    def column_values(self, name: str) -> Optional[np.ndarray]:
        """One column as a new float64 array, or ``None`` if there is no such column.

        Rows marked not measured, and text, read as NaN.
        """
        if name is None:
            return None
        index = self.column_index(name)
        if index < 0:
            return None
        return float_column(self._store, index)

    def column_items(self, index: int) -> np.ndarray:
        """One column's values as they are stored: numbers in their dtype, text as str."""
        return np.array(self._store[int(index)].numpy(), copy=True)

    @property
    def values(self) -> np.ndarray:
        """The table as a ``(n_parameters, n_points)`` float32 array (cached).

        A copy of every column; a caller that needs one or two columns reads
        them with :meth:`column_view` instead.
        """
        if self._cached_values_array is None:
            store = self._store
            columns = [float_column(store, i, dtype=np.float32)
                       for i in range(self.n_parameters)]
            self._cached_values_array = (
                np.vstack(columns) if columns
                else np.zeros((0, 0), dtype=np.float32))
        return self._cached_values_array

    # ---- editing columns ----

    def set_column(self, name: str, values) -> int:
        """Write `values` into the column `name`, adding it at the end if new.

        An existing column keeps its position and takes the dtype of `values`;
        a scalar fills every row. Returns the column's position.
        """
        store = self._store
        array = np.asarray(values)
        n_rows = int(store.n_rows())
        if array.ndim == 0 and (self.n_parameters or n_rows):
            array = np.full(n_rows, array.item(),
                            dtype=array.dtype if array.dtype.kind != "U" else object)
        if self.n_parameters and len(array) != n_rows:
            raise ValueError(
                "column %r has %d rows, the table has %d" % (name, len(array), n_rows))
        index = store.find(str(name))
        if index >= 0:
            column = store.column(index)
            if column.type() == tttrlib.ColumnType_String or array.dtype.kind in ("U", "S", "O"):
                # Text is appended code by code, so the column is rebuilt.
                self._drop_gate_scratch()
                return self._rebuild_column(index, str(name), array)
            column.clear_mask()
            column.set_numpy(array)
            self._values_changed()
            return index
        self._drop_gate_scratch()
        store.add(str(name), array)
        if store.n_columns() == 1:
            store.set_n_rows(len(array))
        self._structure_changed()
        return store.n_columns() - 1

    def _rebuild_column(self, index: int, name: str, array: np.ndarray) -> int:
        store = self._store
        tail = [store.column(i).name() for i in range(index + 1, store.n_columns())]
        rest = store_with_columns(store, tail)
        for i in range(store.n_columns() - 1, index - 1, -1):
            store.remove_column(i)
        store.add(name, array)
        store.append_columns(rest)
        self._structure_changed()
        return index

    def remove_column(self, name: str) -> bool:
        """Remove the column `name`; the columns after it move up one position."""
        index = self._store.find(str(name))
        if index < 0:
            return False
        self._drop_gate_scratch()
        self._store.remove_column(index)
        self._structure_changed()
        return True

    def rename_column(self, name: str, new_name: str) -> bool:
        index = self._store.find(str(name))
        if index < 0:
            return False
        if self._store.find(str(new_name)) >= 0:
            raise ValueError("a column named %r exists" % new_name)
        self._store.column(index).set_name(str(new_name))
        self._structure_changed()
        return True

    def clear(self) -> None:
        self.replace_store(tttrlib.DataStore())

    # ---- rows ----

    def take(self, rows) -> "DataSource":
        """A new source holding `rows` (positions, or one bool per row), in that order."""
        rows = np.asarray(rows)
        if rows.dtype == bool:
            rows = np.flatnonzero(rows)
        taken = self._store.take(np.ascontiguousarray(rows, dtype=np.int32))
        source = DataSource(taken, is_computed=self.is_computed)
        source._drop_gate_scratch()
        return source

    def copy(self) -> "DataSource":
        """An independent copy of the table, without its row selection."""
        source = DataSource(self._store.copy(), is_computed=self.is_computed)
        source._store.clear_row_mask()
        source._drop_gate_scratch()
        return source

    # ---- equations ----

    def compute_columns(
        self,
        constants: Dict[str, float],
        equations: Optional[List[Dict[str, str]]] = None,
        equation_json_fn: Optional[str] = None,
        changed_constants: Optional[Set[str]] = None,
        targets: Optional[Sequence[str]] = None,
    ) -> List[str]:
        """Evaluate the equations into the store; returns the columns written."""
        self._drop_gate_scratch()
        n_before = self._store.n_columns()
        computed = compute_values(
            store=self._store,
            constants=constants,
            equations=equations,
            equation_json_fn=equation_json_fn,
            changed_constants=changed_constants,
            targets=targets,
        )
        self.is_computed = True
        if self._store.n_columns() != n_before:
            self._structure_changed()
        else:
            self._values_changed()
        return computed

    # ---- gates ----

    def selection_mask(self, selections, idxs=(), mask_nan: bool = True,
                       mask_inf: bool = True) -> np.ndarray:
        """Which rows survive every gate. ``True`` means KEPT.

        The one place a gate is evaluated. It happens in the store: the columns
        are already there in their own dtype, the answer is a bit per row, and
        the histogram fill reads that bit directly.

        :param selections: the gates, in any order; disabled ones are ignored
        :param idxs: columns that must have a finite value for the row to count
        :param mask_nan, mask_inf: which kinds of non-finite ``idxs`` rejects
        """
        from . import tttrlib_selection
        store = self._store
        n_rows = int(store.n_rows())
        if n_rows == 0:
            return np.zeros(0, dtype=bool)
        if not selections and not idxs:
            return np.ones(n_rows, dtype=bool)
        return tttrlib_selection.apply(
            store, selections, idxs=idxs, mask_nan=mask_nan,
            mask_inf=mask_inf, n_columns=self.n_parameters,
            scratch=self._gate_scratch,
        )

    def query_mask(self, query: str) -> np.ndarray:
        """Rows kept by a boolean query over the parameter columns.

        Evaluated by ``DataStore.expression_mask``: compiled once and run over
        the columns in their own types. The store's own selection is untouched.

        Parameters
        ----------
        query : str
            Boolean expression over the parameter names. ``&``, ``|`` and
            ``~`` mean and, or and not.

        Returns
        -------
        numpy.ndarray
            Boolean array, one entry per row.

        Raises
        ------
        ValueError
            If the query does not compile, or names an unknown parameter.
        """
        store = self._store
        mask = store.expression_mask(query)
        out = np.empty(int(store.n_rows()), dtype=np.uint8)
        mask.to_bytes(out)
        return out.astype(bool)

    def query_count(self, query: str) -> int:
        """How many rows a query keeps, without materialising a mask."""
        return int(self._store.count_expression(query))

    def get_mask(
        self,
        selections: List[DataSelection],
        idxs: Optional[List[int]] = None,
        mask_nan: bool = True,
        mask_inf: bool = True,
    ) -> np.ndarray:
        """
        Combine selection masks and optionally mask NaN/Inf on selected parameter indices.

        Returns
        -------
        mask : np.ndarray (bool), shape (n_parameters, n_points)
            True → masked/excluded. One read-only row broadcast over the parameters.
        """
        idxs = idxs or []
        n_param, n_pts = self.n_parameters, self.size
        if not selections and not idxs:
            return np.zeros((n_param, n_pts), dtype=bool)
        keep = self.selection_mask(selections, idxs=idxs,
                                   mask_nan=mask_nan, mask_inf=mask_inf)
        return np.broadcast_to(~keep, (n_param, n_pts))

    # ---- column filtering for performance ----

    def get_relevant_column_indices(
        self,
        axis_indices: List[int],
        selections: List[DataSelection],
        extra_indices: Optional[List[int]] = None,
    ) -> List[int]:
        """
        Collect all column indices that are actually needed for current operations.

        Parameters
        ----------
        axis_indices : List[int]
            Indices of axis columns (x, y, z, weight, etc.).
        selections : List[DataSelection]
            Current selections that reference columns by index.
        extra_indices : Optional[List[int]]
            Any additional column indices to include.

        Returns
        -------
        List[int]
            Sorted, unique list of column indices needed.
        """
        indices: Set[int] = set(axis_indices)
        if extra_indices:
            indices.update(extra_indices)

        for sel in selections:
            if isinstance(sel, RectangularDataSelection):
                indices.add(sel.parameter_idx)
            elif isinstance(sel, Gaussian2DSelection):
                indices.add(sel.parameter_idx1)
                indices.add(sel.parameter_idx2)

        n_cols = self.n_parameters
        return sorted(idx for idx in indices if 0 <= idx < n_cols)

    def get_values_subset(
        self,
        column_indices: List[int],
    ) -> Tuple[np.ndarray, Dict[int, int]]:
        """
        The columns `column_indices` as a ``(len(column_indices), n_points)`` float32 array.

        Returns
        -------
        subset : np.ndarray
        index_map : Dict[int, int]
            Mapping from original column index to new index in the subset.
        """
        cache_key = tuple(column_indices)
        if (self._relevant_columns_cache is not None
                and self._relevant_columns_cache[0] == cache_key):
            return self._relevant_columns_cache[1], self._relevant_columns_cache[2]

        if not column_indices:
            return np.empty((0, self.size), dtype=np.float32), {}

        subset = np.vstack([float_column(self._store, i, dtype=np.float32)
                            for i in column_indices])
        index_map = {orig: new for new, orig in enumerate(column_indices)}
        self._relevant_columns_cache = (cache_key, subset, index_map)
        return subset, index_map

    def get_mask_subset(
        self,
        selections: List[DataSelection],
        axis_indices: List[int],
        mask_nan: bool = True,
        mask_inf: bool = True,
    ) -> np.ndarray:
        """Per-point exclusion mask: the gates, and non-finite values on the axes.

        Returns
        -------
        mask : np.ndarray (bool), shape (n_points,)
            True where the point is excluded.
        """
        keep = self.selection_mask(selections, idxs=list(axis_indices or []),
                                   mask_nan=mask_nan, mask_inf=mask_inf)
        return ~keep

    # ---- merge ----

    def merge(self, other_source: "DataSource", mode: str = 'columns',
              warn=None) -> bool:
        """
        Merge data from another DataSource.

        ``'columns'`` puts the other table's columns beside these (same rows;
        a name already present keeps this table's column). ``'rows'`` stacks the
        other table's rows under these, keeping only the columns both have.

        ``warn(title, message)`` is told why rows or columns were left out or
        the merge refused; without one the reason is logged. The GUI passes
        its message box -- the table does not raise dialogs itself.

        Returns
        -------
        bool
            True on success, False otherwise.
        """
        def _warn(title: str, msg: str) -> None:
            if warn is not None:
                warn(title, msg)
            else:
                logging.warning("merge: %s: %s", title, msg)

        own_names = list(self.parameter_names)
        other_names = list(other_source.parameter_names)

        if mode == 'columns':
            if self.size != other_source.size and self.n_parameters:
                _warn(
                    "Row Count Mismatch",
                    f"New data has {other_source.size} rows, current has {self.size} rows. Not merging."
                )
                return False
            new = [n for n in other_names if n not in own_names]
            if not new:
                return True
            self._drop_gate_scratch()
            addition = store_with_columns(other_source.store, new)
            if not own_names:
                self.replace_store(addition)
                return True
            self._store.append_columns(addition)
            self._structure_changed()
            return True

        if mode == 'rows':
            new_unique = set(other_names) - set(own_names)
            if new_unique:
                _warn(
                    "New Columns Found",
                    f"New data contains columns not in current data: {', '.join(sorted(new_unique))}. "
                    f"Only rows of existing columns will be appended."
                )
            common = sorted(set(own_names).intersection(other_names))
            if not common:
                _warn("No Common Columns", "No overlapping columns. Cannot append rows.")
                return False
            combined = store_with_columns(self._store, common)
            appended = store_with_columns(other_source.store, common)
            for name in common:
                mine, theirs = combined[name], appended[name]
                if (mine.type() != theirs.type() and mine.is_numeric()
                        and theirs.is_numeric()):
                    # Two numeric types meet in float64, which holds both.
                    for column in (mine, theirs):
                        column.set_numpy(np.asarray(column.numpy(), dtype=np.float64))
            combined.append_rows(appended, tttrlib.DataStore.Join_Inner)
            self.replace_store(combined)
            return True

        _warn("Invalid Merge Mode", f"Invalid mode: {mode}. Must be 'columns' or 'rows'.")
        return False
