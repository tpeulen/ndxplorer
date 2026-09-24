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

- [x] Window title "ndX" (plus the file name once data is loaded) — `NdxApp.window_title`, carried onto the window by every emtk host (emtk b49285a: native, Tk, Qt, the page title)
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
- [x] The Frame column drives playback (see playback_image_frames: axis Frame, 10 steps, 269923 of 449532 at step 5)

## menu_file — File menu (+ Import, Save submenus)

- [x] File > Import > "Import Text files (*.csv,*.dat)" (Ctrl+O)
- [x] File > Import > "Analysis file (*.zip, *.hdf)"
- [x] File > Import > "Analysis-Folder" (Ctrl+I)
- [x] File > Import > "ChiSurf-Sampling"
- [x] File > Save > "Burst IDs"
- [x] File > Save > "Histograms" (Qt: broken, not connected to anything) — works in the emtk app: the marginals and the 2-D map as one tab-separated file (features/window.py)
- [x] File > "Make Report"
- [~] File > "Print window" (Qt: broken, not connected) — saves a picture of the window (the Screenshot action) for the user to print; no printing system
- [x] File > "Exit" (Qt: broken, not connected; the window close button works) — closes the window through its host; disabled in a browser page, which has no window to close

## menu_settings — Settings menu (+ Save settings submenu)

- [x] Settings > "Performance Settings" (opens the dialog, see performance_settings; usable without data)
- [x] Settings > "Load settings" (io file chooser "ndX settings file"; see load_settings_dialog)
- [x] Settings > Save settings > "Axis settings" (save-file chooser; see save_axis_settings_dialog)
- [x] Settings > Save settings > "Constants" (writes mfd.constants.json in the settings folder: the Parameters tab's Save, values + bounds + fixed, as Qt's save_parameters; the plain values when that tab is not loaded)
- [x] Settings > Save settings > "Equations" (Qt: broken, not connected) -- works: the Equations tab's save (a save-file chooser, default mfd.equations.yaml); `settings/persist.write_equations` when that tab is not loaded
- [x] Settings > "Set default axis" (needs data, as it needs axes)

## menu_view — View menu

- [x] View > "Plot controls" / "Parameters" / "Overlays" (checkable, enabled, checked in parity/emtk/menu_view--menu.png; they toggle the tabs: core for Plot controls, the overlays feature for the other two)
- [x] View > "Fit Gaussians" (checkable entry present and enabled; function: the analysis feature, gaussian_fit)
- [x] View > "Equations" (checkable, enabled; shows the Equations tab, overlays feature)
- [x] View > "UMAP" (entry present and enabled; function: analysis feature, view_umap_action)
- [x] View > "Find informative projections…" (entry present and enabled; function: find_projections)
- [x] View > "Find informative projections (z axis)…" (entry present and enabled; function: find_projections_z)
- [x] View > "Axis Control" (opens the dialog, see axis_control_dialog; usable without data)

## menu_help — Help menu

- [x] Help > "Help" (Qt: disabled in the .ui, not connected) -- works: a help window (what ndX does, the five steps, the project URL)
- [-] Help > "Fix Report Tool" (Qt: broken, see fix_report_tool) -- dropped, justification under fix_report_tool
- [x] Help > "About" (Qt: not connected) -- works: ndXplorer, tttrlib, emtk, numpy, matplotlib and Python versions, author, licence, URL
- [~] Help > "Update" (Qt: not connected) -- an "Update" window with the installed version and how to update (conda / pip, restart; in a browser: reload the page). It installs nothing itself: an app that rewrites its own environment is what deps_installer warns about

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
- [x] Changing bins disables mask drawing and clears the mask (Qt behaviour) — selection feature, with a status line saying so

## weights — Weighted histograms

- [x] "weight" check (tooltip "If checked, histograms are weighted by selected parameter")
- [x] Weight parameter combo lists every parameter; weighting applies to the map and the marginals (same counts and vmin/vmax 3.10e+01 / 4.50e+04 as Qt)

## colour_log_contrast — Colormap, log counts, auto contrast, vmin/vmax

- [x] Colormap combo (the pyqtgraph map list: viridis, inferno, magma, plasma, cividis, turbo, CET-*…)
- [~] "log #" check for a log10 colour scale of the counts — toggling it re-derives vmin/vmax in log10 units; the Qt window keeps its linear limits over the log image (1..200 on values 0..2.3), which washes the map out
- [x] "Contrast" button sets vmin / vmax automatically
- [x] vmin / vmax spin boxes (±1e10, "%.2e", debounced) — arrows and wheel; applied on the next frame, which is the debounce
- [x] Buttons: "Screenshot", "Data", "Clear", "Update", "Contrast", "Export…" (emtk: Contrast and Update on the toolbar over the plots beside the colormap, log # and vmin/vmax; Screenshot, Data, Export… and Clear two by two in the corner between the marginals, or at the toolbar's end when the user drags the marginals too small for them)
- [x] Count fields visible / total (emtk: "12237 / 12237" in the corner between the marginals)
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
- [x] During playback gating the current slice is added as a gate too (playback group) — PanelModel.z_select calls Feature.on_z_select (be26939); playback adds the slice once

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
- [x] "Step" slider (0..steps-1); its tooltip shows the slice and the surviving count (emtk: one slider that writes the step on itself -- a double click types an exact step -- where there was a field beside a slider showing the same number; the tooltip is on its hover)
- [~] Transport buttons: ◀◀ One step back, ◀ Play backward, ⏸ Stop, ▶ Play forward, ▶▶ One step forward (pressing the running direction again stops). emtk and Qt now both label Stop ■, because no font in the emtk atlas or a browser has ⏸ (it drew as a placeholder). Playing is timed by the frame loop (PlaybackViewModel.tick), not a QTimer, so it also runs in a browser.
- [x] "Mode": Window / Integrate / Stack (Stack does no gating)
- [~] "Speed" slider, 1..60 fps; in emtk one slider that writes "10 fps" on itself (double click to type a rate). The emtk app reads the rate from the user's settings file (~/.ndxplorer/mfd.settings.json, through settings.bundle), so the old frame_duration_ms 25 there shows as 40 fps. The Qt window reads only the packaged file (10 fps) and ignores the user's.
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
- [x] K-means/HDBSCAN run on tttrlib's kernels and PCA on NumPy, desktop and browser alike (no scikit-learn); UMAP says it cannot run there (umap-learn needs numba)


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

- [x] "Equation:" combo with the predefined curves, "Add Curve", "Number of points:" (10..999, default 500), "Save CSV"
- [x] Each curve is a checkable group "<name> N" (the check is visibility) with "Equation: y =" or "Function:", a read-only "Filled: y =" field, a Color button, "Fit", "Delete", and a parameter table (Name / Value / Fixed / Lo / Hi / Bounds)
- [x] The curve is drawn over the 2-D map in its colour and updates live when a parameter changes
- [x] Curve parameters can be linked to constants
- [~] The group's check is a check box on the first line of the group (emtk has no checkable group box); a function curve's source is a code editor instead of a one-line field (a `def` does not fit one line); the colour is a swatch with a hex field and an HSV picker instead of QColorDialog; the parameter table has a Link column; linking is a right-click menu (Copy / Paste / Link… / Unlink) and a dialog listing every registered parameter

## overlays_equation_list — Overlays: predefined equation list

- [x] Items: Custom Equation, Perrin-Equation, Perrin 2x rho, FD/FA vs tau (static line), FD/FA vs tau (dynamic line), E vs tau (static line), kFRET vs RDA, E vs tau (dynamic line), Static FRET Line (Gaussian Distribution), WLC FRET Line (Worm-Like Chain), Mixture FRET Line (Gaussian + WLC), Dynamic FRET Line (2-state Gaussian), Circle
- [x] The list is read from the user's curve_equations.yaml, so it can be extended (Qt: broken -- it read the shipped file first, so a user's copy was never seen; fixed in ndxplorer/core/overlay_curves.py for both windows)

## curve_fit_dialog — Fit curve to data dialog

- [x] Title "Fit curve to data"
- [x] "Fit to:" Displayed data (y vs x) / X marginal histogram / Y marginal histogram
- [x] "Fit through:" the cloud (every populated bin) / the population of each column / the mean of each column
- [x] "Scan first" check (on)
- [x] Hint about free, fixed and crosslinked parameters
- [x] Parameter table (Name / Value / Fixed / Lo / Hi / Bounds), plus a second "nDXplorer parameters" table when constants take part
- [x] Status line (red error; green result "reduced χ² = … · k=v")
- [x] Inline progress with Cancel; "Fit" / "Close"
- [x] The fitted values are written back to the curve and the constants
- [~] The status line is plain text in emtk's default colour (no per-feature styling); the fit runs on a thread on a desktop (the window stays live, Cancel stops it) and in the frame in a browser

## parameters_panel — Parameters tab (constants)

- [x] Constants table: gG/gR, Bg, Br, By, PhiA, PhiD, alpha, tauD0, beta, r, forster_radius, omega_r_um, T_K, eta_Pa_s, KB
- [x] Columns Name / Value / Fixed / Lo / Hi / Bounds; an edit recomputes only the dependent columns (debounced) and redraws
- [x] Row context menu: Copy, Paste, Link / Unlink (crosslink to fit parameters)
- [x] "Add parameter" button (tooltip "Add a new constant (name + value)")
- [x] "Save" button (tooltip "Save parameters"), writes mfd.constants.json
- [~] Debounce is one recompute per frame for all edits since the last frame (no timer); a Link column shows what a constant follows; "Link…" opens a list of every registered parameter group (fits, curves, Gaussians) instead of a submenu

## add_parameter — Parameters: Add parameter prompt

- [x] Asks for the name ("Parameter name:"), then the value; a duplicate name is refused with a message
- [~] One dialog with two steps (name, then "Value for 'name':") instead of two QInputDialogs

## equations_panel — Equations tab and names dialog

- [x] The panel can be reached from the UI (Qt: it cannot, see menu_view) -- View > Equations shows the tab and selects it; its check mark follows
- [x] Equation table: Output | Expression | status (✓/✗ with the error as tooltip)
- [x] Preview line and status line ("N equation(s), all valid" / "… with problems")
- [x] "➕" add, "➖" remove, "🔤" names & functions
- [x] "Apply" (validate all and recompute the derived columns)
- [x] "Names & functions" dialog: hint, list of column / constant / function names (click inserts), Close
- [x] Load / save of equation files
- [~] Buttons read "+", "−", "Names" (the default font has no emoji); the error of a ✗ row is shown under the table when the row is selected (a painter has no tooltips); the preview line is the selected equation written out (Qt's rendered preview is off for ndX's quoted names anyway); the names list has a filter box; Delete removes the selected row
- [~] The functions listed are those ndX's equation engine accepts (abs); the Qt dialog lists chisurf's (exp, sqrt, …), which the engine rejects (Qt: broken)

## store_editor — Data button → Table Editor

- [x] Title "Table Editor", about 900×600, edits a copy of the data
- [x] Search field ("🔍 Search…")
- [x] Column picker ☑, hide-empty ✕, colour-by-value 🎨, colour scope ∥, CSV export
- [x] Status "N rows × M columns"
- [x] Sortable table, one column per parameter; edits are staged
- [x] Cell context menu: Copy, Copy with headers, Paste, Export as CSV…, Select all, Filter this column…, Hide this column, Resize columns to contents
- [x] "↺ Reset", "✓ Apply" (writes back and redraws), "✕ Cancel"
- [~] The search field is the table's filter box; hide-empty, colour and one-scale are check boxes ("Hide empty", "Colour by value", "∥ One scale") and the picker and export are buttons ("☑ Columns…", "Export CSV…"); the columns keep a minimum width and the table scrolls sideways (a bar under the rows, shift + wheel); Select all selects rows (Copy copies the selected rows of the shown columns)

## axis_control_dialog — View > Axis Control

- [~] Title "Axis Control" in an emtk dialog window (movable, ✕/Escape close); not resizable: it is sized to hold every control, so the size grip and the "you can resize" hint went (the capture's resize_dialog step is a no-op)
- [x] X Plot: Bottom / Top / Left / Right axis (the ticks of the x marginal; Apply redraws, test_plot_axis_display)
- [x] Y Plot: Bottom / Top / Left / Right axis
- [x] Z Plot: Enable Z Plot (dynamic z-selection, as the Qt box drives checkBoxEnableZ), Bottom / Left axis (disabled until Enable Z Plot, as in Qt)
- [x] 2D Plot: Bottom / Top / Left / Right axis (the map gets ticks; none by default)
- [x] Overlay Plot: Bottom / Top / Left / Right axis -- present and disabled, as in Qt (the overlay is a drawing surface without axes in both apps)
- [~] Axis Label Settings: Enable All Labels; Y Plot labels (Top, Right); X Plot labels (Top); Z Plot labels (Bottom, Left) -- all present, individual boxes disabled while Enable All Labels is on (Qt); the x "top" and y "right" titles switch in the plots; the plots draw no y-top or z titles, so those three switches are stored (axis_labels.yaml) but show nothing
- [~] Font Settings: Title color (swatch + HSV picker + hex, emtk view_form kind "color") works on the axis titles. Tick size / Title size / Bold titles are not shown: the emtk app draws in emtk's default font by the user's directive; their values are kept in axis_labels.yaml for the Qt window
- [x] OK / Save (axis_labels.yaml in the settings folder, named by the settings' axis_labels) / Cancel / Apply

## performance_settings — Settings > Performance Settings

- [x] "Performance Configuration" heading and description
- [~] Histogram Computation: Use Fast Histogram Optimizations, Use Parallel Computation, Histogram Threads (-1..64) present and saved; Plot Backend is not a choice: the emtk app draws with emtk, and a note says the Qt window's backend is kept in the settings for it (Qt never saved that choice; `save_performance_config` now does)
- [x] Memory & Caching: Aggressive Caching, General Cache (MB) 5..1000 (default 50) ("Memory & Caching", no mnemonic)
- [x] Advanced Options info, including "Settings are saved to: ~/.ndxplorer/mfd.settings.json" and "Values in settings file override environment variables."
- [x] "Reset to Defaults", "Cancel", "Apply", "OK" (the ↺ ✕ ✓ glyphs dropped: not in emtk's font); "Settings Applied" message; Reset asks first and then shows the defaults (Qt: broken, it re-read the saved file, so nothing reset), Apply saves them
- Note: none of these values changes a computation in either app today (nothing reads PerformanceConfig), recorded in okf

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

- [~] Title "ndX Report Tool", 1000×700 emtk dialog window, folders left, config and images right (fixed split, no splitter handle)
- [~] "Analysis folders (drop here):" list -- a data_table (Folder, Report ✓ column replaces the green "processed" highlight); drops add the analysis folders found in what was dropped (Qt), right-click "Copy Path(s)"; single selection, not multi-select
- [x] "Add…" (io folder chooser), "Remove" (the selected folder), "Clear" (confirm)
- [x] "Report YAML (report.yaml):" editor (emtk TextEditor via view_form code_editor) with "Load…" / "Save…" (YAML / JSON, validated; a file that does not parse asks "Load as-is?")
- [x] "Browse generated images": folder field, "Plot:" choice, image preview (right-click "Copy Image Path" on the preview, not on the combo)
- [x] "Clear Reports" (confirm; also clears the analysis folders below a listed root) and "Generate Reports" (validation messages, one folder per frame with a progress bar and "Cancel", "Done"/"Canceled" message, combined DOCX offered through io save_bytes when python-docx is installed, which it is not in arm64, so that is said in the message); plus "Close". The work is ndxplorer/export/report.py, shared with the Qt tool; it fixes the transposed 2-D CSV/PNG

## fix_report_tool — Help > Fix Report Tool

- [-] Help > Fix Report Tool (Qt: broken, it shows "Fix Report Tool Error: No module named …") -- dropped from both menus (core 3cf8811). `ndxplorer.fix_report_tool` never existed in the history: a5a1b2a added the menu entry and a dangling import, so there is no intended behaviour to port. What "fixing" a report would mean -- a folder whose report is missing or stale -- is covered by the report tool itself: the Report column shows which folders have one, Clear Reports removes them, Generate Reports rebuilds the ones missing

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

- [x] Stores the current x / y / z / weight (and colormap) in the loaded settings file's `default_axes`, the rest of the file kept, and confirms with "Default axis settings have been updated." (settings/persist.write_default_axes, shared with Qt)

## load_settings_dialog — Settings > Load settings

- [x] File chooser "ndX settings file" (io service; filter ndX settings (*.settings.json)); loading re-applies equations (columns recomputed), constants (taken over by the Parameters tab), per-parameter axis settings, axis titles and colormap, and later saves go to that file

## save_axis_settings_dialog — Settings > Save settings > Axis settings

- [x] Save-file chooser "Axis settings file" (Axis file (*.axis.json), default mfd.axis.json) for the per-parameter axis settings: the axes on screen are taken first ("Set" for x, y, z), then written over the chosen file (or the packaged one), other parameters kept. It opens in the working folder, not in ~/.ndxplorer (the io service has no start-folder argument)

## browse_working_path — Browse (working path)

- [x] "Browse" (tooltip "Change working path") opens a directory chooser and sets the Path field ("Select current path", Qt's caption)

## selection_save — Selection 'save' (gates to *.selection.json)

- [x] "save" writes the gates to a *.selection.json file; "load" reads them back (file chooser "Selection JSON"), any shape; the name gets `.selection.json` when it lacks it. Without ChiSurf (a page) interval gates still save and load

## clear_plot — Clear

- [x] "Clear" (tooltip "Clear plot") empties the plots and the Path field (Qt quirk, do not copy: after Clear the map shows the hidden 1000-row placeholder dataset, two synthetic blobs, while the total still reads 12237)
- [x] "Update" (tooltip "Update plot") redraws

## ChiSurf-hosted window — what ChiSurf's ndX plugin adds

The scenarios below run the Qt window the way ChiSurf's ribbon opens it: the
plugin's `__init__.py` executed with `__name__ == "plugin"` (`capture_qt.py`
scenario key `"host": "chisurf"`). What that adds to the standalone window,
from `chisurf/plugins/ndxplorer/__init__.py` and `rpc_bridge.py`:

- `rpc_bridge.make_ndxplorer`: an in-process ChiSurf RPC client (`chisurf_rpc`), which gives the **ChiSurf Phasor** toolbar and panel and the "Send selection to" targets (PDA, burst FCS, burst MLE); and **the calibration stored in an opened `.pto` is restored** into the constants (factor table, background artifact, saved `fret_calibration`).
- the **Accurate FRET** toolbar: FRET calibration, Save calibration, Load calibration, Sync constants;
- the **MMFDB** toolbar (Open from MMFDB), only when `mmfdb.status` answers;
- the constants published as fitting parameters in the **Global View** (`window._bind_global_view`: since 2026-09-24 the window's own constants group through `core/chisurf_binding`'s one mirror; the "⟲ Sync constants" action went with the copy it synchronised).
- Not GUI: `cli.py` (`chisurf ndxplorer filter|image`, MMFDB-backed headless runs) and `mmfdb_launcher.open_burst_selection_from_mmfdb` / `send_path_to_ndxplorer` (other plugins open ndX with a path).
- Trap: ChiSurf's *menu* route (`run_plugin_from_dir`) opens the manifest's `entrypoints.gui` (`make_ndxplorer`) and never runs `__init__.py`, so a window opened from the menu has the Phasor toolbar and the restore, but **no Accurate FRET or MMFDB toolbar and no Global View parameters**; only the ribbon route runs the decoration.

## chisurf_toolbars — ChiSurf-hosted window: the toolbars and constants ChiSurf adds

- [~] Toolbar "Accurate FRET" (🎯 FRET calibration, 💾 Save calibration, 📂 Load calibration, ⟲ Sync constants) — the **FRET** menu (before Help): FRET calibration…, Save calibration…, Load calibration…, in the app whether or not ChiSurf hosts it; no toolbar button (the toolbar's space was just given to the map)
- [-] "⟲ Sync constants" (Global View -> window, then back) — not needed: the emtk constants *are* the registered parameter group (`overlays.ConstantsPanel` registers it as owner `ndxplorer`, the slot the Qt window publishes in too), so a Global View edit is the window's value; there is no copy to sync
- [ ] Toolbar "ChiSurf Phasor" (◐ Phasor / FRET…, ✕ Clear) — not ported (see chisurf_phasor)
- [ ] Opening a `.pto` restores its stored calibration (Qt shot `parameters_restored`: gG/gR 1.333, PhiA = PhiD = 1, alpha 0.157, beta 0.0674, r 0.9435, Bg/Br/By 4.24/0.538/2.02) — not yet: the restore is `calibration_bridge.restore_calibration_from_container`, held for the accurate-FRET library move. The emtk app opens with the settings' constants, and a calibration started there starts from them (see accurate_fret_run)
- [-] Global View publishing — the emtk constants group is registered in ChiSurf's parameter-group registry already; it reaches the Global View once the emtk app runs inside ChiSurf's process, which no ChiSurf plugin does yet

## accurate_fret_options — Accurate FRET > FRET calibration: the options dialog

- [x] Window "FRET calibration" — FRET > FRET calibration…; the form is `ndxplorer/analysis/fret_calibration_options.view.json`, the *same file* the Qt window's AutoForm shows (moved from the plugin into ndX)
- [x] Determine: α leakage, δ direct excitation, γ detection / QY, β excitation flux (on), R₀ Förster radius (off), two per line, with their tooltips
- [x] Background: Take from (fit / measurement / constants / none), Min. reference bursts (20)
- [x] How (folded): γ from (auto / es / lifetime / combined), Use light-path priors, Bootstrap resamples (50), τ_D(0) (ns) (from the window's tauD0), Linker σ (Å) (6), Add accurate E / S / R_DA columns
- [x] When it finishes: Store the calibration in the measurement (on)
- [x] 🎯 Calibrate / Cancel — Calibrate / Cancel; without a calibration backend Calibrate is off and a line says why (the algorithm is moving into a compiled library)

## accurate_fret_run — Accurate FRET > FRET calibration: a real run and its report

- [x] Progress "FRET calibration…" with Cancel while it runs — a DialogWindow with the step message, a bar and Cancel; the run is an `emtk.tasks` task (a thread on a desktop, slices in a page)
- [x] The factors are written into the constants and ndX's columns recomputed (Parameters tab after the run)
- [x] New columns FRET efficiency (accurate), Stoichiometry (accurate), R_DA (accurate), Population, Off static FRET line, selectable on the axes
- [x] Stored in the measurement when "Store…" is on, before the report opens; the report says where
- [~] Report window "FRET calibration — applied": the text (factors ± uncertainty, populations, γ routes, constants before → after, held factors, fitted background, new columns) — the same text (`fret_calibration.report_text`, moved out of the plugin) in a folded "Full report", with tables above it: correction factors (value, ±, written/held), FRET populations (bursts, E, σE, S, R, τf), constants (before, after)
- [x] Save calibration… / Save report… / Close
- [x] Numbers: from the same starting constants the emtk run gives α 0.15700104, β 1.05988512, γ 0.75022932, δ 0.06742034 and uncertainties identical to the Qt run, and the same report text (verified with ChiSurf's current algorithm behind the backend contract; the shipped app has no backend until the library lands)

## calibration_save_load — Accurate FRET > Save calibration / Load calibration

- [x] Save: "Store the calibration in the measurement?" with the container path, Yes / No / Cancel; Yes stores into the `.pto`, No asks for a `*.fretcal.json` file (io service: a dialog, a download in a page), then says where it went
- [x] Save without a container goes straight to the file
- [x] Load: "This measurement carries N stored calibration(s). Load the most recent one? No opens a file instead." Yes / No / Cancel
- [x] "Apply this calibration to the window?" with when/where it was saved and the changes (or "Nothing would change."), Yes / No; nothing changes before Yes
- [x] A stored report opens in the report window "FRET calibration — loaded"
- [x] Same file format both ways (`ndxplorer/io/fret_calibration_io.py`, moved from the plugin's `calibration_io.py`): a file saved by one window loads in the other

## mmfdb_open — MMFDB > Open from MMFDB (ChiSurf-hosted)

- [~] Toolbar "MMFDB" > "Open from MMFDB" (dataset picker, then open like a drop) — File > Import > "From MMFDB… (only inside ChiSurf)", disabled: it needs ChiSurf's MMFDB client
- [-] (Qt: broken) The Qt toolbar is never added: the plugin builds `MMFDBClient(inprocess=True)` without a session token, and `mmfdb.status` requires one, so `status()` raises and the toolbar is skipped silently (the log's toolbars list has no MMFDB entry)

## chisurf_phasor — ChiSurf Phasor > Phasor / FRET… (ChiSurf-hosted)

- [ ] "Phasor / FRET…" shows the ChiSurf Phasor / FRET dock: Phasor overlays (Frequency, Harmonic, Lifetimes, Donor τ0, Show: universal semicircle / iso-lifetime grid / lifetime ticks / polar grid / FRET trajectory, Draw overlays, Clear), FRET line (Model, Sweep param, Min, Max, Points, Draw FRET line), Derived columns (τ φ/M columns) — not ported: it needs a ChiSurf RPC client, which the emtk app does not get yet (`--chisurf-rpc` does not reach `NdxApp`)
- [ ] "✕ Clear" removes the ChiSurf overlays — not ported (as above)
