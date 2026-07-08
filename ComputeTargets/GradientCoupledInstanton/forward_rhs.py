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

Physics framing -- lambda-scaling (prompt 23 Part B)
-------------------------------------------------------------------------
noise_source_terms/forward_rhs each carry an optional lam parameter
(default 1.0, a complete no-op preserving every pre-prompt-23 call site's
behaviour exactly). Production usage (picard.py) sets it to the outer
shooting loop's actual lambda and passes RESCALED response-field splines
(r_tilde = r/lam, reconstructing response_rhs.terminal_response_state_rescaled's
own backward solve) rather than the astronomic physical ones -- see
response_rhs.py's own module docstring for the full derivation (response_rhs
is exactly linear and homogeneous in the response fields, so this rescaling
is exact, not an approximation) and noise_source_terms's own docstring for
exactly how lam re-enters (as (D*lam)*r_tilde, D*lam computed first).

Physics framing -- SBP-SAT boundary closure (prompt 21/21a)
-------------------------------------------------------------------------
The continuum problem is well-posed: advection-diffusion with a regularity
("natural") condition at the coordinate centre y=+1 (the core) -- like a
driven heat bar where one end is specified data and the far end's value is
an *output* of the dynamics plus regularity, not imposed data. The core field
values are things this model *solves for*, not boundary data it is handed.

What used to fail was purely the discretisation, not the physics: centred
spectral collocation of the advection-dominated spatial operator, with the
core boundary conditions imposed *strongly* (phi_core node-eliminated via a
Neumann formula, never itself integrated), loses the discrete energy
estimate that mirrors the continuum well-posedness. That produces spurious
right-half-plane eigenvalues whose real part grows like n_max^1.6
(integrator-independent -- RK45, Radau, BDF all fail; LSODA returns NaN with
success=True) -- see .documents/gradient-coupled-instanton/
21-sbp-sat-design-note.md for the full derivation.

The fix (SBP-SAT) restores the discrete energy estimate by (a) writing the
advection term in the skew-symmetric "split form" (Numerics.DiscretizedOperators
.advection_split_term) instead of the plain product, and (b) adding a
dissipative SAT ("Simultaneous Approximation Term") penalty at the core node
that exactly cancels the one boundary term the split form still carries. This
does NOT add a new physical boundary condition -- the SAT's *target* value g
is chosen so that the penalty forcing vanishes at the true solution:

  - g_phi (phi_core's target) is the same Neumann/regularity value the old
    strong elimination already imposed (neumann_boundary_value, recomputed
    live from the OTHER, currently-integrated phi nodes at every RHS call --
    never from phi_core itself, so it is never self-referential). Because it
    is recomputed from the live, evolving interior state at every call (not
    frozen across Picard sweeps), it needs no additional lagging: as the
    interior nodes approach their converged shape, g_phi automatically
    approaches consistency with phi_core, and the penalty forcing vanishes
    on its own. See .documents/gradient-coupled-instanton/
    21-sbp-sat-design-note.md Section 6 for why this is the right target
    for phi and why it does not need Picard-level lagging.
  - g_pi (pi_core's target) has no existing analogue to fall back on --
    pi_core previously had NO boundary condition at all (a totally free,
    unconstrained DOF). There is nothing "live" to compute it from, so its
    target is instead the LAGGED, SELF-CONSISTENT core pi(N) trajectory from
    the previous Picard sweep (threaded in as g_pi_core_spline, built by
    picard.py the same way the rfield/rmom response-field splines already
    are), seeded at sweep 0 from a FullInstanton profile. At Picard
    convergence g_pi_core_spline(N) -> pi_core(N) exactly, so the penalty
    forcing -> 0 there too. See picard.py's own module docstring for the
    sweep-to-sweep update and the FullInstanton seed.

Either way, the SAT is a *stabiliser*, not new physics: at the converged
solution both penalties vanish and the model reduces exactly to the
unpenalised continuum dynamics, with regularity (d(pi)/dy -> 0 at the core)
emerging from phi's own regularity through pi = dphi/dN, rather than being
separately imposed.

HOW TO VERIFY THIS IS STILL CORRECT: three checks must stay green --
  (a) the prompt-20/21 abscissa diagnostic (analyze_StiffnessSpectrum.py
      --mode spectrum --closure sbp-sat): spectral_abscissa flat in n_max;
  (b) tests/test_sbp_sat_boundary_closure.py's SAT energy-cancellation check
      (the boundary energy term is <= 0 after the penalty, Phase-1 prototype);
  (c) tests/test_forward_rhs.py's closure-independence (two-seed) regression:
      the converged core trajectory does not depend on which seed started
      Picard sweep 0.

State vector layout (prompt 21a -- CHANGED from the strong-BC layout)
-------------------------------------------------------------------------
Not all 2*(n_max+1) raw grid values are independently integrated:

  - phi_0, pi_0 (outer edge, y=-1): Dirichlet-pinned to
    trajectory.phi_at(N_offset + N)/.pi_at(N_offset + N) -- not integrated,
    recomputed fresh at every RHS call. A(-1) = 0 exactly (see the design
    note's Section 3), so this edge carries no destabilising energy term and
    needs no SAT: the strong Dirichlet imposition here is deliberately left
    unchanged.
  - phi_{n_max} (core): FORMERLY Neumann-eliminated (not integrated, not
    part of the state). NOW a free, integrated DOF, weakly (SAT-)penalised
    toward its live-computed regularity target g_phi (see above) -- this is
    exactly the "stop eliminating the core node" change the SBP-SAT closure
    requires: node elimination is itself what breaks the discrete energy
    estimate, independent of which field is eliminated.
  - pi_{n_max} (core momentum): was already free/integrated; now ALSO
    weakly SAT-penalised toward its lagged target g_pi (see above) --
    previously this node had no boundary condition of any kind.
  - Everything else (phi_1,...,phi_{n_max-1}, pi_1,...,pi_{n_max-1}) is
    integrated exactly as before.

So the ODE state vector now has length 2*n_max (one entry longer than the
old strong-BC layout's 2*n_max-1, since phi_core is promoted from
eliminated to integrated):
(phi_1,...,phi_{n_max}, pi_1,...,pi_{n_max}).
"""

import numpy as np

from Numerics.OnionCoordinate import delta_s, advection_coefficient
from Numerics.DiscretizedOperators import (
    L_operator,
    advection_split_term,
    neumann_boundary_value,
)


def pack_state(phi_full: np.ndarray, pi_full: np.ndarray) -> np.ndarray:
    """
    Restrict (phi_full, pi_full), each of length n_max+1, to the integrated
    state vector of length 2*n_max: (phi_1,...,phi_{n_max}, pi_1,...,
    pi_{n_max}). Drops only phi_full[0]/pi_full[0] (Dirichlet-pinned outer
    edge) -- unlike the pre-prompt-21a layout, phi_full[-1] (the core) is now
    KEPT, not dropped, since it is an integrated DOF rather than
    Neumann-eliminated. See the module docstring's "State vector layout"
    section for the full account of this change.
    """
    return np.concatenate([phi_full[1:], pi_full[1:]])


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

    Indices 1..n_max (interior + core, both fields): read directly from the
    state vector -- no elimination of any kind. Prompt 21a change: phi_full
    [-1] (the core) used to be overwritten here via neumann_boundary_value;
    it is now simply unpacked like every other interior node, since it is an
    integrated DOF. The Neumann/regularity formula is still used elsewhere
    (forward_rhs's own g_phi SAT target), just no longer to *set* this value.

    alpha, H_sq_nl_init, and potential are threaded through for a signature
    shared with forward_rhs's local context; unpack_state itself only needs
    N_offset (for the trajectory lookup).
    """
    n_max = grid.n_max

    phi_full = np.empty(n_max + 1)
    pi_full = np.empty(n_max + 1)

    phi_full[0] = trajectory.phi_at(N_offset + N)
    pi_full[0] = trajectory.pi_at(N_offset + N)

    phi_full[1:n_max + 1] = state[:n_max]
    pi_full[1:n_max + 1] = state[n_max:2 * n_max]

    return phi_full, pi_full


def n_count(
    delta_s_N: float,
    delta_s_loc_array: np.ndarray,
    grid,
) -> np.ndarray:
    """
    Shell-dilution factor n_count(y_j,N) (eq. ncount):
    (3/2) Delta_s(N) e^{3 Delta_s_loc(y,N)} e^{-3/2 (y+1) Delta_s(N)}.

    Factored out of diluted_diffusion_coefficients's own body (which is its
    only production caller) so it is independently, directly testable
    against eq:ncount's closed form -- every existing test touching
    n_count previously constructed its own reference value from this same
    formula, so a wrong exponent/prefactor/node-indexing here would have
    cancelled identically on both sides and never been caught. Purely
    additive: no behavior change to diluted_diffusion_coefficients.

    delta_s_N is the core-only Delta_s(N) (defines the coordinate map
    itself); delta_s_loc_array is the per-node Delta_s_loc(y_j,N).

    Returns an array shape (n_nodes,).
    """
    return (
        1.5 * delta_s_N
        * np.exp(3.0 * delta_s_loc_array)
        * np.exp(-1.5 * (grid.nodes + 1.0) * delta_s_N)
    )


def diluted_diffusion_coefficients(
    phi_full: np.ndarray,
    pi_full: np.ndarray,
    delta_s_N: float,
    delta_s_loc_array: np.ndarray,
    grid,
    potential,
    diffusion_model,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Shell-diluted diffusion coefficients (D_phi, D_pi, D_phipi) -- the same
    coefficients that dress rfield/rmom in noise_source_terms's own sourcing
    terms below. Factored out as its own function so noise summary-statistics
    constructions (e.g. GradientCoupledInstanton's own dimensionless,
    Hawking-standard-deviation noise_field/noise_mom columns, which need the
    coefficients alone, not sourced by any particular rfield/rmom) can reuse
    them without duplicating the n_count/D_matrix loop.

    Steps 2-3 of forward_rhs's own assembly: the shell-dilution factor
    n_count(y_j,N) (eq. ncount) and the per-node diffusion matrix D_matrix
    loop, combined into the diluted coefficients D_phi = 2*D11/n_count,
    D_pi = 2*D22/n_count, D_phipi = 2*D12/n_count.

    delta_s_N is the core-only Delta_s(N) (defines the coordinate map itself);
    delta_s_loc_array is the per-node Delta_s_loc(y_j,N) -- both already
    computed by the caller, passed through rather than recomputed here.

    Returns (D_phi_arr, D_pi_arr, D_phipi_arr), each shape (n_nodes,).
    """
    n_nodes = phi_full.shape[0]

    n_count_array = n_count(delta_s_N, delta_s_loc_array, grid)

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

    return D_phi_arr, D_pi_arr, D_phipi_arr


def noise_source_terms(
    phi_full: np.ndarray,
    pi_full: np.ndarray,
    rfield_full: np.ndarray,
    rmom_full: np.ndarray,
    delta_s_N: float,
    delta_s_loc_array: np.ndarray,
    grid,
    potential,
    diffusion_model,
    lam: float = 1.0,
) -> tuple[np.ndarray, np.ndarray]:
    """
    Diluted noise-source terms sourcing the forward equations (eq. Dnoise-diag,
    Dnoise-cross), factored out of forward_rhs's own assembly so the noise
    summary-statistics columns (noise_field_min/mean/max, noise_mom_min/
    mean/max) can call it directly at every row of the dense solver grid, not
    just inside a single RHS evaluation.

    D_phi*rfield + D_phipi*rmom (sourcing dphi_full) and
    D_pi*rmom + D_phipi*rfield (sourcing dpi_full), where D_phi/D_pi/D_phipi
    are diluted_diffusion_coefficients's own output.

    delta_s_N is the core-only Delta_s(N) (defines the coordinate map itself);
    delta_s_loc_array is the per-node Delta_s_loc(y_j,N) -- both already
    computed by the caller, passed through rather than recomputed here.

    lam (prompt 23 Part B; default 1.0, i.e. no-op, matching every pre-
    prompt-23 call site's behaviour exactly): the response-response's own
    lambda-scaling multiplier. WHAT: when lam=1.0 (the default), rfield_full/
    rmom_full are read as the PHYSICAL response fields, exactly as before --
    this function's behaviour and every existing caller/test is completely
    unchanged. When lam != 1.0 (production usage from prompt 23 onward, via
    forward_rhs's own lam parameter below), rfield_full/rmom_full are
    instead the RESCALED r_tilde = r/lam fields (see
    response_rhs.terminal_response_state's own docstring for the full
    derivation of why this rescaling is exact by linearity), and this
    function reconstructs the physical sourcing term as (D*lam)*r_tilde --
    computing D*lam FIRST, as its own array, before multiplying by the
    (much smaller-magnitude) rescaled field, rather than materializing
    lam*r_tilde ~ O(1e9-1e15) as a bare intermediate first and only then
    multiplying by the tiny D ~ O(1e-11). WHY: D*lam is the genuinely
    physical, well-conditioned O(1)-ish quantity (D ~ H^2/(8 pi^2), a rare-
    event diffusion coefficient; lam ~ 1/D is what a rare fluctuation
    costs -- their product is the astronomic scale FACTORED OUT, see
    response_rhs.py's own module docstring). FAILURE SIGNATURE of grouping
    the other way (lam*rfield_full first): not a single-operation precision
    loss (IEEE double arithmetic is safe at either magnitude here), but
    every OTHER call site downstream that might reuse an already-scaled
    lam*r_tilde intermediate for something that should have stayed at the
    r_tilde scale (e.g. the backward ODE's OWN state vector, which must
    stay unscaled for prompt 23 Part B's conditioning fix to do anything at
    all) becomes silently wrong if the two conventions are ever mixed at a
    call site -- this grouping is the discipline that keeps the boundary
    between scaled and unscaled quantities explicit at the one place they
    cross, rather than leaving it implicit and easy to get backwards.

    Returns (noise_field_array, noise_mom_array), each shape (n_nodes,).
    """
    D_phi_arr, D_pi_arr, D_phipi_arr = diluted_diffusion_coefficients(
        phi_full, pi_full, delta_s_N, delta_s_loc_array, grid, potential, diffusion_model,
    )
    D_phi_lam_arr = D_phi_arr * lam
    D_pi_lam_arr = D_pi_arr * lam
    D_phipi_lam_arr = D_phipi_arr * lam

    noise_field_array = D_phi_lam_arr * rfield_full + D_phipi_lam_arr * rmom_full
    noise_mom_array = D_pi_lam_arr * rmom_full + D_phipi_lam_arr * rfield_full

    return noise_field_array, noise_mom_array


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
    g_pi_core_spline,
    disable_spatial_coupling: bool = False,
    lam: float = 1.0,
) -> np.ndarray:
    """
    Forward-sector RHS (eq. inst-phi/inst-pi), always sourced by the current
    response fields, and (prompt 21a) always closed by the core SAT penalty.

    rfield_splines/rmom_splines are one SplineWrapper per grid node (length
    n_max+1 each), reconstructing the current backward-pass response-field
    solution at whatever N the forward integrator is currently at -- built
    by the caller (the Picard driver) from the most recent response_rhs
    solve. The all-zero-response "zeroth Picard iterate" is just a
    particular choice of these splines (constant zero), not a separate code
    path.

    lam (prompt 23 Part B; default 1.0, matching every pre-prompt-23 call
    site exactly): threaded straight through to noise_source_terms's own
    lam parameter (see that function's docstring for the full scaling
    convention). WHAT rfield_splines/rmom_splines RECONSTRUCT DEPENDS ON
    THIS PARAMETER -- read together, not independently: with the default
    lam=1.0, they reconstruct the PHYSICAL rfield_full(N)/rmom_full(N)
    (unchanged pre-prompt-23 behaviour). With lam set to the actual outer-
    loop shooting parameter (production usage, picard.py), they instead
    reconstruct the RESCALED r_tilde_full(N) = r_full(N)/lam (built by the
    caller from a response_rhs backward pass started at
    response_rhs.terminal_response_state_rescaled, not the astronomic
    terminal_response_state(lam, ...)) -- and lam here supplies the missing
    factor back, via noise_source_terms's (D*lam)*r_tilde grouping, so the
    net sourcing term is exactly the same physical quantity either way.
    Mixing conventions (e.g. astronomic-lambda splines with lam=1.0 here, or
    rescaled splines with lam left at its default) would silently source
    the wrong (off by a factor of lam) forward feedback -- see
    response_rhs.py's own module docstring for why this boundary is
    documented at every crossing point.

    g_pi_core_spline is a SINGLE SplineWrapper (not one per node -- the SAT
    target only exists at the core), reconstructing the lagged
    self-consistent pi_core(N) target from the previous Picard sweep (or the
    FullInstanton seed, at sweep 0). See the module docstring's physics
    framing above and picard.py's own docstring for how it is built/updated.
    phi_core's SAT target has no equivalent spline argument: it is computed
    live, in-line below, from the currently-unpacked phi_full via
    neumann_boundary_value -- see the module docstring for why phi and pi
    are treated differently.

    disable_spatial_coupling=True zeroes the gradient term, both advection
    contributions, AND both SAT penalties together -- the SAT is part of the
    same spatial-coupling closure as the advection/gradient terms (it exists
    only to cancel an advection-operator boundary defect), so when advection
    is switched off there is nothing left for it to cancel; leaving it on
    would inject a spurious penalty into what is supposed to be a set of
    decoupled single-trajectory ODEs, breaking the reduction-limit tests
    that compare this mode directly against FullInstanton. It does NOT zero
    the response-field sourcing terms, which remain active (matching
    FullInstanton's own fwd_rhs, which always includes its P1/P2 sourcing
    terms regardless of gradient coupling).
    """
    phi_full, pi_full = unpack_state(
        state, N, N_offset, alpha, H_sq_nl_init, grid, trajectory, potential
    )

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
        sat_phi_core = 0.0
        sat_pi_core = 0.0
    else:
        L_phi_array = L_operator(phi_full, delta_s_N, grid.nodes, grid.D, grid.D2)
        gradient_term = np.exp(-2.0 * delta_s_loc_array) * L_phi_array

        # ---------------------------------------------------------------
        # Split-form advection (prompt 21a). WHAT: replaces the plain
        # product diag(A) @ D with the product-rule-consistent split form
        # (Numerics.DiscretizedOperators.advection_split_term). WHY: the
        # plain product is not skew under the LGL norm H=diag(grid.weights)
        # in the interior; the split form is, up to a single boundary term
        # at the core (design note Section 3). FAILURE SIGNATURE of using
        # the plain product here instead: spectral_abscissa of the
        # assembled operator grows like n_max^1.6, integrator-independent
        # (this is exactly the bug this prompt fixes, not a hypothetical).
        # ENERGY-ESTIMATE STEP: design note Section 3 ("Exact SBP defect of
        # the split-form advection operator").
        # ---------------------------------------------------------------
        epsilon_core = epsilon_loc_array[-1]
        A_array = advection_coefficient(grid.nodes, delta_s_N, epsilon_core)
        advection_phi_array = advection_split_term(phi_full, A_array, grid.D)
        advection_pi_array = advection_split_term(pi_full, A_array, grid.D)

        # ---------------------------------------------------------------
        # SAT boundary closure at the core (y=+1), prompt 21a.
        #
        # WHAT: a dissipative penalty -tau/w_core * (u_core - g_u) added to
        # each field's own core-row derivative, tau = A(core)/2.
        #
        # WHY: the split-form advection operator above is skew under
        # H=diag(grid.weights) everywhere EXCEPT a single core-row term of
        # size ~A(core) (design note Section 3) -- an O(1), n_max-INDEPENDENT
        # destabilising energy source that dominates as the grid refines and
        # every other (properly shrinking, w_j -> 0) diagonal entry becomes
        # negligible by comparison. tau = A(core)/2 is the exact-cancellation
        # value: substituting it into the discrete energy balance
        # dE/dN = -a'*E + (1/2 A(core) - tau) u_core^2 + tau*u_core*g makes
        # the u_core^2 coefficient vanish identically, leaving pure decay at
        # rate a' plus a bounded forcing term -- see design note Section 4
        # for the full derivation. tau applies identically to phi and pi:
        # advection uses the same A_array for both fields, so both fields
        # carry the same core-row defect independently and both need the
        # penalty (using it on only one field leaves the OTHER field's core
        # row uncancelled).
        #
        # WHAT A WRONG VERSION LOOKS LIKE: tau=0 reduces to the plain
        # split-form operator, still carrying the destabilising core entry;
        # tau < A(core)/2 only partially cancels it (bounded-but-still-
        # positive abscissa, an under-damped variant); applying the penalty
        # to only one of phi/pi leaves the other's defect untouched.
        #
        # THE TARGETS g_phi / g_pi -- deliberately NOT the same kind of
        # object (see module docstring's physics framing and design note
        # Section 6):
        #   g_phi: computed LIVE at every call from the OTHER (non-core)
        #     phi nodes via the same Neumann/regularity formula the old
        #     strong elimination used (neumann_boundary_value) -- this is
        #     the direct weak analogue of the previous strong condition, not
        #     a value-type closure, and needs no Picard-sweep lagging since
        #     it is recomputed from the live, currently-integrated interior
        #     state at every RHS call (never from phi_core itself, so it
        #     can never be identically self-cancelling).
        #   g_pi: NO existing condition to weakly reproduce (pi_core was
        #     previously completely unconstrained), so its target is the
        #     LAGGED SELF-CONSISTENT core pi(N) trajectory from the previous
        #     Picard sweep, reconstructed via g_pi_core_spline (built and
        #     updated by picard.py; seeded from a FullInstanton profile at
        #     sweep 0). At Picard convergence g_pi_core_spline(N) ->
        #     pi_core(N), so this penalty's forcing -> 0 there too, exactly
        #     like g_phi's.
        # ---------------------------------------------------------------
        A_core = float(A_array[-1])
        # tau = |A_core|, NOT 0.5*A_core (design note Section 4's literal,
        # minimal-admissible value) -- TWO deliberate hardenings beyond the
        # Phase-1 frozen-coefficient derivation, both discovered empirically
        # during Phase-2 acceptance testing (prompt 21a) on the production
        # case (N_init=19.5, N_final=16, delta_Nstar=0.1, alpha=0.1) and NOT
        # visible in Phase-1's linear, frozen-coefficient eigenvalue sweep:
        #
        # (1) abs(), not the signed A_core -- SIGN ROBUSTNESS.
        #     A_core = 2*a', a' = (1-epsilon_core)/Delta_s(N), is positive
        #     only while epsilon_core < 1. That holds at the CONVERGED
        #     solution (N_final is chosen before the true end of inflation)
        #     but is NOT guaranteed for the trial states visited mid-
        #     shooting/mid-Picard-iteration: a poor intermediate iterate can
        #     transiently push epsilon_core = 0.5*pi_core^2 above 1. A
        #     signed tau = 0.5*A_core flips NEGATIVE exactly when that
        #     happens, turning the SAT from a dissipative closure into an
        #     amplifier -- observed directly as pi_core running away toward
        #     the H_sq denominator singularity (pi_core^2 = 6) within a
        #     fraction of an e-fold, at n_max >= 9 on the production case,
        #     before this fix.
        # (2) a factor of 2 beyond the minimal |A_core|/2 -- ITERATION
        #     STABILITY MARGIN. Promoting phi_core from Neumann-eliminated
        #     to a free, integrated DOF (this same prompt) gives it genuine
        #     dynamical memory it never had before (previously it was
        #     slaved, instantaneously, to the interior nodes with no
        #     independent timescale of its own). At the design note's
        #     minimal tau = 0.5*|A_core|, this new degree of freedom was
        #     observed to develop a persistent, non-decaying O(1) Picard-
        #     sweep oscillation at n_collocation_points=7 on the production
        #     case (visible as max|dphi| across sweeps failing to shrink at
        #     all) -- a genuinely new failure mode the frozen-coefficient
        #     linear analysis cannot see, since it only bounds the per-sweep
        #     OPERATOR's spectrum, not the full nonlinear Picard/shooting
        #     iteration's own convergence. Doubling tau (a strictly stronger,
        #     still-admissible choice per design note Section 4: "any
        #     tau >= A(core)/2 is admissible") suppressed the oscillation
        #     completely -- every n_collocation_points in {5,7,9,11,13,17,33}
        #     then converges in a single outer Newton iteration and a single
        #     Picard sweep on the production case.
        #
        # Both hardenings are safety margin, not a physics change: the exact
        # energy-balance algebra (design note Section 4, re-derived for the
        # signed/rescaled case) gives a core-row dE/dN coefficient of
        # -a'*(1 + w_core/2) when a'>0 (MORE negative / more stable than the
        # minimal recipe's -a'*w_core/2) and a'*(3 - w_core/2) < 0 when a'<0
        # (over-damped, but strictly stabilizing, since w_core < 2 always for
        # LGL weights) -- so this never weakens the closure. See
        # tests/test_forward_rhs.py's SAT-sign-and-margin tests for the
        # regression guards, and the design note addendum
        # (.documents/gradient-coupled-instanton/21a-production-port-notes.md)
        # for the full empirical account.
        tau = abs(A_core)
        w_core = float(grid.weights[-1])

        g_phi_core = neumann_boundary_value(phi_full, grid.D, boundary_index=-1)
        g_pi_core = float(g_pi_core_spline(N))

        sat_phi_core = -(tau / w_core) * (phi_full[-1] - g_phi_core)
        sat_pi_core = -(tau / w_core) * (pi_full[-1] - g_pi_core)

    # Response-field values at the current N, reconstructed node-by-node from
    # the current backward-pass splines -- rfield_full/rmom_full here are
    # r_tilde = r/lam (rescaled) when lam != 1.0, per this function's own
    # docstring; noise_source_terms's lam parameter below supplies the
    # missing factor back via its (D*lam)*r_tilde grouping.
    rfield_full = np.array([spline(N) for spline in rfield_splines])
    rmom_full = np.array([spline(N) for spline in rmom_splines])

    # Diluted noise-source terms (eq. ncount, Dnoise-diag, Dnoise-cross),
    # reusing delta_s_N and delta_s_loc_array already computed above rather
    # than recomputing delta_s() a third time.
    noise_field_array, noise_mom_array = noise_source_terms(
        phi_full, pi_full, rfield_full, rmom_full, delta_s_N, delta_s_loc_array,
        grid, potential, diffusion_model, lam=lam,
    )

    dphi_full = (
        pi_full
        + advection_phi_array
        + noise_field_array
    )
    dpi_full = (
        -(3.0 - epsilon_loc_array) * pi_full
        - dV_array / H_sq_loc_array
        + gradient_term
        + advection_pi_array
        + noise_mom_array
    )

    # SAT penalties act only at the core row (index -1); every other row is
    # untouched. Added last, after the plain assembly above, since they are
    # additive corrections to the core row's own derivative, not part of the
    # per-node formula every other row shares.
    dphi_full[-1] += sat_phi_core
    dpi_full[-1] += sat_pi_core

    return pack_state(dphi_full, dpi_full)
