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
Regression tests for prompt 22a
(.prompts/gradient-coupled-instanton/22a-fix-degenerate-phi-end-target.md).

Prompt 22's validation (.documents/gradient-coupled-instanton/22-validation.md,
Finding 1) established that the pre-fix ``phi_end`` target in
``ComputeTargets/GradientCoupledInstanton/GradientCoupledInstanton.py``
(``traj.phi_at(N_offset + N_total)``) is an exact algebraic identity with the
value the noiseless background trajectory reaches after integrating for
``N_total`` e-folds -- making ``lambda=0`` (trivial background, zero response
fields, ``msr_action == 0``) an exact solution of the shooting BVP for every
``delta_Nstar``. The fix anchors the target to a fixed endpoint,
``traj.phi_at(traj.N_end - N_final)``, matching ``FullInstanton``'s own
convention and independent of ``delta_Nstar``.

The corrected target does not (yet) admit a converged
``GradientCoupledInstanton`` Picard solve (Finding 2, prompt 22b's concern),
so the tests below use proxies that don't require Picard convergence:

  * the production ``phi_end`` value is captured by monkeypatching
    ``solve_picard`` to fail immediately, then read from the call arguments
    -- this exercises the real production code path (line ~197) without
    needing an actual solve;
  * the ``lambda=0`` shooting residual is computed directly from the
    background trajectory (exactly what an uncoupled, unsourced phi_1 would
    reach), since that is algebraically identical to the pre-fix formula;
  * non-triviality of the corrected target is independently confirmed via
    ``FullInstanton`` (already convergent and validated) at the same
    ``(phi_init, pi_init, phi_end, N_total)``.
"""

import numpy as np
import pytest
from scipy.integrate import solve_ivp

import ComputeTargets.GradientCoupledInstanton.picard as picard_module
from ComputeTargets.FullInstanton import _compute_full_instanton
from ComputeTargets.GradientCoupledInstanton.GradientCoupledInstanton import (
    _compute_gradient_coupled_instanton,
)
from InflationConcepts.DiffusionModel import MasslessDecoupledDiffusion
from Units.Planck_units import Planck_units


# ---------------------------------------------------------------------------
# Stubs (mirroring tests/test_gradient_coupled_instanton_end_to_end.py's own)
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
    tests/test_gradient_coupled_instanton_end_to_end.py's own."""

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


_N_INIT = 5.0
_N_FINAL = 4.9
_DELTA_NSTAR_RANGE = (1.0, 1.5, 2.0, 3.0)


def _setup():
    potential = _StubPotential()
    traj = _make_dense_trajectory(potential)
    units = Planck_units()
    traj_proxy = _TrajProxyStub(traj, units)
    dm = MasslessDecoupledDiffusion()
    return potential, traj, traj_proxy, units, dm


# ---------------------------------------------------------------------------
# Production code path: phi_end must match FullInstanton's fixed-endpoint
# convention and must not depend on delta_Nstar.
# ---------------------------------------------------------------------------


def _capture_production_phi_end(monkeypatch, traj_proxy, dm, N_init, N_final, delta_Nstar):
    """Monkeypatches solve_picard to fail immediately after recording the
    phi_end it was called with -- exercises the real ~line 197 target
    computation without requiring (or waiting on) an actual Picard solve."""
    captured = {}

    def _fake_solve_picard(N_init, N_final, delta_Nstar, alpha, H_sq_nl_init, grid,
                            traj, potential, dm, atol, rtol, phi_end, **kwargs):
        captured["phi_end"] = phi_end
        return {"failure": True, "diagnostics": {}}

    monkeypatch.setattr(picard_module, "solve_picard", _fake_solve_picard)

    result = _compute_gradient_coupled_instanton._function(
        trajectory=traj_proxy,
        dm=dm,
        cosmo_T_CMB_Kelvin=2.725,
        n_collocation_points=5,
        alpha=0.05,
        N_init=N_init,
        N_final=N_final,
        delta_Nstar=delta_Nstar,
        N_sample=[],
        atol=1e-9,
        rtol=1e-9,
        store_full_values=False,
    )
    assert result["failure"] is True
    return captured["phi_end"]


def test_production_phi_end_matches_full_instanton_fixed_endpoint(monkeypatch):
    _, traj, traj_proxy, _, dm = _setup()
    expected = traj.phi_at(traj.N_end - _N_FINAL)

    for delta_Nstar in _DELTA_NSTAR_RANGE:
        phi_end = _capture_production_phi_end(
            monkeypatch, traj_proxy, dm, _N_INIT, _N_FINAL, delta_Nstar,
        )
        assert phi_end == pytest.approx(expected, rel=1e-12)


def test_production_phi_end_is_delta_Nstar_independent(monkeypatch):
    """Directly guards against the bug: the pre-fix formula
    (traj.phi_at(N_offset + N_total)) varies with delta_Nstar since N_total
    does; the fixed target must not."""
    _, _, traj_proxy, _, dm = _setup()

    values = {
        delta_Nstar: _capture_production_phi_end(
            monkeypatch, traj_proxy, dm, _N_INIT, _N_FINAL, delta_Nstar,
        )
        for delta_Nstar in _DELTA_NSTAR_RANGE
    }
    distinct = set(round(v, 12) for v in values.values())
    assert len(distinct) == 1, f"phi_end varies with delta_Nstar: {values}"


# ---------------------------------------------------------------------------
# Positive control 1: lambda=0 is no longer an exact solution of the
# shooting BVP under the corrected target (it was, exactly, under the old
# formula -- an algebraic identity, not a numerical coincidence).
# ---------------------------------------------------------------------------


def _old_buggy_phi_end(traj, N_init, N_final, delta_Nstar):
    """The pre-fix formula (GradientCoupledInstanton.py line ~197, before
    prompt 22a). Reimplemented here only as a historical reference for the
    degeneracy check below -- never call this in production code again."""
    N_offset = traj.N_end - N_init
    N_total = (N_init - N_final) + delta_Nstar
    return traj.phi_at(N_offset + N_total)


def test_old_formula_produces_exact_lambda_zero_degeneracy():
    """The pre-fix target is an exact algebraic identity with the point the
    noiseless (lambda=0) background reaches after N_total e-folds -- the
    residual is exactly zero (to floating-point precision), not merely
    small. This is the degeneracy prompt 22 Finding 1 diagnosed; it must
    never silently return."""
    _, traj, _, _, _ = _setup()

    for delta_Nstar in _DELTA_NSTAR_RANGE:
        N_offset = traj.N_end - _N_INIT
        N_total = (_N_INIT - _N_FINAL) + delta_Nstar
        background_endpoint = traj.phi_at(N_offset + N_total)
        old_target = _old_buggy_phi_end(traj, _N_INIT, _N_FINAL, delta_Nstar)
        assert background_endpoint == pytest.approx(old_target, abs=1e-12)


def test_corrected_target_breaks_lambda_zero_degeneracy():
    """Under the corrected (fixed-endpoint) target, the lambda=0 shooting
    residual |phi_1(N_total) - phi_end| is the distance between where the
    background actually lands and the fixed endpoint -- non-zero and O(the
    field excursion), not O(tolerance), across delta_Nstar in [1, 3]."""
    _, traj, _, _, _ = _setup()
    corrected_target = traj.phi_at(traj.N_end - _N_FINAL)

    for delta_Nstar in _DELTA_NSTAR_RANGE:
        N_offset = traj.N_end - _N_INIT
        N_total = (_N_INIT - _N_FINAL) + delta_Nstar
        background_endpoint = traj.phi_at(N_offset + N_total)
        residual = background_endpoint - corrected_target
        # O(tolerance) would be ~1e-9; the excess-e-fold field excursion is
        # O(0.1) or larger over this potential/trajectory -- five orders of
        # magnitude apart, so 1e-3 cleanly separates "degenerate" from "not".
        assert abs(residual) > 1.0e-3, (
            f"delta_Nstar={delta_Nstar}: residual {residual} is at the "
            f"tolerance floor -- degeneracy may have crept back in"
        )


# ---------------------------------------------------------------------------
# Positive control 2: FullInstanton (independently convergent and validated)
# returns a strictly positive, well-resolved msr_action at the same
# (phi_init, pi_init, phi_end, N_total) -- proof the corrected target admits
# a genuinely non-trivial instanton, without needing
# GradientCoupledInstanton's own Picard solve to converge (Finding 2, out of
# scope here -- prompt 22b).
# ---------------------------------------------------------------------------


def test_full_instanton_independent_nonzero_action_at_corrected_target():
    potential, traj, traj_proxy, units, dm = _setup()
    corrected_target = traj.phi_at(traj.N_end - _N_FINAL)
    N_offset = traj.N_end - _N_INIT
    phi_init = traj.phi_at(N_offset)
    pi_init = traj.pi_at(N_offset)

    for delta_Nstar in _DELTA_NSTAR_RANGE:
        N_total = (_N_INIT - _N_FINAL) + delta_Nstar
        result = _compute_full_instanton._function(
            trajectory=traj_proxy,
            dm=dm,
            phi_init=phi_init,
            pi_init=pi_init,
            phi_final=corrected_target,
            N_total=N_total,
            N_sample=list(np.linspace(0.0, N_total, 50)),
            atol=1e-9,
            rtol=1e-9,
            label=f"phi_end_target_positive_control dNstar={delta_Nstar}",
        )
        assert result["failure"] is False, f"delta_Nstar={delta_Nstar}: FullInstanton failed to converge"
        msr_action = result["msr_action"]
        assert msr_action is not None
        # Well above any plausible tolerance floor (atol/rtol here are 1e-9;
        # a genuine excess-e-folds saddle over this potential/trajectory
        # gives msr_action = O(1), so 1e-3 leaves several orders of margin).
        assert msr_action > 1.0e-3, (
            f"delta_Nstar={delta_Nstar}: msr_action={msr_action} is not "
            f"strictly positive and well-resolved"
        )
