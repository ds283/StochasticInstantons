# dk-and-rpk-migration — verification

This document is the campaign's record of its rehearsals by value: README §4.1's protocol, run
at three points.
- **RH0** (prompt 02) runs it at the start tree.
- **RH1** (07) runs it before the DatastoreKit swap.
- **RH2** (11) runs it through both packages.

Prompt 12 adds the close. Each rehearsal adds one section, and nothing here is rewritten later
(README §5 rule 6).

What a rehearsal checks, and how its stores are compared, are README §4.1–§4.3:
- L1–L4;
- `tools/compare_stores.py`, which compares by value and treats timings and timestamps as
  bookkeeping;
- the reproducibility criterion that RH0 sets for RH1 and RH2.

Each section gives the cluster and the load, the builds with their times and exit statuses, L1–L4,
§4.3's result, and the commands verbatim. The outputs it keeps are in [`out/`](out/), and its
results note holds the detail.

`$R` below is `~/ScienceData/StochasticInstantons-rehearsals/dk-and-rpk-migration`. Store times
are local (BST); `interrupt_when.py` prints UTC.

## 1. RH0 — the start tree (prompt 02, 2026-10-20)

Results note: [`02-rehearse-the-start-tree.md`](02-rehearse-the-start-tree.md). Tree: `b218760`,
SI's own layer and `RayTools/`, with neither package installed.

### 1.0 RH0 was run three times

1. **First attempt, stopped for U11** (board §5.12). The dense builds still built the gradient
   branch, and its solves did not converge in over five hours. The user ruled that no rehearsal
   builds the gradient branch. Its files are in `$R/02-attempt-1-aborted/`.
2. **Second attempt, stopped at a reader** (board §5.12).
   - Its five builds ended as expected.
   - `run_readers.sh` step 2 ran `plot_InstantonSolutions.py` without the build's
     `--n-collocation-points 5`. It therefore inserted an `n_collocation_points=33` row into
     `02-resumed.sqlite`, beside the expected `version` row.
   - The user ruled to fix the script (`b218760`) and re-run.
   - Its preliminary comparisons were: `scalars` against `scalars-2` equal, and `reference`
     against the readers' `before/` copy of `resumed` equal.
   - Its files are in `$R/02-attempt-2-reader-defect/`.
3. **Third attempt, recorded below.**

### 1.1 The cluster and the load

- 10 CPUs. The load was 5.11 / 10.06 / 12.44 at 08:10:57 BST, with no foreign suite or Ray job.
  It rose to 74 during the builds: this cluster's workers and macOS's own processes.
- Started with
  `.documents/dk-and-rpk-migration/rehearsal/ray_cluster.sh start "dk-and-rpk-migration 02 (RH0)"`
  in 7 s. Address `127.0.0.1:6390`; actor line
  `./venv/bin/ray list actors --address 127.0.0.1:6390`.
- Stopped with `ray_cluster.sh stop` in 18 s: no process names `/tmp/ray-si`; ports 6390, 6391,
  8266 and 52366 free; the lock released.

### 1.2 The builds

Each build ran from the repository root, as a background task, with
`.documents/dk-and-rpk-migration/rehearsal/build.sh`. The load column is the load at the build's
start.

| Build | `build.sh` arguments | Start | End | Wall | Load | Exit |
|---|---|---|---|---|---|---|
| `reference` | `02 reference reference 127.0.0.1:6390 dense --profile-db` | 08:11:23 | 08:12:00 | 37 s | 5.26 | 0 |
| `resumed-a` | `02 resumed resumed-a 127.0.0.1:6390 dense` | 08:12:24 | 08:12:47 | 23 s | 33.80 | 1, by `SIGTERM` |
| `resumed-b` | `02 resumed resumed-b 127.0.0.1:6390 dense` | 08:13:05 | 08:13:30 | 25 s | 40.18 | 0 |
| `scalars` | `02 scalars scalars 127.0.0.1:6390 scalars` | 08:13:46 | 08:14:18 | 32 s | 44.99 | 0 |
| `scalars-2` | `02 scalars-2 scalars-2 127.0.0.1:6390 scalars` | 08:14:25 | 08:14:58 | 33 s | 56.31 | 0 |

**The interrupt**, started beside `resumed-a`:

```bash
./venv/bin/python .documents/dk-and-rpk-migration/rehearsal/interrupt_when.py \
    $R/logs/02-resumed-a.log $R/logs/02-resumed-a.pid \
    --banner "STAGE 2: FULL MSR INSTANTONS" --after 11.0 --poll 0.2
```

- **`S` = 11.0 s**, chosen from `reference`. The `STAGE 2` lookup ran at 08:11:34.72 (from the
  profile database), and the `FullInstanton` rows came at +9.77 to +12.76 s after it. 11.0 s falls
  between the fifth and sixth.
- The script saw the banner at 07:12:35 UTC and sent `SIGTERM` at 07:12:46 UTC. One attempt.
- **`resumed-a` left:**
  - the trajectory, validated;
  - **6 `FullInstanton` validated and 2 not** (δN★ 2.0333 and 2.6778, stored 6–24 ms before the
    signal), with 9,552 / 3,474 value rows;
  - no `SlowRollInstanton` and no `CompactionFunction`;
  - no journal file.
- All 11 of its actors were `DEAD` 12 s after the signal.

### 1.3 L1–L4

- **L1 holds.**
  - Four builds exit 0, every pool `ALL WORK ITEMS COMPLETE`.
  - `resumed-a` ends by the signal (`*** SIGTERM received …`), inside the window. Its exit status
    was 1; it was 134 and 15 at the earlier attempts.
  - No traceback.
  - The provenance line appears once in each log:
    `>> packages: datastorekit not installed; raypoolkit not installed`.
- **L2 holds.**
  - `resumed-b`'s open printed `Pruned 1 unvalidated FullInstanton records` on `shard0005` and
    `shard0007`, which is 2, the unvalidated count, on the same shards. Their value rows went
    with them, and no orphan is left.
  - `resumed-b`'s STAGE 2 lookup read "6 already computed, 4 to compute". It computed 4, and
    every later stage 10.
  - STAGE 1 computed nothing.
- **L3 holds.** For `resumed` and `scalars`:
  - steps 0–2 exit 0;
  - `compare_stores` of `before/` against the store finds exactly `version{label='2026.3.0'}`
    B only, no bookkeeping difference, and no problem.
  - `--inventory`, on each store: the grid, 1 trajectory, and 10 `FullInstanton`, 10
    `SlowRollInstanton` and 10 `CompactionFunction`, all validated, none unvalidated, and no
    gradient row.
  - `scalar_data.csv` SHA-256 is
    `b0564eecc22f9106dcccb57fd1a419749543c4b9d15dc0ffe7a8e0780e9058a2` on both stores
    (byte-identical).
- **L4, the baseline** (`out/02-stage-counts.txt`):

  | Stage | `reference` | `resumed-a` | `resumed-b` | `scalars`, `scalars-2` |
  |---|---|---|---|---|
  | STAGE 1 | 1 | 1 | 0 (read) | 1 |
  | STAGE 2 lookup; pool | 0 / 10; 10 | 0 / 10; killed | 6 / 4; 4 | — |
  | STAGE 3 | 0 / 10; 10 | — | 0 / 10; 10 | — |
  | STAGE 4 | 0 / 10; 10 | — | 0 / 10; 10 | — |
  | Unified pipeline | — | — | — | 0 / 10; 10 |
  | Pruned at open | — | — | 2 `FullInstanton` | — |

  The schema snapshots are `out/02-reference-schema.json` and `out/02-scalars-schema.json`, 30
  tables each, and they agree. The profile database holds `jobs` (1 row) and `profile_data`
  (807 rows).

### 1.4 §4.3: RH0 is bitwise reproducible, in both modes

| Comparison | Exit | Result |
|---|---|---|
| `compare_stores.py $R/02-reference.sqlite $R/02-resumed.sqlite` | 1 | only `version{label='2026.3.0'}`, B only: the readers' row |
| `compare_stores.py $R/02-scalars.sqlite $R/02-scalars-2.sqlite` | 1 | only `version{label='2026.3.0'}`, A only: the readers' row |
| `compare_stores.py $R/02-reference.sqlite $R/02-readers/resumed/before/02-resumed.sqlite` | **0** | **`RESULT: equal`** |
| `compare_stores.py $R/02-readers/scalars/before/02-scalars.sqlite $R/02-scalars-2.sqlite` | **0** | **`RESULT: equal`** |

- All 30 tables were matched row for row. In the dense mode that includes 16,564 rows each of
  `FullInstantonValue` and `SlowRollInstantonValue`, 33,128 `CompactionFunctionSamples` and
  7,521 `efold_value`.
- Only timestamps and the JSON timing keys differ.
- The prompt runs the readers before the comparisons, which is why the prescribed pairs carry the
  readers' one `version` row. The pairs taken with the `before/` copies are the builds as they
  ended.
- An independent per-δN★ hash of the value and sample tables, outside the tool, also finds the
  dense pair equal. Its control, `reference` against `scalars`, finds every key different.

**RH1 and RH2 are held to bitwise equality**, timings and timestamps aside, with
`02-reference.sqlite` and `02-scalars.sqlite`. Note that the latter now carries the readers'
`version` row.

### 1.5 S1 — the `slow` block

`./venv/bin/python -m pytest -m "slow and not integration" -p no:cacheprovider -rA --durations=0`,
run once after `ray_cluster.sh stop`, with nothing else running (08:18:02–08:24:33 BST):
- **69 passed** of 69 selected (810 collected), with no failure, error or skip, in 390.24 s;
- 11 warnings, all `Numerics/OnionCoordinate.py:77: RuntimeWarning: invalid value encountered in
  log`.

This is the baseline 09 is held to.

### 1.6 The suites, before the cluster

Run at 07:39–07:40 BST, before the second attempt's cluster. Python has not changed since but
for a docstring.
- `./venv/bin/python -m pytest -m "not integration and not slow" -q -p no:cacheprovider`: **680**
  (679 passed, 1 skipped).
- `RAY_ADDRESS=local ./venv/bin/python -m pytest -m integration -q -p no:cacheprovider`: **61**
  (60 passed, 1 skipped).

### 1.7 The commands, verbatim

From the repository root, in order:

```bash
.documents/dk-and-rpk-migration/rehearsal/ray_cluster.sh start "dk-and-rpk-migration 02 (RH0)"
.documents/dk-and-rpk-migration/rehearsal/build.sh 02 reference reference 127.0.0.1:6390 dense --profile-db
.documents/dk-and-rpk-migration/rehearsal/build.sh 02 resumed resumed-a 127.0.0.1:6390 dense
./venv/bin/python .documents/dk-and-rpk-migration/rehearsal/interrupt_when.py \
    ~/ScienceData/StochasticInstantons-rehearsals/dk-and-rpk-migration/logs/02-resumed-a.log \
    ~/ScienceData/StochasticInstantons-rehearsals/dk-and-rpk-migration/logs/02-resumed-a.pid \
    --banner "STAGE 2: FULL MSR INSTANTONS" --after 11.0 --poll 0.2
./venv/bin/ray list actors --address 127.0.0.1:6390 --filter "state=ALIVE"
.documents/dk-and-rpk-migration/rehearsal/build.sh 02 resumed resumed-b 127.0.0.1:6390 dense
.documents/dk-and-rpk-migration/rehearsal/build.sh 02 scalars scalars 127.0.0.1:6390 scalars
.documents/dk-and-rpk-migration/rehearsal/build.sh 02 scalars-2 scalars-2 127.0.0.1:6390 scalars
.documents/dk-and-rpk-migration/rehearsal/run_readers.sh 02 resumed 127.0.0.1:6390
.documents/dk-and-rpk-migration/rehearsal/run_readers.sh 02 scalars 127.0.0.1:6390
./venv/bin/python tools/compare_stores.py --snapshot $R/02-reference.sqlite --out .documents/dk-and-rpk-migration/out/02-reference-schema.json
./venv/bin/python tools/compare_stores.py --snapshot $R/02-scalars.sqlite --out .documents/dk-and-rpk-migration/out/02-scalars-schema.json
./venv/bin/python tools/compare_stores.py --schema $R/02-scalars.sqlite --against .documents/dk-and-rpk-migration/out/02-reference-schema.json
./venv/bin/python .documents/dk-and-rpk-migration/rehearsal/stage_counts.py $R/logs/02-reference.log \
    $R/logs/02-resumed-a.log $R/logs/02-resumed-b.log $R/logs/02-scalars.log $R/logs/02-scalars-2.log \
    --json .documents/dk-and-rpk-migration/out/02-stage-counts.json
./venv/bin/python tools/compare_stores.py $R/02-reference.sqlite $R/02-resumed.sqlite \
    --json .documents/dk-and-rpk-migration/out/02-compare-reference-resumed.json
./venv/bin/python tools/compare_stores.py $R/02-scalars.sqlite $R/02-scalars-2.sqlite \
    --json .documents/dk-and-rpk-migration/out/02-compare-scalars-scalars-2.json
./venv/bin/python tools/compare_stores.py $R/02-reference.sqlite $R/02-readers/resumed/before/02-resumed.sqlite \
    --json .documents/dk-and-rpk-migration/out/02-compare-reference-resumed-before-readers.json
./venv/bin/python tools/compare_stores.py $R/02-readers/scalars/before/02-scalars.sqlite $R/02-scalars-2.sqlite \
    --json .documents/dk-and-rpk-migration/out/02-compare-scalars-before-readers-scalars-2.json
sqlite3 "file:$R/02-reference-profile.sqlite?mode=ro" ".tables" "select count(*) from jobs;" "select count(*) from profile_data;"
.documents/dk-and-rpk-migration/rehearsal/ray_cluster.sh stop
./venv/bin/python -m pytest -m "slow and not integration" -p no:cacheprovider -rA --durations=0
```

Each comparison's text output was redirected to the `.txt` beside its JSON.

## 2. RH1 — before the DatastoreKit swap (prompt 07, 2026-10-21)

Results note: [`07-rehearse-before-the-datastore-swap.md`](07-rehearse-before-the-datastore-swap.md).
Tree: `9214c9b` (06's code, `5e41ce8`, with records on top). SI's own layer reads its data from
`config/datastore.py`, and the pool is `raypoolkit` `v0.2.0`; `datastorekit` is not installed.

**RH1 equals RH0, bit for bit, in both modes.** All five comparisons give `RESULT: equal`, exit 0.
L1–L4 hold.

### 2.0 Two stops before the cluster

The gate checks began on 2026-10-20 at 21:10 BST. They passed, and the suites were run (§2.6).
- At 21:13 the agent found a ChamPBH test suite running on the machine, another session's. It
  stopped before the cluster and asked.
- The session was then paused overnight by a quota limit.
- It was resumed on 2026-10-21 at 10:01. At once a second ChamPBH suite loop started (pid 91493,
  10:01:31–10:08:36). The agent stopped and asked again.
- The orchestrator ruled to wait for that loop to end, then five minutes or a 1-minute load below
  15, whichever came first.
- The loop ended at 10:08:36, and the five minutes ended at 10:13:41 with the load still 52.9. Only
  desktop processes were running: Time Machine, Spotlight, the Claude apps. There was no suite and
  no Ray job.
- The cluster was started at 10:13:54. No foreign suite or Ray job ran while it was up.

### 2.1 The cluster and the load

- 10 CPUs. The load was 48.14 / 53.12 / 40.04 at 10:13:54 BST, from desktop processes alone. It
  peaked at 108.66 at 10:15, during `resumed-a`, when Time Machine's `backupd` ran and a Claude app
  restarted.
- Started with
  `.documents/dk-and-rpk-migration/rehearsal/ray_cluster.sh start "dk-and-rpk-migration 07 (RH1)"`
  in 7 s, `gcs_server` pid 2788. Address `127.0.0.1:6390`; actor line
  `./venv/bin/ray list actors --address 127.0.0.1:6390`.
- Stopped with `ray_cluster.sh stop` at 10:24:13, in 18 s: `SIGTERM` to 18 processes, `SIGKILL`
  to 2788 and 2812, no process names `/tmp/ray-si`, ports 6390, 6391, 8266 and 52366 free, the
  lock released.

### 2.2 The builds

Each build ran from the repository root, as a background task, with
`.documents/dk-and-rpk-migration/rehearsal/build.sh`. The load column is the 1-minute load at the
build's start.

| Build | `build.sh` arguments | Start | End | Wall | Load | Exit |
|---|---|---|---|---|---|---|
| `reference` | `07 reference reference 127.0.0.1:6390 dense --profile-db` | 10:14:06 | 10:14:42 | 36 s | 44.08 | 0 |
| `resumed-a` | `07 resumed resumed-a 127.0.0.1:6390 dense` | 10:15:13 | 10:15:41 | 28 s | 37.21 | 15, by `SIGTERM`: **outside the window** |
| `resumed-a2` | `07 resumed resumed-a2 127.0.0.1:6390 dense` (fresh store) | 10:19:30 | 10:19:57 | 27 s | 24.84 | 1, by `SIGTERM`: inside the window |
| `resumed-b` | `07 resumed resumed-b 127.0.0.1:6390 dense` | 10:20:20 | 10:20:44 | 24 s | 31.96 | 0 |
| `scalars` | `07 scalars scalars 127.0.0.1:6390 scalars` | 10:20:50 | 10:21:21 | 31 s | 46.12 | 0 |

`reference`'s stages took 5.47 s, 12.1 s, 8.76 s and 1.61 s. RH0's took 5.84, 12.8, 8.77 and 1.68.

**`S`**, chosen from `reference`. The times are the stores' and the profile database's, BST.
- The `STAGE 2` lookup ran at 10:14:17.614–17.632 (the profile database's `object_get
  FullInstanton` vector calls).
- The `FullInstanton` rows came at +9.49, +9.57, +9.61, +10.73, +10.76, +11.01, +11.59, +11.60,
  +11.66 and +12.07 s after it. RH0's came at +9.77 to +12.76 s.
- The last `CompactionFunction` row came at +23.2 s.

**The interrupts**, each started straight after its build:

```bash
./venv/bin/python .documents/dk-and-rpk-migration/rehearsal/interrupt_when.py \
    ~/ScienceData/StochasticInstantons-rehearsals/dk-and-rpk-migration/logs/07-resumed-a.log \
    ~/ScienceData/StochasticInstantons-rehearsals/dk-and-rpk-migration/logs/07-resumed-a.pid \
    --banner "STAGE 2: FULL MSR INSTANTONS" --after 10.5 --poll 0.2
./venv/bin/python .documents/dk-and-rpk-migration/rehearsal/interrupt_when.py \
    ~/ScienceData/StochasticInstantons-rehearsals/dk-and-rpk-migration/logs/07-resumed-a2.log \
    ~/ScienceData/StochasticInstantons-rehearsals/dk-and-rpk-migration/logs/07-resumed-a2.pid \
    --banner "STAGE 2: FULL MSR INSTANTONS" --after 12.0 --poll 0.2
```

- **`resumed-a`, `S` = 10.5 s:**
  - The script saw the banner at 09:15:30 UTC and sent the signal at 09:15:40 UTC. The driver
    logged `SIGTERM received` at 10:15:40.746 BST.
  - The driver was still minting the tenth instanton's `efold_value` grid: its last row is
    10:15:40.731. That is at least banner +10.5 s, against `reference`'s +9.41 s. So no
    `FullInstanton` row had been stored: the signal fell before the window.
  - The store held only the trajectory, validated.
  - Its 11 actors (job `02000000`) were `DEAD` by 10:15:48.
  - Its 11 store files were deleted, and the build was rerun as `resumed-a2` on a fresh store.
- **`resumed-a2`, `S` = 12.0 s**, set to land inside the window if the build ran up to about 25%
  slower than `reference`:
  - The script saw the banner at 09:19:43 UTC and sent the signal at 09:19:55 UTC. The driver
    logged `SIGTERM received` at 10:19:56.035 BST.
  - `FullInstanton` rows were stored from 10:19:53.435 to 10:19:55.967.
- **`resumed-a2` left:**
  - the trajectory, validated (10 replicas, 57,130 value rows);
  - **8 `FullInstanton` validated** (13,122 value rows);
  - **1 not validated**: δN★ 1.7111 on `shard0004`, serial 161, with 1,673 value rows. It was
    stored 68 ms before the signal;
  - δN★ 2.6778 not stored;
  - no `SlowRollInstanton` and no `CompactionFunction`;
  - no `-journal` or `-wal` file.
- **The actor check** at 10:19:59: `ray list actors --address 127.0.0.1:6390 --filter
  "state=ALIVE"` gave "No resource in the cluster". The full listing shows all 11 actors of job
  `03000000` (10 `Datastore`, 1 `SerialPoolBroker`) `DEAD`.

### 2.3 L1–L4

- **L1 holds.**
  - `reference`, `resumed-b` and `scalars` end `** driver exit status 0` with 4, 4 and 2
    `ALL WORK ITEMS COMPLETE`.
  - `resumed-a` and `resumed-a2` end by the signal (`*** SIGTERM received …`, the absl stack),
    with exit statuses 15 and 1.
  - No traceback.
  - The only `WARNING` lines are `resumed-b`'s prune header and, in `scalars`, the raylet's
    `16 PYTHON worker processes` advisory. No line says `did not validate`.
  - The provenance line appears once in each of the five logs:
    `>> packages: datastorekit not installed; raypoolkit 0.2.0 (https://github.com/ds283/RayPoolKit@eaef0ce60e2fc354bb32f0ad576010e6a83c1976, requested v0.2.0)`.
- **L2 holds.**
  - `compare_stores.py $R/07-reference.sqlite $R/07-resumed.sqlite`: `RESULT: equal`, exit 0.
  - `resumed-b`'s open printed one report, from one actor:
    `!! INTEGRITY WARNING (2026-10-21T10:20:24): datastore "shard0004-store" …` and
    `Pruned 1 unvalidated FullInstanton records`. The actor's own log under
    `/tmp/ray-si/session_2026-10-21_10-13-56_480986_2787/logs/` holds the same, read before the
    stop.
  - So 1 was pruned, and 1 was unvalidated, on the same shard. Afterwards every
    `FullInstantonValue` row has a validated parent (16,564), and no orphan is left.
  - `resumed-b`:
    - STAGE 1 computed nothing ("no compute items were evaluated");
    - STAGE 2's lookup read "8 already computed, 2 to compute", and it computed 2;
    - STAGES 3 and 4 computed 10 each.
  - The 8 kept rows keep their `resumed-a2` timestamps.
- **L3 holds.** `run_readers.sh 07 resumed 127.0.0.1:6390` (10:22:40–10:23:12) and
  `run_readers.sh 07 scalars 127.0.0.1:6390` (10:23:20–10:23:45) each exit 1, by design.
  - `status.txt`: steps 0–2 exit 0, step 4 exit 1, step 3 not run (U11).
  - Step 4 finds exactly one row, `version{label='2026.3.0'}`, B only. No bookkeeping differs and
    no problem is named.
  - The plot logs read `n_collocation_points: 1 value = [ 5 ]`.
  - `scalar_data.csv` hashes to
    `b0564eecc22f9106dcccb57fd1a419749543c4b9d15dc0ffe7a8e0780e9058a2` on both stores (11 lines,
    3,592 bytes), RH0's byte for byte.
  - `--inventory` on each store equals RH0's but for the provenance line, Ray's connection lines
    and the timestamps of the records.
- **L4 holds.**
  - `stage_counts.py`'s records for `reference` and `scalars` (`entries`, `complete_lines`,
    `integrity`, `exit_status`) equal RH0's exactly. Only the provenance line differs, as it must.
  - `stage_counts.py` parsed every `raypoolkit` log unchanged.
  - The resume's pattern is RH0's:
    - only unvalidated rows were pruned (1 = 1);
    - only what was not kept was computed (STAGE 2: 8 + 2);
    - the counts add up to `reference`'s (10 / 10 / 10 / 1).
  - The figures differ from RH0's (6 + 4, 2 pruned) because the signal fell at a different point.

  | Stage | `reference` | `resumed-a` | `resumed-a2` | `resumed-b` | `scalars` |
  |---|---|---|---|---|---|
  | STAGE 1 | 1 | 1 | 1 | 0 (read) | 1 |
  | STAGE 2 lookup; pool | 0 / 10; 10 | 0 / 10; killed | 0 / 10; killed | 8 / 2; 2 | — |
  | STAGE 3 | 0 / 10; 10 | — | — | 0 / 10; 10 | — |
  | STAGE 4 | 0 / 10; 10 | — | — | 0 / 10; 10 | — |
  | Unified pipeline | — | — | — | — | 0 / 10; 10 |
  | Pruned at open | — | — | — | 1 `FullInstanton` | — |

- **The schema** (`out/07-reference-schema.json`, 30 tables) is RH0's: it differs from
  `out/02-reference-schema.json` only in its `source` line. `--schema` of `07-reference` and of
  `07-scalars` against RH0's snapshot gives "the schemas agree", exit 0, for both.
- **The profile database** (not under §4.3) holds `jobs` 1 and `profile_data` **803**, against
  RH0's 807:

  | Method | RH0 | RH1 |
  |---|---|---|
  | `object_get` | 443 | 443 |
  | `ClientPool.lease_serial\|lease_serials` | 137 | 135 |
  | `ClientPool.lease_serial\|commit_serials` | 76 | 76 |
  | `ClientPool.release` | 61 | 59 |
  | `object_store` | 40 | 40 |
  | `object_validate_item` | 40 | 40 |
  | `read_largest_store_ids` | 10 | 10 |

  The two missing pairs are one `lease_serials` and one `release` each, for `efold_value`.
  `efold_value` is replicated, and each client that leases its serials adds one of each. Its
  serials were leased through 8 actors at RH0 and 6 at RH1, which pick up 22 and 20 leases. Which
  actor serves a replicated table's request varies from run to run; the other replicated tables'
  serials also went through different shards. No stored value depends on it.

### 2.4 §4.3: RH1 equals RH0, bit for bit, in both modes

The comparisons ran before the readers, so every store is compared as its build left it.

| Comparison | Exit | Result |
|---|---|---|
| `compare_stores.py $R/07-reference.sqlite $R/07-resumed.sqlite` | **0** | **`RESULT: equal`** |
| `compare_stores.py $R/02-reference.sqlite $R/07-reference.sqlite` | **0** | **`RESULT: equal`** |
| `compare_stores.py $R/02-reference.sqlite $R/07-resumed.sqlite` | **0** | **`RESULT: equal`** |
| `compare_stores.py $R/02-scalars-2.sqlite $R/07-scalars.sqlite` | **0** | **`RESULT: equal`** |
| `compare_stores.py $R/02-readers/scalars/before/02-scalars.sqlite $R/07-scalars.sqlite` | **0** | **`RESULT: equal`** |

- Each comparison covers all 30 tables, with nothing in A or B only and no problem named.
- **Dense** (each pair), against RH0's rows per store:
  - `CompactionFunctionSamples` 33,128;
  - `FullInstantonValue` 16,564 and `SlowRollInstantonValue` 16,564;
  - `InflatonTrajectoryValue` 5,713;
  - `efold_value` 7,521;
  - `CompactionFunction`, `FullInstanton` and `SlowRollInstanton` 10 each, and `InflatonTrajectory` 1;
  - `delta_Nstar` 10, and every other replicated parameter table 1 (`version` 1);
  - the three gradient tables, `IntegrationSolver`, `QuarticPotential`, `quartic_coupling`,
    `redshift` and `store_tag` 0.
- **Scalars-only:** the same, with the three value/sample tables 0, as at RH0.
- Only bookkeeping differs between matched rows: timestamps, and the JSON timing keys
  `compute_time` and `mean_time_per_picard_iteration`.
- The first table in build order whose rows differ is **none**.

**So RH1 equals RH0.** SI's layer, fed from `config/datastore.py` and driven by `raypoolkit`,
stores what the start tree stored, bit for bit, across a kill, a prune and a resume. RH2 (11) is
held to the same criterion with RH1's stores and, through them, RH0's.

### 2.5 The tag

`pre-datastorekit`, annotated, on the commit that adds this section (`0527480`). It is not pushed.

### 2.6 The suites, before the cluster

Run on 2026-10-20 at 21:11–21:13 BST at `9214c9b`, before the first stop. They are cited, not
re-run, since no code changed between them and the cluster.
- `./venv/bin/python -m pytest -m "not integration and not slow" -q -p no:cacheprovider`: **696**
  (695 passed, 1 skipped), 31.56 s, at a load of 4.21.
- `RAY_ADDRESS=local ./venv/bin/python -m pytest -m integration -q -p no:cacheprovider`: **62**
  (61 passed, 1 skipped), 33.35 s, at a load of 15.33. A ChamPBH suite was running beside it.

### 2.7 The commands, verbatim

From the repository root, in order. `$R` is
`~/ScienceData/StochasticInstantons-rehearsals/dk-and-rpk-migration`.

```bash
./venv/bin/python tools/compare_stores.py $R/02-reference.sqlite $R/02-readers/resumed/before/02-resumed.sqlite
./venv/bin/python tools/compare_stores.py $R/02-readers/scalars/before/02-scalars.sqlite $R/02-scalars-2.sqlite
./venv/bin/python -m pytest -m "not integration and not slow" -q -p no:cacheprovider
RAY_ADDRESS=local ./venv/bin/python -m pytest -m integration -q -p no:cacheprovider
.documents/dk-and-rpk-migration/rehearsal/ray_cluster.sh start "dk-and-rpk-migration 07 (RH1)"
.documents/dk-and-rpk-migration/rehearsal/build.sh 07 reference reference 127.0.0.1:6390 dense --profile-db
.documents/dk-and-rpk-migration/rehearsal/build.sh 07 resumed resumed-a 127.0.0.1:6390 dense
./venv/bin/python .documents/dk-and-rpk-migration/rehearsal/interrupt_when.py \
    ~/ScienceData/StochasticInstantons-rehearsals/dk-and-rpk-migration/logs/07-resumed-a.log \
    ~/ScienceData/StochasticInstantons-rehearsals/dk-and-rpk-migration/logs/07-resumed-a.pid \
    --banner "STAGE 2: FULL MSR INSTANTONS" --after 10.5 --poll 0.2
./venv/bin/ray list actors --address 127.0.0.1:6390 --filter "state=ALIVE"
rm -v $R/07-resumed.sqlite $R/07-resumed-shard000{0,1,2,3,4,5,6,7,8,9}.sqlite
.documents/dk-and-rpk-migration/rehearsal/build.sh 07 resumed resumed-a2 127.0.0.1:6390 dense
./venv/bin/python .documents/dk-and-rpk-migration/rehearsal/interrupt_when.py \
    ~/ScienceData/StochasticInstantons-rehearsals/dk-and-rpk-migration/logs/07-resumed-a2.log \
    ~/ScienceData/StochasticInstantons-rehearsals/dk-and-rpk-migration/logs/07-resumed-a2.pid \
    --banner "STAGE 2: FULL MSR INSTANTONS" --after 12.0 --poll 0.2
./venv/bin/ray list actors --address 127.0.0.1:6390 --filter "state=ALIVE"
./venv/bin/ray list actors --address 127.0.0.1:6390 --limit 1000
.documents/dk-and-rpk-migration/rehearsal/build.sh 07 resumed resumed-b 127.0.0.1:6390 dense
.documents/dk-and-rpk-migration/rehearsal/build.sh 07 scalars scalars 127.0.0.1:6390 scalars
./venv/bin/python tools/compare_stores.py $R/07-reference.sqlite $R/07-resumed.sqlite \
    --json .documents/dk-and-rpk-migration/out/07-compare-reference-resumed.json
./venv/bin/python tools/compare_stores.py $R/02-reference.sqlite $R/07-reference.sqlite \
    --json .documents/dk-and-rpk-migration/out/07-compare-02reference-07reference.json
./venv/bin/python tools/compare_stores.py $R/02-reference.sqlite $R/07-resumed.sqlite \
    --json .documents/dk-and-rpk-migration/out/07-compare-02reference-07resumed.json
./venv/bin/python tools/compare_stores.py $R/02-scalars-2.sqlite $R/07-scalars.sqlite \
    --json .documents/dk-and-rpk-migration/out/07-compare-02scalars2-07scalars.json
./venv/bin/python tools/compare_stores.py $R/02-readers/scalars/before/02-scalars.sqlite $R/07-scalars.sqlite \
    --json .documents/dk-and-rpk-migration/out/07-compare-02scalarsbefore-07scalars.json
./venv/bin/python tools/compare_stores.py --snapshot $R/07-reference.sqlite --out .documents/dk-and-rpk-migration/out/07-reference-schema.json
./venv/bin/python tools/compare_stores.py --schema $R/07-reference.sqlite --against .documents/dk-and-rpk-migration/out/02-reference-schema.json
./venv/bin/python tools/compare_stores.py --schema $R/07-scalars.sqlite --against .documents/dk-and-rpk-migration/out/02-reference-schema.json
./venv/bin/python .documents/dk-and-rpk-migration/rehearsal/stage_counts.py $R/logs/07-reference.log \
    $R/logs/07-resumed-a.log $R/logs/07-resumed-a2.log $R/logs/07-resumed-b.log $R/logs/07-scalars.log \
    --json .documents/dk-and-rpk-migration/out/07-stage-counts.json
sqlite3 "file:$R/07-reference-profile.sqlite?mode=ro" "select method, count(*) from profile_data group by method;"
.documents/dk-and-rpk-migration/rehearsal/run_readers.sh 07 resumed 127.0.0.1:6390
.documents/dk-and-rpk-migration/rehearsal/run_readers.sh 07 scalars 127.0.0.1:6390
.documents/dk-and-rpk-migration/rehearsal/ray_cluster.sh stop
```

Each comparison's text output, and `stage_counts.py`'s, was redirected to the `.txt` beside its
JSON. The L4 comparison with RH0's records is a scratch script, reproduced in the results note.

## 3. RH2 — through both packages (prompt 11, 2026-10-22)

Results note: [`11-rehearse-through-both-packages.md`](11-rehearse-through-both-packages.md).
Tree: `66b1c81` (10b's code, `19716cd`, with records on top). Every pool is `datastorekit` `v0.5.0`'s
(`f47b9a2`) and every work pool `raypoolkit` `v0.2.0`'s (`eaef0ce6`), both installed from their tags, neither
editable.

**RH2 equals RH1, and so RH0, bit for bit, in both modes.** All six comparisons give `RESULT: equal`, exit 0.
L1–L4 hold, and so does H1. DatastoreKit's G4 holds for SI.

### 3.1 The cluster and the load

- 10 CPUs. The load was 9.05 / 12.84 / 22.65 at the gate (21:26 BST) and 31.90 / 17.67 / 22.87 at 21:29:01, just
  after the integration suite. During the builds it rose to 57–64 from their own workers, and to 80 during the
  scalars readers, with desktop processes beside them. No other session's suite, build or Ray job ran at any
  point (the user had been asked to hold them).
- Started with
  `.documents/dk-and-rpk-migration/rehearsal/ray_cluster.sh start "dk-and-rpk-migration 11 (RH2)"` at 21:29:01 in
  5 s, `gcs_server` pid 72107. Address `127.0.0.1:6390`; actor line
  `./venv/bin/ray list actors --address 127.0.0.1:6390`.
- Stopped with `ray_cluster.sh stop` at 21:35:35, in 19 s: `SIGTERM` to 18 processes, `SIGKILL` to 72107 and
  72108, no process names `/tmp/ray-si`, ports 6390, 6391, 8266 and 52366 free, the lock released.
- The raylet's disk line ("over 95% full, available space: 18.2 GB") appeared in every build. Ray refused nothing.

### 3.2 The builds

Each build ran from the repository root, as a background task, with
`.documents/dk-and-rpk-migration/rehearsal/build.sh`. The load column is the 1-minute load at the build's start.

| Build | `build.sh` arguments | Start | End | Wall | Load | Exit |
|---|---|---|---|---|---|---|
| `reference` | `11 reference reference 127.0.0.1:6390 dense --profile-db` | 21:29:10 | 21:29:50 | 40 s | 32.10 | 0 |
| `resumed-a` | `11 resumed resumed-a 127.0.0.1:6390 dense` | 21:30:24 | 21:30:53 | 29 s | 55.73 | 15, by `SIGTERM`: inside the window |
| `resumed-b` | `11 resumed resumed-b 127.0.0.1:6390 dense` | 21:31:30 | 21:31:58 | 28 s | 57.30 | 0 |
| `scalars` | `11 scalars scalars 127.0.0.1:6390 scalars` | 21:32:17 | 21:32:50 | 33 s | 53.23 | 0 |

`reference`'s stages took 6.04 s, 12.9 s, 9.59 s and 2.27 s. RH1's took 5.47, 12.1, 8.76 and 1.61.

**`S`**, chosen from `reference`. The times are the stores' and the profile database's, BST.
- The `STAGE 2` lookup ran at 21:29:21.865–21:29:21.875 (the profile database's `object_get
  {'object': 'FullInstanton', 'type': 'vector'}` calls, RH1's labels).
- The last `efold_value` row was minted at banner +8.76 s (RH1: +9.41).
- The `FullInstanton` rows came at +9.76, +9.78, +9.85, +10.88, +10.91, +11.32, +11.56, +11.58, +12.30 and +12.89 s
  after it. RH1's came at +9.49 to +12.07 s.
- The last `CompactionFunction` row came at +26.3 s.

**The interrupt**, started straight after its build:

```bash
./venv/bin/python .documents/dk-and-rpk-migration/rehearsal/interrupt_when.py \
    ~/ScienceData/StochasticInstantons-rehearsals/dk-and-rpk-migration/logs/11-resumed-a.log \
    ~/ScienceData/StochasticInstantons-rehearsals/dk-and-rpk-migration/logs/11-resumed-a.pid \
    --banner "STAGE 2: FULL MSR INSTANTONS" --after 12.0 --poll 0.2
```

- **`resumed-a`, `S` = 12.0 s, the first and only attempt.** Set late in the window, for a loaded machine: at
  `reference`'s pace it falls between the eighth and ninth rows, and it stays in the narrow window for a driver up
  to about 23% slower.
  - The script saw the banner at 20:30:39 UTC and sent the signal at 20:30:51 UTC to pid 73409, the pidfile's. The
    driver logged `*** SIGTERM received at time=1792701051 ***` at 21:30:51.666 BST.
  - `FullInstanton` rows were stored from 21:30:50.012 to 21:30:51.590, the last 76 ms before the signal.
- **`resumed-a` left** (read `mode=ro` after it ended):
  - the trajectory, validated (10 replicas, 57,130 value rows);
  - **4 `FullInstanton` validated** (δN★ 0.1, 0.42222, 1.0667, 1.7111; 6,336 value rows);
  - **2 not validated**: δN★ 2.0333 on `shard0005` (serial 81, 1,705 value rows) and δN★ 1.3889 on `shard0003`
    (serial 101, 1,640);
  - δN★ 0.74444, 2.3556, 2.6778 and 3.0 not stored;
  - no `SlowRollInstanton` and no `CompactionFunction`;
  - **the primary's `replication_in_flight`: 0 rows**; no `-journal`, `-wal` or `-shm` file; `efold_value` 7,521
    rows on each of the ten shards.
- **The actor check** at 21:31:00, 9 s after the signal: `ray list actors --address 127.0.0.1:6390 --filter
  "state=ALIVE"` gave "No resource in the cluster". The full listing shows all 11 actors of job `02000000` (10
  `Datastore`, 1 `SerialPoolBroker`) `DEAD`.

### 3.3 L1–L4

- **L1 holds.**
  - `reference`, `resumed-b` and `scalars` end `** driver exit status 0` with 4, 4 and 2
    `ALL WORK ITEMS COMPLETE`.
  - `resumed-a` ends by the signal (`*** SIGTERM received …`, the absl stack), exit 15: Ray's driver handler's
    `sys.exit(15)`.
  - No traceback. The only `WARNING`/`Warning` lines are Ray's start-up `FutureWarning` and `resumed-b`'s two
    prune headers. No line says `did not validate`.
  - The provenance line appears once in each of the four logs, and in each reader's logs:
    `>> packages: datastorekit 0.5.0 (https://github.com/ds283/DatastoreKit@f47b9a255e9ad58e0d0eaf85644f53b575884d31, requested v0.5.0); raypoolkit 0.2.0 (https://github.com/ds283/RayPoolKit@eaef0ce60e2fc354bb32f0ad576010e6a83c1976, requested v0.2.0)`.
- **L2 holds.**
  - `compare_stores.py $R/11-reference.sqlite $R/11-resumed.sqlite`: `RESULT: equal`, exit 0.
  - `resumed-b`'s open printed no reconciliation line (no record had been left) and no replicated prune. Two
    actors pruned, each printing RH1's text:
    `!! INTEGRITY WARNING (2026-10-22T21:31:34): datastore "shard0003-store" …` with
    `Pruned 1 unvalidated FullInstanton records`, and the same for `shard0005-store`. Ray forwarded the second
    only at the end of the log; both actors' own logs under
    `/tmp/ray-si/session_2026-10-22_21-29-03_242377_72080/logs/` hold their two lines, read before the stop.
    `stage_counts.py` finds both.
  - So 2 were pruned, and 2 were unvalidated, on the same shards. Afterwards every `FullInstantonValue` row has a
    validated parent (16,564), and no orphan is left.
  - `resumed-b`:
    - STAGE 1 computed nothing ("no compute items were evaluated");
    - STAGE 2's lookup read "4 already computed, 6 to compute", and it computed 6;
    - STAGES 3 and 4 computed 10 each.
  - The 4 kept rows keep their `resumed-a` timestamps.
- **L3 holds.** `run_readers.sh 11 resumed 127.0.0.1:6390` (21:34:10–21:34:42) and
  `run_readers.sh 11 scalars 127.0.0.1:6390` (21:34:51–21:35:18) each exit 1, by design.
  - `status.txt`: steps 0–2 exit 0, step 4 exit 1, step 3 not run (U11).
  - Step 4 finds exactly one row, `version{label='2026.3.0'}`, B only. No bookkeeping differs and no problem is
    named.
  - The plot logs read `n_collocation_points: 1 value = [ 5 ]`.
  - `scalar_data.csv` hashes to
    `b0564eecc22f9106dcccb57fd1a419749543c4b9d15dc0ffe7a8e0780e9058a2` on both stores (11 lines, 3,592 bytes),
    RH0's and RH1's byte for byte.
  - `--inventory` (now `read_inventory`, before Ray) on each store: `problems: none`; 10 shards, 7,574 records in
    24 classes; the ten δN★, `N_init` 20, `N_final` 5, φ₀ 15, π₀ 0 and m 1e-05 `PlanckMass`, 7,521 e-fold values,
    1 trajectory and 10 of each instanton and compaction function validated, 0 unvalidated, no gradient row:
    RH1's values and counts, in 10's layout.
- **L4 holds.**
  - `stage_counts.py`'s records for `reference` and `scalars` (`entries`, `complete_lines`, `integrity`,
    `exit_status`) equal RH1's exactly. Only the provenance line differs, as it must. The control (RH1's
    `reference` against RH2's `resumed-b`) differs, so the comparison can fail.
  - `stage_counts.py` parsed every log unchanged.
  - The resume's pattern is RH1's:
    - only unvalidated rows were pruned (2 = 2);
    - only what was not kept was computed (STAGE 2: 4 + 6);
    - the counts add up to `reference`'s (10 / 10 / 10 / 1).
  - The figures differ from RH1's (8 + 2, 1 pruned) because the signal fell at a different point.

  | Stage | `reference` | `resumed-a` | `resumed-b` | `scalars` |
  |---|---|---|---|---|
  | STAGE 1 | 1 | 1 | 0 (read) | 1 |
  | STAGE 2 lookup; pool | 0 / 10; 10 | 0 / 10; killed | 4 / 6; 6 | — |
  | STAGE 3 | 0 / 10; 10 | — | 0 / 10; 10 | — |
  | STAGE 4 | 0 / 10; 10 | — | 0 / 10; 10 | — |
  | Unified pipeline | — | — | — | 0 / 10; 10 |
  | Pruned at open | — | — | 2 `FullInstanton` (one per actor) | — |

- **The schema** (`out/11-reference-schema.json`, 30 tables) is RH1's: it differs from
  `out/07-reference-schema.json` and `out/09-temp-schema.json` only in its `source` line. `--schema` of
  `11-reference` and of `11-scalars` against RH1's snapshot gives "the schemas agree", exit 0, for both.
- **The profile database** (not under §4.3) holds `jobs` 1 and `profile_data` **712**, against RH1's 803:

  | Method | RH1 | RH2 |
  |---|---|---|
  | `object_get` | 443 | 352 |
  | `ClientPool.lease_serial\|lease_serials` | 135 | 135 |
  | `ClientPool.lease_serial\|commit_serials` | 76 | 76 |
  | `ClientPool.release` | 59 | 59 |
  | `object_store` | 40 | 40 |
  | `object_validate_item` | 40 | 40 |
  | `read_largest_store_ids` | 10 | 10 |

  The 91 fewer `object_get` events are `efold_value` (210 → 120) and `version` (11 → 10). STAGE 3's ten gets of
  grids every shard already holds ran on all ten actors at RH1 and on one actor each at RH2: the package reads a
  replicated table's existing rows from one shard. No stored value depends on it. The `ProfileAgent` also printed
  its slow-query report (3 `object_get` over 2 s: STAGE 1's `efold_value` replica writes under load), a message
  SI's old agent had too.

### 3.4 §4.3: RH2 equals RH1, and so RH0, bit for bit, in both modes

The comparisons ran before the readers, so every store is compared as its build left it, against baselines with
no readers' row.

| Comparison | Exit | Result |
|---|---|---|
| `compare_stores.py $R/11-reference.sqlite $R/11-resumed.sqlite` | **0** | **`RESULT: equal`** |
| `compare_stores.py $R/07-reference.sqlite $R/11-reference.sqlite` | **0** | **`RESULT: equal`** |
| `compare_stores.py $R/07-reference.sqlite $R/11-resumed.sqlite` | **0** | **`RESULT: equal`** |
| `compare_stores.py $R/07-readers/scalars/before/07-scalars.sqlite $R/11-scalars.sqlite` | **0** | **`RESULT: equal`** |
| `compare_stores.py $R/02-scalars-2.sqlite $R/11-scalars.sqlite` | **0** | **`RESULT: equal`** |
| `compare_stores.py $R/02-reference.sqlite $R/11-reference.sqlite` | **0** | **`RESULT: equal`** |

- Each comparison covers all 30 tables, with nothing in A or B only and no problem named.
- **Dense** (each of the four), RH1's rows per store:
  - `CompactionFunctionSamples` 33,128;
  - `FullInstantonValue` 16,564 and `SlowRollInstantonValue` 16,564;
  - `InflatonTrajectoryValue` 5,713 (57,130 over the ten shards);
  - `efold_value` 7,521;
  - `CompactionFunction`, `FullInstanton` and `SlowRollInstanton` 10 each, and `InflatonTrajectory` 1;
  - `delta_Nstar` 10, and every other replicated parameter table 1 (`version` 1);
  - the three gradient tables, `IntegrationSolver`, `QuarticPotential`, `quartic_coupling`, `redshift` and
    `store_tag` 0.
- **Scalars-only** (both): the same, with the three value/sample tables 0, as at RH0 and RH1.
- Only bookkeeping differs between matched rows: timestamps, and the JSON timing keys `compute_time` and
  `mean_time_per_picard_iteration`. The four dense texts are identical below their headers, and so are the two
  scalars-only texts.
- The first table in build order whose rows differ is **none**.

**So RH2 equals RH1.** SI's tree after the swap, its pools and actors the package's, stores what SI's own layer
stored before it, bit for bit, across a kill, the package's prune at open and a resume, in both modes.

### 3.5 H1: store hygiene by the package

Run after the comparisons and before the readers; no Ray is needed and none was initialised by the tools.
- `./venv/bin/python -m datastorekit.tools.shard_key_audit` on `11-reference`, `11-resumed` and `11-scalars`: each
  `VERDICT: OK -- no inconsistency found in <primary>.`, exit 0 (10 shard keys, one per shard; the cross-file check
  against shard #0 by its bare record; 10 `delta_Nstar` rows).
- `./venv/bin/python -m datastorekit.tools.sharded_store copy $R/11-reference.sqlite $R/11-reference-copy.sqlite`:
  `>> copy: "…/11-reference-copy.sqlite" with 10 shards` and its ten shard lines, exit 0.
- The copy read with `read_inventory` (read-only, Ray not initialised): no problem; 24 classes, each class's
  `(records, validated)` equal to `11-reference`'s.
- `compare_stores.py $R/11-reference.sqlite $R/11-reference-copy.sqlite`: `RESULT: equal`, exit 0, with no
  bookkeeping difference.
- `ShardedPool.closed_store_files` and `ShardedPool.delete_store` on the copy's primary: the same 11 paths (the ten
  shards in serial order, then the primary), deleted; no `11-reference-copy*` file remains.

### 3.6 The suites, before the cluster

Run on 2026-10-22 at 21:27–21:29 BST at `66b1c81`, serially, in the foreground.
- `./venv/bin/python -m pytest -m "not integration and not slow" -q -p no:cacheprovider`: **732**
  (731 passed, 1 skipped), 41.11 s, at a load of 8.64.
- `RAY_ADDRESS=local ./venv/bin/python -m pytest -m integration -q -p no:cacheprovider`: **67**
  (66 passed, 1 skipped), 47.91 s, at a load of 12.80.

### 3.7 The commands, verbatim

From the repository root, in order. `$R` is
`~/ScienceData/StochasticInstantons-rehearsals/dk-and-rpk-migration`.

```bash
./venv/bin/python tools/compare_stores.py $R/07-reference.sqlite $R/07-readers/resumed/before/07-resumed.sqlite
./venv/bin/python tools/compare_stores.py $R/07-readers/scalars/before/07-scalars.sqlite $R/02-scalars-2.sqlite
./venv/bin/python -m pytest -m "not integration and not slow" -q -p no:cacheprovider
RAY_ADDRESS=local ./venv/bin/python -m pytest -m integration -q -p no:cacheprovider
.documents/dk-and-rpk-migration/rehearsal/ray_cluster.sh start "dk-and-rpk-migration 11 (RH2)"
.documents/dk-and-rpk-migration/rehearsal/build.sh 11 reference reference 127.0.0.1:6390 dense --profile-db
./venv/bin/python rows.py $R/11-reference $R/11-reference-profile.sqlite   # scratch; in the results note
.documents/dk-and-rpk-migration/rehearsal/build.sh 11 resumed resumed-a 127.0.0.1:6390 dense
./venv/bin/python .documents/dk-and-rpk-migration/rehearsal/interrupt_when.py \
    ~/ScienceData/StochasticInstantons-rehearsals/dk-and-rpk-migration/logs/11-resumed-a.log \
    ~/ScienceData/StochasticInstantons-rehearsals/dk-and-rpk-migration/logs/11-resumed-a.pid \
    --banner "STAGE 2: FULL MSR INSTANTONS" --after 12.0 --poll 0.2
./venv/bin/ray list actors --address 127.0.0.1:6390 --filter "state=ALIVE"
./venv/bin/ray list actors --address 127.0.0.1:6390 --limit 1000
./venv/bin/python rows.py $R/11-resumed   # scratch
.documents/dk-and-rpk-migration/rehearsal/build.sh 11 resumed resumed-b 127.0.0.1:6390 dense
./venv/bin/python rows.py $R/11-resumed   # scratch
.documents/dk-and-rpk-migration/rehearsal/build.sh 11 scalars scalars 127.0.0.1:6390 scalars
./venv/bin/python tools/compare_stores.py $R/11-reference.sqlite $R/11-resumed.sqlite \
    --json .documents/dk-and-rpk-migration/out/11-compare-reference-resumed.json
./venv/bin/python tools/compare_stores.py $R/07-reference.sqlite $R/11-reference.sqlite \
    --json .documents/dk-and-rpk-migration/out/11-compare-07reference-11reference.json
./venv/bin/python tools/compare_stores.py $R/07-reference.sqlite $R/11-resumed.sqlite \
    --json .documents/dk-and-rpk-migration/out/11-compare-07reference-11resumed.json
./venv/bin/python tools/compare_stores.py $R/02-reference.sqlite $R/11-reference.sqlite \
    --json .documents/dk-and-rpk-migration/out/11-compare-02reference-11reference.json
./venv/bin/python tools/compare_stores.py $R/07-readers/scalars/before/07-scalars.sqlite $R/11-scalars.sqlite \
    --json .documents/dk-and-rpk-migration/out/11-compare-07scalarsbefore-11scalars.json
./venv/bin/python tools/compare_stores.py $R/02-scalars-2.sqlite $R/11-scalars.sqlite \
    --json .documents/dk-and-rpk-migration/out/11-compare-02scalars2-11scalars.json
./venv/bin/python tools/compare_stores.py --snapshot $R/11-reference.sqlite --out .documents/dk-and-rpk-migration/out/11-reference-schema.json
./venv/bin/python tools/compare_stores.py --schema $R/11-reference.sqlite --against .documents/dk-and-rpk-migration/out/07-reference-schema.json
./venv/bin/python tools/compare_stores.py --schema $R/11-scalars.sqlite --against .documents/dk-and-rpk-migration/out/07-reference-schema.json
./venv/bin/python .documents/dk-and-rpk-migration/rehearsal/stage_counts.py $R/logs/11-reference.log \
    $R/logs/11-resumed-a.log $R/logs/11-resumed-b.log $R/logs/11-scalars.log \
    --json .documents/dk-and-rpk-migration/out/11-stage-counts.json
./venv/bin/python -m datastorekit.tools.shard_key_audit $R/11-reference.sqlite
./venv/bin/python -m datastorekit.tools.shard_key_audit $R/11-resumed.sqlite
./venv/bin/python -m datastorekit.tools.shard_key_audit $R/11-scalars.sqlite
./venv/bin/python -m datastorekit.tools.sharded_store copy $R/11-reference.sqlite $R/11-reference-copy.sqlite
./venv/bin/python h1_readback.py $R/11-reference.sqlite $R/11-reference-copy.sqlite   # scratch; in the results note
./venv/bin/python tools/compare_stores.py $R/11-reference.sqlite $R/11-reference-copy.sqlite \
    --json .documents/dk-and-rpk-migration/out/11-compare-reference-copy.json
./venv/bin/python -c "
import sys
from datastorekit.SQL.ShardedPool import ShardedPool
p = sys.argv[1]
planned = ShardedPool.closed_store_files(p)
print('closed_store_files:'); [print('  ', x) for x in planned]
deleted = ShardedPool.delete_store(p)
print('delete_store returned:'); [print('  ', x) for x in deleted]
print('same list:', [str(x) for x in planned] == [str(x) for x in deleted], len(deleted), 'paths')
import ray; print('ray initialised:', ray.is_initialized())
" $R/11-reference-copy.sqlite
.documents/dk-and-rpk-migration/rehearsal/run_readers.sh 11 resumed 127.0.0.1:6390
.documents/dk-and-rpk-migration/rehearsal/run_readers.sh 11 scalars 127.0.0.1:6390
.documents/dk-and-rpk-migration/rehearsal/ray_cluster.sh stop
```

Each comparison's text output, `stage_counts.py`'s and the H1 tools' were redirected to the `.txt` files of
[`out/`](out/) named in the results note. The L4 comparison with RH1's records and `rows.py` are scratch scripts,
reproduced in the results note.
