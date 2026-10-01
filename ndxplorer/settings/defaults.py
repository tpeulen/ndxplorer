"""The shipped defaults, merged under a user's older settings on load.

A settings folder (``~/.ndxplorer``) is seeded once from the files shipped with
ndXplorer and then belongs to the user. A constant, an equation, an axis entry
or an overlay curve shipped later is missing from it, and whatever needs it
silently does nothing (``tau_phi`` needs ``f_rep``; the phasor curves link to
it). So on load the shipped file of the same name is merged *under* the user's:

* **constants** and **axis settings** -- the user's entries win; the shipped
  names the user file lacks are added.
* **equations** (``mfd.equations.yaml``) and **overlay curves**
  (``curve_equations.yaml``) -- the user's entries win and keep their order;
  a shipped entry is appended only when its name is absent from the user file
  *and the user has never been offered it*, so an entry deleted on purpose
  stays deleted. "Offered" is:

  1. the record :func:`record_seen` writes beside the file when the user saves
     equations (``defaults_seen.json``: the shipped names at that time -- the
     load before had added the new ones, so a name missing then was deleted);
  2. without a record (a folder from before it existed), a name shipped
     (:data:`SHIPPED_SINCE`) before the user file was last written: that file
     was saved or seeded after the name existed, so it had it.

Nothing is written on load. The merged values reach the user's files only when
the user saves settings, as before.
"""

from __future__ import annotations

import datetime
import json
import pathlib
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple, Union

from ..logging_config import logging

__all__ = [
    "SHIPPED_DIR",
    "SHIPPED_SINCE",
    "SEEN_FILE",
    "shipped_file",
    "merge_values",
    "offered_names",
    "merge_named",
    "equation_name",
    "curve_name",
    "merge_equations",
    "merge_curves",
    "record_seen",
    "describe_added",
]

PathLike = Union[str, pathlib.Path]

#: Where the shipped settings are.
SHIPPED_DIR = pathlib.Path(__file__).resolve().parent

#: The record of shipped names the user has been offered, beside their files.
SEEN_FILE = "defaults_seen.json"

#: When each shipped equation and curve first shipped (its first commit's
#: date). Without a :data:`SEEN_FILE` a user file written after that date had
#: the entry, so its absence is a deletion. Every shipped name must be here
#: (``test_settings_defaults`` checks); a new one gets the day it ships.
SHIPPED_SINCE: Dict[str, Dict[str, str]] = {
    'mfd.equations.yaml': {
        'Sg': '2025-08-11',
        'Sr': '2025-08-11',
        'Sg/Sr': '2021-03-01',
        'Proximity ratio': '2021-03-01',
        'Fg': '2025-07-21',
        'Fr': '2025-07-21',
        'Fg/Fr': '2021-03-01',
        'Fd/Fa': '2021-03-01',
        'FRET efficiency': '2021-03-01',
        'R_FRET': '2025-09-20',
        'Sg(PIE)': '2025-08-11',
        'Fg(PIE)': '2025-07-21',
        'Sr(PIE)': '2025-08-11',
        'Fr(PIE)': '2025-07-21',
        'Sy(PIE)': '2025-08-11',
        'Fy(PIE)': '2025-07-22',
        'Fg/Fr(PIE)': '2025-07-22',
        'Sg/Sr(PIE)': '2025-07-22',
        'Fd/Fa(PIE)': '2025-07-22',
        'Proximity ratio(PIE)': '2025-08-11',
        'FRET efficiency(PIE)': '2025-08-11',
        'R_FRET(PIE)': '2025-11-03',
        'ratioA(PIE)': '2025-11-03',
        'FRET efficiency_AA(PIE)': '2025-11-03',
        'R_FRET,AA(PIE)': '2025-11-03',
        'Sapp(PIE,S)': '2025-08-11',
        'Sapp(PIE,F)': '2025-08-11',
        'Stoichiometry (PIE)': '2025-07-22',
        'Tg-Tr(ms)': '2025-08-11',
        '<tauD(A)>x': '2021-03-01',
        'Var_tauD(A))': '2021-03-01',
        'Total count rate green + red': '2025-07-17',
        '1/Sensitivity': '2025-07-21',
        'Sg(ALEX)': '2025-09-01',
        'Sr(ALEX)': '2025-09-01',
        'Sy(ALEX)': '2025-09-01',
        'Sx(ALEX)': '2025-09-01',
        'Fg(ALEX)': '2025-09-01',
        'Fr(ALEX)': '2025-09-01',
        'Fy(ALEX)': '2025-09-01',
        'Fg/Fr(ALEX)': '2025-09-01',
        'Sg/Sr(ALEX)': '2025-09-01',
        'Fd/Fa(ALEX)': '2025-09-01',
        'Proximity ratio(ALEX)': '2025-09-01',
        'FRET efficiency(ALEX)': '2025-09-01',
        'Sapp(ALEX,S)': '2025-09-01',
        'Sapp(ALEX,F)': '2025-09-01',
        'Stoichiometry (ALEX)': '2025-09-01',
        'Total count rate (ALEX)': '2025-09-01',
        'Rapp': '2025-09-20',
        'kFRET': '2025-09-20',
        'td_': '2025-12-09',
        'D_um2_s_from_td': '2025-12-09',
        'Rh_nm_from_D': '2025-12-09',
        'E_tau': '2026-06-29',
        'Var(E)': '2026-06-29',
        'sigma_E': '2026-06-29',
        '(1-E)*E_tau': '2026-06-29',
        '(1-E)*E': '2026-06-29',
        'tau_phi': '2026-09-29',
        'tau_m': '2026-09-29',
        'tau_phi (green)': '2026-09-29',
        'tau_m (green)': '2026-09-29',
        'tau_phi (red)': '2026-09-29',
        'tau_m (red)': '2026-09-29',
        'f_bg': '2026-09-29',
        'g corr': '2026-09-29',
        's corr': '2026-09-29',
        'f_bg (green)': '2026-09-29',
        'g corr (green)': '2026-09-29',
        's corr (green)': '2026-09-29',
        'f_bg (red)': '2026-09-29',
        'g corr (red)': '2026-09-29',
        's corr (red)': '2026-09-29',
    },
    'curve_equations.yaml': {
        'Perrin-Equation': '2025-07-08',
        'Perrin 2x rho': '2025-07-08',
        'FD/FA vs tau (static line)': '2025-07-08',
        'FD/FA vs tau (dynamic line)': '2025-07-08',
        'E vs tau (static line)': '2025-07-08',
        'kFRET vs RDA': '2025-09-20',
        'E vs tau (dynamic line)': '2025-07-08',
        'Static FRET Line (Gaussian Distribution)': '2025-07-13',
        'WLC FRET Line (Worm-Like Chain)': '2026-06-29',
        'Mixture FRET Line (Gaussian + WLC)': '2026-06-29',
        'Dynamic FRET Line (2-state Gaussian)': '2026-06-29',
        'Circle': '2025-07-13',
        'Universal circle': '2026-09-29',
        'Lifetime points': '2026-09-29',
        'FRET trajectory': '2026-09-29',
        'FRET trajectory (distance)': '2026-09-29',
        'FRET trajectory (Gaussian distance)': '2026-09-29',
        'Two-component mixing line': '2026-09-29',
        'Iso-phase line': '2026-09-29',
        'Iso-modulation arc': '2026-09-29',
    },
}


def shipped_file(name: Optional[PathLike]) -> Optional[pathlib.Path]:
    """The shipped file called like *name* (its base name), or ``None``."""
    if not name:
        return None
    path = SHIPPED_DIR / pathlib.Path(name).name
    return path if path.is_file() else None


def is_shipped(path: PathLike) -> bool:
    """Whether *path* is a shipped file itself (nothing to merge)."""
    try:
        return pathlib.Path(path).resolve().parent == SHIPPED_DIR
    except OSError:
        return False


# ------------------------------------------------------- constants and axes
def merge_values(user: Mapping[str, Any], shipped: Mapping[str, Any]) -> Tuple[Dict[str, Any], List[str]]:
    """*user* with the keys only *shipped* has added; the user's values win.

    Returns the merged mapping (the user's order, then the added keys in the
    shipped order) and the added names.
    """
    merged = dict(user or {})
    added = [key for key in (shipped or {}) if key not in merged]
    for key in added:
        value = shipped[key]
        merged[key] = dict(value) if isinstance(value, dict) else value
    return merged, added


# ------------------------------------------------------ equations and curves
def equation_name(entry: Any) -> Optional[str]:
    """The output column of an equations-file entry (``{name: expression}``)."""
    if isinstance(entry, Mapping) and len(entry) == 1:
        return str(next(iter(entry)))
    return None


def curve_name(entry: Any) -> Optional[str]:
    """The name of a ``curve_equations.yaml`` entry."""
    if isinstance(entry, Mapping) and "name" in entry:
        return str(entry["name"])
    return None


def _file_date(path: PathLike) -> Optional[datetime.date]:
    try:
        return datetime.date.fromtimestamp(pathlib.Path(path).stat().st_mtime)
    except OSError:
        return None


def _read_seen(folder: pathlib.Path) -> Dict[str, List[str]]:
    try:
        with open(folder / SEEN_FILE, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def offered_names(user_path: PathLike) -> Set[str]:
    """The shipped names the user of *user_path* has been offered (see the module)."""
    path = pathlib.Path(user_path)
    recorded = _read_seen(path.parent).get(path.name)
    if isinstance(recorded, list):
        return {str(n) for n in recorded}
    written = _file_date(path)
    if written is None:
        return set()
    since = SHIPPED_SINCE.get(path.name, {})
    return {name for name, day in since.items()
            if datetime.date.fromisoformat(day) < written}


def merge_named(user: Sequence[Any], shipped: Sequence[Any], name_of: Callable[[Any], Optional[str]],
                offered: Iterable[str] = ()) -> Tuple[List[Any], List[str]]:
    """*user*'s entries, then the shipped ones it never had nor was offered.

    Returns the merged list and the names appended.
    """
    merged = list(user or [])
    have = {name_of(e) for e in merged}
    offered = set(offered)
    added: List[str] = []
    for entry in shipped or []:
        name = name_of(entry)
        if name is None or name in have or name in offered:
            continue
        merged.append(entry)
        have.add(name)
        added.append(name)
    return merged, added


def _load_yaml(path: PathLike) -> List[Any]:
    import yaml

    with open(path, "r", encoding="utf-8") as handle:
        data = yaml.load(handle, Loader=yaml.FullLoader)
    return data if isinstance(data, list) else []


def _merge_file(user: Sequence[Any], user_path: PathLike,
                name_of: Callable[[Any], Optional[str]]) -> Tuple[List[Any], List[str]]:
    if is_shipped(user_path):
        return list(user or []), []
    source = shipped_file(user_path)
    if source is None:
        return list(user or []), []
    try:
        shipped = _load_yaml(source)
    except Exception as exc:  # noqa: BLE001 - a broken shipped file merges nothing
        logging.warning("Could not read the shipped %s: %s", source, exc)
        return list(user or []), []
    return merge_named(user, shipped, name_of, offered_names(user_path))


def merge_equations(user: Sequence[Any], user_path: PathLike) -> Tuple[List[Any], List[str]]:
    """The user's equations (read from *user_path*) with the new shipped ones appended."""
    return _merge_file(user, user_path, equation_name)


def merge_curves(user: Sequence[Any], user_path: PathLike) -> Tuple[List[Any], List[str]]:
    """The user's overlay curves (read from *user_path*) with the new shipped ones appended."""
    return _merge_file(user, user_path, curve_name)


def record_seen(path: PathLike) -> None:
    """Note, beside *path*, the shipped names of its file: the user has seen them.

    Called when the user saves an equations file; a shipped name missing from
    it was deleted then, and the next load does not add it back. Does nothing
    for a file that is not one of the shipped ones.
    """
    path = pathlib.Path(path)
    source = shipped_file(path)
    if source is None or is_shipped(path) or path.name not in SHIPPED_SINCE:
        return
    name_of = curve_name if path.name == "curve_equations.yaml" else equation_name
    try:
        names = [n for n in (name_of(e) for e in _load_yaml(source)) if n is not None]
        seen = _read_seen(path.parent)
        seen[path.name] = sorted(set(names) | set(seen.get(path.name) or []))
        with open(path.parent / SEEN_FILE, "w", encoding="utf-8") as handle:
            json.dump(seen, handle, indent=2)
    except Exception as exc:  # noqa: BLE001 - the save itself succeeded
        logging.warning("Could not record the shipped names beside %s: %s", path, exc)


# ------------------------------------------------------------------ report
_KINDS = (("constants", "constant", "constants"), ("equations", "equation", "equations"),
          ("axis", "axis setting", "axis settings"), ("curves", "overlay curve", "overlay curves"))


def describe_added(added: Mapping[str, Sequence[str]], short: bool = False) -> str:
    """One line: "Added 2 new constants from the defaults: f_rep, harmonic; 6 new equations: ...".

    *short* (the status line) names only the first kind's entries and counts
    the others; the log gets them all.
    """
    parts = []
    for key, one, many in _KINDS:
        names = list(added.get(key) or [])
        if not names:
            continue
        kind = f"{len(names)} new {one if len(names) == 1 else many}"
        if short and parts:
            parts.append(kind)
            continue
        limit = 4 if short else 8
        shown = ", ".join(names[:limit]) + (f", ... ({len(names) - limit} more)"
                                            if len(names) > limit else "")
        parts.append(f"{kind}: {shown}")
    if not parts:
        return ""
    return "Added " + parts[0].replace(": ", " from the defaults: ", 1) + \
        "".join("; " + p for p in parts[1:]) + ("" if not short or len(parts) == 1
                                                 else " (see the log)")
