# 11 — rehearse through both packages (RH2)

**Subject:** Rehearse 10b's tree through `datastorekit` `v0.5.0` and `raypoolkit` `v0.2.0` (RH2), compare it bit
for bit with RH1 (and so RH0), run the store-hygiene tools, and record DatastoreKit's G4
**Commit:** this commit, on branch `dk-and-rpk-migration`, on top of `66b1c81`
**Date:** 2026-10-22, 21:26–21:36 BST (gate to cluster stop), by Claude Opus 5.5
**Result:** **COMPLETE.** L1–L4 (RH2), V3 and H1 hold; gate **RH2** holds and **DatastoreKit G4 holds**.
- **RH2 equals RH1, and so RH0, bit for bit in both modes.** All six comparisons of prompt §1.4.1–§1.4.4 give
  `RESULT: equal`, exit 0. Every row of all 30 tables matched; only timestamps and the JSON timing keys differ.
- The schema is RH1's: `11-reference-schema.json` differs from `07-reference-schema.json` (and from 09's
  `09-temp-schema.json`) in its `source` line alone, and `--schema` of `11-reference` and `11-scalars` against RH1's
  snapshot gives "the schemas agree".
- `resumed-a` fell inside the narrow window **at the first attempt** (`S` = 12.0 s): 4 `FullInstanton` validated, 2
  not. `resumed-b`'s open, through the package's actors calling SI's hook, pruned exactly those 2, in RH1's text,
  and the build computed the other 6. No replicated write was left in flight, so the package's reconciliation at
  open had nothing to do and printed nothing.
- `stage_counts.py` parsed every log unchanged; `reference`'s and `scalars`' records equal RH1's, less `packages`.
- Both `scalar_data.csv` hash to `b0564eec…58a2`; `--inventory` reports `problems: none` on both stores, with
  RH1's values and counts.
- H1: `shard_key_audit` `VERDICT: OK` on all three stores; the `sharded_store copy` read back with no problem,
  compared equal, and was deleted by `delete_store`, nothing left.
- No code changed and no issue is opened. No SI cluster is left running, and the lock is free.

Prompt: [`.prompts/dk-and-rpk-migration/11-rehearse-through-both-packages.md`](../../.prompts/dk-and-rpk-migration/11-rehearse-through-both-packages.md).
The orchestrator's brief for 11 governed where it corrected the prompt; its seventeen corrections were applied as
stated (below). The record of the rehearsal is [`verification.md`](verification.md) §3. The outputs kept are in
[`out/`](out/), as `11-*`. Scratch scripts and their outputs stayed in the session scratchpad (`a11/`); the two that
support claims here are reproduced below.

## How the run went

One sitting, no stop. The user had been asked, at dispatch, to have other sessions hold their suites, builds and
Ray jobs until RH2 was done, and had agreed (the orchestrator's brief).
1. **21:26:34 BST: the gate**, all checks passing (below). No foreign suite or Ray job: `pgrep -fl` for `pytest`,
   `unittest`, `main.py`, `gcs_server`, `raylet`, `ray::` and `/tmp/ray` found nothing. Load 9.05 / 12.84 / 22.65 on
   10 CPUs, desktop apps only.
2. **21:27–21:28: RH1's baseline check and the two suites**, serially, in the foreground, before the cluster.
3. **21:29:01: the cluster**, then the four builds (21:29:10–21:32:50), the comparisons, the hygiene tools and the
   readers (to 21:35:18), and the stop (21:35:35–21:35:54).

No foreign suite or Ray job ran at any point; the processes at the two load peaks (57 during `resumed-b`, 80 during
the scalars readers) were the builds' own workers and desktop processes (WindowServer, ChronoSync, Tower,
`softwareupdated`, `loginwindow`).

## What shipped

- **[`verification.md`](verification.md) §3 RH2**, appended after §2.7. Its introduction, §1 and §2 are not
  touched.
- **[`out/`](out/) `11-*`**, small text only:
  - the seven comparisons, each `.txt` and `.json`: `11-compare-reference-resumed`,
    `11-compare-07reference-11reference`, `11-compare-07reference-11resumed`,
    `11-compare-07scalarsbefore-11scalars`, `11-compare-02scalars2-11scalars`,
    `11-compare-02reference-11reference` and `11-compare-reference-copy` (H1);
  - `11-reference-schema.json`: the schema snapshot, 30 tables;
  - `11-stage-counts.txt`, `.json`: `stage_counts.py` on the four logs;
  - `11-h1-audit.txt`, `11-h1-copy.txt`, `11-h1-readback.txt`, `11-h1-delete.txt`: H1;
  - `11-readers-{resumed,scalars}-{status.txt,inventory.log,compare_stores.txt,scalar_data.csv}`. The inventory
    logs are whole: `--inventory` now runs before Ray, so they hold no raylet line to drop;
  - `11-scalar_data.sha256`.
- **The board:** the §1 row for 11; L1–L4 (RH2) (its "at 10's tree" corrected to 10b's, on `v0.5.0`), V3 and H1;
  a new §2 row for gate RH2; the DatastoreKit G4 row; §5.28; and the header.
- No code, script, tool or test changed. Nothing was installed. `.documents/OPEN-ISSUES.md` is unchanged (59 open,
  29 closed). The README and `.prompts/INDEX.md` are the orchestrator's.

## The orchestrator's corrections, as applied

1. **The board.** The section is `### 5.28 After prompt 11 (2026-10-22)`, after §5.27; the header's status line
   is updated. The §1 row (`:77`) and the items (`:173-175`) are filled in; the L1–L4 (RH2) row's stale "at 10's
   tree" now reads 10b's tree, on `v0.5.0`. A §2 row for gate RH2 is added after RH1's, in its form. The G4 row
   (`:195`) is marked, acceptance 1–5 having held. `.prompts/INDEX.md` and the list of orchestrator notes are left
   to the review.
2. **The suites** were run as given, serially, in the foreground, before `ray_cluster.sh start`: 732 (731 passed, 1
   skipped) and 67 (66 passed, 1 skipped), 10b's counts. No `slow` block.
3. **The provenance line** is the one given, once in each of the four build logs and in each reader's log
   (below). Both packages `editable: False` at the gate.
4. **The prune report** is RH1's text, printed by the package's actors (below). Ray did not mark it repeated; it
   was also read in both actors' own logs under `/tmp/ray-si/session_2026-10-22_21-29-03_242377_72080/logs/`
   before the stop. `stage_counts.py` found both reports.
5. **Between `resumed-a` and `resumed-b`**, read `mode=ro`: the primary's `replication_in_flight` (0 rows; its
   columns `operation`, `class_name`, `controller_shard`, `store_id`, `started`); no `-journal`, `-wal` or `-shm`
   file anywhere in the rehearsal root; `efold_value` 7,521 rows on each of the ten shards. `resumed-b`'s log has
   no `>>` line between the provenance line and `>> Opened existing sharded datastore …`: no record was left, so
   nothing was reconciled.
6. **`S`** was measured from `11-reference` with 07's `rows.py` (extended by correction 5's three reads) and the
   profile database; on a loaded machine it was set late in the window. One attempt sufficed.
7. **`--json OUT`**: every `stage_counts.py` and `compare_stores.py` call names its output file right after
   `--json`, under `out/`. No log or store path follows `--json` anywhere (the commands, below).
8. **The comparisons' file names** are the brief's, each `.txt` and `.json`, each exit code recorded.
9. **H1** as the brief's prototype, after the comparisons and before the readers; its outputs are
   `out/11-h1-*.txt`. `11-reference-profile.sqlite` was not copied (the copy tool copies the primary and its shards
   only).
10. **The readers' outputs** are kept under 07's names with `11-`. The two CSVs are staged with
    `git -c core.autocrlf=false add -f`, and their staged blobs' hashes checked (Verification).
11. **The inventory against RH1's** is compared field by field (below); the text differs by design.
12. **The profile database** is recorded beside RH1's, each difference described (below).
13. **G4.** The board's G4 row records the layer deleted at 09 (`f4da58f`), the pin `v0.5.0` installed at 10a
    (`80d99a7`; `v0.4.0` at 08, `1b1ca6d`), the suites, and RH2 equal to RH1. The text for DatastoreKit's board is in
    "State handed to the next prompt".
14. **`verification.md`** §3 RH2 is appended after §2.7, in §2's form.
15. **`.documents/OPEN-ISSUES.md`** is untouched: no issue opened.
16. **Other sessions.** Checked at the start (none) and again before the cluster (none); none seen while it was up.
17. **The disk.** 20 GB free (98%) at the gate; the raylet printed its "over 95% full, available space: 18.2 GB"
    line in every build, as expected. Ray refused nothing.

## Deviations from the prompt

- **D1: the first hygiene snapshot of the rehearsal root ran GNU `stat -f` by mistake.**
  - The shell's `stat` is GNU coreutils (`/opt/local/libexec/gnubin/stat`), whose `-f` reports the file system
    rather than formatting the file's own fields. `find $R -exec stat -f "%m %z %N" {} +` therefore ran `statfs`
    over every entry of the rehearsal root, RH0's earlier attempts' directories included.
  - It reads metadata only: nothing was opened as a file or a database and nothing was written. The snapshot was
    taken again at once with `/usr/bin/stat`, and that is the one compared after the stop (Hygiene).
  - **UNINTENDED DRIFT** (harmless).
- **D2: RH1's profile database read `mode=ro`.** `07-reference-profile.sqlite` was read with `sqlite3` `mode=ro`
  to describe the per-method counts by object and by actor (correction 12), as 07's D6 read RH0's. It is one of
  RH1's files, read as its baselines are. **IMPLEMENTATION CHOICE.**
- **D3: `rows.py` extended, and L4's control taken within 11.** 07's `rows.py` gained correction 5's three reads
  (replication records, journals including `-shm`, `efold_value` per shard) and reads nothing else new.
  `l4_compare.py` is 07's with its paths changed; its control compares RH1's `reference` with RH2's `resumed-b` (the
  brief's control), where 07's compared RH0's `reference` with RH1's `resumed-b`. **IMPLEMENTATION CHOICE.**

`resumed-a`'s exit status 15 is within the prompt's 134, 15 or 1, and is not a deviation.

## Verification performed

### The gate (2026-10-22, 21:26 BST)

- Branch `dk-and-rpk-migration`, `HEAD` `66b1c81`, clean; `git diff --cached` empty.
- `git diff --stat 19716cd HEAD -- . ':!.prompts' ':!.documents'`: empty.
- `git diff 5868231 HEAD -- .documents/dk-and-rpk-migration/rehearsal/ tools/compare_stores.py`: 0 bytes.
- `ray_cluster.sh status`: the lock free, no `/tmp/ray-si` process, ports 6390, 6391, 8266 and 52366 free.
  `RAY_ADDRESS` unset. No `pytest`, `unittest`, `main.py`, `gcs_server`, `raylet` or `ray::` process.
- `utilities.installed_package_provenance()`: `datastorekit` 0.5.0, `https://github.com/ds283/DatastoreKit`,
  commit `f47b9a255e9ad58e0d0eaf85644f53b575884d31`, requested `v0.5.0`, `editable` False; `raypoolkit` 0.2.0,
  `https://github.com/ds283/RayPoolKit`, commit `eaef0ce60e2fc354bb32f0ad576010e6a83c1976`, requested `v0.2.0`,
  `editable` False. `format_package_provenance` gives correction 3's line exactly. `pip freeze` 83 lines, with the
  two `@ git+…` lines at those commits.
- RH1's `07-reference`, `07-readers/resumed/before/07-resumed`, `07-readers/scalars/before/07-scalars` and RH0's
  `02-reference`, `02-scalars-2`: each a primary and ten shards. **No `11-*` file existed.**
- DatastoreKit `2900d82`, RayPoolKit `17029d9`, both clean (read only).
- Load 9.05 / 12.84 / 22.65 at 21:26 on 10 CPUs. Disk 20 GB free (98%).

### RH1's baseline check (before the cluster)

```bash
./venv/bin/python tools/compare_stores.py $R/07-reference.sqlite $R/07-readers/resumed/before/07-resumed.sqlite
./venv/bin/python tools/compare_stores.py $R/07-readers/scalars/before/07-scalars.sqlite $R/02-scalars-2.sqlite
```

Both gave `RESULT: equal`, exit 0. **RH1's stores have not moved.**

### The suites (before the cluster)

| Selection | Result | Time | Load at start |
|---|---|---|---|
| `./venv/bin/python -m pytest -m "not integration and not slow" -q -p no:cacheprovider` | **732**: 731 passed, 1 skipped, 136 deselected, 10 warnings | 41.11 s (21:27:15–21:28:00) | 8.64 |
| `RAY_ADDRESS=local ./venv/bin/python -m pytest -m integration -q -p no:cacheprovider` | **67**: 66 passed, 1 skipped, 801 deselected, 1 warning | 47.91 s (21:28:05–21:28:54) | 12.80 |

Both equal 10b's counts. No `pytest` or Ray process was left after the integration run.

### The cluster

- `ray_cluster.sh start "dk-and-rpk-migration 11 (RH2)"` at 21:29:01 BST, at a load of 31.90 / 17.67 / 22.87 (the
  integration suite had just ended). "started in 5s; gcs_server pid 72107".
- Address `127.0.0.1:6390`; actor line `./venv/bin/ray list actors --address 127.0.0.1:6390`. The lock's owner
  file: `project: StochasticInstantons`, `purpose: dk-and-rpk-migration 11 (RH2)`, `acquired:
  2026-10-22T21:29:07+01:00`, `ray_temp_dir: /tmp/ray-si`, `ray_address: 127.0.0.1:6390`, `pid: 72107`.
- `ray_cluster.sh stop` at 21:35:35: `SIGTERM` to 18 processes, `SIGKILL` to 72107 and 72108 after the 15 s grace;
  "no process names /tmp/ray-si; ports 6390 6391 8266 52366 are free"; "released the rehearsal lock"; "stopped in
  19s". `status` afterwards: the lock free, no SI process, the four ports free.

### The builds

All times BST. The load is the 1-minute average at the build's start.

| Build | Command | Start | End | Wall | Load | Exit |
|---|---|---|---|---|---|---|
| `reference` | `build.sh 11 reference reference 127.0.0.1:6390 dense --profile-db` | 21:29:10 | 21:29:50 | 40 s | 32.10 | 0 |
| `resumed-a` | `build.sh 11 resumed resumed-a 127.0.0.1:6390 dense` | 21:30:24 | 21:30:53 | 29 s | 55.73 | 15 (`SIGTERM`; in the window) |
| `resumed-b` | `build.sh 11 resumed resumed-b 127.0.0.1:6390 dense` | 21:31:30 | 21:31:58 | 28 s | 57.30 | 0 |
| `scalars` | `build.sh 11 scalars scalars 127.0.0.1:6390 scalars` | 21:32:17 | 21:32:50 | 33 s | 53.23 | 0 |

`reference`'s stages took 6.04 s, 12.9 s, 9.59 s and 2.27 s; RH1's took 5.47, 12.1, 8.76 and 1.61 (RH0's 5.84,
12.8, 8.77, 1.68). The 45-minute limit (P1) is far off. `scalars`' unified pipeline took 18.4 s.

### `S`, and how it was chosen

From the closed `11-reference.sqlite`, read with `sqlite3` `mode=ro` by `rows.py` (below), and from its profile
database. Times are the stores' naive local time, BST.
- The trajectory was stored at 21:29:20.994. Under the package a replicated row carries one timestamp on every
  shard, so all ten replicas share it.
- The profile database's ten `object_get {'object': 'FullInstanton', 'type': 'vector'}` calls, the `STAGE 2`
  lookup, ran at 21:29:21.865–21:29:21.875. So the `STAGE 2: FULL MSR INSTANTONS LOOKUP:` banner, which
  `interrupt_when.py` matches first, was at about **21:29:21.87**. The labels are RH1's, as the brief said.
- The ten `object_get FullInstanton scalar` calls followed from 21:29:23.55, about 0.8 s apart. The last
  `efold_value` row was minted at 21:29:30.621, banner **+8.76 s** (RH1: +9.41).
- `FullInstanton` rows were stored at 31.629, 31.648, 31.710, 32.748, 32.776, 33.180, 33.422, 33.443, 34.165 and
  34.756: banner **+9.76, +9.78, +9.85, +10.88, +10.91, +11.32, +11.56, +11.58, +12.30 and +12.89 s**, a window of
  3.1 s (RH1's +9.49 to +12.07, 2.6 s).
- `SlowRollInstanton` rows were stored at 21:29:43.76–44.32; `CompactionFunction` rows at 21:29:46.90–48.19,
  banner +26.3 s, the end of the wide window.

**`S` = 12.0 s, at the first attempt.** The load was 64 at 21:30, falling from `reference`'s own peak. At
`reference`'s pace 12.0 s falls between the eighth row (+11.58) and the ninth (+12.30); it stays inside the narrow
window for a driver up to about 7% faster or about 23% slower than `reference`. RH1's first attempt fell before the
window because a loaded driver ran slow, so the brief's "aim later" was taken.

What happened (BST; the script prints UTC):
- the trajectory was stored at 21:30:38.421; the script saw the banner in the second 20:30:39 UTC;
- the last `efold_value` row was minted at 21:30:49.006, about banner +9.4 s: about 0.6 s behind `reference`;
- `FullInstanton` rows were stored from 21:30:50.012 to 21:30:51.590;
- the script sent the signal at 20:30:51 UTC, and the driver logged `*** SIGTERM received at time=1792701051 ***`
  at 21:30:51.666, 76 ms after the last row.

**The signal fell inside the narrow window**: some `FullInstanton` rows stored and validated, others stored and not
validated, others not stored.

The `interrupt_when.py` output:

```text
[2026-10-22T20:30:26+00:00] interrupt_when: waiting for "STAGE 2: FULL MSR INSTANTONS" in /Users/ds283/ScienceData/StochasticInstantons-rehearsals/dk-and-rpk-migration/logs/11-resumed-a.log; then 12 s; then SIGTERM
[2026-10-22T20:30:26+00:00] interrupt_when: driver pid 73409 (from /Users/ds283/ScienceData/StochasticInstantons-rehearsals/dk-and-rpk-migration/logs/11-resumed-a.pid)
[2026-10-22T20:30:39+00:00] interrupt_when: saw "STAGE 2: FULL MSR INSTANTONS"; waiting 12 s
[2026-10-22T20:30:51+00:00] interrupt_when: sent SIGTERM to pid 73409
```

It exited 0. Pid 73409 is the one `build.sh` wrote to `11-resumed-a.pid`.

### The rows `resumed-a` left (read `mode=ro` after the build ended)

| Table | Validated | Not validated | Child rows (validated parent / not) |
|---|---|---|---|
| `InflatonTrajectory` | 1 (replicated: 10 rows over 10 shards) | 0 | `InflatonTrajectoryValue` 57,130 / 0 |
| `FullInstanton` | **4** (δN★ 0.42222 `shard0000` serial 1; 0.1 `shard0009` 21; 1.0667 `shard0002` 41; 1.7111 `shard0004` 61) | **2** (δN★ 2.0333 on `shard0005`, serial 81, 1,705 value rows; δN★ 1.3889 on `shard0003`, serial 101, 1,640) | `FullInstantonValue` 6,336 / **3,345** |
| `SlowRollInstanton` | 0 | 0 | — |
| `CompactionFunction` | 0 | 0 | — |

- δN★ 0.74444, 2.3556, 2.6778 and 3.0 were not stored.
- The two unvalidated rows were stored at 21:30:51.222 and 21:30:51.590, 444 ms and 76 ms before the signal.
- **The primary's `replication_in_flight`: 0 rows** (columns `operation`, `class_name`, `controller_shard`,
  `store_id`, `started`).
- **No `-journal`, `-wal` or `-shm` file** beside the primary or any shard (nor anywhere in the rehearsal root).
- **`efold_value`: 7,521 rows on each of the ten shards**, every shard's newest row stamped 21:30:49.006: the
  replicated table is whole on every shard.
- No child row of any of the four tables is orphaned.

So the signal fell after the last replicated write of the run (the tenth grid's minting, 2.7 s earlier), in the
middle of sharded writes: no replicated write was in flight.

**The actor check** at 21:31:00, 9 s after the signal:
- `./venv/bin/ray list actors --address 127.0.0.1:6390 --filter "state=ALIVE"` gave "No resource in the cluster";
- the full listing (`--limit 1000`, 23 actors) shows all 11 actors of job `02000000` (10 `Datastore`
  `shard0000-store`…`shard0009-store`, 1 `SerialPoolBroker`) `DEAD`, and job `01000000`'s 12 (`reference`, with
  its `ProfileAgent`) `DEAD` too.

### L1 — every build ends as it should

- `reference`, `resumed-b` and `scalars` end with `** driver exit status 0`. Their pools print
  `ALL WORK ITEMS COMPLETE` **4, 4 and 2** times, as RH1's did.
- `resumed-a` ends by the signal: its log has `*** SIGTERM received at time=1792701051 ***` (twice, the second
  from `logging.cc`) and the absl stack, with its PC in `memo_get` under `_pickle_Pickler_dump` and the main thread
  in `CoreWorker.submit_actor_task` (pickling an actor call's arguments). Exit 15: Ray's driver handler turns
  `SIGTERM` into `sys.exit(15)`, as ChamPBH's R2 saw; RH1's attempts gave 15 and 1. The stage is `INCOMPLETE`,
  with 1 `ALL WORK ITEMS COMPLETE` (STAGE 1's).
- **No traceback in any log.** Every line matching `Traceback`, `Error`, `WARNING` or `Warning` was read:
  - Ray's start-up `FutureWarning` (accelerator visible devices), once in every log;
  - the raylet's disk line, `/tmp/ray-si/session_2026-10-22_21-29-03_242377_72080 is over 95% full, available
    space: 18.2198 GB; capacity: 926.352 GB. Object creation will fail if spilling is required.`, an `E` line of
    `file_system_monitor.cc`, about every 10 s in every build (it does not match the patterns; it is named
    because the brief names it);
  - `resumed-b`'s two `!! INTEGRITY WARNING` headers (L2).

  No `did not validate` line. The raylet's `16 PYTHON worker processes` advisory that RH1's `scalars` printed did
  not appear in RH2's.
- **The provenance line** appears once in each of the four build logs, identically, and as line 1 of each
  reader's `1-inventory.log` and `2-plot_InstantonSolutions.log`:

  ```text
  >> packages: datastorekit 0.5.0 (https://github.com/ds283/DatastoreKit@f47b9a255e9ad58e0d0eaf85644f53b575884d31, requested v0.5.0); raypoolkit 0.2.0 (https://github.com/ds283/RayPoolKit@eaef0ce60e2fc354bb32f0ad576010e6a83c1976, requested v0.2.0)
  ```

  This is the prompt's line, correction 3's, and the one 10a's results note gives ("State handed to the next
  prompt"). It names both packages at their tags' commits, requested `v0.5.0` and `v0.2.0`; neither is marked
  editable, and provenance gives `editable: False` for both.

### L2 — the resume

- **`resumed-b`'s open.** Between the provenance line and `>> Opened existing sharded datastore
  "…/11-resumed.sqlite" with 10 shards`, the log holds only Ray's two connection lines and the `FutureWarning`: **no
  `>>` line of the package's reconciliation** (no `Rolled back the journal`, no `opened with a replicated write in
  flight`), and no replicated prune (`… pruned by the pool under a "prune" record`). That agrees with the 0
  `replication_in_flight` rows and the validated trajectory read between the builds.
- **The prune.** Every `>>` and `!!` line of `resumed-b`'s open, verbatim (ANSI colour codes removed):

  ```text
  >> Opened existing sharded datastore "/Users/ds283/ScienceData/StochasticInstantons-rehearsals/dk-and-rpk-migration/11-resumed.sqlite" with 10 shards
  (Datastore pid=74512) !! INTEGRITY WARNING (2026-10-22T21:31:34): datastore "shard0003-store" (physical file /Users/ds283/ScienceData/StochasticInstantons-rehearsals/dk-and-rpk-migration/11-resumed-shard0003.sqlite)
  (Datastore pid=74512) Pruned 1 unvalidated FullInstanton records
  ```

  and, forwarded by Ray only at the end of the log (after `** Skipping gradient branch …`), the second actor's
  report, stamped with the same second:

  ```text
  (Datastore pid=74514) !! INTEGRITY WARNING (2026-10-22T21:31:34): datastore "shard0005-store" (physical file /Users/ds283/ScienceData/StochasticInstantons-rehearsals/dk-and-rpk-migration/11-resumed-shard0005.sqlite)
  (Datastore pid=74514) Pruned 1 unvalidated FullInstanton records
  ```

  - **The package printed the report exactly as RH1's layer did** (07's: `!! INTEGRITY WARNING (…): datastore
    "shard0004-store" (physical file …)`, then `Pruned 1 unvalidated FullInstanton records`): the header is the
    package's actor's, the second line SI's hook's. Ray did not mark either as repeated.
  - Both actors' own logs, read before the stop, hold the same two lines each:
    `worker-2016711f…-03000000-74512.out` (lines 3–4) and `worker-5538eb42…-03000000-74514.out` (lines 3–4). No
    other worker log of the session mentions a prune.
  - **`stage_counts.py` finds both** (`integrity: Pruned 1 unvalidated FullInstanton records`, twice), the second
    one despite its place in the log.
  - The total pruned, 2, equals the unvalidated count read between the builds, on the same shards
    (`shard0003`, `shard0005`), so **only unvalidated rows were pruned.**
  - The cascade took their 3,345 value rows. After `resumed-b`, `mode=ro`: 10 `FullInstanton`, all validated, with
    16,564 value rows; no orphan in any of the four child tables; `replication_in_flight` 0 rows; `efold_value`
    7,521 on each shard. The four kept rows keep their `resumed-a` timestamps (21:30:50.01–51.19). The six
    recomputed (δN★ 1.3889 `shard0003` serial 62; 0.74444 `shard0001` 82; 2.0333 `shard0005` 102; 2.3556
    `shard0006` 128; 2.6778 `shard0007` 142; 3.0 `shard0008` 162) are stamped 21:31:42.79–44.20. The pruned
    serials (81, 101) were not reused.
- **`resumed-b` computed only what `resumed-a` had not kept:**
  - STAGE 1: 0 computed, "(no compute items were evaluated - all assets read from datastore)";
  - STAGE 2: lookup "4 already computed, 6 to compute", then 6 computed;
  - STAGES 3 and 4: 10 each.

  `resumed-a`'s 4 kept and `resumed-b`'s 6 make `reference`'s 10. The 2 pruned were recomputed; none kept validated
  was.
- `11-reference` against `11-resumed`: `RESULT: equal`, exit 0 (§4.3 below).

### §4.3 — equal to RH1, and so RH0, bit for bit

All runs are `./venv/bin/python tools/compare_stores.py A B --json out/11-compare-<a>-<b>.json`, the text
redirected to the `.txt` beside it. They ran **before the readers**, against the baselines without a readers'
row: `07-reference.sqlite` (dense) and `07-readers/scalars/before/07-scalars.sqlite` / `02-scalars-2.sqlite`
(scalars-only). Each JSON names both paths.

| A | B | Exit | `RESULT:` | Tables | A only / B only |
|---|---|---|---|---|---|
| `$R/11-reference.sqlite` | `$R/11-resumed.sqlite` | **0** | **equal** | 30 | 0 / 0 |
| `$R/07-reference.sqlite` | `$R/11-reference.sqlite` | **0** | **equal** | 30 | 0 / 0 |
| `$R/07-reference.sqlite` | `$R/11-resumed.sqlite` | **0** | **equal** | 30 | 0 / 0 |
| `$R/07-readers/scalars/before/07-scalars.sqlite` | `$R/11-scalars.sqlite` | **0** | **equal** | 30 | 0 / 0 |
| `$R/02-scalars-2.sqlite` | `$R/11-scalars.sqlite` | **0** | **equal** | 30 | 0 / 0 |
| `$R/02-reference.sqlite` | `$R/11-reference.sqlite` | **0** | **equal** | 30 | 0 / 0 |

**Table by table**, the matched rows in each comparison against RH1's (07's results note, "§4.3"):

| Table | Dense: RH1 | Dense: RH2 (each of the four dense comparisons) | Scalars-only: RH1 | Scalars-only: RH2 (both) |
|---|---|---|---|---|
| `CompactionFunction` | 10 | 10 | 10 | 10 |
| `CompactionFunctionSamples` | 33,128 | 33,128 | 0 | 0 |
| `FullInstanton` | 10 | 10 | 10 | 10 |
| `FullInstantonValue` | 16,564 | 16,564 | 0 | 0 |
| `SlowRollInstanton` | 10 | 10 | 10 | 10 |
| `SlowRollInstantonValue` | 16,564 | 16,564 | 0 | 0 |
| `InflatonTrajectory` | 1 | 1 | 1 | 1 |
| `InflatonTrajectoryValue` | 5,713 | 5,713 | 5,713 | 5,713 |
| `efold_value` | 7,521 | 7,521 | 7,521 | 7,521 |
| `delta_Nstar` | 10 | 10 | 10 | 10 |
| `CosmologicalParams`, `MasslessDecoupledDiffusion`, `N_final`, `N_init`, `QuadraticPotential`, `alpha_regularization`, `inflaton_mass`, `n_collocation_points`, `phi_value`, `pi_value`, `tolerance`, `version` | 1 each | 1 each | 1 each | 1 each |
| `GradientCoupledInstanton`, `…Profile`, `…Value`, `IntegrationSolver`, `QuarticPotential`, `quartic_coupling`, `redshift`, `store_tag` | 0 each | 0 each | 0 each | 0 each |

(`compare_stores` counts a replicated table's rows once, after checking every shard's copy equal to the others';
read `mode=ro` per shard, `InflatonTrajectoryValue` is 57,130 rows over the ten shards in each RH2 store, and
`efold_value` 7,521 on each shard.)

- In every comparison, every row of every table matched. Nothing is A-only or B-only, no near miss, and
  `problems: none`.
- The one note, as at RH0 and RH1: `redshift is on the shards but in neither of the primary's table lists;
  compared as sharded`, for A and for B.
- **Bookkeeping only** differs between matched rows: every `timestamp` (of the 24 tables with rows other than
  `version`), and the JSON timing keys: `compute_time` in `InflatonTrajectory`, `FullInstanton` and
  `SlowRollInstanton` `diagnostics_json`; `compute_time` in `CompactionFunction.metadata` at the top level (dense
  only) and under `full` and `slow_roll`; `FullInstanton.diagnostics_json["mean_time_per_picard_iteration"]`.
- The four dense comparisons' texts are identical below their two header lines (`diff` empty), and so are the two
  scalars-only comparisons'.
- `version` is matched, 1 row each: no reader had touched any store compared.
- **The first table in build order whose rows differ is none.** RH2's three stores equal RH1's of the same mode,
  and through them RH0's, bit for bit.

**The schema.**
- `--snapshot $R/11-reference.sqlite --out out/11-reference-schema.json`: 30 tables, 2,482 lines. It differs from
  `out/07-reference-schema.json`, and from `out/09-temp-schema.json`, in its `source` line alone.
- `--schema $R/11-reference.sqlite --against out/07-reference-schema.json` and `--schema $R/11-scalars.sqlite
  --against` the same file: "RESULT: the schemas agree", exit 0, both. No difference needed listing against 09's
  snapshot: the snapshot compares columns as sets, so the package's column order does not show.

### L3 — the readers

`run_readers.sh 11 resumed 127.0.0.1:6390` ran 21:34:10–21:34:42 (load 44.66), then `run_readers.sh 11 scalars
127.0.0.1:6390` ran 21:34:51–21:35:18 (load 80.35), each as a background task, after H1. Both exited 1, as the
script does by design when step 4 finds the expected row.
- **`status.txt`, both stores:** step 0 `copy-before` exit 0, step 1 `inventory` exit 0, step 2
  `plot_InstantonSolutions` exit 0, step 4 `compare_stores` exit 1. Step 3 is printed as not run (U11).
- **`4-compare_stores.log`, both stores:**
  - exactly one table differs, `version`, `B only 1`, `version{label='2026.3.0'}`;
  - "bookkeeping that differs between matched rows": none;
  - problems: none (the `redshift` notes as above).

  Each plot log reads `n_collocation_points: 1 value = [ 5 ]`. Each carries two of the `Datastore` actors' physics
  warnings `!! WARNING: CompactionFunction(…): slow-roll instanton is compensated (C_min=… < 0) …`, as RH1's did;
  they are not failures. No traceback.
- **`scalar_data.csv`:**
  - on `resumed`: `b0564eecc22f9106dcccb57fd1a419749543c4b9d15dc0ffe7a8e0780e9058a2`;
  - on `scalars` (with `--no-store-values`): `b0564eecc22f9106dcccb57fd1a419749543c4b9d15dc0ffe7a8e0780e9058a2`.

  Both have 11 lines and 3,592 bytes; `cmp` against `out/07-readers-resumed-scalar_data.csv` is silent. RH0's and
  RH1's byte for byte; no `diff` was needed. The staged blobs' hashes are below.
- **What `--inventory` printed** (step 1, read-only, before Ray: no Ray line in either log), field by field against
  RH1's (`out/07-readers-resumed-inventory.log`). The layout is 10's with 10b's counts, so the text differs by
  design; the content:

  | Field | RH1 (`07-resumed`) | RH2 `11-resumed` | RH2 `11-scalars` |
  |---|---|---|---|
  | problems | (not reported by the old layer) | `problems: none` | `problems: none` |
  | store | — | read-only; 10 shards; 7,574 records in 24 classes | the same |
  | δN★ | 10: `[ 0.1, 0.422222, …, 2.67778, 3 ]` | the same 10 | the same 10 |
  | N_init / N_final | `[ 20 ]` / `[ 5 ]` | the same | the same |
  | φ₀ / π₀ | `[ 15 PlanckMass ]` / `[ 0 PlanckMass ]` | the same | the same |
  | m | `[ 1e-05 PlanckMass ]` | the same | the same |
  | quartic couplings | no values committed | the same | the same |
  | e-fold samples | 7521: `[ 0, 0.01, 0.0100003, … 57.112, 57.122 ]` | 7,521, the same first and last ten | the same |
  | trajectories | 1 validated / 0 unvalidated | 1 validated / 0 (5,713 value rows) | the same |
  | Full MSR | 10 / 0 | 10 / 0 (16,564 value rows) | 10 / 0 (0 value rows) |
  | slow-roll | 10 / 0 | 10 / 0 (16,564) | 10 / 0 (0) |
  | compaction | 10 / 0 | 10 / 0 (33,128) | 10 / 0 (0) |
  | gradient-coupled | 0 / 0 | 0 records, 0 / 0 | the same |
  | further classes (10's) | — | `QuadraticPotential` m=1e-05; `QuarticPotential` none; `MasslessDecoupledDiffusion` 1; `n_collocation_points` `[ 5 ]`; `alpha_regularization` `[ 0.01 ]`; `tolerance` `[ 1e-08 ]`; `CosmologicalParams` Planck2018; `redshift`, `IntegrationSolver`, `store_tag` none; `version` `[ 2026.6.1 ]` | the same |

  The two RH2 logs differ only in the stores' names, the commit times and the value-row counts of the three
  scalars-only tables (0 on `scalars`).

### L4 — against RH1

`stage_counts.py` on the four logs (`out/11-stage-counts.txt`, `.json`) parsed every log unchanged: banners,
lookups, `ALL WORK ITEMS COMPLETE`, `Queue summary:`, the no-compute line and both integrity reports.

| Stage | `reference` | `resumed-a` | `resumed-b` | `scalars` |
|---|---|---|---|---|
| `STAGE 1: BACKGROUND INFLATIONARY TRAJECTORIES` | 1 computed | 1 computed | 0, no compute items evaluated | 1 computed |
| `STAGE 2: FULL MSR INSTANTONS` lookup, then pool | 0 / 10; 10 | 0 / 10; INCOMPLETE (signal) | 4 / 6; 6 | — |
| `STAGE 3: SLOW-ROLL INSTANTONS` | 0 / 10; 10 | — | 0 / 10; 10 | — |
| `STAGE 4` section; `COMPACTION FUNCTIONS LOOKUP`; `… AND MASSES` pool | 0 / 10; 10 | — | 0 / 10; 10 | — |
| `PIPELINE LOOKUP`; `STAGES 2+3+4: UNIFIED PIPELINE` | — | — | — | 0 / 10 ("10 skipped"); 10 |
| integrity reports | none | none | 2 × `Pruned 1 unvalidated FullInstanton records` | none |
| `ALL WORK ITEMS COMPLETE` lines | 4 | 1 | 4 | 2 |
| driver exit status | 0 | 15 | 0 | 0 |

**The builds that do not depend on the signal equal RH1's.** `l4_compare.py` (below) compares 11's records for
`reference` and `scalars` with 07's, field by field:

```text
reference  entries         equal
reference  complete_lines  equal
reference  integrity       equal
reference  exit_status     equal
reference  packages        07: ['>> packages: datastorekit not installed; raypoolkit 0.2.0 (https://github.com/ds283/RayPoolKit@eaef0ce60e2fc354bb32f0ad576010e6a83c1976, requested v0.2.0)']
reference                  11: ['>> packages: datastorekit 0.5.0 (https://github.com/ds283/DatastoreKit@f47b9a255e9ad58e0d0eaf85644f53b575884d31, requested v0.5.0); raypoolkit 0.2.0 (https://github.com/ds283/RayPoolKit@eaef0ce60e2fc354bb32f0ad576010e6a83c1976, requested v0.2.0)']
scalars    entries         equal
scalars    complete_lines  equal
scalars    integrity       equal
scalars    exit_status     equal
scalars    packages        07: ['>> packages: datastorekit not installed; raypoolkit 0.2.0 (https://github.com/ds283/RayPoolKit@eaef0ce60e2fc354bb32f0ad576010e6a83c1976, requested v0.2.0)']
scalars                    11: ['>> packages: datastorekit 0.5.0 (https://github.com/ds283/DatastoreKit@f47b9a255e9ad58e0d0eaf85644f53b575884d31, requested v0.5.0); raypoolkit 0.2.0 (https://github.com/ds283/RayPoolKit@eaef0ce60e2fc354bb32f0ad576010e6a83c1976, requested v0.2.0)']
RESULT: L4 records equal
```

It exited 0. **The control**, `l4_compare.py --control` (RH1's `reference` against RH2's `resumed-b`), gives
`reference entries DIFFERS`, `reference integrity DIFFERS`, `RESULT: L4 records DIFFER`, exit 1: the comparison can
fail.

**The resume's pattern is RH1's:**
- the open pruned only unvalidated rows (2 = 2, on the shards that held them);
- the resume computed only what was not kept (STAGE 2: 4 + 6);
- the counts add up to `reference`'s (10 / 10 / 10 / 1).

The figures (4 + 6, 2 pruned, against RH1's 8 + 2, 1 pruned and RH0's 6 + 4, 2 pruned) depend on where the signal
fell. Since it fell after the trajectory stage, no trajectory was pruned, and the package's replicated prune was
not called.

### The profile database

`11-reference-profile.sqlite`, read `mode=ro`, has the tables `jobs` and `profile_data`, as RH1's.
- `jobs`: 1 row,
  `2026.6.1-job-"dk-and-rpk-migration-11-reference"-db-"…/11-reference.sqlite"-2026-10-22T21:29:12`.
- `profile_data`: **712** rows; the `ProfileAgent` printed "712 total database events".

| Method | RH0 | RH1 | RH2 |
|---|---|---|---|
| `object_get` | 443 | 443 | **352** |
| `ClientPool.lease_serial\|lease_serials` | 137 | 135 | 135 |
| `ClientPool.lease_serial\|commit_serials` | 76 | 76 | 76 |
| `ClientPool.release` | 61 | 59 | 59 |
| `object_store` | 40 | 40 | 40 |
| `object_validate_item` | 40 | 40 | 40 |
| `read_largest_store_ids` | 10 | 10 | 10 |
| total | 807 | 803 | 712 |

The method names are RH1's, and so are the `object_get` labels. **Why 91 fewer `object_get` events**, by object
and actor (both databases read `mode=ro`; D2):
- **`efold_value` vector: 210 at RH1, 120 at RH2.** Both record one event per actor for each of the 11 grids
  minted in STAGE 1 and STAGE 2 (110: a write to a replicated table reaches every shard). STAGE 3 then asks again
  for the ten instanton grids, which every shard already holds: at RH1 each such get ran on all ten actors (100
  events), at RH2 on one actor each (10 events: `shard0000`, `0004`, `0000`, `0002`, `0002`, `0004`, `0005`, `0004`,
  `0008`, `0009`, 21:29:34.9–42.7). The package serves a replicated get that finds every row from one shard.
- **`version` scalar: 11 at RH1, 10 at RH2.** RH1's layer read it twice on `shard0009`; the package once per shard.
- Every other object's `object_get` count, and every lease, commit, release, store and validate count, is RH1's.

No stored value depends on these (§4.3). The difference is described, not a stop (correction 12).

**The slow-query lines.** `reference`'s log ends with three lines RH1's did not print:

```text
(ProfileAgent pid=72325) -- Slow queries reported (total): 3 >2 sec (3 new), 0 >5 sec (0 new), 0 >10 sec (0 new), 0 >30 sec (0 new)
(ProfileAgent pid=72325)    New >2 sec queries:
(ProfileAgent pid=72325)      ## object_get: 3
```

The message is the `ProfileAgent`'s, in the package (`datastorekit/SQL/ProfileAgent.py:208`, `:223`) as in SI's
old layer at `0527480`: it prints only when an event exceeds 2 s. Three of STAGE 1's ten `efold_value` replica
writes (5,713 items each) took 2.03–2.11 s under a load of about 32; RH1's longest took 1.88 s.

### H1 — store hygiene by the package (after the comparisons, before the readers)

- **`shard_key_audit`** on each RH2 store (`out/11-h1-audit.txt`): each printed its schema line
  (`current-generation schema (key_serial present)`), `shard_keys row count: 10`, `per-shard key distribution:
  {0: 1, 1: 1, …, 9: 1}`, the cross-file check against shard #0 by its bare record, `'delta_Nstar' table (shard #0)
  row count: 10`, and **`VERDICT: OK -- no inconsistency found in <primary>.`**, exit 0, for `11-reference`,
  `11-resumed` and `11-scalars`.
- **The copy** (`out/11-h1-copy.txt`): `./venv/bin/python -m datastorekit.tools.sharded_store copy
  $R/11-reference.sqlite $R/11-reference-copy.sqlite` printed `>> copy: "…/11-reference-copy.sqlite" with 10 shards`
  and ten `>>   shard #N: …/11-reference-copy-shard000N.sqlite` lines, exit 0. No `11-reference-copy*` file existed
  before.
- **The read-back** (`out/11-h1-readback.txt`; `h1_readback.py`, below): `read_inventory` of `11-reference` and of
  the copy, read-only, with Ray never initialised: `problems` `()` on both; 24 classes each; every class's
  `(records, validated)` count of the copy equal to `11-reference`'s (e.g. `efold_value` `(7521, 0)`,
  `InflatonTrajectory` `(1, 1)`, `FullInstanton`, `SlowRollInstanton`, `CompactionFunction` `(10, 10)`,
  `GradientCoupledInstanton` `(0, 0)`). Exit 0.
- **The comparison** `11-compare-reference-copy`: A `…/11-reference.sqlite`, B `…/11-reference-copy.sqlite`,
  each 10 shards; `RESULT: equal`, exit 0; 30 tables matched, **no bookkeeping difference at all** (the copy carries
  the timestamps), problems none.
- **The deletion** (`out/11-h1-delete.txt`): `ShardedPool.closed_store_files(copy)` then
  `ShardedPool.delete_store(copy)`, from `./venv/bin/python -c`: both lists the same 11 paths, the ten shards
  `11-reference-copy-shard0000.sqlite` … `-shard0009.sqlite` in serial order, then `11-reference-copy.sqlite`;
  `same list: True`; Ray not initialised; exit 0. `ls $R | grep -c 11-reference-copy` then gave 0: **nothing of the
  copy remains.**

### What the package printed that SI's layer did not

A `diff` of each RH2 build log against RH1's of the same build (07's `resumed-a2` for `resumed-a`), with digits,
ANSI codes, the `07-`/`11-` prefix, the raylet's disk lines and the absl frames normalised away:
- **the provenance line**, which now names `datastorekit` (every log);
- **`reference`: the `ProfileAgent`'s three slow-query lines** (above): the same code in both layers, printed
  because of load;
- **`resumed-b`: a second prune report**, because two actors pruned where RH1's one did; its text is RH1's;
- **`reference`: STAGE 1's `Queue summary:` in `avg …/hr`** where RH1's read `avg …/min`: `raypoolkit`'s rate unit,
  since that stage took 6.04 s rather than 5.47 s;
- **`scalars`: no raylet `16 PYTHON worker processes` advisory** (RH1 printed one);
- **`resumed-a`**: only the absl stack's frames (where the signal fell).

`>> Created sharded datastore … with 10 shards` and `>> Opened existing sharded datastore … with 10 shards` are
printed as RH1's layer printed them. **No line of the package's own** (the replicated prune of 09's results note,
the reconciliation at open, a refusal) appeared: none was called for. So "every line the package printed that RH1's
layer did not" is, apart from the provenance line, none.

### Hygiene

- **Stores opened:** RH2's three, each after its build had ended (and `11-resumed` between its builds), the copy,
  the readers' copies through `run_readers.sh`; RH1's `07-reference`, `07-readers/resumed/before/07-resumed`,
  `07-readers/scalars/before/07-scalars` and `07-reference-profile`, and RH0's `02-reference` and `02-scalars-2`,
  through `compare_stores.py` and `sqlite3` `mode=ro` only. `read_inventory` read only `11-reference` and its copy.
- **The rehearsal root unchanged but for RH2's files**: every one of the 660 entries listed at the gate
  (`/usr/bin/stat`, mtime and size) is unchanged after the stop, except the root directory and `logs/`, which gained
  the `11-*` files. The new entries are RH2's stores (three primaries with ten shards each), `11-reference-profile`,
  `11-readers/` and `logs/11-*` (four logs, four pidfiles).
- **Deleted:** only the copy's 11 files, by `delete_store`. No `11-resumed` retry was needed. Nothing of RH0's or
  RH1's.
- **Not opened:** no `test-gradient*.sqlite`, nothing under `out-*/`, no June or July store; RH0's earlier attempts'
  directories only `statfs`ed and `stat`ed (D1).
- `ray stop` and `ray start` were never run. `pip freeze` equals the gate's copy; `pip check` clean. DatastoreKit
  `2900d82` and RayPoolKit `17029d9`, both clean.

### The staged CSVs

`git -c core.autocrlf=false add -f` for the two CSVs, then `git show :<path> | shasum -a 256` for each:
`b0564eecc22f9106dcccb57fd1a419749543c4b9d15dc0ffe7a8e0780e9058a2`, both (checked at staging).

## The scratch scripts

**`rows.py`**, run as `./venv/bin/python rows.py $R/11-reference $R/11-reference-profile.sqlite` and
`./venv/bin/python rows.py $R/11-resumed` (after each of `resumed-a` and `resumed-b`). 07's, with correction 5's
three reads added (marked):

```python
"""Read a closed rehearsal store mode=ro: per shard, the parent rows of the four homogeneous tables
with timestamp, validated and delta_Nstar, plus child-row counts by parent validation. Optionally
the profile database's object_get FullInstanton / efold_value calls.

07's rows.py, unchanged in what it reads, with three additions for 11 (brief, correction 5): the
primary's replication_in_flight rows (all columns), any -journal / -wal / -shm file beside the
primary or a shard, and the efold_value row count on each shard."""
import glob
import sqlite3
import sys

stem = sys.argv[1]  # e.g. $R/11-reference  (no .sqlite)
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
efold = {}  # added for 11
for shard in sorted(glob.glob(f"{stem}-shard*.sqlite")):
    sid = shard.rsplit("shard", 1)[1][:4]
    c = ro(shard)
    efold[sid] = c.execute("SELECT count(*) FROM efold_value").fetchone()[0]  # added for 11
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
print("--- efold_value rows per shard:", efold)  # added for 11
for f in sorted(
    glob.glob(f"{stem}*.sqlite-journal") + glob.glob(f"{stem}*-wal") + glob.glob(f"{stem}*-shm")  # -shm added
):
    print("journal/wal/shm:", f)

# added for 11: the primary's replication_in_flight
c = ro(f"{stem}.sqlite")
tabs = [r[0] for r in c.execute("SELECT name FROM sqlite_master WHERE type='table'")]
print("--- primary tables:", tabs)
if "replication_in_flight" in tabs:
    cols = [r[1] for r in c.execute("PRAGMA table_info(replication_in_flight)")]
    rif = c.execute("SELECT * FROM replication_in_flight").fetchall()
    print(f"--- replication_in_flight: {len(rif)} row(s); columns {cols}")
    for r in rif:
        print("   ", r)
c.close()

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

**`l4_compare.py`**, run from the repository root as `./venv/bin/python l4_compare.py` and, for the control,
`./venv/bin/python l4_compare.py --control`:

```python
"""L4: 11's parsed stage counts for reference and scalars against 07's (RH1's), record by record,
less the provenance line (`packages`). 07's l4_compare.py with its paths changed; with --control,
11's resumed-b is compared in place of 11's reference, which must fail."""
import json
import sys

OLD = ".documents/dk-and-rpk-migration/out/07-stage-counts.json"
NEW = ".documents/dk-and-rpk-migration/out/11-stage-counts.json"
KEYS = ("entries", "complete_lines", "integrity", "exit_status")


def by_build(path, nn):
    data = json.load(open(path))
    return {k.rsplit("/", 1)[-1][len(nn) + 1 : -len(".log")]: v for k, v in data.items()}


old, new = by_build(OLD, "07"), by_build(NEW, "11")
control = "--control" in sys.argv
failed = False
for build in ("reference", "scalars"):
    nbuild = "resumed-b" if (control and build == "reference") else build
    for key in KEYS:
        same = old[build][key] == new[nbuild][key]
        failed |= not same
        print(f"{build:10s} {key:15s} {'equal' if same else 'DIFFERS'}")
    print(f"{build:10s} {'packages':15s} 07: {old[build]['packages']}")
    print(f"{build:10s} {'':15s} 11: {new[nbuild]['packages']}")
print("RESULT:", "L4 records equal" if not failed else "L4 records DIFFER")
sys.exit(1 if failed else 0)
```

**`h1_readback.py`**, run from the repository root as `./venv/bin/python h1_readback.py $R/11-reference.sqlite
$R/11-reference-copy.sqlite`:

```python
"""H1: read the copy of 11-reference back with read_inventory (read-only, no Ray), and compare every
class's (records, validated) count with 11-reference's own. Run from the repository root:
    ./venv/bin/python <this> $R/11-reference.sqlite $R/11-reference-copy.sqlite"""
import sys

sys.path.insert(0, ".")
import ray  # noqa: E402  (imported only to show it is not initialised)
from config.datastore import factories  # noqa: E402
from datastorekit.store_inventory import read_inventory  # noqa: E402

source, copy = sys.argv[1], sys.argv[2]
a = read_inventory(source, factories)
b = read_inventory(copy, factories)


def counts(inv):
    return {
        name: (len(c.records), sum(1 for r in c.records if r.validated))
        for name, c in inv.classes.items()
    }


ca, cb = counts(a), counts(b)
print("source:", source)
print("copy:  ", copy)
print("problems (source):", a.problems)
print("problems (copy):  ", b.problems)
print("classes:", len(ca), len(cb))
for name in ca:
    mark = "equal" if ca[name] == cb.get(name) else "DIFFERS"
    print(f"  {name:28s} source {ca[name]}  copy {cb.get(name)}  {mark}")
same = ca == cb and not a.problems and not b.problems
print("ray initialised:", ray.is_initialized())
print("RESULT:", "copy reads back with no problem, every count equal to the source's" if same else "DIFFERS")
sys.exit(0 if same else 1)
```

The deletion's one-liner is in `out/11-h1-delete.txt` and verbatim in `verification.md` §3.7.

## The deliberate-breakage record

None. This prompt changes no code (README §5 rule 8). Each check above is one a bad build fails:
- a lost or extra row is an A-only or B-only line; a science bit is a near miss (RH0's control, 02's D5, and the
  orchestrator's one-ulp mutation at 07's review, showed the tool catches it);
- a missed or extra prune leaves a count that the rows read between the builds would contradict;
- a recomputed instanton shows in the lookup counts;
- a changed printed line breaks `stage_counts.py`'s parse or the L4 records, whose control is shown failing above;
- a bad copy reads back with a problem or a count that differs from the source's, and compares unequal.

## Observations not acted on

1. **The package's replicated-write repair was not exercised.** The signal fell 2.7 s after the run's last
   replicated write (the tenth `efold_value` grid), so `replication_in_flight` was empty and `resumed-b`'s open
   reconciled nothing. RH2 shows the sharded prune through the package's actors under real Ray, not the repair of
   an interrupted replicated write; a signal during the `efold_value` minting (banner +0 to +8.8 s at `reference`'s
   pace) would exercise it. The prompt's window is the `FullInstanton` one, so this is said, not chased.
2. **`resumed-a` exited 15**, as ChamPBH's R2 did: Ray's handler raised `SystemExit` in the driver's main thread
   (here inside `submit_actor_task`'s pickler). Its 11 actors were `DEAD` 9 s later. Read the log, not the status.
3. **A prune report can reach the driver's log late.** The second actor's report was forwarded after the last
   stage; the actors' own logs show both at the open, the same second. `stage_counts.py` counts it wherever it falls.
4. **The window moved later and wider** under the package: banner +9.76 to +12.89 s against RH1's +9.49 to +12.07,
   with the minting ending earlier (+8.76 against +9.41). At a load near 55, `S` = 12.0 s landed 76 ms after the
   sixth row.
5. **The profile count is not a reproducibility measure** (07's Observation 3): 712 here, because the package reads
   a replicated table's existing rows from one shard. 12 should not hold it to 712.

## State handed to the next prompt

- **RH2 holds, and equals RH1, and so RH0, bit for bit in both modes.**
  - The stores are `11-reference.sqlite`, `11-resumed.sqlite` (dense) and `11-scalars.sqlite` (scalars-only), ten
    shards each, under `~/ScienceData/StochasticInstantons-rehearsals/dk-and-rpk-migration/`, with
    `11-reference-profile.sqlite`, `11-readers/` and `logs/11-*`. They are in the package's format.
  - The read stores carry the readers' `version` `2026.3.0` row: `11-resumed.sqlite` and `11-scalars.sqlite`.
    `11-reference.sqlite` does not. The readers' `before/` copies are under `11-readers/{resumed,scalars}/before/`.
  - No prompt deletes them (README §3); the user may remove the campaign's stores after 12's review.
- **DatastoreKit G4 holds for SI**, recorded on this board (§2). The text for DatastoreKit's extraction board
  (12's draft; the user's commit, P14), with this commit's hash filled in at the review:

  > **G4 holds for StochasticInstanton (SI), 2026-10-22.** SI has adopted `datastorekit` **`v0.5.0`** (tag object
  > `6a6809d`, commit `f47b9a2`), which meets "SI has adopted `v0.3.0` or later" (`v0.4.0` addendum, standing in
  > the `v0.5.0` addendum). Item 9's three conditions:
  > 1. **The 9 layer files are gone and SI imports the package at the pinned tag.** SI's seven layer modules were
  >    deleted and `Datastore/__init__.py` and `Datastore/SQL/__init__.py` emptied at SI's `f4da58f`
  >    (dk-and-rpk-migration prompt 09); every pool is `datastorekit.SQL.ShardedPool`. The pin is
  >    `requirements.txt:16`, `datastorekit @ git+https://github.com/ds283/DatastoreKit@v0.5.0` (pinned `v0.4.0` at
  >    `1b1ca6d`, moved to `v0.5.0` at `80d99a7`), installed from the tag at `f47b9a255e9ad58e…`, not editable.
  > 2. **Both suites pass**, at SI's `66b1c81`: default 732 (731 passed, 1 skipped); integration 67 (66 passed,
  >    1 skipped).
  > 3. **A small grid was rebuilt through the package** (SI's RH2, dk-and-rpk-migration prompt 11, commit
  >    `<this commit>`), under a real Ray cluster with `raypoolkit` `v0.2.0`: a quadratic-potential grid, 10
  >    shards, one trajectory and ten each of `FullInstanton`, `SlowRollInstanton` and `CompactionFunction`, built
  >    straight through, killed by `SIGTERM` in the `FullInstanton` stage and resumed (the package's actors pruned
  >    the 2 unvalidated rows at open; the resume computed the 6 not kept), and built scalars-only. Each store
  >    equals SI's RH1 store of the same mode, built by SI's own layer at the tag `pre-datastorekit` (`0527480`),
  >    bit for bit by value (SI's `tools/compare_stores.py`, `sqlite3` `mode=ro`), timings and timestamps aside.
  >    `shard_key_audit` gave `VERDICT: OK` on each store; a `sharded_store copy` read back with no problem,
  >    compared equal, and was deleted by `delete_store`.
  >
  > Record: SI's `.documents/dk-and-rpk-migration/verification.md` §3 and
  > `.documents/dk-and-rpk-migration/11-rehearse-through-both-packages.md`.

  RayPoolKit's G4 held at 04 (board §2); RH1 and now RH2 ran it under real Ray. Its record is 12's draft as well.
- **The final counts:** suites 732 (731 passed, 1 skipped) and 67 (66 passed, 1 skipped) at `66b1c81`; `slow` from
  S1's 69, not run. `scalar_data.csv` `b0564eec…58a2` at RH0, RH1 and RH2. The schema is RH0's (30 tables).
- **For 12:** the protocol as run (`S` from `reference`'s rows and the profile database's `FullInstanton` vector
  gets; the exit status of a signalled driver 15 here; prune reports possibly forwarded late); the profile count is
  not a target; the package's reconciliation at open was not exercised (Observation 1).
- **No issue opened;** `.documents/OPEN-ISSUES.md` is unchanged (59 open, 29 closed). No SI cluster is running, and
  the lock is free. The venv, DatastoreKit, RayPoolKit, ChamPBH and SGK are untouched. The README and
  `.prompts/INDEX.md` are the orchestrator's.
- **Rollback:** `git revert` of this commit alone (records only); nothing in the venv.
