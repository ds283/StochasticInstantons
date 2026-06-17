# Combined prompt: revert `FullInstanton` final boundary condition and implement `CompactionFunction`

This prompt assumes the following state of the repository:

- `./.prompts/02-fullinstanton-bcs.md` has been applied
- `./.prompts/02a-implement-jacobian.md` has been applied
- The iteration is not converging with the `ρ`-final boundary condition

It makes three groups of changes:

1. **Revert** the final boundary condition of `FullInstanton` from `ρ_final`
   back to `φ_final`, while retaining all other changes from the previous prompts
2. **Implement** a new `CompactionFunction` compute target
3. **Register** the new target in the datastore and configuration

All file paths use the **source-tree** layout.

---

## Part 1: Revert `FullInstanton` final boundary condition

### 1.1 `ComputeTargets/FullInstanton.py`

Revert **only** the changes related to `ρ_final` targeting. All other changes
from `prompt_full_instanton_refactor.md` are retained.

**In `_compute_full_instanton` function signature**, restore `phi_final: float`
and remove `rho_final: float`:

```python
@ray.remote
def _compute_full_instanton(
        trajectory,
        phi_init: float,
        pi_init: float,  # retained from refactor (was pi_SR_init)
        phi_final: float,  # restored
        N_total: float,
        N_sample: list,
        atol: float,
        rtol: float,
        label: Optional[str] = None,
) -> dict:
```

**Restore the outer Newton residual** to field-space:

```python
residual = p1[-1] - phi_final
final_residual = abs(residual)
```

**Restore the original `dres_dlam` computation** (single component):

```python
dlam = max(abs(lam) * 1e-4, 1e-6)
p1_p, p2_p, _, _, n_inner_p = picard_inner(lam + dlam, phi1_f, phi2_f)
picard_iterations_per_outer.append(n_inner_p)
if p1_p is not None:
    dres_dlam = (p1_p[-1] - p1[-1]) / dlam
    if abs(dres_dlam) > 1e-14:
        lam -= residual / dres_dlam
        continue
```

Note: `p2_p` is still unpacked (not discarded with `_`) so it is available
for diagnostics.

**Restore `OUTER_TOL`** as a field-space tolerance:

```python
OUTER_TOL = max(atol * 100.0, 1e-6)
```

**Retain the `compute_rho` helper** and the enhanced diagnostic print showing
`φ₁(T)`, `φ₂(T)`, and `ρ(T)` — these are informative and cost nothing:

```python
def compute_rho(phi1_val, phi2_val):
    Mp = potential._units.PlanckMass
    return 3.0 * (Mp ** 2) * potential.H_sq(phi1_val, phi2_val)


if label:
    print(
        f"[{label}] outer {outer}: λ={lam:.4g}, "
        f"φ₁(T)={p1[-1]:.6g}, φ₂(T)={p2[-1]:.6g}, "
        f"ρ(T)={compute_rho(p1[-1], p2[-1]):.6g}, "
        f"res={residual:.2e}"
    )
```

**Restore the fallback nudge** to the original form:

```python
newton_fallback_count += 1
lam += (phi_final - p1[-1]) * 0.1
```

**In `FullInstanton.compute()`**, restore `phi_final` and remove `rho_final`:

```python
phi_final = traj.phi_at(N_end - float(self._N_final))

self._compute_ref = _compute_full_instanton.remote(
    trajectory=self._trajectory,
    phi_init=phi_init,
    pi_init=pi_init,  # retained rename
    phi_final=phi_final,  # restored
    N_total=N_total,
    N_sample=...,
    atol=atol,
    rtol=rtol,
    label=label,
)
```

### 1.2 What is retained from previous prompts

The following changes from the previous prompts are **not** reverted:

- `InflationConcepts/noiseless_equations.py` — keep entirely
- `InflatonTrajectory.rho_at()` — keep
- `pi_init` rename from `pi_SR_init` throughout `FullInstanton` — keep
- `AbstractPotential.drho_dphi()` and `AbstractPotential.drho_dpi()` — keep
- Enhanced diagnostic print in the outer loop — keep

---

## Part 2: New file `ComputeTargets/CompactionFunction.py`

### 2.1 Overview

`CompactionFunction` accepts a converged `FullInstanton` and/or
`SlowRollInstanton`, builds a `ζ(r)` profile using the δN formula, computes
the compaction functions `C(r)` and `C̄(r)`, determines collapse criteria,
and records PBH mass estimates. It follows the same four-part pattern as other
compute targets: `@ray.remote` function → `CompactionFunctionValue` →
`CompactionFunction` → `CompactionFunctionProxy`.

### 2.2 Cosmological parameters class

At module level, define:

```python
class Planck2018:
    """
    Planck 2018 TT+TE+EE+lowP+lensing+BAO 68% central values.
    Table 2 of arXiv:1807.06209v4.
    """
    omega_cc = 0.6889
    omega_m = 1.0 - omega_cc
    h = 0.6766
    f_baryon = 0.15817
    T_CMB_Kelvin = 2.7255
    Neff = 3.046
    g_star_reh = 106.75  # SM dof at high reheat temperature
    g_star_s_0 = 3.91  # effective entropy dof today
```

### 2.3 Scale matching function

Define a module-level function:

```python
def ln_k_phys_Mpc(
        N_before_end: float,
        V_k: float,
        epsilon_k: float,
        V_end_downflow: float,
        potential: AbstractPotential,
        cosmo: type = Planck2018,
) -> float:
```

This implements the matching equation:

```
ln(k_phys / Mpc^-1) = -N(k)
                     + ln(Mpc * Mp)
                     + ln(T_CMB / Mp)
                     + (1/4) * ln(pi^2 / 135)
                     + (1/4) * ln[ V_k / (V_end_downflow * (1 - epsilon_k/3)) ]
                     + (1/3) * ln(g_star_s_0 / g_star_reh)
```

where:

- `N_before_end` is `N(k)`: e-folds before end of inflation at which scale `k`
  exits the horizon (positive number)
- `V_k` is the potential at horizon crossing in units of `Mp^4`
- `epsilon_k` is `epsilon` at horizon crossing
- `V_end_downflow` is `V(phi)` at `epsilon=1` along the downflow trajectory
  from the instanton endpoint, in units of `Mp^4`
- `Mp = potential._units.PlanckMass`
- `T_CMB` in units of `Mp`: use `k_B = 8.617333e-5 eV/K`,
  `Mp_in_eV = 2.435e27 eV` (reduced Planck mass),
  so `T_CMB_in_Mp = cosmo.T_CMB_Kelvin * k_B_eV / Mp_in_eV`
- `Mpc_times_Mp`: `1 Mpc = 3.085678e22 m`, `Mp^-1 = hbar*c / Mp_energy` in
  metres; compute `Mpc_times_Mp = Mpc_in_metres / (hbar_c_in_MeV_m / Mp_in_MeV)`
  using `hbar*c = 197.3269804e-15 MeV*m` and `Mp_in_MeV = 2.435e27 eV * 1e-6`

Define all conversion constants as named local variables at the top of the
function with inline comments giving their physical meaning and units. Do not
use magic numbers inline in the formula.

The `(1/3) * ln(g_star_s_0 / g_star_reh)` term accounts for the change in
relativistic degrees of freedom between reheating and today.

### 2.4 `@ray.remote` compute function

```python
@ray.remote
def _compute_compaction_function(
        full_instanton_proxy,  # FullInstantonProxy or None
        slow_roll_instanton_proxy,  # SlowRollInstantonProxy or None
        trajectory_proxy,  # InflatonTrajectoryProxy
        C_threshold: float,
        C_bar_threshold: float,
        atol: float,
        rtol: float,
        label: Optional[str] = None,
) -> dict:
```

The function attempts to compute a compaction function profile from each
available instanton independently. It returns a dict with two top-level keys
`"full"` and `"slow_roll"`, each containing either a result sub-dict or
`None` if the corresponding proxy was `None` or the upstream instanton failed.

#### 2.4.1 Per-instanton computation

For each available instanton, perform the following steps. The instanton
provides sample points `{N_inst, phi1, phi2}`. For `SlowRollInstanton`, which
stores only `{phi, P1}`, reconstruct `phi1 = phi` and the attractor momentum
`phi2 = pi_SR(phi) = -potential.dV_dphi(phi) / (3.0 * potential.H_sq(phi, 0.0))`
at each sample point.

**Step A: downflow trajectory from instanton endpoint.**

Call `integrate_noiseless_trajectory` from `InflationConcepts.noiseless_equations`
with initial conditions `(phi1[-1], phi2[-1])` from the last instanton sample
point. This integrates forward until `epsilon = 1`, yielding:

- `sol_downflow`: the ODE solution with `dense_output=True`
- `N_end_downflow`: e-folds from instanton endpoint to end of inflation,
  from `sol_downflow.t_events[0][0]`
- `phi_end_downflow`: `phi` at `epsilon = 1`, from `sol_downflow.y_events[0][0][0]`
- `V_end_downflow = potential.V(phi_end_downflow)`

If the downflow integration fails (sol is None or `t_events[0]` is empty),
record `failure = True` for this path and skip remaining steps.

**Step B: delta-N computation for each instanton sample point.**

Retrieve the full `InflatonTrajectory` via `trajectory_proxy.get()`. Let
`N_end_traj = traj.N_end` and `N_init_val` be the `N_init` parameter of the
instanton (e-folds before end of inflation at the instanton start).

For each sample point `i` at instanton time `N_inst_i`:

1. Compute `rho_i = 3.0 * Mp^2 * potential.H_sq(phi1_i, phi2_i)`
2. Find `N_bg_i` on the noiseless trajectory such that `traj.rho_at(N_bg_i) = rho_i`,
   by bisection over `[0, N_end_traj]`. The noiseless `rho` decreases
   monotonically from start to end for standard single-field models; verify
   this and log a warning if not.
3. The background e-fold count from the instanton start to this density is:
   `N_background_i = N_bg_i - (N_end_traj - N_init_val)`
4. `zeta_i = N_inst_i - N_background_i`

If `rho_i` falls outside `[traj.rho_at(N_end_traj), traj.rho_at(0)]`, mark
`zeta_i = float('nan')` and log a warning for that sample point.

**Step C: scale assignment.**

For each sample point `i`, the number of e-folds before end of inflation at
which its scale exits the horizon is:

```
N_before_end_i = N_end_downflow + (N_total - N_inst_i)
```

where `N_total` is the total instanton duration.

Latest-exit rule: if `N_before_end` is not monotonically decreasing as
`N_inst_i` increases (meaning a scale exited and re-entered), use the minimum
`N_before_end` value seen so far when scanning from `N_inst = 0` upward. This
ensures we use the latest horizon exit for each scale.

For each sample point with valid `zeta`, call `ln_k_phys_Mpc` to obtain
`ln_k_i`, then compute:

```
r_i = 2.0 * pi / exp(ln_k_i)    # comoving radius in Mpc
```

**Step D: build zeta(r), C(r), C_bar(r).**

Collect all sample points with non-NaN `zeta`. Sort by `r_i` ascending. The
first entry (smallest `r`) corresponds to the instanton endpoint (highest `k`);
the last entry (largest `r`) corresponds to the instanton start where
`zeta ≈ 0`.

Build a cubic spline `zeta_spline` over the sorted `(r, zeta)` pairs using
`scipy.interpolate.make_interp_spline`. Compute `zeta_prime(r)` as the
derivative of `zeta_spline`.

At each sample point compute:

```
C_i = (2.0/3.0) * (1.0 - (1.0 + r_i * zeta_prime(r_i))**2)
```

For `C_bar`, compute the cumulative integral numerically. Evaluate the
integrand on a dense grid (at least 10x the number of sample points) by
evaluating the spline. Use `numpy.trapezoid` to accumulate:

```
integrand(r) = r^2 * exp(3*zeta(r)) * (2*r*zeta' + 3*(r*zeta')^2 + (r*zeta')^3)
```

Then at each sample point `r_i`:

```
I_i = trapezoid(integrand, r_grid up to r_i)
C_bar_i = -2.0 * I_i / (r_i^3 * exp(3*zeta(r_i)))
```

For `r` beyond the last sample point, use the analytic extrapolation:

```
C_bar(r) = C_bar_last * (r_last / r)^3
```

where `C_bar_last = C_bar(r_last)` and `r_last` is the largest sample radius.

Flag type-II perturbations: if `C_i < -1.0` at any point, set
`type_II = True` in diagnostics and log a warning.

**Step E: collapse criterion and r_max.**

For `C(r)`:

- Scan sample points for the largest `r_i` with `C_i >= C_threshold`
- If found: `r_max_C = r_i`; if not: `r_max_C = None`

For `C_bar(r)`:

- If `C_bar_last >= C_bar_threshold`: use the analytic extrapolation to find
  `r_max_C_bar = r_last * (C_bar_last / C_bar_threshold)^(1.0/3.0)`
- Otherwise: scan inward from the last sample point for the last crossing of
  `C_bar_threshold`; if none: `r_max_C_bar = None`

**Step F: PBH mass estimate.**

If `r_max` is not None, apply Tomberg (arXiv:2510.09303) Eq. (2.17):

```
M = (1.0 + C_max) * 5.6e15 * (k_star * r_max)^2 * M_sun
```

where `k_star = 0.05` (Mpc^-1, CMB pivot scale), `r_max` is in Mpc, and
`C_max = max(C_i)` over all sample points. Output `M` in solar masses.

Compute separately for `r_max_C` giving `M_C`, and `r_max_C_bar` giving
`M_C_bar`.

#### 2.4.2 Return dict structure

```python
{
    "full": {
        "failure": bool,
        "r": [float, ...],  # Mpc, sorted ascending
        "zeta": [float, ...],
        "C": [float, ...],
        "C_bar": [float, ...],
        "r_max_C": float | None,
        "r_max_C_bar": float | None,
        "M_C": float | None,  # solar masses
        "M_C_bar": float | None,  # solar masses
        "C_max": float | None,
        "V_end_downflow": float | None,
        "N_end_downflow": float | None,
        "diagnostics": dict,
    },
    "slow_roll": {...},  # same structure; None if not provided or failed
}
```

### 2.5 `CompactionFunctionValue`

```python
class CompactionFunctionValue(DatastoreObject):
    """
    zeta, C, and C_bar at a single comoving radius r for one instanton path.
    """

    def __init__(self, store_id, r_Mpc: float, zeta: float, C: float, C_bar: float): ...

    @property
    def r_Mpc(self) -> float: ...

    @property
    def zeta(self) -> float: ...

    @property
    def C(self) -> float: ...

    @property
    def C_bar(self) -> float: ...
```

### 2.6 `CompactionFunction` driver class

```python
class CompactionFunction(DatastoreObject):
    def __init__(
            self,
            store_id: Optional[int],
            full_instanton,  # FullInstantonProxy or None
            slow_roll_instanton,  # SlowRollInstantonProxy or None
            trajectory,  # InflatonTrajectoryProxy
            delta_Nstar: delta_Nstar,
            C_threshold: float = 0.4,
            C_bar_threshold: float = 0.4,
            atol: tolerance = ...,
            rtol: tolerance = ...,
            label: Optional[str] = None,
            tags: Optional[List[store_tag]] = None,
    ): ...
```

Raise `ValueError` in `__init__` if both `full_instanton` and
`slow_roll_instanton` are None.

Properties:

- `available`: `self._my_id is not None`
- `delta_Nstar`: the shard key
- `full_values`: `List[CompactionFunctionValue]`
- `slow_roll_values`: `List[CompactionFunctionValue]`
- `r_max_C_full`, `r_max_C_bar_full`, `M_C_full`, `M_C_bar_full`
- `r_max_C_slow_roll`, `r_max_C_bar_slow_roll`, `M_C_slow_roll`, `M_C_bar_slow_roll`
- `failure_full`, `failure_slow_roll`
- `diagnostics`

`compute()` dispatches `_compute_compaction_function.remote(...)`.

`store()` resolves the Ray future and populates `_full_values` and
`_slow_roll_values` as lists of `CompactionFunctionValue(store_id=None, ...)`.

### 2.7 `CompactionFunctionProxy`

Lightweight proxy holding `store_id` and `delta_Nstar`, following the same
pattern as `FullInstantonProxy`.

---

## Part 3: Datastore registration

### 3.1 New file `Datastore/SQL/ObjectFactories/CompactionFunction.py`

Follow the same pattern as `Datastore/SQL/ObjectFactories/FullInstanton.py`.

**Header table** `compaction_function` (sharded on `delta_Nstar`):

| column                       | type         | notes                    |
|------------------------------|--------------|--------------------------|
| `id`                         | INTEGER PK   |                          |
| `trajectory_serial`          | INTEGER      | FK to InflatonTrajectory |
| `full_instanton_serial`      | INTEGER NULL | FK to FullInstanton      |
| `slow_roll_instanton_serial` | INTEGER NULL | FK to SlowRollInstanton  |
| `delta_Nstar_serial`         | INTEGER      | FK to delta_Nstar        |
| `C_threshold`                | REAL         |                          |
| `C_bar_threshold`            | REAL         |                          |
| `atol_serial`                | INTEGER      |                          |
| `rtol_serial`                | INTEGER      |                          |
| `r_max_C_full`               | REAL NULL    |                          |
| `r_max_C_bar_full`           | REAL NULL    |                          |
| `M_C_full`                   | REAL NULL    | solar masses             |
| `M_C_bar_full`               | REAL NULL    | solar masses             |
| `C_max_full`                 | REAL NULL    |                          |
| `V_end_downflow_full`        | REAL NULL    |                          |
| `N_end_downflow_full`        | REAL NULL    |                          |
| `failure_full`               | INTEGER      | 0 or 1                   |
| `r_max_C_slow_roll`          | REAL NULL    |                          |
| `r_max_C_bar_slow_roll`      | REAL NULL    |                          |
| `M_C_slow_roll`              | REAL NULL    |                          |
| `M_C_bar_slow_roll`          | REAL NULL    |                          |
| `C_max_slow_roll`            | REAL NULL    |                          |
| `V_end_downflow_slow_roll`   | REAL NULL    |                          |
| `N_end_downflow_slow_roll`   | REAL NULL    |                          |
| `failure_slow_roll`          | INTEGER      | 0 or 1                   |
| `validated`                  | INTEGER      | 0 or 1                   |
| `metadata`                   | TEXT         | JSON diagnostics blob    |

**Sample table** `compaction_function_samples` (sharded):

| column          | type       | notes                     |
|-----------------|------------|---------------------------|
| `id`            | INTEGER PK |                           |
| `parent_serial` | INTEGER    | FK to compaction_function |
| `source`        | TEXT       | "full" or "slow_roll"     |
| `r_Mpc`         | REAL       | comoving radius in Mpc    |
| `zeta`          | REAL       |                           |
| `C`             | REAL       |                           |
| `C_bar`         | REAL       |                           |

`build()` matches on `(trajectory_serial, delta_Nstar_serial, C_threshold,
C_bar_threshold, atol_serial, rtol_serial)` and returns `available=False` if
not found. Does not insert stub rows.

`store()` inserts the header row, then bulk-inserts all sample rows for both
sources.

`validate()` sets `validated = 1`.

### 3.2 Register in `Datastore/SQL/Datastore.py`

Add `CompactionFunctionFactory` to the factory registry alongside the existing
instanton factories, following the existing registration pattern exactly.

### 3.3 Update `config/sharding.py`

Add `"compaction_function"` and `"compaction_function_samples"` to
`sharded_tables`, keyed on `delta_Nstar`. Add corresponding entries to
`read_table_config` and `inventory_config` following the existing
`FullInstanton` pattern.

---

## Part 4: Acceptance criteria

1. After the Part 1 revert, `FullInstanton` converges at the same rate as
   before `prompt_full_instanton_refactor.md` was applied. The diagnostic
   print now shows `phi1(T)`, `phi2(T)`, and `rho(T)` in addition to `lambda`
   and `res`.

2. `ln_k_phys_Mpc` at the instanton endpoint (`N_before_end = N_end_downflow`,
   `V_k = V(phi_final)`, `epsilon_k = epsilon(phi_final, pi_final)`) gives a
   scale in the range `[1e-3, 1e3] Mpc^-1` for `N_init=20`, `N_final=17` on
   a quadratic potential.

3. `zeta` at the first instanton sample point (`N_inst = 0`) is zero to within
   numerical tolerance. `zeta` at the last sample point is approximately
   `delta_Nstar`.

4. `C(r)` reaches a positive maximum in the interior of the perturbation and
   falls toward zero at the boundaries.

5. `C_bar(r)` is positive, peaks interior to the perturbation, and falls as
   `1/r^3` for large `r`.

6. Database round-trip preserves all scalar results and sample arrays to
   floating-point precision.

---

## Part 5: Notes and cautions

- **`V_end_downflow` is computed per instanton.** Do not share it between the
  full and slow-roll paths. For `SlowRollInstanton` it will nearly equal the
  noiseless `V_end`; for `FullInstanton` it may differ.

- **`phi2` for `SlowRollInstanton`** must be reconstructed from the attractor
  relation at each sample point, as described in Step A above. The sign is
  negative for a field rolling toward smaller `phi`.

- **`InflationConcepts/noiseless_equations.py` is imported by
  `CompactionFunction`, not by `FullInstanton`.** The downflow integration
  lives entirely inside `_compute_compaction_function`.

- **Sharding key is `delta_Nstar`**, consistent with the instanton tables.

- **The `zeta` profile ordering**: after sorting by `r` ascending, `zeta`
  should increase from near zero (large `r`, instanton start) to approximately
  `delta_Nstar` (small `r`, instanton endpoint). If this ordering is violated,
  log a warning — it may indicate a non-monotonic `N_before_end` that the
  latest-exit rule did not fully resolve.

- **Existing databases** containing `FullInstanton` results computed with the
  old `pi_SR_init` boundary condition at the initial point should be
  recomputed, since the initial momentum now comes from the noiseless
  trajectory rather than the slow-roll approximation.