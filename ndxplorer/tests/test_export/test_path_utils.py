import os
from pathlib import Path

import pytest

from ndxplorer.export import path_utils

# The \\?\ extended-length and UNC prefixes are a Windows filesystem feature;
# pathlib uses a PosixPath backend on non-Windows regardless of the IS_WINDOWS
# flag, so these two cases can only be exercised on Windows.
windows_only = pytest.mark.skipif(os.name != "nt", reason="Windows-only path semantics")


def test_normalize_export_path_expands_user_and_resolves(tmp_path, monkeypatch):
    fake_home = tmp_path / "home"
    fake_home.mkdir()
    monkeypatch.setenv("HOME", str(fake_home))
    monkeypatch.setenv("USERPROFILE", str(fake_home))

    target = path_utils.normalize_export_path("~/exports/result.csv")

    assert target.parent == fake_home / "exports"
    assert target.name == "result.csv"


@windows_only
def test_normalize_handles_long_windows_path(monkeypatch):
    monkeypatch.setattr(path_utils, "IS_WINDOWS", True)
    monkeypatch.setattr(path_utils, "LONG_PATH_THRESHOLD", 8)

    long_path = Path(r"C:\very\long\path\file.csv")
    normalized = path_utils.normalize_export_path(long_path)

    assert str(normalized).startswith(r"\\?\C:\\"), str(normalized)


@windows_only
def test_normalize_handles_unc_paths(monkeypatch):
    monkeypatch.setattr(path_utils, "IS_WINDOWS", True)

    unc_path = Path(r"\\server\share\folder\file.csv")
    normalized = path_utils.normalize_export_path(unc_path)

    assert str(normalized).startswith(r"\\?\UNC\server\share"), str(normalized)
