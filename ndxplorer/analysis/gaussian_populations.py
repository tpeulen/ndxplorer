"""A Gaussian mixture whose components differ between populations.

A Gaussian parameter made a **vector** (``x_1`` with elements ``x_1[HF]``,
``x_1[LF]``) says: *this component is not the same in every population*. The
population axis of the vector -- a label column (``Cluster Label``, a
measurement or time-window label) or per-burst probability columns -- says
which population a burst belongs to. The model is then a **population-conditional
mixture**: a burst of population *q* is drawn from

    p(x | q) = sum_k w_k[q] N(x | mu_k[q], Sigma_k[q])

where a parameter that is a vector takes its element for *q*, and every other
parameter is **shared** by all populations. A burst that belongs to no
population uses the parameters' own (global) values. Component *k* is thus
drawn once per population, and fitted per population where it is a vector and
jointly where it is shared.

Why this is not "one more component": a mixture's components are *latent*
populations -- every burst may come from any of them. A vector's populations
are *observed*: the axis says which one a burst is in. A component per observed
population keeps the latent structure (how many species, their shares) the same
in every population while letting what differs between them (a centre that
shifts with a changed environment, a width) differ -- two components and a
link cannot say that, since each of them would be free to take bursts of the
other population.

EM, in the fit space of :func:`~ndxplorer.analysis.gaussian_mixture.fit_mixture`:
the E-step runs each population's mixture over its bursts (weighted by
membership); the M-step takes a vector element from its population's
responsibilities and a shared parameter from all of them pooled. A covariance
is assembled from its parts: a population-wise ``sd_x`` from that population's
scatter, a shared ``rho`` from the pooled one. Held elements (fixed or linked)
stay at their value, element by element.

Pure numpy.
"""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

import numpy as np

from ..core.gaussian_parameters import (
    SLOTS,
    GaussianComponent,
    cov_from_sd_rho,
    sd_rho_from_cov,
)
from ..core.overlay_curves import population_colour, population_labels, population_sources
from ..core.parameters import is_held

__all__ = [
    "labels_of",
    "components_for",
    "population_rows",
    "membership",
    "fit_population_mixture",
    "write_population_fit",
    "tinted",
]


def labels_of(group) -> List[str]:
    """The populations the mixture is drawn for (``[]``: an ordinary mixture)."""
    return population_labels(group)


def _source_of(parameter, sources: dict, label: Optional[str]):
    """The parameter a population reads *parameter* from: its element, or itself."""
    vector = sources.get(parameter.name)
    if vector is None or label is None:
        return parameter
    element = vector.element(label)
    return element if element is not None else vector


def components_for(group, label: Optional[str]) -> List[GaussianComponent]:
    """Population *label*'s components (``None``: the global ones, :meth:`components`)."""
    if label is None:
        return group.components()
    sources = population_sources(group)
    out = []
    for k in range(len(group)):
        p = {slot: _source_of(q, sources, label) for slot, q in group.parameters_of(k).items()}
        held_rho = is_held(p["rho"])
        w = float(p["w"].value)
        out.append(GaussianComponent(
            mu=np.array([float(p["x"].value), float(p["y"].value)]),
            cov=cov_from_sd_rho(p["sd_x"].value, p["sd_y"].value, p["rho"].value),
            w=w if np.isfinite(w) and w >= 0 else 1.0,
            fix_mu=np.array([is_held(p["x"]), is_held(p["y"])], dtype=bool),
            fix_cov=np.array([[is_held(p["sd_x"]), held_rho], [held_rho, is_held(p["sd_y"])]],
                             dtype=bool),
            fix_w=is_held(p["w"])))
    return out


def population_rows(group) -> List[Tuple[str, int, np.ndarray, np.ndarray, float]]:
    """``[(population, component, mu, cov, weight)]`` for drawing the model.

    A population's weights are normalised over its components and scaled by
    its share of the bursts at the last fit (``group.population_shares``;
    equal shares before any fit), so the rows add up to one mixture.
    """
    labels = labels_of(group)
    shares = dict(getattr(group, "population_shares", None) or {})
    out = []
    for label in labels:
        share = float(shares.get(label, 1.0 / len(labels)))
        comps = components_for(group, label)
        total = sum(max(0.0, c.w) for c in comps) or 1.0
        out += [(label, k, c.mu, c.cov, share * max(0.0, c.w) / total)
                for k, c in enumerate(comps)]
    return out


def membership(column: Callable[[str], Optional[np.ndarray]], n: int, axis,
               labels: Sequence[str]) -> np.ndarray:
    """``(n, P + 1)`` membership of *n* bursts: one column per label, the last "none".

    Probability columns when the axis names one for every label and all
    exist; otherwise 1 where the label column holds the label's code. Raises
    ``ValueError`` when the data has neither.
    """
    probs = dict(getattr(axis, "probabilities", {}) or {})
    cols = None
    if probs and all(label in probs for label in labels):
        stack = [column(probs[label]) for label in labels]
        if all(s is not None for s in stack):
            cols = [np.nan_to_num(np.asarray(s, float), nan=0.0) for s in stack]
    if cols is None:
        codes = column(axis.column)
        if codes is None:
            raise ValueError(f"the data has no population column '{axis.column}'")
        codes = np.asarray(codes, float)
        cols = [(codes == axis.code_of(label, i)).astype(float) for i, label in enumerate(labels)]
    member = np.column_stack(cols + [np.zeros(n)]) if cols else np.zeros((n, 1))
    total = member[:, :-1].sum(axis=1)
    member[:, :-1] /= np.where(total > 1.0, total, 1.0)[:, None]
    member[:, -1] = np.clip(1.0 - member[:, :-1].sum(axis=1), 0.0, 1.0)
    return member


def _axis(group):
    from ..core.vector_constants import PopulationAxis

    vector = next(iter(population_sources(group).values()))
    return PopulationAxis.from_dict(vector.vector_state() if hasattr(vector, "vector_state")
                                    else {})


def fit_population_mixture(group, x, y, column: Callable[[str], Optional[np.ndarray]],
                           x_range, y_range, log_x: bool = False, log_y: bool = False,
                           settings: Optional[Dict[str, Any]] = None) -> dict:
    """Fit the population-conditional mixture (module docstring) to the points ``(x, y)``.

    *column(name)* gives a burst column over the same points (the label or
    probability columns of the vectors' axis). Returns ``{"labels", "values",
    "shares"}``: per population (and ``None``, no population) the fitted
    ``(mu, cov, w)`` of every component in value space, and each population's
    share of the fitted bursts. :func:`write_population_fit` writes it.
    """
    from . import gaussian_mixture as gm

    labels = labels_of(group)
    if not len(group):
        raise gm.GaussianFitError("No Gaussians",
                                  "Add one or more Gaussians (click on the histogram) before fitting.")
    x, y = np.asarray(x, float).ravel(), np.asarray(y, float).ravel()
    try:
        member = membership(column, x.size, _axis(group), labels)
    except ValueError as exc:
        raise gm.GaussianFitError("No populations", f"{exc}: the population-wise Gaussians "
                                  "cannot tell the bursts apart.") from exc
    (x0, x1), (y0, y1) = sorted(map(float, x_range)), sorted(map(float, y_range))
    keep = np.isfinite(x) & np.isfinite(y) & (x >= x0) & (x <= x1) & (y >= y0) & (y <= y1)
    keep &= (x > 0) if log_x else True
    keep &= (y > 0) if log_y else True
    X, member = np.column_stack([x, y])[keep], member[keep]
    if not len(X):
        raise gm.GaussianFitError("No data", "No data within the visible histogram range to fit.")
    X = np.column_stack([np.log(X[:, 0]) if log_x else X[:, 0],
                         np.log(X[:, 1]) if log_y else X[:, 1]])
    cfg = dict(gm.GMM_DEFAULTS)
    cfg.update(settings or {})
    states = [components_for(group, label) for label in labels] + [group.components()]
    sources = population_sources(group)
    names = [group.parameters_of(k) for k in range(len(group))]
    vec = np.array([[p[slot].name in sources for slot in SLOTS] for p in names], dtype=bool)
    mu, cov, w, held = _em_start(states, log_x, log_y)
    mu, cov, w = _em(X, member, mu, cov, w, held, vec, float(cfg["reg_covar"]),
                     int(cfg["max_iter"]), float(cfg["tol"]))
    values = {}
    for q, label in enumerate(labels + [None]):
        values[label] = [gm.to_value_space(mu[q, k], cov[q, k], log_x, log_y) + (float(w[q, k]),)
                         for k in range(len(group))]
    fractions = member.sum(axis=0) / max(float(len(X)), 1.0)
    return {"labels": labels, "values": values,
            "shares": {label: float(f) for label, f in zip(labels + [None], fractions)}}


def _em_start(states, log_x, log_y):
    from . import gaussian_mixture as gm

    q, k = len(states), len(states[0])
    mu, cov, w = np.zeros((q, k, 2)), np.zeros((q, k, 2, 2)), np.zeros((q, k))
    held = np.zeros((q, k, len(SLOTS)), dtype=bool)
    for i, comps in enumerate(states):
        for j, c in enumerate(comps):
            mu[i, j], cov[i, j] = gm.to_fit_space(c.mu, c.cov, log_x, log_y)
            w[i, j] = max(float(c.w), 0.0)
            held[i, j] = [c.fix_mu[0], c.fix_mu[1], c.fix_cov[0, 0], c.fix_cov[1, 1],
                          c.fix_cov[0, 1], c.fix_w]
        total = w[i].sum()
        w[i] = w[i] / total if total > 0 else 1.0 / k
    return mu, cov, w, held


def _em(X, member, mu, cov, w, held, vec, reg, max_iter, tol):
    """EM of the population-conditional mixture; returns ``(mu, cov, w)``."""
    from .gaussian_mixture import _floored, _log_densities

    n_q, n_k = w.shape
    tiny = np.finfo(float).tiny
    anchor = (mu.copy(), cov.copy(), w.copy())
    n_q_bursts = member.sum(axis=0)
    previous = -np.inf
    for _ in range(max(1, max_iter)):
        resp, ll = [], 0.0
        for q in range(n_q):
            if n_q_bursts[q] <= 0:
                resp.append(np.zeros((len(X), n_k)))
                continue
            share = w[q] / max(float(w[q].sum()), tiny)
            logp = _log_densities(X, mu[q], cov[q]) + np.log(np.maximum(share, tiny))[None, :]
            top = logp.max(axis=1, keepdims=True)
            top[~np.isfinite(top)] = 0.0
            norm = top[:, 0] + np.log(np.exp(logp - top).sum(axis=1))
            ll += float(np.sum(member[:, q] * norm))
            r = np.exp(logp - norm[:, None])
            r[~np.isfinite(r)] = 1.0 / n_k
            resp.append(member[:, q, None] * r)
        nqk = np.array([r.sum(axis=0) for r in resp])            # (Q, K)
        for k in range(n_k):
            live = nqk[:, k] > tiny
            sums = np.array([resp[q][:, k] @ X for q in range(n_q)])  # (Q, 2)
            for j in (0, 1):
                if vec[k, j]:
                    mu[live, k, j] = sums[live, j] / nqk[live, k]
                elif live.any():
                    mu[:, k, j] = sums[:, j].sum() / nqk[:, k].sum()
            scatter = np.zeros((n_q, 2, 2))
            for q in np.flatnonzero(live):
                d = X - mu[q, k]
                scatter[q] = (resp[q][:, k][:, None] * d).T @ d
            pooled = scatter.sum(axis=0) / max(nqk[:, k].sum(), tiny)
            for q in np.flatnonzero(live):
                own = scatter[q] / nqk[q, k]
                sx = np.sqrt(max((own if vec[k, 2] else pooled)[0, 0], 0.0))
                sy = np.sqrt(max((own if vec[k, 3] else pooled)[1, 1], 0.0))
                part = own if vec[k, 4] else pooled
                rho = part[0, 1] / max(np.sqrt(part[0, 0] * part[1, 1]), tiny)
                cov[q, k] = _floored(cov_from_sd_rho(sx, sy, rho), reg)
            if vec[k, 5]:
                w[live, k] = nqk[live, k] / np.maximum(n_q_bursts[live], tiny)
            else:
                w[:, k] = nqk[:, k].sum() / max(n_q_bursts.sum(), tiny)
        _stamp(mu, cov, w, held, anchor)
        ll /= max(float(len(X)), 1.0)
        if ll - previous < tol:
            break
        previous = ll
    return mu, cov, w


def _stamp(mu, cov, w, held, anchor):
    """Put every held element back at its anchor."""
    a_mu, a_cov, a_w = anchor
    for j in (0, 1):
        mu[..., j] = np.where(held[..., j], a_mu[..., j], mu[..., j])
    for slot, (r, c) in ((2, (0, 0)), (3, (1, 1)), (4, (0, 1))):
        cov[..., r, c] = np.where(held[..., slot], a_cov[..., r, c], cov[..., r, c])
        cov[..., c, r] = cov[..., r, c]
    w[...] = np.where(held[..., 5], a_w, w)


def write_population_fit(group, fit: dict) -> None:
    """Write :func:`fit_population_mixture`'s result into the group.

    A vector's elements take their population's value, its own (global) value
    the no-population bursts' -- when there were any; a shared parameter takes
    the value of the population with the most bursts. Linked parameters and
    held weights are left alone.
    """
    labels, values, shares = fit["labels"], fit["values"], fit["shares"]
    sources = population_sources(group)
    biggest = max(labels + [None], key=lambda l: shares.get(l, 0.0))
    for k in range(len(group)):
        params = group.parameters_of(k)
        for slot in SLOTS:
            p = params[slot]
            vector = sources.get(p.name)
            if vector is not None and vector is not p:
                continue                              # follows a vector constant
            targets = [(label, p.element(label)) for label in labels] if vector is p else []
            if vector is p and shares.get(None, 0.0) > 0.0:
                targets.append((None, p))
            if vector is None:
                targets = [(biggest, p)]
            for label, target in targets:
                if target is None or target.is_linked or (slot == "w" and is_held(target)):
                    continue
                mu, cov, w = values[label][k]
                sd_x, sd_y, rho = sd_rho_from_cov(cov)
                target.value = float({"x": mu[0], "y": mu[1], "sd_x": sd_x, "sd_y": sd_y,
                                      "rho": rho, "w": w}[slot])
    group.population_shares = {l: shares.get(l, 0.0) for l in labels}


def tinted(rgba: Tuple[int, int, int, int], position: int, count: int) -> Tuple[int, ...]:
    """A component's colour tinted for population *position* of *count*."""
    hexed = population_colour("#%02x%02x%02x" % tuple(rgba[:3]), position, count)
    return tuple(int(hexed[i:i + 2], 16) for i in (1, 3, 5)) + (int(rgba[3]),)
