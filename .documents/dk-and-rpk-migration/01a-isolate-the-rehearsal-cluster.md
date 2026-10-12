# 01a — isolate the rehearsal cluster

**Subject:** Isolate SI's rehearsal cluster and take the shared rehearsal lock
**Commit:** this commit, on branch `dk-and-rpk-migration`, on top of `37126a2`
**Date:** 2026-10-12, by Claude Sonnet 5.5
**Result:** **COMPLETE.** C1–C3 shipped: `ray_cluster.sh start|stop|status`, the lock of
`rehearsal-lock-brief.md` §2, and the proof on a real cluster (nine steps, shown below). The
proof found one defect in the brief's stop (the Ray client server carries no temp dir; D1), fixed
and re-proved from step 1. The default run is 680 (679 passed, 1 skipped) and the integration run
61 (60 passed, 1 skipped), as at `84a5cfc`. All three deliberate breakages are caught. No §4 stop
condition was met and no issue is opened. No Python changed; no `main.py` ran; no store was
opened; nothing was installed; `ray stop` was never run. Nothing is left running and the lock is
free.

Prompt: [`.prompts/dk-and-rpk-migration/01a-isolate-the-rehearsal-cluster.md`](../../.prompts/dk-and-rpk-migration/01a-isolate-the-rehearsal-cluster.md).
Contract: [`rehearsal-lock-brief.md`](../../.prompts/dk-and-rpk-migration/rehearsal-lock-brief.md) §2–§3.

## What shipped

**`.documents/dk-and-rpk-migration/rehearsal/ray_cluster.sh`** (the only new file besides this
note), `#!/usr/bin/env bash`, `set -u`, run from the repository root. Checked under macOS
`/bin/bash` 3.2.57 (the whole proof) and MacPorts bash 5.3.20 (status, start, refused second start,
stop). Usage (`--help`, or no arguments, which exits 2):

```text
usage: ray_cluster.sh start PURPOSE [--num-cpus N]
       ray_cluster.sh stop
       ray_cluster.sh status
       ray_cluster.sh --help

Run from the repository root.

  start PURPOSE   take the rehearsal lock (~/ScienceData/.rehearsal-lock), then start SI's Ray
                  head on /tmp/ray-si: GCS 6390, client 6391, dashboard 8266, dashboard agent
                  52366, N CPUs (default 4). PURPOSE is written to the lock's owner file, e.g.
                  "dk-and-rpk-migration 02 (RH0)". If the lock is held, prints its owner file and
                  exits 3, starting nothing. Prints the cluster's address and the command that
                  lists its actors.
  stop            stop SI's processes (SIGTERM to every process naming /tmp/ray-si, and to their
                  descendants; a grace period of $RAY_CLUSTER_GRACE seconds, default 15; then
                  SIGKILL), confirm none is left and port 6390 is free, then release the lock if
                  its owner is SI's. Touches nothing if the lock is another project's.
  status          the lock, its owner file, whether the owner's pid is alive, and SI's processes.

Never runs `ray stop`. Never waits on a held lock.
```

- **The lock** is brief §2 exactly: `mkdir -p ~/ScienceData`, then `mkdir ~/ScienceData/.rehearsal-lock`
  (no `-p`); on success `owner` is written as `owner.tmp` and renamed, with the seven keys in the
  brief's order (`pid: -` until the cluster is up, then rewritten with the `gcs_server`'s pid);
  held means the owner file is printed and the exit is 3, with nothing started; no waiting, no
  retry, no break. `project:` is `StochasticInstantons` (the brief's example). The release checks
  `project` and `ray_temp_dir`, then removes `owner` and `rmdir`s.
- **The cluster** is SI's row of brief §3: `./venv/bin/ray start --head --temp-dir /tmp/ray-si
  --port 6390 --ray-client-server-port 6391 --dashboard-port 8266 --dashboard-agent-listen-port
  52366 --num-cpus N --disable-usage-stats` (N defaults to 4). A failed `ray start`, or one with
  no `gcs_server` naming the temp dir, runs the stop and releases the lock; an interrupt does the
  same (trap).
- **The stop** never runs `ray stop`. One `ps -axww` snapshot is taken; seeds are the processes
  whose command line names `/tmp/ray-si` or `/private/tmp/ray-si` as a whole path component
  (`/tmp/ray-simple` does not match), plus the cluster's client server (D1); the set is closed
  over children. That set is captured once: workers re-parented to launchd when their raylet dies
  would escape a second descendant search. `SIGTERM` to all, a poll every 0.5 s for the grace
  period, `SIGKILL` to what lives, then a check that no captured pid is alive, that nothing
  matches afresh, and that port 6390 is free. Every pid signalled is printed. The script's own
  process, its ancestors and any process whose command line names `ray_cluster.sh` are never
  seeds. If the lock is another's, `stop` touches nothing and exits 1 (the check is before any
  signal, and again in the release).
- **`status`** prints the lock's state and owner file, whether the owner's `pid` is alive, SI's
  processes and port 6390.
- The script can be `source`d (its main is skipped), so that the proof stops a decoy cluster by
  calling `stop_cluster /tmp/ray-decoy 6379`, the same function `stop` uses.

### The actor line, and why it reaches SI's cluster alone

`start` prints three lines, and then its timing:

```text
>> ray_cluster: address 127.0.0.1:6390
>> ray_cluster: dashboard http://127.0.0.1:8266
>> ray_cluster: actors: ./venv/bin/ray list actors --address 127.0.0.1:6390
```

`--address` is given the cluster's GCS address, the same `127.0.0.1:6390` every driver gets as
`--ray-address`. On the real cluster, with the decoy up, the forms behave so:

| Invocation | Result |
|---|---|
| `ray list actors --address 127.0.0.1:6390` | lists `si_probe` only. **Chosen** |
| `ray list actors --address http://127.0.0.1:8266` | the same (the dashboard form also works) |
| `ray list actors --address 127.0.0.1:8266` (dashboard, no scheme) | times out: "Timed out while waiting for GCS" |
| `RAY_ADDRESS=127.0.0.1:6390 ray list actors` | the same as the first (also works) |
| `ray list actors` (no address) | `ConnectionError: Found multiple active Ray instances: {'127.0.0.1:6379', '127.0.0.1:6390'}` |

So the line reaches SI's cluster alone because it names that cluster's GCS explicitly, and the
bare form, which would not, fails loudly with two clusters up rather than picking one.

**`ray_current_cluster`.** `ray start --temp-dir /tmp/ray-si` writes it to
`/tmp/ray-si/ray_current_cluster`, containing `127.0.0.1:6390`; the decoy's went to
`/tmp/ray-decoy/ray_current_cluster` (`127.0.0.1:6379`). **Neither started a
`/tmp/ray/ray_current_cluster`**, which did not exist throughout, so a bare `ray.init()` can no
longer follow another project's cluster through that file. The file is **not removed by the
stop**: after a stop `/tmp/ray-si/ray_current_cluster` remains, stale (Observation 1).

## The proof

Recorded from `proof.sh`, a scratch script run under `/bin/bash` 3.2 from the repository root,
with the fixed script (the first pass, which found D1, is described under it). Timestamps and
hostname are the machine's. Ports 6379, 6390, 6391, 8265, 8266, 10001, 52365 and 52366 were free
and the lock and every `/tmp/ray-si` and `/tmp/ray-decoy` process were absent beforehand
(checked with `lsof` and `ps`).

**Process counts** are `list_cluster_pids DIR PORT | wc -l`: the processes the script would signal.

```text
bash: 3.2.57(1)-release

=== 1. status, nothing running
lock: free (/Users/ds283/ScienceData/.rehearsal-lock does not exist)
SI cluster (/tmp/ray-si): no processes
port 6390: free

=== 2. start
>> ray_cluster: address 127.0.0.1:6390
>> ray_cluster: dashboard http://127.0.0.1:8266
>> ray_cluster: actors: ./venv/bin/ray list actors --address 127.0.0.1:6390
>> ray_cluster: started in 11s; gcs_server pid 40847
--- owner file
project: StochasticInstantons
purpose: dk-and-rpk-migration 01a (dry run)
acquired: 2026-10-12T11:01:41+01:00
host: mps026088
ray_temp_dir: /tmp/ray-si
ray_address: 127.0.0.1:6390
pid: 40847
--- ray_current_cluster
-rw-r--r-- 1 ds283 wheel 14 Oct 12 10:58 /tmp/ray-si/ray_current_cluster
127.0.0.1:6390
--- SI processes:
decoy: 0 processes; si: 18 processes

=== 3. second start
>> ray_cluster: the rehearsal lock is held (/Users/ds283/ScienceData/.rehearsal-lock); its owner file:
    project: StochasticInstantons
    purpose: dk-and-rpk-migration 01a (dry run)
    acquired: 2026-10-12T11:01:41+01:00
    host: mps026088
    ray_temp_dir: /tmp/ray-si
    ray_address: 127.0.0.1:6390
    pid: 40847
>> ray_cluster: stop and ask the user; this script never waits on, or breaks, the lock
exit=3
--- SI process count after:
decoy: 0 processes; si: 18 processes
--- direct matches unchanged?
unchanged

=== 4. decoy (ports before)
6379/8265/10001/52365 free
2026-10-12 11:01:54,769	SUCC scripts.py:980 -- [32mRay runtime started.[39m
--- decoy ray_current_cluster: 127.0.0.1:6379
decoy: 18 processes; si: 18 processes
--- listeners
Python 41257 127.0.0.1:10001
Python 41319 127.0.0.1:52365
Python 40886 127.0.0.1:52366
gcs_serve 41255 127.0.0.1:6379
gcs_serve 40847 127.0.0.1:6390
Python 40849 127.0.0.1:6391
Python 41269 127.0.0.1:8265
Python 40850 127.0.0.1:8266

=== 5. workers
tasks: [0, 1, 4, 9]
actor: pong
tasks: [0, 1, 4, 9]
actor: pong
--- SI actors line:

======== List: 2026-10-12 11:02:04.010025 ========
Stats:
------------------------------
Total: 1

Table:
------------------------------
    ACTOR_ID                          CLASS_NAME    STATE      JOB_ID  NAME      NODE_ID                      
 0  99dd96b09a20b95b1c8eb9b901000000  Probe         ALIVE    01000000  si_probe  ab4e45802b8295cc433444c38d57f

--- (decoy's own listing, for contrast)

======== List: 2026-10-12 11:02:05.506377 ========
Stats:
------------------------------
Total: 1

Table:
------------------------------
    ACTOR_ID                          CLASS_NAME    STATE      JOB_ID  NAME         NODE_ID                   
 0  151601a96958cbb59af1bb1e01000000  Probe         ALIVE    01000000  decoy_probe  ada84dc888a9dea38e133c32be

--- bare ray list actors
ConnectionError: Found multiple active Ray instances: {'127.0.0.1:6379', '127.0.0.1:6390'}. Please specify the one to connect to by setting the `--address` flag or `RAY_ADDRESS` environment variable.
decoy: 19 processes; si: 19 processes

=== 6. stop
before: decoy: 19 processes; si: 19 processes
>> ray_cluster: SIGTERM to 19 process(es) naming /tmp/ray-si, and their descendants: 40847 40848 40849 40850 40851 40852 40853 40854 40855 40856 40857 40858 40859 40860 40884 40885 40886 40887 41394
>> ray_cluster: grace period of 15s over; SIGKILL to: 40847 40848
>> ray_cluster: no process names /tmp/ray-si; port 6390 is free
>> ray_cluster: released the rehearsal lock
>> ray_cluster: stopped in 19s
after: decoy: 19 processes; si: 0 processes
lock: ls: cannot access '/Users/ds283/ScienceData/.rehearsal-lock': No such file or directory
--- listeners
Python 41257 127.0.0.1:10001
Python 41319 127.0.0.1:52365
gcs_serve 41255 127.0.0.1:6379
Python 41269 127.0.0.1:8265
--- decoy still answers:
1

=== 7. stop the decoy by the same method
>> ray_cluster: SIGTERM to 19 process(es) naming /tmp/ray-decoy, and their descendants: 41255 41256 41257 41269 41282 41283 41284 41285 41286 41287 41288 41289 41290 41291 41316 41317 41319 41320 41410
>> ray_cluster: grace period of 15s over; SIGKILL to: 41255 41256
>> ray_cluster: no process names /tmp/ray-decoy; port 6379 is free
rc=0
any ray-si / ray-decoy / client-server process:
0
lock: ls: cannot access '/Users/ds283/ScienceData/.rehearsal-lock': No such file or directory

=== 8. another project's lock
>> ray_cluster: the rehearsal lock is held (/Users/ds283/ScienceData/.rehearsal-lock); its owner file:
    project: ChamPBH
    purpose: stand-in (01a proof)
    acquired: 2026-10-12T11:00:00+01:00
    host: mps026088
    ray_temp_dir: /tmp/ray-cpbh
    ray_address: 127.0.0.1:6380
    pid: -
>> ray_cluster: stop and ask the user; this script never waits on, or breaks, the lock
start exit=3
>> ray_cluster: the rehearsal lock is another project's (project='ChamPBH' ray_temp_dir='/tmp/ray-cpbh'); touching nothing. Its owner file:
    project: ChamPBH
    purpose: stand-in (01a proof)
    acquired: 2026-10-12T11:00:00+01:00
    host: mps026088
    ray_temp_dir: /tmp/ray-cpbh
    ray_address: 127.0.0.1:6380
    pid: -
stop exit=1
lock after:
project: ChamPBH
purpose: stand-in (01a proof)
acquired: 2026-10-12T11:00:00+01:00
host: mps026088
ray_temp_dir: /tmp/ray-cpbh
ray_address: 127.0.0.1:6380
pid: -
(removed by hand)

=== 9. status
lock: free (/Users/ds283/ScienceData/.rehearsal-lock does not exist)
SI cluster (/tmp/ray-si): no processes
port 6390: free
```

Reading it:

| Step | Outcome |
|---|---|
| 1. `status`, nothing running | lock free, no SI process, port 6390 free |
| 2. `start "dk-and-rpk-migration 01a (dry run)"` | address, dashboard and actor lines; owner file with the seven keys in order and `pid: 40847`, the `gcs_server`'s; 18 SI processes |
| 3. a second `start` | exit 3, owner file printed, "stop and ask the user"; the SI process count is 18 before and after, and the root pids are unchanged |
| 4. the decoy on Ray's defaults, `/tmp/ray-decoy` | ports 6379, 10001, 8265, 52365 free beforehand; both clusters listening at once (8 listeners: SI's 6390/6391/8266/52366, the decoy's 6379/10001/8265/52365); 18 decoy processes |
| 5. workers | from `./venv/bin/python -I`, `ray.init(address="127.0.0.1:6390")`, four tasks and a named **detached** actor `si_probe`, the driver then exiting; the actor line lists `si_probe` and not `decoy_probe`; the decoy's own address lists `decoy_probe` alone. SI and decoy counts rose to 19 each (the actor's worker) |
| 6. `stop` | 19 pids SIGTERMed, including `41394`, the actor's worker; `gcs_server` and its sibling Python process (`40847`, `40848`) ignored SIGTERM and were SIGKILLed after the 15 s grace; no SI process, port 6390 free, lock released; listeners left are the decoy's four only. **Decoy: 19 processes before, 19 after**, and its actor still answered |
| 7. the decoy stopped the same way | `stop_cluster /tmp/ray-decoy 6379`: 19 pids, two SIGKILLed; then 0 processes name `/tmp/ray-si`, `/tmp/ray-decoy`, the client server, `raylet` or `gcs_server`; lock free |
| 8. another project's lock | a hand-made lock with `project: ChamPBH` and `ray_temp_dir: /tmp/ray-cpbh`: `start` exit 3 and prints it; `stop` exit 1, "touching nothing", prints it; the lock is unchanged; removed by hand |
| 9. `status` | free, nothing running |

**Timings** (load average was high, so these are upper bounds): a start 6 to 18 s over the
runs (11 s in the proof); a stop 18 to 19 s, which is the 15 s grace period, because the
`gcs_server` and a sibling process ignore SIGTERM, plus the poll; a stop with nothing running, 0 s.
`RAY_CLUSTER_GRACE` shortens the wait.

**The first pass.** The first full run used a stop that matched only the temp dir and descendants.
Its step 6 passed its own checks (decoy 18 before and after, port 6390 free) but `lsof` showed
`Python 37989 127.0.0.1:6391` still listening: Ray's client server, `python -m
ray.util.client.server --address=127.0.0.1:6390 --host=127.0.0.1 --port=6391 --mode=proxy …`, has
parent pid 1 and no temp dir on its command line. The script's own check of port 6390 could not see
it. It was found by looking at the listeners, terminated by its pid (`kill -TERM 37989`, SI's own),
and D1 added; the proof above was then rerun from step 1.

## Deviations from the prompt

- **D1 — the stop also matches the Ray client server by its `--address`. STRUCTURALLY REQUIRED.**
  Brief §3 and the prompt define the stop as the processes whose command line contains the temp
  dir, and their descendants. On the real cluster that leaves `python -m ray.util.client.server
  --address=127.0.0.1:6390 --port=6391 …` running, holding port 6391: its parent is pid 1 and its
  command line carries no temp dir (the orchestrator's brief noted workers; this is a second
  class). The stop's seeds are now the temp-dir match **or** `ray[.]util[.]client[.]server
  --address=127[.]0[.]0[.]1:<GCS port>` followed by a space or the end of the line. It is a
  property of Ray 2.55.1's `ray start --head`, so ChamPBH and SGK's stop (brief §3) needs the same
  second seed; see Observation 2.
- **D2 — the actor line uses `--address <GCS address>`. IMPLEMENTATION CHOICE.** The prompt left
  the form open; the table above shows GCS and `http://` dashboard both work and the bare form
  and the dashboard without a scheme do not. The GCS address is the one every driver is given.
- **D3 — `start` refuses when processes already name `/tmp/ray-si` though the lock was free (exit
  4), releasing the lock it just took. IMPLEMENTATION CHOICE.** A stale cluster is not the
  script's to guess about; `stop` clears it. It also is what catches breakage B2 (below) before
  `ray start` is reached.
- **D4 — `stop` checks the lock's owner before signalling anything, as well as in the release.
  IMPLEMENTATION CHOICE.** The prompt says that with another project's lock it "touches nothing";
  a check only in the release would stop SI's processes first. Breakage B3 therefore has two
  checks to remove.
- **D5 — `stop` with no lock still stops SI's processes (and says there is no lock to release).
  IMPLEMENTATION CHOICE.** Needed to clear a cluster whose lock was removed by hand.
- **D6 — owner `project:` is `StochasticInstantons`, the brief's example, not the singular used
  in the project's prose. IMPLEMENTATION CHOICE.**
- **D7 — `start` prints a dashboard line and a final `started in Ns; gcs_server pid P` line
  beside the two the prompt asked for; `stop` prints `stopped in Ns`. IMPLEMENTATION CHOICE.**
  Prompt 02 reads the `address` and `actors:` lines by their prefix.
- **D8 — the script has a source guard, so its functions can be called by a proof. IMPLEMENTATION
  CHOICE.**

No UNINTENDED DRIFT was found.

## Verification performed

- **Suites**, before any cluster started, foreground, serially (`-p no:cacheprovider`):
  - `./venv/bin/python -m pytest -m "not integration and not slow" -q`: **679 passed, 1 skipped,
    130 deselected** (680 selected, as at `84a5cfc`), 72 s;
  - `RAY_ADDRESS=local ./venv/bin/python -m pytest -m integration -q`: **60 passed, 1 skipped,
    749 deselected** (61), 42 s.
  No Python changed, so they were not repeated.
- `bash -n` passes; `ray_cluster.sh --help` and no arguments print the usage (exit 0 and 2).
- All nine steps were run under `/bin/bash` 3.2.57; status, start, a refused second start and the
  stop were run again under MacPorts bash 5.3.20 (start 9 s, second start exit 3, stop 18 s, nothing left).
- `ray stop` was never run; `grep -n "ray stop" ray_cluster.sh` finds it in comments only.
- At the end: no process names `/tmp/ray-si` or `/tmp/ray-decoy` and no `raylet`, `gcs_server` or
  client-server process runs; none of the eight ports is held; `~/ScienceData/.rehearsal-lock`
  does not exist.

## The deliberate-breakage record

Each diff is against the committed script, was applied to a tree at this commit with `git apply`,
the proof's step rerun, and reversed. Each passes `git apply --check`, and `git apply -R --check`
once applied, in `bash`, on the tree at this commit. None is committed. All three are caught.

| | Mutation | Step rerun, and what it shows |
|---|---|---|
| B1 | the stop's seeds widened by `ray::` and `raylet` | SI started, a decoy started beside it, the broken stop run: it signalled 21 processes where SI's own were 18 and the decoy's count (by the correct matcher) **fell from 18 to 15**; the decoy lost its workers |
| B2 | `mkdir` of the lock given `-p` | a second `start` with the first running: `mkdir -p` succeeds on the existing directory, so the lock is no longer refused and, **by D3's guard alone**, `ray start` is not reached: exit **4** where step 3 requires 3, and the lock is released from under the running cluster (`status` then shows the lock free beside 18 live processes). Without D3's guard the second `ray start` would have followed on the same ports. The first cluster was stopped at once by the targeted stop |
| B3 | the owner's check removed from both the stop's pre-check and the release | with a stand-in `ChamPBH` lock, `stop` exits 0 and **releases ChamPBH's lock**; with only the release's check removed, `stop` still refuses (exit 1, lock intact), by D4's pre-check |

### B1

```diff
diff --git a/.documents/dk-and-rpk-migration/rehearsal/ray_cluster.sh b/.documents/dk-and-rpk-migration/rehearsal/ray_cluster.sh
index ef35a44..5ab182c 100755
--- a/.documents/dk-and-rpk-migration/rehearsal/ray_cluster.sh
+++ b/.documents/dk-and-rpk-migration/rehearsal/ray_cluster.sh
@@ -167,7 +167,7 @@ list_cluster_pids() {
             for (p in all) {
                 if (p in safe) continue
                 if (cmd[p] ~ /ray_cluster[.]sh/) continue
-                if (cmd[p] ~ re || cmd[p] ~ re2) mark[p]=1
+                if (cmd[p] ~ re || cmd[p] ~ re2 || cmd[p] ~ /ray::|raylet/) mark[p]=1
             }
             do {
                 changed=0
```

### B2

```diff
diff --git a/.documents/dk-and-rpk-migration/rehearsal/ray_cluster.sh b/.documents/dk-and-rpk-migration/rehearsal/ray_cluster.sh
index ef35a44..28618e3 100755
--- a/.documents/dk-and-rpk-migration/rehearsal/ray_cluster.sh
+++ b/.documents/dk-and-rpk-migration/rehearsal/ray_cluster.sh
@@ -110,7 +110,7 @@ print_owner() {
 acquire_lock() {
     # acquire_lock PURPOSE. mkdir WITHOUT -p: the atomic step. Returns 3 when the lock is held.
     mkdir -p "$LOCK_PARENT" || return 1
-    if mkdir "$LOCK_DIR" 2>/dev/null; then
+    if mkdir -p "$LOCK_DIR" 2>/dev/null; then
         write_owner "$1" "-"
         return 0
     fi
```

### B3

```diff
diff --git a/.documents/dk-and-rpk-migration/rehearsal/ray_cluster.sh b/.documents/dk-and-rpk-migration/rehearsal/ray_cluster.sh
index ef35a44..5004a72 100755
--- a/.documents/dk-and-rpk-migration/rehearsal/ray_cluster.sh
+++ b/.documents/dk-and-rpk-migration/rehearsal/ray_cluster.sh
@@ -129,7 +129,7 @@ release_lock() {
     local proj tdir
     proj="$(owner_field project)"
     tdir="$(owner_field ray_temp_dir)"
-    if [ "$proj" != "$LOCK_PROJECT" ] || [ "$tdir" != "$SI_TEMP_DIR" ]; then
+    if false; then
         err "the lock is not SI's; not releasing it. owner has project='$proj' ray_temp_dir='$tdir'; SI is project='$LOCK_PROJECT' ray_temp_dir='$SI_TEMP_DIR'"
         return 1
     fi
@@ -309,7 +309,7 @@ cmd_stop() {
         local proj tdir
         proj="$(owner_field project)"
         tdir="$(owner_field ray_temp_dir)"
-        if [ "$proj" != "$LOCK_PROJECT" ] || [ "$tdir" != "$SI_TEMP_DIR" ]; then
+        if false; then
             err "the rehearsal lock is another project's (project='$proj' ray_temp_dir='$tdir'); touching nothing. Its owner file:"
             print_owner >&2
             return 1
```

## Observations not acted on

1. **`ray_current_cluster` survives the stop.** `/tmp/ray-si/ray_current_cluster` still reads
   `127.0.0.1:6390` after SI's cluster is gone. Nothing reads it while `RAY_ADDRESS` or an explicit
   `--address` is given, which is the rule (README §5 rule 17). A bare `ray.init()` looks in
   `/tmp/ray`, which neither cluster wrote.
2. **The same second seed is owed to ChamPBH.** Its `ray start` has the same client server with
   `--address=127.0.0.1:<its GCS port>`; a stop that matches only the temp dir leaves it holding
   its client port. The brief is the orchestrator's to amend (this prompt may not).
3. **`gcs_server` ignores SIGTERM** (as does one sibling Python process), so every stop pays the
   15 s grace period. Left at 15 s, per the prompt.
4. **The head's processes** are all children of pid 1
   (daemonised by `ray start`), so a descendant walk from the `ray start` process would find none
   of them; the match has to be by command line.
5. **`status`'s "owner pid alive"** tests `kill -0`, which succeeds for any live process, so a
   recycled pid reads alive. Good enough for a stale-lock look by the user.

## State handed to the next prompt

- **`ray_cluster.sh`** from the repository root: `start "dk-and-rpk-migration 02 (RH0)"` (exit 3 if
  the lock is held: stop and ask; exit 4 if a stale SI cluster is up), then pass `127.0.0.1:6390`
  to every driver with `--ray-address`, use the printed `actors:` line for a CLI call, and
  `stop` at the end and after any failure. A start takes about 10 s and a stop about 19 s.
- **`ray_current_cluster`** is at `/tmp/ray-si`, not `/tmp/ray`.
- **Suites:** default 680 (679 passed, 1 skipped); integration 61 (60 passed, 1 skipped), unchanged.
- **Nothing opened**; `.documents/OPEN-ISSUES.md` is unchanged.
