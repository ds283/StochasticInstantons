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
Forward-sector collocation right-hand side for the gradient-coupled instanton
model, with mandatory response-field sourcing (eq. ncount, Dnoise-diag,
Dnoise-cross): response fields are always sourced into the forward equations,
never omitted -- the "zeroth Picard iterate" (response fields zero) is now
just a particular input (all-zero rfield/rmom splines), not a special code
path.

Unlike Numerics/, which is deliberately physics-free, this is the first module
in the GradientCoupledInstanton subpackage allowed to depend directly on
AbstractPotential and InflatonTrajectory -- this is where physics and the
Numerics/ collocation machinery meet.

State vector layout. Not all 2(n_max+1) raw grid values are independently
integrated:

  - phi_0, pi_0 (outer edge, y=-1): Dirichlet-pinned to
    trajectory.phi_at(N_offset + N)/.pi_at(N_offset + N) -- not integrated,
    recomputed fresh at every RHS call.
  - phi_{n_max} (core, y=+1): Neumann-eliminated via neumann_boundary_value
    (Numerics/DiscretizedOperators.py, boundary_index=-1) -- not integrated.
  - pi_{n_max} (core momentum): genuinely free, is integrated.
  - Everything else (phi_1,...,phi_{n_max-1}, pi_1,...,pi_{n_max}) is
    integrated.

So the ODE state vector has length 2*n_max - 1:
(phi_1,...,phi_{n_max-1}, pi_1,...,pi_{n_max}).
"""

import numpy as np

from Numerics.OnionCoordinate import delta_s, advection_coefficient
from Numerics.DiscretizedOperators import (
    L_operator,
    advection_term,
    neumann_boundary_value,
)


def pack_state(phi_full: np.ndarray, pi_full: np.ndarray) -> np.ndarray:
    """
    Restrict (phi_full, pi_full), each of length n_max+1, to the integrated
    state vector of length 2*n_max-1: (phi_1,...,phi_{n_max-1},
    pi_1,...,pi_{n_max}). Drops phi_full[0]/pi_full[0] (Dirichlet-pinned) and
    phi_full[-1] (Neumann-eliminated).
    """
    n_max = len(phi_full) - 1
    return np.concatenate([phi_full[1:n_max], pi_full[1:n_max + 1]])


def unpack_state(
    state: np.ndarray,
    N: float,
    N_offset: float,
    alpha: float,
    H_sq_nl_init: float,
    grid,
    trajectory,
    potential,
):
    """
    Expand the integrated state vector back to the full-length (phi_full,
    pi_full) grid arrays, each of length n_max+1.

    Index 0 (y=-1): Dirichlet-pinned from the noiseless background,
    trajectory.phi_at(N_offset + N)/.pi_at(N_offset + N).

    Index n_max (y=+1): pi_full[n_max] is the free, integrated core
    momentum, taken directly from the state vector. phi_full[n_max] is
    Neumann-eliminated via neumann_boundary_value, using the just-assembled
    phi_full (every index other than the boundary one is already correct;
    neumann_boundary_value ignores whatever placeholder sits at the boundary
    index itself).

    alpha, H_sq_nl_init, and potential are threaded through for a signature
    shared with forward_rhs's local context; unpack_state itself only needs
    N_offset (for the trajectory lookup).
    """
    n_max = grid.n_max

    phi_full = np.empty(n_max + 1)
    pi_full = np.empty(n_max + 1)

    phi_full[0] = trajectory.phi_at(N_offset + N)
    pi_full[0] = trajectory.pi_at(N_offset + N)

    n_phi_interior = n_max - 1
    phi_full[1:n_max] = state[:n_phi_interior]
    pi_full[1:n_max + 1] = state[n_phi_interior:n_phi_interior + n_max]

    phi_full[-1] = neumann_boundary_value(phi_full, grid.D, boundary_index=-1)

    return phi_full, pi_full


def forward_rhs(
    N: float,
    state: np.ndarray,
    N_offset: float,
    alpha: float,
    H_sq_nl_init: float,
    grid,
    trajectory,
    potential,
    rfield_splines,
    rmom_splines,
    diffusion_model,
    disable_spatial_coupling: bool = False,
) -> np.ndarray:
    """
    Forward-sector RHS (eq. inst-phi/inst-pi), always sourced by the current
    response fields.

    rfield_splines/rmom_splines are one SplineWrapper per grid node (length
    n_max+1 each), reconstructing the current backward-pass response-field
    solution rfield_full(N)/rmom_full(N) at whatever N the forward integrator
    is currently at -- built by the caller (the Picard driver) from the most
    recent response_rhs solve. The all-zero-response "zeroth Picard iterate"
    is just a particular choice of these splines (constant zero), not a
    separate code path.

    disable_spatial_coupling=True zeroes both the gradient term and both
    advection contributions together -- zeroing only the gradient term would
    leave nodes coupled through advection (which doesn't vanish at the core),
    so the reduction to a decoupled single trajectory needs both zeroed at
    once. It does NOT zero the response-field sourcing terms, which remain
    active (matching FullInstanton's own fwd_rhs, which always includes its
    P1/P2 sourcing terms regardless of gradient coupling).
    """
    phi_full, pi_full = unpack_state(
        state, N, N_offset, alpha, H_sq_nl_init, grid, trajectory, potential
    )
    n_nodes = phi_full.shape[0]

    # Core-only Delta_s(N), defining the coordinate map itself. N is the
    # local, zero-based running coordinate, so N_init is always 0.0 here.
    H_sq_core = potential.H_sq(phi_full[-1], pi_full[-1])
    delta_s_N = delta_s(N, 0.0, H_sq_core, H_sq_nl_init, alpha)

    # Per-node H^2_loc, epsilon_loc, V' -- vectorized over the full array.
    H_sq_loc_array = potential.H_sq(phi_full, pi_full)
    epsilon_loc_array = potential.epsilon(phi_full, pi_full)
    dV_array = potential.dV_dphi(phi_full)

    # Per-node Delta_s_loc(y_j,N) -- needed both by the gradient-term
    # prefactor (when spatial coupling is enabled) and by n_count below
    # (always, regardless of disable_spatial_coupling), so this is computed
    # unconditionally rather than only inside the spatial-coupling branch.
    delta_s_loc_array = delta_s(N, 0.0, H_sq_loc_array, H_sq_nl_init, alpha)

    if disable_spatial_coupling:
        gradient_term = np.zeros_like(phi_full)
        advection_phi_array = np.zeros_like(phi_full)
        advection_pi_array = np.zeros_like(pi_full)
    else:
        L_phi_array = L_operator(phi_full, delta_s_N, grid.nodes, grid.D, grid.D2)
        gradient_term = np.exp(-2.0 * delta_s_loc_array) * L_phi_array

        A_array = advection_coefficient(grid.nodes, delta_s_N, epsilon_loc_array[-1])
        advection_phi_array = advection_term(phi_full, A_array, grid.D)
        advection_pi_array = advection_term(pi_full, A_array, grid.D)

    # Shell-dilution factor n_count(y_j,N) (eq. ncount), reusing delta_s_N
    # and delta_s_loc_array already computed above rather than recomputing
    # delta_s() a third time.
    n_count_array = (
        1.5 * delta_s_N
        * np.exp(3.0 * delta_s_loc_array)
        * np.exp(-1.5 * (grid.nodes + 1.0) * delta_s_N)
    )

    # Response-field values at the current N, reconstructed node-by-node from
    # the current backward-pass splines.
    rfield_full = np.array([spline(N) for spline in rfield_splines])
    rmom_full = np.array([spline(N) for spline in rmom_splines])

    # Diffusion matrix, per node -- D_matrix is scalar-only (confirmed via
    # MasslessDecoupledDiffusion's bare-float off-diagonal zeros, which would
    # not broadcast correctly over an array phi), so this is a Python-level
    # loop, not a vectorized call.
    D11_arr = np.empty(n_nodes)
    D12_arr = np.empty(n_nodes)
    D22_arr = np.empty(n_nodes)
    for j in range(n_nodes):
        D11_arr[j], D12_arr[j], D22_arr[j] = diffusion_model.D_matrix(
            phi_full[j], pi_full[j], potential
        )

    # Sourced (shell-diluted) noise coefficients (eq. Dnoise-diag, Dnoise-cross).
    D_phi_arr = 2.0 * D11_arr / n_count_array
    D_pi_arr = 2.0 * D22_arr / n_count_array
    D_phipi_arr = 2.0 * D12_arr / n_count_array

    dphi_full = (
        pi_full
        + advection_phi_array
        + D_phi_arr * rfield_full
        + D_phipi_arr * rmom_full
    )
    dpi_full = (
        -(3.0 - epsilon_loc_array) * pi_full
        - dV_array / H_sq_loc_array
        + gradient_term
        + advection_pi_array
        + D_pi_arr * rmom_full
        + D_phipi_arr * rfield_full
    )

    return pack_state(dphi_full, dpi_full)
