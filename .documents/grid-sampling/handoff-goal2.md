# StochasticInstanton — Handoff Document
_Last updated: 2026-06-23. Generated at the close of the Goal 1 scaling
analysis session._

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
3. Extracts scalar summaries: `C_max`, `C̄_max`, collapse scales `r_max` and
   `r_peak`, PBH mass estimates `M_max` and `M_peak`, and `S_MSR` — which
   together determine whether PBH formation occurs and at what mass.

**Key threshold**: `C_max > 0.4` (configurable) → PBH forms.

**Parameter meanings**:
- `N_init`: e-folds before end of inflation at the instanton start point.
- `N_final`: e-folds before end of inflation at the instanton endpoint.
- `delta_Nstar`: excess e-folds accumulated by the instanton relative to
  the noiseless background, ≈ peak ζ (controls amplitude → threshold
  crossing).
- `ΔN = N_init − N_final`: controls the log width of the enhanced
  perturbation spectrum.
- `N_final` sets the absolute physical scale (mass, Mpc).

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
| `14-compaction-rmax-rpeak-refactor.md` | `r_max` and `r_peak` computed from `C(r)` only; `C̄`-based radius estimates removed from schema; `C_bar_threshold` parameter removed. |

### Architecture notes relevant to the new session

**`--no-store-values` mode**: activates unified pipeline, scalars only. This
is the mode used for all DOE runs.

**`generate_lhc_grid.py`** (`config/`): generates `--sample-grid-csv`-compatible
CSVs using Sobol or LHC sampling in `(delta_Nstar, ΔN, N_final)` space.
Cartesian product mode uses `--delta-nstar-values`, `--delta-N-values`,
`--N-final-values`.

**`regression_InstantonOutputs.py`**: standalone GP regression script. Fits
five single-output GPs on `scalar_data.csv`. The GP targets `log(M_PBH)` and
`log(r_PBH)` should be pointed at whichever of `M_max` / `M_peak` columns is
preferred after reviewing Phase A results (see Goal 2 below).

**`CompactionFunction` scalar columns** (post prompt 14):

| Column | Meaning |
|--------|---------|
| `r_max` | Outermost r where C ≥ C_th |
| `M_max` | Mass from r_max (None if r_max_at_grid_edge) |
| `r_peak` | r at argmax C(r) |
| `M_peak` | Mass from r_peak (None if r_peak_at_grid_edge) |
| `C_max` | max C(r) — primary collapse criterion |
| `C_bar_max` | max C̄(r) — diagnostic only, not used for mass |

**`C̄(r)` interpretation**: C̄(r) is the areal-volume average of C(r)
(Raatikainen et al. eq. 4), with denominator `r³ exp(3ζ(r))`. In the
strongly nonlinear regime (large δN★, large ΔN), C̄_max becomes very large
because the exponential metric weighting amplifies the inner high-ζ region
relative to the outer boundary. This is a geometrically correct computation
but the calibrated threshold C̄_th = 0.4 does not apply in this regime.
Use `C_max > 0.4` as the collapse criterion throughout. The type II
transition (C_max → 2/3, corresponding to a neck in the areal radius
R = r exp(ζ)) was not reached in the Goal 1 grid (C_max peaked at ~0.65).

**DiffusionModel** (prompt 13): `AbstractDiffusionModel` inherits from
`DatastoreObject` and `ABC`. `FullInstanton` and `SlowRollInstanton` carry
`diffusion_serial` and `diffusion_type` columns. `InflatonTrajectory` carries
no diffusion model. Polymorphic dispatch via `DIFFUSION_MODEL_REGISTRY`.

---

## 3. Goal 1 results: asymptotic scaling of S_MSR

### Grid

Cartesian product: δN★ ∈ [0.5, 20] (45 values), ΔN ∈ {2, 3, 4, 6},
N_final = 20. 180 points total. Database: `SMSR_scaling.sqlite` (scalars
only) and `SMSR_scaling_values.sqlite` (full per-sample profiles).

### Key findings

**ζ(r) profiles** are clean power laws on log-r at all δN★ values — smooth,
monotone, no oscillations. This is expected: the instanton produces the single
most-probable fluctuation, which is smooth by construction. The spiky profiles
in Raatikainen et al. arise from stochastic realisations, not from the
instanton.

**Scaling exponent** d(log S_MSR)/d(log δN★) at fixed ΔN and N_final:

| δN★ | ΔN = 2 | ΔN = 3 | ΔN = 4 | ΔN = 6 |
|-----|--------|--------|--------|--------|
| 2   | 1.52   | 1.61   | 1.67   | 1.76   |
| 5   | 1.31   | 1.37   | 1.44   | 1.56   |
| 10  | 1.21   | 1.27   | 1.33   | 1.41   |
| 15  | 1.22   | 1.27   | 1.30   | 1.37   |
| 18  | 1.22   | —      | —      | 1.41   |

The exponent falls steeply from δN★ ~ 1–5, then flattens and approaches an
asymptote around **1.21 for ΔN = 2** and **1.37 for ΔN = 6**. The descent
has essentially stopped by δN★ ~ 10–12. The asymptote is ΔN-dependent:
narrower spectra approach a lower asymptote faster, consistent with δN★/ΔN
being the relevant scaling variable.

**The Vennin prediction of exponent 1 is not reached** within the sampled
range. Either the asymptote for the quadratic potential genuinely sits above 1,
or the crossover requires δN★ >> ΔN, which at ΔN = 6 means δN★ >> 6 — and
at δN★ = 20 the rate of descent has slowed dramatically, suggesting the
asymptote is genuinely above 1 in the physically accessible regime.

**Per-slice global fits** (log S = α log δN★ + const, N_final = 20):
- ΔN = 2: α = 1.365 ± 0.013
- ΔN = 3: α = 1.445 ± 0.014
- ΔN = 4: α = 1.507 ± 0.015
- ΔN = 6: α = 1.591 ± 0.014

These are averages over the full δN★ range and should not be interpreted as
asymptotic exponents.

**Full instanton Picard failures** appear at large δN★ (roughly δN★ > 14–16
depending on ΔN). The SR instanton tracks the full instanton closely
throughout the converged range and can substitute for the scaling analysis,
with a note that full/SR agreement was verified up to the failure point.

**r_max vs r_peak**: at moderate δN★ (above threshold, below the strongly
nonlinear regime), r_max ≈ r_peak — C(r) has a clean peak and its outer
threshold crossing coincides with the peak location. At large δN★, C(r)
develops a broad plateau and the two estimates diverge. The physical
interpretation of this divergence requires NR input (contact Sam Young).

---

## 4. Goal 2: minimum-action formation pathway

### Scientific questions

**Question 1 (feasibility)**: For given `M_PBH` and `N_final`, does the
locus of (δN★, ΔN) pairs that produce a PBH of that mass have an endpoint at
large ΔN? That is, is there some ΔN_max(M_PBH, N_final) beyond which no
value of δN★, however large, can produce a PBH of that mass?

Physical intuition: at very large ΔN the perturbation is spread over so many
decades in k that its amplitude per decade (δN★/ΔN) becomes small, and the
compaction function — which is sensitive to the local gradient ζ'(r) — may
be unable to reach threshold regardless of δN★. Whether this actually happens
depends on how ζ'(r) scales with (δN★, ΔN) in the instanton solution.

Note: if no endpoint exists, then along the iso-mass contour δN★ must grow
without bound as ΔN → ∞.

**Question 2 (minimum action)**: At fixed `M_PBH` and `N_final`, what is the
(δN★, ΔN) combination that minimises S_MSR along the iso-mass contour? This
gives the dominant (most probable) PBH formation pathway at that mass.

Question 1 must be answered first — the feasibility boundary determines the
domain over which Question 2 is optimised.

**Derived observable**: along the minimum-action locus, what is the ratio
δN★/ΔN as a function of (M_PBH, N_final)? Prior small-grid evidence
(ΔN ≤ 6) suggested a roughly constant ratio ~0.55–0.62, but this needs
extension to large ΔN.

### Strategy: two-phase grid

**Phase A** (exploratory, 800 Sobol points):

```bash
python3 config/generate_lhc_grid.py \
    --delta-nstar-low  1.5  --delta-nstar-high 10.0 \
    --delta-N-low      0.5  --delta-N-high     14.0 \
    --N-final-low     19.5  --N-final-high     20.5 \
    --n-points        800 \
    --method sobol \
    --seed 42 \
    --output phase_a_grid.csv

python3 main.py \
    --database phase_a.sqlite \
    --config quadratic-asteroid.yaml \
    --sample-grid-csv phase_a_grid.csv \
    --no-store-values

python3 plot_InstantonSolutions.py \
    --database phase_a.sqlite \
    --config quadratic-asteroid.yaml \
    --output-dir out-phase-a \
    --no-store-values
```

The narrow N_final band [19.5, 20.5] keeps the Sobol sequence 3D while
effectively fixing N_final = 20.

Phase A locates the collapse boundary C_max = 0.4 in (δN★, ΔN) space at
large ΔN, and determines whether the boundary terminates or continues.

**Phase B** (targeted, ~900 points): designed after Phase A analysis.
Concentrate points near the collapse boundary and along iso-mass contours,
informed by Phase A results.

### Analysis to perform on Phase A scalar_data.csv

1. **Collapse boundary**: identify the threshold curve δN★_th(ΔN) by
   finding, at each ΔN value, the δN★ where C_max crosses 0.4. Fit a
   smooth curve. Does it terminate at finite ΔN or continue indefinitely?

2. **Iso-mass contours**: from `M_max` or `M_peak` (decide which after
   reviewing Phase A profiles), identify contours of fixed M_PBH in the
   (δN★, ΔN) plane. Do these contours intersect the collapse boundary?
   Where?

3. **Minimum-action locus**: at each M_PBH, find the (δN★, ΔN) point on
   the iso-mass contour that minimises S_MSR. Plot the locus.

4. **δN★/ΔN ratio**: evaluate along the minimum-action locus as a function
   of M_PBH.

### Notes on mass assignment

After the prompt 14 refactor, two mass estimates are available:
- `M_max`: from the outermost radius where C ≥ 0.4. None when
  r_max_at_grid_edge (peak not resolved within grid).
- `M_peak`: from the radius of the C(r) peak. None when
  r_peak_at_grid_edge.

At moderate δN★ (near threshold), M_max ≈ M_peak. At large δN★ they
diverge. The physically correct choice requires NR input (contact Sam Young).
For Phase A analysis, use whichever is more consistently non-None across the
grid, and flag the comparison as an open question.

---

## 5. Deferred / open questions

- **Which mass estimate is physically correct at large δN★**: M_max (outer
  extent of super-critical region) vs M_peak (peak of C(r))? Requires NR.
  Contact Sam Young.
- **ρ_final boundary condition**: switching `FullInstanton`'s terminal BC
  from φ_final to ρ_final failed due to a degrees-of-freedom counting issue.
- **S_instanton vs spectral eigenvalue sum** (Ezquiaga–García-Bellido–Vennin):
  Sturm-Liouville orthogonality obstacle stalled the derivation.
- **FullHankelDiffusion**: architecture in place; implementation deferred.
- **Active learning**: GP posterior on threshold boundary can guide targeted
  sampling. Deferred pending Phase A results.
- **Double-failure handling in pipeline**: when both `FullInstanton` and
  `SlowRollInstanton` fail, `_persist_pipeline_item` raises rather than
  persisting failure rows.
- **Vennin asymptotic exponent**: whether S_MSR ~ δN★ (exponent 1) is
  reached at δN★ >> ΔN remains open. Goal 1 results suggest the asymptote
  for the quadratic potential lies above 1 in the physically accessible
  regime.

---

## 6. Rules files

Codebase invariants are encoded in `.claude/rules/`:
- `ray-dispatch.md`
- `datastore-factories.md`
- `compute-targets.md`

Include or read these in any session that modifies those layers.

---

## 7. Quick-start for Phase A

```bash
# Generate Phase A grid
python3 config/generate_lhc_grid.py \
    --delta-nstar-low 1.5 --delta-nstar-high 10.0 \
    --delta-N-low 0.5 --delta-N-high 14.0 \
    --N-final-low 19.5 --N-final-high 20.5 \
    --n-points 800 --method sobol --seed 42 \
    --output phase_a_grid.csv

# Run DOE pipeline
python3 main.py \
    --database phase_a.sqlite \
    --config quadratic-asteroid.yaml \
    --sample-grid-csv phase_a_grid.csv \
    --no-store-values

# Plot and export scalar data
python3 plot_InstantonSolutions.py \
    --database phase_a.sqlite \
    --config quadratic-asteroid.yaml \
    --output-dir out-phase-a \
    --no-store-values

# scalar_data.csv is at:
# out-phase-a/<traj_dir>/doe_summary/scalar_data.csv

# Key columns to examine:
#   C_max_full / C_max_sr       — collapse criterion (threshold 0.4)
#   M_max_full_solar            — mass from outer threshold crossing
#   M_peak_full_solar           — mass from C(r) peak
#   msr_action_full / _sr       — instanton action
#   delta_Nstar, delta_N        — parameter coordinates
```
