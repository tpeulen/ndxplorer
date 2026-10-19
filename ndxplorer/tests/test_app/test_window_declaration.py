"""Owner-declared viewer geometry, real hosts and existing ChiSurf saved-size integration."""

import json
import pathlib

import pytest
from ndxplorer.app import frame, launch


@pytest.fixture(autouse=True)
def scratch_settings(tmp_path, monkeypatch):
    """Redirect the existing owner settings seam without depending on a live prototype."""
    import ndxplorer.settings as settings
    import ndxplorer.settings.bundle as bundle

    directory = tmp_path / "settings"
    directory.mkdir()
    monkeypatch.setattr(settings, "get_settings_path", lambda: directory)
    monkeypatch.setattr(bundle, "get_settings_path", lambda: directory)


def test_owner_factory_reads_the_declared_viewer_dimensions():
    """The real toolkit-neutral viewer announces its primary window declaration."""
    app = frame.NdxApp(features=[])
    try:
        spec = json.loads(pathlib.Path(frame.__file__).with_name("window.view.json").read_text())
        assert spec["window"] == {"width": 1200, "height": 800}
        assert app.window_size == (1200, 800)
        assert launch.SIZE == app.window_size
    finally:
        app.close()


def test_owner_factory_consumes_authored_metadata(monkeypatch):
    """A new valid declaration reaches the real factory rather than a duplicate constant."""
    original = frame.load_spec

    def changed(name):
        """Substitute only the authored window dimensions, retaining every control spec."""
        if name == "window":
            return {"sections": [], "window": {"width": 1280, "height": 760}}
        return original(name)

    monkeypatch.setattr(frame, "load_spec", changed)
    app = frame.NdxApp(features=[])
    try:
        assert app.window_size == (1280, 760)
    finally:
        app.close()


@pytest.mark.parametrize("host", ["native", "tk"])
@pytest.mark.parametrize("explicit", [None, (980, 640)])
def test_standalone_launcher_delivers_default_and_preserves_explicit_size(monkeypatch, host, explicit):
    """The real owner launcher lets the native app resolve defaults and preserves --size."""
    received = []

    class Host:
        """Observe constructor delivery without creating a GPU or external display."""

        def __init__(self, app, *, size=None, **kwargs):
            received.append((app.window_size, size))

        def run(self):
            """Return immediately; host creation arguments prove this routing boundary."""

        def close(self):
            """Provide the existing owner exit callback."""

    import emtk.native
    import emtk.tk_host

    monkeypatch.setattr(emtk.native, "NativeHost", Host)
    monkeypatch.setattr(emtk.tk_host, "TkHost", Host)
    assert launch.run(host=host, size=explicit) == 0
    assert received == [((1200, 800), explicit if host == "native" else (explicit or (1200, 800)))]


def test_existing_chisurf_host_geometry_retains_saved_user_size(tmp_path, monkeypatch):
    """The existing optional host seam restores dimensions without an owner persistence subsystem."""
    state = pytest.importorskip("chisurf.emtk.state")
    monkeypatch.setenv("CHISURF_SETTINGS_DIR", str(tmp_path / "chisurf"))
    first = state.attach_native_state("ndx_geometry_contract", frame.NdxApp(features=[]))
    assert first.window_size == (1200, 800)
    first.window_resized(960, 640)
    first.close()
    reopened = state.attach_native_state("ndx_geometry_contract", frame.NdxApp(features=[]))
    try:
        assert reopened.window_size == (960, 640)
    finally:
        reopened.close()
