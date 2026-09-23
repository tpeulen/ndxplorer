"""Helpers for opening datasets and handling merge dialogs."""

from __future__ import annotations

from typing import List, Optional

from ..logging_config import logging
from ..io import file_operations, loading


def show_merge_dialog(ndxplorer, title: str):
    """Delegate to file_operations.show_merge_dialog with ndxplorer context."""
    return file_operations.show_merge_dialog(ndxplorer, title)


def open_files(
    ndxplorer,
    file_handles: Optional[List[str]] = None,
    file_type: Optional[str] = None,
    append: bool = False,
    merge_mode: str = "columns",
):
    """Proxy to file_operations.open_files."""
    return file_operations.open_files(
        ndxplorer,
        file_handles=file_handles,
        file_type=file_type,
        append=append,
        merge_mode=merge_mode,
    )


def _open_with_merge_dialog(
    ndxplorer,
    filenames: Optional[List[str]],
    file_type: str,
    dialog_title: str,
    append: bool = False,
    merge_mode: str = "columns",
):
    """Helper to consolidate merge dialog logic for file opening functions."""
    logging.debug(f"_open_with_merge_dialog: {file_type}")
    if (
        filenames is None
        and getattr(ndxplorer, "data_source", None) is not None
        and not ndxplorer.data_source.empty
    ):
        result = show_merge_dialog(ndxplorer, dialog_title)
        if result is None:
            return
        append, merge_mode = result
    open_files(ndxplorer, file_handles=filenames, file_type=file_type, append=append, merge_mode=merge_mode)


def open_csv(ndxplorer, filenames: Optional[List[str]] = None, append: bool = False, merge_mode: str = "columns"):
    _open_with_merge_dialog(ndxplorer, filenames, "csv", loading.IMPORTERS["csv"].merge_title, append, merge_mode)


def open_sampling(
    ndxplorer,
    filenames: Optional[List[str]] = None,
    append: bool = False,
    merge_mode: str = "columns",
):
    _open_with_merge_dialog(ndxplorer, filenames, "cs_sampling", loading.IMPORTERS["cs_sampling"].merge_title, append, merge_mode)


def open_mfd_hdf5(
    ndxplorer,
    filenames: Optional[List[str]] = None,
    append: bool = False,
    merge_mode: str = "columns",
):
    _open_with_merge_dialog(ndxplorer, filenames, "mfd_hdf5", loading.IMPORTERS["mfd_hdf5"].merge_title, append, merge_mode)


def open_smfret(ndxplorer, merge_mode: str = "columns"):
    logging.debug("open_smFRET")
    append = False
    if getattr(ndxplorer, "data_source", None) is not None and not ndxplorer.data_source.empty:
        result = show_merge_dialog(ndxplorer, loading.IMPORTERS["burst_dir"].merge_title)
        if result is None:
            return
        append, merge_mode = result
    open_files(ndxplorer, file_type="burst_dir", append=append, merge_mode=merge_mode)


def open_pto(
    ndxplorer,
    filenames: Optional[List[str]] = None,
    append: bool = False,
    merge_mode: str = "columns",
):
    _open_with_merge_dialog(ndxplorer, filenames, "pto", loading.IMPORTERS["pto"].merge_title, append, merge_mode)
