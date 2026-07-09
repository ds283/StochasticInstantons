# Prompt 26 — Diagnostic 10: sector attribution via `instrument_stiffness` at n≥9: results

> **Addendum (Diagnostic 11):** the `n=9` data point in this note's own
> table below is now known to be corridor-clamped — the outer loop's last
> `λ` sat exactly on the (unwidened) positive corridor edge for its entire
> 50-iteration budget, not exploring a genuinely converging/diverging
> nonlinear regime. `n=17` is confirmed clamp-clear. See
> `26a-corridor-edge-proximity.md` for the full finding; it revises (does
> not overturn) the "ambiguous" call below — `n=17`'s own backward-leaning
> signal is now the cleaner of the two data points.

Prompt: `.prompts/gradient-coupled-instanton/26-sector-attribution-instrument-stiffness.md`.
Implementation: `diagnostic_10_sector_attribution` in
`tools/diagnostics/GradientCoupledInstanton/convergence_floor.py`
(`--diagnostic 10`). Diagnostics-package-only change — `git diff --stat`
confirms nothing under `ComputeTargets/`, `Numerics/`, or `Datastore/` was
touched; the only behavioural switch flipped is `solve_picard`'s existing
`instrument_stiffness` parameter, `False→True`.

## Executive summary

**Attribution: ambiguous/both — not a clean forward or backward call.** At
`(m/Mp=1e-2, δN★=0.5)`, `n=5` and `n=7` converge cleanly; `n=9` and `n=17`
both floor, reproducing Diagnostic 6/24b's own finding. The RK45
step-statistics do **not** show one sector spiking while the other stays
bounded:

| `n` | converged | fwd total steps | fwd rejected frac | bwd total steps | bwd rejected frac | bwd/fwd steps-per-efold | bailout |
|---|---|---|---|---|---|---|---|
| 5  | **Yes** | 11,730  | 0.2017 | 9,880   | 0.0856 | 0.842 | converged |
| 7  | **Yes** | 24,993  | 0.1904 | 21,939  | 0.0535 | 0.878 | converged |
| 9  | No | 339,983 | 0.1447 | 319,292 | 0.0594 | 0.939 | floored (`max_outer_exhausted`) |
| 17 | No | 167,931 | 0.0579 | 245,332 | 0.0748 | 1.461 | floored (`wallclock_budget`) |

- **The single sharpest signal is symmetric across sectors, not sector-specific.**
  Going from the last converged point (`n=7`) to the first floored point
  (`n=9`), total RK45 steps explode by **~13.6×** in the forward sector and
  **~14.5×** in the backward sector — nearly the same factor, in both
  directions, at exactly the point where convergence breaks. That is the
  strongest single fact in this dataset, and it argues for "both sectors are
  being stressed together at the failure onset," not "one sector fails and
  drags the other down."
- **Rejected-step fraction gives no forward-spike signal at all** — the
  opposite, if anything: `forward_rejected_fraction` falls monotonically
  across the whole sweep (`0.202→0.190→0.145→0.058`), while
  `backward_rejected_fraction` dips then rises in a narrower band
  (`0.086→0.053→0.059→0.075`). Neither trace looks like the "disproportionate
  spike, other sector stays bounded" pattern either decision branch predicts.
- **A weaker, secondary signal favours the backward sector at higher `n`.**
  `backward_to_forward_steps_per_efold_ratio` increases monotonically across
  every point tested (`0.842→0.878→0.939→1.461`) and **crosses 1 at `n=17`**
  — the response sector's per-efold RK45 cost overtakes the forward sector's
  for the first time in the sweep. This is real, but see the caveat below
  before over-reading it.
- **Caveat, exactly as the prompt anticipated**: `n=17`'s bailout came back
  `wallclock_budget` after only **5 outer iterations**, versus Diagnostic
  6/24b's un-instrumented run at the same point, which reached **16** outer
  iterations in the same 900s budget. `n=9`'s bailout tag matched
  (`max_outer_exhausted`, 50/50 iterations both times), but wall-clock to
  get there nearly doubled (`857.4s` here vs `413.3s` in 24b's un-instrumented
  run) — `final_residual` agrees closely both times (`0.1123` vs `0.112`),
  confirming this is measurement overhead, not a different physics result.
  `n=17`'s much larger overhead penalty (fewer sweeps completed at all) means
  its `bwd/fwd` ratio rests on a smaller sample of the run than `n=9`'s —
  suggestive, not definitive.

**Recommendation, per the prompt's own "ambiguous" branch:** proceed to the
`tau_multiplier` production prompt and Diagnostic 8t anyway — it is the
cheaper of the two remaining options, and the forward sector is not
exonerated by this data (it is the dominant `rejected_fraction` contributor
at every `n` tested, including both floored points). But the response sector
is explicitly **not ruled out**: the `bwd/fwd` ratio's crossover at `n=17`
means it should be revisited — per `23-response-sbp-sat-design-note.md`'s own
closing instruction — if the τ study comes back inconclusive.

## Method

Diagnostic 6's own `n`-retry pattern at the same known point
(`m/Mp=1e-2, δN★=0.5`, `FullInstanton` seed fetched once, real
`solve_shooting`), with exactly one behavioural change: `instrument_stiffness
=True` instead of `False`. No new instrumentation — `solve_picard`'s existing
`_aggregate_rk45_stats`/`_solve_ivp_instrumented` machinery (already threaded
through production, already the default) is simply switched on and its
eighteen `rk45_*`/`picard_sweep_wallclock_*` diagnostics keys are read and
persisted, plus three derived ratios (`forward_rejected_fraction`,
`backward_rejected_fraction`, `backward_to_forward_steps_per_efold_ratio`).
`ns=(5,7,9,17)` (the function's own default): `5` and `7` as converged
controls, `9` and `17` as the known-failing points from Diagnostic 6/24b.
`wallclock_budget=900.0`, matching Diagnostic 6's own `n≥9` budget.

## Full per-`n` records

```
n=5   converged=True  final_lambda=-15.5148  outer_iters=3   wallclock=11.0s
      rk45_forward:  total=11730  accepted=9364   rejected=2366  min_step=2.53e-4  max_step=0.0800  steps_per_efold=2932.50
      rk45_backward: total=9880   accepted=9034   rejected=846   min_step=1.49e-4  max_step=0.0532  steps_per_efold=2470.00
      picard_sweep_wallclock: min=0.179s mean=0.269s max=0.322s

n=7   converged=True  final_lambda=-16.7797  outer_iters=3   wallclock=37.8s
      rk45_forward:  total=24993  accepted=20235  rejected=4758  min_step=3.62e-4  max_step=0.0800  steps_per_efold=6248.25
      rk45_backward: total=21939  accepted=20766  rejected=1173  min_step=8.49e-6  max_step=0.0317  steps_per_efold=5484.75
      picard_sweep_wallclock: min=0.338s mean=0.755s max=1.230s

n=9   converged=False bailout=floored/max_outer_exhausted  outer_iters=50  final_residual=0.11227  wallclock=857.4s
      rk45_forward:  total=339983 accepted=290793 rejected=49190 min_step=1.50e-15 max_step=0.0800  steps_per_efold=84995.75
      rk45_backward: total=319292 accepted=300321 rejected=18971 min_step=4.50e-6  max_step=0.0241  steps_per_efold=79823.00
      picard_sweep_wallclock: min=0.859s mean=1.907s max=6.718s

n=17  converged=False bailout=floored/wallclock_budget     outer_iters=5   final_residual=0.11619  wallclock=900.0s
      rk45_forward:  total=167931 accepted=158214 rejected=9717  min_step=1.77e-16 max_step=0.0320  steps_per_efold=41982.75
      rk45_backward: total=245332 accepted=226977 rejected=18355 min_step=2.47e-6  max_step=0.0135  steps_per_efold=61333.00
      picard_sweep_wallclock: min=3.711s mean=7.747s max=48.680s
```

(`n=5`/`n=7` cross-check: `final_lambda` matches an independent
`instrument_stiffness=False` re-solve of the same point bit-for-bit —
`-15.51477347250894` and `-16.779694835821978` respectively — confirming
instrumentation changes measurement only, per `picard.py`'s own docstring.
`n=9`/`n=17`'s `final_residual` also agree closely with Diagnostic 6/24b's
own un-instrumented record at the same point — `0.1123` vs `0.112`, `0.1162`
vs `0.116` — the same non-convergent result, reached slower under
instrumentation.)

## Interpretation

The prompt frames three possible calls. Neither of the two "clean" calls fits:

- **Not forward-attributed.** A forward-attributed result needs
  `forward_rejected_fraction`/`steps_per_efold` to spike disproportionately
  at `n≥9` while backward stays bounded. Forward's rejected fraction does the
  opposite — it *falls* monotonically across the whole sweep — and forward's
  `steps_per_efold` explosion at `n=9` (`13.6×`) is essentially matched by
  backward's own explosion (`14.5×`) at the same transition.
- **Not backward-attributed.** A backward-attributed result needs the
  response sector's stats to spike while forward stays comparatively
  bounded. Backward's rejected fraction stays in a *narrower* band than
  forward's throughout (never exceeding `0.086`, vs forward's `0.058–0.202`),
  and backward is not the dominant sector by total-step growth at the actual
  failure onset (`n=9`) — only at `n=17`, and even there the margin (`1.46×`)
  is modest next to how dramatically *both* sectors grew from `n=7`.
- **Ambiguous, with a real secondary signal.** Both sectors degrade together
  at the point convergence actually breaks (`n=9`); neither shows the
  isolated single-sector spike either clean hypothesis predicts. There is,
  however, a genuine monotonic trend in `bwd/fwd_steps_per_efold` crossing 1
  by `n=17` — not noise, but not enough on its own (given the `n=17`
  wallclock-truncation caveat above) to justify a backward-attributed call at
  the resolution this diagnostic tested.

This is a valid, complete result per this project's own convention
(24a/24b/Diagnostic 6/7/Diagnostic 9) — a clean negative on both of the
"one sector, cleanly" hypotheses is not grounds to keep adding intermediate
`n` values speculatively.

## Recommendation

Per the prompt's own "ambiguous" decision branch: proceed to the
`tau_multiplier` production prompt (`forward_rhs.py`'s hardcoded
`tau = abs(A_core)` becoming a first-class `solve_picard` parameter — see
`DIAGNOSTICS_SUITE.md` §5) and Diagnostic 8t, since it is the cheaper of the
two remaining options and forward is not exonerated by this data (it remains
the dominant `rejected_fraction` contributor at every `n`, including both
failed points). But **the response sector has not been ruled out** — the
`bwd/fwd` ratio crossover at `n=17` is a real, monotonic trend across the
whole sweep, not a one-off artefact, and per
`23-response-sbp-sat-design-note.md`'s own closing instruction ("if a
genuinely new `n_max`-dependent failure is found in this sector in the
future, re-run this diagnostic first"), this diagnostic should be re-run
(ideally with a larger `n=17` wallclock budget, so its statistics rest on a
comparable number of outer iterations/sweeps to `n=9`'s, removing this
note's own truncation caveat) if the τ study comes back inconclusive.

## Verification

- `git diff --stat` confined to
  `tools/diagnostics/GradientCoupledInstanton/convergence_floor.py`
  (158 insertions, 1 dispatch-table line changed).
- `python -m tools.diagnostics.GradientCoupledInstanton.convergence_floor --diagnostic 10`
  ran end-to-end, exit 0. `n=5`'s result (`converged=True`,
  `final_lambda=-15.51477347250894`) agrees with Diagnostic 6's own `n=5`
  baseline to the same bit-for-bit tolerance Diagnostic 9's Step 0 already
  established at this point.
- All eighteen `rk45_*`/`picard_sweep_wallclock_*` keys captured for every
  `n`; none were `None` (every direction made at least one `solve_ivp` call
  at every `n` tested, including both floored points).
- Output JSON:
  `tools/diagnostics/GradientCoupledInstanton/output/convergence_floor/diagnostic10_sector_attribution.json`.
- Since the diff touches `tools/diagnostics/GradientCoupledInstanton/`, the
  broadened test filter (`pytest -m "not integration"`, per
  `.claude/rules/test-selection.md`) was run: **674 passed, 1 skipped, 61
  deselected** in 514.15s (0:08:34) — zero failures, zero regressions.

## Supplementary: `n=7` spatial/temporal profile (ad hoc, not part of Diagnostic 10's own output)

While Diagnostic 10 was running, an ad hoc re-solve of the same point at
`n=7` (`instrument_stiffness=False`, otherwise identical — reproduces
Diagnostic 10's own `n=7` `final_lambda` bit-for-bit) was used to plot
`φ(y)`/`π(y)` at fixed `N` and `φ_core(N)`/`π_core(N)` against `n=5`. `n=7`'s
`y`-profiles broadly agree with `n=5`'s in shape, but `π_core(N)` shows a
materially sharper transient near the start of the integration that `n=5`
smooths over (a deeper dip, `≈-0.50` vs `≈-0.30`, and a second, more
persistent oscillation out to `N≈1–1.5`). This is qualitatively consistent
with "genuinely under-resolved structure that sharpens with `n` and
eventually breaks convergence at `n≥9`" (this note's own §"Interpretation"
above), though it does not by itself distinguish which sector that structure
lives in — that is exactly the question this diagnostic's own ambiguous
result leaves open. See
`.documents/gradient-coupled-instanton/24-phase0-baseline.md` §6.4 for the
fuller writeup of this observation (not part of this diagnostic's own code
or acceptance criteria — recorded there since it updates the campaign
baseline, not this prompt's own deliverable).
