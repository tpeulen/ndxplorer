"""The 2-D Gaussians are fitting parameters, so they can be crosslinked.

These are the bookkeeping guarantees the fit panel rests on: a component reads
back as the covariance it was given, "hold this" covers *linked* as well as
fixed, a linked parameter is never written over, and removing one Gaussian
leaves the others intact and correctly numbered.
"""

from __future__ import annotations

import numpy as np
import pytest

gp = pytest.importorskip(
    "ndxplorer.core.gaussian_parameters",
    reason="needs chisurf's fitting parameters",
)


@pytest.fixture
def group():
    g = gp.build_gaussian_group()
    gp.append_component(g, (0.25, 0.35), np.diag([0.04 ** 2, 0.05 ** 2]), 1.0)
    gp.append_component(g, (0.70, 0.70), np.diag([0.06 ** 2, 0.03 ** 2]), 2.0)
    return g


def test_a_component_reads_back_as_the_covariance_it_was_given(group):
    cov = np.array([[0.04 ** 2, 0.5 * 0.04 * 0.05], [0.5 * 0.04 * 0.05, 0.05 ** 2]])
    gp.append_component(group, (0.5, 0.5), cov)
    read = gp.read_components(group)[-1]
    assert read.mu == pytest.approx([0.5, 0.5])
    assert read.cov == pytest.approx(cov, abs=1e-12)


def test_the_parameters_are_laid_out_component_major(group):
    names = [p.name for p in group.parameters_all]
    assert names[: gp.WIDTH] == ["x_1", "y_1", "sd_x_1", "sd_y_1", "rho_1", "w_1"]
    assert len(names) == 2 * gp.WIDTH
    assert gp.component_count(group) == 2


def test_a_width_cannot_be_negative_and_a_correlation_cannot_pass_one(group):
    params = gp.parameters_of(group, 0)
    params["sd_x"].value = -1.0
    params["rho"].value = 5.0
    assert params["sd_x"].value == pytest.approx(0.0)
    assert params["rho"].value == pytest.approx(1.0)


def test_removing_a_gaussian_keeps_the_others_and_renumbers_them(group):
    gp.append_component(group, (0.9, 0.1), np.diag([0.01, 0.01]), 3.0)
    gp.remove_components(group, [0])
    assert gp.component_count(group) == 2
    assert [p.name for p in group.parameters_all][:2] == ["x_1", "y_1"]
    kept = gp.read_components(group)
    assert [c.mu[0] for c in kept] == pytest.approx([0.70, 0.90])


def test_a_linked_parameter_counts_as_held(group):
    from chisurf.core.fitting.parameter import FittingParameter

    master = FittingParameter(name="master", value=0.42)
    gp.parameters_of(group, 0)["x"].link = master
    component = gp.read_components(group)[0]
    assert component.fix_mu[0]
    # ...and reading it follows the master, so the ellipse drawn is what the
    # thing it is pinned to says right now.
    assert component.mu[0] == pytest.approx(0.42)


def test_a_fit_result_is_not_written_over_a_link(group):
    from chisurf.core.fitting.parameter import FittingParameter

    master = FittingParameter(name="master", value=0.42)
    gp.parameters_of(group, 0)["x"].link = master
    gp.write_component(group, 0, (0.99, 0.88), np.diag([0.01, 0.01]))
    read = gp.read_components(group)[0]
    assert read.mu[0] == pytest.approx(0.42)  # the master's, not the fit's
    assert read.mu[1] == pytest.approx(0.88)  # the free one did move


def test_records_round_trip_through_a_saved_file(group):
    gp.parameters_of(group, 1)["sd_x"].fixed = True
    records = gp.components_to_records(group)
    assert set(records[0]) == set(gp.RECORD_FIELDS)

    restored = gp.build_gaussian_group()
    gp.apply_records(restored, records)
    assert gp.components_to_records(restored) == records


def test_clearing_drops_every_component(group):
    gp.clear_components(group)
    assert gp.component_count(group) == 0
    assert gp.read_components(group) == []
