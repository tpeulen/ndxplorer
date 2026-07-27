"""Chisurf-free tests for the ndXplorer RPC subsystem (PRD-56).

No chisurf import and no live server — a fake in-memory client exercises the
:class:`PhasorService` facade and endpoint parsing / graceful degradation.
"""

from __future__ import annotations

import numpy as np
import pytest

from ndxplorer.rpc import (
    FretLines,
    LinesService,
    PhasorLines,
    PhasorService,
    RpcError,
    ZmqRpcClient,
    connect,
    parse_endpoint,
)


class FakeClient:
    """Records calls and replays canned service-result dicts keyed by method."""

    def __init__(self, responses: dict):
        self.responses = responses
        self.calls = []

    def call(self, method: str, params=None) -> dict:
        self.calls.append((method, params))
        return self.responses[method]


# -- endpoint parsing ------------------------------------------------------------------
@pytest.mark.parametrize(
    "endpoint,expected",
    [
        ("127.0.0.1:8765", ("127.0.0.1", 8765)),
        ("localhost:9000", ("localhost", 9000)),
        (":8765", ("127.0.0.1", 8765)),
        ("8765", ("127.0.0.1", 8765)),
        ("myhost", ("myhost", 8765)),
        ("", ("127.0.0.1", 8765)),
    ],
)
def test_parse_endpoint(endpoint, expected):
    assert parse_endpoint(endpoint) == expected


# -- PhasorService facade --------------------------------------------------------------
def test_apparent_lifetime_facade():
    client = FakeClient(
        {"phasor.apparent_lifetime": {"ok": True, "result": {"tau_phi": [2.0], "tau_m": [2.0]}}}
    )
    svc = PhasorService(client)
    tau_phi, tau_m = svc.apparent_lifetime(np.array([0.5]), np.array([0.5]), 80.0)
    assert tau_phi == [2.0] and tau_m == [2.0]
    # numpy arrays are marshalled to lists on the wire
    _, params = client.calls[0]
    assert params["g"] == [0.5]
    assert params["frequency_mhz"] == 80.0


def test_overlays_facade_returns_polylines():
    client = FakeClient(
        {"phasor.overlays": {"ok": True, "result": {"overlays": [{"name": "universal semicircle"}]}}}
    )
    svc = PhasorService(client)
    overlays = svc.overlays(80.0, sets=["semicircle"])
    assert overlays[0]["name"] == "universal semicircle"


def test_filter_facade():
    client = FakeClient({"phasor.filter": {"ok": True, "result": {"g": [[0.4]], "s": [[0.3]]}}})
    svc = PhasorService(client)
    g, s = svc.filter(np.array([[0.4]]), np.array([[0.3]]), kind="median")
    assert g == [[0.4]] and s == [[0.3]]


def test_facade_raises_on_error_result():
    client = FakeClient({"phasor.describe": {"ok": False, "error": "boom"}})
    svc = PhasorService(client)
    with pytest.raises(RpcError, match="boom"):
        svc.describe()


def test_facade_raises_on_empty_result():
    client = FakeClient({"phasor.describe": {}})
    svc = PhasorService(client)
    with pytest.raises(RpcError):
        svc.describe()


# -- graceful degradation --------------------------------------------------------------
def test_connect_returns_none_when_no_server():
    # Nothing is listening on this port; require=False -> graceful None.
    assert connect("127.0.0.1:1", timeout_ms=200, require=False) is None


def test_connect_raises_when_required_and_no_server():
    with pytest.raises(RpcError):
        connect("127.0.0.1:1", timeout_ms=200, require=True)


def test_zmq_client_health_false_without_server():
    client = ZmqRpcClient(cmd_port=1, timeout_ms=200)
    assert client.health() is False
    client.close()


def test_rpcclient_protocol_is_satisfied_by_fake():
    from ndxplorer.rpc import RpcClient

    assert isinstance(FakeClient({}), RpcClient)


# -- unified overlay-lines interface ---------------------------------------------------
def test_phasor_and_fret_lines_share_one_interface():
    client = FakeClient(
        {
            "phasor.overlays": {"ok": True, "result": {"overlays": [{"name": "universal semicircle"}]}},
            "fret_line.overlays": {"ok": True, "result": {"overlays": [{"name": "FRET line"}]}},
        }
    )
    phasor = PhasorLines(client)
    fret = FretLines(client)
    # Same call shape, same return shape (a list of LineSet dicts).
    assert phasor.overlays(frequency_mhz=80.0)[0]["name"] == "universal semicircle"
    assert fret.overlays(components=[], sweep={})[0]["name"] == "FRET line"


def test_lines_service_aggregates_providers():
    client = FakeClient(
        {
            "phasor.overlays": {"ok": True, "result": {"overlays": [{"name": "semicircle"}]}},
            "fret_line.overlays": {"ok": True, "result": {"overlays": [{"name": "static"}]}},
        }
    )
    svc = LinesService(client)
    assert set(svc.providers()) == {"phasor", "fret_line"}
    assert svc.phasor.overlays(frequency_mhz=80.0)[0]["name"] == "semicircle"
    assert svc.fret_line.overlays()[0]["name"] == "static"


def test_overlay_provider_raises_on_error():
    client = FakeClient({"fret_line.overlays": {"ok": False, "error": "bad sweep"}})
    with pytest.raises(RpcError, match="bad sweep"):
        FretLines(client).overlays()


def test_fret_lines_discovery_facades():
    client = FakeClient(
        {
            "fret_line.list_models": {"ok": True, "result": ["FRET: FD (Gaussian)", "FRET: Fixed distance"]},
            "fret_line.list_sweep_targets": {"ok": True, "result": [{"name": "R0"}, {"name": "R(G,1)"}]},
            "fret_line.list_projections": {"ok": True, "result": {"projections": ["E vs tau", "FD/FA vs tau"]}},
        }
    )
    fret = FretLines(client)
    assert fret.list_models() == ["FRET: FD (Gaussian)", "FRET: Fixed distance"]
    assert [t["name"] for t in fret.list_sweep_targets([])] == ["R0", "R(G,1)"]
    assert fret.list_projections() == ["E vs tau", "FD/FA vs tau"]
