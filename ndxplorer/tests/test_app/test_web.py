"""The browser build (``python -m ndxplorer.app.web``): what the page carries.

The page itself is checked in a browser (Chromium with WebGPU); what can be
checked here is the archive -- the one place a missing module or a shipped
Qt module is decided, long before a browser console would say so.
"""

from __future__ import annotations

import zipfile

import pytest

pytest.importorskip("emtk.web.serve")


@pytest.fixture(scope="module")
def names(tmp_path_factory):
    from emtk.web.serve import pack_zip

    from ndxplorer.app.web import bundle

    archive = pack_zip(bundle(tttrlib_wheel=False, impbff_wheel=False),
                       tmp_path_factory.mktemp("web") / "app.zip")
    return set(zipfile.ZipFile(archive).namelist())


def test_the_page_carries_the_app_and_its_views(names):
    assert "ndxplorer/app/frame.py" in names
    assert "ndxplorer/app/views/plot_controls.view.json" in names
    assert "emtk/web/page.py" in names
    assert not [n for n in names if n.startswith("ndxplorer/tests/")]


def test_the_page_carries_chisurf_s_core_and_not_its_gui(names):
    pytest.importorskip("chisurf")
    # What the app imports: the fitting parameters (Gaussian Fit, overlays).
    for needed in ("chisurf/__init__.py", "chisurf/_bundled_packages.py",
                   "chisurf/core/parameter.py", "chisurf/core/fitting/parameter.py",
                   "chisurf/core/settings/__init__.py", "mmfdb/config.py",
                   # chisurf.core.fio.structure's atom dtype, via fitting.fit's
                   # import of every experiment type.
                   "chimol/__init__.py", "chimol/io/atoms.py", "chimol/io/dcd.py"):
        assert needed in names, needed
    for prefix in ("chisurf/gui/", "chisurf/plugins/", "chisurf/server/", "mmfdb/store/",
                   "chimol/render/", "chimol/hosts/"):
        assert not [n for n in names if n.startswith(prefix)], prefix


def test_the_page_loads_what_the_core_imports_from_pyodide():
    from ndxplorer.app.web import bundle

    wanted = bundle(tttrlib_wheel=False, impbff_wheel=False).pyodide_packages
    # lzma: chisurf.core.fio imports it, and Pyodide ships it apart from the stdlib.
    # scikit-learn: Find structure's K-means, PCA and HDBSCAN.
    for name in ("numpy", "scipy", "pyyaml", "matplotlib", "Pillow", "lzma", "scikit-learn"):
        assert name in wanted, name


def test_a_shadowing_directory_is_refused(tmp_path, monkeypatch):
    """``python -m`` puts the working directory first on ``sys.path``: run from
    a folder holding a ``chisurf/`` directory, ``chisurf`` is that empty
    namespace package, and the page would ship nothing of it."""
    import sys

    from ndxplorer.app import web

    (tmp_path / "shadowpkg").mkdir()
    monkeypatch.syspath_prepend(str(tmp_path))
    sys.modules.pop("shadowpkg", None)
    with pytest.raises(FileNotFoundError, match="namespace package"):
        web._package_dir("shadowpkg")


def test_without_the_parameter_runtime_the_gaussian_group_says_so(monkeypatch):
    """A page without an IMP wheel imports chisurf's parameter classes but cannot
    make a parameter. The Gaussian group must fail when it is built -- where the
    panel catches it and shows why -- not on the first "add", inside a frame."""
    try:
        import chisurf.core.parameter as parameter
    except Exception as exc:  # noqa: BLE001 - no chisurf, or an IMP build mid-rebuild
        pytest.skip(f"chisurf.core.parameter does not import here: {exc}")
    from ndxplorer.core import gaussian_parameters as gp

    monkeypatch.setattr(parameter, "_bff", None)
    monkeypatch.setattr(parameter, "_bff_import_error", "No module named 'IMP'", raising=False)
    with pytest.raises(ImportError, match="IMP"):
        gp.build_gaussian_group()


def test_the_wheels_are_found_by_variable_and_an_optional_one_may_be_missing(
        tmp_path, monkeypatch):
    from ndxplorer.app import web

    wheel = tmp_path / "imp_bff-0.1-cp313-cp313-pyodide_2025_0_wasm32.whl"
    wheel.write_bytes(b"")
    monkeypatch.setenv("NDX_IMPBFF_WHEEL", str(wheel))
    assert web.find_wheel("IMP.bff") == wheel
    monkeypatch.setenv("NDX_IMPBFF_WHEEL", str(tmp_path / "gone.whl"))
    with pytest.raises(FileNotFoundError):
        web.find_wheel("IMP.bff")
    monkeypatch.delenv("NDX_IMPBFF_WHEEL")
    monkeypatch.setitem(web.WHEELS, "IMP.bff", ("NDX_IMPBFF_WHEEL", (str(tmp_path / "x*.whl"),),
                                                False))
    assert web.find_wheel("IMP.bff") is None
    monkeypatch.setitem(web.WHEELS, "tttrlib", ("NDX_TTTRLIB_WHEEL", (str(tmp_path / "x*.whl"),),
                                                True))
    monkeypatch.delenv("NDX_TTTRLIB_WHEEL", raising=False)
    with pytest.raises(FileNotFoundError):
        web.find_wheel("tttrlib")
