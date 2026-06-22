"""
Integration tests for scalars-only storage mode on FullInstanton and SlowRollInstanton.

Tests cover:
- Full-fidelity mode (default) is unaffected by the new flag.
- set_store_full_values(False) skips child-row writes and merges
  full_values_stored=False into diagnostics_json.
- validate() passes with zero child rows in scalars-only mode.
- build() with _do_not_populate=True returns an object with _values==[].
- build() without _do_not_populate raises RuntimeError on scalars-only rows.
- Backward compat: rows with diagnostics that lack the full_values_stored key
  are treated as full-fidelity (no raise) — guards the 25k-row production DB.
- Failed instantons: the scalars-only flag is moot and leaves behaviour unchanged.

All tests require the live_pool session fixture (needs a Ray cluster running).
They are marked ``integration`` so they are excluded from the fast unit-test run
via ``pytest -m "not integration"``.

Unique N_init values are chosen for each test scenario so tests do not interfere
with each other or with other test modules that share the session-scoped pool DB.
"""

import types

import pytest
import ray

from ComputeTargets.FullInstanton import FullInstanton, FullInstantonValue
from ComputeTargets.SlowRollInstanton import SlowRollInstanton, SlowRollInstantonValue
from Units.Planck_units import Planck_units


# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

_DNS_VAL      = 0.7     # delta_Nstar value used across all instanton tests here
_N_FINAL_VAL  = 1.0
_LOG10_TOL    = -6.0
_N_SAMPLES    = [1.0, 2.0, 3.0]  # e-fold sample points for per-value rows

# Unique N_init values — must not clash with other integration-test modules.
# Each test that independently calls object_store() needs its own N_init so
# that one_or_none() in build() never finds more than one validated row.
_FI_N_INIT_FULL              = 70.0   # full-fidelity regression
_FI_N_INIT_SCALARS_BASIC     = 71.0   # scalars-only store+validate only
_FI_N_INIT_SCALARS_READ_SKIP = 71.1   # scalars-only + build with _do_not_populate
_FI_N_INIT_SCALARS_READ_RAISE = 71.2  # scalars-only + build raises without flag
_FI_N_INIT_FULL_BUILD        = 72.0   # full-fidelity build round-trip (populate check)
_FI_N_INIT_BACK_COMPAT       = 73.0   # backward-compat: diagnostics without the flag key
_FI_N_INIT_FAIL_NOFLAG       = 74.0   # failure without scalars-only flag
_FI_N_INIT_FAIL_FLAGGED      = 75.0   # failure with scalars-only flag set

_SRI_N_INIT_FULL               = 80.0
_SRI_N_INIT_SCALARS_BASIC      = 81.0
_SRI_N_INIT_SCALARS_READ_SKIP  = 81.1
_SRI_N_INIT_SCALARS_READ_RAISE = 81.2
_SRI_N_INIT_FULL_BUILD         = 82.0
_SRI_N_INIT_BACK_COMPAT        = 83.0
_SRI_N_INIT_FAIL_NOFLAG        = 84.0
_SRI_N_INIT_FAIL_FLAGGED       = 85.0


# ---------------------------------------------------------------------------
# Fake trajectory proxy — minimal stub for factory tests (no Ray calls)
# ---------------------------------------------------------------------------

# Use types.SimpleNamespace so the object is always picklable inside Ray workers
# (a local class defined in this test file would fail to deserialise in the
# Datastore actor subprocess because 'test_scalars_only_storage' is not on the
# Python path in that process).
#
# store_id=999: SQLite does not enforce FK constraints by default, so any integer
# works.  Planck_units has PlanckMass=1.0, making all factory unit conversions
# trivial identity operations.

_FAKE_TRAJ_STORE_ID = 999


def _make_fake_traj():
    return types.SimpleNamespace(
        store_id=_FAKE_TRAJ_STORE_ID,
        units=Planck_units(),
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_prerequisites(pool):
    """Mint (or fetch) all shared prerequisite metadata objects."""
    (dns_list, n_final_list, tol_list, efold_list) = ray.get([
        pool.object_get("delta_Nstar", payload_data=[{"value": _DNS_VAL}]),
        pool.object_get("N_final",     payload_data=[{"value": _N_FINAL_VAL}]),
        pool.object_get("tolerance",   payload_data=[{"log10_tol": _LOG10_TOL}]),
        pool.object_get("efold_value", payload_data=[{"N": n} for n in _N_SAMPLES]),
    ])
    return {
        "dns":         dns_list[0],
        "n_final":     n_final_list[0],
        "tol":         tol_list[0],
        "efold_values": efold_list,     # list of efold_value objects in N order
    }


def _mint_n_init(pool, value: float):
    """Mint a single N_init object and return it."""
    return ray.get(pool.object_get("N_init", payload_data=[{"value": value}]))[0]


def _make_full_instanton(n_init_obj, n_final_obj, dns_obj, tol_obj, efold_values,
                         failure: bool = False, diagnostics: dict = None):
    """
    Construct a FullInstanton as if it had just been successfully computed.

    Sets _failure, _diagnostics, _msr_action, _N_total, and _values directly
    to bypass the actual ODE solve — the factory's store() does not care how
    these fields were populated, only that they exist.
    """
    fake_traj = _make_fake_traj()
    fi = FullInstanton(
        store_id=None,
        trajectory=fake_traj,
        N_init=n_init_obj,
        N_final=n_final_obj,
        delta_Nstar=dns_obj,
        N_sample=None,
        atol=tol_obj,
        rtol=tol_obj,
    )
    fi._diagnostics = diagnostics if diagnostics is not None else {
        "compute_time": 0.1,
        "converged": not failure,
    }
    fi._failure = failure
    if not failure:
        fi._msr_action = 1.5
        fi._N_total = float(_N_SAMPLES[-1])
        fi._values = [
            FullInstantonValue(
                store_id=None,
                N=efold_obj,
                phi1=0.1 * (i + 1),
                phi2=0.2 * (i + 1),
                P1=0.3 * (i + 1),
                P2=0.4 * (i + 1),
            )
            for i, efold_obj in enumerate(efold_values)
        ]
    return fi, fake_traj


def _make_slow_roll_instanton(n_init_obj, n_final_obj, dns_obj, tol_obj, efold_values,
                               failure: bool = False, diagnostics: dict = None):
    """
    Construct a SlowRollInstanton as if it had just been successfully computed.
    """
    fake_traj = _make_fake_traj()
    sri = SlowRollInstanton(
        store_id=None,
        trajectory=fake_traj,
        N_init=n_init_obj,
        N_final=n_final_obj,
        delta_Nstar=dns_obj,
        N_sample=None,
        atol=tol_obj,
        rtol=tol_obj,
    )
    sri._diagnostics = diagnostics if diagnostics is not None else {
        "compute_time": 0.05,
        "converged": not failure,
    }
    sri._failure = failure
    if not failure:
        sri._msr_action = 0.8
        sri._N_total = float(_N_SAMPLES[-1])
        sri._values = [
            SlowRollInstantonValue(
                store_id=None,
                N=efold_obj,
                phi=0.5 * (i + 1),
                P1=0.6 * (i + 1),
            )
            for i, efold_obj in enumerate(efold_values)
        ]
    return sri, fake_traj


# ---------------------------------------------------------------------------
# FullInstanton tests
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestScalarsOnlyFullInstanton:

    def test_full_fidelity_regression(self, live_pool):
        """Default flag stores all value rows and validates — regression guard."""
        prereqs = _get_prerequisites(live_pool)
        n_init = _mint_n_init(live_pool, _FI_N_INIT_FULL)
        fi, _ = _make_full_instanton(n_init, prereqs["n_final"], prereqs["dns"],
                                     prereqs["tol"], prereqs["efold_values"])

        fi_stored = ray.get(live_pool.object_store(fi))
        assert fi_stored._my_id is not None

        validated = ray.get(live_pool.object_validate(fi_stored))
        assert validated is True

    def test_scalars_only_store_and_validate(self, live_pool):
        """set_store_full_values(False) stores zero child rows; validate() passes."""
        prereqs = _get_prerequisites(live_pool)
        n_init = _mint_n_init(live_pool, _FI_N_INIT_SCALARS_BASIC)
        fi, _ = _make_full_instanton(n_init, prereqs["n_final"], prereqs["dns"],
                                     prereqs["tol"], prereqs["efold_values"])
        fi.set_store_full_values(False)

        fi_stored = ray.get(live_pool.object_store(fi))
        assert fi_stored._my_id is not None

        validated = ray.get(live_pool.object_validate(fi_stored))
        assert validated is True

    def test_scalars_only_diagnostics_flag_and_build_do_not_populate(self, live_pool):
        """
        Scalars-only row carries full_values_stored=False in diagnostics_json;
        reading it back with _do_not_populate=True returns _values==[].
        """
        prereqs = _get_prerequisites(live_pool)
        n_init = _mint_n_init(live_pool, _FI_N_INIT_SCALARS_READ_SKIP)
        fake_traj = _make_fake_traj()

        fi, _ = _make_full_instanton(n_init, prereqs["n_final"], prereqs["dns"],
                                     prereqs["tol"], prereqs["efold_values"])
        fi.set_store_full_values(False)
        fi_stored = ray.get(live_pool.object_store(fi))
        ray.get(live_pool.object_validate(fi_stored))

        # Read back with _do_not_populate=True — should succeed and report the flag.
        fi_read = ray.get(live_pool.object_get(
            "FullInstanton",
            trajectory=fake_traj,
            N_init=n_init,
            N_final=prereqs["n_final"],
            delta_Nstar=prereqs["dns"],
            atol=prereqs["tol"],
            rtol=prereqs["tol"],
            _do_not_populate=True,
        ))
        assert fi_read._diagnostics is not None
        assert fi_read._diagnostics.get("full_values_stored") is False
        assert fi_read._values == []

    def test_scalars_only_build_raises_without_do_not_populate(self, live_pool):
        """
        Reading a scalars-only FullInstanton without _do_not_populate raises RuntimeError.
        """
        prereqs = _get_prerequisites(live_pool)
        n_init = _mint_n_init(live_pool, _FI_N_INIT_SCALARS_READ_RAISE)
        fake_traj = _make_fake_traj()

        fi, _ = _make_full_instanton(n_init, prereqs["n_final"], prereqs["dns"],
                                     prereqs["tol"], prereqs["efold_values"])
        fi.set_store_full_values(False)
        fi_stored = ray.get(live_pool.object_store(fi))
        ray.get(live_pool.object_validate(fi_stored))

        # Must raise with a message identifying the scalars-only mode.
        ref = live_pool.object_get(
            "FullInstanton",
            trajectory=fake_traj,
            N_init=n_init,
            N_final=prereqs["n_final"],
            delta_Nstar=prereqs["dns"],
            atol=prereqs["tol"],
            rtol=prereqs["tol"],
        )
        with pytest.raises(Exception, match="scalars-only mode"):
            ray.get(ref)

    def test_full_fidelity_build_unaffected(self, live_pool):
        """build() on a full-fidelity row populates _values normally — no regression."""
        prereqs = _get_prerequisites(live_pool)
        n_init = _mint_n_init(live_pool, _FI_N_INIT_FULL_BUILD)
        fake_traj = _make_fake_traj()

        fi, _ = _make_full_instanton(n_init, prereqs["n_final"], prereqs["dns"],
                                     prereqs["tol"], prereqs["efold_values"])
        fi_stored = ray.get(live_pool.object_store(fi))
        ray.get(live_pool.object_validate(fi_stored))

        fi_read = ray.get(live_pool.object_get(
            "FullInstanton",
            trajectory=fake_traj,
            N_init=n_init,
            N_final=prereqs["n_final"],
            delta_Nstar=prereqs["dns"],
            atol=prereqs["tol"],
            rtol=prereqs["tol"],
        ))
        assert len(fi_read._values) == len(_N_SAMPLES)

    def test_backward_compat_absent_full_values_stored_key(self, live_pool):
        """
        A row whose diagnostics_json has other keys but no full_values_stored key
        must be treated as full-fidelity — no RuntimeError from build().

        This guards every row in the existing 25k-instanton production database,
        which predates the scalars-only feature and therefore has no such key.
        """
        prereqs = _get_prerequisites(live_pool)
        n_init = _mint_n_init(live_pool, _FI_N_INIT_BACK_COMPAT)
        fake_traj = _make_fake_traj()

        # Store with explicit diagnostics that have other keys but not full_values_stored.
        fi, _ = _make_full_instanton(n_init, prereqs["n_final"], prereqs["dns"],
                                     prereqs["tol"], prereqs["efold_values"],
                                     diagnostics={"some_key": 42, "another_key": "value"})
        fi_stored = ray.get(live_pool.object_store(fi))
        ray.get(live_pool.object_validate(fi_stored))

        # Must not raise; _values must be populated.
        fi_read = ray.get(live_pool.object_get(
            "FullInstanton",
            trajectory=fake_traj,
            N_init=n_init,
            N_final=prereqs["n_final"],
            delta_Nstar=prereqs["dns"],
            atol=prereqs["tol"],
            rtol=prereqs["tol"],
        ))
        assert len(fi_read._values) == len(_N_SAMPLES)
        # Absent key is treated as True — confirmed by the fact that no exception
        # was raised above; also verify explicitly.
        assert fi_read._diagnostics.get("full_values_stored", True) is True

    def test_failure_with_scalars_only_flag_behaves_identically(self, live_pool):
        """
        set_store_full_values(False) on a failed FullInstanton has no effect:
        validate() passes for both the flagged and the unflagged failure cases.
        """
        prereqs = _get_prerequisites(live_pool)
        n_init_noflag  = _mint_n_init(live_pool, _FI_N_INIT_FAIL_NOFLAG)
        n_init_flagged = _mint_n_init(live_pool, _FI_N_INIT_FAIL_FLAGGED)

        fi_noflag, _  = _make_full_instanton(n_init_noflag,  prereqs["n_final"],
                                              prereqs["dns"], prereqs["tol"],
                                              prereqs["efold_values"], failure=True)
        fi_flagged, _ = _make_full_instanton(n_init_flagged, prereqs["n_final"],
                                              prereqs["dns"], prereqs["tol"],
                                              prereqs["efold_values"], failure=True)
        fi_flagged.set_store_full_values(False)

        fi_noflag_stored  = ray.get(live_pool.object_store(fi_noflag))
        fi_flagged_stored = ray.get(live_pool.object_store(fi_flagged))

        validated_noflag  = ray.get(live_pool.object_validate(fi_noflag_stored))
        validated_flagged = ray.get(live_pool.object_validate(fi_flagged_stored))

        assert validated_noflag  is True
        assert validated_flagged is True

        # Failure rows must not carry full_values_stored=False in their diagnostics.
        for fi_s in (fi_noflag_stored, fi_flagged_stored):
            diag = fi_s.diagnostics
            if diag is not None:
                assert diag.get("full_values_stored", True) is not False, (
                    "full_values_stored should not be False in a failure row's diagnostics"
                )


# ---------------------------------------------------------------------------
# SlowRollInstanton tests — structurally identical to the FullInstanton tests
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestScalarsOnlySlowRollInstanton:

    def test_full_fidelity_regression(self, live_pool):
        """Default flag stores all value rows and validates — regression guard."""
        prereqs = _get_prerequisites(live_pool)
        n_init = _mint_n_init(live_pool, _SRI_N_INIT_FULL)
        sri, _ = _make_slow_roll_instanton(n_init, prereqs["n_final"], prereqs["dns"],
                                           prereqs["tol"], prereqs["efold_values"])

        sri_stored = ray.get(live_pool.object_store(sri))
        assert sri_stored._my_id is not None

        validated = ray.get(live_pool.object_validate(sri_stored))
        assert validated is True

    def test_scalars_only_store_and_validate(self, live_pool):
        """set_store_full_values(False) stores zero child rows; validate() passes."""
        prereqs = _get_prerequisites(live_pool)
        n_init = _mint_n_init(live_pool, _SRI_N_INIT_SCALARS_BASIC)
        sri, _ = _make_slow_roll_instanton(n_init, prereqs["n_final"], prereqs["dns"],
                                           prereqs["tol"], prereqs["efold_values"])
        sri.set_store_full_values(False)

        sri_stored = ray.get(live_pool.object_store(sri))
        assert sri_stored._my_id is not None

        validated = ray.get(live_pool.object_validate(sri_stored))
        assert validated is True

    def test_scalars_only_diagnostics_flag_and_build_do_not_populate(self, live_pool):
        """
        Scalars-only row carries full_values_stored=False in diagnostics_json;
        reading it back with _do_not_populate=True returns _values==[].
        """
        prereqs = _get_prerequisites(live_pool)
        n_init = _mint_n_init(live_pool, _SRI_N_INIT_SCALARS_READ_SKIP)
        fake_traj = _make_fake_traj()

        sri, _ = _make_slow_roll_instanton(n_init, prereqs["n_final"], prereqs["dns"],
                                           prereqs["tol"], prereqs["efold_values"])
        sri.set_store_full_values(False)
        sri_stored = ray.get(live_pool.object_store(sri))
        ray.get(live_pool.object_validate(sri_stored))

        sri_read = ray.get(live_pool.object_get(
            "SlowRollInstanton",
            trajectory=fake_traj,
            N_init=n_init,
            N_final=prereqs["n_final"],
            delta_Nstar=prereqs["dns"],
            atol=prereqs["tol"],
            rtol=prereqs["tol"],
            _do_not_populate=True,
        ))
        assert sri_read._diagnostics is not None
        assert sri_read._diagnostics.get("full_values_stored") is False
        assert sri_read._values == []

    def test_scalars_only_build_raises_without_do_not_populate(self, live_pool):
        """
        Reading a scalars-only SlowRollInstanton without _do_not_populate raises RuntimeError.
        """
        prereqs = _get_prerequisites(live_pool)
        n_init = _mint_n_init(live_pool, _SRI_N_INIT_SCALARS_READ_RAISE)
        fake_traj = _make_fake_traj()

        sri, _ = _make_slow_roll_instanton(n_init, prereqs["n_final"], prereqs["dns"],
                                           prereqs["tol"], prereqs["efold_values"])
        sri.set_store_full_values(False)
        sri_stored = ray.get(live_pool.object_store(sri))
        ray.get(live_pool.object_validate(sri_stored))

        ref = live_pool.object_get(
            "SlowRollInstanton",
            trajectory=fake_traj,
            N_init=n_init,
            N_final=prereqs["n_final"],
            delta_Nstar=prereqs["dns"],
            atol=prereqs["tol"],
            rtol=prereqs["tol"],
        )
        with pytest.raises(Exception, match="scalars-only mode"):
            ray.get(ref)

    def test_full_fidelity_build_unaffected(self, live_pool):
        """build() on a full-fidelity SlowRollInstanton populates _values normally."""
        prereqs = _get_prerequisites(live_pool)
        n_init = _mint_n_init(live_pool, _SRI_N_INIT_FULL_BUILD)
        fake_traj = _make_fake_traj()

        sri, _ = _make_slow_roll_instanton(n_init, prereqs["n_final"], prereqs["dns"],
                                           prereqs["tol"], prereqs["efold_values"])
        sri_stored = ray.get(live_pool.object_store(sri))
        ray.get(live_pool.object_validate(sri_stored))

        sri_read = ray.get(live_pool.object_get(
            "SlowRollInstanton",
            trajectory=fake_traj,
            N_init=n_init,
            N_final=prereqs["n_final"],
            delta_Nstar=prereqs["dns"],
            atol=prereqs["tol"],
            rtol=prereqs["tol"],
        ))
        assert len(sri_read._values) == len(_N_SAMPLES)

    def test_backward_compat_absent_full_values_stored_key(self, live_pool):
        """
        diagnostics_json with other keys but no full_values_stored is treated as
        full-fidelity; build() must not raise.
        """
        prereqs = _get_prerequisites(live_pool)
        n_init = _mint_n_init(live_pool, _SRI_N_INIT_BACK_COMPAT)
        fake_traj = _make_fake_traj()

        sri, _ = _make_slow_roll_instanton(n_init, prereqs["n_final"], prereqs["dns"],
                                           prereqs["tol"], prereqs["efold_values"],
                                           diagnostics={"some_key": 42, "another_key": "value"})
        sri_stored = ray.get(live_pool.object_store(sri))
        ray.get(live_pool.object_validate(sri_stored))

        sri_read = ray.get(live_pool.object_get(
            "SlowRollInstanton",
            trajectory=fake_traj,
            N_init=n_init,
            N_final=prereqs["n_final"],
            delta_Nstar=prereqs["dns"],
            atol=prereqs["tol"],
            rtol=prereqs["tol"],
        ))
        assert len(sri_read._values) == len(_N_SAMPLES)
        assert sri_read._diagnostics.get("full_values_stored", True) is True

    def test_failure_with_scalars_only_flag_behaves_identically(self, live_pool):
        """
        set_store_full_values(False) on a failed SlowRollInstanton has no effect:
        validate() passes for both the flagged and the unflagged failure cases.
        """
        prereqs = _get_prerequisites(live_pool)
        n_init_noflag  = _mint_n_init(live_pool, _SRI_N_INIT_FAIL_NOFLAG)
        n_init_flagged = _mint_n_init(live_pool, _SRI_N_INIT_FAIL_FLAGGED)

        sri_noflag, _  = _make_slow_roll_instanton(n_init_noflag,  prereqs["n_final"],
                                                    prereqs["dns"], prereqs["tol"],
                                                    prereqs["efold_values"], failure=True)
        sri_flagged, _ = _make_slow_roll_instanton(n_init_flagged, prereqs["n_final"],
                                                    prereqs["dns"], prereqs["tol"],
                                                    prereqs["efold_values"], failure=True)
        sri_flagged.set_store_full_values(False)

        sri_noflag_stored  = ray.get(live_pool.object_store(sri_noflag))
        sri_flagged_stored = ray.get(live_pool.object_store(sri_flagged))

        validated_noflag  = ray.get(live_pool.object_validate(sri_noflag_stored))
        validated_flagged = ray.get(live_pool.object_validate(sri_flagged_stored))

        assert validated_noflag  is True
        assert validated_flagged is True

        # Failure rows must not carry full_values_stored=False in their diagnostics.
        for sri_s in (sri_noflag_stored, sri_flagged_stored):
            diag = sri_s.diagnostics
            if diag is not None:
                assert diag.get("full_values_stored", True) is not False, (
                    "full_values_stored should not be False in a failure row's diagnostics"
                )
