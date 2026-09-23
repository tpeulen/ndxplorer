"""ndXplorer constants as a chisurf ``FittingParameterGroup``.

ndXplorer's model constants (``Bg``, ``gG/gR``, ``PhiA``, ``tauD0`` …) used to be
plain floats in a dict. Wrapping them in a :class:`FittingParameterGroup` of
:class:`FittingParameter` objects lets the GUI render them in chisurf's
fitting-parameter table (value / fixed / bounds + a **link** menu) and lets a
constant be *crosslinked* to a parameter of an actual chisurf fit — when the
linked value changes, ``param.value`` returns the linked master's value, so the
equation engine recomputes against the fit.

This module is deliberately **Qt-free** so it is headless-testable and importable
wherever chisurf-core is available. The GUI wiring lives in
``ndxplorer/ui/parameter_editor.py``.
"""

from __future__ import annotations

import collections.abc
from collections import OrderedDict
from typing import Any, Dict, Iterator, List, Mapping, Optional, Sequence, Tuple

# chisurf is imported lazily inside the functions that build parameters, so the
# pure format helpers (is_state_format / values_from_data) — used by the Qt-free,
# chisurf-free CLI and settings loaders — import without a chisurf dependency.

DEFAULT_GROUP_NAME = "ndX constants"


# ---------------------------------------------------------------- construction
def build_constants_group(
    values: Mapping[str, float],
    name: str = DEFAULT_GROUP_NAME,
) -> FittingParameterGroup:
    """Build a group of ``fixed=True`` :class:`FittingParameter`s from a mapping.

    Constants default to ``fixed`` — they are constants until the user
    deliberately links or unfixes them.
    """
    from chisurf.core.fitting.parameter import FittingParameter, FittingParameterGroup

    group = FittingParameterGroup(name=name)
    # ``parameters_all`` reads ``_parameters``, which is only initialised by
    # ``find_parameters()`` — appending before that raises.
    group.find_parameters()
    for key, value in values.items():
        group.append_parameter(
            FittingParameter(name=str(key), value=float(value), fixed=True)
        )
    return group


def group_to_value_dict(group: FittingParameterGroup) -> "OrderedDict[str, float]":
    """Flat, order-preserving ``{name: value}`` snapshot (the legacy ``.dict``)."""
    return OrderedDict((p.name, float(p.value)) for p in group.parameters_all)


def apply_value_dict(group, values: Mapping[str, float]) -> None:
    """Set existing parameters' values; append any names not yet in the group."""
    from chisurf.core.fitting.parameter import FittingParameter

    existing = group.parameters_all_dict
    for key, value in values.items():
        key = str(key)
        if key in existing:
            existing[key].value = float(value)
        else:
            group.append_parameter(
                FittingParameter(name=key, value=float(value), fixed=True)
            )


# ------------------------------------------------------------------ vectors
# A vector constant is a family of parameters ``base[label]`` (one per
# population) beside the optional global ``base``; see
# :mod:`ndxplorer.core.vector_constants`. What names cannot say -- the order of
# the populations, the axis a burst picks its element by, the uncertainties a
# calibration gave -- is kept on the group as ``_ndx_vectors``.
VECTORS_KEY = "vectors"


def _vector_meta(group) -> Dict[str, dict]:
    meta = getattr(group, "_ndx_vectors", None)
    if not isinstance(meta, dict):
        meta = {}
        group._ndx_vectors = meta
    return meta


def _bump(group) -> None:
    """The group's structure changed: cached factor graphs are stale."""
    try:
        from chisurf.core.fitting import factorgraph

        factorgraph.bump_structure_version()
    except Exception:  # noqa: BLE001 - nothing cached, nothing to invalidate
        pass


def vector_names(group) -> List[str]:
    """The vectors of *group*, in the order their elements appear."""
    from .vector_constants import vector_bases

    return list(vector_bases(p.name for p in group.parameters_all))


def is_vector(group, name: str) -> bool:
    return str(name) in vector_names(group)


def vector_labels(group, name: str) -> List[str]:
    """The populations of vector *name*, in the vector's order."""
    from .vector_constants import vector_bases

    present = vector_bases(p.name for p in group.parameters_all).get(str(name), [])
    wanted = [l for l in _vector_meta(group).get(str(name), {}).get("populations", [])
              if l in present]
    return wanted + [l for l in present if l not in wanted]


def vector_elements(group, name: str) -> List[Tuple[str, Any]]:
    """``[(label, FittingParameter), ...]`` of vector *name*."""
    from .vector_constants import element_name

    params = group.parameters_all_dict
    return [(l, params[element_name(name, l)]) for l in vector_labels(group, name)]


def vector_axis(group, name: str):
    from .vector_constants import PopulationAxis

    return PopulationAxis.from_dict(_vector_meta(group).get(str(name)))


def vector_uncertainty(group, name: str, label: str) -> Optional[float]:
    value = _vector_meta(group).get(str(name), {}).get("uncertainties", {}).get(str(label))
    return None if value is None else float(value)


def _append(group, name: str, value: float, fixed: bool = True):
    from chisurf.core.fitting.parameter import FittingParameter

    parameter = FittingParameter(name=str(name), value=float(value), fixed=bool(fixed))
    group.append_parameter(parameter)
    return parameter


def remove_parameter(group, name: str) -> bool:
    """Take parameter *name* (a scalar, an element) out of *group*."""
    parameter = group.parameters_all_dict.get(str(name))
    if parameter is None:
        return False
    if getattr(parameter, "is_linked", False):
        parameter.link = None
    group.parameters_all.remove(parameter)
    _bump(group)
    return True


def set_vector(group, name: str, values: Sequence[float], populations: Sequence[str],
               uncertainties: Optional[Sequence[float]] = None,
               default: Optional[float] = None, column: Optional[str] = None,
               probabilities: Optional[Mapping[str, str]] = None,
               codes: Optional[Mapping[str, float]] = None) -> List[Any]:
    """Make *name* a vector with one element per population (see the module).

    Existing elements keep their fixed flag, bounds and link, and only their
    value changes; elements of populations no longer listed are removed. The
    global ``name`` is kept (or created: *default*, else the old scalar value,
    else the mean). Returns the element parameters, in order.
    """
    from .vector_constants import DEFAULT_COLUMN, PopulationAxis, element_name

    name = str(name)
    labels = [str(l) for l in populations]
    values = [float(v) for v in values]
    if len(labels) != len(values) or len(set(labels)) != len(labels) or not labels:
        raise ValueError("a vector needs one value per distinct population")
    params = group.parameters_all_dict
    if default is None and name not in params:
        default = sum(values) / len(values)
    if name in params:
        if default is not None:
            params[name].value = float(default)
    else:
        _append(group, name, float(default))
    for label in vector_labels(group, name):
        if label not in labels:
            remove_parameter(group, element_name(name, label))
    params = group.parameters_all_dict
    out = []
    for label, value in zip(labels, values):
        parameter = params.get(element_name(name, label))
        if parameter is None:
            parameter = _append(group, element_name(name, label), value,
                                fixed=params[name].fixed)
        elif not getattr(parameter, "is_linked", False):
            parameter.value = value
        out.append(parameter)
    old = _vector_meta(group).get(name, {})
    axis = PopulationAxis.from_dict(old)
    if column is not None:
        axis.column = str(column) or DEFAULT_COLUMN
    if probabilities is not None:
        axis.probabilities = {str(k): str(v) for k, v in probabilities.items()}
    if codes is not None:
        axis.codes = {str(k): float(v) for k, v in codes.items()}
    entry = {"populations": labels, **axis.to_dict()}
    if uncertainties is not None:
        entry["uncertainties"] = {l: float(u) for l, u in zip(labels, uncertainties)
                                  if u is not None}
        for parameter, u in zip(out, uncertainties):
            if u is not None:
                parameter.error_estimate = float(u)
    _vector_meta(group)[name] = entry
    _bump(group)
    return out


def to_vector(group, name: str, populations: Sequence[str],
              column: Optional[str] = None) -> List[Any]:
    """A scalar becomes a vector: every element starts at the scalar's value."""
    parameter = group.parameters_all_dict[str(name)]
    value = float(parameter.value)
    return set_vector(group, name, [value] * len(populations), populations,
                      default=value, column=column)


def to_scalar(group, name: str) -> None:
    """A vector becomes its global value again: the elements are removed."""
    from .vector_constants import element_name

    for label in vector_labels(group, name):
        remove_parameter(group, element_name(name, label))
    _vector_meta(group).pop(str(name), None)


def group_vectors(group) -> Dict[str, Any]:
    """``{name: PopulationVector}``: what the equation engine evaluates per burst."""
    from .vector_constants import vectors_from_values

    names = vector_names(group)
    if not names:
        return {}
    values = {p.name: float(p.value) for p in group.parameters_all}
    meta = _vector_meta(group)
    return vectors_from_values(values, axes=meta,
                               order={n: vector_labels(group, n) for n in names})


def vectors_state(group) -> Dict[str, dict]:
    """The ``"vectors"`` entry of a saved group: order, axis, uncertainties."""
    meta = _vector_meta(group)
    out = {}
    for name in vector_names(group):
        entry = dict(meta.get(name, {}))
        entry["populations"] = vector_labels(group, name)
        entry.setdefault("column", vector_axis(group, name).column)
        out[name] = entry
    return out


# ------------------------------------------------------------- serialization
def group_state(group: FittingParameterGroup) -> Dict[str, Any]:
    """Rich per-parameter state (value + bounds + fixed) — see group.get_state().

    A group with vector constants adds ``"vectors"``: per vector its
    populations in order and its axis (:func:`vectors_state`).
    """
    state = group.get_state()
    vectors = vectors_state(group)
    if vectors:
        state[VECTORS_KEY] = vectors
    return state


def apply_group_state(group: FittingParameterGroup, state: Mapping[str, Any]) -> None:
    """Restore value/bounds/fixed from a :func:`group_state` payload.

    Applies per parameter rather than via ``group.set_state`` — the group-level
    method re-runs ``find_parameters()``, which rebuilds the parameter list from
    object *attributes* and so wipes a group populated with ``append_parameter``.
    """
    params = group.parameters_all_dict
    for name, pstate in dict(state).get("parameters", {}).items():
        target = params.get(str(name))
        if target is not None:
            target.set_state(dict(pstate))
    vectors = dict(state).get(VECTORS_KEY)
    if isinstance(vectors, Mapping):
        for name, entry in vectors.items():
            if isinstance(entry, Mapping):
                _vector_meta(group)[str(name)] = json_copy(entry)


def json_copy(value):
    import json

    return json.loads(json.dumps(value))


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
) -> FittingParameterGroup:
    """Build a group from parsed JSON in *either* the flat or nested format.

    Nested payloads additionally restore bounds/fixed via ``set_state``.
    """
    group = build_constants_group(values_from_data(data), name=name)
    if is_state_format(data):
        apply_group_state(group, data)
    return group


# --------------------------------------------------------------- live mapping
class ConstantsMapping(collections.abc.Mapping):
    """Live ``name -> float`` view over a :class:`FittingParameterGroup`.

    ``__getitem__`` returns the parameter's numeric ``value`` (a plain ``float``,
    never the :class:`FittingParameter` — the value flows straight into NumPy
    arithmetic in the equation engine), so a *linked* constant reads its master's
    current value. Used as ``self.constants`` in Phase 2; exercised by tests now.
    """

    def __init__(self, group: FittingParameterGroup):
        self._group = group

    @property
    def group(self) -> FittingParameterGroup:
        return self._group

    def __getitem__(self, key: str) -> float:
        return float(self._group.parameters_all_dict[key].value)

    def __iter__(self) -> Iterator[str]:
        return iter(p.name for p in self._group.parameters_all)

    def __len__(self) -> int:
        return len(self._group.parameters_all)

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
]
