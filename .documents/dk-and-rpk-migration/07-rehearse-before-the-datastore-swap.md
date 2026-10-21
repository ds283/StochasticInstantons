# 07 — rehearse before the DatastoreKit swap (RH1)

**Subject:** Rehearse 06's tree (RH1), compare it bit for bit with RH0, and tag `pre-datastorekit`
**Commit:** the commit tagged `pre-datastorekit`, on branch `dk-and-rpk-migration`, on top of `9214c9b`
**Date:** 2026-10-20 (gate and suites) and 2026-10-21 (the rehearsal), by Claude Opus 5.5
**Result:** **COMPLETE.** L1–L4 hold, and **RH1 equals RH0 bit for bit in both modes.**
- All five comparisons give `RESULT: equal`, exit 0. Every row of all 30 tables matched, and only
  timestamps and the JSON timing keys differ.
- The schema is RH0's.
- Both `scalar_data.csv` files hash to RH0's `b0564eec…58a2`.
- `stage_counts.py`'s records for `reference` and `scalars` equal RH0's, except for the provenance
  line. The resume follows RH0's pattern: 1 pruned of 1 unvalidated, then 8 + 2.
- `resumed-a` fell outside its window at the first attempt (the machine was loaded) and inside it
  at the second (`resumed-a2`).
- The tree is tagged `pre-datastorekit` (annotated, local, not pushed).
- No code changed and no issue is opened. No SI cluster is left running, and the lock is free.

Prompt: [`.prompts/dk-and-rpk-migration/07-rehearse-before-the-datastore-swap.md`](../../.prompts/dk-and-rpk-migration/07-rehearse-before-the-datastore-swap.md).
The orchestrator's brief for 07 governed where it corrected the prompt; its thirteen corrections
were applied as stated (below). The record of the rehearsal is
[`verification.md`](verification.md) §2. The outputs kept are in [`out/`](out/), as `07-*`.

## How the run went: two stops, an overnight pause, and a resume

1. **2026-10-20, 21:10–21:13 BST: the gate and the suites, then a stop.**
   - Every gate check passed (below), and both suites passed at `9214c9b`.
   - At 21:13 the load was 27 and one Python process was at about 90% CPU:
     `python -m unittest discover -s ComputeTargets/tests -t . -p test_[g-z]*.py`, with its cwd in
     `/Users/ds283/Documents/Code/ChamPBH`, started about 21:11. That is another session's suite.
   - Under the orchestrator's instructions a foreign suite is a stop, so the agent stopped before
     `ray_cluster.sh start` and asked. The suite had ended by 21:13:29.
2. **Overnight**, the session was paused by a quota limit.
3. **2026-10-21, 10:01: resumed, and stopped again.** The orchestrator said to proceed.
   - The re-check at 10:01:33 found no suite, the lock free and the tree clean, at a load of 47.
   - Eight seconds later the first sample of the load monitor caught a new ChamPBH suite loop:
     - pid 91493, a `zsh -c` from a ChamPBH Claude session, started about 10:01:31;
     - six `unittest discover` groups, one after another, over `CosmologyModels/tests`,
       `ComputeTargets/tests` (two groups), `ObjectFactories/tests`, `tools/tests` and
       `RunDrivers/tests`.
   - The agent stopped its monitor and asked again.
4. **10:02: the orchestrator ruled (b).**
   - Wait with Monitor until pid 91493 has exited and no `unittest`, `pytest`, `main.py` or Ray
     process is left.
   - Then wait until the 1-minute load is below about 15, or five minutes, whichever comes first.
   - Bound the wait at 45 minutes.
   - Once the cluster is up, a foreign suite is recorded, not a stop.
5. **10:08:36:** the loop exited, after about 7 minutes. The five minutes ended at 10:13:41 with
   the load at 52.9. Only desktop processes were running (Time Machine's `backupd`, Spotlight,
   the Claude apps, WindowServer), and no suite or Ray job.
6. **10:13:50: the re-check of condition 1.**
   - `pgrep -fl` found no foreign suite, build or Ray job.
   - The lock was free and the four ports free. `HEAD` was `9214c9b` and the tree clean. No
     `07-*` file existed.
7. **10:13:54–10:24:31: the rehearsal**, recorded below. No foreign suite or Ray job ran while
   the cluster was up.

## What shipped

- **[`verification.md`](verification.md) §2 RH1**, appended (§2.0–§2.7). Its introduction and §1
  are not touched.
- **[`out/`](out/) `07-*`**, small text only:
  - `07-compare-reference-resumed`, `07-compare-02reference-07reference`,
    `07-compare-02reference-07resumed`, `07-compare-02scalars2-07scalars` and
    `07-compare-02scalarsbefore-07scalars`, each `.txt` and `.json`;
  - `07-reference-schema.json`: the schema snapshot, 30 tables;
  - `07-stage-counts.txt`, `.json`: `stage_counts.py` on the five logs;
  - `07-readers-{resumed,scalars}-{status.txt,inventory.log,compare_stores.txt,scalar_data.csv}`.
    The inventory logs drop only the raylet's `file_system_monitor` disk-space lines;
  - `07-scalar_data.sha256`.
- **The board:**
  - the §1 row for 07;
  - L1–L4 (RH1), V2 and Z1;
  - gate RH1;
  - the RayPoolKit G4 row's note;
  - §5.19, and the header.
- **The tag** `pre-datastorekit`, annotated, on this commit. It is not pushed.
- No code, script, tool or test changed. Nothing was installed. `.documents/OPEN-ISSUES.md` is
  unchanged (61 open, 26 closed).

## The orchestrator's corrections, as applied

1. The board section is `### 5.19 After prompt 07 (2026-10-21)`, and the header is updated.
   `.prompts/INDEX.md` and the list of orchestrator notes are left to the review.
2. The suites' expected counts are 696 (695 passed, 1 skipped) and 62 (61 passed, 1 skipped),
   with no `slow` block. Both were run before the cluster.
3. L4's "line for line" is taken as the parsed records less `packages`, compared by a scratch
   script (reproduced below).
4. The provenance line is checked against the one given.
5. The pool's printed lines were not re-diffed. `stage_counts.py` parsed every log unchanged, and
   its stale `RayTools/` line references are not a finding.
6. `S` was measured afresh (below).
7. The prune report was also read in the actor's own log before the stop.
8. The comparison files are named as the correction gives them.
9. The readers' outputs and the CSVs are kept and staged as 02's D6.
10. The profile database is recorded beside RH0's, and its difference explained.
11. One `git ls-remote` was made, at the gate. The tag is checked after the commit and not pushed.
12. `verification.md` §2 is appended.
13. `OPEN-ISSUES.md` is untouched.

## Deviations from the prompt

- **D1: the suites are cited from 2026-10-20 at `9214c9b`, not re-run on 2026-10-21.**
  - Both ran at 21:11–21:13 BST, before the first stop, serially and in the foreground, with no
    cluster up.
  - No code changed between them and the cluster: `HEAD` and the tree were the same on the 21st.
  - The integration run (21:12:38–21:13:12) overlapped the ChamPBH suite of the first stop, and
    passed.
  - The orchestrator's condition 2. **IMPLEMENTATION CHOICE.**
- **D2: the rehearsal ran a day after its gate, across two stops for foreign suites and an
  overnight pause** (above).
  - The gate, the baseline check and the suites are of 2026-10-20. The cluster, the builds, the
    comparisons and the readers are of 2026-10-21.
  - Nothing in the tree, the venv or `$REHEARSAL_ROOT` changed in between. The re-checks at
    10:01 and 10:13 confirmed the state, and the stores RH1 compares against were checked byte for
    byte afterwards (Hygiene).
  - **UNINTENDED DRIFT** (external).
- **D3: a read-only `shasum` of files the prompt says not to open.**
  - At the gate, to be able to show afterwards that RH0's files were untouched, I ran
    `shasum -a 256` over every file under `$REHEARSAL_ROOT` except `logs/`.
  - That read the bytes of the 14 files of `02-attempt-1-aborted/`, the 152 of
    `02-attempt-2-reader-defect/`, and `02-resumed*.sqlite` and `02-scalars.sqlite` with their
    shards (prompt §5: "does not open … either of RH0's earlier attempts' directories").
  - Nothing was opened as a database and nothing was written.
  - From then on those files were checked by listing only (`ls -laTR`).
  - Accepted by the orchestrator. **UNINTENDED DRIFT.**
- **D4: `resumed-a` needed a second attempt, `resumed-a2`, with `S` = 12.0 s in place of 10.5 s.**
  - The first signal fell before any `FullInstanton` row had been stored: the driver was still
    minting the tenth instanton's `efold_value` grid, at least 1.1 s behind `reference`'s pace.
    The load at that build's start was 37, and it rose to 108.66.
  - Its 11 store files (`07-resumed.sqlite` and its ten shards) were deleted. The second attempt
    ran on a fresh store under a new build slug, so its log is `07-resumed-a2.log`. This is as
    prompt §1.3.3 allows.
  - The second attempt fell inside the narrow window.
  - **UNINTENDED DRIFT** (external: the load). The retry itself is the protocol's.
- **D5: the two `scalar_data.csv` copies were staged by force, without line-ending conversion**,
  as 02's D6 did: `git -c core.autocrlf=false add -f <path>`. `*.csv` is ignored by
  `.git/info/exclude`, and the files have CRLF endings. **IMPLEMENTATION CHOICE.**
- **D6: two read-only reads of RH0's profile database** (`02-reference-profile.sqlite`, `sqlite3`
  `mode=ro`). They were needed to explain the profile count (a `ClientPool` breakdown by shard and
  table). It is one of RH0's files, read as its baselines are. **IMPLEMENTATION CHOICE.**

The exit statuses 15 and 1 of the two signalled drivers are within 02's D4 (134, 15 or 1) and are
not a deviation.

## Verification performed

### The gate (2026-10-20, 21:10–21:11 BST)

- Branch `dk-and-rpk-migration`, `HEAD` `9214c9b`, clean, `git diff --cached` empty.
- `git diff --stat 5e41ce8 HEAD`: four record files, all under `.prompts/`.
- `git diff 5868231 HEAD -- .documents/dk-and-rpk-migration/rehearsal/ tools/compare_stores.py`:
  empty (0 bytes).
- `git tag -l pre-datastorekit`: empty. `git ls-remote --tags origin pre-datastorekit`: empty,
  exit 0 (the one network call).
- `ray_cluster.sh status`: the lock free, no `/tmp/ray-si` process, the four ports free.
  `pgrep` found no `gcs_server`, `raylet`, `ray::`, `pytest` or `main.py`. `RAY_ADDRESS` unset.
- `utilities.installed_package_provenance()`: `datastorekit` None; `raypoolkit` 0.2.0,
  `https://github.com/ds283/RayPoolKit`, commit `eaef0ce60e2fc354bb32f0ad576010e6a83c1976`,
  requested `v0.2.0`, `editable` False. `pip freeze` has the one `raypoolkit @ git+…@eaef0ce6…`
  line and no `datastorekit`.
- RH0's stores were in place: `02-reference`, `02-scalars-2`,
  `02-readers/scalars/before/02-scalars` and `02-readers/resumed/before/02-resumed`, each with ten
  shards. No `07-*` file existed.
- Load 2.55 / 5.88 / 8.49 at 21:11 on 10 CPUs.

### RH0's baseline check

```bash
./venv/bin/python tools/compare_stores.py $R/02-reference.sqlite $R/02-readers/resumed/before/02-resumed.sqlite
./venv/bin/python tools/compare_stores.py $R/02-readers/scalars/before/02-scalars.sqlite $R/02-scalars-2.sqlite
```

Both gave `RESULT: equal`, exit 0. The dense text equals
`out/02-compare-reference-resumed-before-readers.txt` but for the paths. **RH0's stores have not
moved.**

### The cluster

- `ray_cluster.sh start "dk-and-rpk-migration 07 (RH1)"` at 10:13:54 BST, at a load of 48.14 /
  53.12 / 40.04 (desktop processes only). It started in 7 s, `gcs_server` pid 2788.
- It printed the address `127.0.0.1:6390` and the actor line
  `./venv/bin/ray list actors --address 127.0.0.1:6390`.
- `ray_cluster.sh stop` at 10:24:13:
  - `SIGTERM` to 18 processes, `SIGKILL` to 2788 and 2812 after the grace;
  - "no process names /tmp/ray-si; ports 6390 6391 8266 52366 are free";
  - "released the rehearsal lock"; "stopped in 18s".

  `status` afterwards: the lock free, no SI process, the four ports free.

### The builds

All times BST. The load is the 1-minute average at the build's start.

| Build | Command | Start | End | Wall | Load | Exit |
|---|---|---|---|---|---|---|
| `reference` | `build.sh 07 reference reference 127.0.0.1:6390 dense --profile-db` | 10:14:06 | 10:14:42 | 36 s | 44.08 | 0 |
| `resumed-a` | `build.sh 07 resumed resumed-a 127.0.0.1:6390 dense` | 10:15:13 | 10:15:41 | 28 s | 37.21 | 15 (`SIGTERM`; before the window) |
| `resumed-a2` | `build.sh 07 resumed resumed-a2 127.0.0.1:6390 dense` | 10:19:30 | 10:19:57 | 27 s | 24.84 | 1 (`SIGTERM`; in the window) |
| `resumed-b` | `build.sh 07 resumed resumed-b 127.0.0.1:6390 dense` | 10:20:20 | 10:20:44 | 24 s | 31.96 | 0 |
| `scalars` | `build.sh 07 scalars scalars 127.0.0.1:6390 scalars` | 10:20:50 | 10:21:21 | 31 s | 46.12 | 0 |

`reference`'s stages took 5.47 s, 12.1 s, 8.76 s and 1.61 s; RH0's took 5.84, 12.8, 8.77 and
1.68. The 45-minute limit (P1) is far off.

### `S`, and how it was chosen

From the closed `07-reference.sqlite`, read with `sqlite3` `mode=ro` by the scratch script
`rows.py` (below), and from its profile database. The times are the stores' naive local time, BST.
- The last `InflatonTrajectory` row (its tenth replica) was stored at 10:14:17.188.
- The profile database's `object_get FullInstanton vector` calls, the `STAGE 2` lookup, ran at
  10:14:17.614–17.632. So the `STAGE 2: FULL MSR INSTANTONS LOOKUP:` banner, which
  `interrupt_when.py` matches first, was at about **10:14:17.61**.
- The ten `object_get FullInstanton scalar` calls followed, from 10:14:19.24, about 0.8 s apart.
  The last `efold_value` row was minted at 10:14:27.025, banner +9.41 s.
- `FullInstanton` rows were stored at 27.109, 27.182, 27.222, 28.345, 28.370, 28.623, 29.202,
  29.214, 29.278 and 29.688. That is banner **+9.49, +9.57, +9.61, +10.73, +10.76, +11.01,
  +11.59, +11.60, +11.66 and +12.07 s**: a window of 2.6 s, starting 0.3 s earlier than RH0's
  (+9.77 to +12.76 s).
- `SlowRollInstanton` rows were stored at 10:14:38.09–38.43. `CompactionFunction` rows were
  stored at 10:14:39.97–40.82, banner +23.2 s, the end of the wide window.

**First attempt, `S` = 10.5 s.**
- At `reference`'s pace this puts the signal between the third and fourth rows, about 0.1 s after
  `interrupt_when.py`'s 0.2 s poll. The orchestrator's brief advised aiming early, since a fresh
  driver has run ahead of its `reference` before.
- What happened (BST; the script prints UTC):
  - the last trajectory row was stored at 10:15:29.621;
  - the script saw the banner in the second 09:15:30 UTC;
  - it sent the signal at 09:15:40 UTC, and the driver logged `SIGTERM received` at 10:15:40.746;
  - the last `efold_value` row was minted at 10:15:40.731. The driver was still minting the
    tenth grid, at least banner +10.5 s, against `reference`'s +9.41.
- No `FullInstanton` row was stored: **the signal fell before the window.** The load was 37 at
  the start and 108.66 at 10:15 (Time Machine's `backupd`, a Claude app restarting). The store
  held only the trajectory, validated (10 replicas, 57,130 value rows).
- The actor check at 10:15:48: "No resource in the cluster" for `state=ALIVE`; job `02000000`'s
  11 actors `DEAD`.
- Its 11 store files were deleted (`rm -v $R/07-resumed.sqlite
  $R/07-resumed-shard000{0..9}.sqlite`); its log and pidfile stay.

**Second attempt, `S` = 12.0 s.**
- Chosen so that the signal falls among the `FullInstanton` rows if the build runs at
  `reference`'s pace (just before the last row) or up to about 25% slower (+11.9 to +15.1 s). The
  load had fallen to 25.
- What happened:
  - the last trajectory row was stored at 10:19:43.388;
  - the script saw the banner in the second 09:19:43 UTC;
  - it sent the signal at 09:19:55 UTC, and the driver logged `SIGTERM received` at
    10:19:56.035;
  - `FullInstanton` rows were stored from 10:19:53.435 to 10:19:55.967.

  That is banner (about 10:19:43.8) +9.6 to +12.2 s, close to `reference`'s pace. **The signal
  fell inside the narrow window.**

The `interrupt_when.py` output:

```text
[2026-10-21T09:15:13+00:00] interrupt_when: waiting for "STAGE 2: FULL MSR INSTANTONS" in …/07-resumed-a.log; then 10.5 s; then SIGTERM
[2026-10-21T09:15:13+00:00] interrupt_when: driver pid 3972 (from …/07-resumed-a.pid)
[2026-10-21T09:15:30+00:00] interrupt_when: saw "STAGE 2: FULL MSR INSTANTONS"; waiting 10.5 s
[2026-10-21T09:15:40+00:00] interrupt_when: sent SIGTERM to pid 3972
[2026-10-21T09:19:31+00:00] interrupt_when: waiting for "STAGE 2: FULL MSR INSTANTONS" in …/07-resumed-a2.log; then 12 s; then SIGTERM
[2026-10-21T09:19:31+00:00] interrupt_when: driver pid 7676 (from …/07-resumed-a2.pid)
[2026-10-21T09:19:43+00:00] interrupt_when: saw "STAGE 2: FULL MSR INSTANTONS"; waiting 12 s
[2026-10-21T09:19:55+00:00] interrupt_when: sent SIGTERM to pid 7676
```

Both runs exited 0.

### The rows `resumed-a2` left (read `mode=ro` after the build ended)

| Table | Validated | Not validated | Child rows (validated parent / not) |
|---|---|---|---|
| `InflatonTrajectory` | 1 (replicated: 10 rows over 10 shards) | 0 | `InflatonTrajectoryValue` 57,130 / 0 |
| `FullInstanton` | **8** (δN★ 0.1, 0.42222, 0.74444, 1.0667, 1.3889, 2.0333, 2.3556, 3.0) | **1** (δN★ 1.7111 on `shard0004`, serial 161) | `FullInstantonValue` 13,122 / **1,673** |
| `SlowRollInstanton` | 0 | 0 | — |
| `CompactionFunction` | 0 | 0 | — |

- δN★ 2.6778 was not stored.
- The unvalidated row was stored at 10:19:55.967, 68 ms before the driver took the signal.
- No `-journal` or `-wal` file was beside any shard, and no child row was orphaned.

**The actor check** at 10:19:59, 3 s after the signal:
- `./venv/bin/ray list actors --address 127.0.0.1:6390 --filter "state=ALIVE"` gave "No resource
  in the cluster";
- the full listing (`--limit 1000`) shows all 11 actors of job `03000000` (10 `Datastore`, 1
  `SerialPoolBroker`) `DEAD`. Jobs `01000000` (`reference`, with its `ProfileAgent`) and
  `02000000` (`resumed-a`) were all `DEAD` too.

### L1 — every build ends as it should

- `reference`, `resumed-b` and `scalars` end with `** driver exit status 0`. Their pools print
  `ALL WORK ITEMS COMPLETE` 4, 4 and 2 times, as RH0's did.
- `resumed-a` and `resumed-a2` end by the signal: each log has `*** SIGTERM received at time=…`
  (twice, the second from `logging.cc`) and the absl stack. Their exit statuses are 15 and 1, both
  within 02's D4.
- **No traceback in any log.** Every line matching `Traceback`, `Error` or `WARNING` was read:
  - Ray's start-up `FutureWarning` (accelerator visible devices), in every log;
  - the raylet's disk warning, `/tmp/ray-si/session_2026-10-21_10-13-56_480986_2787 is over 95%
    full, available space: 40 GB`, as an `E` line of `file_system_monitor.cc`;
  - `resumed-b`'s one `!! INTEGRITY WARNING` header (L2);
  - in `scalars`, the raylet's `WARNING: 16 PYTHON worker processes have been started … 4x the
    maximum expected startup concurrency (4)`. This is 02's Observation 3, printed during the
    unified pipeline at every RH0 attempt too.

  No `did not validate` line appeared.
- **The provenance line** appears once in each of the five logs, identically:

  ```text
  >> packages: datastorekit not installed; raypoolkit 0.2.0 (https://github.com/ds283/RayPoolKit@eaef0ce60e2fc354bb32f0ad576010e6a83c1976, requested v0.2.0)
  ```

  This is the line the prompt and the brief give, and the one 03's results note shows
  (`03-pin-raypoolkit-v0.2.0.md:103`). It names `raypoolkit` at `eaef0ce6…`, requested `v0.2.0`.
  It is not editable: the formatter marks an editable install, and provenance gives
  `editable: False`. `datastorekit` is not installed. Both readers' logs print the same line.

### L2 — the resume

- **The prune at `resumed-b`'s open.** One report was forwarded to the driver's log, from one
  actor:

  ```text
  (Datastore pid=8411) !! INTEGRITY WARNING (2026-10-21T10:20:24): datastore "shard0004-store" (physical file …/07-resumed-shard0004.sqlite)
  (Datastore pid=8411) Pruned 1 unvalidated FullInstanton records
  ```

  - The actor's own log, `/tmp/ray-si/session_2026-10-21_10-13-56_480986_2787/logs/worker-e481…-04000000-8411.out`,
    holds the same two lines, read before the stop. No other actor of the session pruned.
  - The total pruned, 1, equals the unvalidated count read between the builds, on the same shard,
    so **only unvalidated rows were pruned.**
  - The cascade took its 1,673 value rows. After `resumed-b`:
    - every `FullInstantonValue` row has a validated parent (16,564, as in `reference`), and no
      child row of any of the four tables is orphaned;
    - the eight kept rows keep their `resumed-a2` timestamps (10:19:53–55);
    - the two recomputed rows (δN★ 1.7111 on `shard0004`, 2.6778 on `shard0007`) are stamped
      10:20:30.
- **`resumed-b` computed only what `resumed-a2` had not kept:**
  - STAGE 1: 0 computed, "no compute items were evaluated - all assets read from datastore";
  - STAGE 2: lookup "8 already computed, 2 to compute", then 2 computed;
  - STAGES 3 and 4: 10 each.

  `resumed-a2`'s 8 kept plus `resumed-b`'s 2 make `reference`'s 10. The pruned instanton was
  recomputed, and none that had been kept validated was.
- `07-reference` against `07-resumed`: `RESULT: equal`, exit 0 (§4.3 below).

### §4.3 — equal to RH0, bit for bit

All runs are `./venv/bin/python tools/compare_stores.py A B --json …`, each with its text saved
beside its JSON and its exit code recorded. They ran **before the readers**, so the stores are as
their builds left them. `$R` is `~/ScienceData/StochasticInstantons-rehearsals/dk-and-rpk-migration`.

| A | B | Exit | `RESULT:` | Tables | A only / B only |
|---|---|---|---|---|---|
| `$R/07-reference.sqlite` | `$R/07-resumed.sqlite` | **0** | **equal** | 30 | 0 / 0 |
| `$R/02-reference.sqlite` | `$R/07-reference.sqlite` | **0** | **equal** | 30 | 0 / 0 |
| `$R/02-reference.sqlite` | `$R/07-resumed.sqlite` | **0** | **equal** | 30 | 0 / 0 |
| `$R/02-scalars-2.sqlite` | `$R/07-scalars.sqlite` | **0** | **equal** | 30 | 0 / 0 |
| `$R/02-readers/scalars/before/02-scalars.sqlite` | `$R/07-scalars.sqlite` | **0** | **equal** | 30 | 0 / 0 |

**Table by table**, the matched rows in each RH1 store against RH0's rows per store (02's results
note, "Rows per store"):

| Table | Dense: RH0 | Dense: RH1 (`reference`, `resumed`) | Scalars-only: RH0 | Scalars-only: RH1 |
|---|---|---|---|---|
| `CompactionFunction` | 10 | 10, 10 | 10 | 10 |
| `CompactionFunctionSamples` | 33,128 | 33,128, 33,128 | 0 | 0 |
| `FullInstanton` | 10 | 10, 10 | 10 | 10 |
| `FullInstantonValue` | 16,564 | 16,564, 16,564 | 0 | 0 |
| `SlowRollInstanton` | 10 | 10, 10 | 10 | 10 |
| `SlowRollInstantonValue` | 16,564 | 16,564, 16,564 | 0 | 0 |
| `InflatonTrajectory` | 1 | 1, 1 | 1 | 1 |
| `InflatonTrajectoryValue` | 5,713 | 5,713, 5,713 | 5,713 | 5,713 |
| `efold_value` | 7,521 | 7,521, 7,521 | 7,521 | 7,521 |
| `delta_Nstar` | 10 | 10, 10 | 10 | 10 |
| `CosmologicalParams`, `MasslessDecoupledDiffusion`, `N_final`, `N_init`, `QuadraticPotential`, `alpha_regularization`, `inflaton_mass`, `n_collocation_points`, `phi_value`, `pi_value`, `tolerance`, `version` | 1 each | 1 each | 1 each | 1 each |
| `GradientCoupledInstanton`, `…Profile`, `…Value`, `IntegrationSolver`, `QuarticPotential`, `quartic_coupling`, `redshift`, `store_tag` | 0 each | 0 each | 0 each | 0 each |

- In every comparison, every row of every table matched. Nothing is A-only or B-only, and no
  near miss or problem is named.
- `redshift` is noted as in neither of the primary's table lists, as always.
- **Bookkeeping only** differs between matched rows: every `timestamp`, and the JSON timing keys:
  - `compute_time` in `InflatonTrajectory`, `FullInstanton` and `SlowRollInstanton`;
  - `compute_time` in `CompactionFunction.metadata`, at the top level (dense only) and under
    `full` and `slow_roll`;
  - `FullInstanton.diagnostics_json["mean_time_per_picard_iteration"]`.
- `version` is matched, 1 row each: no reader had touched any of the five stores compared, so 02's
  D3 does not arise.
- The two scalars-only comparisons list the same bookkeeping.
- **The first table in build order whose rows differ is none.** RH1's three stores equal RH0's of
  the same mode, bit for bit.

**The schema.**
- `--snapshot $R/07-reference.sqlite` wrote `out/07-reference-schema.json`, 30 tables. It differs
  from `out/02-reference-schema.json` in its `source` line alone.
- `--schema $R/07-reference.sqlite --against out/02-reference-schema.json` and
  `--schema $R/07-scalars.sqlite --against` the same file: "RESULT: the schemas agree", exit 0,
  both.

### L3 — the readers

`run_readers.sh 07 resumed 127.0.0.1:6390` ran 10:22:40–10:23:12 (load 39.74), then
`run_readers.sh 07 scalars 127.0.0.1:6390` ran 10:23:20–10:23:45 (load 43.37), each as a background
task. Both exited 1, as the script does by design when step 4 finds the expected row.
- **`status.txt`, both stores:** step 0 `copy-before` exit 0, step 1 `inventory` exit 0, step 2
  `plot_InstantonSolutions` exit 0, step 4 `compare_stores` exit 1. Step 3 is printed as not run
  (U11).
- **`4-compare_stores.log`, both stores:**
  - exactly one table differs, `version`, `B only 1`, `version{label='2026.3.0'}`;
  - "bookkeeping that differs between matched rows": none;
  - problems: none.

  Step 2's plot log reads `n_collocation_points: 1 value = [ 5 ]`.
- **`scalar_data.csv`:**
  - `plot_InstantonSolutions.py` on `resumed`:
    `b0564eecc22f9106dcccb57fd1a419749543c4b9d15dc0ffe7a8e0780e9058a2`;
  - on `scalars` with `--no-store-values`:
    `b0564eecc22f9106dcccb57fd1a419749543c4b9d15dc0ffe7a8e0780e9058a2`.

  Both have 11 lines and 3,592 bytes, and are RH0's byte for byte. No `diff` was needed. The
  committed blobs' hashes are checked at staging (below).
- **What `--inventory` printed**, against RH0's (`out/02-readers-*-inventory.log`). A `diff` of
  the abridged logs, with the `02-`/`07-` prefix normalized, shows only:
  - the provenance line;
  - Ray's two connection lines (their times);
  - the four `@@ validated: … record(s) | <date> <time> – <time>` lines (their dates).

  The values and counts are RH0's:
  - 10 δN★ `[0.1 … 3]`, N_init `[20]`, N_final `[5]`, φ₀ `[15 PlanckMass]`, π₀ `[0 PlanckMass]`,
    m `[1e-05 PlanckMass]`;
  - quartic couplings "no values committed"; 7,521 e-fold sample values;
  - trajectories 1 validated / 0 unvalidated;
  - Full MSR, slow-roll and compaction 10 validated / 0 unvalidated each;
  - gradient-coupled 0 / 0.
- Each plot log carries two of the `Datastore` actors' physics warnings
  `!! WARNING: CompactionFunction(…): slow-roll instanton is compensated (C_min=… < 0) …` (02's
  Observation 2), Ray marking the rest as repeated. They are not failures.

### L4 — against RH0

`stage_counts.py` on the five logs (`out/07-stage-counts.txt`, `.json`) parsed every `raypoolkit`
log unchanged: its banners, progress lines, `ALL WORK ITEMS COMPLETE`, `Queue summary:` and
`(no compute items were evaluated …)`.

| Stage | `reference` | `resumed-a` | `resumed-a2` | `resumed-b` | `scalars` |
|---|---|---|---|---|---|
| `STAGE 1: BACKGROUND INFLATIONARY TRAJECTORIES` | 1 computed | 1 computed | 1 computed | 0, no compute items evaluated | 1 computed |
| `STAGE 2: FULL MSR INSTANTONS` lookup, then pool | 0 / 10; 10 | 0 / 10; INCOMPLETE (signal) | 0 / 10; INCOMPLETE (signal) | 8 / 2; 2 | — |
| `STAGE 3: SLOW-ROLL INSTANTONS` | 0 / 10; 10 | — | — | 0 / 10; 10 | — |
| `STAGE 4` section; `COMPACTION FUNCTIONS LOOKUP`; `… AND MASSES` pool | 0 / 10; 10 | — | — | 0 / 10; 10 | — |
| `PIPELINE LOOKUP`; `STAGES 2+3+4: UNIFIED PIPELINE` | — | — | — | — | 0 / 10 ("10 skipped"); 10 |
| integrity reports | none | none | none | 1 × `Pruned 1 unvalidated FullInstanton records` | none |
| driver exit status | 0 | 15 | 1 | 0 | 0 |

**The builds that do not depend on the signal equal RH0's.** The scratch script `l4_compare.py`
(below) compares 07's records for `reference` and `scalars` with 02's, field by field:

```text
reference  entries         equal
reference  complete_lines  equal
reference  integrity       equal
reference  exit_status     equal
reference  packages        02: ['>> packages: datastorekit not installed; raypoolkit not installed']
reference                  07: ['>> packages: datastorekit not installed; raypoolkit 0.2.0 (https://github.com/ds283/RayPoolKit@eaef0ce60e2fc354bb32f0ad576010e6a83c1976, requested v0.2.0)']
scalars    entries         equal
scalars    complete_lines  equal
scalars    integrity       equal
scalars    exit_status     equal
scalars    packages        02: ['>> packages: datastorekit not installed; raypoolkit not installed']
scalars                    07: ['>> packages: datastorekit not installed; raypoolkit 0.2.0 (https://github.com/ds283/RayPoolKit@eaef0ce60e2fc354bb32f0ad576010e6a83c1976, requested v0.2.0)']
RESULT: L4 records equal
```

It exited 0. As a control, 02's `reference` `entries` against 07's `resumed-b` and 07's `scalars`
are unequal, so the comparison can fail.

**The resume's pattern is RH0's:**
- the open pruned only unvalidated rows (1 = 1);
- the resume computed only what was not kept (STAGE 2: 8 + 2);
- the counts add up to `reference`'s (10 / 10 / 10 / 1).

The figures (8 + 2, 1 pruned, against RH0's 6 + 4, 2 pruned) depend on where the signal fell.
Since the signal falls after the trajectory stage, no trajectory was pruned, and 06's cascade made
no difference here.

### The profile database

`07-reference-profile.sqlite`, read `mode=ro`, has the tables `jobs` and `profile_data`.
- `jobs`: 1 row,
  `2026.6.1-job-"dk-and-rpk-migration-07-reference"-db-"…/07-reference.sqlite"-2026-10-21T10:14:08`.
- `profile_data`: **803** rows; the ProfileAgent printed "803 total database events".

| Method | RH0 (`02-reference-profile`) | RH1 |
|---|---|---|
| `object_get` | 443 | 443 |
| `ClientPool.lease_serial\|lease_serials` | 137 | 135 |
| `ClientPool.lease_serial\|commit_serials` | 76 | 76 |
| `ClientPool.release` | 61 | 59 |
| `object_store` | 40 | 40 |
| `object_validate_item` | 40 | 40 |
| `read_largest_store_ids` | 10 | 10 |
| total | 807 | 803 |

**Why it is 4 fewer.**
- A `ClientPool` exists per actor and table. Each one that leases serials adds one
  `lease_serials` event per batch, and one `release` event at the end
  (`Datastore/SQL/ClientPool.py:43-63`, `:94-104`).
- `efold_value` is replicated, and the actor that serves each request for a replicated table
  varies from run to run.
- RH0 leased `efold_value` serials through 8 actors (22 leases); RH1 through 6 (20 leases). That
  is two fewer `lease_serials` and two fewer `release` events.
- The other replicated tables' leases likewise moved between shards, with the same counts.
- Every `object_get`, `object_store` and `object_validate_item` count is RH0's.
- This is scheduling in the old layer's serial broker, not a stored value. It is reported, not a
  stop (correction 10).

### The suites (2026-10-20, before the cluster; D1)

| Selection | Collected | Result | Time | Load at start |
|---|---|---|---|---|
| `./venv/bin/python -m pytest -m "not integration and not slow" -q -p no:cacheprovider` | 696 (131 deselected) | 695 passed, 1 skipped, 10 warnings | 31.56 s (21:11:56–21:12:31) | 4.21 |
| `RAY_ADDRESS=local ./venv/bin/python -m pytest -m integration -q -p no:cacheprovider` | 62 (765 deselected) | 61 passed, 1 skipped, 1 warning | 33.35 s (21:12:38–21:13:12) | 15.33 |

Both equal 06's counts. A ChamPBH `unittest` run was going on during the second.

### The tag

After the one commit:

```bash
git tag -a pre-datastorekit -m "Last commit on StochasticInstanton's own datastore layer, rehearsed (RH1, dk-and-rpk-migration prompt 07)"
git cat-file -t pre-datastorekit                 # tag
git rev-parse 'pre-datastorekit^{commit}'        # this commit
git ls-remote --tags origin pre-datastorekit     # not run again: nothing is pushed
```

The tag is annotated, local, and points at the commit that adds this note. **It is not pushed,
and nor is the branch:** the user pushes the tag (README §6.3). The orchestrator fills in the
commit's hash at review.

### Hygiene

- **Stores opened:**
  - RH1's three, each after its build had ended, plus `resumed-a`'s discarded store before its
    deletion;
  - the readers' copies, through `run_readers.sh`;
  - RH0's `02-reference`, `02-scalars-2`, `02-readers/{resumed,scalars}/before/` copies and
    `02-reference-profile`, through `compare_stores.py` and `sqlite3` `mode=ro` only.
- **RH0's stores unchanged**, after the stop:
  - `shasum -a 256 -c` over the 45 files of `02-reference*`, `02-scalars-2*` and both `before/`
    directories against the gate's hashes: all OK;
  - `02-resumed*` and `02-scalars*` by listing only: mtimes of 2026-10-20 08:15;
  - `ls -laTR` of both earlier attempts' directories against the gate's listing: identical but
    for the parent directory's own entry, which gained RH1's files.
- **Deleted:** only `resumed-a`'s 11 store files (D4). Nothing of RH0's.
- **Not opened:** no `test-gradient*.sqlite`, nothing under `out-*/`, no June or July store. The
  earlier attempts' directories were read only by D3's `shasum`.
- `ray stop` and `ray start` were never run. The venv is unchanged: one `raypoolkit` line, no
  `datastorekit`.
- The scratch scripts live in the session scratchpad, not in the repository.

## The scratch scripts

**`rows.py`**, run as `./venv/bin/python rows.py $R/07-reference $R/07-reference-profile.sqlite`
and `./venv/bin/python rows.py $R/07-resumed`. It gives the rows by timestamp, the validated
counts with child rows, orphans, journals and the profile calls:

```python
"""Read a closed rehearsal store mode=ro: per shard, the parent rows of the four homogeneous tables
with timestamp, validated and delta_Nstar, plus child-row counts by parent validation. Optionally
the profile database's object_get FullInstanton / efold_value calls."""
import glob
import sqlite3
import sys

stem = sys.argv[1]  # e.g. $R/07-reference  (no .sqlite)
profile = sys.argv[2] if len(sys.argv) > 2 else None


def ro(path):
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True)


CHILD = {
    "InflatonTrajectory": ("InflatonTrajectoryValue", "trajectory_serial"),
    "FullInstanton": ("FullInstantonValue", "instanton_serial"),
    "SlowRollInstanton": ("SlowRollInstantonValue", "instanton_serial"),
    "CompactionFunction": ("CompactionFunctionSamples", "parent_serial"),
}
rows = []
counts = {}
for shard in sorted(glob.glob(f"{stem}-shard*.sqlite")):
    sid = shard.rsplit("shard", 1)[1][:4]
    c = ro(shard)
    for t, (child, fk) in CHILD.items():
        cols = [r[1] for r in c.execute(f"PRAGMA table_info({t})")]
        dn = "delta_Nstar_serial" in cols
        q = f"SELECT p.serial, p.timestamp, p.validated" + (", d.value" if dn else ", NULL")
        q += f" FROM {t} p" + (" LEFT JOIN delta_Nstar d ON d.serial = p.delta_Nstar_serial" if dn else "")
        for serial, ts, val, dval in c.execute(q):
            nchild = c.execute(f"SELECT count(*) FROM {child} WHERE {fk} = ?", (serial,)).fetchone()[0]
            rows.append((ts, t, sid, serial, val, dval, nchild))
            k = (t, bool(val))
            counts.setdefault(k, [0, 0])
            counts[k][0] += 1
            counts[k][1] += nchild
        orphan = c.execute(
            f"SELECT count(*) FROM {child} WHERE {fk} NOT IN (SELECT serial FROM {t})"
        ).fetchone()[0]
        if orphan:
            print(f"!! shard {sid}: {orphan} orphan rows in {child}")
    c.close()

for r in sorted(rows):
    ts, t, sid, serial, val, dval, nchild = r
    print(f"{ts}  {t:20s} shard{sid} serial={serial} validated={val} dNstar={dval} children={nchild}")
print("--- by table, validated: (rows, child rows)")
for k in sorted(counts):
    print(k, counts[k])
for f in sorted(glob.glob(f"{stem}*.sqlite-journal") + glob.glob(f"{stem}*-wal")):
    print("journal/wal:", f)

if profile:
    c = ro(profile)
    print("--- profile:", [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")])
    for (lab,) in c.execute("SELECT label FROM jobs"):
        print("job:", lab)
    print("profile_data:", c.execute("SELECT count(*) FROM profile_data").fetchone()[0])
    for m, n in c.execute("SELECT method, count(*) FROM profile_data GROUP BY method ORDER BY 2 DESC"):
        print(f"  {m}: {n}")
    for st, m, md in c.execute(
        "SELECT start_time, method, metadata FROM profile_data WHERE method LIKE 'object_get%' "
        "AND (metadata LIKE '%FullInstanton%') ORDER BY start_time LIMIT 15"
    ):
        print("  FI get:", st, m, (md or "")[:100])
    for st, m, md in c.execute(
        "SELECT start_time, method, metadata FROM profile_data WHERE method LIKE 'object_get%' "
        "AND (metadata LIKE '%efold_value%') ORDER BY start_time LIMIT 3"
    ):
        print("  efold get:", st, m, (md or "")[:100])
```

**`l4_compare.py`**, run from the repository root as `./venv/bin/python l4_compare.py`:

```python
"""L4 (orchestrator's correction 3): 07's parsed stage counts for reference and scalars against
02's, record by record, less the provenance line (`packages`)."""
import json
import sys

OLD = ".documents/dk-and-rpk-migration/out/02-stage-counts.json"
NEW = ".documents/dk-and-rpk-migration/out/07-stage-counts.json"
KEYS = ("entries", "complete_lines", "integrity", "exit_status")


def by_build(path, nn):
    data = json.load(open(path))
    return {k.rsplit("/", 1)[-1][len(nn) + 1 : -len(".log")]: v for k, v in data.items()}


old, new = by_build(OLD, "02"), by_build(NEW, "07")
failed = False
for build in ("reference", "scalars"):
    for key in KEYS:
        same = old[build][key] == new[build][key]
        failed |= not same
        print(f"{build:10s} {key:15s} {'equal' if same else 'DIFFERS'}")
    print(f"{build:10s} {'packages':15s} 02: {old[build]['packages']}")
    print(f"{build:10s} {'':15s} 07: {new[build]['packages']}")
print("RESULT:", "L4 records equal" if not failed else "L4 records DIFFER")
sys.exit(1 if failed else 0)
```

## The deliberate-breakage record

None. This prompt changes no code (README §5 rule 8). Each check above is one a bad build fails:
- a lost or extra row is an A-only or B-only line;
- a science bit is a near miss;
- a missed prune leaves an unvalidated row that the count would show;
- a recomputed instanton shows in the lookup counts;
- a changed printed line breaks `stage_counts.py`'s parse or the L4 records.

RH0's control (02's D5, the orchestrator's one-ulp mutation at 02's review) showed that the
comparison can fail. `l4_compare.py`'s control is shown above.

## Observations not acted on

1. **The narrow window depends on the driver's pace, and the pace on the machine's load.**
   - The ~9.5 s before the first `FullInstanton` row is the driver minting ten `efold_value` grids
     in turn (about 0.8 s each). At a load of 37–108 that ran at least 1.1 s slower than in
     `reference`, which put `S` = 10.5 s before the window.
   - The pool's change (`raypoolkit` in place of `RayTools/`) moved `reference`'s window only
     slightly: 0.3 s earlier and 0.4 s narrower than RH0's.
   - For 11: measure `S` from that run's `reference`, and on a loaded machine aim later in the
     window, not earlier.
2. **A `SIGTERM`ed driver's exit status** was 15 and 1 here, within 02's 134, 15 or 1. Read the
   log, not the status.
3. **The profile count varies with which actor serves a replicated table's lease** (above). It is
   not a reproducibility measure, and 11 should not hold it to 807 or 803.
4. **Foreign suites from another session** ran twice around the gate. The rehearsal lock keeps
   rehearsals apart, not suites (README §4.1). Waiting on the foreign process's pid with Monitor,
   then on the load, worked without polling the stores.

## State handed to the next prompt

- **RH1 holds, and equals RH0 bit for bit in both modes.**
  - The stores are `07-reference.sqlite`, `07-resumed.sqlite` (dense) and `07-scalars.sqlite`
    (scalars-only), with ten shards each, under
    `~/ScienceData/StochasticInstantons-rehearsals/dk-and-rpk-migration/`.
  - RH2 (11) is held to bitwise equality, timings and timestamps aside, with RH1's stores and,
    through them, RH0's.
  - The read stores carry the readers' `version` `2026.3.0` row: `07-resumed.sqlite` and
    `07-scalars.sqlite`. `07-reference.sqlite` does not.
  - 11's baselines without that row are therefore:
    - dense: `07-reference.sqlite`, or `07-readers/resumed/before/07-resumed.sqlite`;
    - scalars-only: `07-readers/scalars/before/07-scalars.sqlite`, or RH0's `02-scalars-2.sqlite`.
- **The tag** `pre-datastorekit` is annotated, on this commit, and local. The user pushes it
  (README §6.3). P2's audit of the June and July stores reads from it (U7).
- **`scalar_data.csv`**, for 11's byte comparison: `b0564eecc22f9106dcccb57fd1a419749543c4b9d15dc0ffe7a8e0780e9058a2`
  on both `resumed` and `scalars`, at RH0 and RH1.
- **L4's records**: `reference`'s and `scalars`' `entries`, `complete_lines`, `integrity` and
  `exit_status` in `out/07-stage-counts.json` equal 02's. 11 compares its own with them, less
  `packages`, which will then name `datastorekit` too.
- **The resume pattern** at RH1: `resumed-a2` left 8 validated and 1 unvalidated `FullInstanton`;
  `resumed-b` pruned the 1 (with its 1,673 value rows) and computed 2.
- **The protocol, as run:**
  - `S` comes from `reference`'s stored timestamps and its profile database's `object_get
    FullInstanton` vector calls (the banner). The rows fell at banner +9.49 to +12.07 s.
  - A loaded machine slows the driver's `efold_value` minting, so measure afresh, and on a loaded
    machine aim later.
  - The exit status of a signalled driver may be 134, 15 or 1.
  - One prune report per pruning actor reached the driver's log.
  - `ray_cluster.sh` start took 7 s and stop 18 s.
- **The schema** at 06's tree is RH0's (`out/07-reference-schema.json` equals
  `out/02-reference-schema.json` but for `source`). 09 compares with either.
- **For 09:**
  - The old layer's behaviour under `raypoolkit`, through `config/datastore.py` and the mapping
    form of the vectorized gets, is now rehearsed under real Ray: RayPoolKit G4's run.
  - The profile database's 803 events are not a fixed target (Observation 3).
  - S1's baseline stays 02's: 69 passed of 69.
- **Suites:** default 696 (695 passed, 1 skipped); integration 62 (61 passed, 1 skipped).
- **No issue opened;** `.documents/OPEN-ISSUES.md` is unchanged (61 open, 26 closed). No SI
  cluster is running, and the lock is free.
