# Prompt 22a — Fix the degenerate `phi_end` target (physics change, sign-off gated)

**Scope:** one commit, **one line of production logic**, but a *physics-affecting*
change requiring explicit sign-off (per `CLAUDE.md` conventions) before it lands.
Fixes Finding 1 of the prompt-22 validation: the `GradientCoupledInstanton` final
boundary target is computed so that the noiseless background trajectory satisfies
the BVP exactly for every `delta_Nstar`, forcing `lambda = 0`, zero response
fields, and `msr_action ≡ 0`. Every prior acceptance result for this target
validated only this trivial branch.

## The bug (verified against source)

`ComputeTargets/GradientCoupledInstanton/` main compute function, line ~197:

```python
phi_end = traj.phi_at(N_offset + N_total)
```

With `N_offset = traj.N_end - N_init` and `N_total = (N_init - N_final) + delta_Nstar`,
this is `traj.phi_at(N_end - N_final + delta_Nstar)` — the target *moves with*
`delta_Nstar` to sit exactly where the background lands after integrating the full
`N_total`. So the background (integrated for `N_total` e-folds with `lambda=0`,
zero response sourcing) hits it identically: the instanton is degenerate.

`FullInstanton` (`ComputeTargets/FullInstanton.py` line ~650) does the correct
thing, and `delta_Nstar` is documented (`InflationConcepts/delta_Nstar.py`) as the
**excess** transition time:

```python
phi_final = traj.phi_at(N_end - float(self._N_final))   # FIXED, no delta_Nstar
N_total   = (N_init - N_final) + delta_Nstar             # excess duration only
```

The instanton is meant to travel the **same** field distance
(`phi_init → phi_at(N_end - N_final)`) in `delta_Nstar` **more** e-folds than the
background needs — a genuine excess-e-folds saddle. The production formula cancels
exactly that, by construction, at every `delta_Nstar`.

## The fix

```python
phi_end = traj.phi_at(traj.N_end - N_final)     # fixed target, matching FullInstanton
```

(equivalently `traj.phi_at(N_offset + (N_init - N_final))`). `N_total` is
**unchanged** — the excess duration was always correct; only the target argument
was wrong. Add a comment at the site recording that the target is deliberately
`delta_Nstar`-independent (fixed endpoint, excess *duration*), citing the
`FullInstanton` convention and the `delta_Nstar` = "excess transition time"
definition, so this is never "helpfully" re-coupled to `delta_Nstar` again.

- Confirm line ~197 is the **only** target-computation site in the compute path
  (grep; the class `compute()` at ~652 dispatches to it and does not recompute
  `phi_end`). The `N_offset + N_total > N_end` guard (line ~662) concerns the
  *duration* and is unchanged/correct — leave it.
- The `FullInstanton` seed for the lagged `g_pi_core` inside `solve_picard` takes
  `phi_end` as an argument, so it inherits the corrected target automatically —
  confirm, don't duplicate.

## Positive control — prove the degeneracy is gone WITHOUT needing the full solve

The `GradientCoupledInstanton` solve will **not** converge on the corrected target
(that is Finding 2, remediated separately in prompt 22b). So the non-triviality
must be demonstrated by proxies that don't require Picard convergence:

- [ ] **`lambda=0` is no longer a solution.** With the corrected target, the
      `lambda=0` shooting residual `|phi_1(N_total) - phi_end|` is non-zero and
      O(the field excursion), not O(tolerance) — i.e. the background no longer
      satisfies the final BC. (Before the fix it is exactly zero.)
- [ ] **Independent non-zero action.** `FullInstanton` (already convergent and
      validated) for the same `(phi_init, pi_init, phi_end, N_total)` returns
      `msr_action > 0`, strictly and well above the tolerance floor, across the
      `delta_Nstar ∈ [1.0, 3.0]` range. This is the positive control the whole
      test suite lacked — a case where triviality is impossible.
- [ ] Add a regression test asserting both of the above for the corrected target,
      and asserting the *old* formula produces the exact degeneracy (so the bug
      cannot silently return). This is the "positive control" that must exist in
      the suite from now on.

## Downstream re-validation (flag, do not fix here)

`extraction.py` and `scale_assignment.py` operate on the instanton's *final
profile*, which has been exactly flat (trivial) until now. Two known items were
tuned against that trivial branch and must be re-checked once a genuine converged
profile exists (i.e. after prompt 22b), not here:

- the `extract_zeta_profile` density-bracket tolerance fix from prompt 21a (it was
  "rejecting near-background solutions on floating-point noise" — behaviour on a
  genuinely non-flat `zeta(y)` is unverified);
- scale assignment's handling of a non-trivial `zeta(y)` (`r_max`, `r_peak`,
  the areal-average `C̄` denominator) — developed against flat profiles.

Note these in the commit message / design log as **pending re-validation**, so the
first genuine solve (22b) is understood to also be the first real test of the
extraction/scale-assignment path.

## Acceptance

- [ ] `phi_end` matches the `FullInstanton` fixed-target convention; `N_total`
      unchanged; single site, commented.
- [ ] Positive-control test green: `lambda=0` residual non-zero *and* FullInstanton
      `msr_action > 0` for the corrected target over `delta_Nstar ∈ [1,3]`; old
      formula asserted degenerate.
- [ ] Existing suite still passes (the SBP-SAT linear tests, FullInstanton, etc.
      are target-independent and should be unaffected).
- [ ] Downstream re-validation items flagged, not silently assumed fine.

## Out of scope

- The Picard/Newton non-convergence on the corrected target (Finding 2) — that is
  prompt 22b, and is why this prompt's positive control uses proxies rather than a
  full `GradientCoupledInstanton` solve.
- Re-running Studies A–E (blocked on 22b).
- Re-tuning extraction / scale assignment (blocked on a converged non-trivial
  profile from 22b).
