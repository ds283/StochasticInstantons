# Prompt 23 — Response-sector SBP-SAT closure + λ-scaling (unblocks the resolved regime)

**The last major structural piece.** Prompts 20/21/21a gave the *forward* spatial
operator an SBP-SAT closure (split-form advection + core SAT), curing its
`n_max`-dependent right-half-plane spectral growth. The *response* sector was
explicitly deferred (21a scope note) and still runs the pre-port structure: strong
Neumann-elimination at the core + plain (non-split) advection, using the **same**
`A_array` and therefore — by the response sector's own docstring — the same
destabilising core-node mechanism. At `λ ≈ 0` (every prior acceptance case, incl.
21a's `delta_Nstar=0.1`) this is invisible. At the **astronomic `λ`** the physical
resolved regime requires, it is the binding constraint (prompt 22c Finding 4:
response backward pass hits `H_sq_local < 0` or RK45 step-death). This prompt ports
the forward closure to the response sector and handles the terminal condition at
scale, unblocking the resolved regime and making prompt 22c's fixed-target bias
(Finding 3) measurable where it matters.

Diagnostic-first, mirroring 21. Audit-friendly comments throughout (what / why /
failure-signature / energy-step), as in 21/21a — the response sector will be read by
the same non-specialist physicists.

## Two physical facts that shape the fix

1. **Astronomic `λ` is physics, not a bug.** `D₁₁ = H²/(8π²) ≈ 1.6e-11` is a
   rare-event diffusion coefficient; `λ ~ 1/D ~ 1e9–4e9` is what a rare PBH-forming
   fluctuation costs. The response sector must be numerically stable *at that scale*,
   not rescued from it.
2. **The response system is linear in `(rfield, rmom)`.** Every term in
   `response_rhs` is linear in the response fields, with coefficients frozen from the
   forward background during a backward pass. The terminal condition is `∝ λ`. So the
   entire response solution is `r = λ · r̃`, where `r̃` solves the *same* system with
   an `O(1)` terminal condition `r̃_core = −1/(w·μ)`. And the forward coupling that
   feeds back — `D · rfield` — is `D · λ · r̃`, with `D·λ ~ O(1)` (the physical
   balance). The astronomic scale can be **factored out**, not just stabilised.

## The fix — two coupled parts

### Part A — SBP-SAT port (the `n`-dependent RHP instability; scale-independent)

Mirror the forward closure (21/21a) with the role-swap (`rmom ↔ phi`,
`rfield ↔ pi`). Concretely:

- **Split-form advection** in place of the plain product, for both response fields:
  `A_split = ½(diag(A)·D + D·diag(A) − diag(D·A))`. Same `A_array`/`advection_coefficient`
  as the forward sector.
- **Promote `rmom_core` to a free, integrated DOF** (currently Neumann-eliminated),
  exactly as the forward port promoted `phi_core`. Response state length grows
  `2·n_max − 1 → 2·n_max`; fix every site assuming the old length
  (`pack_response_state`/`unpack_response_state`, the datastore serialisation, the
  Picard state handling, `terminal_response_state`), each commented.
- **Core SATs**, role-swapped:
  - `rfield_core` (the free field, `↔ pi`): the value-type core SAT that cures the
    `rfield_core²` energy defect, `τ = |A_core|` (the forward sector's empirically
    doubled value). Its "target" is set by the **terminal condition** during the
    backward pass — `rfield_core` is anchored at `N_total` by `−λ/(w·μ)` and
    integrated backward — so unlike the forward `pi_core` there is no lagged/fixed
    *value*-target ambiguity here; the SAT provides the dissipation, the terminal BC
    provides the data. Confirm in Phase 1 whether a value-target is needed at all or
    whether split-form + the terminal anchor suffices.
  - `rmom_core` (`↔ phi`): the live-Neumann regularity SAT, as `g_phi_core` in the
    forward sector.
- **Adjoint-consistency is the design constraint, not an afterthought.** The response
  operator is the adjoint of the linearised forward operator; the MSR action pairs
  them, so the *discrete* response closure should be the discrete adjoint of the
  *forward* SBP-SAT closure — otherwise the action is computed against inconsistent
  operators. Use prompt 18a's boundary-block-mismatch diagnostic on the SAT'd
  forward/response pair to verify the mismatch collapses (it was `O(1)` and
  boundary-localised pre-port; it should not *grow* and should be consistent with the
  forward closure). Where "mirror the forward recipe" and "be the forward's discrete
  adjoint" disagree at the boundary, adjoint-consistency wins — flag any such case.

### Part B — λ-scaling (the astronomic terminal condition; conditioning)

Exploit the linearity: **solve the backward pass for `r̃ = r/λ`** (terminal condition
`r̃_core = −1/(w·μ)`, `O(1)`), and form the forward feedback as `(D·λ)·r̃` with
`D·λ` computed as one `O(1)` quantity — never materialising `λ·r̃ ~ 1e10` as an
intermediate. This removes the overflow/precision loss that drives the `H_sq<0`
blow-up, independently of Part A (which fixes the spectrum, not the scale).

- Carry `λ` symbolically out of the response solve; reintroduce it only where a
  genuinely `λ`-scaled quantity is needed (e.g. the MSR action's response-sector
  terms). Document the scaling convention at every boundary between scaled and
  unscaled quantities — a mixed-convention bug here would be silent and severe.
- Part A and Part B are complementary and both needed: without A, `r̃` still suffers
  `n`-dependent RHP growth; without B, even a stable `r̃` loses precision when
  reconstructed at astronomic `λ`. Phase 1 must show each is necessary and the pair
  is sufficient.

## Phase 1 — Diagnostic (prototype; mirror 21 Phase 1)

Extend `analyze_StiffnessSpectrum.py`'s assembly to the **response** operator and use
the prompt-20 signed-abscissa metric:

- [ ] **Confirm the disease.** The strong-BC response operator has positive
      `spectral_abscissa` growing with `n_max` (the same `~n^1.6` RHP growth the
      pre-port forward operator had, expected by the shared `A_array`).
- [ ] **Confirm Part A cures it.** The split-form + core-SAT response operator has
      `spectral_abscissa` bounded in `n_max` (flat), as the forward closure does.
- [ ] **Adjoint-consistency.** Run 18a's boundary-mismatch check on the SAT'd
      forward/response pair; confirm the boundary mismatch does not grow with `n` and
      the response closure is the forward's discrete adjoint to the expected level.
- [ ] **Confirm Part B.** At `λ ≈ 2e9` (the resolved-regime `delta_Nstar=1.0`
      value), the `λ`-scaled backward pass stays feasible (`H_sq_local > 0`, RK45
      completes) where the unscaled one dies; and the scaled result reconstructs the
      unscaled one to precision at moderate `λ` where both run.

Clean-negative is valid, as throughout this project — if some piece does not behave,
report it and scope it rather than forcing the port.

## Phase 2 — Port (gated on Phase 1)

Implement A and B in `response_rhs.py` / `picard.py`; wire the enlarged state through
the datastore and Picard. Then validate on the case the whole chain has targeted:

- [ ] **Resolved regime solves.** `N_init=19.5, N_final=16.0,
      delta_Nstar ∈ {1.0, 2.0, 3.0}`, quadratic `m/Mp=1e-5`: GCI converges at the
      astronomic `λ` (`≈ λ_FI`), `msr_action > 0`, finite, for `n_collocation_points`
      through `{5,7,9,11,13,17,33}`. This is the acceptance prompt 22/22c could not
      reach.
- [ ] **Positive control + n-convergence.** `msr_action(n)` plateaus across `{5…33}`
      on the (now non-flat) resolved profile (prompt 22 Study A, finally runnable).
- [ ] **Fixed-target bias, revisited (prompt 22c Finding 3).** With the resolved
      regime reachable, re-measure the fixed-target bias *in the physical regime*
      (where `λ_FI` should be a good same-sign proxy for GCI's own `λ`, unlike the
      short/regularised fixture that gave ~13× amplification). Report it. If it is
      small, the fixed target stands vindicated. **If it is not**, the pre-agreed
      fallback is a *two-pass outer self-consistency*: re-solve with the previous
      solve's `pi_core` as the new fixed target, iterate the outer loop a few times —
      each pass is fixed-target (machine precision, no ~1e-4 floor), and at the outer
      fixed point the target equals the solution so the bias vanishes. Do **not**
      build this speculatively; scope it only if the measured bias requires it.
- [ ] **Downstream.** This is the first genuine `extraction.py` / `scale_assignment.py`
      run on a non-flat, resolved profile (pending since 22a): confirm the `zeta(r)`
      density bracket and areal-average `C̄` handling behave, or report what breaks.
- [ ] **n=9 regression (22c).** Check whether the small-fixture `n=9` non-convergence
      22c capped around was the same `λ_FI`-proxy issue; it may clear once the response
      sector is stable, or may be a separate small item — report which.
- [ ] Full suite passes; add response-abscissa-bounded-in-n, adjoint-consistency, and
      resolved-regime-convergence regressions.

## Documentation

- `response_rhs.py` module docstring: record that the sector was ported to the SBP-SAT
  closure to match the forward sector, why (RHP growth binding at astronomic `λ`), and
  the `λ`-scaling convention. Update the docstring's own "not ported" note.
- Per-construct comments on the split form, the two core SATs, the adjoint-consistency
  requirement, and every scaled/unscaled boundary (Part B).
- A "how to verify this is still correct" note: response abscissa bounded (prompt 20),
  adjoint-mismatch collapse (18a), and the `λ`-scaling round-trip test.

## Out of scope

- The forward closure, the `phi_end` target, the shared shooting component, the fixed
  target / seeding (prompts 21/21a/22a/22c) — all unchanged.
- The two-pass outer self-consistency — conditional on the Finding-3 re-measurement,
  not built here unless required.
- Higher potentials (quartic/USR), the `alpha` scan, production-grid re-tuning — the
  resolved-regime solve this unblocks is their prerequisite, but they are separate.
