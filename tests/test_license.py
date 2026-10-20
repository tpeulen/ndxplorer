"""The licence ndXplorer reports is the licence it ships under.

The distribution moved from GPL to MIT; the About box kept saying "GPL-2.1"
because the text was written out by hand. These tests tie every place that
names the licence to ``pyproject.toml``.
"""

from __future__ import annotations

import pathlib
import re

import ndxplorer

ROOT = pathlib.Path(__file__).resolve().parents[1]


def _pyproject_license() -> str:
    text = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    match = re.search(r'^license\s*=\s*"([^"]+)"', text, re.M)
    assert match, "pyproject.toml declares no license string"
    return match.group(1)


def test_the_package_licence_is_the_declared_one():
    assert ndxplorer.__license__ == _pyproject_license()


def test_the_licence_file_matches():
    first = (ROOT / "LICENSE").read_text(encoding="utf-8").splitlines()[0]
    assert first.split()[0] == ndxplorer.__license__


def test_no_shipped_text_names_the_old_licence():
    """User-visible strings and catalogues never mention GPL.

    Comments that credit a GPL reference implementation (vizrank,
    projection scores) are attribution, not ndXplorer's licence, and are
    not user-visible; only string literals and catalogues are checked.
    """
    offenders = []
    for path in (ROOT / "ndxplorer").rglob("*"):
        if path.suffix not in {".ts", ".json", ".md"} or not path.is_file():
            continue
        if "GPL" in path.read_text(encoding="utf-8", errors="ignore"):
            offenders.append(str(path.relative_to(ROOT)))
    settings = (ROOT / "ndxplorer" / "app" / "features" / "settings.py").read_text(
        encoding="utf-8"
    )
    if re.search(r'tr\("[^"]*GPL', settings):
        offenders.append("ndxplorer/app/features/settings.py")
    assert not offenders, offenders


def test_the_conda_recipe_reads_the_licence_string():
    meta = (ROOT / "conda-recipe" / "meta.yaml").read_text(encoding="utf-8")
    assert "project['license']" in meta
