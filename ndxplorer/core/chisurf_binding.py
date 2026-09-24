"""Publish nDXplorer's parameters to ChiSurf, when ChiSurf is there.

nDXplorer's :class:`~ndxplorer.core.parameters.ParameterGroup` is the one
source of truth. With chisurf (and IMP.bff) importable, a group registered with
:func:`ndxplorer.core.parameters.register_group` is **mirrored** here as a
chisurf ``FittingParameterGroup`` of ``FittingParameter``\\ s and put in
ChiSurf's parameter-group registry. That gives it what only ChiSurf has: the
Global View, and links *from* a ChiSurf fit to an nDXplorer parameter.

The mirror follows the model both ways, parameter by parameter:

* an nDXplorer write (value, fixed, bounds, link, name) is pushed to its
  ``FittingParameter`` at once;
* an nDXplorer read first compares the ``FittingParameter`` with what was last
  pushed; a difference was made on ChiSurf's side (edited in the Global View,
  linked there) and is taken over.

Without chisurf every function here is a no-op, and nothing else notices.
The Qt window's ChiSurf widgets are handed the mirror (:func:`chisurf_group`).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

__all__ = ["available", "why_unavailable", "publish", "withdraw", "chisurf_group",
           "foreign_targets", "mirrored", "mirrored_list", "release"]

logger = logging.getLogger(__name__)

_STATE: Dict[str, Any] = {}
#: id(ndx group) -> _Mirror
_MIRRORS: Dict[int, "_Mirror"] = {}
#: owner_id -> _Mirror (strong: ChiSurf's registry holds groups weakly)
_PUBLISHED: Dict[str, "_Mirror"] = {}
#: id(FittingParameter) -> ndx Parameter, for mapping a ChiSurf link back
_BACK: Dict[int, Any] = {}
#: id(_Mirror) of the groups :func:`mirrored_list` made for loose parameters
_LOOSE: set = set()


def available() -> bool:
    """Whether a chisurf ``FittingParameter`` can be made here (checked once)."""
    if "ok" not in _STATE:
        try:
            from chisurf.core.fitting.parameter import FittingParameter

            FittingParameter(name="probe", value=1.0)
            _STATE.update(ok=True, why="")
        except Exception as exc:  # noqa: BLE001 - anything: no binding
            _STATE.update(ok=False, why=str(exc).splitlines()[0][:300] if str(exc) else
                          type(exc).__name__)
            logger.info("ChiSurf binding off: %s", _STATE["why"])
    return bool(_STATE["ok"])


def why_unavailable() -> str:
    """Why :func:`available` is ``False`` (``""`` when it is not)."""
    available()
    return str(_STATE.get("why", ""))


def _bump() -> None:
    try:
        from chisurf.core.fitting import factorgraph

        factorgraph.bump_structure_version()
    except Exception:  # noqa: BLE001 - nothing cached
        pass


class _Mirror:
    """One group's ``FittingParameterGroup``, kept in step with the group."""

    def __init__(self, group) -> None:
        from chisurf.core.fitting.parameter import FittingParameterGroup

        self.group = group
        self.cs_group = FittingParameterGroup(name=group.name)
        self.cs_group.find_parameters()
        self.pairs: Dict[int, Any] = {}
        self.seen: Dict[int, tuple] = {}
        self._busy = False
        group.listen(self.rebuild)
        self.rebuild(group)

    # -- structure -----------------------------------------------------------
    def rebuild(self, group) -> None:
        from chisurf.core.fitting.parameter import FittingParameter

        wanted = []
        alive = set()
        # A vector's elements are published as scalars of their own, ``name[pop]``
        # after ``name``: each keeps its fixed flag, bounds and link in ChiSurf.
        for p in group.parameters_flat:
            cs = self.pairs.get(id(p))
            if cs is None:
                value, fixed, lb, ub, bounds_on = p.raw
                cs = FittingParameter(name=p.name, value=value, fixed=fixed, lb=lb, ub=ub,
                                      bounds_on=bounds_on)
                self.pairs[id(p)] = cs
                _BACK[id(cs)] = p
                p._mirror = self
                self.seen[id(p)] = self._read(cs)
            alive.add(id(p))
            wanted.append((p, cs))
        for key in [k for k in self.pairs if k not in alive]:
            cs = self.pairs.pop(key)
            _BACK.pop(id(cs), None)
            self.seen.pop(key, None)
            try:
                cs.link = None
            except Exception:  # noqa: BLE001
                pass
        self.cs_group.name = group.name
        self.cs_group._parameters[:] = [cs for _p, cs in wanted]
        #: The group's revision this mirror holds (see :func:`chisurf_group`).
        self.revision = group.revision
        for p, _cs in wanted:
            if p._link is not None:
                self.push(p, "link")
        _bump()

    def detach(self) -> None:
        self.group.unlisten(self.rebuild)
        for p in self.group.parameters_flat:
            if p._mirror is self:
                p._mirror = None
        for cs in self.pairs.values():
            _BACK.pop(id(cs), None)
        _MIRRORS.pop(id(self.group), None)

    # -- values --------------------------------------------------------------
    @staticmethod
    def _read(cs) -> tuple:
        link = cs.link if cs.is_linked else None
        value = None if link is not None else float(np.ravel(cs._port.value)[0])
        return (value, bool(cs.fixed), float(cs.lb), float(cs.ub), bool(cs.bounds_on),
                id(link) if link is not None else None)

    def push(self, p, what: str) -> None:
        cs = self.pairs.get(id(p))
        if cs is None or self._busy:
            return
        self._busy = True
        try:
            value, fixed, lb, ub, bounds_on = p.raw
            if what == "value":
                cs.value = value
            elif what == "fixed":
                cs.fixed = fixed
            elif what == "bounds":
                cs.lb, cs.ub = lb, ub
                cs.bounds_on = bounds_on
            elif what == "name":
                cs.name = p.name
            elif what == "link":
                cs.link = self._target(p._link)
        except Exception as exc:  # noqa: BLE001 - the model already has it
            logger.debug("ChiSurf mirror of %s: %s", p.name, exc)
        finally:
            self._busy = False
        self.seen[id(p)] = self._read(cs)

    def pull(self, p) -> None:
        cs = self.pairs.get(id(p))
        if cs is None or self._busy:
            return
        now = self._read(cs)
        before = self.seen.get(id(p))
        if now == before:
            return
        self.seen[id(p)] = now
        value, fixed, lb, ub, bounds_on, link = now
        old = p.raw
        p.adopt(old[0] if value is None else value, fixed, lb, ub, bounds_on)
        if before is None or link != before[5]:
            target = cs.link if link is not None else None
            p.set_link_quietly(_BACK.get(id(target), target) if target is not None else None)

    @staticmethod
    def _target(link) -> Any:
        """The ChiSurf parameter an nDXplorer link stands for (``None``: none)."""
        if link is None:
            return None
        mirror = getattr(link, "_mirror", None)
        if mirror is not None:
            return mirror.pairs.get(id(link))
        return link if hasattr(link, "_port") else None


def _mirror(group) -> Optional[_Mirror]:
    if not available():
        return None
    mirror = _MIRRORS.get(id(group))
    if mirror is None or mirror.group is not group:
        mirror = _MIRRORS[id(group)] = _Mirror(group)
    return mirror


def publish(group, owner_id: str, label: str) -> bool:
    """Mirror *group* and put it in ChiSurf's registry; ``False`` without chisurf."""
    mirror = _mirror(group)
    if mirror is None:
        return False
    try:
        from chisurf.core.parameter_group_registry import register_parameter_group

        mirror.cs_group.name = label
        register_parameter_group(mirror.cs_group, owner_id=owner_id, label=label)
    except Exception as exc:  # noqa: BLE001 - linking into it is optional
        logger.debug("could not publish %s: %s", owner_id, exc)
        return False
    old = _PUBLISHED.get(owner_id)
    _PUBLISHED[owner_id] = mirror
    if old is not None and old is not mirror and old not in _PUBLISHED.values():
        old.detach()
    return True


def withdraw(owner_id: str) -> None:
    """Take *owner_id*'s group out of ChiSurf's registry."""
    mirror = _PUBLISHED.pop(owner_id, None)
    if mirror is None:
        return
    try:
        from chisurf.core.parameter_group_registry import unregister_parameter_group

        unregister_parameter_group(owner_id)
    except Exception as exc:  # noqa: BLE001
        logger.debug("could not withdraw %s: %s", owner_id, exc)
    if mirror not in _PUBLISHED.values():
        mirror.detach()


def chisurf_group(group):
    """The ``FittingParameterGroup`` mirroring *group* (``None`` without chisurf).

    For ChiSurf's own widgets (the Qt window's parameter tables): what they edit
    is taken over by the model on its next read.
    """
    mirror = _mirror(group)
    if mirror is None:
        return None
    if getattr(mirror, "revision", None) != group.revision:
        # Asked from another listener of the group, before this mirror's own.
        mirror.rebuild(group)
    return mirror.cs_group


def mirrored(parameter) -> Any:
    """The ``FittingParameter`` mirroring an nDXplorer *parameter*, or ``None``."""
    mirror = getattr(parameter, "_mirror", None)
    return mirror.pairs.get(id(parameter)) if mirror is not None else None


def mirrored_list(parameters, name: str = "") -> Optional[List[Any]]:
    """ChiSurf mirrors of *parameters*, for a ChiSurf table (``None`` without chisurf).

    A vector's elements follow it (``name[pop]``), as its group publishes them.
    Parameters no published group holds (a curve fit's own) are mirrored as a
    group of their own, *name*.
    """
    from .parameters import ParameterGroup

    parameters = _flat(parameters)
    loose = [p for p in parameters if mirrored(p) is None]
    if loose:
        mirror = _mirror(ParameterGroup(name, loose))
        if mirror is None:
            return None
        _LOOSE.add(id(mirror))
    return [mirrored(p) for p in parameters]


def _flat(parameters) -> List[Any]:
    """*parameters* with each vector's elements after it, each once."""
    out, seen = [], set()
    for p in parameters:
        for q in (p.flat() if hasattr(p, "flat") else [p]):
            if id(q) not in seen:
                seen.add(id(q))
                out.append(q)
    return out


def release(parameters) -> None:
    """Drop the mirrors :func:`mirrored_list` made for loose *parameters*.

    A table that showed a curve fit's own parameters calls this when it goes
    away; otherwise their ``FittingParameter``\\ s stay in this module for the
    rest of the process. A parameter of a group's mirror (a published group,
    the constants) keeps it: that one belongs to the group, not to the table.
    """
    for p in _flat(parameters):
        mirror = getattr(p, "_mirror", None)
        if mirror is not None and id(mirror) in _LOOSE:
            _LOOSE.discard(id(mirror))
            mirror.detach()


def foreign_targets() -> List[Tuple[str, str, Any]]:
    """``[(label, name, FittingParameter)]`` of ChiSurf's groups that are not ours."""
    if not available():
        return []
    try:
        from chisurf.core.parameter_group_registry import iter_registered_parameter_groups
    except Exception:  # noqa: BLE001
        return []
    ours = {id(m.cs_group) for m in _MIRRORS.values()}
    out = []
    for _owner, label, group in iter_registered_parameter_groups():
        if id(group) in ours:
            continue
        for p in getattr(group, "parameters_all", ()):
            out.append((str(label), str(p.name), p))
    return out
