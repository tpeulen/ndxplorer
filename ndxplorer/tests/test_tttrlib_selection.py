"""The tttrlib-backed selection path gives the same answer as the numpy one.

The modules are loaded by file path rather than imported through the package.
That is not a workaround: ``ndxplorer.core.__init__`` pulls in the GUI, and the
selection engine deliberately does not depend on it -- loading it this way is
what proves so, and it lets this run in an environment with no Qt bindings.
"""
import importlib.util
import pathlib
import sys

import numpy as np
import pytest

pytest.importorskip("tttrlib")
_ROOT = pathlib.Path(__file__).resolve().parents[1]


def _load(name, relative):
    spec = importlib.util.spec_from_file_location(name, _ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


ts = _load("_ndx_tttrlib_selection", "core/tttrlib_selection.py")
if not ts.is_available():
    pytest.skip("tttrlib without the region API", allow_module_level=True)

roi_mod = pytest.importorskip("chisurf.core.roi")
RectangleROI, EllipseROI, PolygonROI = roi_mod.RectangleROI, roi_mod.EllipseROI, roi_mod.PolygonROI


class Region:
    """The shape of RegionDataSelection that the engine actually reads.

    A stand-in rather than the real class, because importing that reaches the
    GUI. The attributes below are its whole contract with this code.
    """

    def __init__(self, roi, idx1=0, idx2=1, invert=False, enabled=True):
        self.roi, self.idx1, self.idx2 = roi, idx1, idx2
        self.invert, self.enabled = invert, enabled

    def get_mask(self, data):
        """The numpy reference, copied from RegionDataSelection."""
        values = np.asarray(data, dtype=float)
        n_parameters, n_points = values.shape
        out = np.zeros((n_parameters, n_points), dtype=bool)
        if not self.enabled:
            return out
        x, y = values[self.idx1, :], values[self.idx2, :]
        finite = np.isfinite(x) & np.isfinite(y)
        inside = np.zeros(n_points, dtype=bool)
        if finite.any():
            pts = np.column_stack([x[finite], y[finite]])
            inside[finite] = np.asarray(self.roi.contains(pts), dtype=bool)
        if self.invert:
            inside = ~inside & finite
        out[:] = ~inside
        return out


@pytest.fixture
def values():
    rng = np.random.default_rng(3)
    n = 20000
    return np.vstack([rng.uniform(-1, 2, n), rng.uniform(-1, 2, n), rng.uniform(0, 1, n)])


def _numpy_mask(values, selections):
    n_param, n_pts = values.shape
    mask = np.zeros((n_param, n_pts), dtype=bool)
    for sel in selections:
        mask |= sel.get_mask(values)
    return mask


@pytest.mark.parametrize("make_roi", [
    lambda: RectangleROI(0.0, 0.2, 1.0, 0.8),
    lambda: EllipseROI(0.5, 0.5, 0.4, 0.2),
    lambda: PolygonROI(np.array([[0.0, 0.0], [1.0, 0.1], [0.8, 0.9], [0.1, 0.7]])),
])
def test_same_answer_as_numpy(values, make_roi):
    sel = Region(make_roi())
    assert ts.can_evaluate([sel])
    fast, _ = ts.evaluate(values, [sel])
    slow = _numpy_mask(values, [sel])
    # A crossing-number test and the reference can disagree exactly on an edge.
    assert np.count_nonzero(np.asarray(fast) != slow) <= 3


def test_two_gates_combine_the_same_way(values):
    gates = [Region(RectangleROI(0.0, 0.0, 1.0, 1.0)),
             Region(EllipseROI(0.5, 0.5, 0.3, 0.3))]
    fast, _ = ts.evaluate(values, gates)
    assert np.array_equal(np.asarray(fast), _numpy_mask(values, gates))


def test_inverted_gate(values):
    sel = Region(RectangleROI(0.0, 0.0, 1.0, 1.0), invert=True)
    fast, _ = ts.evaluate(values, [sel])
    assert np.array_equal(np.asarray(fast), _numpy_mask(values, [sel]))


def test_a_disabled_gate_does_nothing(values):
    sel = Region(RectangleROI(0.0, 0.0, 0.1, 0.1), enabled=False)
    fast, _ = ts.evaluate(values, [sel])
    assert not np.asarray(fast).any()


def test_an_unknown_selection_declines_rather_than_guessing():
    class Weird:
        enabled = True
    assert not ts.can_evaluate([Weird()])


def test_non_finite_coordinates_are_excluded():
    values = np.array([[0.5, np.nan, 0.5], [0.5, 0.5, np.inf]])
    sel = Region(RectangleROI(0.0, 0.0, 1.0, 1.0))
    fast, _ = ts.evaluate(values, [sel])
    assert list(np.asarray(fast)[0]) == [False, True, True]


def test_the_store_is_reused_between_evaluations(values):
    sel = Region(RectangleROI(0.0, 0.0, 1.0, 1.0))
    _, store = ts.evaluate(values, [sel])
    _, store2 = ts.evaluate(values, [sel], cache=store)
    assert store2 is store, "rebuilding the store on every drag defeats the point"
