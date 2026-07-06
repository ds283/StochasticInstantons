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
MSR (Martin-Siggia-Rose) saddle-point action for the gradient-coupled
instanton model (eq. msr-action).

Sign convention -- worked out explicitly, not just "drop the linear terms":
substituting the forward EOM (eq:inst-phi/eq:inst-pi) back into
eq:msr-action's own linear-in-response-field terms does NOT make them vanish;
it turns each into a *positive* copy of the quadratic term it multiplies
(e.g. the rfield*(phidot - mom - ...) term becomes
rfield*(D_phi rfield + D_phipi rmom) = D_phi rfield^2 + D_phipi rfield rmom).
Combined with the quadratic term eq:msr-action already carries explicitly
(-D_phi/2 rfield^2 - D_phipi rfield rmom - D_pi/2 rmom^2), the net on-shell
integrand is

    +D_phi/2 rfield^2 + D_phipi rfield rmom + D_pi/2 rmom^2 ,

i.e. the OPPOSITE overall sign to a naive "just drop the linear terms and
keep eq:msr-action's own quadratic term as written" reading. This is the
only sign consistent with FullInstanton's own established, tested
convention (msr_action = +integral D11 P1^2 dN, never negative for a real
diffusion matrix) -- the reduction-limit test in
tests/test_msr_action.py cross-checks this directly.

So the on-shell action actually implemented here is

    S = +int dN int_{-1}^1 mu(y,N) dy [ D_phi/2 rfield^2
                                         + D_phipi rfield rmom
                                         + D_pi/2 rmom^2 ] .

This is the FULL three-term quadratic form, not just the single D_phi term
FullInstanton's own code computes (FullInstanton effectively has
D_phipi = D_pi = 0 identically, since MasslessDecoupledDiffusion.D_matrix
returns D12 = D22 = 0 -- the only diffusion model currently implemented).
Do NOT "simplify" this back down to one term by analogy with FullInstanton:
a future diffusion model with genuine off-diagonal structure needs all three
terms, or physics is silently dropped.

Quadrature strategy (settled in discussion, see prompt 15):
  - y-direction: grid.weights (LGL, spectrally accurate) against the
    self-adjoint measure mu(y,N) = Numerics.OnionCoordinate.measure.
  - N-direction: np.trapezoid over the dense solver grid, mirroring
    FullInstanton's own np.trapezoid(D11_arr * P1_f**2, N_grid) call as
    closely as possible.
"""

import numpy as np

from Numerics.OnionCoordinate import delta_s, measure
from ComputeTargets.GradientCoupledInstanton.forward_rhs import (
    diluted_diffusion_coefficients,
)


def y_quadrature(f_nodes: np.ndarray, grid, delta_s_N: float) -> float:
    """
    LGL-quadrature approximation to int_{-1}^1 mu(y,N) f(y) dy:
    sum_j w_j * mu(y_j,N) * f(y_j).

    Isolated as its own function -- independent of any physics input -- so
    "is the quadrature applied correctly" (grid.weights x measure x
    integrand, summed over nodes) can be tested against a synthetic
    integrand with a known closed-form integral, separately from "is the
    physics integrand correct".
    """
    return float(np.sum(grid.weights * measure(grid.nodes, delta_s_N) * f_nodes))


def msr_action_row_integrand(
    phi_row: np.ndarray,
    pi_row: np.ndarray,
    rfield_row: np.ndarray,
    rmom_row: np.ndarray,
    delta_s_N: float,
    delta_s_loc_array: np.ndarray,
    grid,
    potential,
    diffusion_model,
) -> np.ndarray:
    """
    Per-node contribution to the on-shell MSR action's y-integrand at one
    N-row -- see this module's own docstring for the sign derivation:

        +[ D_phi/2 rfield^2 + D_phipi rfield rmom + D_pi/2 rmom^2 ]

    evaluated at every node of the (already shell-diluted) diffusion
    coefficients D_phi/D_phipi/D_pi (forward_rhs.diluted_diffusion_coefficients
    -- the same coefficients that dress rfield/rmom in forward_rhs's own
    sourcing terms). The mu(y,N) measure and grid.weights quadrature are
    NOT applied here -- that is compute_msr_action's own job (or a test's,
    for the isolated quadrature-contraction check) -- this function returns
    only the bracketed integrand itself, per node.

    Returns an array shape (n_nodes,).
    """
    D_phi_arr, D_pi_arr, D_phipi_arr = diluted_diffusion_coefficients(
        phi_row, pi_row, delta_s_N, delta_s_loc_array, grid, potential, diffusion_model,
    )
    return (
        0.5 * D_phi_arr * rfield_row ** 2
        + D_phipi_arr * rfield_row * rmom_row
        + 0.5 * D_pi_arr * rmom_row ** 2
    )


def compute_msr_action(
    N_grid: np.ndarray,
    phi_grid: np.ndarray,
    pi_grid: np.ndarray,
    rfield_grid: np.ndarray,
    rmom_grid: np.ndarray,
    grid,
    potential,
    diffusion_model,
    H_sq_nl_init: float,
    alpha: float,
) -> float:
    """
    S_MSR = +int dN int_{-1}^1 mu(y,N) dy [ D_phi/2 rfield^2
                                             + D_phipi rfield rmom
                                             + D_pi/2 rmom^2 ]
    (eq. msr-action, on-shell -- see this module's own docstring for why the
    sign is "+", not the naive "-" of eq:msr-action's own explicit quadratic
    term alone).

    phi_grid/pi_grid/rfield_grid/rmom_grid each have shape
    (len(N_grid), n_collocation_points) -- solve_picard's own dense-grid
    output (every row of the dense solver grid, not just the final one).

    delta_s_N(N)/delta_s_loc(y,N) are recomputed at every row from that
    row's own core/per-node (phi,pi) state, reusing Numerics.OnionCoordinate
    .delta_s -- Delta_s(N) genuinely evolves across the transition, it is
    not pinned to its final-row value.

    Two-stage, vectorized reduction: build the full
    (len(N_grid), n_collocation_points) integrand array once (the D_matrix
    lookup inside diluted_diffusion_coefficients is scalar-only, so this
    stage is a per-row Python loop, mirroring the same loop structure
    already used by GradientCoupledInstanton.py's own per-row noise-stats
    computation), then contract the node axis in one vectorized
    grid.weights-dot-product step, then np.trapezoid the resulting 1D
    array over N_grid -- mirroring FullInstanton's own
    np.trapezoid(D11_arr * P1_f**2, N_grid) call as closely as the
    grid-valued generalization allows.
    """
    N_grid = np.asarray(N_grid)
    phi_grid = np.asarray(phi_grid)
    pi_grid = np.asarray(pi_grid)
    rfield_grid = np.asarray(rfield_grid)
    rmom_grid = np.asarray(rmom_grid)

    n_rows = len(N_grid)
    n_nodes = grid.n_collocation_points

    integrand_grid = np.empty((n_rows, n_nodes))
    mu_grid = np.empty((n_rows, n_nodes))

    for i in range(n_rows):
        N_i = float(N_grid[i])
        phi_row = phi_grid[i]
        pi_row = pi_grid[i]

        H_sq_core_i = potential.H_sq(phi_row[-1], pi_row[-1])
        delta_s_N_i = delta_s(N_i, 0.0, H_sq_core_i, H_sq_nl_init, alpha)

        H_sq_loc_i = potential.H_sq(phi_row, pi_row)
        delta_s_loc_i = delta_s(N_i, 0.0, H_sq_loc_i, H_sq_nl_init, alpha)

        integrand_grid[i] = msr_action_row_integrand(
            phi_row, pi_row, rfield_grid[i], rmom_grid[i],
            delta_s_N_i, delta_s_loc_i, grid, potential, diffusion_model,
        )
        mu_grid[i] = measure(grid.nodes, delta_s_N_i)

    # y-quadrature: contract the node axis via the grid.weights-and-mu
    # product, vectorized over every N-row at once.
    y_integral = (mu_grid * integrand_grid) @ grid.weights

    # N-quadrature: plain trapezoid over solve_picard's own dense N_grid.
    return float(np.trapezoid(y_integral, N_grid))
