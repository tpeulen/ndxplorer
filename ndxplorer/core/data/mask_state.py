"""Everything that decides which points are shown, as one plain value.

The set of visible points is not determined by the data alone. It also depends on
drawn selections, the z-range slider, which cluster the spinner isolates, and
which frame is on screen -- all of which live in the GUI. Historically the mask
was therefore computed *by* a helper that reached into ``plot_control`` for each
of those, which is why it could not live in the data layer, which is why a second
"clean" implementation grew inside :class:`~ndxplorer.core.data.data_manager.DataManager`
that simply ignored every GUI-dependent term.

The two then disagreed in the worst possible way: no error, no warning, just
selections that quietly stopped narrowing anything on one of the two paths.

This is the fix: the GUI gathers its own state into one plain, Qt-free object and
hands it over. The data layer computes and caches the mask without knowing a
widget exists, and there is one implementation again.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional, Sequence, Tuple

import numpy as np

__all__ = ["MaskState"]


@dataclass
class MaskState:
    """The gating terms that decide which points survive.

    Attributes
    ----------
    selections : sequence
        Drawn selections (``DataSelection`` objects). Note the polarity used
        throughout ndXplorer: a mask entry is ``True`` where the point is
        **excluded**.
    axis_indices : tuple of int
        Column indices of the x, y and z axes. Inf/NaN masking is applied over
        *these* columns only -- a NaN in some column that is not on screen must
        not delete the point.
    mask_inf, mask_nan : bool
        Whether non-finite values on the plotted axes are excluded.
    z_range : tuple of float or None
        Active z-slider range; ``None`` when dynamic z-selection is off (which
        includes the case where the z axis itself is disabled).
    cluster_label : int or None
        Isolate a single cluster; ``None`` shows all. Requires a
        ``Cluster Label`` column, and does nothing without one.
    frame_mask : numpy.ndarray or None
        Precomputed per-point mask for single-frame mode (``True`` = keep), or
        ``None`` when frames are stacked. Passed as an array because deriving it
        needs the frame column the GUI picked.
    frame_number : int or None
        The frame *frame_mask* was built for. Carried separately because it is
        what makes the cache key change when the user steps frames.
    """

    selections: Sequence[Any] = field(default_factory=tuple)
    axis_indices: Tuple[int, int, int] = (0, 1, 2)
    mask_inf: bool = False
    mask_nan: bool = False
    z_range: Optional[Tuple[float, float]] = None
    cluster_label: Optional[int] = None
    frame_mask: Optional[np.ndarray] = None
    frame_number: Optional[int] = None

    def key(self) -> tuple:
        """A comparable token that changes exactly when the mask would.

        Compared with ``==`` rather than hashed, so the selection objects may be
        whatever the selection layer produces. ``frame_mask`` is represented by
        its frame number plus a present/absent flag rather than by the array, so
        that the key stays cheap; stepping frames changes the number.
        """
        return (
            list(self.selections),
            tuple(self.axis_indices),
            self.mask_inf,
            self.mask_nan,
            self.z_range,
            self.cluster_label,
            self.frame_number,
            self.frame_mask is not None,
        )
