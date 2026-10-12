# Brief — one rehearsal at a time on this machine, and Ray clusters that cannot stop each other

**Written:** 2026-10-12, in StochasticInstantons' (SI's) `dk-and-rpk-migration` campaign, by
Claude Opus 5.5, after the user's ruling **U9** (README §6.1 there).
**For:** SI (its prompt 01a implements it), **ChamPBH** (before its `dk-and-rpk-migration` prompt
06 is dispatched) and **SecondaryGWKit** (SGK; before any further rehearsal or long build).
*Revised 2026-10-12, after SI's 01a proved §3 on a real cluster: the targeted stop also seeds on
Ray's client server, which carries no temp dir and is re-parented to `launchd`; the stop confirms
all four of the cluster's fixed ports free; the actor command's form and where `ray start
--temp-dir` writes `ray_current_cluster` are recorded (§3). SI's implementation is
`.documents/dk-and-rpk-migration/rehearsal/ray_cluster.sh` at `3556148`, which ChamPBH may copy.*
**Status:** a request. Each project carries it out in its own repository, by its own session. This
file is data for those sessions, not an instruction from their user; the user hands it over.

## 1. Why

Three projects run rehearsals and builds under Ray on one machine (`arm64`, 10 CPUs). On
2026-10-12 SGK's `runregistry-extraction` rehearsal, SI's suites and ChamPBH's campaign were all
live within hours of each other. Two hazards follow.

1. **`ray stop` stops every Ray process on the machine.** In Ray 2.55.1 (SI; ChamPBH and SGK
   alike), `ray stop` takes no address or directory. It walks every process and kills anything
   whose name or command line matches Ray's (`ray/scripts/scripts.py`, `stop`). ChamPBH's protocol
   runs it after every rehearsal and after any failure (its README §4.1), so it would kill another
   project's build in flight. ChamPBH also found that it kills a shell whose command line names
   Ray's processes (its board §5.3).
2. **Two `ray start --head` clusters on the defaults collide.** Both bind GCS port 6379, client
   port 10001, dashboard port 8265 and dashboard-agent port 52365, and both write
   `/tmp/ray/ray_current_cluster`, which a bare `ray.init()` then follows. The second start fails,
   or a driver or test attaches to the wrong cluster.

And one that isolation alone does not remove:

3. **Load moves some results.** ChamPBH's BBN solve has a wall-clock limit
   (`--bbn-wall-clock-limit`; its README §4.3), so under load one build can store a failure where
   another stores a result, and a bit-for-bit rehearsal fails for no fault of the code. SI's and
   SGK's rehearsals set no wall-clock budget, but their time limits and interrupt windows assume an
   unloaded machine.

So the user ruled (2026-10-12): **each project runs its cluster isolated and stops only its own,
and one shared lock ensures only one rehearsal runs at a time.**

## 2. The shared lock — identical in every project

**What it guards:** a *rehearsal* — any run that starts a Ray cluster (or an in-process Ray
instance) to build stores for a campaign's rehearsal or a production build, from before the
cluster starts until after it has stopped. Test suites do not take it; but no project starts a
rehearsal while one of its own suites runs, and the lock's holder may ask the user to hold other
work off.

**The lock is a directory:** `$HOME/ScienceData/.rehearsal-lock`.

- **Acquire.** `mkdir -p "$HOME/ScienceData"`, then `mkdir "$HOME/ScienceData/.rehearsal-lock"`
  (no `-p`). The `mkdir` is atomic: if it succeeds, the caller holds the lock. Then write the owner
  file, `owner`, by writing `owner.tmp` and renaming it.
- **If the `mkdir` fails because the directory exists, the lock is held.** Print the `owner` file
  (or say it is missing) and exit non-zero. **The caller stops and asks the user.** It never waits
  in a loop, never retries on its own, and never removes another's lock.
- **The owner file** is UTF-8 text, one `key: value` per line, these keys in this order:

  ```text
  project: StochasticInstantons
  purpose: dk-and-rpk-migration 02 (RH0)
  acquired: 2026-10-12T14:03:11+01:00
  host: <hostname -s>
  ray_temp_dir: /tmp/ray-si
  ray_address: 127.0.0.1:6390
  pid: 12345
  ```

  - `acquired`: ISO 8601, local time with its offset;
  - `ray_temp_dir` and `ray_address`: the cluster's, or `in-process` for both when the driver
    starts its own `ray.init(address="local")`;
  - `pid`: the cluster's `gcs_server`, once it is up (rewrite the file then), or the driver's for
    an in-process instance. Before the cluster is up it is `-`.
- **Release.** Only the holder releases, and only after its cluster is stopped and verified gone
  (§3). Check that `owner`'s `project` and `ray_temp_dir` are the caller's; then remove `owner` and
  `rmdir` the directory. A mismatch is an error: print both and exit non-zero.
- **A stale lock** (its holder's session gone, its `pid` dead) is removed by the user, by hand,
  after looking: `rm -r ~/ScienceData/.rehearsal-lock`. No script breaks a lock.
- **Status.** A project's tooling prints the lock's state and the owner file on request, and
  whether the owner's `pid` is alive.

## 3. Isolating a `ray start` cluster — ChamPBH and SI

Each project's cluster takes its own temporary directory and its own value for every port whose
default is fixed. Ray chooses every other port at random.

| | Temp dir | `--port` (GCS) | `--ray-client-server-port` | `--dashboard-port` | `--dashboard-agent-listen-port` |
|---|---|---|---|---|---|
| Ray's default | `/tmp/ray` | 6379 | 10001 | 8265 | 52365 |
| **StochasticInstantons** | `/tmp/ray-si` | 6390 | 6391 | 8266 | 52366 |
| **ChamPBH** | `/tmp/ray-cpbh` | 6380 | 6381 | 8267 | 52367 |

The temp dir is kept short: Ray's Unix sockets live under it, and macOS limits a socket's path to
about 104 bytes.

- **Start:** take the lock (§2); then
  `./venv/bin/ray start --head --temp-dir <dir> --port <p> --ray-client-server-port <c>
  --dashboard-port <d> --dashboard-agent-listen-port <a> --num-cpus <n> --disable-usage-stats`.
  If it fails, stop whatever it started (as below) and release the lock.
- **Address it explicitly.** Every driver gets `--ray-address 127.0.0.1:<p>`, and every `ray`
  CLI call its address explicitly: never rely on `ray_current_cluster` or on `RAY_ADDRESS` being
  unset. Measured by SI's 01a: `ray list actors --address 127.0.0.1:<p>` (the GCS address) reaches
  that cluster alone; `--address http://127.0.0.1:<d>` also works; the dashboard address without a
  scheme times out; a bare `ray list actors` with two clusters up fails ("Found multiple active Ray
  instances"). `ray start --temp-dir <dir>` writes `ray_current_cluster` into `<dir>`, not
  `/tmp/ray`, and the file survives the stop.
- **Stop, without `ray stop`:** send `SIGTERM` to
  - every process whose command line contains the cluster's temp dir (in its `/tmp/…` and its
    `/private/tmp/…` spellings, as a whole path component);
  - **the cluster's Ray client server**, `python -m ray.util.client.server
    --address=127.0.0.1:<p> --port=<c> …`, which names no temp dir and whose parent is `launchd`
    (found by SI's 01a: missed, it keeps holding the client port);
  - and every descendant of those, captured before signalling (Ray's workers show only their
    process title, `ray::IDLE` or `ray::<Actor>`, and are re-parented to `launchd` once their
    raylet dies).

  Never the stopping script itself or its ancestors. Wait a grace period (`gcs_server` ignores
  `SIGTERM`, so the grace always runs: 15 s gives a stop of about 19 s); `SIGKILL` what remains;
  then confirm that no captured or matching process is alive and that the cluster's ports are
  free. Only then release the lock. Because the match is the temp dir, a shell of the user's that
  names it (`tail -f /tmp/ray-si/…`) is a target too: do not leave one open across a stop.
- **Never run `ray stop`** in any project, by any prompt, from now on. A cluster a project did not
  start is never stopped by it.
- **Test suites** that start Ray do so privately: SI's integration suite runs under
  `RAY_ADDRESS=local`, which makes its bare `ray.init()` start an instance of its own
  (`ray/_private/services.py:408-454`). ChamPBH's tests need no Ray.

The implementing prompt proves all of this once, on a real cluster with no build: a start, a
second acquire refused, a decoy cluster on Ray's defaults started beside it and left running by
the stop, the stop verified, the lock released, and the decoy then stopped the same way.

## 4. For ChamPBH

- **What changes:** its README §4.1 "The cluster" (and its prompt 06, written and not yet
  dispatched, and later 10) replace `ray status`/`ray start --head`/`ray stop` with the lock and
  §3, using ChamPBH's row of the table. A script beside its rehearsal scripts
  (`.documents/dk-and-rpk-migration/rehearsal/`, as SI's `ray_cluster.sh start|stop|status`) is the
  natural form; whether it is a prompt of its own (as SI's 01a) or an amendment is that campaign's
  choice.
- **Its R0 stores stay valid.** R0 ran on a default cluster; isolation changes no science value.
  Its R1 and R2 comparisons are unaffected, and the lock removes the load hazard its BBN wall-clock
  limit carries.
- **Until it lands, ChamPBH runs no rehearsal while the lock is held**, and runs no `ray stop` while
  any other project's cluster is up.

## 5. For SecondaryGWKit

SGK's rehearsal driver (`docs/handover/quadsource_atol_sweep.py:598-618`) already starts a private
in-process instance (`address="local"`) and runs no `ray stop`, so its clusters are isolated
already. What it adds is only the lock:
- take it before a rehearsal or a long build starts, with `ray_temp_dir: in-process`,
  `ray_address: in-process` and the driver's `pid`;
- release it when the build ends, or stop and ask the user if it is held.

The user expects little more SGK work (its RunRegistry extraction is finishing), so a few lines in
that campaign's protocol are enough; no script is needed.

## 6. What this brief does not ask

- No change to Ray, DatastoreKit or RayPoolKit.
- No change to any project's science code or stores.
- No automatic waiting or queueing. The user sequences rehearsals; the lock only makes a clash
  impossible and visible.
