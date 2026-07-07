#!/usr/bin/env python3
"""
analyze_StiffnessSpectrum.py

Standalone assembled-operator eigenvalue sweep for the gradient-coupled
("onion model") instanton solver (prompt 17, Part A).

`onion_model_implementation_review.md` measured the bare LGL D2 operator's
own spectrum and found it grows like O(n_max^4) with comparable real and
imaginary eigenvalue parts -- but that table overstates the model's actual
stiffness, because the real ODE right-hand side (forward_rhs.py) never
applies D2 alone: it dresses the second-derivative term with physics
prefactors (4/Delta_s^2 * exp(Delta_s) * exp(Delta_s*y) inside L_operator,
the exp(-2*Delta_s_loc) gradient prefactor, and the advection coefficient)
and folds in the Neumann hard-elimination boundary treatment before RK45
ever sees it. This script assembles *that* operator -- the linearised map
the free-DOF state vector actually experiences per forward_rhs call, at a
frozen (N, n_max, alpha) point -- and reports its eigenvalues, so a stability
envelope can be read off before trusting any n_max convergence scan.

Frozen-coefficient construction, no InflatonTrajectory/AbstractPotential
needed: Delta_s(N) = ln(1+alpha) + N + 0.5*ln(H_sq_local/H_sq_nl_init), and
this script always evaluates it at H_sq_local/H_sq_nl_init == 1 everywhere
(a uniform-H^2 shell) -- so Delta_s(N) is reached simply by choosing N and
alpha directly, without needing a real background trajectory. This is a
deliberate simplification: the O(n_max^4) stiffness this script
characterizes comes from the L_operator/advection matrices themselves, not
from any particular potential's H_sq(phi, pi) profile, so a representative,
potential-independent frozen point is sufficient to map out the stability
envelope. A fixed, representative epsilon_core (--epsilon-core, default
0.01, a typical slow-roll value) feeds the advection coefficient the same
way.

Self-check (assemble_spatial_operator vs finite_difference_spatial_jacobian,
wired together by self_check_assembled_operator): confirms the frozen-
coefficient assembly matches a central finite-difference Jacobian of the
REAL forward_rhs's spatial-only part (isolated via forward_rhs's own
disable_spatial_coupling flag: forward_rhs(disable_spatial_coupling=False) -
forward_rhs(disable_spatial_coupling=True), which exactly cancels every
term outside the gradient/advection branch -- the damping/potential/noise
terms are identical in both calls since they sit outside that branch).
The finite-difference check uses a potential whose H_sq/epsilon are
constants (independent of phi/pi) matching this script's own frozen-
coefficient assumption -- with a *real*, phi-dependent potential, the
finite-difference Jacobian would legitimately pick up extra chain-rule
terms from H_sq's own state-dependence that this script's frozen
construction does not model, and the two would only agree to leading order
in the perturbation rather than to numerical precision.

Out of scope (per prompt 17): consuming this CSV in a further analysis
script, any integrator change (e.g. switching to Radau), the SBP+SAT
fallback. This script only measures.

Prompt 18 adds a second, standalone diagnostic (`--mode adjoint`): whether
the discretised forward/response spatial operators preserve the continuum
adjoint structure the MSR action's stationarity relies on. This measures
DISCRETE VARIATIONAL CONSISTENCY, not correctness -- a nonzero mismatch is
EXPECTED for strong-form collocation (which gets its accuracy from small
nodal residuals, not from discrete adjointness) and is NOT evidence of a
derivation error. Its purpose is to inform the weighted-SBP/SAT decision
flagged in `onion_model_planning.md`'s cross-checks, not to gate
correctness. Also frozen-uniform-H^2 (a real, phi/pi-dependent H_sq(N)
profile is out of scope here, same simplification as `--mode spectrum`).

Prompt 18a amends two of prompt 18's metrics, both metric-definition fixes,
not physics changes:

- `L_selfadj` is redefined inversion-free, `||W L - (W L)^T|| / ||W L||`
  (never forming `W^{-1}`, whose condition number is `exp(3*delta_s)` and
  which made the original `||W^{-1} L^T W - L|| / ||L||` form blow up to pure
  roundoff beyond delta_s~5).
- The `*_eliminated` columns are dropped (they were a role-swapped-elimination
  artifact -- `block_mismatch_gradient_eliminated` collapsed to exactly
  sqrt(2) for every row, independent of any physics). In their place, every
  full-node metric (`L_selfadj` and the three `block_mismatch_*`) gets an
  `*_interior` companion, computed by masking the two boundary nodes
  (y=+-1) out of both the numerator and denominator Frobenius norms. The
  interior/boundary split cleanly separates two different situations: the
  **gradient** operator is bulk spectrally adjoint-consistent under mu (its
  interior residual -> 0 as n_max grows) with an O(1) mismatch that is pure
  boundary -- if that needs fixing, the instrument is a SAT boundary penalty,
  not a bulk operator replacement. The **advection** operator instead shows
  an O(1) *bulk* mismatch at production delta_s that does not vanish in the
  interior -- a genuine operator-level discrepancy between the isolated
  advection-only forward/response comparison, that this diagnostic cannot by
  itself attribute to a missing response-sector term versus an inherently
  ill-posed isolation (advection's true adjoint partner may be distributed
  across the non-spatial couplings excluded from this comparison).

Usage:
    python3 analyze_StiffnessSpectrum.py --output stiffness_spectrum.csv
    python3 analyze_StiffnessSpectrum.py --n-max 8,16,32,64,128 --alpha 0.001,0.05 \
        --N 0.1,5,20,25 --plot
    python3 analyze_StiffnessSpectrum.py --mode adjoint --output adjoint_diagnostic.csv
"""

import argparse
import csv
import sys
from pathlib import Path

import numpy as np

from ComputeTargets.GradientCoupledInstanton.forward_rhs import (
    pack_state,
    forward_rhs,
)
from ComputeTargets.GradientCoupledInstanton.response_rhs import _c_of_N
from Numerics.DiscretizedOperators import (
    L_operator,
    advection_term,
    neumann_boundary_value,
)
from Numerics.LGLCollocation import LGLCollocationGrid
from Numerics.OnionCoordinate import advection_coefficient, delta_s, measure

VERSION_LABEL = "2026.3.0"

# RK45's absolute-stability boundary along the negative real axis reaches out
# to about |lambda|*dt ~ 2.8 -- a rough guide only. For a genuinely complex
# spectrum (as Section 5.2 of onion_model_implementation_review.md found:
# comparable real and imaginary eigenvalue parts) the true stable region is
# an egg-shaped patch of the complex plane, not a disc, so the implied
# max step this script reports is an order-of-magnitude indicator, not a
# rigorous bound.
RK45_REAL_AXIS_STABILITY_RADIUS = 2.8

DEFAULT_EPSILON_CORE = 0.01
_FD_EPS = 1.0e-6

DEFAULT_N_MAX_VALUES = [8, 16, 32, 64, 128, 192]
DEFAULT_ALPHA_VALUES = [1.0e-4, 1.0e-3, 1.0e-2, 0.05, 0.1]
# Reaches both regimes prompt 17 calls out explicitly: N ~ 0.01 near the
# alpha-regularized N_init coordinate singularity, and N ~ 20-25 (with
# delta_s_N = ln(1+alpha) + N) landing in the wide-transition
# Delta_s ~ 20 regime.
DEFAULT_N_VALUES = [0.01, 0.1, 1.0, 5.0, 10.0, 15.0, 20.0, 25.0]

CSV_FIELDNAMES = [
    "n_max", "alpha", "N", "delta_s_N", "op_norm",
    "max_abs_re_lambda", "max_abs_im_lambda", "implied_rk45_max_dt",
]

ADJOINT_CSV_FIELDNAMES = [
    "n_max", "alpha", "N", "delta_s_N", "sbp_residual",
    "L_selfadj", "L_selfadj_interior",
    "block_mismatch_full", "block_mismatch_full_interior",
    "block_mismatch_advection", "block_mismatch_advection_interior",
    "block_mismatch_gradient", "block_mismatch_gradient_interior",
]


# ---------------------------------------------------------------------------
# Assembled operator (frozen-coefficient, direct linear application)
# ---------------------------------------------------------------------------


def assemble_spatial_operator(
    n_max: int, alpha: float, N: float, epsilon_core: float = DEFAULT_EPSILON_CORE,
):
    """
    Assembles the linearised spatial operator -- gradient term (L_operator,
    dressed with its exp(-2*Delta_s_loc) prefactor) plus both advection
    terms, with Neumann elimination folded in -- that the free-DOF state
    vector actually sees per forward_rhs call, at a frozen (N, n_max, alpha)
    point. Excludes the trivial dphi/dN = pi identity coupling and every
    potential/noise/damping term (these are exactly the terms
    forward_rhs's own disable_spatial_coupling=True zeroes; see module
    docstring's finite-difference self-check for why that split is the
    right one to isolate the O(n_max^4)-growing part).

    Frozen-coefficient: Delta_s(N) and the per-node Delta_s_loc(y, N) are
    evaluated once via the real delta_s() formula with
    H_sq_local/H_sq_nl_init held at ratio 1 everywhere (see module
    docstring), so both are then held fixed while L_operator/advection_term
    are applied to each unit basis vector of the (2*n_max-1)-length free-DOF
    state -- matching forward_rhs.pack_state/unpack_state's own layout, with
    the Dirichlet-pinned boundary (phi_full[0]/pi_full[0]) held at zero
    (its true, non-zero value is a fixed additive offset from the
    background trajectory -- not part of the state-dependent linear map).

    Returns (A, delta_s_N): the assembled matrix, shape
    (2*n_max-1, 2*n_max-1), and the scalar Delta_s(N) used to build it.
    """
    grid = LGLCollocationGrid(n_max + 1)
    n_state = 2 * n_max - 1

    delta_s_N = float(delta_s(N, 0.0, 1.0, 1.0, alpha))
    delta_s_loc_array = delta_s(N, 0.0, np.ones(n_max + 1), 1.0, alpha)
    A_array = advection_coefficient(grid.nodes, delta_s_N, epsilon_core)

    def _spatial_rhs(state: np.ndarray) -> np.ndarray:
        phi_full = np.empty(n_max + 1)
        pi_full = np.empty(n_max + 1)
        phi_full[0] = 0.0
        pi_full[0] = 0.0
        n_phi_interior = n_max - 1
        phi_full[1:n_max] = state[:n_phi_interior]
        pi_full[1:n_max + 1] = state[n_phi_interior:n_phi_interior + n_max]
        phi_full[-1] = neumann_boundary_value(phi_full, grid.D, boundary_index=-1)

        L_phi_array = L_operator(phi_full, delta_s_N, grid.nodes, grid.D, grid.D2)
        gradient_term = np.exp(-2.0 * delta_s_loc_array) * L_phi_array
        advection_phi_array = advection_term(phi_full, A_array, grid.D)
        advection_pi_array = advection_term(pi_full, A_array, grid.D)

        dphi_full = advection_phi_array
        dpi_full = gradient_term + advection_pi_array
        return pack_state(dphi_full, dpi_full)

    matrix = np.column_stack([_spatial_rhs(e) for e in np.eye(n_state)])
    return matrix, delta_s_N


# ---------------------------------------------------------------------------
# Finite-difference self-check (real forward_rhs, frozen-coefficient stub potential)
# ---------------------------------------------------------------------------


class _FrozenCoefficientPotential:
    """
    Potential stand-in for the self-check ONLY: H_sq and epsilon are
    constants, independent of (phi, pi), so forward_rhs's own
    Delta_s_N/Delta_s_loc/advection-coefficient prefactors are exactly
    state-independent -- matching assemble_spatial_operator's frozen-
    coefficient assumption exactly rather than merely approximately. (A
    genuinely phi/pi-dependent potential would make forward_rhs's true
    spatial-only Jacobian pick up extra chain-rule terms from the
    coefficients' own state-dependence, which assemble_spatial_operator
    deliberately does not model.) dV_dphi is still phi-dependent -- it
    cancels exactly between the disable_spatial_coupling=True/False
    forward_rhs calls regardless of its form, so its shape doesn't matter.
    """

    def __init__(self, H_sq_value: float, epsilon_value: float, m_sq: float = 1.3):
        self._H_sq_value = H_sq_value
        self._epsilon_value = epsilon_value
        self._m_sq = m_sq

    def dV_dphi(self, phi):
        return self._m_sq * np.asarray(phi)

    def H_sq(self, phi, pi):
        phi = np.asarray(phi, dtype=float)
        return self._H_sq_value * np.ones_like(phi)

    def epsilon(self, phi, pi):
        pi = np.asarray(pi, dtype=float)
        return self._epsilon_value * np.ones_like(pi)


class _ConstSpline:
    """Callable returning a fixed value regardless of N -- stands in for a
    SplineWrapper wherever forward_rhs only needs `spline(N)`."""

    def __init__(self, value: float):
        self._value = value

    def __call__(self, N):
        return self._value


class _FrozenTrajectory:
    """Dirichlet-boundary stand-in: fixed phi/pi at the outer edge,
    independent of N -- its contribution cancels identically between the
    two disable_spatial_coupling branches (it sits outside that branch in
    forward_rhs), so any fixed value works."""

    def __init__(self, phi0: float, pi0: float):
        self._phi0 = phi0
        self._pi0 = pi0

    def phi_at(self, N):
        return self._phi0

    def pi_at(self, N):
        return self._pi0


class _ConstDiffusion:
    """D_matrix returns fixed, nonzero coefficients so noise_source_terms is
    exercised identically in both disable_spatial_coupling branches (and
    hence cancels exactly in their difference) rather than trivially
    skipped."""

    def D_matrix(self, phi, pi, potential):
        return 0.5, 0.1, 0.2


def finite_difference_spatial_jacobian(
    n_max: int, alpha: float, N: float,
    phi0: float = 0.3, pi0: float = -0.05,
    epsilon_core: float = DEFAULT_EPSILON_CORE, fd_eps: float = _FD_EPS,
) -> np.ndarray:
    """
    Self-check companion to assemble_spatial_operator: computes the Jacobian
    of forward_rhs's own spatial-only contribution by central finite
    differences of the REAL forward_rhs function (not a hand-transcribed
    formula) at the same (n_max, alpha, N) point.

    Isolates the spatial-only part exactly as forward_rhs's own
    disable_spatial_coupling flag defines it:
    forward_rhs(disable_spatial_coupling=False) -
    forward_rhs(disable_spatial_coupling=True), evaluated at the same
    state/N/splines. Every term outside that flag's branch
    (noise_source_terms, the -(3-eps)*pi damping, dV_dphi/H_sq) is computed
    identically in both calls from the same phi_full/pi_full, so it cancels
    exactly in the subtraction, leaving only gradient_term +
    advection_phi_array + advection_pi_array -- the same quantity
    assemble_spatial_operator builds directly, up to the two constructions'
    differing treatment of coefficient state-dependence (see
    _FrozenCoefficientPotential's own docstring for why that residual is
    suppressed here).

    Base state built from a uniform (phi0, pi0) with the Dirichlet-pinned
    boundary held at the SAME (phi0, pi0) -- so at the base point
    H_sq_loc/H_sq_nl_init is exactly ratio 1 everywhere, matching
    assemble_spatial_operator's own frozen assumption exactly at that point
    (perturbations away from it are what the two constructions can
    legitimately disagree about, suppressed here via the constant-H_sq/
    epsilon stub potential).
    """
    grid = LGLCollocationGrid(n_max + 1)
    n_state = 2 * n_max - 1

    H_sq_nl_init = 1.0
    potential = _FrozenCoefficientPotential(H_sq_value=H_sq_nl_init, epsilon_value=epsilon_core)
    trajectory = _FrozenTrajectory(phi0, pi0)
    dm = _ConstDiffusion()
    zero_splines = [_ConstSpline(0.0) for _ in range(n_max + 1)]
    N_offset = 0.0

    state0 = pack_state(np.full(n_max + 1, phi0), np.full(n_max + 1, pi0))

    def _spatial_only(state: np.ndarray) -> np.ndarray:
        full = forward_rhs(
            N, state, N_offset, alpha, H_sq_nl_init, grid, trajectory, potential,
            zero_splines, zero_splines, dm, disable_spatial_coupling=False,
        )
        no_coupling = forward_rhs(
            N, state, N_offset, alpha, H_sq_nl_init, grid, trajectory, potential,
            zero_splines, zero_splines, dm, disable_spatial_coupling=True,
        )
        return full - no_coupling

    jacobian = np.empty((n_state, n_state))
    for k in range(n_state):
        e_k = np.zeros(n_state)
        e_k[k] = fd_eps
        jacobian[:, k] = (_spatial_only(state0 + e_k) - _spatial_only(state0 - e_k)) / (2.0 * fd_eps)

    return jacobian


def self_check_assembled_operator(
    n_max: int, alpha: float, N: float, epsilon_core: float = DEFAULT_EPSILON_CORE,
    fd_eps: float = _FD_EPS,
) -> float:
    """
    Returns the max elementwise absolute difference between
    assemble_spatial_operator's frozen-coefficient matrix and
    finite_difference_spatial_jacobian's finite-difference Jacobian of the
    real forward_rhs, at the same (n_max, alpha, N, epsilon_core) point --
    the self-check the acceptance criteria ask for.
    """
    matrix, _ = assemble_spatial_operator(n_max, alpha, N, epsilon_core)
    jacobian = finite_difference_spatial_jacobian(n_max, alpha, N, epsilon_core=epsilon_core, fd_eps=fd_eps)
    return float(np.max(np.abs(matrix - jacobian)))


# ---------------------------------------------------------------------------
# Discrete adjoint-consistency diagnostic (prompt 18, metric fixes in 18a)
#
# Measurement only, sibling to the eigenvalue sweep above: assembles the
# frozen-coefficient forward and response spatial operators the solver
# actually applies (full-node, i.e. pre-elimination -- see prompt 18a for why
# the eliminated representation was dropped), and reports how far each is
# from the continuum adjoint structure the MSR action's stationarity
# assumes, both across the whole node set and restricted to the interior
# (masking the two boundary nodes y=+-1) so the boundary contribution to any
# mismatch is visible separately from the bulk. See the module docstring for
# the "this is not a bug detector" framing.
# ---------------------------------------------------------------------------


def _node_weight_array(grid, delta_s_N: float) -> np.ndarray:
    """w_j * mu(y_j, N), full-node array (length n_max+1) -- the diagonal of
    the weighted norm W used throughout this section."""
    return grid.weights * measure(grid.nodes, delta_s_N)


def _sbp_residual(grid) -> float:
    """
    ‖H D + Dᵀ H − B‖ / ‖H D‖, with H = diag(w_j) and B = diag(-1,0,...,0,+1)
    -- the diagonal-norm SBP identity for the LGL first-derivative matrix D.
    Acceptance anchor ~1e-14: this is a sanity check on the grid/weight
    wiring, not a physics quantity -- if it isn't ~machine-zero, the weight
    or D is wired wrong and every other number in this diagnostic is
    meaningless.
    """
    H = np.diag(grid.weights)
    D = grid.D
    B = np.zeros((grid.n_collocation_points, grid.n_collocation_points))
    B[0, 0] = -1.0
    B[-1, -1] = 1.0
    sbp_defect = H @ D + D.T @ H - B
    return float(np.linalg.norm(sbp_defect) / np.linalg.norm(H @ D))


def _assemble_gradient_operator_full_node(grid, delta_s_N: float) -> np.ndarray:
    """
    Full-node gradient operator L (with its exp(-2*Delta_s_loc) prefactor
    folded in, at the frozen uniform-H^2 point where Delta_s_loc(y,N) ==
    delta_s_N at every node), shape (n_max+1, n_max+1). No boundary
    elimination is applied -- every node is a free row/column -- so this
    isolates L's own discrete self-adjointness structure from the
    Neumann/Dirichlet treatment applied elsewhere in the solver.
    """
    n_full = grid.n_collocation_points
    delta_s_loc_array = np.full(n_full, delta_s_N)

    def _apply(f):
        L_f = L_operator(f, delta_s_N, grid.nodes, grid.D, grid.D2)
        return np.exp(-2.0 * delta_s_loc_array) * L_f

    return np.column_stack([_apply(e) for e in np.eye(n_full)])


def _interior_node_indices(n_full: int) -> np.ndarray:
    """
    Indices [1..n_full-2] -- i.e. every full-node index except the two
    boundary nodes y=-1 (index 0) and y=+1 (index n_full-1, == n_max). Used
    to mask the boundary out of both the numerator and denominator Frobenius
    norms for the `*_interior` metrics (prompt 18a fix 2).
    """
    return np.arange(1, n_full - 1)


def _self_adjoint_residual(
    matrix: np.ndarray, w_diag: np.ndarray, keep: np.ndarray = None,
) -> float:
    """
    ‖W L − (W L)ᵀ‖ / ‖W L‖ for a diagonal weight diag(w_diag) -- the
    inversion-free self-adjointness residual (prompt 18a fix 1). Never forms
    W⁻¹: the weight `W = diag(w_j mu(y_j,N))` is exponentially graded
    (condition number exp(3*delta_s)), so the original `‖W⁻¹ Lᵀ W − L‖ / ‖L‖`
    form is well-conditioned only up to delta_s~5 and pure roundoff beyond
    that.

    If `keep` is given, both the numerator (`W L − (W L)ᵀ`) and denominator
    (`W L`) matrices are restricted to `matrix[keep, keep]` before their
    Frobenius norms are taken -- the interior-only variant, masking the
    boundary rows/cols out of both norms rather than out of `matrix` up
    front, so the weighting by W is applied at full resolution first.
    """
    WL = np.diag(w_diag) @ matrix
    defect = WL - WL.T
    if keep is not None:
        WL = WL[np.ix_(keep, keep)]
        defect = defect[np.ix_(keep, keep)]
    return float(np.linalg.norm(defect) / np.linalg.norm(WL))


def _block_mismatch(
    F: np.ndarray, R: np.ndarray, w_diag: np.ndarray, keep: np.ndarray = None,
) -> float:
    """
    ‖W_b R + Fᵀ W_b‖ / ‖W_b R‖ for a diagonal block weight diag(w_diag) --
    F and R must already be expressed in the SAME block layout (same sizes,
    same node semantics per block, i.e. the full-node representation) for
    this comparison to be meaningful.

    If `keep` is given (typically `keep2 = concat(keep, keep)` for the
    two-field blocks here), both the numerator (`W_b R + Fᵀ W_b`) and
    denominator (`W_b R`) matrices are restricted to `[keep, keep]` before
    their Frobenius norms are taken -- the interior-only variant.
    """
    W_b = np.diag(w_diag)
    numerator_matrix = W_b @ R + F.T @ W_b
    denominator_matrix = W_b @ R
    if keep is not None:
        numerator_matrix = numerator_matrix[np.ix_(keep, keep)]
        denominator_matrix = denominator_matrix[np.ix_(keep, keep)]
    return float(np.linalg.norm(numerator_matrix) / np.linalg.norm(denominator_matrix))


def _forward_operator_full_node(
    grid, alpha: float, N: float, epsilon_core: float,
    *, include_gradient: bool, include_advection: bool,
) -> np.ndarray:
    """
    Full-node forward spatial operator (no boundary elimination -- every
    phi/pi node is a free row/column), shape (2*(n_max+1), 2*(n_max+1)),
    stacked as (phi_full, pi_full) -> (dphi_full, dpi_full). Mirrors
    assemble_spatial_operator's frozen-coefficient conventions exactly, with
    the gradient and advection contributions independently maskable so the
    "advection-only"/"gradient-only" block-mismatch decomposition (prompt 18)
    can reuse this one assembly rather than three near-duplicates.
    """
    n_full = grid.n_collocation_points
    delta_s_N = float(delta_s(N, 0.0, 1.0, 1.0, alpha))
    delta_s_loc_array = np.full(n_full, delta_s_N)
    A_array = advection_coefficient(grid.nodes, delta_s_N, epsilon_core)

    def _rhs(vec):
        phi_full = vec[:n_full]
        pi_full = vec[n_full:]
        if include_gradient:
            gradient_term = np.exp(-2.0 * delta_s_loc_array) * L_operator(
                phi_full, delta_s_N, grid.nodes, grid.D, grid.D2
            )
        else:
            gradient_term = np.zeros(n_full)
        if include_advection:
            advection_phi = advection_term(phi_full, A_array, grid.D)
            advection_pi = advection_term(pi_full, A_array, grid.D)
        else:
            advection_phi = np.zeros(n_full)
            advection_pi = np.zeros(n_full)
        dphi_full = advection_phi
        dpi_full = gradient_term + advection_pi
        return np.concatenate([dphi_full, dpi_full])

    n_state = 2 * n_full
    return np.column_stack([_rhs(e) for e in np.eye(n_state)])


def _response_operator_full_node(
    grid, alpha: float, N: float, epsilon_core: float,
    *, include_gradient: bool, include_advection_and_c: bool,
) -> np.ndarray:
    """
    Full-node response spatial operator (no boundary elimination), shape
    (2*(n_max+1), 2*(n_max+1)), stacked as (rfield_full, rmom_full) ->
    (drfield_full, drmom_full). Mirrors response_rhs's own assembly:
    L acts on rmom (not rfield) -- self-adjointness of L moves the operator
    onto the other response field -- with a MINUS sign relative to the
    forward sector's gradient term, and c(N) dressing both fields exactly
    as the excluded potential/noise/damping terms would be excluded from
    the forward sector's own spatial-only decomposition.
    """
    n_full = grid.n_collocation_points
    delta_s_N = float(delta_s(N, 0.0, 1.0, 1.0, alpha))
    delta_s_loc_array = np.full(n_full, delta_s_N)
    A_array = advection_coefficient(grid.nodes, delta_s_N, epsilon_core)
    c_N = _c_of_N(epsilon_core, delta_s_N)

    def _rhs(vec):
        rfield_full = vec[:n_full]
        rmom_full = vec[n_full:]
        if include_gradient:
            gradient_term = np.exp(-2.0 * delta_s_loc_array) * L_operator(
                rmom_full, delta_s_N, grid.nodes, grid.D, grid.D2
            )
        else:
            gradient_term = np.zeros(n_full)
        if include_advection_and_c:
            advection_rfield = advection_term(rfield_full, A_array, grid.D)
            advection_rmom = advection_term(rmom_full, A_array, grid.D)
            c_rfield = c_N * rfield_full
            c_rmom = c_N * rmom_full
        else:
            advection_rfield = np.zeros(n_full)
            advection_rmom = np.zeros(n_full)
            c_rfield = np.zeros(n_full)
            c_rmom = np.zeros(n_full)
        drfield_full = advection_rfield + c_rfield - gradient_term
        drmom_full = advection_rmom + c_rmom
        return np.concatenate([drfield_full, drmom_full])

    n_state = 2 * n_full
    return np.column_stack([_rhs(e) for e in np.eye(n_state)])


def compute_adjoint_diagnostics(
    n_max: int, alpha: float, N: float, epsilon_core: float = DEFAULT_EPSILON_CORE,
) -> dict:
    """
    Assembles every operator needed for one row of the adjoint-consistency
    diagnostic (prompt 18, metric fixes in 18a) at a single (n_max, alpha, N)
    point. Returns a dict with keys matching ADJOINT_CSV_FIELDNAMES minus
    n_max/alpha/N (filled in by the caller, sweep_adjoint_diagnostics).

    Full-node only (prompt 18a drops the eliminated representation -- the
    role-swapped Neumann elimination put the forward and response states in
    mismatched index layouts, making `block_mismatch_gradient_eliminated`
    collapse to exactly sqrt(2) for every row regardless of n_max/alpha/N,
    an artifact rather than a measurement). Each full-node metric
    (`L_selfadj` and the three `block_mismatch_*`) is reported alongside an
    `*_interior` companion that masks the two boundary nodes (y=+-1) out of
    both the numerator and denominator Frobenius norms -- the interior/
    boundary split that replaces the eliminated representation as the way
    to see the boundary's contribution separately from the bulk.
    """
    grid = LGLCollocationGrid(n_max + 1)
    delta_s_N = float(delta_s(N, 0.0, 1.0, 1.0, alpha))
    n_full = grid.n_collocation_points
    keep = _interior_node_indices(n_full)

    sbp_residual = _sbp_residual(grid)

    L_full_node = _assemble_gradient_operator_full_node(grid, delta_s_N)
    w_full_node = _node_weight_array(grid, delta_s_N)
    L_selfadj = _self_adjoint_residual(L_full_node, w_full_node)
    L_selfadj_interior = _self_adjoint_residual(L_full_node, w_full_node, keep=keep)

    w_b_full_node = np.concatenate([w_full_node, w_full_node])
    keep2 = np.concatenate([keep, keep + n_full])

    F_full = _forward_operator_full_node(
        grid, alpha, N, epsilon_core, include_gradient=True, include_advection=True,
    )
    F_adv = _forward_operator_full_node(
        grid, alpha, N, epsilon_core, include_gradient=False, include_advection=True,
    )
    F_grad = _forward_operator_full_node(
        grid, alpha, N, epsilon_core, include_gradient=True, include_advection=False,
    )
    R_full = _response_operator_full_node(
        grid, alpha, N, epsilon_core, include_gradient=True, include_advection_and_c=True,
    )
    R_adv = _response_operator_full_node(
        grid, alpha, N, epsilon_core, include_gradient=False, include_advection_and_c=True,
    )
    R_grad = _response_operator_full_node(
        grid, alpha, N, epsilon_core, include_gradient=True, include_advection_and_c=False,
    )

    block_mismatch_full = _block_mismatch(F_full, R_full, w_b_full_node)
    block_mismatch_full_interior = _block_mismatch(F_full, R_full, w_b_full_node, keep=keep2)
    block_mismatch_advection = _block_mismatch(F_adv, R_adv, w_b_full_node)
    block_mismatch_advection_interior = _block_mismatch(F_adv, R_adv, w_b_full_node, keep=keep2)
    block_mismatch_gradient = _block_mismatch(F_grad, R_grad, w_b_full_node)
    block_mismatch_gradient_interior = _block_mismatch(F_grad, R_grad, w_b_full_node, keep=keep2)

    return {
        "delta_s_N": delta_s_N,
        "sbp_residual": sbp_residual,
        "L_selfadj": L_selfadj,
        "L_selfadj_interior": L_selfadj_interior,
        "block_mismatch_full": block_mismatch_full,
        "block_mismatch_full_interior": block_mismatch_full_interior,
        "block_mismatch_advection": block_mismatch_advection,
        "block_mismatch_advection_interior": block_mismatch_advection_interior,
        "block_mismatch_gradient": block_mismatch_gradient,
        "block_mismatch_gradient_interior": block_mismatch_gradient_interior,
    }


def sweep_adjoint_diagnostics(n_max_values, alpha_values, N_values, epsilon_core: float = DEFAULT_EPSILON_CORE):
    """Computes one row per (n_max, alpha, N) combination in the Cartesian
    product of the three input lists. Returns a list of dicts with keys
    matching ADJOINT_CSV_FIELDNAMES."""
    rows = []
    for n_max in n_max_values:
        for alpha in alpha_values:
            for N in N_values:
                diagnostics = compute_adjoint_diagnostics(n_max, alpha, N, epsilon_core)
                row = {"n_max": n_max, "alpha": alpha, "N": N}
                row.update(diagnostics)
                rows.append(row)
    return rows


def plot_adjoint_convergence(n_max_values, alpha, N, epsilon_core: float, output_path: Path) -> None:
    """
    block_mismatch_{full,advection,gradient}, full-node vs interior-only,
    overlaid vs n_max at one representative (alpha, N) point, log-y (prompt
    18a): full-node solid, interior-only dashed, same colour per block --
    so the boundary-vs-bulk split is visible in one figure (gradient's
    interior curve should fall away from its flat full-node curve; advection's
    interior curve should track its already-converging full-node curve).
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    labels = ["full", "advection-only", "gradient-only"]
    keys = ["block_mismatch_full", "block_mismatch_advection", "block_mismatch_gradient"]
    full_series = {k: [] for k in keys}
    interior_series = {k: [] for k in keys}
    for n_max in n_max_values:
        diagnostics = compute_adjoint_diagnostics(n_max, alpha, N, epsilon_core)
        for k in keys:
            full_series[k].append(diagnostics[k])
            interior_series[k].append(diagnostics[f"{k}_interior"])

    fig, ax = plt.subplots(figsize=(6, 5))
    for label, key, color in zip(labels, keys, ("C0", "C1", "C2")):
        ax.plot(n_max_values, full_series[key], marker="o", color=color, label=f"{label} (full-node)")
        ax.plot(
            n_max_values, interior_series[key], marker="s", linestyle="--", color=color,
            label=f"{label} (interior)",
        )
    ax.set_yscale("log")
    ax.set_xlabel(r"$n_{\max}$")
    ax.set_ylabel("block mismatch")
    ax.set_title(rf"Forward/response block adjoint mismatch: full vs interior ($\alpha={alpha:.3g}$, $N={N:.3g}$)")
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Sweep + CSV output
# ---------------------------------------------------------------------------


def sweep_eigenvalues(n_max_values, alpha_values, N_values, epsilon_core: float = DEFAULT_EPSILON_CORE):
    """Computes one row per (n_max, alpha, N) combination in the Cartesian
    product of the three input lists. Returns a list of dicts with keys
    matching CSV_FIELDNAMES."""
    rows = []
    for n_max in n_max_values:
        for alpha in alpha_values:
            for N in N_values:
                matrix, delta_s_N = assemble_spatial_operator(n_max, alpha, N, epsilon_core)
                eigvals = np.linalg.eigvals(matrix)
                op_norm = float(np.linalg.norm(matrix, ord=2))
                max_abs_re = float(np.max(np.abs(eigvals.real)))
                max_abs_im = float(np.max(np.abs(eigvals.imag)))
                max_abs_lambda = float(np.max(np.abs(eigvals)))
                implied_dt = (
                    RK45_REAL_AXIS_STABILITY_RADIUS / max_abs_lambda
                    if max_abs_lambda > 0.0 else float("inf")
                )
                rows.append({
                    "n_max": n_max,
                    "alpha": alpha,
                    "N": N,
                    "delta_s_N": delta_s_N,
                    "op_norm": op_norm,
                    "max_abs_re_lambda": max_abs_re,
                    "max_abs_im_lambda": max_abs_im,
                    "implied_rk45_max_dt": implied_dt,
                })
    return rows


def write_csv(rows: list, path: Path, fieldnames: list = CSV_FIELDNAMES) -> None:
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def plot_spectrum_scatter(n_max_values, alpha, N, epsilon_core: float, output_path: Path) -> None:
    """
    Re/Im eigenvalue scatter of the assembled operator across n_max_values,
    at a single representative (alpha, N) point -- one color per n_max, so
    the growth of the spectral radius (and its complex character) with
    resolution is visible in one figure.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import seaborn as sns

    palette = sns.color_palette("viridis", n_colors=len(n_max_values))

    fig, ax = plt.subplots(figsize=(6, 5))
    for color, n_max in zip(palette, n_max_values):
        matrix, _ = assemble_spatial_operator(n_max, alpha, N, epsilon_core)
        eigvals = np.linalg.eigvals(matrix)
        ax.scatter(eigvals.real, eigvals.imag, s=14, color=color, label=rf"$n_{{\max}}={n_max}$")

    ax.set_xlabel(r"$\mathrm{Re}(\lambda)$")
    ax.set_ylabel(r"$\mathrm{Im}(\lambda)$")
    ax.set_title(rf"Assembled operator spectrum ($\alpha={alpha:.3g}$, $N={N:.3g}$)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _parse_float_list(s: str) -> list:
    return [float(x) for x in s.split(",") if x.strip()]


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Assembled-operator eigenvalue sweep (--mode spectrum, "
                     "prompt 17 Part A) and discrete adjoint-consistency "
                     "diagnostic (--mode adjoint, prompt 18) for the "
                     "gradient-coupled instanton's onion-model spatial "
                     "discretisation.",
    )
    parser.add_argument(
        "--n-max", type=str, default=",".join(str(v) for v in DEFAULT_N_MAX_VALUES),
        help="Comma-separated list of n_max (polynomial degree) values to sweep "
             "(default: %(default)s).",
    )
    parser.add_argument(
        "--alpha", type=str, default=",".join(str(v) for v in DEFAULT_ALPHA_VALUES),
        help="Comma-separated list of alpha (regularization) values to sweep "
             "(default: %(default)s).",
    )
    parser.add_argument(
        "--N", type=str, default=",".join(str(v) for v in DEFAULT_N_VALUES),
        help="Comma-separated list of local running-N values to sweep "
             "(default: %(default)s).",
    )
    parser.add_argument(
        "--epsilon-core", type=float, default=DEFAULT_EPSILON_CORE,
        help="Fixed representative core epsilon feeding the advection "
             "coefficient at every sweep point (default: %(default)s).",
    )
    parser.add_argument(
        "--mode", type=str, default="spectrum", choices=["spectrum", "adjoint"],
        help="'spectrum' (default, prompt 17 Part A): assembled-operator "
             "eigenvalue sweep. 'adjoint' (prompt 18): discrete "
             "adjoint-consistency diagnostic -- SBP residual, gradient "
             "self-adjointness, forward/response block adjoint mismatch "
             "(default: %(default)s).",
    )
    parser.add_argument(
        "--output", type=str, default="stiffness_spectrum.csv",
        help="Output CSV path (default: %(default)s).",
    )
    parser.add_argument(
        "--plot", action="store_true",
        help="Also write a plot alongside the CSV: a Re/Im eigenvalue "
             "scatter (largest alpha/N in the sweep, one color per n_max) "
             "in --mode spectrum, or a block-mismatch-vs-n_max convergence "
             "plot in --mode adjoint.",
    )
    parser.add_argument(
        "--plot-format", type=str, default="pdf", choices=["pdf", "png", "svg"],
        help="Output format for --plot (default: %(default)s).",
    )
    return parser


def main(argv=None) -> int:
    parser = create_parser()
    args = parser.parse_args(argv)

    n_max_values = [int(v) for v in _parse_float_list(args.n_max)]
    alpha_values = _parse_float_list(args.alpha)
    N_values = _parse_float_list(args.N)

    if args.mode == "adjoint":
        rows = sweep_adjoint_diagnostics(n_max_values, alpha_values, N_values, args.epsilon_core)
        output_path = Path(args.output)
        write_csv(rows, output_path, fieldnames=ADJOINT_CSV_FIELDNAMES)
        print(f"Wrote {len(rows)} adjoint-diagnostic sweep points to {output_path}")

        if args.plot:
            plot_path = output_path.with_suffix(f".{args.plot_format}")
            plot_adjoint_convergence(
                n_max_values, max(alpha_values), max(N_values), args.epsilon_core, plot_path,
            )
            print(f"Wrote block-mismatch convergence plot to {plot_path}")

        return 0

    self_check_diff = self_check_assembled_operator(
        n_max=8, alpha=alpha_values[0] if alpha_values else 0.05,
        N=N_values[-1] if N_values else 5.0, epsilon_core=args.epsilon_core,
    )
    print(f"Self-check (assembled operator vs. finite-difference Jacobian of "
          f"forward_rhs): max abs diff = {self_check_diff:.3e}")

    rows = sweep_eigenvalues(n_max_values, alpha_values, N_values, args.epsilon_core)
    output_path = Path(args.output)
    write_csv(rows, output_path)
    print(f"Wrote {len(rows)} sweep points to {output_path}")

    if args.plot:
        plot_path = output_path.with_suffix(f".{args.plot_format}")
        plot_spectrum_scatter(
            n_max_values, max(alpha_values), max(N_values), args.epsilon_core, plot_path,
        )
        print(f"Wrote spectrum scatter plot to {plot_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
