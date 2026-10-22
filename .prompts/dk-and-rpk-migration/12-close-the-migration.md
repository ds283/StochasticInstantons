# Prompt 12 — close the migration

**Campaign:** [`README.md`](README.md) · **Board items:** **Y1**–**Y7** ·
**Board:** [`IMPLEMENTATION_STATE.md`](IMPLEMENTATION_STATE.md)
**Written:** 2026-10-23, after 11's review (`2179854`, `18b490a`), as README §2.1 says. The facts
below were measured at `18b490a`. The orchestrator's note hands you any later figure, and your own
measurement governs.
**Gate:**
- 11 landed and reviewed, with **RH2, RayPoolKit G4 and DatastoreKit G4 holding** (board §2);
- on branch `dk-and-rpk-migration`, no tracked change in `git status`;
- no SI Ray process is running and the rehearsal lock is free
  (`.documents/dk-and-rpk-migration/rehearsal/ray_cluster.sh status`). You start no cluster.

**Closes:** `[test-counts-stale-in-claude-md]`, `[pool-prose-stale-after-raypoolkit-adoption]`, and the
campaign. **Opens:** only what the work finds.
**Recommended model:** **Sonnet** (README §2.2). Prose, records and measurements, and one small
sweep of comments and docstrings, each changing what a line says about a deleted path and nothing
else.

**Read first:**

1. `CLAUDE.md`, in full, and every file in `.claude/rules/`.
2. [`README.md`](README.md): §0.3, §1, §2.2 (**12's charter**), §3, §4.4, §5, §6.1, §6.2 (P6, P9,
   P10, P13–P16), §6.3 and **§7**.
3. This board in full: the header, §1, §1.1, §2 (the gates), §3 (the six open issues), §4, and
   §5.16, §5.22, §5.23, §5.28 with their reviews.
4. [`.documents/dk-and-rpk-migration/verification.md`](../../.documents/dk-and-rpk-migration/verification.md):
   the introduction, each section's first paragraph, and §3 in full.
5. The two G4 records drafted by earlier prompts: 04's results note, "The text of the RayPoolKit G4
   record, for 12 to carry into its draft" (`04-adopt-raypoolkit.md:592` on), and 11's results
   note, "State handed to the next prompt" (DatastoreKit's). And **the stale lists** of 09's and
   10's results notes ("What remains stale, for 12": `09-adopt-datastorekit.md:725`,
   `10-port-the-inventory.md:859`), from which §1.1 below is taken.
6. **The two packages, read and never edited** (`/Users/ds283/Documents/Code/DatastoreKit`,
   `/Users/ds283/Documents/Code/RayPoolKit`):
   - DatastoreKit at the tag (`git -C … show v0.5.0:<path>`): `docs/client-contract.md` (§1–§9)
     and `docs/adoption/stochasticinstantons.md` §9 (the acceptance) and §10 (what goes stale), with
     its addenda to `v0.5.0`; its extraction board's §2,
     `prompts/extraction/IMPLEMENTATION_STATE.md` (read at the checkout's `HEAD`), rows **G3** (the
     form a holding gate takes) and **G4** (the cell your draft replaces);
   - RayPoolKit at the tag `v0.2.0`: `README.md` "Using it"; and `docs/adoption/stochasticinstantons.md`
     **at the checkout's `HEAD`** (it is not in the tag) §8 (the acceptance) and §9 (what goes
     stale); its extraction board's §2, `prompts/extraction/IMPLEMENTATION_STATE.md` at `HEAD`, rows
     **G2**, **G3** and **G4**.
7. [`.prompts/INDEX.md`](../INDEX.md) and [`.documents/OPEN-ISSUES.md`](../../.documents/OPEN-ISSUES.md)
   (its header, §2 and §6a).
8. ChamPBH's close, as done (read only): `/Users/ds283/Documents/Code/ChamPBH/prompts/dk-and-rpk-migration/11-close-the-migration.md`
   and its board §5.17. It is this prompt's model; where SI differs, this prompt says so.

---

## 1. What is wanted

Both packages are adopted, RH2 equals RH1 and RH0 bit for bit through them, and both gates hold.
12 leaves the repository saying so: the instructions and the documents that describe the code
describe the packages, nothing outside the dated records names a deleted file as current, the
measurements are taken one last time, each package's gate record is drafted for its own board,
and P2 has its handover. Unlike ChamPBH, **SI owes no science-store rebuild** (README §0.3): P2
recomputes every June number anyway, and reads the June and July stores at the tag.

### 1.1 The facts (at `18b490a`)

- **Both packages' scripts**, each run from its package's root with its own venv:
  - DatastoreKit `./venv/bin/python docs/extraction/measure_client_imports.py si --commit <sha>`: the
    7 layer modules absent (the two `__init__.py` present, empty); 201 tracked `.py` files read
    outside the layer, 0 unparsed; **0** import statements, **0** string literals and **0**
    `import_module` / `__import__` calls naming a layer module; 25 factory-module imports
    (`config/` 22, `CosmologyConcepts/` 2, `tests/` 1).
  - RayPoolKit `./venv/bin/python docs/adoption/measure_client_pools.py si --commit <sha>`:
    `RayTools/` absent; 0 imports (0 naming a private name), 0 `import_module` / `__import__`
    calls; **2** string literals naming `RayTools`, both module docstrings
    (`.documents/dk-and-rpk-migration/rehearsal/stage_counts.py:16`, `tests/test_rehearsal_stage_counts.py:16`);
    **16** `RayWorkPool(...)` calls, `constructs` 16 (12 with `compute_handler=None`, 4 with one);
    402 lines of non-`.py` files naming `RayTools` or `RayWorkPool`; 1 test module;
    `ray.is_initialized()` False.
- **The suites** at `18b490a`: **868** collected; default (`-m "not integration and not slow"`)
  **732** (731 passed, 1 skipped); `integration` **67** (66 passed, 1 skipped); `slow` **69**;
  the three disjoint (`-m "slow and integration"` collects none; `-m "not integration"` 801). The
  nine `slow`-marked files are exactly `test-selection.md`'s table.
- **The venv**: `pip freeze` 83 lines; `datastorekit` 0.5.0 at `f47b9a255e9a…`, `raypoolkit` 0.2.0 at
  `eaef0ce6…`, neither editable; `pip check` clean; the provenance line is 11's.
- **The stale-path sweep** (§2.1) prints **246** lines in 21 files at `18b490a`:
  - **17 to change**, in five files: `.documents/INFRASTRUCTURE.md` `:27`, `:180`, `:190`, `:498`;
    `.documents/architecture-summary.md` `:153`, `:190`, `:197`, `:497`, `:500`, `:580`;
    `tools/compare_stores.py` `:39`, `:94`, `:115`, `:116`;
    `ComputeTargets/GradientCoupledInstanton/picard.py:452`; `tests/test_rehearsal_stage_counts.py`
    `:22`, `:26`;
  - **7 that stay**, not dated records: `tests/test_config_datastore.py:18-19` (what the literals were
    captured from, at 05: history, true) and `:209`, `:234` (the guard that no pool passes the old
    layer's arguments); `.claude/rules/pool-read-apis.md:9` (names `pool.inventory()` as gone);
    `.documents/dk-and-rpk-migration/rehearsal/stage_counts.py:26` (its line numbers are dated
    "as of dk-and-rpk-migration prompt 01's commit", and the rehearsal tooling stays RH0's, README
    §4); `.claude/memory/bug-assign-shard-keys-key-id.md:24` ("Fixed 2026-06-20: …", a dated
    record; see Y2);
  - **222 in dated records, which stay**: the results notes `01`–`10` under
    `.documents/dk-and-rpk-migration/` (219), `verification.md:28`,
    `.documents/gradient-coupled-instanton/24-prerequisite-wallclock-safeguard.md:75`, and
    `.documents/OPEN-ISSUES.md:162` (`[pool-prose-stale-after-raypoolkit-adoption]`'s hook, which
    Y7 moves to §7).
- **Beyond the sweep** (09's and 10's stale lists; the sweep catches paths, not descriptions):
  - **`.documents/INFRASTRUCTURE.md`** (502 lines; title and §1 name SI's `Datastore` and
    `ShardedPool`): §2 (`:25-55`) `DatastoreObject` from `Datastore/object.py`, without `timestamp`
    (U3); §4 (`:114-177`) "inheriting `SQLAFactoryBase`, implementing four methods" (the package's
    base has the hooks of contract §3, three defaulted, plus `inventory_spec`), and its replication
    paragraph (`:151-177`), the old layer's unrecorded replication; §5 (`:178-187`), the actor, with
    `inventory()`; §6 (`:188-235`), the pool, its method table with `inventory(cls_name, …)` and a
    line routing around the gap with it; §9 (`:351-395`), `RayWorkPool`, whose constructor sketch
    (`:357-373`) gives `create_batch_size=10`, `process_batch_size=10`, `max_task_queue=50` where
    the package's defaults are 5, 1 and 200 (`raypoolkit/RayWorkPool.py:26-29`); §12's invariant row
    "`pool.inventory()` is a reporting tool" (`:498`).
  - **`.documents/architecture-summary.md`** (582 lines): the layout (`:14-70`) lists the deleted
    layer files under `Datastore/`; "Datastore layer" (`:151-230`): `DatastoreObject`
    (`Datastore/object.py`), the factory pattern (`base.py`), the actor (with `inventory()`), the
    pool (its method table with `inventory`); "RayWorkPool" (`:319-390`), its constructor sketch
    (`:328-344`, the same 10 / 10 / 50); `main.py`'s flow (`:397-406`, `if args.inventory:
    inventory(pool, units)`); "Inventory" (`:492-504`, the four deleted helpers and
    `pool.inventory()`); the invariant row (`:580`).
  - **`.documents/FILE_MAP.md:54`**: `SQLAFactoryBase`'s protocol listed without `inventory_spec()`.
  - **Three comments in `Datastore/SQL/ObjectFactories/InflatonTrajectory.py`** (`:34`, `:289`,
    `:419`: "Ignored by SI's own layer; DatastoreKit reads it …", "SI's own layer never calls it"):
    true of a layer that is gone.
  - **`.claude/rules/pool-read-apis.md:37-39`** says `config/sharding.py` is on `CLAUDE.md`'s
    protected list; it is not, and was not at planning.
  - **`.claude/rules/datastore-factories.md`** asks nothing of a new factory's `inventory_spec()`; 10's
    coverage test (`tests/test_inventory_specs.py`) fails a registered class that no spec covers,
    reads through, or excludes with a reason.
  - **`ComputeTargets/GradientCoupledInstanton/picard.py:450-456`** (July, `b5a3a9f`) says
    `RayTools/RayWorkPool.py` is protected infrastructure and has no per-task timeout hook; the path
    is gone and the pool is not SI's to protect, but the substance holds (no `timeout` or `cancel`
    in `raypoolkit/RayWorkPool.py` at `v0.2.0`).
  - **`tools/compare_stores.py:34-39`, `:93-98`, `:113-117`**: the comments and the two
    `GLOBAL_BOOKKEEPING` reason strings cite the old layer's lines as if current. Nothing prints the
    strings: the only readers iterate the dict's keys (`tools/compare_stores.py:706`,
    `tests/test_compare_stores.py:1045`). What they describe is still true of an SI-format store (RH0's,
    RH1's, the June and July stores), whose layer is at the tag `pre-datastorekit`; and the package
    gives a **replicated** row one timestamp chosen by the pool, the same on every shard (11's
    results note, README §0.6), where the old layer called `datetime.now()` on each shard.
- **`CLAUDE.md`** (130 lines): `:27` "~464 of 571 tests"; critical rules 2, 3 and 5 (`:48-71`) cite
  only SI's rules files; "Protected infrastructure" (`:91-112`) as 09 left it, each of its 13
  entries present in the tree, and a paragraph that names `datastorekit` and the upstream rule for
  it but not `raypoolkit`. **`.claude/rules/test-selection.md`** `:10` "571 tests", `:26` "464 of 571".
- **The records.** This board: status "LIVE — 14 of 15 prompts written", row 12 "⬜" (written in
  the commit that adds this prompt). `.prompts/INDEX.md`: header "Last updated: 2026-10-19 · 6
  campaigns: 1 live, 1 halted, 4 complete; 2 more planned"; this campaign's row ends `2026-10-11 →
  2026-10-22` and `§6a; 6`; and the "Planned" paragraph ends "(its README §0.3, U7; not yet ruled)",
  stale since 2026-10-12. `.documents/OPEN-ISSUES.md`: **59 open, 29 closed**, 2026-10-22; §6a holds
  six rows, two owned by `dk-12`.

### 1.2 The items

- **Y1 — `CLAUDE.md`.**
  - **Build and test**: the default run's count at the close, the size of the suite, and the
    integration and `slow` counts, each as measured (§1.1, re-measured by you). This closes
    `[test-counts-stale-in-claude-md]`. Keep the paragraph's other sentences.
  - **Critical rules 2, 3 and 5** stay SI's rules, worded as they are, each with one added pointer to
    where the package defines the behaviour (DatastoreKit's client contract at the tag: §1 for the
    pool's table lists, §3 for the hooks, §2 for `owner_column`). Rule 5's value-table list: make it
    agree with `validate-on-startup.md`'s cascade map, or say "the value tables (see the cascade
    map)". **Point; do not copy the contract.**
  - **Protected infrastructure**: the list checked (every entry exists; none names a file of either
    package); the paragraph after it names **both** packages, each pinned to a tag in
    `requirements.txt` and never installed editable, and states the rule: **a defect in either
    package is reported to that package's repository, fixed in a new release, and reaches SI by a
    new pin prompt; it is never patched or worked around in SI** (README §5 rule 11; DatastoreKit's
    `v0.3.0` for U3 and `v0.5.0` for U12 are the precedents, in a clause).
  - Nothing else in `CLAUDE.md` changes.
- **Y2 — `.claude/rules/`.**
  - `test-selection.md`: the counts (`:10`, `:26`), as Y1. Its `slow` table stays (§1.1).
  - `pool-read-apis.md`: `:37-39`'s claim corrected (`config/sharding.py` is not protected; the
    `read_table_config` entry still needs the user's go-ahead because it changes what a pool serves —
    or drop the sentence; say which and why). The rest checked against contract §1 and §7.
  - `datastore-factories.md`: a short section, **every registered factory is covered**: a new factory
    declares `inventory_spec()` (contract §4), or its class is read through an owner's spec
    (`values` / `extra_values`) or excluded with a reason; and it gets its row in
    `tests/test_inventory_specs.py` (`EXPECTED_SPECS`, `READ_THROUGH` or `EXCLUDED`), whose coverage
    test fails otherwise. Its replication section (`:245-301`) was made the package's at 09: checked,
    not rewritten.
  - `ray-dispatch.md`, `validate-on-startup.md`, `proxy-pattern.md`, `populate-ordering.md`,
    `datastore-units.md`, `compute-targets.md`: each **checked** against the packages; a statement
    the packages make false is corrected, a pointer to the contract added where a rule restates it.
    Say file by file what you found, including "true, unchanged".
  - `.claude/memory/bug-assign-shard-keys-key-id.md` and `shard-key-assignment-bug.md` (DatastoreKit
    checklist §10): dated records of a fix in a file that is now the package's. If either does not
    already say where the fix lives now, add **one dated line** saying so
    (`datastorekit/SQL/ShardedPool.py`, `_assign_shard_keys`, both of SI's commits present, as the
    checklist's §10 states); edit nothing else in them.
- **Y3 — the documents** (P13; DatastoreKit checklist §10; RayPoolKit checklist §9).
  - **`.documents/INFRASTRUCTURE.md` and `.documents/architecture-summary.md`**: the sections §1.1
    lists, **rewritten for the packages**. Say what SI supplies — `config/datastore.py` (the registry
    of factory instances, the drop groups and `tables_to_drop` (U5), the batch sizes),
    `config/sharding.py` (the table lists, the shard key, `vectorized_shard_key`), each factory's
    `register`, `build` and, where it defines them, `store`, `validate`, `validate_on_startup`,
    `revalidate` and `inventory_spec` — and what each package does (DatastoreKit: the pool, the actors,
    the broker, the recorded replicated write and the check at open, the read-only reader and
    `read_inventory`, `copy_store` / `delete_store`, the two tools; RayPoolKit: the work queue and its
    handlers), with **pointers to the contract and the README at the tag, not copies of them**. The
    `RayWorkPool` constructor sketches give the package's defaults, or say they are examples (this
    closes `[pool-prose-stale-after-raypoolkit-adoption]`'s part 2). Keep, re-pointed, what is SI's
    and still true (the two-pass dispatch, the proxies, the multi-table invariants, the units
    discipline). Each rewritten section begins with a dated note: rewritten 2026-10-<dd> by this
    campaign's prompt 12; the layer it described is in git at the tag `pre-datastorekit`. Dated notes
    already in a file are records and are not edited.
  - **`.documents/FILE_MAP.md`**: `:54` gains `inventory_spec()`; every row checked against the tree.
  - **Every other line** in those three files that names `RayWorkPool`, `ShardedPool`, `Datastore` or
    a factory hook is read and left if it is true. Say so in the results note, by line or by section.
- **Y4 — the prose in code**, §1.1's list, and only that.
  - `tools/compare_stores.py`: the comments and the two reason strings cite the old layer **at the
    tag** (`pre-datastorekit:Datastore/SQL/…`), as the layer of an SI-format store, and the package's
    file where they speak of a package store (`datastorekit/SQL/…` in the installed package, which
    equals the tag); the `timestamp` reason states the replicated case in as few words as it takes.
  - `ComputeTargets/GradientCoupledInstanton/picard.py:450-456`: the pool is `raypoolkit`'s, a
    package (`CLAUDE.md`'s rule of Y1), with no per-task timeout or cancel hook at `v0.2.0`; the rest of
    the comment stays. This closes the issue's part 1.
  - `tests/test_rehearsal_stage_counts.py:20-27` (the module docstring, named here under README §5
    rule 7): the fixtures were built from the lines of `RayTools/RayWorkPool.py` and SI's actor at
    01's commit; since 04 and 09 the packages print the same lines (07's and 11's `stage_counts.py`
    runs). Past tense where it is history; nothing else.
  - `Datastore/SQL/ObjectFactories/InflatonTrajectory.py:34`, `:289`, `:419`: what the line says of
    the old layer is history or goes; what it says of DatastoreKit stays.
  - **Prose only:** each touched Python file's `ast` is unchanged but for the two string values of
    `GLOBAL_BOOKKEEPING` and the test's module docstring (§2.2). `ruff check --select F401,F811,F821`
    gives each file's count at `18b490a`; no reformatting (README §5 rule 15).
- **Y5 — the final measurements**, saved under `.prompts/dk-and-rpk-migration/measure/out/12-*`:
  - both packages' scripts at your working `HEAD` (they read a commit, not the working tree: run them
    on the commit you start from, and say so; the orchestrator re-runs them at your commit), each
    against §1.1's figures; the RayPoolKit literal count may move with Y4's docstring, and you say
    whether it did;
  - the suites by marker (§2.5), against §1.1;
  - `pip freeze` against 10a's (83 lines), `pip check`, and the provenance line.
- **Y6 — `verification.md` §4, "The close"**, appended after §3:
  - a table of RH0, RH1 and RH2: the tree (commit), the packages (none / `raypoolkit` / both, at
    their commits), the stores, each build's end (exit status), each comparison's result and
    `scalar_data.csv`'s hash, from §1–§3;
  - Y5's measurements;
  - **the two G4 records, drafted** for the packages' extraction boards (P14), each a fenced block
    ready to paste, **in that board's own form**:
    - **DatastoreKit's G4 cell** in the form of its G3 cell: `✅ 2026-10-22: holds. SI adopted
      \`v0.5.0\` …`, mapping each part of the checklist's §9 (with the `v0.4.0` addendum's "`v0.3.0`
      or later", standing in the `v0.5.0` addendum) to the SI commits and the rehearsal that hold it,
      from 11's record (as reviewed, naming `2179854`), and Y5's script figures; then the cell's
      existing dated italic notes, **verbatim**;
    - **RayPoolKit's G4 cell** in the form of its G2 and G3 cells: `**holds** 2026-10-20: SI adopted
      \`v0.2.0\` …`, the five parts of the checklist's item 8 mapped to `ef13445` (04), `5396a3d` (03)
      and the scripts' figures, from 04's record, then RH1 (`0527480`) and RH2 (`2179854`) as the runs
      under real Ray, then the checklist pointer the cell carries now.

    **Neither is committed in its repository**: the user makes those commits, or has a session there
    make them.
  - a closing list: each item of DatastoreKit's checklist §10 and RayPoolKit's §9 ("what goes stale"),
    and where it was done (04, 09, 10, 10b or 12) or why it is left (a dated record).
  **The handover to P2**, as `verification.md` §4's last subsection (still Y6), README §7 carried as
  P2's starting facts:
  - every SI store written before `f4da58f` is refused by the tree (U31): the June stores (named in
    README §0.2), the July `phase_a` stores, `test-gradient.sqlite`, RH0's and RH1's. They stay on
    disk, readable by `tools/compare_stores.py` at any commit after 01, and by the tree at the tag
    `pre-datastorekit` (`0527480`, pushed);
  - **how P2's first prompt (`[hfp-closed-form-audit-not-run]`) reads them**: from a worktree at the
    tag that uses the main checkout's venv, where both packages are installed and the tag's tree
    imports `raypoolkit` and its own layer (§2.6 checks this); read only, never resumed, since a June
    store pruned after an interrupted run may hold orphans (`[inflaton-trajectory-prune-orphans-value-rows]`,
    closed at 06 for new builds only); every driver needs `--ray-address`;
  - P2's own builds go through the packages into fresh stores, on SI's isolated cluster under the
    rehearsal lock (`ray_cluster.sh`, `--ray-address 127.0.0.1:6390`, never `ray stop`);
    `tools/compare_stores.py` is the comparison of P2's rebuilt grids with the June ones, where a
    difference is the expected result;
  - what the package adds for P2: `main.py --inventory` (read-only, before Ray), `python -m
    datastorekit.tools.shard_key_audit`, `python -m datastorekit.tools.sharded_store copy`, and
    `ShardedPool.closed_store_files` / `delete_store`;
  - the issues this board leaves open, with their owners (Y7), and RunRegistryKit as the next
    infrastructure campaign (README §7, last bullet);
  - the decisions left to the user (below).
- **Y7 — the records.**
  - **This board closes.** Status line **COMPLETE**, with the final suite counts; row 12 ✅ with "this
    commit" and its results note; Y1–Y7 in §1.1; §2 gains no gate, but a line after the table that the
    two package records are drafted in `verification.md` §4 (P14); the two issues move from §3 to §4,
    each with how; §3 keeps its four other issues (`[plot-scripts-stale-version-label]` P2,
    `[redshift-registered-in-neither-table-list]` unowned, `[unified-pipeline-stores-null-instanton-labels]`
    unowned, `[gci-picard-inner-fails-on-rehearsal-grid]` P3), unchanged; a final
    `### 5.30 After prompt 12 (<date>)`, listing every issue the campaign leaves open with its owner,
    and every decision left to the user.
  - **`.prompts/INDEX.md`**: this campaign's row **complete**, in the form of its neighbours, with the
    dates, the final suites and `§6a; 4` by counting; the header's count ("0 live", and the rest by
    counting) and date; the "Planned" paragraph's last sentence made true (U7 ruled; the tag made and
    pushed; Phase 2 reads the June and July stores there).
  - **`.documents/OPEN-ISSUES.md`**: the two rows move from §6a to §7 (`| Issue | Closed | By |`, the
    form of `[gci-value-table-outside-the-inventory]`'s row); the header's count (**57 open, 31
    closed**, by counting) and date; the sentence "One campaign has a status board
    (`dk-and-rpk-migration`, §6a)" made true of a closed board; §6a's lead-in if it states the
    campaign's state. `[hfp-closed-form-audit-not-run]`'s hook (§2) may gain a pointer to Y6's handover; no
    other row moves.

**Left for the user, not done here** (README §6.3): the merge of `dk-and-rpk-migration` into `main`
(P15); the two G4 commits in the package repositories (P14); removing the rehearsal stores (§3;
RH0's, RH1's and RH2's, about 25 MB each, under `~/ScienceData/StochasticInstantons-rehearsals/`);
the plot scripts' label and pools (P9, P10; `[plot-scripts-stale-version-label]`); renaming the
`Datastore` package (P6).

---

## 2. Verification

1. **The stale-path sweep.** Over `git ls-files` outside `.prompts/`, a regex for the deleted names
   in path and dotted form — `Datastore/object.py`,
   `Datastore/SQL/{ShardedPool,Datastore,ClientPool,SerialPoolBroker,ProfileAgent}.py`,
   `ObjectFactories/base(.py)`, `Datastore.object`, `Datastore.SQL.{ShardedPool,…}`, `RayTools`,
   `inventory_config`, `drop_actions`, `_drop_order`, `pool.inventory(`, `_default_store_handler`,
   `_default_serial_batch_size` — with a lookbehind that keeps `datastorekit/…` and `datastorekit.…`
   out. The orchestrator's note gives its script; use it or your own, and quote it in the results
   note. **Before any edit** it prints §1.1's 246 lines (the non-vacuity). **After**: the 7 + 222 lines
   §1.1 says stay (less any line Y7 moves, at its new place), and any new line of yours that names a
   deleted path *as deleted* (a dated note, `verification.md` §4, a closed issue's row), each
   classified in the results note. A line that names one as current is a miss.
2. **Y4 changes prose only.** For each Python file Y4 touches: `ast.dump` of the module with docstrings
   removed is identical before and after, **except** `tools/compare_stores.py`, whose dump differs
   only in the two `GLOBAL_BOOKKEEPING` values (show the differing nodes); and the test module,
   compared with its module docstring removed. Comments are not in the AST, so name each file's
   changed lines from `git diff -U0`.
3. **The documents.** `git diff --numstat` on `.documents/`: deletions only in `INFRASTRUCTURE.md`,
   `architecture-summary.md`, `FILE_MAP.md` and `OPEN-ISSUES.md`; none in `verification.md` or any
   results note (README §5 rule 6). Every path, function, section and line you cite in Y1–Y3 and Y6
   exists at the tag or in the tree; give the list in the results note.
4. **The index.** `.documents/OPEN-ISSUES.md`'s count equals its rows by counting (say how); §6a's rows
   agree with this board's §3; `.prompts/INDEX.md`'s row agrees with this board.
5. **The suites**, serially, in the foreground, **before** and **after** your edits:
   `./venv/bin/python -m pytest -m "not integration and not slow" -q -p no:cacheprovider` and
   `RAY_ADDRESS=local ./venv/bin/python -m pytest -m integration -q -p no:cacheprovider`: §1.1's counts
   both times. **And once after**, because Y4 touches `ComputeTargets/` (`.claude/rules/test-selection.md`):
   `./venv/bin/python -m pytest -m slow -q -p no:cacheprovider`, 69 passed (S1's), in the background,
   waited on by notification. `ruff check --select F401,F811,F821` on every touched Python file, as at
   `18b490a`.
6. **The tag still reads the old stores** (the handover's premise), with no store opened and no
   worktree made: `git archive pre-datastorekit | tar -x -C <scratchpad>/tag`, then from that
   directory, with the main checkout's venv and `-I` plus the directory put on `sys.path` in the code:
   `import config.datastore`, `from Datastore.SQL.ShardedPool import ShardedPool`, `from raypoolkit
   import RayWorkPool`; `ray.is_initialized()` False. The extracted tree is deleted afterwards.

---

## 3. Acceptance

1. Y1–Y7 as §1.2 says.
2. §2.1's sweep prints the 246 lines before, and after only the lines §2.1 allows, each classified.
3. §2.2 holds for every touched Python file.
4. The index's count and date agree with its rows; this board, `.prompts/INDEX.md` and
   `.documents/OPEN-ISSUES.md` agree with each other (README §2.2, 12's acceptance 1).
5. Nothing outside `.prompts/` and the dated `.documents/` records names a deleted file as a current
   path (12's acceptance 2).
6. The default and integration runs pass at §1.1's counts, before and after; the `slow` block 69 after
   (12's acceptance 3).
7. §2.6 imports, and nothing is left of the extracted tree.
8. **No deliberate breakage beyond §2.1's non-vacuity run**: 12 adds no code and no test.
9. **One commit**, with the results note `.documents/dk-and-rpk-migration/12-close-the-migration.md` in
   README §5.1's form.

---

## 4. Stop conditions — stop and ask

- A gate of board §2 does not hold when you start, or a §1.1 figure differs at your `HEAD`.
- A line that §2.1 finds is code, not prose, or a Y4 line cannot be made true without changing what
  the code does.
- A sentence of a dated record (a results note, `verification.md` §1–§3, a `> **Note, …**` block, a
  handoff note) would need rewriting rather than adding to.
- A document or rule would need a statement about a package that neither its contract or README at
  the tag nor the installed package bears out.
- Any suite count moves, or a `slow` test fails.
- §2.6 does not import.
- Anything would need an edit in DatastoreKit, RayPoolKit, ChamPBH or SecondaryGWKit.

---

## 5. What this prompt does not do

- **Files it changes:** `CLAUDE.md`; `.claude/rules/test-selection.md`, `pool-read-apis.md`,
  `datastore-factories.md`, and any other rule file Y2 finds false (named in the results note);
  `.claude/memory/bug-assign-shard-keys-key-id.md` and `shard-key-assignment-bug.md` (one dated line
  each, if needed); `.documents/INFRASTRUCTURE.md`, `architecture-summary.md`, `FILE_MAP.md`;
  `tools/compare_stores.py`, `ComputeTargets/GradientCoupledInstanton/picard.py`,
  `Datastore/SQL/ObjectFactories/InflatonTrajectory.py` and `tests/test_rehearsal_stage_counts.py`,
  prose only; `.documents/dk-and-rpk-migration/verification.md` (§4 appended);
  `.documents/OPEN-ISSUES.md`; `.prompts/INDEX.md`; this board; the results note;
  `measure/out/12-*`. Nothing else: not the README, not the rehearsal scripts, not any other test.
- It runs no build, opens no store (not even read-only), starts no Ray cluster (the integration suite's
  private instances aside), installs nothing, and edits nothing outside this repository.
- It does not merge the branch, push anything, or make a commit in a package repository.

**One commit**, in the repository's form, staged by explicit path only, after showing
`git diff --cached --name-only`.

---

## 6. The results note

`.documents/dk-and-rpk-migration/12-close-the-migration.md`, using README §5.1. It holds:
- the gate and §1.1's figures as you measured them;
- Y1–Y4, file by file: what changed and why, and what was checked and left true;
- the sweep's script, its before and after outputs, and the classification of every line after;
- §2.2's `ast` comparison and `git diff -U0` lines per Python file;
- the list of cited paths and lines (§2.3);
- Y5's measurements, and the suites before and after, with the load;
- §2.6's output;
- the two G4 drafts (as in `verification.md` §4);
- "State handed to the next prompt": for P2 (the handover, in brief) and for the user (the decisions
  left, with the two G4 commits first).
