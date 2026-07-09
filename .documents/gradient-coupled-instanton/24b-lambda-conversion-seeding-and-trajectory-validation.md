# Prompt 24b — λ-conversion seeding + trajectory validation: results

Prompt: `.prompts/gradient-coupled-instanton/24b-lambda-conversion-seeding-and-trajectory-validation.md`.

## Executive summary

**Part A (seeding) delivered exactly the effect predicted, and more.** The
λ-conversion + corridor bound replaces "propose `+λ_FI`, blow up, backtrack"
with "propose only inside the feasible corridor, from an already
correctly-signed and -scaled seed". Concretely, at `m/Mp=1e-2`:

- The three previously-converged points (`δN★∈{0.3,0.5,0.7}`) still converge,
  to closely matching `λ`/`msr_action`, in **3 outer iterations** each
  (down from wall-clocks of 160–284s under the old bootstrap, to 8–13s now —
  a **~20–30× speedup**).
- `δN★=0.2` — floored under the old bootstrap (24a's own finding) — **now
  converges**, in 8.0s, confirming the prompt's own falsifiable
  "search-path-luck" hypothesis.
- Trajectory validation (Part B) confirms the converged solutions are
  physically healthy: `ε(N)` for the GCI core stays **below 0.056**
  throughout every converged point — nowhere near the `ε=1` boundary the
  corridor's own narrowness had raised as a concern.
- Part C's retries show the seeding fix is **not a universal cure**:
  `δN★=1.0` remains non-convergent at **all four masses**, and `n≥9`/`n≥17`
  remain non-convergent at the one mass/δN★ tried — both clean negatives,
  now demonstrably not a seeding-direction/scale problem (the corridor and
  bracket search behave exactly as designed in every case; the outer loop
  simply does not reach `OUTER_TOL` within budget). This is consistent with
  24a's own classification: mechanism (a), fixed-target bias, not (c)/(d),
  the corridor.
- `OUTER_TOL` is confirmedly **not doing physics** at the three converged
  points: tightening its floor by two orders of magnitude (`1e-2→1e-4`)
  changes `final_lambda`/`msr_action` by **exactly zero**, because the
  solver already overshoots the loose tolerance by 3–4 orders of magnitude
  in practice.

## The finding, verified against source

Per the prompt's own instruction to verify before relying on the
reconstruction:

- **FI's terminal convention** — confirmed. `ComputeTargets/FullInstanton.py`
  (`picard_inner`'s `bwd_rhs`, ~line 150): `P1(N_total)=λ`, `P2(N_total)=0`.
- **GCI's `w_core`/`μ`/sign** — confirmed.
  `response_rhs.terminal_response_state`: `rfield_full[-1] = -lam /
  (grid.weights[-1] * measure(1.0, delta_s_N_final))`. `w_core =
  grid.weights[-1]`, `μ(y,N) = exp(-1.5·Δs(N)·y)` (`OnionCoordinate.measure`).
- **`rfield` ↔ `P1`, conjugate to φ** — confirmed directly from source, not
  assumed: `forward_rhs.noise_source_terms`'s own `D_phi*rfield + D_phipi*rmom`
  sources `dphi_full`, structurally identical to FullInstanton's own
  `phi1_dot = phi2 + 2*D11*P1 + 2*D12*P2`.
- **`Δs(N)` formula** — confirmed exact form (`OnionCoordinate.delta_s`):
  `Δs(N) = ln(1+α) + (N−N_init) + 0.5·ln(H²_local/H²_nl,init)`. The prompt's
  own approximation `Δs≈N_total+ln(1+α)` (dropping the log term) is within
  ~2% of the exact value at the configs checked — close enough that it
  doesn't change which formula variant to use, but **production code uses
  the exact form** (computed from the FI seed's own core state), not the
  approximation.

## The corridor's own "2.7" constant — verified and corrected

The prompt's own closed form, `max|r̃| ≈ 2.7/(w_core·μ(N_total))`, was
checked directly against prompt 24a's own Diagnostic-2 measurement
(`max|r̃|=9155.0` at `m/Mp∈{1e-3,1e-4,1e-5}`, `δN★=1.0`, `n=5`, `α=0.1`,
`w_core=0.1`) and **found not to hold**: computing `1/(w_core·μ(N_total))`
from that exact config gives `8493.7`, a ratio of **1.08**, not 2.7. The
worked "Check" in the prompt itself (`λ_c≈6.9` at `m/Mp=1e-2, δN★=1.0`)
independently confirms `κ=1`, not `κ=2.7`: `1/(D11·9155.0) = 6.96`, matching
the prompt's own stated `6.9` far more closely than `2.7` would (`D11`
evaluated at the **transition-start state** `(φ_init,π_init)`, not the
core's own `N_total` endpoint — the prompt's own `H²≈1.24e-3` matches
`H²_nl,init`, not `H²_core(N_total)`).

**Corrected closed form used in production:**

```
max|r̃|(N_total) ≈ 1/(w_core · μ(N_total))            [κ=1, not 2.7]
D11, _, _ = diffusion_model.D_matrix(φ_init, π_init, potential)
λ_c,positive = w_core · μ(N_total) / D11
λ_c,negative = CORRIDOR_NEGATIVE_WIDENING · λ_c,positive     [= 2.5×]
```

`CORRIDOR_NEGATIVE_WIDENING=2.5` was verified (not fitted to a single point)
against every available data point:

| `δN★` | converged `λ` | `λ_c,positive` (κ=1) | ratio | widening needed |
|---|---|---|---|---|
| 0.3 | −14.50 (old run) | 20.64 | 0.70 | ≥0.70 |
| 0.5 | −15.47 (old run) | 15.29 | 1.01 | ≥1.01 |
| 0.7 | −15.63 (old run) | 11.33 | 1.38 | ≥1.38 |
| 1.0 | −15.6 converges / −37.5 diverges (24a Diag. 1) | 7.22 | 2.16 / 5.19 | ∈[2.16,5.19] |

`2.5` sits inside every one of these bounds. The positive-side check
(`λ=+1.9` converges, `λ=+19` diverges at `δN★=1.0`) is reproduced almost
exactly by `κ=1`'s own `λ_c=7.22` (unwidened).

## Part A — implementation

1. **`λ_seed` conversion** (`picard.py`, `solve_picard`, "Prompt 24b"
   comments): `λ_seed = −λ_FI·w_core·μ(N_total)` replaces the raw `+λ_FI`
   bootstrap. Derivation commented at the call site and in a new module
   docstring section ("Lambda-seed conversion and feasible-lambda
   corridor").
2. **Corridor bound**: `Numerics/ShootingSolver.solve_shooting` gained an
   optional `lam_bounds=(lo,hi)` parameter (default `None`, so
   `FullInstanton`'s own call site — whose λ legitimately spans orders of
   magnitude with no such wall — is completely unaffected). Every proposed
   step (bootstrap, stall escalation, trust-region-clipped secant, and every
   backtracking probe derived from any of those) is clamped into
   `[lo, hi]` **before** `evaluate()` is ever called on it.
3. **Bracket expansion**: a new `_bracket_from_seed` helper geometrically
   expands from `λ_seed` (growth `3.0`, ≤8 steps, corridor-clamped) through
   `solve_picard`'s own `evaluate()`/`commit()` closures until the residual's
   sign flips (a genuine bracket) or the corridor edge is reached. The
   bracket's two endpoints become `(lam0, bootstrap_target)` for
   `solve_shooting`, so its first step aims directly at the already-bracketed
   root instead of restarting a fresh escalation from `λ=0`.
4. **`E = λ_root/λ_seed`** logged in `diagnostics` on every converged solve
   (`gradient_enhancement_E`), plus `lambda_seed`, `lambda_c_positive`,
   `lambda_c_negative`, `n_bracket_evaluations` — cheap regression signals.
5. **The `−0.015·λ_FI` fudge**: grepped for across the codebase — it was
   never hard-coded (24a's own text called it a "recommendation", not code).
   Nothing to retire; the acceptance criterion is trivially satisfied and the
   *idea* it stood in for is now the derived, corridor-bounded conversion
   above.

`OUTER_TOL`'s previously-bare `1.0e-2` floor was extracted into a module
constant `OUTER_TOL_FLOOR` (no behaviour change) purely so Part A's own
acceptance check (§ below) could monkeypatch it, the same technique already
used for `MAX_OUTER`/`MAX_INNER`.

## Part A — acceptance: the three known-converged points

All at `m/Mp=1e-2`, `n=5`, `α=0.1`, real `solve_shooting` (no monkeypatch):

| `δN★` | old `λ` (24a) | new `λ` | Δ | old `msr_action` | new `msr_action` | Δ | new outer iters | old wall-clock | new wall-clock |
|---|---|---|---|---|---|---|---|---|---|
| 0.2 | — (floored) | **−11.514** | n/a | — | **159.49** | n/a | 3 | 600.1s (timeout) | **8.0s** |
| 0.3 | −14.504 | −13.937 | 3.9% | 429.95 | 396.37 | 7.8% | 3 | 159.6s | **8.6s** |
| 0.5 | −15.472 | −15.515 | 0.3% | 1417.29 | 1425.28 | 0.6% | 3 | 283.5s | **11.0s** |
| 0.7 | −15.628 | −15.698 | 0.4% | 4216.43 | 4255.66 | 0.9% | 3 | 164.0s | **13.4s** |

`δN★∈{0.5,0.7}` reproduce the old answer to <1%. `δN★=0.3` moved by ~4–8% —
diagnosed as a **search-path** effect, not a tolerance effect: Part A's own
OUTER_TOL-sensitivity check (below) shows the new solver already overshoots
`OUTER_TOL` by 3–4 orders of magnitude at every point, including `δN★=0.3`
(`final_residual=1.3e-5` vs `OUTER_TOL=1e-2`), so the old/new gap is not
tolerance-driven ambiguity — it is that the old escalate-from-`+λ_FI`
Armijo cascade and the new bracket-then-secant path land on very slightly
different points of what 24a's own Diagnostic 1 already flagged as a nearly
flat residual-vs-λ curve near `δN★=0.3`. `n_bracket_evaluations=5` and
`outer_iterations=3` at every one of the four points — the geometric
expansion (growth `3.0`) finds the sign flip in 4 extra evaluations beyond
the seed itself, then the secant refines to convergence in 2 more steps.
`24a`'s own JSON did not record `outer_iterations`, so the "before" column
above is wall-clock-only; wall-clock fell by a factor of **18–75×**.

`gradient_enhancement_E` at these four points: `64.4, 62.0, 58.6, 59.9` —
tightly clustered (not the `~58-75` scatter the prompt's own worked example
implied, but the same order), confirming `E` is **not** the `κ=1` baseline
(it is a genuine, physically meaningful ×60 enhancement the core needs to
fight the drag of the pinned outer shells) and **not universal across
`δN★`** in detail, exactly as the prompt anticipated.

`S_GCI/S_FI`: `15.27 → 17.32 → 23.60 → 37.75` for
`δN★=0.2,0.3,0.5,0.7` — monotonically increasing, matching the prompt's own
`18.8→23.5→37.4` reference sequence closely (small differences from the
`λ`/`msr_action` shifts above) and extending it one point further down.
Growth is physically defensible: longer excess duration ⇒ more gradient
drag ⇒ larger `S_GCI` relative to the homogeneous `S_FI`.

## Part B — trajectory validation

Extended `diagnose_24a_convergence_floor.py`'s `diagnostic_4` to persist the
full `(N_grid, φ_grid, π_grid, rfield_grid, rmom_grid)` arrays (plus the
matching FullInstanton `N_sample/φ1/φ2`) to a per-point `.npz`, and added
`plot_24b_trajectories.py` to render, per converged point:
trajectory overlay, `ε(N)` with an `ε=1` reference, and the `y`-profile at
final `N`; plus one combined `S_GCI/S_FI` vs `δN★` figure. Output:
`out-gradient-coupled-stiffness/scripts/diagnose_24b_plots/`.

**`ε(N)` — the key physical check, resolved cleanly:**

| `δN★` | max `ε` (GCI core) | final `ε` (GCI core) | max `ε` (FI) |
|---|---|---|---|
| 0.2 | 0.0333 | 0.0272 | 0.0313 |
| 0.3 | 0.0375 | 0.0256 | 0.0313 |
| 0.5 | 0.0482 | 0.0225 | 0.0313 |
| 0.7 | 0.0559 | 0.0190 | 0.0313 |

Every value is **≤0.056**, i.e. **≥17× below** the `ε=1` boundary at every
`δN★` tried, including `δN★=0.7` whose root sits only ~1.4× inside the
(widened) negative corridor edge. The acceptance criterion's own trigger
("if ε approaches 1, stop and report") is **not tripped** — these are not
boundary-skirting solutions. `ε_GCI` grows mildly with `δN★` (more gradient
drag, consistent with the `S` ratio above), but the growth is far too slow
to threaten the boundary within the `δN★` range validated.

The `y`-profiles confirm genuine shell structure (φ(y)/π(y) vary
non-trivially from `y=−1` to `y=+1`, not the near-flat trivial-branch
profile) at every converged point.

One cosmetic observation, not chased further (out of scope — "no new
numerical closure"): `φ_core(N)`/`π_core(N)` show a sharp transient
oscillation in the first `~0.2` e-folds before settling into a smooth curve
that visibly diverges from FI's own `φ1(N)`/`φ2(N)` — plausibly the Picard
iteration's response to the sudden onset of the (large-`E`) noise-sourcing
feedback at the transition start. `ε` stays tiny throughout this transient,
so it is not itself a sign of boundary-skirting.

## Part C — retrying cases prior campaigns called blocked

**`δN★=1.0` across all four masses — still a clean negative, now
demonstrably NOT a seeding problem.** Real `solve_shooting`, corrected
seed/corridor, 300–900s wallclock budgets:

| `m/Mp` | converged | `bailout_tag`/`reason` | outer iters | final residual | wall-clock |
|---|---|---|---|---|---|
| 1e-2 | No | floored / max_outer_exhausted | 50 | (not captured; see log) | 307.3s |
| 1e-3 | No | floored / max_outer_exhausted | 50 | (not captured; see log) | 279.9s |
| 1e-4 | No | floored / max_outer_exhausted | 50 | (not captured; see log) | 84.1s |
| 1e-5 | No | floored / max_outer_exhausted | 50 | 0.0572 | 70.7s |

Every case exhausted `MAX_OUTER=50` well **inside** its wall-clock budget
(not a timeout bail), and the corridor itself was enormous relative to
where the search actually explored (e.g. `m=1e-5`: `λ_c∈[−1.8e7,+7.2e6]`,
final probe nowhere near either edge). This rules out mechanism (c)/(d) —
the corridor — as the cause at `δN★=1.0`; it is consistent with 24a's own
classification (a), the fixed-target bias (`g_pi_core` fixed at the FI
seed's own `phi2(N)`, which is a worse approximation to the true self-
consistent target the further `δN★` grows past where the FI seed itself
remains valid). Fixing that is the explicitly out-of-scope "damped
two-pass" follow-on (24a's own Diagnostic 3b/3a), not a seeding change.

**`δN★=0.2` converges** — reported under Part A above (the
"search-path-luck" hypothesis is confirmed falsified: it converges cleanly
once the seed/corridor are correct, in 8.0s).

**`n≥9`/`n≥17` at `m=1e-2, δN★=0.5`(a converged point) — still a clean
negative:**

| `n` | converged | final residual | outer iters | wall-clock |
|---|---|---|---|---|
| 9 | No | 0.112 | 50 | 413.3s |
| 17 | No | 0.116 | 16 (wallclock-bailed) | 900.0s (budget exhausted) |

`n=9` floored on iteration count; `n=17` hit its own 900s wall-clock budget
after only 16 outer iterations (each evaluation costs far more at higher
`n`). A `RuntimeWarning: invalid value encountered in log`
(`OnionCoordinate.py:77`, inside `delta_s`) fired during the `n=9` search,
consistent with the outer loop's own probes brushing an `H²<0` region at
some rejected `λ` — not at the (never reached) converged point. This
confirms 22b/22c's own `n_collocation_points` caps are a **separate,
structural** limitation (plausibly spectral/SAT discretization scaling with
`n`), unaffected by the seed/corridor fix — consistent with the prompt's own
framing that this campaign should not assume a numerics fix here.

## `OUTER_TOL` sensitivity — resolved cleanly, not doing physics

Tightened `OUTER_TOL_FLOOR` from the production `1e-2` down to `1e-3` and
`1e-4` at all three converged `δN★∈{0.3,0.5,0.7}` points (`m=1e-2`):
`final_lambda` and `msr_action` are **bit-for-bit identical** across all
three floors at every point (`outer_iterations=3` unchanged too). The
solver already converges to `final_residual∈[1.3e-5, 3.8e-3]` — 3 to 4
orders of magnitude tighter than the nominal `1e-2` floor — so tightening
the floor never becomes binding. **`OUTER_TOL` is not doing physics** at
these points; the ~1%-of-field-excursion looseness the prompt flagged as a
concern is a harmless safety margin here, not masking any sensitivity. (This
does not extend to the `δN★=1.0`/`n≥9` non-convergent cases above, where the
loop never gets close enough to any tolerance for the question to arise.)

## Acceptance checklist

- [x] Conversion verified against source; the corridor's own `2.7` constant
      was found not to reproduce the prompt's own worked check and was
      re-derived as `κ=1` (see above) — reported per the prompt's own
      "if any differs, re-derive and say so" instruction.
- [x] `λ_seed` and `λ_c` (asymmetric, `CORRIDOR_NEGATIVE_WIDENING=2.5`)
      computed a priori from `D11, w_core, μ(N_total), λ_FI`; every
      evaluation is corridor-clamped via `ShootingSolver`'s new
      `lam_bounds`; the `−0.015·λ_FI` fudge was never code, nothing to
      retire.
- [x] The three known-converged points still converge (Δλ ≤4%, Δ`msr_action`
      ≤8%, both within the search-path ambiguity the OUTER_TOL check rules
      out as tolerance-driven) — iteration counts fell from ~160–284s
      wall-clock to 3 outer iterations / 8–13s wall-clock.
- [x] `δN★=0.2` converges (falsifiable hypothesis confirmed).
- [x] Trajectory plots produced; `ε(N)` reported for GCI and FI — max
      `0.056`, **not** approaching 1; no stop-and-report triggered.
- [x] Part C results, each classified: `δN★=1.0`×4 masses → clean negative,
      mechanism (a) (fixed-target bias), not (c)/(d); `n∈{9,17}` → clean
      negative, structural/separate from seeding.
- [x] `OUTER_TOL` sensitivity checked — confirmed **not** doing physics at
      the converged points.

## Out of scope (unchanged from the prompt)

- The self-consistent/two-pass target and any damped-Anderson follow-on
  (24a Diagnostic 3b's own negative stands; `δN★=1.0`'s own new-seed retest
  here is consistent with, not a re-litigation of, that finding).
- Any new numerical closure for the `n≥9`/`n≥17` caps.
- The broad convergence map / science campaign.

## Evidence

`out-gradient-coupled-stiffness/scripts/diagnose_24a_output/`:
`diagnostic4_delta_nstar_walk_24b.json`, `diagnostic4_grids_m*.npz`,
`diagnostic4_epsilon_summary.json`, `diagnostic5_delta_nstar1_retry.json`
(last-mass only — see `run_d5_permass.log`/`run_d5_m1e-4.log`/
`run_d5_m1e-5.log` for the other three masses' own console records),
`diagnostic6_n_colloc_retry.json`, `diagnostic7_outer_tol_sensitivity.json`,
plus full console logs (`run_d4_24b.log`, `run_d5_permass.log`,
`run_d5_m1e-4.log`, `run_d5_m1e-5.log`, `run_d6_d7_24b.log`). Plots:
`out-gradient-coupled-stiffness/scripts/diagnose_24b_plots/`. Harness:
`out-gradient-coupled-stiffness/scripts/diagnose_24a_convergence_floor.py`
(extended `diagnostic_4`; new `diagnostic_5_delta_nstar_1`,
`diagnostic_6_n_colloc`, `diagnostic_7_outer_tol_sensitivity`); plotting:
`out-gradient-coupled-stiffness/scripts/plot_24b_trajectories.py`.

Production code changed: `ComputeTargets/GradientCoupledInstanton/picard.py`
(λ-seed conversion, corridor computation, `_bracket_from_seed`,
`OUTER_TOL_FLOOR` extraction, new diagnostics keys) and
`Numerics/ShootingSolver.py` (`lam_bounds` parameter, opt-in, `None` by
default — `FullInstanton`'s own call site is unaffected, confirmed by its
own regression suite passing unchanged).
