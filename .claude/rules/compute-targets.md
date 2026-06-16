---
paths:
  - "ComputeTargets/**"
---

# ComputeTargets conventions

Loaded when Claude works on files in `ComputeTargets/`. The Ray dispatch
pattern is in `.claude/rules/ray-dispatch.md` (always loaded); this file
covers conventions specific to this directory.

## File layout within each compute target file

```
ComputeTargets/Foo.py
│
├── imports
│
├── @ray.remote
│   def _compute_foo(...) -> dict       # numerical work; stub until Prompt 6
│
├── class FooValue(DatastoreObject)     # one sample point; plain Python
│
├── class Foo(DatastoreObject)          # compute target; plain Python
│   ├── __init__  sets self._compute_ref = None
│   ├── @property available / failure / n_fields / result accessors
│   ├── compute() → ObjectRef
│   └── store()   → None
│         Approach A (FullInstanton, SlowRollInstanton):
│           grid pre-minted at construction; populates self._values directly
│         Approach B (InflatonTrajectory):
│           grid built internally by worker; populates self._raw_sample as
│           a temporary handoff for the custom store_handler in main.py,
│           which mints efold_value objects and then populates self._values
│
└── class FooProxy                      # lightweight reference; plain Python
    ├── __init__(model: Foo)  uses ray.put(model)
    ├── @property available / store_id / key scalars
    └── get() → Foo
```

## `available` and `failure` semantics

`available` is `True` when the object has a valid `store_id` (persisted in the
database). It is `True` even for failed objects — a failed record is a valid
record; it prevents re-attempting the same failing computation on subsequent
runs. `failure` is the separate signal that computation was attempted and failed.

| State               | `available` | `failure` |
|---------------------|-------------|-----------|
| Fresh, unsaved      | `False`     | `False`   |
| Saved, not computed | `True`      | `False`   |
| Computed, succeeded | `True`      | `False`   |
| Computed, failed    | `True`      | `True`    |

## Guards in `compute()`

All compute targets must guard against being called in an incomplete state:

```python
def compute(self, label=None) -> ObjectRef:
    if self._compute_ref is not None:
        raise RuntimeError("compute() already in progress")
    if getattr(self, "_failure", None) is not None:
        raise RuntimeError("already computed (or failed)")
    ...
```

`InflatonTrajectory` additionally guards that `samples_per_N` is set, since
it is `Optional` to allow query-only objects:

```python
    if self._samples_per_N is None:
        raise RuntimeError(
            "InflatonTrajectory: compute() called but samples_per_N is not set. "
            "This object can only represent a query."
        )
```

`FullInstanton` and `SlowRollInstanton` similarly guard that `N_sample` is set:

```python
    if self._N_sample is None:
        raise RuntimeError(
            "FullInstanton: compute() called but N_sample is not set. "
            "This object can only represent a query."
        )
```

## Proxy construction — always from a plain instance

```python
# Correct
traj = InflatonTrajectory(store_id=99, phi0=phi0, ...)   # plain constructor
proxy = InflatonTrajectoryProxy(traj)                     # ray.put(traj)

# Wrong — InflatonTrajectory has no @ray.remote
actor = InflatonTrajectory.remote(...)
proxy = InflatonTrajectoryProxy(actor)
```

## The `label` parameter

`compute(label=None)` passes the label through to the remote function for
logging. `RayWorkPool` supplies it via `label_builder` if one is configured.
The remote function should include it in any print output so log messages are
identifiable in a multi-worker environment.

## Stub remote functions (before Prompt 6)

Until `compute()` is implemented, the `@ray.remote` functions raise
`NotImplementedError`. They must still return an `ObjectRef` when called with
`.remote()` — the `NotImplementedError` propagates through Ray and is caught
by the caller as a `RayTaskError`. This is tested in the AC checks.
