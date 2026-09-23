"""Feature hooks the settings group needed: shared capture ops and targets, drops."""

from __future__ import annotations

import sys
import types

import pytest


def _install(monkeypatch, *classes):
    """Register fake feature modules, in this order."""
    from ndxplorer.app import features

    names = []
    for i, cls in enumerate(classes):
        name = f"fake_hook_{i}"
        module = types.ModuleType(f"ndxplorer.app.features.{name}")
        module.create = cls
        monkeypatch.setitem(sys.modules, module.__name__, module)
        names.append(name)
    monkeypatch.setattr(features, "FEATURES", names)


def test_a_capture_op_returning_false_passes_the_step_on(monkeypatch):
    from ndxplorer.app.capture import Replay
    from ndxplorer.app.features import Feature

    seen = []

    class First(Feature):
        def capture_ops(self):
            return {"click": lambda replay, step: seen.append("first") or False}

    class Second(Feature):
        def capture_ops(self):
            return {"click": lambda replay, step: seen.append("second")}

    _install(monkeypatch, First, Second)
    replay = Replay({"id": "x", "steps": []}, {"scenarios": []}, size=(600, 400))
    try:
        replay.step({"op": "click", "widget": "whatever"})
    finally:
        replay.app.close()
    assert seen == ["first", "second"]


def test_a_target_locator_returning_none_lets_the_next_answer(monkeypatch):
    from ndxplorer.app.capture import Replay
    from ndxplorer.app.features import Feature

    class NotMine(Feature):
        def capture_targets(self):
            return {"dialog": lambda replay: None}

    class Mine(Feature):
        def capture_targets(self):
            return {"dialog": lambda replay: (10.0, 20.0, 100.0, 50.0)}

    _install(monkeypatch, NotMine, Mine)
    replay = Replay({"id": "x", "steps": []}, {"scenarios": []}, size=(600, 400))
    try:
        assert replay.box_of("dialog") == (10.0, 20.0, 100.0, 50.0)
        replay.step({"op": "capture", "name": "dialog", "target": "dialog"})
        assert replay.shots["dialog"].size == (104, 54)
    finally:
        replay.app.close()


def test_a_dialog_capture_falls_back_to_the_message_box(monkeypatch):
    from ndxplorer.app.capture import Replay, Unsupported
    from ndxplorer.app.features import Feature

    class NotMine(Feature):
        def capture_targets(self):
            return {"dialog": lambda replay: None}

    _install(monkeypatch, NotMine)
    replay = Replay({"id": "x", "steps": []}, {"scenarios": []}, size=(600, 400))
    try:
        with pytest.raises(Unsupported):
            replay.step({"op": "capture", "name": "dialog", "target": "dialog"})
        replay.app.message = ("Title", "Text")
        replay.step({"op": "capture", "name": "dialog", "target": "dialog"})
        assert "dialog" in replay.shots
    finally:
        replay.app.close()


def test_a_feature_can_keep_a_drop(monkeypatch):
    from ndxplorer.app.features import Feature
    from ndxplorer.app.frame import NdxApp

    kept = []

    class Taker(Feature):
        def files_dropped(self, paths):
            kept.extend(paths)
            return bool(self.app.storage.get("take"))

    _install(monkeypatch, Taker)
    app = NdxApp()
    opened = []
    app.open_path = lambda path: opened.append(path) or True
    try:
        app.storage["take"] = True
        app.files_dropped(["/a/folder"])
        assert kept == ["/a/folder"] and opened == []
        app.storage["take"] = False
        app.files_dropped(["/b/file.csv"])
        assert opened == ["/b/file.csv"]
    finally:
        app.close()
