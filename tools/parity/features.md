# ndXplorer feature checklist (Qt baseline → emtk port)

Each `## <scenario-id>` section lists what a user can see or do in that scenario
of the Qt app. The port ticks items off; `compare.py` reads the marks:

| Mark | Meaning |
|---|---|
| `[x]` | present in the emtk app |
| `[~]` | deliberately different; say what replaced it |
| `[-]` | intentionally dropped or not applicable; say why |
| `[ ]` | open |

Judge by **control inventory, not pixels**. A control that moved into a table
cell or a popover is still present. A renamed label is still parity (`...` →
`…`, `Auto X` → `Auto`). A *missing* control blocks the port.

Items marked **(Qt: broken)** do not work in the Qt app today. Either fix the
behaviour in the port or drop it deliberately with `[-]`; do not copy the bug.

## global — applies to every scenario

- [ ] Window title "ndX" (plus the file name once data is loaded) — emtk app: the host titles the window "ndX"; no host API yet to retitle it with the file name
- [x] Layout: a panel column on the left with tabs Plot controls / Parameters / Overlays, plus Equations and Gaussian Fit (hidden until the View menu shows them), and a "Plot" area on the right; the column is about ¼ of the width
- [~] Panel tabs can be rearranged (drag or split) and have a context menu (the ChiSurf DockArea) — emtk app: fixed dock layout with tab strips (left: Plot controls/Parameters/Overlays + feature tabs; right: Plot + feature tabs); View > Plot controls hides the column
- [x] Menu bar: File, Settings, View, Help
- [x] Status bar — NdxApp.show_status, a line under the plots
- [x] Controls are disabled until data is loaded (all actions except Import / Select working path, all panels, Screenshot, Contrast, Data, Save parameters, weight, z)
- [x] Keyboard shortcuts Ctrl+O (Import Text files) and Ctrl+I (Analysis-Folder) — every MENUS shortcut, Ctrl = Command on macOS
- [x] Opening a folder or file by dropping it on the Path field (or on the window) works like the CLI `--file` / `--folder` — a drop anywhere on the window (native and web hosts; the Tk host has no drop)
- [~] CLI: `ndx --file`, `--folder`, `--test-data`, `--chisurf-rpc host:port`, `-v` / `--debug`, plus the subcommands `filter` and `image` — `--emtk` takes `--file` / `--folder`, `-v` / `--debug` and `--host native|tk`; `filter` / `image` are headless and unchanged; `--test-data` (hard-coded Windows paths) and `--chisurf-rpc` are Qt-window only for now
- [x] Every control keeps its tooltip (see the per-scenario items) — each view.json section carries its Qt tooltip as `description`
- [x] Qt quirk, do not copy: a fresh window holds a hidden 1000-row placeholder dataset (Tau (green), Proximity ratio, r Experimental (green)), so the first Import already asks the merge question

## startup_empty — Start-up, no data

- [x] Splash image ("NDXPLORER — Visualization and analysis for fluorescence") fills the plot area until data arrives
- [x] Axis combos are empty; bin defaults 81 (1-D) / 31 (2-D); ranges 0..1
- [x] Path field shows the placeholder "Drop folder here."
- [x] Marginal plot axes are visible but empty
- [x] File menu entries shown in the no-data state (Import stays usable)

## open_mfd_folder — File > Import > Analysis-Folder (burst folder)

- [x] File > Import > Analysis-Folder (Ctrl+I) asks for a directory ("Burst analysis folder") and reads bi4_bur/*.bur together with the bg4/br4/by4/bv4/td4/2c4 companions merged by position
- [x] Equations add the derived columns (Sg, Sr, Sg/Sr, Proximity ratio, Fg, Fr, Fg/Fr, Fd/Fa, FRET efficiency, R_FRET, E_tau, …) from mfd.equations.yaml with the constants from the Parameters table
- [x] Default axes come from mfd.settings.json `default_axes`: x Tau (green), y Proximity ratio, z r Experimental (green), weight Number of Photons
- [x] Per-parameter axis settings (min/max/scale/bins) come from mfd.axis.json
- [x] 2-D histogram with the colormap (default viridis)
- [~] x marginal on top (blue, filled step), y marginal on the right (green step), with axis titles in the parameter colour — same plots and titles in emtk/ImPlot default colours (x, y, z = the first colours of ImPlot's colormap), per the user: default look, not Qt's
- [x] Path field shows the opened folder (the folder it sits in, as Qt)
- [x] Count fields show visible / total (12237 / 12237)
- [x] vmin / vmax fields (scientific format, e.g. 1.00e+00 / 2.01e+02)
- [x] Plot controls tab: foldable sections Playback (appears once data is loaded), Histogram (open), z axis, Draw Mask, Selection (open)
- [x] Histogram section, x row: parameter combo (editable), 1-D bins (81), 2-D bins (31), Normalized density check, Logarithmic axis check, Auto-scale check, "Set" (store as default range for this parameter)
- [x] Histogram section, y row: the same controls as x
- [x] x range min / max fields plus "Auto" (auto-range to the data); the same for y
- [x] "weight" check plus a parameter combo (enabled only while checked)

## file_dialog_analysis_folder — Analysis-Folder directory picker

- [x] Directory chooser titled "Burst analysis folder", starting in the working path (emtk file dialog in folder mode, via `app.io_service`; with no working path it starts in the current folder, as Qt's does)
- [x] Cancelling leaves the current data untouched (Cancel or ✕)

## merge_dialog — Merge dialog when data is already loaded

- [x] Title per importer ("Open CSV Files", "Open SmFRET Files", "Open MFD HDF5 Files", "Open Sampling Files", "Open PTO Container") — `io.loading.IMPORTERS[kind].merge_title`, shared with Qt. (No PTO import in the menu of either GUI.)
- [x] Prompt "How do you want to merge the new data?"
- [x] Radio "Replace existing data" (default) — `io/merge.view.json`, a `radio_list` choice
- [x] Radio "Append as columns (add new columns, rows must match)" (a row-count mismatch is reported in a message box)
- [x] Radio "Append as rows (add new rows of existing columns)"
- [x] OK / Cancel (Cancel aborts the import)

## open_csv_iris — File > Import > Import Text files (CSV)

- [x] Import Text files (*.csv, *.dat), Ctrl+O; several files can be selected at once (multi-select file dialog)
- [x] `#` comment lines are skipped and the header row gives the column names (the shared reader)
- [x] Axes can be set to any column (here petal length vs petal width); marginals and counts (150 / 150) update

## open_csv_file_dialog — CSV file picker

- [x] File chooser titled "Comma separated value files", filter "Text files (*.csv *.dat *.er4 *.txt);;All files (*.*)", multi-select

## open_bur_cli — Single .bur file via `ndx --file` (CLI / drop path)

- [x] `ndx --file <x.bur>` (and dropping a .bur/.txt) opens a single burst file (`python -m ndxplorer --emtk --file`, a drop on the window or the page)
- [x] .csv → CSV reader, .er4 → sampling, .h5/.hdf5 → MFD HDF5, directory → burst folder (the same dispatch as a drop) — `io.loading.kind_for_paths`; a folder with parameters.json is a sampling folder, .pto a container
- [x] Tiny files (11 rows) still plot without errors. Fixed on the way: the .bur's trailing tab read as a parameter named "" (both GUIs); the emtk axis chooser picked it and showed an empty x axis

## open_sampling — File > Import > ChiSurf-Sampling

- [x] ChiSurf-Sampling asks for a sampling folder ("Open sampling folder") and reads every .er4 in it
- [x] The er4 columns (chi2, rho_1, lb, sc, ts, xL1, b_1, tL1, bg) become parameters and the plot shows them

## open_analysis_file_error — File > Import > Analysis file: load error

- [x] Analysis file import: file chooser "MFD HDF5 files", filter "HDF5 files (*.h5 *.hdf5);;ZIP files (*.zip);;All Files (*.*)"
- [x] Files load in the background without freezing the window (a thread and a progress window with Cancel; in a page, where there are no threads, on the next frame)
- [x] A failure shows a "Data Load Error" box with the reader's reason (here: "holds no columnar HDF5 table …"), and the current data stays. [~] the reason only, not the Python traceback Qt shows

## open_image_h5 — Image table (X/Y pixel) → image mode

- [x] X pixel / Y pixel columns are detected as image axes: pixel bins, pixel ranges, and a map shown as an image (not upside down) — `axis_helpers.image_axes`, shared; applied however the table was opened
- [x] Photon weighting is switched on automatically
- [x] NaN / inf masking is turned off for pixel axes
- [ ] The Frame column drives playback (see playback_image_frames)

## menu_file — File menu (+ Import, Save submenus)

- [ ] File > Import > "Import Text files (*.csv,*.dat)" (Ctrl+O)
- [ ] File > Import > "Analysis file (*.zip, *.hdf)"
- [ ] File > Import > "Analysis-Folder" (Ctrl+I)
- [ ] File > Import > "ChiSurf-Sampling"
- [ ] File > Save > "Burst IDs"
- [ ] File > Save > "Histograms" (Qt: broken, not connected to anything)
- [ ] File > "Make Report"
- [ ] File > "Print window" (Qt: broken, not connected)
- [ ] File > "Exit" (Qt: broken, not connected; the window close button works)

## menu_settings — Settings menu (+ Save settings submenu)

- [ ] Settings > "Performance Settings" (tooltip "Configure performance settings for histogram computation…")
- [ ] Settings > "Load settings" (file chooser "ndX settings file")
- [ ] Settings > Save settings > "Axis settings" (save-file chooser)
- [ ] Settings > Save settings > "Constants" (writes mfd.constants.json)
- [ ] Settings > Save settings > "Equations" (Qt: broken, not connected)
- [ ] Settings > "Set default axis"

## menu_view — View menu

- [ ] View > "Plot controls" / "Parameters" / "Overlays" (checkable panel toggles; Qt: broken, they only flip their check mark because they were wired to the QDockWidgets that `convert_docks` deletes)
- [ ] View > "Fit Gaussians" (checkable; shows or hides the Gaussian Fit tab)
- [ ] View > "Equations" (checkable; shows the Equations tab; Qt: broken like the other panel toggles, so the Equations panel is unreachable)
- [ ] View > "UMAP" (Qt: broken, see view_umap_action)
- [ ] View > "Find informative projections…" (tooltip "Rank every x/y pair by class separation…")
- [ ] View > "Find informative projections (z axis)…"
- [ ] View > "Axis Control" (tooltip "Control the visibility of axes in plots")

## menu_help — Help menu

- [ ] Help > "Help" (Qt: disabled in the .ui, not connected)
- [ ] Help > "Fix Report Tool" (Qt: broken, see fix_report_tool)
- [ ] Help > "About" (Qt: not connected)
- [ ] Help > "Update" (Qt: not connected)

## axes_fdfa_tau — Set x/y parameters: Fd/Fa vs Tau (green)

- [x] Choosing a parameter in the y combo redraws the 2-D map and the marginals
- [x] The stored axis settings for Fd/Fa apply on selection: logarithmic y, range 0.1..500, bins 81 / 31
- [x] The log axis shows log ticks on the marginal and the 2-D map

## axes_log_norm_bins — Axis scale, normalisation, bins and ranges

- [x] 2-D bins x / y (1..999) re-bin the map (spin boxes)
- [x] 1-D bins (1..999) re-bin the marginal (spin boxes)
- [x] Normalized-density check on the y marginal
- [x] Manual x min / max
- [x] Logarithmic x axis check (log ticks label 0.6..4 inside one decade, emtk 0821285)
- [ ] Changing bins disables mask drawing and clears the mask (Qt behaviour)

## weights — Weighted histograms

- [x] "weight" check (tooltip "If checked, histograms are weighted by selected parameter")
- [x] Weight parameter combo lists every parameter; weighting applies to the map and the marginals (same counts and vmin/vmax 3.10e+01 / 4.50e+04 as Qt)

## colour_log_contrast — Colormap, log counts, auto contrast, vmin/vmax

- [x] Colormap combo (the pyqtgraph map list: viridis, inferno, magma, plasma, cividis, turbo, CET-*…)
- [~] "log #" check for a log10 colour scale of the counts — toggling it re-derives vmin/vmax in log10 units; the Qt window keeps its linear limits over the log image (1..200 on values 0..2.3), which washes the map out
- [x] "Contrast" button sets vmin / vmax automatically
- [x] vmin / vmax spin boxes (±1e10, "%.2e", debounced) — arrows and wheel; applied on the next frame, which is the debounce
- [ ] Buttons: "Screenshot", "Data", "Clear", "Update", "Contrast", "Export…"
- [x] Count fields visible / total
- [x] "inf" and "NaN" masking checks (on by default)

## mask_nan_inf_off — NaN / inf masking off

- [x] Unchecking NaN / inf keeps non-finite rows on the plotted axes, and the counts change accordingly (12237 / 12237, as Qt)

## gate_rectangle — Rectangular gate dragged on the 2-D plot

- [x] Dragging a rectangle (with a rubber-band preview) on the 2-D map adds two range gates, one for the x parameter and one for the y parameter
- [x] Map, marginals and visible count show only the gated bursts
- [x] Selection section: "Cluster" button, cluster spin box (-1 = all), "colour" check, "BID", "clear", "load", "save" (Cluster/BID/load/save are other groups' features)
- [x] Gate table columns: Parameter | Min | Max | Invert | Enable. The table is a `data_table` view spec over `GateList.records()`; it holds all four gate kinds (interval, G2D, region, mask), and a non-interval shows what it is in Min/Max ("Bitmap", "G2D"/"2 σ", the region's shape)
- [~] Clicking a cell edits the name / Min / Max (range gates only): a double click opens Min/Max for typing (emtk's table convention); Parameter is not editable in the emtk table
- [x] Double-clicking a row deletes it (on a non-editable cell, e.g. Parameter); the Delete key deletes the selected rows (all of them after Select All)
- [~] Row numbers (Qt's vertical header) are not shown

## gate_invert_disable — Gate table: invert and disable

- [x] Invert check per gate (keep what is outside)
- [x] Enable check per gate
- [x] The plot updates immediately on either (the next frame recomputes; no timer)

## selection_table_menu — Selection table context menu

- [x] "Select All" (marks every row; Delete then removes them all)
- [x] "Clear"
- [x] "Delete"
- [x] "Send selection to ▸" submenu; it is disabled, with the reason in its title, when there is no ChiSurf RPC, no data, no gate, or no analyses. In the browser the reason is that ChiSurf's RPC needs a native socket

## canvas_context_menu — 2-D canvas context menu

- [x] "Copy 2D Histogram (CSV)" to the clipboard (tab separated, as Qt; `emtk.clipboard`: host hook, `navigator.clipboard` in the browser, pbcopy/clip/xclip on the desktop)
- [x] "Copy 1D Histograms (CSV)" to the clipboard
- [~] "Send to Napari": opens napari in its own process on the desktop. When napari is missing the row is disabled and says "napari is not installed" (no installer prompt); in the browser it says "not in the browser"
- [~] "Fit gate to the population here" (with its tooltip): the menu row has no tooltip (emtk menus have none); the result is reported on the status line
- [x] "Send selection to ▸" submenu (FCS / TCSPC / PDA / PCH targets discovered over ChiSurf RPC; disabled with the reason when there is no connection)

## pick_population — Fit gate to the population here

- [x] Right-click seeds a local 2-D Gaussian fit around the cursor; the fit re-centres on the population. Fixed, not copied: the click is taken in data units, and the population is found in display-scaled units (`core/population_pick.py`: climb to the local density maximum, grow downhill to 25 % of the peak, correct the covariance for the cut). The Qt model half used a raw-unit radius that cut a sliver (105 of 12237 bursts kept); the emtk pick keeps the FRET population (3976 at the scenario's click, 3819 after the scenario's second pick at (3.2, 0.35))
- [x] The fitted ellipse is added as an elliptical gate (type G2D, 2 σ) in the gate table and drawn on the map (every enabled G2D gate is outlined)
- [~] The "refused" shot shows the working pick (the gate fitted at the clicked population) instead of Qt's refusal

## z_axis_dynamic — z axis panel: dynamic z-selection

- [x] "dynamic z-selection" check enables the z axis
- [x] z parameter combo, 1-D bins, Normalized / Log / Auto-scale checks, "Set"
- [x] "z range" min / max fields
- [x] Dynamic-selection check
- [x] "select" button (turn the range into a gate) and "Auto"
- [x] z marginal histogram with a draggable range (two drag lines); dragging it re-gates the plots live while dynamic selection is on (1725 / 12237, as Qt). Measured: a recompute with a z gate, an interval pair and a G2D gate takes ~4 ms at 1e5 rows and ~15–20 ms at 1e6, once per frame however many drags arrived (no timer)

## z_add_selection — z range → gate ('select')

- [x] "select" adds the current z range as a range gate on the z parameter (1725 / 12237, as Qt)
- [ ] During playback gating the current slice is added as a gate too (playback group)

## draw_mask — Draw Mask panel: paint and apply

- [x] "Enable drawing" check; the rubber-band gate is off while drawing
- [x] Draw / Erase radio buttons
- [x] "Cat:" category spin box, 1..255
- [x] "Brush:" spin box, 1..50 px (radius on screen, the Qt kernel)
- [x] Painted mask overlay on the 2-D map, one colour per category. Fixed, not copied: strokes register (`core/mask_paint.py`, dabs along each drag segment); the "painted" shot shows the X stroke
- [x] "Load Mask" (integer TIFF) and "Save Mask" (integer TIFF), through emtk's file dialog
- [x] "Clear" (clear the mask)
- [x] "Apply" turns the painted category into a mask gate in the gate table ("Bitmap 1 (Tau (green), Proximity ratio)", 578 bursts kept)
- [x] Changing bins or axes clears the mask and stops drawing (Qt behaviour)

## playback — Playback panel (window mode)

- [x] "Axis" combo (blank plus every parameter; defaults to the Frame or mean-macro-time column)
- [x] "Steps" (1..100000, default 100; one step per value on an index axis, capped at 1024)
- [x] "Step" slider (0..steps-1); its tooltip shows the slice and the surviving count (emtk: the hover tooltip of the Step slider and its field)
- [~] Transport buttons: ◀◀ One step back, ◀ Play backward, ⏸ Stop, ▶ Play forward, ▶▶ One step forward (pressing the running direction again stops). emtk and Qt now both label Stop ■, because no font in the emtk atlas or a browser has ⏸ (it drew as a placeholder). Playing is timed by the frame loop (PlaybackViewModel.tick), not a QTimer, so it also runs in a browser.
- [x] "Mode": Window / Integrate / Stack (Stack does no gating)
- [~] "Speed" slider, 1..60 fps. The emtk app reads the rate from the user's settings file (~/.ndxplorer/mfd.settings.json, through settings.bundle), so the old frame_duration_ms 25 there shows as 40 fps. The Qt window reads only the packaged file (10 fps) and ignores the user's.
- [x] Window and Integrate modes gate the plots to the current slice (87 of 12237 at step 5 of 20, the same as the Qt window)
- [~] The panel is always there. The Qt window hides it until data is loaded; emtk draws it disabled instead, because the fold belongs to the core spec.

## playback_image_frames — Playback over image frames

- [x] With image data the playback axis is Frame; stepping walks the frames (10 steps, one per frame)
- [x] Integrate mode accumulates frames 0..k. The emtk shot shows Tau/Proximity axes instead of x/y pixel with a weight, because image mode on open belongs to open_image_h5 (io group). The playback state matches: Frame, 10 steps, Integrate, step 5.

## clustering_dialog — Clustering dialog ('Find structure'), every method page

- [x] Opened by "Cluster" (tooltip "Open clustering dialog"); non-modal; Escape or close hides it — a movable `emtk.dialog_window` with ✕; Escape over it closes; the settings survive hiding
- [x] "Method:" combo: PCA / UMAP / HDBSCAN / K-means (default K-means)
- [x] "▦ Columns (n)" button opens the column chooser
- [~] Grey one-line explanation of each method — shown under the combo in the default text colour (emtk default style, no per-feature colours)
- [x] PCA page: Components (2..10, default 2), "Standardise columns" (on)
- [x] UMAP page: Neighbours (2..100, default 15), Min. distance (0..1, default 0.1), Components (2..3), Metric (euclidean, manhattan, chebyshev, minkowski, canberra, braycurtis, cosine, correlation, hamming, jaccard), "Advanced"
- [x] UMAP Advanced: Parallel jobs (-1..64, "All cores"), Learning rate (0.1..10), Initialisation (spectral / random / pca), Spread (0.1..5), Epochs (0..2000, "Auto") — special value texts via view_form `special_text`
- [x] HDBSCAN page: Min. samples (default 5), Min. cluster size (default 50)
- [x] K-means page: Clusters (1..20, default 3)
- [x] Buttons: "▶ Run", "■ Cancel" (shown while running, reads "Cancelling…"), "📈 Plot" (UMAP only), "💾 Save" (labelling methods, once labels exist) — emoji dropped from Plot/Save (the emtk font has none)
- [x] Progress pane: message plus an indeterminate bar ("Running…", "Finished.", "Cancelled or failed.") — view_form `progress` section; the run is an `emtk.tasks` task (thread on desktop, steps in the browser)
- [x] Asks "Select columns?" when a labelling method is run with no columns chosen (No uses the x/y/z axes)
- [~] In a browser (Pyodide) K-means/HDBSCAN/PCA fall back to scikit-learn; UMAP says it cannot run there (umap-learn needs numba)


## column_selection_dialog — Column selection dialog

- [x] Title "Select Columns for Clustering"
- [~] Hint text on keyboard navigation (Up/Down, Ctrl+Space, PageUp/PageDown, Home/End) — says what the emtk table does: Up/Down, PageUp/PageDown, Home/End move; a click on the box toggles (no Ctrl+Space)
- [x] "Filter:" field ("Enter text to filter columns")
- [~] One check box per column, in a scroll area — a data_table with a Use check column and the Column name
- [x] "☑ Select All" and "☐ Deselect All"
- [x] OK / Cancel


## clustering_kmeans_run — K-means clustering run, clusters coloured

- [x] Clustering runs in the background while the window stays responsive (`emtk.tasks`)
- [x] Labels are stored on the data; the cluster spin box can isolate one cluster (-1 = all)
- [x] "colour" check colours the 2-D map by cluster instead of by density — also while one cluster is isolated (Qt lost the colours there: the labels no longer matched the masked values)
- [x] "💾 Save" saves the clustering data to a folder (through the app's file service; writer.save_clustering_data is Qt-free now)


## clustering_pca_run — PCA run: loadings report

- [x] The result text lists which parameters carry the variance (the loadings) — plain text, one line per component and the rows/variance footer
- [x] PC columns are added and can be picked on the axes


## umap_run — UMAP via the clustering dialog

- [~] Missing umap-learn: offers the installer; a cancelled or failed install ends in "Installation was cancelled or failed, so this method cannot run." — the emtk shot shows the offer (Install/Cancel); Install runs conda as a task with its log in the progress window, Cancel gives the same message. In a browser: "not available in the browser" (numba)
- [x] Progress dialog: "UMAP Computation Progress", log view, status line, auto-closes after 3 s on success, "Close" on error — the log is UMAP's own verbose/tqdm output; Cancel while running
- [x] UMAP_1…UMAP_n columns are added ("Added UMAP_1…UMAP_n. Pick them in the axis controls to plot.") and can be used as axes — verified with umap-learn 0.5.12 (outside arm64, `pip --target` scratch path)
- [x] "📈 Plot" opens a "UMAP Projection" window (UMAP 1 / UMAP 2 axes, a legend per cluster when labels exist; a 3-D view for 3 components) — implot / implot3d


## view_umap_action — View > UMAP

- [x] View > UMAP opens UMAP (Qt: broken, `umap_helpers.on_show_umap` does not exist; nothing happens) — opens Find structure on UMAP (fixed in the Qt window too)


## gaussian_fit — Gaussian Fit panel: fit 2-D Gaussians

- [x] View > Fit Gaussians shows the "Gaussian Fit" tab; while that tab is active, clicks on the map add seed Gaussians (point mode)
- [x] Buttons "🎯 Fit", "✕ Clear", "🔍 Select", "⚙ Settings" — without the emoji
- [x] "Selection σ:" (0.1..4.0, step 0.2, default 1.0)
- [x] "Gaussians" table: per component x, y, σx, σy, ρ, w, with Name / Value / Fixed / Lo / Hi / Bounds columns (σ ≥ 0, -1 ≤ ρ ≤ 1, w ≥ 0); add / remove rows; Delete removes the selected components — names without subscripts (x1, σx,1)
- [x] Parameters can be fixed and linked (crosslinked constants) — a Link column: type a parameter name (sd_x_1, or "Group: name" of another registered table), empty unlinks
- [x] Checks: "Select point", "Marginals" (on), "Log Gauss" — Log Gauss now fits and draws in log space (Qt only recorded it in the saved axes)
- [x] "💾 Save" / "📂 Load" (.json / .csv; "Axis Mismatch" warning) — a saved _gaussians.csv loads again (Qt read its '#' header as the column row)
- [x] Ellipses on the 2-D map and Gaussian curves on the marginals
- [x] Warnings "No Gaussians", "No data", "No histogram"
- [~] A click's seed width is the local spread at the clicked bin (Qt read the transposed bin), so the unfitted seeds differ from the Qt "points" shot; the fitted values match


## gaussian_select — Gaussian Fit: turn a component into a gate

- [x] "🔍 Select" adds the chosen component as an elliptical gate at Selection σ — through `model.gates.add_gaussian`; the gate list then outlines it, and the component is no longer drawn by the panel while it is that gate (10257 of 12237 kept, as in Qt)


## gmm_settings_dialog — GMM Settings dialog

- [x] "⚙ Settings" opens it (Qt: broken, wrong import path, the button does nothing) — fixed in the Qt window too
- [x] "Tolerance (tol)", "Reg. covar", "Max iterations", "Verbose", "Weight floor", "Local window (bins)" — Weight floor is applied to the fit now (it was stored and ignored)
- [x] "Fix new means by default"
- [x] OK / Cancel / "💾 Save" (to gmm_settings.json in the user folder)

## overlays_curve — Overlays: static FRET line on Fd/Fa vs Tau

- [ ] "Equation:" combo with the predefined curves, "Add Curve", "Number of points:" (10..999, default 500), "Save CSV"
- [ ] Each curve is a checkable group "<name> N" (the check is visibility) with "Equation: y =" or "Function:", a read-only "Filled: y =" field, a Color button, "Fit", "Delete", and a parameter table (Name / Value / Fixed / Lo / Hi / Bounds)
- [ ] The curve is drawn over the 2-D map in its colour and updates live when a parameter changes
- [ ] Curve parameters can be linked to constants

## overlays_equation_list — Overlays: predefined equation list

- [ ] Items: Custom Equation, Perrin-Equation, Perrin 2x rho, FD/FA vs tau (static line), FD/FA vs tau (dynamic line), E vs tau (static line), kFRET vs RDA, E vs tau (dynamic line), Static FRET Line (Gaussian Distribution), WLC FRET Line (Worm-Like Chain), Mixture FRET Line (Gaussian + WLC), Dynamic FRET Line (2-state Gaussian), Circle
- [ ] The list is read from the user's curve_equations.yaml, so it can be extended

## curve_fit_dialog — Fit curve to data dialog

- [ ] Title "Fit curve to data"
- [ ] "Fit to:" Displayed data (y vs x) / X marginal histogram / Y marginal histogram
- [ ] "Fit through:" the cloud (every populated bin) / the population of each column / the mean of each column
- [ ] "Scan first" check (on)
- [ ] Hint about free, fixed and crosslinked parameters
- [ ] Parameter table (Name / Value / Fixed / Lo / Hi / Bounds), plus a second "nDXplorer parameters" table when constants take part
- [ ] Status line (red error; green result "reduced χ² = … · k=v")
- [ ] Inline progress with Cancel; "Fit" / "Close"
- [ ] The fitted values are written back to the curve and the constants

## parameters_panel — Parameters tab (constants)

- [ ] Constants table: gG/gR, Bg, Br, By, PhiA, PhiD, alpha, tauD0, beta, r, forster_radius, omega_r_um, T_K, eta_Pa_s, KB
- [ ] Columns Name / Value / Fixed / Lo / Hi / Bounds; an edit recomputes only the dependent columns (debounced) and redraws
- [ ] Row context menu: Copy, Paste, Link / Unlink (crosslink to fit parameters)
- [ ] "Add parameter" button (tooltip "Add a new constant (name + value)")
- [ ] "Save" button (tooltip "Save parameters"), writes mfd.constants.json

## add_parameter — Parameters: Add parameter prompt

- [ ] Asks for the name ("Parameter name:"), then the value; a duplicate name is refused with a message

## equations_panel — Equations tab and names dialog

- [ ] The panel can be reached from the UI (Qt: it cannot, see menu_view)
- [ ] Equation table: Output | Expression | status (✓/✗ with the error as tooltip)
- [ ] Preview line and status line ("N equation(s), all valid" / "… with problems")
- [ ] "➕" add, "➖" remove, "🔤" names & functions
- [ ] "Apply" (validate all and recompute the derived columns)
- [ ] "Names & functions" dialog: hint, list of column / constant / function names (click inserts), Close
- [ ] Load / save of equation files

## store_editor — Data button → Table Editor

- [ ] Title "Table Editor", about 900×600, edits a copy of the data
- [ ] Search field ("🔍 Search…")
- [ ] Column picker ☑, hide-empty ✕, colour-by-value 🎨, colour scope ∥, CSV export
- [ ] Status "N rows × M columns"
- [ ] Sortable table, one column per parameter; edits are staged
- [ ] Cell context menu: Copy, Copy with headers, Paste, Export as CSV…, Select all, Filter this column…, Hide this column, Resize columns to contents
- [ ] "↺ Reset", "✓ Apply" (writes back and redraws), "✕ Cancel"

## axis_control_dialog — View > Axis Control

- [ ] Title "Axis Control", resizable (with a size grip and a hint about resizing)
- [ ] X Plot: Bottom / Top / Left / Right axis
- [ ] Y Plot: Bottom / Top / Left / Right axis
- [ ] Z Plot: Enable Z Plot, Bottom / Left axis
- [ ] 2D Plot: Bottom / Top / Left / Right axis
- [ ] Overlay Plot: Bottom / Top / Left / Right axis
- [ ] Axis Label Settings: Enable All Labels; Y Plot labels (Top, Right); X Plot labels (Top); Z Plot labels (Bottom, Left)
- [ ] Font Settings: Tick size (6..48, default 8), Title size (6..64, default 10), Bold titles, Title color (colour picker)
- [ ] OK / Save (axis label settings to the settings folder) / Cancel / Apply

## performance_settings — Settings > Performance Settings

- [ ] "Performance Configuration" heading and description
- [ ] Histogram Computation: Use Fast Histogram Optimizations, Use Parallel Computation, Histogram Threads (-1..64), Plot Backend (pyqtgraph / matplotlib)
- [ ] Memory & Caching: Aggressive Caching, General Cache (MB) 5..1000 (default 50) (Qt shows the group title as "Memory _Caching" because the & is read as a mnemonic)
- [ ] Advanced Options info, including "Settings are saved to: ~/.ndxplorer/mfd.settings.json"
- [ ] "↺ Reset to Defaults", "✕ Cancel", "✓ Apply", "✓ OK"; confirmation messages

## publication_export — Export… (publication figure)

- [x] "Export…" button next to Screenshot (core spec plot_corner; its tooltip is the core spec's "Export a publication figure.")
- [x] "Format:" PDF (vector, default) / SVG (vector) / PNG (raster)
- [x] "DPI (raster):" (default 300), enabled only for PNG
- [x] "Include X/Y marginal histograms" (on)
- [x] "Transparent background" (off)
- [x] "Export…" asks for the file, then writes the figure (vector through matplotlib); "Cancel". emtk: the bytes go to app.io_service.save_bytes, which asks for a path on a desktop and downloads in a browser. Without data it says why (Qt: the same message).

## screenshot_button — Screenshot button

- [x] "Screenshot" asks for a file (PNG / JPEG / BMP) and saves the plot area — the whole window, as Qt's `grab()` does, redrawn without dialogs; in a page it is a PNG download. [-] Qt also copies it to the clipboard; emtk has no image clipboard

## report_tool — File > Make Report

- [ ] Title "ndX Report Tool", 900×600, split view
- [ ] "Analysis folders (drop here):" list (multi-select, accepts folder drops; context menu "Copy Path(s)")
- [ ] "Add…" (folder chooser), "Remove", "Clear" (confirm)
- [ ] "Report YAML (report.yaml):" editor with "Load…" / "Save…" (YAML / JSON)
- [ ] "Browse generated images": folder field, "Plot:" combo (context menu "Copy Image Path"), image preview
- [ ] "Clear Reports" (confirm) and "Generate Reports" (validation, progress "Generating reports…" with Cancel, optional combined DOCX)

## fix_report_tool — Help > Fix Report Tool

- [ ] Help > Fix Report Tool (Qt: broken, it shows "Fix Report Tool Error: No module named …"); implement it or drop the entry deliberately

## find_projections — View > Find informative projections…

- [~] Window "Find informative projections" (520×640) with Help (?) and Guide. emtk: a tool window inside the app (dragged by its title, closed with ✕), with Guide and ? in its title row, because a browser has no second top-level window.
- [x] "Score" choice: Class separation (k-NN) (only when classes exist), Population structure (2-means), Correlation (Pearson), Correlation (Spearman)
- [x] "Classes" choice (for separation only): Gate: inside vs outside, Gates: one population per gate, Clusters, z parameter: <name>. Clusters come from a feature's cluster_labels (analysis group).
- [x] "Sample" (200..200000, default 5000)
- [x] Start / Pause; the Start label reads Start / Continue / Restart with new settings / Finished
- [x] Status "n/N scored (p %) · paused / finished / k failed" and sample info "n of N bursts sampled · k parameters left out"
- [x] "Ranked views - click one to show it" table: score bar, x, y, with a filter; clicking a row sets the axes; the selected row's note sits under the table. Scoring runs through emtk.tasks in slices: a thread on a desktop, steps between frames in a browser.
- [x] Guided tour: What this panel does → Score → Start (waits for the press) → table. emtk: the control is outlined and a step card sits beside the window.

## find_projections_iris — Find informative projections on iris (class separation)

- [x] Class separation works with an integer class column as the z parameter ("z parameter: class")
- [x] Best-ranked view is petal length × petal width (known answer; 0.927, the same six scores as the Qt window), applied to the axes

## find_projections_z — View > Find informative projections (z axis)…

- [x] Window "Find informative z parameters"; the table has a "Parameter" column instead of x / y
- [x] Clicking a row sets the z parameter (and turns the z gate on, as the Qt window's checkBoxEnableZ)

## save_burst_ids — Save Burst IDs ('BID' / File > Save > Burst IDs)

- [x] Folder chooser "Folder for Burst IDs"
- [x] Progress window "Saving Files" / "Saving Burst ID files..." (Cancel) — on a thread, `n / total files`
- [x] "Process Burst IDs" dialog: "Compute microtime histogram" (on), "Open FCS Correlator Wizard to correlate BST files" (off), OK / Cancel — `io/burst_ids.view.json`
- [~] Follow-up messages ("Plugin Not Available", "No BST Files Found", "Launch Error"): the histogram answer is Qt's "Plugin Not Available"; the correlator is a ChiSurf Qt wizard that cannot run in this window, so it says "Plugin Not Available" with the folder and file count (or "No BST Files Found"). No "Launch Error" (nothing is launched). BID is enabled only for a table with First/Last File and First/Last Photon (Qt enables it always and fails later)

## set_default_axis — Settings > Set default axis

- [ ] Stores the current x / y / z / weight in the settings `default_axes` and confirms with a message

## load_settings_dialog — Settings > Load settings

- [ ] File chooser "ndX settings file"; loading re-applies equations, constants, axis settings and colormap

## save_axis_settings_dialog — Settings > Save settings > Axis settings

- [ ] Save-file chooser for the per-parameter axis settings JSON

## browse_working_path — Browse (working path)

- [x] "Browse" (tooltip "Change working path") opens a directory chooser and sets the Path field ("Select current path", Qt's caption)

## selection_save — Selection 'save' (gates to *.selection.json)

- [x] "save" writes the gates to a *.selection.json file; "load" reads them back (file chooser "Selection JSON"), any shape; the name gets `.selection.json` when it lacks it. Without ChiSurf (a page) interval gates still save and load

## clear_plot — Clear

- [x] "Clear" (tooltip "Clear plot") empties the plots and the Path field (Qt quirk, do not copy: after Clear the map shows the hidden 1000-row placeholder dataset, two synthetic blobs, while the total still reads 12237)
- [x] "Update" (tooltip "Update plot") redraws
