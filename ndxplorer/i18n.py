"""ndX's translation domain on :mod:`emtk.i18n`.

ndX speaks English in its source and is translated through emtk's catalogue
mechanism, the same one ChiSurf and every emtk app use -- there is no ndX-only
translation machinery. This module only binds that mechanism to ndX:

* :data:`DOMAIN` -- ndX's strings live in their own catalogue domain,
  ``"ndxplorer"``, so they cannot collide with a host's catalogue;
* :func:`tr` -- translate an imperative string (a status line, a dialog
  title, a ``{placeholder}`` template; format *after* translating);
* :func:`mark` -- mark a string declared as data (a menu label, a dock
  title) for extraction without translating it; whoever draws it translates
  it at draw time, so a language switch shows on the next frame;
* the catalogues in ``ndxplorer/locale`` are registered on import.

Which language: hosted (ChiSurf embeds ndX), the host has already set emtk's
language and ndX follows it -- :func:`select_language` is never called on that
path. Standalone, :func:`select_language` takes the user's choice from
``language.json`` in the settings folder (Settings > Language); without one
emtk's own default stands (``EMTK_LANG``, else the operating system's locale).

ndX's window draws inside :class:`emtk.i18n.use_domain` (``DOMAIN``), so the
labels emtk's widgets translate for it -- view.json forms, dock titles, menu
rows -- resolve in ndX's catalogue before a host's.

The strings and their translations are extracted with::

    python -m emtk.i18n.extract ndxplorer --domain ndxplorer --locales de fr \\
        --out ndxplorer/locale

Column names, equation symbols and constants are data and stay as they are.
"""

from __future__ import annotations

import json
import locale as _locale
import os
import pathlib
from typing import Optional, Tuple

from emtk import i18n as _i18n

__all__ = ["DOMAIN", "LOCALE_DIR", "LANGUAGES", "LANGUAGE_FILE", "tr", "mark",
           "select_language", "saved_language", "save_language", "system_language"]

#: ndX's catalogue domain.
DOMAIN = "ndxplorer"
#: The catalogues, one per language, as the extractor writes them.
LOCALE_DIR = pathlib.Path(__file__).resolve().parent / "locale"
#: The languages ndX ships, with their own names (Settings > Language).
LANGUAGES: Tuple[Tuple[str, str], ...] = (("en", "English"), ("de", "Deutsch"),
                                         ("fr", "Français"))
#: Where the standalone app keeps the user's choice, in the settings folder.
LANGUAGE_FILE = "language.json"


def tr(source: str, context: Optional[str] = None) -> str:
    """*source* in the active language (itself when untranslated)."""
    return _i18n.tr(source, context, domain=DOMAIN)


def mark(source: str) -> str:
    """*source* unchanged, marked for extraction; translated where it is drawn."""
    return _i18n.mark(source)


def system_language() -> str:
    """The operating system's language code (``"de"`` for ``de_DE.UTF-8``); ``"en"``.

    What Settings > Language > *System language* switches back to while running.
    """
    for name in ("EMTK_LANG", "LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(name, "")
        if value and value not in ("C", "POSIX"):
            return value.split(":")[0].split(".")[0].replace("_", "-").split("-")[0].lower()
    try:
        value = _locale.getlocale()[0] or ""
    except (ValueError, TypeError):
        value = ""
    return value.replace("_", "-").split("-")[0].lower() or "en"


def _language_file() -> pathlib.Path:
    from .settings import get_settings_path

    return get_settings_path() / LANGUAGE_FILE


def saved_language() -> str:
    """The language chosen in Settings > Language; ``""`` when none was."""
    try:
        data = json.loads(_language_file().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ""
    return str(data.get("language", "") or "") if isinstance(data, dict) else ""


def save_language(code: str) -> None:
    """Remember *code* (``""`` = follow the system) and switch to it now."""
    _language_file().write_text(json.dumps({"language": str(code or "")}), encoding="utf-8")
    _i18n.set_language(str(code or "") or system_language())


def select_language() -> str:
    """Standalone start: the saved choice, else emtk's default. Returns the language."""
    code = saved_language()
    if code:
        _i18n.set_language(code)
    return _i18n.language()


_i18n.add_catalogue(DOMAIN, LOCALE_DIR)
