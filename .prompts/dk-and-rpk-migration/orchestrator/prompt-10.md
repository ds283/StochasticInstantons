# Orchestrator — prompt 10, port the inventory

Read [`../README.md`](../README.md) first: §0.1 items 4 and 11, §2.2 (10's charter), §5 (all rules),
§6.1 (U6, U8), §6.2 (P13, P18) and §6.3. The conventions are [`prompt-01.md`](prompt-01.md)'s §0
"Conventions", unchanged but where this note says otherwise; [`prompt-06.md`](prompt-06.md)'s
"Conventions particular to 06" hold too (git, Ray, formatting, scratch). The model is ChamPBH's 09
(its board §5.13a, §5.14 and the review below it, at `47cfcfb`); what it found that applies is in §0.

**You do not write code.** You may:
- run the suites, `ruff check` and read-only Python checks, from the session scratchpad;
- build temporary stores in the scratchpad under a private Ray (`ray.init(address="local")`), in a
  separate process, and read them with `read_inventory` and `main.py --inventory`;
- replay the results note's deliberate-breakage diffs with `git apply`, and revert them;
- fix small residue in a follow-up commit of your own (§4).

**The prompt:** [`10-port-the-inventory.md`](../10-port-the-inventory.md) · **Board items:** N1–N6 ·
**Closes:** `[show-all-flag-unused]` · **Opens:** the issue for `GradientCoupledInstanton`'s child
table that no spec reaches (U8), and only what else the work finds · **Model:** Opus, as the prompt
recommends · **No network.**

**Gate:**
- 09 landed (`f4da58f`) and was reviewed (`e81239f`): the layer is the package's, `--inventory`
  refuses with exit 2, the suites are 707 and 63.
- `HEAD` is the commit that adds this note, or a later one that touches no code.
  `git diff --stat f4da58f HEAD -- . ':!.prompts' ':!.documents'` is empty.
- No SI cluster is up, and no other session runs a suite or a Ray job from this venv, or installs
  into it, while 10 runs.

## 0. What makes this prompt unusual

**It adds a contract, not a swap.** Each spec is data the package reads, and the fingerprint
RunRegistryKit will take later reads nothing else (U8). A spec that names a wrong column is caught
by `inventory_classes` or by the column test; a spec that names the *right* columns but the wrong
identity (a leaf the lookup does not match, or a lookup column left out) is caught by nothing but
the results note's table read against each `build`. That table is what the review reads hardest.

**The orchestrator prototyped the specs before dispatch** (correction 17), by attaching them to the
registry entries at runtime in a scratch script; the repository was not touched. They hold:
`inventory_classes` accepts the registry, every column resolves, U5's 31 decisions and messages do
not move, and a two-shard store reads back with no named problem. That is a measurement, not the
agent's work: the agent derives its own table from each `build`, and the review compares.

**Where the acceptance can pass vacuously.**
- **The integration store must be the test's own, not `live_pool`'s.** Six modules write
  `FullInstanton`s and gradient rows into the session store with a stand-in trajectory whose serial
  names no row (`types.SimpleNamespace(store_id=998)` at `tests/test_datastorekit_timestamp.py:116`;
  `store_id=999` at `test_gci_parity_cheap_fetch.py:102`, `test_gci_profile_only_fetch_contract.py:123`,
  `test_gci_parity_persistence_roundtrip.py:93`, `test_gradient_coupled_instanton_end_to_end.py:376`,
  `test_plot_stability_figures.py:100`). An inventory of that store names `unresolved-parent`.
  "No named problem" is only evidence on a store built for it, in a subprocess, every parent a real
  row (the prompt's §2.3.1 says so; hold it to it).
- **A failed and a successful compute target with the same key are a `duplicate`.** Every
  compute-target `build` matches `validated == True` and no failure column, and `validate` sets a
  failed row's flag to `True` (`FullInstanton.py:338-339`, and its siblings). So the store's failed
  rows need keys of their own (another `δN★`), or the test meets a named problem it caused.
- **The report tests can pass on a renderer that prints hex.** A float leaf is `float.hex` in the
  key (`store_inventory.canonical`). Assertions are on the rendered decimal text, with the unit
  beside it, against values the test chose; never re-derived from the key.
- **"Every problem in full" passes vacuously with short problems.** The package's are about 150
  characters (correction 17). The test uses one longer than any width the renderer has, and asserts
  the whole string appears unbroken on one line.
- **The coverage test passes vacuously if it reads the specs it tests** to decide where a class
  belongs. Its three places are written out in the test; "declares a spec" is
  `inventory_spec()` returning one; "read through" checks that the named owner's spec names that
  table in that slot. Breakage 5 is the proof.
- **The `ast` test passes vacuously if it finds no `--inventory` branch.** It asserts the count (one)
  and the order, as 09's did.

**Corrections to the prompt.** Pass them on.
1. **The board section** is **`### 5.23 After prompt 10 (<date>)`**, appended after §5.22. The
   header's "Last updated" and status line are updated to match. N1–N6 are already rows in board
   §1.1; fill in their state. Closing `[show-all-flag-unused]` moves its row from board §3 to §4
   (with how). The opened issue goes into board §3. In `.documents/OPEN-ISSUES.md`: the closed row
   from §6a to §7 "Closed" (`| Issue | Closed | By |`), the new row into §6a (source "board §3 (10,
   <date>)", owner "the user (README §6.3)"), the header **60 open (one closed, one opened), 27 → 28
   closed**, the date. A name for the issue, if the agent has no better one:
   `[gci-value-table-outside-the-inventory]`.
2. **`main.py`'s lines moved at 09.** At `e81239f`: the database check `:95-97`, the provenance print
   `:99`, the refusal (comment and `if`) `:101-110`, the `--drop` `try` `:112-117`, **`ray.init`
   `:119`** (the prompt's `:100` is `91e6f31`'s). `Planck_units` is imported at `:47` and constructed
   at `:1278`, after `ray.init`; it is pure Python, so the `--inventory` branch may construct its own
   before Ray. `--drop` is `nargs="*"`, default `[]`. The other lines the prompt cites hold:
   `config/argument_parser.py:402-407`; `config/sharding.py:78-102` (the file is 102 lines); the 17
   hooks at the lines §1.4 gives; `DimensionfulQuantity.py:30`, `DimensionlessQuantity.py:30`;
   `Datastore/SQL/ObjectFactories/GradientCoupledInstanton.py:542-546`, `:556-562`;
   `tools/compare_stores.py:221-227`; the package's `:916`, `:929`, `:979` and `schema.py:359`.
3. **Version labels: today's report never prints them, and no SI key holds one.** §1.2 asks for
   "its version labels". At `91e6f31`, `_inventory_object` (`main.py:1282-1304`) prints counts, the
   timestamp range and the hooks' `labels`; the hooks collect `versions`, and nothing prints them
   (RH1's log has none). And no SI lookup matches on `version`: the five compute-target `build`s
   filter on `validated` and their parents only, and every other table either has no `version`
   column or does not match it. So `version` is a parent of no spec and no record carries it.
   **Strike "its version labels" from §1.2**: P18's bar is what today's report shows, and the field
   table records them as "collected by the old hooks, never printed; not kept: no key holds a
   version". `version` still gets its own spec (`label`), for coverage. **Do not make `version` a
   parent to print it**: that makes it identity, which SI's lookups say it is not (a rerun at a new
   label reuses the validated row).
4. **`CompactionFunction`'s two instanton parents are nullable.** Its `build` matches
   `full_instanton_serial` and `slow_roll_instanton_serial` with `== serial`, or `.is_(None)` when the
   payload has none (the scalars-only pipeline, or a side not computed). So both are
   `Parent(…, nullable=True)`; without it a NULL is an `unresolved-parent` and the row is not a
   record. The prototype's store holds one `CompactionFunction` with the slow-roll side NULL;
   `StoreInventory.resolve` gives `None` for it.
5. **Lookup details the results note's table should state** (none a stop):
   - `IntegrationSolver.build` matches `label ==` and `stepping >=` (`integration_metadata.py`), a
     minimum, not equality. The leaves are `("label", "stepping")`, as ChamPBH's and SGK's.
   - `MasslessDecoupledDiffusion.build` matches nothing: the table has no column but `serial` and
     `timestamp`, and holds at most one row. Its spec is `InventorySpec()`, with no leaf.
   - `CosmologicalParams.build` matches `name` alone, not the six floats it stores: the leaf is
     `name`.
   - `version`, `store_tag`: `label`. `version` has no `timestamp` column, so its timestamps read
     `None`.
   - The two potentials match `mass_id` and `coupling_id` alone; their `type_id` column is stored and
     not matched, so it is not a leaf.
   - The dimensionful quantities' value column is `self.value_col`, `value_PlanckMass` for all three
     entries; the dimensionless one's is `value`.
   - Every compute target matches `validated == True`, so `validated="validated"`; see §0 on failed
     rows.
6. **The polymorphic maps**, from SI's registries, imported **inside** `inventory_spec`, as
   `read_table` imports them (`InflatonTrajectory.py:321`, `FullInstanton.py:384`):
   `{t: info.table_name for t, info in POTENTIAL_REGISTRY.items()}` gives `{1: "QuadraticPotential",
   2: "QuarticPotential"}`; `{t: info.name for t, info in DIFFUSION_MODEL_REGISTRY.items()}` gives
   `{1: "MasslessDecoupledDiffusion"}`. Both equal `tools/compare_stores.py`'s maps. The diffusion
   registry is filled as a side effect of importing `MasslessDecoupledDiffusion.py` (`:69-72`), which
   `config.datastore` does before any spec is read; were it empty, `Parent` would refuse an empty
   `types` (loud, not silent). `datastorekit.store_inventory` imports only the standard library,
   `sqlalchemy` and `datastorekit.contract` at module scope, so a factory may import `InventorySpec`
   and `Parent` at its top.
7. **22 definitions serve 24 entries.** `sqla_dimensionful_quantity_factory` serves `inflaton_mass`,
   `phi_value` and `pi_value`. So the specs are 22 `def inventory_spec(self)` in 22 modules, and
   `inventory_specs(factories)` returns 24. Say both numbers (ChamPBH's RunRegistryKit adoption
   later stumbled on a count that meant the one for the other). The coverage count holds: **24 specs,
   5 read through** (`InflatonTrajectoryValue`, `FullInstantonValue`, `SlowRollInstantonValue`,
   `CompactionFunctionSamples`, and `GradientCoupledInstantonProfile` on the recommendation), **1
   excluded** (`GradientCoupledInstantonValue`): 30. No SI class is tagged (no association table), so
   `store_tag` is a spec of its own, not read through.
8. **No `cross_shard`.** Every sharded class's parents are replicated (on every shard) or are
   `CompactionFunction`'s instantons, sharded on the same `δN★`. `redshift` is in neither table list
   (`[redshift-registered-in-neither-table-list]`); the primary does not record it as replicated, so
   `read_inventory` reads it as sharded (the union). It holds no rows.
9. **U5 does not move.** With the prototype's specs installed, `tables_to_drop` over all 31 subsets
   gives exactly what it gives without them, decisions and messages: 10 closed, 21 refused. The specs'
   new edges (a trajectory to its potentials, an instanton to the diffusion model, the cosmology) all
   point at tables in no drop group. So `tests/test_tables_to_drop.py`'s bodies stay. **Its module
   docstring becomes false** (`:22-27`: "no factory declares an ``inventory_spec`` yet … Prompt 10's
   ``inventory_spec`` parents may move this table"): correct it, docstring only, as a named P13
   change; the review compares the bodies by `ast`.
10. **09's test of the refusal is two things in `tests/test_main_refusals.py`** (3 tests): the
    `inventory` case of `test_main_refuses_before_ray` (`:67-73`) and the inventory half of
    `test_both_refusals_precede_ray_init` (`:128-153`, which also asserts that nothing else reads
    `args.inventory`). Both go or change; **the `drop-full-instanton` case and the `--drop` half of
    the order test stay**, in substance unchanged. The new `--inventory` tests (exit 1, exit 2, the
    order) may go into this module, changed with a named reason and its docstring made true, or into
    a new one; say which, and give the module's count before and after.
11. **§2.1.3's grep finds more than §1.3–§1.4 list**, and none is a stop. At `e81239f`, outside
    `.prompts/` and `.documents/`, beyond the hooks, `config/sharding.py` and `main.py:101-110`:
    - `tests/test_config_datastore.py:209`, `:234`: 09's `ast` pool test, which asserts that no pool
      passes `inventory_config=`. **It stays**: a guard on the pools, it passes with the name gone;
    - `tests/test_grid_builder_integration.py:138`: a docstring ("the package's pool has no
      ``inventory()``"), still true; stays;
    - `tests/test_main_refusals.py` (correction 10) and `tests/test_tables_to_drop.py:24-27`
      (correction 9);
    - `config/datastore.py:47`, `:191`, `:199`: `_naming` already reads `inventory_specs`; stays;
    - `.claude/rules/pool-read-apis.md:1`, `:9-17`, `:72` (§1.6).
12. **The prose (§1.6) is more than the prompt names.** `.documents/FILE_MAP.md:17` lists
    `inventory_config` in `config/sharding.py`'s row, and `:41` says "dk-and-rpk-migration prompt 10
    ports it": both false after 10, both corrected, beside the new row for `tools/inventory_report.py`.
    `INFRASTRUCTURE.md` (`:183`, `:228`, `:232`, `:498`) and `architecture-summary.md` (`:194`,
    `:227`, `:394-403`, `:492-500`, `:580`) describe `pool.inventory()`; both are already on 12's
    stale list from 09. Add the lines to that list; do not edit them.
13. **Today's report, exactly** (`git show 91e6f31:main.py`, `:1227-1338`), for the field table:
    thirteen classes (`delta_Nstar`, `N_init`, `N_final`, `phi_value`, `pi_value`, `inflaton_mass`,
    `quartic_coupling`, `efold_value`, and the five compute targets); values `.6g`, the dimensionful
    ones with their unit's name; **every value shown up to 20, and 21 or more truncated to the first
    and last ten** (`n <= 20`; the prompt's "20 or more" is off by one); "no values committed" for an
    empty class; per compute target, a validated and an unvalidated line with the count and the
    timestamp range (`%Y-%m-%d %H:%M – %H:%M`), and its labels (serials, today), **more than 10
    truncated to the first five, `...`, and the last five**; `(error: …)` on an exception.
14. **ChamPBH's 09 is at `47cfcfb`**: read it with `git -C ../ChamPBH show 47cfcfb:<path>`. ChamPBH
    has moved on since (`a1c88b6`, `abccc23` changed `tools/inventory_report.py`, and `ScalarModel`
    is now `ScalarHistory`); its working tree is not 09's. SGK's `tools/inventory_report.py` is read
    at its `HEAD` (`031bcb4`, 696 lines).
15. **`read_inventory` on an absent store** raises `RuntimeError` (`Cannot read sharded datastore
    "…": the primary "…" does not exist. Nothing was read or repaired`) and creates nothing. A store
    the package refuses raises `RuntimeError` from `open_read_only` too. `main.py` catches that and
    prints `!! --inventory: <message>` on stderr, exit 1; say which exceptions it catches. Do not
    open RH0's or RH1's stores to show the refusal of an old store (§5); the absent store is the
    test.
16. **The suites at the gate** (09's review, at `f4da58f`; no Python changed since):
    **707 (706 passed, 1 skipped)** and **63 (62 passed, 1 skipped)**. The modules 10 may touch:
    `test_main_refusals.py` 3, `test_tables_to_drop.py` 9, `test_config_datastore.py` 6,
    `test_compare_stores.py` 24 (default); `test_grid_builder_integration.py` 3 (integration). No
    `slow` run unless the diff touches `ComputeTargets/`, `Numerics/` or `Interpolation/`, which it
    should not (§4 of the prompt).
17. **The orchestrator's prototype**, at `e81239f`, from the session scratchpad
    (`orch10/specs_proto.py`, `orch10/store_proto.py`; the agent may read both and owes them
    nothing). Specs attached to the registry entries at runtime: the table of corrections 4–8, the
    compute targets' parents their lookups' serial columns (`trajectory`, `N_init`, `N_final`,
    `delta_Nstar`, `atol`, `rtol`, the diffusion model by `diffusion_type`; for the gradient
    instanton also `n_collocation_points`, `alpha_regularization`, `cosmo`; for the compaction
    function `trajectory`, the two instantons, `delta_Nstar`, `cosmo`, `atol`, `rtol`), each with its
    value table and `validated`.
    - `inventory_classes`: **24 classes**, in the order `version`, `store_tag`, `redshift`,
      `tolerance`, `efold_value`, `delta_Nstar`, `N_init`, `N_final`, `n_collocation_points`,
      `alpha_regularization`, `inflaton_mass`, `quartic_coupling`, `phi_value`, `pi_value`,
      `MasslessDecoupledDiffusion`, `IntegrationSolver`, `CosmologicalParams`, `QuadraticPotential`,
      `QuarticPotential`, `InflatonTrajectory`, `FullInstanton`, `GradientCoupledInstanton`,
      `SlowRollInstanton`, `CompactionFunction`. Every leaf, parent column, type column, `validated`
      and value slot names a column `build_schema` builds.
    - **U5**: 31 subsets, 10 closed before and after, none moved (correction 9).
    - **A store**: two shards through the package's `ShardedPool` under a private Ray (the parameters
      by `object_get`), closed; then rows written with `sqlite3` (two trajectories, one per potential
      type, identical on both shards; a successful `FullInstanton` and `SlowRollInstanton` on each
      shard and a failed one with no values; two `CompactionFunction`s per shard, one unvalidated
      with its slow-roll side NULL; a gradient instanton with five profile rows). `read_inventory`
      in a fresh process: **24 classes, no named problem**, `ray.is_initialized()` `False`. With an
      orphan value row and a compaction function naming a missing instanton added: exactly
      `orphan-value: FullInstanton: 1 FullInstantonValue row(s) on shard #1 name 1 FullInstanton
      row(s) that are not there; e.g. parent serials 999` and `unresolved-parent: CompactionFunction:
      1 row(s) on shard #1 reference a parent that cannot be resolved (field(s) full_instanton), and
      are not records; e.g. serials 77`.
    The agent's own store is built through the pool end to end (the prompt's §2.3.1), not by
    `sqlite3`; the prototype's shortcut is the orchestrator's.
18. **The protected files.** The seven factory modules the prompt names, and `config/sharding.py`
    (not on `CLAUDE.md`'s list, though `pool-read-apis.md` says so: 12's item, from 09's review).
    In each: the `inventory_spec` method, its import line, the `inventory()` hook deleted with any
    import only it used (`ruff --select F401` finds them). Nothing else, not a blank line.
19. **`.prompts/INDEX.md` and the README are the orchestrator's.** The agent touches neither.

**The facts, checked by the orchestrator on 2026-10-21 at `e81239f`, 19:00–19:15 BST.** Pass them
on.
- **The tree.** Branch `dk-and-rpk-migration`, clean, `HEAD` `e81239f` before this note; `git diff
  --stat f4da58f HEAD` outside `.prompts/` and `.documents/` is empty. The 17 store files of
  prompt-01.md §1 step 5 are in the tree (ignored); 10 opens none.
- **Ray and the lock.** `ray_cluster.sh status`: lock free, no `/tmp/ray-si` process, the four ports
  free. `pgrep` finds no `gcs_server`, `raylet`, `ray::`, `pytest`, `unittest` or `main.py`.
  `RAY_ADDRESS` unset.
- **The load** was 14–15 (1 min) on 10 CPUs.
- **The venv.** `pip freeze` 83 lines, 09's; `pip check` clean. 10 installs nothing.
- **DatastoreKit** `38ebb9f`, **RayPoolKit** `17029d9`, both clean; the package's
  `store_inventory.py` is 1,045 lines at `v0.4.0`.
- **The stores.** 10 opens only temporary ones: the tests' (under `tempfile`) and its own scratch
  stores. Not the 17 in the tree, nothing under `out-*/` or `~/ScienceData/`.

**What the review exists to establish.**
- **(E1) N1, the specs.** One per covered entry (24 from 22 definitions), each matching its
  `build`'s lookup as the results note's table states: the leaves, the parents (two nullable, four
  polymorphic from the registries), `values`, `validated`; no `cross_shard`; no `version` parent.
- **(E2) N2, the report.** Renders a `StoreInventory`, reads nothing; at least today's fields
  (correction 13, less the version labels of correction 3), records by physical labels, every
  problem whole.
- **(E3) N3, `main.py --inventory`.** Before `ray.init`; exit 0, 1, 2 as the prompt says; nothing
  created; `--show-all` read.
- **(E4) N4.** The 17 hooks, `inventory_config` and `_instanton_merge` gone, nothing else in those
  files; U5 unmoved.
- **(E5) N5, coverage.** All 30 placed once, by a test that does not read what it tests; the GCI
  issue opened.
- **(E6) N6 and the records.** The prose of correction 12 true; the board and the index.
- **(E7) The verification and nothing else moved.** The tests not vacuous (§0); the suites at 707 and
  63 less the named deletions plus the new; the breakages caught; no file outside the prompt's §5
  list (with corrections 9–12); the venv, the other repositories and every store untouched.

## 1. Before you dispatch

1. **The tree.** `git status --short` clean, `git diff --cached` empty, `git log` since `f4da58f`
   records only.
2. **Ray and the lock.** `ray_cluster.sh status` clean; no Ray process.
3. **The venv.** `pip freeze` saved; `pip check` clean.
4. **The load**, recorded.
5. **Mtimes**, for check 11: the 17 store files, and every entry under `~/ScienceData/`.
   DatastoreKit's and RayPoolKit's `HEAD` and `git status --porcelain`.
6. **The measurements of §0**: the line numbers, the greps, the lookups, the prototype's specs, U5
   over the 31 subsets, the prototype store and its orphan variant, the suites by module.

**Done 2026-10-21, 19:00–19:15 BST,** at `e81239f`: all six hold, step 6 as §0 records. In `orch10/`
in the session scratchpad: `pip-freeze.txt` (83), `mtimes-stores.txt` (17),
`mtimes-sciencedata.txt` (835 entries, the root included), `specs_proto.py` and
`specs_proto.out`, `store_proto.py`, `store-a/` and `store-b/` (the prototype's stores),
`default-by-module.txt` (707), `integration-by-module.txt` (63).

## 2. Dispatch

One fresh-context subagent, on **Opus**, in the background. Give it:
- the prompt;
- the campaign README and the board;
- 09's and 06's results notes (the form of a results note, the store built in a subprocess under a
  private Ray, the provenance line);
- `HEAD`, the load and §0 of this note, up to "## 1. Before you dispatch" only, as a copy in the
  session scratchpad. It does not read `orchestrator/`, and does not read prompt 11. It may read
  `orch10/specs_proto.py` and `orch10/store_proto.py`, and owes them nothing.

Tell it plainly:
- **One commit, at the end, made once.** Its results note is
  `.documents/dk-and-rpk-migration/10-port-the-inventory.md`, in README §5.1's form, with the
  prompt's §6 additions. Stage by explicit path, and show `git diff --cached --name-only` before
  committing.
- **The files it may change** are the prompt's §5 list, with the docstring of
  `tests/test_tables_to_drop.py` (correction 9), `tests/test_main_refusals.py` as correction 10 says,
  and `FILE_MAP.md`'s two rows (correction 12). **Not** `ComputeTargets/`, the plot scripts,
  `tools/compare_stores.py`, any factory beyond its spec and its deleted hook, any other test, the
  README, `.prompts/INDEX.md`, `INFRASTRUCTURE.md`, `architecture-summary.md`, anything in another
  repository or the venv.
- **The corrections in §0**, especially 3 (no version labels, no `version` parent), 4 (nullable),
  10 (what of 09's test goes) and the vacuous-pass list.
- **Stop and ask** on any of the prompt's §4 conditions. Correction 11's hits are not stops. An
  existing test outside correction 10 that fails is current behaviour moving, never a reason to
  edit it.
- **It replies with:**
  - the results note's path and the commit;
  - `git show --stat` of the commit;
  - the spec table, class by class, as in the results note;
  - the coverage placement of the 30 entries, and the GCI issue's board and index rows;
  - `main.py`'s diff, and the report module's public function and what it reads;
  - the field table against today's report;
  - the two sample reports (default and `--show-all`), whole;
  - U5's closures with and without the specs;
  - each changed test's diff summary with its reason, and the new tests by name with what each
    asserts;
  - the breakages and what caught each;
  - the suites by module beside the gate's, with the load;
  - the prose corrected, and the stale list for 12;
  - the closed issue's §4 text and its index row;
  - every deviation with its class;
  - the "State handed to the next prompt" section, verbatim.

## 3. The review — twelve checks

1. **Scope.** `git show --stat <commit>`: the factory modules (22 with a spec, the hooks' modules
   among them), `config/sharding.py`, `main.py`, `config/argument_parser.py` if its help changed,
   `tools/inventory_report.py`, the new test module(s), `test_main_refusals.py`,
   `test_tables_to_drop.py`'s docstring, `pool-read-apis.md`, `FILE_MAP.md`, the results note, the
   board, `OPEN-ISSUES.md`. Nothing else. `git status --short` clean; one commit of the agent's since
   this note, no amend in the reflog, no leftover branch; no scratch file or store in the repository.
2. **E1, the specs against the lookups.** For every spec, read its `build`'s query beside it: each
   leaf and parent column matched there, each matched column a leaf or a parent, no stored label a
   leaf but where matched (`version`, `store_tag`, `IntegrationSolver`, `CosmologicalParams`'s
   `name`). The two nullable parents; the four polymorphic ones with their maps read from the
   registries in the method; no `cross_shard`; no `version` parent. `inventory_specs(factories)`
   24, `def inventory_spec` 22. Against `orch10/specs_proto.py`: any difference is explained in the
   results note.
3. **E4, the factory diffs.** By `ast`, each factory module at `<commit>~1` equals `<commit>`'s with
   the `inventory_spec` method, its import and the deleted `inventory()` (and the imports only it
   used) set aside: nothing else changed, docstrings included. `config/sharding.py` differs by
   `:78-102` alone.
4. **E3, `main.py`.** By `ast`, the top level: the refusal replaced by the `--inventory` branch, still
   before `ray.init`, the `--drop` `try` and every other statement as before. The branch: refuses
   `--drop` (2), reads with `read_inventory(args.database, factories)`, prints, exits 0; on the
   package's refusal prints `!! --inventory: …` on stderr and exits 1; passes `args.show_all` as
   `verbose`.
5. **E3, by running it**, from the scratchpad, `--ray-address 127.0.0.1:9`, `RAY_ADDRESS` the same,
   a timeout: on an absent store, exit 1, the message, no file; with `--drop full-instanton`, exit 2,
   no file; on the prototype's `store-a` (copied), exit 0 with a report, and with `--show-all`; no
   Ray process after. `read_inventory` of `store-b` (copied) rendered by the agent's report: both
   problems printed whole.
6. **E2, the report.** No `open`, `sqlite3`, `create_engine`, `read_inventory` or `open_read_only` in
   `tools/inventory_report.py` (by `ast`, names and attributes). Every field of correction 13 against
   the results note's field table: kept, new, changed or not kept with a reason; version labels not
   kept, as correction 3. The two sample reports in the note equal a rerun on the agent's store, if
   it is reproducible (or the note says why not).
7. **E5–E7, the tests, read.** Licence headers. The Ray-free tests leave `ray.is_initialized()`
   `False`. The integration test builds its own store in a subprocess (not `live_pool`'s), every
   parent real, both potential types, failed rows on keys of their own, and asserts no named problem
   and the rendered fields; it is `integration`-marked and says why. The report tests assert decimal
   text the test chose; the long-problem test's problem is longer than any width in the renderer.
   The coverage test's three places are literal in the test. The `ast` test counts one branch.
8. **E7, the breakages.** Replay the six diffs with `git apply` from the clean tree (`--check` and
   `-R --check` first, in `bash`); each fails what the prompt's §2.4 names (1: the column or
   resolution test, or the integration store's named problem; 2: the column test; 3:
   `inventory_classes`' `ValueError`, naming the type column; 4: the `ast` test; 5: the coverage
   test, naming the owner; 6: the coverage test, naming the class). Revert each; `git status` clean
   after.
9. **E4, U5 replayed.** `tables_to_drop` over all 31 subsets at `<commit>`: decisions and messages
   equal the pre-dispatch run (`orch10/specs_proto.out`: 10 closed, none moved).
   `test_tables_to_drop.py`'s bodies equal `<commit>~1`'s by `ast`, docstrings stripped.
   `test_main_refusals.py`: the `drop-full-instanton` case and the `--drop` half of the order test
   unchanged in substance.
10. **E7, the suites.** The agent's: default 707 less the named deletions plus the new Ray-free
    tests, all passing (1 skipped); integration 63 plus the new integration tests, all passing (1
    skipped). The orchestrator re-runs both at `<commit>`, serially. `ruff check --select
    F401,F811,F821` on every Python file the diff touches: no finding the gate did not have.
11. **E7, hygiene.** `pip freeze` equals §1's copy; `pip check` clean. DatastoreKit and RayPoolKit
    at §1's `HEAD`s, clean. The 17 store files and the 835 `~/ScienceData/` entries keep their mtimes.
    No Ray process; the lock free.
12. **E6, the records.** `pool-read-apis.md` describes `read_inventory` through `main.py --inventory`
    as now, not "from 10"; `FILE_MAP.md`'s three rows; the help of `--show-all` true. The results
    note follows README §5.1 with the prompt's §6 additions (the spec table with each `build`'s
    source, the coverage of 30, the field table, the two reports whole, U5, the suites by module, the
    breakages as diffs, the stale list for 12 with correction 12's lines, "State handed to the next
    prompt"). The board: §1 row (✅, "this commit", the results note), N1–N6, the header, `### 5.23`
    with the rollback (`git revert` alone), `[show-all-flag-unused]` §3 → §4, the GCI issue in §3.
    `OPEN-ISSUES.md`: the closed row in §7, the new row in §6a, 60 open, 28 closed, the date.

## 4. After the review

- **Record it on the board** as an *Orchestrator review of prompt 10* paragraph in §5.23: what each
  check found, and anything handed on to 11 and 12. Fix small residue in a follow-up commit of its
  own:
  - "this commit" → the SHA (board and results note);
  - this note added to the board's list of orchestrator notes, marked "used for 10";
  - `.prompts/INDEX.md`: the campaign's line (10 landed and reviewed; one issue closed, one opened).
- Anything the review finds that is not residue is opened on the board's §3 and in the index, in
  the same commit.
- **Report to the user:** the specs in one line (24 from 22, the nullable and polymorphic parents,
  no `version` parent); the coverage of 30 and the GCI issue, which is theirs (README §6.3); the
  report against today's; `--inventory`'s three exits; U5 unmoved; the suites; what goes stale for
  12.
- **Then 11** can be dispatched; its note is written after this review, at 10's commit.
