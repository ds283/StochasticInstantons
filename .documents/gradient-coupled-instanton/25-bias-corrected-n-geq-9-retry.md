# Prompt 25 — Diagnostic 9: bias-corrected target retry at n≥9: results

Prompt: `.prompts/gradient-coupled-instanton/25-bias-corrected-n-geq-9-retry.md`.
Implementation: `diagnostic_9_bias_corrected_n_retry` in
`tools/diagnostics/GradientCoupledInstanton/convergence_floor.py`
(`--diagnostic 9`). Diagnostics-package-only change — `git diff --stat`
confirms nothing under `ComputeTargets/`, `Numerics/`, or `Datastore/` was
touched.

## Executive summary

**Clean negative — the fixed-`g_pi_core`-target bias mechanism (Diagnostic
3a's own explanation for the `δN★=1.0` floor) does NOT explain the `n∈{9,17}`
non-convergence Diagnostic 6 found**, at the tested point
(`m/Mp=1e-2`, `δN★=0.5`). None of 7 bias-scaled `δg_pi_core` perturbations at
`n=9` converged, and the response to perturbation size/sign is the wrong
shape for a curable bias:

- Measured `bias_n5 = max|pi_core(N) − g_pi_core_final(N)| = 0.0827`, from a
  real `n=5` solve at this point (converged in 3 outer iterations,
  `final_lambda=-15.51`) — not assumed or reused from Diagnostic 3a's
  literal `0.03` (which was calibrated at a different mass, `m/Mp=1e-3`).
- Swept `δ/bias_n5 ∈ {0, ±0.3, ±1.0, ±3.0}` (7 points) at `n=9` under a
  raised `MAX_OUTER=30`, 900s wallclock budget/point: **all 7 floored,
  blew up, or diverged** — none reached `OUTER_TOL=0.01`.
- The one interesting datum, `+0.3·bias_n5` (`final_residual=0.022`, cut off
  by the wallclock budget rather than outer-iteration exhaustion), is
  closer to convergence than the unperturbed baseline (`0.112`) — but every
  *larger* perturbation, in **either** direction, is monotonically worse,
  and `±3·bias_n5` actively destabilizes the outer loop into `blown-up`/
  `diverging` states rather than converging. A genuine curable bias (as
  Diagnostic 3a found at `δN★=1.0`) looks like "a well-chosen `δ` produces
  real convergence"; this looks like "delta=0 is already close to the best
  this resolution can do, and pushing further in either direction only
  makes it worse."
- **Recommendation:** proceed directly to the `tau_multiplier` production
  prompt and Diagnostic 8t. This result rules out the cheap fixed-target-
  bias explanation for the `n≥9` floor; the evidence points at genuinely
  under-resolved structure (a boundary-layer/regularity problem) rather
  than a target-bias artefact fixable by a cheap correction.

## Method

Direct splice of Diagnostic 3a's bias-injection mechanism
(`phi2_perturbed = fi_data["phi2"] + δ`, re-solved via `solve_picard` with
`full_instanton_seed=seed` under a raised `MAX_OUTER`) onto Diagnostic 6's
n-retry pattern (same `(m, δN★)` point, swept `n_collocation_points`). The
one addition prompt 25 required beyond a literal splice: measuring the bias
scale itself (`bias_n5`) from a real solve at the point's own known-converged
resolution, rather than reusing Diagnostic 3a's `m=1e-3`-calibrated literal
`δ=0.03`, since the bias is not universal across mass/`δN★`.

## Step 0 — baseline bias measurement (n=5)

Real `solve_picard` at `(m=1e-2, δN★=0.5, n=5)`, ordinary unperturbed fixed
target (`δ=0`) — the same point Diagnostic 6 established converges cleanly.

| quantity | value |
|---|---|
| converged | True |
| final_residual | 3.77e-4 |
| final_lambda | −15.5148 |
| outer_iterations | 3 |
| wallclock | 11.6s |
| **bias_n5** = max\|pi_core − g_pi_core_final\| | **0.08272** |

(FullInstanton seed for this point: `lambda_FI=1061.42`, `msr_action=60.390`.)

## Step 1 — bias-scaled sweep at n=9

`phi2_perturbed = fi_data["phi2"] + δ`, `δ = frac · bias_n5`, re-solved at
`n=9` under `MAX_OUTER=30`, 900s wallclock budget/point:

| δ/bias_n5 | δ | converged | final_residual | bailout_tag | bailout_reason | outer_iters | wallclock |
|---|---|---|---|---|---|---|---|
| 0 | 0 | No | 0.1123 | floored | max_outer_exhausted | 30 | 666.6s |
| +0.3 | +0.02481 | No | 0.0225 | floored | wallclock_budget | 29 | 900.0s |
| −0.3 | −0.02481 | No | 0.1995 | floored | max_outer_exhausted | 30 | 801.2s |
| +1.0 | +0.08272 | No | 0.1632 | floored | wallclock_budget | 6 | 900.2s |
| −1.0 | −0.08272 | No | 0.4012 | floored | max_outer_exhausted | 30 | 433.8s |
| +3.0 | +0.24815 | No | 0.7868 | **blown-up** | ode_failure | 9 | 333.5s |
| −3.0 | −0.24815 | No | 0.9478 | **diverging** | wallclock_budget | 5 | 900.0s |

No point converged; `msr_action`/`final_lambda`/`gradient_enhancement_E` are
all `None` (not computed for non-converged solves, per the existing
convention). Full per-point records (including `outer_residual_history`-level
detail via the raw solve) are in the JSON artifact below.

## Classification: not confirmed — clean negative

The bias-correction mechanism that cured the `δN★=1.0` floor (Diagnostic 3a)
does not reproduce at `n=9` for this point. The evidence:

- **Residual does not improve monotonically toward a δ that cures it** — it
  gets marginally better at `+0.3·bias_n5` (still 2× the target tolerance,
  and only reached because the wallclock budget cut off outer iteration 29,
  not because it plateaued), then strictly worse in both directions beyond
  that, with the largest magnitudes (`±3·bias_n5`) destabilizing the outer
  loop entirely (`blown-up`/`diverging`) rather than approaching
  convergence.
- **No sign or magnitude in the tested range crosses `OUTER_TOL=0.01`.**
  The closest approach (`0.0225` at `+0.3·bias_n5`) is still more than 2×
  the target tolerance, and its own bailout was a wallclock cutoff, not a
  residual plateau suggesting "nearly there."
- This is a genuinely different shape of result from Diagnostic 3a's own
  `δN★=1.0` bias test, where a chosen `δ` produced real, clean convergence.
  Here, perturbing the target in either direction never converges, and only
  ever makes the outer loop's state worse or more unstable.

Per this project's existing convention (24a/24b/Diagnostic 6/7), a clean
negative like this is treated as a complete, valid result — not grounds to
keep widening `delta_fractions` until something converges.

## Recommendation

Proceed directly to the `tau_multiplier` production prompt
(`ComputeTargets/GradientCoupledInstanton/forward_rhs.py`'s hardcoded
`tau = abs(A_core)` needs to become a first-class `solve_picard` parameter
before Diagnostic 8t is runnable — see `DIAGNOSTICS_SUITE.md` §5) and
Diagnostic 8t itself, since Diagnostic 9 rules out the cheaper
fixed-target-bias explanation for the `n≥9` non-convergence. The evidence is
consistent with a genuine under-resolved boundary layer / regularity issue
at higher `n`, not a seeding/target artefact.

## Verification

- `git diff --stat` confined to
  `tools/diagnostics/GradientCoupledInstanton/convergence_floor.py`.
- `python -m tools.diagnostics.GradientCoupledInstanton.convergence_floor --diagnostic 9`
  ran end-to-end, exit 0.
- Output JSON: `tools/diagnostics/GradientCoupledInstanton/output/convergence_floor/diagnostic9_bias_corrected_n_retry.json`
  (contains both the `bias_n5` baseline measurement and the full 7-point sweep).
- Since the diff touches `tools/diagnostics/GradientCoupledInstanton/`, the
  broadened test filter (`pytest -m "not integration"`, per
  `.claude/rules/test-selection.md`) was run: **585 passed, 1 failed** in
  19m11s. The one failure
  (`test_response_lambda_scaling_prompt23.py::test_rescaled_backward_pass_feasible_at_astronomic_lambda[1e9]`,
  a `wallclock < 10.0` timing assertion that measured `11.5s`) was confirmed
  pre-existing and unrelated: re-run standalone with this diagnostic's
  change stashed out, all 4 parametrized cases (including the `1e9` one)
  passed in 30.3s total. The failure is a timing flake under load (likely
  CPU contention from this diagnostic's own concurrent Picard solves during
  the full-suite run), not a regression — nothing in this change touches
  `ComputeTargets/`, `Numerics/`, or any code that test imports.
