"""File > Save > Histograms, Print window and Exit (ndxplorer.app.features.window)."""

from __future__ import annotations

import numpy as np
import pytest

from ndxplorer.core.data_source import DataSource


@pytest.fixture
def app():
    from ndxplorer.app.frame import NdxApp

    a = NdxApp(features=["window"])
    rng = np.random.default_rng(1)
    a.model.set_source(DataSource.from_columns({"a": rng.normal(size=500),
                                                "b": rng.normal(size=500)}))
    a.model.update()
    yield a
    a.close()


def test_save_histograms_writes_the_marginals_and_the_map(app):
    saved = []

    class Service:
        def save_bytes(self, name, data, mime="", title="", filters=""):
            saved.append((name, data.decode()))

    app.io_service = Service()
    assert app.run_action("save_histograms")
    name, text = saved[0]
    assert name == "histograms.txt"
    assert "# marginals" in text and "# 2-D histogram" in text
    assert text.count("\nX\t") == app.model.x.bins_1d


def test_save_histograms_needs_a_place_to_save(app):
    assert not app.panel.available("save_histograms")        # no io_service yet


def test_print_window_takes_a_screenshot(app):
    shots = []
    app.panel.actions["screenshot"] = lambda: shots.append(1)
    assert app.run_action("print_window") and shots == [1]


def test_exit_closes_through_the_host_and_is_disabled_without_one(app):
    assert not app.panel.available("exit")                     # a page: nothing to close
    closed = []
    app.on_exit = lambda: closed.append(1)
    assert app.run_action("exit") and closed == [1]
