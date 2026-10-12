# `RayWorkPool` in StochasticInstantons (SI) at `7bb3efd`

- **Repository:** `/Users/ds283/Documents/Code/StochasticInstantons`, read through `git` only.
- **Commit:** `7bb3efd0d0a9cc1c367b7848e27fa8b548a76bf7`.
- **Verdicts by:** `raypoolkit 0.2.0`, its own constructor.
- **Files:** 363 tracked; 193 `.py` files outside `RayTools/` parsed; 0 did not parse; 1 binary, not searched; 0 datastores, not read.
- **`ray.is_initialized()` after the verdicts:** False.

## `RayTools/` at the commit

| File | Blob |
|---|---|
| `RayTools/RayWorkPool.py` | `92be5b2c9e4c2c65695078bd1b8f97db2f56c7b0` |
| `RayTools/__init__.py` | `e69de29bb2d1d6434b8b29ae775ad8c2e48c5391` |

## Totals

| Measure | Count |
|---|---|
| Imports of a `RayTools` module | 3 (module level 3, nested 0) |
| … naming a private name | 1 |
| String literals naming `RayTools` | 0 |
| `import_module` / `__import__` calls naming `RayTools` | 0 |
| `RayWorkPool(...)` calls | 16 |
| … no compute handler (`compute_handler=None`) | 12 |
| … compute handler given | 4 |
| … compute handler left at its default | 0 |
| … `store_results=True` | 11 |
| … with a `title` keyword | 16 (`title=None` 10, set 6) |
| … positional arguments | 2 at 16 |
| … with `*args` / `**kwargs` | 0 / 0 |
| Verdicts | `constructs` 16 |
| Calls with a flag / flags | 4 / 5 |
| Lines of non-`.py` files naming `RayTools` or `RayWorkPool` | 89 |
| Test modules naming `RayTools` or `RayWorkPool` | 0 |

## The handler keywords, by spelling

Each handler keyword as absent (—), `None` or set; a row per spelling, with its calls.

| `compute_handler` | `store_handler` | `persist_handler` | `available_handler` | `validation_handler` | `post_handler` | `label_builder` | Calls |
|---|---|---|---|---|---|---|---|
| None | None | None | None | None | None | None | 2 |
| None | None | None | — | None | — | — | 10 |
| set | set | set | — | set | — | set | 4 |

## Imports of a `RayTools` module (3)

| File:line | Scope | Statement | Private names |
|---|---|---|---|
| `main.py:45` | `(module)` | `from RayTools.RayWorkPool import RayWorkPool, _default_store_handler` | `_default_store_handler` |
| `plot_GradientCoupledSolutions.py:100` | `(module)` | `from RayTools.RayWorkPool import RayWorkPool` | — |
| `plot_InstantonSolutions.py:72` | `(module)` | `from RayTools.RayWorkPool import RayWorkPool` | — |

## String literals naming `RayTools` (0)

None.

## `import_module` / `__import__` calls naming `RayTools` (0)

None.

## `RayWorkPool(...)` calls (16)

Each call at the line of its name. Handlers: absent (—), `None` or set. Sizes: the source text of each size keyword given. `results`: `store_results`. Verdict: `v0.2.0`'s constructor, given the classes.

| File:line | Scope | Pos. | `**` | compute | store | persist | available | validation | post | label | Sizes | `results` | Title | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `main.py:221` | `_run_pipeline_queue` | 2 | — | None | None | None | — | None | — | — | `create_batch_size=20`, `process_batch_size=20` | True | None | `constructs` |
| `main.py:249` | `_run_pipeline_queue` | 2 | — | None | None | None | — | None | — | — | `create_batch_size=20`, `process_batch_size=20` | True | None | `constructs` |
| `main.py:316` | `_run_pipeline_queue` | 2 | — | None | None | None | — | None | — | — | `create_batch_size=20`, `process_batch_size=20` | True | None | `constructs` |
| `main.py:383` | `_run_pipeline_queue` | 2 | — | set | set | set | — | set | — | set | `create_batch_size=5`, `process_batch_size=3`, `max_task_queue=MAX_INFLIGHT_PIPELINE_UNIFIED` **flagged** | False | set | `constructs` |
| `main.py:445` | `_run_instanton_queue` | 2 | — | None | None | None | — | None | — | — | `create_batch_size=20`, `process_batch_size=20` | True | None | `constructs` |
| `main.py:492` | `_run_instanton_queue` | 2 | — | set | set | set | — | set | — | set | `create_batch_size=5`, `process_batch_size=3`, `max_task_queue=MAX_INFLIGHT_PIPELINE` **flagged** | False | set | `constructs` |
| `main.py:589` | `_run_gradient_branch` | 2 | — | None | None | None | — | None | — | — | `create_batch_size=20`, `process_batch_size=20` | True | None | `constructs` |
| `main.py:718` | `run_all_pipelines` | 2 | — | set | set | set | — | set | — | set | `create_batch_size=len(traj_payloads)` **flagged**, `process_batch_size=len(traj_payloads)` **flagged** | True | set | `constructs` |
| `main.py:871` | `run_all_pipelines._run_homogeneous_branch` | 2 | — | None | None | None | — | None | — | — | `create_batch_size=20`, `process_batch_size=20` | True | None | `constructs` |
| `main.py:900` | `run_all_pipelines._run_homogeneous_branch` | 2 | — | None | None | None | — | None | — | — | `create_batch_size=20`, `process_batch_size=20` | True | None | `constructs` |
| `main.py:964` | `run_all_pipelines._run_homogeneous_branch` | 2 | — | None | None | None | — | None | — | — | `create_batch_size=20`, `process_batch_size=20` | True | None | `constructs` |
| `main.py:1015` | `run_all_pipelines._run_homogeneous_branch` | 2 | — | None | None | None | — | None | — | — | `create_batch_size=20`, `process_batch_size=20` | True | None | `constructs` |
| `main.py:1041` | `run_all_pipelines._run_homogeneous_branch` | 2 | — | None | None | None | — | None | — | — | `create_batch_size=20`, `process_batch_size=20` | True | None | `constructs` |
| `main.py:1092` | `run_all_pipelines._run_homogeneous_branch` | 2 | — | set | set | set | — | set | — | set | `create_batch_size=5`, `process_batch_size=3`, `max_task_queue=MAX_INFLIGHT_PIPELINE` **flagged** | False | set | `constructs` |
| `plot_GradientCoupledSolutions.py:938` | `run_plots` | 2 | — | None | None | None | None | None | None | None | `create_batch_size=10`, `process_batch_size=10` | False | set | `constructs` |
| `plot_InstantonSolutions.py:1171` | `run_plots` | 2 | — | None | None | None | None | None | None | None | `create_batch_size=10`, `process_batch_size=10` | False | set | `constructs` |

## Calls with a compute path: the handlers given (4)

The source text of each handler keyword given, at each call whose compute handler is given or left at its default.

| File:line | `compute_handler` | `store_handler` | `persist_handler` | `available_handler` | `validation_handler` | `post_handler` | `label_builder` |
|---|---|---|---|---|---|---|---|
| `main.py:383` | `lambda obj, **kw: obj.compute(**kw)` | `pipeline_store_handler` | `pipeline_persist_handler` | — | `lambda obj: pool.object_validate(obj)` | — | `lambda obj: f"Pipeline(dNstar={float(obj.delta_Nstar):.4g})"` |
| `main.py:492` | `lambda obj, **kwargs: obj.compute(**kwargs)` | `store_handler` | `persist_handler` | — | `lambda obj: pool.object_validate(obj)` | — | `label_builder` |
| `main.py:718` | `lambda obj, **kwargs: obj.compute(**kwargs)` | `inflaton_trajectory_store_handler` | `lambda obj, pool: pool.object_store(obj)` | — | `lambda obj: pool.object_validate(obj)` | — | `lambda obj: "InflatonTrajectory"` |
| `main.py:1092` | `lambda obj, **kwargs: obj.compute(**kwargs)` | `_default_store_handler` | `lambda obj, pool: pool.object_store(obj)` | — | `lambda obj: pool.object_validate(obj)` | — | `lambda obj: ( f"CompactionFunction(dNstar={float(obj.delta_Nstar):.4g})" )` |

## Flags (5, on 4 calls)

| Call | Keyword line | Flag |
|---|---|---|
| `main.py:383` | `:396` | `max_task_queue=MAX_INFLIGHT_PIPELINE_UNIFIED is not a literal; replaced by 1` |
| `main.py:492` | `:505` | `max_task_queue=MAX_INFLIGHT_PIPELINE is not a literal; replaced by 1` |
| `main.py:718` | `:729` | `create_batch_size=len(traj_payloads) is not a literal; replaced by 1` |
| `main.py:718` | `:730` | `process_batch_size=len(traj_payloads) is not a literal; replaced by 1` |
| `main.py:1092` | `:1107` | `max_task_queue=MAX_INFLIGHT_PIPELINE is not a literal; replaced by 1` |

## Notification keywords, by source text (2 calls; never passed)

| File:line | Keywords |
|---|---|
| `plot_GradientCoupledSolutions.py:938` | `notify_batch_size=50`, `notify_time_interval=120` |
| `plot_InstantonSolutions.py:1171` | `notify_batch_size=50`, `notify_time_interval=120` |

## Non-`.py` files naming `RayTools` or `RayWorkPool` (89 lines)

| Top directory | Lines | Files |
|---|---|---|
| `.claude/` | 17 | 3 |
| `.documents/` | 44 | 8 |
| `.prompts/` | 27 | 8 |
| `CLAUDE.md` | 1 | 1 |

Each line outside the campaign records (`prompts/`, `.prompts/`), 62:

```text
.claude/rules/compute-targets.md:105: logging. `RayWorkPool` supplies it via `label_builder` if one is configured.
.claude/rules/datastore-factories.md:13: This is the most important rule in this file. Violating it causes `RayWorkPool`
.claude/rules/datastore-factories.md:23: Note: `RayWorkPool` has three distinct handler slots — `store_handler` (calls
.claude/rules/datastore-factories.md:42: # Not found — return UNPOPULATED object; RayWorkPool will call compute()
.claude/rules/datastore-factories.md:113: guaranteed by the `store_handler` step in `RayWorkPool`, which runs before
.claude/rules/datastore-factories.md:223: and `validated = True`. This flag is used by `RayWorkPool` for the initial
.claude/rules/ray-dispatch.md:58: """Must return an ObjectRef. RayWorkPool waits on this."""
.claude/rules/ray-dispatch.md:65: """Called on the DRIVER by RayWorkPool after compute() resolves.
.claude/rules/ray-dispatch.md:99: ## Why `RayWorkPool` requires plain classes
.claude/rules/ray-dispatch.md:101: `RayTools/RayWorkPool.py` accesses compute targets as plain Python objects:
.claude/rules/ray-dispatch.md:106: return an `ObjectRef`; `RayWorkPool` never calls `.remote()` on it
.claude/rules/ray-dispatch.md:116: class Foo(DatastoreObject):          # NEVER — breaks RayWorkPool
.claude/rules/ray-dispatch.md:214: The custom handler must be wired in explicitly at the `RayWorkPool` call site
.claude/rules/ray-dispatch.md:229: O(grid_size). Run this inside a `RayWorkPool` with large batch sizes
.claude/rules/ray-dispatch.md:236: Feed only the missing items into a second `RayWorkPool` with a conservative
.claude/rules/ray-dispatch.md:237: `max_task_queue` (e.g. 20). `RayWorkPool`'s main loop guards task creation
.claude/rules/ray-dispatch.md:245: `RayWorkPool`. This overlaps queries with compute, but has two drawbacks that
.documents/FILE_MAP.md:31: | `RayTools_RayWorkPool.py` | `RayTools/RayWorkPool.py` | `RayWorkPool` class: the core distributed work-queue abstraction; manages the **lookup → compute → store → persist → validate** state machine over a list of compute targets using `ray.wait()`; provides `create_batch_size`, `process_batch_size`, `max_task_queue` controls |
.documents/FILE_MAP.md:287: | `RayTools/` (other files)                               | Only `RayWorkPool.py` is directly relevant                                  |
.documents/INFRASTRUCTURE.md:1: # INFRASTRUCTURE — how `Datastore`, `ShardedPool`, and `RayWorkPool` work
.documents/INFRASTRUCTURE.md:4: (`Datastore`) and distributed dispatch (`RayWorkPool`). It does not cover the
.documents/INFRASTRUCTURE.md:46: `RayWorkPool` uses to decide whether a grid point needs computing at all.
.documents/INFRASTRUCTURE.md:128: is exactly the signal `RayWorkPool` needs to decide computation is required.
.documents/INFRASTRUCTURE.md:286: **Why `Foo` must stay a plain class:** `RayWorkPool` accesses compute targets
.documents/INFRASTRUCTURE.md:289: *return* an `ObjectRef` rather than `RayWorkPool` calling `.remote()` on
.documents/INFRASTRUCTURE.md:346: handler is wired explicitly at the `RayWorkPool` call site — never hidden
.documents/INFRASTRUCTURE.md:351: ## 9. `RayWorkPool` — the distributed work-queue
.documents/INFRASTRUCTURE.md:353: `RayTools/RayWorkPool.py` drives every compute stage through five states:
.documents/INFRASTRUCTURE.md:357: RayWorkPool(
.documents/INFRASTRUCTURE.md:411: `RayWorkPool`, with a conservative `max_task_queue` (e.g. 20). Because
.documents/INFRASTRUCTURE.md:412: `RayWorkPool`'s own loop already caps in-flight tasks, no separate manual
.documents/INFRASTRUCTURE.md:418: `RayWorkPool`. That approach overlaps queries with compute but has two
.documents/INFRASTRUCTURE.md:452: MISS path, inside RayWorkPool:
.documents/INFRASTRUCTURE.md:478: RayWorkPool over compute_list:
.documents/architecture-summary.md:27: RayTools/
.documents/architecture-summary.md:28: RayWorkPool.py               — distributed work-queue abstraction
.documents/architecture-summary.md:172: persisted. `RayWorkPool` reads this property directly.
.documents/architecture-summary.md:188: which signals to `RayWorkPool` that computation is needed.
.documents/architecture-summary.md:245: **Why `Foo` must be a plain class:** `RayWorkPool` accesses compute targets as
.documents/architecture-summary.md:319: ## RayWorkPool
.documents/architecture-summary.md:321: `RayTools/RayWorkPool.py` provides the main distributed work-queue abstraction.
.documents/architecture-summary.md:328: RayWorkPool(
.documents/architecture-summary.md:349: `RayWorkPool.run()` drives a state machine over all in-flight `ObjectRef`s:
.documents/architecture-summary.md:419: One `RayWorkPool` runs over all `(model, phi0, pi0, potential)` combinations.
.documents/architecture-summary.md:482: RayWorkPool(
.documents/architecture-summary.md:518: MISS path in RayWorkPool:
.documents/architecture-summary.md:556: RayWorkPool:
.documents/gradient-coupled-instanton/24-prerequisite-wallclock-safeguard.md:75: the Ray dispatch layer, and `RayTools/RayWorkPool.py` is protected
.documents/gradient-coupled-instanton/24-prerequisite-wallclock-safeguard.md:78: through the *real* `main.py`/`RayWorkPool` pipeline (per the prompt's own
.documents/gradient-coupled-instanton/24-prerequisite-wallclock-safeguard.md:86: driver that bypasses `RayWorkPool` and dispatches
.documents/gradient-coupled-plotting/DESIGN_gradient_coupled_plotting.md:65: dispatch.py          # RayWorkPool wiring, generic _render_item wrapper,
.documents/gradient-coupled-plotting/DESIGN_gradient_coupled_plotting.md:336: the terminal `RayWorkPool(..., store_results=False)` drain stay exactly as they
.documents/gradient-coupled-plotting/PROMPT_AUTHORING_BRIEF.md:209: `RayWorkPool(..., store_results=False)` drain must be preserved exactly.
.documents/handoff-notes/2026-10-08/summary-E-june-pipeline.md:4: `2026-06-14_Codebase-evaluation-and-refactoring-strategy.md`, `2026-06-16_Inflaton-trajectory-sampling-and-database-storage-strategy.md`, `2026-06-16_InflatonTrajectory-validation-failure-diagnosis.md`, `2026-06-16_Refactoring-plotting-scripts-for-RayWorkPool-integration.md`, `2026-06-16_Converting-instanton-trajectories-to-primordial-black-hole-d.md`, `2026-06-21_Enhancing-instanton-solution-plot-styling-and-metadata.md`, `2026-06-21_Radial-density-profile-and-compaction-function-analysis.md`, `2026-06-22_Ray-failure-mode-identification.md`, `2026-06-22_DOE-meaning-in-project-context.md`.
.documents/handoff-notes/2026-10-08/summary-E-june-pipeline.md:20: **14 Jun 20:46.** David's brief (reproduced verbatim as `.prompts/base-implementation/01-initial.md`): reuse ChamPBH's three layers — `RayWorkPool`, `Datastore`/`ShardedPool`, the lookup–compute–store "unit of work"; single-field scope but "build the code in such a way that the extensions of multiple field models is considered from the beginning"; no slow-roll approximation, state `(φ, π=dφ/dN)` doubled by MSR response fields `P₁, P₂`; the compaction-function pipeline sketch (end-of-inflation surface fixes `k_end`; at each step "only the core region continues on the instanton; the outer region detaches"). **Recorded** (01-initial.md).
.documents/handoff-notes/2026-10-08/summary-E-june-pipeline.md:22: **14 Jun 20:47 — Claude's keep/drop evaluation.** Keep: `RayWorkPool`, `ShardedPool`/`Datastore`/`SerialPoolBroker`, `DatastoreObject`, Dimensionless/Dimensionful quantities and factories, `tolerance`/`version`/`store_tag`, `IntegrationSupervisor`/`RHS_timer`, `phi_value`/`pi_value`. Drop: `ConformalCouplings/`, `QCD_Cosmology`, chameleon `StateVector`/`ODEPolicy`, `ScalarModel*`, `AdiabaticHistory`, `BBNData`, `redshift`/`temperature` as time coordinate (replaced by `efold_value`/`efold_array`). Also flagged: `main.py` bug `allowed_drop_actions` undefined (neutralised by hollowing out `main.py`). **Recorded** only at the level of the resulting layout (architecture-summary "Repository layout", CLAUDE.md protected list); the keep/drop *reasoning* and the ChamPBH→instanton correspondence table (e.g. `CompactionFunction` "analogous to `AdiabaticHistory`", `PBHMassFunction` "analogous to `BBNData`") are **NOT recorded**.
.documents/handoff-notes/2026-10-08/summary-E-june-pipeline.md:32: **15 Jun 11:26–12:25 — the `@ray.remote`-on-classes incident.** Claude Code had decorated `InflatonTrajectory` as a Ray actor and used `Foo.__ray_actor_class__(...)` in the factory; David asked why, since `ScalarModel` in ChamPBH was never an actor. Diagnosis: `RayWorkPool` reads `obj.available`, calls `obj.store()` on the driver, and expects `compute()` to return an `ObjectRef`; corrective Prompt 3.5. **Recorded** fully (ray-dispatch.md, datastore-factories.md, CLAUDE.md rule 1).
.documents/handoff-notes/2026-10-08/summary-E-june-pipeline.md:42: ### 16 June — sampling strategy, `RayWorkPool` handlers, time convention
.documents/handoff-notes/2026-10-08/summary-E-june-pipeline.md:48: **16 Jun 10:15–10:29 — backpressure.** Claude's draft left `main.py` driving Ray manually; David: `RayWorkPool` "is supposed to be the abstraction for work queue management. We don't want to submit all tasks to Ray simultaneously otherwise it gets overwhelmed"; a lookup queue then a work queue, as in ChamPBH. David also refused to defer the custom store handler ("The whole point of this refactoring is that `InflatonTrajectory` needs to mint the `efold_value` objects"). **Recorded** (two-pass dispatch in ray-dispatch.md and INFRASTRUCTURE §10, with the grouper-batch comparison).
.documents/handoff-notes/2026-10-08/summary-E-june-pipeline.md:54: **16 Jun 11:39–11:58 — plotting refactor.** `plot_InstantonSolutions.py` must go through `RayWorkPool` "to prevent the machine on which the plotting code is running from being overwhelmed"; `read_table` on sharded tables is forbidden (reads one shard); fetch per-item via `object_get` keyed by `delta_Nstar`; `read_table_config` extended by David to `delta_Nstar`, `efold_value`, `inflaton_mass`, `quartic_coupling`, `phi_value`, `pi_value`. **Recorded** (pool-read-apis.md).
.documents/handoff-notes/2026-10-08/summary-F-june-science.md:15: *Design decisions (all recorded).* Step-1 N_final-decoupling test; Sobol/LHC in (δN★, ΔN) with coarse N_final; GP regressor on the signed distance C̄_max − 0.4 rather than a classifier; scalars-only storage; Sobol indices on the surrogate. David rejected weighting-down extrapolated points: the extrapolation "is done using an exact analytic formula and should be reliable". David proposed the unified single-`RayWorkPool` pipeline (prompts 6–8) after noticing the two-pass architecture made `set_store_full_values(False)` unsafe. David set the integrity rule: a recompute whose scalars disagree with a stored row "is an integrity failure and shouldn't happen ... we would raise an exception" (`PIPELINE_SCALAR_INTEGRITY_RTOL = 1e-4`). Footer provenance `[summary-only]` added after David could not tell the two smoke-test runs apart. Output: prompts 01–10 and `handoff-sparse-sampling.md`.
CLAUDE.md:95: RayTools/                          Datastore/SQL/ShardedPool.py
```

## Test modules naming `RayTools` or `RayWorkPool` (0)

None.

## Files that do not parse (0)

None.
