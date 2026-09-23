"""Histogram data classes for NDXplorer core."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

import numpy as np


@dataclass
class Histogram1D:
    """1D histogram container with edges and counts."""
    edges: np.ndarray
    counts: np.ndarray

    @property
    def n_bins(self) -> int:
        """Get number of bins."""
        return len(self.edges) - 1

    def validate(self) -> bool:
        """Validate histogram consistency."""
        try:
            if len(self.counts.shape) != 1:
                return False

            if len(self.edges.shape) != 1:
                return False

            if len(self.counts) != len(self.edges) - 1:
                return False

            if not np.all(np.diff(self.edges) > 0):
                return False

            return True

        except Exception:
            return False

    def as_tuple(self) -> Tuple[np.ndarray, np.ndarray]:
        """Return as (edges, counts) tuple."""
        return self.edges, self.counts

    def __iter__(self):
        """Unpack as ``edges, counts``.

        Both this container and a plain tuple reach ``_histogram`` depending on
        which computation path ran, and most readers spell it ``edges, counts =
        ndx._histogram["x"]`` inside a bare ``except`` -- so a container that
        refuses to unpack does not raise, it silently drops the overlay.
        """
        return iter(self.as_tuple())


@dataclass
class Histogram2D:
    """2D histogram container with H matrix and axis edges."""
    H: np.ndarray
    x_edges: np.ndarray
    y_edges: np.ndarray

    @property
    def shape(self) -> Tuple[int, int]:
        """Get histogram shape."""
        return self.H.shape

    @property
    def n_bins_x(self) -> int:
        """Get number of X bins."""
        return len(self.x_edges) - 1

    @property
    def n_bins_y(self) -> int:
        """Get number of Y bins."""
        return len(self.y_edges) - 1

    def validate(self) -> bool:
        """Validate histogram consistency."""
        try:
            if len(self.H.shape) != 2:
                return False

            if len(self.x_edges.shape) != 1 or len(self.y_edges.shape) != 1:
                return False

            if self.H.shape[1] != len(self.x_edges) - 1:
                return False

            if self.H.shape[0] != len(self.y_edges) - 1:
                return False

            if not np.all(np.diff(self.x_edges) > 0):
                return False

            if not np.all(np.diff(self.y_edges) > 0):
                return False

            return True

        except Exception:
            return False

    def as_tuple(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Return as (H, x_edges, y_edges) tuple."""
        return self.H, self.x_edges, self.y_edges

    def __iter__(self):
        """Unpack as ``H, x_edges, y_edges`` (see :meth:`Histogram1D.__iter__`)."""
        return iter(self.as_tuple())

    def get_x_marginal(self) -> Histogram1D:
        """Get X marginal histogram (sum along Y axis)."""
        counts = np.sum(self.H, axis=0)
        return Histogram1D(edges=self.x_edges, counts=counts)

    def get_y_marginal(self) -> Histogram1D:
        """Get Y marginal histogram (sum along X axis)."""
        counts = np.sum(self.H, axis=1)
        return Histogram1D(edges=self.y_edges, counts=counts)


@dataclass
class Histogram3D:
    """3D histogram container with H tensor and axis edges."""
    H: np.ndarray
    x_edges: np.ndarray
    y_edges: np.ndarray
    z_edges: np.ndarray

    @property
    def shape(self) -> Tuple[int, int, int]:
        """Get histogram shape."""
        return self.H.shape

    @property
    def n_bins_x(self) -> int:
        """Get number of X bins."""
        return len(self.x_edges) - 1

    @property
    def n_bins_y(self) -> int:
        """Get number of Y bins."""
        return len(self.y_edges) - 1

    @property
    def n_bins_z(self) -> int:
        """Get number of Z bins."""
        return len(self.z_edges) - 1

    def validate(self) -> bool:
        """Validate histogram consistency."""
        try:
            if len(self.H.shape) != 3:
                return False

            if len(self.x_edges.shape) != 1 or len(self.y_edges.shape) != 1 or len(self.z_edges.shape) != 1:
                return False

            if self.H.shape[2] != len(self.x_edges) - 1:
                return False

            if self.H.shape[1] != len(self.y_edges) - 1:
                return False

            if self.H.shape[0] != len(self.z_edges) - 1:
                return False

            if not np.all(np.diff(self.x_edges) > 0):
                return False

            if not np.all(np.diff(self.y_edges) > 0):
                return False

            if not np.all(np.diff(self.z_edges) > 0):
                return False

            return True

        except Exception:
            return False

    def as_tuple(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Return as (H, x_edges, y_edges, z_edges) tuple."""
        return self.H, self.x_edges, self.y_edges, self.z_edges

    def __iter__(self):
        """Unpack as ``H, x_edges, y_edges, z_edges`` (see :meth:`Histogram1D.__iter__`)."""
        return iter(self.as_tuple())

    def get_xy_marginal(self) -> Histogram2D:
        """Get XY marginal histogram (sum along Z axis)."""
        H = np.sum(self.H, axis=0)
        return Histogram2D(H=H, x_edges=self.x_edges, y_edges=self.y_edges)

    def get_xz_marginal(self) -> Histogram2D:
        """Get XZ marginal histogram (sum along Y axis)."""
        H = np.sum(self.H, axis=1)
        return Histogram2D(H=H, x_edges=self.x_edges, y_edges=self.z_edges)

    def get_yz_marginal(self) -> Histogram2D:
        """Get YZ marginal histogram (sum along X axis)."""
        H = np.sum(self.H, axis=2)
        return Histogram2D(H=H, x_edges=self.y_edges, y_edges=self.z_edges)

    def get_x_marginal(self) -> Histogram1D:
        """Get X marginal histogram (sum along Y and Z axes)."""
        counts = np.sum(self.H, axis=(0, 1))
        return Histogram1D(edges=self.x_edges, counts=counts)

    def get_y_marginal(self) -> Histogram1D:
        """Get Y marginal histogram (sum along X and Z axes)."""
        counts = np.sum(self.H, axis=(0, 2))
        return Histogram1D(edges=self.y_edges, counts=counts)

    def get_z_marginal(self) -> Histogram1D:
        """Get Z marginal histogram (sum along X and Y axes)."""
        counts = np.sum(self.H, axis=(1, 2))
        return Histogram1D(edges=self.z_edges, counts=counts)


# ---------------------------------------------------------------------------
# What the 2-D map shows, and the colour limits on it
# ---------------------------------------------------------------------------
# These were computed inline in the Qt window, three times over (the map's
# log transform in ``update_2d_plot``, the Contrast button's limits in
# ``auto_contrast`` and the limits every redraw sets in
# ``update_spinbox_limits``). Both GUIs call these now.

def display_counts(H: np.ndarray, log_counts: bool = False) -> np.ndarray:
    """The counts the 2-D map colours: *H*, or ``log10`` of it with "log #".

    Empty bins are drawn a decade below the smallest filled one, so they stay
    darker than anything filled instead of becoming ``-inf``.
    """
    data = np.array(H, dtype=np.float64)
    if not log_counts:
        return data
    positive = data[data > 0]
    smallest = float(np.min(positive)) if positive.size else 1e-10
    return np.nan_to_num(np.log10(np.maximum(data, smallest / 10.0)))


def auto_contrast_limits(H: np.ndarray, log_counts: bool = False) -> Tuple[float, float]:
    """The Contrast button's limits: the 1st to 99th percentile of the filled bins.

    In the units :func:`display_counts` draws in. ``(0, 1)`` for an empty map.
    """
    from ..utils.performance import compute_percentile_range_optimized

    H = np.asarray(H, dtype=np.float64)
    if H.size == 0 or not np.any(np.isfinite(H)) or np.all(np.nan_to_num(H) == 0):
        return 0.0, 1.0
    shown = display_counts(H, log_counts)
    filled = shown[shown > 0]
    if filled.size == 0:
        return 0.0, 1.0
    vmin, vmax = compute_percentile_range_optimized(filled, 1, 99)
    if vmin == vmax:
        vmin = 0.9 * vmin if vmin != 0 else 0.0
        vmax = 1.1 * vmax if vmax != 0 else 1.0
    return float(vmin), float(vmax)


def colour_limits(H: np.ndarray, log_counts: bool = False, low_pct: float = 0.1,
                  high_pct: float = 99.0) -> Tuple[float, float]:
    """The limits a redraw sets: percentiles of the filled bins.

    Parameters
    ----------
    H : numpy.ndarray
        The 2-D histogram.
    log_counts : bool
        Whether the map is drawn in ``log10`` counts; the limits are then in
        those units too, so they apply to what is drawn.
    low_pct, high_pct : float
        Percentiles in ``[0, 100]``.
    """
    H = np.asarray(H, dtype=np.float64)
    filled = H[np.isfinite(H) & (H > 0)]
    data = np.log10(filled) if log_counts else filled
    if data.size < 2:
        # Too few filled bins for percentiles: the whole range.
        shown = display_counts(H, log_counts)
        shown = shown[np.isfinite(shown)]
        if shown.size == 0:
            return 0.0, 1.0
        return float(np.min(shown)), float(np.max(shown))
    vmin, vmax = np.percentile(data, [low_pct, high_pct])
    return float(vmin), float(vmax)
