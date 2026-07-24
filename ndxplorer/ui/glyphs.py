"""Canonical action glyphs for ndXplorer labels.

ndXplorer buttons and actions should read the same as ChiSurf's — the same
concept drawn with the same emoji. When ndXplorer runs inside ChiSurf we reuse
ChiSurf's authoritative registry (``chisurf.gui.glyphs.Glyphs``) directly; when
it runs standalone (ndXplorer must not hard-depend on ChiSurf) we fall back to a
local copy of the same glyphs so the UI still looks consistent.

Use :func:`label` to compose a ``"<glyph> Text"`` button/action label so the
spacing is uniform everywhere.
"""

from __future__ import annotations

try:  # Reuse ChiSurf's single source of truth when available.
    from chisurf.gui.glyphs import Glyphs, normalize  # type: ignore

    _HAVE_CHISURF_GLYPHS = True
except Exception:  # pragma: no cover - standalone ndXplorer
    _HAVE_CHISURF_GLYPHS = False

    VS16 = "️"  # emoji variation selector (forces colour presentation)

    class Glyphs:  # noqa: D101 - mirrors chisurf.gui.glyphs.Glyphs (subset)
        # Files / IO
        SAVE = "💾"
        OPEN = "📂"
        FOLDER = "📁"
        IMPORT = "📥"
        EXPORT = "📤"
        COPY = "📋"
        # Edit / list
        ADD = "➕"
        REMOVE = "➖"
        DELETE = "🗑" + VS16
        EDIT = "✏" + VS16
        CLEAR = "🧹"
        CLOSE = "✕"
        # Run / lifecycle
        RUN = "▶" + VS16
        STOP = "⏹" + VS16
        REFRESH = "🔄"
        RESET = "♻" + VS16
        # Status / marks
        CHECK = "✓"
        CHECKBOX_ON = "☑" + VS16
        CHECKBOX_OFF = "☐"
        PENDING = "⏳"
        INFO = "ℹ" + VS16
        # Data / view
        SEARCH = "🔍"
        EYE = "👁" + VS16
        CHART = "📊"
        # Tools / config
        SETTINGS = "⚙" + VS16
        TARGET = "🎯"
        PALETTE = "🎨"
        GRID = "🎛" + VS16
        BRAIN = "🧠"

    def normalize(text: str) -> str:  # type: ignore[misc]
        """No-op normalisation fallback (ChiSurf provides the real one)."""
        return text


def label(glyph: str, text: str) -> str:
    """Return ``"<glyph> text"`` for a button/action label (uniform spacing)."""
    return f"{glyph} {text}" if glyph else text


__all__ = ["Glyphs", "normalize", "label"]
