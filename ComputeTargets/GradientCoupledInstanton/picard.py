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

import time
from contextlib import contextmanager
from typing import Optional

import numpy as np
import scipy.integrate._ivp.rk as _scipy_rk
from scipy.integrate import solve_ivp

from Interpolation.spline_wrapper import SplineWrapper
from Numerics.OnionCoordinate import delta_s
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
    terminal_response_state,
)

MAX_OUTER = 50
MAX_INNER = 30

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

    # Prompt 17 Part B -- shared accumulators mutated (via .append(), never
    # reassigned) by picard_inner's closure below; aggregated into
    # "diagnostics" at every return point via _instrumentation_diagnostics().
    fwd_rk45_stats: list = []
    bwd_rk45_stats: list = []
    picard_sweep_wallclocks: list = []

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
    OUTER_TOL = max(atol * 1.0e6, 1.0e-2)
    INNER_TOL = max(atol * 1.0e4, 1.0e-4)

    N_offset = trajectory.N_end - N_init
    N_total = (N_init - N_final) + delta_Nstar
    N_start = 0.0
    N_stop = N_total

    N_grid = np.linspace(N_start, N_stop, N_GRID_SIZE)
    N_grid_rev = N_grid[::-1]

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

    def _fwd_rhs(N, y, rfield_splines, rmom_splines, g_pi_core_spline):
        return forward_rhs(
            N, y, N_offset, alpha, H_sq_nl_init, grid, trajectory, potential,
            rfield_splines, rmom_splines, diffusion_model,
            g_pi_core_spline,
            disable_spatial_coupling=disable_spatial_coupling,
        )

    def _bwd_rhs(N, y, phi_splines, pi_splines):
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
    # lambda_FI (prompt 22c) seeds the outer loop's FIRST STEP TARGET, not
    # its starting point: lam0 itself always stays at the always-feasible
    # 0.0 (the trivial/background point, exactly like the pre-22c outer
    # loop), and lambda_FI is passed to solve_shooting as bootstrap_target
    # (see that function's own docstring). Jumping the outer loop's
    # STARTING point itself directly to lambda_FI was tried and found
    # UNSAFE in general -- FullInstanton's own converged lambda for the
    # "same" nominal BVP is not always a good approximation to this BVP's
    # own true lambda once genuine spatial/gradient coupling and SBP-SAT
    # dissipation are active (observed directly: on several small test
    # cases, lambda_FI put the very FIRST Picard evaluation in an
    # infeasible, H_sq<0 region -- an unrecoverable failure with lam0 as
    # the only evaluated point and no secant history to fall back on).
    # Routing it through bootstrap_target instead means a bad guess safely
    # backtracks to a smaller, feasible step (ordinary Armijo backtracking,
    # unchanged), rather than failing the whole solve outright -- restoring
    # the "seed quality only affects convergence speed" property for
    # lambda too, not just the pi_core target/forward-field grid below.
    lam0 = 0.0
    bootstrap_target: Optional[float] = None

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
        bootstrap_target = profile["lambda_FI"]

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
        rfield_grid = np.zeros((N_GRID_SIZE, n_nodes))
        rmom_grid = np.zeros((N_GRID_SIZE, n_nodes))
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
            sweep_start = time.perf_counter() if (instrument_stiffness or verbose) else None
            n_inner_iters += 1
            phi_splines = _build_node_splines(N_grid, phi_grid, y_transform='linear')
            pi_splines = _build_node_splines(N_grid, pi_grid, y_transform='linear')
            g_pi_core_spline = (
                None if g_pi_values is None
                else SplineWrapper(N_grid, g_pi_values, y_transform='linear', k=3)
            )

            # Backward pass: terminal condition at N_stop (eq. terminal-colloc).
            H_sq_core_final = potential.H_sq(phi_grid[-1, -1], pi_grid[-1, -1])
            delta_s_N_final = delta_s(N_total, 0.0, H_sq_core_final, H_sq_nl_init, alpha)
            terminal_state = terminal_response_state(lam, grid, delta_s_N_final)

            bp, bp_step_stats = _solve_ivp_instrumented(
                instrument_stiffness,
                lambda N, y: _bwd_rhs(N, y, phi_splines, pi_splines),
                (N_stop, N_start), terminal_state, method="RK45",
                t_eval=N_grid_rev, dense_output=True, atol=atol, rtol=rtol,
            )
            ode_solve_count += 1
            if bp_step_stats is not None:
                bwd_rk45_stats.append(bp_step_stats)
            if not bp.success:
                return None, None, None, None, n_inner_iters, None, None, g_pi_values

            response_y = bp.y[:, ::-1]
            rfield_grid, rmom_grid = _unpack_response_grid(response_y, N_grid)

            rfield_splines = _build_node_splines(N_grid, rfield_grid, y_transform='sinh')
            rmom_splines = _build_node_splines(N_grid, rmom_grid, y_transform='sinh')

            # Forward pass, now sourced by the just-computed response fields.
            fp, fp_step_stats = _solve_ivp_instrumented(
                instrument_stiffness,
                lambda N, y: _fwd_rhs(N, y, rfield_splines, rmom_splines, g_pi_core_spline),
                (N_start, N_stop), state_init, method="RK45",
                t_eval=N_grid, dense_output=True, atol=atol, rtol=rtol,
            )
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
    # the narrow window in between).
    shoot = solve_shooting(
        evaluate, commit, lam0=lam0, tol=OUTER_TOL, max_outer=MAX_OUTER,
        bootstrap_target=bootstrap_target, stall_growth=1.5,
    )

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
        "phi_pi_dense_solution": fp_sol_f,
        "response_dense_solution": bp_sol_f,
    }
