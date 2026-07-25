"""Regression tests for equation column computation (compute_values).

Covers the bug behind the "1% parameter tweak redraws the whole plot" report:
a column reference like ``'Fr'`` was resolved by a prefix fallback in
CaseInsensitiveDict to whatever column merely started with "fr" (e.g.
``FRET-2CDE``) when the exact column was not yet in the once-built cache. That
made the initial compute (raw columns) disagree with any later recompute (all
derived columns present), so the plot jumped on the first edit.
"""
import numpy as np
import pandas as pd

from ndxplorer.core.data_source import compute_values, _EQ_CODE_CACHE


def _frame():
    # 'FRET-2CDE' is a decoy that starts with "fr" and (before the fix) would be
    # returned for a reference to the not-yet-cached 'Fr' column.
    return pd.DataFrame({
        "a": np.arange(1, 11, dtype=float),
        "FRET-2CDE": -np.arange(1, 11, dtype=float),
    })


def test_reference_resolves_exactly_not_by_prefix():
    df = _frame()
    eqs = [{"Fr": "'a' * 2"}, {"ratio": "'a' / 'Fr'"}]
    _EQ_CODE_CACHE.clear()
    compute_values(df, constants={}, equations=eqs)
    # ratio = a / (2a) = 0.5, NOT a / FRET-2CDE (which would be -1.0).
    assert np.allclose(df["ratio"].to_numpy(), 0.5)


def test_compute_is_idempotent_on_already_derived_frame():
    df = _frame()
    eqs = [{"Fr": "'a' * 2"}, {"ratio": "'a' / 'Fr'"}]
    _EQ_CODE_CACHE.clear()
    compute_values(df, constants={}, equations=eqs)
    first = df["ratio"].to_numpy().copy()
    # Recomputing on a frame that already holds the derived columns must give
    # the same result — equations are pure functions of raw inputs + constants.
    compute_values(df, constants={}, equations=eqs)
    assert np.allclose(df["ratio"].to_numpy(), first)


def test_left_of_pipe_lookup_still_works():
    """The legitimate 'Name | suffix' -> 'Name' resolution is preserved."""
    df = pd.DataFrame({"S prompt green (kHz) | 0-2048": np.arange(1, 6, dtype=float)})
    eqs = [{"out": "'S prompt green (kHz)' * 2"}]
    _EQ_CODE_CACHE.clear()
    compute_values(df, constants={}, equations=eqs)
    assert np.allclose(df["out"].to_numpy(), np.arange(1, 6) * 2)


def test_constant_edit_only_perturbs_dependents():
    """A tiny constant change yields a tiny output change (no jump)."""
    df = pd.DataFrame({"Sg": np.linspace(10, 50, 20), "Sr": np.linspace(5, 25, 20)})
    eqs = [
        {"Fg": "'Sg' - 'Bg'"},
        {"Fr": "'Sr' - 'Bg'"},
        {"ratio": "'Fg' / 'Fr'"},
    ]
    _EQ_CODE_CACHE.clear()
    compute_values(df, constants={"Bg": 1.2}, equations=eqs)
    r0 = df["ratio"].to_numpy().copy()
    compute_values(df, constants={"Bg": 1.212}, equations=eqs, changed_constants={"Bg"})
    r1 = df["ratio"].to_numpy()
    assert np.nanmax(np.abs(r0 - r1)) < 0.05


if __name__ == "__main__":  # pragma: no cover
    import pytest
    pytest.main([__file__, "-q"])
