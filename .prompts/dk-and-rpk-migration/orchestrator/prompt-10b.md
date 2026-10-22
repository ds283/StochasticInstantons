# Orchestrator — prompt 10b, count the gradient instanton's value table

Read [`../README.md`](../README.md) first: §0.6, §2.2 (10b's charter), §5 (rules 4, 7, 8, 10, 11,
15–17) and §6.1 (U8, U12). The conventions are [`prompt-01.md`](prompt-01.md)'s §0 "Conventions",
unchanged but where this note says otherwise; [`prompt-06.md`](prompt-06.md)'s "Conventions
particular to 06" hold too (git, Ray, formatting, scratch). [`prompt-10.md`](prompt-10.md) is the
model: 10b extends 10's specs, tests and report, and 10's review (board §5.23) is the account of
what those look like when they are right.

**You do not write code.** You may:
- run the suites, `ruff check` and read-only Python checks, from the session scratchpad;
- build temporary stores in the scratchpad under a private Ray (`ray.init(address="local")`), in a
  separate process, and read them with `read_inventory`, `fingerprint_of` and `main.py --inventory`;
- replay the results note's deliberate-breakage diffs with `git apply`, and revert them;
- fix small residue in a follow-up commit of your own (§4).

**The prompt:** [`10b-count-the-gradient-value-table.md`](../10b-count-the-gradient-value-table.md) ·
**Board items:** X1–X5 · **Closes:** `[gci-value-table-outside-the-inventory]` · **Opens:** only what
the work finds · **Model:** Opus, as the prompt recommends · **No network.**

**Gate:**
- 10a landed (`80d99a7`) and was reviewed (`8272efb`): `datastorekit` `0.5.0` at `f47b9a255e9a…`,
  installed, not editable; the suites 730 and 67.
- `HEAD` is the commit that adds this note, or a later one that touches no code.
  `git diff --stat 80d99a7 HEAD -- . ':!.prompts' ':!.documents'` is empty.
- No SI cluster is up, and no other session runs a suite or a Ray job from this venv, or installs
  into it, while 10b runs.

## 0. What makes this prompt unusual

**The declaration is one keyword; everything else is making the tests see it.** A spec that
declares `extra_values` with a misnamed column, or that loses it, must fail a test, and a test
that cannot fail without the keyword shows nothing. 10's own tests were written around the table's
exclusion, so three of them encode the opposite of what 10b wants (the `EXCLUDED` entry, the
`(24, 5, 1)` count, the literal of the stale-exclusion test), and the report has never printed a
second count. The review reads hardest the tests' changes, the breakages and the integration
store's third gradient row.

**The orchestrator prototyped the declaration before dispatch** (correction 9), by attaching it to
the registry entry at runtime in a scratch script; the repository was not touched. It holds:
`inventory_classes` accepts it (24 classes, 10's order), U5 does not move, and a copy of 10's store
with a third, scalars-only gradient instanton validates, reads back with no named problem and with
the counts the prompt's §1.4 asks for; only `GradientCoupledInstanton`'s class digest moves. That is
a measurement, not the agent's work.

**Where the acceptance can pass vacuously.**
- **The scalars-only row must really be scalars-only.** `set_store_full_values(False)` is called on
  the object **before** `pool.object_store`, and its `_values` may stay populated: the factory's
  `store` (`Datastore/SQL/ObjectFactories/GradientCoupledInstanton.py:580`) then writes no value
  rows, and `validate` (`:620-621`) expects 0. A row stored with `_values = []` and full values on
  would also read `(True, 5, {…: 0})` and prove nothing about the flag. The read-back's
  `{"GradientCoupledInstantonValue": 0}` for it, beside `3` for the full one, is the evidence; say
  in the results note how the row was made.
- **The counts must be asserted, not printed.** `(validated, value_count, extra_value_counts)` per
  gradient record, the exact mappings of §1.4, in the test; `problems == ()` on the same read.
- **The identity test passes vacuously if `_as_table` drops `extra_values`.** `EXPECTED_SPECS`' form
  gains a fifth element for **every** entry (`{}` for 23), and `_as_table` returns
  `dict(spec.extra_values)` there; breakage 1 is the proof.
- **The column test passes vacuously if it skips an empty mapping and never meets the one entry.**
  It must check, for `GradientCoupledInstantonValue`, that the table is built, that
  `instanton_serial` is in it, and that the column's foreign keys name exactly
  `{"GradientCoupledInstanton"}`, as the `values` branch does (`tests/test_inventory_specs.py:351-358`);
  breakage 2 is the proof.
- **Coverage passes vacuously if `_slot_tables` reads the wrong thing for a mapping.** Today it
  returns `[value[0]]` for any non-`parent_sets` slot (`:224-228`); on a mapping that is a
  `KeyError` or, worse, a lookup that happens to succeed. For `extra_values` it returns the keys.
  Breakages 1 and 5 are the proof.
- **The new report test passes vacuously if it renders a class with an empty mapping.** Its
  gradient records carry `extra_value_counts` with a non-zero count and a 0, both asserted in the
  rendered text; and a class with none (any of the other compute targets) asserted to print as it
  does today, line for line.
- **The fingerprint comparison passes vacuously on two reads of the same spec.** The script prints
  where `datastorekit` was imported from and the GCI spec's `extra_values` in each case; only
  `GradientCoupledInstanton`'s class digest differs, the other 23 equal.

**Corrections to the prompt.** Pass them on.
1. **The board section** is **`### 5.27 After prompt 10b (<date>)`**, appended after §5.26. The
   header's "Last updated" and status line are updated to match. X1–X5 are already rows in board
   §1.1 (`:167-171`); fill in their state. The §1 row for 10b is `:76`. Closing the issue moves its
   row from board §3 (`:211`) to §4 (with how). In `.documents/OPEN-ISSUES.md`: the row at `:163`
   (in §6a, "Infrastructure — DatastoreKit and RayPoolKit adoption") moves to §7 "Closed" (`| Issue |
   Closed | By |`; `[show-all-flag-unused]`'s row at `:191` is the form), the header (`:3`) **60 → 59
   open, 28 → 29 closed**, the date.
2. **The prompt's line numbers hold at `8272efb`** (10a changed only `requirements.txt`): the spec
   `:147-182`, its comment `:148-155`, `values=` `:180`; the store's profile rows `:594-605` and
   value rows `:580-592`; `validate` `:611-647` (its count check `:614-633`); the value table's
   `instanton_serial` `:686-692`. `tests/test_inventory_specs.py`: `EXPECTED_SPECS` `:105`,
   `READ_THROUGH` `:199-205`, `EXCLUDED` `:208-214`, `SLOTS` `:216`, `_slot_tables` `:224-228`,
   `_as_table` `:283-297`, the column test `:335-358`, the placement `:412`, the stale-exclusion test
   `:430-436`, `dict(EXCLUDED, …)` `:424`, `:432`. `tools/inventory_report.py`: the record line
   `:373-374`, the class summary `:405-406`. `tests/test_inventory_store.py`: the gradient builder
   `:176-197`, `EXPECTED_COUNTS` `:206-231` (`GradientCoupledInstanton` `:228`), the gradient flags `:311`.
3. **§2.1.2's grep finds far more than §1**, and none of the rest is a stop. At `8272efb`, outside
   `.prompts/` and `.documents/`, 51 lines match, almost all of them `GradientCoupledInstantonValue`
   used as a table or a class (the factory, `config/`, `ComputeTargets/`, `tools/compare_stores.py`,
   `plotting/`, other tests, `.claude/rules/populate-ordering.md:80`,
   `validate-on-startup.md:72`). Read the check as: **every hit that says the table is outside the
   inventory, or excludes it,** is §1's. Those are exactly the spec's comment (`:153-155`) and
   `tests/test_inventory_specs.py:209-212` (`EXCLUDED`) and `:435-436` (the stale-exclusion test's
   literal). `.claude/rules/pool-read-apis.md` says nothing of it. Nothing else changes.
4. **Two literals of `test_the_report_shows_the_fields_of_today_s_report` are the gradient
   instanton's record lines**, and move with the report: `tests/test_inventory_store.py:339-340`,
   `"         :: delta_Nstar=0.5 | 5 value rows"` (the full one) and `"… delta_Nstar=2.5 | 0 value
   rows"` (the failed one). With the scalars-only row the class's lines are `delta_Nstar=0.5`, `1.5`
   and `2.5`, all three with `trajectory`, `N_init` and the rest on the `common to every record`
   line, as now. Changing those two literals to the new format, and adding the `1.5` line, is
   §1.4's "the report … tests see the new counts", not a weakening; say so in the results note.
   Every other literal of that test stays (`:352`'s `| 3 value rows` is `FullInstanton`'s and does
   not move; the five `committed` and five `@@ validated:` counts hold).
5. **"Value rows" is ambiguous on the gradient lines.** Today `5 value rows` there means profile rows
   (the `values` slot). The new count is printed **by the table's name** (the prompt's §1.3), so a
   reader can tell `GradientCoupledInstantonValue` rows from the five. The class summary today reads
   `3 records; 10 value rows; committed …` on the prototype store; the format of its extra total is
   the agent's.
6. **The prose made false or incomplete by the change, within the five files**, is corrected in
   place, each named in the results note (README §5 rule 15: nothing else reformatted): the spec's
   comment (§1.1); `tools/inventory_report.py`'s module docstring, whose compute-target bullet says
   "the number of value rows its spec counts" (add the further tables); `tests/test_inventory_store.py`'s
   docstring, which says each compute target has "a successful and a failed record" (add the
   scalars-only gradient instanton, and 10b to its attribution); `tests/test_inventory_report.py`'s
   and `test_inventory_specs.py`'s docstrings only if they become false (the latter's coverage bullet
   stays true with `EXCLUDED` empty), and the `EXCLUDED` and `EXPECTED_SPECS` comments. Nothing
   outside the five files and the records.
7. **The report test's helper.** `tests/test_inventory_report.py`'s `_rec` (`:66-67`) builds a
   `Record` without `extra_value_counts`. A new keyword with a default, or a `Record(...)` built in
   the new test, are both fine; **the existing test functions' bodies stay equal by `ast`**, which
   the review checks.
8. **The stale-exclusion test** (`:430-436`). Once `GradientCoupledInstantonValue` is in
   `READ_THROUGH`, `{"GradientCoupledInstantonValue": " "}` gives two failures, `excluded with no
   reason` and `in more than one place (read through an owner's spec, excluded)`. The prompt suggests
   taking the class out of `READ_THROUGH` for that case (e.g. `{k: v for k, v in READ_THROUGH.items()
   if k != "GradientCoupledInstantonValue"}`), so that the assertion stays the one-element list it is
   today; another literal that isolates "excluded with no reason" is equally good. The first half of
   the test (`temperature`) stays.
9. **The orchestrator's prototype**, at `8272efb`, from the session scratchpad (`orch10b/proto.py`,
   `orch10b/proto.out`; the agent may read both and owes them nothing). The declaration attached by
   `dataclasses.replace(base(f), extra_values={"GradientCoupledInstantonValue": "instanton_serial"})`
   on the factory instance; `datastorekit` imported from the venv's `site-packages`.
   - **U5**: 31 subsets, **10 closed** without and with the declaration, **none moved** (decision,
     tables and message). The spec's `dependencies()` with it: `CosmologicalParams`,
     `InflatonTrajectory`, `MasslessDecoupledDiffusion`, `N_final`, `N_init`,
     `alpha_regularization`, `delta_Nstar`, `n_collocation_points`, `tolerance`; no value table.
   - **`inventory_classes`** with it: 24 classes, 10's order.
   - **The store**: `tests/test_inventory_store.py`'s `_STORE_SCRIPT`, with `gradient()` given a
     `full=True` argument, `obj.set_store_full_values(full)` before `object_store`, and
     `gradient(p_quadratic, dns[1], False, full=False)` added before the failed one. It builds (exit
     0, `RESULT {"ok": true}`; the scalars-only row validates). `read_inventory`, no Ray initialised:
     every class at `EXPECTED_COUNTS` but `GradientCoupledInstanton`, `(2, False)` → `(3, False)`;
     `problems == ()` with and without the declaration.
   - **The gradient records**, sorted: without the declaration `(True, 0, {})`, `(True, 5, {})`,
     `(True, 5, {})`; with it `(True, 0, {'GradientCoupledInstantonValue': 0})`,
     `(True, 5, {'GradientCoupledInstantonValue': 0})`, `(True, 5, {'GradientCoupledInstantonValue': 3})`.
   - **The fingerprint** (`fingerprint_of(inventory, 1)`): without, overall
     `ffac93337770ed6b71659505d6ddd118e730c8438038b0ecce0f554100948658`, GCI class
     `5b88f64ce9dc59ee91a1cf49362d565ac6db316231a349365804e2945dc9ef74`; with, overall
     `e3437a9b2f16415f5635ee121fa7f09d07ac74c30400d5973a3afaeec8fc7c78`, GCI class
     `e342c0aa9bd8dd8348a68bd14d591b37528c9f4cdd19c7b9c773937bb02412ec`; **1 of 24** class digests
     differs. A second, independent build gave the same four digests: they hang on identity, not
     timestamps or serials. So an agent store built as §1.4 says (the third row at `dns[1]` on the
     quadratic trajectory, 10's other rows unchanged) should reproduce them; a difference is to be
     explained in the results note, not hidden.
   - **The renderer today** prints the same report with and without the declaration (it ignores the
     new field): the GCI section is `3 records; 10 value rows; committed …`, then `@@ validated: 3
     record(s)` and `delta_Nstar=0.5 | 5 value rows`, `1.5 | 5 value rows`, `2.5 | 0 value rows`.
10. **The suites at the gate** (re-run by the orchestrator at `8272efb`, 19:59 BST, load 18):
    default **730 (729 passed, 1 skipped)**, 36.1 s; integration **67 (66 passed, 1 skipped)**,
    51.7 s. By module: `test_inventory_specs.py` 12, `test_inventory_report.py` 10 (default);
    `test_inventory_store.py` 4 (integration). The `slow` block is not run (no `ComputeTargets/`
    change). `ruff check --select F401,F811,F821`: 0 findings in each of the five Python files 10b
    touches.
11. **No new test module.** The new report test(s) go into `tests/test_inventory_report.py`; the
    store test changes in place (its four tests stay four; a fifth is not needed, but if the agent
    adds one it says why).
12. **`.prompts/INDEX.md` and the README are the orchestrator's.** The agent touches neither.

**The facts, checked by the orchestrator on 2026-10-22 at `8272efb`, 19:57–20:02 BST.** Pass them
on.
- **The tree.** Branch `dk-and-rpk-migration`, clean, `HEAD` `8272efb` before this note.
  `git diff --stat e2c7b22 HEAD` outside `.prompts/` and `.documents/` is `requirements.txt` alone
  (10a's pin). The 17 store files of prompt-01.md §1 step 5 are in the tree (ignored); 10b opens none.
- **Ray and the lock.** `ray_cluster.sh status`: lock free, no `/tmp/ray-si` process, the four ports
  free. `pgrep` finds no `gcs_server`, `raylet`, `ray::`, `pytest`, `unittest` or `main.py`.
  `RAY_ADDRESS` unset.
- **The load** was 28 / 19 / 17 on 10 CPUs (42 during the integration run).
- **The venv.** `pip freeze` 83 lines, 10a's (`datastorekit @ …@f47b9a255e9ad58e0d0eaf85644f53b575884d31`);
  `pip check` clean. 10b installs nothing.
- **DatastoreKit** `2900d82`, **RayPoolKit** `17029d9`, both clean.
- **The stores.** 10b opens only temporary ones: the tests' (under `tempfile`) and its own scratch
  stores. Not the 17 in the tree, nothing under `out-*/` or `~/ScienceData/`.

**What the review exists to establish.**
- **(E1) X1.** The factory differs from `8272efb`'s by the `extra_values` keyword and the spec's
  comment alone (by `ast`, the spec set aside).
- **(E2) X2.** `EXPECTED_SPECS` carries `extra_values` for all 24; the column test checks the extra
  table, its column and the foreign key; coverage places 30 as **(24, 6, 0)**, `EXCLUDED` an empty
  mapping; no test weakened.
- **(E3) X3.** The report prints each extra count by the table's name, 0 as 0, on the record lines
  and in the class summary; a class without one prints as today.
- **(E4) X4.** The integration store's three gradient records read back `(True, 5, {…: 3})`,
  `(True, 5, {…: 0})`, `(True, 0, {…: 0})`, no problem; the scalars-only one made by the flag.
- **(E5) The fingerprint and U5.** One class digest moves; U5 unmoved.
- **(E6) X5 and the records.** The issue closed on the board and in the index, 59 open, 29 closed.
- **(E7) Nothing else moved.** No file outside the prompt's §5 list; the suites at 730 + the new
  report test(s) and 67; the breakages caught; the venv, the other repositories and every store
  untouched.

## 1. Before you dispatch

1. **The tree.** `git status --short` clean, `git diff --cached` empty, `git log` since `80d99a7`
   records only.
2. **Ray and the lock.** `ray_cluster.sh status` clean; no Ray process.
3. **The venv.** `pip freeze` saved; `pip check` clean.
4. **The load**, recorded.
5. **Mtimes**, for check 11: the 17 store files, and every entry under `~/ScienceData/`.
   DatastoreKit's and RayPoolKit's `HEAD` and `git status --porcelain`.
6. **The measurements of §0**: the line numbers, the grep, the store and validate paths of a
   scalars-only row, the prototype (U5, the store, the counts, the fingerprints, the renderer), the
   suites by module, `ruff`.

**Done 2026-10-22, 19:57–20:02 BST,** at `8272efb`: all six hold, step 6 as §0 records. In
`orch10b/` in the session scratchpad: `pip-freeze.txt` (83), `mtimes-stores.txt` (17),
`mtimes-sciencedata.txt` (835 entries, the root included; the same as 10a's), `proto.py` and
`proto.out`, `store/` (the prototype's store) and `rerun/` (its independent rebuild),
`classes-with.json`, `classes-without.json`, `report-with.txt`, `report-without.txt`,
`default.txt` and `integration.txt` (the gate's suites), `default-by-module.txt` (730),
`integration-by-module.txt` (67).

## 2. Dispatch

One fresh-context subagent, on **Opus**, in the background. Give it:
- the prompt;
- the campaign README and the board;
- 10's and 10a's results notes (the form of a results note, 10's spec table, coverage, report, store
  and breakages);
- `HEAD`, the load and §0 of this note, up to "## 1. Before you dispatch" only, as a copy in the
  session scratchpad. It does not read `orchestrator/`, and does not read prompt 11. It may read
  `orch10b/proto.py` and `orch10b/proto.out`, and owes them nothing.

Tell it plainly:
- **One commit, at the end, made once.** Its results note is
  `.documents/dk-and-rpk-migration/10b-count-the-gradient-value-table.md`, in README §5.1's form,
  with the prompt's §6 additions. Stage by explicit path, and show `git diff --cached --name-only`
  before committing.
- **The files it may change** are the prompt's §5 list: the factory's spec and its comment,
  `tools/inventory_report.py`, the three inventory test modules, the results note, the board,
  `.documents/OPEN-ISSUES.md`; with the docstrings and comments of correction 6. **Not**
  `ComputeTargets/`, `main.py`, `config/`, any other factory or test, the README, `.prompts/INDEX.md`,
  anything in another repository or the venv.
- **The corrections in §0**, especially 3 (the grep), 4 (the two report literals), 8 (the stale
  exclusion) and the vacuous-pass list.
- **Stop and ask** on any of the prompt's §4 conditions. An existing test outside the three modules
  that fails is current behaviour moving, never a reason to edit it.
- **It replies with:**
  - the results note's path and the commit;
  - `git show --stat` of the commit;
  - the factory's diff;
  - each test change with its reason (the `EXPECTED_SPECS` form, `_as_table`, the column test,
    `_slot_tables`, `READ_THROUGH`/`EXCLUDED`/`SLOTS`, the placement, the stale-exclusion literal, the
    store's third row and its assertions, the two report literals), and the new report test(s) by
    name with what each asserts;
  - the report's new field row, and the two sample reports' gradient sections;
  - the three gradient records as read back, and `problems`;
  - the fingerprint comparison: the import path, both overall digests, both GCI class digests, the
    count of class digests that differ;
  - U5 before and after;
  - the breakages and what caught each, with the failure line;
  - the suites by module beside the gate's, with the load; `ruff`;
  - the closed issue's §4 text and its index row, and the header's counts;
  - every deviation with its class;
  - the "State handed to the next prompt" section, verbatim.

## 3. The review — eleven checks

1. **Scope.** `git show --stat <commit>`: the factory, `tools/inventory_report.py`, the three test
   modules, the results note, the board, `OPEN-ISSUES.md`. Nothing else. `git status --short` clean;
   one commit of the agent's since this note, no amend in the reflog, no leftover branch; no scratch
   file or store in the repository.
2. **E1, the factory.** By `ast`, `GradientCoupledInstanton.py` at `<commit>~1` equals `<commit>`'s
   with `inventory_spec` set aside (docstrings included). Within the spec: the `InventorySpec(...)`
   call differs by `extra_values={"GradientCoupledInstantonValue": "instanton_serial"}` alone;
   the comment says the value table is counted as a further value table, 0 for a row stored
   without full values, and no longer that it is outside the inventory.
3. **E2, the spec tests.** `EXPECTED_SPECS`: 24 entries, each with a fifth element, `{}` but for
   `GradientCoupledInstanton`; `_as_table` returns `dict(spec.extra_values)`; nothing else in the
   table changed (compare the four other elements of each entry with `<commit>~1`'s, by evaluating
   both literals). The column test checks the extra table, its column and the foreign key's owner.
   Every other test function of the module equal by `ast` to `<commit>~1`'s but those §1.2 names
   (`test_every_registered_class_is_placed_exactly_once`'s count, the stale-exclusion test).
4. **E2, coverage.** `READ_THROUGH` has six entries, `GradientCoupledInstantonValue →
   ("GradientCoupledInstanton", "extra_values")`; `EXCLUDED == {}` and still defined; `SLOTS`
   includes `"extra_values"`; `_slot_tables` reads a mapping's keys; the placement `(24, 6, 0)`. The
   stale-exclusion test still asserts a one-element list naming "excluded with no reason", by a
   literal that isolates it (correction 8).
5. **E3, the report.** The record line and the class summary print each extra count by table name,
   a 0 as 0; nothing else in `tools/inventory_report.py` changes but its docstring (by `ast`, the
   two functions aside, names and attributes: still no `open`, `sqlite3`, `create_engine`,
   `read_inventory`, `open_read_only`). The new test(s) render records with a non-zero and a 0 count
   and assert the exact text; a class with no extra table asserted unchanged. The existing tests'
   bodies equal `<commit>~1`'s by `ast` (correction 7).
6. **E4, the store test.** The third gradient row: `set_store_full_values(False)` before
   `object_store`, at `dns[1]`, its `_values` as the full one's (or the note says otherwise and why
   it still tests the flag). The assertions of §1.4, exactly; `EXPECTED_COUNTS` differs from
   `<commit>~1`'s by `GradientCoupledInstanton` `2 → 3` alone; the report test's literals differ by
   the gradient lines alone (correction 4); every other assertion unchanged.
7. **E7, the breakages.** Replay the five diffs with `git apply` from the clean tree (`--check` and
   `-R --check` first, in `bash`); each fails what the prompt's §2.4 names (1: the identity test and
   coverage naming `GradientCoupledInstantonValue` "… does not name it in extra_values"; 2: the
   column test; 3: `ValueError: inventory_classes(): GradientCoupledInstanton names
   GradientCoupledInstantonProfile both as its value table and in its extra_values`; 4: the new
   report test; 5: coverage, "in more than one place"). Revert each; `git status` clean after.
8. **E4–E5, by running it.** Build the agent's store with the test's own builder at `<commit>` into
   the scratchpad (its `_STORE_SCRIPT` in a subprocess under a private Ray); `read_inventory`: the
   three gradient records and no problem; `main.py --inventory` on it (`--ray-address 127.0.0.1:9`,
   `RAY_ADDRESS` the same), exit 0, and with `--show-all`; the gradient section prints the counts;
   no file changed; no Ray process after. The fingerprints with and without the declaration (the
   prototype's wrapping, reversed: the entry's `inventory_spec` replaced by one with `extra_values`
   removed): only the GCI class digest differs; compare all four digests with correction 9's and
   with the results note's.
9. **E5, U5 replayed.** `tables_to_drop` over all 31 subsets at `<commit>`: decisions, tables and
   messages equal `orch10b/proto.out`'s (10 closed, none moved).
10. **E7, the suites.** The agent's: default 730 plus the new report test(s), all passing (1
    skipped); integration 67, all passing (1 skipped). The orchestrator re-runs both at `<commit>`,
    serially. `ruff check --select F401,F811,F821` on the five Python files: 0, as at the gate.
11. **E6–E7, hygiene and the records.** `pip freeze` equals §1's copy; `pip check` clean.
    DatastoreKit and RayPoolKit at §1's `HEAD`s, clean. The 17 store files and the 835
    `~/ScienceData/` entries keep their mtimes. No Ray process; the lock free. The results note
    follows README §5.1 with the prompt's §6 additions (the spec's diff, the tests' changes with
    reasons, the report's field row and the two sample reports whole, the fingerprint comparison,
    U5, the suites by module, the breakages as diffs, "State handed to the next prompt" for 11). The
    board: §1 row (✅, "this commit", the results note), X1–X5, the header, `### 5.27` with the
    rollback (`git revert` alone), the issue §3 → §4. `OPEN-ISSUES.md`: the row in §7, 59 open, 29
    closed, the date.

## 4. After the review

- **Record it on the board** as an *Orchestrator review of prompt 10b* paragraph in §5.27: what each
  check found, and anything handed on to 11. Fix small residue in a follow-up commit of its own:
  - "this commit" → the SHA (board and results note);
  - this note added to the board's list of orchestrator notes, marked "used for 10b";
  - `.prompts/INDEX.md`: the campaign's line (10b landed and reviewed; one issue closed).
- Anything the review finds that is not residue is opened on the board's §3 and in the index, in
  the same commit.
- **Report to the user:** the declaration in one line; coverage (24, 6, 0) and the issue closed; the
  three gradient records and the report's new counts; the fingerprint (one class digest moves); U5;
  the suites.
- **Then 11** can be dispatched; its note is written after this review, at 10b's commit.
