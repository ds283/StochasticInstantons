# Prompt 10b — count the gradient instanton's value table

**Campaign:** [`README.md`](README.md) · **Board items:** **X1**–**X5** ·
**Board:** [`IMPLEMENTATION_STATE.md`](IMPLEMENTATION_STATE.md)
**Written:** 2026-10-22, with prompt 10a, after 10's review and the user's ruling **U12** (README
§6.1; board §5.25). Measured at `f5f395b`, whose code is 10's (`e2c7b22`); 10a changes only
`requirements.txt`, so the lines cited here hold at 10a's commit too.
**Gate:**
- 10a landed and reviewed (board §1): `datastorekit` `0.5.0` at `f47b9a255e9a…` installed, not
  editable; the suites at 10's counts, 730 and 67;
- on branch `dk-and-rpk-migration`, no tracked change in `git status`;
- no SI cluster is up, and no other session runs a suite or a Ray job from this venv while 10b
  runs.

**Closes:** `[gci-value-table-outside-the-inventory]` (board §3; its owner). **Opens:** only what the
work finds.
**Recommended model:** **Opus**. The declaration is one keyword; the work is in the tests, which
must see it and must not pass without it.

**Read first:**

1. `CLAUDE.md`, and `.claude/rules/test-selection.md`.
2. [`README.md`](README.md): §0.6 (`v0.5.0`, U12), §2.2 (10b's charter), §5 (rules 4, 7, 8, 10).
3. **Prompt 10 and its results note**, `.documents/dk-and-rpk-migration/10-port-the-inventory.md`:
   the spec table, the coverage placement, the report, the three test modules and the breakages.
   10b extends 10's work; its tests are 10's, changed as §1 names.
4. DatastoreKit's SI checklist, **"Addendum: v0.5.0"** (`docs/adoption/stochasticinstantons.md` in
   `/Users/ds283/Documents/Code/DatastoreKit`), in full: "What SI declares, and where", "What then
   holds" and "What of SI's own moves" are this prompt's map. Contract §9.8. `store_inventory.py` at
   `v0.5.0` (`git -C … show v0.5.0:datastorekit/store_inventory.py`): `InventorySpec.extra_values`,
   `Record.extra_value_counts`, `read_records`' `_count_values`, `inventory_classes`' new refusal.
   **Read; edit nothing there.**
5. The brief SI sent, [`datastorekit-second-value-table-brief.md`](datastorekit-second-value-table-brief.md),
   and where the release departs from it (the addendum's last section): the mapping is keyed by
   **table name**, `extra_values={table: column}`, and the count is read as
   `record.extra_value_counts[table]`.

---

## 0. What this prompt is

10 gave `GradientCoupledInstanton`'s one `values` slot to `GradientCoupledInstantonProfile`, written
for every row, and excluded `GradientCoupledInstantonValue`, written only with full values, so that
no inventory or fingerprint could see it (`[gci-value-table-outside-the-inventory]`). `v0.5.0`,
pinned by 10a, lets a spec count further value tables. 10b declares the second table, and makes
every test, the report and the coverage see it. Then all 30 registered classes are covered and none
is excluded.

SI has recorded no fingerprint, so nothing it holds moves; it has no `fingerprint_format` yet
(RunRegistryKit is adopted after this campaign, README §7). Only `GradientCoupledInstanton`'s records
change: they gain `extra_value_counts`. Every other class's records are byte-identical to 10's
(the release's compatibility property, measured by the orchestrator; README §0.6).

---

## 1. What is wanted

### 1.1 The declaration (X1)

In `Datastore/SQL/ObjectFactories/GradientCoupledInstanton.py`'s `inventory_spec` (`:147-182` at
`e2c7b22`), beside `values=("GradientCoupledInstantonProfile", "parent_serial")` (`:180`), one
keyword:

```python
extra_values={"GradientCoupledInstantonValue": "instanton_serial"},
```

`instanton_serial` is the value table's foreign key to `GradientCoupledInstanton.serial` (`:686-692`).
The spec's comment (`:148-155`) is made true: the value table is counted, as a further value table,
0 for a row stored without full values. **Nothing else in the factory changes**; the review compares
it by `ast` with the spec set aside.

### 1.2 The spec and coverage tests (X2)

`tests/test_inventory_specs.py`, 10's, changed as follows and no further (README §5 rule 7, named
exception for 10b):
- **`EXPECTED_SPECS` and `_as_table`** (`:105-…`, `:283-297`): the table form gains the spec's
  `extra_values`, `{}` for every class but `GradientCoupledInstanton`, whose entry names the table
  and column above. `test_each_spec_is_the_identity_its_build_matches` then fails if the keyword is
  removed or changed (breakage 1).
- **The column test** (`test_every_named_column_is_a_column_of_its_table`, `:335-358`): each extra
  table exists, its column is in it, and that column is a foreign key to the owner, as `values`' is
  checked (`:351-358`).
- **Coverage**: `GradientCoupledInstantonValue` leaves `EXCLUDED` (`:208-214`) for `READ_THROUGH`
  (`:199-205`), owner `GradientCoupledInstanton`, slot `"extra_values"`; `SLOTS` (`:216`) gains
  `"extra_values"`; `_slot_tables` (`:224-228`) reads a mapping slot's tables as its keys (today it
  takes `value[0]` of a pair). The asserted placement becomes **(24, 6, 0)**: 24 specs, 6 read
  through, none excluded (`:412`). `EXCLUDED` stays, as an empty mapping. **One test passes a
  literal that changes with it**: `test_a_stale_or_unexplained_exclusion_is_named` (`:430-436`)
  excludes `GradientCoupledInstantonValue` with `" "`, and once that class is in `READ_THROUGH` it
  gets a second failure ("in more than one place"). Keep what it refuses, with a literal that still
  isolates it (for instance, that class taken out of `READ_THROUGH` for the case), and say how in
  the results note. The tests that build on `EXCLUDED` with `dict(EXCLUDED, …)` (`:424`, `:432`)
  work on an empty mapping as they stand.
- **No test is weakened**: the five existing breakage-catching tests keep their assertions.

### 1.3 The report (X3)

`tools/inventory_report.py` shows each further value table's count wherever it shows `value_count`:
on a compute target's record lines (`:373-374`) and in its class summary (`:405-406`), by the table's
name, a 0 printed as 0. The format is the agent's; record it in the field table of the results note
(one new row). `tests/test_inventory_report.py` gains the test that renders a `StoreInventory`
whose gradient records carry `extra_value_counts`, asserting the exact text the test chose,
including a 0, and that a class with none prints as it does today (one or more new tests; the
existing ones unchanged).

### 1.4 The store (X4)

`tests/test_inventory_store.py` (`integration`, 10's), changed as follows and no further:
- the store's gradient instantons become **three**: the two 10 wrote (successful with full values,
  at `dns[0]`; failed, at `dns[2]`; `:176-197`) and **a successful one stored without full values**
  (`set_store_full_values(False)` before `object_store`, at `dns[1]`), so that a row with profile
  rows and no value rows is in the store;
- the read-back asserts each gradient record's `(validated, value_count, extra_value_counts)`: the
  full one `(True, 5, {"GradientCoupledInstantonValue": 3})`, the scalars-only one
  `(True, 5, {…: 0})`, the failed one `(True, 0, {…: 0})`, and `problems == ()`;
- every other class's assertions as 10 left them (the class counts move only where the third
  gradient row moves them: `GradientCoupledInstanton` 2 → 3, and nothing else);
- the report and `main.py --inventory` tests see the new counts in the printed text.

Before writing this, check that a `GradientCoupledInstanton` stored with `store_full_values` false
validates (`GradientCoupledInstanton.py:614-633`: it expects 0 value rows) and writes its profile
rows (`:594-605`). If either does not hold, stop and ask.

### 1.5 The records (X5)

- `[gci-value-table-outside-the-inventory]` closed: board §3 → §4 (with how), and in
  `.documents/OPEN-ISSUES.md` §6a → §7, the header **60 → 59 open, 28 → 29 closed**, the date.
- The prose this commit makes false (P13): the spec's comment (§1.1); `.claude/rules/pool-read-apis.md`
  only if it says the table is outside the inventory (at `f5f395b` it does not); nothing else is
  expected. A rule asking a new factory for a spec, and for every child table, is 12's.

---

## 2. What to do

### 2.1 Before

1. Record `HEAD` and the load; run both suites (they must be 10a's counts, 730 and 67).
2. `git grep -n "gci-value-table-outside-the-inventory\|outside the inventory\|GradientCoupledInstantonValue"`
   outside `.prompts/` and `.documents/`: every hit is in §1.
3. **U5, at the gate and after**: `config.datastore.tables_to_drop` over all 31 sets, before and
   after the declaration, equal in decision and message. `dependent_tables` reads a spec's
   `dependencies()`, which `extra_values` does not enter (README §0.6), so nothing should move; if
   anything does, stop and ask.

### 2.2 The change

§1.1–§1.5.

### 2.3 Verification

1. **The suites**: default 730 + the new report test(s); integration 67, its counts unchanged in
   number (the store test changes in place). No `slow` block: the diff touches no `ComputeTargets/`
   file.
2. **By running it**: `main.py --inventory` on the integration test's store, built in your scratch
   directory by the test's own builder, and with `--show-all`; both outputs kept whole in the
   results note.
3. **The fingerprint, not recorded, only compared**, in a scratch script: `fingerprint_of(inventory,
   1)` of that store with the declaration and with it removed (by wrapping the entry's
   `inventory_spec` in the script). Only `GradientCoupledInstanton`'s class digest differs. Record
   both digests; SI records no fingerprint (README §7).
4. `ruff check --select F401,F811,F821` on every touched Python file: nothing new.

### 2.4 Deliberate breakage (README §5 rule 8)

Each applied, the named test run, reverted, and recorded as a replayable diff:
1. `extra_values` removed from the spec: the identity test, and coverage naming
   `GradientCoupledInstantonValue` ("its owner's spec does not name it in extra_values");
2. the column misnamed (`instanton_serail`): the column test;
3. `GradientCoupledInstantonProfile` named in both `values` and `extra_values`: the package's
   `ValueError` from `inventory_classes`;
4. the report no longer prints the extra count: the new report test;
5. `GradientCoupledInstantonValue` put back into `EXCLUDED` as well: coverage, "in more than one
   place".

---

## 3. Acceptance

1. **X1–X4** as §1; every test of §1.2–§1.4 passes, and each breakage of §2.4 is caught.
2. The integration store reads back with no named problem and with the three gradient records'
   counts as §1.4.
3. **The suites** give 10a's counts plus the new report test(s), by module, with
   `test_inventory_specs.py` and `test_inventory_store.py` at their counts.
4. **U5** unmoved (§2.1.3).
5. **The records**, in the one commit:
   - this board: the §1 row for 10b, items X1–X5, `### 5.N After prompt 10b (<date>)` with the
     rollback (`git revert` alone), the issue moved §3 → §4;
   - `.documents/OPEN-ISSUES.md` in the same commit: the row to §7, 59 open, 29 closed, the date.

---

## 4. Stop conditions — stop and ask

- The gate's suites are not 10a's counts.
- A scalars-only gradient instanton does not validate, or writes no profile rows (§1.4).
- `read_inventory` names a problem on the integration store that the declaration cannot explain, or
  the release behaves otherwise than its addendum says. **Do not work around a package defect in
  SI** (README §5 rule 11).
- U5 moves.
- Anything would need a change to a factory beyond §1.1, to `ComputeTargets/`, to a test outside
  §1.2–§1.4, or in another repository or the venv.

---

## 5. What this prompt does not do

- **Files it changes:** `Datastore/SQL/ObjectFactories/GradientCoupledInstanton.py` (the spec and its
  comment), `tools/inventory_report.py`, `tests/test_inventory_specs.py`,
  `tests/test_inventory_report.py`, `tests/test_inventory_store.py`, the results note, this board,
  `.documents/OPEN-ISSUES.md`.
- **Not:** any other factory, `ComputeTargets/`, `main.py`, `config/`, the plot scripts,
  `tools/compare_stores.py`, `requirements.txt`, the README, `.prompts/INDEX.md`, anything in another
  repository or the venv.
- **No store but temporary ones.** It runs no build, no cluster, no rehearsal.
- It chooses no `fingerprint_format` and records no fingerprint: the next campaign's (README §7).

---

## 6. The results note

`.documents/dk-and-rpk-migration/10b-count-the-gradient-value-table.md`, using README §5.1. It holds:
- the spec's diff, and the tests' changes, each with its reason;
- the report's new field row, and the two sample reports whole;
- the fingerprint comparison of §2.3.3;
- U5 before and after;
- the suites by module beside 10a's; the breakages as diffs;
- "State handed to the next prompt": for 11, that the inventory now counts
  `GradientCoupledInstantonValue`, which RH2's stores do not hold (U11: no gradient rows), so its
  `--inventory` output differs from 10's only where a gradient row would be.

**One commit**, in the repository's form, staged by explicit path only, after showing
`git diff --cached --name-only`.
