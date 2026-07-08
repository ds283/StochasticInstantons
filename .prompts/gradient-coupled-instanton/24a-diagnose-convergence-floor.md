# Prompt 24a — Diagnose the δN★=1 floor: one closure-fix away, or genuinely blocked?

**A cheap, instrumented diagnostic — not a sweep.** Prompt 24 Phase A found that
GCI does not converge at `(δN★=1.0, n=5, α=0.1, N_init=19.5, N_final=16.0)` across
`m/Mp ∈ {1e-2…1e-5}`, and its closeout is at risk of being read as "operating-envelope
boundary." That reading is premature: the evidence is a to-do list, not a wall.
Specifically —

- the **mildest mass (`m=1e-2`) was CPU-contention-confounded** (bit-identical
  internals under a doubled budget, load average ~700 on a shared laptop) — the point
  most likely to converge never got a fair run;
- the residual **floors scale with `λ`** (~0.056 at `m=1e-3`, ~0.24 at `m=1e-4`/`1e-5`),
  the signature of the **known fixed-target bias** (22c Finding 3's 13× amplification)
  acting at the outer level — for which the **two-pass outer self-consistency was
  pre-scoped** (22c/23) and never tried;
- the `m=1e-4`/`1e-5` residual **barely moves at all** (0.2455→0.2454), which is a
  *different* symptom (outer shooting insensitive to `λ`) than the `m=1e-3` move-then-floor,
  and points at a possible **inner-solve / response-sector failure**, undiagnosed;
- **Part B's λ-rescaling was never validated end-to-end** (23 note: unit-tested in
  isolation only; Phase A was meant to be that validation and wasn't); and
- the **easier small-`δN★` region between the working trivial branch (`0.1`) and the
  first tested failure (`1.0`) is entirely untested** — the most likely place for a
  first genuine non-trivial convergence.

This prompt runs a handful of instrumented points to distinguish **"one closure-fix
away"** from **"genuinely blocked,"** and ideally to produce the project's first
non-trivial (`λ≠0`, `msr_action>0`) converged GCI solve.

**Machine note:** the residual-behaviour diagnostics (1–3 below) read
*deterministic* internals — `evaluate(λ)` values, inner-solve convergence, whether a
floor tracks a target perturbation — and are therefore **machine-independent**; run
them anywhere. Only the `m=1e-2` *budget-limitedness* question (does it converge given
enough wall-clock) needs an uncontended machine, and it is secondary.

## Diagnostic 1 — Characterise `evaluate(λ)` at each mass (the central one)

For each `m ∈ {1e-2, 1e-3, 1e-4, 1e-5}` at the Phase-A slice: **sweep the outer
shooting residual `evaluate(λ)` over a range of `λ` bracketing `λ_FI` and 0**, and at
each `λ` record *both* the residual *and the inner Picard solve's own convergence
status* (converged / floored / blown-up, inner residual). This one cheap sweep
(a dozen `λ` per mass, no outer root-find) answers most of the open questions:

- [ ] **Is the root-find well-posed?** Is `evaluate(λ)` smooth, monotone, and does it
      cross zero? Where is the root relative to `λ_FI` (i.e. is the bootstrap *aim*
      good, or is the true GCI root far from FullInstanton's)?
- [ ] **Inner vs outer.** Does the inner solve converge at each fixed `λ`, or floor at
      every `λ`? A floor at every `λ` is an inner/response problem masquerading as an
      outer one.
- [ ] **Explain the two symptoms.** Is `m=1e-4`/`1e-5`'s flat outer residual because
      `evaluate(λ)` is genuinely flat (root-find ill-posed — the response isn't
      producing usable `λ`-sensitivity) or because the inner solve fails identically at
      every `λ`? These are different diseases; name which.

## Diagnostic 2 — Is Part B (λ-rescaling) actually active and correct end-to-end?

The 23 note deferred end-to-end validation of `r = λ·r̃`. Confirm, in the *real*
`m=1e-4`/`1e-5` Picard/shooting path (not the isolated unit test):

- [ ] The rescaled path is **engaged** — `lam` is threaded through, the backward pass
      integrates the `O(1)` `r̃` (not `λ·r̃`), and the forward feedback uses
      `(D·λ)·r̃`. Instrument and confirm, don't assume; a silent default of `lam=1.0`
      somewhere in this path would reintroduce the astronomic-scale response and alone
      explain a flat/failed `evaluate(λ)`.
- [ ] The reconstructed physical response is **finite and sensible** (no overflow, NaN,
      or collapse to zero) at these `λ`, and its `λ`-dependence actually reaches
      `evaluate(λ)`.

If Part B is inactive or broken in the loop, that is the finding — it is a concrete,
localised defect, and the deferred Finding-5 validation finally gets closed.

## Diagnostic 3 — Is the `m=1e-3` floor the fixed-target bias, and does two-pass cure it?

At `m=1e-3` (where `evaluate(λ)` moves before flooring):

- [ ] **Direct bias test.** Perturb the fixed `g_pi` target; check whether the outer
      floor **tracks** the perturbation. If it does, the floor *is* the fixed-target
      bias (22c Finding 3 at the outer level).
- [ ] **Prototype the two-pass fix.** Wrap the solve in an outer self-consistency loop:
      solve with the fixed FullInstanton `g_pi` target → set the new target to the
      resulting core `pi_core(N)` → re-solve → iterate a few outer passes. Does the
      residual **push below the floor** across passes? At the outer fixed point the
      target equals the solution, so the bias vanishes by construction — if the floor
      drops toward tolerance, the pre-scoped two-pass closure is the fix, and a
      follow-on can productionise it. Keep this a lightweight prototype, not a
      production wiring.

## Diagnostic 4 — Establish the first non-trivial convergence (small δN★)

Walk `δN★ ∈ {0.2, 0.3, 0.5, 0.7}` at a tractable mass (`m=1e-2` or `1e-3`), `n=5`,
`α=0.1`, generous-but-bounded budget:

- [ ] Find the **first `δN★` that produces a genuine `λ≠0`, `msr_action>0` converged
      solve** — the project's first non-trivial GCI convergence, and the `δN★`-boundary
      of the currently-reachable region.
- [ ] If one converges, sanity-check it against FullInstanton (core trajectory / `λ` /
      `msr_action` similar, not equal) — the first real FI-consistency data point.

## Deliverable / acceptance

- [ ] A **classification of the δN★=1 floor** into (at least) one of: (a) fixed-target
      bias, curable by two-pass self-consistency (with Diagnostic-3 evidence); (b) Part
      B inactive/broken end-to-end (with the specific defect, Diagnostic 2); (c)
      inner-solve/response failure at fixed `λ` (a deeper response-sector problem,
      Diagnostic 1); (d) bootstrap-aim problem (`evaluate(λ)` well-posed but root far
      from `λ_FI`, Diagnostic 1). The mechanism may differ by mass — say so.
- [ ] The explicit **"one fix away" vs "genuinely blocked"** verdict this campaign was
      meant to deliver, per mass, backed by the diagnostics rather than asserted.
- [ ] The **`δN★`-boundary of first non-trivial convergence** (Diagnostic 4), and — if
      any point converges — the first FI-consistency check.
- [ ] `m=1e-2` budget-limitedness re-tested on an uncontended machine *if* Diagnostic 1
      shows its `evaluate(λ)` is well-posed (i.e. worth spending the wall-clock on);
      skip if Diagnostic 1 shows the root-find is ill-posed there anyway.
- [ ] Clean-negative remains valid: if the diagnostics show a genuine structural block
      (e.g. inner solve fails at every `λ` for reasons Part B doesn't fix), that is a
      real result — but it must be *shown*, not inferred from Phase A's floors.

## Out of scope

- The broad convergence map (only worth it once a convergent path exists).
- Production-wiring the two-pass self-consistency (this prompt prototypes and tests
  whether it is warranted; a follow-on implements it if Diagnostic 3 says yes).
- Any new numerical closure beyond what Diagnostic 2 might reveal as a Part-B defect
  fix.
- Higher potentials / the science campaign.
