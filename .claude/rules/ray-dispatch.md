# Ray dispatch pattern for compute targets

This rule has no `paths:` frontmatter, so it loads at session start alongside
`CLAUDE.md`. It provides the detailed specification for the pattern summarised
in `CLAUDE.md`. Read this before creating or editing any compute target class.

## The correct three-part structure

Every compute target in `ComputeTargets/` follows this layout, in this order:

```
1. @ray.remote FUNCTION  — does the numerical work, returns a plain dict
2. FooValue class        — stores output at one sample point (plain Python)
3. Foo class             — the compute target (plain Python, NO @ray.remote)
4. FooProxy class        — lightweight reference (plain Python, NO @ray.remote)
```

### Part 1: the `@ray.remote` function

```python
@ray.remote
def _compute_foo(param1: float, param2: float, ...) -> dict:
    """Does the work. Takes plain, serialisable arguments. Returns a dict."""
    ...
    return {"result_key": value, ..., "failure": False}
```

- Decorated with `@ray.remote` — this is the ONLY thing in a compute target
  file that gets this decorator
- Takes only plain, Ray-serialisable arguments (floats, dicts, `ObjectRef`s)
- Never takes a compute target *object* as an argument — extract its parameters
  and pass those instead
- Returns a plain `dict` with a `"failure"` key

### Part 2: `FooValue`

Plain `DatastoreObject` subclass. No `@ray.remote`. Normal `@property` access.

### Part 3: `Foo` — the compute target class

```python
class Foo(DatastoreObject):          # plain class — NO @ray.remote

    def __init__(self, store_id, param1, ...):
        DatastoreObject.__init__(self, store_id)
        self._param1 = param1
        self._compute_ref = None     # holds ObjectRef while work is in flight

    @property                        # @property — NOT a plain method
    def available(self) -> bool:
        return self._my_id is not None

    @property
    def failure(self) -> bool:
        return getattr(self, "_failure", False)

    def compute(self, label=None) -> ObjectRef:
        """Must return an ObjectRef. RayWorkPool waits on this."""
        if self._compute_ref is not None:
            raise RuntimeError("compute() already in progress")
        self._compute_ref = _compute_foo.remote(self._param1, ...)
        return self._compute_ref

    def store(self):
        """Called on the DRIVER by RayWorkPool after compute() resolves.
        Must NOT make Ray calls or database calls."""
        data = ray.get(self._compute_ref)
        self._compute_ref = None
        if data.get("failure", False):
            self._failure = True
            return
        self._failure = False
        # Save raw lists for the factory's store() to serialise:
        self._raw_sample = {"N_sample": data["N_sample"], ...}
```

### Part 4: `FooProxy`

```python
class FooProxy:                      # plain class — NO @ray.remote

    def __init__(self, model: Foo):
        # model is a plain Python instance, NOT a Ray actor handle
        self._ref = ray.put(model)
        self._store_id = model.store_id if model.available else None

    @property                        # normal @property
    def available(self) -> bool:
        return self._store_id is not None

    def get(self) -> Foo:
        return ray.get(self._ref)
```

See `.claude/rules/proxy-pattern.md` for how `FooProxy` instances must be
consumed — pass the proxy itself, never expose or reach past it for the raw
`ObjectRef`.

## Why `RayWorkPool` requires plain classes

`RayTools/RayWorkPool.py` accesses compute targets as plain Python objects:

- **Line 354:** `if obj.available:` — direct attribute read, no `.remote()`
- **Line 436:** `obj.store()` — direct method call on the driver
- **Line 393:** `compute_task = compute_handler(obj)` — `compute()` must
  return an `ObjectRef`; `RayWorkPool` never calls `.remote()` on it

If `Foo` is decorated `@ray.remote`, it becomes a `ray.actor.ActorClass`, not a
`type`. Direct attribute access fails. `obj.store()` fails. The factory cannot
call `Foo(...)` — it would need `Foo.remote(...)` which dispatches to a worker.

## What is absolutely forbidden

```python
@ray.remote
class Foo(DatastoreObject):          # NEVER — breaks RayWorkPool

    def available(self):             # NEVER — must be @property
        return ...
```

```python
# NEVER — private Ray internals, breaks between Ray versions
obj = Foo.__ray_actor_class__(store_id=1, ...)
```

If you find yourself needing `__ray_actor_class__`, the class has been
incorrectly decorated with `@ray.remote`. Remove the decorator.

## Populating `_values` after computation — two approaches

`store()` runs on the driver (no database access). The factory's `store()`
runs inside a Datastore actor (has database access). Before the factory runs,
`obj._values` must be fully populated with typed `FooValue` objects whose `N`
fields are `efold_value` instances with valid `store_id`s. This is the same
state the object would be in after `factory._populate()` on a database load.

There are two approaches depending on whether the sample grid endpoint is known
before dispatch.

### Approach A — pre-minted grid (used by `FullInstanton`, `SlowRollInstanton`)

The integration span `[0, N_total]` is known on the controller before the
remote function is dispatched. The controller builds the grid, mints
`efold_value` objects via `pool.object_get("efold_value", ...)`, constructs
an `efold_array`, and passes it to the compute target at construction time.

`store()` populates `self._values` directly from the returned float arrays
and the pre-existing `efold_array`:

```python
def store(self):
    data = ray.get(self._compute_ref)
    self._compute_ref = None
    if data.get("failure", False):
        self._failure = True
        self._values = []
        return
    self._failure = False
    self._values = [
        FooValue(store_id=None, N=N_obj, phi1=phi1, ...)
        for N_obj, phi1, ... in zip(self._N_sample, data["phi1"], ...)
    ]
```

No `_raw_sample` handoff is needed. The factory's `store()` reads
`v.N.store_id` directly from `obj._values`. The default `store_handler`
(`obj.store()`) is sufficient — no custom handler is needed.

### Approach B — internally-built grid (used by `InflatonTrajectory`)

The integration endpoint `N_end` is not known until the ODE completes, so the
grid cannot be pre-minted. The remote function builds the grid internally from
`samples_per_N` and returns float lists.

`store()` stashes these as a temporary handoff in `self._raw_sample`:

```python
def store(self):
    data = ray.get(self._compute_ref)
    self._compute_ref = None
    if data.get("failure", False):
        self._failure = True
        self._values = []
        return
    self._failure = False
    self._N_end = data["N_end"]
    # Temporary handoff for the store_handler; deleted after _values is built.
    self._raw_sample = {"N_sample": data["N_sample"], "phi": data["phi"], ...}
```

A custom `store_handler` in `main.py` then mints `efold_value` objects via
the pool and assembles `self._values`, after which `_raw_sample` is deleted:

```python
def foo_store_handler(obj, pool):
    obj.store()                          # populates _raw_sample
    if obj.failure:
        return
    raw = obj._raw_sample
    efold_objects = ray.get(
        pool.object_get("efold_value", payload_data=[{"N": N} for N in raw["N_sample"]])
    )
    obj._values = [
        FooValue(store_id=None, N=N_obj, ...)
        for N_obj, ... in zip(efold_objects, raw["phi"], ...)
    ]
    del obj._raw_sample
```

The factory's `store()` reads `v.N.store_id` directly from `obj._values`,
which are fully populated by the time the factory runs.

The custom handler must be wired in explicitly at the `RayWorkPool` call site
in `main.py` — never hidden in a default. This makes the non-standard behaviour
visible to anyone reading the pipeline.

## Verification

Before finishing any session that touches `ComputeTargets/`:

```bash
# Confirm no compute target class has @ray.remote
python -c "
import inspect
from ComputeTargets import InflatonTrajectory, FullInstanton, SlowRollInstanton
for cls in [InflatonTrajectory, FullInstanton, SlowRollInstanton]:
    assert isinstance(cls, type), f'{cls.__name__} is a Ray actor, not a plain class'
print('All plain Python classes: OK')
"

# Confirm no private Ray bypass anywhere
grep -rn "__ray_actor_class__" ComputeTargets/ Datastore/
# must return no output

# Confirm InflatonTrajectory uses samples_per_N, not N_sample
grep -n "N_sample" ComputeTargets/InflatonTrajectory.py
# must return no output (N_sample was replaced by samples_per_N)

# Confirm FullInstanton and SlowRollInstanton use N_sample (efold_array, pre-minted)
grep -n "samples_per_N" ComputeTargets/FullInstanton.py ComputeTargets/SlowRollInstanton.py
# must return no output (these use Approach A, not samples_per_N)
```
