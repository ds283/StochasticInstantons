# Prompt 01 — rehearsal tooling and run provenance

**Campaign:** [`README.md`](README.md) · **Board items:** **T1**–**T3** ·
**Board:** [`IMPLEMENTATION_STATE.md`](IMPLEMENTATION_STATE.md)
**Written:** 2026-10-12, with prompts 02–04, after the user reviewed the plan and ruled U1, U2 and
U4–U7 as recommended (README §6.1; P1–P19 stand as proposed).
**Gate:**
- you are on branch `dk-and-rpk-migration`, whose first commit is the planning commit;
- `git status` shows no tracked change. The ignored store files in the working tree
  (`test-gradient*.sqlite`, `out-*/`) are not yours: do not open, move or delete them;
- the venv holds neither `datastorekit` nor `raypoolkit` (`./venv/bin/pip show` finds neither).

**Closes:** nothing. **Opens:** only what the work finds.
**Recommended model:** **Opus**. The comparison tool is the acceptance instrument of three
rehearsals, and later of P2's comparison of its rebuilt grids with the June ones. Its correctness
is the point of the prompt.

**Read first:**

1. `CLAUDE.md`, in full, with `.claude/rules/test-selection.md`, `datastore-units.md` and
   `populate-ordering.md`. They say which tests to run, which columns carry units, and in what
   order the value tables are read.
2. [`README.md`](README.md): §0.1 (items 9, 11 and 13), §0.2, §2.2 (01's charter), **§4.1** (the
   protocol the scripts serve), **§4.2** (the comparison), §4.3, §5 and §6.2 (P1–P3, P5).
3. **ChamPBH's 01, which this prompt follows**, at ChamPBH `d7791c5` (read through
   `git -C /Users/ds283/Documents/Code/ChamPBH show d7791c5:<path>`; **read it, and import, copy-run
   or edit nothing there**, README §5 rule 12). It was dispatched and reviewed on 2026-10-12 (its
   board §5.2):
   - `utilities.py:174-271`: `RECORDED_DISTRIBUTIONS`, `installed_package_provenance()` and
     `format_package_provenance()`;
   - `tools/compare_stores.py`: the comparison, with its bookkeeping list, its polymorphic map, its
     near-miss pairing and its schema snapshot;
   - `Datastore/tests/test_package_provenance.py` and `Datastore/tests/test_compare_stores.py`;
   - `.documents/dk-and-rpk-migration/rehearsal/`: its four scripts;
   - `prompts/dk-and-rpk-migration/logs/01-rehearsal-tooling-and-run-provenance.md`, and its board's
     §5.2–§5.3, for what the review found.

   You may take ChamPBH's code as the starting point of SI's, adapting it, since the two layers
   write the same store format. Say in the results note what you took and what you changed. SI's
   tool must stand on its own: it imports nothing from ChamPBH.
4. SGK's `RunRegistry.package_provenance()`, at
   `/Users/ds283/Documents/Code/SecondaryGWKit/RunRegistry/__init__.py:122` (read only). ChamPBH's
   helper has its fields and meanings, and so must SI's.
5. **Every factory under `Datastore/SQL/ObjectFactories/`**: each `register()` (its columns and
   foreign keys) and each `store` (what it writes, and from where). §2.2 needs the bookkeeping
   list, the polymorphic references and the JSON columns.
6. **Every compute target under `ComputeTargets/`**: where each builds the `diagnostics` dict that
   its factory writes to `diagnostics_json` (and `CompactionFunction`'s to `metadata`). §2.2 needs
   the timing keys.
7. `Datastore/SQL/ShardedPool.py:80-135` and `:285-345`: how SI's primary records its shards.
   DatastoreKit's `datastorekit/shard_paths.py` and `docs/client-contract.md` §5, at `v0.3.0`:
   how the package's primary records them, and which primary tables are the layer's. Read
   DatastoreKit through `git -C /Users/ds283/Documents/Code/DatastoreKit show v0.3.0:<path>`;
   edit nothing there.
8. `RayTools/RayWorkPool.py`'s `print` calls (from `:181`) and `main.py`'s stage titles
   (`STAGE 1:` at `:727`, `STAGE 2:` `:825`, `STAGE 3:` `:849`, `STAGE 4` `:860` and `:1103`,
   `STAGES 2+3+4: UNIFIED PIPELINE` `:204`, `STAGE G:` `:665`). These are the lines
   `stage_counts.py` and `interrupt_when.py` read. No SI rehearsal log exists yet. Build your test
   fixture from the shape the code prints, and say so.

---

## 1. What is wanted

Three things, none of which runs a build:
- **T1, run provenance (P5).** Each driver says, in its own output, which `datastorekit` and
  `raypoolkit` it ran with, so that every rehearsal log, and every later production log, records
  it.
- **T2, the comparison of two stores by value (P3, README §4.2).** `tools/compare_stores.py` is a
  lasting tool, tested. It reads SI's store format and the package's, through `sqlite3`
  read-only and never through either layer, so that a store built before the DatastoreKit swap can
  be compared with one built after it.
- **T3, the rehearsal scripts (README §4.1)**, which 02, 07 and 11 run unchanged.

---

## 2. What to build

### 2.1 T1 — `utilities.installed_package_provenance`

`utilities.py` is on `CLAUDE.md`'s protected list. **This prompt names it, and the change is
exactly this:** two new functions, the constant they default to, and the imports they need.
Nothing else in the file changes, and nothing in it is reformatted.

- **`installed_package_provenance(names=RECORDED_DISTRIBUTIONS) -> dict`**, where
  `RECORDED_DISTRIBUTIONS = ("datastorekit", "raypoolkit")`. It behaves as ChamPBH's does. For each
  name:
  - `None` if the distribution is not installed;
  - otherwise exactly `{"version", "url", "commit", "requested_revision", "editable"}`, read with
    the standard library from `importlib.metadata` and the distribution's PEP 610
    `direct_url.json`;
  - a field the install does not record is `None`;
  - `editable` is `True` only when `dir_info.editable` is the boolean `true`;
  - an absent, unreadable or malformed `direct_url.json` gives `None` for the three VCS fields and
    `False` for `editable`.

  It never raises, and never imports a package it describes.
- **`format_package_provenance(provenance) -> str`**: one line, worded as ChamPBH's, so that the
  three clients' logs read alike. ChamPBH's line with nothing installed is
  `>> packages: datastorekit not installed; raypoolkit not installed`. Its review found that pip
  records a VCS URL **without** `git+` (ChamPBH board §5.4), and the line prints the URL as
  recorded.
- **The drivers.** `main.py`, `plot_InstantonSolutions.py` and `plot_GradientCoupledSolutions.py`
  each print that line once, after argument parsing and **before `ray.init(`** and their
  `ShardedPool(` construction:
  - `main.py` calls `ray.init` at module level (`:97`), after `parser.parse_args()` (`:91`);
  - each plot script calls it inside `run_plots` (`plot_InstantonSolutions.py:1204`,
    `plot_GradientCoupledSolutions.py:971`).

  Nothing else in them changes. The line is printed, never a refusal.
- **Tests**, in `tests/test_package_provenance.py`, unmarked (fast). They use stand-in
  distributions and no real install. The cases are:
  - not installed;
  - a VCS install at a tag (commit and requested revision);
  - an editable install (`editable: True`);
  - `direct_url.json` absent;
  - `direct_url.json` present but not a JSON object;
  - and the line's format for each.

  How you stand in a distribution is yours; say which.

### 2.2 T2 — `tools/compare_stores.py`

README §4.2 is the specification. This section adds what SI's factories and compute targets show.

**Interface**, as ChamPBH's:

```bash
./venv/bin/python tools/compare_stores.py A.sqlite B.sqlite [--json OUT]   # compare two stores
./venv/bin/python tools/compare_stores.py --snapshot A.sqlite [--out F]    # write A's schema snapshot
./venv/bin/python tools/compare_stores.py --schema A.sqlite --against F    # compare A with a snapshot
```

`A.sqlite` is a primary. The tool exits 0 when nothing compared differs, 1 when something does,
and 2 when a store cannot be read. Output is human-readable by default; `--json` also writes the
full result.

**Reading a store.**
- Open every file with `sqlite3.connect(f"file:{path}?mode=ro", uri=True)`, and nothing else.
  Never open a store through `Datastore`, `ShardedPool`, `datastorekit` or Ray, and import none of
  them, nor SQLAlchemy.
- Find the shards by the glob `<stem>-shard*<suffix>` beside the primary. Check their number
  against the rows of the primary's `shards` table, and stop (exit 2) if they disagree.
- **Never open a path read from the `shards` table.** SI's primary records the absolute path of
  the resolved primary (DatastoreKit checklist item 8; `Datastore/SQL/ShardedPool.py:88`, `:296`),
  which for a copied store names the original's files.
- **The client tables** are the shards' tables that are not the layer's. The primary's tables are
  the layer's and are not compared: `shards`, `shard_key_config`, `shard_keys`,
  `replicated_tables`, `sharded_tables`, and `replication_in_flight` where it exists. Check, from
  the code, whether an SI primary holds any client table. The results note says what you found.

**Identities** (README §4.2).
- A row's identity is its columns except the bookkeeping ones, each value in canonical form:
  - a float by `float.hex` of the stored value;
  - an integer, string, boolean or `None` as it is;
  - a JSON column as below.
- **Foreign keys** (`PRAGMA foreign_key_list` on each table) are replaced by the identity of the
  row they name, on the same shard, recursively. The `version` column resolves to the version
  row's label.
- **The value tables have composite primary keys and no `serial`** (`FullInstantonValue`,
  `SlowRollInstantonValue`, `InflatonTrajectoryValue`, `GradientCoupledInstantonValue`;
  `serial: False` in their `register()`). Their rows are identified by their resolved references
  (parent and `efold_value`) and their remaining columns, as any other row's.
- **Polymorphic references** have no foreign key and must be declared:
  - `InflatonTrajectory.potential_serial`, resolved by `potential_type`. `1` is
    `QuadraticPotential` and `2` is `QuarticPotential` (`CosmologyConcepts/Potentials/model_ids.py`;
    `POTENTIAL_REGISTRY`, `CosmologyConcepts/Potentials/registry.py:27-42`).
  - `GradientCoupledInstanton.diffusion_serial`, resolved by `diffusion_type`. `1` is
    `MasslessDecoupledDiffusion` (`InflationConcepts/DiffusionModel/model_ids.py`;
    `DIFFUSION_MODEL_REGISTRY`, filled at `Datastore/SQL/ObjectFactories/MasslessDecoupledDiffusion.py:71`).

  Find any other such pair in any factory: a `*_serial` column with no `ForeignKey` beside a
  `*_type` column. Declare the map in the tool as data. A test (§2.4, test 12) checks it against
  the two registries, which the test may import and the tool may not. A type value the map lacks
  is a named problem, not a crash.
- **JSON columns** are parsed and compared structurally. The candidates are `fields_json` on the
  four value tables, `diagnostics_json` on `InflatonTrajectory`, `FullInstanton`,
  `SlowRollInstanton` and `GradientCoupledInstanton`, and `metadata` on `CompactionFunction`
  (`Datastore/SQL/ObjectFactories/CompactionFunction.py:111`, `:362-364`).
  - Confirm each is `json.dumps` output. A `Text` column that is not JSON is compared as text.
  - A parsed value's floats are compared by `float.hex`, recursively through lists and dicts.
  - Its **timing keys** are bookkeeping, at any depth: reported when they differ, never counted.
  - Keys present in one row and not the other are a difference.
- **Memoise identities** by `(shard, table, serial)`, as a digest, so that a value table resolves
  its parent once.

**Bookkeeping**, reported and never compared. Each entry is a constant in the tool with a comment
giving the `path:line` that justifies it, and each is tested.
- **Columns:** `serial` and `timestamp` in every table; and any column whose value depends on the
  run rather than on the physics. Candidates to classify by reading where each is written:
  - the `label` columns of `FullInstanton`, `SlowRollInstanton` and `GradientCoupledInstanton`
    (`FullInstanton.py:89`, `SlowRollInstanton.py:88`, `GradientCoupledInstanton.py:134`;
    `ComputeTargets/FullInstanton.py:670`, `SlowRollInstanton.py:636`). A label that carries a job
    name or a time is bookkeeping; one built from the physics is not.
- **JSON timing keys**, by `git grep` over `ComputeTargets/` at planning:
  - `compute_time`, in every compute target;
  - `compute_time_total`;
  - `mean_time_per_picard_iteration`;
  - `picard_sweep_wallclock_min`, `_mean` and `_max` (`GradientCoupledInstanton`, under its
    stiffness instrumentation).

  Confirm each where it is set, and find any the list misses. **Not bookkeeping:**
  - `wallclock_budget`, `wallclock_budget_seconds` and `wallclock_budget_exceeded`. They are the
    solve's configuration and its outcome against it. Unbudgeted, as the rehearsal is (README
    §4.1), they are constant.
  - Step counts, iteration counts and the `rk45_*` statistics that are not times. These are set
    by the integrator, not by the clock.

  If a key cannot be classed from the code alone, stop (§4).

**Replicated tables.** Within one store, each shard's copy of a replicated table is compared with
the others' (by identity), and a difference is reported as a named problem. Between stores, one
copy is compared: the lowest shard's.

**The output**, as ChamPBH's:
- per client table, the counts of rows matched, in A only and in B only, with each unmatched row's
  identity rendered by physical labels;
- **near misses**: an A-only and a B-only row whose resolved references and non-float columns are
  equal are paired, and each float that differs (in a column or inside JSON) is printed with both
  values and the relative difference;
- the bookkeeping differences, counted, and kept apart from the result;
- the problems: divergent replicated copies, unresolved references, unknown type values, JSON that
  does not parse.

**The schema snapshot**, as ChamPBH's. For each client table on shard 0, write as sorted JSON:
- its columns (name, declared type, not null, primary key);
- its indices (as their columns and uniqueness, not by name);
- its foreign keys, as sets.

`--schema A --against F` reports each difference. A column's order is not a difference: the
package prepends `serial`, `version`, `timestamp`, `stepping` in that order (contract §2), and SI's
layer may not.

### 2.3 T3 — the rehearsal scripts

They go under `.documents/dk-and-rpk-migration/rehearsal/`.
- Each runs from the repository root, with `--help` (or a usage line for a shell script).
- Each takes the rehearsal root from an argument or the variable `REHEARSAL_ROOT`, whose default is
  `~/ScienceData/StochasticInstantons-rehearsals/dk-and-rpk-migration` (P2).
- Like ChamPBH's, `build.sh` and `run_readers.sh` refuse to overwrite an existing log or readers
  directory.

The scripts:
- **`build.sh NN STORE BUILD ADDRESS MODE [--profile-db]`**: one build of README §4.1.
  - `STORE` names the store, `$REHEARSAL_ROOT/NN-STORE.sqlite`: `reference`, `resumed`,
    `scalars`, and at RH0 only `scalars-2` (prompt 02). Any slug of letters, digits and hyphens is
    accepted. `BUILD` is the build's slug: `reference`, `resumed-a`, `resumed-b`, `scalars` or
    `scalars-2`.
  - `MODE` is `dense` or `scalars`. `dense` passes `--targets homogeneous gradient`; `scalars`
    passes `--targets homogeneous --no-store-values` (README §4.1, build 4, and
    `[gci-main-no-store-values-crash]`).
  - `--profile-db` adds `--profile-db $REHEARSAL_ROOT/NN-STORE-profile.sqlite`.
  - The command is README §4.1's, verbatim but for these parameters: `--config
    quadratic-minimal.yaml`, `--n-collocation-points 5 --alpha-regularization 0.01`, `--job-name
    dk-and-rpk-migration-NN-BUILD`, `--ray-address ADDRESS`.
  - Output goes to `$REHEARSAL_ROOT/logs/NN-BUILD.log`, and the driver's pid to
    `$REHEARSAL_ROOT/logs/NN-BUILD.pid` as soon as it starts. When it ends, the script appends
    `** driver exit status N`.
  - It runs in the foreground; the caller backgrounds it.
- **`interrupt_when.py LOG PIDFILE --banner TEXT --after SECONDS`**:
  - it waits until `LOG` holds a line containing `TEXT`, then `SECONDS` more;
  - then it sends `SIGTERM` to the pid in `PIDFILE`, and prints what it did and when;
  - it reads the log file and starts nothing;
  - if the driver exits before the banner appears, it says so and exits non-zero.

  ChamPBH found that a `SIGTERM`ed driver exits **134**, not 143: Ray's failure-signal handler
  aborts (ChamPBH board §5.3). The script reports what it sent, not what the driver did.
- **`stage_counts.py LOG...`**: for each log and each stage title of §Read-first 8, the queue's
  summary counts without the rates (lookup, compute, store, validation, as the pool prints them),
  and the number of `ALL WORK ITEMS COMPLETE`. It is tested on a fixture built from the shape the
  code prints (`tests/test_rehearsal_stage_counts.py`, unmarked).
- **`run_readers.sh NN STORE ADDRESS`**: README §4.1's L3 on `$REHEARSAL_ROOT/NN-STORE.sqlite`,
  into `$REHEARSAL_ROOT/NN-readers/STORE/`.
  1. A copy of the store's files into `NN-readers/STORE/before/`, for the comparison only. No layer
     ever opens it.
  2. `main.py --config quadratic-minimal.yaml --database <store> --inventory --ray-address <ADDRESS>`.
  3. `plot_InstantonSolutions.py --config quadratic-minimal.yaml --database <store> --output-dir
     NN-readers/STORE/plot_InstantonSolutions --ray-address <ADDRESS>`. Add `--no-store-values`
     when `STORE` begins `scalars`, so that it writes `scalar_data.csv`.
  4. When `STORE` does not begin `scalars`: `plot_GradientCoupledSolutions.py --config
     quadratic-minimal.yaml --database <store> --output-dir NN-readers/STORE/plot_GradientCoupledSolutions
     --n-collocation-points 5 --alpha-regularization 0.01 --ray-address <ADDRESS>`.
  5. `tools/compare_stores.py NN-readers/STORE/before/<primary> <store>`, kept in full. README
     §4.1 expects it to differ by **one `version` row, labelled `2026.3.0`**, written by the plot
     scripts' read-write pools (P9, P10), and by bookkeeping. The script prints that verdict,
     without judging it.

  Each step's output goes to its own file, each exit status is recorded, and the script exits
  non-zero if any step did. **Check every flag against `config/argument_parser.py` and each
  script's own parser.** The plot scripts' flags above, and the rest of what they need to find the
  grid's instantons, are your reading of those parsers. A flag that does not exist is a stop, not
  a guess.

No script starts or stops a Ray cluster: 02, 07 and 11 do that themselves (README §4.1, "The
cluster").

### 2.4 The tests of T2

In `tests/test_compare_stores.py`, unmarked. Each test builds its stores in a `tempfile` directory
with `sqlite3` alone. A store has:
- a primary with a `shards` table, and two shards;
- a replicated parameter table, and a `version` table;
- a sharded parent table with a foreign key into the parameter table and a `version` column;
- a value table with a composite primary key, no `serial`, and a `fields_json` column;
- one polymorphic pair;
- a `diagnostics_json` column holding a timing key and a science key.

At least:
1. two equal stores: an empty result, exit 0;
2. one float changed in its last bit (`math.nextafter`): named, with both values, exit 1;
3. a row in one store only: named, by its physical labels;
4. equal content under different serials and a different shard assignment: an empty result;
5. `timestamp` differing: reported apart, exit 0;
6. **`compute_time` inside `diagnostics_json` differing**: reported apart, exit 0. **A science
   key inside it differing in its last bit**: named, exit 1;
7. **a float inside `fields_json` changed in its last bit**: named and paired as a near miss;
8. **one row under two different `potential_serial`s, its potential equal in content**: an empty
   result. An unknown `potential_type`: a named problem, not an exception;
9. a primary whose `shards` table holds absolute paths, and one holding bare names: both read, and
   the absolute paths never opened (point them at files that do not exist);
10. a shard count that disagrees with the `shards` table: exit 2;
11. two shards whose copies of a replicated table differ: a named problem;
12. **the declared maps:**
    - every polymorphic entry equals `POTENTIAL_REGISTRY`'s and `DIFFUSION_MODEL_REGISTRY`'s;
    - every bookkeeping column names a column some factory's `register()` declares;
    - every JSON timing key appears in `ComputeTargets/`.

    `register()` needs no store and no Ray.
13. the schema snapshot round-trips, and a dropped index is reported;
14. no file the tool reads changes: every file's checksum and modification time, before and after.

---

## 3. Acceptance

1. **T1:** §2.1's tests pass. No driver is run.
   - In today's venv, `format_package_provenance(installed_package_provenance())` prints both
     packages as not installed (shown in the results note).
   - A test reads each driver's `ast`, and finds exactly one call of it, before the driver's
     `ray.init(` and its `ShardedPool(`.
2. **T2:** §2.4's tests pass, and `--help` runs.
3. **T3:** each script prints its usage, and `stage_counts.py`'s test passes. **No script is run on
   a real build, and no store but a test's temporary one is opened.**
4. **The suites** (`.claude/rules/test-selection.md`; the diff touches none of its slow paths):
   - `pytest -m "not integration and not slow"`: 631 at `7bb3efd` (630 passed, 1 skipped), plus
     exactly the tests you add, all passing. The results note counts the new ones by module;
   - `pytest -m integration`: 61 (60 passed, 1 skipped), unchanged.
5. **Formatting.** The new files may be formatted with `./venv/bin/ruff format`. The three drivers
   and `utilities.py` are **not** reformatted: their diffs are only the lines §2.1 adds (README §5
   rule 15).
6. **Deliberate breakage** (README §5 rule 8). Each is caught by a test, and each is recorded as a
   diff that `git apply` replays:
   - `float.hex` replaced by `repr` rounded to 12 digits in the canonical form: test 2 must fail;
   - the timing keys emptied: test 6 must fail;
   - the potential map's two entries swapped: test 8 or 12 must fail;
   - the glob replaced by the paths in the `shards` table: test 9 must fail;
   - the provenance helper's `editable` read from the wrong key: its editable test must fail;
   - one driver's provenance call moved after its `ray.init(`: §3.1's test must fail.
7. **The records**, in the same commit:
   - this board's §1 row for 01;
   - items T1–T3, and a `### 5.5 After prompt 01 (<date>)` entry;
   - a §3 entry for anything opened, with `.documents/OPEN-ISSUES.md` in the same commit
     (`CLAUDE.md`).

---

## 4. Stop conditions — stop and ask

- An SI primary turns out to hold client tables, or a shard to hold a layer table other than those
  §2.2 names.
- A column or a JSON key cannot be classed as bookkeeping or physics from the code alone.
- A polymorphic type value cannot be mapped to a table from the code.
- A `Text` column holds JSON in some rows and not in others.
- Any suite's count falls, or an existing test fails.
- Meeting §3 would need a change to a factory, to the layer, to `RayTools/`, or to any driver
  beyond the one provenance line.

---

## 5. What this prompt does not do

- **Files it changes:**
  - `utilities.py` (§2.1 only);
  - in each of the three drivers, the one provenance line and its import;
  - the new `tools/compare_stores.py`, `tests/test_package_provenance.py`,
    `tests/test_compare_stores.py`, `tests/test_rehearsal_stage_counts.py` and
    `.documents/dk-and-rpk-migration/rehearsal/`;
  - the results note `.documents/dk-and-rpk-migration/01-rehearsal-tooling-and-run-provenance.md`;
  - this board.

  Nothing else.
- It runs no build, starts no Ray, and opens no store but a test's temporary one: not
  `test-gradient*.sqlite`, and nothing under `out-*/`.
- It installs nothing, and changes nothing in DatastoreKit, RayPoolKit, ChamPBH or SecondaryGWKit.

---

## 6. The results note

`.documents/dk-and-rpk-migration/01-rehearsal-tooling-and-run-provenance.md`, using README §5.1.
It holds:
- the provenance line's exact format;
- the bookkeeping columns, the JSON columns and timing keys, and the polymorphic map, each entry
  with the `path:line` that justifies it;
- what an SI primary was found to hold (§2.2);
- what you took from ChamPBH's tool and scripts, and what you changed;
- the deliberate-breakage record, as diffs;
- the two suites beside the planning baselines.

**One commit**, in the repository's form (an imperative title, a body, and a `Co-Authored-By:`
line), staged by explicit path only, after showing `git diff --cached --name-only`.
