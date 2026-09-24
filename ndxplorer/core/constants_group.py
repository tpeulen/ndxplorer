"""ndXplorer constants as a :class:`~ndxplorer.core.parameters.ParameterGroup`.

The model constants (``Bg``, ``gG/gR``, ``PhiA``, ``tauD0`` ...) are parameters
with value / fixed / bounds and a **link**: a constant can follow another
parameter -- a curve's, a Gaussian's, and with ChiSurf present a fit's -- and
``param.value`` then returns the master's value, so the equation engine
recomputes against it. A vector constant is a family ``base[label]`` of them
(:mod:`ndxplorer.core.vector_constants`).

Pure Python: no chisurf, no Qt. With chisurf present the registered group is
also published as ChiSurf fitting parameters (:mod:`ndxplorer.core.chisurf_binding`).
"""

from __future__ import annotations

import collections.abc
from collections import OrderedDict
from typing import Any, Dict, Iterator, List, Mapping, Optional, Sequence, Tuple

from .parameters import VECTORS_KEY, Parameter, ParameterGroup, json_copy

DEFAULT_GROUP_NAME = "ndX constants"


# ---------------------------------------------------------------- construction
def build_constants_group(
    values: Mapping[str, float],
    name: str = DEFAULT_GROUP_NAME,
) -> ParameterGroup:
    """Build a group of ``fixed=True`` parameters from a mapping.

    Constants default to ``fixed`` — they are constants until the user
    deliberately links or unfixes them. Element names (``gamma[HF]``) make
    their constant a vector.
    """
    group = ParameterGroup(name)
    apply_value_dict(group, values)
    return group


def group_to_value_dict(group: ParameterGroup) -> "OrderedDict[str, float]":
    """Flat, order-preserving ``{name: value}`` snapshot (the legacy ``.dict``).

    A vector's elements follow it by name (``gamma``, ``gamma[HF]`` …).
    """
    return OrderedDict((p.name, float(p.value)) for p in group.parameters_flat)


def apply_value_dict(group, values: Mapping[str, float]) -> None:
    """Set existing parameters' values; add any names not yet in the group.

    A new element name (``gamma[HF]``) adds that population to vector
    ``gamma`` -- made a vector, or added (at its elements' mean) when needed.
    """
    from .vector_constants import split_element

    existing = group.parameters_all_dict
    new_elements: "OrderedDict[str, List[Tuple[str, float]]]" = OrderedDict()
    for key, value in values.items():
        key = str(key)
        if key in existing:
            existing[key].value = float(value)
            continue
        parts = split_element(key)
        if parts is not None:
            new_elements.setdefault(parts[0], []).append((parts[1], float(value)))
            continue
        existing[key] = group.append_parameter(Parameter(key, float(value), fixed=True))
    for base, pairs in new_elements.items():
        parameter = group.get(base)
        if parameter is None:
            mean = sum(v for _l, v in pairs) / len(pairs)
            parameter = group.append_parameter(Parameter(base, mean, fixed=True))
        labels = parameter.populations + [l for l, _v in pairs]
        numbers = [e._value for e in parameter.elements] + [v for _l, v in pairs]
        parameter.set_vector(numbers, labels)


# ------------------------------------------------------------------ vectors
# A vector constant is a parameter with one element ``base[label]`` per
# population (:meth:`ndxplorer.core.parameters.Parameter.set_vector`); these
# are the constants' spellings of the group's vector API.


def vector_names(group) -> List[str]:
    """The vectors of *group*, in order."""
    return group.vector_names()


def is_vector(group, name: str) -> bool:
    return str(name) in vector_names(group)


def _vector(group, name: str) -> Optional[Parameter]:
    parameter = group.get(str(name))
    return parameter if parameter is not None and parameter.is_vector else None


def vector_labels(group, name: str) -> List[str]:
    """The populations of vector *name*, in the vector's order."""
    parameter = _vector(group, name)
    return parameter.populations if parameter is not None else []


def vector_elements(group, name: str) -> List[Tuple[str, Any]]:
    """``[(label, Parameter), ...]`` of vector *name*."""
    parameter = _vector(group, name)
    return list(zip(parameter.populations, parameter.elements)) if parameter is not None else []


def vector_axis(group, name: str):
    from .vector_constants import PopulationAxis

    parameter = _vector(group, name)
    return PopulationAxis.from_dict(parameter.vector_state() if parameter is not None else None)


def vector_uncertainty(group, name: str, label: str) -> Optional[float]:
    parameter = _vector(group, name)
    element = parameter.element(label) if parameter is not None else None
    return element.uncertainty() if element is not None else None


def remove_parameter(group, name: str) -> bool:
    """Take parameter *name* (a scalar, a vector, an element) out of *group*."""
    parameter = group.get(str(name))
    if parameter is None:
        return False
    group.remove_parameter(parameter)
    return True


def set_vector(group, name: str, values: Sequence[float], populations: Sequence[str],
               uncertainties: Optional[Sequence[float]] = None,
               default: Optional[float] = None, column: Optional[str] = None,
               probabilities: Optional[Mapping[str, str]] = None,
               codes: Optional[Mapping[str, float]] = None) -> List[Any]:
    """Make constant *name* a vector (:meth:`Parameter.set_vector`).

    A constant the group does not hold yet is added, fixed, at *default* or
    the mean. Returns the element parameters, in order.
    """
    if group.get(str(name)) is None:
        numbers = [float(v) for v in values]
        start = default if default is not None else sum(numbers) / max(len(numbers), 1)
        group.append_parameter(Parameter(str(name), float(start), fixed=True))
    return group.set_vector(name, values, populations, uncertainties=uncertainties,
                            default=default, column=column, probabilities=probabilities,
                            codes=codes)


def to_vector(group, name: str, populations: Sequence[str],
              column: Optional[str] = None) -> List[Any]:
    """A scalar becomes a vector: every element starts at the scalar's value."""
    return group.get(str(name)).to_vector(populations, column=column)


def to_scalar(group, name: str) -> None:
    """A vector becomes its global value again: the elements are removed."""
    parameter = group.get(str(name))
    if parameter is not None:
        parameter.to_scalar()


def group_vectors(group) -> Dict[str, Any]:
    """``{name: PopulationVector}``: what the equation engine evaluates per burst."""
    return group.vectors()


def vectors_state(group) -> Dict[str, dict]:
    """The ``"vectors"`` entry of a saved group: order, axis, uncertainties."""
    return group.vectors_state()


def apply_vector_entries(group, vectors: Mapping[str, Mapping[str, Any]]) -> List[str]:
    """Apply stored vector constants: ``{name: {"values", "populations", ...}}``.

    The format a calibration stores (and :func:`ndxplorer.io.fret_calibration_io.restorable`
    returns): per vector its ``values`` and ``populations``, optionally
    ``uncertainties`` (by population, or by position), ``default``,
    ``column``, ``probabilities``, ``codes``. Entries without values are
    skipped. Returns the names applied.
    """
    done = []
    for name, entry in dict(vectors or {}).items():
        entry = dict(entry or {})
        values, populations = entry.get("values"), entry.get("populations")
        if not values or not populations:
            continue
        populations = [str(p) for p in populations]
        uncertainties = entry.get("uncertainties")
        if isinstance(uncertainties, Mapping):
            uncertainties = [uncertainties.get(p) for p in populations]
        set_vector(group, str(name), list(values), populations, uncertainties=uncertainties,
                   default=entry.get("default"), column=entry.get("column"),
                   probabilities=entry.get("probabilities"), codes=entry.get("codes"))
        done.append(str(name))
    return done


#: How a calibration report names a factor.
_SYMBOLS = {"gamma": "γ", "alpha": "α", "beta": "β", "delta": "δ"}


def replace_shared_factors(group, result: Mapping[str, Any]) -> List[str]:
    """A calibration's shared factor replaces a population-wise one (*Make scalar*).

    A calibration result writes each factor it determined either as one value
    (``result["factors"]``) or per population (``result["vectors"]``, keyed by
    the factor's name, as :func:`ndxplorer.analysis.fret_result.species_vectors`
    writes them). A window may still hold a vector of that factor from before
    -- restored from the measurement, or an earlier run -- and the equations
    would go on reading its stale elements. So each factor the result wrote as
    one value (``applied_factors``) turns such a vector back into a scalar at
    the new value. The result records what was replaced
    (``"replaced_vectors"``) and its report says so.

    Returns the names replaced.
    """
    vectors = dict(result.get("vectors") or {})
    factors = dict(result.get("factors") or {})
    applied = list(result.get("applied_factors") or factors)
    replaced = []
    for name in applied:
        parameter = group.get(str(name))
        if name in vectors or name not in factors or parameter is None \
                or not parameter.is_vector:
            continue
        parameter.to_scalar()
        parameter.value = float(factors[name])
        replaced.append(str(name))
    if replaced and isinstance(result, dict):
        result["replaced_vectors"] = replaced
        lines = [f"  Replaced population-wise {_SYMBOLS.get(n, n)} with shared "
                 f"{_SYMBOLS.get(n, n)} = {float(factors[n]):.4f}" for n in replaced]
        result["report"] = "\n".join([str(result.get("report") or "")] + lines)
    return replaced


# ------------------------------------------------------------- serialization
def group_state(group: ParameterGroup) -> Dict[str, Any]:
    """Rich per-parameter state (value + bounds + fixed, and the vectors)."""
    return group.get_state()


def apply_group_state(group: ParameterGroup, state: Mapping[str, Any]) -> None:
    """Restore value/bounds/fixed (and the vectors) from a :func:`group_state` payload."""
    group.set_state(dict(state))


def is_state_format(data: Any) -> bool:
    """True for the rich nested ``{"parameters": {...}}`` format.

    The legacy on-disk format is a flat ``{name: value}`` object.
    """
    return (
        isinstance(data, Mapping)
        and isinstance(data.get("parameters"), Mapping)
    )


def values_from_data(data: Mapping[str, Any]) -> "OrderedDict[str, float]":
    """Extract a flat ``{name: value}`` mapping from either on-disk format."""
    if is_state_format(data):
        params = data["parameters"]
        return OrderedDict(
            (str(k), float(v.get("value"))) for k, v in params.items()
        )
    return OrderedDict((str(k), float(v)) for k, v in data.items())


def build_group_from_data(
    data: Mapping[str, Any],
    name: str = DEFAULT_GROUP_NAME,
) -> ParameterGroup:
    """Build a group from parsed JSON in *either* the flat or nested format.

    Nested payloads additionally restore bounds/fixed.
    """
    group = build_constants_group(values_from_data(data), name=name)
    if is_state_format(data):
        apply_group_state(group, data)
    return group


# --------------------------------------------------------------- live mapping
class ConstantsMapping(collections.abc.Mapping):
    """Live ``name -> float`` view over a :class:`ParameterGroup`.

    ``__getitem__`` returns the parameter's numeric ``value`` (a plain ``float``,
    never the :class:`Parameter` — the value flows straight into NumPy
    arithmetic in the equation engine), so a *linked* constant reads its master's
    current value. The data manager reads its constants through one.
    """

    def __init__(self, group: ParameterGroup):
        self._group = group

    @property
    def group(self) -> ParameterGroup:
        return self._group

    def __getitem__(self, key: str) -> float:
        parameter = self._group.get(key)
        if parameter is None:
            raise KeyError(key)
        return float(parameter.value)

    def __iter__(self) -> Iterator[str]:
        return iter(p.name for p in self._group.parameters_flat)

    def __len__(self) -> int:
        return len(self._group.parameters_flat)

    def update(self, other: Optional[Mapping[str, float]] = None, **kwargs) -> None:
        """Write values back into the group (append unknown names)."""
        merged: Dict[str, float] = {}
        if other:
            merged.update(other)
        merged.update(kwargs)
        apply_value_dict(self._group, merged)

    # -- vectors (see ndxplorer.core.vector_constants) ------------------------
    def vector_values(self) -> Dict[str, Any]:
        """``{name: PopulationVector}``: read by the equation engine per burst."""
        return group_vectors(self._group)

    def vector_names(self) -> List[str]:
        return vector_names(self._group)

    def set_vector(self, name: str, values: Sequence[float], populations: Sequence[str],
                   uncertainties: Optional[Sequence[float]] = None, **axis) -> List[Any]:
        """Make *name* a per-population vector; see :func:`set_vector`.

        ``axis`` takes ``default``, ``column``, ``probabilities``, ``codes``.
        """
        return set_vector(self._group, name, values, populations,
                          uncertainties=uncertainties, **axis)

    def to_scalar(self, name: str) -> None:
        to_scalar(self._group, name)

    def apply_vectors(self, vectors: Mapping[str, Mapping[str, Any]]) -> List[str]:
        """Stored vector constants; see :func:`apply_vector_entries`."""
        return apply_vector_entries(self._group, vectors)

    def replace_shared_factors(self, result: Mapping[str, Any]) -> List[str]:
        """See :func:`replace_shared_factors`."""
        return replace_shared_factors(self._group, result)


__all__ = [
    "DEFAULT_GROUP_NAME",
    "build_constants_group",
    "build_group_from_data",
    "group_to_value_dict",
    "apply_value_dict",
    "group_state",
    "apply_group_state",
    "is_state_format",
    "values_from_data",
    "ConstantsMapping",
    "VECTORS_KEY",
    "vector_names",
    "is_vector",
    "vector_labels",
    "vector_elements",
    "vector_axis",
    "vector_uncertainty",
    "remove_parameter",
    "set_vector",
    "to_vector",
    "to_scalar",
    "group_vectors",
    "vectors_state",
    "apply_vector_entries",
    "replace_shared_factors",
]
