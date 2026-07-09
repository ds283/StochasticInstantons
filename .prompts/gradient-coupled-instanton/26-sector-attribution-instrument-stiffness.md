# Prompt 26 — Diagnostic 10: sector attribution via `instrument_stiffness` at n≥9

*(Numbering assumption: continues the `.prompts/gradient-coupled-instanton/`
sequence after prompt 25. Renumber if a different slot is taken — nothing in
the task depends on the number.)*

## Implements

`diagnostic_10_sector_attribution` in
`tools/diagnostics/GradientCoupledInstanton/convergence_floor.py`, wired into
the existing `--diagnostic` CLI. **Diagnostics-package-only change. No file
under `ComputeTargets/`, `Numerics/`, or `Datastore/` is touched, and no new
instrumentation is added** — `solve_picard`'s `instrument_stiffness` flag
already exists, already aggregates per-sector RK45 step statistics into its
`diagnostics` dict, and is already threaded through the production call
(`main.py`'s `_compute_gradient_coupled_instanton`, default `True`); every
diagnostic script so far has simply always called it with
`instrument_stiffness=False`. This prompt only turns that flag on and reports
what it already measures.

## Track / step

Diagnostics suite, following Diagnostic 9's clean negative (the
fixed-`g_pi_core`-target bias does not explain the `n≥9` non-convergence).
This diagnostic answers the question raised immediately afterward: **which
sector** — forward (`forward_rhs.py`, SBP-SAT-ported, prompt 21a) or response
(`response_rhs.py`, deliberately un-ported, prompt 23) — is actually
destabilising as `n_collocation_points` increases through the known failure
point, at the genuinely-coupled `(m=1e-2, δN★=0.5)` point Diagnostic 6
established fails at `n∈{9,17}` but succeeds at `n=5`. The answer determines
whether the `tau_multiplier` production prompt (forward-sector fix) is the
right next step, or whether effort should go to the response sector instead
(§4 of `21a-production-port-notes.md`, "deliberately unchanged", flagged as
an open risk precisely for a case that "specifically stresses it").

## Depends on

- `tools/diagnostics/GradientCoupledInstanton/harness.py` — unchanged,
  read-only dependency (`setup`, `fetch_full_instanton`,
  `full_instanton_seed_from`, `save_json`, `output_dir`, `N_INIT`, `N_FINAL`,
  `ALPHA`, `ATOL`, `RTOL`, `picard_module`, `LGLCollocationGrid`,
  `compute_msr_action`).
- `tools/diagnostics/GradientCoupledInstanton/convergence_floor.py`'s
  existing `diagnostic_6_n_colloc` (the n-retry pattern this reuses) — read
  it in full before starting; Diagnostic 10 is that pattern plus
  `instrument_stiffness=True` plus reading six additional dict keys per
  sector, not new machinery.
- `ComputeTargets/GradientCoupledInstanton/picard.py`'s `solve_picard` —
  **read only**.

## Context to read first

- `.documents/gradient-coupled-instanton/21a-production-port-notes.md`, §4
  ("Response sector: deliberately unchanged") and §5 (the `n=7` oscillation
  traced to forward-sector τ, and the two empirical hardenings that were
  needed beyond the frozen-coefficient spectral check) — this is the direct
  precedent for what this diagnostic is trying to distinguish.
- `.documents/gradient-coupled-instanton/21a-production-port-notes.md`, §8.1
  — a *different* divergence where τ's magnitude (`1×`–`8×`) was tested and
  ruled out; read this so the eventual τ study (if this diagnostic points at
  the forward sector) isn't mistaken for re-deriving an already-settled
  question. It isn't: that finding was on a mismatched-seed divergence at
  `δN★=0.1`; this diagnostic is run at a genuinely-coupled `δN★=0.5` case.
- `.documents/gradient-coupled-instanton/23-response-sbp-sat-design-note.md`
  — the response sector's frozen-coefficient spectral abscissa is already
  confirmed bounded up to `n_max=192` (Part A, clean negative). Note
  carefully what this does and does not rule out: it is a *linearised,
  frozen-coefficient* check, not a check of the real nonlinear Picard
  iteration — exactly the gap that, on the forward sector, turned out to
  hide two real effects (§5.1–5.2 above). A bounded frozen-coefficient
  spectrum does not by itself rule out the response sector as this
  diagnostic's answer.
- `ComputeTargets/GradientCoupledInstanton/picard.py`'s own module
  docstring, `instrument_stiffness`/`_aggregate_rk45_stats` sections, for
  the exact returned-dict keys (reproduced below, but read the docstring's
  caveats on `dense_output=True`/empty-list fallback too).
- `tools/diagnostics/GradientCoupledInstanton/DIAGNOSTICS_SUITE.md` §6.

## Assumable interfaces (exact current signatures)

From `harness.py` (unchanged from prompt 25):
```python
h.setup(m, phi0=PHI0, pi0=PI0, atol=ATOL, rtol=RTOL) -> (potential, units, traj, dm)
h.production_phi_end(traj, N_init=N_INIT, N_final=N_FINAL) -> float
h.H_sq_nl_init_of(potential, traj, N_init=N_INIT) -> float
h.fetch_full_instanton(potential, traj, dm, N_init, N_final, delta_Nstar,
                        atol=ATOL, rtol=RTOL, label="") -> dict
h.full_instanton_seed_from(fi_data) -> Optional[dict]
h.save_json(path, obj) -> str
h.output_dir(*parts) -> str
h.LGLCollocationGrid(n_collocation_points)
h.compute_msr_action(N_grid, phi_grid, pi_grid, rfield_grid, rmom_grid,
                      grid, potential, dm, H_sq_nl_init, alpha) -> float
h.picard_module.solve_picard(N_init, N_final, delta_Nstar, alpha,
    H_sq_nl_init, grid, traj, potential, dm, atol, rtol, phi_end,
    instrument_stiffness=False, verbose=False, full_instanton_seed=None,
    wallclock_budget_seconds=None, label="") -> dict
```

`solve_picard`'s result `"diagnostics"` dict, the keys this prompt actually
needs (present whenever `instrument_stiffness=True`; `None`-valued if the
corresponding direction made no `solve_ivp` calls, e.g. an early failure):
```
converged, final_residual, bailout_tag, bailout_reason, outer_iterations,
rk45_forward_total_steps,  rk45_forward_accepted_steps,  rk45_forward_rejected_steps,
rk45_forward_min_step,     rk45_forward_max_step,        rk45_forward_steps_per_efold,
rk45_backward_total_steps, rk45_backward_accepted_steps, rk45_backward_rejected_steps,
rk45_backward_min_step,    rk45_backward_max_step,        rk45_backward_steps_per_efold,
picard_sweep_wallclock_min, picard_sweep_wallclock_mean, picard_sweep_wallclock_max
```
(`"backward"` = the response sector, integrated backward in `N`; `"forward"`
= the forward/onion sector.)

## Task

Add one new function, matching the existing section-banner convention:

```python
def diagnostic_10_sector_attribution(
    m: float = 1.0e-2, delta_Nstar: float = 0.5, ns=(5, 7, 9, 17),
    wallclock_budget: float = 900.0,
):
```

1. Fetch the `FullInstanton` seed once at `(m, delta_Nstar)`, exactly as
   `diagnostic_6_n_colloc` does (same point, so this is directly comparable
   to that diagnostic's own converged/floored record).
2. For each `n` in `ns`, build `grid = h.LGLCollocationGrid(n)` and call
   `solve_picard` with **`instrument_stiffness=True`** (the one behavioural
   difference from `diagnostic_6_n_colloc`), the same `full_instanton_seed`,
   `wallclock_budget_seconds=wallclock_budget`, `label=f"D10 n={n}"`.
3. From the returned `diagnostics` dict, record all eighteen keys listed
   above verbatim, plus `converged`/`final_lambda`/`msr_action` (computed
   the same way `diagnostic_6` already does, when converged) and the
   harness-measured wallclock (`time.perf_counter()` around the call, same
   pattern as every other diagnostic here — distinct from the returned
   `picard_sweep_wallclock_*`, which is internal per-sweep timing).
4. Compute two derived ratios per `n`, guarding `None`/zero denominators:
   - `forward_rejected_fraction = rk45_forward_rejected_steps / rk45_forward_total_steps`
   - `backward_rejected_fraction = rk45_backward_rejected_steps / rk45_backward_total_steps`
   - `backward_to_forward_steps_per_efold_ratio =
     rk45_backward_steps_per_efold / rk45_forward_steps_per_efold`
   These three are what actually answer the attribution question at a
   glance across the `n` sweep — include them in both the JSON and the
   printed table.
5. Persist everything via `h.save_json` at
   `f"{OUT_DIR}/diagnostic10_sector_attribution.json"` (`OUT_DIR` is the
   existing module-level constant).
6. Print a summary table, one row per `n`, columns: `n`, `converged`,
   `forward_total_steps`, `forward_rejected_fraction`,
   `backward_total_steps`, `backward_rejected_fraction`,
   `backward_to_forward_steps_per_efold_ratio`, `bailout_tag`. This should
   make the attribution readable directly off stdout.
7. Wire `"10": lambda args: diagnostic_10_sector_attribution()` into
   `_DIAGNOSTIC_DISPATCH`. No new CLI flags needed beyond the existing
   `--diagnostic` selector.

## Constraints

- No file under `ComputeTargets/`, `Numerics/`, or `Datastore/` changes —
  `instrument_stiffness=True` is the only behavioural switch this prompt
  flips, and it is an existing parameter.
- `wallclock_budget` default `900.0`, matching `diagnostic_6`'s own n≥9
  budget. Instrumentation adds measurement overhead (per `picard.py`'s own
  docstring) — if a run's `bailout_tag` comes back `wallclock_budget` where
  Diagnostic 6's equivalent run floored on `max_outer_exhausted` instead,
  note that discrepancy explicitly in the completion note rather than
  treating the two runs as directly comparable outer-iteration counts; the
  RK45 step *statistics* accumulated up to the bailout are still valid and
  are what this diagnostic is actually after.
- `n=5` **must** be included in `ns` (it is in the default) — it is the
  known-converged control every ratio should be read relative to.
- Reuse `h.save_json`/`h.output_dir`/`h.fetch_full_instanton`/
  `h.full_instanton_seed_from` exactly as existing diagnostics do.
- Docstring should state plainly what a forward-attributed vs.
  backward-attributed result would each imply (see "Decision point" below)
  so a future reader doesn't have to reconstruct the reasoning from this
  prompt file.

## Must NOT

- Must NOT modify `picard.py`, `forward_rhs.py`, `response_rhs.py`, or any
  other production file — this diagnostic exists specifically because no
  production change is needed to get this evidence.
- Must NOT re-derive or re-run the frozen-coefficient spectral checks
  (`spectrum.py`) as part of this function — that's a separate, already-built
  tool; if the completion note wants to cross-reference it, that's a manual
  follow-up comment, not code this prompt adds.
- Must NOT treat a `None`-valued `rk45_*` key (early failure before any
  `solve_ivp` call in that direction) as zero — report it as `None`/"n/a" in
  both JSON and the printed table, and say so explicitly if it happens for
  any swept `n`.
- Must NOT change the existing behaviour, numbering, or output filenames of
  Diagnostics 1–9.

## Acceptance test

- [ ] `git diff --stat` confined to
      `tools/diagnostics/GradientCoupledInstanton/convergence_floor.py`.
- [ ] Runs at `ns=(5,7,9,17)` without raising; `n=5`'s result is reported as
      converged (cross-check against Diagnostic 6's own `n=5` baseline —
      should agree on `converged`/`final_lambda` to the same tolerance
      Diagnostic 9's Step 0 already established at this point).
- [ ] All eighteen `rk45_*`/`picard_sweep_wallclock_*` keys are captured
      per `n` (or explicitly recorded as `None` where the underlying solve
      never reached that direction).
- [ ] The three derived ratios are computed and appear in both the JSON and
      the printed summary table for every `n`.
- [ ] `python -m tools.diagnostics.GradientCoupledInstanton.convergence_floor --diagnostic 10`
      runs end-to-end via the CLI and exits 0.
- [ ] Output JSON exists at
      `tools/diagnostics/GradientCoupledInstanton/output/convergence_floor/diagnostic10_sector_attribution.json`.
- [ ] A short completion note (matching the narrative style of the existing
      24a/24b/25 notes) reports the table, states plainly which sector's
      statistics diverge first/worse as `n` increases through 5→9, and
      gives an explicit attribution call — "forward-attributed",
      "backward-attributed", or "ambiguous/both" — with the numbers that
      justify it. An ambiguous result is a valid, reportable outcome; it is
      not grounds to keep adding intermediate `n` values speculatively.

## Decision point

Report back with the attribution before taking further action:

- **Forward-attributed** (forward sector's `rejected_fraction`/
  `steps_per_efold` spikes disproportionately at `n≥9`, backward stays
  bounded): proceed to the `tau_multiplier` production prompt and
  Diagnostic 8t — consistent with, and a higher-resolution recurrence of,
  the precedent in `21a-production-port-notes.md` §5.2.
- **Backward-attributed** (response sector's stats are the ones that spike,
  forward stays comparatively bounded): this contradicts the frozen-
  coefficient bound from prompt 23 in the same way the forward sector's own
  Phase 1 check was contradicted by its later nonlinear behaviour (§5 of
  21a) — recommend re-opening the response-sector SBP-SAT question
  (`23-response-sbp-sat-design-note.md`'s own closing instruction: "if a
  genuinely new n_max-dependent failure is found in this sector in the
  future, re-run this diagnostic first") rather than proceeding with the
  forward-only `tau_multiplier` prompt as currently scoped.
- **Ambiguous** (both sectors degrade together, or neither shows a clear
  signal despite non-convergence): recommend falling back to the
  `tau_multiplier` study anyway, since it is the cheaper of the two
  remaining options and directly informed by real precedent either way, but
  flag explicitly that the response sector has not been ruled out and may
  need revisiting if the τ study also comes back inconclusive.
