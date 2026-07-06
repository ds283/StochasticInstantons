# Datastore unit-conversion discipline

This rule has no `paths:` frontmatter, so it loads at session start alongside
`CLAUDE.md`. It applies to every factory in `Datastore/SQL/ObjectFactories/` and
every compute target in `ComputeTargets/` that stores dimensionful quantities.

## Core rule

**Never write a bare float to the database when it carries physical dimensions.**
Divide by the storage unit before writing; multiply by it on reading. Encode the
storage unit in the column or JSON-key name so that the database is self-documenting
and safe to read from any unit system.

---

## Suffix naming convention

The unit specifier is a **suffix** appended to the physical quantity name:

| Unit stored | Suffix |
|---|---|
| PlanckMass | `_PlanckMass` |
| 1/PlanckMass | `_invPlanckMass` |
| PlanckMass⁴ | `_PlanckMass4` |
| Mpc | `_Mpc` |
| SolarMass | `_SolarMass` |

When the column already carries a `_full` or `_slow_roll` qualifier, the unit
specifier is appended **after** that qualifier:

```
r_max_C_full_Mpc           ✓
r_max_C_Mpc_full           ✗
V_end_downflow_slow_roll_PlanckMass4   ✓
V_end_downflow_PlanckMass4_slow_roll   ✗
```

Dimensionless quantities (`C`, `C_bar`, `zeta`, e-fold counts `N_*`, action `msr_action`)
require no suffix.

---

## Conversion table

| Dimension | Example fields | Store (write) | Restore (read) |
|---|---|---|---|
| mass¹ | φ, π, φ₁, φ₂ | `value / units.PlanckMass` | `stored * units.PlanckMass` |
| mass⁻¹ | P₁, P₂ (MSR response fields) | `value * units.PlanckMass` | `stored / units.PlanckMass` |
| mass⁴ | V (potential) | `value / units.PlanckMass**4` | `stored * units.PlanckMass**4` |
| length | r (comoving radius) | `value / units.Mpc` | `stored * units.Mpc` |
| mass | M (PBH mass) | `value / units.SolarMass` | `stored * units.SolarMass` |

---

## Radial coordinate convention

`ln_k_phys_Mpc()` in `ComputeTargets/CompactionFunction.py` returns
`ln(k in working_units⁻¹)` — **not** `ln(k in Mpc⁻¹)` — because its
return value includes `- log(units.Mpc)`. As a consequence `r = 2π/exp(lnk)`
is in working units, consistent with all other length quantities. The factory
stores `v.r / units.Mpc` and restores `row.r_Mpc * units.Mpc`.

**Do not remove the `- log(Mpc)` term from `ln_k_phys_Mpc`.** Removing it would
make `r` unit-system-independent (always in Mpc) while all other quantities
remain in working units, breaking dimensional consistency across the code.

---

## How factories access `units`

| Factory | Source of `units` |
|---|---|
| `sqla_InflatonTrajectory_factory` | `obj._potential._units` |
| `sqla_FullInstantonFactory` | `obj._trajectory.units` (from `InflatonTrajectoryProxy`) |
| `sqla_SlowRollInstantonFactory` | `obj._trajectory.units` |
| `sqla_CompactionFunctionFactory` | `obj._trajectory.units` (store/populate); `payload["trajectory"].units` (build) |
| `sqla_GradientCoupledInstantonFactory` | `obj._trajectory.units` (store); `trajectory.units` where `trajectory = payload["trajectory"]` (build/populate) |

`InflatonTrajectoryProxy` carries `self._units = model._potential._units` set in
`__init__` and exposed via `@property units`. This is the only unit-carrying scalar
the proxy needs to propagate; it avoids Ray calls inside factories.

For factories where `_populate()` is also called from `read_table()` (with
`trajectory=None`), `_populate()` accepts `units=None` as a keyword argument
and `read_table()` passes its own `units` parameter through.

---

## JSON key names in `fields_json` columns

Value tables store fields as JSON rather than individual columns. Apply the same
suffix convention to the JSON keys:

```python
# InflatonTrajectory — φ and π have mass dimension 1
json.dumps({
    "phi_PlanckMass": [v.phi / units.PlanckMass],
    "pi_PlanckMass":  [v.pi  / units.PlanckMass],
})

# FullInstanton — φ₁, φ₂ dim +1; P₁, P₂ dim -1
json.dumps({
    "phi1_PlanckMass":  [v.phi1 / units.PlanckMass],
    "phi2_PlanckMass":  [v.phi2 / units.PlanckMass],
    "P1_invPlanckMass": [v.P1 * units.PlanckMass],
    "P2_invPlanckMass": [v.P2 * units.PlanckMass],
})

# SlowRollInstanton
json.dumps({
    "phi_PlanckMass":   [v.phi / units.PlanckMass],
    "P1_invPlanckMass": [v.P1 * units.PlanckMass],
})
```

Restore symmetrically: `data["phi_PlanckMass"][0] * units.PlanckMass`, etc.

---

## Checklist for a new factory with dimensionful fields

1. Add unit-suffixed column names in `register()`.
2. In `store()`: obtain `units` from the appropriate source (see table above),
   then divide or multiply before inserting.
3. In `_populate()` / `build()`: multiply or divide when constructing the Python
   object from DB values.
4. Add `units=None` kwarg to `_populate()` if it is also called from `read_table()`.
5. Verify the JSON key names in `fields_json` columns follow the convention.
6. Do **not** apply unit conversion to dimensionless scalars (C, zeta, N-values, etc.).
