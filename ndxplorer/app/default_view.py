"""Which parameters ndX opens a table on: the default x, y, z and weight.

A table says what it is by its columns. Images (pixel tables, one row per
pixel: ``x pixel``/``y pixel``) open on the phasor plot; burst tables open
on the view their columns allow -- lifetime against FRET for MFD data,
FRET against stoichiometry for ALEX/PIE, FRET against FRET-2CDE for cw.

Order of choice, per axis:

1. **What the user saved** (Settings > Set default axes), *for this kind of
   data*: ``default_axes`` for burst tables (the key the settings always
   had), ``default_axes_image`` for images. Used when its x and y exist in the
   table.
2. **The first view of** :data:`DEFAULT_VIEWS` (or the settings'
   ``default_views``) whose x and y the table has; each axis is a list of
   candidates, the first present one wins.
3. **The first columns that vary**, skipping index-like ones (photon
   indices, pixel coordinates, frame numbers) that make a useless histogram.

In the app, a pixel table with image geometry is then shown as the image
itself (``features/io.py`` image mode: x pixel by y pixel, weighted by the
photons), which replaces x and y and keeps z -- the image plus the lifetime
to gate on. The phasor view is what a pixel table opens on without that.

x, y and z are always three different parameters when the table has three.
Presets are matched by exact name, ignoring case -- never by substring,
because ``s (green)`` is a substring of ``Number of Photons (green)``.
"""
from __future__ import annotations

from typing import Callable, Dict, List, Mapping, Optional, Sequence

__all__ = ["DEFAULT_VIEWS", "IMAGE_MARKERS", "INDEX_LIKE", "choose_axes", "data_kind", "saved_axes_key"]

#: Columns that make a table an image (one row per pixel).
IMAGE_MARKERS = ("x pixel", "y pixel")

#: Columns that index rows rather than measure them: never a default axis.
INDEX_LIKE = ("first photon", "last photon", "x pixel", "y pixel", "frame", "pixel", "line",
              "burst id", "bid", "index", "frame time (s)", "first file", "last file")

#: The views ndX opens, per kind of table, in order of preference.
DEFAULT_VIEWS: Dict[str, List[dict]] = {
    "image": [
        {"name": "phasor",
         "x": ["g corr (green)", "g (green)", "g corr", "g"],
         "y": ["s corr (green)", "s (green)", "s corr", "s"],
         "z": ["Tau (green)", "tau_phi (green)", "tau_m (green)", "Proximity Ratio", "Number of Photons"],
         "weight": ["Number of Photons"]},
        {"name": "lifetime vs FRET",
         "x": ["Tau (green)"],
         "y": ["FRET Efficiency", "Proximity Ratio"],
         "z": ["Number of Photons"],
         "weight": ["Number of Photons"]},
        {"name": "lifetime vs brightness",
         "x": ["Tau (green)", "Tau (red)"],
         "y": ["Number of Photons"],
         "z": ["Proximity Ratio"],
         "weight": ["Number of Photons"]},
    ],
    "bursts": [
        {"name": "MFD: lifetime vs FRET",
         "x": ["Tau (green)", "TauD(A)", "tau_f"],
         "y": ["FRET Efficiency", "Proximity Ratio", "E"],
         "z": ["r Experimental (green)", "r Scatter (green)", "Stoichiometry", "Number of Photons"],
         "weight": ["Number of Photons"]},
        {"name": "ALEX/PIE: FRET vs stoichiometry",
         "x": ["FRET Efficiency", "Proximity Ratio", "E"],
         "y": ["Stoichiometry (corrected)", "Stoichiometry", "S"],
         "z": ["ALEX-2CDE", "TGX-TRR", "Duration (ms)", "Number of Photons"],
         "weight": ["Number of Photons"]},
        {"name": "cw: FRET vs FRET-2CDE",
         "x": ["FRET Efficiency", "Proximity Ratio", "E"],
         "y": ["FRET-2CDE", "Duration (ms)", "Number of Photons"],
         "z": ["Number of Photons", "Count Rate (KHz)", "Duration (ms)"],
         "weight": ["Number of Photons"]},
        {"name": "bursts: duration vs size",
         "x": ["Duration (ms)"],
         "y": ["Number of Photons"],
         "z": ["Count Rate (KHz)"],
         "weight": ["Number of Photons"]},
    ],
}


def data_kind(names: Sequence[str]) -> str:
    """``"image"`` for a pixel table, else ``"bursts"``."""
    low = {n.lower() for n in names}
    return "image" if all(m in low for m in IMAGE_MARKERS) else "bursts"


def saved_axes_key(kind: str) -> str:
    """The settings key the user's default axes for *kind* are stored under."""
    return "default_axes" if kind == "bursts" else f"default_axes_{kind}"


def _exact(names: Sequence[str], wanted: str) -> Optional[str]:
    if not wanted:
        return None
    for name in names:
        if name == wanted:
            return name
    low = wanted.lower()
    return next((n for n in names if n.lower() == low), None)


def _first(names, candidates, taken) -> Optional[str]:
    for wanted in candidates or ():
        got = _exact(names, wanted)
        if got is not None and got not in taken:
            return got
    return None


def _index_like(name: str) -> bool:
    low = name.lower()
    return low in INDEX_LIKE or low.endswith(" index")


def choose_axes(names: Sequence[str], settings: Optional[Mapping] = None,
                varies: Optional[Callable[[str], bool]] = None,
                find_saved: Optional[Callable[[Sequence[str], str], Optional[str]]] = None) -> dict:
    """The default ``x``, ``y``, ``z`` and ``weight`` for a table with *names*.

    Parameters
    ----------
    names : sequence of str
        The table's parameters, in order.
    settings : mapping, optional
        The ndX settings: ``default_axes`` / ``default_axes_<kind>`` (what the
        user saved) and an optional ``default_views`` overriding
        :data:`DEFAULT_VIEWS`.
    varies : callable, optional
        ``varies(name)`` -- whether a column takes more than one finite value;
        the last-resort choice skips constant columns with it.
    find_saved : callable, optional
        How a saved name is looked up (ndX's ``find_parameter``, which also
        accepts a substring for names the user typed). Exact match otherwise.

    Returns
    -------
    dict
        ``{"x", "y", "z", "weight", "kind", "view"}``; ``view`` says where the
        choice came from (``"saved"``, a view's name, or ``"first columns"``).
    """
    names = list(names)
    settings = settings or {}
    kind = data_kind(names)
    out = {"x": "", "y": "", "z": "", "weight": "", "kind": kind, "view": ""}
    if not names:
        return out
    views = (settings.get("default_views") or {}).get(kind) or DEFAULT_VIEWS.get(kind, [])
    lookup = find_saved or (lambda ns, w: _exact(ns, w))

    saved = settings.get(saved_axes_key(kind)) or {}
    sx, sy = lookup(names, saved.get("x", "")), lookup(names, saved.get("y", ""))
    if sx and sy and sx != sy:
        out.update(x=sx, y=sy, view="saved")
        sz = lookup(names, saved.get("z", ""))
        if sz and sz not in (sx, sy):
            out["z"] = sz
        sw = lookup(names, saved.get("weight", ""))
        if sw:
            out["weight"] = sw
    else:
        for view in views:
            x = _first(names, view.get("x"), ())
            y = _first(names, view.get("y"), {x})
            if x and y:
                out.update(x=x, y=y, view=view.get("name", ""))
                out["z"] = _first(names, view.get("z"), {x, y}) or ""
                out["weight"] = _first(names, view.get("weight"), ()) or ""
                break

    # The rest: z from the views when the choice left it open, then the
    # first measured columns that vary.
    if out["x"] and not out["z"]:
        for view in views:
            out["z"] = _first(names, view.get("z"), {out["x"], out["y"]}) or ""
            if out["z"]:
                break
    useful = [n for n in names if not _index_like(n) and (varies is None or varies(n))]
    pool = useful or names
    for axis in ("x", "y", "z"):
        if not out[axis]:
            taken = {out["x"], out["y"], out["z"]}
            out[axis] = next((n for n in pool if n not in taken), out[axis] or pool[0])
            if out["view"] == "":
                out["view"] = "first columns"
    if not out["weight"]:
        out["weight"] = _first(names, ["Number of Photons"], ()) or pool[0]
    return out
