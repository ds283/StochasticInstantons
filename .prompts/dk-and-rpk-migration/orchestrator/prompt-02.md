# Orchestrator — prompt 02, rehearse the start tree (RH0)

Read [`../README.md`](../README.md) first: §0.2, §2.2 (02's charter), §3, §4, §4.1, §4.2, §4.3,
§5 (rules 14, 17, 18) and §6.1 (U2, U9). Then the board's §5.5 and §5.7–§5.10, which hand this
note the points taken up below. The conventions are [`prompt-01.md`](prompt-01.md)'s §0
"Conventions", unchanged but where this note says otherwise. ChamPBH's R0 note
(`ChamPBH/prompts/dk-and-rpk-migration/orchestrator/prompt-02.md`) and its reviews of R0 and R1
(ChamPBH board §5.3, §5.10) are the model; what they found that applies to SI is in §0.

**You do not write code.** You may:
- run the suites, `compare_stores.py`, `stage_counts.py` and `--snapshot` on the agent's stores;
- read the agent's stores with `sqlite3` in `mode=ro`, never through the layer;
- run a probe from the session scratchpad on a *copy* of an agent's store, never committing one;
- fix small residue in a follow-up commit of your own (§4).

**The prompt:** [`02-rehearse-the-start-tree.md`](../02-rehearse-the-start-tree.md)
**Board items:** L1–L4 (RH0), V1, S1; gate RH0 · **Closes:** nothing · **Narrows:** nothing ·
**Opens:** only what the work finds · **Model:** Opus, as the prompt recommends.

**Gate:**
- 01 (`84a5cfc`, reviewed `bd3f242`) and 01a (`3556148`, reviewed `ed9399a`) landed.
- `HEAD` is the commit that adds this note, or a later one that touches no code ("code" as
  prompt-01.md's gate defines it). Since 01a's review, code has moved once:
  `config/argument_parser.py` (`d6d550b`, `--ray-address` required), and the cluster script
  (`8e04a7c`, the four-port checks). Both are covered in §0.
- One prompt at a time in this checkout, and **no other session runs a suite, a build or a Ray job
  on this machine while 02's builds run**.

## 0. What makes this prompt unusual

**It is the first prompt that runs `main.py` on a store, and it changes no code.** Everything it
produces is a measurement. The review reproduces each one from what the agent leaves (the logs,
the stores, the readers' directories), and does not take the results note's word for it.

**It sets the criterion for RH1 and RH2.** If both comparisons are empty but for bookkeeping, 07
and 11 are held to bitwise equality with `02-reference.sqlite` and `02-scalars.sqlite`. A
vacuous "equal" (the wrong pair compared, a table the tool skipped, a resume that never ran a
partial stage) would set the strictest criterion on false evidence. So the review re-runs both
comparisons and checks the dense one independently of the tool.

**It is the first real test of the gradient child tables.** No store in the tree holds a
`GradientCoupledInstantonValue` or `GradientCoupledInstantonProfile` row (prompt-01.md §0), so
`compare_stores` has met them only in imitation tests. RH0's dense stores are the first that hold
them. A crash, exit 2 or a skipped table there is a finding about the tool, and a stop (prompt §4,
last item).

**The resume is only a test if it is partial.** `resumed-a` must die while some
`GradientCoupledInstanton` rows are stored and some are not. Unlike ChamPBH, SI's labels carry no
job name (01's review, board §5.5 check 7), so rows cannot be attributed to a build by label. The
evidence is the `timestamp` column and the logs (below).

**Corrections to the prompt.** Pass them on.
1. **Line numbers.** The branch order is `main.py:1113-1114` (homogeneous) then `:1118-1119`
   (gradient), not `:1114`/`:1127`. `_run_gradient_branch` is `:539`; the `STAGE G` pool's title
   is `:667`, inside its `_run_instanton_queue` call. `Datastore/SQL/Datastore.py:434-460`
   (`_validate_on_startup`) stands. `--prune-unvalidated` is `config/argument_parser.py:46-50`.
2. **A retry of `resumed-a` needs a new build name.** `build.sh` refuses an existing log, and the
   prompt allows no log to be deleted. A retry is `build.sh 02 resumed resumed-a2 …` (then
   `resumed-a3`), with `interrupt_when.py` on `02-resumed-a2.log` and `02-resumed-a2.pid`. The
   store files the prompt lets the agent delete before a retry are exactly `02-resumed.sqlite`,
   `02-resumed-shard0000.sqlite` … `-shard0009.sqlite`, and any `-journal` file beside one of
   them (a stale journal would be applied to the new file of the same name). Nothing else.
   Earlier attempts' logs and pidfiles stay.
3. **The banner matches the lookup line first.** `interrupt_when.py` matches a substring, and
   `_run_instanton_queue` prints `** STAGE G: GRADIENT-COUPLED (ONION MODEL) INSTANTONS LOOKUP:`
   (`main.py:474-478`) immediately before the pool prints its own banner. Nothing slow lies
   between them, so `S` is measured from the lookup line. Say so in the results note.
4. **`### 5.8` is taken.** The board's dispatch record now runs to §5.11. 02's section is
   `### 5.12 After prompt 02 (<date>)`.
5. **The `slow` block cannot run "in the foreground"** as one Bash call: a call is capped at ten
   minutes, and the block's nine files each took most of a minute or more on their own
   (`.claude/rules/test-selection.md`). Run it once, with nothing else running, as a background
   Bash task writing to a file in the agent's scratch directory, and wait for the notification.
   If that is impossible, run it file by file, serially, and add the counts and durations.
   A failure is re-run alone before it is recorded as the start tree's.
6. **The integration suite** runs as `RAY_ADDRESS=local ./venv/bin/python -m pytest -m
   integration -q -p no:cacheprovider` (README §5 rule 17), and both suites run before
   `ray_cluster.sh start`.

**Handed on from 01's and 01a's reviews and the later sections (board §5.5, §5.7–§5.10):**
- **`run_readers.sh` exits 1 by design** when step 4 finds the expected `2026.3.0` `version` row.
  L3 reads `status.txt` (steps 0–3 exit 0) and `4-compare_stores.log` (only `version` differs,
  `B only 1`, plus bookkeeping).
- **A `SIGTERM`ed driver exits 134**, Ray's absl failure-signal handler aborting (ChamPBH board
  §5.3), not 143.
- **`diagnostics_data.csv`'s timing columns** are `diag_compute_time_<kind>` (01's results note,
  Observation 6): `diag_compute_time_gradient_coupled`, and `_full`, `_slow_roll` where present.
  `scalar_data.csv` carries none.
- **The cluster.** `ray_cluster.sh start` takes about 6–22 s and `stop` about 19–35 s (`gcs_server`
  ignores `SIGTERM`, so the 15 s grace runs). Nothing else may name `/tmp/ray-si` on its command
  line during a stop (a shell that does is signalled). `ray_current_cluster` is written into
  `/tmp/ray-si`, so every `ray` CLI call needs `--address 127.0.0.1:6390`.
- **`--ray-address` is required** by `main.py` and both plot scripts (`d6d550b`). `build.sh` and
  `run_readers.sh` already pass it.
- **ChamPBH has carried out the brief** (its 05a), so its `ray stop` can no longer kill SI's
  cluster; the lock decides who runs.

**From ChamPBH's R0 and R1, for SI:**
- **Prune reports reach the driver's log through Ray's log forwarding**, and Ray deduplicates
  identical lines across actors (`[repeated Nx across cluster]`). SI's report is a count, not a
  row list: under `!! INTEGRITY WARNING (…): datastore "shardNNNN-store" (physical file …)`
  (`Datastore.py:450-458`) the factory's `Pruned N unvalidated GradientCoupledInstanton records`
  (`ObjectFactories/GradientCoupledInstanton.py:632`), and likewise for the other factories. If a
  line is marked repeated, the agent reads the actors' own logs under
  `/tmp/ray-si/session_*/logs/` (or `logs/old/` once the job has ended) **before**
  `ray_cluster.sh stop`. "Only unvalidated rows were pruned" is shown by the total pruned equal
  to the unvalidated count the agent read between `resumed-a` and `resumed-b`.
- **The killed build can store a row and not validate it** (ChamPBH R1 stored five, validated
  two). That is what the prune at open is for, and not a stop.

**The facts, checked by the orchestrator on 2026-10-20 at `15f301a`.** Pass them on.
- **The tree.** Branch `dk-and-rpk-migration`, `HEAD` `15f301a` before this note, clean. The 17
  store files of prompt-01.md §1 step 5 are in the tree (ignored); none is the agent's.
- **The lock and Ray.** `ray_cluster.sh status`: lock free, no `/tmp/ray-si` process, ports 6390,
  6391, 8266 and 52366 free. No `raylet`, `gcs_server` or `ray::` process on the machine.
  `RAY_ADDRESS` is unset. ChamPBH's `dk-and-rpk-migration` and `rrk-adoption` campaigns are
  closed, and SGK records its `rrk-v020-adoption` campaign closed; neither is known to be about
  to rehearse, and SGK takes the lock for its rehearsals (its `docs/*/rehearsal/lock_*.txt`).
- **The venv.** `pip show datastorekit raypoolkit` finds neither. Every provenance line should
  read `>> packages: datastorekit not installed; raypoolkit not installed`.
- **The machine.** 10 CPUs. Load average 8.2 / 11.0 / 9.2 at 01:22 BST, from system daemons and
  the desktop app; no suite, build or Ray job. It rose to about 40 for a minute after the
  orchestrator's suites. The prompt's gate asks for an idle machine: the agent checks again at its
  start (`uptime`, and `pgrep -fl 'pytest|main.py|raylet|gcs_server'`), and if a foreign suite or
  Ray job is running, it stops and asks.
- **`~/ScienceData/`** holds only `ChamPBH-rehearsals/`, which the agent does not touch.
  `$REHEARSAL_ROOT` does not exist; the agent creates it with `mkdir -p`.
- **The time zone.** The machine is on BST (UTC+1). The stores' `timestamp` is a naive local
  `datetime.now()` (`Datastore.py:652`), stamped at insert; `RayWorkPool`'s progress lines are
  local time (`RayTools/RayWorkPool.py:552`); `interrupt_when.py` prints UTC. Every time the
  results note compares across them is converted, and says so.
- **The log has a clock.** A titled pool prints a progress line at most once a minute, and at
  least every five minutes or 500 batches (`RayWorkPool.py:30-32`, `:539-570`):
  `   -- <local time> (<elapsed> running): n/N work items remaining …`. So the `STAGE G` banner's
  time is the first such line's time less its elapsed, and is also just after the last
  `CompactionFunction` row's `timestamp`.
- **Choosing `S`.** From `reference`'s ten `GradientCoupledInstanton` timestamps, sorted, relative
  to the banner: aim between the 4th and the 5th if the gap leaves at least 30 s each side;
  otherwise anywhere that leaves 2–8 rows stored. In-window is 1–9 rows stored (prompt §1.3.3).
  The solves run minutes each, so a few seconds' drift between builds does not matter here.
- **The killed store.** A `SIGTERM` during a store may leave a `-journal` beside a shard. The
  agent records any such file (name, size) and touches none; `resumed-b`'s open recovers it. If
  `sqlite3` `mode=ro` cannot read a shard because of it, that is recorded, and the count of §1.3.4
  is taken from the shards that can be read, with the gap stated.
- **The actors are named, not detached** (`ShardedPool.py:96`, `:158`, `:179`; `ray.init` at
  `main.py:99` passes no namespace), so they die with the killed driver. The check is
  `./venv/bin/ray list actors --address 127.0.0.1:6390 --filter "state=ALIVE"`.
- **Expected stage counts** (the agent confirms from `stage_counts.py`; a different pattern is a
  finding to explain, not a failure by itself, unless something stored was recomputed):

  | Stage | `reference` | `resumed-a` | `resumed-b` | `scalars`, `scalars-2` |
  |---|---|---|---|---|
  | `STAGE 1: BACKGROUND INFLATIONARY TRAJECTORIES` | 1 | 1 | 0 | 1 |
  | `STAGE 2`/`3`/`4` lookups | 0 computed, 10 to compute | as `reference` | 10 computed, 0 to compute (no pool banner, `main.py:480`) | — |
  | `STAGES 2+3+4: UNIFIED PIPELINE` (`PIPELINE LOOKUP`) | — | — | — | 0 computed, 10 to compute |
  | `STAGE G` lookup, then pool | 0 / 10; `SAT closure seed: 10/10` | 0 / 10; killed | *k* computed, 10 − *k* to compute; seed 10/10 | — |

  *k* is the number of validated `GradientCoupledInstanton` rows `resumed-a` left.
- **Rows per store.** Each dense store: 1 `InflatonTrajectory`; 10 each of `FullInstanton`,
  `SlowRollInstanton`, `CompactionFunction`, `GradientCoupledInstanton`, with their child rows.
  Each scalars-only store: the trajectory, the 10 `CompactionFunction`s and the instanton rows the
  unified pipeline keeps, with `label` NULL (`[unified-pipeline-stores-null-instanton-labels]`,
  bookkeeping to the tool). Each store is a primary and ten shards, `<stem>-shard0000.sqlite` …
  `-shard0009.sqlite` (`ShardedPool.py:113`); `reference` also has `02-reference-profile.sqlite`,
  which the shard glob does not match.
- **What is not a failure:** Ray's start-up `FutureWarning`s; `(raylet) … have not registered
  within the timeout` under load. Any line with `Traceback`, `Error` or `WARNING` not of these is
  read in full and recorded; `!! WARNING: … did not validate` (`RayWorkPool.py:516-518`) is a
  finding.
- **Baselines at `15f301a`** (run by the orchestrator, 01:25 BST, before this note):
  - `-m "not integration and not slow"`: **680** (679 passed, 1 skipped), 28 s;
  - `RAY_ADDRESS=local … -m integration`: **61** (60 passed, 1 skipped), 13 s; no Ray process
    left afterwards;
  - `-m "slow and not integration" --collect-only`: **69** of 810, in nine files (`test_picard`
    18, `test_sbp_sat_boundary_closure` 16, `test_response_lambda_scaling_prompt23` 11,
    `test_response_spectrum_prompt23` 10, `test_msr_action` 5,
    `test_gradient_coupled_instanton_stiffness_instrumentation` 4,
    `test_gradient_coupled_instanton_end_to_end` 3, `test_gci_parity_scalars` 1,
    `test_gci_diagnostics_convergence_floor_cli` 1). Not run; S1 runs it.
- **Expected duration.** At July's 315 s a solve, `STAGE G` is three waves, about 15 minutes; the
  homogeneous branch a few minutes more. Allow 20–30 minutes for `reference` (the stop is 45),
  and two to three hours for the whole prompt with the `slow` block.

**What the review exists to establish.**
- **(E1) The builds.** Each log has the provenance line once, its banners and summaries, and
  `** driver exit status`, as prompt §2 L1 says. `resumed-a` died by the signal inside `STAGE G`,
  134, and its actors were gone before `resumed-b`.
- **(E2) The resume.** By the stage counts and by the stores' rows and timestamps: `resumed-b`
  computed exactly the gradient rows `resumed-a` had not kept validated, and nothing was pruned
  but unvalidated rows.
- **(E3) §4.3.** Both comparisons, re-run by the orchestrator, give the agent's result and exit
  code. The dense one is confirmed by a check independent of the tool, controlled and shown able
  to fail.
- **(E4) The readers.** Steps 0–3 exit 0 for each store; each before/after comparison holds only
  the `2026.3.0` `version` row and bookkeeping; the SHA-256s are as recorded.
- **(E5) The baseline.** The stage counts, the schema snapshots and the profile database's tables,
  each reproduced from the artefacts.
- **(E6) S1.** The `slow` block's count, duration and failures, each failure re-run alone.
- **(E7) Hygiene.** No code changed; no store but the agent's own opened; no SI cluster left, the
  lock free.
- **(E8) The records.** The verification document, the results note, the board, and the index if
  an issue opened.

**Conventions particular to 02.** prompt-01.md's conventions all hold, but these replace its
rules on stores and Ray:
- **Background tasks.** Each `build.sh` runs as a background Bash task, so the agent is notified
  when it ends; `interrupt_when.py` runs as a second background task beside `resumed-a`'s,
  started straight after it. If the harness does not notify, the agent waits with the `Monitor`
  tool on the log's `** driver exit status` line, **never with a loop of `sleep` and reads**.
- **Ray.** Only `ray_cluster.sh start "dk-and-rpk-migration 02 (RH0)"` and `ray_cluster.sh stop`,
  each as a command of its own; `stop` after any stop condition too, before reporting. **Never
  `ray stop`, never `ray start`.** Exit 3 from `start` (lock held) or 4 (a port or a stale
  process) is a stop: nothing is waited for, retried or removed.
- **Stores.** The agent opens only its four stores (and the readers' `before/` copies), through
  the drivers, `compare_stores.py`, `stage_counts.py` and `sqlite3` `mode=ro`, and reads a store
  directly only once its build has ended. It deletes nothing under `$REHEARSAL_ROOT` but what
  correction 2 allows.
- **Commands verbatim.** The results note and the verification document quote each command as
  run, with the actual address and `S`.
- **Outputs committed** are small text only, under `.documents/dk-and-rpk-migration/out/02-*`. A
  file over about 1 MB is a finding to report before committing, not something to commit.
- **A §4.3 difference** is a stop *after* the readers and the records: the agent finishes §1.4 and
  §1.5, writes the results note and the verification document, stops the cluster, and **does not
  commit**. It reports and waits.

## 1. Before you dispatch

1. **The tree.** `git status --short` clean; `git diff --cached` empty; `git log --oneline
   15f301a..HEAD` is this note's commit only.
2. **Ray and the lock.** `ray_cluster.sh status` clean; no `raylet`, `gcs_server` or `ray::`
   process.
3. **The venv.** Neither package installed.
4. **The load.** `uptime`, passed on.
5. **Mtimes**, for check 10: the 17 store files in the tree, and every entry under
   `~/ScienceData/` (174 at dispatch), by `/usr/bin/stat -f '%m %z %N'`, saved in the scratchpad.

**Done at dispatch (2026-10-20, 01:22–01:27 BST):** `HEAD` `15f301a` + this note; clean; lock
free, no Ray; neither package installed; the baselines in §0; mtimes in
`orch02/stores-mtimes-before.txt` and `orch02/sciencedata-before.txt` in the session scratchpad.

## 2. Dispatch

One fresh-context subagent, on **Opus**. Give it:
- the prompt;
- the campaign README and the board;
- 01's and 01a's results notes, and `rehearsal-lock-brief.md` §2–§3;
- `HEAD`, the load, and §0 of this note up to "## 1. Before you dispatch", as a copy in the
  session scratchpad. It does not read `orchestrator/`, and does not read prompts 03–04.

Tell it plainly:
- **One commit, at the end**, unless §4.3 finds a difference (then none). Its results note is
  `.documents/dk-and-rpk-migration/02-rehearse-the-start-tree.md`, in README §5.1's form, with
  the prompt's §6 additions.
- **The files it may add or change** are the prompt's §5 list (`verification.md`,
  `.documents/dk-and-rpk-migration/out/02-*`, the results note, the board) and
  `.documents/OPEN-ISSUES.md` if an issue opens. **No code, no script of 01's or 01a's, no tool,
  no test, not the README, not `.prompts/INDEX.md`.**
- **It runs the protocol as written**, with §0's corrections, waits on each build by notification,
  and keeps the suites away from the cluster.
- **Stop and ask** on any of the prompt's §4 conditions: stop the cluster first, then reply with
  its state, the lock's state and the logs' paths. The orchestrator takes it to the user, and the
  agent resumes by `SendMessage`.
- **It replies with:**
  - the results note's path and the commit;
  - the load at each build's start, the address, the actor line, and each build's start, end,
    wall time and exit status, every `resumed-a` attempt included;
  - `S`, and the timestamps it was chosen from;
  - the gradient rows `resumed-a` left (validated and not), any journal file, and the actor check;
  - the stage counts; each prune report, with where it was read;
  - the readers' statuses, the two `scalar_data.csv` SHA-256s, and what `--inventory` printed;
  - both comparisons' `RESULT:` lines and exit codes, the tables and row counts they covered, and
    the full text of either that is not 0;
  - the profile database's tables and row counts;
  - S1: count, duration, every failure, error and skip by id;
  - the two suites;
  - every deviation with its class;
  - the "State handed to the next prompt" section, verbatim.

## 3. The review — eleven checks

1. **Scope.** `git show --stat <commit>` touches only `verification.md`, `out/02-*`, the results
   note, the board and, if an issue opened, `.documents/OPEN-ISSUES.md`. Every `out/02-*` file is
   text and under about 1 MB. `git status --short` is clean.
2. **Ray and the lock.** `ray_cluster.sh status` clean; no `/tmp/ray-si` process; the four ports
   free. The results note shows `start`, its address and actor line, the actor check before
   `resumed-b`, and `stop` with the lock released. `ray stop` appears only as "never run".
3. **E1, the logs**, read in `$REHEARSAL_ROOT/logs/`, all five (and any retry).
   - The provenance line once each, both packages not installed.
   - `reference`, `resumed-b`, `scalars`, `scalars-2` end `** driver exit status 0`, every pool
     complete; `resumed-a` ends 134 after the `STAGE G` banner.
   - `grep -n 'Traceback\|Error\|WARNING'` gives only §0's known lines.
   - `interrupt_when.py`'s output: the banner seen, `S` waited, `SIGTERM` to the pid in
     `02-resumed-a.pid`, at a UTC time that matches the log's end.
4. **E2, the counts.** Re-run `stage_counts.py` on the five logs and diff with the committed
   text and JSON. Then, `mode=ro` on each shard of `02-resumed.sqlite` and `02-reference.sqlite`:
   every row validated; ten `GradientCoupledInstanton` rows in each; in `resumed`, *k* with a
   `timestamp` before `resumed-a`'s signal (converted to BST) and 10 − *k* after it, *k* equal to
   `resumed-b`'s "already computed" and 10 − *k* to its compute count. The homogeneous rows of
   `resumed` all date from `resumed-a`.
5. **E2, the prune.** Every prune report in the five logs, read in full (and in the actors' logs
   if the agent had to go there). The total pruned in `resumed-b` equals the unvalidated count the
   agent recorded between builds. No other build pruned anything, or the note explains it.
6. **E3, §4.3, re-run.** Both `compare_stores` runs into the scratchpad: the `RESULT:` line, exit
   code and JSON equal the committed ones. Every client table is listed with counts that fit §0's
   rows per store, the two gradient child tables included and non-empty in the dense pair.
   Bookkeeping differences are only `serial`, `timestamp`, the two NULL-able labels and the timing
   keys.
7. **E3, independently of the tool.** A scratchpad script, `sqlite3` `mode=ro`, resolves each
   `GradientCoupledInstanton` to its `δN★` and hashes, by stored bits: its science columns and
   `diagnostics_json` less the timing keys (references resolved, not raw serials), its value rows
   ordered by `efold_value.N`, and its profile rows ordered by `node_index`; and the same for its
   `FullInstanton` seed. Run first on `02-reference` against itself as a control, then on the
   dense pair; then on a scratch copy of `02-resumed` with one `GradientCoupledInstantonValue`
   float moved one ulp, which it must report. The copy is deleted afterwards.
8. **E4, the readers.** For each store: `status.txt` steps 0–3 exit 0, step 4 exit 1 for the
   `version` row alone; `4-compare_stores.log` as L3 says. `shasum -a 256` of the two
   `scalar_data.csv` files equals the recorded values; the `diagnostics_data.csv` header holds
   §0's timing columns. `1-inventory.log` holds what the note says it printed.
9. **E5, the baseline.** `--snapshot` of `02-reference.sqlite` and `02-scalars.sqlite`, each
   byte-identical to the committed file. The profile database, read `mode=ro`: its tables and row
   counts as recorded, and not empty.
10. **E7, hygiene.** The 17 store files and every pre-existing entry under `~/ScienceData/` have
    their §1 mtimes and sizes. `$REHEARSAL_ROOT` holds the four stores (11 files each, `reference`
    one more), `logs/` (five logs, five pidfiles, and any retry's), and `02-readers/`. `pip
    freeze` equals `measure/out/7bb3efd-pip-freeze.txt`. No scratch file in the repository.
11. **E6 and E8, S1 and the records.**
    - S1: the count is 69; each failure the note records re-run alone by the orchestrator.
    - `verification.md`: an introduction pointing at README §4, and §1 RH0 with the cluster, the
      load, the five builds, every `resumed-a` attempt, L1–L4, §4.3 for both modes, S1 and the
      commands verbatim.
    - The board: the §1 row (✅, "this commit", the results note), L1–L4 (RH0), V1 and S1, gate
      RH0 in §2, and `### 5.12 After prompt 02`.
    - Any §3 entry, with the index's row, count and date in the same commit.
    - The suites as the agent ran them: 680 and 61.

## 4. After the review

- **Record it on the board** as an *Orchestrator review of prompt 02* paragraph in §5.12: what
  each check found, the re-run comparisons and the independent check, and anything handed on.
  Fix small residue in a follow-up commit of its own:
  - "this commit" → the SHA (board, results note, verification document);
  - this note added to the board's list of orchestrator notes, marked "used for 02";
  - `.prompts/INDEX.md`: the campaign's line (02 landed; RH0's criterion).
- Anything the review finds that is not residue is opened on the board's §3 and in the index, in
  the same commit.
- **Report to the user:**
  - §4.3's answer for each mode, in one sentence each, and what it means for RH1 and RH2;
  - the builds' times under the measured load;
  - the resume's *k*, what was pruned, and what `resumed-b` recomputed;
  - the readers, and the two SHA-256s;
  - S1's result, the baseline for 09;
  - anything opened.
- **Then 05–07 are written** (README §2.1): bitwise equality if both comparisons are empty, or the
  user's ruling if not. 03 and 04 are already written and can be dispatched once this review is
  recorded.
