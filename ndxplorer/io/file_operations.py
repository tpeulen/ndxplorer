"""Utility helpers to keep the file-loading logic for NDXplorer separate from plot_main."""

from __future__ import annotations

import functools
from pathlib import Path
from typing import Iterable, List, Optional, Sequence

import numpy as np
from qtpy import QtWidgets

from ..logging_config import logging
from ..io import reader

if False:  # pragma: no cover - circular import safety for type checkers
    from .plot_main import NDXplorer


def _ensure_sequence(handles: Optional[Sequence[str]]) -> Sequence[str]:
    """Normalize Qt's return types (tuple/list) to a plain tuple."""
    if handles is None or isinstance(handles, bool):
        return ()
    if isinstance(handles, (list, tuple)):
        return tuple(handles)
    return (handles,)


def _update_working_path(ndxplorer: "NDXplorer", first_selection: Optional[str]) -> None:
    """Keep ndxplorer.working_path synced with the most recent selection."""
    if not first_selection:
        return
    try:
        dir_path = str(Path(first_selection).parent)
    except Exception as exc:  # pragma: no cover - defensive
        logging.debug("Could not derive working path: %s", exc)
        return
    ndxplorer.working_path = dir_path


def _update_window_title(
    ndxplorer: "NDXplorer", selections: Sequence[str], append: bool
) -> None:
    """Title the window by WHAT was opened, not where it lives.

    A title is identification, not navigation: the filename is what a user
    scans window lists and tab bars by, and the full path of a deep data
    folder pushes it off screen. The full paths stay reachable as the header
    Path field's tooltip. Appending keeps the current title -- the window
    still shows the first thing it was opened for.
    """
    if append or not selections:
        return
    try:
        first = Path(str(selections[0]))
        title = f"ndX - {first.name}"
        if len(selections) > 1:
            title += f" (+{len(selections) - 1})"
        ndxplorer.setWindowTitle(title)
        edit = getattr(ndxplorer, "lineEditWorkingPath", None)
        if edit is not None:
            edit.setToolTip("\n".join(str(s) for s in selections))
    except Exception:  # pragma: no cover - defensive
        logging.debug("Could not update the window title", exc_info=True)


def _handle_append(ndxplorer: "NDXplorer", new_source, merge_mode: str) -> None:
    """Append/replace loaded data followed by UI updates."""
    current = ndxplorer.data_source
    if current is not None and not current.empty:
        def warn(title: str, message: str) -> None:
            QtWidgets.QMessageBox.warning(ndxplorer, title, message)

        if current.merge(new_source, mode=merge_mode, warn=warn):
            # Re-assign through the property so the data manager sees the
            # merged frame and its caches are invalidated.
            ndxplorer.data_source = current
            ndxplorer.update()
    else:
        ndxplorer.data_source = new_source
        ndxplorer.update()


def open_files(
    ndxplorer: "NDXplorer",
    file_handles: Optional[Sequence[str]] = None,
    file_type: Optional[str] = None,
    append: bool = False,
    merge_mode: str = "columns",
) -> None:
    """Central entry point for all data-loading actions."""
    logging.info("NDXplorer: Opening files..")
    logging.debug("Merge mode: %s", merge_mode)
    
    # Auto-detect sampling folder
    file_handles_seq = _ensure_sequence(file_handles)
    if not file_type and file_handles_seq and len(file_handles_seq) == 1:
        p = Path(file_handles_seq[0])
        if p.is_dir() and (p / "parameters.json").exists():
            file_type = "sampling_folder"

    file_handles_seq = _ensure_sequence(file_handles)
    reader_input = file_handles_seq
    working_path = str(ndxplorer.working_path)

    # --- Sampling / ER4 ----------------------------------------------------
    if file_type == "cs_sampling":
        if not file_handles_seq:
            directory = QtWidgets.QFileDialog.getExistingDirectory(
                ndxplorer, "Open sampling folder", working_path
            )
            file_handles_seq = (directory,) if directory else ()
        
        if file_handles_seq:
            reader_input = str(file_handles_seq[0])
            logging.info("Opening sampling folder: %s", reader_input)
            data_reader = reader.read_sampling_folder
            _update_working_path(ndxplorer, reader_input)
        else:
            reader_input = ()

    elif file_type == "er4":
        if not file_handles_seq:
            file_handles_seq, _ = QtWidgets.QFileDialog.getOpenFileNames(
                ndxplorer,
                "ChiSurf sampling files",
                working_path,
                "Sampling files (*.er4);;All files (*.*)",
            )
        if file_handles_seq:
            _update_working_path(ndxplorer, file_handles_seq[0])
            logging.info("Opening files (%s): %s", file_type, file_handles_seq)
            data_reader = reader.read_csv_sampling
            reader_input = file_handles_seq
        else:
            reader_input = ()

    # --- Sampling Folder (New Format) --------------------------------------
    elif file_type == "sampling_folder":
        if not file_handles_seq:
            directory = QtWidgets.QFileDialog.getExistingDirectory(
                ndxplorer, "Open sampling folder", working_path
            )
            file_handles_seq = (directory,) if directory else ()
        
        if file_handles_seq:
            reader_input = file_handles_seq[0]
            data_reader = reader.read_sampling_folder
        else:
            reader_input = ()

    # --- HDF5 / zipped HDF5 ------------------------------------------------
    elif file_type == "mfd_hdf5":
        if not file_handles_seq:
            file_handles_seq, _ = QtWidgets.QFileDialog.getOpenFileNames(
                ndxplorer,
                "MFD HDF5 files",
                working_path,
                "HDF5 files (*.h5 *.hdf5);;ZIP files (*.zip);;All Files (*.*)",
            )

        _update_working_path(ndxplorer, file_handles_seq[0] if file_handles_seq else None)
        logging.info("Opening MFD HDF5/Zip files: %s", file_handles_seq)

        if not file_handles_seq:
            return

        # Through the shared path, like every other format. This branch used to
        # load inline instead -- synchronously on the GUI thread, duplicating
        # what read_mfd_hdf5 already does with zips and multiple files, and then
        # calling _apply_axes_and_refresh with the wrong number of arguments, so
        # opening an MFD HDF5 raised a TypeError after the data had loaded.
        #
        # Falling through is not only shorter: it is what runs the image-axis
        # detection, populates the parameter combo boxes and puts the load on
        # the background runner. An imaging HDF5 opened here never got any of
        # those.
        data_reader = functools.partial(reader.read_mfd_hdf5, merge_mode=merge_mode)
        reader_input = [str(f) for f in file_handles_seq]

    # --- Burst analysis folder (bi4_bur/*.bur) -----------------------------
    elif file_type == "burst_dir":
        if not file_handles_seq:
            folder = QtWidgets.QFileDialog.getExistingDirectory(
                ndxplorer, "Burst analysis folder", working_path
            )
            file_handles_seq = [folder] if folder else []
        if not file_handles_seq:
            return
        _update_working_path(ndxplorer, file_handles_seq[0])
        # read_burst_analysis takes a single base path containing bi4_bur/ (or
        # bur/). Route it through the shared async loader so the result is
        # finalized via the data_source property (data_manager) like every other
        # reader — previously burst_dir fell through to the CSV loader, which
        # tried to read the directory itself ("Is a directory") and loaded zero
        # bursts, leaving the bundled example data on screen.
        data_reader = reader.read_burst_analysis
        reader_input = str(file_handles_seq[0])

    # --- PTO Measurement Container (.pto) -----------------------------------
    elif file_type == "pto" or (file_handles_seq and any(str(f).lower().endswith(".pto") for f in file_handles_seq)):
        if not file_handles_seq:
            file_handles_seq, _ = QtWidgets.QFileDialog.getOpenFileNames(
                ndxplorer,
                "PTO Measurement Containers",
                working_path,
                "PTO files (*.pto);;All Files (*.*)",
            )
        if not file_handles_seq:
            return
        _update_working_path(ndxplorer, file_handles_seq[0])
        from .pto_reader import read_container
        data_reader = read_container
        reader_input = str(file_handles_seq[0])

    # --- Generic CSV loader ------------------------------------------------
    else:
        if not file_handles_seq:
            file_handles_seq, _ = QtWidgets.QFileDialog.getOpenFileNames(
                ndxplorer,
                "Comma separated value files",
                working_path,
                "Text files (*.csv *.dat *.er4 *.txt);;All files (*.*)",
            )
        _update_working_path(ndxplorer, file_handles_seq[0] if file_handles_seq else None)

        # Auto-detect .er4 in generic loader
        if any(str(f).lower().endswith(".er4") for f in file_handles_seq):
            data_reader = reader.read_csv_sampling
        else:
            data_reader = reader.read_csv
        reader_input = file_handles_seq

    if reader_input:
        logging.info("Opening files (%s): %s", file_type or "csv", file_handles_seq)
        _update_window_title(ndxplorer, file_handles_seq, append)

        # Capture equations and constants to use in worker thread
        # Important: do this BEFORE launching the thread to avoid main-thread access issues
        equations = getattr(ndxplorer, "equations", [])
        constants = getattr(ndxplorer, "constants", {})

        def load_callable():
            # Perform initial raw data load
            ds = data_reader(reader_input)

            # Re-read equations/constants at execution time (not just the values
            # captured above): when a viewer is opened right after construction the
            # settings — and thus the equations that derive Sg/Sr/Proximity ratio/
            # FRET etc. — may still be loading in deferred init, so the captured
            # copies can be stale/empty.
            eqs = getattr(ndxplorer, "equations", None) or equations
            cs = getattr(ndxplorer, "constants", None) or constants

            # If successful and not empty, perform heavy column computations in background
            if ds is not None and not ds.empty:
                logging.info(f"Background: Computing columns for {ds.size} rows")
                ds.compute_columns(constants=cs, equations=eqs)
                logging.info("Background: Column computation complete.")
            return ds

        _dispatch_data_load(
            ndxplorer,
            f"Loading {file_type or 'CSV'} files",
            load_callable,
            append,
            merge_mode,
        )


def _dispatch_data_load(
    ndxplorer: "NDXplorer",
    description: str,
    load_callable,
    append: bool,
    merge_mode: str,
) -> None:
    """Route loading through NDxplorer's async runner when available."""
    runner = getattr(ndxplorer, "_run_data_load_task", None)
    if callable(runner):
        runner(description, load_callable, append, merge_mode)
    else:
        data_source = load_callable()
        _finalize_loaded_data(ndxplorer, data_source, append, merge_mode)


def _finalize_loaded_data(
    ndxplorer: "NDXplorer", data_source, append: bool, merge_mode: str
) -> None:
    """Apply the loaded data to NDxplorer and refresh the UI."""
    logging.debug("_finalize_loaded_data")
    
    # Block histogram computations during initial data loading
    # This prevents computing histograms with wrong bins before image detection
    if hasattr(ndxplorer, 'plot_control'):
        ndxplorer.plot_control._loading_data = True
        logging.info("Set _loading_data flag to block premature histogram computation")
    
    if data_source is None:
        return
    
    # IMPORTANT: Detect image axes BEFORE setting data_source
    # The data_source setter calls compute_columns() which may replace raw columns
    # So we need to check for X pixel/Y pixel in the RAW loaded data first
    has_image_data = False
    image_dims = None
    if not append and data_source is not None and not data_source.empty:
        try:
            param_names = list(data_source.parameter_names)
            logging.info(f"Raw data has {len(param_names)} parameters before compute_columns: {param_names[:10]}")
            
            has_x_pixel = any("x pixel" in name.lower() for name in param_names)
            has_y_pixel = any("y pixel" in name.lower() for name in param_names)
            
            if has_x_pixel and has_y_pixel:
                has_image_data = True
                x_pixel_param = next((name for name in param_names if "x pixel" in name.lower()), None)
                y_pixel_param = next((name for name in param_names if "y pixel" in name.lower()), None)
                
                # Get image dimensions from raw data
                x_values = data_source.values[param_names.index(x_pixel_param), :]
                y_values = data_source.values[param_names.index(y_pixel_param), :]
                
                x_pixels = int(np.max(x_values)) + 1 if len(x_values) > 0 else 256
                y_pixels = int(np.max(y_values)) + 1 if len(y_values) > 0 else 256
                
                image_dims = (x_pixels, y_pixels, x_pixel_param, y_pixel_param)
                logging.info(f"Detected image data in raw loaded data: {x_pixels}x{y_pixels} pixels")
        except Exception as e:
            logging.error(f"Error detecting image data in raw data: {e}")
    
    if append:
        _handle_append(ndxplorer, data_source, merge_mode)
    else:
        # For image data, skip compute_columns to preserve raw pixel columns
        if has_image_data:
            logging.info("Skipping compute_columns for image data to preserve pixel columns")
            # Bypass BOTH the setter AND data_manager to preserve raw columns
            # Directly set the internal _data_source attribute
            object.__setattr__(ndxplorer, '_data_source', data_source)
            ndxplorer.invalidate_values_cache()
            ndxplorer._set_data_loaded(not data_source.empty)
            # Also bypass data_manager if it exists
            if hasattr(ndxplorer, 'data_manager'):
                object.__setattr__(ndxplorer.data_manager, '_data_source', data_source)
            # Enable UI controls now that data is loaded
            ndxplorer.update_ui_enabled_state()
            logging.info(f"Image data loaded with {len(data_source.parameter_names)} raw parameters preserved")
        else:
            # Normal data: use the setter which calls compute_columns
            ndxplorer.data_source = data_source
            ndxplorer.update_ui_data()
        
        # Apply image settings if detected in raw data
        if has_image_data and image_dims:
            x_pixels, y_pixels, x_pixel_param, y_pixel_param = image_dims
            logging.info(f"Applying image settings: {x_pixels}x{y_pixels}, axes: {x_pixel_param}, {y_pixel_param}")
            
            # Store image info for deferred axis detection
            ndxplorer._detected_image_dims = image_dims
        # Populate comboboxes with BOTH raw AND computed parameter names
        # This is critical so X pixel/Y pixel are available for selection
        raw_param_names = []
        if has_image_data and image_dims:
            # Get raw parameter names from the original data_source before compute_columns
            try:
                raw_param_names = list(data_source.parameter_names)
                logging.info(f"Including {len(raw_param_names)} raw parameter names in combo boxes")
            except Exception:
                pass
        
        # After compute_columns, get the computed parameter names from the public data_source
        active_ds = ndxplorer.data_source
        computed_param_names = list(active_ds.parameter_names) if active_ds and not active_ds.empty else []
        
        # Combine raw and computed, preserving order and removing duplicates
        all_param_names = []
        seen = set()
        for name in raw_param_names + computed_param_names:
            if name not in seen:
                all_param_names.append(name)
                seen.add(name)
        
        # Only perform manual population if we actually have parameters to show,
        # or if we are in the image data path where we skip the full update().
        if all_param_names:
            logging.info(f"Populating combo boxes with {len(all_param_names)} total parameters")
            
            for combo in [ndxplorer.plot_control.comboBoxSelX, 
                          ndxplorer.plot_control.comboBoxSelY,
                          ndxplorer.plot_control.comboBoxSelZ]:
                combo.blockSignals(True)
                combo.clear()
                combo.addItems(all_param_names)
                combo.blockSignals(False)
            # The weight combo is a parameter chooser like the other three and
            # has to be filled like one. It used to get blockSignals(True) and
            # nothing else -- never cleared, never populated, and left with its
            # signals still blocked -- so it stayed empty, weighting could not
            # be chosen at all, and the automatic "weight by photon count" for
            # image data silently failed to find its parameter.
            if hasattr(ndxplorer.plot_control, 'comboBoxWeight'):
                weight_combo = ndxplorer.plot_control.comboBoxWeight
                previous = weight_combo.currentText()
                weight_combo.blockSignals(True)
                weight_combo.clear()
                weight_combo.addItems(all_param_names)
                if previous in all_param_names:
                    weight_combo.setCurrentIndex(all_param_names.index(previous))
                weight_combo.blockSignals(False)
        else:
            logging.warning("No parameters found to populate combo boxes.")
    _apply_axes_and_refresh(ndxplorer, all_param_names)


def _apply_axes_and_refresh(ndxplorer: "NDXplorer",
                            all_param_names: Optional[List[str]] = None) -> None:
    """Shared tail for open operations: apply axes + refresh plots.

    The names default to whatever the data source now holds, which is where they
    come from in every case anyway. They were a required argument, and a caller
    that forgot them raised a TypeError only once the data had already loaded --
    at the point where the failure looks like a problem with the file.
    """
    if all_param_names is None:
        all_param_names = list(getattr(ndxplorer.data_source, "parameter_names", []))
    # Defer axis detection until AFTER comboboxes are fully populated
    # (plot_control.update() may take time to restore selections)
    from qtpy.QtCore import QTimer
    
    def _deferred_axis_detection():
        """Run after combobox update completes."""
        logging.info("Running deferred image axis detection")
        
        # Check if current axes are valid for the new data
        # If not, pick sensible defaults
        p1_name = ndxplorer.plot_control.comboBoxSelX.currentText()
        p2_name = ndxplorer.plot_control.comboBoxSelY.currentText()
        
        needs_auto_axis = False
        if p1_name not in all_param_names or p2_name not in all_param_names:
            needs_auto_axis = True
            logging.info(f"Current axes ({p1_name}, {p2_name}) not in new data. Selecting defaults.")
            
        # Check if image dimensions were detected in raw data before compute_columns
        detected_dims = getattr(ndxplorer, '_detected_image_dims', None)
        image_axes_already_set = False
        
        if detected_dims:
            x_pixels, y_pixels, x_pixel_param, y_pixel_param = detected_dims
            logging.info(f"Image data: {x_pixels}x{y_pixels} on {x_pixel_param}, "
                         f"{y_pixel_param}")

            # One function does this, and it is check_and_set_image_axes: axes,
            # bins, RANGES, the frame selector and the photon weighting, all
            # derived from the data. This branch used to do about half of it
            # inline -- axes and bins but not ranges -- and then skip the real
            # one as "redundant". The result was an image binned 256 across an
            # x range of 0 to 1: every pixel in the first bin, one flat colour.
            #
            # The dims are detected before this only because detection has to
            # happen before compute_columns could replace the pixel columns.
            # They say WHETHER this is an image; what it looks like comes from
            # the data, here.
            image_axes_already_set = bool(ndxplorer.check_and_set_image_axes())

            # Pixel coordinates are always valid, so a NaN/Inf mask on them can
            # only remove real pixels.
            #
            # This used to write to a pair of flags on the data manager that
            # nothing read -- the checkboxes below are what actually decide the
            # mask -- so it logged success and changed nothing. Going through
            # the checkboxes means the UI also shows the state it is in.
            ndxplorer.checkBoxMaskNaN.setChecked(False)
            ndxplorer.checkBoxMaskInf.setChecked(False)
            ndxplorer.onMaskChanged()
            logging.info("Disabled NaN/Inf masking for image data")

            # Clear the stored dims
            delattr(ndxplorer, '_detected_image_dims')
        
        # Log data source info for debugging
        try:
            ds = ndxplorer.data_source
            if ds and not ds.empty:
                param_names = list(ds.parameter_names)
                logging.info(f"Data source has {len(param_names)} parameters: {param_names}")
            else:
                logging.warning("Data source is empty or None during axis detection")
        except Exception as e:
            logging.error(f"Error accessing data source during axis detection: {e}")
        
        # Skip redundant image detection if we already set the axes from raw data
        if not image_axes_already_set:
            # Cancelling an in-flight worker and holding off new requests used
            # to happen here. Histograms are computed synchronously now, so
            # there is nothing in flight to cancel while the axes are chosen.
            img_applied = ndxplorer.check_and_set_image_axes()
            logging.info(f"Image axis detection result: {img_applied}")
            if not img_applied:
                try:
                    ndxplorer.apply_default_axes_from_settings()
                except Exception as exc:  # pragma: no cover - defensive
                    logging.debug("Could not apply default axes: %s", exc)

            # Invalidate cache to ensure fresh computation with new bins
            ndxplorer.invalidate_values_cache()
        else:
            logging.info("Skipping redundant image detection - axes already set from raw data")
            # Still invalidate cache
            ndxplorer.invalidate_values_cache()
        
        # Every data set can be played back along one of its own columns, so
        # this runs for all of them and not only for the images the branches
        # above are about: a frame index if there is one, otherwise the macro
        # time, which is what gives a burst measurement its time axis.
        try:
            ndxplorer.plot_control.setup_playback(ndxplorer.data_source)
        except Exception as exc:  # pragma: no cover - defensive
            logging.warning("Could not set up playback: %s", exc, exc_info=True)

        # Clear loading flag IMMEDIATELY to allow histogram computation
        # This must happen before any histogram trigger to prevent blocking
        if hasattr(ndxplorer, 'plot_control'):
            ndxplorer.plot_control._loading_data = False
            logging.info("Cleared _loading_data flag - histogram computation now enabled")
        
        # Trigger histogram update after file loading completes
        # Ensure deferred initialization is complete first
        try:
            # Make sure deferred init is done before updating histograms
            if not getattr(ndxplorer, "_deferred_init_done", False):
                if hasattr(ndxplorer, '_deferred_init'):
                    ndxplorer._deferred_init()
                    logging.info("Triggered deferred init before histogram update")
            
            from ..plotting.plot_update_helpers import update_histograms
            update_histograms(ndxplorer)
            logging.info("Triggered automatic histogram update after file loading")
        except Exception as e:
            logging.warning(f"Failed to trigger automatic histogram update: {e}")
    
    # Use short delay to ensure comboboxes are ready (they're now populated directly)
    QTimer.singleShot(10, _deferred_axis_detection)


def show_merge_dialog(
    ndxplorer: "NDXplorer", title: str
) -> Optional[tuple[bool, str]]:
    """Modal dialog prompting the user for merge behavior."""
    logging.debug("show_merge_dialog")
    dialog = QtWidgets.QDialog(ndxplorer)
    dialog.setWindowTitle(title)
    layout = QtWidgets.QVBoxLayout()

    label = QtWidgets.QLabel("How do you want to merge the new data?")
    layout.addWidget(label)

    replace_rb = QtWidgets.QRadioButton("Replace existing data")
    append_columns_rb = QtWidgets.QRadioButton(
        "Append as columns (add new columns, rows must match)"
    )
    append_rows_rb = QtWidgets.QRadioButton(
        "Append as rows (add new rows of existing columns)"
    )
    replace_rb.setChecked(True)

    layout.addWidget(replace_rb)
    layout.addWidget(append_columns_rb)
    layout.addWidget(append_rows_rb)

    buttons = QtWidgets.QDialogButtonBox(
        QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
    )
    buttons.accepted.connect(dialog.accept)
    buttons.rejected.connect(dialog.reject)
    layout.addWidget(buttons)

    dialog.setLayout(layout)
    result = dialog.exec_()
    if result != QtWidgets.QDialog.Accepted:
        return None

    append = append_columns_rb.isChecked() or append_rows_rb.isChecked()
    merge_mode = "columns"
    if append_columns_rb.isChecked():
        merge_mode = "columns"
    elif append_rows_rb.isChecked():
        merge_mode = "rows"
    return append, merge_mode
