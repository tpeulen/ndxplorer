"""Which column indexes the frames, and what an axis range is over.

Frame detection decides whether an image stack opens with a frame selector and
how many frames it claims to have. Getting it wrong is not a crash: picking a
*timestamp* column builds a selector with one entry per second of acquisition,
each showing the handful of bursts whose timestamp rounds into it, and the whole
thing looks like a plausible -- if oddly sparse -- movie.

That is the bug this file pins. ``_FRAME_COLUMN_NAMES`` grew a "frame" entry
with an explicit comment that ``"Frame Time (s)"`` is a timestamp and must not
match, and the exact-match pass did reject it -- but the loose pass that ran
straight afterwards, inside the same loop, admitted it again.
"""

from __future__ import annotations

import numpy as np
import pytest

from ndxplorer.utils.axis_helpers import (frame_column, compute_axis_max,
                                          compute_axis_min)


# --- frame-column detection --------------------------------------------------


@pytest.mark.parametrize(
    "columns, expected",
    [
        # The names the exporters actually write.
        (["X pixel", "Y pixel", "Frame"], "Frame"),
        (["X pixel", "Y pixel", "T pixel"], "T pixel"),
        (["X pixel", "Y pixel", "Z pixel"], "Z pixel"),
        # Loose match: a frame index under a longer name.
        (["X pixel", "Y pixel", "Frame Nbr"], "Frame Nbr"),
        (["X pixel", "Y pixel", "Frame (index)"], "Frame (index)"),
        # No frame axis at all -- a single image, not a stack.
        (["X pixel", "Y pixel"], None),
        (["Fg", "Fr", "Number of Photons"], None),
        (["X pixel", "Y pixel", "Frame Time (s)"], None),
        (["First Photon", "Duration (ms)"], None),
        # Documented precedence: "T pixel" wins over "Frame".
        (["X pixel", "Y pixel", "T pixel", "Frame"], "T pixel"),
        (["X pixel", "Y pixel", "Frame", "T pixel"], "T pixel"),
        # A real frame index alongside a frame timestamp: the index wins.
        (["X pixel", "Y pixel", "Frame Time (s)", "Frame"], "Frame"),
        (["X pixel", "Y pixel", "Frame", "Frame Time (s)"], "Frame"),
    ],
)
def test_the_frame_column_is_an_index_never_a_timestamp(columns, expected):
    assert frame_column(columns) == expected


@pytest.mark.parametrize(
    "name",
    ["Frame Time (s)", "Frame Duration", "Frame Rate (Hz)", "Frame Period",
     "Frame Interval (ms)"],
)
def test_a_frame_quantity_is_not_a_frame_index(name):
    """Each of these has "frame" in it and none of them counts frames.

    ``n_frames = int(max(column)) + 1`` over any of them is a number of seconds,
    hertz or milliseconds -- and the selector built from it is silently wrong
    rather than empty.
    """
    assert frame_column(["X pixel", "Y pixel", name]) is None


def test_detection_is_case_insensitive():
    assert frame_column(["x pixel", "y pixel", "FRAME"]) == "FRAME"
    assert frame_column(["x pixel", "y pixel", "frame time (s)"]) is None


def test_no_columns_at_all_is_not_an_error():
    assert frame_column([]) is None


# --- axis ranges -------------------------------------------------------------


def test_a_linear_range_ignores_the_non_finite_values():
    values = np.array([np.nan, 3.0, -np.inf, 7.0, np.inf, -2.0])
    assert compute_axis_min(values) == -2.0
    assert compute_axis_max(values) == 7.0


def test_a_log_range_also_drops_the_non_positive_values():
    """A log axis cannot show zero or a negative value, and taking the minimum
    over them puts the whole population in the top bin."""
    values = np.array([-5.0, 0.0, 0.25, 4.0, np.nan])
    assert compute_axis_min(values, scale="log") == 0.25
    assert compute_axis_max(values, scale="log") == 4.0
    # The linear reading of the same column is a different, larger interval.
    assert compute_axis_min(values, scale="lin") == -5.0


def test_a_column_with_nothing_usable_falls_back_rather_than_raising():
    all_nan = np.full(5, np.nan)
    assert compute_axis_min(all_nan) == 0.0
    assert compute_axis_max(all_nan) == 0.0
    # Every value non-positive: nothing survives the log filter.
    non_positive = np.array([-1.0, 0.0, -3.0])
    assert compute_axis_min(non_positive, scale="log") == 0.0
    assert compute_axis_max(non_positive, scale="log") == 0.0


def test_an_empty_column_falls_back_rather_than_raising():
    assert compute_axis_min(np.array([])) == 0.0
    assert compute_axis_max(np.array([])) == 0.0


def test_a_constant_column_reports_that_constant():
    values = np.full(20, 2.5)
    assert compute_axis_min(values) == 2.5
    assert compute_axis_max(values) == 2.5
