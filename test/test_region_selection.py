"""Gates backed by ChiSurf regions, and selection files that keep every shape.

The saved-selection path had two defects that a user meets in the same click.
``onSave_selection`` dumped ``selection.__dict__`` to JSON, so the moment a
Gaussian or painted selection was in the list it raised ``TypeError: Object of
type ndarray is not JSON serializable`` — *after* opening the destination file
for writing, which truncates it. ``onLoad_selection`` then read
``parameter_idx``/``lower``/``upper`` off every entry, so only rectangles could
come back at all.

Both go through a ChiSurf ``RegionCollection`` now, which serialises each shape
itself; and a region can be used as a gate directly, which gives ndXplorer
polygon selections it never had.
"""

from __future__ import annotations

import json

import numpy as np
import pytest

from ndxplorer.core.data_source import (
    Gaussian2DSelection,
    MaskDataSelection,
    RectangularDataSelection,
)
from ndxplorer.core.region_selection import (
    RegionDataSelection,
    from_collection,
    load_selections,
    save_selections,
    to_collection,
)


@pytest.fixture
def data():
    rng = np.random.default_rng(1)
    x = rng.normal(10.0, 2.0, 800)
    y = 0.8 * x + rng.normal(0.0, 1.0, 800)
    return np.vstack([x, y])


def _combined(selections, data):
    mask = np.zeros(data.shape, dtype=bool)
    for selection in selections:
        mask |= selection.get_mask(data)
    return mask


def _polygon(name="wedge"):
    from chisurf.core.roi import PolygonROI

    return PolygonROI([(6.0, 4.0), (14.0, 4.0), (10.0, 14.0)], name=name)


# --- a region as a gate -------------------------------------------------------
def test_a_region_gates_like_any_other_selection(data):
    """``True`` means excluded, as every ``DataSelection`` promises."""
    selection = RegionDataSelection(_polygon(), 0, 1)
    mask = selection.get_mask(data)

    assert mask.shape == data.shape
    assert mask.any() and not mask.all()
    # Every parameter row carries the same answer, as ndXplorer's combiner wants.
    np.testing.assert_array_equal(mask[0], mask[1])

    inside = ~mask[0]
    assert inside.sum() > 0
    # A point the polygon contains is kept; one far outside is excluded.
    probe = np.array([[10.0, 6.0], [30.0, 30.0]]).T
    probe_mask = selection.get_mask(probe)
    assert probe_mask[0].tolist() == [False, True]


def test_inverting_a_region_gate_keeps_the_outside(data):
    plain = RegionDataSelection(_polygon(), 0, 1)
    inverted = RegionDataSelection(_polygon(), 0, 1, invert=True)
    finite = np.isfinite(data[0]) & np.isfinite(data[1])
    np.testing.assert_array_equal(~plain.get_mask(data)[0] & finite,
                                  inverted.get_mask(data)[0] & finite)


def test_a_disabled_region_gate_excludes_nothing(data):
    selection = RegionDataSelection(_polygon(), 0, 1, enabled=False)
    assert not selection.get_mask(data).any()


def test_a_point_with_no_position_on_this_plane_is_excluded():
    """A NaN coordinate cannot be shown to be inside; admitting it would widen
    every gate silently."""
    selection = RegionDataSelection(_polygon(), 0, 1)
    data = np.array([[10.0, np.nan], [6.0, 6.0]])
    assert selection.get_mask(data)[0].tolist() == [False, True]


def test_indices_beyond_the_data_are_ignored_not_an_error(data):
    selection = RegionDataSelection(_polygon(), 0, 7)
    assert not selection.get_mask(data).any()


# --- files --------------------------------------------------------------------
def test_saving_a_gaussian_selection_no_longer_raises(tmp_path, data):
    """The old saver died on the numpy arrays — after truncating the file."""
    selection = Gaussian2DSelection(
        0, 1, data.mean(axis=1), np.cov(data), sigma=1.0, name="cluster"
    )
    with pytest.raises(TypeError):
        json.dumps([selection.__dict__])          # what it used to do

    path = save_selections([selection], str(tmp_path / "gates.selection.json"))
    assert json.loads(open(path).read())["entries"]


def test_every_shape_survives_a_save_and_reload(tmp_path, data):
    selections = [
        RectangularDataSelection(0, 8.0, 12.0, name="x band"),
        Gaussian2DSelection(
            0, 1, data.mean(axis=1), np.cov(data), sigma=1.0, name="cluster", invert=True
        ),
        RegionDataSelection(_polygon(), 0, 1),
    ]
    path = save_selections(selections, str(tmp_path / "gates.selection.json"))
    back = load_selections(path)

    assert [s.name for s in back] == ["x band", "cluster", "wedge"]
    assert [s.shape for s in back] == ["rectangle", "ellipse", "polygon"]
    assert back[1].invert is True

    # And they gate identically — the point of keeping them.
    np.testing.assert_array_equal(_combined(selections, data), _combined(back, data))


def test_a_painted_mask_survives_a_save_and_reload(tmp_path, data):
    edges1 = np.linspace(data[0].min(), data[0].max(), 25)
    edges2 = np.linspace(data[1].min(), data[1].max(), 25)
    mask = np.zeros((24, 24), dtype=bool)
    mask[6:16, 6:16] = True
    selection = MaskDataSelection(0, 1, mask, edges1, edges2, name="painted")

    path = save_selections([selection], str(tmp_path / "gates.selection.json"))
    (back,) = load_selections(path)

    theirs, ours = selection.get_mask(data), back.get_mask(data)
    disagree = int((theirs != ours).sum() / data.shape[0])
    assert disagree <= 3, f"{disagree} points disagree"


def test_a_file_written_by_the_old_saver_still_opens(tmp_path):
    """Rectangles are all it could ever hold, but they must not be orphaned."""
    legacy = [
        {"parameter_idx": 0, "lower": 1.0, "upper": 2.0,
         "invert": False, "enabled": True, "name": "old band"},
    ]
    path = tmp_path / "legacy.selection.json"
    path.write_text(json.dumps(legacy))

    (back,) = load_selections(str(path))
    assert isinstance(back, RectangularDataSelection)
    assert (back.lower, back.upper, back.name) == (1.0, 2.0, "old band")


# --- the shared collection ----------------------------------------------------
def test_selections_convert_to_a_collection_with_their_flags(data):
    selections = [
        RectangularDataSelection(0, 8.0, 12.0, name="band", enabled=False),
        RegionDataSelection(_polygon(), 0, 1, invert=True),
    ]
    collection = to_collection(selections)

    assert collection.names == ["band", "wedge"]
    assert collection["band"].enabled is False
    assert collection["wedge"].invert is True
    # ndXplorer excludes a point if *any* enabled selection does, i.e. an AND of
    # what each keeps.
    assert collection.combine == "and"


def test_a_collection_converts_back_to_selections(data):
    collection = to_collection([RegionDataSelection(_polygon(), 0, 1, invert=True)])
    (back,) = from_collection(collection, axes=(0, 1))

    assert isinstance(back, RegionDataSelection)
    assert back.invert is True
    assert (back.idx1, back.idx2) == (0, 1)


# --- multi-class painted masks -------------------------------------------------
def test_each_painted_class_becomes_its_own_gate():
    """The brush paints class ids, so one image carries several populations.

    As a single MaskDataSelection they had no names, could not be measured or
    inverted separately and could not be combined — the multi-label information
    existed and nothing downstream could reach it.
    """
    from ndxplorer.core.region_selection import selections_from_label_mask

    labels = np.zeros((20, 20), dtype=int)
    labels[2:8, 2:8] = 1
    labels[12:18, 12:18] = 2
    edges1 = np.linspace(0.0, 20.0, 21)
    edges2 = np.linspace(0.0, 20.0, 21)

    gates = selections_from_label_mask(labels, edges1, edges2, names={2: "bright"})
    assert [g.name for g in gates] == ["class 1", "bright"]

    # Each selects its own population and not the other's.
    first, second = (np.array([[5.0], [5.0]]), np.array([[15.0], [15.0]]))
    assert gates[0].get_mask(first)[0].tolist() == [False]
    assert gates[0].get_mask(second)[0].tolist() == [True]
    assert gates[1].get_mask(second)[0].tolist() == [False]


def test_an_empty_mask_yields_no_gates():
    from ndxplorer.core.region_selection import selections_from_label_mask

    edges = np.linspace(0.0, 10.0, 11)
    assert selections_from_label_mask(np.zeros((10, 10), dtype=int), edges, edges) == []


def test_classes_round_trip_back_into_a_mask():
    """A set of region gates can be handed back to the brush."""
    from ndxplorer.core.region_selection import (
        label_mask_from_selections,
        selections_from_label_mask,
    )

    labels = np.zeros((20, 20), dtype=int)
    labels[2:8, 2:8] = 1
    labels[12:18, 12:18] = 2
    edges = np.linspace(0.0, 20.0, 21)

    gates = selections_from_label_mask(labels, edges, edges)
    back = label_mask_from_selections(gates, labels.shape, edges, edges)

    assert set(np.unique(back)) == {0, 1, 2}
    np.testing.assert_array_equal(back > 0, labels > 0)
    np.testing.assert_array_equal(back, labels)
