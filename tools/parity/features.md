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

- [ ] Window title "ndX" (plus the file name once data is loaded)
- [ ] Layout: a panel column on the left with tabs Plot controls / Parameters / Overlays, plus Equations and Gaussian Fit (hidden until the View menu shows them), and a "Plot" area on the right; the column is about ¼ of the width
- [ ] Panel tabs can be rearranged (drag or split) and have a context menu (the ChiSurf DockArea)
- [ ] Menu bar: File, Settings, View, Help
- [ ] Status bar
- [ ] Controls are disabled until data is loaded (all actions except Import / Select working path, all panels, Screenshot, Contrast, Data, Save parameters, weight, z)
- [ ] Keyboard shortcuts Ctrl+O (Import Text files) and Ctrl+I (Analysis-Folder)
- [ ] Opening a folder or file by dropping it on the Path field (or on the window) works like the CLI `--file` / `--folder`
- [ ] CLI: `ndx --file`, `--folder`, `--test-data`, `--chisurf-rpc host:port`, `-v` / `--debug`, plus the subcommands `filter` and `image`
- [ ] Every control keeps its tooltip (see the per-scenario items)
- [ ] Qt quirk, do not copy: a fresh window holds a hidden 1000-row placeholder dataset (Tau (green), Proximity ratio, r Experimental (green)), so the first Import already asks the merge question

## startup_empty — Start-up, no data

- [ ] Splash image ("NDXPLORER — Visualization and analysis for fluorescence") fills the plot area until data arrives
- [ ] Axis combos are empty; bin defaults 81 (1-D) / 31 (2-D); ranges 0..1
- [ ] Path field shows the placeholder "Drop folder here."
- [ ] Marginal plot axes are visible but empty
- [ ] File menu entries shown in the no-data state (Import stays usable)

## open_mfd_folder — File > Import > Analysis-Folder (burst folder)

- [ ] File > Import > Analysis-Folder (Ctrl+I) asks for a directory ("Burst analysis folder") and reads bi4_bur/*.bur together with the bg4/br4/by4/bv4/td4/2c4 companions merged by position
- [ ] Equations add the derived columns (Sg, Sr, Sg/Sr, Proximity ratio, Fg, Fr, Fg/Fr, Fd/Fa, FRET efficiency, R_FRET, E_tau, …) from mfd.equations.yaml with the constants from the Parameters table
- [ ] Default axes come from mfd.settings.json `default_axes`: x Tau (green), y Proximity ratio, z r Experimental (green), weight Number of Photons
- [ ] Per-parameter axis settings (min/max/scale/bins) come from mfd.axis.json
- [ ] 2-D histogram with the colormap (default viridis)
- [ ] x marginal on top (blue, filled step), y marginal on the right (green step), with axis titles in the parameter colour
- [ ] Path field shows the opened folder
- [ ] Count fields show visible / total (12237 / 12237)
- [ ] vmin / vmax fields (scientific format, e.g. 1.00e+00 / 2.01e+02)
- [ ] Plot controls tab: foldable sections Playback (appears once data is loaded), Histogram (open), z axis, Draw Mask, Selection (open)
- [ ] Histogram section, x row: parameter combo (editable), 1-D bins (81), 2-D bins (31), Normalized density check, Logarithmic axis check, Auto-scale check, "Set" (store as default range for this parameter)
- [ ] Histogram section, y row: the same controls as x
- [ ] x range min / max fields plus "Auto" (auto-range to the data); the same for y
- [ ] "weight" check plus a parameter combo (enabled only while checked)

## file_dialog_analysis_folder — Analysis-Folder directory picker

- [ ] Directory chooser titled "Burst analysis folder", starting in the working path
- [ ] Cancelling leaves the current data untouched

## merge_dialog — Merge dialog when data is already loaded

- [ ] Title per importer ("Open CSV Files", "Open SmFRET Files", "Open MFD HDF5 Files", "Open Sampling Files", "Open PTO Container")
- [ ] Prompt "How do you want to merge the new data?"
- [ ] Radio "Replace existing data" (default)
- [ ] Radio "Append as columns (add new columns, rows must match)"
- [ ] Radio "Append as rows (add new rows of existing columns)"
- [ ] OK / Cancel (Cancel aborts the import)

## open_csv_iris — File > Import > Import Text files (CSV)

- [ ] Import Text files (*.csv, *.dat), Ctrl+O; several files can be selected at once
- [ ] `#` comment lines are skipped and the header row gives the column names
- [ ] Axes can be set to any column (here petal length vs petal width); marginals and counts (150 / 150) update

## open_csv_file_dialog — CSV file picker

- [ ] File chooser titled "Comma separated value files", filter "Text files (*.csv *.dat *.er4 *.txt);;All files (*.*)", multi-select

## open_bur_cli — Single .bur file via `ndx --file` (CLI / drop path)

- [ ] `ndx --file <x.bur>` (and dropping a .bur/.txt) opens a single burst file
- [ ] .csv → CSV reader, .er4 → sampling, .h5/.hdf5 → MFD HDF5, directory → burst folder (the same dispatch as a drop)
- [ ] Tiny files (11 rows) still plot without errors

## open_sampling — File > Import > ChiSurf-Sampling

- [ ] ChiSurf-Sampling asks for a sampling folder ("Open sampling folder") and reads every .er4 in it
- [ ] The er4 columns (chi2, rho_1, lb, sc, ts, xL1, b_1, tL1, bg) become parameters and the plot shows them

## open_analysis_file_error — File > Import > Analysis file: load error

- [ ] Analysis file import: file chooser "MFD HDF5 files", filter "HDF5 files (*.h5 *.hdf5);;ZIP files (*.zip);;All Files (*.*)"
- [ ] Files load in the background without freezing the window
- [ ] A failure shows a "Data Load Error" box with the reader's reason (here: "holds no columnar HDF5 table …"), and the current data stays

## open_image_h5 — Image table (X/Y pixel) → image mode

- [ ] X pixel / Y pixel columns are detected as image axes: pixel bins, pixel ranges, and a map shown as an image (not upside down)
- [ ] Photon weighting is switched on automatically
- [ ] NaN / inf masking is turned off for pixel axes
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

- [ ] Choosing a parameter in the y combo redraws the 2-D map and the marginals
- [ ] The stored axis settings for Fd/Fa apply on selection: logarithmic y, range 0.1..500, bins 81 / 31
- [ ] The log axis shows log ticks on the marginal and the 2-D map

## axes_log_norm_bins — Axis scale, normalisation, bins and ranges

- [ ] 2-D bins x / y (1..999) re-bin the map
- [ ] 1-D bins (1..999) re-bin the marginal
- [ ] Normalized-density check on the y marginal
- [ ] Manual x min / max
- [ ] Logarithmic x axis check
- [ ] Changing bins disables mask drawing and clears the mask (Qt behaviour)

## weights — Weighted histograms

- [ ] "weight" check (tooltip "If checked, histograms are weighted by selected parameter")
- [ ] Weight parameter combo lists every parameter; weighting applies to the map and the marginals

## colour_log_contrast — Colormap, log counts, auto contrast, vmin/vmax

- [ ] Colormap combo (the pyqtgraph map list: viridis, inferno, magma, plasma, cividis, turbo, CET-*…)
- [ ] "log #" check for a log10 colour scale of the counts
- [ ] "Contrast" button sets vmin / vmax automatically
- [ ] vmin / vmax spin boxes (±1e10, "%.2e", debounced)
- [ ] Buttons: "Screenshot", "Data", "Clear", "Update", "Contrast", "Export…"
- [ ] Count fields visible / total
- [ ] "inf" and "NaN" masking checks (on by default)

## mask_nan_inf_off — NaN / inf masking off

- [ ] Unchecking NaN / inf keeps non-finite rows on the plotted axes, and the counts change accordingly

## gate_rectangle — Rectangular gate dragged on the 2-D plot

- [ ] Dragging a rectangle (with a rubber-band preview) on the 2-D map adds two range gates, one for the x parameter and one for the y parameter
- [ ] Map, marginals and visible count show only the gated bursts
- [ ] Selection section: "Cluster" button, cluster spin box (-1 = all), "colour" check, "BID", "clear", "load", "save"
- [ ] Gate table columns: Parameter | Min | Max | Invert | Enable
- [ ] Clicking a cell edits the name / Min / Max (range gates only)
- [ ] Double-clicking a row deletes it (tooltip "Double click to remove a selection"); the Delete key deletes the selected rows

## gate_invert_disable — Gate table: invert and disable

- [ ] Invert check per gate (keep what is outside)
- [ ] Enable check per gate
- [ ] The plot updates immediately on either

## selection_table_menu — Selection table context menu

- [ ] "Select All"
- [ ] "Clear"
- [ ] "Delete"
- [ ] "Send selection to ▸" submenu; it is disabled, with the reason in its title, when there is no ChiSurf RPC, no data, no gate, or no analyses

## canvas_context_menu — 2-D canvas context menu

- [ ] "Copy 2D Histogram (CSV)" to the clipboard
- [ ] "Copy 1D Histograms (CSV)" to the clipboard
- [ ] "Send to Napari" (offers to install napari when it is missing)
- [ ] "Fit gate to the population here" (with its tooltip)
- [ ] "Send selection to ▸" submenu (FCS / TCSPC / PDA / PCH targets discovered over ChiSurf RPC)

## pick_population — Fit gate to the population here

- [ ] Right-click seeds a local 2-D Gaussian fit around the cursor; the fit re-centres on the population (Qt: broken, the click is mapped to bin indices and then checked against data ranges, so it is always refused as "outside the plotted range")
- [ ] The fitted ellipse is added as an elliptical gate (type G2D) in the gate table and drawn on the map

## z_axis_dynamic — z axis panel: dynamic z-selection

- [ ] "dynamic z-selection" check enables the z axis (tooltip "Gate the plots by the z range below…")
- [ ] z parameter combo, 1-D bins, Normalized / Log / Auto-scale checks, "Set"
- [ ] "z range" min / max fields
- [ ] Dynamic-selection check (tooltip "When checked, 2D and 1D histograms (except Z) will only display data selected by region selector")
- [ ] "select" button (turn the range into a gate) and "Auto" (auto-range; the region becomes mean ± 2 sd)
- [ ] z marginal histogram (magenta) with a draggable range region; dragging it re-gates the plots live while dynamic selection is on

## z_add_selection — z range → gate ('select')

- [ ] "select" adds the current z range as a range gate on the z parameter
- [ ] During playback gating the current slice is added as a gate too

## draw_mask — Draw Mask panel: paint and apply

- [ ] "Enable drawing" check (tooltip "Enable/disable drawing on 2D plot"); the rubber-band gate is off while drawing
- [ ] Draw / Erase radio buttons
- [ ] "Cat:" category spin box, 1..255 ("Category/class ID for drawing (1-255)")
- [ ] "Brush:" spin box, 1..50 px ("Brush radius in pixels")
- [ ] Painted mask overlay on the 2-D map, one colour per category (Qt: broken, strokes never register because `PGImageWidget.invTransform` raises NameError `_QWT_X_BOTTOM`; the port must make painting work)
- [ ] "Load Mask" (integer TIFF) and "Save Mask" (integer TIFF)
- [ ] "Clear" (clear the mask)
- [ ] "Apply" turns the mask into a mask gate in the gate table

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

- [ ] Opened by "Cluster" (tooltip "Open clustering dialog"); non-modal; Escape or close hides it
- [ ] "Method:" combo: PCA / UMAP / HDBSCAN / K-means (default K-means)
- [ ] "▦ Columns (n)" button opens the column chooser
- [ ] Grey one-line explanation of each method
- [ ] PCA page: Components (2..10, default 2), "Standardise columns" (on)
- [ ] UMAP page: Neighbours (2..100, default 15), Min. distance (0..1, default 0.1), Components (2..3), Metric (euclidean, manhattan, chebyshev, minkowski, canberra, braycurtis, cosine, correlation, hamming, jaccard), "Advanced"
- [ ] UMAP Advanced: Parallel jobs (-1..64, "All cores"), Learning rate (0.1..10), Initialisation (spectral / random / pca), Spread (0.1..5), Epochs (0..2000, "Auto")
- [ ] HDBSCAN page: Min. samples (default 5), Min. cluster size (default 50)
- [ ] K-means page: Clusters (1..20, default 3)
- [ ] Buttons: "▶ Run", "■ Cancel" (shown while running, reads "Cancelling…"), "📈 Plot" (UMAP only), "💾 Save" (labelling methods, once labels exist)
- [ ] Progress pane: message plus an indeterminate bar ("Running…", "Finished.", "Cancelled or failed.")
- [ ] Asks "Select columns?" when a labelling method is run with no columns chosen

## column_selection_dialog — Column selection dialog

- [ ] Title "Select Columns for Clustering"
- [ ] Hint text on keyboard navigation (Up/Down, Ctrl+Space, PageUp/PageDown, Home/End)
- [ ] "Filter:" field ("Enter text to filter columns")
- [ ] One check box per column, in a scroll area
- [ ] "☑ Select All" and "☐ Deselect All"
- [ ] OK / Cancel

## clustering_kmeans_run — K-means clustering run, clusters coloured

- [ ] Clustering runs in the background while the window stays responsive
- [ ] Labels are stored on the data; the cluster spin box can isolate one cluster (-1 = all)
- [ ] "colour" check colours the 2-D map by cluster instead of by density
- [ ] "💾 Save" saves the clustering data to a folder

## clustering_pca_run — PCA run: loadings report

- [ ] The result text lists which parameters carry the variance (the loadings)
- [ ] PC columns are added and can be picked on the axes

## umap_run — UMAP via the clustering dialog

- [ ] Missing umap-learn: offers the installer; a cancelled or failed install ends in "Installation was cancelled or failed, so this method cannot run." (the baseline environment has no umap-learn, so this is what the Qt shots show)
- [ ] Progress dialog: "UMAP Computation Progress", log view, status line, auto-closes after 3 s on success, "Close" on error
- [ ] UMAP_1…UMAP_n columns are added ("Added UMAP_1…UMAP_n. Pick them in the axis controls to plot.") and can be used as axes
- [ ] "📈 Plot" opens a "UMAP Projection" window (UMAP 1 / UMAP 2 axes, a legend per cluster when labels exist; a 3-D view for 3 components)

## view_umap_action — View > UMAP

- [ ] View > UMAP opens UMAP (Qt: broken, `umap_helpers.on_show_umap` does not exist; nothing happens)

## gaussian_fit — Gaussian Fit panel: fit 2-D Gaussians

- [ ] View > Fit Gaussians shows the "Gaussian Fit" tab; while that tab is active, clicks on the map add seed Gaussians (point mode)
- [ ] Buttons "🎯 Fit", "✕ Clear", "🔍 Select", "⚙ Settings"
- [ ] "Selection σ:" (0.1..4.0, step 0.2, default 1.0)
- [ ] "Gaussians" table: per component x, y, σx, σy, ρ, w, with Name / Value / Fixed / Lo / Hi / Bounds columns (σ ≥ 0, -1 ≤ ρ ≤ 1, w ≥ 0); add / remove rows; Delete removes the selected components
- [ ] Parameters can be fixed and linked (crosslinked constants)
- [ ] Checks: "Select point", "Marginals" (on), "Log Gauss"
- [ ] "💾 Save" / "📂 Load" (.json / .csv; "Axis Mismatch" warning)
- [ ] Ellipses on the 2-D map and Gaussian curves on the marginals
- [ ] Warnings "No Gaussians", "No data", "No histogram"

## gaussian_select — Gaussian Fit: turn a component into a gate

- [ ] "🔍 Select" adds the chosen component as an elliptical gate at Selection σ

## gmm_settings_dialog — GMM Settings dialog

- [ ] "⚙ Settings" opens it (Qt: broken, wrong import path, the button does nothing)
- [ ] "Tolerance (tol)", "Reg. covar", "Max iterations", "Verbose", "Weight floor", "Local window (bins)"
- [ ] "Fix new means by default"
- [ ] OK / Cancel / "💾 Save" (to gmm_settings.json in the user folder)

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

- [ ] "Screenshot" asks for a file (PNG / JPEG / BMP) and saves the plot area

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

- [ ] Folder chooser "Folder for Burst IDs"
- [ ] Progress window "Saving Files" / "Saving Burst ID files..." (Cancel)
- [ ] "Process Burst IDs" dialog: "Compute microtime histogram" (on), "Open FCS Correlator Wizard to correlate BST files" (off), OK / Cancel
- [ ] Follow-up messages ("Plugin Not Available", "No BST Files Found", "Launch Error")

## set_default_axis — Settings > Set default axis

- [ ] Stores the current x / y / z / weight in the settings `default_axes` and confirms with a message

## load_settings_dialog — Settings > Load settings

- [ ] File chooser "ndX settings file"; loading re-applies equations, constants, axis settings and colormap

## save_axis_settings_dialog — Settings > Save settings > Axis settings

- [ ] Save-file chooser for the per-parameter axis settings JSON

## browse_working_path — Browse (working path)

- [ ] "Browse" (tooltip "Change working path") opens a directory chooser and sets the Path field

## selection_save — Selection 'save' (gates to *.selection.json)

- [ ] "save" writes the gates to a *.selection.json file; "load" reads them back (file chooser "Selection JSON")

## clear_plot — Clear

- [ ] "Clear" (tooltip "Clear plot") empties the plots and the Path field (Qt quirk, do not copy: after Clear the map shows the hidden 1000-row placeholder dataset, two synthetic blobs, while the total still reads 12237)
- [ ] "Update" (tooltip "Update plot") redraws
