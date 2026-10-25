# 04 — rehearse registered runs

**Subject:** Rehearse registered runs on SI's isolated cluster: four builds through the wrapper, a
`SIGTERM` and a `SIGKILL`, the hard-kill route, the resume and the stores compared
**Commit:** this commit, on branch `rrk-adoption`, on top of `535b7e7`
**Date:** 2026-10-25, 15:42 (the gate's stop) and 16:00–16:21 GMT (the rehearsal), by Claude Opus 5.5
**Result:** **COMPLETE.** H0–H6 done; the gate **R** holds.
- **The four builds were recorded as planned:**
  - `reference` `done`/0;
  - `resumed-a` `killed`/143 (`SIGTERM`);
  - `resumed-b` `running`, then `stale` and `!!` after its `SIGKILL`; a launch on its store was
    refused with nothing created; `end` recorded it `lost`;
  - `resumed-c` `done`/0, computing only the 20 rows missing.

  Every manifest was written before `main.py`'s first line, and every `results_store_id` is what
  correction 13 rules.
- **The stores.** `compare_stores` gives `RESULT: equal`, bookkeeping aside, for the reference
  against the resumed store and for the reference against RH2's `11-reference`. The two `var/`
  stores' fingerprints are one digest, `a9f716fb88cf8647327748e533e7402e6f406a59aba3826956e966b7f9081ea7`.
- **P9, measured.** Ray 2.55.1, attached to the external cluster, installs its own Python
  `SIGTERM` handler, and the wrapper's replaces it. The `SIGTERM`ed driver exited 143 (RH2's
  unregistered one exited 15), with no absl `*** SIGTERM received` banner and no `** cancelled an
  alarm` line.
- **Nothing left behind.** Nothing outlived the `SIGKILL` in Ray. The cluster was stopped by the
  script, exit 0, and the lock is free.
- **The suites** before and after: 848 (847 passed, 1 skipped) and 72 (71 passed, 1 skipped), the
  baselines. `pip freeze` unchanged.
- **The stop at the gate.** The rehearsal ran after a stop at the gate (15:42: `~/ScienceData`
  absent). The user restored it from a backup, and the orchestrator lifted the stop (deviation 19).
- No code changed, and no issue is opened.

Prompt: [`.prompts/rrk-adoption/04-rehearse-registered-runs.md`](../../.prompts/rrk-adoption/04-rehearse-registered-runs.md).
The orchestrator's brief for 04 governed where it differs from the prompt. Its 18 corrections are
classified below. The record of the rehearsal is [`verification.md`](verification.md) §1; its
outputs are [`out/04-*`](out/). The stores, run records and launch logs stay in `var/` (ignored),
for the user. Scratch scripts and their outputs were kept in the session scratchpad
(`orch04-agent/`); the scripts are committed as text under `out/`.

## What shipped

- **H0 — the launcher**, [`rehearsal/build_registered.sh`](rehearsal/build_registered.sh), after
  `dk-and-rpk-migration`'s `build.sh`, with its licence header and a header naming this prompt.
  - **Usage:** `build_registered.sh STORE BUILD ADDRESS PURPOSE [LAUNCH]`, from the root.
  - **What it runs:** `PYTHONPATH=. ./venv/bin/python -u RunDrivers/registered_run.py --campaign
    rrk-adoption --prompt 04 --register BUILD --purpose PURPOSE -- --config quadratic-minimal.yaml
    --database $S/rrk-adoption-04-STORE.sqlite --job-name rrk-adoption-04-BUILD --targets
    homogeneous --n-collocation-points 5 --alpha-regularization 0.01 --ray-address ADDRESS`, with
    `S=$PWD/var/datastores` and the launch files in `$PWD/var/rrk-adoption-04/LAUNCH.{log,pid}`.
  - **How it detaches.** It **detaches itself**: after its checks it runs `nohup bash -c
    '<runner>' … > /dev/null 2>&1 < /dev/null &` and `disown`, and returns at once. The runner
    launches the driver with its output to the log, writes `$!` to the pid file at once, `wait`s on
    it (so a killed driver is reaped), and appends `** launcher saw exit status N`.
  - **What it does not do.** It writes no `** driver exit status` line and starts no cluster.
  - **Its refusals.** Each is one `!! ` line, exit 2: an argument count other than four or five
    (the usage), a bad slug, an empty address or purpose, a run from outside the root, a missing
    `var/datastores/`, and an existing log.
  - `bash -n` passes.
- **H1–H4** — the four builds, and the refused launch, as [`verification.md`](verification.md)
  §1.3–§1.8 records them.
- **H5** — the two comparisons, both fingerprints and both `store show`s (§1.8).
- **H6** — [`verification.md`](verification.md), new, §1. Its subsections:
  - §1.0, the stop at the gate and its resolution;
  - §1.1, the cluster and the load, with `start`, `ray status` and `stop`;
  - §1.2, the probe; §1.3, the four builds, as a table;
  - §1.4, the heartbeat; §1.5, the two delays; §1.6, the signal;
  - §1.7, the hard-kill route, line by line; §1.8, the resume and the stores;
  - §1.9, `git_dirty`; §1.10, the launcher and the launch lines;
  - §1.11, the suites; §1.12, the observations; §1.13, the commands verbatim.
- **[`out/04-*`](out/)**, 34 files, 308 KB in all, the largest 55 KB (`04-cluster.txt`):
  - the five launch logs, ANSI codes removed;
  - `04-resumed-a.interrupt.log` and `04-resumed-b.kill.log`;
  - each run's `manifest.json` and `status.json`, whole;
  - `04-checks.txt` (the four checks, every `list`, the status before `end`, `end`);
  - `04-waits.txt` (the waiters' line arrival times);
  - `04-refusal.txt`, `04-stage-counts.txt`, `04-store.txt` (every `store` command whole);
  - `04-compare-reference-resumed.{txt,json}` and `04-compare-reference-11reference.{txt,json}`;
  - `04-rows.txt`;
  - `04-cluster.txt` (both gates' status, `start`, the five points, `ray status`, `stop`, status
    after);
  - `04-probe-p9.txt`, `04-suites.txt`;
  - the scratch scripts as text: `04-wait_for_line.py.txt`, `04-kill_when.py.txt` with
    `04-kill_when.diff`, `04-check.py.txt`, `04-ray_state.sh.txt`, `04-rows.py.txt`.
- **The board:** row 04 landed, H0–H6 done, the gate **R** held, `### 5.6 After prompt 04
  (2026-10-25)`, and the header at 4 of 5. Also `.prompts/INDEX.md`'s campaign line.
  `.documents/OPEN-ISSUES.md` is unchanged: no issue opened.
- **Not changed:** no `.py` file, no test, no rule, no `CLAUDE.md`. The rehearsal directory
  `.documents/dk-and-rpk-migration/rehearsal/`, the venv, RH2's stores and every sibling
  repository are untouched.

## Deviations from the prompt

**The orchestrator's corrections** (the brief, §0):
1. **`STRUCTURALLY REQUIRED`** (correction 1). The board section is `### 5.6 After prompt 04
   (2026-10-25)`, not `5.5`.
2. **`STRUCTURALLY REQUIRED`** (correction 2). The commit holds the launcher, this note,
   `verification.md`, `out/04-*`, the board and `INDEX.md`'s one line. Outside the repository,
   only the lock (created by `start`, removed by `stop`), the cluster's temp dir and my scratch
   directory were written.
3. **`NOTED`** (correction 3). The prompt's "exited 134" is ChamPBH's pre-wrapper figure; RH2's
   unregistered `resumed-a` exited 15, with absl's banner twice. Measured here against RH2: exit
   143, no banner, no alarm line, the expected result (verification §1.6).
4. **`IMPLEMENTATION CHOICE`** (correction 4). The probe was run after `start` and before H1, as
   given: `before 0`, then `after <function init.<locals>.sigterm_handler …>
   ray._private.worker init.<locals>.sigterm_handler`, exit 0. It added job `01000000`,
   `SUCCEEDED`.
5. **`NOTED`** (correction 5). The registration lines are `>> `. At the first three checks the
   stage was `null`; at `resumed-c`'s it was a `** ` banner's line. Never a `>> ` line. The two
   `done` runs end on `Skipping gradient branch (--targets excludes 'gradient')`.
6. **`IMPLEMENTATION CHOICE`** (correction 6). I used no `Monitor`: one waiter,
   `<scratch>/wait_for_line.py LOG TEXT --timeout S [--echo]`. It reads the log at 5 Hz, prints the
   matching line with its UTC time to 0.1 s and, with `--echo`, every line with the time it was
   first seen. Each wait was one foreground Bash call (`--timeout 120` for registration, `420` for
   the launcher's line). None timed out, so none was repeated. There was no `sleep` loop, no
   `pgrep`, no `tail -f`, and no `run_in_background`.
7. **`IMPLEMENTATION CHOICE`** (correction 7). The launcher's interface is `STORE BUILD ADDRESS
   PURPOSE [LAUNCH]`, and it detaches itself (What shipped). The launch lines, exactly as run, are
   in verification §1.10.
8. **`IMPLEMENTATION CHOICE`** (correction 8). After each launch I waited for `>> registered_run:
   registered as`, then made one check, `<scratch>/check.py LAUNCH`. It covers the manifest from
   the `>>   manifest` line and that it exists; `status.json`'s state, pid against the pid file,
   heartbeat age and stage; `list`; and the log's and manifest's birth times by
   `/usr/bin/stat -f %SB`.
9. **`IMPLEMENTATION CHOICE`** (correction 9). The banner time came from `reference`'s log as the
   waiter saw it arrive, and the rows' times from `rows.py` (`mode=ro`) after its `store create`
   and `store fingerprint --write`. `<s>` = 33 s, at a load of 34.9. The signal fell inside the
   wide window and outside the narrow one: all ten `FullInstanton` rows were stored and validated,
   because the driver ran 1.4 times faster than `reference`, whose load had peaked at 135. Recorded
   and not retuned, by the brief's rule; one attempt (verification §1.5).
10. **`IMPLEMENTATION CHOICE`** (correction 10). `kill_when.py` is `interrupt_when.py` with
    `SIGTERM` → `SIGKILL` in five lines (the signal and four messages). The diff is
    `out/04-kill_when.diff`, the same five hunks as ChamPBH's. The banner was `STAGE 3: SLOW-ROLL
    INSTANTONS`, with a 10 s delay (bound 11.5 s, floor 2 s). I expected, and got, no
    `SlowRollInstanton` row stored. Correction 10 names "no row stored" as an outcome recorded, not
    a stop.
11. **`IMPLEMENTATION CHOICE`** (correction 11).
    - **The four points.** At each, `ray_cluster.sh status`, live workers, `ALIVE` actors and jobs,
      by `<scratch>/ray_state.sh`; at the fourth also the full actor listing by `--format json`.
      Every point listed the baseline's 18 pids exactly, with no live worker and no `ALIVE` actor.
    - **A fifth listing, before the stop:** five jobs, 44 actors all `DEAD`, 65 workers none alive.
    - **Nothing was left behind**, so there was nothing to wait for.
    - **Beside the store, after the kill:** no `-journal`, `-wal` or `-shm`; one
      `replication_in_flight` record, which `resumed-c`'s open reconciled.
12. **`IMPLEMENTATION CHOICE`** (correction 12). The refused launch is step 6's with `LAUNCH` =
    `resumed-c-refused`.
    - It exited 2 with one `!! ` line naming `resumed-b`'s run and `python -m runregistrykit end`,
      then `** driver exit status 2` and `** launcher saw exit status 2`.
    - `find var/runs | sort` before and after: `diff` empty. No Ray job was added.
13. **`STRUCTURALLY REQUIRED`** (correction 13). `results_store_id`: `reference` `null`,
    `resumed-a` `null`, `resumed-b` and `resumed-c` `b7904d18f0d24466b255fb7c0224a805`, the
    resumed store's `store_id` as `store show` prints it. No run carries the reference's id
    `503640899e96453a968de535c5b677a8`.
14. **`IMPLEMENTATION CHOICE`** (correction 14). The digests are equal where `compare_stores` says
    equal (`a9f716fb…1ea7` for both stores, all 24 classes equal as JSON), so there was no stop.
    - **One digest for `resumed-c`:** its status, the sidecar after it and `store fingerprint` on
      the closed store agree.
    - **No fingerprint after the kill:** `store fingerprint` was not run on the resumed store
      between the kill and `end`.
15. **`STRUCTURALLY REQUIRED`** (correction 15). `start`, `stop` and every `status` were each alone
    in their Bash call, with output to a file and never piped. No `PURPOSE` names the temp dir.
    `start` exited 0, not 3 or 4. No build, waiter or signaller was alive at `stop`. No `ray stop`.
    One slip is deviation 26.
16. **`NOTED`** (correction 16). Bit for bit against RH2 was expected and held. The provenance line
    differs from RH2's in `raypoolkit 0.3.0 (…@67a75b97…, requested v0.3.0)`, a log line.
17. **`NOTED`** (correction 17). `git_dirty` is `true` in every manifest, history and fingerprint,
    because the launcher's directory was untracked when `reference` began. `git_head` is `535b7e7`.
18. **`NOTED`** (correction 18). None of these ran:
    - `store retire`, `move`, `copy`, `amend` or `adopt`;
    - `end --unverified`;
    - any `store` command on RH2's stores;
    - `--profile-db`;
    - a plot script;
    - `main.py` other than through the launcher.

**Mine:**

19. **`NOTED` — the stop at the gate and its resolution.** At 15:42 the gate found `~/ScienceData`
    absent: `ls` gave "No such file or directory", the same with the sandbox disabled for that one
    read-only `ls`, and `mdfind` found no `11-reference.sqlite`. By the prompt's gate I stopped
    before anything ran and asked.
    - **Restored.** The user restored `~/ScienceData` from a backup.
    - **The orchestrator's check (15:59).** `11-reference.sqlite`, its ten shards (mtime 22 Oct
      21:29, as RH2 left them), its profile database and `logs/11-*` are back. Its schema agrees
      with RH2's recorded snapshot `.documents/dk-and-rpk-migration/out/11-reference-schema.json`
      (`compare_stores.py --schema … --against …`: "RESULT: the schemas agree", exit 0).
    - **My re-check (16:00).** I re-checked the gate, and the rehearsal ran from step 1. The
      restored store then compared equal, bit for bit, to this prompt's `reference` (§1.8).
20. **`IMPLEMENTATION CHOICE`** — `--poll 0.2` on `interrupt_when.py` and `kill_when.py`. It is an
    existing option of the unchanged tool (default 1 s), and it keeps the banner's detection within
    0.2 s of its arrival.
21. **`IMPLEMENTATION CHOICE`** — the registration wait, the one check and the end wait were run
    in one Bash call (in that order), so that no stage banner arrived in a gap between tool calls.
    Correction 9 needs `reference`'s banner times from its log. The check is still one check.
22. **`IMPLEMENTATION CHOICE`** — three scratch scripts beyond the brief's two, committed as text:
    - `check.py` (deviation 8);
    - `ray_state.sh` (deviation 11);
    - `rows.py`, which is RH2's `rows.py`, as its results note reproduces it, less the profile
      database and plus the newest `efold_value` per shard.
23. **`NOTED`** — step 6's "the prune's printed report removed only unvalidated rows". There was
    no report, because there was nothing unvalidated: the rows read after `resumed-a` and after
    `resumed-b` hold no unvalidated row of any table, and `resumed-c`'s lookups found all 10
    `FullInstanton` rows.
24. **`NOTED`** — step 6's "every stage's ALL WORK ITEMS COMPLETE". `resumed-c` printed three
    (STAGES 1, 3 and 4): STAGE 2 had nothing to compute, so `main.py` built no pool for it, as
    `stage_counts.py`'s docstring says of such a stage.
25. **`IMPLEMENTATION CHOICE`** — RH2's `11-reference*.sqlite` mtimes were listed before and after
    `compare_stores`, which is metadata only and not an open. They are unchanged, and no journal
    appeared.
26. **`UNINTENDED DRIFT`** (harmless) — one command line of mine named the cluster's temp dir. It
    was the `echo` that wrote the lock's owner file contents (whose `ray_temp_dir` line names it)
    into `out/04-cluster.txt`, run after `stop` and `status` had shown the lock free and no SI
    process. No lock or cluster existed then, so no process rule could seed on it. Every command
    while the cluster was up avoided it.

## Verification performed

- **The gate**, re-checked at 16:00 (after deviation 19):
  - `HEAD` `535b7e7` on `rrk-adoption`, `git status --short` empty, main checkout only;
  - `ray_cluster.sh status`, exit 0: lock free, no SI process, the four ports free;
  - `runregistrykit list`: no runs;
  - `var/` held only the empty `var/runs` and `var/datastores`, and there was no
    `var/rrk-adoption-04/`;
  - RH2's `11-reference.sqlite` and ten shards present; `~/ScienceData/.rehearsal-lock` absent;
  - `RAY_ADDRESS` unset; load 5.25.
- **The suites**, before `start` and after `stop`, against the orchestrator's baselines (default
  848: 847 passed, 1 skipped, 141 deselected; integration 72: 71 passed, 1 skipped):

  | | Before | After |
  |---|---|---|
  | default | 847 passed, 1 skipped, 141 deselected; 48.4 s; load 3.78 → 6.02 | 847 passed, 1 skipped, 141 deselected; 52.6 s; load 7.30 → 7.72 |
  | `RAY_ADDRESS=local` integration | 71 passed, 1 skipped; 79.3 s; load 5.65 → 18.16 | 71 passed, 1 skipped; 119.5 s; load 7.66 → 53.19 |

- **`pip freeze`:** 84 lines, before (16:00) and after (16:21), `cmp` exit 0; also equal to the
  orchestrator's dispatch copy.
- **The cluster:**
  - `start` at 16:05:41, exit 0, 13 s, `gcs_server` pid 24439, load 15.3;
  - `ray status`: one node, 4 CPUs;
  - `stop` at about 16:17:30, exit 0, 20 s, "released the rehearsal lock";
  - `status` after: lock free, no SI process, ports free.
- **The four runs:**

  | Run | State | Exit | Wall | `results_store_id` | Fingerprint digest | Its time at finish |
  |---|---|---|---|---|---|---|
  | `rrk-adoption-04-reference-20261025T160704` | `done` | 0 | 2 min 16 s | `null` | `a9f716fb88cf8647327748e533e7402e6f406a59aba3826956e966b7f9081ea7` | 16:09:14 → 16:09:19, ≤ 5 s |
  | `rrk-adoption-04-resumed-a-20261025T161131` | `killed` | 143 | 69 s | `null` | `33c77e5c8cc06201874341931b6251735802f1bd104efa97a6cb75069a313612` | 16:12:34 → 16:12:38, ≤ 4 s |
  | `rrk-adoption-04-resumed-b-20261025T161352` | `running` → `lost` | `null` | 21 s (`SIGKILL` at 20 s) | `b7904d18f0d24466b255fb7c0224a805` | none | — |
  | `rrk-adoption-04-resumed-c-20261025T161521` | `done` | 0 | 43 s | `b7904d18f0d24466b255fb7c0224a805` | `a9f716fb88cf8647327748e533e7402e6f406a59aba3826956e966b7f9081ea7` | 16:15:58 → 16:16:02, ≤ 4 s |

  There was no retune.
- **The heartbeat's age at the checks** (`status.json`, not `list`'s `AGE`):
  - `reference` 10.1 s, `resumed-a` 9.0 s and `resumed-b` 8.5 s, each stage `null`;
  - `resumed-c` 0.3 s, stage `STAGE 1: … all work items complete`.

  The longest silence was `reference`'s STAGE 2, 42.9 s, inside 03's 45 s and far inside the 900 s
  window. No run was shown stale while it ran.
- **The two delays.**
  - **`resumed-a`: 33 s after `STAGE 2: FULL MSR INSTANTONS`.** It came from `reference`'s banner
    (seen 16:07:55.5) and its `FullInstanton` rows (+32.2 to +42.6 s), with the last
    `CompactionFunction` row at +77.0 s.
  - **`resumed-b`: 10 s after `STAGE 3: SLOW-ROLL INSTANTONS`.** It came from `resumed-a`'s state
    (all `FullInstanton` validated, nothing after) and `reference`'s STAGE 3 (23 s, the first
    `SlowRollInstanton` at banner +21.0 s).
- **The signal (P9):**
  - exit **143**; no absl `*** SIGTERM received` banner; no `** cancelled an alarm` line;
  - signal → `killed` record: **0 s ±1 s**; signal → the final record with the fingerprint:
    **5 s ±1 s**.
- **The hard-kill route** — `kill_when` sent `SIGKILL` to pid 26796 at 16:14:12. Then, in order:
  - the log ended with the launcher's `137` and no marker;
  - Ray had nothing alive, and the 18 baseline pids were unchanged;
  - `list` showed `!! … running … 59s` with its stderr summary;
  - the refused launch exited 2 with nothing created;
  - `end` gave "is now lost, verified: its pid 26796 does not answer kill -0 on this host";
  - `list` showed `lost` (verification §1.7).
- **`compare_stores`:**
  - the reference against the resumed store: `RESULT: equal`, exit 0;
  - the reference against RH2's `11-reference`: `RESULT: equal`, exit 0;
  - in both, 30 tables matched, 0 rows in either only, timestamps and JSON timing keys differing
    only.
- **Acceptance:**
  1. H0–H6 as §1.2 says.
  2. The cluster was started and stopped by the script alone, under the lock. Nothing is left
     running.
  3. Nothing was written outside `var/` and `.documents/rrk-adoption/` but the board and the INDEX
     line (correction 2). No existing store was opened but RH2's `11-reference`, by
     `compare_stores`. The venv is unchanged.
  4. `git diff 1c223e8 -- main.py plot_InstantonSolutions.py plot_GradientCoupledSolutions.py
     utilities.py` is empty.
  5. One commit, staged by explicit path.

## The deliberate-breakage record

None. This prompt changes no code. The checks that would catch a wrong record are the prompt's own:
- a state, an exit code or a fingerprint against what §1.1 says;
- the refusal, and `find var/runs` around it;
- `end` against `kill -0`.

Each held. The launcher's own refusals were each tried once and refused, exit 2: too few
arguments, a bad slug, an empty address, a blank purpose, a run from outside the root, and an
existing log.

## Observations not acted on

1. **The package's repair of an interrupted replicated write was exercised**, which RH2 had not
   done. Both signals fell during a replicated `get` of `efold_value`. Both resumes opened with the
   record, found every shard holding what the controlling shard held, repaired nothing and cleared
   it. A `get` that finds its rows writes none, so this is the benign case.
2. **Ray records a `SIGKILL`ed driver's job as `SUCCEEDED`**, as ChamPBH saw. The registry's
   `stale` is what tells of the kill.
3. **`end`'s write stamps `heartbeat`**: the lost status's `heartbeat` is `end`'s time, and the last
   beat is in `ended.evidence.heartbeat`.
4. **The load came largely from outside SI.** During `reference` it peaked at 135, largely from
   SecondaryGWKit's suite (another session, another venv) and macOS's `system_profiler` and Time
   Machine. That made `reference` 3 to 6 times slower than RH2's. A delay set from one build's
   timestamps assumes a steady load. The wide window held, as the protocol needs.
5. **`resumed-a`'s purpose says "in STAGE 2"**; the signal fell 1.5 s into STAGE 3. The manifest is
   left as recorded.
6. **`begin`'s refusal names both** "by its results and results_store_id", once the store has a
   sidecar. That is the second-store refusal ChamPBH recorded, here on SI's paths.

## State handed to the next prompt

- **The gate R holds** (board §2), with the measurements in [`verification.md`](verification.md) §1.
  05 quotes them in the handover and in RunRegistryKit's gate drafts (P13).
  - **The builds:** four registered builds, `done`, `killed`/143, `lost` (via `end`) and `done`.
  - **The resumed store** equals the reference bit for bit, and the reference equals RH2's
    `11-reference` bit for bit. Fingerprint digest
    `a9f716fb88cf8647327748e533e7402e6f406a59aba3826956e966b7f9081ea7`.
  - **P9:** Ray 2.55.1 attached to an external cluster installs `ray._private.worker`'s
    `init.<locals>.sigterm_handler`. The wrapper replaces it, and the `SIGTERM`ed driver exits 143
    with no absl banner and no alarm.
- **The stores**, `var/datastores/rrk-adoption-04-reference.sqlite` and `…-resumed.sqlite` (10
  shards each), are kept for the user (README §3, §7). Their sidecars:
  - `rrk-adoption-04-reference.manifest.json`, `store_id` `503640899e96453a968de535c5b677a8`, with
    the fingerprint written by a person;
  - `rrk-adoption-04-resumed.manifest.json`, `store_id` `b7904d18f0d24466b255fb7c0224a805`, with
    the fingerprint written by `resumed-c`.
- **The runs and logs** are also kept: the four run directories under `var/runs/`, and the launch
  logs, pid files and signallers' logs under `var/rrk-adoption-04/`. `runregistrykit list`: 4 runs,
  4 finished. Removing any of them is the user's.
- **RH2's stores** under `~/ScienceData/StochasticInstantons-rehearsals/dk-and-rpk-migration/` were
  restored by the user from a backup on 2026-10-25 (deviation 19). They were read only by
  `compare_stores`, and their mtimes are unchanged.
- **The suites** at 04's close: default 848 (847 passed, 1 skipped), `integration` 72 (71 passed, 1
  skipped), the counts 05 starts from.
- **The launcher** `.documents/rrk-adoption/rehearsal/build_registered.sh` is 04's. Phase 2's
  builds launch through the wrapper with their own arguments (README §7).
- **No issue opened;** `.documents/OPEN-ISSUES.md` is unchanged.
- **No SI cluster is running and the lock is free.** The venv, RunRegistryKit, DatastoreKit,
  RayPoolKit, ChamPBH and SGK are untouched. Nothing was pushed.
- **Rollback:** `git revert` of this commit alone (records and one script); `var/` is the user's.
