# Prompt 06 — prepare the `InflatonTrajectory` factories for the package

**Campaign:** [`README.md`](README.md) · **Board items:** **I1**–**I6** ·
**Board:** [`IMPLEMENTATION_STATE.md`](IMPLEMENTATION_STATE.md)
**Written:** 2026-10-20, with prompts 05 and 07, after 02's review (board §5.13).
**Gate:**
- 05 landed and reviewed (board §1); `config/datastore.py` holds the registry, and
  `.documents/dk-and-rpk-migration/out/05-temp-schema.json` exists;
- on branch `dk-and-rpk-migration`, no tracked change in `git status`;
- no SI cluster is up (`.documents/dk-and-rpk-migration/rehearsal/ray_cluster.sh status`); the
  venv holds `raypoolkit` 0.2.0 and no `datastorekit`.

**Closes:** `[inflaton-trajectory-prune-orphans-value-rows]`. **Opens:** only what the work finds.
**Recommended model:** **Opus**. The change is small, but `revalidate` must agree with `validate`
and `store` as they are, and the tests must show it on rows a real build would leave.

**No protected file is touched.** The 12 hooks are all in `Datastore/SQL/ObjectFactories/`, in
factories that are not on `CLAUDE.md`'s protected list. `Datastore/SQL/Datastore.py`, which calls
the hooks, does not change.

**Read first:**

1. [`README.md`](README.md): §0.1 item 9 (U4, in full), §0.2 ("The old layer ignores `register()`
   keys it does not read"), §2.2 (06's charter), §4 (what 06 ships), §5, §6.1 (U4) and §6.2 (P13,
   P17).
2. DatastoreKit at the tag, read with `git -C /Users/ds283/Documents/Code/DatastoreKit show
   v0.4.0:<path>`. **Read; edit nothing in that repository** (README §5 rule 12).
   - `docs/client-contract.md` §2 (`owner_column`, `validated_column`, `validate_on_startup`) and
     §3 (`validate_on_startup(conn, table, tables, prune=False)`, `revalidate(serial, conn, table,
     tables)`);
   - `datastorekit/SQL/ShardedPool.py`: the replicated prune (`_prune_needed`, `_prune_shard`,
     `_unit_tables`) and the repair of an interrupted validate (the call of `revalidate`). They are
     what 09 will run these hooks under. What they require of a hook is §1's "What the package
     will ask";
   - `datastorekit/SQL/schema.py`, where `owner_column` and `validated_column` are checked at
     schema build;
   - SI's checklist, `docs/adoption/stochasticinstantons.md`, the items on `InflatonTrajectory`.
3. `Datastore/SQL/ObjectFactories/InflatonTrajectory.py`, in full: `register` (`:28-89`), `store`
   (`:186-228`), `validate` (`:230-254`), `validate_on_startup` (`:256-266`), and the value
   factory (`:384-432`).
4. `Datastore/SQL/Datastore.py`: `_build_schema` (`:287-…`), which reads `register()`; the store
   and validate paths, `object_store` (`:562`) and `object_validate` (`:682`), and the transaction each opens
   (`with self._engine.begin()`); and `_validate_on_startup` (`:434-460`), which calls each hook
   positionally.
5. `.claude/rules/validate-on-startup.md` and `.claude/rules/datastore-factories.md` (its
   `validate_on_startup` pattern, `:199-216`).
6. `tests/conftest.py`'s `live_pool` (`:36-74`): session-scoped, one shard,
   `prune_unvalidated=False`.
7. Prompt 02's results note, "L2 — the resume": what a real prune at open printed, and the cascade
   that `FullInstanton`'s hook already makes.

Line numbers are at `7ceb089`; 05 does not touch these files.

---

## 0. What this prompt is

`InflatonTrajectory` is SI's one replicated class that validates and prunes at startup. Under
DatastoreKit the pool prunes such a class itself, across its shards, and polices what the prune
may delete. Four things follow (U4, README §0.1 item 9), and all four land here, on SI's own layer,
before the swap:
- the prune leaves `InflatonTrajectoryValue` rows behind today, which is a bug of SI's
  (`[inflaton-trajectory-prune-orphans-value-rows]`);
- the package will refuse that cascade unless the value table declares its owner;
- the package repairs an interrupted replicated validate only for a class that declares its flag
  and can recompute it;
- the package calls the hook by keyword, `prune=`.

On the old layer the two new `register()` keys and `revalidate` are read by nothing, and the hooks
are called positionally, so the only behaviour that changes is the cascade.

---

## 1. What is wanted

- **I1 — the cascade.** `sqla_InflatonTrajectory_factory.validate_on_startup` deletes the
  unvalidated trajectories' `InflatonTrajectoryValue` rows, by `trajectory_serial`, **before** it
  deletes the trajectories, in the same transaction, as `.claude/rules/validate-on-startup.md`
  requires:
  - `tables.get("InflatonTrajectoryValue")`, so that a schema without the table still opens (the
    rule's pattern);
  - its messages keep their wording (`Pruned N unvalidated InflatonTrajectory records`, `Found N …
    (not pruned)`), since 07 reads them from the logs. A count of value rows deleted may be added
    as a second line; say whether you added it.
  - `.claude/rules/validate-on-startup.md`'s cascade map gains its row:
    `sqla_InflatonTrajectory_factory` | `InflatonTrajectory` | `InflatonTrajectoryValue` |
    `trajectory_serial`. One sentence under the map may say that this parent is replicated, so its
    value table also declares `owner_column` (I3).
- **I2 — `prune`** (P17). The hook's fourth parameter is renamed from `prune_unvalidated` to
  `prune` in **all 12 hooks** that take it, and each body changes only that name:
  - `CompactionFunction.py:491`, `:601`;
  - `CosmologicalParams.py:82`;
  - `FullInstanton.py:361`, `:589`;
  - `GradientCoupledInstanton.py:610`, `:744`, `:792`;
  - `InflatonTrajectory.py:256`, `:431`;
  - `SlowRollInstanton.py:356`, `:584`.

  Re-measure first (§2.1.1). **Only the hook's parameter is renamed.** `prune_unvalidated` as an
  argument of `ShardedPool` and of the `Datastore` actor, as `self._prune_unvalidated`, as the
  `--prune-unvalidated` flag and in `main.py`, the plot scripts and `tests/conftest.py` is a
  different name, and stays: the package's `ShardedPool` takes `prune_unvalidated=` too.
  - The rules' examples follow, since this commit makes them false (P13):
    `.claude/rules/validate-on-startup.md:38`, `:43` and `:83`, and
    `.claude/rules/datastore-factories.md:205`, `:209`. The name changes and nothing else.
- **I3 — `register()` gains two keys**, and nothing else in either `register` changes:
  - `sqla_InflatonTrajectoryValue_factory.register()`: `"owner_column": "trajectory_serial"`. That
    column carries exactly one foreign key, to `InflatonTrajectory.serial` (`:394-401`), which is
    what the package's schema check requires;
  - `sqla_InflatonTrajectory_factory.register()`: `"validated_column": "validated"`, the
    `sqla.Boolean` column at `:81-87`.

  Each with a one-line comment saying the old layer ignores it and DatastoreKit reads it (U4).
- **I4 — `revalidate(self, serial, conn, table, tables)`** on `sqla_InflatonTrajectory_factory`.
  It recomputes the stored row's `validated` flag by `validate`'s rule, writes it, and returns it.
  The rule, as stored:
  - a row whose `N_end` is NULL is a failure, and is validated (`validate`, `:234-235`; `store`
    writes `N_end` NULL exactly on failure, `:206-209`);
  - otherwise the row is validated when it has **at least one** `InflatonTrajectoryValue` row.

  `validate` asks for `actual == expected and actual > 0`, and `expected` (`len(obj._values)`) is
  not stored. The rule above stands for it because `store` writes the row and all its value rows
  in one transaction, so on any shard that holds the row, "at least one" and "all" coincide.
  **Check this against the code and say so in the results note:** that `object_store` runs the
  factory's `store` inside one `engine.begin()`, that `store` inserts every value row there, and
  that a non-failed `store` never writes `N_end` NULL. If either does not hold, stop: the rule
  would not be `validate`'s.
  - A serial with no row: raise, naming the serial; the package calls it only for a row it holds.
  - Docstring: when the package calls it (contract §3), and that the old layer never does.

### What the package will ask of these hooks

From the contract at `v0.4.0` (§2–§3), so that 09 changes only an import:
- **the prune**: called with `prune=True`, the hook deletes the unvalidated rows and their units;
  then called with `prune=False`, it must report nothing; and only the class's unit (the class, its
  tag tables, and tables whose `owner_column` names it) may have lost rows. I1 and I3 together
  meet this;
- **the repair**: `revalidate` on a shard that held `False` may return `True`, which is kept; a
  shard that held `True` and gets `False` is refused as `ReplicatedDivergence`. I4's rule must
  therefore never give `False` for a row `validate` set `True`.

No test here runs the package (it is not installed until 08). §2.3.2's tests check these
properties on SI's own hooks; 09's acceptance 4 runs the package's prune.

---

## 2. What to do

### 2.1 Before

1. `git grep -n "def validate_on_startup" -- 'Datastore/SQL/ObjectFactories/*.py'` lists exactly
   the 12 hooks of I2; `git grep -n prune_unvalidated -- ':!.prompts' ':!.documents'` lists them,
   the rules' examples, and the pool, actor, driver and fixture sites I2 leaves. If either finds
   more, stop.
2. Read `object_store` and `object_validate` in `Datastore/SQL/Datastore.py`, and I4's two facts.
   Record the lines.
3. The schema snapshot of a temporary store, as 05 built one (05's §2.3.1), is what §2.3.1 compares
   with: `out/05-temp-schema.json`.

### 2.2 The change

I1–I4, as §1 says, and the rules' lines. Do not reformat any file you touch.

### 2.3 Verification

1. **The schema does not change.** Build a temporary store exactly as 05's §2.3.1 did (private
   `ray.init(address="local")`, two shards, nothing stored), and compare its schema with
   `out/05-temp-schema.json` and with `out/02-reference-schema.json`: both agree. The two new keys
   add no column. Delete the store.
2. **New tests, without Ray** (in the default run), in `tests/test_inflaton_trajectory_prune.py`
   with the licence header. They use a temporary SQLite file in a `tempfile` directory whose tables
   are built from the factories' `register()`, as `Datastore._build_schema` builds them (the
   `serial`, `version` and `timestamp` columns by `register()`'s flags, then its columns), for the
   tables the tests need. Say whether the helper builds the parent tables (`efold_value`,
   `phi_value`, `tolerance`, …) or relies on SQLite not enforcing foreign keys. The tests:
   - **the cascade:** two trajectories, one validated and one not, each with value rows. The
     prune (`prune=True`) deletes the unvalidated trajectory **and its value rows**, and leaves the
     validated one with all of its own. A second call with `prune=False` reports nothing. No table
     but `InflatonTrajectory` and `InflatonTrajectoryValue` lost a row;
   - **without `prune`:** the same store, `prune=False`: the `Found 1 …` line, nothing deleted;
   - **`revalidate` agrees with `validate`** on three rows: a complete row (validated by
     `validate`, then the flag cleared by hand: `revalidate` gives `True` and writes it); a failed
     row (`N_end` NULL, no value rows: `True`); a row whose value rows were removed by hand
     (`False`). And it never gives `False` for a row `validate` set `True` on a store `store`
     wrote (the complete row's case);
   - **`prune` everywhere:** every factory in `config.datastore.factories` whose class defines
     `validate_on_startup` takes, by `inspect.signature`, the parameters `(conn, table, tables,
     prune)`. Twelve are found;
   - **the keys:** `register()` gives `owner_column == "trajectory_serial"` for the value table,
     and that column has one foreign key, to `InflatonTrajectory.serial`; and `validated_column ==
     "validated"`, a `Boolean` column, for the trajectory.
3. **An integration test** (`@pytest.mark.integration`, saying why it needs Ray: the old layer's
   prune runs inside its actors at open). Through SI's `ShardedPool`, on a store of its own with
   two shards in a `tempfile` directory:
   - open with `prune_unvalidated=False`; store two trajectories through the pool (replicated, so
     on both shards), validate one and **withhold the other's validation**; close;
   - reopen with `prune_unvalidated=True`; close;
   - read both shards with `sqlite3` `mode=ro`: on each, the validated trajectory and all its value
     rows remain; the other trajectory is gone, and **no `InflatonTrajectoryValue` row names a
     missing trajectory**.

   Build the trajectories from synthetic values (a few `efold_value`s minted through the pool),
   not from a solve, so that the test is not `slow` (`.claude/rules/test-selection.md`). It cannot
   use `live_pool` itself, which is session-scoped and opened without the prune; it may share the
   Ray instance `live_pool` starts, and must not shut Ray down if it did not start it. Say how it
   handles that, and why.
4. **The suites** (`.claude/rules/test-selection.md`: the 12 hooks are factories, so the diff
   touches none of its slow paths, and `slow` is not run): the default run gives 05's count plus the
   new tests; `RAY_ADDRESS=local ./venv/bin/python -m pytest -m integration` gives 05's plus the
   new one. All pass.

### 2.4 Deliberate breakage (README §5 rule 8)

Each is applied to the working tree, shown to be caught, reverted, and recorded as a diff that
`git apply` replays:
1. **The cascade removed** (the value-row delete deleted from I1): the cascade test fails, and the
   integration test finds orphans.
2. **`revalidate`'s failure branch inverted** (`N_end` NULL gives `False`): the failed-row case
   fails.
3. **One hook's parameter renamed back** to `prune_unvalidated` (say `CosmologicalParams.py:82`):
   the `inspect.signature` test fails, naming the factory.
4. **`owner_column` removed** from the value table's `register()`: the keys test fails. (Under the
   package the prune would also be refused; that is 09's breakage.)
5. **`revalidate` counting all value rows on every shard** (or any rule that can give `False` for a
   row `validate` set `True`): the complete-row case fails.

---

## 3. Acceptance

1. **The schema does not change** (§2.3.1). The two new keys are read by nothing on the old layer.
2. **I1:** the cascade test and the integration test pass; the rule's cascade map has the row.
3. **I2:** 12 hooks take `prune`; `git diff` of each hook is the parameter and its uses in that
   hook; the rules' examples follow; no other `prune_unvalidated` changes.
4. **I3, I4:** the keys and `revalidate` as §1 says, with I4's two facts checked and recorded.
5. **The suites** give 05's counts plus the new tests.
6. **The breakages of §2.4** are caught, and recorded as diffs.
7. **The records**, in the same commit:
   - this board: the §1 row for 06, items I1–I6, and `### 5.N After prompt 06 (<date>)`, N the
     next free number in §5;
   - **`[inflaton-trajectory-prune-orphans-value-rows]` closed**: moved from board §3 to §4, with
     how; and in `.documents/OPEN-ISSUES.md` moved to the closed section, the count and date in its
     header corrected (`CLAUDE.md`'s maintenance rule);
   - a §3 entry for anything opened, with `.documents/OPEN-ISSUES.md`.

The board's items: **I1** the cascade and the rule's row; **I2** `prune` in the 12 hooks and the
rules' examples; **I3** the two `register()` keys; **I4** `revalidate`; **I5** the tests without
Ray; **I6** the integration test.

---

## 4. Stop conditions — stop and ask

- §2.1.1 finds a hook, or a `prune_unvalidated` the hook rename would touch, beyond §1's.
- I4's two facts do not hold: `store` and its value rows are not one transaction, or a non-failed
  row can have `N_end` NULL. The rule would then not be `validate`'s; the user rules.
- The schema changes.
- The integration test cannot be written without changing `live_pool` or another existing test
  (README §5 rule 7 names none for 06).
- Any suite's count or result moves, other than by the new tests.
- Reading the package shows that it needs more of these hooks than §1 says (for example a hook
  this prompt does not add). Record what, and stop: the charter is U4's.

---

## 5. What this prompt does not do

- **Files it changes:**
  - the six factory modules of I2 (`CompactionFunction.py`, `CosmologicalParams.py`,
    `FullInstanton.py`, `GradientCoupledInstanton.py`, `InflatonTrajectory.py`,
    `SlowRollInstanton.py`), each as §1 says;
  - `.claude/rules/validate-on-startup.md` and `.claude/rules/datastore-factories.md`, the lines
    §1 names;
  - new: `tests/test_inflaton_trajectory_prune.py` (and the integration test, in it or beside it);
  - `.documents/OPEN-ISSUES.md`, the results note and this board.

  Nothing else.
- It changes no other hook's body, no pool, no driver, no `live_pool`, and no stored value: the
  cascade changes which rows a prune deletes, never a value (README §1).
- It does not touch `Datastore/SQL/Datastore.py`, which keeps calling the hooks positionally.
- It does not install `datastorekit`, runs no build and starts no Ray cluster beyond the private
  instances of §2.3.
- It changes nothing in DatastoreKit, RayPoolKit, ChamPBH or SGK.

---

## 6. The results note

`.documents/dk-and-rpk-migration/06-prepare-the-inflaton-trajectory-factories.md`, using README
§5.1. It holds:
- §2.1.1's lists;
- **I4's check**: the lines of `object_store`, `object_validate`, `store` and `validate` that make
  the rule `validate`'s, in a few sentences;
- the schema checks;
- what the package will ask (§1), and how each test shows SI's hooks meet it;
- the deliberate-breakage record, as diffs;
- the two suites beside 05's counts.

**One commit**, in the repository's form, staged by explicit path only, after showing
`git diff --cached --name-only`.
