"""The plots draw the axes and titles ``model.axis_display`` asks for (View > Axis Control)."""

from __future__ import annotations

import numpy as np
import pytest

from ndxplorer.core.data_source import DataSource
from ndxplorer.plotting.axis_display import AxisDisplay


@pytest.fixture
def area():
    from ndxplorer.app.model import ExplorerModel
    from ndxplorer.app.plots import PlotArea

    rng = np.random.default_rng(0)
    model = ExplorerModel()
    model.set_source(DataSource.from_columns({"E": rng.random(500), "S": rng.random(500)}))
    return PlotArea(model)


def test_without_a_display_the_plots_keep_their_axes(area):
    assert area._decorations("xmarginal", True) == (True, True)     # ticks on top
    assert area._decorations("ymarginal", False) == (True, True)    # ticks on the right
    assert area._decorations("map", True) == (False, False)
    assert area._decorations("zmarginal", True) == (True, False)
    assert area._title_shown("xmarginal", "top")


def test_the_display_moves_and_hides_axes_and_titles(area):
    display = AxisDisplay()
    area.model.axis_display = display
    display.set_visible("map", "bottom", True)
    display.set_visible("xmarginal", "top", False)
    display.set_visible("ymarginal", "left", True)
    assert area._decorations("map", True) == (True, False)
    assert area._decorations("xmarginal", True) == (False, False)
    assert area._decorations("ymarginal", False) == (True, False)   # left wins over right
    display.set_enable_all_labels(False)
    display.set_label("xmarginal", "top", False)
    assert not area._title_shown("xmarginal", "top")
    assert area._title_shown("ymarginal", "right")


def test_the_titles_take_the_display_colour(area):
    from emtk.testing import RecordingPainter

    display = AxisDisplay()
    display.set_title_colour("#00ff00")
    area.model.axis_display = display
    area._titles = [("h", 0.0, 0.0, 100.0, 20.0, "E")]
    painter = RecordingPainter()
    area.draw_overlays(painter)
    assert painter.texts[0][6][:3] == (0, 255, 0)
