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
Picard iteration / shooting driver for the gradient-coupled instanton model
(eq. colloc-eqs, terminal-colloc, shooting), tying together the forward and
response collocation right-hand sides of forward_rhs.py / response_rhs.py.

Mirrors FullInstanton's own adjoint/Picard/outer-Newton structure
(ComputeTargets/FullInstanton.py's _compute_full_instanton) as closely as the
grid-valued generalization allows: the same constants, the same overall
shape (background pass -> Picard inner loop -> outer Newton loop on the
shooting parameter lambda), generalized from scalar (phi, pi, P1, P2) arrays
over N to grid-valued arrays over (N, y) of shape
(len(N_grid), n_collocation_points).

N convention. N_init/N_final/delta_Nstar are supplied in the same
"e-folds before the end of inflation" convention as FullInstanton's own
constructor parameters (N_init > N_final; delta_Nstar the excess duration
added on top of the naive N_init-N_final span). Numerics/OnionCoordinate.py's
delta_s(N, N_init, ...) requires its own running N argument to *increase*
away from N_init for Delta_s(N) to grow from ln(1+alpha) (at the transition
start) to the O(10) values reached by the transition end (Numerics/
OnionCoordinate.py and the onion-model notes' Delta_s(N_init) identity), so
the actual domain used here is [N_init, N_init + N_total] with
N_total = (N_init - N_final) + delta_Nstar -- the same N_total FullInstanton
computes, just used as an additive offset from N_init rather than a reset to
zero, so that forward_rhs's own N_init parameter and the domain's lower
bound coincide exactly.
"""

import time
from typing import Optional

import numpy as np
from scipy.integrate import solve_ivp

from Interpolation.spline_wrapper import SplineWrapper
from Numerics.OnionCoordinate import delta_s
from ComputeTargets.GradientCoupledInstanton.forward_rhs import (
    pack_state,
    unpack_state,
    forward_rhs,
)
from ComputeTargets.GradientCoupledInstanton.response_rhs import (
    unpack_response_state,
    response_rhs,
    terminal_response_state,
)

MAX_OUTER = 50
MAX_INNER = 30

# Number of temporal sample points spanning [N_init, N_init + N_total];
# matches FullInstanton's own floor value (N_GRID = max(300, ...)).
N_GRID_SIZE = 300


def _build_node_splines(N_grid: np.ndarray, values_grid: np.ndarray, y_transform: str) -> list:
    """One SplineWrapper per grid node (columns of values_grid), each built
    over the shared N_grid. values_grid has shape (len(N_grid), n_nodes)."""
    n_nodes = values_grid.shape[1]
    return [
        SplineWrapper(N_grid, values_grid[:, j], y_transform=y_transform, k=3)
        for j in range(n_nodes)
    ]


def solve_picard(
    N_init: float,
    N_final: float,
    delta_Nstar: float,
    alpha: float,
    H_sq_nl_init: float,
    grid,
    trajectory,
    potential,
    diffusion_model,
    atol: float,
    rtol: float,
    phi_end: float,
    disable_spatial_coupling: bool = False,
    label: Optional[str] = None,
) -> dict:
    """
    Solve the gradient-coupled instanton BVP over the onion coordinate grid
    by Picard iteration with an outer Newton correction on the shooting
    parameter lambda = P1-equivalent terminal Lagrange multiplier.

    Boundary conditions:
        phi(y_j, N_init) = phi_init, pi(y_j, N_init) = pi_init  (uniform in y)
        phi(y=+1, N_stop) = phi_end   [shooting condition on lambda]

    Returns a dict with keys:
        "N_total", "N_grid", "phi_grid", "pi_grid", "rfield_grid",
        "rmom_grid", "final_lambda", "failure", "diagnostics"
    """
    compute_start = time.perf_counter()
    ode_solve_count = 0

    _lbl = label if label else f"phi_end={phi_end:.4g} N_init={N_init:.3g} N_final={N_final:.3g}"

    n_max = grid.n_max
    n_nodes = n_max + 1

    OUTER_TOL = max(atol * 100.0, 1e-6)
    INNER_TOL = atol * 10.0

    N_total = (N_init - N_final) + delta_Nstar
    N_start = N_init
    N_stop = N_init + N_total

    N_grid = np.linspace(N_start, N_stop, N_GRID_SIZE)
    N_grid_rev = N_grid[::-1]

    phi_init = trajectory.phi_before_end(N_start)
    pi_init = trajectory.pi_before_end(N_start)

    # Uniform-in-y initial condition (eq. bc-init): the core has not yet
    # deviated from the noiseless background anywhere on the grid.
    state_init = pack_state(np.full(n_nodes, phi_init), np.full(n_nodes, pi_init))

    def _unpack_grid(y_matrix: np.ndarray, N_values: np.ndarray):
        phi_grid = np.empty((len(N_values), n_nodes))
        pi_grid = np.empty((len(N_values), n_nodes))
        for i, N_i in enumerate(N_values):
            phi_full_i, pi_full_i = unpack_state(
                y_matrix[:, i], N_i, N_init, alpha, H_sq_nl_init, grid, trajectory, potential
            )
            phi_grid[i] = phi_full_i
            pi_grid[i] = pi_full_i
        return phi_grid, pi_grid

    def _unpack_response_grid(y_matrix: np.ndarray, N_values: np.ndarray):
        rfield_grid = np.empty((len(N_values), n_nodes))
        rmom_grid = np.empty((len(N_values), n_nodes))
        for i in range(len(N_values)):
            rfield_full_i, rmom_full_i = unpack_response_state(y_matrix[:, i], grid)
            rfield_grid[i] = rfield_full_i
            rmom_grid[i] = rmom_full_i
        return rfield_grid, rmom_grid

    def _fwd_rhs(N, y, rfield_splines, rmom_splines):
        return forward_rhs(
            N, y, N_init, alpha, H_sq_nl_init, grid, trajectory, potential,
            rfield_splines, rmom_splines, diffusion_model,
            disable_spatial_coupling=disable_spatial_coupling,
        )

    def _bwd_rhs(N, y, phi_splines, pi_splines):
        return response_rhs(
            N, y, N_init, alpha, H_sq_nl_init, grid, phi_splines, pi_splines, potential,
        )

    def _failure_diagnostics(outer_iterations, newton_fallback_count,
                              picard_iterations_per_outer, picard_time_total,
                              picard_iters_total, final_residual):
        return {
            "compute_time": time.perf_counter() - compute_start,
            "converged": False,
            "final_residual": final_residual,
            "total_ode_solves": ode_solve_count,
            "outer_iterations": outer_iterations,
            "newton_fallback_count": newton_fallback_count,
            "final_lambda": None,
            "picard_iterations_per_outer": picard_iterations_per_outer,
            "min_picard_iterations": min(picard_iterations_per_outer) if picard_iterations_per_outer else None,
            "max_picard_iterations": max(picard_iterations_per_outer) if picard_iterations_per_outer else None,
            "mean_picard_iterations": (
                sum(picard_iterations_per_outer) / len(picard_iterations_per_outer)
                if picard_iterations_per_outer else None
            ),
            "mean_time_per_picard_iteration": (
                picard_time_total / picard_iters_total if picard_iters_total else None
            ),
        }

    def _failure_result(diagnostics):
        return {
            "failure": True,
            "N_total": N_total,
            "N_grid": [],
            "phi_grid": [], "pi_grid": [],
            "rfield_grid": [], "rmom_grid": [],
            "final_lambda": None,
            "diagnostics": diagnostics,
        }

    # ── Zeroth Picard iterate: background pass, response fields zero ──────
    zero_splines = _build_node_splines(N_grid, np.zeros((N_GRID_SIZE, n_nodes)), y_transform='sinh')

    bg_sol = solve_ivp(
        lambda N, y: _fwd_rhs(N, y, zero_splines, zero_splines),
        (N_start, N_stop), state_init, method="RK45", t_eval=N_grid, atol=atol, rtol=rtol,
    )
    ode_solve_count += 1
    if not bg_sol.success:
        print(f"[{_lbl}] background ODE failed for zeroth Picard iterate")
        return _failure_result(_failure_diagnostics(0, 0, [], 0.0, 0, None))

    phi_grid0, pi_grid0 = _unpack_grid(bg_sol.y, N_grid)

    def picard_inner(lam: float, phi_grid_in: np.ndarray, pi_grid_in: np.ndarray):
        """Run Picard iteration for fixed lambda. Returns grids or Nones."""
        nonlocal ode_solve_count
        phi_grid = phi_grid_in.copy()
        pi_grid = pi_grid_in.copy()
        rfield_grid = np.zeros((N_GRID_SIZE, n_nodes))
        rmom_grid = np.zeros((N_GRID_SIZE, n_nodes))
        n_inner_iters = 0

        for _ in range(MAX_INNER):
            n_inner_iters += 1
            phi_splines = _build_node_splines(N_grid, phi_grid, y_transform='linear')
            pi_splines = _build_node_splines(N_grid, pi_grid, y_transform='linear')

            # Backward pass: terminal condition at N_stop (eq. terminal-colloc).
            H_sq_core_final = potential.H_sq(phi_grid[-1, -1], pi_grid[-1, -1])
            delta_s_N_final = delta_s(N_stop, N_init, H_sq_core_final, H_sq_nl_init, alpha)
            terminal_state = terminal_response_state(lam, grid, delta_s_N_final)

            bp = solve_ivp(
                lambda N, y: _bwd_rhs(N, y, phi_splines, pi_splines),
                (N_stop, N_start), terminal_state, method="RK45",
                t_eval=N_grid_rev, atol=atol, rtol=rtol,
            )
            ode_solve_count += 1
            if not bp.success:
                return None, None, None, None, n_inner_iters

            response_y = bp.y[:, ::-1]
            rfield_grid, rmom_grid = _unpack_response_grid(response_y, N_grid)

            rfield_splines = _build_node_splines(N_grid, rfield_grid, y_transform='sinh')
            rmom_splines = _build_node_splines(N_grid, rmom_grid, y_transform='sinh')

            # Forward pass, now sourced by the just-computed response fields.
            fp = solve_ivp(
                lambda N, y: _fwd_rhs(N, y, rfield_splines, rmom_splines),
                (N_start, N_stop), state_init, method="RK45",
                t_eval=N_grid, atol=atol, rtol=rtol,
            )
            ode_solve_count += 1
            if not fp.success:
                return None, None, None, None, n_inner_iters

            phi_grid_new, pi_grid_new = _unpack_grid(fp.y, N_grid)
            inner_res = np.max(np.abs(phi_grid_new - phi_grid))
            phi_grid, pi_grid = phi_grid_new, pi_grid_new
            if inner_res < INNER_TOL:
                break

        return phi_grid, pi_grid, rfield_grid, rmom_grid, n_inner_iters

    # ── Outer Newton loop on lambda ────────────────────────────────────────
    lam = 0.0
    phi_grid_f, pi_grid_f = phi_grid0, pi_grid0
    rfield_grid_f = np.zeros((N_GRID_SIZE, n_nodes))
    rmom_grid_f = np.zeros((N_GRID_SIZE, n_nodes))
    converged = False
    final_residual = None
    outer_iterations = 0
    newton_fallback_count = 0
    picard_iterations_per_outer = []
    picard_time_total = 0.0
    picard_iters_total = 0

    for outer in range(MAX_OUTER):
        outer_iterations = outer + 1
        picard_start = time.perf_counter()
        pg, pig, rfg, rmg, n_inner = picard_inner(lam, phi_grid_f, pi_grid_f)
        picard_time_total += time.perf_counter() - picard_start
        picard_iters_total += n_inner
        picard_iterations_per_outer.append(n_inner)
        if pg is None:
            print(f"[{_lbl}] Picard inner failed at outer iter {outer}")
            break

        # Shooting residual: core node (y=+1), final row (N_stop).
        residual = pg[-1, -1] - phi_end
        final_residual = abs(residual)

        phi_grid_f, pi_grid_f, rfield_grid_f, rmom_grid_f = pg, pig, rfg, rmg

        if abs(residual) < OUTER_TOL:
            converged = True
            break

        # Finite-difference Newton step.
        dlam = max(abs(lam) * 1e-4, 1e-6)
        picard_start = time.perf_counter()
        pg_p, _, _, _, n_inner_p = picard_inner(lam + dlam, phi_grid_f, pi_grid_f)
        picard_time_total += time.perf_counter() - picard_start
        picard_iters_total += n_inner_p
        picard_iterations_per_outer.append(n_inner_p)
        if pg_p is not None:
            dres_dlam = (pg_p[-1, -1] - pg[-1, -1]) / dlam
            if abs(dres_dlam) > 1e-14:
                lam -= residual / dres_dlam
                continue
        # Fallback nudge.
        newton_fallback_count += 1
        lam += (phi_end - pg[-1, -1]) * 0.1

    diagnostics = {
        "compute_time": time.perf_counter() - compute_start,
        "converged": converged,
        "final_residual": final_residual,
        "total_ode_solves": ode_solve_count,
        "outer_iterations": outer_iterations,
        "newton_fallback_count": newton_fallback_count,
        "final_lambda": lam if converged else None,
        "picard_iterations_per_outer": picard_iterations_per_outer,
        "min_picard_iterations": min(picard_iterations_per_outer) if picard_iterations_per_outer else None,
        "max_picard_iterations": max(picard_iterations_per_outer) if picard_iterations_per_outer else None,
        "mean_picard_iterations": (
            sum(picard_iterations_per_outer) / len(picard_iterations_per_outer)
            if picard_iterations_per_outer else None
        ),
        "mean_time_per_picard_iteration": (
            picard_time_total / picard_iters_total if picard_iters_total else None
        ),
    }

    if not converged:
        print(f"[{_lbl}] outer loop did not converge "
              f"after {MAX_OUTER} iterations (target tolerance was {OUTER_TOL})")
        return _failure_result(diagnostics)

    return {
        "failure": False,
        "N_total": N_total,
        "N_grid": N_grid.tolist(),
        "phi_grid": phi_grid_f.tolist(),
        "pi_grid": pi_grid_f.tolist(),
        "rfield_grid": rfield_grid_f.tolist(),
        "rmom_grid": rmom_grid_f.tolist(),
        "final_lambda": lam,
        "diagnostics": diagnostics,
    }
