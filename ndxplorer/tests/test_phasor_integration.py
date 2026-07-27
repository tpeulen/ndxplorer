"""Chisurf-free tests for ndXplorer's phasor-integration helpers (PRD-56 Phase 4).

A light fake ``ndx`` (real ``DataSource`` + optional pyqtgraph ``overlay_plot`` + fake RPC
services) exercises axis detection, overlay drawing/mapping and column injection without
constructing the full ndXplorer window or importing chisurf.
"""

from __future__ import annotations

import os

import numpy as np
import pandas as pd
import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from ndxplorer import phasor_integration as pi  # noqa: E402
from ndxplorer.core.data_source import DataSource  # noqa: E402
from ndxplorer.rpc import LinesService, PhasorService  # noqa: E402


class FakeClient:
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def call(self, method, params=None):
        self.calls.append((method, params))
        return self.responses[method]


class FakeAxes:
    def __init__(self, x, y):
        self._x, self._y = x, y

    @property
    def p1(self):
        return (0, self._x)

    @property
    def p2(self):
        return (1, self._y)


class FakeNdx:
    def __init__(self, df, x_axis="g", y_axis="s", client=None, plot=None, hist=None):
        self._ds = DataSource(data=df)
        self.plot_control = FakeAxes(x_axis, y_axis)
        self.overlay_plot = plot
        self._histogram = {"2d": hist} if hist is not None else {}
        self._param_refreshed = False
        if client is not None:
            self.phasor_service = PhasorService(client)
            self.lines_service = LinesService(client)

    @property
    def data_source(self):
        return self._ds

    def value_to_bin(self, value, edges):
        # Simple linear map into [0, len(edges)-1]; None if out of range.
        lo, hi = edges[0], edges[-1]
        if value < lo or value > hi:
            return None
        return (value - lo) / (hi - lo) * (len(edges) - 1)

    def invalidate_values_cache(self):
        pass

    def update_parameter_names(self):
        self._param_refreshed = True


def _df():
    return pd.DataFrame({"g (P1)": [0.4, 0.6], "s (P1)": [0.3, 0.45], "n_photons": [10, 20]})


# -- axis / column inspection ----------------------------------------------------------
def test_axes_look_like_phasor():
    ndx = FakeNdx(_df(), x_axis="g (P1)", y_axis="s (P1)")
    assert pi.axes_look_like_phasor(ndx)
    assert pi.current_axes(ndx) == ("g (P1)", "s (P1)")


def test_axes_not_phasor():
    ndx = FakeNdx(_df(), x_axis="Tau (green)", y_axis="Proximity ratio")
    assert not pi.axes_look_like_phasor(ndx)


def test_find_column_by_token():
    ndx = FakeNdx(_df())
    g = pi.find_column(ndx, "g")
    s = pi.find_column(ndx, "s")
    assert list(g) == [0.4, 0.6]
    assert list(s) == [0.3, 0.45]
    assert pi.find_column(ndx, "missing") is None


# -- column injection ------------------------------------------------------------------
def test_inject_columns_adds_and_refreshes():
    ndx = FakeNdx(_df())
    added = pi.inject_columns(ndx, {"tau_phi": [1.0, 2.0], "tau_m": [1.1, 2.1]})
    assert set(added) == {"tau_phi", "tau_m"}
    assert "tau_phi" in ndx.data_source.data.columns
    assert ndx._param_refreshed


def test_compute_apparent_lifetime_columns():
    client = FakeClient(
        {"phasor.apparent_lifetime": {"ok": True, "result": {"tau_phi": [1.0, 2.0], "tau_m": [1.5, 2.5]}}}
    )
    ndx = FakeNdx(_df(), client=client)
    added = pi.compute_apparent_lifetime_columns(ndx, frequency_mhz=80.0)
    assert set(added) == {"tau_phi", "tau_m"}
    # The g / s arrays were marshalled to the RPC call.
    method, params = client.calls[0]
    assert method == "phasor.apparent_lifetime"
    assert params["g"] == [0.4, 0.6]


# -- overlay drawing (needs a real pyqtgraph plot) -------------------------------------
def test_draw_overlays_maps_and_counts():
    import pyqtgraph as pg

    pg.mkQApp()
    widget = pg.PlotWidget()  # keep a reference so its ViewBox is not GC'd
    plot = widget.getPlotItem()
    client = FakeClient(
        {
            "phasor.overlays": {
                "ok": True,
                "result": {
                    "overlays": [
                        {"name": "semicircle", "kind": "curve", "x": [0.0, 0.5, 1.0],
                         "y": [0.0, 0.5, 0.0], "style": {"color": "w"}},
                        {"name": "ticks", "kind": "scatter", "x": [0.5], "y": [0.5],
                         "labels": ["2 ns"], "style": {"color": "y"}},
                    ]
                },
            }
        }
    )
    hist = (np.zeros((4, 4)), np.linspace(0, 1, 5), np.linspace(0, 1, 5))
    ndx = FakeNdx(_df(), x_axis="g (P1)", y_axis="s (P1)", client=client, plot=plot, hist=hist)
    ndx._plot_widget = widget  # keep the widget alive for the duration of the test
    n = pi.show_phasor_overlays(ndx, sets=["semicircle", "lifetime_ticks"], frequency_mhz=80.0)
    assert n >= 2  # curve + scatter (+ label text)
    # A second draw clears the first (no accumulation).
    n2 = pi.show_phasor_overlays(ndx, sets=["semicircle"], frequency_mhz=80.0)
    assert ndx._server_overlays["phasor"]  # tracked
    pi.clear_line_overlays(ndx, tag="phasor")
    assert not ndx._server_overlays.get("phasor")


def test_draw_overlays_on_drawing_overlay_widget():
    """The painter-based DrawingOverlayWidget backend (real ndX) uses add_curve, not addItem."""
    import pyqtgraph as pg

    from ndxplorer.widgets.drawing_overlay_widget import DrawingOverlayWidget

    pg.mkQApp()
    overlay = DrawingOverlayWidget()
    client = FakeClient(
        {
            "phasor.overlays": {
                "ok": True,
                "result": {
                    "overlays": [
                        {"name": "semicircle", "kind": "curve", "x": [0.0, 0.5, 1.0],
                         "y": [0.0, 0.5, 0.0], "style": {"color": "w"}},
                        {"name": "ticks", "kind": "scatter", "x": [0.5], "y": [0.5],
                         "labels": ["2 ns"], "style": {"color": "y"}},
                    ]
                },
            }
        }
    )
    hist = (np.zeros((4, 4)), np.linspace(0, 1, 5), np.linspace(0, 1, 5))
    ndx = FakeNdx(_df(), x_axis="g (P1)", y_axis="s (P1)", client=client, plot=overlay, hist=hist)
    n = pi.show_phasor_overlays(ndx, sets=["semicircle", "lifetime_ticks"], frequency_mhz=80.0)
    assert n >= 2  # a curve + a scatter marker (both via add_curve)
    assert len(overlay._curves) == n  # curves actually landed on the widget
    # A pre-existing user equation curve must survive our clear (surgical removal).
    overlay.add_curve(np.array([0.0, 1.0]), np.array([0.0, 1.0]))
    user_curves = len(overlay._curves)
    pi.show_phasor_overlays(ndx, sets=["semicircle"], frequency_mhz=80.0)
    pi.clear_line_overlays(ndx, tag="phasor")
    assert not ndx._server_overlays.get("phasor")
    assert len(overlay._curves) == user_curves - n  # only ours removed; user curve kept


def test_show_overlays_without_service_is_noop():
    ndx = FakeNdx(_df())  # no client -> no phasor_service
    assert pi.show_phasor_overlays(ndx) == 0
