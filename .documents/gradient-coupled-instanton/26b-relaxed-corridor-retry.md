# Prompt 26 addendum — Diagnostic 12: relaxed-corridor retry at n=9: results

Direct empirical test of the question 26a raised: is `n=9`'s floor
(`m/Mp=1e-2, δN★=0.5`) actually caused by the outer shooting loop being
clamped against the corridor's unwidened positive edge, or was it only
*sitting* there — with the real obstruction being genuine physics further
out? 26a found the last-tried `λ` pinned bit-for-bit on `lambda_c_positive`
for the entire 50-iteration budget; it could not by itself distinguish
"the clamp is hiding a real root" from "the clamp happens to coincide with
where the search would have gotten stuck anyway."

## Executive summary

**The corridor clamp is ruled out. Widening it, by up to 10×, does not
produce convergence — the real obstruction is a genuine physics failure
("Picard inner failed") in a `λ≈5–12` band that the outer loop keeps
running into regardless of how much room the clamp gives it.**

| widening | corridor `[λ_c,neg, λ_c,pos]` | converged | last `λ` tried | nearest-edge fraction | outer iters | bailout |
|---|---|---|---|---|---|---|
| 1.0 (baseline)  | `[−10.62, 4.248]`   | No | 4.248 | **0.000** | 50 | floored / `max_outer_exhausted` |
| 2.5             | `[−26.55, 10.62]`   | No | 5.431 | 0.140 | 16 | floored / `wallclock_budget` |
| 5.0             | `[−53.10, 21.24]`   | No | 5.672 | 0.209 | 17 | floored / `wallclock_budget` |
| 10.0            | `[−106.2, 42.48]`   | No | 5.620 | 0.248 | 17 | floored / `wallclock_budget` |

- **`widening=1.0` reproduces Diagnostic 11's exact finding** (sanity check
  on this diagnostic's own harness, not a new result): pinned bit-for-bit at
  `λ_c,positive=4.247941624378134`.
- **The moment the corridor is relaxed at all (`widening=2.5`), the search
  moves well off the (now much larger) edge** — `nearest_edge_fraction` jumps
  to `0.14` — confirming the clamp genuinely was constraining the search at
  `widening=1.0`.
- **But it never converges, at any widening tried, including 10×.** And the
  console trace makes the reason concrete: at `widening∈{2.5,5.0,10.0}`, the
  search repeatedly logs `Picard inner failed at lambda=X` for
  `X` in roughly `5.6`–`12.5` — the **same specific λ values recur across
  widening=5.0 and widening=10.0** (`8.41744, 6.35119, 11.5168, 6.86775,
  6.39559, ...`, verbatim). Giving the outer loop 4× more corridor room
  between those two runs changed nothing about where it gets stuck — it
  still lands on the same handful of infeasible λ points. `final_residual`
  and `outer_iterations` are identical to several significant figures
  between `widening=5.0` and `widening=10.0` (`0.1119929355628475`, `17`
  both times) — a search that has saturated, not one still finding new
  territory as the wall recedes.
- **This is an inner-Picard-solve failure, not an outer-corridor
  question.** `Picard inner failed` is the inner BVP sub-solve failing
  outright at a given `λ` (the same failure mode 24a's Diagnostic 1
  originally characterised as a genuine feasibility wall, `H²<0` or similar
  — see `24a-diagnose-convergence-floor.md`'s own Diagnostic 1). The outer
  corridor clamp was never the thing preventing convergence at `n=9`; it
  just happened to sit close to where the search would stall regardless.

## Interpretation

This closes the question 26/26a opened: **`n=9`'s non-convergence is
genuine physics/discretisation stiffness, not a calibration artefact of the
`n=5`-derived corridor.** The `tau_multiplier` recommendation already made
in `26-sector-attribution-instrument-stiffness.md` stands, now on
considerably firmer ground — this diagnostic directly rules out the
alternative ("just widen the clamp") that would have been the cheaper fix
had it worked.

Two secondary observations worth keeping for later work:

- The inner-Picard failures cluster in `λ≈5–12`, on the **positive** side —
  the same side `n=9`'s last-tried point sat on at `widening=1.0`, and the
  same (unwidened, tighter) side of the asymmetric corridor. Whether this
  positive-side clustering is itself a clue (e.g. the search's own
  escalation logic systematically probing positive before negative at this
  `n`) or coincidental is not established here — the search never got a
  clean look at the negative side under any widening tested, since it kept
  failing on the positive side first.
- `outer_iterations` fell sharply once the corridor stopped being the
  limiting factor (`50 → 16 → 17 → 17`) while `wallclock` correspondingly
  rose to the full `900s` budget at every widening beyond `1.0` — each
  individual outer-loop evaluation costs much more once the search is
  actually reaching further-out, harder `λ` values instead of being
  clamp-limited to a handful of cheap near-edge probes. This is consistent
  with (not new evidence for or against) Diagnostic 10's own RK45
  step-explosion finding at `n=9`.

## Production change this diagnostic required

`ComputeTargets/GradientCoupledInstanton/picard.py`: added
`CORRIDOR_POSITIVE_WIDENING = 1.0` (module constant, mirroring the existing
`CORRIDOR_NEGATIVE_WIDENING = 2.5`), and changed
`lambda_c_positive = lgl_w_core * mu_final_seed / D11_seed` to
`lambda_c_positive = CORRIDOR_POSITIVE_WIDENING * lgl_w_core * mu_final_seed
/ D11_seed`. Default `1.0` reproduces the original `κ=1` unwidened bound
bit-for-bit — verified directly: an `n=5` re-solve at the default constant
reproduces `final_lambda=-15.51477347250894`,
`lambda_c_positive=15.292589847761285`,
`lambda_c_negative=-38.231474619403215` to full precision, matching
Diagnostics 6/9/10/11's own `n=5` baseline exactly.

This was necessary — not a convenience — because no diagnostic-only
monkeypatch could isolate the corridor bound from the real physics: `lam_bounds`
is a plain local variable computed inline inside `solve_picard`, and both of
its two candidate override points (`diffusion_model.D_matrix`,
`Numerics.OnionCoordinate.measure`) are also called from inside
`forward_rhs.py`'s own per-step RHS evaluation, so patching either to widen
the corridor would have silently changed the actual physics being
integrated, not just the outer-loop clamp. Confirmed with the user before
making this change (see conversation).

## Verification

- `git diff --stat` confined to
  `ComputeTargets/GradientCoupledInstanton/picard.py` (7 lines: one new
  constant + its use in `lambda_c_positive`) and
  `tools/diagnostics/GradientCoupledInstanton/convergence_floor.py` (new
  `diagnostic_12_relaxed_corridor_retry`).
- Default-behaviour bit-for-bit check (above) passed before the sweep was
  run.
- `python -m tools.diagnostics.GradientCoupledInstanton.convergence_floor --diagnostic 12`
  ran end-to-end, exit 0.
- Output JSON:
  `tools/diagnostics/GradientCoupledInstanton/output/convergence_floor/diagnostic12_relaxed_corridor_retry.json`.
- Since this diff touches `ComputeTargets/GradientCoupledInstanton/picard.py`
  directly (not just the diagnostics package), the broadened test filter
  (`pytest -m "not integration"`, per `.claude/rules/test-selection.md`) was
  run: **696 passed, 1 skipped, 61 deselected** in 807.00s (0:13:27) — zero
  failures, zero regressions from the new `CORRIDOR_POSITIVE_WIDENING`
  constant.
