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
