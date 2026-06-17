# Prompt: Stage 4 — `CompactionFunction` orchestration in `main.py`

## Prerequisites

This prompt assumes:

- `prompt_compaction_function_v3.md` and its `patch1` have been applied
- `CompactionFunction`, `CosmologicalParams`, and their factories are
  registered and working
- Stages 1–3 in `main.py` are unchanged

## Overview

Add Stage 4 to `run_all_pipelines()` in `main.py`. It runs after Stage 3
and computes a `CompactionFunction` for every grid point
`(model, N_init, N_final, delta_Nstar)`. The pattern follows the ChamPBH
two-pass approach: a vectorised existence check via `RayWorkPool`, then a
parallel lookup of the required upstream instanton objects for missing items,
then computation.

The stage is driven by the same `grid` list already built for Stages 2 and 3.

---

## Part 1: register `CosmologicalParams` in `execute()`

In `execute()`, after the tolerances and initial conditions are registered
and before `run_all_pipelines()` is called, add:

```python
## -----------------------------------------------------------------------
## REGISTER COSMOLOGICAL PARAMETERS
## -----------------------------------------------------------------------
from CosmologicalModels.params import Planck2018
from CosmologicalModels.cosmo_params import CosmologicalParams

cosmo = ray.get(
    pool.object_get("CosmologicalParams", payload={"params": Planck2018()})
)
print(f"\n** Cosmological parameters: {cosmo.name} (store_id={cosmo.store_id})")
```

Pass `cosmo` into `run_all_pipelines()` as a new keyword argument:

```python
run_all_pipelines(
    pool=pool,
    ...
cosmo = cosmo,
)
```

Update the `run_all_pipelines()` signature accordingly:

```python
def run_all_pipelines(
        pool: ShardedPool,
        model_list: List[dict],
        N_init_array: List[N_init],
        N_final_array: List[N_final],
        delta_Nstar_array: List[delta_Nstar],
        phi0: phi_value,
        pi0: pi_value,
        samples_per_N: float,
        atol: tolerance,
        rtol: tolerance,
        cosmo,  # CosmologicalParams instance
        diffusion_model=None,
):
```

---

## Part 2: add Stage 4 to `run_all_pipelines()`

Add the following block immediately after the Stage 3 `_run_instanton_queue`
call, before the closing of `run_all_pipelines()`.

```python
## -----------------------------------------------------------------------
## STAGE 4: Compaction functions — two-pass pattern with upstream lookup
## -----------------------------------------------------------------------

from ComputeTargets.CompactionFunction import CompactionFunction, CompactionFunctionProxy
from ComputeTargets.FullInstanton import FullInstantonProxy
from ComputeTargets.SlowRollInstanton import SlowRollInstantonProxy

print("\n** STAGE 4: COMPACTION FUNCTIONS")

C_THRESHOLD = 0.4
C_BAR_THRESHOLD = 0.4


def cf_key_fields(item) -> dict:
    """Cheap identifying fields for the Pass-1 existence check."""
    model_idx, N_init_obj, N_final_obj, dns = item
    return dict(
        trajectory=traj_proxies[model_idx],
        delta_Nstar=dns,
        cosmo=cosmo,
        C_threshold=C_THRESHOLD,
        C_bar_threshold=C_BAR_THRESHOLD,
        atol=atol,
        rtol=rtol,
        tags=[],
    )


## Pass 1: vectorised existence check, binned by shard key (delta_Nstar)
cf_binned = {}
for item in grid:
    cf_binned.setdefault(shard_key_of(item), []).append(item)

cf_shard_keys = list(cf_binned.keys())

cf_query_queue = RayWorkPool(
    pool,
    cf_shard_keys,
    task_builder=lambda key: pool.object_get_vectorized(
        "CompactionFunction",
        key,
        payload_data=[
            {**cf_key_fields(item), "_do_not_populate": True}
            for item in cf_binned[key]
        ],
    ),
    compute_handler=None,
    store_handler=None,
    persist_handler=None,
    validation_handler=None,
    title=None,
    store_results=True,
    create_batch_size=20,
    process_batch_size=20,
)
cf_query_queue.run()

cf_missing = [
    item
    for key, objs in zip(cf_shard_keys, cf_query_queue.results)
    for item, obj in zip(cf_binned[key], objs)
    if not obj.available
]
print(
    f"   -- {len(grid) - len(cf_missing)} already computed, "
    f"{len(cf_missing)} to compute"
)

if cf_missing:
    ## Pass 2a: look up FullInstanton instances for missing items (do not populate)
    fi_binned = {}
    for item in cf_missing:
        fi_binned.setdefault(shard_key_of(item), []).append(item)

    fi_shard_keys = list(fi_binned.keys())

    fi_lookup_queue = RayWorkPool(
        pool,
        fi_shard_keys,
        task_builder=lambda key: pool.object_get_vectorized(
            "FullInstanton",
            key,
            payload_data=[
                {**key_fields(item), "_do_not_populate": True}
                for item in fi_binned[key]
            ],
        ),
        compute_handler=None,
        store_handler=None,
        persist_handler=None,
        validation_handler=None,
        title=None,
        store_results=True,
        create_batch_size=20,
        process_batch_size=20,
    )
    fi_lookup_queue.run()

    # Build a dict from item identity to FullInstanton lookup result
    fi_results = {
        id(item): obj
        for key, objs in zip(fi_shard_keys, fi_lookup_queue.results)
        for item, obj in zip(fi_binned[key], objs)
    }

    ## Pass 2b: look up SlowRollInstanton instances for missing items
    sr_lookup_queue = RayWorkPool(
        pool,
        fi_shard_keys,
        task_builder=lambda key: pool.object_get_vectorized(
            "SlowRollInstanton",
            key,
            payload_data=[
                {**key_fields(item), "_do_not_populate": True}
                for item in fi_binned[key]
            ],
        ),
        compute_handler=None,
        store_handler=None,
        persist_handler=None,
        validation_handler=None,
        title=None,
        store_results=True,
        create_batch_size=20,
        process_batch_size=20,
    )
    sr_lookup_queue.run()

    sr_results = {
        id(item): obj
        for key, objs in zip(fi_shard_keys, sr_lookup_queue.results)
        for item, obj in zip(fi_binned[key], objs)
    }


    ## Pass 2c: filter to items where at least one instanton is available,
    ## build proxies, and enqueue CompactionFunction computation
    def build_cf_work_ref(item):
        model_idx, N_init_obj, N_final_obj, dns = item

        fi_obj = fi_results[id(item)]
        sr_obj = sr_results[id(item)]

        fi_proxy = FullInstantonProxy(fi_obj) if fi_obj.available else None
        sr_proxy = SlowRollInstantonProxy(sr_obj) if sr_obj.available else None

        if fi_proxy is None and sr_proxy is None:
            # Both upstream instantons missing — cannot compute CompactionFunction
            return None

        return pool.object_get(
            "CompactionFunction",
            trajectory=traj_proxies[model_idx],
            full_instanton=fi_proxy,
            slow_roll_instanton=sr_proxy,
            delta_Nstar=dns,
            cosmo=cosmo,
            C_threshold=C_THRESHOLD,
            C_bar_threshold=C_BAR_THRESHOLD,
            atol=atol,
            rtol=rtol,
            tags=[],
        )


    # Filter out items where both instantons are missing
    computable = [
        item for item in cf_missing
        if fi_results[id(item)].available or sr_results[id(item)].available
    ]
    n_skipped = len(cf_missing) - len(computable)
    if n_skipped > 0:
        print(
            f"   -- {n_skipped} item(s) skipped: no converged instanton available "
            f"for either FullInstanton or SlowRollInstanton"
        )

    cf_work_queue = RayWorkPool(
        pool,
        computable,
        task_builder=build_cf_work_ref,
        compute_handler=lambda obj, **kwargs: obj.compute(**kwargs),
        store_handler=_default_store_handler,
        persist_handler=lambda obj, pool: pool.object_store(obj),
        validation_handler=lambda obj: pool.object_validate(obj),
        label_builder=lambda obj: (
            f"CompactionFunction(dNstar={float(obj.delta_Nstar):.4g}, "
            f"Ninit={float(obj.N_init_value):.4g}, "
            f"Nfinal={float(obj.N_final_value):.4g})"
        ),
        title="STAGE 4: COMPACTION FUNCTIONS",
        store_results=False,
        create_batch_size=5,
        process_batch_size=3,
        max_task_queue=MAX_INFLIGHT_COMPUTE,
    )
    cf_work_queue.run()
```

---

## Part 3: update imports in `main.py`

Add to the top-level imports:

```python
from CosmologicalModels.params import Planck2018
from CosmologicalModels.cosmo_params import CosmologicalParams
from ComputeTargets.CompactionFunction import CompactionFunction, CompactionFunctionProxy
```

---

## Part 4: update `inventory()` in `main.py`

Add after the existing `_inventory_object` calls:

```python
_inventory_object(pool, "CompactionFunction", "Compaction functions")
```

---

## Part 5: acceptance criteria

1. With a fully-populated Stage 2 and Stage 3 database, Stage 4 runs without
   error and produces `CompactionFunction` entries for every grid point where
   at least one of `FullInstanton` or `SlowRollInstanton` converged.

2. Grid points where both instantons failed or are absent produce a console
   warning and are skipped — no exception is raised.

3. Re-running the pipeline with the same database skips all items already
   present (Pass 1 returns `available=True` for all).

4. The `cosmo_serial` FK on every `compaction_function` row matches the
   `store_id` of the `Planck2018` parameter bundle registered in Stage 0.

5. `inventory()` reports `CompactionFunction` counts correctly.

---

## Part 6: notes

- **`key_fields` is reused from Stages 2/3** for the instanton lookups in
  Passes 2a and 2b. This works because `CompactionFunction` identifies its
  upstream instantons using the same `(trajectory, N_init, N_final,
  delta_Nstar, atol, rtol)` key that `FullInstanton` and `SlowRollInstanton`
  use for their own identity.

- **Both instanton lookups use `_do_not_populate=True`** in Passes 2a and 2b.
  We only need to know whether the objects exist and obtain their `store_id`s
  for proxy construction — we do not need to deserialise their sample arrays.

- **`fi_proxy` and `sr_proxy` carry `store_id`s** from the lookup, so the
  `CompactionFunction` factory can record `full_instanton_serial` and
  `slow_roll_instanton_serial` FKs correctly even though the sample data is
  not populated.

- **`build_cf_work_ref` returns `None`** for items where both instantons are
  missing. The `RayWorkPool` `task_builder` must handle `None` returns by
  skipping that item. Verify this is the case in the existing `RayWorkPool`
  implementation; if not, filter before passing to the queue (the `computable`
  list already does this, so `None` should not be returned in practice).

- **`C_THRESHOLD` and `C_BAR_THRESHOLD`** are defined as module-level
  constants at the top of the Stage 4 block. If CLI arguments for these are
  added later, replace with `args.C_threshold` and `args.C_bar_threshold`.

- **`cosmo` is registered once** in `execute()` and passed through
  `run_all_pipelines()`. It is not re-registered inside the stage loop.