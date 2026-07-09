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
Tests for prompt 23 Part B -- the response-sector lambda-scaling convention
(response_rhs.terminal_response_state_rescaled, forward_rhs.noise_source_terms's
own lam parameter, and picard.py's rfield_tilde_grid/rmom_tilde_grid ->
rfield_grid/rmom_grid reconstruction). Full derivation:
.documents/gradient-coupled-instanton/23-response-sbp-sat-design-note.md.

Exercises response_rhs directly (isolated backward-pass solve_ivp calls, not
the full Picard/shooting loop) to keep these fast and to isolate exactly the
claim Part B makes: response_rhs is linear and homogeneous in the response
fields, so r(N) = lam * r_tilde(N) EXACTLY, and integrating r_tilde (an
O(1)-ish terminal condition) stays numerically feasible at astronomic lam
where integrating the physical r directly becomes intractable.
"""

import time

import numpy as np
import pytest
from scipy.integrate import solve_ivp

from ComputeTargets.GradientCoupledInstanton.response_rhs import (
    response_rhs,
    terminal_response_state,
    terminal_response_state_rescaled,
    unpack_response_state,
)
from ComputeTargets.GradientCoupledInstanton.forward_rhs import noise_source_terms, diluted_diffusion_coefficients
from Numerics.LGLCollocation import LGLCollocationGrid
from Numerics.OnionCoordinate import delta_s

# Parametrized solve_ivp backward passes across lambda values -- tens of
# seconds per case, minutes total. Only worth running when ComputeTargets/
# (or its numerical dependencies) change; see .claude/rules/test-selection.md.
pytestmark = pytest.mark.slow


class _StubPotential:
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


class _ConstSpline:
    def __init__(self, v):
        self._v = v

    def __call__(self, N):
        return self._v


def _setup(n_max=17):
    grid = LGLCollocationGrid(n_max + 1)
    alpha = 0.1
    N_total = 4.5
    potential = _StubPotential(m_sq=1.3)

    phi0, pi0 = 3.0, -0.05
    phi_splines = [_ConstSpline(phi0) for _ in range(n_max + 1)]
    pi_splines = [_ConstSpline(pi0) for _ in range(n_max + 1)]

    # Self-consistent H_sq_nl_init (matches the constant trajectory's own
    # H_sq exactly), so delta_s_N(N) = ln(1+alpha) + N -- a realistic,
    # positive-growing Delta_s(N) rather than an arbitrary mismatched value
    # (which can drive delta_s_N negative, an unphysical/out-of-domain
    # regime for this model unrelated to the lambda-scaling question these
    # tests isolate).
    H_sq_nl_init = potential.H_sq(phi0, pi0)
    H_sq_core_final = potential.H_sq(phi0, pi0)
    delta_s_N_final = delta_s(N_total, 0.0, H_sq_core_final, H_sq_nl_init, alpha)

    return grid, alpha, N_total, H_sq_nl_init, potential, phi_splines, pi_splines, delta_s_N_final


def _integrate_backward(grid, alpha, N_total, H_sq_nl_init, potential, phi_splines, pi_splines,
                         terminal_state, max_step=None, timeout_nfev=2_000_000):
    kwargs = dict(atol=1.0e-10, rtol=1.0e-8)
    if max_step is not None:
        kwargs["max_step"] = max_step
    sol = solve_ivp(
        lambda N, y: response_rhs(N, y, alpha, H_sq_nl_init, grid, phi_splines, pi_splines, potential),
        (N_total, 0.0), terminal_state, method="RK45", **kwargs,
    )
    return sol


# ---------------------------------------------------------------------------
# Linearity: response_rhs is exactly linear and homogeneous, so the response
# solution scales exactly with lam -- the algebraic fact Part B's rescaling
# rests on.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("lam", [0.5, 3.7, -2.1])
def test_response_solution_scales_exactly_with_lambda(lam):
    grid, alpha, N_total, H_sq_nl_init, potential, phi_splines, pi_splines, delta_s_N_final = _setup(n_max=9)

    terminal_tilde = terminal_response_state_rescaled(grid, delta_s_N_final)
    sol_tilde = _integrate_backward(grid, alpha, N_total, H_sq_nl_init, potential, phi_splines, pi_splines, terminal_tilde)
    assert sol_tilde.success

    terminal_physical = terminal_response_state(lam, grid, delta_s_N_final)
    sol_physical = _integrate_backward(grid, alpha, N_total, H_sq_nl_init, potential, phi_splines, pi_splines, terminal_physical)
    assert sol_physical.success

    # Same N_eval grid for a direct comparison.
    N_eval = np.linspace(0.0, N_total, 25)
    y_tilde = sol_tilde.sol(N_eval) if sol_tilde.sol is not None else None
    y_physical = sol_physical.sol(N_eval) if sol_physical.sol is not None else None
    if y_tilde is None or y_physical is None:
        # dense_output wasn't requested; fall back to the terminal/initial
        # endpoints only via sol.y directly (still probative).
        np.testing.assert_allclose(sol_physical.y[:, -1], lam * sol_tilde.y[:, -1], rtol=1.0e-6)
        return

    np.testing.assert_allclose(y_physical, lam * y_tilde, rtol=1.0e-6, atol=1.0e-10 * abs(lam))


# ---------------------------------------------------------------------------
# Feasibility at astronomic lambda: the rescaled backward pass reaches
# N=0.0 (RK45 succeeds) at lam ~ 2e9-4e9 (the resolved-regime magnitude),
# with a bounded number of function evaluations -- confirming the rescaled
# state vector stays well-conditioned regardless of lam.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("lam", [1.0, 1.0e5, 1.0e9, 4.0e9])
def test_rescaled_backward_pass_feasible_at_astronomic_lambda(lam):
    grid, alpha, N_total, H_sq_nl_init, potential, phi_splines, pi_splines, delta_s_N_final = _setup(n_max=33)

    terminal_tilde = terminal_response_state_rescaled(grid, delta_s_N_final)
    t0 = time.perf_counter()
    sol = _integrate_backward(grid, alpha, N_total, H_sq_nl_init, potential, phi_splines, pi_splines, terminal_tilde)
    wallclock = time.perf_counter() - t0

    # The rescaled terminal condition (and the whole backward-pass ODE) does
    # not depend on lam at all -- solving it should succeed, in essentially
    # the SAME number of steps, regardless of what lam the outer loop is
    # actually probing. This is the concrete "stays feasible... at
    # lambda ~ 2e9" acceptance check: nfev/wallclock must not blow up with lam.
    assert sol.success
    assert sol.nfev < 200_000
    assert wallclock < 10.0

    rfield_full, rmom_full = unpack_response_state(sol.y[:, -1], grid)
    assert np.all(np.isfinite(rfield_full))
    assert np.all(np.isfinite(rmom_full))


# ---------------------------------------------------------------------------
# forward_rhs's own lam parameter reconstructs the physical (D*lam)*r_tilde
# sourcing term exactly, matching the pre-prompt-23 D*r formula applied to
# the already-scaled physical field.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("lam", [1.0, 3.0, 1.0e6])
def test_noise_source_terms_lam_reconstructs_physical_sourcing(lam):
    grid = LGLCollocationGrid(10)
    from InflationConcepts.DiffusionModel import MasslessDecoupledDiffusion

    potential = _StubPotential(m_sq=1.3)
    dm = MasslessDecoupledDiffusion()

    rng = np.random.default_rng(99)
    n_nodes = grid.n_collocation_points
    phi_full = 3.0 + 0.1 * rng.standard_normal(n_nodes)
    pi_full = -0.05 + 0.01 * rng.standard_normal(n_nodes)
    rfield_tilde_full = rng.uniform(-1.0, 1.0, size=n_nodes)
    rmom_tilde_full = rng.uniform(-1.0, 1.0, size=n_nodes)

    delta_s_N = 3.7
    delta_s_loc_array = np.full(n_nodes, delta_s_N)

    # Reference: apply the OLD (lam=1.0-equivalent) formula directly to the
    # already-physically-scaled fields.
    rfield_physical = lam * rfield_tilde_full
    rmom_physical = lam * rmom_tilde_full
    noise_field_ref, noise_mom_ref = noise_source_terms(
        phi_full, pi_full, rfield_physical, rmom_physical, delta_s_N, delta_s_loc_array, grid, potential, dm,
    )

    # Under test: pass the TILDE fields plus lam, letting noise_source_terms
    # do the (D*lam)*r_tilde reconstruction itself.
    noise_field_test, noise_mom_test = noise_source_terms(
        phi_full, pi_full, rfield_tilde_full, rmom_tilde_full, delta_s_N, delta_s_loc_array, grid, potential, dm,
        lam=lam,
    )

    np.testing.assert_allclose(noise_field_test, noise_field_ref, rtol=1.0e-12)
    np.testing.assert_allclose(noise_mom_test, noise_mom_ref, rtol=1.0e-12)


def test_noise_source_terms_default_lam_is_exact_no_op():
    """lam's default (1.0) must reproduce every pre-prompt-23 call's
    behaviour bit-for-bit -- a regression guard on the default."""
    grid = LGLCollocationGrid(9)
    from InflationConcepts.DiffusionModel import MasslessDecoupledDiffusion

    potential = _StubPotential(m_sq=1.3)
    dm = MasslessDecoupledDiffusion()

    rng = np.random.default_rng(7)
    n_nodes = grid.n_collocation_points
    phi_full = 3.0 + 0.1 * rng.standard_normal(n_nodes)
    pi_full = -0.05 + 0.01 * rng.standard_normal(n_nodes)
    rfield_full = rng.uniform(-1.0, 1.0, size=n_nodes)
    rmom_full = rng.uniform(-1.0, 1.0, size=n_nodes)
    delta_s_N = 2.1
    delta_s_loc_array = np.full(n_nodes, delta_s_N)

    default_call = noise_source_terms(
        phi_full, pi_full, rfield_full, rmom_full, delta_s_N, delta_s_loc_array, grid, potential, dm,
    )
    explicit_lam1 = noise_source_terms(
        phi_full, pi_full, rfield_full, rmom_full, delta_s_N, delta_s_loc_array, grid, potential, dm, lam=1.0,
    )
    np.testing.assert_array_equal(default_call[0], explicit_lam1[0])
    np.testing.assert_array_equal(default_call[1], explicit_lam1[1])
