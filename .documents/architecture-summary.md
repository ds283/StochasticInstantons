# StochasticInstanton — Architecture Summary

## Overview

StochasticInstanton computes stochastic instantons in inflationary scalar-field
models. The pipeline integrates background inflaton trajectories and then solves
for Euclidean (MSR) instanton saddle-points over a grid of physical parameters.
All heavy computation is distributed via [Ray](https://ray.io); results are
persisted into a sharded SQLite datastore with full idempotency (re-running the
pipeline skips work that is already stored and validated).

---

## Repository layout

*Rewritten 2026-10-23 by dk-and-rpk-migration prompt 12; the layer it described is in git at the tag `pre-datastorekit` (`0527480`).*

*Extended 2026-10-25 by rrk-adoption prompt 05 (the run registry's entries); what the registry records is `INFRASTRUCTURE.md` §13.*

```
main.py                        — orchestrator / CLI entry-point
RunDrivers/
  registered_run.py            — the wrapper that registers a main.py run with the run registry and
                                 runs it unchanged; main.py stays launchable without it
runregistrykit.toml            — the run registry's configuration: runs_root, stores_root,
                                 distributions and the store fingerprinter
.claude/settings.json          — the SessionStart hook that runs `runregistrykit list` (discovery)
var/                           — ignored by git: var/runs/ (a run's records), var/datastores/ (the
                                 stores of registered runs and their sidecars)
config/
  argument_parser.py           — CLI + YAML argument parsing
  defaults.py                  — string/float precision constants
  model_list.py                — builds the list of inflationary models
  sharding.py                  — the ShardedPool's table lists, shard key, read_table_config
  datastore.py                 — what SI hands to datastorekit: the factory registry, --drop groups, serial batch sizes
  fingerprint.py               — what SI hands to runregistrykit: the store fingerprint's format, the
                                 pin of every inventory spec's digest, and the fingerprinter
ComputeTargets/
  InflatonTrajectory.py        — background ODE integration
  FullInstanton.py             — full MSR instanton BVP
  SlowRollInstanton.py         — slow-roll-approximated instanton BVP
(packages, pinned to tags in requirements.txt; not in this repository)
  raypoolkit                   — RayWorkPool, the distributed work queue
  datastorekit                 — ShardedPool, the Datastore actors, SerialPoolBroker, ProfileAgent,
                                 DatastoreObject, SQLAFactoryBase, read_inventory, two tools
  runregistrykit               — the run registry: begin/finish, list, end, the store sidecar and
                                 fingerprint (INFRASTRUCTURE.md §13)
Datastore/                     — SI's factories only (both __init__.py are empty)
  SQL/
    ObjectFactories/           — one factory per persisted type, subclassing SQLAFactoryBase
      version.py, store_tag.py, tolerance.py
      DimensionlessQuantity.py, DimensionfulQuantity.py
      integration_metadata.py, redshift.py
      InflatonTrajectory.py, FullInstanton.py, SlowRollInstanton.py, CompactionFunction.py,
      GradientCoupledInstanton.py, … (22 modules)
tools/
  inventory_report.py          — the report main.py --inventory prints
  compare_stores.py            — compares two stores by value
CosmologyConcepts/
  DimensionlessQuantity.py     — base for dimensionless physics values
  DimensionfulQuantity.py      — base for dimensional physics values
  Potentials/
    AbstractPotential.py       — potential/Hubble/diffusion interface
    QuadraticPotential.py      — V(φ) = ½m²φ²
    QuarticPotential.py        — V(φ) = λφ⁴
InflationConcepts/
  delta_Nstar.py               — shard key: excess transition e-fold count
  efold_value.py               — single e-fold sample coordinate N
  N_init.py, N_final.py        — grid endpoint values
  inflaton_mass.py             — inflaton mass (dimensional)
  phi_value.py, pi_value.py    — field value and velocity (dimensional)
  quartic_coupling.py          — λ coupling constant (dimensionless)
  DiffusionModel.py            — abstract + concrete diffusion matrix D_{ij}
MetadataConcepts/
  tolerance.py                 — ODE tolerance token
  store_tag.py                 — string label for grouping
  version.py                   — version string + timestamp
Quadrature/
  integration_metadata.py      — ODE solver metadata record
  supervisors/base.py          — supervisor base class
Units/
  base.py                      — UnitsLike abstract base class
  Planck_units.py              — concrete implementation (Mₚ = 1)
```

---

## Units convention

All physics is done in **reduced Planck units** with `Mₚ = 1` (`8πG = 1`).
Dimensionful quantities stored in the database record their value divided by the
appropriate unit, e.g. `phi_value.value = phi / units.PlanckMass`.

### The `UnitsLike` pattern

`Units/base.py` defines an abstract base class `UnitsLike` with abstract
properties for every unit the code needs:

```python
class UnitsLike(ABC):
    @property
    @abstractmethod
    def PlanckMass(self): ...

    @property
    @abstractmethod
    def Metre(self): ...

    # ... Kilometre, Kilogram, Second, Kelvin, eV, c, Mpc
```

The concrete implementation `Planck_units` sets all constants relative to
reduced Planck units and is instantiated once in `main.py`. Passing `units`
through to factory helpers keeps all unit conversions explicit and
swappable — no global state.

---

## Domain objects

### CosmologyConcepts

| Class | Description |
|---|---|
| `DimensionlessQuantity` | Base for all dimensionless values; carries `store_id` and `float` value |
| `DimensionfulQuantity` | Base for all dimensional values; value stored divided by unit |

### InflationConcepts

| Class | Description |
|---|---|
| `delta_Nstar` | Excess number of e-folds at transition (dimensionless); **shard key** |
| `efold_value` | A single e-fold coordinate N used as a sample point |
| `N_init` | Initial e-fold count for instanton grid |
| `N_final` | Final e-fold count for instanton grid |
| `inflaton_mass` | Inflaton mass m (dimensional) |
| `phi_value` | Field value φ at the initial condition (dimensional) |
| `pi_value` | Field velocity π = dφ/dN at the initial condition (dimensional) |
| `quartic_coupling` | Quartic self-coupling λ in V(φ) = λφ⁴ (dimensionless) |

### Potentials

`AbstractPotential` defines the interface that all inflationary models must
satisfy:

```
H²(φ, π)       — Hubble parameter squared
ε(φ, π)        — slow-roll parameter
dV/dφ(φ)       — potential gradient
d²V/dφ²(φ)    — potential Hessian
D_matrix(φ, π) — 2×2 diffusion tensor (via AbstractDiffusionModel)
```

Concrete implementations: `QuadraticPotential` and `QuarticPotential`.
`AbstractDiffusionModel` (and its default `MasslessDecoupledDiffusion`) provide
the diffusion matrix D_{ij}(φ, π) needed for the stochastic equations.

### MetadataConcepts

| Class | Purpose |
|---|---|
| `tolerance` | Tokenises a float tolerance to `log10_tol`; fuzzy-matches on read |
| `store_tag` | String label attached to a group of stored objects |
| `version` | Version label + creation timestamp; written once per database |

---

## Datastore layer

*Rewritten 2026-10-23 by dk-and-rpk-migration prompt 12; the layer it described is in git at the tag `pre-datastorekit` (`0527480`).*

The datastore layer is the `datastorekit` package (`v0.5.0`, pinned in
`requirements.txt`, never editable); SI has no copy of it. What a client gives
it is DatastoreKit's client contract, `docs/client-contract.md` at the tag; its
`README.md`, "Using it", is the index. `.documents/INFRASTRUCTURE.md` §1 lists
what SI supplies and what the package does; this section is the short form. SI's
old layer is in git at the tag `pre-datastorekit` (`0527480`).

### DatastoreObject base class (`datastorekit.object`)

Every persistable domain object inherits from `datastorekit.object.DatastoreObject`
(`datastorekit/object.py:5-38`), which carries `_my_id`, the read-only
properties `store_id` (it raises `RuntimeError` until the id is set),
`available` (`_my_id is not None`) and `timestamp` (the row's timestamp as the
factory passed it, or `None`), and takes `store_id` and the keyword-only
`timestamp` in its constructor.

`available` is the single canonical test for whether an object has been
persisted. `RayWorkPool` reads this property directly
(`raypoolkit/RayWorkPool.py:385`).

### ObjectFactory pattern (`datastorekit.SQL.factory_base.SQLAFactoryBase`)

Each persisted type has a factory in `Datastore/SQL/ObjectFactories/`
inheriting `SQLAFactoryBase`; `config/datastore.py` registers an instance of
each (30 registered classes). The base's abstract hooks are `register()` and
`build()`; it defaults `store()`, `validate()`, `validate_on_startup()`,
`revalidate()`, `owned_serials()` and `inventory_spec()` (client contract, §3
and §9.5):

| Method | Runs on | Purpose |
|---|---|---|
| `register()` | startup | declares the SQLAlchemy schema (columns, version/timestamp flags, `validate_on_startup`; `owner_column` and `validated_column` where the pool repairs or prunes a replicated class) |
| `build(payload, conn, ...)` | Datastore actor | **query only** — looks up existing row; returns unpopulated object if not found |
| `store(obj, conn, ...)` | Datastore actor | inserts new row(s); sets `obj._my_id`; serialises `obj._values` to JSON |
| `validate(obj, conn, ...)` | Datastore actor | consistency check; sets `validated = TRUE` in database |
| `validate_on_startup(conn, table, tables, prune)` | actor at open; the pool for a replicated class | reports unvalidated rows; deletes them, with their child rows, under `prune` |
| `revalidate`, `owned_serials` | the pool | `InflatonTrajectory` defines `revalidate`; no SI factory defines `owned_serials` |
| `inventory_spec()` | `read_inventory` | how the inventory reads the class (22 definitions, 24 classes) |

The critical invariant is that `build()` **never calls `inserter()`**. It can
only find or miss. If it misses, it returns an object with `store_id = None`,
which signals to `RayWorkPool` that computation is needed.

### Datastore actor (`datastorekit.SQL.Datastore`)

A `@ray.remote class Datastore` per shard wraps a SQLite connection. It is
given SI's registry (`config/datastore.py`'s `factories`), builds the tables
from each factory's `register()`, and serves `object_get`, store, validate and
`read_table` by finding the relevant factory and delegating to it. It has no
`inventory()`. Beside the shard actors the package runs one `SerialPoolBroker`
(serial numbers, leased in the batches of `serial_batch_sizes`) and, if asked,
a `ProfileAgent` (`--profile-db`).

### ShardedPool (`datastorekit.SQL.ShardedPool`)

The primary API seen by `main.py` and all compute targets. It coordinates
multiple Datastore actors (one per shard), routing calls to the right shard
based on the shard key. `main.py` builds it from the CLI and from
`config/sharding.py` and `config/datastore.py` (the contract's §1 lists the
arguments).

**Sharding configuration** (`config/sharding.py`):

- **Shard key type:** `delta_Nstar` — each shard holds all data for one ΔN★
  value.
- **Replicated tables:** metadata and small domain objects are identical across
  all shards (`version`, `store_tag`, `tolerance`, `efold_value`, `delta_Nstar`,
  `N_init`, `N_final`, `phi_value`, `pi_value`, `inflaton_mass`,
  `quartic_coupling`, `InflatonTrajectory`, `InflatonTrajectoryValue`,
  potentials, etc.).
- **Sharded tables:** large compute results are partitioned by `delta_Nstar`
  (`FullInstanton`, `FullInstantonValue`, `SlowRollInstanton`,
  `SlowRollInstantonValue`, `CompactionFunction`, `CompactionFunctionSamples`,
  `GradientCoupledInstanton` and its two child tables).

Every table name appears in **exactly one** of the two collections; a table in
both (or neither) causes routing failures. (`redshift` is registered and in
neither, and nothing uses it: `[redshift-registered-in-neither-table-list]`.)

**Key ShardedPool methods:**

| Method | Description |
|---|---|
| `object_get(cls_name, **payload)` | Query or insert a single object; returns `ObjectRef` resolving to the object (a recorded replicated write for a replicated class) |
| `object_get_vectorized(cls_name, shard_key, payload_data=[...])` | Vectorised query for a whole list of objects of a sharded class on one shard; used in Pass 1; the shard key is the mapping `{field: key}` (`config.sharding.vectorized_shard_key`) |
| `object_store(obj)` | Persist a fully populated object; routes to the appropriate shard |
| `object_validate(obj)` | Validate a persisted object |
| `read_table(cls_name, ...)` | Read all rows of a replicated table; requires entry in `read_table_config` |

There is no `ShardedPool.inventory()`; see "Inventory" below.

---

## Compute targets

Each compute target lives in `ComputeTargets/` and follows a rigid four-part
structure (enforced by the `.claude/rules/ray-dispatch.md` project rule).

### Four-part structure

```
1. @ray.remote function   — does the numerical work; returns a plain dict
2. FooValue class         — stores output at one sample point (plain Python)
3. Foo class              — the compute target (plain Python, NO @ray.remote)
4. FooProxy class         — lightweight Ray object-store reference
```

**Why `Foo` must be a plain class:** `RayWorkPool` accesses compute targets as
ordinary Python objects — `obj.available`, `obj.store()`, `obj.compute()`. If
`Foo` were decorated `@ray.remote` it would become a `ray.actor.ActorClass`,
breaking direct attribute access and driver-side method calls.

### InflatonTrajectory

Integrates the stochastic background ODE from an initial condition `(φ₀, π₀)`
forward in e-fold time until the end of inflation. The integration endpoint
`N_end` is not known in advance, so the sample grid is built internally by the
remote function.

- **Remote function:** `_compute_inflaton_trajectory(phi0, pi0, potential,
  samples_per_N, atol, rtol)` — returns `{N_end, N_sample[], phi[], pi[],
  failure}`.
- **store():** stashes raw float lists in `self._raw_sample`; a custom
  `store_handler` in `main.py` then mints `efold_value` objects from the pool
  and assembles `self._values`.
- **InflatonTrajectoryValue:** one sample point `(N: efold_value, phi, pi)`.

### FullInstanton

Solves the full MSR instanton boundary-value problem over a fixed interval
`[0, N_total]` for the field quartet `(φ₁, φ₂, P₁, P₂)`. The algorithm uses
an inner Picard iteration (adjoint backward pass + forward field pass) nested
inside an outer Newton loop that enforces the terminal boundary condition
`φ₁(N_total) = φ_final`.

The sample grid `N_sample` is pre-minted before dispatch (Approach A in
`ray-dispatch.md`), so `store()` can populate `self._values` directly without a
raw-sample handoff.

- **Remote function:** `_compute_full_instanton(trajectory_proxy, phi_init,
  phi_final, pi_SR_init, N_total, N_sample[], atol, rtol)` — returns
  `{phi1[], phi2[], P1[], P2[], msr_action, failure}`.
- **FullInstantonValue:** one sample point `(N: efold_value, phi1, phi2, P1,
  P2)`.

### SlowRollInstanton

Same BVP structure as `FullInstanton` but enforces the slow-roll approximation
for the background fields. Shares the same Approach A grid pattern.

---

## The FooProxy pattern

Computing instantons requires passing trajectory data into Ray remote functions.
A full `InflatonTrajectory` object with thousands of sample points is expensive
to serialise repeatedly. The proxy pattern solves this:

```python
class InflatonTrajectoryProxy:
    def __init__(self, model: InflatonTrajectory):
        self._ref = ray.put(model)                          # store once
        self._store_id = model.store_id if model.available else None

    @property
    def available(self) -> bool:
        return self._store_id is not None

    def get(self) -> InflatonTrajectory:
        return ray.get(self._ref)                           # materialise on demand
```

The proxy is passed by value into any `@ray.remote` function or `compute()`
call. Ray's serialiser detects the embedded `ObjectRef` and transfers it by
reference — the trajectory data is stored exactly once in the Ray object store
and shared across all tasks that need it. Consumers call `proxy.get()` inside
the remote function to materialise the trajectory; they never reach past the
proxy to touch `proxy._ref` directly.

---

## RayWorkPool

*Rewritten 2026-10-23 by dk-and-rpk-migration prompt 12; the copy of `RayWorkPool` it once described, `RayTools/RayWorkPool.py`, was deleted by prompt 04 (`ef13445`) and is in git at that commit's parent.*

`RayWorkPool` is the `raypoolkit` package's (`from raypoolkit import
RayWorkPool`, pinned in `requirements.txt` at `v0.3.0`, never editable); SI has
no copy of it. Its documentation is RayPoolKit's `README.md` at the tag, "Using
it". It provides the main distributed work-queue abstraction and manages the
full lifecycle of a set of compute targets through the stages: **lookup →
compute → store → persist → validate**.

### Constructor

```python
RayWorkPool(
    pool,                         # the ShardedPool: any object with object_store(obj)
    task_list,                    # iterable of work items
    task_builder,                 # callable: item → ObjectRef (lookup)
    compute_handler=...,          # callable: (obj, **kwargs) → ObjectRef   [default: obj.compute(**kwargs)]
    store_handler=...,            # callable: (obj, pool) → None            [default: obj.store()]
    persist_handler=...,          # callable: (obj, pool) → ObjectRef       [default: pool.object_store(obj)]
    available_handler=None,       # called when obj already available
    validation_handler=None,      # callable: obj → ObjectRef
    post_handler=None,            # called after each fully processed item
    label_builder=None,           # callable: obj → label, passed to the compute handler as label=
    create_batch_size=5,          # the package's defaults: 5, 1 and 200
    process_batch_size=1,         #   (raypoolkit/RayWorkPool.py:26-29)
    max_task_queue=200,           # cap on in-flight tasks
    store_results=False,          # if True, collect results in self.results
    title=None,                   # display name for progress reporting
)
```

The sizes are the package's defaults. SI's call sites give their own: for
example `create_batch_size=20, process_batch_size=20` for the lookup pools, and
`create_batch_size=5, process_batch_size=3` with `max_task_queue=50`
(`MAX_INFLIGHT_PIPELINE`, `main.py:55-65`) for the instanton compute pools.

### Event loop (`run()`)

`RayWorkPool.run()` drives a state machine over all in-flight `ObjectRef`s:

```
for each task in task_list (batched by create_batch_size):
    if len(inflight) < max_task_queue:
        enqueue: ref = task_builder(descriptor)
        inflight[ref] = ("lookup", descriptor)

for each completed ref (via ray.wait, batched by process_batch_size):
    match state:
        "lookup":
            obj = ray.get(ref)
            if obj.available → available_handler or post_handler; done
            else           → compute_handler(obj); state = "compute"
        "compute":
            store_handler(obj, pool)
            persist_ref = persist_handler(obj, pool)
            state = "persist"
        "persist":
            if validation_handler:
                validation_handler(obj); state = "validate"
            else:
                post_handler; done
        "validate":
            post_handler; done
```

`max_task_queue` prevents flooding the Ray object store: new tasks are only
enqueued when the number of in-flight tasks drops below the cap
(`raypoolkit/RayWorkPool.py:290`).

### Default handlers

The default handlers delegate to the standard object protocol:
- `compute_handler`: calls `obj.compute(**kwargs)` (with `label=` when a
  `label_builder` gives one), returns the `ObjectRef`
- `store_handler`: calls `obj.store()` (resolves the compute `ObjectRef`)
- `persist_handler`: calls `pool.object_store(obj)`, returns persist `ObjectRef`

Custom handlers (e.g. `inflaton_trajectory_store_handler` in `main.py`) replace
only the steps that need non-default behaviour. A pool with no compute handler
(a lookup-only pool; 12 of SI's 16 call sites) passes `compute_handler=None`.

---

## main.py — the orchestrator

`main.py` is the single CLI entry point. It parses arguments, initialises Ray
and the ShardedPool, and then runs either the compute pipeline or an inventory
report. A run that is to be recorded in the run registry is launched through
`RunDrivers/registered_run.py`, which runs `main.py` unchanged; `main.py` stays
launchable by hand without it (`INFRASTRUCTURE.md` §13).

### Top-level flow

*Rewritten 2026-10-23 by dk-and-rpk-migration prompt 12; the layer it described is in git at the tag `pre-datastorekit` (`0527480`).*

```
parse_args()
  → if args.inventory:                     # before Ray starts, before any pool opens
        inventory = read_inventory(args.database, factories)
        print(format_inventory_report(inventory, args.database, verbose=args.show_all))
        exit
  → drop_tables = tables_to_drop(args.drop)    # refused here (exit 2) if it would leave references
  → ray.init(address=args.ray_address)
  → ShardedPool(...)  using config/sharding.py and config/datastore.py
  → execute(pool, units)
```

### Pipeline stages (`execute`, then `run_all_pipelines`)

**Stage 0 — register shared objects**

`execute()` calls `pool.object_get(...)` to ensure tolerances, initial
conditions (`phi_value`, `pi_value`), and the parameter grid arrays
(`N_init_array`, `N_final_array`, `delta_Nstar_array`) all exist in the
database. These are plain upsert calls; if the objects already exist, their
`store_id`s are returned immediately.

**Stage 1 — InflatonTrajectory**

One `RayWorkPool` runs over all `(model, phi0, pi0, potential)` combinations.
The `task_builder` is `pool.object_get("InflatonTrajectory", **payload)`.

Because the integration endpoint `N_end` is not known until the ODE completes,
a custom `store_handler` is used:

```python
def inflaton_trajectory_store_handler(obj, pool):
    obj.store()                          # resolves Ray future → _raw_sample
    if obj.failure:
        return
    raw = obj._raw_sample
    efold_objects = ray.get(
        pool.object_get("efold_value",
                        payload_data=[{"N": n} for n in raw["N_sample"]])
    )
    obj._values = [
        InflatonTrajectoryValue(store_id=None, N=N_obj, phi=phi, pi=pi)
        for N_obj, phi, pi in zip(efold_objects, raw["phi"], raw["pi"])
    ]
    del obj._raw_sample
```

After Stage 1, each trajectory is wrapped in an `InflatonTrajectoryProxy` and
stored in the `traj_proxies` list.

**Stages 2 & 3 — FullInstanton / SlowRollInstanton**

Both instanton stages use the **two-pass dispatch pattern** via
`_run_instanton_queue()`.

### Two-pass dispatch pattern (`_run_instanton_queue`)

This is the core scheduling optimisation. It separates existence checks
(cheap, vectorised) from computation (expensive, serial) to minimise database
round-trips.

**Pass 1 — vectorised existence check**

```
Bin grid items by shard key (delta_Nstar)
For each shard key:
    refs = pool.object_get_vectorized(
        cls_name, delta_Nstar_obj,
        payload_data=[key_fields(item) | {_do_not_populate: True}]
    )
    → for each obj: if obj.available → skip; else → add to compute_list
```

`_do_not_populate=True` tells the factory to return a lightweight sentinel
without deserialising the full `_values` JSON, keeping Pass 1 fast.

Round-trips to Datastore actors are **O(num_shard_keys)** rather than
O(grid_size).

**Pass 2 — compute missing items**

```
For each item in compute_list:
    Mint efold_value grid: pool.object_get("efold_value", ...)
    full_payload = key_fields + N_sample grid
    task_builder = pool.object_get(cls_name, **full_payload)

RayWorkPool(
    task_list=compute_list,
    task_builder=task_builder,
    max_task_queue=MAX_INFLIGHT_PIPELINE,  # = 50 (main.py:65)
)
```

The `max_task_queue` cap (`MAX_INFLIGHT_PIPELINE`, 50, which counts the
in-flight items of every stage, not only the instanton BVPs; `main.py:55-65`)
keeps the number of in-flight tasks bounded, preventing the Ray object store
from being flooded.

### Inventory

*Rewritten 2026-10-23 by dk-and-rpk-migration prompt 12; the layer it described is in git at the tag `pre-datastorekit` (`0527480`).*

`main.py --inventory` reads the closed store read-only, before Ray starts and
before any pool opens, with `datastorekit.store_inventory.read_inventory(primary,
factories)` (DatastoreKit's client contract, §7): it changes nothing, refuses
`--drop`, and a store that is absent, or that the package refuses, is refused
with a `RuntimeError`. `tools/inventory_report.py`'s
`format_inventory_report(inventory, db_name, verbose=False)` renders the
`StoreInventory` it returns, and `--show-all` is `verbose`. The inventory is
read over each factory's `inventory_spec()` (§4 of the contract; see
`.claude/rules/datastore-factories.md`): 24 classes, each registered class
covered by a spec or read through one.

The inventory is a report — records, counts and named problems — and **not** a
data-fetch API. There is no `pool.inventory()`.

---

## End-to-end object lifecycle

This traces one grid point `(N_init=5, N_final=3, delta_Nstar=0.1)` through the
full pipeline.

### Stage 1: InflatonTrajectory

```
pool.object_get("InflatonTrajectory", phi0, pi0, potential, samples_per_N, atol, rtol)
  → Factory.build() queries database
    → HIT: returns InflatonTrajectory(store_id=42)          [available=True]
    → MISS: returns InflatonTrajectory(store_id=None)       [available=False]

MISS path in RayWorkPool:
  obj.compute() → _compute_inflaton_trajectory.remote(...)  [ObjectRef A]
  ray.wait([A]) resolves
  inflaton_trajectory_store_handler(obj, pool):
    obj.store()     → resolves ObjectRef A, populates obj._raw_sample
    mint efold_values via pool.object_get(...)
    obj._values = [InflatonTrajectoryValue(...), ...]
    del obj._raw_sample
  pool.object_store(obj) → Factory.store() inserts rows, sets obj._my_id=42
  pool.object_validate(obj) → Factory.validate() sets validated=TRUE

→ traj_proxy = InflatonTrajectoryProxy(obj)   [ray.put(obj) → ObjectRef B]
```

### Stage 2: FullInstanton (Pass 1)

```
delta_Nstar_obj = delta_Nstar(store_id=7, value=0.1)

pool.object_get_vectorized(
    "FullInstanton", delta_Nstar_obj,
    payload_data=[{trajectory: traj_proxy, N_init: ..., N_final: ..., _do_not_populate: True}]
)
→ Factory.build() queries: NOT FOUND → FullInstanton(store_id=None)
→ added to compute_list
```

### Stage 2: FullInstanton (Pass 2)

```
N_total = N_init - N_final + delta_Nstar  (= 5 - 3 + 0.1 = 2.1)
Mint N_grid via pool.object_get("efold_value", ...)
full_payload = {trajectory: traj_proxy, N_init, N_final, delta_Nstar, atol, rtol,
                N_sample: efold_array(N_grid)}

pool.object_get("FullInstanton", **full_payload)
  → Factory.build() queries: MISS → FullInstanton(store_id=None)

RayWorkPool:
  obj.compute() → _compute_full_instanton.remote(
      traj_proxy,          # proxy: ray sees embedded ObjectRef B
      phi_init, phi_final, pi_SR_init,
      N_total=2.1, N_sample=[...], atol, rtol
  )
  [Inside remote function: trajectory = traj_proxy.get() materialises obj]

  obj.store()  → ray.get(compute_ref), populates obj._values with FullInstantonValue objects
  pool.object_store(obj)    → Factory.store() inserts row with JSON values blob
  pool.object_validate(obj) → Factory.validate() checks count, sets validated=TRUE
```

---

## Key design invariants

| Invariant | Where enforced |
|---|---|
| Compute targets are plain Python classes; only remote *functions* get `@ray.remote` | `.claude/rules/ray-dispatch.md`, CLAUDE.md |
| `sharded_tables` is a dict `{name → shard_key_field}`; never a list | CLAUDE.md |
| Every table name appears in exactly one of `replicated_tables` / `sharded_tables` | `.claude/rules/pool-read-apis.md`, CLAUDE.md |
| `FooProxy` never exposes the raw `ObjectRef`; consumers call `.get()` | `.claude/rules/proxy-pattern.md` |
| Factory `build()` never inserts; only queries | ObjectFactory protocol |
| There is no `pool.inventory()`; the inventory (`read_inventory`, `main.py --inventory`) is a report, not a data-fetch API | `.claude/rules/pool-read-apis.md` |
| `available` is a `@property`, never a plain method | `.claude/rules/ray-dispatch.md` |
| All physics values in reduced Planck units (Mₚ = 1) | CLAUDE.md, Units/ |
