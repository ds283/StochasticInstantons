# Combined prompt: revert `FullInstanton` final boundary condition and implement `CompactionFunction`

## Prerequisites

This prompt assumes:

- `./prompts/02-fullinstanton-bcs.md` has been applied
- `./prompts/02a-implement-jacobian.md` has been applied
- The `rho`-final boundary condition is not converging and must be reverted

It makes four groups of changes:

1. **Revert** the final boundary condition of `FullInstanton` from `rho_final`
   back to `phi_final`, retaining all other changes from previous prompts
2. **Add** a `CosmologicalParams` domain object and factory
3. **Implement** the `CompactionFunction` compute target
4. **Register** new targets in the datastore and configuration

All file paths use the **source-tree** layout.

---

## Part 1: Revert `FullInstanton` final boundary condition

### 1.1 `ComputeTargets/FullInstanton.py`

Revert **only** the `rho_final` changes. All other changes from previous
prompts are retained.

**Restore `phi_final: float` parameter, remove `rho_final: float`:**

```python
@ray.remote
def _compute_full_instanton(
        trajectory,
        phi_init: float,
        pi_init: float,  # retained rename from pi_SR_init
        phi_final: float,  # restored
        N_total: float,
        N_sample: list,
        atol: float,
        rtol: float,
        label: Optional[str] = None,
) -> dict:
```

**Restore the outer Newton residual to field-space:**

```python
residual = p1[-1] - phi_final
```

**Restore the single-component `dres_dlam`:**

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

**Restore `OUTER_TOL` as a field-space tolerance:**

```python
OUTER_TOL = max(atol * 100.0, 1e-6)
```

**Retain the `compute_rho` helper and enhanced diagnostic print:**

```python
def compute_rho(phi1_val, phi2_val):
    Mp = potential._units.PlanckMass
    return 3.0 * (Mp ** 2) * potential.H_sq(phi1_val, phi2_val)


if label:
    print(
        f"[{label}] outer {outer}: lambda={lam:.4g}, "
        f"phi1(T)={p1[-1]:.6g}, phi2(T)={p2[-1]:.6g}, "
        f"rho(T)={compute_rho(p1[-1], p2[-1]):.6g}, "
        f"res={residual:.2e}"
    )
```

**Restore the fallback nudge:**

```python
newton_fallback_count += 1
lam += (phi_final - p1[-1]) * 0.1
```

**In `FullInstanton.compute()`**, restore `phi_final`:

```python
phi_final = traj.phi_at(N_end - float(self._N_final))

self._compute_ref = _compute_full_instanton.remote(
    trajectory=self._trajectory,
    phi_init=phi_init,
    pi_init=pi_init,
    phi_final=phi_final,
    N_total=N_total,
    ...
)
```

### 1.2 What is retained from previous prompts

Do **not** revert any of the following:

- `InflationConcepts/noiseless_equations.py` — keep entirely
- `InflatonTrajectory.rho_at()` — keep
- `pi_init` rename from `pi_SR_init` throughout `FullInstanton` — keep
- `AbstractPotential.drho_dphi()` and `AbstractPotential.drho_dpi()` — keep
- Enhanced diagnostic print showing `phi1(T)`, `phi2(T)`, `rho(T)` — keep

---

## Part 2: `CosmologicalParams` domain object and factory

### 2.1 `CosmologicalModels/params.py` — no base class change needed

The existing `Planck2013`, `Planck2015`, `Planck2018` classes remain as plain
Python classes with class-level attributes. They are **not** `DatastoreObject`
subclasses — they are lightweight parameter bundles, not persistable objects
in their own right. No changes to `params.py` are required.

### 2.2 New class `CosmologicalParams` in `CosmologicalModels/cosmo_params.py`

```python
from Datastore.object import DatastoreObject
from typing import Optional


class CosmologicalParams(DatastoreObject):
    """
    Persistable wrapper around a cosmological parameter bundle.

    Usage:
        params = Planck2018()
        cosmo  = CosmologicalParams(store_id=None, params=params)

    After pool.object_get(), cosmo.store_id is set and cosmo is available.
    """

    def __init__(self, store_id: Optional[int], params):
        DatastoreObject.__init__(self, store_id)
        self._params = params

    @property
    def name(self) -> str:
        return self._params.name

    @property
    def omega_cc(self) -> float:
        return self._params.omega_cc

    @property
    def omega_m(self) -> float:
        return self._params.omega_m

    @property
    def h(self) -> float:
        return self._params.h

    @property
    def f_baryon(self) -> float:
        return self._params.f_baryon

    @property
    def T_CMB_Kelvin(self) -> float:
        return self._params.T_CMB_Kelvin

    @property
    def Neff(self) -> float:
        return self._params.Neff
```

### 2.3 New file `Datastore/SQL/ObjectFactories/CosmologicalParams.py`

```python
class sqla_cosmological_params_factory(SQLAFactoryBase):

    def register(self):
        return {
            "version": False,
            "timestamp": True,
            "columns": [
                sqla.Column("name", sqla.String, index=True, unique=True),
                sqla.Column("omega_cc", sqla.Float(64)),
                sqla.Column("omega_m", sqla.Float(64)),
                sqla.Column("h", sqla.Float(64)),
                sqla.Column("f_baryon", sqla.Float(64)),
                sqla.Column("T_CMB_Kelvin", sqla.Float(64)),
                sqla.Column("Neff", sqla.Float(64)),
            ],
        }

    def build(self, payload, conn, table, inserter, tables, inserters):
        params = payload["params"]
        name = params.name

        query = sqla.select(table.c.serial).filter(table.c.name == name)
        row = conn.execute(query).one_or_none()

        if row is None:
            store_id = inserter(conn, {
                "name": name,
                "omega_cc": params.omega_cc,
                "omega_m": params.omega_m,
                "h": params.h,
                "f_baryon": params.f_baryon,
                "T_CMB_Kelvin": params.T_CMB_Kelvin,
                "Neff": params.Neff,
            })
            obj = CosmologicalParams(store_id=store_id, params=params)
            obj._new_insert = True
        else:
            store_id = row.serial
            obj = CosmologicalParams(store_id=store_id, params=params)
            obj._deserialized = True

        return obj
```

Matching is on `name` (exact string, unique per parameter set). No separate
`store()` or `validate()` methods needed — `build()` is idempotent.

### 2.4 Register in `Datastore/SQL/Datastore.py`

```python
from CosmologicalModels.cosmo_params import CosmologicalParams
from Datastore.SQL.ObjectFactories.CosmologicalParams import sqla_cosmological_params_factory

# in the factory registry:
"CosmologicalParams": sqla_cosmological_params_factory(),
```

Add `"cosmological_params"` to `replicated_tables` in `config/sharding.py`.

### 2.5 Usage in `main.py`

```python
from CosmologicalModels.params import Planck2018
from CosmologicalModels.cosmo_params import CosmologicalParams

cosmo = ray.get(pool.object_get("CosmologicalParams", payload={"params": Planck2018()}))
```

`cosmo` is a `CosmologicalParams` instance with `available=True` and
`store_id` set. Pass it explicitly to `CompactionFunction` as an input.
Subsequent calls with the same `Planck2018()` bundle return the same
`store_id` (idempotent upsert on `name`).

---

No other parts of `prompt_compaction_function_v3.md` change. In particular,
the remote function signature and `ln_k_phys_Mpc` are unchanged — the remote
function still receives `cosmo_T_CMB_Kelvin: float` and `cosmo_store_id: int`
as separate scalar arguments, extracted from `cosmo` by the driver class
`compute()` method before dispatch.

---

## Part 3: New file `ComputeTargets/CompactionFunction.py`

### 3.1 Scale matching function

Define a module-level function (no Ray, no class):

```python
def ln_k_phys_Mpc(
        N_before_end: float,
        V_k: float,
        epsilon_k: float,
        V_end_downflow: float,
        units,  # UnitsLike instance
        cosmo,  # CosmologicalParams instance
) -> float:
```

Implements the matching equation derived from Leach & Liddle (astro-ph/0305263)
Eq. (2), with instantaneous reheating:

```
ln(k / Mpc^-1) = -N_before_end
               + ln(Mpc * Mp)
               + ln(T_CMB / Mp)
               + (1/4) * ln(pi^2 / 135)
               + (1/4) * ln( V_k / (V_end_downflow * (1 - epsilon_k/3)) )
```

Implementation:

```python
from math import log, pi as PI


def ln_k_phys_Mpc(N_before_end, V_k, epsilon_k, V_end_downflow, units, cosmo):
    Mp = units.PlanckMass  # reduced Planck mass in working units
    Mpc = units.Mpc  # 1 Mpc in working units (length)
    T_CMB = cosmo.T_CMB_Kelvin * units.Kelvin  # CMB temperature in working units

    return (
            - N_before_end
            + log(Mpc * Mp)
            + log(T_CMB / Mp)
            + 0.25 * log(PI ** 2 / 135.0)
            + 0.25 * log(V_k / (V_end_downflow * (1.0 - epsilon_k / 3.0)))
    )
```

All arguments are in the working unit system. `V_k` and `V_end_downflow` are
returned by `potential.V()` and are therefore already in working units.
`epsilon_k` and `N_before_end` are dimensionless. No conversion constants are
hard-coded; everything flows from `units` and `cosmo`.

### 3.2 `@ray.remote` compute function

```python
@ray.remote
def _compute_compaction_function(
        full_instanton_proxy,  # FullInstantonProxy or None
        slow_roll_instanton_proxy,  # SlowRollInstantonProxy or None
        trajectory_proxy,  # InflatonTrajectoryProxy
        cosmo_class_name: str,  # e.g. "Planck2018"
        cosmo_store_id: int,
        cosmo_T_CMB_Kelvin: float,  # only the field needed by ln_k_phys_Mpc
        C_threshold: float,
        C_bar_threshold: float,
        atol: float,
        rtol: float,
        label: Optional[str] = None,
) -> dict:
```

`cosmo` is reconstructed inside the remote function from `cosmo_class_name`
and `cosmo_store_id` to avoid serialisation issues with `DatastoreObject`.
Only `T_CMB_Kelvin` is actually needed by `ln_k_phys_Mpc`; passing it
explicitly is simpler than deserialising the full object. The `cosmo_store_id`
is recorded in the return dict for provenance.

Inside the function, obtain `units` from the potential:

```python
traj = trajectory_proxy.get()
potential = traj._potential
units = potential._units
```

Then construct a lightweight cosmo proxy:

```python
class _CosmoProxy:
    def __init__(self, T_CMB_Kelvin):
        self.T_CMB_Kelvin = T_CMB_Kelvin


cosmo = _CosmoProxy(cosmo_T_CMB_Kelvin)
```

This is sufficient for `ln_k_phys_Mpc`, which only needs `cosmo.T_CMB_Kelvin`.

The function returns:

```python
{
    "full": {...} or None,
    "slow_roll": {...} or None,
    "cosmo_store_id": cosmo_store_id,
}
```

#### 3.2.1 Per-instanton computation

For each available instanton, perform steps A-F below. The instanton provides
sample points `{N_inst, phi1, phi2}`. For `SlowRollInstanton`, which stores
only `{phi, P1}`, reconstruct at each sample point:

```python
phi1 = phi
phi2 = -potential.dV_dphi(phi) / (3.0 * potential.H_sq(phi, 0.0))  # pi_SR
```

**Step A: downflow trajectory from instanton endpoint.**

```python
from InflationConcepts.noiseless_equations import integrate_noiseless_trajectory

sol_down, _, _ = integrate_noiseless_trajectory(
    phi1[-1], phi2[-1], potential, atol, rtol, label=label
)
```

Extract:

```python
N_end_downflow = sol_down.t_events[0][0]
phi_end_downflow = sol_down.y_events[0][0][0]
V_end_downflow = potential.V(phi_end_downflow)
```

If `sol_down` is None or `t_events[0]` is empty, record `failure = True`
and skip remaining steps for this path.

**Step B: delta-N at each sample point.**

```python
traj = trajectory_proxy.get()
N_end_traj = traj.N_end
N_init_val = instanton.N_init  # e-folds before end of inflation at instanton start
Mp = units.PlanckMass
```

For each sample point `i`:

```python
rho_i = 3.0 * Mp ** 2 * potential.H_sq(phi1_i, phi2_i)

# bisect to find N_bg_i such that traj.rho_at(N_bg_i) == rho_i
from scipy.optimize import brentq

rho_start = traj.rho_at(0.0)
rho_end = traj.rho_at(N_end_traj)

if not (rho_end <= rho_i <= rho_start):
    zeta_i = float('nan')
    # log warning
else:
    N_bg_i = brentq(lambda N: traj.rho_at(N) - rho_i, 0.0, N_end_traj,
                    xtol=atol, rtol=rtol)
    N_background_i = N_bg_i - (N_end_traj - N_init_val)
    zeta_i = N_inst_i - N_background_i
```

**Step C: scale assignment.**

```python
N_before_end_i = N_end_downflow + (N_total - N_inst_i)
```

Latest-exit rule: replace `N_before_end_i` with
`min(N_before_end_j for j <= i)` if `N_before_end` is non-monotone.

For each non-NaN point:

```python
ln_k_i = ln_k_phys_Mpc(N_before_end_i, potential.V(phi1_i),
                       potential.epsilon(phi1_i, phi2_i),
                       V_end_downflow, units, cosmo)
r_i = 2.0 * PI / exp(ln_k_i)  # comoving radius in Mpc
```

**Step D: `zeta(r)`, `C(r)`, `C_bar(r)`.**

Sort non-NaN sample points by `r_i` ascending. Build cubic spline
`zeta_spline` over `(r, zeta)`. Compute `zeta_prime(r)` from spline
derivative.

At each sample point:

```python
C_i = (2.0 / 3.0) * (1.0 - (1.0 + r_i * zeta_prime(r_i)) ** 2)
```

For `C_bar`, build a dense `r` grid (at least 10x sample count) and compute:

```python
rz = r_dense * zeta_prime_dense
integrand = r_dense ** 2 * np.exp(3.0 * zeta_dense) * (
        2.0 * rz + 3.0 * rz ** 2 + rz ** 3)
```

Accumulate with `numpy.trapezoid`. At each sample `r_i`:

```python
C_bar_i = -2.0 * integral_to_r_i / (r_i ** 3 * np.exp(3.0 * zeta_i))
```

Beyond `r_last`, extrapolate analytically:

```python
C_bar(r) = C_bar_last * (r_last / r) ** 3
```

Flag type-II: if any `C_i < -1.0`, set `type_II = True` in diagnostics.

**Step E: `r_max`.**

For `C(r)`: largest `r_i` with `C_i >= C_threshold`, else `None`.

For `C_bar(r)`:

- If `C_bar_last >= C_bar_threshold`:
  `r_max_C_bar = r_last * (C_bar_last / C_bar_threshold)**(1.0/3.0)`
- Else: last crossing of `C_bar_threshold` scanning inward; else `None`.

**Step F: PBH mass.**

```python
k_star = 0.05  # Mpc^-1
C_max = max(C_i)
if r_max is not None:
    M = (1.0 + C_max) * 5.6e15 * (k_star * r_max) ** 2  # solar masses
```

Compute `M_C` from `r_max_C` and `M_C_bar` from `r_max_C_bar`.

#### 3.2.2 Return dict structure

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
    "cosmo_store_id": int,
}
```

### 3.3 `CompactionFunctionValue`

```python
class CompactionFunctionValue(DatastoreObject):
    def __init__(self, store_id, r_Mpc: float, zeta: float,
                 C: float, C_bar: float): ...

    @property
    def r_Mpc(self) -> float: ...

    @property
    def zeta(self) -> float: ...

    @property
    def C(self) -> float: ...

    @property
    def C_bar(self) -> float: ...
```

### 3.4 `CompactionFunction` driver class

```python
class CompactionFunction(DatastoreObject):
    def __init__(
            self,
            store_id: Optional[int],
            full_instanton,  # FullInstantonProxy or None
            slow_roll_instanton,  # SlowRollInstantonProxy or None
            trajectory,  # InflatonTrajectoryProxy
            cosmo,  # CosmologicalParams instance with store_id set
            delta_Nstar: delta_Nstar,
            C_threshold: float = 0.4,
            C_bar_threshold: float = 0.4,
            atol: tolerance = ...,
            rtol: tolerance = ...,
            label: Optional[str] = None,
            tags: Optional[List[store_tag]] = None,
    ): ...
```

Raise `ValueError` if both `full_instanton` and `slow_roll_instanton` are None.

`compute()` passes to the remote function:

- `cosmo_class_name = type(cosmo).__name__`
- `cosmo_store_id = cosmo.store_id`
- `cosmo_T_CMB_Kelvin = cosmo.T_CMB_Kelvin`

`store()` resolves the Ray future and populates `_full_values` and
`_slow_roll_values` as `List[CompactionFunctionValue(store_id=None, ...)]`.

### 3.5 `CompactionFunctionProxy`

Lightweight proxy holding `store_id` and `delta_Nstar`, following the same
pattern as `FullInstantonProxy`.

---

## Part 4: Datastore registration

### 4.1 New file `Datastore/SQL/ObjectFactories/CompactionFunction.py`

Follow `Datastore/SQL/ObjectFactories/FullInstanton.py`.

**Header table** `compaction_function` (sharded on `delta_Nstar`):

| column                       | type         | notes                           |
|------------------------------|--------------|---------------------------------|
| `id`                         | INTEGER PK   |                                 |
| `trajectory_serial`          | INTEGER      | FK to InflatonTrajectory        |
| `full_instanton_serial`      | INTEGER NULL | FK to FullInstanton             |
| `slow_roll_instanton_serial` | INTEGER NULL | FK to SlowRollInstanton         |
| `delta_Nstar_serial`         | INTEGER      | FK to delta_Nstar               |
| `cosmo_serial`               | INTEGER      | FK to cosmological params table |
| `C_threshold`                | REAL         |                                 |
| `C_bar_threshold`            | REAL         |                                 |
| `atol_serial`                | INTEGER      |                                 |
| `rtol_serial`                | INTEGER      |                                 |
| `r_max_C_full`               | REAL NULL    | Mpc                             |
| `r_max_C_bar_full`           | REAL NULL    | Mpc                             |
| `M_C_full`                   | REAL NULL    | solar masses                    |
| `M_C_bar_full`               | REAL NULL    | solar masses                    |
| `C_max_full`                 | REAL NULL    |                                 |
| `V_end_downflow_full`        | REAL NULL    | working units                   |
| `N_end_downflow_full`        | REAL NULL    | e-folds                         |
| `failure_full`               | INTEGER      | 0 or 1                          |
| `r_max_C_slow_roll`          | REAL NULL    | Mpc                             |
| `r_max_C_bar_slow_roll`      | REAL NULL    | Mpc                             |
| `M_C_slow_roll`              | REAL NULL    | solar masses                    |
| `M_C_bar_slow_roll`          | REAL NULL    | solar masses                    |
| `C_max_slow_roll`            | REAL NULL    |                                 |
| `V_end_downflow_slow_roll`   | REAL NULL    | working units                   |
| `N_end_downflow_slow_roll`   | REAL NULL    | e-folds                         |
| `failure_slow_roll`          | INTEGER      | 0 or 1                          |
| `validated`                  | INTEGER      | 0 or 1                          |
| `metadata`                   | TEXT         | JSON diagnostics blob           |

`build()` matches on `(trajectory_serial, delta_Nstar_serial, cosmo_serial,
C_threshold, C_bar_threshold, atol_serial, rtol_serial)`. Returns
`available=False` if not found. Never inserts stub rows.

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

`r_Mpc` is stored in Mpc regardless of working units, as this is the natural
observable unit and the matching equation produces it directly.

### 4.2 Register in `Datastore/SQL/Datastore.py`

Add `CompactionFunctionFactory` to the factory registry alongside existing
instanton factories.

### 4.3 Update `config/sharding.py`

```python
# sharded_tables:
"compaction_function": "delta_Nstar",
"compaction_function_samples": "delta_Nstar",
```

Add corresponding entries to `read_table_config` and `inventory_config`
following the `FullInstanton` pattern.

---

## Part 5: Acceptance criteria

1. After Part 1 revert, `FullInstanton` converges at the same rate as before
   `prompt_full_instanton_refactor.md` was applied. The diagnostic print shows
   `phi1(T)`, `phi2(T)`, `rho(T)`, and `res`.

2. `pool.object_get("Planck2018", ...)` returns a `Planck2018` object with
   `available=True` and a consistent `store_id` across multiple calls.

3. `ln_k_phys_Mpc` at the instanton endpoint returns a value in the range
   `log(1e-3)` to `log(1e3)` for `N_init=20`, `N_final=17` on a quadratic
   potential.

4. `zeta` at `N_inst=0` is zero to within numerical tolerance. `zeta` at the
   last sample point is approximately `delta_Nstar`.

5. After sorting by `r` ascending, `zeta` increases monotonically from near
   zero (large `r`) to approximately `delta_Nstar` (small `r`).

6. `C(r)` is positive in the interior and falls to zero at the boundaries.
   Values outside `(-1, 1)` trigger a logged warning.

7. `C_bar(r)` is positive, peaks in the interior, and falls as `1/r^3` for
   large `r`.

8. Every `compaction_function` row has a non-null `cosmo_serial` FK.

9. Database round-trip preserves all scalar results and sample arrays.

---

## Part 6: Notes and cautions

- **Unit correctness.** `ln_k_phys_Mpc` obtains all dimensional quantities
  from `units` (a `UnitsLike` instance). `T_CMB = cosmo.T_CMB_Kelvin *
  units.Kelvin` converts the Kelvin value to working units. `units.Mpc` and
  `units.PlanckMass` provide `Mpc` and `Mp` in working units. No conversion
  constants are hard-coded anywhere.

- **`V_end_downflow` is per-instanton.** Computed fresh from the downflow
  trajectory for each path. Not shared between `"full"` and `"slow_roll"`.

- **`phi2` for `SlowRollInstanton`** is reconstructed at each sample point
  from the attractor relation. Sign is negative for a field rolling toward
  smaller `phi`.

- **`InflationConcepts/noiseless_equations.py` is imported only by
  `CompactionFunction`.** The downflow integration does not touch `FullInstanton`.

- **Shard key is `delta_Nstar`**, consistent with instanton tables.

- **`r_Mpc` stored in Mpc** regardless of working units.

- **Existing `FullInstanton` databases** should be recomputed since `pi_init`
  now comes from the noiseless trajectory rather than the slow-roll
  approximation.

- **`cosmo_serial` FK** is a foreign key into the single `cosmological_params`
  replicated table, which holds all parameter sets distinguished by their
  `name` column. No companion column is needed to identify the table.