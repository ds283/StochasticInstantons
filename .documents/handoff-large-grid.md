# StochasticInstanton — Handoff Document
_Last updated: 2026-06-23. Generated at the close of the sparse-sampling and
GP regression session._

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
   perturbation profile `ζ(r)` and the compaction function `C(r)`, `C̄(r)`
   (`CompactionFunction`).
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

---

## 2. State of the codebase

All prompts listed below are implemented and committed.

### Prompt inventory (`.prompts/sparse-sampling/`)

| File | What it does |
|------|-------------|
| `01-extrapolation-diagnostic-flag.md` | Adds `r_max_C_bar_extrapolated` and `r_max_C_at_grid_edge` boolean diagnostic keys. |
| `02-sample-grid-csv-main.md` | `config/grid_builder.py` + `--sample-grid-csv` in `main.py`. |
| `02b-live-sharded-pool-fixture-dedup-test.md` | Live `ShardedPool` pytest fixture; dedup integration test. |
| `03-sample-grid-csv-plot-script.md` | `--sample-grid-csv` wired into `plot_InstantonSolutions.py`. |
| `04-scalars-only-full-slowroll-instanton.md` | `set_store_full_values(False)` build-time guard. |
| `05-scalars-only-compaction-function.md` | Same for `CompactionFunction`. |
| `06-populate-from-result-refactor.md` | `_populate_from_result(data)` extracted from `store()`. |
| `07-pipeline-work-item.md` | `ComputeTargets/pipeline.py`: unified `@ray.remote compute_pipeline`. |
| `08-pipeline-wiring-main.md` | `--no-store-values` CLI flag; `_run_pipeline_queue` in `main.py`. |
| `09-doe-summary-plots.md` | DOE scatter plots and `scalar_data.csv` export. |
| `10-provenance-footer.md` | Two-line provenance footer on all figures. |
| `11-gp-regression.md` | `regression_InstantonOutputs.py`: five single-output GPs on scalar outputs. |
| `12-noise-amplitude-scalars.md` | `noise_phi1_min/mean/max` and `noise_phi2_min/mean/max` scalar columns on `FullInstanton` and `SlowRollInstanton`; twelve new columns in `scalar_data.csv`. |
| `12b-noise-profile-methods.md` | `noise_profile()` and `noise_profile_arrays()` methods on both instanton classes. |
| `13-diffusion-model-datastore.md` | `DiffusionModel` promoted to first-class datastore object following the `AbstractPotential` pattern. |

### Architecture notes relevant to the new session

**`--no-store-values` mode**: activates unified pipeline, scalars only. This
is the mode used for all DOE runs. Value rows (per-sample field profiles) are
only stored in full-fidelity runs.

**`generate_lhc_grid.py`** (`config/`): generates `--sample-grid-csv`-compatible
CSVs using Sobol or LHC sampling in `(delta_Nstar, ΔN, N_final)` space. Key
flags:
```
--delta-nstar-low/high   bounds for delta_Nstar
--delta-N-low/high       bounds for ΔN
--N-final-low/high       bounds for N_final
--n-points               total Sobol points
--method sobol|lhc
--seed
--output
```
Cartesian product mode (for validation runs) uses `--delta-nstar-values`,
`--delta-N-values`, `--N-final-values` together.

**`regression_InstantonOutputs.py`**: standalone GP regression script. Fits
five single-output GPs on `scalar_data.csv`. Outputs `.joblib` model files
and diagnostic plots. Run as:
```bash
python3 regression_InstantonOutputs.py \
    --scalar-data scalar_data-asteroid.csv \
    --output-dir regression_output/
```

**DiffusionModel** (prompt 13): `AbstractDiffusionModel` now inherits from
`DatastoreObject` and `ABC`. `FullInstanton` and `SlowRollInstanton` carry
`diffusion_serial` and `diffusion_type` columns (no FK constraint; polymorphic
dispatch via `DIFFUSION_MODEL_REGISTRY`, following `POTENTIAL_REGISTRY`
pattern). `InflatonTrajectory` no longer carries a diffusion model — it is
noiseless. The diffusion model is a peer input to the instanton solve alongside
the trajectory.

---

## 3. Scientific findings from completed DOE runs

### N_final decoupling (Step 1 validation)

Confirmed at fixed `ΔN = 3.5`, `N_final ∈ {16, 17, 18, 19}`:
- `C̄_max` and `C_max`: vary < 1.3% across N_final → treat as decoupled
- `M_PBH`: scales as `exp(1.974 × N_final)` (expected 2.0 from RD horizon mass)
- `r_PBH`: scales as `exp(0.987 × N_final)` (expected 1.0 from r ~ 1/k)
- `S_MSR`: decreases ~10–11% per e-fold in N_final (NOT decoupled; driven by
  V(φ) decreasing toward end of inflation)

**Consequence**: N_final is a calibration axis for mass/scale but must be
included as a full GP input dimension for S_MSR.

### Empirical scaling law for S_MSR

Fitted on both asteroid (N_final ∈ [15,25]) and solar (N_final ∈ [35,45])
datasets with R² = 0.993:

    S_MSR ~ delta_Nstar^1.74 · ΔN^{-0.72} · N_final^{-1.86}

Equivalently:

    S_MSR ~ (delta_Nstar / ΔN)^1.74 · ΔN^1.01

The exponent on ΔN alone is essentially 1. The dominant structure is:
- Action cost grows as a power of the "peakedness" ratio `delta_Nstar / ΔN`
- Broader spectra (larger ΔN) are cheaper at fixed δN★

**Local exponent trend** (d log S / d log δN★ at fixed ΔN, N_final):

| δN★ range | local exponent |
|-----------|---------------|
| [0.10, 0.83) | 1.871 |
| [0.83, 1.55) | 1.692 |
| [1.55, 2.27) | 1.587 |
| [2.27, 3.00) | 1.522 |

The exponent is falling and has not converged. The dataset only reaches
δN★ ≤ 3, which is just above the PBH formation threshold (~2.3 for typical
ΔN). Vennin's asymptotic linear prediction (exponent = 1) applies at large
δN★ — a regime not yet sampled. The data is in a transient region between the
Gaussian saddle-point limit (exponent 2) and the Vennin large-fluctuation
limit (exponent 1).

### Threshold boundary and minimum-action channel

The PBH formation threshold (`C̄_max = 0.4`) defines a rising curve in
(δN★, ΔN) space: wider perturbations need larger amplitude to collapse. The
GP fit (R² = 0.999) locates this boundary accurately within the sampled range.

The minimum-action formation channel at fixed M_PBH: within the sampled range
(ΔN ≤ 6), the optimizer always runs to the boundary at maximum ΔN. This is
consistent with the scaling law — at fixed mass, the cheapest path is always
the broadest perturbation that still crosses threshold. The ratio
`delta_Nstar / ΔN ≈ 0.55–0.62` along the minimum-action locus, nearly
constant across the mass range.

**Physical interpretation**: the dominant PBH formation channel is the
shallowest density profile (largest ΔN) that still collapses. This is
analogous to a critical bubble in a first-order phase transition — the
"critical instanton" is the one that barely crosses threshold.

### GP regression results

Five single-output GPs with Matérn(5/2) + ARD:

| GP | Target | R² (asteroid) | R² (solar) |
|----|--------|--------------|-----------|
| 1 | C̄_max | 0.9991 | 0.9997 |
| 2 | C_max | 1.0000 | 1.0000 |
| 3 | log(S_MSR) | 1.0000 | 1.0000 |
| 4 | log(M) | 0.8806 | 0.9970 |
| 5 | log(r) | 0.8802 | 0.9970 |

The R² = 0.88 on asteroid GPs 4–5 reflects genuine near-threshold nonlinearity
in (δN★, ΔN) → log(r_max), not a fitting failure. The solar dataset's larger
N_final range makes the N_final trend dominate the variance, giving higher R².
Active learning near the threshold boundary is the appropriate remedy.

---

## 4. Immediate next task: large exploratory grid

### Scientific questions to address

**Question 1**: Does the local exponent d(log S)/d(log δN★) approach 1 at
large δN★, as predicted by Vennin's asymptotic formula? At what δN★ does the
transition occur? Is this δN★ in a physically realistic regime (i.e. still
producing density perturbations that could form PBHs), or does it require
unrealistically large fluctuations?

**Question 2**: What is the minimum-action locus in (δN★, ΔN) space at fixed
M_PBH, extended to large ΔN? Is the relationship between δN★ and ΔN along
this locus simply "the shallowest perturbation that still collapses", or is
there additional structure? What does this imply for PBH abundance calculations
that use Vennin's linear formula?

### Strategy

A single large grid covers both questions simultaneously:
- Large δN★ (up to ~8) probes the asymptotic scaling of S_MSR
- Large ΔN (up to ~12) extends the collapse boundary search
- Fixed N_final (use N_final = 20, the asteroid-mass anchor) concentrates the
  full point budget in (δN★, ΔN)
- The joint (δN★, ΔN) surface including the large-δN★ / large-ΔN corner
  is where the minimum-action locus is expected to run

N_final is fixed at 20 because:
- The N_final dependence is already well-characterised (prompt 12 results)
- A single fixed N_final puts all 1000–1500 points into the two dimensions
  that answer the open questions

### Suggested grid parameters

```bash
python3 config/generate_lhc_grid.py \
    --delta-nstar-low  0.1  --delta-nstar-high  8.0 \
    --delta-N-low      0.5  --delta-N-high     12.0 \
    --N-final-low     19.5  --N-final-high     20.5 \
    --n-points        1500 \
    --method sobol \
    --seed 42 \
    --output large_grid_1500.csv
```

Using a narrow N_final band [19.5, 20.5] rather than a single value keeps
the Sobol sequence 3D (required by the script) while effectively fixing
N_final ≈ 20. The narrow band also gives a small sample of the local
N_final sensitivity as a consistency check.

Then run:
```bash
python3 main.py \
    --database large-grid-1500.sqlite \
    --config quadratic-asteroid.yaml \
    --sample-grid-csv large_grid_1500.csv \
    --no-store-values

python3 plot_InstantonSolutions.py \
    --database large-grid-1500.sqlite \
    --config quadratic-asteroid.yaml \
    --output-dir out-large-grid \
    --no-store-values
```

### Analysis to perform on the resulting scalar_data.csv

**For Question 1** (asymptotic scaling):
- Compute local exponent d(log S)/d(log δN★) in bins of δN★, after
  residualising against ΔN and N_final
- Plot exponent vs δN★ to see whether it converges toward 1
- Compare the δN★ value at which the transition occurs with the threshold
  δN★ for PBH formation — is the asymptotic regime physically accessible?

**For Question 2** (minimum-action locus):
- At each mass bin (fixed detrended log M), find the (δN★, ΔN) combination
  minimising S_MSR
- Plot the locus in (δN★, ΔN) space and check whether it tracks the
  collapse boundary
- Check whether the ratio δN★/ΔN along the locus is constant (as seen
  in the smaller grid) or varies

### Noise amplitude analysis (once prompt 12 columns are populated)

The `scalar_data.csv` now includes `noise_phi1_mean_full` — the mean value of
σ_φ1 = √(2D11)|P1| along the instanton trajectory, in units of the Hawking
standard deviation per e-fold. Use this to compute:

    dimensionless_ratio = delta_Nstar / (noise_phi1_mean_full × ΔN)

This measures how many "typical" Hawking noise steps are needed to accumulate
the excess δN★. When this ratio is O(1), the Gaussian approximation is
self-consistent. When it is >> 1, each step requires an anomalously large
fluctuation and the MSR path-integral may be underestimating the formation
suppression (the genuine Euclidean tunnelling amplitude at horizon exit may
be needed instead).

Plot this ratio vs δN★ and vs ΔN to characterise the regime of validity.

---

## 5. Deferred / open questions

- **ρ_final boundary condition**: switching `FullInstanton`'s terminal BC
  from φ_final to ρ_final failed due to a degrees-of-freedom counting issue.
- **S_instanton vs spectral eigenvalue sum** (Ezquiaga–García-Bellido–Vennin):
  Sturm-Liouville orthogonality obstacle stalled the derivation.
- **FullHankelDiffusion**: architecture is in place (registry, model_ids);
  implementation deferred. Extension points marked in `model_ids.py` and
  `registry.py`.
- **Active learning**: the GP posterior on the threshold boundary can guide
  targeted sampling (acquisition function = |GP_mean| / GP_std). Deferred
  pending the large-grid results.
- **Double-failure handling in pipeline**: when both `FullInstanton` and
  `SlowRollInstanton` fail for the same grid point, `_persist_pipeline_item`
  raises rather than persisting the failure rows.

---

## 6. Rules files

Codebase invariants are encoded in `.claude/rules/`:
- `ray-dispatch.md`
- `datastore-factories.md`
- `compute-targets.md`

Include or read these in any session that modifies those layers.

---

## 7. Quick-start for the new session

```bash
# Generate large exploratory grid
python3 config/generate_lhc_grid.py \
    --delta-nstar-low 0.1 --delta-nstar-high 8.0 \
    --delta-N-low 0.5 --delta-N-high 12.0 \
    --N-final-low 19.5 --N-final-high 20.5 \
    --n-points 1500 --method sobol --seed 42 \
    --output large_grid_1500.csv

# Run DOE pipeline
python3 main.py \
    --database large-grid-1500.sqlite \
    --config quadratic-asteroid.yaml \
    --sample-grid-csv large_grid_1500.csv \
    --no-store-values

# Plot and export scalar data
python3 plot_InstantonSolutions.py \
    --database large-grid-1500.sqlite \
    --config quadratic-asteroid.yaml \
    --output-dir out-large-grid \
    --no-store-values

# scalar_data.csv is at:
# out-large-grid/<traj_dir>/doe_summary/scalar_data.csv

# GP regression (once scalar_data.csv is ready)
python3 regression_InstantonOutputs.py \
    --scalar-data out-large-grid/<traj_dir>/doe_summary/scalar_data.csv \
    --output-dir regression_output_large/
```
