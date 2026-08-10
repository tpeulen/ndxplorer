"""Every name ndX computes with is one mmfdb defines.

ndX's equation file is a vocabulary in its own right: each entry names a derived
quantity and writes it in terms of other names. Those names reach a user as axis
labels, column headers and exported columns, so an equation referring to a
column mmfdb does not define produces a plot whose axis nothing can look up.

**mmfdb is the naming repository** (tttrlib `okf/specs/mmfdb-is-the-vocabulary.md`).
The dictionary loader used to prefer a copy bundled beside these settings, with
tttrlib's `okf/nomenclature/mmfdb.dic` as the documented canonical source; both
have been retired — tttrlib's copy had drifted from mmfdb by eighteen terms
while every test that compared it to itself passed.

Skipped, loudly, when mmfdb cannot be found: a vocabulary that cannot be checked
is a finding, not a pass.
"""

from __future__ import annotations

import os
import pathlib
import re

import pytest
import yaml

from ndxplorer.settings import mmfdb_dic

SETTINGS = pathlib.Path(mmfdb_dic.__file__).resolve().parent
EQUATIONS = SETTINGS / "mfd.equations.yaml"


def _dictionary_names() -> set[str]:
    try:
        return set(mmfdb_dic.load_dic())
    except FileNotFoundError:
        return set()


def _require_or_skip(names: set[str]) -> None:
    """A skip is right locally and never right in CI.

    A skipped conformance test reads as a pass in a CI summary, so the one
    place this check protects anybody is the one place it must not vanish.
    ChiSurf declares `mmfdb` as a dependency, so a missing dictionary here means
    something is broken rather than merely absent -- `MMFDB_REQUIRED` says so
    out loud instead of leaving a green tick.
    """
    if names:
        return
    if os.environ.get("MMFDB_REQUIRED"):
        raise AssertionError(
            "MMFDB_REQUIRED is set and no mmfdb dictionary resolved; the "
            "equation conformance test would have skipped, which in CI is "
            "indistinguishable from passing."
        )
    pytest.skip(
        "no mmfdb dictionary found; looked for the installed package, "
        "$MMFDB_DIC_DIR and ~/dev/mmfdb/src/mmfdb/data"
    )


@pytest.fixture(scope="module")
def names() -> set[str]:
    found = _dictionary_names()
    _require_or_skip(found)
    return found


@pytest.fixture(scope="module")
def equations() -> list[dict]:
    if not EQUATIONS.exists():
        pytest.skip(f"{EQUATIONS.name} not found")
    return yaml.safe_load(EQUATIONS.read_text())


def _defined_and_referenced(equations):
    defined, referenced = set(), set()
    for item in equations:
        for key, value in item.items():
            defined.add(key)
            referenced |= set(re.findall(r"'([^']+)'", str(value)))
    return defined, referenced


def test_the_dictionary_comes_from_mmfdb(names):
    """Not from a copy beside these settings, and not from tttrlib."""
    sources = [p for p in mmfdb_dic._candidate_paths() if p.exists()]
    assert sources, "no dictionary resolved at all"
    assert not any(p.parent == SETTINGS for p in sources), (
        f"ndX is reading a dictionary bundled at {SETTINGS}; mmfdb is the "
        "naming repository and the bundled copy is an offline fallback only."
    )
    assert any("mmfdb" in p.parts for p in sources), (
        f"resolved {[str(p) for p in sources]}, none of which is mmfdb's"
    )


def test_every_equation_reference_resolves(names, equations):
    """A reference is either a dictionary name or something an equation defines.

    Nothing else: a name that is neither is a column that will not exist at
    evaluation time, and the failure surfaces as an empty plot rather than as an
    error.
    """
    defined, referenced = _defined_and_referenced(equations)
    unresolved = sorted(r for r in referenced if r not in names and r not in defined)
    assert not unresolved, (
        f"{len(unresolved)} equation reference(s) are in neither mmfdb nor the "
        f"equation file: {unresolved}"
    )


def test_every_equation_output_is_an_mmfdb_name(names, equations):
    """What an equation *produces* is a column a user sees and exports, so it is
    a name in the shared vocabulary rather than one ndX coined."""
    defined, _ = _defined_and_referenced(equations)
    invented = sorted(d for d in defined if d not in names)
    assert not invented, (
        f"{len(invented)} equation output(s) are not defined in mmfdb: "
        f"{invented}. Add them to mmfdb's dictionary — improve the standard "
        "rather than working around it."
    )
