# 02 — rehearse the start tree (RH0)

**Subject:** Rehearse the start tree (RH0) and record its baseline
**Commit:** this commit, on branch `dk-and-rpk-migration`, on top of `b218760`
**Date:** 2026-10-20, by Claude Opus 5.5
**Result:** **COMPLETE, at the third attempt.** L1–L4 hold. §4.3 is measured for both modes:
**RH0 is bitwise reproducible.** The two dense stores agree in every science value, and so do the
two scalars-only stores. Their only difference is the one `version` row (`2026.3.0`) that the
readers write. The prompt runs the readers before the comparisons, so the prescribed comparisons
exit 1 on that row alone (D3). The same comparisons against the readers' `before/` copies give
`RESULT: equal`, exit 0. S1: the `slow` block passes in full, 69 of 69, in 6 min 30 s.
The suites at dispatch were 680 (679 passed, 1 skipped) and 61 (60 passed, 1 skipped). No code
changed. No issue is opened. No SI cluster is left running and the lock is free.

Prompt: [`.prompts/dk-and-rpk-migration/02-rehearse-the-start-tree.md`](../../.prompts/dk-and-rpk-migration/02-rehearse-the-start-tree.md),
as amended for U11 and after the second attempt. The orchestrator's notes for 02 governed where
they corrected the prompt: the integration suite's form, and S1 run as a background task.
The record of the rehearsal is [`verification.md`](verification.md) §1. The outputs kept are in
[`out/`](out/), as `02-*`.

## The three attempts

1. **First attempt (01:28–07:09 BST): stopped for U11** (board §5.12). Its `reference` still built
   the gradient branch. The homogeneous branch was stored in about 35 s. None of the first four
   `GradientCoupledInstanton` solves finished in 5 h 24 min, and every inner Picard step failed
   (`[gci-picard-inner-fails-on-rehearsal-grid]`). The user ruled U11: no rehearsal builds the
   gradient branch. That attempt's files are in `$REHEARSAL_ROOT/02-attempt-1-aborted/`. This
   agent did not run it and did not open its files.
2. **Second attempt (07:37–07:46 BST, this agent): stopped at a reader.**
   - Suites before the cluster: 680 and 61 (below).
   - All five builds ended as expected, in 24–35 s each. `resumed-a` used `S` = 10.5 s, left 3
     validated `FullInstanton` rows and nothing unvalidated, and exited **15**. `resumed-b`
     computed the other 7 and every later stage, and pruned nothing.
   - `run_readers.sh 02 resumed` then added **two** replicated rows to `02-resumed.sqlite`: the
     expected `version` `2026.3.0`, and `n_collocation_points=33`. Step 2 ran
     `plot_InstantonSolutions.py` without the build's `--n-collocation-points 5`. The parser's
     default (`config/argument_parser.py:331-341`, `[33]`) reached `config/pipeline_setup.py:95-106`,
     which gets-or-inserts the value whatever the targets. That is a stop under prompt §4.
   - The agent stopped the cluster (the lock was released) and did not patch the script.
   - Preliminary comparisons, read-only, after the stop:
     - `scalars` against `scalars-2`: `RESULT: equal`, exit 0;
     - `reference` against `resumed`: exit 1, on the reader's two rows only;
     - `reference` against the readers' `before/` copy of `resumed`: `RESULT: equal`, exit 0.
   - Findings carried here: the exit status 15 (Observation 1), the raylet's worker-count warning
     (Observation 3) and the `PIPELINE LOOKUP` wording (Observation 4). Its fourth finding, the
     stale `STAGE G` in `interrupt_when.py`'s docstring, was fixed by the orchestrator.
   - **The user ruled: fix the reader and re-run RH0 from the start.** The orchestrator made the
     fix at `b218760`: step 2 now passes `--n-collocation-points 5 --alpha-regularization 0.01`.
     The attempt's files are in `$REHEARSAL_ROOT/02-attempt-2-reader-defect/`.
3. **Third attempt (08:10–08:24 BST, this agent):** the run recorded below, on the standard
   names, with the fixed script.

## What shipped

- **[`verification.md`](verification.md)**, created: an introduction and **§1 RH0**.
- **[`out/`](out/) `02-*`**, small text only (about 220 KB in all; the largest file is 40 KB):
  - `02-reference-schema.json`, `02-scalars-schema.json`: the schema snapshots, 30 tables each.
    The second checked against the first gives "the schemas agree";
  - `02-stage-counts.txt`, `.json`: `stage_counts.py` on the five logs;
  - `02-compare-reference-resumed.{txt,json}` and `02-compare-scalars-scalars-2.{txt,json}`: the
    two comparisons of prompt §1.4.2;
  - `02-compare-reference-resumed-before-readers.{txt,json}` and
    `02-compare-scalars-before-readers-scalars-2.{txt,json}`: the same pairs, taken with the
    readers' `before/` copy in place of the read store (D3);
  - `02-readers-{resumed,scalars}-{status.txt,inventory.log,compare_stores.txt,scalar_data.csv}`:
    the readers' abridged output. The inventory logs drop only the raylet's disk-space lines;
  - `02-scalar_data.sha256`.
- The board: the §1 row, L1–L4, V1, S1, gate RH0 and §5.13.
- No code, script, tool or test changed. Nothing was installed.

## Deviations from the prompt

- **D1 — the suites are cited from the second attempt, not re-run.** They ran at 07:39 BST,
  before that attempt's cluster. Since then Python has changed only in a docstring of
  `interrupt_when.py` (`b218760`; `git diff 9caeea3 b218760 -- '*.py'`). The orchestrator's ruling
  allowed citing them. **IMPLEMENTATION CHOICE.**
- **D2 — `S` = 11.0 s, not the 10.5 s that worked at the second attempt.** It was chosen afresh
  from this `reference`, whose `FullInstanton` rows came about 0.5 s later after the banner (see
  "S" below). **IMPLEMENTATION CHOICE.**
- **D3 — both prescribed comparisons exit 1, on the readers' `version` row alone; supplementary
  comparisons against the `before/` copies were added.**
  - Prompt §1.4 runs the readers (§1.4.1) before the comparisons (§1.4.2). The plot script's
    read-write pool then writes the expected `version` `2026.3.0` row into `02-resumed.sqlite` and
    `02-scalars.sqlite`, and not into `02-reference.sqlite` or `02-scalars-2.sqlite`. So each
    prescribed comparison reports that one row:
    - `reference` against `resumed`: `B only 1`;
    - `scalars` against `scalars-2`: `A only 1`.
  - Every other table matched, with only bookkeeping differing and no problem named.
  - The readers' own before/after comparison (L3) shows that the row is theirs.
  - To measure §4.3 on the stores as the builds left them, the same two pairs were also compared
    with the readers' `before/` copies: both `RESULT: equal`, exit 0.
  - I read this as **no §4.3 difference**: the builds agree bit for bit, and the one row is L3's
    documented effect. So the prompt's "do not commit" did not apply, and this commit is made.
  - The ordering is the prompt's (**STRUCTURALLY REQUIRED**). The extra comparisons are an
    **IMPLEMENTATION CHOICE**. 07 and 11 meet the same row (State handed on).
- **D4 — `resumed-a` exited 1, neither 134 nor 15.** Its log shows Ray's
  `*** SIGTERM received at time=1792480366 ***` and the absl stack dump, as at both earlier
  attempts, so it ended by the signal. The exit status Ray's handler leaves varies: 134 at the
  first attempt, 15 at the second, 1 here. **UNINTENDED DRIFT** in the expectation, not in any
  code. L1 is read from the log's `SIGTERM received` line, not from the status.
- **D5 — an independent check of the dense pair, beside the tool.** It was a scratch script that
  reads every shard `mode=ro`. For each δN★ it hashes the sorted
  `(efold N bits, fields_json text)` rows of `FullInstantonValue` and `SlowRollInstantonValue`,
  and every non-key column of `CompactionFunctionSamples`.
  - `reference` against `resumed`: 30 keys and 66,256 rows each side, no key differing.
  - Control, `reference` against `scalars` (no value rows): all 30 keys differ, so the check can
    fail.
  - `reference` against the second attempt's `reference`: no key differing, so the grid is
    reproducible across attempts too. That is the agent's own earlier store; the orchestrator's
    message allowed reading it.
  
  **IMPLEMENTATION CHOICE.**

- **D6 — the two `scalar_data.csv` copies were staged by force, without line-ending conversion.**
  - `.git/info/exclude:24` ignores `*.csv`. The prompt asks for the files to be kept, so they were
    added by explicit path with `-f`.
  - They have CRLF line endings (Python's `csv` default), and the user's global
    `core.autocrlf=input` would have committed them with LF, so their committed SHA-256 would not
    have been the one recorded. They were staged with
    `git -c core.autocrlf=false add -f <path>`, a one-command override that changes no
    configuration.
  - `git show :<path> | shasum -a 256` gives
    `b0564eecc22f9106dcccb57fd1a419749543c4b9d15dc0ffe7a8e0780e9058a2` for both.
  
  **IMPLEMENTATION CHOICE.**

No other deviation.

## Verification performed

### The machine and the cluster

- **Idle at the start.**
  - At 08:10:57 BST the load was 5.11 / 10.06 / 12.44 on 10 CPUs.
  - No `pytest`, `main.py`, `raylet`, `gcs_server` or `ray::` process; no process names `/tmp/ray-si`.
  - Lock free; the four ports free; `RAY_ADDRESS` unset; `pip show datastorekit raypoolkit`
    finds neither.
  - `$REHEARSAL_ROOT` held only the two attempt directories and an empty `logs/`.
  - At 08:11:12, just before the start: 4.49 / 9.69 / 12.26.
- **`ray_cluster.sh start "dk-and-rpk-migration 02 (RH0)"`:** started in 7 s, `gcs_server` pid
  49871. It printed the address `127.0.0.1:6390` and the actor line
  `./venv/bin/ray list actors --address 127.0.0.1:6390`. Every actor check below used that line,
  with `--filter "state=ALIVE"`.
- **The load during the builds** rose from 5 to 74. In the second attempt's run the high load was
  checked with `ps`: macOS's own processes, Dropbox, the Claude apps, and this cluster's workers.
  No foreign suite or Ray job ran at any time.
- **`ray_cluster.sh stop`** (about 08:17:39):
  - `SIGTERM` to 18 processes, `SIGKILL` to 49871 and 49883 after the grace;
  - "no process names /tmp/ray-si; ports 6390 6391 8266 52366 are free";
  - "released the rehearsal lock"; "stopped in 18s".
  
  `status` at 08:17:57: lock free, no SI processes, the four ports free.

### The builds

Each build was a background task: `.documents/dk-and-rpk-migration/rehearsal/build.sh … ` from the
repository root. Times are BST, and the load is the 1-minute average at the build's start.

| Build | Command | Start | End | Wall | Load | Exit |
|---|---|---|---|---|---|---|
| `reference` | `build.sh 02 reference reference 127.0.0.1:6390 dense --profile-db` | 08:11:23 | 08:12:00 | 37 s | 5.26 | 0 |
| `resumed-a` | `build.sh 02 resumed resumed-a 127.0.0.1:6390 dense` | 08:12:24 | 08:12:47 | 23 s | 33.80 | 1 (`SIGTERM`) |
| `resumed-b` | `build.sh 02 resumed resumed-b 127.0.0.1:6390 dense` | 08:13:05 | 08:13:30 | 25 s | 40.18 | 0 |
| `scalars` | `build.sh 02 scalars scalars 127.0.0.1:6390 scalars` | 08:13:46 | 08:14:18 | 32 s | 44.99 | 0 |
| `scalars-2` | `build.sh 02 scalars-2 scalars-2 127.0.0.1:6390 scalars` | 08:14:25 | 08:14:58 | 33 s | 56.31 | 0 |

**Beside `resumed-a`**, started straight after it:

```bash
./venv/bin/python .documents/dk-and-rpk-migration/rehearsal/interrupt_when.py \
    ~/ScienceData/StochasticInstantons-rehearsals/dk-and-rpk-migration/logs/02-resumed-a.log \
    ~/ScienceData/StochasticInstantons-rehearsals/dk-and-rpk-migration/logs/02-resumed-a.pid \
    --banner "STAGE 2: FULL MSR INSTANTONS" --after 11.0 --poll 0.2
```

Its output, in UTC:

```text
[2026-10-20T07:12:24+00:00] interrupt_when: waiting for "STAGE 2: FULL MSR INSTANTONS" in …/02-resumed-a.log; then 11 s; then SIGTERM
[2026-10-20T07:12:24+00:00] interrupt_when: driver pid 50508 (from …/02-resumed-a.pid)
[2026-10-20T07:12:35+00:00] interrupt_when: saw "STAGE 2: FULL MSR INSTANTONS"; waiting 11 s
[2026-10-20T07:12:46+00:00] interrupt_when: sent SIGTERM to pid 50508
```

It exited 0. One attempt sufficed.

`reference`'s stage times were STAGE 1 5.84 s, STAGE 2 12.8 s, STAGE 3 8.77 s and STAGE 4 1.68 s,
so the branch takes 37 s; the 45-minute limit (P1) is far off.

### `S`, and how it was chosen

From the closed `02-reference.sqlite`, read with `sqlite3` `mode=ro`, and its profile database.
Times are the stores' naive local time, BST.
- The last `InflatonTrajectory` row (its tenth replica) was at 08:11:34.237.
- The profile database's `object_get FullInstanton vector` calls, the `STAGE 2` lookup, were at
  08:11:34.719–34.726. So the `** STAGE 2: FULL MSR INSTANTONS LOOKUP:` banner, which
  `interrupt_when.py` matches first, was at about 08:11:34.73.
- `FullInstanton` rows were stored at 08:11:44.503, 44.528, 44.596, 45.473, 45.504, 46.122,
  46.648, 46.667, 46.732 and 47.485. That is banner +9.77, +9.80, +9.87, +10.74, +10.77, +11.39,
  +11.92, +11.94, +12.00 and +12.76 s.
- `SlowRollInstanton` rows: 08:11:55.854–56.186. `CompactionFunction` rows:
  08:11:58.014–58.963, i.e. banner +24.2 s, the end of the wide window.
- The roughly 9.8 s before the first row is the driver minting each instanton's `efold_value`
  grid in turn, about 0.75 s each (the profile database's `object_get efold_value` calls from
  34.749 on). That is store work, not worker start-up, so a warm cluster does not shorten it much.

`S` = 11.0 s puts the signal between the fifth and sixth rows at reference's pace. It still falls
among the rows if `resumed-a` runs up to about 1.2 s slower, or up to 1.7 s faster. If it runs
faster still, the signal lands in the wide window (up to +24 s). At the second attempt
`resumed-a` ran about 0.2 s behind its `reference`.

**What happened** (BST):
- `resumed-a`'s last trajectory row was at 08:12:34.778;
- `interrupt_when.py` saw the banner in the second 08:12:35;
- the driver logged `SIGTERM received` at 08:12:46.364;
- `FullInstanton` rows were stored from 08:12:44.485 to 08:12:46.358.

### The rows `resumed-a` left (read `mode=ro` after the build ended)

| Table | Validated | Not validated | Child rows (validated parent / not) |
|---|---|---|---|
| `InflatonTrajectory` | 1 (replicated: 10 rows over 10 shards) | 0 | `InflatonTrajectoryValue` 57,130 / 0 |
| `FullInstanton` | **6** (δN★ 0.1, 0.42222, 0.74444, 1.0667, 1.3889, 1.7111) | **2** (δN★ 2.0333 on shard 5, 2.6778 on shard 7) | `FullInstantonValue` 9,552 / **3,474** |
| `SlowRollInstanton` | 0 | 0 | — |
| `CompactionFunction` | 0 | 0 | — |

- The two unvalidated rows were stored at 08:12:46.340 and 46.358, 6–24 ms before the driver took
  the signal. They were stored and never validated: the case the prune at open exists for.
- No `-journal` or `-wal` file was beside any shard.

**The actor check** at 08:12:58, 12 s after the signal:
- `ray list actors --address 127.0.0.1:6390 --filter "state=ALIVE"` gave "No resource in the
  cluster";
- the full listing showed all 11 actors of job `02000000` (10 `Datastore`, 1 `SerialPoolBroker`)
  `DEAD`.

### L1 — every build ends as it should

- `reference`, `resumed-b`, `scalars` and `scalars-2` end with `** driver exit status 0`. Every
  pool they build prints `ALL WORK ITEMS COMPLETE`: 4, 4, 2 and 2 lines.
- `resumed-a` ends by the signal (`*** SIGTERM received …`, the absl stack), inside the narrow
  window, with exit status 1 (D4).
- **No traceback in any log.** Every line matching `Traceback`, `Error` or `WARNING` was read:
  - the raylet's disk warning, which is known: `/tmp/ray-si/session_* is over 95% full`;
  - Ray's start-up `FutureWarning`;
  - `resumed-b`'s two `!! INTEGRITY WARNING` headers (L2);
  - one raylet `WARNING: 16 PYTHON worker processes have been started … 4x the maximum expected
    startup concurrency (4)` in `scalars` (Observation 3).
  
  No `did not validate` line appeared.
- Each log carries the provenance line once:
  `>> packages: datastorekit not installed; raypoolkit not installed`.

### L2 — the resume

- **The prune at `resumed-b`'s open.** Two reports were forwarded to the driver's log, one per
  actor, and were not deduplicated. The actors' own logs under
  `/tmp/ray-si/session_2026-10-20_08-11-14_631654_49870/logs/` were read before the stop, and
  hold the same two:

  ```text
  (Datastore pid=50870) !! INTEGRITY WARNING (2026-10-20T08:13:09): datastore "shard0007-store" (physical file …/02-resumed-shard0007.sqlite)
  (Datastore pid=50870) Pruned 1 unvalidated FullInstanton records
  (Datastore pid=50867) !! INTEGRITY WARNING (2026-10-20T08:13:09): datastore "shard0005-store" (physical file …/02-resumed-shard0005.sqlite)
  (Datastore pid=50867) Pruned 1 unvalidated FullInstanton records
  ```

  The total pruned, 2, equals the unvalidated count read between the builds, on the same two
  shards, so **only unvalidated rows were pruned**. The cascade took their 3,474 value rows: after
  `resumed-b` every `FullInstantonValue` row has a validated parent (16,564, as in `reference`),
  and none is orphaned. No other build printed a prune report.
- **`resumed-b` computed only what `resumed-a` had not kept:**
  - STAGE 1: 0 computed, "no compute items were evaluated";
  - STAGE 2: lookup "6 already computed, 4 to compute", then 4 computed;
  - STAGE 3 and STAGE 4: 10 each.
  
  `resumed-a`'s 6 kept plus `resumed-b`'s 4 make `reference`'s 10. The two pruned instantons
  were recomputed, and none that was kept validated was.
- §4.3's dense comparison is below.

### L3 — the readers

`run_readers.sh 02 resumed 127.0.0.1:6390` (08:15:06–08:15:44, load 63.84), then
`run_readers.sh 02 scalars 127.0.0.1:6390` (08:15:52–08:16:27, load 64.61), each a background
task. Both exited 1, as the script does by design when step 4 finds the expected row.
- **`status.txt`, both stores:** step 0 `copy-before` exit 0, step 1 `inventory` exit 0, step 2
  `plot_InstantonSolutions` exit 0, step 4 `compare_stores` exit 1. Step 3 is printed as not run
  (U11).
- **`4-compare_stores.log`, both stores:** exactly one table differs, `version`, `B only 1`,
  `version{label='2026.3.0'}`. Bookkeeping that differs: none. Problems: none.
  `n_collocation_points` matches: step 2's plot log now reads `n_collocation_points: 1 value =
  [ 5 ]`.
- **What `--inventory` printed** (identical on both stores but for the paths and the times):
  - 10 δN★ `[0.1 … 3]`, N_init `[20]`, N_final `[5]`, φ₀ `[15 PlanckMass]`, π₀ `[0 PlanckMass]`,
    m `[1e-05 PlanckMass]`;
  - quartic couplings "no values committed"; 7,521 e-fold sample values;
  - trajectories 1 validated / 0 unvalidated;
  - Full MSR, slow-roll and compaction 10 validated / 0 unvalidated each;
  - gradient-coupled 0 / 0.
  
  Saved as `out/02-readers-*-inventory.log`.
- **`scalar_data.csv`:**
  - `plot_InstantonSolutions.py` on `resumed`:
    `b0564eecc22f9106dcccb57fd1a419749543c4b9d15dc0ffe7a8e0780e9058a2`;
  - on `scalars` with `--no-store-values`:
    `b0564eecc22f9106dcccb57fd1a419749543c4b9d15dc0ffe7a8e0780e9058a2`.
  
  The two are byte-identical (11 lines, 3,592 bytes) and also equal the second attempt's.
- The plot logs carry the `Datastore` actors' physics warnings
  `!! WARNING: CompactionFunction(…): slow-roll instanton is compensated (C_min=… < 0) …`
  (Observation 2).

### L4 — the baseline

`stage_counts.py` on the five logs (`out/02-stage-counts.txt`). Every pool reported lookup,
compute, store and validation equal.

| Stage | `reference` | `resumed-a` | `resumed-b` | `scalars`, `scalars-2` |
|---|---|---|---|---|
| `STAGE 1: BACKGROUND INFLATIONARY TRAJECTORIES` | 1 computed | 1 computed | 0, no compute items evaluated | 1 computed |
| `STAGE 2: FULL MSR INSTANTONS` lookup, then pool | 0 / 10; 10 | 0 / 10; INCOMPLETE (signal) | 6 / 4; 4 | — |
| `STAGE 3: SLOW-ROLL INSTANTONS` | 0 / 10; 10 | — | 0 / 10; 10 | — |
| `STAGE 4` section; `COMPACTION FUNCTIONS LOOKUP`; `… AND MASSES` pool | 0 / 10; 10 | — | 0 / 10; 10 | — |
| `PIPELINE LOOKUP`; `STAGES 2+3+4: UNIFIED PIPELINE` | — | — | — | 0 / 10 ("10 skipped"); 10 |
| integrity reports | none | none | 2 × `Pruned 1 unvalidated FullInstanton records` | none |
| driver exit status | 0 | 1 | 0 | 0 |

The resume's **pattern** for 07 and 11:
- it prunes only unvalidated rows (2 = 2);
- it computes only what was not kept (STAGE 2 6 + 4);
- its counts add up to `reference`'s.

The figures depend on where the signal fell.

**Rows per store** (from the comparisons):
- Each dense store: `InflatonTrajectory` 1 (`InflatonTrajectoryValue` 5,713 on each shard),
  `FullInstanton` 10 (`FullInstantonValue` 16,564), `SlowRollInstanton` 10
  (`SlowRollInstantonValue` 16,564), `CompactionFunction` 10 (`CompactionFunctionSamples` 33,128),
  `efold_value` 7,521, `delta_Nstar` 10. No gradient row.
- Each scalars-only store: the same but for the three value/sample tables, which are empty.

**The profile database** `02-reference-profile.sqlite` (read `mode=ro`) has two tables:
- `jobs`: 1 row, `2026.6.1-job-"dk-and-rpk-migration-02-reference"-db-"…/02-reference.sqlite"-2026-10-20T08:11:25`;
- `profile_data`: 807 rows: `object_get` 443, `ClientPool.lease_serial|lease_serials` 137,
  `ClientPool.lease_serial|commit_serials` 76, `ClientPool.release` 61, `object_store` 40,
  `object_validate_item` 40, `read_largest_store_ids` 10.

The ProfileAgent printed "807 total database events".

**The schema snapshots:** `out/02-reference-schema.json` and `out/02-scalars-schema.json`, 30
client tables each. `compare_stores.py --schema 02-scalars.sqlite --against
out/02-reference-schema.json`: "RESULT: the schemas agree", exit 0. The two files differ only in
their `source` line.

### §4.3 — the reproducibility: bitwise, in both modes

All runs are `./venv/bin/python tools/compare_stores.py A B --json …`, with the text saved beside
each JSON. `$R` is `~/ScienceData/StochasticInstantons-rehearsals/dk-and-rpk-migration`.

| A | B | Exit | `RESULT:` | Differs |
|---|---|---|---|---|
| `$R/02-reference.sqlite` | `$R/02-resumed.sqlite` | 1 | the stores differ, or a problem was named | `version`: B only 1, `version{label='2026.3.0'}` (the readers' row) |
| `$R/02-scalars.sqlite` | `$R/02-scalars-2.sqlite` | 1 | the stores differ, or a problem was named | `version`: A only 1, `version{label='2026.3.0'}` (the readers' row) |
| `$R/02-reference.sqlite` | `$R/02-readers/resumed/before/02-resumed.sqlite` | **0** | **equal** | none |
| `$R/02-readers/scalars/before/02-scalars.sqlite` | `$R/02-scalars-2.sqlite` | **0** | **equal** | none |

- **Every table was covered**: 30 tables, and every row of each was matched.
  - Dense: `CompactionFunctionSamples` 33,128, `FullInstantonValue` 16,564,
    `SlowRollInstantonValue` 16,564, `InflatonTrajectoryValue` 5,713, `efold_value` 7,521, the
    four parents 10 / 10 / 10 / 1, and every replicated parameter table.
  - Scalars-only: the same with the three value/sample tables empty.
  - The three gradient tables are empty in all four stores (U11's known gap). `redshift` is
    noted, as always.
- **Bookkeeping only** differs between matched rows: every `timestamp`; the JSON timing keys
  `compute_time` (`InflatonTrajectory`, `FullInstanton`, `SlowRollInstanton`, and
  `CompactionFunction.metadata` at the top level, the top level being dense only, and under
  `full`/`slow_roll`); and `FullInstanton.diagnostics_json["mean_time_per_picard_iteration"]`.
- No problem is named, and no near miss occurs.
- The independent check (D5) agrees for the dense pair.

**So RH0 is bitwise reproducible in both modes.** `reference` and `resumed` computed every point
independently, `resumed` across a kill and a prune. RH1 and RH2 are held to bitwise equality with
`02-reference.sqlite` and `02-scalars.sqlite` (P4). Their timings and timestamps are set aside.
The first table in build order whose rows differ is none.

### S1 — the `slow` block

`./venv/bin/python -m pytest -m "slow and not integration" -p no:cacheprovider -rA --durations=0`,
run once, after `ray_cluster.sh stop`, with nothing else running. It ran as a background task
writing to the agent's scratch directory, per the orchestrator's correction 2, from 08:18:02 to
08:24:33 BST. The load was 19.08 at the start, falling as the cluster's load decayed, and 4.76 at
the end.

- **69 selected** (810 collected, 741 deselected), **69 passed**, 0 failed, 0 errors, 0 skipped,
  in **390.24 s (6 min 30 s)**. Exit 0.
- By file:
  - `test_picard` 18;
  - `test_sbp_sat_boundary_closure` 16;
  - `test_response_lambda_scaling_prompt23` 11;
  - `test_response_spectrum_prompt23` 10;
  - `test_msr_action` 5;
  - `test_gradient_coupled_instanton_stiffness_instrumentation` 4;
  - `test_gradient_coupled_instanton_end_to_end` 3;
  - `test_gci_parity_scalars` 1;
  - `test_gci_diagnostics_convergence_floor_cli` 1.
  
  These are the nine files and counts of the planning collection.
- **The slowest tests:**
  - `test_picard.py::test_solve_picard_production_case_core_trajectory_converges_across_n`,
    70.36 s;
  - `test_picard.py::test_solve_picard_production_case_converges_for_previously_failing_n[33]`,
    47.45 s;
  - `test_gradient_coupled_instanton_stiffness_instrumentation.py::test_instrument_stiffness_false_gives_bitwise_identical_physics`,
    31.92 s;
  - `test_picard.py::test_solve_picard_fixed_target_bias_is_quantified_and_bounded`, 29.82 s.
- **11 warnings**, all one: `Numerics/OnionCoordinate.py:77: RuntimeWarning: invalid value
  encountered in log`. They come from `test_gci_parity_scalars` (1),
  `test_gradient_coupled_instanton_end_to_end` (3), `..._stiffness_instrumentation` (4) and
  `test_picard` (3). This is a warning, not a failure, and is recorded as the baseline.

Nothing failed, so nothing was re-run and no issue is opened. **09's criterion: the same: 69
passed.**

### The suites (at dispatch, before the cluster; D1)

Both were run by this agent at 07:39–07:40 BST, before the second attempt's cluster. Python has
not changed since but for a docstring.

| Selection | Collected | Result | Time |
|---|---|---|---|
| `./venv/bin/python -m pytest -m "not integration and not slow" -q -p no:cacheprovider` | 680 (130 deselected) | 679 passed, 1 skipped | 24.99 s |
| `RAY_ADDRESS=local ./venv/bin/python -m pytest -m integration -q -p no:cacheprovider` | 61 (749 deselected) | 60 passed, 1 skipped | 12.46 s |

Both equal 01's counts.

### Hygiene

- Stores opened: the four of this attempt, the readers' `before/` copies, and (D5) the second
  attempt's `02-reference.sqlite`. All were opened through the drivers, `compare_stores.py`,
  `stage_counts.py` and `sqlite3` `mode=ro`, each after its build had ended.
- Not opened: no `test-gradient*.sqlite`, nothing under `out-*/`, nothing in
  `02-attempt-1-aborted/`, nothing under `~/ScienceData/ChamPBH-rehearsals/`.
- Nothing was deleted. `ray stop` and `ray start` were never run.

## The deliberate-breakage record

None. This prompt changes no code (README §5 rule 8). Each check above is one a bad build fails:
- a lost or extra row is an A-only or B-only line;
- a science bit is a near miss;
- a missed prune leaves an unvalidated row that the count would show;
- a recomputed instanton shows in the lookup counts.

The independent check was shown able to fail (D5's control).

## Observations not acted on

1. **A `SIGTERM`ed driver's exit status is not fixed:** 134, 15 and 1 at the three attempts, each
   with the same `SIGTERM received` line and absl stack. Recorded for 07 and 11: read the log, not
   the status (D4).
2. **The plot script prints physics warnings from the `Datastore` actors**, e.g.
   `CompactionFunction(id=1, delta_Nstar=0.1): slow-roll instanton is compensated (C_min=-0.0316 < 0).
   Underdense shell present; C_peak threshold criterion may overestimate collapse probability.`
   These are the population code's own diagnostics, on every store, every attempt. They are not
   failures and not this campaign's.
3. **The raylet's `WARNING: 16 PYTHON worker processes have been started … 4x the maximum expected
   startup concurrency (4)`** appeared in `scalars`, once at each of the second and third attempts,
   during the unified pipeline. It is Ray's advisory about workers blocked in `ray.get()`, and is
   harmless here: `scalars-2` did not print it and equals `scalars` bit for bit.
4. **`PIPELINE LOOKUP` reads "0 already computed, 10 to compute, 10 skipped (no instanton
   available)".** The "skipped" items are also counted in "to compute" (`main.py:343-354`: the
   compaction lookup is skipped for them, and they go to the compute list). The wording misleads;
   the counts are right.
5. **The window is about 3 s wide at four CPUs.** `FullInstanton` rows are stored over about 3 s,
   9.8 s after the banner. The roughly 10 s offset is the driver's serial minting of each
   instanton's `efold_value` grid (about 0.75 s each), not the solves.

## State handed to the next prompt

- **RH0 holds, and is bitwise reproducible in both modes.** RH1 (07) and RH2 (11) are held to
  bitwise equality, timings and timestamps aside, with `02-reference.sqlite` (dense) and
  `02-scalars.sqlite` (scalars-only), under `~/ScienceData/StochasticInstantons-rehearsals/dk-and-rpk-migration/`.
- **Mind the readers' row.**
  - `02-scalars.sqlite` and `02-resumed.sqlite` now carry the `version` `2026.3.0` row the
    readers wrote. `02-reference.sqlite` and `02-scalars-2.sqlite` do not.
  - A comparison with the scalars-only baseline should use `02-readers/scalars/before/02-scalars.sqlite`,
    or `02-scalars-2.sqlite`, or account for that row.
  - Likewise, if 07/11 compare after their own readers, their read stores carry the row (D3).
- **`scalar_data.csv`**, for the byte comparison at 07 and 11:
  `b0564eecc22f9106dcccb57fd1a419749543c4b9d15dc0ffe7a8e0780e9058a2` on both `resumed` and
  `scalars`.
- **L4's pattern:** the open prunes only unvalidated rows (here 2 `FullInstanton`, with their
  3,474 value rows); the resume computes only what was not kept (STAGE 2 6 + 4); and the counts
  add up to `reference`'s (10 / 10 / 10 / 1).
- **The schema snapshot of the start tree** is `out/02-reference-schema.json`, 30 tables. 05, 06
  and 09 compare with it.
- **S1 baseline for 09:** `-m "slow and not integration"` selects 69 of 810; 69 passed, no skip, 390 s on an idle machine; 11 warnings, all `Numerics/OnionCoordinate.py:77` `RuntimeWarning: invalid value encountered in log`.
- **The protocol, as run:**
  - `S` comes from `reference`'s stored timestamps and its profile database's lookup calls (the
    banner's time). The `FullInstanton` rows fell at banner +9.8 to +12.8 s; `S` = 11.0 s left 6
    validated and 2 unvalidated.
  - A `SIGTERM`ed driver may exit 134, 15 or 1.
  - The prune reports reached the driver's log undeduplicated: two actors, two lines.
  - `ray_cluster.sh` start took 7 s and stop 18 s.
- **Suites:** default 680 (679 passed, 1 skipped); integration 61 (60 passed, 1 skipped).
- **No issue opened;** `.documents/OPEN-ISSUES.md` is unchanged. No SI cluster is running, and
  the lock is free.
