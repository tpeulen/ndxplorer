"""ndX's `.pto` handling and FRET calibration run on tttrlib alone: no ChiSurf, no IMP.

Each check runs in a fresh interpreter where ``chisurf``, ``IMP`` and
``IMP.bff`` are blocked (``sys.modules[...] = None``), so a half-rebuilt
IMP.bff or a missing ChiSurf cannot take ndX's `.pto` files or the FRET menu
down with them. The blocked process reads the container itself: the burst
table (equal, column for column, to ChiSurf's own reading of it), the measured
background, and the calibrations stored in it.
"""
import json
import os
import shutil
import subprocess
import sys
import textwrap

import numpy as np
import pytest

DATA = os.environ.get("TTTRLIB_DATA", "/Users/tpeulen/dev/tttr-data")
CAL1 = os.path.join(DATA, "sm", "cal1", "001_60g_25r_cal1_cy3b_8_18_33bp_atto647n_alex.pto")
BH = os.path.join(DATA, "bh", "bh_spc132_sm_dna", "m000.pto")
CONSTANTS = {"Bg": 1.2, "Br": 0.6, "By": 0.6, "PhiA": 0.32, "PhiD": 0.8, "alpha": 0.015,
             "beta": 0.005, "forster_radius": 52.0, "gG/gR": 0.6, "r": 1.0, "tauD0": 4.0}

BLOCK = textwrap.dedent("""
    import json, sys
    for name in ("chisurf", "IMP", "IMP.bff"):
        sys.modules[name] = None
    import numpy as np

    def unblocked():
        return sorted({m.split(".")[0] for m, v in sys.modules.items()
                       if v is not None and m.split(".")[0] in ("chisurf", "IMP")})
""")

CALIBRATE = BLOCK + textwrap.dedent("""
    from ndxplorer.analysis import fret_calibration as fc
    source, constants, background = sys.argv[1], json.loads(sys.argv[2]), sys.argv[3]
    if source.endswith(".npz"):
        data = np.load(source)
        columns, container = {name: data[name] for name in data.files}, ""
    else:
        from ndxplorer.io.fret_calibration_io import container_of
        from ndxplorer.io.loading import read

        table = read(source)
        columns, container = fc.burst_columns(table), container_of(type("W", (), {"data_source": table}))
    options = fc.CalibrationOptions(donor_lifetime=constants.get("tauD0", 4.0))
    options.n_bootstrap = 10
    options.background = background
    result = fc.calibrate(columns, constants, options, container=container)
    print(json.dumps({"ok": result.get("ok"), "error": result.get("error"),
                      "factors": result.get("factors"), "notes": result.get("notes"),
                      "per_burst": result.get("background_per_burst"),
                      "constants": result.get("constants"), "unblocked": unblocked(),
                      "new_columns": sorted(result.get("new_columns") or {})}, default=str))
""")

READ = BLOCK + textwrap.dedent("""
    from ndxplorer.io.loading import read
    table = read(sys.argv[1])
    store = table.store
    out = {}
    for i in range(store.n_columns()):
        column = store.column(i)
        values = column.numpy() if column.is_numeric() else \\
            np.array([str(column.string_at(r)) for r in range(store.n_rows())])
        out[f"{i}|{column.name()}"] = values
    np.savez(sys.argv[2], **out)
    print(json.dumps({"unblocked": unblocked(), "sources": len(table.provenance["sources"])}))
""")

ROUND_TRIP = BLOCK + textwrap.dedent("""
    from ndxplorer.io import fret_calibration_io as cio
    from ndxplorer.io.loading import read

    window = type("W", (), {"data_source": read(sys.argv[1])})()
    before = len(cio.stored_calibrations(window))
    constants = {"gG/gR": 0.4321, "Bg": 1.5, "alpha": 0.123}
    saved = cio.save_calibration(constants, ndx=window, note="round trip", embed=True)
    stored = cio.stored_calibrations(window)
    loaded = cio.load_calibration(ndx=window)
    print(json.dumps({"saved": saved, "before": before, "after": len(stored),
                      "loaded": loaded.get("constants"), "note": loaded.get("note"),
                      "where": loaded.get("where"), "unblocked": unblocked()}))
""")


def _child(script, *args, cwd):
    proc = subprocess.run([sys.executable, "-c", script, *map(str, args)],
                          capture_output=True, text=True, cwd=str(cwd))
    assert proc.returncode == 0, proc.stderr[-3000:]
    out = json.loads(proc.stdout.strip().splitlines()[-1])
    assert out.pop("unblocked") == [], "chisurf/IMP was imported"
    return out


def _run(tmp_path, columns, background="fit"):
    path = tmp_path / "columns.npz"
    np.savez(path, **columns)
    return _child(CALIBRATE, path, json.dumps(CONSTANTS), background, cwd=tmp_path)


def _synthetic(seed=0):
    rng = np.random.default_rng(seed)
    dd, da, aa, dur = [], [], [], []

    def add(n, f_dd, f_da, f_aa):
        tot = rng.uniform(40, 160, n)
        dd.append(rng.poisson(f_dd * tot)), da.append(rng.poisson(f_da * tot))
        aa.append(rng.poisson(f_aa * tot)), dur.append(rng.uniform(0.5, 3.0, n))

    add(300, 1.0, 0.07, 0.003)          # donor-only
    add(300, 0.003, 0.045, 0.9)         # acceptor-only
    for e in (0.3, 0.7):                # two FRET species, gamma 0.8
        add(900, (1 - e) / 0.8, e + 0.07 * (1 - e) / 0.8 + 0.045, 0.9)
    cat = lambda v: np.concatenate(v).astype(float)  # noqa: E731
    return {"Number of Photons (green)": cat(dd), "Number of Photons (red)": cat(da),
            "Number of Photons (yellow)": cat(aa), "Duration (ms)": cat(dur)}


def _needs(path):
    if not os.path.exists(path):
        pytest.skip(f"{os.path.basename(path)} test data not present")


def test_synthetic_calibration_without_chisurf(tmp_path):
    out = _run(tmp_path, _synthetic())
    assert out["ok"], out["error"]
    assert out["factors"]["gamma"] == pytest.approx(0.8, rel=0.1)
    assert "FRET efficiency (accurate)" in out["new_columns"]


def test_cal1_calibration_without_chisurf(tmp_path):
    """The blocked process opens the `.pto` itself and gets the desktop's factors."""
    _needs(CAL1)
    out = _child(CALIBRATE, CAL1, json.dumps(CONSTANTS), "fit", cwd=tmp_path)
    assert out["ok"], out["error"]
    assert out["factors"]["gamma"] == pytest.approx(0.7502, abs=5e-4)
    assert out["factors"]["alpha"] == pytest.approx(0.1570, abs=5e-4)
    assert out["factors"]["delta"] == pytest.approx(0.0674, abs=5e-4)


def test_cal1_measured_background_without_chisurf(tmp_path):
    """``background="measurement"`` reads the rates the container stores."""
    _needs(CAL1)
    out = _child(CALIBRATE, CAL1, json.dumps(CONSTANTS), "measurement", cwd=tmp_path)
    assert out["ok"], out["error"]
    assert not any("background" in note for note in out["notes"] or []), out["notes"]
    assert out["per_burst"] == ["i_aa", "i_da", "i_dd"]
    stored = _stored_rates(CAL1)
    assert {k: out["constants"][k] for k in ("Bg", "Br", "By")} == \
        {"Bg": stored["green"], "Br": stored["red"], "By": stored["yellow"]}


def _stored_rates(path):
    """The newest ``background`` table's rates, read here with tttrlib directly."""
    import tttrlib

    handle = tttrlib.PtoFile()
    assert handle.open(path, False)
    try:
        uid = [o.uid for o in handle.objects() if o.name == "background"][-1]
        store = tttrlib.pto_store(handle, uid)
        names = [store.column(i).name() for i in range(store.n_columns())]
        detector, rate = store.column(names.index("Detector")), store.column(names.index("Rate"))
        return {detector.string_at(r).lower(): float(rate.numpy()[r]) for r in range(store.n_rows())}
    finally:
        handle.close()


@pytest.mark.parametrize("path", [CAL1, BH], ids=["cal1", "bh_spc132"])
def test_pto_columns_equal_the_chisurf_read(tmp_path, path):
    """Column for column what ChiSurf's own container reader gives."""
    _needs(path)
    pto = pytest.importorskip("chisurf.core.fio.pto")
    from chisurf.core.fio.fluorescence.burst_container import deinterleave_bursts

    out = _child(READ, path, tmp_path / "read.npz", cwd=tmp_path)
    got = np.load(tmp_path / "read.npz")
    names = [key.split("|", 1)[1] for key in got.files]
    with pto.Measurement.open(path) as measurement:
        tables = [obj for obj in measurement.artifacts(artifact_kind="burst_table")]
        expected = deinterleave_bursts(measurement.get_store(tables[-1].uid))
        assert out["sources"] == len(measurement.instrument_uids)
    assert len(names) == expected.n_columns()
    for i in range(expected.n_columns()):
        column = expected.column(i)
        name = column.name()
        if name == "Mean Macro Time (ms)":   # ndX shows it in seconds, last
            name, scale = "Mean Macro Time (s)", 1000.0
        else:
            scale = None
        key = got.files[names.index(name)]
        if column.is_numeric():
            values = np.asarray(column.numpy())
            np.testing.assert_array_equal(got[key], values if scale is None else values / scale)
        else:
            assert list(got[key]) == [str(column.string_at(r)) for r in range(expected.n_rows())]


def test_calibration_round_trip_through_a_copied_pto(tmp_path):
    """Save into a copy of the measurement, list it, load it back -- all blocked."""
    _needs(BH)
    copy = tmp_path / "m000.pto"
    shutil.copyfile(BH, copy)
    out = _child(ROUND_TRIP, copy, cwd=tmp_path)
    assert out["saved"]["ok"] and out["saved"]["where"] == "container", out["saved"]
    assert out["after"] == out["before"] + 1
    assert out["where"] == "container" and out["note"] == "round trip"
    assert out["loaded"] == {"gG/gR": 0.4321, "Bg": 1.5, "alpha": 0.123}
    assert not (tmp_path / "m000.pto.lock").exists()


def test_lifetime_route_says_it_used_the_no_linker_line(tmp_path):
    columns = _synthetic(1)
    e = columns["Number of Photons (red)"] / (columns["Number of Photons (red)"]
                                              + columns["Number of Photons (green)"])
    columns["tau (green)"] = 4.0 * (1.0 - e)
    out = _run(tmp_path, columns)
    assert out["ok"], out["error"]
    assert any("no-linker line" in note for note in out["notes"])
