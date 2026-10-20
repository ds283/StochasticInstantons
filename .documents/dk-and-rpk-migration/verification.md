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
