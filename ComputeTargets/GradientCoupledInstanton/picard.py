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
Picard iteration / shooting driver for the gradient-coupled instanton model
(eq. colloc-eqs, terminal-colloc, shooting), tying together the forward and
response collocation right-hand sides of forward_rhs.py / response_rhs.py.

Mirrors FullInstanton's own adjoint/Picard/outer-Newton structure
(ComputeTargets/FullInstanton.py's _compute_full_instanton) as closely as the
grid-valued generalization allows: the same constants, the same overall
shape (seed -> Picard inner loop -> outer shooting loop on lambda),
generalized from scalar (phi, pi, P1, P2) arrays over N to grid-valued
arrays over (N, y) of shape (len(N_grid), n_collocation_points). Prompt 22c
made this mirroring closer still: FullInstanton is now GradientCoupledInstanton's
own SEED SOURCE (see below), and both modules share the same outer-loop
hardening via Numerics/ShootingSolver.py.

N convention -- matches FullInstanton exactly. N_init/N_final/delta_Nstar
are supplied in the same "e-folds before the end of inflation" convention
as FullInstanton's own constructor parameters (N_init > N_final;
delta_Nstar the excess duration added on top of the naive N_init-N_final
span), and N_total = (N_init - N_final) + delta_Nstar is the same quantity
FullInstanton computes. But the running N actually integrated over here is
local and zero-based, exactly like FullInstanton's own t_span: it starts at
0.0 (the transition start) and increases to N_total (the transition end),
matching Numerics/OnionCoordinate.py's delta_s(N, N_init, ...), which
requires its own running N argument to *increase* away from N_init for
Delta_s(N) to grow from ln(1+alpha) (at N=N_init) to the O(10) values
reached by the transition end -- so every delta_s() call anywhere in this
module or in forward_rhs.py/response_rhs.py passes a literal 0.0 for that
N_init argument.

Trajectory lookups (InflatonTrajectory.phi_at/pi_at) use InflatonTrajectory's
own absolute N (0.0 at its own initial condition, increasing to N_end at the
end of inflation), which is a different coordinate from the local N above.
N_offset = trajectory.N_end - N_init converts between them, computed once
here from the compute target's raw parameters and threaded through to every
forward_rhs call as absolute_N = N_offset + local_N. response_rhs has no
trajectory dependency, so it needs no N_offset.

Response-sector lambda-scaling (prompt 23 Part B)
-------------------------------------------------------------------------
picard_inner's own backward pass solves for r_tilde = r/lam, NOT the
physical response state (terminal_response_state_rescaled, an O(1)-ish
terminal condition independent of the outer loop's actual lam), and the
loop-local rfield_tilde_grid/rmom_tilde_grid built from it are what feed
forward_rhs's own sourcing splines every sweep -- forward_rhs's own lam
parameter reconstructs the physical (D*lam)*r_tilde sourcing term at the
one place it is actually needed, never materializing lam*r_tilde as a bare
intermediate. picard_inner converts back to the PHYSICAL rfield_grid/
rmom_grid exactly once, at its own return statement (lam * rfield_tilde_grid),
so every caller of picard_inner -- and every consumer of solve_picard's own
returned "rfield_grid"/"rmom_grid" -- sees physical values, matching every
pre-prompt-23 caller's expectation exactly. The one exception is
solve_picard's own "response_dense_solution" (the raw OdeSolution of the
converged final sweep's backward pass): it is still r_tilde-valued, since
converting a continuous OdeSolution back to physical would require
re-wrapping it in a callable rather than a single array multiply -- see that
key's own comment in solve_picard's return dict.

lam=0.0 (the outer loop's own trivial starting point) degenerates correctly:
terminal_response_state_rescaled is lam-INDEPENDENT (still O(1)-ish, never
degenerate), so r_tilde solves the same well-posed backward pass regardless;
the final "* lam" reconstruction then correctly gives EXACTLY zero physical
response fields at lam=0, matching the pre-prompt-23 behaviour (and prompt
22's own Finding 1: lambda=0 is an exact fixed point of the unsourced
system) with no special-casing needed.

See response_rhs.py's and forward_rhs.py's own module docstrings for the
full derivation (response_rhs is exactly linear and homogeneous in the
response fields, so this rescaling is exact by linearity, not an
approximation) and the physics motivation (astronomic lam ~ 1e9-4e9 in the
resolved regime; carrying that dynamic range through the adaptive-step
backward integrator and the nonlinear Picard/shooting iteration is what
drives the H_sq_local<0/RK45 step-death failures prompt 22c's Finding 4
reported).

pi_core SAT target -- history and the prompt 22c fixed-target replacement
-------------------------------------------------------------------------
forward_rhs.py's core SAT penalty for pi needs a target g_pi(N) that is
*not* pi_core itself (see that module's docstring for why a self-referential
target would make the penalty a no-op). Since pi_core has no live formula to
compute it from (unlike phi_core's Neumann/regularity target, recomputed
live every RHS call from the OTHER, currently-integrated phi nodes), earlier
prompts (21a, 22b) made g_pi track a LAGGED, SELF-CONSISTENT estimate of
pi_core(N) itself, updated every Picard sweep from that sweep's own
just-computed pi_core trajectory:

  Prompt 21a: g_pi(N) <- (1-theta)*g_pi_prev(N) + theta*pi_core_new(N)
    (plain lagged replacement). Prompt 22's Finding 2 showed this DIVERGES
    once phi_end is corrected to a genuinely non-degenerate target (prompt
    22a): the sweep-to-sweep residual falls for ~15 sweeps then grows
    without bound, at every (n_collocation_points, delta_Nstar) tried, with
    no under-relaxation curing it in a practical sweep budget.

  Prompt 22b: replaced the update rule with Type-I Anderson acceleration
    (_AndersonMixer below), which cured the *divergence* but converges only
    to a genuine, not-fully-explained residual floor around 1e-4 to 1e-5
    (absolute, phi/pi units of order 1-10) -- confirmed not an accelerator
    artefact (scipy's own newton_krylov hits the same floor on the isolated
    sub-problem). This floor is comfortably above machine precision but
    below what a "the SAT forcing truly vanishes at the solution" claim
    needs, and it made the OUTER shooting loop on the prompt-22 "resolved
    regime" production case barely move over dozens of outer iterations
    even with the outer loop's own secant/backtracking/trust-region
    hardening (also prompt 22b) -- see
    .documents/gradient-coupled-instanton/
    22b-convergent-iteration-design-note.md's own "What is NOT yet
    demonstrated" section.

  Prompt 22c: a diagnostic fork (fixing g_pi at its sweep-0 seed for the
    WHOLE solve, no lagging at all -- prompt 22b's own theta=0 probe)
    showed this converges the SAME coupled map to MACHINE precision
    (~1e-13, one sweep) at every (n, delta_Nstar) point tried, while the
    lagged/Anderson target reproduces the ~1e-4 floor. A permanently frozen
    target was ruled out by prompt 22b's own broader stress test (a frozen,
    mismatched target biases the shooting problem enough that no lambda can
    drive the true phi_end residual below tolerance) -- but that failure
    mode only bites when the outer Newton loop drifts FAR from where the
    target was seeded. Prompt 22c removes the drift instead of chasing a
    convergent self-consistent update: the outer loop is now SEEDED at
    lambda_FI (FullInstanton's own converged terminal multiplier for the
    same BVP), so it starts and stays near the solution the fixed target
    was built from. The target is therefore

        g_pi_core(N) = FullInstanton's own pi_core(N) (phi2(N)), FIXED for
        the entire solve (never updated sweep-to-sweep or outer-iteration-
        to-outer-iteration).

    This trades a small, QUANTIFIED bias (the converged msr_action moves by
    an amount that vanishes as the fixed target's own mismatch with the
    true solution shrinks -- see tests/test_picard.py's fixed-target-bias
    regression) for machine-precision Picard convergence and a well-
    conditioned outer loop. The self-consistent/lagged/Anderson path
    (theta>0, anderson_m>0) is kept DORMANT for regression comparison only
    (DEFAULT_SAT_THETA=0.0, DEFAULT_ANDERSON_M=0 now reduce _AndersonMixer's
    update() to an exact no-op -- see _AndersonMixer's own docstring) -- it
    is not a recommended production setting and is not exercised by the
    default parameters of solve_picard.

g_phi (phi_core's target) is UNCHANGED by any of the above: it is computed
live, every RHS call, via neumann_boundary_value from the OTHER, currently-
integrated phi nodes -- never self-referential, never lagged, not a
contested closure at any point in this history.

Lambda-seed conversion and feasible-lambda corridor (prompt 24b)
-------------------------------------------------------------------------
Prompt 22c seeded the outer loop's bootstrap_target directly at
lambda_FI -- FullInstanton's own converged terminal multiplier. This is
WRONG SIGN and ~3 ORDERS OF MAGNITUDE TOO LARGE for GCI's own lambda:
FullInstanton's lambda is P1(N_total), the terminal condition of a
DIFFERENT boundary-value problem (see ComputeTargets/FullInstanton.py's
own bwd_rhs, ~line 150: "Backward pass: terminal conds
P1(N_total)=lambda, P2(N_total)=0"), whereas GCI's own terminal condition
(response_rhs.terminal_response_state) is

    rfield_core(N_total) = -lambda_GCI / (w_core * mu(N_total))

with w_core = grid.weights[-1] (the LGL boundary quadrature weight) and
mu(y,N) = exp(-1.5*Delta_s(N)*y) (Numerics/OnionCoordinate.measure).
Equating the physical terminal response (rfield <-> P1 -- both source the
SAME dphi/dN equation: forward_rhs.noise_source_terms's own
D_phi*rfield + ... term plays the role of FullInstanton's own
2*D11*P1 + ... term in fwd_rhs, confirmed directly from source, not
assumed) at gradient-enhancement factor E=1 (the core/homogeneous
baseline -- the true root's E, driven by the core fighting the drag of
outer shells pinned to the background, is O(10)-O(100) and NOT known a
priori, see the bracket-expansion below) gives

    lambda_seed = -lambda_FI * w_core * mu(N_total)

lambda_seed replaces the raw lambda_FI as bootstrap_target below.

Feasible-lambda corridor. The forward blow-up mode is H^2_local<0 (i.e.
epsilon>1), driven by the noise-sourcing feedback D11*lambda*r_tilde
(forward_rhs.noise_source_terms). The corridor derivation this module
docstring section had inherited (.prompts/gradient-coupled-instanton/
24b-lambda-conversion-seeding-and-trajectory-validation.md's own "Check")
asserted max|r_tilde| ~= 2.7/(w_core*mu(N_total)) -- VERIFIED AGAINST
SOURCE AND FOUND NOT TO HOLD: directly comparing to prompt 24a's own
Diagnostic-2 measurement (max|r_tilde|=9155.0 at m/Mp in
{1e-3,1e-4,1e-5}, delta_Nstar=1.0, n=5, alpha=0.1, w_core=0.1) against
1/(w_core*mu(N_total)) computed from the SAME config gives 8493.7 -- a
ratio of 1.08, not 2.7. The correct closed form is therefore

    max|r_tilde| ~= 1/(w_core * mu(N_total))     [kappa=1, not 2.7]

i.e. very close to the terminal boundary value of r_tilde itself (the
~8% excess is the modest additional growth the backward integration adds
on top of the terminal condition, at this delta_Nstar; not itself
resolved into a closed form here). This kappa=1 form independently
reproduces the module's own worked "Check" (lambda_c ~= 6.9 at
m/Mp=1e-2, delta_Nstar=1.0) to within 4%, using D11 evaluated at the
TRANSITION-START state (phi_init, pi_init -- NOT the core's own N_total
endpoint, which gives a visibly worse match): the check's own H^2~=1.24e-3
matches H_sq_nl_init, not H_sq_core(N_total). Hence

    D11, _, _ = diffusion_model.D_matrix(phi_init, pi_init, potential)
    lambda_c_positive = w_core * mu(N_total) / D11

The negative side is confirmed WIDER (prompt 24a Diagnostics 1 & 4: the
sign of the noise kick decides whether it drives epsilon toward 1 or away
from it) -- CORRIDOR_NEGATIVE_WIDENING=2.5 below is chosen to sit inside
every bound implied by the four cross-checked data points available
(m/Mp=1e-2: delta_Nstar in {0.3,0.5,0.7} converged at
lambda/lambda_c_positive = 0.70, 1.01, 1.38 respectively -- i.e. NOT
symmetric-corridor-feasible past delta_Nstar=0.5 without widening at all;
delta_Nstar=1.0's own Diagnostic-1 boundary, lambda=-15.6 converges /
lambda=-37.5 diverges, requires the widening factor to lie in
[2.16, 5.19]). 2.5 is not a fit to any single point -- it is the
documented, defensible middle of the prompt's own "~2-3x" language,
verified (not merely asserted) to satisfy every constraint above.

lambda_c_positive/lambda_c_negative bound solve_shooting's own lam_bounds
(Numerics/ShootingSolver.py, prompt 24b) -- every step the outer loop
proposes (bootstrap, stall escalation, trust-region-clipped secant, and
every backtracking probe derived from any of those) is clamped into this
corridor BEFORE evaluate() is ever called on it, so a "propose, blow up,
backtrack" cascade cannot occur; the shooting solver only ever proposes
points inside the feasible set.

Bracket expansion from the seed (prompt 24b). Since E is O(10)-O(100) and
not known a priori, the true root is typically NOT at lambda_seed (E=1)
itself -- it is found by a geometric expansion FROM lambda_seed (same
sign, corridor-clamped), evaluating each successive point through
solve_picard's own evaluate()/commit() closures (so every expansion probe
also warm-starts the next Picard inner solve, exactly like solve_shooting's
own per-outer-iteration commit), until the residual's sign flips relative
to the previous point -- a genuine bracket -- or the corridor edge is
reached. The bracket's two endpoints are handed to solve_shooting as
(lam0, bootstrap_target): lam0 is the last point evaluated (already
known-feasible, unlike the pre-24b lam0=0.0 trivial-point convention),
bootstrap_target is the point on the far side of the sign flip, so
solve_shooting's own existing bootstrap-step logic (Numerics/
ShootingSolver.py) aims its very first outer-loop step directly at the
already-bracketed root instead of restarting a fresh escalation from
lambda=0. See _bracket_from_seed's own docstring below for the exact
algorithm and the graceful fallback (ordinary escalation from
lambda_seed, no bootstrap_target) when no bracket is found before the
corridor edge.

E = lambda_root / lambda_seed is logged in solve_picard's own returned
"diagnostics" dict ("gradient_enhancement_E") on every converged solve --
a physically interesting quantity (how much extra terminal response the
core needs beyond the homogeneous baseline to fight the drag of the outer
shells) and a cheap regression signal (prompt 22a/22c/23's own precedent
of quantifying, not just fixing, whatever bias/rescaling a given prompt
introduces).

FullInstanton seed (prompt 21a; extended prompt 22c)
-------------------------------------------------------------------------
_fetch_full_instanton_profile implements a three-tier fetch-then-fallback
(unchanged preference order from prompt 21a's _seed_pi_core_values, which it
replaces): (1) a pre-fetched full_instanton_seed dict, if supplied and not
itself a failure -- datastore access only happens on the driver, never
inside a @ray.remote worker (.claude/rules/ray-dispatch.md), so
GradientCoupledInstanton.py's own remote function fetches one (if available)
and passes the resulting dict in here; (2) otherwise, an inline
_compute_full_instanton._function call (bypassing Ray, the same "call the
delegate directly" pattern used throughout this test suite); (3) if that
ALSO fails, the noiseless background trajectory's own (phi, pi)(N) with
lambda_FI=0.0 -- always available, no extra ODE solve. Prompt 22c widened
what this profile is used for: not just g_pi_core's fixed target (phi2), but
also the outer loop's own seed lambda (lambda_FI) and the sweep-0
onion-interpolated forward-field guess (phi1 as the "core" endmember, see
below). Tier 3 degrades gracefully on all three: lambda_FI=0.0 and
core(N)=exterior(N) collapse the seed to exactly the pre-22c un-seeded
starting point (uniform background at every y, lambda starting at 0) --
seed QUALITY only affects how quickly (or, in the pathological case where
FullInstanton itself is entirely unobtainable, whether) the solve converges,
via how close the seed is to the true solution; it is the FIXED TARGET
(same profile, different role) whose quality can also introduce the small
bias quantified above.

Sweep-0 forward-field seed -- the onion interpolation (prompt 22c)
-------------------------------------------------------------------------
Before this prompt, the initial guess handed to the first picard_inner call
was a genuine ODE solve (the "zeroth Picard iterate"): integrate the
uniform-in-y initial condition forward under zero response-field sourcing.
This produces a nearly-uniform-in-y profile -- a poor starting guess for a
genuinely resolved (non-flat, lambda far from 0) solution, and wasted an
extra ODE solve every call. Prompt 22c replaces it with a pure array
construction (no ODE solve): a linear interpolation in the onion coordinate
y between the "core" endmember (FullInstanton's own converged core
trajectory, evaluated at y=+1) and the "exterior" endmember (the noiseless
background trajectory, evaluated at y=-1):

    field(y, N) = ((1+y)/2) * core(N) + ((1-y)/2) * exterior(N)

Linear is the primary/default shape (DEFAULT_SEED_PROFILE), motivated by the
gradient-free zeta(r) being ~linear in log(r) hence phi(y) ~linear in y in
slow roll (onion_model.tex). seed_profile is a single, documented knob
(_seed_profile_weights) so a more core-concentrated alternative
("exponential") can be tried if linear is ever found not to converge on a
far-from-slow-roll case -- untried in production as of prompt 22c.

Response fields (rfield, rmom) are deliberately NOT interpolated: their
terminal boundary condition (rfield=0 at N=N_total on every non-core shell)
is enforced by the backward integration itself, so a consistent response
seed falls out for free as the natural first half-step of Picard -- the
existing picard_inner loop's OWN first action, every sweep, is a backward
pass built from whatever (phi, pi) grid it was handed. Seeding phi_grid_in/
pi_grid_in with the onion interpolation above (and lambda with lambda_FI) is
therefore sufficient on its own; no separate "run one backward pass" step is
needed in solve_picard's own body (see solve_picard's docstring for where
the seeded grid is threaded in as the very first picard_inner call's input).

The per-sweep linear stability of the assembled operator is unaffected by
any of the above: the "-tau*g" part of the SAT is a constant additive
forcing term, not part of the Jacobian an eigenvalue analysis probes, so
changing how (or whether) g_pi is updated changes only the fixed point the
iteration converges to (or whether/how fast it converges), never the
per-sweep operator's own spectrum.
"""

import math
import time
from contextlib import contextmanager
from typing import Optional

import numpy as np
import scipy.integrate._ivp.rk as _scipy_rk
from scipy.integrate import solve_ivp

from Interpolation.spline_wrapper import SplineWrapper
from Numerics.OnionCoordinate import delta_s, measure
from Numerics.ShootingSolver import solve_shooting
from ComputeTargets.FullInstanton import _compute_full_instanton
from ComputeTargets.GradientCoupledInstanton.forward_rhs import (
    pack_state,
    unpack_state,
    forward_rhs,
)
from ComputeTargets.GradientCoupledInstanton.response_rhs import (
    unpack_response_state,
    response_rhs,
    terminal_response_state_rescaled,
)

MAX_OUTER = 50
MAX_INNER = 30

# Floor applied to OUTER_TOL = max(atol*1e6, OUTER_TOL_FLOOR) below (prompt
# 24b: extracted into a module constant so it can be monkeypatched by a
# diagnostic harness -- see that computation's own comment).
OUTER_TOL_FLOOR = 1.0e-2

# Number of consecutive inner sweeps required below INNER_TOL before
# picard_inner declares convergence (prompt 22b -- see picard_inner's own
# comment at the sustained-convergence check). 1 reduces to a single-dip
# check; kept > 1 as a guard against the still-available (dormant)
# self-consistent/Anderson path's noisy convergence, even though the
# default fixed target (prompt 22c) converges monotonically and would pass
# a single-dip check trivially.
INNER_CONSECUTIVE_REQUIRED = 3

# Divergence early-exit for picard_inner (prompt 22c -- see the sweep
# loop's own comment at the check). A probe at a poorly-chosen lambda whose
# residual grows for this many consecutive sweeps, once past
# DIVERGENCE_RESIDUAL_FLOOR, is abandoned rather than run to MAX_INNER.
DIVERGENCE_GROWTH_PATIENCE = 3
DIVERGENCE_RESIDUAL_FLOOR = 1.0e-2

# Number of temporal sample points spanning the local domain [0.0, N_total];
# matches FullInstanton's own floor value (N_GRID = max(300, ...)).
N_GRID_SIZE = 300

# Mixing/damping factor for the (now-dormant, prompt 22c) self-consistent
# pi_core SAT target update -- Walker-Ni's "beta" when anderson_m>0, the old
# plain lagged-replacement blend's theta when anderson_m=0. DEFAULT 0.0
# together with DEFAULT_ANDERSON_M=0 makes _AndersonMixer.update() an exact
# no-op (returns its input unchanged, see _AndersonMixer's own docstring),
# i.e. the production default is now a FIXED (never-updated) target -- see
# the module docstring's "pi_core SAT target" section. theta=1.0,
# anderson_m=5 (prompt 22b's own production values) remain reachable for
# regression comparison against the abandoned self-consistent path, not
# recommended for production use.
DEFAULT_SAT_THETA = 0.0

# Anderson acceleration window (prompt 22b; dormant as of prompt 22c -- see
# DEFAULT_SAT_THETA's own comment). 0 disables acceleration AND, combined
# with theta=0.0, freezes the target outright.
DEFAULT_ANDERSON_M = 0

# Sweep-0 onion-interpolation shape between the FullInstanton "core"
# endmember and the noiseless-background "exterior" endmember (prompt 22c
# -- see the module docstring's own "Sweep-0 forward-field seed" section
# and _seed_profile_weights below). "linear" is the only shape validated in
# production; "exponential" is available as an untried, more
# core-concentrated fallback.
DEFAULT_SEED_PROFILE = "linear"

# Concentration rate for seed_profile="exponential" (module constant, not a
# solve_picard parameter -- this shape is an untried contingency, not a
# tuned production knob; see _seed_profile_weights).
SEED_EXPONENTIAL_RATE = 3.0

# ---------------------------------------------------------------------------
# Prompt 24 prerequisite -- wall-clock safeguard + non-convergence
# classification. Companion timing analysis (24 Phase 0) found the
# disqualifying gap: MAX_OUTER/MAX_INNER bound iteration COUNTS, but nothing
# bounded wall-clock, so a single RK45 backward pass could step-halve
# indefinitely in exactly the small-m/large-delta_Nstar corner this campaign
# explores. Three layered defences, all optional (None/default preserves
# every pre-existing caller's unbounded behaviour exactly):
#   1. wallclock_budget_seconds (solve_picard param): a global deadline
#      checked (a) inside every forward/backward RHS call -- the finest
#      granularity, catching runaway step-halving on the very next RHS
#      evaluation rather than waiting for a whole solve_ivp call to return;
#      (b) at the top of picard_inner's own sweep loop; (c) inside
#      Numerics/ShootingSolver.solve_shooting's own outer loop (deadline
#      param there). A deadline hit is a GRACEFUL bail: whatever grid the
#      last completed sweep/outer-iteration produced is kept and returned
#      exactly as if MAX_INNER/MAX_OUTER had been exhausted instead --
#      never a hard crash, never a partially-overwritten grid.
#   2. max_step (solve_picard param, default DEFAULT_MAX_STEP_FRACTION *
#      N_total): bounds solve_ivp's own maximum accepted step, so a single
#      step attempt cannot itself take an unbounded stride into a poorly-
#      resolved region before the deadline check on the NEXT RHS call gets
#      a chance to fire.
#   3. A Ray task-level hard timeout (outer safety net, defence-in-depth
#      beyond 1-2 for the case the in-process deadline somehow fails to
#      fire): NOT implemented here -- ShootingSolver.py/picard.py have no
#      access to the Ray dispatch layer, and RayTools/RayWorkPool.py (which
#      main.py's own gradient branch dispatches through) is protected
#      infrastructure (CLAUDE.md) not to be modified without explicit
#      instruction, and exposes no per-task timeout/cancel hook to layer
#      this on top of. A driver that bypasses RayWorkPool and calls
#      GradientCoupledInstanton.compute() ObjectRefs directly could add this
#      via ray.wait(refs, timeout=...) + ray.cancel(ref, force=True) on
#      whatever is still pending past budget + margin; the prompt-24
#      campaign runs through the real main.py/RayWorkPool pipeline instead
#      (per the prompt's own instruction), so relies on layers 1-2 alone --
#      see .documents/gradient-coupled-instanton/
#      24-prerequisite-wallclock-safeguard.md for the full writeup of this
#      trade-off.
# Every non-convergent bail (timeout, MAX_OUTER exhaustion, H_sq<0/
# step-death) is tagged via _classify_bailout below, folded into the
# returned "diagnostics" dict as "bailout_tag"/"bailout_reason" -- this is
# what makes a timeout a DATA POINT (convergent-but-slow vs structural)
# rather than a hole in the record.
# ---------------------------------------------------------------------------

DEFAULT_MAX_STEP_FRACTION = 1.0 / 50.0

# Window (number of trailing outer-loop residual evaluations) and relative
# threshold used by _classify_bailout's residual-trend heuristic below.
RESIDUAL_TREND_WINDOW = 5
RESIDUAL_TREND_RELATIVE_THRESHOLD = 0.05

# ---------------------------------------------------------------------------
# Prompt 24b -- lambda-seed conversion + feasible-lambda corridor. See the
# module docstring's own "Lambda-seed conversion and feasible-lambda
# corridor" section for the full derivation and verification against prompt
# 24a's own Diagnostic-2/4 data.
# ---------------------------------------------------------------------------

# Widening factor applied to the corridor's NEGATIVE edge only (the positive
# edge uses kappa=1 unwidened) -- see the module docstring's own derivation;
# verified to sit inside every bound implied by the four cross-checked
# m/Mp=1e-2 data points available (delta_Nstar in {0.3,0.5,0.7}'s own
# converged lambda/lambda_c_positive ratios, and delta_Nstar=1.0's own
# Diagnostic-1 converges/diverges boundary), not fitted to any single one.
CORRIDOR_NEGATIVE_WIDENING = 2.5

# Geometric growth factor and step cap for _bracket_from_seed's own
# expansion away from lambda_seed (E=1) toward the true root (E typically
# O(10)-O(100), not known a priori -- see the module docstring). 3.0 reaches
# a factor of ~590 in 6 steps, comfortably covering the documented E range
# without excessive probing; corridor-clamped regardless (see
# _bracket_from_seed), so an overly aggressive growth factor cannot itself
# cause an infeasible evaluation.
BRACKET_GROWTH_FACTOR = 3.0
BRACKET_MAX_STEPS = 8


class _WallclockBudgetExceeded(Exception):
    """Raised from inside a forward/backward RHS call once
    wallclock_budget_seconds has elapsed (see the module-level comment
    above). Caught immediately around the enclosing solve_ivp call in
    picard_inner -- never propagates out of solve_picard itself."""
    pass


def _classify_bailout(
    converged: bool,
    ode_failure_at_bail: bool,
    residual_history: list,
) -> str:
    """
    Tags a solve_picard outcome as one of: "converged", "blown-up",
    "diverging", "floored", "descending" -- see the module-level comment
    above and .prompts/gradient-coupled-instanton/24-revised-deep-dive-
    then-map.md's own definitions.

    converged: the outer shooting loop reached tol.
    ode_failure_at_bail: the LAST outer-loop evaluation failed outright
        (H_sq_local<0, RK45 step-death, or the divergence early-exit) rather
        than the loop simply running out of outer iterations or wall-clock
        with its most recent evaluation still succeeding -- always
        "blown-up" (structural), regardless of any earlier trend.
    residual_history: abs(residual) at every SUCCESSFUL outer-loop
        evaluation, in call order (solve_picard's own "evaluate" closure
        appends to this).
    """
    if converged:
        return "converged"
    if ode_failure_at_bail:
        return "blown-up"
    if len(residual_history) < 2:
        # No trend data (bailed before or at the second successful
        # evaluation) -- cannot distinguish descending/floored/diverging;
        # treat conservatively as structural rather than guessing.
        return "blown-up"
    window = residual_history[-min(RESIDUAL_TREND_WINDOW, len(residual_history)):]
    baseline = max(abs(window[0]), 1.0e-300)
    rel_change = (window[-1] - window[0]) / baseline
    if rel_change > RESIDUAL_TREND_RELATIVE_THRESHOLD:
        return "diverging"
    if rel_change < -RESIDUAL_TREND_RELATIVE_THRESHOLD:
        return "descending"
    return "floored"


class _AndersonMixer:
    """
    Type-I Anderson acceleration (Walker & Ni, SIAM J. Numer. Anal. 2011)
    for the (now-DORMANT, prompt 22c) self-consistent pi_core SAT target
    update -- see picard.py's own module docstring for the full history
    (prompt 21a's plain lagged replacement, prompt 22's Finding 2
    divergence, prompt 22b's Anderson fix and its own residual floor, and
    prompt 22c's replacement of the whole self-consistent scheme with a
    FIXED FullInstanton-derived target). Retained ONLY so the abandoned
    path remains reachable for regression comparison
    (tests/test_picard.py's own Anderson-mixer unit tests); production code
    calls this with window=DEFAULT_ANDERSON_M=0 and theta=DEFAULT_SAT_THETA
    =0.0, which makes update() an exact identity (see below) -- i.e. the
    production default is a genuinely fixed target, not "Anderson with
    trivial settings".

    The map being accelerated is x -> T(x), where T(x) is "the pi_core(N)
    trajectory produced by one Picard sweep run with SAT target x" --
    already computed as an ordinary side effect of picard_inner's existing
    backward+forward solve, so this class only changes how the NEXT target
    is built from the accumulated history of (x, g) pairs, where
    g = T(x) - x is the fixed-point residual. It does not add any new ODE
    solves, derivatives, or Jacobian.

    window (m): number of past (x, g) pairs retained, beyond the current
    one -- i.e. the least-squares problem uses at most m past differences.
    m=0 makes every update() call return exactly x_k + theta*g_k -- with
    theta=0.0 (DEFAULT_SAT_THETA, prompt 22c) this is x_k unchanged: a
    permanently fixed target. m=0, theta=1.0 reproduces the old plain
    Picard/theta-blend rule (prompt 21a's original scheme).

    theta (Walker-Ni's "beta"): mixing/damping factor applied to the
    residual and to the correction's ΔG contribution; theta=1 is undamped
    Anderson/plain-replacement, matching the module docstring's x_{k+1}
    formula exactly. NOTE: theta=0 alone does NOT freeze the target unless
    window is ALSO 0 -- with window>0 the least-squares correction term
    `(dX + theta*dG) @ gamma` survives even at theta=0 (gamma is fit to
    reduce g_k, not guaranteed zero). Both DEFAULT_SAT_THETA=0.0 AND
    DEFAULT_ANDERSON_M=0 are required together for the fixed-target
    default; this is why both defaults changed together in prompt 22c.

    Tikhonov regularization: plain (unregularized) least-squares Anderson
    was found empirically (prompt 22b acceptance testing) to STALL on this
    nonlinear map -- it knocks the residual down by ~2 orders of magnitude
    within a handful of sweeps, then oscillates indefinitely around that
    level instead of continuing to decrease. The mechanism is the classic
    Anderson failure mode on a genuinely nonlinear (non-affine) map: once
    ||g_k|| stops shrinking, ΔG's columns are all similarly-scaled "noise"
    directions rather than a well-separated basis, and the *exact*
    least-squares fit (which reproduces g_k precisely on that noisy basis)
    injects exactly that noise into the next iterate. A hard restart
    (dropping the window and falling back to an undamped plain-Picard step)
    was tried and made this WORSE, not better -- it reintroduces prompt 22
    Finding 2's own theta=1 instability on every reset. The fix that
    actually works is standard Tikhonov regularization of the small
    least-squares solve (a much gentler intervention, still smoothly
    blending in the full Anderson step when ΔG is well-conditioned):

        gamma = (ΔG^T ΔG + REG_EPS * ||ΔG||_F^2 * I)^{-1} ΔG^T g_k

    REG_EPS is a small, fixed relative regularization strength -- large
    enough to damp the noise-fitting behaviour, small enough that the
    Anderson correction still dominates the plain-Picard fallback whenever
    ΔG is genuinely well-conditioned (early sweeps, still-shrinking
    residual). This mechanism is retained purely for regression fidelity to
    prompt 22b's own dormant path; it plays no role in the prompt 22c fixed-
    target default.
    """

    REG_EPS = 1.0e-2

    def __init__(self, window: int, theta: float):
        self._m = max(0, int(window))
        self._theta = theta
        self._X: list = []
        self._G: list = []

    def update(self, x_k: np.ndarray, g_k: np.ndarray) -> np.ndarray:
        if self._m == 0:
            return x_k + self._theta * g_k

        self._X.append(x_k)
        self._G.append(g_k)
        if len(self._X) > self._m + 1:
            self._X.pop(0)
            self._G.pop(0)

        m_k = len(self._X) - 1
        if m_k == 0:
            return x_k + self._theta * g_k

        dX = np.stack([self._X[i + 1] - self._X[i] for i in range(m_k)], axis=1)
        dG = np.stack([self._G[i + 1] - self._G[i] for i in range(m_k)], axis=1)

        gram = dG.T @ dG
        reg = self.REG_EPS * float(np.linalg.norm(dG, ord='fro') ** 2)
        gamma = np.linalg.solve(gram + reg * np.eye(m_k), dG.T @ g_k)
        return x_k + self._theta * g_k - (dX + self._theta * dG) @ gamma


# ---------------------------------------------------------------------------
# Prompt 17 Part B -- per-solve RK45 instrumentation. Pure measurement: none
# of this changes solve_ivp's method, tolerances, grid, or output values.
# ---------------------------------------------------------------------------


@contextmanager
def _count_rk45_step_attempts():
    """
    Counts every call to scipy's module-level ``rk_step`` helper -- one call
    per *attempted* RK45 step, whether that step is ultimately accepted or
    rejected (see ``scipy.integrate._ivp.rk.RungeKutta._step_impl``, whose
    inner ``while not step_accepted:`` retry loop calls ``rk_step`` exactly
    once per trial). ``RungeKutta._step_impl`` looks up the name
    ``rk_step`` in its own module's globals at call time, so temporarily
    replacing ``scipy.integrate._ivp.rk.rk_step`` redirects those calls
    without touching ``RK45`` itself.

    This is a pure observability hook: the wrapped function is a thin
    pass-through to the original ``rk_step``, so step selection, accepted
    step sizes, and every numerical output are completely unaffected --
    only a call counter increments. Restored in a ``finally`` block so a
    solver exception never leaves the patch in place.

    Combined with ``len(sol.sol.interpolants)`` (the number of *accepted*
    steps, available whenever ``dense_output=True``), this gives an exact
    rejected = total - accepted count without needing to duplicate any of
    RK45's own step-acceptance logic.
    """
    counter = {"attempts": 0}
    original = _scipy_rk.rk_step

    def _wrapped(*args, **kwargs):
        counter["attempts"] += 1
        return original(*args, **kwargs)

    _scipy_rk.rk_step = _wrapped
    try:
        yield counter
    finally:
        _scipy_rk.rk_step = original


def _solve_ivp_instrumented(instrument: bool, *args, **kwargs):
    """
    Thin wrapper around ``solve_ivp``. If ``instrument`` is False, calls
    ``solve_ivp`` completely unchanged and returns ``(sol, None)`` -- no
    monkeypatching, no extra work, so the non-instrumented path costs
    nothing beyond whatever ``dense_output``/``t_eval`` the caller already
    requested.

    If ``instrument`` is True, wraps the call with
    ``_count_rk45_step_attempts`` and returns ``(sol, step_stats)``, where
    ``step_stats`` is a dict with keys ``accepted``, ``rejected``, ``total``,
    ``step_sizes`` (list of accepted step sizes, ``abs(t_max - t_min)`` per
    dense-output interpolant). The caller must pass ``dense_output=True``
    for ``accepted``/``step_sizes`` to be populated; without it ``sol.sol``
    is ``None`` and this falls back to ``accepted=0``, ``step_sizes=[]``
    (every current call site in ``solve_picard`` passes ``dense_output=True``
    whenever it instruments, so this fallback is not expected to trigger in
    production use).
    """
    if not instrument:
        return solve_ivp(*args, **kwargs), None

    with _count_rk45_step_attempts() as counter:
        sol = solve_ivp(*args, **kwargs)

    interpolants = sol.sol.interpolants if sol.sol is not None else []
    accepted = len(interpolants)
    total = counter["attempts"]
    rejected = total - accepted
    step_sizes = [abs(ip.t - ip.t_old) for ip in interpolants]

    return sol, {
        "accepted": accepted,
        "rejected": rejected,
        "total": total,
        "step_sizes": step_sizes,
    }


def _aggregate_rk45_stats(stats_list: list, label: str, N_total: float) -> dict:
    """
    Aggregates a list of per-solve step-stats dicts (as produced by
    ``_solve_ivp_instrumented``) across every forward- or backward-direction
    ``solve_ivp`` call made during one whole ``solve_picard`` invocation --
    every inner-Picard forward/backward solve across every outer shooting
    evaluation -- into the six columns the diagnostics dict exposes for that
    direction: ``rk45_{label}_total_steps``, ``_accepted_steps``,
    ``_rejected_steps``, ``_min_step``, ``_max_step``, ``_steps_per_efold``
    (total steps / N_total).

    Returns a dict of all-``None`` values if ``stats_list`` is empty (e.g.
    ``instrument_stiffness=False``, or a direction that made no solve_ivp
    calls before an early failure).
    """
    keys = (
        f"rk45_{label}_total_steps", f"rk45_{label}_accepted_steps",
        f"rk45_{label}_rejected_steps", f"rk45_{label}_min_step",
        f"rk45_{label}_max_step", f"rk45_{label}_steps_per_efold",
    )
    if not stats_list:
        return {k: None for k in keys}

    total_steps = sum(s["total"] for s in stats_list)
    accepted_steps = sum(s["accepted"] for s in stats_list)
    rejected_steps = sum(s["rejected"] for s in stats_list)
    all_step_sizes = [sz for s in stats_list for sz in s["step_sizes"]]

    return {
        f"rk45_{label}_total_steps": total_steps,
        f"rk45_{label}_accepted_steps": accepted_steps,
        f"rk45_{label}_rejected_steps": rejected_steps,
        f"rk45_{label}_min_step": min(all_step_sizes) if all_step_sizes else None,
        f"rk45_{label}_max_step": max(all_step_sizes) if all_step_sizes else None,
        f"rk45_{label}_steps_per_efold": (total_steps / N_total) if N_total else None,
    }


def _build_node_splines(N_grid: np.ndarray, values_grid: np.ndarray, y_transform: str) -> list:
    """One SplineWrapper per grid node (columns of values_grid), each built
    over the shared N_grid. values_grid has shape (len(N_grid), n_nodes)."""
    n_nodes = values_grid.shape[1]
    return [
        SplineWrapper(N_grid, values_grid[:, j], y_transform=y_transform, k=3)
        for j in range(n_nodes)
    ]


class _FullInstantonSeedPotentialHolder:
    """Duck-typed stand-in for InflatonTrajectory, exposing only the
    ._potential attribute _compute_full_instanton actually reads -- the same
    minimal stub used by tests/test_picard.py and
    scripts/compare_gradient_full.py for the same "bypass Ray, call the
    delegate directly" pattern."""

    def __init__(self, potential):
        self._potential = potential


class _FullInstantonSeedProxyStub:
    """Duck-typed stand-in for InflatonTrajectoryProxy: _compute_full_instanton
    only ever calls trajectory.get()._potential. Used only for the
    FullInstanton seed's fallback delegate call below -- solve_picard itself
    already has `potential` directly, with no proxy of its own to reuse (its
    own `trajectory` parameter is the materialised InflatonTrajectory, not a
    proxy)."""

    def __init__(self, potential):
        self._holder = _FullInstantonSeedPotentialHolder(potential)

    def get(self):
        return self._holder


def _fetch_full_instanton_profile(
    N_grid: np.ndarray,
    N_offset: float,
    phi_init: float,
    pi_init: float,
    phi_end: float,
    N_total: float,
    trajectory,
    potential,
    diffusion_model,
    atol: float,
    rtol: float,
    label: str,
    full_instanton_seed: Optional[dict],
) -> dict:
    """
    Fetches the FullInstanton profile used, as of prompt 22c, for THREE
    purposes: (1) the fixed pi_core SAT target (phi2), (2) the "core"
    endmember of the sweep-0 onion-interpolated forward-field seed (phi1),
    and (3) the outer shooting loop's own seed lambda (lambda_FI). Replaces
    prompt 21a's _seed_pi_core_values, which only ever needed (1) -- see
    picard.py's own module docstring for the full history.

    Preference order (unchanged from _seed_pi_core_values):
      1. full_instanton_seed, if supplied and not itself a failure -- a
         pre-computed dict shaped like _compute_full_instanton's own return
         value (plus a top-level "final_lambda", which
         GradientCoupledInstanton.py's own remote function copies out of the
         fetched FullInstanton's diagnostics -- see that module's Step 3b).
         This is the "prefer fetching the already-computed FullInstanton
         result from the datastore" path: datastore access only happens on
         the driver (never inside a @ray.remote worker, see
         .claude/rules/ray-dispatch.md), so GradientCoupledInstanton.py's own
         Ray remote function is responsible for fetching one (if available)
         and passing the resulting dict in here -- solve_picard itself never
         touches the datastore.
      2. Otherwise, compute one inline via _compute_full_instanton._function
         -- bypassing Ray, the same "call the underlying function directly"
         pattern already used throughout this test suite
         (tests/test_picard.py) and scripts/compare_gradient_full.py. This is
         a well-tested, standalone delegate call, not a reimplementation of
         FullInstanton's own physics.
      3. If that ALSO fails to converge (e.g. a pathological corner of
         parameter space), fall back to lambda_FI=0.0 and the noiseless
         background trajectory's own (phi, pi)(N) for BOTH phi1 and phi2 --
         always available, no extra ODE solve. This degenerates the whole
         seed (target, core endmember, outer-loop lambda) to exactly the
         pre-22c un-seeded starting point.

    Returns {"phi1": array on N_grid, "phi2": array on N_grid,
    "lambda_FI": float}.
    """

    def _interp(data: dict, key: str) -> Optional[np.ndarray]:
        seed_N = np.asarray(data["N_sample"], dtype=float)
        seed_vals = np.asarray(data[key], dtype=float)
        if len(seed_N) < 4:
            return None
        spline = SplineWrapper(seed_N, seed_vals, y_transform='linear', k=3)
        return np.asarray(spline(N_grid), dtype=float)

    def _try(data: Optional[dict]) -> Optional[dict]:
        if data is None or data.get("failure", True):
            return None
        phi1 = _interp(data, "phi1")
        phi2 = _interp(data, "phi2")
        if phi1 is None or phi2 is None:
            return None
        lambda_FI = data.get("final_lambda")
        if lambda_FI is None:
            lambda_FI = (data.get("diagnostics") or {}).get("final_lambda")
        return {
            "phi1": phi1, "phi2": phi2,
            "lambda_FI": float(lambda_FI) if lambda_FI is not None else 0.0,
        }

    result = _try(full_instanton_seed)
    if result is not None:
        return result

    fi_data = _compute_full_instanton._function(
        trajectory=_FullInstantonSeedProxyStub(potential),
        dm=diffusion_model,
        phi_init=phi_init,
        pi_init=pi_init,
        phi_final=phi_end,
        N_total=N_total,
        N_sample=N_grid.tolist(),
        atol=atol,
        rtol=rtol,
        label=f"[{label}] FullInstanton seed (prompt 22c)",
    )
    result = _try(fi_data)
    if result is not None:
        return result

    print(
        f"[{label}] FullInstanton seed: unavailable, and the inline delegate "
        f"also failed to converge; falling back to lambda_FI=0.0 and the "
        f"noiseless background trajectory's own (phi,pi)(N) for both the "
        f"fixed pi_core target and the onion-interpolation core endmember. "
        f"This degenerates to the pre-prompt-22c un-seeded starting point "
        f"and may converge more slowly (or, if the true solution is far "
        f"from background, fail to converge at all) -- see picard.py's own "
        f"module docstring."
    )
    ext_phi = np.array([trajectory.phi_at(N_offset + N) for N in N_grid])
    ext_pi = np.array([trajectory.pi_at(N_offset + N) for N in N_grid])
    return {"phi1": ext_phi, "phi2": ext_pi, "lambda_FI": 0.0}


def _seed_profile_weights(y: np.ndarray, seed_profile: str):
    """
    Core/exterior interpolation weights for the sweep-0 onion seed (prompt
    22c -- see the module docstring's own "Sweep-0 forward-field seed"
    section): field(y, N) = w_core(y)*core(N) + w_ext(y)*exterior(N), with
    w_core(-1)=0 (pure exterior/background at the outer edge, y=-1) and
    w_core(+1)=1 (pure FullInstanton core at the core node, y=+1).

    "linear" (DEFAULT_SEED_PROFILE) is the validated production shape.
    "exponential" is a more core-concentrated alternative -- untried in
    production as of prompt 22c, kept available only as a documented,
    single knob in case "linear" is ever found not to converge on a
    far-from-slow-roll case (per the prompt's own contingency).
    """
    if seed_profile == "linear":
        w_core = (1.0 + y) / 2.0
    elif seed_profile == "exponential":
        w_core = np.expm1(SEED_EXPONENTIAL_RATE * (1.0 + y) / 2.0) / np.expm1(SEED_EXPONENTIAL_RATE)
    else:
        raise ValueError(
            f"solve_picard: unknown seed_profile {seed_profile!r} "
            f"(expected 'linear' or 'exponential')"
        )
    return w_core, 1.0 - w_core


def _bracket_from_seed(
    evaluate,
    commit,
    lambda_seed: float,
    lam_lo: float,
    lam_hi: float,
    growth: float = BRACKET_GROWTH_FACTOR,
    max_steps: int = BRACKET_MAX_STEPS,
):
    """
    Geometric expansion from lambda_seed (prompt 24b's own E=1 baseline)
    toward the true root, whose gradient-enhancement factor E is O(10)-O(100)
    but not known a priori (see the module docstring's own "Lambda-seed
    conversion and feasible-lambda corridor" section) -- stops the moment two
    successively evaluated residuals have opposite sign (a genuine bracket)
    or the corridor edge [lam_lo, lam_hi] is reached first.

    Every probe goes through the CALLER's own evaluate()/commit() closures
    (solve_picard's own, exactly as the outer shooting loop uses them), so
    each expansion step also warm-starts the next Picard inner solve from
    the previous expansion point's converged grid -- identical to how
    solve_shooting itself commits every evaluated point, accepted or not.

    Returns (lam0, bootstrap_target):
      - A genuine bracket found: lam0 is the LAST point evaluated (already
        known-feasible), bootstrap_target is the point on the other side of
        the sign flip -- handed to solve_shooting so its own first-step
        bootstrap logic (Numerics/ShootingSolver.py) aims directly at the
        already-bracketed root.
      - No bracket found before the corridor edge (or lambda_seed itself is
        infeasible, e.g. an unavailable/degenerate FullInstanton seed
        collapsing lambda_seed to 0.0): falls back to lam0=lambda_seed (or
        0.0 if even that failed), bootstrap_target=None -- solve_shooting's
        own ordinary stall-escalation resumes from there, still corridor-
        clamped via lam_bounds.
    """
    lam_prev = lambda_seed
    res_prev, ok, aux = evaluate(lam_prev)
    if not ok:
        # lambda_seed itself was infeasible (e.g. an unavailable/degenerate
        # FullInstanton seed) -- fall back to the always-feasible trivial
        # point as lam0, but still hand lambda_seed through as
        # bootstrap_target (rather than None/undirected) so solve_shooting's
        # own Armijo backtracking gets a directed first step to shrink from,
        # exactly like the pre-24b "let a bad guess safely backtrack"
        # contract for bootstrap_target.
        return 0.0, lambda_seed
    commit(aux)
    sign_prev = math.copysign(1.0, res_prev) if res_prev != 0.0 else 0.0

    for _ in range(max_steps):
        lam_next = max(lam_lo, min(lam_hi, lam_prev * growth))
        if lam_next == lam_prev:
            break  # corridor edge reached -- cannot expand further
        res_next, ok, aux = evaluate(lam_next)
        if not ok:
            break  # infeasible past this point -- hand off what we have
        commit(aux)
        sign_next = math.copysign(1.0, res_next) if res_next != 0.0 else 0.0
        if sign_next != sign_prev and sign_prev != 0.0:
            return lam_prev, lam_next
        lam_prev, sign_prev = lam_next, sign_next

    return lam_prev, None


def solve_picard(
    N_init: float,
    N_final: float,
    delta_Nstar: float,
    alpha: float,
    H_sq_nl_init: float,
    grid,
    trajectory,
    potential,
    diffusion_model,
    atol: float,
    rtol: float,
    phi_end: float,
    disable_spatial_coupling: bool = False,
    instrument_stiffness: bool = True,
    label: Optional[str] = None,
    verbose: bool = False,
    full_instanton_seed: Optional[dict] = None,
    theta: float = DEFAULT_SAT_THETA,
    anderson_m: int = DEFAULT_ANDERSON_M,
    seed_profile: str = DEFAULT_SEED_PROFILE,
    wallclock_budget_seconds: Optional[float] = None,
    max_step: Optional[float] = None,
) -> dict:
    """
    Solve the gradient-coupled instanton BVP over the onion coordinate grid
    by Picard iteration with an outer shooting correction on the shooting
    parameter lambda = P1-equivalent terminal Lagrange multiplier.

    Boundary conditions (local N; see module docstring for the N convention):
        phi(y_j, N=0.0) = phi_init, pi(y_j, N=0.0) = pi_init  (uniform in y)
        phi(y=+1, N=N_total) = phi_end   [shooting condition on lambda]

    full_instanton_seed (prompt 21a, optional; extended prompt 22c): a
    pre-computed result dict shaped like _compute_full_instanton's own
    return value (plus "final_lambda"), used to seed (a) sweep-0's onion-
    interpolated forward-field guess, (b) the outer shooting loop's initial
    lambda, and (c) the FIXED pi_core SAT target -- see
    _fetch_full_instanton_profile's own docstring for the full fetch-then-
    fallback preference order. None (the default) means "no pre-fetched
    seed available" -- solve_picard computes one inline instead. Ignored
    entirely when disable_spatial_coupling=True (there is no SAT and no
    onion structure to seed in that reduction mode -- see below).

    theta, anderson_m (prompts 21a/22b, optional; DORMANT as of prompt 22c
    -- see DEFAULT_SAT_THETA's own comment and the module docstring's "pi_core
    SAT target" section): together control the now-abandoned self-consistent
    update rule for g_pi_core. The production defaults (0.0, 0) make the
    target permanently FIXED at the FullInstanton seed for the whole solve;
    non-default values (e.g. theta=1.0, anderson_m=5, prompt 22b's own
    production values) remain reachable for regression comparison only.

    seed_profile (prompt 22c, optional, default DEFAULT_SEED_PROFILE): the
    sweep-0 onion-interpolation shape between the FullInstanton core and
    noiseless-background exterior endmembers -- see _seed_profile_weights.

    wallclock_budget_seconds (prompt 24 prerequisite, optional, default
    None): a global wall-clock budget for this ENTIRE solve_picard call
    (every outer shooting evaluation, every inner Picard sweep, every
    forward/backward solve_ivp call). None (default) means unbounded --
    every pre-existing caller's behaviour is unchanged. When set, a deadline
    of compute_start + wallclock_budget_seconds is checked at RHS-call
    granularity (the finest level, see the module-level "prerequisite"
    comment above); once passed, the solve bails GRACEFULLY, keeping
    whatever grid the last completed sweep/outer-iteration produced --
    never a hard crash. The outcome is tagged via _classify_bailout and
    exposed in "diagnostics" as "bailout_tag"/"bailout_reason".

    max_step (prompt 24 prerequisite, optional, default None): forwarded to
    every solve_ivp call as its own max_step. None (default) resolves to
    DEFAULT_MAX_STEP_FRACTION * N_total, bounding a single accepted step to
    a generous fraction of the whole integration span so a pathological
    single step cannot itself run unbounded before the next RHS-level
    deadline check gets a chance to fire.

    instrument_stiffness (prompt 17 Part B; default True): when True,
    every forward/backward RK45 solve_ivp call made during this solve (every
    inner-Picard forward/backward solve across every outer shooting
    evaluation) is instrumented via _solve_ivp_instrumented/
    _count_rk45_step_attempts, and the aggregated step-count/step-size/
    wall-clock statistics are folded into the returned "diagnostics" dict
    under "rk45_forward_*", "rk45_backward_*", and
    "picard_sweep_wallclock_min/mean/max" (see _aggregate_rk45_stats's own
    docstring for the exact keys). This gates *measurement overhead only*
    -- it never changes solve_ivp's method, tolerances, grid, or the
    physics result. When False, these diagnostics keys are simply absent.

    verbose (default False): print one line per inner Picard sweep and one
    line per outer shooting evaluation (residual, lambda), so a long-running
    solve's progress is visible instead of blocking silently until it
    converges or exhausts MAX_OUTER. Off by default since production runs
    dispatch hundreds of solves in parallel Ray workers, where per-sweep
    prints would flood the log; intended for interactive/exploratory use.

    Returns a dict with keys:
        "N_total", "N_grid", "phi_grid", "pi_grid", "rfield_grid",
        "rmom_grid", "final_lambda", "failure", "diagnostics"
    """
    compute_start = time.perf_counter()
    ode_solve_count = 0

    # Prompt 24 prerequisite -- global deadline (None means unbounded, see
    # this function's own "wallclock_budget_seconds" docstring). Checked at
    # RHS-call granularity via _check_deadline() below.
    deadline = (
        None if wallclock_budget_seconds is None
        else compute_start + wallclock_budget_seconds
    )
    # budget_state["hit"] is set True the moment ANY deadline check fires --
    # read by the outer-loop bailout classification below to distinguish
    # "ran out of wall-clock" from a genuine ODE/structural failure (only
    # the latter is tagged "blown-up"; see _classify_bailout).
    budget_state = {"hit": False}

    def _check_deadline():
        if deadline is not None and time.perf_counter() > deadline:
            budget_state["hit"] = True
            raise _WallclockBudgetExceeded()

    # Prompt 17 Part B -- shared accumulators mutated (via .append(), never
    # reassigned) by picard_inner's closure below; aggregated into
    # "diagnostics" at every return point via _instrumentation_diagnostics().
    fwd_rk45_stats: list = []
    bwd_rk45_stats: list = []
    picard_sweep_wallclocks: list = []
    # Prompt 24 prerequisite -- abs(residual) at every SUCCESSFUL outer-loop
    # evaluation, in call order; the trend this traces out is what
    # _classify_bailout reads to tell "descending" (convergent-but-slow)
    # apart from "floored"/"diverging" at a non-convergent bail.
    outer_residual_history: list = []

    _lbl = label if label else f"phi_end={phi_end:.4g} N_init={N_init:.3g} N_final={N_final:.3g}"

    n_max = grid.n_max
    n_nodes = n_max + 1

    # Prompt 22b recalibration: atol*100 / atol*10 (the pre-22b values) were
    # never validated against genuine nonlinear coupling -- Finding 1 (prompt
    # 22) established that lambda=0 was an EXACT fixed point under the old
    # degenerate target, so these tolerances were always trivially satisfied
    # in a single sweep and never actually exercised. INNER_TOL is kept at
    # its prompt 22b recalibrated level even though the prompt 22c fixed
    # target converges the Picard sub-problem to machine precision in
    # practice (well below this tolerance) -- OUTER_TOL is the one that
    # actually gates outer-loop convergence for the fixed target.
    # OUTER_TOL_FLOOR (prompt 24b: extracted from the previously-bare 1.0e-2
    # literal into a module constant, purely so a diagnostic harness can
    # monkeypatch it -- same technique already used for MAX_OUTER/MAX_INNER
    # by tests/test_picard.py and this project's own diagnose_24a_
    # convergence_floor.py -- to check whether tightening it moves
    # msr_action, i.e. whether the floor is "doing physics" rather than
    # being a harmless safety margin. No default-behavior change.
    OUTER_TOL = max(atol * 1.0e6, OUTER_TOL_FLOOR)
    INNER_TOL = max(atol * 1.0e4, 1.0e-4)

    N_offset = trajectory.N_end - N_init
    N_total = (N_init - N_final) + delta_Nstar
    N_start = 0.0
    N_stop = N_total

    N_grid = np.linspace(N_start, N_stop, N_GRID_SIZE)
    N_grid_rev = N_grid[::-1]

    # Prompt 24 prerequisite -- see this function's own "max_step" docstring.
    effective_max_step = (
        max_step if max_step is not None else DEFAULT_MAX_STEP_FRACTION * N_total
    )

    if verbose:
        print(f"[{_lbl}] starting: n_nodes={n_nodes} N_total={N_total:.6g} "
              f"alpha={alpha:.6g} MAX_OUTER={MAX_OUTER} MAX_INNER={MAX_INNER}", flush=True)

    phi_init = trajectory.phi_at(N_offset + N_start)
    pi_init = trajectory.pi_at(N_offset + N_start)

    # Uniform-in-y initial condition (eq. bc-init): the core has not yet
    # deviated from the noiseless background anywhere on the grid. This is
    # the TRUE boundary condition phi(y_j, N=0)=phi_init for every y_j, and
    # is used as the forward pass's own ODE initial condition on EVERY
    # sweep of EVERY outer iteration -- never replaced by the sweep-0 seed
    # below, which only supplies the spline coefficients picard_inner's
    # first backward pass is built from (see the module docstring's own
    # "Sweep-0 forward-field seed" section).
    state_init = pack_state(np.full(n_nodes, phi_init), np.full(n_nodes, pi_init))

    def _unpack_grid(y_matrix: np.ndarray, N_values: np.ndarray):
        phi_grid = np.empty((len(N_values), n_nodes))
        pi_grid = np.empty((len(N_values), n_nodes))
        for i, N_i in enumerate(N_values):
            phi_full_i, pi_full_i = unpack_state(
                y_matrix[:, i], N_i, N_offset, alpha, H_sq_nl_init, grid, trajectory, potential
            )
            phi_grid[i] = phi_full_i
            pi_grid[i] = pi_full_i
        return phi_grid, pi_grid

    def _unpack_response_grid(y_matrix: np.ndarray, N_values: np.ndarray):
        rfield_grid = np.empty((len(N_values), n_nodes))
        rmom_grid = np.empty((len(N_values), n_nodes))
        for i in range(len(N_values)):
            rfield_full_i, rmom_full_i = unpack_response_state(y_matrix[:, i], grid)
            rfield_grid[i] = rfield_full_i
            rmom_grid[i] = rmom_full_i
        return rfield_grid, rmom_grid

    def _fwd_rhs(N, y, rfield_splines, rmom_splines, g_pi_core_spline, lam):
        # Prompt 24 prerequisite -- finest-granularity deadline check (see
        # the module-level comment): fires on the very next RHS evaluation,
        # so a runaway step-halving cascade is caught promptly rather than
        # only between whole solve_ivp calls.
        _check_deadline()
        return forward_rhs(
            N, y, N_offset, alpha, H_sq_nl_init, grid, trajectory, potential,
            rfield_splines, rmom_splines, diffusion_model,
            g_pi_core_spline,
            disable_spatial_coupling=disable_spatial_coupling,
            lam=lam,
        )

    def _bwd_rhs(N, y, phi_splines, pi_splines):
        _check_deadline()
        return response_rhs(
            N, y, alpha, H_sq_nl_init, grid, phi_splines, pi_splines, potential,
        )

    def _instrumentation_diagnostics() -> dict:
        """Folds the accumulated rk45_*/picard_sweep_wallclock_* keys into
        whatever diagnostics dict is about to be returned (success or
        failure) -- empty dict if instrument_stiffness is False, so those
        keys are simply absent rather than populated with placeholder
        values."""
        if not instrument_stiffness:
            return {}
        out = _aggregate_rk45_stats(fwd_rk45_stats, "forward", N_total)
        out.update(_aggregate_rk45_stats(bwd_rk45_stats, "backward", N_total))
        out["picard_sweep_wallclock_min"] = min(picard_sweep_wallclocks) if picard_sweep_wallclocks else None
        out["picard_sweep_wallclock_mean"] = (
            sum(picard_sweep_wallclocks) / len(picard_sweep_wallclocks) if picard_sweep_wallclocks else None
        )
        out["picard_sweep_wallclock_max"] = max(picard_sweep_wallclocks) if picard_sweep_wallclocks else None
        return out

    def _failure_result(diagnostics):
        return {
            "failure": True,
            "N_total": N_total,
            "N_grid": [],
            "phi_grid": [], "pi_grid": [],
            "rfield_grid": [], "rmom_grid": [],
            "final_lambda": None,
            "diagnostics": diagnostics,
        }

    # ── Sweep-0 seed: FullInstanton lambda/core profile + onion-
    # interpolated forward fields (prompt 22c) ─────────────────────────────
    # See the module docstring's "FullInstanton seed" and "Sweep-0
    # forward-field seed" sections. Skipped (falling back to the pre-22c
    # uniform-background starting point) when disable_spatial_coupling=True:
    # the SAT is switched off entirely in that (test-only) reduction mode,
    # every node then integrates the SAME decoupled per-node ODE from the
    # SAME uniform initial condition, so there is nothing on the grid for
    # the onion interpolation to distinguish, and no FullInstanton fetch is
    # worth paying for.
    # lambda_seed (prompt 24b -- see the module docstring's own "Lambda-seed
    # conversion" section; replaces prompt 22c's raw lambda_FI, wrong sign
    # and ~3 orders of magnitude too large for GCI's own lambda) seeds the
    # outer loop's FIRST STEP TARGET. lam0 itself defaults to the
    # always-feasible 0.0 (the trivial/background point) here, but is
    # overridden below (once evaluate()/commit() exist) by
    # _bracket_from_seed's own geometric-expansion result -- see that
    # function's own docstring. bootstrap_target/lam_bounds default to
    # None/unbounded (disable_spatial_coupling mode: no SAT, no onion
    # structure, no corridor to compute).
    lam0 = 0.0
    bootstrap_target: Optional[float] = None
    lambda_seed = 0.0
    lam_bounds: Optional[tuple] = None

    if disable_spatial_coupling:
        g_pi_values = None
        g_pi_core_spline = None
        ext_phi_N = np.array([trajectory.phi_at(N_offset + N) for N in N_grid])
        ext_pi_N = np.array([trajectory.pi_at(N_offset + N) for N in N_grid])
        phi_grid_seed = np.tile(ext_phi_N[:, None], (1, n_nodes))
        pi_grid_seed = np.tile(ext_pi_N[:, None], (1, n_nodes))
    else:
        profile = _fetch_full_instanton_profile(
            N_grid, N_offset, phi_init, pi_init, phi_end, N_total,
            trajectory, potential, diffusion_model, atol, rtol, _lbl,
            full_instanton_seed,
        )
        # The FIXED pi_core SAT target (prompt 22c): FullInstanton's own
        # pi_core(N) = phi2(N), never updated after this point (see the
        # module docstring's "pi_core SAT target" section and
        # _AndersonMixer's docstring for how DEFAULT_SAT_THETA=0.0 /
        # DEFAULT_ANDERSON_M=0 enforce this).
        g_pi_values = profile["phi2"]
        g_pi_core_spline = SplineWrapper(N_grid, g_pi_values, y_transform='linear', k=3)

        # Prompt 24b -- lambda_seed and the feasible corridor, both computed
        # a priori from D11, w_core, mu(N_total), lambda_FI (see the module
        # docstring's own derivation). "lgl_w_core" is the LGL BOUNDARY
        # QUADRATURE WEIGHT (grid.weights[-1]) -- deliberately named
        # differently from _seed_profile_weights' own w_core/w_ext ONION-
        # INTERPOLATION arrays a few lines below, an unrelated quantity
        # despite the similar name.
        lgl_w_core = grid.weights[-1]
        H_sq_core_seed = potential.H_sq(profile["phi1"][-1], profile["phi2"][-1])
        delta_s_N_final_seed = delta_s(N_total, 0.0, H_sq_core_seed, H_sq_nl_init, alpha)
        mu_final_seed = measure(1.0, delta_s_N_final_seed)
        lambda_seed = -profile["lambda_FI"] * lgl_w_core * mu_final_seed

        D11_seed, _, _ = diffusion_model.D_matrix(phi_init, pi_init, potential)
        lambda_c_positive = lgl_w_core * mu_final_seed / D11_seed
        lambda_c_negative = CORRIDOR_NEGATIVE_WIDENING * lambda_c_positive
        lam_bounds = (-lambda_c_negative, lambda_c_positive)

        bootstrap_target = lambda_seed

        w_core, w_ext = _seed_profile_weights(grid.nodes, seed_profile)
        ext_phi_N = np.array([trajectory.phi_at(N_offset + N) for N in N_grid])
        ext_pi_N = np.array([trajectory.pi_at(N_offset + N) for N in N_grid])
        phi_grid_seed = np.outer(profile["phi1"], w_core) + np.outer(ext_phi_N, w_ext)
        pi_grid_seed = np.outer(profile["phi2"], w_core) + np.outer(ext_pi_N, w_ext)

    def picard_inner(
        lam: float, phi_grid_in: np.ndarray, pi_grid_in: np.ndarray,
        g_pi_values_in: Optional[np.ndarray],
    ):
        """
        Run Picard iteration for fixed lambda. Returns grids or Nones, plus
        the dense-output (`dense_output=True`) solve_ivp solutions of the
        *last* inner iteration's forward/backward passes -- fp_sol maps
        N -> packed forward state (unpack via forward_rhs.unpack_state),
        bp_sol maps N -> packed response state (unpack via
        response_rhs.unpack_response_state). Exposed so callers (the MSR
        action convergence diagnostic) can resample at an arbitrary, finer
        N resolution without re-solving any ODE.

        phi_grid_in/pi_grid_in is the CURRENT-outer-iteration warm-start
        grid: the sweep-0 onion seed on the very first call (see
        solve_picard's own body), or the previous outer iteration's
        converged core trajectory thereafter. It is used directly to build
        this call's first backward pass's spline coefficients -- the
        response-field seed described in the module docstring's "Sweep-0
        forward-field seed" section is exactly this first backward pass,
        with no separate code path.

        g_pi_values_in is the pi_core SAT target, sampled on N_grid -- None
        when disable_spatial_coupling=True (never dereferenced in that
        mode). Returned (updated) as the final element of the tuple so the
        caller can carry it into the NEXT outer-loop evaluation; with the
        production defaults (DEFAULT_SAT_THETA=0.0, DEFAULT_ANDERSON_M=0)
        this is returned UNCHANGED (see _AndersonMixer.update), i.e. the
        fixed target, carried through unmodified rather than recomputed.
        """
        nonlocal ode_solve_count
        phi_grid = phi_grid_in.copy()
        pi_grid = pi_grid_in.copy()
        # rfield_tilde_grid/rmom_tilde_grid (prompt 23 Part B): the
        # lambda-RESCALED response fields r_tilde = r/lam, not the physical
        # ones -- see response_rhs.py's own module docstring for why this
        # rescaling is exact (response_rhs is linear and homogeneous in the
        # response fields) and why production integrates r_tilde rather than
        # the astronomic physical r. Converted back to physical (* lam) only
        # once, at this function's own return statement below.
        rfield_tilde_grid = np.zeros((N_GRID_SIZE, n_nodes))
        rmom_tilde_grid = np.zeros((N_GRID_SIZE, n_nodes))
        g_pi_values = None if g_pi_values_in is None else g_pi_values_in.copy()
        # Fresh mixer state per picard_inner call: lambda is fixed within
        # one call but changes between outer-loop evaluations, so even in
        # the dormant self-consistent mode (theta>0/anderson_m>0) stale
        # history would mix iterates/residuals from a different map. With
        # the production defaults this mixer is a no-op (see its own
        # docstring), so this is bookkeeping for the dormant path only.
        mixer = _AndersonMixer(anderson_m, theta)
        n_inner_iters = 0
        n_consecutive_converged = 0
        n_consecutive_growth = 0
        prev_inner_res = None
        fp_sol = None
        bp_sol = None

        for _ in range(MAX_INNER):
            # Prompt 24 prerequisite -- loop-level deadline check, BEFORE
            # starting a new sweep: a graceful bail that simply stops here,
            # keeping whatever phi_grid/pi_grid the last COMPLETED sweep
            # produced -- exactly like exhausting MAX_INNER naturally (see
            # this function's own docstring; no distinction is made
            # downstream between "converged inner" and "ran out of
            # iterations/budget", both proceed with whatever grid resulted).
            if deadline is not None and time.perf_counter() > deadline:
                budget_state["hit"] = True
                break
            sweep_start = time.perf_counter() if (instrument_stiffness or verbose) else None
            n_inner_iters += 1
            phi_splines = _build_node_splines(N_grid, phi_grid, y_transform='linear')
            pi_splines = _build_node_splines(N_grid, pi_grid, y_transform='linear')
            g_pi_core_spline = (
                None if g_pi_values is None
                else SplineWrapper(N_grid, g_pi_values, y_transform='linear', k=3)
            )

            # Backward pass: terminal condition at N_stop (eq. terminal-colloc).
            # prompt 23 Part B: solves for r_tilde = r/lam, NOT the physical
            # (astronomic-at-large-lam) response state -- terminal_response_state_rescaled
            # is the O(1)-ish, lambda-independent terminal condition (==
            # terminal_response_state(1.0, ...)); this is what keeps the
            # backward ODE's own state vector well-conditioned regardless of
            # how large the outer loop's actual lam is. See
            # response_rhs.py's own module docstring for the full account.
            H_sq_core_final = potential.H_sq(phi_grid[-1, -1], pi_grid[-1, -1])
            delta_s_N_final = delta_s(N_total, 0.0, H_sq_core_final, H_sq_nl_init, alpha)
            terminal_state = terminal_response_state_rescaled(grid, delta_s_N_final)

            try:
                bp, bp_step_stats = _solve_ivp_instrumented(
                    instrument_stiffness,
                    lambda N, y: _bwd_rhs(N, y, phi_splines, pi_splines),
                    (N_stop, N_start), terminal_state, method="RK45",
                    t_eval=N_grid_rev, dense_output=True, atol=atol, rtol=rtol,
                    max_step=effective_max_step,
                )
            except _WallclockBudgetExceeded:
                # Prompt 24 prerequisite -- caught at the same granularity as
                # an outright ODE failure (bp.success=False below): the
                # caller's evaluate() treats this exactly like an infeasible
                # probe, but budget_state["hit"] (already set inside
                # _check_deadline) lets the top-level classifier tell the
                # two apart -- "blown-up" is reserved for a genuine ODE
                # failure, not a wall-clock bail.
                return None, None, None, None, n_inner_iters, None, None, g_pi_values
            ode_solve_count += 1
            if bp_step_stats is not None:
                bwd_rk45_stats.append(bp_step_stats)
            if not bp.success:
                return None, None, None, None, n_inner_iters, None, None, g_pi_values

            response_y = bp.y[:, ::-1]
            rfield_tilde_grid, rmom_tilde_grid = _unpack_response_grid(response_y, N_grid)

            # Splines reconstruct r_tilde(N), not the physical response
            # field -- forward_rhs's own lam parameter below supplies the
            # missing factor back at the point it is actually needed (the
            # noise-sourcing feedback), via noise_source_terms's
            # (D*lam)*r_tilde grouping, never materializing lam*r_tilde as a
            # bare intermediate. sinh transform is unchanged (still
            # appropriate: r_tilde can be either sign and spans orders of
            # magnitude, just a smaller dynamic range than the physical r).
            rfield_splines = _build_node_splines(N_grid, rfield_tilde_grid, y_transform='sinh')
            rmom_splines = _build_node_splines(N_grid, rmom_tilde_grid, y_transform='sinh')

            # Forward pass, now sourced by the just-computed response fields
            # (rescaled -- lam supplies the physical scale back inside
            # forward_rhs/noise_source_terms).
            try:
                fp, fp_step_stats = _solve_ivp_instrumented(
                    instrument_stiffness,
                    lambda N, y: _fwd_rhs(N, y, rfield_splines, rmom_splines, g_pi_core_spline, lam),
                    (N_start, N_stop), state_init, method="RK45",
                    t_eval=N_grid, dense_output=True, atol=atol, rtol=rtol,
                    max_step=effective_max_step,
                )
            except _WallclockBudgetExceeded:
                return None, None, None, None, n_inner_iters, None, None, g_pi_values
            ode_solve_count += 1
            if fp_step_stats is not None:
                fwd_rk45_stats.append(fp_step_stats)
            if not fp.success:
                return None, None, None, None, n_inner_iters, None, None, g_pi_values

            phi_grid_new, pi_grid_new = _unpack_grid(fp.y, N_grid)
            inner_res = np.max(np.abs(phi_grid_new - phi_grid))
            phi_grid, pi_grid = phi_grid_new, pi_grid_new
            fp_sol, bp_sol = fp.sol, bp.sol

            # Divergence early-exit (prompt 22c): outside the small
            # neighbourhood the fixed target is seeded near, an outer-loop
            # probe at a poorly-chosen lambda can produce a Picard map whose
            # residual GROWS every sweep rather than merely failing an ODE
            # solve outright (H_sq_local < 0 etc.) -- exhausting the full
            # MAX_INNER budget on a probe that was never going to converge,
            # every outer iteration, made the outer loop's own escalation
            # (stall_growth) impractically slow. DIVERGENCE_GROWTH_PATIENCE
            # consecutive sweeps of growth, once the residual is well above
            # INNER_TOL (not just noise near the fixed point), is treated
            # exactly like an outright ODE failure -- this probe's lambda is
            # rejected by the caller's backtracking, not silently degraded
            # to a worse "converged" answer.
            if prev_inner_res is not None and inner_res > prev_inner_res and inner_res > DIVERGENCE_RESIDUAL_FLOOR:
                n_consecutive_growth += 1
                if n_consecutive_growth >= DIVERGENCE_GROWTH_PATIENCE:
                    return None, None, None, None, n_inner_iters, None, None, g_pi_values
            else:
                n_consecutive_growth = 0
            prev_inner_res = inner_res

            # ---------------------------------------------------------------
            # pi_core SAT target update (prompts 21a/22b; DORMANT as of
            # prompt 22c -- see the module docstring's "pi_core SAT target"
            # section). With the production defaults (DEFAULT_SAT_THETA=0.0,
            # DEFAULT_ANDERSON_M=0), mixer.update returns g_pi_values
            # UNCHANGED: the target is genuinely fixed at the FullInstanton
            # seed for the whole solve, not updated from this sweep's own
            # just-computed pi_core(N). Non-default (theta>0/anderson_m>0)
            # reproduces the abandoned self-consistent scheme, kept only for
            # regression comparison.
            # ---------------------------------------------------------------
            if g_pi_values is not None:
                g_k = pi_grid_new[:, -1] - g_pi_values
                g_pi_values = mixer.update(g_pi_values, g_k)

            if instrument_stiffness:
                picard_sweep_wallclocks.append(time.perf_counter() - sweep_start)
            if verbose:
                sweep_time = time.perf_counter() - sweep_start if sweep_start is not None else None
                print(
                    f"[{_lbl}]     picard sweep {n_inner_iters}/{MAX_INNER}: "
                    f"max|dphi|={inner_res:.6e} (tol={INNER_TOL:.3e})"
                    + (f"  [{sweep_time:.2f}s]" if sweep_time is not None else ""),
                    flush=True,
                )
            # Sustained-convergence check (prompt 22b): guards against a
            # transient single-sweep dip being mistaken for having reached
            # the fixed point -- matters most for the dormant self-
            # consistent path (whose map is not monotone); the fixed target
            # (production default) converges monotonically to machine
            # precision so this check is trivially satisfied there.
            if inner_res < INNER_TOL:
                n_consecutive_converged += 1
                if n_consecutive_converged >= INNER_CONSECUTIVE_REQUIRED:
                    break
            else:
                n_consecutive_converged = 0

        # Reintroduce lam HERE, exactly once, as a single vectorized
        # multiply -- prompt 23 Part B's own scaled/unscaled boundary.
        # Every consumer of this function's return value (msr_action,
        # datastore storage, noise diagnostics, the outer loop's own
        # phi_end residual check via phi_grid -- unaffected, phi/pi were
        # never rescaled) expects the PHYSICAL response fields, matching
        # every pre-prompt-23 caller's expectation exactly; only the
        # backward ODE integration itself (above) and forward_rhs's own
        # noise-sourcing feedback ever see r_tilde.
        rfield_grid = lam * rfield_tilde_grid
        rmom_grid = lam * rmom_tilde_grid
        return phi_grid, pi_grid, rfield_grid, rmom_grid, n_inner_iters, fp_sol, bp_sol, g_pi_values

    # ── Outer shooting loop on lambda (prompt 22c: shared with FullInstanton
    # via Numerics/ShootingSolver.py; see that module's own docstring for the
    # secant/Armijo-backtracking/trust-region algorithm) ───────────────────
    phi_grid_f, pi_grid_f = phi_grid_seed, pi_grid_seed
    rfield_grid_f = np.zeros((N_GRID_SIZE, n_nodes))
    rmom_grid_f = np.zeros((N_GRID_SIZE, n_nodes))
    fp_sol_f = None
    bp_sol_f = None
    picard_iterations_per_outer = []
    picard_time_total = 0.0
    picard_iters_total = 0

    def evaluate(lam: float):
        nonlocal picard_time_total, picard_iters_total
        if verbose:
            print(f"[{_lbl}]   shooting probe: lambda={lam:.6g}", flush=True)
        picard_start = time.perf_counter()
        pg, pig, rfg, rmg, n_inner, fp_sol, bp_sol, g_pi_new = picard_inner(
            lam, phi_grid_f, pi_grid_f, g_pi_values
        )
        picard_time_total += time.perf_counter() - picard_start
        picard_iters_total += n_inner
        picard_iterations_per_outer.append(n_inner)
        if pg is None:
            print(f"[{_lbl}] Picard inner failed at lambda={lam:.6g}")
            return None, False, None
        residual = pg[-1, -1] - phi_end
        # Prompt 24 prerequisite -- the trend _classify_bailout reads at a
        # non-convergent bail (see this function's own outer-scope comment).
        outer_residual_history.append(abs(residual))
        if verbose:
            print(
                f"[{_lbl}]   lambda={lam:.6g}: residual={residual:.6e} "
                f"(tol={OUTER_TOL:.3e}), {n_inner} picard sweeps, "
                f"{picard_time_total:.1f}s picard time so far", flush=True,
            )
        return residual, True, (pg, pig, rfg, rmg, fp_sol, bp_sol, g_pi_new)

    def commit(aux):
        nonlocal phi_grid_f, pi_grid_f, rfield_grid_f, rmom_grid_f, fp_sol_f, bp_sol_f, g_pi_values
        pg, pig, rfg, rmg, fp_sol, bp_sol, g_pi_new = aux
        phi_grid_f, pi_grid_f, rfield_grid_f, rmom_grid_f = pg, pig, rfg, rmg
        fp_sol_f, bp_sol_f = fp_sol, bp_sol
        g_pi_values = g_pi_new

    # Prompt 24b -- bracket the root by geometric expansion from lambda_seed
    # (E=1) BEFORE handing off to the hardened secant/Armijo/trust-region
    # solver below, replacing "propose lambda_FI, blow up, backtrack" with
    # "propose only inside the feasible corridor, from an already correctly
    # -signed and -scaled seed" (see the module docstring's own "Bracket
    # expansion from the seed" section and _bracket_from_seed's own
    # docstring). Only runs when a corridor was actually computed (skipped
    # in disable_spatial_coupling mode, where lam_bounds/lambda_seed stay at
    # their unbounded/0.0 defaults and the pre-24b lam0=0.0/
    # bootstrap_target=None convention is unchanged). n_bracket_evaluations
    # is read off outer_residual_history's own length (every evaluate() call
    # appends to it, bracket-phase or not) purely for diagnostics -- these
    # evaluations are NOT counted in solve_shooting's own
    # outer_iterations/n_evaluations below, since they happen before that
    # loop starts.
    n_bracket_evaluations = 0
    if lam_bounds is not None:
        lam_lo, lam_hi = lam_bounds
        lam0, bootstrap_target = _bracket_from_seed(
            evaluate, commit, lambda_seed, lam_lo, lam_hi,
        )
        n_bracket_evaluations = len(outer_residual_history)

    # stall_growth is set far more conservatively than FullInstanton's own
    # call site (which needs to reach O(1e9) from O(0.05) -- see that
    # module's own comment): GCI's own lambda is expected to stay modest
    # (O(1)-O(100)), so its true root, when the bootstrap_target guess
    # turns out to be somewhat off, is typically NEARBY rather than
    # orders of magnitude further out. An aggressive escalation factor
    # here was observed to overshoot straight past a nearby, narrow
    # feasible window (confirmed directly on a small test case where the
    # true, fixed-target-biased root sat within O(1) of lam0 but a 10x
    # per-stall escalation jumped to O(100) and back without ever probing
    # the narrow window in between). lam_bounds (prompt 24b) additionally
    # clamps every proposed step -- bootstrap, stall, secant, and every
    # backtracking probe derived from any of those -- into the feasible
    # corridor; see Numerics/ShootingSolver.py's own lam_bounds docstring.
    shoot = solve_shooting(
        evaluate, commit, lam0=lam0, tol=OUTER_TOL, max_outer=MAX_OUTER,
        bootstrap_target=bootstrap_target, stall_growth=1.5,
        deadline=deadline, lam_bounds=lam_bounds,
    )

    # Prompt 24 prerequisite -- non-convergence classification (see the
    # module-level comment and _classify_bailout's own docstring). A
    # non-convergent bail is tagged "blown-up" (structural: an outright
    # ODE/divergence failure on the LAST outer evaluation) only when neither
    # ShootingSolver's own deadline check NOR any inner-loop/RHS-level
    # deadline check (budget_state["hit"]) fired, and the loop broke before
    # exhausting MAX_OUTER -- the signature of evaluate() returning
    # success=False. Everything else (deadline fired anywhere, or MAX_OUTER
    # genuinely exhausted with the last evaluation still succeeding) falls
    # through to the residual-trend classifier.
    bail_is_ode_failure = (
        not shoot.converged
        and not shoot.budget_exceeded
        and not budget_state["hit"]
        and shoot.outer_iterations < MAX_OUTER
    )
    bailout_tag = _classify_bailout(shoot.converged, bail_is_ode_failure, outer_residual_history)
    if shoot.converged:
        bailout_reason = "converged"
    elif shoot.budget_exceeded or budget_state["hit"]:
        bailout_reason = "wallclock_budget"
    elif bail_is_ode_failure:
        bailout_reason = "ode_failure"
    else:
        bailout_reason = "max_outer_exhausted"

    diagnostics = {
        "compute_time": time.perf_counter() - compute_start,
        "converged": shoot.converged,
        "final_residual": shoot.final_residual,
        "total_ode_solves": ode_solve_count,
        "outer_iterations": shoot.outer_iterations,
        "newton_fallback_count": shoot.newton_fallback_count,
        "final_lambda": shoot.lam if shoot.converged else None,
        "picard_iterations_per_outer": picard_iterations_per_outer,
        "min_picard_iterations": min(picard_iterations_per_outer) if picard_iterations_per_outer else None,
        "max_picard_iterations": max(picard_iterations_per_outer) if picard_iterations_per_outer else None,
        "mean_picard_iterations": (
            sum(picard_iterations_per_outer) / len(picard_iterations_per_outer)
            if picard_iterations_per_outer else None
        ),
        "mean_time_per_picard_iteration": (
            picard_time_total / picard_iters_total if picard_iters_total else None
        ),
        "bailout_tag": bailout_tag,
        "bailout_reason": bailout_reason,
        "outer_residual_history": outer_residual_history,
        "wallclock_budget_seconds": wallclock_budget_seconds,
        "wallclock_budget_exceeded": shoot.budget_exceeded or budget_state["hit"],
        # Prompt 24b -- lambda-seed conversion + feasible-lambda corridor
        # (see the module docstring's own derivation). lambda_c_positive/
        # negative and lambda_seed are None in disable_spatial_coupling mode
        # (lam_bounds stays unset there -- no SAT, no corridor to compute).
        # gradient_enhancement_E = final_lambda / lambda_seed is the
        # physically interesting "how much extra terminal response the core
        # needs beyond the homogeneous baseline" quantity the module
        # docstring's own "Bracket expansion" section describes -- only
        # defined on a converged solve with a nonzero lambda_seed.
        "lambda_seed": lambda_seed if lam_bounds is not None else None,
        "lambda_c_positive": lam_bounds[1] if lam_bounds is not None else None,
        "lambda_c_negative": lam_bounds[0] if lam_bounds is not None else None,
        "n_bracket_evaluations": n_bracket_evaluations,
        "gradient_enhancement_E": (
            shoot.lam / lambda_seed
            if shoot.converged and lambda_seed not in (0.0, None)
            else None
        ),
        **_instrumentation_diagnostics(),
    }

    if not shoot.converged:
        print(f"[{_lbl}] outer loop did not converge "
              f"after {MAX_OUTER} iterations (target tolerance was {OUTER_TOL})")
        return _failure_result(diagnostics)

    return {
        "failure": False,
        "N_total": N_total,
        "N_grid": N_grid.tolist(),
        "phi_grid": phi_grid_f.tolist(),
        "pi_grid": pi_grid_f.tolist(),
        "rfield_grid": rfield_grid_f.tolist(),
        "rmom_grid": rmom_grid_f.tolist(),
        "final_lambda": shoot.lam,
        "diagnostics": diagnostics,
        # Final pi_core SAT target (prompt 21a; fixed as of prompt 22c),
        # sampled on N_grid -- None when disable_spatial_coupling=True.
        # Stored for post-hoc auditability: with the production (fixed-
        # target) defaults this equals the FullInstanton seed's phi2 array
        # EXACTLY (never updated), so max|pi_core - g_pi_core_final| is the
        # fixed-target bias quantified by tests/test_picard.py's own
        # regression, NOT expected to vanish at convergence (contrast the
        # pre-22c self-consistent target, whose whole point was that this
        # gap DID vanish).
        "g_pi_core_final": g_pi_values.tolist() if g_pi_values is not None else None,
        # Dense-output (continuous, not just N_grid-sampled) forward/response
        # solutions of the converged final Picard iteration -- scipy
        # OdeSolution callables, N -> packed state vector (unpack via
        # forward_rhs.unpack_state / response_rhs.unpack_response_state).
        # Exposed so a caller can resample at an arbitrary finer N resolution
        # (e.g. the MSR action's empirical N-quadrature convergence
        # diagnostic) without re-solving any ODE. Not JSON-serializable and
        # not consumed by the Ray remote function's own returned dict -- a
        # test-only / direct-solve_picard-caller convenience.
        #
        # response_dense_solution IS THE RESCALED r_tilde SOLUTION (prompt 23
        # Part B), NOT the physical response state -- unlike "rfield_grid"/
        # "rmom_grid" above (already converted back to physical, * final_lambda,
        # inside picard_inner's own return statement), this dense OdeSolution
        # is the raw backward-pass integrator output, which integrates
        # r_tilde = r/lam throughout (see response_rhs.py's own module
        # docstring). A caller resampling this directly must multiply by
        # "final_lambda" (this same dict's own key) to recover the physical
        # response state at the resampled N.
        "phi_pi_dense_solution": fp_sol_f,
        "response_dense_solution": bp_sol_f,
    }
