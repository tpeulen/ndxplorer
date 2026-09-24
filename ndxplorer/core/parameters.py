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

**Vectors.** Any parameter can hold **one value per population**
(:meth:`Parameter.set_vector`): it then has *elements*, each an ordinary
:class:`Parameter` named ``base[label]`` with its own value, fixed flag,
bounds and link, while the parameter's own value is the **global / default**
one -- what a consumer that does not know about populations reads, and what a
burst in no population gets. The elements belong to their parameter, not to
the group, so a group's layout (six parameters per Gaussian) never shifts;
:attr:`ParameterGroup.parameters_flat` lists them in, and names find them
(``group.get("gamma[HF]")``). How a burst picks its element (the axis) and the
populations' order travel in the vector's :meth:`Parameter.vector_state`; see
:mod:`ndxplorer.core.vector_constants` for the per-burst evaluation.

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
    "VECTORS_KEY",
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
        #: The group holding this parameter (told when its elements change).
        self._group: Optional["ParameterGroup"] = None
        #: A vector's elements, one per population, in order (empty: a scalar).
        self._elements: List["Parameter"] = []
        #: A vector's axis and uncertainties (see :meth:`vector_state`).
        self._vector: Dict[str, Any] = {}
        #: An element's vector and population label.
        self._parent: Optional["Parameter"] = None
        self._label = ""
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
        """The name; an element's is its vector's with its label, ``gamma[HF]``."""
        if self._parent is not None:
            return f"{self._parent.name}[{self._label}]"
        return self._name

    @name.setter
    def name(self, value: str) -> None:
        if self._parent is not None:
            raise AttributeError(f"{self.name} is named by its vector and population")
        self._name = str(value)
        self._push("name")
        for element in self._elements:
            element._push("name")

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

    # -- vectors -------------------------------------------------------------
    @property
    def is_vector(self) -> bool:
        """Whether this parameter holds one value per population."""
        return bool(self._elements)

    @property
    def elements(self) -> List["Parameter"]:
        """A vector's elements, in the populations' order (``[]`` for a scalar)."""
        return list(self._elements)

    @property
    def populations(self) -> List[str]:
        return [e._label for e in self._elements]

    @property
    def parent(self) -> Optional["Parameter"]:
        """The vector an element belongs to (``None`` for any other parameter)."""
        return self._parent

    @property
    def label(self) -> str:
        """An element's population label (``""`` for any other parameter)."""
        return self._label

    def element(self, label: str) -> Optional["Parameter"]:
        return next((e for e in self._elements if e._label == str(label)), None)

    def flat(self) -> List["Parameter"]:
        """This parameter, then its elements."""
        return [self] + list(self._elements)

    def set_vector(self, values: Sequence[float], populations: Sequence[str],
                   uncertainties: Optional[Sequence[Optional[float]]] = None,
                   default: Optional[float] = None, column: Optional[str] = None,
                   probabilities: Optional[Dict[str, str]] = None,
                   codes: Optional[Dict[str, float]] = None) -> List["Parameter"]:
        """Hold one value per population (see :mod:`ndxplorer.core.vector_constants`).

        An element that exists keeps its fixed flag, bounds and link, and only
        its value changes (not while linked); a new one starts with this
        parameter's fixed flag and bounds; the elements of populations no longer
        listed are removed. *default*, when given, becomes this parameter's own
        (global) value. *column*, *probabilities* and *codes* set the axis a
        burst picks its element by; left out, they keep what they were.
        Returns the elements, in order.
        """
        from .vector_constants import PopulationAxis

        if self._parent is not None:
            raise ValueError(f"{self.name} is an element; it cannot be a vector")
        labels = [str(l) for l in populations]
        values = [float(v) for v in values]
        if len(labels) != len(values) or len(set(labels)) != len(labels) or not labels:
            raise ValueError("a vector needs one value per distinct population")
        if any("[" in l or "]" in l for l in labels):
            raise ValueError("a population label cannot hold [ or ]")
        if default is not None:
            self.value = float(default)
        gone = [e for e in self._elements if e._label not in labels]
        kept = {e._label: e for e in self._elements if e._label in labels}
        out = []
        for label, value in zip(labels, values):
            element = kept.get(label)
            if element is None:
                element = Parameter("", value, fixed=self.fixed, lb=self.lb, ub=self.ub,
                                    bounds_on=self.bounds_on)
                element._parent, element._label = self, label
            elif element._link is None:
                element.value = value
            out.append(element)
        self._elements = out
        if gone:
            break_links(gone, also=[self._group] if self._group is not None else ())
        axis = PopulationAxis.from_dict(self._vector)
        if column is not None:
            axis.column = str(column) or axis.column
        if probabilities is not None:
            axis.probabilities = {str(k): str(v) for k, v in probabilities.items()}
        if codes is not None:
            axis.codes = {str(k): float(v) for k, v in codes.items()}
        errors = {l: u for l, u in dict(self._vector.get("uncertainties") or {}).items()
                  if l in labels}
        if uncertainties is not None:
            errors = {l: float(u) for l, u in zip(labels, uncertainties) if u is not None}
            for element, u in zip(out, uncertainties):
                if u is not None:
                    element.error_estimate = float(u)
        self._vector = axis.to_dict()
        if errors:
            self._vector["uncertainties"] = errors
        self._structure_changed()
        return out

    def set_populations(self, populations: Sequence[str],
                        column: Optional[str] = None) -> List["Parameter"]:
        """*Make vector…* / *Populations…*: hold one value for each of *populations*.

        A population the vector already has keeps its element; a new one starts
        at the global value. What every table's vector menu calls (the emtk
        :class:`~ndxplorer.app.parameter_table.ParameterTable`, ChiSurf's Qt
        table through :mod:`ndxplorer.core.chisurf_binding`).
        """
        default = float(self.value)
        values = [float(self.element(l).value) if self.element(l) is not None else default
                  for l in populations]
        return self.set_vector(values, list(populations), column=column)

    def to_vector(self, populations: Sequence[str],
                  column: Optional[str] = None) -> List["Parameter"]:
        """A scalar becomes a vector: every element starts at its value."""
        value = float(self.value)
        return self.set_vector([value] * len(populations), populations, column=column)

    def to_scalar(self) -> None:
        """A vector becomes its global value again: the elements are removed."""
        gone, self._elements, self._vector = self._elements, [], {}
        if gone:
            break_links(gone, also=[self._group] if self._group is not None else ())
            self._structure_changed()

    def vector_state(self) -> Dict[str, Any]:
        """``{"populations", "column", ...}``: what names cannot say about a vector."""
        if not self._elements:
            return {}
        return {"populations": self.populations, **self._vector}

    def set_vector_state(self, state: Dict[str, Any]) -> None:
        """Take a vector's axis and uncertainties from :meth:`vector_state`'s output."""
        state = dict(state or {})
        state.pop("populations", None)
        self._vector = json_copy(state)

    def uncertainty(self) -> Optional[float]:
        """An element's uncertainty as its vector stores it (``None``: none)."""
        if self._parent is None:
            return None
        value = dict(self._parent._vector.get("uncertainties") or {}).get(self._label)
        return None if value is None else float(value)

    def population_vector(self):
        """This vector as a :class:`~ndxplorer.core.vector_constants.PopulationVector`."""
        import numpy as np

        from .vector_constants import PopulationAxis, PopulationVector

        return PopulationVector(self.name, self.populations,
                                np.array([float(e.value) for e in self._elements]),
                                float(self.value), PopulationAxis.from_dict(self._vector))

    def _structure_changed(self) -> None:
        if self._group is not None:
            self._group.changed()

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
    A vector's elements are not in it -- they belong to their parameter -- but
    :attr:`parameters_flat` and every lookup by name include them.
    """

    def __init__(self, name: str = "", parameters: Sequence[Parameter] = ()) -> None:
        self.name = str(name)
        self._parameters: List[Parameter] = list(parameters)
        for p in self._parameters:
            if p._group is None:    # a view over another group's parameters keeps theirs
                p._group = self
        #: Bumped when parameters (or a vector's elements) are added, removed or reordered.
        self.revision = 0
        self._listeners: List[Callable[["ParameterGroup"], None]] = []

    @property
    def parameters_all(self) -> List[Parameter]:
        return self._parameters

    @property
    def parameters_flat(self) -> List[Parameter]:
        """Every parameter, each vector followed by its elements."""
        return [q for p in self._parameters for q in p.flat()]

    @property
    def parameters_all_dict(self) -> Dict[str, Parameter]:
        """``{name: parameter}``, the vectors' elements (``gamma[HF]``) included."""
        return {p.name: p for p in self.parameters_flat}

    def __len__(self) -> int:
        return len(self._parameters)

    def __iter__(self) -> Iterator[Parameter]:
        return iter(self._parameters)

    def get(self, name: str) -> Optional[Parameter]:
        """The parameter, or vector element, called *name*."""
        name = str(name)
        return next((p for p in self.parameters_flat if p.name == name), None)

    def append_parameter(self, parameter: Parameter) -> Parameter:
        parameter._group = self
        self._parameters.append(parameter)
        self.changed()
        return parameter

    def add(self, name: str, value: float = 1.0, **kwargs: Any) -> Parameter:
        """Append a new parameter; see :class:`Parameter` for the keywords."""
        return self.append_parameter(Parameter(name, value, **kwargs))

    def remove_parameter(self, parameter: Parameter) -> None:
        """Take out a parameter (with its elements), or one element of a vector."""
        parent = parameter.parent
        if parent is not None:
            labels = [l for l in parent.populations if l != parameter.label]
            if not labels:
                parent.to_scalar()
                return
            parent.set_vector([parent.element(l)._value for l in labels], labels)
            return
        self._parameters.remove(parameter)
        break_links(parameter.flat())
        self.changed()

    def replace_parameters(self, parameters: Sequence[Parameter]) -> None:
        """Hold exactly *parameters*, in that order; the dropped ones are unlinked."""
        kept = {id(p) for p in parameters}
        gone = [q for p in self._parameters if id(p) not in kept for q in p.flat()]
        self._parameters[:] = list(parameters)
        for p in self._parameters:
            p._group = self
        if gone:
            break_links(gone, also=[self])
        self.changed()

    # -- vectors ---------------------------------------------------------------
    def vector_names(self) -> List[str]:
        """The names of the parameters holding one value per population."""
        return [p.name for p in self._parameters if p.is_vector]

    def set_vector(self, name: str, values: Sequence[float], populations: Sequence[str],
                   uncertainties: Optional[Sequence[Optional[float]]] = None,
                   default: Optional[float] = None, **axis: Any) -> List[Parameter]:
        """Make parameter *name* a vector (:meth:`Parameter.set_vector`).

        A name the group does not hold yet is added, its value *default* or the
        mean of *values*. ``axis`` takes ``column``, ``probabilities``, ``codes``.
        """
        parameter = next((p for p in self._parameters if p.name == str(name)), None)
        if parameter is None:
            numbers = [float(v) for v in values]
            start = default if default is not None else sum(numbers) / max(len(numbers), 1)
            parameter = self.append_parameter(Parameter(str(name), float(start)))
        return parameter.set_vector(values, populations, uncertainties=uncertainties,
                                    default=default, **axis)

    def vectors_state(self) -> Dict[str, dict]:
        """``{name: Parameter.vector_state()}`` of the group's vectors."""
        return {p.name: p.vector_state() for p in self._parameters if p.is_vector}

    def vectors(self) -> Dict[str, Any]:
        """``{name: PopulationVector}``: what the equation engine evaluates per burst."""
        return {p.name: p.population_vector() for p in self._parameters if p.is_vector}

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
        """``{"parameters": {name: state}}`` (chisurf's group format).

        A vector's elements are saved by name (``gamma[HF]``) beside it, and a
        group with vectors adds ``"vectors"``: per vector its populations in
        order and its axis (:meth:`Parameter.vector_state`).
        """
        state: dict = {"parameters": {p.name: p.get_state() for p in self.parameters_flat}}
        vectors = self.vectors_state()
        if vectors:
            state[VECTORS_KEY] = vectors
        return state

    def set_state(self, state: dict) -> None:
        """Restore :meth:`get_state`: values, bounds, fixed, and the vectors.

        An element name (``gamma[HF]``) of a parameter the group holds makes
        that parameter a vector, the populations in the order ``"vectors"``
        gives, else in the order they come.
        """
        from .vector_constants import vector_bases

        pstates = {str(k): v for k, v in dict(state.get("parameters") or {}).items()
                   if isinstance(v, dict)}
        vectors = dict(state.get(VECTORS_KEY) or {})
        top = {p.name: p for p in self._parameters}
        for base, labels in vector_bases(pstates).items():
            parameter = top.get(base)
            if parameter is None:
                continue
            order = [str(l) for l in dict(vectors.get(base) or {}).get("populations", ())
                     if str(l) in labels]
            order += [l for l in labels if l not in order]
            known = {l: e._value for l, e in zip(parameter.populations, parameter._elements)}
            parameter.set_vector([float(pstates[f"{base}[{l}]"].get("value", known.get(l, 0.0)))
                                  for l in order], order)
        for name, entry in vectors.items():
            parameter = top.get(str(name))
            if parameter is not None and parameter.is_vector and isinstance(entry, dict):
                parameter.set_vector_state(entry)
        params = self.parameters_all_dict
        for name, pstate in pstates.items():
            target = params.get(name)
            if target is not None:
                target.set_state(pstate)

    def __repr__(self) -> str:
        return f"ParameterGroup({self.name!r}, {len(self)} parameters)"


#: The entry of a saved group that holds its vectors' order and axis.
VECTORS_KEY = "vectors"


def json_copy(value: Any) -> Any:
    import json

    return json.loads(json.dumps(value))


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
        break_links(entry[1].parameters_flat)
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
           for p in group.parameters_flat if p is not exclude]
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
        for p in group.parameters_flat:
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
