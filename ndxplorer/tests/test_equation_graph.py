"""Tests for the AST equation dependency-graph engine."""
import numpy as np
import pytest

from ndxplorer.core.equation_graph import (
    EquationGraph,
    compute_values_ast,
    validate_equation,
)
from ndxplorer.core.data_source import float_column, store_from_columns


def _column(store, name):
    return float_column(store, store.find(name))


def test_topological_order_handles_out_of_declaration_order():
    """B declared before its dependency A must still compute correctly."""
    df = store_from_columns({"x": np.arange(1, 6, dtype=float)})
    eqs = [
        {"B": "'A' + 1"},   # depends on A, declared first
        {"A": "'x' * 2"},
    ]
    computed = compute_values_ast(df, {}, eqs)
    assert set(computed) == {"A", "B"}
    np.testing.assert_allclose(_column(df, "A"), np.arange(1, 6) * 2)
    np.testing.assert_allclose(_column(df, "B"), np.arange(1, 6) * 2 + 1)


def test_targets_narrow_the_recompute_to_what_is_asked_for():
    """A fit reads two columns; it must not pay for the other forty.

    ``targets`` keeps only the outputs those columns depend on — the difference
    between a fit step costing one equation and costing every equation the
    constant feeds.
    """
    df = store_from_columns({"x": np.arange(1, 6, dtype=float)})
    eqs = [
        {"A": "'x' * 'k'"},          # the plotted column's dependency
        {"Plotted": "'A' + 1"},      # what the fit reads
        {"Elsewhere": "'A' * 10"},   # depends on k too, nobody is looking at it
    ]
    compute_values_ast(df, {"k": 2.0}, eqs)
    elsewhere_before = _column(df, "Elsewhere")

    recomputed = compute_values_ast(
        df, {"k": 3.0}, eqs, changed_constants={"k"}, targets=["Plotted"]
    )

    assert set(recomputed) == {"A", "Plotted"}
    np.testing.assert_allclose(_column(df, "Plotted"), np.arange(1, 6) * 3 + 1)
    np.testing.assert_allclose(_column(df, "Elsewhere"), elsewhere_before)

    # ...and the full recompute afterwards catches the column up.
    compute_values_ast(df, {"k": 3.0}, eqs, changed_constants={"k"})
    np.testing.assert_allclose(_column(df, "Elsewhere"), np.arange(1, 6) * 30)


def test_targeted_recompute_only_transitive_dependents():
    df = store_from_columns({"x": np.arange(1, 6, dtype=float)})
    eqs = [
        {"A": "'x' * 'k'"},      # depends on constant k
        {"B": "'A' + 1"},        # transitively depends on k
        {"C": "'x' + 1"},        # independent of k
    ]
    compute_values_ast(df, {"k": 2.0}, eqs)
    c_before = _column(df, "C")

    recomputed = compute_values_ast(df, {"k": 3.0}, eqs, changed_constants={"k"})
    assert set(recomputed) == {"A", "B"}     # C is NOT recomputed
    np.testing.assert_allclose(_column(df, "A"), np.arange(1, 6) * 3)
    np.testing.assert_allclose(_column(df, "B"), np.arange(1, 6) * 3 + 1)
    np.testing.assert_allclose(_column(df, "C"), c_before)


def test_abs_function_supported():
    df = store_from_columns({"x": np.array([-3.0, 2.0, -1.0])})
    computed = compute_values_ast(df, {}, [{"y": "abs('x')"}])
    assert computed == ["y"]
    np.testing.assert_allclose(_column(df, "y"), [3.0, 2.0, 1.0])


def test_unresolvable_equation_is_skipped():
    df = store_from_columns({"x": np.arange(3, dtype=float)})
    eqs = [{"y": "'missing_col' * 2"}, {"z": "'x' + 1"}]
    computed = compute_values_ast(df, {}, eqs)
    assert computed == ["z"]         # y references a column that doesn't exist
    assert df.find("y") < 0


def test_constant_vs_column_resolution():
    # 'Bg' is a constant; 'Sg' is a column. A column takes precedence if a name
    # is both, matching the legacy engine.
    df = store_from_columns({"Sg": np.array([10.0, 20.0])})
    computed = compute_values_ast(df, {"Bg": 1.5}, [{"Fg": "'Sg' - 'Bg'"}])
    assert computed == ["Fg"]
    np.testing.assert_allclose(_column(df, "Fg"), [8.5, 18.5])


def test_disallowed_expression_is_dropped_not_executed():
    """Only whitelisted arithmetic runs; anything else is skipped, not eval'd."""
    df = store_from_columns({"x": np.arange(3, dtype=float)})
    # attribute access / arbitrary call is not in the whitelist
    computed = compute_values_ast(df, {}, [{"y": "'x'.__class__"}])
    assert computed == []
    assert df.find("y") < 0


def test_graph_reports_resolvable_and_order():
    eqs = [{"A": "'x' * 2"}, {"B": "'A' + 1"}]
    g = EquationGraph(eqs, columns=["x"], constant_keys=[])
    out_order = [e.out_key for e in g._ordered]
    assert out_order == ["A", "B"]


def test_validate_equation_accepts_known_names():
    ok, msg = validate_equation(
        "'Sg' - 'Bg'", known_columns=["Sg"], known_constants=["Bg"]
    )
    assert ok and msg is None


def test_validate_equation_accepts_left_of_pipe_column():
    # Column headers can carry a "Name | unit" suffix; the left side resolves.
    ok, msg = validate_equation("'Green Count Rate' * 2", known_columns=["Green Count Rate | kHz"])
    assert ok, msg


def test_validate_equation_accepts_forward_output_reference():
    ok, _ = validate_equation("'E' + 1", known_outputs=["E"])
    assert ok


def test_validate_equation_flags_unknown_name():
    ok, msg = validate_equation("'nope' + 1", known_columns=["x"])
    assert not ok
    assert "nope" in msg


def test_validate_equation_flags_syntax_error():
    ok, msg = validate_equation("'x' +", known_columns=["x"])
    assert not ok
    assert "syntax" in msg.lower()


def test_validate_equation_flags_disallowed_node():
    ok, msg = validate_equation("'x'.__class__", known_columns=["x"])
    assert not ok
    assert "disallowed" in msg.lower()


def test_validate_equation_flags_empty():
    ok, msg = validate_equation("   ", known_columns=["x"])
    assert not ok
    assert "empty" in msg.lower()


if __name__ == "__main__":  # pragma: no cover
    pytest.main([__file__, "-q"])
