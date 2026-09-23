#!/usr/bin/env python
"""Side-by-side parity report: Qt baseline vs emtk port, per scenario.

Reads

* ``tools/parity/scenarios.json`` -- the scenario order, titles and descriptions;
* ``parity/qt/``   -- ``<id>.png`` and ``<id>--<shot>.png`` from ``capture_qt.py``;
* ``parity/emtk/`` -- the same file names, written by the emtk capture side;
* ``tools/parity/features.md`` -- the per-scenario feature checklist, whose tick
  marks are the port's status (``[x]`` done, ``[~]`` deliberately different,
  ``[-]`` not applicable / dropped on purpose, ``[ ]`` open);

and writes ``parity/report.html``: one section per scenario with its status and
checklist, and one row per shot with the Qt image left and the emtk image right
(``MISSING`` where the emtk side has not produced that file yet).

Only the standard library is used, so it runs in any Python 3.8+.

Usage::

    python tools/parity/compare.py
    python tools/parity/compare.py --embed        # self-contained HTML (base64 images)
    python tools/parity/compare.py --qt parity/qt --emtk parity/emtk --out parity/report.html
"""

from __future__ import annotations

import argparse
import base64
import html
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]

MARKS = {"x": "done", "X": "done", "~": "different", "-": "n/a", " ": "open"}


# ─────────────────────────────────────────────────────────────────────────────
# Inputs
# ─────────────────────────────────────────────────────────────────────────────
def parse_features(path: Path) -> dict:
    """``{scenario_id: [(state, text), ...]}`` from the markdown checklist.

    A scenario section starts with a level-2 heading whose first word is the
    scenario id (``## gate_rectangle — Rectangular gate ...``); every
    ``- [?] text`` line below it, up to the next level-2 heading, is one item.
    Items in sections that are not scenario ids (e.g. a "Global" section) are
    kept under that heading's first word too.
    """
    out: dict = {}
    current = None
    if not path.exists():
        return out
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"^##\s+`?([A-Za-z0-9_\-]+)`?", line)
        if m:
            current = m.group(1)
            out.setdefault(current, [])
            continue
        m = re.match(r"^\s*[-*]\s+\[([ xX~\-])\]\s+(.*)$", line)
        if m and current:
            out[current].append((MARKS[m.group(1)], m.group(2).strip()))
    return out


def shots_for(sid: str, folder: Path) -> list:
    """File names of one scenario's captures in ``folder``, main shot first."""
    if not folder.is_dir():
        return []
    names = []
    if (folder / f"{sid}.png").exists():
        names.append(f"{sid}.png")
    names += sorted(p.name for p in folder.glob(f"{sid}--*.png"))
    return names


def qt_log(sid: str, folder: Path) -> dict:
    """The Qt run's record of one scenario: its own log, else its index.json entry."""
    p = folder / f"{sid}.log.json"
    try:
        if p.exists():
            return json.loads(p.read_text())
        index = folder / "index.json"
        if index.exists():
            return json.loads(index.read_text()).get("scenarios", {}).get(sid, {})
    except Exception:
        pass
    return {}


# ─────────────────────────────────────────────────────────────────────────────
# Status
# ─────────────────────────────────────────────────────────────────────────────
def scenario_status(items: list, qt_shots: list, emtk_shots: list) -> tuple:
    """(label, css class, detail) for one scenario."""
    counts = {k: 0 for k in ("done", "different", "n/a", "open")}
    for state, _ in items:
        counts[state] += 1
    total = len(items)
    closed = counts["done"] + counts["different"] + counts["n/a"]
    missing = [s for s in qt_shots if s not in emtk_shots]
    detail = f"{closed}/{total} features" + (f", {len(missing)}/{len(qt_shots)} shots missing"
                                             if qt_shots else "")
    if not emtk_shots:
        return "NOT STARTED", "todo", detail
    if missing or counts["open"]:
        return "PARTIAL", "partial", detail
    return "PARITY", "ok", detail


# ─────────────────────────────────────────────────────────────────────────────
# HTML
# ─────────────────────────────────────────────────────────────────────────────
CSS = """
:root { --bg:#fff; --fg:#1d1d1f; --muted:#6e6e73; --line:#d2d2d7; --card:#f5f5f7;
        --ok:#1a7f37; --partial:#9a6700; --todo:#cf222e; --miss:#fff1f0; }
@media (prefers-color-scheme: dark) {
  :root { --bg:#161618; --fg:#f2f2f2; --muted:#a1a1a6; --line:#3a3a3c; --card:#1f1f22;
          --ok:#3fb950; --partial:#d29922; --todo:#f85149; --miss:#3a1d1d; } }
* { box-sizing:border-box; }
body { margin:0; padding:16px; background:var(--bg); color:var(--fg);
       font:14px/1.45 -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; }
h1 { font-size:22px; margin:0 0 4px; } h2 { font-size:18px; margin:0; }
.muted { color:var(--muted); }
table.summary { border-collapse:collapse; width:100%; margin:16px 0 28px; }
table.summary th, table.summary td { border-bottom:1px solid var(--line); padding:5px 8px;
       text-align:left; vertical-align:top; }
.badge { display:inline-block; padding:1px 8px; border-radius:10px; font-size:12px;
         font-weight:600; border:1px solid currentColor; white-space:nowrap; }
.ok { color:var(--ok); } .partial { color:var(--partial); } .todo { color:var(--todo); }
section { border:1px solid var(--line); border-radius:8px; padding:12px; margin:0 0 24px;
          background:var(--card); }
section header { display:flex; gap:12px; align-items:baseline; flex-wrap:wrap; }
.pair { display:grid; grid-template-columns:1fr 1fr; gap:12px; margin-top:12px; }
.pair figure { margin:0; min-width:0; }
.pair figcaption { font-size:12px; color:var(--muted); margin-bottom:4px; word-break:break-all; }
.pair img { max-width:100%; height:auto; border:1px solid var(--line); background:#fff; }
.missing { display:flex; align-items:center; justify-content:center; min-height:160px;
           border:2px dashed var(--todo); color:var(--todo); font-weight:700;
           background:var(--miss); border-radius:6px; letter-spacing:.1em; }
details { margin-top:10px; } summary { cursor:pointer; }
ul.features { margin:6px 0 0; padding-left:20px; columns:2 420px; }
ul.features li { break-inside:avoid; }
li.done::marker { content:"✓ "; color:var(--ok); }
li.different::marker { content:"≈ "; color:var(--partial); }
li.na::marker { content:"– "; color:var(--muted); }
li.open::marker { content:"☐ "; color:var(--todo); }
.warn { color:var(--todo); font-size:12px; }
@media (max-width:760px) { .pair { grid-template-columns:1fr; } }
"""


def img_tag(path: Path, rel_to: Path, embed: bool, alt: str) -> str:
    if embed:
        data = base64.b64encode(path.read_bytes()).decode("ascii")
        src = f"data:image/png;base64,{data}"
    else:
        src = os.path.relpath(path, rel_to).replace(os.sep, "/")
    return (f'<a href="{html.escape(src)}" target="_blank">'
            f'<img loading="lazy" src="{html.escape(src)}" alt="{html.escape(alt)}"></a>')


def build(args) -> str:
    doc = json.loads(Path(args.scenarios).read_text(encoding="utf-8"))
    scenarios = doc["scenarios"]
    features = parse_features(Path(args.features))
    qt_dir, emtk_dir = Path(args.qt), Path(args.emtk)
    out_dir = Path(args.out).resolve().parent

    rows, sections = [], []
    totals = {"ok": 0, "partial": 0, "todo": 0}
    for sc in scenarios:
        sid = sc["id"]
        q = shots_for(sid, qt_dir)
        e = shots_for(sid, emtk_dir)
        items = features.get(sid, [])
        label, css, detail = scenario_status(items, q, e)
        totals[css] += 1
        log = qt_log(sid, qt_dir)
        warn = ""
        if log and log.get("status") not in (None, "ok"):
            warn = (f'<div class="warn">Qt baseline: {html.escape(str(log.get("status")))} — '
                    f'{html.escape("; ".join(log.get("errors", [])[:2]))}</div>')
        rows.append(
            f'<tr><td><a href="#{sid}"><code>{sid}</code></a></td>'
            f'<td>{html.escape(sc.get("title", ""))}</td>'
            f'<td><span class="badge {css}">{label}</span></td>'
            f'<td class="muted">{html.escape(detail)}</td></tr>')

        pairs = []
        for name in q + [n for n in e if n not in q]:
            left = (img_tag(qt_dir / name, out_dir, args.embed, f"Qt {name}")
                    if name in q else '<div class="missing">NO QT BASELINE</div>')
            right = (img_tag(emtk_dir / name, out_dir, args.embed, f"emtk {name}")
                     if name in e else '<div class="missing">MISSING</div>')
            pairs.append(
                f'<div class="pair"><figure><figcaption>Qt · {html.escape(name)}</figcaption>'
                f'{left}</figure><figure><figcaption>emtk · {html.escape(name)}</figcaption>'
                f'{right}</figure></div>')
        feat = "".join(
            f'<li class="{"na" if st == "n/a" else st}">{html.escape(text)}</li>'
            for st, text in items) or '<li class="open">no checklist in features.md</li>'
        sections.append(
            f'<section id="{sid}"><header><h2><code>{sid}</code> — '
            f'{html.escape(sc.get("title", ""))}</h2>'
            f'<span class="badge {css}">{label}</span>'
            f'<span class="muted">{html.escape(detail)}</span></header>'
            f'<div class="muted">{html.escape(sc.get("description", ""))}</div>{warn}'
            f'<details open><summary>Feature checklist ({len(items)})</summary>'
            f'<ul class="features">{feat}</ul></details>'
            + "".join(pairs) + "</section>")

    glob_items = features.get("global", [])
    glob = ""
    if glob_items:
        glob = ("<section id='global'><header><h2>Global (every scenario)</h2></header>"
                "<ul class='features'>" + "".join(
                    f'<li class="{"na" if st == "n/a" else st}">{html.escape(t)}</li>'
                    for st, t in glob_items) + "</ul></section>")
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>ndXplorer parity</title><style>{CSS}</style></head><body>
<h1>ndXplorer parity: Qt baseline vs emtk port</h1>
<div class="muted">{len(scenarios)} scenarios · parity {totals['ok']} · partial {totals['partial']}
 · not started {totals['todo']} · Qt: <code>{html.escape(str(qt_dir))}</code>
 · emtk: <code>{html.escape(str(emtk_dir))}</code></div>
<table class="summary"><thead><tr><th>Scenario</th><th>Title</th><th>Status</th><th>Detail</th>
</tr></thead><tbody>{''.join(rows)}</tbody></table>
{glob}
{''.join(sections)}
</body></html>"""


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--qt", default=str(REPO / "parity" / "qt"))
    ap.add_argument("--emtk", default=str(REPO / "parity" / "emtk"))
    ap.add_argument("--features", default=str(HERE / "features.md"))
    ap.add_argument("--scenarios", default=str(HERE / "scenarios.json"))
    ap.add_argument("--out", default=str(REPO / "parity" / "report.html"))
    ap.add_argument("--embed", action="store_true",
                    help="inline the PNGs as base64 (self-contained, large)")
    args = ap.parse_args(argv)
    page = build(args)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(page, encoding="utf-8")
    print(f"wrote {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
