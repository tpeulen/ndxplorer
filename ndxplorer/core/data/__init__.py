"""
Data management layer for NDXplorer.

This package provides a clean separation between data operations and UI,
making the code more testable and maintainable.
"""

from .data_manager import DataManager
from .cache_coordinator import CacheCoordinator
from .mask_state import MaskState

__all__ = ['DataManager', 'CacheCoordinator', 'MaskState']
