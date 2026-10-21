# Prompt 09 — adopt `datastorekit`

**Campaign:** [`README.md`](README.md) · **Board items:** **A1**–**A9** ·
**Board:** [`IMPLEMENTATION_STATE.md`](IMPLEMENTATION_STATE.md)
**Written:** 2026-10-21, with prompts 08, 10 and 11, after 07's review (board §5.19). Measured at
`91e6f31`; 08 changes no Python file, so every line cited here holds at 08's commit unless 08's
results note says otherwise.
**Gate:**
- 08 landed and reviewed (board §1): `datastorekit` `0.4.0` at `c8570e849334…` is installed, not
  editable, and every driver prints it in its provenance line;
- on branch `dk-and-rpk-migration`, no tracked change in `git status`;
- no SI cluster is up (`.documents/dk-and-rpk-migration/rehearsal/ray_cluster.sh status`), and no
  other session runs a suite or a Ray job from this venv while 09 runs.

**Closes:** `[config-datastore-cannot-be-imported-before-the-layer]`. **Opens:** only what the work
finds.
**Recommended model:** **Opus**. One commit, because the tree cannot pass between its parts: the
layer goes, every import of it moves, four pools are rebuilt, the drop policy is new, and the
harness is rebuilt. It is the change that makes every SI store before it unreadable by the tree
(README §7).

**The protected files this prompt touches, and what changes in each** (`CLAUDE.md`, "Protected
infrastructure"; README §5 rule 15):
- **deleted:** `Datastore/SQL/ShardedPool.py`, `Datastore/object.py`,
  `Datastore/SQL/SerialPoolBroker.py`, `Datastore/SQL/ClientPool.py`,
  `Datastore/SQL/ProfileAgent.py`, `Datastore/SQL/ObjectFactories/base.py`, and
  `Datastore/SQL/Datastore.py` (governed by `CLAUDE.md`'s "When a prompt says modify …");
- **emptied** (0 bytes; P6): `Datastore/__init__.py`, `Datastore/SQL/__init__.py`;
- **one import line each, module path only**: the seven protected factories that import
  `SQLAFactoryBase` (`version.py:18`, `store_tag.py:18`, `tolerance.py:20`,
  `DimensionlessQuantity.py:21`, `DimensionfulQuantity.py:20`, `integration_metadata.py:18`, and
  `redshift.py:20`, all under `Datastore/SQL/ObjectFactories/`); `MetadataConcepts/store_tag.py:16`,
  `MetadataConcepts/tolerance.py:20`, `MetadataConcepts/version.py:16`; and
  `Quadrature/integration_metadata.py:18`;
- **`CLAUDE.md`'s protected list and the sentence after it** (P13; §1.7).

Nothing else on the protected list changes. `utilities.py`, `Units/`, `constants.py` and
`Quadrature/supervisors/base.py` are not touched.

**Read first:**

1. `CLAUDE.md`, in full, and `.claude/rules/` (all of it: `pool-read-apis.md`,
   `datastore-factories.md`, `validate-on-startup.md` and `test-selection.md` are touched or bear
   on this prompt).
2. [`README.md`](README.md): §0.1 (items 1–9), §0.4, §0.5, §2.2 (09's charter), §4 (what 09 ships),
   §4.4, §5 (all rules), §6.1 (U3, U4, U5) and §6.2 (P6, P11, P13, P16).
3. DatastoreKit at the tag, read with `git -C /Users/ds283/Documents/Code/DatastoreKit show
   v0.4.0:<path>`, and the installed package. **Read; edit nothing in that repository** (README §5
   rule 12):
   - `docs/adoption/README.md` §2 (the module map), §3 and §4;
   - SI's checklist `docs/adoption/stochasticinstantons.md`, items 2–7 and every addendum;
   - `docs/client-contract.md` §2, §3 and §9;
   - `datastorekit/SQL/ShardedPool.py`: `__init__` (`:106-125`), `_refuse_undeclared_drop_tables`
     (`:811`) and the dependents check after it (`:830-840`), and the replicated prune
     (`_prune_needed`, `_prune_shard`, `_unit_tables`);
   - `datastorekit/SQL/schema.py`: `build_schema` (`:60`), `drop_order` (`:319`),
     `dependent_tables` (`:359`).
4. **ChamPBH's 08, as done** (read only): its prompt `08-adopt-datastorekit.md`, board §5.12a and
   §5.13 with the review below it, in
   `/Users/ds283/Documents/Code/ChamPBH/prompts/dk-and-rpk-migration/`, and its log 08. Its U4 is
   this prompt's U5; its `config.datastore.tables_to_drop` is the model for §1.5. Its harness is
   unittest without Ray and does not carry over; SI's is pytest with a live Ray (§1.6).
5. The results notes of 05, 06 and 07 in `.documents/dk-and-rpk-migration/`; 08's when it lands.
6. `tests/conftest.py`, `tests/test_config_datastore.py`, `tests/test_inflaton_trajectory_prune.py`,
   `tests/test_grid_builder_integration.py` and `tests/test_compare_stores.py:930-950`, in full
   where this prompt changes them.

---

## 0. What this prompt is

The DatastoreKit swap. After it, SI's tree imports no layer of its own, and every pool is the
package's. Nothing a build stores may change (README §5 rule 9); 11 measures that on a real grid.
Here it is held by the suites, the schema snapshot, and two integration tests under real Ray.

**What changed since the charter was written** (measured at `91e6f31` with DatastoreKit's own
script, `docs/extraction/measure_client_imports.py si --commit 91e6f31`, run from DatastoreKit's
root with its venv):
- **48 layer import statements in 47 files, 2 nested**, not the charter's 47: 04 removed
  `RayTools/RayWorkPool.py:23`, and 05 added the fallback at `tests/test_compare_stores.py:944`
  (nested in a `try`). §1.2 lists all 48.
- **3 `import_module` calls naming a layer module**, all in tests 05 and 06 added:
  `tests/test_config_datastore.py:38`, `:39`, and `tests/test_inflaton_trajectory_prune.py:53`.
- **One more import the script cannot see**, inside a code string run in a subprocess:
  `tests/test_inflaton_trajectory_prune.py:459` (`from Datastore.SQL.ShardedPool import
  ShardedPool`), and the pool built there with `drop_actions=` and `inventory_config=` (`:467-472`).
- So **more tests change than the charter named.** Each is named in §1.6, with its reason. Any
  other test that fails is a stop (§4).

---

## 1. What is wanted

### 1.1 The files (A1)

- **Delete** the seven layer modules: `Datastore/object.py`,
  `Datastore/SQL/{ClientPool,Datastore,ProfileAgent,SerialPoolBroker,ShardedPool}.py` and
  `Datastore/SQL/ObjectFactories/base.py` (2,546 lines at `91e6f31`). Remove their ignored
  `__pycache__` files too.
- **Empty** `Datastore/__init__.py` and `Datastore/SQL/__init__.py` (0 bytes; P6). The factories
  stay in `Datastore/SQL/ObjectFactories/`; that package's `__init__.py` is not touched.

### 1.2 The imports (A2)

Rewritten by the adoption README's module map, **module path only**; the names imported do not
change. The 48 statements at `91e6f31`:

| Module now | Becomes | Sites |
|---|---|---|
| `Datastore.SQL.ObjectFactories.base` (`SQLAFactoryBase`) | `datastorekit.SQL.factory_base` | 24: the 22 factory modules; `CosmologyConcepts/Potentials/registry.py:5`; `InflationConcepts/DiffusionModel/registry.py:5` (under `TYPE_CHECKING`) |
| `Datastore` (`DatastoreObject`) | `datastorekit` | 12: `CosmologyConcepts/{DimensionfulQuantity.py:20, DimensionlessQuantity.py:20, Potentials/AbstractPotential.py:6, redshift.py:19}`; `InflationConcepts/{DiffusionModel/__init__.py:6, alpha_regularization.py:20, efold_value.py:5, n_collocation_points.py:22}`; `MetadataConcepts/{store_tag.py:16, tolerance.py:20, version.py:16}`; `Quadrature/integration_metadata.py:18` |
| `Datastore.object` (`DatastoreObject`) | `datastorekit.object` | 6: `ComputeTargets/{CompactionFunction.py:25, FullInstanton.py:23, GradientCoupledInstanton/GradientCoupledInstanton.py:75, InflatonTrajectory.py:24, SlowRollInstanton.py:23}`; `CosmologyModels/cosmo_params.py:19` |
| `Datastore.SQL.ShardedPool` | `datastorekit.SQL.ShardedPool` | 4: `main.py:38`, `plot_GradientCoupledSolutions.py:61`, `plot_InstantonSolutions.py:43`, `tests/conftest.py:25` |
| `Datastore.SQL.ProfileAgent` | `datastorekit.SQL.ProfileAgent` | 1: `main.py:37` |
| `Datastore.SQL.Datastore` (`_factories`) | removed | 1: `tests/test_compare_stores.py:944`, the fallback (§1.6) |

**U3.** The 14 `DatastoreObject.__init__(…, timestamp=…)` calls and the 10 subclasses that pass
`timestamp=` change nothing but their module's import: the package's `DatastoreObject` takes it,
keyword-only, and every SI site passes it by keyword (README §0.4; checked on the installed package
by 08's K7).

### 1.3 The factories (A3)

**Each factory module's diff is its one import line.** They stay instances, their hooks keep
`self`, and 06's `prune`, `owner_column`, `validated_column` and `revalidate` are already in the
package's form. If any factory needs more than its import to work on the package, stop (§4).

### 1.4 The pools (A4)

The four constructions (`main.py:1342-1357`, `plot_GradientCoupledSolutions.py:976-991`,
`plot_InstantonSolutions.py:1210-1227`, `tests/conftest.py:57-71`):
- pass `factories=config.datastore.factories` and
  `serial_batch_sizes=config.datastore.serial_batch_sizes`, by keyword (the package requires
  `factories` by keyword, `ShardedPool.py:122-124`);
- pass no `drop_actions=` and no `inventory_config=` (the package takes neither: a `TypeError`);
- `main.py`'s passes `drop_tables=` (§1.5); the plot scripts and `live_pool` pass none;
- keep every other argument as it is. The plot scripts stay read-write (P10).

`config/sharding.py`'s `inventory_config` stays until 10 deletes it with the hooks (README §2.2,
10's item 4). The drivers stop importing it. `read_table_config` stays and is passed as before.

Two behaviours of the package differ from the layer's and need no change, but the results note
says so: a table with no batch size leases **500** serials at a time, not 5 (no SI table leases
under the old fallback: 05's results note), and `serial_batch_sizes`' `temperature` entry, a
ChamPBH leftover with no table (P12), is ignored.

### 1.5 U5, the drop policy (A5)

`main.py`'s `--drop` takes groups (`config/argument_parser.py:52-63`); the package takes tables and
refuses a drop that leaves references. **Before Ray starts** (`main.py:100`, `ray.init`), `main.py`
turns the requested groups into tables through `config.datastore.drop_groups` and checks the
closure with `datastorekit.SQL.schema.dependent_tables(tables, factories)`. If a dependent table is
not among the requested ones, it refuses, on stderr, naming the groups to add, and exits 2, having
created nothing. Put the logic in a function of `config/datastore.py`, as ChamPBH's
`tables_to_drop` (its log 08, D1), so that it is tested without `main.py`.

At this tree (no `inventory_spec` is declared yet; foreign keys alone):
- `compaction-function` and `gradient-coupled-instanton` are closed alone;
- **`full-instanton` alone** and **`slow-roll-instanton` alone** are refused: `CompactionFunction`
  names both (`CompactionFunction.py:44`, `:51`). The message names `compaction-function`;
- **`inflaton-trajectory`** is refused unless every sharded family comes with it:
  `FullInstanton`, `SlowRollInstanton`, `GradientCoupledInstanton` and `CompactionFunction` name it.

A test pins the message for each of the three unclosed groups, and accepts each closed set,
including all five together. The wording is yours; say it in the results note.

**One inherited hazard, recorded, not fixed:** a closed set with `inflaton-trajectory` drops a
**replicated** table, which DatastoreKit's own issue
`[00-a-drop-action-drops-a-replicated-table-outside-the-in-flight-record]` says an interrupted drop
can leave unopenable. It is the package's (README §5 rule 11). Record it under "Observations"; no
test drops a replicated table on a real store.

### 1.6 The harness and the tests (A6)

**Named exceptions to README §5 rule 7**, each with its reason. No other existing test changes.
1. **`tests/conftest.py`'s `live_pool`** (`:36-74`): the package's pool, with `factories=` and
   `serial_batch_sizes=`, without `drop_actions=` and `inventory_config=`; its import moves. Its
   `ray.init(ignore_reinit_error=True)` and teardown stay. The 61 integration tests that reach it
   (all but 06's I6, which builds its own pools) change only where an import does.
2. **`tests/test_grid_builder_integration.py:113-140`**: the row counts without `pool.inventory`,
   which the package lacks. Through `live_pool.read_table(...)` (`N_init`, `N_final` and
   `delta_Nstar` are replicated and in `read_table_config`), or by a `sqlite3` `mode=ro` read of
   the temporary shard; say which, and why.
3. **`tests/test_config_datastore.py`**, 05's test of the moved data:
   - its two `import_module` calls of the layer (`:38-39`) go: the cycle they work around is
     gone (§1.8);
   - `test_layer_reads_the_data_from_config_datastore` (`:173-176`) and
     `test_layer_drop_order_names_exactly_the_drop_groups` (`:179-181`) test the deleted layer.
     They are deleted, and replaced by a test that the four pool constructions pass
     `config.datastore`'s two objects (an `ast` test over the four files: each `ShardedPool(...)`
     call has `factories=` and `serial_batch_sizes=` naming them, and no `drop_actions=` or
     `inventory_config=`);
   - `test_importing_the_data_starts_no_ray` (`:184-201`) imports `config.datastore` **alone** in
     its fresh process, which is the closing test of `[config-datastore-cannot-be-imported-before-the-layer]`;
   - its module docstring is corrected; the captured literals are unchanged.
4. **`tests/test_inflaton_trajectory_prune.py`**, 06's:
   - its `import_module` of the layer (`:53`) and the comment over it go;
   - **I6, the integration test** (`:449` on): its subprocess script builds the **package's**
     `ShardedPool`, with `factories=` and without `drop_actions=` and `inventory_config=`. This is
     acceptance 4 (§3): the prune at reopen is then the package's replicated prune
     (`_prune_shard`), which polices the unit through `owner_column`. Keep the two processes and
     both reads of the shards; the package's `__exit__` kills its actors (contract §9.3), so one
     process would also do, but the test's structure does not need to change;
   - its Ray-free tests keep their store helper if it still builds all 30 tables; if the layer's
     rule it mirrors (`serial`, `version`, `timestamp`, `stepping`) no longer matches, build with
     `datastorekit.SQL.schema.build_schema` instead and say so;
   - the signature test still counts 12 hooks by each class's own `__dict__`; the inherited one
     is now the package's base's.
5. **`tests/test_compare_stores.py:938-945`**: `_registry()`'s `try`/`except ImportError` fallback to
   the layer goes; it imports `config.datastore` directly. Its tests are otherwise unchanged.
   (`tools/compare_stores.py` itself imports no layer and does not change.)

**New tests** (README §5 rule 10):
- U5's (§1.5), without Ray;
- the pool-construction `ast` test (item 3 above), without Ray;
- **U3 through the package** (acceptance 5), `integration`;
- `--inventory`'s refusal (§1.7), without Ray: a subprocess with an address nothing listens on and a
  timeout, as ChamPBH's, and an `ast` check that the refusal precedes `ray.init`.

### 1.7 `--inventory`, and the prose (A7)

- **`--inventory` refuses until 10 (P11).** `main.py` prints, on stderr, that the inventory is
  unavailable until it is ported (dk-and-rpk-migration prompt 10), and exits 2, **before Ray
  starts**, creating nothing. The five helpers (`inventory`, `_inventory_dimensionless`,
  `_inventory_dimensionful`, `_inventory_efold`, `_inventory_object`; `main.py:1227-1304`), their
  four `pool.inventory` calls, and the two printers only they call (`_print_value_list`,
  `_print_label_list`; `:1307-1338`) are deleted, with any import left unused only by them.
- **The prose this commit makes false** (P13), corrected in it:
  - `CLAUDE.md:95-119`: the protected list loses the seven deleted files (`:101-104`), and the
    sentence on modifying `Datastore/SQL/Datastore.py` (`:117-119`) is replaced by one saying the
    layer is the package's and is changed in DatastoreKit, reaching SI through its pin;
  - `.claude/rules/pool-read-apis.md`, its title and `:1-35`: `pool.inventory()` does not exist; say so, and that the
    inventory is `read_inventory` on a closed store from 10;
  - `.claude/rules/datastore-factories.md:245-301`, "Replicated-table factories MUST honour a
    supplied `serial`": the account of how the layer replicates a row is now the package's
    recorded write, checked at open; the requirement on `build` stands. Correct the account, not
    the rule;
  - `.claude/memory/bug-assign-shard-keys-key-id.md:24` and `shard-key-assignment-bug.md`: a
    status line that the fix now lives in the package (`_assign_shard_keys`; checklist item 10);
  - `.documents/FILE_MAP.md`: the rows of the seven deleted files (`:40-42`, `:54` and the others
    the file has) and the `config/datastore.py` row (`:18`);
  - `config/datastore.py`'s docstring (`:32-45`), on the import order: the cycle is gone.

  `.documents/INFRASTRUCTURE.md` and `.documents/architecture-summary.md` describe the layer at
  length; they are 12's (P13). List what in them is now stale, for 12.

### 1.8 The closed issue (A8)

`[config-datastore-cannot-be-imported-before-the-layer]`: with `Datastore/SQL/__init__.py` empty,
nothing imports the layer, and `./venv/bin/python -I -c "import config.datastore"` from the
repository root (with the root on `sys.path` by `PYTHONPATH`, not `-I`'s default; say how you ran
it) exits 0. Close it on the board (§3 → §4, with how) and in `.documents/OPEN-ISSUES.md` (§6a →
§7, the count and the date) in the same commit.

---

## 2. What to do

### 2.1 Before

1. Record `HEAD`, the load (`uptime`) and `git status --short`.
2. **The suites at the gate**, serially, before any edit: the default and the integration run
   (README §5 rule 17). They should be 08's counts (07's, **696** and **62**).
3. **Re-measure** with DatastoreKit's script at your `HEAD` (from DatastoreKit's root, its own
   venv), and `git grep` for `Datastore.SQL`, `Datastore.object`, `ObjectFactories.base`,
   `from Datastore import`, `drop_actions`, `inventory_config` and `.inventory(` outside
   `.prompts/` and `.documents/`. Every hit must be in §0, §1.2, §1.4, §1.6 or §1.7. An
   unaccounted hit is a stop.
4. **Snapshot the schema at the gate**: a two-shard temporary store built through SI's pool under a
   private Ray (`ray.init(address="local")`, in a separate process, in your scratch directory), as
   06's `schema_build.py` did (06's results note), compared with `out/07-reference-schema.json`.
   This is the baseline for acceptance 3.

### 2.2 The change

§1.1–§1.8, in one working tree. Do not commit until §2.3 holds.

### 2.3 Verification

1. **By DatastoreKit's script**, at a dangling commit of the staged tree (`git commit-tree` of
   `git write-tree`, on no branch, as ChamPBH's 08 did): none of the 7 deleted modules present; the
   two `__init__.py` present and 0 bytes; outside `.prompts/` and `.documents/`, 0 layer imports, 0
   string literals and 0 `import_module` calls. Also `git grep` for the five layer module names
   inside string literals (the subprocess scripts): none.
2. **Without Ray** (`ray.is_initialized()` `False` after each):
   - `import config.datastore` alone, in a fresh process: 30 entries, each an instance of
     `datastorekit.SQL.factory_base.SQLAFactoryBase`;
   - `./venv/bin/python -m datastorekit.tools.sharded_store --help` exits 0;
   - the three drivers byte-compile, and every module they import resolves (by `ast`; none
     executed: 04's results note has the script);
   - `main.py --database <scratch>/x.sqlite --ray-address 127.0.0.1:9 --inventory`, and the same
     with `--drop full-instanton`: each prints the provenance line and its refusal, exits 2, and
     creates no file.
3. **The schema.** A two-shard temporary store built through the **rebuilt** harness (the
   package's pool, `factories=`), snapshot by `tools/compare_stores.py --snapshot`, against §2.1.4's
   and `out/07-reference-schema.json`: "the schemas agree", or each difference listed. The package
   prepends `serial`, `version`, `timestamp`, `stepping` (contract §2), as SI's layer did; ChamPBH's
   08 found no difference. Keep the snapshot as `out/09-temp-schema.json`.
4. **The suites**, serially:
   - default: 08's count, less the tests deleted with a named reason (§1.6 item 3: 2), plus 09's new
     ones; derive the count by module in the results note;
   - integration (`RAY_ADDRESS=local`): 08's 62, plus the U3 test;
   - **`slow`, once** (README §5 rule 16; the diff touches `ComputeTargets/`), as a background task
     writing to your scratch directory, waited on by notification: **69 passed**, S1's baseline
     (02's results note). A failure is re-run alone before it is recorded.
5. **`ruff check --select F401,F811,F821`** on every Python file the diff touches: no finding the
   gate did not have.

### 2.4 Deliberate breakage (README §5 rule 8)

Each applied to the clean change, the named test run, then reverted. Record each as a diff that
replays with `git apply`.
1. One factory's `SQLAFactoryBase` import pointed back at `Datastore.SQL.ObjectFactories.base`:
   collection fails (`ModuleNotFoundError`), and §2.3.2's import check names it.
2. `timestamp=row.timestamp` dropped from `sqla_FullInstantonFactory.build`: acceptance 5's test
   fails on the sharded object.
3. `owner_column` removed from `InflatonTrajectoryValue`'s `register()`: the package refuses the
   cascading prune, and acceptance 4's test fails (name the refusal).
4. The closure check removed from §1.5's function: U5's test fails for each unclosed group.
5. `factories=` dropped from `live_pool`: the integration suite errors at setup (`TypeError`), and
   the pool-construction `ast` test names `tests/conftest.py`.
6. The `--inventory` refusal moved after `ray.init`: its `ast` test fails.

---

## 3. Acceptance

1. **By DatastoreKit's script**, at the commit: the 7 modules gone, the two `__init__.py` 0 bytes;
   outside `.prompts/` and `.documents/`, 0 import statements, 0 string literals and 0
   `import_module` calls naming a layer module.
2. **The suites**: the default and integration counts of §2.3.4, all passing (1 skipped each, as
   before, unless the results note names why); `slow` 69 passed.
3. **Without Ray**, §2.3.2 and §2.3.3: `config.datastore` imports alone; `sharded_store --help`
   exits 0; the drivers byte-compile and resolve; the refusals exit 2 before Ray; the schema agrees
   with RH1's, or each difference is listed.
4. **Under real Ray: the package's replicated prune** (U4). 06's I6, rebuilt on the package (§1.6
   item 4): on a 2-shard temporary store, an unvalidated `InflatonTrajectory` and its value rows
   are pruned at reopen on both shards, the validated one kept with all its value rows, no orphan,
   and no refusal.
5. **U3 through the package**: an integration test through `live_pool` that a replicated object
   (a `delta_Nstar`) and a sharded one (a `FullInstanton`), each fetched back after it is stored,
   carry a `timestamp` that is not `None` and equals the row's `timestamp` column read with
   `sqlite3` `mode=ro`.
6. **The breakages of §2.4**, all caught.
7. **The records**, in the one commit:
   - this board: the §1 row for 09, items A1–A9 (A9 is the results note's record of the
     verification), `### 5.N After prompt 09 (<date>)` with the rollback (`git revert` alone;
     nothing in the venv, README §4.4), and the closed issue moved §3 → §4;
   - `.documents/OPEN-ISSUES.md`: the closed issue moved to §7, the counts and the date; any issue
     opened, added;
   - `out/09-temp-schema.json`.

---

## 4. Stop conditions — stop and ask

- The gate's suites are not 08's counts, or §2.1.3 finds a hit §0–§1 do not account for.
- A factory needs more than its import line to work on the package; a hook the package calls
  behaves differently from the layer's call; or the package refuses anything SI's tree does that
  §1 does not name. **Do not work around a package defect in SI** (README §5 rule 11).
- Any existing test outside §1.6's list fails, or would need a change.
- The schema differs from RH1's in anything but the prepended columns' order.
- The `slow` block fails, re-run alone, where S1 passed.
- Acceptance 4's prune is refused by the package.
- Anything would need a change in DatastoreKit, RayPoolKit, ChamPBH or SecondaryGWKit, or in the
  venv.

---

## 5. What this prompt does not do

- **Files it changes:** the 9 layer files (deleted or emptied); the 47 files of §1.2; `main.py` and
  the two plot scripts (§1.4, §1.5, §1.7); `config/datastore.py` (§1.5, its docstring);
  `tests/conftest.py` and the four test modules of §1.6; the new test module(s); `CLAUDE.md`,
  `.claude/rules/pool-read-apis.md`, `.claude/rules/datastore-factories.md`,
  `.claude/memory/bug-assign-shard-keys-key-id.md`, `shard-key-assignment-bug.md`,
  `.documents/FILE_MAP.md`; `out/09-temp-schema.json`; the results note; this board;
  `.documents/OPEN-ISSUES.md`.
- **Not:** `config/sharding.py` (its `inventory_config` is 10's), any factory beyond its import line,
  `tools/compare_stores.py`, the rehearsal scripts, `requirements.txt`, the README,
  `.prompts/INDEX.md`, anything in another repository, anything in the venv.
- **The inventory** is 10's: no `inventory_spec`, no report.
- **No store but temporary ones**, under your scratch directory or `tempfile`. 09 runs no build, no
  cluster and no rehearsal. It opens none of RH0's or RH1's stores, the June or July stores, or
  anything under `out-*/` or `~/ScienceData/`.

---

## 6. The results note

`.documents/dk-and-rpk-migration/09-adopt-datastorekit.md`, using README §5.1. It holds:
- the gate's measurement (§2.1), the script's output before and after;
- each file's diff summarised, every factory's and concept module's shown to be its import line
  alone (an `ast` comparison with the module path normalised, as ChamPBH's 08 review did);
- U5's function, its message for each unclosed group, and the closed sets;
- the harness change, and each test changed under §1.6 with its reason;
- §2.3's checks with commands and output; the suites by module beside 08's; `slow`'s result;
- the breakages as diffs;
- the prose corrected, and the list of what remains stale for 12;
- "State handed to the next prompt": for 10, the suites' counts, U5's table (10's specs may move
  it: `dependent_tables` reads `inventory_spec` parents too), and what `--inventory` must replace;
  for 11, what a build now prints that RH1's did not (the package's actor and pool lines).

**One commit**, in the repository's form, staged by explicit path only (deletions with `git rm`),
after showing `git diff --cached --name-only`.
