# Prompt 8 — Pipeline mode wiring: `--no-store-values` and `_run_pipeline_queue`

## Context

This is the final wiring prompt. Prompts 4–7 built the per-factory
scalars-only storage mode, the `_populate_from_result` refactor,
`compute_pipeline`, and `PipelineWorkItem`. This prompt plugs all of that
into `main.py` and the CLI, replacing Stages 2, 3, and 4 in
`run_all_pipelines` with a single unified pipeline stage when
`--no-store-values` is given.

**Before writing anything, read these files in full:**
- `main.py` — the entire file, especially:
  - Module-level constants (`MAX_INFLIGHT_PIPELINE`, `_PIPELINE_STAGES`)
  - `_run_instanton_queue` (lines ~109–200)
  - `run_all_pipelines` Stages 2–4 (lines ~330–634)
  - `execute()` and how it calls `run_all_pipelines` (lines ~637–704)
- `config/argument_parser.py` — to find the right argument group and
  existing flag style
- `ComputeTargets/pipeline.py` — `PipelineWorkItem`, `compute_pipeline`,
  `_check_scalar_integrity` (added in Prompt 7)
- `ComputeTargets/FullInstanton.py` — `set_store_full_values()`,
  `_my_id` (private attr backing `store_id`)
- `ComputeTargets/SlowRollInstanton.py` — same
- `ComputeTargets/CompactionFunction.py` — `set_store_full_values()`,
  `CompactionFunction.__init__` parameter list
- `Datastore/object.py` — `DatastoreObject`, confirm `_my_id` is the
  backing attribute for `store_id` and that setting it directly is safe
  (no setter exists that would need to be called instead)

Do not guess at attribute names, argument groups, or import paths.

## Task

### 1. `config/argument_parser.py` — add `--no-store-values`

Add to the "Instanton parameters" group (or whichever group currently
holds `--sample-grid-csv` from Prompt 2):

```python
parser.add_argument(
    "--no-store-values",
    action="store_true",
    default=False,
    help=(
        "Skip writing per-sample value rows for FullInstanton, "
        "SlowRollInstanton, and CompactionFunction. Only scalar summary "
        "columns are persisted. Activates unified pipeline mode: all three "
        "compute targets are computed in a single Ray task per grid point, "
        "so FullInstanton and SlowRollInstanton values are passed in-memory "
        "to the CompactionFunction computation and never need to be loaded "
        "from the database. Recommended for sparse-sampling / "
        "sensitivity-analysis runs."
    ),
)
```

### 2. `main.py` — add `_run_pipeline_queue`

Add a new function `_run_pipeline_queue` alongside `_run_instanton_queue`.
Its structure mirrors the multi-pass pre-dispatch check in the current
Stage 4 (which it replaces), then runs a single `RayWorkPool` for the
compute/persist/validate cycle.

```python
def _run_pipeline_queue(
    pool: ShardedPool,
    task_list: list,            # full grid: [(model_idx, N_init, N_final, dns), ...]
    key_fields,                 # callable: item → dict (no N_sample)
    full_payload,               # callable: item → dict (with N_sample, efold_array)
    shard_key_of,               # callable: item → delta_Nstar
    traj_proxies: list,         # indexed by model_idx
    cosmo,                      # CosmologicalParams
    atol,                       # tolerance domain object
    rtol,                       # tolerance domain object
    dm,                         # AbstractDiffusionModel
    C_threshold: float,
    C_bar_threshold: float,
    no_store_values: bool,
    title: str = "STAGES 2+3+4: UNIFIED PIPELINE",
):
```

Body:

**Pre-dispatch Step A — vectorized FullInstanton lookup (scalar-only)**

Identical to Stage 4's current Pass 1a: bin `task_list` by `shard_key_of`,
run a `RayWorkPool` with `compute_handler=None` using
`pool.object_get_vectorized("FullInstanton", key, payload_data=[{**key_fields(item), "_do_not_populate": True} for item in binned[key]])`,
`store_results=True`. Collect results into `fi_existing_map: dict` keyed
by `id(item)`.

**Pre-dispatch Step B — vectorized SlowRollInstanton lookup (scalar-only)**

Identical pattern, for `"SlowRollInstanton"`. Collect into
`sri_existing_map`.

**Pre-dispatch Step C — CF existence check**

Identical to Stage 4's current Pass 1c:

```python
def cf_key_fields(item):
    model_idx, N_init_obj, N_final_obj, dns = item
    fi_obj  = fi_existing_map[id(item)]
    sri_obj = sri_existing_map[id(item)]
    fi_proxy  = FullInstantonProxy(fi_obj)  if fi_obj.available  else None
    sri_proxy = SlowRollInstantonProxy(sri_obj) if sri_obj.available else None
    return dict(
        trajectory=traj_proxies[model_idx],
        full_instanton=fi_proxy,
        slow_roll_instanton=sri_proxy,
        delta_Nstar=dns,
        cosmo=cosmo,
        C_threshold=C_threshold,
        C_bar_threshold=C_bar_threshold,
        atol=atol,
        rtol=rtol,
        tags=[],
    )
```

Run the CF existence check only for items where at least one instanton
is available (`fi_obj.available or sri_obj.available`). Items where
neither instanton is available cannot produce a CF and must be skipped
with a note:

```python
skippable = [item for item in task_list
             if not fi_existing_map[id(item)].available
             and not sri_existing_map[id(item)].available]
checkable = [item for item in task_list if item not in set(skippable)]
```

Run vectorized CF query for `checkable` items. Collect the resulting CF
objects. Items where the CF is already available: skip. Items where the
CF is missing: add to `cf_missing`.

Print a status line, e.g.:
```
** PIPELINE LOOKUP:
   -- N already computed, M to compute[, K skipped (no instanton available)]
```

**Compute step — single `RayWorkPool` for `cf_missing`**

```python
def build_pipeline_item(item):
    model_idx, N_init_obj, N_final_obj, dns = item
    payload = full_payload(item)   # builds N_sample via pool.object_get("efold_value", ...)
    return PipelineWorkItem(
        grid_item=item,
        traj_proxy=traj_proxies[model_idx],
        N_sample=payload["N_sample"],
        dm=dm,
        cosmo=cosmo,
        C_threshold=C_threshold,
        C_bar_threshold=C_bar_threshold,
        atol_obj=atol,
        rtol_obj=rtol,
        fi_existing=fi_existing_map[id(item)],
        sri_existing=sri_existing_map[id(item)],
    )

def pipeline_store_handler(item, pool):
    item.store()   # resolves Ray future, reconstructs fi/sri/cf, integrity check

def pipeline_persist_handler(item, pool):
    return _persist_pipeline_item(item, pool, no_store_values)

def pipeline_validation_handler(item):
    return pool.object_validate(item.cf)

pipeline_queue = RayWorkPool(
    pool,
    cf_missing,
    task_builder=build_pipeline_item,
    compute_handler=lambda obj, **kw: obj.compute(**kw),
    store_handler=pipeline_store_handler,
    persist_handler=pipeline_persist_handler,
    validation_handler=pipeline_validation_handler,
    label_builder=lambda obj: (
        f"Pipeline(dNstar={float(obj.delta_Nstar):.4g})"
    ),
    title=title,
    store_results=False,
    create_batch_size=5,
    process_batch_size=3,
    max_task_queue=MAX_INFLIGHT_PIPELINE,
)
pipeline_queue.run()
```

### 3. `main.py` — add `_persist_pipeline_item`

A module-level function (not a lambda) for clarity and testability:

```python
def _persist_pipeline_item(item: PipelineWorkItem, pool: ShardedPool, no_store_values: bool):
    """
    Persist FullInstanton, SlowRollInstanton, and CompactionFunction for one
    pipeline work item, in FK order: fi first, then sri, then cf.

    If fi or sri already exist in the database (scalar-only rows from a
    prior DOE run), their store_ids are reused and no new rows are inserted.
    Otherwise they are persisted as scalar-only (if no_store_values=True)
    or full-fidelity (if False).

    Returns the ObjectRef from pool.object_store(cf), which RayWorkPool
    awaits before calling the validation_handler.
    """
    fi  = item.fi
    sri = item.sri
    cf  = item.cf

    # ── FullInstanton ────────────────────────────────────────────────────────
    if item.fi_existing is not None and item.fi_existing.available:
        # Reuse existing DB row as FK anchor — propagate its store_id to
        # the freshly-computed fi object. Since cf._full_instanton IS fi
        # (Python reference), this also fixes cf's FK reference.
        fi._my_id = item.fi_existing.store_id
    else:
        if no_store_values:
            fi.set_store_full_values(False)
        fi_stored = ray.get(pool.object_store(fi))
        fi._my_id = fi_stored.store_id    # propagate store_id back to local fi
        ray.get(pool.object_validate(fi)) # scalar-only validate is trivial

    # ── SlowRollInstanton ────────────────────────────────────────────────────
    if item.sri_existing is not None and item.sri_existing.available:
        sri._my_id = item.sri_existing.store_id
    else:
        if no_store_values:
            sri.set_store_full_values(False)
        sri_stored = ray.get(pool.object_store(sri))
        sri._my_id = sri_stored.store_id
        ray.get(pool.object_validate(sri))

    # ── CompactionFunction ───────────────────────────────────────────────────
    # fi._my_id and sri._my_id are now set.
    # cf._full_instanton IS fi and cf._slow_roll_instanton IS sri
    # (reference semantics — set in PipelineWorkItem.store()), so
    # the factory's store() will read the correct FK serials automatically.
    if no_store_values:
        cf.set_store_full_values(False)

    return pool.object_store(cf)   # ObjectRef — RayWorkPool awaits this
```

**Critical note for implementation**: confirm that `cf._full_instanton` and
`cf._slow_roll_instanton` in `PipelineWorkItem.store()` (Prompt 7) are set
to `fi` and `sri` directly (not copies), so that `fi._my_id = X` above is
immediately visible through `cf._full_instanton.store_id`. If Prompt 7's
implementation passed anything other than the same object references, this
will silently produce `full_instanton_serial = NULL` in the database. Verify
by inspection before finishing this prompt.

### 4. `main.py` — modify `run_all_pipelines`

Add `no_store_values: bool = False` to the signature of `run_all_pipelines`.

When `no_store_values is True`, **replace Stages 2, 3, and 4** with a
single call to `_run_pipeline_queue`:

```python
if no_store_values:
    # Unified pipeline: compute all three targets per grid point in a single
    # Ray task. Stages 2, 3, and 4 are merged.
    if stop_after in {"full-instanton", "slow-roll-instanton"}:
        print(
            f"\n!! WARNING: --stop-after {stop_after!r} is not supported in "
            f"pipeline mode (--no-store-values). The full pipeline will run "
            f"(FullInstanton + SlowRollInstanton + CompactionFunction)."
        )
    _run_pipeline_queue(
        pool=pool,
        task_list=grid,
        key_fields=key_fields,
        full_payload=full_payload,
        shard_key_of=shard_key_of,
        traj_proxies=traj_proxies,
        cosmo=cosmo,
        atol=atol,
        rtol=rtol,
        dm=dm,
        C_threshold=C_THRESHOLD,
        C_bar_threshold=C_BAR_THRESHOLD,
        no_store_values=True,
    )
    return
```

Place this block immediately after the `traj_proxies` / `grid` / `key_fields`
/ `full_payload` / `shard_key_of` setup and before the existing Stage 2
`_run_instanton_queue` call. The existing stages 2, 3, and 4 are **not
removed** — they remain as the `else` branch (i.e., when
`no_store_values is False`). The `C_THRESHOLD` / `C_BAR_THRESHOLD`
constants must be visible at the point of the `_run_pipeline_queue` call
(currently defined inside the Stage 4 block — move them to just after the
grid setup, shared between both branches).

### 5. `execute()` — pass `no_store_values` through

```python
run_all_pipelines(
    ...,
    no_store_values=args.no_store_values,
)
```

### 6. `_PIPELINE_STAGES` update

Add `"compaction-function"` if it's not already in `_PIPELINE_STAGES`
(check the existing list). `stop_after == "compaction-function"` should
remain supported in pipeline mode (it's a no-op since the pipeline already
terminates at CF). Do not add `"full-instanton"` or `"slow-roll-instanton"`
as separate stop points that the pipeline pretends to support — just the
warning.

## Acceptance criteria

- [ ] `python main.py --help` shows `--no-store-values` in the argument
      listing with the docstring above.
- [ ] Running `main.py` with `--no-store-values` and a small grid (2–3
      `delta_Nstar` values, 1–2 `N_init`/`N_final` values) against a fresh
      database completes without error and produces:
      - Validated `FullInstanton` rows with `full_values_stored: false` in
        `diagnostics_json` (check via `--inventory` or direct DB query)
      - Validated `SlowRollInstanton` rows with same
      - Validated `CompactionFunction` rows with `full_values_stored: false`
        in `metadata`
      - Zero rows in `FullInstantonValue`, `SlowRollInstantonValue`, and
        `CompactionFunctionSamples` tables
      - `full_instanton_serial` and `slow_roll_instanton_serial` FKs in
        `CompactionFunction` rows are non-NULL and point to the correct
        `FullInstanton`/`SlowRollInstanton` rows
- [ ] Running `main.py` WITHOUT `--no-store-values` against a fresh
      database produces identical results to the current `main` branch:
      full value rows are present in all three child tables, FK references
      are correct, validated = True. This is the regression check that the
      existing pipeline is untouched.
- [ ] Running `main.py` with `--no-store-values` against a database that
      already has scalar-only `FullInstanton`/`SlowRollInstanton` rows for
      the same grid (i.e., a restart scenario): the CF is computed and
      stored correctly, no duplicate fi/sri rows are inserted, the CF FK
      references point to the pre-existing fi/sri store_ids.
- [ ] `_persist_pipeline_item` is unit-tested (no live Ray needed) with a
      mock pool that records what was called, verifying:
      - When `fi_existing.available` is True: `pool.object_store` is NOT
        called for fi, and `fi._my_id` is set from `fi_existing.store_id`
      - When `fi_existing` is None: `pool.object_store` IS called for fi
      - `no_store_values=True` causes `set_store_full_values(False)` to be
        called on fi/sri/cf before their respective `pool.object_store` calls
      - `pool.object_store(cf)` is always the return value (always called
        last)
- [ ] `_check_scalar_integrity` is called and raises correctly when a
      pre-existing fi row has mismatched `msr_action` — tested end-to-end
      by constructing a `PipelineWorkItem` with a synthetic `fi_existing`
      whose `msr_action` differs from what the pipeline returned, and
      asserting `RuntimeError` is raised from `item.store()`.
- [ ] `git diff` touches only `main.py`, `config/argument_parser.py`, and
      test files. No compute-target files, no factory files, no
      `RayWorkPool.py`.

## Out of scope (do not attempt in this prompt)

- The Latin hypercube / Sobol CSV generation script — handled separately.
- Any changes to `plot_InstantonSolutions.py` for pipeline-mode awareness
  (it already skips value-dependent plots gracefully per Prompt 3).
- The GP / sensitivity-analysis tooling.
- Any performance tuning of `_run_pipeline_queue`'s batch sizes beyond
  reusing `MAX_INFLIGHT_PIPELINE`.

## Commit

One commit, message along the lines of:
`main: add --no-store-values and unified pipeline mode (_run_pipeline_queue)`
