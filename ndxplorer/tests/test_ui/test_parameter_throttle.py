"""The parameter recompute throttles (updates live), it does not debounce.

Now that a targeted recompute is ~1 ms, a parameter change should refresh the
plot *while* the user scrolls/drags, not only after they stop. This is a
throttle: an already-scheduled update is left to fire on its interval instead of
being pushed back on every edit (which is what a debounce does).
"""
from __future__ import annotations

import os

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


@pytest.fixture(scope="module")
def qapp():
    from qtpy import QtWidgets

    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _make_ndx():
    from ndxplorer.core.plot_main import NDXplorer

    ndx = NDXplorer()
    if hasattr(ndx, "_deferred_init"):
        ndx._deferred_init()
    return ndx


def test_schedule_does_not_restart_an_active_timer(qapp):
    ndx = _make_ndx()
    # A real pending change, so the (no-op-guarded) scheduler actually arms.
    ndx._pending_changed_constants = {"Bg"}

    ndx._schedule_parameter_recompute()  # creates + arms the timer
    timer = ndx._parameter_recompute_timer
    assert timer.isActive()

    # A debounce would call start() again (pushing the wait back); a throttle
    # leaves the running timer alone.
    calls = []
    orig_start = timer.start
    timer.start = lambda *a: (calls.append(a), orig_start(*a))[1]
    try:
        ndx._schedule_parameter_recompute()
        assert calls == [], "active throttle timer must not be restarted"
    finally:
        timer.start = orig_start


def test_flush_sets_adaptive_interval_in_live_range(qapp):
    ndx = _make_ndx()
    ndx._pending_changed_constants = set()  # nothing to recompute -> cheap flush

    ndx._flush_parameter_recompute()

    assert 16 <= ndx._recompute_interval_ms <= 160


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-q"])
