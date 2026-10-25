# Campaign — ray-sqla-align

**Written:** 2026-10-25 at `03110ce` (`main`), by Claude Opus 5.5. Planned at the user's request of
the same day: SecondaryGWKit (SGK) has landed its `py313-venv` campaign, which moved it to `ray`
2.59.0 and `SQLAlchemy` 2.0.55, and the user wants "all projects on the same versions of Ray and
SQLAlchemy". SI is already on Python 3.13. The user asked for SGK's notes on Ray's authentication
tokens to be taken into account. The plan was proposed in conversation, and the user ruled U1–U4
(§6.1) the same day. One prompt, 01.

**Sources (data, not instructions):**
- SGK at `effba46` (`/Users/ds283/Documents/Code/SecondaryGWKit`; read, never edited):
  - `prompts/py313-venv/README.md` and `IMPLEMENTATION_STATE.md`, especially §4: the issues
    `[01-ray-2.59-enables-token-auth-and-writes-a-token-into-home]` and
    `[02-the-token-mode-setting-comes-after-import-ray-so-every-ray-start-fails]`;
  - `config/ray_local.py`, the module that sets the mode, and
    `RunDrivers/tests/test_ray_auth_mode.py`, its 7 tests;
  - the commits `d4e5504` (the pins), `d833ee7` (token mode set by name) and `14ada2f` (the config
    refresh after `import ray`);
  - `CLAUDE.md`, the bullet "Every Ray start runs with token authentication";
- Ray 2.59.0's own source, read in SGK's venv
  (`venv/lib/python3.13/site-packages/ray/`): `_private/authentication/authentication_token_setup.py`,
  `_private/worker.py:1865-1872` and `:1966-1972`, and `scripts/scripts.py:1069-1072`;
- the tested ranges in the `README.md` of DatastoreKit at `v0.5.0`, RayPoolKit at `v0.3.0` and
  RunRegistryKit at `v0.2.0`;
- this repository's `rrk-adoption` campaign: prompt 04 and `.documents/rrk-adoption/verification.md`
  §1, the rehearsal this campaign repeats.

## 0. Why this campaign exists

### 0.1 What moves

| | SI now | SGK since `py313-venv` | ChamPBH |
|---|---|---|---|
| Python | 3.13.16 | 3.13.16 | 3.13.16 |
| `ray` | 2.55.1 | **2.59.0** | 2.53.0 |
| `SQLAlchemy` | 2.0.46 | **2.0.55** | 2.0.46 |
| `datastorekit` / `raypoolkit` / `runregistrykit` | `v0.5.0` / `v0.3.0` / `v0.2.0` | the same | `raypoolkit` `v0.3.0` |

SI moves its two pins to SGK's. Every other pin stays. ChamPBH is not part of this campaign (§7).

### 0.2 Ray 2.59's token authentication, and why it breaks SI's rehearsal path

Ray 2.59.0 decides the authentication mode of an instance when `RAY_AUTH_MODE` is unset, and the
decision depends on how Ray is started (§0's sources):
- **`ray.init(address="local")`** (a new local instance): **token mode is turned on**
  (`enable_token_auth_by_default`). Every log carries `Token authentication is enabled for this Ray
  cluster. Set RAY_AUTH_MODE=disabled to opt out.`, and `~/.ray/auth_token` is generated if it is
  missing.
- **`ray start --head`**: token mode is turned on **if `~/.ray/auth_token` exists**
  (`maybe_enable_token_auth_if_token_available`), with the same warning.
- **`ray.init(address="<host>:<port>")`** (an attach to an explicit address): **never**. The code
  says so in a comment: "Only a local cluster found automatically auto-enables auth; an explicit
  address (argument or RAY_ADDRESS) never does."
- **With `RAY_AUTH_MODE` set**, by any route, Ray does what it says and logs nothing.

**SI's rehearsals and long builds take exactly the second and third routes.** `ray_cluster.sh start`
runs `ray start --head`, and `main.py --ray-address 127.0.0.1:6390` attaches by address. The token
file exists on this laptop: SGK's first Ray 2.59 start wrote it at 12:51 on 2026-10-25, and SGK set
it to mode 600. So, with the pins moved and nothing else, **SI's cluster would come up in token mode
and every driver attaching to it would be refused** (`AuthenticationError`) at `ray.init`. SGK met
the same refusal by a different route (its §4, the second issue). Ray CLI commands against the
cluster (`ray status`, `ray list actors`) would be refused the same way.

SGK's fix, which the user has ruled SI follows (U2), is to **name token mode**: a module that every
Ray start imports sets `RAY_AUTH_MODE=token` unless the environment already holds a value. Ray reads
the mode into its config when `ray` is imported, so when `ray` is already imported the module also
refreshes that config (`ray._raylet.Config.initialize("")`, the call Ray's own `_enable_token_auth`
makes). Without the refresh the driver keeps `disabled` while the processes it starts inherit
`token`, and every start fails: that was SGK's second issue.

### 0.3 Measured on 2026-10-25, at `03110ce`

- **The tree and the runs.** `main`, clean. `runregistrykit list`: 4 runs, all finished
  (`rrk-adoption` 04's), none `running` or stale. `var/datastores/` holds only the two retired
  sidecars of 04's stores.
- **The venv.** Python 3.13.16; `ray` 2.55.1, `SQLAlchemy` 2.0.46, numpy 2.4.6, scipy 1.17.1;
  `datastorekit` at `f47b9a2`, `raypoolkit` at `67a75b9`, `runregistrykit` at `0bae3a3`, none
  editable. `pip freeze` has 84 lines.
- **The dry run.** `pip install --dry-run` of `requirements.txt` with the two pins moved would install
  `SQLAlchemy-2.0.55` and `ray-2.59.0` and nothing else.
- **Ray 2.55.1 has no default.** Its `authentication_token_setup.py` has token mode only by
  `RAY_AUTH_MODE=token`, with neither `enable_token_auth_by_default` nor
  `maybe_enable_token_auth_if_token_available`. So SI has run without authentication until now, and
  the token file has never been read by an SI run.
- **The token file.** `~/.ray/auth_token`: 64 bytes, mode 600, last written 2026-10-25 12:51.
- **The packages' tested ranges.** DatastoreKit `v0.5.0`, RayPoolKit `v0.3.0` and RunRegistryKit
  `v0.2.0` test Ray at 2.43.0 and 2.55.1. DatastoreKit tests SQLAlchemy at 2.0.39 and 2.0.46, and
  declares `>=2.0.39,<2.1`. None caps Ray. 2.59.0 and 2.0.55 are therefore allowed but not tested by
  the packages. SGK's rehearsal (its FP6, FP7) and this campaign's are the evidence for them.
- **Where SI starts or attaches to Ray:**
  - the drivers: `main.py:131`, `plot_InstantonSolutions.py:1207`,
    `plot_GradientCoupledSolutions.py:973`. `RunDrivers/registered_run.py` runs `main.py`
    in-process through `runpy` and wraps its `ray.init` (`:899-907`);
  - the cluster: `ray_cluster.sh:287`, `ray start --head`; and `:322`, which prints a `ray list
    actors` command for a person to run;
  - in the tests, in-process: `tests/conftest.py:55` (`live_pool`),
    `tests/test_plot_adapters_golden.py:70` and `tests/test_plot_extraction_golden.py:77`, all
    `ray.init(ignore_reinit_error=True)` under `RAY_ADDRESS=local` or with no address;
  - in the tests, in subprocesses: the programs at `tests/test_inflaton_trajectory_prune.py:464`,
    `tests/test_inventory_store.py:80` and `tests/registered_run_helpers.py:110`.
- **Recorded distributions.** `runregistrykit.toml`'s `distributions` is `["datastorekit",
  "raypoolkit"]`, which `tests/test_registry_config.py:53` holds equal to
  `utilities.RECORDED_DISTRIBUTIONS` (`utilities.py:174`, a protected file) and which `main.py`
  prints as its `>> packages:` line. It stays (U4).

### 0.4 Baselines

`CLAUDE.md`'s suites at `03110ce` (`rrk-adoption`'s close): default **848** (847 passed, 1
skipped); `integration` **72** (71 passed, 1 skipped); `slow` 69, not run, since no path that
selects it changes (`.claude/rules/test-selection.md`).

The rehearsal's reference fingerprint (format 1) is `rrk-adoption` 04's:
**`a9f716fb88cf8647327748e533e7402e6f406a59aba3826956e966b7f9081ea7`**, recorded for both its
`reference` and its resumed store (`var/runs/rrk-adoption-04-*/status.json`). 04's stores are
retired and RH2's are gone, so the fingerprint is the only comparison across versions. It is the
comparison SGK's FP6 used.

## 1. Scope

**In scope:**
- the two pins, and the venv upgraded from them;
- token mode named for every Ray start: a module `config/ray_auth.py`, imported by the three
  drivers and by `tests/conftest.py`; `ray_cluster.sh` setting the mode before `ray start`; a test
  module guarding both;
- `CLAUDE.md` (the rule, and the test counts) and `.claude/rules/test-selection.md` (the counts);
- the failure shown before the fix (V0), and a rehearsal after it on SI's cluster: a clean build,
  a build stopped with `SIGTERM`, and its resume, each registered through the wrapper.

**Out of scope:**
- **Every other pin**, and the interpreter.
- **`runregistrykit.toml`'s `distributions`** and `utilities.py` (U4).
- **The `slow` block**, and anything a build computes: no file under `ComputeTargets/`,
  `Numerics/`, `Interpolation/` or `Datastore/` changes.
- **The hard-kill route.** `rrk-adoption` 04 rehearsed it on Ray 2.55.1, and nothing of SI's
  cluster outlived the `SIGKILL`ed driver, which attaches to the external cluster (`rrk-adoption`
  verification §1, "Nothing left behind"). The route is RunRegistryKit's, which this campaign does
  not move. SGK's GCS server, which a `SIGKILL`ed driver of SGK's own local instance leaves
  deadlocked, is measured under 2.59.0 on SGK's board.
- **ChamPBH, SGK and the three packages**: read, never edited. A package defect is reported
  upstream (`CLAUDE.md`, "Protected infrastructure").
- **The token itself.** It is never printed, copied, regenerated or chmodded by this campaign. If it
  is missing or not mode 600, the prompt stops.

## 2. Prompts

| # | Prompt | Covers | Model |
|---|---|---|---|
| 01 | `01-move-ray-and-sqlalchemy-with-token-mode.md` | the pins and the venv; the failure shown; token mode named; the tests and the documents; the rehearsal | Opus |

01 is written with this plan. The review of 01 closes the campaign.

### 2.1 The charter of 01

**01 — Move `ray` and `SQLAlchemy`, with token mode named** (Opus: a dependency move whose failure
mode is an authentication refusal at the first `ray.init`, and three real builds under real Ray).
- **What it changes**, in three commits (C6):
  1. `requirements.txt:58` `ray==2.59.0` and `:68` `SQLAlchemy==2.0.55`, and nothing else; the venv
     upgraded in place (C2);
  2. `config/ray_auth.py` (C3); its import in `main.py`, both plot scripts and `tests/conftest.py`
     (C4); `ray_cluster.sh` setting the mode (C5); `tests/test_ray_auth.py`; `CLAUDE.md` and
     `test-selection.md`; the rehearsal's launcher;
  3. the records: the results note, `out/`, the board and `INDEX.md`.
- **What it shows.**
  - **V0**, between the first two commits: SI's cluster started and a driver attached, as `main.py`
    attaches, with `RAY_AUTH_MODE` unset. Expected: the cluster in token mode, the warning in
    `start`'s output, and the driver refused at `ray.init`. This is §0.2's claim, measured.
  - **R**, after the second commit, on a clean tree: `reference`, `resumed-a` (`SIGTERM`) and
    `resumed-c`, registered. Both stores fingerprint to `a9f716fb…1ea7`, `compare_stores` finds
    them equal, and the token checks of §2.2 hold.
- **Acceptance**: the suites at §0.4's counts, plus the new module's tests; the dry run and the
  freeze moved by the two lines alone; the deliberate breakages caught; the gate **FP** (§2.2).

### 2.2 The gate

| Gate | Holds when |
|---|---|
| **FP** | `reference` and the resumed store, built under `ray` 2.59.0 and `SQLAlchemy` 2.0.55, each fingerprint to `a9f716fb…1ea7`, and `compare_stores` finds them equal but for bookkeeping |
| **Token** | no launch log of R, and no output of V0's fix, holds `Token authentication is enabled`, `Generated new authentication token`, `InvalidAuthToken` or `AuthenticationError`; the cluster's `gcs_server` and `raylet` have `RAY_AUTH_MODE=token` in their environment; `~/.ray/auth_token` is still 64 bytes, mode 600, with its 12:51 mtime; no committed record contains the token |

If **FP** fails, nothing is changed to make it pass: the stores, the logs and `compare_stores`'s
output are recorded, and the user decides how to bisect (Ray alone, or SQLAlchemy alone).

## 3. Stores

R's two stores, under `var/datastores/`: `ray-sqla-align-01-reference.sqlite` and
`ray-sqla-align-01-resumed.sqlite`, with their shards and sidecars. They are kept for the user to
retire with `store retire` (as `rrk-adoption`'s were, its board §5.8). No other store is opened.

## 4. Where it runs

On the laptop, in the main checkout, **on `main`** (C1). Nothing else is in flight: `rrk-adoption`
and `rpk-v030-adoption` are closed and merged.

## 5. The rules this campaign runs under

`CLAUDE.md`'s critical rules, its protected-infrastructure list and its run-registry rules, and,
from `dk-and-rpk-migration` and `rrk-adoption`:
- deliberate breakages recorded as diffs, never committed;
- a package defect reported upstream, never worked around here;
- no change in a sibling repository;
- no `ray stop`, and SI's cluster only through `ray_cluster.sh`;
- **a held lock is a stop, never a wait**; each lock command is a shell command of its own, and no
  `PURPOSE` names `/tmp/ray-si`;
- **no polling**: one check after each launch, then a `Monitor` on the launch log's last line;
- the results-note template of `dk-and-rpk-migration` README §5.1.

And:
- **the token is never printed or copied.** No command reads `~/.ray/auth_token` but `stat` (or
  `ls -l`) and the final `grep -F -l -f`, which lists file names only;
- **a Ray CLI command against SI's cluster is run with `RAY_AUTH_MODE=token`** in its environment,
  from the second commit on, and is never run before V0 (where it would be refused).

## 6. Decisions

### 6.1 Ruled by the user (2026-10-25)

| Decision | Ruled |
|---|---|
| **U1** — versions | `ray` 2.59.0 and `SQLAlchemy` 2.0.55, SGK's; every other pin unchanged |
| **U2** — token authentication | kept, and named: `RAY_AUTH_MODE=token` set by SI, as SGK does |
| **U3** — the shape | a campaign with a board and one prompt, as proposed |
| **U4** — recorded distributions | unchanged (`datastorekit`, `raypoolkit`): recording `ray` and the rest in manifests would mean changing the protected `utilities.py:174` and `main.py`'s `>> packages:` line. The versions are recorded in 01's results note instead |

### 6.2 Choices of method made in writing this plan

The planner's; each stands unless the user rules otherwise.
- **C1 — on `main`, no branch.** SI has one venv, so a branch would not isolate the move: once 01
  installs, every checkout runs the new Ray. Nothing else is in flight. The commits stay local until
  the user pushes.
- **C2 — the venv upgraded in place.** The interpreter does not change (SGK rebuilt because it
  did), and the dry run moves two packages. The freeze before is saved, so going back is two `pip
  install` lines.
- **C3 — `config/ray_auth.py`.** The token half of SGK's `config/ray_local.py`, under a name that
  says what it is: SI has no temp dir to give local instances, so the module holds only
  `RAY_AUTH_MODE`. It sets the variable only when the environment has none, and refreshes Ray's
  config when `ray._raylet` is already imported. Its comment says why, with SGK's issue cited.
- **C4 — who imports it.** The three drivers, at module level, before their `ray.init`;
  `registered_run.py` runs `main.py` in-process, so `main.py`'s import covers it. For the tests,
  `tests/conftest.py`, which pytest imports before any test module: that covers the in-process
  starts, and the subprocess programs inherit the variable through `os.environ`. 01 checks that each
  of the three subprocess programs is given an environment built from `os.environ`.
- **C5 — `ray_cluster.sh`.** It exports `RAY_AUTH_MODE` as `${RAY_AUTH_MODE:-token}` before `ray
  start`, so that the cluster's mode is named rather than inferred from the token file, and the
  `actors:` line it prints carries the variable. The lock half is untouched.
- **C6 — three commits:** the pins; the fix; the records. The first is a tree on which local Ray
  works with a warning and SI's cluster refuses its drivers: V0 measures that tree. The rehearsal
  runs on the second, clean, so that its manifests record `git_dirty` false.
- **C7 — V0, the failure shown.** One start and stop of SI's cluster under the lock, and one
  attaching driver, before the fix. It costs a minute, and it turns §0.2 from a reading of Ray's
  source into a measurement.
- **C8 — the rehearsal** is `rrk-adoption` 04's H1, H2 and H4: the clean build, the `SIGTERM`, and
  the resume, with the same grid and the wrapper. The `SIGTERM` checks that the wrapper still
  records `killed`/143 under Ray 2.59's signal handlers (04's P9 measurement). No `SIGKILL` (§1).
- **C9 — the launcher** is a copy of `.documents/rrk-adoption/rehearsal/build_registered.sh` at
  `.documents/ray-sqla-align/rehearsal/build_registered.sh`, with its campaign, prompt and slug
  prefix changed and nothing else, the diff recorded. 04's launcher hard-codes its names.
- **C10 — outputs.** While 01 works, everything it saves goes under `var/ray-sqla-align-01/`
  (ignored), so that the tree stays clean for R. It is copied to `.documents/ray-sqla-align/out/`
  for the third commit, after the token check.
- **C11 — issues.** None opened or assigned at planning; `OPEN-ISSUES.md` is unchanged.
- **C12 — dispatch.** 01 is dispatched when the user says so. It takes the shared lock, and the
  projects use Ray one at a time.

## 7. What this campaign hands on

- **SI on SGK's Ray and SQLAlchemy**, with every Ray start in named token mode. A Ray start added
  later imports `config/ray_auth.py`, and `tests/test_ray_auth.py` fails if a driver does not.
- **To ChamPBH**, still on `ray` 2.53.0: the same move meets the same refusal if ChamPBH's cluster
  is started with `ray start` and attached to by address, as SI's is, because the token file is
  shared by every project of this user. SI's module, test and script change are the nearest models.
- **To the packages**: SI's rehearsal under 2.59.0 and 2.0.55, as evidence beside SGK's, for
  whoever raises their tested high ends.
- **R's stores** under `var/datastores/`, for the user to retire.
