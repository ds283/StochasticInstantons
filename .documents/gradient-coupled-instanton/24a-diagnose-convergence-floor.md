# Prompt 24a — diagnosing the delta_Nstar=1 floor: results

Prompt: `.prompts/gradient-coupled-instanton/24a-diagnose-convergence-floor.md`.
Diagnostic-only campaign: **no production code was modified**. All four
diagnostics run through a standalone harness,
`out-gradient-coupled-stiffness/scripts/diagnose_24a_convergence_floor.py`
(same Ray/Datastore-bypassing pattern as `validation_22_resolved_regime.py`
and `explore_onion_stiffness.py`), calling `solve_picard`'s real internals
directly — the only "trick" used is monkeypatching
`picard_module.solve_shooting` so a `lambda` sweep or a `commit()`-capturing
wrapper can observe/control the outer loop without touching a single line of
`picard.py`, `response_rhs.py`, or `forward_rhs.py`. Every number below is
reproducible from the JSON records in
`out-gradient-coupled-stiffness/scripts/diagnose_24a_output/`.

## Executive summary

**Verdict: one/two fixes away at small `delta_Nstar`, not a wall.** The
project's **first non-trivial (`lambda != 0`, `msr_action > 0`) converged GCI
solve at production scale** was produced in this campaign, at
`m=1e-2, delta_Nstar in {0.3, 0.5, 0.7}` (Diagnostic 4) — the campaign's
primary deliverable. The `delta_Nstar=1.0` floor Phase A found is **not** a
single wall; it is the compound effect of (at least) two distinct,
independently-confirmed mechanisms, neither of which is a Part-B defect:

- **(a) Fixed-target bias — confirmed, and shown curable at `m=1e-3`**
  (Diagnostic 3a): perturbing the fixed `g_pi_core` target by a small,
  physically-plausible `delta=+0.03` moves the `delta_Nstar=1.0` floor from
  `0.0565` (Phase A's own `0.0556`) to `0.00325` — **fully converged**, below
  `OUTER_TOL=0.01`. The *naive* two-pass self-consistency prototype meant to
  find such a correction automatically (Diagnostic 3b) **diverges** instead
  (`0.0565 -> 0.0821 -> 0.4176` over 3 passes) — a clean negative, not a
  contradiction: it reproduces prompt 22's own abandoned undamped-lagged-target
  divergence mechanism, because full target replacement each pass is exactly
  that undamped scheme. A *damped* (Anderson-style) two-pass variant is the
  actual follow-on this suggests, not the one prototyped here.
- **(c)/(d) A narrow feasible `lambda` corridor near 0, orders of magnitude
  inside `lambda_FI`, with the true root off to one (mass-dependent) side —
  confirmed at all four masses** (Diagnostic 1): `evaluate(lambda)` is only
  ever informative (converges, moves the residual) within roughly
  `1e-3` to `1e-2` of `lambda_FI`; just outside that, every mass diverges or
  blows up (`H_sq<0`) outright. Diagnostic 4's own converged answers land
  exactly in this predicted corridor (`lambda ≈ -1 to -2%` of `lambda_FI`,
  negative sign), cross-validating Diagnostic 1's read from an independent
  direction.
- **(b) Part-B lambda-rescaling — ruled out** (Diagnostic 2): confirmed
  correct end-to-end in the real solve path, not just the isolated unit test.

`delta_Nstar=1.0` itself was not re-tested for convergence in this campaign
(out of scope — Diagnostic 4 walks smaller `delta_Nstar` only), so the
precise mechanism for *that exact point* is not independently re-confirmed
here beyond Phase A's own record; what this campaign shows is that the
*general* disease (narrow corridor + fixed-target bias) is real, mass-general,
and — at nearby, smaller `delta_Nstar` — not fatal.

## Diagnostic 1 — `evaluate(lambda)` sweep at each mass (no outer root-find)

Method: for each `m in {1e-2, 1e-3, 1e-4, 1e-5}` at
`(delta_Nstar=1.0, n=5, alpha=0.1, N_init=19.5, N_final=16.0)`, fetch the real
FullInstanton seed (`lambda_FI`), then call `solve_picard`'s own
`evaluate(lambda)` closure directly at a dozen chosen `lambda` values
bracketing 0 and `lambda_FI` — each point gets its **own** `solve_picard` call
(hence its own wall-clock deadline), so one expensive point cannot starve the
rest of the sweep. `m=1e-2` used a reduced 6-point grid plus a targeted
5-point supplement at finer fractions (its per-sweep cost is high enough —
see below — that the full 12-point grid was not "cheap").

### Result: the same qualitative structure at every mass

| `m` | `lambda_FI` | last successful `lambda`/`lambda_FI` | first diverging | first blown-up |
|---|---|---|---|---|
| 1e-2  | 1900.4     | `1.0e-3` (residual `-0.283`, moving *away* from 0) | `1.0e-2` | `3.0e-2` |
| 1e-3  | 190043     | `1.0e-4` (residual `-0.249`)      | `1.0e-2` | `0.1` |
| 1e-4  | 1.900e7    | `1.0e-4` (residual `-0.249`)      | `1.0e-2` | `0.1` |
| 1e-5  | 1.900e9    | `1.0e-4` (residual `-0.249`)      | `1.0e-2` | `0.1` |

(`residual` at `lambda=0`, the exact trivial fixed point, is `-0.2455` at
every mass — an exact cross-check that the harness reproduces the production
trivial branch. "diverging" = the `DIVERGENCE_GROWTH_PATIENCE` early-exit;
"blown-up" = `H_sq<0`/ODE failure on sweep 1, i.e. immediate.)

**The feasible corridor is 2-3 orders of magnitude narrower than `lambda_FI`
itself, at every mass tried.** Beyond `~1%` of `lambda_FI`, the Picard forward
pass cannot tolerate the resulting noise-sourcing feedback without `H_sq<0`
(classification (c), inner-solve/response-sector failure at fixed `lambda`) —
this is **not** a root-finding conditioning problem in the usual sense
(bracket too wide, wrong step size); it is a genuine feasibility wall. Inside
the corridor, `m=1e-3/1e-4/1e-5` show `evaluate(lambda)` barely moving
(`-0.2455 -> -0.249`, `~2%` of the residual scale) — consistent with Phase
A's own "flat" read for `m=1e-4/1e-5` — but **`m=1e-2` shows more movement
or steeper movement (`-0.2455 -> -0.283` at just `0.1%` of `lambda_FI`,
already exceeding `OUTER_TOL` in magnitude) and, critically, the wrong
sign of movement**: the residual moves *away* from zero as `lambda`
increases through small positive values. This is the first direct evidence
that **`m=1e-2`'s true root sits on the negative-`lambda` side** —
independently confirmed by Diagnostic 4 below.

Negative-`lambda` evaluations are markedly more expensive at every mass
(`90-240s` vs `<2s` for the equivalent positive point) — the harness's
per-point wall-clock budget was hit outright at `m=1e-2, lambda=-190`
(`fraction -0.1`, `240s` budget) and `m=1e-3/1e-4/1e-5, lambda=-0.1*lambda_FI`
(`90s` budget each) — so the negative corridor's own fine structure (as
opposed to its existence) is **not resolved** by this campaign; see
"Recommendation for `m=1e-2`" below.

**This reframes Phase A's own "m=1e-3 moves-then-floors vs m=1e-4/1e-5 flat"
distinction.** The underlying reachability structure (a narrow near-zero
corridor) is the *same* at every mass; Phase A's own outer loop (secant +
`stall_growth=1.5` escalation from `lam0=0`) simply explored different
amounts of that corridor before getting stuck, depending on how its
particular escalation path interacted with the corridor's boundary — not
because the physics differs qualitatively between `m=1e-3` and `m=1e-4/1e-5`.

## Diagnostic 2 — Part-B (lambda-rescaling) end-to-end validation

**Confirmed working correctly, in the real `solve_picard` path (not the
isolated unit test), at every mass where a nonzero-`lambda` evaluation
succeeded.** Reused Diagnostic 1's own successful evaluations (no separate
run needed — "cheap" per the prompt's own framing):

| `m` | `lambda` tested | `max\|rfield\|` (physical) | `max\|rfield\|/lambda`  (`~= max\|r_tilde\|`) |
|---|---|---|---|
| 1e-3 | 19.00   | 173984     | 9155.01 |
| 1e-4 | 1900.43 | 1.7398e7   | 9155.01 |
| 1e-5 | 190043  | 1.7398e9   | 9155.01 |

The ratio is constant to 6 significant figures across three masses spanning
**5 orders of magnitude in absolute `lambda`** — direct empirical
confirmation that `r = lambda * r_tilde` holds exactly end-to-end in
production code, not merely in Prompt 23's own isolated unit tests. No
`NaN`/`Inf`/collapse anywhere tested, including at `m=1e-5, lambda=1.9e5`
where the physical `rfield_max=1.74e9` is itself astronomic. **Part-B is
ruled out as a contributor to the `delta_Nstar=1` floor** — classification
(b) does not apply at any mass tested.

(`m=1e-2` has no entry: its only successful nonzero-`lambda` evaluations in
the main sweep were at `lambda=0` exactly, where `rfield_max=0` trivially;
the supplement's two successful points, `1739.8` and `17238.4` at
`lambda=0.19` and `1.90`, give ratios `9155.0` and `9070.8` respectively —
consistent with the same constant (the second point's small `~1%` departure
is expected: it is close to where the corridor starts breaking down, per
this same diagnostic's own next row, `lambda=19.0`, already diverging), just
computed separately since the supplement was a later, targeted run.)

## Diagnostic 3a — is the `m=1e-3` floor the fixed-target bias?

Method: perturb the fixed `g_pi_core` target (FullInstanton's own `phi2(N)`)
by a uniform additive `delta`, re-run `solve_picard` at `m=1e-3,
delta_Nstar=1.0` with `MAX_OUTER` capped to 20 (Phase A's own floor
established within `~20` outer iterations, so this reaches the plateau
without paying for the full 50-iteration oscillation tail).

| `delta` | `final_residual` | `bailout_tag` |
|---|---|---|
| `-0.01` | `0.0867` | floored (worse) |
| `0` (baseline) | `0.0565` | descending (matches Phase A's `0.0556` closely) |
| `+0.01` | `0.0295` | floored (better) |
| `+0.03` | **`0.00325`** | **converged** |

**Clean, monotonic bias-tracking.** The floor moves systematically and
monotonically with the target perturbation, crossing below `OUTER_TOL=0.01`
between `delta=0.01` and `delta=0.03`. This directly confirms classification
(a): at `m=1e-3, delta_Nstar=1.0`, the fixed-target bias is large enough on
its own to be the difference between "floored at `~5x` tolerance" and
"converged" — a concrete, actionable "one small, well-chosen correction away"
result, not merely a plausible mechanism.

## Diagnostic 3b — does naive two-pass self-consistency find that correction?

Prototype (explicitly out of scope to productionise — see the prompt's own
"out of scope"): re-seed the fixed target, each pass, from the *previous*
pass's own last-committed core `pi(N)` trajectory (captured via a thin
`commit()`-wrapping monkeypatch of `solve_shooting`, since a non-convergent
`solve_picard` call discards its grids in `_failure_result` — this required
one fix to the harness itself, not production code). `MAX_OUTER=20` per pass,
same as 3a.

| pass | `final_residual` | `bailout_tag` |
|---|---|---|
| 0 | `0.0565` | descending (== 3a's own baseline) |
| 1 | `0.0821` | floored (**worse**) |
| 2 | `0.4176` | floored (**much worse**) |

**Clean negative — diverges monotonically, not a contradiction of 3a.** The
naive prototype is an *undamped, full-replacement* update rule — exactly
prompt 22's own abandoned `theta=1` lagged-target scheme
(`.documents/gradient-coupled-instanton/22c-fullinstanton-seed-fixed-target.md`),
just applied once per bounded outer-loop sub-solve instead of once per Picard
sweep. It reproduces that scheme's own divergence mechanism at this coarser
granularity. **This does not contradict 3a's own finding** that the
underlying bias is real and a *small*, controlled correction cures it — it
shows that *finding* the right correction by naive full self-consistency
overshoots badly. A production follow-on (out of scope here) would need
Anderson-style damping (à la the abandoned `_AndersonMixer`, or a fresh
under-relaxed blend) between the old and new target, not full replacement.

## Diagnostic 4 — first non-trivial convergence: the `delta_Nstar` boundary

Method: real full outer shooting (unmodified `solve_shooting`, not the
Diagnostic-1 sweep monkeypatch) at `m=1e-2, n=5, alpha=0.1`, walking
`delta_Nstar in {0.2, 0.3, 0.5, 0.7}`, `600s` wall-clock budget per point.

| `delta_Nstar` | `lambda_FI` | converged | `final_lambda` | `msr_action` | `lambda`/`lambda_FI` |
|---|---|---|---|---|---|
| 0.2 | 457.06  | **No** (floored, residual `0.0487`) | — | — | — |
| 0.3 | 668.49  | **Yes** | `-14.504` | `429.95` | `-2.17%` |
| 0.5 | 1061.42 | **Yes** | `-15.472` | `1417.29` | `-1.46%` |
| 0.7 | 1419.24 | **Yes** | `-15.628` | `4216.43` | `-1.10%` |

**The project's first non-trivial (`lambda != 0`, `msr_action > 0`) converged
GCI solve at production scale**, at three consecutive `delta_Nstar` points.
`msr_action` grows with `delta_Nstar` as physically expected (longer,
excess-duration transitions cost more action). `delta_Nstar=0.2` does *not*
converge within budget — floored at `0.0487`, close to (same order as) the
Phase-A-family floors seen elsewhere, suggesting the same mechanism (narrow
corridor / bias) rather than a different disease at the small-`delta_Nstar`
end; not independently diagnosed further here (out of scope for this
prompt's Diagnostic 4, which asks only for the boundary).

**Cross-validates Diagnostic 1 directly.** Every converged `lambda` is
**negative** and sits at `1-2%` of `lambda_FI` in magnitude — exactly the
narrow corridor scale, on exactly the sign, that Diagnostic 1 predicted from
`m=1e-2`'s own residual-direction evidence (positive `lambda` moving the
residual the wrong way). Two independent diagnostics (a fixed-`lambda`
sweep with no root-finding, and a real secant/Armijo outer loop) landed on
the same physical picture from different directions.

## Classification and verdict, per mass

| `m` | Mechanism(s) confirmed | Verdict |
|---|---|---|
| 1e-2 | (c)/(d): narrow corridor, root on negative side (Diagnostics 1 & 4, directly cross-validated). No independent bias test run at this mass. | **One fix away, and partly already fixed**: `delta_Nstar in {0.3,0.5,0.7}` already converge with the *unmodified* production algorithm — no fix needed there. `delta_Nstar=1.0` itself is closer to (or past) the edge of the corridor; likely curable by a smarter bootstrap that aims near `-1..-2%` of `lambda_FI` instead of `+lambda_FI` (see recommendation below), not by any closure change. |
| 1e-3 | (a) fixed-target bias, confirmed and shown curable by a small correction (Diagnostic 3a); (c)/(d) narrow corridor also present (Diagnostic 1). (b) ruled out. | **One (small, well-chosen) fix away** — demonstrated directly. The gap is a *general* method for finding the right correction (3b's naive attempt diverges), not the existence of one. |
| 1e-4 | (c)/(d) narrow corridor, near-flat residual within it (Diagnostic 1). (b) ruled out. Bias (a) **not independently tested at this mass** — extrapolating 1e-3's result would be a guess, not evidence. | **Evidence incomplete.** The corridor finding alone does not distinguish "one fix away" from "genuinely blocked" here; flagged as a gap, not resolved. |
| 1e-5 | Same as 1e-4 — corridor confirmed, near-flat residual, bias untested. | **Evidence incomplete**, same caveat as 1e-4. |

## Recommendation for `m=1e-2` budget-limitedness (Phase A's own open question)

Phase A's own acceptance criterion ("re-test `m=1e-2` on an uncontended
machine *if* Diagnostic 1 shows `evaluate(lambda)` is well-posed") is
answered **conditionally**: `evaluate(lambda)` *is* informative — genuinely
well-posed — but **only within the narrow negative corridor now roughly
located** (`~-1%` to `-2%` of `lambda_FI`, i.e. absolute `lambda` of roughly
`-19` to `-38` at `delta_Nstar=1.0`'s own `lambda_FI=1900.4`), not anywhere
near `lambda_FI` itself where Phase A's own bootstrap aimed. **Any future
wall-clock campaign at `m=1e-2` should not spend budget re-running the
existing bootstrap-toward-`lambda_FI` escalation** (Phase A's own expensive
Armijo cascade at `lambda~1900`, confirmed here to be on the *wrong side and
the wrong scale* of the true root) — it should instead seed the outer loop's
bootstrap aim at a small *negative* multiple of `lambda_FI` (e.g.
`bootstrap_target = -0.015 * lambda_FI`, informed directly by Diagnostic 4's
own converged answers at nearby `delta_Nstar`) and verify whether
`delta_Nstar=1.0` itself converges under that much better-informed aim. This
machine's CPU contention (load average `12-58` on 10 cores throughout this
session, matching Phase A's own caveat) still applies to any absolute
wall-clock numbers reported here, but the qualitative corridor-location
finding is deterministic-internals-based (sweep counts, convergence status,
sign of residual movement) and machine-independent, per the prompt's own
framing.

## What this campaign does NOT establish (out of scope / gaps)

- **`delta_Nstar=1.0` itself was not re-tested for convergence** under any
  corrected bootstrap or target — Diagnostic 4 walks smaller `delta_Nstar`
  only, per its own scope. Whether the informed-bootstrap recommendation
  above actually converges `delta_Nstar=1.0` is untested.
- **Diagnostics 3a/3b (fixed-target bias, two-pass prototype) were run only
  at `m=1e-3`.** Whether the same bias-tracking/divergence pattern holds at
  `m=1e-4/1e-5` is not established — flagged as a genuine evidence gap in the
  classification table above, not assumed by extrapolation.
- **The negative-`lambda` corridor's fine structure is not resolved** at any
  mass — only its existence and rough order of magnitude (via Diagnostic 1's
  coarse probes and Diagnostic 4's converged answers). A finer negative-side
  sweep (e.g. logarithmically spaced between `-1e-3` and `-0.1` of
  `lambda_FI`) would sharpen this but was not run here (would not be "cheap"
  at `m=1e-2`'s own per-point cost).
- **A damped (Anderson-style) two-pass production implementation** is
  explicitly out of scope per the prompt (3b prototypes and tests whether
  the naive form is warranted — it is not; a damped follow-on is a separate,
  future decision).
- **`delta_Nstar=0.2`'s own non-convergence** was observed but not
  independently diagnosed (no lambda sweep or bias test run at that point).

## Evidence

All raw records: `out-gradient-coupled-stiffness/scripts/diagnose_24a_output/`
(`diagnostic1_lambda_sweep.json`, `diagnostic1_supplement_m1e-2.json`,
`diagnostic2_linearity.json`, `diagnostic3_bias.json`,
`diagnostic3b_two_pass.json`, `diagnostic4_delta_nstar_walk.json`), plus full
console logs (`run_d1d2.log`, `run_d3.log`, `run_d4.log`) capturing every
per-sweep residual trace. Harness:
`out-gradient-coupled-stiffness/scripts/diagnose_24a_convergence_floor.py`.
