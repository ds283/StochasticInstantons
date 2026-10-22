# 10b — count the gradient instanton's value table

**Subject:** `GradientCoupledInstanton`'s `inventory_spec` declares `GradientCoupledInstantonValue` as a further value
table (`extra_values`, DatastoreKit `v0.5.0`, pinned by 10a), so that `read_inventory`, and any fingerprint taken
through it, counts that table per record; 10's spec, coverage and store tests and the report follow
**Commit:** this commit, on branch `dk-and-rpk-migration`, on top of `d590b30`
**Date:** 2026-10-22, by Claude Opus 5.5
**Result:** **COMPLETE.** X1–X5 hold. One keyword in the spec, `extra_values={"GradientCoupledInstantonValue":
"instanton_serial"}`, and its comment made true; nothing else in the factory. The 30 registry entries are placed
**24 / 6 / 0** (specs, read through, excluded): `GradientCoupledInstantonValue` is read through its owner's
`extra_values` slot and nothing is excluded. The integration store holds a third gradient instanton, stored without
full values by `set_store_full_values(False)`, and its three gradient records read back `(True, 5, {…: 3})`,
`(True, 5, {…: 0})` and `(True, 0, {…: 0})` with **no named problem**. The report prints each further table's
count by its name, on the record lines and the class summary, 0 as 0. With the declaration and without it, only
`GradientCoupledInstanton`'s class digest moves (1 of 24); the four digests equal the orchestrator's prototype's. U5
does not move (31 of 31 sets equal). The suites give **732 (731 passed, 1 skipped)** and **67 (66 passed, 1
skipped)**: 10a's 730 and 67, plus the two new report tests. The five breakages are caught.
`[gci-value-table-outside-the-inventory]` is closed. No stop condition of the prompt's §4 was met.

Prompt: [`.prompts/dk-and-rpk-migration/10b-count-the-gradient-value-table.md`](../../.prompts/dk-and-rpk-migration/10b-count-the-gradient-value-table.md),
corrected by the orchestrator's brief (twelve corrections and the facts; applied, see Deviations). Scratch scripts
and outputs were kept outside the repository, in the session scratchpad (`agent10b/`); each script that supports a
claim is described or reproduced below. The orchestrator's prototype (`orch10b/proto.py`) was read; nothing of it
was run or reused but its digests, which this note compares against.

## What shipped

### X1 — the declaration

`Datastore/SQL/ObjectFactories/GradientCoupledInstanton.py`, the whole diff:

```diff
--- a/Datastore/SQL/ObjectFactories/GradientCoupledInstanton.py
+++ b/Datastore/SQL/ObjectFactories/GradientCoupledInstanton.py
@@ -150,9 +150,9 @@ class sqla_GradientCoupledInstantonFactory(SQLAFactoryBase):
         # model (with diffusion_type, which names its table) and the cosmology; the version,
         # label, tags and the runtime knobs are not matched. The diffusion model's map is
         # DIFFUSION_MODEL_REGISTRY's. Of the two child tables, the profile, written for every
-        # row, takes the one values slot; GradientCoupledInstantonValue, written only with full
-        # values, is outside the inventory (dk-and-rpk-migration prompt 10;
-        # [gci-value-table-outside-the-inventory])
+        # row, takes the values slot; GradientCoupledInstantonValue, written only with full
+        # values, is counted as a further value table (extra_values), 0 for a row stored without
+        # full values (dk-and-rpk-migration prompts 10 and 10b)
         from InflationConcepts.DiffusionModel.registry import DIFFUSION_MODEL_REGISTRY
 
         return InventorySpec(
@@ -178,6 +178,7 @@ class sqla_GradientCoupledInstantonFactory(SQLAFactoryBase):
                 "cosmo": Parent("cosmo_serial", of="CosmologicalParams"),
             },
             values=("GradientCoupledInstantonProfile", "parent_serial"),
+            extra_values={"GradientCoupledInstantonValue": "instanton_serial"},
             validated="validated",
         )
 
```

The keyword is `:181`, beside `values=` (`:180`); `instanton_serial` is the value table's foreign key to
`GradientCoupledInstanton.serial` (`:686-692`). The comment (`:148-155`) now says the table is counted as a further
value table, 0 for a row stored without full values, and no longer cites the closed issue. Nothing else changes: by
`ast`, the module at `d590b30` and now differ in `inventory_spec` alone, and there by the one keyword (comments are
not in the tree).

### X2 — the spec and coverage tests (`tests/test_inventory_specs.py`, 12 tests, unchanged in number)

Each change, with its reason (README §5 rule 7's named exception for 10b):
- **`EXPECTED_SPECS`** (`:102-194`): every entry gains a fifth element, the spec's `extra_values` as a mapping: `{}`
  for 23 classes and `{"GradientCoupledInstantonValue": "instanton_serial"}` for `GradientCoupledInstanton`. Its
  comment names the fifth element. Reason: the table is the spec's written-out identity, and a spec that lost or
  changed the keyword must fail it.
- **`_as_table`** (`:289-309`) returns `dict(spec.extra_values)` as the fifth element. Reason: without it the identity
  test compares four elements and passes whatever `extra_values` is (the brief's first vacuous pass). Breakage 1 is
  the proof.
- **The column test** (`test_every_named_column_is_a_column_of_its_table`, `:347-389`): for each extra table, that the
  table is built, that its column is in it, and that the column's foreign keys name exactly the owner, as the
  `values` branch does; and, after the loop, that the tables it met are exactly those `EXPECTED_SPECS` declares
  (`{"GradientCoupledInstanton": ["GradientCoupledInstantonValue"]}`), so that it cannot pass by meeting none.
  Breakage 2 is the proof (the misnamed column fails here, not only in the identity test).
- **`READ_THROUGH`** (`:206-213`) gains `"GradientCoupledInstantonValue": ("GradientCoupledInstanton",
  "extra_values")`; **`EXCLUDED`** (`:215-217`) is an empty mapping, its comment saying none is excluded since 10b;
  **`SLOTS`** (`:219`) gains `"extra_values"`. Reason: the table is now read through its owner's spec.
- **`_slot_tables`** (`:227-234`) returns a mapping slot's keys for `"extra_values"` (today it took `value[0]` of a
  pair, which on a mapping is a `KeyError` or a lookup that happens to succeed). Breakages 1 and 5 are the proof.
- **The placement** (`:443`): `(24, 6, 0)` in place of `(24, 5, 1)`.
- **The stale-exclusion literal** (`test_a_stale_or_unexplained_exclusion_is_named`, `:461-472`): its second case
  excluded `GradientCoupledInstantonValue` with `" "`; that class is now in `READ_THROUGH`, so the case would get a
  second failure ("in more than one place"). The class is taken out of `READ_THROUGH` for that case only (`{k: v for
  k, v in READ_THROUGH.items() if k != "GradientCoupledInstantonValue"}`), so the assertion is still the one-element
  list `["GradientCoupledInstantonValue: excluded with no reason"]` and refuses what it refused. The first case
  (`temperature`) is unchanged.
- The two tests that build on `EXCLUDED` with `dict(EXCLUDED, …)` work on the empty mapping as they stand, unchanged.
  No assertion of the five breakage-catching tests was removed or loosened. The module docstring stays true (its
  coverage bullet holds with `EXCLUDED` empty) and is unchanged.

By `ast` against `d590b30`, the functions that changed are exactly `_slot_tables`, `_as_table`, the column test, the
placement test and the stale-exclusion test; no function was added or removed.

### X3 — the report (`tools/inventory_report.py`)

A compute target's record line and class summary now carry, after the value rows its `values` slot counts, the rows
of each further value table its spec declares, by the table's name, in the table names' order, `; `-separated, 0
printed as 0. A class with none prints exactly as 10's. One helper, `_counts_text` (`:368-377`), used by
`_record_lines` (`:387`); the summary's totals (`:423-426`). The module docstring's compute-target bullet names the
further tables (brief correction 6). The field-table row (10's table, one new row):

| Today's report (10's) | This report | |
|---|---|---|
| a record's `\| n value rows` and the class's `n value rows` (the `values` slot: for `GradientCoupledInstanton`, its profile rows) | the same, then, for each further value table the spec declares (`extra_values`), `; n <table> rows` by the table's name, 0 printed as 0, on each record line and in the class summary: `:: delta_Nstar=0.5 \| 5 value rows; 3 GradientCoupledInstantonValue rows` and `3 records; 10 value rows; 3 GradientCoupledInstantonValue rows; committed …` | new (10b) |

`tests/test_inventory_report.py` gains two tests and one helper; its ten existing test functions, `_rec` and the
other helpers are unchanged (by `ast`):
- `_with_gradient_instantons()`: `_inventory()` and a `GradientCoupledInstanton` class of three records, built with
  `Record(...)` directly: δN★ 0.25 with 5 profile rows and `{"GradientCoupledInstantonValue": 3}`, δN★ 0.75 with 5
  and `{…: 0}`, δN★ 1.25 with 0 and `{…: 0}`, as 10b's store holds them.
- `test_a_further_value_table_is_counted_by_its_name`: the gradient section, whole, with and without `verbose`:
  the title, `3 records; 10 value rows; 3 GradientCoupledInstantonValue rows; committed 2026-10-21 10:19:00 –
  2026-10-21 10:20:30`, the common line, and the three record lines `| 5 value rows; 3 GradientCoupledInstantonValue
  rows`, `| 5 value rows; 0 GradientCoupledInstantonValue rows`, `| 0 value rows; 0 GradientCoupledInstantonValue
  rows`: a non-zero count and two 0s, asserted in the text.
- `test_a_class_with_no_further_value_table_prints_as_before`: in the same report, the trajectories' and the
  compaction function's sections line for line as 10's tests assert them, the full instantons' summary and first
  record line as 10's, and the table named on exactly four lines, all in the gradient section.

### X4 — the store (`tests/test_inventory_store.py`, `integration`, 4 tests, unchanged in number)

- **The third gradient instanton.** `_STORE_SCRIPT`'s `gradient()` takes `full=True` and calls
  `obj.set_store_full_values(full)` just before `pool.object_store(obj)`; `gradient(p_quadratic, dns[1], False,
  full=False)` is added between the two 10 wrote (successful at `dns[0]`, failed at `dns[2]`). The scalars-only row
  is made **by the flag alone**: its `_values` is populated exactly as the full one's (3 values), so the factory's
  `store` writes no value rows because `store_full_values` is false (`:580`), and `validate` expects 0 (`:620-621`);
  its profile rows are written unconditionally (`:594-605`). The script's own `assert
  ray.get(pool.object_validate(stored)) is True` holds for it (the store builds, `RESULT {"ok": true}`). A row with
  `_values = []` and full values on would also read `(True, 5, {…: 0})`; this one is the flag's.
- **`EXPECTED_COUNTS`**: `GradientCoupledInstanton` `(2, False)` → `(3, False)`; nothing else moves.
- **The read-back** (`test_the_store_reads_back_with_every_class_and_no_problem`): 10's
  `flags("GradientCoupledInstanton") == [(True, 0), (True, 5)]` is replaced by the gradient records keyed by their
  δN★ (resolved through `inventory.resolve`), each `(validated, value_count, extra_value_counts)`:
  `{0.5: (True, 5, {"GradientCoupledInstantonValue": 3}), 1.5: (True, 5, {…: 0}), 2.5: (True, 0, {…: 0})}`, beside
  10's `problems == ()` on the same read. Every other class's assertion is 10's.
- **The report test**: the two gradient literals move to the new format and the scalars-only line is added
  (`delta_Nstar=0.5 | 5 value rows; 3 GradientCoupledInstantonValue rows`, `1.5 | 5 …; 0 …`, `2.5 | 0 …; 0 …`), and
  the class summary is asserted to begin `3 records; 10 value rows; 3 GradientCoupledInstantonValue rows; committed `
  (brief correction 4: "the report … tests see the new counts", not a weakening). Every other literal stays (`| 3
  value rows` is `FullInstanton`'s; the five `committed` and five `@@ validated:` counts hold).
- **The two `main.py --inventory` tests** each gain one assertion that the printed text carries a gradient line with
  its count (`0.5 … 3 …` by default, `1.5 … 0 …` with `--show-all`). Their equality with the renderer's output is
  10's and unchanged; on its own it would pass whatever the renderer prints.
- The docstring says the store has the scalars-only gradient instanton and that each gradient record counts its
  `GradientCoupledInstantonValue` rows, and attributes them to 10b (brief correction 6).

### X5 — the records

`[gci-value-table-outside-the-inventory]` closed: board §3 → §4 with how, `.documents/OPEN-ISSUES.md` §6a → §7, its
header 60 → 59 open, 28 → 29 closed, 2026-10-22. The board's header, §1 row, X1–X5 and §5.27. Prose this commit makes
false: the spec's comment, the report's docstring, the store test's docstring and the `EXPECTED_SPECS` and `EXCLUDED`
comments, all corrected in place. `.claude/rules/pool-read-apis.md` says nothing of the table (checked) and is
unchanged.

## Deviations from the prompt

1. **The board section is §5.27**, after §5.26; the header's status line is updated to match (brief correction 1).
   `STRUCTURALLY REQUIRED`.
2. **§2.1.2's grep found 51 lines**, not only §1's (brief correction 3): almost all are the table used as a table or a
   class. Of those that say the table is outside the inventory or exclude it, there are exactly the three §1 names:
   the spec's comment (`:153-155` at `d590b30`), `EXCLUDED` (`tests/test_inventory_specs.py:209-212`) and the
   stale-exclusion literal (`:435-436`). None of the rest is a stop, and none is edited. `STRUCTURALLY REQUIRED`.
3. **The report literals of `test_the_report_shows_the_fields_of_today_s_report` changed** (the two gradient lines
   to the new format, the `1.5` line added) and the class summary asserted (brief correction 4). `STRUCTURALLY
   REQUIRED`.
4. **The report's format** (`| n value rows; m <table> rows`, the summary likewise; brief correction 5): the
   profile's count stays "value rows", as 10's, and the further table is named, so a reader can tell the two apart.
   `IMPLEMENTATION CHOICE`.
5. **The column test asserts it met every extra table `EXPECTED_SPECS` names**, beyond checking each one it meets
   (the brief's vacuous-pass list). `IMPLEMENTATION CHOICE`.
6. **The stale-exclusion case takes the class out of `READ_THROUGH`** for that case (the prompt's suggestion; brief
   correction 8). `IMPLEMENTATION CHOICE`.
7. **Two new report tests, not one**, and one helper building `Record(...)` directly; `_rec` is unchanged (brief
   correction 7). `IMPLEMENTATION CHOICE`.
8. **The gradient read-back is keyed by δN★**, replacing 10's `flags("GradientCoupledInstanton")` pair assertion
   with the triple of which the pair is a part, so that which record carries which count is asserted, not only the
   multiset. `IMPLEMENTATION CHOICE`.
9. **One assertion added to each `main.py --inventory` test** (the printed text carries the count), under the
   prompt's §1.4 last bullet. `IMPLEMENTATION CHOICE`.
10. **`ruff format` on the three test modules**, which 10 left formatted: it reflowed only lines this commit adds;
    the store test's δN★ lookup is a small nested function so that it formats readably. `tools/inventory_report.py`
    was already formatted as edited. `IMPLEMENTATION CHOICE`.
11. **Breakage 4 removes both of the report's extra prints** (the record lines' and the summary's), the prompt's
    "no longer prints the extra count". `IMPLEMENTATION CHOICE`.
12. **Docstrings and comments corrected in place** (brief correction 6): the factory's spec comment, the report's
    module docstring and `_counts_text`'s, the store test's docstring, the `EXPECTED_SPECS` and `EXCLUDED` comments.
    `tests/test_inventory_specs.py`'s and `tests/test_inventory_report.py`'s module docstrings stay true and are
    unchanged. `STRUCTURALLY REQUIRED`.
13. No `UNINTENDED DRIFT`: every test passed the first time it was run as committed; no existing test outside the
    three modules failed.

## Verification performed

### §2.1 — before

- `HEAD` `d590b30fb78412e4fa50db621b0525b809bd1349`; `git status --short` empty; 20:05 BST, load 25.99 22.91 19.73
  (10 CPUs). `RAY_ADDRESS` unset; no `gcs_server`, `raylet`, `ray::`, `pytest` or `main.py` process;
  `ray_cluster.sh status`: lock free, no processes on `/tmp/ray-si`, the four ports free. `pip freeze` 83 lines,
  `datastorekit @ …@f47b9a255e9ad58e0d0eaf85644f53b575884d31`.
- **The suites at the gate**, serially, in the foreground, each to a file in the scratch directory:

  | Run | Result | Time | Load before; after |
  |---|---|---|---|
  | `./venv/bin/python -m pytest -m "not integration and not slow" -q -p no:cacheprovider` | **730: 729 passed, 1 skipped** (136 deselected) | 45.0 s | 25.59; 25.68 |
  | `RAY_ADDRESS=local ./venv/bin/python -m pytest -m integration -q -p no:cacheprovider` | **67: 66 passed, 1 skipped** (799 deselected) | 56.1 s | 24.88; 91.61 |

  10a's counts.
- **§2.1.2, the grep** (`git grep -n "gci-value-table-outside-the-inventory\|outside the inventory\|GradientCoupledInstantonValue"`
  outside `.prompts/` and `.documents/`): 51 lines in 19 files (the factory 14, `ComputeTargets/…/GradientCoupledInstanton.py`
  6, `config/datastore.py` 4, `tests/test_config_datastore.py` 4, `tests/test_inventory_specs.py` 4, eight other tests
  1–2 each, `config/sharding.py`, `config/argument_parser.py`, `plotting/adapters/gradient.py`, `tools/compare_stores.py`,
  `.claude/rules/populate-ordering.md`, `.claude/rules/validate-on-startup.md` 1 each). The lines that say the table is
  outside the inventory or exclude it: `GradientCoupledInstanton.py:154-155`, `tests/test_inventory_specs.py:209-212`
  and `:435-436` (deviation 2).
- **§1.4's precondition, read before writing the store change:** `store` writes value rows only `if
  store_full_values` (`GradientCoupledInstanton.py:580-592`), the profile rows unconditionally (`:594-605`), and
  `validate` expects `0 if not store_full_values else len(obj._values)` value rows (`:620-621`). So a scalars-only row
  validates and writes its profile; the build confirmed it (the script asserts `object_validate` is `True` for every
  row, and exits `RESULT {"ok": true}`).

### U5, at the gate and after (§2.1.3)

`u5.py` (scratch, run with `./venv/bin/python -I`, SI's root appended to `sys.path`) records, for all 31 non-empty
sets of the five drop groups, `dependent_tables(tables, factories)`, `tables_to_drop`'s decision and its message, as
JSON; it also prints where `datastorekit` was imported from and the GCI spec's `extra_values` and `dependencies()`.

| | GCI `extra_values` | Sets | Closed | Refused | Equal to the gate's (deps, decision, message) |
|---|---|---|---|---|---|
| gate (`u5-before.json`) | `{}` | 31 | 10 | 21 | — |
| after (`u5-after.json`) | `{'GradientCoupledInstantonValue': 'instanton_serial'}` | 31 | 10 | 21 | **31 of 31** (the two files byte-equal) |

`datastorekit` from `venv/lib/python3.13/site-packages/datastorekit/`. The spec's `dependencies()`, both runs:
`CosmologicalParams`, `InflatonTrajectory`, `MasslessDecoupledDiffusion`, `N_final`, `N_init`,
`alpha_regularization`, `delta_Nstar`, `n_collocation_points`, `tolerance`: no value table, as `extra_values` does not
enter it (README §0.6). The closed sets: `compaction-function` alone; `gradient-coupled-instanton` alone;
`compaction-function` with any non-empty set of `full-instanton`, `slow-roll-instanton` and
`gradient-coupled-instanton` (7); all five. **U5 does not move.**

### §2.3.1 — the suites

Serially, in the foreground, on the finished tree (after the breakages were reverted), each to a file in the scratch
directory. No `slow` run: the diff touches no file under `ComputeTargets/`, `Numerics/`, `Interpolation/` or
`tools/diagnostics/` (`.claude/rules/test-selection.md`).

| Suite | Gate (10a's) | Now | Time | Load before; after |
|---|---|---|---|---|
| default, `-m "not integration and not slow"` | 730 (729 passed, 1 skipped) | **732 (731 passed, 1 skipped)**, 136 deselected | 36.0 s | 16.19; 23.79 |
| integration, `RAY_ADDRESS=local … -m integration` | 67 (66 passed, 1 skipped) | **67 (66 passed, 1 skipped)**, 801 deselected | 68.1 s | 23.79; 103.07 |

**By module** (`--collect-only -q`, compared with the orchestrator's by-module lists at the gate; every module not
listed has the same count):

| Module | At the gate | Now | Why |
|---|---|---|---|
| `tests/test_inventory_specs.py` (default) | 12 | 12 | changed in place (X2) |
| `tests/test_inventory_report.py` (default) | 10 | **12** | + `test_a_further_value_table_is_counted_by_its_name`, + `test_a_class_with_no_further_value_table_prints_as_before` (X3) |
| **default total** | **730** | **732** | 730 + 2 |
| `tests/test_inventory_store.py` (integration) | 4 | 4 | changed in place (X4) |
| **integration total** | **67** | **67** | unchanged |

The integration run's deselected count is 801, 799 + the two new default tests. No Ray process after either run. No
test failed at any point, so nothing was re-run alone.

### §2.3.2 — by running it

The store: built by the integration test's own `_STORE_SCRIPT`, imported from `tests.test_inventory_store` and run
unchanged by `fp.py` (below) in a subprocess (`ray.init(address="local")`), under `<scratch>/store/` (`<scratch>` is
`/private/tmp/claude-35086/-Users-ds283-Documents-Code-StochasticInstantons/b01c44a6-3957-4b2b-851b-229569464b51/scratchpad/agent10b`):
exit 0, `RESULT {"ok": true}`. Then, with no Ray:

```bash
RAY_ADDRESS=127.0.0.1:9 timeout 120 ./venv/bin/python main.py --database <scratch>/store/inventory.sqlite --ray-address 127.0.0.1:9 --inventory
RAY_ADDRESS=127.0.0.1:9 timeout 120 ./venv/bin/python main.py --database <scratch>/store/inventory.sqlite --ray-address 127.0.0.1:9 --inventory --show-all
```

Both exit 0, stderr empty; the three files' SHA-256 are the same before and after; no Ray process after. The two
outputs, whole:

**Default:**

```text
>> packages: datastorekit 0.5.0 (https://github.com/ds283/DatastoreKit@f47b9a255e9ad58e0d0eaf85644f53b575884d31, requested v0.5.0); raypoolkit 0.2.0 (https://github.com/ds283/RayPoolKit@eaef0ce60e2fc354bb32f0ad576010e6a83c1976, requested v0.2.0)
@@ DATASTORE INVENTORY: /private/tmp/claude-35086/-Users-ds283-Documents-Code-StochasticInstantons/b01c44a6-3957-4b2b-851b-229569464b51/scratchpad/agent10b/store/inventory.sqlite
   read-only; 2 shards (#0, #1); 59 records in 24 classes
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
      3 records; 50 value rows; committed 2026-10-22 20:12:40 – 2026-10-22 20:12:40
      common to every record: pi0=-0.1 PlanckMass, atol=1e-08, rtol=1e-06
      @@ validated: 3 record(s)
         :: phi0=15 PlanckMass, potential=QuadraticPotential(m=1e-05 PlanckMass) | 25 value rows
         :: phi0=15 PlanckMass, potential=QuarticPotential(lambda_=1e-13) | 25 value rows
         :: phi0=16 PlanckMass, potential=QuadraticPotential(m=1e-05 PlanckMass) | 0 value rows
      @@ unvalidated: 0 record(s)

   -- Full MSR instantons (FullInstanton, sharded)
      3 records; 6 value rows; committed 2026-10-22 20:12:41 – 2026-10-22 20:12:41
      common to every record: N_init=20, N_final=5, diffusion_model=MasslessDecoupledDiffusion, atol=1e-08, rtol=1e-06
      @@ validated: 3 record(s)
         :: delta_Nstar=0.5, trajectory=InflatonTrajectory(phi0=15 PlanckMass, potential=QuadraticPotential(m=1e-05 PlanckMass)) | 3 value rows
         :: delta_Nstar=1.5, trajectory=InflatonTrajectory(phi0=15 PlanckMass, potential=QuarticPotential(lambda_=1e-13)) | 3 value rows
         :: delta_Nstar=2.5, trajectory=InflatonTrajectory(phi0=15 PlanckMass, potential=QuadraticPotential(m=1e-05 PlanckMass)) | 0 value rows
      @@ unvalidated: 0 record(s)

   -- Slow-roll instantons (SlowRollInstanton, sharded)
      3 records; 6 value rows; committed 2026-10-22 20:12:41 – 2026-10-22 20:12:41
      common to every record: N_init=20, N_final=5, diffusion_model=MasslessDecoupledDiffusion, atol=1e-08, rtol=1e-06
      @@ validated: 3 record(s)
         :: delta_Nstar=0.5, trajectory=InflatonTrajectory(phi0=15 PlanckMass, potential=QuadraticPotential(m=1e-05 PlanckMass)) | 3 value rows
         :: delta_Nstar=1.5, trajectory=InflatonTrajectory(phi0=15 PlanckMass, potential=QuarticPotential(lambda_=1e-13)) | 3 value rows
         :: delta_Nstar=2.5, trajectory=InflatonTrajectory(phi0=15 PlanckMass, potential=QuadraticPotential(m=1e-05 PlanckMass)) | 0 value rows
      @@ unvalidated: 0 record(s)

   -- Compaction functions (CompactionFunction, sharded)
      3 records; 12 value rows; committed 2026-10-22 20:12:41 – 2026-10-22 20:12:41
      common to every record: cosmo=Planck2018 68% central values TT+TE+EE+lowP+lensing+BAO, atol=1e-08, rtol=1e-06
      @@ validated: 2 record(s)
         :: delta_Nstar=0.5, trajectory=InflatonTrajectory(phi0=15 PlanckMass, potential=QuadraticPotential(m=1e-05 PlanckMass)), full_instanton=FullInstanton(delta_Nstar=0.5, trajectory=InflatonTrajectory(phi0=15 PlanckMass, potential=QuadraticPotential(m=1e-05 PlanckMass))), slow_roll_instanton=SlowRollInstanton(delta_Nstar=0.5, trajectory=InflatonTrajectory(phi0=15 PlanckMass, potential=QuadraticPotential(m=1e-05 PlanckMass))) | 8 value rows
         :: delta_Nstar=2.5, trajectory=InflatonTrajectory(phi0=15 PlanckMass, potential=QuadraticPotential(m=1e-05 PlanckMass)), full_instanton=FullInstanton(delta_Nstar=2.5, trajectory=InflatonTrajectory(phi0=15 PlanckMass, potential=QuadraticPotential(m=1e-05 PlanckMass))), slow_roll_instanton=SlowRollInstanton(delta_Nstar=2.5, trajectory=InflatonTrajectory(phi0=15 PlanckMass, potential=QuadraticPotential(m=1e-05 PlanckMass))) | 0 value rows
      @@ unvalidated: 1 record(s)
         :: delta_Nstar=1.5, trajectory=InflatonTrajectory(phi0=15 PlanckMass, potential=QuarticPotential(lambda_=1e-13)), full_instanton=FullInstanton(delta_Nstar=1.5, trajectory=InflatonTrajectory(phi0=15 PlanckMass, potential=QuarticPotential(lambda_=1e-13))), slow_roll_instanton=none | 4 value rows

   -- Gradient-coupled (onion model) instantons (GradientCoupledInstanton, sharded)
      3 records; 10 value rows; 3 GradientCoupledInstantonValue rows; committed 2026-10-22 20:12:41 – 2026-10-22 20:12:41
      common to every record: N_init=20, N_final=5, n_collocation_points=5, alpha_regularization=0.01, trajectory=InflatonTrajectory(phi0=15 PlanckMass, potential=QuadraticPotential(m=1e-05 PlanckMass)), cosmo=Planck2018 68% central values TT+TE+EE+lowP+lensing+BAO, diffusion_model=MasslessDecoupledDiffusion, atol=1e-08, rtol=1e-06
      @@ validated: 3 record(s)
         :: delta_Nstar=0.5 | 5 value rows; 3 GradientCoupledInstantonValue rows
         :: delta_Nstar=1.5 | 5 value rows; 0 GradientCoupledInstantonValue rows
         :: delta_Nstar=2.5 | 0 value rows; 0 GradientCoupledInstantonValue rows
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
>> packages: datastorekit 0.5.0 (https://github.com/ds283/DatastoreKit@f47b9a255e9ad58e0d0eaf85644f53b575884d31, requested v0.5.0); raypoolkit 0.2.0 (https://github.com/ds283/RayPoolKit@eaef0ce60e2fc354bb32f0ad576010e6a83c1976, requested v0.2.0)
@@ DATASTORE INVENTORY: /private/tmp/claude-35086/-Users-ds283-Documents-Code-StochasticInstantons/b01c44a6-3957-4b2b-851b-229569464b51/scratchpad/agent10b/store/inventory.sqlite
   read-only; 2 shards (#0, #1); 59 records in 24 classes
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
      3 records; 50 value rows; committed 2026-10-22 20:12:40 – 2026-10-22 20:12:40
      common to every record: pi0=-0.1 PlanckMass, atol=1e-08, rtol=1e-06
      @@ validated: 3 record(s)
         :: phi0=15 PlanckMass, potential=QuadraticPotential(m=1e-05 PlanckMass) | 25 value rows
         :: phi0=15 PlanckMass, potential=QuarticPotential(lambda_=1e-13) | 25 value rows
         :: phi0=16 PlanckMass, potential=QuadraticPotential(m=1e-05 PlanckMass) | 0 value rows
      @@ unvalidated: 0 record(s)

   -- Full MSR instantons (FullInstanton, sharded)
      3 records; 6 value rows; committed 2026-10-22 20:12:41 – 2026-10-22 20:12:41
      common to every record: N_init=20, N_final=5, diffusion_model=MasslessDecoupledDiffusion, atol=1e-08, rtol=1e-06
      @@ validated: 3 record(s)
         :: delta_Nstar=0.5, trajectory=InflatonTrajectory(phi0=15 PlanckMass, potential=QuadraticPotential(m=1e-05 PlanckMass)) | 3 value rows
         :: delta_Nstar=1.5, trajectory=InflatonTrajectory(phi0=15 PlanckMass, potential=QuarticPotential(lambda_=1e-13)) | 3 value rows
         :: delta_Nstar=2.5, trajectory=InflatonTrajectory(phi0=15 PlanckMass, potential=QuadraticPotential(m=1e-05 PlanckMass)) | 0 value rows
      @@ unvalidated: 0 record(s)

   -- Slow-roll instantons (SlowRollInstanton, sharded)
      3 records; 6 value rows; committed 2026-10-22 20:12:41 – 2026-10-22 20:12:41
      common to every record: N_init=20, N_final=5, diffusion_model=MasslessDecoupledDiffusion, atol=1e-08, rtol=1e-06
      @@ validated: 3 record(s)
         :: delta_Nstar=0.5, trajectory=InflatonTrajectory(phi0=15 PlanckMass, potential=QuadraticPotential(m=1e-05 PlanckMass)) | 3 value rows
         :: delta_Nstar=1.5, trajectory=InflatonTrajectory(phi0=15 PlanckMass, potential=QuarticPotential(lambda_=1e-13)) | 3 value rows
         :: delta_Nstar=2.5, trajectory=InflatonTrajectory(phi0=15 PlanckMass, potential=QuadraticPotential(m=1e-05 PlanckMass)) | 0 value rows
      @@ unvalidated: 0 record(s)

   -- Compaction functions (CompactionFunction, sharded)
      3 records; 12 value rows; committed 2026-10-22 20:12:41 – 2026-10-22 20:12:41
      common to every record: cosmo=Planck2018 68% central values TT+TE+EE+lowP+lensing+BAO, atol=1e-08, rtol=1e-06
      @@ validated: 2 record(s)
         :: delta_Nstar=0.5, trajectory=InflatonTrajectory(phi0=15 PlanckMass, potential=QuadraticPotential(m=1e-05 PlanckMass)), full_instanton=FullInstanton(delta_Nstar=0.5, trajectory=InflatonTrajectory(phi0=15 PlanckMass, potential=QuadraticPotential(m=1e-05 PlanckMass))), slow_roll_instanton=SlowRollInstanton(delta_Nstar=0.5, trajectory=InflatonTrajectory(phi0=15 PlanckMass, potential=QuadraticPotential(m=1e-05 PlanckMass))) | 8 value rows
         :: delta_Nstar=2.5, trajectory=InflatonTrajectory(phi0=15 PlanckMass, potential=QuadraticPotential(m=1e-05 PlanckMass)), full_instanton=FullInstanton(delta_Nstar=2.5, trajectory=InflatonTrajectory(phi0=15 PlanckMass, potential=QuadraticPotential(m=1e-05 PlanckMass))), slow_roll_instanton=SlowRollInstanton(delta_Nstar=2.5, trajectory=InflatonTrajectory(phi0=15 PlanckMass, potential=QuadraticPotential(m=1e-05 PlanckMass))) | 0 value rows
      @@ unvalidated: 1 record(s)
         :: delta_Nstar=1.5, trajectory=InflatonTrajectory(phi0=15 PlanckMass, potential=QuarticPotential(lambda_=1e-13)), full_instanton=FullInstanton(delta_Nstar=1.5, trajectory=InflatonTrajectory(phi0=15 PlanckMass, potential=QuarticPotential(lambda_=1e-13))), slow_roll_instanton=none | 4 value rows

   -- Gradient-coupled (onion model) instantons (GradientCoupledInstanton, sharded)
      3 records; 10 value rows; 3 GradientCoupledInstantonValue rows; committed 2026-10-22 20:12:41 – 2026-10-22 20:12:41
      common to every record: N_init=20, N_final=5, n_collocation_points=5, alpha_regularization=0.01, trajectory=InflatonTrajectory(phi0=15 PlanckMass, potential=QuadraticPotential(m=1e-05 PlanckMass)), cosmo=Planck2018 68% central values TT+TE+EE+lowP+lensing+BAO, diffusion_model=MasslessDecoupledDiffusion, atol=1e-08, rtol=1e-06
      @@ validated: 3 record(s)
         :: delta_Nstar=0.5 | 5 value rows; 3 GradientCoupledInstantonValue rows
         :: delta_Nstar=1.5 | 5 value rows; 0 GradientCoupledInstantonValue rows
         :: delta_Nstar=2.5 | 0 value rows; 0 GradientCoupledInstantonValue rows
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

### §2.3.3 — the fingerprint, compared, not recorded

`fp.py` (scratch), run as `RAY_ADDRESS=local ./venv/bin/python -I fp.py <scratch>` from SI's root: it asserts that
`datastorekit` is imported from the venv's `site-packages`, builds the store above if absent, and reads it with
`read_inventory` twice, **without** the declaration (the registry entry's `inventory_spec` wrapped on the instance,
in memory, as `dataclasses.replace(<the tree's spec>, extra_values={})`) and **with** it (the wrapper removed: the
tree's spec), printing the spec's `extra_values` in each case, the problems, the gradient records and
`fingerprint_of(inventory, 1)`'s overall and `GradientCoupledInstanton` digests, then which of the 24 class digests
differ. Nothing is written but `fp.json` in the scratch directory. Its output (the per-class `counts:` lines, which
are 10's `EXPECTED_COUNTS` with `GradientCoupledInstanton` 3, left out):

```text
datastorekit.store_inventory from /Users/ds283/Documents/Code/StochasticInstantons/venv/lib/python3.13/site-packages/datastorekit/store_inventory.py
datastorekit.store_fingerprint from /Users/ds283/Documents/Code/StochasticInstantons/venv/lib/python3.13/site-packages/datastorekit/store_fingerprint.py
store build: exit 0 ['RESULT {"ok": true}']
--- without the declaration: GCI extra_values = {}
problems: ()
GCI record: delta_Nstar=0.5 -> (True, 5, {})
GCI record: delta_Nstar=1.5 -> (True, 5, {})
GCI record: delta_Nstar=2.5 -> (True, 0, {})
fingerprint digest: ffac93337770ed6b71659505d6ddd118e730c8438038b0ecce0f554100948658
GradientCoupledInstanton class digest: 5b88f64ce9dc59ee91a1cf49362d565ac6db316231a349365804e2945dc9ef74
--- with the declaration: GCI extra_values = {'GradientCoupledInstantonValue': 'instanton_serial'}
problems: ()
GCI record: delta_Nstar=0.5 -> (True, 5, {'GradientCoupledInstantonValue': 3})
GCI record: delta_Nstar=1.5 -> (True, 5, {'GradientCoupledInstantonValue': 0})
GCI record: delta_Nstar=2.5 -> (True, 0, {'GradientCoupledInstantonValue': 0})
fingerprint digest: e3437a9b2f16415f5635ee121fa7f09d07ac74c30400d5973a3afaeec8fc7c78
GradientCoupledInstanton class digest: e342c0aa9bd8dd8348a68bd14d591b37528c9f4cdd19c7b9c773937bb02412ec
class digests that differ: ['GradientCoupledInstanton'], 1 of 24
ray.is_initialized(): False
```

| | Overall digest | `GradientCoupledInstanton` class digest |
|---|---|---|
| without the declaration | `ffac93337770ed6b71659505d6ddd118e730c8438038b0ecce0f554100948658` | `5b88f64ce9dc59ee91a1cf49362d565ac6db316231a349365804e2945dc9ef74` |
| with the declaration | `e3437a9b2f16415f5635ee121fa7f09d07ac74c30400d5973a3afaeec8fc7c78` | `e342c0aa9bd8dd8348a68bd14d591b37528c9f4cdd19c7b9c773937bb02412ec` |

**1 of 24 class digests differs**, `GradientCoupledInstanton`'s; the other 23 are equal. All four digests equal the
orchestrator's prototype's (brief correction 9), from an independent build of the same store: they hang on identity,
not on timestamps or serials. SI records no fingerprint (README §7).

### §2.3.4 — `ruff check --select F401,F811,F821`

On the five Python files the diff touches, each at the gate (`git show HEAD:<file> | ruff check --stdin-filename
<file> -`) and now: **0 findings at the gate, 0 now**, in each. `ruff format --check` passes on
`tools/inventory_report.py` and the three test modules.

## The deliberate-breakage record

Each diff was applied with `git apply` to the working tree that this commit records, the named tests run, and
reverted with `git apply -R`; after all five, `git diff` and `git status --short` were byte-identical to those saved
before the first. Each is recorded as `diff -u` labelled `a/` and `b/`, so that `git apply` replays it from a clean
tree at this commit (`git apply --check` and `-R --check` after the commit: State handed to the next prompt).

### Breakage 1 — `extra_values` removed from the spec

```diff
--- a/Datastore/SQL/ObjectFactories/GradientCoupledInstanton.py
+++ b/Datastore/SQL/ObjectFactories/GradientCoupledInstanton.py
@@ -178,7 +178,6 @@
                 "cosmo": Parent("cosmo_serial", of="CosmologicalParams"),
             },
             values=("GradientCoupledInstantonProfile", "parent_serial"),
-            extra_values={"GradientCoupledInstantonValue": "instanton_serial"},
             validated="validated",
         )
 
```

Caught. `pytest tests/test_inventory_specs.py`: 7 failed, 5 passed. `test_each_spec_is_the_identity_its_build_matches`:
`AssertionError: GradientCoupledInstanton … At index 4 diff: {} != {'GradientCoupledInstantonValue':
'instanton_serial'}`; `test_every_named_column_is_a_column_of_its_table`: `assert {} == {'GradientCoupledInstanton':
['GradientCoupledInstantonValue']}`; `test_every_registered_class_is_placed_exactly_once` (coverage): `Left contains
one more item: "GradientCoupledInstantonValue: GradientCoupledInstanton's spec does not name it in extra_values"`; the
four coverage tests that compare against a registry's own failures meet the same line.

### Breakage 2 — the column misnamed (`instanton_serail`)

```diff
--- a/Datastore/SQL/ObjectFactories/GradientCoupledInstanton.py
+++ b/Datastore/SQL/ObjectFactories/GradientCoupledInstanton.py
@@ -178,7 +178,7 @@
                 "cosmo": Parent("cosmo_serial", of="CosmologicalParams"),
             },
             values=("GradientCoupledInstantonProfile", "parent_serial"),
-            extra_values={"GradientCoupledInstantonValue": "instanton_serial"},
+            extra_values={"GradientCoupledInstantonValue": "instanton_serail"},
             validated="validated",
         )
 
```

Caught. 2 failed, 10 passed. `test_every_named_column_is_a_column_of_its_table`: `AssertionError:
GradientCoupledInstanton: extra_values GradientCoupledInstantonValue.instanton_serail` (`assert 'instanton_serail' in
<…>.c`); and the identity test, `At index 4 diff: {'GradientCoupledInstantonValue': 'instanton_serail'} != {…:
'instanton_serial'}`.

### Breakage 3 — `GradientCoupledInstantonProfile` named in both `values` and `extra_values`

```diff
--- a/Datastore/SQL/ObjectFactories/GradientCoupledInstanton.py
+++ b/Datastore/SQL/ObjectFactories/GradientCoupledInstanton.py
@@ -178,7 +178,10 @@
                 "cosmo": Parent("cosmo_serial", of="CosmologicalParams"),
             },
             values=("GradientCoupledInstantonProfile", "parent_serial"),
-            extra_values={"GradientCoupledInstantonValue": "instanton_serial"},
+            extra_values={
+                "GradientCoupledInstantonValue": "instanton_serial",
+                "GradientCoupledInstantonProfile": "parent_serial",
+            },
             validated="validated",
         )
 
```

Caught. 3 failed, 9 passed. `test_inventory_classes_accepts_the_registry_and_orders_it` meets the package's refusal:
`ValueError: inventory_classes(): GradientCoupledInstanton names GradientCoupledInstantonProfile both as its value
table and in its extra_values`; the identity and column tests fail too.

### Breakage 4 — the report no longer prints the extra count

```diff
--- a/tools/inventory_report.py
+++ b/tools/inventory_report.py
@@ -372,8 +372,6 @@
     counts = []
     if value_count is not None:
         counts.append(_plural(value_count, "value row"))
-    for table in sorted(extra_value_counts):
-        counts.append(_plural(extra_value_counts[table], f"{table} row"))
     return "; ".join(counts)
 
 
@@ -420,10 +418,6 @@
     if any(r.value_count is not None for r in cls.records):
         total = sum(r.value_count or 0 for r in cls.records)
         summary.append(_plural(total, "value row"))
-    # each further value table's rows, by the table's name (prompt 10b)
-    for table in sorted({t for r in cls.records for t in r.extra_value_counts}):
-        total = sum(r.extra_value_counts.get(table, 0) for r in cls.records)
-        summary.append(_plural(total, f"{table} row"))
     if cls.earliest_timestamp is not None:
         summary.append(
             f"committed {_timestamp(cls.earliest_timestamp)} – {_timestamp(cls.latest_timestamp)}"
```

Caught. `pytest tests/test_inventory_report.py`: 2 failed, 10 passed. `test_a_further_value_table_is_counted_by_its_name`:
`At index 1 diff: '      3 records; 10 value rows; committed 2026-10-21 10:19:00 – 2026-10-21 10:20:30' != '      3
records; 10 value rows; 3 GradientCoupledInstantonValue rows; committed 2026-10-21 10:19:00 – 2026-10-21 10:20:30'`;
`test_a_class_with_no_further_value_table_prints_as_before`: `assert 0 == 4` (the table named on no line). The ten
existing report tests pass, as they should: none renders a class with a further table.

### Breakage 5 — `GradientCoupledInstantonValue` put back into `EXCLUDED` as well

```diff
--- a/tests/test_inventory_specs.py
+++ b/tests/test_inventory_specs.py
@@ -214,7 +214,9 @@
 
 # N5: the registered classes that are in no spec, each with a one-line reason. None since prompt
 # 10b, which reads GradientCoupledInstantonValue through its owner's extra_values
-EXCLUDED: Dict[str, str] = {}
+EXCLUDED: Dict[str, str] = {
+    "GradientCoupledInstantonValue": "written only when store_full_values is set",
+}
 
 SLOTS = ("tags", "values", "parent_sets", "extra_values")
 
```

Caught. `pytest tests/test_inventory_specs.py`: 5 failed, 7 passed. `test_every_registered_class_is_placed_exactly_once`:
`Left contains one more item: "GradientCoupledInstantonValue: in more than one place (read through an owner's spec,
excluded)"`; the other four coverage tests, which build on `EXCLUDED`, meet the same line.

## Observations not acted on

- **A store with no gradient rows prints and fingerprints as before.** With no records, `_compute_lines` prints `0
  records` and names no further table (the summary's tables are those its records carry), and a class with no records
  has no record line to carry `extra_value_counts`. Read from the code; not run on such a store.
- **A spec with `extra_values` but no `values`** would print its record lines as `| m <table> rows` alone; SI has
  none, and no test renders one.
- **`tests/test_inventory_report.py`'s module docstring** lists the fields of today's report; it says nothing false,
  but does not name the further tables' counts, which two tests now assert. Left (brief correction 6: only if false).
- **DatastoreKit's advice for a spec guard** (its SI addendum, "What of SI's own moves"): a RunRegistryKit spec guard
  should leave out an `extra_values` whose value is empty. For the RunRegistryKit adoption after this campaign
  (README §7), not 10b's.

## State handed to the next prompt

- **Branch** `dk-and-rpk-migration`, this commit on `d590b30`. Changed: `Datastore/SQL/ObjectFactories/GradientCoupledInstanton.py`
  (the spec's keyword and comment), `tools/inventory_report.py`, `tests/test_inventory_specs.py`,
  `tests/test_inventory_report.py`, `tests/test_inventory_store.py`, the board, `.documents/OPEN-ISSUES.md`. New:
  this note.
- **The inventory.** `read_inventory(primary, config.datastore.factories)` reads the 24 classes in 10's order; every
  registered class is covered: 24 specs, 6 read through (`InflatonTrajectoryValue`, `FullInstantonValue`,
  `SlowRollInstantonValue`, `CompactionFunctionSamples`, `GradientCoupledInstantonProfile` by `values`;
  `GradientCoupledInstantonValue` by `GradientCoupledInstanton`'s `extra_values`), **none excluded**. Each
  `GradientCoupledInstanton` record carries `extra_value_counts == {"GradientCoupledInstantonValue": n}`, 0 for a row
  stored without full values; an orphan row of that table is an `orphan-value` problem. Every other class's records are
  10's.
- **For 11.** The inventory now counts `GradientCoupledInstantonValue`, which RH2's stores do not hold (U11: no
  gradient rows), so its `--inventory` output differs from 10's only where a gradient row would be: a store with no
  gradient rows prints the gradient section as `0 records`, `@@ validated: 0 record(s)`, `@@ unvalidated: 0
  record(s)`, as 10's report did. A clean RH2 store should still print `problems: none`. The suites start from **732
  (731 passed, 1 skipped)** and **67 (66 passed, 1 skipped)**; `slow` from S1's 69, not run here.
- **For the RunRegistryKit adoption (README §7).** Only `GradientCoupledInstanton`'s class digest moves with the
  declaration (1 of 24, on the integration test's store); SI records no fingerprint and has no `fingerprint_format`.
- **The venv** is untouched (nothing installed). No Ray cluster is up; the rehearsal lock is untouched. The only stores
  opened were temporary ones: the tests' (under `tempfile`) and the scratch store `<scratch>/store/` (built through the
  package's pool under a private Ray, read by `read_inventory` and `main.py --inventory`). DatastoreKit, RayPoolKit,
  ChamPBH and SGK are untouched (read only).
- **Closed:** `[gci-value-table-outside-the-inventory]` (board §4; `.documents/OPEN-ISSUES.md` §7). **Opened:** none.
  59 open, 29 closed. The README and `.prompts/INDEX.md` are the orchestrator's.
- **Rollback:** `git revert` of this commit alone; nothing in the venv (README §4.4).
