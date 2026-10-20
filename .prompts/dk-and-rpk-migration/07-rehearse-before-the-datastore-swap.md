# Prompt 07 — rehearse before the DatastoreKit swap (RH1)

**Campaign:** [`README.md`](README.md) · **Board items:** **L1**–**L4** (RH1), **V2**, **Z1**;
gate **RH1**, and RayPoolKit G4's run under real Ray ·
**Board:** [`IMPLEMENTATION_STATE.md`](IMPLEMENTATION_STATE.md)
**Written:** 2026-10-20, with prompts 05 and 06, after 02's review (board §5.13). It runs README
§4.1 as amended by **U11**: the homogeneous branch only, the interrupt in `STAGE 2`, and
`run_readers.sh` as fixed at `b218760`.
**Gate:**
- 03, 04, 05 and 06 landed and reviewed (board §1); RayPoolKit's G4 recorded in board §2;
- on branch `dk-and-rpk-migration`, no tracked change in `git status`;
- **the rehearsal tooling is RH0's:** `git diff 5868231 HEAD --
  .documents/dk-and-rpk-migration/rehearsal/ tools/compare_stores.py` is empty (README §4: 07 runs
  the scripts and the tool **unchanged**);
- the venv holds `raypoolkit` 0.2.0 at `eaef0ce6…`, not editable, and no `datastorekit`
  (`utilities.installed_package_provenance()`);
- **RH0's stores are in place** under `$REHEARSAL_ROOT` (below): `02-reference.sqlite`,
  `02-scalars-2.sqlite` and `02-readers/scalars/before/02-scalars.sqlite`, each with its ten
  shards, and `02-readers/resumed/before/02-resumed.sqlite`;
- `git tag -l pre-datastorekit` and `git ls-remote --tags origin pre-datastorekit` are both empty;
- **the rehearsal lock is free** (`.documents/dk-and-rpk-migration/rehearsal/ray_cluster.sh status`)
  and no process names `/tmp/ray-si`. If the lock is held, stop and ask: another project is
  rehearsing, or a stale lock needs the user. Other projects' clusters may be up; leave them alone;
- **the machine is otherwise idle**: no other session's suite, rehearsal or build is running. If
  you cannot tell, ask the user before starting the cluster.

**Closes:** nothing. **Opens:** anything you find, **without fixing it**.
**Recommended model:** **Opus**. It runs four builds and the readers under a real Ray cluster, the
first through `raypoolkit` and the moved data, and the work is in reading what they did.

**This prompt runs `main.py` on stores.** The user's ruling **U2** (README §6.1) makes that the
agent's work for prompts 02, 07 and 11, within README §4.1 and no further.

**Read first:**

1. `CLAUDE.md`, in full.
2. [`README.md`](README.md): §2.2 (07's charter), §3, **§4.1** (the protocol, as amended for U11),
   **§4.2**, **§4.3**, §5 (rules 9, 14, 17, 18) and §6.1 (U2, U7, U9, U11).
3. **Prompt 02's results note**, `.documents/dk-and-rpk-migration/02-rehearse-the-start-tree.md`,
   in full, and **`verification.md` §1**. This prompt is 02 again at a later tree, held to 02's
   results. In particular: how `S` was chosen; the exit status of a `SIGTERM`ed driver; the prune
   reports; the readers' `version` row (02's D3); and "State handed to the next prompt".
4. [`02-rehearse-the-start-tree.md`](02-rehearse-the-start-tree.md), the prompt: §1.2–§1.4 are the
   steps this prompt repeats, with the changes of §1 below.
5. The board's §5.13, with the orchestrator's review of 02 and its "Handed on" list, which binds
   this prompt.
6. The results notes of 03–06, for what changed since RH0: `raypoolkit` in place of `RayTools/`
   (03, 04); the registry, drop groups and batch sizes in `config/datastore.py`, and the vectorized
   gets in the mapping form (05); the `InflatonTrajectory` cascade, `prune`, and the keys the old
   layer ignores (06).
7. RayPoolKit's `README.md` at the tag (`git -C /Users/ds283/Documents/Code/RayPoolKit show
   v0.2.0:README.md`), "The printed lines are part of the interface". **Read; edit nothing there.**

---

## 0. What this prompt is

RH1 rebuilds RH0's grid at 06's tree: SI's own layer, now fed from `config/datastore.py`, with
`raypoolkit` in place of `RayTools/`. It answers:
- **does the tree before the DatastoreKit swap build, resume and read the grid cleanly?** (L1–L3);
- **is what it stores RH0's, bit for bit?** RH0 is bitwise reproducible in both modes (board
  §5.13), so RH1 is held to **bitwise equality**, timings and timestamps aside (README §4.3, P4).
  No tolerance applies;
- **does the resume behave as RH0's did?** (L4).

If all three hold, 07's commit is the last on SI's own layer, rehearsed, and is tagged
`pre-datastorekit` (U7). P2's audit reads the June and July stores from that tag (README §7).

---

## 1. The protocol, with this prompt's names

Everything is as prompt 02's §1, with NN = `07`, except where this section says otherwise.

### 1.1 Names, and RH0's baseline

- `$REHEARSAL_ROOT` is `~/ScienceData/StochasticInstantons-rehearsals/dk-and-rpk-migration/`
  (P2). It exists; touch nothing in it but your own files.
- **RH1's stores**, each with ten shards: `07-reference.sqlite` and `07-resumed.sqlite` (dense),
  and `07-scalars.sqlite` (scalars-only). **There is no `07-scalars-2`:** the second scalars-only
  build is RH0's only (README §4.1, build 5). None of the three may exist before you start; if one
  does, stop and ask.
- Logs to `$REHEARSAL_ROOT/logs/07-<build>.log`; readers to `$REHEARSAL_ROOT/07-readers/`;
  outputs kept in the repository to `.documents/dk-and-rpk-migration/out/07-*`, small text only,
  as 02's §1.1 says.
- **RH0's stores are read, never written.** Open them only with `tools/compare_stores.py` and
  `sqlite3` in `mode=ro`, never through a driver or the layer. **The baselines:**
  - dense: **`02-reference.sqlite`**, which the readers never touched;
  - scalars-only: **`02-scalars-2.sqlite`** and **`02-readers/scalars/before/02-scalars.sqlite`**.
    Not `02-scalars.sqlite` itself: it carries the readers' `version` row (`2026.3.0`).
- **First, check the baseline is intact** (before the cluster): `compare_stores.py
  $R/02-reference.sqlite $R/02-readers/resumed/before/02-resumed.sqlite` and `compare_stores.py
  $R/02-readers/scalars/before/02-scalars.sqlite $R/02-scalars-2.sqlite` both give `RESULT: equal`,
  exit 0, as at 02 (`out/02-compare-*-before-readers.txt`). If either does not, stop: RH0's stores
  have moved.

### 1.2 The cluster

As 02's §1.2, with `ray_cluster.sh start "dk-and-rpk-migration 07 (RH1)"`. Record `uptime`, the
CPUs, the address (`127.0.0.1:6390`) and the actor line. `ray_cluster.sh stop` at the end and after
any stop, as a command of its own, the lock released. **Never `ray stop`.**

### 1.3 The builds

Each with `build.sh` as a background task; wait for each to end; **do not poll.**

1. **`reference`:** `build.sh 07 reference reference <address> dense --profile-db`. Record its wall
   time and each stage's. RH0's took 37 s; if this one takes more than 45 minutes, stop (P1).
2. **Choose `S`** for build 3 from `07-reference`, as 02 did (its results note, "`S`, and how it
   was chosen"): the closed store's `timestamp`s read `mode=ro` (the last `InflatonTrajectory` row,
   and the `FullInstanton`, `SlowRollInstanton` and `CompactionFunction` rows), and the profile
   database's `object_get FullInstanton` vector calls, which date the `STAGE 2` lookup banner. At
   RH0 the `FullInstanton` rows fell at banner +9.8 to +12.8 s, and `S` = 11.0 s left 6 validated
   and 2 unvalidated. **The pool is now `raypoolkit`'s**, so do not assume RH0's timings: measure
   them. Record `S` and how you chose it.
3. **`resumed-a`:** `build.sh 07 resumed resumed-a <address> dense`, with `interrupt_when.py` on
   its log and pidfile, `--banner "STAGE 2: FULL MSR INSTANTONS" --after <S> --poll 0.2`. The
   window, the retries (twice at most, `resumed-a2`, `resumed-a3`, each on a fresh `07-resumed`
   store, deleting only your own `07-resumed` files), and what to record, are 02's §1.3.3. **A
   `SIGTERM`ed driver may exit 134, 15 or 1** (02's D4): it ended by the signal if its log shows
   `SIGTERM received`.
4. **Between `resumed-a` and `resumed-b`:** as 02's §1.3.4. Record the rows `07-resumed.sqlite`
   holds, by table, validated and not, with their child rows, and confirm with the actor line
   (`--filter "state=ALIVE"`) that the killed driver's actors are gone. An actor still alive after
   a minute is a stop.
5. **`resumed-b`:** `build.sh 07 resumed resumed-b <address> dense`.
6. **`scalars`:** `build.sh 07 scalars scalars <address> scalars`.

### 1.4 After the builds: the comparisons first, then the readers

**The comparisons run before the readers**, so that every store is compared as its build left it
(the orchestrator's hand-on from 02, board §5.13). Each with its text output saved beside its JSON,
as `.documents/dk-and-rpk-migration/out/07-compare-<a>-<b>.{txt,json}`. `$R` is
`$REHEARSAL_ROOT`.

1. **Within RH1** (L2): `07-reference` against `07-resumed`.
2. **Against RH0, dense:**
   - `$R/02-reference.sqlite` against `$R/07-reference.sqlite`;
   - `$R/02-reference.sqlite` against `$R/07-resumed.sqlite`.
3. **Against RH0, scalars-only:**
   - `$R/02-scalars-2.sqlite` against `$R/07-scalars.sqlite`;
   - `$R/02-readers/scalars/before/02-scalars.sqlite` against `$R/07-scalars.sqlite`.
4. **The schema:** `--snapshot $R/07-reference.sqlite --out .documents/dk-and-rpk-migration/out/07-reference-schema.json`,
   then `--schema $R/07-reference.sqlite --against .documents/dk-and-rpk-migration/out/02-reference-schema.json`
   and `--schema $R/07-scalars.sqlite --against` the same file: both "the schemas agree". 05 and 06
   changed no schema.
5. **The stage counts:** `stage_counts.py` on all four logs (and any `resumed-a2`/`a3`), saved as
   `out/07-stage-counts.{txt,json}`.
6. **The profile database** of `reference`, read `mode=ro`: its tables and row counts, beside
   RH0's (`jobs` 1, `profile_data` 807).
7. **Then the readers:** `run_readers.sh 07 resumed <address>`, then `run_readers.sh 07 scalars
   <address>`. Each exits 1 by design when its step 4 finds the expected `version` row; read
   `status.txt`.
8. `ray_cluster.sh stop`, as its own command; the lock released.

No `slow` block runs here: 07 changes no code, and S1 is 02's (09 runs `slow` again).

---

## 2. What to verify

- **L1 — every build ends as it should.**
  - `reference`, `resumed-b` and `scalars` end with `** driver exit status 0` and every pool's
    `ALL WORK ITEMS COMPLETE` (4, 4 and 2 lines, as RH0's).
  - `resumed-a` ends by the signal (`SIGTERM received`), inside the window.
  - No traceback in any log. Read every `Traceback`, `Error` and `WARNING` line, and name each.
  - **The provenance line**, once in each log, names `raypoolkit` at `eaef0ce6…`, requested
    `v0.2.0`, not editable, and `datastorekit` not installed. By 01's format (board §5.5) and
    03's install it should read
    `>> packages: datastorekit not installed; raypoolkit 0.2.0 (https://github.com/ds283/RayPoolKit@eaef0ce60e2fc354bb32f0ad576010e6a83c1976, requested v0.2.0)`;
    check it against the line 03's results note shows, and quote what each log prints.
- **L2 — the resume is the reference.**
  - §1.4.1 gives `RESULT: equal`, exit 0;
  - the prune at `resumed-b`'s open removed only unvalidated rows: its printed reports (one per
    actor that pruned) against the unvalidated count of §1.3.4;
  - `resumed-b` computed only what `resumed-a` had not kept, by `stage_counts.py`.
- **§4.3 — equal to RH0, bit for bit.** Every comparison of §1.4.2 and §1.4.3 gives
  **`RESULT: equal`, exit 0**: every row of all 30 tables matched, and only bookkeeping (timestamps,
  the JSON timing keys) differs. Say so table by table, with the row counts beside RH0's (02's
  results note, "Rows per store"). **Anything else is a miss** (§4 below).
- **L3 — every reader.**
  - `status.txt` on both stores: steps 0, 1 and 2 exit 0; step 4 exit 1. Step 3 is printed as not
    run (U11).
  - Step 4's `compare_stores` of `before/` against the store: **exactly one row more in `version`,
    labelled `2026.3.0`**, and otherwise only bookkeeping. The plot log reads
    `n_collocation_points: 1 value = [ 5 ]`.
  - **`scalar_data.csv`**: the SHA-256 of the file `plot_InstantonSolutions.py` wrote, on `resumed`
    and on `scalars` (with `--no-store-values`), each equal to RH0's
    **`b0564eecc22f9106dcccb57fd1a419749543c4b9d15dc0ffe7a8e0780e9058a2`**, byte for byte. If
    either differs, `diff` it against `.documents/dk-and-rpk-migration/out/02-readers-*-scalar_data.csv`
    and record every line that differs; it is a miss.
  - What `--inventory` printed, against RH0's (`out/02-readers-*-inventory.log`): the same values
    and counts, but for paths and times.
- **L4 — RH0's resume pattern** (02's results note, "L4's pattern"):
  - the open prunes only unvalidated rows;
  - the resume computes only what was not kept;
  - its counts add up to `reference`'s (10 / 10 / 10 / 1).

  The figures themselves depend on where the signal fell and need not be RH0's. **The builds that
  do not depend on it must equal RH0's line for line:** `stage_counts.py` for `reference` and
  `scalars` against `out/02-stage-counts.json`'s. The queue banners, progress and summary lines are
  `raypoolkit`'s now ("printed lines are part of the interface"): that `stage_counts.py` parses
  them unchanged is part of L4. Since the interrupt falls after the trajectory stage, no trajectory
  is pruned, and 06's cascade makes no difference here (06's tests and 09's acceptance 4 cover it).
  **If L1–L3 and §4.3 hold and L4 differs,** that is a finding to explain (README §4.1), and it
  holds back the tag (§3.6).

---

## 3. Acceptance

1. RH0's baseline is intact (§1.1).
2. L1–L3 hold, each shown, with the provenance line quoted.
3. **§4.3:** RH1's three stores equal RH0's of the same mode, bit for bit (§1.4.2–§1.4.3), and the
   schema is RH0's.
4. **L4** holds.
5. **No deliberate breakage** (README §5 rule 8): 07 changes no code. Each check is one a bad
   build fails, and RH0's control (D5) showed the comparison can fail.
6. **Z1 — U7, the tag.** Once 1–4 hold, and only then: commit the records (7 below), then make an
   **annotated** tag on that commit:
   ```bash
   git tag -a pre-datastorekit -m "Last commit on StochasticInstanton's own datastore layer, rehearsed (RH1, dk-and-rpk-migration prompt 07)"
   ```
   Show `git cat-file -t pre-datastorekit` (`tag`) and `git rev-parse 'pre-datastorekit^{commit}'`
   (07's commit). **Do not push it**, nor the branch: the user pushes the tag (README §6.3). If L4
   differs (§2) but everything else holds, commit the records and **do not tag**: stop and ask.
7. **The suites**, before `ray_cluster.sh start`: the default run and `RAY_ADDRESS=local
   ./venv/bin/python -m pytest -m integration` give 06's counts. Record them.
8. **The records**, in the one commit:
   - **`verification.md` §2 RH1**, in §1's form: the cluster and the load; the four builds, with
     their times and exit statuses, and every `resumed-a` attempt; L1–L4; the comparisons against
     RH0, table by table; the commands, verbatim. It says plainly whether RH1 equals RH0;
   - `.documents/dk-and-rpk-migration/out/07-*`;
   - this board: the §1 row for 07; items L1–L4 (RH1), V2 and Z1; gate **RH1** in §2; the
     RayPoolKit G4 row's note that RH1 ran under real Ray through the package; and
     `### 5.N After prompt 07 (<date>)`, N the next free number in §5, naming the tag and the
     commit it points at;
   - a §3 entry for anything opened, with `.documents/OPEN-ISSUES.md` in the same commit.

The tag names the commit that carries these records, so the board and results note name the tag,
not the commit hash (the orchestrator fills the hash in at review, as for every prompt).

---

## 4. Stop conditions — stop and ask

- The lock is held, an SI cluster is up, the machine is not idle, a store of §1.1 exists, RH0's
  baseline has moved, the rehearsal tooling differs from RH0's, or `pre-datastorekit` exists.
- `reference` takes more than 45 minutes.
- A build fails, raises, or does not end as §2 says.
- `resumed-a` cannot be made to fall in its window in three attempts.
- An actor of the killed build is still alive after a minute.
- **A comparison misses** (§1.4.1–§1.4.4), or a `scalar_data.csv` differs. Then:
  - record `compare_stores`' full output (and the CSV `diff`), and name the first table in build
    order whose rows differ (trajectory, `FullInstanton`, `SlowRollInstanton`,
    `CompactionFunction`): a later table built from an earlier one inherits its difference;
  - run the readers anyway only if the stores are otherwise sound, and say so;
  - **change no code, commit nothing and make no tag.** The cause is in 03–06, all on SI's layer
    (README §4.1). Leave the results note and the verification section uncommitted in the working
    tree, stop the cluster, and report.
- A reader fails, or changes a store beyond the one `version` row and bookkeeping.
- `stage_counts.py` cannot parse a `raypoolkit` log: a changed printed line is a finding about the
  package (README §5 rule 11), not something to patch here.
- Anything would need a change to code, to a rehearsal script or to the tool.

---

## 5. What this prompt does not do

- **Files it changes:** `.documents/dk-and-rpk-migration/verification.md` (§2 added; §1 not
  touched, README §5 rule 6), `.documents/dk-and-rpk-migration/out/07-*`, the results note and this
  board. **No code.** And the tag.
- It opens no store but its own three, the readers' copies, and RH0's baselines read-only. It does
  not open `test-gradient*.sqlite`, anything under `out-*/`, the June or July stores, or either of
  RH0's earlier attempts' directories.
- It installs nothing, pushes nothing, never runs `ray stop`, and leaves no SI cluster running and
  the lock free.
- It deletes no store but its own `07-resumed` files on a `resumed-a` retry (§1.3.3), and no RH0
  store ever (README §3).

---

## 6. The results note

`.documents/dk-and-rpk-migration/07-rehearse-before-the-datastore-swap.md`, using README §5.1. It
holds:
- RH0's baseline check (§1.1);
- the cluster's address and the load;
- each command verbatim, and each build's start, end and exit status;
- `S` and why, with every attempt;
- the rows `resumed-a` left, by table, validated and not, and the actor check;
- L1–L4, each against RH0's, and every comparison of §1.4 in full;
- the provenance line as each log printed it;
- the two `scalar_data.csv` hashes;
- the two suites at dispatch;
- the tag: its name, type, and the commit it points at, and that it is not pushed;
- "State handed to the next prompt": for 08–11, RH1's stores as RH2's baseline (11 compares
  with RH1's, and so RH0's), and anything 09 should know.

**One commit**, in the repository's form, staged by explicit path only, after showing
`git diff --cached --name-only`; then the tag (§3.6).
