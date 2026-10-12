# Prompt 02 — rehearse the start tree (RH0)

**Campaign:** [`README.md`](README.md) · **Board items:** **L1**–**L4** (RH0), **V1**, **S1** ·
**Board:** [`IMPLEMENTATION_STATE.md`](IMPLEMENTATION_STATE.md)
**Written:** 2026-10-12, with prompts 01, 03 and 04, after the user's rulings (README §6.1).
**Gate:**
- 01 landed and reviewed (board §1), and its scripts and tool are as its results note describes;
- on branch `dk-and-rpk-migration`, no tracked change in `git status`;
- the venv holds neither `datastorekit` nor `raypoolkit`;
- **no Ray cluster is up** (`./venv/bin/ray status` finds none). If one is, stop and ask: it may be
  the user's, or ChamPBH's campaign's;
- **the machine is otherwise idle.** No other session's test suite, rehearsal or build is running.
  ChamPBH's R0 ran at a load of 100 or more on 10 CPUs, because another session's suite shared the
  machine (ChamPBH board §5.3). If you cannot tell, ask the user before starting the cluster.

**Closes:** nothing. **Opens:** anything you find, **without fixing it**.
**Recommended model:** **Opus**. It runs five builds and the readers under a real Ray cluster, and
the work is in reading what they did.

**This prompt runs `main.py` on stores.** The user's ruling **U2** (README §6.1) makes that the
agent's work for prompts 02, 07 and 11, within README §4.1 and no further.

**Read first:**

1. `CLAUDE.md`, in full, and `.claude/rules/test-selection.md` (the `slow` block, §3 below).
2. [`README.md`](README.md): §0.2 (the gradient solves; `[gci-main-no-store-values-crash]`), §2.2
   (02's charter), §3, **§4.1** (the protocol), **§4.2**, **§4.3**, §5 and §6.
3. Prompt 01's results note
   (`.documents/dk-and-rpk-migration/01-rehearsal-tooling-and-run-provenance.md`): the provenance
   line's format, the bookkeeping list, and each script's usage.
4. ChamPBH's R0, as done (read only):
   - `/Users/ds283/Documents/Code/ChamPBH/prompts/dk-and-rpk-migration/logs/02-rehearse-the-start-tree.md`;
   - its board's §5.3 and the review below it.

   What it met is listed in §1.2 and §1.3 below.
5. `quadratic-minimal.yaml`, and `config/argument_parser.py`'s defaults for the instanton grid
   (`N_init` 20, `N_final` 5, ten `δN★` on `[0.1, 3.0]`).
6. `main.py`:
   - its branch order: the homogeneous branch, then the gradient branch (`:1114`, `:1127`);
   - `_run_gradient_branch`, and the `STAGE G` queue it builds (`:665`);
   - and the actors' prune at open, `Datastore/SQL/Datastore.py:434-460` (`_validate_on_startup`),
     which every build runs, since `--prune-unvalidated` is always on
     (`config/argument_parser.py`, `store_true` with `default=True`).
7. `.documents/gradient-coupled-instanton/24-phase-a-deep-dive.md:35-45`: at `m = 10⁻⁵ M_P`,
   `n = 5`, one gradient solve took 315 s and stopped at its cap of 50 outer iterations.

---

## 0. What this prompt is

RH0 is the campaign's baseline, on the code as it stands: SI's own layer and `RayTools/`. It
answers three questions before anything changes:
- **does the start tree build, resume and read the grid cleanly?** (L1–L3);
- **do two builds of one grid agree bit for bit?** (README §4.3). That answer sets the criterion
  for RH1 (07) and RH2 (11). It is measured here, not assumed;
- **what does the `slow` test block do at the start tree?** (S1), the baseline 09 is held to.

---

## 1. The protocol, with this prompt's names

### 1.1 Names

- NN = `02`. The rehearsal root is `~/ScienceData/StochasticInstantons-rehearsals/dk-and-rpk-migration/`
  (`$REHEARSAL_ROOT`, P2). Create it with `mkdir -p`. `~/ScienceData/` exists (ChamPBH's
  rehearsals are under it); touch nothing else there.
- **Stores**, each with the 10 shards `quadratic-minimal.yaml` asks for:
  - `02-reference.sqlite` and `02-resumed.sqlite`, the dense mode;
  - `02-scalars.sqlite` and **`02-scalars-2.sqlite`**, the scalars-only mode.

  The second scalars-only store is RH0's only. It measures that mode's reproducibility, which
  RH1 and RH2 are then held to (README §4.3). None of the four may exist before you start; if one
  does, stop and ask.
- **Logs** go to `$REHEARSAL_ROOT/logs/02-<build>.log`, and **readers** to
  `$REHEARSAL_ROOT/02-readers/`.
- **Outputs kept in the repository** go to `.documents/dk-and-rpk-migration/out/02-*`: small text
  only, meaning comparison results, stage counts, schema snapshots, abridged reader output, and
  the `scalar_data.csv` files with their SHA-256. No store, log, profile database or figure is
  committed.

### 1.2 The cluster

1. Record `uptime` and the number of CPUs.
2. Run `./venv/bin/ray start --head --num-cpus 4 --disable-usage-stats` from the repository root.
   Four CPUs make the ten gradient solves run in three waves (README §4.1).
   - Record the address. If `ray start` prints none, it is in `/tmp/ray/ray_current_cluster`
     (`127.0.0.1:6379` by default; ChamPBH board §5.3).
   - Pass it to every driver as `--ray-address`.
3. At the end, and after any stop, run `./venv/bin/ray stop` **as a command of its own**. ChamPBH
   found that it also kills a shell whose command line names Ray's processes. You stop only the
   cluster you started.

### 1.3 The builds

Run each with prompt 01's `build.sh` as a background task, so that you are notified when it ends.
Wait for each to end before starting the next. **Do not poll.**

1. **`reference`:** `build.sh 02 reference reference <address> dense --profile-db`.
   - Record its wall time, and each stage's from the log.
   - **If it takes more than 45 minutes, stop** after it ends: the user rules on a smaller grid
     (README P1).
2. **Choose `S`** for build 3, from `reference`. The aim is that the `SIGTERM` falls after the
   first wave of four gradient solves is stored, and before the second wave is.
   - Use the `STAGE G` banner's position in the log.
   - Also read the closed `02-reference.sqlite` read-only through `sqlite3`: the `timestamp`
     column of `GradientCoupledInstanton` against that of the last `CompactionFunction` row,
     which is stored just before `STAGE G` starts.
   - Record `S` and how you chose it.
3. **`resumed-a`:** `build.sh 02 resumed resumed-a <address> dense`. Start beside it
   `interrupt_when.py $REHEARSAL_ROOT/logs/02-resumed-a.log $REHEARSAL_ROOT/logs/02-resumed-a.pid
   --banner "STAGE G: GRADIENT-COUPLED (ONION MODEL) INSTANTONS" --after <S>`.
   - A `SIGTERM`ed driver exits **134** (Ray's failure-signal handler aborts; ChamPBH board §5.3).
   - **If the signal lands outside the window** (no gradient row stored, or all ten), you may
     delete `02-resumed.sqlite` and its shards, retune `S`, and run `resumed-a` again, twice at
     most. These are the only store files this prompt deletes, and only its own. Record every
     attempt.
4. **Between `resumed-a` and `resumed-b`:**
   - Read the closed `02-resumed.sqlite` read-only, and record how many `GradientCoupledInstanton`
     rows it holds, validated and not.
   - Confirm that the killed driver's actors are gone (`./venv/bin/ray list actors --filter
     "state=ALIVE"`), and record what you saw. If an actor of the killed job is still alive after
     a minute, stop and ask.
5. **`resumed-b`:** `build.sh 02 resumed resumed-b <address> dense`. Its open prunes what
   `resumed-a` left unvalidated.
6. **`scalars`:** `build.sh 02 scalars scalars <address> scalars`.
7. **`scalars-2`:** `build.sh 02 scalars-2 scalars-2 <address> scalars`, into
   `02-scalars-2.sqlite`.

### 1.4 After the builds

1. **The readers:** `run_readers.sh 02 resumed <address>`, then `run_readers.sh 02 scalars
   <address>`.
2. **The comparisons**, each with its text output saved beside its JSON:
   - `tools/compare_stores.py $REHEARSAL_ROOT/02-reference.sqlite $REHEARSAL_ROOT/02-resumed.sqlite
     --json .documents/dk-and-rpk-migration/out/02-compare-reference-resumed.json`;
   - `tools/compare_stores.py $REHEARSAL_ROOT/02-scalars.sqlite $REHEARSAL_ROOT/02-scalars-2.sqlite
     --json .documents/dk-and-rpk-migration/out/02-compare-scalars-scalars-2.json`.
3. **The schema snapshots** of `02-reference.sqlite` and `02-scalars.sqlite`, saved as
   `.documents/dk-and-rpk-migration/out/02-reference-schema.json` and `02-scalars-schema.json`.
   05, 06 and 09 compare with the first.
4. **The stage counts:** `stage_counts.py` on all five logs, saved.
5. **The profile database** of `reference`: read it read-only, and record its tables and their
   row counts. It must exist and hold rows.
6. `ray stop`, as its own command.

### 1.5 The `slow` block (S1)

After `ray stop`, with the machine idle, run `./venv/bin/python -m pytest -m "slow and not
integration"` once, in the foreground (69 tests at planning). Record:
- the count and the duration;
- each failure or error by test id, and each skip.

A failure here is the start tree's, not this campaign's: record it, and open it as a §3 issue.
09's criterion becomes "the same results as 02's", not "all pass". Do not stop for it.

---

## 2. What to verify

- **L1 — every build ends as it should.**
  - `reference`, `resumed-b`, `scalars` and `scalars-2` end with `** driver exit status 0`, and
    every stage's `ALL WORK ITEMS COMPLETE`.
  - `resumed-a` ends by the signal, inside `STAGE G`.
  - No traceback in any log.
  - Each log carries the provenance line once, both packages not installed.
- **L2 — the resume.** From the logs and `stage_counts.py`:
  - what each open pruned, by `_validate_on_startup`'s printed report, and that it was only
    unvalidated rows. `resumed-a`'s kill may leave a gradient row stored and not validated;
  - that `resumed-b` computed only what `resumed-a` had not kept: its compute counts per stage
    against `reference`'s;
  - and the comparison of `reference` with `resumed` (§1.4.2), which is also §4.3's measurement.
- **L3 — every reader** exits 0 on both stores. For each store, `run_readers.sh`'s last step
  (`compare_stores` of `before/` against the store) must report:
  - **exactly one row more in `version`, labelled `2026.3.0`**, which the plot scripts' read-write
    pools write (README §4.1, P9, P10);
  - and otherwise only bookkeeping.

  Anything else is a stop. Also record:
  - what `--inventory` printed;
  - the SHA-256 of each `scalar_data.csv`: the one `plot_InstantonSolutions.py --no-store-values`
    writes on `scalars`, and the one `plot_GradientCoupledSolutions.py` writes on `resumed`;
  - the `diagnostics_data.csv` columns that 01 lists as timings.

  07 and 11 compare them with these.
- **L4 — the baseline.** Record each stage's counts in all five builds, and what the resume pruned
  and recomputed. The figures depend on where the signal fell, so L4 at 07 and 11 compares the
  resume's **pattern**: it prunes only unvalidated rows; it computes only what was not kept; and
  its counts add up to `reference`'s.

**§4.3, the reproducibility.** `reference` and `resumed` compute every point independently, and so
do `scalars` and `scalars-2`.
- **If both comparisons report nothing but bookkeeping,** RH0 is **bitwise reproducible**, and RH1
  and RH2 are held to bitwise equality with `02-reference.sqlite` and `02-scalars.sqlite` (P4). Say
  so plainly in the results note and the verification document.
- **If either reports differences,** record every one, with the near-miss pairs, and look for the
  cause without changing anything.
  - A first candidate is the gradient solve. It seeds from a `FullInstanton` read back from the
    store (README §0.2); compare the seeds as stored.
  - **Then stop.** The user rules on RH1's criterion before 05–07 are written (README §2.1, §4.3).
    No tolerance is chosen by an agent.

---

## 3. Acceptance

1. L1–L3 hold, each shown.
2. §4.3 is measured and recorded for both modes, either way.
3. L4's baseline is recorded.
4. The two schema snapshots are saved.
5. **S1:** the `slow` block's result at the start tree is recorded.
6. **No deliberate breakage** (README §5 rule 8): 02 changes no code. Each of its checks is one a
   bad build would fail.
7. **The suites**, before `ray start`: the default and `integration` runs give 01's counts. 02
   changes no code; record them, as `CLAUDE.md` asks.
8. **The records**, in the same commit:
   - `.documents/dk-and-rpk-migration/verification.md`, created. It has an introduction (what the
     document is, pointing at README §4), and **§1 RH0**:
     - the cluster and the load;
     - the five builds, with their times and exit statuses, and every `resumed-a` attempt;
     - L1–L4, and §4.3's result for both modes;
     - S1;
     - the commands, verbatim.
   - `.documents/dk-and-rpk-migration/out/02-*`;
   - this board: the §1 row for 02; items L1–L4 (RH0), V1 and S1; gate RH0 in §2; and
     `### 5.6 After prompt 02 (<date>)`;
   - a §3 entry for anything opened, with `.documents/OPEN-ISSUES.md` in the same commit.

---

## 4. Stop conditions — stop and ask

- A Ray cluster is already up, the machine is not idle, or a store of §1.1 already exists.
- `reference` takes more than 45 minutes (P1).
- A build fails, raises, or does not end as §2 says. The start tree is SI's: the failure is not
  this campaign's to fix, and nothing after 02 is dispatched until the user has ruled.
- `resumed-a` cannot be made to fall in its window in three attempts.
- An actor of the killed build is still alive after a minute.
- A reader fails, or changes a store beyond the one `version` row and bookkeeping.
- §4.3 finds a difference in either mode (the user rules on the criterion).
- Anything would need a change to code, to a script of 01's, or to the tool. A script that does not
  do what its usage says is a finding: record it, and stop rather than patch it, since 07 and 11
  must run the same scripts.

---

## 5. What this prompt does not do

- **Files it changes:** `.documents/dk-and-rpk-migration/verification.md`,
  `.documents/dk-and-rpk-migration/out/02-*`, the results note and this board. No code.
- It opens no store but its own four (and the readers' copies). It does not open
  `test-gradient*.sqlite`, anything under `out-*/`, or any June or July store.
- It installs nothing, and leaves no Ray cluster running.

---

## 6. The results note

`.documents/dk-and-rpk-migration/02-rehearse-the-start-tree.md`, using README §5.1. It holds:
- the cluster's address and the load;
- each command verbatim, and each build's start, end and exit status;
- `S` and why, with every attempt;
- the gradient rows `resumed-a` left, and the actor check;
- L1–L4, and §4.3's result in full for both modes;
- S1;
- the two suites at dispatch.

**One commit**, in the repository's form, staged by explicit path only, after showing
`git diff --cached --name-only`.
