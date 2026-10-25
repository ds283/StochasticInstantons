# Orchestrator — prompt 04, rehearse registered runs

Read [`../README.md`](../README.md) first: §0.2 (what the wrapper does), §0.3 (the rehearsal
tooling and RH2's stage times), §2.2 (04's charter), §3, §5 (the one-off exception, the cluster and
lock rules, "No agent polls a run") and §6 (U2, P8–P10). Then the board's §5.5 (03's record and
review, and its "For 04's note"). The conventions are note 02's ([`prompt-02.md`](prompt-02.md),
which carries `dk-and-rpk-migration`'s [`prompt-01.md`](../../dk-and-rpk-migration/orchestrator/prompt-01.md)
§0 "Conventions"), restated in §0 where 04 needs them. ChamPBH ran the same rehearsal on
2026-10-19; its orchestrator note for 04 (`prompts/rrk-adoption/orchestrator/prompt-04.md` at
ChamPBH `98e001b`) ruled twelve points, and most of them carry. They are restated below in SI's
terms, so that the agent need not read ChamPBH's note.

**You do not write code.** You may:
- run the suites, `compare_stores.py`, `stage_counts.py` and the registry's read-only commands
  (`list`, `store show`, `store fingerprint` without `--write`) on 04's own stores and runs;
- read the agent's logs, records and outputs under `var/rrk-adoption-04/`, `var/runs/` and
  `.documents/rrk-adoption/out/`, and 04's stores through `sqlite3` with `mode=ro` URIs only;
- run a probe from the session scratchpad (`orch04/`), never committing one, and never starting Ray;
- fix small residue in a follow-up commit of your own (§4).

**The prompt:** [`04-rehearse-registered-runs.md`](../04-rehearse-registered-runs.md) · **Board
items:** H0–H6 · **Gate:** "R" · **Closes:** nothing · **Opens:** only what the work finds ·
**Model:** Opus, as the prompt recommends · **Network:** none. Nothing is pushed.

**Gate:**
- 01 (`60687f0`, `7071bb8`), 02 (`0fcaf7c`, reviewed `ff3ddd6`) and 03 (`16e1cc1`, reviewed
  `edb03ea`) landed; the gates **Pin**, **Fingerprint** and **Wrapper** hold (board §2). `HEAD` is
  the commit that adds this note, on top of `edb03ea`, on `rrk-adoption`; the tree is clean;
  `git worktree list` shows the main checkout alone.
- The prompt's own gate (its header), checked by the orchestrator (below).
- No other session runs a suite or a Ray job from this venv, or installs into it, while 04 runs.
  05 is not dispatched until 04 is reviewed.

## 0. What makes this prompt unusual

**It is the only prompt of the campaign that runs real builds, and it kills two of them on
purpose.** Nothing in it is code but the launcher. What it produces is a record: that the
registry's account of four builds is what happened to them, under real Ray, attached to SI's
isolated cluster. A mistake here is not a wrong value but a wrong claim in the verification
document, so **every claim in it is a line the agent saw, quoted, with the command that produced
it.**

**Corrections to the prompt**, each recorded in the results note as a deviation of the class given.

1. **The board section is `### 5.6`, not `### 5.5`** (`STRUCTURALLY REQUIRED`). §5.5 is 03's.
   Acceptance 5's `### 5.5 After prompt 04` becomes `### 5.6 After prompt 04 (<date>)`.

2. **What may be written** (`STRUCTURALLY REQUIRED`). Acceptance 3 says nothing outside `var/` and
   `.documents/rrk-adoption/` is written; acceptance 5 puts the board in the commit, and
   `CLAUDE.md`'s maintenance rule moves `.prompts/INDEX.md`'s campaign line (status 4 / 5) with it.
   **Ruled:** the commit holds the launcher, the results note, `verification.md`, the
   `out/04-*` files, the board and `INDEX.md`'s one line; `OPEN-ISSUES.md` only if an issue opens,
   in the same commit. Outside the repository, only what the cluster writes: the lock under
   `~/.raypoolkit/` (by `start`, removed by `stop`) and `/tmp/ray-si/`. Scratch goes to the agent's
   own subdirectory of the session scratchpad.

3. **The `SIGTERM`ed drivers of `dk-and-rpk-migration` exited 15, not 134** (`NOTED`, and the
   record states both). Step 4 says they exited 134. RH2's `resumed-a` exited **15**, and RH1's
   attempts 15 and 1 (`.documents/dk-and-rpk-migration/11-rehearse-through-both-packages.md`,
   "L1", and its line "`resumed-a`'s exit status 15 is within the prompt's 134, 15 or 1"): Ray's
   Python handler turned the signal into `sys.exit(15)`. 134 is what ChamPBH saw before its wrapper,
   and `interrupt_when.py`'s docstring cites ChamPBH's board for it. RH2's log also has absl's
   `*** SIGTERM received at time=…` banner, twice, with its stack. **So P9's measurement is,
   against RH2:** the exit status (143 expected, 15 for RH2); whether absl's `*** SIGTERM received`
   banner appears (it did in RH2; with the wrapper's handler installed after `ray.init` returns, it
   should not); and whether `** cancelled an alarm` appears (it should not). A 143 with no absl
   banner and no alarm line is the expected result. Any other exit status is a stop (§3, "a record is
   wrong"); a banner or an alarm line with 143 is recorded as a finding, not a stop.

4. **P9 needs a positive measurement, not only an absent line** (`IMPLEMENTATION CHOICE`, ChamPBH's
   ruling 8). An absent alarm line does not show that `ray.init`, attached to an external cluster,
   installs Ray's own Python handler. After `start` and before H1, one probe, from the repository
   root:

   ```bash
   ./venv/bin/python -c 'import signal, ray; a = signal.getsignal(signal.SIGTERM); ray.init(address="127.0.0.1:6390"); b = signal.getsignal(signal.SIGTERM); print("before", a); print("after", b, getattr(b, "__module__", None), getattr(b, "__qualname__", None)); ray.shutdown()'
   ```

   Record its output and the job it adds (`ray list jobs --address 127.0.0.1:6390`). It opens no
   store and runs no solve. The four builds and this probe are five Ray jobs; the refused launch of
   step 5 reaches no `ray.init` and adds none.

5. **SI's registration lines begin `>> `** (`NOTED`; 03's correction 4). They are
   `>> registered_run: registered as <id>`, `>>   manifest <path>` and `>>   list it with: …`
   (`RunDrivers/registered_run.py:866-870`), not ChamPBH's `** registered_run:`. Every wait, check
   and order test below uses SI's form. So:
   - at the one check, `status.json`'s stage is `null` or one of `main.py`'s `** ` banners
     (`BUILDING PARAMETER SAMPLING GRIDS`, `COSMOLOGICAL PARAMETERS: …`, `DIFFUSION MODEL: …`, a
     `STAGE …` title or its `… LOOKUP:` line), **never** a `>> ` line: not `>> packages:`, not
     `>> Created sharded datastore …`, not a registration line;
   - a `done` homogeneous run's stage is `Skipping gradient branch (--targets excludes 'gradient')`,
     `main.py`'s last `** ` line (03's observation 3);
   - the handler's line (stderr) is `** SIGTERM at <local time>: recorded killed, exit code 143;
     stopping main.py; the process will exit with status 143` (`:456-461`), possibly followed by
     `** SIGTERM: main.py ended with SystemExit(1); recording killed, exit code 143` (`:536-540`);
     the alarm line is `:516-519`; the marker `** driver exit status N` is printed last, on a line
     of its own (`:978`), and there is none after a `SIGKILL`.

6. **How to wait without polling** (`IMPLEMENTATION CHOICE`, ChamPBH's ruling 3). The prompt asks
   for a `Monitor`. A subagent cannot end its turn and be woken. **Ruled:**
   - the agent writes one waiter in its scratch directory, `wait_for_line.py LOG TEXT --timeout
     SECONDS`. It reads `LOG` until a line contains `TEXT`, prints that line with the time (UTC, to
     0.1 s), and exits 0; at the deadline it exits 1. It reads the file only: no `pgrep`, no
     `kill -0`, no Ray. It may also print each new line of the log with the time it first saw it
     (to time the banners: correction 9), polling at no more than 5 Hz;
   - each wait is **one foreground Bash call**, with the tool's timeout at 600 000 ms: `--timeout
     120` for the registration line, `--timeout 420` for the launcher's line. RH2's builds took
     28–40 s;
   - a wait that times out may be repeated **once**, and the note records it. A second time-out is
     a stop: a build of about 40 s that has not ended in 14 min is not healthy;
   - no `sleep` loop, no `pgrep -f`, no `tail -f`, and no `run_in_background` Bash call for a build
     (rule 3: the build is detached by `nohup`, not held by the agent's tool).

7. **H0, the launcher** (`IMPLEMENTATION CHOICE` for its interface; the requirements are the
   prompt's and these). `.documents/rrk-adoption/rehearsal/build_registered.sh`, after `build.sh`,
   with `build.sh`'s licence header and a header giving the usage and naming this prompt:
   - it takes the store's slug, the build's slug, the address and the purpose, and optionally a
     slug for the launch files (for correction 12's refused launch); it checks each as `build.sh`
     does, each refusal one `!! ` line, exit 2; it refuses to overwrite a log; it runs from the root;
   - it runs `PYTHONPATH=. ./venv/bin/python -u RunDrivers/registered_run.py --campaign
     rrk-adoption --prompt 04 --register <build> --purpose "<purpose>" -- <§1.1's arguments>` with
     the driver's stdout and stderr to `$L/<slug>.log`, writes `$!` to `$L/<slug>.pid` at once,
     `wait`s on it, and appends `** launcher saw exit status N`. It appends **no** `** driver exit
     status` line: the wrapper prints that, and `build.sh`'s second marker is the reason this
     launcher exists (03's observation 2);
   - the driver's pid is the wrapper's Python process (`runpy` runs `main.py` in it), so the pid file
     and `status.json`'s `pid` are one number;
   - **detached** (rule 3): either the launcher detaches itself (`nohup … &`, with its output away
     from the caller) and returns at once, or one Bash call runs `nohup bash build_registered.sh …
     > /dev/null 2>&1 &`. Either way a `bash` waits on the driver and reaps it, so that `end` is not
     refused by an unreaped process (RunRegistryKit's `[04-a-killed-process-not-yet-reaped-answers-kill-0]`).
     The note says which, and quotes the launch line exactly as run;
   - `$S` and `$L` are **absolute** (`$PWD/var/datastores`, `$PWD/var/rrk-adoption-04`), so that
     the wrapper and `list` agree on the store's path. The manifest still records `results`
     relative to the client root;
   - it starts and stops no cluster, and no command line it creates names `/tmp/ray-si`
     (correction 15). It is the one script committed; `bash -n` passes on it.

8. **The one check after a launch must not race the registration** (`IMPLEMENTATION CHOICE`,
   ChamPBH's ruling 4). The wrapper registers only after its imports. After each launch, wait
   (correction 6, `--timeout 120`) for the log's `>> registered_run: registered as` line, then make
   the one check in a **single** Bash call:
   - the manifest's path from the `>>   manifest` line, and that it exists;
   - `status.json`'s `state` and `pid`, against `$L/<slug>.pid`; its `heartbeat` against the time
     of the call (the heartbeat's age: `list`'s `AGE` is the run's age since `created`,
     `runregistrykit/__main__.py:652`) and its `stage`;
   - `list`'s line for the run;
   - the manifest's `created` against the log's birth time, by **`/usr/bin/stat -f %SB`**. The
     shell's `stat` is GNU coreutils (`/opt/local/libexec/gnubin/stat`), whose `-f` means something
     else (RH2's deviation D1).

   **The manifest is written before the driver's first line** is shown by the log's order: the three
   `>> registered_run` lines come before `main.py`'s first line, `>> packages: …`.

9. **Choosing H2's delay without a profile database** (`IMPLEMENTATION CHOICE`, after ChamPBH's
   ruling 6). RH2 timed the `STAGE 2` banner by its profile database; §1.1 drops `--profile-db`, so
   that route is gone. **Ruled:**
   - the banner's time comes from H1's own log, as the waiter saw each line arrive (correction 6),
     or, if that was not recorded, from the trajectory row's timestamp plus RH2's measured gap
     (trajectory stored 21:29:20.994, banner about 21:29:21.87: +0.9 s);
   - the rows' times come from the reference store after H1 has closed, and after its `store create`
     and `store fingerprint --write`: `FullInstanton.timestamp` on each shard, the last
     `efold_value` minted, and the first and last `SlowRollInstanton` and `CompactionFunction`
     stored, read through `sqlite3` with `file:…?mode=ro` URIs only, as RH2's `rows.py` read them.
     Record the query and the times;
   - **the clocks went back at 01:00 today** (2026-10-25): the local zone is GMT, `+0000`, so the
     stores' naive local timestamps, the wrapper's local times and `interrupt_when.py`'s UTC agree
     with no conversion. RH2's times are BST, `+0100`;
   - `<s>` aims inside the **narrow window** (some `FullInstanton` rows stored and validated, others
     not), as RH2 did (12.0 s, between the eighth and ninth rows, at a load near 55), saying which
     rows it expects stored, and with the load at the time. The prompt's retune rule is README
     §4.1's, and so is its window: a signal anywhere from the first `FullInstanton` stored to the
     last `CompactionFunction` stored leaves a partial store and is **in the window**; a narrow miss
     inside the wide window is recorded, not retuned. A signal that lands before the first row, or
     that `interrupt_when.py` does not send because the driver had ended, is outside it;
   - **a retune needs a fresh store, and the old one is kept.** The second attempt is store
     `rrk-adoption-04-resumed-2.sqlite`, build `resumed-a-2` (and `-3` for a third); H3 and H4 then
     use the last attempt's store, with the slugs `resumed-b` and `resumed-c` unchanged. Nothing is
     deleted; every attempt's run and store are recorded in the table. A third miss is a stop.

10. **H3, the kill** (`IMPLEMENTATION CHOICE`, ChamPBH's rulings 2 and 6). `interrupt_when.py` sends
    only `SIGTERM` and runs unchanged. **Ruled:**
    - the agent copies it into its scratch directory as `kill_when.py`, changes `SIGTERM` to
      `SIGKILL` in the signal sent and in its messages, and nothing else. The diff between the two
      is recorded; the copy is committed only as text, `out/04-kill_when.py.txt`. The rehearsal
      directory is not touched. It signals the pid in `$L/resumed-b.pid` alone, which is the
      prompt's "by pid alone";
    - **the banner and the delay** follow from `resumed-a`'s state (`stage_counts.py` on its log; its
      rows read `mode=ro` after it) and H1's banner arrival times. They aim inside a stage that
      `resumed-b` still has work in, after its banner, at no more than half that stage's time in H1
      and at least 2 s, so that work remains: for RH2's pattern that is `STAGE 3: SLOW-ROLL
      INSTANTONS` (9.6 s in RH2's reference; `resumed-b`'s `STAGE 2` recomputes only what
      `resumed-a` left, about 9 s). The note says how they were chosen;
    - an outcome other than expected (no `SlowRollInstanton` row stored, or all) is **recorded, not
      a stop**: the store is partial whatever stage remains. If `kill_when.py` sends nothing because
      the driver had ended, the store is whole and the hard-kill route was not rehearsed: **stop and
      ask**.

11. **What a `SIGKILL` leaves behind** (`IMPLEMENTATION CHOICE`, ChamPBH's ruling 9). `ray_cluster.sh
    status` lists processes whose command names `/tmp/ray-si` and their descendants (RayPoolKit's
    `docs/rehearsal-lock.md` §6 at `v0.3.0`); a Ray worker shows only `ray::<name>`. **Ruled:** at
    each of four points record `ray_cluster.sh status`, `./venv/bin/ray list workers --address
    127.0.0.1:6390 --filter "is_alive=True"` (or the filter Ray 2.55.1 accepts, as run), `ray list
    actors --address 127.0.0.1:6390 --filter "state=ALIVE"` and `ray list jobs --address
    127.0.0.1:6390`. The points: after `start` (the baseline), after H1, after H2, and straight after
    H3's kill. **A process left behind** is a live worker or actor of `resumed-b`'s job, or an
    `/tmp/ray-si` process not in the baseline. If there is one, wait for it **by pid**, with a waiter
    of correction 6's form that tests `kill -0` on that pid alone; the ten-minute limit is the
    prompt's §3. After the kill, also list the resumed store's directory: any `-journal`, `-wal` or
    `-shm` file beside the primary or a shard is recorded (DatastoreKit reconciles it at
    `resumed-c`'s open, and that open's `>>` lines are quoted).

12. **The refused `resumed-c` keeps its own launch files** (`IMPLEMENTATION CHOICE`, ChamPBH's
    ruling 10). "Launch `resumed-c` exactly as step 6 will" would write `$L/resumed-c.log`, which
    step 6 then needs. **Ruled:** the refused launch is step 6's, with the launch files
    `$L/resumed-c-refused.log` and `.pid` and nothing else changed: `--register resumed-c`, the same
    purpose and the same `main.py` arguments, `--job-name rrk-adoption-04-resumed-c` included. Wait
    for its launcher's line, then show: exit status 2; one `!! ` line naming `resumed-b`'s run id and
    `python -m runregistrykit end`; `** driver exit status 2`; `find var/runs | sort` the same before
    and after, by `diff`; no Ray job added.

13. **What each manifest's `results_store_id` should be** (`STRUCTURALLY REQUIRED`, ChamPBH's
    ruling 11). `begin` reads the store's sidecar when there is one
    (`runregistrykit/__init__.py:1088-1107`). So `reference` and `resumed-a` (and any retune) begin
    with none, `null`; `resumed-b` and the real `resumed-c` begin after step 4's `store create`, with
    the resumed store's `store_id` as `store show` prints it. The reference's sidecar is made after
    H1 has finished, so no run carries its id. The table gives all four; any other value is a stop
    ("a record is wrong").

14. **The fingerprints** (`IMPLEMENTATION CHOICE`, ChamPBH's ruling 12). The expectation is that
    the two stores' digests are equal when `compare_stores` says equal.
    - A digest that differs where `compare_stores` says equal is **not** a stop during the
      rehearsal: finish the protocol, stop the cluster, record both fingerprints' per-class detail
      and the classes whose counts or digests differ, then **stop and ask before committing**;
    - the fingerprint in `resumed-c`'s status, the sidecar's after it, and `store fingerprint` on the
      closed resumed store are one digest, or that is a stop;
    - `store fingerprint` refuses a store an unfinished run names, so it is not run on the resumed
      store between the kill and `end`.

15. **The lock and the process table** (`STRUCTURALLY REQUIRED`; board §5.3). The lock is
    RayPoolKit's `raypoolkit.rehearsal_lock` at `~/.raypoolkit/rehearsal-lock`, whose contract is
    RayPoolKit's `docs/rehearsal-lock.md` at `v0.3.0` (§6 above all), not the brief's §2.
    `.prompts/dk-and-rpk-migration/rehearsal-lock-brief.md` is still read for the rest. From the
    contract and `CLAUDE.md`:
    - **`start`, `stop` and `status` are each the only process of their Bash call, output
      redirected to a file, never piped** (`… > <scratch>/start.txt 2>&1`), then the file read;
    - no `PURPOSE` names `/tmp/ray-si`, and **no command line of the agent's names it**: the Bash
      tool's shell carries the whole command, and a shell that names the temp dir is a seed whose
      other descendants are listed. So no `cat`, `grep`, `ls` or `tail` of `/tmp/ray-si/…`, ever;
    - `start` exits 3 if the lock is held or its old location exists, and 4 if a port is held or a
      cluster process is alive: **either is a stop and ask**, never a wait, never a retry;
    - `stop` runs with no build, waiter or signaller alive, and its exit status is recorded (the Bash
      tool reports a non-zero exit; `stop` prints `stopped in` only on success);
    - **no `ray stop`, ever.**

16. **H5 against RH2: what changed since** (`NOTED`, measured here). RH2 ran at `2179854`. Since
    then, the code that computes has changed in comments only: `ComputeTargets/GradientCoupledInstanton/picard.py`
    (one comment), `Datastore/SQL/ObjectFactories/InflatonTrajectory.py` (three comments), and
    `tools/compare_stores.py` (docstring and comments). `main.py` is unchanged since `1c223e8`.
    `raypoolkit` moved from `v0.2.0` to `v0.3.0`, whose `RayWorkPool.py` is byte-identical
    (`rpk-v030-adoption` README §0.3); `runregistrykit` was added. So bit for bit is the expectation,
    and the provenance line differs from RH2's in `raypoolkit 0.3.0 (…@67a75b97…, requested v0.3.0)`,
    which is a log line, not a stored value.

17. **`git_dirty` will be `true`** (`NOTED`). `begin` records `bool(git status --porcelain)`
    (`runregistrykit/__init__.py:163`), which counts untracked files. The launcher is untracked under
    `.documents/rrk-adoption/rehearsal/` when H1 begins, and the outputs under `out/` as they are
    copied. `var/` is ignored and does not count; at `edb03ea` `git status --porcelain` is empty.
    So `git_dirty` is `true` in every manifest, store history and fingerprint, for that reason. The
    note says so; it is not a stop. `git_head` is this note's commit.

18. **Commands not run** (`NOTED`). `store retire`, `move`, `copy`, `amend` and `adopt`; `end
    --unverified`; any `store` command on RH2's stores; `--profile-db`; a plot script; `main.py`
    other than through the launcher. RH2's stores are opened only by `compare_stores.py`
    (`mode=ro`); RH2's logs, which are text files, may be read.

**What the orchestrator measured at `edb03ea`** (2026-10-25, 11:30–11:50 GMT). Pass them on.
- **The prompt's gate.** `git status --short` empty, main checkout only. `ray_cluster.sh status`,
  exit 0: `lock: free (… does not exist)`, no Ray process of `/tmp/ray-si`, ports 6390, 6391, 8266
  and 52366 free. `runregistrykit list`: no runs. `var/` holds only the empty `var/runs/` and
  `var/datastores/`; no `var/rrk-adoption-04/`. RH2's `11-reference.sqlite`, its ten shards and its
  profile database are under `~/ScienceData/StochasticInstantons-rehearsals/dk-and-rpk-migration/`.
  `RAY_ADDRESS` is unset.
- **The venv.** Ray 2.55.1; `raypoolkit` 0.3.0 at `67a75b97…`; `datastorekit` 0.5.0; `runregistrykit`
  0.2.0. `pip freeze` kept in `orch04/pip-freeze-dispatch.txt`.
- **`main.py`**: SHA-256 `07fbf19a530584008b3e335c94335a827d050790507c0243eb4cf7dda5503744`;
  `git diff 1c223e8 -- main.py plot_InstantonSolutions.py plot_GradientCoupledSolutions.py
  utilities.py` empty.
- **RH2's reference**, by `stage_counts.py` on its log (read only): STAGE 1 1/1/1/1; STAGE 2 lookup
  0 already, 10 to compute, then 10/10/10/10; STAGE 3 likewise; STAGE 4 likewise; `Skipping
  gradient branch`; 4 `ALL WORK ITEMS COMPLETE`; exit 0. Its stages: 6.04, 12.9, 9.59 and 2.27 s.
  RH2's `resumed-b` log shows the order of lines a resume prints: `** STAGE 2: FULL MSR INSTANTONS
  LOOKUP:` before `** STAGE 2: FULL MSR INSTANTONS`, and the same for `STAGE 3`, so a banner text
  `STAGE 3: SLOW-ROLL INSTANTONS` first matches the lookup line.
- **The registry's commands** at `v0.2.0`: `store create --purpose TEXT PRIMARY`; `store
  fingerprint [--write] PRIMARY`; `store show PRIMARY`; `end RUN_ID --reason TEXT [--unverified]
  [--root DIR]`; `list [--stale-after SECONDS]`, default 900. A sidecar is `<stem>.manifest.json`
  beside the primary.
- **`compare_stores.py`**: `PRIMARY A B`, `--json OUT`, `--max-rows N`; exit 0 equal, 1 different,
  2 unreadable.
- **The load** was 41 at 11:38 (Safari, a `munki` Python and backup software, none of them SI's),
  13–31 during the baselines. RH2 ran at 32–64 and met its criteria; no solve depends on load, only
  the delays do. Record the load at each launch. If the one-minute load at `start` is over 50,
  stop and ask.
- **Baselines**, serially, at `edb03ea`: see §1.

**What moves on purpose:** correction 2's list. **What must not move:** every `.py` file;
`main.py`, the plot scripts and `utilities.py`; every test; `.claude/`; `CLAUDE.md`; the rehearsal
directory `.documents/dk-and-rpk-migration/rehearsal/`; the venv; RH2's stores; RunRegistryKit,
ChamPBH and RayPoolKit. `var/` is not committed and nothing in it is deleted.

**Conventions.** All of these bind the agent.
- **Staging and reporting.** One commit, at the end, staged by explicit path only, after showing
  `git diff --cached --name-only`. Count, then paste. "this commit" where the SHA goes.
- **Suites.** `./venv/bin/python -m pytest -m "not integration and not slow" -q -p no:cacheprovider`
  and `RAY_ADDRESS=local ./venv/bin/python -m pytest -m integration -q -p no:cacheprovider`,
  serially, in the foreground, output to a file in the scratch directory, the verdict grepped,
  `uptime` beside each. **Never with the cluster up, and never with `RAY_ADDRESS` naming it**: two
  default-selection modules call `ray.init()` with no address, which reads `RAY_ADDRESS`
  (`[default-suite-starts-ray-in-process]`, board §3). A failure is re-run alone before it is called
  real.
- **Scratch** is the agent's own subdirectory of the session scratchpad, never `/tmp`. Its scripts
  live there; run outputs go to `$L`; copies of small ones to `.documents/rrk-adoption/out/04-*`,
  logs with ANSI codes removed (`sed -E 's/\x1b\[[0-9;]*m//g'`), JSON copied unchanged. Not the run
  directories' `stdout.log` and `stderr.log`, which repeat the launch logs. A file over about 1 MB is
  reported before committing.
- **The outputs** under `out/`: the four launch logs, the refused one and any retune's; the
  `interrupt_when.py` and `kill_when.py` logs; each run's `manifest.json` and `status.json` whole;
  the checks; every `list`, `store` and `stage_counts.py` output; `compare_stores.py`'s two outputs;
  the cluster's record (`start`, correction 11's four points, `ray status`, `stop`, `status`); the
  probe; the rows query and its result; and the scratch scripts (`wait_for_line.py`, `kill_when.py`
  and any query script) as `.txt`, with `kill_when.py`'s diff.
- **Stop conditions are real**: the prompt's §3, and corrections 3, 6, 9, 10, 13, 14 and 15 here.
  The cluster is stopped first, unless the stop is what failed. A stop goes to the user through the
  orchestrator; the agent resumes by message.
- **Other sessions** may land commits on this branch. Check `git log` before committing.

## 1. Before you dispatch

1. The Gate, as §0's facts.
2. **Baselines**, both suites serially at `edb03ea` (`orch04/default.txt`, `orch04/integration.txt`),
   with the load.
3. `pip freeze` kept for the review.
4. **The commit of this note**, alone, staged by path.

**Done at dispatch (2026-10-25):** the Gate as §0; the baselines at `edb03ea`, serially: default
**848** (847 passed, 1 skipped, 141 deselected), 87 s, load 41 → 13; `RAY_ADDRESS=local … -m
integration` **72** (71 passed, 1 skipped), 111 s, load 13 → 31. 03's counts. After them,
`ray_cluster.sh status`: lock free, no SI process, ports free; no Ray process on the machine;
`var/runs/` and `var/datastores/` empty.

## 2. Dispatch

One fresh-context subagent, on **Opus**, in the main checkout. Give it the prompt, the README, the
board, `HEAD`, the baselines, and §0 of this note up to "## 1. Before you dispatch", as a copy in the
session scratchpad. The agent does not read `orchestrator/`, nor prompt 05.

Tell it plainly:
- **One commit, at the end**, with the results note `.documents/rrk-adoption/04-rehearse-registered-runs.md`
  in `dk-and-rpk-migration` README §5.1's form, `verification.md` §1 (the prompt's H6), the board's
  `### 5.6`, and `INDEX.md`'s line.
- **The files it may add or change are correction 2's list, and nothing else.**
- **§0's corrections** bind it, each recorded with its class.
- **Stop and ask** on any of the prompt's §3 conditions or §0's. The cluster is stopped first.
- **It replies with:** the commit's SHA, message and `--stat`; the launcher's usage and the launch
  line as run; the four runs (and any retune): id, state, exit code, wall time, `results_store_id`,
  the fingerprint's digest and its time at finish; the probe's output; P9's three measurements
  (correction 3) and the signal's two intervals; the two delays and how each was chosen, with the
  times they came from; the hard-kill route line by line (`stale`, the refusal, `end`, `lost`) and
  what correction 11 found after the kill; `compare_stores`' two results and the digests; the
  heartbeat ages at the checks; `start` and `stop` with their exit statuses and times; the suites
  before and after, with the load; `pip freeze` before and after; every deviation with its class;
  "State handed to the next prompt", verbatim.

## 3. The review — twelve checks

1. **Scope.** `git show --stat <agent>` is correction 2's list. `git status --short` clean.
   `git diff --name-only edb03ea <agent> -- '*.py'` empty. `git diff 1c223e8 <agent> -- main.py
   plot_InstantonSolutions.py plot_GradientCoupledSolutions.py utilities.py` empty. `var/` not in
   the commit. Nothing pushed.
2. **The venv.** `pip freeze` equals `orch04/pip-freeze-dispatch.txt`.
3. **The cluster.** `ray_cluster.sh status`, exit 0: lock free, no SI process, the four ports free;
   no `raylet`, `gcs_server` or `ray::` process on the machine. The note has `start`'s output,
   `ray status`, and `stop`'s exit status with its time.
4. **The runs, from the registry itself.** `list` shows the four runs (and any retune): `reference`
   `done`, `resumed-a` `killed`, `resumed-b` `lost`, `resumed-c` `done`. Each `manifest.json` and
   `status.json` under `var/runs/` read against the committed copies and the table: state, exit code,
   `script` and `script_sha256` against `shasum -a 256 main.py`, `results`, `results_store_id`
   (correction 13), `git_head` (this note's commit), `git_dirty` (correction 17), `scope` (03's
   literal, with each run's job name) and `heartbeat_means` (03's), and `resumed-b`'s `ended` with its
   reason.
5. **The order of the records.** In each launch log, the three `>> registered_run` lines come before
   `>> packages:`. Each manifest's `created` is no earlier than its log's birth time.
6. **H2's signal.** The handler's line, then `** driver exit status 143`, then the launcher's 143;
   no alarm line; whether absl's banner appears. Recompute the signal → `killed` interval and the
   signal → final record interval from the quoted lines and `status.json`.
7. **H3's route.** The launcher's 137 and no driver marker. The `stale` line and its stderr summary;
   the refused launch's lines and the `find var/runs` diff; `end`'s output; the `lost` record; and
   correction 11's four snapshots for anything of `resumed-b`'s job.
8. **The delays.** Re-read the reference's row timestamps by the same read-only query. Each delay
   follows corrections 9 and 10 from them; the account of what H2 and H3 stored matches
   `stage_counts.py` on the logs and the prune report at the next open.
9. **The stores, re-measured.** `compare_stores.py` on the reference and the resumed store, and on
   the reference and RH2's `11-reference`: the logged results. `store fingerprint` on each `var/`
   store, without `--write`: the logged digests, each equal to its sidecar's. `store show` on each:
   the runs as logged. `stage_counts.py` on the four logs: the logged counts.
10. **The launcher, by reading.** Correction 7's requirements: the header, the checks, the refusal
    to overwrite, the pid file, the launcher's line and no second driver marker, the `wait` that
    reaps, no `/tmp/ray-si`. `bash -n` passes. It is run from nowhere in the review.
11. **The records.** The board: header (4 of 5), row 04 landed with "this commit", H0–H6, the gate
    **R**, `### 5.6`. The note in §5.1's form, every deviation classed, the commands verbatim.
    `verification.md` §1's figures match the outputs under `out/`. Nothing is claimed that no quoted
    line shows (the heartbeat's history above all). `INDEX.md`'s line. `OPEN-ISSUES.md` untouched
    unless an issue opened, and then in the same commit. The message ends with the `Co-Authored-By`
    line.
12. **The suites** at the agent's commit, serially, with no cluster up: default 848, `integration`
    72. `runregistrykit list` afterwards shows the same runs, and `var/` the same files.

## 4. After the review

If it passes, residue in a follow-up commit of its own:
- "this commit" → the SHA, on the board, in the note, in `verification.md` and in `INDEX.md`;
- the board's list of orchestrator notes gains this one, "used for 04";
- `### 5.6` gains an *Orchestrator review of prompt 04* paragraph: what each check found.
- Prompt 04 is left as it ran; the paragraph names corrections 1, 2, 3 and 6.

Anything that is not residue is opened on the board's §3 and in `OPEN-ISSUES.md` in the same commit.

**Report to the user:** the message as committed; the corrections that read the prompt otherwise
than it was written (the section, 1; what is written, 2; 15 not 134, 3; the waits, 6); the four
runs and the hard-kill route in a few lines; P9's measurement; both comparisons and the digests;
the stores and run records left under `var/` for the user (README §3, §7); and that 05 is next, its
note to be written after this review.
