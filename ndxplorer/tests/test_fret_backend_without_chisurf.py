"""The accurate-FRET calibration runs on tttrlib alone: no ChiSurf, no IMP.

Each check runs :func:`ndxplorer.analysis.fret_calibration.calibrate` in a fresh
interpreter where ``chisurf`` and ``IMP`` are blocked (``sys.modules[...] =
None``), so a half-rebuilt IMP.bff or a missing ChiSurf cannot take the FRET
menu down with it. The cal1 burst columns are read in this process (reading a
``.pto`` still goes through ChiSurf's container reader) and handed over as an
``.npz``.
"""
import os
import subprocess
import sys
import textwrap

import numpy as np
import pytest

CAL1 = os.path.join(os.environ.get("TTTRLIB_DATA", "/Users/tpeulen/dev/tttr-data"), "sm", "cal1",
                    "001_60g_25r_cal1_cy3b_8_18_33bp_atto647n_alex.pto")
CONSTANTS = {"Bg": 1.2, "Br": 0.6, "By": 0.6, "PhiA": 0.32, "PhiD": 0.8, "alpha": 0.015,
             "beta": 0.005, "forster_radius": 52.0, "gG/gR": 0.6, "r": 1.0, "tauD0": 4.0}

CHILD = textwrap.dedent("""
    import json, sys
    sys.modules["chisurf"] = None
    sys.modules["IMP"] = None
    import numpy as np
    from ndxplorer.analysis import fret_calibration as fc
    data = np.load(sys.argv[1])
    columns = {name: data[name] for name in data.files}
    constants = json.loads(sys.argv[2])
    options = fc.CalibrationOptions(donor_lifetime=constants.get("tauD0", 4.0))
    options.n_bootstrap = 10
    result = fc.calibrate(columns, constants, options)
    assert "chisurf" not in [m.split(".")[0] for m, v in sys.modules.items() if v is not None]
    print(json.dumps({"ok": result.get("ok"), "error": result.get("error"),
                      "factors": result.get("factors"), "notes": result.get("notes"),
                      "new_columns": sorted(result.get("new_columns") or {})}))
""")


def _run(tmp_path, columns):
    path = tmp_path / "columns.npz"
    np.savez(path, **columns)
    import json

    proc = subprocess.run([sys.executable, "-c", CHILD, str(path), json.dumps(CONSTANTS)],
                          capture_output=True, text=True, cwd=str(tmp_path))
    assert proc.returncode == 0, proc.stderr[-2000:]
    return json.loads(proc.stdout.strip().splitlines()[-1])


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


def test_synthetic_calibration_without_chisurf(tmp_path):
    out = _run(tmp_path, _synthetic())
    assert out["ok"], out["error"]
    assert out["factors"]["gamma"] == pytest.approx(0.8, rel=0.1)
    assert "FRET efficiency (accurate)" in out["new_columns"]


def test_cal1_calibration_without_chisurf(tmp_path):
    if not os.path.exists(CAL1):
        pytest.skip("cal1 test data not present")
    try:
        from ndxplorer.io.loading import read

        source = read(CAL1)
    except Exception as exc:  # noqa: BLE001 - reading a .pto needs ChiSurf here
        pytest.skip(f"cal1 could not be read in the parent: {exc}")
    from ndxplorer.analysis.fret_calibration import burst_columns

    out = _run(tmp_path, burst_columns(source))
    assert out["ok"], out["error"]
    # the same factors the Qt window gets with ChiSurf present: the gates, the
    # fitted background and the 1/S-vs-E fit do not use the static line
    assert out["factors"]["gamma"] == pytest.approx(0.7502, abs=5e-4)
    assert out["factors"]["alpha"] == pytest.approx(0.1570, abs=5e-4)
    assert out["factors"]["delta"] == pytest.approx(0.0674, abs=5e-4)


def test_lifetime_route_says_it_used_the_no_linker_line(tmp_path):
    columns = _synthetic(1)
    e = columns["Number of Photons (red)"] / (columns["Number of Photons (red)"]
                                              + columns["Number of Photons (green)"])
    columns["tau (green)"] = 4.0 * (1.0 - e)
    out = _run(tmp_path, columns)
    assert out["ok"], out["error"]
    assert any("no-linker line" in note for note in out["notes"])
