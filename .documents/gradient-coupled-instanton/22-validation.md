# Prompt 22 — Validation of the SBP-SAT `GradientCoupledInstanton` closure in the resolved regime

Prompt: `.prompts/gradient-coupled-instanton/22-validation-resolved-regime.md`.
Harness: `out-gradient-coupled-stiffness/scripts/validation_22_resolved_regime.py`.
Data/plots: `out-gradient-coupled-stiffness/scripts/validation_22_output/`.

**Verdict: clean negative closeout.** Studies A–E could not be executed as
scoped, because two blocking issues — found during this validation, not
present in the prompt's premise — mean **no converged, non-degenerate
`GradientCoupledInstanton` solution currently exists to validate**, under
either the production wiring or any direct workaround available from outside
production code. This is reported plainly per the prompt's own acceptance
criterion ("a clean negative result here is a valid closeout, since the point
is to know whether the `n=33` number is trustworthy, not to force a green
tick"). No production code was modified anywhere in this investigation.

## Summary

1. **Finding 1** (`GradientCoupledInstanton.py` line ~197): the production
   `phi_end` target is an exact algebraic identity with the noiseless
   background trajectory, for *every* `delta_Nstar`. The shooting BVP is
   therefore degenerate everywhere: `lambda = 0` is an exact solution,
   response fields are identically zero, and `msr_action = 0.0` to machine
   precision. Every prior acceptance/regression result for this compute
   target (prompts 19–21a) exercised only this trivial branch — the
   gradient/shell coupling that is the entire point of the onion model has
   never actually been driven by a real production run.
2. Correcting the target locally in this validation harness (passing the
   `FullInstanton`-consistent value directly into `solve_picard` — an
   ordinary, pre-existing parameter, no production code touched) does produce
   a genuine, non-trivial target, confirmed independently against
   `FullInstanton` itself (**Finding 1b**).
3. **Finding 2**: once the target is genuinely non-trivial, the production
   Picard scheme (`DEFAULT_SAT_THETA = 1.0`, the lagged `g_pi_core` target)
   **does not converge**. The sweep-to-sweep residual falls for ~15 sweeps
   and then grows without bound — reproduced at every
   `(n_collocation_points, delta_Nstar)` combination tried, including the
   smallest possible grid (`n=5`) and an infinitesimal perturbation
   (`dlam ~ 1e-6`) away from the exact trivial fixed point. Under-relaxation
   (`theta < 1`, an existing, already-documented, currently-unused-by-default
   escape hatch) delays the onset but does not cure it within any practical
   sweep budget.

Because Finding 2 blocks convergence regardless of which target is used, the
SBP-SAT boundary closure itself (prompts 20/21/21a's own subject) was **not**
newly implicated by this investigation, and its own linear/frozen-coefficient
validation (Phase 1 of prompt 21, `tests/test_sbp_sat_boundary_closure.py`)
stands. What failed is the *nonlinear Picard iteration* built on top of it —
specifically the lagged-`g_pi_core` closure's fixed-point map — which had
never previously been exercised with genuine (non-zero) response-field
coupling because of Finding 1.

## Method

Per the prompt's instruction to use "the direct Ray-bypassing pattern the
suite already uses", every result below calls `solve_picard` /
`_compute_full_instanton._function` directly (no Ray, no Datastore), matching
`scripts/compare_gradient_full.py` and the existing test suite. The only
non-standard technique used is monkeypatching `picard.MAX_OUTER`/`MAX_INNER`
at runtime to isolate the inner Picard loop cheaply — the exact pattern
`tests/test_picard.py::test_solve_picard_non_convergence_returns_failure_dict`
already uses (`monkeypatch.setattr(picard_module, "MAX_OUTER", 1)`). No file
under version control was edited.

Background: quadratic potential, `m/Mp = 1e-5`, `phi0 = 15 Mp`, `pi0 = 0`,
`Planck_units`, `atol = rtol = 1e-8` — the same physical setup as prompt
21a's own acceptance case and `compare_gradient_full.py`. `N_init = 19.5`,
`N_final = 16.0` (`ΔN = 3.5`), `alpha = 0.1` throughout, matching the
`quadratic-asteroid-small.yaml` production grid.

## Finding 1 — production `phi_end` target is degenerate

`GradientCoupledInstanton.py`'s remote function computes:

```python
phi_end = traj.phi_at(N_offset + N_total)
```

Since `N_offset = trajectory.N_end - N_init` and
`N_total = (N_init - N_final) + delta_Nstar`, this is identically
`traj.phi_at(N_end - N_final + delta_Nstar)` — **the value the noiseless
background trajectory reaches after locally integrating for exactly
`N_total` e-folds**, for every `delta_Nstar`. The core forward equation, run
with `lambda = 0` and zero response-field sourcing, trivially lands on
exactly this value (it *is* the background). `lambda = 0` is therefore an
exact fixed point of the shooting problem for every `delta_Nstar`, and
`terminal_response_state(0, ...)` is identically zero at every node
(`response_rhs.py` line ~267), so the backward/response sector never sources
anything nonzero either — the entire model (forward, backward, `msr_action`)
collapses to the trivial background solution.

This differs from **`FullInstanton`**'s own convention
(`ComputeTargets/FullInstanton.py` line ~650):

```python
phi_final = traj.phi_at(N_end - float(self._N_final))   # no delta_Nstar
```

and from the onion-model design document itself
(`.documents/gradient-coupled-instanton/onion_model.tex` §"Motivation" /
eq:bc-final-core): `\phiend` is described as a *fixed* target independent of
`delta_Nstar`, with `delta_Nstar` controlling only how much *longer* than the
background's own natural duration the excursion is allowed to take to reach
it — the "excess/delayed e-folds" instanton that is the entire physical
content of `delta_Nstar`. The production formula cancels this physics
identically by construction, not merely in some parameter corner.

**Direct evidence** (`finding1_target_degeneracy.csv`, `n_collocation_points=9`):

| `delta_Nstar` | production target | corrected target | difference | converged | `lambda` | `msr_action` | `rfield` max | φ y-spread |
|---|---|---|---|---|---|---|---|---|
| 0.1 | 7.892219 | 7.917258 | −0.0250 | yes | 0.0 | **0.0** | 0.0 | 3.5e-9 |
| 1.0 | 7.663260 | 7.917258 | −0.2540 | yes | 0.0 | **0.0** | 0.0 | 5.0e-9 |
| 1.5 | 7.533120 | 7.917258 | −0.3841 | yes | 0.0 | **0.0** | 0.0 | 5.6e-9 |
| 1.9 | 7.427403 | 7.917258 | −0.4899 | yes | 0.0 | **0.0** | 0.0 | 6.1e-9 |
| 2.5 | 7.266012 | 7.917258 | −0.6512 | yes | 0.0 | **0.0** | 0.0 | 6.9e-9 |
| 3.0 | 7.128796 | 7.917258 | −0.7885 | yes | 0.0 | **0.0** | 0.0 | 7.5e-9 |

`msr_action` and `rfield` max are **exactly** `0.0` (not "small") at every
`delta_Nstar` tried, including the values in the prompt's own recommended
`delta_Nstar ∈ [1.0, 3.0]` "resolved regime" range — confirming this is not
a resolution/floor issue but an exact identity. The residual y-spread quoted
in the table (`~1e-9`) is pure solver-tolerance noise around the exactly-flat
trivial solution, an order of magnitude *below* even the `n=5` "near-uniform"
floor the prompt's own gate check anticipated (`~1e-6`) — because there is,
in fact, no physics driving any spread at all.

**This fully explains why the prompt's own gate check (pick a `delta_Nstar`
with a resolved y-profile) could not be satisfied**: no `delta_Nstar` value
produces a resolved profile under the production wiring, because the profile
is not merely small, it is exactly zero.

## Finding 1b — the corrected target is genuinely physical

To confirm the corrected target is not itself somehow degenerate (e.g. by
another accidental coincidence), it was cross-checked against
`FullInstanton` — a completely independent, already-validated compute target
— at the same `(phi_init, phi_end, N_total)`
(`delta_Nstar = 1.0`, `N_total = 4.5`):

```
FullInstanton: failure=False, msr_action = 2.147e8
```

(`finding1b_full_instanton_cross_check.csv`). This is a large, non-zero,
finite action — genuine "excess-duration" instanton physics, not a
degenerate reduction. The size of the action (`~2e8`) reflects that this
particular corner (`m/Mp = 1e-5`, `ΔN = 3.5`, `delta_Nstar = 1.0`) is itself
poorly conditioned for `FullInstanton`'s own shooting problem — consistent
with prompt 21a §8.1's own observation that this same physical setup forces
`P1 ~ 1e8` even for `FullInstanton` alone. This is flagged as context, not
as a new problem: it means the *specific* case checked here is numerically
stiff for reasons unrelated to the onion-model gradient coupling, and a
future remediation attempt may want to first re-run this same cross-check at
a gentler `(N_init, N_final, ΔN)` point before concluding anything about
`GradientCoupledInstanton`'s own behaviour from its magnitude specifically.
It does not affect Finding 1's conclusion (the production target's exact
triviality) or Finding 2 below (reproduced independently at multiple
`delta_Nstar`, not just this one).

## Finding 2 — Picard iteration diverges under genuine coupling

With the corrected (non-degenerate) target passed directly into
`solve_picard`, the production Picard scheme (`theta = 1.0`,
`DEFAULT_SAT_THETA`) was probed by isolating the *first* outer-Newton
derivative probe (`MAX_OUTER = 1`, `lambda = 0 → lambda = dlam ≈ 1e-6`) and
recording `max|dphi|` sweep-by-sweep (`finding2_picard_divergence.csv`,
plotted in `finding2_picard_divergence.png`):

| case | sweeps captured | min residual | residual at cutoff | converged (`<1e-7`)? |
|---|---|---|---|---|
| `n=5, ΔN*=1.0, θ=1.0` | 30 | 6.99e-5 (sweep 15) | 7.94e-3 (sweep 30) | **no** |
| `n=5, ΔN*=1.0, θ=0.5` | 30 | 4.10e-5 (sweep 29) | 4.48e-5 (sweep 30) | no |
| `n=5, ΔN*=1.0, θ=0.5`, extended budget (`MAX_INNER=150`) | 150 | 4.10e-5 (sweep 29) | 3.66e-3 (sweep 150, after peaking ~2e-2 near sweep 100) | **no** |
| `n=5, ΔN*=1.0, θ=0.2` | 30 | 9.23e-5 (sweep 30, still falling) | — | no (too slow) |
| `n=5, ΔN*=1.0, θ=0.05` | 30 | 6.65e-5 (sweep 30, still falling) | — | no (too slow) |
| `n=7, ΔN*=1.0, θ=1.0` | 30 | 4.01e-4 (sweep ~13) | 1.51e+0 (sweep 30) | **no** |
| `n=5, ΔN*=1.5, θ=1.0` | 30 | 9.66e-5 | 1.24e-2 (sweep 30) | **no** |
| `n=5, ΔN*=2.5, θ=1.0` | 30 | 1.39e-4 | 1.97e-2 (sweep 30) | **no** |

Reading the plot: every `theta = 1.0` case (independent of `n` and
`delta_Nstar`) traces the same qualitative shape — a smooth decrease for
`~15` sweeps, followed by unbounded growth (up to `O(1)`, i.e. comparable to
the field values themselves, well before `MAX_INNER = 30` is exhausted).
This is not resolution-dependent (`n=5` and `n=7` both show it) and not
specific to one `delta_Nstar` (`1.0`, `1.5`, `2.5` all show it) — it is a
generic property of the `theta=1` lagged-`g_pi_core` fixed-point map once the
response fields are genuinely non-zero.

Under-relaxation (`theta<1`) — already implemented and documented in
`picard.py` precisely as the escape hatch for "`theta=1` observed to
oscillate or diverge" — delays but does not cure this:

- `theta=0.5` looks convergent through 30 sweeps (residual falls
  monotonically to `4.1e-5`), but the extended-budget run
  (`MAX_INNER=150`) shows this was only a transient minimum: the residual
  turns around at sweep ~30 and grows to a broad peak (`~2e-2`) around sweep
  100 before partially receding — a bounded, non-monotone oscillation, never
  approaching the `1e-7` target within 150 sweeps (5× the production
  budget).
- `theta=0.2` and `theta=0.05` do decrease monotonically throughout, but at
  a contraction rate that would require several hundred to well over a
  thousand sweeps to reach `1e-7` (extrapolated from the observed per-sweep
  ratio) — impractical within any reasonable sweep budget, and slower than
  simply increasing `MAX_INNER` would ever be worth.

**This is a genuinely new failure mode**, not a rediscovery of anything
prompt 21a already characterised: that prompt's own "Picard-sweep
oscillation" finding (§5.2 of the 21a design note addendum) was about
`phi_core`'s *own* new dynamical freedom interacting with `tau`, fixed by
doubling `tau`; the present divergence occurs with `tau` at its
already-hardened production value (`tau = abs(A_core)`) and is driven
instead by the lagged `g_pi_core` *target update* itself once it tracks a
genuinely non-trivial `pi_core(N)`. It was invisible to every previous test
and acceptance run because Finding 1 meant `pi_core(N)` was always
identically the background value, so the lagged target was always trivially
self-consistent from sweep 0.

## Why Studies A–E cannot be executed

Every one of Studies A (n-convergence), B (closure-independence), C
(regularity/tau-sensitivity), and D (Picard/Newton convergence audit)
presupposes a *converged*, non-degenerate `GradientCoupledInstanton` solution
to examine. Under the production target (Finding 1) that solution is exactly
the trivial background at every `n` — there is no y-profile, no
`msr_action`, and no response field to check convergence, seed-independence,
regularity, or `tau`-sensitivity *of*. Under the corrected target (the only
available route to a non-trivial profile without touching production code),
the Picard iteration itself does not converge (Finding 2) at any
`n_collocation_points` tried — so there is still no converged solution to
examine. Study D's own question ("does the Picard residual reach tolerance,
not stall above it?") is in fact answered directly and unambiguously by
Finding 2: **no**, it does not, once genuine coupling is present.

Study E (physics sanity) is the exception the prompt's acceptance section
allows to be "reported as available" rather than required: the
`FullInstanton` cross-check in Finding 1b is, in effect, one small piece of
Study E's "uniform-limit reduction" check (done at the level of the target
alone, not across `n`, since no `GradientCoupledInstanton` solution
converges to compare against). No further Study E work was attempted, since
it is strictly weaker evidence than Findings 1/1b/2 and would not change the
verdict.

## Acceptance (per the prompt's own closeout criterion)

> "If any of A–D fails, the report says so plainly and scopes the remaining
> work — a clean negative result here is a valid closeout, since the point is
> to know whether the `n=33` number is trustworthy, not to force a green
> tick."

**The `n=33` number (and every other `n`) is not trustworthy for any
non-trivial `delta_Nstar`**, because production code never computes anything
but the exact trivial background (Finding 1), and the one available
diagnostic route to a genuine solve does not converge (Finding 2). Studies
A–D fail in the specific, well-evidenced sense that their precondition
(a converged, resolved solution) is not obtainable at all, under either
wiring.

## Scoping the remaining work (separate prompt, not attempted here)

Per the prompt's explicit "out of scope" list, no closure or physics change
was made here. Remediation likely needs, as a follow-on prompt:

1. **Fix `GradientCoupledInstanton.py`'s `phi_end`** (line ~197) to match
   `FullInstanton`'s convention (`traj.phi_at(traj.N_end - N_final)`,
   independent of `delta_Nstar`) — a one-line, well-understood fix, but a
   physics-affecting production change requiring explicit sign-off per
   `CLAUDE.md`'s conventions, and out of this validation prompt's scope.
2. **Re-derive or replace the lagged-`g_pi_core` Picard closure's stability
   properties.** Finding 2 shows the current `theta=1` scheme is unstable
   once genuinely coupled, and that the exposed `theta<1` relaxation trades
   instability for impractically slow convergence rather than curing the
   underlying issue — the fixed-point map itself likely needs
   re-examination (e.g. a proper Newton/quasi-Newton step on the coupled
   `(lambda, g_pi_core)` system, or a differently-constructed target/closure),
   not just a relaxation-parameter retune. This is squarely a physics/
   algorithm design question, not a validation one, and should be scoped as
   its own prompt with its own derivation, mirroring how prompts 20/21/21a
   handled the advection-operator instability.
3. Once both are fixed, **this prompt's own Studies A–E should be re-run
   from scratch** — none of the diagnostic infrastructure built here
   (`validation_22_resolved_regime.py`) depended on the buggy target or the
   unstable closure, so it can be reused directly once a converged solution
   exists to feed it.

## Artefacts

- `out-gradient-coupled-stiffness/scripts/validation_22_resolved_regime.py`
  — the harness reproducing every number in this report (no Ray, no
  Datastore, no production code modified).
- `out-gradient-coupled-stiffness/scripts/validation_22_output/finding1_target_degeneracy.csv`
- `out-gradient-coupled-stiffness/scripts/validation_22_output/finding1b_full_instanton_cross_check.csv`
- `out-gradient-coupled-stiffness/scripts/validation_22_output/finding2_picard_divergence.csv`
- `out-gradient-coupled-stiffness/scripts/validation_22_output/finding2_picard_divergence.png`
