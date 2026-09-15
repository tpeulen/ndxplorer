"""The declared dependencies are actually importable.

Fourteen test modules guard a ChiSurf import with ``pytest.importorskip``. Each
one is individually reasonable and collectively they are a hazard: with ChiSurf
off the path the suite does not fail, it **shrinks** -- twenty-odd tests turn
into skips, the region-gate semantics stop being checked at all, and what is
left still prints green. A misconfigured ``PYTHONPATH`` then reads exactly like
a passing run.

This file is the one place that says so out loud. It is a single named failure
that points at the cause, rather than a silence spread across a dozen files.
ChiSurf is a declared dependency in ``pyproject.toml`` -- region and lasso gates
are ``chisurf.core.roi`` shapes, the parameter and constants tables are
``chisurf.core.fitting.parameter`` groups, the data-frame editor and glyphs come
from ``chisurf.gui`` -- so a run without it is a broken environment, not a
supported configuration.

Deliberately **not** in ``conda-recipe/meta.yaml``: no chisurf conda package
exists on the channels that recipe builds against. See the comment there.
"""

from __future__ import annotations

import importlib
import pathlib
import tomllib

import pytest

#: The ChiSurf modules ndXplorer reaches into, and what breaks without each.
#: Qt-free ones only -- the ``chisurf.gui`` importers all degrade to a local
#: fallback and are covered by their own tests.
REQUIRED = {
    "chisurf.core.roi": "region and lasso gates (ndxplorer.core.region_selection)",
    "chisurf.core.fitting.parameter": "the parameter and constants tables",
    "chisurf.core.models.parse": "the curve-fit equation models",
}


def test_chisurf_is_declared_in_pyproject():
    """The dependency has to be written down, not just used.

    It was used by the ROI gates, the parameter tables, the data-frame editor,
    the curve-fit dialog and the glyphs, and named in no dependency list -- so a
    clean install imported fine and raised the first time somebody drew a lasso.
    """
    root = pathlib.Path(__file__).resolve().parents[2]
    metadata = tomllib.loads((root / "pyproject.toml").read_text())
    declared = metadata["project"]["dependencies"]

    names = {entry.split()[0].split(">")[0].split("=")[0].split("[")[0].lower()
             for entry in declared}
    assert "chisurf" in names, (
        f"ChiSurf is imported throughout ndxplorer but not in {declared}")


@pytest.mark.parametrize("module", sorted(REQUIRED), ids=sorted(REQUIRED))
def test_a_declared_dependency_is_importable(module):
    """A missing ChiSurf must fail here, loudly and once.

    Without this, it fails nowhere: every module that needs it guards the import
    with ``importorskip`` and the suite quietly gets smaller.
    """
    try:
        importlib.import_module(module)
    except ImportError as exc:  # pragma: no cover - only on a broken env
        pytest.fail(
            f"{module} is not importable, so {REQUIRED[module]} is untested and "
            f"broken at runtime.\n"
            f"  cause: {exc}\n"
            f"  fix: run in the `arm64` conda env with the ChiSurf source tree "
            f"on PYTHONPATH, e.g.\n"
            f"       PYTHONPATH=/path/to/chisurf python -m pytest ...\n"
            f"  ChiSurf is on no package index; it and ndXplorer install from "
            f"the same source tree.")


def test_the_region_gate_path_really_is_live():
    """Not just importable -- reachable through ndXplorer's own seam.

    ``importorskip('chisurf.core.roi')`` succeeding does not prove the gate
    works; the bridge in ``region_selection`` has its own import, which is the
    one that used to raise ``ModuleNotFoundError`` mid-analysis.
    """
    import numpy as np

    from ndxplorer.core.region_selection import RegionDataSelection

    roi_module = importlib.import_module("chisurf.core.roi")
    rectangle = roi_module.RectangleROI(x0=0.0, y0=0.0, x1=1.0, y1=1.0)
    gate = RegionDataSelection(rectangle, 0, 1)

    # (n_parameters, n_points); True means EXCLUDED.
    data = np.array([[0.5, 5.0], [0.5, 5.0]])
    excluded = gate.get_mask(data)
    assert excluded.shape == (2, 2)
    assert not excluded[0, 0], "a point inside the rectangle was excluded"
    assert excluded[0, 1], "a point outside the rectangle was kept"
