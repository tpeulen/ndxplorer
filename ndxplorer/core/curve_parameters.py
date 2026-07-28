"""Overlay-curve parameters as a chisurf ``FittingParameterGroup``.

An overlay curve (``a*exp(-(x-mu)**2/(2*sig**2))``, a static FRET line, …) has
free parameters that used to be a grid of home-made slider widgets. Wrapping
them in a :class:`FittingParameterGroup` of :class:`FittingParameter` objects
gives them the same editor every other parameter in chisurf and nDXplorer has —
value / fixed / bounds, the wheel, copy-paste, the detail popup — and, because
the group is registered in the parameter-group registry, lets a curve parameter
be **crosslinked** to a fit's parameter: pin a FRET line's ``tau_d0`` to the
donor lifetime of an actual TCSPC fit and the line follows the fit.

Like :mod:`ndxplorer.core.constants_group` this module is deliberately Qt-free,
so the parameter bookkeeping is headless-testable; the widget wiring lives in
``ndxplorer/plotting/curve_overlay.py``.
"""

from __future__ import annotations

from collections import OrderedDict
from typing import Any, Dict, Iterable, Mapping, Optional, Sequence

# chisurf is imported inside the functions so importing this module does not
# require chisurf (nDXplorer runs standalone, with the legacy slider grid).

#: What a parameter that the equation just grew starts out as. The slider grid
#: used the same three numbers, so a freshly typed equation behaves as before.
DEFAULT_VALUE = 1.0
DEFAULT_LB = 0.1
DEFAULT_UB = 10.0

DEFAULT_GROUP_NAME = "Curve"


def build_curve_group(
    names: Sequence[str],
    values: Optional[Mapping[str, float]] = None,
    name: str = DEFAULT_GROUP_NAME,
):
    """Build a group holding one free :class:`FittingParameter` per name.

    Parameters
    ----------
    names : sequence of str
        Parameter names, in the order they should appear.
    values : mapping of str to float, optional
        Starting values; names not present use :data:`DEFAULT_VALUE`.
    name : str, optional
        Group name, shown as the owner label when crosslinking.

    Returns
    -------
    FittingParameterGroup
        A group whose parameters are *free* (unlike the ndX constants, which
        default to fixed): they are what the user drags to shape the curve, and
        what a fit to the marginal histogram is allowed to move.
    """
    from chisurf.core.fitting.parameter import FittingParameterGroup

    group = FittingParameterGroup(name=name)
    # ``parameters_all`` reads ``_parameters``, which only exists after
    # ``find_parameters()`` — appending before that raises.
    group.find_parameters()
    sync_curve_group(group, names, values=values)
    return group


def sync_curve_group(
    group,
    names: Sequence[str],
    values: Optional[Mapping[str, float]] = None,
) -> bool:
    """Make ``group`` hold exactly ``names``, keeping the parameters it already has.

    Editing the equation adds and drops names. The parameters that survive keep
    their value, bounds and — crucially — their **link**, so retyping an
    unrelated part of the equation does not silently unpin a crosslinked
    parameter.

    Parameters
    ----------
    group : FittingParameterGroup
        The group to update in place.
    names : sequence of str
        The parameter names the equation now has.
    values : mapping of str to float, optional
        Starting values for names that are **new** to the group. A parameter the
        group already has keeps its value: adding a term to an equation must not
        reset the ones the user already set.

    Returns
    -------
    bool
        Whether the membership changed (the caller rebuilds the table if so).
    """
    from chisurf.core.fitting.parameter import FittingParameter

    values = dict(values or {})
    existing = {p.name: p for p in group.parameters_all}
    wanted = [str(n) for n in names]
    changed = wanted != [p.name for p in group.parameters_all]
    if not changed:
        return False

    ordered = []
    for key in wanted:
        param = existing.get(key)
        if param is None:
            param = FittingParameter(
                name=key,
                value=float(values.get(key, DEFAULT_VALUE)),
                lb=DEFAULT_LB,
                ub=DEFAULT_UB,
                bounds_on=False,
            )
        ordered.append(param)

    # ``FittingParameterGroup`` has ``append_parameter`` but no removal: the
    # groups it was written for are discovered from model attributes, not edited.
    # Replacing the list in place is the whole of "the equation lost a name".
    group._parameters[:] = ordered
    return True


def curve_values(group) -> "OrderedDict[str, float]":
    """Flat ``{name: value}`` snapshot, following crosslinks.

    Reading ``param.value`` on a linked parameter returns its master's current
    value, so the curve is drawn against whatever the fit says right now.
    """
    return OrderedDict((p.name, float(p.value)) for p in group.parameters_all)


def apply_curve_values(
    group,
    values: Mapping[str, float],
    ranges: Optional[Mapping[str, Iterable[float]]] = None,
) -> None:
    """Write values (and optional ``[lb, ub]`` ranges) into existing parameters.

    A supplied range **activates** the parameter's bounds. In the slider grid a
    range was a hard limit — the widget could not be dragged past it — and the
    predefined-curve definitions were written against that: a width's range
    starts at zero because a negative width is meaningless. Storing the range
    without arming it would let a fit walk a Gaussian to ``sig = -0.08``, which
    draws the identical curve and reads as nonsense. The user can still switch
    the bounds off in the table.

    Names the group does not have are ignored — the equation decides which
    parameters exist, not the payload.
    """
    params = {p.name: p for p in group.parameters_all}
    for key, value in dict(values).items():
        param = params.get(str(key))
        if param is not None:
            param.value = float(value)
    for key, bounds in dict(ranges or {}).items():
        param = params.get(str(key))
        if param is None:
            continue
        pair = list(bounds)
        if len(pair) == 2:
            param.lb, param.ub = float(pair[0]), float(pair[1])
            param.bounds_on = True


def group_state(group) -> Dict[str, Any]:
    """Per-parameter state (value + bounds + fixed) for saving a session."""
    return group.get_state()


__all__ = [
    "DEFAULT_VALUE",
    "DEFAULT_LB",
    "DEFAULT_UB",
    "DEFAULT_GROUP_NAME",
    "build_curve_group",
    "sync_curve_group",
    "curve_values",
    "apply_curve_values",
    "group_state",
]
