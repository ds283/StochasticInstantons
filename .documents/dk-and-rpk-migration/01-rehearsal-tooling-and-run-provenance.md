# 01 — rehearsal tooling and run provenance

**Subject:** Add run provenance and the tooling for the migration rehearsals
**Commit:** this commit, on branch `dk-and-rpk-migration`, on top of `b4088d1`
**Date:** 2026-10-12, by Claude Opus 5.5
**Result:** **COMPLETE.** T1–T3 shipped. The default run is 631 → **680** (679 passed, 1
skipped): +24 `test_compare_stores`, +20 `test_package_provenance`, +5
`test_rehearsal_stage_counts`. The integration run is 61 (60 passed, 1 skipped), unchanged. All
six deliberate breakages are caught. No §4 stop condition was met, and no issue is opened. No
build or driver was run; no Ray cluster was started (the integration suite's private instance,
under `RAY_ADDRESS=local`, aside); and no store was opened but a test's temporary one and two
scratch probes' own, built in the scratch directory.

Prompt: [`.prompts/dk-and-rpk-migration/01-rehearsal-tooling-and-run-provenance.md`](../../.prompts/dk-and-rpk-migration/01-rehearsal-tooling-and-run-provenance.md).
Where the orchestrator's brief corrected the prompt, the brief governed: Deviations D1–D3, and
the `label` ruling under T2.

## What shipped

### T1 — run provenance (`utilities.py`; the three drivers; `tests/test_package_provenance.py`)

- `utilities.RECORDED_DISTRIBUTIONS = ("datastorekit", "raypoolkit")`.
- `utilities.installed_package_provenance(names=RECORDED_DISTRIBUTIONS) -> dict`. For each name,
  `None` if the distribution is not installed; otherwise exactly `{"version", "url", "commit",
  "requested_revision", "editable"}`, read through `importlib.metadata.distribution(name)`
  (called as a module attribute, after `import importlib.metadata`) and the distribution's
  PEP 610 `direct_url.json`:
  - `url` is `direct_url.json`'s `url`; `commit` and `requested_revision` are its
    `vcs_info.commit_id` and `vcs_info.requested_revision`;
  - `editable` is `dir_info.get("editable") is True`, so only the boolean `true` counts;
  - an absent `direct_url.json` (`read_text` gives `None`, so `json.loads` raises `TypeError`),
    one that is not JSON or not UTF-8 (`ValueError`), one that cannot be read (`OSError`), or one
    that is not a JSON object, gives `None` for the three VCS fields and `False` for `editable`;
    a `vcs_info` or `dir_info` that is not an object is treated as absent.

  Its fields and their meanings are those of SGK's `RunRegistry.package_provenance()`
  (`SecondaryGWKit/RunRegistry/__init__.py:122-169`, read, not imported) and of ChamPBH's helper
  (ChamPBH `d7791c5`, `utilities.py:174-271`), whose code it is. It uses the standard library
  only (`importlib.metadata`, `json`: two new module-level imports), never imports a package it
  describes, and never raises on odd metadata.
- `utilities.format_package_provenance(provenance) -> str`, worded as ChamPBH's.
- **The provenance line's exact format**:

  ```text
  >> packages: ENTRY; ENTRY
  ```

  one `ENTRY` per name, in `RECORDED_DISTRIBUTIONS` order, each one of:

  | Install | `ENTRY` |
  |---|---|
  | not installed | `NAME not installed` |
  | VCS install at a tag | `NAME VERSION (URL@COMMIT, requested REVISION)` |
  | VCS install, no requested revision recorded | `NAME VERSION (URL@COMMIT)` |
  | editable install | `NAME VERSION (editable, URL)` |
  | a local directory, not editable | `NAME VERSION (URL)` |
  | a commit with no URL | `NAME VERSION (commit COMMIT)` |
  | no `direct_url.json`, or nothing usable in it | `NAME VERSION (no recorded origin)` |

  The URL is printed as pip records it, which for a VCS install is **without** `git+` (ChamPBH
  board §5.4). The commit is printed in full.
- **In this venv** (`./venv/bin/python -c "import utilities as u;
  print(u.format_package_provenance(u.installed_package_provenance()))"`):

  ```text
  >> packages: datastorekit not installed; raypoolkit not installed
  ```

  `installed_package_provenance()` itself gives `{'datastorekit': None, 'raypoolkit': None}`, and
  `./venv/bin/pip show datastorekit raypoolkit` finds neither.
- **The drivers.** Each gains one import line and one statement,
  `print(format_package_provenance(installed_package_provenance()), flush=True)`, placed directly
  before its `ray.init(`:

  | Driver | Import (new line) | Print (new line) | `ray.init(` | `ShardedPool(` |
  |---|---|---|---|---|
  | `main.py` | `:48`, after `from Units.base import UnitsLike` | `:98`, module level, after the database check | `:99` | `:1347` |
  | `plot_InstantonSolutions.py` | `:74`, after `from Units import Planck_units` | `:1205`, inside `if __name__ == "__main__":` | `:1206` | `:1209` |
  | `plot_GradientCoupledSolutions.py` | `:102`, after `from Units import Planck_units` | `:972`, inside `if __name__ == "__main__":` | `:973` | `:976` |

  An `ast` comparison of each driver and of `utilities.py` with `0209137` finds no other changed
  statement (Verification, item 3). None of the four files was reformatted.
- **Tests:** `tests/test_package_provenance.py`, unmarked, **20 items** (under 2 s). Stand-ins are
  real `<name>-<version>.dist-info` directories (`METADATA`, and a `direct_url.json` where the
  case has one) in a `tempfile` directory put first on `sys.path`, found by the real
  `importlib.metadata`: **nothing is patched**, so no test can pass through a mock aimed at the
  wrong name. The stand-in names (`si-standin-*`) are on no index. Cases: not installed; a VCS
  install at a tag; an editable install; `editable` only for the boolean `true` (4
  parametrised: `{}`, `false`, `"true"`, `1`); `direct_url.json` absent; not an object or
  unreadable (5 parametrised: a list, a string, a number, not JSON, not UTF-8) and a directory in
  its place; `vcs_info`/`dir_info` not objects; several names in order with the described
  package never imported (its stand-in module raises on import); the default names; and the line's
  format in each case. The driver test (3 parametrised) reads each driver's `ast`, finds the scope
  in which it calls `ray.init` (the module body for `main.py`, the body of the module-level
  `if __name__ == "__main__":` block for the plot scripts), and checks there is exactly one
  provenance print, a statement of that scope, before the single `ray.init(` (itself a statement
  of the same scope) and before every `ShardedPool(`, and that both names are imported from
  `utilities`.

### T2 — `tools/compare_stores.py`

Interface as prompt §2.2 and ChamPBH's: `A.sqlite B.sqlite [--json OUT] [--max-rows N]`,
`--snapshot A.sqlite [--out F]`, `--schema A.sqlite --against F`. Exit 0 when nothing compared
differs, 1 when something does (a row in one store only, a science value that differs, or a named
problem), 2 when a store cannot be read. `--help` runs.

**Reading.** Every connection is `sqlite3.connect("file:" + quote(path) + "?mode=ro",
uri=True)` (`connect_ro`), on the primary or on a shard found by the glob
`<stem>-shard*<suffix>` beside it; the count is checked against `select count(*) from shards`,
and **the `filename` column is never read**, so no recorded path can be opened. The tool imports
the standard library only (a test checks its `ast`): no `Datastore`, `ShardedPool`,
`datastorekit`, Ray or SQLAlchemy, and no `ATTACH`.

**What an SI primary holds, per the code:** the five layer tables `shards`, `shard_key_config`,
`shard_keys`, `replicated_tables`, `sharded_tables`, and **no client table**.
`Datastore/SQL/ShardedPool.py:232-284` defines exactly those five on the primary's engine,
`:287-291` creates them (`_write_shard_data`), and after creation the primary's engine only
inserts into `shard_keys` (`:810-821`, `_assign_shard_keys`). Every `Datastore` actor is given a
shard file and never the primary (`:158-191`), and an actor creates only the registered tables
(`Datastore/SQL/Datastore.py:309-394`), none of which has a layer table's name. The `shards`
rows record `str(db_name)` of each shard path built from the **resolved** primary (`:88`,
`:113-121`, `:296`), so absolute paths. A DatastoreKit primary adds `replication_in_flight`
(client contract §5); a non-empty one is a named problem. A client table found on a primary, or a
layer table on a shard, is a named problem.

**Identities.** A row's identity is its columns less the bookkeeping ones, each in canonical
form, tagged by kind (`["f", float.hex]`, `["i", n]`, `["s", text]`, `["x", hex]`, `None`); each
foreign key (`PRAGMA foreign_key_list`) is replaced by the digest of the identity of the row it
names on the same shard, recursively, so `version` resolves to its label; each declared
polymorphic reference is resolved the same way through its type column; each JSON column is
replaced by its parsed value's canonical form (below). Digests are BLAKE2b-128 of the sorted
identity and are memoised by `(shard, table, key column, key value)`. The value tables
(`serial: False`, composite primary keys) are identified by their resolved references and
`fields_json`, as any other row.

**The bookkeeping columns** (reported, never compared):

| Column | Tables | Why (`path:line`) |
|---|---|---|
| `serial` | every table that has it | the layer's key, leased from the broker at insert: `Datastore/SQL/Datastore.py:317`, `:639-647` |
| `timestamp` | every table that has it | `datetime.now()` at insert: `Datastore/SQL/Datastore.py:651-652` |
| `label` | `FullInstanton` | factory default (`.4g` of `N_init`, `N_final`, `dNstar`): `Datastore/SQL/ObjectFactories/FullInstanton.py:149-155`, written at `:285`, `:310`; the unified pipeline constructs with no label: `ComputeTargets/pipeline.py:288-298`, so NULL (`ComputeTargets/FullInstanton.py:430`, `:443`) |
| `label` | `SlowRollInstanton` | factory default: `Datastore/SQL/ObjectFactories/SlowRollInstanton.py:148-154`, written at `:282`, `:307`; unified pipeline: `ComputeTargets/pipeline.py:304-314`, so NULL (`ComputeTargets/SlowRollInstanton.py:429`, `:444`) |

**How `label` was classed.** What reaches each column is `obj._label`, set only from the
constructor's `label` argument (`ComputeTargets/FullInstanton.py:443`,
`SlowRollInstanton.py:444`, `GradientCoupledInstanton/GradientCoupledInstanton.py:634`).
`RayWorkPool`'s `label_builder` value goes only to `compute(label=…)`
(`RayTools/RayWorkPool.py:385-391`), which passes it to the remote function for printing and never
assigns `_label`; no driver payload carries a `label` key (no `"label":` key in any payload
outside the factories themselves). So a row stored by `main.py`'s per-stage queues carries the
factory default, a `.4g` rendering of the physics. **But the unified pipeline
(`--no-store-values`, `main.py:206`, `:393`) builds its `FullInstanton` and `SlowRollInstanton`
with no label** (`ComputeTargets/pipeline.py:288-298`, `:304-314`; persisted unchanged by
`main.py:_persist_pipeline_item`, `:134-189`), so the column is NULL. One grid built both ways, on
one tree, differs in this column and in nothing else it stores here, and its content is a
rounded copy of three references the identity already compares to the bit. By the brief's test,
`FullInstanton.label` and `SlowRollInstanton.label` are **bookkeeping**.
`GradientCoupledInstanton.label` is **compared**: its only writer is `main.py`'s gradient branch,
whose payload has no `label` (`main.py:632-643`), so it is always the factory default
(`Datastore/SQL/ObjectFactories/GradientCoupledInstanton.py:223-231`, written at `:492`, `:536`)
and cannot differ between two builds of one grid; there is no unified path for it. A straight build
and a resumed one take the same path, so neither label differs between them.

**The JSON columns** (parsed and compared structurally). Every one is written only by
`json.dumps`, or is NULL, at the line given; no other `Text` column is JSON:

| Table | Column | Written at |
|---|---|---|
| `InflatonTrajectory` | `diagnostics_json` | `Datastore/SQL/ObjectFactories/InflatonTrajectory.py:204` |
| `InflatonTrajectoryValue` | `fields_json` | `InflatonTrajectory.py:222-225` |
| `FullInstanton` | `diagnostics_json` | `FullInstanton.py:259-264` |
| `FullInstantonValue` | `fields_json` | `FullInstanton.py:324-329` |
| `SlowRollInstanton` | `diagnostics_json` | `SlowRollInstanton.py:256-261` |
| `SlowRollInstantonValue` | `fields_json` | `SlowRollInstanton.py:321-324` |
| `GradientCoupledInstanton` | `diagnostics_json` | `GradientCoupledInstanton.py:452-457` |
| `GradientCoupledInstantonValue` | `fields_json` | `GradientCoupledInstanton.py:548-553` |
| `CompactionFunction` | `metadata` | `CompactionFunction.py:358-364` |

The other four `Text` columns are text: the three `label` columns, and
`CompactionFunctionSamples.source` (the constants `'full'` and `'slow_roll'`,
`CompactionFunction.py:442`, `:452`). A JSON value's canonical form is an object as its sorted
`(key, value)` pairs **less its timing keys, at any depth**, a list in order, a float by
`float.hex`, and a boolean, integer and string each tagged by kind (so `4`, `4.0` and `true`
differ). A key present on one side only is a difference. A value that does not parse is a named
problem ("JSON that does not parse") and is compared as text.

**The JSON timing keys** (bookkeeping at any depth; their differences between matched rows are
counted per path, e.g. `FullInstanton.diagnostics_json["nested"]["compute_time"]`):

| Key | Set at |
|---|---|
| `compute_time` | `ComputeTargets/InflatonTrajectory.py:76`, `:99`, `:114`, `:140`; `FullInstanton.py:111`, `:269`; `SlowRollInstanton.py:146`, `:180`, `:241`, `:268`, `:306`; `CompactionFunction.py:143`, `:168`, `:252`, `:263`, `:315`, `:404`, copied to the metadata's top level at `:671`, `:679` and nested under `full`/`slow_roll`; `GradientCoupledInstanton/picard.py:1704` |
| `compute_time_total` | `GradientCoupledInstanton/GradientCoupledInstanton.py:453` |
| `mean_time_per_picard_iteration` | `FullInstanton.py:122`, `:283`; `GradientCoupledInstanton/picard.py:1718` |
| `picard_sweep_wallclock_min` / `_mean` / `_max` | `GradientCoupledInstanton/picard.py:1276`, `:1277-1279`, `:1280` (under `instrument_stiffness`, default `True`, `GradientCoupledInstanton.py:114`) |

Each is a `time.perf_counter()` interval. A search of every string literal in `ComputeTargets/`
naming a time (`time`, `wallclock`, `clock`, `elapsed`, `seconds`, `duration`) finds these six
and three more, which are **not** timing keys: `wallclock_budget_seconds` and
`wallclock_budget_exceeded` (`picard.py:1724-1725`; the configuration and its outcome, constant
when unbudgeted), and `wallclock_budget`, a value of `bailout_reason` (`:1697`), not a key. The
only other clock reads under `ComputeTargets/` are the Picard deadline checks (`picard.py:1155`,
`:1432`) and verbose prints (`:1556`), none stored. The `reason` that
`GradientCoupledInstanton/scale_assignment.py:157-169` stores is built from NaN counts and node
indices, not a time. The GCI diagnostics nest the Picard dict and `scale_assignment`
(`GradientCoupledInstanton.py:445-453`), and `CompactionFunction`'s metadata nests each path's
diagnostics (`CompactionFunction.py:668-680`); the timing keys are removed at every depth. The
prompt's list was complete; the test (12d) now fails if a new time-like key appears unclassed.

**The polymorphic map — four pairs, not two:**

| Table | Pair | Declared at | Map |
|---|---|---|---|
| `InflatonTrajectory` | `potential_serial` / `potential_type` | `Datastore/SQL/ObjectFactories/InflatonTrajectory.py:52-63` (written `:194-195`) | `1 → QuadraticPotential`, `2 → QuarticPotential` (`CosmologyConcepts/Potentials/model_ids.py`; `POTENTIAL_REGISTRY`, `registry.py:27-42`) |
| `FullInstanton` | `diffusion_serial` / `diffusion_type` | `FullInstanton.py:78-79` | `1 → MasslessDecoupledDiffusion` (`InflationConcepts/DiffusionModel/model_ids.py`; `DIFFUSION_MODEL_REGISTRY`, filled at `Datastore/SQL/ObjectFactories/MasslessDecoupledDiffusion.py:69-72`) |
| `SlowRollInstanton` | `diffusion_serial` / `diffusion_type` | `SlowRollInstanton.py:77-78` | as above |
| `GradientCoupledInstanton` | `diffusion_serial` / `diffusion_type` | `GradientCoupledInstanton.py:91-92` | as above |

The prompt (§2.2), and README §0.1 item 11 and §4.2, name only the first and the last: **the
README undercounted**. Every type value the code defines is mapped. A type value a map lacks is a
named problem ("unknown type value"), counted once per row, and the row is compared with the
unmapped value in its identity.

**Replicated tables.** Within a store, each shard's copy of a replicated table is checked equal,
by identity, to the lowest shard's, and a difference is a named problem (it also names a
replicated table that references the divergent rows). Between stores the lowest shard's copy is
compared. **`redshift`**, registered and on every shard but in neither of the primary's lists
(`config/sharding.py`; `[redshift-registered-in-neither-table-list]`), is classified as
ChamPBH's tool classifies an unlisted table (replicated if its foreign keys, other than into
`store_tag`, all name replicated tables; otherwise sharded): with no foreign key it is
**compared as sharded, its rows taken from every shard**, and each store gets a note saying so.
It is empty in every SI store, so in practice only the note appears. A table a primary lists but
no shard holds is noted and skipped.

**Output** as ChamPBH's: per table the rows matched and in each store only, each unmatched row
rendered by its physical labels (references as their rows' columns; a referenced row's JSON
omitted; timing keys omitted); near misses, paired by a near key that drops float columns and
replaces each float inside JSON by a bare tag, so that a pair names each differing float in a
column or at a JSON path (`fields_json["P1_invPlanckMass"][0]`) with both values, both hex forms
and the relative difference, and the children of a near-missed parent pair with their
counterparts; the bookkeeping differences, counted apart; the problems. `--json` writes it all;
the human output lists at most `--max-rows` per list and clips a value at 120 characters.

**Schema snapshot** as ChamPBH's (format `stochasticinstanton-compare-stores-schema`, version 1):
each client table on the lowest shard, its columns (name, declared type, not null, primary key),
its indices (columns and uniqueness, not names) and its foreign keys, as sorted sets. Column order
is not a difference.

**Tests:** `tests/test_compare_stores.py`, unmarked, **24 items** (about 3 s). Every store is built
with `sqlite3` alone in a `tempfile` directory: a primary and two shards, with SI's own table
names so that the tool's real maps apply and nothing is patched (the module docstring lists the
tables). Prompt §2.4's fourteen: (1) `test_01`; (2) `test_02`; (3) `test_03`; (4) `test_04`; (5)
`test_05`; (6) `test_06`, timing keys at the top level, nested, and in two tables, then a science
key moved one ulp; (7) `test_07`; (8) `test_08`, the two potential tables' serials exchanged, an
unknown `potential_type` and an unknown `diffusion_type`; (9) `test_09`, with every
`sqlite3.connect` recorded; (10) `test_10`; (11) `test_11`; (12) `test_12a`–`test_12d`; (13)
`test_13`; (14) `test_14`. And six more: keys on one side only, JSON that does not parse,
`4`/`4.0`/`true` distinct, the classification and notes (with `redshift`), a client table on the
primary, `--help`, and the standard-library-only import check.

**Test 12** imports `Datastore/SQL/ObjectFactories/MasslessDecoupledDiffusion.py` to fill
`DIFFUSION_MODEL_REGISTRY`, asserts both registries non-empty, and asserts the tool's whole
`POLYMORPHIC_REFERENCES` **equals** the map built from the registries (both directions); it checks
each registry key against the class's `type_id` and the `model_ids` constants; that every
`*_serial` column without a foreign key, and every `*_type` column, in any factory's `register()`
is a declared pair (so a fifth pair fails it); that every bookkeeping column is registered; that
the JSON columns are registered `Text` columns and every other registered `Text` column is one of
the four known text columns; and that every timing key is a literal in `ComputeTargets/` and every
time-like literal there is a timing key or one of the three known not to be. `register()` is read
from `config.datastore.factories` if it exists (from prompt 05) and otherwise from
`Datastore.SQL.Datastore._factories`; no store and no Ray.

**What was taken from ChamPBH's tool, and what was changed.** The reading (`connect_ro`, the glob,
the count check), the store classification, the identity scheme with its memoised digests, the
near-miss pairing, the replicated-copy check, the rendering, the schema snapshot and the command
line are ChamPBH's (`d7791c5`), adapted; nothing is imported from ChamPBH. Changed:
- **JSON columns**, new: structural comparison, floats by `float.hex` inside JSON, timing keys set
  aside at any depth and reported per path, near-miss pairing through JSON paths.
- **SI's maps**: four polymorphic pairs; the bookkeeping list above; no `MASKED_FRAGMENTS` and no
  `UNSTORED_TYPE_VALUES` (SI has no run-dependent fragment in a physics column, and every defined
  type value is stored).
- **Problems are counted once per row**, keyed by `(table, the row's values)`, rather than once
  per read: a replicated row read on every shard, or read again as a reference, is one problem.
- **A note for an unlisted table** (`redshift`).
- A referenced row's labels omit its JSON; human output clips long values.

### T3 — the rehearsal scripts (`.documents/dk-and-rpk-migration/rehearsal/`)

Each runs from the repository root and prints its usage with `--help` (exit 0); the shell
scripts take `REHEARSAL_ROOT`, default
`~/ScienceData/StochasticInstantons-rehearsals/dk-and-rpk-migration`. None starts or stops Ray.
- **`build.sh NN STORE BUILD ADDRESS MODE [--profile-db]`** (executable). README §4.1's command
  verbatim but for its parameters: `PYTHONPATH=. ./venv/bin/python -u main.py --config
  quadratic-minimal.yaml --database $REHEARSAL_ROOT/NN-STORE.sqlite --job-name
  dk-and-rpk-migration-NN-BUILD --targets TARGETS --n-collocation-points 5
  --alpha-regularization 0.01 --ray-address ADDRESS [--no-store-values] [--profile-db
  $REHEARSAL_ROOT/NN-STORE-profile.sqlite]`, with `dense` → `--targets homogeneous gradient` and
  `scalars` → `--targets homogeneous --no-store-values`. Output to
  `$REHEARSAL_ROOT/logs/NN-BUILD.log`, the pid to `NN-BUILD.pid` as soon as the driver starts,
  `** driver exit status N` appended; exits with the driver's status; refuses an existing log. It
  runs in the foreground. Bash 3.2-safe (no empty-array expansion under `set -u`).
- **`interrupt_when.py LOG PIDFILE --banner TEXT --after SECONDS [--poll SECONDS]`**, ChamPBH's
  unchanged but for its docstring: reads the log, waits for the banner, then the delay, then sends
  `SIGTERM` to the pid in `PIDFILE` only, and prints what it did and when (UTC); exits 1, sending
  nothing, if the driver exits before the banner or during the delay. It reports what it sent,
  not what the driver did (a `SIGTERM`ed driver exits 134).
- **`stage_counts.py LOG... [--json OUT]`**. For each log, in order: each **pool** banner (the six
  titles of `main.py`, printed by `RayWorkPool.py:181`) with whether it completed, its
  queue-summary counts without rates, and whether no compute item was evaluated; the **section**
  banner `** STAGE 4: COMPACTION FUNCTIONS` (`main.py:862`), kept apart from the pool
  `STAGE 4: COMPACTION FUNCTIONS AND MASSES` (`:1105`); each **lookup** banner (`** TITLE
  LOOKUP:`, `PIPELINE LOOKUP`, `COMPACTION FUNCTIONS LOOKUP`) with its "N already computed, M to
  compute[, K skipped]"; each `** Skipping …`/`** Stopping …` line. And per log: the number of
  `ALL WORK ITEMS COMPLETE` lines, the provenance line, the actors' `Pruned/Found N unvalidated …`
  reports with Ray's `(Name pid=N)` prefix and colour codes removed, and `** driver exit status
  N`. Its printed output carries no time, rate or pid. **No SI rehearsal log exists yet: the test
  fixture (`tests/test_rehearsal_stage_counts.py`, unmarked, 5 items) is built from the lines the
  code prints** (a straight dense build, one signalled in the gradient stage, its resume with a
  prune, a scalars-only build).
- **`run_readers.sh NN STORE ADDRESS`** (executable). README §4.1's L3 into
  `$REHEARSAL_ROOT/NN-readers/STORE/`: (0) a copy of the primary and its shards into `before/`;
  (1) `main.py --config quadratic-minimal.yaml --database STORE --inventory --ray-address
  ADDRESS`; (2) `plot_InstantonSolutions.py --config quadratic-minimal.yaml --database STORE
  --output-dir …/plot_InstantonSolutions --ray-address ADDRESS`, plus `--no-store-values` when
  `STORE` begins `scalars`; (3) when it does not, `plot_GradientCoupledSolutions.py --config
  quadratic-minimal.yaml --database STORE --output-dir …/plot_GradientCoupledSolutions
  --n-collocation-points 5 --alpha-regularization 0.01 --ray-address ADDRESS`; (4)
  `tools/compare_stores.py before/NN-STORE.sqlite STORE --json …`. Each step's output to its own
  file, each exit status to `status.txt`, exit 1 if any step did not exit 0; it prints
  `compare_stores`'s `<-- differs` lines and `RESULT:` line without judging them. It refuses an
  existing `NN-readers/STORE/`. **Every flag was checked** against `config/argument_parser.py`
  (`--config` `:13`, `--database` `:19`, `--ray-address` `:80`, `--no-store-values` `:270`,
  `--targets` `:301`, `--n-collocation-points` `:329`, `--alpha-regularization` `:341`,
  `--inventory` `:394`, `--profile-db` `:34`, `--job-name` `:40`) and each plot script's
  `create_plot_parser`, which extends it and adds `--output-dir` (`plot_InstantonSolutions.py:81`,
  `plot_GradientCoupledSolutions.py:126`). The grid needs no further flag: both plot scripts
  rebuild it from the same `--config` and the parser's defaults, as `main.py` does.

## Deviations from the prompt

- **D1 — four polymorphic pairs, not two. STRUCTURALLY REQUIRED.** The prompt asked for any other
  pair; `FullInstanton` and `SlowRollInstanton` carry `diffusion_serial`/`diffusion_type` too
  (the brief said so). All four are declared, and test 12b fails if a fifth appears.
- **D2 — the plot scripts' print is in their `if __name__ == "__main__":` block, not in
  `run_plots`. STRUCTURALLY REQUIRED.** Prompt §2.1 placed `ray.init` inside `run_plots`; it is in
  the module-level `__main__` block (`plot_InstantonSolutions.py:1196`,
  `plot_GradientCoupledSolutions.py:963` at `0209137`). The `ast` test descends into that block.
- **D3 — test 12 imports the diffusion factory module, asserts both registries non-empty, and
  checks the maps by equality. STRUCTURALLY REQUIRED** (the brief): without the import
  `DIFFUSION_MODEL_REGISTRY` is empty and a one-directional check passes vacuously.
- **D4 — test 12 checks more than the prompt's three items. IMPLEMENTATION CHOICE.** Every
  undeclared `*_serial`/`*_type` pair, every `Text` column's classification, and every time-like
  literal in `ComputeTargets/` are pinned, so that a new pair, JSON column or timing key fails a
  test rather than being compared silently.
- **D5 — `build.sh` accepts any slug for `BUILD`, not only the five named. IMPLEMENTATION
  CHOICE.** README §4.1 lets a prompt rerun `resumed-a` on a fresh store, which may want a new
  slug; the five are listed in the usage.
- **D6 — `stage_counts.py` reports lookup lines, the section banner, skip lines, the provenance
  line and the prune reports, beside the pools' counts. IMPLEMENTATION CHOICE.** In SI a stage
  with nothing to compute prints its lookup line and no pool banner (`main.py:474-480`), so L2's
  "the resume recomputed nothing it had stored" is read from the lookups; L2's prune check and
  02's acceptance 2 (the provenance line) read the other two.
- **D7 — problems are counted once per row, not once per read. IMPLEMENTATION CHOICE.** A
  replicated row is held by every shard and read again as a reference; ChamPBH's per-read count
  would report one unknown type value on a replicated `InflatonTrajectory` four times in a
  two-shard store.
- **D8 — test numbering.** Prompt §2.4's tests are `test_01`…`test_14`, with 12 split into
  `test_12a`–`test_12d`; test 11 perturbs `quartic_coupling` and so also names the replicated
  `QuarticPotential` that references it. **IMPLEMENTATION CHOICE.**
- **D9 — the import line's place.** Each driver's new import follows its `Units` import, so the
  `RayTools` imports that prompt 04 rewrites keep their lines (`main.py:45`,
  `plot_InstantonSolutions.py:72`, `plot_GradientCoupledSolutions.py:100`). **IMPLEMENTATION
  CHOICE.**
- **D10 — breakage B1's "`repr` rounded to 12 digits"** is `format(value, ".12g")`, twelve
  significant digits. **IMPLEMENTATION CHOICE.**

No UNINTENDED DRIFT was found.

## Verification performed

1. **Suites**, foreground, serially, `-p no:cacheprovider`, output in the scratch directory
   (`.claude/rules/test-selection.md`: the diff touches none of the `slow` paths):

   | Selection | Planning (`7bb3efd`) / orchestrator (`0209137`) | This commit |
   |---|---|---|
   | `-m "not integration and not slow"` | 631 collected; 630 passed, 1 skipped (110 s / 328 s) | **680 collected; 679 passed, 1 skipped**, 90 s (load ≈ 55–110) |
   | `RAY_ADDRESS=local … -m integration` | 61; 60 passed, 1 skipped (24 s / 104 s) | **61; 60 passed, 1 skipped**, 77 s, unchanged |

   The default run was also run in two halves by file (283 passed + 396 passed, 1 skipped), with
   the same total. New tests by module: `test_compare_stores` **24**, `test_package_provenance`
   **20**, `test_rehearsal_stage_counts` **5**: 631 + 49 = 680. The integration run started a
   private Ray instance (`RAY_ADDRESS=local`); no `ray start` or `ray stop` was run.
2. **The provenance line in this venv:** `>> packages: datastorekit not installed; raypoolkit not
   installed`.
3. **Drivers and `utilities.py` by `ast`, against `0209137`:** in each driver exactly two
   statements are new (the `ImportFrom utilities` and the print; in the plot scripts the print is
   inside the `__main__` block), and every other statement dumps identically; in `utilities.py`
   only the two imports, the constant and the two functions are new. `git diff --stat`: `main.py`,
   `plot_InstantonSolutions.py`, `plot_GradientCoupledSolutions.py` `+2` each, `utilities.py`
   `+106`, no deletion.
4. **A store with SI's real schema** (a scratch probe, not a test). Two two-shard stores whose
   shards were created from every factory's `register()` by SQLAlchemy `create_all` (not through
   the layer), one row per table with the real column names, under other serials, another shard
   assignment, other timestamps and other timing keys at three depths: `RESULT: equal`, all 30
   tables, every timing difference reported per path (e.g. `CompactionFunction.metadata["full"]
   ["compute_time"]`), `redshift` noted. One ulp inside a `GradientCoupledInstantonValue`
   `fields_json` gives exit 1 and the pair `fields_json["phi_PlanckMass"][1]: A = 2.5
   (0x1.4000000000000p+1), B = 2.5000000000000004 (0x1.4000000000001p+1)`; `potential_type = 99`
   gives the named problem. The snapshot lists 30 tables.
5. **Scale.** A ten-shard imitation with 6,000 trajectory value rows (replicated) and ten
   instantons of 6,000 value rows each compares equal in 9–29 s under the machine's load.
6. **`interrupt_when.py`** on a scratch `sleep 120` with a scratch log: it waited for the banner
   and the 2 s delay, sent `SIGTERM` to that pid only (it exited 143), and on a process that exited
   before the banner it said so and exited 1.
7. **Usage:** `build.sh --help`, `run_readers.sh --help`, `interrupt_when.py --help`,
   `stage_counts.py --help`, `compare_stores.py --help` each print their usage and exit 0. No
   script was run on a build.
8. **Formatting:** the new Python files are `ruff format`ted (0.15.17) and pass `ruff check
   --select F,E9`; the three drivers and `utilities.py` were not formatted. Each new Python file
   and shell script carries SI's licence header.
9. **Stores:** no file under `out-*/` and no `test-gradient*.sqlite` was opened. Nothing was
   created under `~/ScienceData/`, which exists already (ChamPBH's rehearsal made it, with
   `ChamPBH-rehearsals/`, at 01:12 today); `StochasticInstantons-rehearsals/` does not exist.

## The deliberate-breakage record

Each diff below is exactly as applied, from a clean tree at this commit, and was replayed with
`git apply`, the three new test modules run, and reversed with `git apply -R`. All six were
caught; the named tests fail for the stated reason.

| | Mutation | Named test, and why it fails | Also failing |
|---|---|---|---|
| B1 | `canonical_float` by `format(value, ".12g")` | `test_02`: the one-ulp change is invisible, exit 0 where 1 is asserted | `test_06`, `test_07` |
| B2 | `TIMING_KEYS = {}` | `test_06`: the `compute_time` differences are compared, exit 1 where 0 is asserted | `test_03`, `test_12d` |
| B3 | the potential map's two entries swapped | `test_08`: the trajectory's potential no longer resolves, exit 1 where 0 is asserted; `test_12a`: the map no longer equals `POTENTIAL_REGISTRY`'s | seven more comparison tests |
| B4 | the glob replaced by the paths in the `shards` table | `test_09`: the recorded absolute paths (`/private/var/…`) are opened instead of the globbed files | `test_10` |
| B5 | `editable` read from `direct_url.json`'s top level, not `dir_info` | `test_editable_install`: `editable` is `False` | — |
| B6 | `main.py`'s provenance print moved after its `ray.init(` | `test_each_driver_prints_the_line_once_before_ray_and_its_pool[main.py]`: `assert 99 < 98` | — |

#### B1

```diff
--- a/tools/compare_stores.py
+++ b/tools/compare_stores.py
@@ -253,7 +253,7 @@
 
 def canonical_float(value: float):
     """A float's canonical form: its stored bits, by float.hex."""
-    return ["f", value.hex()]
+    return ["f", format(value, ".12g")]
 
 
 def canonical_value(value):
```

#### B2

```diff
--- a/tools/compare_stores.py
+++ b/tools/compare_stores.py
@@ -201,6 +201,7 @@
     "picard_sweep_wallclock_max": "per-sweep wall time, under instrument_stiffness "
     "(ComputeTargets/GradientCoupledInstanton/picard.py:1280)",
 }
+TIMING_KEYS = {}
 
 # Polymorphic references: a serial column with no foreign key, whose table is named by a type
 # column. table -> serial column -> (type column, {type value: table}). Every such pair in the
```

#### B3

```diff
--- a/tools/compare_stores.py
+++ b/tools/compare_stores.py
@@ -216,7 +216,7 @@
 #   name (filled at Datastore/SQL/ObjectFactories/MasslessDecoupledDiffusion.py:69-72).
 # tests/test_compare_stores.py checks these maps against both registries; this tool imports
 # neither. A type value a map lacks is a named problem, not a crash.
-_POTENTIAL_TYPES = {1: "QuadraticPotential", 2: "QuarticPotential"}
+_POTENTIAL_TYPES = {1: "QuarticPotential", 2: "QuadraticPotential"}
 _DIFFUSION_TYPES = {1: "MasslessDecoupledDiffusion"}
 POLYMORPHIC_REFERENCES = {
     "InflatonTrajectory": {"potential_serial": ("potential_type", _POTENTIAL_TYPES)},
```

#### B4

```diff
--- a/tools/compare_stores.py
+++ b/tools/compare_stores.py
@@ -472,6 +472,10 @@
             self.recorded_shards = conn.execute(
                 'select count(*) from "shards"'
             ).fetchone()[0]
+            self.recorded_paths = [
+                row[0]
+                for row in conn.execute('select filename from "shards" order by serial')
+            ]
 
             self.replicated = []
             if "replicated_tables" in tables:
@@ -520,7 +524,7 @@
             + "*"
             + glob.escape(suffix)
         )
-        self.shard_files = [Path(p) for p in sorted(glob.glob(pattern))]
+        self.shard_files = [self.primary.parent / p for p in self.recorded_paths]
         if len(self.shard_files) != self.recorded_shards:
             raise StoreReadError(
                 f"{self.name}: the primary's shards table records {self.recorded_shards} "
```

#### B5

```diff
--- a/utilities.py
+++ b/utilities.py
@@ -224,7 +224,7 @@
             "url": origin.get("url"),
             "commit": vcs_info.get("commit_id"),
             "requested_revision": vcs_info.get("requested_revision"),
-            "editable": dir_info.get("editable") is True,
+            "editable": origin.get("editable") is True,
         }
     return packages
 
```

#### B6

```diff
--- a/main.py
+++ b/main.py
@@ -95,8 +95,8 @@
     parser.print_help()
     sys.exit()
 
+ray.init(address=args.ray_address)
 print(format_package_provenance(installed_package_provenance()), flush=True)
-ray.init(address=args.ray_address)
 
 
 def inflaton_trajectory_store_handler(obj, pool):
```

## Observations not acted on

1. **The README and the prompt undercount the polymorphic references** (README §0.1 item 11 and
   §4.2 name two; there are four, D1). Not corrected here: the README is not on this prompt's list.
2. **The unified pipeline stores `FullInstanton` and `SlowRollInstanton` with a NULL `label`**
   (`ComputeTargets/pipeline.py:288-298`, `:304-314`), where the per-stage queues store the
   factory default. Nothing parses the column: the inventory builds its own labels
   (`Datastore/SQL/ObjectFactories/FullInstanton.py:505-510`), and the provenance footers read it
   by `getattr` (`plotting/provenance.py:46`). It changes no science value and no reader fails on
   it, so no issue is opened; the orchestrator may open one.
3. **The July label the brief quotes, `FullInstanton(N_init=20.12, N_final=19, dNstar=0.825)`, is
   today's factory default** (`Datastore/SQL/ObjectFactories/FullInstanton.py:149-155`), not a
   format of an older builder: `RayWorkPool`'s label builders never reach the column.
4. **`run_readers.sh` will exit 1 at L3.** README §4.1 expects step 4 to find the `2026.3.0`
   `version` row, so `compare_stores` exits 1, and the script, as the prompt says, exits 1 if any
   step did. Read `status.txt`: steps 0–3 exit 0, and step 4's `4-compare_stores.log` shows
   `version` as the only table that differs, with `B only 1`.
5. **A parent that cannot pair lists its children unpaired** (as ChamPBH's review found): an
   `InflatonTrajectory` that differs, or whose type value is unmapped, lists all its value rows
   on each side in `--json` (about 57,000 per side for `test-gradient.sqlite`'s size), beside the
   named problem. The human output is capped by `--max-rows`.
6. **`diagnostics_data.csv`'s timing columns** (README §4.1 L3), for the byte-for-byte comparison
   at 07 and 11: `plot_GradientCoupledSolutions.py` writes `diag_<key>_<kind>` for each key of
   `_DIAGNOSTIC_CSV_KEYS` (`:114-123`) and each adapter kind present (`:529-532`; kinds
   `gradient_coupled`, `full`, `slow_roll`, from `plotting/adapters/*.py`), so its timing columns
   are **`diag_compute_time_gradient_coupled`**, and `diag_compute_time_full` and
   `diag_compute_time_slow_roll` when those adapters are present. `scalar_data.csv` carries no
   timing column (`_flatten_gci_points_for_csv`, `:489`; `plotting/fetch.py:373`,
   `flatten_doe_points_for_csv`, for the homogeneous script). `plot_InstantonSolutions.py` writes no `diagnostics_data.csv`.
7. **Line numbers prompt 04 cites have moved in `main.py`**: lines `48`–`97` of `0209137` are one
   later, and lines from `98` on two later. `main.py:45` is unchanged; `:410` → `:412`, `:497` →
   `:499`, `:664` → `:666`, `:824` → `:826`, `:848` → `:850`, `:1097` → `:1099`. The plot
   scripts' `RayTools` imports (`:72`, `:100`) are unchanged.

## State handed to the next prompt

- **Run provenance:** `utilities.installed_package_provenance()` and
  `format_package_provenance()`; every driver prints `>> packages: …` once, before `ray.init(`.
  In today's venv: `>> packages: datastorekit not installed; raypoolkit not installed`. 03 and 08
  read the helper's dict for their pins; a VCS URL prints without `git+`.
- **`tools/compare_stores.py A.sqlite B.sqlite [--json OUT]`**, exit 0/1/2; `--snapshot`
  and `--schema … --against`. It reads either store format through `sqlite3` `mode=ro` only,
  finds shards by glob, and never opens a recorded path. Bookkeeping: `serial`, `timestamp`,
  `FullInstanton.label`, `SlowRollInstanton.label`, and six JSON timing keys at any depth.
  `GradientCoupledInstanton.label` is compared. Four polymorphic pairs. `redshift` is noted and
  compared as sharded.
- **The rehearsal scripts** under `.documents/dk-and-rpk-migration/rehearsal/`, run unchanged by
  02, 07 and 11, from the repository root:
  - `build.sh NN STORE BUILD ADDRESS MODE [--profile-db]`, backgrounded by the caller; logs and
    pidfiles in `$REHEARSAL_ROOT/logs/`; refuses an existing log;
  - `interrupt_when.py LOG PIDFILE --banner "STAGE G: GRADIENT-COUPLED (ONION MODEL) INSTANTONS"
    --after S` for `resumed-a`; expect the driver to exit 134;
  - `stage_counts.py LOG… [--json OUT]`: pools, lookups ("N already computed, M to compute"),
    the section banner, skips, the provenance line and the prune reports;
  - `run_readers.sh NN STORE ADDRESS`: exits 1 when step 4 finds the expected `2026.3.0`
    `version` row; read `status.txt` and `4-compare_stores.log`.
- **For 02:** `REHEARSAL_ROOT` defaults to
  `~/ScienceData/StochasticInstantons-rehearsals/dk-and-rpk-migration`, which does not exist
  yet (`~/ScienceData/` does, made by ChamPBH's campaign). `build.sh` creates `logs/` under it. The diagnostics CSV's timing columns are
  Observation 6's.
- **For 04:** `main.py`'s line numbers after `:47` have moved (Observation 7).
- **Suites at this commit:** default 680 (679 passed, 1 skipped); integration 61 (60 passed, 1
  skipped).
- **Nothing opened**; `.documents/OPEN-ISSUES.md` is unchanged.
