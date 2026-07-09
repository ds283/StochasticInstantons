# Prompt 24b — λ-conversion seeding + corridor-bounded search, and trajectory validation

**Two coupled deliverables**, both flowing from one finding: `FullInstanton`'s `λ`
and `GradientCoupledInstanton`'s `λ` are **different quantities**, and GCI has been
bootstrapped with FI's value raw — wrong sign, ~3400× too large. Fixing that is
cheap and plausibly converts "converges when the backtracking cascade gets lucky"
into "converges by construction." Separately, the three converged solves from
prompt 24a have never been *looked at* — only their scalars are persisted — so their
physical validity is unverified.

Part A (seeding) is the consequential half. Part B (trajectory plot) is the check that
what we are converging to is real. Do A first; B validates both the old and new solves.

Audit-friendly comments throughout, as in 21/21a/23.

## The finding (verify against source before relying on it)

- `ComputeTargets/FullInstanton.py` (~line 149) sets the backward-pass terminal
  condition `P₁(N_total) = λ_FI`, `P₂(N_total) = 0`. **FI's `λ` *is* the terminal
  response value.**
- GCI's terminal condition (`response_rhs.terminal_response_state`) is
  `rfield_core = −λ_GCI / (w_core · μ(N_total))`, with `w_core` the LGL boundary
  weight and `μ = exp(−1.5·Δs)`.
- Equating the physical terminal response (`rfield ↔ P₁`, both conjugate to `φ`):

  ```
  λ_GCI  ≈  − λ_FI · w_core · μ(N_total) · E
  ```

  where `E` is a dimensionless **gradient-enhancement factor** (the core must fight
  the drag of outer shells pinned to the background, so it needs more terminal
  response than the homogeneous instanton).

Empirical support (prompt 24a Diagnostic 4, `m/Mp=1e-2`, `n=5`, `α=0.1`,
`w_core=0.1`, `Δs ≈ N_total + ln(1+α)`):

| δN★ | λ_FI | `−λ_FI·w_core·μ` | λ_GCI observed | `E` |
|---|---|---|---|---|
| 0.3 | 668.5 | −0.194 | −14.50 | 74.8 |
| 0.5 | 1061.4 | −0.228 | −15.47 | 67.8 |
| 0.7 | 1419.2 | −0.226 | −15.63 | 69.2 |

Note the conversion explains the otherwise-puzzling near-constancy of `λ_GCI`
(λ_FI grows, μ shrinks, the product cancels) and the sign flip (GCI's own minus sign
— a convention, not a bug). **`E` is not universal**: the prompt-22c small fixture
(`N_total=0.15, α=0.05`) implies `E ≈ 13`, not ~70. So the conversion delivers the
**sign and ~3 orders of magnitude**, not the exact root — enough to seed, not enough
to skip the search.

**Verify, don't trust this reconstruction.** Confirm from source: (i) FI's terminal
convention; (ii) GCI's `w_core`/`μ` factors and the sign; (iii) that `rfield` is the
`P₁`-analogue (conjugate to `φ`), not `rmom`; (iv) the `Δs(N)` formula (the table above
assumed `Δs ≈ N + ln(1+α)`, validated against `stiffness_spectrum.csv`'s `delta_s_N`
column). If any differs, re-derive the conversion and say so — the *structure* of the
fix survives, the constants may not.

## The feasible-λ corridor, in closed form

The forward blow-up mode is `H²_local < 0` (⟺ `ε > 1`), driven by the noise source
`D₁₁ · λ · r̃`. Prompt 24a Diagnostic 2 established `max|r̃| = |rfield|/λ ≈ 9155`,
constant across five orders of magnitude in `λ` (Part B linearity confirmed). Hence

```
|λ|  ≲  λ_c  ≈  1 / ( D₁₁ · max|r̃| )        and      max|r̃| ≈ 2.7 / (w_core · μ)
```

Check: `m/Mp=1e-2` → `H² ≈ 1.24e-3`, `D₁₁ = H²/(8π²) ≈ 1.57e-5` → `λ_c ≈ 6.9`.
Observed: `λ=+1.9` converges, `λ=+19` diverges. ✓ (The negative side is ~2–3× wider —
`−15.6` converges, `−37.5` fails — since the sign of the kick decides whether it drives
`ε` toward 1 or away. Treat the corridor as **asymmetric**; do not assume `±λ_c`.)

Both `λ_c` and the seed are therefore computable **a priori**, for any potential/grid
parameters, from `D₁₁`, `w_core`, `μ(N_total)`, `λ_FI`.

## Part A — Seeding and search (production change)

1. **Convert the seed.** Replace the raw `+λ_FI` bootstrap aim with
   `λ_seed = −λ_FI · w_core · μ(N_total)` (i.e. `E=1`), which is comfortably inside the
   corridor and on the correct sign. Comment the derivation at the call site.
2. **Bound the search by the corridor.** Compute `λ_c` (both signs, allowing asymmetry)
   before searching; the shooting solver must never propose `|λ|` beyond it, so the
   `blown-up` evaluations that currently dominate the Armijo cascade cannot occur.
   This replaces "propose, blow up, backtrack" with "propose only inside the feasible
   set."
3. **Expand outward from the seed.** Since `E ∈ [~10, ~100]` and is not known a priori,
   bracket the root by expanding from `λ_seed` (geometric expansion, corridor-clamped)
   until the residual changes sign, then hand the bracket to the existing hardened
   secant/Armijo/trust-region solver. Log `E = λ_root / λ_seed` per solve — it is a
   physically interesting quantity (gradient drag) and a cheap regression signal.
4. **Retire the empirical fudge.** `−0.015·λ_FI` (24a's recommendation) is this scaling
   law seen sideways; it should not be hard-coded. Derive, don't fit.

## Part B — Trajectory validation (diagnostic; persist grids, then plot)

The 24a harness (`diagnose_24a_convergence_floor.py`) reconstructs the solves but
persists only scalars. Extend it to persist the grids, and plot, for each converged
point (the three existing `δN★ ∈ {0.3,0.5,0.7}` solves, and any new ones from Part A):

- [ ] `φ_core(N)` and `π_core(N)` (GCI, `y=+1`) overlaid on FI's `φ₁(N)`, `φ₂(N)`.
- [ ] **`ε(N) = ½π²/Mp²` for both, with a reference line at `ε=1`.** This is the key
      physical check: the root sits only ~1.3–2.4× inside the negative corridor edge, so
      if `ε` climbs toward 1 anywhere along the GCI core trajectory, the solution is
      skirting the `H²<0` boundary and its action is suspect. FI's `ε` should stay well
      below 1 throughout.
- [ ] The **y-profile** `φ(y)`, `π(y)` at final `N` — confirm the shell structure is
      genuinely resolved (non-flat), not the near-uniform profile of the trivial branch.
- [ ] `S_GCI/S_FI` vs `δN★` (observed 18.8 → 23.5 → 37.4). Gradient drag makes
      `S_GCI > S_FI` the right sign; comment on whether the growth rate is defensible.

## Part C — Retry what was called blocked

With the seed fixed, re-attempt the cases prior campaigns concluded were structurally
blocked, **before** anyone writes them into the record as an operating-envelope wall:

- [ ] `δN★ = 1.0` at `m/Mp ∈ {1e-2, 1e-3, 1e-4, 1e-5}` (prompt 24 Phase A's four "no"s).
- [ ] `δN★ = 0.2` (24a's non-monotonic failure — expected to be search-path luck, and to
      converge once the seed is right; if it still fails, that is informative).
- [ ] `n ≥ 9`, `n ≥ 17` (22b/22c caps), at a converged `δN★`.
- [ ] If any still fail, classify with the existing `bailout_tag` machinery and report
      the mechanism — a clean negative remains valid, but it must now be a negative
      *given a correct seed*.

## Acceptance

- [ ] Conversion verified against source (or re-derived and documented if it differs).
- [ ] `λ_seed` and the corridor bound `λ_c` computed a priori; no evaluation is ever
      proposed outside the corridor; the `−0.015·λ_FI` fudge is gone.
- [ ] The three known-converged points still converge, to the **same** `λ` and
      `msr_action` (within tolerance) — the seeding change must not move the answer,
      only how reliably it is found. Report iteration counts before/after.
- [ ] `δN★ = 0.2` converges (the search-path-luck hypothesis, falsifiable).
- [ ] Trajectory plots produced; `ε(N)` reported for GCI and FI. **If `ε` approaches 1
      along the GCI core trajectory, stop and report** — that would mean the converged
      solutions are boundary-skirting and the physics needs revisiting before any
      science use.
- [ ] Part C results, each classified.
- [ ] `OUTER_TOL = max(atol·1e6, 1e-2)` is ~1% of the field excursion (≈0.86 here) —
      loose for a stationary quantity. Check whether tightening it moves `msr_action`;
      if it does, the tolerance is doing physics and should be revisited.

## Out of scope

- The self-consistent / two-pass target (24a Diagnostic 3b's clean negative stands;
  it diverges, reproducing prompt 22's undamped-target mechanism).
- Any new numerical closure. Note that if Part A makes the corridor a non-issue for
  seeding but the *root itself* still sits near the corridor edge at larger `δN★`, that
  is a genuine physical limit of this formulation (the required response drives `ε→1`),
  and is a separate, important conversation — not a numerics fix.
- The broad convergence map; the science campaign.
