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
Response-sector collocation right-hand side for the gradient-coupled
instanton model (eq. inst-rphi/inst-rpi, discretized as the response rows of
eq. colloc-eqs), plus the terminal-condition construction at N_final
(eq. terminal-colloc).

State vector layout. Mirrors the forward sector structurally (same total
length, same style of Dirichlet/Neumann/free split), but the roles of the
two fields are swapped relative to forward_rhs.py -- get this right, it is
not a copy-paste of the forward layout:

  - rfield_0, rmom_0 (outer edge, y=-1): both pinned to exactly zero -- no
    trajectory lookup needed, unlike the forward sector's Dirichlet row.
  - rmom_{n_max} (core momentum-response): Neumann-eliminated via
    neumann_boundary_value (boundary_index=-1) -- not integrated.
  - rfield_{n_max} (core field-response): genuinely free, is integrated --
    this is the node that carries the terminal condition.
  - Everything else -- i.e. the full integrated set -- is
    rfield_1,...,rfield_{n_max} and rmom_1,...,rmom_{n_max-1}.

So the ODE state vector has length 2*n_max - 1, same total as the forward
sector, but laid out as:
(rfield_1,...,rfield_{n_max}, rmom_1,...,rmom_{n_max-1}).

In the forward sector phi was eliminated at the core and pi was free; here
it is the opposite -- rmom eliminated, rfield free. The gradient term in
the rfield equation applies L to rmom (not rfield) -- self-adjointness of L
moves the operator onto the other response field; this is not a typo
relative to the forward sector's L(phi).
"""

import numpy as np

from Numerics.OnionCoordinate import delta_s, advection_coefficient, measure
from Numerics.DiscretizedOperators import (
    L_operator,
    advection_term,
    neumann_boundary_value,
)


def pack_response_state(rfield_full: np.ndarray, rmom_full: np.ndarray) -> np.ndarray:
    """
    Restrict (rfield_full, rmom_full), each of length n_max+1, to the
    integrated state vector of length 2*n_max-1:
    (rfield_1,...,rfield_{n_max}, rmom_1,...,rmom_{n_max-1}).

    Drops rfield_full[0]/rmom_full[0] (both pinned to zero) and
    rmom_full[-1] (Neumann-eliminated). Note this keeps rfield_full[-1]
    (the core, free) but drops rmom_full[-1] (the core, eliminated) -- the
    reverse of pack_state's treatment of phi/pi.
    """
    n_max = len(rfield_full) - 1
    return np.concatenate([rfield_full[1:n_max + 1], rmom_full[1:n_max]])


def unpack_response_state(state: np.ndarray, grid) -> tuple[np.ndarray, np.ndarray]:
    """
    Expand the integrated response state vector back to the full-length
    (rfield_full, rmom_full) grid arrays, each of length n_max+1.

    Index 0 (y=-1): both pinned to exactly zero -- trivial, no lookup.

    Index n_max (y=+1): rfield_full[n_max] is the free, integrated core
    field-response, taken directly from the state vector. rmom_full[n_max]
    is Neumann-eliminated via neumann_boundary_value, using the
    just-assembled rmom_full (every index other than the boundary one is
    already correct; neumann_boundary_value ignores whatever placeholder
    sits at the boundary index itself).
    """
    n_max = grid.n_max

    rfield_full = np.empty(n_max + 1)
    rmom_full = np.empty(n_max + 1)

    rfield_full[0] = 0.0
    rmom_full[0] = 0.0

    n_rfield_free = n_max
    rfield_full[1:n_max + 1] = state[:n_rfield_free]
    rmom_full[1:n_max] = state[n_rfield_free:n_rfield_free + (n_max - 1)]

    rmom_full[-1] = neumann_boundary_value(rmom_full, grid.D, boundary_index=-1)

    return rfield_full, rmom_full


def _c_of_N(epsilon_core: float, delta_s_N: float) -> float:
    """
    c(N) = (1 - epsilon_core(N)) * [1/Delta_s(N) - 1.5].

    A single scalar per N -- the y-dependence that would otherwise appear
    here cancels exactly between the advective-adjoint term and a
    previously-missing measure-derivative term (see the tex's calculation
    panel); this is an exact simplification, not an approximation. Callers
    must apply the return value identically to every node, not recompute
    it per node.
    """
    return (1.0 - epsilon_core) * (1.0 / delta_s_N - 1.5)


def _assemble_response_derivatives(
    rfield_full: np.ndarray,
    rmom_full: np.ndarray,
    d2V_array: np.ndarray,
    H_sq_loc_array: np.ndarray,
    epsilon_loc_array: np.ndarray,
    c_N: float,
    gradient_term: np.ndarray,
    advection_rfield_array: np.ndarray,
    advection_rmom_array: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Final assembly step of the response-sector equations of motion, given
    every already-computed per-node array and the single scalar c(N).

    gradient_term is the fully-composed
    exp(-2*Delta_s_loc(y,N)) * (L rmom) contribution (sign already applied
    as it enters drfield_full below); advection_rfield_array/
    advection_rmom_array are advection_term(...) applied to rfield/rmom
    respectively. Factored out from response_rhs so the reduction-limit
    cross-check can call it directly with these three arguments zeroed,
    rather than needing to contrive a field configuration for which the
    gradient/advection contributions vanish identically.
    """
    drfield_full = (
        advection_rfield_array
        + rfield_full * c_N
        + d2V_array / H_sq_loc_array * rmom_full
        - gradient_term
    )
    drmom_full = (
        advection_rmom_array
        + rmom_full * c_N
        - rfield_full
        + (3.0 - epsilon_loc_array) * rmom_full
    )
    return drfield_full, drmom_full


def response_rhs(
    N: float,
    response_state: np.ndarray,
    alpha: float,
    H_sq_nl_init: float,
    grid,
    phi_splines,
    pi_splines,
    potential,
) -> np.ndarray:
    """
    Response-sector RHS (eq. inst-rphi/inst-rpi, discretized as the response
    rows of eq. colloc-eqs).

    phi_splines/pi_splines are one SplineWrapper per grid node (length
    n_max+1 each), reconstructing the current forward-pass solution
    phi_full(N)/pi_full(N) at whatever N the backward integrator is
    currently at. Building this list of splines from a stored forward
    solution is the caller's job (the Picard driver); this function just
    consumes them.

    N is the local, zero-based running coordinate shared with forward_rhs
    (0.0 at the transition start, N_total at the transition end -- see
    picard.py's module docstring), so every delta_s() call below passes a
    literal 0.0 for N_init. Integrated backward in N from N_total down to
    0.0, same convention as FullInstanton's bwd_rhs: this function itself
    still computes the literal d/dN derivative (forward sense); it is
    solve_ivp's t_span that runs in reverse, handled by the caller. Unlike
    forward_rhs, response_rhs has no trajectory dependency (the outer-edge
    response condition is a trivial constant zero), so it needs no
    N_offset parameter.
    """
    phi_full = np.array([spline(N) for spline in phi_splines])
    pi_full = np.array([spline(N) for spline in pi_splines])

    rfield_full, rmom_full = unpack_response_state(response_state, grid)

    # Core-only Delta_s(N), defining the coordinate map itself.
    H_sq_core = potential.H_sq(phi_full[-1], pi_full[-1])
    delta_s_N = delta_s(N, 0.0, H_sq_core, H_sq_nl_init, alpha)

    epsilon_core = potential.epsilon(phi_full[-1], pi_full[-1])
    c_N = _c_of_N(epsilon_core, delta_s_N)

    # Per-node H^2_loc, epsilon_loc, V'' -- vectorized over the full array.
    H_sq_loc_array = potential.H_sq(phi_full, pi_full)
    epsilon_loc_array = potential.epsilon(phi_full, pi_full)
    d2V_array = potential.d2V_dphi2(phi_full)

    # Gradient term: L applied to rmom (not rfield) -- self-adjointness of L
    # moves the operator onto the other response field.
    L_rmom_array = L_operator(rmom_full, delta_s_N, grid.nodes, grid.D, grid.D2)
    delta_s_loc_array = delta_s(N, 0.0, H_sq_loc_array, H_sq_nl_init, alpha)
    gradient_term = np.exp(-2.0 * delta_s_loc_array) * L_rmom_array

    A_array = advection_coefficient(grid.nodes, delta_s_N, epsilon_core)
    advection_rfield_array = advection_term(rfield_full, A_array, grid.D)
    advection_rmom_array = advection_term(rmom_full, A_array, grid.D)

    drfield_full, drmom_full = _assemble_response_derivatives(
        rfield_full,
        rmom_full,
        d2V_array,
        H_sq_loc_array,
        epsilon_loc_array,
        c_N,
        gradient_term,
        advection_rfield_array,
        advection_rmom_array,
    )

    return pack_response_state(drfield_full, drmom_full)


def terminal_response_state(lam: float, grid, delta_s_N_final: float) -> np.ndarray:
    """
    Builds the response state vector at N_final: all zeros except
    rfield_{n_max} = -lam / (grid.weights[-1] * measure(1.0, delta_s_N_final)).

    Uses grid.weights[-1] directly (already validated against the closed
    form 2/[n_max(n_max+1)] in prompt 01's tests) rather than recomputing it.
    """
    n_max = grid.n_max

    rfield_full = np.zeros(n_max + 1)
    rmom_full = np.zeros(n_max + 1)

    rfield_full[-1] = -lam / (grid.weights[-1] * measure(1.0, delta_s_N_final))

    return pack_response_state(rfield_full, rmom_full)
