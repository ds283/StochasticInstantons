# Prompt 7 — `compute_pipeline` and `PipelineWorkItem`

## Context

This prompt adds the compute infrastructure for the unified pipeline
architecture: a single `@ray.remote` function that computes `FullInstanton`,
`SlowRollInstanton`, and `CompactionFunction` for one grid point in sequence
inside a Ray worker (never blocking the driver), and a `PipelineWorkItem`
wrapper that presents the standard `compute()`/`store()`/`available`
interface that `RayWorkPool` expects.

This prompt does NOT modify `main.py`'s `run_all_pipelines` — that wiring,
and the `--no-store-values` CLI flag, are Prompt 8. The goal here is a
self-contained, testable unit that Prompt 8 can plug in without needing to
also debug the compute logic.

**Before writing anything**, read these files in full:
- `ComputeTargets/FullInstanton.py` — `FullInstanton.__init__`, `compute()`,
  `_populate_from_result()`, `set_store_full_values()`
- `ComputeTargets/SlowRollInstanton.py` — same
- `ComputeTargets/CompactionFunction.py` — `_compute_instanton_path`
  signature (lines 62–75), `CompactionFunction.__init__`, `store()`,
  `_populate_from_result()`, `set_store_full_values()`
- `main.py` lines 1–200 — imports, `_run_instanton_queue`, `full_payload`,
  `key_fields`, `shard_key_of`, `MAX_INFLIGHT_PIPELINE`
- `main.py` lines 200–635 — all of `run_all_pipelines` including Stage 4's
  five-pass CF pattern, to understand exactly what this new infrastructure
  must replace in Prompt 8
- `RayTools/RayWorkPool.py` — the `compute_handler` → `store_handler` →
  `persist_handler` → `validation_handler` hook lifecycle

Do not guess at attribute names, dict keys, or import paths — use what
you read.

## New file: `ComputeTargets/pipeline.py`

### 1. `PIPELINE_SCALAR_INTEGRITY_RTOL`

A module-level named constant:

```python
# Relative tolerance for the integrity check on pre-existing scalar-only
# rows. Must be loose enough to tolerate floating-point non-determinism
# between two ODE solves (typically < 1e-10), but tight enough to catch
# real mismatches. 1e-4 (100 ppm) is conservative.
PIPELINE_SCALAR_INTEGRITY_RTOL = 1e-4
```

### 2. `_check_scalar_integrity(cls_name, existing_obj, fresh_data)`

A module-level private helper:

```python
def _check_scalar_integrity(
    cls_name: str,
    existing_obj,        # FullInstanton or SlowRollInstanton with .msr_action / ._N_total
    fresh_data: dict,    # raw result dict from _compute_full/slow_roll_instanton
) -> None:
```

- If `fresh_data.get("failure", False)` is `True`: return immediately —
  comparing a failure result against a previously successful scalar row is
  not meaningful here.
- Check `msr_action` and `N_total` (use `fresh_data["msr_action"]` and
  `fresh_data["N_total"]`; stored values are `existing_obj.msr_action` and
  `getattr(existing_obj, "_N_total", None)`).
- If either stored value is `None` (e.g., the existing row itself was a
  failure): skip that scalar silently.
- Relative error: `abs(stored - fresh) / max(abs(stored), 1e-300)`.
- If relative error exceeds `PIPELINE_SCALAR_INTEGRITY_RTOL`: raise
  `RuntimeError` with a message of the form:
  ```
  {cls_name}(id={existing_obj.store_id}): recomputed {scalar_name}=
  {fresh_val!r} disagrees with stored value {stored_val!r}
  (relative error {rel_err:.2e} > tolerance {PIPELINE_SCALAR_INTEGRITY_RTOL:.2e}).
  This is a database integrity failure — the computation may be
  non-deterministic or the database row may be corrupt.
  ```

### 3. `@ray.remote(num_cpus=0) def compute_pipeline(...)`

`num_cpus=0` is required: this function is an orchestrator that blocks on
nested Ray tasks while holding no CPU itself. The actual CPU work happens
inside the nested `_compute_full_instanton.remote(...)` and
`_compute_slow_roll_instanton.remote(...)` calls.

Signature:

```python
@ray.remote(num_cpus=0)
def compute_pipeline(
    trajectory,           # InflatonTrajectoryProxy
    N_init_obj,           # N_init domain object
    N_final_obj,          # N_final domain object
    delta_Nstar_obj,      # delta_Nstar domain object
    N_sample,             # efold_array (pre-built on driver)
    atol_obj,             # tolerance domain object
    rtol_obj,             # tolerance domain object
    dm,                   # AbstractDiffusionModel
    cosmo,                # CosmologicalParams
    C_threshold: float,
    C_bar_threshold: float,
    label: Optional[str] = None,
    verbose: bool = False,
) -> dict:
```

Body, in order:

1. **Construct `fi` and `sri` shells directly** (no `pool.object_get`):
   ```python
   fi  = FullInstanton(store_id=None, trajectory=trajectory,
                       N_init=N_init_obj, N_final=N_final_obj,
                       delta_Nstar=delta_Nstar_obj, N_sample=N_sample,
                       atol=atol_obj, rtol=rtol_obj, diffusion_model=dm)
   sri = SlowRollInstanton(store_id=None, trajectory=trajectory,
                           N_init=N_init_obj, N_final=N_final_obj,
                           delta_Nstar=delta_Nstar_obj, N_sample=N_sample,
                           atol=atol_obj, rtol=rtol_obj, diffusion_model=dm)
   ```

2. **Fan out both compute tasks in parallel**:
   ```python
   fi_ref  = fi.compute(label=label, verbose=verbose)
   sri_ref = sri.compute(label=label, verbose=verbose)
   fi_data, sri_data = ray.get([fi_ref, sri_ref])
   ```
   This blocks in the **worker**, not the driver.

3. **Populate fi and sri in memory**:
   ```python
   fi._populate_from_result(fi_data)
   sri._populate_from_result(sri_data)
   ```

4. **Load the trajectory for `_compute_instanton_path`**:
   ```python
   traj = trajectory.get()
   potential = traj._potential
   units = traj._units
   atol_f = 10.0 ** atol_obj.log10_tol
   rtol_f = 10.0 ** rtol_obj.log10_tol
   ```

5. **Call `_compute_instanton_path` directly** (bypassing the
   `CompactionFunction.compute()` → proxy → `available` check pathway —
   this is intentional; see architecture notes below):
   ```python
   full_cf_result = None
   if not fi.failure:
       full_cf_result = _compute_instanton_path(
           fi, False, traj, potential, units, cosmo,
           C_threshold, C_bar_threshold, atol_f, rtol_f,
           label=label, verbose=verbose,
       )

   sr_cf_result = None
   if not sri.failure:
       sr_cf_result = _compute_instanton_path(
           sri, True, traj, potential, units, cosmo,
           C_threshold, C_bar_threshold, atol_f, rtol_f,
           label=label, verbose=verbose,
       )
   ```

6. **Return combined result dict**:
   ```python
   return {
       "fi_data":    fi_data,
       "sri_data":   sri_data,
       "full":       full_cf_result,
       "slow_roll":  sr_cf_result,
   }
   ```
   Note: `cosmo_store_id` is NOT included — the driver has the `cosmo`
   object and sets `cf._cosmo_store_id` directly.

**Architecture note — why `_compute_instanton_path` is called directly:**
In the existing pipeline, `CompactionFunction.compute()` wraps
`_compute_instanton_path` inside a further `@ray.remote` function and
gates it on `full_instanton_proxy.available` (i.e., `store_id is not None`).
Inside `compute_pipeline`, `fi` and `sri` are populated in memory but have
no `store_id` (they haven't been persisted yet). The `available` check
would therefore incorrectly suppress both CF branches. Since
`_compute_instanton_path` only needs `instanton_obj.N_init_value`,
`instanton_obj.N_final_value`, and `instanton_obj.values` — all set by
`_populate_from_result` — calling it directly is both correct and avoids
an unnecessary extra layer of Ray dispatch.

### 4. `class PipelineWorkItem`

```python
class PipelineWorkItem:
    def __init__(
        self,
        grid_item,           # (model_idx, N_init_obj, N_final_obj, delta_Nstar_obj)
        traj_proxy,          # InflatonTrajectoryProxy
        N_sample,            # efold_array
        dm,                  # AbstractDiffusionModel
        cosmo,               # CosmologicalParams
        C_threshold: float,
        C_bar_threshold: float,
        atol_obj,            # tolerance
        rtol_obj,            # tolerance
        fi_existing,         # FullInstanton (scalars-only from DB, with store_id), or None
        sri_existing,        # SlowRollInstanton (scalars-only from DB, with store_id), or None
    ):
```

Store all constructor args as private attributes. Also:
- `self._compute_ref: Optional[ObjectRef] = None`
- `self._fi: Optional[FullInstanton] = None` — set by `store()`
- `self._sri: Optional[SlowRollInstanton] = None` — set by `store()`
- `self._cf: Optional[CompactionFunction] = None` — set by `store()`

Properties:

- `available -> bool`: always returns `False` — by construction,
  `PipelineWorkItem` is only created for grid points where CF does not yet
  exist.
- `delta_Nstar` → `self._grid_item[3]` — needed for shard routing.
- `fi -> Optional[FullInstanton]`: returns `self._fi` (populated by
  `store()`).
- `sri -> Optional[SlowRollInstanton]`: returns `self._sri`.
- `cf -> Optional[CompactionFunction]`: returns `self._cf`.
- `fi_existing -> Optional[FullInstanton]`: returns the DB-loaded scalar-
  only fi, if one was found before dispatch.
- `sri_existing -> Optional[SlowRollInstanton]`: same.

**`compute(self, label=None, verbose=False) -> ObjectRef`**:

```python
def compute(self, label=None, verbose=False) -> ObjectRef:
    if self._compute_ref is not None:
        raise RuntimeError("compute() already in progress")
    _, N_init_obj, N_final_obj, delta_Nstar_obj = self._grid_item
    self._compute_ref = compute_pipeline.remote(
        trajectory=self._traj_proxy,
        N_init_obj=N_init_obj,
        N_final_obj=N_final_obj,
        delta_Nstar_obj=delta_Nstar_obj,
        N_sample=self._N_sample,
        atol_obj=self._atol_obj,
        rtol_obj=self._rtol_obj,
        dm=self._dm,
        cosmo=self._cosmo,
        C_threshold=self._C_threshold,
        C_bar_threshold=self._C_bar_threshold,
        label=label,
        verbose=verbose,
    )
    return self._compute_ref
```

**`store(self) -> None`**:

Called by `RayWorkPool`'s store_handler after `compute()` resolves.
Resolves the Ray future, reconstructs all three in-memory objects, and
runs the integrity check.

```python
def store(self) -> None:
    if self._compute_ref is None:
        raise RuntimeError("store() called but no compute() is in progress")
    data = ray.get(self._compute_ref)
    self._compute_ref = None

    _, N_init_obj, N_final_obj, delta_Nstar_obj = self._grid_item

    # -- Reconstruct FullInstanton in memory
    self._fi = FullInstanton(
        store_id=None, trajectory=self._traj_proxy,
        N_init=N_init_obj, N_final=N_final_obj,
        delta_Nstar=delta_Nstar_obj, N_sample=self._N_sample,
        atol=self._atol_obj, rtol=self._rtol_obj,
        diffusion_model=self._dm,
    )
    self._fi._populate_from_result(data["fi_data"])

    # -- Integrity check: if fi existed as a scalars-only row, compare
    if self._fi_existing is not None and self._fi_existing.available:
        _check_scalar_integrity("FullInstanton", self._fi_existing, data["fi_data"])

    # -- Reconstruct SlowRollInstanton in memory
    self._sri = SlowRollInstanton(
        store_id=None, trajectory=self._traj_proxy,
        N_init=N_init_obj, N_final=N_final_obj,
        delta_Nstar=delta_Nstar_obj, N_sample=self._N_sample,
        atol=self._atol_obj, rtol=self._rtol_obj,
        diffusion_model=self._dm,
    )
    self._sri._populate_from_result(data["sri_data"])

    if self._sri_existing is not None and self._sri_existing.available:
        _check_scalar_integrity("SlowRollInstanton", self._sri_existing, data["sri_data"])

    # -- Reconstruct CompactionFunction in memory.
    # fi_proxy / sri_proxy are constructed below only for the CF constructor;
    # they are transient (no store_id yet) and are not put into Ray object store.
    fi_proxy  = FullInstantonProxy(self._fi)  if not self._fi.failure  else None
    sri_proxy = SlowRollInstantonProxy(self._sri) if not self._sri.failure else None

    if fi_proxy is None and sri_proxy is None:
        # Both branches failed — CF will be a failure row too.
        pass  # cf remains None; handled in persist step

    self._cf = CompactionFunction(
        store_id=None,
        full_instanton=fi_proxy,
        slow_roll_instanton=sri_proxy,
        trajectory=self._traj_proxy,
        cosmo=self._cosmo,
        delta_Nstar=delta_Nstar_obj,
        C_threshold=self._C_threshold,
        C_bar_threshold=self._C_bar_threshold,
        atol=self._atol_obj,
        rtol=self._rtol_obj,
    )
    self._cf._cosmo_store_id = self._cosmo.store_id
    self._cf._populate_from_result({
        "full":      data["full"],
        "slow_roll": data["slow_roll"],
    })
```

**Note on `FullInstantonProxy(self._fi)` without a `store_id`:**
`FullInstantonProxy.__init__` does `ray.put(model)`, which serialises the
whole `FullInstanton` into the Ray object store. This works even when
`model.store_id is None` — it's used here only to carry the in-memory
populated `_values` into the `CompactionFunction` constructor, not for
database routing. However, if this creates unacceptable memory pressure
(full instanton values being copied into the Ray object store for every
pipeline item), a lighter alternative is to set `fi.available`-related
attributes temporarily for the CF constructor call and avoid creating a
proxy at all — see the architecture note about bypassing the proxy pathway
in `_compute_instanton_path`. Inspect `CompactionFunction.__init__` to see
exactly how it uses `full_instanton` and `slow_roll_instanton`, and decide
whether a proxy is actually needed here or whether passing None and later
setting internal attributes directly is cleaner.

## Acceptance criteria

- [ ] `ComputeTargets/pipeline.py` exists and is importable.
- [ ] `_check_scalar_integrity` raises `RuntimeError` with a clear message
      when relative error exceeds `PIPELINE_SCALAR_INTEGRITY_RTOL` — unit
      tested for:
      - matching scalars (no raise)
      - mismatched `msr_action` (raises)
      - mismatched `N_total` (raises)
      - fresh compute failure (`fresh_data["failure"] = True`) → no raise
        regardless of stored values
      - stored value `None` (existing row was a failure) → no raise
- [ ] `PipelineWorkItem.available` always returns `False`.
- [ ] `PipelineWorkItem.compute()` raises if called twice without an
      intervening `store()`.
- [ ] `PipelineWorkItem.store()` raises if called without a prior
      `compute()`.
- [ ] `PipelineWorkItem.store()` calls `_check_scalar_integrity` for fi when
      `fi_existing` is available, and for sri when `sri_existing` is
      available — unit-tested with synthetic `fi_existing`/`sri_existing`
      mocks (no Ray needed).
- [ ] `compute_pipeline` is importable and has `num_cpus=0` in its remote
      decorator (inspect `compute_pipeline.remote.__self__.num_cpus` or
      equivalent, or verify via `compute_pipeline._function_descriptor`).
- [ ] `git diff` touches only `ComputeTargets/pipeline.py` (new) and test
      files. `main.py`, all factory files, and all other compute-target
      files are untouched.
- [ ] A `@pytest.mark.integration` test dispatches `compute_pipeline.remote`
      against a real InflatonTrajectory (using the live_pool fixture from
      `tests/conftest.py`) for one small `(N_init, N_final, delta_Nstar)`
      triple, and asserts:
      - return dict contains keys `fi_data`, `sri_data`, `full`,
        `slow_roll`
      - at least one of `full`/`slow_roll` is not `None` (i.e., at least
        one CF branch succeeded)
      - `fi_data["failure"]` is a bool (not absent)
      If setting up a real InflatonTrajectory in the test fixture is
      disproportionately complex (e.g., requires spinning up the full Stage
      1 pipeline), document why and skip the integration test with a clear
      comment — the end-to-end test will come naturally in Prompt 8. Do not
      silently omit it.

## Out of scope (do not attempt in this prompt)

- Any changes to `main.py` — that is Prompt 8.
- The `--no-store-values` CLI flag — Prompt 8.
- A `_run_pipeline_queue` function in `main.py` — Prompt 8.
- `pool.object_store` calls for fi/sri/cf — those belong in the
  persist/validation handlers wired up in Prompt 8.
- The `_store_full_values` flag interaction with the pipeline persist step
  — Prompt 8.

## Commit

One commit, message along the lines of:
`ComputeTargets: add compute_pipeline remote function and PipelineWorkItem`
