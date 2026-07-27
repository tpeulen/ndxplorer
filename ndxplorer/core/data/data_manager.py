"""
Central data management for NDXplorer.

Separates data state and operations from UI concerns, providing:
- Single source of truth for data
- Unified cache management
- Clean interfaces for data access
- Testability without Qt dependencies
"""

from typing import Optional, Tuple, Dict, List
import numpy as np

from ...logging_config import logging
from ..data_source import DataSource
from .cache_coordinator import CacheCoordinator
from .mask_state import MaskState


class DataManager:
    """
    Central data manager for NDXplorer.
    
    Manages:
    - Data source and computed columns
    - Value caching and retrieval
    - Axis value extraction
    - Cache coordination
    - Selection/masking
    """
    
    def __init__(self):
        self._default_data_source = self._create_default_data_source()
        self._data_source = DataSource()  # Start empty, will use default if needed
        
        self.cache = CacheCoordinator()
        self._mask_state = None  # type: Optional[MaskState]
        
        self.constants = {}  # type: Dict[str, float]
        self.equations = []  # type: List[Dict[str, str]]
        
    def _create_default_data_source(self) -> DataSource:
        """Create default demo data source."""
        return DataSource(
            ["Tau (green)", "Proximity ratio", "r Experimental (green)"],
            np.vstack([
                np.random.multivariate_normal(
                    [4.1, 0.0, 0.05], 
                    [[0.1, 0.0, 0.0], [0.0, 0.01, 0.0], [0.0, 0.0, 0.01]], 
                    size=500
                ),
                np.random.multivariate_normal(
                    [2.0, 0.5, 0.15], 
                    [[0.1, 0.0, 0.0], [0.0, 0.01, 0.0], [0.0, 0.0, 0.01]], 
                    size=500
                )
            ])
        )
        
    @property
    def data_source(self) -> DataSource:
        """Get current data source (or default if empty)."""
        if self._data_source.empty:
            logging.debug("DataManager: Using default data source")
            return self._default_data_source
        return self._data_source
        
    @data_source.setter
    def data_source(self, v: DataSource) -> None:
        """Set data source and invalidate caches."""
        logging.info(f"DataManager: Setting data source with {v.values.shape[1] if not v.empty else 0} data points")
        self._data_source = v
        self.cache.invalidate_all()
        # Skip re-computation if already finalized in background
        if not getattr(v, 'is_computed', False):
            self._data_source.compute_columns(
                constants=self.constants,
                equations=self.equations
            )
        else:
            logging.info("DataManager: Skipping re-computation, data source is already computed.")
        
    @property
    def is_empty(self) -> bool:
        """Check if data source is empty (considering default fallback)."""
        # If actual data source is not empty, we have data
        if not self._data_source.empty:
            return False
        # If actual is empty, check if we have default
        return self._default_data_source is None or self._default_data_source.empty
        
    def invalidate_caches(self) -> None:
        """Invalidate all caches."""
        self.cache.invalidate_all()
        
    def compute_columns(self) -> None:
        """Recompute columns with current equations and constants."""
        logging.debug("DataManager: Computing columns with equations and constants")
        self._data_source.compute_columns(
            constants=self.constants,
            equations=self.equations
        )
        
    def get_raw_values(self) -> np.ndarray:
        """
        Get raw data values without any filtering.
        
        Returns:
            2D array (n_params, n_points)
        """
        return self.data_source.values
        
    @property
    def mask_state(self) -> MaskState:
        """The gating terms currently in force.

        Defaults to no gating at all, which is what a headless caller reading the
        data wants. The window assigns a fully populated :class:`MaskState` on
        every update, so drawn selections, the z-slider, the cluster spinner and
        single-frame mode reach the data layer without it importing Qt.
        """
        if self._mask_state is None:
            return MaskState()
        return self._mask_state

    @mask_state.setter
    def mask_state(self, state: Optional[MaskState]) -> None:
        self._mask_state = state

    def get_filtered_values(self) -> np.ndarray:
        """
        Get the visible points: raw data with every excluded point dropped.

        Returns:
            2D array (n_params, n_visible) -- note the second axis is *shorter*
            than the raw data, and is indexed by position among the survivors,
            not by original row. Use :meth:`get_value_mask` when you need to map
            back to original rows.
        """
        mask = self.get_value_mask()
        cached_values = self.cache.get_cache_value('filtered_values')
        if (cached_values is not None
                and self.cache.get_cache_value('filtered_values_mask_id') == id(mask)):
            logging.debug("DataManager: Using cached filtered values")
            return cached_values

        all_values = self.get_raw_values()
        n_valid = int(np.count_nonzero(~mask))
        if n_valid == all_values.shape[1]:
            # Nothing excluded — hand back the original rather than copying it.
            values = all_values
        elif n_valid == 0:
            values = np.empty((all_values.shape[0], 0), dtype=all_values.dtype)
        else:
            values = all_values[:, np.flatnonzero(~mask)]

        self.cache.set_cache_value('filtered_values', values)
        self.cache.set_cache_value('filtered_values_mask_id', id(mask))
        return values

    def get_axis_values(self, 
                       axis: str, 
                       param_idx: int,
                       use_filtered: bool = True) -> np.ndarray:
        """
        Get values for specific axis (x, y, or z).
        
        Uses cache when possible.
        
        Args:
            axis: 'x', 'y', or 'z'
            param_idx: Parameter index to extract
            use_filtered: Whether to use filtered values (apply masks)
            
        Returns:
            1D array of values for the specified axis
        """
        axis = axis.lower()
        if axis not in ('x', 'y', 'z'):
            raise ValueError(f"Invalid axis: {axis}")
            
        # Keyed on the *mask* identity, not on the data version alone: drawing a
        # selection changes which points survive without changing the data, and
        # a version-only guard would keep serving the pre-selection slice.
        values = self.get_filtered_values() if use_filtered else self.get_raw_values()
        token = id(values)
        cached_values = self.cache.get_cache_value(f'{axis}_values')
        if (cached_values is not None and
            self.cache.get_cache_value(f'{axis}_param_idx') == param_idx and
            self.cache.get_cache_value(f'{axis}_values_id') == token):
            logging.debug(f"DataManager: Using cached {axis} values")
            return cached_values

        logging.debug(f"DataManager: Computing {axis} values for param_idx={param_idx}")
        axis_values = values[param_idx]

        self.cache.set_cache_value(f'{axis}_values', axis_values)
        self.cache.set_cache_value(f'{axis}_param_idx', param_idx)
        self.cache.set_cache_value(f'{axis}_values_id', token)

        return axis_values
        
    def get_value_mask(self) -> np.ndarray:
        """
        Which points are excluded, over the **full, uncompressed** data.

        Every gating term is applied here and only here: Inf/NaN on the plotted
        axes, drawn selections, the dynamic z-range, cluster isolation, and
        single-frame mode. Consumers that need to map a result back onto original
        rows (the background histogram path builds ``valid_indices`` from this)
        depend on the length matching the raw data, so the mask is never
        computed over already-compressed values.

        Cached, and returning the *same object* while nothing has changed. That
        identity is load-bearing rather than a micro-optimisation: the histogram
        layer keys on it to decide whether an update needs a recompute, so
        handing back an equal-but-new array on every call would make every pan
        and zoom recompute every histogram.

        Returns:
            Boolean mask (n_points,) where True means excluded
        """
        data_version = self.data_source.data_version
        state = self.mask_state
        key = state.key()
        cached = self.cache.get_cache_value('value_mask')
        if (cached is not None
                and self.cache.get_cache_value('value_mask_version') == data_version
                and self.cache.get_cache_value('value_mask_state') == key):
            return cached

        source = self.data_source
        mask = source.get_mask_subset(
            selections=list(state.selections),
            axis_indices=list(state.axis_indices),
            mask_nan=state.mask_nan,
            mask_inf=state.mask_inf,
        )

        if state.z_range is not None:
            z_values = source.values[state.axis_indices[2]]
            z_min, z_max = min(state.z_range), max(state.z_range)
            mask = mask | ~((z_values >= z_min) & (z_values <= z_max))

        if state.cluster_label is not None:
            if "Cluster Label" in source.data.columns:
                labels = source.data["Cluster Label"].values
                mask = mask | (labels != state.cluster_label)
            else:
                # Reachable whenever the spinner is left on a cluster and the
                # data is replaced by a file that was never clustered.
                logging.warning(
                    "cluster %s requested but there is no 'Cluster Label' column; "
                    "showing all points", state.cluster_label
                )

        if state.frame_mask is not None:
            mask = mask | ~state.frame_mask

        self.cache.set_cache_value('value_mask', mask)
        self.cache.set_cache_value('value_mask_version', data_version)
        self.cache.set_cache_value('value_mask_state', key)
        return mask

    def get_stats(self) -> dict:
        """Get data and cache statistics."""
        raw_values = self.get_raw_values()
        filtered_values = self.get_filtered_values()
        
        return {
            'raw_points': raw_values.shape[1] if raw_values.ndim > 1 else len(raw_values),
            'filtered_points': filtered_values.shape[1] if filtered_values.ndim > 1 else len(filtered_values),
            'num_parameters': raw_values.shape[0] if raw_values.ndim > 1 else 1,
            'num_selections': len(self.mask_state.selections),
            'cache_stats': self.cache.get_stats(),
            'mask_state': self.mask_state.key(),
        }
