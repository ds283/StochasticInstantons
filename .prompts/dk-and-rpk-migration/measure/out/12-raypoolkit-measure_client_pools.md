# `RayWorkPool` in StochasticInstantons (SI) at `47c0a77`

- **Repository:** `/Users/ds283/Documents/Code/StochasticInstantons`, read through `git` only.
- **Commit:** `47c0a77a37295ee4eca960a553d293b9bd1ff4df`.
- **Verdicts by:** `raypoolkit 0.2.0`, its own constructor.
- **Files:** 505 tracked; 203 `.py` files outside `RayTools/` parsed; 0 did not parse; 1 binary, not searched; 0 datastores, not read.
- **`ray.is_initialized()` after the verdicts:** False.

## `RayTools/` at the commit

| File | Blob |
|---|---|

## Totals

| Measure | Count |
|---|---|
| Imports of a `RayTools` module | 0 (module level 0, nested 0) |
| … naming a private name | 0 |
| String literals naming `RayTools` | 2 |
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
| Lines of non-`.py` files naming `RayTools` or `RayWorkPool` | 421 |
| Test modules naming `RayTools` or `RayWorkPool` | 1 |

## The handler keywords, by spelling

Each handler keyword as absent (—), `None` or set; a row per spelling, with its calls.

| `compute_handler` | `store_handler` | `persist_handler` | `available_handler` | `validation_handler` | `post_handler` | `label_builder` | Calls |
|---|---|---|---|---|---|---|---|
| None | None | None | None | None | None | None | 2 |
| None | None | None | — | None | — | — | 10 |
| set | — | set | — | set | — | set | 2 |
| set | set | set | — | set | — | set | 2 |

## Imports of a `RayTools` module (0)

None.

## String literals naming `RayTools` (2)

```text
.documents/dk-and-rpk-migration/rehearsal/stage_counts.py:16 [(module)] "\nEach pipeline stage's work-item counts from a main.py log, without the rates or times\n(dk-and-rpk-migration README section 4.1, L2 and L4). Written for dk-a
tests/test_rehearsal_stage_counts.py:16 [(module)] "\nThe rehearsal log parser `.documents/dk-and-rpk-migration/rehearsal/stage_counts.py`\n(dk-and-rpk-migration prompt 01, item T3).\n\n**The fixtures are built 
```

## `import_module` / `__import__` calls naming `RayTools` (0)

None.

## `RayWorkPool(...)` calls (16)

Each call at the line of its name. Handlers: absent (—), `None` or set. Sizes: the source text of each size keyword given. `results`: `store_results`. Verdict: `v0.2.0`'s constructor, given the classes.

| File:line | Scope | Pos. | `**` | compute | store | persist | available | validation | post | label | Sizes | `results` | Title | Verdict |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| `main.py:255` | `_run_pipeline_queue` | 2 | — | None | None | None | — | None | — | — | `create_batch_size=20`, `process_batch_size=20` | True | None | `constructs` |
| `main.py:283` | `_run_pipeline_queue` | 2 | — | None | None | None | — | None | — | — | `create_batch_size=20`, `process_batch_size=20` | True | None | `constructs` |
| `main.py:350` | `_run_pipeline_queue` | 2 | — | None | None | None | — | None | — | — | `create_batch_size=20`, `process_batch_size=20` | True | None | `constructs` |
| `main.py:417` | `_run_pipeline_queue` | 2 | — | set | set | set | — | set | — | set | `create_batch_size=5`, `process_batch_size=3`, `max_task_queue=MAX_INFLIGHT_PIPELINE_UNIFIED` **flagged** | False | set | `constructs` |
| `main.py:478` | `_run_instanton_queue` | 2 | — | None | None | None | — | None | — | — | `create_batch_size=20`, `process_batch_size=20` | True | None | `constructs` |
| `main.py:525` | `_run_instanton_queue` | 2 | — | set | — | set | — | set | — | set | `create_batch_size=5`, `process_batch_size=3`, `max_task_queue=MAX_INFLIGHT_PIPELINE` **flagged** | False | set | `constructs` |
| `main.py:621` | `_run_gradient_branch` | 2 | — | None | None | None | — | None | — | — | `create_batch_size=20`, `process_batch_size=20` | True | None | `constructs` |
| `main.py:749` | `run_all_pipelines` | 2 | — | set | set | set | — | set | — | set | `create_batch_size=len(traj_payloads)` **flagged**, `process_batch_size=len(traj_payloads)` **flagged** | True | set | `constructs` |
| `main.py:900` | `run_all_pipelines._run_homogeneous_branch` | 2 | — | None | None | None | — | None | — | — | `create_batch_size=20`, `process_batch_size=20` | True | None | `constructs` |
| `main.py:929` | `run_all_pipelines._run_homogeneous_branch` | 2 | — | None | None | None | — | None | — | — | `create_batch_size=20`, `process_batch_size=20` | True | None | `constructs` |
| `main.py:993` | `run_all_pipelines._run_homogeneous_branch` | 2 | — | None | None | None | — | None | — | — | `create_batch_size=20`, `process_batch_size=20` | True | None | `constructs` |
| `main.py:1044` | `run_all_pipelines._run_homogeneous_branch` | 2 | — | None | None | None | — | None | — | — | `create_batch_size=20`, `process_batch_size=20` | True | None | `constructs` |
| `main.py:1070` | `run_all_pipelines._run_homogeneous_branch` | 2 | — | None | None | None | — | None | — | — | `create_batch_size=20`, `process_batch_size=20` | True | None | `constructs` |
| `main.py:1121` | `run_all_pipelines._run_homogeneous_branch` | 2 | — | set | — | set | — | set | — | set | `create_batch_size=5`, `process_batch_size=3`, `max_task_queue=MAX_INFLIGHT_PIPELINE` **flagged** | False | set | `constructs` |
| `plot_GradientCoupledSolutions.py:939` | `run_plots` | 2 | — | None | None | None | None | None | None | None | `create_batch_size=10`, `process_batch_size=10` | False | set | `constructs` |
| `plot_InstantonSolutions.py:1173` | `run_plots` | 2 | — | None | None | None | None | None | None | None | `create_batch_size=10`, `process_batch_size=10` | False | set | `constructs` |

## Calls with a compute path: the handlers given (4)

The source text of each handler keyword given, at each call whose compute handler is given or left at its default.

| File:line | `compute_handler` | `store_handler` | `persist_handler` | `available_handler` | `validation_handler` | `post_handler` | `label_builder` |
|---|---|---|---|---|---|---|---|
| `main.py:417` | `lambda obj, **kw: obj.compute(**kw)` | `pipeline_store_handler` | `pipeline_persist_handler` | — | `lambda obj: pool.object_validate(obj)` | — | `lambda obj: f"Pipeline(dNstar={float(obj.delta_Nstar):.4g})"` |
| `main.py:525` | `lambda obj, **kwargs: obj.compute(**kwargs)` | — | `persist_handler` | — | `lambda obj: pool.object_validate(obj)` | — | `label_builder` |
| `main.py:749` | `lambda obj, **kwargs: obj.compute(**kwargs)` | `inflaton_trajectory_store_handler` | `lambda obj, pool: pool.object_store(obj)` | — | `lambda obj: pool.object_validate(obj)` | — | `lambda obj: "InflatonTrajectory"` |
| `main.py:1121` | `lambda obj, **kwargs: obj.compute(**kwargs)` | — | `lambda obj, pool: pool.object_store(obj)` | — | `lambda obj: pool.object_validate(obj)` | — | `lambda obj: ( f"CompactionFunction(dNstar={float(obj.delta_Nstar):.4g})" )` |

## Flags (5, on 4 calls)

| Call | Keyword line | Flag |
|---|---|---|
| `main.py:417` | `:430` | `max_task_queue=MAX_INFLIGHT_PIPELINE_UNIFIED is not a literal; replaced by 1` |
| `main.py:525` | `:537` | `max_task_queue=MAX_INFLIGHT_PIPELINE is not a literal; replaced by 1` |
| `main.py:749` | `:760` | `create_batch_size=len(traj_payloads) is not a literal; replaced by 1` |
| `main.py:749` | `:761` | `process_batch_size=len(traj_payloads) is not a literal; replaced by 1` |
| `main.py:1121` | `:1135` | `max_task_queue=MAX_INFLIGHT_PIPELINE is not a literal; replaced by 1` |

## Notification keywords, by source text (2 calls; never passed)

| File:line | Keywords |
|---|---|
| `plot_GradientCoupledSolutions.py:939` | `notify_batch_size=50`, `notify_time_interval=120` |
| `plot_InstantonSolutions.py:1173` | `notify_batch_size=50`, `notify_time_interval=120` |

## Non-`.py` files naming `RayTools` or `RayWorkPool` (421 lines)

| Top directory | Lines | Files |
|---|---|---|
| `.claude/` | 18 | 3 |
| `.documents/` | 148 | 16 |
| `.prompts/` | 255 | 26 |

Each line outside the campaign records (`prompts/`, `.prompts/`), 166:

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
.claude/rules/ray-dispatch.md:101: `raypoolkit.RayWorkPool` (the `raypoolkit` package, pinned in
.claude/rules/ray-dispatch.md:103: plain Python objects. Lines are those of `raypoolkit/RayWorkPool.py` at `v0.2.0`:
.claude/rules/ray-dispatch.md:107: — `compute()` must return an `ObjectRef`; `RayWorkPool` never calls
.claude/rules/ray-dispatch.md:122: class Foo(DatastoreObject):          # NEVER — breaks RayWorkPool
.claude/rules/ray-dispatch.md:220: The custom handler must be wired in explicitly at the `RayWorkPool` call site
.claude/rules/ray-dispatch.md:235: O(grid_size). Run this inside a `RayWorkPool` with large batch sizes
.claude/rules/ray-dispatch.md:242: Feed only the missing items into a second `RayWorkPool` with a conservative
.claude/rules/ray-dispatch.md:243: `max_task_queue` (e.g. 20). `RayWorkPool`'s main loop guards task creation
.claude/rules/ray-dispatch.md:251: `RayWorkPool`. This overlaps queries with compute, but has two drawbacks that
.documents/FILE_MAP.md:32: | — (not a file of this repository) | `raypoolkit.RayWorkPool` | `RayWorkPool` class, from the `raypoolkit` package pinned in `requirements.txt`: the core distributed work-queue abstraction; manages the **lookup → compute → store → persist → validate** state machine over a list of compute targets using `ray.wait()`; provides `create_batch_size`, `process_batch_size`, `max_task_queue` controls |
.documents/INFRASTRUCTURE.md:1: # INFRASTRUCTURE — how `Datastore`, `ShardedPool`, and `RayWorkPool` work
.documents/INFRASTRUCTURE.md:4: (`Datastore`) and distributed dispatch (`RayWorkPool`). It does not cover the
.documents/INFRASTRUCTURE.md:46: `RayWorkPool` uses to decide whether a grid point needs computing at all.
.documents/INFRASTRUCTURE.md:128: is exactly the signal `RayWorkPool` needs to decide computation is required.
.documents/INFRASTRUCTURE.md:286: **Why `Foo` must stay a plain class:** `RayWorkPool` accesses compute targets
.documents/INFRASTRUCTURE.md:289: *return* an `ObjectRef` rather than `RayWorkPool` calling `.remote()` on
.documents/INFRASTRUCTURE.md:346: handler is wired explicitly at the `RayWorkPool` call site — never hidden
.documents/INFRASTRUCTURE.md:351: ## 9. `RayWorkPool` — the distributed work-queue
.documents/INFRASTRUCTURE.md:353: `RayWorkPool`, from the `raypoolkit` package (pinned in `requirements.txt`), drives every compute stage through five states:
.documents/INFRASTRUCTURE.md:357: RayWorkPool(
.documents/INFRASTRUCTURE.md:411: `RayWorkPool`, with a conservative `max_task_queue` (e.g. 20). Because
.documents/INFRASTRUCTURE.md:412: `RayWorkPool`'s own loop already caps in-flight tasks, no separate manual
.documents/INFRASTRUCTURE.md:418: `RayWorkPool`. That approach overlaps queries with compute but has two
.documents/INFRASTRUCTURE.md:452: MISS path, inside RayWorkPool:
.documents/INFRASTRUCTURE.md:478: RayWorkPool over compute_list:
.documents/OPEN-ISSUES.md:162: | `[pool-prose-stale-after-raypoolkit-adoption]` | board §3 (04, 2026-10-20) | dk-12 | `picard.py:450-456` still calls `RayTools/RayWorkPool.py` protected infrastructure; the constructor sketches in `INFRASTRUCTURE.md` and `architecture-summary.md` give defaults of 10, 10 and 50 where the pool's are 5, 1 and 200. |
.documents/architecture-summary.md:28: RayWorkPool                  — distributed work-queue abstraction
.documents/architecture-summary.md:172: persisted. `RayWorkPool` reads this property directly.
.documents/architecture-summary.md:188: which signals to `RayWorkPool` that computation is needed.
.documents/architecture-summary.md:245: **Why `Foo` must be a plain class:** `RayWorkPool` accesses compute targets as
.documents/architecture-summary.md:319: ## RayWorkPool
.documents/architecture-summary.md:321: `RayWorkPool`, from the `raypoolkit` package (pinned in `requirements.txt`), provides the main distributed work-queue abstraction.
.documents/architecture-summary.md:328: RayWorkPool(
.documents/architecture-summary.md:349: `RayWorkPool.run()` drives a state machine over all in-flight `ObjectRef`s:
.documents/architecture-summary.md:419: One `RayWorkPool` runs over all `(model, phi0, pi0, potential)` combinations.
.documents/architecture-summary.md:482: RayWorkPool(
.documents/architecture-summary.md:518: MISS path in RayWorkPool:
.documents/architecture-summary.md:556: RayWorkPool:
.documents/dk-and-rpk-migration/01-rehearsal-tooling-and-run-provenance.md:148: `RayWorkPool`'s `label_builder` value goes only to `compute(label=…)`
.documents/dk-and-rpk-migration/01-rehearsal-tooling-and-run-provenance.md:149: (`RayTools/RayWorkPool.py:385-391`), which passes it to the remote function for printing and never
.documents/dk-and-rpk-migration/01-rehearsal-tooling-and-run-provenance.md:309: titles of `main.py`, printed by `RayWorkPool.py:181`) with whether it completed, its
.documents/dk-and-rpk-migration/01-rehearsal-tooling-and-run-provenance.md:372: `RayTools` imports that prompt 04 rewrites keep their lines (`main.py:45`,
.documents/dk-and-rpk-migration/01-rehearsal-tooling-and-run-provenance.md:560: format of an older builder: `RayWorkPool`'s label builders never reach the column.
.documents/dk-and-rpk-migration/01-rehearsal-tooling-and-run-provenance.md:580: scripts' `RayTools` imports (`:72`, `:100`) are unchanged.
.documents/dk-and-rpk-migration/03-pin-raypoolkit-v0.2.0.md:112: | archive, outside `raypoolkit/tests/` | 4: `__init__.py`, `RayWorkPool.py`, `_timing.py`, `contract.py` |
.documents/dk-and-rpk-migration/03-pin-raypoolkit-v0.2.0.md:127: RayWorkPool; print(ray.is_initialized())"` prints `False`. No Ray was started.
.documents/dk-and-rpk-migration/03-pin-raypoolkit-v0.2.0.md:165: - **Nothing imports `raypoolkit` yet.** `RayTools/` is intact; 04 deletes it and rewrites the three
.documents/dk-and-rpk-migration/03-pin-raypoolkit-v0.2.0.md:166: imports to `from raypoolkit import RayWorkPool`. The package exports `RayWorkPool` and imports
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:3: **Subject:** Replace SI's copy of `RayWorkPool` with the packaged `raypoolkit.RayWorkPool`
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:7: `RayTools/` is gone; the three drivers import `RayWorkPool` from `raypoolkit`; `_default_store_handler`
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:19: - **W1.** `git rm RayTools/RayWorkPool.py RayTools/__init__.py`. The ignored `RayTools/__pycache__/`
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:21: `rm -r`, and then the empty `RayTools/` with `rmdir`. `ls -d RayTools` now fails and
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:22: `git ls-files RayTools` is empty.
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:24: are `from raypoolkit import RayWorkPool` (a one-line replacement each, in place; the file's
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:35: - `.claude/rules/ray-dispatch.md:99-112`, "Why `RayWorkPool` requires plain classes": it names
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:36: `raypoolkit.RayWorkPool`, pinned in `requirements.txt` and not a file of this repository, and
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:41: with `git -C RayPoolKit show v0.2.0:raypoolkit/RayWorkPool.py`. The rule's argument is unchanged.
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:43: `raypoolkit.RayWorkPool`, and says the class is from the `raypoolkit` package pinned in
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:45: `RayTools/ (other files)` is deleted (it described a directory that is gone and never held another
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:48: sentence names `RayWorkPool` "from the `raypoolkit` package (pinned in `requirements.txt`)".
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:49: - `.documents/architecture-summary.md:27-28`: the layout's `RayTools/` / `  RayWorkPool.py` become
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:50: `(raypoolkit package, pinned in requirements.txt)` / `  RayWorkPool`.
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:63: -from RayTools.RayWorkPool import RayWorkPool, _default_store_handler
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:64: +from raypoolkit import RayWorkPool
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:81: -from RayTools.RayWorkPool import RayWorkPool
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:82: +from raypoolkit import RayWorkPool
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:87: -from RayTools.RayWorkPool import RayWorkPool
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:88: +from raypoolkit import RayWorkPool
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:97: 3. **The re-measure finds 2 string literals and 1 test module naming `RayTools`**, where §2.1 and
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:102: constructs `RayTools` or `RayWorkPool`". `STRUCTURALLY REQUIRED` (correction 3).
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:111: `raypoolkit.RayWorkPool` is not a `RayTools` module). Its catch is the import-check script's
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:118: requirements.txt)`, in place of `RayTools/`, so that the tree's shape is kept and nothing is
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:130: about the surviving `RayTools/__pycache__/`). `IMPLEMENTATION CHOICE`.
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:156: | string literals naming `RayTools` | 0 | 2 | the docstrings 01 added (`84a5cfc`); deviation 3 |
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:157: | test modules naming `RayTools` or `RayWorkPool` | 0 | 1 | `tests/test_rehearsal_stage_counts.py:22`; deviation 3 |
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:168: `git grep -n -e RayTools -e _default_store_handler -- ':!.prompts' ':!.documents' ':!.claude' ':!CLAUDE.md'`
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:169: (before the change) gives 11 lines: `RayTools/RayWorkPool.py:79`, `:94`; the three imports; the four uses
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:187: RayTools/ parsed`.
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:191: | `RayTools/` table | 2 files | 2 files | **empty** |
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:192: | Imports of a `RayTools` module | 3 | 3 | **0** |
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:194: | String literals naming `RayTools` | 0 | 2 | **2** (the two docstrings, unchanged) |
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:196: | `RayWorkPool(...)` calls | 16 | 16 | **16** |
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:216: `git ls-tree db29b7ffa061e60788ebe3975ec4b45f28daed1d RayTools` prints nothing.
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:351: - lists every `RayWorkPool(...)` call's `store_handler` keyword: `None` at the 12 lookup-only sites,
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:364: # 1. every store_handler keyword on a RayWorkPool call
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:367: if isinstance(n, ast.Call) and getattr(n.func, "id", None) == "RayWorkPool":
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:371: for r in rows: print("RayWorkPool call", r)
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:403: RayWorkPool call (223, 'None')
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:404: RayWorkPool call (251, 'None')
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:405: RayWorkPool call (318, 'None')
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:406: RayWorkPool call (385, 'pipeline_store_handler')
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:407: RayWorkPool call (446, 'None')
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:408: RayWorkPool call (493, 'absent')
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:409: RayWorkPool call (589, 'None')
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:410: RayWorkPool call (717, 'inflaton_trajectory_store_handler')
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:411: RayWorkPool call (868, 'None')
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:412: RayWorkPool call (897, 'None')
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:413: RayWorkPool call (961, 'None')
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:414: RayWorkPool call (1012, 'None')
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:415: RayWorkPool call (1038, 'None')
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:416: RayWorkPool call (1089, 'absent')
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:441: RayWorkPool` for two of the three drivers; no test imports `main.py`, so its import is checked by
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:442: `ast` alone. No test imports or constructs `RayTools` or `RayWorkPool`
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:444: first through the package: it constructs no `RayWorkPool` and imports nothing from `RayTools`.
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:456: - **W5 against the package.** Every corrected statement agrees with `raypoolkit/RayWorkPool.py` at
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:457: `v0.2.0` (`git -C RayPoolKit show v0.2.0:raypoolkit/RayWorkPool.py`): `:385` is `if obj.available:`
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:479: -from raypoolkit import RayWorkPool
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:480: +from RayTools.RayWorkPool import RayWorkPool
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:484: - **Import check:** exit 1: `UNRESOLVED main.py:45  from RayTools.RayWorkPool import RayWorkPool  --
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:485: find_spec raised ModuleNotFoundError: No module named 'RayTools'`; `unresolved: 1`. (The module is
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:486: gone; no `RayTools` directory survives to make a namespace package.)
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:487: - **The script, at a throwaway commit** (`1c74186…`): `Imports of a RayTools module | 1`
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:488: (`main.py:45`, `from RayTools.RayWorkPool import RayWorkPool`, no private name); `RayTools/` table
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:501: -from raypoolkit import RayWorkPool
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:508: - The script at its throwaway commit (`a802687…`) reports 0 imports of `RayTools` (the import is of
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:524: from raypoolkit import RayWorkPool
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:525: +from raypoolkit.RayWorkPool import _default_store_handler
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:530: - **RayPoolKit's script** at its throwaway commit (`0270097…`): `Imports of a RayTools module | 0`,
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:532: `raypoolkit.RayWorkPool` is not a `RayTools` module.
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:534: `private names imported from raypoolkit: 1 [('main.py', 46, 'raypoolkit.RayWorkPool', '_default_store_handler')]`.
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:536: - **`git grep -n _default_store_handler -- main.py`:** `main.py:46:from raypoolkit.RayWorkPool import _default_store_handler`.
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:552: UNRESOLVED main.py:45  from raypoolkit import RayWorkPool  -- find_spec found nothing
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:553: UNRESOLVED plot_InstantonSolutions.py:72  from raypoolkit import RayWorkPool  -- find_spec found nothing
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:554: UNRESOLVED plot_GradientCoupledSolutions.py:100  from raypoolkit import RayWorkPool  -- find_spec found nothing
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:569: - **`picard.py:450-456`** (a July comment, `b5a3a9f`) says `RayTools/RayWorkPool.py` "is protected
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:571: SI's to protect; the substance holds (no `timeout` or `cancel` in `raypoolkit/RayWorkPool.py` at
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:581: - **The board's "Code:" line** (its header) still lists `RayTools/` among the campaign's code, as the
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:583: - **Import order.** `from raypoolkit import RayWorkPool` sits where the old line was, between
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:585: - **Dated records** naming `RayTools/RayWorkPool.py` (`gradient-coupled-instanton/24-…:75` and the rest
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:588: - **The ignored `__pycache__`** under the old `RayTools/` was removed by hand because it kept the
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:597: > 1. **`RayTools/` is gone.** `git ls-tree <commit> RayTools` is empty, and no `RayTools` directory is
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:601: >    imports of a `RayTools` module, 0 private names, 0 `import_module` / `__import__` calls, and
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:602: >    `RayTools/` empty. It reports **2 string literals** naming `RayTools`: the module docstrings of
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:606: >    The script looks only at `RayTools`, so it cannot see a private `raypoolkit` name: SI's own `ast`
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:626: - **Branch** `dk-and-rpk-migration`, `ef13445` on `9a7cb50`. Tracked changes: `RayTools/` deleted
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:630: - **The pool is the package's.** All three drivers `from raypoolkit import RayWorkPool`; the 16 sites
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:637: - **`RayTools/` is gone**, including the ignored `__pycache__`. `DatastoreKit`'s rewrite list loses
.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md:638: `RayTools/RayWorkPool.py:23` (README U1); no U12 exception is needed (09).
.documents/dk-and-rpk-migration/07-rehearse-before-the-datastore-swap.md:90: its stale `RayTools/` line references are not a finding.
.documents/dk-and-rpk-migration/07-rehearse-before-the-datastore-swap.md:693: - The pool's change (`raypoolkit` in place of `RayTools/`) moved `reference`'s window only
.documents/dk-and-rpk-migration/09-adopt-datastorekit.md:719: `Datastore` actor and `SQLAFactoryBase`, as 04 did for `RayWorkPool`; the "not included" table loses the
.documents/dk-and-rpk-migration/10-port-the-inventory.md:179: from raypoolkit import RayWorkPool
.documents/dk-and-rpk-migration/verification.md:28: SI's own layer and `RayTools/`, with neither package installed.
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
```

## Test modules naming `RayTools` or `RayWorkPool` (1)

```text
tests/test_rehearsal_stage_counts.py:22: RayTools/RayWorkPool.py (the `** TITLE` banner at :181, the progress lines at :556-566, the
```

## Files that do not parse (0)

None.
