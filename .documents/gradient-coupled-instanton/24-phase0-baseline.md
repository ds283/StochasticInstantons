# Prompt 24, Phase 0 — Verified-status baseline

**Purpose:** reconstruct, from the test suite and the 21/21a/22/22a/22b/22c/23
design notes, what is *actually* verified about `GradientCoupledInstanton`
(GCI) convergence before the prompt-24 convergence-domain-map campaign adds
anything new. This is an audit, not new analysis — every claim below is
sourced to a specific test function or design-note finding.

Sources reviewed: `.documents/gradient-coupled-instanton/{21-sbp-sat-design-note,
21a-production-port-notes,22-validation,22b-convergent-iteration-design-note,
22c-fullinstanton-seed-fixed-target,23-response-sbp-sat-design-note}.md`;
`tests/test_gradient_coupled_instanton_end_to_end.py`,
`tests/test_gradient_coupled_instanton_phi_end_target.py`,
`tests/test_gradient_coupled_instanton_stiffness_instrumentation.py`,
`tests/test_sbp_sat_boundary_closure.py`, `tests/test_response_rhs.py`,
`tests/test_response_lambda_scaling_prompt23.py`,
`tests/test_response_spectrum_prompt23.py`, `tests/test_picard.py`,
`tests/test_n_collocation_points.py`.

---

## 1. Points with a passing test, and what each actually asserts

| Point `(N_init, N_final, δN★, n, α, potential)` | Test | Result | What is actually checked |
|---|---|---|---|
| `N_init=5.0, N_final=4.9, δN★=0.05` (`N_total=0.15`), `n=5, α=0.05`, `StubPotential(m_sq=1.3)` | `test_compute_gradient_coupled_instanton_end_to_end_full_values` and siblings in `test_gradient_coupled_instanton_end_to_end.py` | ✅ pass | Plumbing/shape/finiteness sanity only — array lengths, `r_phys` finite, noise-field stats finite/non-negative. Docstring explicitly frames this as a "basic convergence/plumbing sanity check." **Does not** assert `msr_action > 0` or `λ ≠ 0`. |
| Same point, `n=5`, **corrected (22a)** `phi_end` target | `test_solve_picard_converges_under_genuine_coupling_across_n` (`test_picard.py`) | ✅ pass | `failure is False`, `converged is True`, `final_lambda != 0` (`abs=1e-8`). **This is the only test anywhere in the suite with a genuine (`λ≠0`), non-trivial converged GCI solve.** Parametrized `n_collocation_points=[5]` only — despite the "across_n" name, only one value is tried. Docstring states `n=9` "does NOT reliably converge within a practical outer-loop budget," attributed to the fixed-target-biased root sitting at `λ≈-1.3`, opposite sign from `λ_FI≈+1.36`. |
| `N_init=19.5, N_final=16.0, δN★=0.1, α=0.1`, quadratic `m/Mp=1e-5`, `n∈{5,9,17,33}` | `test_solve_picard_production_case_converges_for_previously_failing_n`, `test_solve_picard_production_case_core_trajectory_converges_across_n` (`test_picard.py`) | ✅ pass | `converged=True`, cross-checked against FullInstanton at `n=5` (`rtol=1e-5`), `n`-spread `<1e-4` across `n∈{9,11,13,17,33}`. **`δN★=0.1` is the exact degenerate branch** (22 Finding 1: `λ=0` identically, `msr_action=0` to machine precision) — production-scale mass and `N_init/N_final`, but physically trivial. |
| `δN★ ∈ {1.0, 2.0, 3.0}` at production scale (`N_init=19.5, N_final=16.0, m/Mp=1e-5`), any `n` | — | **no test exists** | Never converged end-to-end anywhere in the design-note record. 22c Finding 4 names the specific blocker (§3 below). |

Supporting/adjacent tests that are **not** GCI-solve evidence (for completeness,
since Phase 24's later phases may reach for them):

- `test_gradient_coupled_instanton_phi_end_target.py` — regression suite for
  the 22a target-formula fix. No test in this file calls the production GCI
  solve to completion on the corrected target; positive-control checks use
  `FullInstanton` or pure algebra instead, because (per its own docstring) GCI's
  Picard solve does not converge on the corrected target without 22b/22c.
- `test_gradient_coupled_instanton_stiffness_instrumentation.py` — instrumentation
  plumbing only, on the same tiny `N_total=0.15` fixture; no numeric convergence
  content beyond ordering/presence checks.
- `test_sbp_sat_boundary_closure.py`, `test_response_spectrum_prompt23.py` —
  linear/frozen-coefficient spectral-operator diagnostics against
  `analyze_StiffnessSpectrum.py`. Explicitly, no production Picard/shooting code
  is exercised.
- `test_response_rhs.py`, `test_response_lambda_scaling_prompt23.py` — unit
  tests on the response-sector RHS and the isolated (non-Picard) backward pass.
  `test_rescaled_backward_pass_feasible_at_astronomic_lambda` reaches
  `λ∈{1e5,1e9,4e9}` but only for a single isolated backward integration, not
  the full nonlinear Picard/shooting loop — deferred explicitly in the 23
  design note.
- `test_n_collocation_points.py` — SQL/factory object tests for the
  `n_collocation_points` concept type; no solver content.

---

## 2. Capped / xfailed points, and why

| Cap | Where | Reason |
|---|---|---|
| `n` capped at `{5, 9}` | 22b design note | `n=17` tried on the small genuinely-coupled fixture; fails outright on the first outer iteration even after Armijo backtracking, within `MAX_OUTER=50`. |
| `n=9` dropped entirely | 22c design note; `test_solve_picard_converges_under_genuine_coupling_across_n` now covers `n=5` only | Fixed-target-biased root sits at `λ≈-1.3`, opposite sign from `λ_FI≈+1.36` — the FullInstanton seed is a poor proxy at this `n`. |
| 21a's `n∈{5,7,9,11,13,17,33}` "all converge in 1 sweep" table | 21a design note, production case | Valid but on `δN★=0.1`, later shown (22 Finding 1) to be the exact `λ=0` degenerate branch — not evidence of resolved-regime convergence at any `n`. |
| 5 previously-`xfail(strict=True)` tests | end-to-end + stiffness-instrumentation files | Markers removed once 22b/22c fixes made them pass outright; per 22b these are "the first genuine non-trivial GCI solve ... any prior prompt's acceptance run has ever produced" — but still confined to the tiny `N_total=0.15` `StubPotential` fixture at `n=5`. |

---

## 3. Named failure modes (chronological)

1. **Target degeneracy** (22 Finding 1) — the pre-22a `phi_end` formula is an
   exact algebraic identity with the noiseless background trajectory after
   `N_total` e-folds, for *every* `δN★` tried (`{0.1,1.0,1.5,1.9,2.5,3.0}`) →
   `λ=0` exactly, `msr_action=0.0` to machine precision. "Every prior
   acceptance/regression result for this compute target (prompts 19–21a)
   exercised only this trivial branch."
2. **Lagged-target Picard divergence** (22 Finding 2) — with the corrected
   target and the self-consistent lagged `g_pi(N)` target at `θ=1.0`, residual
   falls for ~15 sweeps then grows unboundedly, at every `(n, δN★)` tried
   including `n=5`. `θ=0.5` delays but doesn't cure it; `θ∈{0.2,0.05}` decreases
   monotonically but needs "several hundred to well over a thousand sweeps."
3. **Anderson residual floor** (22b) — plain Anderson mixing on `g_pi_core`
   stalls at a residual floor `~1e-4`–`1e-6`, confirmed not a tuning artifact
   (swept window size, damping, Tikhonov regularization, and a
   `newton_krylov` cross-check all reproduce the same plateau; insensitive to
   ODE tolerance and grid density).
4. **Fixed-target bias, amplified not damped** (22c Finding 3) — on the small
   genuinely-coupled fixture, perturbing the fixed FullInstanton target by
   `δ=1e-3` moves the converged `msr_action` by `~1.3e-2` — a **13× amplification**,
   not a damping. On a degenerate-target case the same test gives `diff=0`
   exactly — bias is "only demonstrably small in the near-background regime,
   not in general."
5. **Astronomic-λ response-sector failure** (22c Finding 4; 23) — at the
   production resolved-regime case, `λ_FI≈1.9e9`–`4.1e9`. GCI's own solve at
   this `λ` fails: the response-sector backward pass hits `H_sq_local<0`, or
   becomes "pathologically slow (RK45 step-halving without terminating in a
   practical time budget)." Root cause: `terminal_response_state` amplifies
   `λ` by an *additional* `O(10×)` via small LGL boundary weights at the
   terminal BC — invisible at the `δN★=0.1` trivial-`λ` scale every prior
   acceptance table used. 23 Part A confirms the response sector's own
   stiffness is **not** the same disease as the forward sector (backward-relevant
   abscissa is already bounded across the full `n_max=8..192` sweep); porting
   the SBP-SAT closure there anyway would make forward-safe-direction stiffness
   **~23× worse**, so it was **not ported** (clean negative). 23 Part B
   (λ-rescaling, `r=λ·r̃`) is implemented and unit-tested in isolation, but
   **not validated end-to-end against Finding 4** — that validation is exactly
   what prompt 24 Phase 1 is for.
6. **`n=9` non-convergence** on the one genuinely-coupled fixture available
   (22c) — see cap table above.

---

## 4. Explicit statement: non-trivial converged solve at production scale

**None exists.** No design note and no test presents a converged, `λ≠0`,
resolved-regime (`δN★∈[1,3]`) solve at production scale
(`N_init=19.5, N_final=16.0, m/Mp=1e-5`). The only genuine `λ≠0` converged
solve anywhere in the record is on the tiny `N_total=0.15`, `StubPotential`
fixture, capped at `n=5`.

This matches the prompt's own stated expectation ("the honest answer is
currently 'none at production scale'") — a consistency check that the baseline
above is complete, not a new finding.

---

## 5. What this baseline means for prompt 24

- **Phase 1** targets exactly the gap in Finding 5 / row 3 of §1: a converged
  non-trivial resolved-regime solve. Nothing in the existing record shows this
  has ever succeeded, so Phase 1 is not re-deriving a known result.
- **Phase 2**'s sweep axes (`m`, `δN★`, `n`, `α`) each have at least one prior
  data point confirming *part* of the space is degenerate/trivial (`δN★=0.1`,
  large `m`) and one confirming another part fails structurally (`δN★≥1`,
  `m/Mp=1e-5`) — but the map connecting them, especially the `n=9` cap's
  generality and the `m`-dependence of the astronomic-`λ` onset, has not been
  characterized.
- **Phase 3**'s FI-consistency comparison has no prior baseline at all in the
  non-trivial regime — 22c Finding 3's bias measurement is the only existing
  data point, and it is on the tiny fixture, not the physical regime Phase 3
  asks for.

---

## 6. Update — status after prompts 24 (revised)/24a/24b/25/26 (as of 2026-07-09)

This section records what changed once the campaign this baseline was
written *for* actually ran. It does not rewrite §§1–5 above, which remain an
accurate snapshot of what was known *before* prompt 24 — new findings are
appended here instead, each sourced the same way as above. Read this section
alongside `24-campaign-closeout.md` (the original `δN★=1.0`-only Phase A/B/C
run, superseded in scope — not correctness — by 24a/24b below),
`24a-diagnose-convergence-floor.md`, `24b-lambda-conversion-seeding-and-trajectory-validation.md`,
`25-bias-corrected-n-geq-9-retry.md`, and `26-sector-attribution-instrument-stiffness.md`.

### 6.1 §4 is now superseded: a non-trivial converged solve exists

**§4's "None exists" claim no longer holds.** 24a's Diagnostic 4, confirmed
and sped up ~20–75× by 24b's Part A (λ-seed conversion + corridor bound),
produced the project's first genuine (`λ≠0`, `msr_action>0`) converged GCI
solves, at `m/Mp=1e-2`, `n=5`, `α=0.1`, `δN★∈{0.2,0.3,0.5,0.7}`. 24b's Part B
confirmed these are physically healthy, not boundary-skirting artefacts:
`ε(N)` for the GCI core stays `≤0.056` throughout every converged point,
`≥17×` below the `ε=1` reference boundary.

Caveat carried over precisely, not glossed: this is at `m/Mp=1e-2`, the
*cheap* end of the four-mass sweep `{1e-2,1e-3,1e-4,1e-5}`, not the literal
production point `m/Mp=1e-5` §4 named. `δN★=1.0` — the point the original
Phase A/B/C run (`24-campaign-closeout.md`) tested — and `m/Mp=1e-5` at any
`δN★≥1` still do not converge (see 6.2). So §4's *general* statement
("no converged resolved-regime solve exists anywhere") is now false; its
narrower reading ("...at the specific production point tested") still holds.

### 6.2 `δN★=1.0` remains a clean negative at all four masses, seeding ruled out

24b's Part C re-ran `δN★=1.0` across all four masses under the *corrected*
λ-seed/corridor — still `floored`/`max_outer_exhausted` at `MAX_OUTER=50`
everywhere, well inside the wall-clock budget (not a timeout artefact), with
the outer search never approaching either corridor edge. This directly rules
out mechanism (c)/(d) — the narrow-corridor/wrong-side-root explanation §3
item 5 and the original Phase A/B/C closeout both entertained — as the cause
at this specific point, leaving 24a's mechanism (a) (fixed-`g_pi_core`-target
bias) as the standing explanation, per 24b's own classification. This
confirms the original closeout's Phase A finding ("no non-trivial converged
solve at `δN★=1.0`, any mass") was correct as far as it went; 24a/24b add the
mechanism, not a contradiction.

### 6.3 The `n≥9` cap: explanation revised twice since §2/§3

§2's cap-table row and §3 item 6 record the *pre-24* explanation for `n=9`
being dropped: "fixed-target-biased root sits at `λ≈-1.3`, opposite sign from
`λ_FI≈+1.36`" (22c) — i.e., the old bootstrap-toward-`+λ_FI` search finding
the wrong-signed root. **This exact mechanism no longer applies**: 24b's
corrected λ-seed already aims at the correct (negative) corridor from the
start, yet `n∈{9,17}` still floor at `m/Mp=1e-2, δN★=0.5` (a point that
converges cleanly at `n=5`) — `n=9` at `final_residual=0.112`
(`MAX_OUTER=50` exhausted), `n=17` at `0.116` (wall-clock-bailed after only
16 outer iterations). So the cap is real and reproduces, but the *reason*
given for it in §2/§3 is stale.

25's Diagnostic 9 then tested the next candidate explanation — whether this
is 24a's own mechanism (a), the fixed-`g_pi_core`-target bias, now biting at
finer resolution — directly, by sweeping bias-scaled target perturbations
(`δ/bias_n5∈{0,±0.3,±1.0,±3.0}`) at `n=9`: **clean negative**. No perturbation
converged; the response is the wrong shape for a curable bias (worse
monotonically in both directions beyond a marginal `+0.3·bias_n5` dip, with
the largest magnitudes destabilizing the outer loop into `blown-up`/
`diverging` states). This rules out mechanism (a) too, at this point.
**Current standing explanation: genuinely under-resolved structure (a
boundary-layer/regularity problem), not a seeding or target-bias artefact.**

26's Diagnostic 10 then sector-attributed that under-resolved structure
between the forward (onion, SBP-SAT-ported) and response/backward
(deliberately un-ported) directions, via `solve_picard`'s existing
`instrument_stiffness` RK45 step statistics. **Result: ambiguous, not a
clean single-sector call.** Total RK45 step counts explode in **both**
sectors from `n=7` to the first floored point `n=9` (forward
`24,993→339,983`, backward `21,939→319,292` — both ~14×) — symmetric, not
sector-specific — and `forward_rejected_fraction` actually *falls*
monotonically across the whole sweep, the opposite of a forward-attributed
signal. The one real secondary signal is `backward_to_forward_steps_per_efold_ratio`
climbing monotonically and crossing 1 at `n=17` (`0.842→0.878→0.939→1.461`),
which keeps the response sector from being ruled out without being decisive
on its own. Recommendation: proceed to the `tau_multiplier` study, revisit
the response sector if that's inconclusive. See
`26-sector-attribution-instrument-stiffness.md` for the full table and
reasoning.

**Diagnostic 11 (addendum), prompted directly by the question "could the
corridor clamp itself be hiding the true root?", adds an important caveat
to that reading.** `lam_bounds`'s corridor (`λ_c,positive=w_core·μ(N_total)/D11`,
`λ_c,negative=2.5×` that) was calibrated only at `n=5`, and `w_core =
grid.weights[-1]` shrinks sharply with `n` (`0.1000→0.0476→0.0278→0.00735`
at `n=5,7,9,17` — confirmed directly), narrowing the corridor by the same
factor with no physics change. Checking where the outer loop's own
last-tried `λ` sat relative to the corridor walls (recovered via a new
harness helper, `capture_shooting_result()`, since `solve_picard`'s own
`diagnostics["final_lambda"]` is masked to `None` on non-convergence) found:
`n=9`'s last-tried `λ` sits **exactly** on the corridor's positive edge
(`4.247941624378134`, bit-for-bit identical to `lambda_c_positive`), pinned
there for its entire 50-outer-iteration budget — the clamp is directly
implicated in `n=9`'s own floor, not ruled out as a confound. `n=17`, by
contrast, sits 33% of the corridor's width from either edge — clamp-clear,
genuinely wallclock-limited instead (only 7 outer iterations fit in 900s).
This means `n=9`'s own RK45 statistics (Diagnostic 10's "both sectors
explode together" data point) may reflect many near-duplicate evaluations at
a clamped point rather than a clean stiffness signal, while `n=17`'s
backward-leaning ratio is NOT under that cloud. See
`26a-corridor-edge-proximity.md` for the full finding.

**Diagnostic 12 then closed this question directly, and it is a clean
negative: the corridor clamp is ruled out.** Sweeping a new
`CORRIDOR_POSITIVE_WIDENING` production constant (`1.0→2.5→5.0→10.0`, added
specifically to make this test possible — see 26b's own "Production change
this diagnostic required" for why no pure-monkeypatch path existed) at
`n=9`: the `widening=1.0` baseline reproduced Diagnostic 11's exact
wall-pinning, but every wider setting — up to `10×`, giving the search a
corridor `[−106.2, 42.48]` vs the original `[−10.62, 4.248]` — still failed
to converge. The console trace shows why: the outer loop keeps running into
genuine `Picard inner failed` errors at `λ≈5–12`, the **same specific values
recurring verbatim** between `widening=5.0` and `widening=10.0`
(`final_residual`/`outer_iterations` identical between those two runs) — a
saturated search hitting real physics infeasibility, not one still finding
new territory as the wall recedes. **`n=9`'s floor is genuine
physics/discretisation stiffness, not a corridor-calibration artefact.** The
`tau_multiplier` recommendation stands, now on firmer ground — the cheaper
alternative this whole line of inquiry was checking for has been directly
ruled out rather than merely not attempted. See
`26b-relaxed-corridor-retry.md` for the full table and trace.

### 6.4 New data point: `n=7` converges, and is not just "`n=5` refined"

Not covered by any prior diagnostic — 24b's own `n≥9` retry (§6.3) tested
`n∈{9,17}` only, and 21a's own `n∈{5,7,9,...,33}` table (§2) was on the
degenerate `δN★=0.1` branch. An ad hoc re-solve of the Diagnostic 10 control
point at `n=7` (`m/Mp=1e-2, δN★=0.5`, `instrument_stiffness=False`,
otherwise identical to Diagnostic 10's own `n=7` call — reproduces its
`final_lambda=-16.7797` bit-for-bit) shows `n=7` converges cleanly, extending
the known-good resolution range up from `n=5`. Its `y`-profiles broadly agree
with `n=5`'s in shape, but `π_core(N)` shows a materially sharper transient
near the start of the integration than `n=5` resolves — a deeper dip
(`≈-0.50` vs `n=5`'s `≈-0.30`) and a second, more persistent oscillation out
to `N≈1–1.5` that is essentially absent at `n=5`. This is consistent with (not
proof of) 6.3's "genuine under-resolved structure" reading: `n=7` is
revealing real transient structure `n=5` smooths over, sharpening further —
and eventually breaking convergence — by `n=9`, rather than `n=7`/`n=9` simply
adding numerical noise on top of an otherwise-identical solution.

### 6.5 Other closed-out items from §2/§3

- **`OUTER_TOL`** (24b, confirmed again by Diagnostic 7): not doing physics
  at the converged `δN★∈{0.3,0.5,0.7}` points — tightening the floor two
  orders of magnitude changes `final_lambda`/`msr_action` by exactly zero.
- **`α_regularization` sensitivity** (Diagnostic 8a): stable across
  `α∈{0.01,0.05,0.1,0.3}` at every converged Diagnostic-4 point — no
  production change needed, no regularization-scale artefact found.
- **`τ_multiplier` sensitivity** (Diagnostic 8t): still blocked, unchanged
  from §3/DIAGNOSTICS_SUITE.md's own "Known gaps" — `tau=abs(A_core)` remains
  a hardcoded local in `forward_rhs.py`, not a `solve_picard` parameter; a
  small, explicitly-scoped production prompt is still a prerequisite.
- **Astronomic-`λ` response-sector failure** (§3 item 5, Finding 4/23 Part B):
  still not validated end-to-end at production scale (`m/Mp=1e-5`,
  `λ_FI~1e9`) — nothing in 24a/24b/25/26 touches this; all of the above is at
  `m/Mp=1e-2`. This remains open exactly as §3 left it.
