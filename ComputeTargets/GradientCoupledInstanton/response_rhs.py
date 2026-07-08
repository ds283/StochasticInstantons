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

Prompt 23 Part A finding -- SBP-SAT closure NOT ported (clean negative)
-------------------------------------------------------------------------
Prompt 21a's own scope note (superseded here) flagged this module's
advection_term call as a "known, symmetric follow-on candidate" for the
forward sector's SBP-SAT port, on the theory that the SAME A_array
construction plus rmom_full's OWN Neumann elimination at the core (see
unpack_response_state below) would produce the same n_max-growing spectral
defect forward_rhs.py had before prompt 21/21a.

Prompt 23 Phase 1 tested this directly (analyze_StiffnessSpectrum.py's
response-sector diagnostic section: assemble_response_operator_strong,
assemble_response_operator_sbp_sat, response_spectral_stability_metrics) and
found the symmetry argument does NOT hold once the response sector's actual
integration direction is correctly accounted for. response_rhs is integrated
BACKWARD in N (picard.py's solve_ivp call uses a decreasing t_span), and for
backward integration the numerically catastrophic eigenvalue direction is
the OPPOSITE of the forward sector's (see the diagnostic section's own
module comment in analyze_StiffnessSpectrum.py for the full sign argument).
Correctly analyzed, the pre-port "strong" closure's backward-relevant
spectral abscissa is ALREADY bounded/n_max-independent across the full
default (alpha, N) sweep grid at n_max=8..192 -- there is no disease to
cure. A naive same-recipe SBP-SAT port (even with the sign flip backward
integration requires on the live-Neumann-target field) does not improve
this and measurably worsens the safe-direction stiffness instead. Full
numbers: .documents/gradient-coupled-instanton/
23-response-sbp-sat-design-note.md.

This module's advection therefore remains the plain-product advection_term
below, and rmom_full remains Neumann-eliminated at the core (unpack_response_state,
unchanged) -- both deliberately, not by oversight. If a genuinely new
n_max-dependent failure is found in this sector in the future, re-run the
Phase-1 diagnostic first (it is a permanent regression fixture, not a
one-off check) before assuming the forward sector's fix recipe applies
unchanged.

Prompt 23 Part B -- lambda-scaling convention (astronomic lambda)
-------------------------------------------------------------------------
Independent of Part A: response_rhs (below) is exactly LINEAR AND
HOMOGENEOUS in (rfield, rmom) -- lambda enters this model ONLY through the
terminal condition (terminal_response_state), never through response_rhs's
own right-hand side. So the response solution scales exactly with lambda:
r(N) = lambda * r_tilde(N), where r_tilde solves the IDENTICAL backward-pass
ODE from the O(1)-ish terminal condition
terminal_response_state_rescaled(grid, delta_s_N_final) (==
terminal_response_state(1.0, ...)). Production code (picard.py) integrates
r_tilde, not the astronomic r itself (lambda ~ 1e9-4e9 in the resolved
regime that makes r_core ~ 1e9-1e15) -- carrying that dynamic range through
the adaptive-step backward integrator and the nonlinear Picard/shooting
iteration is what drives the H_sq_local<0/RK45 step-death failures (prompt
22c Finding 4). lambda is reintroduced afterwards in ONE vectorized
multiply (picard.py's own final rfield_grid/rmom_grid reconstruction) and,
separately, inside forward_rhs's noise-sourcing feedback via a dedicated
lam parameter that computes (D*lambda) as one quantity BEFORE multiplying
by r_tilde -- see forward_rhs.py's own module docstring and
noise_source_terms's docstring for that half of the convention.
See terminal_response_state's own docstring for the full rationale.

HOW TO VERIFY THIS IS STILL CORRECT -- three checks must stay green:
  (a) response-abscissa-bounded-in-n (Part A regression):
      tests/test_response_spectrum_prompt23.py's
      test_strong_closure_backward_abscissa_bounded_across_default_grid --
      if this ever fails, re-read the design note before assuming the
      forward sector's SBP-SAT recipe should now be ported (Phase 1 found
      it should not, but that finding is about THIS closure's spectrum, not
      a permanent law -- if the spectrum genuinely changes, re-derive).
  (b) adjoint-consistency (Part A regression):
      tests/test_response_spectrum_prompt23.py's
      test_sat_forward_vs_unchanged_response_mismatch_bounded_in_n -- the
      forward sector's own closure evolving further (a future prompt) could
      reopen this; re-run analyze_StiffnessSpectrum.py's
      compute_forward_sat_vs_response_adjoint_mismatch against whatever the
      forward operator becomes.
  (c) lambda-scaling round-trip (Part B regression):
      tests/test_response_lambda_scaling_prompt23.py's
      test_response_solution_scales_exactly_with_lambda (linearity) and
      test_rescaled_backward_pass_feasible_at_astronomic_lambda
      (feasibility at the resolved-regime lambda scale).
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

    lambda-scaling convention (prompt 23 Part B) -- READ THIS BEFORE PASSING
    A NON-1.0 VALUE HERE. response_rhs (above) is exactly LINEAR AND
    HOMOGENEOUS in (rfield, rmom): it has no lambda-dependence anywhere in
    its own right-hand side, only through whatever terminal_response_state
    it was started from. So by linearity, the response solution scales
    EXACTLY with lambda: r(N) = lambda * r_tilde(N), where r_tilde solves
    the IDENTICAL backward-pass ODE from the O(1)-terminal condition
    terminal_response_state(1.0, grid, delta_s_N_final) -- see
    terminal_response_state_rescaled below, the PREFERRED call for
    production use. Calling this function directly with the true,
    astronomic lambda (~1e9-4e9 in the resolved regime) makes rfield_core
    ~1e5-1e15 in magnitude (delta_s_N_final's own measure(1,.) factor can
    itself be a further ~1e-3 to 1e-20, see the design note), which is
    exactly the materialization Part B exists to avoid: it is not that any
    SINGLE floating-point operation on such a value loses precision (IEEE
    double arithmetic is safe well beyond this range), but that carrying an
    O(1e9+)-dynamic-range component through the SAME adaptive-step
    integrator, the SAME nonlinear Picard/shooting iteration, and the
    forward sector's own noise-sourcing feedback as every OTHER (O(1))
    state component is what empirically drives the H_sq_local<0/RK45
    step-death failures (prompt 22c Finding 4) at the astronomic lambda the
    resolved regime requires.
    """
    n_max = grid.n_max

    rfield_full = np.zeros(n_max + 1)
    rmom_full = np.zeros(n_max + 1)

    rfield_full[-1] = -lam / (grid.weights[-1] * measure(1.0, delta_s_N_final))

    return pack_response_state(rfield_full, rmom_full)


def terminal_response_state_rescaled(grid, delta_s_N_final: float) -> np.ndarray:
    """
    terminal_response_state(1.0, grid, delta_s_N_final) -- the O(1)-ish
    (NOT astronomic) terminal condition for the lambda-RESCALED backward
    pass, r_tilde = r / lambda (prompt 23 Part B). This is the call
    production code (picard.py) should use for the actual backward
    solve_ivp integration; the true lambda is reintroduced afterwards, in
    ONE vectorized multiply, only where a genuinely lambda-scaled physical
    quantity is needed (the forward sector's noise-sourcing feedback -- see
    forward_rhs.noise_source_terms's own lam parameter -- and the physical
    rfield/rmom grids returned by solve_picard for msr_action/datastore
    storage/noise diagnostics). See terminal_response_state's own docstring
    for the full scaling-convention rationale and failure mode this avoids.

    A thin, self-documenting wrapper (not a new formula) so call sites read
    "the rescaled terminal condition", making the scaling boundary explicit
    at the point of use rather than relying on a reader noticing "lam=1.0"
    is deliberate and not a placeholder/bug.
    """
    return terminal_response_state(1.0, grid, delta_s_N_final)
