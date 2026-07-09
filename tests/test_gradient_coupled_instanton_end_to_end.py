# (c) University of Sussex 2026
# Created by David Seery
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Tests for prompt 14 — GradientCoupledInstanton compute target and persistence.

Part B (trajectory-range guard) is a pure unit test, no Ray/datastore needed.
Everything else requires the live_pool session fixture (needs a Ray cluster
running) and is marked ``integration``, matching tests/test_scalars_only_storage.py's
own convention (excluded from the fast unit-test run via
``pytest -m "not integration"``).

The end-to-end numerical pipeline (solve_picard -> extract_zeta_profile ->
assign_scales -> noise stats -> N_sample interpolation) is exercised by calling
_compute_gradient_coupled_instanton._function(...) directly -- the same
"bypass .remote(), call the underlying function in-process" pattern already
used by tests/test_picard.py and tests/test_extraction.py for
_compute_full_instanton, to avoid the separate concern of whether a
locally-defined stub trajectory/potential class survives Ray's
cross-process pickling.
"""

import types

import numpy as np
import pytest
import ray
from scipy.integrate import solve_ivp

from ComputeTargets.GradientCoupledInstanton.GradientCoupledInstanton import (
    GradientCoupledInstanton,
    GradientCoupledInstantonValue,
    GradientCoupledInstantonProfileValue,
    _compute_gradient_coupled_instanton,
)
from CosmologyModels.params import Planck2018
from InflationConcepts.DiffusionModel import MasslessDecoupledDiffusion
from InflationConcepts.efold_value import efold_value, efold_array
from Units.Planck_units import Planck_units


# ---------------------------------------------------------------------------
# Shared stubs (mirroring tests/test_picard.py's own stub potential)
# ---------------------------------------------------------------------------


class _StubPotential:
    def __init__(self, m_sq: float = 1.3):
        self._m_sq = m_sq
        self._units = Planck_units()

    def V(self, phi):
        phi = np.asarray(phi)
        return 0.5 * self._m_sq * phi ** 2

    def dV_dphi(self, phi):
        return self._m_sq * np.asarray(phi)

    def d2V_dphi2(self, phi):
        return self._m_sq * np.ones_like(np.asarray(phi, dtype=float))

    def H_sq(self, phi, pi):
        phi = np.asarray(phi)
        pi = np.asarray(pi)
        return self.V(phi) / (3.0 - 0.5 * pi ** 2)

    def epsilon(self, phi, pi):
        pi = np.asarray(pi)
        return 0.5 * pi ** 2


def _make_dense_trajectory(potential, phi0=10.0, pi0=-0.01, atol=1e-9, rtol=1e-9):
    """A genuine noiseless-background trajectory, reaching its own true
    end of inflation (epsilon=1) via dense output -- same construction as
    tests/test_extraction.py's own _DenseTrajectory."""

    def bg_rhs(N, y):
        phi, pi = y
        return [
            pi,
            -(3.0 - potential.epsilon(phi, pi)) * pi
            - potential.dV_dphi(phi) / potential.H_sq(phi, pi),
        ]

    def event_end(N, y):
        return potential.epsilon(y[0], y[1]) - 1.0

    event_end.terminal = True
    event_end.direction = 1

    sol = solve_ivp(
        bg_rhs, (0.0, 1000.0), [phi0, pi0], method="RK45", atol=atol, rtol=rtol,
        events=event_end, dense_output=True, max_step=0.5,
    )
    assert sol.t_events[0].size > 0
    N_end = float(sol.t_events[0][0])

    class _Traj:
        def __init__(self):
            self._potential = potential
            self.N_end = N_end

        def phi_at(self, N):
            return float(sol.sol(N)[0])

        def pi_at(self, N):
            return float(sol.sol(N)[1])

    return _Traj()


class _TrajProxyStub:
    """Duck-typed InflatonTrajectoryProxy stand-in exposing exactly what
    compute()/the remote function/zeta_C_r_at_time read: .N_end, .units,
    and .get()."""

    def __init__(self, traj, units):
        self._traj = traj
        self.N_end = traj.N_end
        self.units = units

    def get(self):
        return self._traj


# ---------------------------------------------------------------------------
# Part B — trajectory-range guard (pure unit test, no Ray needed)
# ---------------------------------------------------------------------------


class _FakeFloatConcept:
    def __init__(self, v):
        self._v = v

    def __float__(self):
        return self._v


class _FakeIntConcept:
    def __init__(self, v):
        self._v = v

    def __int__(self):
        return self._v


class _FakeTolerance:
    def __init__(self, log10_tol):
        self.log10_tol = log10_tol


def _make_guard_test_object(N_end, N_init_val, N_final_val, delta_Nstar_val):
    traj_proxy = types.SimpleNamespace(N_end=N_end)
    n_sample = efold_array([efold_value(store_id=1, N=0.0)])
    return GradientCoupledInstanton(
        store_id=None,
        trajectory=traj_proxy,
        N_init=_FakeFloatConcept(N_init_val),
        N_final=_FakeFloatConcept(N_final_val),
        delta_Nstar=_FakeFloatConcept(delta_Nstar_val),
        n_collocation_points=_FakeIntConcept(5),
        alpha_regularization=_FakeFloatConcept(0.05),
        atol=_FakeTolerance(-9.0),
        rtol=_FakeTolerance(-9.0),
        cosmo=types.SimpleNamespace(T_CMB_Kelvin=2.725),
        N_sample=n_sample,
    )


def test_guard_raises_when_N_init_exceeds_trajectory_N_end():
    """N_offset = N_end - N_init < 0 -- configuration error."""
    obj = _make_guard_test_object(N_end=10.0, N_init_val=15.0, N_final_val=5.0, delta_Nstar_val=1.0)
    with pytest.raises(ValueError, match="exceeds the"):
        obj.compute()


def test_guard_raises_when_delta_Nstar_exceeds_N_final():
    """N_offset + N_total > N_end -- transition would run past end of inflation."""
    # N_init=10, N_final=2, delta_Nstar=3 > N_final=2 -- runs past the end.
    obj = _make_guard_test_object(N_end=10.0, N_init_val=10.0, N_final_val=2.0, delta_Nstar_val=3.0)
    with pytest.raises(ValueError, match="delta_Nstar"):
        obj.compute()


def test_guard_passes_for_valid_configuration():
    """A configuration that satisfies both guards should not raise ValueError
    from the guard itself -- compute() proceeds to dispatch a Ray task
    (returning an ObjectRef) instead. The dispatched task will itself fail
    later, once resolved, because the fake trajectory/cosmo stand-ins here
    are bare SimpleNamespace objects without a real .get()/potential -- that
    is an unrelated, expected failure of the *dispatched task*, not of the
    guard under test, so the ObjectRef is deliberately never resolved here."""
    obj = _make_guard_test_object(N_end=10.0, N_init_val=5.0, N_final_val=2.0, delta_Nstar_val=1.0)
    ref = obj.compute()
    assert ref is not None


# ---------------------------------------------------------------------------
# Numerical pipeline smoke test (direct ._function call, no Ray dispatch)
# ---------------------------------------------------------------------------


@pytest.mark.slow
def test_compute_gradient_coupled_instanton_end_to_end_full_values():
    """
    Small, fast scenario (short transition, trivial background-anchored
    target) exercising the whole ten-step pipeline: solve_picard converges,
    extract_zeta_profile/assign_scales produce a per-node profile, noise
    summary stats are finite, and N_sample interpolation produces
    correctly-shaped (N_sample, node) arrays.

    A genuine disable_spatial_coupling-style reduction check (as used
    throughout prompts 04-09) is not reproduced here: that flag is not part
    of GradientCoupledInstanton's public surface (deliberately -- it is an
    internal solve_picard test knob, not exposed by prompt 14's Part C
    design), so a literal reduction test would need a new pass-through
    parameter out of scope for this prompt. Instead this is a basic
    convergence/plumbing sanity check under full spatial coupling, using a
    short transition (delta_Nstar small relative to N_final) so the
    background-anchored shooting target remains reachable.
    """
    potential = _StubPotential()
    traj = _make_dense_trajectory(potential)
    units = Planck_units()
    traj_proxy = _TrajProxyStub(traj, units)

    N_init = 5.0
    N_final = 4.9
    delta_Nstar = 0.05
    N_total = (N_init - N_final) + delta_Nstar
    n_colloc = 5

    dm = MasslessDecoupledDiffusion()
    N_sample_floats = list(np.linspace(0.0, N_total, 6))

    result = _compute_gradient_coupled_instanton._function(
        trajectory=traj_proxy,
        dm=dm,
        cosmo_T_CMB_Kelvin=2.725,
        n_collocation_points=n_colloc,
        alpha=0.05,
        N_init=N_init,
        N_final=N_final,
        delta_Nstar=delta_Nstar,
        N_sample=N_sample_floats,
        atol=1e-9,
        rtol=1e-9,
        store_full_values=True,
        label="test-end-to-end",
    )

    assert result["failure"] is False
    assert result["N_total"] == pytest.approx(N_total)

    assert len(result["zeta"]) == n_colloc
    assert len(result["r_ratio"]) == n_colloc
    assert len(result["C"]) == n_colloc
    assert len(result["r_phys"]) == n_colloc
    assert all(np.isfinite(result["r_phys"]))

    # MasslessDecoupledDiffusion has D12=D22=0 identically, so the noise_mom_*
    # channel is degenerate (mirrors FullInstanton's own noise_phi2_*=None
    # convention for this same diffusion model). noise_field_* stays finite
    # since D11 (and hence the diluted D_phi) is nonzero.
    for key in ("noise_field_min", "noise_field_mean", "noise_field_max"):
        assert result[key] is not None
        assert np.isfinite(result[key])
        assert result[key] >= 0.0
    for key in ("noise_mom_min", "noise_mom_mean", "noise_mom_max"):
        assert result[key] is None

    assert len(result["N_sample"]) == len(result["phi"]) == len(result["pi"])
    assert all(len(row) == n_colloc for row in result["phi"])
    assert all(len(row) == n_colloc for row in result["rfield"])


@pytest.mark.slow
def test_compute_gradient_coupled_instanton_scalars_only_skips_interpolation():
    """store_full_values=False -- profile still computed, per-sample arrays empty."""
    potential = _StubPotential()
    traj = _make_dense_trajectory(potential)
    units = Planck_units()
    traj_proxy = _TrajProxyStub(traj, units)

    N_init = 5.0
    N_final = 4.9
    delta_Nstar = 0.05
    N_total = (N_init - N_final) + delta_Nstar

    dm = MasslessDecoupledDiffusion()

    result = _compute_gradient_coupled_instanton._function(
        trajectory=traj_proxy,
        dm=dm,
        cosmo_T_CMB_Kelvin=2.725,
        n_collocation_points=5,
        alpha=0.05,
        N_init=N_init,
        N_final=N_final,
        delta_Nstar=delta_Nstar,
        N_sample=list(np.linspace(0.0, N_total, 6)),
        atol=1e-9,
        rtol=1e-9,
        store_full_values=False,
    )

    assert result["failure"] is False
    assert result["phi"] == []
    assert result["pi"] == []
    assert result["rfield"] == []
    assert result["rmom"] == []
    assert len(result["zeta"]) == 5
    assert len(result["r_phys"]) == 5


# ---------------------------------------------------------------------------
# Integration tests -- SQL persistence (live_pool fixture)
# ---------------------------------------------------------------------------

_DNS_VAL = 0.6
_N_FINAL_VAL = 1.0
_LOG10_TOL = -6.0
_N_COLLOC_VAL = 5
_ALPHA_VAL = 0.05
_N_SAMPLES = [0.0, 0.03, 0.06, 0.09, 0.12, 0.15]

_GCI_N_INIT_FULL = 170.0
_GCI_N_INIT_SCALARS_BASIC = 171.0
_GCI_N_INIT_SCALARS_READ_SKIP = 171.1
_GCI_N_INIT_SCALARS_READ_RAISE = 171.2
_GCI_N_INIT_FULL_BUILD = 172.0
_GCI_N_INIT_FAILURE = 173.0
_GCI_N_INIT_ZETA_RECON = 174.0


def _get_prerequisites(pool):
    (dns_list, n_final_list, tol_list, n_colloc_list, alpha_list, efold_list) = ray.get([
        pool.object_get("delta_Nstar", payload_data=[{"value": _DNS_VAL}]),
        pool.object_get("N_final", payload_data=[{"value": _N_FINAL_VAL}]),
        pool.object_get("tolerance", payload_data=[{"log10_tol": _LOG10_TOL}]),
        pool.object_get("n_collocation_points", payload_data=[{"n_collocation_points": _N_COLLOC_VAL}]),
        pool.object_get("alpha_regularization", payload_data=[{"alpha": _ALPHA_VAL}]),
        pool.object_get("efold_value", payload_data=[{"N": n} for n in _N_SAMPLES]),
    ])
    diffusion = ray.get(pool.object_get("MasslessDecoupledDiffusion"))
    cosmo = ray.get(pool.object_get("CosmologicalParams", params=Planck2018()))
    return {
        "dns": dns_list[0],
        "n_final": n_final_list[0],
        "tol": tol_list[0],
        "n_colloc": n_colloc_list[0],
        "alpha": alpha_list[0],
        "efold_values": efold_list,
        "diffusion": diffusion,
        "cosmo": cosmo,
    }


def _mint_n_init(pool, value: float):
    return ray.get(pool.object_get("N_init", payload_data=[{"value": value}]))[0]


def _make_fake_traj():
    return types.SimpleNamespace(store_id=999, units=Planck_units())


def _make_gci(n_init_obj, prereqs, efold_values, failure: bool = False,
              diagnostics: dict = None, n_nodes: int = _N_COLLOC_VAL):
    fake_traj = _make_fake_traj()
    obj = GradientCoupledInstanton(
        store_id=None,
        trajectory=fake_traj,
        N_init=n_init_obj,
        N_final=prereqs["n_final"],
        delta_Nstar=prereqs["dns"],
        n_collocation_points=prereqs["n_colloc"],
        alpha_regularization=prereqs["alpha"],
        atol=prereqs["tol"],
        rtol=prereqs["tol"],
        cosmo=prereqs["cosmo"],
        N_sample=None,
        diffusion_model=prereqs["diffusion"],
    )
    obj._diagnostics = diagnostics if diagnostics is not None else {
        "compute_time": 0.1, "converged": not failure,
    }
    obj._failure = failure
    if not failure:
        obj._N_total = float(_N_SAMPLES[-1])
        obj._noise_field_min, obj._noise_field_mean, obj._noise_field_max = -0.1, 0.0, 0.1
        obj._noise_mom_min, obj._noise_mom_mean, obj._noise_mom_max = -0.2, 0.0, 0.2
        obj._values = [
            GradientCoupledInstantonValue(
                store_id=None,
                N=efold_obj,
                phi=[0.1 * (i + 1) + 0.01 * j for j in range(n_nodes)],
                pi=[0.2 * (i + 1) + 0.01 * j for j in range(n_nodes)],
                rfield=[0.3 * (i + 1) + 0.01 * j for j in range(n_nodes)],
                rmom=[0.4 * (i + 1) + 0.01 * j for j in range(n_nodes)],
            )
            for i, efold_obj in enumerate(efold_values)
        ]
        obj._profile = [
            GradientCoupledInstantonProfileValue(
                node_index=j,
                zeta=0.01 * j,
                r_ratio=1.0 - 0.1 * j,
                C=0.05 * j,
                r_phys=1.0e3 * (n_nodes - j),
            )
            for j in range(n_nodes)
        ]
    return obj, fake_traj


@pytest.mark.integration
class TestGradientCoupledInstantonPersistence:

    def test_full_fidelity_round_trip(self, live_pool):
        prereqs = _get_prerequisites(live_pool)
        n_init = _mint_n_init(live_pool, _GCI_N_INIT_FULL)
        fake_traj = _make_fake_traj()
        gci, _ = _make_gci(n_init, prereqs, prereqs["efold_values"])

        gci_stored = ray.get(live_pool.object_store(gci))
        assert gci_stored._my_id is not None

        validated = ray.get(live_pool.object_validate(gci_stored))
        assert validated is True

        gci_read = ray.get(live_pool.object_get(
            "GradientCoupledInstanton",
            trajectory=fake_traj,
            N_init=n_init,
            N_final=prereqs["n_final"],
            delta_Nstar=prereqs["dns"],
            n_collocation_points=prereqs["n_colloc"],
            alpha_regularization=prereqs["alpha"],
            atol=prereqs["tol"],
            rtol=prereqs["tol"],
            cosmo=prereqs["cosmo"],
            diffusion_model=prereqs["diffusion"],
        ))
        assert len(gci_read.values) == len(_N_SAMPLES)
        assert len(gci_read.profile) == _N_COLLOC_VAL

        # noise_field_*/noise_mom_* are dimensionless (Hawking standard
        # deviations) and round-trip with no unit conversion at all -- exact
        # equality, not just approx.
        assert gci_read.noise_field_min == gci._noise_field_min
        assert gci_read.noise_field_mean == gci._noise_field_mean
        assert gci_read.noise_field_max == gci._noise_field_max
        assert gci_read.noise_mom_min == gci._noise_mom_min
        assert gci_read.noise_mom_mean == gci._noise_mom_mean
        assert gci_read.noise_mom_max == gci._noise_mom_max

        # Round-trip numerical fidelity (Planck_units has PlanckMass=1.0, so
        # phi/pi/rfield/rmom conversions are identity; r_phys goes through a
        # genuine Mpc division/multiplication round trip).
        for orig, restored in zip(gci._values, gci_read.values):
            np.testing.assert_allclose(restored.phi, orig.phi, rtol=1e-12)
            np.testing.assert_allclose(restored.pi, orig.pi, rtol=1e-12)
            np.testing.assert_allclose(restored.rfield, orig.rfield, rtol=1e-12)
            np.testing.assert_allclose(restored.rmom, orig.rmom, rtol=1e-12)

        for orig, restored in zip(gci._profile, gci_read.profile):
            assert restored.node_index == orig.node_index
            assert restored.zeta == pytest.approx(orig.zeta, rel=1e-10)
            assert restored.r_ratio == pytest.approx(orig.r_ratio, rel=1e-10)
            assert restored.C == pytest.approx(orig.C, rel=1e-10)
            assert restored.r_phys == pytest.approx(orig.r_phys, rel=1e-8)

    def test_scalars_only_store_skips_values_but_keeps_profile(self, live_pool):
        prereqs = _get_prerequisites(live_pool)
        n_init = _mint_n_init(live_pool, _GCI_N_INIT_SCALARS_BASIC)
        gci, _ = _make_gci(n_init, prereqs, prereqs["efold_values"])
        gci.set_store_full_values(False)

        gci_stored = ray.get(live_pool.object_store(gci))
        assert gci_stored._my_id is not None

        validated = ray.get(live_pool.object_validate(gci_stored))
        assert validated is True

    def test_scalars_only_build_do_not_populate_returns_empty_values(self, live_pool):
        prereqs = _get_prerequisites(live_pool)
        n_init = _mint_n_init(live_pool, _GCI_N_INIT_SCALARS_READ_SKIP)
        fake_traj = _make_fake_traj()
        gci, _ = _make_gci(n_init, prereqs, prereqs["efold_values"])
        gci.set_store_full_values(False)
        gci_stored = ray.get(live_pool.object_store(gci))
        ray.get(live_pool.object_validate(gci_stored))

        gci_read = ray.get(live_pool.object_get(
            "GradientCoupledInstanton",
            trajectory=fake_traj,
            N_init=n_init,
            N_final=prereqs["n_final"],
            delta_Nstar=prereqs["dns"],
            n_collocation_points=prereqs["n_colloc"],
            alpha_regularization=prereqs["alpha"],
            atol=prereqs["tol"],
            rtol=prereqs["tol"],
            cosmo=prereqs["cosmo"],
            diffusion_model=prereqs["diffusion"],
            _do_not_populate=True,
        ))
        assert gci_read._diagnostics.get("full_values_stored") is False
        assert gci_read.values == []

    def test_scalars_only_build_raises_without_do_not_populate(self, live_pool):
        prereqs = _get_prerequisites(live_pool)
        n_init = _mint_n_init(live_pool, _GCI_N_INIT_SCALARS_READ_RAISE)
        fake_traj = _make_fake_traj()
        gci, _ = _make_gci(n_init, prereqs, prereqs["efold_values"])
        gci.set_store_full_values(False)
        gci_stored = ray.get(live_pool.object_store(gci))
        ray.get(live_pool.object_validate(gci_stored))

        ref = live_pool.object_get(
            "GradientCoupledInstanton",
            trajectory=fake_traj,
            N_init=n_init,
            N_final=prereqs["n_final"],
            delta_Nstar=prereqs["dns"],
            n_collocation_points=prereqs["n_colloc"],
            alpha_regularization=prereqs["alpha"],
            atol=prereqs["tol"],
            rtol=prereqs["tol"],
            cosmo=prereqs["cosmo"],
            diffusion_model=prereqs["diffusion"],
        )
        with pytest.raises(Exception, match="scalars-only mode"):
            ray.get(ref)

    def test_failure_round_trip(self, live_pool):
        prereqs = _get_prerequisites(live_pool)
        n_init = _mint_n_init(live_pool, _GCI_N_INIT_FAILURE)
        gci, _ = _make_gci(n_init, prereqs, prereqs["efold_values"], failure=True)

        gci_stored = ray.get(live_pool.object_store(gci))
        validated = ray.get(live_pool.object_validate(gci_stored))
        assert validated is True

    def test_zeta_C_r_at_time_raises_without_full_values(self, live_pool):
        prereqs = _get_prerequisites(live_pool)
        n_init = _mint_n_init(live_pool, _GCI_N_INIT_FULL_BUILD)
        gci, _ = _make_gci(n_init, prereqs, prereqs["efold_values"])
        gci.set_store_full_values(False)
        # Not persisted at all -- values simply never populated in memory.
        gci._values = []
        with pytest.raises(RuntimeError, match="store_full_values"):
            gci.zeta_C_r_at_time(prereqs["efold_values"][0])


# ---------------------------------------------------------------------------
# zeta_C_r_at_time — reconstruction consistency check (no live_pool needed;
# operates purely on an in-memory, freshly-computed object)
# ---------------------------------------------------------------------------


@pytest.mark.slow
def test_zeta_c_r_at_time_reconstructs_stored_final_row():
    """
    zeta_C_r_at_time() at the final stored N_sample point should reproduce
    the stored profile (computed via the same extract_zeta_profile/
    assign_scales pipeline at the parent's own N_total) to numerical
    precision -- a genuine consistency check between the two code paths
    (dense-grid extraction at compute time vs. reconstruction-from-stored-
    values), not merely "doesn't crash".
    """
    potential = _StubPotential()
    traj = _make_dense_trajectory(potential)
    units = Planck_units()
    traj_proxy = _TrajProxyStub(traj, units)

    N_init = 5.0
    N_final = 4.9
    delta_Nstar = 0.05
    N_total = (N_init - N_final) + delta_Nstar
    n_colloc = 5

    dm = MasslessDecoupledDiffusion()
    N_sample_floats = list(np.linspace(0.0, N_total, 6))

    result = _compute_gradient_coupled_instanton._function(
        trajectory=traj_proxy,
        dm=dm,
        cosmo_T_CMB_Kelvin=2.725,
        n_collocation_points=n_colloc,
        alpha=0.05,
        N_init=N_init,
        N_final=N_final,
        delta_Nstar=delta_Nstar,
        N_sample=N_sample_floats,
        atol=1e-9,
        rtol=1e-9,
        store_full_values=True,
    )
    assert result["failure"] is False

    efold_objs = [efold_value(store_id=i + 1, N=n) for i, n in enumerate(N_sample_floats)]
    n_sample_arr = efold_array(efold_objs)

    obj = GradientCoupledInstanton(
        store_id=42,
        trajectory=traj_proxy,
        N_init=_FakeFloatConcept(N_init),
        N_final=_FakeFloatConcept(N_final),
        delta_Nstar=_FakeFloatConcept(delta_Nstar),
        n_collocation_points=_FakeIntConcept(n_colloc),
        alpha_regularization=_FakeFloatConcept(0.05),
        atol=_FakeTolerance(-9.0),
        rtol=_FakeTolerance(-9.0),
        cosmo=types.SimpleNamespace(T_CMB_Kelvin=2.725),
        N_sample=n_sample_arr,
    )
    obj._populate_from_result(result)
    assert len(obj.values) == len(N_sample_floats)
    assert len(obj.profile) == n_colloc

    recon = obj.zeta_C_r_at_time(efold_objs[-1])
    stored_zeta = [p.zeta for p in obj.profile]
    stored_r_phys = [p.r_phys for p in obj.profile]

    np.testing.assert_allclose(recon["zeta"], stored_zeta, atol=1e-6)
    np.testing.assert_allclose(recon["r_phys"], stored_r_phys, rtol=1e-6)


def test_zeta_c_r_at_time_raises_when_not_fully_stored():
    obj = GradientCoupledInstanton(
        store_id=1,
        trajectory=types.SimpleNamespace(),
        N_init=_FakeFloatConcept(5.0),
        N_final=_FakeFloatConcept(2.0),
        delta_Nstar=_FakeFloatConcept(1.0),
        n_collocation_points=_FakeIntConcept(5),
        alpha_regularization=_FakeFloatConcept(0.05),
        atol=_FakeTolerance(-9.0),
        rtol=_FakeTolerance(-9.0),
        cosmo=types.SimpleNamespace(T_CMB_Kelvin=2.725),
        N_sample=None,
    )
    with pytest.raises(RuntimeError, match="store_full_values"):
        obj.zeta_C_r_at_time(efold_value(store_id=1, N=0.0))
