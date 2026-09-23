"""ndX in a browser tab: ``python -m ndxplorer.app.web``.

Builds the emtk app (:func:`ndxplorer.app.frame.make_app`) into a page --
Pyodide runs it, the browser's WebGPU draws it -- and serves it::

    python -m ndxplorer.app.web                       # build, serve on :8795, open a tab
    python -m ndxplorer.app.web --no-open --port 8800
    python -m ndxplorer.app.web --wheels ~/wheels/imp-*.whl   # one more local wheel
    python -m ndxplorer.app.web --build-only --out site/      # a static site to host

Every :mod:`emtk.web.serve` option works; this only presets the bundle.

What the page carries
---------------------
* **ndxplorer** (without its tests) and **emtk**, as the archive;
* **chisurf**'s Qt-free core (``chisurf.core``, ``chisurf.settings``) and
  **mmfdb**'s runtime config, which that core reads at import. The GUI, the
  plugins and the server stay behind (:data:`CHISURF_KEEP`, :data:`MMFDB_KEEP`);
* from the Pyodide distribution: numpy, scipy, PyYAML, matplotlib, Pillow, and
  ``lzma`` (a stdlib module Pyodide ships apart; ``chisurf.core.fio`` imports it);
* **tttrlib**'s Pyodide wheel (:func:`find_tttrlib_wheel`) -- every data
  source is a ``tttrlib.DataStore``;
* any further ``--wheels``: IMP (with ``IMP.bff``, the fitting-parameter
  runtime) when a Pyodide build of it exists. Without it the page boots
  anyway; Gaussian Fit and the overlay curves say on their tabs why they are
  off, as they do in any environment without IMP.

Data comes in by dropping a file (a ``.bur``, a ``.csv``) or a whole
burst-analysis folder on the view, or through *Mount folder...* (Chrome);
a save is a download.
"""

from __future__ import annotations

import glob
import os
import pathlib
import sys
from typing import Iterable, Optional, Sequence

__all__ = [
    "APP",
    "CHISURF_KEEP",
    "DEFAULT_PORT",
    "MMFDB_KEEP",
    "PYODIDE_PACKAGES",
    "TTTRLIB_WHEEL_GLOBS",
    "bundle",
    "find_tttrlib_wheel",
    "main",
]

#: The factory the page mounts.
APP = "ndxplorer.app.frame:make_app"

#: Not emtk's 8788 (other emtk pages) nor 8765 (ChiSurf's command port).
DEFAULT_PORT = 8795

#: Loaded from the Pyodide distribution.
PYODIDE_PACKAGES = ("numpy", "scipy", "pyyaml", "matplotlib", "Pillow", "lzma")

#: The parts of the ``chisurf`` package the page ships: what the Qt-free core
#: imports (``chisurf/__init__`` reaches ``_bundled_packages``, ``core`` and
#: ``settings``; ``chisurf.logging`` it defines itself). Everything else --
#: ``gui``, ``plugins``, ``server``, ``macros``, ``startup``, ``history`` -- is
#: Qt, sockets or both.
CHISURF_KEEP = ("__init__.py", "_bundled_packages.py", "settings", "core")

#: The parts of ``mmfdb`` the page ships: its root re-exports ``config``, which
#: ``chisurf.core.settings`` reads; the database layer is never imported.
MMFDB_KEEP = ("__init__.py", "config.py")

#: Where a tttrlib Pyodide wheel is looked for when ``$NDX_TTTRLIB_WHEEL`` is
#: not set: a tttrlib checkout's ``dist/pyodide`` (``pyodide build`` puts it
#: there), first match wins.
TTTRLIB_WHEEL_GLOBS = (
    "~/dev/worktrees/tttrlib-pyodide/dist/pyodide/tttrlib-*-pyodide_*_wasm32.whl",
    "~/dev/tttrlib/dist/pyodide/tttrlib-*-pyodide_*_wasm32.whl",
)


def find_tttrlib_wheel(patterns: Iterable[str] = TTTRLIB_WHEEL_GLOBS) -> pathlib.Path:
    """The tttrlib wheel built for Pyodide: ``$NDX_TTTRLIB_WHEEL``, else the newest
    match of *patterns*.

    Raises
    ------
    FileNotFoundError
        If there is none. A page without tttrlib boots and then cannot open a
        single file, so the build stops here instead.
    """
    named = os.environ.get("NDX_TTTRLIB_WHEEL")
    if named:
        path = pathlib.Path(os.path.expanduser(named))
        if not path.is_file():
            raise FileNotFoundError(f"$NDX_TTTRLIB_WHEEL={named}: no such file")
        return path
    for pattern in patterns:
        matches = sorted(glob.glob(os.path.expanduser(pattern)), key=os.path.getmtime)
        if matches:
            return pathlib.Path(matches[-1])
    raise FileNotFoundError(
        "no tttrlib wheel for Pyodide found; build one (pyodide build in a tttrlib "
        "checkout) and point $NDX_TTTRLIB_WHEEL at it, or pass --no-tttrlib-wheel "
        "with --wheels PATH")


def _package_dir(name: str) -> Optional[pathlib.Path]:
    """The directory of the regular package *name*, or ``None`` if it is not installed.

    Raises
    ------
    FileNotFoundError
        If *name* resolves to a namespace package: a stray directory of that
        name (``~/chisurf`` when run from ``~``; ``python -m`` puts the working
        directory first on ``sys.path``) shadowing the real one. Packing it
        would ship an empty package and the page would fail at import.
    """
    import importlib.util

    spec = importlib.util.find_spec(name)
    if spec is None:
        return None
    if not spec.origin or not spec.origin.endswith("__init__.py"):
        where = ", ".join(map(str, spec.submodule_search_locations or []))
        raise FileNotFoundError(
            f"{name!r} resolves to a namespace package ({where}), a directory that "
            f"shadows the installed {name}; run from another directory")
    return pathlib.Path(spec.origin).resolve().parent


def _exclude_all_but(name: str, keep: Sequence[str]) -> list[str]:
    """Archive prefixes that leave only *keep* of package *name* (a directory
    entry is excluded as ``name/entry/``, a file as ``name/entry``)."""
    root = _package_dir(name)
    if root is None:
        return []
    out = []
    for entry in sorted(root.iterdir()):
        if entry.name in keep or entry.name == "__pycache__":
            continue
        out.append(f"{name}/{entry.name}/" if entry.is_dir() else f"{name}/{entry.name}")
    return out


def bundle(tttrlib_wheel: bool = True):
    """The :class:`emtk.web.serve.Bundle` for ndX: app, dependencies, wheels."""
    from emtk.web.serve import DEFAULT_PYODIDE_PACKAGES, Bundle

    extra, exclude = [], ["ndxplorer/tests/"]
    for name, keep in (("chisurf", CHISURF_KEEP), ("mmfdb", MMFDB_KEEP)):
        if _package_dir(name) is not None:
            extra.append(name)
            exclude += _exclude_all_but(name, keep)
    pyodide = list(DEFAULT_PYODIDE_PACKAGES)
    pyodide += [p for p in PYODIDE_PACKAGES if p not in pyodide]
    return Bundle(
        app=APP,
        packages=["ndxplorer"],
        extra_packages=extra,
        pyodide_packages=pyodide,
        wheels=[find_tttrlib_wheel()] if tttrlib_wheel else [],
        exclude=tuple(exclude),
        title="ndX",
        ready_message="ready -- drop a burst folder, .bur or .csv on the view",
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    """``python -m ndxplorer.app.web [emtk.web.serve options] [--no-tttrlib-wheel]``."""
    from emtk.web import serve

    argv = list(sys.argv[1:] if argv is None else argv)
    tttrlib_wheel = "--no-tttrlib-wheel" not in argv
    argv = [a for a in argv if a != "--no-tttrlib-wheel"]
    if not any(a == "--port" or a.startswith("--port=") for a in argv):
        argv += ["--port", str(DEFAULT_PORT)]
    return serve.main(argv, base=bundle(tttrlib_wheel=tttrlib_wheel))


if __name__ == "__main__":  # pragma: no cover - a dev server
    sys.exit(main())
