# Prompt 25 — Diagnostic 9: bias-corrected target retry at n≥9

*(Numbering assumption: this continues the `.prompts/gradient-coupled-instanton/`
sequence after whatever prompt landed the `tools/diagnostics/GradientCoupledInstanton`
refactor. Renumber the filename/header if a different slot is already taken —
nothing in the task itself depends on the number.)*

## Implements

`diagnostic_9_bias_corrected_n_retry` in
`tools/diagnostics/GradientCoupledInstanton/convergence_floor.py`, wired into
that module's existing `--diagnostic` CLI. **Diagnostics-package-only change.
No file under `ComputeTargets/`, `Numerics/`, or `Datastore/` is touched.**

## Track / step

Diagnostics suite, following on from Diagnostic 8a. Tests the cheaper of two
competing explanations for the `n∈{9,17}` non-convergence Diagnostic 6
recorded at a point that converges cleanly at `n=5`: is it the same,
already-documented, resolution-independent fixed-`g_pi_core`-target bias
(Diagnostic 3a's own mechanism) simply biting harder once the discretisation
resolves more structure — or does it need new numerics (the tau study, or a
genuine boundary-layer fix)? This prompt answers that question without
touching production code; its result determines whether the `tau_multiplier`
production prompt is the next necessary step or an optional completeness
check.

## Depends on

- `tools/diagnostics/GradientCoupledInstanton/harness.py` — unchanged,
  read-only dependency.
- `tools/diagnostics/GradientCoupledInstanton/convergence_floor.py`'s
  existing `diagnostic_3` (bias-injection pattern) and `diagnostic_6_n_colloc`
  (n-retry pattern) — this prompt is a direct splice of the two, not new
  machinery. Read both in full before starting.
- `ComputeTargets/GradientCoupledInstanton/picard.py`'s `solve_picard` —
  **read only**, not modified by this prompt.

## Context to read first

- `.documents/gradient-coupled-instanton/24a-diagnose-convergence-floor.md`,
  Diagnostic 3 section (the bias mechanism; the `m=1e-3, delta_Nstar=1.0,
  delta=+0.03` result that cured that floor).
- `.documents/gradient-coupled-instanton/24b-lambda-conversion-seeding-and-trajectory-validation.md`,
  Part C (`n∈{9,17}` clean negative at `m=1e-2, delta_Nstar=0.5`).
- `tools/diagnostics/GradientCoupledInstanton/DIAGNOSTICS_SUITE.md`, §6
  ("n-convergence... the cheaper next step").
- `ComputeTargets/GradientCoupledInstanton/picard.py`'s own module
  docstring, "pi_core SAT target -- history and the prompt 22c fixed-target
  replacement" section — for what perturbing `g_pi_core` means physically
  and why it is currently frozen at the FullInstanton seed's own `phi2(N)`.
- `picard.solve_picard`'s own return dict: note the `"g_pi_core_final"` key
  (the fixed target actually used, sampled on `N_grid`) — this prompt needs
  it to measure the n=5 bias directly, not just to seed n=9.

## Assumable interfaces (exact current signatures)

From `harness.py`:
```python
h.setup(m, phi0=PHI0, pi0=PI0, atol=ATOL, rtol=RTOL) -> (potential, units, traj, dm)
h.production_phi_end(traj, N_init=N_INIT, N_final=N_FINAL) -> float
h.H_sq_nl_init_of(potential, traj, N_init=N_INIT) -> float
h.fetch_full_instanton(potential, traj, dm, N_init, N_final, delta_Nstar,
                        atol=ATOL, rtol=RTOL, label="") -> dict
h.full_instanton_seed_from(fi_data) -> Optional[dict]
h.MonkeypatchGuard(module, **overrides)          # context manager
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

From `convergence_floor.py` (existing, for pattern reference only):
```python
def diagnostic_3(m=1.0e-3, delta_Nstar=1.0, deltas=(0.0, 0.01, -0.01, 0.03),
                  max_outer_cap=20, wallclock_budget_seconds=500.0): ...
def diagnostic_6_n_colloc(m=1.0e-2, delta_Nstar=0.5, ns=(9, 17),
                           wallclock_budget=900.0): ...
_DIAGNOSTIC_DISPATCH = {...}   # dict[str, Callable[[argparse.Namespace], Any]]
```

`solve_picard`'s result dict (relevant keys only): `"failure"`, `"final_lambda"`,
`"phi_grid"`, `"pi_grid"`, `"rfield_grid"`, `"rmom_grid"`, `"N_grid"`,
`"g_pi_core_final"` (list, same length as `"N_grid"`, or `None`),
`"diagnostics"` (dict with `"converged"`, `"final_residual"`, `"bailout_tag"`,
`"bailout_reason"`, `"outer_iterations"`, `"gradient_enhancement_E"`).

## Task

Add one new function, in the same style/section-banner convention as the
existing diagnostics:

```python
def diagnostic_9_bias_corrected_n_retry(
    m: float = 1.0e-2, delta_Nstar: float = 0.5, n_baseline: int = 5,
    n_retry: int = 9, delta_fractions=(0.0, 0.3, 1.0, 3.0),
    max_outer_cap: int = 30, wallclock_budget_seconds: float = 900.0,
):
```

1. **Step 0 — measure the n=5 baseline bias, don't assume it.** Solve at
   `(m, delta_Nstar, n_baseline)` with `delta=0.0` (the ordinary,
   unperturbed fixed target, exactly as `diagnostic_4`/`diagnostic_6` already
   do at this point). From the converged result, compute
   `bias_n5 = max(abs(np.asarray(pi_grid)[:, -1] - np.asarray(g_pi_core_final)))`
   — the actual sweep-0-to-convergence drift between the frozen target and
   the converged `pi_core(N)` at the resolution that *does* converge. This
   is the "how big is this bias in practice, at this specific grid point"
   measurement Diagnostic 3a never made at m=1e-3 (Diagnostic 3a used an
   arbitrary literal `0.03`); do not reuse that literal here, since it was
   calibrated for a different mass and `delta_Nstar`.
2. **Step 1 — sweep `delta_fractions × bias_n5` at n_retry.** For each
   `frac` in `delta_fractions` (both signs — the caller-supplied default
   already includes `0.0` as a control and should be extended with negative
   fractions too, e.g. effectively sweeping
   `delta ∈ {0, ±0.3, ±1.0, ±3.0} × bias_n5`), build the perturbed seed via
   `phi2_perturbed = np.asarray(fi_data["phi2"]) + delta` (identical
   mechanism to `diagnostic_3`'s own 3a), and call `solve_picard` at
   `n_retry` with `full_instanton_seed=seed`, under
   `h.MonkeypatchGuard(h.picard_module, MAX_OUTER=max_outer_cap)`.
3. **Step 2 — record, per delta:** `delta`, `delta / bias_n5` (the
   dimensionless ratio a reader actually wants), `converged`,
   `final_residual`, `bailout_tag`, `bailout_reason`, `final_lambda`,
   `gradient_enhancement_E`, `msr_action` (if converged, via
   `h.compute_msr_action`, same pattern as every other diagnostic in this
   module), `outer_iterations`, `wallclock`.
4. **Step 3 — persist** the n=5 baseline measurement and the full n=9 sweep
   together in one JSON via `h.save_json`, at
   `f"{OUT_DIR}/diagnostic9_bias_corrected_n_retry.json"` (`OUT_DIR` is the
   module-level constant already used by every other diagnostic here).
5. **Step 4 — print a clear summary** at the end: the measured `bias_n5`,
   then a table of `(delta/bias_n5, converged, final_lambda, msr_action,
   bailout_tag)` — enough for a human to read the classification straight
   off stdout without opening the JSON.
6. **Wire it up**: add `"9": lambda args: diagnostic_9_bias_corrected_n_retry()`
   to `_DIAGNOSTIC_DISPATCH`, add `"9"` to nothing else (it takes no
   diagnostic-specific CLI flags beyond the shared `--diagnostic` selector —
   don't add new argparse options unless you find you need them; if the
   `delta_fractions`/`n_retry` defaults turn out to need overriding often,
   flag that in your own completion note rather than guessing at flag names
   now).

## Constraints

- No file under `ComputeTargets/`, `Numerics/`, or `Datastore/` changes.
  Confirm this with `git diff --stat` before/after and include it in your
  completion note.
- `wallclock_budget_seconds` default is `900.0` (matching `diagnostic_6`'s
  own n≥9 budget, not `diagnostic_3`'s `500.0`) — n=9 Picard sweeps are
  individually more expensive than n=5's, so wallclock, not outer-iteration
  count, is the binding constraint here.
- Reuse `h.MonkeypatchGuard`, `h.save_json`, `h.output_dir`,
  `h.full_instanton_seed_from` etc. exactly as the existing diagnostics do —
  no parallel/duplicate helper functions.
- Keep the function's docstring at the same level of interpretive framing as
  `diagnostic_8_alpha_sensitivity`'s own docstring (state what a "bias
  confirmed" vs "bias not confirmed" result would mean, so a future reader
  doesn't have to reconstruct the reasoning from this prompt file).

## Must NOT

- Must NOT modify `picard.py`, `forward_rhs.py`, or any other production
  file — this is a pure diagnostics-harness addition.
- Must NOT hardcode an absolute `delta` value copied from Diagnostic 3a's
  `m=1e-3` result — the whole point of Step 0 is to derive a point-specific
  scale instead.
- Must NOT report a wallclock-budget bailout as if it were a genuine
  "did not converge at this delta" result — keep `bailout_tag`/
  `bailout_reason` visible in both the persisted JSON and the printed
  summary, exactly as Diagnostics 5/6/7/8a already do.
- Must NOT change the existing behaviour, numbering, or output filenames of
  Diagnostics 1–8.
- Must NOT attempt to also implement the `tau_multiplier` production change
  in the same commit — that is a separate, already-scoped follow-on prompt
  (see `DIAGNOSTICS_SUITE.md` §5) and is out of scope here regardless of
  what this diagnostic finds.

## Acceptance test

- [ ] `git diff --stat` shows changes confined to
      `tools/diagnostics/GradientCoupledInstanton/convergence_floor.py`.
- [ ] `bias_n5` is computed from a real `n=5` solve at
      `(m=1e-2, delta_Nstar=0.5)`, not assumed or hardcoded, and is printed
      and persisted before the `n=9` sweep results.
- [ ] The `n=9` sweep runs at, at minimum, `delta_fractions=(0.0, ±0.3, ±1.0, ±3.0)`
      (7 points) without raising, and every point's outcome (converged or
      not, with `bailout_tag`) is captured in the output JSON.
- [ ] `python -m tools.diagnostics.GradientCoupledInstanton.convergence_floor --diagnostic 9`
      runs this diagnostic end-to-end via the CLI and exits 0.
- [ ] Output JSON exists at
      `tools/diagnostics/GradientCoupledInstanton/output/convergence_floor/diagnostic9_bias_corrected_n_retry.json`
      and contains both the `bias_n5` measurement and the full sweep.
- [ ] A short completion note (matching the narrative style of the existing
      `24a`/`24b` design notes — a few paragraphs, not just "tests pass")
      reports: the measured `bias_n5`; whether any swept `delta` converged
      at `n=9`; and, per this prompt's own framing, an explicit
      classification — "fixed-target-bias mechanism confirmed at n=9" or
      "clean negative, mechanism not confirmed" — with the evidence for
      that call stated plainly (a clean negative is a valid, complete result
      here, per this project's existing convention; it is not grounds to
      keep tuning `delta_fractions` until something converges).

## Decision point

Report back with the classification before doing anything further:

- **If confirmed** (some `delta` converges at `n=9`): recommend, but do not
  yet implement, whether the next step should be a production two-pass /
  Anderson-damped self-consistent `g_pi_core` target (the follow-on 24a's
  own Diagnostic 3b already flagged as unbuilt), versus treating this
  diagnostic as sufficient evidence and still running the `tau_multiplier`
  study for completeness before drawing conclusions about n-convergence.
- **If not confirmed** (no swept `delta` converges within the tested range):
  recommend proceeding directly to the `tau_multiplier` production prompt
  and Diagnostic 8t, since this result would rule out the cheaper
  explanation.
