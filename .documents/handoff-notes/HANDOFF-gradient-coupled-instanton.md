# GradientCoupledInstanton — handoff brief

**Date:** 9 July 2026  
**Prepared by:** David Seery and Claude (Opus 4.8)  
**Purpose.** Everything a fresh conversation needs to pick up the
`GradientCoupledInstanton` (GCI) workstream without re-deriving what took prompts
20–24b to establish. Read this first; it supersedes any stale summary.

**Status in one line.** The numerical scheme is fixed and GCI now produces genuine
non-trivial converged solves — but *only* at `n_collocation_points = 5`,
`m/Mp = 1e-2`, `δN★ ≤ 0.7`. There is still **zero n-convergence evidence**, so no
result is yet defensible as physics.

---

## 1. What is verified, and where

Converged, non-trivial (`λ≠0`, `msr_action>0`) GCI solves exist at:
`N_init=19.5, N_final=16.0, m/Mp=1e-2, n=5, α=0.1`, quadratic potential:

| δN★ | λ_GCI   | S_GCI  | S_GCI/S_FI | E = λ/λ_seed | max ε |
|-----|---------|--------|------------|--------------|-------|
| 0.2 | −11.514 | 159.5  | 15.3       | 64.4         | 0.033 |
| 0.3 | −13.937 | 396.4  | 17.3       | 62.0         | 0.038 |
| 0.5 | −15.515 | 1425.3 | 23.6       | 58.6         | 0.048 |
| 0.7 | −15.698 | 4255.7 | 37.8       | 59.9         | 0.056 |

Each solves in 8–13 s, 3 outer iterations. `ε ≪ 1` everywhere — the solutions are
**not** skirting the `H²<0` boundary.

**Does not converge:** `δN★ = 1.0` at every mass `{1e-2, 1e-3, 1e-4, 1e-5}` (tagged
`floored`, not budget-limited); `n ≥ 9` and `n ≥ 17` at any δN★ (tagged `floored`).

---

## 2. Hard-won facts worth carrying verbatim

**λ_FI and λ_GCI are different quantities.** `FullInstanton` sets terminal
`P₁(N_total) = λ_FI` (λ *is* the terminal response). GCI sets
`rfield_core = −λ_GCI/(w_core·μ)`. Hence

```
λ_GCI  =  − λ_FI · w_core · μ(N_total) · E
w_core = 2/(n_max(n_max+1))          # LGL boundary weight
μ(N)   = exp(−1.5·Δs(N)),  Δs(N) ≈ N + ln(1+α)
E ≈ 61 ± 3   (gradient-drag enhancement; NOT universal — ≈13 on the small 22c fixture)
```

Seeding GCI at raw `+λ_FI` (which the code did until 24b) is wrong in sign and
~3400× too large. This single defect caused: 22c's "λ_FI is a poor proxy," the
Armijo cascades that dominated prompt-24 Phase A, and the non-monotonic
`δN★=0.2 fails / 0.3 succeeds` pattern (search-path luck, now cured).

**Feasible-λ corridor, computable a priori.** Forward blow-up is `H²_local<0`
(⟺ `ε>1`), driven by the noise source `D₁₁·λ·r̃`:

```
|λ| ≲ κ / (D₁₁ · max|r̃|),   κ = 1,   D₁₁ = H²/(8π²)
max|r̃| = 1/(w_core · μ(N_total))     # i.e. the TERMINAL CORE value
negative side ≈ 2.5× wider than positive (asymmetric — do not assume ±λ_c)
```

`κ=1` has physical content: **the optimal noise `r̃` peaks at the terminal core and
decreases backward.** It does not grow backward. (An earlier claim of mine that it
did, and a "2.7" constant, were wrong; Claude Code caught both.)

**Action is quadratic in λ locally:** `dlnS/dlnλ ≈ 2`. Root precision propagates
*squared* into `msr_action`. An 8% shift in S at δN★=0.3 between 24a and 24b came
purely from a tighter root-find.

**Response sector is integrated backward**, which flips which eigenvalue sign is
catastrophic. Its backward-relevant abscissa is already bounded in `n_max`; the
forward sector's SBP-SAT closure must **not** be ported there (prompt 23 Part A,
clean negative — porting it makes stiffness ~23× worse).

**Response is exactly linear in the response fields**, so `r = λ·r̃` exactly; prompt
23 Part B integrates the `O(1)` `r̃` and reconstructs physical grids once. Valid at
tree level / Gaussian noise; would break under loop corrections to the MSR action
(Schwinger–Keldysh), which is a real but distant concern.

---

## 3. Traps that produced false positives (do not repeat)

1. **The `phi_end` degeneracy.** Until prompt 22a, `phi_end = traj.phi_at(N_offset +
   N_total)` made the noiseless background an exact BVP solution for *every* δN★ →
   `λ=0`, `msr_action≡0`. **Every acceptance result from prompts 19–21a validated
   only this trivial branch**, including "matches FullInstanton to 1e-8" (both sides
   computed the background). Fixed to `traj.phi_at(N_end − N_final)`.
   → **Every future acceptance test must include a positive control asserting
   `msr_action > 0` on a case where triviality is impossible.**
2. **`abs()` hid the instability.** The stiffness sweep reported
   `max_abs_re_lambda`, so a spurious `+1500` was indistinguishable from a stable
   `−1500`. Fixed in prompt 20 (`spectral_abscissa`, signed; `n_rhp`). The right
   acceptance criterion for any closure is **abscissa bounded in `n`**, not
   `abscissa ≤ 0` and not `n_rhp = 0`.
3. **"Converged" ≠ "non-trivial."** Several passing tests assert convergence on the
   `λ=0` branch. Distinguish these explicitly.
4. **`OUTER_TOL = max(atol·1e6, 1e-2)` binds silently** when the root-find lacks a
   bracket. Tolerance sweeps showing "no change" only prove it isn't binding *there*.
5. **Self-consistent / lagged SAT targets diverge.** Lagged `g_pi` (22 Finding 2),
   Anderson (~1e-4 floor, `newton_krylov`-confirmed structural), and the two-pass
   outer self-consistency (24a D3b: 0.057→0.082→0.418) are all clean negatives.
   The fixed FullInstanton target is the working closure.

---

## 4. The open question, and the immediate next action

**Do not write the physics narrative yet.** The trajectory plots (24b) show
φ_core/π_core oscillating ~2–3 times over the transition, and a tempting reading is
episodic assembly: gradient drag, then a noise burst driving the core back up the
potential, repeat. Four things argue it may instead be under-resolution:

- The y-profile shows systematic node-to-node alternation (~5–7% of amplitude) — the
  classic highest-spectral-mode signature.
- All converged points are `n=5` (3 interior shells); oscillation count ≈ shell count.
- The violent transient sits at `N≈0`, where `Δs = ln(1+α) ≈ 0.095`, so
  `A_core ≈ 21` **and** `τ = |A_core| ≈ 21`. But `r̃` (the noise) is *weakest* there
  (κ=1, above). Transient and noise do not line up.
- **Least-action argument (sharpest):** noise cost `∫D r̃² dN` is positive-definite,
  so an oscillating optimal noise is strictly more expensive than a smooth one. A
  genuine minimiser should not ring. `S_GCI/S_FI` climbing 15→38 while `E` stays
  flat at ~61 is more consistent with *ringing cost* than with a physical drag.

**Next, in order (solves are now 8–13 s; these are minutes, not campaigns):**

1. **τ-sensitivity** on the four converged points: `τ ∈ {A_c/2, |A_c|, 2|A_c|}`.
   τ is a numerical penalty; converged physics must not depend on it. This is prompt
   21's Study-C check, never run on a non-trivial solution.
2. **α-sensitivity**: `α ∈ {0.01, 0.05, 0.1, 0.3}`. If the transient and `S` scale
   like `1/ln(1+α)`, it is the initial layer, not physics.
3. **Plot `r̃(y,N)`** — if the optimal noise itself oscillates, the question is settled
   directly.
4. **Unblock `n ≥ 9`.** Hypothesis: LGL nodes cluster at the boundaries as `n` grows,
   so `n≥9` is the first resolution that *sees* the core boundary layer imposed by
   `τ ~ 2/Δs`, and the inner Picard dies. Uncomfortable corollary: **n=5 may converge
   because it cannot resolve the layer.** Without n≥9 there is no n-convergence, and
   without that there is no correctness evidence at all.

Also still open: the fixed-target bias (13× amplification, 22c Finding 3) has never
been measured in the physical regime; `δN★=1.0`'s floor is attributed to it but
unproven; `extraction.py` / `scale_assignment.py` have never run on a non-flat
profile.

---

## 5. What to upload to the new conversation

Project knowledge (source, `onion_model.tex`, `FILE_MAP.md`, `NUMERICAL_SCHEMES.md`)
persists — no need to re-upload. Add:

- **This brief.**
- Design notes: `21-sbp-sat-design-note.md`, `21a-production-port-notes.md`,
  `22-validation.md`, `22b-convergent-iteration-design-note.md`,
  `22c-fullinstanton-seed-fixed-target.md`, `23-response-sbp-sat-design-note.md`,
  `24-phase0-baseline.md`, `24-phase-a-deep-dive.md`, `24-campaign-closeout.md`,
  `24a-diagnose-convergence-floor.md`, `24b-...-trajectory-validation.md`.
- The 24b trajectory plots (`trajectory_m0_01_dNstar*.png`) and
  `S_ratio_vs_delta_Nstar.png` — the oscillation question is visual.
- The reusable harness `diagnose_24a_convergence_floor.py` (it already reconstructs
  solves and now persists grids; the τ/α sweeps are small extensions of it).

Prompts themselves are lower value than the design notes — the notes record what was
*found*, including the clean negatives, which is what stops rediscovery.

---

## 6. Working conventions (unchanged)

Claude drafts numbered `.prompts/<feature>/XX-identifier.md` specs — single commit
scope, explicit acceptance criteria with checkboxes, explicit out-of-scope, executed
by Claude Code in a separate session, results reviewed here for physics consistency.
Diagnostic-first: derive/measure before changing the scheme. Validation runs in fresh
sessions. Implementation code carries comments sufficient for audit by a
non-specialist in numerical methods. Clean negatives are valid results and are to be
reported, not forced past.
