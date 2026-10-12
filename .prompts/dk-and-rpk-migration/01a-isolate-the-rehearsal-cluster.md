# Prompt 01a — isolate the rehearsal cluster, and take the shared rehearsal lock

**Campaign:** [`README.md`](README.md) · **Board items:** **C1**–**C3** ·
**Board:** [`IMPLEMENTATION_STATE.md`](IMPLEMENTATION_STATE.md)
**Written:** 2026-10-12, after 01's review, when the user ruled **U9** (README §6.1): SI's
rehearsal cluster is isolated from other projects' and stops only itself, and a lock shared with
ChamPBH and SecondaryGWKit lets one rehearsal run at a time.
**Gate:**
- 01 landed and reviewed (board §1, §5.5); on branch `dk-and-rpk-migration`, no tracked change in
  `git status`;
- the venv holds neither `datastorekit` nor `raypoolkit`;
- **`~/ScienceData/.rehearsal-lock` does not exist**, and no process's command line contains
  `/tmp/ray-si` or `/tmp/ray-decoy`. If either fails, stop and ask.

**Closes:** nothing. **Opens:** only what the work finds.
**Recommended model:** **Sonnet**. The design is fixed by the brief; the work is a careful shell
script and a real start/stop on this machine.

**Read first:**

1. `CLAUDE.md`, and `.claude/rules/test-selection.md`.
2. **[`rehearsal-lock-brief.md`](rehearsal-lock-brief.md), in full.** §2 (the lock) and §3 (the
   cluster) are this prompt's specification. Its contract is shared with ChamPBH and SGK, so it is
   followed exactly: the lock's path, the owner file's keys and order, the refusal when held, the
   release check. SI's row of §3's table gives the temp dir and the ports.
3. [`README.md`](README.md): §4.1 "The cluster" (as amended for U9), §5 (rules 17 and 18) and §6.1
   U9.
4. Prompt 01's results note and its scripts under `.documents/dk-and-rpk-migration/rehearsal/`:
   house style for a script here (licence header, usage, `REHEARSAL_ROOT`, refusals).
5. Prompt 02 (`02-rehearse-the-start-tree.md`) §1.2–§1.4, which will call your script: its
   `start`, its `stop`, and its actor check.

---

## 1. What is wanted

**`.documents/dk-and-rpk-migration/rehearsal/ray_cluster.sh`**, run from the repository root:

```bash
.documents/dk-and-rpk-migration/rehearsal/ray_cluster.sh start PURPOSE [--num-cpus N]
.documents/dk-and-rpk-migration/rehearsal/ray_cluster.sh stop
.documents/dk-and-rpk-migration/rehearsal/ray_cluster.sh status
```

- **`start PURPOSE`** (e.g. `"dk-and-rpk-migration 02 (RH0)"`; `--num-cpus` defaults to 4, README
  §4.1):
  1. takes the lock (brief §2), writing the owner file with `pid: -`; if it is held, prints the
     owner file and exits 3, starting nothing;
  2. runs `./venv/bin/ray start --head` with SI's row of brief §3 (`--temp-dir /tmp/ray-si --port
     6390 --ray-client-server-port 6391 --dashboard-port 8266 --dashboard-agent-listen-port 52366`)
     and `--num-cpus N --disable-usage-stats`;
  3. on success, rewrites the owner file with the `gcs_server`'s pid, and prints one line
     `>> ray_cluster: address 127.0.0.1:6390` (and the dashboard's address);
  4. on failure, stops whatever it started (as `stop` does) and releases the lock, exit non-zero.
- **`stop`:** stops SI's cluster by brief §3's targeted stop, **never `ray stop`**: `SIGTERM` to
  every process whose command line contains `/tmp/ray-si` or `/private/tmp/ray-si`, and to their
  descendants; a grace period (default 15 s); `SIGKILL` to what remains; then it confirms that no
  process matches and that port 6390 is free. Only then it releases the lock, after checking the
  owner file's `project` and `ray_temp_dir` are SI's. It prints every pid it signalled. If nothing
  matched and the lock is SI's, it releases the lock and says so; if the lock is another's, it
  touches nothing and exits non-zero.
- **`status`:** the lock's state and owner file, whether its `pid` is alive, and SI's cluster's
  processes, if any.

It never runs `ray stop`, never waits on a held lock, and never removes a lock that is not SI's.
Shell: `#!/usr/bin/env bash`, `set -u`, and correct under macOS `/bin/bash` 3.2 as well as
MacPorts' bash 5 (01's review checked `build.sh` under both).

**How a CLI call finds SI's cluster.** `ray list actors` is served by the dashboard and otherwise
finds its cluster through `ray_current_cluster` or `RAY_ADDRESS`. Establish, on the real cluster,
the invocation that reaches SI's cluster and no other (`--address`, with the GCS or the dashboard
address, or `RAY_ADDRESS=127.0.0.1:6390`), and print it from `start` as a second line,
`>> ray_cluster: actors: <command>`. Prompt 02 uses that line. Also record where `ray start
--temp-dir /tmp/ray-si` writes `ray_current_cluster`.

## 2. The proof — on a real cluster, with no build

Run, in order, recording each command and its output in the results note. No `main.py`, no store.

1. **`status`** with nothing running: the lock is free, no SI process.
2. **`start "dk-and-rpk-migration 01a (dry run)"`**: the address line and the actor line. The owner
   file has the brief's seven keys in order, with the `gcs_server`'s pid.
3. **A second `start`**: exits 3, prints the owner file, starts nothing (process list unchanged).
4. **A decoy on Ray's defaults but its own temp dir**, from the scratchpad:
   `./venv/bin/ray start --head --temp-dir /tmp/ray-decoy --num-cpus 1 --disable-usage-stats`
   (ports 6379, 10001, 8265, 52365). Both clusters run at once; record both.
   - If anything already holds 6379 or 52365, skip the decoy's start, say so, and stop and ask.
5. **Workers on SI's cluster**: from a `./venv/bin/python -I` scratch script, `ray.init(address=
   "127.0.0.1:6390")`, run a few tasks and one named actor, and leave the actor alive; then the
   actor line's command lists it, and the same command does **not** list anything of the decoy's.
   Exit the script (the actor is detached or the driver is kept alive in the background, your
   choice; say which).
6. **`stop`**: every SI process gone (gcs, raylet, dashboard, agents, log monitor, workers, the
   actor's worker), port 6390 free, the lock released. **The decoy's processes all still run**
   (count them before and after).
7. **The decoy stopped the same way**, by the same targeted method aimed at `/tmp/ray-decoy`
   (call the script's internal stop function with that temp dir, or a scratch copy of it). Then no
   process names `/tmp/ray-si` or `/tmp/ray-decoy`, and the lock is free.
8. **A lock held by another project**: write a stand-in owner file with `project: ChamPBH` and
   `ray_temp_dir: /tmp/ray-cpbh` into a lock you create by hand; `start` exits 3 and prints it;
   `stop` refuses to release it, exit non-zero; then remove it by hand.
9. **`status`** again: free, nothing running.

If a step leaves a Ray process you cannot account for, stop and ask; do **not** run `ray stop`.

## 3. Acceptance

1. §2's nine steps pass, each shown.
2. `ray_cluster.sh --help` (or no arguments) prints its usage.
3. `bash -n` passes, and the script is run under `/bin/bash` (3.2) for steps 1–3 at least.
4. **The suites** (`.claude/rules/test-selection.md`; this changes no Python): the default run 680
   (679 passed, 1 skipped) and `RAY_ADDRESS=local … -m integration` 61 (60 passed, 1 skipped), as
   at `84a5cfc`. Run them **before** step 2 or **after** step 9, not while a cluster is up.
5. **Deliberate breakage** (README §5 rule 8), each shown by rerunning the step it breaks, never
   committed, recorded as a diff that `git apply` replays:
   - the stop's match widened from the temp dir to `ray::`/`raylet` alone: step 6's decoy count
     falls;
   - the lock's `mkdir` given `-p`: step 3 starts a second cluster (stop it by the targeted stop at
     once);
   - the release's owner check removed: step 8's `stop` releases ChamPBH's lock.
6. **The records**, in the same commit:
   - the results note `.documents/dk-and-rpk-migration/01a-isolate-the-rehearsal-cluster.md`
     (README §5.1), with the actor line, where `ray_current_cluster` went, the decoy counts and
     the timings of a start and a stop;
   - the board: the §1 row for 01a; items C1–C3; a `### 5.7 After prompt 01a (<date>)` entry;
   - a §3 entry for anything opened, with `.documents/OPEN-ISSUES.md` in the same commit.

---

## 4. Stop conditions — stop and ask

- The lock exists at the start, or a process already names `/tmp/ray-si` or `/tmp/ray-decoy`.
- Something already holds 6379, 6390, 8265, 8266, 52365 or 52366.
- A step leaves a Ray process the targeted stop does not remove, or removes one it should not.
- No CLI invocation reaches SI's cluster alone (§1, "How a CLI call finds SI's cluster").
- Meeting §3 would need a change to anything but the new script, or to the brief's contract.

---

## 5. What this prompt does not do

- **Files it changes:** the new `.documents/dk-and-rpk-migration/rehearsal/ray_cluster.sh` (and a
  test fixture only if you find one useful), the results note and the board. **No other file**:
  not 01's scripts, not the brief, not the README or prompt 02 (the orchestrator amends those),
  and nothing in ChamPBH or SecondaryGWKit.
- It runs no `main.py`, opens no store, installs nothing, and **never runs `ray stop`**.
- It leaves no cluster running and the lock free.

## 6. The results note

`.documents/dk-and-rpk-migration/01a-isolate-the-rehearsal-cluster.md`, README §5.1. **One
commit**, in the repository's form, staged by explicit path, after showing
`git diff --cached --name-only`.
