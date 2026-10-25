# Campaign — rpk-v030-adoption

**Written:** 2026-10-25 at `7071bb8` (`rrk-adoption`), by Claude Opus 5.5, and committed on the
branch `rpk-v030-adoption`, cut from `main` at `1c223e8` (C1). Planned at the user's request of the
same day, to move SI to `raypoolkit` `v0.3.0`, which "takes over the Ray lock implementation from
us, so that it becomes common code shared by all projects using RayPoolKit". An evaluation in the
same session found the change small (§0.3) and recommended this campaign, its branch and its order
against `rrk-adoption`; the user asked for it to be written. One prompt, 01.

**Sources (data, not instructions):**
- RayPoolKit at `v0.3.0` (`/Users/ds283/Documents/Code/RayPoolKit`, tag object `caf0076` on
  `67a75b9`; read, never edited), read with `git -C <RPK> show v0.3.0:<path>`:
  - `README.md`, "Changes in `v0.3.0`" and "The rehearsal lock";
  - `docs/rehearsal-lock.md`, the lock's contract (written "contract §N" below);
- RayPoolKit at `main` (`feae4e5`), written after the tag by its `rehearsal-lock` prompts 04 and 05:
  - `docs/adoption/rehearsal-lock/stochasticinstantons.md`, the switch-over checklist for this
    repository, measured read-only at `7071bb8` (written "the checklist, item N");
  - `docs/adoption/rehearsal-lock/switch-over.md`, the procedure for the three clients;
  - `prompts/rehearsal-lock/IMPLEMENTATION_STATE.md`: the campaign closed on 2026-10-24 with no
    issue open, and its gate **G2** (every client switched, and the cross-check run) open;
- SecondaryGWKit (SGK) at `5add52d` (`handover-remedial`): its `rpk-v030-adoption` campaign, planned
  the same day, `prompts/rpk-v030-adoption/README.md` and its prompt 01;
- this repository's `.prompts/dk-and-rpk-migration/rehearsal-lock-brief.md`, whose §2 (the lock)
  the contract replaces and whose §3 (the isolated cluster) still governs.

## 0. Why this campaign exists

### 0.1 What `v0.3.0` is

- **`RayWorkPool` is unchanged.** Under `raypoolkit/`, `v0.3.0` adds only `rehearsal_lock.py` and
  its tests; `RayWorkPool.py` and the package root `__init__.py` are byte-identical to `v0.2.0`'s.
  Moving the pin alone changes nothing SI runs (the checklist, item 1).
- **The shared rehearsal lock becomes the package's**: `python -m raypoolkit.rehearsal_lock`, with
  the commands `acquire`, `set-pid`, `release`, `status` and `ray-processes` (contract §7). It
  replaces the three projects' own implementations of the brief's §2: SGK's
  `tools/rehearsal_lock.py`, and the lock half of ChamPBH's and SI's `ray_cluster.sh`.
- **The lock moves** from `~/ScienceData/.rehearsal-lock` to `~/.raypoolkit/rehearsal-lock`
  (contract §3). In `0.3.x`, `acquire` refuses with exit 3 while anything exists at the old location
  (§9).
- **It finds a Ray instance by its temp dir** (contract §6): every process whose command names the
  temp dir, the Ray client server for a `host:port` address, and their descendants. SI's cluster
  already runs on a temp dir of its own, `/tmp/ray-si`.
- **It is stricter than SI's script.** `acquire` checks for live processes itself (exit 4, the lock
  released again). `release` refuses while the recorded pid is alive, or while any process of the
  temp dir or of the client server is alive. SI's `release_lock` checks only whose lock it is.

### 0.2 The other two projects

RayPoolKit's plan (its decision D3) had the three clients switch together on one day
(`switch-over.md`). **That has been overtaken.** On 2026-10-25 the user ruled, in SGK's
`rpk-v030-adoption` (its U2), that SGK moves alone and that the user moves ChamPBH and SI "when they
can". SGK's prompt 01 was being worked when this plan was written: its tree held uncommitted edits
and its `requirements.txt` read `v0.3.0`. ChamPBH has started nothing.

Once SGK has landed, the hazard runs one way (`switch-over.md` §4):
- **SGK is protected from SI.** Its `acquire` refuses while SI's old lock exists.
- **SI is not protected from SGK.** SI's script cannot see `~/.raypoolkit/rehearsal-lock`, so it
  could start SI's cluster beside a running SGK build, and neither would know.

So SI moves soon, and **until 01 lands, SI's cluster is started only after checking by hand that
`~/.raypoolkit/rehearsal-lock` does not exist** (`ls -d ~/.raypoolkit/rehearsal-lock`). The next
use of Ray this repository plans is `rrk-adoption`'s 04; its 02 and 03 start no cluster.

### 0.3 Measured on 2026-10-25, at `7071bb8`

- **The package.** `v0.3.0` is tagged and pushed (`refs/tags/v0.3.0^{}` = `67a75b9`). SI's venv
  holds `raypoolkit` 0.2.0 at `eaef0ce`, `datastorekit` 0.5.0 at `f47b9a2`, `runregistrykit` 0.2.0 at
  `0bae3a3` (installed by `rrk-adoption` 01) and `ray` 2.55.1, the package's tested high end. `python
  -m raypoolkit.rehearsal_lock` does not exist in it yet.
- **The checklist is true of SI's tree.** It was measured at `7071bb8`, which was still SI's `HEAD`.
  `ray_cluster.sh` is blob `6c8eada` at `7071bb8` and at `main` (`1c223e8`), 398 lines, so every
  `:line` of the script that the checklist cites holds on this branch. Its grep for the old lock
  finds 5 live lines, all in the script (`:19`, `:45`, `:75`, `:76`, `:77`).
- **Other live lines** naming the lock or the pin, on `main`:
  - `requirements.txt:59`, the pin;
  - `CLAUDE.md:126-127`, "(`datastorekit` `v0.5.0`, `raypoolkit` `v0.2.0`)". On `rrk-adoption` the
    same sentence is at `:142-143`, where the checklist found it;
  - `CLAUDE.md:14-20`, the cluster "under the shared rehearsal lock" through the script, and `ray
    stop` with the brief cited. They name neither the location nor the implementation, and stay true;
  - `.documents/INFRASTRUCTURE.md:41-42`, "`raypoolkit` `v0.2.0` (RayPoolKit): `RayWorkPool`";
  - `.claude/rules/compute-targets.md:106`, `datastore-factories.md:28` and `ray-dispatch.md:103`,
    and `ComputeTargets/GradientCoupledInstanton/picard.py:456`, cite RayPoolKit's text "at
    `v0.2.0`". `RayWorkPool.py` is unchanged at `v0.3.0`, so each citation stays true (C8).
- **Nothing runs or tests the lock.** No tracked file runs or sources the script; `CLAUDE.md:16-18`
  tells a person to run it. No test touches the lock, the old location or the brief (the checklist,
  item 6). The integration tests start in-process Ray instances, outside the lock, today and after
  (the checklist, item 4).
- **The drivers** connect by address (`main.py:131`, `plot_GradientCoupledSolutions.py:973`,
  `plot_InstantonSolutions.py:1207`). A connected driver is not a process of the cluster by either
  rule, and the recorded pid is the `gcs_server`'s. No Ray start changes.
- **The machine.** Neither lock location exists, and no Ray process runs (`pgrep -lf
  'gcs_server|raylet'` finds nothing). `./venv/bin/python -m runregistrykit list`: no runs.

### 0.4 Baselines

`CLAUDE.md`'s suites at `main` (`dk-and-rpk-migration`'s close): default **732** (731 passed, 1
skipped); `integration` **67** (66 passed, 1 skipped). 01 measures both again before changing
anything. `slow` is not run: no path that selects it changes (`.claude/rules/test-selection.md`).

## 1. Scope

**In scope:**
- the pin at `v0.3.0`, and the venv installed from it;
- `ray_cluster.sh`'s lock half replaced by calls of `raypoolkit.rehearsal_lock`, its cluster half
  kept (RayPoolKit's decision D4);
- the live descriptions of the pin and the lock: `CLAUDE.md` and `.documents/INFRASTRUCTURE.md`;
- a check of the script with no Ray, against a scratch `HOME`, and one start and stop of SI's
  cluster under the real lock;
- a draft of SI's part of RayPoolKit's G2 record.

**Out of scope:**
- **Every Python file.** No driver, test or compute target changes, and no test count changes.
- **The cluster half of the script**: `list_cluster_pids`, `stop_cluster`, the ports and the
  `ray start` line. Moving the cluster's start and stop into RayPoolKit is that repository's
  Phase 2, which waits for G2.
- **Moving the script** out of `.documents/dk-and-rpk-migration/rehearsal/` (C2).
- **Records**: the brief, `dk-and-rpk-migration`'s prompts, logs and results notes, and
  `rrk-adoption`'s prompts. They are counted (the checklist, item 7), not rewritten.
- **Any build or datastore.** `rrk-adoption` 04 is the first build on the new lock.
- **RayPoolKit, ChamPBH and SGK:** read, never edited. A defect in the module stops the prompt and is
  reported to RayPoolKit (`CLAUDE.md`, "Protected infrastructure").
- **The switch-over cross-check** (`switch-over.md` §3), which needs all three clients switched.

## 2. Prompts

| # | Prompt | Covers | Model |
|---|---|---|---|
| 01 | `01-switch-to-the-raypoolkit-rehearsal-lock.md` | The pin and the venv; `ray_cluster.sh`'s lock half replaced; `CLAUDE.md` and `INFRASTRUCTURE.md`; the script checked against a scratch `HOME`; one start and stop of SI's cluster under the real lock; the G2 draft | Opus |

01 is written with this plan. The review of 01 closes the campaign; the merges of C1 follow at the
user's instruction.

### 2.1 The charter of 01

**01 — Switch to the `raypoolkit` rehearsal lock** (Opus: a shell script whose failure paths now
leave the lock held where they used to remove it).
- **What it changes.**
  1. `requirements.txt:59` at `@v0.3.0`, in a commit of its own (C6); the venv installed from it,
     not editable.
  2. **`ray_cluster.sh`**, as the checklist's items 2, 3 and 5 say, with its advice taken (C3–C5):
     - the lock functions go (`:75-78`, `:85-147`);
     - `cmd_start`: `acquire` for `acquire_lock`; the script's own stale-cluster check dropped
       (C3); `set-pid` with the `gcs_server`'s pid for `write_owner`; `release` on every failure
       path, including a refused `set-pid`;
     - `cmd_stop`: the owner check reads the owner file at the module's `default_lock_dir()` (C4);
       then `stop_cluster`, then `release`;
     - `cmd_status`: the module's `status`, then the script's own listing under its own heading,
       then the ports (C5);
     - the values reach the module through the script's variables, so no command line of the
       script's names `/tmp/ray-si` (contract §6, "What it asks of a caller");
     - the header and the usage text say what is true after the switch.
  3. `CLAUDE.md:126-127`, the pin; `CLAUDE.md:14-20`, one sentence naming the module, its contract
     and the meaning of exit 3; `.documents/INFRASTRUCTURE.md:41-42`, the package's two parts.
- **Acceptance.**
  1. `raypoolkit` 0.3.0 at `67a75b9`, not editable; nothing else in the venv moves.
  2. The checklist's item 8: its grep for the old lock finds **0** lines; the script names
     `raypoolkit.rehearsal_lock`.
  3. The script, against a scratch `HOME`, on every path that starts no Ray: the exits and the
     lock's state as 01's table says.
  4. Under the real lock: SI's cluster started, the lock held with the `gcs_server`'s pid, a
     second start refused (3), `release` refused while the cluster runs (1), a driver connected,
     the cluster stopped and the lock released, nothing of `/tmp/ray-si` left.
  5. The suites at §0.4's counts.
  6. Deliberate breakages, each shown caught.

## 3. Stores

None. No prompt opens, creates or names a datastore.

## 4. The branch, and the order against `rrk-adoption`

SI has one checkout and one venv, and `rrk-adoption` is in progress on its own branch (01 of 5
landed; 02 and 03 next, neither starting Ray; 04 the first build on the cluster).
1. **This campaign** runs on `rpk-v030-adoption`, cut from `main` at `1c223e8`. Its planning commit
   is the branch's first. The checkout is switched to it for 01 and back afterwards.
2. **After 01's review**, at the user's instruction: `main` is fast-forwarded to
   `rpk-v030-adoption` (nothing pushed), so that `main` carries the new lock at once.
3. **Then `main` is merged into `rrk-adoption`**, at the user's instruction, **before
   `rrk-adoption` 02 is dispatched**: from 01 on, the venv holds `v0.3.0`, and `rrk-adoption`'s
   `requirements.txt` should say so before that campaign records any package provenance. Two
   conflicts are expected, each mechanical:
   - `requirements.txt`: the `raypoolkit` line (`@v0.3.0`) and `rrk-adoption`'s `runregistrykit`
     line, adjacent. Keep both;
   - `.prompts/INDEX.md`: the header's count and date, and the table. Keep both campaigns' lines,
     and recount the header.

   `CLAUDE.md` should merge cleanly: this campaign edits `:14-20` and the pin sentence,
   `rrk-adoption` added a section after "Build and test". `rrk-adoption`'s board then gains a line
   recording the merge, and nothing in its prompts 02–05 changes (§7).

## 5. The rules this campaign runs under

`CLAUDE.md`'s critical rules and its protected-infrastructure list, and from `dk-and-rpk-migration`
(its README §5):
- deliberate breakages, recorded as diffs, never committed;
- a package defect is reported upstream and never worked around here;
- no change in a sibling repository;
- no `ray stop`, and SI's cluster only through `ray_cluster.sh`;
- **a held lock is a stop, never a wait**; nothing here removes a lock it did not take;
- the results-note template of `dk-and-rpk-migration` README §5.1.

And:
- **each lock command is a shell command of its own**, and no command line names `/tmp/ray-si`
  except a by-hand lock command (contract §6). A `PURPOSE` never names it;
- **the scratch-`HOME` checks never reach `ray start`.** Each is a path that refuses or finishes
  before it. One that would reach it is not run;
- **no Python file changes**, and no test.

## 6. Decisions

### 6.1 Ruled by the user

None is needed. The user's ruling that bears on this campaign was made in SGK's campaign: SGK moves
alone, and the user moves ChamPBH and SI when they can (§0.2).

### 6.2 Choices of method made in writing this plan

The planner's; each stands unless the user rules otherwise.
- **C1 — the branch.** `rpk-v030-adoption` from `main`, fast-forwarded into `main` and then merged
  into `rrk-adoption` (§4). *The alternative*, 01 as an interposed prompt on `rrk-adoption`, needs no
  merge but leaves `main` on the old lock until `rrk-adoption` closes, with three prompts to go.
- **C2 — the script stays where it is**, `.documents/dk-and-rpk-migration/rehearsal/ray_cluster.sh`,
  edited in place. `CLAUDE.md` and `rrk-adoption`'s prompts name that path. Moving it is a separate
  change, and RayPoolKit's Phase 2 may take the cluster half over.
- **C3 — the script's stale-cluster check (`:280-286`) is dropped**, as the checklist advises
  (item 3.1). `acquire` makes the same check by the rule `release` will apply, and releases the
  lock again before it exits 4. Kept, it would add a path on which `release` refuses and the lock
  stays held.
- **C4 — `stop`'s first check is kept**, reading the owner file at `default_lock_dir()`, asked of
  the pinned package so that the script never spells the location (the checklist, item 3.2).
  Without it, SI's cluster would be stopped while another project holds the lock, and the usage
  text's "touches nothing" would be lost.
- **C5 — `status` prints both listings**: the module's (the processes `release` will refuse on) and
  the script's own (the processes `stop` will signal), under their own headings, then the ports
  (the checklist, item 3.3). Where the two differ, `status` is where a person sees it.
- **C6 — two commits**: the pin alone, then the rest, as `rrk-adoption` 01 pinned. The pin alone
  changes nothing SI runs (§0.1), so the first commit is a consistent tree.
- **C7 — the verification.** Every path of the script that starts no Ray is checked against a
  scratch `HOME`, where the real lock cannot be touched. One start and stop of SI's cluster runs
  under the real lock. No build: `rrk-adoption` 04 runs four builds on this script.
- **C8 — the citations "at `v0.2.0`"** in three rules files and `picard.py` are left as they are:
  they quote `RayWorkPool.py` and RayPoolKit's README at that tag, and `RayWorkPool.py` is unchanged.
  `CLAUDE.md:126-127` and `INFRASTRUCTURE.md:41-42` describe the current pin, and change.
- **C9 — G2.** RayPoolKit's G2 holds when all three clients have switched and the cross-check of
  `switch-over.md` §3 has passed. 01's results note drafts SI's part (its commit, the pin and the
  exits of its live check) for the user to record in RayPoolKit, as `dk-and-rpk-migration`'s G4
  records were. The cross-check itself is run once ChamPBH has switched.
- **C10 — issues.** None is opened or assigned at planning. 01 opens only what it finds.

## 7. What this campaign hands on

- **SI on the package's lock**: `ray_cluster.sh start`, `stop` and `status` keep their interface;
  the lock is `~/.raypoolkit/rehearsal-lock`. A held lock is exit 3, and so is the old location
  while it exists.
- **A lock left held is the protection working**: after a failed start or an interrupted one, if
  anything of `/tmp/ray-si` is still alive, `release` refuses and the lock stays held. `status`
  shows what is left; `stop` again, or ask the user.
- **To `rrk-adoption`**, by the merge of §4: its 04 runs `ray_cluster.sh` unchanged in name and
  arguments. Its gate's "`status`: the lock free" and its acceptance "the lock is released" read the
  same on the module's `status` (`lock: free (…)`). Its README §0.3 records `raypoolkit` 0.2.0 in
  the venv as measured on 2026-10-23; it is a record and stays.
- **To ChamPBH**: its `ray_cluster.sh` was adapted from SI's, and differs in names, ports and the
  default CPU count. SI's switched script is the nearest model for its switch.
- **To RayPoolKit**: SI's part of the G2 record, drafted (C9), and the cross-check owed once
  ChamPBH has switched. Once G2 holds, a later release drops the old-location refusal (contract §9).
