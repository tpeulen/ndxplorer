"""ndXplorer has no Qt: the emtk app is its only GUI.

The Qt window (``core/plot_main.py``, ``ui/``, ``widgets/``, the pyqtgraph
plotting modules) was deleted after commit 990ebe2; ``tools/parity/README.md``
says how to rebuild the Qt baseline from that commit. Two checks keep it gone:

* every module of the package imports in a fresh interpreter in which the Qt
  bindings and pyqtgraph cannot be imported at all;
* no source file imports one of them -- not at module level, not inside a
  function, and (outside the tests) not through ``importlib`` either, so a
  lazy import that the first check never executes cannot bring Qt back.
"""

from __future__ import annotations

import ast
import pathlib
import subprocess
import sys
import textwrap

PACKAGE = pathlib.Path(__file__).resolve().parents[1]

#: Top-level names that must never be imported.
BLOCKED = ("qtpy", "PyQt5", "PyQt6", "PySide2", "PySide6", "pyqtgraph")

_IMPORT_ALL = textwrap.dedent('''
    import importlib, pkgutil, sys
    for name in {blocked!r}:
        sys.modules[name] = None  # ``import`` raises ImportError
    import ndxplorer
    failed = []
    for info in pkgutil.walk_packages(ndxplorer.__path__, "ndxplorer."):
        try:
            importlib.import_module(info.name)
        except Exception as exc:
            failed.append(f"{{info.name}}: {{exc!r}}")
    loaded = sorted(m for m in sys.modules
                    if m.split(".")[0] in {blocked!r} and sys.modules[m] is not None)
    print("FAILED", failed)
    print("LOADED", loaded)
''')


def test_every_module_imports_with_qt_blocked():
    result = subprocess.run(
        [sys.executable, "-c", _IMPORT_ALL.format(blocked=BLOCKED)],
        capture_output=True, text=True, timeout=600, cwd=str(PACKAGE.parent),
    )
    assert result.returncode == 0, result.stderr[-3000:]
    assert "FAILED []" in result.stdout, result.stdout[-4000:]
    assert "LOADED []" in result.stdout, result.stdout[-2000:]


def _qt_imports(path: pathlib.Path, dynamic: bool):
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in ast.walk(tree):
        names = []
        if isinstance(node, ast.Import):
            names = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            names = [node.module]
        elif dynamic and isinstance(node, ast.Call) and node.args:
            func = node.func
            called = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
            first = node.args[0]
            if called in ("import_module", "__import__", "find_spec") and \
                    isinstance(first, ast.Constant) and isinstance(first.value, str):
                if called == "find_spec":
                    continue  # asking whether a package exists imports nothing
                names = [first.value]
        for name in names:
            if name.split(".")[0] in BLOCKED:
                yield f"{path.relative_to(PACKAGE.parent)}:{node.lineno}: {name}"


def test_no_source_file_imports_qt():
    found = []
    for path in sorted(PACKAGE.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        found.extend(_qt_imports(path, dynamic="tests" not in path.relative_to(PACKAGE).parts))
    assert not found, "Qt is imported here:\n" + "\n".join(found)


def test_the_qt_gui_is_gone():
    for gone in ("core/plot_main.py", "plotting/plot_main.ui",
                 "plotting/pg_image_widget.py", "plotting/curve_overlay.py"):
        assert not (PACKAGE / gone).exists(), gone
    for package in ("ui", "widgets"):  # a stale __pycache__ may stay behind
        assert not list((PACKAGE / package).glob("*.py")), package
