### Prompt P7 — Diagnostics as first-class figures (`figures/diagnostics.py`)

- **Implements:** design §8 in full.
- **Track / step:** P7
- **Depends on:** P4
- **Files (real paths):**
  - add:  `plotting/figures/diagnostics.py`
  - edit: `plotting/fetch.py` (fuse the diagnostics-collection pass into the
    existing DOE scalar-collection fetch — see Task item 1; this touches
    the generic `fetch_over_grid`/DOE-collection call site added in P1, not
    its internals)
- **Context to read first:** `plotting/adapters/base.py::InstantonAdapter.diagnostics()`
  (P2/P4 — a uniform pure read across all three kinds, already required by
  the base protocol); `ComputeTargets/GradientCoupledInstanton/picard.py`'s
  diagnostics-dict construction (the `diagnostics = {...}` literal near the
  end of `solve_picard`, and `_aggregate_rk45_stats`) — read this to confirm
  the exact key names before using them, don't take the list below on faith
  alone; `ComputeTargets/FullInstanton.py`'s own compute-time diagnostics
  (whatever the current `instanton_compute_times` figure reads) to convert
  it to adapter-fed rather than FullInstanton-specific.
- **Assumable interfaces:** `InstantonAdapter.diagnostics() -> Optional[dict]`
  rehydrates on the cheap `_do_not_populate=True` scalar fetch for every
  kind (the parent-row `diagnostics_json` blob, not gated on child-row
  fidelity) — confirmed for GCI post-U3, and already true for
  `FullInstanton`/`SlowRollInstanton`. GCI's diagnostics keys, verified
  directly against `picard.py` (state the exact set found; do not guess a
  superset or subset):
  - convergence: `converged`, `final_residual`, `outer_iterations`,
    `newton_fallback_count`, `final_lambda`
  - iteration structure: `picard_iterations_per_outer`,
    `min_picard_iterations`, `max_picard_iterations`, `mean_picard_iterations`,
    `mean_time_per_picard_iteration`
  - cost: `total_ode_solves`, `compute_time`, `compute_time_total`
  - RK45 stiffness: `rk45_{forward,backward}_total_steps`, `_accepted_steps`,
    `_rejected_steps`, `_min_step`, `_max_step`, `_steps_per_efold`
  - sweep timing: `picard_sweep_wallclock_min/mean/max`
  - scale assignment: `scale_assignment.{r_max, r_peak, r_phys_out, r_max_at_grid_edge, r_peak_at_grid_edge}`
  - extraction health: `extraction_failure_mask` (per-node bool array — a
    spatial health map, only meaningful alongside a `SpatialAdapter`)
- **Task:**
  1. Fuse diagnostics collection into the existing DOE scalar-collection
     pass: wherever the driver already does a shard-binned
     `_do_not_populate=True` vectorized fetch to build `scalar_data.csv`
     (the function moved to `plotting/fetch.py` in P1,
     `_collect_doe_scalar_data`'s replacement/generalisation), also pull
     `.diagnostics()` off each fetched adapter in that same pass — no
     second fetch pass, since the diagnostics blob rides on the same parent
     row (design §8's own point: "this costs essentially nothing extra").
  2. **Compute-time distributions**: per-solver (converged vs.
     non-converged), medians — generalise the existing
     `instanton_compute_times` figure to read `.diagnostics()["compute_time"]`/
     `["converged"]` off a list of adapters instead of FullInstanton-specific
     fields.
  3. **Cost vs. parameters**: compute-time and `total_ode_solves` vs. δN★ and
     ΔN, binned means/heatmaps.
  4. **Convergence map**: converged/non-converged scatter over `(δN★, ΔN)`;
     for GCI, add facets over `alpha`/`n_collocation_points` (read off
     `adapter.coords`, populated per P4).
  5. **Speed-up**: GCI vs. FI vs. SR compute-time ratios where the same
     grid point exists across more than one solver — matchable because
     adapters share the same `coords` keys (`N_init`/`N_final`/`delta_Nstar`)
     across kinds (design §7.5/§8 item 4's "genuine cross-solver comparison").
  6. **Picard/Newton structure** (GCI-only): outer-iteration and
     Picard-iteration-count distributions; Newton-fallback frequency vs.
     where in parameter space — skip (no-op, not an error) for any adapter
     where these keys are absent (i.e. non-GCI adapters).
  7. **Stiffness** (GCI-only): RK45 steps-per-efold, forward vs. backward,
     vs. δN★.
  8. **Extraction-failure map** (GCI-only, spatial): fraction of failed
     shells vs. grid point, and a per-node (vs. `y`) failure heatmap for
     individual solves — gate this one specifically on
     `adapter.is_spatial()` (it needs `y_nodes`, from `SpatialAdapter`, P4),
     unlike items 6–7 which only need the cheap-tier `diagnostics()` dict.
  9. Emit `diagnostics_data.csv` next to `scalar_data.csv`, with a matching
     row-key convention (same grid-point identification columns), so
     `regression_InstantonOutputs.py` or a sibling script can consume
     solver cost/convergence as regression targets alongside `C_bar_max`/
     `C_max`/`M_PBH`.
- **Constraints:** follow the conventions checklist; plus: every figure in
  this file must be solver-agnostic via the adapter — GCI-specific figures
  (items 6–8) key off "does this adapter's `.diagnostics()` contain this
  key" or `.is_spatial()`, never `adapter.kind == "gradient-coupled"`.
- **Must NOT:** add a second, separate diagnostics-collection fetch pass;
  must NOT read any GCI-specific diagnostics key from a non-GCI adapter (use
  `.get(key)` and skip/`None` when absent, don't assume presence); must NOT
  compute any of the diagnostics values here — they are read verbatim off
  the persisted `diagnostics_json` blob.
- **Acceptance test:** a named smoke test rendering all nine figure
  families (items 2–8, plus the CSV emission in item 9) against a mixed
  fixture set (some `FullInstanton`, some `SlowRollInstanton`, some
  `GradientCoupledInstanton` records, including at least one
  non-converged GCI record) without error, and asserting
  `diagnostics_data.csv` and `scalar_data.csv` share the same set of
  grid-point identifying columns (so a downstream join is possible).
- **Decision point:** none.
