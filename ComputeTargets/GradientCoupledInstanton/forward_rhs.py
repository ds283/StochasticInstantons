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
model, response fields identically zero (the "zeroth Picard iterate").

Unlike Numerics/, which is deliberately physics-free, this is the first module
in the GradientCoupledInstanton subpackage allowed to depend directly on
AbstractPotential and InflatonTrajectory -- this is where physics and the
Numerics/ collocation machinery meet.

State vector layout. Not all 2(n_max+1) raw grid values are independently
integrated:

  - phi_0, pi_0 (outer edge, y=-1): Dirichlet-pinned to
    trajectory.phi_before_end(N)/.pi_before_end(N) -- not integrated,
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
    N_init: float,
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
    trajectory.phi_before_end(N)/.pi_before_end(N).

    Index n_max (y=+1): pi_full[n_max] is the free, integrated core
    momentum, taken directly from the state vector. phi_full[n_max] is
    Neumann-eliminated via neumann_boundary_value, using the just-assembled
    phi_full (every index other than the boundary one is already correct;
    neumann_boundary_value ignores whatever placeholder sits at the boundary
    index itself).

    N_init, alpha, H_sq_nl_init, and potential are threaded through for a
    signature shared with forward_rhs's local context; unpack_state itself
    does not need them.
    """
    n_max = grid.n_max

    phi_full = np.empty(n_max + 1)
    pi_full = np.empty(n_max + 1)

    phi_full[0] = trajectory.phi_before_end(N)
    pi_full[0] = trajectory.pi_before_end(N)

    n_phi_interior = n_max - 1
    phi_full[1:n_max] = state[:n_phi_interior]
    pi_full[1:n_max + 1] = state[n_phi_interior:n_phi_interior + n_max]

    phi_full[-1] = neumann_boundary_value(phi_full, grid.D, boundary_index=-1)

    return phi_full, pi_full


def forward_rhs(
    N: float,
    state: np.ndarray,
    N_init: float,
    alpha: float,
    H_sq_nl_init: float,
    grid,
    trajectory,
    potential,
    disable_spatial_coupling: bool = False,
) -> np.ndarray:
    """
    Forward-sector RHS (eq. inst-phi/inst-pi), response fields zero.

    disable_spatial_coupling=True zeroes both the gradient term and both
    advection contributions together -- zeroing only the gradient term would
    leave nodes coupled through advection (which doesn't vanish at the core),
    so the reduction to a decoupled single trajectory needs both zeroed at
    once.
    """
    phi_full, pi_full = unpack_state(
        state, N, N_init, alpha, H_sq_nl_init, grid, trajectory, potential
    )

    # Core-only Delta_s(N), defining the coordinate map itself.
    H_sq_core = potential.H_sq(phi_full[-1], pi_full[-1])
    delta_s_N = delta_s(N, N_init, H_sq_core, H_sq_nl_init, alpha)

    # Per-node H^2_loc, epsilon_loc, V' -- vectorized over the full array.
    H_sq_loc_array = potential.H_sq(phi_full, pi_full)
    epsilon_loc_array = potential.epsilon(phi_full, pi_full)
    dV_array = potential.dV_dphi(phi_full)

    if disable_spatial_coupling:
        gradient_term = np.zeros_like(phi_full)
        advection_phi_array = np.zeros_like(phi_full)
        advection_pi_array = np.zeros_like(pi_full)
    else:
        L_phi_array = L_operator(phi_full, delta_s_N, grid.nodes, grid.D, grid.D2)

        # Per-node Delta_s_loc(y_j,N), using the full H^2_loc array.
        delta_s_loc_array = delta_s(N, N_init, H_sq_loc_array, H_sq_nl_init, alpha)
        gradient_term = np.exp(-2.0 * delta_s_loc_array) * L_phi_array

        A_array = advection_coefficient(grid.nodes, delta_s_N, epsilon_loc_array[-1])
        advection_phi_array = advection_term(phi_full, A_array, grid.D)
        advection_pi_array = advection_term(pi_full, A_array, grid.D)

    dphi_full = pi_full + advection_phi_array
    dpi_full = (
        -(3.0 - epsilon_loc_array) * pi_full
        - dV_array / H_sq_loc_array
        + gradient_term
        + advection_pi_array
    )

    return pack_state(dphi_full, dpi_full)
