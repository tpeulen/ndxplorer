"""The 2-D map a window draws is the histogram just computed, however often it changes.

A user opened a ``.pto`` in the emtk app, chose Stoichiometry (PIE) against FRET
efficiency with CET-L19, and the map was blank white while the marginals showed
43 283 bursts. The histogram was right -- it equals the Qt window's, bin for
bin. What the GPU drew was not: the image atlas knew a texture by its ``id``,
the map makes a new texture on every change, and a new one allocated where a
dead one had been was drawn as the dead one's picture (or, once dead maps had
filled the atlas, as a flat white box).
"""

from __future__ import annotations

import gc
import pathlib

import numpy as np
import pytest

from ndxplorer.core.data_source import DataSource

PTO = pathlib.Path.home() / "dev/tttr-data/sm/cal1/001_60g_25r_cal1_cy3b_8_18_33bp_atto647n_alex.pto"


def _atlas_copy(atlas, texture) -> np.ndarray:
    """The RGB the atlas holds for *texture* (opaque, so premultiplying is a no-op)."""
    x, y, w, h = atlas._placed[id(texture)][-4:]
    return atlas.pixels[y:y + h, x:x + w, :3]


def _pixels(texture) -> np.ndarray:
    return np.frombuffer(bytes(texture.px), np.uint8).reshape(
        texture.height, texture.width, 4)[:, :, :3]


def test_the_gpu_atlas_holds_the_current_map_after_many_changes():
    from emtk.gpu_atlas import ImageAtlas

    from ndxplorer.app.model import ExplorerModel
    from ndxplorer.app.plots import PlotArea

    rng = np.random.default_rng(0)
    model = ExplorerModel()
    model.set_source(DataSource.from_columns({
        "E": rng.normal(0.8, 0.1, 5000), "S": rng.normal(0.5, 0.1, 5000),
        "tau": rng.normal(3.0, 0.5, 5000)}))
    model.set_parameter("x", "S")
    model.set_parameter("y", "E")
    area = PlotArea(model)
    atlas = ImageAtlas(256, 256)       # small, so a leak shows within the loop
    for i in range(300):
        model.colormap = ("viridis", "CET-L19")[i % 2]
        if i % 7 == 0:
            model.set_parameter("y", ("E", "tau")[(i // 7) % 2])
            model.x.bins_2d = (31, 50)[(i // 7) % 2]
            model.invalidate()
        model.update()
        texture = area.texture()
        assert atlas.region(texture) is not None, f"map declined after {i} changes"
        assert np.array_equal(_atlas_copy(atlas, texture), _pixels(texture)), \
            f"change {i}: the atlas drew another map"
        gc.collect()


@pytest.mark.skipif(not PTO.exists(), reason="needs ~/dev/tttr-data")
def test_the_pto_map_holds_every_burst_inside_both_ranges():
    """The user's state: every burst finite on both axes and inside both
    ranges is in the map -- the count an independent fill gives, bin for bin."""
    from ndxplorer.app.model import ExplorerModel

    model = ExplorerModel()
    assert model.open(str(PTO))
    model.set_parameter("x", "Stoichiometry (PIE)")
    model.set_parameter("y", "FRET efficiency")
    model.y.lo, model.y.hi = -0.93, 1.49
    model.invalidate()
    model.update()
    H = model.histograms.H
    assert H.shape == (model.y.bins_2d, model.x.bins_2d)

    x = np.asarray(model.source.column_values("Stoichiometry (PIE)"), dtype=np.float64)
    y = np.asarray(model.source.column_values("FRET efficiency"), dtype=np.float64)
    finite = np.isfinite(x) & np.isfinite(y)
    expected, _, _ = np.histogram2d(
        y[finite], x[finite], bins=[model.y.bins_2d, model.x.bins_2d],
        range=[(model.y.lo, model.y.hi), (model.x.lo, model.x.hi)])
    np.testing.assert_array_equal(H, expected)
    # every row in both ranges, most of the 44 270 bursts
    assert H.sum() == expected.sum() > 40_000
    # the FRET population (E ~ 0.85, S ~ 0.55) is the brightest part of the map
    iy, ix = np.unravel_index(np.argmax(H), H.shape)
    assert 0.75 < model.histograms.y_edges[iy] < 0.95
    assert 0.45 < model.histograms.x_edges[ix] < 0.65
