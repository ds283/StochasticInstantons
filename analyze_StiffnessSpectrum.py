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

Prompt 20 amends `--mode spectrum` to report the SIGNED spectral abscissa
(`max(ev.real)`, not `max(|ev.real|)`) plus a right-half-plane eigenvalue
count and the associated growth e-fold time. `max_abs_re_lambda` alone cannot
distinguish a genuinely unstable `+1500` from a stable `-1500`; the sign is
the entire question of whether the assembled operator itself is unstable,
independent of which integrator is thrown at it. `implied_rk45_max_dt` is
only a meaningful stability step when `spectral_abscissa <= 0` -- when it is
positive, the semi-discrete ODE grows for ANY step size, and
`growth_efold_time` (directly comparable to `N_total`) is the relevant
number instead.

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

from ComputeTargets.GradientCoupledInstanton.forward_rhs import noise_source_terms
from ComputeTargets.GradientCoupledInstanton.response_rhs import _c_of_N
from Numerics.DiscretizedOperators import (
    L_operator,
    advection_term,
    advection_split_term,
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
# rigorous bound. It is also only a *stability* step at all when
# `spectral_abscissa <= 0` (prompt 20): when the spectral abscissa is
# positive, the semi-discrete system has an exponentially growing mode and
# NO step size is stable -- `growth_efold_time` is the relevant number in
# that regime, not `implied_rk45_max_dt`.
RK45_REAL_AXIS_STABILITY_RADIUS = 2.8

# Relative right-half-plane threshold (prompt 20): an eigenvalue counts as
# "unstable" (contributing to n_rhp) only if its real part exceeds this
# fraction of the largest eigenvalue magnitude, so the count is scale-robust
# across the O(n_max^4) growth in |lambda| rather than using a fixed
# absolute cutoff.
RHP_REL_TOL = 1.0e-6

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
    "spectral_abscissa", "n_rhp", "growth_efold_time",
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


def _pack_state_strong(phi_full: np.ndarray, pi_full: np.ndarray) -> np.ndarray:
    """
    Frozen, LOCAL copy of the pre-prompt-21a
    ComputeTargets.GradientCoupledInstanton.forward_rhs.pack_state: drops
    the Dirichlet-pinned outer edge AND the Neumann-eliminated phi_core,
    giving the (2*n_max-1)-length strong-BC state
    (phi_1,...,phi_{n_max-1}, pi_1,...,pi_{n_max}).

    Prompt 21a promoted phi_core to a free, integrated DOF in the
    PRODUCTION forward_rhs/pack_state (state length 2*n_max), which is
    exactly the closure this module's own "sbp-sat" operator
    (assemble_spatial_operator_sbp_sat) was built to validate BEFORE that
    port happened. assemble_spatial_operator below is the deliberately
    preserved "strong" BASELINE every prompt-17/20/21 test compares the new
    closure against -- it must keep representing the OLD, node-eliminating
    closure exactly, independent of how the live production module
    evolves. Hence this local copy, rather than importing the (now
    different) production pack_state.
    """
    n_max = len(phi_full) - 1
    return np.concatenate([phi_full[1:n_max], pi_full[1:n_max + 1]])


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
    state -- the STRONG (node-eliminating) closure's own layout (see
    _pack_state_strong's docstring for why this is now a local, frozen
    copy rather than the live production pack_state), with the
    Dirichlet-pinned boundary (phi_full[0]/pi_full[0]) held at zero (its
    true, non-zero value is a fixed additive offset from the background
    trajectory -- not part of the state-dependent linear map).

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
        return _pack_state_strong(dphi_full, dpi_full)

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


def _unpack_state_strong(state, N, N_offset, alpha, H_sq_nl_init, grid, trajectory, potential):
    """Frozen LOCAL copy of the pre-prompt-21a
    ComputeTargets.GradientCoupledInstanton.forward_rhs.unpack_state:
    Neumann-eliminates phi_core rather than integrating it -- see
    _pack_state_strong's docstring for why this module keeps its own copy
    rather than calling the (now different) production unpack_state."""
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


def _forward_rhs_strong(
    N, state, N_offset, alpha, H_sq_nl_init, grid, trajectory, potential,
    rfield_splines, rmom_splines, diffusion_model, disable_spatial_coupling=False,
):
    """
    Frozen LOCAL copy of the pre-prompt-21a
    ComputeTargets.GradientCoupledInstanton.forward_rhs.forward_rhs (plain-
    product advection, Neumann-eliminated phi_core, no SAT closure) -- used
    ONLY by finite_difference_spatial_jacobian below.

    Prompt 21a changed the PRODUCTION forward_rhs to a different closure
    (split-form advection, an enlarged/free-DOF state, a core SAT penalty).
    finite_difference_spatial_jacobian's whole purpose is to validate
    assemble_spatial_operator's hand-transcribed STRONG-closure matrix
    against an independently-computed RHS of THAT SAME (deliberately
    preserved) closure -- so it must keep testing against a frozen copy of
    the old physics, not the evolved production module, or the comparison
    would no longer be checking what assemble_spatial_operator claims to
    represent. See _pack_state_strong's docstring for the full rationale.
    diluted_diffusion_coefficients/noise_source_terms/n_count themselves are
    UNCHANGED by prompt 21a (only the boundary closure moved), so those are
    still imported directly from the production module rather than
    duplicated here.
    """
    phi_full, pi_full = _unpack_state_strong(
        state, N, N_offset, alpha, H_sq_nl_init, grid, trajectory, potential
    )

    H_sq_core = potential.H_sq(phi_full[-1], pi_full[-1])
    delta_s_N = delta_s(N, 0.0, H_sq_core, H_sq_nl_init, alpha)

    H_sq_loc_array = potential.H_sq(phi_full, pi_full)
    epsilon_loc_array = potential.epsilon(phi_full, pi_full)
    dV_array = potential.dV_dphi(phi_full)
    delta_s_loc_array = delta_s(N, 0.0, H_sq_loc_array, H_sq_nl_init, alpha)

    if disable_spatial_coupling:
        gradient_term = np.zeros_like(phi_full)
        advection_phi_array = np.zeros_like(phi_full)
        advection_pi_array = np.zeros_like(pi_full)
    else:
        L_phi_array = L_operator(phi_full, delta_s_N, grid.nodes, grid.D, grid.D2)
        gradient_term = np.exp(-2.0 * delta_s_loc_array) * L_phi_array
        epsilon_core = epsilon_loc_array[-1]
        A_array = advection_coefficient(grid.nodes, delta_s_N, epsilon_core)
        advection_phi_array = advection_term(phi_full, A_array, grid.D)
        advection_pi_array = advection_term(pi_full, A_array, grid.D)

    rfield_full = np.array([spline(N) for spline in rfield_splines])
    rmom_full = np.array([spline(N) for spline in rmom_splines])
    noise_field_array, noise_mom_array = noise_source_terms(
        phi_full, pi_full, rfield_full, rmom_full, delta_s_N, delta_s_loc_array,
        grid, potential, diffusion_model,
    )

    dphi_full = pi_full + advection_phi_array + noise_field_array
    dpi_full = (
        -(3.0 - epsilon_loc_array) * pi_full
        - dV_array / H_sq_loc_array
        + gradient_term
        + advection_pi_array
        + noise_mom_array
    )

    return _pack_state_strong(dphi_full, dpi_full)


def finite_difference_spatial_jacobian(
    n_max: int, alpha: float, N: float,
    phi0: float = 0.3, pi0: float = -0.05,
    epsilon_core: float = DEFAULT_EPSILON_CORE, fd_eps: float = _FD_EPS,
) -> np.ndarray:
    """
    Self-check companion to assemble_spatial_operator: computes the Jacobian
    of the STRONG closure's own spatial-only contribution
    (_forward_rhs_strong, prompt 21a's frozen copy of the pre-existing
    forward_rhs -- see that function's docstring for why this is no longer
    the live production forward_rhs) by central finite differences, at the
    same (n_max, alpha, N) point.

    Isolates the spatial-only part exactly as _forward_rhs_strong's own
    disable_spatial_coupling flag defines it:
    _forward_rhs_strong(disable_spatial_coupling=False) -
    _forward_rhs_strong(disable_spatial_coupling=True), evaluated at the same
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

    state0 = _pack_state_strong(np.full(n_max + 1, phi0), np.full(n_max + 1, pi0))

    def _spatial_only(state: np.ndarray) -> np.ndarray:
        full = _forward_rhs_strong(
            N, state, N_offset, alpha, H_sq_nl_init, grid, trajectory, potential,
            zero_splines, zero_splines, dm, disable_spatial_coupling=False,
        )
        no_coupling = _forward_rhs_strong(
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
# SBP-SAT boundary closure (prompt 21)
#
# Phase 1 standalone prototype: split-form advection (skew under the plain
# LGL diagonal norm H=diag(w), up to a single boundary term) plus a
# dissipative SAT penalty at the core node, chosen via the discrete energy
# estimate to cancel that boundary term exactly. Full derivation:
# .documents/gradient-coupled-instanton/21-sbp-sat-design-note.md.
#
# State layout differs from assemble_spatial_operator's: promoting phi_core
# from Neumann-eliminated to a free, SAT-penalized DOF requires it to be
# part of the state vector, so this operator's state is
# (phi_1,...,phi_{n_max}, pi_1,...,pi_{n_max}), length 2*n_max -- one entry
# longer than the strong-BC operator's 2*n_max-1, because phi_core is now
# integrated rather than eliminated. pi_core was already free in the
# strong-BC layout, so nothing changes there. This is a PROTOTYPE-ONLY
# layout choice to test the stability claim in isolation; it does not
# commit Phase 2 to any particular production state-vector convention (an
# implementation decision for Phase 2 itself, out of scope here). The outer
# edge (y=-1) is untouched -- held at zero exactly as
# assemble_spatial_operator does -- because the design note (Section 3)
# shows A(-1)=0 exactly, so the outer edge carries no destabilizing energy
# term and needs no SAT: a WRONG version that also added an outer-edge SAT
# would be harmless for stability (that term is already zero) but would be
# undocumented, unmotivated extra machinery.
# ---------------------------------------------------------------------------


def advection_split_matrix(A_array: np.ndarray, D: np.ndarray) -> np.ndarray:
    """
    A_split = 1/2 * (diag(A) @ D + D @ diag(A) - diag(D @ A)) -- the
    product-rule-consistent split form of variable-coefficient advection
    (design note Section 3). Continuum-identical to the plain diag(A) @ D
    (both equal A(y) du/dy for smooth u -- substitute the continuum product
    rule (Au)_y = A_y u + A u_y into 1/2*(A u_y + (Au)_y - A_y u) and the
    extra terms cancel, leaving A u_y), but NOT identical as MATRICES: D
    only differentiates polynomials up to degree n_max exactly, so
    D @ diag(A) applied to a degree-n_max grid function differentiates an
    effectively degree-2*n_max object and picks up an aliasing residual
    relative to diag(A) @ D + diag(D @ A) -- the explicit "- diag(D @ A)"
    term corrects for exactly that residual. This is what makes A_split
    (and not the plain product) skew under H=diag(w) up to a single
    boundary term (see advection_split_energy_defect below).

    A WRONG version would use the plain product diag(A) @ D directly (no
    correction term) -- that operator's failure signature is exactly the
    one this prompt starts from: spectral_abscissa growing like n^1.6,
    integrator-independent (see the module docstring's Background summary
    and the design note Section 1).
    """
    return 0.5 * (
        np.diag(A_array) @ D + D @ np.diag(A_array) - np.diag(D @ A_array)
    )


def advection_split_energy_defect(grid, A_array: np.ndarray) -> np.ndarray:
    """
    H @ A_split + A_split^T @ H, where A_split = advection_split_matrix(...)
    and H = diag(grid.weights) -- the quantity the design note (Section 3)
    derives a closed form for:

        diag(-A_0, 0, ..., 0, A_{n_max}) - H @ diag(D @ A)

    which, because A(y) is affine in y (so D @ A is the exact constant
    a' = (1-epsilon_core)/Delta_s(N) at every node) and A_0 = A(-1) = 0
    exactly, reduces further to -a'*H + diag(0,...,0, A_{n_max}). Exposed
    standalone (not inlined in assemble_spatial_operator_sbp_sat) purely so
    the closed-form energy-estimate derivation itself can be regression-
    tested against this general definition, independent of the SAT penalty
    built on top of it. A WRONG derivation would show up here as this
    matrix having off-diagonal structure, or a diagonal that doesn't match
    -a'*w_j (with the single +A_{n_max} correction at the core row) --
    both are asserted directly in tests/test_sbp_sat_boundary_closure.py.
    """
    H = np.diag(grid.weights)
    A_split = advection_split_matrix(A_array, grid.D)
    return H @ A_split + A_split.T @ H


def assemble_spatial_operator_sbp_sat(
    n_max: int, alpha: float, N: float, epsilon_core: float = DEFAULT_EPSILON_CORE,
    *, include_gradient: bool = True,
):
    """
    SBP-SAT closure of the spatial operator (prompt 21 Phase 1b): split-form
    advection (advection_split_matrix) in place of the plain product, plus a
    dissipative SAT penalty at the core node (y=+1) on BOTH phi and pi (the
    same A_array/tau applies to each -- advection_term dresses both fields
    identically in forward_rhs), with tau = A(core)/2 -- the design note's
    Section 4 exact-cancellation value. Frozen-coefficient, same convention
    as assemble_spatial_operator (Delta_s(N)/Delta_s_loc(y,N) evaluated at
    H_sq_local/H_sq_nl_init held at ratio 1 everywhere).

    include_gradient=False isolates advection+SAT alone, for the
    "advection-only sub-check reproduces the validated -A(core)/4 constant"
    acceptance item (design note Section 4's "reproducing the validated
    recipe").

    Energy-estimate reference: design note Section 4. WRONG versions and
    their failure signatures:
      - tau=0 (no SAT): reduces to the plain split-form operator, which
        still carries the single destabilizing diagonal entry
        S_{core,core} ~ A(core) (design note Section 3) -- abscissa still
        grows/stays positive at the core-dominated mode.
      - tau < A(core)/2: partial cancellation, the u_core^2 coefficient
        (A(core)/2 - tau) stays positive -- abscissa bounded in n but still
        positive and non-decaying (a smaller, but still real, n-independent
        instability) -- distinguishable from the tau=A(core)/2 case only by
        checking the sign/value of the plateaued abscissa, not by whether
        it grows with n.
      - SAT applied only to pi, not phi (or vice versa): leaves the OTHER
        field's core row with the uncancelled S_{core,core} defect --
        because advection couples phi and pi through the SAME A_array, both
        need the penalty independently.

    Returns (matrix, delta_s_N, tau, A_core): the assembled matrix (shape
    (2*n_max, 2*n_max) -- see module comment above this function for the
    state-layout note), the frozen Delta_s(N), the SAT coefficient tau
    used, and A(core) itself (so callers can check tau == A_core/2 and
    compare abscissa against -A_core/4 in the advection-only case).
    """
    grid = LGLCollocationGrid(n_max + 1)
    n_state = 2 * n_max

    delta_s_N = float(delta_s(N, 0.0, 1.0, 1.0, alpha))
    delta_s_loc_array = delta_s(N, 0.0, np.ones(n_max + 1), 1.0, alpha)
    A_array = advection_coefficient(grid.nodes, delta_s_N, epsilon_core)
    A_split = advection_split_matrix(A_array, grid.D)

    A_core = float(A_array[-1])
    tau = 0.5 * A_core
    w_core = float(grid.weights[-1])

    def _spatial_rhs(state: np.ndarray) -> np.ndarray:
        phi_full = np.empty(n_max + 1)
        pi_full = np.empty(n_max + 1)
        phi_full[0] = 0.0
        pi_full[0] = 0.0
        # Both phi_core and pi_core are free, integrated DOF here -- no
        # Neumann elimination of phi_full[-1] (contrast
        # assemble_spatial_operator, where it is eliminated every call).
        phi_full[1:n_max + 1] = state[:n_max]
        pi_full[1:n_max + 1] = state[n_max:2 * n_max]

        if include_gradient:
            L_phi_array = L_operator(phi_full, delta_s_N, grid.nodes, grid.D, grid.D2)
            gradient_term = np.exp(-2.0 * delta_s_loc_array) * L_phi_array
        else:
            gradient_term = np.zeros(n_max + 1)

        advection_phi_array = A_split @ phi_full
        advection_pi_array = A_split @ pi_full

        dphi_full = advection_phi_array
        dpi_full = gradient_term + advection_pi_array

        # SAT penalty (design note Section 4): -tau/w_core * u_core at the
        # core row only, for each field independently. The "-tau*g" part of
        # the full SAT (-tau/H*(u_core-g)) is a constant additive forcing,
        # not part of the linear map an eigenvalue analysis probes -- it
        # shifts the fixed point, not the spectrum -- so it is correctly
        # omitted from this linear operator assembly (see design note
        # Section 6 for where g re-enters, in Phase 2's production RHS).
        dphi_full[-1] -= (tau / w_core) * phi_full[-1]
        dpi_full[-1] -= (tau / w_core) * pi_full[-1]

        return np.concatenate([dphi_full[1:n_max + 1], dpi_full[1:n_max + 1]])

    matrix = np.column_stack([_spatial_rhs(e) for e in np.eye(n_state)])
    return matrix, delta_s_N, tau, A_core


# ---------------------------------------------------------------------------
# Response-sector spectral diagnostic (prompt 23 Phase 1)
#
# response_rhs.py's own pre-port docstring flagged this as a "known, symmetric
# follow-on candidate": the response sector uses the SAME A_array construction
# as the forward sector's advection term, and rmom_full is ALSO
# Neumann-eliminated at the core -- structurally the same defect-generating
# ingredients prompt 21/21a found and fixed for the forward sector. This
# section extends the assembled-operator sweep to test whether that symmetry
# argument actually holds.
#
# CRITICAL DIFFERENCE FROM THE FORWARD SECTOR: response_rhs is integrated
# BACKWARD in N (picard.py calls solve_ivp with t_span=(N_stop, N_start),
# N_stop > N_start). For a linear mode dy/dN = lambda*y integrated with a
# NEGATIVE step h (backward), the quantity that governs the numerical
# integrator's stability is z = h*lambda, not lambda itself -- and h<0 flips
# which SIGN of Re(lambda) is the catastrophic (unconditionally-unstable,
# any-step-size-fails) one. For forward integration (h>0), Re(lambda) >> 0
# growing with n_max is catastrophic (this is exactly prompt 21's disease:
# spectral_abscissa = max(Re(eig)) growing with n_max). For BACKWARD
# integration (h<0), it is Re(lambda) << 0 growing MORE NEGATIVE with n_max
# that is catastrophic (z = h*lambda > 0 for any h<0, outside RK45's stability
# region unconditionally) -- while Re(lambda) >> 0 growing is merely stiffness
# (z = h*lambda < 0, deep in the LHP; conditionally stable, just forces a
# smaller step). So the response sector's OWN "spectral_abscissa" -- the
# quantity that must stay bounded in n_max for the ACTUAL backward solve to be
# safe -- is max(Re(-eig)) = -min(Re(eig)) of the SAME assembled matrix M
# (dy/dN = M y convention, built the same way as the forward sector's
# assemble_spatial_operator for direct comparability), NOT max(Re(eig))
# itself. response_spectral_stability_metrics below encodes this by feeding
# spectral_stability_metrics the NEGATED eigenvalues -- see that function's
# own docstring.
# ---------------------------------------------------------------------------


def _pack_response_state_strong(rfield_full: np.ndarray, rmom_full: np.ndarray) -> np.ndarray:
    """
    Frozen, LOCAL copy of the pre-prompt-23
    ComputeTargets.GradientCoupledInstanton.response_rhs.pack_response_state:
    drops rfield_full[0]/rmom_full[0] (both pinned to zero) and rmom_full[-1]
    (Neumann-eliminated), giving the (2*n_max-1)-length state
    (rfield_1,...,rfield_{n_max}, rmom_1,...,rmom_{n_max-1}).

    Kept as a local copy (mirroring _pack_state_strong's own rationale) so
    this module's "strong" BASELINE keeps representing the OLD,
    node-eliminating closure exactly, independent of whether prompt 23
    Phase 2 ever changes the live production response_rhs.py.
    """
    n_max = len(rfield_full) - 1
    return np.concatenate([rfield_full[1:n_max + 1], rmom_full[1:n_max]])


def assemble_response_operator_strong(
    n_max: int, alpha: float, N: float, epsilon_core: float = DEFAULT_EPSILON_CORE,
):
    """
    Assembles the linearised response-sector spatial operator -- the SAME
    structural pieces response_rhs.py's own pre-port assembly applies:
    advection (plain product, advection_term) on both rfield/rmom, the
    gradient term (L applied to rmom, MINUS sign, per response_rhs.py's own
    docstring on why the sign and field are swapped relative to the forward
    sector), and the scalar c(N) dressing both fields -- with rmom_full[-1]
    (the core) Neumann-eliminated exactly as
    ComputeTargets.GradientCoupledInstanton.response_rhs.unpack_response_state
    does, and rfield_full[-1] (the core) free/integrated.

    Frozen-coefficient, same convention as assemble_spatial_operator: N and
    alpha fix Delta_s(N) via delta_s() evaluated at H_sq_local/H_sq_nl_init
    held at ratio 1 everywhere; epsilon_core is a fixed representative value
    feeding both the advection coefficient and c(N) (mirrors response_rhs's
    own epsilon_core = potential.epsilon(phi_full[-1], pi_full[-1]), a single
    scalar read at the core).

    Returns (A, delta_s_N): the assembled matrix, shape
    (2*n_max-1, 2*n_max-1), and the scalar Delta_s(N) used to build it.
    """
    grid = LGLCollocationGrid(n_max + 1)
    n_state = 2 * n_max - 1

    delta_s_N = float(delta_s(N, 0.0, 1.0, 1.0, alpha))
    delta_s_loc_array = delta_s(N, 0.0, np.ones(n_max + 1), 1.0, alpha)
    A_array = advection_coefficient(grid.nodes, delta_s_N, epsilon_core)
    c_N = _c_of_N(epsilon_core, delta_s_N)

    def _spatial_rhs(state: np.ndarray) -> np.ndarray:
        rfield_full = np.empty(n_max + 1)
        rmom_full = np.empty(n_max + 1)
        rfield_full[0] = 0.0
        rmom_full[0] = 0.0
        rfield_full[1:n_max + 1] = state[:n_max]
        rmom_full[1:n_max] = state[n_max:2 * n_max - 1]
        rmom_full[-1] = neumann_boundary_value(rmom_full, grid.D, boundary_index=-1)

        L_rmom_array = L_operator(rmom_full, delta_s_N, grid.nodes, grid.D, grid.D2)
        gradient_term = np.exp(-2.0 * delta_s_loc_array) * L_rmom_array

        advection_rfield_array = advection_term(rfield_full, A_array, grid.D)
        advection_rmom_array = advection_term(rmom_full, A_array, grid.D)

        # Isolates the SAME "spatial coupling only" subset the forward
        # sector's own assemble_spatial_operator isolates (gradient +
        # advection, dressed by c(N) -- the genuine spatial-coupling
        # analogue of c(N)'s role here): EXCLUDES the "-rfield_full" mass
        # coupling and "+(3-eps)*rmom" damping terms
        # _assemble_response_derivatives always adds (response_rhs.py's own
        # eq. inst-rpi) -- both are O(1), n_max-INDEPENDENT contributions
        # (a fixed -1/+3 diagonal shift, not growing with resolution), so
        # excluding them does not change whether the assembled operator's
        # eigenvalues grow with n_max, exactly mirroring why forward's own
        # isolation (excluding "-(3-eps)*pi" and "-dV/H_sq") is the right
        # comparison target rather than an arbitrary simplification.
        drfield_full = advection_rfield_array + c_N * rfield_full - gradient_term
        drmom_full = advection_rmom_array + c_N * rmom_full

        return _pack_response_state_strong(drfield_full, drmom_full)

    matrix = np.column_stack([_spatial_rhs(e) for e in np.eye(n_state)])
    return matrix, delta_s_N


def assemble_response_operator_sbp_sat(
    n_max: int, alpha: float, N: float, epsilon_core: float = DEFAULT_EPSILON_CORE,
    *, include_gradient: bool = True, tau_mult: float = 0.5,
):
    """
    SBP-SAT-closure CANDIDATE for the response sector (prompt 23 Phase 1),
    mirroring assemble_spatial_operator_sbp_sat's role-swap: split-form
    advection (advection_split_term) on both rfield/rmom, rmom_core promoted
    from Neumann-eliminated to a free/integrated DOF with a SAT penalty
    toward the LIVE Neumann target (mirrors forward's g_phi_core exactly,
    just role-swapped field name -- rmom's own natural regularity condition),
    and rfield_core (already free) SAT-penalized toward a FIXED target g=0
    (mirrors forward's g_pi_core role -- the "free field with no existing
    condition" -- but see the module docstring above: unlike forward's
    pi_core, rfield_core's terminal condition already anchors it, so a
    trivial zero target -- pure dissipation -- is tried first per the
    prompt's own suggestion, "confirm whether a value-target is needed at
    all").

    THE SIGN IS FLIPPED ON THE rmom_core SAT relative to forward's g_phi_core
    recipe: forward uses "-(tau/w_core)*(u_core-g)"; this uses
    "+(tau/w_core)*(rmom_core-g)". This is not a typo -- it is the direct,
    empirically-confirmed (see the Phase-1 test suite) consequence of the
    backward-integration sign flip described in this section's module
    comment above. rfield_core's SAT keeps forward's ORIGINAL sign
    ("-(tau/w_core)*rfield_core") because its target is the state-INDEPENDENT
    constant g=0: Phase-1 testing (see tests/test_response_spectrum_prompt23.py)
    found a DECOUPLED, constant-target SAT is exactly n-independent under
    EITHER sign (a diagonal-only correction -- the exact-cancellation tau
    value zeroes the anomalous term regardless of integration direction),
    so its sign is not a live design question the way rmom_core's is; "-" is
    kept purely for continuity with the forward sector's own convention.

    tau_mult (default 0.5, i.e. tau = A(core)/2, the EXACT algebraic
    cancellation value from the design note's Section 4 -- NOT forward's own
    empirically-hardened tau=|A(core)| doubling): Phase-1 testing found that
    using forward's doubled tau on the response sector's rmom_core SAT
    OVERSHOOTS the exact cancellation and flips the sign of the (now
    backward-relevant) u_core^2 coefficient, reproducing exactly the kind of
    n_max-growing catastrophic mode this closure is meant to remove -- see
    the design note (prompt 23) for the full account and the numbers.

    Returns (matrix, delta_s_N, tau, A_core), matching
    assemble_spatial_operator_sbp_sat's own return shape. State layout:
    (rfield_1,...,rfield_{n_max}, rmom_1,...,rmom_{n_max}), length 2*n_max --
    one longer than the strong closure's 2*n_max-1, since rmom_core is
    promoted from eliminated to integrated (PROTOTYPE-ONLY layout choice, as
    for the forward sector's own Phase-1 prototype).
    """
    grid = LGLCollocationGrid(n_max + 1)
    n_state = 2 * n_max

    delta_s_N = float(delta_s(N, 0.0, 1.0, 1.0, alpha))
    delta_s_loc_array = delta_s(N, 0.0, np.ones(n_max + 1), 1.0, alpha)
    A_array = advection_coefficient(grid.nodes, delta_s_N, epsilon_core)
    c_N = _c_of_N(epsilon_core, delta_s_N)

    A_core = float(A_array[-1])
    tau = tau_mult * A_core
    w_core = float(grid.weights[-1])

    def _spatial_rhs(state: np.ndarray) -> np.ndarray:
        rfield_full = np.empty(n_max + 1)
        rmom_full = np.empty(n_max + 1)
        rfield_full[0] = 0.0
        rmom_full[0] = 0.0
        rfield_full[1:n_max + 1] = state[:n_max]
        rmom_full[1:n_max + 1] = state[n_max:2 * n_max]

        if include_gradient:
            L_rmom_array = L_operator(rmom_full, delta_s_N, grid.nodes, grid.D, grid.D2)
            gradient_term = np.exp(-2.0 * delta_s_loc_array) * L_rmom_array
        else:
            gradient_term = np.zeros(n_max + 1)

        advection_rfield_array = advection_split_term(rfield_full, A_array, grid.D)
        advection_rmom_array = advection_split_term(rmom_full, A_array, grid.D)

        drfield_full = advection_rfield_array + c_N * rfield_full - gradient_term
        drmom_full = advection_rmom_array + c_N * rmom_full

        # rfield_core SAT: fixed g=0 target, forward's original sign.
        drfield_full[-1] += -(tau / w_core) * (rfield_full[-1] - 0.0)
        # rmom_core SAT: LIVE Neumann target, SIGN FLIPPED (see docstring).
        g_rmom_core = neumann_boundary_value(rmom_full, grid.D, boundary_index=-1)
        drmom_full[-1] += (tau / w_core) * (rmom_full[-1] - g_rmom_core)

        return np.concatenate([drfield_full[1:n_max + 1], drmom_full[1:n_max + 1]])

    matrix = np.column_stack([_spatial_rhs(e) for e in np.eye(n_state)])
    return matrix, delta_s_N, tau, A_core


def response_spectral_stability_metrics(eigvals: np.ndarray) -> dict:
    """
    The response-sector analogue of spectral_stability_metrics, accounting
    for the backward-integration sign flip (see this section's module
    comment above): feeds spectral_stability_metrics the NEGATED eigenvalues,
    so its "spectral_abscissa" = max(Re(-eig)) = -min(Re(eig)) of the
    ORIGINAL (dy/dN = M y convention) matrix -- the quantity that must stay
    bounded in n_max for solve_ivp's ACTUAL backward (t_span decreasing)
    integration of this operator to be safe from unconditional instability.

    A caller who mistakenly used spectral_stability_metrics directly on a
    response-sector matrix would be checking max(Re(eig)) -- the
    FORWARD-integration criterion -- against an operator that is never
    integrated forward; this function exists specifically to prevent that
    mistake being silently repeated at every response-sector call site.
    """
    return spectral_stability_metrics(-eigvals)


def _response_rhs_strong_spatial_only(
    N, state, alpha, H_sq_nl_init, grid, phi_splines, pi_splines, potential,
):
    """
    Frozen LOCAL copy of the real (pre-prompt-23) response_rhs, with the
    mass-coupling ("-rfield_full") and damping ("+(3-eps_loc)*rmom_full")
    terms EXCLUDED -- the response-sector analogue of _forward_rhs_strong's
    isolation of "everything disable_spatial_coupling=True zeroes". Used
    ONLY by self_check_response_assembled_operator, to validate
    assemble_response_operator_strong's hand-transcribed matrix against an
    independently-computed RHS restricted to the SAME spatial-only subset
    (advection + gradient + c(N)) -- see assemble_response_operator_strong's
    own comment for why excluding the mass/damping terms is the right
    comparison (both are O(1), n_max-independent, exactly mirroring why
    forward's own isolation excludes its "-(3-eps)*pi"/"-dV/H_sq" terms).
    """
    phi_full = np.array([spline(N) for spline in phi_splines])
    pi_full = np.array([spline(N) for spline in pi_splines])

    rfield_full, rmom_full = _unpack_response_state_strong_local(state, grid)

    H_sq_core = potential.H_sq(phi_full[-1], pi_full[-1])
    delta_s_N = delta_s(N, 0.0, H_sq_core, H_sq_nl_init, alpha)
    epsilon_core = potential.epsilon(phi_full[-1], pi_full[-1])
    c_N = _c_of_N(epsilon_core, delta_s_N)

    H_sq_loc_array = potential.H_sq(phi_full, pi_full)
    delta_s_loc_array = delta_s(N, 0.0, H_sq_loc_array, H_sq_nl_init, alpha)

    L_rmom_array = L_operator(rmom_full, delta_s_N, grid.nodes, grid.D, grid.D2)
    gradient_term = np.exp(-2.0 * delta_s_loc_array) * L_rmom_array

    A_array = advection_coefficient(grid.nodes, delta_s_N, epsilon_core)
    advection_rfield_array = advection_term(rfield_full, A_array, grid.D)
    advection_rmom_array = advection_term(rmom_full, A_array, grid.D)

    drfield_full = advection_rfield_array + c_N * rfield_full - gradient_term
    drmom_full = advection_rmom_array + c_N * rmom_full

    return _pack_response_state_strong(drfield_full, drmom_full)


def _unpack_response_state_strong_local(state, grid):
    """Frozen LOCAL copy of unpack_response_state's pre-prompt-23 layout --
    see _pack_response_state_strong's own docstring for why this module
    keeps its own copy."""
    n_max = grid.n_max
    rfield_full = np.empty(n_max + 1)
    rmom_full = np.empty(n_max + 1)
    rfield_full[0] = 0.0
    rmom_full[0] = 0.0
    rfield_full[1:n_max + 1] = state[:n_max]
    rmom_full[1:n_max] = state[n_max:2 * n_max - 1]
    rmom_full[-1] = neumann_boundary_value(rmom_full, grid.D, boundary_index=-1)
    return rfield_full, rmom_full


def self_check_response_assembled_operator(
    n_max: int, alpha: float, N: float, epsilon_core: float = DEFAULT_EPSILON_CORE,
    fd_eps: float = _FD_EPS,
) -> float:
    """
    Self-check companion to assemble_response_operator_strong: builds a
    central finite-difference Jacobian of
    _response_rhs_strong_spatial_only (the frozen, spatial-only-isolated
    local copy above) at the same frozen (n_max, alpha, N, epsilon_core)
    point, and compares it to assemble_response_operator_strong's own
    hand-assembled matrix -- the response-sector analogue of
    self_check_assembled_operator.
    """
    grid = LGLCollocationGrid(n_max + 1)
    n_state = 2 * n_max - 1

    H_sq_nl_init = 1.0
    potential = _FrozenCoefficientPotential(H_sq_value=H_sq_nl_init, epsilon_value=epsilon_core)

    phi0, pi0 = 0.3, -0.05
    phi_splines = [_ConstSpline(phi0) for _ in range(n_max + 1)]
    pi_splines = [_ConstSpline(pi0) for _ in range(n_max + 1)]

    state0 = _pack_response_state_strong(np.zeros(n_max + 1), np.zeros(n_max + 1))

    def _spatial_only(state: np.ndarray) -> np.ndarray:
        return _response_rhs_strong_spatial_only(
            N, state, alpha, H_sq_nl_init, grid, phi_splines, pi_splines, potential,
        )

    jacobian = np.empty((n_state, n_state))
    for k in range(n_state):
        e_k = np.zeros(n_state)
        e_k[k] = fd_eps
        jacobian[:, k] = (_spatial_only(state0 + e_k) - _spatial_only(state0 - e_k)) / (2.0 * fd_eps)

    matrix, _ = assemble_response_operator_strong(n_max, alpha, N, epsilon_core)
    return float(np.max(np.abs(matrix - jacobian)))


def sweep_response_eigenvalues(
    n_max_values, alpha_values, N_values, epsilon_core: float = DEFAULT_EPSILON_CORE,
    closure: str = "strong",
):
    """
    Response-sector analogue of sweep_eigenvalues: one row per (n_max, alpha,
    N) combination, using response_spectral_stability_metrics (NOT
    spectral_stability_metrics directly -- see this section's module
    comment) so the reported spectral_abscissa/n_rhp/growth_efold_time are
    the backward-integration-relevant quantities.

    closure="strong" (default): the pre-port Neumann-eliminated/plain-product
    assemble_response_operator_strong. closure="sbp-sat" (prompt 23 Phase 1
    candidate): assemble_response_operator_sbp_sat instead.
    """
    rows = []
    for n_max in n_max_values:
        for alpha in alpha_values:
            for N in N_values:
                if closure == "sbp-sat":
                    matrix, delta_s_N, _tau, _A_core = assemble_response_operator_sbp_sat(
                        n_max, alpha, N, epsilon_core,
                    )
                elif closure == "strong":
                    matrix, delta_s_N = assemble_response_operator_strong(n_max, alpha, N, epsilon_core)
                else:
                    raise ValueError(
                        f"sweep_response_eigenvalues: closure must be 'strong' or 'sbp-sat', got {closure!r}"
                    )
                eigvals = np.linalg.eigvals(matrix)
                op_norm = float(np.linalg.norm(matrix, ord=2))
                max_abs_re = float(np.max(np.abs(eigvals.real)))
                max_abs_im = float(np.max(np.abs(eigvals.imag)))
                max_abs_lambda = float(np.max(np.abs(eigvals)))
                implied_dt = (
                    RK45_REAL_AXIS_STABILITY_RADIUS / max_abs_lambda
                    if max_abs_lambda > 0.0 else float("inf")
                )
                stability_metrics = response_spectral_stability_metrics(eigvals)
                rows.append({
                    "n_max": n_max,
                    "alpha": alpha,
                    "N": N,
                    "delta_s_N": delta_s_N,
                    "op_norm": op_norm,
                    "max_abs_re_lambda": max_abs_re,
                    "max_abs_im_lambda": max_abs_im,
                    "implied_rk45_max_dt": implied_dt,
                    **stability_metrics,
                })
    return rows


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
    *, include_gradient: bool, include_advection: bool, advection_fn=advection_term,
) -> np.ndarray:
    """
    Full-node forward spatial operator (no boundary elimination -- every
    phi/pi node is a free row/column), shape (2*(n_max+1), 2*(n_max+1)),
    stacked as (phi_full, pi_full) -> (dphi_full, dpi_full). Mirrors
    assemble_spatial_operator's frozen-coefficient conventions exactly, with
    the gradient and advection contributions independently maskable so the
    "advection-only"/"gradient-only" block-mismatch decomposition (prompt 18)
    can reuse this one assembly rather than three near-duplicates.

    advection_fn (default advection_term, prompt 18/18a's own plain-product
    convention): pass advection_split_term (prompt 23) to build the operator
    with the SAME split-form advection the current PRODUCTION forward_rhs.py
    actually uses (prompt 21a) -- see
    compute_forward_sat_vs_response_adjoint_diagnostics below, which uses
    this to re-run the adjoint-consistency check against the closure that is
    actually live in production, not the pre-prompt-21 baseline this
    function still defaults to (so existing prompt-18/18a callers/tests are
    completely unaffected by this parameter's addition).
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
            advection_phi = advection_fn(phi_full, A_array, grid.D)
            advection_pi = advection_fn(pi_full, A_array, grid.D)
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


def compute_forward_sat_vs_response_adjoint_mismatch(
    n_max: int, alpha: float, N: float, epsilon_core: float = DEFAULT_EPSILON_CORE,
) -> dict:
    """
    Prompt 23 Phase 1's adjoint-consistency checkbox: "Run 18a's
    boundary-mismatch check on the SAT'd forward/response pair; confirm the
    boundary mismatch does not grow with n and the response closure is the
    forward's discrete adjoint to the expected level."

    Since Phase 1's own eigenvalue diagnostic (assemble_response_operator_sbp_sat,
    response_spectral_stability_metrics -- see that section's module
    comment) found the response sector's pre-port "strong" closure is
    ALREADY bounded in n_max for its own (backward) integration direction,
    and a naive same-recipe SBP-SAT port makes the safe-direction stiffness
    (max Re) markedly WORSE with no compensating benefit (the design note
    has the full numbers), prompt 23 does NOT port the response sector's
    advection to the SBP-SAT closure (see this module's own response-sector
    section for the full account). "The SAT'd forward/response pair" this
    function checks is therefore: the CURRENT PRODUCTION forward operator
    (prompt 21a's split-form advection, via _forward_operator_full_node's
    advection_fn=advection_split_term) against the UNCHANGED response
    operator (_response_operator_full_node, plain advection_term, as it was
    pre-prompt-23) -- i.e. this directly answers "did porting the FORWARD
    sector alone (already done, prompt 21a) leave the two sectors'
    boundary-mismatch bounded, or did it introduce a NEW n-growing
    mismatch by making the two sectors' advection treatments asymmetric?"

    Returns a dict with the same block_mismatch_*/block_mismatch_*_interior
    keys as compute_adjoint_diagnostics, computed for the FULL operator
    (gradient + advection together) only -- the advection-only/gradient-only
    decomposition is not repeated here since compute_adjoint_diagnostics
    already establishes (prompt 18a) that the gradient piece alone is not
    the source of any n-growth; this function's whole purpose is the
    advection-closure-asymmetry question specifically.
    """
    grid = LGLCollocationGrid(n_max + 1)
    delta_s_N = float(delta_s(N, 0.0, 1.0, 1.0, alpha))
    n_full = grid.n_collocation_points
    keep = _interior_node_indices(n_full)

    w_full_node = _node_weight_array(grid, delta_s_N)
    w_b_full_node = np.concatenate([w_full_node, w_full_node])
    keep2 = np.concatenate([keep, keep + n_full])

    F_sat = _forward_operator_full_node(
        grid, alpha, N, epsilon_core, include_gradient=True, include_advection=True,
        advection_fn=advection_split_term,
    )
    R_unchanged = _response_operator_full_node(
        grid, alpha, N, epsilon_core, include_gradient=True, include_advection_and_c=True,
    )

    return {
        "delta_s_N": delta_s_N,
        "block_mismatch_full": _block_mismatch(F_sat, R_unchanged, w_b_full_node),
        "block_mismatch_full_interior": _block_mismatch(F_sat, R_unchanged, w_b_full_node, keep=keep2),
    }


def sweep_forward_sat_vs_response_adjoint_mismatch(
    n_max_values, alpha_values, N_values, epsilon_core: float = DEFAULT_EPSILON_CORE,
):
    """Computes one row per (n_max, alpha, N) combination -- see
    compute_forward_sat_vs_response_adjoint_mismatch's own docstring."""
    rows = []
    for n_max in n_max_values:
        for alpha in alpha_values:
            for N in N_values:
                diagnostics = compute_forward_sat_vs_response_adjoint_mismatch(n_max, alpha, N, epsilon_core)
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


def spectral_stability_metrics(eigvals: np.ndarray) -> dict:
    """
    Signed spectral abscissa, right-half-plane eigenvalue count, and growth
    e-fold time for an assembled operator's eigenvalues `eigvals` (prompt 20).

    Unlike `max_abs_re_lambda` (prompt 17), `spectral_abscissa = max(ev.real)`
    keeps its SIGN: `> 0` means the semi-discrete system has a genuinely
    growing mode -- no time integrator, explicit or implicit, can rescue it,
    because it would be faithfully integrating an ODE that is itself blowing
    up. `n_rhp` counts eigenvalues with real part exceeding a *relative*
    threshold (`RHP_REL_TOL * max(1, max|lambda|)`), so the count stays
    meaningful across the O(n_max^4) growth in eigenvalue magnitude rather
    than using a fixed absolute cutoff. `growth_efold_time = 1/spectral_abscissa`
    is the e-fold timescale of the fastest growing mode, directly comparable
    to `N_total`; it is reported as `inf` when there is no growing mode
    (`spectral_abscissa <= 0`).
    """
    real_parts = eigvals.real
    spectral_abscissa = float(np.max(real_parts))
    max_abs_lambda = float(np.max(np.abs(eigvals)))
    rhp_tol = RHP_REL_TOL * max(1.0, max_abs_lambda)
    n_rhp = int(np.sum(real_parts > rhp_tol))
    growth_efold_time = (
        1.0 / spectral_abscissa if spectral_abscissa > 0.0 else float("inf")
    )
    return {
        "spectral_abscissa": spectral_abscissa,
        "n_rhp": n_rhp,
        "growth_efold_time": growth_efold_time,
    }


def sweep_eigenvalues(
    n_max_values, alpha_values, N_values, epsilon_core: float = DEFAULT_EPSILON_CORE,
    closure: str = "strong",
):
    """Computes one row per (n_max, alpha, N) combination in the Cartesian
    product of the three input lists. Returns a list of dicts with keys
    matching CSV_FIELDNAMES.

    closure="strong" (default, unchanged prompt-17/20 behaviour): the
    existing Neumann-eliminated/plain-product assemble_spatial_operator.
    closure="sbp-sat" (prompt 21): assemble_spatial_operator_sbp_sat instead
    -- same CSV schema either way (the two closures differ in the numbers,
    not the columns), so before/after comparisons are two separate sweeps
    rather than a combined column."""
    rows = []
    for n_max in n_max_values:
        for alpha in alpha_values:
            for N in N_values:
                if closure == "sbp-sat":
                    matrix, delta_s_N, _tau, _A_core = assemble_spatial_operator_sbp_sat(
                        n_max, alpha, N, epsilon_core,
                    )
                elif closure == "strong":
                    matrix, delta_s_N = assemble_spatial_operator(n_max, alpha, N, epsilon_core)
                else:
                    raise ValueError(
                        f"sweep_eigenvalues: closure must be 'strong' or 'sbp-sat', got {closure!r}"
                    )
                eigvals = np.linalg.eigvals(matrix)
                op_norm = float(np.linalg.norm(matrix, ord=2))
                max_abs_re = float(np.max(np.abs(eigvals.real)))
                max_abs_im = float(np.max(np.abs(eigvals.imag)))
                max_abs_lambda = float(np.max(np.abs(eigvals)))
                implied_dt = (
                    RK45_REAL_AXIS_STABILITY_RADIUS / max_abs_lambda
                    if max_abs_lambda > 0.0 else float("inf")
                )
                stability_metrics = spectral_stability_metrics(eigvals)
                rows.append({
                    "n_max": n_max,
                    "alpha": alpha,
                    "N": N,
                    "delta_s_N": delta_s_N,
                    "op_norm": op_norm,
                    "max_abs_re_lambda": max_abs_re,
                    "max_abs_im_lambda": max_abs_im,
                    "implied_rk45_max_dt": implied_dt,
                    **stability_metrics,
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


def plot_spectral_abscissa(n_max_values, alpha, N, epsilon_core: float, output_path: Path) -> None:
    """
    Signed spectral abscissa vs n_max (prompt 20), at a single representative
    (alpha, N) point near N_init (small Delta_s) -- a y=0 reference line
    makes a positive, n_max-growing curve read as instability at a glance,
    consistent with the empirical blow-up localizing near N_init.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    abscissa_values = []
    for n_max in n_max_values:
        matrix, _ = assemble_spatial_operator(n_max, alpha, N, epsilon_core)
        eigvals = np.linalg.eigvals(matrix)
        abscissa_values.append(spectral_stability_metrics(eigvals)["spectral_abscissa"])

    fig, ax = plt.subplots(figsize=(6, 5))
    ax.axhline(0.0, color="k", linewidth=0.8, linestyle="--")
    ax.plot(n_max_values, abscissa_values, marker="o", color="C3")
    ax.set_xlabel(r"$n_{\max}$")
    ax.set_ylabel(r"spectral abscissa $\max(\mathrm{Re}\,\lambda)$")
    ax.set_title(rf"Signed spectral abscissa ($\alpha={alpha:.3g}$, $N={N:.3g}$)")
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
        "--closure", type=str, default="strong", choices=["strong", "sbp-sat"],
        help="Only affects --mode spectrum. 'strong' (default, unchanged "
             "prompt-17/20 behaviour): Neumann-eliminated core, plain-"
             "product advection. 'sbp-sat' (prompt 21 Phase 1b): split-form "
             "advection plus the core SAT penalty (default: %(default)s).",
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

    check_n_max = 8
    check_alpha = alpha_values[0] if alpha_values else 0.05
    check_N = N_values[-1] if N_values else 5.0

    self_check_diff = self_check_assembled_operator(
        n_max=check_n_max, alpha=check_alpha, N=check_N, epsilon_core=args.epsilon_core,
    )
    print(f"Self-check (assembled operator vs. finite-difference Jacobian of "
          f"forward_rhs): max abs diff = {self_check_diff:.3e}")

    check_matrix, _ = assemble_spatial_operator(check_n_max, check_alpha, check_N, args.epsilon_core)
    check_metrics = spectral_stability_metrics(np.linalg.eigvals(check_matrix))
    print(f"Self-check point (n_max={check_n_max}, alpha={check_alpha:.3g}, N={check_N:.3g}): "
          f"spectral_abscissa = {check_metrics['spectral_abscissa']:.3e}, "
          f"n_rhp = {check_metrics['n_rhp']}")

    rows = sweep_eigenvalues(n_max_values, alpha_values, N_values, args.epsilon_core, args.closure)
    output_path = Path(args.output)
    write_csv(rows, output_path)
    print(f"Wrote {len(rows)} sweep points to {output_path} (closure={args.closure})")

    if args.plot:
        if args.closure != "strong":
            print(
                f"Note: --plot's scatter/abscissa plots always use the 'strong' "
                f"closure's assemble_spatial_operator (unaffected by --closure) -- "
                f"pass --closure sbp-sat and compare the written CSVs directly for "
                f"a closure-vs-closure comparison."
            )
        plot_path = output_path.with_suffix(f".{args.plot_format}")
        plot_spectrum_scatter(
            n_max_values, max(alpha_values), max(N_values), args.epsilon_core, plot_path,
        )
        print(f"Wrote spectrum scatter plot to {plot_path}")

        abscissa_plot_path = output_path.with_name(
            f"{output_path.stem}_abscissa"
        ).with_suffix(f".{args.plot_format}")
        plot_spectral_abscissa(
            n_max_values, max(alpha_values), min(N_values), args.epsilon_core, abscissa_plot_path,
        )
        print(f"Wrote spectral abscissa vs n_max plot to {abscissa_plot_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
