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
Discretized L operator, advection term, and Neumann hard elimination for the
gradient-coupled instanton model.

Standalone numerical module: plain functions, no shared state, depends on
numpy only -- no AbstractPotential, no InflatonTrajectory, no
DatastoreObject, nothing under Datastore/.

L_operator's own discretization uses only the single, core-only,
coordinate-defining Delta_s(N) (bare, no y-subscript) -- it applies no
1/r_out^2 or (aH)_loc-related scaling of any kind. That composition, using
the y-dependent Delta_s_loc(y,N), is a separate multiplicative prefactor
applied by the caller wherever L appears in the equations of motion.
"""

import numpy as np


def L_operator(
    f: np.ndarray,
    delta_s_N: float,
    y_nodes: np.ndarray,
    D: np.ndarray,
    D2: np.ndarray,
) -> np.ndarray:
    """
    (L f)_j = exp(delta_s_N) * exp(delta_s_N * y_j)
              * [ (4/delta_s_N**2)(D2 @ f)_j - (2/delta_s_N)(D @ f)_j ]

    delta_s_N is the single, core-only Delta_s(N) -- NOT a per-node value.
    Does not apply any 1/r_out^2 or (aH)_loc scaling; that composition
    happens in a later prompt.

    f must already have every boundary value resolved (Dirichlet
    assignment, Neumann elimination, or free dynamical value) before being
    passed in -- this function does no boundary handling itself.
    """
    prefactor = np.exp(delta_s_N) * np.exp(delta_s_N * y_nodes)
    bracket = (4.0 / delta_s_N**2) * (D2 @ f) - (2.0 / delta_s_N) * (D @ f)
    return prefactor * bracket


def advection_term(f: np.ndarray, A_array: np.ndarray, D: np.ndarray) -> np.ndarray:
    """
    A_array * (D @ f), elementwise. A_array is the precomputed
    advection_coefficient(y_nodes, delta_s_N, epsilon_core) array from
    Numerics/OnionCoordinate.py -- this function doesn't recompute it.

    f must already have every boundary value resolved before being passed
    in -- this function does no boundary handling itself.

    SUPERSEDED by advection_split_term for the production forward/response
    RHS (prompt 21a) -- see that function's docstring for why the plain
    product form is destabilizing under strong boundary elimination. Kept
    here (still used by tools/diagnostics/GradientCoupledInstanton/spectrum.py's strong-BC baseline
    operator, prompt 20) as the explicit "wrong/old" comparison point the
    SBP-SAT closure is measured against; do not use it in new production code.
    """
    return A_array * (D @ f)


def advection_split_matrix(A_array: np.ndarray, D: np.ndarray) -> np.ndarray:
    """
    A_split = 1/2 * (diag(A) @ D + D @ diag(A) - diag(D @ A)) -- the
    product-rule-consistent ("skew-symmetric split form") discretization of
    variable-coefficient advection A(y) du/dy, replacing the plain product
    diag(A) @ D used by advection_term.

    WHAT IT IS: continuum-identical to the plain product (both equal
    A(y) du/dy for smooth u -- substitute the continuum product rule
    (Au)_y = A_y u + A u_y into 1/2*(A u_y + (Au)_y - A_y u) and the extra
    terms cancel, leaving A u_y), but NOT identical as a matrix acting on
    grid functions: D only differentiates polynomials up to degree n_max
    exactly, so D @ diag(A) applied to a degree-n_max grid function
    differentiates an effectively degree-2*n_max object and picks up an
    aliasing residual relative to diag(A) @ D + diag(D @ A) -- the explicit
    "- diag(D @ A)" term corrects for exactly that residual.

    WHY IT IS HERE: this is what makes the discrete advection operator skew
    under the LGL quadrature norm H = diag(grid.weights), up to a single
    boundary term -- i.e. it restores the discrete mirror of the continuum
    energy identity dE/dN = 1/2 [A u^2]_{boundary} that the plain product
    form loses in the interior. The remaining boundary-localised term is
    exactly what the SAT penalty (see forward_rhs.py) is built to cancel.

    FAILURE SIGNATURE OF THE WRONG (plain-product) VERSION: this is not a
    hypothetical -- it is the documented history of this operator.
    Discretising with the plain product diag(A) @ D and STRONG (node-
    elimination) boundary conditions produces a semi-discrete spectrum whose
    abscissa grows like n_max^1.6 (integrator-independent -- RK45, Radau,
    BDF all fail; LSODA returns NaN with success=True), which is exactly the
    instability that made the GradientCoupledInstanton solve blow up for
    n_collocation_points >= 9 before this closure (prompt 17/20/21).

    ENERGY-ESTIMATE REFERENCE: .documents/gradient-coupled-instanton/
    21-sbp-sat-design-note.md, Section 3 ("Exact SBP defect of the
    split-form advection operator"). Ported here, unchanged in form, from
    the validated Phase-1 prototype (tools/diagnostics/GradientCoupledInstanton/spectrum.py's own
    advection_split_matrix) -- this IS the production home for that
    construction; the prototype's own copy is left in place as the frozen,
    independently-tested reference the Phase-1 gate was passed against.
    """
    return 0.5 * (
        np.diag(A_array) @ D + D @ np.diag(A_array) - np.diag(D @ A_array)
    )


def advection_split_term(f: np.ndarray, A_array: np.ndarray, D: np.ndarray) -> np.ndarray:
    """
    advection_split_matrix(A_array, D) @ f -- the split-form counterpart of
    advection_term, with the same (f, A_array, D) call signature so
    production call sites (forward_rhs.py) can swap one for the other
    directly. See advection_split_matrix's own docstring for the full
    what/why/failure-signature/energy-estimate account.

    f must already have every boundary value resolved before being passed
    in -- this function does no boundary handling itself (same contract as
    advection_term).
    """
    return advection_split_matrix(A_array, D) @ f


def neumann_boundary_value(f: np.ndarray, D: np.ndarray, boundary_index: int) -> float:
    """
    Returns the boundary node value f_b consistent with a homogeneous
    Neumann condition d f/dy = 0 at that node, i.e. solves
    sum_k D[boundary_index, k] * f[k] = 0 for f[boundary_index], using the
    OTHER entries of f (f[boundary_index] itself is ignored, not assumed
    correct on entry):

        f_b = -1/D[b,b] * sum_{k != b} D[b,k] * f[k]

    Returns a scalar; does not modify f. The only current use is
    boundary_index = -1 (the y=+1 / n_max node), but the index is kept as
    a parameter rather than hardcoded, since the formula itself doesn't
    care which row it's given.

    Does not build a modified/reduced differentiation matrix: this is the
    scalar-first-then-ordinary-D/D2 approach, mathematically equivalent to
    the classical reduced-D2 substitution but simpler to implement and
    verify.
    """
    row = D[boundary_index, :]
    diag = row[boundary_index]

    mask = np.ones(row.shape[0], dtype=bool)
    mask[boundary_index] = False

    return -np.sum(row[mask] * f[mask]) / diag
