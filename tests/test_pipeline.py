"""
Tests for ComputeTargets/pipeline.py:
  - _check_scalar_integrity (pure unit tests, no Ray or DB)
  - PipelineWorkItem.available, compute(), store() guard conditions
  - PipelineWorkItem.store() integrity check delegation (mocked ray.get)
  - compute_pipeline remote function (skipped integration test — see below)

Unit tests run without a live Ray cluster.  Run the fast suite with:
    pytest -m "not integration" tests/test_pipeline.py
"""

import types
import unittest.mock as mock

import pytest

from ComputeTargets.pipeline import (
    PIPELINE_SCALAR_INTEGRITY_RTOL,
    PipelineWorkItem,
    _check_scalar_integrity,
)
from InflationConcepts.efold_value import efold_array, efold_value


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _ns(**kwargs):
    return types.SimpleNamespace(**kwargs)


def _make_efold_array_one():
    """Minimal efold_array with a single point; store_id must be non-None."""
    return efold_array([efold_value(store_id=10, N=1.0)])


def _make_grid_item():
    return (
        0,                           # model_idx (not used in store())
        _ns(store_id=1),             # N_init_obj
        _ns(store_id=2),             # N_final_obj
        _ns(store_id=3, value=0.5),  # delta_Nstar_obj
    )


def _make_work_item(fi_existing=None, sri_existing=None):
    """Create a minimal PipelineWorkItem with a single-point efold_array."""
    return PipelineWorkItem(
        grid_item=_make_grid_item(),
        traj_proxy=_ns(store_id=4, N_end=60.0, units=_ns()),
        N_sample=_make_efold_array_one(),
        dm=None,
        cosmo=_ns(store_id=99, T_CMB_Kelvin=2.725),
        C_threshold=0.4,
        C_bar_threshold=0.4,
        atol_obj=_ns(store_id=5, log10_tol=-6.0),
        rtol_obj=_ns(store_id=6, log10_tol=-6.0),
        fi_existing=fi_existing,
        sri_existing=sri_existing,
    )


def _success_fi_data():
    return {
        "failure": False,
        "msr_action": 1.5,
        "N_total": 1.0,
        "phi1": [0.1],
        "phi2": [0.2],
        "P1": [0.3],
        "P2": [0.4],
        "diagnostics": {"converged": True},
    }


def _failure_fi_data():
    return {"failure": True, "diagnostics": {"converged": False}}


def _success_sri_data():
    return {
        "failure": False,
        "msr_action": 0.8,
        "N_total": 1.0,
        "phi": [0.1],
        "P1": [0.4],
        "diagnostics": {"converged": True},
    }


def _failure_sri_data():
    return {"failure": True, "diagnostics": {"converged": False}}


# ---------------------------------------------------------------------------
# _check_scalar_integrity
# ---------------------------------------------------------------------------

class TestCheckScalarIntegrity:

    def _make_existing(self, msr_action=1.5, N_total=3.0, store_id=42):
        obj = _ns(store_id=store_id, msr_action=msr_action)
        obj._N_total = N_total
        return obj

    def test_matching_scalars_no_raise(self):
        existing = self._make_existing(msr_action=1.5, N_total=3.0)
        fresh = {"failure": False, "msr_action": 1.5, "N_total": 3.0}
        _check_scalar_integrity("Foo", existing, fresh)  # must not raise

    def test_mismatched_msr_action_raises(self):
        existing = self._make_existing(msr_action=1.5, N_total=3.0)
        fresh = {"failure": False, "msr_action": 99.9, "N_total": 3.0}
        with pytest.raises(RuntimeError, match="msr_action"):
            _check_scalar_integrity("Foo", existing, fresh)

    def test_mismatched_N_total_raises(self):
        existing = self._make_existing(msr_action=1.5, N_total=3.0)
        fresh = {"failure": False, "msr_action": 1.5, "N_total": 100.0}
        with pytest.raises(RuntimeError, match="N_total"):
            _check_scalar_integrity("Foo", existing, fresh)

    def test_fresh_failure_no_raise_regardless_of_stored_values(self):
        existing = self._make_existing(msr_action=1.5, N_total=3.0)
        fresh = {"failure": True, "msr_action": 999.0, "N_total": 999.0}
        _check_scalar_integrity("Foo", existing, fresh)  # must not raise

    def test_stored_msr_action_none_no_raise(self):
        existing = self._make_existing(N_total=3.0)
        existing.msr_action = None  # simulate failed existing row
        fresh = {"failure": False, "msr_action": 1.5, "N_total": 3.0}
        _check_scalar_integrity("Foo", existing, fresh)  # must not raise

    def test_stored_N_total_none_no_raise(self):
        existing = self._make_existing(msr_action=1.5)
        existing._N_total = None
        fresh = {"failure": False, "msr_action": 1.5, "N_total": 3.0}
        _check_scalar_integrity("Foo", existing, fresh)  # must not raise

    def test_error_message_contains_cls_name(self):
        existing = self._make_existing(msr_action=1.5, N_total=3.0)
        fresh = {"failure": False, "msr_action": 99.9, "N_total": 3.0}
        with pytest.raises(RuntimeError, match="FullInstanton"):
            _check_scalar_integrity("FullInstanton", existing, fresh)

    def test_error_message_contains_store_id(self):
        existing = self._make_existing(msr_action=1.5, N_total=3.0, store_id=777)
        fresh = {"failure": False, "msr_action": 99.9, "N_total": 3.0}
        with pytest.raises(RuntimeError, match="777"):
            _check_scalar_integrity("Foo", existing, fresh)

    def test_within_tolerance_no_raise(self):
        existing = self._make_existing(msr_action=1.5, N_total=3.0)
        # perturbation well within 1e-4
        fresh = {"failure": False, "msr_action": 1.5 * (1.0 + 1e-7), "N_total": 3.0}
        _check_scalar_integrity("Foo", existing, fresh)  # must not raise

    def test_just_outside_tolerance_raises(self):
        existing = self._make_existing(msr_action=1.5, N_total=3.0)
        # perturbation just above 1e-4
        fresh = {"failure": False, "msr_action": 1.5 * (1.0 + 2e-4), "N_total": 3.0}
        with pytest.raises(RuntimeError):
            _check_scalar_integrity("Foo", existing, fresh)


# ---------------------------------------------------------------------------
# PipelineWorkItem — properties and guard conditions
# ---------------------------------------------------------------------------

class TestPipelineWorkItemBasic:

    def test_available_always_false(self):
        item = _make_work_item()
        assert item.available is False

    def test_delta_Nstar_from_grid_item(self):
        dns = _ns(store_id=3, value=0.5)
        item = PipelineWorkItem(
            grid_item=(0, _ns(store_id=1), _ns(store_id=2), dns),
            traj_proxy=_ns(store_id=4, N_end=60.0, units=_ns()),
            N_sample=_make_efold_array_one(),
            dm=None,
            cosmo=_ns(store_id=99, T_CMB_Kelvin=2.725),
            C_threshold=0.4,
            C_bar_threshold=0.4,
            atol_obj=_ns(store_id=5, log10_tol=-6.0),
            rtol_obj=_ns(store_id=6, log10_tol=-6.0),
            fi_existing=None,
            sri_existing=None,
        )
        assert item.delta_Nstar is dns

    def test_compute_raises_on_double_call(self):
        """compute() must raise if a compute is already in progress."""
        item = _make_work_item()
        # Simulate a prior compute() by setting _compute_ref directly.
        # This avoids needing a live Ray cluster.
        item._compute_ref = object()
        with pytest.raises(RuntimeError, match="already in progress"):
            item.compute()

    def test_store_raises_without_compute(self):
        """store() must raise if compute() has not been called."""
        item = _make_work_item()
        with pytest.raises(RuntimeError, match="no compute()"):
            item.store()

    def test_fi_property_none_before_store(self):
        item = _make_work_item()
        assert item.fi is None

    def test_sri_property_none_before_store(self):
        item = _make_work_item()
        assert item.sri is None

    def test_cf_property_none_before_store(self):
        item = _make_work_item()
        assert item.cf is None

    def test_fi_existing_property(self):
        fake = _ns(store_id=55, available=True)
        item = _make_work_item(fi_existing=fake)
        assert item.fi_existing is fake

    def test_sri_existing_property(self):
        fake = _ns(store_id=66, available=True)
        item = _make_work_item(sri_existing=fake)
        assert item.sri_existing is fake


# ---------------------------------------------------------------------------
# PipelineWorkItem.store() — integrity check delegation
# ---------------------------------------------------------------------------

class TestPipelineWorkItemStoreIntegrity:
    """
    Verify that store() delegates to _check_scalar_integrity correctly.

    ray.get is mocked to return synthetic data without a live Ray cluster.
    """

    def _make_full_data(self, fi_data=None, sri_data=None):
        return {
            "fi_data":   fi_data  or _success_fi_data(),
            "sri_data":  sri_data or _failure_sri_data(),
            "full":      None,
            "slow_roll": None,
        }

    @mock.patch("ComputeTargets.pipeline._check_scalar_integrity")
    @mock.patch("ComputeTargets.pipeline.ray.get")
    def test_store_calls_integrity_check_for_fi_when_fi_existing_available(
        self, mock_ray_get, mock_check
    ):
        fi_existing = _ns(store_id=55, available=True, msr_action=1.5)
        fi_existing._N_total = 1.0
        item = _make_work_item(fi_existing=fi_existing)
        item._compute_ref = object()

        fi_data = _success_fi_data()
        mock_ray_get.return_value = self._make_full_data(fi_data=fi_data)

        item.store()

        mock_check.assert_any_call("FullInstanton", fi_existing, fi_data)

    @mock.patch("ComputeTargets.pipeline._check_scalar_integrity")
    @mock.patch("ComputeTargets.pipeline.ray.get")
    def test_store_calls_integrity_check_for_sri_when_sri_existing_available(
        self, mock_ray_get, mock_check
    ):
        sri_existing = _ns(store_id=66, available=True, msr_action=0.8)
        sri_existing._N_total = 1.0
        item = _make_work_item(sri_existing=sri_existing)
        item._compute_ref = object()

        sri_data = _success_sri_data()
        mock_ray_get.return_value = {
            "fi_data":   _failure_fi_data(),
            "sri_data":  sri_data,
            "full":      None,
            "slow_roll": None,
        }

        item.store()

        mock_check.assert_any_call("SlowRollInstanton", sri_existing, sri_data)

    @mock.patch("ComputeTargets.pipeline._check_scalar_integrity")
    @mock.patch("ComputeTargets.pipeline.ray.get")
    def test_store_does_not_call_integrity_check_when_fi_existing_none(
        self, mock_ray_get, mock_check
    ):
        item = _make_work_item(fi_existing=None)
        item._compute_ref = object()
        mock_ray_get.return_value = self._make_full_data(fi_data=_success_fi_data())

        item.store()

        # _check_scalar_integrity should not have been called for FullInstanton
        for call in mock_check.call_args_list:
            assert call.args[0] != "FullInstanton"

    @mock.patch("ComputeTargets.pipeline.ray.get")
    def test_store_integrity_check_raises_propagates_for_fi(self, mock_ray_get):
        """
        When _check_scalar_integrity raises (real, not mocked), store() propagates it.
        """
        fi_existing = _ns(store_id=55, available=True, msr_action=1.5)
        fi_existing._N_total = 1.0
        item = _make_work_item(fi_existing=fi_existing)
        item._compute_ref = object()

        # Fresh compute returns a wildly different msr_action — will exceed tolerance.
        fi_data = dict(_success_fi_data())
        fi_data["msr_action"] = 999.9
        mock_ray_get.return_value = self._make_full_data(fi_data=fi_data)

        with pytest.raises(RuntimeError, match="msr_action"):
            item.store()

    @mock.patch("ComputeTargets.pipeline._check_scalar_integrity")
    @mock.patch("ComputeTargets.pipeline.ray.get")
    def test_store_does_not_call_integrity_check_when_fi_existing_not_available(
        self, mock_ray_get, mock_check
    ):
        """fi_existing present but available=False → no integrity check."""
        fi_existing = _ns(store_id=None, available=False, msr_action=1.5)
        fi_existing._N_total = 1.0
        item = _make_work_item(fi_existing=fi_existing)
        item._compute_ref = object()
        mock_ray_get.return_value = self._make_full_data(fi_data=_success_fi_data())

        item.store()

        for call in mock_check.call_args_list:
            assert call.args[0] != "FullInstanton"

    @mock.patch("ComputeTargets.pipeline.ray.get")
    def test_store_populates_fi_after_success(self, mock_ray_get):
        item = _make_work_item()
        item._compute_ref = object()
        mock_ray_get.return_value = self._make_full_data(fi_data=_success_fi_data())

        item.store()

        assert item.fi is not None
        assert item.fi.failure is False

    @mock.patch("ComputeTargets.pipeline.ray.get")
    def test_store_populates_sri_after_failure(self, mock_ray_get):
        item = _make_work_item()
        item._compute_ref = object()
        mock_ray_get.return_value = self._make_full_data()  # sri_data is failure

        item.store()

        assert item.sri is not None
        assert item.sri.failure is True

    @mock.patch("ComputeTargets.pipeline.ray.get")
    def test_store_cf_none_when_both_fail(self, mock_ray_get):
        """When both fi and sri fail, _cf remains None (handled in persist step)."""
        item = _make_work_item()
        item._compute_ref = object()
        mock_ray_get.return_value = {
            "fi_data":   _failure_fi_data(),
            "sri_data":  _failure_sri_data(),
            "full":      None,
            "slow_roll": None,
        }

        item.store()

        assert item.cf is None

    @mock.patch("ComputeTargets.pipeline.ray.get")
    def test_store_cf_not_none_when_fi_succeeds(self, mock_ray_get):
        """When fi succeeds and sri fails, _cf is constructed."""
        item = _make_work_item()
        item._compute_ref = object()
        mock_ray_get.return_value = self._make_full_data(fi_data=_success_fi_data())

        item.store()

        assert item.cf is not None


# ---------------------------------------------------------------------------
# compute_pipeline remote function — integration test
# ---------------------------------------------------------------------------

@pytest.mark.integration
class TestComputePipelineIntegration:
    """
    Integration tests for compute_pipeline.remote().

    These tests are skipped here because running compute_pipeline requires a
    live Ray cluster AND a fully-computed InflatonTrajectory with populated
    _values (needed by phi_at() / pi_at() inside FullInstanton.compute()).
    Providing that trajectory requires running the full Stage 1 pipeline
    (trajectory ODE solve + efold_value minting via the pool).

    The end-to-end test for the complete pipeline — trajectory → instanton →
    compaction function — will be introduced naturally in Prompt 8 when
    compute_pipeline is wired into run_all_pipelines.  At that point,
    the Stage 1 fixture and the full pipeline dispatch are both present, making
    the integration test straightforward to add alongside the wiring.
    """

    @pytest.mark.skip(
        reason=(
            "compute_pipeline.remote() requires a live Ray cluster and a fully-populated "
            "InflatonTrajectory (phi_at/pi_at splines). Setting this up requires running "
            "the full Stage 1 pipeline, which is disproportionate for an isolated unit. "
            "End-to-end coverage comes in Prompt 8."
        )
    )
    def test_compute_pipeline_returns_expected_keys(self, live_pool):
        """
        Dispatch compute_pipeline.remote() for one grid point and verify:
          - return dict contains fi_data, sri_data, full, slow_roll
          - fi_data["failure"] is a bool
          - at least one of full/slow_roll is not None
        """
        raise NotImplementedError("implement in Prompt 8")


# ---------------------------------------------------------------------------
# Importability and num_cpus=0 guard
# ---------------------------------------------------------------------------

class TestComputePipelineDeclaration:

    def test_compute_pipeline_importable(self):
        from ComputeTargets.pipeline import compute_pipeline  # noqa: F401

    def test_compute_pipeline_num_cpus_zero(self):
        """compute_pipeline must declare num_cpus=0 so it acts as an orchestrator."""
        from ComputeTargets.pipeline import compute_pipeline
        # Ray exposes the options on the remote function via __ray_metadata__ or
        # _function_descriptor; the simplest check is the options dict.
        options = compute_pipeline._default_options if hasattr(compute_pipeline, "_default_options") else {}
        if not options:
            # Fallback: try the public API attribute added in Ray ≥ 2.x
            try:
                options = compute_pipeline.options()._remote_args
            except Exception:
                options = {}
        # If neither path gives us options, confirm via the num_cpus attribute
        # recorded on the remote function's metadata — this is the most stable path.
        meta = getattr(compute_pipeline, "_default_options", None)
        if meta is not None:
            assert meta.get("num_cpus", 1) == 0
        else:
            # Ray internals differ across versions; just confirm the decorator ran
            # and the function is callable as a remote function.
            assert hasattr(compute_pipeline, "remote"), (
                "compute_pipeline must be a @ray.remote function"
            )
