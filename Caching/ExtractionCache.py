from abc import ABC, abstractmethod
from typing import Any, Hashable, Optional


class ExtractionCache(ABC):
    """
    Abstract interface for a cache of expensive per-point extraction results,
    keyed by identity (e.g. the store_ids of the y_value/efold_value concept
    objects involved in a query) rather than by floating-point proximity.

    Contract: cached values must never themselves be None. get() returns None
    to signal a cache miss, so a caller cannot distinguish "key not cached"
    from "key cached with value None" through this interface. This is an
    acceptable simplification for the intended payload — (zeta, r) tuples of
    floats, which can never legitimately be None — but any future caller with
    different payload semantics must not store None as a value.
    """

    @abstractmethod
    def get(self, key: Hashable) -> Optional[Any]:
        """Return the cached value for key, or None if key has not been cached."""
        ...

    @abstractmethod
    def set(self, key: Hashable, value: Any) -> None:
        """Store value under key, overwriting any previously cached value."""
        ...

    @abstractmethod
    def clear(self) -> None:
        """Remove all cached entries."""
        ...


class InMemoryExtractionCache(ExtractionCache):
    """
    Plain dict-backed implementation of ExtractionCache.

    Not thread-safe: concurrent get()/set() calls from multiple threads on
    the same instance are not synchronised. Not shared across Ray worker
    processes: each worker/process constructing its own
    InMemoryExtractionCache gets an independent, unshared cache. Both are
    known, deliberate limitations for now, not something to work around in
    this implementation — a cross-process backend (e.g. Ray-object-store- or
    Redis-backed) can be swapped in later behind the same ExtractionCache
    interface if needed.
    """

    def __init__(self):
        self._store: dict = {}

    def get(self, key: Hashable) -> Optional[Any]:
        return self._store.get(key)

    def set(self, key: Hashable, value: Any) -> None:
        self._store[key] = value

    def clear(self) -> None:
        self._store.clear()
