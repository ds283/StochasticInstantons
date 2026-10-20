# Orchestrator — prompt 02, rehearse the start tree (RH0)

Read [`../README.md`](../README.md) first: §0.2, §2.2 (02's charter), §3, §4, §4.1, §4.2, §4.3,
§5 (rules 14, 17, 18) and §6.1 (U2, U9, U11). Then the board's §5.5, §5.7–§5.10 and §5.12, which
hand this note the points taken up below. The conventions are [`prompt-01.md`](prompt-01.md)'s §0
"Conventions", unchanged but where this note says otherwise. ChamPBH's R0 note
(`ChamPBH/prompts/dk-and-rpk-migration/orchestrator/prompt-02.md`) and its reviews of R0 and R1
(ChamPBH board §5.3, §5.10) are the model; what they found that applies to SI is in §0.

*Revised 2026-10-20 for **U11**, after the first dispatch (`0ff3609`) was stopped. Its `reference`
build ran 5 h 36 min: the homogeneous branch was stored in about 35 s, and none of the four
gradient solves of the first wave finished, every inner Picard step failing
(`[gci-picard-inner-fails-on-rehearsal-grid]`, board §5.12). The user ruled that no build runs the
gradient branch. The prompt, the README, `build.sh` and `run_readers.sh` are amended; this note is
rewritten to match, and the agent is dispatched afresh.*

*Revised again 2026-10-20, after the second dispatch (`9caeea3`) stopped at a reader:
`run_readers.sh` step 2 lacked the build's `--n-collocation-points 5`, so the plot script inserted
an `n_collocation_points=33` row. The user ruled to fix the script and re-run all; the same agent
re-runs. The second attempt's files are under `$REHEARSAL_ROOT/02-attempt-2-reader-defect/`.*

**You do not write code.** You may:
- run the suites, `compare_stores.py`, `stage_counts.py` and `--snapshot` on the agent's stores;
- read the agent's stores with `sqlite3` in `mode=ro`, never through the layer;
- run a probe from the session scratchpad on a *copy* of an agent's store, never committing one;
- fix small residue in a follow-up commit of your own (§4).

**The prompt:** [`02-rehearse-the-start-tree.md`](../02-rehearse-the-start-tree.md), as amended for
U11 · **Board items:** L1–L4 (RH0), V1, S1; gate RH0 · **Closes:** nothing · **Narrows:** nothing ·
**Opens:** only what the work finds · **Model:** Opus, as the prompt recommends.

**Gate:**
- 01 (`84a5cfc`, reviewed `bd3f242`) and 01a (`3556148`, reviewed `ed9399a`) landed.
- `HEAD` is the commit that records U11 (this note's revision), or a later one that touches no
  code ("code" as prompt-01.md's gate defines it). Since 01a's review, code has moved in
  `config/argument_parser.py` (`d6d550b`, `--ray-address` required), the cluster script
  (`8e04a7c`, the four-port checks), and now `build.sh` and `run_readers.sh` (U11). All are
  covered in §0.
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

**This is the second attempt.** The first was stopped for U11, and its files are kept, moved aside
to `$REHEARSAL_ROOT/02-attempt-1-aborted/` (its store, shards, profile database, log and pidfile).
They are not this attempt's: the agent reads its timestamps only as the prompt's §1.3.2 quotes
them, and opens nothing there. (Its primary's `shards` table records the old absolute paths, so
the layer could not open it there anyway.)

**The rehearsals now build the homogeneous branch only (U11).** The two gradient child tables are
never written, so `compare_stores` meets them only in its imitation tests. That is a known gap,
recorded under U11, not something 02 can close.

**The resume is only a test if it is partial, and the window is short.** At the first attempt the
whole homogeneous branch was stored within 25 s of its trajectory: `FullInstanton` rows 10.0–12.9 s
after the last `InflatonTrajectory` row, `SlowRollInstanton` rows 21.3–21.6 s, `CompactionFunction`
rows 23.3–24.4 s. So `resumed-a` must be signalled inside a window of a few seconds to leave some
`FullInstanton` rows stored and others not, and within about 14 s to leave the store partial at
all. `interrupt_when.py` polls once a second by default; the prompt now passes `--poll 0.2`.
Unlike ChamPBH, SI's labels carry no job name (01's review, board §5.5 check 7), so rows cannot be
attributed to a build by label. The evidence is the `timestamp` column and the logs.

**Corrections to the prompt, still standing after its amendment.** Pass them on.
1. **Line numbers.** `--prune-unvalidated` is `config/argument_parser.py:46-50`;
   `Datastore/SQL/Datastore.py:434-460` (`_validate_on_startup`) stands.
2. **The `slow` block cannot run "in the foreground"** as one Bash call: a call is capped at ten
   minutes, and the block's nine files each took most of a minute or more on their own
   (`.claude/rules/test-selection.md`). Run it once, with nothing else running, as a background
   Bash task writing to a file in the agent's scratch directory, and wait for the notification.
   If that is impossible, run it file by file, serially, and add the counts and durations.
   A failure is re-run alone before it is recorded as the start tree's.
3. **The integration suite** runs as `RAY_ADDRESS=local ./venv/bin/python -m pytest -m
   integration -q -p no:cacheprovider` (README §5 rule 17), and both suites run before
   `ray_cluster.sh start`.

The amendment itself carries what were corrections 2–4 of the first dispatch: a retry's build name
(`resumed-a2`, `resumed-a3`), the banner matching the lookup line first, and the board section
(now `### 5.13`, since §5.12 records the first attempt).

**Handed on from 01's and 01a's reviews and the later sections (board §5.5, §5.7–§5.10):**
- **`run_readers.sh` exits 1 by design** when step 4 finds the expected `2026.3.0` `version` row.
  L3 reads `status.txt` (steps 0–2 exit 0; step 3 is now printed as not run) and
  `4-compare_stores.log` (only `version` differs, `B only 1`, plus bookkeeping).
- **A `SIGTERM`ed driver exits 134 or 15.** The first attempt's exited 134, the second's 15; both
  logs show Ray's absl handler (`SIGTERM received`, the native stack). Either is "by the signal".
- **The second attempt's timing, for `S`.** In its `reference`, the `STAGE 2` banner was at about
  07:40:37.25 (from the profile database's lookup queries), the `FullInstanton` rows at +9.26 to
  +12.04 s (the delay is the driver minting each instanton's `efold_value` grid, about 0.75 s
  each), the last `CompactionFunction` at +23.4 s. `S` = 10.5 s left 3 of 10 stored.
- **The cluster.** `ray_cluster.sh start` takes about 6–22 s and `stop` about 19–35 s (`gcs_server`
  ignores `SIGTERM`, so the 15 s grace runs; at the first attempt, 19 s). Nothing else may name
  `/tmp/ray-si` on its command line during a stop. `ray_current_cluster` is written into
  `/tmp/ray-si`, so every `ray` CLI call needs `--address 127.0.0.1:6390`.
- **`--ray-address` is required** by `main.py` and both plot scripts (`d6d550b`). `build.sh` and
  `run_readers.sh` already pass it.
- **ChamPBH has carried out the brief** (its 05a), so its `ray stop` can no longer kill SI's
  cluster; the lock decides who runs.

**From ChamPBH's R0 and R1, for SI:**
- **Prune reports reach the driver's log through Ray's log forwarding**, and Ray deduplicates
  identical lines across actors (`[repeated Nx across cluster]`). SI's report is a count, not a
  row list: under `!! INTEGRITY WARNING (…): datastore "shardNNNN-store" (physical file …)`
  (`Datastore.py:450-458`) each factory prints `Pruned N unvalidated Foo records`. If a line is
  marked repeated, the agent reads the actors' own logs under `/tmp/ray-si/session_*/logs/` (or
  `logs/old/` once the job has ended) **before** `ray_cluster.sh stop`. "Only unvalidated rows
  were pruned" is shown by the total pruned equal to the unvalidated count the agent read between
  `resumed-a` and `resumed-b`.
- **The killed build can store a row and not validate it** (ChamPBH R1 stored five, validated
  two). That is what the prune at open is for, and not a stop.
- **A fresh driver on a warm cluster ran 2–5 s ahead of its `reference`** (ChamPBH R1). With a
  window of a few seconds, that matters here: aim early.

**The facts, checked by the orchestrator on 2026-10-20.** Pass them on.
- **The tree.** Branch `dk-and-rpk-migration`, clean at the commit that records U11. The 17 store
  files of prompt-01.md §1 step 5 are in the tree (ignored), unchanged by the first attempt; none
  is the agent's.
- **The lock and Ray.** After the first attempt's `stop` (07:09 BST): lock free, no `/tmp/ray-si`
  process, the four ports free, no Ray actor left. `RAY_ADDRESS` is unset. ChamPBH's
  `dk-and-rpk-migration` and `rrk-adoption` campaigns are closed, and SGK records its
  `rrk-v020-adoption` campaign closed; SGK takes the lock for its rehearsals.
- **The venv.** `pip show datastorekit raypoolkit` finds neither. Every provenance line should
  read `>> packages: datastorekit not installed; raypoolkit not installed` (it did at the first
  attempt).
- **The machine.** 10 CPUs. The load was 7–12 through the first attempt's homogeneous branch and
  its gradient stage. It read 78 a minute after the cluster's stop, with no Ray process left;
  the agent checks again at its start (`uptime`, and `pgrep -fl 'pytest|main.py|raylet|gcs_server'`),
  and if a foreign suite or Ray job is running, it stops and asks.
- **The disk** has about 40 GB free (96% used). Ray's raylet warns every ten seconds that
  `/tmp/ray-si/session_*` is "over 95% full". That is a warning, not a failure; the stores are a
  few tens of MB.
- **The time zone.** The machine is on BST (UTC+1). The stores' `timestamp` is a naive local
  `datetime.now()` (`Datastore.py:652`), stamped at insert; `interrupt_when.py` prints UTC. Every
  time the results note compares across them is converted, and says so.
- **Expected stage counts** (the agent confirms from `stage_counts.py`; a different pattern is a
  finding to explain, not a failure by itself, unless something stored was recomputed). At the
  first attempt, `reference`'s were exactly the first column:

  | Stage | `reference` | `resumed-b` | `scalars`, `scalars-2` |
  |---|---|---|---|
  | `STAGE 1: BACKGROUND INFLATIONARY TRAJECTORIES` | 1 compute | 0, "no compute items were evaluated" | 1 compute |
  | `STAGE 2: FULL MSR INSTANTONS` lookup, then pool | 0 / 10; 10 compute | *f* computed, 10 − *f* to compute (no pool if 0, `main.py:480-481`) | — |
  | `STAGE 3: SLOW-ROLL INSTANTONS` | 0 / 10; 10 compute | *s* / 10 − *s* | — |
  | `STAGE 4` section, `COMPACTION FUNCTIONS LOOKUP`, then `… AND MASSES` pool | 0 / 10; 10 compute | *c* / 10 − *c* | — |
  | `STAGES 2+3+4: UNIFIED PIPELINE` (`PIPELINE LOOKUP`) | — | — | 0 / 10; 10 compute |

  *f*, *s*, *c* are the validated rows `resumed-a` left. `resumed-a` shows `reference`'s pattern
  up to the stage where it was killed.
- **Rows per store.** Each dense store: 1 `InflatonTrajectory` (replicated: 1 row on each of the
  10 shards); 10 each of `FullInstanton`, `SlowRollInstanton` and `CompactionFunction`, with
  their child rows; no `GradientCoupledInstanton` row. Each scalars-only store: the trajectory, the
  10 `CompactionFunction`s and the instanton rows the unified pipeline keeps, with `label` NULL
  (`[unified-pipeline-stores-null-instanton-labels]`, bookkeeping to the tool). Each store is a
  primary and ten shards, `<stem>-shard0000.sqlite` … `-shard0009.sqlite`; `reference` also has
  `02-reference-profile.sqlite`, which the shard glob does not match.
- **What is not a failure:** Ray's start-up `FutureWarning`s; `(raylet) … have not registered
  within the timeout` under load; the raylet's disk warning above. Any line with `Traceback`,
  `Error` or `WARNING` not of these is read in full and recorded; `!! WARNING: … did not validate`
  (`RayTools/RayWorkPool.py:516-518`) is a finding.
- **Baselines at `15f301a`** (run by the orchestrator, 01:25 BST; no Python has changed since):
  - `-m "not integration and not slow"`: **680** (679 passed, 1 skipped), 28 s;
  - `RAY_ADDRESS=local … -m integration`: **61** (60 passed, 1 skipped), 13 s;
  - `-m "slow and not integration" --collect-only`: **69** of 810, in nine files (`test_picard`
    18, `test_sbp_sat_boundary_closure` 16, `test_response_lambda_scaling_prompt23` 11,
    `test_response_spectrum_prompt23` 10, `test_msr_action` 5,
    `test_gradient_coupled_instanton_stiffness_instrumentation` 4,
    `test_gradient_coupled_instanton_end_to_end` 3, `test_gci_parity_scalars` 1,
    `test_gci_diagnostics_convergence_floor_cli` 1). Not run; S1 runs it. The first attempt's
    agent ran the first two before its cluster: 680 and 61.
- **Expected duration.** About a minute a build, the readers a few minutes each, so the builds
  and readers well under an hour, the `slow` block apart.

**What the review exists to establish.**
- **(E1) The builds.** Each log has the provenance line once, its banners and summaries, and
  `** driver exit status`, as prompt §2 L1 says. `resumed-a` died by the signal inside its
  window (134 or 15), and its actors were gone before `resumed-b`.
- **(E2) The resume.** By the stage counts and by the stores' rows and timestamps: `resumed-b`
  computed exactly the rows `resumed-a` had not kept validated, and nothing was pruned but
  unvalidated rows.
- **(E3) §4.3.** Both comparisons, re-run by the orchestrator, give the agent's result and exit
  code. The dense one is confirmed by a check independent of the tool, controlled and shown able
  to fail.
- **(E4) The readers.** Steps 0–2 exit 0 for each store; each before/after comparison holds only
  the `2026.3.0` `version` row and bookkeeping; the SHA-256s are as recorded.
- **(E5) The baseline.** The stage counts, the schema snapshots and the profile database's tables,
  each reproduced from the artefacts.
- **(E6) S1.** The `slow` block's count, duration and failures, each failure re-run alone.
- **(E7) Hygiene.** No code changed; no store but the agent's own opened; the first attempt's
  files untouched; no SI cluster left, the lock free.
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
  directly only once its build has ended. It deletes nothing under `$REHEARSAL_ROOT` but what the
  prompt's §1.3.3 allows for a retry, and touches nothing in `02-attempt-1-aborted/`.
- **Commands verbatim.** The results note and the verification document quote each command as
  run, with the actual address and `S`.
- **Outputs committed** are small text only, under `.documents/dk-and-rpk-migration/out/02-*`. A
  file over about 1 MB is a finding to report before committing, not something to commit.
- **A §4.3 difference** is a stop *after* the readers and the records: the agent finishes §1.4 and
  §1.5, writes the results note and the verification document, stops the cluster, and **does not
  commit**. It reports and waits.
- **The results note records both earlier attempts** in a short section of its own, from board
  §5.12, and the verification document's §1 says that RH0 was run three times and why.

## 1. Before you dispatch

1. **The tree.** `git status --short` clean; `git diff --cached` empty; `git log` shows the U11
   commit on top.
2. **Ray and the lock.** `ray_cluster.sh status` clean; no `raylet`, `gcs_server` or `ray::`
   process.
3. **The venv.** Neither package installed.
4. **The load.** `uptime`, passed on.
5. **Mtimes**, for check 10: the 17 store files in the tree, and every entry under
   `~/ScienceData/` outside the SI rehearsal root, by `/usr/bin/stat -f '%m %z %N'`, saved in the
   scratchpad; and the first attempt's files under `02-attempt-1-aborted/`.

**Done at the first dispatch (2026-10-20, 01:22–01:27 BST):** `HEAD` `15f301a` + this note
(`0ff3609`); the baselines in §0; mtimes in `orch02/stores-mtimes-before.txt` and
`orch02/sciencedata-before.txt` in the session scratchpad. **Done at the second:** see board
§5.12.

## 2. Dispatch

One fresh-context subagent, on **Opus**. Give it:
- the prompt, as amended;
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
- **It runs the protocol as amended**, with §0's corrections, waits on each build by
  notification, and keeps the suites away from the cluster.
- **Stop and ask** on any of the prompt's §4 conditions: stop the cluster first, then reply with
  its state, the lock's state and the logs' paths. The orchestrator takes it to the user, and the
  agent resumes by `SendMessage`.
- **It replies with:**
  - the results note's path and the commit;
  - the load at each build's start, the address, the actor line, and each build's start, end,
    wall time and exit status, every `resumed-a` attempt included;
  - `S`, and the timestamps it was chosen from;
  - the rows `resumed-a` left, by table, validated and not, any journal file, and the actor check;
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
     complete; `resumed-a` ends 134 or 15 after the `STAGE 2` banner, and before the last
     `CompactionFunction` was stored.
   - No `STAGE G` banner in any log.
   - `grep -n 'Traceback\|Error\|WARNING'` gives only §0's known lines (and `resumed-a`'s abort).
   - `interrupt_when.py`'s output: the banner seen, `S` waited, `SIGTERM` to the pid in the
     attempt's pidfile, at a UTC time that matches the log's end.
4. **E2, the counts.** Re-run `stage_counts.py` on the five logs and diff with the committed
   text and JSON. Then, `mode=ro` on each shard of `02-resumed.sqlite` and `02-reference.sqlite`:
   every row validated; 10 each of `FullInstanton`, `SlowRollInstanton`, `CompactionFunction`;
   no `GradientCoupledInstanton`. In `resumed`, for each table, the rows with a `timestamp`
   before `resumed-a`'s signal (converted to BST) equal *f*, *s*, *c*, and those after equal
   `resumed-b`'s compute counts.
5. **E2, the prune.** Every prune report in the five logs, read in full (and in the actors' logs
   if the agent had to go there). The total pruned in `resumed-b` equals the unvalidated count the
   agent recorded between builds. No other build pruned anything, or the note explains it.
6. **E3, §4.3, re-run.** Both `compare_stores` runs into the scratchpad: the `RESULT:` line, exit
   code and JSON equal the committed ones. Every client table is listed with counts that fit §0's
   rows per store. Bookkeeping differences are only `serial`, `timestamp`, the two NULL-able
   labels and the timing keys.
7. **E3, independently of the tool.** A scratchpad script, `sqlite3` `mode=ro`, resolves each
   `FullInstanton`, `SlowRollInstanton` and `CompactionFunction` to its `δN★` and hashes, by stored
   bits: its science columns and JSON less the timing keys (references resolved, not raw serials),
   and its child rows in their `_populate` order (`efold_value.N`; `source`, `r_Mpc`). Also the
   trajectory and its value rows. Run first on `02-reference` against itself as a control, then
   on the dense pair; then on a scratch copy of `02-resumed` with one `FullInstantonValue` float
   moved one ulp, which it must report. The copy is deleted afterwards.
8. **E4, the readers.** For each store: `status.txt` steps 0–2 exit 0, step 4 exit 1 for the
   `version` row alone; step 3 printed as not run; `4-compare_stores.log` as L3 says.
   `shasum -a 256` of the two `scalar_data.csv` files equals the recorded values.
   `1-inventory.log` holds what the note says it printed.
9. **E5, the baseline.** `--snapshot` of `02-reference.sqlite` and `02-scalars.sqlite`, each
   byte-identical to the committed file. The profile database, read `mode=ro`: its tables and row
   counts as recorded, and not empty.
10. **E7, hygiene.** The 17 store files, every entry under `~/ScienceData/` outside the SI
    rehearsal root, and both earlier attempts' files all have their §1 mtimes and sizes.
    `$REHEARSAL_ROOT` holds the four stores (11 files each, `reference` one more),
    `02-attempt-1-aborted/`, `02-attempt-2-reader-defect/`, `logs/` (five logs, five pidfiles, and any retry's) and `02-readers/`.
    `pip freeze` equals `measure/out/7bb3efd-pip-freeze.txt`. No scratch file in the repository.
11. **E6 and E8, S1 and the records.**
    - S1: the count is 69; each failure the note records re-run alone by the orchestrator.
    - `verification.md`: an introduction pointing at README §4, and §1 RH0 with the cluster, the
      load, the first attempt and U11, the five builds, every `resumed-a` attempt, L1–L4, §4.3
      for both modes, S1 and the commands verbatim.
    - The board: the §1 row (✅, "this commit", the results note), L1–L4 (RH0), V1 and S1, gate
      RH0 in §2, and `### 5.13 After prompt 02`.
    - Any §3 entry, with the index's row, count and date in the same commit.
    - The suites as the agent ran them: 680 and 61.

## 4. After the review

- **Record it on the board** as an *Orchestrator review of prompt 02* paragraph in §5.13: what
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
  - the resume's *f*, *s*, *c*, what was pruned, and what `resumed-b` recomputed;
  - the readers, and the two SHA-256s;
  - S1's result, the baseline for 09;
  - anything opened.
- **Then 05–07 are written** (README §2.1): bitwise equality if both comparisons are empty, or the
  user's ruling if not. 03 and 04 are already written and can be dispatched once this review is
  recorded.
