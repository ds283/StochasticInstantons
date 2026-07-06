"""
Unit / integration tests for the Picard iteration and shooting driver,
ComputeTargets/GradientCoupledInstanton/picard.py.
"""

import numpy as np
import pytest
from scipy.integrate import solve_ivp

from ComputeTargets.FullInstanton import _compute_full_instanton
from ComputeTargets.GradientCoupledInstanton import picard as picard_module
from ComputeTargets.GradientCoupledInstanton.picard import solve_picard
from InflationConcepts.DiffusionModel import MasslessDecoupledDiffusion
from Interpolation.spline_wrapper import SplineWrapper
from Numerics.LGLCollocation import LGLCollocationGrid


# ---------------------------------------------------------------------------
# Stubs
# ---------------------------------------------------------------------------


class _StubPotential:
    """
    Standalone duck-typed canonical-inflation potential (Mp = 1), matching
    AbstractPotential's own H_sq/epsilon formulas -- the same stub used in
    tests/test_forward_rhs.py and tests/test_response_rhs.py.
    """

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
    """
    Duck-typed trajectory stub whose phi_before_end/pi_before_end trace out
    the *noiseless* background ODE (dphi/dN = pi,
    dpi/dN = -(3-eps)*pi - dV/Hsq -- FullInstanton's own bg_rhs) over
    [N_start, N_stop], reconstructed via SplineWrapper.

    Used for the reduction-limit test: with disable_spatial_coupling=True
    and identically-zero response-field sourcing, every collocation node
    (outer edge, interior, core) is governed by this same, decoupled,
    per-node ODE with the same uniform initial condition (eq. bc-init), so
    they all track this background exactly and the core (Neumann-eliminated
    from the other, background-tracking nodes) reduces to it too.
    """

    def __init__(self, potential, phi_init, pi_init, N_start, N_stop, atol, rtol):
        def bg_rhs(N, y):
            phi, pi = y
            return [
                pi,
                -(3.0 - potential.epsilon(phi, pi)) * pi
                - potential.dV_dphi(phi) / potential.H_sq(phi, pi),
            ]

        N_grid = np.linspace(N_start, N_stop, 400)
        sol = solve_ivp(
            bg_rhs, (N_start, N_stop), [phi_init, pi_init],
            method="RK45", t_eval=N_grid, atol=atol, rtol=rtol,
        )
        assert sol.success

        self._phi_spline = SplineWrapper(N_grid, sol.y[0], k=3)
        self._pi_spline = SplineWrapper(N_grid, sol.y[1], k=3)

    def phi_before_end(self, N: float) -> float:
        return float(self._phi_spline(N))

    def pi_before_end(self, N: float) -> float:
        return float(self._pi_spline(N))


class _PotentialHolder:
    """Duck-typed stand-in for InflatonTrajectory, exposing only the
    ._potential attribute _compute_full_instanton actually reads."""

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
# Reduction-limit, end to end
# ---------------------------------------------------------------------------


def test_solve_picard_reduction_limit_matches_full_instanton():
    """
    With gradient coupling structurally disabled (disable_spatial_coupling=
    True) and a trajectory stub that tracks the same noiseless background
    ODE FullInstanton's own bg_rhs solves, solve_picard's full output at the
    core node should match what FullInstanton itself produces for the same
    (phi_init, pi_init, phi_final, N_total, potential, diffusion_model)
    -- the integration-level version of the unit-level reduction tests in
    prompts 04-05.
    """
    potential = _StubPotential()
    diffusion_model = MasslessDecoupledDiffusion()

    N_init = 5.0
    N_final = 2.0
    delta_Nstar = 1.0
    N_total = (N_init - N_final) + delta_Nstar
    N_stop = N_init + N_total

    phi_init = 10.0
    pi_init = -0.01
    atol = 1.0e-9
    rtol = 1.0e-9

    trajectory = _BackgroundTrackingTrajectory(
        potential, phi_init, pi_init, N_init, N_stop, atol, rtol
    )
    phi_end = trajectory.phi_before_end(N_stop)

    alpha = 0.05
    H_sq_nl_init = potential.H_sq(phi_init, pi_init)
    grid = LGLCollocationGrid(5)  # small n_collocation_points to keep this fast

    result = solve_picard(
        N_init, N_final, delta_Nstar, alpha, H_sq_nl_init, grid,
        trajectory, potential, diffusion_model, atol, rtol, phi_end,
        disable_spatial_coupling=True,
    )

    assert result["failure"] is False
    assert result["diagnostics"]["converged"] is True

    N_grid = np.array(result["N_grid"])
    t_grid = (N_grid - N_init).tolist()

    fi_data = _compute_full_instanton._function(
        trajectory=_TrajectoryProxyStub(potential),
        dm=diffusion_model,
        phi_init=phi_init,
        pi_init=pi_init,
        phi_final=phi_end,
        N_total=N_total,
        N_sample=t_grid,
        atol=atol,
        rtol=rtol,
    )
    assert fi_data["failure"] is False

    phi_grid = np.array(result["phi_grid"])
    core_phi = phi_grid[:, -1]
    fi_phi1 = np.array(fi_data["phi1"])

    np.testing.assert_allclose(core_phi, fi_phi1, rtol=1.0e-5, atol=1.0e-6)

    # Every other node (outer edge, interior) should also track the same
    # background, since disable_spatial_coupling=True decouples every node
    # and they all share the same uniform initial condition.
    for j in range(phi_grid.shape[1]):
        np.testing.assert_allclose(phi_grid[:, j], fi_phi1, rtol=1.0e-5, atol=1.0e-6)


# ---------------------------------------------------------------------------
# Convergence diagnostics shape
# ---------------------------------------------------------------------------


def test_solve_picard_diagnostics_match_full_instanton_shape():
    potential = _StubPotential()
    diffusion_model = MasslessDecoupledDiffusion()

    N_init = 5.0
    N_final = 2.0
    delta_Nstar = 1.0
    N_stop = N_init + (N_init - N_final) + delta_Nstar

    phi_init = 10.0
    pi_init = -0.01
    atol = 1.0e-8
    rtol = 1.0e-8

    trajectory = _BackgroundTrackingTrajectory(
        potential, phi_init, pi_init, N_init, N_stop, atol, rtol
    )
    phi_end = trajectory.phi_before_end(N_stop)

    grid = LGLCollocationGrid(5)
    result = solve_picard(
        N_init, N_final, delta_Nstar, 0.05, potential.H_sq(phi_init, pi_init),
        grid, trajectory, potential, diffusion_model, atol, rtol, phi_end,
        disable_spatial_coupling=True,
    )

    expected_keys = {
        "compute_time", "converged", "final_residual", "total_ode_solves",
        "outer_iterations", "newton_fallback_count", "final_lambda",
        "picard_iterations_per_outer", "min_picard_iterations",
        "max_picard_iterations", "mean_picard_iterations",
        "mean_time_per_picard_iteration",
    }
    assert expected_keys.issubset(result["diagnostics"].keys())
    assert result["diagnostics"]["converged"] is True
    assert result["diagnostics"]["outer_iterations"] >= 1


# ---------------------------------------------------------------------------
# Non-convergence returns a failure dict, doesn't raise
# ---------------------------------------------------------------------------


def test_solve_picard_non_convergence_returns_failure_dict(monkeypatch):
    """Force non-convergence by capping MAX_OUTER at 1 outer iteration and
    picking an unreachable shooting target -- mirrors how a too-tight
    OUTER_TOL-equivalent or too-few-MAX_OUTER scenario would be constructed,
    per the prompt's guidance to check for an existing FullInstanton
    non-convergence test first (there is none) before inventing this one."""
    monkeypatch.setattr(picard_module, "MAX_OUTER", 1)

    potential = _StubPotential()
    diffusion_model = MasslessDecoupledDiffusion()

    N_init = 5.0
    N_final = 2.0
    delta_Nstar = 1.0
    N_stop = N_init + (N_init - N_final) + delta_Nstar

    phi_init = 10.0
    pi_init = -0.01
    atol = 1.0e-8
    rtol = 1.0e-8

    trajectory = _BackgroundTrackingTrajectory(
        potential, phi_init, pi_init, N_init, N_stop, atol, rtol
    )
    # Deliberately unreachable in a single outer iteration.
    phi_end = trajectory.phi_before_end(N_stop) + 0.5

    grid = LGLCollocationGrid(5)
    result = picard_module.solve_picard(
        N_init, N_final, delta_Nstar, 0.05, potential.H_sq(phi_init, pi_init),
        grid, trajectory, potential, diffusion_model, atol, rtol, phi_end,
        disable_spatial_coupling=True,
    )

    assert result["failure"] is True
    assert result["diagnostics"]["converged"] is False
