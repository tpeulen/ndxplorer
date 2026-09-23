"""Overlay curves: an equation, or a traced function, drawn over the 2-D map.

An overlay curve is ``y = f(x; p)`` typed as text (``x*tauD0*kf/((tauD0-x)*PhiA)``)
or a Python function that traces a parametric line and returns ``(x, y)`` (a
static FRET line from a distance distribution). Its free parameters are a
chisurf :class:`FittingParameterGroup` (see :mod:`ndxplorer.core.curve_parameters`),
so they have value / fixed / bounds and can be crosslinked to a fit.

Everything here is toolkit-free: both windows -- the Qt one
(``ndxplorer/plotting/curve_overlay.py``) and the emtk one
(``ndxplorer/app/features/overlays.py``) -- parse, evaluate, sample and save
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
    "CurveEvaluator",
    "OverlayCurve",
    "equation_parameter_names",
    "signature_defaults",
    "filled_text",
    "predefined_equation_paths",
    "load_predefined_equations",
    "sample_x",
    "curve_points",
    "write_curves_csv",
    "next_curve_title",
]

#: The first entry of the equation list: a curve the user types.
CUSTOM_EQUATION = "Custom Equation"

#: Names that appear in an equation but are NOT free parameters: the independent
#: variables and the maths functions/constants the evaluator provides. Without
#: this, a regex that harvests identifiers turns ``exp``/``sqrt``/``pi`` into
#: spurious parameters and corrupts the "filled" equation display.
NON_PARAMETER_NAMES = frozenset({
    "x", "y", "pi", "e", "inf", "nan", "np",
    "exp", "expm1", "log", "log2", "log10", "log1p", "sqrt", "cbrt", "square",
    "abs", "sign", "power", "hypot", "mod", "fmod", "sin", "cos", "tan",
    "arcsin", "arccos", "arctan", "arctan2", "sinh", "cosh", "tanh",
    "deg2rad", "rad2deg", "floor", "ceil", "trunc", "round", "clip", "where",
    "minimum", "maximum", "heaviside", "nan_to_num", "sinc", "erf",
})

#: What an equation or a function body may call, besides its parameters.
_NAMESPACE = {
    "np": np, "sin": np.sin, "cos": np.cos, "tan": np.tan, "exp": np.exp,
    "log": np.log, "log10": np.log10, "sqrt": np.sqrt, "pi": np.pi, "e": np.e,
}


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
    names = set(re.findall(r"\b([a-zA-Z][a-zA-Z0-9_]*)\b", text))
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
    import yaml

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
        return [e for e in entries if isinstance(e, dict) and "name" in e]
    logging.warning("Curve overlay predefined equations not found")
    return []


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


class OverlayCurve:
    """One overlay curve: its text, its parameters, its colour and visibility.

    Parameters
    ----------
    title : str
        ``"FD/FA vs tau (static line) 1"``.
    text : str
        The equation, or the ``def`` source of a function curve.
    is_function : bool
        Whether *text* defines a function.
    color : str
        ``#rrggbb``.
    """

    _SEQ = [0]

    def __init__(self, title: str, text: str = "x", is_function: bool = False,
                 color: str = "#ff0000") -> None:
        OverlayCurve._SEQ[0] += 1
        self.title = str(title)
        self.is_function = bool(is_function)
        self.color = str(color)
        self.visible = True
        self.evaluator = CurveEvaluator()
        self.function: Optional[Callable] = None
        self.error = ""
        self.group = None
        self.owner_id = f"ndxplorer.overlay.{OverlayCurve._SEQ[0]}"
        self._registered = False
        self.text = ""
        self.set_text(text)

    # ---------------------------------------------------------- equation
    def set_text(self, text: str) -> None:
        """A new equation: re-derive the parameters (surviving ones keep their state)."""
        from . import curve_parameters as cp

        self.text = str(text)
        self.error = ""
        names: List[str] = []
        if self.is_function:
            try:
                self.function = self.evaluator.compile_function(self.text)
                names = self.evaluator.get_function_parameters(self.function)
            except Exception as exc:  # noqa: BLE001 - shown to the user
                self.function = None
                self.error = f"cannot compile the function: {exc}"
        else:
            names = equation_parameter_names(self.text)
        defaults = signature_defaults(self.function)
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

    @property
    def curve_evaluator(self) -> CurveEvaluator:
        return self.evaluator

    @property
    def parameter_group(self):
        """The curve's :class:`FittingParameterGroup`: what a fit optimises."""
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
        return filled_text(self.text, self.get_parameters(),
                           self.function if self.is_function else None)

    def points(self, num_points: int, x_edges, y_edges, x_log=False, y_log=False):
        """``(x, y)`` to draw over the displayed histogram; see :func:`curve_points`."""
        x, y = curve_points(self.evaluator, self.equation, self.get_parameters(), num_points,
                            x_edges, y_edges, x_log, y_log)
        self.error = self.evaluator.last_error or ("" if not self.is_function or self.function
                                                   else self.error)
        return x, y

    # ------------------------------------------------------ crosslinking
    def register(self) -> None:
        """Publish the parameters so another table's link menu can reach them."""
        try:
            from chisurf.core.parameter_group_registry import register_parameter_group

            self.group.name = self.title
            register_parameter_group(self.group, owner_id=self.owner_id,
                                     label=f"ndX {self.title}")
            self._registered = True
        except Exception as exc:  # noqa: BLE001 - linking is optional
            logging.debug("Could not register curve parameter group: %s", exc)

    def unregister(self) -> None:
        """Drop the registry entry; a deleted curve takes its links with it."""
        if not self._registered:
            return
        try:
            from chisurf.core.parameter_group_registry import unregister_parameter_group

            unregister_parameter_group(self.owner_id)
        except Exception:  # noqa: BLE001
            pass
        self._registered = False

    @classmethod
    def from_entry(cls, entry: Mapping[str, Any], title: str) -> "OverlayCurve":
        """A curve from a predefined-equation entry (``equation`` or ``function``)."""
        if "function" in entry:
            curve = cls(title, str(entry["function"]), is_function=True)
        else:
            curve = cls(title, str(entry.get("equation", "x")))
        if entry.get("parameters"):
            curve.set_parameters(entry["parameters"], entry.get("ranges") or {})
        return curve
