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

Usage:
    python3 analyze_StiffnessSpectrum.py --output stiffness_spectrum.csv
    python3 analyze_StiffnessSpectrum.py --n-max 8,16,32,64,128 --alpha 0.001,0.05 \
        --N 0.1,5,20,25 --plot
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
from Numerics.DiscretizedOperators import (
    L_operator,
    advection_term,
    neumann_boundary_value,
)
from Numerics.LGLCollocation import LGLCollocationGrid
from Numerics.OnionCoordinate import advection_coefficient, delta_s

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


def write_csv(rows: list, path: Path) -> None:
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDNAMES)
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
        description="Assembled-operator eigenvalue sweep for the "
                     "gradient-coupled instanton's onion-model spatial "
                     "discretisation (prompt 17, Part A).",
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
        "--output", type=str, default="stiffness_spectrum.csv",
        help="Output CSV path (default: %(default)s).",
    )
    parser.add_argument(
        "--plot", action="store_true",
        help="Also write a Re/Im eigenvalue scatter plot (largest alpha/N "
             "in the sweep, one color per n_max) alongside the CSV.",
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
