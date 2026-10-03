"""Overlay curves: an equation, or a traced function, drawn over the 2-D map.

An overlay curve is ``y = f(x; p)`` typed as text (``x*tauD0*kf/((tauD0-x)*PhiA)``)
or a Python function that traces a parametric line and returns ``(x, y)`` (a
static FRET line from a distance distribution), a **parametric** line
``(x(t), y(t))`` for ``t`` in ``[t0, t1]`` (the phasor's universal circle, a
FRET trajectory), or a **point set**: markers at listed ``t`` values, labelled
(lifetime points on the circle), or a **data** line: tabulated ``x``, ``y``
arrays another tool computed (ChiSurf's FRET lines), without parameters.
Parametric curves and point sets are specs
(``x``, ``y``, ``where``, ``t``, ``labels``) compiled to the same traced-function
contract a ``def`` has, so drawing, the CSV, population-wise curves and the fit
take all kinds alike. Its free parameters are a
:class:`~ndxplorer.core.parameters.ParameterGroup` (see
:mod:`ndxplorer.core.curve_parameters`), so they have value / fixed / bounds and
can be crosslinked to another parameter (with ChiSurf present, to a fit's).

Everything here is toolkit-free: the app's Overlays tab
(``ndxplorer/app/features/overlays.py``) parses, evaluates, samples and saves
curves through this module.
"""

from __future__ import annotations

import csv
import inspect
import pathlib
import re
import textwrap
from collections import OrderedDict
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import numpy as np

from ..logging_config import logging

__all__ = [
    "NON_PARAMETER_NAMES",
    "CUSTOM_EQUATION",
    "KINDS",
    "TRACED_KINDS",
    "SPEC_KINDS",
    "data_spec",
    "CurveEvaluator",
    "parse_where",
    "spec_parameter_names",
    "compile_spec",
    "spec_labels",
    "spec_t",
    "spec_function_source",
    "OverlayCurve",
    "equation_parameter_names",
    "signature_defaults",
    "filled_text",
    "predefined_equation_paths",
    "load_predefined_equations",
    "predefined_equations_with_added",
    "sample_x",
    "curve_points",
    "write_curves_csv",
    "next_curve_title",
    "population_colour",
    "population_sources",
    "population_labels",
    "population_parameter_sets",
]

#: The first entry of the equation list: a curve the user types.
CUSTOM_EQUATION = "Custom Equation"

#: Names that appear in an equation but are NOT free parameters: the independent
#: variables and the maths functions/constants the evaluator provides. Without
#: this, a regex that harvests identifiers turns ``exp``/``sqrt``/``pi`` into
#: spurious parameters and corrupts the "filled" equation display.
NON_PARAMETER_NAMES = frozenset({
    "x", "y", "pi", "e", "inf", "nan", "np", "None", "True", "False",
    "exp", "expm1", "log", "log2", "log10", "log1p", "sqrt", "cbrt", "square",
    "abs", "sign", "power", "hypot", "mod", "fmod", "sin", "cos", "tan",
    "arcsin", "arccos", "arctan", "arctan2", "sinh", "cosh", "tanh",
    "deg2rad", "rad2deg", "floor", "ceil", "trunc", "round", "clip", "where",
    "minimum", "maximum", "heaviside", "nan_to_num", "sinc", "erf",
})

#: What an equation or a function body may call, besides its parameters: every
#: maths name above that numpy has (so ``arctan``, ``where`` or ``clip`` in a curve
#: evaluate instead of turning into a parameter that then fails).
_NAMESPACE = {"np": np, "abs": np.abs, "inf": np.inf, "nan": np.nan}
_NAMESPACE.update({name: getattr(np, name) for name in NON_PARAMETER_NAMES
                   if name not in _NAMESPACE and hasattr(np, name)})

#: A name in an expression; an attribute (``np.linspace``) is not one.
_IDENTIFIER = re.compile(r"(?<![.\w])([a-zA-Z][a-zA-Z0-9_]*)\b")

#: The kinds of overlay curve: ``y = f(x)`` text, a ``def`` that traces itself,
#: a parametric line ``(x(t), y(t))`` for ``t`` in ``[t0, t1]``, and a point set
#: (markers, optionally labelled, at listed ``t`` values), and a data line
#: (tabulated ``x``, ``y`` arrays handed over by another tool).
KINDS = ("equation", "function", "parametric", "points", "data")
#: The kinds drawn from ``(x, y)`` a curve computes itself (not sampled over x).
TRACED_KINDS = ("function", "parametric", "points", "data")
#: The kinds defined by a spec rather than by text.
SPEC_KINDS = ("parametric", "points", "data")
#: The curve variable of a parametric curve or a point set.
T_NAME = "t"


class CurveEvaluator:
    """Evaluate a curve: an equation string, a ``def`` string or a function."""

    def __init__(self) -> None:
        self.last_error: Optional[str] = None
        #: ``def`` source -> compiled function.
        self.compiled_functions: Dict[str, Callable] = {}

    def compile_function(self, function_str: str) -> Callable:
        """Compile the Python function a ``def ...`` string defines.

        Parameters
        ----------
        function_str : str
            The source; indentation is normalised.

        Returns
        -------
        callable
        """
        function_str = textwrap.dedent(function_str)
        if "\n" not in function_str:
            # A one-line definition: put its body on a line of its own.
            function_str = function_str.replace("    ", "\n    ")
            if "\n" not in function_str:
                head, _, body = function_str.partition(":")
                if body:
                    function_str = f"{head.strip()}:\n    {body.strip()}"
        namespace = dict(_NAMESPACE)
        exec(function_str, namespace)  # noqa: S102 - the user's own curve definition
        name = function_str.split("def ", 1)[1].split("(", 1)[0].strip()
        return namespace[name]

    @staticmethod
    def get_function_parameters(function: Callable) -> List[str]:
        """The parameter names of *function*, in signature order."""
        return list(inspect.signature(function).parameters.keys())

    def evaluate(self, equation_or_function, x_values, parameters):
        """Evaluate the curve.

        Parameters
        ----------
        equation_or_function : str or callable
            ``"y = 1 - x/tau0"`` (the part after ``=`` is used), a ``def`` string,
            or a function returning ``(x, y)``.
        x_values : numpy.ndarray
            Where an equation is evaluated.
        parameters : mapping
            Parameter values by name.

        Returns
        -------
        tuple or numpy.ndarray
            ``(x, y)`` for a function, ``y`` for an equation.
        """
        self.last_error = None
        if callable(equation_or_function):
            return tuple(equation_or_function(**parameters))
        text = str(equation_or_function)
        if text.strip().startswith("def "):
            function = self.compiled_functions.get(text)
            if function is None:
                function = self.compiled_functions[text] = self.compile_function(text)
            return tuple(function(**parameters))
        if "=" in text:
            text = text.split("=", 1)[1].strip()
        local = dict(_NAMESPACE, x=x_values)
        local.update(parameters)
        return eval(text, {"__builtins__": {}}, local)  # noqa: S307 - arithmetic only


def equation_parameter_names(text: str) -> List[str]:
    """The free parameters of an equation: its identifiers minus x and the maths names."""
    if "=" in text:
        text = text.split("=", 1)[1]
    names = set(_IDENTIFIER.findall(text))
    return sorted(names - NON_PARAMETER_NAMES)


def signature_defaults(function: Optional[Callable]) -> Dict[str, float]:
    """Starting values a function curve declares in its own signature.

    ``def static_fret_line(forster_radius=52.0, ..., num_points=500)`` says what
    those parameters are; falling back to a generic 1.0 traced a line with a
    single point, which cannot be drawn or fitted.
    """
    if function is None:
        return {}
    defaults = {}
    for name, p in inspect.signature(function).parameters.items():
        if p.default is not inspect.Parameter.empty:
            try:
                defaults[name] = float(p.default)
            except (TypeError, ValueError):
                continue
    return defaults


def filled_text(text: str, values: Mapping[str, Any], function: Optional[Callable] = None,
                formatted: Optional[Mapping[str, str]] = None) -> str:
    """The curve with its parameter values written in.

    Parameters
    ----------
    text : str
        The equation (``y =`` prefix optional).
    values : mapping
        Parameter values.
    function : callable, optional
        For a function curve: shown as ``name(p=v, ...)`` instead.
    formatted : mapping, optional
        Value spellings to use; ``%.4e`` otherwise.
    """
    shown = {}
    for name, value in values.items():
        if formatted is not None and name in formatted:
            shown[name] = str(formatted[name])
            continue
        try:
            shown[name] = f"{float(value):.4e}"
        except (TypeError, ValueError):
            shown[name] = str(value)
    if function is not None:
        return f"{function.__name__}(" + ", ".join(f"{k}={v}" for k, v in shown.items()) + ")"
    if "=" in text:
        text = text.split("=", 1)[1].strip()
    for name, spelled in shown.items():
        text = re.sub(r"\b" + re.escape(name) + r"\b", spelled, text)
    return text


# ------------------------------------------------- parametric curves and points
def parse_where(text: Any) -> List[Tuple[str, str]]:
    """``[(name, expression)]`` from ``"omega = 2*pi*f\\ntau = tan(t)/omega"``.

    Definitions are separated by new lines or ``;`` and evaluated in order, so
    a later one may use an earlier one. A mapping is accepted as well.
    """
    if isinstance(text, Mapping):
        return [(str(k).strip(), str(v).strip()) for k, v in text.items()]
    out = []
    for line in re.split(r"[;\n]", str(text or "")):
        name, sep, expression = line.partition("=")
        if sep and name.strip() and expression.strip():
            out.append((name.strip(), expression.strip()))
    return out


def spec_parameter_names(spec: Mapping[str, Any]) -> List[str]:
    """The free parameters of a parametric / points spec, in order of appearance.

    Every identifier of its ``where``, ``x`` and ``y`` expressions except ``t``,
    the names ``where`` defines and the maths names.
    """
    if spec.get("kind") == "data":
        return []
    where = parse_where(spec.get("where"))
    defined = {name for name, _ in where} | {T_NAME}
    names: List[str] = []
    for text in [e for _, e in where] + [str(spec.get("x", "")), str(spec.get("y", ""))]:
        for name in _IDENTIFIER.findall(text):
            if name not in NON_PARAMETER_NAMES and name not in defined and name not in names:
                names.append(name)
    return names


def spec_t(spec: Mapping[str, Any], samples: int = 256) -> np.ndarray:
    """The ``t`` values: ``samples`` over ``[t0, t1]`` (parametric), the list (points)."""
    values = [float(v) for v in (spec.get("t") or [])]
    if spec.get("kind") == "points":
        return np.asarray(values, dtype=float)
    t0, t1 = values[:2] if len(values) >= 2 else (0.0, 1.0)
    return np.linspace(t0, t1, max(int(samples), 2))


def _evaluate_spec(spec: Mapping[str, Any], values: Mapping[str, float],
                   t: np.ndarray) -> Tuple[np.ndarray, np.ndarray, dict]:
    local = dict(_NAMESPACE)
    local.update({k: float(v) for k, v in values.items()})
    local[T_NAME] = t
    with np.errstate(all="ignore"):
        for name, expression in parse_where(spec.get("where")):
            local[name] = eval(expression, {"__builtins__": {}}, local)  # noqa: S307
        x = eval(str(spec.get("x", T_NAME)), {"__builtins__": {}}, local)  # noqa: S307
        y = eval(str(spec.get("y", T_NAME)), {"__builtins__": {}}, local)  # noqa: S307
    x = np.broadcast_to(np.asarray(x, dtype=float), t.shape).copy()
    y = np.broadcast_to(np.asarray(y, dtype=float), t.shape).copy()
    return x, y, local


def compile_spec(spec: Mapping[str, Any], samples: Callable[[], int] = lambda: 256
                 ) -> Callable[..., Tuple[np.ndarray, np.ndarray]]:
    """``f(**parameters) -> (x, y)`` for a parametric curve or a point set.

    The traced-function contract function curves have, so drawing, the CSV,
    population-wise curves and the curve fit take it as they take a ``def``.

    Parameters
    ----------
    spec : mapping
        ``{"kind": "parametric" | "points", "x", "y", "where", "t", "labels"}``.
    samples : callable
        How many ``t`` a parametric curve is traced with (read on every call).
    """
    spec = dict(spec)
    if spec.get("kind") == "data":
        xs = np.asarray(spec.get("x") or [], dtype=float)
        ys = np.asarray(spec.get("y") or [], dtype=float)

        def tabulated(**_values):
            return xs.copy(), ys.copy()

        tabulated.__name__ = "data"
        return tabulated

    def traced(**values):
        x, y, _ = _evaluate_spec(spec, values, spec_t(spec, samples()))
        return x, y

    traced.__name__ = str(spec.get("kind", "parametric"))
    return traced


def data_spec(x: Iterable[float], y: Iterable[float], source: str = "") -> Dict[str, Any]:
    """A data line's spec: ``x`` and ``y`` as lists of floats, and where they came from.

    Raises
    ------
    ValueError
        When *x* and *y* differ in length or hold fewer than two points.
    """
    xs = [float(v) for v in np.asarray(list(x), dtype=float).ravel()]
    ys = [float(v) for v in np.asarray(list(y), dtype=float).ravel()]
    if len(xs) != len(ys):
        raise ValueError(f"x has {len(xs)} values, y {len(ys)}")
    if len(xs) < 2:
        raise ValueError("a line needs at least two points")
    spec: Dict[str, Any] = {"kind": "data", "x": xs, "y": ys}
    if source:
        spec["source"] = str(source)
    return spec


def spec_labels(spec: Mapping[str, Any], values: Mapping[str, float]) -> List[str]:
    """One label per point: ``spec["labels"]`` formatted with ``t``, the parameters
    and the ``where`` names at that point (``"{t:g} ns"``); ``[]`` without labels."""
    fmt = str(spec.get("labels") or "")
    if not fmt:
        return []
    t = spec_t(spec)
    try:
        _x, _y, local = _evaluate_spec(spec, values, t)
    except Exception:  # noqa: BLE001 - labels of a broken spec: the bare t
        local = {T_NAME: t}
    out = []
    for i in range(t.size):
        words = {k: (v[i] if isinstance(v, np.ndarray) and v.shape == t.shape else v)
                 for k, v in local.items() if not callable(v)}
        try:
            out.append(fmt.format(**words))
        except Exception:  # noqa: BLE001 - a bad format: say the value
            out.append(f"{t[i]:g}")
    return out


def spec_function_source(spec: Mapping[str, Any], defaults: Mapping[str, float] = (),
                         samples: int = 256) -> str:
    """A parametric spec as the ``def`` source of an equivalent function curve.

    For a window that only knows equation and function curves (the legacy Qt
    overlay widget): the same line, as code the user can read and edit there.
    """
    defaults = dict(defaults or {})
    names = spec_parameter_names(spec)
    args = ", ".join(f"{n}={float(defaults.get(n, 1.0))!r}" for n in names)
    t = [float(v) for v in (spec.get("t") or [0.0, 1.0])]
    lines = [f"def parametric({args}{', ' if args else ''}num_points={int(samples)}):",
             f"    t = np.linspace({t[0]!r}, {t[-1]!r}, int(num_points))"]
    lines += [f"    {n} = {e}" for n, e in parse_where(spec.get("where"))]
    lines += [f"    x = {spec.get('x', 't')}", f"    y = {spec.get('y', 't')}",
              "    return np.broadcast_to(x, t.shape), np.broadcast_to(y, t.shape)"]
    return "\n".join(lines) + "\n"


def predefined_equation_paths() -> List[pathlib.Path]:
    """Where the equation list is looked for: the user's file, then the shipped one.

    The user's ``~/.ndxplorer/curve_equations.yaml`` comes first so that it can
    add curves (the Qt window read the shipped file first, so an edited copy
    was never seen).
    """
    paths: List[pathlib.Path] = []
    try:
        from ..settings import get_settings_path

        paths.append(get_settings_path() / "curve_equations.yaml")
    except Exception:  # noqa: BLE001 - no user folder: the shipped list
        pass
    paths.append(pathlib.Path(__file__).resolve().parents[1] / "settings" / "curve_equations.yaml")
    return paths


def load_predefined_equations(paths: Optional[Sequence[pathlib.Path]] = None) -> List[dict]:
    """The predefined curves: ``[{name, equation | function, parameters, ranges}]``."""
    return predefined_equations_with_added(paths)[0]


def predefined_equations_with_added(paths: Optional[Sequence[pathlib.Path]] = None
                                    ) -> Tuple[List[dict], List[str]]:
    """The predefined curves, and the names the shipped file added to the user's.

    The first readable file wins; a user's file gets the curves shipped since
    it was written appended (:func:`ndxplorer.settings.defaults.merge_curves`:
    a curve the user deleted stays deleted). Nothing is written.
    """
    import yaml

    from ..settings import defaults

    for path in (paths if paths is not None else predefined_equation_paths()):
        path = pathlib.Path(path)
        if not path.exists():
            continue
        try:
            with open(path, "r", encoding="utf-8") as handle:
                entries = yaml.safe_load(handle) or []
        except Exception as exc:  # noqa: BLE001 - a broken file: try the next one
            logging.error("Error loading predefined equations from %s: %s", path, exc)
            continue
        entries = [e for e in entries if isinstance(e, dict) and "name" in e]
        entries, added = defaults.merge_curves(entries, path)
        if added:
            logging.info(defaults.describe_added({"curves": added}))
        return entries, added
    logging.warning("Curve overlay predefined equations not found")
    return [], []


def sample_x(lo: float, hi: float, n: int, log: bool = False) -> np.ndarray:
    """*n* x values over ``[lo, hi]``, evenly spaced on the axis's own scale."""
    n = max(int(n), 2)
    if log:
        lo = lo if lo > 0 else 1e-6
        hi = hi if hi > 0 else 1e-6
        return np.logspace(np.log10(lo), np.log10(hi), n)
    return np.linspace(lo, hi, n)


def curve_points(evaluator: CurveEvaluator, equation, parameters: Mapping[str, float],
                 num_points: int, x_edges, y_edges, x_log: bool = False,
                 y_log: bool = False) -> Tuple[np.ndarray, np.ndarray]:
    """The curve over the displayed x range, in data units, cut to the y range.

    Parameters
    ----------
    evaluator : CurveEvaluator
    equation : str or callable
    parameters : mapping
    num_points : int
        Samples of an equation curve (a function traces its own).
    x_edges, y_edges : array_like
        The displayed histogram's edges; their ends are the axis ranges.
    x_log, y_log : bool
        Logarithmic axes: x is sampled evenly in log, y clamped positive.

    Returns
    -------
    x, y : numpy.ndarray
        Empty when the curve cannot be evaluated.
    """
    x_edges = np.asarray(x_edges, dtype=float)
    y_edges = np.asarray(y_edges, dtype=float)
    xs = sample_x(float(x_edges[0]), float(x_edges[-1]), num_points, x_log)
    try:
        # A line through a pole (x = tauD0) divides by zero there; that is the
        # curve, not an error.
        with np.errstate(all="ignore"):
            result = evaluator.evaluate(equation, xs, dict(parameters))
    except Exception as exc:  # noqa: BLE001 - a bad equation draws nothing
        evaluator.last_error = str(exc)
        return np.empty(0), np.empty(0)
    if result is None:
        return np.empty(0), np.empty(0)
    if isinstance(result, tuple) and len(result) == 2:
        xs, ys = result
    else:
        ys = result
    xs = np.atleast_1d(np.asarray(xs, dtype=float))
    ys = np.asarray(ys, dtype=float)
    if ys.ndim == 0:
        # A constant equation ("2") is a horizontal line.
        ys = np.full(xs.shape, float(ys))
    if ys.shape != xs.shape:
        evaluator.last_error = "x and y differ in length"
        return np.empty(0), np.empty(0)
    if y_log:
        ys = np.maximum(ys, 1e-6)
    keep = np.isfinite(xs) & np.isfinite(ys) & (ys >= y_edges[0]) & (ys <= y_edges[-1])
    return xs[keep], ys[keep]


def write_curves_csv(path, curves: Iterable[Tuple[str, np.ndarray, np.ndarray]]) -> None:
    """Save curves side by side: a name row, an ``x, y`` row, then the points.

    A shorter curve is padded with empty cells.
    """
    curves = list(curves)
    longest = max((len(x) for _, x, _ in curves), default=0)
    with open(path, mode="w", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow([name for name, _, _ in curves for _ in (0, 1)])
        writer.writerow(["x", "y"] * len(curves))
        for i in range(longest):
            row: List[Any] = []
            for _, x, y in curves:
                row.extend([x[i], y[i]] if i < len(x) else ["", ""])
            writer.writerow(row)


def next_curve_title(base: str, titles: Iterable[str]) -> str:
    """``"<base> N"``, N one more than the curves already named after *base*."""
    existing = sum(1 for t in titles if str(t).startswith(base))
    return f"{base} {existing + 1}"


def population_colour(colour: str, position: int, count: int) -> str:
    """The curve's colour tinted for population *position* of *count*.

    The hue stays the curve's, so the populations of one curve read as one
    family; the lightness steps from darker to lighter across them.
    """
    import colorsys

    text = str(colour).lstrip("#")
    try:
        r, g, b = (int(text[i:i + 2], 16) / 255.0 for i in (0, 2, 4))
    except ValueError:
        r, g, b = 1.0, 0.0, 0.0
    if count <= 1:
        return "#%02x%02x%02x" % tuple(int(round(v * 255)) for v in (r, g, b))
    h, _l, s = colorsys.rgb_to_hls(r, g, b)
    lightness = 0.40 + 0.40 * float(position) / float(count - 1)
    rgb = colorsys.hls_to_rgb(h, lightness, max(s, 0.55))
    return "#%02x%02x%02x" % tuple(int(round(v * 255)) for v in rgb)


def population_sources(group) -> "OrderedDict[str, Any]":
    """``{parameter name: vector}`` for a curve's parameters with one value per population.

    A parameter is population-wise when it is a vector itself, or when it
    follows (is linked to) a vector -- a constant ``gamma`` with elements
    ``gamma[...]`` that the curve pins its ``gamma`` to. Every other parameter
    is shared by all populations.
    """
    out: "OrderedDict[str, Any]" = OrderedDict()
    for p in group.parameters_all:
        if getattr(p, "is_vector", False):
            out[p.name] = p
            continue
        master = getattr(p, "link", None)
        if master is not None and getattr(master, "is_vector", False):
            out[p.name] = master
    return out


def population_labels(group) -> List[str]:
    """The populations a curve is drawn for: the union over its vectors, in order."""
    labels: List[str] = []
    for vector in population_sources(group).values():
        labels += [l for l in vector.populations if l not in labels]
    return labels


def population_parameter_sets(group) -> List[Tuple[str, "OrderedDict[str, float]"]]:
    """``[(population, {name: value})]``: each population's parameters.

    A population-wise parameter reads its element for that population (its
    global value where the vector has no such element); a shared one reads its
    own value. Empty when no parameter is population-wise.
    """
    sources = population_sources(group)
    base = OrderedDict((p.name, float(p.value)) for p in group.parameters_all)
    out = []
    for label in population_labels(group):
        values = OrderedDict(base)
        for name, vector in sources.items():
            element = vector.element(label)
            values[name] = float(element.value if element is not None else vector.value)
        out.append((label, values))
    return out


class OverlayCurve:
    """One overlay curve: its definition, its parameters, its colour and visibility.

    Parameters
    ----------
    title : str
        ``"FD/FA vs tau (static line) 1"``.
    text : str
        The equation, or the ``def`` source of a function curve.
    is_function : bool
        Whether *text* defines a function (``kind="function"``).
    color : str
        ``#rrggbb``.
    kind : str, optional
        One of :data:`KINDS`; ``"parametric"`` and ``"points"`` take *spec*.
    spec : mapping, optional
        A parametric curve or point set: ``x`` and ``y`` (expressions of ``t``
        and the parameters), ``where`` (definitions evaluated first), ``t``
        (``[t0, t1]``, or the points' values) and ``labels`` (a format such as
        ``"{t:g} ns"``).
    """

    _SEQ = [0]

    def __init__(self, title: str, text: str = "x", is_function: bool = False,
                 color: str = "#ff0000", kind: Optional[str] = None,
                 spec: Optional[Mapping[str, Any]] = None) -> None:
        OverlayCurve._SEQ[0] += 1
        self.title = str(title)
        self.kind = str(kind) if kind in KINDS else ("function" if is_function else "equation")
        self.color = str(color)
        self.visible = True
        self.evaluator = CurveEvaluator()
        self.function: Optional[Callable] = None
        self.error = ""
        self.group = None
        self.owner_id = f"ndxplorer.overlay.{OverlayCurve._SEQ[0]}"
        self._registered = False
        #: Samples a parametric curve is traced with (the Overlays tab's points).
        self.samples = 256
        #: ``{parameter: constant}``: parameters that follow a constant of the
        #: Parameters tab when it has one (:meth:`link_to`).
        self.links: Dict[str, str] = {}
        self.text = ""
        self.spec: Dict[str, Any] = {}
        if self.kind in SPEC_KINDS:
            self.set_spec(dict(spec or {}, kind=self.kind))
        else:
            self.set_text(text)

    @property
    def is_function(self) -> bool:
        """Whether the curve traces its own ``(x, y)`` (a ``def``, parametric, points)."""
        return self.kind in TRACED_KINDS

    # ---------------------------------------------------------- equation
    def set_text(self, text: str) -> None:
        """A new equation: re-derive the parameters (surviving ones keep their state)."""
        self.text = str(text)
        self.error = ""
        names: List[str] = []
        if self.kind == "function":
            try:
                self.function = self.evaluator.compile_function(self.text)
                names = self.evaluator.get_function_parameters(self.function)
            except Exception as exc:  # noqa: BLE001 - shown to the user
                self.function = None
                self.error = f"cannot compile the function: {exc}"
        else:
            names = equation_parameter_names(self.text)
        self._sync(names, signature_defaults(self.function))

    def set_spec(self, spec: Optional[Mapping[str, Any]] = None, **changes: Any) -> None:
        """A new parametric / points definition (or some of its fields)."""
        self.spec = dict(spec if spec is not None else self.spec, **changes)
        self.spec["kind"] = self.kind
        self.error = ""
        self.function = compile_spec(self.spec, lambda: self.samples)
        if self.kind == "data":
            source = self.spec.get("source")
            self.text = f"{len(self.spec.get('x') or [])} tabulated points" + (
                f" from {source}" if source else "")
        else:
            self.text = f"x = {self.spec.get('x', '')}; y = {self.spec.get('y', '')}"
        self._sync(spec_parameter_names(self.spec), {})

    def _sync(self, names: Sequence[str], defaults: Mapping[str, float]) -> None:
        from . import curve_parameters as cp

        if self.group is None:
            self.group = cp.build_curve_group(names, values=defaults, name=self.title)
        else:
            cp.sync_curve_group(self.group, names, values=defaults)

    @property
    def equation(self):
        """What the evaluator takes: the function, or the equation text."""
        if self.is_function and self.function is not None:
            return self.function
        return self.text

    def get_equation(self):
        """The equation or function (the name the fit builder asks for)."""
        return self.equation

    def labels(self, values: Optional[Mapping[str, float]] = None) -> List[str]:
        """A point set's labels, one per point (``[]`` for other kinds)."""
        if self.kind != "points":
            return []
        return spec_labels(self.spec, self.get_parameters() if values is None else values)

    def link_to(self, group) -> List[str]:
        """Pin the parameters named in :attr:`links` to *group*'s (the constants).

        Parameters
        ----------
        group : ParameterGroup
            Where the constants live; a name it lacks leaves the parameter free.

        Returns
        -------
        list of str
            The parameters now linked.
        """
        targets = getattr(group, "parameters_all_dict", {}) if group is not None else {}
        own = {p.name: p for p in self.group.parameters_all}
        linked = []
        for name, constant in self.links.items():
            if name in own and constant in targets:
                own[name].link = targets[constant]
                linked.append(name)
        return linked

    @property
    def curve_evaluator(self) -> CurveEvaluator:
        return self.evaluator

    @property
    def parameter_group(self):
        """The curve's :class:`~ndxplorer.core.parameters.ParameterGroup`: what a fit optimises."""
        return self.group

    # -------------------------------------------------------- parameters
    def get_parameters(self) -> "OrderedDict[str, float]":
        """``{name: value}``, following crosslinks."""
        from . import curve_parameters as cp

        return cp.curve_values(self.group)

    def set_parameters(self, values: Mapping[str, float],
                       ranges: Optional[Mapping[str, Iterable[float]]] = None) -> None:
        """Write values (and ``[lb, ub]`` ranges, which arm the bounds)."""
        from . import curve_parameters as cp

        cp.apply_curve_values(self.group, values, ranges)

    @property
    def filled(self) -> str:
        """The curve with the values written in."""
        if self.kind == "data":
            return self.text
        if self.kind in ("parametric", "points"):
            values = self.get_parameters()
            parts = [f"{n} = {filled_text(e, values)}" for n, e in parse_where(self.spec.get("where"))]
            parts += [f"{axis} = {filled_text(str(self.spec.get(axis, '')), values)}"
                      for axis in ("x", "y")]
            return "; ".join(parts)
        return filled_text(self.text, self.get_parameters(),
                           self.function if self.kind == "function" else None)

    def points(self, num_points: int, x_edges, y_edges, x_log=False, y_log=False):
        """``(x, y)`` to draw over the displayed histogram; see :func:`curve_points`."""
        self.samples = int(num_points)
        x, y = curve_points(self.evaluator, self.equation, self.get_parameters(), num_points,
                            x_edges, y_edges, x_log, y_log)
        self.error = self.evaluator.last_error or ("" if not self.is_function or self.function
                                                   else self.error)
        return x, y

    # -------------------------------------------------------- populations
    def population_sources(self) -> "OrderedDict[str, Any]":
        """See :func:`population_sources`."""
        return population_sources(self.group)

    def populations(self) -> List[str]:
        """See :func:`population_labels` (``[]``: one global curve)."""
        return population_labels(self.group)

    def population_parameters(self) -> List[Tuple[str, "OrderedDict[str, float]"]]:
        """See :func:`population_parameter_sets`."""
        return population_parameter_sets(self.group)

    def population_points(self, num_points: int, x_edges, y_edges, x_log=False,
                          y_log=False) -> List[Tuple[str, np.ndarray, np.ndarray]]:
        """``[(population, x, y)]``: one curve per population (see :meth:`points`)."""
        out = []
        self.samples = int(num_points)
        for label, values in self.population_parameters():
            x, y = curve_points(self.evaluator, self.equation, values, num_points, x_edges,
                                y_edges, x_log, y_log)
            out.append((label, x, y))
        self.error = self.evaluator.last_error or ""
        return out

    def drawn_curves(self, num_points: int, x_edges, y_edges, x_log=False, y_log=False
                     ) -> List[Tuple[str, str, np.ndarray, np.ndarray]]:
        """``[(name, colour, x, y)]``: what the map shows for this curve.

        One curve per population, named ``"<title> [<population>]"`` and tinted
        (:func:`population_colour`), when a parameter is population-wise; the
        one global curve otherwise.
        """
        if not self.populations():
            x, y = self.points(num_points, x_edges, y_edges, x_log, y_log)
            return [(self.title, self.color, x, y)]
        curves = self.population_points(num_points, x_edges, y_edges, x_log, y_log)
        return [(f"{self.title} [{label}]", population_colour(self.color, i, len(curves)), x, y)
                for i, (label, x, y) in enumerate(curves)]

    def drawn_points(self, x_edges, y_edges
                     ) -> List[Tuple[str, str, np.ndarray, np.ndarray, List[str]]]:
        """``[(name, colour, x, y, labels)]``: a point set's markers inside the axes.

        Like :meth:`drawn_curves` (one set per population), with each marker's
        label kept beside it; ``[]`` for a curve that is not a point set.
        """
        if self.kind != "points" or self.function is None:
            return []
        sets = self.population_parameters() or [("", self.get_parameters())]
        x_edges = np.asarray(x_edges, dtype=float)
        y_edges = np.asarray(y_edges, dtype=float)
        out = []
        for i, (label, values) in enumerate(sets):
            try:
                x, y = self.function(**values)
            except Exception as exc:  # noqa: BLE001 - a bad spec draws nothing
                self.error = str(exc)
                return []
            texts = self.labels(values) or [""] * x.size
            keep = (np.isfinite(x) & np.isfinite(y) & (x >= x_edges[0]) & (x <= x_edges[-1])
                    & (y >= y_edges[0]) & (y <= y_edges[-1]))
            name = f"{self.title} [{label}]" if label else self.title
            colour = population_colour(self.color, i, len(sets)) if label else self.color
            out.append((name, colour, x[keep], y[keep],
                        [t for t, k in zip(texts, keep) if k]))
        return out

    # ------------------------------------------------------ crosslinking
    def register(self) -> None:
        """Publish the parameters so another table's link menu can reach them."""
        from .parameters import register_group

        self.group.name = self.title
        register_group(self.group, self.owner_id, f"ndX {self.title}")
        self._registered = True

    def unregister(self) -> None:
        """Drop the registry entry; a deleted curve takes its links with it."""
        if not self._registered:
            return
        from .parameters import unregister_group

        unregister_group(self.owner_id)
        self._registered = False

    @classmethod
    def from_entry(cls, entry: Mapping[str, Any], title: str) -> "OverlayCurve":
        """A curve from a predefined entry: ``equation``, ``function``,
        ``parametric``, ``points`` or ``data``; with ``parameters`` and ``ranges``,
        ``fixed`` (names held fixed), ``links`` (``{parameter: constant}``,
        see :meth:`link_to`) and ``color``."""
        colour = str(entry.get("color", "#ff0000"))
        if "function" in entry:
            curve = cls(title, str(entry["function"]), is_function=True, color=colour)
        elif any(k in entry for k in SPEC_KINDS):
            kind = next(k for k in SPEC_KINDS if k in entry)
            curve = cls(title, kind=kind, spec=dict(entry[kind] or {}), color=colour)
        else:
            curve = cls(title, str(entry.get("equation", "x")), color=colour)
        if entry.get("parameters"):
            curve.set_parameters(entry["parameters"], entry.get("ranges") or {})
        for p in curve.group.parameters_all:
            if p.name in (entry.get("fixed") or ()):
                p.fixed = True
        curve.links = {str(k): str(v) for k, v in dict(entry.get("links") or {}).items()}
        return curve
