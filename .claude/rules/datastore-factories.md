---
paths:
  - "Datastore/SQL/ObjectFactories/**"
---

# Datastore factory conventions

Loaded when Claude works on files in `Datastore/SQL/ObjectFactories/`. These
conventions apply to all factory classes in this directory.

## CRITICAL: `build()` never INSERTs — `store()` does the INSERT

This is the most important rule in this file. Violating it causes `RayWorkPool`
to see every object as `available=True` on first lookup and skip `compute()`
entirely — nothing ever gets computed.

| Method | Responsibility |
|--------|---------------|
| `build()` | Query only. Return `store_id=None` (available=False) when not found. **Never call `inserter()`**. |
| `store()` | Call `inserter()` to INSERT the main row. Set `obj._my_id = store_id`. Insert value rows. |
| `validate()` | Verify row counts. Call `UPDATE … SET validated=True`. Return bool. |

### `build()` — query only, no INSERT

```python
def build(self, payload, conn, table, inserter, tables, inserters):
    ...
    query = sqla.select(table.c.serial, ...).filter(
        table.c.validated == True,        # only return completed records
        table.c.foo_serial == foo.store_id,
        ...
    )
    row = conn.execute(query).one_or_none()

    if row is None:
        # Not found — return UNPOPULATED object; RayWorkPool will call compute()
        return Foo(store_id=None, ...)    # NO inserter() call here

    # Found — deserialise and return
    obj = Foo(store_id=row.serial, ...)
    if not payload.get("_do_not_populate"):
        self._populate(obj, row, tables, conn)
    setattr(obj, "_deserialized", True)
    return obj
```

`build()` must filter `validated == True`. This ensures that a partially-written
or failed record from a previous run does not shadow a new compute attempt. Only
a fully-validated record counts as "already done".

### `store()` — INSERT main row, then value rows

```python
def store(self, obj, conn, table, inserter, tables, inserters):
    if obj.failure:
        store_id = inserter(conn, {"N_end": None, ..., "validated": False})
        obj._my_id = store_id
        return obj

    raw = obj._raw_sample
    store_id = inserter(conn, {"N_end": obj._N_end, ..., "validated": False})
    obj._my_id = store_id          # makes obj.available == True from this point

    # insert value rows ...
    return obj
```

### `validate()` — set validated=True after checking counts

```python
def validate(self, obj, conn, table, tables):
    if not obj.available:
        raise RuntimeError("...")
    validated = True if obj.failure else (actual_count == expected_count)
    conn.execute(sqla.update(table).where(...).values(validated=validated))
    return validated
```

## Factory `build()` returns a plain Python instance

```python
# Correct — plain constructor
obj = InflatonTrajectory(store_id=store_id, phi0=phi0, ...)

# NEVER — private Ray internals
obj = InflatonTrajectory.__ray_actor_class__(store_id=store_id, ...)
```

The returned object must be accessible with normal Python attribute syntax
immediately after `build()` returns — no `.remote()`, no `ray.get()`. This
is required because `ShardedPool.object_get()` returns the result of
`factory.build()` directly to the caller.

## Factory `store()` reads `_raw_sample`

When a compute target's `store()` has been called by `RayWorkPool`, the object
carries a `_raw_sample` dict of plain lists. The factory's `store()` method
(called later by `ShardedPool.object_store()`) reads this to insert value rows:

```python
def store(self, obj, conn, table, inserter, tables, inserters):
    raw = obj._raw_sample          # set by Foo.store() on the driver
    N_vals  = raw["N_sample"]      # list[float]
    phi_vals = raw["phi"]          # list[float]
    ...
    # Look up or create efold_value records, insert FooValue rows
    efold_table    = tables["efold"]
    efold_inserter = inserters["efold"]
    for N, phi in zip(N_vals, phi_vals):
        # find or create the efold_value for this N
        ...
```

The factory's `store()` has database access; `Foo.store()` on the driver does
not. Keep this separation clean.

## Foreign key naming — dual tolerance references

When a table references the `tolerance` table twice (for `atol` and `rtol`),
SQLAlchemy requires distinct constraint names to avoid a collision:

```python
sqla.Column(
    "atol_serial", sqla.Integer,
    sqla.ForeignKey("tolerance.serial", name="fk_<tablename>_atol"),
    index=True, nullable=False,
),
sqla.Column(
    "rtol_serial", sqla.Integer,
    sqla.ForeignKey("tolerance.serial", name="fk_<tablename>_rtol"),
    index=True, nullable=False,
),
```

## `potential_serial` — no foreign key

Potentials (`QuadraticPotential`, `QuarticPotential`) live in separate tables.
The `potential_serial` column on compute target tables is a plain indexed
`Integer` with no `ForeignKey(...)`. This avoids a cross-table FK constraint
that would be incorrect when either potential type could be referenced:

```python
sqla.Column("potential_serial", sqla.Integer, index=True, nullable=False),
# TODO: replace with FK to a unified potential_registry table
```

## `validate_on_startup` pattern

Factories that set `"validate_on_startup": True` in `register()` must implement:

```python
def validate_on_startup(self, conn, table, tables, prune_unvalidated):
    rows = conn.execute(
        sqla.select(table.c.serial).filter(table.c.validated == False)
    ).fetchall()
    if prune_unvalidated and rows:
        conn.execute(sqla.delete(table).where(
            table.c.serial.in_([r.serial for r in rows])
        ))
        return [f"Pruned {len(rows)} unvalidated records from {table.name}"]
    if rows:
        return [f"Found {len(rows)} unvalidated records in {table.name} (not pruned)"]
    return []
```

## `_do_not_populate` flag

When `payload.get("_do_not_populate")` is `True`, `build()` should return the
object with its `store_id` set but `_values` empty, even if the record exists
and `validated = True`. This flag is used by `RayWorkPool` for the initial
existence-check pass, where deserialising the full trajectory would be wasteful.

## Idempotency requirement

`build()` must be idempotent: calling it twice with the same payload must return
objects with the same `store_id`. The existence query must use fuzzy float
comparison for any `FLOAT(64)` column used as a lookup key:

```python
from config.defaults import DEFAULT_FLOAT_PRECISION

# For non-zero values:
sqla.func.abs((table.c.N_init - N_init_val) / N_init_val) < DEFAULT_FLOAT_PRECISION

# For values that may be zero (add a guard):
if abs(N_init_val) == 0:
    sqla.func.abs(table.c.N_init - N_init_val) < DEFAULT_FLOAT_PRECISION
else:
    sqla.func.abs((table.c.N_init - N_init_val) / N_init_val) < DEFAULT_FLOAT_PRECISION
```
