# Prompt 04 — rehearse registered runs

**Campaign:** [`README.md`](README.md) · **Board items:** **H1**–**H6** ·
**Board:** [`IMPLEMENTATION_STATE.md`](IMPLEMENTATION_STATE.md)
**Written:** 2026-10-23, after the user's rulings (README §6; U2: the hard-kill route rehearsed). It
follows `dk-and-rpk-migration`'s rehearsal protocol (that README §4.1) for the cluster, the grid
and the resume, with every build launched through the wrapper. Its orchestrator note, written after
03's review, governs where it differs from this file.
**Gate:**
- 01, 02 and 03 landed and reviewed, with the gates "Pin", "Fingerprint" and "Wrapper" holding
  (board §2);
- on branch `rrk-adoption`, no tracked change in `git status`;
- `.documents/dk-and-rpk-migration/rehearsal/ray_cluster.sh status`: the lock free, no SI process,
  SI's ports free;
- `./venv/bin/python -m runregistrykit list`: no run `running`, stale or unknown;
- neither `var/datastores/rrk-adoption-04-reference.sqlite` nor `…-resumed.sqlite` exists (nor any
  of their shards), and nor does `var/rrk-adoption-04/`;
- RH2's reference store is where `dk-and-rpk-migration` 11 left it:
  `~/ScienceData/StochasticInstantons-rehearsals/dk-and-rpk-migration/11-reference.sqlite` and its
  ten shards. (The user may remove those stores; if they are gone, stop and ask: H5's second
  comparison needs them.)

If any of these fails, stop and ask.

**Closes:** nothing. **Opens:** only what the work finds.
**Recommended model:** **Opus**. Four real builds under real Ray, two of them killed on purpose,
and the registry's records read against what happened.

**Read first:**

1. [`README.md`](README.md): §0.2, §0.3, §2.2 (04's charter), §3, §5 (the one-off exception for
   this prompt, the cluster and lock rules, and "No agent polls a run"), §6 (U2, P7–P10).
2. `CLAUDE.md`: "Build and test" and "Long-running jobs — the run registry"; and
   `.claude/rules/run-registry.md`.
3. `.prompts/dk-and-rpk-migration/README.md` §4.1 (the cluster, the grid, the builds, L1 and L2),
   §4.2 (comparing stores by value) and §4.3 (the bit-for-bit criterion);
   `.prompts/dk-and-rpk-migration/rehearsal-lock-brief.md`.
4. `.documents/dk-and-rpk-migration/11-rehearse-through-both-packages.md`: RH2, its times, its
   `interrupt_when.py` delay and how it was chosen, and its commands. They are the model for yours.
5. The rehearsal tools, run **unchanged** (`.documents/dk-and-rpk-migration/rehearsal/`):
   `ray_cluster.sh` (`start`, `stop`, `status`), `interrupt_when.py` and `stage_counts.py`. Read
   each one's `--help`. `build.sh` is the model for H0's launcher, and is **not** run: it runs
   `main.py` directly.
6. `RunDrivers/registered_run.py`'s docstring and results note 03: the usage, the heartbeat, the
   marker, the refusals, and the longest silence 03 expects.
7. ChamPBH's `.documents/rrk-adoption-verification.md` §1 (read, never edit): the same rehearsal
   on ChamPBH, and what it measured.
8. RunRegistryKit's `README.md` at `v0.2.0`: "Ending a run whose end was never recorded", and the
   `store` commands. Its open issue `[04-a-killed-process-not-yet-reaped-answers-kill-0]`: a killed
   process its parent has not reaped still answers `kill -0`, and `end` refuses it.

---

## 1. What is wanted

The proof that 03's tests cannot give: under real Ray, on SI's isolated cluster, the wrapper
records a build from its first second to its end:
- a clean build, `done`;
- a build interrupted with `SIGTERM`, `killed`;
- a build killed outright with `SIGKILL`, which stays `running` until a person ends it with `end`,
  and whose store refuses a resume until then;
- a resume after both interruptions, `done`, equal to the clean build, which is itself equal to
  RH2's reference.

And the store layer acts on a real store: `store create` after the first close, the fingerprint
recorded at finish, `store fingerprint` and `store show`.

This prompt is a one-off exception to the rule that no campaign prompt starts a `main.py` run with
a datastore (README §5). It is four builds of about 30 s each.

### 1.1 The protocol

Throughout:
- `ADDRESS=127.0.0.1:6390`, `S=var/datastores` and `L=var/rrk-adoption-04` (the launch logs and pid
  files), all under the repository root and ignored by git (R6).
- Every build is `dk-and-rpk-migration` README §4.1's dense build, given to the wrapper after `--`:

  ```
  --config quadratic-minimal.yaml --database $S/rrk-adoption-04-<store>.sqlite \
  --job-name rrk-adoption-04-<slug> --targets homogeneous \
  --n-collocation-points 5 --alpha-regularization 0.01 --ray-address $ADDRESS
  ```

  No `--profile-db` (README §4.1 used it for `reference` to exercise `ProfileAgent`; this campaign
  does not). The wrapper's own flags are `--campaign rrk-adoption --prompt 04 --register <slug>
  --purpose "<one line>"`.
- **H0 — the launcher** (P8): `.documents/rrk-adoption/rehearsal/build_registered.sh`, after
  `build.sh`: it takes the store's and the build's slugs and the address, runs the wrapper with the
  arguments above, **detached** (rule 3), writes the driver's pid to `$L/<slug>.pid` as soon as it
  starts and its output to `$L/<slug>.log`, appends `** launcher saw exit status N` when it ends,
  and refuses to overwrite a log. The launch goes through `sh` (or `bash`), so that the shell reaps
  the driver when it dies and `end` is not refused by an unreaped process (the open issue above).
  It starts and stops no cluster. Its header gives the usage and names this prompt.
- **One check after each launch** (rule 4): the manifest exists, `status.json` says `running` with
  the pid in `$L/<slug>.pid`, and `list` shows the run. Then wait on the build by a `Monitor` whose
  condition is the log's `** launcher saw exit status` line, never a `sleep` loop and never a
  `pgrep`.
- Every driver gets `--ray-address $ADDRESS`, and every `ray` CLI call `--address $ADDRESS`. **No
  `ray stop`, ever.**

**Steps:**
1. **The suites**, before `start`, serially, with no cluster up: the counts 03 handed on.
2. `ray_cluster.sh start "rrk-adoption 04 (R)"`. If the lock is held, it refuses: **stop and ask**;
   never wait on it, never break it. Record `start`'s output and `ray status --address $ADDRESS`.
   `mkdir -p $L`.
3. **H1 — `reference`**, into `$S/rrk-adoption-04-reference.sqlite`, straight through.
   - The log ends `** driver exit status 0`, then the launcher's line; every stage's "ALL WORK ITEMS
     COMPLETE"; `stage_counts.py` gives RH2's counts.
   - `list` shows it finished, `done`.
   - Its `status.json` has a `fingerprint`, and `fingerprint_sidecar` saying "not written", since
     there is no sidecar yet (README §0.2 item 6).
   - Its manifest: `script` is `main.py` with `main.py`'s SHA-256 (`shasum -a 256 main.py`);
     `results` is the store; `packages`, `host`, `git_head`, `git_dirty`, `scope` and
     `heartbeat_means` are as 03 wrote them.
   - Then `store create $S/rrk-adoption-04-reference.sqlite --purpose "…"`, `store fingerprint …
     --write`, and `store show …`. The fingerprint `store fingerprint` reads equals the run's.
4. **H2 — `resumed-a`**, into `$S/rrk-adoption-04-resumed.sqlite`, interrupted with `SIGTERM`:
   `interrupt_when.py $L/resumed-a.log $L/resumed-a.pid --banner "STAGE 2: FULL MSR INSTANTONS"
   --after <s>`. Choose `<s>` from H1's stored timestamps, as README §4.1 build 2 and RH2 chose it,
   so that some `FullInstanton` rows are stored and some are not, and say how you chose it. If the
   signal lands outside the window, retune and rerun on a fresh store, twice at most, as §4.1
   allows.
   - The log has the wrapper's `killed` line, then `** driver exit status 143`, then the launcher's
     `143`. **The exit status is the measurement P9 asks for**: `dk-and-rpk-migration`'s
     unregistered `SIGTERM`ed drivers exited 134 (Ray's failure-signal handler aborting;
     `interrupt_when.py`'s docstring), and the wrapper's `alarm(0)` is meant to make it 143. Record
     which, and any `cancelled an alarm` line.
   - The status is `killed`/143, with the fingerprint. The time from the signal (by
     `interrupt_when.py`'s line) to the `killed` record is measured.
   - Then `store create` on the closed store.
5. **H3 — `resumed-b`**, on the same store, killed with **`SIGKILL`**:
   - once its log shows a stage banner and a delay has passed while work remains, `kill -KILL
     $(cat $L/resumed-b.pid)`, by pid alone. Choose the banner and the delay from `resumed-a`'s
     state and H1's stage times, and say how; the store must be left partial again;
   - the log ends with the launcher's `137` and no `** driver exit status`;
   - `list` shows it stale, `!!`, its pid not answering. Record the line and the stderr summary;
   - `ray_cluster.sh status`: any SI process the kill left behind, by pid. A driver attached to an
     external cluster should leave none (ChamPBH's verification §1.7); if one is left, record it and
     **wait, by pid, for it to exit** before step 6. Ending it is a person's: stop and ask if it is
     still there ten minutes after the kill;
   - **the refusal**: launch `resumed-c` exactly as step 6 will. The wrapper refuses it: exit 2, one
     `!! ` line naming `resumed-b`'s run and `python -m runregistrykit end`. Nothing new appears
     under `var/runs/`;
   - **`end`**: `./venv/bin/python -m runregistrykit end <resumed-b's run id> --reason "SIGKILLed
     on purpose by rrk-adoption 04 to rehearse the hard-kill route"`. It is accepted, and `list`
     shows it finished, `lost`. The status's `ended` record is quoted in the results note.
6. **H4 — `resumed-c`**, on the same store, straight through (the open prunes unvalidated rows by
   default):
   - `done`/0, every stage's "ALL WORK ITEMS COMPLETE"; the prune's printed report removed only
     unvalidated rows;
   - `fingerprint_sidecar` "written", and the sidecar's `fingerprint` equals the status's;
   - `stage_counts.py`: the resume computed only what was missing.
7. **H5 — the stores.**
   - `PYTHONPATH=. ./venv/bin/python tools/compare_stores.py` on the reference and the resumed
     store: equal, bit for bit, but bookkeeping (README §4.2–§4.3 of `dk-and-rpk-migration`).
   - `tools/compare_stores.py` on the reference and RH2's `11-reference` (P10; `compare_stores`
     opens every file `mode=ro`): equal, bit for bit, but bookkeeping. Nothing that computes has
     changed since RH2, so this is the campaign's proof that the wrapper changes nothing `main.py`
     stores.
   - `store fingerprint` on each of the two `var/` stores: they compare as `compare_stores` says.
   - `store show` on each: the runs that name it, and their states.
8. `ray_cluster.sh stop`, as a command on its own; then `status`, which must show the lock free and
   no SI process.
9. **The suites** again, after `stop`.

### 1.2 The items

- **H0** — the launcher, as §1.1 says.
- **H1–H4** as steps 3–6 say, each with its run id, its log's last lines, its `status.json` (less
  the fingerprint's per-class detail) and its `list` line.
- **H5** as step 7 says.
- **H6 — the record.** A new `.documents/rrk-adoption/verification.md`, §1:
  - the cluster and the load;
  - the four builds, as a table: run id, slug, store, pid, state, exit code, wall time, and the
    fingerprint's time at finish;
  - the heartbeat: its age (read from `status.json`, not `list`'s `AGE`, which is the run's age) and
    stage at each build's one check, and the final status's last beat against the build's end, set
    against the longest silence 03 expected. `status.json` keeps only the latest beat, so no history
    of beats is claimed;
  - the signal's measurements (step 4) and what they say about P9;
  - the hard-kill route, line by line;
  - the stores compared, and the fingerprints;
  - `git_dirty` as recorded, and why;
  - the commands, verbatim.

  Small text outputs go under `.documents/rrk-adoption/out/04-*`: the logs, the `list` and `store
  show` outputs, the manifests and statuses. A file over about 1 MB is a finding to report before
  committing.

---

## 2. Acceptance

1. H0–H6 as §1.2 says.
2. The cluster was started and stopped by the script alone, under the lock. The results note shows
   `start`'s output, `ray status`, and `stop`'s exit status. Nothing is left running.
3. **Nothing outside `var/` and `.documents/rrk-adoption/`** is written, and no existing store is
   opened but RH2's `11-reference`, read-only by `compare_stores`. The venv is unchanged (`pip
   freeze` before and after).
4. `git diff 1c223e8 -- main.py plot_InstantonSolutions.py plot_GradientCoupledSolutions.py
   utilities.py` is empty.
5. **One commit**, with the results note `.documents/rrk-adoption/04-rehearse-registered-runs.md`.
   The commit holds: the launcher (H0); the verification document; `.documents/rrk-adoption/out/04-*`;
   the board: row 04, H0–H6, the gate "R", and a `### 5.5 After prompt 04 (<date>)`. Write "this
   commit" where the SHA goes. **`var/` is not committed**; the stores and runs stay there for the
   user (README §3).

## 3. Stop conditions: stop and ask (after `ray_cluster.sh stop`, unless the stop is what failed)

- The lock is held, or the cluster will not start.
- A build fails other than by the signal it was sent.
- A record is wrong: a state, an exit code or a fingerprint is not what §1.1 says; a manifest is
  written after its driver's first line; a `SIGTERM`ed run is not recorded `killed`; the refusal in
  step 5 is not made, or creates anything.
- `end` refuses `resumed-b` although its pid does not answer, or accepts it while it does.
- A Ray process outlives the kill by more than ten minutes.
- Either comparison of H5 finds a difference beyond bookkeeping. Record `compare_stores`'s full
  output and change nothing.
- The wrapper needs a change. That is a lettered prompt, 03b (README §4), never an edit here.

## 4. What this prompt does not do

- It changes no code or test. Its one script is H0's launcher, under `.documents/rrk-adoption/`.
- It registers no plotting run, and runs no `--inventory` through the wrapper.
- It keeps its stores and runs under `var/`. Removing them is the user's (README §3, §7).

**One commit** in the repository's form, staged by explicit path only, after showing
`git diff --cached --name-only`.
