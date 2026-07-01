# Prompt 1 — `y_value` / `y_array` shared concept objects

## Context

`GradientCoupledInstanton` and `GradientCoupledCompactionFunction` (upcoming
compute targets implementing the onion model) both operate on a radial
shell coordinate `y ∈ [0, 1]`, with `y = 0` the outer edge of the overdense
region and `y = 1` the core. Multiple instantons — and, downstream, multiple
compaction-function evaluations of the same instanton at different times —
will want to share an identical `y`-sample grid. As with the existing
`efold_value`/`efold_array` pattern (`InflationConcepts/efold_value.py`,
`Datastore/SQL/ObjectFactories/efold.py`), persisting `y_value` objects in a
shared database table lets shared sample points be identified exactly by
`store_id`, rather than relying on floating-point equality — this matters in
particular for the identity-keyed extraction cache planned for
`GradientCoupledCompactionFunction` in a later prompt.

This prompt introduces `y_value`/`y_array` and their SQL persistence layer,
mirroring `efold_value`/`efold_array` as closely as the differing semantics
allow. No compute target in this prompt consumes them yet — this is
infrastructure only.

## Task

### 1. `InflationConcepts/y_value.py`

Create `y_value(DatastoreObject)` and `y_array`, modelled directly on
`InflationConcepts/efold_value.py`:

- `y_value.__init__(self, store_id, y, timestamp=None)`, storing `self.y = y`.
  `store_id` required (raise `ValueError` if `None`), same as `efold_value`.
- `__float__` returns `float(self.y)`.
- `__eq__` compares `store_id` (raise `NotImplementedError` for
  non-`y_value` comparisons), same as `efold_value`.
- `__lt__` orders ascending by `y` (0 = outer edge → 1 = core). Note in the
  docstring that this is a **geometric** ordering (outer-to-inner), not a
  temporal one — don't reuse `efold_value`'s "earlier times are smaller"
  language, since it doesn't apply here.
- `__hash__` returns `("y_value", self.store_id).__hash__()`.
- Add a validation guard not present in `efold_value`: raise `ValueError` if
  `y` is constructed outside `[0, 1]` (with some small numerical tolerance,
  reuse whatever epsilon convention is already used elsewhere in the
  codebase for this kind of bound check — check
  `CosmologyConcepts_DimensionlessQuantity.py` for precedent before
  inventing a new one). `y` is a physically bounded coordinate in this
  model, unlike `N`, so this guard has no analogue in `efold_value` and is a
  genuine addition, not an oversight if it looks different.
- `y_array`: copy `efold_array`'s interface exactly — ascending-sorted,
  deduplicated container over `y_value`, with `__iter__`, `__getitem__`,
  `__len__`, `__eq__`/`__ne__`, `__add__`, `as_float_list()`, `.min`, `.max`.
- `check_ysample(A, B)`: direct analogue of `check_Nsample`, raising
  `RuntimeError` if two `y_array` instances (or objects carrying a
  `y_sample` attribute) don't represent the same grid.

### 2. `Datastore/SQL/ObjectFactories/y.py`

Create `sqla_y_factory(SQLAFactoryBase)`, modelled directly on
`Datastore/SQL/ObjectFactories/efold.py`'s `sqla_efold_factory`:

- `register()`: single `Float(64)` column `y`, indexed. No version, with
  timestamp (matches `efold`'s registration exactly).
- `build(payload, conn, table, inserter, tables, inserters)`: look up an
  existing row within tolerance, insert if none found — same
  absolute/relative-tolerance branching as `sqla_efold_factory.build()`
  (`fabs(y) == 0` uses absolute tolerance, otherwise relative). Add new
  constants `DEFAULT_Y_PRECISION` / `DEFAULT_Y_RELATIVE_PRECISION` to
  `config/defaults.py` alongside the existing `DEFAULT_EFOLD_PRECISION`
  constants — don't reuse the e-fold constants, since `y ∈ [0,1]` has a very
  different natural scale to `N`, which can range over tens of e-folds.
- `read_table()` and `inventory()`: direct analogues of the `efold`
  versions, ordering by `y` ascending. Leave the same `# TODO (Prompt N):`
  style comment for the eventual join to
  `GradientCoupledInstantonValue`/`GradientCoupledCompactionFunctionSamples`
  once those tables exist, matching the existing `# TODO (Prompt 4):`
  comment in `efold.py`.

### 3. Wire into `Datastore/SQL/Datastore.py`

- Import `sqla_y_factory` alongside the other factory imports.
- Add `"y_value": sqla_y_factory()` to the `_factories` dict, next to
  `"efold_value": sqla_efold_factory()`.

### 4. Wire into the remaining three registration points

New `DatastoreObject` models need to be registered in four places, not just
the `_factories` dict above. Confirmed for `y_value`:

- **`ClientPool.py`**: add `"y_value"` to the `_default_serial_batch_size`
  table, mirroring whatever batch size `"efold_value"` already uses there
  (locate the existing `efold_value` entry rather than guessing a value).
- **`config/sharding.py`**: add `"y_value"` to `replicated_tables` (`y`
  sample points are shared infrastructure across shards, exactly like
  `efold_value` — not sharded by `delta_Nstar`). Do **not** add it to
  `sharded_tables`.
- **`config/sharding.py`**: add `"y_value": {"tables_arg": False}` to
  `read_table_config`, mirroring the existing `"efold_value": {"tables_arg":
  False}` entry — `y_value` is infrastructure and should support
  `read_table()`, same reasoning as `efold_value`.

### 5. Tests

Add unit tests mirroring whatever existing test coverage exists for
`efold_value`/`efold_array` (locate it before writing new tests — don't
assume a location). At minimum:

- `y_value` ordering, equality, hashing.
- `y_array` dedup/sort/`as_float_list`/`min`/`max`.
- Out-of-range construction raises.
- Round-trip through the SQL factory: build the same `y` twice, confirm the
  second call returns the same `store_id` (within tolerance) rather than
  inserting a duplicate row; build two `y` values far enough apart that they
  should NOT collide, confirm distinct `store_id`s.

## Acceptance criteria

- [ ] `InflationConcepts/y_value.py` created with `y_value`, `y_array`,
      `check_ysample`, matching the interface of `efold_value.py` except
      where explicitly noted above.
- [ ] Out-of-range `y` (outside `[0,1]`, beyond tolerance) raises
      `ValueError` at construction.
- [ ] `Datastore/SQL/ObjectFactories/y.py` created with `sqla_y_factory`,
      matching `sqla_efold_factory`'s structure.
- [ ] `DEFAULT_Y_PRECISION` / `DEFAULT_Y_RELATIVE_PRECISION` added to
      `config/defaults.py`.
- [ ] `"y_value"` registered in `Datastore/SQL/Datastore.py`'s `_factories`
      dict.
- [ ] `"y_value"` registered in `ClientPool.py`'s `_default_serial_batch_size`
      table.
- [ ] `"y_value"` registered in `config/sharding.py`'s `replicated_tables`
      list (not `sharded_tables`).
- [ ] `"y_value"` registered in `config/sharding.py`'s `read_table_config`
      dict with `{"tables_arg": False}`.
- [ ] Unit tests pass, including the round-trip/dedup test against the SQL
      factory.
- [ ] No other files touched — this prompt is infrastructure only, no
      compute target changes.

## Commit

Single commit, message along the lines of:
`Add shared y_value/y_array concept objects and SQL persistence`
