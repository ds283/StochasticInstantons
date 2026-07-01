"""
Unit and integration tests for the y_value/y_array shared concept objects and
their SQL persistence layer (Datastore/SQL/ObjectFactories/y.py).

Mirrors the style of the round-trip/dedup tests exercised for efold_value in
tests/test_scalars_only_storage.py (see _get_prerequisites' use of
pool.object_get("efold_value", ...)).

Pure-Python tests (ordering, equality, hashing, y_array, out-of-range guard)
require no fixtures. The SQL round-trip/dedup tests require the live_pool
session fixture (needs a Ray cluster running) and are marked ``integration``.
"""

import pytest
import ray

from InflationConcepts.y_value import y_value, y_array, check_ysample


# ---------------------------------------------------------------------------
# y_value: ordering, equality, hashing
# ---------------------------------------------------------------------------

def test_y_value_ordering():
    a = y_value(store_id=1, y=0.1)
    b = y_value(store_id=2, y=0.5)
    c = y_value(store_id=3, y=0.9)

    assert a < b < c
    assert c > b > a
    assert sorted([c, a, b]) == [a, b, c]


def test_y_value_equality_by_store_id():
    a1 = y_value(store_id=1, y=0.3)
    a2 = y_value(store_id=1, y=0.7)  # same store_id, different y: still equal
    b = y_value(store_id=2, y=0.3)

    assert a1 == a2
    assert a1 != b


def test_y_value_equality_raises_for_other_types():
    a = y_value(store_id=1, y=0.3)
    with pytest.raises(NotImplementedError):
        a == 0.3
    with pytest.raises(NotImplementedError):
        a < 0.3


def test_y_value_hashing():
    a1 = y_value(store_id=1, y=0.3)
    a2 = y_value(store_id=1, y=0.3)
    b = y_value(store_id=2, y=0.3)

    assert hash(a1) == hash(a2)
    assert {a1, a2, b} == {a1, b}  # a1/a2 collapse in a set


def test_y_value_float_cast():
    a = y_value(store_id=1, y=0.42)
    assert float(a) == 0.42


def test_y_value_requires_store_id():
    with pytest.raises(ValueError):
        y_value(store_id=None, y=0.5)


# ---------------------------------------------------------------------------
# y_value: out-of-range construction guard
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("y", [-0.5, -0.1, 1.1, 2.0])
def test_y_value_out_of_range_raises(y):
    with pytest.raises(ValueError):
        y_value(store_id=1, y=y)


@pytest.mark.parametrize("y", [0.0, 0.5, 1.0])
def test_y_value_in_range_ok(y):
    obj = y_value(store_id=1, y=y)
    assert obj.y == y


# ---------------------------------------------------------------------------
# y_array: dedup, sort, as_float_list, min, max
# ---------------------------------------------------------------------------

def test_y_array_sorts_and_dedups():
    v1 = y_value(store_id=1, y=0.5)
    v2 = y_value(store_id=2, y=0.1)
    v3 = y_value(store_id=3, y=0.9)
    v1_dup = y_value(store_id=1, y=0.5)  # same store_id as v1 -> duplicate

    arr = y_array([v1, v2, v3, v1_dup])

    assert len(arr) == 3
    assert list(arr) == [v2, v1, v3]
    assert arr[0] == v2
    assert arr.min == v2
    assert arr.max == v3
    assert arr.as_float_list() == [0.1, 0.5, 0.9]


def test_y_array_equality():
    v1 = y_value(store_id=1, y=0.1)
    v2 = y_value(store_id=2, y=0.5)

    arr_a = y_array([v1, v2])
    arr_b = y_array([v2, v1])
    arr_c = y_array([v1])

    assert arr_a == arr_b
    assert arr_a != arr_c


def test_y_array_add():
    v1 = y_value(store_id=1, y=0.1)
    v2 = y_value(store_id=2, y=0.5)
    v3 = y_value(store_id=3, y=0.9)

    arr_a = y_array([v1, v2])
    arr_b = y_array([v2, v3])

    combined = arr_a + arr_b
    assert combined.as_float_list() == [0.1, 0.5, 0.9]


def test_check_ysample_passes_for_equal_grids():
    v1 = y_value(store_id=1, y=0.1)
    v2 = y_value(store_id=2, y=0.5)

    arr_a = y_array([v1, v2])
    arr_b = y_array([v2, v1])

    check_ysample(arr_a, arr_b)  # should not raise


def test_check_ysample_raises_for_unequal_grids():
    v1 = y_value(store_id=1, y=0.1)
    v2 = y_value(store_id=2, y=0.5)
    v3 = y_value(store_id=3, y=0.9)

    arr_a = y_array([v1, v2])
    arr_b = y_array([v1, v3])

    with pytest.raises(RuntimeError):
        check_ysample(arr_a, arr_b)


def test_check_ysample_accepts_object_with_y_sample_attribute():
    import types

    v1 = y_value(store_id=1, y=0.1)
    v2 = y_value(store_id=2, y=0.5)

    arr = y_array([v1, v2])
    carrier = types.SimpleNamespace(y_sample=y_array([v2, v1]))

    check_ysample(arr, carrier)  # should not raise


# ---------------------------------------------------------------------------
# SQL round-trip / dedup against the live datastore
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestYValueSQLRoundTrip:
    def test_build_twice_returns_same_store_id(self, live_pool):
        y_val = 0.314159

        first = ray.get(
            live_pool.object_get("y_value", payload_data=[{"y": y_val}])
        )[0]
        second = ray.get(
            live_pool.object_get("y_value", payload_data=[{"y": y_val}])
        )[0]

        assert first.store_id == second.store_id
        assert first == second

    def test_distinct_y_values_get_distinct_store_ids(self, live_pool):
        first = ray.get(
            live_pool.object_get("y_value", payload_data=[{"y": 0.111111}])
        )[0]
        second = ray.get(
            live_pool.object_get("y_value", payload_data=[{"y": 0.888888}])
        )[0]

        assert first.store_id != second.store_id
