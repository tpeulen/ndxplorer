"""Utility helpers to keep the file-loading logic for NDXplorer separate from plot_main."""

from __future__ import annotations

from typing import List, Optional, Sequence

from qtpy import QtWidgets

from ..logging_config import logging
from ..io import loading
from ..utils.axis_helpers import image_axes

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
    ndxplorer.working_path = loading.working_path_for(first_selection)


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
        ndxplorer.setWindowTitle(loading.window_title(selections))
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

        if loading.merge(current, new_source, merge_mode, warn=warn):
            # Re-assign through the property so the data manager sees the
            # merged frame and its caches are invalidated.
            ndxplorer.data_source = current
            ndxplorer.update()
    else:
        ndxplorer.data_source = new_source
        ndxplorer.update()


def _ask_paths(ndxplorer: "NDXplorer", importer: "loading.Importer", working_path: str):
    """The Qt dialog for *importer*: a folder, or files."""
    if importer.mode == "folder":
        folder = QtWidgets.QFileDialog.getExistingDirectory(
            ndxplorer, importer.title, working_path
        )
        return (folder,) if folder else ()
    files, _ = QtWidgets.QFileDialog.getOpenFileNames(
        ndxplorer, importer.title, working_path, loading.filter_string(importer.filters)
    )
    return _ensure_sequence(files)


#: Kinds older callers pass that are spelled differently in ``loading.IMPORTERS``.
_KIND_ALIASES = {"sampling_folder": "cs_sampling"}


def open_files(
    ndxplorer: "NDXplorer",
    file_handles: Optional[Sequence[str]] = None,
    file_type: Optional[str] = None,
    append: bool = False,
    merge_mode: str = "columns",
) -> None:
    """Central entry point for all data-loading actions.

    Which dialog to raise, which reader to run and what the working path
    becomes are :mod:`ndxplorer.io.loading`'s, shared with the emtk app; this
    raises the Qt dialog and hands the load to the window's worker.
    """
    logging.info("NDXplorer: Opening files..")
    logging.debug("Merge mode: %s", merge_mode)

    file_handles_seq = _ensure_sequence(file_handles)
    kind = _KIND_ALIASES.get(file_type, file_type)
    if kind not in loading.IMPORTERS:
        # No importer named (a drop, ``--file``, a macro): the paths decide.
        kind = loading.kind_for_paths(file_handles_seq) if file_handles_seq else "csv"

    if not file_handles_seq:
        file_handles_seq = _ask_paths(
            ndxplorer, loading.IMPORTERS[kind], str(ndxplorer.working_path)
        )
    if not file_handles_seq:
        return
    _update_working_path(ndxplorer, file_handles_seq[0])

    logging.info("Opening files (%s): %s", kind, file_handles_seq)
    _update_window_title(ndxplorer, file_handles_seq, append)

    # Capture equations and constants to use in worker thread
    # Important: do this BEFORE launching the thread to avoid main-thread access issues
    equations = getattr(ndxplorer, "equations", [])
    constants = getattr(ndxplorer, "constants", {})

    def load_callable():
        # Re-read equations/constants at execution time (not just the values
        # captured above): when a viewer is opened right after construction the
        # settings — and thus the equations that derive Sg/Sr/Proximity ratio/
        # FRET etc. — may still be loading in deferred init, so the captured
        # copies can be stale/empty.
        eqs = getattr(ndxplorer, "equations", None) or equations
        cs = getattr(ndxplorer, "constants", None) or constants
        return loading.load(file_handles_seq, kind, merge_mode, equations=eqs, constants=cs)

    _dispatch_data_load(
        ndxplorer,
        f"Loading {kind} files",
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
            image = image_axes(data_source)
        except Exception as e:
            logging.error(f"Error detecting image data in raw data: {e}")
            image = None
        if image is not None:
            has_image_data = True
            image_dims = (image.nx, image.ny, image.x, image.y)
            logging.info(f"Detected image data in raw loaded data: {image.nx}x{image.ny} pixels")

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

    layout.addWidget(QtWidgets.QLabel(loading.MERGE_PROMPT))
    radios = []
    for index, (_mode, text) in enumerate(loading.MERGE_CHOICES):
        radio = QtWidgets.QRadioButton(text)
        radio.setChecked(index == 0)
        layout.addWidget(radio)
        radios.append(radio)

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

    chosen = next(i for i, radio in enumerate(radios) if radio.isChecked())
    append, merge_mode = loading.merge_choice(chosen)
    return append, merge_mode
