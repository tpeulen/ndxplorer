"""
Parameter Editor widget.
Uses chisurf's ParameterEditor if chisurf is available,
otherwise falls back to the local pyqtgraph-based implementation.
"""
from typing import Dict, List
from qtpy import QtCore, QtGui, QtWidgets
import re
import json
import sys
import pathlib
import logging
from collections import OrderedDict

try:
    from chisurf.gui.widgets.parameter_editor import ParameterEditor as CSParameterEditor
    HAS_CHISURF = True
except ImportError:
    HAS_CHISURF = False


if HAS_CHISURF:

    _NDX_OWNER_ID = "ndxplorer"

    class _CompactColumns:
        """Section stub whitelisting the constant-relevant columns.

        ``ParameterGroupTableWidget`` reads ``section.columns`` to decide which
        columns to show; we hide the fit-``error`` column (no fit runs here).
        """
        columns = ("name", "value", "fixed", "bounds_lo", "bounds_hi", "bounds_on")

    class ParameterEditor(QtWidgets.QWidget):
        """ndXplorer constants as a chisurf fitting-parameter table.

        Renders the constants as ``FittingParameter``s (value/fixed/bounds + a
        link menu) and registers the group so a constant can be crosslinked to a
        chisurf fit's parameter. Falls back to the legacy dict editor if the
        fitting-table stack is unavailable. Keeps the same public surface
        (``dict``, ``set_callback``, ``json_file``) so ``plot_main`` is untouched.
        """

        #: Emitted (on the GUI thread) when a constant's value changed outside a
        #: local table edit — e.g. a fit moved a parameter this constant is
        #: linked to. plot_main connects it to its recompute throttle.
        constantsChangedExternally = QtCore.Signal()
        #: Internal, thread-safe hop: fit-client callbacks may fire off the GUI
        #: thread; emitting this (queued) marshals onto the GUI thread.
        _externalEvent = QtCore.Signal()

        def __init__(
                self,
                json_file=None,  # type: str
                parent=None,  # type: QtWidgets.QWidget
                callback=None  # type: callable
        ):
            super(ParameterEditor, self).__init__(parent)
            self._json_file = json_file
            self._callback = callback
            self._group = None
            self._table = None
            self._cs_editor = None      # legacy fallback editor
            self._registered = False
            self._mapping = None
            self._subscribed = False
            self._reg_cb = None
            self._fc_cb = None

            # Marshal off-GUI-thread external events onto the GUI thread.
            self._externalEvent.connect(self._on_external_gui, QtCore.Qt.QueuedConnection)

            data = self._load_data(json_file)

            layout = QtWidgets.QVBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(2)

            try:
                from ..core import constants_group as _cg
                from chisurf.gui.autoform.sections.parameter_table import (
                    ParameterGroupTableWidget,
                )
                self._cg = _cg
                self._group = _cg.build_group_from_data(data)
                self._table = ParameterGroupTableWidget(
                    self._group.parameters_all,
                    section=_CompactColumns(),
                    parent=self,
                    on_change=self._on_change,
                    # These constants are ndXplorer's own; no fit holds them, so
                    # an edit must not be sent to the fitting backend, which can
                    # only answer "fit not found" -- once per keystroke, and once
                    # per wheel notch, with a stack trace each time.
                    remote=False,
                )
                layout.addWidget(self._table, 1)
                # Add-parameter affordance so a new constant can be created
                # without hand-editing the JSON.
                add_bar = QtWidgets.QHBoxLayout()
                btn_add = QtWidgets.QToolButton()
                btn_add.setText("➕ parameter")
                btn_add.setToolTip("Add a new constant (name + value)")
                btn_add.clicked.connect(self._add_parameter)
                add_bar.addWidget(btn_add)
                add_bar.addStretch(1)
                layout.addLayout(add_bar)
                self._register_group()
                self._subscribe_external()
            except Exception as exc:
                # Degrade gracefully to the legacy dict editor.
                logging.warning(
                    "Fitting-parameter table unavailable, using dict editor: %s", exc
                )
                self._group = None
                self._table = None
                backing = OrderedDict(self._values_only(data))
                self._cs_editor = CSParameterEditor(
                    target=backing, json_file=json_file, callback=callback
                )
                layout.addWidget(self._cs_editor)

            self.setWindowTitle("Configuration: %s" % self.json_file)

        # -- loading -------------------------------------------------------
        def _load_data(self, json_file):
            """Return parsed JSON (flat or nested), falling back to the default."""
            candidates = []
            if json_file is not None:
                candidates.append(pathlib.Path(json_file))
            candidates.append(
                pathlib.Path(__file__).parent.parent / "settings" / "mfd.constants.json"
            )
            for path in candidates:
                try:
                    if path.exists():
                        with open(path, "r") as fp:
                            return json.load(fp, object_pairs_hook=OrderedDict)
                except Exception:
                    continue
            return OrderedDict()

        @staticmethod
        def _values_only(data):
            try:
                from ..core import constants_group as _cg
                return _cg.values_from_data(data)
            except Exception:
                return OrderedDict(data) if isinstance(data, dict) else OrderedDict()

        # -- crosslink registration ---------------------------------------
        def _register_group(self):
            try:
                from chisurf.core.parameter_group_registry import register_parameter_group
                register_parameter_group(
                    self._group, owner_id=_NDX_OWNER_ID, label="ndX"
                )
                self._registered = True
            except Exception as exc:
                logging.debug("Could not register constants group: %s", exc)

        def _unregister_group(self):
            if not self._registered:
                return
            try:
                from chisurf.core.parameter_group_registry import unregister_parameter_group
                unregister_parameter_group(_NDX_OWNER_ID)
            except Exception:
                pass
            self._registered = False

        def closeEvent(self, event):  # noqa: N802 (Qt override)
            self._unsubscribe_external()
            self._unregister_group()
            super().closeEvent(event)

        # -- live mapping (Phase 2) ---------------------------------------
        @property
        def constants_mapping(self):
            """Live ``name -> float`` view over the group (follows crosslinks).

            Reading a linked constant returns its master's current value, so the
            equation engine always computes against the up-to-date value.
            Falls back to the legacy editor's dict when the fitting table is not
            in use.
            """
            if self._group is not None:
                if self._mapping is None:
                    self._mapping = self._cg.ConstantsMapping(self._group)
                return self._mapping
            return self._cs_editor.dict if self._cs_editor is not None else {}

        # -- external (fit-driven) change subscription --------------------
        def _subscribe_external(self):
            """Recompute when a fit moves a parameter a constant is linked to."""
            try:
                from chisurf.core import parameter_group_registry as reg
                reg.subscribe(self._on_external_event)
                self._reg_cb = self._on_external_event
            except Exception:
                self._reg_cb = None
            try:
                from chisurf.gui.widgets.fitting.fitting_client import get_fitting_client
                fc = get_fitting_client()
                if fc is not None:
                    cb = lambda *a, **k: self._on_external_event()  # noqa: E731
                    fc.subscribe("parameter.", cb)
                    fc.subscribe("fit.", cb)
                    self._fc_cb = (fc, cb)
            except Exception:
                self._fc_cb = None
            self._subscribed = True

        def _unsubscribe_external(self):
            if not self._subscribed:
                return
            self._subscribed = False
            try:
                if self._reg_cb is not None:
                    from chisurf.core import parameter_group_registry as reg
                    reg.unsubscribe(self._reg_cb)
            except Exception:
                pass
            try:
                if self._fc_cb is not None:
                    fc, cb = self._fc_cb
                    fc.unsubscribe("parameter.", cb)
                    fc.unsubscribe("fit.", cb)
            except Exception:
                pass
            self._reg_cb = self._fc_cb = None

        def _on_external_event(self, *args, **kwargs):
            # May arrive on an RPC thread — hop to the GUI thread via a queued
            # signal before touching widgets.
            try:
                self._externalEvent.emit()
            except Exception:
                pass

        def _on_external_gui(self):
            # GUI thread: refresh the table (a link may have changed a shown
            # value) and tell plot_main to re-diff + recompute.
            self._refresh_table()
            self.constantsChangedExternally.emit()

        # -- edit signal ---------------------------------------------------
        def _on_change(self):
            if self._callback is not None:
                try:
                    self._callback()
                except Exception:
                    pass

        def set_callback(self, cb):
            self._callback = cb
            if self._cs_editor is not None:
                self._cs_editor.callback = cb

        def _add_parameter(self):
            """Prompt for a new constant (name + value) and append it to the group."""
            if self._group is None:
                return
            name, ok = QtWidgets.QInputDialog.getText(self, "Add parameter", "Parameter name:")
            name = (name or "").strip()
            if not ok or not name:
                return
            if name in self._group.parameters_all_dict:
                QtWidgets.QMessageBox.information(
                    self, "Add parameter", f"A parameter named '{name}' already exists."
                )
                return
            value, ok = QtWidgets.QInputDialog.getDouble(
                self, "Add parameter", f"Value for '{name}':", 0.0, -1e12, 1e12, 6
            )
            if not ok:
                return
            self._cg.apply_value_dict(self._group, {name: float(value)})
            try:
                self._table.set_params(self._group.parameters_all)
            except Exception:
                self._refresh_table()
            self._on_change()  # host re-diffs constants -> recompute + names update

        # -- public data surface ------------------------------------------
        @property
        def dict(self):
            """Flat ``{name: value}`` snapshot (drives the throttle + seeding)."""
            if self._group is not None:
                return self._cg.group_to_value_dict(self._group)
            return self._cs_editor.dict

        def apply_values(self, values):
            """Set constants from a flat ``{name: value}`` mapping.

            The write has to reach the parameter *table*, because the table is
            what ``plot_main._schedule_parameter_recompute`` reads back into
            ``plot_main.constants``. A caller that only updates the ``constants``
            mapping has its values silently reverted on the next parameter event
            — which is what happened to an automatic FRET calibration pushed in
            from outside.

            Names not yet in the group are appended, so a calibration may
            introduce a constant the shipped table does not carry.

            Parameters
            ----------
            values : Mapping[str, float]
                Constant name to value.
            """
            if self._group is not None:
                self._cg.apply_value_dict(self._group, values)
                self._refresh_table()
                return
            editor = self._cs_editor
            target = getattr(editor, "dict", None) if editor is not None else None
            if isinstance(target, dict):
                target.update({str(k): float(v) for k, v in dict(values).items()})

        def get_state(self):
            """Rich per-parameter state (value + bounds + fixed) for persistence."""
            if self._group is not None:
                return self._cg.group_state(self._group)
            return {"parameters": {k: {"value": v} for k, v in self.dict.items()}}

        def set_state(self, state):
            if self._group is not None:
                self._cg.apply_group_state(self._group, state)
                self._refresh_table()

        def _refresh_table(self):
            if self._table is not None:
                try:
                    self._table.sync()
                except Exception:
                    pass

        @property
        def json_file(self):
            return self._json_file

        @json_file.setter
        def json_file(self, v):
            self._json_file = v
            data = self._load_data(v)
            if self._group is not None:
                if self._cg.is_state_format(data):
                    self._cg.apply_group_state(self._group, data)
                else:
                    self._cg.apply_value_dict(self._group, self._cg.values_from_data(data))
                self._refresh_table()
            elif self._cs_editor is not None:
                self._cs_editor.json_file = v

else:
    from pyqtgraph.parametertree import Parameter, ParameterTree
    from pyqtgraph.parametertree.parameterTypes import ListParameter

    def dict2pt(target, origin):
        """Creates an array from a dictionary that can be used to initialize a pyqtgraph parameter-tree"""
        for i, key in enumerate(origin.keys()):
            if key.endswith('_options'):
                target[-1]['values'] = origin[key]
                target[-1]['type'] = 'list'
                continue
            d = dict()
            d['name'] = key
            if isinstance(origin[key], dict):
                d['type'] = 'group'
                d['children'] = dict2pt(list(), origin[key])
            else:
                value = origin[key]
                type = value.__class__.__name__
                if type == 'unicode':
                    type = 'str'
                iscolor = re.search(r'^#(?:[0-9a-fA-F]{3}){1,2}$', str(value))
                if iscolor:
                    type = 'color'
                if type == 'float':
                    d['dec'] = True
                    import math
                    av = abs(float(value))
                    min_step = 10 ** (math.floor(math.log10(av)) - 4)
                    d['minStep'] = min_step
                elif type == 'int':
                    d['int'] = True
                    d['step'] = 1
                d['type'] = type
                d['value'] = value
                d['expanded'] = False
            target.append(d)
        return target

    def pt2dict(parameter_tree, target=OrderedDict()):
        """Converts a pyqtgraph parameter tree to an ordinary dictionary that could be saved as JSON file"""
        children = parameter_tree.children()
        for i, child in enumerate(children):
            if child.type() == "action":
                continue
            if not child.children():
                value = child.opts['value']
                name = child.name()
                if isinstance(value, QtGui.QColor):
                    value = str(value.name())
                if isinstance(child, ListParameter):
                    target[name + '_options'] = child.opts['values']
                target[name] = value
            else:
                target[child.name()] = pt2dict(child, OrderedDict())
        return target

    class ParameterEditor(QtWidgets.QWidget):
        def __init__(
                self,
                json_file=None,  # type: str
                parent=None,  # type: QtWidgets.QWidget
                callback=None  # type: callable
        ):
            super(ParameterEditor, self).__init__(parent)

            self._dict = dict()  # type: Dict
            self._p = None
            self._json_file = None  # type: str
            self._target = list()  # type: List

            self._json_file = json_file
            self.json_file = json_file

            self._p = Parameter.create(
                name='params',
                type='group',
                children=dict2pt(self._target, self._dict),
                expanded=True
            )

            self.setWindowTitle("Configuration: %s" % self.json_file)
            t = ParameterTree()
            t.setParameters(self._p, showTop=False)
            layout = QtWidgets.QGridLayout()
            layout.addWidget(t, 1, 0, 1, 1)
            self.setLayout(layout)
            self.setSizePolicy(
                QtWidgets.QSizePolicy(
                    QtWidgets.QSizePolicy.Expanding,
                    QtWidgets.QSizePolicy.Expanding
                )
            )

            self.set_callback(callback)

        def set_callback(self, cb, root=None):
            if root is None:
                root = self._p
            root.sigValueChanged.connect(cb)
            for ch in root.children():
                self.set_callback(cb, ch)

        @property
        def dict(self):
            if self._p is not None:
                return pt2dict(self._p, OrderedDict())
            else:
                return self._dict

        def apply_values(self, values):
            """Set constants from a flat ``{name: value}`` mapping.

            Mirrors the chisurf-backed editor's method so a caller (e.g. an
            automatic FRET calibration) can write the table without knowing
            which implementation is in use. Unknown names are added to the
            backing dict.

            Parameters
            ----------
            values : Mapping[str, float]
                Constant name to value.
            """
            for key, value in dict(values).items():
                key, value = str(key), float(value)
                parameter = None
                if self._p is not None:
                    try:
                        parameter = self._p.param(key)
                    except Exception:
                        parameter = None
                if parameter is not None:
                    parameter.setValue(value)
                else:
                    self._dict[key] = value

        @property
        def parameter_dict(self):
            od = OrderedDict(self.dict)
            params = dict2pt(list(), od)
            params.append(
                {
                    'name': 'Save',
                    'type': 'action'
                }
            )
            return params

        @property
        def json_file(self):
            return self._json_file

        @json_file.setter
        def json_file(self, v):
            if v is not None and pathlib.Path(v).exists():
                with open(v, 'r') as fp:
                    self._dict = json.load(fp, object_pairs_hook=OrderedDict)
            else:
                logging.warning(f"Parameter file not found: {v}")
                try:
                    default_v = pathlib.Path(__file__).parent.parent / "settings" / "mfd.constants.json"
                    if default_v.exists():
                        with open(default_v, 'r') as fp:
                            self._dict = json.load(fp, object_pairs_hook=OrderedDict)
                except Exception as e:
                    logging.error(f"Failed to load default parameters: {e}")
            self._json_file = v


def main():
    app = QtWidgets.QApplication(sys.argv)
    target = dict()
    pt = ParameterEditor(
        target=target,
        json_file="settings/mfd.constants.json"
    )
    pt.show()
    app.exec_()


if __name__ == "__main__":
    main()
