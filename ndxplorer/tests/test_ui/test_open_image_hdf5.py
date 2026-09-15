"""Opening an image HDF5 through the window's own File menu path.

``open_files(file_type="mfd_hdf5")`` used to load inline instead of going
through the shared loader every other format uses, and then called
``_apply_axes_and_refresh`` with the wrong number of arguments. The data loaded
and the program then raised ``TypeError`` -- at the point where the failure
looks like a problem with the file rather than with the caller.

The unit tests cover the reader and the store. This covers the thing between
them: the branch in ``open_files``, which no unit test reached because it needs
a window.
"""

from __future__ import annotations

import numpy as np
import pytest
import tttrlib
from qtpy import QtCore, QtWidgets

from ndxplorer.io import file_operations

pytestmark = pytest.mark.skipif(not tttrlib.hdf5_table_available(),
                                reason="tttrlib built without HDF5")

# Deliberately NOT square: a square image cannot tell a transposed axis or a
# bin count that defaulted from one that came from the data.
NX, NY = 12, 20
N_FRAMES = 2


@pytest.fixture(scope="session")
def qapp() -> QtWidgets.QApplication:
    app = QtWidgets.QApplication.instance()
    if app is None:
        app = QtWidgets.QApplication([])
    return app


def open_and_wait(window, app, path, settled=None, timeout_ms: int = 30_000):
    """Open `path` and pump the event loop until the load has settled.

    Two waits, not one. The load runs on a worker thread -- which is the point
    of routing it through the shared path -- and the axis detection then runs on
    a timer AFTER it, once the combo boxes have been populated. A test that
    stops at the first of those reads the axes as they were before the file was
    opened.
    """
    file_operations.open_files(window, file_handles=[str(path)],
                               file_type="mfd_hdf5")

    def loaded():
        return window.data_source.size == N_FRAMES * NY * NX

    for condition, what in ((loaded, "the data"),
                            (settled or loaded, "the axis detection")):
        deadline = QtCore.QElapsedTimer()
        deadline.start()
        while not condition():
            app.processEvents()
            if deadline.elapsed() > timeout_ms:
                raise AssertionError(f"{what} never arrived")


@pytest.fixture
def image_file(tmp_path):
    rng = np.random.default_rng(11)
    frame, y, x = np.indices((N_FRAMES, NY, NX))
    n = frame.size
    counts = rng.integers(1, 40, n).astype(np.int32)
    tau = rng.uniform(1.0, 5.0, n)
    tau[counts < 5] = np.nan

    store = tttrlib.DataStore("image")
    store.set_n_rows(n)
    store.add("X pixel", x.ravel().astype(np.int32))
    store.add("Y pixel", y.ravel().astype(np.int32))
    store.add("Frame", frame.ravel().astype(np.int32))
    store.add("Number of Photons", counts)
    store.add("Tau (green)", tau).mask_non_finite()
    # A timestamp, not a frame index -- the frame detection has to tell them
    # apart, and "Frame Time (s)" contains the word "frame".
    store.add("Frame Time (s)", frame.ravel().astype(np.float64) * 0.01)

    path = tmp_path / "image.h5"
    assert tttrlib.write_hdf5(str(path), store)
    return path


def test_opening_an_image_hdf5_does_not_raise(qapp, image_file):
    from ndxplorer.core.plot_main import NDXplorer

    window = NDXplorer()
    try:
        # No exception is the assertion: this raised TypeError after the data
        # had already loaded.
        open_and_wait(window, qapp, image_file)

        assert window.data_source.size == N_FRAMES * NY * NX
        names = window.data_source.parameter_names
        assert "X pixel" in names and "Tau (green)" in names
    finally:
        window.close()


def test_the_pixel_axes_are_detected(qapp, image_file):
    """Going through the shared loader is what runs image detection at all.

    The inline branch skipped it, so an imaging HDF5 opened with whatever axes
    happened to be selected and the default bin counts -- an image drawn at 50
    bins across, which looks like data rather than like a mistake.

    Asserted on the settled state (the axes and the 2-D bin counts) rather than
    on ``_detected_image_dims``, which is deleted once it has been applied.
    """
    from ndxplorer.core.plot_main import NDXplorer

    window = NDXplorer()
    try:
        control = window.plot_control
        open_and_wait(window, qapp, image_file,
                      settled=lambda: control.n_yhist_2d == NY)
        assert control.comboBoxSelX.currentText().lower().startswith("x pixel")
        assert control.comboBoxSelY.currentText().lower().startswith("y pixel")
        # One bin per pixel, not the default fifty -- and not 256, which is
        # what the saved per-axis settings supply when they have no entry.
        assert (control.n_xhist_2d, control.n_yhist_2d) == (NX, NY)
        # The ranges come from the data too. They used to come from those same
        # settings, which gave an x range of 0 to 1 binned 256 ways: every pixel
        # in the first bin and one flat colour on screen.
        #
        # [0, n), not [0, n-1]: with n bins over [0, n) each bin is exactly one
        # pixel. Over the largest INDEX each bin is (n-1)/n of a pixel wide and
        # bin and pixel drift apart across the image.
        assert (control.xmin, control.xmax) == (0.0, NX)
        assert (control.ymin, control.ymax) == (0.0, NY)
    finally:
        window.close()


def test_a_frame_stack_gets_a_frame_selector(qapp, image_file):
    """A column called "Frame" is a frame index.

    Only "T pixel" and "Z pixel" were recognised, which is what the older burst
    exporters wrote -- so a stack written as "Frame" opened with no frame
    control and every frame drawn on top of the others. That does not look like
    a missing widget, it looks like one noisy image.

    The selector is now the Playback panel, which plays any column back; a
    frame index is the case where one step is one value.
    """
    from ndxplorer.core.plot_main import NDXplorer

    window = NDXplorer()
    try:
        control = window.plot_control
        open_and_wait(window, qapp, image_file,
                      settled=lambda: control.n_yhist_2d == NY)
        assert control.playback.axis_name == "Frame"
        assert control.playback.n_steps == N_FRAMES
        assert control.playback.is_index
        # isHidden, not isVisible: the window is never shown in these tests.
        assert not control.playback_form.isHidden()
    finally:
        window.close()


def test_a_frame_window_shows_exactly_one_frame(qapp, image_file):
    """Stepping the playback changes which points are drawn.

    The gate is an interval now rather than an equality, so this is the test
    that the interval still lands on one frame: the count has to be one frame's
    worth of pixels, and it has to be a *different* frame's worth after a step.
    """
    from ndxplorer.core.playback import MODE_WINDOW
    from ndxplorer.core.plot_main import NDXplorer

    window = NDXplorer()
    try:
        control = window.plot_control
        open_and_wait(window, qapp, image_file,
                      settled=lambda: control.n_yhist_2d == NY)

        control.playback_model.mode = MODE_WINDOW
        qapp.processEvents()
        shown = (~window.value_mask).sum()
        assert shown == NX * NY

        control.playback_model.step_forward()
        qapp.processEvents()
        assert control.playback.position == 1
        assert (~window.value_mask).sum() == NX * NY

        # ...and it is a different frame, not the same one counted twice.
        frames = window.data_source.column_values("Frame")[~window.value_mask]
        assert set(np.unique(frames)) == {1.0}
    finally:
        window.close()


def test_integrate_mode_accumulates_frames(qapp, image_file):
    from ndxplorer.core.playback import MODE_INTEGRATE
    from ndxplorer.core.plot_main import NDXplorer

    window = NDXplorer()
    try:
        control = window.plot_control
        open_and_wait(window, qapp, image_file,
                      settled=lambda: control.n_yhist_2d == NY)

        control.playback_model.mode = MODE_INTEGRATE
        qapp.processEvents()
        assert (~window.value_mask).sum() == NX * NY

        control.playback_model.position = N_FRAMES - 1
        qapp.processEvents()
        assert (~window.value_mask).sum() == N_FRAMES * NX * NY
    finally:
        window.close()
