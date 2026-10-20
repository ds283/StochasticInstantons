# 06 — prepare the `InflatonTrajectory` factories for the package

**Subject:** `InflatonTrajectory`'s startup prune cascades to its value rows; the 12 `validate_on_startup` hooks name their fourth parameter `prune`; the two `InflatonTrajectory` factories declare `owner_column` and `validated_column`; `revalidate` recomputes the stored flag by `validate`'s rule
**Commit:** this commit, on branch `dk-and-rpk-migration`, on top of `a8cb166`
**Date:** 2026-10-20, by Claude Opus 5.5
**Result:** **COMPLETE.** I1–I6 hold. The prune deletes the unvalidated trajectories' `InflatonTrajectoryValue`
rows before the trajectories, in the actor's one transaction; the 12 hooks take `(conn, table, tables, prune)`;
the two `register()` keys are present and add no column (the schema of a two-shard store agrees with
`05-temp-schema.json` and `02-reference-schema.json`); `revalidate` is `validate`'s rule as stored, and its two
premises hold. Through SI's own `ShardedPool` on two shards, a pruning reopen leaves no orphan, where with the
cascade removed it leaves three on each shard. The suites give 696 (695 passed, 1 skipped) and 62 (61 passed,
1 skipped): 05's 690 and 61 plus the 6 and 1 new tests. No stop condition of the prompt's §4 was met.
`[inflaton-trajectory-prune-orphans-value-rows]` is closed; nothing is opened.

Prompt: [`.prompts/dk-and-rpk-migration/06-prepare-the-inflaton-trajectory-factories.md`](../../.prompts/dk-and-rpk-migration/06-prepare-the-inflaton-trajectory-factories.md),
corrected by the orchestrator's brief (fourteen corrections). Scratch scripts and outputs were kept outside the
repository, in the session scratchpad; each script that supports a claim is reproduced below.

## What shipped

- **I1 — the cascade.** `sqla_InflatonTrajectory_factory.validate_on_startup`
  (`Datastore/SQL/ObjectFactories/InflatonTrajectory.py:298-316`) takes `tables.get("InflatonTrajectoryValue")`
  and, when the table is there, deletes its rows whose `trajectory_serial` is among the unvalidated serials, then the
  trajectories, on the one `conn` the actor's `_validate_on_startup` opens (`Datastore/SQL/Datastore.py:343`). It
  follows `FullInstanton.py:361-379` line for line, comment included. Both messages keep their wording; **no second
  line with the count of value rows was added**. `.claude/rules/validate-on-startup.md`'s cascade map gains the row
  `sqla_InflatonTrajectory_factory` | `InflatonTrajectory` | `InflatonTrajectoryValue` | `trajectory_serial`, and
  one sentence under the map says the parent is replicated, so its value table also declares `owner_column`.
- **I2 — `prune`.** The fourth parameter of the 12 hooks, and its 5 uses in bodies, renamed; nothing else in any
  hook. The rules' five example lines follow (`validate-on-startup.md:38`, `:43`, `:83`;
  `datastore-factories.md:205`, `:209`). The 11 other `prune_unvalidated`s (pool, actor, drivers, fixture) are
  untouched.
- **I3 — the keys.** `sqla_InflatonTrajectory_factory.register()` gains `"validated_column": "validated"` (`:34`),
  `sqla_InflatonTrajectoryValue_factory.register()` gains `"owner_column": "trajectory_serial"` (`:444`), each
  under a one-line comment saying SI's layer ignores it and DatastoreKit reads it (U4). Nothing else in either
  `register()` changes.
- **I4 — `revalidate(self, serial, conn, table, tables)`** (`:258-296`), between `validate` and
  `validate_on_startup`. It reads the row's `N_end`; NULL gives `True`; otherwise it counts the row's
  `InflatonTrajectoryValue` rows and gives `bool(count > 0)`. It writes the flag with `conn` (committing nothing),
  returns a Python `bool`, and raises `RuntimeError` naming the serial when there is no row. Its docstring says when
  the package calls it (contract §3) and that SI's layer never does.
- **I5, I6 — `tests/test_inflaton_trajectory_prune.py`** (new): 6 tests without Ray and 1 `integration` test,
  below.
- The board, `.documents/OPEN-ISSUES.md` (the issue closed) and this note.

### `InflatonTrajectory.py`'s diff

```diff
@@ -30,6 +30,8 @@ class sqla_InflatonTrajectory_factory(SQLAFactoryBase):
             "version": True,
             "timestamp": True,
             "validate_on_startup": True,
+            # Ignored by SI's own layer; DatastoreKit reads it to repair an interrupted validate (U4).
+            "validated_column": "validated",
             "columns": [
                 sqla.Column(
                     "phi0_serial",
@@ -253,12 +255,60 @@ class sqla_InflatonTrajectory_factory(SQLAFactoryBase):
         )
         return validated
 
-    def validate_on_startup(self, conn, table, tables, prune_unvalidated):
+    def revalidate(self, serial, conn, table, tables):
+        """Recompute, write and return the stored row's validated flag, by validate()'s rule.
+
+        DatastoreKit calls this (client contract §3) after an interrupted validate of this
+        replicated class, on each shard that holds the row, inside a savepoint it opens; it
+        keeps a True on a shard that held False, and refuses a False on a shard that held True.
+        SI's own layer never calls it.
+
+        The rule, as stored: a row whose N_end is NULL is a failure (store() writes N_end NULL
+        exactly on failure) and is validated; otherwise the row is validated when it has at
+        least one InflatonTrajectoryValue row. validate() asks for all of len(obj._values),
+        which is not stored; "at least one" stands for it because store() inserts the row and
+        all its value rows in one transaction, so a shard holding the row holds all of them.
+        """
+        row = conn.execute(
+            sqla.select(table.c.serial, table.c.N_end).filter(table.c.serial == serial)
+        ).one_or_none()
+        if row is None:
+            raise RuntimeError(
+                f"InflatonTrajectory.revalidate(): no row with serial {serial}"
+            )
+
+        if row.N_end is None:
+            validated = True
+        else:
+            value_table = tables["InflatonTrajectoryValue"]
+            count = conn.execute(
+                sqla.select(sqla.func.count()).select_from(value_table).filter(
+                    value_table.c.trajectory_serial == serial
+                )
+            ).scalar()
+            validated = bool(count > 0)
+
+        conn.execute(
+            sqla.update(table)
+            .where(table.c.serial == serial)
+            .values(validated=validated)
+        )
+        return validated
+
+    def validate_on_startup(self, conn, table, tables, prune):
         query = sqla.select(table.c.serial).filter(table.c.validated == False)
         rows = conn.execute(query).fetchall()
 
-        if prune_unvalidated and len(rows) > 0:
+        if prune and len(rows) > 0:
             serials = [r.serial for r in rows]
+            # Delete child value rows first; there is no ON DELETE CASCADE on the FK.
+            value_table = tables.get("InflatonTrajectoryValue")
+            if value_table is not None:
+                conn.execute(
+                    sqla.delete(value_table).where(
+                        value_table.c.trajectory_serial.in_(serials)
+                    )
+                )
             conn.execute(sqla.delete(table).filter(table.c.serial.in_(serials)))
             return [f"Pruned {len(serials)} unvalidated InflatonTrajectory records"]
         elif len(rows) > 0:
@@ -390,6 +440,8 @@ class sqla_InflatonTrajectoryValue_factory(SQLAFactoryBase):
             "serial": False,
             "version": False,
             "timestamp": False,
+            # Ignored by SI's own layer; DatastoreKit reads it to put this table in its owner's unit (U4).
+            "owner_column": "trajectory_serial",
             "columns": [
                 sqla.Column(
                     "trajectory_serial",
@@ -428,5 +480,5 @@ class sqla_InflatonTrajectoryValue_factory(SQLAFactoryBase):
             "sqla_InflatonTrajectoryValue_factory.validate() is not used directly."
         )
 
-    def validate_on_startup(self, conn, table, tables, prune_unvalidated):
+    def validate_on_startup(self, conn, table, tables, prune):
         return []
```

The other five modules' diffs are the parameter and its uses only: `CompactionFunction.py` `:491`, `:495`, `:601`;
`CosmologicalParams.py` `:82`; `FullInstanton.py` `:361`, `:365`, `:589`; `GradientCoupledInstanton.py` `:610`,
`:614`, `:744`, `:792`; `SlowRollInstanton.py` `:356`, `:360`, `:584` (each `-…prune_unvalidated…` /
`+…prune…`, 1 line for 1). `git diff --stat`: 6, 2, 6, 8, 6 lines respectively.

## Deviations from the prompt

Classified as README §5 rule 2 asks. The brief's fourteen corrections are applied as they state and not repeated,
except where the application itself was a choice.

1. **The integration test runs SI's pool in subprocesses** (brief 6), not in the pytest process beside
   `live_pool`'s Ray, which the prompt allowed. `STRUCTURALLY REQUIRED`: a second `ShardedPool` cannot open in a Ray
   session where another is open (fixed actor names), and in the `-m integration` run `live_pool` is open when the
   test runs (the `test_gci_*` modules that use it collect first; checked with `--collect-only`). Not a stop: no
   existing test changes. **Two processes, one per open** — `IMPLEMENTATION CHOICE`, as the brief recommends: each
   exits with its Ray, so nothing depends on when the first pool is collected. The test never calls `ray.init` or
   `ray.shutdown` in the pytest process.
2. **No count line in the prune's messages.** `IMPLEMENTATION CHOICE`, allowed by the prompt: the hook returns the
   one `Pruned …` line, exactly as `FullInstanton`'s does.
3. **The test helper builds all 30 tables and mints the parent rows** (brief 5 recommends the tables and says the
   parent rows need not exist). `IMPLEMENTATION CHOICE`: the trajectories' parents (`version`, two `tolerance`s,
   `phi_value`, `pi_value`s, `inflaton_mass`, `QuadraticPotential`, five `efold_value`s) are minted by their own
   factories' `build()` in the temporary store, so the trajectories are real objects with real `store_id`s, written
   by the factory's own `store()`, and the cascade test's "no table but the two lost a row" is checked against
   non-empty parent tables. The prompt's question "builds the parent tables or relies on SQLite not enforcing foreign
   keys": it builds them, and their rows too; SQLite's foreign keys are not switched on and are not needed.
4. **The helper's inserter** is `Datastore._insert` without the serial broker: the engine assigns serials, the
   `version` column takes the minted `version` row's serial, and `timestamp` is stamped. `IMPLEMENTATION CHOICE`.
5. **Extra cases in the `revalidate` test**: a non-failed row stored with no value rows (`validate` and `revalidate`
   both `False`), and a second `revalidate` of a row holding `True` (stays `True`; the other rows untouched). A
   separate test for the missing serial. `IMPLEMENTATION CHOICE`; they test the rule the prompt states, in the
   direction the package refuses as well as the direction it keeps.
6. **`revalidate` reads the value table as `tables["InflatonTrajectoryValue"]`**, as `validate` does, not by
   `tables.get`. `IMPLEMENTATION CHOICE`: it computes a flag that requires the table; only the prune's cascade needs
   to degrade without it.
7. **Breakage 5's form**: `revalidate` compares the trajectory's value rows with the number of `efold_value` rows on
   the shard (a plausible "expected" that is not `validate`'s). `IMPLEMENTATION CHOICE`; the prompt allows any rule
   that can give `False` for a row `validate` set `True`.
8. **Breakage 1's integration half fails at the first shard it reads** (`prune-shard0000.sqlite: 3 orphaned value
   rows`); the loop stops there, so shard 1's three orphans (brief 7 measured them) are not reported by the test.
   `IMPLEMENTATION CHOICE` of the assertion order; not a gap in what is caught.
9. **The new test module was formatted with `ruff format`**, and one `E741` (`l`) renamed. `IMPLEMENTATION CHOICE`
   (README §5 rule 15 allows it). No existing file was formatted. `ruff check` of `InflatonTrajectory.py` gives the
   three `E712`s it gave at `HEAD` (`validated == True` / `== False` in `build`, `validate_on_startup` and
   `read_table`), none new.
10. **Board section 5.18** (brief 12). `STRUCTURALLY REQUIRED`.
11. **A copy of `HEAD`'s `InflatonTrajectory.py` was written to `/tmp/x.py`** by one lint command and deleted in the
    same command (the comparison then used the scratch directory). No store, nothing else outside the scratch
    directory. `UNINTENDED DRIFT` from the convention that scratch files go in the scratch directory; no effect.

## Verification performed

### Before

Branch `dk-and-rpk-migration`, `HEAD` `a8cb166`, `git status` clean. `git diff --stat 875cf41 HEAD -- . ':!.prompts'
':!.documents'` is `tests/test_config_datastore.py` alone, one line. Load 4.17 6.03 6.85 at 20:30 on 10 CPUs.
`RAY_ADDRESS` unset; `pgrep -fl 'gcs_server|raylet|ray::|pytest|main.py'` finds nothing; `ray_cluster.sh status`: no
processes, the four ports free. `pip freeze` has the one `raypoolkit @ …@eaef0ce6…` line and no `datastorekit`.
DatastoreKit at `38ebb9f`, clean; `v0.4.0` is `c8570e8`.

### §2.1.1 — the two greps

`git grep -n "def validate_on_startup" -- 'Datastore/SQL/ObjectFactories/*.py'`, before:

```
Datastore/SQL/ObjectFactories/CompactionFunction.py:491:    def validate_on_startup(self, conn, table, tables, prune_unvalidated):
Datastore/SQL/ObjectFactories/CompactionFunction.py:601:    def validate_on_startup(self, conn, table, tables, prune_unvalidated):
Datastore/SQL/ObjectFactories/CosmologicalParams.py:82:    def validate_on_startup(self, conn, table, tables, prune_unvalidated):
Datastore/SQL/ObjectFactories/FullInstanton.py:361:    def validate_on_startup(self, conn, table, tables, prune_unvalidated):
Datastore/SQL/ObjectFactories/FullInstanton.py:589:    def validate_on_startup(self, conn, table, tables, prune_unvalidated):
Datastore/SQL/ObjectFactories/GradientCoupledInstanton.py:610:    def validate_on_startup(self, conn, table, tables, prune_unvalidated):
Datastore/SQL/ObjectFactories/GradientCoupledInstanton.py:744:    def validate_on_startup(self, conn, table, tables, prune_unvalidated):
Datastore/SQL/ObjectFactories/GradientCoupledInstanton.py:792:    def validate_on_startup(self, conn, table, tables, prune_unvalidated):
Datastore/SQL/ObjectFactories/InflatonTrajectory.py:256:    def validate_on_startup(self, conn, table, tables, prune_unvalidated):
Datastore/SQL/ObjectFactories/InflatonTrajectory.py:431:    def validate_on_startup(self, conn, table, tables, prune_unvalidated):
Datastore/SQL/ObjectFactories/SlowRollInstanton.py:356:    def validate_on_startup(self, conn, table, tables, prune_unvalidated):
Datastore/SQL/ObjectFactories/SlowRollInstanton.py:584:    def validate_on_startup(self, conn, table, tables, prune_unvalidated):
Datastore/SQL/ObjectFactories/base.py:29:    def validate_on_startup(self, conn, table, tables, prune=False):
```

Thirteen lines: I2's twelve at the prompt's lines, and `base.py:29`, the base class's own, which already says `prune`
and is protected (brief 1; not a stop). After: the same thirteen, each of the twelve ending `prune):`
(`InflatonTrajectory.py` at `:298` and `:483`, the others at their old lines).

`git grep -n prune_unvalidated -- ':!.prompts' ':!.documents'`, before (33 lines):

```
.claude/rules/datastore-factories.md:205:def validate_on_startup(self, conn, table, tables, prune_unvalidated):
.claude/rules/datastore-factories.md:209:    if prune_unvalidated and rows:
.claude/rules/validate-on-startup.md:38:def validate_on_startup(self, conn, table, tables, prune_unvalidated):
.claude/rules/validate-on-startup.md:43:    if prune_unvalidated and rows:
.claude/rules/validate-on-startup.md:83:def validate_on_startup(self, conn, table, tables, prune_unvalidated):
Datastore/SQL/Datastore.py:68:        prune_unvalidated: Optional[bool] = False,
Datastore/SQL/Datastore.py:78:        self._prune_unvalidated = prune_unvalidated
Datastore/SQL/Datastore.py:345:                        conn, tab, self._tables, self._prune_unvalidated
Datastore/SQL/ObjectFactories/CompactionFunction.py:491:    def validate_on_startup(self, conn, table, tables, prune_unvalidated):
Datastore/SQL/ObjectFactories/CompactionFunction.py:495:        if prune_unvalidated and len(rows) > 0:
Datastore/SQL/ObjectFactories/CompactionFunction.py:601:    def validate_on_startup(self, conn, table, tables, prune_unvalidated):
Datastore/SQL/ObjectFactories/CosmologicalParams.py:82:    def validate_on_startup(self, conn, table, tables, prune_unvalidated):
Datastore/SQL/ObjectFactories/FullInstanton.py:361:    def validate_on_startup(self, conn, table, tables, prune_unvalidated):
Datastore/SQL/ObjectFactories/FullInstanton.py:365:        if prune_unvalidated and len(rows) > 0:
Datastore/SQL/ObjectFactories/FullInstanton.py:589:    def validate_on_startup(self, conn, table, tables, prune_unvalidated):
Datastore/SQL/ObjectFactories/GradientCoupledInstanton.py:610:    def validate_on_startup(self, conn, table, tables, prune_unvalidated):
Datastore/SQL/ObjectFactories/GradientCoupledInstanton.py:614:        if prune_unvalidated and len(rows) > 0:
Datastore/SQL/ObjectFactories/GradientCoupledInstanton.py:744:    def validate_on_startup(self, conn, table, tables, prune_unvalidated):
Datastore/SQL/ObjectFactories/GradientCoupledInstanton.py:792:    def validate_on_startup(self, conn, table, tables, prune_unvalidated):
Datastore/SQL/ObjectFactories/InflatonTrajectory.py:256:    def validate_on_startup(self, conn, table, tables, prune_unvalidated):
Datastore/SQL/ObjectFactories/InflatonTrajectory.py:260:        if prune_unvalidated and len(rows) > 0:
Datastore/SQL/ObjectFactories/InflatonTrajectory.py:431:    def validate_on_startup(self, conn, table, tables, prune_unvalidated):
Datastore/SQL/ObjectFactories/SlowRollInstanton.py:356:    def validate_on_startup(self, conn, table, tables, prune_unvalidated):
Datastore/SQL/ObjectFactories/SlowRollInstanton.py:360:        if prune_unvalidated and len(rows) > 0:
Datastore/SQL/ObjectFactories/SlowRollInstanton.py:584:    def validate_on_startup(self, conn, table, tables, prune_unvalidated):
Datastore/SQL/ShardedPool.py:51:        prune_unvalidated: Optional[bool] = False,
Datastore/SQL/ShardedPool.py:66:        self._prune_unvalidated: Optional[List[str]] = prune_unvalidated
Datastore/SQL/ShardedPool.py:165:            prune_unvalidated=self._prune_unvalidated,
Datastore/SQL/ShardedPool.py:187:                    prune_unvalidated=self._prune_unvalidated,
main.py:1353:    prune_unvalidated=args.prune_unvalidated,
plot_GradientCoupledSolutions.py:987:        prune_unvalidated=False,
plot_InstantonSolutions.py:1223:        prune_unvalidated=False,
tests/conftest.py:67:        prune_unvalidated=False,
```

The 12 definitions, the 5 uses in bodies, the 5 rule lines, and the 11 that stay; nothing more, so no stop. After
(11 lines):

```
Datastore/SQL/Datastore.py:68:        prune_unvalidated: Optional[bool] = False,
Datastore/SQL/Datastore.py:78:        self._prune_unvalidated = prune_unvalidated
Datastore/SQL/Datastore.py:345:                        conn, tab, self._tables, self._prune_unvalidated
Datastore/SQL/ShardedPool.py:51:        prune_unvalidated: Optional[bool] = False,
Datastore/SQL/ShardedPool.py:66:        self._prune_unvalidated: Optional[List[str]] = prune_unvalidated
Datastore/SQL/ShardedPool.py:165:            prune_unvalidated=self._prune_unvalidated,
Datastore/SQL/ShardedPool.py:187:                    prune_unvalidated=self._prune_unvalidated,
main.py:1353:    prune_unvalidated=args.prune_unvalidated,
plot_GradientCoupledSolutions.py:987:        prune_unvalidated=False,
plot_InstantonSolutions.py:1223:        prune_unvalidated=False,
tests/conftest.py:67:        prune_unvalidated=False,
```

The actor still passes the flag positionally (`Datastore.py:344-346`), so the rename changes no call.

### I4's check — the rule is `validate`'s

Read at this commit (`InflatonTrajectory.py` lines are two below `HEAD`'s, for the two lines I3 adds in `register`):

- **One transaction per store call.** `Datastore.object_store` (`Datastore/SQL/Datastore.py:462`) opens one
  `with self._engine.begin() as conn:` (`:478`), calls the factory's `store(obj, conn=conn, …)` for every object of
  the call inside it (`:495-504`), and commits once (`:509`). A replicated store is one such call on the controlling
  shard and then one on each other shard (`Datastore/SQL/ShardedPool.py:666-689`, `_store_impl_replicated_table`),
  each its own transaction. `object_validate` (`Datastore.py:582`) likewise runs `validate` in one `engine.begin()`
  (`:591`).
- **`store` writes the row and every value row there.** `sqla_InflatonTrajectory_factory.store` (`:188-230`) inserts
  the trajectory (`:215`) and then, on the same `conn`, one `InflatonTrajectoryValue` row per element of
  `obj._values` (`:220-228`). An insert that fails (a duplicate `N_serial` under the composite key) raises, and the
  whole call rolls back, so a shard never holds a row with some of its value rows.
- **`N_end` is NULL exactly on failure.** The failure branch writes `"N_end": None` and no value row (`:208-211`);
  the other branch writes `obj._N_end` (`:215`), which the compute target sets from the remote function's `N_end`
  (`ComputeTargets/InflatonTrajectory.py:353`), always `float(sol.t_events[0][0])` on success (`:123`, returned at
  `:135`), never `None`. A success also has at least two samples (`n_points = max(2, …)`, `:129`), so `validate`'s
  `actual > 0` holds for every real non-failed row.
- **So** `validate` (`:232-256`) — `True` for a failure (`:236-237`), otherwise `actual == expected and actual > 0`
  (`:246`) — gives, on any shard holding a row `store` wrote: `True` for `N_end` NULL; and for a non-failed row,
  `actual` is all of `len(obj._values)`, so `actual == expected` always and the flag is `actual > 0`, which is
  `revalidate`'s "at least one". Both facts hold; not a stop.

### §2.3.1 — the schema does not change

05's `schema_build.py` (05's results note §2.3.1) with its label changed, run from the repository root as
`./venv/bin/python <scratch>/schema_build.py <scratch>/tmp-store`, at the working tree that became this commit:

```python
"""Build a temporary store with SI's own ShardedPool (two shards, nothing stored), then close it."""
import sys, os, tempfile, shutil
sys.path.insert(0, os.getcwd())
import ray
from Datastore.SQL.ShardedPool import ShardedPool
from config.sharding import (ShardKeyType, get_shard_key_store_id, inventory_config,
                             read_table_config, replicated_tables, sharded_tables)

tmpdir = tempfile.mkdtemp(prefix="si06-schema-", dir=sys.argv[1])
db = os.path.join(tmpdir, "temp.sqlite")
print("TMP", db)
ray.init(address="local", include_dashboard=False)
try:
    with ShardedPool(
        version_label="06-schema-check",
        db_name=db,
        ShardKeyType=ShardKeyType,
        ShardKeyStoreIdGetter=get_shard_key_store_id,
        replicated_tables=replicated_tables,
        sharded_tables=sharded_tables,
        timeout=None,
        shards=2,
        profile_agent=None,
        job_name=None,
        prune_unvalidated=False,
        drop_actions=[],
        read_table_config=read_table_config,
        inventory_config=inventory_config,
    ) as pool:
        pass
finally:
    ray.shutdown()
print("FILES", sorted(os.listdir(tmpdir)))
```

Output: `Created sharded datastore … with 2 shards`; `FILES ['temp-shard0000.sqlite', 'temp-shard0001.sqlite',
'temp.sqlite']`. Then:

```
./venv/bin/python tools/compare_stores.py --schema <tmp>/temp.sqlite --against .documents/dk-and-rpk-migration/out/05-temp-schema.json
RESULT: the schemas agree
exit 0
./venv/bin/python tools/compare_stores.py --schema <tmp>/temp.sqlite --against .documents/dk-and-rpk-migration/out/02-reference-schema.json
RESULT: the schemas agree
exit 0
```

A snapshot of the store (`--snapshot`, kept in the scratch directory, not committed) differs from
`05-temp-schema.json` only in `source`; 30 tables. The two new keys add no column, since `_build_schema` reads only
`serial`, `version`, `timestamp`, `stepping`, `validate_on_startup` and `columns` (`Datastore.py:187-289`). The store
was deleted; no Ray process was left.

### What the package will ask, and how the tests show SI's hooks meet it

Read at `v0.4.0` (`c8570e8`): `docs/client-contract.md` §2–§3, `datastorekit/SQL/ShardedPool.py`
`_recompute_validated` (`:2084`, the call at `:2110`, `is True` at `:2111` and `:2125`) and `_unit_tables` (`:2243`).
Nothing more is asked of these hooks than the prompt's §1 says (as the brief's correction 10 found).

| The package asks | Test |
|---|---|
| `validate_on_startup(..., prune=True)` deletes the unvalidated rows and their units | `test_prune_deletes_the_unvalidated_trajectory_and_its_value_rows`: the trajectory and its 3 value rows go, the validated one keeps all 3 |
| a second call with `prune=False` reports nothing | the same test: `[]`, and no count changes |
| only the class's unit lost rows | the same test: across all 30 tables, the rows lost are exactly `{"InflatonTrajectory": 1, "InflatonTrajectoryValue": 3}`; the seven parent tables keep their (non-zero) counts |
| the value table is in the unit: `owner_column`, a column with one foreign key, to the class | `test_register_declares_owner_column_and_validated_column` |
| `validated_column` is a `Boolean` column | the same test |
| the hook is called by keyword, `prune=` | `test_every_hook_takes_prune`: 12 factories by own `__dict__`, each `(conn, table, tables, prune)`; the helper calls the hook positionally, as SI's actor does, and the keyword name is what the package uses |
| `revalidate(serial, conn, table, tables)` may turn `False` into `True`; a Python `bool` | `test_revalidate_agrees_with_validate`: the complete row (cleared by hand) gives `is True` and the flag is written; the failed row gives `is True` |
| it never gives `False` for a row `validate` set `True` on rows `store` wrote | the same test: the complete and failed rows, both written by the factory's `store` and set `True` by its `validate` |
| it is called only for a row the shard holds | `test_revalidate_raises_for_a_missing_serial`: raises, naming the serial |
| the prune, on shards, at open (09's acceptance runs the package's) | `test_prune_at_open_leaves_no_orphan_on_either_shard`, through SI's own pool |

### §2.3.2, §2.3.3 — the new tests

`tests/test_inflaton_trajectory_prune.py`, with the licence header. It imports the layer first, by
`importlib.import_module("Datastore.SQL.Datastore")`, then `config.datastore`, with the reason in the module
docstring (brief 4).

The helper `_Store` builds a temporary SQLite file (in a `tempfile.TemporaryDirectory`, one per test) with all 30
tables of `config.datastore.factories`, in order, as `_build_schema` builds them; `_Parents` mints the parent rows by
their factories' `build()`; trajectories are stored and validated by `sqla_InflatonTrajectory_factory.store` and
`.validate`, each in one `engine.begin()`. Without Ray (default run):

1. `test_prune_deletes_the_unvalidated_trajectory_and_its_value_rows` — two trajectories, 3 value rows each, the
   first validated (`True`), the second withheld; `prune=True` returns
   `["Pruned 1 unvalidated InflatonTrajectory records"]`, leaves `{kept: True}` and `{kept: 3}` value rows, and the
   per-table loss is exactly the two tables' 1 and 3; a second call with `prune=False` returns `[]` and changes nothing.
2. `test_without_prune_the_hook_reports_and_deletes_nothing` — the same store, `prune=False`:
   `["Found 1 unvalidated InflatonTrajectory records (not pruned)"]`, every count unchanged.
3. `test_revalidate_agrees_with_validate` — complete row: `validate` `True`, flag cleared, `revalidate` `is True` and
   writes it; failed row (`N_end` NULL, no value rows): `validate` `True`, cleared, `revalidate` `is True`; a row whose
   value rows were deleted by hand: `revalidate` `is False` and writes it; a non-failed row stored with no value rows:
   `validate` `False`, `revalidate` `is False`; a second `revalidate` of the complete row stays `True`, the others as
   they were.
4. `test_revalidate_raises_for_a_missing_serial` — `RuntimeError` matching `serial 4242`.
5. `test_every_hook_takes_prune` — the factories whose own class defines `validate_on_startup` are exactly the 12
   named, and each `inspect.signature(...).parameters` is `[conn, table, tables, prune]`; a failure names the factory.
6. `test_register_declares_owner_column_and_validated_column` — `owner_column == "trajectory_serial"`, that column's
   one foreign key is `InflatonTrajectory.serial`; `validated_column == "validated"`, a `sqla.Boolean`.

Integration (`@pytest.mark.integration`):

7. `test_prune_at_open_leaves_no_orphan_on_either_shard` — needs Ray because the old layer prunes inside its
   `Datastore` actors at open. It runs `[sys.executable, "-c", _POOL_SCRIPT, <root>, <mode>, <db>]` twice, `cwd` the
   repository root, each process under its own `ray.init(address="local", include_dashboard=False)` and exiting
   with `ray.shutdown()`: `store` opens a two-shard pool with `prune_unvalidated=False`, mints the parents and three
   `efold_value`s through the pool, stores two trajectories on synthetic values (replicated, so on both shards),
   validates the first (`True`) and withholds the second, and prints the serials; `reopen` opens with
   `prune_unvalidated=True` and closes. Between and after, the test reads both shard files with `sqlite3`
   `mode=ro`: before, `{kept: True, pruned: False}` and 3 value rows each, no orphan; after, `{kept: True}`, 3
   value rows, no orphan. The pytest process never initialises or shuts down Ray, so `live_pool` is untouched (why
   it cannot share `live_pool`'s Ray: deviation 1). It does not depend on the actors' printed lines. 14 s alone.

### §2.3.4 — the suites

| Suite | Command | 05 | Now |
|---|---|---|---|
| default | `./venv/bin/python -m pytest -m "not integration and not slow" -q -p no:cacheprovider` | 690 (689 passed, 1 skipped) | **696 (695 passed, 1 skipped)**, 131 deselected, 30.4 s; load 4.91 6.74 6.98 |
| integration | `RAY_ADDRESS=local ./venv/bin/python -m pytest -m integration -q -p no:cacheprovider` | 61 (60 passed, 1 skipped) | **62 (61 passed, 1 skipped)**, 765 deselected, 32.9 s; load 4.16 6.34 6.82 |

The differences are the new tests: 6 in the default run, 1 in the integration run. Run serially, in the foreground,
output to files in the scratch directory; no failure, so nothing was re-run. The `slow` block is not run: the diff
touches none of `.claude/rules/test-selection.md`'s paths. No Ray process after either run.

## The deliberate-breakage record

Each was applied to the working tree, run, reverted (the file restored from a copy saved before the mutation, `cmp`
identical), and recorded as `diff -u` labelled `a/` and `b/`, so that `git apply` replays it from a clean tree at this
commit. (`git apply --check` and `-R --check` after the commit are in the hand-off, since a commit cannot record its
own check.)

### Breakage 1 — the cascade removed

```diff
--- a/Datastore/SQL/ObjectFactories/InflatonTrajectory.py
+++ b/Datastore/SQL/ObjectFactories/InflatonTrajectory.py
@@ -301,14 +301,6 @@
 
         if prune and len(rows) > 0:
             serials = [r.serial for r in rows]
-            # Delete child value rows first; there is no ON DELETE CASCADE on the FK.
-            value_table = tables.get("InflatonTrajectoryValue")
-            if value_table is not None:
-                conn.execute(
-                    sqla.delete(value_table).where(
-                        value_table.c.trajectory_serial.in_(serials)
-                    )
-                )
             conn.execute(sqla.delete(table).filter(table.c.serial.in_(serials)))
             return [f"Pruned {len(serials)} unvalidated InflatonTrajectory records"]
         elif len(rows) > 0:
```

Caught by the cascade test, and, run alone by node id under `RAY_ADDRESS=local`, by the integration test:

```
E       assert {1: 3, 2: 3} == {1: 3}
FAILED tests/test_inflaton_trajectory_prune.py::test_prune_deletes_the_unvalidated_trajectory_and_its_value_rows
1 failed, 5 passed, 1 deselected in 0.49s
E               AssertionError: prune-shard0000.sqlite: 3 orphaned value rows
E               assert 3 == 0
FAILED tests/test_inflaton_trajectory_prune.py::test_prune_at_open_leaves_no_orphan_on_either_shard
1 failed in 12.31s
```

### Breakage 2 — `revalidate`'s failure branch inverted

```diff
--- a/Datastore/SQL/ObjectFactories/InflatonTrajectory.py
+++ b/Datastore/SQL/ObjectFactories/InflatonTrajectory.py
@@ -278,7 +278,7 @@
             )
 
         if row.N_end is None:
-            validated = True
+            validated = False
         else:
             value_table = tables["InflatonTrajectoryValue"]
             count = conn.execute(
```

Caught by the failed-row case:

```
>       assert store.revalidate(failed.store_id) is True
E       assert False is True
E        +  where False = revalidate(2)
FAILED tests/test_inflaton_trajectory_prune.py::test_revalidate_agrees_with_validate
1 failed, 5 passed, 1 deselected in 0.49s
```

### Breakage 3 — one hook's parameter renamed back (`CosmologicalParams.py:82`)

```diff
--- a/Datastore/SQL/ObjectFactories/CosmologicalParams.py
+++ b/Datastore/SQL/ObjectFactories/CosmologicalParams.py
@@ -79,7 +79,7 @@
             "CosmologicalParams does not use the validate/store pipeline."
         )
 
-    def validate_on_startup(self, conn, table, tables, prune):
+    def validate_on_startup(self, conn, table, tables, prune_unvalidated):
         return []
 
     def read_table(self, conn, table, tables, units=None):
```

Caught by the signature test, naming the factory:

```
E       AssertionError: hooks not taking (conn, table, tables, prune): {'CosmologicalParams (sqla_cosmological_params_factory)': ['conn', 'table', 'tables', 'prune_unvalidated']}
FAILED tests/test_inflaton_trajectory_prune.py::test_every_hook_takes_prune
1 failed, 5 passed, 1 deselected in 0.44s
```

### Breakage 4 — `owner_column` removed

```diff
--- a/Datastore/SQL/ObjectFactories/InflatonTrajectory.py
+++ b/Datastore/SQL/ObjectFactories/InflatonTrajectory.py
@@ -440,8 +440,6 @@
             "serial": False,
             "version": False,
             "timestamp": False,
-            # Ignored by SI's own layer; DatastoreKit reads it to put this table in its owner's unit (U4).
-            "owner_column": "trajectory_serial",
             "columns": [
                 sqla.Column(
                     "trajectory_serial",
```

Caught by the keys test:

```
E       KeyError: 'owner_column'
FAILED tests/test_inflaton_trajectory_prune.py::test_register_declares_owner_column_and_validated_column
1 failed, 5 passed, 1 deselected in 0.43s
```

### Breakage 5 — `revalidate` measuring against every `efold_value` on the shard

```diff
--- a/Datastore/SQL/ObjectFactories/InflatonTrajectory.py
+++ b/Datastore/SQL/ObjectFactories/InflatonTrajectory.py
@@ -286,7 +286,10 @@
                     value_table.c.trajectory_serial == serial
                 )
             ).scalar()
-            validated = bool(count > 0)
+            expected = conn.execute(
+                sqla.select(sqla.func.count()).select_from(tables["efold_value"])
+            ).scalar()
+            validated = bool(count == expected)
 
         conn.execute(
             sqla.update(table)
```

Caught by the complete-row case (3 value rows, 5 `efold_value` rows on the store):

```
E       assert False is True
E        +  where False = revalidate(1)
FAILED tests/test_inflaton_trajectory_prune.py::test_revalidate_agrees_with_validate
1 failed, 5 passed, 1 deselected in 0.42s
```

Mutations were never staged or committed.

## Observations not acted on

- **`CLAUDE.md`'s critical rule 5** lists three value tables as examples (`FullInstantonValue`,
  `SlowRollInstantonValue`, `CompactionFunctionSamples`). 06 makes it no less true; it stays (12 may widen it).
- **`.claude/rules/datastore-factories.md`'s `validate_on_startup` pattern** (`:200-217`) shows no cascade; it is the
  pattern for a factory without a value table and was left as it is but for the name (P13 asks only for that).
- **`InflatonTrajectory.py`'s three `E712`s** (`== True` / `== False` in SQLAlchemy filters) are as at `HEAD`.
- **README §0.2's line numbers in `Datastore.py`** (`:297-330`, `:443-446`) are older still (brief 3); they are the
  README's, and 06 does not correct them.
- **DatastoreKit's SI checklist** quotes the old parameter name; it is that repository's and is not edited.

## State handed to the next prompt

- **Branch** `dk-and-rpk-migration`, this commit on `a8cb166`. New: `tests/test_inflaton_trajectory_prune.py`, this
  note. Changed: the six factory modules (`InflatonTrajectory.py`: I1, I3, I4 and its two renames; the other five: the
  rename only), `.claude/rules/validate-on-startup.md` (three lines renamed, the cascade-map row and one sentence),
  `.claude/rules/datastore-factories.md` (two lines renamed), `.documents/OPEN-ISSUES.md`, the board.
- **For 07 (RH1):** the only behaviour of the old layer that changed is which rows a pruning open deletes:
  `InflatonTrajectoryValue` rows of pruned trajectories now go with them. The messages are unchanged
  (`Pruned N unvalidated InflatonTrajectory records`). A build that prunes no trajectory is unaffected; the schema is
  unchanged (`RESULT: the schemas agree` against `02-reference-schema.json`), and no stored value changes.
- **For 09:** the `InflatonTrajectory` factories are in their package form. `owner_column` and `validated_column` are
  declared; `revalidate(serial, conn, table, tables)` returns a Python `bool` and writes with `conn`; every hook takes
  `prune`. 09 changes only their base's import. The integration test here runs SI's pool in subprocesses because SI's
  pool cannot open twice in one Ray session; once `live_pool` is the package's (09), the package's `__exit__` kills its
  actors (contract §9.3), but this test owes it nothing and can stay as it is.
- **Suites:** 696 (695 passed, 1 skipped) and 62 (61 passed, 1 skipped); `slow` baseline 69 of 69 (02's S1).
- **The venv** is untouched. No Ray cluster is up; the rehearsal lock is untouched. The only stores opened were the
  temporary ones (the schema build's, deleted; the tests' under `tempfile`). DatastoreKit (`38ebb9f`), RayPoolKit,
  ChamPBH and SGK are untouched.
- **Closed:** `[inflaton-trajectory-prune-orphans-value-rows]` (board §4; `.documents/OPEN-ISSUES.md` §7; 61 open,
  26 closed). Nothing opened. `.prompts/INDEX.md` is the orchestrator's.
- **Rollback:** `git revert` of this commit alone. The venv needs nothing.
