"""The rows of the Parameters tab: scalars, and vectors as expandable rows.

A scalar constant is one row. A vector constant (:mod:`ndxplorer.core.vector_constants`)
is a parent row -- ``gamma [2]`` with its values summed up, ``0.61, 0.83`` --
whose children are its global value and one row per population, each with its
own value, fixed flag, bounds and link. The table draws the tree
(``tree_key``); this module only shapes the records, each a
:func:`~ndxplorer.app.parameter_table.parameter_record` like every other
parameter table's.
"""

from __future__ import annotations

from typing import Any, List, Mapping, Optional, Sequence

from ...core.vector_constants import (
    DEFAULT_COLUMN,
    element_name,
    split_element,
    summary_text,
)
from ..parameter_table import parameter_record

__all__ = [
    "constant_rows",
    "parse_populations",
    "parent_key",
]


def parent_key(name: str) -> str:
    """The row key of vector *name*'s parent row (never a parameter's name)."""
    return f"{name}[]"


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


def constant_rows(parameters: Sequence[Any],
                  vectors: Optional[Mapping[str, dict]] = None) -> List[dict]:
    """The table records, in the constants' order, vectors as parent + children.

    Parameters
    ----------
    parameters : sequence of Parameter
        Every constant (elements ``base[label]`` included), in order.
    vectors : mapping, optional
        ``base -> {"populations", "column", "uncertainties", ...}``: the
        vectors' order, axis and uncertainties (the group's ``"vectors"``).
    """
    params = {p.name: p for p in parameters}
    vectors = vectors or {}
    labels: dict = {}
    for name in params:
        parts = split_element(name)
        if parts is not None:
            labels.setdefault(parts[0], []).append(parts[1])
    rows: List[dict] = []
    done = set()
    for name, parameter in params.items():
        parts = split_element(name)
        base = parts[0] if parts is not None else name
        if base in labels:
            if base not in done:
                done.add(base)
                rows.extend(_vector_rows(base, labels[base], params,
                                         dict(vectors.get(base) or {})))
            continue
        rows.append(parameter_record(parameter))
    return rows


def _vector_rows(base: str, present: Sequence[str], params, meta: dict) -> List[dict]:
    order = [l for l in meta.get("populations", ()) if l in present]
    order += [l for l in present if l not in order]
    column = str(meta.get("column") or DEFAULT_COLUMN)
    errors = dict(meta.get("uncertainties") or {})
    elements = [element_name(base, l) for l in order]
    key = parent_key(base)
    parent = {
        "key": key, "param": "", "name": f"{base} [{len(order)}]",
        "value": summary_text([float(params[e].value) for e in elements]),
        "fixed": all(bool(params[e].fixed) for e in elements),
        "lo": "", "hi": "", "link": "", "parent": "",
        "note": (f"{base}: one value per population, picked per burst by the column "
                 f"'{column}'" + (" or mixed by the assignment probabilities"
                                  if meta.get("probabilities") else "")
                 + ". Right-click for the vector's menu."),
    }
    rows = [parent]
    if base in params:
        rows.append(parameter_record(params[base], name="(global)", parent=key,
                                     note=f"{base}: the value of a burst in no population."))
    for label, element in zip(order, elements):
        error = errors.get(label)
        value = float(params[element].value)
        note = f"{element}: population {label}" + (
            f", {value:.4g} ± {float(error):.2g}" if error is not None else "")
        rows.append(parameter_record(params[element], name=label, parent=key, note=note))
    return rows
