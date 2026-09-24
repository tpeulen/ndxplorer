"""Vector constants: one value per population, chosen burst by burst.

A constant such as ``gamma`` can differ between the species of a
measurement (a local environment changes a dye's quantum yield). ndX holds such
a constant as a **vector over a population axis**:

* every element is an ordinary constant named ``base[label]`` --
  ``gamma[HF]``, ``gamma[LF]`` -- with its own value, fixed flag, bounds and
  link (each a :class:`~ndxplorer.core.parameters.Parameter`; with ChiSurf
  present also a ``FittingParameter`` of its own in the Global View);
* the plain name ``gamma``, when present, is the **global / default** value:
  what a burst that belongs to no population gets;
* the **axis** says how a burst picks its element: a label column (``Cluster
  Label`` by default; element *i* applies where the column equals the label's
  code) and, when the populations come with per-burst assignment
  probabilities, one probability column per label -- the burst then gets the
  probability-weighted mix ``sum_k p_k gamma_k / sum_k p_k``.

Because an element is only a name, a flat ``{name: value}`` mapping (the old
constants file, a calibration's ``constants``, the Qt window's dict) carries a
vector with no change of format; the axis, when it is not the default, travels
in the rich file format's ``"vectors"`` entry.

**Equations.** ``'gamma'`` in an equation is evaluated per burst as above;
``'gamma[HF]'`` reads that one element as a scalar. An equation that names only
scalars is evaluated exactly as before.

This module is pure (numpy only), so the equation engine, the CLI and the
browser page use it without chisurf.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from typing import Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import numpy as np

__all__ = [
    "DEFAULT_COLUMN",
    "PopulationAxis",
    "PopulationVector",
    "element_name",
    "split_element",
    "vector_bases",
    "vectors_from_values",
    "summary_text",
    "parse_populations",
]

#: The label column a new vector selects by: what K-means / Find structure write.
DEFAULT_COLUMN = "Cluster Label"

_ELEMENT = re.compile(r"^(?P<base>.*[^\s])\[(?P<label>[^\[\]]+)\]$")


def element_name(base: str, label) -> str:
    """The constant name of one element: ``gamma`` + ``HF`` -> ``gamma[HF]``."""
    return f"{base}[{label}]"


def split_element(name: str) -> Optional[Tuple[str, str]]:
    """``("gamma", "HF")`` for ``gamma[HF]``; ``None`` for a scalar name."""
    match = _ELEMENT.match(str(name))
    if match is None:
        return None
    return match.group("base"), match.group("label")


def vector_bases(names: Iterable[str]) -> "Dict[str, List[str]]":
    """``{base: [label, ...]}`` of the vectors among *names*, in their order."""
    out: Dict[str, List[str]] = {}
    for name in names:
        parts = split_element(name)
        if parts is not None:
            out.setdefault(parts[0], []).append(parts[1])
    return out


def _int_code(label: str) -> Optional[float]:
    try:
        number = float(label)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) and number == int(number) else None


@dataclass
class PopulationAxis:
    """How a burst picks its element of a vector.

    Attributes
    ----------
    column : str
        The per-burst label column. Element *i* applies where it equals the
        label's code.
    codes : dict
        ``label -> value in the column``. Unlisted labels use their own number
        when they are an integer (``"2"`` -> 2), else their position (0, 1, …).
    probabilities : dict
        ``label -> probability column``. When every listed column exists, a
        burst gets the probability-weighted mix instead of one element.
    """

    column: str = DEFAULT_COLUMN
    codes: Dict[str, float] = field(default_factory=dict)
    probabilities: Dict[str, str] = field(default_factory=dict)

    def code_of(self, label: str, position: int) -> float:
        if label in self.codes:
            return float(self.codes[label])
        number = _int_code(label)
        return float(position) if number is None else number

    def to_dict(self) -> dict:
        out: dict = {"column": self.column}
        if self.codes:
            out["codes"] = {str(k): float(v) for k, v in self.codes.items()}
        if self.probabilities:
            out["probabilities"] = {str(k): str(v) for k, v in self.probabilities.items()}
        return out

    @classmethod
    def from_dict(cls, data: Optional[Mapping]) -> "PopulationAxis":
        data = dict(data or {})
        return cls(column=str(data.get("column") or DEFAULT_COLUMN),
                   codes={str(k): float(v) for k, v in dict(data.get("codes") or {}).items()},
                   probabilities={str(k): str(v) for k, v in
                                  dict(data.get("probabilities") or {}).items()})

    def columns(self) -> List[str]:
        """Every burst column this axis reads (label column, probabilities)."""
        return [self.column] + list(self.probabilities.values())


@dataclass
class PopulationVector:
    """The values of one vector constant, ready to be evaluated per burst."""

    name: str
    labels: List[str]
    values: np.ndarray
    default: float
    axis: PopulationAxis = field(default_factory=PopulationAxis)

    def element(self, label: str) -> float:
        return float(self.values[self.labels.index(label)])

    def per_burst(self, column: Callable[[str], Optional[np.ndarray]], n_rows: int):
        """This constant for every burst: an array of *n_rows*, or the default.

        *column(name)* returns a burst column as float64, or ``None`` when the
        data has no such column.
        """
        values = np.asarray(self.values, dtype=np.float64)
        probs = self.axis.probabilities
        if probs and all(label in probs for label in self.labels):
            stack = [column(probs[label]) for label in self.labels]
            if all(p is not None for p in stack):
                p = np.nan_to_num(np.vstack(stack).T, nan=0.0)
                weight = p.sum(axis=1)
                with np.errstate(all="ignore"):
                    mixed = (p @ values) / weight
                return np.where(weight > 0.0, mixed, self.default)
        labels = column(self.axis.column)
        if labels is None:
            return float(self.default)
        out = np.full(int(n_rows), float(self.default), dtype=np.float64)
        for position, (label, value) in enumerate(zip(self.labels, values)):
            out[labels == self.axis.code_of(label, position)] = value
        return out

    def summary(self) -> str:
        return summary_text(self.values)


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


def summary_text(values: Sequence[float], limit: int = 6) -> str:
    """``"0.61, 0.83"``: a vector's values as a row shows them collapsed."""
    parts = [f"{float(v):.4g}" for v in list(values)[:limit]]
    if len(values) > limit:
        parts.append("…")
    return ", ".join(parts)


def vectors_from_values(values: Mapping[str, float],
                        axes: Optional[Mapping[str, Mapping]] = None,
                        order: Optional[Mapping[str, Sequence[str]]] = None,
                        ) -> Dict[str, PopulationVector]:
    """The vectors a flat ``{name: value}`` mapping holds.

    Parameters
    ----------
    values : mapping
        Constant names (``gamma``, ``gamma[HF]`` …) to numbers.
    axes : mapping, optional
        ``base -> PopulationAxis.to_dict()``; the default axis otherwise.
    order : mapping, optional
        ``base -> labels`` in the vector's order; the mapping's order otherwise.

    The default of a vector is its plain name's value; a vector without one
    falls back to the mean of its elements.
    """
    axes = axes or {}
    order = order or {}
    out: Dict[str, PopulationVector] = {}
    for base, labels in vector_bases(values.keys()).items():
        wanted = [str(label) for label in order.get(base, ()) if label in labels]
        labels = wanted + [label for label in labels if label not in wanted]
        numbers = np.array([float(values[element_name(base, label)]) for label in labels])
        default = values.get(base)
        default = float(default) if default is not None else float(np.nanmean(numbers))
        out[base] = PopulationVector(base, labels, numbers, default,
                                     PopulationAxis.from_dict(axes.get(base)))
    return out
