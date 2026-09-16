"""Utilities for running expensive data-loading operations off the UI thread."""

from __future__ import annotations

import traceback
from dataclasses import dataclass
from typing import Callable, Optional

from qtpy import QtCore

from ..logging_config import logging

if False:  # pragma: no cover - for type checkers only
    from ..core.data_source import DataSource


@dataclass
class DataLoadTask:
    """Description of a deferred data loading job."""

    description: str
    load_callable: Callable[[], "DataSource"]
    on_success: Callable[["DataSource"], None]
    on_error: Optional[Callable[[str], None]] = None


@dataclass
class DataLoadResult:
    """Bundle emitted when the worker finishes successfully."""

    task: DataLoadTask
    data_source: "DataSource"


class DataLoadWorker(QtCore.QObject):
    """Qt worker object that executes a :class:`DataLoadTask` in a thread."""

    finished = QtCore.Signal(object)  # DataLoadResult
    error = QtCore.Signal(str)

    def __init__(self, task: DataLoadTask):
        super().__init__()
        self._task = task

    @QtCore.Slot()
    def run(self) -> None:
        try:
            logging.info("Starting background data load: %s", self._task.description)
            data_source = self._task.load_callable()
        except Exception:  # pragma: no cover - GUI path
            logging.exception("Background data load failed")
            self.error.emit(traceback.format_exc())
            return

        self.finished.emit(DataLoadResult(task=self._task, data_source=data_source))


def run_task_inline(task: DataLoadTask) -> None:
    """Execute ``task`` synchronously (used when no GUI thread is available)."""

    try:
        data_source = task.load_callable()
    except Exception as exc:  # pragma: no cover - CLI/tests
        logging.exception("Synchronous data load failed")
        if task.on_error is not None:
            task.on_error(str(exc))
        else:
            raise
        return

    task.on_success(data_source)


def _in_gui_thread() -> bool:
    """Whether this is the thread a Qt application runs its event loop on."""
    app = QtCore.QCoreApplication.instance()
    if app is None:
        return False
    try:
        return app.thread() == QtCore.QThread.currentThread()
    except Exception:
        return False


#: Live (thread, worker) pairs. A QThread that goes out of scope while running
#: takes the worker with it, so the loader holds each one until it finishes.
_RUNNING: list = []


def run_task(task: DataLoadTask) -> None:
    """Run *task* off the UI thread, or inline when there is no UI.

    This is the only place that needs to know whether Qt is running: readers
    call it and stay free of Qt. The worker is a ``QObject``, so it is moved
    onto a real ``QThread`` -- callers used to call ``start()`` on the worker
    itself, which a QObject does not have.
    """
    if not _in_gui_thread():
        run_task_inline(task)
        return

    thread = QtCore.QThread()
    worker = DataLoadWorker(task)
    worker.moveToThread(thread)
    entry = (thread, worker)
    _RUNNING.append(entry)

    def _done() -> None:
        thread.quit()
        thread.wait()
        if entry in _RUNNING:
            _RUNNING.remove(entry)

    thread.started.connect(worker.run)
    worker.finished.connect(lambda result: task.on_success(result.data_source))
    worker.finished.connect(lambda _result: _done())
    if task.on_error is not None:
        worker.error.connect(task.on_error)
    worker.error.connect(lambda _message: _done())
    thread.start()
