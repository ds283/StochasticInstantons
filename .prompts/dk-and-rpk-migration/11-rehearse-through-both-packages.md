# Prompt 11 — rehearse through both packages (RH2)

**Campaign:** [`README.md`](README.md) · **Board items:** **L1**–**L4** (RH2), **V3**, **H1**; gate
**RH2**, and **DatastoreKit G4** ·
**Board:** [`IMPLEMENTATION_STATE.md`](IMPLEMENTATION_STATE.md)
**Written:** 2026-10-21, with prompts 08–10, after 07's review (board §5.19). It runs README §4.1
as amended by U11, held to RH1 as 07 was held to RH0.
*Amended 2026-10-22, when the user ruled **U12** (README §6.1; board §5.25): 10a pins `datastorekit`
`v0.5.0` and 10b counts the gradient instanton's value table, both before this prompt. RH2 runs at
10b's tree, on `v0.5.0`; the gate, the provenance line, G4's record and the counts below follow.
Nothing else changes: `v0.5.0` differs from `v0.4.0` only in the read-only inventory modules
(README §0.6), and RH2's stores hold no gradient row (U11).*
**Gate:**
- 08, 09, 10, 10a and 10b landed and reviewed (board §1);
- on branch `dk-and-rpk-migration`, no tracked change in `git status`;
- **the rehearsal tooling is RH0's:** `git diff 5868231 HEAD -- .documents/dk-and-rpk-migration/rehearsal/
  tools/compare_stores.py` is empty (README §4: 11 runs the scripts and the tool **unchanged**);
- the venv holds `datastorekit` 0.5.0 at `f47b9a255e9a…` and `raypoolkit` 0.2.0 at `eaef0ce6…`,
  neither editable (`utilities.installed_package_provenance()`);
- **RH1's stores are in place** under `$REHEARSAL_ROOT` (below): `07-reference.sqlite`,
  `07-readers/resumed/before/07-resumed.sqlite` and `07-readers/scalars/before/07-scalars.sqlite`,
  each with its ten shards, and RH0's `02-reference.sqlite` and `02-scalars-2.sqlite`;
- **the rehearsal lock is free** and no process names `/tmp/ray-si`. If the lock is held, stop and
  ask. Other projects' clusters may be up; leave them alone;
- **the machine is otherwise idle**: no other session's suite, rehearsal or build is running.
  **Ask the user, before you start, to have other sessions hold their suites until RH2 is done**
  (07 was stopped twice by ChamPBH's suites; board §5.19). If you cannot tell, ask before starting
  the cluster.

**Closes:** nothing. **Opens:** anything you find, **without fixing it**.
**Recommended model:** **Opus**. The first builds, prunes and reads through the package under a
real cluster, and the work is in reading what they did.

**This prompt runs `main.py` on stores.** The user's ruling U2 (README §6.1) makes that the
agent's work for 02, 07 and 11, within README §4.1 and no further.

**Read first:**

1. `CLAUDE.md`, in full.
2. [`README.md`](README.md): §2.2 (11's charter), §3, **§4.1–§4.3**, §5 (rules 9, 11, 14, 17, 18)
   and §6.1 (U2, U9, U11), §6.2 (P14).
3. **Prompt 07 and its results note**, `.documents/dk-and-rpk-migration/07-rehearse-before-the-datastore-swap.md`,
   in full, and **`verification.md` §2**. This prompt is 07 again through both packages, held to
   RH1's results. In particular: how `S` was chosen and why `resumed-a` needed a second attempt;
   the exit status of a `SIGTERM`ed driver; the prune report; the comparisons run **before** the
   readers; L4 compared less the provenance line; "State handed to the next prompt".
4. Prompt 02's results note, for RH0's protocol, and [`07-rehearse-before-the-datastore-swap.md`](07-rehearse-before-the-datastore-swap.md),
   the prompt: §1–§2 are the steps this prompt repeats, with the changes of §1 below.
5. The board's §5.19 (07's review and its "Handed on"), and the "State handed to the next prompt"
   of 08, 09, 10, 10a and 10b.
6. DatastoreKit's SI checklist item 9 (G4) and its `v0.4.0` and `v0.5.0` addenda (G4 reads "SI has adopted
   `v0.3.0` or later"), and `datastorekit/tools/shard_key_audit.py` and `sharded_store.py`'s
   docstrings at the tag. **Read; edit nothing there.**
7. ChamPBH's 10, as done (read only): its board §5.15 and the review below it. Its `resumed-a`
   exited 15 with the `with ShardedPool` block closing the pool: under the package, a `SIGTERM`ed
   driver may close its pool on the way out.

---

## 0. What this prompt is

RH2 rebuilds RH0's grid at 10b's tree, through `datastorekit` and `raypoolkit`. It answers:
- **does the tree after the swap build, resume and read the grid cleanly?** (L1–L3);
- **is what it stores RH1's, and so RH0's, bit for bit?** RH1 equals RH0 bit for bit in both modes
  (board §5.19), so RH2 is held to **bitwise equality** with RH1, timings and timestamps aside
  (README §4.3). No tolerance applies;
- **does the resume behave as RH1's did, now that the prune at open is the package's?** (L4).

If all three hold, **DatastoreKit's G4 holds** for SI (checklist item 9: the layer deleted and the
package imported at the pinned tag; both suites pass; a small grid rebuilt through the package,
here compared with RH1). The board records it (P14); recording it on DatastoreKit's own board is
12's draft and the user's commit.

**Every store is now in the package's format.** `tools/compare_stores.py` reads both formats
directly, `mode=ro`, never through either layer (README §4.2), so RH2's stores compare with RH1's
and RH0's. `main.py --inventory` reads only package stores: on RH0's and RH1's it exits 1 (10's
state handed on). The baselines are read only by `compare_stores.py` and `sqlite3` `mode=ro`.

---

## 1. The protocol, with this prompt's names

Everything is as prompt 07's §1, with NN = `11`, except where this section says otherwise.

### 1.1 Names, and RH1's baseline

- `$REHEARSAL_ROOT` is `~/ScienceData/StochasticInstantons-rehearsals/dk-and-rpk-migration/`.
  Touch nothing in it but your own files.
- **RH2's stores**, each with ten shards: `11-reference.sqlite` and `11-resumed.sqlite` (dense),
  and `11-scalars.sqlite` (scalars-only). None may exist before you start; if one does, stop and
  ask.
- Logs to `$REHEARSAL_ROOT/logs/11-<build>.log`; readers to `$REHEARSAL_ROOT/11-readers/`; outputs
  kept in the repository to `.documents/dk-and-rpk-migration/out/11-*`, small text only, as 07's.
- **The baselines**, read never written:
  - dense: **`07-reference.sqlite`** (no readers' row), and through it RH0's `02-reference.sqlite`;
  - scalars-only: **`07-readers/scalars/before/07-scalars.sqlite`** and RH0's
    **`02-scalars-2.sqlite`**. Not `07-scalars.sqlite`: it carries the readers' `version` row.
- **First, check the baseline is intact** (before the cluster): `compare_stores.py
  $R/07-reference.sqlite $R/07-readers/resumed/before/07-resumed.sqlite` and `compare_stores.py
  $R/07-readers/scalars/before/07-scalars.sqlite $R/02-scalars-2.sqlite` both give `RESULT: equal`,
  exit 0, as at 07. If either does not, stop.

### 1.2 The cluster

As 07's, with `ray_cluster.sh start "dk-and-rpk-migration 11 (RH2)"`. Record `uptime`, the CPUs,
the address (`127.0.0.1:6390`) and the actor line. `ray_cluster.sh stop` at the end and after any
stop, as a command of its own, the lock released. **Never `ray stop`.**

### 1.3 The builds

Each with `build.sh` as a background task; wait for each to end by notification; **do not poll.**

1. **`reference`:** `build.sh 11 reference reference <address> dense --profile-db`. Record its
   wall time and each stage's. RH1's took 36 s; more than 45 minutes is a stop (P1).
2. **Choose `S`** for build 3 from `11-reference`, as 07 did: the stored `timestamp`s read
   `mode=ro`, and the profile database's `object_get FullInstanton` vector calls, which date the
   `STAGE 2` lookup banner. At RH1 the `FullInstanton` rows fell at banner +9.49 to +12.07 s, and
   `S` = 10.5 s fired before the window at a load near 100, the driver still minting `efold_value`
   grids; `S` = 12.0 s left 8 validated and 1 unvalidated. **The pool and the actors are now the
   package's**: measure, and on a loaded machine aim later in the window.
3. **`resumed-a`:** `build.sh 11 resumed resumed-a <address> dense`, with `interrupt_when.py`
   `--banner "STAGE 2: FULL MSR INSTANTONS" --after <S> --poll 0.2`. The window, the retries (twice
   at most, `resumed-a2`, `resumed-a3`, each on a fresh `11-resumed` store, deleting only your own
   `11-resumed` files), and what to record, are 07's. **A `SIGTERM`ed driver may exit 134, 15 or
   1**; it ended by the signal if its log shows `SIGTERM received`.
4. **Between `resumed-a` and `resumed-b`:** record the rows `11-resumed.sqlite` holds, by table,
   validated and not, with their child rows, and confirm with the actor line (`--filter
   "state=ALIVE"`) that the killed driver's actors are gone. An actor alive after a minute is a
   stop.
5. **`resumed-b`:** `build.sh 11 resumed resumed-b <address> dense`.
6. **`scalars`:** `build.sh 11 scalars scalars <address> scalars`.

### 1.4 After the builds: the comparisons first, then the hygiene, then the readers

Each comparison with `--json`, its text saved beside it, as
`.documents/dk-and-rpk-migration/out/11-compare-<a>-<b>.{txt,json}`. `$R` is `$REHEARSAL_ROOT`.

1. **Within RH2** (L2): `11-reference` against `11-resumed` (`11-compare-reference-resumed`).
2. **Against RH1, dense:** `07-reference` against `11-reference` and against `11-resumed`
   (`11-compare-07reference-11reference`, `11-compare-07reference-11resumed`).
3. **Against RH1 and RH0, scalars-only:** `07-readers/scalars/before/07-scalars` against
   `11-scalars`, and `02-scalars-2` against `11-scalars` (`11-compare-07scalarsbefore-11scalars`,
   `11-compare-02scalars2-11scalars`).
4. **Against RH0, dense, once:** `02-reference` against `11-reference`
   (`11-compare-02reference-11reference`): the chain made explicit.
5. **The schema:** `--snapshot $R/11-reference.sqlite --out .documents/dk-and-rpk-migration/out/11-reference-schema.json`,
   then `--schema` of `11-reference` and of `11-scalars` against `out/07-reference-schema.json`:
   "the schemas agree", or each difference listed against 09's `out/09-temp-schema.json`, which
   recorded the package's column order.
6. **The stage counts:** `stage_counts.py` on all logs, saved as `out/11-stage-counts.{txt,json}`.
7. **The profile database** of `reference`, `mode=ro`: its tables and per-method counts beside
   RH1's (`jobs` 1, `profile_data` 803; board §5.19). The package's `ProfileAgent` records its own
   methods; a difference is described, not a stop.
8. **Store hygiene by the package** (H1; charter acceptance 5), with no cluster needed:
   - `./venv/bin/python -m datastorekit.tools.shard_key_audit <store>` on each of the three RH2
     stores: `VERDICT: OK`, exit 0;
   - `./venv/bin/python -m datastorekit.tools.sharded_store copy $R/11-reference.sqlite
     $R/11-reference-copy.sqlite`; the copy read with `read_inventory` (read-only, no Ray: no named
     problem, every class's count equal to `11-reference`'s) and compared with `11-reference` by
     `compare_stores.py`: `RESULT: equal`, exit 0 (`11-compare-reference-copy`);
   - the copy then deleted with `datastorekit.SQL.ShardedPool.ShardedPool.delete_store(<copy
     primary>)`, which returns the paths it deleted; show them, and that no `11-reference-copy*`
     file remains. This is the one store a prompt deletes (README §3).
9. **Then the readers:** `run_readers.sh 11 resumed <address>`, then `run_readers.sh 11 scalars
   <address>`. Each exits 1 by design when its step 4 finds the expected `version` row; read
   `status.txt`. Step 1 is now 10's `main.py --inventory`, read-only and before Ray.
10. `ray_cluster.sh stop`, as its own command; the lock released.

No `slow` block runs: 11 changes no code.

---

## 2. What to verify

- **L1 — every build ends as it should.**
  - `reference`, `resumed-b` and `scalars` end with `** driver exit status 0` and every pool's
    `ALL WORK ITEMS COMPLETE` (4, 4 and 2 lines, as RH1's).
  - `resumed-a` ends by the signal (`SIGTERM received`), inside the window.
  - No traceback in any log. Read every `Traceback`, `Error` and `WARNING` line and name each;
    the package's actors and pool print some lines SI's layer did not (09's results note), and
    each is named.
  - **The provenance line**, once in each log, names both packages at their commits, requested
    `v0.5.0` and `v0.2.0`, neither editable:
    `>> packages: datastorekit 0.5.0 (https://github.com/ds283/DatastoreKit@f47b9a255e9ad58e0d0eaf85644f53b575884d31, requested v0.5.0); raypoolkit 0.2.0 (https://github.com/ds283/RayPoolKit@eaef0ce60e2fc354bb32f0ad576010e6a83c1976, requested v0.2.0)`.
    Check it against 10a's results note, and quote what each log prints.
- **L2 — the resume is the reference.** §1.4.1 gives `RESULT: equal`, exit 0; the prune at
  `resumed-b`'s open removed only unvalidated rows (its printed reports against §1.3.4's count, and
  the store read `mode=ro`); `resumed-b` computed only what `resumed-a` had not kept, by
  `stage_counts.py`. **The prune is now the package's actor calling SI's hook** (a sharded class;
  no trajectory is pruned, since the signal falls after the trajectory stage). If the package
  prints the report differently, say exactly how, and whether `stage_counts.py` still finds it.
- **§4.3 — equal to RH1, bit for bit.** Every comparison of §1.4.2–§1.4.4 gives **`RESULT: equal`,
  exit 0**: every row of all 30 tables matched, and only bookkeeping differs. Say so table by
  table, with the row counts beside RH1's (07's results note). **Anything else is a miss** (§4).
- **L3 — every reader.**
  - `status.txt` on both stores: steps 0, 1 and 2 exit 0; step 4 exit 1; step 3 printed as not
    run (U11).
  - Step 4's `compare_stores` of `before/` against the store: **exactly one row more in `version`,
    labelled `2026.3.0`**, and otherwise only bookkeeping. The plot log reads
    `n_collocation_points: 1 value = [ 5 ]`.
  - **`scalar_data.csv`** on `resumed` and on `scalars` each hashes to
    **`b0564eecc22f9106dcccb57fd1a419749543c4b9d15dc0ffe7a8e0780e9058a2`**, RH0's and RH1's, byte
    for byte. If either differs, `diff` it against `out/07-readers-*-scalar_data.csv` and record
    every line; it is a miss.
  - **`--inventory`** (step 1) reports **no named problem** on either store, and the same values and
    counts as RH1's inventory (`out/07-readers-*-inventory.log`): the ten `δN★`, `N_init` 20,
    `N_final` 5, φ₀ 15, π₀ 0, m 1e-05 `PlanckMass`, 7,521 efold values, 1 trajectory and 10 of each
    instanton and compaction function validated, 0 unvalidated, no gradient row. Its layout is 10's (with 10b's counts),
    so the text differs from RH1's by design: compare the content, field by field.
- **L4 — RH1's pattern.** The builds that do not depend on the signal equal RH1's: for
  `reference` and `scalars`, `stage_counts.py`'s `entries`, `complete_lines`, `integrity` and
  `exit_status` equal `out/07-stage-counts.json`'s, less `packages` (which now names
  `datastorekit` too). A short scratch script, reproduced in the results note. The resume: the open
  prunes only unvalidated rows; the resume computes only what was not kept; the counts add up to
  `reference`'s (10 / 10 / 10 / 1). The figures depend on where the signal fell. **If L1–L3 and
  §4.3 hold and L4 differs,** that is a finding to explain (README §4.1), and it holds back G4
  (§3.6) for the user.

---

## 3. Acceptance

1. RH1's baseline is intact (§1.1).
2. L1–L3 hold, each shown, with the provenance line quoted and `--inventory` reporting no problem.
3. **§4.3:** RH2's three stores equal RH1's of the same mode, and so RH0's, bit for bit; the schema
   is RH1's, or each difference is the package's column order as 09 recorded it.
4. **L4** holds.
5. **H1:** `shard_key_audit` is OK on each store; the copy reads back with no problem and compares
   equal; it is deleted with `delete_store`, and nothing of it remains.
6. **DatastoreKit G4**, once 1–5 hold, and only then: the board's §2 records it as holding (the
   layer deleted at 09, the pin `v0.5.0` installed at 10a (`v0.4.0` at 08), the suites below, the grid rebuilt and
   equal to RH1). If L4 alone differs, record the rest and **do not mark G4**: stop and ask.
7. **The suites**, before `ray_cluster.sh start`: the default and `RAY_ADDRESS=local
   ./venv/bin/python -m pytest -m integration` give 10b's counts. Record them.
8. **No deliberate breakage** (README §5 rule 8): 11 changes no code. Each check is one a bad build
   fails, and RH0's control (02's D5) showed the comparison can fail.
9. **The records**, in the one commit:
   - **`verification.md` §3 RH2**, in §1's and §2's form: the cluster and the load; the builds,
     with their times and exit statuses, and every `resumed-a` attempt; L1–L4; the comparisons
     against RH1 and RH0, table by table; H1; the commands, verbatim. It says plainly whether RH2
     equals RH1;
   - `.documents/dk-and-rpk-migration/out/11-*`;
   - this board: the §1 row for 11; items L1–L4 (RH2), V3 and H1; gate **RH2** and **DatastoreKit
     G4** in §2; `### 5.N After prompt 11 (<date>)`, N the next free number;
   - a §3 entry for anything opened, with `.documents/OPEN-ISSUES.md` in the same commit.

---

## 4. Stop conditions — stop and ask

- The lock is held, an SI cluster is up, the machine is not idle, a store of §1.1 exists, RH1's
  baseline has moved, or the rehearsal tooling differs from RH0's.
- `reference` takes more than 45 minutes.
- A build fails, raises, or does not end as §2 says. **The package refuses something**: record the
  refusal whole; it is a finding about the package or about 09–10b, not something to work around
  (README §5 rule 11).
- `resumed-a` cannot be made to fall in its window in three attempts.
- An actor of the killed build is still alive after a minute.
- **A comparison misses** (§1.4.1–§1.4.4), or a `scalar_data.csv` differs. Then:
  - record `compare_stores`' full output (and the CSV `diff`), and name the first table in build
    order whose rows differ (trajectory, `FullInstanton`, `SlowRollInstanton`,
    `CompactionFunction`);
  - run the readers anyway only if the stores are otherwise sound, and say so;
  - **change no code, commit nothing, and mark no gate.** The cause is the package's or 08–10b's
    (README §4.1). Leave the results note and the verification section uncommitted, stop the
    cluster, and report.
- `--inventory` names a problem on an RH2 store, or `shard_key_audit` is not OK.
- A reader fails, or changes a store beyond the one `version` row and bookkeeping.
- `stage_counts.py` cannot parse a log: a changed printed line is a finding (README §5 rule 11).
- Anything would need a change to code, to a rehearsal script or to the tool.

---

## 5. What this prompt does not do

- **Files it changes:** `.documents/dk-and-rpk-migration/verification.md` (§3 added; §1 and §2 not
  touched, README §5 rule 6), `.documents/dk-and-rpk-migration/out/11-*`, the results note and this
  board. **No code.**
- It opens no store but its own three, the copy, the readers' copies, and RH1's and RH0's
  baselines read-only. Not `test-gradient*.sqlite`, anything under `out-*/`, the June or July
  stores, or RH0's earlier attempts' directories.
- It deletes no store but its own `11-resumed` files on a retry and the copy (§1.4.8), and no RH0
  or RH1 store ever (README §3).
- It installs nothing, pushes nothing, never runs `ray stop`, and leaves no SI cluster running and
  the lock free.
- It records G4 on this board only. DatastoreKit's and RayPoolKit's boards are 12's draft and the
  user's commits (P14).

---

## 6. The results note

`.documents/dk-and-rpk-migration/11-rehearse-through-both-packages.md`, using README §5.1. It
holds:
- RH1's baseline check (§1.1);
- the cluster's address and the load; whether other sessions held their suites;
- each command verbatim, and each build's start, end and exit status;
- `S` and why, with every attempt;
- the rows `resumed-a` left, by table, validated and not, and the actor check;
- L1–L4, each against RH1's, and every comparison of §1.4 in full;
- the provenance line as each log printed it;
- the two `scalar_data.csv` hashes, and the inventory against RH1's, field by field;
- H1: the audits, the copy, its comparison and its deletion;
- what the package printed that SI's layer did not, line by line;
- the two suites at dispatch;
- "State handed to the next prompt": for 12, G4's record for both packages' boards, the final
  counts, and anything opened.

**One commit**, in the repository's form, staged by explicit path only, after showing
`git diff --cached --name-only`.
