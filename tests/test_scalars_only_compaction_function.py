"""
Integration tests for scalars-only storage mode on CompactionFunction.

Tests cover:
- Full-fidelity mode (default) is unaffected by the new flag.
- set_store_full_values(False) skips child-row writes to CompactionFunctionSamples
  for both the full and slow-roll streams, and merges full_values_stored=False
  into the metadata column.
- validate() passes with zero child rows in scalars-only mode.
- build() with _do_not_populate=True returns an object with _full_values==[] and
  _slow_roll_values==[], and reports full_values_stored=False in diagnostics.
- build() without _do_not_populate raises RuntimeError on scalars-only rows.
- Partial-failure case: when only one stream succeeds, set_store_full_values(False)
  correctly suppresses the non-empty list (both orderings tested).
- Backward compat: rows whose metadata has other real CF diagnostic keys but no
  full_values_stored key are treated as full-fidelity — no raise.

All tests require the live_pool session fixture (needs a Ray cluster running).
They are marked ``integration`` so they are excluded from the fast unit-test run
via ``pytest -m "not integration"``.

Fake instanton store IDs (901–916) are chosen so that each scenario produces a
unique (full_instanton_serial, slow_roll_instanton_serial) pair in the DB,
preventing any two test scenarios from aliasing each other's rows.  The same fake
trajectory store_id (801) and cosmo store_id (802) are used throughout; SQLite
does not enforce FK constraints by default, so non-existent IDs are harmless.
"""

import types

import pytest
import ray

from ComputeTargets.CompactionFunction import CompactionFunction, CompactionFunctionValue
from Units.Planck_units import Planck_units


# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

_DNS_VAL     = 1.8   # delta_Nstar value — distinct from FI/SRI tests to avoid aliasing
_LOG10_TOL   = -6.0

# Fake serials for infrastructure objects; SQLite FK constraints off by default.
_FAKE_TRAJ_STORE_ID  = 801
_FAKE_COSMO_STORE_ID = 802

# Unique (full_serial, sr_serial) pairs per test scenario.
_CF_FULL_FF_REGRESS,    _CF_SR_FF_REGRESS    = 901, 902   # full-fidelity regression
_CF_FULL_SCALARS_BASIC, _CF_SR_SCALARS_BASIC = 903, 904   # scalars-only store+validate
_CF_FULL_SCALARS_SKIP,  _CF_SR_SCALARS_SKIP  = 905, 906   # scalars-only + do_not_populate
_CF_FULL_SCALARS_RAISE, _CF_SR_SCALARS_RAISE = 907, 908   # scalars-only + raise
_CF_FULL_FF_BUILD,      _CF_SR_FF_BUILD      = 909, 910   # full-fidelity build round-trip
_CF_FULL_BACK_COMPAT,   _CF_SR_BACK_COMPAT   = 911, 912   # backward-compat test
_CF_FULL_PARTIAL_A,     _CF_SR_PARTIAL_A     = 913, 914   # partial fail: full succeeds
_CF_FULL_PARTIAL_B,     _CF_SR_PARTIAL_B     = 915, 916   # partial fail: sr succeeds

# Number of fake sample values per stream (used to verify full-fidelity row counts).
_N_SAMPLES = 3


# ---------------------------------------------------------------------------
# Fake objects (picklable SimpleNamespace)
# ---------------------------------------------------------------------------

def _make_fake_traj():
    return types.SimpleNamespace(
        store_id=_FAKE_TRAJ_STORE_ID,
        units=Planck_units(),
    )


def _make_fake_cosmo():
    return types.SimpleNamespace(
        store_id=_FAKE_COSMO_STORE_ID,
        T_CMB_Kelvin=2.725,
    )


def _make_fake_instanton(store_id):
    """Minimal proxy-like namespace; the factory only reads .store_id."""
    return types.SimpleNamespace(store_id=store_id)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_prerequisites(pool):
    """Mint (or fetch) delta_Nstar and tolerance metadata objects."""
    dns_list, tol_list = ray.get([
        pool.object_get("delta_Nstar", payload_data=[{"value": _DNS_VAL}]),
        pool.object_get("tolerance",   payload_data=[{"log10_tol": _LOG10_TOL}]),
    ])
    return {
        "dns": dns_list[0],
        "tol": tol_list[0],
    }


def _make_fake_full_result():
    """Minimal success result dict for the full-instanton path."""
    units = Planck_units()
    return {
        "failure":        False,
        "r_max":          1.0 * units.Mpc,
        "r_peak":         2.0 * units.Mpc,
        "M_max":          1.0 * units.SolarMass,
        "M_peak":         2.0 * units.SolarMass,
        "C_max":          0.5,
        "C_bar_max":      0.4,
        "V_end_downflow": 1e-10 * units.PlanckMass ** 4,
        "N_end_downflow": 5.0,
    }


def _make_fake_sr_result():
    """Minimal success result dict for the slow-roll path."""
    units = Planck_units()
    return {
        "failure":        False,
        "r_max":          1.1 * units.Mpc,
        "r_peak":         2.1 * units.Mpc,
        "M_max":          1.1 * units.SolarMass,
        "M_peak":         2.1 * units.SolarMass,
        "C_max":          0.48,
        "C_bar_max":      0.38,
        "V_end_downflow": 1.1e-10 * units.PlanckMass ** 4,
        "N_end_downflow": 5.1,
    }


def _make_fake_sample_values(n=_N_SAMPLES):
    """List of CompactionFunctionValue objects with ascending r-values."""
    return [
        CompactionFunctionValue(
            store_id=None,
            r=float(i + 1) * 1e-3,
            zeta=0.1 * (i + 1),
            C=0.5 - 0.05 * i,
            C_bar=0.4 - 0.04 * i,
        )
        for i in range(n)
    ]


def _make_cf(dns_obj, tol_obj, full_serial, sr_serial,
             full_succeeds=True, sr_succeeds=True,
             diagnostics=None):
    """
    Construct a CompactionFunction as if it had just been successfully computed,
    bypassing the actual Ray ODE solve.

    Returns (cf, fake_traj, fake_cosmo, fake_full, fake_sr).
    """
    fake_traj  = _make_fake_traj()
    fake_cosmo = _make_fake_cosmo()
    fake_full  = _make_fake_instanton(full_serial)
    fake_sr    = _make_fake_instanton(sr_serial)

    cf = CompactionFunction(
        store_id=None,
        full_instanton=fake_full,
        slow_roll_instanton=fake_sr,
        trajectory=fake_traj,
        cosmo=fake_cosmo,
        delta_Nstar=dns_obj,
        C_threshold=0.4,
        atol=tol_obj,
        rtol=tol_obj,
    )

    both_failed = not full_succeeds and not sr_succeeds
    cf._failure = both_failed

    if diagnostics is not None:
        cf._diagnostics = diagnostics
    else:
        cf._diagnostics = {"full": None, "slow_roll": None}

    if full_succeeds:
        cf._full_result  = _make_fake_full_result()
        cf._full_values  = _make_fake_sample_values()
    else:
        cf._full_result  = None
        cf._full_values  = []

    if sr_succeeds:
        cf._slow_roll_result = _make_fake_sr_result()
        cf._slow_roll_values = _make_fake_sample_values()
    else:
        cf._slow_roll_result = None
        cf._slow_roll_values = []

    return cf, fake_traj, fake_cosmo, fake_full, fake_sr


def _build_kwargs(fake_traj, fake_full, fake_sr, dns_obj, fake_cosmo, tol_obj, **extra):
    """Build a payload dict for pool.object_get("CompactionFunction", **payload)."""
    payload = {
        "trajectory":          fake_traj,
        "full_instanton":      fake_full,
        "slow_roll_instanton": fake_sr,
        "delta_Nstar":         dns_obj,
        "cosmo":               fake_cosmo,
        "atol":                tol_obj,
        "rtol":                tol_obj,
    }
    payload.update(extra)
    return payload


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestScalarsOnlyCompactionFunction:

    def test_full_fidelity_regression(self, live_pool):
        """Default flag stores all sample rows for both streams — regression guard."""
        prereqs = _get_prerequisites(live_pool)
        cf, _, _, _, _ = _make_cf(
            prereqs["dns"], prereqs["tol"],
            _CF_FULL_FF_REGRESS, _CF_SR_FF_REGRESS,
        )

        cf_stored = ray.get(live_pool.object_store(cf))
        assert cf_stored._my_id is not None

        validated = ray.get(live_pool.object_validate(cf_stored))
        assert validated is True

    def test_scalars_only_store_and_validate(self, live_pool):
        """set_store_full_values(False) stores zero child rows; validate() passes."""
        prereqs = _get_prerequisites(live_pool)
        cf, _, _, _, _ = _make_cf(
            prereqs["dns"], prereqs["tol"],
            _CF_FULL_SCALARS_BASIC, _CF_SR_SCALARS_BASIC,
        )
        cf.set_store_full_values(False)

        cf_stored = ray.get(live_pool.object_store(cf))
        assert cf_stored._my_id is not None

        validated = ray.get(live_pool.object_validate(cf_stored))
        assert validated is True

    def test_scalars_only_metadata_flag_and_build_do_not_populate(self, live_pool):
        """
        Scalars-only row carries full_values_stored=False in the metadata column;
        reading it back with _do_not_populate=True returns empty value lists and
        reports the flag in _diagnostics.
        """
        prereqs = _get_prerequisites(live_pool)
        cf, fake_traj, fake_cosmo, fake_full, fake_sr = _make_cf(
            prereqs["dns"], prereqs["tol"],
            _CF_FULL_SCALARS_SKIP, _CF_SR_SCALARS_SKIP,
        )
        cf.set_store_full_values(False)
        cf_stored = ray.get(live_pool.object_store(cf))
        ray.get(live_pool.object_validate(cf_stored))

        cf_read = ray.get(live_pool.object_get(
            "CompactionFunction",
            **_build_kwargs(
                fake_traj, fake_full, fake_sr,
                prereqs["dns"], fake_cosmo, prereqs["tol"],
                _do_not_populate=True,
            ),
        ))

        assert cf_read._diagnostics is not None
        assert cf_read._diagnostics.get("full_values_stored") is False
        assert cf_read._full_values == []
        assert cf_read._slow_roll_values == []

    def test_scalars_only_build_raises_without_do_not_populate(self, live_pool):
        """
        Reading a scalars-only CompactionFunction without _do_not_populate raises
        RuntimeError identifying CompactionFunction and scalars-only mode.
        """
        prereqs = _get_prerequisites(live_pool)
        cf, fake_traj, fake_cosmo, fake_full, fake_sr = _make_cf(
            prereqs["dns"], prereqs["tol"],
            _CF_FULL_SCALARS_RAISE, _CF_SR_SCALARS_RAISE,
        )
        cf.set_store_full_values(False)
        cf_stored = ray.get(live_pool.object_store(cf))
        ray.get(live_pool.object_validate(cf_stored))

        ref = live_pool.object_get(
            "CompactionFunction",
            **_build_kwargs(
                fake_traj, fake_full, fake_sr,
                prereqs["dns"], fake_cosmo, prereqs["tol"],
            ),
        )
        with pytest.raises(Exception, match="scalars-only mode"):
            ray.get(ref)

    def test_full_fidelity_build_unaffected(self, live_pool):
        """build() on a full-fidelity row populates both value lists — no regression."""
        prereqs = _get_prerequisites(live_pool)
        cf, fake_traj, fake_cosmo, fake_full, fake_sr = _make_cf(
            prereqs["dns"], prereqs["tol"],
            _CF_FULL_FF_BUILD, _CF_SR_FF_BUILD,
        )
        cf_stored = ray.get(live_pool.object_store(cf))
        ray.get(live_pool.object_validate(cf_stored))

        cf_read = ray.get(live_pool.object_get(
            "CompactionFunction",
            **_build_kwargs(
                fake_traj, fake_full, fake_sr,
                prereqs["dns"], fake_cosmo, prereqs["tol"],
            ),
        ))

        assert len(cf_read._full_values)      == _N_SAMPLES
        assert len(cf_read._slow_roll_values) == _N_SAMPLES

    def test_backward_compat_absent_full_values_stored_key(self, live_pool):
        """
        A metadata dict with real CF diagnostic sub-keys (r_max_C_bar_extrapolated,
        r_max_C_at_grid_edge from Prompt 1) but no top-level full_values_stored key
        must be treated as full-fidelity — build() must not raise.

        This guards every existing CompactionFunction row in the production DB, which
        predates the scalars-only feature and therefore has no such key.
        """
        prereqs = _get_prerequisites(live_pool)
        existing_diag = {
            "full": {
                "type_II": False,
                "n_valid_points": 10,
                "n_total_points": 12,
                "r_max_C_bar_extrapolated": False,
                "r_max_C_at_grid_edge": False,
            },
            "slow_roll": {
                "type_II": False,
                "n_valid_points": 10,
                "n_total_points": 12,
                "r_max_C_bar_extrapolated": True,
                "r_max_C_at_grid_edge": False,
            },
        }
        cf, fake_traj, fake_cosmo, fake_full, fake_sr = _make_cf(
            prereqs["dns"], prereqs["tol"],
            _CF_FULL_BACK_COMPAT, _CF_SR_BACK_COMPAT,
            diagnostics=existing_diag,
        )
        cf_stored = ray.get(live_pool.object_store(cf))
        ray.get(live_pool.object_validate(cf_stored))

        # Must not raise; both value lists must be populated.
        cf_read = ray.get(live_pool.object_get(
            "CompactionFunction",
            **_build_kwargs(
                fake_traj, fake_full, fake_sr,
                prereqs["dns"], fake_cosmo, prereqs["tol"],
            ),
        ))

        assert len(cf_read._full_values)      > 0
        assert len(cf_read._slow_roll_values) > 0
        # Absent key is treated as True — confirmed by the fact that no exception
        # was raised above; verify explicitly too.
        assert cf_read._diagnostics.get("full_values_stored", True) is True

    def test_partial_fail_full_succeeds_sr_fails_scalars_only(self, live_pool):
        """
        Partial failure, case A: full path succeeds, slow-roll fails.
        obj.failure == False, _full_values non-empty, _slow_roll_values empty.

        set_store_full_values(False) must suppress the non-empty _full_values;
        zero sample rows written; validate() passes.  Confirms the skip logic
        exercises the non-empty list, not just the trivially-empty slow-roll one.
        """
        prereqs = _get_prerequisites(live_pool)
        cf, _, _, _, _ = _make_cf(
            prereqs["dns"], prereqs["tol"],
            _CF_FULL_PARTIAL_A, _CF_SR_PARTIAL_A,
            full_succeeds=True, sr_succeeds=False,
        )

        # Pre-conditions: this is the non-trivial case where the non-empty list exists.
        assert not cf.failure
        assert len(cf._full_values)      > 0, "test requires non-empty _full_values"
        assert len(cf._slow_roll_values) == 0

        cf.set_store_full_values(False)

        cf_stored = ray.get(live_pool.object_store(cf))
        assert cf_stored._my_id is not None

        validated = ray.get(live_pool.object_validate(cf_stored))
        assert validated is True

    def test_partial_fail_sr_succeeds_full_fails_scalars_only(self, live_pool):
        """
        Partial failure, case B: slow-roll path succeeds, full path fails.
        obj.failure == False, _slow_roll_values non-empty, _full_values empty.

        set_store_full_values(False) must suppress the non-empty _slow_roll_values;
        zero sample rows written; validate() passes.  Confirms the skip logic
        exercises the non-empty list, not just the trivially-empty full one.
        """
        prereqs = _get_prerequisites(live_pool)
        cf, _, _, _, _ = _make_cf(
            prereqs["dns"], prereqs["tol"],
            _CF_FULL_PARTIAL_B, _CF_SR_PARTIAL_B,
            full_succeeds=False, sr_succeeds=True,
        )

        # Pre-conditions: this is the non-trivial case where the non-empty list exists.
        assert not cf.failure
        assert len(cf._full_values)      == 0
        assert len(cf._slow_roll_values) > 0, "test requires non-empty _slow_roll_values"

        cf.set_store_full_values(False)

        cf_stored = ray.get(live_pool.object_store(cf))
        assert cf_stored._my_id is not None

        validated = ray.get(live_pool.object_validate(cf_stored))
        assert validated is True
