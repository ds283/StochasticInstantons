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
    """
    return A_array * (D @ f)


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
