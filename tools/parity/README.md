# ndXplorer Qt → emtk parity harness

The emtk port of ndXplorer (`ndxplorer/app`) has to show that no feature was lost
compared with the Qt app (`ndxplorer/core/plot_main.py:NDXplorer`). This
directory holds the evidence:

| File | Role |
|---|---|
| `scenarios.json` | Ordered scenarios: data file, steps, and named captures. Both sides replay the same list. |
| `capture_qt.py` | Replays each scenario on the real Qt window and writes the baseline PNGs to `parity/qt/`. |
| `features.md` | Checklist of every user-facing control/option/column per scenario. The port ticks these off. |
| `compare.py` | Builds `parity/report.html`: Qt and emtk images side by side, with the status taken from `features.md`. |

Parity is judged on the **control inventory, not on pixels**. The port is expected
to change the layout; it may not lose a control. A missing control blocks the
port. A deliberate difference is marked `[~]` with a note that says what replaced
the control.

## Run

```bash
PY=~/mambaforge/envs/arm64/bin/python   # the arm64 conda env: baseline screenshots must come from it
$PY tools/parity/capture_qt.py                     # all scenarios -> parity/qt/
$PY tools/parity/capture_qt.py -s gate_rectangle   # one scenario (repeat -s for more)
$PY tools/parity/capture_qt.py --list
python3 tools/parity/compare.py                    # -> parity/report.html (add --embed for one file)
```

`capture_qt.py` runs each scenario in its own subprocess. Each subprocess gets:

- a 1400×900 window;
- `QT_QPA_PLATFORM=offscreen`, which renders pyqtgraph correctly;
- a scratch `$HOME`, so the shipped default settings are used instead of your own `~/.ndxplorer`;
- `PYTHONPATH` pointing at the sibling sources ChiSurf needs: `chisurf`, `mmfdb`, `chinet`, `imp-tricks`, `~/dev/chimol`.

**Why chimol matters.** Without `chimol`, the equation columns (Sg, Proximity ratio, FRET efficiency…) are silently missing, and the default axes fall back to the first column.

## Baseline provenance

The baseline was taken from commit `44da1f2`, the last commit before the emtk port started. Running from an export of that commit keeps the port's concurrent edits in the working tree out of the baseline:

```bash
git archive 44da1f2 ndxplorer | tar -x -C /tmp/ndx_qt
echo "44da1f2" > /tmp/ndx_qt/.parity-revision
$PY tools/parity/capture_qt.py --app-root /tmp/ndx_qt
```

`parity/qt/index.json` records which revision each run used (`app_revision`), and every `<id>.log.json` records the `ndxplorer` package that was actually imported.

**Where the data comes from.**

- Datasets are real files from the repository and `~/dev/tttr-data` (see `datasets` in `scenarios.json`).
- One dataset is generated on first run: the image table `parity/.cache/data/image_test.h5`, built by `tools/make_image_hdf5.py`.

**What the baseline environment lacks.** It has no `umap-learn`, so `umap_run` records the missing-package path rather than a UMAP result.

## The contract for the emtk capture side

1. **One PNG per shot. The file name is the shot's identity:**
   - `parity/emtk/<scenario-id>.png` is the main window at the end of the scenario (the capture named `main`).
   - `parity/emtk/<scenario-id>--<shot>.png` is every other capture, where `<shot>` is the `name` of the `capture` step in `scenarios.json` (for example `menu_file--menu_import.png`, `clustering_dialog--umap.png`).

   The ids and shot names come from `scenarios.json`. Do not rename them. A shot the port cannot produce shows up as MISSING in the report.
2. **Format.** PNG, any size. Use the same window size as the baseline (1400×900) so the images are comparable at a glance.
3. **Same data, same state.** Replay the scenario's steps in the emtk app:
   - Open the same dataset (`datasets` in `scenarios.json`; `$REPO` is `modules/ndxplorer`).
   - Set the same axes, gates and options.
   - Photograph the same surface: the whole window, the dialog or panel that replaced a Qt dialog, or the menu or popover that replaced a Qt menu.

   If a Qt dialog became an inline panel, capture the panel under the dialog's shot name.
4. **Log (optional).** Write `parity/emtk/<scenario-id>.log.json` in the same shape as the Qt one (`status`, `errors`, `captures`). The report shows the Qt log's errors. An emtk log is currently ignored.
5. **Checklist.** Tick `tools/parity/features.md` items as they land:

   | Mark | Meaning |
   |---|---|
   | `[x]` | done |
   | `[~]` | deliberately different; say what replaced the control |
   | `[-]` | intentionally dropped or not applicable; say why |
   | `[ ]` | open |

   A scenario reaches PARITY in the report when every Qt shot has an emtk counterpart and no item is `[ ]`.

## Scenario step vocabulary (`capture_qt.py`)

| op | arguments | what it does (through the real widgets) |
|---|---|---|
| `open` | `action`, `path`, (`via: "cli"`), (`dialog_result`), (`expect_error`), (`timeout`) | Queues `path` as the file dialog's answer and triggers the File > Import action. `via: "cli"` uses `ndx --file` / the drop path instead. Answers the merge dialog with its default, Replace, then waits for data and histograms. With `expect_error` it waits for the "Data Load Error" box instead. |
| `axis` | `axis` (`x`/`y`/`z`/`weight`), `name` | Selects the parameter in the axis combo. |
| `set` | `widget` (Python expression), `value` | Sets a combo box (by text), check box, spin box or line edit. |
| `click` | `widget` | Calls `.click()` on a button. Expressions can use `button('Label', root)`. |
| `trigger` | `action` (`checked`) | Triggers a menu action, or sets a checkable one. |
| `menu` / `close_menus` | `path` (for example `["File","Import"]`) | Pops up a menu bar menu and its submenus. |
| `tab` | `title` | Selects a dock-area tab (Plot controls, Parameters, Overlays, Equations, Gaussian Fit). |
| `drag` | `start`, `end` (fractions of the widget), (`widget`) | Real mouse press/move/release on the 2-D canvas. Makes a rectangular gate, or paints a mask when drawing is on. |
| `canvas_click` | `at`, (`button`) | Left click (for example Gaussian point mode) or right click (context menu). |
| `menu_choice` | `text` | The next context menu returns this entry, as a click on it would. |
| `file_answer` / `dialog_result` / `question_answer` | | What the next file dialog / `exec_()` / question box answers. |
| `dialog_results` / `question_answers` | `values` | Queues: the next `exec_()` calls / questions take these in turn (`[1, 0]`: accept the options, leave the report open; `"yes"`/`"no"`/`"cancel"`). |
| `call` | `code` | Python with `win`, `pc` (plot control), `h` (harness), `button`, `np`, `QtCore`. Used only where no widget exists for the action: setting a view-model value, or a dead button's dialog. |
| `wait`, `wait_until`, `wait_plot` | `ms` / `expr`, `timeout` | Pumps events until time passes, a condition holds, or the plot is idle. |
| `resize_dialog` | `size`, (`target`) | Enlarges a scrolled dialog so every control is on the picture. |
| `capture` | `name`, `target` | Saves a shot. `target` is one of `window` (default), `dialog` (latest opened), `dialog:<Class or title>`, `menu`, or `widget:<expr>`. |

**ChiSurf-hosted scenarios.** A scenario with `"host": "chisurf"` builds the
window as ChiSurf's ribbon opens it: `chisurf/plugins/ndxplorer/__init__.py`
executed with `__name__ == "plugin"`, which adds the Accurate FRET, MMFDB and
ChiSurf Phasor toolbars, the Global View parameters and the calibration
restore on opening a `.pto`. `chisurf.gui.dialogs` is told the session is
interactive so its boxes show. `trigger` accepts `tool('<label>')` (a toolbar
action by its text, glyph ignored); the log records `toolbars` and the final
`constants`. `open` with `"copy": true` opens a copy in the scratch `$HOME`
(the calibration is written into the container), and `$HOME` in a path is that
scratch home (`~` is the real one).

`capture_qt.py` makes blocking Qt calls non-blocking, so a scenario can photograph what they open:

- `exec_()` on dialogs, menus and message boxes shows the widget and returns.
- The static `QFileDialog`, `QMessageBox` and `QInputDialog` helpers show a real (non-native) dialog and return "cancelled", unless an answer was queued.

## Outputs

- `parity/qt/<id>.png`, `parity/qt/<id>--<shot>.png`: the baseline.
- `parity/qt/<id>.log.json`: steps run, captures, errors, message-box texts, and a blank-image check.
- `parity/qt/index.json`: a summary of the run.
- `parity/report.html`: the side-by-side report.

Nothing under `parity/` is committed; it is all in `.gitignore`. The baseline is about 115 PNGs and 10 MB, over the 5 MB budget for committed images, and it can be regenerated exactly from `44da1f2` (see *Baseline provenance*).
