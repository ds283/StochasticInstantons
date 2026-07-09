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
Standalone exploration of the GradientCoupledInstanton "zeroth Picard
iterate" background ODE, reproducing the exact production setup
(quadratic-asteroid-small.yaml: phi0=15, pi0=0, m=1e-5 Mp) without any
Ray/Datastore machinery, to test whether the observed failures
("background ODE failed for zeroth Picard iterate") are:

  (a) a genuine stiffness limitation of the explicit RK45 integrator
      (as .documents/onion_model_implementation_review.md Section 5
      predicts), or
  (b) an actual bug independent of integrator choice.

``StubPotential``, ``build_real_trajectory``, and ``run_case`` are consumed
by ``harness.py`` and ``seed_screen.py`` elsewhere in this package. This
module predates the rest of the diagnostic suite and its own ``main()``/
``run_units_system()`` entry point (below) is retained standalone, run as
``python -m tools.diagnostics.GradientCoupledInstanton.explore_onion_stiffness``.
"""

import numpy as np
from scipy.integrate import solve_ivp

from Interpolation.spline_wrapper import SplineWrapper
from Numerics.LGLCollocation import LGLCollocationGrid
from ComputeTargets.GradientCoupledInstanton.forward_rhs import forward_rhs, pack_state
from InflationConcepts.DiffusionModel import MasslessDecoupledDiffusion


# ---------------------------------------------------------------------------
# Stub potential -- same duck-typed formulas as tests/test_picard.py's
# _StubPotential, generalized to carry an explicit UnitsLike (Mp need not be
# 1) so the same physics can be exercised under Planck_units or GeV_units,
# exactly mirroring AbstractPotential.H_sq/epsilon's own units.PlanckMass
# formulas rather than hardcoding Mp=1.
# ---------------------------------------------------------------------------
class StubPotential:
    def __init__(self, m_sq, units):
        self._m_sq = m_sq
        self._units = units

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
        Mp = self._units.PlanckMass
        return self.V(phi) / (3.0 * Mp * Mp - 0.5 * pi * pi / (Mp * Mp))

    def epsilon(self, phi, pi):
        pi = np.asarray(pi)
        Mp = self._units.PlanckMass
        return 0.5 * pi * pi / (Mp * Mp)


class SplineTrajectory:
    def __init__(self, N_end, phi_spline, pi_spline):
        self._N_end = N_end
        self._phi_spline = phi_spline
        self._pi_spline = pi_spline

    @property
    def N_end(self) -> float:
        return self._N_end

    def phi_at(self, N: float) -> float:
        return float(self._phi_spline(N))

    def pi_at(self, N: float) -> float:
        return float(self._pi_spline(N))


def build_real_trajectory(potential, phi0, pi0, atol, rtol):
    """Integrate the real noiseless background (dphi/dN=pi, dpi/dN=-(3-eps)pi
    - dV/H^2) from N=0 to epsilon=1, exactly as InflatonTrajectory does."""

    def bg_rhs(N, y):
        phi, pi = y
        return [
            pi,
            -(3.0 - potential.epsilon(phi, pi)) * pi
            - potential.dV_dphi(phi) / potential.H_sq(phi, pi),
        ]

    def end_event(N, y):
        return potential.epsilon(y[0], y[1]) - 1.0

    end_event.terminal = True
    end_event.direction = 1

    sol = solve_ivp(
        bg_rhs, (0.0, 200.0), [phi0, pi0], method="RK45",
        atol=atol, rtol=rtol, events=end_event, dense_output=True, max_step=0.05,
    )
    assert sol.success, "background trajectory integration failed"
    assert len(sol.t_events[0]) == 1, "end-of-inflation event not hit exactly once"
    N_end = float(sol.t_events[0][0])

    N_grid = np.linspace(0.0, N_end, 6000)
    y = sol.sol(N_grid)
    phi_spline = SplineWrapper(N_grid, y[0], k=3)
    pi_spline = SplineWrapper(N_grid, y[1], k=3)
    return SplineTrajectory(N_end, phi_spline, pi_spline)


def run_case(traj, potential, dm, N_init, N_final, delta_Nstar, n_colloc, alpha,
             atol, rtol, method="RK45", verbose=True, diagnose=False):
    grid = LGLCollocationGrid(n_colloc)
    n_max = grid.n_max
    n_nodes = n_max + 1

    N_offset = traj.N_end - N_init
    N_total = (N_init - N_final) + delta_Nstar

    phi_init = traj.phi_at(N_offset)
    pi_init = traj.pi_at(N_offset)
    H_sq_nl_init = potential.H_sq(phi_init, pi_init)

    state_init = pack_state(np.full(n_nodes, phi_init), np.full(n_nodes, pi_init))
    zero_splines = [lambda N: 0.0 for _ in range(n_nodes)]

    n_calls = [0]
    last = {}

    def rhs(N, y):
        n_calls[0] += 1
        out = forward_rhs(
            N, y, N_offset, alpha, H_sq_nl_init, grid, traj, potential,
            zero_splines, zero_splines, dm, disable_spatial_coupling=False,
        )
        if diagnose:
            last["N"] = N
            last["y"] = y.copy()
            last["out"] = out.copy()
        return out

    try:
        sol = solve_ivp(
            rhs, (0.0, N_total), state_init, method=method,
            t_eval=np.linspace(0.0, N_total, 300), atol=atol, rtol=rtol,
        )
        success, message = sol.success, sol.message
        N_reached = sol.t[-1] if len(sol.t) else 0.0
    except ValueError as exc:
        success, message = False, f"EXCEPTION: {exc}"
        N_reached = last.get("N", 0.0)

    result = {
        "method": method, "success": success, "n_calls": n_calls[0],
        "N_reached": N_reached, "N_total": N_total, "message": message,
    }
    if verbose:
        print(
            f"  method={method:6s} n_colloc={n_colloc:3d} alpha={alpha:<7g} "
            f"success={success!s:5s} N_reached={result['N_reached']:.4f}/"
            f"{N_total:.4f} rhs_calls={n_calls[0]:5d}  {message}"
        )
    if diagnose and last:
        from ComputeTargets.GradientCoupledInstanton.forward_rhs import unpack_state
        N_last = last["N"]
        phi_full, pi_full = unpack_state(
            last["y"], N_last, N_offset, alpha, H_sq_nl_init, grid, traj, potential
        )
        H_sq_core = potential.H_sq(phi_full[-1], pi_full[-1])
        print(f"    [diagnose] last N={N_last:.6g}  phi_core={phi_full[-1]:.6g} "
              f"pi_core={pi_full[-1]:.6g}  H_sq_core={H_sq_core:.6g}  "
              f"pi_max={np.max(np.abs(pi_full)):.6g}  phi_range=[{phi_full.min():.4g},{phi_full.max():.4g}]")
    return result


def run_units_system(units, label):
    """phi0-Mp/pi0-Mp/m-values-Mp in quadratic-asteroid-small.yaml are
    dimensionless multiples of Mp -- converting them to raw values under a
    given UnitsLike means multiplying by units.PlanckMass, exactly as
    Datastore/SQL factories restore dimensionful columns (see
    .claude/rules/datastore-units.md). atol/rtol are dimensionless
    solver tolerances (rtol always; atol is negligible here since state
    magnitudes >> 1e-8 in both systems), so they are not rescaled."""
    Mp = units.PlanckMass
    m = 1.0e-5 * Mp
    phi0, pi0 = 15.0 * Mp, 0.0 * Mp
    atol = rtol = 1.0e-8

    potential = StubPotential(m * m, units)

    print(f"\n{'#' * 78}\n# Units system: {label}  (PlanckMass = {Mp:.6g})\n{'#' * 78}")
    print(f"Building real background trajectory (phi0={phi0:.6g}, pi0={pi0:.6g}, m={m:.6g})...")
    traj = build_real_trajectory(potential, phi0, pi0, atol, rtol)
    print(f"  N_end = {traj.N_end:.6f}\n")

    dm = MasslessDecoupledDiffusion()

    # One of the failing combinations from the interrupted run.
    N_init, N_final, delta_Nstar = 19.5, 16.0, 0.1

    print(f"Case: N_init={N_init}, N_final={N_final}, delta_Nstar={delta_Nstar}")
    print("=" * 78)
    print("-- Finding the n_collocation_points threshold under RK45 (alpha=0.1) --")
    for n_colloc in (5, 7, 9, 11, 13, 15, 17, 21, 25, 33):
        run_case(traj, potential, dm, N_init, N_final, delta_Nstar,
                  n_colloc, 0.1, atol, rtol, method="RK45")
    return traj, potential, dm


def main():
    from Units.Planck_units import Planck_units
    from Units.GeV_units import GeV_units

    run_units_system(Planck_units(), "Planck_units")
    traj, potential, dm = run_units_system(GeV_units(), "GeV_units")

    N_init, N_final, delta_Nstar = 19.5, 16.0, 0.1
    atol = rtol = 1.0e-8

    print()
    print("-- Same failing case (n_colloc=17, alpha=0.1) under every integrator --")
    for method in ("RK45", "DOP853", "Radau", "BDF", "LSODA"):
        run_case(traj, potential, dm, N_init, N_final, delta_Nstar,
                  17, 0.1, atol, rtol, method=method, diagnose=True)

    print()
    print("-- Diagnosing the n_colloc=9 (success) vs n_colloc=17 (fail) boundary --")
    for n_colloc in (9, 11, 13, 15, 17):
        run_case(traj, potential, dm, N_init, N_final, delta_Nstar,
                  n_colloc, 0.1, atol, rtol, method="RK45", diagnose=True)


if __name__ == "__main__":
    main()
