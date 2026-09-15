"""The playback gate, without a Qt event loop.

The interesting cases are all at the edges: the last step (which used to drop the
largest value in the data), the frame column (whose gate has to keep meaning
exactly ``column == frame``, because that is the behaviour the frame selector had
and image stacks still rely on), and the cache key (which is what makes stepping
show a different population instead of the previous one again).
"""

from __future__ import annotations

import numpy as np
import pytest

from ndxplorer.core import playback as pb
from ndxplorer.core.data_source import DataSource


N_FRAMES = 6
NX = NY = 4


@pytest.fixture
def frame_source():
    """An image stack: a 'Frame' index column and a value column."""
    import pandas as pd

    frame, y, x = np.indices((N_FRAMES, NY, NX))
    data = pd.DataFrame({
        "Frame": frame.ravel().astype(np.float64),
        "X pixel": x.ravel().astype(np.float64),
        "Y pixel": y.ravel().astype(np.float64),
        "Number of Photons": np.arange(frame.size, dtype=np.float64),
    })
    return DataSource(list(data.columns), data)


@pytest.fixture
def burst_source():
    """A burst table whose macro time runs 0…10 s over 101 bursts."""
    import pandas as pd

    times = np.linspace(0.0, 10.0, 101)
    data = pd.DataFrame({
        "Mean Macro Time (s)": times,
        "Proximity ratio": np.linspace(0.1, 0.9, times.size),
    })
    return DataSource(list(data.columns), data)


# --------------------------------------------------------------- detection

def test_macro_time_column_prefers_seconds():
    names = ["Duration (ms)", "Mean Macro Time (ms)", "Mean Macro Time (s)"]
    assert pb.macro_time_column(names) == "Mean Macro Time (s)"


def test_macro_time_column_falls_back_to_milliseconds():
    # The HDF5 and CSV readers do not rename the column, so a table loaded that
    # way carries only the millisecond spelling.
    assert pb.macro_time_column(["Mean Macro Time (ms)"]) == "Mean Macro Time (ms)"


def test_macro_time_column_absent():
    assert pb.macro_time_column(["Tau (green)", "Duration (ms)"]) is None


def test_the_frame_detector_still_rejects_a_timestamp():
    """"Frame Time (s)" is a timestamp, not a frame index."""
    from ndxplorer.utils.axis_helpers import frame_column

    assert frame_column(["Frame Time (s)", "Tau (green)"]) is None
    assert frame_column(["Frame", "Frame Time (s)"]) == "Frame"


# ---------------------------------------------------------------- geometry

def test_an_integer_column_is_an_index_axis():
    lo, hi, n, is_index = pb.axis_geometry(np.arange(N_FRAMES, dtype=float))
    assert (lo, hi, n, is_index) == (-0.5, N_FRAMES - 0.5, N_FRAMES, True)


def test_a_continuous_column_is_cut_into_the_requested_steps():
    lo, hi, n, is_index = pb.axis_geometry(np.linspace(0.0, 10.0, 500), n_steps=25)
    assert (lo, hi, n, is_index) == (0.0, 10.0, 25, False)


def test_a_wide_integer_column_is_not_an_index_axis():
    """A step per photon count is a playback thousands of frames long."""
    values = np.arange(pb.MAX_INDEX_STEPS + 10, dtype=float)
    _, _, n, is_index = pb.axis_geometry(values)
    assert not is_index
    assert n == pb.DEFAULT_N_STEPS


def test_a_constant_column_still_has_one_step():
    lo, hi, n, is_index = pb.axis_geometry(np.full(10, 3.5))
    assert n == 1 and lo < hi and not is_index


def test_non_finite_values_do_not_set_the_bounds():
    values = np.array([0.0, 1.0, np.nan, np.inf, 2.0])
    lo, hi, n, is_index = pb.axis_geometry(values)
    assert (lo, hi) == (-0.5, 2.5) and is_index


# -------------------------------------------------------------------- gate

def test_frame_mode_is_exactly_equality(frame_source):
    """The unification is only honest if it reproduces the old gate.

    The frame selector filtered on ``column == frame``. A window over an index
    axis has to select the same rows, bit for bit, or every image stack quietly
    changes what it shows.
    """
    control = pb.PlaybackController()
    control.set_axis("Frame", frame_source.column_values("Frame"))
    control.set_mode(pb.MODE_WINDOW)

    values = frame_source.column_view(frame_source.column_index("Frame"))
    for frame in range(N_FRAMES):
        control.set_position(frame)
        np.testing.assert_array_equal(control.mask(frame_source), values == frame)


def test_the_last_step_includes_the_top_of_the_range(burst_source):
    """Playing to the end must not show an empty plot.

    A half-open interval on every step leaves the largest value -- the last
    burst, the last frame -- in no step at all.
    """
    control = pb.PlaybackController()
    control.set_axis("Mean Macro Time (s)",
                     burst_source.column_values("Mean Macro Time (s)"), n_steps=10)
    control.set_mode(pb.MODE_WINDOW)
    control.set_position(control.n_steps - 1)
    mask = control.mask(burst_source)
    assert mask[-1], "the last burst fell outside every step"


def test_every_point_lands_in_exactly_one_window(burst_source):
    control = pb.PlaybackController()
    control.set_axis("Mean Macro Time (s)",
                     burst_source.column_values("Mean Macro Time (s)"), n_steps=7)
    control.set_mode(pb.MODE_WINDOW)
    hits = np.zeros(burst_source.size, dtype=int)
    for step in range(control.n_steps):
        control.set_position(step)
        hits += control.mask(burst_source).astype(int)
    np.testing.assert_array_equal(hits, np.ones_like(hits))


def test_integrate_accumulates_and_ends_with_everything(burst_source):
    control = pb.PlaybackController()
    control.set_axis("Mean Macro Time (s)",
                     burst_source.column_values("Mean Macro Time (s)"), n_steps=10)
    control.set_mode(pb.MODE_INTEGRATE)

    counts = []
    for step in range(control.n_steps):
        control.set_position(step)
        counts.append(int(control.mask(burst_source).sum()))

    assert counts == sorted(counts), "the integral went down"
    assert counts[-1] == burst_source.size
    assert counts[0] < counts[-1]


def test_stack_gates_nothing(burst_source):
    control = pb.PlaybackController()
    control.set_axis("Mean Macro Time (s)",
                     burst_source.column_values("Mean Macro Time (s)"))
    control.set_mode(pb.MODE_STACK)
    assert control.mask(burst_source) is None
    assert control.slice_key() is None


def test_no_axis_gates_nothing(burst_source):
    control = pb.PlaybackController()
    control.set_mode(pb.MODE_WINDOW)
    assert control.mask(burst_source) is None


def test_a_missing_column_gates_nothing(burst_source):
    """Reached on the redraw between one file being closed and the next loading."""
    control = pb.PlaybackController(axis_name="Not A Column", mode=pb.MODE_WINDOW)
    assert control.mask(burst_source) is None


# ------------------------------------------------------------------- cache

def test_stepping_changes_the_mask_and_the_key(burst_source):
    """The failure this guards against shows the previous population, silently."""
    control = pb.PlaybackController()
    control.set_axis("Mean Macro Time (s)",
                     burst_source.column_values("Mean Macro Time (s)"), n_steps=10)
    control.set_mode(pb.MODE_WINDOW)

    first_mask, first_key = control.mask(burst_source).copy(), control.slice_key()
    control.step(1)
    assert control.slice_key() != first_key
    assert not np.array_equal(control.mask(burst_source), first_mask)


def test_the_key_carries_every_term_that_moves_the_gate(burst_source):
    control = pb.PlaybackController()
    control.set_axis("Mean Macro Time (s)",
                     burst_source.column_values("Mean Macro Time (s)"), n_steps=10)
    control.set_mode(pb.MODE_WINDOW)
    control.set_position(3)
    base = control.slice_key()

    control.set_mode(pb.MODE_INTEGRATE)
    assert control.slice_key() != base
    control.set_mode(pb.MODE_WINDOW)
    assert control.slice_key() == base

    control.set_n_steps(20)
    assert control.slice_key() != base


def test_the_mask_is_reused_while_nothing_changed(burst_source):
    control = pb.PlaybackController()
    control.set_axis("Mean Macro Time (s)",
                     burst_source.column_values("Mean Macro Time (s)"), n_steps=10)
    control.set_mode(pb.MODE_WINDOW)
    # Asked about five times per redraw; a rebuild each time is five passes over
    # the column for one frame of playback.
    assert control.mask(burst_source) is control.mask(burst_source)


# ------------------------------------------------------------------ moving

def test_stepping_wraps_at_both_ends(burst_source):
    control = pb.PlaybackController()
    control.set_axis("Mean Macro Time (s)",
                     burst_source.column_values("Mean Macro Time (s)"), n_steps=5)
    control.set_mode(pb.MODE_WINDOW)
    assert control.step(-1) == 4
    assert control.step(1) == 0
    control.set_position(4)
    assert control.step(1) == 0


def test_recutting_keeps_the_position_proportional(burst_source):
    control = pb.PlaybackController()
    control.set_axis("Mean Macro Time (s)",
                     burst_source.column_values("Mean Macro Time (s)"), n_steps=10)
    control.set_position(5)
    control.set_n_steps(100)
    # Half way through stays half way through, rather than jumping back to the
    # first twentieth of the measurement.
    assert control.position == 50


def test_bounds_and_window(burst_source):
    control = pb.PlaybackController()
    control.set_axis("Mean Macro Time (s)",
                     burst_source.column_values("Mean Macro Time (s)"), n_steps=10)
    control.set_mode(pb.MODE_WINDOW)
    control.set_position(2)
    lower, upper = control.bounds
    assert (lower, upper) == pytest.approx((2.0, 3.0))
    assert control.window == pytest.approx(1.0)

    control.set_mode(pb.MODE_INTEGRATE)
    lower, upper = control.bounds
    assert (lower, upper) == pytest.approx((0.0, 3.0))


def test_status_text_reports_the_slice(burst_source):
    control = pb.PlaybackController()
    control.set_axis("Mean Macro Time (s)",
                     burst_source.column_values("Mean Macro Time (s)"), n_steps=10)
    control.set_mode(pb.MODE_WINDOW)
    control.set_position(2)
    text = control.status_text()
    assert "3/10" in text and "s" in text


def test_status_text_of_an_index_axis_talks_in_integers(frame_source):
    control = pb.PlaybackController()
    control.set_axis("Frame", frame_source.column_values("Frame"))
    control.set_mode(pb.MODE_WINDOW)
    control.set_position(3)
    assert "index 3" in control.status_text()
    # And never in the half-step bounds that make the interval test exact.
    assert "-0.5" not in control.status_text()
    control.set_mode(pb.MODE_STACK)
    assert "-0.5" not in control.status_text()


def test_an_unknown_mode_is_refused():
    control = pb.PlaybackController()
    with pytest.raises(ValueError):
        control.set_mode("scrub")
