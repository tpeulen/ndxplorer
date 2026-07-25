"""AST-based dependency graph for computing derived burst columns.

Each equation ``{out_key: "expr"}`` has an arithmetic expression whose *quoted*
names refer to columns or constants (e.g. ``"'Fg' / 'Fr'"``,
``"(1.+ 'Fd/Fa' * 'PhiA' / 'PhiD')**(-1.0)"``). This module replaces the old
string-preprocess + ``CaseInsensitiveDict`` + ``eval`` pipeline with:

1. **Parse once** — each expression is parsed to a Python AST; quoted names
   become variables (validated against a small arithmetic whitelist, so nothing
   but ``+ - * / ** -x`` and ``abs`` can run).
2. **Resolve by exact name** — a reference resolves to a column (case-insensitive
   or left-of-``|``) or a constant. There is no prefix/fuzzy matching, so ``'Fr'``
   never binds to ``'FRET-2CDE'`` and the result never depends on which columns
   happen to exist when the cache was built.
3. **Order by dependency** — outputs are evaluated in topological order, so a
   forward reference (equation B using equation A's output, declared earlier)
   is always correct, and a changed constant recomputes exactly its transitive
   dependents.
4. **Evaluate on NumPy arrays** — references are resolved to arrays once and the
   compiled expression runs on them (no per-access dict lookups / Series
   alignment), which is also faster.

The public entry point mirrors the legacy ``compute_values`` contract: it
mutates ``d`` in place and returns the list of output columns it (re)computed.
"""

from __future__ import annotations

import ast
import threading
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

import numpy as np
import pandas as pd

from ..logging_config import logging

# Only arithmetic — no attribute access, comprehensions, arbitrary calls, etc.
_ALLOWED_NODES = (
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant, ast.Name, ast.Load,
    ast.Call, ast.Add, ast.Sub, ast.Mult, ast.Div, ast.Pow, ast.Mod,
    ast.USub, ast.UAdd,
)
_ALLOWED_FUNCS = {"abs"}
_EVAL_GLOBALS = {"__builtins__": {}, "abs": np.abs}


def _normalize_left(name: str) -> str:
    """Return the part of a column/reference name before the first ``|``."""
    return str(name).split("|", 1)[0].strip()


class _RefRewriter(ast.NodeTransformer):
    """Replace each quoted-name string constant with a numbered variable.

    ``'Fg' / 'Fr'`` becomes ``_r0 / _r1`` with ``refs == ['Fg', 'Fr']``; numeric
    literals are left untouched.
    """

    def __init__(self) -> None:
        self.refs: List[str] = []

    def visit_Constant(self, node: ast.Constant):  # noqa: N802 (Qt/ast naming)
        if isinstance(node.value, str):
            idx = len(self.refs)
            self.refs.append(node.value)
            return ast.copy_location(ast.Name(id=f"_r{idx}", ctx=ast.Load()), node)
        return node

    def visit_Call(self, node: ast.Call):  # noqa: N802
        self.generic_visit(node)
        fn = getattr(node.func, "id", None)
        if fn not in _ALLOWED_FUNCS:
            raise ValueError(f"disallowed function call: {fn!r}")
        return node


# expr string -> (compiled code, ordered ref names). Parsing + compiling is the
# expensive step; it depends only on the expression text.
_PARSE_CACHE: Dict[str, Tuple[Any, Tuple[str, ...]]] = {}
_PARSE_LOCK = threading.Lock()


def _parse_expression(expr: str) -> Tuple[Any, Tuple[str, ...]]:
    """Parse ``expr`` into a compiled code object + its ordered references."""
    cached = _PARSE_CACHE.get(expr)
    if cached is not None:
        return cached
    tree = ast.parse(expr, mode="eval")
    rewriter = _RefRewriter()
    new_tree = rewriter.visit(tree)
    ast.fix_missing_locations(new_tree)
    for node in ast.walk(new_tree):
        if not isinstance(node, _ALLOWED_NODES):
            raise ValueError(f"disallowed expression node: {type(node).__name__}")
    code = compile(new_tree, "<equation>", "eval")
    result = (code, tuple(rewriter.refs))
    with _PARSE_LOCK:
        _PARSE_CACHE[expr] = result
    return result


class _Entry:
    """One parsed equation and its resolved reference classification."""

    __slots__ = ("out_key", "code", "refs", "data_refs", "const_refs")

    def __init__(self, out_key, code, refs, data_refs, const_refs):
        self.out_key = out_key
        self.code = code
        self.refs = refs                # ordered, index i -> variable _r{i}
        self.data_refs = data_refs      # ref names that are columns / eq outputs
        self.const_refs = const_refs    # ref names that are constants


class EquationGraph:
    """Parsed, dependency-ordered equation set for a given column/constant schema."""

    def __init__(
        self,
        equations: Sequence[Dict[str, str]],
        columns: Sequence[str],
        constant_keys: Sequence[str],
    ):
        self._entries: List[_Entry] = []
        cols_lower = {str(c).lower() for c in columns}
        cols_left = {_normalize_left(c).lower() for c in columns}
        consts_lower = {str(k).lower() for k in constant_keys}
        eq_keys_lower = {str(k).lower() for m in equations for k in m}

        for mapping in equations:
            for out_key, expr in mapping.items():
                try:
                    code, refs = _parse_expression(str(expr))
                except Exception as exc:  # unparseable -> drop this equation
                    logging.debug("equation_graph: cannot parse %r: %s", out_key, exc)
                    continue
                data_refs: List[str] = []
                const_refs: List[str] = []
                for ref in refs:
                    rl = ref.lower()
                    rll = _normalize_left(ref).lower()
                    if rl in cols_lower or rll in cols_left or rl in eq_keys_lower:
                        data_refs.append(ref)
                    elif rl in consts_lower:
                        const_refs.append(ref)
                    else:
                        # Unknown name: treat as data so a genuinely missing
                        # column makes the equation unresolvable (and skipped),
                        # matching the legacy behaviour.
                        data_refs.append(ref)
                self._entries.append(_Entry(out_key, code, refs, data_refs, const_refs))

        # Resolvability: an output can be computed once every data ref resolves to
        # a real column or another resolvable output, and every constant exists.
        resolvable: Set[str] = set()
        grew = True
        while grew:
            grew = False
            for e in self._entries:
                okl = str(e.out_key).lower()
                if okl in resolvable:
                    continue
                if not all(cr.lower() in consts_lower for cr in e.const_refs):
                    continue
                if all(
                    dr.lower() in cols_lower
                    or _normalize_left(dr).lower() in cols_left
                    or dr.lower() in resolvable
                    for dr in e.data_refs
                ):
                    resolvable.add(okl)
                    grew = True
        self._resolvable = resolvable

        # Topological order among resolvable outputs. Edge A->B when B's data refs
        # include output A. Ties broken by declaration order for determinism.
        out_keys_lower = {str(e.out_key).lower() for e in self._entries}
        order_index = {id(e): i for i, e in enumerate(self._entries)}
        deps: Dict[int, Set[str]] = {}
        for e in self._entries:
            okl = str(e.out_key).lower()
            if okl not in resolvable:
                continue
            deps[id(e)] = {
                dr.lower() for dr in e.data_refs
                if dr.lower() in out_keys_lower and dr.lower() in resolvable and dr.lower() != okl
            }

        resolved_entries = [e for e in self._entries if str(e.out_key).lower() in resolvable]
        done: Set[str] = set()
        ordered: List[_Entry] = []
        remaining = list(resolved_entries)
        while remaining:
            progressed = False
            # stable pass in declaration order
            for e in sorted(remaining, key=lambda x: order_index[id(x)]):
                okl = str(e.out_key).lower()
                if deps[id(e)] <= done:
                    ordered.append(e)
                    done.add(okl)
                    remaining.remove(e)
                    progressed = True
            if not progressed:
                # Cyclic / unsatisfiable remainder — append in declaration order so
                # they are at least attempted (and typically caught at eval).
                ordered.extend(sorted(remaining, key=lambda x: order_index[id(x)]))
                break
        self._ordered = ordered

    # ---- evaluation -------------------------------------------------------
    def compute(
        self,
        d: pd.DataFrame,
        constants: Dict[str, float],
        changed_constants: Optional[Set[str]] = None,
    ) -> List[str]:
        """Evaluate (a subset of) the graph into ``d`` in place; return outputs written."""
        # Which outputs to (re)compute.
        if changed_constants:
            changed_lower = {str(x).lower() for x in changed_constants}
            affected = {
                str(e.out_key).lower()
                for e in self._ordered
                if {cr.lower() for cr in e.const_refs} & changed_lower
            }
            grew = True
            while grew:
                grew = False
                for e in self._ordered:
                    okl = str(e.out_key).lower()
                    if okl in affected:
                        continue
                    if {dr.lower() for dr in e.data_refs} & affected:
                        affected.add(okl)
                        grew = True
            to_compute = affected & self._resolvable
        else:
            to_compute = self._resolvable

        # Case-insensitive / left-of-pipe resolver over the live frame plus the
        # output keys (which appear as columns are written in topological order).
        name_map: Dict[str, str] = {}
        for col in d.columns:
            cs = str(col)
            name_map.setdefault(cs.lower(), col)
            name_map.setdefault(_normalize_left(cs).lower(), col)
        for e in self._ordered:
            name_map.setdefault(str(e.out_key).lower(), e.out_key)
        const_map = {str(k).lower(): k for k in constants}

        arr_cache: Dict[str, np.ndarray] = {}

        def _column_array(ref: str) -> np.ndarray:
            actual = name_map.get(ref.lower()) or name_map.get(_normalize_left(ref).lower())
            if actual is None or actual not in d.columns:
                raise KeyError(ref)
            key = str(actual)
            cached = arr_cache.get(key)
            if cached is not None:
                return cached
            series = d[actual]
            arr = (
                series.to_numpy()
                if pd.api.types.is_numeric_dtype(series)
                else pd.to_numeric(series, errors="coerce").to_numpy()
            )
            arr_cache[key] = arr
            return arr

        computed: List[str] = []
        for e in self._ordered:
            okl = str(e.out_key).lower()
            if okl not in to_compute:
                continue
            try:
                ns = {}
                for i, ref in enumerate(e.refs):
                    if ref in e.const_refs and ref.lower() in const_map:
                        ns[f"_r{i}"] = constants[const_map[ref.lower()]]
                    else:
                        ns[f"_r{i}"] = _column_array(ref)
                with np.errstate(all="ignore"):
                    value = eval(e.code, _EVAL_GLOBALS, ns)  # noqa: S307 (whitelisted AST)
                d[e.out_key] = value
                # A freshly written column invalidates any cached array of the
                # same name (a later equation may read it).
                arr_cache.pop(str(e.out_key), None)
                computed.append(e.out_key)
            except Exception as exc:
                logging.debug("equation_graph: could not compute %r: %s", e.out_key, exc)
        return computed


# Graph cache keyed by (equation identity, column schema, constant keys). The
# schema only affects resolvability, so a stable schema reuses the whole graph.
_GRAPH_CACHE: Dict[Any, EquationGraph] = {}
_GRAPH_LOCK = threading.Lock()


def _graph_key(equations, columns, constant_keys):
    eqs = tuple((k, str(v)) for m in equations for k, v in m.items())
    return (eqs, frozenset(str(c).lower() for c in columns), frozenset(str(k).lower() for k in constant_keys))


def compute_values_ast(
    d: pd.DataFrame,
    constants: Dict[str, float],
    equations: Optional[List[Dict[str, str]]] = None,
    changed_constants: Optional[Set[str]] = None,
) -> List[str]:
    """AST-graph replacement for ``compute_values`` (same mutate-and-return contract)."""
    equations = equations or []
    key = _graph_key(equations, d.columns, constants.keys())
    graph = _GRAPH_CACHE.get(key)
    if graph is None:
        graph = EquationGraph(equations, list(d.columns), list(constants.keys()))
        with _GRAPH_LOCK:
            _GRAPH_CACHE[key] = graph
    return graph.compute(d, constants, changed_constants=changed_constants)


__all__ = ["EquationGraph", "compute_values_ast"]
