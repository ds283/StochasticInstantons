# Orchestrator — prompt 01a, isolate the rehearsal cluster

Read [`../README.md`](../README.md) §4.1 "The cluster", §5 rules 17–18 and §6.1 U9, and
[`../rehearsal-lock-brief.md`](../rehearsal-lock-brief.md) in full. The conventions are
[`prompt-01.md`](prompt-01.md)'s §0 "Conventions", unchanged but for what follows.

**The prompt:** [`01a-isolate-the-rehearsal-cluster.md`](../01a-isolate-the-rehearsal-cluster.md)
**Board items:** C1–C3 · **Closes:** nothing · **Opens:** only what the work finds ·
**Model:** Sonnet, as the prompt recommends.

**Gate:** `HEAD` is `fe2248b` (U9 and 01a written) or a later commit touching no code; the tree is
clean; `~/ScienceData/.rehearsal-lock` does not exist; no process names `/tmp/ray-si` or
`/tmp/ray-decoy`; nothing listens on 6379, 6390, 6391, 8265, 8266, 10001, 52365 or 52366.

## 0. What makes this prompt unusual

**It is the first prompt that starts a real Ray cluster, and the first with a way to damage
another project's work.** A targeted stop that matches too widely kills ChamPBH's or SGK's cluster;
one that matches too narrowly leaves SI's workers running and the next start colliding. So the
review re-runs the proof itself rather than reading it, and counts the decoy's processes.

**The contract is shared, so drift is a defect even where SI alone would not notice it.** ChamPBH
and SGK will implement brief §2 from the text. The lock's path, the `mkdir` without `-p`, the owner
file's seven keys in their order, the refusal (exit 3, owner printed, nothing started), and the
release's check on `project` and `ray_temp_dir` must be as written.

**Facts checked by the orchestrator on 2026-10-12 at `fe2248b`.** Pass them on.
- No Ray process is running; the lock does not exist; none of the eight ports is held. Load
  average ≈ 29.
- Ray 2.55.1. `ray stop` has only `--force`, `--grace-period` and logging options
  (`ray/scripts/scripts.py`, `stop`, walks `psutil.process_iter`). `ray start` fixes four ports by
  default (6379, 10001, 8265, 52365); every other port is random. `ray list actors --address` is
  "the address of Ray API server", otherwise found "from querying the GCS server" — so through
  `RAY_ADDRESS` or `ray_current_cluster`.
- In SGK's cluster this morning, `gcs_server`, `raylet` and the dashboard agent carried the temp
  dir (`--temp_dir=/tmp/ray`, `--log_dir=/tmp/ray/session_…`) on their command lines; the
  `ray::IDLE`/`ray::<Actor>` workers showed only their process title and environment. So workers
  are reached as descendants, not by the temp-dir match: the proof must show they go.
- macOS `/tmp` is a symlink to `/private/tmp`; Ray may print either.
- `flock` is not installed; `mkdir` is the lock primitive (brief §2).
- macOS `/bin/bash` is 3.2; MacPorts' `bash` (on `PATH`) is 5.3.
- ChamPBH has not yet adopted the brief. Its prompt 06 (a rehearsal on Ray's defaults) is written
  and not dispatched. If a ChamPBH or SGK Ray process appears during the run, the agent stops and
  asks.
- Baselines at `84a5cfc` (no Python has changed since): default 680 (679 passed, 1 skipped);
  `RAY_ADDRESS=local … -m integration` 61 (60 passed, 1 skipped).

**What the review exists to establish.**
- **(F1)** The script never runs `ray stop`, and stops exactly SI's processes, workers and actors
  included, and nothing of a concurrent default cluster.
- **(F2)** The lock is brief §2 exactly: atomic acquire, refusal when held, owner file, checked
  release, no wait, no break.
- **(F3)** The actor line reaches SI's cluster alone.
- **(F4)** Nothing is left running and the lock is free at the end; the suites are unchanged; the
  three breakages are caught.

## 1. Before you dispatch

1. The tree, `HEAD`, the gate above.
2. Store mtimes: reuse `orch01/stores-mtimes-before.txt` (unchanged at 01's review).

## 2. Dispatch

One fresh-context subagent, on **Sonnet**. Give it the prompt, the brief, README §4.1 and §5, the
board, `HEAD`, the baselines and §0 above as a scratchpad copy. It does not read `orchestrator/`.
Tell it plainly: one commit; the files of the prompt's §5 only; **never `ray stop`**; a held lock
or an unaccountable Ray process is a stop; its scratch directory; reply with the results note's
path, the script's usage, the actor line, where `ray_current_cluster` went, each proof step's
outcome with the decoy's process counts, the breakages, the suites and the deviations.

## 3. The review — six checks

1. **Scope.** The commit touches `ray_cluster.sh`, the results note and the board only.
2. **Reading.** `grep -n "ray stop"` in the script finds no command. The lock: `mkdir` without
   `-p` on `$HOME/ScienceData/.rehearsal-lock`; owner keys and order as brief §2; written via
   `owner.tmp` and `mv`; release checks `project` and `ray_temp_dir`. The stop: both spellings of
   the temp dir; descendants; `SIGTERM`, grace, `SIGKILL`; port check before release.
3. **The proof, re-run by the orchestrator** under `/bin/bash`: `status`; `start`; a second `start`
   (exit 3); a decoy on defaults with `/tmp/ray-decoy`; a detached actor on SI's cluster; the actor
   line lists it and nothing of the decoy's; `stop` — SI's processes all gone (by `pgrep` of the
   temp dir and of the recorded raylet's descendants before), the decoy's count unchanged, the lock
   gone; the decoy then stopped by the same method; nothing left.
4. **Breakages.** Replay the three diffs in bash; each breaks the step named; revert; tree clean.
   The `-p` breakage's second cluster is stopped at once.
5. **Suites** at the agent's commit, with no cluster up: 680 and 61.
6. **Records and leftovers.** Results note (README §5.1); board §1 row, C1–C3, §5.7. No process
   names `/tmp/ray-si` or `/tmp/ray-decoy`; the lock is free; store mtimes unchanged.

## 4. After the review

Record it on the board in §5.7 as an *Orchestrator review of prompt 01a* paragraph; fix residue in a
follow-up ("this commit" → SHA; this note in the list of orchestrator notes). Then report to the
user, with the reminder that ChamPBH and SGK must carry out the brief before their next rehearsal,
and write 02's note.
