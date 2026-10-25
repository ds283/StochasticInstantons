# rrk-adoption — verification

**Campaign:** [`.prompts/rrk-adoption/`](../../.prompts/rrk-adoption/README.md) ·
**Board:** [`IMPLEMENTATION_STATE.md`](../../.prompts/rrk-adoption/IMPLEMENTATION_STATE.md) ·
**Outputs:** [`out/`](out/) (`04-*`) ·
**Launcher:** [`rehearsal/build_registered.sh`](rehearsal/build_registered.sh) (H0) ·
**Rehearsal tools:** `.documents/dk-and-rpk-migration/rehearsal/` (`ray_cluster.sh`,
`interrupt_when.py`, `stage_counts.py`), run unchanged

This document records the campaign's rehearsal (prompt 04; the user's ruling U2 for the hard-kill
route) in §1. It shows that, under real Ray on SI's isolated cluster, the wrapper
`RunDrivers/registered_run.py` records a build from before its first line to its end. It also
shows that the registry's account of four builds matches what happened to them: one clean, one
`SIGTERM`ed, one `SIGKILL`ed and ended by a person, and one resume to the end.

It is additive. A re-run that supersedes a figure gets a new dated subsection, and the figures
below stay as they are, correct for the tree they were taken on.

The stores, the run records and the launch logs live in the repository's `var/`, which git ignores
(README §3, R6):
- the stores in `var/datastores/`;
- the runs in `var/runs/`;
- the launch logs, pid files and signallers' logs in `var/rrk-adoption-04/`.

They are kept, and removing them is the user's. Only small text outputs are committed, under
[`out/04-*`](out/). Every claim below is a line in one of them, or in a command's output quoted
here. Times are GMT (`+0000`). The clocks went back at 01:00 on 2026-10-25, so the stores' naive
local timestamps, the wrapper's local times and the UTC of the scripts agree with no conversion.

---

## 1. The rehearsal (prompt 04, 2026-10-25)

**Tree.** `HEAD` `535b7e7` (the orchestrator's note for 04, on top of `edb03ea`), tree clean but
for 04's own untracked files (§1.9).
- `main.py` SHA-256 `07fbf19a530584008b3e335c94335a827d050790507c0243eb4cf7dda5503744`, and
  `git diff 1c223e8 -- main.py plot_InstantonSolutions.py plot_GradientCoupledSolutions.py
  utilities.py` is empty.
- Packages: `datastorekit` 0.5.0 at `f47b9a25…`, `raypoolkit` 0.3.0 at `67a75b97…`,
  `runregistrykit` 0.2.0 at `0bae3a3c…`, none editable; Ray 2.55.1.
- The venv's `pip freeze`, 84 lines, is identical (`cmp` exit 0) at 16:00, before the suites, and
  at 16:21, after the last suite. It is also identical to the orchestrator's dispatch copy.

**Result: the gate "R" holds.**
- **`reference`** ran to `done`/0.
- **`resumed-a`** was recorded `killed`/143. Its handler's record fell in the same second as the
  signal, and it exited 143, with no Ray `*** SIGTERM received` banner and no `** cancelled an
  alarm` line.
- **`resumed-b`** was `SIGKILL`ed. It then showed `stale` with `!!`, and a further run on its store
  was refused with nothing created. `end` ended it `lost`.
- **`resumed-c`** ran to `done`/0, computed only the 20 rows missing, and wrote its fingerprint to
  the sidecar.
- **The manifests.** Every manifest was written before `main.py`'s first line. `results_store_id`
  is `null` for the two runs begun with no sidecar, and the resumed store's id for the two begun
  after `store create`.
- **The stores.** `compare_stores` of the reference and the resumed store, and of the reference and
  RH2's `11-reference`, each gives **`RESULT: equal`**, bookkeeping aside. The two `var/` stores'
  fingerprints are one digest,
  `a9f716fb88cf8647327748e533e7402e6f406a59aba3826956e966b7f9081ea7`.
- **What Ray installs (P9).** Ray, attached to the external cluster, installs its own Python
  `SIGTERM` handler (the probe, §1.2), and the wrapper's handler replaced it.
- **Nothing left behind.** No Ray worker, actor or SI cluster process outlived any build, the
  `SIGKILL`ed one included, and none outlived the stop.

### 1.0 The stop at the gate, and its resolution

- **The stop.** At 15:42 the gate found `~/ScienceData` absent. `ls` of
  `~/ScienceData/StochasticInstantons-rehearsals/dk-and-rpk-migration/` gave "No such file or
  directory", the same with the sandbox disabled for that one read-only `ls`. `mdfind` found no
  `11-reference.sqlite`. The prompt's gate says to stop and ask if RH2's stores are gone, so I
  stopped before anything ran: no cluster, suite, launch or file in the repository.
- **The resolution.** The user restored `~/ScienceData` from a backup. The orchestrator checked it
  at 15:59:
  - `11-reference.sqlite`, its ten shards (mtime 22 Oct 21:29, as RH2 left them),
    `11-reference-profile.sqlite` and `logs/11-*` are back;
  - `compare_stores.py --schema <11-reference.sqlite> --against
    .documents/dk-and-rpk-migration/out/11-reference-schema.json` gives "RESULT: the schemas
    agree", exit 0.
- **The re-check.** I re-checked the gate at 16:00: the store and its shards present, all mtime
  22 Oct 21:29, and the old lock location `~/ScienceData/.rehearsal-lock` absent. Everything below
  ran from then on.

### 1.1 The cluster and the load

- 10 CPUs, host `mps026088` (`mps026088.phys.susx.ac.uk` in the manifests). The cluster ran with
  `ray_cluster.sh`'s default 4 CPUs.
- **The load.** At the gate it came from desktop processes and other sessions; no Ray process was
  on the machine. During `reference` it peaked at 135. That peak was not SI's alone:
  - SecondaryGWKit's suite (`python -m unittest discover -s ComputeTargets/tests -t .`, pid 24650,
    working directory `~/Documents/Code/SecondaryGWKit`, started about 16:06, another session's,
    not SI's venv) ran beside it;
  - so did macOS's `system_profiler`, `backupd-helper` (Time Machine), `contactsd` and `tccd`.

  No stop condition bears on load except the one-minute load at `start`, 15.3 here.

  | When (GMT) | Load average (1 / 5 / 15 min) |
  |---|---|
  | 15:42, the gate (the stop) | 14.21 / 11.37 / 9.39 |
  | 16:00, the gate re-checked | 5.25 / 5.39 / 6.53 |
  | 16:03–16:05, the suites before | 3.78 → 6.02; 5.65 → 18.16 |
  | 16:05, just before `start` | 16.94 / 9.10 / 7.68 |
  | 16:06:01, after `start` | 15.28 / 9.34 / 7.80 |
  | 16:07:03, `reference` launched | 9.87 / 8.80 / 7.70 |
  | 16:09, `reference` ended | 135.20 / 56.56 / 26.91 |
  | 16:10:56, before `resumed-a` | 42.80 / 47.09 / 26.40 |
  | 16:11:30, `resumed-a` launched | 34.92 / 44.66 / 26.35 |
  | 16:12, `resumed-a` ended | 33.83 / 43.63 / 27.48 |
  | 16:13:52, `resumed-b` launched | 14.49 / 35.70 / 25.75 |
  | 16:14:12, after its `SIGKILL` | 22.88 / 36.34 / 26.22 |
  | 16:14:58, the refused launch | 19.43 / 33.73 / 25.79 |
  | 16:15:20, `resumed-c` launched | 14.31 / 31.39 / 25.18 |
  | 16:16:03, `resumed-c` ended | 25.63 / 31.70 / 25.55 |
  | 16:17:16, before `stop` | 12.19 / 26.24 / 24.00 |
  | 16:18–16:21, the suites after | 7.30 → 7.72; 7.66 → 53.19 |

- **The start**, at 16:05:41, from the repository root:
  `.documents/dk-and-rpk-migration/rehearsal/ray_cluster.sh start "rrk-adoption 04 (R)" >
  <scratch>/start.txt 2>&1`, alone in its Bash call. It took **13 s** and exited **0** (the Bash
  tool reports a non-zero exit, and reported none). It ended:
  ```text
  recorded pid 24439 in /Users/ds283/.raypoolkit/rehearsal-lock/owner
  >> ray_cluster: address 127.0.0.1:6390
  >> ray_cluster: dashboard http://127.0.0.1:8266
  >> ray_cluster: actors: ./venv/bin/ray list actors --address 127.0.0.1:6390
  >> ray_cluster: started in 13s; gcs_server pid 24439
  ```
  - The lock's owner file: `project: StochasticInstantons`, `purpose: rrk-adoption 04 (R)`,
    `acquired: 2026-10-25T16:05:41+00:00`, `host: mps026088`, `ray_temp_dir` SI's,
    `ray_address: 127.0.0.1:6390`, `pid: 24439`.
  - `ray_cluster.sh status`, exit 0: the lock held by that owner, 18 SI processes, the four ports
    held.
  - `./venv/bin/ray status --address 127.0.0.1:6390`, exit 0: one active node, `0.0/4.0 CPU`,
    7.16 GiB memory, 2.00 GiB object store, no failures.
  - `ray list workers --filter "is_alive=True"`, `ray list actors --filter "state=ALIVE"` and `ray
    list jobs`, each `--address 127.0.0.1:6390`: each `No resource in the cluster`. Ray 2.55.1
    accepts the filters as written.
- **The four points** of correction 11 (after `start`, after H1, after H2, straight after H3's
  kill). At each, `ray_cluster.sh status` lists the baseline's 18 pids exactly (`diff` empty), and
  there are no live workers and no `ALIVE` actors (§1.7 for the fourth).
- **The jobs**, at 16:17:16, before the stop, all `SUCCEEDED`:

  | Job | What | Driver pid |
  |---|---|---|
  | `01000000` | the probe | 24927 |
  | `02000000` | `reference` | 24979 |
  | `03000000` | `resumed-a` | 26077 |
  | `04000000` | `resumed-b` | 26796 |
  | `05000000` | `resumed-c` | 27449 |

  So the four builds and the probe are five Ray jobs. The refused `resumed-c` stopped before Ray
  and added none. Ray records the `SIGKILL`ed driver's job as `SUCCEEDED` too. Actors: 44
  recorded, 0 `ALIVE`, ten `Datastore` and one `SerialPoolBroker` for each build. Workers: 65
  recorded, 0 alive.
- **The stop**, at about 16:17:30, alone in its Bash call, with no build, waiter or signaller
  running: `ray_cluster.sh stop > <scratch>/stop.txt 2>&1`. It took **20 s** and exited **0**.
  - `SIGTERM` to the 18 baseline processes (24439–24520);
  - after the 15 s grace, `SIGKILL` to 24439 (`gcs_server`) and 24448;
  - "no process names [SI's temp dir]; ports 6390 6391 8266 52366 are free";
  - "released the rehearsal lock (/Users/ds283/.raypoolkit/rehearsal-lock)";
  - "stopped in 20s". The script prints `stopped in` only on success.
- **After the stop**, at 16:18:01: `ray_cluster.sh status`, exit 0, shows `lock: free`, no SI
  process and the four ports free, and no `raylet` or `gcs_server` is on the machine. `ray stop`
  was never run.

Output: [`04-cluster.txt`](out/04-cluster.txt).

### 1.2 The probe (P9; the brief's correction 4)

After the baseline and before `reference`, at 16:06:45, from the repository root:

```bash
./venv/bin/python -c 'import signal, ray; a = signal.getsignal(signal.SIGTERM); ray.init(address="127.0.0.1:6390"); b = signal.getsignal(signal.SIGTERM); print("before", a); print("after", b, getattr(b, "__module__", None), getattr(b, "__qualname__", None)); ray.shutdown()'
```

exit 0, printing (after Ray's connection lines and its `FutureWarning`)

```text
before 0
after <function init.<locals>.sigterm_handler at 0x109e760c0> ray._private.worker init.<locals>.sigterm_handler
```

`0` is `SIG_DFL`. So on Ray 2.55.1, `ray.init` attached to an external cluster installs Ray's own
Python `SIGTERM` handler, `ray._private.worker`'s `init.<locals>.sigterm_handler`, as ChamPBH found
on 2.53 and SecondaryGWKit on a Ray it started itself. The probe added the job `01000000`,
`SUCCEEDED`, driver pid 24927. It opened no store and ran no solve. Output:
[`04-probe-p9.txt`](out/04-probe-p9.txt).

### 1.3 The four builds

Each build was launched by H0's launcher, which detaches itself (§1.10), and checked once. It was
then waited on by `wait_for_line.py`, which reads the launch log only. The wall time runs from the
launch to the launcher's line as the waiter saw it (±0.2 s). The fingerprint's time runs from
`fingerprint.taken.when`, stamped before the store is read, to the final `status.json` write,
whose `heartbeat` every write stamps.

| Run id | Slug | Store | pid | State | Exit | Launched → ended | Wall | `results_store_id` | Fingerprint at finish |
|---|---|---|---|---|---|---|---|---|---|
| `rrk-adoption-04-reference-20261025T160704` | `reference` | `reference` | 24979 | `done` | 0 | 16:07:03.5 → 16:09:19.7 | 2 min 16 s | `null` | `a9f716fb…1ea7`, 16:09:14 → 16:09:19, ≤ 5 s |
| `rrk-adoption-04-resumed-a-20261025T161131` | `resumed-a` | `resumed` | 26077 | `killed` | 143 | 16:11:30 → 16:12:38.8 | 69 s | `null` | `33c77e5c…3612`, 16:12:34 → 16:12:38, ≤ 4 s |
| `rrk-adoption-04-resumed-b-20261025T161352` | `resumed-b` | `resumed` | 26796 | `running` → `lost` | `null` | 16:13:52 → 16:14:12.8 (`SIGKILL` 16:14:12) | 21 s | `b7904d18f0d24466b255fb7c0224a805` | none (no `finish`) |
| `rrk-adoption-04-resumed-c-20261025T161521` | `resumed-c` | `resumed` | 27449 | `done` | 0 | 16:15:20 → 16:16:03.5 | 43 s | `b7904d18f0d24466b255fb7c0224a805` | `a9f716fb…1ea7`, 16:15:58 → 16:16:02, ≤ 4 s |

The refused launch of `resumed-c` (§1.7, step 6), driver pid 27298, was launched at 16:14:58 and
had exited 2 when the waiter first read its log at 16:15:07.0.

The stages' times, from each log's `ALL WORK ITEMS COMPLETE` lines:

| Build | STAGE 1 | STAGE 2 | STAGE 3 | STAGE 4 | `stage_counts.py` |
|---|---|---|---|---|---|
| `reference` | 34.8 s | 42.9 s | 23 s | 7.46 s | each stage 1/1/1/1 or 10/10/10/10; lookups 0 already, 10 to compute; 4 `ALL WORK ITEMS COMPLETE`; exit status 0 |
| `resumed-a` | 16.2 s | 31.3 s | — | — | stages 1 and 2 complete; STAGE 3 `INCOMPLETE; no queue summary`; exit status 143 |
| `resumed-b` | 0.19 s | — | — | — | STAGE 1 lookup 1, compute 0 ("no compute items"); STAGE 2 lookup 10 already, 0 to compute (no pool); STAGE 3 `INCOMPLETE`; exit status not recorded |
| `resumed-c` | 0.176 s | — | 17.5 s | 4.85 s | STAGE 1 compute 0; STAGE 2 10 already, 0 to compute; STAGE 3 10/10/10/10; STAGE 4 10/10/10/10; exit status 0 |
| RH2's `11-reference` | 6.04 s | 12.9 s | 9.59 s | 2.27 s | as `reference` |

- `reference`'s `stage_counts.py` record is RH2's `11-reference` record, provenance line aside (the
  orchestrator's reading of RH2's log: 1/1/1/1, then 10s, 4 complete lines, exit 0).
- `reference` ran 3 to 6 times slower than RH2's, stage for stage, at the load peak of §1.1. No
  solve depends on the load, and the stores compare equal (§1.8).
- No log has a `Traceback`, an `INTEGRITY` report, a `Pruned` or `Found … unvalidated` line, a `***
  SIGTERM received` banner or an `alarm` line (by `grep -i`). The only unusual lines are Ray's
  start-up `FutureWarning` in every log, and the package's reconciliation lines at the two resumes'
  opens (§1.7, §1.8).

**Each manifest** ([`04-<slug>.manifest.json`](out/)):
- `script` `main.py`, `script_sha256` `07fbf19a…3744`, which is `shasum -a 256 main.py`;
- `results` `var/datastores/rrk-adoption-04-<store>.sqlite`, relative to the client root;
- `argv` the wrapper's absolute path and its arguments, with the database absolute;
- `packages` the three, each `editable: false` with its tag and commit;
- `host` `id` `8d2b247824882486`, `arm64`, `Darwin` `27.0.0`, Python 3.13.16;
- `git_head` `535b7e7e21cdb7706d969003a9641913d246d93f`, `git_dirty` `true` (§1.9);
- `scope`, for `reference`, the literal 03 tested: `config quadratic-minimal.yaml; targets
  homogeneous; potential Quadratic; m 1e-05 Mp; N_init 20–20, 1 sample; N_final 5–5, 1 sample;
  delta_Nstar 0.1–3, 10 samples; n_collocation_points 5; alpha_regularization 0.01; 10 shards; job
  rrk-adoption-04-reference`, and the same with each run's job name for the others;
- `heartbeat_means` the text 03 committed;
- `results_store_id` as the table above.

**Written before the driver's first line** (correction 8). In every one of the four launch logs the
three `>> registered_run` lines are lines 1–3, and `main.py`'s first line, `>> packages: …`, is line
4. Each log, which the launcher's shell creates at the launch, is born before or in the same second
as its manifest (`/usr/bin/stat -f %SB`):

| Build | Log born | Manifest `created` | Manifest born |
|---|---|---|---|
| `reference` | 16:07:03 | 16:07:04 | 16:07:04 |
| `resumed-a` | 16:11:30 | 16:11:31 | 16:11:31 |
| `resumed-b` | 16:13:52 | 16:13:52 | 16:13:52 |
| `resumed-c` | 16:15:20 | 16:15:21 | 16:15:21 |

**`reference`'s record.**
- Its log ends `** driver exit status 0`, `** launcher saw exit status 0`. `list` shows it `done`,
  `1 finished`, with the stage `Skipping gradient branch (--targets excludes 'gradient')`.
- `status.json`: `done`, `exit_code` 0, and the fingerprint: digest `a9f716fb…1ea7`, `problems`
  `{}`, `taken` by its own run id.
- `fingerprint_sidecar`: `not written: /Users/ds283/Documents/Code/StochasticInstantons/var/datastores/rrk-adoption-04-reference.manifest.json
  is not a problem-free registry sidecar (there is none)`, since none existed yet. `resumed-a`'s
  status says the same of the resumed store.

Outputs:
- the launch logs: [`04-reference.log`](out/04-reference.log),
  [`04-resumed-a.log`](out/04-resumed-a.log), [`04-resumed-b.log`](out/04-resumed-b.log),
  [`04-resumed-c.log`](out/04-resumed-c.log), [`04-resumed-c-refused.log`](out/04-resumed-c-refused.log);
- each run's `manifest.json` and `status.json` whole;
- the checks, [`04-checks.txt`](out/04-checks.txt);
- the waiters' line-by-line arrival times, [`04-waits.txt`](out/04-waits.txt);
- the counts, [`04-stage-counts.txt`](out/04-stage-counts.txt).

### 1.4 The heartbeat

`status.json` keeps only the latest beat, so no history of beats is claimed. `list`'s `AGE` column
is the run's age since its manifest's `created`, not the heartbeat's. So the heartbeat's age at each
check is the check's time against `status.json`'s `heartbeat`, both read in the one call:

| Build | Check at | `status.json` heartbeat | Age | Stage in `status.json` | `list` at the check |
|---|---|---|---|---|---|
| `reference` | 16:07:14.127 | 16:07:04 | 10.1 s | `null` | `running`, `AGE 11s`, no stage, `1 alive` |
| `resumed-a` | 16:11:39.951 | 16:11:31 | 9.0 s | `null` | `running`, `AGE 10s`, no stage, `1 alive, 1 finished` |
| `resumed-b` | 16:14:00.495 | 16:13:52 | 8.5 s | `null` | `running`, `AGE 9s`, no stage, `1 alive, 2 finished` |
| `resumed-c` | 16:15:32.331 | 16:15:32 | 0.3 s | `STAGE 1: BACKGROUND INFLATIONARY TRAJECTORIES, all work items complete` | `running`, `AGE 12s`, stage `STAGE 3: SLOW-ROLL INSTANTONS`, `1 alive, 3 finished` |

- At the first three checks the log held only `>> ` lines, Ray's lines and the warning. These do not
  move the stage (correction 5), so the stage is still `null` and the beat is the one taken at
  registration.
- At `resumed-c`'s check its banners had begun. The STAGE 3 banner beat between the status read and
  `list`'s read, a second or less apart.

**The final status's last beat against the build's end:**
- `reference`: 16:09:19, against the launcher's line at 16:09:19.7;
- `resumed-a`: 16:12:38, against 16:12:38.8;
- `resumed-c`: 16:16:02, against 16:16:03.5;
- `resumed-b`: its last beat was 16:14:02, the STAGE 3 banner, 10 s before the `SIGKILL` at 16:14:12.
  At `end`, 16:15:16, its age was 74.1 s (the `ended` record's `heartbeat_age`). `end`'s own write
  then stamped `heartbeat` 16:15:16 in the lost status, since every status write stamps it.

**Against the longest silence 03 expected** (results note 03, §2.3: `STAGE 2`, banner to
completion, about 13 s at RH2's load; the heartbeat's age under about 45 s):
- **`reference`.** Its log has no line between the `STAGE 2: FULL MSR INSTANTONS` banner (line 36,
  seen 16:07:55.5) and that stage's completion line (line 37, seen 16:08:38.4). So that stage was
  silent for **42.9 s**, longer than 13 s because the stage ran 3.3 times longer, and the
  heartbeat's age reached about 43 s at most, inside the 45 s 03 set and far inside the 900 s
  window.
- **The other gaps.** STAGE 1's worker line (16:07:27.4) to its completion (16:07:55.3) is 27.9 s.
  No RayWorkPool progress line appeared in any log, as 03 predicted for stages under 60 s.
- **`stale`.** No `list` taken while a build ran showed it `stale`.

### 1.5 Choosing the two delays (correction 9 and correction 10)

**`reference`'s rows**, read after it had finished and after its `store create` and `store
fingerprint --write`. The reads were made through `sqlite3` with `file:…?mode=ro` URIs only, by
`rows.py`, which is RH2's `rows.py` less the profile database, plus the newest `efold_value` per
shard ([`04-rows.py.txt`](out/04-rows.py.txt); output [`04-rows.txt`](out/04-rows.txt)). Its
query per shard:

```sql
SELECT p.serial, p.timestamp, p.validated, d.value FROM FullInstanton p
  LEFT JOIN delta_Nstar d ON d.serial = p.delta_Nstar_serial        -- and likewise for the
SELECT max(timestamp) FROM efold_value                              -- other three tables
```

The banner time is from `reference`'s own log, as the waiter saw each line arrive
([`04-waits.txt`](out/04-waits.txt)). `interrupt_when.py --banner "STAGE 2: FULL MSR INSTANTONS"`
first matches the `** STAGE 2: FULL MSR INSTANTONS LOOKUP:` line (line 33), seen at 16:07:55.5,
with the pool banner (line 36) in the same read.

| Event in `reference` | Time | From the banner |
|---|---|---|
| `InflatonTrajectory` stored (all ten replicas) | 16:07:50.461 | −5.0 s |
| the last `efold_value` minted (every shard) | 16:08:24.841 | +29.3 s |
| `FullInstanton` rows stored | 16:08:27.686, 27.955, 28.596, 31.271, 33.924, 35.677, 35.925, 36.127, 38.106, 38.134 | +32.2, +32.5, +33.1, +35.8, +38.4, +40.2, +40.4, +40.6, +42.6, +42.6 s |
| `SlowRollInstanton` rows stored | 16:08:59.356 – 16:09:00.869 | +63.9 – +65.4 s |
| `CompactionFunction` rows stored | 16:09:07.319 – 16:09:12.465 | +71.8 – +77.0 s |

So at `reference`'s pace the narrow window (some `FullInstanton` rows stored, others not) ran from
+32.2 to +42.6 s, and the wide window (first `FullInstanton` to last `CompactionFunction`) from
+32.2 to +77.0 s. The load had been 135 during `reference` and was 34.9 at `resumed-a`'s launch,
so a faster pace was likely.

- **`<s>` for `resumed-a` = 33 s** (`--after 33 --poll 0.2`). Three things decided it:
  - **Where it falls at `reference`'s pace:** between the second row (+32.5) and the third
    (+33.1), early in the narrow window. So I expected δN★ 0.42222 and 1.0667 stored, possibly not
    yet validated, and the other eight not.
  - **Why early:** a driver running at a fraction f of `reference`'s time leaves 33 s inside the
    narrow window for f from 0.77 to 1.03, and inside the wide window for f from 0.43 to 1.03. That
    covers a driver up to 2.3 times faster than `reference` (the load was falling) and down to 3%
    slower.
  - **RH2's choice:** it aimed between its eighth and ninth rows at a steady load. Here the load had
    just fallen from its peak, and the early end hedged against the faster pace.
- **What `resumed-a` did** (the same query on the resumed store after it):
  - the trajectory was stored at 16:11:56.817, and the banner was seen at 16:12:00 (by
    `interrupt_when.py`) and at 16:12:00.0 (by my waiter);
  - the last `efold_value` was minted at 16:12:20.634 (banner +20.6 s, against +29.3 at `reference`);
  - the `FullInstanton` rows were stored from 16:12:22.731 to 16:12:31.151 (banner +22.7 to +31.2
    s), about 0.72 of `reference`'s time, 1.4 times faster;
  - STAGE 2 completed at 16:12:31.5, and the signal came at 16:12:33, 1.5 s into STAGE 3.

  **So the signal fell inside the wide window and missed the narrow one**: all ten `FullInstanton`
  rows were stored and validated, and no `SlowRollInstanton` or `CompactionFunction` row was
  stored. The store was partial. By the brief's rule (correction 9) a narrow miss inside the wide
  window is recorded, not retuned, so there was one attempt and no retune. It fell during a
  replicated `get` of `efold_value` (STAGE 3's grids), which the primary's
  `replication_in_flight` recorded (`('get', 'efold_value', 6, None, '2026-10-25
  16:12:32.963602')`), with `efold_value` whole (7,521 rows) on every shard and no orphan.
- **The delay for `resumed-b` = 10 s after `STAGE 3: SLOW-ROLL INSTANTONS`** (`--after 10 --poll
  0.2`).
  - **The stage.** `resumed-a` left every `FullInstanton` validated and no `SlowRollInstanton`
    stored, so `resumed-b`'s first stage with work was STAGE 3. Its banner text first matches the
    `** STAGE 3: SLOW-ROLL INSTANTONS LOOKUP:` line, printed with the pool banner in the same
    second.
  - **The bound.** `reference`'s STAGE 3 took 23 s, so half is 11.5 s, and the floor is 2 s.
  - **The expectation.** In `reference` the first `SlowRollInstanton` row came 21.0 s after its
    STAGE 3 banner (16:08:38.4 → 16:08:59.36), and about 15 s at `resumed-a`'s faster pace. So
    10 s was expected to leave every `SlowRollInstanton` unstored: the store partial whatever came
    next.
  - **What it did.** The banner was seen at 16:14:02, and `SIGKILL` was sent at 16:14:12. After the
    kill the resumed store held the same 10 validated `FullInstanton` rows and the trajectory, and
    no `SlowRollInstanton` or `CompactionFunction` row: `resumed-b` stored nothing. It was killed
    1.5 s into a replicated `get` of `efold_value` (`('get', 'efold_value', 5, None, '2026-10-25
    16:14:10.522558')`), with `efold_value` whole on every shard. This is the outcome expected;
    correction 10 says such an outcome is recorded, not a stop.

### 1.6 The signal (H2, P9; correction 3)

`interrupt_when.py` ([`04-resumed-a.interrupt.log`](out/04-resumed-a.interrupt.log)), in UTC:

```text
[2026-10-25T16:12:00+00:00] interrupt_when: saw "STAGE 2: FULL MSR INSTANTONS"; waiting 33 s
[2026-10-25T16:12:33+00:00] interrupt_when: sent SIGTERM to pid 26077
```

`resumed-a`'s log, after the STAGE 3 banner (lines 43–47):

```text
** STAGE 3: SLOW-ROLL INSTANTONS
** SIGTERM at 2026-10-25 16:12:33 +0000: recorded killed, exit code 143; stopping main.py; the process will exit with status 143
** SIGTERM: main.py ended with SystemExit(1); recording killed, exit code 143
** driver exit status 143
** launcher saw exit status 143
```

- **Signal → the `killed` record.** The handler's line says 16:12:33 +0000, against `sent SIGTERM`
  at 16:12:33 UTC: **0 s, ±1 s**. The waiter saw the line at 16:12:34.1. The handler writes the
  record before it prints the line. So "within about a second" holds to the resolution the two
  clocks give.
- **Signal → the final record.** `finish_after_exec`'s record, with the fingerprint, has
  `status.json`'s heartbeat at 16:12:38 against 16:12:33: **5 s, ±1 s**. The fingerprint began at
  16:12:34 (`taken.when`); the rest is `main.py` unwinding its `with ShardedPool` and the read.
- `main.py` ended with `SystemExit(1)`, not 143: the handler's `SystemExit(143)`, raised inside a
  Ray wait, reaches the driver as `SystemExit(1)`. The latch carried the signal, so the run is
  `killed`/143 and exited 143.
- **P9's three measurements, against RH2's unregistered `resumed-a`:**

  | | RH2's `resumed-a` (`dk-and-rpk-migration` 11) | This `resumed-a` |
  |---|---|---|
  | exit status | 15 | **143** |
  | absl's `*** SIGTERM received at time=…` banner | present, twice, with its stack | **absent** |
  | `** cancelled an alarm` line | — (no wrapper) | **absent** |

  With the probe (§1.2), this is P9's answer for Ray 2.55.1 attached to an external cluster:
  - `ray.init` installs Ray's Python `SIGTERM` handler, and the wrapper's replaces it;
  - Ray's handler did not run, and neither did absl's C handler, so no alarm was armed;
  - the driver exits 143, not RH2's 15 or the 134 ChamPBH saw before its wrapper.

  This is the expected result (correction 3).
- **The records.** `status.json` ([`04-resumed-a.status.json`](out/04-resumed-a.status.json)):
  `killed`, `exit_code` 143, stage `STAGE 3: SLOW-ROLL INSTANTONS`, the fingerprint (digest
  `33c77e5c8cc06201874341931b6251735802f1bd104efa97a6cb75069a313612`, `taken` by its run id at
  16:12:34, `problems` `{}`), and `fingerprint_sidecar` "not written … (there is none)". `list`:
  `killed`, `2 finished`.
- **Then `store create`** at 16:13:31, on the closed store, exit 0:
  ```text
  ./venv/bin/python -m runregistrykit store create var/datastores/rrk-adoption-04-resumed.sqlite --purpose "rrk-adoption 04 H2-H4: the rehearsal grid built by resumes after SIGTERM and SIGKILL, kept for the user"
  ```
  It gave `store_id` `b7904d18f0d24466b255fb7c0224a805`. `store show` then listed
  `rrk-adoption-04-resumed-a-20261025T161131  killed    finished  by results`.

### 1.7 The hard-kill route (H3, U2)

Line by line, in order:

1. **The kill.** `kill_when.py` is `interrupt_when.py` with `SIGTERM` changed to `SIGKILL` in the
   signal sent and in its messages, and nothing else (correction 10;
   [`04-kill_when.diff`](out/04-kill_when.diff), the same five hunks as ChamPBH's). Its log
   ([`04-resumed-b.kill.log`](out/04-resumed-b.kill.log)):
   ```text
   [2026-10-25T16:14:02+00:00] interrupt_when: saw "STAGE 3: SLOW-ROLL INSTANTONS"; waiting 10 s
   [2026-10-25T16:14:12+00:00] interrupt_when: sent SIGKILL to pid 26796
   ```
   It signalled the pid in `resumed-b.pid` alone.
2. **The log** ends with the STAGE 3 banner and `** launcher saw exit status 137`. There is no `**
   driver exit status` line (`grep -c` 0).
3. **The status left behind**, read at 16:14:50: `running`, `exit_code` `null`, `pid` 26796,
   `heartbeat` 16:14:02, stage `STAGE 3: SLOW-ROLL INSTANTONS`, no fingerprint.
4. **What the kill left in Ray**, at 16:14:32 (the fourth point of correction 11):
   - `ray_cluster.sh status` lists the 18 baseline pids exactly (`diff` empty);
   - `ray list workers --filter "is_alive=True"` and `ray list actors --filter "state=ALIVE"` each
     give `No resource in the cluster`;
   - the full actor listing is 33 actors, all `DEAD`, among them `04000000`'s ten `Datastore` and
     its `SerialPoolBroker`, and job `04000000` is `SUCCEEDED`;
   - `kill -0 26796`: `no such process`.

   So the driver, attached to an external cluster, left nothing behind, and there was nothing to
   wait for.
5. **Beside the store**, after the kill: no `-journal`, `-wal` or `-shm` file beside the primary or
   any shard (`ls var/datastores`; `rows.py`). The primary's `replication_in_flight` held the one
   record of §1.5. `resumed-c`'s open reconciled it (§1.8).
6. **`stale`**, at 16:14:50, `list` stdout:
   ```text
   !! rrk-adoption-04-resumed-b-20261025T161352  running           -      59s  rrk-adoption 04 H3: a resume of the resumed store, killed with SIGKILL in STAGE 3  · STAGE 3: SLOW-ROLL INSTANTONS
   3 run(s) under /Users/ds283/Documents/Code/StochasticInstantons/var/runs: 2 finished, 1 stale; 0 with no host recorded.
   ```
   and stderr:
   ```text
   !! 1 run(s) say they are running and are not: the pid does not answer kill -0, the heartbeat is older than 900 s, or this machine has rebooted since. Nothing here has killed or cleaned anything — go and look. Once you know one is over, end it with `python -m runregistrykit end RUN_ID --reason TEXT`.
   ```
7. **The refusal** (correction 12), at 16:14:58: step 6's launch with the launch files
   `resumed-c-refused.log` and `.pid`, and nothing else changed. Its whole log:
   ```text
   !! Cannot begin run rrk-adoption-04-resumed-c-20261025T161459 with results "/Users/ds283/Documents/Code/StochasticInstantons/var/datastores/rrk-adoption-04-resumed.sqlite": run rrk-adoption-04-resumed-b-20261025T161352 is running (stale, pid 26796) and names this store by its results and results_store_id. A stale run is ended by a person, with `python -m runregistrykit end RUN_ID --reason TEXT`, before another run is begun on its store; the registry does not decide that a run is dead. No run directory was created
   ** driver exit status 2
   ** launcher saw exit status 2
   ```
   - Exit status 2. One `!! ` line, naming `resumed-b`'s run and `python -m runregistrykit end`.
     The marker.
   - `find var/runs | sort` before and after: `diff` empty. `ls var/datastores` before and after:
     unchanged.
   - No Ray job was added (four before and after).
8. **`end`**, at 16:15:15, after `kill -0 26796` again gave `no such process`:
   ```text
   $ ./venv/bin/python -m runregistrykit end rrk-adoption-04-resumed-b-20261025T161352 --reason "SIGKILLed on purpose by rrk-adoption 04 to rehearse the hard-kill route"
   >> end: rrk-adoption-04-resumed-b-20261025T161352 is now lost, verified: its pid 26796 does not answer kill -0 on this host
   ```
   It exited 0. The launcher's bash had reaped the driver, so `end` was not refused by an unreaped
   process (RunRegistryKit's `[04-a-killed-process-not-yet-reaped-answers-kill-0]`).
9. **`lost`.** `list` then showed
   `rrk-adoption-04-resumed-b-20261025T161352  lost` and `3 finished`. The status's `ended` record
   ([`04-resumed-b.status.json`](out/04-resumed-b.status.json)):
   ```json
   "ended": {
     "at": "2026-10-25T16:15:16+00:00",
     "by": "ds283",
     "evidence": {"boot": "this", "heartbeat": "2026-10-25T16:14:02+00:00", "heartbeat_age": 74.100194,
                  "host": "this", "pid": 26796, "pid_answers": false, "state": "running", "status_readable": true},
     "git_head": "535b7e7e21cdb7706d969003a9641913d246d93f",
     "host": {"boot": "376461AF-4985-4F42-8E41-F4E914F5E3E6", "id": "8d2b247824882486", "name": "mps026088.phys.susx.ac.uk"},
     "not_verified_because": null,
     "reason": "SIGKILLed on purpose by rrk-adoption 04 to rehearse the hard-kill route",
     "verified": true
   }
   ```
   with `state` `lost` and `exit_code` `null`; every other field kept, but `heartbeat`, which the
   write stamps (16:15:16).
10. **The resume.** `resumed-c` was then begun on the same store and accepted (§1.8).

Outputs: [`04-resumed-b.kill.log`](out/04-resumed-b.kill.log), [`04-refusal.txt`](out/04-refusal.txt),
[`04-checks.txt`](out/04-checks.txt) (the status before `end`, `list` after the kill, `end` and
`list` after it), [`04-resumed-b.status.json`](out/04-resumed-b.status.json).

### 1.8 The resume (H4) and the stores (H5)

- **`resumed-c`'s open.** The `>>` lines between Ray's connection lines and STAGE 1, verbatim:
  ```text
  >> Sharded datastore "/Users/ds283/Documents/Code/StochasticInstantons/var/datastores/rrk-adoption-04-resumed.sqlite" was opened with a replicated write in flight (operation="get", class="efold_value", controlling shard=5, store_id=None, started=2026-10-25 16:14:10.522558)
  >>   every shard already holds what the controlling shard holds: nothing was repaired
  >>   the replication_in_flight record was cleared
  >> Opened existing sharded datastore "/Users/ds283/Documents/Code/StochasticInstantons/var/datastores/rrk-adoption-04-resumed.sqlite" with 10 shards
  ```
  `resumed-b`'s open had printed the same three lines for `resumed-a`'s record (`controlling
  shard=6`, started 16:12:32.963602).
- **The prune.** It printed no report, since there was nothing to prune: the rows read after
  `resumed-a` and after `resumed-b` held no unvalidated row of any table. The prune removed no
  validated row: `resumed-c`'s STAGE 2 lookup found all 10 `FullInstanton` rows.
- **`resumed-c` ran to `done`/0.** Each stage that had work printed its `ALL WORK ITEMS COMPLETE`
  (STAGES 1, 3 and 4; STAGE 2 had nothing to compute, so no pool). `stage_counts.py` shows that the
  resume computed only what was missing:
  - STAGE 1: compute 0, "no compute items were evaluated";
  - STAGE 2: "10 already computed, 0 to compute";
  - STAGE 3: 10 to compute, 10/10/10/10;
  - STAGE 4: 10 to compute, 10/10/10/10.

  After it, `mode=ro`: every table 10 rows (the trajectory 1 × 10 replicas), all validated, no
  orphan, `replication_in_flight` empty, `efold_value` 7,521 on every shard.
- **Its fingerprint.** `fingerprint_sidecar` `"written"`. Three readings are one digest,
  `a9f716fb88cf8647327748e533e7402e6f406a59aba3826956e966b7f9081ea7`, with the per-class
  `classes` of the status and the sidecar equal as JSON:
  - the fingerprint in its status;
  - the sidecar's after it (`taken` by `rrk-adoption-04-resumed-c-20261025T161521` at 16:15:58);
  - `store fingerprint` on the closed store.
- **`compare_stores`, the reference against the resumed store**, at 16:16:28: `PYTHONPATH=.
  ./venv/bin/python tools/compare_stores.py --json <scratch>/compare-reference-resumed.json
  var/datastores/rrk-adoption-04-reference.sqlite var/datastores/rrk-adoption-04-resumed.sqlite`.
  - It exited 0 with **`RESULT: equal`**, `problems: none`.
  - All 30 tables matched, with 0 rows in A only or B only. Among them: `FullInstanton` 10,
    `FullInstantonValue` 16,564, `SlowRollInstanton` 10, `SlowRollInstantonValue` 16,564,
    `CompactionFunction` 10, `CompactionFunctionSamples` 33,128, `InflatonTrajectoryValue` 5,713
    and `efold_value` 7,521.
  - The bookkeeping that differs, and is not compared: the timestamps, and the JSON timing keys
    (`CompactionFunction.metadata` `compute_time` with its `full` and `slow_roll` ones;
    `FullInstanton.diagnostics_json` `compute_time` and `mean_time_per_picard_iteration`;
    `InflatonTrajectory` and `SlowRollInstanton` `compute_time`). That is what `dk-and-rpk-migration`
    README §4.2 allows.
- **`compare_stores`, the reference against RH2's `11-reference`** (P10), at 16:16:45, the same
  command with B =
  `~/ScienceData/StochasticInstantons-rehearsals/dk-and-rpk-migration/11-reference.sqlite`.
  - It exited 0 with **`RESULT: equal`**, `problems: none`: the same 30 tables, the same counts, and
    the same bookkeeping list (`diff` of the two outputs from the bookkeeping section on: empty).
  - The tool opens every file `mode=ro`. The `11-reference*.sqlite` files' mtimes were the same
    before and after it, and no journal appeared beside them.
  - So the wrapper changed nothing `main.py` stores, bit for bit by value, against a build made
    without it three days earlier (correction 16: since RH2 only comments and the `raypoolkit` pin,
    with a byte-identical `RayWorkPool.py`, have moved).
- **`store fingerprint`** on each `var/` store, at 16:16:59 and 16:17:03, without `--write`, both exit 0:
  - the reference: digest `a9f716fb…1ea7`, `problems: none`, "matches the fingerprint taken
    2026-10-25T16:10:30+00:00 by a person, at 535b7e7e… (dirty)";
  - the resumed store: the same digest, "matches the fingerprint taken 2026-10-25T16:15:58+00:00 by
    run rrk-adoption-04-resumed-c-20261025T161521, at 535b7e7e… (dirty)".

  The two sidecars' per-class `classes` objects, all 24 classes, compare equal as JSON. So the
  fingerprints compare as `compare_stores` says (correction 14).
- **The reference's sidecar.** At 16:10:29, `store create
  var/datastores/rrk-adoption-04-reference.sqlite --purpose "rrk-adoption 04 H1: the reference build
  of the rehearsal grid, kept for the user"`, exit 0, gave `store_id`
  `503640899e96453a968de535c5b677a8`. Then `store fingerprint … --write`, exit 0, gave the digest
  `a9f716fb…1ea7`, equal to the one in `reference`'s status, and said "wrote the fingerprint into
  the sidecar; it replaced none". No run of this prompt carries the reference's id (correction 13).
- **`store show`**, just after 16:17:03, the runs naming each store:
  ```text
  reference:  rrk-adoption-04-reference-20261025T160704  done      finished  by results
  resumed:    rrk-adoption-04-resumed-c-20261025T161521  done      finished  by results and results_store_id
              rrk-adoption-04-resumed-b-20261025T161352  lost      finished  by results and results_store_id
              rrk-adoption-04-resumed-a-20261025T161131  killed    finished  by results
  ```

Outputs: [`04-compare-reference-resumed.txt`](out/04-compare-reference-resumed.txt) and `.json`,
[`04-compare-reference-11reference.txt`](out/04-compare-reference-11reference.txt) and `.json`,
[`04-store.txt`](out/04-store.txt) (every `store` command's output whole),
[`04-rows.txt`](out/04-rows.txt).

### 1.9 `git_dirty`, and what was written

- **`git_dirty`** is `true` in every manifest, store history and fingerprint. `begin` records
  `bool(git status --porcelain)`, which counts untracked files.
  - When `reference` began, the one untracked entry was the launcher's directory,
    `.documents/rrk-adoption/rehearsal/`.
  - The outputs under `.documents/rrk-adoption/out/` were copied after the last build.
  - No tracked file changed and nothing was staged before the commit.
  - `var/` is ignored and does not count.
- **`git_head`** is `535b7e7e21cdb7706d969003a9641913d246d93f`, the orchestrator's note for 04.
- **Written:**
  - `var/datastores/`: the two stores, 11 files each, and their two sidecars;
  - `var/runs/`: the four run directories;
  - `var/rrk-adoption-04/`: five launch logs, five pid files, and the two signallers' logs;
  - the launcher and `out/04-*`, in the repository;
  - outside it, the lock under `~/.raypoolkit/` (created by `start`, removed by `stop`), the
    cluster's temp dir, and my scratch directory.

  Nothing under `var/` was deleted. No existing store was opened but RH2's `11-reference`, by
  `compare_stores` alone.

### 1.10 The launcher (H0), and how each build was launched

`.documents/rrk-adoption/rehearsal/build_registered.sh STORE BUILD ADDRESS PURPOSE [LAUNCH]`, run
from the root (`bash -n` passes):
- **Its checks.** It checks its arguments as `build.sh` does, each refusal one `!! ` line, exit 2.
  These were tried: too few arguments (usage, exit 2), a bad slug, an empty address, a blank
  purpose, a run from outside the root, and an existing log (`reference.log`, after H1).
- **What it runs.** It then **detaches itself**: `nohup bash -c '<runner>' … > /dev/null 2>&1 <
  /dev/null &`, then `disown`, and returns at once. The runner:
  - starts `PYTHONPATH=. ./venv/bin/python -u RunDrivers/registered_run.py --campaign rrk-adoption
    --prompt 04 --register BUILD --purpose PURPOSE -- <§1.1's arguments>` with stdout and stderr to
    `$L/LAUNCH.log`;
  - writes `$!` to `$L/LAUNCH.pid` at once;
  - `wait`s on it, and so reaps it;
  - appends `** launcher saw exit status N`.
- **The pid.** `$!` is the wrapper's Python process, so the pid file and `status.json`'s `pid` were
  one number at every check.
- **The paths.** `$S` and `$L` are absolute (`$PWD/var/datastores`, `$PWD/var/rrk-adoption-04`).
- **No marker of its own.** It appends no `** driver exit status` line.
- **The cluster.** It starts and stops no cluster.

The launch lines, as run (each in a Bash call of its own; for H2 and H3 the signaller followed in
the same call):

```bash
.documents/rrk-adoption/rehearsal/build_registered.sh reference reference 127.0.0.1:6390 "rrk-adoption 04 H1: the rehearsal grid straight through, the reference store"
.documents/rrk-adoption/rehearsal/build_registered.sh resumed resumed-a 127.0.0.1:6390 "rrk-adoption 04 H2: the rehearsal grid into the resumed store, interrupted with SIGTERM in STAGE 2" && L=$PWD/var/rrk-adoption-04 && nohup ./venv/bin/python .documents/dk-and-rpk-migration/rehearsal/interrupt_when.py $L/resumed-a.log $L/resumed-a.pid --banner "STAGE 2: FULL MSR INSTANTONS" --after 33 --poll 0.2 > $L/resumed-a.interrupt.log 2>&1 < /dev/null & disown
.documents/rrk-adoption/rehearsal/build_registered.sh resumed resumed-b 127.0.0.1:6390 "rrk-adoption 04 H3: a resume of the resumed store, killed with SIGKILL in STAGE 3" && L=$PWD/var/rrk-adoption-04 && nohup ./venv/bin/python <scratch>/kill_when.py $L/resumed-b.log $L/resumed-b.pid --banner "STAGE 3: SLOW-ROLL INSTANTONS" --after 10 --poll 0.2 > $L/resumed-b.kill.log 2>&1 < /dev/null & disown
.documents/rrk-adoption/rehearsal/build_registered.sh resumed resumed-c 127.0.0.1:6390 "rrk-adoption 04 H4: the last resume of the resumed store, straight through" resumed-c-refused
.documents/rrk-adoption/rehearsal/build_registered.sh resumed resumed-c 127.0.0.1:6390 "rrk-adoption 04 H4: the last resume of the resumed store, straight through"
```

`resumed-a`'s purpose says "in STAGE 2". The signal fell 1.5 s into STAGE 3 (§1.5); a manifest is
not amended.

### 1.11 The suites

Serially, each in the foreground, never with the cluster up, and with `RAY_ADDRESS` unset
(integration under `RAY_ADDRESS=local`). The load is the one-minute figure at the start and the end:

| Selection | Before `start` | After `stop` |
|---|---|---|
| `./venv/bin/python -m pytest -m "not integration and not slow" -q -p no:cacheprovider` | **848**: 847 passed, 1 skipped, 141 deselected; 48.4 s (16:03:09–16:04:01); load 3.78 → 6.02 | **848**: 847 passed, 1 skipped, 141 deselected; 52.6 s (16:18:07–16:19:04); load 7.30 → 7.72 |
| `RAY_ADDRESS=local ./venv/bin/python -m pytest -m integration -q -p no:cacheprovider` | **72**: 71 passed, 1 skipped; 79.3 s (16:04:08–16:05:29); load 5.65 → 18.16 | **72**: 71 passed, 1 skipped; 119.5 s (16:19:11–16:21:13); load 7.66 → 53.19 |

These are 03's counts and the orchestrator's baselines exactly. Nothing failed, so nothing was
re-run. No `raylet`, `gcs_server` or `pytest` process remained after the first integration run.
Output: [`04-suites.txt`](out/04-suites.txt).

### 1.12 Observed, not acted on

- **The package's repair of an interrupted replicated write ran twice.** RH2 never exercised it.
  Both signals fell during a replicated `get` of `efold_value`, so both resumes opened with a
  `replication_in_flight` record. Each time the package found every shard already holding what the
  controlling shard held, repaired nothing and cleared the record. A `get` that found its rows
  writes none, so this is the benign case, not a repair of divergent shards.
- **Ray records a `SIGKILL`ed driver's job as `SUCCEEDED`** (`04000000`), as ChamPBH saw. The
  registry's `stale`, not Ray's job status, is what told of the kill.
- **`end`'s write stamps `heartbeat`.** After `end` the lost status's `heartbeat` is the `end`'s
  time (16:15:16), not the last beat (16:14:02, kept in `ended.evidence.heartbeat`). A reader who
  wants the last beat of a lost run reads `ended.evidence`.
- **The load during `reference`** came largely from processes outside SI (§1.1), and it made that
  build 3 to 6 times slower than RH2's. It also shifted `resumed-a`'s pace against `reference`'s,
  which is why the narrow window was missed. The wide window held and the protocol needs no
  retune, but a delay chosen from one build's timestamps assumes a steady load.

### 1.13 The commands, verbatim

From the repository root. `<scratch>` is my scratch directory
(`/private/tmp/claude-35086/-Users-ds283-Documents-Code-StochasticInstantons/52f41163-0fa6-4f34-86f5-bca5f365b9e9/scratchpad/orch04-agent/`).
The scripts there are committed as text: [`04-wait_for_line.py.txt`](out/04-wait_for_line.py.txt),
[`04-kill_when.py.txt`](out/04-kill_when.py.txt) with [`04-kill_when.diff`](out/04-kill_when.diff),
[`04-check.py.txt`](out/04-check.py.txt), [`04-ray_state.sh.txt`](out/04-ray_state.sh.txt) and
[`04-rows.py.txt`](out/04-rows.py.txt). The committed logs have ANSI colour codes removed (`sed -E
's/\x1b\[[0-9;]*m//g'`) and are otherwise verbatim; the `.json` files are copied unchanged.

```bash
# the gate (each status alone in its Bash call, output to a file)
.documents/dk-and-rpk-migration/rehearsal/ray_cluster.sh status > <scratch>/gate-status-2.txt 2>&1
./venv/bin/python -m runregistrykit list
./venv/bin/pip freeze > <scratch>/pip-freeze-before.txt
shasum -a 256 main.py
git diff 1c223e8 --stat -- main.py plot_InstantonSolutions.py plot_GradientCoupledSolutions.py utilities.py

# the suites before
./venv/bin/python -m pytest -m "not integration and not slow" -q -p no:cacheprovider > <scratch>/suite-default-before.txt 2>&1
RAY_ADDRESS=local ./venv/bin/python -m pytest -m integration -q -p no:cacheprovider > <scratch>/suite-integration-before.txt 2>&1

# the cluster
.documents/dk-and-rpk-migration/rehearsal/ray_cluster.sh start "rrk-adoption 04 (R)" > <scratch>/start.txt 2>&1
.documents/dk-and-rpk-migration/rehearsal/ray_cluster.sh status > <scratch>/status-1-baseline.txt 2>&1
./venv/bin/ray status --address 127.0.0.1:6390
bash <scratch>/ray_state.sh "1 baseline, after start"
./venv/bin/python -c 'import signal, ray; a = signal.getsignal(signal.SIGTERM); ray.init(address="127.0.0.1:6390"); b = signal.getsignal(signal.SIGTERM); print("before", a); print("after", b, getattr(b, "__module__", None), getattr(b, "__qualname__", None)); ray.shutdown()'
./venv/bin/ray list jobs --address 127.0.0.1:6390
mkdir -p var/rrk-adoption-04

# H1 (the launch line of §1.10), then one Bash call: the registration wait, the one check, the end wait
./venv/bin/python <scratch>/wait_for_line.py var/rrk-adoption-04/reference.log ">> registered_run: registered as" --timeout 120 --echo
./venv/bin/python <scratch>/check.py reference
./venv/bin/python <scratch>/wait_for_line.py var/rrk-adoption-04/reference.log "** launcher saw exit status" --timeout 420 --echo
./venv/bin/python .documents/dk-and-rpk-migration/rehearsal/stage_counts.py var/rrk-adoption-04/reference.log
./venv/bin/python -m runregistrykit list
.documents/dk-and-rpk-migration/rehearsal/ray_cluster.sh status > <scratch>/status-2-after-H1.txt 2>&1
bash <scratch>/ray_state.sh "2 after H1"
./venv/bin/python -m runregistrykit store create var/datastores/rrk-adoption-04-reference.sqlite --purpose "rrk-adoption 04 H1: the reference build of the rehearsal grid, kept for the user"
./venv/bin/python -m runregistrykit store fingerprint var/datastores/rrk-adoption-04-reference.sqlite --write
./venv/bin/python -m runregistrykit store show var/datastores/rrk-adoption-04-reference.sqlite
./venv/bin/python <scratch>/rows.py var/datastores/rrk-adoption-04-reference

# H2 (the launch line of §1.10, with interrupt_when.py), then the waits and the check as for H1, then
./venv/bin/python .documents/dk-and-rpk-migration/rehearsal/stage_counts.py var/rrk-adoption-04/resumed-a.log
./venv/bin/python <scratch>/rows.py var/datastores/rrk-adoption-04-resumed
.documents/dk-and-rpk-migration/rehearsal/ray_cluster.sh status > <scratch>/status-3-after-H2.txt 2>&1
bash <scratch>/ray_state.sh "3 after H2"
./venv/bin/python -m runregistrykit store create var/datastores/rrk-adoption-04-resumed.sqlite --purpose "rrk-adoption 04 H2-H4: the rehearsal grid built by resumes after SIGTERM and SIGKILL, kept for the user"
./venv/bin/python -m runregistrykit store show var/datastores/rrk-adoption-04-resumed.sqlite

# H3 (the launch line of §1.10, with kill_when.py), then the waits and the check as for H1, then
.documents/dk-and-rpk-migration/rehearsal/ray_cluster.sh status > <scratch>/status-4-after-kill.txt 2>&1
bash <scratch>/ray_state.sh "4 straight after H3's SIGKILL"
./venv/bin/ray list actors --address 127.0.0.1:6390 --limit 1000 --format json
kill -0 26796
cat var/runs/rrk-adoption-04-resumed-b-20261025T161352/status.json
./venv/bin/python -m runregistrykit list
ls -la var/datastores
./venv/bin/python <scratch>/rows.py var/datastores/rrk-adoption-04-resumed
find var/runs | sort > <scratch>/runs-find-before-refusal.txt
.documents/rrk-adoption/rehearsal/build_registered.sh resumed resumed-c 127.0.0.1:6390 "rrk-adoption 04 H4: the last resume of the resumed store, straight through" resumed-c-refused
./venv/bin/python <scratch>/wait_for_line.py var/rrk-adoption-04/resumed-c-refused.log "** launcher saw exit status" --timeout 120
find var/runs | sort > <scratch>/runs-find-after-refusal.txt
diff <scratch>/runs-find-before-refusal.txt <scratch>/runs-find-after-refusal.txt
kill -0 26796
./venv/bin/python -m runregistrykit end rrk-adoption-04-resumed-b-20261025T161352 --reason "SIGKILLed on purpose by rrk-adoption 04 to rehearse the hard-kill route"
./venv/bin/python -m runregistrykit list

# H4 (the launch line of §1.10), then the waits and the check as for H1, then
./venv/bin/python .documents/dk-and-rpk-migration/rehearsal/stage_counts.py var/rrk-adoption-04/resumed-c.log
./venv/bin/python -m runregistrykit list

# H5
PYTHONPATH=. ./venv/bin/python tools/compare_stores.py --json <scratch>/compare-reference-resumed.json var/datastores/rrk-adoption-04-reference.sqlite var/datastores/rrk-adoption-04-resumed.sqlite
PYTHONPATH=. ./venv/bin/python tools/compare_stores.py --json <scratch>/compare-reference-11reference.json var/datastores/rrk-adoption-04-reference.sqlite ~/ScienceData/StochasticInstantons-rehearsals/dk-and-rpk-migration/11-reference.sqlite
./venv/bin/python -m runregistrykit store fingerprint var/datastores/rrk-adoption-04-reference.sqlite
./venv/bin/python -m runregistrykit store fingerprint var/datastores/rrk-adoption-04-resumed.sqlite
./venv/bin/python -m runregistrykit store show var/datastores/rrk-adoption-04-reference.sqlite
./venv/bin/python -m runregistrykit store show var/datastores/rrk-adoption-04-resumed.sqlite
./venv/bin/python <scratch>/rows.py var/datastores/rrk-adoption-04-resumed

# the stop and the suites after
.documents/dk-and-rpk-migration/rehearsal/ray_cluster.sh stop > <scratch>/stop.txt 2>&1
.documents/dk-and-rpk-migration/rehearsal/ray_cluster.sh status > <scratch>/status-5-after-stop.txt 2>&1
./venv/bin/python -m pytest -m "not integration and not slow" -q -p no:cacheprovider > <scratch>/suite-default-after.txt 2>&1
RAY_ADDRESS=local ./venv/bin/python -m pytest -m integration -q -p no:cacheprovider > <scratch>/suite-integration-after.txt 2>&1
./venv/bin/pip freeze > <scratch>/pip-freeze-after.txt
cmp <scratch>/pip-freeze-before.txt <scratch>/pip-freeze-after.txt
```

---

## 2. RunRegistryKit's two gate records, drafted (prompt 05, 2026-10-25)

Added by `rrk-adoption` prompt 05. Nothing above this heading has been changed.

The campaign's plan (README P13) has RunRegistryKit's two gates for SI recorded there, by the user,
from drafts made here, as `dk-and-rpk-migration` did for its packages' boards
(`.documents/dk-and-rpk-migration/verification.md` §4.3), and as ChamPBH drafted its two
(`.documents/rrk-adoption-verification.md` §2 there, at ChamPBH `58c1c93`). **Neither cell is
committed in RunRegistryKit. Nothing was written in that repository, and the user makes those
commits, or has a session there make them.** Each draft below is the text of **the second column**
of one board row, ready to paste, in the form of the rows those boards already hold for
SecondaryGWKit (`| **G<n>** | **holds** <date>: … |`, one line each). The rows are read at
RunRegistryKit's `main`, `70ee1e8` (`v0.2.0` is `0bae3a3`), through `git show` only:

- **`prompts/extraction/IMPLEMENTATION_STATE.md` §2, row `G4`**, at `:1130`, which reads `| **G4** |
  not yet (SI adopts, after its `dk-and-rpk-migration`); its checklist is
  [`docs/adoption/stochasticinstantons.md`](../../docs/adoption/stochasticinstantons.md) (07,
  `aaab408`) |`. Its first column, `**G4**`, stays. The form is `G2` (SGK) at `:1128`. The draft takes
  the checklist's item 9 (`docs/adoption/stochasticinstantons.md` at `v0.2.0`), point by point, and
  keeps the checklist link of the row's old text at its end.
- **`prompts/interrupted-runs/IMPLEMENTATION_STATE.md` §2, row `G3`**, at `:1182`, which reads `|
  **G3** | not yet (SI adopts) |`. Its first column stays. The form is `G1` (SGK) at `:1180`. The
  draft goes through the six checks of the `v0.2.0` adoption note, `docs/adoption/v0.2.0/README.md`
  §3 (the SI note, `docs/adoption/v0.2.0/stochasticinstantons.md` §1, says each "applies to what it
  writes when it adopts"), then its §2 and the route after a hard kill (its §4).

**Where the rows differ from the prompt's reading.** The two boards were read at `main`, not at the
tag: at `v0.2.0` the `interrupted-runs` board's `G1` reads "not yet", and SGK's record is on `main`
only. The checklist, the `v0.2.0` note and `docs/adoption/v0.2.0/README.md` are at `v0.2.0` (they are
the same at `main`: since the tag, `docs/adoption/` changed only in its top-level `README.md`). The
rows for ChamPBH, `G3` at `:1129` and `G2` at `:1181`, still read "not yet": the user has not yet
committed ChamPBH's drafts.

**What the drafts leave out, and what is the user's to bring up to date when recording them.**
- **No "Read here" clause.** In SGK's rows that clause is the reading the recording session made in
  RunRegistryKit. The session that records these adds its own.
- **The date is the campaign's close**, 2026-10-25.
- **Both say the branch `rrk-adoption` is not merged into `main`.** If the merge has been made by
  the time of recording (README R7), say so, with its commit.
- **The pin was added, not moved.** SI never pinned `v0.1.0`, so the move of the `v0.2.0` note's §1
  (`v0.1.0` to `v0.2.0`) did not arise: `git log -S runregistrykit -- requirements.txt` gives one
  commit, `60687f0`, which changes `requirements.txt` alone, by one inserted line. The `G3` draft
  says "added at `v0.2.0`, in a commit of its own".
- **The checklist's item 9 has six points.** Point 4 (the helper) does not apply, by R3, and point
  6 is the record itself.
- **No SI commit of prompt 05 is named.** 05's own commit adds the documents and one docstring
  sentence in `utilities.py` (point 4 below says what is true of the file at `39fc819`).

**Checks made for the drafts**, from the repository root, with RunRegistryKit and ChamPBH read only
(`git show`, `git log`, `git grep`), at `HEAD` `085f45f` plus this prompt's documents:

```text
$ git log --format=%h -S runregistrykit -- requirements.txt         # the commits that add or remove the name
60687f0
$ git show 60687f0 --stat --format=%h | tail -2; git show 60687f0 -- requirements.txt | grep '^[+-]'
 requirements.txt | 1 +
 1 file changed, 1 insertion(+)
+runregistrykit[stores] @ git+https://github.com/ds283/RunRegistryKit@v0.2.0
$ sed -n 63p requirements.txt
runregistrykit[stores] @ git+https://github.com/ds283/RunRegistryKit@v0.2.0
$ git diff 1c223e8 39fc819 -- main.py plot_InstantonSolutions.py plot_GradientCoupledSolutions.py utilities.py | wc -l
0
$ cat venv/lib/python3.13/site-packages/runregistrykit-0.2.0.dist-info/direct_url.json
{"url": "https://github.com/ds283/RunRegistryKit", "vcs_info": {"commit_id": "0bae3a3c501a8264ee4be5bc24f06422af38720f", "requested_revision": "v0.2.0", "vcs": "git"}}
```

The six checks of the `G3` draft are `git grep` over SI's tracked tree, excluding `.prompts/` and
`.documents/`:

```text
## 1. a comparison with liveness's values
$ git grep -n -i -E 'liveness|"foreign"|'foreign'|"stale"' -- . :!.prompts :!.documents
.claude/rules/run-registry.md:19:2. **Liveness.** A run is alive iff its pid answers `kill -0` **and** its heartbeat is inside the
.claude/rules/run-registry.md:61:- `pgrep -f` (or any command-line match) as a liveness test.
tests/test_inventory_specs.py:455:    excluded = dict(EXCLUDED, FullInstantonValue="stale")
## 2. TERMINAL_STATES, and its fourth value
$ git grep -n -E 'TERMINAL_STATES' -- . :!.prompts :!.documents
$ git grep -n -w -E 'lost' -- . :!.prompts :!.documents (hits that name a run's state only)
.claude/rules/run-registry.md:39:   recorded `lost`.
notes/onion-model/onion_model.tex:1919:the response fields is lost, together with the one-multiply reinstatement
tests/test_registered_run_outcomes.py:238:        assert read_json(dead / "status.json")["state"] == "lost"
## 3. a store refusal's text
$ git grep -n -E 'Run\.finish|names this store|is running|runregistrykit end' -- . :!.prompts :!.documents
.claude/rules/run-registry.md:38:   `./venv/bin/python -m runregistrykit end RUN_ID --reason TEXT` on the host it ran on. The run is
.claude/rules/run-registry.md:43:A run stopped by `SIGTERM` needs no `end`: the wrapper records it `killed`. `Run.finish` is never
RunDrivers/registered_run.py:88:with `python -m runregistrykit end` (`.claude/rules/run-registry.md`, the route after a hard kill).
RunDrivers/registered_run.py:98:refused by `begin`, whose text names `python -m runregistrykit end`; nothing is created.
tests/test_registered_run_outcomes.py:170:    one `!! ` line naming `python -m runregistrykit end`, and nothing created. Once that run is
tests/test_registered_run_outcomes.py:228:        assert_one_refusal_line(refused, "python -m runregistrykit end")
## 4. a test that begins two unfinished runs on one store
$ git grep -n -E 'runregistrykit\.begin\(' -- '*.py' ':!.prompts' ':!.documents'
RunDrivers/registered_run.py:819:        run = runregistrykit.begin(
tests/test_registered_run_outcomes.py:68:run = runregistrykit.begin(
tests/test_registered_run_signals.py:85:        return runregistrykit.begin(
tests/test_registered_run_streams.py:158:        self.run = runregistrykit.begin(
## 5. a caller of pid_alive
$ git grep -n pid_alive -- . :!.prompts :!.documents
## 6. a test that pins a record's key set
$ git grep -n -E '(set|sorted|list)\(.*(manifest|status)|(manifest|status)[a-z_]*\.keys\(\)|"host"|"ended"|EXPECTED_KEYS' -- tests RunDrivers config
tests/registered_run_helpers.py:82:MANIFESTS_AT_START = sorted(_glob.glob({manifests!r}))
tests/test_registry_config.py:23:  deliberate one, so the test holds the exact set of keys: prompt 02 extends `EXPECTED_KEYS` with
tests/test_registry_config.py:45:EXPECTED_KEYS = {"runs_root", "stores_root", "distributions", "stores"}
tests/test_registry_config.py:59:    assert set(config) == EXPECTED_KEYS
```

Only `.claude/rules/run-registry.md` (prose), `RunDrivers/registered_run.py` (two comment lines in its
docstring) and the campaign's own tests name any of it, and each was written for `v0.2.0`.

### 2.1 `extraction` board, row `G4`

```text
| **G4** | **holds** 2026-10-25: SI adopted `v0.2.0` directly, with the store layer, in a campaign of its own, `rrk-adoption` (branch `rrk-adoption`, cut from `main` at `1c223e8`; **not merged into `main` when this was drafted**), and the checklist's item 9 has six points, of which four hold, one does not apply and one is this record. (1) **The pin and the venv**, SI `60687f0`: `requirements.txt:63` holds `runregistrykit[stores] @ git+https://github.com/ds283/RunRegistryKit@v0.2.0`, the one line the commit adds (`datastorekit` at `:16`, `v0.5.0`, and `raypoolkit` at `:59`, `v0.3.0`, are not touched by it); the venv was installed from the file, `pip show runregistrykit` gives 0.2.0, and its `direct_url.json` names `0bae3a3c501a8264ee4be5bc24f06422af38720f` with `requested_revision` `v0.2.0` and no `dir_info`, so it is not editable (the venv's `pip freeze` changed by that one line and `pip check` was clean, SI's 01 results note). (2) **The config and `var/`**, SI `7071bb8`: `runregistrykit.toml` at SI's root holds `runs_root = "var/runs"`, `stores_root = "var/datastores"` and `distributions = ["datastorekit", "raypoolkit"]`, with `[stores] fingerprinter = "config.fingerprint:fingerprinter"` added by `0fcaf7c`; `.gitignore:23` is `var/`, and `git check-ignore` matches `var/runs/x` (`var/datastores/x.sqlite` is also ignored by the older `*.sqlite` rule, so the test's first path carries the check). (3) **A run is listed, with its `packages`**, SI `29705f2` (a rehearsal on SI's isolated Ray cluster, 2026-10-25): `python -m runregistrykit list` lists four runs, begun and finished through SI's wrapper `RunDrivers/registered_run.py` (`16e1cc1`): `rrk-adoption-04-reference-20261025T160704` `done`/0, `rrk-adoption-04-resumed-a-20261025T161131` `killed`/143, `rrk-adoption-04-resumed-b-20261025T161352` `lost` and `rrk-adoption-04-resumed-c-20261025T161521` `done`/0, none `running` or stale; each manifest, committed under `.documents/rrk-adoption/out/04-<slug>.manifest.json`, has `packages` naming `runregistrykit` 0.2.0 (`0bae3a3c…`), `datastorekit` 0.5.0 (`f47b9a25…`) and `raypoolkit` 0.3.0 (`67a75b97…`), each `editable: false`, the config's `distributions` beside the registry itself. (4) **The helper is not substituted, so this point does not apply**: SI kept `utilities.installed_package_provenance` (ruled by the user, R3, 2026-10-23: substituting it would make `main.py` and both plot scripts import `runregistrykit`, against the ruling that they stay launchable without it), so `measure_client_registry.py` was not run; `main.py`, `plot_InstantonSolutions.py`, `plot_GradientCoupledSolutions.py` and `utilities.py` are byte-identical to `1c223e8`, where the branch was cut, at `39fc819` (`git diff 1c223e8 39fc819 -- <the four>` is empty), and the only code outside the tests that imports the package is `RunDrivers/registered_run.py` (inside its `register`) and `config/fingerprint.py` (which the registry loads from the config, and which neither `main.py` nor a plot script imports); the wrapper runs `main.py` unchanged, by `runpy`. (5) **The store layer**: the config's fingerprinter loads (SI `0fcaf7c`: `tests/test_store_fingerprint_golden.py`, `TestConfigFingerprint`, in the default selection, beside the Q5 guard `tests/test_fingerprint_format_guard.py`, 5 tests, which pins the 24 `(class, spec digest)` pairs of format 1 and names the class that changes, and a golden fingerprint `tests/data/store_fingerprint_rrk-adoption-02.json`, digest `e3437a9b2f16415f5635ee121fa7f09d07ac74c30400d5973a3afaeec8fc7c78`, written once from two identical builds and never overwritten), and `python -m runregistrykit store fingerprint` reads a closed store (`0fcaf7c`, `TestCommandLine`, on the harness's store, exit 0; and `29705f2`, `.documents/rrk-adoption/out/04-store.txt`: the reference store `rrk-adoption-04-reference.sqlite` and the resumed store `rrk-adoption-04-resumed.sqlite` each give the digest `a9f716fb88cf8647327748e533e7402e6f406a59aba3826956e966b7f9081ea7`, format 1, and each "matches" the fingerprint its sidecar records; the resumed store's was written into its sidecar by the run `resumed-c` itself, `fingerprint_sidecar` `written`). (6) **This record.** Beyond the checklist: the wrapper that registers a `main.py` run and leaves `main.py` unchanged (SI `16e1cc1`, 106 tests, 104 in the default selection and 2 `integration`), the hard-kill route rehearsed (`29705f2`; the `interrupted-runs` board's `G3`), and the resumed store and SI's earlier `dk-and-rpk-migration` reference `11-reference` each equal to `reference` in every stored science column, by `tools/compare_stores.py` (`RESULT: equal`, timestamps and JSON timing keys aside). SI's suites at the close of 04: default 848 (847 passed, 1 skipped) and `integration` 72 (71 passed, 1 skipped), unmoved from before the rehearsal. **No defect of the package was met.** SI's record is `.documents/rrk-adoption/verification.md` §1 to §3 and the results notes 01 to 05 (campaign `rrk-adoption`), and its handover to the user is §3 there. Its checklist is [`docs/adoption/stochasticinstantons.md`](../../docs/adoption/stochasticinstantons.md) (07, `aaab408`) |
```

### 2.2 `interrupted-runs` board, row `G3`

```text
| **G3** | **holds** 2026-10-25: SI adopted `v0.2.0` directly, with the store layer, in a campaign of its own, `rrk-adoption` (branch `rrk-adoption`, cut from `main` at `1c223e8`; **not merged into `main` when this was drafted**). **The pin was added at `v0.2.0`, in a commit of its own:** SI `60687f0` (2026-10-23) changes `requirements.txt` alone, by one inserted line (`:63`, `runregistrykit[stores] @ git+https://github.com/ds283/RunRegistryKit@v0.2.0`; `git log --format=%h -S runregistrykit -- requirements.txt` gives `60687f0` alone, and it is the one commit of the campaign to touch the file). SI never pinned `v0.1.0`, so the `v0.1.0` to `v0.2.0` move of the `v0.2.0` note's §1 did not arise. The venv then held `runregistrykit` 0.2.0 at `0bae3a3c…`, `requested_revision` `v0.2.0`, not editable, and `datastorekit` 0.5.0 and `raypoolkit` 0.3.0 unmoved. **The six checks of [`docs/adoption/v0.2.0/README.md`](../../docs/adoption/v0.2.0/README.md) §3** apply to what SI wrote when it adopted, since none of its code predates the adoption (`git grep` over SI's tracked tree at its close, excluding `.prompts/` and `.documents/`): (1) a comparison with `liveness`'s values: none; `liveness` is named in SI's code and rules only in prose (`.claude/rules/run-registry.md`), nothing compares a run's liveness with `foreign` or `stale` (the one string `"stale"`, `tests/test_inventory_specs.py:455`, is a fixture's reason for an excluded class); (2) `TERMINAL_STATES`: named nowhere; the wrapper names the states it records, `done`, `failed` and `killed`, as arguments of `finish`, keeps no list of terminal states, and the one test that names the fourth, `lost`, asserts that `end` records it (`tests/test_registered_run_outcomes.py:238`); (3) a store refusal's text: `Run.finish`, `names this store` and `is running` are matched nowhere (`Run.finish` appears once, in `.claude/rules/run-registry.md`, in a sentence saying it is never called by hand), and the one test that matches a refusal, `tests/test_registered_run_outcomes.py` `TestBeginsRefusal.test_refused_then_accepted_after_end`, was written for `v0.2.0`: it asserts the fragment `python -m runregistrykit end`, the dead run's name and `No run directory was created`; (4) a test that begins two unfinished runs on one store: none: `runregistrykit.begin(` is called in the wrapper and in three test modules, each test beginning one run in a fresh temporary runs root, except `TestBeginsRefusal`, which begins a second on a store an unfinished run names precisely to assert the refusal, then `end`, then the acceptance; all 106 tests of `tests/test_registered_run*.py` pass under `v0.2.0` (SI `16e1cc1`), run three times in a row; (5) a caller of `pid_alive`: none (`git grep pid_alive` finds nothing); (6) a test that pins a record's key set: none pins a manifest's or a status's keys (`tests/test_registry_config.py` pins the config's four keys, `EXPECTED_KEYS`; the wrapper's tests read named fields). **§2 of that README holds trivially**: SI has one checkout, and `git worktree list` shows it alone, so no checkout shares a runs root with another. **§4, the route for a hard-killed run, was rehearsed** on SI's isolated Ray cluster (SI `29705f2`, H3, 2026-10-25): `rrk-adoption-04-resumed-b-20261025T161352` was `SIGKILL`ed 10 s into `STAGE 3: SLOW-ROLL INSTANTONS` (16:14:12) and `list` showed it `stale` with `!!`, with nothing left in Ray; the next registration on its store (a launch of `resumed-c`) was refused, exit 2, with one `!! ` line saying that run `rrk-adoption-04-resumed-b-20261025T161352` "is running (stale, pid 26796) and names this store", naming `python -m runregistrykit end RUN_ID --reason TEXT` and ending `No run directory was created` (`find var/runs` unchanged by `diff`); `end … --reason …` was accepted, "now lost, verified: its pid 26796 does not answer kill -0 on this host", and `list` showed it `lost`; then `rrk-adoption-04-resumed-c-20261025T161521`, begun on the same store, ran to `done` (exit 0), computed only the 20 rows missing, wrote its fingerprint into the sidecar (`fingerprint_sidecar` `written`, digest `a9f716fb…1ea7`), and its store compares equal to the reference's by `tools/compare_stores.py` (`RESULT: equal`). SI's wrapper's own `TestBeginsRefusal` shows the same refusal and `end` on a `SIGKILL`ed child. **No defect of the package was met**; neither `[04-a-killed-process-not-yet-reaped-answers-kill-0]` nor `[03-a-run-whose-manifest-cannot-be-read-names-no-store]` was: SI's launcher waits on the driver (`bash` reaps it), so `end` was not refused by an unreaped process, and every run's `status.json` was readable. SI's record is `.documents/rrk-adoption/verification.md` §1 (the rehearsal, §1.7 the route) to §3, and the results notes 01 to 05 (campaign `rrk-adoption`) |
```

### 2.3 What the drafts do not claim

- **Nothing about RunRegistryKit's own tests or CI.** The package's suite on SI's venv was run once, at
  01, and is in 01's results note; it is not a clause of either draft.
- **Nothing about a production run.** Those are the user's. The rehearsal's grid is
  `quadratic-minimal.yaml` with `--targets homogeneous`: it builds no gradient branch (U11 of
  `dk-and-rpk-migration`), so no `GradientCoupledInstanton` row was written under the registry, and a
  gradient-branch run that outlives the staleness window while it works is described in §3 and not
  rehearsed.
- **The hard-kill route is rehearsed with the launcher's `bash` as the driver's parent**, which reaps
  the driver, so `end` was not refused by an unreaped process. A launch that does not reap it is read,
  not rehearsed.
- **The `SIGTERM` handling is measured on Ray 2.55.1 attached to SI's external cluster** (P9), not on a
  Ray the driver started itself.
- **The store layer's golden fingerprint is of the test harness's store**, which has no row of
  `store_tag`, `redshift` or `IntegrationSolver` (02, deviation 8); the two `var/` stores are of the
  rehearsal grid, whose gradient tables are empty.
- **`git_dirty` is `true` in every manifest of 04** (§1.9): an untracked directory of the prompt's own
  counted as dirty.

---

## 3. The handover to Phase 2 (prompt 05, 2026-10-25)

This section adds to `.documents/dk-and-rpk-migration/verification.md` §4.5, Phase 2's handover, by
statement. It does not edit it: everything §4.5 says stands, and what follows is what a build now
also does.

- **A build is launched through the wrapper**, from the repository root, never a bare `main.py` when
  its record matters (`CLAUDE.md`, "Long-running jobs — the run registry"):
  ```bash
  PYTHONPATH=. ./venv/bin/python RunDrivers/registered_run.py --campaign C --prompt N \
      --register SLUG --purpose "one line" -- <main.py's arguments>
  ```
  - **The four flags** are all required. `--campaign` names the work (for Phase 2, for example
    `fullinstanton-hamiltonian`); `--prompt` the prompt of the launch, and the resuming launch of an
    interrupted build gets its own; `--register SLUG` names the run and **matches `--job-name`**
    (04's launcher used `rrk-adoption-04-<slug>`); `--purpose` is one line. `main.py`'s arguments
    follow the bare `--`, verbatim.
  - **Detached**: `nohup` and `disown` (`setsid` is not on macOS), with the launching shell's own
    output redirected to a log under `var/`, and the pid written at once. 04's launcher,
    `.documents/rrk-adoption/rehearsal/build_registered.sh`, is a working example of the whole
    (§1.10); it is 04's, with its own fixed arguments, and a Phase 2 build writes its own.
  - **The database goes under `var/datastores/`** (R6). The wrapper records it, made absolute, as
    the run's `results`.
  - **A cluster** is `ray_cluster.sh start PURPOSE` under the shared rehearsal lock, then
    `--ray-address 127.0.0.1:6390` (`CLAUDE.md`); never `ray stop`. The registry does not start or
    stop one.
  - **Do not babysit.** Launch, check once that it started, end the turn (`.claude/rules/run-registry.md`,
    rule 4). The wrapper's last stdout line is `** driver exit status N`.
- **After a store's first close**, a person makes its sidecar: `./venv/bin/python -m runregistrykit
  store create var/datastores/<store>.sqlite --purpose "…"`. Nothing in the code does (R4). Do it
  before the next run on the store: a run begun after that carries the store's `store_id`
  (`results_store_id`), and the wrapper then writes the fingerprint into the sidecar at the end of
  the run. `store fingerprint PRIMARY` reads a closed store; `--write` records it.
- **After a hard kill** (`SIGKILL`, a power loss, the OOM killer), the run is `stale`, `!!` in
  `list`, and any launch on its store is refused with nothing created. A person checks the run is
  over, then `./venv/bin/python -m runregistrykit end RUN_ID --reason TEXT`, on the host it ran on;
  the run is `lost`. Then the same build again, with the `--prompt` of the resuming launch: the open
  prunes unvalidated rows by default, so it needs no flag. A run stopped by `SIGTERM` or `SIGINT`
  needs no `end`; the wrapper records `killed`/143 or 130. Rehearsed in 04, §1.7.
- **The plot scripts and `main.py --inventory` stay unregistered** (R5). The wrapper refuses
  `--inventory`.
- **A gradient-branch build may show `stale` while it works** (P7). A queue whose items each print
  nothing for longer than 900 s is reported stale, and the branch's solves have run for hours. That
  means go and look (`list --stale-after SECONDS` widens the reader's window), never kill, and never
  `end` a run whose pid still answers.
- **04's stores and runs are kept under `var/`**, ignored by git, until the user removes them: the
  stores `var/datastores/rrk-adoption-04-reference.sqlite` and `…-resumed.sqlite` (10 shards each)
  with their sidecars; the four run directories under `var/runs/`; and the launch logs, pid files and
  signallers' logs under `var/rrk-adoption-04/`. `list` shows the four runs. Never `git clean -x` or
  `-X`, which would delete them.
- **What Phase 2 needs from the registry**: nothing is required of a prompt but the habit
  (`./venv/bin/python -m runregistrykit list` at the start of a session and before launching
  anything long). A store a Phase 2 build makes is new, and gets a sidecar after its first close.
