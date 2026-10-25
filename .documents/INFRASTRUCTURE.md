# INFRASTRUCTURE — how SI uses `datastorekit`, `raypoolkit` and `runregistrykit`

This document explains the non-physics infrastructure: persistence (the
`datastorekit` package's `ShardedPool` and `Datastore` actors, with SI's
factories) and distributed dispatch (the `raypoolkit` package's `RayWorkPool`).
It does not cover the compute targets themselves (`FullInstanton`,
`GradientCoupledInstanton`, …) — see `NUMERICAL_SCHEMES.md` for those — except
where needed to explain how they plug into this machinery.
The run registry, `runregistrykit`, which records a long run and the stores it
makes and is not part of how a pipeline computes, is §13.

---

## 1. Why this layer exists, and whose it is

*Rewritten 2026-10-23 by dk-and-rpk-migration prompt 12; the layer it described is in git at the tag `pre-datastorekit` (`0527480`).*

Every physics compute target (`InflatonTrajectory`, `FullInstanton`,
`SlowRollInstanton`, `CompactionFunction`, `GradientCoupledInstanton`) is
expensive to evaluate and needs to run over a large parameter grid. The
infrastructure layer provides three things on top of that: (a) distributed
execution via Ray, so many grid points compute in parallel across a cluster;
(b) idempotent persistence via a sharded SQLite datastore, so re-running the
pipeline skips anything already computed and validated; (c) a uniform
protocol (`DatastoreObject` + `ObjectFactory`) so every new compute target
gets both of these almost for free by following the same shape.

**Neither (a) nor (b) is SI's code.** Each is a package, pinned to a tag in
`requirements.txt`, installed from it and never editable:

- **`datastorekit` `v0.5.0`** (DatastoreKit): the pool, the per-shard actors,
  the serial broker, the optional profile agent, `DatastoreObject` and
  `SQLAFactoryBase`, the recorded replicated write and the check at open, the
  read-only reader and `read_inventory`, `ShardedPool.copy_store` /
  `move_store` / `closed_store_files` / `delete_store`, and two tools
  (`python -m datastorekit.tools.shard_key_audit`, `python -m
  datastorekit.tools.sharded_store`). What a client gives it is **the client
  contract**, `docs/client-contract.md` at the tag (§1 the pool's constructor,
  §2 the keys of `register()`, §3 the factory hooks, §4 the inventory's
  declarations, §5 the layer's own tables, §6 what it reads from a stored
  object, §7 the other entry points, §9 the changes after `v0.2.0`); its
  `README.md`, "Using it", is the index.
- **`raypoolkit` `v0.3.0`** (RayPoolKit): `RayWorkPool`, and the shared
  rehearsal lock `raypoolkit.rehearsal_lock`. How each is called is its
  `README.md` at the tag, "Using it" and "The rehearsal lock"; the lock's
  contract is its `docs/rehearsal-lock.md` at the tag.

This document points at those two documents and does not copy them. What SI
supplies, and what the package does with it:

| | SI supplies | The package does |
|---|---|---|
| The registry | `config/datastore.py`: `factories` (30 factory instances, table name → factory), `drop_groups` with `tables_to_drop(groups)`, `serial_batch_sizes` | builds a table for each entry from its `register()` (contract §2) and gives the registry to every actor, the reader and the inventory (§1 row 15, §7) |
| The pool's arguments | `config/sharding.py`: the shard-key type `delta_Nstar` and `get_shard_key_store_id`, `replicated_tables`, `sharded_tables`, `read_table_config`, `vectorized_shard_key`; `main.py` builds the pool from these and the CLI | routes each call to its shard, opens or creates the store and checks it (§1) |
| The factories | `Datastore/SQL/ObjectFactories/*.py`: each `register()` and `build()` and, where it defines them, `store`, `validate`, `validate_on_startup`, `revalidate` and `inventory_spec` | calls each hook where §3 says; defaults the rest (§9.5) |
| Replication | each replicated factory forwards `payload["serial"]` and sets `_new_insert` (§4 below) | makes the recorded replicated write, checks the replicas, compares and repairs at open (§6, and the comment above `_replicated_write`) |
| The inventory | `inventory_spec()` on the factories; `tools/inventory_report.py` and `main.py --inventory` | `read_inventory(primary, factories)`: read-only, on a closed store, with no Ray (§4, §7) |
| The work queue | the work items, `task_builder`, any handlers, and the call sites in `main.py` and the plot scripts | `RayWorkPool`: the state machine, the in-flight cap, the progress lines |

SI's old datastore layer, which `datastorekit` replaced, is in git at the tag
`pre-datastorekit` (`0527480`): `Datastore/object.py` and `Datastore/SQL/*.py`
there. SI's copy of `RayWorkPool`, `RayTools/RayWorkPool.py`, went earlier: it
was deleted by prompt 04 (`ef13445`) and is in git at that commit's parent, and
the tag already uses `raypoolkit`. No store written by the old layer is
readable by the current tree (the package refuses it); the tag reads them.

---

## 2. `DatastoreObject` — the base persistence contract

*Rewritten 2026-10-23 by dk-and-rpk-migration prompt 12; the layer it described is in git at the tag `pre-datastorekit` (`0527480`).*

`datastorekit.object.DatastoreObject` (`datastorekit/object.py:5-38`) is the
single base class every persistable domain object inherits:

```python
class DatastoreObject:
    def __init__(self, store_id: Optional[int], *, timestamp: Optional[datetime] = None):
        self._my_id = store_id
        self._timestamp = timestamp

    @property
    def store_id(self) -> int: ...          # raises RuntimeError until it is set
    @property
    def available(self) -> bool: ...        # self._my_id is not None
    @property
    def timestamp(self) -> Optional[datetime]: ...   # read-only; see below
```

`available` is the single canonical test for "has this been persisted".
`_my_id is None` means "not yet in the database" — this is the signal
`RayWorkPool` uses to decide whether a grid point needs computing at all (it
reads `obj.available`: `raypoolkit/RayWorkPool.py:385`). Read `store_id` only
after `available`: it raises on an unstored object. Compute targets add a
second, independent flag, `failure`, for "computation was attempted and
failed" — a failed record is still `available` (it has a `store_id`), which is
what prevents the pipeline from re-attempting a known failing computation on
every subsequent run. See the `available`/`failure` truth table in
`.claude/rules/ray-dispatch.md` / the `compute-targets.md` rule for the four
states this pair distinguishes.

`timestamp` is the row's `timestamp` column as the factory that built the
object passed it, or `None`. The layer stamps the column at insert for a class
whose `register()` declares `"timestamp": True`, and a replicated row carries
the one timestamp of the write on every shard; the package never sets or reads
the attribute on an object (client contract §9.6). It is the package's `v0.3.0`
addition, made at SI's request.

---

## 3. Persistence discipline for dimensionful quantities

Every physics quantity in this codebase is expressed in natural units
(`c = ħ = 1`) and, on top of that, reduced Planck units (`M_p = 1`) — see
`NUMERICAL_SCHEMES.md` §0 for the `UnitsLike`/`Planck_units` concept this
depends on. The compute layer is free to choose whatever concrete `UnitsLike`
instance is convenient for a given run, but the **database must not depend on
that choice**: a value written to disk under one `UnitsLike` instance must
mean the same physical quantity when read back — even in a hypothetical
future session using a *different* concrete `UnitsLike` implementation (e.g.
one fixing `GeV = 1` instead of `PlanckMass = 1`).

This is achieved with a simple convert-on-write, convert-on-read discipline:

- **On `store()`**, divide the in-memory (dimensionful, `UnitsLike`-relative)
  value by the chosen storage unit before writing the plain float to the
  database — e.g. `value / units.PlanckMass` for a mass-dimension-1 quantity,
  `value / units.Mpc` for a length.
- **On `build()`/`_populate()`** (rehydration), multiply the stored float back
  up by the same unit, taken from whatever `UnitsLike` instance the *current*
  session is using — e.g. `stored * units.PlanckMass`.
- **The column or JSON-key name records which unit was chosen** as a suffix,
  so the database is self-documenting: `phi_PlanckMass`, `P1_invPlanckMass`
  (mass⁻¹), `V_end_downflow_PlanckMass4` (mass⁴), `r_max_Mpc` (length),
  `M_max_SolarMass` (mass, but in a human-scale unit rather than
  `PlanckMass`). Dimensionless quantities (`C`, `C̄`, `ζ`, e-fold counts,
  `msr_action`) need no suffix and no conversion at all.

This buys two things: **the compute layer can use different units than the
storage layer** without the database's meaning changing (a run performed in
`GeV`-normalised units and a run performed in `Planck`-normalised units
produce numerically different in-memory floats but write the *same* database
value, once each divides by its own `units.PlanckMass`), and **a value
written under one unit choice keeps its physical meaning even if the project
later switches which `UnitsLike` implementation is the default** — nothing
about the stored *number* changes; only the conversion factor applied on
read does, and that factor is derived from the current `UnitsLike` instance
at read time, not baked into the stored value.

`CosmologyConcepts/DimensionfulQuantity.py`'s generic factory
(`Datastore_SQL_ObjectFactories_DimensionfulQuantity.py`) is the simplest
worked example: a `classname → column_name` dispatch table maps each
dimensionful subclass (`phi_value`, `pi_value`, `inflaton_mass`) to its
storage column, and `store()`/`build()` apply exactly the divide/multiply
pair above using `units.PlanckMass`. The same discipline is applied by hand
(not through this generic factory, since the compute targets hold several
dimensionful fields inline rather than as separate `DimensionfulQuantity`
objects) in `Datastore_SQL_ObjectFactories_FullInstanton.py`,
`..._SlowRollInstanton.py`, `..._CompactionFunction.py`, and
`..._GradientCoupledInstanton.py` — the last of these is the largest worked
example: it converts eleven "parity" scalars (§7 below) across four different
units (`Mpc`, `SolarMass`, `PlanckMass⁴`, and two dimensionless booleans
stored as `Integer`) in a single `store()` call, using the exact suffix
convention above (`r_max_Mpc`, `M_max_SolarMass`, `V_end_downflow_PlanckMass4`)
and the mirror-image multiply in `build()`.

---

## 4. The `ObjectFactory` pattern

*Rewritten 2026-10-23 by dk-and-rpk-migration prompt 12; the layer it described is in git at the tag `pre-datastorekit` (`0527480`).*

Every persisted type has a factory (`Datastore/SQL/ObjectFactories/*.py`)
inheriting `datastorekit.SQL.factory_base.SQLAFactoryBase`
(`datastorekit/SQL/factory_base.py:5-80`); `config/datastore.py` registers
**instances** of them, whose hooks take `self` (contract §9.5). The base's two
abstract hooks are `register` and `build`; it defaults six more — `store`,
`validate` and `validate_on_startup` (which raise `NotImplementedError` where a
factory does not define them), `revalidate`, `owned_serials` and
`inventory_spec`. What each hook is, when the pool calls it and what happens
when it is wrong or absent is the client contract, §3 (with §9.5 for the
defaults); the keys `register()` returns are §2; the inventory's declarations
are §4.

| Hook | Runs on | Purpose (and SI's use) |
|---|---|---|
| `register()` | startup | declares the SQLAlchemy schema (columns, `version`/`timestamp` flags, `validate_on_startup`; for a replicated class the pool must repair or prune, `owner_column` and `validated_column`) |
| `build(payload, conn, ...)` | Datastore actor | **query only** — looks up an existing, validated row; returns an unpopulated object (`store_id=None`) if not found |
| `store(obj, conn, ...)` | Datastore actor | inserts the row(s); sets `obj._my_id`; serialises `obj._values` (or a child value table) |
| `validate(obj, conn, ...)` | Datastore actor | consistency check; sets `validated = TRUE` |
| `validate_on_startup(conn, table, tables, prune)` | actor at open; the pool for a replicated class | reports the unvalidated rows and, under `prune`, deletes them with their child rows (§7) |
| `revalidate(serial, conn, table, tables)` | the pool, at open | recomputes the validated flag after an interrupted validate; only `InflatonTrajectory` declares `validated_column`, so only it defines this |
| `inventory_spec()` | `read_inventory` | how the inventory reads the class: `.claude/rules/datastore-factories.md`, "Every registered factory is covered by the inventory" (22 definitions serve 24 classes; the rest are read through an owner's spec) |

**The critical invariant: `build()` never calls `inserter()`.** It can only
find-or-miss. If it misses, it returns an object with `store_id=None`, which
is exactly the signal `RayWorkPool` needs to decide computation is required.
Violating this (having `build()` insert a placeholder row) makes every object
look `available=True` on first lookup and silently skips all computation —
this is the single most consequential bug class in this layer, called out
explicitly in `.claude/rules/datastore-factories.md`.

Factories that filter on `validated == True` in `build()`'s query ensure a
partially-written or crashed-mid-computation record from a previous run does
not shadow a fresh compute attempt — only a fully-validated row counts as
"done".


### Simple vs. multi-table factories

Simple factories (`tolerance`, `delta_Nstar`, `n_collocation_points`,
`alpha_regularization`) map one Python object to one table row. Compute
targets with a per-sample value list (`InflatonTrajectory`, `FullInstanton`,
`SlowRollInstanton`) serialise `obj._values` into a JSON blob column on the
main row. The two most complex factories, `CompactionFunction` and
`GradientCoupledInstanton`, additionally own separate **child value/sample
tables** (`CompactionFunctionSamples`; `GradientCoupledInstantonValue`,
`GradientCoupledInstantonProfile`) with their own foreign key back to the
parent row — see §7 below for the two extra rules this structure requires.

### Replicated-table factories must honour a supplied `serial`

A **replicated** table's rows are written by the pool as a *recorded*
replicated write (DatastoreKit's client contract, §6, and the comment above
`_replicated_write`, `datastorekit/SQL/ShardedPool.py:3147-3169`;
`.claude/rules/datastore-factories.md` has the steps). The pool commits a
`replication_in_flight` record on the primary, picks a controlling shard and
calls `build()` there; if the answer carries `_new_insert` (or `_updated`) it
calls `build()` on every other shard, passing the controller's serial as
`payload["serial"]` and one timestamp for the write; it checks every replica's
serial against the controller's (`ReplicationMismatch` on a difference), and
only then deletes the record. At every open, before any actor exists, the pool
compares the replicated tables of the shards and repairs or refuses them. Any
factory whose `build()` calls `inserter()` for a replicated table must
therefore forward that serial when present:

```python
if "serial" in payload:
    insert_data["serial"] = payload["serial"]
store_id = inserter(conn, insert_data)
setattr(obj, "_new_insert", True)   # signals ShardedPool to replicate
```

If this is skipped, a replica inserts under its own serial and the pool
raises `ReplicationMismatch`, leaving its record set for the next open to
repair or refuse. (SI's old layer had no such check: there, each shard
assigned its own serial and the same logical object ended up with *different*
serials on different shards. Sharded tables that store a foreign key into a
replicated table, e.g. `FullInstanton.diffusion_serial`, then matched only on
whichever shard shared the "lucky" first-writer's serial — silently breaking
lookups on every other shard. That was observed in a production store: a
`MasslessDecoupledDiffusion` row with serials `1, 6, 11, 16, …` across ten
shards, but every `FullInstanton` row pointing at serial `1`, so 90% of
lookups on other shards returned "not found".)

---

## 5. `Datastore` — the per-shard actor

*Rewritten 2026-10-23 by dk-and-rpk-migration prompt 12; the layer it described is in git at the tag `pre-datastorekit` (`0527480`).*

`datastorekit.SQL.Datastore` defines `@ray.remote class Datastore`
(`datastorekit/SQL/Datastore.py:37`), wrapping a single SQLite connection.
Each actor is given the registry (`factories=`, SI's `config/datastore.py`),
builds the tables from each factory's `register()`, and serves `object_get`,
store, validate and `read_table` by delegating to the relevant factory; it
prunes the unvalidated rows of its sharded classes at open under
`prune_unvalidated`. One `Datastore` actor exists per database shard, named
`shard{key:04d}-store`, beside one `SerialPoolBroker` per store, which leases
serials in the batches `serial_batch_sizes` gives (contract §1 rows 11, 15 and
16; §9.3). It has no `inventory()`: the inventory is read from a closed store
(§6 below).

---

## 6. `ShardedPool` — the coordinator

*Rewritten 2026-10-23 by dk-and-rpk-migration prompt 12; the layer it described is in git at the tag `pre-datastorekit` (`0527480`).*

`datastorekit.SQL.ShardedPool.ShardedPool` is the API every driver script
(`main.py`, `plot_InstantonSolutions.py`) and every compute target actually
talks to. It creates or opens the store, checks it, starts the per-shard
`Datastore` actors, and routes each call to the correct shard(s). `main.py`
builds it with `with ShardedPool(...) as pool`, giving it 15 of the 16
arguments of the contract's §1 (all but `read_only`), from the CLI, `config/sharding.py`
and `config/datastore.py`; opening applies `--drop` (the tables
`tables_to_drop` names) and `--prune-unvalidated`, and closing frees the
actors' names.

### Sharding configuration (`config/sharding.py`)

- **Shard key type:** `delta_Nstar` — each shard holds all data for one
  ΔN★ value.
- **`replicated_tables`** (a list; contract §1 row 5): small domain objects and
  metadata, identical on every shard — `version`, `store_tag`, `tolerance`,
  `efold_value`, `delta_Nstar` itself, `N_init`, `N_final`,
  `n_collocation_points`, `alpha_regularization`, `phi_value`, `pi_value`,
  `inflaton_mass`, `quartic_coupling`, potentials, `MasslessDecoupledDiffusion`,
  `IntegrationSolver`, `InflatonTrajectory`/`Value`, `CosmologicalParams`.
- **`sharded_tables`** (a **dict**, `table_name → shard_key_field_name`,
  never a list — a list causes a silent `KeyError` deep inside
  `ShardedPool`; contract §1 row 6): large per-grid-point compute results,
  partitioned by `delta_Nstar` — `FullInstanton`/`Value`,
  `SlowRollInstanton`/`Value`, `CompactionFunction`/`Samples`,
  `GradientCoupledInstanton`/`Value`/`Profile`.
- **`read_table_config`** (contract §1 row 13): the replicated classes that
  `read_table` serves, each with `tables_arg`.

Every table name appears in **exactly one** of the two collections (the one
exception is `redshift`, registered and in neither, unused:
`[redshift-registered-in-neither-table-list]`) — `delta_Nstar` itself is a
cautionary example: it must be in `replicated_tables` (it's the shard key type)
and must **not** also appear in `sharded_tables`, because
`ShardedPool.read_table()` checks raw membership in `sharded_tables` with no
replicated-first carve-out (`datastorekit/SQL/ShardedPool.py:3695-3731`), so a
stray entry there makes it wrongly reject a fully-replicated table as
"sharded". See `.claude/rules/pool-read-apis.md` for the full incident.

### Key `ShardedPool` methods

| Method | Description |
|---|---|
| `object_get(cls_name, **payload)` | Query-or-insert a single object; returns an `ObjectRef` resolving to it. For a replicated class this is the recorded replicated write |
| `object_get_vectorized(cls_name, shard_key, payload_data=[...])` | Vectorised query for a whole list of objects of a **sharded** class on one shard — the workhorse of Pass 1 dispatch (§10). `shard_key` is the mapping form, `{field: key}`, which every call builds with `config.sharding.vectorized_shard_key` |
| `object_store(obj)` | Persist a fully-populated object; routes to the right shard(s) |
| `object_validate(obj)` | Validate a persisted object |
| `read_table(cls_name, ...)` | Read all rows of a **replicated** table; requires an entry in `read_table_config`; raises for sharded tables (reading from one random shard would silently drop the other shards' data) |

There is no `ShardedPool.inventory()`. The inventory is
`datastorekit.store_inventory.read_inventory(primary, factories)`, read-only on
a closed store with no Ray, which `main.py --inventory` runs before Ray starts
and `tools/inventory_report.py` prints (contract §7). It is a report — counts,
labels and named problems — and **not** a data-fetch API; do not use it to
obtain objects for use in a pipeline. If `read_table()` raises "the read_table
service is not available", the fix is adding an entry to `read_table_config` in
`config/sharding.py` (with the user's go-ahead), not routing around the gap.

---

## 7. Two invariants specific to multi-table factories

`CompactionFunction` and `GradientCoupledInstanton` each own child value
tables with a foreign key back to the parent row but **no `ON DELETE
CASCADE`** (SQLite). Two rules follow directly from this, both loaded at
session start as project rules:

1. **Cascade delete on `validate_on_startup`.** When startup pruning deletes
   unvalidated parent rows, the child rows must be deleted *first* —
   otherwise they are orphaned, and SQLite's serial-number reuse (no
   `AUTOINCREMENT`) means the next parent INSERT can claim a serial that
   still has orphaned children, causing a `UNIQUE constraint failed` error
   on the child table's composite primary key.
2. **`ORDER BY` + monotonicity assertion in `_populate()`.** SQLite gives no
   row-order guarantee for a query without `ORDER BY`. Every `_populate()`
   that reads a multi-row child table must explicitly order by the
   physically meaningful key (`efold_value.N` via a JOIN for instanton value
   tables — not the FK serial, which is not guaranteed to correlate with
   ascending `N`; `source, r_Mpc` for `CompactionFunctionSamples`;
   `node_index` for `GradientCoupledInstantonProfile`) and assert the key is
   strictly non-decreasing after the read, so an ordering bug fails loudly
   (a `RuntimeError`) instead of silently producing a zigzag plot or a wrong
   cumulative integral. This was confirmed as a real, not hypothetical,
   failure mode: a fold-back artefact in a stored `CompactionFunction`'s
   `C̄(r)` curve that vanished when the data was recomputed from scratch,
   with the integration math independently verified correct.

`GradientCoupledInstanton`'s parent row itself is a further illustration of
why "unconditional rehydration" matters for scalars that live *outside* the
child tables: its eleven parity scalars (§3 above, `NUMERICAL_SCHEMES.md`
§3.7) are plain columns on the parent row, not a child table, so they carry
no `ORDER BY`/cascade-delete concern — but they are still rehydrated
unconditionally in `build()`, on every fetch tier including the cheap
`_do_not_populate=True` path (§10), exactly like `msr_action`, so a caller
that only wants the scalar summary never has to pay for deserialising the
full node-by-node profile.

---

## 8. Compute targets: the plain-Python / `@ray.remote`-function split

Every compute target follows a rigid four-part structure (`ComputeTargets/Foo.py`):

```
1. @ray.remote function    — does the numerical work; returns a plain dict
2. FooValue class          — one sample point; plain Python, DatastoreObject
3. Foo class               — the compute target itself; plain Python, NO @ray.remote
4. FooProxy class          — lightweight Ray-object-store reference; plain Python
```

**Why `Foo` must stay a plain class:** `RayWorkPool` accesses compute targets
as ordinary Python objects — `obj.available` (direct attribute read),
`obj.store()` (direct method call on the driver), and `compute()` must
*return* an `ObjectRef` rather than `RayWorkPool` calling `.remote()` on
anything. If `Foo` were decorated `@ray.remote` it would become a
`ray.actor.ActorClass`, not a `type`; direct attribute/method access would
fail, and the factory could no longer construct it with a plain call.

### The `FooProxy` pattern — passing large objects cheaply

Downstream compute targets often need read-only access to an upstream
result (e.g. `FullInstanton`/`GradientCoupledInstanton` need the background
`InflatonTrajectory`). Re-serialising a large object into every Ray task
that needs it would be wasteful, so it is wrapped once:

```python
class FooProxy:
    def __init__(self, model: Foo):
        self._ref = ray.put(model)                # stored once in the object store
        self._store_id = model.store_id if model.available else None

    @property
    def available(self) -> bool:
        return self._store_id is not None

    def get(self) -> Foo:
        return ray.get(self._ref)                 # materialise on demand
```

Ray's serialiser specially tracks embedded `ObjectRef`s for transfer by
reference regardless of nesting depth, so passing the *proxy* itself into a
`@ray.remote` function or a `compute()` call costs nothing extra versus
passing the raw `ObjectRef` — the only practical difference is that a bare
`ObjectRef` argument is auto-dereferenced by Ray before the task body runs,
while a proxy requires the consumer to call `.get()` itself. That one extra
line is the trade that keeps the proxy's Ray plumbing opaque: **no `FooProxy`
exposes its `ObjectRef`** (no `.ref` property), and no caller reaches past a
proxy for its private `_ref` — every consumer holds the proxy and calls
`.get()` internally.

### Populating `_values` after computation

`store()` runs on the driver (no database access); the factory's own
`store()` runs inside a `Datastore` actor (has database access) afterward.
Two approaches populate `obj._values` in between, depending on whether the
sample grid endpoint is known before dispatch:

- **Approach A** (`FullInstanton`, `SlowRollInstanton`,
  `GradientCoupledInstanton`): the integration span is known upfront, so the
  controller pre-mints `efold_value` grid objects before dispatch and
  `store()` zips the returned float arrays directly against that
  pre-existing grid — no extra handoff needed, the default `store_handler`
  suffices.
- **Approach B** (`InflatonTrajectory`): the integration endpoint (`N_end`)
  is not known until the ODE completes, so the remote function builds its
  own grid internally and `store()` only stashes raw float lists in
  `self._raw_sample`. A **custom** `store_handler`
  (`inflaton_trajectory_store_handler` in `main.py`) then mints
  `efold_value` objects from the just-discovered `N_sample` list and
  assembles `obj._values`, deleting `_raw_sample` afterward. This custom
  handler is wired explicitly at the `RayWorkPool` call site — never hidden
  behind a default — so the non-standard behaviour stays visible.

---

## 9. `RayWorkPool` — the distributed work-queue

*Rewritten 2026-10-23 by dk-and-rpk-migration prompt 12; the copy of `RayWorkPool` it once described, `RayTools/RayWorkPool.py`, was deleted by prompt 04 (`ef13445`) and is in git at that commit's parent.*

`RayWorkPool` is `raypoolkit`'s (`from raypoolkit import RayWorkPool`, pinned in
`requirements.txt` at `v0.3.0`). Its documentation is RayPoolKit's `README.md`
at the tag, "Using it": the constructor, the handlers and their defaults, the
sizes, the objects a lookup returns, which handlers a pool needs, and the
printed lines (which are the package's interface). It drives every compute
stage through five states: **lookup → compute → store → persist → validate**.

```python
RayWorkPool(
    pool,                     # the ShardedPool: any object with object_store(obj)
    task_list,                # iterable of work items
    task_builder,             # item -> ObjectRef (the lookup)
    compute_handler=...,      # (obj, **kwargs) -> ObjectRef      [default: obj.compute(**kwargs)]
    store_handler=...,        # (obj, pool) -> None               [default: obj.store()]
    persist_handler=...,      # (obj, pool) -> ObjectRef          [default: pool.object_store(obj)]
    available_handler=None,   # called when obj is already available
    validation_handler=None,  # obj -> ObjectRef
    post_handler=None,        # called after each fully processed item
    label_builder=None,       # obj -> label, passed to the compute handler as label=
    create_batch_size=5,      # the package's defaults: 5, 1 and 200
    process_batch_size=1,     #   (raypoolkit/RayWorkPool.py:26-29)
    max_task_queue=200,       # cap on in-flight tasks
    store_results=False,
    title=None,
)
```

The sizes above are the package's defaults, not SI's: SI's call sites give their
own, for example `create_batch_size=20, process_batch_size=20` for the lookup
pools and `create_batch_size=5, process_batch_size=3` with
`max_task_queue=MAX_INFLIGHT_PIPELINE` (50, `main.py:55-65`) for the compute
pools. A pool with no compute handler passes `compute_handler=None` (12 of SI's
16 call sites); the constructor refuses, with `ValueError`, a store, persist,
validation or label handler given to a pool that has no compute handler, a
`None` store or persist handler on one that has, and a size below 1 (README,
"Which handlers a pool needs").

`run()`'s event loop enqueues lookups (batched by `create_batch_size`),
drains completed `ObjectRef`s via `ray.wait()` (batched by
`process_batch_size`), and advances each item through its state:

```
"lookup":  obj = ray.get(ref)
           obj.available?  -> available_handler / post_handler; done
           else            -> compute_handler(obj); state = "compute"
"compute": store_handler(obj, pool)
           persist_ref = persist_handler(obj, pool); state = "persist"
"persist": validation_handler(obj) if configured; state = "validate", else done
"validate": post_handler; done
```

`max_task_queue` prevents flooding the Ray object store: new compute tasks
are only enqueued while `len(inflight) < max_task_queue`
(`raypoolkit/RayWorkPool.py:290`), so no manual batch sizing is needed
regardless of how many parameter points are queued.

---

## 10. The two-pass dispatch pattern (`main.py`'s `_run_instanton_queue` / `_run_gradient_branch`)

This is the scheduling optimisation used for every instanton compute stage:
it separates a cheap, vectorised existence check from expensive computation,
to minimise round-trips to the `Datastore` actors.

**Pass 1 — vectorised availability check.** Flatten the full parameter grid,
bin items by shard key (`delta_Nstar`), and issue **one**
`pool.object_get_vectorized()` call per shard key (not per grid item) with
`_do_not_populate=True` in the payload — this tells the factory to return a
lightweight sentinel without deserialising the full value list, keeping the
check fast. Round-trips scale as O(num_shard_keys), not O(grid_size). Items
with `obj.available == False` are collected into a compute list.

**Pass 2 — compute queue.** Feed only the missing items into a second
`RayWorkPool`, with a conservative `max_task_queue` (e.g. 20). Because
`RayWorkPool`'s own loop already caps in-flight tasks, no separate manual
batching is required here.

This is deliberately different from the "grouper-batch" approach used in
sibling projects (ChamPBH, SecondaryGWKit), which slices the grid into fixed
batches, queries missing items per batch, and hands the results straight to
`RayWorkPool`. That approach overlaps queries with compute but has two
downsides avoided here: query round-trips scale with grid size rather than
shard-key count, and avoiding object-store flooding requires manually tuning
the batch size (a source of disk-spill incidents in those projects) rather
than relying on `max_task_queue`. The latency advantage of overlapping
queries with compute is negligible in this codebase because individual
queries take microseconds while ODE/collocation solves take seconds to
minutes.

`GradientCoupledInstanton`'s own dispatch (`_run_gradient_branch`) follows
the same two-pass shape, with one addition: it fetches a populated
`FullInstanton` once per *base* grid point `(model, N_init, N_final,
delta_Nstar)` — shared across every `(n_collocation_points,
alpha_regularization)` combination at that base point — and threads a
`FullInstantonProxy` into the constructor purely as an optional
Picard/shooting-loop bootstrap seed (`NUMERICAL_SCHEMES.md` §2.4/§3.3). This
proxy is **not** part of the object's persisted identity: it can only affect
how many Picard/shooting iterations a solve takes, never what it converges
to, so two rows differing only in which (if any) `FullInstanton` was
available to seed them are the same physical object and must resolve to the
same database row.

---

## 11. End-to-end example: one grid point through the pipeline

Tracing `(N_init=5, N_final=3, delta_Nstar=0.1)` for `FullInstanton`:

```
pool.object_get("InflatonTrajectory", phi0, pi0, potential, samples_per_N, atol, rtol)
  -> Factory.build() queries the database
     HIT:  InflatonTrajectory(store_id=42)   [available=True]
     MISS: InflatonTrajectory(store_id=None) [available=False]

MISS path, inside RayWorkPool:
  obj.compute() -> _compute_inflaton_trajectory.remote(...)      [ObjectRef A]
  ray.wait([A]) resolves
  inflaton_trajectory_store_handler(obj, pool):        # custom (Approach B)
    obj.store()  -> resolves A, populates obj._raw_sample
    mint efold_value objects via pool.object_get(...)
    obj._values = [InflatonTrajectoryValue(...), ...]
    del obj._raw_sample
  pool.object_store(obj)    -> Factory.store() inserts rows, sets obj._my_id
  pool.object_validate(obj) -> Factory.validate() sets validated=TRUE

traj_proxy = InflatonTrajectoryProxy(obj)   # ray.put(obj) once

# --- Pass 1 (FullInstanton) ---
delta_Nstar_obj = delta_Nstar(store_id=7, value=0.1)
pool.object_get_vectorized(
    "FullInstanton", delta_Nstar_obj,
    payload_data=[{trajectory: traj_proxy, N_init, N_final, _do_not_populate: True}]
) -> NOT FOUND -> added to compute_list

# --- Pass 2 (FullInstanton) ---
N_total = N_init - N_final + delta_Nstar        # = 2.1
mint N_grid via pool.object_get("efold_value", ...)  # Approach A: pre-minted
full_payload = {trajectory: traj_proxy, N_init, N_final, delta_Nstar, atol, rtol,
                N_sample: efold_array(N_grid)}

RayWorkPool over compute_list:
  obj.compute() -> _compute_full_instanton.remote(traj_proxy, phi_init, phi_final,
                                                    pi_SR_init, N_total, N_sample, atol, rtol)
    # inside the remote function: trajectory = traj_proxy.get() materialises the object
  obj.store()                -> populates obj._values from the returned arrays directly
  pool.object_store(obj)     -> Factory.store() inserts the row, serial-orders JOIN on efold
  pool.object_validate(obj)  -> Factory.validate() checks count, sets validated=TRUE
```

---

## 12. Key design invariants (quick reference)

| Invariant | Where enforced |
|---|---|
| Compute targets are plain Python classes; only remote *functions* get `@ray.remote` | `.claude/rules/ray-dispatch.md` |
| `sharded_tables` is a dict `{name -> shard_key_field}`; never a list | CLAUDE.md |
| Every table name appears in exactly one of `replicated_tables` / `sharded_tables` | `.claude/rules/pool-read-apis.md` |
| `FooProxy` never exposes the raw `ObjectRef`; consumers call `.get()` | `.claude/rules/proxy-pattern.md` |
| Factory `build()` never inserts; only queries | `.claude/rules/datastore-factories.md` |
| There is no `pool.inventory()`; the inventory (`read_inventory`, `main.py --inventory`) is a report, not a data-fetch API | `.claude/rules/pool-read-apis.md` |
| `available` is a `@property`, never a plain method | `.claude/rules/ray-dispatch.md` |
| Child value/sample rows deleted before parent rows in `validate_on_startup` | `.claude/rules/validate-on-startup.md` |
| `_populate()` on a multi-row child table always `ORDER BY`s + asserts monotonicity | `.claude/rules/populate-ordering.md` |
| All physics values in reduced Planck units (Mₚ = 1); divide by the storage unit on write, multiply back on read | CLAUDE.md, `Units/`, §3 above |

---

## 13. The run registry — `runregistrykit`

*Written 2026-10-25 by rrk-adoption prompt 05; the campaign's plan is `.prompts/rrk-adoption/README.md`, its record `.documents/rrk-adoption/verification.md` §1.*

`runregistrykit` `v0.2.0` (RunRegistryKit) is a third package, pinned in
`requirements.txt`, installed from its tag and never editable. It is neither
(a) nor (b) of §1: nothing in the compute pipeline calls it. It **records** a
run; it does not schedule, supervise, restart or lock one. How it is called is
its `README.md` at the tag, "Using it" and "The rules"; the rules SI works under
are `.claude/rules/run-registry.md`. This section points at both and does not
copy them.

**What it records, and where.** `runregistrykit.toml` at the repository root
sets `runs_root = "var/runs"`, `stores_root = "var/datastores"` and
`distributions = ["datastorekit", "raypoolkit"]`, and `.gitignore` ignores
`var/`. For each registered run:
- `var/runs/<run id>/manifest.json`, written before the job starts: the
  arguments, the hash of the program (`main.py`), the store it makes
  (`results`), the git commit and whether the tree was dirty, the installed
  packages (`runregistrykit` and the config's `distributions`, each with its
  tag, commit and whether it is editable), the host, the run's `scope` and the
  text of `heartbeat_means`;
- `status.json` beside it: the state (`running`, `done`, `failed`, `killed` or
  `lost`), the exit code, the pid, the heartbeat, the stage and, at the end, the
  store's fingerprint;
- `stdout.log` and `stderr.log`, copies of what the run wrote.

A store's own record, its **sidecar**, is `var/datastores/<stem>.manifest.json`.
`./venv/bin/python -m runregistrykit list` reads the runs; `store show` reads a
sidecar and the runs that name its store. A `SessionStart` hook in
`.claude/settings.json` runs `list` at the start of every session in this
repository, so that a job's existence does not depend on anyone remembering it.

**How a run is registered, and why `main.py` is not changed.** A registered run
is launched through the wrapper, from the repository root:

```
PYTHONPATH=. ./venv/bin/python RunDrivers/registered_run.py --campaign C --prompt N \
    --register SLUG --purpose "one line" -- <main.py's arguments>
```

The wrapper registers the run, runs `main.py` unchanged (with `runpy`, as
`__main__`), and records how it ended (`done`, `failed` or `killed`), with the
store's fingerprint, whatever `main.py` does. **`main.py` stays launchable by
hand, without it**, and imports nothing of `runregistrykit`; a run launched that
way is recorded nowhere. The plot scripts and `main.py --inventory` are never
registered, and the wrapper refuses `--inventory` and a missing or empty
database before it registers anything (exit 2, one `!! ` line). SI's own
`utilities.installed_package_provenance` is kept for the same reason: the
package's helper would make `main.py` and the plot scripts import
`runregistrykit`. Every manifest's `packages` records the same fields. A wrapper
is a client's code, so it lives here, in `RunDrivers/`, as it does in ChamPBH
and SecondaryGWKit.

**What the heartbeat means.** The wrapper refreshes `status.json`'s heartbeat
when the run writes a line to stdout, at most once every 30 s, and at once when
a line changes the stage (a `** ` banner, or a progress or completion line of
`RayWorkPool`); the line is the `stage`. It means that this driver process wrote
a line, nothing more: the work is in Ray tasks and actors, and a beat cannot say
that any of them is progressing. `RayWorkPool` prints a progress line only after
completed work, so a beat from it means work completed within about five
minutes, and several of `main.py`'s queues print nothing. The registry calls a
run `stale` when its heartbeat is older than 900 s (`list --stale-after`
changes the reader's window, not the package's). **A queue whose items each
take longer than that is therefore shown stale while it works, and the gradient
branch is such a queue**: its solves have run for hours. Stale means go and
look, never kill. The exact text is `HEARTBEAT_MEANS` in
`RunDrivers/registered_run.py`, copied into every manifest.

**The fingerprint, its format and its guard.** A store's fingerprint is made of
what the factories' `inventory_spec()` hooks describe (§4), so what goes into it
is SI's, how it is encoded and digested is DatastoreKit's
(`datastorekit.store_fingerprint`), and when it is taken and where it is
recorded is RunRegistryKit's. SI's part is `config/fingerprint.py`:
`FINGERPRINT_FORMAT` (1), `SPEC_DIGESTS` (the digest of every spec, 24 pairs, 18
distinct) and `fingerprinter`, which `runregistrykit.toml`'s `[stores]` names.
- **The guard** is `tests/test_fingerprint_format_guard.py`. A change to any
  factory's `inventory_spec()`, or to the registry's classes, fails it, naming
  the class. The change is made with a new format number, a new pin in
  `SPEC_DIGESTS`, and a new golden file.
- **The golden file** is `tests/data/store_fingerprint_rrk-adoption-02.json`,
  checked by `tests/test_store_fingerprint_golden.py` against a store built
  through the pool. It was written once and is never overwritten; a later
  format adds a file beside it.

**The sidecar is made by a person.** After a store's first close, a person runs
`./venv/bin/python -m runregistrykit store create PRIMARY --purpose TEXT`.
Nothing in SI's code creates a sidecar, `main.py` included. Until one exists a
run's `status.json` records the fingerprint but says the sidecar was not
written; once it exists the wrapper writes the fingerprint into it at the end of
each run on the store, and `store fingerprint PRIMARY` reads a closed store and
compares it with the recorded one.
