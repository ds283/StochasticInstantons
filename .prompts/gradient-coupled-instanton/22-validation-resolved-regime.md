# Prompt 22 — Validation of the SBP-SAT GradientCoupledInstanton in the resolved regime

**Scope:** a validation study, not a refactor. Prompts 21/21a delivered and
committed the SBP-SAT closure; the solve now runs to `n_collocation_points = 33`
with finite `msr_action`. But the only *correctness* check so far is agreement
with `FullInstanton` at `n=5`, which is the near-homogeneous limit (flat y-profile,
~1e-6 spread) — the regime where the onion model trivially reduces to a single
trajectory. This prompt establishes that the number the scheme produces *in the
regime it was built for* — a resolved, non-trivial y-profile — is correct. No
production code changes except, if needed, read-only diagnostic instrumentation
(persisted residuals / boundary quantities already largely available). Validate
the scheme **as implemented** (`tau = |A_core|`, the live-Neumann `g_phi`, the
lagged `g_pi`, the fallback-seed retry, the extraction tolerance fix) — not the
idealized derivation.

## Pick a non-trivial validation case first

The `n=5` agreement is uninformative because that profile is essentially flat.
Choose (and confirm) a case with a genuinely resolved y-profile: larger
`delta_Nstar` / closer to the collapse threshold, where the shell structure is
real. For `ΔN = N_init − N_final = 3.5`, the threshold is near
`delta_Nstar ≈ 0.55·ΔN ≈ 1.9`, so a case around `delta_Nstar ∈ [1.0, 3.0]` (e.g.
the `quadratic-asteroid-small.yaml` upper range) should give a profile whose y-spread
is orders of magnitude above the `~1e-6` near-background floor. **Gate:** confirm
the chosen case's y-profile spread at `n=17` is `≫` the `n=5` near-uniform level
before proceeding; if it isn't, pick a sharper case. Run all studies below on this
case (and ideally one second case at a different `delta_Nstar` for robustness).

## Study A — n-convergence of the answer (PRIMARY correctness evidence)

Compute the full solve for `n_collocation_points = 5, 7, 9, 11, 13, 17, 25, 33`
and tabulate `msr_action(n)` and the y-profile (`phi(y)`, `pi(y)` at the final N)
vs `n`.

- [ ] `msr_action(n)` **plateaus** — the change between successive `n` decreases
      and the value settles to a resolution-independent limit (report the relative
      change per refinement; it should fall, ideally toward the solver tolerance
      floor). "Finite" is not "converged"; a visible plateau is the acceptance bar.
- [ ] The y-profile converges pointwise as `n` grows (successive profiles overlie);
      no growing spatial ringing, no drift of the profile shape with `n`.
- [ ] If `msr_action(n)` is still drifting at `n=33`, that is the finding — report
      it and the drift rate; it would mean production `n` must go higher or the
      scheme has residual resolution-dependence to chase.

## Study B — Closure-independence (the key acceptance gate)

The lagged `g_pi` target must make the SAT penalty vanish at convergence, so the
answer cannot depend on the seed. Run the same case twice: `g_pi` seeded from the
**FullInstanton** profile, and seeded from the **background** trajectory.

- [ ] Converged `msr_action` agrees between the two seeds to solver tolerance, at a
      representative `n` (e.g. 17) and at `n=33`.
- [ ] The converged core `pi(N)` trajectories agree between seeds.
- [ ] The SAT penalty forcing `|tau·(pi_core − g_pi)|` at convergence is at the
      Picard-residual level (→ 0) — the direct evidence the lagged closure is inert
      at the fixed point. This especially matters for any parameter point that hit
      the **fallback-seed retry** path (a target-mismatched seed): confirm such
      points converge to the same answer as a clean seed, since a seed-dependent
      answer there would be silently wrong.

## Study C — Regularity, and τ-sensitivity of the two closures

The two fields' closures are asymmetric and must be checked differently:

- [ ] **`pi` (lagged target):** `(D·pi)_core → 0` at convergence *without* having
      been imposed — confirming `pi` inherits `phi`'s regularity through the
      dynamics (`pi = dphi/dN`), i.e. the well-posed "output, not imposed data"
      picture holds discretely.
- [ ] **`phi` (live-Neumann target):** the `g_phi` SAT imposes regularity only
      *weakly*, to an `O(1/tau)` boundary layer (flagged in the design note §6, and
      only checked at trivial `n=5`). At the resolved case and high `n`: confirm
      `(D·phi)_core` is small at convergence, and that the converged `msr_action` is
      **insensitive to `tau`** (re-run at, say, `tau = |A_core|` and `2|A_core|`;
      the answer must not move beyond tolerance). Unlike `pi`'s lagged closure, the
      `phi` closure does not vanish at convergence, so this τ-insensitivity is the
      check that its boundary layer is thin enough not to distort the answer where
      the profile is sharp.

## Study D — Genuine Picard convergence audit

The empirical `tau = |A_core|` (doubled from the derived `A_core/2`) was needed to
damp a Picard oscillation from `phi_core`'s new dynamical freedom. Confirm the
"converged" solves are genuinely converged, not a damped slow drift parked below
the former oscillation:

- [ ] Picard residual actually reaches the target tolerance (not stalling above it)
      for every `n` in Study A; report residual-vs-sweep for the hardest `n`.
- [ ] Outer Newton converges (not hitting `MAX_OUTER`); report iteration counts vs
      `n`.

## Study E — Physics sanity (independent-of-FullInstanton where possible)

Self-convergence (Study A) is the minimum; these are stronger where feasible:

- [ ] **Uniform-limit reduction across `n`, not just `n=5`.** At a *small*
      `delta_Nstar` (near-background) case, confirm `msr_action` → the FullInstanton
      action as `n` grows, at several `n` — so the FullInstanton agreement is a
      genuine limit, not an `n=5` coincidence.
- [ ] **Sensible dependence on profile sharpness.** Across a small `delta_Nstar`
      scan, the gradient-coupled action should differ from FullInstanton in a
      physically sensible, monotonic direction (the gradient/shell coupling is real
      physics content; its sign and growth with sharpness should be reportable and
      defensible, not erratic).
- [ ] **Optional, strongest:** reproduce an established qualitative result at
      production `n` that does not reference FullInstanton — e.g. the
      mass-independence of the collapse threshold `delta_Nstar_th(ΔN)` (independent
      of `N_final`), or the near-linear small-ΔN threshold `≈ 0.55·ΔN`. If a cheap
      slice of one of these reproduces, it is independent evidence the resolved-regime
      answer is physical.

## Deliverable

A short validation report (`.documents/gradient-coupled-instanton/22-validation.md`)
with: the chosen case(s); the `msr_action(n)` convergence table/plot; the two-seed
closure-independence result; the regularity and τ-sensitivity results; the Picard
convergence audit; and the physics-sanity findings. Persist the underlying data as
CSVs and the convergence/profile plots as PNGs, in the style of the existing
`compare_gradient_full.py` outputs. Run via the direct Ray-bypassing pattern the
suite already uses.

## Acceptance (task closeout)

The task is complete when: Study A shows a converged `msr_action` at production `n`;
Study B shows seed-independence to tolerance (including on a fallback-seed point);
Study C shows regularity emergent for `pi` and the `phi` closure τ-insensitive; and
Study D confirms genuine convergence. Study E is reported as available. If any of
A–D fails, the report says so plainly and scopes the remaining work — a clean
negative result here is a valid closeout, since the point is to know whether the
`n=33` number is trustworthy, not to force a green tick.

## Out of scope

- Any change to the closure or the physics equations (this validates the committed
  scheme; if a study fails, remediation is a separate prompt).
- The full production grid re-run / alpha scan / production-`n` re-tuning — those
  follow from, and are informed by, this study's converged-`n` finding.
- Response-sector or higher-potential (quartic/USR) extension — separate threads.
