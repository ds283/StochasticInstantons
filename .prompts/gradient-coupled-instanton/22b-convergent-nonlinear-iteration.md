# Prompt 22b — Convergent nonlinear iteration for the coupled instanton (diagnostic-first)

**Scope:** a diagnosis-then-fix task in the style of prompts 20/21 — derive/measure
before changing the scheme. Fixes Finding 2 of the prompt-22 validation: on the
corrected (non-degenerate) target from prompt 22a, the production Picard iteration
does not converge — the sweep-to-sweep residual falls for ~15 sweeps then grows
without bound (`theta=1`), at every `n_collocation_points` and `delta_Nstar`
tried, and under-relaxation (`theta<1`) only trades divergence for impractically
slow convergence. **Gated on prompt 22a** (there is no non-trivial problem to
converge until the target is fixed).

The instanton is a genuine saddle of a well-posed BVP, so a convergent scheme
provably exists; the current fixed-point map simply isn't it. This is an
algorithm-design problem, not a physics dead end.

## Phase 1 — Diagnosis (no scheme change; instrument and isolate)

The prompt-22 harness (`validation_22_resolved_regime.py`) isolated the *inner*
Picard loop at a fixed Newton `lambda`-probe and showed it diverges. It did **not**
isolate *why*. The single most decision-relevant experiment resolves this fork:

### 1a. The fork: is it the lagged target, or the response coupling itself?

Run the inner Picard loop on the corrected target under two closures, same case(s),
residual-vs-sweep:

- **Lagged `g_pi_core`** (current production): reproduce Finding 2 (baseline).
- **Fixed `g_pi_core = FullInstanton pi_core(N)`** (no lagging — the target does not
  chase the solution between sweeps): does the response↔forward Picard converge?

Interpretation:
- If the **fixed** target converges → the lagging is the culprit. The lagged
  penalty `-tau(pi_core^{k+1} - g^k)` is a delayed-feedback loop
  (`∝` sweep-to-sweep *change* in `pi_core`), a classic route to iteration
  instability, and its removal fixes it. Go to 2A.
- If the **fixed** target also diverges → the response↔forward coupling is itself
  non-contractive, independent of the target. Go to 2B.

This one experiment determines the entire remediation. Record it cleanly.

### 1b. Characterise the map (supporting evidence)

- Confirm the divergence is the *inner* loop (already indicated: it appears at a
  fixed `lambda`-probe), not the outer Newton — so the fix targets the inner
  fixed-point map.
- Estimate the fixed-point map's local contraction factor (ratio of successive
  residuals in the *descending* phase, and in the *growing* phase) vs `n` and
  `delta_Nstar` — a factor `>1` in the growing phase quantifies "how
  non-contractive," and whether it worsens with `n` (a spatial-resolution
  coupling) or is `n`-independent.
- Note whether the divergence onset (~15 sweeps) coincides with `g_pi_core` (or the
  response fields) developing structure away from the seed — i.e. whether it is the
  *departure from the trivial-seed neighbourhood* that triggers it.

Write Phase 1 into a short design note (fork outcome, contraction estimates,
mechanism) before touching the scheme.

## Phase 2 — Fix (contingent on the Phase 1 fork)

### Path 2A — lagging is the culprit

Two options; the design note should recommend one, with reasoning:

1. **Fixed `FullInstanton` target + quantify the bias.** Revert to the user's
   original proposal 3 (fixed `g_pi = FullInstanton pi_core`), which has no delayed
   feedback. The cost is that the SAT penalty no longer vanishes at convergence, so
   the answer carries a bias. **Measure it**: because `tau ~ A_core/2 ~ 1/Delta_s`
   is large only near `N_init` (where the gradient-coupled core and FullInstanton
   nearly coincide) and small where they diverge, the bias should be small and
   self-limiting. Demonstrate closure-independence *approximately*: solve with the
   FullInstanton target and with a deliberately perturbed fixed target, and show
   `msr_action` moves by `≪` the physics signal. If the bias is demonstrably at or
   below solver tolerance, this is the pragmatic answer.
2. **Solve `g_pi_core` by Newton / Anderson acceleration** rather than naive
   lagging — keeping zero bias (the self-consistent target) but replacing the
   unstable delayed-feedback fixed-point update with a convergent one. Anderson
   acceleration on the `g_pi_core` update is the low-intrusion option (uses residual
   history, no Jacobian); a Newton step on the coupled `(lambda, g_pi_core)` system
   is the robust one. Prefer Anderson first if it converges — it is a small,
   well-understood wrapper around the existing sweep.

Decision guide: if 2A.1's measured bias is at tolerance, take it (simplest, and it
resolves the original bias worry empirically rather than by construction). If the
bias is non-negligible, take 2A.2.

### Path 2B — the response coupling is non-contractive

The target choice is a side issue; the Picard fixed-point map on the coupled
`(forward, response)` sectors must be replaced with a convergent iteration:

- **Anderson acceleration** on the existing Picard sweep first (cheapest; often
  converts a mildly non-contractive map without new derivatives).
- If that is insufficient, a **Newton / quasi-Newton** step on the coupled residual
  (the standard robust approach for instanton BVP saddles). This needs the coupled
  Jacobian (or a matrix-free JFNK with the existing sweep as the residual
  evaluation) — scope the derivation explicitly, mirroring how 20/21 handled the
  operator.
- The lagged-vs-fixed target question still applies on top and is resolved as in 2A
  once the coupling iteration converges.

## Acceptance

- [ ] Phase 1 fork resolved and documented (fixed-target convergence result +
      contraction estimates).
- [ ] On the corrected target (22a), the chosen scheme converges to the inner
      tolerance for `n_collocation_points ∈ {5,7,9,11,13,17,33}` at a resolved
      `delta_Nstar` (the prompt-22 non-trivial case), within a practical sweep
      budget — with residual-vs-sweep plots showing genuine convergence, not a
      parked drift.
- [ ] Outer Newton on `lambda` converges (not hitting `MAX_OUTER`).
- [ ] **Positive control:** the converged `GradientCoupledInstanton` `msr_action`
      is `> 0`, strictly, on the non-trivial case — the first genuine non-trivial
      solution this target has ever produced.
- [ ] If Path 2A.1 (fixed target) is chosen, the bias-magnitude / approximate
      closure-independence evidence is recorded; if 2A.2 or 2B, the zero-bias claim
      is demonstrated via the two-seed check.
- [ ] Hand-off: with a converged non-trivial solution now existing, **prompt 22's
      Studies A–E can be re-run** (the harness is reusable). Note that this is also
      the first genuine exercise of `extraction.py` / `scale_assignment.py` on a
      non-flat profile (flagged pending in 22a) — watch for the tolerance / areal-
      average issues there.

## Out of scope

- The `phi_end` target fix (prompt 22a, prerequisite).
- Studies A–E themselves (prompt 22, re-run after this converges).
- The SBP-SAT linear closure (prompts 20/21) — validated and target-independent; not
  re-opened here. Finding 2 is a *nonlinear-iteration* failure layered on top of the
  (correct) linear closure, not a defect in the closure.
