"""Population-wise Gaussians: one component per population, fitted by EM.

A Gaussian parameter made a vector gives that component one value per
population (:mod:`ndxplorer.analysis.gaussian_populations`). Synthetic bursts
of two labelled populations whose component differs only in its centre: the
fit must recover each population's centre and the shared widths, and write
them into the elements; a weight vector recovers each population's shares.
"""

from __future__ import annotations

import numpy as np
import pytest
from ndxplorer.analysis import gaussian_populations as gpop
from ndxplorer.core.gaussian_parameters import build_gaussian_group


def _data(seed=0, n=3000):
    rng = np.random.default_rng(seed)
    label = np.repeat([0.0, 1.0], n)
    x = np.where(label == 0, 2.0, 6.0) + rng.normal(0.0, 0.5, 2 * n)
    y = 5.0 + rng.normal(0.0, 0.8, 2 * n)
    return x, y, {"Cluster Label": label}


def test_the_centre_is_fitted_per_population_and_the_widths_are_shared():
    x, y, cols = _data()
    group = build_gaussian_group()
    group.append((4.0, 4.0), np.diag([1.0, 1.0]))
    group.get("x_1").to_vector(["0", "1"])
    assert gpop.labels_of(group) == ["0", "1"]
    fit = gpop.fit_population_mixture(group, x, y, cols.get, (0.0, 10.0), (0.0, 10.0))
    gpop.write_population_fit(group, fit)
    assert group.get("x_1[0]").value == pytest.approx(2.0, abs=0.05)
    assert group.get("x_1[1]").value == pytest.approx(6.0, abs=0.05)
    assert group.get("y_1").value == pytest.approx(5.0, abs=0.05)          # shared
    assert group.get("sd_x_1").value == pytest.approx(0.5, abs=0.03)       # pooled width
    assert group.get("sd_y_1").value == pytest.approx(0.8, abs=0.05)
    assert group.population_shares == pytest.approx({"0": 0.5, "1": 0.5})
    # each population's component is drawn at its own centre
    centres = [c.mu[0] for c in (gpop.components_for(group, "0")[0],
                                 gpop.components_for(group, "1")[0])]
    assert centres == pytest.approx([2.0, 6.0], abs=0.05)
    rows = gpop.population_rows(group)
    assert [(label, k) for label, k, *_ in rows] == [("0", 0), ("1", 0)]
    assert sum(r[-1] for r in rows) == pytest.approx(1.0)


def test_a_weight_vector_gives_each_population_its_shares():
    rng = np.random.default_rng(1)
    # population 0: 80 % at x=2, 20 % at x=6; population 1: the other way round
    n = 4000
    label = np.repeat([0.0, 1.0], n)
    high = np.concatenate([rng.random(n) < 0.2, rng.random(n) < 0.8])
    x = np.where(high, 6.0, 2.0) + rng.normal(0.0, 0.4, 2 * n)
    y = rng.normal(5.0, 0.4, 2 * n)
    group = build_gaussian_group()
    group.append((2.5, 5.0), np.diag([0.3, 0.3]))
    group.append((5.5, 5.0), np.diag([0.3, 0.3]))
    group.get("w_1").to_vector(["0", "1"])
    group.get("w_2").to_vector(["0", "1"])
    fit = gpop.fit_population_mixture(group, x, y, {"Cluster Label": label}.get,
                                      (0.0, 10.0), (0.0, 10.0))
    gpop.write_population_fit(group, fit)
    assert group.get("w_1[0]").value == pytest.approx(0.8, abs=0.03)
    assert group.get("w_1[1]").value == pytest.approx(0.2, abs=0.03)
    assert group.get("x_1").value == pytest.approx(2.0, abs=0.05)          # centres shared
    assert group.get("x_2").value == pytest.approx(6.0, abs=0.05)


def test_a_held_element_stays_and_probability_columns_work():
    x, y, cols = _data()
    cols = {"P0": (cols["Cluster Label"] == 0).astype(float),
            "P1": (cols["Cluster Label"] == 1).astype(float)}
    group = build_gaussian_group()
    group.append((4.0, 5.0), np.diag([1.0, 1.0]))
    group.get("x_1").set_vector([4.0, 4.0], ["A", "B"], column="none",
                                probabilities={"A": "P0", "B": "P1"})
    group.get("x_1[B]").fixed = True
    fit = gpop.fit_population_mixture(group, x, y, cols.get, (0.0, 10.0), (0.0, 10.0))
    gpop.write_population_fit(group, fit)
    assert group.get("x_1[A]").value == pytest.approx(2.0, abs=0.05)
    assert group.get("x_1[B]").value == pytest.approx(4.0)


def test_no_population_column_is_a_fit_error():
    from ndxplorer.analysis.gaussian_mixture import GaussianFitError

    x, y, _cols = _data()
    group = build_gaussian_group()
    group.append((4.0, 5.0), np.diag([1.0, 1.0]))
    group.get("x_1").to_vector(["0", "1"])
    with pytest.raises(GaussianFitError, match="Cluster Label"):
        gpop.fit_population_mixture(group, x, y, {}.get, (0.0, 10.0), (0.0, 10.0))
