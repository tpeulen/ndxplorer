"""Load and expose the mmfdb naming dictionary (mmCIF format).

**mmfdb is the naming repository.** Every controlled name that flows through ndX
-- a burst column, a calibration constant, a derived quantity an equation
computes -- is defined in ``mmfdb/src/mmfdb/data/*.dic`` and nowhere else.

This used to say the canonical dictionary lived in tttrlib's
``okf/nomenclature/mmfdb.dic``, and that was the problem rather than a detail:
tttrlib kept a copy, the copy drifted from mmfdb by eighteen terms, and the
registry and the writer were both brought into agreement with the copy. That
file is gone; its three genuinely-new categories (``mmfdb_burst_column``,
``mmfdb_constant``, ``mmfdb_derived_column``) were migrated into mmfdb, which is
where a name belongs.

Resolution order is mmfdb first, everywhere: the installed package,
``$MMFDB_DIC_DIR``, a sibling checkout. The copy beside this file is a
last-resort offline fallback and is not authoritative -- if it is what answers,
the names came from a file nobody maintains.

Used by the equation editor, the import path, and the conformance test, so that
every name ndX renders or validates is one mmfdb defines.
"""

from __future__ import annotations

import os
import pathlib
import re
from typing import Dict, List, Optional

_DIC_CATEGORIES = {
    "burst_column": "column",
    "constant": "name",
    "derived_column": "column",
}


def _candidate_paths() -> List[pathlib.Path]:
    """Every dictionary to read, mmfdb first.

    All of them are read and merged, not just the first that exists: mmfdb
    spreads the vocabulary over several files (`mmfdb_flr_ext.dic`,
    `mmfdb_workflow_ext.dic`) and a name may be in any of them.
    """
    here = pathlib.Path(__file__).resolve().parent
    found: List[pathlib.Path] = []

    # 1. the installed mmfdb package -- the authority
    try:
        import mmfdb

        found += sorted((pathlib.Path(mmfdb.__file__).parent / "data").glob("*.dic"))
    except Exception:  # noqa: BLE001
        pass

    # 2. an explicit override, for a checkout that is not installed
    env = os.environ.get("MMFDB_DIC_DIR")
    if env:
        found += sorted(pathlib.Path(env).glob("*.dic"))

    # 3. a sibling checkout, which is how the repositories are laid out here
    for root in (pathlib.Path.home() / "dev" / "mmfdb" / "src" / "mmfdb" / "data",):
        found += sorted(root.glob("*.dic"))

    # 4. the copy beside this file -- offline fallback only, not authoritative
    if not found:
        found = [here / "mmfdb.dic"]
    return found


_CACHE: Optional[Dict[str, dict]] = None


def _parse_mmcif_dic(text: str) -> Dict[str, dict]:
    """Parse an mmCIF .dic file, returning {column_name: metadata}.

    Extracts every item name from _mmfdb_burst_column.column,
    _mmfdb_constant.name, and _mmfdb_derived_column.column values.
    """
    columns: Dict[str, dict] = {}
    for category, key in _DIC_CATEGORIES.items():
        pattern = rf"_mmfdb_{category}\.{key}\s+(?:\"([^\"]+)\"|(\S+))"
        for m in re.finditer(pattern, text):
            name = m.group(1) or m.group(2)
            columns[name] = {"category": category}
    return columns


def load_dic(force: bool = False) -> Dict[str, dict]:
    """Load and cache the mmfdb.dic mmCIF dictionary.

    Parameters
    ----------
    force : bool
        Bypass the cache and re-read the file.

    Returns
    -------
    dict
        Mapping ``{column_name: {"category": str}}`` for every item
        defined in the dictionary.

    Raises
    ------
    FileNotFoundError
        If no mmfdb.dic is found in any candidate location.
    """
    global _CACHE
    if _CACHE is not None and not force:
        return _CACHE
    merged: Dict[str, dict] = {}
    for p in _candidate_paths():
        if p.exists():
            # Merged, not first-wins: mmfdb spreads one vocabulary over several
            # files, so a name may be in any of them and reading only the first
            # silently loses the rest.
            merged.update(_parse_mmcif_dic(p.read_text(encoding="utf-8")))
    if not merged:
        raise FileNotFoundError(
            "no mmfdb dictionary found. Searched: "
            + ", ".join(str(p) for p in _candidate_paths())
        )
    _CACHE = merged
    return _CACHE


def all_column_names() -> set[str]:
    """Every column name (burst + derived) defined in the dictionary."""
    dic = load_dic()
    return {k for k, v in dic.items() if v["category"] in ("burst_column", "derived_column")}


def all_constant_names() -> set[str]:
    """Every constant name defined in the dictionary."""
    dic = load_dic()
    return {k for k, v in dic.items() if v["category"] == "constant"}


def lookup(name: str) -> Optional[dict]:
    """Return the dictionary entry for *name*, or ``None`` if not found."""
    return load_dic().get(name)


def validate_names(names: List[str]) -> List[str]:
    """Return the subset of *names* not defined in the dictionary."""
    known = set(load_dic())
    return [n for n in names if n not in known]
