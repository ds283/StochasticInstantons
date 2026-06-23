# Prompt 12 — Noise amplitude summary statistics on FullInstanton and SlowRollInstanton

## Motivation

The MSR instanton equations shift the fields beyond their drift values by noise
forcing terms.  In the Starobinsky–Langevin picture, the actual noise realisation
required by an instanton solution can be measured in units of the Hawking
standard deviation per e-fold — i.e. how many sigma the noise must be at each
point along the trajectory.

For a general diffusion matrix (D11, D12, D22), the noise forcing on φ1 per
e-fold is `(2 D11 P1 + 2 D12 P2) dN`, while the Langevin variance of a φ1 step
is `2 D11 dN`.  Dividing gives the pointwise noise amplitude in units of the φ1
standard deviation:

    σ_φ1(N) = [ 2 D11(N) |P1(N)| + 2 D12(N) |P2(N)| ] / √(2 D11(N))
             = √(2 D11) |P1| + [2 D12 / √(2 D11)] |P2|

Similarly for φ2 (Langevin variance `2 D22 dN`):

    σ_φ2(N) = [ 2 D12(N) |P1(N)| + 2 D22(N) |P2(N)| ] / √(2 D22(N))
             = [2 D12 / √(2 D22)] |P1| + √(2 D22) |P2|

Both quantities are dimensionless.  They reduce to `√(2 D11) |P1| = (H/2π)|P1|`
and zero respectively in the `MasslessDecoupledDiffusion` limit (D12=D22=0),
but the full expressions must be used so that the code is correct for any
future diffusion model (e.g. `FullHankelDiffusion`).

**Guard for vanishing diagonal elements.**  If `D11 = 0` at any grid point,
`σ_φ1` is undefined (division by zero).  If `D22 = 0` at any grid point,
`σ_φ2` is undefined.  In the `MasslessDecoupledDiffusion` model `D22 = 0`
everywhere, so `σ_φ2` is always undefined for that model.  The rule is:

- If `D11 = 0` anywhere on `N_grid`: set `noise_phi1_min/mean/max` all to `None`.
- If `D22 = 0` anywhere on `N_grid`: set `noise_phi2_min/mean/max` all to `None`.

A value of `None` means "this noise channel does not exist in this diffusion
model", which is distinct from zero.

---

## Changes to `_compute_full_instanton`
### File: `ComputeTargets/FullInstanton.py`

`D11_arr` is already computed over `N_grid` for the MSR action integral.
Extend this block to also compute `D12_arr` and `D22_arr`, then derive the
noise amplitude arrays.

Replace:

    D11_arr    = np.array([_Dij(phi1_f[i], phi2_f[i])[0]
                           for i in range(len(N_grid))])
    msr_action = float(np.trapezoid(D11_arr * P1_f ** 2, N_grid))

with:

    D11_arr = np.array([_Dij(phi1_f[i], phi2_f[i])[0] for i in range(len(N_grid))])
    D12_arr = np.array([_Dij(phi1_f[i], phi2_f[i])[1] for i in range(len(N_grid))])
    D22_arr = np.array([_Dij(phi1_f[i], phi2_f[i])[2] for i in range(len(N_grid))])
    msr_action = float(np.trapezoid(D11_arr * P1_f ** 2, N_grid))

    # Noise amplitude in units of Hawking standard deviations per e-fold.
    # σ_φ1 = √(2 D11) |P1| + [2 D12 / √(2 D11)] |P2|
    # σ_φ2 = [2 D12 / √(2 D22)] |P1| + √(2 D22) |P2|
    # None if the corresponding diagonal element is zero anywhere.
    abs_P1 = np.abs(P1_f)
    abs_P2 = np.abs(P2_f)

    if np.any(D11_arr == 0.0):
        noise_phi1_min = noise_phi1_mean = noise_phi1_max = None
    else:
        sqrt_2D11 = np.sqrt(2.0 * D11_arr)
        sigma_phi1 = sqrt_2D11 * abs_P1 + (2.0 * D12_arr / sqrt_2D11) * abs_P2
        noise_phi1_min  = float(sigma_phi1.min())
        noise_phi1_mean = float(sigma_phi1.mean())
        noise_phi1_max  = float(sigma_phi1.max())

    if np.any(D22_arr == 0.0):
        noise_phi2_min = noise_phi2_mean = noise_phi2_max = None
    else:
        sqrt_2D22 = np.sqrt(2.0 * D22_arr)
        sigma_phi2 = (2.0 * D12_arr / sqrt_2D22) * abs_P1 + sqrt_2D22 * abs_P2
        noise_phi2_min  = float(sigma_phi2.min())
        noise_phi2_mean = float(sigma_phi2.mean())
        noise_phi2_max  = float(sigma_phi2.max())

Add all six keys to the returned dict alongside `msr_action`:

    "noise_phi1_min":  noise_phi1_min,
    "noise_phi1_mean": noise_phi1_mean,
    "noise_phi1_max":  noise_phi1_max,
    "noise_phi2_min":  noise_phi2_min,
    "noise_phi2_mean": noise_phi2_mean,
    "noise_phi2_max":  noise_phi2_max,

Add the same six keys with value `None` to **both** failure-return dicts (the
early background-ODE failure and the outer-loop non-convergence failure).

**Note on efficiency.** `_Dij` is called three times per grid point in the
replacement above.  This is fine for correctness and clarity.  If profiling
later shows this to be a bottleneck, the three components can be collected in
a single pass — but do not optimise prematurely.

---

## Changes to `_compute_slow_roll_instanton`
### File: `ComputeTargets/SlowRollInstanton.py`

The slow-roll instanton has only `P1` (no `P2`).  The φ2 noise channel
therefore does not exist, and `noise_phi2_*` should always be `None`.

After the MSR action integral (wherever `D11_arr` and `P1_arr` are computed),
add:

    D12_arr = np.array([dm.D_matrix(phi_arr[i], 0.0, potential)[1]
                        for i in range(len(N_grid))])

    abs_P1 = np.abs(P1_arr)   # use whatever variable name holds P1 on N_grid

    if np.any(D11_arr == 0.0):
        noise_phi1_min = noise_phi1_mean = noise_phi1_max = None
    else:
        sqrt_2D11 = np.sqrt(2.0 * D11_arr)
        # In slow-roll P2=0, so the D12 term vanishes identically.
        sigma_phi1 = sqrt_2D11 * abs_P1
        noise_phi1_min  = float(sigma_phi1.min())
        noise_phi1_mean = float(sigma_phi1.mean())
        noise_phi1_max  = float(sigma_phi1.max())

    # φ2 channel does not exist in the slow-roll approximation (no P2).
    noise_phi2_min = noise_phi2_mean = noise_phi2_max = None

Add the same six keys to the returned dict and to both failure-return dicts.

---

## Changes to `FullInstanton` class
### File: `ComputeTargets/FullInstanton.py`

In `__init__`, initialise alongside `_msr_action`:

    self._noise_phi1_min:  Optional[float] = None
    self._noise_phi1_mean: Optional[float] = None
    self._noise_phi1_max:  Optional[float] = None
    self._noise_phi2_min:  Optional[float] = None
    self._noise_phi2_mean: Optional[float] = None
    self._noise_phi2_max:  Optional[float] = None

In `store()`, after `self._msr_action = data["msr_action"]`, add:

    self._noise_phi1_min  = data.get("noise_phi1_min")
    self._noise_phi1_mean = data.get("noise_phi1_mean")
    self._noise_phi1_max  = data.get("noise_phi1_max")
    self._noise_phi2_min  = data.get("noise_phi2_min")
    self._noise_phi2_mean = data.get("noise_phi2_mean")
    self._noise_phi2_max  = data.get("noise_phi2_max")

Add six read-only properties:

    @property
    def noise_phi1_min(self) -> Optional[float]:
        return self._noise_phi1_min

    @property
    def noise_phi1_mean(self) -> Optional[float]:
        return self._noise_phi1_mean

    @property
    def noise_phi1_max(self) -> Optional[float]:
        return self._noise_phi1_max

    @property
    def noise_phi2_min(self) -> Optional[float]:
        return self._noise_phi2_min

    @property
    def noise_phi2_mean(self) -> Optional[float]:
        return self._noise_phi2_mean

    @property
    def noise_phi2_max(self) -> Optional[float]:
        return self._noise_phi2_max

Apply the same `__init__`, `store()`, and property changes to `SlowRollInstanton`
in `ComputeTargets/SlowRollInstanton.py`.

---

## Changes to `sqla_FullInstantonFactory`
### File: `Datastore/SQL/ObjectFactories/FullInstanton.py`

**`register()`** — add six nullable Float(64) columns after `msr_action`:

    sqla.Column("noise_phi1_min",  sqla.Float(64), nullable=True),
    sqla.Column("noise_phi1_mean", sqla.Float(64), nullable=True),
    sqla.Column("noise_phi1_max",  sqla.Float(64), nullable=True),
    sqla.Column("noise_phi2_min",  sqla.Float(64), nullable=True),
    sqla.Column("noise_phi2_mean", sqla.Float(64), nullable=True),
    sqla.Column("noise_phi2_max",  sqla.Float(64), nullable=True),

**`build()`** — add the six columns to the SELECT query alongside `msr_action`,
then after the existing `if row_data.msr_action is not None: obj._msr_action = ...`
block add:

    obj._noise_phi1_min  = row_data.noise_phi1_min
    obj._noise_phi1_mean = row_data.noise_phi1_mean
    obj._noise_phi1_max  = row_data.noise_phi1_max
    obj._noise_phi2_min  = row_data.noise_phi2_min
    obj._noise_phi2_mean = row_data.noise_phi2_mean
    obj._noise_phi2_max  = row_data.noise_phi2_max

**`store()`** — add to the inserter dict for both the success path and the
failure path (use `None` for the failure path):

    "noise_phi1_min":  obj.noise_phi1_min,
    "noise_phi1_mean": obj.noise_phi1_mean,
    "noise_phi1_max":  obj.noise_phi1_max,
    "noise_phi2_min":  obj.noise_phi2_min,
    "noise_phi2_mean": obj.noise_phi2_mean,
    "noise_phi2_max":  obj.noise_phi2_max,

Apply the identical factory changes to `sqla_SlowRollInstantonFactory` in
`Datastore/SQL/ObjectFactories/SlowRollInstanton.py`.

---

## Changes to `_populate_from_result`
### Files: `ComputeTargets/FullInstanton.py`, `ComputeTargets/SlowRollInstanton.py`

In both `_populate_from_result` methods (added in prompt 06), after reading
`msr_action` from `data`, also read:

    self._noise_phi1_min  = data.get("noise_phi1_min")
    self._noise_phi1_mean = data.get("noise_phi1_mean")
    self._noise_phi1_max  = data.get("noise_phi1_max")
    self._noise_phi2_min  = data.get("noise_phi2_min")
    self._noise_phi2_mean = data.get("noise_phi2_mean")
    self._noise_phi2_max  = data.get("noise_phi2_max")

---

## Changes to `scalar_data.csv` output
### File: `plot_InstantonSolutions.py`

In `_collect_doe_scalar_data`, add twelve new keys immediately after the
`msr_action_*` entries — six per instanton type:

    "noise_phi1_min_full":  full_instanton.noise_phi1_min,
    "noise_phi1_mean_full": full_instanton.noise_phi1_mean,
    "noise_phi1_max_full":  full_instanton.noise_phi1_max,
    "noise_phi2_min_full":  full_instanton.noise_phi2_min,
    "noise_phi2_mean_full": full_instanton.noise_phi2_mean,
    "noise_phi2_max_full":  full_instanton.noise_phi2_max,
    "noise_phi1_min_sr":    sr_instanton.noise_phi1_min,
    "noise_phi1_mean_sr":   sr_instanton.noise_phi1_mean,
    "noise_phi1_max_sr":    sr_instanton.noise_phi1_max,
    "noise_phi2_min_sr":    sr_instanton.noise_phi2_min,
    "noise_phi2_mean_sr":   sr_instanton.noise_phi2_mean,
    "noise_phi2_max_sr":    sr_instanton.noise_phi2_max,

`None` values produce empty cells in the CSV, consistent with the existing
convention for undefined scalars such as `M_C_bar_full_solar`.

---

## Changes to `_check_scalar_integrity`
### File: `ComputeTargets/pipeline.py`

Add `noise_phi1_mean` to the set of scalar attributes checked for both
`FullInstanton` and `SlowRollInstanton`.  Use `is not None` as the check
predicate — a non-failure row with `noise_phi1_mean is None` should trigger
recomputation.

Do **not** add `noise_phi2_mean` to the integrity check, because it is
legitimately `None` for any run using `MasslessDecoupledDiffusion`.  Checking
it would incorrectly flag every existing row as incomplete.

---

## Out of scope

- Computing noise amplitudes normalised by φ̇, slow-roll parameters, or any
  other trajectory quantity.  Store raw dimensionless σ values only.
- Any change to `FullInstantonValue` or `SlowRollInstantonValue` row storage.
- The `CompactionFunction` compute target.
- `generate_lhc_grid.py` or `regression_InstantonOutputs.py`.
- Implementing `FullHankelDiffusion` (noted as a TODO in `DiffusionModel.py`).

---

## Acceptance criteria

1. A fresh run of `main.py` on a 5×5×5 test grid using `MasslessDecoupledDiffusion`
   produces database rows where every non-failed `FullInstanton` and
   `SlowRollInstanton` has `noise_phi1_min/mean/max` populated with finite
   positive values, and `noise_phi2_min/mean/max` are all `NULL`.
2. Running `plot_InstantonSolutions.py --no-store-values` on the same database
   produces a `scalar_data.csv` containing all twelve new columns, with
   `noise_phi2_*` columns entirely empty and `noise_phi1_*` columns populated
   for non-failed rows.
3. Failed instanton rows have `NULL` for all twelve new columns.
4. `--no-store-values` pipeline runs correctly persist the six scalar columns
   on the parent row without writing value rows.
5. `_check_scalar_integrity` flags a pre-existing non-failure row with
   `noise_phi1_mean is None` as requiring recomputation, and does not flag
   rows where `noise_phi2_mean is None`.
