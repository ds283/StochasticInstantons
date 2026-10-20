# Orchestrator — prompt 07, rehearse before the DatastoreKit swap (RH1)

Read [`../README.md`](../README.md) first: §2.2 (07's charter), §3, §4, §4.1, §4.2, §4.3, §5 (rules 9,
14, 17, 18) and §6.1 (U2, U7, U9, U11). Then the board's §5.13 (02's review and its "Handed on"
list), §5.14 (07 as written), and the "Handed on" lines of §5.16–§5.18. The conventions are
[`prompt-01.md`](prompt-01.md)'s §0 "Conventions", unchanged but where this note says otherwise.
[`prompt-02.md`](prompt-02.md) is the model: 07 is 02 again at a later tree, and its conventions on
background tasks, Ray, stores and verbatim commands hold here unchanged (its §0, "Conventions
particular to 02").

**You do not write code.** You may:
- run the suites, `compare_stores.py`, `stage_counts.py` and `--snapshot` on the agent's stores;
- read the agent's stores and RH0's with `sqlite3` in `mode=ro`, never through the layer;
- run a probe from the session scratchpad on a *copy* of an agent's store, never committing one;
- fix small residue in a follow-up commit of your own (§4). **The tag is not moved** by it.

**The prompt:** [`07-rehearse-before-the-datastore-swap.md`](../07-rehearse-before-the-datastore-swap.md) ·
**Board items:** L1–L4 (RH1), V2, Z1; gate RH1; RayPoolKit G4's run under real Ray ·
**Closes:** nothing · **Narrows:** nothing · **Opens:** only what the work finds ·
**Model:** Opus, as the prompt recommends · **Network:** one `git ls-remote` at the gate, nothing
else; nothing is pushed.

**Gate:**
- 03 (`5396a3d`), 04 (`ef13445`), 05 (`875cf41`) and 06 (`5e41ce8`) landed and were reviewed
  (`0c3d4b6`, `3c02d43`, `436fc8d` with `5dbcd22`, `22f7e76`). RayPoolKit G4 is in board §2.
- `HEAD` is the commit that adds this note, or a later one that touches no code.
  `git diff --stat 5e41ce8 HEAD` is records only (`.prompts/`, `.documents/`).
- The rehearsal tooling is RH0's: `git diff 5868231 HEAD -- .documents/dk-and-rpk-migration/rehearsal/
  tools/compare_stores.py` is empty.
- No SI cluster is up, the lock is free, and no other session runs a suite, a build or a Ray job on
  this machine while 07 runs.

## 0. What makes this prompt unusual

**It is the first build through `raypoolkit` and `config/datastore.py`, and the last on SI's own
layer.** 04 proved the 16 pool sites construct; 05 moved the registry and changed the vectorized
gets' shard-key argument; 06 changed which rows a pruning open deletes. None of that has run under
a real cluster on a real grid until now. RH0 is bitwise reproducible (board §5.13), so the
criterion is **bitwise equality** with RH0's stores of the same mode, timings and timestamps
aside. A vacuous "equal" would carry a false baseline into RH2 and put the tag on an unrehearsed
tree, so the review re-runs every comparison and checks the dense and scalars-only pairs
independently of the tool.

**It ends in a tag.** `pre-datastorekit` (U7), annotated, on the agent's one commit, not pushed.
P2's audit reads the June and July stores from it. The tag is made only if L1–L4 and §4.3 hold;
on an L4 difference alone the records are committed and the tag waits for the user; on a miss
nothing is committed or tagged.

**Corrections to the prompt.** Pass them on.
1. **The board section** is **`### 5.19 After prompt 07 (<date>)`**, appended after §5.18; the
   header's "Last updated" and status line are updated to match. `.prompts/INDEX.md` and the
   board's list of orchestrator notes are the orchestrator's, at the review.
2. **"06's counts"** are **696 (695 passed, 1 skipped)** and **62 (61 passed, 1 skipped)**, by
   `./venv/bin/python -m pytest -m "not integration and not slow" -q -p no:cacheprovider` and
   `RAY_ADDRESS=local ./venv/bin/python -m pytest -m integration -q -p no:cacheprovider`, serially,
   in the foreground, **before** `ray_cluster.sh start` (README §5 rules 16–17). The `slow` block is
   not run.
3. **L4 "line for line" means the parsed records, less the provenance line.**
   `out/02-stage-counts.json` is keyed by each log's absolute path, and each record carries
   `entries`, `complete_lines`, `packages`, `integrity` and `exit_status`. `packages` is the
   provenance line, which **must** differ from RH0's (`raypoolkit not installed` then; L1 checks
   the new one). So for `reference` and for `scalars`: 07's `entries`, `complete_lines`,
   `integrity` and `exit_status` equal 02's record of the same build exactly. Compare them with a
   short scratch script (reproduced in the results note), not by eye; `stage_counts.py` itself is
   run unchanged.
4. **The provenance line, measured at `HEAD`:**
   `>> packages: datastorekit not installed; raypoolkit 0.2.0 (https://github.com/ds283/RayPoolKit@eaef0ce60e2fc354bb32f0ad576010e6a83c1976, requested v0.2.0)`,
   exactly as the prompt gives it (`utilities.format_package_provenance(utilities.installed_package_provenance())`).
5. **The pool's printed lines are the copy's.** The orchestrator diffed `RayTools/RayWorkPool.py`
   at `5868231` against the installed `raypoolkit/RayWorkPool.py`. Every format string
   `stage_counts.py` parses is identical: the banner `\n** {title}` (`:181` → `:206`), the
   `!! WARNING: … did not validate …` line (`:516` → `:541`), the progress pair (`:563`, `:567` →
   `:588`, `:592`), and `-- ALL WORK ITEMS COMPLETE`, `Queue summary:` and `(no compute items were
   evaluated …)` (`:581-590` → `:606-616`). `_build_completed_status_message` is unchanged.
   `stage_counts.py`'s docstring still cites `RayTools/` lines; that is stale prose in a tool 07
   runs unchanged, not a finding. If it fails to parse a log, that is the prompt's §4 stop.
6. **What did change in the pool, and why `S` must be measured afresh.** The package keys its
   in-flight and data maps by `ref.hex()` where the copy keyed them by the bound method `ref.hex`
   (equivalent while `ray.wait` hands back the same `ObjectRef` instances); it passes the stored
   object to `post_handler` (SI passes none); and it checks its constructor's arguments. None
   changes what is computed or stored, but scheduling may move, and the window is about 3 s wide.
   RH0's `reference`: the `STAGE 2` lookup banner at 08:11:34.73 BST (from the profile database's
   `object_get FullInstanton` vector calls), `FullInstanton` rows at banner +9.77 … +12.76 s
   (about 0.75 s each of driver-side `efold_value` minting before them), `CompactionFunction`
   rows to +24.2 s; `S` = 11.0 s left 6 validated and 2 unvalidated. A fresh driver on a warm
   cluster has run ahead of its `reference` before (ChamPBH R1): aim early in the window.
7. **The prune reports** are printed by the actor at open: the header `!! INTEGRITY WARNING (…):
   datastore "shardNNNN-store" (physical file …)` (`Datastore/SQL/Datastore.py:354`, moved by 05),
   then each factory's line (`FullInstanton.py:376`, `Pruned N unvalidated FullInstanton records`).
   06 changed only `InflatonTrajectory`'s hook, and the interrupt falls after the trajectory
   stage, so no trajectory is pruned. If Ray marks a line `[repeated Nx across cluster]`, read the
   actors' own logs under `/tmp/ray-si/session_*/logs/` **before** `ray_cluster.sh stop`.
8. **The comparisons' file names.** Use, under `.documents/dk-and-rpk-migration/out/`:
   `07-compare-reference-resumed`, `07-compare-02reference-07reference`,
   `07-compare-02reference-07resumed`, `07-compare-02scalars2-07scalars`,
   `07-compare-02scalarsbefore-07scalars`, each `.txt` and `.json`. Each is run with `--json`, its
   text saved beside it, its exit code recorded.
9. **The readers' outputs kept** are as 02's: `out/07-readers-{resumed,scalars}-{status.txt,
   inventory.log,compare_stores.txt,scalar_data.csv}` and `out/07-scalar_data.sha256`. The
   inventory logs may drop Ray's raylet disk lines only, and say so. **The CSVs** are ignored by
   `.git/info/exclude` (`*.csv`) and have CRLF endings, so stage them as 02's D6 did,
   `git -c core.autocrlf=false add -f <path>`, and check `git show :<path> | shasum -a 256` gives
   the recorded hash.
10. **The profile database** is not under §4.3. Record its tables and per-function row counts
    beside RH0's (`jobs` 1; `profile_data` 807: `object_get` 443, `lease_serials` 137,
    `commit_serials` 76, `release` 61, `object_store` 40, `object_validate_item` 40,
    `read_largest_store_ids` 10). A different count is reported and explained, not a stop.
11. **The tag.** `git ls-remote --tags origin pre-datastorekit` is the one network call; the
    orchestrator ran it at 21:07 (empty, exit 0) and the agent runs it again at its gate. After the
    commit: `git tag -a` exactly as the prompt gives it, then `git cat-file -t pre-datastorekit`
    (`tag`) and `git rev-parse 'pre-datastorekit^{commit}'` (the commit). **No push of anything.**
    The records name the tag; the orchestrator fills the hash in at review, in a later commit, and
    the tag stays where it is.
12. **`verification.md`**: §2 RH1 is appended; §1 and the introduction are not touched (README §5
    rule 6).
13. **`.documents/OPEN-ISSUES.md`** is touched only if an issue opens; it stands at **61 open, 26
    closed**.

**The facts, checked by the orchestrator on 2026-10-20 at `22f7e76`, 21:05–21:10 BST.** Pass them
on.
- **The tree.** Branch `dk-and-rpk-migration`, clean, `HEAD` `22f7e76` before this note; `git diff
  --cached` empty. `git diff --stat 5e41ce8 22f7e76` is three record files. The tooling diff since
  `5868231` is empty. No local tag `pre-datastorekit`, none on `origin`. The 17 store files of
  prompt-01.md §1 step 5 are in the tree (ignored); none is the agent's.
- **Ray and the lock.** `ray_cluster.sh status`: lock free (`~/ScienceData/.rehearsal-lock` absent),
  no `/tmp/ray-si` process, ports 6390, 6391, 8266 and 52366 free. `pgrep` finds no `gcs_server`,
  `raylet`, `ray::`, `pytest` or `main.py`. `RAY_ADDRESS` unset.
- **The machine.** 10 CPUs. Load 21.2 / 11.3 / 10.9 at 21:06, 6.9 / 9.3 / 10.1 at 21:07; the top
  processes were desktop apps and Claude sessions, no suite or Ray job. The agent checks again at
  its start, and asks if a foreign suite or Ray job is running. **The disk** has 34 GB free (97%
  used): the raylet's "over 95% full" warning is expected and is not a failure.
- **The time zone** is BST (UTC+1) until 25 October. Stores stamp naive local time;
  `interrupt_when.py` prints UTC. Every cross-comparison says which it uses.
- **The venv.** `pip freeze` has the one `raypoolkit @ git+https://github.com/ds283/RayPoolKit@eaef0ce6…`
  line and no `datastorekit`; `pip check` clean. 07 installs nothing.
- **RH0's baseline is intact.** `compare_stores.py $R/02-reference.sqlite
  $R/02-readers/resumed/before/02-resumed.sqlite` and `compare_stores.py
  $R/02-readers/scalars/before/02-scalars.sqlite $R/02-scalars-2.sqlite`: both `RESULT: equal`,
  exit 0; the dense text equals `out/02-compare-reference-resumed-before-readers.txt` but for
  paths. `$REHEARSAL_ROOT` holds RH0's four stores (each a primary and ten shards;
  `02-reference-profile.sqlite`), `02-attempt-1-aborted/`, `02-attempt-2-reader-defect/`,
  `02-readers/` and `logs/` (ten 02 files). No `07-*` file exists.
- **Expected**, from RH0 (board §5.13; 02's results note): stage times about 37 s for `reference`;
  each dense store 1 trajectory (5,713 value rows on each of 10 shards), 10 each of
  `FullInstanton` (16,564 value rows), `SlowRollInstanton` (16,564) and `CompactionFunction`
  (33,128 samples), `efold_value` 7,521, `delta_Nstar` 10, no gradient row; each scalars-only store
  the same with the three value/sample tables empty. `scalar_data.csv` `b0564eec…58a2`, 11 lines,
  3,592 bytes. A `SIGTERM`ed driver may exit 134, 15 or 1. `ray_cluster.sh` start 7 s, stop 18 s.
- **What is not a failure:** Ray's start-up `FutureWarning`s; `(raylet) … have not registered
  within the timeout` under load; the raylet's disk warning; its `16 PYTHON worker processes …`
  advisory in `scalars`; the plot logs' `slow-roll instanton is compensated` physics warnings.
  Any other `Traceback`, `Error` or `WARNING` line is read in full and recorded; `!! WARNING: … did
  not validate` is a finding.

**What the review exists to establish.**
- **(E1) The builds.** Each log has the new provenance line once, its banners and summaries, and
  `** driver exit status`, as the prompt's §2 L1 says. `resumed-a` died by the signal inside its
  window, and its actors were gone before `resumed-b`.
- **(E2) The resume.** By the stage counts and by the stores' rows and timestamps: `resumed-b`
  computed exactly what `resumed-a` had not kept validated, and pruned only unvalidated rows.
- **(E3) §4.3.** All five comparisons, re-run by the orchestrator, give the agent's results, and
  each RH1 store equals RH0's of its mode bit for bit, confirmed by a per-δN★ hash independent of
  the tool, with its control shown able to fail.
- **(E4) The readers.** Steps 0–2 exit 0 for each store; each before/after comparison holds only
  the `2026.3.0` `version` row and bookkeeping; both `scalar_data.csv` hash to `b0564eec…58a2`.
- **(E5) L4.** `reference`'s and `scalars`' parsed stage counts equal RH0's; the resume's pattern
  holds.
- **(E6) The tag.** Annotated, on the agent's commit, local only.
- **(E7) Hygiene.** No code changed; no store opened but the agent's own, its readers' copies and
  RH0's read-only; RH0's files and the earlier attempts' untouched; no SI cluster, the lock free;
  the venv as it was.
- **(E8) The records.** `verification.md` §2, the results note, `out/07-*`, the board.

## 1. Before you dispatch

1. **The tree.** `git status --short` clean, `git diff --cached` empty, the tooling diff empty, no
   tag.
2. **Ray and the lock.** `ray_cluster.sh status` clean; no Ray process.
3. **The venv.** `pip freeze` saved; `pip check` clean.
4. **The load and the disk.** `uptime`, `df -h ~`.
5. **Mtimes**, for check 10: the 17 store files in the tree, and every entry under
   `~/ScienceData/`, by `/usr/bin/stat -f '%m %z %N'`. DatastoreKit's and RayPoolKit's `HEAD` and
   `git status --porcelain`.
6. **RH0's baseline**, both `before/` comparisons; the provenance line at `HEAD`; the pool's
   printed lines against the copy's.

**Done 2026-10-20, 21:05–21:10 BST,** at `22f7e76`: all six hold. In `orch07/` in the session
scratchpad: `pip-freeze.txt`, `tree-stores.txt` and `mtimes-stores.txt` (17), `mtimes-sciencedata.txt`
(606 entries, 433 of them SI's rehearsal root), `base-dense.txt`, `base-scalars.txt`, and 02's
review scripts `indep.py` and `rows.py`, copied from that review's scratchpad (`indep.py` re-run on
RH0's dense pair: 0 differing digests, 57,130 / 16,564 / 16,564 / 33,128 child rows each side).
DatastoreKit `38ebb9f`, RayPoolKit `17029d9`, both clean.

## 2. Dispatch

One fresh-context subagent, on **Opus**, in the background. Give it:
- the prompt;
- the campaign README and the board;
- 02's results note and `verification.md` §1; 03–06's results notes; `rehearsal-lock-brief.md`
  §2–§3;
- `HEAD`, the load and §0 of this note, up to "## 1. Before you dispatch" only, as a copy in the
  session scratchpad. It does not read `orchestrator/`.

Tell it plainly:
- **One commit, at the end, made once, then the tag**, unless a comparison misses (then neither)
  or L4 alone differs (then the commit and no tag). Its results note is
  `.documents/dk-and-rpk-migration/07-rehearse-before-the-datastore-swap.md`, in README §5.1's
  form, with the prompt's §6 additions.
- **The files it may add or change** are the prompt's §5 list (`verification.md` §2, `out/07-*`,
  the results note, the board) and `.documents/OPEN-ISSUES.md` if an issue opens. **No code, no
  rehearsal script, no tool, no test, not the README, not `.prompts/INDEX.md`, nothing in the venv,
  nothing in DatastoreKit, RayPoolKit, ChamPBH or SGK.** No push.
- **It runs the protocol** with §0's corrections, the suites before the cluster, each build as a
  background task waited on by notification (or `Monitor` on `** driver exit status`), never a
  loop of `sleep`.
- **Stop and ask** on any of the prompt's §4 conditions: stop the cluster first, then reply with
  its state, the lock's state and the logs' paths. The orchestrator takes it to the user, and the
  agent resumes by `SendMessage`.
- **It replies with:**
  - the results note's path, the commit, and the tag's three lines (`cat-file -t`, `rev-parse`,
    `ls-remote` still empty);
  - RH0's baseline check;
  - the load at each build's start, the address, the actor line, and each build's start, end,
    wall time and exit status, every `resumed-a` attempt included;
  - `S`, and the timestamps it was chosen from;
  - the rows `resumed-a` left, by table, validated and not, any journal file, and the actor check;
  - the stage counts, the L4 comparison with RH0's records, and each prune report with where it
    was read;
  - all five comparisons' `RESULT:` lines and exit codes, table by table with row counts beside
    RH0's, and the full text of any that is not 0;
  - the schema checks;
  - the profile database's tables and counts beside RH0's;
  - the readers' statuses, the two `scalar_data.csv` SHA-256s, and the inventory beside RH0's;
  - the provenance line as each log printed it;
  - the two suites, with the load;
  - every deviation with its class;
  - the "State handed to the next prompt" section, verbatim.

## 3. The review — twelve checks

1. **Scope.** `git show --stat <commit>` touches only `verification.md`, `out/07-*`, the results
   note, the board and, if an issue opened, `OPEN-ISSUES.md`. Every `out/07-*` file is text and
   under about 1 MB. `git status --short` clean; one commit of the agent's since this note, no
   amend in the reflog; no scratch file in the repository. `verification.md`'s diff only appends.
2. **E6, the tag.** `git cat-file -t pre-datastorekit` is `tag`; `git rev-parse
   'pre-datastorekit^{commit}'` is `<commit>`; the message is the prompt's; `git ls-remote --tags
   origin pre-datastorekit` empty; `git status -sb` shows the branch not pushed beyond where it
   was.
3. **Ray and the lock.** `ray_cluster.sh status` clean; no `/tmp/ray-si` process; ports free. The
   note shows `start`, its address and actor line, the actor check before `resumed-b`, and `stop`
   with the lock released. `ray stop` appears only as "never run".
4. **E1, the logs**, all in `$REHEARSAL_ROOT/logs/07-*`. The provenance line of correction 4 once
   each. `reference`, `resumed-b`, `scalars` end `** driver exit status 0` with 4, 4, 2 `ALL WORK
   ITEMS COMPLETE`; `resumed-a` shows `SIGTERM received` inside the `STAGE 2` pool. No `STAGE G`
   banner. `grep -n 'Traceback\|Error\|WARNING'` gives only §0's known lines. `interrupt_when.py`'s
   output: banner seen, `S` waited, `SIGTERM` to the pidfile's pid at a time matching the log.
5. **E2 and E5, the counts.** `stage_counts.py` re-run on the logs equals the committed text and
   JSON. The orchestrator's own script compares `reference`'s and `scalars`' records with
   `out/02-stage-counts.json`'s (`entries`, `complete_lines`, `integrity`, `exit_status`). Then
   `mode=ro`: every row of the three stores validated, the counts of §0; in `07-resumed`, the rows
   per table timestamped before the signal (in BST) equal `resumed-b`'s "already computed", and
   those after equal its compute counts; no orphan value row.
6. **E2, the prune.** Every report read in full; the total in `resumed-b` equals the unvalidated
   count recorded between builds; no other build pruned; no trajectory pruned.
7. **E3, §4.3, re-run.** All five comparisons into the scratchpad: `RESULT:` line, exit code and
   JSON equal the committed ones (paths aside). All 30 tables listed with §0's counts; bookkeeping
   that differs only timestamps, `serial`, the two NULL-able labels and the timing keys.
8. **E3, independently of the tool.** `orch07/indep.py`: `02-reference` against `07-reference`, and
   against `07-resumed`; `02-scalars-2` against `07-scalars`: 0 differing digests, equal child-row
   counts. Control: `07-reference` against `07-scalars`, all instanton digests differ; and a
   scratch copy of `07-resumed` with one `FullInstantonValue` float moved one ulp, reported (then
   deleted).
9. **E4, the readers.** `status.txt` on both stores; each `4-compare_stores.log` finds only
   `version{label='2026.3.0'}`; plot logs read `n_collocation_points: 1 value = [ 5 ]`;
   `shasum -a 256` of both `scalar_data.csv`, on disk and as committed blobs, is `b0564eec…58a2`;
   the inventory as RH0's but for paths and times.
10. **E7, hygiene.** The 17 store files and every entry under `~/ScienceData/` outside the files
    07 created have their §1 mtimes and sizes (RH0's stores, `before/` copies, logs and the two
    attempt directories included). `$REHEARSAL_ROOT` gains only `07-*` stores, `07-readers/` and
    `logs/07-*`; any `resumed-a` retry deleted only its own `07-resumed` files. `pip freeze` equals
    §1's; `pip check` clean. DatastoreKit and RayPoolKit as at §1 (another session may move them;
    nothing of theirs may be the agent's).
11. **E5 and E8, the schema and the profile database.** `--snapshot` of `07-reference` is
    byte-identical to the committed `out/07-reference-schema.json`; `--schema` of `07-reference`
    and `07-scalars` against `02-reference-schema.json`: "the schemas agree". The profile database,
    `mode=ro`, as recorded.
12. **E8, the records and the suites.** The results note in README §5.1's form with the prompt's
    §6 list; `verification.md` §2 with the commands verbatim and the plain statement whether RH1
    equals RH0; the board's §1 row (✅, the tag), L1–L4 (RH1), V2, Z1, gate RH1 in §2, the G4
    row's note, `### 5.19`. The orchestrator re-runs both suites at `<commit>`: 696 and 62.

## 4. After the review

- **Record it on the board** as an *Orchestrator review of prompt 07* paragraph in §5.19: what
  each check found, the re-run comparisons and the independent check, and anything handed on.
  Fix small residue in a follow-up commit of its own (records only; the tag stays on `<commit>`):
  - the commit hash beside the tag where the records name it (board, results note,
    `verification.md`);
  - this note added to the board's list of orchestrator notes, marked "used for 07";
  - `.prompts/INDEX.md`: the campaign's line (07 landed and reviewed; RH1 holds; the tag).
- Anything the review finds that is not residue is opened on the board's §3 and in the index, in
  the same commit.
- **Report to the user:**
  - §4.3's answer for each mode, in one sentence each;
  - the builds' times under the measured load, and `S`;
  - the resume: what `resumed-a` left, what was pruned, what `resumed-b` recomputed;
  - the readers and the two SHA-256s;
  - the tag, its commit, and that **the user pushes it** (README §6.3);
  - anything opened.
- **Then 08–11 are written** (README §2.1), at the reviewed tree.
