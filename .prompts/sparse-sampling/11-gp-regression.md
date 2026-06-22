# Prompt 11 — GP regression on DOE scalar outputs

## Context

`regression_InstantonOutputs.py` is a **standalone** analysis script in the
project root.  It has no dependency on Ray, ShardedPool, or any other
StochasticInstanton module.  Its only inputs are one or more `scalar_data.csv`
files produced by `plot_InstantonSolutions.py --no-store-values`, and its
outputs are serialised GP models plus diagnostic plots.

---

## CSV schema

The input CSV has comment lines prefixed with `#` followed by a header row and
data rows.  All numeric columns are floats; cells are empty (not `NaN`) when
the quantity is undefined (see below).

```
N_init, N_final, delta_Nstar, delta_N,
msr_action_full, msr_action_sr,
C_max_full, C_bar_max_full,
M_C_full_solar, M_C_bar_full_solar, r_max_C_full_Mpc, r_max_C_bar_full_Mpc,
C_max_sr, C_bar_max_sr,
M_C_sr_solar, M_C_bar_sr_solar, r_max_C_sr_Mpc, r_max_C_bar_sr_Mpc
```

`M_C_bar_full_solar`, `r_max_C_bar_full_Mpc`, and their `_sr` and `M_C_full`
counterparts are **structurally missing** (empty cell) whenever
`C_bar_max_full <= 0.4` (the PBH formation threshold).  These are not
measurement failures; the quantity is simply undefined below threshold.
Treat empty cells as `NaN`.

---

## Inputs (GP features)

The three columns used as GP input features are:

| Column        | Symbol   | Notes                                      |
|---------------|----------|--------------------------------------------|
| `delta_Nstar` | δN★      | Perturbation amplitude proxy               |
| `delta_N`     | ΔN       | Log spectral width, = `N_init − N_final`   |
| `N_final`     | N_final  | Physical scale calibration axis            |

**Standardise** all three features to zero mean and unit variance using the
training-set statistics before fitting any GP.  Store the scaler so predictions
on new points can be transformed consistently.

---

## Outputs to model

Fit **five independent single-output GPs**, one per target listed below.
Each GP is fit separately; there is no multi-output structure at this stage.

### GP 1 — `C_bar_max_full` (signed distance to threshold)

- **Training rows:** all rows where `C_bar_max_full` is not NaN (should be
  all rows).
- **Target transform:** fit `y = C_bar_max_full` directly (no log).  The
  quantity ranges from ~0.03 to ~1.6; a single GP with a smooth kernel handles
  this range without transformation.
- **Physical meaning:** `y − 0.4` is the signed distance to the PBH formation
  threshold.  The GP posterior mean and variance directly locate the threshold
  boundary and quantify uncertainty about it.

### GP 2 — `C_max_full`

- **Training rows:** all rows where `C_max_full` is not NaN.
- **Target transform:** fit `y = C_max_full` directly.
- **Physical meaning:** maximum of the (unaveraged) compaction function.

### GP 3 — `log(msr_action_full)`

- **Training rows:** all rows where `msr_action_full` is not NaN.
- **Target transform:** `y = log(msr_action_full)` (natural log).  The raw
  action spans ~3 orders of magnitude; the log is smooth and well-behaved.
- **Physical meaning:** MSR instanton action; determines the exponential
  suppression of the PBH formation rate.

### GP 4 — `log(M_C_bar_full_solar)`

- **Training rows:** rows where `M_C_bar_full_solar` is not NaN (i.e. where
  `C_bar_max_full > 0.4`).  This is ~45–47% of all rows.
- **Target transform:** `y = log(M_C_bar_full_solar)` (natural log).  The mass
  spans ~14 orders of magnitude; log is essential.
- **Physical meaning:** PBH mass in solar masses at the C̄ collapse scale.
- **Note in output:** record the number of training rows used and the fraction
  of the total.

### GP 5 — `log(r_max_C_bar_full_Mpc)`

- **Training rows:** same subset as GP 4 (same threshold condition).
- **Target transform:** `y = log(r_max_C_bar_full_Mpc)` (natural log).
- **Physical meaning:** PBH collapse radius in Mpc.

---

## Kernel

For all five GPs use:

```python
from sklearn.gaussian_process.kernels import Matern, WhiteKernel, ConstantKernel

kernel = ConstantKernel(1.0) * Matern(length_scale=[1.0, 1.0, 1.0], nu=2.5,
                                       length_scale_bounds=(1e-2, 1e2)) \
       + WhiteKernel(noise_level=1e-4, noise_level_bounds=(1e-10, 1e0))
```

- `Matern(nu=2.5)` is twice-differentiable — appropriate for the smooth
  but non-analytic response surfaces seen in these outputs.
- The three-element `length_scale` list enables **ARD** (automatic relevance
  determination): one length-scale per input dimension, so the GP can
  automatically discover that N_final has a long length-scale for C̄_max but
  a short one for S_MSR.
- `WhiteKernel` absorbs numerical noise and mild model misspecification.
- `ConstantKernel` sets the overall output scale.

Use `GaussianProcessRegressor(kernel=kernel, n_restarts_optimizer=5,
normalize_y=True)`.

---

## Train / test split

Use an **80/20 random split** (stratified on `C_bar_max_full > 0.4` to ensure
the above-threshold minority is represented in both sets).  Fix
`random_state=42` for reproducibility.

For GPs 4 and 5 (mass and radius), apply the 80/20 split **to the
above-threshold subset only**, not the full dataset.

---

## Diagnostics to compute and print

After fitting each GP, compute and print to stdout:

1. **Fitted kernel parameters** — the optimised hyperparameters, including
   each ARD length-scale labelled by its input column name.
2. **Test-set R²** — `sklearn.metrics.r2_score` on the test set, in the
   transformed space (log space for GPs 3–5).
3. **Test-set RMSE** — root mean squared error in the transformed space.
4. **Log marginal likelihood** — `gp.log_marginal_likelihood_value_`.

Print these in a formatted block per GP, e.g.:

```
GP 1 — C_bar_max_full
  kernel (optimised): 1.23**2 * Matern(...) + WhiteKernel(...)
  ARD length-scales:  delta_Nstar=0.412  delta_N=1.834  N_final=8.211
  test R²:            0.9821
  test RMSE:          0.0143
  log marginal lik:   -312.4
```

---

## Plots to produce

All plots written to `--output-dir` (default: `regression_output/`).
File format controlled by `--format` (default: `pdf`).

### Plot A — Predicted vs actual (one panel per GP)

A single figure with 5 subplots arranged in a 2×3 grid (last cell empty or
used for a legend/notes box).  Each subplot:
- x-axis: actual target value (transformed space)
- y-axis: GP posterior mean on the test set (transformed space)
- error bars: ±1 GP posterior standard deviation on each test point
- diagonal line: y = x (perfect prediction)
- Title: GP name, R² value

Filename: `predicted_vs_actual.<format>`

### Plot B — Threshold boundary in (δN★, ΔN) space

A single figure showing the `C̄_max = 0.4` boundary estimated by the GP
(GP 1), evaluated on a dense grid in (δN★, ΔN) at **three fixed N_final
values**: the minimum, midpoint, and maximum of the training N_final range.

For each N_final slice:
- Evaluate the GP posterior mean on a 100×100 grid covering
  `delta_Nstar ∈ [0, 3]`, `delta_N ∈ [0.5, 6]`.
- Draw the `mean = 0.4` contour line.
- Shade the region where `mean − std > 0.4` (confidently above threshold)
  and `mean + std < 0.4` (confidently below threshold) in distinct colours;
  leave the uncertainty band unshaded or lightly hatched.
- Overlay the training points as small scatter markers coloured by their
  actual `C̄_max` value.

Three N_final slices as three subplots in a 1×3 row.

Filename: `threshold_boundary.<format>`

### Plot C — ARD length-scale summary

A horizontal bar chart with one bar per (GP, input dimension) combination,
showing the optimised ARD length-scale.  Group bars by GP.  This visualises
which inputs matter for each output.

Filename: `ard_length_scales.<format>`

---

## Model serialisation

After fitting, serialise each GP model (including the fitted scaler) using
`joblib.dump` to `--output-dir/models/`.  Use filenames:

```
gp_C_bar_max_full.joblib
gp_C_max_full.joblib
gp_log_msr_action_full.joblib
gp_log_M_C_bar_full_solar.joblib
gp_log_r_max_C_bar_full_Mpc.joblib
```

Each `.joblib` file should contain a plain dict:

```python
{
    "gp":           <fitted GaussianProcessRegressor>,
    "scaler":       <fitted StandardScaler>,
    "feature_cols": ["delta_Nstar", "delta_N", "N_final"],
    "target_col":   "<column name or description>",
    "target_transform": "identity" | "log",
    "n_train":      <int>,
    "n_test":       <int>,
    "test_r2":      <float>,
    "test_rmse":    <float>,
}
```

This dict is the **complete interface** for downstream scripts that load and
query the fitted models.  A downstream script should be able to make
predictions by loading this dict, applying `scaler.transform()` to new input
rows, and calling `gp.predict()`.

---

## CLI interface

```
python3 regression_InstantonOutputs.py \
    --scalar-data  scalar_data-asteroid.csv \
    --output-dir   regression_output/ \
    --format       pdf \
    --seed         42
```

| Flag            | Type   | Default               | Description                              |
|-----------------|--------|-----------------------|------------------------------------------|
| `--scalar-data` | `Path` | required              | Path to input `scalar_data.csv`.         |
| `--output-dir`  | `Path` | `regression_output/`  | Directory for plots and serialised models. |
| `--format`      | str    | `pdf`                 | Plot file format: `pdf`, `png`, `svg`.   |
| `--seed`        | int    | `42`                  | Random seed for train/test split.        |

`--scalar-data` is the only required argument.  Exit with a clear error
message if the file does not exist or does not have the expected columns.

---

## Dependencies

Standard scientific Python stack only:

```
numpy, pandas, scikit-learn, scipy, matplotlib, joblib
```

No project-internal imports.

---

## Structure

Organise the script with clearly separated top-level functions:

```python
def load_scalar_data(path: Path) -> pd.DataFrame: ...
def fit_gp(name, X_train, y_train, kernel, seed) -> GaussianProcessRegressor: ...
def evaluate_gp(gp, scaler, X_test, y_test) -> dict: ...
def plot_predicted_vs_actual(results, output_dir, fmt): ...
def plot_threshold_boundary(gp1_bundle, df, output_dir, fmt): ...
def plot_ard_length_scales(all_bundles, output_dir, fmt): ...
def save_models(all_bundles, output_dir): ...
def main(): ...
```

`main()` orchestrates: load → split → fit each GP → evaluate → print
diagnostics → produce plots → serialise models.

---

## Out of scope

- Multi-output GPs or correlated GP models.
- Active learning or acquisition functions.
- The `_sr` (slow-roll) output columns — fit only the `_full` columns.
- The `M_C_full_solar` and `r_max_C_full_Mpc` columns (C_max collapse scale,
  not C̄_max collapse scale) — fit only the C̄-based mass and radius.
- Any dependency on StochasticInstanton project modules.
- Hyperparameter sensitivity analysis or Sobol indices — those come later,
  loading the serialised models from this script.
