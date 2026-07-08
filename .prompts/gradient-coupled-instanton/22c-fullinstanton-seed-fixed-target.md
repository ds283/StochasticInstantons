# Prompt 22c — FullInstanton seeding + fixed SAT target for the coupled instanton

**Builds on** commit `c8c4a98` (prompt 22b). **Does not revert it** — 22b's outer-
Newton hardening (secant / Armijo / trust-region) and its correct diagnosis
(lagging is Finding 2's cause) are kept. This prompt makes two coupled changes
that 22b's own evidence points to:

1. **Abandon the self-consistent (lagged/Anderson) `g_pi_core` target; use a fixed
   target `g_pi_core = FullInstanton pi_core(N)`.** 22b's fork showed the fixed
   target converges to machine precision (5e-14, one sweep) while the self-
   consistent target stalls at a ~1e-4 floor that `scipy.optimize.newton_krylov`
   also hits — i.e. the floor is structural to self-consistently determining
   `g_pi_core` (plausibly because `tau ~ 1/Delta_s` leaves `g` weakly determined
   where the coupling is negligible), not an accelerator artefact. The self-
   consistent target's goal (zero bias) is not achieved in practice anyway
   (~`tau·1e-4` residual bias), so it is dropped in favour of a fixed target whose
   (small, quantifiable) bias buys machine-precision convergence.
2. **Seed the solve from FullInstanton**, so the outer Newton starts next to the
   solution rather than at `lambda=0`. This is the direct fix for the resolved-
   regime / `n≥17` non-convergence 22b left open and attributed to shooting
   conditioning — starting the shooting at `lambda_FI` *is* the conditioning fix.

The fixed target is safe here specifically *because* of the seed: with `lambda`
seeded at `lambda_FI` the outer loop stays near the solution, avoiding the drift-
far-from-seed failure that ruled out a fixed target in 22b's stress test.

Diagnostic-first, matching prompts 20/21/22b: prototype and validate the hypothesis
on the hard cases before the production change. Audit-friendly comments throughout
(what / why / failure-signature), as in 21/21a.

## The seed (precise)

- **`lambda`**: initialise the outer Newton at `lambda_FI`, FullInstanton's own
  converged terminal multiplier (P1-equivalent) for the same
  `(phi_init, pi_init, phi_end, N_total)`.
- **Forward fields `(phi, pi)`**: interpolate in the onion coordinate `y ∈ [-1,+1]`
  between the core and exterior boundary seeds,
  ```
  field(y, N) = ((1+y)/2) * core(N) + ((1-y)/2) * exterior(N)
  ```
  with `core(N) = FullInstanton (phi,pi)(N)` and `exterior(N) = noiseless
  background (phi,pi)(N_offset + N)`. **Linear** is the primary shape — motivated
  by the gradient-free `zeta(r)` being ~linear in `log r`, hence `phi(y)` ~linear
  in `y` in slow-roll. Keep the interpolation shape a single, documented knob (a
  `seed_profile` selector) so a more core-concentrated form (e.g. exponential in
  `y`) can be tried *only if* linear fails to converge on a far-from-slow-roll case.
- **Response fields `(rfield, rmom)`**: **do not interpolate them.** Their terminal
  boundary condition (`rfield = 0` at `N=N_total` on every non-core shell — noise
  no longer acts in the outer shells at the endpoint) is enforced by the backward
  integration. So derive the response seed by running **one backward pass** from the
  seeded forward state (the natural first half-step of Picard). This yields a
  response seed consistent with the seeded forward profile and exactly BC-respecting,
  with no `rfield`/`rmom` interpolation and no "reshape the exterior noise" transient.
- Ensure the seeded forward grid is actually *used* as the sweep-0 current guess
  (not silently recomputed from the uniform IC + zero response, which is the current
  `_solve_picard_once` behaviour) — verify this against the Picard structure and
  comment it; a seed that doesn't stick is the obvious failure mode.

## Fixed target

- `g_pi_core(N) = FullInstanton pi_core(N)` (i.e. FullInstanton's `phi2(N)`),
  **fixed** for the whole solve. In 22b's parameterisation this is `theta=0` with
  the seed supplied; make it the explicit default and document that the self-
  consistent path (`theta>0` / Anderson) is deprecated, kept dormant only for
  regression comparison, not for production use.
- Keep `g_phi_core` as the existing **live-Neumann** target
  (`neumann_boundary_value` from the current interior) — it imposes regularity, is
  computed from the current state (no lag, no delayed feedback), and is not the
  contested closure.

## Shared shooting infrastructure

Factor 22b's scalar root-finder on `lambda` (secant on real evaluated points +
Armijo backtracking + trust-region cap) into a **reusable component**, and use it in
both `GradientCoupledInstanton` and `FullInstanton`. FullInstanton's own shooting
was flagged as poorly conditioned (prompt 22 Finding 1b) and now sits on the
critical path as the seed source, so it should get the same hardening. Anderson does
**not** port — it accelerated the (now-abandoned) self-consistent fixed point.

## Phase 1 — Diagnostic (prototype, no production change)

In the standalone harness (`validation_22_resolved_regime.py` /
`explore_onion_stiffness.py` style, Ray-bypassing), assemble the fixed-target solve
with the FullInstanton seed and confirm the hypothesis on the cases 22b could not
converge:

- [ ] On the resolved-regime production case (`N_init=19.5, N_final=16.0,
      delta_Nstar ∈ {1.0, 2.0, 3.0}`, quadratic `m/Mp=1e-5`), the fixed-target +
      seeded solve **converges to machine precision** (no ~1e-4 floor), for
      `n_collocation_points` through `{5,7,9,11,13,17,33}` — the regime and `n`
      values 22b left open.
- [ ] The outer Newton, seeded at `lambda_FI`, converges in few iterations (not
      hitting `MAX_OUTER`), with the residual actually moving (contrast 22b's
      "barely moves over dozens of iterations" on this case).
- [ ] Record convergence vs `n` and vs interpolation shape; confirm linear
      suffices, or document where a more concentrated shape is needed.

If Phase 1 does **not** converge on some case, that is the finding — report it and
scope it, rather than forcing the production change. (A clean negative is valid, as
in prompt 22.)

## Phase 2 — Production port (gated on Phase 1)

- Seed logic in `solve_picard` / `_solve_picard_once`: FullInstanton `lambda`,
  interpolated forward fields, response-via-backward-pass, seeded grid actually used.
- Fixed target as default; self-consistent path deprecated/dormant.
- Reusable shooting component wired into both targets.
- FullInstanton seed **fetched** from the datastore where available (it is computed
  upstream for the same parameters), computed via the delegate as fallback — as in
  21a, but now the fetched seed and this BVP share the *same* fixed target (22a), so
  the 21a retry-band-aid for mismatched seeds should be removable; confirm and remove
  it if so (it was an artefact of Finding 1).

## Acceptance

- [ ] **Convergence, no floor:** fixed-target + seeded solve converges to solver
      tolerance (not the ~1e-4 self-consistent floor) on the resolved-regime case at
      `n ∈ {5,7,9,11,13,17,33}`.
- [ ] **Positive control:** `msr_action > 0`, `lambda ≈ lambda_FI` (order-of-
      magnitude), on the resolved case — a genuine non-trivial coupled solve at
      production `n`.
- [ ] **Fixed-target bias is quantified and small:** perturb the fixed target
      (`g_pi_core → g_pi_core + delta`) and confirm the converged `msr_action` moves
      by `≪` the physics signal / at tolerance — the empirical statement that the
      fixed closure does not distort the answer. (This replaces the two-seed check
      for the fixed target.)
- [ ] **n-convergence:** `msr_action(n)` plateaus across `{5…33}` on a resolved,
      non-flat-profile case (the primary correctness evidence, per prompt 22 Study A).
- [ ] **Regularity emergent:** `(D·pi)_core → 0` at convergence without being imposed.
- [ ] Shooting hardening shared; FullInstanton uses it; Anderson/self-consistent
      path deprecated; 21a retry-band-aid removed if now redundant.
- [ ] Full existing suite passes; the prompt-22a positive-control tests still pass;
      add fixed-target-bias and resolved-regime-convergence regressions.
- [ ] **Downstream:** this is the first genuine exercise of `extraction.py` /
      `scale_assignment.py` on a non-flat profile (flagged pending in 22a) — confirm
      the `zeta(r)` density bracket and areal-average handling behave, or report what
      breaks.

## Documentation

- Module docstring: record that the self-consistent target was tried (21a),
  destabilised the iteration (22b Finding 2 / lagging) and stalled at a structural
  ~1e-4 floor (22b, `newton_krylov`-confirmed), and was **replaced by a fixed
  FullInstanton target seeded to keep the outer loop near the solution** — so the
  reasoning is legible to someone who did not follow the prompt chain.
- Per-construct comments on the seed interpolation, the response-via-backward-pass,
  the fixed target, and the shared shooting component (what / why / failure-signature).

## Out of scope

- The SBP-SAT linear closure (prompts 20/21) — validated, unchanged.
- The `phi_end` target (22a) — prerequisite, unchanged.
- Re-running the *full* prompt-22 Study suite E (physics cross-checks) — do Study A
  (n-convergence) here as the correctness gate; the broader physics validation is a
  follow-on once a converged resolved-regime answer exists.
- Higher potentials (quartic/USR), the alpha scan, production-grid re-tuning.
