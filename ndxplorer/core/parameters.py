"""nDXplorer's parameters: its own model, with or without chisurf.

A :class:`Parameter` is a named number with what a fit needs to know about it:
whether it is **fixed**, its bounds **lb**/**ub** (enforced while **bounds_on**)
and an optional **link** to another parameter whose value it then follows. A
:class:`ParameterGroup` is an ordered list of them. The constants, the overlay
curves and the Gaussians are all groups of this kind, and the parameter tables
of the app show and edit them the same way (:mod:`ndxplorer.app.parameter_table`).

This is the single source of truth. It is pure Python (numpy is not even
needed), so every feature built on it works without chisurf and without IMP.bff.
When chisurf *is* importable, :mod:`ndxplorer.core.chisurf_binding` publishes a
group as chisurf ``FittingParameter``\\ s -- the Global View, links to and from
a ChiSurf fit -- and keeps that mirror in step with these objects; it is an
optional layer on top, never a requirement.

**Links.** A link target is anything with a ``value``: another parameter of
nDXplorer, or a ChiSurf fit's parameter. A linked parameter reads its master's
value; the fits hold it (:func:`is_held`) and never write it back.

**Registry.** :func:`register_group` names a group as something other
parameters may link to (``owner_id`` -> ``(label, group)``);
:func:`link_targets` lists what a parameter can follow, ChiSurf's own groups
included when the binding is there.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, Iterator, List, Optional, Sequence, Tuple

__all__ = [
    "Parameter",
    "ParameterGroup",
    "is_held",
    "register_group",
    "unregister_group",
    "registered_groups",
    "link_targets",
    "break_links",
    "find",
]

INF = float("inf")


class Parameter:
    """One named value: fixed flag, bounds and an optional link.

    Parameters
    ----------
    name : str
    value : float
    fixed : bool
        Held by a fit.
    lb, ub : float
        Lower and upper bound; ``-inf``/``inf`` where there is none.
    bounds_on : bool
        Whether the bounds are enforced: a value read is clipped into them.
    label_text : str
        What a table shows instead of the name (may hold ``<sub>`` markup).
    """

    def __init__(self, name: str, value: float = 1.0, fixed: bool = False,
                 lb: float = -INF, ub: float = INF, bounds_on: bool = False,
                 label_text: str = "", link: Any = None) -> None:
        self._name = str(name)
        self._value = float(value)
        self._fixed = bool(fixed)
        self._lb = -INF if lb is None else float(lb)
        self._ub = INF if ub is None else float(ub)
        self._bounds_on = bool(bounds_on)
        self.label_text = str(label_text or "")
        self.error_estimate: Optional[float] = None
        self._link: Any = None
        #: The chisurf mirror (:mod:`ndxplorer.core.chisurf_binding`), when published.
        self._mirror: Any = None
        if link is not None:
            self.link = link

    # -- the mirror ---------------------------------------------------------
    def _pull(self) -> None:
        mirror = self._mirror
        if mirror is not None:
            mirror.pull(self)

    def _push(self, what: str) -> None:
        mirror = self._mirror
        if mirror is not None:
            mirror.push(self, what)

    # -- attributes ----------------------------------------------------------
    @property
    def name(self) -> str:
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        self._name = str(value)
        self._push("name")

    @property
    def value(self) -> float:
        """The value: the master's while linked, clipped into enforced bounds."""
        self._pull()
        if self._link is not None:
            return float(self._link.value)
        value = self._value
        if self._bounds_on:
            value = min(max(value, self._lb), self._ub)
        return value

    @value.setter
    def value(self, value: float) -> None:
        self._pull()
        self._value = float(value)
        self._push("value")

    @property
    def fixed(self) -> bool:
        self._pull()
        return self._fixed

    @fixed.setter
    def fixed(self, value: bool) -> None:
        self._pull()
        self._fixed = bool(value)
        self._push("fixed")

    @property
    def lb(self) -> float:
        self._pull()
        return self._lb

    @lb.setter
    def lb(self, value: float) -> None:
        self._pull()
        self._lb = -INF if value is None else float(value)
        self._push("bounds")

    @property
    def ub(self) -> float:
        self._pull()
        return self._ub

    @ub.setter
    def ub(self, value: float) -> None:
        self._pull()
        self._ub = INF if value is None else float(value)
        self._push("bounds")

    @property
    def bounds_on(self) -> bool:
        self._pull()
        return self._bounds_on

    @bounds_on.setter
    def bounds_on(self, value: bool) -> None:
        self._pull()
        self._bounds_on = bool(value)
        self._push("bounds")

    @property
    def raw(self) -> tuple:
        """``(value, fixed, lb, ub, bounds_on)`` as stored (no link, no clipping)."""
        return self._value, self._fixed, self._lb, self._ub, self._bounds_on

    def adopt(self, value: float, fixed: bool, lb: float, ub: float, bounds_on: bool) -> None:
        """Take the stored attributes from outside (the mirror), pushing nothing back."""
        self._value, self._fixed = float(value), bool(fixed)
        self._lb, self._ub, self._bounds_on = float(lb), float(ub), bool(bounds_on)

    # -- links ---------------------------------------------------------------
    @property
    def link(self) -> Any:
        """The parameter this one follows, or ``None``."""
        self._pull()
        return self._link

    @link.setter
    def link(self, target: Any) -> None:
        if target is self:
            raise ValueError(f"{self.name} cannot follow itself.")
        seen, node = set(), target
        while node is not None and id(node) not in seen:
            if node is self:
                raise ValueError(f"Linking {self.name} would make a cycle.")
            seen.add(id(node))
            node = getattr(node, "link", None)
        if target is not None and not hasattr(target, "value"):
            raise TypeError(f"{self.name} can only follow something with a value.")
        self._pull()
        self._link = target
        self._push("link")

    def set_link_quietly(self, target: Any) -> None:
        """Set the link from outside (the mirror), pushing nothing back."""
        self._link = target

    @property
    def is_linked(self) -> bool:
        return self.link is not None

    # -- state ---------------------------------------------------------------
    def get_state(self) -> dict:
        """``value``, ``bounds_on``, ``bounds`` and ``fixed`` (chisurf's format)."""
        return {"value": float(self.value), "bounds_on": bool(self.bounds_on),
                "bounds": [float(self.lb), float(self.ub)], "fixed": bool(self.fixed)}

    def set_state(self, state: dict) -> None:
        bounds = state.get("bounds")
        if isinstance(bounds, (list, tuple)) and len(bounds) == 2:
            self.lb = -INF if bounds[0] is None else float(bounds[0])
            self.ub = INF if bounds[1] is None else float(bounds[1])
        if "bounds_on" in state:
            self.bounds_on = bool(state["bounds_on"])
        if "fixed" in state:
            self.fixed = bool(state["fixed"])
        if "value" in state:
            self.value = float(state["value"])

    def __float__(self) -> float:
        return float(self.value)

    def __repr__(self) -> str:
        return f"Parameter({self.name!r}, {self.value!r}, fixed={self.fixed})"


class ParameterGroup:
    """An ordered, named list of :class:`Parameter`.

    ``parameters_all`` is the live list; change it through the methods so the
    group's :attr:`revision` moves and a listener (the chisurf mirror) follows.
    """

    def __init__(self, name: str = "", parameters: Sequence[Parameter] = ()) -> None:
        self.name = str(name)
        self._parameters: List[Parameter] = list(parameters)
        #: Bumped when parameters are added, removed or reordered.
        self.revision = 0
        self._listeners: List[Callable[["ParameterGroup"], None]] = []

    @property
    def parameters_all(self) -> List[Parameter]:
        return self._parameters

    @property
    def parameters_all_dict(self) -> Dict[str, Parameter]:
        return {p.name: p for p in self._parameters}

    def __len__(self) -> int:
        return len(self._parameters)

    def __iter__(self) -> Iterator[Parameter]:
        return iter(self._parameters)

    def get(self, name: str) -> Optional[Parameter]:
        return next((p for p in self._parameters if p.name == name), None)

    def append_parameter(self, parameter: Parameter) -> Parameter:
        self._parameters.append(parameter)
        self.changed()
        return parameter

    def add(self, name: str, value: float = 1.0, **kwargs: Any) -> Parameter:
        """Append a new parameter; see :class:`Parameter` for the keywords."""
        return self.append_parameter(Parameter(name, value, **kwargs))

    def remove_parameter(self, parameter: Parameter) -> None:
        self._parameters.remove(parameter)
        break_links([parameter])
        self.changed()

    def replace_parameters(self, parameters: Sequence[Parameter]) -> None:
        """Hold exactly *parameters*, in that order; the dropped ones are unlinked."""
        kept = {id(p) for p in parameters}
        gone = [p for p in self._parameters if id(p) not in kept]
        self._parameters[:] = list(parameters)
        if gone:
            break_links(gone, also=[self])
        self.changed()

    # -- listeners -------------------------------------------------------------
    def changed(self) -> None:
        """The membership changed: bump :attr:`revision` and tell the listeners."""
        self.revision += 1
        for listener in list(self._listeners):
            listener(self)

    def listen(self, callback: Callable[["ParameterGroup"], None]) -> None:
        if callback not in self._listeners:
            self._listeners.append(callback)

    def unlisten(self, callback: Callable[["ParameterGroup"], None]) -> None:
        if callback in self._listeners:
            self._listeners.remove(callback)

    # -- state -------------------------------------------------------------------
    def get_state(self) -> dict:
        """``{"parameters": {name: state}}`` (chisurf's group format)."""
        return {"parameters": {p.name: p.get_state() for p in self._parameters}}

    def set_state(self, state: dict) -> None:
        params = self.parameters_all_dict
        for name, pstate in dict(state.get("parameters") or {}).items():
            target = params.get(str(name))
            if target is not None and isinstance(pstate, dict):
                target.set_state(pstate)

    def __repr__(self) -> str:
        return f"ParameterGroup({self.name!r}, {len(self)} parameters)"


def is_held(parameter: Any) -> bool:
    """Whether a fit must leave *parameter* alone: it is fixed **or** linked."""
    return bool(getattr(parameter, "fixed", False)) or bool(getattr(parameter, "is_linked", False))


# ------------------------------------------------------------------ registry
#: owner_id -> (label, group): the groups other parameters may link to.
_GROUPS: Dict[str, Tuple[str, ParameterGroup]] = {}


def register_group(group: ParameterGroup, owner_id: str, label: str) -> None:
    """Offer *group* for linking (again, replacing *owner_id*'s group).

    With chisurf present the group is also published to ChiSurf (Global View,
    links from a fit); without it this is all there is.
    """
    _GROUPS[str(owner_id)] = (str(label), group)
    from . import chisurf_binding

    chisurf_binding.publish(group, str(owner_id), str(label))


def unregister_group(owner_id: str) -> None:
    entry = _GROUPS.pop(str(owner_id), None)
    if entry is not None:
        break_links(list(entry[1].parameters_all))
    from . import chisurf_binding

    chisurf_binding.withdraw(str(owner_id))


def registered_groups() -> List[Tuple[str, str, ParameterGroup]]:
    """``[(owner_id, label, group), ...]`` of nDXplorer's registered groups."""
    return [(owner, label, group) for owner, (label, group) in _GROUPS.items()]


def link_targets(exclude: Any = None) -> List[Tuple[str, str, Any]]:
    """``[(owner label, name, parameter), ...]`` that *exclude* could follow.

    nDXplorer's own groups first, then (with chisurf) the parameter groups
    ChiSurf has registered -- its fits' working models, other plugins.
    """
    out = [(label, p.name, p) for _owner, label, group in registered_groups()
           for p in group.parameters_all if p is not exclude]
    from . import chisurf_binding

    out += [(label, name, p) for label, name, p in chisurf_binding.foreign_targets()
            if p is not exclude]
    return out


def break_links(parameters: Sequence[Any], also: Sequence[ParameterGroup] = ()) -> None:
    """Unlink *parameters*, and every parameter that follows one of them.

    Followers are looked for in the registered groups and in *also*.

    A removed parameter that is still some other table's master would leave that
    follower reading a value nothing updates any more.
    """
    going = {id(p) for p in parameters}
    for p in parameters:
        if isinstance(p, Parameter) and p._link is not None:
            p.link = None
    groups = [group for _owner, _label, group in registered_groups()] + list(also)
    for group in groups:
        for p in group.parameters_all:
            if p._link is not None and id(p._link) in going:
                p.link = None


def find(name: str, groups: Optional[Sequence[ParameterGroup]] = None) -> Optional[Parameter]:
    """The registered parameter called *name* (``"Label: name"`` picks the group)."""
    label, _, bare = str(name).rpartition(":")
    label, bare = label.strip(), bare.strip()
    for owner_label, pname, p in link_targets():
        if pname == bare and (not label or label == owner_label):
            return p
    return None
