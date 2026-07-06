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
Unit tests for the MSR saddle-point action,
ComputeTargets/GradientCoupledInstanton/msr_action.py (prompt 15, Part B).
"""

import numpy as np
import pytest
from scipy.integrate import solve_ivp

from ComputeTargets.FullInstanton import _compute_full_instanton
from ComputeTargets.GradientCoupledInstanton.forward_rhs import unpack_state
from ComputeTargets.GradientCoupledInstanton.msr_action import (
    y_quadrature,
    compute_msr_action,
)
from ComputeTargets.GradientCoupledInstanton.picard import solve_picard, N_GRID_SIZE
from ComputeTargets.GradientCoupledInstanton.response_rhs import unpack_response_state
from InflationConcepts.DiffusionModel import MasslessDecoupledDiffusion
from Interpolation.spline_wrapper import SplineWrapper
from Numerics.LGLCollocation import LGLCollocationGrid


# ---------------------------------------------------------------------------
# Stubs -- same pattern as tests/test_picard.py's own reduction-limit fixtures
# ---------------------------------------------------------------------------


class _StubPotential:
    """Standalone duck-typed canonical-inflation potential (Mp = 1), matching
    AbstractPotential's own H_sq/epsilon formulas -- the same stub used
    throughout tests/test_picard.py, tests/test_forward_rhs.py, etc."""

    def __init__(self, m_sq: float = 1.3):
        self._m_sq = m_sq

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


class _BackgroundTrackingTrajectory:
    """Duck-typed trajectory stub tracing out the noiseless background ODE
    over [0.0, N_total] -- identical construction to
    tests/test_picard.py's own fixture of the same name."""

    def __init__(self, potential, phi_init, pi_init, N_total, atol, rtol, N_end):
        def bg_rhs(N, y):
            phi, pi = y
            return [
                pi,
                -(3.0 - potential.epsilon(phi, pi)) * pi
                - potential.dV_dphi(phi) / potential.H_sq(phi, pi),
            ]

        N_grid = np.linspace(0.0, N_total, 400)
        sol = solve_ivp(
            bg_rhs, (0.0, N_total), [phi_init, pi_init],
            method="RK45", t_eval=N_grid, atol=atol, rtol=rtol,
        )
        assert sol.success

        self._phi_spline = SplineWrapper(N_grid, sol.y[0], k=3)
        self._pi_spline = SplineWrapper(N_grid, sol.y[1], k=3)
        self._N_end = N_end

    @property
    def N_end(self) -> float:
        return self._N_end

    def phi_at(self, N: float) -> float:
        return float(self._phi_spline(N))

    def pi_at(self, N: float) -> float:
        return float(self._pi_spline(N))


class _PotentialHolder:
    """Duck-typed stand-in for InflatonTrajectory, exposing only ._potential."""

    def __init__(self, potential):
        self._potential = potential


class _TrajectoryProxyStub:
    """Duck-typed stand-in for InflatonTrajectoryProxy: _compute_full_instanton
    only ever calls trajectory.get()._potential."""

    def __init__(self, potential):
        self._holder = _PotentialHolder(potential)

    def get(self):
        return self._holder


# ---------------------------------------------------------------------------
# y_quadrature -- isolated quadrature-contraction check, independent of any
# physics input, against a synthetic integrand with a known closed-form
# y-integral: f(y) = 1, so int_{-1}^1 mu(y,N) dy = int e^{-a y} dy with
# a = 1.5*delta_s_N, closed form 2*sinh(a)/a.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("n_collocation_points", [9, 13, 17])
def test_y_quadrature_matches_closed_form_constant_integrand(n_collocation_points):
    grid = LGLCollocationGrid(n_collocation_points)
    delta_s_N = 1.3
    f_nodes = np.ones(n_collocation_points)

    result = y_quadrature(f_nodes, grid, delta_s_N)

    a = 1.5 * delta_s_N
    expected = 2.0 * np.sinh(a) / a

    assert result == pytest.approx(expected, rel=1e-10)


# ---------------------------------------------------------------------------
# Reduction-limit test -- trivial zero-response scenario, matching
# tests/test_picard.py's own test_solve_picard_reduction_limit_matches_full_instanton
# construction exactly (phi_end pinned to the background's own endpoint, so
# lambda=0 and rfield=rmom=0 identically throughout). Both GradientCoupled-
# Instanton's and FullInstanton's own msr_action are therefore exactly zero
# for this configuration -- an exact (not approximate) check, settled with
# the user: a genuinely nonzero-response scenario does not reduce exactly to
# FullInstanton, because the shell-dilution factor n_count(y=+1,N) =
# 1.5*Delta_s(N) is not pinned to 1 and evolves with N, so this trivial
# configuration is the correct scope for an *exact* reduction-limit check.
# ---------------------------------------------------------------------------


def test_msr_action_reduction_limit_matches_full_instanton_trivial_zero_response():
    potential = _StubPotential()
    diffusion_model = MasslessDecoupledDiffusion()

    N_init = 5.0
    N_final = 2.0
    delta_Nstar = 1.0
    N_total = (N_init - N_final) + delta_Nstar

    phi_init = 10.0
    pi_init = -0.01
    atol = 1.0e-9
    rtol = 1.0e-9

    trajectory = _BackgroundTrackingTrajectory(
        potential, phi_init, pi_init, N_total, atol, rtol, N_end=N_init
    )
    phi_end = trajectory.phi_at(N_total)  # trivial -- gives lambda=0, rfield=rmom=0

    alpha = 0.05
    H_sq_nl_init = potential.H_sq(phi_init, pi_init)
    grid = LGLCollocationGrid(5)

    result = solve_picard(
        N_init, N_final, delta_Nstar, alpha, H_sq_nl_init, grid,
        trajectory, potential, diffusion_model, atol, rtol, phi_end,
        disable_spatial_coupling=True,
    )
    assert result["failure"] is False
    assert result["diagnostics"]["converged"] is True

    N_grid = np.asarray(result["N_grid"])
    phi_grid = np.asarray(result["phi_grid"])
    pi_grid = np.asarray(result["pi_grid"])
    rfield_grid = np.asarray(result["rfield_grid"])
    rmom_grid = np.asarray(result["rmom_grid"])

    # Confirm this is genuinely the trivial (zero-response) configuration,
    # not merely a numerically-small one.
    assert np.all(rfield_grid == 0.0)
    assert np.all(rmom_grid == 0.0)

    gci_msr_action = compute_msr_action(
        N_grid, phi_grid, pi_grid, rfield_grid, rmom_grid, grid, potential,
        diffusion_model, H_sq_nl_init, alpha,
    )

    fi_data = _compute_full_instanton._function(
        trajectory=_TrajectoryProxyStub(potential),
        dm=diffusion_model,
        phi_init=phi_init,
        pi_init=pi_init,
        phi_final=phi_end,
        N_total=N_total,
        N_sample=N_grid.tolist(),
        atol=atol,
        rtol=rtol,
    )
    assert fi_data["failure"] is False

    assert gci_msr_action == pytest.approx(0.0, abs=1.0e-12)
    assert fi_data["msr_action"] == pytest.approx(0.0, abs=1.0e-12)
    assert gci_msr_action == pytest.approx(fi_data["msr_action"], abs=1.0e-12)


# ---------------------------------------------------------------------------
# Empirical N-quadrature convergence diagnostic -- genuinely nonzero-response
# scenario (phi_end displaced off the background, forcing a nonzero shooting
# parameter and hence nonzero rfield/rmom), resampled at increasing
# resolution via the dense-output solutions solve_picard already computed
# (no re-solving). Diagnostic only -- reports the observed convergence rate
# rather than asserting a specific tight tolerance chosen in advance.
# ---------------------------------------------------------------------------


def test_msr_action_convergence_diagnostic_shrinks_with_finer_N_resampling():
    potential = _StubPotential()
    diffusion_model = MasslessDecoupledDiffusion()

    N_init = 5.0
    N_final = 2.0
    delta_Nstar = 1.0
    N_total = (N_init - N_final) + delta_Nstar

    phi_init = 10.0
    pi_init = -0.01
    atol = 1.0e-9
    rtol = 1.0e-9

    trajectory = _BackgroundTrackingTrajectory(
        potential, phi_init, pi_init, N_total, atol, rtol, N_end=N_init
    )
    # Displaced off the background's own endpoint -- a genuine, nonzero
    # shooting parameter (unlike the reduction-limit test above), so rfield/
    # rmom are nonzero and the quadratic-form machinery is genuinely
    # exercised, not trivially zero.
    phi_end = trajectory.phi_at(N_total) + 0.05

    alpha = 0.05
    H_sq_nl_init = potential.H_sq(phi_init, pi_init)
    grid = LGLCollocationGrid(5)

    result = solve_picard(
        N_init, N_final, delta_Nstar, alpha, H_sq_nl_init, grid,
        trajectory, potential, diffusion_model, atol, rtol, phi_end,
        disable_spatial_coupling=True,
    )
    assert result["failure"] is False
    assert result["diagnostics"]["converged"] is True

    N_grid_native = np.asarray(result["N_grid"])
    phi_grid_native = np.asarray(result["phi_grid"])
    pi_grid_native = np.asarray(result["pi_grid"])
    rfield_grid_native = np.asarray(result["rfield_grid"])
    rmom_grid_native = np.asarray(result["rmom_grid"])

    assert np.any(rfield_grid_native != 0.0)

    msr_native = compute_msr_action(
        N_grid_native, phi_grid_native, pi_grid_native, rfield_grid_native,
        rmom_grid_native, grid, potential, diffusion_model, H_sq_nl_init, alpha,
    )

    fp_sol = result["phi_pi_dense_solution"]
    bp_sol = result["response_dense_solution"]
    assert fp_sol is not None
    assert bp_sol is not None

    N_offset = trajectory.N_end - N_init
    n_nodes = grid.n_collocation_points

    def _resample(n_points: int) -> float:
        """Reuse solve_picard's own dense-output ODE solutions (no
        re-solving) to reconstruct (phi, pi, rfield, rmom) at a finer,
        arbitrary N resolution, then recompute msr_action on that grid."""
        N_fine = np.linspace(0.0, N_total, n_points)
        fp_states = fp_sol(N_fine)
        bp_states = bp_sol(N_fine)

        phi_rows = np.empty((n_points, n_nodes))
        pi_rows = np.empty((n_points, n_nodes))
        rfield_rows = np.empty((n_points, n_nodes))
        rmom_rows = np.empty((n_points, n_nodes))
        for i, N_i in enumerate(N_fine):
            phi_full, pi_full = unpack_state(
                fp_states[:, i], N_i, N_offset, alpha, H_sq_nl_init, grid,
                trajectory, potential,
            )
            rfield_full, rmom_full = unpack_response_state(bp_states[:, i], grid)
            phi_rows[i] = phi_full
            pi_rows[i] = pi_full
            rfield_rows[i] = rfield_full
            rmom_rows[i] = rmom_full

        return compute_msr_action(
            N_fine, phi_rows, pi_rows, rfield_rows, rmom_rows, grid, potential,
            diffusion_model, H_sq_nl_init, alpha,
        )

    msr_2x = _resample(2 * N_GRID_SIZE)
    msr_4x = _resample(4 * N_GRID_SIZE)

    # Native (300-point) and 2x/4x-resampled values should all agree with
    # each other at the percent level or better (trapezoid on an already
    # fairly fine grid), and refine towards a common limit.
    d1 = abs(msr_2x - msr_native)
    d2 = abs(msr_4x - msr_2x)

    print(
        f"\nmsr_action convergence diagnostic: "
        f"S(300)={msr_native:.12g}, S(600)={msr_2x:.12g}, S(1200)={msr_4x:.12g}, "
        f"|S(600)-S(300)|={d1:.3e}, |S(1200)-S(600)|={d2:.3e}, "
        f"ratio={d1 / d2 if d2 > 0 else float('inf'):.3g} "
        f"(expect ~4 for second-order trapezoid convergence under grid halving)"
    )

    # Diagnostic, not a strict gate: confirm the discrepancy genuinely
    # shrinks under refinement (loose bound -- the empirically observed
    # ratio is close to 4, consistent with trapezoid's O(h^2) convergence).
    assert d2 < d1
    assert d1 > 0.0 and d2 > 0.0
    ratio = d1 / d2
    assert ratio > 2.0
