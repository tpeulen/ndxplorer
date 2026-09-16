"""File reading and writing.

``__all__`` names only what actually exists here. It used to name four symbols
that did not (``read_data``, ``write_data``, ``FileOperations``,
``open_file_dialog``), which turns ``from ndxplorer.io import *`` into an
AttributeError rather than the convenience it looks like.
"""

from .reader import *
from .writer import *
from .file_operations import *
from .file_open_helpers import *

#: Nothing is re-exported: the two names that used to be here,
#: ``save_burst_ids`` and ``save_clustering_data``, are GUI actions -- they
#: take the main window and raise file dialogs -- and live in
#: :mod:`ndxplorer.ui.export_actions`. Their headless counterparts are in
#: :mod:`ndxplorer.io.writer`.
__all__: list[str] = []
