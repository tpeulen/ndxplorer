# Clean-room functional spec: ranking candidate views in ndX

Status: spec, step 1 of 2 (written 2026-10-20 by the "dirty" team).
Audience: the implementer who writes the replacements. **You must not open the
modules being replaced, their git history, the third-party toolkit this spec is
replacing, or that toolkit's tests. Do not read the OKF pages
`okf/references/orange3-*.md`, or the ndX/chisurf docstrings and docs that quote
the toolkit. Section 1 is the owner's inventory; you need only section 0's
paths.** Everything you need is in this file and in
the ndX modules listed under "Code you may read".

ndX is MIT-licensed. Three of its modules were written against a GPL-3.0
reference implementation. Rewriting them from this spec removes that
derivation. The spec states *what* the code must do: the observable API, the
mathematics with published references, numbers to test against, and
performance. It deliberately does **not** describe how the old code was laid out.
Where the old behaviour was an arbitrary choice that the literature does not
support, this spec gives the sound behaviour instead and says so (section 9).

---

## 0. Scope

### 0.1 To be rewritten from this spec (delete the old file, write a new one at the same path)

| Path (ndxplorer repo) | What it is for |
|---|---|
| `ndxplorer/analysis/vizrank.py` | Qt-free framework: run states, scored-row value type, background scoring loop, enumeration of single columns and column pairs |
| `ndxplorer/analysis/vizrank_model.py` | Panel model the `vizrank.view.json` spec binds to: settings, Start/Pause, status text, ranked rows, selection |
| `ndxplorer/analysis/projection_scores.py` | Scores (class separation by nearest neighbours, correlation, population separation via `separation.find_populations`), the shared subsample, the column-selection logic, the two concrete rankers |
| `ndxplorer/tests/test_vizrank.py` | Tests of the framework. Write new ones from sections 2 and 7 |
| `ndxplorer/tests/test_projection_scores.py` | Tests of the scores. Write new ones from sections 4 and 7 |

### 0.2 Touched minimally (by the implementer, after the rewrite)

* `ndxplorer/app/features/playback_export.py`: change the docstring of
  `PlaybackExportFeature.follow_axes` so that it no longer credits the
  third-party toolkit. A neutral wording is "Select the ranked row that shows
  the view the user picked by hand." Do not change any code there. It is the
  host, and its contract is in section 5.
* `ndxplorer/analysis/vizrank.view.json` stays as it is. It is ndX's own spec,
  and the names it binds are listed in section 3.

### 0.3 Code you may read (ndX's own and not derived)

`ndxplorer/analysis/projection_rank_model.py` (the subclass of the panel model,
which must keep working unchanged), `ndxplorer/analysis/separation.py`
(`find_populations`, `RobustAxis`), `ndxplorer/utils/axis_helpers.py`
(`robust_axis_range`), `ndxplorer/analysis/vizrank.view.json`,
`ndxplorer/app/features/playback_export.py` (the host),
`ndxplorer/tests/test_separation.py` and
`ndxplorer/tests/test_app/test_playback_export.py`. Those two tests are the
acceptance suite and must stay green unmodified. tttrlib's `KDTree` and
`chisurf.core.math.special` (`rankdata`, `t`) are also available.

---

## 1. Provenance inventory (what was found, across all repos)

The sweep covered `~/dev/chisurf` (`chisurf/`, `modules/ndxplorer`, `okf/`,
`docs/`, `junk/`), `~/dev/emtk`, `~/dev/chimol` and `~/dev/tttrlib`. It searched
for the toolkit's name, its widget file names, the ranking method's name, the
lab's name and city, and the euphemism "GPL visual-analytics toolkit". `junk/`
holds no checkout of the toolkit and no `CHISURF-TAKEN` header naming it.

**Derived (transcribed, ported, or "reimplemented against" the source). Must be rewritten:**

| Repo | File | What was taken |
|---|---|---|
| ndxplorer | `ndxplorer/analysis/vizrank.py` (all 357 lines) | Subclass contract, run states and button captions, worker loop, single and pair enumeration in the toolkit's order. The module docstring says so |
| ndxplorer | `ndxplorer/analysis/vizrank_model.py` (all 468 lines) | Panel state machine: pause on close and resume on reopen, select the best row at the end, restart on a settings change, auto-select a hand-picked view |
| ndxplorer | `ndxplorer/analysis/projection_scores.py` | `knn_separation` and `nearest_neighbours` ("transcribed" from the toolkit's scatter-plot ranker), `correlation` (from its correlation widget), `MIN_K`, the bar colours, the single-column ordering used as the toolkit's attribute heuristic. The rest of the file is ndX's own work, but it is interleaved and is rewritten with the file |
| ndxplorer | `ndxplorer/tests/test_vizrank.py` | Expectations "read from" the toolkit's own test files |
| ndxplorer | `ndxplorer/tests/test_projection_scores.py` | Expectations ported from the toolkit's correlation tests (a missing-value test matrix and iris numbers) |
| ndxplorer | `ndxplorer/app/features/playback_export.py:861` | Docstring credit only ("auto-select"). The code is ndX's own |

**Dependent (calls the derived API, not itself derived). Keep, and do not modify:**

| Repo | File | Note |
|---|---|---|
| ndxplorer | `ndxplorer/analysis/projection_rank_model.py` | Subclasses the panel model and uses its protected surface (section 3.4) |
| ndxplorer | `ndxplorer/app/features/playback_export.py` (`FrameTask`, `frame_runner`, `RankingPanel`) | Host and cooperative runner (section 5) |
| ndxplorer | `ndxplorer/analysis/vizrank.view.json`, `app/features/playback_export/vizrank_help*.md`, `vizrank_guide.json` | ndX's own UI text. No foreign content was found |
| ndxplorer | `ndxplorer/tests/fixtures/iris.csv` | Fisher's iris data (1936), which is public domain. The header says "as shipped with" the toolkit. Re-source it from UCI or R's `datasets::iris` and fix the header |

**Idea-level or trivial (reported to the caller; outside this rewrite):**

| Repo | File | Finding |
|---|---|---|
| chisurf | `chisurf/core/curve.py` (`NCurve.array_attributes`, `unlocked()`) | Write-locked arrays with a scoped `unlocked()`. The OKF page `okf/references/orange3-adopted.md` §1 says the idea and the method name were taken and the code was written independently. Low risk. Owner's call |
| chisurf | `chisurf/gui/task.py` (`run_in_background`), `chisurf/gui/widgets/messages.py` | Recorded as "adopted" from the toolkit's concurrency mixin and widget messages (OKF adopted §2–3). **Both files no longer exist at HEAD**, because they were deleted with the Qt shell (commit 68783966d). They remain in git history only. Note that `vizrank_model.py` still imports `chisurf.gui.task` as its default runner, so its default path is broken today (section 9, D1) |
| chisurf | `chisurf/core/pipeline/store.py:3` | Docstring cites the toolkit's saved-workflow idea. Idea only |
| emtk | `emtk/widgets/data_table.py:239-241` | `POSITIVE_COLOUR` / `NEGATIVE_COLOUR` RGB values, commented as the toolkit's correlation colours. Colour values are not protectable, but strictly they are borrowed. Recommend choosing ndX/emtk palette colours and dropping the comment |
| chisurf | `docs/concepts/multidimensional_exploration.md:221,277,285` | Prose credits ("the design is …'s VizRank"). After the rewrite, cite the published paper (Leban et al. 2006) instead |
| chisurf | `okf/references/orange3-adopted.md`, `orange3-mining.md`, `orange3-lessons.md`, `okf/prds/prd-154.md` W15 | The record of what was taken. Update after the rewrite with the clean-room dates |
| chimol, tttrlib | none | No findings (only colour-name strings and agent-board text) |

Git history: the derived code entered ndxplorer in commit `3d5bd43`. Rewriting
does not remove it from history. Tagging the boundary is covered by PRD-154 W15.

---

## 2. Module A — ranking framework (`ndxplorer/analysis/vizrank.py`)

### 2.1 Purpose

A *ranking* enumerates candidate configurations ("states": one column, or an
ordered pair of columns), gives each a score, and keeps the scored states
sorted best first while scoring runs, so the table fills progressively. The
module is pure Python with no GUI imports.

### 2.2 Names that must exist (imported elsewhere)

* **`RunState`**, an `enum.IntEnum` with at least the members **`Initialized`,
  `Ready`, `Running`, `Paused`, `Hidden`, `Done`**, and the method
  **`can_run() -> bool`**, which is true exactly for `Ready`, `Paused` and
  `Hidden`. The host uses `Running`, `Hidden` and `Done`, and the acceptance
  tests use `Done`. Meanings:
  * `Initialized`: has data, and no ranking has been prepared yet.
  * `Ready`: a ranking is prepared and has not started.
  * `Running`: scoring is in progress.
  * `Paused`: the user stopped it. Reopening the window does **not** resume it.
  * `Hidden`: it stopped because the window closed. Reopening resumes it.
  * `Done`: every state has been scored.
  An extra member for "no data" is allowed.
* **`RankRow`**, a value type describing how one scored state appears in the
  table. Fields, which the rankers in module C build and the panel model reads:
  `cells: tuple[str, ...]` (display text: the score text first, then the
  column labels, then any extra cells), `payload: dict` (what applying the row
  sets), `bar: float | None` (bar length in [0, 1]), `sort_value: float`
  (higher is better), `tooltip: str`, `bar_color: tuple[int,int,int] | None`,
  `value: float | None` (the number the score column shows when it differs
  from `sort_value`, such as a signed r).
* **Base classes for single-column and pair rankers.** Module C's rankers need
  some base. Any internal contract may be chosen, and you are encouraged to
  design your own. Section 4.7 lists only what module C's rankers must expose
  to the panel model and to `projection_rank_model.py`.

Everything else in the module (the score container, the batch type, the
scoring loop, caption tables) is internal. Name and shape it freely.

### 2.3 Required behaviour

1. **Order of rows.** Lower score is better. Scores are totally ordered values,
   usually tuples compared lexicographically. States whose score is "none" are
   left out of the table but are counted as scored. Rows are kept in ascending
   score order. **Among equal scores, the row scored earlier stays first**
   (stable insertion). See section 9, D4.
2. **Enumeration of pairs.** Take the columns in a chosen order
   c₀, c₁, …, c_{m−1}. Each unordered pair appears exactly once, as (cⱼ, cᵢ)
   with j < i. The enumeration must be *prefix-complete*: every pair among the
   first p columns is produced before any pair that involves column p. The count
   is m(m−1)/2, and 0 when m < 2. For m = 4 the required order is
   (0,1), (0,2), (1,2), (0,3), (1,3), (2,3). Because of this property, putting
   promising columns first fills the top of the table early.
3. **Column ordering** may be computed by the ranker before enumeration (for
   example, by scoring each column alone). It is computed at most once per
   ranking.
4. **Scoring loop** (runs in the runner's worker or in time slices):
   * Each state taken from the enumeration is scored, then accounted as
     completed, **before** the loop checks for cancellation. A pause therefore
     never loses or repeats a state, and a continued run resumes with the next
     state. Pausing after any number of states and continuing must give the same
     multiset of (state, score) and the same final order as one uninterrupted run.
   * If scoring one state raises, that state is skipped and counted as both
     completed and *failed*. The ranking goes on.
   * Results go to the GUI side in **batches**, throttled by a monotonic clock
     to at most one batch per `interval` seconds (default 0.05 s). Nothing scored
     may be lost: a final batch is always delivered before the loop returns,
     including after cancellation.
   * Each batch carries the identity ("generation") of the ranking it belongs
     to. The receiving side drops batches from a superseded ranking.
   * The insert position of each row is computed **on the receiving (GUI) side**
     as batches arrive, never inside the worker.

---

## 3. Module B — panel model (`ndxplorer/analysis/vizrank_model.py`)

### 3.1 Module-level names

* `VIEW_SPEC: pathlib.Path` is the path of `vizrank.view.json`, next to the module.
* `load_spec() -> dict` returns the parsed JSON (UTF-8). The host and tests import it.
* `VizRankModel`, the class below.

### 3.2 Constructor

`VizRankModel(on_apply=None, on_change=None, runner=None, defer=None)`

* `on_apply(payload: dict)` is called when the user selects a row, or when the
  best row is auto-applied at the end of a ranking.
* `on_change()` is called after anything visible changed. It must never break a
  run: exceptions from it are caught and logged at debug level.
* `runner` is a callable with the contract in section 5.1. **When it is `None`,
  the model runs the work synchronously inline**, with the same callback order
  as section 5.1. The old default imported a module that no longer exists
  (section 9, D1).
* `defer(fn)` runs `fn` soon but not now. It is used to launch a continued run
  once the previous run has released. When it is `None`, `fn` is called inline.

Initial state: `run_state = RunState.Initialized`, `rows = []`,
`completed = 0`, `failed = 0`, `progress_text = ""`, `error = ""`,
`select_request = None`, and no current run.

### 3.3 Public surface bound by `vizrank.view.json` and used by the host

| Name | Kind | Contract |
|---|---|---|
| `title` | class attribute, str | `"Score views"` (marked for translation). Subclasses override it |
| `rows` | list of dict | Ranked records, best first. **Mutated in place** while a ranking streams (a table renderer rebinds only when the list object changes). A new ranking assigns a new list |
| `ranked_rows()` | method → list | Returns `rows` (the `data_table` `source`) |
| `ranked_columns()` | method → list of dict | First the score column: `{"key": "score", "title": <translated header[0]>, "display": "bar", "range": [lo, hi], "format": "%+.3f" if lo < 0 else "%.3f", "width": 90, "tooltip": …}`. Then one `{"key": "name<i>", "title": <translated header>, "tooltip": …}` per remaining header entry. With no run, the header is `("Score",)` and the range is `[0, 1]` |
| `status_text()` | method → str | `error` if set. Otherwise: `Initialized` → "Press Start to rank every view."; if the total is known → "{done}/{total} scored ({percent} %)"; else "{done} scored". Append " · paused" when `Paused`, " · finished" when `Done`, and " · {n} failed" when failed > 0 |
| `sample_text()` | method → str | Returns `note()` |
| `enabled(name)` | method → bool | `"start"`: not `Running`, and (`can_run()` or `Initialized` or a restart is offered). `"pause"`: `Running`. Anything else: True |
| `restart_offered()` | method → bool | A run exists and `current_settings()` differs from the settings it was prepared with |
| `start_label` | property → str | "Restart with new settings" if a restart is offered. Otherwise "Continue" (`Paused`/`Hidden`), "Finished" (`Done`) or "Start". **The parity scenarios wait for `start_label == 'Finished'`** |
| `progress` | property → int | round(100·completed/total), or 0 when the total is unknown |
| `start()` | action | Start, continue, or restart as appropriate (3.5) |
| `pause()` | action | Pause (3.5) |
| `settings_changed(*_)` | action | If `Running`, pause. Then notify `on_change` |
| `apply_row(record)` | `data_table` `selected_call` | Ignore `None`, and ignore calls made while auto-selecting. Otherwise `on_apply(record["payload"])` |
| `auto_select(wanted: dict)` | method | Set `select_request` to the `key` of the first row whose payload *matches* `wanted` (ranker's match rule, 4.7). Set it to `None` if no row matches. **Do not apply.** Notify |
| `select_request` | attribute | A row key the host should mark as selected without applying it. The host sets it back to `None` after it has selected the row |
| `pause_computation(new_state=RunState.Paused)` | method | Only when `Running`: cancel any pending deferred launch, set the state to `new_state` (the host passes `Hidden` on window close), and cancel the task |
| `dialog_reopened()` | method | Unless `Paused`, behave like `start()`. So a `Hidden` ranking resumes and a `Done` one stays done |
| `shutdown()` | method | Cancel the task and any pending launch, for good |
| `begin_task(message="", maximum=0, cancel=None)` | method | Progress-host hook: returns an object whose text updates `progress_text` and clears it on finish or close. Keep it for runners that look for a progress host. It may be minimal |
| `progress_text`, `error`, `completed`, `failed`, `run_state` | attributes | As named |

**Row record format** (each element of `rows`):
`{"score": float, "key": str, "note": str, "payload": dict, "name0": str, "name1": str, …}`.
`score` is the row's `value` if present, else its `sort_value`. `name<i>` are
the row's `cells[1:]` in order. `key` is a deterministic string that is unique
per payload within a ranking. The view spec uses it as `row_key`. For a dict
payload, use the sorted `k=v` pairs joined by `|`. `note` is the row tooltip
(the spec's `tooltip_key`). The host's tests read `rows[0]["name0"]`,
`["name1"]` and `["name2"]` (the island count for population pairs).

### 3.4 Protected surface used by the subclass `projection_rank_model.ProjectionRankModel` (keep these names)

* Hooks the subclass overrides: `make_ranker() -> ranker` (may raise; the
  message is shown), `current_settings() -> hashable/comparable value`, and
  `note() -> str`.
* `self._run`: `None` before the first prepared ranking. Otherwise an object
  with `.ranker` (the ranker), `.settings` (the `current_settings()` value it was
  prepared with, which the subclass indexes as a tuple, `settings[4]`),
  `.generation` (an int that increases with each prepared ranking; the host keys
  its islands overlay on it), and `.total` (the state count, 0 until known).
* `self._changed()` notifies `on_change` safely.
* `self.set_run_state(state)`.

### 3.5 State machine (observable behaviour)

* **start()**: if a restart is offered, go back to `Initialized`. If
  `Initialized`, *prepare*: cancel any task, increment the generation, clear
  rows, scores, counts and error, take `current_settings()`, call
  `make_ranker()`, call the ranker's `prepare()` **on the calling (GUI) thread**
  (it reads the live table), record the run, and set `Ready`. If preparing
  raises, set `error = "Cannot rank: {error}"`, notify, and stay put. Then, if
  `can_run()`: set `Running`. If the previous task is still running (a fast
  Pause→Continue), do **not** supersede it. Mark "launch when idle" and launch
  through `defer` once that task reports done. Otherwise launch now.
* **The work function** handed to the runner: on its first call for a run,
  obtain the state count and the state enumeration from the ranker. The
  ranker's column selection and ordering run here, so off the GUI thread.
  Publish the total as a partial result of its own kind, so the GUI side sets
  `_run.total`. Then run the scoring loop (2.3.4) over the **shared**
  enumeration, which persists on the run object across calls. A later call, after
  a pause or a time slice, continues it. The work reports its phase with
  `set_text` ("ordering parameters", then "scoring").
* **On each partial batch** for the current generation: for every
  (state, score), increment `completed`. Skip "none" scores. Otherwise insert
  the record at its stable sorted position. Add the batch's failures to
  `failed`. Notify.
* **On result**: only if `Running`, no launch is pending, and
  `completed >= total`: set `Done`. If there are rows and no `select_request`,
  set `select_request` to the first row's key **and apply that row**
  (`on_apply`).
* **On error** (the ranking failed as a whole, not one state): log it, set
  `error = "Ranking failed: {error}"`, and set `Paused`.
* **On task done**: forget the task. If a launch is pending, clear the flag and
  call `defer(launch-if-still-running)`, never from inside the completion
  callback itself. Notify.

---

## 4. Module C — scores and rankers (`ndxplorer/analysis/projection_scores.py`)

### 4.1 Public names (imported by `projection_rank_model.py` and by tests)

`MIN_K` (= 10), `DEFAULT_MAX_ROWS` (= 5000), `MIN_DISTINCT` (= 20),
`DERIVED_RHO` (= 0.98), `METHODS`, `METHOD_HELP`, `ColumnView`, `ClassLabels`,
`RankingTable`, `display_coordinates`, `nearest_neighbours`, `knn_separation`,
`chance_corrected_agreement`, `correlation`, `correlation_ratio`, `is_clock`,
`ColumnSet`, `ProjectionRanker`, `ParameterRanker`. Additional constants used
below: function threshold η²_f = 0.98, curve threshold η²_c = 0.95, clock share
0.9, and bins for η² = 32.

`METHODS: dict[str, tuple[caption, needs_labels, ranks_pairs, ranks_single]]`,
in this order (the panel lists the options in this order, and the first is the
default):

| key | caption | needs labels | pairs | single |
|---|---|---|---|---|
| `"populations"` | "Separation" | no | yes | yes |
| `"correlation"` | "Correlation" | no | yes | no |
| `"separation"` | "Classes" | yes | yes | yes |

`METHOD_HELP: dict[key, str]` holds the three explanatory strings of Appendix A.
Captions and help strings are marked for translation (`ndxplorer.i18n.mark`).
The existing `de`/`fr` catalogues translate exactly the Appendix A strings, so
keep them verbatim.

### 4.2 Data types

* `ColumnView(name: str, scale: str = "lin", lo: float|None = None, hi: float|None = None)`
  is a dataclass. `scale` is `"lin"` or `"log"`. A `None` bound means "the
  automatic range".
* `ClassLabels(values: ndarray, discrete: bool, name: str, exclude: tuple[str,...] = (), use_all_rows: bool = False)`
  is a dataclass. `values` has full table length, and NaN means "no class"
  (the row is not eligible). `exclude` lists the columns that define the labels
  (a gate's parameters). `use_all_rows` means that rows the gates remove are
  still eligible, because the labels contrast inside with outside.

### 4.3 `display_coordinates(values, view) -> ndarray`

Maps a column to [0, 1] the way the axis draws it. If either bound is `None`,
take it from `ndxplorer.utils.axis_helpers.robust_axis_range(values, view.scale)`.
On a log axis, both bounds must be > 0 or the result is all-NaN. Values ≤ 0
become NaN, and values and bounds are mapped by log₁₀. Non-finite values become
NaN. If the span hi − lo is not finite and > 0, the result is all-NaN.
Otherwise u = (x − lo)/(hi − lo), clipped to [0, 1], with NaN kept as NaN.
Output dtype is float64 and the shape is preserved.

### 4.4 `RankingTable(columns, views=None, rows=None, labels=None, max_rows=DEFAULT_MAX_ROWS, seed=0, weights=None)`

One subsample shared by every state of a ranking, so that all views are
compared on the same bursts.

* Attributes callers read: `columns` (a dict copy of the mapping), `views`,
  `labels`, `n_eligible: int`, `n_rows` (property; the sample size, 0 before
  prepare), `names` (property; surviving columns in the given order), `raw:
  dict[name → float64 sample]`, `coords: dict[name → display coordinates]`,
  `distinct: dict[name → number of distinct finite coordinates]`, `y` (sampled
  labels or `None`), `w` (sampled weights normalised to mean 1, or `None`),
  `total_weight` (Σw, or the sample size without weights), and `index` (the
  sampled row indices, ascending).
* `view(name) -> ColumnView` returns the given view, or a default linear
  automatic view.
* `prepare()` is idempotent. Eligible rows: all rows, AND `rows` (unless the
  labels have `use_all_rows`), AND finite labels (if labels are given), AND
  finite, positive weights (if weights are given). If the number eligible
  exceeds `max_rows > 0`, draw `max_rows` of them uniformly without replacement
  with `numpy.random.default_rng(seed)` and sort them ascending. Only the
  sampled rows are converted to float64. The full column must never be widened
  first, because float32 views of large tables stay unconverted. A column is
  dropped if fewer than 2 finite display coordinates remain, or if they are all
  equal. A constant column has no view to rank.
* `derived_from(sources, threshold=DERIVED_RHO) -> list[str]` returns the
  surviving columns (other than `sources`) whose Spearman |ρ| with any present
  source is ≥ `threshold`. ρ is computed on raw sampled values with **average
  ranks for ties**, over rows finite in both, and only if there are at least
  `MIN_K` such rows.
* `matrix(names) -> ndarray (n_rows, len(names))` holds the display coordinates.

### 4.5 The scores

#### 4.5.1 Class separation by nearest neighbours (method `"separation"`)

**Literature.** VizRank (Leban, Zupan, Vidmar & Bratko 2006) scores a
projection of class-labelled data by how well a k-nearest-neighbour (k-NN)
classifier, trained on the projected coordinates alone, predicts each point's
class. The projection's quality is the *average probability that the classifier
assigns to the correct class*, estimated without letting a point vote for
itself. The authors chose it over plain accuracy because it rewards confident
separation (supplement to Leban et al. 2005/2006, "VizRank method details").
They used Euclidean distance, distance-weighted votes and k = √N. With uniform
(unweighted) votes and leave-one-out evaluation, the k-NN probability of the
true class for point i is just the fraction of its k neighbours that share its
class. The average over points is the score below. Coordinates are those the
user sees, as in VizRank, where the score is computed on the visualised
projection.

**ndX definition.** Given points P (n × d, display coordinates) and labels y:

1. Drop rows where any coordinate or y is non-finite, leaving n_v rows. Keep
   n_tot (the `n_total` argument, default len(y)).
2. If n_v < k + 1, return `None` (every point needs k other points; see D5).
3. For each point i, its neighbour set Nᵢ holds the k points j ≠ i with the
   smallest Euclidean distance ‖pᵢ − pⱼ‖. **The point itself is never in Nᵢ,
   even when duplicates sit at distance 0.** **Ties at the k-th distance are
   broken by ascending row index** (deterministic, and independent of the
   column order; see D3).
4. Discrete labels: p_o = (1/(n_v·k)) Σᵢ Σ_{j∈Nᵢ} [y_j = y_i].
   `knn_separation(..., discrete=True)` returns **−p_o** (lower is better).
5. Continuous labels (a quantity rather than ids): ŷᵢ = mean of y over Nᵢ.
   R² = 1 − Σ(yᵢ − ŷᵢ)² / Σ(yᵢ − ȳ)². If the denominator is 0, return `None`.
   Return **−R² · n_v/n_tot**. The factor is the coverage share: a view that
   cannot draw a row explains none of that row's variance.

Signature: `knn_separation(points, y, *, discrete: bool, n_total: int|None = None, k: int = MIN_K) -> float|None`.
`points` may be 1-D (n,) or 2-D (n, d).

`nearest_neighbours(points, k) -> ndarray[int] (n, k)` returns the neighbour
indices with the rules of step 3, in ascending (distance, index) order. Use a
KD-tree (`tttrlib.KDTree`) or any exact method. The answer must be exact, not
approximate.

**Chance correction.** `chance_corrected_agreement(same_fraction, y) -> float|None`:
the displayed class score is κ = (p_o − p_e)/(1 − p_e), where p_e is the
agreement expected when labels are unrelated to position. For a neighbour drawn
uniformly from the *other* n − 1 points (without replacement),
p_e = Σ_c n_c(n_c − 1) / (n(n − 1)), where n_c are the class counts of the
finite labels (see D2). Return `None` when only one class remains, or when there
are no finite labels. This is Scott's π / Fleiss' form of chance-corrected
agreement (one shared marginal; Scott 1955; Cohen 1960 for the general idea).
κ = 0 for a random view, 1 for perfect separation, and < 0 for anti-separation.
The raw fraction misleads when classes are unbalanced: with a 95 %/5 % gate a
random view already has p_o ≈ 0.9. κ also compares views fairly when their
missing values remove different rows. Because p_e is fixed for a fixed set of
rows, κ is a monotone function of p_o, so it ranks identically there.

**Ranker score (separation).**
* Discrete: the score key is (−κ, −p_o, n_v). Skip the state (`None`) if κ is
  undefined.
* Continuous: (−R²·coverage, −R²·coverage, n_v).
* Before computing κ, apply the same coverage factor n_v/n_tot to κ (D6), so
  that a view drawing half the bursts cannot win on that half alone.
* Columns ranked for this method: the table's surviving `names`, minus
  `labels.exclude`, minus `derived_from(sorted(exclude))`. Flags and clocks are
  **not** filtered for this method.

#### 4.5.2 Correlation (method `"correlation"`)

**Literature.** Pearson's product-moment correlation (Pearson 1895). Spearman's
rank correlation is Pearson's r on ranks, with tied values given the **average**
of the ranks they span (Spearman 1904; Kendall & Gibbons 1990). Significance:
t = r·√((n − 2)/(1 − r²)) follows Student's t with n − 2 degrees of freedom
under H₀: ρ = 0 (two-sided p). This is exact for Pearson under bivariate
normality and the usual large-sample approximation for Spearman (the convention
of `scipy.stats.spearmanr`).

`correlation(a, b, method="pearson") -> (key, r, p)`:
1. Keep the rows where both values are finite (pairwise deletion; ±inf counts
   as missing). Call the count n.
2. If n < 2, return (+inf, NaN, NaN).
3. For `"spearman"`, replace each column by its average ranks.
4. Centre both columns. If either has zero sum of squares (constant), return
   (+inf, NaN, NaN).
5. r = Σab / √(Σa²Σb²), clamped to [−1, 1].
6. p = 1 if n = 2 (no degrees of freedom; same convention as
   `scipy.stats.pearsonr`); p = 0 if |r| = 1; otherwise the two-sided t-test p.
7. key = −|r|.

**Ranker score (correlation).** Spearman |ρ| of the two columns, computed on
the column-set coordinates of 4.6 (the robust-axis coordinates) with **average
ranks** (D7). The comparison key is (−|ρ|, p), and ties keep scoring order. A
pair whose ρ is undefined is skipped (`None`), not shown as "N/A" (D8).

#### 4.5.3 Population separation (method `"populations"`, the default)

This score is ndX's own. It is defined and implemented in
`ndxplorer/analysis/separation.py` and is **not** part of the rewrite. The rankers call
`find_populations(matrix, total_weight, w)`. The arguments are the column-set
coordinates (4.6) of the 1 or 2 columns, the table's `total_weight` and `w`.
The call returns `None` (skip the state) or an object with `.score` (in
[0, 1), where 0 means one population), `.count` (number of islands),
`.shares`, `.in_islands`, `.label(points, core=bool)` and
`.assign(points, mode)`.
* Score key: (−score, −count), and ties keep scoring order. The key must hold
  the found object for the row, and comparisons must never compare two found
  objects. Add an arrival counter before it, or keep the object outside the key.
* A pair where one axis is (nearly) a function of the other
  (`ColumnSet.is_curve`) is skipped: its "populations" are stretches of one
  line, already seen in 1-D.

### 4.6 `ColumnSet(table, exclude=())` (the columns worth ranking for populations and correlation)

Calls `table.prepare()`. For each surviving column in table order that is not
in `exclude`, set it aside with a reason in `left_out: dict[name → str]`, using
the first rule that applies:
1. `table.distinct[name] < MIN_DISTINCT` → "a flag (few distinct values)".
2. `is_clock(raw)` → "the acquisition clock". `is_clock(values)`: over the
   finite values in row order, there are more than 2·MIN_K of them, and the
   share of consecutive differences that are > 0 is ≥ 0.9.
3. `separation.RobustAxis.fit(raw, view.scale)` returns `(axis, u)`. If the
   axis is `None`, or u has fewer than 5·MIN_K finite values → "nothing left
   after outliers".

Otherwise, keep `axes[name] = axis` and `coords[name] = u`. Compute
`ranks[name]` = average ranks of the finite u (NaN elsewhere), and
`uniform[name] = ranks / max(n_finite − 1, 1)`.

`correlation_ratio(y, x, bins=32) -> float` is η² of y given x, with both
values in [0, 1]. Use the rows finite in both. Return 0 with fewer than
2·MIN_K rows, or when y has zero variance. Bin x by ⌊x·bins⌋ clipped to
[0, bins − 1]. Return 1 − Σ(y − mean_bin(y))² / Σ(y − ȳ)² (Pearson 1903;
Fisher's η²). It is 1 when y is any function of x, monotone or not.

**Aliases ("the same quantity").** Visit the kept columns with those that have
a fixed axis range (both `lo` and `hi` set) first. Within each group, later
table position goes first. Add each column to the first existing group whose
head h satisfies Spearman |ρ(h, c)| ≥ DERIVED_RHO (on `ranks`, needing
≥ 2·MIN_K joint finite rows, otherwise 0), or η²(u_h | u_c) ≥ 0.98 **and**
η²(u_c | u_h) ≥ 0.98 (on `uniform`). If no group qualifies, start a new group.
`aliases: dict[head → list of members]`. Each member gets the reason
"the same as {head}".

**Folds.** A head is "a fold of {other}" if, for some other head,
η²(u_name | u_other) ≥ 0.98 and η²(u_other | u_name) < 0.9. Such a column is
a many-to-one function of another, for example (1−E)·E of E. It adds nothing,
and it piles density up where it folds.

`names`: the heads that were not set aside, in table order.
`matrix(names)`: the `coords` of those columns stacked as (n, len).
`is_curve(a, b)`: max(η²(u_a|u_b), η²(u_b|u_a)) ≥ 0.95.

The η² checks use the rank-uniform values, not the coordinates. Two species
far apart on both axes explain much of each other's coordinate variance, but
within each species the ranks are independent. A true function stays a
function of the other column's ranks.

### 4.7 Rankers: `ProjectionRanker(table, method)` (pairs) and `ParameterRanker(table, method)` (single columns)

Construction raises `ValueError` if the method is not a key of `METHODS`, if the
method needs labels and `table.labels is None`, or (for `ParameterRanker`) if
the method does not rank single columns. Construction only stores. It must not
read or sample the table.

What the panel model and `projection_rank_model.py` use:

* `prepare()` runs on the GUI thread. It calls `table.prepare()` and resets the
  column choice, so it is deferred until the first state count is requested.
* Some way to report the state count and to iterate the states (section 2).
  Column selection (`ColumnSet`, or the separation column list) and ordering
  happen lazily on that first request, which runs in the worker.
* Scoring one state, and turning (score, state) into a `RankRow`.
* `table` (attribute): the `RankingTable`.
* `attrs` (attribute): the list of ranked column names after selection
  (`[]` before). `projection_rank_model.note()` uses
  `len(table.columns) - len(attrs)` as "parameters left out or merged".
* `_columns_ready` (attribute, bool): false between `prepare()` and the lazy
  column selection, true after. `note()` reads it with
  `getattr(..., "_columns_ready", True)`. **Keep this name.**
* `columns` (attribute): the `ColumnSet` for populations and correlation, or
  `None`.
* `left_out() -> dict[str, str]` returns a copy of `columns.left_out`, or `{}`.
* `header -> tuple[str, ...]` (property):
  * populations: `("Separation", <name headers>…, "Islands")`
  * correlation: `("ρ", "x", "y")`
  * separation: `("κ", <name headers>)` for discrete labels, and `("R²", <name headers>)`
    for continuous ones (D9).
  * Name headers: `("x", "y")` for pairs, `("Parameter",)` for single columns.
* `score_span -> (lo, hi)`: populations (0, 0.5), correlation (−1, 1),
  separation (0, 1).
* `matches(payload, wanted) -> bool`. Pairs: the sets {x, y} are equal, because
  a transposed view is the same view. Single columns: equal `"z"`.
* `dimension`: 2 for pairs, 1 for single columns.
* Population-only helpers. Each returns `None` unless the method is
  `"populations"` and the columns are known:
  * `ranked_names(names) -> list|None` maps each name to itself if it was ranked,
    or to the head whose alias group contains it. Returns `None` if any name is
    neither.
  * `islands(names, values, core=False) -> ndarray|None` re-finds the view's
    populations on the ranking sample (as scored), maps every value row through
    each column's `axes[name].transform`, and returns `found.label(points, core=core)`.
  * `assign_islands(names, values, mode="whole") -> (labels, probabilities)|None`
    does the same and returns `found.assign(points, mode)`.

**Column order for pairs.** Populations and separation: sort the selected
columns by their own single-column score's primary key (ascending; `None`
counts as +inf), with ties broken by selection order. Correlation: keep the
selection order. Single-column rankers do not reorder. VizRank used a
univariate heuristic (ReliefF; Kononenko 1994) for the same purpose: score the
promising projections first. ndX uses the method's own 1-D score instead.

**Payloads.**
* Pairs: `{"x": name_x, "y": name_y, "scale_x": view(x).scale, "scale_y": view(y).scale}`,
  with x the earlier column in the enumeration order.
* Single columns: `{"z": name, "scale_z": scale}`.

**Rows** (`RankRow`). A column label is `name`, or `"{name} (log)"` on a log
axis. n means `table.n_rows`.
* Populations: cells (`f"{score:.3f}"`, labels…, `str(count)`). Bar is
  min(1, score/0.5). `sort_value` is score. The tooltip is the "{count} islands
  holding …" text when count > 1, else "One population: …" (Appendix A). It is
  followed by " Also this view: {aliases}." when the shown columns have aliases.
* Correlation: cells (`f"{r:+.3f}"`, labels…). Bar is |r|. `sort_value` is
  |r|. `value` is r (signed). The bar colour is one colour for r ≥ 0 and another
  for r < 0. **Choose your own two colours** (D10). The tooltip is
  "Spearman ρ = {rho:+.4f}, p = {p:.3g} over {n} sampled bursts: …" plus the
  aliases.
* Separation, discrete: cells (`f"{κ:.3f}"`, labels…). Bar is κ clamped to
  [0, 1]. `sort_value` is κ. The tooltip is "{share:.1%} of each burst's {k}
  nearest neighbours share its class ({classes}); κ = {kappa:.3f} above chance,
  over {valid} of {n} sampled rows."
* Separation, continuous: cells (`f"{R²c:.3f}"`, labels…), where R²c is the
  coverage-weighted R². Bar is R²c clamped to [0, 1]. `sort_value` is R²c. The
  tooltip is the "The mean {classes} of each burst's …" text, where `r2` is the
  unweighted R² and `share` is the coverage, formatted `.0%`.

---

## 5. The host contract (keep compatible; the host code is not changed)

### 5.1 Runner

`runner(owner, text, func, *, args=(), maximum=0, on_partial=None, on_result=None, on_error=None, on_done=None, owner=…, cancellable=True, **ignored) -> task`.

Owner is passed both positionally and as a keyword. Ignore the keyword, or
accept it in `**ignored`.

* The runner calls `func(*args, handle)`, possibly **several times** for one
  task. The emtk host runs it in time slices: `handle.is_cancelled` turns true
  when the slice's time budget is spent, and the host then calls `func` again
  with the same arguments. `func` must therefore resume from state kept on the
  run object (the shared enumeration), not from local variables, and must hand
  every scored state to `handle.set_partial` before returning.
* `handle` provides `is_cancelled` (property, polled after each state),
  `set_partial(value)`, `set_progress(value)` and `set_text(text)`.
* Callbacks run on the GUI thread, in this order: all `on_partial` values,
  then `on_result(result)` only when the run ended uncancelled (or
  `on_error(exc)` if it raised), then `on_done()`.
* The returned task has `cancel()` and `is_running` (bool).
* Reference implementations to test against, which are ndX's own:
  `playback_export.frame_runner`/`FrameTask` (sliced) and `inline_runner` in
  `ndxplorer/tests/test_separation.py` (synchronous).

### 5.2 What the host and the subclass call (all listed above)

`RunState.Hidden`/`Running`/`Done`, `VizRankModel.load_spec`, `model._run`
(`None`-ness, `.generation`, `.ranker`), `model.ranked_key()` (subclass),
`model.refresh_context()` (subclass), `shutdown()`, `dialog_reopened()`,
`pause_computation(RunState.Hidden)`, `run_state`, `rows`, `select_request`,
`auto_select({"x":…, "y":…})` / `auto_select({"z":…})`, `start()`,
`settings_changed()`, `start_label`, and the `data_table` binding to
`ranked_rows`.

### 5.3 Persistence

There is no file format of its own. The host saves the settings of each ranking
window in the analysis session state of the `.pto` as
`{"rankings": {"pairs"|"z": {"sample_rows": int, "classes": str, "method": str, "photon_mode": str, "min_photons": int, "open": bool}}}`.
Those attributes live on the subclass. The rewrite must not add state that has
to persist.

---

## 6. Threading, progress, cancellation (summary)

* The ranker's `prepare()` (subsampling, which reads the live table) runs on the
  GUI thread. Column selection, ordering and scoring run in `func`, which may
  be a worker thread or time slices of the frame loop. The ranker must not
  touch the live table after `prepare()`.
* Cancellation is cooperative. It is polled after every state and never
  interrupts a state that is being scored.
* Progress is counted on the GUI side from arriving batches, as `completed` /
  `_run.total`. The worker does not report progress counts. This avoids a race
  when a continued run starts before the previous run's last batch was counted.

---

## 7. Observable input → output examples (facts measured by running the current code on 2026-10-20 unless marked NEW)

Tolerances: 1e-9 unless stated otherwise. "NEW" marks values under the
corrected behaviour of section 9. I computed them with an independent
brute-force reference.

**Correlation**
| input | method | result (key, r, p) |
|---|---|---|
| a = [1,2,3,4,5], b = [2,1,4,3,5] | pearson | (−0.8, 0.8, 0.104088038662) |
| same | spearman | (−0.8, 0.8, 0.104088038662) |
| a = [1,1,2,3], b = [1,2,2,3] | pearson | (−0.852802865422, 0.852802865422, 0.147197134578) |
| same | spearman (average ranks) | (−0.833333333333, 0.833333333333, 0.166666666667) |
| a = [1,2,3,4,5,6], b = [2,4,5,4,5,7] | pearson | (−0.878310065654, 0.878310065654, 0.021311641129) |
| same | spearman | (−0.853310335188, 0.853310335188, 0.030698562973) |
| a = [1,2,NaN,4,5], b = [2,1,7,3,inf] (pairwise deletion leaves 3 rows) | pearson | (−0.654653670708, 0.654653670708, 0.545628948343) |
| a = [1,2], b = [3,1] | pearson | (−1, −1, 1) |
| a = [1], b = [3] | any | (inf, NaN, NaN) |
| a = ones(5), b = 0..4 | any | (inf, NaN, NaN) |
| a = 0..4, b = 2a+1 | pearson | (−1, 1, 0) |
| a = 0..4, b = −a | pearson | (−1, −1, 0) |
| iris sepal length vs sepal width | pearson | r = −0.109369, p = 0.182765 (4 dp) |
| iris petal length vs petal width | pearson | r = 0.962757 |
| iris sepal length vs sepal width | spearman | ρ = −0.159457, p = 0.051285 |
| iris petal length vs petal width | spearman | ρ = 0.936003 |
Results must agree with `scipy.stats.pearsonr` / `spearmanr` to 1e-6 (they are
used as test oracles only, not as runtime dependencies).

Ranker-level defect, measured: the current ranker ranks with *ordinal* ranks.
For a = [1,1,2,3], b = [1,2,2,3] that gives ρ = 1.0 (p = 0) instead of
0.8333. NEW: the ranker must report 0.8333.

**Nearest neighbours**
* Points (1-D) [0, 1, 3, 6, 10], k = 2 → [[1,2],[0,2],[1,0],[2,4],[3,2]].
  The only tie is the second neighbour of point 2 (x = 3): index 0 (x = 0) and
  index 3 (x = 6) are both at distance 3, and the lower index, 0, is taken.
* Points 4×(0,0) followed by 3×(5,5), k = 3: no row contains its own index. Row
  0 = {1,2,3}. Rows 4..6 contain the other two (5,5) points plus one (0,0)
  point. NEW: under index tie-breaking that point is index 0, so row 4 =
  [5,6,0], row 5 = [4,6,0], row 6 = [4,5,0].

**k-NN class separation** (x = [0,1,3,6,10,15,21,28,36,45,55,66] as a column,
1-D, which has no distance ties at the k-th neighbour)
| labels | k | `knn_separation` | κ current (p_e = Σp²) | κ NEW (p_e without replacement) |
|---|---|---|---|---|
| six 0s then six 1s | 3 | −0.888888888889 | 0.777777777778 (p_e 0.5) | 0.796296296296 (p_e 0.454545454545) |
| [0,0,1,1,2,2,0,1,2,0,1,2] | 3 | −0.194444444444 | −0.208333333333 | −0.107638888889 |
| six 0s/six 1s with x[0] = NaN (11 valid) | 3 | −0.878787878788 | 0.755555555556 | 0.777777777778; NEW with coverage 11/12 → 0.712962962963 |
| fewer valid rows than k (9 rows, k = 10) | 10 | `None` | | |
| exactly k rows (3 rows, k = 3) | 3 | current −1.0 (uses k−1 neighbours) | | NEW: `None` |

2-D: P = [(0.1,0.2),(0.15,0.22),(0.2,0.15),(0.12,0.3),(0.8,0.7),(0.85,0.75),(0.9,0.66),(0.7,0.8),(0.5,0.5),(0.45,0.55)],
y = [0,0,0,0,1,1,1,1,0,1], k = 3 → p_o = 0.866666666667. κ current is
0.733333333333 and κ NEW is 0.76.

Continuous labels, same x, y = 0..11, k = 3: −0.912975912975913. With x[0] = NaN:
R² over the 11 rows = 0.890909090909, and the function returns −0.816666666667
(× 11/12). With constant y the result is `None`.

`chance_corrected_agreement` (current p_e = Σp²): (1.0, all one class) → `None`;
(0.5, five 0s and five 1s) → 0.0; (0.9, 95 zeros and 5 ones) → −0.052631578947.
NEW (without replacement): 0.5 with [0,1]×5 → (0.5 − 4/9)/(5/9) = 0.1.
0.9 with 95/5 → p_e = (95·94 + 5·4)/(100·99) = 0.904040…, so κ = −0.042105263158.

A random view of 4000 uniform points with a 5 % class: p_o > 0.85 but |κ| < 0.05.

**display_coordinates** for v = [−1, 0, 1, 10, 100, 1000, NaN, inf]
* log, [1, 100] → [NaN, NaN, 0, 0.5, 1, 1, NaN, 1]. NEW: +inf must be NaN
  (non-finite → NaN; the current code gives 1, see D11).
* lin, [0, 10] → [0, 0, 0.1, 1, 1, 1, NaN, 1]. NEW: last element NaN.
* lin, [5, 5] → all NaN.

**Iris, method "separation", classes = species, all four columns (linear
automatic display ranges)**, ranked best first with κ (current p_e):
petal width × petal length 0.928 (p_o 0.952). Then petal width × sepal width
0.883, petal width × sepal length 0.878, petal length × sepal length 0.863,
petal length × sepal width 0.850, and sepal length × sepal width 0.569. The
column order chosen for enumeration is [petal width, petal length, sepal
length, sepal width]. The top pair must be {petal length, petal width} and the
bottom pair {sepal length, sepal width}. Measured trap: the current value of
the top pair is 0.926 if the two columns are passed in the other order (0.952
vs 0.9507 raw). That is caused by tie-breaking that depends on column order,
which D3 removes.

**Enumeration and insertion**
* Pairs over 4 columns: (0,1),(0,2),(1,2),(0,3),(1,3),(2,3). Over 0 or 1 columns: none.
* Scores arriving in order [0.5, 1/3, 0.25, 2/3, 0.5, 0.75] are inserted at
  positions NEW [0, 0, 0, 3, 3, 5] (stable: the second 0.5 goes after the first).
* A score function over states 0..9 that returns `None` for state 3 gives 10
  completed and 9 rows.
* Cancelled before the first check: exactly one state is scored, and the
  enumeration's next state is the second one.
* 100 states at 10 ms each with a 50 ms interval give 15–25 batches holding
  100 items in total.

**End-to-end (acceptance tests, which already exist and must stay green)**:
`test_separation.py::test_every_rank_by_option_ranks_end_to_end`,
`test_an_unknown_method_falls_back_to_separation`,
`test_photon_options_follow_the_photon_column`,
`test_the_view_spec_names_only_what_the_model_has`, the MFD/ALEX real-data
tests (when the data is present), and the ranking tests in
`test_app/test_playback_export.py`. One of the latter is iris by class "z
parameter: class": it must find {petal width, petal length} and apply it to
the axes.

---

## 8. Performance

Measured on the owner's arm64 Mac with the current code, for a 20 000-row,
40-column table with the default 5000-row sample:
* correlation, 780 pairs: 0.6 s in total, including column selection.
* separation by classes (k = 10), 780 pairs: 11.9 s, about 15 ms per pair.
* populations, 12 columns (66 pairs): 0.3 s.

Requirements:
* Scoring cost is independent of the full table size. Only the sample is
  touched after `prepare()`.
* k-NN separation must take ≤ 20 ms per pair at n = 5000, k = 10. A KD-tree
  query for k + 1 neighbours, with self and tie handling vectorised, meets this.
* `prepare()` on the GUI thread must take ≤ 50 ms for 40 columns × 10⁶ rows of
  float32 views. It gathers the sampled rows only.
* A single score call must return within one time slice budget (about 10 ms)
  for correlation, so the emtk frame loop stays responsive.
* For reference: k = √N (71 at N = 5000), the VizRank default, cost 6× more in
  a measurement (0.64 s vs 0.11 s for 10 pairs) and gave the same top ranking on
  a planted two-species table and on iris (k = 12). This supports keeping
  k = 10 as the ndX default (D12).

---

## 9. Deliberate changes from the current behaviour (the implementer follows the spec, not the old code)

| # | Current | Spec | Why |
|---|---|---|---|
| D1 | With no `runner`, the model imports `chisurf.gui.task.run_in_background`, which was deleted, so start() raises | Run inline synchronously | The default path is broken, and inline is the documented headless behaviour |
| D2 | Chance agreement p_e = Σ p_c² (with replacement) | p_e = Σ n_c(n_c−1)/(n(n−1)) | A neighbour is one of the *other* n−1 points. This makes E[κ] = 0 exactly under random labels. The difference is ~1/n, which matters at small n |
| D3 | Ties at the k-th distance are resolved by KD-tree traversal, so the score depends on the column order (iris: 0.928 vs 0.926) | Ties are broken by ascending row index | Deterministic, and invariant to swapping x and y. Burst tables have many duplicates (integer counts) |
| D4 | Equal scores: the newer row goes before the older | The older row stays first (stable) | Arbitrary before. Stable is the intuitive choice and makes the order reproducible across pauses |
| D5 | n_v = k uses k−1 neighbours | n_v ≤ k → `None` | Every point needs k others, so the score always has one definition of k |
| D6 | Coverage factor only on the continuous score | Also on κ | Treats rows a view cannot draw the same way in both scores |
| D7 | Ranker Spearman uses ordinal ranks (ties broken by position) | Average ranks | That is the definition of Spearman's ρ. Ordinal ranks gave ρ = 1 for a tied example whose ρ is 0.833 |
| D8 | An undefined correlation row is shown as "N/A" with score NaN | Skipped, but counted as scored | A NaN in a sorted numeric table column is not a rank |
| D9 | The continuous-class header says "κ" over an R² value | Says "R²" | It mislabelled the number |
| D10 | Bar colours taken from the third-party toolkit | ndX's own pair (for example from ndX's colormap) | Provenance |
| D11 | +inf maps to the top edge (1) | Every non-finite value → NaN | Matches the documented rule that values the axis cannot draw become NaN |
| D12 | k = 10 with no stated basis | k = 10 kept as an explicit, documented default, and exposed as a parameter of `knn_separation` | The published value is √N. The rankings agreed on the test tables at 6× the cost (section 8) |

Strings shown to the user that mention "10 nearest neighbours" stay valid,
because k stays 10.

---

## 10. References

* Leban G, Zupan B, Vidmar G, Bratko I. VizRank: Data Visualization Guided by Machine Learning. *Data Min Knowl Disc* 13:119–136 (2006). doi:10.1007/s10618-005-0031-5
* Leban G, Bratko I, Petrovic U, Curk T, Zupan B. VizRank: finding informative data projections in functional genomics by machine learning. *Bioinformatics* 21(3):413–414 (2005). The supplementary page "VizRank method details" (file.biolab.si/biolab/supp/bi-vizrank/details.html) states the k-NN, k = √N, distance-weighted votes, and average-probability-of-correct-class measure.
* Cover TM, Hart PE. Nearest neighbor pattern classification. *IEEE Trans Inf Theory* 13:21–27 (1967). doi:10.1109/TIT.1967.1053964
* Scott WA. Reliability of content analysis: the case of nominal scale coding. *Public Opinion Quarterly* 19:321–325 (1955). doi:10.1086/266577
* Cohen J. A coefficient of agreement for nominal scales. *Educ Psychol Meas* 20:37–46 (1960). doi:10.1177/001316446002000104
* Pearson K. Note on regression and inheritance in the case of two parents. *Proc R Soc Lond* 58:240–242 (1895). doi:10.1098/rspl.1895.0041
* Pearson K. Mathematical contributions to the theory of evolution. On homotyposis… (correlation ratio η) (1903). Standard textbook treatment: Kendall MG, Stuart A. *The Advanced Theory of Statistics*, vol. 2, ch. on regression (correlation ratio).
* Spearman C. The proof and measurement of association between two things. *Am J Psychol* 15:72–101 (1904). doi:10.2307/1412159
* Kendall MG, Gibbons JD. *Rank Correlation Methods*, 5th ed. Edward Arnold (1990). Average ranks for ties.
* Student [Gosset WS]. The probable error of a mean. *Biometrika* 6:1–25 (1908). doi:10.1093/biomet/6.1.1. t-test of r.
* Kononenko I. Estimating attributes: analysis and extensions of RELIEF. *ECML-94*, LNCS 784:171–182 (1994). doi:10.1007/3-540-57868-4_57
* Fisher RA. The use of multiple measurements in taxonomic problems. *Ann Eugen* 7:179–188 (1936). doi:10.1111/j.1469-1809.1936.tb02137.x. Iris data, public domain.

---

## Appendix A — user-visible strings to keep verbatim (they are in the de/fr catalogues)

Panel model: "Score views", "Score", "Press Start to rank every view.",
"Restart with new settings", "Start", "Pause", "Continue", "Finished",
"Scoring views…", "ordering parameters", "The score; the bar is its share of the range.",
"The {axis} parameter of the view; hover a shortened name for the whole of it.",
"{done}/{total} scored ({percent} %)", "{done} scored", "paused", "finished",
"{n} failed", "Cannot rank: {error}", "Ranking failed: {error}".

Scores: captions "Separation", "Correlation", "Classes"; header "Parameter".
Method help:
* populations: "How many bursts fall into clearly separated islands: donor-only, acceptor-only and FRET species in E vs S, a dynamic population off the static FRET line. 0: one population; 0.5: two equal islands with empty space between; 0.67: three."
* correlation: "|Spearman rho| of the pair: parameters that measure related things (E and a lifetime, a rate and its count), not populations. Parameters that are the same quantity are ranked once."
* separation: "Do the bursts of one label (a gate, the clusters) sit together in this view? Share of each burst's 10 nearest neighbours with its label, above chance."

Row tooltips:
"{count} islands holding {shares} of the {n} sampled bursts; {inside} % sit clearly inside one (not on a bridge or in a tail). Score {score}: the chance that two bursts are in two different, clearly separated populations."
(shares as "NN %" joined by ", "; inside as an integer percent; score .3f),
"One population: no significant density valley over {n} sampled bursts.",
"Also this view: {names}." (prefixed by one space),
"Spearman ρ = {rho}, p = {p} over {n} sampled bursts: the two move together, which says nothing about populations.",
"{share} of each burst's {k} nearest neighbours share its class ({classes}); κ = {kappa} above chance, over {valid} of {n} sampled rows.",
"The mean {classes} of each burst's {k} nearest neighbours predicts its own with R² = {r2}; weighted by the {share} of sampled rows that have values.",
"No finite pairs, or a constant column." (unused after D8; it may be dropped).
`{classes}` is the translated `ClassLabels.name`.

---

## Clarifications (2026-10-20)

These answer the implementer's questions after the first rewrite (ndxplorer
0a66a36). Each answer is functional. "Specified" marks where the answer fixes a
choice that this spec left open or that differs from the earlier behaviour.

1. **D6 and what the discrete row shows.** Yes, that is correct. The score
   cell, the bar and the sort order all use the coverage-weighted value
   κ_c = κ · n_v/n_tot. The tooltip reports the **unweighted** κ, together
   with "over {valid} of {n} sampled rows". The reader then sees both parts of
   the product: how well the view separates the rows it can draw, and what
   share of rows that is. The tooltip string stays verbatim (Appendix A).
   `{share}` there is p_o, the unweighted same-class fraction.

2. **Tie-break on the number of valid rows.** Specified: **−n_v**. The full
   key is (−κ_c, −p_o, −n_v), and after that, scoring order. When the
   agreement is equal, the view supported by more bursts is better evidence,
   so it ranks first. The continuous key gets the same last element:
   (−R²_c, −R²_c, −n_v).

3. **`uniform` from 0-based average ranks.** Yes, that is correct, and
   0-based is required. Average ranks run from 0 to n_f − 1 over the n_f finite
   values. Tied values share the mean of the positions they span. Dividing by
   max(n_f − 1, 1) puts the values on [0, 1], which is the domain that
   `correlation_ratio`'s 32 bins assume. With 1-based ranks the top value
   would fall outside [0, 1] and be clipped into the last bin.

4. **Spearman inside `ColumnSet` (alias test) and in the correlation score.**
   Yes. Specified as the exact Spearman ρ under pairwise deletion: take the
   rows finite in **both** columns, rank each column **over that joint subset**
   with average ranks, and compute Pearson's r on those ranks. Ranks computed
   per column over each column's own finite rows are not used for ρ. The
   per-column ranks described in 4.6 serve only to build `uniform` for the η²
   tests. The minimum of 2·MIN_K joint rows still applies to the alias test.
   Below it, ρ counts as 0, which means "not an alias".

5. **Column tooltips.** Yes, that is correct. The "The {axis} parameter of the
   view; …" tooltip goes on the parameter-name columns only (x, y, or
   Parameter). The Islands column carries no parameter tooltip. A tooltip that
   names it is optional. If you add one, it is a new string and falls under
   item 10.

6. **Phase text.** Yes, that is correct. Use the existing translated strings:
   "ordering parameters" while the columns are being selected and ordered,
   then "Scoring views…" while scoring. No phase text may go out untranslated.

7. **`derived_from` and sources dropped in `prepare()`.** Specified: only
   sources that **survived** `prepare()` count. A source that was dropped as
   constant or undrawable over the sample has no defined rank correlation with
   anything, so it cannot make another column "derived". Treating it as
   present must give the same result, because its ρ is undefined and so never
   reaches the threshold. Skipping it explicitly is the specified behaviour.
   Note the difference from the exclusion list: a source that is listed in
   `labels.exclude` is still excluded from ranking whether or not it survived.

8. **Folds against heads that are themselves folds.** Yes. Specified as one
   pass over the alias heads. Each head is tested against **every** other head
   by the data relation alone, regardless of whether that other head is itself
   marked as a fold. Being a many-to-one function of another column is a
   property of the data and does not depend on which columns end up shown. A
   function of a fold is also a function of what that fold folds, so the
   result does not depend on the visiting order. The first matching "other"
   (in table order) names the reason.

9. **Automatic display range from the sample.** Yes, that is correct. The
   automatic range (a `None` bound in `ColumnView`) is the robust range of the
   **sampled** rows. Those are the bursts being ranked, and the robust range
   is quantile-based, so the sample estimates it well. The full column is not
   read after `prepare()`. Fixed bounds from the axis settings are used as
   given.

10. **The "Islands" header and i18n.** Specified: mark it for translation (the
    same marking as "Separation" and "Parameter") and render it through the
    translator. ndX's interface must be multilingual, so an unmarked string is
    a defect, not a workaround. Until the de/fr catalogues carry the entry, the
    translator falls back to English, so marking it is safe now. Adding the
    catalogue entries ("Islands": de "Inseln", fr "Îlots") belongs to the
    queued i18n catalogue job, not to this rewrite. Record it as an open item
    there. The same applies to any other new user-visible string, such as an
    optional tooltip from item 5. The headers "x", "y", "ρ", "κ" and "R²" are
    symbols and stay unmarked.
