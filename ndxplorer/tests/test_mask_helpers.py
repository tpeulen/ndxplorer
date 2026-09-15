"""Painted masks: what survives a save and reload, and what the brush paints.

A painted mask is a *label* image -- integers naming populations, not a yes/no
bitmap -- so every operation here has to preserve which class a pixel belongs
to. The failure mode is quiet: a relabelled mask still opens, still paints, and
still gates; only the population membership is different.

The fixtures are deliberately awkward for that reason. A square mask cannot show
a transpose, a mask whose labels all fit in a byte cannot show the 16-bit path,
and a brush applied in the middle of an image cannot show the edge clipping.
"""

from __future__ import annotations

import numpy as np
import pytest

from ndxplorer.utils.mask_helpers import (apply_brush_to_mask,
                                          create_circular_brush_kernel,
                                          create_empty_mask,
                                          create_gaussian_brush_kernel,
                                          create_pixel_radius_brush_kernel,
                                          extract_class_mask,
                                          get_mask_statistics,
                                          load_mask_from_tiff, mask_to_selection,
                                          merge_masks, save_mask_as_bitmap)


@pytest.fixture
def labelled_mask():
    """Non-square, several classes, one of them past a byte."""
    mask = np.zeros((7, 11), dtype=np.int32)   # 7 rows, 11 columns
    mask[1:3, 2:5] = 1
    mask[5, 8:10] = 300
    mask[0, 10] = 2                            # the far corner, for orientation
    return mask


# --- round trip --------------------------------------------------------------


def test_a_label_mask_survives_a_save_and_reload(tmp_path, labelled_mask):
    path = tmp_path / "mask.tif"
    save_mask_as_bitmap(labelled_mask, str(path), binary=False)
    reloaded, classes = load_mask_from_tiff(str(path))

    assert reloaded.shape == labelled_mask.shape, "the mask came back transposed"
    np.testing.assert_array_equal(np.asarray(reloaded, dtype=np.int32), labelled_mask)
    assert classes == [1, 2, 300]


def test_a_class_past_a_byte_keeps_its_number(tmp_path):
    """uint8 would wrap 300 to 44 and the population would be renamed."""
    mask = np.zeros((4, 6), dtype=np.int32)
    mask[1, 2] = 300
    path = tmp_path / "wide.tif"
    save_mask_as_bitmap(mask, str(path), binary=False)
    reloaded, classes = load_mask_from_tiff(str(path))
    assert reloaded.dtype == np.uint16
    assert classes == [300]
    assert int(reloaded[1, 2]) == 300


def test_a_binary_save_keeps_the_shape_but_not_the_classes(tmp_path, labelled_mask):
    path = tmp_path / "binary.tif"
    save_mask_as_bitmap(labelled_mask, str(path), binary=True)
    reloaded, classes = load_mask_from_tiff(str(path))
    assert reloaded.shape == labelled_mask.shape
    assert classes == [255]
    np.testing.assert_array_equal(reloaded > 0, labelled_mask > 0)


def test_saving_does_not_modify_the_mask_it_was_given(tmp_path, labelled_mask):
    before = labelled_mask.copy()
    save_mask_as_bitmap(labelled_mask, str(tmp_path / "m.tif"), binary=True)
    np.testing.assert_array_equal(labelled_mask, before)


# --- the refusals ------------------------------------------------------------


def test_an_empty_mask_is_refused_with_a_readable_message(tmp_path):
    """A freshly created, never-painted mask used to fail three frames deep
    inside libtiff with "zero-size array to reduction operation maximum"."""
    with pytest.raises(ValueError, match="empty mask"):
        save_mask_as_bitmap(create_empty_mask((0, 0)), str(tmp_path / "e.tif"),
                            binary=False)


def test_a_negative_label_is_refused_rather_than_wrapped(tmp_path):
    """``astype(np.uint8)`` turns -1 into 255: a silently relabelled mask."""
    mask = np.array([[-1, 0], [0, 1]], dtype=np.int32)
    with pytest.raises(ValueError, match="negative class label"):
        save_mask_as_bitmap(mask, str(tmp_path / "n.tif"), binary=False)


def test_a_label_past_16_bits_is_refused_rather_than_wrapped(tmp_path):
    mask = np.zeros((3, 3), dtype=np.int64)
    mask[1, 1] = 70_000
    with pytest.raises(ValueError, match="65535"):
        save_mask_as_bitmap(mask, str(tmp_path / "huge.tif"), binary=False)


# --- the brush ---------------------------------------------------------------


def test_a_brush_paints_the_class_it_was_given():
    mask = create_empty_mask((9, 9))
    apply_brush_to_mask(mask, (4, 4), create_circular_brush_kernel(2), class_id=3)
    assert set(np.unique(mask)) == {0, 3}
    assert mask[4, 4] == 3


@pytest.mark.parametrize("position", [(0, 0), (0, 8), (8, 0), (8, 8), (4, 0), (0, 4)])
def test_a_brush_at_an_edge_paints_only_what_fits(position):
    """The kernel window and the mask window have to be clipped in step; if they
    are not, the brush wraps to the opposite edge or raises on the shape."""
    mask = create_empty_mask((9, 9))
    apply_brush_to_mask(mask, position, create_circular_brush_kernel(3), class_id=1)

    y, x = position
    painted = np.argwhere(mask > 0)
    assert painted.size > 0, "nothing was painted at the edge"
    # Everything painted is within the brush radius of where it was applied.
    assert np.all(np.abs(painted[:, 0] - y) <= 3)
    assert np.all(np.abs(painted[:, 1] - x) <= 3)


def test_a_brush_on_a_non_square_mask_does_not_confuse_the_axes():
    mask = create_empty_mask((5, 20))
    apply_brush_to_mask(mask, (2, 18), create_circular_brush_kernel(2), class_id=7)
    painted = np.argwhere(mask == 7)
    assert painted.size > 0
    assert np.all(np.abs(painted[:, 0] - 2) <= 2)
    assert np.all(np.abs(painted[:, 1] - 18) <= 2)


def test_erasing_removes_only_what_the_brush_covers():
    mask = np.ones((9, 9), dtype=np.int32)
    apply_brush_to_mask(mask, (4, 4), create_circular_brush_kernel(1), class_id=0,
                        mode="erase")
    assert mask[4, 4] == 0
    assert mask[0, 0] == 1


@pytest.mark.parametrize("radius", [1, 2, 5, 11])
def test_a_circular_kernel_is_round_and_centred(radius):
    kernel = create_circular_brush_kernel(radius)
    assert kernel.shape == (2 * radius + 1, 2 * radius + 1)
    assert kernel[radius, radius] == 1.0
    assert kernel[0, 0] == 0.0                      # corners are outside a circle
    np.testing.assert_array_equal(kernel, kernel[::-1])   # symmetric in y
    np.testing.assert_array_equal(kernel, kernel[:, ::-1])  # and in x


def test_an_even_gaussian_kernel_is_made_odd_so_it_has_a_centre():
    kernel = create_gaussian_brush_kernel(size=20, sigma=3.0)
    assert kernel.shape[0] % 2 == 1
    assert kernel.shape[0] == kernel.shape[1]


def test_an_anisotropic_pixel_brush_is_wider_on_the_compressed_axis():
    """One screen radius over axes with different pixels-per-bin has to be an
    ellipse in bin space, or the brush paints a different area depending on the
    zoom of each axis."""
    kernel = create_pixel_radius_brush_kernel(10, px_per_bin_x=1.0, px_per_bin_y=5.0)
    height, width = kernel.shape
    assert width > height


# --- the rest of the vocabulary ----------------------------------------------


def test_merging_binary_masks_lets_the_higher_class_win():
    masks = {1: np.array([[1, 1], [0, 0]]), 2: np.array([[1, 0], [1, 0]])}
    merged = merge_masks(masks)
    # (0,0) is claimed by both; the higher id is applied last.
    np.testing.assert_array_equal(merged, np.array([[2, 1], [2, 0]]))


def test_merging_nothing_is_nothing():
    assert merge_masks({}) is None


def test_extracting_a_class_keeps_only_that_class(labelled_mask):
    binary = extract_class_mask(labelled_mask, 300)
    assert binary.sum() == int((labelled_mask == 300).sum())
    assert set(np.unique(binary)) <= {0, 1}


def test_mask_statistics_count_pixels_per_class_and_skip_background(labelled_mask):
    stats = get_mask_statistics(labelled_mask)
    assert stats == {1: 6, 2: 1, 300: 2}
    assert 0 not in stats


def test_a_selection_is_one_class_or_every_class(labelled_mask):
    every = mask_to_selection(labelled_mask)
    one = mask_to_selection(labelled_mask, class_id=1)
    assert every.sum() == 9
    assert one.sum() == 6
    assert np.all(every[one])       # one class is a subset of all of them
