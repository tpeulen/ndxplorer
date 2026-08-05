"""The fit panel's 2-D Gaussians as a chisurf ``FittingParameterGroup``.

Each Gaussian drawn on the two-dimensional map is six numbers — its centre
``(x, y)``, its widths ``(sd_x, sd_y)``, the correlation ``rho`` between them
and its weight ``w``. They used to live as text in a home-made table, with a
checkbox in the corner of each cell standing in for "hold this one". Wrapping
them in :class:`FittingParameter` objects gives them what every other parameter
in chisurf and nDXplorer has — value / fixed / bounds, the wheel, copy-paste,
the detail popup — and, once the group is published in the parameter-group
registry, lets a Gaussian be **crosslinked**: pin a population's centre to a
parameter of an actual fit, or pin two populations' widths to each other, and
the EM holds them there.

A **linked** parameter is held fixed by the fit and never written back: its
value belongs to the master it follows, so optimising it would either be
discarded or fight the link. That is the same contract
:mod:`ndxplorer.analysis.curve_fit` uses for the overlay curves.

The parameters are laid out **component-major** — ``[x_1, y_1, sd_x_1, sd_y_1,
rho_1, w_1, x_2, …]`` — which is exactly what chisurf's
``PairedParameterTableWidget`` renders one component per row.

This module is deliberately Qt-free so the bookkeeping is headless-testable;
the widget wiring lives in :mod:`ndxplorer.analysis.gaussian_fit`.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass
from typing import Any

import numpy as np

# chisurf is imported inside the functions: nDXplorer installs standalone.

#: One component's parameters, in the order they are stored and shown.
SLOTS: tuple[str, ...] = ("x", "y", "sd_x", "sd_y", "rho", "w")

#: Parameters per component — the paired table's row width.
WIDTH = len(SLOTS)

#: Column titles for the six slots (rich text; the table's header renders it).
SLOT_LABELS: tuple[str, ...] = ("x", "y", "&sigma;<sub>x</sub>", "&sigma;<sub>y</sub>", "&rho;", "w")

#: Per-slot ``(label template, lb, ub, bounds_on)``. Bounds are *armed* where a
#: value outside them is not a worse fit but a meaningless one: a negative width
#: draws the identical ellipse, and a correlation past ±1 is not a covariance at
#: all. ``x``/``y`` live wherever the axes do, so they start unbounded.
_SLOT_SPEC: dict[str, tuple[str, float, float, bool]] = {
    "x": ("x<sub>{i}</sub>", float("-inf"), float("inf"), False),
    "y": ("y<sub>{i}</sub>", float("-inf"), float("inf"), False),
    "sd_x": ("&sigma;<sub>x,{i}</sub>", 0.0, float("inf"), True),
    "sd_y": ("&sigma;<sub>y,{i}</sub>", 0.0, float("inf"), True),
    "rho": ("&rho;<sub>{i}</sub>", -1.0, 1.0, True),
    "w": ("w<sub>{i}</sub>", 0.0, float("inf"), True),
}

DEFAULT_GROUP_NAME = "Gaussians"

#: Smallest eigenvalue a covariance is nudged up to, so a degenerate ellipse
#: still has a Cholesky factor.
_COV_FLOOR = 1e-9


@dataclass
class GaussianComponent:
    """One Gaussian, read out of the group.

    Attributes
    ----------
    mu : ndarray, shape (2,)
        Centre in value space.
    cov : ndarray, shape (2, 2)
        Covariance built from ``sd_x``, ``sd_y`` and ``rho``.
    w : float
        Mixture weight (not normalised here).
    fix_mu : ndarray of bool, shape (2,)
        Which centre coordinates the fit must hold.
    fix_cov : ndarray of bool, shape (2, 2)
        Which covariance elements the fit must hold. ``sd_x`` maps to the
        ``[0, 0]`` element, ``sd_y`` to ``[1, 1]`` and ``rho`` to the two
        off-diagonal ones.
    fix_w : bool
        Whether the weight is held.
    """

    mu: np.ndarray
    cov: np.ndarray
    w: float
    fix_mu: np.ndarray
    fix_cov: np.ndarray
    fix_w: bool


# -- covariance <-> (sd, rho) -------------------------------------------------


def cov_from_sd_rho(sd_x: float, sd_y: float, rho: float) -> np.ndarray:
    """Build a 2×2 covariance from two standard deviations and a correlation."""
    sx = max(0.0, float(sd_x))
    sy = max(0.0, float(sd_y))
    r = float(np.clip(float(rho), -1.0, 1.0))
    off = r * sx * sy
    cov = np.array([[sx * sx, off], [off, sy * sy]], dtype=float)
    return regularized(cov)


def sd_rho_from_cov(cov: Sequence[Sequence[float]]) -> tuple[float, float, float]:
    """Return ``(sd_x, sd_y, rho)`` of a 2×2 covariance."""
    c = np.asarray(cov, dtype=float).reshape(2, 2)
    sd_x = float(np.sqrt(max(float(c[0, 0]), 0.0)))
    sd_y = float(np.sqrt(max(float(c[1, 1]), 0.0)))
    denom = sd_x * sd_y
    rho = float(c[0, 1] / denom) if denom > 0 else 0.0
    return sd_x, sd_y, float(np.clip(rho, -1.0, 1.0))


def regularized(cov: Sequence[Sequence[float]]) -> np.ndarray:
    """Return ``cov`` nudged to positive definiteness if it is not already."""
    c = np.asarray(cov, dtype=float).reshape(2, 2).copy()
    try:
        if np.any(np.linalg.eigvalsh(c) <= 0):
            c = c + _COV_FLOOR * np.eye(2)
    except Exception:
        c = c + _COV_FLOOR * np.eye(2)
    return c


# -- the group ----------------------------------------------------------------


def build_gaussian_group(name: str = DEFAULT_GROUP_NAME):
    """Return an empty group ready to take components.

    Parameters
    ----------
    name : str, optional
        Group name, shown as the owner label when crosslinking.

    Returns
    -------
    FittingParameterGroup
        A group with no parameters; :func:`append_component` fills it.
    """
    from chisurf.core.fitting.parameter import FittingParameterGroup

    group = FittingParameterGroup(name=name)
    # ``parameters_all`` reads ``_parameters``, which only exists once
    # ``find_parameters()`` has run.
    group.find_parameters()
    group._parameters[:] = []
    return group


def component_count(group) -> int:
    """Return the number of Gaussians the group holds."""
    return len(group.parameters_all) // WIDTH


def parameters_of(group, index: int) -> dict[str, Any]:
    """Return ``{slot: FittingParameter}`` of one component."""
    params = group.parameters_all
    start = index * WIDTH
    if index < 0 or start + WIDTH > len(params):
        raise IndexError(f"no Gaussian at index {index}")
    return dict(zip(SLOTS, params[start : start + WIDTH]))


def append_component(
    group,
    mu: Sequence[float],
    cov: Sequence[Sequence[float]],
    w: float = 1.0,
    fixed: Mapping[str, bool] | None = None,
) -> int:
    """Add one Gaussian to the group; return its index.

    Parameters
    ----------
    group : FittingParameterGroup
        The group to extend.
    mu : sequence of float
        Centre ``(x, y)`` in value space.
    cov : array_like, shape (2, 2)
        Covariance; stored as ``sd_x``, ``sd_y`` and ``rho``.
    w : float, optional
        Mixture weight.
    fixed : mapping of str to bool, optional
        Which of the six slots start held.
    """
    from chisurf.core.fitting.parameter import FittingParameter

    index = component_count(group) + 1
    sd_x, sd_y, rho = sd_rho_from_cov(cov)
    values = {
        "x": float(mu[0]),
        "y": float(mu[1]),
        "sd_x": sd_x,
        "sd_y": sd_y,
        "rho": rho,
        "w": float(w),
    }
    held = dict(fixed or {})
    made = []
    for slot in SLOTS:
        label, lb, ub, bounds_on = _SLOT_SPEC[slot]
        made.append(
            FittingParameter(
                name=f"{slot}_{index}",
                value=values[slot],
                lb=lb,
                ub=ub,
                bounds_on=bounds_on,
                fixed=bool(held.get(slot, False)),
                label_text=label.format(i=index),
            )
        )
    group._parameters.extend(made)
    return index - 1


def remove_components(group, indices: Iterable[int]) -> None:
    """Drop the given components and renumber the survivors.

    Renumbering keeps the names the link menu shows in step with the row
    numbers the user sees. A link already made survives it: a link holds the
    master *object*, not its name.
    """
    drop = {int(i) for i in indices}
    params = group.parameters_all
    kept: list[Any] = []
    removed: list[Any] = []
    for c in range(len(params) // WIDTH):
        (kept if c not in drop else removed).extend(params[c * WIDTH : (c + 1) * WIDTH])
    group._parameters[:] = kept
    # After the list is cut, so a *surviving* component that followed a removed
    # one is found as a follower and unlinked too.
    _break_links(removed)
    _renumber(group)


def clear_components(group) -> None:
    """Remove every Gaussian, breaking any links that pointed at them."""
    going = list(group.parameters_all)
    group._parameters[:] = []
    _break_links(going)


def _renumber(group) -> None:
    """Re-derive every parameter's name and label from its component index."""
    params = group.parameters_all
    for c in range(len(params) // WIDTH):
        for slot, param in zip(SLOTS, params[c * WIDTH : (c + 1) * WIDTH]):
            label, _, _, _ = _SLOT_SPEC[slot]
            param.name = f"{slot}_{c + 1}"
            param.__dict__["label_text"] = label.format(i=c + 1)


def _break_links(parameters: Sequence[Any]) -> None:
    """Unlink removed parameters and any follower pointing back at them.

    A removed Gaussian whose parameter is still some other table's master would
    leave that follower reading a value nothing updates any more.
    """
    try:
        from chisurf.core.parameter_group_registry import break_links

        break_links(parameters)
    except Exception:
        for param in parameters:
            try:
                param.link = None
            except Exception:
                continue


# -- reading / writing --------------------------------------------------------


def is_held(param) -> bool:
    """Whether the fit must hold this parameter (fixed **or** linked)."""
    return bool(getattr(param, "fixed", False)) or bool(getattr(param, "is_linked", False))


def read_components(group) -> list[GaussianComponent]:
    """Read every Gaussian out of the group, following crosslinks.

    Reading a linked parameter returns its master's current value, so the
    ellipse drawn is whatever the fit it is pinned to says right now.
    """
    out: list[GaussianComponent] = []
    params = group.parameters_all
    for c in range(len(params) // WIDTH):
        p = dict(zip(SLOTS, params[c * WIDTH : (c + 1) * WIDTH]))
        w = float(p["w"].value)
        if not np.isfinite(w) or w < 0:
            w = 1.0
        cov = cov_from_sd_rho(p["sd_x"].value, p["sd_y"].value, p["rho"].value)
        held_rho = is_held(p["rho"])
        out.append(
            GaussianComponent(
                mu=np.array([float(p["x"].value), float(p["y"].value)], dtype=float),
                cov=cov,
                w=w,
                fix_mu=np.array([is_held(p["x"]), is_held(p["y"])], dtype=bool),
                fix_cov=np.array(
                    [
                        [is_held(p["sd_x"]), held_rho],
                        [held_rho, is_held(p["sd_y"])],
                    ],
                    dtype=bool,
                ),
                fix_w=is_held(p["w"]),
            )
        )
    return out


def write_component(
    group,
    index: int,
    mu: Sequence[float],
    cov: Sequence[Sequence[float]],
    w: float | None = None,
) -> None:
    """Write a fitted component back into the group.

    Linked parameters are skipped — their value is owned by the master they
    follow, so assigning here would be either discarded or a silent unlink.
    """
    p = parameters_of(group, index)
    sd_x, sd_y, rho = sd_rho_from_cov(cov)
    values = {
        "x": float(mu[0]),
        "y": float(mu[1]),
        "sd_x": sd_x,
        "sd_y": sd_y,
        "rho": rho,
    }
    if w is not None:
        values["w"] = float(w)
    for slot, value in values.items():
        param = p[slot]
        if getattr(param, "is_linked", False):
            continue
        try:
            param.value = float(value)
        except (TypeError, ValueError):
            continue


# -- persistence --------------------------------------------------------------

#: The record a Gaussian is saved as. Unchanged from the hand-rolled table, so
#: a file written before the parameters became fitting parameters still loads.
RECORD_FIELDS = (
    "x", "y", "sd_x", "sd_y", "rho", "w",
    "fix_x", "fix_y", "fix_sd_x", "fix_sd_y", "fix_rho",
)


def components_to_records(group) -> list[dict[str, Any]]:
    """Return one flat ``{field: value}`` record per Gaussian, for saving."""
    records = []
    params = group.parameters_all
    for c in range(len(params) // WIDTH):
        p = dict(zip(SLOTS, params[c * WIDTH : (c + 1) * WIDTH]))
        record: dict[str, Any] = {slot: float(p[slot].value) for slot in SLOTS}
        for slot in ("x", "y", "sd_x", "sd_y", "rho"):
            record[f"fix_{slot}"] = bool(is_held(p[slot]))
        records.append(record)
    return records


def apply_records(group, records: Sequence[Mapping[str, Any]]) -> None:
    """Replace the group's Gaussians with the ones in ``records``."""
    clear_components(group)
    for record in records:
        cov = cov_from_sd_rho(
            record.get("sd_x", 0.0), record.get("sd_y", 0.0), record.get("rho", 0.0)
        )
        append_component(
            group,
            (float(record.get("x", 0.0)), float(record.get("y", 0.0))),
            cov,
            float(record.get("w", 1.0)),
            fixed={
                slot: bool(record.get(f"fix_{slot}", False))
                for slot in ("x", "y", "sd_x", "sd_y", "rho")
            },
        )


def group_state(group) -> dict[str, Any]:
    """Per-parameter state (value + bounds + fixed) for saving a session."""
    return group.get_state()


__all__ = [
    "SLOTS",
    "SLOT_LABELS",
    "WIDTH",
    "DEFAULT_GROUP_NAME",
    "RECORD_FIELDS",
    "GaussianComponent",
    "append_component",
    "apply_records",
    "build_gaussian_group",
    "clear_components",
    "component_count",
    "components_to_records",
    "cov_from_sd_rho",
    "group_state",
    "is_held",
    "parameters_of",
    "read_components",
    "regularized",
    "remove_components",
    "sd_rho_from_cov",
    "write_component",
]
