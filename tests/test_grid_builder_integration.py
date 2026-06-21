"""
Integration tests for config/grid_builder.py — requires a live ShardedPool.

These tests verify that build_grid_from_csv and the axis-grid path
(pool.object_get with payload_data) produce identical store_ids for the
same float values, against a real database.  This was an explicit
acceptance criterion of prompt 2 (build_grid_from_csv) that the mock-based
tests in test_grid_builder.py could not satisfy.

Mark: ``@pytest.mark.integration`` — excluded from the fast unit-test run
via ``pytest -m "not integration"``.
"""

import os
import tempfile

import pytest
import ray

from config.grid_builder import build_grid_from_csv


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write_csv(content: str) -> str:
    fd, path = tempfile.mkstemp(suffix=".csv")
    with os.fdopen(fd, "w") as f:
        f.write(content)
    return path


def _count_approx(values: list, target: float, rtol: float = 1e-9) -> int:
    """Count entries in *values* within *rtol* of *target* (relative tolerance)."""
    if abs(target) == 0.0:
        return sum(1 for v in values if abs(v) < rtol)
    return sum(1 for v in values if abs(v - target) / abs(target) < rtol)


def _mint_via_object_get(pool, n_init_val, n_final_val, dns_val):
    """
    Mint (N_init, N_final, delta_Nstar) objects using the same pool.object_get
    pattern as build_pipeline_inputs / the axis-grid path.  Returns a tuple of
    the three domain objects.
    """
    n_init_list, n_final_list, dns_list = ray.get([
        pool.object_get("N_init",      payload_data=[{"value": n_init_val}]),
        pool.object_get("N_final",     payload_data=[{"value": n_final_val}]),
        pool.object_get("delta_Nstar", payload_data=[{"value": dns_val}]),
    ])
    return n_init_list[0], n_final_list[0], dns_list[0]


# ---------------------------------------------------------------------------
# Unique values for these tests — chosen to avoid interference with any other
# integration test that shares the session-scoped pool's database.
# ---------------------------------------------------------------------------
_N_INIT_A  = 61.0
_N_FINAL_A = 1.0
_DNS_A     = 0.3

_N_INIT_B  = 62.0   # used in the distinct-values sanity check
_N_INIT_C  = 63.0

_MODEL_LIST = [{"label": "M"}]


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestCsvAxisGridDedup:
    """
    Verify that build_grid_from_csv and direct pool.object_get give the same
    store_ids for matching float values, and that no duplicate rows are
    created in the underlying tables.
    """

    def test_store_ids_match_between_csv_and_axis_grid_path(self, live_pool, tmp_path):
        """
        Minting the same (N_init, N_final, delta_Nstar) triple through the
        axis-grid path (pool.object_get) and then through build_grid_from_csv
        must yield identical store_ids — not just matching float values.
        """
        # Axis-grid path: same call pattern as build_pipeline_inputs
        n_init_a, n_final_a, dns_a = _mint_via_object_get(
            live_pool, _N_INIT_A, _N_FINAL_A, _DNS_A
        )

        # CSV path
        csv_content = (
            f"N_init,N_final,delta_Nstar\n"
            f"{_N_INIT_A},{_N_FINAL_A},{_DNS_A}\n"
        )
        csv_path = _write_csv(csv_content)
        try:
            grid = build_grid_from_csv(live_pool, csv_path, _MODEL_LIST)
        finally:
            os.unlink(csv_path)

        assert len(grid) == 1
        _, n_init_b, n_final_b, dns_b = grid[0]

        assert n_init_b.store_id  == n_init_a.store_id,  "N_init store_id mismatch"
        assert n_final_b.store_id == n_final_a.store_id, "N_final store_id mismatch"
        assert dns_b.store_id     == dns_a.store_id,     "delta_Nstar store_id mismatch"

    def test_no_duplicate_rows_created(self, live_pool, tmp_path):
        """
        After minting the same value through both paths, the underlying table
        must contain exactly one row for that value — not two.

        Uses pool.inventory() (available for all replicated tables without
        requiring read_table_config) to count rows by value.
        """
        # Ensure the value is in the DB via the axis-grid path
        _mint_via_object_get(live_pool, _N_INIT_A, _N_FINAL_A, _DNS_A)

        # Mint again via the CSV path
        csv_content = (
            f"N_init,N_final,delta_Nstar\n"
            f"{_N_INIT_A},{_N_FINAL_A},{_DNS_A}\n"
        )
        csv_path = _write_csv(csv_content)
        try:
            build_grid_from_csv(live_pool, csv_path, _MODEL_LIST)
        finally:
            os.unlink(csv_path)

        # Exactly one row for each target value in the respective tables
        n_init_inv = live_pool.inventory("N_init")
        n_final_inv = live_pool.inventory("N_final")
        dns_inv = live_pool.inventory("delta_Nstar")

        assert _count_approx(n_init_inv["values"],  _N_INIT_A)  == 1, \
            f"Expected 1 N_init row for {_N_INIT_A}, got {_count_approx(n_init_inv['values'], _N_INIT_A)}"
        assert _count_approx(n_final_inv["values"], _N_FINAL_A) == 1, \
            f"Expected 1 N_final row for {_N_FINAL_A}, got {_count_approx(n_final_inv['values'], _N_FINAL_A)}"
        assert _count_approx(dns_inv["values"],     _DNS_A)     == 1, \
            f"Expected 1 delta_Nstar row for {_DNS_A}, got {_count_approx(dns_inv['values'], _DNS_A)}"

    def test_distinct_values_give_distinct_store_ids_via_both_paths(self, live_pool, tmp_path):
        """
        Sanity check: two distinct float values must produce distinct store_ids
        through both the axis-grid path and the CSV path.  This confirms the
        dedup tests above are not trivially passing because the pool maps
        everything to a single sentinel ID.
        """
        # Axis-grid path: two different N_init values
        n_init_b, _, _ = _mint_via_object_get(live_pool, _N_INIT_B, _N_FINAL_A, _DNS_A)
        n_init_c, _, _ = _mint_via_object_get(live_pool, _N_INIT_C, _N_FINAL_A, _DNS_A)

        assert n_init_b.store_id != n_init_c.store_id, \
            "Distinct N_init values must have distinct store_ids via the axis-grid path"

        # CSV path: same two different values in a two-row CSV
        csv_content = (
            f"N_init,N_final,delta_Nstar\n"
            f"{_N_INIT_B},{_N_FINAL_A},{_DNS_A}\n"
            f"{_N_INIT_C},{_N_FINAL_A},{_DNS_A}\n"
        )
        csv_path = _write_csv(csv_content)
        try:
            grid = build_grid_from_csv(live_pool, csv_path, _MODEL_LIST)
        finally:
            os.unlink(csv_path)

        # grid = [(0, n_init_b2, ...), (0, n_init_c2, ...)]
        assert len(grid) == 2
        _, n_init_b2, _, _ = grid[0]
        _, n_init_c2, _, _ = grid[1]

        assert n_init_b2.store_id != n_init_c2.store_id, \
            "Distinct N_init values must have distinct store_ids via the CSV path"

        # Cross-path: each CSV-derived object has the same ID as the axis-grid one
        assert n_init_b2.store_id == n_init_b.store_id, \
            "N_init store_id for value B differs between axis-grid and CSV paths"
        assert n_init_c2.store_id == n_init_c.store_id, \
            "N_init store_id for value C differs between axis-grid and CSV paths"
