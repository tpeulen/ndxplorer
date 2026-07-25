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
from typing import Any, Dict, Iterator, Mapping, Optional

# chisurf is imported lazily inside the functions that build parameters, so the
# pure format helpers (is_state_format / values_from_data) — used by the Qt-free,
# chisurf-free CLI and settings loaders — import without a chisurf dependency.

DEFAULT_GROUP_NAME = "ndXplorer constants"


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


# ------------------------------------------------------------- serialization
def group_state(group: FittingParameterGroup) -> Dict[str, Any]:
    """Rich per-parameter state (value + bounds + fixed) — see group.get_state()."""
    return group.get_state()


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
]
