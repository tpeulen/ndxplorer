"""The Gaussian fit panel edits chisurf fitting parameters, so it can be linked.

The panel used to hold its Gaussians as table text with a checkbox in the corner
of each cell. They are :class:`FittingParameter` objects now, which is what lets
a population's centre be pinned to a parameter of an actual fit — so the things
worth testing are that the EM still moves a free parameter onto the data, that
it leaves a *fixed* one alone, and that it treats a **linked** one as held and
never writes over its master's value.
"""

from __future__ import annotations

import numpy as np
import pytest
from ndxplorer.core.data_source import DataSource
from qtpy import QtCore, QtWidgets

gp = pytest.importorskip(
    "ndxplorer.core.gaussian_parameters",
    reason="needs chisurf's fitting parameters",
)

#: Where the two simulated populations sit, and how wide they are.
BLOBS = [(0.25, 0.35, 0.04, 0.05), (0.70, 0.70, 0.06, 0.03)]


@pytest.fixture(scope="module")
def qt_app():
    return QtWidgets.QApplication.instance() or QtWidgets.QApplication([])


def _settle(app, ms: int = 50) -> None:
    loop = QtCore.QEventLoop()
    QtCore.QTimer.singleShot(ms, loop.quit)
    loop.exec_()
    app.processEvents()


@pytest.fixture(scope="module")
def window(qt_app):
    """Return a window showing two well-separated blobs, axes selected."""
    from ndxplorer.core.plot_main import NDXplorer

    rng = np.random.default_rng(0)
    data = np.vstack(
        [
            np.column_stack([rng.normal(cx, sx, 3000), rng.normal(cy, sy, 3000)])
            for cx, cy, sx, sy in BLOBS
        ]
    )
    source = DataSource.from_columns(
        {"E": data[:, 0], "S": data[:, 1], "z": rng.normal(0, 1, len(data))}
    )
    columns = source.parameter_names

    win = NDXplorer(data_source=source)
    win.resize(900, 700)
    win.show()
    qt_app.processEvents()
    control = win.plot_control
    control.update(update_comboboxes=True, update_plots=False)
    control.comboBoxSelX.setCurrentIndex(columns.index("E"))
    control.comboBoxSelY.setCurrentIndex(columns.index("S"))
    control.comboBoxSelZ.setCurrentIndex(columns.index("z"))
    win.update_plots()
    for _ in range(10):
        _settle(qt_app, 100)
        if win._histogram.get("2d") is not None:
            break
    yield win
    win.close()


@pytest.fixture
def panel(window):
    """Return the Gaussian panel, seeded with one component per blob and no links."""
    gf = window.gaussian_fit
    gf.on_clear_gaussians()
    for cx, cy, sx, sy in BLOBS:
        # Deliberately off the truth, so a fit that does nothing is visible.
        gf._append_gaussian_row((cx + 0.05, cy - 0.05), np.diag([sx ** 2, sy ** 2]))
    yield gf
    gf.on_clear_gaussians()


def test_the_panel_stacks_a_gaussian_s_parameters(panel):
    """One row per *parameter*: six numbers side by side would not fit the dock."""
    model = panel._table.table_model
    assert model.rowCount() == 2 * gp.WIDTH
    assert [p.name for p in model.parameters][: gp.WIDTH] == [
        f"{slot}_1" for slot in gp.SLOTS
    ]


def test_a_selected_row_names_the_gaussian_it_belongs_to(panel):
    view = panel._table.table_view
    view.selectRow(gp.WIDTH + 2)  # a parameter of the second component
    assert panel.selected_component_rows() == [1]


def test_the_gaussians_are_published_for_crosslinking(panel):
    from ndxplorer.analysis.gaussian_fit import GAUSSIAN_OWNER_ID

    from chisurf.core.parameter_group_registry import get_registered_parameter_group

    from ndxplorer.core.chisurf_binding import chisurf_group

    published = get_registered_parameter_group(GAUSSIAN_OWNER_ID)
    assert published is chisurf_group(panel.group)      # ChiSurf's mirror of the model
    assert [p.name for p in published.parameters_all][:2] == ["x_1", "y_1"]


def test_a_free_gaussian_is_fitted_onto_its_population(panel):
    panel.on_fit_2d_gaussian()
    fitted = panel.group.components()
    for component, (cx, cy, _, _) in zip(fitted, BLOBS):
        assert component.mu[0] == pytest.approx(cx, abs=0.01)
        assert component.mu[1] == pytest.approx(cy, abs=0.01)


def test_a_fixed_centre_is_left_exactly_where_it_was(panel):
    held = panel.group.parameters_of(0)["x"]
    held.fixed = True
    before = float(held.value)
    panel.on_fit_2d_gaussian()
    assert float(held.value) == pytest.approx(before, abs=1e-12)
    # ...while the free coordinate of the same component did move onto the data.
    assert panel.group.components()[0].mu[1] == pytest.approx(BLOBS[0][1], abs=0.01)


def test_a_crosslinked_centre_is_held_at_its_master(panel):
    from chisurf.core.fitting.parameter import FittingParameter

    master = FittingParameter(name="tau_donor", value=0.31)
    panel.group.parameters_of(0)["x"].link = master

    panel.on_fit_2d_gaussian()

    assert panel.group.components()[0].mu[0] == pytest.approx(0.31)
    # The master itself is untouched: the fit may not reach through a link.
    assert float(master.value) == pytest.approx(0.31)
    # And the ellipse follows the master when *it* moves.
    master.value = 0.44
    assert panel.group.components()[0].mu[0] == pytest.approx(0.44)


def test_deleting_a_row_removes_that_gaussian(panel):
    first_y = panel.group.components()[1].mu[1]
    panel._delete_selected_gaussian_rows([0])
    remaining = panel.group.components()
    assert len(remaining) == 1
    assert remaining[0].mu[1] == pytest.approx(first_y)
    assert panel._table.table_model.rowCount() == gp.WIDTH


def test_saved_records_carry_the_held_flags(panel):
    panel.group.parameters_of(1)["rho"].fixed = True
    records = panel._rows_to_dicts()
    assert len(records) == 2
    assert records[1]["fix_rho"] is True
    assert records[0]["fix_rho"] is False
