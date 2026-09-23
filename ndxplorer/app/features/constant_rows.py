"""The rows of the Parameters tab: scalars, and vectors as expandable rows.

A scalar constant is one row. A vector constant (:mod:`ndxplorer.core.vector_constants`)
is a parent row -- ``gamma [2]`` with its values summed up, ``0.61, 0.83`` --
whose children are its global value and one row per population, each with its
own value, fixed flag, bounds and link. The table draws the tree
(``tree_key``); this module only builds the records.

Bounds: **Lo** and **Hi** always show a value. A bound that is enforced shows
its number, a side without one shows ``−∞`` / ``∞``. Typing a number sets that
bound (and switches enforcement on); typing nothing, ``∞`` or ``inf`` removes it.

Qt-free and chisurf-free: the rows of a plain ``{name: value}`` mapping (the
browser without chisurf's parameters) are built the same way.
"""

from __future__ import annotations

import math
from typing import Any, Dict, List, Mapping, Optional, Sequence

from ...core.vector_constants import (
    DEFAULT_COLUMN,
    element_name,
    split_element,
    summary_text,
)

__all__ = [
    "LOW",
    "HIGH",
    "constant_rows",
    "is_unbounded_text",
    "parse_populations",
    "parent_key",
]

#: What an unbounded side shows.
LOW, HIGH = "−∞", "∞"


def parent_key(name: str) -> str:
    """The row key of vector *name*'s parent row (never a parameter's name)."""
    return f"{name}[]"


def is_unbounded_text(value) -> bool:
    """Whether a typed bound means "no bound": empty, ``∞``, ``inf``, ``none``."""
    text = str(value if value is not None else "").strip().lower().lstrip("+-−")
    return text in ("", "∞", "inf", "infinity", "none")


def parse_populations(text) -> List[str]:
    """``"3"`` -> ``["0", "1", "2"]``; ``"HF, LF"`` -> ``["HF", "LF"]``.

    A count names the populations by their code in a label column (K-means
    writes 0, 1, 2 …); names are kept in their order, duplicates dropped.
    """
    text = str(text or "").strip()
    if text.isdigit():
        return [str(i) for i in range(int(text))]
    out: List[str] = []
    for part in text.replace(";", ",").split(","):
        part = part.strip()
        if part and part not in out and "[" not in part and "]" not in part:
            out.append(part)
    return out


def _bounds(p) -> tuple:
    if p is None or not bool(getattr(p, "bounds_on", False)):
        return LOW, HIGH
    lo, hi = float(p.lb), float(p.ub)
    return (lo if math.isfinite(lo) else LOW), (hi if math.isfinite(hi) else HIGH)


def _row(key: str, name: str, value, p=None, parent: str = "", note: str = "",
         param: Optional[str] = None) -> dict:
    lo, hi = _bounds(p)
    link = getattr(p, "link", None) if p is not None and getattr(p, "is_linked", False) else None
    return {
        "key": key,
        "param": key if param is None else param,
        "name": name,
        "value": value,
        "fixed": bool(p.fixed) if p is not None else True,
        "lo": lo,
        "hi": hi,
        "link": str(getattr(link, "name", "")) if link is not None else "",
        "parent": parent,
        "note": note,
    }


def constant_rows(values: Mapping[str, float], params: Optional[Mapping[str, Any]] = None,
                  vectors: Optional[Mapping[str, dict]] = None) -> List[dict]:
    """The table records, in the constants' order, vectors as parent + children.

    Parameters
    ----------
    values : mapping
        ``name -> value`` of every constant (elements ``base[label]`` included).
    params : mapping, optional
        ``name -> FittingParameter``, for the fixed flags, bounds and links.
    vectors : mapping, optional
        ``base -> {"populations", "column", "uncertainties", ...}``: the
        vectors' order, axis and uncertainties (the group's ``"vectors"``).
    """
    params = params or {}
    vectors = vectors or {}
    labels: Dict[str, List[str]] = {}
    for name in values:
        parts = split_element(name)
        if parts is not None:
            labels.setdefault(parts[0], []).append(parts[1])
    rows: List[dict] = []
    done = set()
    for name in values:
        parts = split_element(name)
        base = parts[0] if parts is not None else name
        if base in labels:
            if base not in done:
                done.add(base)
                rows.extend(_vector_rows(base, labels[base], values, params,
                                         dict(vectors.get(base) or {})))
            continue
        rows.append(_row(name, name, float(values[name]), params.get(name)))
    return rows


def _vector_rows(base: str, present: Sequence[str], values, params, meta: dict) -> List[dict]:
    order = [l for l in meta.get("populations", ()) if l in present]
    order += [l for l in present if l not in order]
    column = str(meta.get("column") or DEFAULT_COLUMN)
    errors = dict(meta.get("uncertainties") or {})
    elements = [element_name(base, l) for l in order]
    key = parent_key(base)
    summary = summary_text([float(values[e]) for e in elements])
    parent = _row(key, f"{base} [{len(order)}]", summary, None, note=(
        f"{base}: one value per population, picked per burst by the column "
        f"'{column}'" + (" or mixed by the assignment probabilities"
                         if meta.get("probabilities") else "")
        + f". Right-click for the vector's menu."), param="")
    parent["fixed"] = all(bool(getattr(params.get(e), "fixed", True)) for e in elements)
    parent["lo"] = parent["hi"] = ""
    rows = [parent]
    if base in values:
        rows.append(_row(base, "(global)", float(values[base]), params.get(base), parent=key,
                         note=f"{base}: the value of a burst in no population."))
    for label, element in zip(order, elements):
        error = errors.get(label)
        note = f"{element}: population {label}" + (
            f", {float(values[element]):.4g} ± {float(error):.2g}" if error is not None else "")
        rows.append(_row(element, label, float(values[element]), params.get(element),
                         parent=key, note=note))
    return rows
