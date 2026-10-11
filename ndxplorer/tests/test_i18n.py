"""ndX is translated: no display string bypasses ``tr()``/``mark()``, and the catalogues hold.

Three guards, all static (nothing of the app is imported to scan it):

* emtk's widget sinks (``emtk.text``, ``im.button``, tooltips, hints …) --
  :func:`emtk.i18n.testing.untranslated_literals`, with ndX's ``emtk.<call>``
  spelling added to the receivers;
* ndX's own display sinks -- the status bar, message boxes, questions,
  dialog and menu titles -- on whatever object they are called;
* message boxes set by assignment (``app.message = (title, text)``).

The allow-list is empty and stays empty: a literal that reaches the screen
is wrapped, or it is not prose (a hidden ``##id``, a number, a symbol).

Then the catalogues: every source string extraction finds has a finished
German and French translation that keeps its ``{placeholders}``.
"""

from __future__ import annotations

import ast
import pathlib
import re

import pytest

PACKAGE = pathlib.Path(__file__).resolve().parents[1]

#: ndX's display sinks: call name -> positional arguments shown to the user.
NDX_SINKS = {
    "show_status": (0,), "status": (0,), "message": (0, 1), "ask": (0, 1), "_report": (0, 1),
    "_ask": (1,), "DialogWindow": (0,), "MenuItem": (0,), "Menu": (0,), "Popup": (),
    "TextWindow": (1, 2), "open_menu": (),
}
#: Keyword arguments of those calls shown to the user.
NDX_KEYWORDS = {"title", "text", "tooltip", "description", "label", "hint", "yes", "no"}


def _prose(node: ast.expr):
    """The text of a string literal or f-string that a user would read, else ``None``."""
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        text = node.value
    elif isinstance(node, ast.JoinedStr):
        text = "".join(v.value for v in node.values
                       if isinstance(v, ast.Constant) and isinstance(v.value, str))
    else:
        return None
    if text.startswith("##") or not any(ch.isalpha() for ch in text.split("##", 1)[0]):
        return None
    return text


def _sources(package=PACKAGE):
    for path in sorted(package.rglob("*.py")):
        parts = path.relative_to(package).parts
        if any(p in ("tests", "test", "__pycache__") for p in parts[:-1]) \
                or path.name.startswith("test_"):
            continue
        yield path.relative_to(package.parent).as_posix(), path.read_text(encoding="utf-8")


def ndx_literals(package=PACKAGE):
    """``path:line: call 'text'`` of every literal at an ndX sink or message assignment."""
    found = []
    for rel, source in _sources(package):
        for node in ast.walk(ast.parse(source, filename=rel)):
            if isinstance(node, ast.Call):
                func = node.func
                name = func.attr if isinstance(func, ast.Attribute) else getattr(func, "id", "")
                if name not in NDX_SINKS:
                    continue
                values = [node.args[i] for i in NDX_SINKS[name] if i < len(node.args)]
                values += [k.value for k in node.keywords if k.arg in NDX_KEYWORDS]
            elif isinstance(node, ast.Assign) and any(
                    isinstance(t, ast.Attribute) and t.attr == "message" for t in node.targets):
                name = "message ="
                values = list(node.value.elts) if isinstance(node.value, ast.Tuple) else []
            else:
                continue
            for value in values:
                text = _prose(value)
                if text is not None:
                    found.append(f"{rel}:{node.lineno}: {name} {text!r}")
    return found


def test_no_untranslated_literal_at_an_emtk_widget():
    """``emtk.text("…")``, ``im.button("…")``, a tooltip or hint: every literal is wrapped."""
    from emtk.i18n.testing import DEFAULT_RECEIVERS, untranslated_literals

    found = untranslated_literals(PACKAGE, receivers=DEFAULT_RECEIVERS | {"emtk"})
    assert [f"{f.path}:{f.line}: {f.call} {f.text!r}" for f in found] == []


def test_no_untranslated_literal_at_an_ndx_sink():
    """Status lines, message boxes, questions, dialog and menu titles: every literal is wrapped."""
    assert ndx_literals() == []


def test_the_guard_sees_what_it_guards(tmp_path):
    """A bare literal at each kind of sink is found; the wrapped spelling is not."""
    package = tmp_path / "pkg"
    package.mkdir()
    (package / "probe.py").write_text(
        'app.show_status("Loaded")\n'
        'self.app.message = ("Error", f"Bad {n}")\n'
        'DialogWindow("Title", key="k")\n'
        'MenuItem(tr("Open"), tooltip="Open a file")\n'
        'feature.ask(tr("Sure?"), tr("Really?"), yes="Go")\n', encoding="utf-8")
    assert sorted(ndx_literals(package)) == sorted([
        "pkg/probe.py:1: show_status 'Loaded'", "pkg/probe.py:2: message = 'Error'",
        "pkg/probe.py:2: message = 'Bad '", "pkg/probe.py:3: DialogWindow 'Title'",
        "pkg/probe.py:4: MenuItem 'Open a file'", "pkg/probe.py:5: ask 'Go'"])
    assert _prose(ast.parse('f"Loaded {n} rows"', mode="eval").body) == "Loaded  rows"
    assert _prose(ast.parse('"##hidden"', mode="eval").body) is None
    assert _prose(ast.parse('"3.14 …"', mode="eval").body) is None
    assert _prose(ast.parse('tr("Open")', mode="eval").body) is None


# --------------------------------------------------------------------------- catalogues
LOCALES = ("de", "fr")
_PLACEHOLDER = re.compile(r"\{[A-Za-z_][A-Za-z0-9_]*(?:[:!][^{}]*)?\}")


def _extracted():
    from emtk.i18n.extract import collect

    from ndxplorer.i18n import DOMAIN

    return {source for (_context, source) in collect(PACKAGE, DOMAIN)}


@pytest.mark.parametrize("language", LOCALES)
def test_every_string_is_translated(language):
    """Each extracted string has a finished translation in ``ndxplorer_<language>.ts``."""
    from emtk.i18n.catalogue import read_messages

    from ndxplorer.i18n import DOMAIN, LOCALE_DIR

    path = LOCALE_DIR / f"{DOMAIN}_{language}.ts"
    messages = {m.source: m for m in read_messages(path)[1]}
    missing = sorted(s for s in _extracted()
                     if s not in messages or not messages[s].translation
                     or messages[s].status in ("unfinished", "obsolete", "vanished"))
    assert missing == [], f"{len(missing)} untranslated in {path.name}: {missing[:20]}"


@pytest.mark.parametrize("language", LOCALES)
def test_translations_keep_their_placeholders(language):
    """``{name}`` in the source is ``{name}`` in the translation: ``.format`` cannot fail."""
    from emtk.i18n.catalogue import read_messages

    from ndxplorer.i18n import DOMAIN, LOCALE_DIR

    broken = [m.source for m in read_messages(LOCALE_DIR / f"{DOMAIN}_{language}.ts")[1]
              if m.translation and m.status not in ("obsolete", "vanished")
              and sorted(_PLACEHOLDER.findall(m.source))
              != sorted(_PLACEHOLDER.findall(m.translation))]
    assert broken == []


def test_the_window_follows_the_language():
    """Switching emtk's language retitles the docks and rebuilds the menus on the next frame;
    the catalogue is ndX's own domain."""
    from emtk import i18n

    from ndxplorer.app.frame import NdxApp
    from ndxplorer.app.docks import PLOT_CONTROLS
    from ndxplorer.i18n import DOMAIN, tr

    before = i18n.language()
    app = NdxApp()
    try:
        i18n.set_language("de")
        app._follow_language()
        assert app.docks.windows[PLOT_CONTROLS].title == tr(PLOT_CONTROLS) != PLOT_CONTROLS
        titles = [menu.label for menu in app.menubar.menus]
        assert titles[0] == i18n.tr("File", domain=DOMAIN) == "Datei"
        i18n.set_language("fr")
        app._follow_language()
        assert app.menubar.menus[0].label == "Fichier"
    finally:
        i18n.set_language(before)
        app.close()
