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
Tests for prompt 17 Part B -- instrument_stiffness on
_compute_gradient_coupled_instanton / solve_picard.

Stubs mirror tests/test_gradient_coupled_instanton_end_to_end.py's own
_StubPotential/_make_dense_trajectory/_TrajProxyStub (duplicated here rather
than imported, matching that file's own "mirrors tests/test_picard.py's own
stub potential" convention of a small amount of duplication per test file
rather than a shared fixture module).
"""

import numpy as np
import pytest
from scipy.integrate import solve_ivp

from ComputeTargets.GradientCoupledInstanton.GradientCoupledInstanton import (
    _compute_gradient_coupled_instanton,
)
from InflationConcepts.DiffusionModel import MasslessDecoupledDiffusion
from Units.Planck_units import Planck_units


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
    def __init__(self, traj, units):
        self._traj = traj
        self.N_end = traj.N_end
        self.units = units

    def get(self):
        return self._traj


def _run(instrument_stiffness: bool) -> dict:
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

    return _compute_gradient_coupled_instanton._function(
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
        instrument_stiffness=instrument_stiffness,
        label="test-stiffness-instrumentation",
    )


_RK45_KEYS = (
    "rk45_forward_total_steps", "rk45_forward_accepted_steps", "rk45_forward_rejected_steps",
    "rk45_forward_min_step", "rk45_forward_max_step", "rk45_forward_steps_per_efold",
    "rk45_backward_total_steps", "rk45_backward_accepted_steps", "rk45_backward_rejected_steps",
    "rk45_backward_min_step", "rk45_backward_max_step", "rk45_backward_steps_per_efold",
)
_WALLCLOCK_KEYS = (
    "picard_sweep_wallclock_min", "picard_sweep_wallclock_mean", "picard_sweep_wallclock_max",
)


@pytest.mark.xfail(
    reason=(
        "prompt 22a fixed phi_end to FullInstanton's delta_Nstar-independent "
        "target (.prompts/gradient-coupled-instanton/22a-fix-degenerate-phi-end-target.md); "
        "per prompt 22's Finding 2 (.documents/gradient-coupled-instanton/22-validation.md), "
        "the theta=1 lagged-pi_core Picard closure does not converge once "
        "genuine coupling is present, even for this scenario's small "
        "delta_Nstar. Remediating the closure is prompt 22b's job; remove "
        "this xfail once that lands."
    ),
    strict=True,
)
def test_instrument_stiffness_false_gives_bitwise_identical_physics():
    """The key correctness property of the switch: instrument_stiffness must
    gate measurement overhead only, never the physics result."""
    result_true = _run(instrument_stiffness=True)
    result_false = _run(instrument_stiffness=False)

    assert result_true["failure"] is False
    assert result_false["failure"] is False

    assert result_true["msr_action"] == result_false["msr_action"]
    assert result_true["zeta"] == result_false["zeta"]
    assert result_true["r_ratio"] == result_false["r_ratio"]
    assert result_true["C"] == result_false["C"]
    assert result_true["r_phys"] == result_false["r_phys"]
    assert result_true["phi"] == result_false["phi"]
    assert result_true["pi"] == result_false["pi"]
    assert result_true["rfield"] == result_false["rfield"]
    assert result_true["rmom"] == result_false["rmom"]
    assert result_true["N_total"] == result_false["N_total"]
    assert result_true["N_sample"] == result_false["N_sample"]
    for key in ("noise_field_min", "noise_field_mean", "noise_field_max",
                "noise_mom_min", "noise_mom_mean", "noise_mom_max"):
        assert result_true[key] == result_false[key]


def test_instrument_stiffness_false_omits_diagnostics_keys():
    result = _run(instrument_stiffness=False)
    diagnostics = result["diagnostics"]
    for key in _RK45_KEYS + _WALLCLOCK_KEYS:
        assert key not in diagnostics


def test_instrument_stiffness_true_populates_plausible_diagnostics():
    result = _run(instrument_stiffness=True)
    diagnostics = result["diagnostics"]

    for key in _RK45_KEYS + _WALLCLOCK_KEYS:
        assert key in diagnostics
        assert diagnostics[key] is not None

    for label in ("forward", "backward"):
        assert diagnostics[f"rk45_{label}_total_steps"] > 0
        assert diagnostics[f"rk45_{label}_accepted_steps"] > 0
        assert diagnostics[f"rk45_{label}_rejected_steps"] >= 0
        assert (
            diagnostics[f"rk45_{label}_accepted_steps"]
            + diagnostics[f"rk45_{label}_rejected_steps"]
            == diagnostics[f"rk45_{label}_total_steps"]
        )
        assert diagnostics[f"rk45_{label}_min_step"] <= diagnostics[f"rk45_{label}_max_step"]
        assert diagnostics[f"rk45_{label}_steps_per_efold"] > 0

    assert (
        diagnostics["picard_sweep_wallclock_min"]
        <= diagnostics["picard_sweep_wallclock_mean"]
        <= diagnostics["picard_sweep_wallclock_max"]
    )
    assert diagnostics["picard_sweep_wallclock_min"] > 0.0


@pytest.mark.xfail(
    reason=(
        "prompt 22a fixed phi_end to FullInstanton's delta_Nstar-independent "
        "target; per prompt 22's Finding 2, the theta=1 lagged-pi_core Picard "
        "closure does not converge once genuine coupling is present, even for "
        "this scenario's small delta_Nstar. Remediating the closure is prompt "
        "22b's job; remove this xfail once that lands."
    ),
    strict=True,
)
def test_instrument_stiffness_defaults_to_true():
    """Default is True 'for now' per prompt 17 Part B -- omitting the kwarg
    entirely should populate the same diagnostics keys as passing True
    explicitly."""
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
        store_full_values=True,
    )
    assert result["failure"] is False
    for key in _RK45_KEYS:
        assert key in result["diagnostics"]
