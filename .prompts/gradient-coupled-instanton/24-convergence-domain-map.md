# Prompt 24 — Convergence-domain map + FullInstanton-consistency campaign

**Scope:** a characterisation campaign, not a feature. After prompts 20–23 the
`GradientCoupledInstanton` (GCI) pipeline has many validated *pieces* but no
*map*: it is not established, systematically, for which `(potential scale, ΔN,
δN★, n_collocation_points, α)` the full solve converges, nor where its output is
physically sensible (in slow-roll it should resemble — not necessarily equal —
the corresponding `FullInstanton` (FI) solution). This prompt produces that map.
It is expected to surface bugs (notably the resolved-regime "bootstrap"
non-convergence prompt 22c/23 flagged but did not chase); fixing small blockers
that stand between here and a readable map is in scope, large new closures are not.

Run through the **actual `main.py` / datastore pipeline**, not ad-hoc toy scripts
— this is a compute campaign and the toy-script attempts are exactly what produced
the murky "bootstrap issue" reports. Where a fast standalone reproduction is useful
for debugging a single failing point, that is fine, but the map itself comes from
real pipeline runs.

## Phase 0 — Audit what is already verified (before running anything new)

Reconstruct, from the test suite and the 21/21a/22*/23 design notes, a single table
of the *current* verified status, so the campaign extends a known baseline rather
than re-discovering it:

- [ ] Which `(N_init, N_final, δN★, n, α, potential)` points have a **passing**
      end-to-end GCI test, and what each asserts (converged? `msr_action>0`? matches
      FI? — distinguish these; several "passing" cases are near-trivial `λ≈0`).
- [ ] Which are **capped/xfailed** and why (e.g. 22c's `n=9` cap, 22b's `n≥17` cap).
- [ ] The known failure modes named so far: astronomic-λ response (pre-23),
      fixed-target bias (22c Finding 3), bootstrap non-convergence (22c/23), n=9.
- [ ] Note explicitly which points, if any, have a **non-trivial** (`λ≠0`,
      resolved-profile) converged solve — the honest answer is currently "none at
      production scale," and the map's job is to change that.

Deliverable: a short "verified-status baseline" section. This directly answers
"what has actually been checked" before adding anything.

## Phase 1 — Unblock and characterise the resolved-regime bootstrap failure

Take one resolved-regime point (`N_init=19.5, N_final=16.0, δN★=1.0`, quadratic
`m/Mp=1e-5`) through the real pipeline and diagnose the outer-loop non-convergence
Claude Code hit:

- [ ] Reproduce it via `main.py` (not a toy script) and characterise it: is it the
      `bootstrap_target` first-step aim, the shooting on the astronomic λ, the
      fixed-target bias at that λ, or the Part-B-rescaled response feedback? The
      shared `ShootingSolver` and `picard_inner` already log enough to localise it;
      add read-only instrumentation if not.
- [ ] Fix it if it is a small, well-localised blocker (a bootstrap/shooting-config
      issue of the kind 22b/22c already dealt with). If it is a genuine new
      structural gap, **stop and report** — do not force it; scope it as a follow-on.
- [ ] Acceptance for Phase 1: either one genuinely converged non-trivial
      resolved-regime solve exists (`λ≈λ_FI≈1.9e9`, `msr_action>0`, finite), or a
      crisp statement of what blocks it.

## Phase 2 — The convergence map

Sweep and record convergence + diagnostics for each point, via the pipeline. Use a
coarse grid first to find the boundaries, then refine near them.

**Axes (start coarse):**
- **Potential / diffusion scale** — vary `m/Mp` across e.g. `{1e-2, 1e-3, 1e-4,
  1e-5}`. This is the single most informative axis: `λ ~ 1/D ~ 1/H² ` grows sharply
  as `m` shrinks, so this walks the solve from a mild-λ, easy regime into the
  astronomic-λ resolved regime, and locates where convergence degrades. The larger-`m`
  end is also the clean **FI-comparison control** (moderate λ, both solvers happy).
- **δN★** — `{0.1, 0.5, 1.0, 2.0, 3.0}`: trivial/near-background → resolved.
- **n_collocation_points** — `{5, 7, 9, 11, 13, 17, 33}`: the convergence-vs-resolution
  behaviour, and whether the 22c `n=9` cap generalises or was fixture-specific.
- **α-regularization** — `{0.001, 0.01, 0.05, 0.1}`: its effect on stiffness /
  conditioning near `N_init`.
- (ΔN can stay fixed at 3.5 for the first pass; add a second ΔN only if the map
  looks ΔN-sensitive.)

**Record per point:** converged (Y/N), outer/inner iteration counts, final residual,
`λ`, `msr_action`, wall-clock, and the failure mode if not converged (ODE `H_sq<0`,
step-death, outer-loop stall, inner floor, bootstrap). Persist as a CSV; the map is a
table before it is a plot.

**Deliverable:** a convergence map — which regions converge, which fail and *why* —
with the failure modes attributed to the named causes, so the boundary of GCI's
current domain of applicability is explicit.

## Phase 3 — FullInstanton-consistency (sanity of the output)

For the converged points, compare against FI at the same
`(phi_init, pi_init, phi_end, N_total)`:

- [ ] **Agreement where expected:** in the near-trivial / slow-roll, small-`δN★`
      limit, GCI's core trajectory, `λ`, and `msr_action` should closely track FI
      (the onion structure is negligible there). Confirm, across `n`, that this is a
      genuine limit, not an `n=5` coincidence.
- [ ] **Sensible divergence where expected:** as `δN★` grows and the y-profile
      resolves, GCI should differ from FI — but *smoothly and in a physically
      defensible direction/magnitude* (the gradient/compaction structure is the
      onion model's content). Report the sign and size of `S_GCI − S_FI` vs `δN★`
      and confirm it is monotone/smooth, not erratic.
- [ ] **n-convergence of the difference:** the GCI–FI gap should itself converge in
      `n`, not drift — otherwise the "difference" is a resolution artefact.
- [ ] **Fixed-target bias, in the physical regime (22c Finding 3, still open):** at a
      converged resolved point (where `λ_FI` is a good same-sign proxy), re-measure
      the fixed-target bias (perturb the target, watch `msr_action`). Report whether
      it is now small; if not, this is where the pre-agreed two-pass outer
      self-consistency (prompt 23) gets scoped.
- [ ] **Downstream sanity:** the first genuine `extraction.py`/`scale_assignment.py`
      runs on a resolved, non-flat `zeta(y)` — confirm `C(r)`/`C̄(r)`, `r_max`,
      `r_peak` come out sensible, or report what breaks.

## Acceptance

- [ ] Phase 0 baseline table produced.
- [ ] Phase 1: a converged non-trivial resolved-regime solve exists, or the blocker
      is crisply scoped.
- [ ] Phase 2: a convergence map (CSV + short narrative) with failure modes attributed
      — the explicit statement of *where GCI converges*.
- [ ] Phase 3: FI-consistency demonstrated in the limit where it should hold, and the
      GCI–FI difference characterised (sign, magnitude, `n`-convergence) where it
      should not; fixed-target bias re-measured in the physical regime.
- [ ] Clean-negative remains valid: if large regions do not converge, the map *is* the
      result — the goal is to know the domain, not to force universal convergence.

## Out of scope

- New numerical closures (forward/response SBP-SAT are done; the two-pass
  self-consistency is scoped only if Phase 3 shows the bias demands it).
- Higher potentials beyond quadratic (quartic/USR) — the map here is the prerequisite.
- Physics production runs / the science campaign — this establishes the trustworthy
  operating envelope those will run inside.
