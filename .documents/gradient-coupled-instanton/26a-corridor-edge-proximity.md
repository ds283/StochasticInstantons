# Prompt 26 addendum — Diagnostic 11: corridor-edge proximity at n≥9

Follow-up to `26-sector-attribution-instrument-stiffness.md`, prompted by a
direct question in conversation: 24b's `lam_bounds` corridor clamp
(`λ_c,positive = w_core·μ(N_total)/D11`, `λ_c,negative = 2.5×λ_c,positive`)
was derived and calibrated **only at `n=5`**, against four `δN★` points at
one mass. `w_core = grid.weights[-1]` (the LGL terminal quadrature weight)
depends on `n` and shrinks quickly with it, so the corridor itself narrows
with `n` purely from discretisation, independent of any physics change —
raising the question of whether the `n≥9` floor Diagnostics 6/9/10 all found
is (at least partly) the outer loop being clamped against an artificially
tight wall, rather than genuine physical/discretisation stiffness. This was
never checked: no prior diagnostic that touched `n≥9` logged
`lambda_seed`/`lambda_c_positive`/`lambda_c_negative`, even though
`solve_picard` has always computed and exposed them.

Implementation: `diagnostic_11_corridor_edge_proximity` in
`tools/diagnostics/GradientCoupledInstanton/convergence_floor.py`
(`--diagnostic 11`), plus one new harness helper,
`capture_shooting_result()`, in `harness.py`. No production code touched —
`git diff --stat` confined to those two diagnostics-package files.

## Executive summary

**`n=9`'s floor is directly, unambiguously implicated with the corridor
clamp. `n=17`'s is not.**

| `n` | `w_core` | corridor `[λ_c,neg, λ_c,pos]` | converged | last `λ` tried | nearest-edge fraction | bailout |
|---|---|---|---|---|---|---|
| 5  | 0.1000  | `[−38.23, 15.29]` | **Yes** | −15.51 | 0.424 | converged |
| 7  | 0.0476  | `[−18.21, 7.282]` | **Yes** | −16.78 | **0.056** | converged |
| 9  | 0.0278  | `[−10.62, 4.248]` | No | **4.248** | **0.000** | floored / `max_outer_exhausted` |
| 17 | 0.00735 | `[−2.811, 1.124]` | No | −0.157 | 0.326 | floored / `wallclock_budget` |

- **`n=9`: `last_lambda_tried` equals `lambda_c_positive` bit-for-bit**
  (`4.247941624378134` both). The outer loop spent its **entire** 50-iteration
  budget (`559.8s`, comfortably inside the `900s` budget — this was not a
  time cutoff) sitting pinned at the corridor's positive wall. That is about
  as direct as evidence gets: the search was clamp-limited, not exploring a
  genuinely stiff nonlinear region and failing to converge on its own terms.
- **`n=17`: not clamp-limited.** `last_lambda_tried=-0.157` sits 33% of the
  corridor's own width from the nearer edge — comparable to `n=5`'s margin.
  Its bailout was `wallclock_budget` after only **7** outer iterations, not
  `max_outer_exhausted` — consistent with Diagnostic 10's own finding that
  individual Picard sweeps get very expensive at `n=17` (mean `7.7s`, max
  `48.7s` per sweep). This floor looks like genuine cost/stiffness, not a
  clamp artefact.
- **`n=7` is a warning sign, not a failure.** It converges, but its root
  sits only **5.6%** of the corridor's width from the (already `2.5×`-widened)
  negative edge — a much thinner margin than `n=5`'s `42%`. The margin the
  `CORRIDOR_NEGATIVE_WIDENING=2.5` calibration bought at `n=5` is visibly
  eroding by `n=7`, well before `n=9` snaps shut entirely.
- **A sign asymmetry worth flagging.** `n=5`, `n=7`, and `n=17`'s
  last-tried/converged `λ` are all on the **negative** side — matching
  24a/24b's own established finding that this mass's true root sits negative.
  `n=9`'s last-tried point is **positive**, pinned against the *unwidened*
  (`κ=1`, no `2.5×` analogue) positive bound. That bound is the tighter of
  the two by construction (`λ_c,positive` is `2.5×` smaller in magnitude than
  `λ_c,negative` at every `n`) — so if the search's own escalation logic ever
  probes positive at `n=9`, it hits a wall much sooner than it would probing
  negative.

## Method

New `diagnostic_11_corridor_edge_proximity` in `convergence_floor.py`,
following Diagnostic 6/9/10's own pattern at the identical point
(`m/Mp=1e-2, δN★=0.5`, real `FullInstanton` seed, `ns=(5,7,9,17)`,
`wallclock_budget=900.0`). Two pieces of data needed, both already computed
by `solve_picard` regardless of convergence outcome:

- `lambda_seed`, `lambda_c_positive`, `lambda_c_negative`,
  `n_bracket_evaluations` — pre-existing `solve_picard` diagnostics keys
  (already used by Diagnostic 5's own `δN★=1.0` corridor check), read
  directly, no new instrumentation needed.
- The outer loop's **last-tried `λ`**, even on non-convergence. This is the
  one piece `solve_picard`'s own `diagnostics["final_lambda"]` does NOT
  expose — it is masked to `None` whenever `shoot.converged` is `False`
  (`picard.py`), discarding exactly the value this check needs.
  `Numerics.ShootingSolver.ShootingResult.lam` itself carries no such
  masking — it is always the last value the outer loop actually committed
  to, converged or not. Recovered without touching production code via a new
  harness helper, `capture_shooting_result()`, which monkeypatches
  `picard_module.solve_shooting` to capture its return value — the same
  idiom `harness.capture_last_commit()` already uses to recover
  `commit()`'s last argument, just capturing the whole `ShootingResult`
  instead.

`w_core` itself (`grid.weights[-1]`) is read directly from the harness's own
`LGLCollocationGrid`, no monkeypatch needed.

`nearest_edge_fraction = min((λ_c,pos − last_λ), (last_λ − λ_c,neg)) /
(λ_c,pos − λ_c,neg)` — the last-tried `λ`'s distance to the nearer corridor
wall, as a fraction of the corridor's own width. `0` means sitting exactly
on a wall; values well away from `0` (as at `n=5`/`n=17`) rule the clamp out
as the limiting factor, mirroring 24b's own "final probe nowhere near either
edge" check for `δN★=1.0`.

## What this means for Diagnostic 10's own "ambiguous" call

Diagnostic 10 found both the forward and backward sectors' RK45 step counts
explode by nearly the same ~14× factor at `n=9`, and called the result
ambiguous — neither sector cleanly dominates. This diagnostic adds an
important caveat to that reading, without overturning it wholesale:

- **`n=9`'s data is now suspect as a clean stiffness measurement.** If the
  outer loop is pinned at the corridor wall for 50 iterations, it is likely
  re-evaluating very similar (or literally repeated) `λ` values rather than
  exploring a genuinely evolving nonlinear regime — the RK45 statistics
  Diagnostic 10 measured there are real integration cost, but may reflect
  the cost of many near-duplicate evaluations at a clamped point rather than
  a clean signal about which sector degrades with resolution.
- **`n=17`'s data is NOT under this cloud** — its search was demonstrably
  clamp-clear. That makes `n=17`'s own `backward_to_forward_steps_per_efold_ratio
  =1.461` (the crossover past 1, the one signal in Diagnostic 10 that leaned
  toward the response sector) a cleaner data point than it first appeared,
  since it isn't confounded by wall-pinning the way `n=9`'s statistics might
  be.

## Recommendation

Two candidate next steps, in order of cost:

1. **Cheapest, most direct test of this diagnostic's own finding**: re-run
   `n=9` with a temporarily widened/relaxed positive-side corridor bound
   (still a diagnostic-only monkeypatch, no production change — e.g. apply
   the same `2.5×` widening to `λ_c,positive` that the negative side already
   gets, or simply relax both bounds by a larger factor) and see whether it
   converges once freed from the wall it is currently pinned against. This
   directly tests whether a genuine root exists just beyond `4.248` (or
   beyond `−10.62`) that the current clamp is hiding, exactly the concern
   this whole line of inquiry started from. Not run here — flagging as the
   natural next diagnostic (would need a new `n_collocation_points`-dependent
   `lam_bounds` override monkeypatch, a small addition in the same style as
   `MonkeypatchGuard`) rather than assuming the answer.
2. If (1) shows relaxing the clamp does NOT produce convergence, that
   strengthens rather than weakens Diagnostic 10's original reading (the
   floor is genuine stiffness, not a clamp artefact) and the `tau_multiplier`
   recommendation stands unchanged. If (1) DOES converge, the fix is
   revisiting `CORRIDOR_NEGATIVE_WIDENING`'s own asymmetry (a production
   change to `picard.py`, requiring the same kind of multi-point calibration
   24b did, not a guess) — a materially cheaper fix than either the
   `tau_multiplier` study or reopening the response-sector SBP-SAT question.

## Verification

- `git diff --stat` confined to
  `tools/diagnostics/GradientCoupledInstanton/convergence_floor.py` and
  `tools/diagnostics/GradientCoupledInstanton/harness.py`.
- `python -m tools.diagnostics.GradientCoupledInstanton.convergence_floor --diagnostic 11`
  ran end-to-end, exit 0. `n=5`'s `converged=True`/`final_lambda=-15.51477347250894`
  matches Diagnostics 6/9/10's own `n=5` baseline bit-for-bit.
- `lambda_c_negative / lambda_c_positive = 2.500` exactly at every `n`
  tested (`38.23/15.29`, `18.21/7.282`, `10.62/4.248`, `2.811/1.124`) —
  confirms `CORRIDOR_NEGATIVE_WIDENING=2.5` is applied uniformly, and rules
  out an arithmetic slip in this diagnostic's own `nearest_edge_fraction`
  calculation (an independent recomputation from the raw
  `lambda_c_positive`/`lambda_c_negative`/`last_lambda_tried` JSON fields
  reproduces every reported `nearest_edge_fraction` to full precision).
- Output JSON:
  `tools/diagnostics/GradientCoupledInstanton/output/convergence_floor/diagnostic11_corridor_edge_proximity.json`.
- Since the diff touches `tools/diagnostics/GradientCoupledInstanton/`
  (`convergence_floor.py` and `harness.py`), the broadened test filter
  (`pytest -m "not integration"`, per `.claude/rules/test-selection.md`) was
  run: **696 passed, 1 skipped, 61 deselected** in 767.92s (0:12:47) — zero
  failures, zero regressions from the new `capture_shooting_result()` harness
  helper or `diagnostic_11_corridor_edge_proximity`.
