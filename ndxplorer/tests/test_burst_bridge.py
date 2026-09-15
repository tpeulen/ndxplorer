"""Gate → per-file photon intervals → ChiSurf burst-analysis RPC (headless)."""
from collections import OrderedDict

import numpy as np
import pytest

from ndxplorer.analysis.burst_bridge import (
    BurstAnalysisBridge,
    BurstBridgeError,
    selection_to_burst_slices,
)
from ndxplorer.core.data_source import DataSource


def _burst_columns(drop=()):
    """Six bursts over two files; the last straddles two files (must be dropped)."""
    columns = {
        "First File": ["a.ptu", "a.ptu", "a.ptu", "b.ptu", "b.ptu", "a.ptu"],
        "Last File": ["a.ptu", "a.ptu", "a.ptu", "b.ptu", "b.ptu", "b.ptu"],
        "First Photon": np.array([0, 100, 200, 0, 50, 300], dtype=np.int64),
        "Last Photon": np.array([40, 140, 260, 30, 90, 360], dtype=np.int64),
        "E": np.array([0.1, 0.5, 0.5, 0.9, 0.5, 0.5]),
    }
    return {k: v for k, v in columns.items() if k not in drop}


class _FakeDataSource(DataSource):
    """A burst table whose gates exclude a prescribed set of rows."""

    def __init__(self, columns, excluded_rows=()):
        super().__init__(DataSource.from_columns(columns).store)
        self._excluded = set(excluded_rows)

    def selection_mask(self, selections, idxs=(), mask_nan=True, mask_inf=True):
        return np.array([i not in self._excluded for i in range(self.size)], dtype=bool)


class _FakeRpc:
    """Records calls; echoes params back as the result.

    Also answers ``bursts.consumers``: the bridge no longer holds a list of
    analyses, it asks the server which ones exist, so a stand-in ChiSurf has to
    advertise something before anything can be dispatched to it.
    """

    ADVERTISED = [
        {"key": "fcs", "title": "FCS", "rpc": "burst_fcs.correlate_file",
         "per_file": True, "operation_type": "fcs_correlation",
         "product_type": "fcs_correlation"},
        {"key": "pda", "title": "PDA", "rpc": "pda.from_bursts",
         "per_file": False, "operation_type": "pda_histogram_computation",
         "product_type": "pda_histogram"},
    ]

    def __init__(self, ok=True):
        self.calls = []
        self._ok = ok

    def call(self, method, params):
        if method == "bursts.consumers":
            # Not recorded: discovery is bookkeeping, and counting it would make
            # every dispatch assertion below fragile.
            return {"ok": True, "result": {"consumers": self.ADVERTISED}}
        self.calls.append((method, params))
        if self._ok:
            return {"ok": True, "result": {"echo": params}}
        return {"ok": False, "error": "boom"}


# -- selection_to_burst_slices ------------------------------------------------

def test_no_selection_keeps_all_single_file_bursts():
    ds = _FakeDataSource(_burst_columns())
    slices = selection_to_burst_slices(ds, ())
    assert list(slices) == ["a.ptu", "b.ptu"]          # file order preserved
    assert slices["a.ptu"] == [(0, 40), (100, 140), (200, 260)]  # row 5 straddles -> dropped
    assert slices["b.ptu"] == [(0, 30), (50, 90)]


def test_gate_excludes_masked_rows():
    ds = _FakeDataSource(_burst_columns(), excluded_rows={1, 4})
    slices = selection_to_burst_slices(ds, [object()])  # non-empty -> mask applied
    assert slices["a.ptu"] == [(0, 40), (200, 260)]    # row 1 gone
    assert slices["b.ptu"] == [(0, 30)]                # row 4 gone


def test_missing_provenance_column_raises():
    ds = _FakeDataSource(_burst_columns(drop=["Last Photon"]))
    with pytest.raises(BurstBridgeError):
        selection_to_burst_slices(ds, ())


def test_empty_frame_returns_empty():
    ds = _FakeDataSource({})
    assert selection_to_burst_slices(ds, ()) == OrderedDict()


# -- BurstAnalysisBridge dispatch --------------------------------------------

def test_bridge_unavailable_without_rpc():
    bridge = BurstAnalysisBridge(None, _FakeDataSource(_burst_columns()))
    assert not bridge.available()
    with pytest.raises(BurstBridgeError):
        bridge.send_to_correlator([], pairs=[])


def test_correlator_one_call_per_file():
    rpc = _FakeRpc()
    bridge = BurstAnalysisBridge(rpc, _FakeDataSource(_burst_columns()))
    out = bridge.send_to_correlator((), pairs=[{"ch1": [0], "ch2": [1]}], settings={"n_casc": 20})
    assert [m for m, _ in rpc.calls] == ["burst_fcs.correlate_file", "burst_fcs.correlate_file"]
    first = rpc.calls[0][1]
    assert first["tttr_path"] == "a.ptu"
    assert first["ranges"] == [[0, 40], [100, 140], [200, 260]]
    assert first["pairs"] == [{"ch1": [0], "ch2": [1]}]
    assert first["settings"] == {"n_casc": 20}
    assert [o["file"] for o in out] == ["a.ptu", "b.ptu"]


def test_pda_single_call_with_burst_slices():
    rpc = _FakeRpc()
    bridge = BurstAnalysisBridge(rpc, _FakeDataSource(_burst_columns()))
    bridge.send_to_pda((), n_bins=81, green_channels=[0])
    assert len(rpc.calls) == 1
    method, params = rpc.calls[0]
    assert method == "pda.from_bursts"
    assert params["burst_slices"]["a.ptu"] == [[0, 40], [100, 140], [200, 260]]
    assert params["n_bins"] == 81 and params["green_channels"] == [0]


def test_generic_send_per_file_and_single():
    rpc = _FakeRpc()
    bridge = BurstAnalysisBridge(rpc, _FakeDataSource(_burst_columns()))
    bridge.send_to("burst_mle.decays", (), per_file=True, model="fit23")
    assert all(m == "burst_mle.decays" for m, _ in rpc.calls)
    assert rpc.calls[0][1]["tttr_path"] == "a.ptu" and rpc.calls[0][1]["model"] == "fit23"
    rpc.calls.clear()
    bridge.send_to("lifetime.summary", (), per_file=False)
    assert "burst_slices" in rpc.calls[0][1]


def test_rpc_error_is_raised():
    rpc = _FakeRpc(ok=False)
    bridge = BurstAnalysisBridge(rpc, _FakeDataSource(_burst_columns()))
    with pytest.raises(BurstBridgeError, match="boom"):
        bridge.send_to_pda(())


def test_empty_selection_result_raises():
    ds = _FakeDataSource(_burst_columns(), excluded_rows=set(range(6)))
    bridge = BurstAnalysisBridge(_FakeRpc(), ds)
    with pytest.raises(BurstBridgeError, match="empty"):
        bridge.send_to_pda([object()])


# -- integration: agree with the trusted .bst writer -------------------------

def test_matches_save_burst_ids_writer(tmp_path):
    """selection_to_burst_slices must reproduce what the .bst writer emits."""
    from ndxplorer.io.writer import save_burst_ids_headless

    ds = DataSource.from_columns(_burst_columns())
    save_burst_ids_headless(str(tmp_path), selections=[], data_source=ds)

    slices = selection_to_burst_slices(ds, ())
    for path, ranges in slices.items():
        bst = tmp_path / f"{path}.bst"
        written = np.atleast_2d(np.loadtxt(bst, dtype=int, delimiter="\t"))
        expected = np.array(ranges, dtype=int)
        np.testing.assert_array_equal(np.sort(written, axis=0), np.sort(expected, axis=0))


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-q"])
