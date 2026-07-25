"""
Parameter Editor widget.
Uses chisurf's ParameterEditor if chisurf is available,
otherwise falls back to the local pyqtgraph-based implementation.
"""
from typing import Dict, List
from qtpy import QtGui, QtWidgets
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

            data = self._load_data(json_file)

            layout = QtWidgets.QGridLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)

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
                )
                layout.addWidget(self._table)
                self._register_group()
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
                    self._group, owner_id=_NDX_OWNER_ID, label="ndXplorer"
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
            self._unregister_group()
            super().closeEvent(event)

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

        # -- public data surface ------------------------------------------
        @property
        def dict(self):
            """Flat ``{name: value}`` snapshot (drives the throttle + seeding)."""
            if self._group is not None:
                return self._cg.group_to_value_dict(self._group)
            return self._cs_editor.dict

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
