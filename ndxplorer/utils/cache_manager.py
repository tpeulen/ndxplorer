"""
Advanced caching system for ndxplorer computations.

Provides multi-level caching with LRU eviction, memory-aware limits,
and hash-based invalidation for expensive operations like histograms.
"""

from __future__ import annotations

import hashlib
import time
from collections import OrderedDict
from typing import Any, Optional, Tuple, Callable
import numpy as np

from ..logging_config import logging


class CacheEntry:
    """Single cache entry with metadata."""
    
    __slots__ = ('value', 'timestamp', 'hits', 'size_bytes')
    
    def __init__(self, value: Any, size_bytes: int = 0):
        self.value = value
        self.timestamp = time.perf_counter()
        self.hits = 0
        self.size_bytes = size_bytes


class LRUCache:
    """
    Least Recently Used cache with memory limits.
    
    Features:
    - Automatic eviction when memory limit exceeded
    - Access count tracking
    - Fast hash-based lookups
    - Memory-aware capacity management
    """
    
    def __init__(self, max_memory_mb: float = 100.0, max_entries: int = 100):
        """
        Parameters
        ----------
        max_memory_mb : float
            Maximum memory usage in MB before eviction
        max_entries : int
            Maximum number of entries before eviction
        """
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._max_memory_bytes = int(max_memory_mb * 1024 * 1024)
        self._max_entries = max_entries
        self._current_memory = 0
        self._hits = 0
        self._misses = 0
    
    def _compute_size(self, value: Any) -> int:
        """Estimate memory size of value in bytes."""
        if isinstance(value, np.ndarray):
            return value.nbytes
        elif isinstance(value, tuple):
            return sum(self._compute_size(v) for v in value)
        elif isinstance(value, dict):
            return sum(self._compute_size(k) + self._compute_size(v) for k, v in value.items())
        else:
            # Rough estimate for other types
            return 64
    
    def _evict_if_needed(self, incoming_size: int) -> None:
        """Evict LRU entries until we have space."""
        while (
            self._cache and
            (len(self._cache) >= self._max_entries or 
             self._current_memory + incoming_size > self._max_memory_bytes)
        ):
            key, entry = self._cache.popitem(last=False)
            self._current_memory -= entry.size_bytes
            logging.debug(f"[LRUCache] Evicted key {key[:16]}... (freed {entry.size_bytes} bytes)")
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache, updating access order."""
        if key in self._cache:
            self._hits += 1
            entry = self._cache[key]
            entry.hits += 1
            entry.timestamp = time.perf_counter()
            # Move to end (most recent)
            self._cache.move_to_end(key)
            return entry.value
        self._misses += 1
        return None
    
    def put(self, key: str, value: Any) -> None:
        """Add or update cache entry."""
        size = self._compute_size(value)
        
        # Remove old entry if updating
        if key in self._cache:
            old_entry = self._cache.pop(key)
            self._current_memory -= old_entry.size_bytes
        
        self._evict_if_needed(size)
        
        entry = CacheEntry(value, size)
        self._cache[key] = entry
        self._current_memory += size
    
    def invalidate(self, key: str) -> None:
        """Remove specific entry from cache."""
        if key in self._cache:
            entry = self._cache.pop(key)
            self._current_memory -= entry.size_bytes
    
    def clear(self) -> None:
        """Clear entire cache."""
        self._cache.clear()
        self._current_memory = 0
        self._hits = 0
        self._misses = 0
    
    def stats(self) -> dict:
        """Return cache statistics."""
        total = self._hits + self._misses
        hit_rate = self._hits / total if total > 0 else 0.0
        return {
            'entries': len(self._cache),
            'memory_mb': self._current_memory / (1024 * 1024),
            'hits': self._hits,
            'misses': self._misses,
            'hit_rate': hit_rate,
        }


# HistogramCache stood here, keyed on three sampled values of the data (first,
# middle, last) and on the number of points a gate kept -- so two datasets that
# happened to agree at three positions shared a key, as did two gates keeping
# the same count. Nothing ever put a histogram in it, and there is no histogram
# to cache any more: a fill costs a few milliseconds, less than deciding
# whether a cached one is still valid.

class ComputationCache:
    """
    General-purpose memoization cache for expensive computations.
    
    Supports automatic key generation from function arguments.
    """
    
    def __init__(self, max_memory_mb: float = 50.0):
        self._cache = LRUCache(max_memory_mb=max_memory_mb, max_entries=100)
    
    def _make_key(self, func_name: str, args: tuple, kwargs: dict) -> str:
        """Create a cache key from the function name and its arguments.

        Arrays are hashed by their **contents**, positionally for args and by
        name for kwargs. Neither used to be: an array argument contributed three
        sampled values, and an array *keyword* argument contributed only its
        shape and dtype -- so ``f(data, weights=w1)`` and ``f(data, weights=w2)``
        were the same call as far as this cache was concerned, and the second
        got the first one's answer.
        """
        h = hashlib.blake2b(digest_size=16)
        h.update(func_name.encode())

        def _digest(value) -> None:
            if isinstance(value, np.ndarray):
                h.update(b'ndarray')
                h.update(str(value.shape).encode())
                h.update(str(value.dtype).encode())
                h.update(np.ascontiguousarray(value).tobytes())
            else:
                h.update(b'repr')
                h.update(repr(value).encode())

        for arg in args:
            _digest(arg)

        for k, v in sorted(kwargs.items()):
            h.update(k.encode())
            _digest(v)

        return h.hexdigest()
    
    def memoize(self, func: Callable) -> Callable:
        """
        Decorator to memoize function results.
        
        Example:
            @cache_manager.computation_cache.memoize
            def expensive_function(data):
                return slow_computation(data)
        """
        def wrapper(*args, **kwargs):
            key = self._make_key(func.__name__, args, kwargs)
            result = self._cache.get(key)
            if result is not None:
                logging.debug(f"[ComputationCache] Hit for {func.__name__}")
                return result
            
            logging.debug(f"[ComputationCache] Miss for {func.__name__}, computing...")
            result = func(*args, **kwargs)
            self._cache.put(key, result)
            return result
        
        wrapper.__name__ = func.__name__
        wrapper.__doc__ = func.__doc__
        return wrapper
    
    def clear(self) -> None:
        """Clear computation cache."""
        self._cache.clear()
    
    def stats(self) -> dict:
        """Return cache statistics."""
        return self._cache.stats()


class CacheManager:
    """
    Central cache manager for ndxplorer.
    
    Manages multiple specialized caches with coordinated memory limits.
    """
    
    def __init__(
        self,
        computation_memory_mb: float = 50.0,
        general_memory_mb: float = 50.0,
    ):
        self.computation_cache = ComputationCache(max_memory_mb=computation_memory_mb)
        self.general_cache = LRUCache(max_memory_mb=general_memory_mb, max_entries=100)
    
    def clear_all(self) -> None:
        """Clear all caches."""
        self.computation_cache.clear()
        self.general_cache.clear()
        logging.info("[CacheManager] All caches cleared")
    
    def stats(self) -> dict:
        """Return statistics for all caches."""
        return {
            'computation': self.computation_cache.stats(),
            'general': self.general_cache.stats(),
        }
    
    def log_stats(self) -> None:
        """Log cache statistics."""
        stats = self.stats()
        logging.info("[CacheManager] Statistics:")
        for cache_name, cache_stats in stats.items():
            logging.info(f"  {cache_name}: {cache_stats}")


# Global cache manager instance
_global_cache_manager: Optional[CacheManager] = None


def get_cache_manager() -> CacheManager:
    """Get or create global cache manager."""
    global _global_cache_manager
    if _global_cache_manager is None:
        _global_cache_manager = CacheManager()
    return _global_cache_manager


def clear_all_caches() -> None:
    """Clear all ndxplorer caches."""
    manager = get_cache_manager()
    manager.clear_all()
