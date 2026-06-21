# Prompt: Fix non-deterministic sample/value ordering on datastore read-back

# (CompactionFunction, FullInstanton, SlowRollInstanton)

## Root cause (confirmed)

Three `_populate()` methods read child/value tables from SQLite with no
`ORDER BY`, relying on undefined row order:

1. `Datastore_SQL_ObjectFactories_CompactionFunction.py::_populate()` reads
   `CompactionFunctionSamples` filtered by `parent_serial`, no ordering.
2. `Datastore_SQL_ObjectFactories_FullInstanton.py::_populate()` reads
   `FullInstantonValue` filtered by `instanton_serial`, no ordering — and
   separately joins to `efold_value` per-row via N_serial.
3. `Datastore_SQL_ObjectFactories_SlowRollInstanton.py::_populate()` — same
   pattern as (2).

SQLite gives no row-order guarantee for a query without `ORDER BY`. Each of
these result lists is consumed downstream as an implicitly-ordered array
(plotted as a line, fed into cumulative integrals, zipped against an
r-grid/N-grid) — e.g. `plot_zeta_and_compaction()` and
`plot_instanton_fields()` in `plot_InstantonSolutions.py`, and
`_compute_instanton_path()` in `ComputeTargets_CompactionFunction.py`
(though note: the latter does its own `argsort` on `r`, so it's self-healing
for *r*-ordering specifically — but `FullInstanton`/`SlowRollInstanton`
values feeding it, and any other direct consumer of `._values`, are not
protected, since they're ordered by `N`, which nothing currently sorts on
read).

This was diagnosed via `CompactionFunction(id=17483)`: a fold-back / zigzag
artefact in a plotted C̄(r) curve that vanished when the same data was
recomputed from scratch (bypassing the DB read-back), with the integration
math itself independently verified correct.

## Task

Apply the following three fixes (diffs below are illustrative — match exact
current file state, since line numbers may have drifted):

### 1. `Datastore_SQL_ObjectFactories_CompactionFunction.py`

In `_populate()`, change:

```python
rows = conn.execute(
    sqla.select(
        samples_table.c.source,
        samples_table.c.r_Mpc,
        samples_table.c.zeta,
        samples_table.c.C,
        samples_table.c.C_bar,
    ).filter(samples_table.c.parent_serial == obj.store_id)
).fetchall()
```

to:

```python
rows = conn.execute(
    sqla.select(
        samples_table.c.source,
        samples_table.c.r_Mpc,
        samples_table.c.zeta,
        samples_table.c.C,
        samples_table.c.C_bar,
    )
    .filter(samples_table.c.parent_serial == obj.store_id)
    .order_by(samples_table.c.source, samples_table.c.r_Mpc)
).fetchall()
```

### 2. `Datastore_SQL_ObjectFactories_FullInstanton.py`

In `_populate()`, replace the unordered value-table read plus per-row N+1
efold lookup:

```python
rows = conn.execute(
    sqla.select(
        value_table.c.N_serial,
        value_table.c.fields_json,
    ).filter(value_table.c.instanton_serial == obj.store_id)
).fetchall()

for r in rows:
    efold_row = conn.execute(
        sqla.select(efold_table.c.serial, efold_table.c.N).filter(
            efold_table.c.serial == r.N_serial
        )
    ).one()
    N_obj = efold_value(store_id=efold_row.serial, N=efold_row.N)
    data = json.loads(r.fields_json)
```

with a single joined, ordered query:

```python
rows = conn.execute(
    sqla.select(
        value_table.c.N_serial,
        value_table.c.fields_json,
        efold_table.c.N,
    )
    .select_from(value_table.join(efold_table, value_table.c.N_serial == efold_table.c.serial))
    .filter(value_table.c.instanton_serial == obj.store_id)
    .order_by(efold_table.c.N)
).fetchall()

for r in rows:
    N_obj = efold_value(store_id=r.N_serial, N=r.N)
    data = json.loads(r.fields_json)
```

(Ordering by the actual e-fold value `N`, not by `N_serial`, since the FK
serial is not guaranteed to correlate with ascending `N`. This also removes
an N+1 query pattern as a side benefit — confirm this doesn't break anything
relying on `efold_value.store_id` being independently fetched; it's the same
serial either way.)

### 3. `Datastore_SQL_ObjectFactories_SlowRollInstanton.py`

Apply the identical fix as (2), adapted to `SlowRollInstantonValue` /
`obj._values` (phi/P1 fields rather than phi1/phi2/P1/P2).

## Additional checks

4. **Audit for the same pattern elsewhere.** Grep the
   `Datastore_SQL_ObjectFactories_*.py` files for any other
   `sqla.select(...).filter(...)` (no `.order_by`) feeding a list that's
   later consumed as an ordered sequence (anything zipped against N, r, or
   e-fold, or plotted as a line). `InflatonTrajectory`,
   `delta_Nstar`, `efold` factories are worth a specific look since
   `InflatonTrajectory` backs the noiseless background ODE referenced
   elsewhere as a single source of truth. List anything else found, even if
   deferred.

5. **Add regression checks.** After each `_populate()` builds its values
   list, assert the ordering key (`r` for CompactionFunction samples, `N`
   for instanton values) is strictly non-decreasing, and raise/log clearly
   if violated — so this class of bug fails loudly rather than silently
   producing bad plots.

6. **Verify.** Re-render plots for `CompactionFunction(id=17483)` (and its
   parent `FullInstanton`/`SlowRollInstanton` records) and confirm:
    - `ζ(r)`, `C(r)`, `C̄(r)` curves are now single smooth monotonic lines
      with no fold-back.
    - `plot_instanton_fields()` output (φ₁, φ₂, P₁, P₂ vs N) likewise shows
      no discontinuous jumps from scrambled N-ordering.

7. Do not modify the integration logic in `ComputeTargets_CompactionFunction.py`
   — independently verified correct. This pass is read-path/ordering only.

### 4. Write a rules file to prevent this happening

Please generate a rules file that requires future `_populate()` instances
built for the `ComputeTargets` pattern to have a defined sort order. If this
sort order cannot be determined from the write-out order in the `store` phase,
please STOP and confirm the intended order from a human user.

## Acceptance criteria

- All three `_populate()` methods have explicit `ORDER BY` (or join+order)
  on the physically meaningful ordering key.
- N+1 query pattern in FullInstanton/SlowRollInstanton removed as part of
  the join (not required, but natural given the fix — don't skip if it adds
  risk; flag instead).
- Regression assertions added for monotonicity on load, for all three.
- Audit of other factories completed and findings reported, even if no
  further fixes are made in this pass.
- Re-rendered plots for id=17483 and its parent instantons show smooth,
  monotonic curves with no scrambled-order artefacts.
- Commit message(s) clearly state this is a deterministic-read-order fix,
  not a numerical/physics fix.
