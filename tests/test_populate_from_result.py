"""
Unit tests for _populate_from_result on FullInstanton, SlowRollInstanton,
and CompactionFunction.

These are pure unit tests — no Ray cluster or database required. They verify
that _populate_from_result sets the correct in-memory state from a synthetic
result dict, producing identical results to what store() would produce from the
same dict.
"""
import types

import pytest

from ComputeTargets.CompactionFunction import CompactionFunction, CompactionFunctionValue
from ComputeTargets.FullInstanton import FullInstanton, FullInstantonValue
from ComputeTargets.SlowRollInstanton import SlowRollInstanton, SlowRollInstantonValue
from InflationConcepts.efold_value import efold_array, efold_value


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_N_VALUES = [1.0, 2.0, 3.0]


def _ns(**kwargs):
    return types.SimpleNamespace(**kwargs)


def _make_efold_array(N_values):
    return efold_array(
        [efold_value(store_id=i + 1, N=float(n)) for i, n in enumerate(N_values)]
    )


def _make_full_instanton():
    fi = FullInstanton(
        store_id=None,
        trajectory=_ns(store_id=1),
        N_init=_ns(store_id=2),
        N_final=_ns(store_id=3),
        delta_Nstar=_ns(store_id=4),
        N_sample=None,
        atol=_ns(store_id=5),
        rtol=_ns(store_id=6),
    )
    fi._N_sample = _make_efold_array(_N_VALUES)
    return fi


def _make_slow_roll_instanton():
    sri = SlowRollInstanton(
        store_id=None,
        trajectory=_ns(store_id=1),
        N_init=_ns(store_id=2),
        N_final=_ns(store_id=3),
        delta_Nstar=_ns(store_id=4),
        N_sample=None,
        atol=_ns(store_id=5),
        rtol=_ns(store_id=6),
    )
    sri._N_sample = _make_efold_array(_N_VALUES)
    return sri


def _make_compaction_function():
    return CompactionFunction(
        store_id=None,
        full_instanton=_ns(store_id=10, available=True),
        slow_roll_instanton=None,
        trajectory=_ns(store_id=1),
        cosmo=_ns(store_id=2),
        delta_Nstar=_ns(store_id=3),
    )


_FI_SUCCESS_DATA = {
    "failure": False,
    "diagnostics": {"converged": True, "iters": 5},
    "msr_action": 1.5,
    "N_total": 3.0,
    "phi1": [0.1, 0.2, 0.3],
    "phi2": [0.4, 0.5, 0.6],
    "P1": [0.7, 0.8, 0.9],
    "P2": [1.0, 1.1, 1.2],
}

_FI_FAILURE_DATA = {
    "failure": True,
    "diagnostics": {"converged": False, "iters": 2},
}

_SRI_SUCCESS_DATA = {
    "failure": False,
    "diagnostics": {"converged": True, "iters": 3},
    "msr_action": 0.8,
    "N_total": 3.0,
    "phi": [0.1, 0.2, 0.3],
    "P1": [0.4, 0.5, 0.6],
}

_SRI_FAILURE_DATA = {
    "failure": True,
    "diagnostics": {"converged": False},
}


def _cf_branch_success():
    return {
        "failure": False,
        "diagnostics": {"ok": True},
        "r": [1.0, 2.0, 3.0],
        "zeta": [0.1, 0.2, 0.3],
        "C": [0.05, 0.10, 0.15],
        "C_bar": [0.04, 0.09, 0.14],
        "r_max_C": 2.5,
        "r_max_C_bar": 2.4,
        "M_C": 1e15,
        "M_C_bar": 1e14,
        "C_max": 0.15,
        "C_bar_max": 0.14,
        "V_end_downflow": 1e-10,
        "N_end_downflow": 2.9,
    }


def _cf_branch_failure():
    return {"failure": True, "diagnostics": {"ok": False}}


# ---------------------------------------------------------------------------
# FullInstanton._populate_from_result
# ---------------------------------------------------------------------------

class TestFullInstantonPopulateFromResult:

    def test_success_sets_values(self):
        fi = _make_full_instanton()
        fi._populate_from_result(_FI_SUCCESS_DATA)

        assert fi._failure is False
        assert fi._msr_action == pytest.approx(1.5)
        assert fi._N_total == pytest.approx(3.0)
        assert fi._diagnostics == {"converged": True, "iters": 5}
        assert len(fi._values) == len(_N_VALUES)

    def test_success_values_correct(self):
        fi = _make_full_instanton()
        fi._populate_from_result(_FI_SUCCESS_DATA)

        for i, v in enumerate(fi._values):
            assert isinstance(v, FullInstantonValue)
            assert v.phi1 == pytest.approx(_FI_SUCCESS_DATA["phi1"][i])
            assert v.phi2 == pytest.approx(_FI_SUCCESS_DATA["phi2"][i])
            assert v.P1 == pytest.approx(_FI_SUCCESS_DATA["P1"][i])
            assert v.P2 == pytest.approx(_FI_SUCCESS_DATA["P2"][i])
            assert v.N.N == pytest.approx(_N_VALUES[i])

    def test_failure_sets_empty_values(self):
        fi = _make_full_instanton()
        fi._populate_from_result(_FI_FAILURE_DATA)

        assert fi._failure is True
        assert fi._values == []
        assert fi._diagnostics == {"converged": False, "iters": 2}

    def test_failure_does_not_set_msr_action(self):
        fi = _make_full_instanton()
        fi._populate_from_result(_FI_FAILURE_DATA)

        assert fi._msr_action is None

    def test_no_diagnostics_key(self):
        fi = _make_full_instanton()
        data = dict(_FI_SUCCESS_DATA)
        del data["diagnostics"]
        fi._populate_from_result(data)

        assert fi._diagnostics is None
        assert fi._failure is False


# ---------------------------------------------------------------------------
# SlowRollInstanton._populate_from_result
# ---------------------------------------------------------------------------

class TestSlowRollInstantonPopulateFromResult:

    def test_success_sets_values(self):
        sri = _make_slow_roll_instanton()
        sri._populate_from_result(_SRI_SUCCESS_DATA)

        assert sri._failure is False
        assert sri._msr_action == pytest.approx(0.8)
        assert sri._N_total == pytest.approx(3.0)
        assert sri._diagnostics == {"converged": True, "iters": 3}
        assert len(sri._values) == len(_N_VALUES)

    def test_success_values_correct(self):
        sri = _make_slow_roll_instanton()
        sri._populate_from_result(_SRI_SUCCESS_DATA)

        for i, v in enumerate(sri._values):
            assert isinstance(v, SlowRollInstantonValue)
            assert v.phi == pytest.approx(_SRI_SUCCESS_DATA["phi"][i])
            assert v.P1 == pytest.approx(_SRI_SUCCESS_DATA["P1"][i])
            assert v.N.N == pytest.approx(_N_VALUES[i])

    def test_failure_sets_empty_values(self):
        sri = _make_slow_roll_instanton()
        sri._populate_from_result(_SRI_FAILURE_DATA)

        assert sri._failure is True
        assert sri._values == []
        assert sri._diagnostics == {"converged": False}

    def test_failure_does_not_set_msr_action(self):
        sri = _make_slow_roll_instanton()
        sri._populate_from_result(_SRI_FAILURE_DATA)

        assert sri._msr_action is None

    def test_no_diagnostics_key(self):
        sri = _make_slow_roll_instanton()
        data = dict(_SRI_SUCCESS_DATA)
        del data["diagnostics"]
        sri._populate_from_result(data)

        assert sri._diagnostics is None
        assert sri._failure is False


# ---------------------------------------------------------------------------
# CompactionFunction._populate_from_result
# ---------------------------------------------------------------------------

class TestCompactionFunctionPopulateFromResult:

    def test_both_failed_sets_failure(self):
        cf = _make_compaction_function()
        cf._populate_from_result({"full": _cf_branch_failure(), "slow_roll": _cf_branch_failure()})

        assert cf._failure is True

    def test_both_none_sets_failure(self):
        cf = _make_compaction_function()
        cf._populate_from_result({"full": None, "slow_roll": None})

        assert cf._failure is True

    def test_both_failed_diagnostics(self):
        cf = _make_compaction_function()
        cf._populate_from_result({"full": _cf_branch_failure(), "slow_roll": _cf_branch_failure()})

        assert cf._diagnostics["full"] == {"ok": False}
        assert cf._diagnostics["slow_roll"] == {"ok": False}

    def test_both_succeeded(self):
        cf = _make_compaction_function()
        cf._populate_from_result({"full": _cf_branch_success(), "slow_roll": _cf_branch_success()})

        assert cf._failure is False
        assert len(cf._full_values) == 3
        assert len(cf._slow_roll_values) == 3

    def test_both_succeeded_scalar_attrs(self):
        cf = _make_compaction_function()
        branch = _cf_branch_success()
        cf._populate_from_result({"full": branch, "slow_roll": branch})

        assert cf._r_max_C_full == pytest.approx(2.5)
        assert cf._r_max_C_bar_full == pytest.approx(2.4)
        assert cf._C_peak_full == pytest.approx(0.15)
        assert cf._C_bar_peak_full == pytest.approx(0.14)
        assert cf._V_end_downflow_full == pytest.approx(1e-10)
        assert cf._N_end_downflow_full == pytest.approx(2.9)
        assert cf._r_max_C_slow_roll == pytest.approx(2.5)
        assert cf._C_peak_slow_roll == pytest.approx(0.15)

    def test_full_succeeds_slow_roll_fails(self):
        cf = _make_compaction_function()
        cf._populate_from_result({"full": _cf_branch_success(), "slow_roll": _cf_branch_failure()})

        assert cf._failure is False
        assert len(cf._full_values) == 3
        assert cf._slow_roll_result is None

    def test_full_fails_slow_roll_succeeds(self):
        cf = _make_compaction_function()
        cf._populate_from_result({"full": _cf_branch_failure(), "slow_roll": _cf_branch_success()})

        assert cf._failure is False
        assert cf._full_result is None
        assert len(cf._slow_roll_values) == 3

    def test_value_objects_correct(self):
        cf = _make_compaction_function()
        branch = _cf_branch_success()
        cf._populate_from_result({"full": branch, "slow_roll": None})

        for i, v in enumerate(cf._full_values):
            assert isinstance(v, CompactionFunctionValue)
            assert v.r == pytest.approx(branch["r"][i])
            assert v.zeta == pytest.approx(branch["zeta"][i])
            assert v.C == pytest.approx(branch["C"][i])
            assert v.C_bar == pytest.approx(branch["C_bar"][i])

    def test_cosmo_store_id_not_set(self):
        """_populate_from_result must not touch _cosmo_store_id."""
        cf = _make_compaction_function()
        assert not hasattr(cf, "_cosmo_store_id")
        cf._populate_from_result({"full": _cf_branch_success(), "slow_roll": None})
        assert not hasattr(cf, "_cosmo_store_id")
