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

| Method       | Responsibility                                                                                                     |
|--------------|--------------------------------------------------------------------------------------------------------------------|
| `build()`    | Query only. Return `store_id=None` (available=False) when not found. **Never call `inserter()`**.                  |
| `store()`    | Call `inserter()` to INSERT the main row. Set `obj._my_id = store_id`. Write `trajectory_json` from `obj._values`. |
| `validate()` | Verify row counts. Call `UPDATE … SET validated=True`. Return bool.                                                |

Note: `RayWorkPool` has three distinct handler slots — `store_handler` (calls
`obj.store()` on the compute target to resolve the Ray future and populate
`obj._values`), then `persist_handler` (calls `pool.object_store(obj)`, which
in turn calls this factory's `store()` method). The factory's `store()` is
invoked only from `persist_handler`, after `obj._values` is fully populated.

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

    # obj._values is fully populated before this method is called.
    # Read store_ids directly — no efold_value upsert needed here.
    json_rows = [
        {"N_serial": v.N.store_id, "phi": v.phi, ...}
        for v in obj._values
    ]
    store_id = inserter(conn, {
        "N_end": obj._N_end,
        ...,
        "trajectory_json": json.dumps(json_rows),
        "validated": False,
    })
    obj._my_id = store_id          # makes obj.available == True from this point
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

## Factory `store()` reads from `obj._values`

By the time the factory's `store()` is called by `ShardedPool.object_store()`,
`obj._values` has already been fully populated with typed `FooValue` objects
whose `N` fields are `efold_value` instances with valid `store_id`s. This is
guaranteed by the `store_handler` step in `RayWorkPool`, which runs before
`persist_handler` (which calls `pool.object_store(obj)`).

The factory reads `store_id`s directly from `obj._values` — no upsert or
tolerance-match query against the `efold_value` table is needed:

```python
def store(self, obj, conn, table, inserter, tables, inserters):
    if obj.failure:
        store_id = inserter(conn, {"N_end": None, ..., "validated": False})
        obj._my_id = store_id
        return obj

    json_rows = [
        {"N_serial": v.N.store_id, "phi": v.phi, ...}
        for v in obj._values
    ]
    store_id = inserter(conn, {
        "N_end": obj._N_end,
        ...,
        "trajectory_json": json.dumps(json_rows),
        "validated": False,
    })
    obj._my_id = store_id
    return obj
```

Do not read `_raw_sample` in the factory. If `_raw_sample` is present on the
object when the factory runs, the store_handler has not completed correctly.

### How `obj._values` gets populated — two approaches

**Approach A (`FullInstanton`, `SlowRollInstanton`):** The sample grid is
pre-minted on the controller before dispatch (because `N_total` is known in
advance). `obj.store()` constructs `_values` directly from the returned float
arrays and the pre-existing `efold_array`. The default `store_handler` is used.

**Approach B (`InflatonTrajectory`):** The grid endpoint (`N_end`) is not known
until the ODE completes. `obj.store()` leaves a temporary `_raw_sample` dict.
A custom `store_handler` in `main.py` mints `efold_value` objects via the pool,
assembles `_values`, and deletes `_raw_sample` before the factory runs.

In both cases the factory sees a fully-populated `obj._values` and uses the
same `v.N.store_id` pattern above.

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

## `potential_serial` — no foreign key, disambiguated by `potential_type`

Potentials (`QuadraticPotential`, `QuarticPotential`) live in separate tables.
The `potential_serial` column on `InflatonTrajectory` is a plain indexed
`Integer` with no `ForeignKey(...)`. This avoids a cross-table FK constraint
that would be incorrect when either potential type could be referenced.
Because two different potential tables can independently produce rows with
the same `serial`, `potential_serial` alone is ambiguous; a sibling
`potential_type` column carries the `type_id` (from
`CosmologyConcepts/Potentials/model_ids.py`) needed to resolve it:

```python
sqla.Column("potential_serial", sqla.Integer, index=True, nullable=False),
sqla.Column("potential_type", sqla.Integer, index=True, nullable=False),
```

`CosmologyConcepts/Potentials/registry.py` maps `type_id → PotentialTypeInfo`
(class, table name, factory instance). `sqla_InflatonTrajectory_factory.read_table()`
dispatches through this registry — `info.factory.load_by_serial(conn, tables, serial, units=units)`
— instead of trying each potential table in turn. Adding a new potential type
means giving it a `type_id`, a `type_id` column on its own factory, a
`load_by_serial()` method on its factory, and one entry in
`POTENTIAL_REGISTRY` — no changes to `InflatonTrajectory` itself.

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

## Replicated-table factories MUST honour a supplied `serial`

### How `ShardedPool` replicates a new row

When `pool.object_get()` is called for a replicated table, `ShardedPool`:

1. Picks a random "controlling" shard and calls `factory.build()` on it.
2. If `build()` set `_new_insert` on the returned object, the pool calls
   `factory.build()` on every **other** shard, passing `serial=<store_id>` in
   the kwargs so they insert with the same serial.

Step 2 only works if the factory honours that supplied serial. If `inserter()` is
called without forwarding `payload["serial"]`, each shard uses its own
autoincrement sequence and the same logical object ends up with **different
serials in different shards**.

### The consequence of ignoring the serial

Sharded tables (e.g. `FullInstanton`) store the serial of a replicated object
(e.g. `diffusion_serial`) as a plain integer. When `FullInstanton.build()` later
looks up records on shard N, it compares against `dm.store_id` — which came from
whichever shard the pool queried for the diffusion model. If replicated serials
are inconsistent, only the one shard whose serial happens to match will return
results; all others silently miss every record. This was confirmed by
`SMSR_scaling_values.sqlite`, where `MasslessDecoupledDiffusion` had serials
1, 6, 11, 16, 21, 26, 32, 36, 41, 46 across ten shards, but every
`FullInstanton` row stored `diffusion_serial=1` (from the lucky first-writer
shard), making 90 % of instanton lookups return unavailable.

### Required pattern for replicated-table `build()`

Any `build()` that calls `inserter()` (i.e. any factory for a replicated
parameter/metadata table) **must** forward the serial when one is provided:

```python
if row_data is None:
    insert_data = {"value": value, ...}   # whatever columns this table has
    if "serial" in payload:               # replication supplies this
        insert_data["serial"] = payload["serial"]
    store_id = inserter(conn, insert_data)
    obj = Foo(store_id=store_id, ...)
    setattr(obj, "_new_insert", True)     # signals ShardedPool to replicate
else:
    obj = Foo(store_id=row_data.serial, ...)
    setattr(obj, "_deserialized", True)
```

Both `_new_insert` (on insert) and `_deserialized` (on existing-row read) must
be set so `ShardedPool` can tell whether to trigger replication.

### Checklist for every replicated-table factory

- [ ] `build()` checks `if "serial" in payload` before calling `inserter()`.
- [ ] `inserter()` is called with `{"serial": payload["serial"], ...}` when the
      key is present.
- [ ] `setattr(obj, "_new_insert", True)` is set on a fresh insert.
- [ ] `setattr(obj, "_deserialized", True)` is set on an existing-row read.
