"""
Unit and integration tests for the n_collocation_points concept object and its
SQL factory.

n_collocation_points is a pure numerical-implementation (solver-convergence)
parameter: an exact integer count fed to Numerics/LGLCollocation.py's
LGLCollocationGrid. It must therefore be looked up by exact equality, not a
tolerance band -- unlike delta_Nstar/alpha_regularization, which are
continuous floats.

The SQL round-trip tests require the live_pool session fixture (needs a Ray
cluster running) and are marked ``integration`` so they are excluded from the
fast unit-test run via ``pytest -m "not integration"``.
"""

import pytest
import ray

from InflationConcepts.n_collocation_points import n_collocation_points


# ---------------------------------------------------------------------------
# Pure-Python unit tests: construction, ordering, equality, hashing
# ---------------------------------------------------------------------------

class TestNCollocationPointsConstruction:
    def test_valid_construction(self):
        obj = n_collocation_points(store_id=1, n_collocation_points=17)
        assert int(obj) == 17
        assert float(obj) == 17.0

    def test_store_id_none_raises(self):
        with pytest.raises(ValueError):
            n_collocation_points(store_id=None, n_collocation_points=17)

    def test_non_integer_raises(self):
        with pytest.raises(ValueError) as excinfo:
            n_collocation_points(store_id=1, n_collocation_points=17.5)
        assert "integer" in str(excinfo.value)

    def test_below_minimum_raises(self):
        for bad_value in (0, 1, -5):
            with pytest.raises(ValueError) as excinfo:
                n_collocation_points(store_id=1, n_collocation_points=bad_value)
            assert ">= 2" in str(excinfo.value)

    def test_type_and_value_errors_have_distinct_messages(self):
        with pytest.raises(ValueError) as type_err:
            n_collocation_points(store_id=1, n_collocation_points=17.5)
        with pytest.raises(ValueError) as value_err:
            n_collocation_points(store_id=1, n_collocation_points=1)
        assert str(type_err.value) != str(value_err.value)

    def test_no_n_max_property(self):
        obj = n_collocation_points(store_id=1, n_collocation_points=17)
        assert not hasattr(obj, "n_max")


class TestNCollocationPointsOrdering:
    def test_ordering_by_count(self):
        small = n_collocation_points(store_id=1, n_collocation_points=5)
        large = n_collocation_points(store_id=2, n_collocation_points=17)
        assert small < large
        assert large > small
        assert small <= large
        assert large >= small

    def test_sorted(self):
        a = n_collocation_points(store_id=1, n_collocation_points=33)
        b = n_collocation_points(store_id=2, n_collocation_points=5)
        c = n_collocation_points(store_id=3, n_collocation_points=17)
        assert sorted([a, b, c], key=int) == [b, c, a]


class TestNCollocationPointsEqualityHashing:
    def test_equality_by_store_id(self):
        a = n_collocation_points(store_id=1, n_collocation_points=17)
        b = n_collocation_points(store_id=1, n_collocation_points=17)
        assert a == b

    def test_inequality_different_store_id(self):
        a = n_collocation_points(store_id=1, n_collocation_points=17)
        b = n_collocation_points(store_id=2, n_collocation_points=17)
        assert a != b

    def test_hash_consistent_with_equality(self):
        a = n_collocation_points(store_id=1, n_collocation_points=17)
        b = n_collocation_points(store_id=1, n_collocation_points=17)
        assert hash(a) == hash(b)
        assert len({a, b}) == 1


# ---------------------------------------------------------------------------
# SQL round-trip tests: exact-equality lookup, no tolerance collision
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestNCollocationPointsSQLRoundTrip:
    def test_same_count_returns_same_store_id(self, live_pool):
        first, second = ray.get([
            live_pool.object_get("n_collocation_points", payload_data=[{"n_collocation_points": 21}]),
            live_pool.object_get("n_collocation_points", payload_data=[{"n_collocation_points": 21}]),
        ])
        assert first[0].store_id == second[0].store_id

    def test_adjacent_counts_are_distinct(self, live_pool):
        n25, n26 = ray.get([
            live_pool.object_get("n_collocation_points", payload_data=[{"n_collocation_points": 25}]),
            live_pool.object_get("n_collocation_points", payload_data=[{"n_collocation_points": 26}]),
        ])
        assert n25[0].store_id != n26[0].store_id
        assert int(n25[0]) == 25
        assert int(n26[0]) == 26
