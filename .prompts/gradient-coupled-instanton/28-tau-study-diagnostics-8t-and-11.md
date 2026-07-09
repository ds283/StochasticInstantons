# Prompt 28 — Diagnostic 8t + Diagnostic 11: the τ study, both halves

*(Numbering assumption: continues after prompt 27. **Hard dependency: prompt
27 must have landed first** — this prompt cannot start until
`solve_picard`/`forward_rhs` accept `tau_multiplier`.)*

## Implements

Two diagnostics-package-only functions in
`tools/diagnostics/GradientCoupledInstanton/convergence_floor.py`:

1. `diagnostic_8_tau_sensitivity` — replaces the current
   `NotImplementedError` stub. Answers the **robustness** question: are the
   four converged Diagnostic-4 points (`n=5`, `δN★∈{0.2,0.3,0.5,0.7}`)
   stable to `tau_multiplier`, or are they resolution artefacts that happen
   to depend on the exact SAT penalty strength?
2. `diagnostic_11_tau_unlock_n_retry` — new. Answers the **unlock**
   question: can a different `tau_multiplier` make `n≥9` converge at all, at
   the same `(m=1e-2, δN★=0.5)` point Diagnostic 6/9/10 established fails
   under the production value?

No production code changes in this commit (prompt 27 already did that).

## Track / step

Directly follows Diagnostic 10's "ambiguous/both" sector attribution: τ is
not exonerated by that result (forward remained the dominant
`rejected_fraction` contributor at every `n` tested), and the response
sector's `bwd/fwd` crossover at `n=17` was flagged as a real but
inconclusive secondary signal. Per Diagnostic 10's own recommendation,
proceed to the τ study now; per its own caveat, come back to the response
sector if this study is also inconclusive.

## Depends on

- **Prompt 27, landed**: `solve_picard(..., tau_multiplier=1.0, ...)` must
  exist and be a real, functioning parameter.
- `tools/diagnostics/GradientCoupledInstanton/harness.py` — unchanged.
- `convergence_floor.py`'s existing `diagnostic_8_alpha_sensitivity` (the
  direct structural template for `diagnostic_8_tau_sensitivity` — same
  point set, same per-point solve/report pattern, sweeping a different
  parameter) and `diagnostic_6_n_colloc`/`diagnostic_9_bias_corrected_n_retry`
  (the direct structural template for `diagnostic_11_tau_unlock_n_retry` —
  same `n`-retry point, same wallclock-budget conventions).

## Context to read first

- `tools/diagnostics/GradientCoupledInstanton/DIAGNOSTICS_SUITE.md` §5 —
  the original scoping note for both halves, including the specific sweep
  values (`tau_multiplier∈{0.5,1.0,2.0}`) already committed to there.
- `.documents/gradient-coupled-instanton/25-bias-corrected-n-geq-9-retry.md`
  and `26-sector-attribution-instrument-stiffness.md` — the two "clean
  negative but here's what it rules in/out" results this prompt continues
  from; match their reporting style (executive summary with an explicit
  classification, full per-point table, verification section).
- `.documents/gradient-coupled-instanton/21a-production-port-notes.md` §5.1
  ("sign robustness") — a reminder that `tau_multiplier` values pushing
  `tau` toward or below the admissibility floor (`tau_multiplier < 0.5`)
  are expected, on theoretical grounds, to risk exactly the runaway
  `pi_core -> -sqrt(6)` failure mode documented there. **Do not sweep below
  `0.5`** in either diagnostic without an explicit reason — this is not a
  region the design note considers safe, and a failure there is not
  informative about the `n≥9` question either diagnostic is actually
  investigating.

## Assumable interfaces (exact current signatures, post-prompt-27)

```python
h.picard_module.solve_picard(N_init, N_final, delta_Nstar, alpha,
    H_sq_nl_init, grid, traj, potential, dm, atol, rtol, phi_end,
    instrument_stiffness=False, verbose=False, full_instanton_seed=None,
    wallclock_budget_seconds=None, label="",
    tau_multiplier=1.0) -> dict          # <-- new parameter, prompt 27
```
Every other harness/diagnostic interface is unchanged from prompts 25/26
(see those prompt files for the full list — `h.setup`, `h.fetch_full_instanton`,
`h.full_instanton_seed_from`, `h.save_json`, `h.output_dir`,
`h.LGLCollocationGrid`, `h.compute_msr_action`, `h.MonkeypatchGuard`).

`diagnostic_8_alpha_sensitivity`'s exact structure (the template for part 1):
```python
def diagnostic_8_alpha_sensitivity(m=1.0e-2, delta_Nstars=(0.2,0.3,0.5,0.7),
                                    alpha_values=(0.01,0.05,0.1,0.3),
                                    wallclock_budget=600.0): ...
```

`diagnostic_9_bias_corrected_n_retry`'s exact structure (the template for
part 2's baseline-then-sweep pattern):
```python
def diagnostic_9_bias_corrected_n_retry(m=1.0e-2, delta_Nstar=0.5,
    n_baseline=5, n_retry=9, delta_fractions=(0.0,0.3,1.0,3.0),
    max_outer_cap=30, wallclock_budget_seconds=900.0): ...
```

## Task

### Part 1 — `diagnostic_8_tau_sensitivity` (replaces the `NotImplementedError` stub)

```python
def diagnostic_8_tau_sensitivity(m: float = 1.0e-2, delta_Nstars=(0.2, 0.3, 0.5, 0.7),
                                  tau_multipliers=(0.5, 1.0, 2.0),
                                  wallclock_budget: float = 600.0):
```

Direct structural copy of `diagnostic_8_alpha_sensitivity`: for each
`delta_Nstar` in `delta_Nstars` and each `tau_multiplier` in
`tau_multipliers`, fetch the FullInstanton seed, call `solve_picard` at
`n=5` (module-level `N_COLLOC`, unchanged) with `alpha=h.ALPHA` (production
value, not swept here — this diagnostic isolates `tau_multiplier` alone)
and the new `tau_multiplier=tau_multiplier` keyword, record
`converged`/`final_residual`/`bailout_tag`/`final_lambda`/
`gradient_enhancement_E`/`outer_iterations`/`wallclock`/`msr_action`
(when converged, via `h.compute_msr_action`, same pattern as 8a) and
`max_epsilon_core` (same `0.5*pi_grid[:,-1]**2` computation as 8a). Persist
to `f"{OUT_DIR}/diagnostic8t_tau_sensitivity.json"`. Docstring should state
the same interpretation frame as 8a's own: a convergent discretisation's
`msr_action`/`final_lambda`/`max_epsilon_core` should be stable across this
range (design note's own admissibility claim, "any tau>=A(core)/2");
material dependence indicates the `n=5` solutions are sensitive to the SAT
penalty strength rather than converged to a tau-independent continuum
answer.

### Part 2 — `diagnostic_11_tau_unlock_n_retry` (new)

```python
def diagnostic_11_tau_unlock_n_retry(m: float = 1.0e-2, delta_Nstar: float = 0.5,
                                      n_retry: int = 9,
                                      tau_multipliers=(0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0),
                                      max_outer_cap: int = 30,
                                      wallclock_budget_seconds: float = 900.0):
```

Same point as Diagnostic 6/9/10 (`m=1e-2, delta_Nstar=0.5, n=9`, known to
floor at `tau_multiplier=1.0`, the production value — this is already the
middle entry of the default sweep, giving a free cross-check against
Diagnostic 6/10's own recorded `final_residual=0.112`-ish result). For each
`tau_multiplier` in `tau_multipliers`: fetch the FullInstanton seed once
(outside the loop — identical seed for every `tau_multiplier`, this is not
Diagnostic 9's bias study), solve at `n=n_retry` under
`h.MonkeypatchGuard(h.picard_module, MAX_OUTER=max_outer_cap)`, record the
same field set as Diagnostic 9/10 (`converged`, `final_residual`,
`bailout_tag`, `bailout_reason`, `final_lambda`, `gradient_enhancement_E`,
`outer_iterations`, `wallclock`, `msr_action` when converged). Persist to
`f"{OUT_DIR}/diagnostic11_tau_unlock_n_retry.json"`. Print a summary table
(`tau_multiplier`, `converged`, `final_residual`, `bailout_tag`) — the
direct analogue of Diagnostic 9's own bias-sweep table, swept parameter
changed from `delta` to `tau_multiplier`.

Interpretation to state in the docstring: if some `tau_multiplier` in this
range converges at `n=9` where `1.0` floors, that's a direct unlock —
report which value, and whether the resulting solution's `msr_action`/
`final_lambda` is close to the `n=5` extrapolation. If none converge, this
is a second clean negative for τ specifically (distinct from, but
complementary to, Diagnostic 9's bias clean negative) and strengthens the
case for revisiting the response sector per Diagnostic 10's own
recommendation.

### Both parts

- Wire `"8t": lambda args: diagnostic_8_tau_sensitivity()` (replacing the
  current stub entry) and
  `"11": lambda args: diagnostic_11_tau_unlock_n_retry()` into
  `_DIAGNOSTIC_DISPATCH`.
- Remove the `NotImplementedError`-raising stub function entirely (do not
  leave it as dead code alongside the real implementation).

## Constraints

- `diagnostic_8_tau_sensitivity`'s per-point cost is the same order as
  `diagnostic_8_alpha_sensitivity`'s (`n=5`, ~10s/solve per prompt 25/26's
  own timing data) — `wallclock_budget=600.0` is ample headroom, not a
  binding constraint; if it binds anywhere, that is itself a reportable
  anomaly (an `n=5` point that was previously fast now timing out at a
  different `tau_multiplier` would be surprising and worth flagging, not
  silently absorbing into a larger default budget).
- `diagnostic_11_tau_unlock_n_retry`'s per-point cost is `n=9`-scale
  (minutes, per Diagnostic 9/10's own timings, 400-900s/point) — do not
  reduce `wallclock_budget_seconds` below `900.0` without a stated reason;
  Diagnostic 10 already showed instrumentation-free `n=9` solves can take
  up to ~860s to floor.
- Do not sweep `tau_multiplier < 0.5` in either diagnostic (see "Context to
  read first" above) without flagging explicitly why in the completion
  note.
- Reuse `h.MonkeypatchGuard`, `h.save_json`, `h.output_dir`,
  `h.fetch_full_instanton`, `h.full_instanton_seed_from`,
  `h.compute_msr_action` exactly as existing diagnostics do — no parallel
  helpers.

## Must NOT

- Must NOT modify `forward_rhs.py`, `picard.py`, or `GradientCoupledInstanton.py`
  further — prompt 27 already made the one production change needed; this
  prompt only calls the resulting parameter.
- Must NOT sweep `alpha` in `diagnostic_8_tau_sensitivity` (it isolates
  `tau_multiplier`; use the fixed production `h.ALPHA`) — a joint
  `alpha`×`tau_multiplier` sweep is out of scope here and would confound
  the two already-separately-answered sensitivity questions (Diagnostic 8a
  vs this one).
- Must NOT change Diagnostics 1–7, 8a, 9, or 10's existing behaviour,
  numbering, or output filenames.
- Must NOT draw a conclusion about the response sector from
  `diagnostic_11_tau_unlock_n_retry`'s result alone — a clean negative here
  motivates revisiting the response sector (per Diagnostic 10's own
  recommendation) but does not itself constitute that investigation.

## Acceptance test

- [ ] `git diff --stat` confined to
      `tools/diagnostics/GradientCoupledInstanton/convergence_floor.py`
      (plus, if needed, the module docstring's own "Known gaps"-adjacent
      text — no production files).
- [ ] `diagnostic_8_tau_sensitivity()` runs end-to-end at the default point
      set, and its `tau_multiplier=1.0` row at each `delta_Nstar` matches
      Diagnostic 4's own recorded `final_lambda`/`msr_action` at that point
      to the same bit-for-bit tolerance prompt 27's own acceptance test
      established (this is the direct regression check that `tau_multiplier
      =1.0` is a true no-op, exercised here from the diagnostics side too).
- [ ] `diagnostic_11_tau_unlock_n_retry()` runs end-to-end at the default
      seven-point sweep; its `tau_multiplier=1.0` row matches Diagnostic
      6/10's own recorded `n=9` result (`final_residual≈0.112`,
      `bailout_tag=floored/max_outer_exhausted`) to a sanity-check
      tolerance (exact match not expected/required, since Diagnostic 10 ran
      with `instrument_stiffness=True`, adding measurement overhead per its
      own verification section — but `converged`/`bailout_tag` and
      `final_residual`'s order of magnitude should agree).
- [ ] `python -m tools.diagnostics.GradientCoupledInstanton.convergence_floor --diagnostic 8t 11`
      runs both end-to-end via the CLI and exits 0.
- [ ] Both output JSONs exist under
      `tools/diagnostics/GradientCoupledInstanton/output/convergence_floor/`.
- [ ] A completion note (matching 25/26's style) reports both tables and
      gives two explicit classifications: (1) robustness —
      "`n=5` results tau-independent" or "material tau-dependence found,
      at [which point(s)]"; (2) unlock — "some `tau_multiplier` converges
      `n=9`, value=[X]" or "clean negative, no swept value converges `n=9`".
      Both are separately reportable; a clean negative on (2) is not
      grounds to widen `tau_multipliers` speculatively.

## Decision point

Report back with both classifications before further action:

- **(1) tau-independent AND (2) unlocks n=9 at some value**: best possible
  outcome — recommend adopting that `tau_multiplier` as the new production
  default (a further, small, separately-scoped prompt) and re-running
  Diagnostic 6-style `n∈{9,17,...}` convergence checks under it.
- **(1) tau-independent AND (2) clean negative**: the `n=5` physics is
  trustworthy but `n≥9` needs something other than τ — recommend revisiting
  the response sector next, per Diagnostic 10's own closing recommendation.
- **(1) material tau-dependence found**: this is the more concerning
  outcome regardless of (2)'s result — the `n=5` "converged" solutions
  reported since Diagnostic 4 would need to be treated as provisional/SAT-
  penalty-dependent rather than physics, and revisiting them (which
  `delta_Nstar`/point(s) are affected, how strongly) becomes the immediate
  priority over the `n≥9` question.
