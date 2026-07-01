"""
Unit tests for the ExtractionCache interface and its InMemoryExtractionCache
implementation (Caching/ExtractionCache.py).

All tests interact with InMemoryExtractionCache purely through the
ExtractionCache interface (get/set/clear) -- no reaching into ._store.
"""

import pytest

from Caching.ExtractionCache import ExtractionCache, InMemoryExtractionCache


@pytest.fixture
def cache() -> ExtractionCache:
    return InMemoryExtractionCache()


def test_get_on_empty_cache_returns_none(cache):
    assert cache.get(("y", 1)) is None


def test_set_then_get_returns_stored_value(cache):
    cache.set(("y", 1), (0.5, 100.0))
    assert cache.get(("y", 1)) == (0.5, 100.0)


def test_get_with_different_key_returns_none(cache):
    cache.set((1, 2), "value")
    assert cache.get((1, 3)) is None
    assert cache.get((2, 2)) is None


def test_set_twice_with_same_key_overwrites(cache):
    cache.set("k", "first")
    cache.set("k", "second")
    assert cache.get("k") == "second"


def test_clear_empties_cache(cache):
    cache.set("k1", "v1")
    cache.set("k2", "v2")
    cache.clear()
    assert cache.get("k1") is None
    assert cache.get("k2") is None


def test_usable_purely_through_interface_type():
    cache: ExtractionCache = InMemoryExtractionCache()
    assert cache.get("missing") is None
    cache.set("present", 42)
    assert cache.get("present") == 42
    cache.clear()
    assert cache.get("present") is None
