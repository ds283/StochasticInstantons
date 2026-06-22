# StochasticInstanton — Sparse Sampling Handoff

_Last updated: 2026-06-22. Generated at the close of the sparse-sampling
implementation session._

---

## 1. What the pipeline does

StochasticInstanton computes PBH formation probabilities using the
Martin-Siggia-Rose (MSR) path-integral / instanton method in stochastic
inflation. For each parameter triple `(N_init, N_final, delta_Nstar)` under a
chosen inflaton potential, it:

1. Solves the MSR BVP (`FullInstanton`) and slow-roll approximation
   (`SlowRollInstanton`) to obtain the instanton trajectory and saddle-point
   action `S_MSR`.
2. Embeds the instanton in the background spacetime to compute the curvature
   perturbation profile `ζ(r)` and the compaction function `C(r)`,
   `C̄(r)` (`CompactionFunction`).
3. Extracts scalar summaries: `C_max`, `C̄_max`, collapse scale `r_PBH`,
   PBH mass `M_PBH`, and `S_MSR` — which together determine whether PBH
   formation occurs and at what mass.

**Key threshold**: `C̄_max > 0.4` (configurable) → PBH forms.

**Parameter meanings**:
- `N_init`: e-folds before end of inflation at the instanton start point.
- `N_final`: e-folds before end of inflation at the instanton endpoint.
- `delta_Nstar`: excess e-folds accumulated by the instanton relative to
  the noiseless background, ≈ peak ζ (controls amplitude → threshold
  crossing).
- `ΔN = N_init − N_final`: controls the log width of the enhanced
  perturbation spectrum.
- `N_final` sets the absolute physical scale (mass, Mpc) — largely
  decoupled from the compaction function shape.

**Effective parameter space**: `(delta_Nstar, ΔN)` governs the physics;
`N_final` governs the mass calibration.

**Fiducial range** (quadratic potential, `m = 1e-5 Mp`):
```
N_init      ∈ [19.5, 22.0]
N_final     ∈ [16.0, 19.0]
delta_Nstar ∈ [0.1,  3.0]
```
PBH threshold crossed at `delta_Nstar ≳ 2.3` for typical `(N_init, N_final)`.

---

## 2. State of the codebase

All prompts listed below are implemented, committed, and smoke-tested against
a 5 × 5 × 5 = 125-point test grid.

### Prompt inventory (`.prompts/sparse-sampling/`)

| File | What it does |
|------|-------------|
| `01-extrapolation-diagnostic-flag.md` | Adds `r_max_C_bar_extrapolated` and `r_max_C_at_grid_edge` boolean keys to `CompactionFunction` diagnostics. |
| `02-sample-grid-csv-main.md` | `config/grid_builder.py` + `--sample-grid-csv` in `main.py`. CSV of explicit `(N_init, N_final, delta_Nstar)` triples replaces the Cartesian axis grid. |
| `02b-live-sharded-pool-fixture-dedup-test.md` | Live `ShardedPool` pytest fixture; dedup integration test confirming CSV and axis-grid paths mint the same `store_id`s. |
| `03-sample-grid-csv-plot-script.md` | `--sample-grid-csv` wired into `plot_InstantonSolutions.py`. Sweep plots restored in CSV mode (sparse is fine); `_generate_instanton_samples` skipped when `--no-store-values`. |
| `04-scalars-only-full-slowroll-instanton.md` | `set_store_full_values(False)` + `_do_not_populate` build-time guard for `FullInstanton` / `SlowRollInstanton`. |
| `05-scalars-only-compaction-function.md` | Same for `CompactionFunction` (single combined flag, `metadata` column, partial-failure cases). |
| `06-populate-from-result-refactor.md` | `_populate_from_result(data)` extracted from `store()` on all three compute targets. Prerequisite for the pipeline remote function. |
| `07-pipeline-work-item.md` | `ComputeTargets/pipeline.py`: `@ray.remote(num_cpus=0) compute_pipeline(...)` + `PipelineWorkItem`. Integrity check (`_check_scalar_integrity`) on pre-existing scalar-only rows. |
| `08-pipeline-wiring-main.md` | `--no-store-values` CLI flag; `_run_pipeline_queue` + `_persist_pipeline_item` in `main.py`. Replaces Stages 2+3+4 with a unified pipeline when flag is set. |
| `09-doe-summary-plots.md` | `_collect_doe_scalar_data`, `plot_doe_scalar_summary`, `_run_doe_summary_plots` in `plot_InstantonSolutions.py`. Produces scatter plots and `scalar_data.csv`. |
| `10-provenance-footer.md` | Two-line provenance footer: database name, config file, `[summary-only]` flag, version, timestamp. |

### Key new behaviours

**`--no-store-values` mode**
- Activates unified pipeline: all three compute targets computed in one
  `@ray.remote` task per grid point (no inter-stage DB round-trips).
- Only scalar parent-row columns are persisted; per-sample value rows are
  skipped. `diagnostics_json` records `"full_values_stored": false`.
- Build-time guard raises `RuntimeError` if you attempt to populate a
  scalar-only object without `_do_not_populate=True`.
- Storage: ~5–10× smaller than full-fidelity; fast enough for O(1000)-point
  DOE runs in reasonable time.

**`--sample-grid-csv <path>`**
- CSV format: header `N_init,N_final,delta_Nstar` (case-sensitive);
  float values; any column order.
- Replaces the Cartesian axis grid entirely; crossed only against the model
  list, not against itself.
- Compatible with `--no-store-values` (the intended combination for DOE
  runs).

**DOE outputs**
- `plot_InstantonSolutions.py --no-store-values` produces:
  - Sweep plots of `C̄_max`, `M_PBH`, `r_PBH` vs each axis
    (sparse but correct).
  - DOE scatter plots in `(delta_Nstar, ΔN)` space under `doe_summary/`.
  - `doe_summary/scalar_data.csv`: flat table of all scalar outputs,
    one row per grid point — the primary input for GP regression.

---

## 3. Immediate next task: Latin hypercube grid generation

A standalone Python script (suggest `config/generate_lhc_grid.py`) that
produces a `--sample-grid-csv`-compatible CSV.

### Design decisions already settled

- **Effective 2D space**: sample primarily in `(delta_Nstar, ΔN)` since
  these are the physics-controlling parameters. `N_final` is a coarse third
  axis (3–5 values spanning [16, 19]) overlaid on the 2D design.
- **`N_final` decoupling** (Step 1 validation, see §4 below) should be
  done before the main DOE run to confirm `N_final` can be treated as
  near-independent.
- **Method**: `scipy.stats.qmc.LatinHypercube(d=2)` or `Sobol(d=2)` for
  the `(delta_Nstar, ΔN)` plane. Sobol gives better space-filling
  properties for sensitivity analysis; LHC is simpler and more familiar.
  Either is fine for an initial campaign.
- **Constraint**: `ΔN > 0` (i.e. `N_init > N_final`). Enforce at
  generation time, not post-hoc.
- **Derived columns**: from the 2D design + a fixed `N_final` value, compute
  `N_init = N_final + ΔN`. Output columns are `N_init`, `N_final`,
  `delta_Nstar`.
- **Reproducibility**: seed the sampler explicitly and record the seed in
  the CSV header comment (e.g. `# seed=42 n=500 method=sobol`).
- **Number of points**: ~500 initial points in `(delta_Nstar, ΔN)` per
  `N_final` slice is a reasonable starting point. Adjust based on compute
  budget (pipeline runs at ~200–300 instantons/min on M1).

### Suggested script interface

```
python3 config/generate_lhc_grid.py \
    --delta-nstar-low 0.1 --delta-nstar-high 3.0 \
    --delta-N-low 0.5    --delta-N-high 6.0 \
    --N-final-values 16.0 17.5 19.0 \
    --n-points 500 \
    --method sobol \
    --seed 42 \
    --output lhc_grid_500.csv
```

The script should:
1. Generate `n_points` quasi-random samples in the unit square using the
   chosen method.
2. Map to `(delta_Nstar, ΔN)` using the specified bounds.
3. For each `N_final` value, compute `N_init = N_final + ΔN` and emit a row.
4. Drop any rows where `N_init > N_init_max` (configurable; default 25 or so)
   or `delta_Nstar < delta_Nstar_min`.
5. Write the CSV with the header comment and column header
   `N_init,N_final,delta_Nstar`.

---

## 4. Step 1 validation (before large DOE run)

Test the `N_final`-decoupling hypothesis with a cheap targeted run (~20
points):

- Fix `ΔN = 3.5`, `delta_Nstar ∈ {1.0, 2.0, 2.5}`.
- Vary `N_final ∈ {16.0, 17.0, 18.0, 19.0}`.
- Run with `--no-store-values` (fast, minimal storage).
- Check: `C̄_max_full` and `C_max_full` are invariant across `N_final` at
  each fixed `(ΔN, delta_Nstar)`.
- Check: `M_PBH` and `r_PBH` scale as `exp(−N_final × something)` —
  i.e., pure mass/scale shift.
- If invariant: treat `N_final` as a near-independent "calibration" axis
  and sample it coarsely (3–5 values). This is the expected result.
- If NOT invariant: investigate before investing in a large DOE run. This
  would imply the Hubble-rate variation across `N_final` affects the
  compaction shape non-trivially.

---

## 5. Subsequent steps: sensitivity analysis and active learning

### 5.1 GP regression on DOE output

**Input**: `scalar_data.csv` from `plot_InstantonSolutions.py
--no-store-values`.

**Outputs to model**: `C_bar_max_full`, `msr_action_full`, `M_C_bar_full_solar`,
`r_max_C_bar_full_Mpc` (and slow-roll equivalents for comparison).

**Suggested library**: `scikit-learn`'s `GaussianProcessRegressor` with a
Matérn(5/2) kernel + automatic relevance determination (one length-scale
per input dimension), on standardised `(N_init, N_final, delta_Nstar)` or
`(delta_Nstar, ΔN, N_final)`.

**What to fit first**: `C_bar_max_full − 0.4` (signed distance to threshold)
as a continuous regressor, rather than the binary threshold-crossing. The
posterior mean and variance directly identify the threshold boundary and
the uncertainty about its location.

### 5.2 Sobol sensitivity indices

Compute first-order and total-effect Sobol indices on the fitted GP
surrogate (not on the raw data directly — the sparse DOE design isn't a
Saltelli sequence). `SALib` can compute indices from the GP posterior.

Expected result based on physical reasoning:
- `delta_Nstar` dominates `C̄_max` (it controls amplitude).
- `ΔN` has moderate effect (controls how the gradient spreads).
- `N_final` has negligible effect on `C̄_max` (mostly decoupled).
- `N_final` dominates `M_PBH` and `r_PBH` (absolute scale).

### 5.3 Threshold boundary identification

The PBH abundance is exponentially sensitive to the location of the
`C̄_max = 0.4` boundary in parameter space. After fitting the GP:

1. Find the iso-surface `GP_mean(x) = 0` in `(delta_Nstar, ΔN)` space
   (at fixed `N_final`).
2. Quantify uncertainty on the boundary location from the GP posterior
   variance.
3. Generate a refined plot of the boundary in `(delta_Nstar, ΔN)` space.

### 5.4 Active learning refinement

To sharpen the boundary estimate cheaply:

1. Score a dense candidate pool (e.g. 10,000 Sobol points in the design
   space) using an acquisition function — simplest: minimise
   `|GP_mean(x)| / GP_std(x)` (points near the boundary with high
   uncertainty).
2. Take the top-K candidates, write as a new `--sample-grid-csv` CSV.
3. Run `main.py --no-store-values --sample-grid-csv <new_csv>`.
4. Append results to `scalar_data.csv`, refit the GP.
5. Repeat 2–3 iterations.

This is the step most likely to require a standalone Python script (outside
`plot_InstantonSolutions.py`) since it needs the fitted GP model, the
candidate pool, and the CSV writer.

---

## 6. Deferred / open questions

These were identified and discussed but deliberately set aside:

- **`ρ_final` boundary condition**: switching `FullInstanton`'s terminal BC
  from `φ_final` to `ρ_final` was attempted but failed due to a
  degrees-of-freedom counting issue. Left for a future session.
- **Relationship between `S_instanton` and spectral eigenvalue sum** in the
  Ezquiaga–García-Bellido–Vennin formalism: the Sturm-Liouville
  orthogonality obstacle stalled a derivation. Unresolved.
- **Double-failure handling in pipeline**: when both `FullInstanton` and
  `SlowRollInstanton` fail for the same grid point, `_persist_pipeline_item`
  raises rather than persisting the failure rows. Acceptable for DOE runs
  (rare case), but diverges from Stage 2/3/4 behaviour.

---

## 7. Rules files

Codebase invariants are encoded in `.claude/rules/` scoped rules files:
`ray-dispatch.md`, `datastore-factories.md`, `compute-targets.md`. These
should be included or read by Claude Code in any session that modifies
those layers.

---

## 8. Quick-start for the new session

```bash
# Generate LHC grid (script to be written)
python3 config/generate_lhc_grid.py \
    --delta-nstar-low 0.1 --delta-nstar-high 3.0 \
    --delta-N-low 0.5 --delta-N-high 6.0 \
    --N-final-values 16.0 17.5 19.0 \
    --n-points 500 --method sobol --seed 42 \
    --output lhc_grid_500.csv

# Run DOE pipeline
python3 main.py \
    --database doe-run-500.sqlite \
    --config quadratic-asteroid-small.yaml \
    --sample-grid-csv lhc_grid_500.csv \
    --no-store-values

# Plot and export scalar data
python3 plot_InstantonSolutions.py \
    --database doe-run-500.sqlite \
    --config quadratic-asteroid-small.yaml \
    --output-dir out-doe-500 \
    --no-store-values

# scalar_data.csv is at:
# out-doe-500/<traj_dir>/doe_summary/scalar_data.csv
```
