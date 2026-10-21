# Orchestrator — prompt 09, adopt `datastorekit`

Read [`../README.md`](../README.md) first: §0.1, §0.4, §0.5, §2.2 (09's charter), §4.4, §5 (all
rules) and §6.2 (P6, P11, P13, P16). The conventions are [`prompt-01.md`](prompt-01.md)'s §0
"Conventions", unchanged but where this note says otherwise; [`prompt-06.md`](prompt-06.md)'s
"Conventions particular to 06" hold too (git, Ray, formatting, scratch). The model is ChamPBH's 08
(its board §5.12a, §5.13 and the review below it); what it found that applies is in §0.

**You do not write code.** You may:
- run the suites, `ruff check`, DatastoreKit's measuring script (from its root, its venv),
  `tools/compare_stores.py` and read-only Python checks, from the session scratchpad;
- build temporary stores in the scratchpad under a private Ray (`ray.init(address="local")`), in a
  separate process;
- export a tree into the scratchpad and run it there (with `STOCHASTIC_INSTANTONS_REPO` set to the
  export; §0 correction 7);
- replay the results note's deliberate-breakage diffs with `git apply`, and revert them;
- fix small residue in a follow-up commit of your own (§4).

**The prompt:** [`09-adopt-datastorekit.md`](../09-adopt-datastorekit.md) · **Board items:**
A1–A9 · **Closes:** `[config-datastore-cannot-be-imported-before-the-layer]` · **Narrows:**
nothing · **Opens:** only what the work finds · **Model:** Opus, as the prompt recommends · **No
network.**

**Gate:**
- 08 landed (`1b1ca6d`) and was reviewed (`e797705`): `datastorekit` `0.4.0` at `c8570e849334…`
  installed, not editable; every driver prints it.
- `HEAD` is the commit that adds this note, or a later one that touches no code ("code" as
  prompt-01.md's gate defines it). `git diff --stat 1b1ca6d HEAD -- . ':!.prompts' ':!.documents'`
  is empty.
- No SI cluster is up, and **no other session runs a suite or a Ray job from this venv, or installs
  into it, while 09 runs** (README §4.4).

## 0. What makes this prompt unusual

**It is the swap.** Every pool becomes the package's, the layer goes, and every SI store written
before it becomes unreadable by the tree (README §7). It is the largest diff of the campaign (about
60 files), and most of it is mechanical: 48 import lines. The review's effort goes where the
mechanical part can hide a change, and where the new parts can pass vacuously:
- **"Each factory's diff is its import line"** is checked by `ast`, with the module path
  normalised, over every file of §1.2 (as ChamPBH's 08 review did: 30 of 30 identical). A factory
  edited beyond its import, to make it work on the package, would be a §4 stop the diff hides.
- **The integration suite passing is evidence only because `live_pool` is the package's.** A
  harness left on the layer by accident cannot exist after the deletion (it would not import), but
  a pool constructed without `factories=` would fail loudly; one constructed with a *different*
  registry would not. The pool-construction `ast` test pins the name.
- **U5's test can pass on a table that matches by luck.** Its truth is `dependent_tables`'
  closure, which the orchestrator measured over all 31 subsets (correction 9). The review replays
  the function over all 31.
- **Acceptance 5 can pass vacuously** if the `timestamp` compared is read through the same object,
  or if the row read with `sqlite3` is not the row the object came from. The test reads the shard
  file by `serial`.
- **The `slow` block, run once.** It is the only run of the real solves through the package's
  `DatastoreObject`; S1's 69 is the bar.

**The orchestrator prototyped the change** (correction 10), mechanically, in a scratch export of
`HEAD`. It holds at every point the prompt names: nothing found is a §4 stop. That is a measurement,
not the agent's work: the agent does its own, and the review compares.

**Corrections to the prompt.** Pass them on.
1. **The board section** is **`### 5.22 After prompt 09 (<date>)`**, appended after §5.21. The
   header's "Last updated" and status line are updated to match. A1–A9 are already rows in board
   §1.1; fill in their state. Closing the issue moves its row from board §3 to §4 (with how), and in
   `.documents/OPEN-ISSUES.md` from §6a to §7 "Closed" (`| Issue | Closed | By |`), the header
   **61 → 60 open, 26 → 27 closed**, the date.
2. **§2.1.3's greps find more than §0–§1 list, and none of it is a stop.** Measured at `e797705`
   (outside `.prompts/` and `.documents/`):
   - `Datastore\.SQL` (75 lines) also matches **the factory-module imports**, which stay (the
     factory package stays): `config/datastore.py:45-98` (22 statements),
     `CosmologyConcepts/Potentials/registry.py:6-7`, `tests/test_compare_stores.py:973`. It also
     matches the layer's own files (deleted), `config/datastore.py:32-41` (the docstring, §1.7),
     `tests/test_config_datastore.py:18-28` (the docstring) and `:188` (the subprocess code
     string; both §1.6 item 3);
   - `Datastore\.object` also matches `Datastore/SQL/Datastore.py:421`, a comment in the layer;
   - `drop_actions` outside the layer: the six sites `main.py:1354`,
     `plot_GradientCoupledSolutions.py:988`, `plot_InstantonSolutions.py:1224`,
     `tests/conftest.py:68`, `tests/test_config_datastore.py:175`,
     `tests/test_inflaton_trajectory_prune.py:471`;
   - `inventory_config` and `.inventory(` also match `config/sharding.py:78` (a comment) and `:97`
     (the definition), which stay for 10 (§1.4); `.claude/rules/pool-read-apis.md` (§1.7);
     `tests/test_grid_builder_integration.py:115` (the docstring of the test §1.6 item 2 changes);
     `Datastore/SQL/Datastore.py:714` (the layer).

   `.inventory(` must be grepped as a fixed string (`git grep -F`); as a regex it is unbalanced.
   DatastoreKit's script at `e797705` gives exactly the prompt's §0: **48 statements in 47 files, 2
   nested; 0 literals; 3 `import_module`**.
3. **`read_table_config` has no `N_init` or `N_final` entry** (`config/sharding.py:66-76`: it has
   `delta_Nstar` and seven others). So §1.6 item 2's first route fails for two of the three
   tables, and `config/sharding.py` is not 09's to change. **Use the `sqlite3` `mode=ro` read** of
   the temporary shard. The package names it `<stem>-shard0000.sqlite` beside the primary
   (`datastorekit.shard_paths.shard_file_name(primary, serial)`); the pool's primary is
   `live_pool.primary` (a public property of the package's pool). The three tables have a `value`
   column. Say so in the results note.
4. **Breakage 2's line** is `timestamp=row_data.timestamp`, at
   `Datastore/SQL/ObjectFactories/FullInstanton.py:180` (not `row.timestamp`).
5. **`shard-key-assignment-bug.md` is at the repository root**, not under `.claude/memory/`.
   `.claude/memory/bug-assign-shard-keys-key-id.md:24` is as the prompt says. The package's fix is
   `ShardedPool._assign_shard_keys` with `key_serial` (`v0.4.0`, `:917`, `:1176-1181`).
6. **Stale citations outside 09's file list**, for the list for 12 (§1.7), not edited:
   `tools/compare_stores.py:39`, `:94`, `:115`, `:116` (paths into `Datastore/SQL/ShardedPool.py`
   and `Datastore.py`; the last two inside its bookkeeping-reason strings) and
   `tests/test_rehearsal_stage_counts.py:26` (a docstring). ChamPBH's 08 met the same in its
   `compare_stores.py`. **§2.3.1's grep "for the five layer module names inside string literals"**
   is for the dotted names, `Datastore\.(SQL\.(ShardedPool|Datastore|ClientPool|ProfileAgent|SerialPoolBroker)|object)\b`
   and `ObjectFactories\.base`; those path citations are not module names and do not fail it. List
   them. Also `.documents/FILE_MAP.md:273-275` name three deleted files in its "not included" table:
   they are rows of deleted files, under §1.7's `FILE_MAP.md` item.
7. **`tools/diagnostics/GradientCoupledInstanton/harness.py:70-73` puts the checkout on `sys.path`**
   (`/Users/ds283/Documents/Code/StochasticInstantons`, hard-coded) unless
   `STOCHASTIC_INSTANTONS_REPO` is set. In the checkout this is harmless. Run from any copy of the
   tree outside it (an export of the dangling commit, say), the suites import the checkout's
   modules, silently. Run nothing from a copy without `STOCHASTIC_INSTANTONS_REPO` set to the copy.
   DatastoreKit's script reads through `git` only and is unaffected.
8. **Where the refusals go in `main.py`.** The database check is `:93-95`, the provenance print
   `:99`, `ray.init` `:100`. The two refusals go **after the provenance print and before
   `ray.init`** (§2.3.2 expects the line printed first). The inventory helpers are
   `:1227-1304` (`inventory` `:1227`, the four `_inventory_*` from `:1250`), the printers
   `:1307-1338`. `UnitsLike` stays (`execute`, `:1127`, uses it); `ShardedPool` and `ProfileAgent`
   stay (`:1327-1340` constructs the package's `@ray.remote` `ProfileAgent` with the same
   `db_name`, `timeout`, `label`). `--drop` is `nargs="*"`, default `[]`
   (`config/argument_parser.py:51-63`).
9. **U5, measured on the installed package** (`dependent_tables` over SI's registry, every one of
   the 31 non-empty subsets of the five groups; `orch09/u5_proto.py`): **10 closed, 21 refused.**
   The closed sets: `compaction-function`; `gradient-coupled-instanton`; each of `full-instanton`,
   `slow-roll-instanton`, `gradient-coupled-instanton` with `compaction-function`, in any
   combination of them (seven sets, these two among them); and all five. **No closed set holds
   `inflaton-trajectory` but all five.** Alone:
   - `full-instanton` and `slow-roll-instanton`: the dependents are `CompactionFunction`,
     `CompactionFunctionSamples`, so the group to add is `compaction-function`;
   - `inflaton-trajectory`: nine dependent tables, so `compaction-function`, `full-instanton`,
     `gradient-coupled-instanton`, `slow-roll-instanton`.

   Every dependent table at this tree belongs to a group, so the message can always name groups.
   The package refuses the same drops itself, at open, after Ray
   (`_refuse_drop_that_leaves_references`, `ShardedPool.py:825-843`); SI's check is the earlier
   one, and breakage 4 removes only SI's. The test asserts the closure decision for all 31 (or
   says why fewer), and the message for the three unclosed singletons.
10. **The orchestrator's prototype**, at `e797705`, in a scratch export (`orch09/proto/`): the 7
    files deleted, the two `__init__.py` emptied, the 48 imports rewritten by `sed`, the four pools
    and I6's script given `factories=` and `serial_batch_sizes=` and stripped of `drop_actions=`
    and `inventory_config=`, the two layer tests and three `import_module` lines deleted, the
    fallback removed. **Not** done: U5, the refusals, the inventory deletion, the grid-builder
    test, the prose, any new test. Run with `STOCHASTIC_INSTANTONS_REPO` set to the export:
    - `import config.datastore` alone, `-I`: **30 entries, every one an instance of
      `datastorekit.SQL.factory_base.SQLAFactoryBase`**, `ray.is_initialized()` `False`. (At the
      gate the same check gives `False` for "every one": they are the layer's base's.)
    - default: **693 passed, 1 skipped** (694 = 696 − the 2 deleted), 33 s;
    - integration (`RAY_ADDRESS=local`): **60 passed, 1 skipped, 1 failed**, 33 s. The failure is
      exactly `test_grid_builder_integration.py::…::test_no_duplicate_rows_created`,
      `AttributeError: 'ShardedPool' object has no attribute 'inventory'`, which §1.6 item 2
      rewrites. **06's I6 passes on the package's pool**: the package's replicated prune takes, no
      refusal, no orphan (acceptance 4);
    - a two-shard store built through the package's pool (`orch09/schema_build_pkg.py`):
      `compare_stores.py --schema` against `07-reference-schema.json`, `05-temp-schema.json` and
      `02-reference-schema.json`: **"the schemas agree"** each time. The shards have the 30 tables.
      The primary holds the package's `replication_in_flight` beside SI's five tables (for 11's
      account of what changed; the snapshot does not compare it);
    - `slow`: **69 passed** (11 warnings, S1's), 385 s, at loads of 4–18.
11. **The suites at the gate**, from 08's review at `1b1ca6d` (no Python has changed since):
    **696 (695 passed, 1 skipped)** and **62 (61 passed, 1 skipped)**; `slow` **69** (collected
    69 at `e797705`; S1's 69 passed). The modules §1.6 touches: `test_config_datastore.py` 7,
    `test_inflaton_trajectory_prune.py` 6 + 1 integration, `test_compare_stores.py` 24,
    `test_grid_builder_integration.py` 3 integration. The suites run as README §5 rules 16–17 say,
    serially, in the foreground; `slow` in the background with a notification, as the prompt says.
12. **The docstrings of the named tests** that 09 makes false are corrected with them (P13):
    `tests/test_config_datastore.py`'s module docstring (the prompt says so),
    `tests/test_inflaton_trajectory_prune.py`'s module docstring (`:16-37`, "SI's own
    `ShardedPool`", "`Datastore._build_schema`", the import order) and I6's (`:558-567`, "the old
    layer", "SI's `__exit__` does not free the names"; the package's does, contract §9.3),
    `tests/test_compare_stores.py`'s `_registry()` docstring, and `tests/conftest.py`'s where it
    describes the pool. Docstrings and comments only; the review compares the bodies by `ast`.
13. **ChamPBH's 08, what applies.** Its U4 message named the tables that reference the requested
    ones directly, and let the closure decide (its log D1); its `--inventory` test used an address
    nothing listens on and a timeout; its `ast` order test is on module-level statements. It met
    the same stale citations in `compare_stores.py`. It had no `slow` block and no live-Ray
    harness; SI's has both, so its harness (a stand-in pool under `unittest`) does not carry over.
14. **`.prompts/INDEX.md` and the README are the orchestrator's.** The agent touches neither.

**The facts, checked by the orchestrator on 2026-10-21 at `e797705`, 17:35–17:50 BST.** Pass them
on.
- **The tree.** Branch `dk-and-rpk-migration`, clean, `HEAD` `e797705` before this note. `git diff
  --stat 91e6f31 HEAD` outside `.prompts/` and `.documents/` is `requirements.txt` alone (08's
  pin). The 17 store files of prompt-01.md §1 step 5 are in the tree (ignored); 09 opens none.
- **Ray and the lock.** `ray_cluster.sh status`: lock free, no `/tmp/ray-si` process, the four
  ports free. `pgrep` finds no `gcs_server`, `raylet`, `ray::`, `pytest`, `unittest` or `main.py`.
  `RAY_ADDRESS` unset.
- **The load** was 10–18 (1 min) on 10 CPUs. It affects only the suites' times.
- **The venv.** `pip freeze` 83 lines: 08's, with `datastorekit @ …@c8570e84…` and `raypoolkit @
  …@eaef0ce6…`; `pip check` clean. 09 installs nothing.
- **The layer**: 2,546 lines in the seven modules (`object.py` 45, `ClientPool.py` 230,
  `Datastore.py` 716, `ProfileAgent.py` 355, `SerialPoolBroker.py` 164, `ShardedPool.py` 1,001,
  `base.py` 35); `Datastore/__init__.py` is `from .object import DatastoreObject`,
  `Datastore/SQL/__init__.py` `from .Datastore import Datastore`.
- **The package at `v0.4.0`**, at the lines the prompt cites: `ShardedPool.__init__` `:106-125`
  (`factories` and `serial_batch_sizes` keyword-only, `drop_tables`, no `drop_actions` or
  `inventory_config`); `_refuse_undeclared_drop_tables` `:811`; `read_table` `:3695`, which refuses
  a sharded table or one not in `read_table_config`; no `inventory` method. `schema.py`:
  `build_schema` `:60`, `drop_order` `:319`, `dependent_tables` `:359`. The pool methods SI calls
  (`object_get`, `object_get_vectorized`, `object_store`, `object_validate`, `read_table`) all
  exist; `inventory` is called only at `main.py:1253-1285` and the grid-builder test.
- **The line numbers of the prompt** hold at `e797705`: the four pool constructions
  (`main.py:1342-1357`, `plot_GradientCoupledSolutions.py:976-991`,
  `plot_InstantonSolutions.py:1210-1227`, `tests/conftest.py:57-71`); `live_pool` `:36-74`;
  `test_grid_builder_integration.py:113-140`; `test_config_datastore.py:38-39`, `:173-176`,
  `:179-181`, `:184-201`; `test_inflaton_trajectory_prune.py:53`, `:449` on, `:459`, `:467-472`;
  `test_compare_stores.py:938-945`; `CLAUDE.md:95-119` (the seven at `:101-104`, the sentence
  `:117-118`); `datastore-factories.md:245` on; `FILE_MAP.md:18`, `:40-42`, `:54`.
- **DatastoreKit** `38ebb9f`, **RayPoolKit** `17029d9`, both clean.
- **The stores.** 09 opens only temporary ones: the tests' (under `tempfile`) and the schema builds'
  (under the agent's scratch directory). Not the 17 in the tree, nothing under `out-*/` or
  `~/ScienceData/`.

**What the review exists to establish.**
- **(E1) A1, the deletion.** The 7 modules gone (and their `.pyc`), the two `__init__.py` 0 bytes;
  by DatastoreKit's script at the commit, 0 imports, 0 literals, 0 `import_module`.
- **(E2) A2–A3, the imports only.** Every file of §1.2 differs from its gate by its import's module
  path, by `ast`; nothing else in any factory, concept or compute-target module.
- **(E3) A4, the pools.** The four constructions pass `config.datastore`'s two objects by keyword,
  no `drop_actions=`, no `inventory_config=`; `main.py`'s passes `drop_tables=`; every other
  argument as before; the drivers stop importing `inventory_config`.
- **(E4) A5, U5.** The function decides by `dependent_tables`, refuses before Ray, exits 2, creates
  nothing; its decisions over the 31 subsets equal correction 9's.
- **(E5) A6, the harness and tests.** `live_pool` is the package's; each changed test changes as
  §1.6 names and no other; the new tests are not vacuous; acceptance 4 and 5 hold under real Ray.
- **(E6) A7–A8, the refusal, the prose and the closed issue.** `--inventory` refuses before Ray;
  the seven helpers gone; the prose of §1.7 true; `import config.datastore` alone exits 0; the
  issue closed on the board and in the index.
- **(E7) A9, the verification and nothing else moved.** The schema agrees; the suites at 694 + new,
  62 + new, `slow` 69; the breakages caught; no file outside the prompt's §5 list; the venv, the
  other repositories and every store untouched.

## 1. Before you dispatch

1. **The tree.** `git status --short` clean, `git diff --cached` empty, `git log` since `1b1ca6d`
   records only.
2. **Ray and the lock.** `ray_cluster.sh status` clean; no Ray process.
3. **The venv.** `pip freeze` saved; `pip check` clean.
4. **The load**, recorded.
5. **Mtimes**, for check 11: the 17 store files, and every entry under `~/ScienceData/`.
   DatastoreKit's and RayPoolKit's `HEAD` and `git status --porcelain`.
6. **The measurements of §0**: DatastoreKit's script, the greps, the line numbers, U5 over the 31
   subsets, the prototype with its three suites and schema check.

**Done 2026-10-21, 17:35–17:50 BST,** at `e797705`: all six hold, step 6 as §0 records (the
prototype's `slow` run finished at 17:48, 69 passed, before dispatch). In `orch09/` in the session scratchpad:
`pip-freeze.txt` (83), `mtimes-stores.txt` (17), `mtimes-sciencedata.txt` (835 entries, the root
included), `measure-e797705.md`, `u5_proto.py` and its output, `schema_build_pkg.py`, `proto/`,
`proto-default.txt`, `proto-integration.txt`, `proto-slow.txt`, `default-by-module.txt`,
`integration-by-module.txt`. DatastoreKit `38ebb9f` and RayPoolKit `17029d9`, both clean.

## 2. Dispatch

One fresh-context subagent, on **Opus**, in the background. Give it:
- the prompt;
- the campaign README and the board;
- 05's, 06's and 08's results notes (the schema-build script, the I6 design, the form of a results
  note, the provenance line);
- `HEAD`, the load and §0 of this note, up to "## 1. Before you dispatch" only, as a copy in the
  session scratchpad. It does not read `orchestrator/`, and does not read prompts 10–11. It may
  read `orch09/u5_proto.py` and `orch09/schema_build_pkg.py`, and owes them nothing.

Tell it plainly:
- **One commit, at the end, made once.** Its results note is
  `.documents/dk-and-rpk-migration/09-adopt-datastorekit.md`, in README §5.1's form, with the
  prompt's §6 additions. Stage by explicit path (deletions with `git rm`), and show
  `git diff --cached --name-only` before committing.
- **The files it may change** are the prompt's §5 list, with `shard-key-assignment-bug.md` at the
  root (correction 5) and the docstrings of correction 12. **Not** `config/sharding.py`,
  `tools/compare_stores.py`, `tests/test_rehearsal_stage_counts.py`, any factory beyond its import
  line, any test outside §1.6, the README, `.prompts/INDEX.md`, anything in another repository or
  the venv.
- **The corrections in §0**, especially 3 (the grid-builder test reads the shard), 6 (the stale
  citations are listed, not edited), 7 (`STOCHASTIC_INSTANTONS_REPO` for any run from a copy) and
  8 (where the refusals go).
- **Stop and ask** on any of the prompt's §4 conditions. Correction 2's hits are not stops. An
  existing test outside §1.6 that fails is current behaviour moving, never a reason to edit it.
- **It replies with:**
  - the results note's path and the commit;
  - `git show --stat` of the commit;
  - DatastoreKit's script's totals before and at the dangling commit;
  - the `ast` comparison's result over every §1.2 file;
  - the four pool constructions' diffs, and `main.py`'s diff outside them;
  - U5's function, its three messages, and its decisions over the subsets it tests;
  - each changed test's diff summary with its reason, and the new tests by name with what each
    asserts;
  - §2.3.2's four checks' outputs, and the schema result;
  - the breakages and what caught each;
  - the three suites by module beside the gate's, with the load;
  - the prose corrected, and the stale list for 12;
  - the closed issue's §4 text and its index row;
  - every deviation with its class;
  - the "State handed to the next prompt" section, verbatim.

## 3. The review — twelve checks

1. **Scope.** `git show --stat <commit>`: the 9 layer files deleted or emptied; the 47 files of
   §1.2; `main.py`, the plot scripts, `config/datastore.py`; `tests/conftest.py`, the four test
   modules of §1.6 and the new module(s); the prose of §1.7; `out/09-temp-schema.json`; the results
   note, the board, `OPEN-ISSUES.md`. Nothing else. `git status --short` clean; one commit of the
   agent's since this note, no amend in the reflog, no leftover branch; no scratch file in the
   repository; no ignored `.pyc` of a deleted module left.
2. **E1, by DatastoreKit's script at the commit**, from its root: the 7 files absent; both
   `__init__.py` 0 bytes; 0 imports, 0 literals, 0 `import_module`. Equal to the results note's
   dangling-commit output. `git grep` (correction 6's dotted pattern) outside `.prompts/` and
   `.documents/`: no hit but the docstrings the note lists.
3. **E2, by `ast`.** For each of the 42 files of §1.2 other than the five that change more
   (`main.py`, the two plot scripts, `conftest.py`, `test_compare_stores.py`), `ast.dump` at
   `<commit>~1` with each rewritten `ImportFrom`'s module mapped by the adoption README's module
   map equals `<commit>`'s: 42 of 42, docstrings included. The 24 `SQLAFactoryBase` and 18
   `DatastoreObject` sites, by count.
4. **E3, the pools and the drivers.** By `ast`, each of the four `ShardedPool(...)` calls: keywords
   `factories=config.datastore.factories` (or an equivalent bare name the module binds to it) and
   `serial_batch_sizes=…serial_batch_sizes`, no `drop_actions`, no `inventory_config`, every other
   keyword and value as at `<commit>~1`; `main.py`'s adds `drop_tables=`. The plot scripts' diffs:
   imports and the pool's arguments only. `main.py`'s: the two imports, the refusals between `:99`
   and `ray.init`, the pool's arguments, the seven helpers and `if args.inventory` gone; every
   other top-level statement dumps as before.
5. **E4, U5 replayed.** The function over all 31 subsets, from the scratchpad, without Ray: its
   accept/refuse decisions equal `orch09/u5_proto.out`'s; the three singleton messages name the
   groups of correction 9. `main.py --database <scratch>/x.sqlite --ray-address 127.0.0.1:9` with
   `--drop full-instanton`, `--drop inflaton-trajectory`, and `--inventory`: each prints the
   provenance line, then its refusal on stderr, exits 2, creates no file, and leaves no Ray
   process. `--drop compaction-function` is not refused before `ray.init` (run it with a timeout
   against the dead address: it must get past the check, and fail at Ray, creating no store).
6. **E5, the changed tests.** By `ast`, docstrings stripped, against `<commit>~1`: `conftest.py`
   differs by the import and the pool's arguments; `test_config_datastore.py` by the two removed
   `import_module` lines, the two deleted tests, the replacing `ast` test and the no-Ray test's
   code string; `test_inflaton_trajectory_prune.py` by `:53` and I6's script (its import and pool
   arguments) alone, every Ray-free test body equal (its store helper unchanged, or rebuilt on
   `build_schema` as the note says); `test_compare_stores.py` by `_registry()`'s body;
   `test_grid_builder_integration.py` by `test_no_duplicate_rows_created`'s count route alone.
   Every other existing test module byte-identical.
7. **E5, the new tests.** Licence header; Ray-free ones leave `ray.is_initialized()` `False`; the
   `ast` pool test names the four files and fails naming the file; the `--inventory` test runs a
   subprocess with a timeout and a dead address, and an `ast` order check; the U3 test is
   `integration`-marked, says why, and reads the `timestamp` column of the row whose `serial` is
   the object's `store_id`, on the shard file, `mode=ro`, for one replicated and one sharded
   object.
8. **E5–E6, the breakages.** Replay the six diffs with `git apply` from the clean tree (`--check`
   and `-R --check` first, in `bash`); each fails what the prompt names (1: collection
   `ModuleNotFoundError`; 2: the U3 test, on the sharded object; 3: I6, naming the package's
   refusal, run alone under `RAY_ADDRESS=local`; 4: U5's test for each unclosed group; 5: the
   integration suite errors at setup and the `ast` test names `tests/conftest.py`; 6: the order
   test). Revert each; `git status` clean after.
9. **E6–E7, without Ray and the schema.** `./venv/bin/python -I` with `PYTHONPATH` the root:
   `import config.datastore` alone, 30 entries, each an instance of the package's
   `SQLAFactoryBase`, no Ray; `sharded_store --help` exits 0; the drivers byte-compile and their
   imports resolve by `ast`. Re-run `orch09/schema_build_pkg.py` at `<commit>`: "the schemas
   agree" against `out/09-temp-schema.json`, `07-reference-schema.json` and the prototype's store.
10. **E7, the suites.** The agent's: default 694 + the new Ray-free tests, all passing (1
    skipped); integration 62 + the new integration tests, all passing (1 skipped); `slow` 69
    passed. The orchestrator re-runs default and integration at `<commit>`, serially.
    `ruff check --select F401,F811,F821` on every Python file the diff touches: no finding the gate
    did not have.
11. **E7, hygiene.** `pip freeze` equals §1's copy; `pip check` clean. DatastoreKit and RayPoolKit
    at §1's `HEAD`s, clean (another session may move them; nothing of theirs may be the agent's).
    The 17 store files and the 835 `~/ScienceData/` entries keep their mtimes. No Ray process; the
    lock free.
12. **E6–E7, the records.** The prose: `CLAUDE.md`'s protected list less the seven and the new
    sentence; `pool-read-apis.md` says `pool.inventory()` does not exist; `datastore-factories.md`'s
    account corrected, the rule kept; the two memory notes; `FILE_MAP.md`'s rows (including
    `:273-275`); `config/datastore.py`'s docstring. The results note follows README §5.1 with the
    prompt's §6 additions, the stale list for 12 including correction 6's citations. The board: §1
    row (✅, "this commit", the results note), A1–A9, the header, `### 5.22` with the rollback
    (`git revert` alone), the issue moved §3 → §4. `OPEN-ISSUES.md`: the row in §7, 60 open, 27
    closed, the date.

## 4. After the review

- **Record it on the board** as an *Orchestrator review of prompt 09* paragraph in §5.22: what each
  check found, and anything handed on to 10 and 11. Fix small residue in a follow-up commit of its
  own:
  - "this commit" → the SHA (board and results note);
  - this note added to the board's list of orchestrator notes, marked "used for 09";
  - `.prompts/INDEX.md`: the campaign's line (09 landed and reviewed; the issue closed; the open
    count 8 → 7).
- Anything the review finds that is not residue is opened on the board's §3 and in the index, in
  the same commit.
- **Report to the user:** the swap in one line (files deleted, imports moved, pools rebuilt); the
  `ast` result; U5's refusals and closed sets; acceptance 4 and 5 under real Ray; the schema; the
  three suites; the closed issue; what goes stale for 12.
- **Then 10** can be dispatched; its note is written after this review, at 09's commit.
