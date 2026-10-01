"""Shipped defaults merged under an older settings folder, and axis patterns.

Every test uses a temporary HOME with an old-style ``~/.ndxplorer``; the real
one is never read or written.
"""

import json
import os
import pathlib
import shutil
import time

import pytest
import yaml

from ndxplorer.settings import defaults
from ndxplorer.settings.bundle import read_settings

SHIPPED = defaults.SHIPPED_DIR
OLD = time.mktime((2026, 4, 15, 10, 40, 0, 0, 0, -1))  # before the phasor names shipped
CHANNELS = ("", " (green)", " (red)")
#: The phasor equations in shipped order: the corrected coordinates, then the lifetimes.
PHASOR_EQUATIONS = ([n for c in CHANNELS for n in (f"f_bg{c}", f"g corr{c}", f"s corr{c}")]
                    + [n for c in CHANNELS for n in (f"tau_phi{c}", f"tau_m{c}")])
PHASOR_CONSTANTS = (["f_rep", "harmonic"]
                    + [n for c in CHANNELS for n in (f"g_irf{c}", f"s_irf{c}")]
                    + [f"n_bg{c}" for c in CHANNELS] + ["g_bg", "s_bg"])
PHASOR_AXES = {"re:g( \\(.+\\))?", "re:s( \\(.+\\))?", "re:g corr( \\(.+\\))?",
               "re:s corr( \\(.+\\))?", "re:f_bg( \\(.+\\))?"}


def _old_folder(home: pathlib.Path) -> pathlib.Path:
    folder = home / ".ndxplorer"
    folder.mkdir(parents=True)
    for f in SHIPPED.iterdir():
        if f.is_file() and f.suffix in (".json", ".yaml"):
            shutil.copy2(f, folder / f.name)
    constants = json.loads((SHIPPED / "mfd.constants.json").read_text())
    for name in PHASOR_CONSTANTS:
        constants.pop(name)
    constants["alpha"] = 0.5  # a user value
    (folder / "mfd.constants.json").write_text(json.dumps(constants))
    equations = yaml.safe_load((SHIPPED / "mfd.equations.yaml").read_text())
    equations = [e for e in equations if next(iter(e)) not in PHASOR_EQUATIONS]
    equations = [e for e in equations if next(iter(e)) != "Sapp(PIE,S)"]  # deleted by the user
    (folder / "mfd.equations.yaml").write_text(yaml.safe_dump(equations, sort_keys=False))
    axes = json.loads((SHIPPED / "mfd.axis.json").read_text())
    axes = {k: v for k, v in axes.items() if not k.startswith("re:")}
    axes["Fd/Fa"]["max"] = 99.0
    (folder / "mfd.axis.json").write_text(json.dumps(axes))
    curves = yaml.safe_load((SHIPPED / "curve_equations.yaml").read_text())
    keep = [c for c in curves if defaults.SHIPPED_SINCE["curve_equations.yaml"][c["name"]] < "2026-04-15"]
    keep = [c for c in keep if c["name"] != "Circle"]  # deleted by the user
    (folder / "curve_equations.yaml").write_text(yaml.safe_dump(keep, sort_keys=False))
    for f in folder.iterdir():
        if f.is_file():
            os.utime(f, (OLD, OLD))
    return folder


@pytest.fixture
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.delenv("NDXPLORER_SETTINGS_DIR", raising=False)
    monkeypatch.setattr(pathlib.Path, "home", classmethod(lambda cls: tmp_path))
    return tmp_path


def _snapshot(folder):
    return {f.name: f.read_bytes() for f in folder.iterdir() if f.is_file()}


def test_old_folder_gets_new_shipped_entries_without_writing(home):
    folder = _old_folder(home)
    before = _snapshot(folder)
    bundle = read_settings(folder / "mfd.settings.json")
    assert bundle.added["constants"] == PHASOR_CONSTANTS
    assert bundle.constants["f_rep"] == 80.0 and bundle.constants["alpha"] == 0.5
    names = [next(iter(e)) for e in bundle.equations]
    assert bundle.added["equations"] == PHASOR_EQUATIONS
    assert names[-len(PHASOR_EQUATIONS):] == PHASOR_EQUATIONS
    assert "Sapp(PIE,S)" not in names  # shipped long before the file was written: a deletion
    assert bundle.axis_settings["Fd/Fa"]["max"] == 99.0  # the user's value wins
    assert set(bundle.added["axis"]) == PHASOR_AXES
    text = defaults.describe_added(bundle.added)
    assert text.startswith(f"Added {len(PHASOR_CONSTANTS)} new constants from the defaults: "
                           "f_rep, harmonic")
    assert defaults.describe_added(bundle.added, short=True) == (
        f"Added {len(PHASOR_CONSTANTS)} new constants from the defaults: f_rep, harmonic, "
        f"g_irf, s_irf, ... ({len(PHASOR_CONSTANTS) - 4} more); "
        f"{len(PHASOR_EQUATIONS)} new equations; {len(PHASOR_AXES)} new axis settings "
        "(see the log)")
    assert _snapshot(folder) == before  # nothing written on load


def test_curves_added_and_deleted_ones_respected(home):
    from ndxplorer.core.overlay_curves import predefined_equations_with_added

    folder = _old_folder(home)
    entries, added = predefined_equations_with_added([folder / "curve_equations.yaml"])
    names = [e["name"] for e in entries]
    assert "Universal circle" in added and "Iso-phase line" in added
    assert "WLC FRET Line (Worm-Like Chain)" in added
    assert "Circle" not in names


def test_saved_equations_record_deletions(home):
    from ndxplorer.settings.persist import write_equations

    folder = _old_folder(home)
    bundle = read_settings(folder / "mfd.settings.json")
    kept = [e for e in bundle.equations if next(iter(e)) != "tau_m"]
    write_equations(folder / "mfd.equations.yaml", kept)
    seen = json.loads((folder / defaults.SEEN_FILE).read_text())
    assert "tau_m" in seen["mfd.equations.yaml"]
    again = read_settings(folder / "mfd.settings.json")
    names = [next(iter(e)) for e in again.equations]
    assert "tau_m" not in names and "tau_phi" in names
    assert "equations" not in again.added


def test_record_overrides_the_date_rule(home):
    folder = _old_folder(home)
    (folder / defaults.SEEN_FILE).write_text(json.dumps({"mfd.equations.yaml": []}))
    bundle = read_settings(folder / "mfd.settings.json")
    assert "Sapp(PIE,S)" in bundle.added["equations"]  # never offered, so it is new


def test_shipped_files_merge_nothing():
    bundle = read_settings(SHIPPED / "mfd.settings.json")
    assert bundle.added == {}


def test_every_shipped_name_has_a_date():
    for fname, name_of in (("mfd.equations.yaml", defaults.equation_name),
                           ("curve_equations.yaml", defaults.curve_name)):
        entries = yaml.safe_load((SHIPPED / fname).read_text())
        names = [name_of(e) for e in entries if name_of(e)]
        missing = [n for n in names if n not in defaults.SHIPPED_SINCE[fname]]
        assert not missing, f"add {missing} to SHIPPED_SINCE[{fname!r}]"


def test_merge_values_user_wins():
    merged, added = defaults.merge_values({"a": 1, "b": 2}, {"b": 5, "c": 3})
    assert merged == {"a": 1, "b": 2, "c": 3} and added == ["c"]
