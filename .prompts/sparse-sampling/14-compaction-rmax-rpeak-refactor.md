# Prompt 14 — CompactionFunction: r_max / r_peak refactor

## Context

The current pipeline computes two radius estimates for PBH mass assignment:
`r_max_C` (outermost radius where `C ≥ C_th`) and `r_max_C_bar` (outermost
radius where `C̄ ≥ C̄_th`). Analysis of large-δN★ profiles has shown that
`C̄_max` becomes very large in the strongly nonlinear regime due to the
exponential metric-weighting in the areal-volume-average denominator
`r³ exp(3ζ(r))`. The `C̄`-based radius is therefore unreliable as a mass
estimator in this regime.

The correct approach is to base all radius and mass estimates on `C(r)` alone,
with two physically distinct estimates:

- **`r_max`**: outermost radius where `C(r) ≥ C_th` (scanning inward from
  grid edge). Measures the spatial extent of the super-critical region.
- **`r_peak`**: radius where `C(r)` is maximised (`argmax C`). Measures the
  characteristic scale of the overdensity peak.

Both radius estimates have associated mass estimates via the Leach-Liddle
horizon-mass formula. There is currently no physical argument to prefer one
over the other in the strongly nonlinear regime; both are retained for
comparison.

`C̄(r)` and `C̄_max` are retained as computed diagnostics but are no longer
used for any radius or mass calculation.

---

## Files to modify

1. `ComputeTargets/CompactionFunction.py`
2. `Datastore/SQL/ObjectFactories/CompactionFunction.py`
3. `plot_InstantonSolutions.py`

---

## Acceptance criteria

- [ ] `_classify_r_max` replaced by `_classify_radii` returning
      `(r_max, r_peak, r_max_at_grid_edge, r_peak_at_grid_edge)`
- [ ] Result dict from `_compute_instanton_path` contains keys
      `r_max`, `M_max`, `r_peak`, `M_peak` (replacing `r_max_C`,
      `M_C`, `r_max_C_bar`, `M_C_bar`)
- [ ] `C_bar_threshold` parameter removed from `_compute_instanton_path`,
      `_compute_compaction_function`, and `CompactionFunction.__init__`
- [ ] `CompactionFunction` class has properties
      `r_max_full`, `M_max_full`, `r_peak_full`, `M_peak_full`,
      `r_max_slow_roll`, `M_max_slow_roll`, `r_peak_slow_roll`,
      `M_peak_slow_roll` (old `r_max_C_*`, `M_C_*`, `r_max_C_bar_*`,
      `M_C_bar_*` properties removed)
- [ ] Schema columns in `sqla_CompactionFunctionFactory.register()` are
      exactly the set listed below — old columns removed, new columns added
- [ ] `store()` writes new column names; `build()` reads new column names
- [ ] `validate_on_startup` performs no migration (databases are regenerated)
- [ ] `plot_InstantonSolutions.py`: all references to old property names
      updated; DOE mass/collapse-scale plots show both `M_max` and `M_peak`
      as separate series; `scalar_data.csv` fieldnames updated
- [ ] No references to `r_max_C_bar`, `M_C_bar`, `C_bar_threshold`,
      `r_max_C_bar_extrapolated` remain anywhere in modified files

---

## Schema — `CompactionFunction` table

Replace the scalar columns block with exactly the following (retain all FK
columns, `C_threshold`, `metadata`, `validated` unchanged):

```python
# Full instanton scalars
sqla.Column("r_max_full_Mpc",              sqla.Float(64), nullable=True),
sqla.Column("M_max_full_SolarMass",        sqla.Float(64), nullable=True),
sqla.Column("r_peak_full_Mpc",             sqla.Float(64), nullable=True),
sqla.Column("M_peak_full_SolarMass",       sqla.Float(64), nullable=True),
sqla.Column("C_max_full",                  sqla.Float(64), nullable=True),
sqla.Column("C_bar_max_full",              sqla.Float(64), nullable=True),
sqla.Column("V_end_downflow_full_PlanckMass4", sqla.Float(64), nullable=True),
sqla.Column("N_end_downflow_full",         sqla.Float(64), nullable=True),
sqla.Column("failure_full",  sqla.Integer, nullable=False, default=1),
# Slow-roll instanton scalars
sqla.Column("r_max_slow_roll_Mpc",         sqla.Float(64), nullable=True),
sqla.Column("M_max_slow_roll_SolarMass",   sqla.Float(64), nullable=True),
sqla.Column("r_peak_slow_roll_Mpc",        sqla.Float(64), nullable=True),
sqla.Column("M_peak_slow_roll_SolarMass",  sqla.Float(64), nullable=True),
sqla.Column("C_max_slow_roll",             sqla.Float(64), nullable=True),
sqla.Column("C_bar_max_slow_roll",         sqla.Float(64), nullable=True),
sqla.Column("V_end_downflow_slow_roll_PlanckMass4", sqla.Float(64), nullable=True),
sqla.Column("N_end_downflow_slow_roll",    sqla.Float(64), nullable=True),
sqla.Column("failure_slow_roll", sqla.Integer, nullable=False, default=1),
```

Remove `C_bar_threshold` column from the schema entirely.

---

## `_classify_radii` specification

Replace `_classify_r_max` with:

```python
def _classify_radii(r_v, C_v, C_threshold: float):
    """
    Compute r_max and r_peak from C(r) sample arrays.

    r_max: outermost r where C >= C_threshold, scanning inward.
           r_max_at_grid_edge=True when C_v[-1] >= C_threshold
           (peak not resolved within grid).
           r_max=None if C nowhere reaches C_threshold.

    r_peak: r at which C is maximised (nanargmax).
            r_peak_at_grid_edge=True when argmax == len-1
            (peak not resolved within grid).

    Returns (r_max, r_peak, r_max_at_grid_edge, r_peak_at_grid_edge).
    """
```

---

## Compute layer changes (`_compute_instanton_path`)

Remove `C_bar_threshold` parameter. Replace the Step E / Step F block:

```python
# ── Step E: radii ─────────────────────────────────────────────────────
r_max, r_peak, r_max_at_grid_edge, r_peak_at_grid_edge = (
    _classify_radii(r_v, C_v, C_threshold)
)

# ── Step F: PBH mass ──────────────────────────────────────────────────
k_star = 0.05 / units.Mpc
C_max    = float(np.nanmax(C_v))
C_bar_max = float(np.nanmax(C_bar_v))

M_max = None
if r_max is not None and not r_max_at_grid_edge and C_max >= C_threshold:
    M_max = (1.0 + C_max) * 5.6e15 * (k_star * r_max) ** 2 * units.SolarMass

M_peak = None
if r_peak is not None and not r_peak_at_grid_edge and C_max >= C_threshold:
    M_peak = (1.0 + C_max) * 5.6e15 * (k_star * r_peak) ** 2 * units.SolarMass
```

Result dict keys: replace `r_max_C`, `M_C`, `r_max_C_bar`, `M_C_bar` with
`r_max`, `M_max`, `r_peak`, `M_peak`. Diagnostics dict: replace
`r_max_C_bar_extrapolated` / `r_max_C_at_grid_edge` with
`r_max_at_grid_edge` / `r_peak_at_grid_edge`.

Note: `M_max` is set to `None` when `r_max_at_grid_edge` is True because in
that case the outer boundary of the super-critical region lies beyond the
sampled grid and the mass estimate would be a lower bound only. `M_peak` is
set to `None` when `r_peak_at_grid_edge` is True for the same reason.
`C_bar_max` is still computed and returned; it is not used for mass
assignment.

---

## `CompactionFunction` class properties

Remove: `r_max_C_full`, `r_max_C_bar_full`, `M_C_full`, `M_C_bar_full`,
`r_max_C_slow_roll`, `r_max_C_bar_slow_roll`, `M_C_slow_roll`,
`M_C_bar_slow_roll`, `C_bar_threshold`.

Add:
```python
@property
def r_max_full(self) -> Optional[float]: ...

@property
def M_max_full(self) -> Optional[float]: ...

@property
def r_peak_full(self) -> Optional[float]: ...

@property
def M_peak_full(self) -> Optional[float]: ...

# and slow_roll counterparts
```

Retain: `C_max_full`, `C_bar_max_full`, `C_max_slow_roll`,
`C_bar_max_slow_roll`, `C_threshold`.

Remove `C_bar_threshold` from `__init__` signature and `_C_bar_threshold`
attribute. Update `_populate_from_result` to use new result dict keys.

---

## Factory changes (`sqla_CompactionFunctionFactory`)

**`build()` SELECT query**: remove `r_max_C_bar_*`, `M_C_bar_*` columns;
add `r_max_*`, `M_max_*`, `r_peak_*`, `M_peak_*` columns. Remove
`C_bar_threshold` from constructor call (remove `C_bar_threshold` column from
schema and query entirely).

**`build()` restore block**: update attribute assignments to match new
property names.

**`store()` inserter dict**: replace old keys with:
```python
"r_max_full_Mpc":              _r(full_result, "r_max"),
"M_max_full_SolarMass":        _M(full_result, "M_max"),
"r_peak_full_Mpc":             _r(full_result, "r_peak"),
"M_peak_full_SolarMass":       _M(full_result, "M_peak"),
"C_max_full":                  _plain(full_result, "C_max"),
"C_bar_max_full":              _plain(full_result, "C_bar_max"),
# ... and slow_roll equivalents
```

**`validate_on_startup`**: remove the existing `ALTER TABLE ADD COLUMN`
migration for `C_bar_max_*` (databases are regenerated; no migration needed).

---

## `plot_InstantonSolutions.py` changes

### `_extract_compaction_scalars` helper (lines ~130–175)

Replace:
```python
"r_max_C_full_Mpc":     _div(cf.r_max_C_full, Mpc),
"r_max_C_bar_full_Mpc": _div(cf.r_max_C_bar_full, Mpc),
"M_C_full_solar":       _div(cf.M_C_full, SolarMass),
"M_C_bar_full_solar":   _div(cf.M_C_bar_full, SolarMass),
# ... slow_roll equivalents
```
With:
```python
"r_max_full_Mpc":       _div(cf.r_max_full, Mpc),
"r_peak_full_Mpc":      _div(cf.r_peak_full, Mpc),
"M_max_full_solar":     _div(cf.M_max_full, SolarMass),
"M_peak_full_solar":    _div(cf.M_peak_full, SolarMass),
# ... slow_roll equivalents
```

Update the `keys` list and unpacking tuple accordingly.

### Compaction summary plot (lines ~1112–1142)

Replace the tuple unpacking and all `r_max_C_bar_*` / `M_C_bar_*` references
with the new names. The compaction summary plot should show `r_max` and
`r_peak` as separate series (where available) rather than `r_max_C` and
`r_max_C_bar`.

### DOE mass / collapse-scale plots (lines ~1980–1985)

Currently plots `M_C_bar` and `r_max_C_bar` as the primary mass/scale series.
Replace with two series per instanton type:
- `M_max` (circle markers, solid line) — labelled `M_max (full)` / `M_max (SR)`
- `M_peak` (square markers, dashed line) — labelled `M_peak (full)` / `M_peak (SR)`

Same treatment for the `r` panel.

### `_collect_doe_scalar_data` (lines ~1794–1805)

Replace `M_C_bar_*`, `r_max_C_bar_*`, `M_C_*`, `r_max_C_*` dict keys with:
```python
"r_max_full_Mpc":       s[...],
"r_peak_full_Mpc":      s[...],
"M_max_full_solar":     s[...],
"M_peak_full_solar":    s[...],
"r_max_sr_Mpc":         s[...],
"r_peak_sr_Mpc":        s[...],
"M_max_sr_solar":       s[...],
"M_peak_sr_solar":      s[...],
```

The `scalar_data.csv` fieldnames follow automatically from the dict keys.

---

## Out of scope

- `regression_InstantonOutputs.py`: the GP targets `log(M_PBH)` and
  `log(r_PBH)` will be updated manually by the user to point to whichever
  of `M_max` / `M_peak` columns they choose after reviewing results. No
  automated change to the regression script.
- The `CompactionFunctionSamples` child table is unchanged.
- No change to `C_threshold` default value (0.4).
- No change to how `C̄(r)` is computed — only its use for radius/mass
  assignment is removed.

---

## Single commit target

All changes in one commit: `refactor(compaction): replace C_bar-based radius
estimates with r_max and r_peak from C(r)`.
