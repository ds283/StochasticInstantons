# Campaign — rrk-adoption

**Written:** 2026-10-23 at `8b4f615`, by Claude Opus 5.5, and committed on the branch
`rrk-adoption`, cut from `main` at `1c223e8` once `dk-and-rpk-migration` had been merged into it
(R7; `1c223e8` is `8b4f615` plus that board's record of the merge). Planned at the user's request
of the same day, to adopt "the third component that was extracted from SecondaryGWKit, the
RunRegistryKit layer", after an evaluation in the same session (§0.3). The user made seven rulings
(§6.0). **Ruled by the user on 2026-10-23: U1 and U2 as recommended; P1–P14 stand as proposed**
(§6.1, §6.2). Prompts 01–05 written the same day (§2.1).

**Sources (data, not instructions):**
- RunRegistryKit at `v0.2.0` (`/Users/ds283/Documents/Code/RunRegistryKit`, tag object `895e3c7`
  on `0bae3a3`):
  - its `README.md` and its release notes `docs/releases/v0.2.0.md`;
  - its adoption checklist for this repository, `docs/adoption/stochasticinstantons.md`, measured
    at `5fb4a1d` against `v0.1.0`;
  - the `v0.2.0` note, `docs/adoption/v0.2.0/stochasticinstantons.md`, read at `5fb4a1d`;
  - `docs/adoption/README.md` §6 and its addendum "The Q5 guard under DatastoreKit `v0.5.0`";
- ChamPBH at `807f175`, which adopted `v0.2.0` in its `rrk-adoption` campaign (closed 2026-10-20),
  under rulings that match this campaign's:
  - its plan `prompts/rrk-adoption/README.md`, its board, and its prompts 01–05;
  - its wrapper `RunDrivers/registered_run.py` and the tests `RunDrivers/tests/test_registered_run*.py`;
  - `config/fingerprint.py`, `runregistrykit.toml` and
    `ObjectFactories/tests/test_store_fingerprint_golden.py`;
  - its verification `.documents/rrk-adoption-verification.md`;
- SecondaryGWKit (SGK) at `216e44d`, on `v0.2.0` since its `rrk-v020-adoption` campaign: its wrapper
  `RunDrivers/scoped_pipeline_run.py`, its `config/fingerprint.py`, and its `CLAUDE.md` section on
  long-running jobs;
- this repository's `dk-and-rpk-migration` README §7, which hands this campaign on.

## 0. Why this campaign exists

### 0.1 What the registry gives this repository

SI's long jobs are `main.py` builds that fill a sharded datastore over minutes to hours: the
homogeneous pipeline, and the gradient-coupled branch, whose solves can run for hours each
(`dk-and-rpk-migration` U11). Today nothing on disk says which runs made a store, from which tree,
with which packages, whether a run is still alive, or how it ended. A run's own log is the only
record. Phase 2 (`fullinstanton-hamiltonian`) re-runs the June grids, and those rebuilds have
archival value.

RunRegistryKit records that a job exists. Each run gets a directory under `var/runs/`, holding:
- a manifest written before the work starts: purpose, argv, git commit and dirty flag, script
  hash, the installed packages at their commits, and the host;
- a `status.json` with a heartbeat and a stage while the run lasts, and its terminal state at the
  end.

Its store layer keeps a sidecar, `<stem>.manifest.json`, beside each datastore. The sidecar says
what the store is for, which runs made it, and its content fingerprint when the last run finished.
`copy`, `move`, `fingerprint` and `retire` then act on the store under that record. The package
records; it does not schedule, supervise, restart or lock.

### 0.2 What ChamPBH and SGK do, which this campaign follows

Neither registers a run inside `main.py`. Every registered run goes through a **wrapper driver**,
and `main.py` runs byte-identically with or without it (R2). ChamPBH's wrapper,
`RunDrivers/registered_run.py`, is the closest model, since its `main.py` has the same shape as
SI's: a module-level script that attaches to an external cluster with `--ray-address` and ends in
`with ShardedPool(...)`. The wrapper:
1. **Registers before anything starts.** It parses `main.py`'s arguments with `main.py`'s own
   parser, refuses what would be recorded wrongly, and calls `runregistrykit.begin(...)` with
   `results` = the database, before Ray starts. A refusal from `begin` (a store an unfinished run
   names; a retired store) is one `!!` line, exit 2, and nothing is created.
2. **Beats from stdout.** Pass-through proxies copy every write into the run directory's
   `stdout.log` and `stderr.log`. A stdout line refreshes the heartbeat, at most every 30 s, and
   `StageTracker` reads the stage off RayWorkPool's banners and progress lines. stderr never beats.
   The manifest's `heartbeat_means` says exactly what a fresh beat asserts.
3. **Records a signal.** `ray.init` installs its own `SIGTERM` handler, and absl's aborts the
   process about 3 s later. So the wrapper wraps `ray.init` and installs its own handler straight
   after it, which records `killed`, `128 + signum`.
4. **Runs `main.py` unchanged** with `runpy.run_path(..., run_name="__main__")`.
5. **Finishes after `main.py` unwinds**, once the pool has closed, with `done`, `failed` or
   `killed` and `fingerprint=True`, and exits with `main.py`'s code. It prints
   `** driver exit status N` last, which is the marker SI's `interrupt_when.py` reads.
6. **Leaves the store's sidecar to a person** (R4). `store create --purpose …` is run on the store
   after its first close. Until then a run's status says `fingerprint_sidecar: "not written …
   (there is none)"`, and `written` after it.

**This is a third copy of one wrapper.** ChamPBH's is SGK's carried over. SI's would be ChamPBH's
carried over, differing in `describe_scope` (SI's arguments), `HEARTBEAT_MEANS` (SI's notify
intervals and the gradient branch) and the refusals' details. The user accepted the trade-off in
ruling R2. §7 records the observation that its generic part could belong in RunRegistryKit; that
is out of this campaign's scope.

### 0.3 Measured on 2026-10-23, at `8b4f615`

Measured by the evaluation that preceded this plan. Nothing in SI's tree, venv or stores was
changed: the probes ran in a session scratchpad, on copies.

**The package.**
- `v0.2.0` is tagged and pushed (`refs/tags/v0.2.0^{}` = `0bae3a3`).
- `pip install --dry-run "runregistrykit[stores] @ …@v0.2.0"` into SI's venv: **would install
  `runregistrykit-0.2.0` and nothing else.** The `datastorekit` line it needs is already pinned
  (`requirements.txt:16`, `v0.5.0`; the extra requires `>=0.4.0`).
- The venv: Python 3.13.16, `datastorekit` 0.5.0, `raypoolkit` 0.2.0, `ray` 2.55.1, `SQLAlchemy`
  2.0.46. All are inside the declared range. RunRegistryKit's CI tests `datastorekit` 0.4.0 only.
- **Its suite on SI's venv**, from a clone at the tag with the package on `PYTHONPATH`: 410 tests,
  406 passed, 1 skipped, and 3 failures. Each failure is a test that starts a fresh interpreter,
  which cannot see a package supplied only by `PYTHONPATH`. They pass once the package is installed
  (01 runs the suite again on the installed package; acceptance item 2).
- **The store layer over SI's registry.** `DatastoreKitFingerprinter(config.datastore.factories, 1)`
  on a copy of RH2's closed `11-reference` store: all 24 classes read, `problems: none`, about 5 s
  for 24 MB. A second fingerprint compared equal to the one recorded.
- **The core.** On that copy, `begin` → `record`/`heartbeat` → `finish(fingerprint=True)` was
  recorded `done`, with the fingerprint written to the sidecar. A run that died after `begin` was
  shown `stale`, `!!`, and a second `begin` on its store was refused with nothing created. `end`
  recorded it `lost` after checking that its pid did not answer, and `begin` was then accepted.
- A store with no sidecar gets its fingerprint in the run's status and `fingerprint_sidecar: not
  written`. A store that does not exist yet at `begin` is accepted; that is every fresh build.
- The store operations refuse when the runs root is not a directory. 01 creates `var/runs/`.
- The six open RunRegistryKit issues (its `docs/OPEN_ISSUES.md` §1.3) bear on nothing SI does: one
  is Python 3.14 only, one is a docstring, three are malformed records, and one is a killed process
  that its parent has not yet reaped.

**This repository.**
- No code imports a run registry. `.gitignore` does not ignore `var/`, and there is no `var/`.
- `git status --porcelain` is empty. The files at the root that are not tracked are all ignored,
  so a run begun from this checkout is recorded clean.
- `main.py` runs at module scope:
  - the provenance line at `:101`;
  - the `--inventory` branch, which reads the closed store and exits before Ray, at `:107`;
  - refusals that exit 2 at `:114` and `:129`;
  - `ray.init(address=args.ray_address)` at `:131`;
  - `with ShardedPool(…) as pool: execute(pool, units)` at `:1273`.

  It installs no signal handler.
- **The queues' printing.** `main.py` sets no notify interval, so its titled queues ("STAGE 1:
  BACKGROUND INFLATIONARY TRAJECTORIES", …, "STAGE 4: COMPACTION FUNCTIONS AND MASSES") use
  RayPoolKit's defaults: a progress line at most every 60 s (`DEFAULT_NOTIFY_MIN_INTERVAL`), and
  only after completed work. Several queues are silent (`title=None`).
- `--database` may come from a YAML config: the parser is `configargparse`
  (`config/argument_parser.py`, `--config` with `is_config_file=True`). The wrapper must use the
  same parser.
- **The registry.** `config.datastore.factories`: 24 classes in the inventory, 22 spec
  definitions, every class covered and none excluded (`dk-and-rpk-migration` 10b). One spec,
  `GradientCoupledInstanton`'s, declares a non-empty `extra_values`.
- **The provenance helper.** `utilities.installed_package_provenance` is RunRegistryKit's
  `package_provenance` but for one redundant statement (the checklist's item 4). It stays (R3).
- **The tests.** One root, `tests/` (pytest, no `testpaths`, no `tests/__init__.py`). The markers
  are `integration` (a live Ray and a store) and `slow`. `tests/test_inventory_store.py` builds a
  two-shard store of synthetic rows through the package's pool under a private Ray, in a
  subprocess, with a row of every class (`integration`).
- **The rehearsal tooling** is `dk-and-rpk-migration`'s, under
  `.documents/dk-and-rpk-migration/rehearsal/`: `ray_cluster.sh` (SI's isolated cluster and the
  shared lock), `build.sh`, `interrupt_when.py` and `stage_counts.py`. A build of
  `quadratic-minimal.yaml`, homogeneous only (U11), takes about 30 s (stages 6.0, 12.9, 9.6 and 2.3
  s at RH2).

### 0.4 Baselines

`CLAUDE.md`'s suites at `8b4f615` (`dk-and-rpk-migration`'s close): default **732** (731 passed, 1
skipped); `integration` **67** (66 passed, 1 skipped); `slow` **69**. `1c223e8` changes only that
campaign's board. 01 measures the first two again on the branch before changing anything; `slow` is
not run, since no prompt touches the paths that select it (`.claude/rules/test-selection.md`).

## 1. Scope

**In scope:**
- the pin, `runregistrykit.toml`, `var/` ignored, and the rules (01);
- the fingerprinter, its format number, the guard against a spec changing without a bump, and a
  golden fingerprint (02);
- the wrapper driver, `RunDrivers/registered_run.py`, with tests that need no Ray (03);
- a rehearsal on SI's isolated cluster: a registered build, an interrupted one resumed, a
  hard-killed one ended, `store create` and the fingerprint (04);
- the documents, the handover and the drafts of RunRegistryKit's gate records (05).

**Out of scope:**
- **`main.py`, the plot scripts and `utilities.py`'s code.** They stay launchable without
  RunRegistryKit (R2), and none of them imports it (R3). 05 adds one sentence to the helper's
  docstring (P12).
- **Registering the plot scripts or `--inventory`** (R5).
- **What the code computes.** No stored value changes.
- **Existing stores**: the June and July stores (read at the tag `pre-datastorekit`), and the
  rehearsal stores under `~/ScienceData/StochasticInstantons-rehearsals/`. None is opened, adopted
  or given a sidecar (P10). The June stores cannot be fingerprinted at this tree in any case:
  they are unreadable by the tree since `dk-and-rpk-migration` 09.
- **`dk-and-rpk-migration`'s rehearsal tooling**: used, not edited. 04 writes its own launcher
  (P8).
- **Phase 2's builds**, which are that campaign's.
- **RunRegistryKit, DatastoreKit, RayPoolKit, ChamPBH and SGK:** read, never edited. A defect in
  RunRegistryKit stops the prompt and is reported to that repository (`CLAUDE.md`, "Protected
  infrastructure").

## 2. Prompts

| # | Prompt | Covers | Model |
|---|---|---|---|
| 01 | `01-pin-config-and-rules.md` | The pin and the venv; RunRegistryKit's suite on the installed package; `runregistrykit.toml` without `[stores]`; `var/` in `.gitignore`; the rules (`CLAUDE.md` and `.claude/rules/run-registry.md`); the `SessionStart` discovery hook (U1); a test of the config | Sonnet |
| 02 | `02-the-fingerprinter.md` | `config/fingerprint.py` (format 1, `SPEC_DIGESTS`, the fingerprinter); `[stores]` in the config; the format guard, with the `v0.5.0` amendment; a golden fingerprint of a temporary store | Sonnet |
| 03 | `03-the-wrapper.md` | `RunDrivers/registered_run.py`, after ChamPBH's: register, proxy and beat, the signal handler after `ray.init`, run `main.py` unchanged, finish with the fingerprint, the refusals. Tests with no Ray | Opus |
| 04 | `04-rehearse-registered-runs.md` | On the isolated cluster, under the lock: a registered build; a `SIGTERM`ed build resumed; a `SIGKILL`ed build ended with `end` and resumed (U2); `store create`; the fingerprint at finish; the stores compared | Opus |
| 05 | `05-close.md` | `CLAUDE.md`, the rules and the architecture documents; the stale prose (P12); the drafts of RunRegistryKit's gate records; the board closed, the indexes | Sonnet |

### 2.1 When each prompt file is written

01–05 are written once the user has ruled on §6.1 and §6.2 (*written 2026-10-23, after the rulings*). 01 comes first. 02 and 03 each need only
01, so they are independent of each other. 04 needs 02 and 03. 05 needs 04.

### 2.2 The charters

**01 — The pin, the config and the rules** (Sonnet).
- **What it changes.**
  1. `requirements.txt`: `runregistrykit[stores] @ git+https://github.com/ds283/RunRegistryKit@v0.2.0`,
     in a commit of its own, beside the existing `datastorekit` line. The venv is installed from
     it, not editable.
  2. `runregistrykit.toml` at the root: `runs_root = "var/runs"`, `stores_root =
     "var/datastores"` (R6), `distributions = ["datastorekit", "raypoolkit"]` (the helper's
     `RECORDED_DISTRIBUTIONS`). No `[stores]` yet, since 02 writes the module it names. `var/runs/`
     and `var/datastores/` are created.
  3. `.gitignore`: `var/`.
  4. **The rules**, in SI's form: a short binding section in `CLAUDE.md`, "Long-running jobs",
     and the detail in a new `.claude/rules/run-registry.md` with no `paths:` frontmatter, as the
     other rules files. Together they give:
     - the package and where it records; the six rules, with `./venv/bin/python -m
       runregistrykit list` as the discovery command; the route after a hard kill (`end`, then the
       build again, which prunes unvalidated rows at open: SI's `--prune-unvalidated` defaults to
       on);
     - the wrapper as the way to launch a registered run, with a forward reference to 03;
     - that `main.py` stays launchable without the wrapper, and that the plot scripts and
       `--inventory` are never registered (R5);
     - stores under `var/datastores/`, and **never `git clean -x` or `-X`**, which deletes ignored
       files;
     - that production runs are the user's, and that no prompt starts one but 04's rehearsal.
  5. **The discovery hook** (U1): a `SessionStart` hook in the project's `.claude/settings.json` that runs `./venv/bin/python -m runregistrykit list` from the root.
- **Acceptance.**
  1. `pip show runregistrykit` is 0.2.0, its `direct_url.json` names `0bae3a3`, and it is not
     editable. `datastorekit`, `raypoolkit`, `ray` and `SQLAlchemy` are unmoved.
  2. RunRegistryKit's suite, run on the installed package from a temporary clone at the tag: 410
     tests, OK (one skipped). This closes §0.3's three failures.
  3. `python -m runregistrykit list` on the empty runs root prints no run and exits 0.
  4. `git check-ignore var/runs/x var/datastores/x.sqlite` matches both.
  5. A new test, `tests/test_registry_config.py`: `find_client_root(client_root=<root>)` gives
     these roots and distributions; the config has no key the package does not know; `var/` is
     ignored.
  6. The suites at §0.4's counts plus the new tests.
  7. Deliberate breakages: `var/` removed from `.gitignore`; a misspelt key in the config.

**02 — The fingerprinter** (Sonnet).
- **What it changes.**
  1. `config/fingerprint.py`, after ChamPBH's and SGK's:
     - `FINGERPRINT_FORMAT = 1`, with its history in the docstring;
     - `SPEC_DIGESTS = {1: [[class, sha256], …]}`, in registry order;
     - `fingerprinter = DatastoreKitFingerprinter(factories, FINGERPRINT_FORMAT)`.
  2. `runregistrykit.toml` gains `[stores] fingerprinter = "config.fingerprint:fingerprinter"`.
  3. `tests/test_fingerprint_format_guard.py`: RunRegistryKit's recipe (its
     `docs/adoption/README.md` §6) **with the `v0.5.0` amendment**, which leaves out an empty
     `extra_values` (P5). The test asserts that the list of digests equals
     `SPEC_DIGESTS[FINGERPRINT_FORMAT]`.
  4. `tests/test_store_fingerprint_golden.py` (`integration`): a temporary store with a row of
     every class that declares a spec, built as `tests/test_inventory_store.py` builds its store
     (P6). Its fingerprint, `taken` removed, equals a committed golden file under `tests/data/`.
     `load_fingerprinter` loads the config's fingerprinter.
- **Acceptance.**
  1. The guard passes with no Ray. The golden test passes under `RAY_ADDRESS=local pytest -m
     integration`, with no store outside a `tempfile` directory.
  2. `python -m runregistrykit store fingerprint <the temporary store>` prints the digest the
     golden file holds.
  3. The suites at 01's counts plus the new tests.
  4. **Deliberate breakages**, each shown failing:
     - a leaf added to one spec, with no bump;
     - the format bumped with no new pin;
     - `GradientCoupledInstanton`'s `extra_values` emptied: its digest moves, and no other class's
       does;
     - a row changed in the golden store.

**03 — The wrapper** (Opus).
- **What it changes.** A new package `RunDrivers/` with `registered_run.py` (P1):

  ```
  PYTHONPATH=. ./venv/bin/python RunDrivers/registered_run.py --campaign C --prompt N \
      --register SLUG --purpose "one line" -- <main.py's arguments, verbatim>
  ```

  1. **It parses `main.py`'s arguments** with `config.argument_parser.create_argument_parser()`,
     so that a `--database` from a YAML config is seen. It refuses before `begin()`, exit 2: a run
     with no database, an empty one, and an `--inventory` run (P3).
  2. **It calls `runregistrykit.begin(…)`** before Ray starts:
     - `campaign`, `prompt`, `slug` and `purpose` from its flags (P2);
     - `script` = `main.py` (P4);
     - `results` = the database;
     - `scope` from `main.py`'s arguments: the config file, `--targets`, the model and grid
       options, the shards and the job name;
     - `heartbeat_means`, SI's version of ChamPBH's sentence (P7).

     A `RuntimeError` from `begin` is a one-line `!!` refusal, exit 2, and nothing is created. A
     `ConfigError` propagates.
  3. **Its streams** are ChamPBH's `RegisteredStream` and `StageTracker`, carried over, with stage
     patterns matched to SI's banners ("STAGE n: …") and progress lines. stdout beats at most every
     30 s and sets the stage; stderr is copied and never beats.
  4. **It wraps `ray.init`** so that its `SIGTERM`/`SIGINT` handler is installed straight after
     Ray's own, and records `killed`, `128 + signum`. A signal before Ray starts is handled by a
     handler installed at registration.
  5. **It runs `main.py`** with `runpy.run_path(<root>/main.py, run_name="__main__")`, with
     `sys.argv = [main.py, *its arguments]`.
  6. **It finishes after `main.py` returns or raises**, with the pool closed: `alarm(0)` first,
     then `done` (exit 0), `failed` (any other exit or exception) or `killed` (a signal), each with
     `fingerprint=True`, then it exits with `main.py`'s code.
  7. It prints the run id, the manifest's path and the `list` command at registration, and
     `** driver exit status N` at the end.
- **Acceptance.** Tests in `tests/test_registered_run*.py` (P11). None starts Ray but the fingerprint tests (item 3, `integration`): `ray.init` is
  stubbed, and the program run is a stand-in script that prints SI's RayWorkPool lines. Each test
  makes its own temporary runs root and client root.
  1. **What is recorded:** the manifest exists before the program's first line runs, with `script`
     = `main.py`'s path and hash, `results`, `scope`, `heartbeat_means` and `packages`; beats are
     throttled to 30 s, with stages read off the stand-in's lines, and stderr does not beat; exits
     0, 1, 2 and an exception give `done` and `failed` with their codes, and the wrapper exits with
     the same code.
  2. **The handlers:** a `SIGTERM` after the stubbed `ray.init` gives `killed`/143, in a
     subprocess; a handler installed before `ray.init` is replaced as Ray replaces it, and the
     wrapper's is reinstated.
  3. **The fingerprint:** a run on a temporary store with a sidecar records `fingerprint_sidecar:
     written`; one without a sidecar records "not written".
  4. **The refusals:** a second `begin` on a store an unfinished run names is refused, exit 2, with
     no run directory created; after `python -m runregistrykit end`, the same `begin` is accepted;
     `--inventory` and a missing database are refused before `begin`.
  5. **`main.py` itself is unchanged:** `git diff 1c223e8 -- main.py` is empty, and `main.py`
     imports nothing of `runregistrykit` (by `ast`).
  6. The suites at 02's counts plus the new tests.
  7. Deliberate breakages: the handler installed before `ray.init` only; `fingerprint=True` passed
     while the program runs; the exit code dropped.

**04 — Rehearse registered runs** (Opus). Under the shared lock, on SI's isolated cluster
(`ray_cluster.sh start "rrk-adoption 04"`, `--ray-address 127.0.0.1:6390`), from this checkout. The
grid is the `dk-and-rpk-migration` rehearsal's: `quadratic-minimal.yaml`, `--targets homogeneous`,
`--n-collocation-points 5 --alpha-regularization 0.01`, about 30 s a build. Every build is launched
through the wrapper, detached, by a launcher of this campaign's (P8), and checked once.
- **What it does.**
  1. **`reference`**, into `var/datastores/rrk-adoption-04-reference.sqlite`. `list` shows it
     `running`, then `done`; its status says `fingerprint_sidecar` "not written … (there is none)";
     then `store create --purpose …` and `store fingerprint --write`.
  2. **`resumed-a`**, into `var/datastores/rrk-adoption-04-resumed.sqlite`, `SIGTERM`ed by
     `interrupt_when.py` at `STAGE 2`. It is recorded `killed`/143 within about a second, with its
     fingerprint. Then `store create` on the closed store.
  3. **`resumed-b`** (U2), on the same store, `SIGKILL`ed during a later stage: `list` shows it
     `stale`, `!!`; a `resumed-c` launch is refused with nothing created, naming `end`; `end <run>
     --reason …` records it `lost`.
  4. **`resumed-c`** (SI prunes unvalidated rows at open by default) runs to `done`, and its fingerprint is written to
     the sidecar.
  5. **The stores compared:** `tools/compare_stores.py` on the reference and the resumed store, and
     on the reference and RH2's `11-reference` (read-only, P10). Each pair is equal bit for bit,
     the criterion `dk-and-rpk-migration` README §4.3 set and RH0–RH2 met: nothing that computes
     has changed. The recorded fingerprints of the reference and the resumed store agree.
  6. **Measured:** the fingerprint's time at finish; the heartbeat ages read from `status.json`
     (`list`'s `AGE` is the run's age, not the heartbeat's: ChamPBH's verification §1.4); the Ray
     processes after each kill (`ray_cluster.sh status`); and `git_dirty` as recorded. On Ray
     2.55.1 attached to an external cluster, that Ray installs its `SIGTERM` handler as ChamPBH
     found on 2.53 (P9).
- **Acceptance.**
  1. The four builds are recorded as above, every manifest written before its driver's first line.
  2. The resumed store equals the reference by `compare_stores.py`.
  3. No SI Ray process outlives the cluster's `stop`; the lock is released.
  4. `.documents/rrk-adoption/verification.md` created, with the outputs under
     `.documents/rrk-adoption/out/` (small text only).
- **Out.** The stores stay under `var/datastores/` until the user removes them (§3).

**05 — Close** (Sonnet).
- `CLAUDE.md`: the wrapper's sentence made definite, the suite counts, and the test-selection
  counts in `.claude/rules/test-selection.md`.
- `.documents/architecture-summary.md` and `.documents/INFRASTRUCTURE.md`: the wrapper,
  `config/fingerprint.py`, `runregistrykit.toml` and `var/`.
- The stale prose (P12).
- The drafts of the two gate records in RunRegistryKit (P13).
- The board closed; `.prompts/INDEX.md` and `.documents/OPEN-ISSUES.md`. The final suites.

## 3. Stores

Only 04's: `var/datastores/rrk-adoption-04-reference.sqlite` and `…-resumed.sqlite`, with their
shards, inside the repository and ignored by git. 01, 02, 03 and 05 open no store but the tests'
temporary ones. No existing store is opened.

## 4. The interfaces between prompts

- **01 ships** the pin, the config without `[stores]`, `var/` ignored, and the rules. 02 adds
  `[stores]`; 03 relies on the config's roots.
- **02 ships** `config.fingerprint:fingerprinter`, named in the config. 03's fingerprint tests and
  04's `store` commands load it.
- **03 ships** `RunDrivers/registered_run.py`, which 04 runs unchanged. If 04 finds a defect in it,
  04 stops; the fix is a lettered prompt (03b), not an edit in 04.
- **04 ships** the measurements and the verification document. 05's handover quotes them.

## 5. The rules this campaign runs under

`CLAUDE.md`'s critical rules and its protected-infrastructure list. From `dk-and-rpk-migration`
(its README §5):
- deliberate breakages, recorded as diffs;
- no stored science value changes;
- no test needs Ray outside the `integration` marker, and none opens a store outside a `tempfile`
  directory;
- a package defect is reported upstream and never worked around here;
- no change in a sibling repository;
- no `ray stop`, and a cluster only through `ray_cluster.sh`;
- the shared rehearsal lock: a held lock is a stop, never a wait;
- the results-note template of its §5.1.

And:
- **`main.py` and the plot scripts are byte-identical at every commit of the campaign**
  (`git diff 1c223e8 -- main.py plot_*.py` empty), and `utilities.py` is too but for P12's one
  sentence at 05.
- **Existing tests are not modified**, except the docstring sentence of P12.
- **04's rehearsal is a one-off exception** to the rule that no campaign prompt starts a `main.py`
  run with a datastore, as `dk-and-rpk-migration`'s U2 was.
- **No agent polls a run** (the registry's rule 4). 04 launches, checks once, and waits on the
  task's notification or a `Monitor` on the log's `** driver exit status` line.

## 6. Decisions

### 6.0 Ruled by the user, 2026-10-23

- **R1 — the store layer**, adopted with the core. It follows from R4, which rules on the
  sidecars.
- **R2 — a wrapper, not `main.py`.** "I don't want `main.py` to depend on RunRegistryKit. It
  should be possible for me to launch jobs by hand without it. I'd like wrapper scripts, like the
  sibling ChamPBH and SecondaryGWKit projects already use. There are disadvantages, but it's a
  trade-off."
- **R3 — the provenance helper is kept.** The user first ruled to substitute
  `runregistrykit.package_provenance`. The substitution would make `main.py` and both plot scripts
  import the package, against R2, and the user then ruled to keep SI's helper, as ChamPBH did (its
  U1). Every registered run's manifest records the same fields under `packages`.
- **R4 — the sidecar**: "don't create in `main.py`. Use the same pattern as ChamPBH and
  SecondaryGWKit": a person runs `store create --purpose …` after the store's first close (§0.2
  item 6).
- **R5 — what registers.** "Plot scripts don't register. This is really for long-running tasks or
  those that have archival value."
- **R6 — stores in `var/datastores/`**, the package's default `stores_root`, as ChamPBH and SGK.
- **R7 — the branch.** `dk-and-rpk-migration` is merged into `main` first (its P15). *Done
  2026-10-23 at the user's instruction:* a fast-forward of `main` from `7bb3efd` to `1c223e8`, not
  pushed (that board's §5.31). `rrk-adoption` is cut from `main` at `1c223e8` and merged back at
  the close.

### 6.1 Ruled by the user

**Ruled on 2026-10-23: U1 and U2 as recommended.** The recommendation in each row is the decision.

| | Recommended (ruled) | The alternative (rejected) |
|---|---|---|
| **U1** — discovery | **A `SessionStart` hook** in the project's `.claude/settings.json` that runs `./venv/bin/python -m runregistrykit list`, so that every session starts by reading the registry. The package's rule 1 says it "supports the habit; it cannot enforce it", and its README calls a registry nobody reads worse than none. `list` reads only `var/runs/` and takes well under a second | The rule in `CLAUDE.md` alone, as ChamPBH and SGK |
| **U2** — the hard-kill route in 04 | **Rehearsed** (04 item 3): `SIGKILL`, `stale`, a refused resume, `end`, then a resume to `done`. It is the route a rebuild needs after a power loss, and a build is 30 s | `SIGTERM` only; the route is then covered by 03's tests alone |

### 6.2 Proposed by the planner (P1–P14)

Accepted as proposed unless the user rules otherwise. The user gave no ruling on any of them, so
all fourteen stand as proposed.
- **P1 — the wrapper's place**: `RunDrivers/registered_run.py` (a new package,
  `RunDrivers/__init__.py`), as ChamPBH and SGK, run as `PYTHONPATH=. ./venv/bin/python
  RunDrivers/registered_run.py`. `tools/` keeps repository tooling.
- **P2 — its flags.** `--campaign`, `--prompt`, `--register SLUG` and `--purpose` are all
  required, since the wrapper exists only to register; `main.py`'s arguments follow `--`. An
  unregistered run is `main.py` itself (R2). For a user's own launch, `--campaign` names the work
  it serves (for example `fullinstanton-hamiltonian`) and the slug matches `--job-name`.
- **P3 — the refusals before `begin`**: no database, an empty one, and `--inventory` (R5), each
  exit 2 with one `!!` line. `main.py`'s own refusals after registration (a `--drop` it refuses,
  for one) are recorded `failed` with their exit code, which is true.
- **P4 — the `script` a manifest records** is `main.py`, so that its hash is the hash of what
  computed; the wrapper is covered by `git_head` and `git_dirty`. As ChamPBH (its U3).
- **P5 — the format guard** uses RunRegistryKit's recipe with the `v0.5.0` amendment: an empty
  `extra_values` is left out of a plain spec. SI starts at `v0.5.0` with no digest pinned, so the
  amendment only keeps SI's digests computed as ChamPBH's and SGK's are.
- **P6 — the golden store** is built as `tests/test_inventory_store.py` builds its store
  (synthetic rows through the package's pool, in a subprocess under a private Ray, every class
  present, the gradient branch included), by importing that builder or, if it cannot be imported
  without modifying the file, by a copy, recorded as a deviation. The rehearsal stores cannot
  serve: they hold no gradient rows (U11).
- **P7 — the heartbeat.** ChamPBH's streams and tracker, 30 s throttle. With RayPoolKit's default
  60 s floor a beat arrives about every minute while work completes. `heartbeat_means` states what
  it does not assert: a queue whose items each print nothing for longer than the staleness window
  (900 s) is shown stale while it works. **The gradient branch is such a queue**: its solves have
  run for hours (U11). `list --stale-after` is the reader's remedy, not a longer window in the
  package.
- **P8 — 04's launcher** is `.documents/rrk-adoption/rehearsal/build_registered.sh`: the
  `dk-and-rpk-migration` `build.sh` command, through the wrapper, detached (`nohup`), with its log,
  pid file and marker. `ray_cluster.sh`, `interrupt_when.py` and `stage_counts.py` are used from
  `dk-and-rpk-migration`'s folder, unchanged.
- **P9 — the signals**: ChamPBH's design, from SGK's audit. 04 measures it on Ray 2.55.1 attached
  to SI's external cluster.
- **P10 — existing stores** are neither adopted nor given a sidecar, as ChamPBH's R5. Deleting the
  rehearsal stores stays the user's (`dk-and-rpk-migration` close, decision 3). **One read**: 04
  compares its `reference` with RH2's `11-reference` by `tools/compare_stores.py`, which opens every
  file `mode=ro`, as `dk-and-rpk-migration` 11 compared RH2 with RH1. Nothing else of an existing
  store is opened.
- **P11 — tests** live in `tests/`, SI's only root: `test_registry_config.py` (01);
  `test_fingerprint_format_guard.py` and `test_store_fingerprint_golden.py` (02);
  `test_registered_run*.py` (03). They need no Ray but where a test needs a closed store with real
  rows, which SI builds only through the pool under a private Ray: 02's golden test and 03's
  fingerprint tests, which are `integration`. None is `slow`.
- **P12 — the stale prose**, at 05:
  - `.claude/rules/datastore-factories.md:240` and `tests/test_inventory_specs.py:33` (docstring
    only) say SI "will" adopt RunRegistryKit; they become present tense;
  - `utilities.py:191`'s docstring says a later move to a shared registry "is a substitution": one
    sentence is added saying that the substitution was declined (R3). `utilities.py` is on
    `CLAUDE.md`'s protected list, so 05's prompt names it and quotes the sentence.
- **P13 — RunRegistryKit's gates.** Its `extraction` board's G4 (SI adopts a release) and its
  `interrupted-runs` board's G3 (SI adopts `v0.2.0`) are recorded in that repository. 05 drafts both
  records, quoting the checklist's acceptance (its item 9; item 4 does not apply, by R3), and the
  user commits them, as with `dk-and-rpk-migration`'s G4 records.
- **P14 — issues.** None is opened or assigned at planning. No open issue in
  `.documents/OPEN-ISSUES.md` concerns how runs are launched or tracked. The models are: 01, 02 and
  05 Sonnet; 03 and 04 Opus.

## 7. What this campaign hands on

- **Phase 2's builds** launch through the wrapper, detached, into `var/datastores/`; `store create
  --purpose …` after a store's first close; after a hard kill, `python -m runregistrykit end RUN_ID
  --reason …`, then the build again with `--prompt` of the resuming launch (the open prunes
  unvalidated rows by default).
- **04's two stores**, kept under `var/datastores/` until the user removes them.
- **The two gate records** in RunRegistryKit (P13).
- **An observation for RunRegistryKit, not a request.** SI's wrapper is the third copy of SGK's
  (§0.2). The generic part (the stream proxies, the stage tracker, the signal latch and the finish
  after the program unwinds) could be a module of the package, with each client supplying its
  parser, its scope and its stage patterns. Whether to raise it there is the user's.
