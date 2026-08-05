"""The fit panel's 2-D Gaussians as a chisurf parameter group.

Each Gaussian drawn on the two-dimensional map is six numbers — its centre
``(x, y)``, its widths ``(sd_x, sd_y)``, the correlation ``rho`` between them
and its weight ``w``. They used to live as text in a home-made table, with a
checkbox in the corner of each cell standing in for "hold this one". They are a
``FittingParameterGroup`` of the ordinary kind now, so the panel gets what every
other parameter in chisurf and nDXplorer has — value / fixed / bounds, the
wheel, copy-paste, the detail popup — and, once the group is published in the
parameter-group registry, lets a Gaussian be **crosslinked**: pin a population's
centre to a parameter of an actual fit, or pin two populations' widths to each
other, and the EM holds them there.

A **linked** parameter is held fixed by the fit and never written back: its
value belongs to the master it follows, so optimising it would either be
discarded or fight the link. That is the same contract
:mod:`ndxplorer.analysis.curve_fit` uses for the overlay curves.

The group is a **variable-length list of components** with ``append`` and
``pop``, which is the contract chisurf's ``dynamic_group`` view section is
written against: :class:`GaussianMixtureView` declares one such section
(``style: "table"``, ``row_width: 6``) and ``AutoForm`` renders it exactly like
the lifetime and rotation tables of a model editor — one component per row, with
the same add / remove controls and the same columns. The structural definition
of "what a row is" therefore stays here, in the group, and the panel carries no
table code at all.

Qt-free, so the bookkeeping is headless-testable; the widget wiring lives in
:mod:`ndxplorer.analysis.gaussian_fit`. chisurf is imported lazily throughout,
because nDXplorer also installs standalone.
"""

from __future__ import annotations

import dataclasses
from collections.abc import Mapping, Sequence
from typing import Any

import numpy as np

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

#: The record a Gaussian is saved as. Unchanged from the hand-rolled table, so
#: a file written before the parameters became fitting parameters still loads.
RECORD_FIELDS = (
    "x", "y", "sd_x", "sd_y", "rho", "w",
    "fix_x", "fix_y", "fix_sd_x", "fix_sd_y", "fix_rho",
)


@dataclasses.dataclass
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
    return regularized(np.array([[sx * sx, off], [off, sy * sy]], dtype=float))


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


def is_held(param) -> bool:
    """Return whether the fit must hold this parameter (fixed **or** linked)."""
    return bool(getattr(param, "fixed", False)) or bool(getattr(param, "is_linked", False))


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


# -- the group ----------------------------------------------------------------

_MIXTURE_CLASS: Any = None


def gaussian_mixture_class():
    """Return the mixture group class, defining it on first call.

    The base class lives in chisurf, which this module must not import at
    import time (nDXplorer installs standalone), so the class is built on
    demand and cached — ``isinstance`` against this return value works as
    usual.
    """
    global _MIXTURE_CLASS
    if _MIXTURE_CLASS is not None:
        return _MIXTURE_CLASS

    from chisurf.core.fitting.parameter import FittingParameter, FittingParameterGroup

    class GaussianMixture(FittingParameterGroup):
        """A variable-length list of 2-D Gaussians, six parameters each.

        Implements the ``append`` / ``pop`` contract chisurf's ``dynamic_group``
        section drives, so the table, its add/remove buttons and its column
        layout are the shared renderer's rather than the panel's.
        """

        def __init__(self, name: str = DEFAULT_GROUP_NAME, **kwargs):
            super().__init__(name=name, **kwargs)
            # ``parameters_all`` reads ``_parameters``, which only exists once
            # ``find_parameters()`` has run.
            self.find_parameters()
            self._parameters[:] = []
            #: ``() -> (mu, cov)`` for a Gaussian added with no coordinates —
            #: the shared "add" button calls ``append()`` with none. A unit
            #: Gaussian at the origin is off the map for axes that run 0 to 1,
            #: so the host, which knows what is displayed, supplies this.
            self.default_component = None

        def _default(self) -> tuple:
            """Centre and covariance for a Gaussian the caller did not place."""
            if callable(self.default_component):
                try:
                    mu, cov = self.default_component()
                    return np.asarray(mu, dtype=float), np.asarray(cov, dtype=float)
                except Exception:
                    pass
            return np.zeros(2), np.eye(2)

        # -- structure ------------------------------------------------------
        def rows(self) -> list:
            """Return the parameters making up the rows (the section's ``rows_source``)."""
            return list(self.parameters_all)

        def __len__(self) -> int:
            """Return the number of Gaussians the group holds."""
            return len(self.parameters_all) // WIDTH

        def parameters_of(self, index: int) -> dict:
            """Return ``{slot: FittingParameter}`` of one component."""
            params = self.parameters_all
            start = index * WIDTH
            if index < 0 or start + WIDTH > len(params):
                raise IndexError(f"no Gaussian at index {index}")
            return dict(zip(SLOTS, params[start : start + WIDTH]))

        def append(
            self,
            mu: Sequence[float] | None = None,
            cov: Sequence[Sequence[float]] | None = None,
            w: float = 1.0,
            fixed: Mapping[str, bool] | None = None,
        ) -> int:
            """Add one Gaussian; return its index.

            Parameters
            ----------
            mu : sequence of float, optional
                Centre ``(x, y)`` in value space. Defaults to whatever
                :attr:`default_component` says — the shared "add" button calls
                this with no arguments.
            cov : array_like, shape (2, 2), optional
                Covariance; stored as ``sd_x``, ``sd_y`` and ``rho``.
            w : float, optional
                Mixture weight.
            fixed : mapping of str to bool, optional
                Which of the six slots start held.
            """
            if mu is None or cov is None:
                default_mu, default_cov = self._default()
                mu = default_mu if mu is None else mu
                cov = default_cov if cov is None else cov
            index = len(self) + 1
            sd_x, sd_y, rho = sd_rho_from_cov(cov)
            values = {
                "x": float(mu[0]), "y": float(mu[1]),
                "sd_x": sd_x, "sd_y": sd_y, "rho": rho, "w": float(w),
            }
            held = dict(fixed or {})
            for slot in SLOTS:
                label, lb, ub, bounds_on = _SLOT_SPEC[slot]
                self._parameters.append(
                    FittingParameter(
                        name=f"{slot}_{index}",
                        value=values[slot],
                        lb=lb, ub=ub, bounds_on=bounds_on,
                        fixed=bool(held.get(slot, False)),
                        label_text=label.format(i=index),
                    )
                )
            return index - 1

        def pop(self, index: int | None = None) -> None:
            """Remove one Gaussian — the given one, or the last — and renumber.

            Renumbering keeps the names the link menu shows in step with the row
            numbers the user sees. A link already made survives it: a link holds
            the master *object*, not its name.
            """
            if len(self) == 0:
                return
            index = len(self) - 1 if index is None else int(index)
            if not 0 <= index < len(self):
                return
            removed = list(self._parameters[index * WIDTH : (index + 1) * WIDTH])
            del self._parameters[index * WIDTH : (index + 1) * WIDTH]
            # After the list is cut, so a *surviving* component that followed a
            # removed one is found as a follower and unlinked too.
            _break_links(removed)
            self._renumber()

        def clear(self) -> None:
            """Remove every Gaussian, breaking any links that pointed at them."""
            going = list(self.parameters_all)
            self._parameters[:] = []
            _break_links(going)

        def _renumber(self) -> None:
            """Re-derive every parameter's name and label from its component index."""
            params = self.parameters_all
            for c in range(len(params) // WIDTH):
                for slot, param in zip(SLOTS, params[c * WIDTH : (c + 1) * WIDTH]):
                    label, _, _, _ = _SLOT_SPEC[slot]
                    param.name = f"{slot}_{c + 1}"
                    param.__dict__["label_text"] = label.format(i=c + 1)

        # -- values ---------------------------------------------------------
        def components(self) -> list:
            """Read every Gaussian out of the group, following crosslinks.

            Reading a linked parameter returns its master's current value, so
            the ellipse drawn is whatever the fit it is pinned to says now.
            """
            out = []
            params = self.parameters_all
            for c in range(len(params) // WIDTH):
                p = dict(zip(SLOTS, params[c * WIDTH : (c + 1) * WIDTH]))
                w = float(p["w"].value)
                if not np.isfinite(w) or w < 0:
                    w = 1.0
                held_rho = is_held(p["rho"])
                out.append(
                    GaussianComponent(
                        mu=np.array([float(p["x"].value), float(p["y"].value)], dtype=float),
                        cov=cov_from_sd_rho(p["sd_x"].value, p["sd_y"].value, p["rho"].value),
                        w=w,
                        fix_mu=np.array([is_held(p["x"]), is_held(p["y"])], dtype=bool),
                        fix_cov=np.array(
                            [[is_held(p["sd_x"]), held_rho],
                             [held_rho, is_held(p["sd_y"])]], dtype=bool,
                        ),
                        fix_w=is_held(p["w"]),
                    )
                )
            return out

        def write(
            self,
            index: int,
            mu: Sequence[float],
            cov: Sequence[Sequence[float]],
            w: float | None = None,
        ) -> None:
            """Write a fitted component back.

            Linked parameters are skipped — their value is owned by the master
            they follow, so assigning here would be either discarded or a silent
            unlink.
            """
            p = self.parameters_of(index)
            sd_x, sd_y, rho = sd_rho_from_cov(cov)
            values = {
                "x": float(mu[0]), "y": float(mu[1]),
                "sd_x": sd_x, "sd_y": sd_y, "rho": rho,
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

        # -- persistence ----------------------------------------------------
        def records(self) -> list:
            """Return one flat ``{field: value}`` record per Gaussian, for saving."""
            records = []
            params = self.parameters_all
            for c in range(len(params) // WIDTH):
                p = dict(zip(SLOTS, params[c * WIDTH : (c + 1) * WIDTH]))
                record: dict[str, Any] = {slot: float(p[slot].value) for slot in SLOTS}
                for slot in ("x", "y", "sd_x", "sd_y", "rho"):
                    record[f"fix_{slot}"] = bool(is_held(p[slot]))
                records.append(record)
            return records

        def apply_records(self, records: Sequence[Mapping[str, Any]]) -> None:
            """Replace the Gaussians with the ones in ``records``."""
            self.clear()
            for record in records:
                self.append(
                    (float(record.get("x", 0.0)), float(record.get("y", 0.0))),
                    cov_from_sd_rho(
                        record.get("sd_x", 0.0), record.get("sd_y", 0.0),
                        record.get("rho", 0.0),
                    ),
                    float(record.get("w", 1.0)),
                    fixed={
                        slot: bool(record.get(f"fix_{slot}", False))
                        for slot in ("x", "y", "sd_x", "sd_y", "rho")
                    },
                )

    _MIXTURE_CLASS = GaussianMixture
    return _MIXTURE_CLASS


def build_gaussian_group(name: str = DEFAULT_GROUP_NAME):
    """Return an empty mixture group ready to take components."""
    return gaussian_mixture_class()(name=name)


@dataclasses.dataclass
class GaussianMixtureView:
    """Renderable view of a mixture group — one ``dynamic_group`` section.

    ``AutoForm(GaussianMixtureView(group))`` produces the same component table a
    model editor uses for lifetimes and rotations: one Gaussian per row, the
    shared add / remove buttons, the shared columns. Everything particular to
    this host is *declared* here rather than wired by hand — the slot titles
    (the group starts empty, so they cannot be read off the first component),
    the column subset (no chisurf fit optimises these, so there is no error
    estimate to show), and that an edit has no backend fit to be sent to.

    Parameters
    ----------
    group : GaussianMixture
        The mixture to render.
    on_changed : callable, optional
        Called after any edit or add/remove; the hook ``AutoForm`` looks for on
        a model that is not a fit model, and how the panel learns to redraw.
    title : str, optional
        Section title.
    """

    group: Any
    on_changed: Any = None
    title: str = DEFAULT_GROUP_NAME

    def view_spec(self):
        """Return the view: one panel holding the component table."""
        from chisurf.core.dataspec import DynamicGroupSection, ModelView, PanelSection

        return ModelView(
            sections=(
                PanelSection(
                    title=self.title,
                    # The panel's header carries the shared "bounds" button, which
                    # is what keeps the Lo/Hi/Bounds columns out of a narrow dock
                    # while leaving them one click (or one details popup) away.
                    bounds_toggle=True,
                    sections=(
                        DynamicGroupSection(
                            target="group",
                            rows_source="rows",
                            row_width=WIDTH,
                            style="table",
                            slot_labels=SLOT_LABELS,
                            # No fit optimises these, so there is no error to show.
                            columns=("value", "fixed", "bounds_lo", "bounds_hi", "bounds_on"),
                            remote=False,
                            min_rows=0,
                            collapsible=False,
                        ),
                    ),
                ),
            )
        )


__all__ = [
    "SLOTS",
    "SLOT_LABELS",
    "WIDTH",
    "DEFAULT_GROUP_NAME",
    "RECORD_FIELDS",
    "GaussianComponent",
    "GaussianMixtureView",
    "build_gaussian_group",
    "cov_from_sd_rho",
    "gaussian_mixture_class",
    "is_held",
    "regularized",
    "sd_rho_from_cov",
]
