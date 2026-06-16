# `*Proxy` objects stay opaque — never expose the raw `ObjectRef`

This rule has no `paths:` frontmatter, so it loads at session start alongside
`CLAUDE.md`. It applies to every `FooProxy` class in `ComputeTargets/` (e.g.
`InflatonTrajectoryProxy`, `FullInstantonProxy`, `SlowRollInstantonProxy`) and
to any code that consumes one — other compute targets, `main.py`,
`plot_*.py`. See `.claude/rules/ray-dispatch.md` Part 4 for the basic shape
of a `FooProxy` class; this file covers how it must be *used*.

## The idiom

A `FooProxy` wraps a plain `Foo` instance in `ray.put()` so it can be handed
to other Ray tasks without re-serialising the full object every time it is
passed around:

```python
class FooProxy:
    def __init__(self, model: Foo):
        self._ref = ray.put(model)
        self._store_id = model.store_id if model.available else None

    @property
    def available(self) -> bool:
        return self._store_id is not None

    def get(self) -> Foo:
        return ray.get(self._ref)
```

To consume one, **pass the proxy itself** as the argument — to a `@ray.remote`
function, to a `compute()` method, in a work-item payload dict — and call
`.get()` *inside* the consumer to materialise the real object:

```python
@ray.remote
def _compute_full_instanton(trajectory: InflatonTrajectoryProxy, ...) -> dict:
    traj = trajectory.get()
    potential = traj._potential
    ...
```

This is the pattern already used by `ComputeTargets/FullInstanton.py` and
`ComputeTargets/SlowRollInstanton.py`, where `trajectory.get()` is called
both inside the `@ray.remote` worker function and inside `compute()` on the
driver.

## Why passing the proxy is enough — no `.ref` shortcut needed

Ray's serialisation context specially tracks `ObjectRef`s for transfer by
reference (not by value) regardless of whether the ref is a bare top-level
argument to `.remote()` or nested as an attribute inside a plain Python
object that gets pickled into the task args. So passing `proxy` instead of
`proxy._ref` costs nothing extra — the underlying `Foo` data is not
serialised a second time either way.

The only practical difference: a bare `ObjectRef` argument to `.remote()` is
auto-dereferenced by Ray before the task body runs, so the function receives
the materialised object directly with no explicit `.get()` call. Passing the
proxy means the consumer must call `.get()` itself. That one extra line is
the right trade — it keeps the proxy's Ray plumbing opaque to every caller.

## What is forbidden

```python
class FooProxy:
    @property
    def ref(self) -> ObjectRef:        # NEVER — leaks the ObjectRef
        return self._ref
```

Do not add a `.ref` (or similarly named) property that exposes the
underlying `ObjectRef`, and do not call `proxy._ref` or `ray.get(proxy._ref)`
from outside the proxy class. If a call site needs the materialised object,
it should hold the proxy and call `proxy.get()` — never reach past the proxy
for its private `ObjectRef`.

This was flagged after `InflatonTrajectoryProxy.ref` was added solely so
`plot_InstantonSolutions.py` could pass `traj_proxy.ref` into
`_plot_trajectory_item` and rely on Ray's auto-dereferencing, bypassing
`.get()`. It worked, but broke encapsulation and made `InflatonTrajectoryProxy`
inconsistent with `FullInstantonProxy`/`SlowRollInstantonProxy`, neither of
which expose anything beyond `.get()`. Fixed by removing `.ref` and changing
`_plot_trajectory_item` to accept the proxy and call `traj_proxy.get()`
internally, matching the pattern used everywhere else this idiom appears.

## Checklist for any new `FooProxy`

- Wraps the underlying object via `ray.put()` in `__init__`, storing only the
  `ObjectRef` plus whatever plain scalars (`store_id`, key parameters) are
  needed for cheap checks without materialising the object.
- Exposes `.get()` to materialise the real object — and nothing that exposes
  the `ObjectRef` itself.
- Is passed by value (the proxy instance) into remote functions, `compute()`
  methods, and work-item payloads; the consumer calls `.get()` internally.
