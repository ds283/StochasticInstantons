# 09 — adopt `datastorekit`

**Subject:** SI's own datastore layer deleted; every import of it rewritten by the module map; the four
pools built by the `datastorekit` package with SI's registry and batch sizes; `--drop` groups turned into
tables and refused before Ray when not closed (U5); `--inventory` refused before Ray until 10 (P11); the
harness and the named tests rebuilt on the package; the prose this commit makes false corrected
**Commit:** `f4da58f`, on branch `dk-and-rpk-migration`, on top of `597730f`
**Date:** 2026-10-21, by Claude Opus 5.5
**Result:** **COMPLETE.** A1–A9 hold. The 7 layer modules (2,546 lines) are deleted and the two
`__init__.py` are empty; by DatastoreKit's own script at a dangling commit of the staged tree, 0 import
statements, 0 string literals and 0 `import_module` calls name a layer module (48, 0 and 3 at the gate).
By `ast`, with the module path normalised, 42 of the 48 files of §1.2 differ from the gate by their
import's module path alone (every factory, concept and compute-target module); the other 6 are the files
§1.4–§1.6 name. A two-shard store built through the package's pool has the gate's schema and RH1's
("the schemas agree"). The suites give 707 (706 passed, 1 skipped), 63 (62 passed, 1 skipped) and
`slow` 69 passed (S1's 69). Under real Ray the package's replicated prune takes 06's I6 (acceptance 4), and U3 holds
through `live_pool` for a replicated and a sharded object (acceptance 5). The six breakages are caught.
`[config-datastore-cannot-be-imported-before-the-layer]` is closed; nothing is opened. No stop condition
of the prompt's §4 was met.

Prompt: [`.prompts/dk-and-rpk-migration/09-adopt-datastorekit.md`](../../.prompts/dk-and-rpk-migration/09-adopt-datastorekit.md),
corrected by the orchestrator's brief (fourteen corrections and the facts; see Deviations). Scratch scripts
and outputs were kept outside the repository, in the session scratchpad (`agent09/`); each script that
supports a claim is described or reproduced below.

## What shipped

- **A1, the files.** Deleted with `git rm`: `Datastore/object.py` (45 lines), `Datastore/SQL/ClientPool.py`
  (230), `Datastore/SQL/Datastore.py` (716), `Datastore/SQL/ProfileAgent.py` (355),
  `Datastore/SQL/SerialPoolBroker.py` (164), `Datastore/SQL/ShardedPool.py` (1,001),
  `Datastore/SQL/ObjectFactories/base.py` (35); 2,546 lines. Their ignored `.pyc` files (9: the two
  `ClientPool` and `ShardedPool` ones under both CPython 3.13 and 3.14, and one each of the others) are
  removed. `Datastore/__init__.py` (was `from .object import DatastoreObject`) and
  `Datastore/SQL/__init__.py` (was `from .Datastore import Datastore`) are 0 bytes (P6).
  `Datastore/SQL/ObjectFactories/__init__.py` (already 0 bytes) is untouched; the factories stay.
- **A2, the imports.** 47 statements rewritten by `perl`, by exact line, module path only:
  | Module at the gate | Now | Statements |
  |---|---|---|
  | `Datastore.SQL.ObjectFactories.base` | `datastorekit.SQL.factory_base` | 24 (22 factories; the two registries, one under `TYPE_CHECKING`) |
  | `Datastore` | `datastorekit` | 12 |
  | `Datastore.object` | `datastorekit.object` | 6 |
  | `Datastore.SQL.ShardedPool` | `datastorekit.SQL.ShardedPool` | 4 (`main.py`, both plot scripts, `tests/conftest.py`) |
  | `Datastore.SQL.ProfileAgent` | `datastorekit.SQL.ProfileAgent` | 1 (`main.py`) |

  The 48th, `tests/test_compare_stores.py:944`'s `from Datastore.SQL.Datastore import _factories as
  factories`, is removed with its `try`/`except ImportError` (§1.6 item 5). The same `perl` pass rewrote
  the one import inside I6's subprocess script (`tests/test_inflaton_trajectory_prune.py:459`), which the
  script cannot see. U3's 24 timestamp sites change nothing but their module's import.
- **A3, the factories.** Each factory module's diff is its one import line (the `ast` comparison below).
- **A4, the pools.** The four constructions (`main.py`, `plot_GradientCoupledSolutions.py`,
  `plot_InstantonSolutions.py`, `tests/conftest.py`) pass `factories=factories` and
  `serial_batch_sizes=serial_batch_sizes`, imported by `from config.datastore import ...`, and neither
  `drop_actions=` nor `inventory_config=`. `main.py`'s passes `drop_tables=drop_tables`, where it had
  `drop_actions=args.drop`; the plot scripts' and `live_pool`'s pass no drop. Every other argument is as
  it was; the plot scripts stay read-write (P10). No driver imports `inventory_config` (it stays in
  `config/sharding.py` for 10). Two behaviours of the package differ from the layer's and need no change:
  a table with no batch size leases **500** serials at a time, not 5 (no SI table is without one: 05's
  results note), and `serial_batch_sizes`' `temperature` entry, which has no table (P12), is ignored.
- **A5, U5.** `config.datastore.tables_to_drop(groups)` (below); `main.py` calls it after the provenance
  print and before `ray.init`, and refuses on stderr with exit 2.
- **A6, the harness and the tests.** `live_pool` is the package's pool; four existing test modules change
  as §1.6 names; three new test modules (below).
- **A7.** `--inventory` refuses before Ray; `main.py`'s five inventory helpers and two printers are deleted
  (100 lines, `main.py:1227-1338` at the gate) with their four `pool.inventory` calls; no import was left
  unused by them alone (`ruff`, below). The prose of §1.7 is corrected (below).
- **A8.** The issue is closed on the board (§3 → §4) and in `.documents/OPEN-ISSUES.md` (§6a → §7; 60
  open, 27 closed, 2026-10-21).
- **A9.** This note, and `out/09-temp-schema.json`.

## Deviations from the prompt

1. **The board section is §5.22**, after §5.21, and the header's status line is updated (brief correction
   1). `STRUCTURALLY REQUIRED`.
2. **§2.1.3's greps found more than §0–§1 list** — the factory-module imports that stay, the layer's own
   files, docstrings and the code string of the tests §1.6 changes, `config/sharding.py`'s
   `inventory_config` and its comment — exactly as correction 2 lists; none is a stop.
   `.inventory(` was grepped as a fixed string. `STRUCTURALLY REQUIRED`.
3. **The grid-builder test reads the shard with `sqlite3` `mode=ro`**, not `live_pool.read_table`:
   `read_table_config` has no `N_init` or `N_final` entry (correction 3), and `config/sharding.py` is not
   09's. `STRUCTURALLY REQUIRED`.
4. **Breakage 2's line** is `timestamp=row_data.timestamp` (`FullInstanton.py:180`; correction 4).
   **`shard-key-assignment-bug.md`** is at the repository root (correction 5). `STRUCTURALLY REQUIRED`.
5. **§1.8's command.** `./venv/bin/python -I -c "import config.datastore"` cannot see the repository: `-I`
   ignores `PYTHONPATH` and puts neither the current directory nor the script's on `sys.path`, so it
   fails with `ModuleNotFoundError: No module named 'config'` from the root (shown below). The check was
   run twice instead: with the root on `sys.path` by `PYTHONPATH` (not isolated, from the scratch
   directory, so that the current directory is not the means), and with `-I` and the root inserted by the
   code's first statement. Both exit 0. `STRUCTURALLY REQUIRED`.
6. **The pool constructions import the two objects by name** (`from config.datastore import factories,
   serial_batch_sizes`), not as `config.datastore.factories` (§1.4's wording), in the form the drivers'
   other `config` imports take. The `ast` test accepts either form and checks the name resolves to
   `config.datastore`'s object. I6's script, which already had a different import style, uses
   `import config.datastore` and the dotted names. `IMPLEMENTATION CHOICE`.
7. **U3's acceptance test is one integration test** checking both objects (a `delta_Nstar`, then a
   `FullInstanton`), so that the integration count is 08's 62 plus one, as §2.3.4 says.
   `IMPLEMENTATION CHOICE`.
8. **`tables_to_drop` follows ChamPBH's** (its log 08, D1): the decision is `dependent_tables`' alone; the
   message names the requested groups, the tables that reference them directly, every table that must go
   with them, and the groups to add. `IMPLEMENTATION CHOICE`.
9. **One new test was wrong at first and corrected before the suites were recorded:**
   `test_tables_to_drop.py`'s check that no Ray starts asserted `ray.is_initialized()` in the pytest
   process, which an earlier test of the default run had initialised (1 failed, 705 passed). It now runs
   in a fresh process, as `test_config_datastore.py`'s does. No existing test failed at any point.
   `IMPLEMENTATION CHOICE`.
10. **The docstrings and comments of the named tests** that this commit makes false are corrected with
    them (correction 12): `test_config_datastore.py`'s module docstring, `test_inflaton_trajectory_prune.py`'s
    module docstring, its `_HOOK_FACTORIES` and inserter comments and I6's docstring and section comment,
    `test_compare_stores.py`'s `_registry()` docstring, `conftest.py`'s module and fixture docstrings, and
    `test_grid_builder_integration.py`'s test docstring. `STRUCTURALLY REQUIRED`.
11. No `UNINTENDED DRIFT`.

## Verification performed

### §2.1 — before

- `HEAD` `597730fe30f37cce9b8c4e254cd417a9dd4b62e7`; `git status --short` empty; `uptime` at 17:49 BST:
  load 5.33 8.03 15.84 (10 CPUs). `RAY_ADDRESS` unset; no `gcs_server`, `raylet`, `ray::`, `pytest` or
  `main.py` process; `ray_cluster.sh status`: no processes on `/tmp/ray-si`, ports 6390, 6391, 8266, 52366
  free.
- **§2.1.2, the suites at the gate**, serially, output to files in the scratch directory:

  | Run | Result | Time | Load before; after |
  |---|---|---|---|
  | `./venv/bin/python -m pytest -m "not integration and not slow" -q -p no:cacheprovider` | **696: 695 passed, 1 skipped** (131 deselected) | 26.5 s | 5.70; 6.53 |
  | `RAY_ADDRESS=local ./venv/bin/python -m pytest -m integration -q -p no:cacheprovider` | **62: 61 passed, 1 skipped** (765 deselected) | 33.3 s | 18.41; 55.19 |

  08's counts. `slow` collected 69 (S1's 69 passed).
- **§2.1.3, DatastoreKit's script at `HEAD`**, from DatastoreKit's root with its venv
  (`./venv/bin/python docs/extraction/measure_client_imports.py si --commit 597730f`; DatastoreKit at
  `38ebb9f`, clean):

  | What | Count |
  |---|---|
  | Layer files absent | none |
  | Import statements naming a layer module | **48** in 47 files, 2 nested (`InflationConcepts/DiffusionModel/registry.py:5` under `if TYPE_CHECKING`; `tests/test_compare_stores.py:944` in a `try`) |
  | String literals naming a layer module | 0 |
  | `import_module` calls naming a layer module | **3** (`tests/test_config_datastore.py:38`, `:39`; `tests/test_inflaton_trajectory_prune.py:53`) |
  | Imports of factory modules (not layer imports) | 25 (`config/` 22, `CosmologyConcepts/` 2, `tests/` 1) |

  By module: `Datastore` 12, `Datastore.SQL.Datastore` 1, `Datastore.SQL.ObjectFactories.base` 24,
  `Datastore.SQL.ProfileAgent` 1, `Datastore.SQL.ShardedPool` 4, `Datastore.object` 6: the prompt's §0
  and §1.2 exactly.
- **The greps** (`git grep -n -E`, outside `.prompts/` and `.documents/`, the layer's own seven files set
  aside): `Datastore\.SQL` — the 24 `base` imports of §1.2, `main.py:37-38`, the plot scripts' and
  `conftest.py`'s imports, `test_compare_stores.py:944`, and correction 2's list (the factory imports at
  `config/datastore.py:45-98`, `CosmologyConcepts/Potentials/registry.py:6-7`,
  `tests/test_compare_stores.py:973`; the docstrings `config/datastore.py:32-37` and
  `tests/test_config_datastore.py:18-28`; `:38-39` and the code string `:188`;
  `tests/test_inflaton_trajectory_prune.py:53` and `:459`); `Datastore\.object` — the 6 of §1.2;
  `ObjectFactories\.base` — the two registries; `from Datastore import` — the 12 of §1.2; `drop_actions` —
  the six sites of correction 2; `inventory_config` — `config/sharding.py:97`, the three drivers' imports
  and constructions, `conftest.py:32`, `:70`, `test_inflaton_trajectory_prune.py:460`, `:472`;
  `.inventory(` (fixed string) — `pool-read-apis.md:5-35`, `config/sharding.py:78`, `main.py:1253`,
  `:1263`, `:1275`, `:1285`, `test_grid_builder_integration.py:115`, `:133-135`. Every hit is in §0–§1.7
  or correction 2.
- **§2.1.4, the schema at the gate.** 06's `schema_build.py` with its label changed (`09-gate-schema-check`),
  run from the root as `./venv/bin/python <scratch>/schema_build_gate.py <scratch>/tmp-store`: SI's own
  pool, two shards, `ray.init(address="local")` in its own process, nothing stored. `Created sharded
  datastore … with 2 shards`; files `temp-shard0000.sqlite`, `temp-shard0001.sqlite`, `temp.sqlite`.
  `tools/compare_stores.py --snapshot` to `<scratch>/gate-schema.json`;
  `--schema … --against out/07-reference-schema.json`: `RESULT: the schemas agree`, exit 0. The primary
  holds `replicated_tables`, `shard_key_config`, `shard_keys`, `sharded_tables`, `shards`.

### A2–A3 — every file of §1.2 by `ast`

`ast_compare.py` (scratch): for each of the 48 files of §1.2 (the 47 the `perl` pass touched and
`tests/test_compare_stores.py`), it parses `git show 597730f:<file>` and the working file, rewrites each
`from <layer module> import …` of the gate by the module map, and compares `ast.dump` (docstrings
included, comments not). Output:

```text
identical after normalisation: 42 of 48
  DIFF  main.py (2 import rewritten at gate)
        insert gate stmts at [] -> now [23]                 # from config.datastore import ...
        replace gate stmts at [25] -> now [26]              # config.sharding import, less inventory_config
        insert gate stmts at [] -> now [103, 113]           # the two refusals
        delete gate stmts at [1227, 1250, 1260, 1272, 1282, 1307, 1319] -> now []   # the 7 inventory functions
        replace gate stmts at [1342] -> now [1261]          # the pool's `with`
  DIFF  plot_GradientCoupledSolutions.py (1 import rewritten at gate)
        insert gate stmts at [] -> now [50]                 # from config.datastore import ...
        replace gate stmts at [52] -> now [53]              # config.sharding import, less inventory_config
        replace gate stmts at [964] -> now [964]            # `if __name__ == "__main__":`, the pool's arguments
  DIFF  plot_InstantonSolutions.py (1 import rewritten at gate)
        insert gate stmts at [] -> now [30]
        replace gate stmts at [32] -> now [33]
        replace gate stmts at [1198] -> now [1198]
  DIFF  tests/conftest.py (1 import rewritten at gate)
        replace gate stmts at [1] -> now [1]                # module docstring
        replace gate stmts at [26, 37] -> now [28, 29, 39]  # imports; live_pool (docstring and arguments)
  DIFF  tests/test_compare_stores.py (0 import rewritten at gate)
        replace gate stmts at [938] -> now [938]            # _registry(): the fallback removed, docstring
  DIFF  tests/test_inflaton_trajectory_prune.py (0 import rewritten at gate)
        replace gate stmts at [16] -> now [16]              # module docstring
        delete gate stmts at [53] -> now []                 # importlib.import_module("Datastore.SQL.Datastore")
        replace gate stmts at [452] -> now [450]            # _POOL_SCRIPT (the I6 script)
        replace gate stmts at [556] -> now [556]            # I6 (its docstring only)
```

(The comments after `#` are added here.) The 42 identical files are the 22 factory modules, the two
registries, the 12 `from Datastore import DatastoreObject` modules and the 6 `Datastore.object` ones: **every
factory's, concept module's and compute target's diff is its import line**. The plot scripts' `replace` at
the `if __name__` block is the pool's three arguments alone (the diffs below).

### The four pool constructions

```diff
--- a/main.py   (the pool; the imports and the refusals are below)
@@ ShardedPool(
     prune_unvalidated=args.prune_unvalidated,
-    drop_actions=args.drop,
+    drop_tables=drop_tables,
     read_table_config=read_table_config,
-    inventory_config=inventory_config,
+    factories=factories,
+    serial_batch_sizes=serial_batch_sizes,
 ) as pool:
     units = Planck_units()
-    if args.inventory:
-        inventory(pool, units)
-    else:
-        execute(pool, units)
+    execute(pool, units)
--- a/plot_GradientCoupledSolutions.py   (and plot_InstantonSolutions.py, identically)
@@ ShardedPool(
         prune_unvalidated=False,
-        drop_actions=[],
         read_table_config=read_table_config,
-        inventory_config=inventory_config,
+        factories=factories,
+        serial_batch_sizes=serial_batch_sizes,
     ) as pool:
--- a/tests/conftest.py
@@ ShardedPool(
         prune_unvalidated=False,
-        drop_actions=[],
         read_table_config=read_table_config,
-        inventory_config=inventory_config,
+        factories=factories,
+        serial_batch_sizes=serial_batch_sizes,
     ) as pool:
```

Each file also gains `from config.datastore import factories, serial_batch_sizes` (`main.py`: `…,
tables_to_drop`) after `from config.argument_parser import …` (in `conftest.py`, after the `ShardedPool`
import), loses `inventory_config` from its `config.sharding` import, and has its `ShardedPool` (and in
`main.py` `ProfileAgent`) import rewritten. `main.py` outside the pool: the two refusals after the
provenance print (below), and the seven deleted functions. `live_pool`'s `ray.init(ignore_reinit_error=True)`
and `ray.shutdown()` are unchanged.

### U5 — `tables_to_drop`

`config/datastore.py` gains `tables_to_drop(groups)` and two helpers (`_naming`, which words the message,
and `_joined`), with the imports `typing`, `sqlalchemy`, `datastorekit.SQL.schema.build_schema`,
`dependent_tables` and `datastorekit.store_inventory.inventory_specs`. It returns the requested groups'
tables, each once, in `drop_groups`' order; it raises `ValueError` for an unknown group; and it raises
`ValueError` when `dependent_tables(tables, factories)` names a table not among them. `main.py`:

```python
print(format_package_provenance(installed_package_provenance()), flush=True)

# --inventory refuses until the inventory is ported to the datastorekit package, whose pool has no
# inventory(); before Ray starts, so that nothing is created (dk-and-rpk-migration prompt 09; P11)
if args.inventory:
    print(
        "!! --inventory: the datastore inventory is unavailable until it is ported to the "
        "datastorekit package (dk-and-rpk-migration prompt 10). Nothing was opened",
        file=sys.stderr,
    )
    sys.exit(2)

# the --drop groups become the tables the pool drops; a drop that would leave rows naming dropped
# rows is refused here, before Ray starts (dk-and-rpk-migration prompt 09; U5)
try:
    drop_tables = tables_to_drop(args.drop)
except ValueError as e:
    print(f"!! --drop: {e}. Nothing was opened", file=sys.stderr)
    sys.exit(2)

ray.init(address=args.ray_address)
```

**The three messages** (each printed after `!! --drop: ` and followed by `. Nothing was opened`):

- `full-instanton`: `cannot drop full-instanton alone: CompactionFunction names its rows, so
  CompactionFunction and CompactionFunctionSamples must be dropped too; add --drop compaction-function`
- `slow-roll-instanton`: the same, with `slow-roll-instanton`.
- `inflaton-trajectory`: `cannot drop inflaton-trajectory alone: FullInstanton, GradientCoupledInstanton,
  SlowRollInstanton and CompactionFunction name its rows, so FullInstanton, FullInstantonValue,
  GradientCoupledInstanton, GradientCoupledInstantonValue, GradientCoupledInstantonProfile,
  SlowRollInstanton, SlowRollInstantonValue, CompactionFunction and CompactionFunctionSamples must be
  dropped too; add --drop full-instanton slow-roll-instanton compaction-function gradient-coupled-instanton`

**The decisions over all 31 non-empty sets** (`u5_replay.py`, scratch: `tables_to_drop` on each, beside
`dependent_tables`' own closure): **closed 10, refused 21, agree with `dependent_tables` 31 of 31**, and the
closed sets are exactly the orchestrator's (correction 9):

| Closed (10) |
|---|
| `compaction-function`; `gradient-coupled-instanton`; `full-instanton`+`compaction-function`; `slow-roll-instanton`+`compaction-function`; `compaction-function`+`gradient-coupled-instanton`; `full-instanton`+`slow-roll-instanton`+`compaction-function`; `full-instanton`+`compaction-function`+`gradient-coupled-instanton`; `slow-roll-instanton`+`compaction-function`+`gradient-coupled-instanton`; the four without `inflaton-trajectory`; all five |

| Refused (21) | `add --drop …` |
|---|---|
| any set without `compaction-function` that holds `full-instanton` or `slow-roll-instanton` and not `inflaton-trajectory` (5 sets) | `compaction-function` |
| any set with `inflaton-trajectory` but not all five (15 sets) | the missing groups among `full-instanton`, `slow-roll-instanton`, `compaction-function`, `gradient-coupled-instanton` |
| `inflaton-trajectory` alone (counted above) | all four others |

No closed set holds `inflaton-trajectory` but all five. Every dependent table at this tree belongs to a
group, so no message names a loose table. No Ray was started (`ray.is_initialized()` `False`).

### The harness and the tests changed under §1.6

1. **`tests/conftest.py`, `live_pool`** — the package's `ShardedPool` (its import moved), with
   `factories=` and `serial_batch_sizes=` from `config.datastore`, without `drop_actions=` and
   `inventory_config=`; `ray.init(ignore_reinit_error=True)` and the teardown unchanged; docstrings say
   whose pool it is. *Reason:* the layer it built is deleted, and the package requires `factories` and
   refuses the two retired keywords. The other integration tests change nowhere.
2. **`tests/test_grid_builder_integration.py`, `test_no_duplicate_rows_created`** — counts rows by value
   with a `sqlite3` `mode=ro` read of each shard file beside `live_pool.primary` (`<stem>-shard*.sqlite`,
   the first checked against `datastorekit.shard_paths.shard_file_name(primary, 0)`), `SELECT value FROM
   <table>`, requiring exactly one row near the target on every shard; a new helper `_shard_values`, and
   the imports `sqlite3`, `Path`, `shard_file_name`. *Reason:* the package's pool has no `inventory`, and
   `read_table` would refuse `N_init` and `N_final`, which `read_table_config` does not list (correction
   3); the three tables are replicated, each with a `value` column. The test's other two tests and its
   assertions' meaning are unchanged.
3. **`tests/test_config_datastore.py`** — the two `import_module` calls of the layer gone;
   `test_layer_reads_the_data_from_config_datastore` and
   `test_layer_drop_order_names_exactly_the_drop_groups` deleted (they tested the deleted layer) and
   replaced by `test_every_pool_construction_passes_config_datastore`; `test_importing_the_data_starts_no_ray`
   imports `config.datastore` alone, first, in its fresh process (the closing test of the issue); the
   module docstring corrected; the captured literals unchanged. 7 → 6 tests.
4. **`tests/test_inflaton_trajectory_prune.py`** — the `import_module` of the layer and its comment gone;
   I6's script builds the package's `ShardedPool` (`import config.datastore`; `factories=`,
   `serial_batch_sizes=`; no `drop_actions=`, no `inventory_config=`), both processes and both reads of the
   shards kept; the Ray-free tests keep their `_Store` helper, since the package's `build_schema` prepends
   the same four columns by the same flags in the same order with the same types (`schema.py:60-170`) and
   it still builds all 30 tables; docstrings and two comments corrected. The signature test still counts
   12 hooks by each class's own `__dict__` (the inherited one is now the package's base's).
5. **`tests/test_compare_stores.py`, `_registry()`** — imports `config.datastore` directly; the `try`/`except
   ImportError` fallback to the layer gone; its docstring corrected. Its 24 tests otherwise unchanged.

### The new tests

- **`tests/test_tables_to_drop.py`** (9, default run, no Ray): `test_the_groups_are_the_five` (the five
  groups in order; 31 sets; 10 closed); `test_an_unclosed_group_alone_is_refused_naming_the_groups_to_add`
  ×3 (each singleton's message, verbatim); `test_every_set_is_decided_as_measured` (all 31: a closed set
  returns exactly its groups' tables in `drop_groups`' order; a refused one raises, names only groups it
  lacks, and those groups close it); `test_duplicates_and_order_do_not_matter`; `test_no_group_drops_nothing`;
  `test_an_unknown_group_is_refused`; `test_no_ray_is_started` (a fresh process).
- **`tests/test_config_datastore.py::test_every_pool_construction_passes_config_datastore`** (default, no
  Ray, `ast`): in each of the four files exactly one `ShardedPool(...)` call; `factories=` and
  `serial_batch_sizes=` present and naming `config.datastore`'s objects (an imported name, or
  `config.datastore.<name>`); no `drop_actions=`, no `inventory_config=`, no `**kwargs`. A failure names
  `file:line`.
- **`tests/test_main_refusals.py`** (3, default run, no Ray): `test_main_refuses_before_ray[inventory]`
  and `[drop-full-instanton]` run `main.py --database <tmp>/x.sqlite --ray-address 127.0.0.1:9` (and
  `RAY_ADDRESS=127.0.0.1:9`, a 120 s timeout) with `--inventory`, or `--drop full-instanton`: exit 2, stdout
  begins with the provenance line, the message is a line of stderr, no `Traceback`, and the temporary
  directory is empty. `test_both_refusals_precede_ray_init`, by `ast` on `main.py`'s module-level
  statements: one `ray.init(...)`, one `if args.inventory:` with `sys.exit(2)`, one `try` calling
  `tables_to_drop` with an `except ValueError` and `sys.exit`, both before `ray.init`; and no other read
  of `args.inventory`.
- **`tests/test_datastorekit_timestamp.py::test_replicated_and_sharded_objects_carry_their_rows_timestamp`**
  (integration; needs Ray because the objects are written and read through the package's pool, whose
  actors hold the shards): through `live_pool`, a `delta_Nstar` (0.937) is got, then got again; the
  second object's `timestamp` is a `datetime` and equals, on every shard, the `timestamp` column of the
  row with its `serial`, read with `sqlite3` `mode=ro` and parsed by `datetime.fromisoformat`. Then a
  `FullInstanton` (`N_init` 93.7, a synthetic computed object as `test_scalars_only_storage.py` makes
  them) is stored and validated, fetched back by `object_get`, and its `timestamp` equals the column of
  the one shard row with its `serial`. Unique values, so the shared store holds one row of each.

### §2.3.1 — DatastoreKit's script at a dangling commit

The staged tree was written (`git write-tree` → `36c715b2edde…`) and committed on no branch (`git
commit-tree … -p HEAD` → `3c36d34d49e0…`, unreferenced); the script was run on it from DatastoreKit's root:

| What | Count |
|---|---|
| Layer files absent | `Datastore/object.py`, `Datastore/SQL/ClientPool.py`, `Datastore/SQL/Datastore.py`, `Datastore/SQL/ProfileAgent.py`, `Datastore/SQL/SerialPoolBroker.py`, `Datastore/SQL/ShardedPool.py`, `Datastore/SQL/ObjectFactories/base.py` |
| Import statements naming a layer module | **0** in 0 files |
| String literals naming a layer module | **0** |
| `import_module` calls naming a layer module | **0** |
| Imports of factory modules | 25 (unchanged) |
| Files read / not parsed | 197 / 0 |

`git ls-tree -l` of that commit: `Datastore/__init__.py` and `Datastore/SQL/__init__.py` present, 0 bytes
(blob `e69de29…`). `git grep -n -E
'Datastore\.(SQL\.(ShardedPool|Datastore|ClientPool|ProfileAgent|SerialPoolBroker)|object)\b|ObjectFactories\.base'
<commit> -- . ':!.prompts' ':!.documents'`: no hit (exit 1). The path citations of the deleted files that
remain (`tools/compare_stores.py:39`, `:94`, `:115`, `:116`; `tests/test_rehearsal_stage_counts.py:26`) are
paths, not module names, and are listed for 12 below. The script was re-run at the final staged tree before
the commit, at a second dangling commit (`3a8e5a4177f0…`, tree `8b7600ee94a7…`, which differs from this commit's only in this note's final paragraphs): the 7 absent, **0** imports, **0** literals, **0** `import_module`, the two `__init__.py` 0 bytes, the dotted-name grep empty.

### §2.3.2 — without Ray

1. **`config.datastore` alone, in a fresh process** (deviation 5). From the scratch directory,
   `PYTHONPATH=<root> ./venv/bin/python -c "<code>"`, and `./venv/bin/python -I -c "import sys;
   sys.path.insert(0, '<root>'); <code>"`, where `<code>` imports `config.datastore` first and then
   prints:
   ```text
   entries 30
   all package base instances True
   datastorekit from /Users/ds283/Documents/Code/StochasticInstantons/venv/lib/python3.13/site-packages/datastorekit/__init__.py
   Datastore.SQL.ShardedPool loaded False ; Datastore.SQL.Datastore loaded False
   ray initialized False
   ```
   Both exit 0. From the root, `PYTHONPATH=<root> ./venv/bin/python -c "import config.datastore"` exits 0;
   `./venv/bin/python -I -c "import config.datastore"` exits 1 with `ModuleNotFoundError: No module named
   'config'` (`-I`'s isolation, not the tree). At the gate (an export of `597730f`, run with
   `STOCHASTIC_INSTANTONS_REPO` and `PYTHONPATH` set to the export) the same import fails with
   `ImportError: cannot import name 'serial_batch_sizes' from partially initialized module
   'config.datastore' (most likely due to a circular import)`.
2. **`./venv/bin/python -m datastorekit.tools.sharded_store --help`** exits 0 (`usage: python -m
   datastorekit.tools.sharded_store [-h] {copy,move} src dst`).
3. **The drivers.** `./venv/bin/python -m py_compile main.py plot_InstantonSolutions.py
   plot_GradientCoupledSolutions.py` succeeds. 04's `import_check.py`, extended to report private names of
   either package and any layer module loaded, run as `./venv/bin/python -I <scratch>/import_check.py`
   (the root added by path; no driver executed):
   ```text
   imports checked: 165 in 3 drivers
   unresolved: 0
   private names imported from raypoolkit or datastorekit: 0 []
   raypoolkit origin: /Users/ds283/Documents/Code/StochasticInstantons/venv/lib/python3.13/site-packages/raypoolkit/__init__.py
   datastorekit origin: /Users/ds283/Documents/Code/StochasticInstantons/venv/lib/python3.13/site-packages/datastorekit/__init__.py
   Datastore layer modules loaded: []
   ray.is_initialized(): False
   ```
   Exit 0. At the gate (the export) it checks 161; the 4 more are `main.py`'s three `config.datastore`
   names and each plot script's two, less the three `inventory_config`s.
4. **The refusals**, `RAY_ADDRESS=127.0.0.1:9 ./venv/bin/python main.py --database <scratch>/refusal/x.sqlite
   --ray-address 127.0.0.1:9 --inventory`, and the same with `--drop full-instanton` instead:
   ```text
   >> packages: datastorekit 0.4.0 (https://github.com/ds283/DatastoreKit@c8570e849334d09085bbd84876095fc9e22bd005, requested v0.4.0); raypoolkit 0.2.0 (https://github.com/ds283/RayPoolKit@eaef0ce60e2fc354bb32f0ad576010e6a83c1976, requested v0.2.0)
   !! --inventory: the datastore inventory is unavailable until it is ported to the datastorekit package (dk-and-rpk-migration prompt 10). Nothing was opened
   exit 2
   >> packages: datastorekit 0.4.0 (… as above …)
   !! --drop: cannot drop full-instanton alone: CompactionFunction names its rows, so CompactionFunction and CompactionFunctionSamples must be dropped too; add --drop compaction-function. Nothing was opened
   exit 2
   ```
   1.9 s and 1.0 s; `<scratch>/refusal/` empty after both; no Ray process.

### §2.3.3 — the schema

`schema_build_pkg.py` (scratch): the gate's script with the package's pool built as `live_pool` now builds
it (`from datastorekit.SQL.ShardedPool import ShardedPool`; `factories=`, `serial_batch_sizes=` from
`config.datastore`; no `drop_actions=`, no `inventory_config=`), two shards, `ray.init(address="local")`, nothing
stored. Output: `Created sharded datastore … with 2 shards`; the same three files. Then:

```text
./venv/bin/python tools/compare_stores.py --snapshot <tmp>/temp.sqlite --out .documents/dk-and-rpk-migration/out/09-temp-schema.json   # exit 0
./venv/bin/python tools/compare_stores.py --schema <tmp>/temp.sqlite --against <scratch>/gate-schema.json
RESULT: the schemas agree        # exit 0
./venv/bin/python tools/compare_stores.py --schema <tmp>/temp.sqlite --against .documents/dk-and-rpk-migration/out/07-reference-schema.json
RESULT: the schemas agree        # exit 0
```

Also against `05-temp-schema.json` and `02-reference-schema.json`: `RESULT: the schemas agree`.
`09-temp-schema.json` differs from the gate's snapshot only in `source`; 30 tables. **No difference, not even
in the prepended columns' order** (contract §2; ChamPBH's 08 found none either). Each shard has 30 tables. The
primary holds `replicated_tables`, `replication_in_flight`, `shard_key_config`, `shard_keys`, `sharded_tables`,
`shards`: the package's `replication_in_flight` is new beside SI's five (the snapshot compares the shards'
registered tables, not the primary's).

### §2.3.4 — the suites

Serially, in the foreground, each to a file in the scratch directory; `slow` once, in the background.

| Suite | Gate (08's) | Now | Time | Load before; after |
|---|---|---|---|---|
| default, `-m "not integration and not slow"` | 696 (695 passed, 1 skipped) | **707 (706 passed, 1 skipped)**, 132 deselected | 29.8 s | 6.43; 7.79 |
| integration, `RAY_ADDRESS=local … -m integration` | 62 (61 passed, 1 skipped) | **63 (62 passed, 1 skipped)**, 776 deselected | 33.4 s | 7.25; 21.39 |
| `slow`, `-m slow` | S1: 69 passed | **69 passed** (770 deselected, 11 warnings: S1's `RuntimeWarning`s from `Numerics/OnionCoordinate.py:77`) | 397.0 s | 19.84; 10.48 |

The default and integration runs were made again on the same tree after the six breakages had been
reverted (the session was paused by an API limit between the two): default **707 (706 passed, 1 skipped)**,
31.1 s, load 11.30; 12.82; integration **63 (62 passed, 1 skipped)**, 36.0 s, load 12.44; 15.50. No Ray process
was left after any run.

**By module** (collected with `--collect-only -q`, gate and now; every module not listed has the same count):

| Module | Default at the gate | Now | Why |
|---|---|---|---|
| `tests/test_config_datastore.py` | 7 | 6 | −2 layer tests (§1.6 item 3), +1 `ast` test |
| `tests/test_tables_to_drop.py` | — | 9 | new (U5) |
| `tests/test_main_refusals.py` | — | 3 | new (the refusals) |
| **total** | **696** | **707** | 696 − 2 + 1 + 9 + 3 |

| Module | Integration at the gate | Now | Why |
|---|---|---|---|
| `tests/test_datastorekit_timestamp.py` | — | 1 | new (U3, acceptance 5) |
| **total** | **62** | **63** | 62 + 1 |

The changed modules keep their counts: `test_inflaton_trajectory_prune.py` 6 + 1 integration,
`test_compare_stores.py` 24, `test_grid_builder_integration.py` 3 integration. The skip in each run is the
gate's. `slow` collects the same 69 in the same 9 modules. The one failure met during development was in a
new test (deviation 9); no existing test failed, so nothing was re-run alone.

**Acceptance 4** is I6, in the integration run (and alone first: the three changed integration modules,
5 passed, 30.2 s): on a two-shard temporary store through the package's pool, the unvalidated
`InflatonTrajectory` and its 3 value rows are gone from both shards after the pruning reopen, the validated
one kept with its 3, no orphan, and the reopen process exits 0 (no refusal). The same script, run by hand from the scratch directory (store, then reopen; then deleted),
shows what the package prints at a pruning reopen, where SI's old layer printed its actors' prune messages:

```text
!! INTEGRITY WARNING (2026-10-21T18:46:27): sharded datastore "<scratch>/i6run/prune.sqlite", shard 0 (physical file <scratch>/i6run/prune-shard0000.sqlite), pruned by the pool under a "prune" record
Pruned 1 unvalidated InflatonTrajectory records
!! INTEGRITY WARNING (2026-10-21T18:46:27): sharded datastore "<scratch>/i6run/prune.sqlite", shard 1 (physical file <scratch>/i6run/prune-shard0001.sqlite), pruned by the pool under a "prune" record
Pruned 1 unvalidated InflatonTrajectory records
>> Pruned the unvalidated rows of "InflatonTrajectory" from every shard of "<scratch>/i6run/prune.sqlite" under a "prune" record, which was cleared
>> Opened existing sharded datastore "<scratch>/i6run/prune.sqlite" with 2 shards
```

(`Pruned 1 unvalidated InflatonTrajectory records` is the factory's own message, unchanged from 06.) After it,
each shard holds trajectory 1 (validated) and its 3 value rows only.

### §2.3.5 — `ruff check --select F401,F811,F821`

On the 56 Python files the diff adds or modifies, each at the gate (`git show 597730f:<file> | ruff check
--stdin-filename <file> -`) and now: 33 findings at the gate, 31 now, **none new**. The two gone are the two
`__init__.py`s' `F401`s (their re-exports, now empty files). The rest are the gate's own (`main.py` 12 `F401`
and 4 `F811`, `plot_InstantonSolutions.py` 9, `ComputeTargets/FullInstanton.py`, `SlowRollInstanton.py`,
two factories' unused `datetime`, `InflationConcepts/efold_value.py` 2), at the same names. The three new test
files: `ruff format`, then `ruff check --select F401,F811,F821,F541`: clean.

## The deliberate-breakage record

Each was applied with `git apply` to the clean change (the working tree that this commit records), the named
test run, then reverted with `git apply -R`; after each, `git diff --quiet` of the file against the staged change
held, and after all six the staged and unstaged diffs were byte-identical to those saved before the first. Each is
recorded as `diff -u` labelled `a/` and `b/`, so that `git apply` replays it from a clean tree at `f4da58f`.
(`git apply --check` and `-R --check` after the commit are in the hand-off, since a commit cannot record its own
check.)

### Breakage 1 — one factory's import pointed back at the layer (`N_init.py`, not a protected factory)

```diff
--- a/Datastore/SQL/ObjectFactories/N_init.py
+++ b/Datastore/SQL/ObjectFactories/N_init.py
@@ -4,7 +4,7 @@
 import sqlalchemy as sqla
 
 from InflationConcepts.N_init import N_init
-from datastorekit.SQL.factory_base import SQLAFactoryBase
+from Datastore.SQL.ObjectFactories.base import SQLAFactoryBase
 from config.defaults import (
     DEFAULT_EFOLD_PRECISION,
     DEFAULT_EFOLD_RELATIVE_PRECISION,
```

Caught. The default run stops at collection, exit 4: `ImportError while loading conftest` —
`tests/conftest.py:28` → `config/datastore.py:88` → `Datastore/SQL/ObjectFactories/N_init.py:7`: `E
ModuleNotFoundError: No module named 'Datastore.SQL.ObjectFactories.base'`. §2.3.2's `import_check.py` exits 1
with 7 `UNRESOLVED` lines, each `from config.datastore import …` of the three drivers, each naming
`ModuleNotFoundError: No module named 'Datastore.SQL.ObjectFactories.base'`.

### Breakage 2 — `timestamp=row_data.timestamp` dropped from `sqla_FullInstantonFactory.build`

```diff
--- a/Datastore/SQL/ObjectFactories/FullInstanton.py
+++ b/Datastore/SQL/ObjectFactories/FullInstanton.py
@@ -177,7 +177,6 @@
             rtol=rtol,
             diffusion_model=diffusion_model,
             label=row_data.label,
-            timestamp=row_data.timestamp,
         )
         obj._trajectory_serial = trajectory.store_id
         obj._delta_Nstar_serial = delta_Nstar_obj.store_id
```

Caught. `RAY_ADDRESS=local pytest -m integration tests/test_datastorekit_timestamp.py`: 1 failed. The replicated
half passes; the sharded half fails at `test_datastorekit_timestamp.py:146`, `assert isinstance(fetched.timestamp,
datetime)`, `where None = <FullInstanton …>.timestamp`.

### Breakage 3 — `owner_column` removed from `InflatonTrajectoryValue`'s `register()`

```diff
--- a/Datastore/SQL/ObjectFactories/InflatonTrajectory.py
+++ b/Datastore/SQL/ObjectFactories/InflatonTrajectory.py
@@ -441,7 +441,6 @@
             "version": False,
             "timestamp": False,
             # Ignored by SI's own layer; DatastoreKit reads it to put this table in its owner's unit (U4).
-            "owner_column": "trajectory_serial",
             "columns": [
                 sqla.Column(
                     "trajectory_serial",
```

Caught, by the package's refusal. I6 (`tests/test_inflaton_trajectory_prune.py`, `-m integration`): 1 failed,
`AssertionError: reopen process failed (1)`; the reopen process raised:

```text
RuntimeError: Sharded datastore "…/prune.sqlite": the prune of "InflatonTrajectory" on shard 0 ("…/prune-shard0000.sqlite") did not take: "InflatonTrajectoryValue" lost rows [(2, 1), (2, 2), (2, 3)], and a prune of "InflatonTrajectory" deletes only from ['InflatonTrajectory']. That shard's transaction was rolled back, and the replication_in_flight record of the prune is left set, so the next open of this store completes the prune on every shard
```

That is `_prune_shard` policing the unit (`_unit_tables`): without `owner_column` the value table is outside
`InflatonTrajectory`'s unit, so the cascade 06 added is refused and rolled back.

### Breakage 4 — the closure check removed from `tables_to_drop`

```diff
--- a/config/datastore.py
+++ b/config/datastore.py
@@ -237,7 +237,7 @@
         if group in requested
         for table in group_tables
     ]
-    dependents = [table for table in dependent_tables(tables, factories) if table not in tables]
+    dependents = []
     if len(dependents) == 0:
         return tables
 
```

Caught. `pytest tests/test_tables_to_drop.py tests/test_main_refusals.py`: 5 failed, 7 passed —
`test_an_unclosed_group_alone_is_refused_naming_the_groups_to_add` for each of `full-instanton`,
`slow-roll-instanton` and `inflaton-trajectory`; `test_every_set_is_decided_as_measured`, listing each of the 21
refused sets as `accepted (…)`; and `test_main_refuses_before_ray[drop-full-instanton]`, where `main.py` went on
to `ray.init(address="127.0.0.1:9")`, which nothing answers, and the subprocess was killed at its 120 s timeout
(`subprocess.TimeoutExpired`): the guard the address is there for. No process was left.

### Breakage 5 — `factories=` dropped from `live_pool`

```diff
--- a/tests/conftest.py
+++ b/tests/conftest.py
@@ -69,7 +69,6 @@
         job_name="pytest-integration",
         prune_unvalidated=False,
         read_table_config=read_table_config,
-        factories=factories,
         serial_batch_sizes=serial_batch_sizes,
     ) as pool:
         yield pool
```

Caught. The integration run: 61 errors at setup, each `TypeError: ShardedPool.__init__() missing 1 required
keyword-only argument: 'factories'`; 1 passed (I6, which builds its own pools) and the gate's 1 skipped.
`tests/test_config_datastore.py`: 1 failed, `AssertionError: tests/conftest.py:60: no factories=`.

### Breakage 6 — the `--inventory` refusal moved after `ray.init`

```diff
--- a/main.py
+++ b/main.py
@@ -97,16 +97,6 @@
     sys.exit()
 
 print(format_package_provenance(installed_package_provenance()), flush=True)
-
-# --inventory refuses until the inventory is ported to the datastorekit package, whose pool has no
-# inventory(); before Ray starts, so that nothing is created (dk-and-rpk-migration prompt 09; P11)
-if args.inventory:
-    print(
-        "!! --inventory: the datastore inventory is unavailable until it is ported to the "
-        "datastorekit package (dk-and-rpk-migration prompt 10). Nothing was opened",
-        file=sys.stderr,
-    )
-    sys.exit(2)
 
 # the --drop groups become the tables the pool drops; a drop that would leave rows naming dropped
 # rows is refused here, before Ray starts (dk-and-rpk-migration prompt 09; U5)
@@ -117,6 +107,16 @@
     sys.exit(2)
 
 ray.init(address=args.ray_address)
+
+# --inventory refuses until the inventory is ported to the datastorekit package, whose pool has no
+# inventory(); before Ray starts, so that nothing is created (dk-and-rpk-migration prompt 09; P11)
+if args.inventory:
+    print(
+        "!! --inventory: the datastore inventory is unavailable until it is ported to the "
+        "datastorekit package (dk-and-rpk-migration prompt 10). Nothing was opened",
+        file=sys.stderr,
+    )
+    sys.exit(2)
 
 
 def inflaton_trajectory_store_handler(obj, pool):
```

Caught. `pytest tests/test_main_refusals.py -k precede`: 1 failed, `AssertionError: the --inventory refusal (line
113) must precede ray.init (line 109)`. (The subprocess tests were not run on this mutation: `main.py` would try
to connect to `127.0.0.1:9` first and wait out the timeout, as breakage 4 shows.)

## The prose corrected (P13)

- **`CLAUDE.md`, "Protected infrastructure".** The list loses `Datastore/SQL/ShardedPool.py`,
  `Datastore/object.py`, `Datastore/SQL/SerialPoolBroker.py`, `Datastore/SQL/ClientPool.py`,
  `Datastore/SQL/ProfileAgent.py`, `Datastore/SQL/ObjectFactories/base.py` (the seventh deleted file,
  `Datastore.py`, was governed by the sentence after the list). The sentence "When a prompt says 'modify
  `Datastore/SQL/Datastore.py`' …" is replaced by one saying that the layer (`ShardedPool`, the `Datastore`
  actor, `ClientPool`, `SerialPoolBroker`, `ProfileAgent`, `DatastoreObject`, `SQLAFactoryBase`) is the
  pinned `datastorekit` package, changed in DatastoreKit and reaching SI through a new pin, that SI's data
  for it is `config/datastore.py`, and, kept, that nothing else in a file one is told to modify is
  reformatted or reordered.
- **`.claude/rules/pool-read-apis.md`**, title and `:1-35`: the title is "`read_table()`, and no
  `inventory()`"; the opening says the pool is the package's; the section on `pool.inventory()` says the
  package's pool has none, that `--inventory` refuses until 10, and that from 10 the inventory is
  `datastorekit.store_inventory.read_inventory(primary, factories)`, read-only on a closed store, a report and
  not a data API; the two "route around the gap with `pool.inventory()`" phrases no longer name it.
- **`.claude/rules/datastore-factories.md`, "Replicated-table factories MUST honour a supplied `serial`"**:
  the account of the replication is the package's recorded write (a `replication_in_flight` record on the
  primary, a random controlling shard, the replicas given `serial=` and one timestamp, each answer checked,
  `ReplicationMismatch`, the record cleared last) and its check at open (`_reconcile_replicated_tables`:
  repair from the controlling shard, or `ReplicatedDivergence`); what ignoring the serial now does (a
  `ReplicationMismatch`, the record left set), with the old layer's silent divergence kept as the history the
  next section records; and that the package reads `_new_insert` (or `_updated`), not `_deserialized`. The
  rule, its pattern and its checklist stand.
- **`.claude/memory/bug-assign-shard-keys-key-id.md`** (after `:24`) and **`shard-key-assignment-bug.md`**
  (after its title): a status line that the file is deleted and the fix lives in the package's
  `ShardedPool._assign_shard_keys` (`datastorekit/SQL/ShardedPool.py:3618`; the `key_serial` insert at
  `:3674`, `3f1caad`'s; the de-duplication at `:3626`, `20d9a61`'s), reaching SI through its pin (checklist
  item 10). (The checklist's own line numbers, `:3572` and `:3524`, are of an earlier tree; these are
  `v0.4.0`'s, read in the installed file, which is byte-equal to the tag's: 08's K6.)
- **`.documents/FILE_MAP.md`**: the `config/datastore.py` row (`:18`) now says the package is given the data
  and names `tables_to_drop`; §3's three rows (`:40-42`) and §4's `base.py` row (`:54`) become rows "— (not a
  file of this repository)" naming the package's `DatastoreObject`, `ShardedPool` (no `inventory`),
  `Datastore` actor and `SQLAFactoryBase`, as 04 did for `RayWorkPool`; the "not included" table loses the
  three rows of deleted files (`:273-275`).
- **`config/datastore.py`'s docstring** (`:16-44` at the gate): the layer it names is the package; the import
  order paragraph is replaced by a sentence that the cycle is gone; the default batch size is the package's
  500 and `temperature` is ignored; `tables_to_drop` is described.

### What remains stale, for 12

- **`.documents/INFRASTRUCTURE.md`**: the title and §1 name SI's `Datastore`/`ShardedPool`; §2 (`:25-50`)
  cites `Datastore/object.py` and shows a `DatastoreObject` without `timestamp`; §4 (`:117`) "inheriting
  `SQLAFactoryBase`, implementing four methods" (the package's base has five hooks, three defaulted); §4's
  replication paragraph (`:153-175`), the old layer's unrecorded replication; §5 (`:180-184`) cites
  `Datastore/SQL/Datastore.py` and lists `inventory()` on the actor; §6 (`:190`) cites
  `Datastore/SQL/ShardedPool.py`, its method table lists `inventory(cls_name, ...)` (`:228`) and `:232`
  routes around the gap with `inventory()`; the invariant table's row `pool.inventory()` is a reporting tool
  (`:498`).
- **`.documents/architecture-summary.md`**: the tree (`:30-38`) lists `object.py`, `ShardedPool.py`,
  `ClientPool.py`, `Datastore.py`, `SerialPoolBroker.py`, `ProfileAgent.py`, `base.py` under `Datastore/`;
  the sections on `DatastoreObject` (`:153-172`, `Datastore/object.py`), the factory pattern (`:174`,
  `base.py`), the `Datastore` actor (`:190-195`, with `inventory()`) and `ShardedPool` (`:197-230`, its method
  table with `inventory`); `main.py`'s flow (`:394-403`, `if args.inventory: inventory(pool, units)`); the
  inventory section (`:494-500`, the four deleted helpers and `pool.inventory()`); the invariant row (`:580`).
- **Path citations outside 09's list** (correction 6): `tools/compare_stores.py:39` (`ShardedPool.py:88`,
  `:296`), `:94` (`ShardedPool.py:244-284`, `:287-291`), `:115`, `:116` (`Datastore.py:317`, `:639-647`,
  `:651-652`, inside its bookkeeping-reason strings); `tests/test_rehearsal_stage_counts.py:26` (a docstring
  citing `Datastore/SQL/Datastore.py` `_validate_on_startup`).
- **Comments in a factory**, which 09 may not edit beyond its import: `Datastore/SQL/ObjectFactories/InflatonTrajectory.py:33`
  and `:443` ("Ignored by SI's own layer; DatastoreKit reads it …") and `:264` ("SI's own layer never calls
  it"): true of the old layer, now the history of one.
- **`config/sharding.py:78`**, "Merge policies for `pool.inventory()` calls", with `inventory_config` (`:97`):
  10's, which deletes both.
- **`.claude/rules/pool-read-apis.md:37-39`** says `config/sharding.py` is on `CLAUDE.md`'s protected list; it
  is not, and was not before this commit. Not made false here, so not corrected (P13).

## Observations not acted on

- **The inherited drop hazard** (§1.5). A closed `--drop` set holding `inflaton-trajectory` (only all five
  are closed) drops a **replicated** table, which DatastoreKit's
  `[00-a-drop-action-drops-a-replicated-table-outside-the-in-flight-record]` says an interrupted drop can
  leave unopenable. It is the package's (README §5 rule 11); no test drops a replicated table on a real store.
- **The package refuses the same drops itself**, at open and after Ray (`_refuse_drop_that_leaves_references`,
  `ShardedPool.py:825-843`), naming tables; SI's check is the earlier one and names groups. Breakage 4 removes
  SI's alone.
- **What a build now prints that RH1's did not** (for 11). Opening and closing a pool print the same `>> Created
  sharded datastore … with N shards` line under both layers (the two schema builds' outputs). The primary of a
  new store holds the package's `replication_in_flight` table. A pruning reopen prints the package's lines
  (above, from I6's reopen): an `!! INTEGRITY WARNING (…) … pruned by the pool under a "prune" record` per
  shard, then `>> Pruned the unvalidated rows of "<class>" from every shard … which was cleared`, then `>> Opened
  existing sharded datastore … with N shards`. 11's `stage_counts.py` and L4 will meet these. The actors' own lines, and the pool's on an existing store, were not exercised
  here: 09 runs no build.
- **`-I` and `PYTHONPATH`** (deviation 5): any later prompt that asks for `python -I -c "import <SI module>"`
  must put the root on `sys.path` in the code.
- **`tools/diagnostics/GradientCoupledInstanton/harness.py:70-73`** puts the checkout on `sys.path` unless
  `STOCHASTIC_INSTANTONS_REPO` is set (correction 7). The only run outside the checkout here was the gate
  export's import and import checks, with that variable set to the export.

## State handed to the next prompt

- **Branch** `dk-and-rpk-migration`, `f4da58f` on `597730f`. Deleted: the 7 layer modules. Emptied:
  `Datastore/__init__.py`, `Datastore/SQL/__init__.py`. One import line each: the 22 factory modules, the two
  registries, the 12 concept modules, the 5 compute targets and `CosmologyModels/cosmo_params.py`. Changed:
  `main.py`, both plot scripts, `config/datastore.py`, `tests/conftest.py`, `tests/test_config_datastore.py`,
  `tests/test_inflaton_trajectory_prune.py`, `tests/test_grid_builder_integration.py`,
  `tests/test_compare_stores.py`, `CLAUDE.md`, `.claude/rules/pool-read-apis.md`,
  `.claude/rules/datastore-factories.md`, `.claude/memory/bug-assign-shard-keys-key-id.md`,
  `shard-key-assignment-bug.md`, `.documents/FILE_MAP.md`, `.documents/OPEN-ISSUES.md`, the board. New:
  `tests/test_tables_to_drop.py`, `tests/test_main_refusals.py`, `tests/test_datastorekit_timestamp.py`,
  `out/09-temp-schema.json`, this note.
- **SI imports no layer of its own.** Every pool is `datastorekit.SQL.ShardedPool`, given
  `factories=config.datastore.factories` and `serial_batch_sizes=config.datastore.serial_batch_sizes`;
  `main.py`'s also `drop_tables=config.datastore.tables_to_drop(args.drop)`. `config.datastore` imports alone.
  Every SI store written before `f4da58f` is unreadable by the tree (README §7).
- **Suites:** default **707** (706 passed, 1 skipped), integration **63** (62 passed, 1 skipped), `slow` **69
  passed**. By module: 08's, with `test_config_datastore.py` 7 → 6 and the new `test_tables_to_drop.py` 9,
  `test_main_refusals.py` 3 (default) and `test_datastorekit_timestamp.py` 1 (integration).
- **For 10.**
  - **`live_pool`** is the package's pool, with SI's registry; 10's tests can build their stores through it.
  - **U5's table** at this tree, by foreign keys alone (no `inventory_spec` yet): 10 of the 31 non-empty sets
    of `--drop` groups are closed — `compaction-function`; `gradient-coupled-instanton`; any set of
    `full-instanton`, `slow-roll-instanton`, `gradient-coupled-instanton` with `compaction-function`; all five —
    and 21 refused. `full-instanton` and `slow-roll-instanton` alone need `compaction-function`;
    `inflaton-trajectory` needs all four others. **10's specs may move it**: `dependent_tables` also follows the
    parents an `inventory_spec` declares, so a spec naming a parent outside today's foreign keys adds a
    dependency. `tests/test_tables_to_drop.py` pins the 10 closed sets and the three singleton messages
    verbatim; re-measure after the specs (as the orchestrator's `u5_proto.py` and this note's `u5_replay.py`
    do) and update the test with a named reason if the table moves.
  - **What `--inventory` must replace.** `main.py` refuses `--inventory` after the provenance print and before
    `ray.init` (exit 2, nothing created), pinned by `tests/test_main_refusals.py` (a subprocess test with the
    message, and an `ast` test of the order; 10 changes both with the refusal). The deleted report printed,
    under `@@ DATASTORE INVENTORY`: the `delta_Nstar`, `N_init`, `N_final` and `quartic_coupling` values; the
    `phi_value`, `pi_value` and `inflaton_mass` values in their units; the `efold_value` samples (each list
    truncated to 10 + 10 when over 20); and for `InflatonTrajectory`, `FullInstanton`, `SlowRollInstanton`,
    `CompactionFunction` and `GradientCoupledInstanton` the validated and unvalidated counts with the earliest
    and latest timestamps and up to 10 labels (5 + 5). `--show-all` was read by none of it. 10's report runs
    `read_inventory(primary, factories)` on the closed store before Ray, as ChamPBH's `main.py` does.
  - **`config/sharding.py`'s `inventory_config`** (`:97`) and its comment (`:78`) are still there, read by
    nothing; the 17 factory `inventory()` hooks are untouched. Both are 10's.
- **For 11.** What a build now prints that RH1's did not: at a pruning reopen, the package's `!! INTEGRITY
  WARNING (…) … pruned by the pool under a "prune" record` per shard and `>> Pruned the unvalidated rows of
  "<class>" from every shard … which was cleared`, before `>> Opened existing sharded datastore … with N
  shards`; the factories' own `Pruned N unvalidated …` lines are unchanged. A new store's primary holds the
  package's `replication_in_flight` table beside SI's five. `>> Created sharded datastore … with N shards` is
  printed as before. The package's actor lines on a long build, and its lines on reopening a populated store,
  were not exercised here (09 runs no build). Every driver's provenance line is unchanged from 08's.
- **The venv** is untouched (nothing installed). No Ray cluster is up; the rehearsal lock is untouched. The
  only stores opened were temporary ones (the tests' under `tempfile`; the schema builds' and I6's hand run
  under the scratch directory, deleted). DatastoreKit (`38ebb9f`), RayPoolKit, ChamPBH and SGK are untouched.
- **Closed:** `[config-datastore-cannot-be-imported-before-the-layer]` (board §4; `.documents/OPEN-ISSUES.md`
  §7; 60 open, 27 closed). Nothing opened. The README and `.prompts/INDEX.md` are the orchestrator's.
- **Rollback:** `git revert` of `f4da58f` alone; the venv needs nothing (README §4.4). The revert makes any
  store written through the package unreadable by the tree again (none exists but temporary ones).
