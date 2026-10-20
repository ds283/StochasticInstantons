# Orchestrator — prompt 06, prepare the `InflatonTrajectory` factories for the package

Read [`../README.md`](../README.md) first: §0.1 (item 9), §0.2 ("The old layer ignores `register()`
keys it does not read"), §2.2 (06's charter), §4, §5 (rules 4, 7, 8, 10, 12, 15–17) and §6.2 (P13,
P17). The conventions are [`prompt-01.md`](prompt-01.md)'s §0 "Conventions", unchanged but where
this note says otherwise. ChamPBH has no counterpart: none of its classes is replicated and
validated at startup (README §0.1 item 9), so this note has no model and no ChamPBH findings to
pass on.

**You do not write code.** You may:
- run the suites, `ruff check`, `tools/compare_stores.py` and read-only Python checks, from the
  session scratchpad;
- build temporary stores in the scratchpad under a private Ray (`ray.init(address="local")`), in a
  separate process, to measure the old layer's prune;
- replay the results note's deliberate-breakage diffs with `git apply`, and revert them;
- fix small residue in a follow-up commit of your own (§4).

**The prompt:** [`06-prepare-the-inflaton-trajectory-factories.md`](../06-prepare-the-inflaton-trajectory-factories.md) ·
**Board items:** I1–I6 · **Closes:** `[inflaton-trajectory-prune-orphans-value-rows]` ·
**Narrows:** nothing · **Opens:** only what the work finds · **Model:** Opus, as the prompt
recommends · **No network.**

**Gate:**
- 05 landed (`875cf41`) and was reviewed (`436fc8d`, residue `5dbcd22`);
  `.documents/dk-and-rpk-migration/out/05-temp-schema.json` exists.
- `HEAD` is the commit that adds this note, or a later one that touches no code ("code" as
  prompt-01.md's gate defines it). `git diff --stat 875cf41 HEAD -- . ':!.prompts' ':!.documents'`
  is `tests/test_config_datastore.py` alone, one docstring line (`5dbcd22`).
- No SI cluster is up, and the venv holds `raypoolkit` 0.2.0 at `eaef0ce6…` and no `datastorekit`.
- One prompt at a time in this checkout, and no other session runs a suite or a Ray job from this
  venv while 06 runs.

## 0. What makes this prompt unusual

**It changes the one behaviour of the old layer it can, and three things the old layer never
reads.** The cascade changes which rows a pruning open deletes. The two `register()` keys,
`revalidate` and the parameter's name are inert on the old layer: `_build_schema` reads neither key,
nothing calls `revalidate`, and the actor calls every hook positionally. So the existing suites pass
whether or not those three are right. Three pieces of evidence are not vacuous, and the review leans
on them:
- **the cascade on rows a real build leaves**, in the integration test, on two shards, read back
  with `sqlite3` `mode=ro`, *with the state before the reopen read too* (correction 6), so that a
  store that never happened cannot pass as a prune that took;
- **`revalidate` against `validate` on rows the factory's own `store` wrote**, not rows the test
  inserts by hand, in the test without Ray;
- **the signature test counting 12**, by the class's own `__dict__` (correction 2): every factory
  inherits `base.py`'s `validate_on_startup(self, conn, table, tables, prune=False)`, so a test by
  `hasattr` or by the MRO would find 30 and pass with the rename undone.

**The package is not installed and no test runs it.** What it will ask is read at `v0.4.0`, and the
tests check those properties on SI's own hooks (the prompt's §1, "What the package will ask"). The
orchestrator read the package and found nothing more (below); 09's acceptance runs the real prune.

**The prompt was written on 2026-10-20 at `7ceb089`.** 05 has landed since, and it *did* touch
`Datastore/SQL/Datastore.py` (it lost the registry), so the prompt's line numbers in that file are
stale (correction 3). Nothing else the prompt measures has moved.

**Corrections to the prompt.** Pass them on.
1. **§2.1.1's first grep finds 13 lines, not 12, and it is not a stop.** The thirteenth is
   `Datastore/SQL/ObjectFactories/base.py:29`, `def validate_on_startup(self, conn, table, tables,
   prune=False):`, the base class's own. It is not a hook of a registered factory, it already says
   `prune`, and `base.py` is on `CLAUDE.md`'s protected list: 06 does not touch it. The other 12 are
   exactly I2's, at the lines the prompt gives. The second grep finds **33 lines**, all expected:
   - the 12 hook definitions and the **5** uses in bodies (`CompactionFunction.py:495`,
     `FullInstanton.py:365`, `GradientCoupledInstanton.py:614`, `InflatonTrajectory.py:260`,
     `SlowRollInstanton.py:360`). The other 7 hooks are `return []` and use no name;
   - the 5 rule lines of I2 (`validate-on-startup.md:38`, `:43`, `:83`; `datastore-factories.md:205`,
     `:209`);
   - the 11 that stay: `Datastore/SQL/Datastore.py:68`, `:78`, `:345`; `Datastore/SQL/ShardedPool.py:51`,
     `:66`, `:165`, `:187`; `main.py:1353`; `plot_GradientCoupledSolutions.py:987`;
     `plot_InstantonSolutions.py:1223`; `tests/conftest.py:67`.

   After the change the same grep finds those 11 and nothing else. (`--prune-unvalidated` in
   `config/argument_parser.py` is spelled with hyphens, and the grep does not find it.)
2. **"Every factory whose class defines `validate_on_startup`" means its own class.** Measured from
   `config.datastore.factories` (the layer imported first, correction 4): `"validate_on_startup" in
   type(f).__dict__` holds for **12 of the 30** entries, one per hook of I2 (`InflatonTrajectory`,
   `InflatonTrajectoryValue`, `CosmologicalParams`, `FullInstanton`, `FullInstantonValue`,
   `GradientCoupledInstanton`, `GradientCoupledInstantonValue`, `GradientCoupledInstantonProfile`,
   `SlowRollInstanton`, `SlowRollInstantonValue`, `CompactionFunction`, `CompactionFunctionSamples`).
   The other 18 inherit `base.py`'s, whose parameters already end in `prune`, so a test that walked
   the MRO would pass vacuously. Of the 12, five register `validate_on_startup: True` and so are
   called at open (`InflatonTrajectory`, `FullInstanton`, `GradientCoupledInstanton`,
   `SlowRollInstanton`, `CompactionFunction`); only `InflatonTrajectory` is replicated. The test
   asserts 12 and names the factory on failure (breakage 3).
3. **`Datastore/SQL/Datastore.py`'s lines at `HEAD`** (05 removed 100 lines above them):
   `_build_schema` **`:187`**; `_validate_on_startup` **`:334-359`**, its `engine.begin()` at `:343`
   and the positional call at `:344-346`, run only when the shard file already exists at open
   (`:107-115`); `object_store` **`:462`**, its one `engine.begin()` at `:478`, the factory's `store`
   at `:495-504`, `conn.commit()` at `:509`; `_insert` `:519`; `object_validate` **`:582`**, its
   `engine.begin()` at `:591`. The factory modules, the rules, `tests/conftest.py` (`live_pool`,
   `:36-74`) and the hook lines are where the prompt says. README §0.2's `:297-330` and `:443-446`
   are older still; they are the README's, and 06 does not correct them.
4. **`import config.datastore` must follow the layer** (`[config-datastore-cannot-be-imported-before-the-layer]`,
   05). The new test module imports the layer first, by
   `importlib.import_module("Datastore.SQL.Datastore")`, with a comment saying why, as
   `tests/test_config_datastore.py` does; or it imports a factory module first, which loads the layer
   too. Importing the layer and every factory module starts no Ray (measured:
   `ray.is_initialized()` `False`).
5. **The helper must build the parent tables.** SQLAlchemy resolves every `ForeignKey` at
   `create_all`, whatever SQLite enforces: building only `InflatonTrajectory` and
   `InflatonTrajectoryValue` fails with `NoReferencedTableError` (`'InflatonTrajectory.rtol_serial'
   could not find table 'tolerance'`; measured). Building **all 30** tables of
   `config.datastore.factories`, in its order, as `_build_schema` builds them (`serial`, `version`,
   `timestamp`, `stepping` by the flags, then `columns`), creates cleanly in a `tempfile` SQLite file
   (measured). The orchestrator recommends exactly that: it is `_build_schema`'s rule with nothing
   chosen, and it lets the cascade test check that **no table** but the two lost a row. The rows
   themselves may then name parents that are not there (`phi0_serial = 1` and no `phi_value` row),
   since SQLite does not enforce foreign keys unless asked. So the answer to the prompt's question
   is "both": the tables are built, the parent rows are not. Say so. Each test builds its own store
   (fresh `Column` objects come from each `register()` call).
6. **The integration test cannot share `live_pool`'s Ray; it runs in a subprocess.** This replaces
   the prompt's "it may share the Ray instance `live_pool` starts". Measured with SI's
   `ShardedPool`, under a private Ray:
   - **a second pool cannot open while another is open in the same Ray session.** Its actors have
     fixed names (`SerialPoolBroker`, `ShardedPool.py:96`; `shard{key:04d}-store`, `:158`, `:179`), so
     with a one-shard pool open, as `live_pool` is from its first use to the end of the session,
     another open fails at once: `ActorAlreadyExistsError: The name SerialPoolBroker
     (namespace=None) is already taken`. In the `-m integration` run, every `test_gci_*` module sorts
     before `test_inflaton_trajectory_prune.py`, so `live_pool` is open when the test runs;
   - **SI's `__exit__` frees no name.** It calls each shard's `__exit__` and disposes the engine
     (`:218-230`); the named actors live until the pool object is deleted and collected. So the
     test's own reopen meets its own first pool's names unless that pool is gone. (The package's
     `__exit__` kills its actors, contract §9.3; SI's layer is protected and stays as it is.)

   Neither is a §4 stop: the test can be written without touching `live_pool` or any other test.
   **It runs its pools in a fresh process**, `[sys.executable, "-c", <script>, <tmpdir>]` with `cwd`
   the repository root and the script inserting the root on `sys.path`, under its own
   `ray.init(address="local")`, and asserts on what it reads back. The orchestrator recommends
   **two processes**, one per open (store, then reopen with the prune): each exits with its Ray, so
   nothing depends on collection. One process that deletes the first pool, calls `gc.collect()` and
   waits (bounded) for `ray.util.list_named_actors()` to be empty also worked in the measurement.
   Either is an `IMPLEMENTATION CHOICE`; say which, and why the test is in a subprocess. It never
   calls `ray.init` or `ray.shutdown` in the pytest process, so `live_pool` is untouched.
   - **Read the shard files twice.** After the store process, before the reopen: on each shard both
     trajectories, one validated and one not, each with all its value rows. After the reopen: the
     validated one and all its value rows, the other gone, and no `InflatonTrajectoryValue` row
     naming a missing trajectory. The primary (`<name>.sqlite`) holds no `InflatonTrajectory`
     table; only the shard files are read.
   - **The actors' "Pruned …" lines** reach the subprocess's stdout only if Ray forwards them before
     it shuts down; the test must not depend on them. The database is the evidence.
7. **What the orchestrator's run of that scenario gives at `HEAD`** (no cascade): two shards; two
   trajectories stored through the pool on synthetic values (three `efold_value`s, a real
   `QuadraticPotential` from an `inflaton_mass`, `phi_value`, `pi_value` and two `tolerance`s minted
   through the pool), the first validated (`True`), the second withheld; reopened with
   `prune_unvalidated=True`: each shard's actor printed `Pruned 1 unvalidated InflatonTrajectory
   records`, and **each shard then held trajectory 1 alone and all six value rows, three of them
   orphans** (`trajectory_serial` 2). That is the bug, reproduced, and the integration test with the
   cascade removed must find exactly this (breakage 1). The script is `orch06/probe_pools.py` in the
   session scratchpad; the agent may read it, and owes it nothing.
8. **I4's two facts hold; the orchestrator checked them, and the agent checks them again and writes
   them down.** `object_store` runs every object of a call, and so the factory's `store` with all its
   value inserts, inside one `engine.begin()` (`Datastore.py:478`, `:495-504`, `:509`); a replicated
   store is one such call per shard (`ShardedPool.py`, `_store_impl_replicated_table`). `store`
   writes `N_end` NULL exactly on failure (`InflatonTrajectory.py:206-209`), and otherwise
   `obj._N_end` (`:213`), which `ComputeTargets/InflatonTrajectory.py:353` sets from the remote
   function's `N_end`, always `float(sol.t_events[0][0])` on success (`:123`, returned at `:135`),
   never `None`; a success also has at least two samples (`n_points = max(2, …)`, `:129`), so
   `validate`'s `actual > 0` holds for every real non-failed row. A value insert that failed
   (a duplicate `N_serial` under the composite key) would raise and roll back the whole call, so a
   shard never holds a row with some of its value rows. **Not a stop.**
9. **`revalidate` returns a Python `bool`.** The package keeps a result only if `result is True`
   (`datastorekit/SQL/ShardedPool.py:2111` at `v0.4.0`) and refuses when the shard held `True` and
   `result is not True` (`:2125`). A `numpy.bool_`, an `int` from `count()`, or `None` would be read
   as `False`. It runs inside a savepoint the package opens (`:2109`), so it writes with `conn` and
   commits nothing. The test asserts `is True` / `is False`, not truthiness.
10. **What the package will ask, read at `v0.4.0`** (`c8570e8`), with the lines at the tag (the
    contract's own citations are older):
    - the prune: `_replicated_prune_classes` (`ShardedPool.py:2210`) picks a replicated class whose
      `register()` asks for `validate_on_startup`; `_prune_needed` (`:2275`) calls the hook with
      `prune=False`; `_prune_shard` (`:2300`) calls it with `prune=True` and again with
      `prune=False` (`:2324-2325`), and refuses if the second reports anything, if any compared
      table gained or changed a row, or if one outside the unit lost a row. `_unit_tables` (`:2243`):
      the class, its tag tables, and the compared tables whose `owner_column`'s foreign key names
      it. `InflatonTrajectoryValue` is in SI's `replicated_tables` (`config/sharding.py:42`), so it
      is compared, and without `owner_column` its deletions would be refused;
    - the repair: `_recompute_validated` (`:2084`), the call `factory.revalidate(serial, conn,
      table, tables)` positionally (`:2110`), only for a row the shard holds (`:2104`);
    - the actors call every hook positionally (`datastorekit/SQL/Datastore.py:492`), and never prune
      a replicated class themselves;
    - the schema: `owner_column` must be a column with exactly one foreign key, `validated_column` a
      `Boolean` column (`datastorekit/SQL/schema.py:207-283`); `trajectory_serial` has one, to
      `InflatonTrajectory.serial`, and `validated` is `sqla.Boolean`;
    - SI's checklist (`docs/adoption/stochasticinstantons.md:220-242` at the tag) asks for the same
      four things, and nothing more. `owned_serials` is optional and not needed (the value rows have
      no `serial`), and `monotone_flags` does not apply. **So no §4 stop.**
11. **The messages.** Keep both lines' wording; a second line with the count of value rows deleted is
    allowed. `FullInstanton.py:361-379` is the house pattern for the cascade (`tables.get`, the
    comment, the delete before the parent's); follow it.
12. **The board section** is **`### 5.18 After prompt 06 (<date>)`**, appended after §5.17; the
    board's header ("Last updated", the status line) is updated to match. Closing the issue moves its
    row from board §3 to §4 (with how), and in `.documents/OPEN-ISSUES.md` moves its row from §6a to
    §7 "Closed" (`| Issue | Closed | By |`), the header **62 → 61 open, 25 → 26 closed**, the date.
13. **The suites** run as README §5 rules 16–17 say, serially, in the foreground, with no cluster up:
    - `./venv/bin/python -m pytest -m "not integration and not slow" -q -p no:cacheprovider`;
    - `RAY_ADDRESS=local ./venv/bin/python -m pytest -m integration -q -p no:cacheprovider`.

    "05's counts" are **690 (689 passed, 1 skipped)** and **61 (60 passed, 1 skipped)**. The `slow`
    block is not run: the diff touches none of its paths. Breakage 1's integration half is run
    alone, by node id, under `RAY_ADDRESS=local`.
14. **`.prompts/INDEX.md` is the orchestrator's**, at the review. The agent does not touch it.

**The facts, checked by the orchestrator on 2026-10-20 at `436fc8d`, 20:15–20:40 BST.** Pass them
on.
- **The tree.** Branch `dk-and-rpk-migration`, clean, `HEAD` `436fc8d` before this note; `git diff
  --cached` empty. The 17 store files of prompt-01.md §1 step 5 are in the tree (ignored); none is
  the agent's, and 06 opens none of them.
- **Ray and the lock.** `ray_cluster.sh status`: lock free, no `/tmp/ray-si` process, the four
  ports free. `pgrep -fl 'gcs_server|raylet|ray::|pytest|main.py'` finds nothing. `RAY_ADDRESS` is
  unset. The orchestrator's probes left no Ray process.
- **The load** was 4.5 / 7.1 / 7.5 at 20:22, on 10 CPUs.
- **The venv** is as 05 left it: `pip freeze` has the one `raypoolkit @
  git+https://github.com/ds283/RayPoolKit@eaef0ce6…` line and no `datastorekit`; `pip check` clean.
  06 installs nothing.
- **The hooks, the names and the rules**, as corrections 1–3.
- **The registry**, as correction 2; the table build, as correction 5; the two pools and the
  scenario, as corrections 6–7.
- **`InflatonTrajectory.py`** at `HEAD`: `register` `:28-89` (`validated`, `sqla.Boolean`, `:81-87`),
  `store` `:186-228`, `validate` `:230-254`, `validate_on_startup` `:256-266`, the value factory
  `:384-432` (`trajectory_serial`, one `ForeignKey("InflatonTrajectory.serial")`, `:394-401`), as the
  prompt says.
- **The prose.** Outside `.prompts/` and `.documents/`, only the five rule lines of correction 1 name
  the hook's parameter, and no file names `revalidate`, `owner_column` or `validated_column`.
  `CLAUDE.md`'s critical rule 5 lists three value tables as examples ("The value tables
  (`FullInstantonValue`, `SlowRollInstantonValue`, `CompactionFunctionSamples`)…"); 06 makes it no
  less true, and it stays (12 may widen it). DatastoreKit's checklist quotes the old parameter name;
  it is that repository's and is not edited.
- **DatastoreKit** at `/Users/ds283/Documents/Code/DatastoreKit`: `HEAD` `38ebb9f`, clean; `v0.4.0`
  is `c8570e8`.
- **The stores.** 06 opens only its temporary stores: the tests' (under `tempfile`) and the schema
  build's (under the agent's scratch directory). Not the 17 in the tree, not 02's under
  `~/ScienceData/StochasticInstantons-rehearsals/`, nothing else under `~/ScienceData/`.

**What the review exists to establish.**
- **(E1) I1, the cascade.** The hook deletes the value rows of exactly the unvalidated trajectories,
  before them, in the actor's one transaction; the messages keep their wording; the rule's map has the
  row. On two shards, through SI's own pool, a pruning reopen leaves no orphan, where at `HEAD` it
  left three on each.
- **(E2) I2, the name.** 12 hooks take `prune`; each module's `ast`, with the hook's parameter and
  its uses renamed back, equals the gate's (except `InflatonTrajectory.py`'s I1, I3 and I4); the five
  rule lines change that name only; the 11 other `prune_unvalidated`s are untouched.
- **(E3) I3, the keys.** Each `register()` differs by its one key and comment; the schema does not
  change.
- **(E4) I4, `revalidate`.** It is `validate`'s rule as stored, returns a `bool`, raises for a missing
  serial, and never gives `False` for a row `validate` set `True` on rows `store` wrote; the two facts
  are written down with their lines.
- **(E5) The tests and the breakages.** The tests check the package's properties on SI's hooks, the
  signature test counts 12, the integration test reads both states, and breakages 1–5 are caught.
- **(E6) Nothing else moved.** No file outside the prompt's §5 list; the venv as 05 left it; no store
  opened but the temporary ones; DatastoreKit untouched; the suites at 690 + new and 61 + new.
- **(E7) The records.** The board's §1 row, I1–I6, `### 5.18`, the issue closed on the board and in
  the index; the results note with §2.1.1's lists, I4's check, the schema checks, the package's
  properties against the tests, and the breakages as diffs.

**Conventions particular to 06.** prompt-01.md's conventions hold (the venv: nothing installed or
uninstalled). In addition:
- **git.** The only commit on `dk-and-rpk-migration` is the agent's one, made once (no `--amend`).
  No `checkout`, `switch`, `stash`, `reset --hard` or `rebase`.
- **Ray.** The only Ray the agent causes is the schema build's private instance, the integration
  test's subprocesses' private instances and the integration suite's, under `RAY_ADDRESS=local`. No
  `ray start`, no `ray stop`, no driver run.
- **Formatting.** No existing file is reformatted (README §5 rule 15); `ruff format` is not run on
  any file the prompt does not create. The new test module may be formatted.
- **Scratch.** The schema-build script (05's `schema_build.py`, from 05's results note §2.3.1, with
  its label changed) lives in the agent's scratch directory and is reproduced in the results note.
  Temporary stores are under the scratch directory or `tempfile`, never in the repository.

## 1. Before you dispatch

1. **The tree.** Record the branch and `HEAD`. `git status --short` is clean and `git diff
   --cached` empty. `git log --oneline 436fc8d..HEAD` touches no code.
2. **Ray and the lock.** `ray_cluster.sh status` clean; `pgrep` finds no Ray process.
3. **The venv.** `pip freeze` saved in the scratchpad; `pip check` clean.
4. **The load.** `uptime`, recorded and passed on.
5. **Mtimes**, for check 10: the 17 store files in the tree, and every entry under `~/ScienceData/`,
   by `/usr/bin/stat -f '%m %z %N'`, saved in the scratchpad. DatastoreKit's `git status
   --porcelain` empty; its `HEAD` recorded.
6. **The greps, the registry, the table build, the two pools and the scenario at `HEAD`**, as §0's
   corrections, saved in the scratchpad.

**Done 2026-10-20, 20:15–20:40 BST,** at `436fc8d`: all six hold. The freeze (`pip-freeze.txt`),
the probe (`probe_pools.py`), the mtimes (`mtimes-stores.txt`, 17 files; `mtimes-sciencedata.txt`,
607 entries, 433 of them SI's rehearsal root) and the package's three modules at `v0.4.0`
(`dk_*.py`) are in `orch06/` in the session scratchpad. DatastoreKit `HEAD` `38ebb9f`, clean.

The suites are not re-run by the orchestrator before dispatch: the only Python change since
`875cf41`, whose review re-ran them, is one docstring line (`5dbcd22`), and the agent runs them.

## 2. Dispatch

One fresh-context subagent, on **Opus**. Give it:
- the prompt;
- the campaign README and the board;
- 05's results note (the suites' commands and counts, the schema-build script, and the form of a
  results note);
- `HEAD`, the load and §0 of this note, up to "## 1. Before you dispatch" only, as a copy in the
  session scratchpad. It does not read `orchestrator/`, and does not read prompt 07.

Tell it plainly:
- **One commit, at the end, made once.** Its results note is
  `.documents/dk-and-rpk-migration/06-prepare-the-inflaton-trajectory-factories.md`, in README §5.1's
  form, with the prompt's §6 additions.
- **The files it may change** are the prompt's §5 list. **No other test, no `ComputeTargets/` file,
  no protected file (not `base.py`, not `ShardedPool.py`, not `Datastore.py`), nothing in
  DatastoreKit, RayPoolKit, ChamPBH or SGK, nothing in the venv, not the README, not
  `.prompts/INDEX.md`.**
- **Stop and ask** on any of the prompt's §4 conditions. The thirteenth grep line of correction 1 and
  the subprocess of correction 6 are not stops.
- **It replies with:**
  - the results note's path and the commit;
  - `git diff --cached --name-only` as committed, and `git diff --stat` of the commit;
  - §2.1.1's two lists, before and after;
  - `InflatonTrajectory.py`'s diff in full, and the diff of each other factory module;
  - I4's check, with its lines;
  - the schema checks' commands and results;
  - the new tests by name, what each asserts, and how the integration test handles Ray;
  - the five breakages and what caught each;
  - the two suites, with the load;
  - the closed issue's §4 text and its index row;
  - every deviation with its class;
  - the "State handed to the next prompt" section, verbatim.

## 3. The review — twelve checks

1. **Scope.** `git show --stat <commit>` touches only the six factory modules, the two rule files,
   the new test module(s), `OPEN-ISSUES.md`, the results note and the board. `git status --short` is
   clean; `git log` since this note shows one commit of the agent's, and the reflog no amend; `git
   branch` no leftover branch; no scratch file in the repository.
2. **E2, the name.** For `CompactionFunction.py`, `CosmologicalParams.py`, `FullInstanton.py`,
   `GradientCoupledInstanton.py` and `SlowRollInstanton.py`: with `prune` renamed back to
   `prune_unvalidated` in each `validate_on_startup`'s arguments and body, the module's `ast` dumps
   equal to `<commit>~1`'s (a script from the scratchpad). `git diff <commit>~1 <commit>` of each is
   the definition line and, where there is one, the one body line. `git grep -n prune_unvalidated --
   ':!.prompts' ':!.documents'` gives the 11 lines of correction 1, at their lines. The five rule
   lines change the name only (`git diff --word-diff`).
3. **E1, the cascade, by reading.** `InflatonTrajectory.py`'s `validate_on_startup`: `tables.get(
   "InflatonTrajectoryValue")`, the delete by `trajectory_serial.in_(serials)` before the parent's,
   both on `conn`, the two message lines as before (and the count line, if added). Every other method
   of `sqla_InflatonTrajectory_factory` but `register` and the new `revalidate`, and every method of
   the value factory but `register` and the hook's name, dumps by `ast` as at `<commit>~1`. The rule's
   cascade map has the row, and nothing else in the rule changed but the three names.
4. **E3, the keys.** Each `register()`'s diff is one key and one comment. Called at `<commit>` and
   at `<commit>~1` (a `git archive` copy), each `register()` gives the same columns (`repr` of each
   `Column`, with its foreign keys) and differs only by the key.
5. **E4, `revalidate`.** By reading: the rule of the prompt's I4, `bool` returned, a raise naming the
   serial for a missing row, the docstring (contract §3; the old layer never calls it). Against the
   code, the note's I4 check cites the lines of correction 8 and states both facts. From the
   scratchpad, on a temporary store built as correction 5: rows written by the factory's `store` (a
   complete one, a failed one), `validate` run, the flag cleared, `revalidate` gives `True` and writes
   it; a row whose value rows are deleted by hand gives `False`; an unknown serial raises.
6. **E5, the tests and the breakages.** The new module carries the licence header, imports the layer
   first (with the comment), and the tests without Ray leave `ray.is_initialized()` `False`. The
   signature test asserts 12 by the class's own `__dict__`. The integration test is `integration`-
   marked, says why, runs its pools in a subprocess and asserts the state before and after the
   reopen. Replay breakages 1–5 with `git apply` from the clean tree (`--check` and `-R --check`
   first, in `bash`); each fails what the prompt names (1: the cascade test, and the integration test
   finding orphans, run alone under `RAY_ADDRESS=local`; 2: the failed-row case; 3: the signature
   test, naming `CosmologicalParams`; 4: the keys test; 5: the complete-row case). Revert each; `git
   status` clean after.
7. **E1 and E3, the schema.** Re-run the results note's schema-build script at `<commit>`, in the
   scratchpad: `ray.is_initialized()` `False` before and no Ray process after. `--schema` against
   `05-temp-schema.json` and against `02-reference-schema.json`: "the schemas agree" both times.
8. **E1, the orchestrator's scenario.** Re-run `orch06/probe_pools.py`'s scenario at `<commit>`
   (its third part; in its own process): each shard holds trajectory 1 and its three value rows, and
   **no orphan**, where at `HEAD` before dispatch each held three.
9. **The venv.** `pip freeze` equals §1's copy; `pip check` clean. Nothing installed or removed.
10. **E6, hygiene.** DatastoreKit's `git status --porcelain` empty and its `HEAD` reported (another
    session may move it; nothing of it may be the agent's). The §1 mtimes of the 17 store files and
    of SI's rehearsal root are unchanged (the rest of `~/ScienceData/` is other projects', reported
    but not held against the agent). No Ray process; the lock free.
11. **E6, the suites.** The agent's: 690 + the new tests without Ray (all passing, 1 skipped) and 61
    + the integration test (60 + 1 passed, 1 skipped), with the load. The orchestrator re-runs both
    at `<commit>`. `ruff check --select F401,F811,F821` on the six modules and the new test module
    adds no finding to the gate's.
12. **E7, the records.** The results note follows README §5.1, with §2.1.1's lists, I4's check, the
    schema checks, what the package will ask set against each test, the breakages as diffs and the
    suites beside 05's counts. The board has the §1 row (✅, "this commit", the results note), I1–I6,
    `### 5.18 After prompt 06` with the rollback (`git revert` alone; nothing in the venv), the issue
    moved from §3 to §4 with how. `OPEN-ISSUES.md`: the row moved from §6a to §7, 61 open, 26 closed,
    the date today.

## 4. After the review

- **Record it on the board** as an *Orchestrator review of prompt 06* paragraph in §5.18: what each
  check found, and anything handed on to 07. Fix small residue in a follow-up commit of its own:
  - "this commit" → the SHA (board and results note);
  - this note added to the board's list of orchestrator notes, marked "used for 06";
  - `.prompts/INDEX.md`: the campaign's line (06 landed and reviewed; the open count 9 → 8).
- Anything the review finds that is not residue is opened on the board's §3 and in the index, in
  the same commit.
- **Report to the user:**
  - the change in one line (the cascade; `prune` in 12 hooks; two keys; `revalidate`);
  - the orphan bug, reproduced at the gate and gone at the commit, on two shards;
  - `revalidate` against `validate`, and the package's properties as tested;
  - the subprocess, and why `live_pool`'s Ray could not be shared;
  - the suites.
- **Then 07** can be dispatched; its note is written after this review, at 06's commit. 07 reads
  the prune's messages from the logs, which 06 keeps as they were.
