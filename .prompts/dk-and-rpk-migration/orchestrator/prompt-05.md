# Orchestrator — prompt 05, move SI's data out of the layer

Read [`../README.md`](../README.md) first: §0.1 (items 1–3), §1, §2.2 (05's charter), §4, §5
(rules 4, 7, 8, 10, 12, 15–17) and §6.2 (P8, P12, P13). The conventions are
[`prompt-01.md`](prompt-01.md)'s §0 "Conventions", unchanged but where this note says otherwise.
ChamPBH's 05 note (`ChamPBH/prompts/dk-and-rpk-migration/orchestrator/prompt-05.md`) and its review
(ChamPBH board §5.7) are the model; what they found that applies to SI is in §0.

**You do not write code.** You may:
- run the suites, `ruff check`, `tools/compare_stores.py` and read-only Python checks, from the
  session scratchpad;
- apply the move to a scratch copy of the tree (`git archive HEAD | tar -x`) to measure it, and
  build the empty two-shard store there under a private Ray (`ray.init(address="local")`);
- replay the results note's deliberate-breakage diffs with `git apply`, and revert them;
- fix small residue in a follow-up commit of your own (§4).

**The prompt:** [`05-move-si-data-out-of-the-layer.md`](../05-move-si-data-out-of-the-layer.md) ·
**Board items:** M1–M6 · **Closes:** nothing · **Narrows:** nothing · **Opens:** one issue, for 09
(§0, correction 1), and anything else the work finds · **Model:** Sonnet, as the prompt
recommends · **No network.**

**Gate:**
- 04 landed (`ef13445`) and was reviewed (`3c02d43`); the RayPoolKit G4 row of board §2 is ✅.
- `HEAD` is the commit that adds this note, or a later one that touches no code ("code" as
  prompt-01.md's gate defines it). `git diff --stat ef13445 HEAD -- . ':!.prompts' ':!.documents'`
  is empty at `3c02d43`.
- No SI cluster is up, and the venv holds `raypoolkit` 0.2.0 at `eaef0ce6…` and no `datastorekit`.
- One prompt at a time in this checkout, and no other session runs a suite or a Ray job from this
  venv while 05 runs.

## 0. What makes this prompt unusual

**It moves data behind names that keep working whatever is moved.** The layer keeps `_factories`,
`_drop_actions` and `_default_serial_batch_size` as module-level names, now bound by import. So every
existing test, the integration suite and the schema check pass whether the data moved, was copied,
or was changed on the way. Three pieces of evidence are not vacuous, and the review leans on them:
- **the captured literals** (§2.1.1), taken from the gate's tree *before* any edit, by a script that
  reads the layer, not `config.datastore`. The review compares them with the orchestrator's own
  capture (below), entry by entry;
- **the identity test**, without which a copy left in the layer passes the data test. Breakage 4
  shows it;
- **the `ast` comparison of the moved definitions** (review check 3): the three dict literals in
  `config/datastore.py` dump identically to the ones removed from the layer, and no other top-level
  statement of either layer file changed.

**The schema check is necessary but weak.** The actor builds its tables from the registry, so if
the registry is the same objects the schema cannot move. It would catch an entry dropped, not a
changed batch size or drop group; the data test covers those.

**M3 and M4 are "these lines and no others".** The `ast` test proves every call is wrapped, not that
nothing else in a call changed. The review reads the diff, and normalises each call's shard-key
argument to compare the three files' `ast` with the gate's.

**The prompt was written on 2026-10-20 at `7ceb089`.** 04 has landed since and deleted six lines of
`main.py`; nothing else the prompt measures has moved.

**Corrections to the prompt.** Pass them on.
1. **There is an import cycle, and it is not a stop.** The orchestrator applied M1–M2 to a scratch
   copy (below). `Datastore/SQL/__init__.py` is `from .Datastore import Datastore`, so importing any
   `Datastore.SQL.ObjectFactories.*` module first runs the layer's `Datastore.py`, which imports
   `ClientPool.py`, which (after M2) imports `config.datastore`. So **a fresh `import config.datastore`
   fails**: `ImportError: cannot import name 'serial_batch_sizes' from partially initialized module
   'config.datastore' (most likely due to a circular import)`. Importing `Datastore.SQL.Datastore`,
   `Datastore.SQL.ClientPool`, `Datastore`, `plotting.fetch`, or any factory module first works, and
   then `config.datastore` imports cleanly. The prompt's §2.3.2 check (`import Datastore.SQL.Datastore,
   config.datastore`) passes because of its order, and would not have found it.
   - It is not a §4 stop: no order of the three definitions or the imports avoids it (the module must
     import the factories, whose package imports the layer, which needs `factories`), and breaking it
     means emptying `Datastore/SQL/__init__.py`, which is 09's (P6). ChamPBH met the same cycle at its
     05 and accepted it the same way (its `[05-config-datastore-cannot-be-imported-before-the-layer]`,
     closed by its 08).
   - **Today no entry point meets it.** Every driver, actor and test imports the layer first. One
     test meets it silently: `tests/test_compare_stores.py:938-945`'s `_registry()` tries
     `from config.datastore import factories` first and falls back to
     `from Datastore.SQL.Datastore import _factories` on `ImportError`. Run first in a fresh process,
     the first attempt fails, the fallback loads the layer, and what it returns *is*
     `config.datastore.factories` (identity measured). The fallback would also hide a genuine
     `ImportError` in `config.datastore`. The test is not edited (README §5 rule 7).
   - **So:** `config/datastore.py`'s docstring says the module must, until 09, be imported after the
     layer, and why; `tests/test_config_datastore.py` imports the layer first, with a comment saying
     why; the results note records, in a section of its own, each import order measured in a fresh
     process (`./venv/bin/python -I -c …` from the root, with `sys.path` set to the root), and
     `_registry()`'s path. **One §3 issue is opened**, `[config-datastore-cannot-be-imported-before-the-layer]`,
     owner **09**, with `.documents/OPEN-ISSUES.md` (§6a; header 61 → 62 open, date) in the same
     commit. It gives what, the impact (none today; `_registry()`'s fallback) and the next step (09
     deletes the layer and empties the two `__init__.py` files, P6; its acceptance should include a
     fresh `import config.datastore`).
2. **`Datastore.SQL.Datastore` as an attribute is the actor, not the module.** `import
   Datastore.SQL.Datastore as m` and `Datastore.SQL.Datastore._factories` reach the `ActorClass`
   (`AttributeError: 'ActorClass(Datastore)' object has no attribute '_factories'`; measured).
   The identity test and the capture script find the module with
   `importlib.import_module("Datastore.SQL.Datastore")` (or `sys.modules[…]`). `from
   Datastore.SQL.Datastore import _factories` works, as `_registry()` shows. `ClientPool` is not
   re-exported, so `import Datastore.SQL.ClientPool as c` is the module.
3. **The `main.py` lines at `3c02d43`.** 04's deletions moved all but the first three: the 10 calls
   are **`:226`, `:254`, `:321`, `:449`, `:592`, `:871`, `:900`, `:964`, `:1015`, `:1041`** (the
   prompt's `:450` is −1, `:594` −2, the last five −5); the docstring is **`:420`**. The plot script's
   (`:698`, `:701`, `:734`) and `plotting/fetch.py`'s (`:127`, `:143` docstring, `:166`) are where
   the prompt says, and so are every line it gives in `Datastore.py`, `ClientPool.py`,
   `ShardedPool.py`, the tests and `FILE_MAP.md`. Each call passes its key as the second positional
   argument, on its own line in `main.py` (`key`) and inline in the plot script (`dns_val`) and in
   `fetch.py` (`dns_val`, `shard_key`).
4. **"Each file gains one import."** `main.py:25-32` and `plot_InstantonSolutions.py:32-39` already
   import a parenthesised list from `config.sharding`; the one line each gains is
   `    vectorized_shard_key,` in that list (last, as the list is alphabetical). `plotting/fetch.py`
   imports nothing from `config.sharding`; it gains one `from config.sharding import
   vectorized_shard_key` line. Either form is one added line, which is what acceptance 4 checks.
5. **M4 is one stub and four assertions, not four stubs.** Measured on the scratch copy with M3
   applied and the tests untouched: 5 tests fail, and 5 lines fix them (74 pass in the two files):
   - `tests/test_plot_adapters_golden.py:1012`, `_MultiClassStubPool`'s lookup,
     `self._responses.get((class_name, shard_key["delta_Nstar"]))`; without it three tests fail with
     `TypeError` (the dict in the tuple is unhashable);
   - `:1047`, `called_pairs = {(c, s["delta_Nstar"]) for c, s, _ in pool.calls}`;
   - `:1103`, `assert cf_calls[0][1]["delta_Nstar"] == 5.0`;
   - `tests/test_plot_extraction_golden.py:414`, `assert shard_key["delta_Nstar"] == 5.0` (in the
     test that uses `_StubPool`, `:381`; the stub itself records what it is given and does not
     change);
   - `:467`, `shard_keys_called = {call[1]["delta_Nstar"] for call in pool.calls}` (`_ShardedStubPool`,
     `:450`, likewise unchanged).

   **`_RecordingStubPool` (`:477`) needs no change:** it records only the payloads, and its test
   passes as it is. Each of the five lines changes only where it reads the key; every assertion keeps
   what it asserts. This is inside M4's exception (the three tests that use the four stubs), so not a
   stop; a sixth line would be. The results note lists the five with their lines, and says that
   `:381`, `:450` and `:477` are unchanged.
6. **§2.1.3, the finding for 09, measured.** The registry has 30 entries and the sizes 29;
   registered with no size, `version` and `InflatonTrajectoryValue`; a size with no table,
   `temperature`. **Neither unsized table leases a serial:** `InflatonTrajectoryValue` registers
   `"serial": False` (`InflatonTrajectory.py:390`), and `version` has a `serial` column but the actor
   never leases one for it (`Datastore.py:642`, `… and (cls_name != "version")`). So no table leases
   under SI's fallback of 5, and the README's "none but `version`" is better than expected: not even
   `version`. **One more fact for 09:** three tables carry a size of 500 but register `"serial": False`,
   so their sizes are never read: `FullInstantonValue` (`FullInstanton.py:548`),
   `SlowRollInstantonValue` (`SlowRollInstanton.py:543`) and `GradientCoupledInstantonValue`
   (`GradientCoupledInstanton.py:703`). They move verbatim (P12). Record all of it under "State
   handed to the next prompt"; add nothing.
7. **The lint baseline is one finding, and it stays.** `./venv/bin/ruff` is in the venv (0.15.17).
   At the gate, `ruff check --select F401,F811,F821` on the two layer files gives exactly **one**:
   `F401` `CosmologyModels.cosmo_params.CosmologicalParams` imported but unused, `Datastore.py:35`.
   It is not a factory import and the registry does not use it, so it neither moves nor goes:
   deleting it is a change §1 does not name (README §5 rule 4). After the move the same one finding
   remains, at its new line, and `config/datastore.py` adds none. Record it as an observation.
8. **What moves from `Datastore.py:28-86`, and what stays.** Every import there moves except
   `SQLAFactoryBase` (`:67`, used by `_FactoryMappingType`, `:129`) and the unused
   `CosmologicalParams` (`:35`, correction 7). The moved ones include the four non-factory names the
   registry needs: `phi_value`, `pi_value` (`:28`), `inflaton_mass` (`:85`), `quartic_coupling`
   (`:86`). `:27` (`ClientPool`), `:87` (`ProfileAgent`) and `:88` (`utilities`) are outside the range
   and stay. The orchestrator's scratch move, done this way, leaves the layer with `ClientPool`,
   `config.datastore`, `CosmologicalParams`, `base`, `ProfileAgent` and `utilities`, and passes the
   lint as correction 7 says.
9. **Where the new imports go.** "In place of the definitions" admits two readings. The
   orchestrator's scratch move put `Datastore.py`'s import in the import block, after `:27`, and
   `ClientPool.py`'s where the dict was (`:24`, below the `ProfileAgent` import, so also in the
   import block). Both work under every import order of correction 1. Either placement is an
   `IMPLEMENTATION CHOICE`; the diff of each file must still be only the removed lines and the one
   added import.
10. **Verbatim.** The three literals move byte for byte, renamed only in their binding
    (`factories =`, `drop_groups =`, `serial_batch_sizes =`). `_drop_actions` is hand-aligned
    (`"inflaton-trajectory":   [`); `ruff format` would realign it. The prompt allows formatting the
    new file, but **the orchestrator recommends not formatting it**, so that `git diff --color-moved`
    shows the blocks as moved. If it is formatted, say so; the review compares by `ast` either way.
11. **The `ray.is_initialized()` assertion.** The prompt has `test_config_datastore.py` assert it
    `False` "at the end". In-process, that depends on test order: any earlier test that calls
    `ray.put` (the stub pools do) initialises Ray. None of the five files sorting before
    `test_config_datastore.py` does today, but the orchestrator recommends the robust form: a
    subprocess, `[sys.executable, "-c", …]` with `cwd` the repository root, that imports the layer by
    `importlib` and then `config.datastore`, and asserts `ray.is_initialized()` is `False`. This is
    also the measured import order of correction 1. Either form is an `IMPLEMENTATION CHOICE`.
12. **The `ast` test's tree.** "Every `.py` file outside `tests/`, `venv/`, `.prompts/` and
    `.documents/`": also skip `.git/` and the other dot-directories. The ignored `out-*/` trees hold
    five scripts (`out-gradient-coupled-stiffness/scripts/*.py`), none of which calls
    `object_get_vectorized`, so a walk of the filesystem and a walk of `git ls-files` both find 15. The
    test must not depend on `git` being present; a filesystem walk is the simpler choice. Say which.
13. **The board section** is **`### 5.17 After prompt 05 (<date>)`**, appended after §5.16; the
    board's header ("Last updated", the status line) is updated to match.
14. **The suites** run as README §5 rules 16–17 say, serially, in the foreground, with no cluster up:
    - `./venv/bin/python -m pytest -m "not integration and not slow" -q -p no:cacheprovider`;
    - `RAY_ADDRESS=local ./venv/bin/python -m pytest -m integration -q -p no:cacheprovider`.

    "04's counts" are **680 (679 passed, 1 skipped)** and **61 (60 passed, 1 skipped)**. The `slow`
    block is not run: the diff touches none of its paths.
15. **`.prompts/INDEX.md` is the orchestrator's**, at the review. The agent does not touch it.

**From ChamPBH's 05, for SI** (ChamPBH board §5.7; its review passed all twelve checks):
- the test module imported the layer first, with a comment, and found the module by `importlib`;
- the capture script read the layer, not `config.datastore`, and its output was kept in the log;
- breakage 4 failed only the identity test, the data tests passing;
- the agent amended its own commit once, which the review then had to check in the reflog. Don't:
  one commit, made once.

**The facts, checked by the orchestrator on 2026-10-20 at `3c02d43`, 19:20–19:50 BST.** Pass them
on. The orchestrator applied M1–M3 and the five test lines to a scratch copy (`git archive HEAD`);
nothing in the repository was touched.
- **The tree.** Branch `dk-and-rpk-migration`, clean, `HEAD` `3c02d43` before this note; `git diff
  --cached` empty. The 17 store files of prompt-01.md §1 step 5 are in the tree (ignored); none is
  the agent's, and 05 opens none of them.
- **Ray and the lock.** `ray_cluster.sh status`: lock free, no `/tmp/ray-si` process, the four
  ports free. `pgrep -fl 'gcs_server|raylet|ray::|pytest|main.py'` finds nothing. `RAY_ADDRESS` is
  unset.
- **The load** was 3.5 / 5.3 / 7.9 at 19:22, on 10 CPUs.
- **The venv** is as 04 left it: `pip freeze` is `measure/out/7bb3efd-pip-freeze.txt` plus the one
  `raypoolkit @ git+https://github.com/ds283/RayPoolKit@eaef0ce6…` line, no `datastorekit`; `pip
  check` clean. 05 installs nothing.
- **The 15 calls** (`git grep -n object_get_vectorized -- '*.py'`): the definition
  (`ShardedPool.py:584`), the 15 calls of correction 3, the two docstrings (`main.py:420`,
  `fetch.py:143`) and the four stubs; nothing else. No call in `tools/`, `config/`, the gradient plot
  script or any ignored script.
- **The capture, at `3c02d43`** (the orchestrator's, which the agent's must equal), by
  `importlib.import_module` of the two layer modules; `ray.is_initialized()` `False` after:
  - **the registry, 30 entries in `Datastore.py:97-126`'s order**, each `type(factory).__name__` the
    constructor named there. Four hold a quantity class as `ObjectType`: `inflaton_mass`
    (`sqla_dimensionful_quantity_factory`, `inflaton_mass`), `quartic_coupling`
    (`sqla_dimensionless_quantity_factory`, `quartic_coupling`), `phi_value` and `pi_value`
    (`sqla_dimensionful_quantity_factory`, `phi_value` / `pi_value`). (The prompt says "the two
    quantity factories"; they are two classes, four entries.)
  - **`drop_groups`, 5**, in order: `inflaton-trajectory` (`InflatonTrajectoryValue`,
    `InflatonTrajectory`), `full-instanton` (`FullInstantonValue`, `FullInstanton`),
    `slow-roll-instanton` (`SlowRollInstantonValue`, `SlowRollInstanton`), `compaction-function`
    (`CompactionFunctionSamples`, `CompactionFunction`), `gradient-coupled-instanton`
    (`GradientCoupledInstantonValue`, `GradientCoupledInstantonProfile`, `GradientCoupledInstanton`).
    `_drop_order`: `compaction-function`, `slow-roll-instanton`, `full-instanton`,
    `gradient-coupled-instanton`, `inflaton-trajectory`;
  - **`serial_batch_sizes`, 29**, in `ClientPool.py:25-53`'s order, `"store_tag": 5` first and
    `"IntegrationSolver": 6` last.

  The orchestrator's capture script and output are `orch05/capture.py` in the session scratchpad.
- **The import orders**, each in a fresh `python -I` process on the scratch copy: `import
  config.datastore` fails (correction 1); `import Datastore.SQL.ClientPool`, `import
  Datastore.SQL.Datastore, config.datastore`, `import Datastore` and `import plotting.fetch` each
  succeed. `_registry()`'s logic, run first: the `ImportError`, then the fallback, 30 entries,
  `is config.datastore.factories` `True`, and the layer's `_factories` (by `importlib`) the same
  object.
- **The schema, on the scratch copy:** SI's own `ShardedPool`, `ray.init(address="local")`, two
  shards, `prune_unvalidated=False`, `drop_actions=[]`, `config.sharding`'s `read_table_config` and
  `inventory_config`, no profile agent, opened and closed in a scratch temporary directory: three files
  (`temp.sqlite`, `temp-shard0000.sqlite`, `temp-shard0001.sqlite`). `compare_stores.py --schema
  <tmp>/temp.sqlite --against .documents/dk-and-rpk-migration/out/02-reference-schema.json`:
  **`RESULT: the schemas agree`, exit 0**. Its `--snapshot`'s `tables` equal the reference's (30
  tables; RH0's store had the default 20 shards, and the primary's schema does not depend on the
  count). No Ray process was left after `ray.shutdown()`. **`--schema` takes the primary `.sqlite`,
  `--against` the JSON.** The snapshot is `orch05/orch-sim-schema.json` in the scratchpad.
- **The lint, on the scratch copy:** the one baseline `F401` of correction 7, nothing else, over
  the two layer files and `config/datastore.py`.
- **The tests, on the scratch copy:** with M3 applied, the two plot-test files give 5 failed, 69
  passed; with correction 5's five lines, 74 passed. (The orchestrator's full default run on the
  copy is not evidence: something in the suite puts this repository on `sys.path` ahead of the copy,
  so `plotting.fetch` was imported from here. The agent's run, in the repository, is the evidence.)
- **The prose (M6).** `FILE_MAP.md:17` and `:41` are as the prompt says; the `config/` rows are
  `:17-22`, and `:23` (`quadratic-minimal.yaml`) closes the table. **Left as they are**, since 05 makes
  none of them false:
  - `INFRASTRUCTURE.md:181` and `architecture-summary.md:193` say the actor "owns a registry of all
    factories": it still does, filled by `register_factories` from the module;
  - the sketches at `INFRASTRUCTURE.md:467` and `architecture-summary.md:461`, `:537` pass a bare
    `delta_Nstar_obj` to `object_get_vectorized`. SI's layer still accepts it; the package will not,
    so they become false at 09. Record them for 09/12 under "State handed to the next prompt"; open
    nothing for them.
  - `FILE_MAP.md:272` (`ClientPool.py`, "protected infrastructure; internal to `ShardedPool`") stays
    true.
  - `CLAUDE.md` and `.claude/rules/` name none of the three objects (`git grep` finds only the two
    layer files, `tests/test_compare_stores.py:944` and dated records).
- **The licence header** is the Apache one of `config/defaults.py:1-14` (also `grid_builder.py`,
  `pipeline_setup.py`, and `Datastore.py:1-14`). `config/sharding.py` has none; 05 adds none to it.
- **DatastoreKit** at `/Users/ds283/Documents/Code/DatastoreKit`: `HEAD` `38ebb9f`, clean; `v0.4.0`
  is `c8570e8`. The checklist's §3 and §4 and `docs/client-contract.md` §1's rows 12, 15 and 16
  (`drop_tables`, `factories`, `serial_batch_sizes`) are read at the tag; row 16 gives the package's
  fallback of 500 (`SQL/ClientPool.py:130`).
- **The stores.** 05 opens one store: its temporary one, under `tempfile`, outside the repository,
  deleted afterwards. Not the 17 in the tree, not 02's under
  `~/ScienceData/StochasticInstantons-rehearsals/`, nothing else under `~/ScienceData/`.

**What the review exists to establish.**
- **(E1) M1, verbatim.** `config/datastore.py` holds the three literals, `ast`-equal to those
  removed from the layer, with the imports they need and nothing unused.
- **(E2) M2, the layer.** Each layer file's diff is the removed definitions and imports and one
  added import; every other top-level statement dumps by `ast` as at the gate; the lint is the one
  baseline finding.
- **(E3) The data, captured.** The test's literals equal the orchestrator's capture; the identity
  holds; the data and identity tests catch breakages 2–4.
- **(E4) M3–M4.** 15 calls, each through `vectorized_shard_key`, the three files' `ast` equal to the
  gate's with the shard-key argument normalised, and one import line each; the five test lines and
  nothing else under `tests/` but the two new files.
- **(E5) The schema** agrees with RH0's `reference`, and the snapshot is saved.
- **(E6) Nothing else moved.** No file outside the prompt's §5 list (and `OPEN-ISSUES.md` for the
  issue); the venv's freeze as 04 left it; no store opened but the temporary one; DatastoreKit
  untouched; the suites at 680 + new and 61.
- **(E7) The records.** The board's §1 row, M1–M6, `### 5.17`, the §3 issue with its index row;
  the results note with the capture, the import orders, §2.1.3's finding for 09.

**Conventions particular to 05.** prompt-01.md's conventions hold (the venv: nothing installed or
uninstalled). In addition:
- **git.** The only commit on `dk-and-rpk-migration` is the agent's one, made once (no `--amend`).
  No `checkout`, `switch`, `stash`, `reset --hard` or `rebase`. 05 needs no throwaway commit: no
  script it runs reads git.
- **Ray.** The only Ray the agent causes is the schema build's private instance
  (`ray.init(address="local")`, shut down by the script) and the integration suite's, under
  `RAY_ADDRESS=local`. No `ray start`, no `ray stop`, no driver run.
- **Formatting.** No existing file is reformatted (README §5 rule 15); `ruff format` is not run on
  any file the prompt does not create (correction 10 for the one it does).
- **Scratch.** The capture, schema-build and import-order scripts live in the agent's scratch
  directory and are reproduced in the results note. The temporary store's directory is under the
  scratch directory or `tempfile`, never in the repository.

## 1. Before you dispatch

1. **The tree.** Record the branch and `HEAD`. `git status --short` is clean and `git diff
   --cached` empty. `git log --oneline 3c02d43..HEAD` touches no code.
2. **Ray and the lock.** `ray_cluster.sh status` clean; `pgrep` finds no Ray process.
3. **The venv.** `pip freeze` saved in the scratchpad; it equals the committed
   `measure/out/7bb3efd-pip-freeze.txt` plus the one `raypoolkit` line. `pip check` clean.
4. **The load.** `uptime`, recorded and passed on.
5. **Mtimes**, for check 10: the 17 store files in the tree, and every entry under `~/ScienceData/`,
   by `/usr/bin/stat -f '%m %z %N'`, saved in the scratchpad. DatastoreKit's `git status
   --porcelain` empty; its `HEAD` recorded.
6. **The capture, the scratch move, the import orders, the schema and the lint**, as §0's facts,
   saved in the scratchpad for comparison with the agent's.

**Done 2026-10-20, 19:20–19:50 BST,** at `3c02d43`: all six hold. The freeze, the capture
(`capture.py`), the scratch copy with the move applied (`sim/`), its schema snapshot
(`orch-sim-schema.json`), the schema-build script (`build_temp_store.py`) and the mtimes (17 store
files; 607 entries under `~/ScienceData/`, 433 of them SI's rehearsal root) are in `orch05/` in the
session scratchpad. DatastoreKit `HEAD` `38ebb9f`, clean.

The suites are not re-run by the orchestrator before dispatch: no Python has changed since
`ef13445`, whose review re-ran them, and the agent runs them.

## 2. Dispatch

One fresh-context subagent, on **Sonnet**. Give it:
- the prompt;
- the campaign README and the board;
- 04's results note (the suites' commands and counts, and the form of a results note);
- `HEAD`, the load and §0 of this note, up to "## 1. Before you dispatch" only, as a copy in the
  session scratchpad. It does not read `orchestrator/`, and does not read prompts 06–07.

Tell it plainly:
- **One commit, at the end, made once.** Its results note is
  `.documents/dk-and-rpk-migration/05-move-si-data-out-of-the-layer.md`, in README §5.1's form, with
  the prompt's §6 additions and the import-order section of correction 1.
- **The files it may change** are the prompt's §5 list and `.documents/OPEN-ISSUES.md` for the
  issue of correction 1. **No other test, no `ComputeTargets/` file, nothing in DatastoreKit,
  RayPoolKit, ChamPBH or SGK, nothing in the venv, not the README, not `.prompts/INDEX.md`.**
- **Stop and ask** on any of the prompt's §4 conditions. The import cycle of correction 1, the five
  test lines of correction 5 and the lint finding of correction 7 are not stops.
- **It replies with:**
  - the results note's path and the commit;
  - `git diff --cached --name-only` as committed, and `git diff --stat` of the commit;
  - the capture's output, and how the test's literals were written from it;
  - the layer's diff (both files), the lint before and after, and the import orders measured;
  - the 15 calls, with the lines at the gate and after, and the five test lines;
  - the schema check's command and result;
  - the five breakages and what caught each;
  - the two suites, with the load, and the new tests by module;
  - the §3 issue's text and its index row;
  - every deviation with its class;
  - the "State handed to the next prompt" section, verbatim.

## 3. The review — twelve checks

1. **Scope.** `git show --stat <commit>` touches only `config/datastore.py`, the two new tests,
   `out/05-temp-schema.json`, `Datastore/SQL/Datastore.py`, `Datastore/SQL/ClientPool.py`,
   `config/sharding.py`, `main.py`, `plot_InstantonSolutions.py`, `plotting/fetch.py`, the two
   plot-test files, `FILE_MAP.md`, `OPEN-ISSUES.md`, the results note and the board. `git status
   --short` is clean; `git log` since this note shows one commit of the agent's, and the reflog no
   amend; `git branch` no leftover branch; no scratch file in the repository.
2. **E2, the layer.** `git diff <commit>~1 <commit> -- Datastore/SQL/Datastore.py
   Datastore/SQL/ClientPool.py`: the removed imports of correction 8, `_factories`, `_drop_actions`,
   `_default_serial_batch_size`, and one added import each. By an `ast` check from the scratchpad,
   every other top-level statement of each file dumps as at `<commit>~1`. `_drop_order`, `:192`'s
   `register_factories(_factories)`, the method `_drop_actions` and `ClientPool`'s
   `.get(table, 5)` are byte-identical. `ruff check --select F401,F811,F821` on the two files and
   `config/datastore.py`: the one baseline finding.
3. **E1, verbatim.** The three dict literals in `config/datastore.py` dump by `ast` identically to
   those removed at `<commit>~1`. The module imports nothing it does not use and nothing the
   registry does not need; it has the licence header and a docstring naming each object, the old
   layer's aliases until 09, and the import-order hazard.
4. **E4, the call sites.** For `main.py`, `plot_InstantonSolutions.py` and `plotting/fetch.py`, with
   each `object_get_vectorized` call's shard-key argument unwrapped and the one import removed, the
   `ast` equals `<commit>~1`'s. `config/sharding.py`'s diff is the function and its comment alone.
   `git grep -n object_get_vectorized -- '*.py'` lists the same entries as §0, at the new lines.
5. **E3, the captured data.** The test's three literals equal the orchestrator's capture (§0),
   entry by entry and in order, including the four quantity classes. The results note's capture
   script reads the layer by `importlib`, not `config.datastore`, and its output in the note equals
   the orchestrator's.
6. **E3–E4, the tests and the breakages.** The two new test modules carry the licence header,
   import the layer first (with the comment), and find the module by `importlib`. The `ast` test
   asserts 15 and names file and line on failure. Replay breakages 1–5 with `git apply` from the
   clean tree (`--check` and `-R --check` first, in `bash`); each fails what the prompt names:
   - 1: the `ast` test, naming `plotting/fetch.py` and the line (and, by correction 5, the plot
     tests that reach `fetch_over_grid`: `_ShardedStubPool`'s and `_MultiClassStubPool`'s, by
     `TypeError` on the bare key);
   - 2: the batch-size data test, naming `FullInstantonValue`;
   - 3: the registry data test, naming `inflaton_mass`;
   - 4: only the identity test, the data tests passing;
   - 5: `_MultiClassStubPool`'s three tests, `TypeError: unhashable type: 'dict'`.

   Revert each; `git status` clean after.
7. **E5, the schema.** Re-run the results note's schema-build script at `<commit>`, in the
   repository (a `tempfile` directory outside it): `ray.is_initialized()` `False` before and no Ray
   process after. `--schema` against `02-reference-schema.json` and against `orch05/orch-sim-schema.json`:
   "the schemas agree" both times. `out/05-temp-schema.json`'s `tables` equal the reference's.
8. **The import cycle and the issue.** In fresh `python -I` processes from the root: `import
   config.datastore` fails with the partially-initialised `ImportError`; `import
   Datastore.SQL.Datastore, config.datastore` works; `tests/test_compare_stores.py` run alone
   passes (24). The §3 entry gives what, impact (naming `_registry()`'s fallback, and that it would
   hide a real `ImportError`) and next step (09, P6, with a fresh `import config.datastore` in its
   acceptance). The index row is under §6a, the header 62 open, the date today.
9. **The venv.** `pip freeze` equals §1's copy; `pip check` clean. Nothing installed or removed.
10. **E6, hygiene.** DatastoreKit's `git status --porcelain` empty and its `HEAD` reported (another
    session may move it; nothing of it may be the agent's). The §1 mtimes of the 17 store files and
    of SI's rehearsal root are unchanged (the rest of `~/ScienceData/` is other projects', reported
    but not held against the agent). No Ray process; the lock free.
11. **E6, the suites.** The agent's: 680 + the new tests (all passing, 1 skipped) and 61 (60 passed,
    1 skipped), with the load. The orchestrator re-runs both at `<commit>`. `py_compile` of `main.py`,
    `plot_InstantonSolutions.py`, `plot_GradientCoupledSolutions.py` and `plotting/fetch.py`
    succeeds.
12. **E7, the records.** The results note follows README §5.1, with every §2 check's command and
    output, the capture, the import orders and the breakages as diffs. The board has the §1 row (✅,
    "this commit", the results note), M1–M6, `### 5.17 After prompt 05` with the rollback (`git
    revert` alone; nothing in the venv), the §3 issue and its index row. §2.1.3's finding (correction
    6) and the three bare-key sketches (§0, "The prose") are under "State handed to the next prompt".
    `FILE_MAP.md`'s diff is `:41` and one new `config/` row, and `:17` naming `vectorized_shard_key`.

## 4. After the review

- **Record it on the board** as an *Orchestrator review of prompt 05* paragraph in §5.17: what each
  check found, and anything handed on to 06. Fix small residue in a follow-up commit of its own:
  - "this commit" → the SHA (board and results note);
  - this note added to the board's list of orchestrator notes, marked "used for 05";
  - `.prompts/INDEX.md`: the campaign's line (05 landed and reviewed; the open count 8 → 9).
- Anything the review finds that is not residue is opened on the board's §3 and in the index, in
  the same commit.
- **Report to the user:**
  - the move in one line (three objects, verbatim, the layer reading them by alias; 15 calls
    wrapped; five test lines);
  - the schema, and the data test against the capture;
  - the import cycle, and the issue opened for 09;
  - the finding for 09 (no unsized table leases; three dead sizes);
  - the suites.
- **Then 06** can be dispatched; its note is written after this review, at 05's commit.
