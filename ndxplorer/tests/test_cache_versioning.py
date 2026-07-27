"""Regression tests for data_version-guarded value caches.

These lock in the architectural contract introduced when the blanket
``invalidate_values_cache()`` on every interactive update was replaced by
caches that self-guard on ``DataSource.data_version``:

* A cache read must miss (recompute) after the underlying data changes, even
  when no explicit invalidation call is made.
* A cache read must hit (reuse the same object) when nothing changed, so
  view-only updates (pan/zoom, colormap) no longer recompute the mask and the
  filtered slice.
"""

import numpy as np
import pandas as pd
import pytest

from ndxplorer.core.data_source import DataSource
from ndxplorer.core.data.data_manager import DataManager


def _make_source(scale: float = 1.0) -> DataSource:
    df = pd.DataFrame(
        {
            "a": np.arange(10, dtype=float) * scale,
            "b": np.arange(10, dtype=float)[::-1] * scale,
        }
    )
    return DataSource(data=df)


def test_data_version_bumps_on_data_change():
    ds = _make_source()
    v0 = ds.data_version
    # Reassigning .data is the canonical "data changed" event.
    ds.data = pd.DataFrame({"a": np.ones(10), "b": np.ones(10)})
    assert ds.data_version != v0


def test_filtered_values_cache_hits_when_unchanged():
    dm = DataManager()
    dm.data_source = _make_source()

    first = dm.get_filtered_values()
    second = dm.get_filtered_values()
    # No data change → same cached object handed back, not a recompute.
    assert second is first


def test_filtered_values_cache_misses_after_data_change():
    dm = DataManager()
    ds = _make_source(scale=1.0)
    dm.data_source = ds

    first = dm.get_filtered_values().copy()
    # Mutate the underlying data in place (bumps data_version) without any
    # explicit cache invalidation — the version guard must catch it.
    ds.data = pd.DataFrame({"a": np.arange(10, dtype=float) * 3.0,
                            "b": np.arange(10, dtype=float)[::-1] * 3.0})
    second = dm.get_filtered_values()

    assert not np.array_equal(first, second)
    # The fresh values reflect the new data.
    np.testing.assert_allclose(np.sort(second[0]), np.sort(np.arange(10) * 3.0))


def test_axis_values_cache_respects_version():
    dm = DataManager()
    ds = _make_source(scale=1.0)
    dm.data_source = ds

    a0 = dm.get_axis_values("x", 0)
    a0_again = dm.get_axis_values("x", 0)
    assert a0_again is a0  # cache hit, same object

    ds.data = pd.DataFrame({"a": np.arange(10, dtype=float) * 5.0,
                            "b": np.arange(10, dtype=float)[::-1] * 5.0})
    a1 = dm.get_axis_values("x", 0)
    assert not np.array_equal(a0, a1)
    np.testing.assert_allclose(np.sort(a1), np.sort(np.arange(10) * 5.0))


def test_value_mask_cache_hits_and_versions():
    """The mask must be stable when nothing changed and refresh when data does.

    Previously exercised through ``utils.value_cache``, a second implementation
    that lived beside the data manager's own. The two did not merely risk
    drifting -- they had already diverged: one applied selections, clusters,
    frames and the z-range, the other silently ignored all four. There is one
    implementation now, and this asserts the caching behaviour of it.
    """
    dm = DataManager()
    ds = _make_source()
    dm.data_source = ds

    m0 = dm.get_value_mask()
    m0_again = dm.get_value_mask()
    # Nothing changed → same cached mask object (this stability is what lets the
    # histogram layer skip recompute on view-only updates).
    assert m0_again is m0

    # A data change bumps data_version; the mask must be recomputed even though
    # no explicit invalidation was called and the selection/view key is
    # byte-for-byte identical.
    ds.data = pd.DataFrame({"a": np.ones(10), "b": np.zeros(10)})
    m1 = dm.get_value_mask()
    assert m1 is not m0


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-q"])
