# DIAGNOSTICS_SUITE — `tools/diagnostics/GradientCoupledInstanton`

Standalone, Ray/Datastore-bypassing diagnostic suite for the
`GradientCoupledInstanton` compute target (informally "GCI" in prose below;
the code and directory name always spell it out in full). Nothing in this
package is imported by production code (`main.py`, `ComputeTargets/`,
`Datastore/`) — it is a consumer of the production API
(`solve_picard`, `_compute_full_instanton`, `LGLCollocationGrid`, ...), never
the other way around, and no production file is modified by anything here.

This document replaces the ad hoc "run this script, then that one, in this
order" knowledge that previously lived only in each prompt's own design note.
It follows `.documents/FILE_MAP.md`'s own per-file-purpose convention.

---

## 1. Package layout

| File | Purpose |
|---|---|
| `__init__.py` | Package docstring/version; no logic. |
| `__main__.py` | Lets the whole package run as `python -m tools.diagnostics.GradientCoupledInstanton <subcommand>`. |
| `cli.py` | Unified argparse dispatcher across all subcommands (see §3). Each module also remains independently runnable as `python -m tools.diagnostics.GradientCoupledInstanton.<module> ...`. |
| `harness.py` | Shared setup/fetch/IO/monkeypatch helpers factored out of the three predecessor scripts (see §2). Every other module imports from here; nothing here imports from them. |
| `convergence_floor.py` | Diagnostics 1–8: the `delta_Nstar`/mass/`n_collocation_points`/`OUTER_TOL`/`alpha_regularization` convergence-floor campaign (prompts 24a, 24b, and the new Diagnostic 8). |
| `trajectory_plots.py` | Trajectory-validation plots (phi/pi(N) vs FullInstanton, epsilon(N), y-profile, action-ratio-vs-sweep-variable) for any converged-solve JSON+`.npz` record produced by `convergence_floor.py`. |
| `seed_screen.py` | Cheap `alpha_regularization` vs `n_collocation_points` zeroth-Picard-iterate pre-screen, before spending a full solve budget on an untested corner. |
| `spectrum.py` | Assembled-operator eigenvalue sweep + discrete-adjoint diagnostic (prompts 17/18/18a/20/21/21a/23) for the onion-model spatial discretisation. Self-contained: frozen-coefficient, potential-independent synthetic operators, no `harness.py`/`InflatonTrajectory` dependency. |
| `archive/prompt22_validation.py` | Historical replay of prompt 22's own validation harness (Findings 1/1b/2 — the `phi_end` degeneracy and Picard divergence that blocked Studies A–E until 22a/22c/24b). Not part of the active CLI; kept for provenance only. |
| `output/` | Created on demand (`.gitignore`-able); every diagnostic writes its JSON/CSV/`.npz`/PNG records under `output/<module-name>/`, replacing each predecessor script's own bespoke `..._output/` directory. |

---

## 2. What moved into `harness.py`, and why

Before this refactor, `diagnose_24a_convergence_floor.py`,
`compare_gradient_full.py`, and `validation_22_resolved_regime.py` each
independently reimplemented:

- `_PotentialHolder` / `_TrajProxyStub` (or `_TrajectoryProxyStub`) — the
  duck-typed stand-in `_compute_full_instanton` needs when called outside
  Ray/Datastore. Identical in all three; a single class now.
- A `setup()`/background-trajectory-builder, cached by mass only in the
  original scripts (now cached by `(m, phi0, pi0, atol, rtol)`, so a future
  initial-condition sensitivity study doesn't need a fourth copy).
- A `production_phi_end()` helper — **this is where the three scripts had
  already silently drifted**: `compare_gradient_full.py` and
  `validation_22_resolved_regime.py`'s own copies still computed the
  **pre-22a degenerate** formula (`traj.phi_at(N_offset + N_total)`, prompt
  22's own Finding 1), while `diagnose_24a_convergence_floor.py`'s copy had
  already been updated to the corrected, current-production formula
  (`traj.phi_at(traj.N_end - N_final)`). `harness.production_phi_end` is
  now the single, current-production definition; the archived script keeps
  its own pre-22a copy only because reproducing that exact historical bug
  is the entire point of Finding 1 (see its own module docstring).
- `fetch_full_instanton()` / the four-key `full_instanton_seed` dict literal
  — repeated at nearly every call site across every script; now
  `harness.fetch_full_instanton` / `harness.full_instanton_seed_from`.
- The `solve_shooting`-monkeypatch pattern for single-lambda evaluation
  (Diagnostic 1/2's engine) and for capturing the last `commit()`-ed Picard
  state on a non-convergent solve (Diagnostic 3b) — now
  `harness.sweep_evaluate` / `harness.capture_last_commit`.
- The `try: setattr(...) / finally: restore` pattern used everywhere to
  temporarily override `MAX_OUTER`/`MAX_INNER`/`OUTER_TOL_FLOOR` — now
  `harness.MonkeypatchGuard`, a context manager, so a diagnostic can no
  longer forget the `finally` and leave an override live.
- The ad hoc `.npz` schema `diagnostic_4`/`plot_24b_trajectories.py`
  invented between themselves for persisting full `(N, y)` grids — now
  `harness.save_grids_npz` / `harness.load_grids_npz`, a single documented
  schema any future diagnostic can reuse.

`explore_onion_stiffness.py` (`StubPotential`, `build_real_trajectory`,
`run_case`) lives alongside `harness.py` in this package — it predates every
diagnostic this suite consolidates and was not one of the scripts being
merged, but it was relocated here (from the old `out-gradient-coupled-stiffness/`
scratch directory) so the package no longer depends on anything outside
itself. **`run_case` is currently broken against production `forward_rhs`**
(it predates the `g_pi_core_spline` SAT-penalty argument — see `seed_screen.py`'s
own module docstring), so `seed-screen` is a known-broken subcommand pending
a follow-up physics decision; it is not fixed by this relocation.

---

## 3. CLI quick reference

```bash
# Everything (equivalent to running each diagnostic 1-8 in turn):
python -m tools.diagnostics.GradientCoupledInstanton convergence-floor --diagnostic all

# Just the delta_Nstar walk (Diagnostic 4), then plot its trajectories:
python -m tools.diagnostics.GradientCoupledInstanton convergence-floor --diagnostic 4
python -m tools.diagnostics.GradientCoupledInstanton trajectory-plots \
    --input convergence_floor/diagnostic4_delta_nstar_walk.json

# New: alpha-regularization sensitivity at every converged 24b point
# (resurrects prompt 22's Study C, alpha half):
python -m tools.diagnostics.GradientCoupledInstanton convergence-floor --diagnostic 8a \
    --alpha-values 0.01,0.05,0.1,0.3
python -m tools.diagnostics.GradientCoupledInstanton trajectory-plots \
    --input convergence_floor/diagnostic8a_alpha_sensitivity.json --x-key alpha

# Cheap pre-screen before spending a full solve budget on an untried
# (alpha, n_collocation_points) corner:
python -m tools.diagnostics.GradientCoupledInstanton seed-screen \
    --n-colloc 5,7,9,11,13,17,25,33 --alpha-powers 0,1,2,3

# Assembled-operator spectral abscissa / adjoint diagnostics (unaffected by
# this refactor -- see §5):
python -m tools.diagnostics.GradientCoupledInstanton spectrum \
    --mode spectrum --closure sbp-sat --plot
```

Every module also runs standalone
(`python -m tools.diagnostics.GradientCoupledInstanton.convergence_floor ...`)
if you only need one of them in a script.

Environment: set `STOCHASTIC_INSTANTONS_REPO` if the main repository isn't
checked out at the hardcoded default path every predecessor script used
(`harness.py` falls back to that default, matching the original scripts'
behaviour unmodified).

---

## 4. Diagnostic-to-provenance map

| Diagnostic | Provenance | What it answers |
|---|---|---|
| 1, 2 | prompt 24a | Is `evaluate(lambda)` well-posed at all, per mass? Does the Part-B lambda-rescaling hold end-to-end? |
| 3 (3a/3b) | prompt 24a | Is the `delta_Nstar=1` floor explained by the fixed `pi_core` SAT-target bias? (3a: yes, curable by a small correction. 3b: a naive automatic two-pass correction diverges — clean negative.) |
| 4 | prompts 24a/24b | The first genuinely non-trivial converged solves (`delta_Nstar∈{0.2,0.3,0.5,0.7}`, `m=1e-2`, `n=5`) — this suite's own baseline result. |
| 5 | prompt 24b Part C | Retries `delta_Nstar=1.0` across all four masses under the corrected seed/corridor — still a clean negative (fixed-target bias, not a seeding problem). |
| 6 | prompt 24b Part C | Retries `n∈{9,17}` at a known-converged point — still a clean negative (see §6, "The n≥9 question", for what this suite recommends trying next). |
| 7 | prompt 24b | `OUTER_TOL` sensitivity — confirmed not doing physics at the three converged points. |
| 8a | new (resurrects prompt 22 Study C, alpha half) | `alpha_regularization` sensitivity at every converged Diagnostic-4 point. Fully runnable today — `alpha` is already a first-class `solve_picard` parameter. |
| 8t | new (resurrects prompt 22 Study C, tau half) | **Not yet runnable** — see §5. |
| `archive/prompt22_validation.py` | prompt 22 | Historical: the `phi_end` degeneracy (Finding 1) and Picard divergence (Finding 2) that blocked Studies A–E until 22a/22c/24b. Kept for provenance only. |
| `seed_screen.py` | prompt 17-era `compare_gradient_full.py`, modernized | Cheap zeroth-Picard-iterate `alpha` vs `n_collocation_points` pre-screen. |
| `spectrum.py` | prompts 17/18/18a/20 | Assembled-operator spectral abscissa (stability envelope) and discrete-adjoint-consistency diagnostics for the SBP-SAT closure. |

---

## 5. Known gaps (read before running Diagnostic 8)

**Diagnostic 8t (tau-sensitivity) is not implemented and will raise
`NotImplementedError` if called.** `tau = abs(A_core)` is currently a
hardcoded local inside `ComputeTargets/GradientCoupledInstanton/forward_rhs.py`'s
core SAT penalty, not a parameter threaded through `solve_picard` — unlike
`OUTER_TOL_FLOOR`, which prompt 24b already extracted into a module constant
specifically so a diagnostic could override it. There is no monkeypatch
point available from outside production code for a value computed inline
mid-function.

Running the tau study needs a small, explicitly-scoped **production** change
first (a follow-on numbered prompt, not part of this diagnostics-package
refactor):

> Add `tau_multiplier: float = 1.0` to `forward_rhs`'s core-SAT-penalty
> construction (`tau = tau_multiplier * abs(A_core)`), threaded through
> `picard.solve_picard`'s own signature, default reproducing current
> behaviour bit-for-bit. Single commit, single acceptance test: "with
> `tau_multiplier=1.0`, every existing golden result
> (`delta_Nstar∈{0.2,0.3,0.5,0.7}`, `m=1e-2`, `n=5`) reproduces bit-for-bit."

Once that lands, `diagnostic_8_tau_sensitivity` in `convergence_floor.py`
should sweep `tau_multiplier∈{0.5, 1.0, 2.0}` (i.e. the design note's minimal
admissible value, the current production value, and a further hardening) at
every Diagnostic-4 point, following the same pattern as `diagnostic_8_alpha_sensitivity`.

**`archive/prompt22_validation.py` is frozen, not maintained.** Its own
`production_phi_end` deliberately reproduces the pre-22a degenerate formula
it was written to diagnose — do not "fix" it to match
`harness.production_phi_end`, that would silently break the comparison the
whole script exists to make.

---

## 6. Open questions this suite is set up to answer next

Carried over from the July 2026 handoff brief
(`HANDOFF-gradient-coupled-instanton.md`) and the conversation that produced
this refactor:

- **n-convergence** (prompt 22 Study A): still zero evidence. `diagnostic_6_n_colloc`
  reproduces the `n∈{9,17}` non-convergence; before assuming this needs a new
  numerical closure, the cheaper next step is retrying `n=9` with a small,
  controlled `pi_core` target perturbation in the style of Diagnostic 3a
  (`delta=+0.03`-type correction) — separating "n≥9 fails because of an
  under-resolved boundary layer" from "n≥9 fails because the resolution-
  independent fixed-target bias becomes more consequential once the
  discretization can see the sharper structure it approximates."
- **The `phi_core`/`pi_core` transient oscillation** (24b's own "cosmetic
  observation, not chased further"): `diagnostic_8_alpha_sensitivity` plus
  the pending tau study are the two cheap tests the handoff brief proposed;
  plotting the response field `r̃(y,N)` itself (the sharpest, "least-action"
  test — an oscillating optimal noise is strictly more expensive than a
  smooth one) is not yet wired into `trajectory_plots.py` and would be a
  natural next addition, resampling a converged solve's own
  `response_dense_solution`.
