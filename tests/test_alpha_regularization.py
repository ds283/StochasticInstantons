"""
Unit and integration tests for the alpha_regularization concept object and its
SQL factory.

alpha_regularization is a pure numerical-implementation (solver-convergence)
parameter: the continuous coordinate regularization parameter alpha consumed
by Numerics/OnionCoordinate.py's delta_s(). It must therefore use ordinary
tolerance-banded float lookup (matching delta_Nstar/N_init), including the
zero-vs-nonzero absolute/relative branching -- alpha == 0 is a valid,
well-defined value, not just "small".

The SQL round-trip tests require the live_pool session fixture (needs a Ray
cluster running) and are marked ``integration`` so they are excluded from the
fast unit-test run via ``pytest -m "not integration"``.
"""

import pytest
import ray

from InflationConcepts.alpha_regularization import alpha_regularization


# ---------------------------------------------------------------------------
# Pure-Python unit tests: construction, ordering, equality, hashing
# ---------------------------------------------------------------------------

class TestAlphaRegularizationConstruction:
    def test_valid_construction(self):
        obj = alpha_regularization(store_id=1, alpha=0.05)
        assert float(obj) == 0.05

    def test_store_id_none_raises(self):
        with pytest.raises(ValueError):
            alpha_regularization(store_id=None, alpha=0.05)

    def test_negative_raises(self):
        with pytest.raises(ValueError):
            alpha_regularization(store_id=1, alpha=-0.01)

    def test_zero_is_valid(self):
        obj = alpha_regularization(store_id=1, alpha=0.0)
        assert float(obj) == 0.0


class TestAlphaRegularizationOrdering:
    def test_ordering_by_alpha(self):
        small = alpha_regularization(store_id=1, alpha=0.01)
        large = alpha_regularization(store_id=2, alpha=0.1)
        assert small < large
        assert large > small

    def test_sorted(self):
        a = alpha_regularization(store_id=1, alpha=0.5)
        b = alpha_regularization(store_id=2, alpha=0.0)
        c = alpha_regularization(store_id=3, alpha=0.1)
        assert sorted([a, b, c], key=float) == [b, c, a]


class TestAlphaRegularizationEqualityHashing:
    def test_equality_by_store_id(self):
        a = alpha_regularization(store_id=1, alpha=0.05)
        b = alpha_regularization(store_id=1, alpha=0.05)
        assert a == b

    def test_inequality_different_store_id(self):
        a = alpha_regularization(store_id=1, alpha=0.05)
        b = alpha_regularization(store_id=2, alpha=0.05)
        assert a != b

    def test_hash_consistent_with_equality(self):
        a = alpha_regularization(store_id=1, alpha=0.05)
        b = alpha_regularization(store_id=1, alpha=0.05)
        assert hash(a) == hash(b)
        assert len({a, b}) == 1


# ---------------------------------------------------------------------------
# SQL round-trip tests: tolerance-banded lookup, both zero (absolute) and
# nonzero (relative) branches exercised distinctly.
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestAlphaRegularizationSQLRoundTrip:
    def test_zero_alpha_round_trip_absolute_branch(self, live_pool):
        first, second = ray.get([
            live_pool.object_get("alpha_regularization", payload_data=[{"alpha": 0.0}]),
            live_pool.object_get("alpha_regularization", payload_data=[{"alpha": 0.0}]),
        ])
        assert first[0].store_id == second[0].store_id
        assert float(first[0]) == 0.0

    def test_nonzero_alpha_round_trip_relative_branch(self, live_pool):
        first, second = ray.get([
            live_pool.object_get("alpha_regularization", payload_data=[{"alpha": 0.037}]),
            live_pool.object_get("alpha_regularization", payload_data=[{"alpha": 0.037}]),
        ])
        assert first[0].store_id == second[0].store_id
        assert float(first[0]) == pytest.approx(0.037)

    def test_zero_and_nonzero_are_distinct(self, live_pool):
        zero, nonzero = ray.get([
            live_pool.object_get("alpha_regularization", payload_data=[{"alpha": 0.0}]),
            live_pool.object_get("alpha_regularization", payload_data=[{"alpha": 0.021}]),
        ])
        assert zero[0].store_id != nonzero[0].store_id
