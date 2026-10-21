# Prompt 10 — port the inventory

**Campaign:** [`README.md`](README.md) · **Board items:** **N1**–**N6** ·
**Board:** [`IMPLEMENTATION_STATE.md`](IMPLEMENTATION_STATE.md)
**Written:** 2026-10-21, with prompts 08, 09 and 11, after 07's review (board §5.19). Measured at
`91e6f31`; 09 moves lines in `main.py` and adds and changes tests, so re-measure every line this
prompt cites in a file 09 touched.
**Gate:**
- 09 landed and reviewed (board §1): the layer is the package's, `--inventory` refuses with exit 2
  (P11), and the suites pass at 09's counts;
- on branch `dk-and-rpk-migration`, no tracked change in `git status`;
- no SI cluster is up, and no other session runs a suite or a Ray job from this venv while 10
  runs.

**Closes:** `[show-all-flag-unused]`. **Opens:** one issue for `GradientCoupledInstanton`'s child
table that no spec can reach (§1.1, U8), and anything else the work finds.
**Recommended model:** **Opus**. Each spec's leaves and parents are read off its factory's `build`
lookup, table by table, and the coverage test has to place all 30 registry entries.

**The protected files this prompt touches, and what changes in each** (`CLAUDE.md`; README §5
rule 15): each of these factories gains an `inventory_spec` method and loses its `inventory()`
hook where it has one, and nothing else changes in it:
`Datastore/SQL/ObjectFactories/{version,store_tag,tolerance,DimensionlessQuantity,DimensionfulQuantity,integration_metadata,redshift}.py`.
`config/sharding.py` loses `inventory_config` and its `_instanton_merge` helper, and nothing else.

**Read first:**

1. `CLAUDE.md`, and `.claude/rules/pool-read-apis.md` and `datastore-factories.md` as 09 left them.
2. [`README.md`](README.md): §0.1 items 4 and 11, §2.2 (10's charter, in full, with its acceptance
   item 5), §4, §5, §6.1 (U6, U8) and §6.2 (P18), §6.3 (the question at 10).
3. DatastoreKit at the tag (`git -C /Users/ds283/Documents/Code/DatastoreKit show v0.4.0:<path>`),
   and the installed package. **Read; edit nothing there** (README §5 rule 12):
   - `docs/client-contract.md` §4 (the inventory spec) and §9.7;
   - `datastorekit/store_inventory.py`, in full: `Parent` (with `types=`, `type_column=`,
     `nullable=`, `cross_shard=`), `ParentSet`, `InventorySpec`, `inventory_specs` (`:916`),
     `inventory_classes` (`:929`), `read_inventory` (`:979`), and the named problems in the module
     docstring;
   - `datastorekit/SQL/schema.py`'s `dependent_tables` (`:359`): it reads `inventory_spec` parents
     as well as foreign keys, so the specs can move 09's drop table (§1.4).
4. **ChamPBH's 09 and SGK's report, as done** (read only; import nothing from either):
   - ChamPBH: `prompts/dk-and-rpk-migration/09-port-the-inventory.md`, its board §5.13a and §5.14
     with the review below it, its log 09 (with its field-by-field table of what the old report
     showed and what the new one shows), and `tools/inventory_report.py` (570 lines; 17
     `inventory_spec(self)` methods in its factories);
   - SecondaryGWKit: `tools/inventory_report.py` (696 lines), `format_inventory_report`.
5. 09's results note: its "State handed to the next prompt", U5's table, and the test counts.
6. **What today's report shows**: `.documents/dk-and-rpk-migration/out/07-readers-resumed-inventory.log`
   (RH1's run of `main.py --inventory`), and the five helpers 09 deleted, at `91e6f31`
   (`git show 91e6f31:main.py`, `:1227-1338`).

---

## 0. What this prompt is

U6: the inventory, ported. The package has no `pool.inventory`; its inventory is
`datastorekit.store_inventory.read_inventory(primary, factories)`, read-only, on a **closed** store,
with no Ray, over each factory's `inventory_spec()`. It also names problems the old inventory never
looked for (orphan value rows, unresolved parents, a replicated class that differs between shards).

It is also **U8**: RunRegistryKit, which SI adopts after this campaign (README §7), fingerprints a
store through `read_inventory`, which reads only the classes that declare a spec and passes over the
rest silently. So every registered class must be covered: a spec of its own, read through an
owner's, or excluded by name with a reason, enforced by a test.

---

## 1. What is wanted

### 1.1 The specs (N1)

**Each factory whose class the report covers defines `inventory_spec()`, and so does every class a
spec depends on** (contract §4). At least:
- the parameters: `delta_Nstar`, `N_init`, `N_final`, `efold_value`, `n_collocation_points`,
  `alpha_regularization`;
- the quantities: `phi_value`, `pi_value`, `inflaton_mass`, `quartic_coupling`;
- `QuadraticPotential`, `QuarticPotential`, `MasslessDecoupledDiffusion`, `tolerance`,
  `CosmologicalParams`, `version` and `store_tag`;
- the five compute targets, `InflatonTrajectory`, `FullInstanton`, `SlowRollInstanton`,
  `CompactionFunction` and `GradientCoupledInstanton`, each with its value table in the `values`
  slot: `InflatonTrajectoryValue` (`trajectory_serial`), `FullInstantonValue` and
  `SlowRollInstantonValue` (`instanton_serial`), `CompactionFunctionSamples` (`parent_serial`);
- **`redshift` and `IntegrationSolver`** (U8): registered, written by no driver (README §4.1; P12),
  and named by no other spec. **A spec each is preferred** (README §2.2, 10's item 5): it is cheap,
  and an exclusion means a row that did appear would change no fingerprint. Exclude either only
  with a reason the results note gives.

**Settled points:**
- **The quantity factories' specs are instance methods**, since `ObjectType` is held on the
  instance (`DimensionfulQuantity.py:30`, `DimensionlessQuantity.py:30`). The package reads the
  spec by `getattr` on the registry entry (`inventory_specs`, `:916-926`), so every spec may be an
  instance method; ChamPBH's are all `inventory_spec(self)`. Use one form throughout.
- **The four polymorphic references are `Parent(column, types={…}, type_column=…)`**, with the type
  column among the leaves (`inventory_classes` refuses otherwise): `InflatonTrajectory.potential_serial`
  by `potential_type`, and `diffusion_serial` by `diffusion_type` on `FullInstanton`,
  `SlowRollInstanton` and `GradientCoupledInstanton` (README §0.1 item 11). **Take the maps from
  SI's own registries** (`CosmologyConcepts/Potentials/registry.py`'s `POTENTIAL_REGISTRY`, keyed by
  `CosmologyConcepts/Potentials/model_ids`; `InflationConcepts/DiffusionModel/registry.py`), not as
  literals, and check them against `tools/compare_stores.py`'s `POLYMORPHIC_REFERENCES` (`:221-227`),
  which 01's tests already tie to those registries
  (`tests/test_compare_stores.py`).
- **No parent is `cross_shard`** unless you find one that needs it: every sharded class's parents
  are replicated (on every shard) or sharded on the same `delta_Nstar` (`CompactionFunction`'s
  instantons). Say so, table by table.
- **Leaves and parents are each `build`'s lookup**: the columns its get-or-insert query matches
  on. A stored `label` is not identity and is not a leaf (ChamPBH's §1.2). Derive the table **before
  writing any spec**, and record it, table by table, in the results note: class, leaves, parents
  (column → class, or the type map), `values`, `validated`, and why.

**`GradientCoupledInstanton` has two child tables and a spec one `values` slot** (U8; README §6.3).
`GradientCoupledInstantonProfile` (`parent_serial`) is written for every row and holds the radial
profile, the science output (`GradientCoupledInstanton.py:556-562`);
`GradientCoupledInstantonValue` (`instanton_serial`) is written only when `store_full_values` is
set (`:542-546`). **The recommendation is that `GradientCoupledInstantonProfile` takes the slot**,
and `GradientCoupledInstantonValue` is excluded in the coverage test with that reason. Whichever is
left out, **open an issue for it** on the board's §3 and in `.documents/OPEN-ISSUES.md`: a
fingerprint of a store holding gradient rows cannot see that table. Whether to ask DatastoreKit
for a second value table per spec stays the user's (README §6.3); the issue says so, and is owned
by the user.

### 1.2 The report (N2)

A new `tools/inventory_report.py`: `format_inventory_report(inventory, db_name, units,
verbose=False) -> str` (or a list of lines; say which). It renders a `StoreInventory` and **reads
nothing itself**: no `open`, `sqlite3`, `create_engine`, `read_inventory` or `open_read_only` in the
module (the registry may be read, in memory, to learn which leaves are floats and in which unit, as
SGK's and ChamPBH's do). Modelled on theirs; import nothing from either.

**It shows at least what today's `--inventory` shows** (P18; RH1's log, read-first item 6):
- each parameter's and quantity's values, with the unit of a dimensionful one (`PlanckMass` for φ,
  π and m, read from the column's unit suffix: `.claude/rules/datastore-units.md`), the
  efold values truncated to the first and last ten when there are 20 or more, and "no values" for
  an empty class;
- each compute target's validated and unvalidated counts, its version labels and timestamp range,
  and its records **by physical labels** (`δN★`, `N_init`, `N_final`, the trajectory's φ₀ and the
  potential), not by serials as today's report prints them;
- and also **every named problem, in full**, never truncated, under its class.

Record, as ChamPBH's log 09 did, a table of every field today's report shows against the new
report: kept, new, changed, or not kept (with why). Nothing parses either report (P18).

### 1.3 `main.py --inventory` (N3)

- Reads the closed store with `read_inventory(args.database, config.datastore.factories)`, prints
  the report and exits, **before `ray.init`** (`main.py:100` at `91e6f31`), replacing 09's refusal.
  It never starts Ray, never prunes, never drops, and never creates a store.
- Exit codes, as ChamPBH's: **0** with the report; **1** with `!! --inventory: <message>` on stderr
  for an absent store or one the package refuses (every store before 09's, README §7); **2** with
  `--drop`, which is refused (`--inventory` with `--drop` makes no sense on a read-only reader).
- **`--show-all`** (`config/argument_parser.py:402-407`), parsed today and read by nothing, maps to
  `verbose`: no truncation. Its help text is made true. This closes `[show-all-flag-unused]`.
- `--ray-address` stays required by the parser (`CLAUDE.md`, "Build and test"); `--inventory` simply
  never uses it.

### 1.4 The old inventory deleted, and U5 re-checked (N4)

- The 17 `inventory()` hooks (`CompactionFunction.py:511`, `CosmologicalParams.py:106`,
  `DimensionfulQuantity.py:127`, `DimensionlessQuantity.py:100`, `FullInstanton.py:486`,
  `GradientCoupledInstanton.py:637`, `InflatonTrajectory.py:384`, `N_final.py:68`, `N_init.py:68`,
  `QuadraticPotential.py:100`, `QuarticPotential.py:103`, `SlowRollInstanton.py:481`,
  `alpha_regularization.py:85`, `delta_Nstar.py:68`, `efold.py:67`, `n_collocation_points.py:81`,
  `redshift.py:93`, all under `Datastore/SQL/ObjectFactories/`, at `91e6f31`) are deleted, with any
  import only they used.
- `config/sharding.py`'s `inventory_config` and `_instanton_merge` (`:78-102` at `91e6f31`, the end of the file) are
  deleted; nothing imports them after 09.
- **U5, re-run.** `dependent_tables` reads each spec's parents as well as foreign keys, so a spec
  can make a group a dependent of another. Re-run 09's drop test, and compute the closure of every
  subset of the five groups with and without the specs: say what moved. If anything moved, the
  refusal's message and 09's test follow it, and that is a named change to 09's test (README §5
  rule 7).

### 1.5 Coverage, for the fingerprint (N5; U8)

A test walks `config.datastore.factories` and puts **every registered class in exactly one of
three places**:
1. it declares a spec;
2. it is a value or tag table read through an owner's spec, the test naming the owner and the slot
   (and checking that the owner's spec names it there);
3. it is excluded, by name, in a table in the test, with a one-line reason.

It fails on a class in none of the three or in more than one, on an exclusion naming a class no
longer registered, and on an exclusion with no reason. At `91e6f31` the 30 entries should come to
24 specs (§1.1's 22, with `redshift` and `IntegrationSolver`), 4 read through (`InflatonTrajectoryValue`,
`FullInstantonValue`, `SlowRollInstantonValue`, `CompactionFunctionSamples`) plus one of the two
`GradientCoupledInstanton` tables, and 1 excluded (the other). Confirm or correct this count.

### 1.6 The prose (N6)

What this commit makes false (P13): `.claude/rules/pool-read-apis.md` as 09 left it (the inventory
is now `read_inventory` on a closed store, through `main.py --inventory`), and
`.documents/FILE_MAP.md` (a row for `tools/inventory_report.py`). A rule asking every new factory
for a spec is 12's, with the rest of the rules' rewrite; record it for 12.

---

## 2. What to do

### 2.1 Before

1. Record `HEAD` and the load; run both suites (they must be 09's counts).
2. **Derive the spec table** (§1.1) from each `build`, before writing a spec. Prototype it, as
   ChamPBH's orchestrator did, by attaching the specs at runtime in a scratch script (not in the
   repository): `inventory_classes(factories)` accepts them; every column a spec names is in
   `build_schema`'s tables.
3. `git grep -n "inventory(\|inventory_config\|_instanton_merge\|show_all\|--show-all"` outside
   `.prompts/` and `.documents/`: every hit is in §1.3 or §1.4.

### 2.2 The change

§1.1–§1.6.

### 2.3 Verification

1. **The tests** (README §5 rule 10: stores only under `tempfile`; Ray only where needed, and then
   `integration`-marked with the reason):
   - **without Ray:** `inventory_classes` accepts the registry; each spec's leaves and parents
     resolve against `build_schema`; the report, rendered from `StoreInventory` objects the test
     builds, prints each field of §1.2's table, a dimensionful value in its unit, the truncation and
     `verbose`, and a long problem whole on one line; the coverage test (§1.5); an `ast` test that
     `--inventory` is handled before `ray.init` and never reaches it; `main.py --inventory` on an
     absent store (exit 1, nothing created) and with `--drop` (exit 2), as subprocesses with an
     address nothing listens on and a timeout;
   - **under Ray, `integration`:** a 2-shard store built through the package's pool in a
     subprocess under a private Ray (as 06's I6 and 09's acceptance 4 do), holding a trajectory,
     one of each compute target, successful and failed, and both potential types, from synthetic
     values (no solve, so not `slow`). Closed, then read in the test process by `read_inventory`:
     every class present with its count, **no named problem**; and the report rendered from it
     shows P18's fields. Then `main.py --inventory` on it exits 0 with that report.
2. **The suites**: default and integration at 09's counts, less any test deleted with a named
   reason (09's `--inventory` refusal test, which this prompt replaces), plus the new ones, by
   module. No `slow` block: the diff touches `Datastore/SQL/ObjectFactories/`, not `ComputeTargets/`
   (`.claude/rules/test-selection.md`). If it does touch `ComputeTargets/`, run `slow` once.
3. **By running it**: `main.py --inventory` on your integration store, and with `--show-all`; both
   outputs kept in the results note, whole.
4. `ruff check --select F401,F811,F821` on every touched Python file: nothing new.

### 2.4 Deliberate breakage (README §5 rule 8)

Each applied, the named test run, reverted, and recorded as a replayable diff:
1. one spec's parent removed (e.g. `FullInstanton`'s `delta_Nstar_serial`);
2. one leaf misnamed;
3. the type column dropped from a polymorphic parent's leaves (`inventory_classes` refuses);
4. `--inventory` moved after `ray.init` (the `ast` test);
5. the spec removed from one owner (the coverage test names it);
6. a new registered class with no spec and no exclusion (the coverage test names it).

---

## 3. Acceptance

1. **The specs and their tests** (§2.3.1): `inventory_classes` accepts the registry; every spec's
   columns resolve; the integration store reads back with no named problem and renders every field
   of P18's list; problems print in full.
2. **`main.py --inventory`** needs no Ray: on a missing store it exits 1 cleanly, creating nothing;
   with `--drop` 2; on a package store 0.
3. **The suites** give 09's counts plus the new tests, less the named deletion, by module.
4. **The breakages of §2.4**, all caught.
5. **Coverage** (U8): every registered class placed exactly once; the GCI table left out opened as
   an issue.
6. **U5** re-checked (§1.4), with what moved, if anything.
7. **The records**, in the one commit:
   - this board: the §1 row for 10, items N1–N6, `### 5.N After prompt 10 (<date>)` with the
     rollback (`git revert` alone), `[show-all-flag-unused]` moved §3 → §4, the GCI issue added to
     §3;
   - `.documents/OPEN-ISSUES.md` in the same commit: the closed issue to §7, the opened one added,
     the counts and the date.

---

## 4. Stop conditions — stop and ask

- The gate's suites are not 09's counts.
- A spec cannot express a class's identity (a key that needs more than leaves, parents and parent
  sets), or `read_inventory` names a problem on a store the package wrote that the spec cannot
  explain. **Do not work around a package defect in SI** (README §5 rule 11).
- U5's table moves in a way that refuses a set 09 accepted.
- Anything would need a change to a factory beyond its `inventory_spec` and the deleted
  `inventory()`, to `ComputeTargets/`, or in another repository or the venv.

---

## 5. What this prompt does not do

- **Files it changes:** the factory modules (a spec each, the `inventory()` hook deleted);
  `config/sharding.py` (§1.4); `main.py` (§1.3); `config/argument_parser.py` (`--show-all`'s help
  only); `tools/inventory_report.py` (new); the new test module(s), and 09's test of the refusal;
  09's drop test only if §1.4 moves it; `.claude/rules/pool-read-apis.md`, `.documents/FILE_MAP.md`;
  the results note; this board; `.documents/OPEN-ISSUES.md`.
- **Not:** `ComputeTargets/`, the plot scripts, `tools/compare_stores.py`, the rehearsal scripts,
  `requirements.txt`, the README, `.prompts/INDEX.md`, anything in another repository or the venv.
- **No store but temporary ones.** It runs no build, no cluster, no rehearsal, and opens none of
  RH0's or RH1's stores (the package refuses them anyway).
- It does not adopt RunRegistryKit or take a fingerprint: that is the next campaign's (README §7).

---

## 6. The results note

`.documents/dk-and-rpk-migration/10-port-the-inventory.md`, using README §5.1. It holds:
- the spec table, class by class, with each leaf's and parent's source in `build`;
- the coverage placement of all 30 entries, and the GCI choice with its issue;
- the report's field table against today's (P18), and two sample reports whole (default and
  `--show-all`) from the integration store;
- U5's closures with and without the specs;
- the suites by module beside 09's; the breakages as diffs;
- "State handed to the next prompt": for 11, what `main.py --inventory` prints on a fresh store
  (its readers' step 1 now reads before Ray, and its layout differs from RH1's by design), and that
  RH0's and RH1's stores are refused by it (exit 1), so `compare_stores` remains the comparison.

**One commit**, in the repository's form, staged by explicit path only, after showing
`git diff --cached --name-only`.
