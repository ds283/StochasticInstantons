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
Generic scalar shooting/secant solver with Armijo backtracking and a
trust-region step cap (prompt 22c), factored out of
``ComputeTargets/GradientCoupledInstanton/picard.py``'s own outer Newton
loop (prompt 22b) so ``ComputeTargets/FullInstanton.py`` -- whose own
finite-difference-probe outer loop was independently flagged as poorly
conditioned (``.documents/gradient-coupled-instanton/22-validation.md``
Finding 1b) and, as of prompt 22c, sits on the critical path as the
GradientCoupledInstanton seed source -- can share the same hardening rather
than duplicating it.

Deliberately physics-free, matching the rest of ``Numerics/``: this module
knows nothing about phi/pi/lambda or any BVP-specific state. It only knows
that ``evaluate(lam) -> (residual, success, aux)`` is a scalar residual map
whose root is being sought, and that ``commit(aux)`` lets the caller fold a
newly-accepted evaluation's payload into whatever warm-start state its OWN
next ``evaluate()`` call will read (e.g. the current Picard core-field
grids) -- ``aux`` is passed straight through, never inspected here.

Algorithm (unchanged from prompt 22b's picard.py implementation): a secant
step between the last two REAL evaluated ``(lambda, residual)`` points, not
a finite-difference derivative probe -- a small-``dlam`` probe is dominated
by inner-loop noise once the shooting problem is genuinely (nonlinearly)
coupled, see ``.documents/gradient-coupled-instanton/
22b-convergent-iteration-design-note.md`` Section "The outer shooting loop
needed its own, separate hardening". The secant step is trust-region capped
and Armijo-backtracked (halve the step until a probe both succeeds and
strictly reduces ``|residual|``, or exhaust ``max_backtrack`` and take the
smallest step tried regardless). The winning backtrack evaluation is carried
forward as ``pending`` into the next outer iteration rather than re-solved
from scratch, halving the typical per-outer-iteration cost.
"""

import math
import time
from dataclasses import dataclass
from typing import Any, Callable, Optional, Tuple

# (residual, success, aux) -- aux is opaque payload, only ever handed to
# `commit`, never inspected by this module.
EvalResult = Tuple[Optional[float], bool, Any]

DEFAULT_MAX_BACKTRACK = 5
DEFAULT_TRUST_RADIUS0 = 0.05
DEFAULT_TRUST_RADIUS_MAX = 1.0e2
DEFAULT_TRUST_RADIUS_MIN = 1.0e-6
DEFAULT_FALLBACK_GAIN = 0.1
DEFAULT_STALL_GROWTH = 10.0


@dataclass
class ShootingResult:
    lam: float
    converged: bool
    final_residual: Optional[float]
    outer_iterations: int
    newton_fallback_count: int
    n_evaluations: int
    # True when the loop exited because `deadline` (prompt 24 prerequisite
    # wall-clock safeguard) elapsed before the next outer iteration started,
    # rather than because max_outer was exhausted or evaluate() failed
    # outright. Lets callers (picard.py's own non-convergence classifier)
    # distinguish "ran out of wall-clock" from "ran out of iterations" from
    # "the underlying BVP solve failed" -- see picard.py's own
    # _classify_bailout.
    budget_exceeded: bool = False


def solve_shooting(
    evaluate: Callable[[float], EvalResult],
    commit: Callable[[Any], None],
    lam0: float,
    tol: float,
    max_outer: int,
    max_backtrack: int = DEFAULT_MAX_BACKTRACK,
    trust_radius0: float = DEFAULT_TRUST_RADIUS0,
    trust_radius_max: float = DEFAULT_TRUST_RADIUS_MAX,
    trust_radius_min: float = DEFAULT_TRUST_RADIUS_MIN,
    fallback_gain: float = DEFAULT_FALLBACK_GAIN,
    stall_growth: float = DEFAULT_STALL_GROWTH,
    bootstrap_target: Optional[float] = None,
    deadline: Optional[float] = None,
    lam_bounds: Optional[Tuple[float, float]] = None,
) -> ShootingResult:
    """
    Find lam such that ``evaluate(lam)``'s residual is within ``tol`` of
    zero, via secant + Armijo backtracking + trust region.

    ``deadline`` (prompt 24 prerequisite wall-clock safeguard, optional): a
    ``time.perf_counter()``-comparable timestamp. Checked at the top of
    every outer iteration (before calling ``evaluate`` again); once passed,
    the loop exits immediately with whatever ``lam``/``final_residual`` was
    last committed, exactly as if ``max_outer`` had been reached, with
    ``ShootingResult.budget_exceeded=True`` so the caller can tell the two
    apart. ``None`` (default) disables this check entirely -- unbounded by
    wall-clock, matching every pre-existing caller's behaviour.

    ``bootstrap_target`` (prompt 22c -- e.g. GradientCoupledInstanton's own
    FullInstanton-derived lambda_FI): an optional, independently-sourced
    guess at the answer, used ONLY to aim the very first step (there being
    no secant slope yet to aim it with otherwise). ``lam0`` itself should
    always be a value ``evaluate`` is known-safe at (e.g. the trivial/
    background point) -- ``bootstrap_target`` is not evaluated directly and
    unconditionally; the first step's SIZE is ``bootstrap_target - lam0``,
    but it goes through the ordinary Armijo backtracking loop below like any
    other step, so a bad guess (e.g. infeasible, or a poor approximation to
    the true answer for a DIFFERENT underlying model than whatever computed
    the guess) safely degrades to a smaller, feasible step rather than an
    unrecoverable first-evaluation failure. None (default) falls back to
    the ordinary fallback-gain/stall-escalation bootstrap.

    ``stall_growth`` (prompt 22c -- added when porting FullInstanton's own
    outer loop onto this shared component surfaced a failure mode GCI's own
    lambda range never exercised): when the secant slope is unavailable --
    at bootstrap (no second point yet) or because the last two evaluated
    residuals are indistinguishable (``|dres| <= 1e-14``, e.g. deep inside a
    region where the shooting parameter has almost no effect on the
    residual, such as FullInstanton's own lambda at an astronomically small
    diffusion coefficient) -- a small fixed-fraction nudge
    (``-residual * fallback_gain``) can never escape that region within a
    bounded ``max_outer``. Each such "stall" instead grows ``trust_radius``
    by a factor of ``stall_growth`` (compounding on consecutive stalls) and
    takes a step of exactly that size, so the search escalates geometrically
    until it reaches a region where lam actually has an effect. Once a real
    secant slope is available, ordinary trust-region-clipped secant steps
    resume.

    ``lam_bounds`` (prompt 24b -- ``(lo, hi)``, ``lo`` may be negative):
    an optional FEASIBLE-region clamp, physics-free from this module's own
    point of view (the caller derives ``lo``/``hi`` from whatever closed-form
    reasoning applies to its own BVP -- see
    ``ComputeTargets/GradientCoupledInstanton/picard.py``'s own corridor
    computation for the motivating case, a narrow window outside which the
    noise-sourcing feedback drives the forward pass's ``H^2_local<0``).
    ``None`` (default) disables clamping entirely -- every pre-existing
    caller (``FullInstanton``, whose own ``lambda`` legitimately spans many
    orders of magnitude with no such wall) is completely unaffected. When
    set, EVERY proposed evaluation point -- the bootstrap step, a stall
    escalation, a trust-region-clipped secant step, and every backtracking
    probe derived from any of those -- is clipped into ``[lo, hi]`` before
    ``evaluate`` is ever called on it, so a poorly-scaled guess or a runaway
    escalation can never itself request an infeasible point; the existing
    Armijo backtracking (which still applies afterwards) is therefore never
    asked to recover from a point ``evaluate`` was never going to accept.
    ``lam0`` itself is NOT clamped (the caller's responsibility to supply a
    value already inside ``[lo, hi]``, exactly like the existing
    "``evaluate`` is known-safe at ``lam0``" contract for ``bootstrap_target``
    above).

    ``evaluate(lam)`` must return ``(residual, success, aux)``: ``success``
    is False if lam is infeasible for the underlying BVP solve (e.g. an
    inner Picard/shooting sub-solve failed outright), in which case
    ``residual``/``aux`` are ignored. ``aux`` is an opaque per-evaluation
    payload (e.g. the resulting field grids) that this function never
    inspects -- it exists solely to be handed to ``commit``.

    ``commit(aux)`` is called once per outer iteration, with the ``aux`` of
    whichever evaluation becomes "current" (either freshly evaluated, or
    reused from the previous iteration's winning backtrack probe) -- this is
    the caller's opportunity to update whatever warm-start state its own
    ``evaluate`` closure reads on the next call (mirrors the pre-22c
    picard.py pattern of assigning ``phi_grid_f, pi_grid_f, ... = pg, pig,
    ...`` at the top of the outer loop).
    """
    lam = lam0
    lam_prev: Optional[float] = None
    residual_prev: Optional[float] = None
    trust_radius = trust_radius0
    # Direction used by the stall-escalation branch when there is no
    # secant slope to derive a sign from (prompt 22c). None until first
    # needed, at which point it is seeded from the residual's own sign (the
    # same heuristic as the plain fallback step); flipped thereafter
    # whenever a WHOLE escalation attempt (every backtrack halving) fails
    # outright, since that is direct evidence the guessed direction is
    # infeasible at every scale tried, not just poorly scaled -- see the
    # post-backtracking comment below.
    stall_sign: Optional[float] = None

    converged = False
    final_residual: Optional[float] = None
    outer_iterations = 0
    newton_fallback_count = 0
    n_evaluations = 0
    budget_exceeded = False

    # (residual, aux) of an already-evaluated point, reusable at the top of
    # the next outer iteration instead of re-running evaluate() there.
    pending: Optional[Tuple[float, Any]] = None

    for outer in range(max_outer):
        if deadline is not None and time.perf_counter() > deadline:
            budget_exceeded = True
            break
        outer_iterations = outer + 1
        if pending is not None:
            residual, aux = pending
            pending = None
        else:
            residual, success, aux = evaluate(lam)
            n_evaluations += 1
            if not success:
                break
        final_residual = abs(residual)
        commit(aux)

        if abs(residual) < tol:
            converged = True
            break
        if outer == max_outer - 1:
            # Last allowed outer iteration -- computing (and backtracking-
            # validating) a further step would be pure waste: the loop is
            # about to exit on its own range() bound and the result could
            # never be consumed.
            break

        # Secant step between the last two REAL evaluated points; bootstrap
        # (no second point yet) and degenerate-slope cases stall-escalate
        # instead (see stall_growth's own docstring above) -- UNLESS this is
        # the very first step and a bootstrap_target was supplied, in which
        # case that informed guess aims the first step instead.
        is_bootstrap = lam_prev is None
        if is_bootstrap:
            step = None
        else:
            dres = residual - residual_prev
            step = -residual * (lam - lam_prev) / dres if abs(dres) > 1.0e-14 else None
        lam_prev, residual_prev = lam, residual
        # direction_is_guessed: True whenever `step`'s SIGN carries no real
        # information from evaluate() (bootstrap_target's own guess, or the
        # residual-implied stall_sign default) -- see the post-backtracking
        # comment below for why this matters (flipping stall_sign only
        # makes sense when the direction itself was a guess, not when a
        # genuine secant slope was simply clipped to the trust radius).
        direction_is_guessed = False
        if step is None and is_bootstrap and bootstrap_target is not None:
            newton_fallback_count += 1
            step = bootstrap_target - lam
            stall_sign = math.copysign(1.0, step)
            direction_is_guessed = True
            if abs(step) > trust_radius:
                trust_radius = min(abs(step), trust_radius_max)
        elif step is None:
            newton_fallback_count += 1
            trust_radius = min(trust_radius * stall_growth, trust_radius_max)
            if stall_sign is None:
                stall_sign = math.copysign(1.0, -residual)
            step = math.copysign(trust_radius, stall_sign)
            direction_is_guessed = True
        elif abs(step) > trust_radius:
            # The secant slope DID resolve (dres above the 1e-14 floor), but
            # implies a step far beyond the current trust radius -- e.g. a
            # tiny-but-genuine slope deep inside a poorly-conditioned
            # shooting problem's near-flat region, correctly implying the
            # true root is many orders of magnitude further out. Growing
            # only via the (much slower) post-acceptance 1.2x multiplier
            # below would take hundreds of outer iterations to catch up to
            # what the model already, correctly, suggests. Escalate the
            # trust radius toward the model's own estimate at the same
            # bounded per-iteration rate as an outright stall
            # (stall_growth), rather than trusting a single possibly-noisy
            # estimate outright -- backtracking still catches a genuine
            # overshoot regardless.
            trust_radius = min(trust_radius * stall_growth, abs(step), trust_radius_max)
            step = math.copysign(trust_radius, step)

        # Corridor clamp (prompt 24b -- see lam_bounds's own docstring
        # above): clip the PROPOSED TARGET (not the step in isolation) into
        # [lo, hi], then re-derive step from the clipped target, so every
        # source of `step` above (bootstrap, stall escalation, trust-region-
        # clipped secant) is covered by one shared clamp rather than three
        # separate ones. Applied BEFORE backtracking begins, so no probe in
        # the loop below can ever request a point outside the corridor
        # (halving a step that already lands inside [lo, hi] can only move
        # the probe closer to lam, i.e. still inside).
        if lam_bounds is not None:
            lo, hi = lam_bounds
            target = min(max(lam + step, lo), hi)
            step = target - lam

        # Armijo-style backtracking: halve the step until a probe succeeds
        # and does not make |residual| worse, or exhaust max_backtrack and
        # take the smallest step tried regardless. Accepting a TIED (not
        # just strictly improved) residual matters for a flat/insensitive
        # region (stall_growth's own docstring): requiring strict
        # improvement there would keep halving an already-too-small step
        # forever, collapsing trust_radius instead of escalating it.
        best_step = step
        best_eval: Optional[Tuple[float, Any]] = None
        n_backtracks = 0
        for n_backtracks in range(max_backtrack):
            probe_residual, probe_success, probe_aux = evaluate(lam + step)
            n_evaluations += 1
            if probe_success:
                best_step = step
                best_eval = (probe_residual, probe_aux)
                if abs(probe_residual) <= abs(residual):
                    break
            step *= 0.5
        else:
            step = best_step

        if best_eval is not None:
            lam += step
            # Carry the accepted step's own evaluation into the next outer
            # iteration instead of re-solving it from scratch.
            pending = best_eval
        else:
            # EVERY probe in the backtracking sub-loop failed outright (not
            # just "didn't improve") -- there is no feasible step at this
            # scale in either direction tried. Do NOT fall back to the
            # ORIGINAL (already-confirmed-infeasible) step: lam stays put,
            # and the trust-region shrink below means the next outer
            # iteration's bootstrap/stall/secant step is smaller, tried
            # from the SAME last-known-good point, instead of jumping
            # straight back onto a point that just failed and dying on the
            # very next outer iteration's fresh (unconditional) evaluation.
            pending = None
            if direction_is_guessed:
                # The residual-implied (or bootstrap_target-implied)
                # direction was infeasible at EVERY scale tried in this
                # whole escalation attempt -- not just poorly scaled, since
                # backtracking already halves the magnitude down to a tiny
                # fraction of the attempted step before giving up. Flip the
                # guessed direction for the next stall attempt rather than
                # repeating a direction already shown to be a dead end
                # (confirmed necessary in practice: a fixed-target-biased
                # BVP's true root can sit on the OPPOSITE side of lam0 from
                # where the residual's own local sign points).
                stall_sign = -stall_sign if stall_sign is not None else None

        # Trust-region update: no backtracking needed -> the linear model
        # was locally trustworthy, so relax the radius; any backtracking ->
        # shrink it so the next step is not similarly overconfident.
        if n_backtracks == 0 and best_eval is not None:
            trust_radius = min(trust_radius * 1.2, trust_radius_max)
        else:
            trust_radius = max(trust_radius * 0.5, trust_radius_min)

    return ShootingResult(
        lam=lam,
        converged=converged,
        final_residual=final_residual,
        outer_iterations=outer_iterations,
        newton_fallback_count=newton_fallback_count,
        n_evaluations=n_evaluations,
        budget_exceeded=budget_exceeded,
    )
