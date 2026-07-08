# Prompt 24 (revised), Phase A — go/no-go deep-dive: results

**Verdict: NO.** No non-trivial (`λ≠0`) GradientCoupledInstanton solve converges
anywhere across `m/Mp ∈ {1e-2, 1e-3, 1e-4, 1e-5}` at
`(δN★=1.0, n=5, α=0.1, N_init=19.5, N_final=16.0)`, even with a generous
(1–2 hour) per-point wall-clock budget. This is the campaign's primary
result; see `.documents/gradient-coupled-instanton/24-phase0-baseline.md`
for the pre-existing record this supersedes.

## Method

Run through the real `main.py`/`ShardedPool` datastore pipeline (not a
bypass script): `--targets homogeneous gradient --stop-after full-instanton`
so each point gets a real, database-stored `FullInstanton` seed (`n=5`
`GradientCoupledInstanton`, `α=0.1`, `δN★=1.0`, same `N_init`/`N_final` as
the base grid). `--gci-wallclock-budget-seconds` (this prompt's own
prerequisite safeguard) set the per-point budget; every point is classified
via the new `bailout_tag`/`bailout_reason` diagnostics. Two runs:

1. **Main sweep** (`out-gci-convergence-campaign/phase_a.sqlite`): all four
   `m` values, 3600 s budget each, 4-way Ray-parallel (6 CPUs available).
2. **Follow-up** (`out-gci-convergence-campaign/phase_a_followup.sqlite`):
   `m=1e-2` alone, re-run in isolation at double the budget (7200 s), to
   resolve whether its "descending" tag from the main sweep meant genuine
   convergent-but-slow progress or a plateau not yet revealed.

One incidental pipeline bug was hit and worked around (not fixed, out of
scope): `--no-store-values` combined with `--targets homogeneous gradient`
crashes the gradient branch's `FullInstanton` seed fetch
(`Datastore/SQL/ObjectFactories/FullInstanton.py`'s `build()` raises on a
scalars-only-stored row instead of degrading gracefully, because
`_run_gradient_branch`'s Pass-0 fetch doesn't pass `_do_not_populate`). Both
runs here used full-fidelity `FullInstanton` storage instead.

## Results

| `m/Mp` | `compute_time` | outer iterations | final `|residual|` | `bailout_tag` | `bailout_reason` |
|---|---|---|---|---|---|
| 1e-2 (3600s budget) | 3603.5 s | 4 / 50 | 0.0584 | **descending** | wallclock_budget |
| 1e-2 (7200s budget, isolated re-run) | 7224.9 s | 4 / 50 | 0.0584 | **descending** | wallclock_budget |
| 1e-3 | 1358 s | 50 / 50 | 0.0556 | **floored** | max_outer_exhausted |
| 1e-4 | 390 s | 50 / 50 | 0.2361 | **floored** | max_outer_exhausted |
| 1e-5 | 315 s | 50 / 50 | 0.2454 | **floored** | max_outer_exhausted |

(`OUTER_TOL = max(atol·1e6, 1e-2) = 1e-2` — no point got within an order of
magnitude of tolerance.)

## The `m=1e-2` doubled-budget result is the most important single data point

Doubling the wall-clock budget for `m=1e-2` from 3600 s to 7200 s reproduced
**bit-for-bit identical** internals: same `outer_iterations=4`, same
`final_residual=0.05840954869663317`, same `outer_residual_history`
(`[0.2455, 0.2455, 0.0956, 0.0584, 0.0584]`), same `total_ode_solves=87`,
same `rk45_forward_total_steps=152000`, same
`picard_iterations_per_outer=[4,1,1,1,1,1,3,2,2,6,8,10,4,0]`. Only the
measured wall-clock (`compute_time`: 3603.5 s → 7224.9 s, almost exactly 2×)
and the derived `mean_time_per_picard_iteration` (81.9 s → 164.2 s) changed.

Since this is a fully deterministic computation (no randomness anywhere in
`solve_picard`), identical step/iteration counts under a doubled budget can
only mean the SAME fixed sequence of ~44 Picard sweeps / ~163,500 combined
RK45 steps — the Armijo-backtracking cascade away from the
`FullInstanton`-bootstrapped `λ≈1900.4` seed (probed at `1900.4, 950.2,
475.1, 237.6, 118.8, -75, -37.5, -18.75, -24.75`, each failing outright) —
took ~2× longer in wall-clock terms the second time, on the same code, same
inputs, same machine. `pmset -g therm` showed no thermal-throttling
warnings, but `uptime` showed a load average of ~700 on this development
laptop (777 processes, including OrbStack, several browser/webkit
processes, and multiple concurrent Claude sessions) — genuine CPU
contention on a shared personal machine, not a dedicated cluster, is the
plausible explanation. **This is a real methodological caveat for any
wall-clock-budgeted campaign run here**, and it directly undercuts treating
`m=1e-2`'s "descending" tag as evidence that more budget would eventually
converge: the *same* fixed 44-sweep/163k-step block consumed the *entire*
budget both times, with no headroom left to show whether outer iteration 5
is reachable at all, let alone iteration 50. There is no evidence from
either run that additional wall-clock crosses `OUTER_TOL`.

## Interpreting the failure modes

- **`m ∈ {1e-3, 1e-4, 1e-5}`: floored, not budget-limited.** All three
  finished in well under 40% of their 3600 s budget (315–1358 s). The outer
  shooting-loop residual genuinely plateaus — for `m=1e-3` it falls from
  0.245 to ~0.056 over the first ~20 outer iterations, then *oscillates* in
  a tight `0.0556–0.0561` band for the remaining ~90 evaluate() calls; for
  `m=1e-4`/`1e-5` it barely moves at all (0.2455→0.236, 0.2455→0.2454).
  `newton_fallback_count=2` throughout — the secant/trust-region search is
  not stalling on convergence *speed*, it is converging to a residual
  fixed point that is not the target. More `MAX_OUTER` would not help here;
  this is the "floored" classification working as designed, distinct from
  both a budget problem and an outright `H_sq<0`/step-death structural
  failure. This is a *new* failure mode beyond Phase 0's two-category
  (slow-vs-blown-up) framing — a genuine third category the classification
  scheme added by this prompt's prerequisite was built to distinguish.
- **`m=1e-2`: dominated by an expensive large-`λ` Armijo cascade, not
  simply slow.** `λ_FI=1900.4` (from a real, converged, database-stored
  `FullInstanton`, `msr_action=214.71`) is nowhere near the "astronomic"
  `λ~1e9` regime Phase 0's Finding 5 attributed the response-sector
  step-death problem to — yet the very first bootstrap-aimed outer-loop
  probe already triggers a 100k+-RK45-step cascade across its Armijo
  backtracking. This suggests the astronomic-`λ` response-sector cost onset
  (prompt 22c Finding 4 / prompt 23) is not a sharp threshold near `1e9`; it
  is already a serious cost driver at `λ~O(1000)`, well inside what Phase 0
  called "moderate `λ`, should be tractable." That expectation is not borne
  out here.

## Answering Phase A's own questions

- **Does the mild-`m` end converge?** No. `m=1e-2` is the mildest mass
  tried and does not converge; worse, it is *not demonstrably*
  convergent-but-slow either (see the doubled-budget result above) — the
  honest classification is "descending across the 4 outer iterations
  actually completed, with no evidence about what comes after." Per the
  prompt's own framing, this is the deeper finding: even the case expected
  to be most tractable does not produce a converged non-trivial solve.
- **Where, and how, does it break as `m` shrinks?** There is no clean
  "converges up to `m≈X`, then breaks" boundary in this range — nothing in
  `{1e-2,...,1e-5}` converges. The *mechanism* changes with `m`: at
  `m≤1e-3` it is a genuine outer-residual floor (structural-ish, not a
  budget problem); at `m=1e-2` it is an extremely expensive per-outer-iteration
  cost driven by the bootstrap seed's own `λ`, with too few completed
  iterations (4 of 50) to characterize the asymptotic trend at all.
- **Sanity-check against FullInstanton where converged:** N/A — no point
  converged, so there is no core trajectory/`λ`/`msr_action` to compare.
  (For reference, the four `FullInstanton` seeds themselves all converged
  cleanly and quickly: `λ_FI` = 1900.4 (`m=1e-2`), and larger — not
  extracted here — for the smaller masses, consistent with Phase 0's
  `λ_FI≈1.9e9–4.1e9` figure at the production `δN★=0.1` point; `δN★=1.0`
  here is a different, larger point on the `δN★` axis, so these are not
  directly the same `λ_FI` values Phase 0 quoted.)

## Recommendation for Phase B / Phase C

Per this prompt's own acceptance criteria: *"Phase B map produced if Phase A
found a region worth mapping; otherwise Phase B is descoped and the finding
is the Phase-A boundary."* Phase A found no converged region anywhere in the
four points tried. Phase C similarly requires converged points to check
FullInstanton-consistency of, which do not exist here (the only converged
non-trivial GCI solve anywhere in the project's history remains the tiny
`N_total=0.15` toy fixture from Phase 0's baseline).

**Recommendation: descope Phase B/C as originally scoped (mapping/consistency
of a converged region), and treat this Phase A result as the campaign's
answer.** A narrower, cheap follow-up — e.g. a short-cap pilot at smaller
`δN★` (closer to the `δN★=0.1` degenerate-but-trivial branch) or smaller `n`,
to see whether *any* corner of the `(m, δN★, n, α)` grid produces a
non-trivial converged solve at all — would be a reasonable, small next step
if the project wants one, but that is a different question than the
originally-scoped Phase B/C and should be scoped as its own follow-on rather
than run silently under this prompt's structure.
