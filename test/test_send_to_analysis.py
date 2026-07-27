"""A gated population, handed to an analysis, with the gate recorded beside it.

Exploring a burst parameter space finds *where* the populations are; the next
question needs their photons back. These cover the whole path — right-click a
gate, pick an analysis, the photons go to ChiSurf, and the handoff is written to
the metadata store — for all four targets, against a fake RPC so the assertions
are about the bridge rather than about ChiSurf.

The provenance half matters as much as the dispatch: a decay computed from a
sub-population is uninterpretable without the gate that produced it, so if the
gate stops travelling with the result nothing raises and the record silently
becomes useless.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from ndxplorer.analysis.burst_bridge import (
    BurstAnalysisBridge,
    BurstBridgeError,
    Target,
    describe_selections,
    summarise_result,
)
from ndxplorer.core.data_source import DataSource, RectangularDataSelection


class FakeRpc:
    """Records every call and answers with a plausible payload."""

    def __init__(self, fail_provenance: bool = False):
        self.calls = []
        self.fail_provenance = fail_provenance

    #: What this fake ChiSurf says it can do with bursts.
    ADVERTISED = [
        {"key": "fcs", "title": "FCS", "summary": "Correlate them.",
         "rpc": "burst_fcs.correlate_file", "per_file": True,
         "operation_type": "fcs_correlation", "product_type": "fcs_correlation",
         "defaults": {"pairs": [{"ch1": [0], "ch2": [1]}], "settings": {}}},
        {"key": "tcspc", "title": "TCSPC decay", "summary": "Decay them.",
         "rpc": "tcspc.from_bursts", "per_file": False,
         "operation_type": "tcspc_histogram_computation",
         "product_type": "tcspc_decay", "defaults": {"channels": [[0], [1]]}},
        {"key": "pda", "title": "PDA", "summary": "S1/S2.",
         "rpc": "pda.from_bursts", "per_file": False,
         "operation_type": "pda_histogram_computation",
         "product_type": "pda_histogram", "defaults": {"channels": [[0], [1]]}},
        {"key": "pch", "title": "PCH", "summary": "P(k).",
         "rpc": "pch.from_bursts", "per_file": False,
         "operation_type": "pch_histogram_computation",
         "product_type": "pch_histogram",
         "defaults": {"bin_time_us": 50.0, "mode": "span"},
         "caveat": "Only 'span' mode means brightness."},
    ]

    def call(self, method, params):
        self.calls.append((method, params))
        if method == "bursts.consumers":
            return {"ok": True, "result": {"consumers": self.ADVERTISED}}
        if method == "ndxplorer.record_analysis":
            if self.fail_provenance:
                return {"ok": False, "error": "database is read-only"}
            return {"ok": True, "processing_run": {"processing_id": "proc_1"}}
        if method == "tcspc.from_bursts":
            return {"ok": True, "result": {
                "decays": [{"name": "green", "counts": [1, 2, 3], "n_photons": 6}],
                "n_files": 1, "n_photons": 6}}
        if method == "pch.from_bursts":
            return {"ok": True, "result": {
                "k_vals": [0, 1], "counts": [5.0, 3.0], "p_exp": [0.625, 0.375],
                "n_bins": 8, "n_photons": 3, "mode": "span",
                "bin_time_us": 50.0, "burst_duty_cycle": 0.4}}
        if method == "pda.from_bursts":
            return {"ok": True, "result": {
                "curves": [{"name": "c", "shape": [3, 3], "n_photons": 9}],
                "n_files": 1}}
        return {"ok": True, "result": {"curves": []}}

    def methods(self):
        return [m for m, _ in self.calls]


def _burst_table(n: int = 6) -> DataSource:
    """A burst table with the provenance columns the bridge needs."""
    frame = pd.DataFrame({
        "First File": ["m.ptu"] * n,
        "Last File": ["m.ptu"] * n,
        "First Photon": np.arange(n) * 1000,
        "Last Photon": np.arange(n) * 1000 + 499,
        "Proximity ratio": np.linspace(0.05, 0.95, n),
    })
    return DataSource(list(frame.columns), frame)


class Owner:
    """The identifiers provenance needs, without a whole window."""

    processed_data_id = "proc_data_7"
    experiment_id = "exp_42"


@pytest.fixture
def bridge():
    """A bridge over a fake ChiSurf, attributed to a database product."""
    return BurstAnalysisBridge(FakeRpc(), _burst_table(), owner=Owner())


@pytest.fixture
def gate():
    """A gate keeping the high-FRET half of the table."""
    return [RectangularDataSelection(parameter_idx=4, lower=0.5, upper=1.0)]


# ------------------------------------------------------------------ registry


def test_the_client_hard_codes_no_analyses(bridge):
    """The menu is what ChiSurf advertises, not a list kept in ndXplorer.

    This is the property that lets a new burst analysis — including one in a
    ChiSurf plugin — appear here with no client release, and stops an older
    ChiSurf from producing a menu full of methods it does not have.
    """
    import ndxplorer.analysis.burst_bridge as module
    import ndxplorer.analysis.send_menu as menu_module

    for name in ("TARGETS", "TARGETS_BY_KEY"):
        assert not hasattr(module, name), f"{name} is back; the client is guessing again"
    for rpc in ("pda.from_bursts", "pch.from_bursts", "tcspc.from_bursts"):
        assert rpc not in menu_module.__doc__ or "advertis" in menu_module.__doc__

    assert list(bridge.discover()) == ["fcs", "tcspc", "pda", "pch"]


def test_discovery_asks_once_and_caches(bridge):
    """The advertised set changes when ChiSurf changes, not while working."""
    bridge.discover()
    bridge.discover()
    assert bridge._rpc.methods().count("bursts.consumers") == 1
    bridge.discover(refresh=True)
    assert bridge._rpc.methods().count("bursts.consumers") == 2


def test_a_chisurf_that_advertises_nothing_yields_no_menu(gate):
    """An older ChiSurf must produce an empty menu, not a menu of guesses."""

    class Silent(FakeRpc):
        def call(self, method, params):
            if method == "bursts.consumers":
                return {"ok": False, "error": "method not found"}
            return super().call(method, params)

    quiet = BurstAnalysisBridge(Silent(), _burst_table(), owner=Owner())
    assert quiet.discover() == {}
    with pytest.raises(BurstBridgeError, match="does not advertise"):
        quiet.send("pda", gate)


def test_a_malformed_advertisement_is_skipped_not_fatal(gate):
    """One bad entry must not cost the user the whole menu."""

    class Sloppy(FakeRpc):
        def call(self, method, params):
            if method == "bursts.consumers":
                return {"ok": True, "result": {"consumers": [
                    {"title": "no key at all"},
                    {"key": "pda", "rpc": "pda.from_bursts"},
                ]}}
            return super().call(method, params)

    bridge = BurstAnalysisBridge(Sloppy(), _burst_table(), owner=Owner())
    assert list(bridge.discover()) == ["pda"]


def test_advertised_defaults_fill_in_and_unknown_fields_are_ignored():
    """A newer ChiSurf may advertise fields this client has no use for."""
    target = Target.from_dict({
        "key": "x", "rpc": "x.go", "something_new": 42,
    })
    assert target.key == "x" and target.rpc == "x.go"
    assert target.title == "x" and target.defaults == {}
    assert target.operation_type == "analysis"


def test_chisurf_advertises_terms_the_store_will_accept():
    """The real advertisement must use the mmCIF vocabulary.

    The store rejects an unknown term on write, so a typo would surface as a
    failed provenance record long after the send appeared to work.
    """
    models = pytest.importorskip("mmfdb.models")
    consumers = pytest.importorskip("chisurf.server.services.bursts").consumers
    advertised = consumers(None)["result"]["consumers"]

    assert {c["key"] for c in advertised} >= {"fcs", "tcspc", "pda", "pch"}
    for entry in advertised:
        assert entry["operation_type"] in models.OPERATION_TYPES, entry["key"]
        assert entry["product_type"] in models.ARTIFACT_TYPES, entry["key"]


def test_the_pch_caveat_is_advertised_by_chisurf():
    """The analysis that needs a qualification is the one that declares it."""
    consumers = pytest.importorskip("chisurf.server.services.bursts").consumers
    pch = next(
        c for c in consumers(None)["result"]["consumers"] if c["key"] == "pch"
    )
    assert "span" in pch["caveat"] and "brightness" in pch["caveat"]


# ------------------------------------------------------------------- dispatch


@pytest.mark.parametrize("key", ["fcs", "tcspc", "pda", "pch"])
def test_each_target_calls_its_own_rpc_with_the_gated_bursts(bridge, gate, key):
    """The gate must reach the analysis as photon intervals, per file."""
    reply = bridge.send(key, gate)
    spec = bridge.target(key)

    assert spec.rpc in bridge._rpc.methods()
    assert reply["target"] == key
    assert reply["n_files"] == 1
    assert reply["n_bursts"] == 3, "the gate keeps the upper half of six bursts"

    _, params = next(c for c in bridge._rpc.calls if c[0] == spec.rpc)
    if spec.per_file:
        assert params["tttr_path"] == "m.ptu"
        assert len(params["ranges"]) == 3
    else:
        assert list(params["burst_slices"]) == ["m.ptu"]
        assert len(params["burst_slices"]["m.ptu"]) == 3


def test_target_defaults_apply_and_can_be_overridden(bridge, gate):
    """Defaults spare the caller; explicit parameters must still win."""
    bridge.send("pch", gate)
    _, params = next(c for c in bridge._rpc.calls if c[0] == "pch.from_bursts")
    assert params["mode"] == "span" and params["bin_time_us"] == 50.0

    bridge.send("pch", gate, mode="interior", bin_time_us=200.0)
    _, params = [c for c in bridge._rpc.calls if c[0] == "pch.from_bursts"][-1]
    assert params["mode"] == "interior" and params["bin_time_us"] == 200.0


def test_an_unknown_target_is_refused(bridge, gate):
    """A typo must not silently become a call to nothing."""
    with pytest.raises(BurstBridgeError, match="does not advertise"):
        bridge.send("nmr", gate)


def test_an_empty_gate_is_refused(bridge):
    """Sending everything is never what "send the selection" meant."""
    everything = [RectangularDataSelection(parameter_idx=4, lower=10.0, upper=11.0)]
    with pytest.raises(BurstBridgeError, match="empty"):
        bridge.send("pda", everything)


def test_without_a_connection_nothing_is_sent(gate):
    """No ChiSurf means a clear refusal, not a half-completed send."""
    offline = BurstAnalysisBridge(None, _burst_table(), owner=Owner())
    assert not offline.available()
    with pytest.raises(BurstBridgeError, match="no ChiSurf RPC connection"):
        offline.send("pda", gate)


# ----------------------------------------------------------------- provenance


@pytest.mark.parametrize("key", ["fcs", "tcspc", "pda", "pch"])
def test_every_send_is_recorded_with_its_gate(bridge, gate, key):
    """The record must carry the gate, not merely say an analysis happened."""
    reply = bridge.send(key, gate)
    spec = bridge.target(key)

    assert reply["provenance"]["ok"] is True
    _, payload = next(
        c for c in bridge._rpc.calls if c[0] == "ndxplorer.record_analysis"
    )

    assert payload["input_processed_data_ids"] == ["proc_data_7"]
    assert payload["experiment_id"] == "exp_42"
    assert payload["products"][0]["product_type"] == spec.product_type

    settings = payload["settings"]
    assert settings["operation_type"] == spec.operation_type
    assert settings["rpc"] == spec.rpc
    assert settings["n_bursts"] == 3
    assert settings["bursts_per_file"] == {"m.ptu": 3}

    described = settings["gate"]
    assert len(described) == 1
    assert described[0]["type"] == "RectangularDataSelection"
    assert described[0]["lower"] == 0.5 and described[0]["upper"] == 1.0


def test_a_failed_provenance_write_keeps_the_analysis(gate):
    """Losing the record is bad; discarding a finished computation is worse."""
    bridge = BurstAnalysisBridge(
        FakeRpc(fail_provenance=True), _burst_table(), owner=Owner()
    )
    reply = bridge.send("tcspc", gate)

    assert reply["result"]["n_photons"] == 6, "the analysis result survived"
    assert reply["provenance"]["ok"] is False
    assert "read-only" in reply["provenance"]["error"]


def test_no_database_product_means_no_record_and_no_error(gate):
    """A bridge driven from a script has nothing to attribute the work to."""
    bridge = BurstAnalysisBridge(FakeRpc(), _burst_table(), owner=None)
    reply = bridge.send("pda", gate)
    assert reply["provenance"] is None
    assert "ndxplorer.record_analysis" not in bridge._rpc.methods()


def test_recording_can_be_switched_off(bridge, gate):
    """Batch callers that record their own operation must be able to opt out."""
    reply = bridge.send("pda", gate, record=False)
    assert reply["provenance"] is None
    assert "ndxplorer.record_analysis" not in bridge._rpc.methods()


def test_the_result_payload_is_summarised_not_embedded(bridge, gate):
    """The store indexes provenance; it is not a results archive.

    A PDA histogram or a set of correlation curves can be megabytes, and
    embedding them would make every provenance query drag the data along.
    """
    bridge.send("tcspc", gate)
    _, payload = next(
        c for c in bridge._rpc.calls if c[0] == "ndxplorer.record_analysis"
    )
    stored = payload["products"][0]["data"]

    assert stored["analysis"] == "tcspc"
    assert stored["decays"] == [{"name": "green", "n_photons": 6, "n_bins": 3}]
    assert "counts" not in stored


def test_the_pch_bias_warning_reaches_the_record():
    """An interior-mode P(k) is biased, and the record must say so.

    Someone reading the provenance later has no other way to know the histogram
    cannot be read as an absolute brightness.
    """
    spec = Target(key="pch", title="PCH", rpc="pch.from_bursts")
    stored = summarise_result(
        spec, {"mode": "interior", "selection_bias": "…not valid as an absolute…",
               "n_bins": 10, "burst_duty_cycle": 0.2}
    )
    assert stored["mode"] == "interior"
    assert "selection_bias" in stored
    assert stored["burst_duty_cycle"] == 0.2


def test_unrecognised_selections_still_describe_themselves():
    """Gate shapes differ; an unknown one must not vanish from the record."""

    class OddSelection:
        name = "drawn mask"
        enabled = True

    described = describe_selections([OddSelection()])
    assert described == [{"type": "OddSelection", "name": "drawn mask", "enabled": True}]


# ------------------------------------------------------------------ the menu


@pytest.fixture(scope="module")
def qt_app():
    """A single QApplication for the module (offscreen)."""
    from qtpy import QtWidgets

    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


@pytest.fixture
def explorer(qt_app):
    """A window holding a burst table with provenance columns."""
    from ndxplorer.core.plot_main import NDXplorer

    window = NDXplorer(data_source=_burst_table(20))
    window.plot_control.update(update_comboboxes=True, update_plots=False)
    qt_app.processEvents()
    yield window
    window.close()


def _submenu(window):
    """Build a context menu and return its send submenu."""
    from qtpy import QtWidgets

    from ndxplorer.analysis.send_menu import add_send_menu

    menu = QtWidgets.QMenu()
    return add_send_menu(menu, window), menu


def test_the_menu_offers_what_chisurf_advertises(explorer):
    """One entry per advertised consumer, in the order ChiSurf gave them."""
    explorer.chisurf_rpc = FakeRpc()
    submenu, _menu = _submenu(explorer)
    from ndxplorer.analysis.send_menu import make_bridge

    advertised = [t.title for t in make_bridge(explorer).discover().values()]
    assert [a.text() for a in submenu.actions()] == advertised
    assert advertised, "nothing was advertised, so the menu proves nothing"


def test_the_menu_says_why_it_is_disabled_rather_than_hiding(explorer, qt_app):
    """A missing entry reads as "no such feature"; a reason is actionable.

    Three things can block a send — no ChiSurf, no burst columns, no gate — and
    which one it is determines what the user does next.
    """
    from ndxplorer.analysis.send_menu import why_unavailable

    # No connection.
    explorer.chisurf_rpc = None
    submenu, _menu = _submenu(explorer)
    assert not submenu.isEnabled()
    assert "No ChiSurf connection" in submenu.title()
    assert all(not a.isEnabled() for a in submenu.actions())

    # Connected, but nothing gated: the whole table is not a selection.
    explorer.chisurf_rpc = FakeRpc()
    assert "No selection" in (why_unavailable(explorer) or "")
    submenu, _menu = _submenu(explorer)
    assert not submenu.isEnabled()

    # Gated: everything opens up.
    columns = list(explorer.data_source.data.columns)
    explorer.plot_control.addSelection(
        columns.index("Proximity ratio"), 0.5, 1.0, False, True, "Proximity ratio"
    )
    qt_app.processEvents()
    assert why_unavailable(explorer) is None
    submenu, _menu = _submenu(explorer)
    assert submenu.isEnabled()
    assert all(a.isEnabled() for a in submenu.actions())


def test_a_table_without_burst_provenance_cannot_be_sent(qt_app):
    """Sending needs the photon intervals, which a plain table does not carry."""
    from ndxplorer.analysis.send_menu import why_unavailable
    from ndxplorer.core.plot_main import NDXplorer

    frame = pd.DataFrame({"a": [1.0, 2.0], "b": [3.0, 4.0]})
    window = NDXplorer(data_source=DataSource(list(frame.columns), frame))
    try:
        window.chisurf_rpc = FakeRpc()
        reason = why_unavailable(window)
        assert "burst provenance" in reason
        assert "First Photon" in reason
    finally:
        window.close()


def test_choosing_an_entry_sends_and_reports(explorer, qt_app):
    """Clicking through must reach the RPC and say what happened."""
    from ndxplorer.analysis.send_menu import send_selection

    explorer.chisurf_rpc = FakeRpc()
    columns = list(explorer.data_source.data.columns)
    explorer.plot_control.addSelection(
        columns.index("Proximity ratio"), 0.5, 1.0, False, True, "Proximity ratio"
    )
    qt_app.processEvents()

    reply = send_selection(explorer, "tcspc")
    assert reply is not None
    assert "tcspc.from_bursts" in explorer.chisurf_rpc.methods()
    # No database product attached, so nothing to attribute the operation to.
    assert reply["provenance"] is None
    assert "not recorded" in explorer.statusBar().currentMessage()


def test_a_refused_send_reports_instead_of_raising(explorer):
    """A disabled reason reached by other means must not crash the window."""
    from ndxplorer.analysis.send_menu import send_selection

    explorer.chisurf_rpc = None
    assert send_selection(explorer, "pda") is None
    assert "No ChiSurf connection" in explorer.statusBar().currentMessage()


# ------------------------------------------------- the two sides, end to end


def test_ndx_renders_what_chisurf_actually_advertises():
    """The contract, checked against the real service rather than a fake.

    Both halves are easy to keep self-consistent and still not fit each other:
    ChiSurf could advertise a field name the client ignores, or the client could
    require one ChiSurf never sends. This drives the real ``bursts.consumers``
    through the real ``Target.from_dict`` and asserts the result is usable.
    """
    service = pytest.importorskip("chisurf.server.services.bursts")

    class RealChiSurf:
        """Answers exactly what the ChiSurf service answers."""

        def __init__(self):
            self.calls = []

        def call(self, method, params):
            self.calls.append((method, params))
            if method == "bursts.consumers":
                return service.consumers(None)
            return {"ok": True, "result": {}}

        def methods(self):
            return [m for m, _ in self.calls]

    bridge = BurstAnalysisBridge(RealChiSurf(), _burst_table(), owner=Owner())
    targets = bridge.discover()

    assert set(targets) >= {"fcs", "tcspc", "pda", "pch"}
    for target in targets.values():
        assert target.rpc and target.title and target.summary
        assert isinstance(target.per_file, bool)
        assert isinstance(target.defaults, dict)

    # The call shapes ChiSurf declares must match how the services are written:
    # FCS takes one file at a time, the rest take the whole mapping.
    assert targets["fcs"].per_file is True
    assert all(not targets[k].per_file for k in ("tcspc", "pda", "pch"))

    # And the one analysis that needs a qualification carries it to the client.
    assert targets["pch"].caveat and "span" in targets["pch"].caveat


def test_every_advertised_rpc_exists_on_the_server():
    """An advertised method that is not registered is a menu entry that fails.

    The failure would only appear when a user clicks it, which is the worst
    possible moment to discover a name is wrong.
    """
    import json
    from importlib import resources

    service = pytest.importorskip("chisurf.server.services.bursts")
    advertised = {c["rpc"] for c in service.consumers(None)["result"]["consumers"]}

    with resources.files("chisurf.server").joinpath("server_methods.json").open() as fp:
        spec = json.load(fp)
    entries = spec if isinstance(spec, list) else spec.get("methods", [])
    registered = {e["rpc"] for e in entries if "rpc" in e}

    # burst_fcs.* is a plugin service, registered through the plugin manifest
    # rather than the core registry, so it is checked separately.
    core = {r for r in advertised if not r.startswith("burst_fcs.")}
    assert core <= registered, f"advertised but unregistered: {core - registered}"

    plugin_manifest = json.loads(
        (
            resources.files("chisurf.plugins.burst.burst_fcs_correlator")
            / "manifest.json"
        ).read_text(encoding="utf-8")
    )
    plugin_rpcs = {m["name"] for m in plugin_manifest.get("rpc_methods", [])}
    assert {"burst_fcs.correlate_file"} <= plugin_rpcs
