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

# Optional Numba acceleration
try:
    import numba as nb
    _HAVE_NUMBA = True
except ImportError:
    nb = None
    _HAVE_NUMBA = False

# Optional PyArrow for faster numeric conversion
try:
    import pyarrow as pa
    import pyarrow.compute as pc
    _HAVE_PYARROW = True
except ImportError:
    pa = None
    pc = None
    _HAVE_PYARROW = False



# ----------------------------------------
# Numba-accelerated mask computation
# ----------------------------------------

if _HAVE_NUMBA:
    @nb.njit(cache=True, parallel=True, fastmath=True)
    def _rectangular_mask_numba(
        vals: np.ndarray,
        lower: float,
        upper: float,
        invert: bool,
        mask: np.ndarray,
    ) -> None:
        """Apply rectangular selection mask in-place using Numba."""
        n = vals.shape[0]
        for i in nb.prange(n):
            v = vals[i]
            if invert:
                if v > lower and v < upper:
                    mask[i] = True
            else:
                if v < lower or v > upper:
                    mask[i] = True
    
    @nb.njit(cache=True, fastmath=True)
    def _gaussian2d_mask_numba(
        x: np.ndarray,
        y: np.ndarray,
        mu0: float,
        mu1: float,
        inv_cov00: float,
        inv_cov01: float,
        inv_cov11: float,
        sigma_sq: float,
        invert: bool,
        log_x: bool,
        log_y: bool,
        mask: np.ndarray,
    ) -> None:
        """Apply Gaussian 2D selection mask in-place using Numba."""
        n = x.shape[0]
        for i in range(n):
            xv = x[i]
            yv = y[i]
            
            # Apply log transform if needed
            if log_x:
                if xv > 0.0:
                    xv = np.log(xv)
                else:
                    mask[i] = True
                    continue
            if log_y:
                if yv > 0.0:
                    yv = np.log(yv)
                else:
                    mask[i] = True
                    continue
            
            # Check for invalid values
            if not np.isfinite(xv) or not np.isfinite(yv):
                mask[i] = True
                continue
            
            dx = xv - mu0
            dy = yv - mu1
            d2 = inv_cov00 * dx * dx + 2.0 * inv_cov01 * dx * dy + inv_cov11 * dy * dy
            
            if invert:
                if d2 <= sigma_sq:
                    mask[i] = True
            else:
                if d2 > sigma_sq:
                    mask[i] = True

    @nb.njit(cache=True, parallel=True, fastmath=True)
    def _mask_nan_inf_numba(col: np.ndarray, mask: np.ndarray, do_nan: bool, do_inf: bool) -> None:
        """Mask NaN and/or Inf values in-place."""
        n = col.shape[0]
        for i in nb.prange(n):
            v = col[i]
            if do_nan and np.isnan(v):
                mask[i] = True
            elif do_inf and np.isinf(v):
                mask[i] = True

else:
    _rectangular_mask_numba = None
    _gaussian2d_mask_numba = None
    _mask_nan_inf_numba = None


# ---------------------------
# Fast numeric conversion
# ---------------------------

def _fast_to_numeric(df: pd.DataFrame, use_float32: bool = True) -> pd.DataFrame:
    """
    Convert DataFrame columns to numeric efficiently.
    
    Uses PyArrow when available for ~2-5x faster conversion on large DataFrames.
    Falls back to pandas apply() otherwise.
    
    Parameters
    ----------
    df : pd.DataFrame
        Input DataFrame with potentially mixed types
    use_float32 : bool
        If True (default), use float32 to halve memory usage.
    
    Returns
    -------
    pd.DataFrame
        DataFrame with all columns converted to numeric (non-numeric → NaN)
    """
    if df.empty:
        return df.copy()
    
    import time
    t0 = time.perf_counter()
    
    # Target dtype for memory efficiency
    target_dtype = np.float32 if use_float32 else np.float64
    
    if _HAVE_PYARROW:
        pa_target = pa.float32() if use_float32 else pa.float64()
        try:
            # Convert to Arrow Table for fast processing
            table = pa.Table.from_pandas(df, preserve_index=False)
            
            # Convert each column to target float type
            new_columns = []
            for i, col_name in enumerate(table.column_names):
                col = table.column(i)
                col_type = col.type
                
                # If already numeric, cast to target type
                if pa.types.is_floating(col_type) or pa.types.is_integer(col_type):
                    new_columns.append(pc.cast(col, pa_target, safe=False))
                elif pa.types.is_boolean(col_type):
                    new_columns.append(pc.cast(col, pa_target, safe=False))
                else:
                    # String or other type: try to convert
                    try:
                        # Use Arrow's string-to-float conversion
                        new_columns.append(pc.cast(col, pa_target, safe=False))
                    except (pa.ArrowInvalid, pa.ArrowNotImplementedError):
                        # Fall back to pandas for this column
                        series = col.to_pandas()
                        numeric_series = pd.to_numeric(series, errors='coerce').astype(target_dtype)
                        new_columns.append(pa.array(numeric_series.values))
            
            # Reconstruct table and convert back to pandas
            result_table = pa.Table.from_arrays(new_columns, names=table.column_names)
            result = result_table.to_pandas(
                self_destruct=True,
                split_blocks=True,
                zero_copy_only=False,
            )
            
            t1 = time.perf_counter()
            logging.debug("[_fast_to_numeric] PyArrow (%s): %d rows × %d cols in %.3fs",
                         'float32' if use_float32 else 'float64',
                         len(df), len(df.columns), t1 - t0)
            return result
            
        except Exception as e:
            logging.debug("[_fast_to_numeric] PyArrow failed: %s, falling back to pandas", e)
    
    # Fallback to pandas (still optimized)
    result = df.copy()
    for col in result.columns:
        if not pd.api.types.is_numeric_dtype(result[col]):
            result[col] = pd.to_numeric(result[col], errors='coerce').astype(target_dtype)
        elif result[col].dtype != target_dtype:
            result[col] = result[col].astype(target_dtype)
    
    t1 = time.perf_counter()
    logging.debug("[_fast_to_numeric] pandas (%s): %d rows × %d cols in %.3fs",
                 'float32' if use_float32 else 'float64',
                 len(df), len(df.columns), t1 - t0)
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

class DataSelection(abc.ABC):
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

    def __eq__(self, other):
        if not isinstance(other, Gaussian2DSelection):
            return False
        # Fast path check using selection_id if available
        if hasattr(self, 'selection_id') and hasattr(other, 'selection_id'):
            if self.selection_id == other.selection_id:
                # If IDs match, check if properties changed (e.g. enabled/invert)
                return (self.enabled == other.enabled and self.invert == other.invert)
        
        return (self.parameter_idx1 == other.parameter_idx1 and
                self.parameter_idx2 == other.parameter_idx2 and
                np.allclose(self.mu, other.mu) and
                np.allclose(self.cov, other.cov) and
                np.allclose(self.sigma, other.sigma) and
                self.invert == other.invert and
                self.enabled == other.enabled and
                self.log_x == other.log_x and
                self.log_y == other.log_y)

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

    def __eq__(self, other):
        if not isinstance(other, RectangularDataSelection):
            return False
        # Fast path check using selection_id
        if hasattr(self, 'selection_id') and hasattr(other, 'selection_id'):
            if self.selection_id == other.selection_id:
                return (self.enabled == other.enabled and self.invert == other.invert)
                
        return (self.parameter_idx == other.parameter_idx and
                np.allclose(self.lower, other.lower) and
                np.allclose(self.upper, other.upper) and
                self.invert == other.invert and
                self.enabled == other.enabled)

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

    def __eq__(self, other):
        if not isinstance(other, MaskDataSelection):
            return False
        # Fast path check using selection_id
        if hasattr(self, 'selection_id') and hasattr(other, 'selection_id'):
            if self.selection_id == other.selection_id:
                # If IDs match, only check binary properties
                return (self.enabled == other.enabled and self.invert == other.invert)
        
        # Slow path (fallback)
        return (self.idx1 == other.idx1 and
                self.idx2 == other.idx2 and
                self.invert == other.invert and
                self.enabled == other.enabled and
                np.array_equal(self.mask, other.mask) and
                np.array_equal(self.edges1, other.edges1) and
                np.array_equal(self.edges2, other.edges2))

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

    def column_values(self, name: str) -> Optional[np.ndarray]:
        """One numeric column as a float array, or ``None`` if there is no such column.

        :attr:`values` rebuilds a ``(n_parameters, n_points)`` copy of the
        *whole* table whenever anything changed — right once per redraw, ruinous
        inside a fit that recomputes one column and re-reads it thousands of
        times. Names resolve case-insensitively and on the part left of ``|``,
        as everywhere else.
        """
        frame = self._data_numeric if self._data_numeric is not None else self._data
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

        # Fast path: evaluate the gates in tttrlib's DataStore, which holds the
        # columns in their own dtypes and answers with one bit per row. The
        # path below converts the whole table to float64, allocates an
        # (n_parameters, n_points) bool array, copies the coordinates again for
        # the finite points, and then broadcasts one row of results across every
        # parameter row -- four costs that are not the geometry. Measured on
        # five million rows with a 64-vertex lasso: 96 ms against 618 ms.
        #
        # All or nothing: if any selection is a kind tttrlib does not implement,
        # the whole thing falls through, so there is never a partial evaluation
        # or a second mask representation to combine.
        from . import tttrlib_selection
        if tttrlib_selection.can_evaluate(selections):
            try:
                mask, self._tttrlib_selection_cache = tttrlib_selection.evaluate(
                    d, selections, idxs=idxs, mask_nan=mask_nan, mask_inf=mask_inf,
                    cache=getattr(self, "_tttrlib_selection_cache", None),
                    names=list(getattr(self, "parameter_names", []) or []),
                )
                return mask
            except Exception as e:
                # A translation that turns out to be wrong must not take the
                # answer down with it; the numpy path below is still correct.
                logging.warning("tttrlib selection unavailable (%s); using numpy", e)
        
        # Process selections with vectorized operations
        for sel in selections:
            try:
                m = sel.get_mask(d)
                if isinstance(m, np.ndarray) and m.shape == mask.shape:
                    count_before = np.count_nonzero(np.any(mask, axis=0))
                    # Use in-place OR operation for better performance
                    mask |= m
                    count_after = np.count_nonzero(np.any(mask, axis=0))
                    logging.info(f"Applied selection '{getattr(sel, 'name', 'unnamed')}': points masked {count_before} -> {count_after}/{n_pts}")
            except Exception as e:
                logging.error(f"[DataSource.get_mask] Selection error ({getattr(sel, 'name', 'unnamed')}): {e}")

        # Vectorized NaN/Inf filtering for selected indices
        if idxs:
            valid_idxs = np.array([idx for idx in idxs if 0 <= idx < n_param], dtype=int)
            if valid_idxs.size:
                cols = d[valid_idxs, :]
                bad_mask = np.zeros(n_pts, dtype=bool)
                if mask_nan:
                    bad_mask |= np.any(np.isnan(cols), axis=0)
                if mask_inf:
                    bad_mask |= np.any(np.isinf(cols), axis=0)
                if np.any(bad_mask):
                    mask[:, bad_mask] = True

        return mask

    @property
    def data(self) -> pd.DataFrame:
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
        """
        Compute mask using only the relevant columns for better performance.

        This is an optimized version of get_mask that first filters to only
        the columns referenced by selections and axes, reducing memory and
        computation for large datasets with many columns.

        Uses Numba JIT compilation when available for ~10x speedup, operating on
        the native float32 columns to avoid per-rebuild dtype copies.

        Parameters
        ----------
        selections : List[DataSelection]
            Current selections.
        axis_indices : List[int]
            Indices of axis columns (x, y, z).
        mask_nan : bool
            Whether to mask NaN values.
        mask_inf : bool
            Whether to mask Inf values.
        use_bitfield : bool
            Deprecated, ignored. Retained for signature compatibility; the
            bitfield mask path was removed (it converted back to a boolean array
            anyway, giving no memory saving while adding Python-level overhead).

        Returns
        -------
        mask : np.ndarray (bool), shape (n_points,)
            1D mask where True means the point should be excluded.
        """
        relevant_indices = self.get_relevant_column_indices(axis_indices, selections)
        if not relevant_indices:
            return np.zeros(self.size, dtype=bool)

        subset, index_map = self.get_values_subset(relevant_indices)
        n_pts = subset.shape[1]

        mask = np.zeros(n_pts, dtype=bool)

        # Operate on the native subset dtype (float32). The Numba kernels compile a
        # specialisation per dtype, so passing float32 directly avoids a full
        # float64 copy of every column on each mask rebuild (~3x faster and
        # bit-identical for the comparisons/NaN-Inf tests done here).
        def _col(new_idx: int) -> np.ndarray:
            return np.ascontiguousarray(subset[new_idx, :])

        for sel in selections:
            if not getattr(sel, 'enabled', True):
                continue
            try:
                if isinstance(sel, RectangularDataSelection):
                    new_idx = index_map.get(sel.parameter_idx)
                    if new_idx is None:
                        continue
                    vals = _col(new_idx)

                    if _HAVE_NUMBA and _rectangular_mask_numba is not None:
                        _rectangular_mask_numba(vals, sel.lower, sel.upper, sel.invert, mask)
                    else:
                        if sel.invert:
                            mask |= (vals > sel.lower) & (vals < sel.upper)
                        else:
                            mask |= (vals < sel.lower) | (vals > sel.upper)

                elif isinstance(sel, Gaussian2DSelection):
                    new_idx1 = index_map.get(sel.parameter_idx1)
                    new_idx2 = index_map.get(sel.parameter_idx2)
                    if new_idx1 is None or new_idx2 is None:
                        continue
                    x = _col(new_idx1)
                    y = _col(new_idx2)

                    try:
                        inv_cov = np.linalg.inv(sel.cov)
                    except Exception:
                        inv_cov = np.linalg.pinv(sel.cov)

                    # Use Numba if available
                    if _HAVE_NUMBA and _gaussian2d_mask_numba is not None:
                        _gaussian2d_mask_numba(
                            x, y,
                            float(sel.mu[0]), float(sel.mu[1]),
                            float(inv_cov[0, 0]), float(inv_cov[0, 1]), float(inv_cov[1, 1]),
                            float(sel.sigma * sel.sigma),
                            sel.invert, sel.log_x, sel.log_y,
                            mask
                        )
                    else:
                        with np.errstate(divide='ignore', invalid='ignore'):
                            zx = np.where(x > 0.0, np.log(x), np.nan) if sel.log_x else x
                            zy = np.where(y > 0.0, np.log(y), np.nan) if sel.log_y else y
                        dx = zx - sel.mu[0]
                        dy = zy - sel.mu[1]
                        invalid = ~np.isfinite(dx) | ~np.isfinite(dy)
                        dx = np.nan_to_num(dx, nan=np.inf)
                        dy = np.nan_to_num(dy, nan=np.inf)
                        a, b, c = inv_cov[0, 0], inv_cov[0, 1], inv_cov[1, 1]
                        d2 = a * dx * dx + 2.0 * b * dx * dy + c * dy * dy
                        d2[invalid] = np.inf
                        if sel.invert:
                            mask |= d2 <= (sel.sigma * sel.sigma)
                        else:
                            mask |= d2 > (sel.sigma * sel.sigma)

                elif isinstance(sel, MaskDataSelection):
                    # For MaskDataSelection, we need to call get_mask on the full dataset
                    # because it uses 2D histogram binning that requires all data
                    new_idx1 = index_map.get(sel.idx1)
                    new_idx2 = index_map.get(sel.idx2)
                    if new_idx1 is None or new_idx2 is None:
                        continue

                    # Get the full mask from the selection (it operates on full data)
                    full_mask_2d = sel.get_mask(self.values)
                    # Extract the 1D mask for all points (OR across all parameters)
                    full_mask_1d = np.any(full_mask_2d, axis=0)
                    mask |= full_mask_1d

            except Exception as e:
                logging.warning("Selection mask error (%s): %s", getattr(sel, 'name', 'unnamed'), e)

        # Mask NaN/Inf on axis columns - use Numba if available
        if mask_nan or mask_inf:
            for orig_idx in axis_indices:
                new_idx = index_map.get(orig_idx)
                if new_idx is None:
                    continue
                col = _col(new_idx)

                if _HAVE_NUMBA and _mask_nan_inf_numba is not None:
                    _mask_nan_inf_numba(col, mask, mask_nan, mask_inf)
                else:
                    if mask_nan:
                        mask |= np.isnan(col)
                    if mask_inf:
                        mask |= np.isinf(col)

        return mask

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
