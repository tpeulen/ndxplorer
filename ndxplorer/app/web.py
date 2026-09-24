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
* **chisurf**'s Qt-free core (``chisurf.core``, ``chisurf.settings``),
  **mmfdb**'s runtime config, which that core reads at import, and **chimol**'s
  readers (``chimol.io``): ``chisurf.core.fitting.fit`` imports every experiment
  type, and the modelling one reaches ``chisurf.core.fio.structure``, which takes
  its atom dtype from ``chimol.io.atoms``. The GUI, the plugins, the server and
  chimol's viewer stay behind (:data:`CHISURF_KEEP`, :data:`MMFDB_KEEP`,
  :data:`CHIMOL_KEEP`);
* from the Pyodide distribution: numpy, scipy, PyYAML, matplotlib, Pillow,
  and ``lzma`` (a stdlib module Pyodide ships apart; ``chisurf.core.fio``
  imports it). No scikit-learn: Find structure's PCA is NumPy;
* **tttrlib**'s Pyodide wheel -- every data source is a ``tttrlib.DataStore``,
  and Find structure's HDBSCAN and K-means are its kernels;
* **IMP.bff**'s Pyodide wheel (the IMP-free core, ``import IMP, IMP.bff``) --
  the port runtime behind chisurf's fitting parameters: the Parameters tab,
  the overlay curves, the curve fit and Gaussian Fit. Without it the page boots
  anyway and those say on their tabs why they are off;
* any further ``--wheels``.

The wheels are found by :func:`find_wheel` (:data:`WHEELS`): an environment
variable naming the file, else the newest match under a checkout's
``dist/pyodide``.

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
    "CHIMOL_KEEP",
    "WHEELS",
    "bundle",
    "find_wheel",
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

#: The parts of ``chimol`` the page ships: its readers, which ``chisurf.core``
#: imports (``chimol.io.atoms``, ``chimol.io.dcd``); the viewer does not come.
CHIMOL_KEEP = ("__init__.py", "io")

#: The Pyodide wheels a page needs, by name: ``(environment variable, globs,
#: required)``. The variable names the file; otherwise the newest match of the
#: globs (a checkout's ``dist/pyodide``, where ``pyodide build`` puts it) wins.
#: A missing required wheel stops the build; a missing optional one is said.
WHEELS = {
    "tttrlib": ("NDX_TTTRLIB_WHEEL", (
        "~/dev/worktrees/tttrlib-pyodide/dist/pyodide/tttrlib-*-pyodide_*_wasm32.whl",
        "~/dev/tttrlib/dist/pyodide/tttrlib-*-pyodide_*_wasm32.whl",
    ), True),
    "IMP.bff": ("NDX_IMPBFF_WHEEL", (
        "~/dev/worktrees/imp.bff-pyodide/dist/pyodide/imp_bff-*-pyodide_*_wasm32.whl",
        "~/dev/imp.bff/dist/pyodide/imp_bff-*-pyodide_*_wasm32.whl",
    ), False),
}


def find_wheel(name: str) -> Optional[pathlib.Path]:
    """The Pyodide wheel of *name* (a key of :data:`WHEELS`), or ``None``.

    Raises
    ------
    FileNotFoundError
        If the environment variable names a file that is not there, or a
        required wheel (tttrlib: a page without it cannot open a single file)
        is not found.
    """
    variable, patterns, required = WHEELS[name]
    named = os.environ.get(variable)
    if named:
        path = pathlib.Path(os.path.expanduser(named))
        if not path.is_file():
            raise FileNotFoundError(f"${variable}={named}: no such file")
        return path
    for pattern in patterns:
        matches = sorted(glob.glob(os.path.expanduser(pattern)), key=os.path.getmtime)
        if matches:
            return pathlib.Path(matches[-1])
    if required:
        raise FileNotFoundError(
            f"no {name} wheel for Pyodide found; build one (pyodide build in a {name} "
            f"checkout) and point ${variable} at it, or pass --no-{name.lower()}-wheel "
            "with --wheels PATH")
    return None


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


def bundle(tttrlib_wheel: bool = True, impbff_wheel: bool = True):
    """The :class:`emtk.web.serve.Bundle` for ndX: app, dependencies, wheels."""
    from emtk.web.serve import DEFAULT_PYODIDE_PACKAGES, Bundle

    extra, exclude = [], ["ndxplorer/tests/"]
    for name, keep in (("chisurf", CHISURF_KEEP), ("mmfdb", MMFDB_KEEP),
                       ("chimol", CHIMOL_KEEP)):
        if _package_dir(name) is not None:
            extra.append(name)
            exclude += _exclude_all_but(name, keep)
    pyodide = list(DEFAULT_PYODIDE_PACKAGES)
    pyodide += [p for p in PYODIDE_PACKAGES if p not in pyodide]
    wheels = []
    for name, wanted in (("tttrlib", tttrlib_wheel), ("IMP.bff", impbff_wheel)):
        wheel = find_wheel(name) if wanted else None
        if wheel is not None:
            wheels.append(wheel)
        elif wanted:
            print(f"no {name} wheel for Pyodide found (${WHEELS[name][0]}); "
                  "the page boots without it")
    return Bundle(
        app=APP,
        packages=["ndxplorer"],
        extra_packages=extra,
        pyodide_packages=pyodide,
        wheels=wheels,
        exclude=tuple(exclude),
        title="ndX",
        ready_message="ready -- drop a burst folder, .bur or .csv on the view",
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    """``python -m ndxplorer.app.web [emtk.web.serve options] [--no-tttrlib-wheel]
    [--no-imp.bff-wheel]``."""
    from emtk.web import serve

    argv = list(sys.argv[1:] if argv is None else argv)
    flags = {"tttrlib": "--no-tttrlib-wheel", "impbff": "--no-imp.bff-wheel"}
    off = {key for key, flag in flags.items() if flag in argv}
    argv = [a for a in argv if a not in flags.values()]
    if not any(a == "--port" or a.startswith("--port=") for a in argv):
        argv += ["--port", str(DEFAULT_PORT)]
    return serve.main(argv, base=bundle(tttrlib_wheel="tttrlib" not in off,
                                        impbff_wheel="impbff" not in off))


if __name__ == "__main__":  # pragma: no cover - a dev server
    sys.exit(main())
