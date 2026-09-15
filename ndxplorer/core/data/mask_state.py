"""Everything that decides which points are shown, as one plain value.

The set of visible points is not determined by the data alone. It also depends on
drawn selections, the z-range slider, which cluster the spinner isolates, and
which slice of the playback axis is on screen -- all of which live in the GUI. Historically the mask
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


def gate_key(selection) -> tuple:
    """A gate reduced to comparable values, never the object itself.

    Each selection class knows what identifies it; anything that does not say
    falls back to its type and flags, which is conservative in the safe
    direction -- a key that changes too often costs a recomputation, one that
    changes too rarely shows the wrong data.
    """
    own = getattr(selection, "gate_key", None)
    if callable(own):
        return own()
    return (type(selection).__name__,
            bool(getattr(selection, "enabled", True)),
            bool(getattr(selection, "invert", False)),
            getattr(selection, "selection_id", id(selection)))


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
    slice_mask : numpy.ndarray or None
        Precomputed per-point mask for the slice of the playback axis on screen
        (``True`` = keep), or ``None`` when playback is stacked or off. Passed as
        an array because deriving it needs the column the GUI picked.
    slice_key : tuple or None
        The scalars *slice_mask* was built from -- axis, mode, step, step count
        and bounds. Carried separately because it is what makes the cache key
        change when the user steps the playback; the array itself is never in
        the key, being both expensive to compare and, by identity, wrong.
    """

    selections: Sequence[Any] = field(default_factory=tuple)
    axis_indices: Tuple[int, int, int] = (0, 1, 2)
    mask_inf: bool = False
    mask_nan: bool = False
    z_range: Optional[Tuple[float, float]] = None
    cluster_label: Optional[int] = None
    slice_mask: Optional[np.ndarray] = None
    slice_key: Optional[tuple] = None

    def key(self) -> tuple:
        """A comparable token that changes exactly when the mask would.

        Compared with ``==`` rather than hashed, so the parts may be whatever
        the selection layer produces. ``slice_mask`` is represented by its
        ``slice_key`` plus a present/absent flag rather than by the array, so
        that the key stays cheap; stepping the playback changes the key.

        The selections are reduced to VALUES rather than kept as objects. The
        selection table edits a gate in place -- toggling ``enabled``, dragging a
        boundary -- so a key holding the object compares it against itself and
        reports that nothing changed, whatever ``__eq__`` says. The plot then
        keeps showing the previous population.
        """
        return (
            [gate_key(s) for s in self.selections],
            tuple(self.axis_indices),
            self.mask_inf,
            self.mask_nan,
            self.z_range,
            self.cluster_label,
            self.slice_key,
            self.slice_mask is not None,
        )
