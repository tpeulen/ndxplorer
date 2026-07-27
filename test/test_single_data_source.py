"""One data source, not two.

An unfinished refactor moved data ownership to ``DataManager`` but left a
private ``_data_source`` field on the window as a "backward compatible" copy.
The manager took over, so that copy stayed **permanently empty** — while several
call sites went on reading and writing it. Nothing raised:

* clustering and UMAP read it, saw zero rows, and quietly did nothing;
* appending a file checked ``_data_source.empty`` (always true), so it never
  merged, and then wrote the new data *into the dead copy* — the load appeared
  to succeed and changed nothing.

The field is gone. These tests keep it gone.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from qtpy import QtWidgets

from ndxplorer.core.data_source import DataSource


@pytest.fixture(scope="module")
def qt_app():
    """A single QApplication for the module (offscreen)."""
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _select_axes(window, x_name: str, y_name: str) -> None:
    """Point the x/y combo boxes at named columns.

    Without this the combos sit at index ``-1``, which quietly means "the last
    column" everywhere downstream -- so a test that adds a column would silently
    change which one it is reading.
    """
    control = window.plot_control
    control.update(update_comboboxes=True, update_plots=False)
    columns = list(window.data_source.data.columns)
    control.comboBoxSelX.setCurrentIndex(columns.index(x_name))
    control.comboBoxSelY.setCurrentIndex(columns.index(y_name))
    QtWidgets.QApplication.instance().processEvents()


@pytest.fixture
def window(qt_app):
    """A window holding two columns."""
    from ndxplorer.core.plot_main import NDXplorer

    frame = pd.DataFrame({"x": [1.0, 2.0, 3.0], "y": [4.0, 5.0, 6.0]})
    win = NDXplorer(data_source=DataSource(list(frame.columns), frame))
    yield win
    win.close()


def test_there_is_no_second_data_source(window):
    """The private copy must not come back: it is the trap the bugs came from."""
    assert not hasattr(window, "_data_source"), (
        "a second data source is back; every consumer that reads it will see "
        "whatever the manager is not using"
    )
    assert not hasattr(window, "_default_data_source")


def test_the_property_is_what_the_constructor_filled(window):
    """Data passed in must be reachable through the public property."""
    frame = window.data_source.data
    assert list(frame.columns) == ["x", "y"]
    assert len(frame) == 3


def test_appending_reaches_the_visible_data(window):
    """A merged file must actually appear.

    This is the user-visible bug: the append path tested the dead copy's
    ``empty`` (always true), so it took the replace branch and assigned into
    that copy. The load reported success and the new column never appeared.
    """
    from ndxplorer.io.file_operations import _handle_append

    extra = DataSource(["z"], pd.DataFrame({"z": [7.0, 8.0, 9.0]}))
    _handle_append(window, extra, "columns")

    columns = list(window.data_source.data.columns)
    assert "z" in columns, f"the appended column never arrived; got {columns}"
    assert list(window.data_source.data["z"]) == [7.0, 8.0, 9.0]


def test_appending_into_an_empty_window_replaces(qt_app):
    """The other branch: with nothing loaded, the new source is simply taken."""
    from ndxplorer.core.plot_main import NDXplorer
    from ndxplorer.io.file_operations import _handle_append

    win = NDXplorer()
    try:
        win.data_source.clear()
        _handle_append(win, DataSource(["a"], pd.DataFrame({"a": [1.0, 2.0]})), "columns")
        assert "a" in list(win.data_source.data.columns)
    finally:
        win.close()


def test_axis_values_come_from_the_manager(window):
    """The axis accessors must read the one source, with no fallback path."""
    _select_axes(window, "x", "y")

    assert np.allclose(np.asarray(window.x_values), [1.0, 2.0, 3.0])
    assert np.allclose(np.asarray(window.y_values), [4.0, 5.0, 6.0])


def test_there_is_only_one_value_cache(window):
    """The duplicate cache module and its window attributes are gone.

    ``utils/value_cache`` reimplemented the manager's caching with its own
    ``_cached_*`` attributes on the window and its own invalidation. They agreed
    on output but could drift; only the manager's remains.
    """
    with pytest.raises(ImportError):
        from ndxplorer.utils import value_cache  # noqa: F401

    for attribute in ("_cached_values", "_cached_x_values", "_cached_y_values",
                      "_cached_values_mask_id", "_cached_filtered_values"):
        assert not hasattr(window, attribute), f"{attribute} is back"


def test_the_surviving_cache_is_stable_and_versioned(window):
    """Identity on repeat reads is what stops pan/zoom recomputing everything."""
    first = window.value_mask
    assert window.value_mask is first

    window.data_source.data = pd.DataFrame({"x": [9.0, 9.0, 9.0], "y": [1.0, 1.0, 1.0]})
    assert window.value_mask is not first


def test_a_selection_change_invalidates_the_histogram_key(window):
    """A gate change must show up in the histogram cache key.

    ``extract_histogram_params`` builds the key that decides whether the
    histograms are recomputed. Its ``data_hash`` tracks the *data*, which a
    selection does not change -- so the mask identity is the only component
    that reacts to gating. If it goes constant, drawing a selection leaves every
    histogram stale, with no error anywhere.
    """
    from ndxplorer.utils.histogram_helpers import extract_histogram_params

    before = extract_histogram_params(window)[0].mask_id
    assert before is not None, "the mask identity dropped out of the cache key"
    assert extract_histogram_params(window)[0].mask_id == before, (
        "the key changes when nothing changed; every update would recompute"
    )

    window._mask_nan = not window._mask_nan
    after = extract_histogram_params(window)[0].mask_id
    assert after != before, (
        "the histogram key ignored a gating change; histograms would stay stale"
    )


def test_a_selection_narrows_what_is_plotted(window):
    """The point of the whole mask: a drawn gate must remove points.

    Two mask implementations coexisted -- one that applied selections and one
    that ignored them -- and the axis values were served by the one that ignored
    them, so selecting a region left the plots unchanged. There is one
    implementation now, and this is what it has to do.
    """
    from ndxplorer.core.data.mask_state import MaskState
    from ndxplorer.core.data_source import RectangularDataSelection

    assert len(window.x_values) == 3

    gate = RectangularDataSelection(parameter_idx=0, lower=0.5, upper=2.5)
    window.data_manager.mask_state = MaskState(selections=[gate])

    manager = window.data_manager
    mask = manager.get_value_mask()
    assert mask.shape == (3,), (
        "the mask must stay full-length; the histogram path turns it into row "
        "indices into the unfiltered data"
    )
    assert list(mask) == [False, False, True]

    values = manager.get_filtered_values()
    assert values.shape == (2, 2), f"the gate did not narrow the data: {values.shape}"
    assert np.allclose(np.sort(manager.get_axis_values("x", 0)), [1.0, 2.0])
    assert np.allclose(np.sort(manager.get_axis_values("y", 1)), [4.0, 5.0])


def test_the_window_collects_cluster_isolation(window):
    """The window must translate its widgets into the gating state.

    The cluster spinner is the clearest case: it changes nothing about the data,
    only which rows count, so it can only reach the data layer through the
    collected state.
    """
    from ndxplorer.core.data.mask_state import MaskState

    frame = window.data_source.data
    frame["Cluster Label"] = [0, 1, 1]
    window.data_source.data = frame

    _select_axes(window, "x", "y")
    window._use_clustering = True
    window.plot_control.spinBoxCluster.setValue(1)

    state = window._collect_mask_state()
    assert state.cluster_label == 1

    assert list(window.value_mask) == [True, False, False]
    assert np.allclose(np.sort(window.x_values), [2.0, 3.0])

    # Turning isolation off must bring the points back -- the state key has to
    # notice, or the cached mask would outlive the change.
    window._use_clustering = False
    assert list(window.value_mask) == [False, False, False]
    assert len(window.x_values) == 3
