# 10 — port the inventory

**Subject:** the inventory ported to the `datastorekit` package: an `inventory_spec()` on every factory whose
class the inventory reads (24 registry entries, from 22 definitions), each the identity its `build` matches;
`tools/inventory_report.py`, which renders `read_inventory`'s `StoreInventory` by physical labels with every named
problem whole; `main.py --inventory` reading the closed store before Ray; the 17 old `inventory()` hooks and
`config/sharding.py`'s `inventory_config` deleted; every registered class covered, read through, or excluded with a
reason (U8), enforced by a test
**Commit:** `e2c7b22`, on branch `dk-and-rpk-migration`, on top of `62cdca5`
**Date:** 2026-10-21, by Claude Opus 5.5
**Result:** **COMPLETE.** N1–N6 hold. `inventory_classes` accepts the registry (24 classes); every column a spec
names is a column `build_schema` builds; a two-shard store written through the package's pool under a private Ray
reads back with every class at its count and **no named problem**, and its report shows today's fields.
`main.py --inventory` runs before `ray.init`: exit 0 with the report on that store, 1 on an absent store, 2 with
`--drop`, creating and changing nothing. The 30 registry entries are placed 24 / 5 / 1. U5 does not move: 31 of 31
sets give the same decision, message and `dependent_tables` with and without the specs. The suites give 730 (729
passed, 1 skipped) and 67 (66 passed, 1 skipped): the gate's 707 and 63, plus 22 new and one changed module's +1
default tests and 4 new integration tests. The six breakages are caught. `[show-all-flag-unused]` is closed;
`[gci-value-table-outside-the-inventory]` is opened. No stop condition of the prompt's §4 was met.

Prompt: [`.prompts/dk-and-rpk-migration/10-port-the-inventory.md`](../../.prompts/dk-and-rpk-migration/10-port-the-inventory.md),
corrected by the orchestrator's brief (nineteen corrections and the facts; see Deviations). Scratch scripts and
outputs were kept outside the repository, in the session scratchpad (`agent10/`); each script that supports a claim
is described or reproduced below. The orchestrator's prototypes (`orch10/specs_proto.py`, `store_proto.py`) were
read after the spec table below had been derived from the builds; the two tables agree in every leaf, parent,
`values` and `validated`, and differ only in key-field names (`lambda_` and `diffusion_model` here, `lambda` and
`diffusion` there: here every key field is named after the payload key its `build` reads it from).

## What shipped

- **N1, the specs.** 22 `def inventory_spec(self)` methods, one in each of 22 factory modules, each placed between
  `register()` and `build()` with a comment naming what `build` matches; each module gains one import line
  (`from datastorekit.store_inventory import InventorySpec` or `InventorySpec, Parent`, after the factory base's).
  `inventory_specs(factories)` returns **24**: `sqla_dimensionful_quantity_factory` serves `inflaton_mass`,
  `phi_value` and `pi_value`, each by its own `self.value_col`. One form throughout (instance methods). The two
  polymorphic maps are read from SI's registries inside the method, as `read_table` imports them. The table is
  below.
- **N2, the report.** `tools/inventory_report.py` (new, 498 lines, `ruff format`ted):
  `format_inventory_report(inventory, db_name, verbose=False) -> str`, one string. It reads nothing: its only
  look outside the `StoreInventory` is `build_schema(sqla.MetaData(), config.datastore.factories)`, in memory, for
  which columns are floats.
- **N3, `main.py --inventory`.** Two import lines and the `--inventory` block (`main.py:103-121`), before the
  `--drop` refusal and `ray.init` (`:131`). The diff is below.
- **N4.** The 17 hooks deleted, with the `from datetime import datetime` that only the hook used in 11 of the
  modules (the two other modules' `datetime` imports, `CompactionFunction.py:17` and `FullInstanton.py:17`, were
  already unused at the gate, so they stay). `config/sharding.py` loses `:77-102` (the blank line, the comment,
  `_instanton_merge` and `inventory_config`), nothing else.
- **N5.** `tests/test_inventory_specs.py`'s coverage test; placement below.
- **N6.** `.claude/rules/pool-read-apis.md` §1, `.documents/FILE_MAP.md` (two rows corrected, one added),
  `tests/test_tables_to_drop.py`'s docstring, `config/argument_parser.py`'s `--show-all` help.
- **Tests.** New: `tests/test_inventory_specs.py` (12), `tests/test_inventory_report.py` (10),
  `tests/test_inventory_store.py` (4, `integration`). Changed: `tests/test_main_refusals.py` (3 → 4).
- **Records.** This note; the board (§1, §1.1, §3, §4, §5.23, the header); `.documents/OPEN-ISSUES.md`.

### The spec table (N1), class by class

Each class's leaves and parents are the columns its `build`'s get-or-insert query matches, read at this tree
(file and line of the query's filter; "matches" is `==` unless it says otherwise). A stored column the query does
not match is not identity and is not in the key; the "not in the key" column names each such column a reader
might expect. `values` is `(value table, its column naming the owner)`; `validated` is the flag column the query
matches `== True`. No class is tagged (SI has no association table), so `tags` is `None` throughout; no parent set.
"Parent" is `key field: column → class`.

| Class | Leaves | Parents | `values` | `validated` | Source in `build`; not in the key |
|---|---|---|---|---|---|
| `version` | `label` | — | — | — | `version.py:42` `label ==`. Its table has no `timestamp`, so its timestamps read `None` |
| `store_tag` | `label` | — | — | — | `store_tag.py:42` `label ==` |
| `redshift` | `z` | — | — | — | `redshift.py:48-58` `z` relatively (absolutely at `z = 0`, by a query whose comparison is inside the `abs`: Observations) |
| `tolerance` | `log10_tol` | — | — | — | `tolerance.py:49-51` `log10_tol` within `DEFAULT_FLOAT_PRECISION`; `build` takes `tol` or `log10_tol`, stores `log10_tol` |
| `efold_value` | `N` | — | — | — | `efold.py:34-41` `N` relatively (absolutely at 0) |
| `delta_Nstar`, `N_init`, `N_final` | `value` | — | — | — | `delta_Nstar.py`, `N_init.py`, `N_final.py:34-43` `value` relatively (absolutely at 0) |
| `n_collocation_points` | `n_collocation_points` | — | — | — | `n_collocation_points.py:46-48` exact integer equality |
| `alpha_regularization` | `alpha` | — | — | — | `alpha_regularization.py:49-59` `alpha` relatively (absolutely at 0) |
| `inflaton_mass`, `phi_value`, `pi_value` | `value_PlanckMass` (`self.value_col`) | — | — | — | `DimensionfulQuantity.py:66-84` the value column relatively (absolutely at 0), the value divided by the unit first |
| `quartic_coupling` | `value` | — | — | — | `DimensionlessQuantity.py:48-64` `value` relatively (absolutely at 0) |
| `QuadraticPotential` | — | `m: mass_id → inflaton_mass` | — | — | `QuadraticPotential.py:38-40` `mass_id ==` alone; `type_id` is stored, not matched |
| `QuarticPotential` | — | `lambda_: coupling_id → quartic_coupling` | — | — | `QuarticPotential.py:38-40` `coupling_id ==` alone; `type_id` likewise |
| `MasslessDecoupledDiffusion` | — | — | — | — | `MasslessDecoupledDiffusion.py:34-36`: matches nothing; the table has only `serial` and `timestamp` and holds at most one row. `InventorySpec()` |
| `IntegrationSolver` | `label`, `stepping` | — | — | — | `integration_metadata.py:48-51` `label ==` and `stepping >=`, a minimum (the layer's `"stepping": "minimum"` column) |
| `CosmologicalParams` | `name` | — | — | — | `CosmologicalParams.py:52` `name ==` alone; the six floats it stores are not matched |
| `InflatonTrajectory` | `potential_type` | `phi0: phi0_serial → phi_value`; `pi0: pi0_serial → pi_value`; `potential: potential_serial`, by `potential_type`, `{1: QuadraticPotential, 2: QuarticPotential}`; `atol: atol_serial → tolerance`; `rtol: rtol_serial → tolerance` | `InflatonTrajectoryValue`, `trajectory_serial` | `validated` | `InflatonTrajectory.py:134-142`. Not in the key: `version`, `n_fields`, `N_end`, `diagnostics_json` (outputs), `samples_per_N` (not stored) |
| `FullInstanton`, `SlowRollInstanton` | `diffusion_type` | `trajectory: trajectory_serial → InflatonTrajectory`; `N_init: N_init_serial → N_init`; `N_final: N_final_serial → N_final`; `delta_Nstar: delta_Nstar_serial → delta_Nstar`; `atol`, `rtol` as above; `diffusion_model: diffusion_serial`, by `diffusion_type`, `{1: MasslessDecoupledDiffusion}` | `FullInstantonValue` / `SlowRollInstantonValue`, `instanton_serial` | `validated` | `FullInstanton.py:162-172`, `SlowRollInstanton.py:161-171`. Not in the key: `version`, `label`, `tags` (payload, not matched), `n_fields`, the scalars and `diagnostics_json` |
| `GradientCoupledInstanton` | `diffusion_type` | as `FullInstanton`'s, and `n_collocation_points: n_collocation_points_serial → n_collocation_points`; `alpha_regularization: alpha_regularization_serial → alpha_regularization`; `cosmo: cosmo_serial → CosmologicalParams` | `GradientCoupledInstantonProfile`, `parent_serial` (N5) | `validated` | `GradientCoupledInstanton.py:244-257`. Not in the key: `version`, `label`, `tags`, the runtime knobs (`full_instanton`, `wallclock_budget_seconds`, `max_step`, which the code says are "not part of the identity query"), the scalars |
| `CompactionFunction` | — | `trajectory: trajectory_serial → InflatonTrajectory`; `full_instanton: full_instanton_serial → FullInstanton`, **nullable**; `slow_roll_instanton: slow_roll_instanton_serial → SlowRollInstanton`, **nullable**; `delta_Nstar`; `cosmo: cosmo_serial → CosmologicalParams`; `atol`, `rtol` | `CompactionFunctionSamples`, `parent_serial` | `validated` | `CompactionFunction.py:191-210`: the five `==`, and each instanton `== serial` or `.is_(None)` when the payload has none (`:200-210`; brief correction 4). Not in the key: `C_threshold` (stored, defaulted from the payload, not matched), `label`, `tags`, `version`, the scalars, `metadata` |

- **The type columns are leaves** (`potential_type`, `diffusion_type`), as `inventory_classes` requires; both are
  matched by the lookups. The maps are `{t: info.table_name for t, info in POTENTIAL_REGISTRY.items()}` and
  `{t: info.name for t, info in DIFFUSION_MODEL_REGISTRY.items()}`, each equal to `tools/compare_stores.py`'s
  `POLYMORPHIC_REFERENCES` (asserted by `test_the_polymorphic_maps_are_si_registries_and_compare_stores`).
- **No parent is `cross_shard`, table by table.** Every parent of a replicated class is replicated. The sharded
  classes' parents: `trajectory` (replicated), `N_init`, `N_final`, `delta_Nstar`, `tolerance` ×2,
  `n_collocation_points`, `alpha_regularization`, `CosmologicalParams`, the diffusion model (all replicated, so on
  every shard), and `CompactionFunction`'s two instantons, sharded on `delta_Nstar` as it is, and given by `main.py`
  from the same `delta_Nstar`'s instanton (`_persist_pipeline_item`, `cf._full_instanton is fi`), so on its shard.
  `redshift` is in neither table list (`[redshift-registered-in-neither-table-list]`); the primary does not record
  it as replicated, so `read_inventory` reads it as sharded, the union, and it has no parent.
- **`version` is no parent and no leaf** (brief correction 3): no SI lookup matches it, and a rerun under a new
  label reuses the validated row. It has a spec of its own (`label`), for coverage.
- **Why each value table takes its slot:** each is the owner's only child table, named by its foreign key on the
  column given, except `GradientCoupledInstanton`'s two (N5).

### Coverage (N5; U8): the 30 entries

| Place | Entries | Count |
|---|---|---|
| declares a spec (`inventory_spec()` returns one) | `version`, `store_tag`, `redshift`, `tolerance`, `efold_value`, `delta_Nstar`, `N_init`, `N_final`, `n_collocation_points`, `alpha_regularization`, `inflaton_mass`, `quartic_coupling`, `phi_value`, `pi_value`, `QuadraticPotential`, `QuarticPotential`, `MasslessDecoupledDiffusion`, `IntegrationSolver`, `InflatonTrajectory`, `CosmologicalParams`, `FullInstanton`, `GradientCoupledInstanton`, `SlowRollInstanton`, `CompactionFunction` | 24 |
| read through an owner's spec, `values` slot | `InflatonTrajectoryValue` (`InflatonTrajectory`), `FullInstantonValue` (`FullInstanton`), `SlowRollInstantonValue` (`SlowRollInstanton`), `CompactionFunctionSamples` (`CompactionFunction`), `GradientCoupledInstantonProfile` (`GradientCoupledInstanton`) | 5 |
| excluded, with its reason | `GradientCoupledInstantonValue`: "written only when store_full_values is set, and a spec has one values slot, which GradientCoupledInstantonProfile (written for every row) takes; a fingerprint cannot see it: [gci-value-table-outside-the-inventory]" | 1 |

The prompt's count (24 / 4 + 1 / 1) is confirmed: 24 + 5 + 1 = 30. `redshift` and `IntegrationSolver` have specs
(preferred by the charter: cheap, and a row that did appear changes a fingerprint). The GCI choice is the prompt's
recommendation: the profile is written for every row and is the science output (`GradientCoupledInstanton.py`'s
`store`, `:597-606`), the value table only under `store_full_values` (`:580-591`). The opened issue,
`[gci-value-table-outside-the-inventory]`, is on the board's §3 and in `.documents/OPEN-ISSUES.md` §6a, owned by
the user (README §6.3: whether to ask DatastoreKit for a second value table per spec).

The coverage test does not read the specs to decide where a class belongs: `READ_THROUGH` and `EXCLUDED` are
written out; "declares a spec" is the hook returning one; for each read-through entry it checks that the named
owner's spec names that table in that slot. `EXPECTED_SPECS` likewise writes out the table above, so that a spec
naming the right columns but another identity fails a test (breakage 1 is caught only there).

### The report (N2)

`format_inventory_report(inventory: StoreInventory, db_name, verbose: bool = False) -> str` returns one string
(lines joined by `\n`, no trailing newline; `main.py` `print`s it). It imports `datetime`, `typing`, `sqlalchemy`
and `datastorekit.store_inventory` (`ClassInventory`, `Record`, `StoreInventory`) at module scope, and, inside
`_float_columns()`, `datastorekit.SQL.schema.build_schema` and `config.datastore.factories`, to build the tables in
memory and learn which columns are `Float`. No `open`, `sqlite3`, `create_engine`, `connect`, `read_inventory` or
`open_read_only` appears in it (`test_the_report_reads_nothing`, by `ast`). What it reads from the inventory: the
shards; each class's `records` (`key`, `validated`, `value_count`), `count`, `replicated`, `parents`,
`parent_types`, `earliest_timestamp`, `latest_timestamp` and `problems`; parents are found by
`StoreInventory.digest_of`. Its layout is in its module docstring; in short: a title and three summary lines; one
section per class in `SECTIONS`' order (today's thirteen first, with today's titles, then the eleven it never
showed, then "Other classes" for anything the registry adds later); a float to `.6g` with its column's unit
suffix; a parent by its own key (a one-leaf parent by its value, any other as `Class(fields that vary across its
class)`; a trajectory always with `phi0` and its potential); per compute target the class's timestamp range and
value rows, a `common to every record` line, and the validated and unvalidated groups; every problem whole as
`!! <problem>` under its class.

**The field table, against today's report** (`git show 91e6f31:main.py`, `:1227-1338`; RH1's
`out/07-readers-resumed-inventory.log`):

| Today's report | This report | |
|---|---|---|
| title `@@ DATASTORE INVENTORY` | `@@ DATASTORE INVENTORY: <db_name>`, then `read-only; N shards (#…); R records in C classes` and `problems: none` (or the count) | kept, and new lines |
| 13 sections, in this order, with these titles: `Delta N★ values`, `N_init values`, `N_final values`, `phi_0 values`, `pi_0 values`, `Inflaton mass values`, `Quartic coupling values`, `E-fold sample values`, `Inflaton trajectories`, `Full MSR instantons`, `Slow-roll instantons`, `Compaction functions`, `Gradient-coupled (onion model) instantons` | the same 13, order and titles, each title followed by `(<class>, replicated\|sharded)` | kept |
| a parameter's or quantity's values, sorted, `.6g` | the same | kept |
| a dimensionful value with its unit's name (`15 PlanckMass`), from the hook's `unit` and a units object | the same text, the unit read from the column's suffix (`value_PlanckMass`), so no units object | kept (its source changed) |
| `n value(s): [ … ]`; up to 20 whole, 21 or more as the first ten, `...`, the last ten | `n value(s)` pluralised (`1 value`, `3 values`); the same thresholds; the `...` says how many are hidden and that `--show-all` shows them | kept; `--show-all` new |
| `no values committed` for an empty class | the same | kept |
| per compute target, `@@ validated: n record(s)` and `@@ unvalidated: n record(s)` | the same two lines (and a third, `validated NULL`, should a row hold NULL) | kept |
| each group's earliest and latest timestamp, `%Y-%m-%d %H:%M – %H:%M` | one range per class, `committed %Y-%m-%d %H:%M:%S – %Y-%m-%d %H:%M:%S`, on the class's summary line | changed: `ClassInventory` carries one range per class, not one per validated group |
| each record's label, `:: FullInstanton(N_init_serial=1, N_final_serial=1, delta_Nstar_serial=1)`, sorted as strings | `:: delta_Nstar=0.5, trajectory=InflatonTrajectory(phi0=15 PlanckMass, potential=QuadraticPotential(m=1e-05 PlanckMass)) \| 3 value rows`: physical values, sorted numerically, the fields common to every record of the class printed once above | changed (P18: by physical labels, not serials) |
| a group of more than 10 labels as the first five, `...`, the last five | the same thresholds; the `...` line says how many | kept; `--show-all` new |
| the trajectory label's `N_end` | not shown | not kept: `N_end` is a computed output, in no key (the lookup does not match it) |
| `CompactionFunction(delta_Nstar_serial=…)` alone | its full key: trajectory, both instantons (`none` for a NULL side), `delta_Nstar`, `cosmo`, tolerances | changed (more) |
| the version labels | — | not kept, and never shown: the hooks collected `versions` and nothing printed them (RH1's log has none); no SI key holds a version (brief correction 3) |
| `(error: …)` for a class whose `pool.inventory` raised | — | not kept: nothing is read class by class; a store the reader refuses is refused whole, `!! --inventory: <message>` on stderr, exit 1 |
| — | the eleven classes today's report never showed: `version` (its label), `store_tag`, `redshift`, `tolerance`, `n_collocation_points`, `alpha_regularization`, `QuadraticPotential`, `QuarticPotential`, `MasslessDecoupledDiffusion`, `IntegrationSolver`, `CosmologicalParams` | new |
| — | each record's value-row count and each compute target's total (`InflatonTrajectoryValue`, …) | new |
| — | every named problem, whole, one per line, never truncated | new |

Nothing parses either report (P18; the readers' scripts and `stage_counts.py` do not read `--inventory`).

### `main.py` (N3)

```diff
@@ -36,6 +36,7 @@ from CosmologyModels.cosmo_params import CosmologicalParams
 from CosmologyModels.params import Planck2018
 from datastorekit.SQL.ProfileAgent import ProfileAgent
 from datastorekit.SQL.ShardedPool import ShardedPool
+from datastorekit.store_inventory import read_inventory
 from InflationConcepts import (
     N_final,
     N_init,
@@ -44,6 +45,7 @@ from InflationConcepts import (
 )
 from MetadataConcepts import store_tag, tolerance
 from raypoolkit import RayWorkPool
+from tools.inventory_report import format_inventory_report
 from Units import Planck_units
 from Units.base import UnitsLike
 from utilities import format_package_provenance, installed_package_provenance
@@ -98,15 +100,25 @@ if args.database is None:
 
 print(format_package_provenance(installed_package_provenance()), flush=True)
 
-# --inventory refuses until the inventory is ported to the datastorekit package, whose pool has no
-# inventory(); before Ray starts, so that nothing is created (dk-and-rpk-migration prompt 09; P11)
+# --inventory reads the closed store read-only (datastorekit.store_inventory.read_inventory), before
+# Ray starts and before any pool opens: a pool's open would apply --drop, prune unvalidated rows and
+# create a store that is not there. It changes nothing; a store that is absent, or that the package
+# refuses, is refused by the reader with a RuntimeError (dk-and-rpk-migration prompt 10)
 if args.inventory:
-    print(
-        "!! --inventory: the datastore inventory is unavailable until it is ported to the "
-        "datastorekit package (dk-and-rpk-migration prompt 10). Nothing was opened",
-        file=sys.stderr,
-    )
-    sys.exit(2)
+    if len(args.drop) > 0:
+        print(
+            f"!! --inventory: the inventory is read-only and drops nothing; it refuses --drop "
+            f"({', '.join(args.drop)}). Nothing was opened",
+            file=sys.stderr,
+        )
+        sys.exit(2)
+    try:
+        inventory = read_inventory(args.database, factories)
+    except RuntimeError as e:
+        print(f"!! --inventory: {e}", file=sys.stderr)
+        sys.exit(1)
+    print(format_inventory_report(inventory, args.database, verbose=args.show_all))
+    sys.exit(0)
 
 # the --drop groups become the tables the pool drops; a drop that would leave rows naming dropped
 # rows is refused here, before Ray starts (dk-and-rpk-migration prompt 09; U5)
```

- **Which exceptions it catches: `RuntimeError` alone.** Every refusal of `open_read_only` is one: `_refuse(…)`
  (an absent primary, a journal beside a file, an unreadable or unusable `shards` table — an absolute shard record
  included, `ShardedPool._resolve_shard_rows` —, no shards, an unreadable `replicated_tables`, an undeclared
  class) and `StoreSchemaMismatch`, a `RuntimeError` subclass (`datastorekit/SQL/schema.py:513`). A `ValueError`
  from `inventory_classes` (a spec that does not fit the registry) is SI's own defect and is left to raise.
- `--ray-address` stays required by the parser; `--inventory` never uses it. `Planck_units` is not needed: the
  report reads units from the column names. No `ray.init`, no pool, no prune, no drop, no file created.
- `config/argument_parser.py`: `--show-all`'s help was "Show all items in inventory (not just first/last 10)"; it is
  now "With --inventory, list every value and record (otherwise a list of more than 20 values shows its first and
  last 10, and a group of more than 10 records its first and last 5)". Nothing else in the file.

### U5, re-run (N4)

`dependent_tables` reads each spec's `dependencies()` as well as foreign keys. `u5.py` (scratch) records, for all
31 non-empty sets of the five groups, `dependent_tables(tables)` and `tables_to_drop`'s decision and message;
run at the gate (0 specs) and after (24 specs):

| | Specs | Closed | Refused | Sets equal to the gate's (deps, decision, message) |
|---|---|---|---|---|
| gate (`u5-before.json`) | 0 | 10 | 21 | — |
| `e2c7b22` (`u5-after.json`) | 24 | 10 | 21 | **31 of 31** |

The closed sets, both runs: `compaction-function` alone; `gradient-coupled-instanton` alone; `compaction-function`
with any non-empty set of `full-instanton`, `slow-roll-instanton` and `gradient-coupled-instanton` (7); all five. **Nothing moved**: the specs' edges that no foreign key gives are `InflatonTrajectory` →
`QuadraticPotential`, `QuarticPotential` and `FullInstanton`, `SlowRollInstanton`, `GradientCoupledInstanton` →
`MasslessDecoupledDiffusion` (computed: each spec's `dependencies()` less its table's foreign-key targets), and all
point at tables in no drop group. `tests/test_tables_to_drop.py`'s bodies are unchanged and pass (9); its module
docstring said "no factory declares an `inventory_spec` yet … Prompt 10's `inventory_spec` parents may move this
table", false now, and is corrected (docstring only; brief correction 9).

## Deviations from the prompt

1. **The board section is §5.23**, and the counts in `.documents/OPEN-ISSUES.md` are 60 open (one closed, one
   opened) and 28 closed (brief correction 1). `STRUCTURALLY REQUIRED`.
2. **"Its version labels" struck from §1.2** (brief correction 3): today's report never printed them, and no key
   holds a version, so no record can. `version` has its own spec (`label`) and is no parent; the field table
   records them as not kept. `STRUCTURALLY REQUIRED`.
3. **`CompactionFunction`'s two instanton parents are `nullable=True`** (brief correction 4), as its `build`
   matches `.is_(None)` for a missing side. `STRUCTURALLY REQUIRED`.
4. **The truncation thresholds are today's, not the prompt's wording**: a list of **more than** 20 values is
   truncated (today's `n <= 20` is shown whole; the prompt's "20 or more" is off by one, brief correction 13), and
   a group of more than 10 records shows its first and last five, as today's labels did. `STRUCTURALLY REQUIRED`
   (P18: at least what today's shows).
5. **The report's signature has no `units`.** The prompt and README name `format_inventory_report(inventory,
   db_name, units, verbose=False)`. The stored column already holds each dimensionful value in its unit
   (`value_PlanckMass`, `.claude/rules/datastore-units.md`), so the report prints the stored number with the unit
   read from the column's suffix, and a units object would be read by nothing (ChamPBH's and SGK's reports have no
   `units` either). The prompt's "or a list of lines; say which": one string. `IMPLEMENTATION CHOICE`.
6. **One range of timestamps per class, not per validated group**: `ClassInventory` carries
   `earliest_timestamp` and `latest_timestamp` for the class only. Changed in the field table. `STRUCTURALLY
   REQUIRED`.
7. **Key fields are named after the payload key `build` reads them from** (`phi0`, `pi0`, `potential`, `m`,
   `lambda_`, `trajectory`, `N_init`, `N_final`, `delta_Nstar`, `n_collocation_points`, `alpha_regularization`,
   `atol`, `rtol`, `diffusion_model`, `cosmo`, `full_instanton`, `slow_roll_instanton`). The names are part of a
   fingerprint's records, so the rule is written down here. `IMPLEMENTATION CHOICE`.
8. **The new `--inventory` tests stay in `tests/test_main_refusals.py`** (brief correction 10), changed with a
   named reason: its `inventory` case becomes `inventory-with-drop` (exit 2, the new message), a test of the
   absent store (exit 1) is added, and the order test's inventory half checks the new branch (`read_inventory`,
   `format_inventory_report`, and `sys.exit(0)`, `(1)`, `(2)`) instead of the refusal; the `drop-full-instanton`
   case and the `--drop` half are unchanged; the docstring is made true. The module goes from 3 tests to 4. The exit
   0 on a store is `tests/test_inventory_store.py`'s (integration), since a store can only be written through the
   pool. `IMPLEMENTATION CHOICE`.
9. **`tests/test_tables_to_drop.py`'s docstring corrected**, its bodies untouched (brief correction 9; P13).
   `STRUCTURALLY REQUIRED`.
10. **`.documents/FILE_MAP.md`'s two other rows** (`config/sharding.py`'s `inventory_config`, and the
    `ShardedPool` row's "prompt 10 ports it") corrected beside the new row (brief correction 12). `STRUCTURALLY
    REQUIRED`.
11. **The redshift lookup finding is added to the open `[redshift-registered-in-neither-table-list]`** (board §3
    and its index row), not opened as an issue of its own: the factory is the one that row is about, nothing writes
    it, and the brief's count of one opened issue stands. `IMPLEMENTATION CHOICE`.
12. **One new test was wrong at first and corrected before the suites were recorded.** `test_inventory_specs.py`'s
    order test asserted `not ray.is_initialized()` in the pytest process; in the default run an earlier module
    (`test_gradient_coupled_instanton_end_to_end.py`) has initialised Ray there, so it failed in the suite and
    passed alone. The assertion was removed (the no-Ray claims are made in subprocesses: `main.py --inventory`'s
    tests, and `u5.py`). `UNINTENDED DRIFT`, caught by the suite and fixed before the recorded runs.
13. **§2.1.3's grep found more than §1.3–§1.4 list**, exactly correction 11's list; none is a stop, none edited
    beyond correction 9, 10 and 12. `STRUCTURALLY REQUIRED`.

## Verification performed

### §2.1 — before

- `HEAD` `62cdca51a5c403e2e52028329a373c5f74ef6889`; `git status --short` empty; `uptime` at 19:15 BST: load 11.46
  14.67 15.44 (10 CPUs). `RAY_ADDRESS` unset; no `gcs_server`, `raylet`, `ray::`, `pytest` or `main.py` process;
  `ray_cluster.sh status`: no processes on `/tmp/ray-si`, ports 6390, 6391, 8266, 52366 free.
- **The suites at the gate**, serially, in the foreground, each to a file in the scratch directory:

  | Run | Result | Time | Load before; after |
  |---|---|---|---|
  | `./venv/bin/python -m pytest -m "not integration and not slow" -q -p no:cacheprovider` | **707: 706 passed, 1 skipped** (132 deselected) | 31.3 s | 14.07; 26.12 |
  | `RAY_ADDRESS=local ./venv/bin/python -m pytest -m integration -q -p no:cacheprovider` | **63: 62 passed, 1 skipped** (776 deselected) | 31.9 s | 26.43; 41.97 |

  09's counts (brief correction 16).
- **§2.1.3, the grep** (`git grep -n "inventory(\|inventory_config\|_instanton_merge\|show_all\|--show-all"`, outside
  `.prompts/` and `.documents/`): the 17 hooks; `config/sharding.py:78-101`; `main.py:102` (09's refusal);
  `config/argument_parser.py:403`; `.claude/rules/pool-read-apis.md:1`, `:9`, `:15`, `:72`;
  `tests/test_config_datastore.py:209`, `:234`; `tests/test_grid_builder_integration.py:138`;
  `tests/test_main_refusals.py:19`. And `inventory_spec` in `config/datastore.py:47`, `:191`, `:199` and
  `tests/test_tables_to_drop.py:24`, `:27`. Correction 11's list exactly. `test_config_datastore.py`'s `ast` guard
  on the pools (no `inventory_config=`) and the grid-builder docstring stay true and are untouched; `config/datastore.py`
  already reads `inventory_specs`.
- **§2.1.2, the spec table first.** Derived from each `build` (above) before any spec was written; then checked by
  attaching nothing at runtime but applying the specs to the tree and running `inventory_classes`, the column check
  and U5's replay (`u5.py`).

### §2.3.1 — the tests

**Without Ray** (default run):
- `tests/test_inventory_specs.py` (12): `test_inventory_classes_accepts_the_registry_and_orders_it` (the 24 classes
  in the package's order); `test_twenty_two_definitions_serve_twenty_four_entries` (24 entries; 22 SI classes in
  their MROs define the method; the three dimensionful entries' value columns);
  `test_each_spec_is_the_identity_its_build_matches` (every spec equals `EXPECTED_SPECS`, the table above written
  out: leaves, parents with column, class or map and nullability, `values`, `validated`; no tags, no parent sets);
  `test_every_named_column_is_a_column_of_its_table` (every leaf, parent column, type column — also among the
  leaves —, `validated` and value column resolves against `build_schema`, and each value column is a foreign key
  to its owner); `test_the_polymorphic_maps_are_si_registries_and_compare_stores`; `test_no_parent_crosses_a_shard`
  (no `cross_shard`; a sharded parent only under a child sharded on the same key; any other parent replicated);
  `test_version_is_no_parent`; and coverage: `test_every_registered_class_is_placed_exactly_once` (no failure; 30
  entries; 24 / 5 / 1), `test_a_class_in_none_of_the_three_is_named`, `test_a_class_in_two_places_is_named`,
  `test_a_stale_or_unexplained_exclusion_is_named` (an exclusion of a class no longer registered; one with a blank
  reason), `test_a_wrong_slot_or_owner_is_named`.
- `tests/test_inventory_report.py` (10), each on a `StoreInventory` built in the test (float leaves `float.hex`ed,
  parents by `reference_digest`), asserting rendered lines against the values chosen there:
  `test_the_title_shards_and_problems` (and no `0x` anywhere); `test_each_parameter_and_quantity_by_its_values_and_unit`
  (`14.5 PlanckMass`, `-0.25 PlanckMass`, `2e-06 PlanckMass`, `3e-14`, tolerances `1e-09, 1e-07`, δN★ sorted);
  `test_an_empty_class_says_no_values_committed`; `test_twenty_values_show_whole_and_twenty_one_are_truncated_unless_verbose`;
  `test_a_compute_target_by_counts_timestamps_and_physical_labels` (the summary line with both timestamps, the
  common line, 11 validated records cut to five and five with `... 1 record not shown ...`, the unvalidated one;
  `verbose` shows the hidden one); `test_the_trajectories_name_both_potentials_by_class`;
  `test_a_nullable_parent_with_none_prints_none`; `test_a_long_problem_is_printed_whole_on_one_line` (a problem of
  over 600 characters, with and without `verbose`, appears unbroken as one line, and the header counts it);
  `test_every_class_of_the_inventory_is_printed` (a class `SECTIONS` does not name goes under "Other classes");
  `test_the_report_reads_nothing` (`ast`: no `open`, `sqlite3`, `create_engine`, `read_inventory`,
  `open_read_only`, `connect`; the six modules it imports).
- `tests/test_main_refusals.py` (4): `test_main_refuses_before_ray[inventory-with-drop]` (exit 2, the message, the
  provenance line first, no `Traceback`, nothing in the directory) and `[drop-full-instanton]` (09's, unchanged);
  `test_inventory_of_an_absent_store_exits_1_and_creates_nothing` (exit 1; one stderr line
  `!! --inventory: Cannot read sharded datastore "<path>": the primary "<path>" …. Nothing was read or repaired`;
  nothing created); `test_both_refusals_precede_ray_init` (one `ray.init`, one `if args.inventory:` branch with
  `read_inventory`, `format_inventory_report` and exits 0, 1, 2, one `--drop` `try`, both before `ray.init`, and no
  other read of `args.inventory`). Each subprocess runs with `--ray-address 127.0.0.1:9`, `RAY_ADDRESS` set to it,
  and a 120 s timeout.

**Under Ray** (`integration`; it needs Ray because the store is written through the package's pool, whose actors
hold the shards): `tests/test_inventory_store.py` (4), on a module-scoped two-shard store under `tempfile`, built
by its `_STORE_SCRIPT` in a subprocess under `ray.init(address="local")` (13.6 s for the module alone). Through the
pool: the parameters by `object_get`; three trajectories (quadratic and quartic at `phi0 = 15`, both with 25 value
rows; a failed quadratic one at `phi0 = 16`) by `object_store` and `object_validate`, through
`InflatonTrajectoryProxy`; `FullInstanton` and `SlowRollInstanton` each successful at δN★ 0.5 (quadratic) and 1.5
(quartic) with 3 value rows and failed at 2.5; `CompactionFunction` validated at 0.5 (both sides, 8 samples), left
unvalidated at 1.5 with no slow-roll side (4 samples), failed at 2.5; `GradientCoupledInstanton` at 0.5 (5 profile
rows, 3 value rows) and failed at 2.5. Then, in the test process, with no Ray:
`test_the_store_reads_back_with_every_class_and_no_problem` (every class's count and replicated flag as expected,
`problems == ()`, the sharded rows on both shards, each record's validated flag and value count, the nullable side
resolving to `None`); `test_the_report_shows_the_fields_of_today_s_report`;
`test_main_inventory_prints_the_report_before_ray_and_changes_nothing` (exit 0; stdout the provenance line and
exactly the report; stderr empty; every file's size and SHA-256 unchanged);
`test_main_inventory_show_all_is_verbose`.

### §2.3.2 — the suites

Serially, in the foreground, each to a file in the scratch directory. No `slow` run: the diff touches no file under
`ComputeTargets/`, `Numerics/`, `Interpolation/` or `tools/diagnostics/` (`.claude/rules/test-selection.md`).

| Suite | Gate (09's) | Now | Time | Load before; after |
|---|---|---|---|---|
| default, `-m "not integration and not slow"` | 707 (706 passed, 1 skipped) | **730 (729 passed, 1 skipped)**, 136 deselected | 29.9 s | 56.18; 38.44 |
| integration, `RAY_ADDRESS=local … -m integration` | 63 (62 passed, 1 skipped) | **67 (66 passed, 1 skipped)**, 799 deselected | 46.3 s | 35.92; 41.05 |

Both were run again on the finished tree, after the breakages were reverted and before the commit: default **730 (729
passed, 1 skipped)**, 30.4 s, load 7.76; 7.91; integration **67 (66 passed, 1 skipped)**, 44.9 s, load 7.91; 37.64. No
Ray process was left after any run.

**By module** (`--collect-only -q`, gate and now; every module not listed has the same count):

| Module | Default at the gate | Now | Why |
|---|---|---|---|
| `tests/test_inventory_specs.py` | — | 12 | new (N1, N5) |
| `tests/test_inventory_report.py` | — | 10 | new (N2) |
| `tests/test_main_refusals.py` | 3 | 4 | the `inventory` case → `inventory-with-drop`; + the absent-store test (deviation 8) |
| **total** | **707** | **730** | 707 + 12 + 10 + 1 |

| Module | Integration at the gate | Now | Why |
|---|---|---|---|
| `tests/test_inventory_store.py` | — | 4 | new (N1–N3) |
| **total** | **63** | **67** | 63 + 4 |

No test was deleted: 09's refusal test is the changed `inventory` case. `tests/test_tables_to_drop.py` 9 (bodies
unchanged), `tests/test_config_datastore.py` 6, `tests/test_compare_stores.py` 24 and
`tests/test_grid_builder_integration.py` 3 keep their counts. The skip in each run is the gate's. `slow` collects
69, as at the gate. The one failure met during development was in a new test (deviation 12); no existing test
failed, so nothing was re-run alone.

### §2.3.3 — by running it

`main.py --inventory` on a store built by the same script as the integration test's (`build_store.py`, scratch;
byte-equal to `_STORE_SCRIPT`), under `<scratch>/store2/`, with `RAY_ADDRESS=127.0.0.1:9 timeout 120
./venv/bin/python main.py --database <scratch>/store2/inventory.sqlite --ray-address 127.0.0.1:9 --inventory` (and
`--show-all`): both exit 0, stderr empty; the three files' SHA-256 are the same before and after; no Ray process
before or after. On `<scratch>/store2/absent.sqlite`: exit 1, stderr `!! --inventory: Cannot read sharded
datastore "<scratch>/store2/absent.sqlite": the primary "<scratch>/store2/absent.sqlite" does not exist. Nothing
was read or repaired`, nothing created; with `--drop full-instanton`: exit 2, stderr `!! --inventory: the
inventory is read-only and drops nothing; it refuses --drop (full-instanton). Nothing was opened`. The two outputs,
whole (`<scratch>` is `/private/tmp/claude-35086/-Users-ds283-Documents-Code-StochasticInstantons/c59b6b58-6fc9-43aa-8b1e-765620e378f4/scratchpad/agent10`):

**Default:**

```text
>> packages: datastorekit 0.4.0 (https://github.com/ds283/DatastoreKit@c8570e849334d09085bbd84876095fc9e22bd005, requested v0.4.0); raypoolkit 0.2.0 (https://github.com/ds283/RayPoolKit@eaef0ce60e2fc354bb32f0ad576010e6a83c1976, requested v0.2.0)
@@ DATASTORE INVENTORY: /private/tmp/claude-35086/-Users-ds283-Documents-Code-StochasticInstantons/c59b6b58-6fc9-43aa-8b1e-765620e378f4/scratchpad/agent10/store2/inventory.sqlite
   read-only; 2 shards (#0, #1); 58 records in 24 classes
   problems: none

   -- Delta N★ values (delta_Nstar, replicated)
      3 values: [ 0.5, 1.5, 2.5 ]

   -- N_init values (N_init, replicated)
      1 value: [ 20 ]

   -- N_final values (N_final, replicated)
      1 value: [ 5 ]

   -- phi_0 values (phi_value, replicated)
      2 values: [ 15 PlanckMass, 16 PlanckMass ]

   -- pi_0 values (pi_value, replicated)
      1 value: [ -0.1 PlanckMass ]

   -- Inflaton mass values (inflaton_mass, replicated)
      1 value: [ 1e-05 PlanckMass ]

   -- Quartic coupling values (quartic_coupling, replicated)
      1 value: [ 1e-13 ]

   -- E-fold sample values (efold_value, replicated)
      25 values: [ 0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, ... 5 values not shown (--show-all shows every one) ..., 7.5, 8, 8.5, 9, 9.5, 10, 10.5, 11, 11.5, 12 ]

   -- Inflaton trajectories (InflatonTrajectory, replicated)
      3 records; 50 value rows; committed 2026-10-21 19:33:33 – 2026-10-21 19:33:33
      common to every record: pi0=-0.1 PlanckMass, atol=1e-08, rtol=1e-06
      @@ validated: 3 record(s)
         :: phi0=15 PlanckMass, potential=QuadraticPotential(m=1e-05 PlanckMass) | 25 value rows
         :: phi0=15 PlanckMass, potential=QuarticPotential(lambda_=1e-13) | 25 value rows
         :: phi0=16 PlanckMass, potential=QuadraticPotential(m=1e-05 PlanckMass) | 0 value rows
      @@ unvalidated: 0 record(s)

   -- Full MSR instantons (FullInstanton, sharded)
      3 records; 6 value rows; committed 2026-10-21 19:33:33 – 2026-10-21 19:33:33
      common to every record: N_init=20, N_final=5, diffusion_model=MasslessDecoupledDiffusion, atol=1e-08, rtol=1e-06
      @@ validated: 3 record(s)
         :: delta_Nstar=0.5, trajectory=InflatonTrajectory(phi0=15 PlanckMass, potential=QuadraticPotential(m=1e-05 PlanckMass)) | 3 value rows
         :: delta_Nstar=1.5, trajectory=InflatonTrajectory(phi0=15 PlanckMass, potential=QuarticPotential(lambda_=1e-13)) | 3 value rows
         :: delta_Nstar=2.5, trajectory=InflatonTrajectory(phi0=15 PlanckMass, potential=QuadraticPotential(m=1e-05 PlanckMass)) | 0 value rows
      @@ unvalidated: 0 record(s)

   -- Slow-roll instantons (SlowRollInstanton, sharded)
      3 records; 6 value rows; committed 2026-10-21 19:33:33 – 2026-10-21 19:33:33
      common to every record: N_init=20, N_final=5, diffusion_model=MasslessDecoupledDiffusion, atol=1e-08, rtol=1e-06
      @@ validated: 3 record(s)
         :: delta_Nstar=0.5, trajectory=InflatonTrajectory(phi0=15 PlanckMass, potential=QuadraticPotential(m=1e-05 PlanckMass)) | 3 value rows
         :: delta_Nstar=1.5, trajectory=InflatonTrajectory(phi0=15 PlanckMass, potential=QuarticPotential(lambda_=1e-13)) | 3 value rows
         :: delta_Nstar=2.5, trajectory=InflatonTrajectory(phi0=15 PlanckMass, potential=QuadraticPotential(m=1e-05 PlanckMass)) | 0 value rows
      @@ unvalidated: 0 record(s)

   -- Compaction functions (CompactionFunction, sharded)
      3 records; 12 value rows; committed 2026-10-21 19:33:33 – 2026-10-21 19:33:34
      common to every record: cosmo=Planck2018 68% central values TT+TE+EE+lowP+lensing+BAO, atol=1e-08, rtol=1e-06
      @@ validated: 2 record(s)
         :: delta_Nstar=0.5, trajectory=InflatonTrajectory(phi0=15 PlanckMass, potential=QuadraticPotential(m=1e-05 PlanckMass)), full_instanton=FullInstanton(delta_Nstar=0.5, trajectory=InflatonTrajectory(phi0=15 PlanckMass, potential=QuadraticPotential(m=1e-05 PlanckMass))), slow_roll_instanton=SlowRollInstanton(delta_Nstar=0.5, trajectory=InflatonTrajectory(phi0=15 PlanckMass, potential=QuadraticPotential(m=1e-05 PlanckMass))) | 8 value rows
         :: delta_Nstar=2.5, trajectory=InflatonTrajectory(phi0=15 PlanckMass, potential=QuadraticPotential(m=1e-05 PlanckMass)), full_instanton=FullInstanton(delta_Nstar=2.5, trajectory=InflatonTrajectory(phi0=15 PlanckMass, potential=QuadraticPotential(m=1e-05 PlanckMass))), slow_roll_instanton=SlowRollInstanton(delta_Nstar=2.5, trajectory=InflatonTrajectory(phi0=15 PlanckMass, potential=QuadraticPotential(m=1e-05 PlanckMass))) | 0 value rows
      @@ unvalidated: 1 record(s)
         :: delta_Nstar=1.5, trajectory=InflatonTrajectory(phi0=15 PlanckMass, potential=QuarticPotential(lambda_=1e-13)), full_instanton=FullInstanton(delta_Nstar=1.5, trajectory=InflatonTrajectory(phi0=15 PlanckMass, potential=QuarticPotential(lambda_=1e-13))), slow_roll_instanton=none | 4 value rows

   -- Gradient-coupled (onion model) instantons (GradientCoupledInstanton, sharded)
      2 records; 5 value rows; committed 2026-10-21 19:33:34 – 2026-10-21 19:33:34
      common to every record: N_init=20, N_final=5, n_collocation_points=5, alpha_regularization=0.01, trajectory=InflatonTrajectory(phi0=15 PlanckMass, potential=QuadraticPotential(m=1e-05 PlanckMass)), cosmo=Planck2018 68% central values TT+TE+EE+lowP+lensing+BAO, diffusion_model=MasslessDecoupledDiffusion, atol=1e-08, rtol=1e-06
      @@ validated: 2 record(s)
         :: delta_Nstar=0.5 | 5 value rows
         :: delta_Nstar=2.5 | 0 value rows
      @@ unvalidated: 0 record(s)

   -- Quadratic potentials (QuadraticPotential, replicated)
      1 record
         :: m=1e-05 PlanckMass

   -- Quartic potentials (QuarticPotential, replicated)
      1 record
         :: lambda_=1e-13

   -- Diffusion models (MasslessDecoupledDiffusion, replicated)
      1 record
         :: (no key fields)

   -- Collocation points (n_collocation_points, replicated)
      1 value: [ 5 ]

   -- Regularization alpha values (alpha_regularization, replicated)
      1 value: [ 0.01 ]

   -- Tolerances (tolerance, replicated)
      2 values: [ 1e-08, 1e-06 ]

   -- Cosmological parameters (CosmologicalParams, replicated)
      1 value: [ Planck2018 68% central values TT+TE+EE+lowP+lensing+BAO ]

   -- Redshifts (redshift, sharded)
      no values committed

   -- Integration solvers (IntegrationSolver, replicated)
      no records committed

   -- Version labels (version, replicated)
      1 value: [ 10-inventory-test ]

   -- Store tags (store_tag, replicated)
      no values committed
```

**`--show-all`** (it differs from the default in the one `E-fold sample values` line):

```text
>> packages: datastorekit 0.4.0 (https://github.com/ds283/DatastoreKit@c8570e849334d09085bbd84876095fc9e22bd005, requested v0.4.0); raypoolkit 0.2.0 (https://github.com/ds283/RayPoolKit@eaef0ce60e2fc354bb32f0ad576010e6a83c1976, requested v0.2.0)
@@ DATASTORE INVENTORY: /private/tmp/claude-35086/-Users-ds283-Documents-Code-StochasticInstantons/c59b6b58-6fc9-43aa-8b1e-765620e378f4/scratchpad/agent10/store2/inventory.sqlite
   read-only; 2 shards (#0, #1); 58 records in 24 classes
   problems: none

   -- Delta N★ values (delta_Nstar, replicated)
      3 values: [ 0.5, 1.5, 2.5 ]

   -- N_init values (N_init, replicated)
      1 value: [ 20 ]

   -- N_final values (N_final, replicated)
      1 value: [ 5 ]

   -- phi_0 values (phi_value, replicated)
      2 values: [ 15 PlanckMass, 16 PlanckMass ]

   -- pi_0 values (pi_value, replicated)
      1 value: [ -0.1 PlanckMass ]

   -- Inflaton mass values (inflaton_mass, replicated)
      1 value: [ 1e-05 PlanckMass ]

   -- Quartic coupling values (quartic_coupling, replicated)
      1 value: [ 1e-13 ]

   -- E-fold sample values (efold_value, replicated)
      25 values: [ 0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5, 5.5, 6, 6.5, 7, 7.5, 8, 8.5, 9, 9.5, 10, 10.5, 11, 11.5, 12 ]

   -- Inflaton trajectories (InflatonTrajectory, replicated)
      3 records; 50 value rows; committed 2026-10-21 19:33:33 – 2026-10-21 19:33:33
      common to every record: pi0=-0.1 PlanckMass, atol=1e-08, rtol=1e-06
      @@ validated: 3 record(s)
         :: phi0=15 PlanckMass, potential=QuadraticPotential(m=1e-05 PlanckMass) | 25 value rows
         :: phi0=15 PlanckMass, potential=QuarticPotential(lambda_=1e-13) | 25 value rows
         :: phi0=16 PlanckMass, potential=QuadraticPotential(m=1e-05 PlanckMass) | 0 value rows
      @@ unvalidated: 0 record(s)

   -- Full MSR instantons (FullInstanton, sharded)
      3 records; 6 value rows; committed 2026-10-21 19:33:33 – 2026-10-21 19:33:33
      common to every record: N_init=20, N_final=5, diffusion_model=MasslessDecoupledDiffusion, atol=1e-08, rtol=1e-06
      @@ validated: 3 record(s)
         :: delta_Nstar=0.5, trajectory=InflatonTrajectory(phi0=15 PlanckMass, potential=QuadraticPotential(m=1e-05 PlanckMass)) | 3 value rows
         :: delta_Nstar=1.5, trajectory=InflatonTrajectory(phi0=15 PlanckMass, potential=QuarticPotential(lambda_=1e-13)) | 3 value rows
         :: delta_Nstar=2.5, trajectory=InflatonTrajectory(phi0=15 PlanckMass, potential=QuadraticPotential(m=1e-05 PlanckMass)) | 0 value rows
      @@ unvalidated: 0 record(s)

   -- Slow-roll instantons (SlowRollInstanton, sharded)
      3 records; 6 value rows; committed 2026-10-21 19:33:33 – 2026-10-21 19:33:33
      common to every record: N_init=20, N_final=5, diffusion_model=MasslessDecoupledDiffusion, atol=1e-08, rtol=1e-06
      @@ validated: 3 record(s)
         :: delta_Nstar=0.5, trajectory=InflatonTrajectory(phi0=15 PlanckMass, potential=QuadraticPotential(m=1e-05 PlanckMass)) | 3 value rows
         :: delta_Nstar=1.5, trajectory=InflatonTrajectory(phi0=15 PlanckMass, potential=QuarticPotential(lambda_=1e-13)) | 3 value rows
         :: delta_Nstar=2.5, trajectory=InflatonTrajectory(phi0=15 PlanckMass, potential=QuadraticPotential(m=1e-05 PlanckMass)) | 0 value rows
      @@ unvalidated: 0 record(s)

   -- Compaction functions (CompactionFunction, sharded)
      3 records; 12 value rows; committed 2026-10-21 19:33:33 – 2026-10-21 19:33:34
      common to every record: cosmo=Planck2018 68% central values TT+TE+EE+lowP+lensing+BAO, atol=1e-08, rtol=1e-06
      @@ validated: 2 record(s)
         :: delta_Nstar=0.5, trajectory=InflatonTrajectory(phi0=15 PlanckMass, potential=QuadraticPotential(m=1e-05 PlanckMass)), full_instanton=FullInstanton(delta_Nstar=0.5, trajectory=InflatonTrajectory(phi0=15 PlanckMass, potential=QuadraticPotential(m=1e-05 PlanckMass))), slow_roll_instanton=SlowRollInstanton(delta_Nstar=0.5, trajectory=InflatonTrajectory(phi0=15 PlanckMass, potential=QuadraticPotential(m=1e-05 PlanckMass))) | 8 value rows
         :: delta_Nstar=2.5, trajectory=InflatonTrajectory(phi0=15 PlanckMass, potential=QuadraticPotential(m=1e-05 PlanckMass)), full_instanton=FullInstanton(delta_Nstar=2.5, trajectory=InflatonTrajectory(phi0=15 PlanckMass, potential=QuadraticPotential(m=1e-05 PlanckMass))), slow_roll_instanton=SlowRollInstanton(delta_Nstar=2.5, trajectory=InflatonTrajectory(phi0=15 PlanckMass, potential=QuadraticPotential(m=1e-05 PlanckMass))) | 0 value rows
      @@ unvalidated: 1 record(s)
         :: delta_Nstar=1.5, trajectory=InflatonTrajectory(phi0=15 PlanckMass, potential=QuarticPotential(lambda_=1e-13)), full_instanton=FullInstanton(delta_Nstar=1.5, trajectory=InflatonTrajectory(phi0=15 PlanckMass, potential=QuarticPotential(lambda_=1e-13))), slow_roll_instanton=none | 4 value rows

   -- Gradient-coupled (onion model) instantons (GradientCoupledInstanton, sharded)
      2 records; 5 value rows; committed 2026-10-21 19:33:34 – 2026-10-21 19:33:34
      common to every record: N_init=20, N_final=5, n_collocation_points=5, alpha_regularization=0.01, trajectory=InflatonTrajectory(phi0=15 PlanckMass, potential=QuadraticPotential(m=1e-05 PlanckMass)), cosmo=Planck2018 68% central values TT+TE+EE+lowP+lensing+BAO, diffusion_model=MasslessDecoupledDiffusion, atol=1e-08, rtol=1e-06
      @@ validated: 2 record(s)
         :: delta_Nstar=0.5 | 5 value rows
         :: delta_Nstar=2.5 | 0 value rows
      @@ unvalidated: 0 record(s)

   -- Quadratic potentials (QuadraticPotential, replicated)
      1 record
         :: m=1e-05 PlanckMass

   -- Quartic potentials (QuarticPotential, replicated)
      1 record
         :: lambda_=1e-13

   -- Diffusion models (MasslessDecoupledDiffusion, replicated)
      1 record
         :: (no key fields)

   -- Collocation points (n_collocation_points, replicated)
      1 value: [ 5 ]

   -- Regularization alpha values (alpha_regularization, replicated)
      1 value: [ 0.01 ]

   -- Tolerances (tolerance, replicated)
      2 values: [ 1e-08, 1e-06 ]

   -- Cosmological parameters (CosmologicalParams, replicated)
      1 value: [ Planck2018 68% central values TT+TE+EE+lowP+lensing+BAO ]

   -- Redshifts (redshift, sharded)
      no values committed

   -- Integration solvers (IntegrationSolver, replicated)
      no records committed

   -- Version labels (version, replicated)
      1 value: [ 10-inventory-test ]

   -- Store tags (store_tag, replicated)
      no values committed
```

### §2.3.4 — `ruff check --select F401,F811,F821`

On the 27 Python files the diff modifies, each at the gate (`git show HEAD:<file> | ruff check --stdin-filename
<file> -`) and now: **18 findings at the gate, 18 now, none new** (`main.py` 12 `F401` and 4 `F811`;
`CompactionFunction.py:17` and `FullInstanton.py:17`, `datetime`, the gate's). The 11 `datetime` imports deleted
were used by the hooks alone, so they are not findings at the gate and would have been after. The four new files:
`ruff format`, then `ruff check --select F401,F811,F821,F541`: clean.

## The deliberate-breakage record

Each diff was applied with `git apply` to the working tree that `e2c7b22` records, the named tests run, and
reverted with `git apply -R`; after all six, `git diff` and `git status --short` were byte-identical to those saved
before the first. Each is recorded as `diff -u` labelled `a/` and `b/`, so that `git apply` replays it from a clean
tree at `e2c7b22`. (`git apply --check` and `-R --check` after the commit are in the hand-off, since a commit
cannot record its own check.)

### Breakage 1 — one spec's parent removed (`FullInstanton`'s `delta_Nstar`)

```diff
--- a/Datastore/SQL/ObjectFactories/FullInstanton.py
+++ b/Datastore/SQL/ObjectFactories/FullInstanton.py
@@ -112,7 +112,6 @@
                 "trajectory": Parent("trajectory_serial", of="InflatonTrajectory"),
                 "N_init": Parent("N_init_serial", of="N_init"),
                 "N_final": Parent("N_final_serial", of="N_final"),
-                "delta_Nstar": Parent("delta_Nstar_serial", of="delta_Nstar"),
                 "atol": Parent("atol_serial", of="tolerance"),
                 "rtol": Parent("rtol_serial", of="tolerance"),
                 "diffusion_model": Parent(
```

Caught. `pytest tests/test_inventory_specs.py tests/test_tables_to_drop.py`: 1 failed, 20 passed;
`test_each_spec_is_the_identity_its_build_matches`: `AssertionError: FullInstanton … At index 1 diff`. Only the
written-out table catches it: the columns still resolve and the foreign key still makes the U5 edge.

### Breakage 2 — one leaf misnamed (`N_init`'s `value` → `valu`)

```diff
--- a/Datastore/SQL/ObjectFactories/N_init.py
+++ b/Datastore/SQL/ObjectFactories/N_init.py
@@ -26,7 +26,7 @@
 
     def inventory_spec(self):
         # build() matches value alone, relatively (absolutely at 0) (dk-and-rpk-migration prompt 10)
-        return InventorySpec(leaves=("value",))
+        return InventorySpec(leaves=("valu",))
 
     def build(self, payload, conn, table, inserter, tables, inserters):
         value = payload["value"]
```

Caught. `pytest tests/test_inventory_specs.py`: 2 failed, 10 passed; `test_each_spec_is_the_identity_its_build_matches`
(`('valu',) != ('value',)`) and `test_every_named_column_is_a_column_of_its_table` (`N_init: leaf valu`).

### Breakage 3 — the type column dropped from a polymorphic parent's leaves (`InflatonTrajectory`)

```diff
--- a/Datastore/SQL/ObjectFactories/InflatonTrajectory.py
+++ b/Datastore/SQL/ObjectFactories/InflatonTrajectory.py
@@ -99,7 +99,7 @@
         from CosmologyConcepts.Potentials.registry import POTENTIAL_REGISTRY
 
         return InventorySpec(
-            leaves=("potential_type",),
+            leaves=(),
             parents={
                 "phi0": Parent("phi0_serial", of="phi_value"),
                 "pi0": Parent("pi0_serial", of="pi_value"),
```

Caught. 3 failed, 9 passed; `test_inventory_classes_accepts_the_registry_and_orders_it` meets the package's refusal,
`ValueError: inventory_classes(): InflatonTrajectory.potential is a polymorphic parent whose type column
potential_type is not one of InflatonTrajectory's leaves`; the identity and column tests fail too.

### Breakage 4 — `--inventory` moved after `ray.init`

```diff
--- a/main.py
+++ b/main.py
@@ -99,6 +99,16 @@
     sys.exit()
 
 print(format_package_provenance(installed_package_provenance()), flush=True)
+
+# the --drop groups become the tables the pool drops; a drop that would leave rows naming dropped
+# rows is refused here, before Ray starts (dk-and-rpk-migration prompt 09; U5)
+try:
+    drop_tables = tables_to_drop(args.drop)
+except ValueError as e:
+    print(f"!! --drop: {e}. Nothing was opened", file=sys.stderr)
+    sys.exit(2)
+
+ray.init(address=args.ray_address)
 
 # --inventory reads the closed store read-only (datastorekit.store_inventory.read_inventory), before
 # Ray starts and before any pool opens: a pool's open would apply --drop, prune unvalidated rows and
@@ -119,16 +129,6 @@
         sys.exit(1)
     print(format_inventory_report(inventory, args.database, verbose=args.show_all))
     sys.exit(0)
-
-# the --drop groups become the tables the pool drops; a drop that would leave rows naming dropped
-# rows is refused here, before Ray starts (dk-and-rpk-migration prompt 09; U5)
-try:
-    drop_tables = tables_to_drop(args.drop)
-except ValueError as e:
-    print(f"!! --drop: {e}. Nothing was opened", file=sys.stderr)
-    sys.exit(2)
-
-ray.init(address=args.ray_address)
 
 
 def inflaton_trajectory_store_handler(obj, pool):
```

Caught. `pytest tests/test_main_refusals.py -k precede`: 1 failed; `AssertionError: the --inventory branch (line
117) must precede ray.init (line 111)`. (The subprocess tests were not run on this mutation: `main.py` would try
to connect to `127.0.0.1:9` first and wait out the timeout, as 09's breakage 4 showed.)

### Breakage 5 — the spec removed from one owner (`GradientCoupledInstanton`)

```diff
--- a/Datastore/SQL/ObjectFactories/GradientCoupledInstanton.py
+++ b/Datastore/SQL/ObjectFactories/GradientCoupledInstanton.py
@@ -144,43 +144,6 @@
             ],
         }
 
-    def inventory_spec(self):
-        # build() matches validated == True and the serials of the trajectory, N_init, N_final,
-        # delta_Nstar, n_collocation_points, alpha_regularization, atol, rtol, the diffusion
-        # model (with diffusion_type, which names its table) and the cosmology; the version,
-        # label, tags and the runtime knobs are not matched. The diffusion model's map is
-        # DIFFUSION_MODEL_REGISTRY's. Of the two child tables, the profile, written for every
-        # row, takes the one values slot; GradientCoupledInstantonValue, written only with full
-        # values, is outside the inventory (dk-and-rpk-migration prompt 10;
-        # [gci-value-table-outside-the-inventory])
-        from InflationConcepts.DiffusionModel.registry import DIFFUSION_MODEL_REGISTRY
-
-        return InventorySpec(
-            leaves=("diffusion_type",),
-            parents={
-                "trajectory": Parent("trajectory_serial", of="InflatonTrajectory"),
-                "N_init": Parent("N_init_serial", of="N_init"),
-                "N_final": Parent("N_final_serial", of="N_final"),
-                "delta_Nstar": Parent("delta_Nstar_serial", of="delta_Nstar"),
-                "n_collocation_points": Parent(
-                    "n_collocation_points_serial", of="n_collocation_points"
-                ),
-                "alpha_regularization": Parent(
-                    "alpha_regularization_serial", of="alpha_regularization"
-                ),
-                "atol": Parent("atol_serial", of="tolerance"),
-                "rtol": Parent("rtol_serial", of="tolerance"),
-                "diffusion_model": Parent(
-                    "diffusion_serial",
-                    type_column="diffusion_type",
-                    types={t: info.name for t, info in DIFFUSION_MODEL_REGISTRY.items()},
-                ),
-                "cosmo": Parent("cosmo_serial", of="CosmologicalParams"),
-            },
-            values=("GradientCoupledInstantonProfile", "parent_serial"),
-            validated="validated",
-        )
-
     def build(self, payload, conn, table, inserter, tables, inserters):
         from ComputeTargets.GradientCoupledInstanton.GradientCoupledInstanton import (
             GradientCoupledInstanton,
```

Caught. `pytest tests/test_inventory_specs.py`: 9 failed, 3 passed. The coverage test names both consequences:
`GradientCoupledInstanton: declares no inventory_spec, is read through no owner's spec, and is not excluded` and
`GradientCoupledInstantonProfile: its owner GradientCoupledInstanton declares no spec`; the order, count, identity
and map tests fail too.

### Breakage 6 — a new registered class with no spec and no exclusion

```diff
--- a/config/datastore.py
+++ b/config/datastore.py
@@ -129,6 +129,7 @@
     "CosmologicalParams": sqla_cosmological_params_factory(),
     "FullInstanton": sqla_FullInstantonFactory(),
     "FullInstantonValue": sqla_FullInstantonValue_factory(),
+    "ScratchValue": sqla_FullInstantonValue_factory(),
     "GradientCoupledInstanton": sqla_GradientCoupledInstantonFactory(),
     "GradientCoupledInstantonValue": sqla_GradientCoupledInstantonValue_factory(),
     "GradientCoupledInstantonProfile": sqla_GradientCoupledInstantonProfileFactory(),
```

Caught. `pytest tests/test_inventory_specs.py`: 5 failed, 7 passed; `test_every_registered_class_is_placed_exactly_once`:
`ScratchValue: declares no inventory_spec, is read through no owner's spec, and is not excluded` (the other four are
the coverage tests that compare against the registry's own failures).

## The prose corrected (P13)

- **`.claude/rules/pool-read-apis.md`**, §"There is no `pool.inventory()`" (`:11-19`): "Until dk-and-rpk-migration
  prompt 10 ports it, `main.py --inventory` refuses before Ray starts. From 10 the inventory is …" becomes "Since
  dk-and-rpk-migration prompt 10 the inventory is `read_inventory(primary, factories)`: read-only, on a closed
  store, with no Ray, over each factory's `inventory_spec()`. `main.py --inventory` runs it before Ray starts and
  prints `tools/inventory_report.py`'s report." The title (`:1`) and `:72` ("not via `inventory()`") stay true and
  are unchanged.
- **`.documents/FILE_MAP.md`**: `config/sharding.py`'s row (`:17`) no longer lists `inventory_config`; the
  `ShardedPool` row (`:41`) says the inventory is `read_inventory`, which `main.py --inventory` runs before Ray, in
  place of "prompt 10 ports it"; a row for `tools/inventory_report.py` (`:42`).
- **`tests/test_tables_to_drop.py`'s docstring** (`:23-29`): the specs did not move U5, and why.
- **`config/argument_parser.py`**: `--show-all`'s help (above).

### What remains stale, for 12

- **A rule asking every new factory for an `inventory_spec`** (and for a row in the test's `EXPECTED_SPECS`, or in
  `READ_THROUGH` / `EXCLUDED`), in `.claude/rules/datastore-factories.md` or a rule of its own: 12's, with the rules'
  rewrite (the prompt's §1.6).
- **`.documents/INFRASTRUCTURE.md`** `:183` (`inventory()` among the actor's methods), `:228` (`inventory(cls_name,
  ...)` in the pool's method table), `:232` (routing around the gap with `inventory()`), `:498` (the invariant row
  "`pool.inventory()` is a reporting tool"); already on 09's list.
- **`.documents/architecture-summary.md`** `:194` (`inventory()` on the actor), `:227` (the method table), `:394`,
  `:403` (`main.py`'s flow, `if args.inventory: inventory(pool, units)`), `:494-500` (the four deleted helpers and
  `pool.inventory()`), `:580` (the invariant row); already on 09's list.
- **`.documents/FILE_MAP.md:54`**: `SQLAFactoryBase`'s protocol is listed without `inventory_spec()`, which SI's
  factories now declare (incomplete rather than false; not changed).
- 09's list otherwise stands (`tools/compare_stores.py:39`, `:94`, `:115-116`;
  `tests/test_rehearsal_stage_counts.py:26`; three comments in `ObjectFactories/InflatonTrajectory.py`, now at
  `:34`, `:289`, `:419`; `pool-read-apis.md`'s claim that `config/sharding.py` is on `CLAUDE.md`'s protected list).

## Observations not acted on

- **`sqla_redshift_factory.build`'s query at `z = 0`** (`redshift.py:49-51`) reads
  `sqla.func.abs((table.c.z - z) < DEFAULT_REDSHIFT_PRECISION)`: the comparison is inside the `abs`, so it matches
  every row whose `z` is below the precision (negative ones too), and `one_or_none()` raises when two do. ChamPBH's
  inherited factory has the same line (its 09 opened an issue for it). Nothing in SI writes `redshift`, so it is
  unreachable; the spec reads the stored leaf, not the lookup. Recorded in `[redshift-registered-in-neither-table-list]`
  (deviation 11). A fix is a factory change outside this prompt.
- **A failed and a successful compute target with one key are a `duplicate`** to the package (every compute-target
  `build` matches `validated == True` with no failure column, and `validate` sets a failed row's flag to `True`).
  SI's drivers never write both under one key (a validated failure is reused, not recomputed), so a store the
  drivers wrote names none; the integration store gives its failed rows keys of their own. An unvalidated row
  left beside a recomputed validated one (after an interrupt, before a pruning reopen) would also be a `duplicate`:
  11's killed-and-resumed build prunes at the resumed open, so its stores should name none.
- **`IntegrationSolver`'s `stepping` is matched as a minimum**, so two rows with one label and different
  `stepping` are two records though one lookup can return either; nothing writes the table.
- **`CompactionFunction` records render long** (the trajectory again inside each instanton parent); every field is
  physical, and nothing parses the report.
- **The `live_pool` store would name `unresolved-parent`** (brief §0): six modules write rows whose trajectory is a
  stand-in serial. Not a defect of the specs; a reason the integration test builds its own store.

## State handed to the next prompt

- **Branch** `dk-and-rpk-migration`, `e2c7b22` on `62cdca5`. Changed: the 22 factory modules (a spec and its
  import each; the 17 hooks and 11 `datetime` imports gone), `config/sharding.py` (`inventory_config`,
  `_instanton_merge` and their comment gone), `config/argument_parser.py` (`--show-all`'s help), `main.py` (the
  `--inventory` branch and two imports), `tests/test_main_refusals.py`, `tests/test_tables_to_drop.py` (docstring),
  `.claude/rules/pool-read-apis.md`, `.documents/FILE_MAP.md`, `.documents/OPEN-ISSUES.md`, the board. New:
  `tools/inventory_report.py`, `tests/test_inventory_specs.py`, `tests/test_inventory_report.py`,
  `tests/test_inventory_store.py`, this note.
- **The inventory.** `datastorekit.store_inventory.read_inventory(primary, config.datastore.factories)` reads 24
  classes in the order `version`, `store_tag`, `redshift`, `tolerance`, `efold_value`, `delta_Nstar`, `N_init`,
  `N_final`, `n_collocation_points`, `alpha_regularization`, `inflaton_mass`, `quartic_coupling`, `phi_value`,
  `pi_value`, `MasslessDecoupledDiffusion`, `IntegrationSolver`, `CosmologicalParams`, `QuadraticPotential`,
  `QuarticPotential`, `InflatonTrajectory`, `FullInstanton`, `GradientCoupledInstanton`, `SlowRollInstanton`,
  `CompactionFunction`; 22 SI definitions; every registered class covered (24 specs, 5 read through, 1 excluded:
  `GradientCoupledInstantonValue`, `[gci-value-table-outside-the-inventory]`). For RunRegistryKit (README §7): a
  client `fingerprint_format` will be SI's to choose; any change to a spec or to the registry changes what a
  fingerprint sees.
- **Suites:** default **730** (729 passed, 1 skipped), integration **67** (66 passed, 1 skipped); `slow` not run (69
  collected, as at the gate).
- **For 11.**
  - **`main.py --inventory` now reads before Ray** (its readers' step 1): it prints the provenance line, then the
    report, and exits 0, with no `ray.init` and no pool. On a fresh store the report has the layout of the two
    samples above: a title naming the path as given, `read-only; N shards (#0, …); R records in 24 classes`,
    `problems: none` (or a count, each problem whole under its class), then the 24 sections in `SECTIONS`' order
    (today's thirteen first, with today's titles), each compute target with a class-wide `committed … – …` range, a
    `common to every record:` line and its validated and unvalidated records by physical labels. **Its layout
    differs from RH1's by design** (`out/07-readers-resumed-inventory.log`; the field table above): no serial labels,
    one timestamp range per class, eleven more classes, value-row counts. Nothing parses it, `stage_counts.py`
    included. A clean RH2 store should print `problems: none` (11's L-items ask for "`--inventory` with no
    problem"); a `duplicate` would mean an unvalidated row beside a validated one with the same key (Observations).
  - **RH0's and RH1's stores are refused by it, exit 1** with `!! --inventory: Cannot read sharded datastore "…":
    … Nothing was read or repaired` on stderr: every store SI's old layer wrote is refused by the package (README
    §0.1 item 6, §7; among the reasons, its absolute shard records, which `ShardedPool._resolve_shard_rows` refuses
    as unusable). This was not run on those stores (10 opens none); the absent-store test shows the exit and the
    message's form. So `tools/compare_stores.py` remains the comparison between RH1 and RH2.
- **For 12.** The stale list above (a spec rule for new factories; `INFRASTRUCTURE.md` and `architecture-summary.md`
  lines; `FILE_MAP.md:54`; 09's list).
- **The venv** is untouched (nothing installed). No Ray cluster is up; the rehearsal lock is untouched. The only
  stores opened were temporary ones: the tests' (under `tempfile`) and the scratch stores `store1/`, `store2/`
  (built through the package's pool under a private Ray, read by `read_inventory` and `main.py --inventory`).
  DatastoreKit, RayPoolKit, ChamPBH and SGK are untouched (read only).
- **Closed:** `[show-all-flag-unused]` (board §4; `.documents/OPEN-ISSUES.md` §7). **Opened:**
  `[gci-value-table-outside-the-inventory]` (board §3; index §6a; the user's, README §6.3). 60 open, 28 closed. The
  README and `.prompts/INDEX.md` are the orchestrator's.
- **Rollback:** `git revert` of `e2c7b22` alone; nothing in the venv (README §4.4). The revert restores 09's
  refusal and the old hooks; no store changes.
