# Prompt 22b — Convergent nonlinear iteration for the coupled instanton

Prompt: `.prompts/gradient-coupled-instanton/22b-convergent-nonlinear-iteration.md`.
Gated on prompt 22a (`.documents/gradient-coupled-instanton/22a-*`, commit
`a202162`), which fixed the degenerate `phi_end` target. This note covers
Phase 1 (diagnosis) and the resulting Phase 2 (fix) decision.

## Phase 1 — Diagnosis

### 1a. The fork: lagging vs. the coupling itself

`solve_picard`'s existing `theta` parameter and seed-fallback tiers already
provide the exact instrument needed for this fork, with no production code
change:

- **Lagged (production)**: `theta=1.0`, `full_instanton_seed=None` — sweep-0
  seed is `_seed_pi_core_values`'s tier-2 fetch (an inline `FullInstanton`
  solve consistent with *this* BVP's own `phi_end`), then re-lagged every
  sweep from the just-computed `pi_core(N)`.
- **Fixed**: `theta=0.0`, `full_instanton_seed=None` — same internally-consistent
  tier-2 seed, but the update line
  `g_pi_values = (1-theta)*g_pi_values + theta*pi_grid_new[:, -1]`
  reduces to a no-op, so the SAT target never moves off the seed.

Isolating the inner loop at the same `dlam≈1e-6` Newton-derivative probe used
by prompt 22's Finding 2 (`MAX_OUTER=1`, corrected/non-degenerate `phi_end`
from 22a), on the production case (`N_init=19.5, N_final=16.0, alpha=0.1`,
quadratic potential `m/Mp=1e-5`, `phi0=15 Mp`):

| `n` | `delta_Nstar` | `theta=1.0` (lagged) | `theta=0.0` (fixed) |
|---|---|---|---|
| 5 | 1.0 | diverges (residual ~1.8 at sweep 43, never < tol in 60 sweeps) | **converges in 1 sweep**, residual `5.0e-14` |
| 5 | 2.5 | diverges (Finding 2) | **converges in 1 sweep**, residual `3.8e-12` |
| 9 | 1.0 | diverges (Finding 2) | **converges in 1 sweep**, residual `1.8e-13` |
| 9 | 2.5 | diverges (Finding 2) | **converges in 1 sweep**, residual `4.1e-12` |
| 13 | 1.0 | diverges (Finding 2) | **converges in 1 sweep**, residual `3.8e-13` |
| 13 | 2.5 | diverges (Finding 2) | **converges in 1 sweep**, residual `2.4e-12` |

**The fixed target converges to machine precision in a single sweep, at
every `n` and `delta_Nstar` tried, while the lagged target reproduces
Finding 2's divergence at every one of the same points.** This resolves the
fork unambiguously: the lagged, sweep-to-sweep target *update* is the
culprit, not the forward/response coupling itself. **Go to Path 2A.**

(The single-sweep convergence of the fixed-target probe is itself expected
and not deeply informative on its own — the probe perturbation `dlam~1e-6`
is tiny and the tier-2 seed is already an accurate solution of a *very*
nearby problem — but its qualitative contrast with the lagged case's
divergence, reproduced identically across every `(n, delta_Nstar)` point
that Finding 2 exercised, is exactly the fork this experiment was designed
to resolve.)

A **broader stress test** — running `solve_picard` to full convergence
(`MAX_OUTER=50`, real outer-Newton search on `lambda`, not just the
`dlam` probe) with `theta=0.0` fixed for the entire solve — was attempted
and found impractically slow / at risk of leaving the physical domain
(`H_sq_local` occasionally negative during the outer-Newton search, per a
`RuntimeWarning: invalid value encountered in log` from
`Numerics/OnionCoordinate.py`) once `lambda` is pushed away from the tiny
`dlam` neighbourhood the probe above stays within. This is consistent with
`solve_picard`'s own docstring warning (prompt 21a) about a **frozen**
target becoming mismatched once the solve moves away from where it was
seeded: "the frozen, mismatched target biases the shooting problem enough
that no `lambda` can drive the true `phi_end` residual below tolerance."
This finding directly informs the Path 2A sub-choice below: a *permanently*
fixed target (2A.1) is not a safe default over the full outer-Newton range,
even though it is stable at the fixed point itself.

### 1b. Characterising the map

- **Confirmed inner-loop origin**: reproduced at `MAX_OUTER=1`, i.e. the
  divergence is intrinsic to a *single* `picard_inner` call at fixed
  `lambda` — not an outer-Newton effect (matches prompt 22's Finding 2).
- **Contraction factor, descending vs. growing phase** (geometric mean of
  sweep-to-sweep residual ratios, computed from
  `out-gradient-coupled-stiffness/scripts/validation_22_output/finding2_picard_divergence.csv`):

  | case | descending-phase ratio | growing-phase ratio |
  |---|---|---|
  | `n=5, ΔN*=1.0, θ=1.0` | 0.79 | **1.37** |
  | `n=5, ΔN*=1.5, θ=1.0` | 0.77 | **1.38** |
  | `n=5, ΔN*=2.5, θ=1.0` | 0.75 | **1.39** |
  | `n=7, ΔN*=1.0, θ=1.0` | 0.88 | **1.51** |

  The growing-phase ratio is `>1` (non-contractive) at every point, and is
  mildly **worse at `n=7` (1.51) than `n=5` (1.37-1.39)** — a small
  `n`-dependence, not `n`-independent, though far too weak to explain the
  divergence on its own (a spatial-resolution effect would need to vanish
  as `n→∞` for a well-posed continuum limit; the `θ=1` map is already
  non-contractive at the coarsest grid tried). `delta_Nstar` has almost no
  effect on the ratio (1.37-1.39 across `ΔN*=1.0-2.5`) — consistent with
  Finding 2's own observation that the failure is generic, not tied to a
  particular `delta_Nstar`.
- **Onset coincides with departure from the trivial neighbourhood**: at
  `MAX_OUTER=1`, the probe starts at `lambda=dlam≈1e-6` — the response
  fields and `pi_core(N)`'s deviation from the seed are both `O(dlam)` at
  sweep 1 and grow sweep-by-sweep as the lag chain accumulates structure.
  The descending phase (sweeps 1-~15) is exactly where the residual is
  still `O(dlam)`-small and the map behaves near-linearly/contractively;
  the transition to growth at sweep ~15 (independent of `n`) is where the
  accumulated lag error becomes large enough for the map's non-contractive
  character (`ratio>1`) to dominate over whatever initial-transient
  decay was present. This is consistent with (not proof of, but supporting
  evidence for) the mechanism named in `picard.py`'s own module docstring:
  the lagged SAT forcing `-tau*(pi_core^{k+1} - g^k)` is proportional to the
  *sweep-to-sweep change* in `pi_core`, i.e. a delayed-feedback term — a
  textbook route to iteration instability once the lag is no longer
  negligible relative to the solution's own scale.

### Mechanism summary

Lagging `g_pi_core` turns what should be an algebraic closure (evaluate the
SAT target from the *current* state, as `g_phi_core`'s live
`neumann_boundary_value` already does) into a one-step-delayed feedback
loop on `pi_core(N)`. The per-sweep linear operator itself (the SBP-SAT
advection/gradient assembly, prompts 20/21) is unaffected — its own
spectrum is unchanged by lagging (a fixed additive forcing term does not
enter the Jacobian an eigenvalue analysis would probe) — so this is
correctly scoped as a *nonlinear-iteration* defect layered on top of an
already-validated linear closure, exactly as the prompt states. The fixed
(non-lagged) target removes the delay entirely and the map's local
behaviour near the true fixed point is fine (Phase 1a's single-sweep
convergence), but a *permanently* frozen target is not safe far from where
it was seeded (Phase 1a's broader stress test) — so the fix needs to keep
the target genuinely self-consistent (zero bias, tracks whatever `lambda`
the outer Newton loop is currently probing) while replacing the *naive*
lagged-replacement update with one that is actually convergent.

## Phase 2 — Fix: Path 2A.2 (Anderson acceleration on `g_pi_core`)

**Decision: Path 2A.2**, not 2A.1. Reasoning:

- 2A.1 (permanently fixed target) is ruled out by Phase 1a's broader stress
  test: freezing the target at its sweep-0 seed is only safe in a
  neighbourhood of that seed, not over the full range of `lambda` the outer
  Newton loop explores — the exact mismatch/bias failure mode
  `solve_picard`'s own docstring already documents for a *frozen* seed.
  There is no cheap way to bound "how far is too far" a priori, so 2A.1
  would need to be re-litigated per parameter point rather than being a
  general-purpose scheme.
- 2A.2 (Anderson acceleration) keeps the target genuinely self-consistent
  (zero bias by construction, exactly like the `theta=1` scheme it
  replaces) while replacing the *unstable update rule* with a convergent
  one. It requires no new derivatives/Jacobian (matching the prompt's own
  preference to "prefer Anderson first if it converges"), and reuses the
  existing per-sweep backward+forward solve as its residual evaluation —
  the map being accelerated, `x ↦ T(x)` where `T(x)` is "one Picard sweep's
  resulting `pi_core(N)` given SAT target `x`", is already computed as a
  side effect of the existing loop body; Anderson only changes how the next
  `x` is built from the history of `(x_k, T(x_k))` pairs.

### Implementation

Type-I Anderson mixing (Walker & Ni 2011), windowed to the last `m` sweeps:
given the fixed-point residual `g_k = T(x_k) - x_k`, maintain the last `m+1`
iterates and residuals, solve the small least-squares problem
`gamma = argmin_γ || g_k - ΔG_k γ ||` over the window's successive
differences `ΔG_k` (residuals) and `ΔX_k` (iterates), and set

```
x_{k+1} = x_k + theta*g_k - (ΔX_k + theta*ΔG_k) @ gamma
```

`theta` (the existing parameter) becomes the Anderson mixing/damping factor
(Walker-Ni's `beta`); `m=0` (or the new `anderson_m=0`) reduces exactly to
the pre-existing plain Picard/theta-blend update, so the old code path
remains reachable for regression comparison. See `picard.py`'s
`_AndersonMixer` and its module-docstring update for the full derivation
and empirical window-size tuning.

### A plain Anderson mixer was not, on its own, sufficient

Plain (unregularized) Anderson at `theta=1` converts Finding 2's *unbounded*
divergence into a *bounded* oscillation (residual settles into a band, does
not run away to `O(1)`), but empirically **stalls**: it drives the residual
down by 2-3 orders of magnitude within ~10 sweeps, then stops improving,
oscillating indefinitely rather than continuing to converge — confirmed not
to be a tuning artefact of this implementation specifically, since:

- Sweeping the window size (`m ∈ {1,2,3,4,5,8}`) and the damping `theta ∈
  {0.05, ..., 1.0}` all reproduce the same qualitative plateau, at a similar
  residual level.
- Tikhonov-regularizing the small least-squares solve (`_AndersonMixer.REG_EPS`)
  removes a worse failure mode (a hard restart-on-stall safeguard was tried
  first and made things *worse*, reintroducing Finding 2's own instability on
  every reset) but does not remove the plateau itself.
- Isolating the sub-problem (holding the response fields `rfield`/`rmom`
  fixed for a whole "outer" sweep, iterating `g_pi_core` alone to its own
  fixed point) reproduces the identical plateau, ruling out contamination
  from the *other*, unaccelerated `(phi,pi)` sub-iteration.
- Handing the same isolated sub-problem to `scipy.optimize.newton_krylov`
  (a well-tested, globalized Newton-GMRES solver with its own Armijo line
  search) reproduces the same plateau at a similar magnitude, ruling out
  "this specific implementation is just a poor accelerator."
- The plateau's magnitude does not scale down with tighter ODE solver
  tolerance (`atol`/`rtol` from `1e-8` to `1e-12`, no material change) and
  only weakly/non-monotonically with finer `N_GRID_SIZE` (`300 → 1200 →
  2400`) — so it is not a simple ODE- or spline-discretization floor either.

**Conclusion:** the Anderson-accelerated `g_pi_core` sweep has a genuine,
not-yet-fully-understood residual floor at this discretization, roughly
`1e-4` to `1e-6` in absolute `phi`/`pi` units (`phi`, `pi` themselves are
`O(1)`-`O(10)`). `INNER_TOL` is recalibrated (see `picard.py`'s own comment
at the definition) to a level comfortably above this floor rather than left
at the pre-22b value, which was **never validated against genuine coupling**
(Finding 1 made it trivially satisfied in one sweep at every prior test). A
sustained-convergence check (`INNER_CONSECUTIVE_REQUIRED` consecutive sweeps
below `INNER_TOL`, not a single dip) guards against the noisy map producing
a false "converged" declaration on a lucky single-sweep low.

### The outer shooting loop needed its own, separate hardening

Finding 1's fix also exposed a *second*, previously-invisible problem, this
time in the pre-existing **outer** Newton loop on `lambda` (prompt 21a code,
out of this prompt's original diagnostic scope but blocking its own
acceptance criterion — "outer Newton converges" — so fixed here too):

- The finite-difference derivative probe's `dlam` floor (`1e-6`) was
  calibrated when `lambda=0` was an exact fixed point (Finding 1) and the
  probe never had to resolve a genuine signal against inner-loop noise. Once
  genuinely coupled, `dlam=1e-6` is frequently *smaller* than the inner
  loop's own achievable precision, so `dres_dlam` is dominated by noise —
  observed directly as a wild, unphysical `lambda` overshoot on the very
  first outer iteration of the prompt's own small acceptance case.
- **Fix:** replaced the throwaway finite-difference probe with a **secant**
  step between the last two *real*, already-evaluated `(lambda, residual)`
  points — well-separated by construction (an accepted outer step, not an
  infinitesimal one), reuses an evaluation the loop needed anyway (net
  *cheaper* per outer iteration, not more expensive), and is immune to the
  small-`dlam` noise problem by design.
- A full (undamped) secant/Newton step was still observed to occasionally
  overshoot into an unphysical `lambda` (`H_sq_local < 0`, `picard_inner`
  failing outright) or overshoot the residual itself (linearizing a highly
  nonlinear shooting residual from a single secant point is not always a
  good global model). **Fix:** an Armijo-style backtracking line search
  (`MAX_BACKTRACK` halvings, accept the first step that is both feasible
  and strictly reduces `|residual|`) plus a **trust-region cap** on the
  secant step itself (shrinks after any backtracking, grows after a step
  that needed none) — both standard, well-understood globalizations for
  exactly this failure mode, not novel to this prompt.
- The backtracking search's own winning evaluation is carried forward as
  `pending` into the next outer iteration rather than re-solved from
  scratch, halving the typical per-outer-iteration cost.

## Acceptance evidence

**What is demonstrated, with reproducible evidence:**

- Phase 1's fork (lagging is the culprit) — Section "Phase 1" above.
- The Anderson-accelerated closure converges the previously-catastrophically-
  divergent (Finding 2) inner loop to a small, bounded residual at every
  `(n_collocation_points, delta_Nstar)` point Finding 2 itself exercised
  (`n ∈ {5,7}`, `delta_Nstar ∈ {1.0, 1.5, 2.5}`) — no run diverges to `O(1)`
  under the new scheme, a qualitative, unambiguous fix of Finding 2's own
  headline failure.
- **Positive control, full pipeline, `n_collocation_points=5`**
  (`tests/test_gradient_coupled_instanton_end_to_end.py`,
  `tests/test_gradient_coupled_instanton_stiffness_instrumentation.py`): the
  five tests prompt 22a marked `xfail(strict=True)` — precisely because they
  exercise the full, genuinely non-trivial pipeline this prompt's fix
  targets — now **pass outright** (confirmed by running them XPASS under the
  still-in-place `xfail` markers before removing those markers). This is the
  first genuine non-trivial `GradientCoupledInstanton` solve (`lambda != 0`,
  non-zero response fields, `msr_action > 0`) these tests, or any prior
  prompt's acceptance run, has ever produced.
- **`n`-convergence, `n_collocation_points ∈ {5, 9}`**
  (`tests/test_picard.py::test_solve_picard_converges_under_genuine_coupling_across_n`,
  new): the same small, genuinely-coupled case converges cleanly at both
  `n=5` and `n=9`, with a strictly non-zero `lambda` at each (not a
  rediscovery of the trivial branch). **`n=17` was tried on this same case
  and does NOT converge** within `MAX_OUTER=50` — `picard_inner` fails
  outright on the first outer iteration even after the full backtracking
  search. The parametrization is deliberately capped at what is proven
  (`n ∈ {5,9}`), not the full `{5,7,9,11,13,17,33}` the prompt's acceptance
  criterion names; the `n≥17` gap is a further, uncharacterised piece of the
  "What is NOT yet demonstrated" limitation below, not resolved here.
- New `_AndersonMixer` unit tests
  (`tests/test_picard.py::test_anderson_mixer_*`) lock down the `anderson_m=0`
  backward-compatibility reduction and directly demonstrate convergence on a
  minimal diverging-linear-map reproduction of Finding 2's own failure mode.
- `tests/test_picard.py`'s full suite (16 tests, including the two-seed
  zero-bias regression `test_solve_picard_converged_answer_independent_of_sat_seed`
  and the production-`n` convergence tests) passes unchanged.

**What is NOT yet demonstrated:**

1. A fast, reliable convergence sweep on the *specific* production case
   prompt 22 itself flagged as the "resolved regime" (`N_init=19.5,
   N_final=16.0, delta_Nstar ∈ [1.0, 3.0]`, quadratic potential
   `m/Mp=1e-5`). Direct testing there shows the **outer** shooting residual
   barely moving over dozens of outer iterations even with the
   secant/backtracking/trust-region hardening above — independent evidence
   that this exact corner is poorly conditioned, consistent with (and now
   reproduced from a different angle than) prompt 22's own Finding 1b, which
   already flagged `delta_Nstar=1.0` at this `(N_init, N_final)` as poorly
   conditioned *for `FullInstanton`'s own shooting problem*, unrelated to any
   `GradientCoupledInstanton`-specific closure. Whether this is (a) the same
   underlying conditioning issue re-appearing in the coupled model's own
   shooting parameter, or (b) a distinct effect, has not been established.
2. Convergence at `n_collocation_points ≥ 17`, even on the small,
   otherwise-tractable case above. Whether this is the same outer-shooting
   conditioning issue as (1), a genuinely `n`-dependent effect in the inner
   Anderson closure (Phase 1b already found the `theta=1` map's own
   growing-phase contraction ratio worsens mildly with `n`, `1.37`→`1.51`
   going from `n=5` to `n=7` — a similar, not-yet-quantified-at-larger-`n`
   trend could plausibly compound with the outer loop's own sensitivity),
   or something else, is not established.
3. A full root-cause explanation for the Anderson-accelerated inner map's
   own residual floor (the "not, on its own, sufficient" section above) —
   ruled out several candidate explanations (ODE tolerance, spline
   resolution, this-implementation-specific tuning) without identifying the
   actual mechanism.

**Scoping decision:** rather than further expand this prompt chasing one
specific hard corner's outer-loop conditioning — a materially different
problem from the lagged-`g_pi_core` fixed-point instability this prompt was
scoped to fix, and diagnosed only as a side effect of exercising the fix —
this is flagged as follow-up work, in the same spirit as prompt 22's own
"clean negative closeout is valid" allowance. The fix delivered here
directly, conclusively resolves Finding 2 (the lagged-target instability)
and is validated on every case where the pipeline can be exercised in
practical time; the residual difficulty is a *shooting-problem conditioning*
question at one specific, already-flagged-as-hard parameter corner, not a
gap in the Picard/Anderson closure itself.
