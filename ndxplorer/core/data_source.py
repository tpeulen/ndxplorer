#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Data utilities: case-insensitive column lookup, computed columns from formulas,
and selection masks (rectangular & 2D Gaussian). Includes a DataSource wrapper.

Key improvements
---------------
- De-duplicated imports & added type hints/docstrings.
- Robust equation-file loading (YAML or JSON by extension).
- Constant handling fixed: quoted names that match constants are wrapped as c['Name'].
- Safer evaluation: try pandas.eval (engine='python'), fall back to plain eval.
- Case-insensitive + "left-of-pipe" column matching preserved.
- DataSource cache invalidation and merge helpers retained and clarified.
"""

from __future__ import annotations

import abc
import json
import sys
from typing import Dict, List, Optional, Iterable, Any, Set, Tuple
from collections import OrderedDict

import numpy as np
import pandas as pd

from ..logging_config import logging

try:
    import yaml  # optional
except Exception:  # pragma: no cover
    yaml = None  # type: ignore

# ---------------------------
# Fast numeric conversion
# ---------------------------

def _fast_to_numeric(df: pd.DataFrame, use_float32: bool = True) -> pd.DataFrame:
    """Convert DataFrame columns to numeric; anything that is not a number becomes NaN.

    Parameters
    ----------
    df : pd.DataFrame
        Input DataFrame with potentially mixed types
    use_float32 : bool
        If True (default), use float32 to halve memory usage.
    """
    if df.empty:
        return df.copy()
    target_dtype = np.float32 if use_float32 else np.float64
    result = df.copy()
    for col in result.columns:
        if not pd.api.types.is_numeric_dtype(result[col]):
            result[col] = pd.to_numeric(result[col], errors='coerce').astype(target_dtype)
        elif result[col].dtype != target_dtype:
            result[col] = result[col].astype(target_dtype)
    return result


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
    d: pd.DataFrame,
    constants: Dict[str, float],
    equations: Optional[List[Dict[str, str]]] = None,
    equation_json_fn: Optional[str] = None,
    engine: str = "python",
    changed_constants: Optional[Set[str]] = None,
    targets: Optional[Sequence[str]] = None,
) -> List[str]:
    """
    Compute columns in DataFrame `d` from `equations`, using case-insensitive
    column lookup and quoted-name replacement for data/constant references.

    Parameters
    ----------
    d : pd.DataFrame
        The table to augment; new columns are added/overwritten in-place.
    constants : Dict[str, float]
        Name → value constants. Accessed in formulas as c['Name'].
    equations : Optional[List[Dict[str, str]]]
        List of {new_column_name: "expression"} dicts. If None, taken from file.
    equation_json_fn : Optional[str]
        Path to YAML/JSON file with equations (detected by extension).
    engine : str
        Passed to pandas.eval. Use 'python' (default) for widest syntax support.

    Notes
    -----
    - Expressions may refer to columns or constants using *quoted* names:
        'Sg' / 'Sr'               -> columns
        'Bg'                      -> constant (if present in `constants`)
    - The preprocessor will auto-wrap quoted names not already written
      as d['...'] or c['...'] into the appropriate form (favoring data columns).
    """
    equations = equations or []
    if not equations and equation_json_fn:
        try:
            equations = _load_equations_file(equation_json_fn)
        except Exception as e:
            logging.warning(f"compute_values: Failed to load equations from {equation_json_fn}: {e}")
            equations = []

    # Delegate to the AST dependency-graph engine: quoted names resolve by exact
    # (case-insensitive / left-of-pipe) match, equations evaluate in topological
    # order on NumPy arrays, and a changed constant recomputes exactly its
    # transitive dependents. Idempotent by construction and faster than the old
    # string-preprocess + eval pipeline.
    from .equation_graph import compute_values_ast

    return compute_values_ast(
        d, constants or {}, equations,
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
# DataSource wrapper
# ---------------------------


def _numeric_column(series) -> np.ndarray:
    """One DataFrame column as a contiguous float32 array.

    float32 rather than float64 throughout: it halves the table, and no plot
    axis, gate boundary or histogram edge in this program can show the
    difference. A column that is not numeric becomes NaN, which is the store's
    "not measured" and gates as such.

    RECONSTRUCTED after the working-tree copy of this file was lost; the
    docstring and the names it referred to came from the compiled bytecode.
    """
    import pandas as pd
    try:
        if pd.api.types.is_bool_dtype(series):
            return np.ascontiguousarray(series.to_numpy(dtype=np.float32))
        if pd.api.types.is_numeric_dtype(series):
            return np.ascontiguousarray(series.to_numpy(dtype=np.float32))
        coerced = pd.to_numeric(series, errors="coerce")
        return np.ascontiguousarray(coerced.to_numpy(dtype=np.float32))
    except (TypeError, ValueError):
        return np.full(len(series), np.nan, dtype=np.float32)


def build_store(frame, label: str = ""):
    """A :class:`tttrlib.DataStore` holding `frame`'s columns as float32.

    The store is the numeric representation -- there is no second one. Gates are
    evaluated in it, histograms fill out of it, and :attr:`DataSource.values`
    is assembled from it when a caller still wants the whole table at once.

    Columns are addressed by POSITION, never by the name given here: a
    DataFrame may carry the same column name twice, and a lookup by name would
    silently answer with the first.

    RECONSTRUCTED after the working-tree copy of this file was lost.
    """
    import tttrlib
    store = tttrlib.DataStore()
    n_rows = int(len(frame))
    for i in range(frame.shape[1]):
        store.add(str(frame.columns[i]), _numeric_column(frame.iloc[:, i]))
    store.set_n_rows(n_rows)
    if label:
        store.set_label(label)
    return store


class DataSource:
    """
    Light wrapper around a DataFrame that provides:
    - cached numeric values (transposed) for fast selection operations,
    - computed columns from equations/constants,
    - merge (by columns or rows) convenience,
    - masking utilities that combine multiple selections and NaN/Inf culling.
    - **column filtering** for operating on only relevant columns (axes + selections)
    """

    _data: pd.DataFrame
    _data_numeric: pd.DataFrame
    _parameter_names: List[str]
    _relevant_columns_cache: Optional[Tuple[Tuple[int, ...], np.ndarray]] = None

    def __init__(self, parameter_names: Optional[List[str]] = None, data: Optional[pd.DataFrame | np.ndarray] = None, is_computed: bool = False):
        # Performance optimization: initialize cache before data assignment
        self._column_cache = {}
        self._cache_valid = False
        self._cached_values_array = None
        self.is_computed = is_computed
        
        if isinstance(data, np.ndarray):
            self.data = pd.DataFrame(data, columns=parameter_names)
        elif isinstance(data, pd.DataFrame):
            self.data = data
        else:
            self.data = pd.DataFrame()

        if isinstance(parameter_names, list):
            self._parameter_names = parameter_names
        else:
            self._parameter_names = list(self._data.columns)

    def __str__(self) -> str:  # pragma: no cover
        return self._data.__str__()

    def __len__(self) -> int:
        return self.size

    # ---- properties ----

    @property
    def parameter_names(self) -> List[str]:
        return self._parameter_names

    @property
    def values(self) -> np.ndarray:
        """
        Returns (n_parameters, n_points) numeric np.ndarray (cached).
        Optimized for large datasets with lazy evaluation and memory efficiency.
        Uses float32 to halve memory usage compared to float64.
        
        The transposed array is cached to avoid repeated memory copies.
        """
        if self._cached_values_array is not None:
            return self._cached_values_array

        if self._data is None:
            # A store-backed source: the columns are read from the store, not
            # from a DataFrame nobody asked to build.
            store = self.store
            columns = [np.asarray(store[i].numpy(), dtype=np.float32)
                       for i in range(self.n_parameters)]
            self._cached_values_array = (np.vstack(columns) if columns
                                         else np.zeros((0, 0), dtype=np.float32))
            return self._cached_values_array

        # Get underlying numpy array - avoid DataFrame overhead
        numeric_data = self._data_numeric.values
        
        # Convert to float32 only if needed (halves memory vs float64)
        if numeric_data.dtype != np.float32:
            # Use Fortran order for the transposed result to be C-contiguous
            self._cached_values_array = np.ascontiguousarray(
                numeric_data.T, dtype=np.float32
            )
        else:
            # If already float32, just transpose with contiguous memory
            self._cached_values_array = np.ascontiguousarray(numeric_data.T)
        
        return self._cached_values_array

    @property
    def store(self):
        """The :class:`tttrlib.DataStore` holding the numeric columns.

        Built once when the data changes. Gates are evaluated in it and
        histograms fill out of it, so nothing on either path copies the table.
        """
        store = getattr(self, "_store", None)
        if store is None:
            store = build_store(self.data)
            self._store = store
        return store

    @property
    def n_parameters(self) -> int:
        """How many parameter columns the table has."""
        return len(self._parameter_names)

    @classmethod
    def from_store(cls, store, is_computed: bool = False) -> "DataSource":
        """Wrap a :class:`tttrlib.DataStore` -- the store IS the data.

        The shortest path from a file to a plot. A columnar HDF5 or a CSV read
        by tttrlib arrives as a store already, and this takes it as it is: no
        DataFrame is built, no column is converted, and nothing is copied. The
        table can be most of the memory in the process, so "nothing is copied"
        is the difference between a file opening and not.

        The DataFrame is built lazily, and only by the things that genuinely
        need one -- the equation engine, the table editor, a pandas ``query``.
        Loading, gating, histogramming and plotting never ask for it.
        """
        source = cls()
        source._store = store
        source._data = None
        source._data_numeric = None
        source._parameter_names = [store.column(i).name()
                                   for i in range(store.n_columns())]
        source.is_computed = is_computed
        source._invalidate_caches()
        return source

    def column_index(self, name: str) -> int:
        """The position of `name`, or -1.

        Case-insensitive and on the part left of ``|``, as everywhere else. By
        position rather than by name because a table may carry the same column
        name twice and a lookup by name would silently answer with the first.
        """
        wanted = str(name).split("|")[0].strip().lower()
        for i, candidate in enumerate(list(self._parameter_names)):
            if str(candidate).split("|")[0].strip().lower() == wanted:
                return i
        return -1

    def column_view(self, index: int) -> Optional[np.ndarray]:
        """One column as a float32 view INTO the store -- no copy.

        The view keeps the store alive, so it cannot outlive its data. Write to
        it and you have written to the table; :meth:`column_values` is the
        copying form for a caller that wants to modify what it gets.
        """
        if not (0 <= int(index) < self.n_parameters):
            return None
        return self.store[int(index)].numpy()

    def selection_mask(self, selections, idxs=(), mask_nan: bool = True,
                       mask_inf: bool = True) -> np.ndarray:
        """Which rows survive every gate. ``True`` means KEPT.

        The one place a gate is evaluated. It happens in the store: the columns
        are already there in their own dtype, the answer is a bit per row, and
        the histogram fill reads that bit directly -- so no ``(n_parameters,
        n_points)`` boolean array is built, no index array is made from it, and
        no rows are copied.

        :param selections: the gates, in any order; disabled ones are ignored
        :param idxs: columns that must have a finite value for the row to count
        :param mask_nan, mask_inf: which kinds of non-finite ``idxs`` rejects
        """
        from . import tttrlib_selection
        store = self.store
        n_rows = int(store.n_rows())
        if n_rows == 0:
            return np.zeros(0, dtype=bool)
        if not selections and not idxs:
            return np.ones(n_rows, dtype=bool)
        if getattr(self, "_gate_scratch", None) is None:
            self._gate_scratch = {}
        return tttrlib_selection.apply(
            store, selections, idxs=idxs, mask_nan=mask_nan,
            mask_inf=mask_inf, n_columns=self.n_parameters,
            scratch=self._gate_scratch,
        )

    def _refresh_store_columns(self, names) -> bool:
        """Write recomputed columns back into the store, in place.

        **The store is what the picture is made of.** Gates are evaluated in it
        and histograms fill out of it, so a column that changed in ``_data``
        and not in the store is a plot that disagrees with its own numbers —
        which is exactly what a parameter edit produced: the derived FRET
        columns moved and the histograms did not, with nothing anywhere saying
        so.

        Returns
        -------
        bool
            ``True`` when every named column was written. ``False`` means the
            store no longer matches the table (a column was added, or the
            positions moved) and the caller must drop it so it rebuilds —
            columns are addressed by **position**, so a mismatch cannot be
            patched, only rebuilt.
        """
        store = getattr(self, "_store", None)
        if store is None or self._data is None:
            return True
        columns = list(self._data.columns)
        for name in names:
            try:
                index = columns.index(name)
            except ValueError:
                return False
            if index >= store.n_columns() or store.column(index).name() != str(name):
                return False
            try:
                store.column(index).set_numpy(
                    _numeric_column(self._data.iloc[:, index]))
            except Exception:
                return False
        return True

    def _invalidate_caches(self) -> None:
        """Drop everything derived from the numeric data.

        The store itself is kept unless the caller cleared it: rewriting one
        column in place is a targeted refresh, and rebuilding the whole table
        for it is what this exists to avoid.
        """
        self._cached_values_array = None
        self._cache_valid = False
        if hasattr(self, "_column_cache"):
            self._column_cache.clear()
        self._relevant_columns_cache = None
        self._data_version = getattr(self, "_data_version", 0) + 1

    def query_mask(self, query: str) -> np.ndarray:
        """Rows kept by a boolean query over the parameter columns.

        Evaluated by the store itself: ``DataStore.select_expression`` compiles
        the query once and runs it over the columns in their own types --
        float32 bound directly, integers widened through typed pointers --
        writing a bit-packed selection. Nothing is copied per query, and the
        DataFrame is never built for one.

        The store's own selection is left as it was: this answers a question
        rather than applying a gate. To *set* the selection, call
        ``select_expression`` on the store directly, where it composes with
        the other gates through ``Combine_And``/``Or``/``AndNot``.

        Parameters
        ----------
        query : str
            Boolean expression over the parameter names. ``&``, ``|`` and
            ``~`` mean what they do in a pandas query.

        Returns
        -------
        numpy.ndarray
            Boolean array, one entry per row.

        Raises
        ------
        ValueError
            If the query does not compile, or names an unknown parameter.
        """
        store = self.store
        had_mask = store.has_row_mask()
        saved = store.selection().copy() if had_mask else None
        try:
            store.select_expression(query)
            return store.selection().copy()
        finally:
            if had_mask:
                store.select(saved)
            else:
                store.clear_row_mask()

    def query_count(self, query: str) -> int:
        """How many rows a query keeps, without materialising a mask.

        The cheapest form of the question: the store counts the bits and
        nothing crosses into Python.
        """
        return int(self.store.count_expression(query))

    def column_values(self, name: str) -> Optional[np.ndarray]:
        """One numeric column as a float array, or ``None`` if there is no such column.

        :attr:`values` rebuilds a ``(n_parameters, n_points)`` copy of the
        *whole* table whenever anything changed — right once per redraw, ruinous
        inside a fit that recomputes one column and re-reads it thousands of
        times. Names resolve case-insensitively and on the part left of ``|``,
        as everywhere else.
        """
        frame = self._data_numeric if self._data_numeric is not None else self._data
        if frame is None and name is not None and getattr(self, "_store", None) is not None:
            index = self.column_index(name)
            return None if index < 0 else np.array(self._store[index].numpy(), copy=True)
        if frame is None or name is None:
            return None
        column = None
        if name in frame.columns:
            column = name
        else:
            wanted = str(name).lower()
            wanted_left = str(name).split("|", 1)[0].strip().lower()
            for candidate in frame.columns:
                text = str(candidate)
                if text.lower() == wanted or text.split("|", 1)[0].strip().lower() == wanted_left:
                    column = candidate
                    break
        if column is None:
            return None
        return np.asarray(frame[column].values, dtype=float)

    def clear(self) -> None:
        self.data = pd.DataFrame()

    def compute_columns(
        self,
        constants: Dict[str, float],
        equations: Optional[List[Dict[str, str]]] = None,
        equation_json_fn: Optional[str] = None,
        engine: str = "python",
        changed_constants: Optional[Set[str]] = None,
        targets: Optional[Sequence[str]] = None,
    ) -> None:
        computed = compute_values(
            d=self.data,
            constants=constants,
            equations=equations,
            equation_json_fn=equation_json_fn,
            engine=engine,
            changed_constants=changed_constants,
            targets=targets,
        )
        self.is_computed = True

        if changed_constants and computed and getattr(self, "_data_numeric", None) is not None:
            # Targeted refresh: only re-convert the columns that were actually
            # recomputed instead of re-running _fast_to_numeric over the whole
            # (100-column) frame. Avoids a full reconversion on every param edit.
            try:
                existing = [c for c in computed if c in self._data.columns]
                if existing:
                    sub = _fast_to_numeric(self._data[existing])
                    for col in existing:
                        if col in sub.columns:
                            self._data_numeric[col] = sub[col]
                # The store holds its own copy of every column and is what the
                # histograms and gates read. Updating only `_data_numeric` left
                # it on the previous values, so an edited constant changed the
                # table and not the picture.
                if not self._refresh_store_columns(existing):
                    self._store = None
                self._cached_values_array = None
                self._cache_valid = False
                if hasattr(self, "_column_cache"):
                    self._column_cache.clear()
                self._relevant_columns_cache = None
                self._data_version = getattr(self, "_data_version", 0) + 1
                return
            except Exception as exc:
                logging.debug("Targeted numeric refresh failed, full refresh: %s", exc)

        # Full refresh (initial load or no targeting info)
        self.data = self.data

    @property
    def empty(self) -> bool:
        if self._data is None:
            store = self.store
            return store.n_rows() == 0 or store.n_columns() == 0
        return self._data.empty

    def get_mask(
        self,
        selections: List[DataSelection],
        idxs: Optional[List[int]] = None,
        mask_nan: bool = True,
        mask_inf: bool = True,
    ) -> np.ndarray:
        """
        Combine selection masks and optionally mask NaN/Inf on selected parameter indices.
        Optimized for large datasets with vectorized operations and early termination.

        Returns
        -------
        mask : np.ndarray (bool), shape (n_parameters, n_points)
            True → masked/excluded.
        """
        from ..logging_config import logging
        idxs = idxs or []
        d = self.values
        n_param, n_pts = d.shape

        # Pre-allocate mask with zeros for better performance
        mask = np.zeros((n_param, n_pts), dtype=bool)

        # Early exit if no selections and no idx filtering
        if not selections and not idxs:
            return mask

        # The gates are evaluated in tttrlib's DataStore, which answers per row
        # ("True means KEPT"); this method's contract is per parameter row and
        # inverted ("True means masked out"), so the one answer is broadcast:
        # a read-only view, every parameter row the same row.
        keep = self.selection_mask(selections, idxs=idxs,
                                   mask_nan=mask_nan, mask_inf=mask_inf)
        return np.broadcast_to(~keep, (n_param, n_pts))

    @property
    def data(self) -> pd.DataFrame:
        """The table as a DataFrame, built from the store the first time a
        store-backed source is asked for one (the equation engine, the table
        editor); loading, gating and histogramming never ask."""
        if self._data is None and getattr(self, "_store", None) is not None:
            store = self._store
            frame = pd.DataFrame({i: np.array(store[i].numpy(), copy=True)
                                  for i in range(store.n_columns())})
            frame.columns = list(self._parameter_names)
            self._data = frame
            self._data_numeric = frame
        return self._data

    @data.setter
    def data(self, v: pd.DataFrame) -> None:
        # Avoid copy if v is already a DataFrame and caller doesn't need original
        # For large datasets, this saves significant memory and time
        if isinstance(v, pd.DataFrame):
            # Always copy to ensure we own the data and avoid unexpected mutations
            # The copy is necessary for correctness but we optimize the numeric conversion
            self._data = v.copy()
        else:
            self._data = pd.DataFrame()
        self._parameter_names = list(self._data.columns)
        # Optimized numeric conversion using PyArrow when available
        self._data_numeric = _fast_to_numeric(self._data)
        # The store is derived from this table and addresses its columns by
        # position, so a new table invalidates it wholesale. Keeping it meant an
        # in-place data replacement went on plotting the previous table.
        self._store = None
        # Invalidate all caches
        self._cached_values_array = None
        self._cache_valid = False
        if hasattr(self, '_column_cache'):
            self._column_cache.clear()
        # Invalidate column subset cache
        self._relevant_columns_cache = None
        # Bump the monotonic data version so downstream caches can detect a data
        # change with an O(1) integer compare instead of hashing the whole array.
        self._data_version = getattr(self, "_data_version", 0) + 1

    @property
    def size(self) -> int:
        if self._data is None:
            return int(self.store.n_rows()) if not self.empty else 0
        return self.values.shape[1] if not self.empty else 0

    @property
    def data_version(self) -> int:
        """Monotonic counter bumped whenever the underlying data changes.

        Lets caches detect a data change with an O(1) integer compare instead of
        hashing the array on every access.
        """
        return getattr(self, "_data_version", 0)

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

        n_cols = len(self._parameter_names)
        return sorted(idx for idx in indices if 0 <= idx < n_cols)

    def get_values_subset(
        self,
        column_indices: List[int],
    ) -> Tuple[np.ndarray, Dict[int, int]]:
        """
        Return a subset of the values array containing only the specified columns.

        Parameters
        ----------
        column_indices : List[int]
            Original column indices to include.

        Returns
        -------
        subset : np.ndarray
            Shape (len(column_indices), n_points) with only the requested columns.
        index_map : Dict[int, int]
            Mapping from original column index to new index in the subset.
        """
        cache_key = tuple(column_indices)
        if (
            hasattr(self, '_relevant_columns_cache')
            and self._relevant_columns_cache is not None
            and self._relevant_columns_cache[0] == cache_key
        ):
            return self._relevant_columns_cache[1], self._relevant_columns_cache[2]

        all_values = self.values
        if not column_indices:
            empty = np.empty((0, all_values.shape[1]), dtype=np.float32)
            return empty, {}

        subset = all_values[column_indices, :]
        index_map = {orig: new for new, orig in enumerate(column_indices)}
        self._relevant_columns_cache = (cache_key, subset, index_map)
        return subset, index_map

    def get_mask_subset(
        self,
        selections: List[DataSelection],
        axis_indices: List[int],
        mask_nan: bool = True,
        mask_inf: bool = True,
        use_bitfield: bool = True,
    ) -> np.ndarray:
        """Per-point exclusion mask: the gates, and non-finite values on the axes.

        Evaluated in tttrlib's DataStore through :meth:`selection_mask`, the one
        gate implementation. ``use_bitfield`` is ignored.

        Returns
        -------
        mask : np.ndarray (bool), shape (n_points,)
            True where the point is excluded.
        """
        keep = self.selection_mask(selections, idxs=list(axis_indices or []),
                                   mask_nan=mask_nan, mask_inf=mask_inf)
        return ~keep

    # ---- merge helpers ----

    def merge(self, other_source: "DataSource", mode: str = 'columns') -> bool:
        """
        Merge data from another DataSource.

        Parameters
        ----------
        other_source : DataSource
        mode : {'columns', 'rows'}

        Returns
        -------
        bool
            True on success, False otherwise.
        """
        # Lazy import to avoid hard dependency on Qt in headless environments
        def _warn(title: str, msg: str) -> None:
            try:
                from qtpy.QtWidgets import QMessageBox  # type: ignore
                QMessageBox.warning(None, title, msg)
            except Exception:
                print(f"[merge:{title}] {msg}", file=sys.stderr)

        if mode == 'columns':
            if len(self.data) != len(other_source.data):
                _warn(
                    "Row Count Mismatch",
                    f"New data has {len(other_source.data)} rows, current has {len(self.data)} rows. Not merging."
                )
                return False

            duplicate_cols = set(self.data.columns).intersection(set(other_source.data.columns))
            df_unique = other_source.data.drop(columns=list(duplicate_cols)) if duplicate_cols else other_source.data
            combined = pd.concat([self.data, df_unique], axis=1)
            self.data = combined
            return True

        if mode == 'rows':
            existing = set(self.data.columns)
            incoming = set(other_source.data.columns)
            new_unique = incoming - existing
            if new_unique:
                _warn(
                    "New Columns Found",
                    f"New data contains columns not in current data: {', '.join(sorted(new_unique))}. "
                    f"Only rows of existing columns will be appended."
                )

            common = sorted(existing.intersection(incoming))
            if not common:
                _warn("No Common Columns", "No overlapping columns. Cannot append rows.")
                return False

            other_common = other_source.data[common]
            combined = pd.concat([self.data[common], other_common], axis=0, ignore_index=True)
            # Keep original full set of columns if desired; here we keep only common to ensure consistency
            self.data = combined
            return True

        _warn("Invalid Merge Mode", f"Invalid mode: {mode}. Must be 'columns' or 'rows'.")
        return False
