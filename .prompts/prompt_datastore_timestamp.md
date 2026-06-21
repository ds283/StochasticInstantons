# Prompt: surface row-creation timestamps via `DatastoreObject`

## Context

`Datastore/SQL/Datastore.py` already writes a `timestamp` column
(`datetime.now()` at insert time) for any table whose factory's
`register()` returns `"timestamp": True`. Currently opted in:

- CompactionFunction
- FullInstanton
- SlowRollInstanton
- InflatonTrajectory
- QuadraticPotential
- delta_Nstar
- efold
- tolerance
- DimensionfulQuantity
- DimensionlessQuantity

Not opted in, but should be: **CosmologicalParams**.

The column is written but never read back. Each factory's `build()`
selects an explicit column list and does not include `table.c.timestamp`,
and no `DatastoreObject` subclass stores a timestamp. We want a
`timestamp` property parallel to the existing `store_id` property,
implemented once in the base class and inherited everywhere, rather
than reimplemented per-object.

## Goal

1. `DatastoreObject.__init__` accepts an optional `timestamp` argument
   (`Optional[datetime]`, default `None`) and stores it as `self._timestamp`.
2. Add a `timestamp` property to `DatastoreObject`:
   - Returns the stored `datetime` if present.
   - Returns `None` if this object's table doesn't use timestamps, or if
     the object hasn't been persisted yet (`store_id` not yet known) —
     do **not** raise, unlike `store_id`. Calling code (e.g. the plotting
     script) should be able to do `obj.timestamp` unconditionally and
     branch on `None`.
3. Add a small shared helper in `Datastore/SQL/ObjectFactories/base.py`
   (e.g. `SQLAFactoryBase._select_timestamp_column(table)` or similar)
   that factories can use to conditionally add `table.c.timestamp` to a
   `sqla.select(...)` only when the table actually has that column —
   use `hasattr(table.c, "timestamp")` or equivalent, so factories for
   non-timestamped tables don't need special-casing.
4. For each of the 10 already-timestamped factories listed above:
   - Add `table.c.timestamp` to the existing `build()` query's `select()`.
   - Pass the retrieved value through to the constructed object as the
     `timestamp=` argument, which flows up to `DatastoreObject.__init__`
     via each class's own `__init__`/`super().__init__()` call.
   - Every intermediate `__init__` in the chain (e.g. `FullInstanton.__init__`)
     needs an optional `timestamp: Optional[datetime] = None` parameter
     threaded through to `DatastoreObject.__init__`.
5. Add `"timestamp": True` to `CosmologicalParams`'s factory `register()`
   dict, and wire its `build()`/constructor the same way as the others.
   This is a schema addition for that table — confirm whether existing
   `CosmologicalParams` rows need a migration/backfill strategy, or
   whether it's acceptable for pre-existing rows to read back `NULL`/`None`.
6. **Freshly-computed-this-session objects** (the `row_data is None`
   branch in each factory's `build()`, before `.store()` has run): leave
   `timestamp=None` at construction. Do not attempt to backfill it
   immediately after insert — the property should just be `None` until
   the object is re-read from the database in a later session. State
   this explicitly as expected behaviour in a docstring/comment so it
   isn't "fixed" later as a bug.

## Explicit non-goals

- Do not add a plot-provenance footer in this pass — that's separate,
  unimplemented, and out of scope here.
- Do not add timestamps to `store_tag` or any other currently
  non-timestamped table beyond `CosmologicalParams`.
- Do not change the `version`/`stepping` handling already present in
  the insert path.

## Acceptance criteria

- [ ] `DatastoreObject` has a `timestamp` property; calling it on an
      object built before this change (i.e. `timestamp=None` passed
      implicitly) returns `None` without raising.
- [ ] For each of the 11 tables (10 existing + CosmologicalParams),
      round-tripping an object — store it, then re-fetch it via the
      factory's normal `object_get`-style path in a fresh process —
      yields a `.timestamp` that is a `datetime` close to when the row
      was inserted (not `None`).
- [ ] For a table that does *not* use timestamps (e.g. `store_tag`,
      `CosmologicalParams` *before* this change is applied to it),
      `.timestamp` returns `None` rather than raising or erroring.
- [ ] A freshly-computed object that hasn't been persisted yet
      (`store_id` unavailable) has `.timestamp is None`.
- [ ] Existing tests/behaviour around `store_id`/`available` are
      unaffected — this is purely additive.
- [ ] `CosmologicalParams` objects newly written after this change
      carry a timestamp; pre-existing rows are handled gracefully
      (document whatever choice is made — NULL-tolerant read is fine,
      no migration required unless you judge it necessary).

## Suggested approach / order of work

1. `Datastore/object.py`: extend `DatastoreObject.__init__` and add the
   `timestamp` property.
2. `Datastore/SQL/ObjectFactories/base.py`: add the shared
   timestamp-column-select helper.
3. Update the 10 existing timestamped factories one at a time, each as
   its own commit: add the column to the query, thread `timestamp`
   through the relevant `ComputeTargets`/`CosmologyConcepts`/`InflationConcepts`
   object constructor, confirm `build()` passes it through on both the
   "row found" and "row not found" branches (`None` on the latter).
4. Add `"timestamp": True` to `CosmologicalParams`'s `register()` and
   repeat the same wiring for that one table.
5. Quick smoke test: store and re-fetch one object of each of the 11
   types, print `.timestamp`, confirm non-`None` and sane.

Please work through this list incrementally, committing after each
object type is converted, rather than editing all 11 factories in one
pass — these files are mechanically similar but not identical (some
have multiple FK-derived constructor args, `CompactionFunction` has
two child value tables), so each deserves its own check.
