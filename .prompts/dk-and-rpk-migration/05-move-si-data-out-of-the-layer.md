# Prompt 05 — move SI's data out of the layer

**Campaign:** [`README.md`](README.md) · **Board items:** **M1**–**M6** ·
**Board:** [`IMPLEMENTATION_STATE.md`](IMPLEMENTATION_STATE.md)
**Written:** 2026-10-20, with prompts 06 and 07, after 02's review (board §5.13).
**Gate:**
- 04 landed and reviewed (board §1), with RayPoolKit's G4 recorded in board §2;
- on branch `dk-and-rpk-migration`, no tracked change in `git status`;
- no SI cluster is up (`.documents/dk-and-rpk-migration/rehearsal/ray_cluster.sh status`), and
  the venv holds `raypoolkit` 0.2.0 at `eaef0ce6…` and no `datastorekit`.

**Closes:** nothing. **Opens:** only what the work finds.
**Recommended model:** **Sonnet**. Three objects moved verbatim into a new module, three imports in
the layer, one helper, fifteen call sites and four test stubs, each measured.

**`Datastore/SQL/Datastore.py`, `Datastore/SQL/ClientPool.py` and `config/sharding.py` are named
here.** The first two are on `CLAUDE.md`'s protected list (`CLAUDE.md:89-112`), and
`.claude/rules/pool-read-apis.md` treats the third as protected. §1 says exactly what changes in
each, and nothing else in them may change (README §5 rule 15).

**Read first:**

1. [`README.md`](README.md): §0.1 items 1 and 3, §1, §2.2 (05's charter), §4 (what 05 ships), §5,
   and §6.2 (P8, P12, P13).
2. DatastoreKit's checklist for SI, `/Users/ds283/Documents/Code/DatastoreKit/docs/adoption/stochasticinstantons.md`,
   items 3 and 4, and `docs/client-contract.md` §1's rows for `factories`, `serial_batch_sizes`
   and `drop_tables`, read at the tag (`git -C <DatastoreKit> show v0.4.0:<path>`). They are why
   the data moves, and the shape 09 will hand it to the package in. **Read; edit nothing in that
   repository** (README §5 rule 12).
3. `Datastore/SQL/Datastore.py`: the factory imports (`:28-86`), `_factories` (`:96-127`),
   `_drop_actions` (`:133-143`), `_drop_order` (`:144-147`), and every use of the three names
   (`:192`, `:411-414`). Note that the method `Datastore._drop_actions` (`:402`) shares its name
   with the module-level dict it reads.
4. `Datastore/SQL/ClientPool.py`: `_default_serial_batch_size` (`:24-54`) and its one use, with
   SI's fallback of 5 (`:172`).
5. `Datastore/SQL/ShardedPool.py:584-610`, `object_get_vectorized`, which already accepts the
   mapping form (`:597-605`).
6. `config/sharding.py`, in full.
7. The 15 calls and four stubs of §1 (M3, M4), and `plotting/fetch.py`'s `fetch_over_grid`.
8. Prompt 02's results note (`.documents/dk-and-rpk-migration/02-rehearse-the-start-tree.md`),
   "State handed to the next prompt": the start tree's schema snapshot is
   `.documents/dk-and-rpk-migration/out/02-reference-schema.json`.
9. ChamPBH's 05, as done, if it has landed (read only): its board's "After prompt 05" and the
   review below it, in `/Users/ds283/Documents/Code/ChamPBH/prompts/dk-and-rpk-migration/IMPLEMENTATION_STATE.md`.
   Its `config/datastore.py` is the model for the module's shape; SI's differs in holding
   instances (README §0.1 item 2) and five drop groups.

Line numbers below are at `7ceb089`. 04 moves `main.py`'s by a few lines; re-measure (§2.1).

---

## 1. What is wanted

DatastoreKit takes a client's data as arguments: `ShardedPool(factories=…, serial_batch_sizes=…,
drop_tables=…)`. SI's lives inside its layer, which 09 deletes. This prompt moves it out first,
on SI's own layer, so that 09 only has to pass it on. Nothing that is stored, and no schema,
changes.

- **M1 — a new `config/datastore.py`** holds three objects, each moved **verbatim** from the
  layer, with the imports it needs:
  - `factories`: the registry `_factories`, all 30 entries in their order, each an instance
    constructed exactly as today (`sqla_dimensionful_quantity_factory(inflaton_mass)` and so on);
  - `drop_groups`: `_drop_actions`'s five groups, each list in its order;
  - `serial_batch_sizes`: `_default_serial_batch_size`, all 29 entries, `redshift` and
    `temperature` included (P12).

  This is SGK's and CPBH's module name for the same data. The module gets the licence header the
  other `config/` modules carry, and a docstring saying what each object is and that the layer
  (and from 09 the package) reads it. It may be formatted with `ruff format` (README §5 rule 15).
- **M2 — the old layer imports them from there**, under the names it uses today, so that no line
  that reads them changes:
  - `Datastore/SQL/Datastore.py`: `from config.datastore import factories as _factories,
    drop_groups as _drop_actions`, in place of the two definitions. **The aliases are the
    point:** `register_factories(_factories)` (`:192`) and the method `_drop_actions` (`:411-414`)
    stay byte for byte as they are.
  - Each factory import of `:28-86` that nothing left in `Datastore.py` uses moves with the
    registry. One still used in the file (for example `SQLAFactoryBase`, in
    `_FactoryMappingType`) stays. Decide by reading, and check by M2's lint (§2.3.2).
  - `_drop_order` stays in `Datastore.py`. 09 deletes it with the file, since the package orders
    a drop by foreign key.
  - `Datastore/SQL/ClientPool.py`: `from config.datastore import serial_batch_sizes as
    _default_serial_batch_size`, in place of the definition. `:172`, with **SI's fallback of 5**,
    stays as it is (the package's is 500; README §0.1 item 1).
  - Nothing else in either file changes: no reformatting, no reordering, no renaming.
- **M3 — the 15 vectorized gets pass a mapping** (P8). `config/sharding.py` gains one function and
  changes nothing else:
  ```python
  def vectorized_shard_key(key) -> dict:
      """The shard key of a vectorized get, in the mapping form both layers take."""
      return {"delta_Nstar": key}
  ```
  with a comment saying the field name is `sharded_tables`' value for every sharded class, and that
  DatastoreKit accepts only this form. Each call then passes `vectorized_shard_key(<its key>)` in
  place of `<its key>`. Nothing else in a call changes, and each file gains one import. The calls,
  at `7ceb089`:
  - `main.py` 10: `:226`, `:254`, `:321`, `:450`, `:594`, `:876`, `:905`, `:969`, `:1020`,
    `:1046` (each a `task_builder=lambda key: pool.object_get_vectorized(…)`);
  - `plot_InstantonSolutions.py` 3: `:698`, `:701`, `:734`;
  - `plotting/fetch.py` 2: `:127` and `:166`. In `fetch_over_grid` the bare key stays the key of
    `by_shard` and `refs`; only the argument to the call is wrapped.

  `main.py:421` and `plotting/fetch.py:143` are docstrings, not calls.
- **M4 — the four test stubs take the mapping** (a named exception to README §5 rule 7). Each
  stub's `object_get_vectorized(self, class_name, shard_key, payload_data)` now receives a dict:
  - `tests/test_plot_adapters_golden.py:1001-1015`, `_MultiClassStubPool`, keys its canned
    responses by `(class_name, shard_key)`. A dict is not hashable, so it looks up
    `(class_name, shard_key["delta_Nstar"])`. Its `self.calls` records what it was given; any
    assertion on a recorded key reads the field.
  - `tests/test_plot_extraction_golden.py:381` (`_StubPool`), `:450` (`_ShardedStubPool`) and
    `:477` (`_RecordingStubPool`). `:450`'s test asserts `{call[1] for call in pool.calls} ==
    {"a", "b"}`, which now raises on a dict; it reads `call[1]["delta_Nstar"]`. Check every
    assertion on `calls` in the three tests that use them.

  Each stub changes only where it reads the key, and each test keeps what it asserts. Record each
  change, with the line, in the results note. If a fifth stub or test turns out to need a change,
  stop: README §5 rule 7 names only these four.
- **M5 — the new tests** (§2.3.3), in new files with the licence header.
- **M6 — the prose this commit makes false** (P13):
  - `.documents/FILE_MAP.md:41`: the `Datastore.py` row says the actor "owns the factory
    registry". It now registers the factories of `config/datastore.py`; say so, and change nothing
    else in the row;
  - `.documents/FILE_MAP.md`'s `config/` rows (`:17-22`) gain one for `config/datastore.py`, in the
    same form, and `:17`'s `config/sharding.py` row names `vectorized_shard_key`.

  Leave `CLAUDE.md` and `.claude/rules/` alone: nothing in them names the three objects (§2.1.4
  checks this), and 09 and 12 rewrite them.

---

## 2. What to do

### 2.1 Before

1. **Capture the data as it is**, at the gate's `HEAD`, into your scratch directory, by a short
   script that imports `Datastore.SQL.Datastore` and `Datastore.SQL.ClientPool` (no Ray is
   started):
   - the registry: for each entry in order, its name, `type(factory).__name__`, and for the two
     quantity factories the class they hold (`factory.ObjectType.__name__`);
   - the five drop groups and `_drop_order`;
   - the 29 batch sizes.

   This is what M5's first test is written from, **literally**, not computed from the module it
   tests. Keep the script and its output in the results note.
2. **The 15 calls.** `git grep -n object_get_vectorized -- '*.py'` lists the 15 calls of M3, the
   two docstrings, the definition in `ShardedPool.py` and the four stubs, and nothing else. If it
   lists another call, stop.
3. **The registry's tables and the batch sizes.** Record which registered names have no batch
   size, and which batch sizes name no registered table. At `7ceb089`:
   - registered, no size: `version`, and `InflatonTrajectoryValue` (`"serial": False`,
     `Datastore/SQL/ObjectFactories/InflatonTrajectory.py:390`, so it leases none);
   - a size, not registered: `temperature` (a ChamPBH leftover; it moves verbatim, P12).

   For each registered name without a size, record whether its table has a `serial` column, and so
   whether it leases serials under SI's fallback of 5. The README expects none but `version` to
   lease without a size; record what you find, including whether `version` leases. This is data for
   09, which hands the sizes to a package whose fallback is 500; do not add an entry.
4. `git grep -n -e "_factories" -e "_drop_actions" -e "_default_serial_batch_size" -- ':!.prompts'`
   lists only the two layer files (and nothing in `CLAUDE.md`, `.claude/` or `.documents/` outside
   dated records). If a current document names them, add it to M6 and say so.
5. `./venv/bin/ruff check --select F401,F811,F821 Datastore/SQL/Datastore.py
   Datastore/SQL/ClientPool.py`, saved. M2's lint (§2.3.2) compares with it. (If `ruff` is not in
   the venv, use whatever `ruff` is on the path and record which.)

### 2.2 The change

M1–M6, as §1 says. Do not reformat any existing file you touch: the diff of each is only the lines
§1 names.

### 2.3 Verification

1. **The schema does not change.** Build a temporary store with SI's own `ShardedPool`, at the
   staged tree, in a `tempfile` directory outside the repository:
   - under a private Ray, `ray.init(address="local")`, as the integration suite's form does
     (README §5 rule 17). No cluster is started with `ray start`, and `ray stop` is never run;
   - with `config.sharding`'s tables, two shards, `prune_unvalidated=False`, `drop_actions=[]`,
     and no profile agent; opened and closed, nothing stored.

   Then `./venv/bin/python tools/compare_stores.py --snapshot <tmp>.sqlite --out
   .documents/dk-and-rpk-migration/out/05-temp-schema.json`, and `--schema <tmp>.sqlite --against
   .documents/dk-and-rpk-migration/out/02-reference-schema.json`: "the schemas agree", exit 0. If
   the tool reports a difference that the shard count alone explains, show it and say why; any
   other difference is a stop. Delete the temporary store afterwards; it is the only store this
   prompt opens.
2. **The layer is unchanged but for its imports.**
   - `git diff` of `Datastore/SQL/Datastore.py` removes the factory imports §1 moved, `_factories`
     and `_drop_actions`, and adds the one `from config.datastore import …` line; of
     `ClientPool.py`, it removes the dict and adds the one import. Nothing else.
   - §2.1.5's `ruff` run, repeated: no new finding. In particular no `F821` (a name the move left
     undefined) and no `F401` (an import the move left unused).
   - `./venv/bin/python -c "import Datastore.SQL.Datastore, config.datastore"` succeeds: there is
     no import cycle. If there is one, stop: breaking it would change more than §1 names.
3. **The new tests** (no Ray; in the default run):
   - **`tests/test_config_datastore.py`.** `config.datastore`'s three objects equal §2.1.1's
     capture, written out literally: the registry by name, order, factory class and held quantity
     class; the drop groups; the batch sizes. And the layer reads them from there:
     `Datastore.SQL.Datastore._factories is config.datastore.factories`, the same for
     `_drop_actions` and `drop_groups`, and `Datastore.SQL.ClientPool._default_serial_batch_size is
     config.datastore.serial_batch_sizes`. Importing `Datastore.SQL.Datastore` starts no Ray;
     assert `ray.is_initialized()` is `False` at the end.
   - **`tests/test_vectorized_shard_key.py`.**
     - `vectorized_shard_key(k) == {"delta_Nstar": k}`, and its key equals every value of
       `config.sharding.sharded_tables`.
     - An `ast` test (P8): it parses every `.py` file in the tree outside `tests/`, `venv/`,
       `.prompts/` and `.documents/`, and finds every call whose function is an attribute named
       `object_get_vectorized`. It asserts there are **15**, and that each passes, as its shard key
       (the second positional argument, or `shard_key=`), a call of `vectorized_shard_key`. A
       failure names the file and line.
4. **The suites** (`.claude/rules/test-selection.md`; the diff touches none of its slow paths): the
   default run gives 04's count plus the new tests, all passing; `RAY_ADDRESS=local
   ./venv/bin/python -m pytest -m integration` gives 04's (61; 60 passed, 1 skipped). The four
   changed stubs' tests pass. The integration run builds `live_pool` through the moved registry,
   so it is also the check that the layer finds its data.
5. The three drivers byte-compile (`./venv/bin/python -m py_compile main.py
   plot_InstantonSolutions.py plot_GradientCoupledSolutions.py plotting/fetch.py`).

### 2.4 Deliberate breakage (README §5 rule 8)

Each is applied to the working tree, shown to be caught, reverted, and recorded as a diff that
`git apply` replays:
1. **One vectorized get reverted to the bare key** (say `plotting/fetch.py:166`): the `ast` test
   fails, naming the line.
2. **A batch size changed** (say `"FullInstantonValue": 500` → `400` in `config/datastore.py`):
   `test_config_datastore.py` fails, naming the table.
3. **A registry entry given another quantity type** (`"inflaton_mass":
   sqla_dimensionful_quantity_factory(phi_value)`): `test_config_datastore.py` fails, naming the
   entry.
4. **The layer given a registry of its own again** (`_factories` redefined in `Datastore.py` as a
   copy): the identity assertion fails.
5. **One stub's lookup left on the bare key** (`_MultiClassStubPool` keyed by `(class_name,
   shard_key)`): its test fails with `TypeError: unhashable type: 'dict'`, which is why M4 exists.

---

## 3. Acceptance

1. **M1:** `config/datastore.py` holds `factories` (30), `drop_groups` (5) and
   `serial_batch_sizes` (29), equal to the layer's at the gate (§2.3.3).
2. **M2:** the layer reads them from there (the identity test), and §2.3.2's diff and lint hold.
3. **The schema does not change** (§2.3.1), and the snapshot is saved.
4. **M3:** 15 calls, each through `vectorized_shard_key` (the `ast` test); `git diff` of each
   call site is the wrapped argument and the file's one import.
5. **M4:** the four stubs, and nothing else under `tests/` but the two new files.
6. **The suites** give 04's counts plus the new tests.
7. **M6:** `git diff .documents/FILE_MAP.md` is the lines §1 names.
8. **The breakages of §2.4** are caught, and recorded as diffs.
9. **The records**, in the same commit:
   - this board: the §1 row for 05, items M1–M6, and `### 5.N After prompt 05 (<date>)`, N the
     next free number in §5;
   - §2.1.3's finding, under "State handed to the next prompt", for 09;
   - a §3 entry for anything opened, with `.documents/OPEN-ISSUES.md` in the same commit.

---

## 4. Stop conditions — stop and ask

- `git grep` finds a vectorized call, or a stub, beyond §1's.
- The move needs a change to the layer beyond §1's imports: an import cycle, a name the layer
  reads that the aliases do not cover, or a factory import still used elsewhere in `Datastore.py`
  that cannot stay.
- The temporary store's schema differs from RH0's `reference` other than by the shard count.
- Any suite's count or result moves, other than by the new tests.
- An existing test other than the four stubs would need a change.

---

## 5. What this prompt does not do

- **Files it changes:**
  - new: `config/datastore.py`, `tests/test_config_datastore.py`,
    `tests/test_vectorized_shard_key.py`, `.documents/dk-and-rpk-migration/out/05-temp-schema.json`;
  - `Datastore/SQL/Datastore.py` and `Datastore/SQL/ClientPool.py`, as M2 says;
  - `config/sharding.py`, the one function;
  - `main.py`, `plot_InstantonSolutions.py`, `plotting/fetch.py`: the 15 wrapped arguments and one
    import each;
  - the four stubs in `tests/test_plot_adapters_golden.py` and `tests/test_plot_extraction_golden.py`;
  - `.documents/FILE_MAP.md`, as M6 says;
  - the results note and this board.

  Nothing else.
- It changes no factory, no schema and no stored value; `redshift` stays registered and
  `temperature` keeps its size (P12).
- It does not touch `_drop_order`, the pool constructions, `drop_actions=`, `inventory_config` or
  `live_pool`: those are 09's and 10's.
- It does not install `datastorekit`, runs no build and starts no Ray cluster beyond §2.3.1's
  private instance.
- It changes nothing in DatastoreKit, RayPoolKit, ChamPBH or SGK.

---

## 6. The results note

`.documents/dk-and-rpk-migration/05-move-si-data-out-of-the-layer.md`, using README §5.1. It holds:
- §2.1.1's capture script and its output;
- the 15 calls at the gate, with their lines, and each stub's change;
- §2.1.3's finding, for 09;
- the schema check, the lint before and after, and the import check;
- the deliberate-breakage record, as diffs;
- the two suites beside 04's counts, with the new tests by module.

**One commit**, in the repository's form, staged by explicit path only, after showing
`git diff --cached --name-only`.
