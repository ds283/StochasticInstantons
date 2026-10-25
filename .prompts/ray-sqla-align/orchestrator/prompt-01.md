# Orchestrator — prompt 01, move `ray` and `SQLAlchemy`, with token mode named

Read [`../README.md`](../README.md) first: §0.2 (the mechanism), §0.3, §2 (01's charter and the
gates), §3, §5 and §6. Then the board ([`../IMPLEMENTATION_STATE.md`](../IMPLEMENTATION_STATE.md)),
§5.0 and §5.1. This is the campaign's only note. Its conventions are `rrk-adoption`'s note for 04
([`../../rrk-adoption/orchestrator/prompt-04.md`](../../rrk-adoption/orchestrator/prompt-04.md),
§0, "Conventions" and corrections 6, 8, 9 and 15), which 01's rehearsal repeats; they are restated
in §0 where 01 needs them, so that the agent need not read that note.

**You do not write code.** You may:
- run the suites, `pip` read-only commands, `compare_stores.py`, `stage_counts.py`, the registry's
  read-only commands (`list`, `store show`, `store fingerprint` without `--write`) on 01's own
  stores and runs, the lock's `status` and `ray_cluster.sh status`;
- read the agent's logs, records and outputs under `var/ray-sqla-align-01/`, `var/runs/` and
  `.documents/ray-sqla-align/out/`, and 01's stores through `sqlite3` with `mode=ro` URIs only;
- read SGK's repository with `git`, never changing it;
- run a probe from the session scratchpad (`orch01/`), never committing one;
- fix small residue in a follow-up commit of your own (§4).

**The prompt:** [`01-move-ray-and-sqlalchemy-with-token-mode.md`](../01-move-ray-and-sqlalchemy-with-token-mode.md)
· **Board items:** B1, P1, V0, T1–T3, D1, L1, R1–R4 · **Gates:** **FP**, **Token** · **Closes:**
nothing · **Opens:** only what the work finds · **Model:** Opus, as the prompt recommends ·
**Network:** PyPI, for the install of 2.2 alone. Nothing is pushed.

**Gate:**
- The campaign is planned (`6a6cc03`) and U4 revised (`c5af555`, `900d3f7`, `a5721f9`). `HEAD` is
  the commit that adds this note, on top of `a5721f9`, on `main`; it is the prompt's **dispatch
  commit**. The tree is clean; `git worktree list` shows the main checkout alone.
- The prompt's own Gate (its header), checked by the orchestrator (below).
- No other session runs a suite or a Ray job from this venv, or installs into it, while 01 runs.
  The orchestrator creates no file in the repository between the fix commit and the records
  commit: R's manifests must record `git_dirty` false.

## 0. What makes this prompt unusual

**It moves the venv under the whole repository, and its failure mode is a refusal at the first
`ray.init`.** SI has one venv (C1), so once 2.2 installs, every checkout runs Ray 2.59.0, and the
way back is two `pip install` lines (prompt §4). And it runs real Ray twice under the shared lock:
once to show the refusal (V0) and once for three registered builds (R). As in `rrk-adoption` 04,
**every claim in the results note is a line the agent saw, quoted, with the command that produced
it.**

**Corrections to the prompt**, each recorded in the results note as a deviation of the class given.

1. **The board section is `### 5.2`, not `### 5.1`** (`STRUCTURALLY REQUIRED`). The board's §5.1 is
   "U4 revised, before dispatch". §6's `### 5.1 After prompt 01 (<date>)` becomes `### 5.2 After
   prompt 01 (<date>)`.

2. **The `>> packages:` line names six, the manifest seven** (`STRUCTURALLY REQUIRED`). §2.8 step 5
   says each manifest names the four "beside the three git packages" and each `>> packages:` line
   "the same six". They differ by one: the manifest's `packages` is `runregistrykit.toml`'s six
   (`datastorekit`, `raypoolkit`, `ray`, `SQLAlchemy`, `numpy`, `scipy`) plus `runregistrykit`,
   which the registry records of itself (04's manifests: `datastorekit`, `raypoolkit`,
   `runregistrykit`); the `>> packages:` line is `utilities.RECORDED_DISTRIBUTIONS`, the same six
   without `runregistrykit`. **Ruled:** R4 holds when each manifest names those seven, and each
   `>> packages:` line those six, with `ray` 2.59.0, `SQLAlchemy` 2.0.55, numpy 2.4.6 and scipy
   1.17.1. The four PyPI installs print `(no recorded origin)` (board §5.1).

3. **Ray's token warning is a `logging` call, so pytest does not show it** (`NOTED`, with a probe
   added: `IMPLEMENTATION CHOICE`). Ray 2.59.0 emits `Token authentication is enabled for this Ray
   cluster…` by `logger.warning` (`ray/_private/authentication/authentication_token_setup.py:85`,
   read in SGK's venv), not by `warnings.warn`. `pytest -q` keeps captured log output for failing
   tests only, and the subprocess tests capture their children's stderr. So §2.3's "expected among
   [the new warnings]" and §2.7's "gone from both runs" cannot be measured from the suites' output.
   **Ruled:**
   - record what the suites' output holds (expected: the line in neither, before or after);
   - measure the claim directly, by one probe on each tree, in the foreground, its stderr saved to
     `$L/out/01-token.txt`: `./venv/bin/python -c 'import ray; ray.init(address="local",
     include_dashboard=False); ray.shutdown()'` on the pins alone, with `RAY_AUTH_MODE` unset
     (expected: the warning), and, after the fix, the same with `import config.ray_auth` before
     `import ray`, from the root with `PYTHONPATH=.` (expected: no warning). These start a local
     instance in Ray's default temp dir, as the suites do: they are not SI's cluster, take no lock
     and need none. They are run with SI's cluster down;
   - **Token**'s check of the suites' output (§2.9) stays, and is recorded as the weak check it is.

   Note also: `enable_token_auth_by_default` sets `os.environ["RAY_AUTH_MODE"] = "token"` in the
   process that calls it (`:64-68`, `:109-118`). So on the pins alone, after the first local
   `ray.init` of a pytest session, the rest of that session already runs in named token mode. This
   is why the pins alone do not break the suites.

4. **What R measures, and what it cannot** (`NOTED`). A driver attaching by address never logs the
   token warning, with or without the fix (README §0.2, the third route), so R's launch logs being
   free of it shows nothing by itself. R's evidence is: `start`'s output without the warning (the
   cluster's mode named, not inferred); the `gcs_server` and `raylet` environments; and the three
   drivers attaching at all, which V0 shows they cannot without the fix. **R also exercises the
   refresh**: `RunDrivers/registered_run.py:897` imports `ray` before `runpy` runs `main.py`, so
   `main.py`'s `import config.ray_auth` finds `ray._raylet` in `sys.modules` and must call
   `Config.initialize("")`. Without it the driver keeps `disabled` and is refused (SGK's second
   issue). The results note says so.

5. **The subprocess programs** (`NOTED`; measured by the orchestrator, for §2.5's check):
   - `tests/test_inflaton_trajectory_prune.py:464` is inside `_POOL_SCRIPT`, launched at `:513` by
     `subprocess.run` with **no `env=`**, so the child inherits the parent's environment, which an
     assignment to `os.environ` updates (`os.environ.__setitem__` calls `putenv`);
   - `tests/test_inventory_store.py:80` is inside `_STORE_SCRIPT`, launched at `:247` with no
     `env=`; the same file's `_main` (`:282`) passes `env=dict(os.environ, RAY_ADDRESS=…)`;
   - `tests/registered_run_helpers.py:110` is inside the stubbed program, run by `run_stubbed`
     (`:363`) and `run_the_script` (`:380`) with `subprocess_env()`, `dict(os.environ)` less
     `RAY_ADDRESS` (`:254-258`).

   **Ruled:** "no `env=`" counts as built from `os.environ` (inherited), and is not the prompt's
   stop. The agent confirms each by reading, and records it.

6. **How to wait without polling** (`IMPLEMENTATION CHOICE`; 04's correction 6). §2.8 asks for a
   `Monitor`. A subagent cannot end its turn and be woken. **Ruled:**
   - the agent copies `rrk-adoption` 04's waiter, `.documents/rrk-adoption/out/04-wait_for_line.py.txt`,
     into its scratch directory as `wait_for_line.py` (`LOG TEXT --timeout SECONDS`; it reads the
     file only, at no more than 5 Hz, and prints each new line with the time it first saw it). Its
     check script `04-check.py.txt` and its rows query `04-rows.py.txt` may be copied the same way,
     with the names changed, and the diffs recorded;
   - each wait is **one foreground Bash call**, with the tool's timeout at 600 000 ms: `--timeout
     120` for the registration line, `--timeout 420` for the launcher's line. 04's builds took 43 s
     to 2 min 16 s at loads of 35 to 135;
   - a wait that times out may be repeated **once**, and the note records it. A second time-out is
     a stop;
   - no `sleep` loop, no `pgrep -f`, no `tail -f`, and no `run_in_background` Bash call for a build
     (rule 3: the build is detached by L1's `nohup`, not held by the agent's tool).

7. **The one check after a launch** (`IMPLEMENTATION CHOICE`; 04's correction 8). The wrapper
   registers only after its imports. After each launch, wait (correction 6) for the log's `>>
   registered_run: registered as` line, then make the one check in a **single** Bash call: the
   manifest from the `>>   manifest` line; `status.json`'s `state` and `pid` against
   `$L/<slug>.pid`, its `heartbeat` and `stage`; `list`'s line for the run. Times by
   `/usr/bin/stat -f %SB`: the shell's `stat` is GNU coreutils (`/opt/local/libexec/gnubin/stat`).
   SI's registration lines begin `>> `; the stage at the check is `null` or one of `main.py`'s `** `
   banners, never a `>> ` line; a `done` homogeneous run's last stage is `Skipping gradient branch
   (--targets excludes 'gradient')`.

8. **R2's delay and its retune** (`IMPLEMENTATION CHOICE`; 04's correction 9).
   - **The banner** `STAGE 2: FULL MSR INSTANTONS` first matches the `** STAGE 2: FULL MSR
     INSTANTONS LOOKUP:` line, printed with the pool banner in the same read (04's verification
     §1.5). The delay counts from there.
   - **`<s>`** comes from R1's own log, as the waiter saw each line arrive, and from R1's rows: the
     `FullInstanton`, `SlowRollInstanton` and `CompactionFunction` timestamps and the last
     `efold_value` minted, read after R1 has closed and after its `store create` and `store
     fingerprint --write`, through `sqlite3` with `file:…?mode=ro` URIs only. 04 chose 33 s
     against its reference's narrow window (+32.2 to +42.6 s, at a load of 135) and landed 1.5 s
     into STAGE 3. The agent aims inside R1's narrow window (some `FullInstanton` rows stored,
     others not), says why, and records the load at the launch.
   - **What counts** is the prompt's: a signal that leaves any stage incomplete. A narrow miss is
     recorded, not retuned. A signal that lands after the last stage, or that `interrupt_when.py`
     does not send because the driver had ended, is retuned.
   - **A retune needs a fresh store, and the old one is kept.** The second attempt is store
     `resumed-2`, build `resumed-a-2` (and `-3` for the third); R3 then uses the last attempt's
     store, with the slug `resumed-c` unchanged. Nothing is deleted; every attempt's run and store
     are in R's table. The prompt allows two retunes; a third miss is a stop.
   - **The clocks**: the local zone is GMT, `+0000`, since 01:00 today, so the stores' naive local
     timestamps, the wrapper's local times and `interrupt_when.py`'s UTC agree without conversion.

9. **Each manifest's `results_store_id`** (`STRUCTURALLY REQUIRED`; 04's correction 13). `begin`
   reads the store's sidecar when there is one. So `reference` and `resumed-a` (and any retune)
   begin with none, `null`; `resumed-c` begins after R2's `store create`, with the resumed store's
   `store_id` as `store show` prints it. Any other value is a stop.

10. **The fingerprints** (`IMPLEMENTATION CHOICE`; 04's correction 14). The fingerprint in
    `resumed-c`'s status, the sidecar's after it, and `store fingerprint` on the closed resumed
    store are one digest, or that is a stop. FP's failure is the prompt's stop: finish the
    protocol, stop the cluster, record both fingerprints' per-class detail and `compare_stores`'s
    full output, change nothing, and stop before the records commit.

11. **The lock and the process table** (`STRUCTURALLY REQUIRED`; 04's correction 15, and
    `CLAUDE.md`). The lock is RayPoolKit's `raypoolkit.rehearsal_lock`, contract `docs/rehearsal-lock.md`
    at `v0.3.0`, §6 above all:
    - **`ray_cluster.sh start`, `stop` and `status` are each the only process of their Bash call,
      output redirected to a file, never piped** (`… > <scratch>/start.txt 2>&1`, then the file
      read), the exit status recorded with the builtin `echo $?`;
    - no `PURPOSE` names `/tmp/ray-si`, and **no command line of the agent's names it**, ever: no
      `cat`, `grep`, `ls` or `tail` of `/tmp/ray-si/…`;
    - `start` exits 3 if the lock is held or its old location exists, and 4 if a port is held or a
      cluster process is alive: **either is a stop and ask**, never a wait, never a retry;
    - V0's driver, R's builds, the waiters and the `ray` CLI commands each run in their own Bash
      call, never in one with a lock command; `stop` runs with no build, waiter or signaller alive;
    - **no `ray stop`, ever.**
    SGK is working (`levin-phase-floor` 01 and `handover` 11 were dispatched today, SGK `757ef01`),
    so the lock may be held when V0 or R starts: that is a stop, never a wait.

12. **The cluster's environment** (`NOTED`, measured by the orchestrator). `ps -E -ww -o command=
    -p <pid>` prints a process's environment after its command on this macOS for a binary of the
    venv (probed with the venv's `python`: the variable was found). Pipe it to `grep -o
    'RAY_AUTH_MODE=[a-z]*'` only; never print the whole environment. If either pid shows no
    environment at all (a control `grep -c 'PATH='` of 0), record that and go on: the orchestrator
    rules on that item of **Token** at review. It is not a stop.

13. **The final token grep is meaningful** (`NOTED`, measured without reading the token). `wc -lc`
    on `~/.ray/auth_token` gives 0 newlines and 64 bytes, so `grep -F -f` reads one pattern of 64
    characters, and no empty pattern that would match every file. Exit 1 is the pass; exit 0 lists
    a file (delete that copy, report it); exit 2 is an error, and a stop.

14. **The load** (`NOTED`). 18 to 34 at 18:15, and 73 to 85 at 18:24 after the baselines, with no
    SI process (a backup, Spotlight and the user's applications). No solve depends on it; only R2's delay does. Record the one-minute load at each
    start and launch. If it is over 50 at `start`, stop and ask.

15. **Citations of Ray 2.55.1 stay** (`NOTED`). `RunDrivers/registered_run.py:72`, `:81` and
    `tests/registered_run_helpers.py:27` cite Ray 2.55.1's source and 04's measurement: history,
    not the pin. They are out of scope (prompt §5). `git grep` finds no other live statement of
    either old version outside `requirements.txt` and the campaigns' records.

**What the orchestrator measured at `a5721f9`** (2026-10-25, 18:15–18:30 GMT). Pass them on.
- **The prompt's Gate.** `main` at `a5721f9`, `git status --porcelain` empty, no stash, the main
  checkout alone. `runregistrykit list`: the four runs of `rrk-adoption` 04, `done`, `killed`,
  `lost`, `done`: none `running`, stale or unknown. `env | grep -c RAY_AUTH_MODE` 0; no `RAY_*`
  variable set. The venv: Python 3.13.16, `ray==2.55.1`, `SQLAlchemy==2.0.46`, numpy 2.4.6, scipy
  1.17.1, `datastorekit` at `f47b9a255e9a…`, `raypoolkit` at `67a75b97a656…`, `runregistrykit` at
  `0bae3a3c501a…`, none editable; `pip freeze` 84 lines (kept as `orch01/pip-freeze-before.txt`).
  `ls -l ~/.ray/auth_token`: `-rw------- … 64 Oct 25 12:51`; `/usr/bin/stat`: 12:51:17. The lock's
  `status`: free, `~/.raypoolkit/rehearsal-lock` does not exist. `ray_cluster.sh status`, exit 0:
  lock free, no Ray process of `/tmp/ray-si`, ports 6390, 6391, 8266 and 52366 free; no `gcs_server`
  or `raylet` on the machine. Neither `var/ray-sqla-align-01/` nor `.documents/ray-sqla-align/`
  exists; `var/datastores/` holds only 04's two retired sidecars.
- **The line numbers** the prompt cites hold: `requirements.txt:58` and `:68`;
  `ray_cluster.sh:249` (`cmd_start`), `:287` (`"$RAY_BIN" start --head`), `:322` (the `actors:`
  line), usage at `:44`; `CLAUDE.md:35-38`; `test-selection.md:10`, `:26`, `:60-61`; `main.py:131`
  (`ray.init` at module level, `import ray` at `:7`); `plot_InstantonSolutions.py:1207` and
  `plot_GradientCoupledSolutions.py:973` (each inside a function); `tests/conftest.py`'s `import ray`
  at module level and `ray.init` inside `live_pool`.
- **SGK** at `3f75bbf`: `config/ray_local.py`, `RunDrivers/tests/test_ray_auth_mode.py` and
  `prompts/py313-venv/` unchanged since `effba46`, the README's reading.
- **04's tools** for reuse, under `.documents/rrk-adoption/out/`: `04-wait_for_line.py.txt`,
  `04-check.py.txt`, `04-rows.py.txt`, `04-ray_state.sh.txt`. `interrupt_when.py`: `log pidfile
  --banner B --after S [--poll P]`, `SIGTERM` only. `compare_stores.py`: `PRIMARY A B`, `--json
  OUT`; exit 0 equal, 1 different, 2 unreadable. The registry at `v0.2.0`: `store create --purpose
  TEXT PRIMARY`; `store fingerprint [--write] PRIMARY`; `store show PRIMARY`; `list`.
- **04's reference** for comparison: stages 34.8, 42.9, 23 and 7.46 s, 2 min 16 s, at a load of 135
  (verification §1.3); `resumed-c` 43 s.
- **Baselines**, serially, at `a5721f9`: see §1.

**What moves on purpose:** the prompt's three commits: `requirements.txt` (the first); §2.7's ten
paths (the second); the results note, `.documents/ray-sqla-align/out/`, the board and
`.prompts/INDEX.md`'s line (the third), with `.documents/OPEN-ISSUES.md` only if an issue opens. The
venv's `ray` and `SQLAlchemy`. Outside the repository, only what Ray writes: the lock under
`~/.raypoolkit/` (by `start`, removed by `stop`), `/tmp/ray-si/`, and Ray's default temp dir for the
local instances of the suites and correction 3's probes.

**What must not move:** `~/.ray/auth_token` (never printed, copied, regenerated or chmodded);
every other pin and the interpreter; `utilities.py`, `runregistrykit.toml`, `RunDrivers/`; every
file under `ComputeTargets/`, `Numerics/`, `Interpolation/`, `Datastore/`; every test but the new
`tests/test_ray_auth.py` and the one import in `tests/conftest.py`; the rehearsal directory but
`ray_cluster.sh`'s T2 lines; every record of another campaign; SGK, ChamPBH and the three packages;
04's sidecars and run records. `var/` is not committed and nothing in it is deleted.

**Conventions.** All of these bind the agent.
- **Staging and reporting.** Three commits (C6), each staged by explicit path only, after showing
  `git diff --cached --name-only`. Count, then paste. "this commit" where the third's SHA goes.
- **Suites.** `./venv/bin/python -m pytest -m "not integration and not slow" -q -p no:cacheprovider
  -W default` and `RAY_ADDRESS=local ./venv/bin/python -m pytest -m integration -q -p
  no:cacheprovider`, serially, in the foreground, output to `$L/out/01-suites.txt` (each block
  headed by its command), the verdict and the warnings summary grepped, `uptime` beside each.
  **Never with SI's cluster up, and never with `RAY_ADDRESS` naming it.** A failure is re-run alone
  before it is called real.
- **Scratch** is the agent's own subdirectory of the session scratchpad, never `/tmp`, and never in
  the repository: R's manifests must record `git_dirty` false, so **no file is created in the tree
  between the fix commit and the end of R4**, results-note drafts included.
- **The outputs** under `$L/out/` as §1 of the prompt lists, plus: the three launch logs and any
  retune's; the `interrupt_when.py` log; each run's `manifest.json` and `status.json`; the checks;
  every `list`, `store` and `stage_counts.py` output; `compare_stores.py`'s output; the cluster's
  record (`start`, `ray status`, the two environment matches, `stop`, `status`); the rows query and
  its result; correction 3's probes; the scratch scripts as `.txt`, with their diffs from 04's.
  Copied to `.documents/ray-sqla-align/out/` in §2.9 with ANSI codes removed from logs
  (`sed -E 's/\x1b\[[0-9;]*m//g'`), JSON unchanged; not the run directories' `stdout.log` and
  `stderr.log`. A file over about 1 MB is reported before committing.
- **Stop conditions are real**: the prompt's §4, and corrections 6, 8, 9, 10, 11, 13 and 14 here.
  SI's cluster is stopped first, unless the stop is what failed. A stop after the install says
  that the venv holds the new versions. A stop goes to the user through the orchestrator; the
  agent resumes by message.
- **Other sessions** may land commits on `main`. Check `git log` before each commit.

## 1. Before you dispatch

1. The Gate, as §0's facts.
2. **Baselines**, both suites serially at `a5721f9` (`orch01/baseline-suites.txt`), with the load.
3. `pip freeze` kept for the review (`orch01/pip-freeze-before.txt`).
4. **The commit of this note**, alone, staged by path.

**Done at dispatch (2026-10-25):** the Gate as §0; `pip freeze` as `orch01/pip-freeze-before.txt`;
the baselines at `a5721f9`, serially: default **848** (847 passed, 1 skipped, 141 deselected, 10
warnings), 164 s, load 11 → 28; `RAY_ADDRESS=local … -m integration` **72** (71 passed, 1 skipped,
1 warning: Ray's `FutureWarning` on `RAY_ACCEL_ENV_VAR_OVERRIDE_ON_ZERO`), 229 s, load 28 → 85.
README §0.4's counts. The load at the end came from a backup (ChronoSync), Spotlight and
`WindowServer`, none of them SI's or Ray's; the lock was free after it.

## 2. Dispatch

One fresh-context subagent, on **Opus**, in the main checkout. Give it the prompt, the README, the
board, `HEAD`, the baselines, and §0 of this note up to "## 1. Before you dispatch", as a copy in the
session scratchpad. The agent does not read `orchestrator/`.

Tell it plainly:
- **Three commits** (C6): the pins (§2.3), the fix (§2.7), the records (§2.9), each staged by
  explicit path after showing `git diff --cached --name-only`.
- **§0's corrections** bind it, each recorded with its class.
- **The token is never printed, copied or changed**; it is read only by `ls -l`/`stat`, and by the
  final `grep -F -l -f`.
- **Lock commands: one per shell command, output to a file, no pipe** (correction 11). A held lock
  is a stop, never a wait.
- **The breakages** are recorded as diffs that `git apply` replays from a clean tree at the fix
  commit, checked with `git apply --check` and `-R --check`, never committed.
- **Stop and ask** on any of the prompt's §4 conditions or §0's. The cluster is stopped first.
- **It replies with:** the three commits' SHAs, messages and `--stat`; the dry run, the freeze diff
  and `pip check`; both suites at each of the three points (2.1, 2.3, 2.7), with counts, time, load
  and new warnings; correction 3's two probes; V0 line by line (`start`'s exit and whether it
  carried the warning, the driver's refusal lines and exit status, `stop` and `status`); the three
  subprocess sites as read; `config/ray_auth.py` and `ray_cluster.sh`'s diff whole; T3's tests by
  name, with the standalone time; B1–B4, each with what caught it; L1's diff from 04's launcher; R:
  `start`'s output, `ray status`, the two environment matches, then each run (id, slug, store,
  state, exit, wall time, `results_store_id`, fingerprint at finish), `<s>` and how it was chosen,
  with the times it came from, the signal's lines, `stage_counts.py` for each, `compare_stores`'s
  result, the manifests' `git_head`, `git_dirty` and `packages`, each log's `>> packages:` line,
  and `stop` with its exit; the token checks of §2.9 and the final grep's exit; every deviation with
  its class.

## 3. The review — eleven checks

1. **Scope.** `git show --stat` of each commit: the first is `requirements.txt` alone, two lines;
   the second exactly §2.7's ten paths; the third the records. `git diff --name-only <dispatch>
   HEAD` is acceptance 6's list. `git diff <dispatch> HEAD -- utilities.py runregistrykit.toml
   RunDrivers ComputeTargets Numerics Interpolation Datastore` empty. `git status --short` clean;
   `var/` not in a commit; nothing pushed.
2. **The venv, measured here.** `pip freeze` against `orch01/pip-freeze-before.txt`: exactly the
   `ray` and `SQLAlchemy` lines moved; the git packages unmoved and not editable; `pip check` clean;
   `pip install --dry-run -r requirements.txt` installs nothing. `01-pip.txt` has the dry run before
   the install, the two packages alone.
3. **The token file, here.** `ls -l` and `/usr/bin/stat`: 64 bytes, mode 600, 12:51:17. `grep -r -F
   -l -f ~/.ray/auth_token .documents/ray-sqla-align/ .prompts/ray-sqla-align/` exits 1, and so
   does the same over the three commits' blobs (`git grep -F -l -f ~/.ray/auth_token HEAD`).
4. **The fix, by reading.** `config/ray_auth.py` as §2.5 T1 says: the constant; the set only when
   absent; the refresh only when `ray._raylet` is imported; no Ray import; the licence header; the
   comment's four points in SI's voice. The four importers: one line each, module level, before
   `ray.init`, nothing else changed. `ray_cluster.sh`: the export before `"$RAY_BIN" start`, with
   the `:-token` default and its comment; the `actors:` line; the usage sentence; no hunk in the lock
   half, the stop or the ports. `bash -n` on it and on L1.
5. **T3 and the breakages.** `tests/test_ray_auth.py`'s tests cover §2.5's four groups, start no
   Ray, write nothing; it runs here standalone, with its time. Each of B1–B4 replayed here with `git
   apply` from the clean tree, its check run, its failure seen, and reverted (`git status` clean).
6. **V0, from `01-v0.txt`.** `start` 0 with `Token authentication is enabled` in its output; the
   driver's refusal lines (`InvalidAuthToken`/`AuthenticationError`) and non-zero exit; `stop` 0;
   `status` free, no SI process, ports free.
7. **The runs, from the registry.** `list` shows R's runs (and any retune): `reference` `done`,
   `resumed-a` `killed`, `resumed-c` `done`. Each `manifest.json` and `status.json` under
   `var/runs/` against the committed copies and the table: state, exit code, `script_sha256`
   against `shasum -a 256 main.py`, `results_store_id` (correction 9), `git_head` the fix commit,
   `git_dirty` false, `packages` (correction 2). Each log's `>> packages:` line (correction 2).
8. **R2's signal and delay.** The wrapper's `killed` line, `** driver exit status 143`, the
   launcher's 143. Re-read R1's rows by the same read-only query: `<s>` follows correction 8 from
   them; `stage_counts.py` on the logs and the prune lines at `resumed-c`'s open match the account.
9. **The stores, re-measured.** `compare_stores.py` on the two stores: equal but for bookkeeping.
   `store fingerprint` on each, without `--write`: `a9f716fb…1ea7`, each equal to its sidecar's.
   `store show` on each: the runs as logged.
10. **The records.** The results note in `dk-and-rpk-migration` README §5.1's form, every deviation
    classed (§0's among them), the commands verbatim, SGK's two issues named. The board: header (01
    landed, awaiting review), the §1 row, the items, the gates **FP** and **Token**, `### 5.2 After
    prompt 01` (correction 1) with the first two SHAs in full. `INDEX.md`'s line. `OPEN-ISSUES.md`
    untouched unless an issue opened, and then in the same commit. `CLAUDE.md` and
    `test-selection.md` stating the new counts, consistent with check 11. Messages end with the
    `Co-Authored-By` line.
11. **The suites** at the third commit, serially, with no cluster up: default 848 + T3's (one skip),
    `integration` 72 (one skip). Correction 3's second probe, re-run here: no warning. Then `ray_cluster.sh
    status` (a command of its own): lock free, no SI process, ports free. `runregistrykit list` the
    same runs, and `var/` the same files.

## 4. After the review

If it passes, residue first, in a follow-up commit of its own:
- "this commit" → the third commit's SHA, on the board, in the results note and in `INDEX.md`;
- the board's list of orchestrator notes, with this one marked "used for 01";
- prompt 01 left as it ran; the review names corrections 1, 2 and 3.

Then **the close**, one commit of the orchestrator's (README §2: the review of 01 closes the
campaign): the board's header (**CLOSED — 1 of 1 landed and reviewed**), its §1 row, the gates,
`### 5.3 Review and close (<date>)` holding what each check found, and the campaign's line in
`.prompts/INDEX.md` with the header's count and date. Anything that is not residue is opened on the
board's §3 and in `OPEN-ISSUES.md` instead, in the same commit.

**Report to the user:** the three commits; the venv on `ray` 2.59.0 and `SQLAlchemy` 2.0.55; V0's
refusal; the fix and what guards it; R and the fingerprints; the stores left under `var/datastores/`
for the user to retire (README §3); that nothing is pushed; and what README §7 hands to ChamPBH.
