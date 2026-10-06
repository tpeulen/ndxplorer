"""ndXplorer's settings YAML may embed Python (curve equations) -- never scipy.

The import guards scan ``.py`` files only, so a model defined in YAML is the
one place scipy could come back unseen. ndXplorer runs on NumPy, tttrlib and
chisurf; scipy is not a dependency.
"""

from __future__ import annotations

import pathlib
import re

_SETTINGS = pathlib.Path(__file__).resolve().parents[1] / "settings"
_PATTERN = re.compile(r"(import\s+scipy\b|from\s+scipy\b|\bscipy\.)")


def test_settings_never_import_scipy():
    offenders = [
        str(p.name)
        for p in _SETTINGS.rglob("*.y*ml")
        if _PATTERN.search(p.read_text(encoding="utf-8", errors="replace"))
    ]
    assert not offenders, f"scipy in settings YAML: {offenders}"


def test_scipy_is_not_a_dependency():
    text = (_SETTINGS.parents[1] / "pyproject.toml").read_text(encoding="utf-8")
    deps = text.split("dependencies = [", 1)[1].split("]", 1)[0]
    assert '"scipy"' not in deps
