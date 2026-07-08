### Prompt U3 — Persist + rehydrate the parity scalar columns

- **Implements:** design §7.2 (bullet 3), §7.3 (bullet 1, schema part).
- **Track / step:** U3
- **Depends on:** U2a, U2b
- **Files (real paths):**
  - edit: `ComputeTargets/GradientCoupledInstanton/GradientCoupledInstanton.py`
    (the `GradientCoupledInstanton` class: `__init__`, new properties, and
    `_populate_from_result`; the `GradientCoupledInstantonProfileValue` class
    already gained `C_bar` in U2a — no further edit needed there)
  - edit: `Datastore/SQL/ObjectFactories/GradientCoupledInstanton.py` (all
    three factory classes: `sqla_GradientCoupledInstantonFactory.register/build/store`,
    `sqla_GradientCoupledInstantonProfileFactory.register`)
- **Context to read first:** `Datastore/SQL/ObjectFactories/CompactionFunction.py`
  in full — this is the naming/unit-conversion convention to mirror exactly
  (`r_max_full_Mpc`, `M_max_full_SolarMass`, `V_end_downflow_full_PlanckMass4`,
  `compensated_full`/`type_II_full` stored as `sqla.Integer` 0/1 and restored
  via `bool(row.x) if row.x is not None else None`, and the `_restore_r`/
  `_restore_M`/`_restore_V` closures used in `build()`); the current
  `GradientCoupledInstanton` factory's `register()`/`build()`/`store()` in
  full (this is the file you are editing — read all of it, not just the
  `msr_action`/`noise_*` columns, since your new columns sit alongside
  them); `GradientCoupledInstanton.py`'s current `__init__`,
  `_populate_from_result`, and `store()` methods.
- **Assumable interfaces:**
  - U2b's Ray-remote function now returns these additional keys in its
    result dict (unsuffixed, per design §7.1): `C_peak`, `C_bar_peak`,
    `C_min`, `compensated` (bool), `type_II` (bool), `r_max`, `r_peak`
    (both in working units, i.e. reduced-Planck length, NOT yet Mpc),
    `M_max`, `M_peak` (both in working units, NOT yet solar masses),
    `V_end_downflow` (working units, i.e. `Mp^4`-like, NOT yet
    `PlanckMass**4`-normalised), `N_end_downflow` (dimensionless e-folds,
    no conversion needed). `scales["C_bar"]` (a per-node array, U2a) is
    already flowing into `GradientCoupledInstantonProfileValue.C_bar` via
    the existing profile-construction call site — no change needed there.
  - The current `_populate_from_result` method signature and body (verbatim,
    so you insert at the right point): it sets `self._diagnostics`, bails
    out to `self._failure = True` with empty `_values`/`_profile` on
    failure, then on success sets `self._N_total`, `self._msr_action`,
    `self._noise_field_min/mean/max`, `self._noise_mom_min/mean/max`, then
    builds `self._profile` and `self._values`.
- **Task:**
  1. In `GradientCoupledInstanton.__init__`, add instance attributes for the
     new scalars (default `None`), mirroring the existing
     `self._msr_action: Optional[float] = None` pattern: `self._C_peak`,
     `self._C_bar_peak`, `self._C_min`, `self._compensated`, `self._type_II`,
     `self._r_max`, `self._r_peak`, `self._M_max`, `self._M_peak`,
     `self._V_end_downflow`, `self._N_end_downflow`.
  2. Add a `@property` for each, mirroring `msr_action`'s property exactly
     (plain `return self._x`).
  3. In `_populate_from_result`, after the existing `self._noise_mom_max = ...`
     line and before the `self._profile = [...]` construction, add:
     `self._C_peak = data.get("C_peak")`, `self._C_bar_peak = data.get("C_bar_peak")`,
     `self._C_min = data.get("C_min")`, `self._compensated = data.get("compensated")`,
     `self._type_II = data.get("type_II")`, `self._r_max = data.get("r_max")`,
     `self._r_peak = data.get("r_peak")`, `self._M_max = data.get("M_max")`,
     `self._M_peak = data.get("M_peak")`, `self._V_end_downflow = data.get("V_end_downflow")`,
     `self._N_end_downflow = data.get("N_end_downflow")`.
  4. In `Datastore/SQL/ObjectFactories/GradientCoupledInstanton.py`'s
     `register()`, add columns following `CompactionFunction`'s exact naming
     convention: `C_peak` (Float64), `C_bar_peak` (Float64), `C_min`
     (Float64), `compensated` (Integer, nullable), `type_II` (Integer,
     nullable), `r_max_Mpc` (Float64), `r_peak_Mpc` (Float64),
     `M_max_SolarMass` (Float64), `M_peak_SolarMass` (Float64),
     `V_end_downflow_PlanckMass4` (Float64), `N_end_downflow` (Float64) — all
     `nullable=True`, matching every other scalar column on this table (a
     failed compute leaves them unset).
  5. In `build()`'s `query = sqla.select(...)`, add the new columns to the
     selected list, and in the "row found" branch (after the existing
     `obj._noise_mom_max = row_data.noise_mom_max` line) rehydrate each with
     the correct unit conversion, mirroring `CompactionFunction`'s
     `_restore_r`/`_restore_M`/`_restore_V` closures:
     `obj._r_max = row_data.r_max_Mpc * units.Mpc if row_data.r_max_Mpc is not None else None`
     (and similarly for `r_peak`, `M_max`/`M_peak` via `units.SolarMass`,
     `V_end_downflow` via `units.PlanckMass**4`); `C_peak`/`C_bar_peak`/
     `C_min`/`N_end_downflow` need no conversion (dimensionless/e-folds);
     `compensated`/`type_II` convert via
     `bool(row_data.compensated) if row_data.compensated is not None else None`.
     **This rehydration must happen unconditionally in `build()`, not gated
     on `do_not_populate`** — these are parent-row scalar columns, exactly
     like `msr_action`, and must be available on a cheap
     `_do_not_populate=True` fetch (this is the whole point of the parity
     requirement: DOE/sweep figures use the cheap fetch tier).
  6. In `store()`, add the new columns to both `inserter(conn, {...})` calls
     (the `obj.failure` branch, where they should be `None`, and the success
     branch, where they should read `obj.C_peak`, `obj.r_max / units.Mpc if obj.r_max is not None else None`,
     etc. — the inverse unit conversion of step 5).
- **Constraints:** follow the conventions checklist; plus: the parity
  columns are parent-row scalars — do not touch the
  `GradientCoupledInstantonValue`/`GradientCoupledInstantonProfile` child
  tables' schemas in this prompt (the `C_bar` profile column was already
  added in U2a; if it turns out U2a's edit to
  `sqla_GradientCoupledInstantonProfileFactory` was left for this prompt
  instead — check the current state of `register()`/`build()`/`store()` for
  that factory before writing any code — then add exactly that one column
  here, following the same `zeta`/`r_ratio`/`C`/`r_phys_Mpc` pattern already
  present).
- **Must NOT:** change `validate()`'s row-count logic (`expected_values`/
  `expected_profile`/`actual_values`/`actual_profile`) — these new columns
  are unconditionally-present parent-row scalars and do not affect child-row
  cascade counting; must NOT change the `full_values_stored is False` raise
  behaviour in `build()` (that guard is P3's job, in a different track); must
  NOT add these columns to `GradientCoupledInstantonValue` or
  `GradientCoupledInstantonProfileValue` (wrong table — they are one-per-
  instanton, not one-per-node or one-per-sample).
- **Acceptance test:** two named unit tests. (a)
  `tests/test_gci_parity_persistence_roundtrip.py` — store a
  `GradientCoupledInstanton` with a full computed result, reload it via
  `build()` with `do_not_populate=False`, and assert every one of the eleven
  new properties round-trips to the pre-store value (within float64
  round-trip tolerance for the unit-converted ones). (b)
  `tests/test_gci_parity_cheap_fetch.py` — reload the same stored instanton
  via `build()` with `_do_not_populate=True`, and assert all eleven
  properties are populated (not `None`) while `.values` and `.profile` are
  both empty lists.
