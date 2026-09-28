"""The analysis view, kept in the measurement: the session feature.

Opening a `.pto` that holds a saved view brings the window back to it -- axes,
gates, clusters, curves, Gaussians, colours, playback, the ranking settings.
The state is collected from the model and every feature
(:mod:`ndxplorer.app.session_state`) and written into the container
(:mod:`ndxplorer.io.session_io`).

When it is written
    File > Save session (Ctrl+S); on leaving the file (another opens, Clear);
    on closing the window -- the last two only in the user's app
    (``NdxApp(session_autosave=True)``: :func:`~ndxplorer.app.frame.make_app`,
    the launcher), never in a test, a capture or a script. Leaving and closing
    write only when the view
    changed since it was restored or last saved, so opening and closing a
    file leaves it untouched. There is no timed autosave: every write is a
    new version in the measurement's short history (the last five), and a
    history of "every ten seconds" would push out the states worth going back
    to; a write also takes the container's lock, which another program
    (ChiSurf) may hold at any moment.
When it is read
    Once per opened table, after it loaded and the other features reset.
    A state saved on another table (columns or rows differ) is applied where
    it still fits; what did not is said in the status line.
In a browser
    The dropped file is an in-memory copy: the state is written into it, and
    File > Download .pto with session hands it back as a download.
"""

from __future__ import annotations

import hashlib
import json
import logging
import pathlib
import shutil
from typing import Any, Callable, Dict, Optional

from . import Feature

__all__ = ["SessionFeature", "create"]

logger = logging.getLogger(__name__)

ACTIONS = ("save_session", "revert_session", "forget_session", "download_session_pto")


class SessionFeature(Feature):
    """Save and restore the analysis view in the `.pto` it belongs to."""

    name = "session"

    def __init__(self, app) -> None:
        super().__init__(app)
        #: id of the table the state was last restored for (restore once each).
        self._source_id: Optional[int] = None
        #: The container of the table on screen, and its identity at load.
        self.container = ""
        self.identity: Dict[str, Any] = {}
        self.columns: list = []
        #: Hash of the view as restored or last saved (``None``: not taken yet).
        self._baseline: Optional[str] = None
        self._baseline_due = False
        #: Colour limits to set once the first recompute has run.
        self._limits: Optional[tuple] = None
        #: The last restore's notes (tests, the status line).
        self.notes: list = []

    # ------------------------------------------------------------- the seam
    def actions(self) -> Dict[str, Callable[[], Any]]:
        return {"save_session": self.save, "revert_session": self.revert,
                "forget_session": self.forget, "download_session_pto": self.download}

    def available(self, action: str) -> Optional[bool]:
        if action in ACTIONS:
            return bool(self.app.model.has_data and self._container())
        return None

    def on_data_changed(self) -> None:
        model = self.app.model
        if not model.has_data or id(model.source) == self._source_id:
            return
        from ...io.session_io import table_identity

        self._source_id = id(model.source)
        self.container = self._container()
        self.columns = list(model.parameter_names)
        self.identity = table_identity(self.columns, model.source.size)
        self._baseline, self._baseline_due, self._limits = None, True, None
        if self.container:
            self.restore()

    def draw_windows(self) -> bool:
        # After the frame's recompute: the colour limits a recompute resets,
        # then what the view looks like "as restored".
        if self._limits is not None and self.app.model.histograms is not None:
            self.app.model.vmin, self.app.model.vmax = self._limits
            self._limits = None
        if self._baseline_due and self._limits is None:
            self._baseline, self._baseline_due = self._hash(), False
        return False

    def on_data_leaving(self) -> None:
        self._save_if_changed()
        self._source_id = None

    def on_close(self) -> None:
        self._save_if_changed()

    # --------------------------------------------------------------- state
    def _container(self) -> str:
        from ...io.fret_calibration_io import container_of

        model = self.app.model
        if not model.has_data:
            return ""
        path = container_of(type("W", (), {"data_source": model.source})())
        return path if path and pathlib.Path(path).is_file() else ""

    def state(self) -> Dict[str, Any]:
        from ..session_state import collect

        return collect(self.app)

    def _hash(self, state: Optional[dict] = None) -> str:
        from ...io.session_io import _jsonable

        state = json.loads(json.dumps(state or self.state(), default=_jsonable))
        # the colour limits follow every recompute: not a change of the view
        for key in ("vmin", "vmax"):
            state.get("view", {}).pop(key, None)
        return hashlib.sha256(json.dumps(state, sort_keys=True).encode("utf-8")).hexdigest()

    def changed(self) -> bool:
        """Whether the view differs from the one restored or last saved."""
        return self._baseline is None or self._hash() != self._baseline

    # --------------------------------------------------------------- saving
    def save(self, quiet: bool = False) -> dict:
        """File > Save session: the view into the measurement, as a new version."""
        from ...io.session_io import payload, save_session

        container = self.container or self._container()
        if not container or not self.app.model.has_data:
            return {"ok": False, "error": "no measurement container"}
        state = self.state()
        result = save_session(container, payload(state, self.identity, self.columns))
        name = pathlib.Path(container).name
        if result["ok"]:
            self._baseline = self._hash(state)
            self.app.show_status(f"Session saved in {name}")
        else:
            why = ("it is open for writing in another program" if result.get("locked")
                   else result.get("error", "unknown error"))
            self.app.show_status(f"Session not saved in {name}: {why}")
            logger.warning("session not saved in %s: %s", container, result.get("error"))
            if not quiet:
                self.app.message = ("Save session", f"The session could not be saved in "
                                    f"{name}: {result.get('error')}")
        return result

    def _save_if_changed(self) -> None:
        if not getattr(self.app, "session_autosave", False):
            return
        if not self.container or not self.app.model.has_data:
            return
        if self._source_id != id(self.app.model.source):
            return
        try:
            if self.changed():
                self.save(quiet=True)
        except Exception:  # noqa: BLE001 - leaving a file must not fail on this
            logger.exception("saving the session of %s", self.container)

    # ------------------------------------------------------------- restoring
    def restore(self) -> Optional[list]:
        """Apply the newest state stored in the container; ``None`` when there is none."""
        from ...io.session_io import latest_session
        from ..session_state import SessionContext, apply, colour_limits

        saved = latest_session(self.container)
        if saved is None:
            return None
        model = self.app.model
        table = dict(saved.get("table") or {})
        same = (table.get("columns_sha256") == self.identity.get("columns_sha256")
                and table.get("n_rows") == self.identity.get("n_rows"))
        ctx = SessionContext(model.parameter_names, model.source.size, saved, same,
                             newer_calibration=self._calibration_newer(saved))
        if not same:
            ctx.skip("saved on another table" if ctx.rows_match else
                     f"saved on {table.get('n_rows')} rows, {model.source.size} now")
        state = dict(saved.get("state") or {})
        apply(self.app, state, ctx)
        self._limits = colour_limits(dict(state.get("view") or {}))
        self._baseline, self._baseline_due = None, True
        self.notes = list(ctx.notes)
        when = str(saved.get("saved_utc", ""))[:16].replace("T", " ")
        text = f"Restored the session saved {when} UTC"
        if ctx.notes:
            text += "; not restored: " + "; ".join(ctx.notes)
        self.app.show_status(text)
        return self.notes

    def _calibration_newer(self, saved: dict) -> bool:
        from ...io.fret_calibration_io import stored_calibrations

        calibrations = stored_calibrations(container=self.container)
        return bool(calibrations) and str(calibrations[-1].get("saved_utc", "")) > \
            str(saved.get("saved_utc", ""))

    def revert(self) -> None:
        """File > Revert to saved session."""
        if self.restore() is None:
            self.app.show_status("This measurement holds no saved session")

    def forget(self) -> None:
        """File > Forget session: remove every stored state from the measurement."""
        from ...io.session_io import forget_sessions

        result = forget_sessions(self.container)
        name = pathlib.Path(self.container).name
        if result["ok"]:
            # the view on screen is the baseline: closing does not write it back
            self._baseline = self._hash()
            self.app.show_status(f"Removed {result['removed']} saved session(s) from {name}")
        else:
            self.app.show_status(f"Could not remove the sessions from {name}: "
                                 f"{result.get('error')}")

    # ------------------------------------------------------------- download
    def download(self) -> None:
        """File > Download .pto with session: the container, the view saved in it.

        In a browser the dropped file is an in-memory copy; this is how the
        user gets it back. On a desktop it saves a copy where the user says.
        """
        if not self.save(quiet=False).get("ok"):
            return
        service = getattr(self.app, "io_service", None)
        if service is None:
            return
        name = pathlib.Path(self.container).name
        if service.browser:
            with open(self.container, "rb") as handle:
                service.download(name, handle.read(), "application/octet-stream")
            return
        source = self.container
        service.ask_save("Save .pto with session", [("Measurement", ["*.pto"])], name,
                         lambda path: shutil.copyfile(source, path))


def create(app) -> SessionFeature:
    return SessionFeature(app)
