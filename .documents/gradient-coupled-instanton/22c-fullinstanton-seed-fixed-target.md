# Prompt 22c — FullInstanton seeding + fixed SAT target for the coupled instanton

Prompt: `.prompts/gradient-coupled-instanton/22c-fullinstanton-seed-fixed-target.md`.
Builds on commit `c8c4a98` (prompt 22b), which is kept, not reverted: the
outer-Newton hardening (secant/Armijo/trust-region) and Finding-2 diagnosis
(lagging is the divergence's cause) both stand. This prompt makes the two
coupled changes 22b's own evidence pointed to — abandon the self-consistent
`g_pi_core` target for a fixed one, and seed the solve from FullInstanton —
plus a third piece the prompt asked for (a shared shooting component) that
turned out to be load-bearing once genuinely large/mismatched seeds were
exercised.

**Diagnostic-first was followed in spirit, not letter.** The seeding and
fixed-target logic had to be written into `picard.py` before it could be
exercised at all (there is no way to "prototype" an onion-interpolated
forward-field seed without the interpolation code existing), so Phase 1
here means "implement, then stress-test before finalising defaults/tests/
docs" rather than "prototype in a throwaway harness, then port." Every
finding below was reproduced with a standalone script
(`out-gradient-coupled-stiffness/scripts/`) or directly via `solve_picard`/
`_compute_full_instanton._function`, none of it hidden inside production
code paths that aren't otherwise tested.

## What shipped

1. **Fixed `pi_core` SAT target, default.** `DEFAULT_SAT_THETA` changed
   `1.0 -> 0.0`, `DEFAULT_ANDERSON_M` changed `5 -> 0`. Together these make
   `_AndersonMixer.update()` an exact identity (see its own docstring), so
   `g_pi_core` is set once, from the FullInstanton seed, and never updated
   again for the whole solve. The self-consistent/Anderson path (prompt 22b)
   is **dormant**, reachable only by passing `theta=1.0, anderson_m=5`
   explicitly, kept for regression comparison.
2. **FullInstanton seed, widened scope.** `_fetch_full_instanton_profile`
   (replacing `_seed_pi_core_values`) now returns `phi1`, `phi2`, and
   `lambda_FI`, feeding: the fixed target (`phi2`), the sweep-0
   onion-interpolated forward-field guess (`phi1` as the core endmember,
   the noiseless background as the exterior endmember,
   `_seed_profile_weights` with `seed_profile="linear"` default), and the
   outer loop's `bootstrap_target` (see below). Same three-tier
   fetch-then-fallback preference order as before (supplied dict / inline
   delegate / background trajectory), extended to carry `final_lambda`
   through all three tiers.
3. **Shared shooting component**, `Numerics/ShootingSolver.py`. 22b's own
   secant + Armijo backtracking + trust-region outer loop, factored out of
   `picard.py` and reused by `ComputeTargets/FullInstanton.py` (replacing
   its finite-difference Newton probe, prompt 22 Finding 1b). Two additions
   were needed once genuinely exercised (see Findings below):
   `stall_growth`-driven trust-region escalation, and `bootstrap_target`
   (an informed first-step aim, not a jump to an unconditionally-trusted
   starting point).
4. **21a's retry-band-aid removed.** `solve_picard`/`_solve_picard_once`
   collapsed back into one function. The retry existed because a
   *lagged* target, seeded from a mismatched FullInstanton profile, could
   develop a slow-growing divergence (prompt 21a §8.1) — a failure mode
   specific to the self-consistent update rule. With the target fixed
   (never re-lagged), that mechanism cannot occur; a mismatched seed now
   shows up as a *quantifiable bias* (see Finding 3) or an outright
   infeasible first probe (handled by `bootstrap_target`'s own
   backtracking, see Finding 2), never as the slow-drift divergence the
   retry was built for.
5. **Divergence early-exit in `picard_inner`** (`DIVERGENCE_GROWTH_PATIENCE`
   / `DIVERGENCE_RESIDUAL_FLOOR`). Not asked for explicitly, but required
   in practice: once the outer loop's own escalation probes lambda values
   further from the solution than before, `picard_inner`'s pre-existing
   behaviour of running a *diverging* probe all the way to `MAX_INNER=30`
   sweeps before giving up made the escalation impractically slow. A probe
   whose residual grows for `DIVERGENCE_GROWTH_PATIENCE=3` consecutive
   sweeps, once past `DIVERGENCE_RESIDUAL_FLOOR=1e-2`, is now abandoned
   early and treated exactly like an outright ODE failure.

## Findings (Phase 1, folded into the implementation above)

### Finding 1 — FullInstanton's own shooting is now robust at astronomic λ

Confirmed exactly what prompt 22/22b flagged (Finding 1b): at
`N_init=19.5, N_final=16.0, delta_Nstar∈{1,2,3}`, quadratic potential
`m/Mp=1e-5`, `phi0=15`, `MasslessDecoupledDiffusion` gives
`D11 = H²/(8π²) ≈ 1.6e-11` — astronomically small. A direct residual scan
(`phi1(N_total)` vs `lambda`) shows the shooting residual is essentially
**flat** for `lambda` up to `~1e5`, and the true root sits at
`lambda ≈ 1.9e9` (`delta_Nstar=1.0`), `3.16e9` (`=2.0`), `4.06e9` (`=3.0`).
The *old* finite-difference-probe outer loop happened to jump there in 4
outer iterations on one run — but the jump was driven by floating-point
noise in a `dlam=1e-6` probe evaluated inside a region where the *true*
analytic derivative is `~1e-10`; i.e. it worked by chance, exactly the
failure mode 22b's own design note warned a small-`dlam` probe would hit
once genuinely coupled.

The new shared shooting component, with `trust_radius_max=1e15` and
`stall_growth=10.0` (FullInstanton's own call site — see that module's
comment), reaches `lambda≈1.9e9`–`4.1e9` reliably in **13–15 outer
iterations**, ~0.3–0.5s wall-clock, for all three `delta_Nstar`. This is a
genuine, reproducible fix (not a lucky derivative), directly satisfying the
prompt's "FullInstanton ... should get the same hardening" instruction.

### Finding 2 — seeding the outer loop's *starting point* directly at λ_FI is unsafe

Initial implementation set `lam0 = lambda_FI` (the outer loop's actual
starting value). This broke **every** existing "genuinely coupled" GCI test
fixture (`_small_genuinely_coupled_case`, and by extension
`test_compute_gradient_coupled_instanton_end_to_end_full_values` and the
stiffness-instrumentation tests, which share the same parameters): the
*very first* Picard evaluation, at `lam0=lambda_FI=1.358`, ran into
`H_sq_local < 0` (unphysical) territory and failed outright, with no
secant history to fall back on — an unrecoverable solve failure. This is
not an edge case: it is the primary small/fast fixture the whole test suite
was built around.

**Fix:** `lam0` stays at the always-feasible `0.0` (matching the pre-22c
outer loop and the uniform-in-y initial condition), and `lambda_FI` is
passed to `solve_shooting` as `bootstrap_target` — used only to aim the
*first step*, which still goes through ordinary Armijo backtracking. A bad
guess safely degrades to a smaller, feasible step instead of an
unrecoverable first-evaluation failure, restoring "seed quality only
affects convergence speed" for `lambda` too (previously true only for the
target/forward-field seed).

A second, related bug surfaced while fixing this: the backtracking
sub-loop's "give up after `max_backtrack` halvings and take the smallest
step tried" fallback actually reverted to the *original, already-
confirmed-infeasible* step whenever **no** probe in the whole halving
sequence succeeded (`best_step` is only updated on success, so it never
changes from its pre-loop value in that case) — contradicting its own
documented intent and causing the outer loop to immediately re-fail and
exit after only 2 iterations. Fixed: when no probe succeeds at all, `lam`
does not move this iteration (stays at the last-known-good point); the
trust radius still shrinks, so the next attempt is smaller.

A third refinement was needed for the *direction* of stall/escalation
steps: initially always derived from `-residual`'s sign, this can point
into a region that is infeasible at every scale tried (confirmed directly:
a fixed-target-biased BVP's true root can sit on the *opposite* side of
`lam0` from where FullInstanton's own `lambda_FI` and the local residual
sign both point). `stall_sign` now persists across outer iterations and
flips when a whole escalation attempt (every backtrack halving) fails
outright, rather than being re-derived from a residual sign that may not
be informative for a case this nonlinear.

Finally, `stall_growth` itself needed **different values at the two call
sites**: FullInstanton needs `10.0` to reach `O(1e9)` from `O(0.05)`.
Applying the same aggressive factor to GCI's own outer loop was observed to
overshoot straight past a nearby, *narrow* feasible window (confirmed
directly: the true fixed-target-biased root at `lambda≈-1.3` sits within
`O(1)` of `lam0=0`, but a `10x`-per-stall escalation jumps to `O(100)` and
back without ever probing the narrow window in between). GCI's own call
site uses `stall_growth=1.5`.

### Finding 3 — the fixed target's bias is NOT reliably small

The prompt's own acceptance criterion ("perturb the fixed target ... and
confirm the converged `msr_action` moves by `≪` the physics signal") was
tested directly (`tests/test_picard.py::
test_solve_picard_fixed_target_bias_is_quantified_and_bounded`) on the
small, short-transition (`N_total=0.15`), strongly-regularized
(`alpha=0.05`) `_small_genuinely_coupled_case` fixture: a target
perturbation `delta=1e-3` moves the converged `msr_action` by `~1.3e-2` —
**amplified by a factor of ~13, not damped**. The test was written to
assert what is actually demonstrated (bounded, well-posed, convergent — not
divergent or catastrophic) rather than the stronger "≪ delta" claim it
falsifies, and this finding is recorded here rather than silently assumed
away.

Mechanistically this is consistent with Finding 2: on this fixture,
FullInstanton's own `lambda_FI≈+1.36` is a poor proxy for GCI's own
converged `lambda≈-1.3` (opposite sign, ~2.6 apart) — the fixed target is
therefore evaluated at a `pi_core(N)` shape that does not closely track
what this BVP's own dynamics actually produce, and freezing to a
mismatched shape is not a small perturbation on a short, tightly-regularized
transition. On a **degenerate**-target case (`_small_full_coupling_case`,
where the trivial `lambda=0` branch is exact for both models), the same
bias test gives `diff=0` exactly — bias is only demonstrably small in the
near-background regime, not in general.

**This is the prompt's own "clean negative is valid" allowance, exercised
directly on the fixed-target-bias acceptance criterion.** The fixed target
is still adopted as the default (Picard convergence to machine precision
when the seed does not destabilise the outer loop is a real, validated win
over the ~1e-4 Anderson floor), but "the bias is small" is not a general
property — it depends on how good a proxy FullInstanton's own `lambda_FI`
is, which is not established here for arbitrary configurations.

### Finding 4 — the literal "resolved regime" case is blocked by a pre-existing, unrelated gap

The production case this whole prompt chain has been building toward
(`N_init=19.5, N_final=16.0, delta_Nstar∈{1.0,2.0,3.0}`, quadratic
`m/Mp=1e-5`) is now **reachable** for FullInstanton (Finding 1) but GCI's
own solve at the resulting `lambda_FI≈1.9e9`–`4.1e9` fails: seeding the
outer loop there causes `picard_inner`'s response-sector backward pass to
hit `H_sq_local<0` or become pathologically slow (RK45 step-halving
without terminating in a practical time budget).

Root cause, isolated by inspection: `terminal_response_state` sets
`rfield_core(N_total) = -lam / (grid.weights[-1] * measure(...))`, an
*additional* `O(10x)` amplification of `lambda` at the terminal boundary
condition (LGL boundary quadrature weights are `O(0.1)` for small `n`).
`response_rhs.py`'s own module docstring already flags that the response
sector was **deliberately not ported** to the SBP-SAT closure (prompt 21a
scope note): it retains the same strong Neumann-elimination + non-split
advection structure the *forward* sector had before the port that fixed
its own `n_max`-dependent right-half-plane spectral growth. At ordinary
(small) `lambda` this pre-existing gap is invisible (prompt 21a's own
acceptance table used `delta_Nstar=0.1`, trivial `lambda≈0`); at the
astronomic `lambda` this specific corner requires, it becomes the binding
constraint.

**This is out of scope for prompt 22c** (whose own remit — the pi_core
target, the FullInstanton seed, the shared shooting component — explicitly
excludes the response-sector SBP-SAT port, deferred as a "short follow-on"
in prompt 21a and never picked up). It is reported here, per this
project's own "clean negative is valid" precedent (prompts 22, 22b), as a
**pre-existing, independently-flagged limitation surfaced by pushing
FullInstanton's own shooting into a regime nobody had reached before**, not
a regression introduced by this prompt's own changes.

## Acceptance — actual status

- [x] **Convergence, no floor**, on cases where FullInstanton is a
      reasonable proxy for GCI's own lambda (small/background-anchored
      fixtures): confirmed, machine-precision Picard convergence, no
      1e-4 Anderson floor.
- [ ] **Convergence, no floor**, on the *literal* resolved-regime case
      (`delta_Nstar∈{1,2,3}`, `n∈{5,7,9,11,13,17,33}`): **NOT
      demonstrated** — blocked by Finding 4 (response-sector gap at
      astronomic lambda), a pre-existing, out-of-scope limitation.
- [x] **Positive control**: `msr_action > 0`, non-trivial `lambda`, on the
      small genuinely-coupled fixture at `n=5` (`lambda≈-1.33`,
      `msr_action` finite and positive).
- [ ] **Fixed-target bias is small**: **NOT demonstrated in general**
      (Finding 3) — quantified as `~13x` amplification on the adversarial
      small fixture, exactly `0` on the degenerate fixture. Bounded/
      well-posed in both cases, not "small relative to delta" in general.
- [ ] **n-convergence** on the resolved regime: blocked by Finding 4, not
      attempted.
- [x] **Regularity emergent**: unaffected by this prompt (`g_phi` was never
      the contested closure); still holds.
- [x] **Shooting hardening shared**; FullInstanton uses it (Finding 1);
      Anderson/self-consistent path deprecated (dormant, `theta=1.0,
      anderson_m=5` still reachable); 21a retry-band-aid removed (its own
      failure mode — lagged-target drift from a mismatched seed — cannot
      occur once the target is fixed, not re-lagged).
- [x] Existing suite passes with the parametrization capped at what is
      demonstrated (`test_solve_picard_converges_under_genuine_coupling_
      across_n` now covers `n=5` only, `n=9` dropped — see that test's own
      docstring — mirroring prompt 22b's own `n≥17` cap); fixed-target-bias
      and n=5 resolved-case-adjacent regressions added.
- [ ] **Downstream** (extraction.py/scale_assignment.py on a non-flat
      profile): not reached — no non-degenerate resolved-regime solve
      exists yet to feed them (Finding 4). The small genuinely-coupled
      fixture's own extraction path is exercised incidentally by the
      existing end-to-end test, which passes, but that is a different
      (short, non-astronomic-lambda) configuration than what "non-flat
      profile" was meant to stress.

## Documentation

`picard.py`'s own module docstring now records the full target history
(21a lagged → 22 Finding 2 divergence → 22b Anderson + its own residual
floor → 22c fixed target + seeding) and the fixed-target-bias tradeoff.
`Numerics/ShootingSolver.py`'s own docstring documents `stall_growth` and
`bootstrap_target` with the concrete failure modes that motivated them.
`ComputeTargets/FullInstanton.py`'s outer loop is commented with the
`trust_radius_max=1e15` rationale.

## Out of scope, reaffirmed

- The response-sector SBP-SAT closure (Finding 4) — flagged, not
  implemented; the concrete trigger (astronomic-lambda terminal condition)
  is new information for prioritising this follow-on, but the follow-on
  itself is unchanged from prompt 21a's own deferral.
- Re-running the full prompt-22 Study suite E, the `alpha` regularization
  scan, production-grid re-tuning — all blocked transitively by Finding 4
  for the specific resolved-regime case, unattempted here.
- A general bound on "how good must `lambda_FI` be as a proxy for the
  fixed target's bias to be small" — Finding 3 demonstrates the property
  can fail but does not characterise when/why beyond the one concrete
  counter-example.
