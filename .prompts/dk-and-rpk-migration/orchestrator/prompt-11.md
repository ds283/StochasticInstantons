# Orchestrator — prompt 11, rehearse through both packages (RH2)

Read [`../README.md`](../README.md) first: §0.6, §2.2 (11's charter), §3, §4, §4.1–§4.3, §5 (rules 9,
11, 14, 17, 18) and §6.1 (U2, U9, U11, U12), §6.2 (P14). Then the board's §5.19 (07's review and its
"Handed on"), and the "Handed on" lines of §5.21–§5.27. The conventions are
[`prompt-01.md`](prompt-01.md)'s §0 "Conventions", unchanged but where this note says otherwise.
[`prompt-07.md`](prompt-07.md) is the model: 11 is 07 again, through `datastorekit` as well as
`raypoolkit`, and its conventions on background tasks, Ray, stores and verbatim commands hold here
unchanged.

**You do not write code.** You may:
- run the suites, `compare_stores.py`, `stage_counts.py` and `--snapshot` on the agent's stores;
- read the agent's stores, RH1's and RH0's with `sqlite3` in `mode=ro`, or with `read_inventory`,
  never through a pool;
- run `shard_key_audit` on the agent's stores, and a probe from the session scratchpad on a *copy*
  of one, never committing one;
- fix small residue in a follow-up commit of your own (§4).

**The prompt:** [`11-rehearse-through-both-packages.md`](../11-rehearse-through-both-packages.md) ·
**Board items:** L1–L4 (RH2), V3, H1; gates RH2 and DatastoreKit G4 · **Closes:** nothing ·
**Opens:** only what the work finds · **Model:** Opus, as the prompt recommends · **No network.**
Nothing is pushed, and no tag is made.

**Gate:**
- 08 (`1b1ca6d`), 09 (`f4da58f`), 10 (`e2c7b22`), 10a (`80d99a7`) and 10b (`19716cd`) landed and
  were reviewed (`e797705`, `e81239f`, `d0ce59c`, `8272efb`, `4e0f2fd`).
- `HEAD` is the commit that adds this note, or a later one that touches no code.
  `git diff --stat 19716cd HEAD -- . ':!.prompts' ':!.documents'` is empty.
- The rehearsal tooling is RH0's: `git diff 5868231 HEAD -- .documents/dk-and-rpk-migration/rehearsal/
  tools/compare_stores.py` is empty.
- No SI cluster is up, the lock is free, and no other session runs a suite, a build or a Ray job on
  this machine while 11 runs (the user has been asked; §2).

## 0. What makes this prompt unusual

**It is the first build through `datastorekit` under a real cluster, and G4 hangs on it.** 09 swapped
the layer and 10–10b ported the inventory, but every store since 07 has been a test's: two shards,
a private Ray, a handful of rows. RH2 is the first grid built, killed, pruned, reopened and read by
the package's pool, actors, broker and `ProfileAgent`, with the package's replicated-write protocol
(a `replication_in_flight` record per replicated write) and its reconciliation at open. RH1 equals
RH0 bit for bit (board §5.19), so the criterion is **bitwise equality** with RH1's stores of the same
mode, timings and timestamps aside. A vacuous "equal" would mark DatastoreKit's G4 on an
unrehearsed swap, so the review re-runs every comparison and checks the dense and scalars-only
pairs independently of the tool.

**What the package does differently, measured for this note** (the package at `v0.5.0`, installed;
`P` is `venv/lib/python3.13/site-packages/datastorekit`):
- **The prune of a sharded class is still the actor's, and prints what RH1 printed.** `P/SQL/Datastore.py:470-505`:
  under `prune_unvalidated` each actor prunes the sharded classes and prints the header
  `!! INTEGRITY WARNING (…): datastore "shardNNNN-store" (physical file …)`, then the factory's own
  lines (`Pruned N unvalidated FullInstanton records`). `stage_counts.py`'s `INTEGRITY` pattern
  (`^(?:Pruned|Found) \d+ unvalidated `) reads them as before. A replicated class is pruned by the
  pool before any actor exists, under a `prune` record, with lines of its own (`… pruned by the pool
  under a "prune" record` per shard, then `>> Pruned the unvalidated rows of "<class>" from every
  shard …`; 09's results note shows them). The signal falls after the trajectory stage, so none is
  expected.
- **A killed driver may leave a replicated write in flight, and the next open repairs it.** Every
  replicated `object_get`, `object_store` and `object_validate` commits a record on the primary
  before the controlling shard's call and deletes it after the replicas'
  (`P/SQL/ShardedPool.py:3147-3170`); "any exception after step 1 leaves the record set". The
  driver's `efold_value` minting (`main.py:564`, one vector get per instanton grid) is such a write,
  and so is every replicated lookup in STAGE 2. Ray 2.55.1's driver handler turns `SIGTERM` into
  `sys.exit(15)` (`ray/_private/worker.py:1656-1660`), so the `SystemExit` may unwind through a
  replicated write and then through `main.py:1273`'s `with ShardedPool(...)`, whose `__exit__`
  closes every actor (ChamPBH's R2, its board §5.15: exit 15, the pool closed). `resumed-b`'s open
  then runs `_reconcile_replicated_tables` (`:1203-1330`) before any actor exists: a hot journal is
  rolled back (`>> Rolled back the journal left beside …`); a record over identical shards is
  cleared; a record whose interrupted write explains a difference is repaired from the controlling
  shard; any other difference raises `ReplicatedDivergence` and nothing opens. The repair prints
  `>> Sharded datastore "…" was opened with a replicated write in flight (operation=…, class=…,
  controlling shard=…, store_id=…, started=…)`, then `>>   copied …`, `>>   set …` or
  `>>   every shard already holds what the controlling shard holds: nothing was repaired`, then
  `>>   the replication_in_flight record was cleared` (`:2146-2177`). **A repair is the package's
  documented behaviour, recorded verbatim, not a stop; a refusal is a stop** (prompt §4, "the
  package refuses something").
- **The profile labels are RH1's.** `P/SQL/Datastore.py:524-531` records `object_get` with metadata
  `{'object': 'FullInstanton', 'type': 'vector'|'scalar'}`, the strings RH1's profile database
  holds, so 07's way of dating the `STAGE 2` banner holds. Other method names (leases, releases,
  `object_read_batch`) are the package's.
- **H1, prototyped.** On a two-shard SI store built through the package by
  `tests/test_inventory_store.py`'s `_STORE_SCRIPT` (the scratchpad's `orch11/h1/`):
  `shard_key_audit` printed its schema, row-count, distribution and cross-file lines and
  `VERDICT: OK -- no inconsistency found in <primary>.`, exit 0; `sharded_store copy` printed
  `>> copy: "<dst>" with 2 shards` and one `>>   shard #N: <path>` line each, exit 0;
  `read_inventory` of source and copy, no Ray initialised: `problems == ()` on both, 24 classes,
  every `(records, validated)` count equal; `compare_stores.py` source against copy `RESULT:
  equal`, exit 0; `ShardedPool.closed_store_files(copy)` and `ShardedPool.delete_store(copy)` the
  same three paths (shards in serial order, then the primary), and none left. `shard_key_audit`
  refuses (exit 2) a primary not in the package's format, so it is run on RH2's stores only.
- **The schema.** A package store's `--snapshot` differs from `out/07-reference-schema.json` in its
  `source` line alone (`out/09-temp-schema.json` against 07's: one line), since columns are compared
  as sets; `--schema` of the prototype store against `out/07-reference-schema.json`: "RESULT: the
  schemas agree", exit 0. So RH2's should agree, and a difference is a finding.

**Where the acceptance can pass vacuously.**
- **A comparison against the wrong baseline, or after the readers.** The readers add a `version`
  row to `11-resumed` and `11-scalars`, and RH1's `07-resumed` and `07-scalars` already carry one.
  §1.4's comparisons run before the readers, against `07-reference.sqlite` and
  `07-readers/scalars/before/07-scalars.sqlite` / `02-scalars-2.sqlite`; the JSON names both paths,
  and the review reads them.
- **An "equal" over empty tables.** Each comparison's table-by-table counts are shown beside RH1's
  (1 / 10 / 10 / 10 parents; 57,130 / 16,564 / 16,564 / 33,128 child rows dense, 57,130 and none
  scalars-only, `InflatonTrajectoryValue` counted over its ten replicas). A store missing a stage
  would compare unequal, but a count read off the wrong file would not.
- **L4 compared by eye, or against itself.** A scratch script compares 11's `entries`,
  `complete_lines`, `integrity` and `exit_status` for `reference` and `scalars` with
  `out/07-stage-counts.json`'s, less `packages`, with a control that fails (07's `l4_compare.py`,
  its paths changed, and its control: `reference` against `resumed-b`).
- **A resume that kept nothing, or everything.** The narrow window is "some `FullInstanton` rows
  stored and validated, others not". `resumed-a`'s rows are read `mode=ro` between the builds; a
  signal before the first row or after the last is outside the window and is retried (07's D4).
- **`--inventory` "no problem" on a refused store.** Step 1's exit status is 0 and its log shows the
  report with `problems: none` and the counts of the prompt's §2 L3; an exit 1 is a refusal.
- **H1's copy compared with itself.** `11-compare-reference-copy` names `11-reference.sqlite` and
  `11-reference-copy.sqlite`; the read-back compares the copy's counts with `11-reference`'s, not
  the copy's with the copy's.
- **The CSV hash of a converted file.** The committed blobs, not only the files on disk, hash to
  `b0564eec…58a2` (correction 10).

**Corrections to the prompt.** Pass them on.
1. **The board.**
   - The section is **`### 5.28 After prompt 11 (<date>)`**, appended after §5.27. The header's "Last
     updated" and status line are updated to match.
   - The §1 row for 11 is `IMPLEMENTATION_STATE.md:77`; the items are `:173-175`. **The L1–L4 (RH2)
     row's "at 10's tree" is stale** (U12): it is 10b's tree, on `v0.5.0`; correct it in place.
   - **§2 has no row for gate RH2.** Add one after RH1's (`:191`), in its form: "10b's tree, through
     both packages, equals RH1 bit for bit, timings and timestamps aside, dense and scalars-only |
     11 | …".
   - The DatastoreKit G4 row is `:195`; it is marked only under acceptance 6.
   - `.prompts/INDEX.md` and the board's list of orchestrator notes are the orchestrator's, at the
     review.
2. **"10b's counts"** are **732 (731 passed, 1 skipped)** and **67 (66 passed, 1 skipped)**, re-run by
   10b's review at `19716cd` (board §5.27, check 10). Run as `./venv/bin/python -m pytest -m "not
   integration and not slow" -q -p no:cacheprovider` and `RAY_ADDRESS=local ./venv/bin/python -m
   pytest -m integration -q -p no:cacheprovider`, serially, in the foreground, **before**
   `ray_cluster.sh start`. The `slow` block is not run.
3. **The provenance line, measured at `HEAD`**
   (`utilities.format_package_provenance(utilities.installed_package_provenance())`), exactly the
   prompt's:
   `>> packages: datastorekit 0.5.0 (https://github.com/ds283/DatastoreKit@f47b9a255e9ad58e0d0eaf85644f53b575884d31, requested v0.5.0); raypoolkit 0.2.0 (https://github.com/ds283/RayPoolKit@eaef0ce60e2fc354bb32f0ad576010e6a83c1976, requested v0.2.0)`.
   Both `editable: False`.
4. **The prune report** is §0's first bullet. If Ray marks a line `[repeated Nx across cluster]`,
   read the actors' own logs under `/tmp/ray-si/session_*/logs/` **before** `ray_cluster.sh stop`.
   L2's "if the package prints the report differently" is answered by §0: the sharded prune prints
   RH1's text; say whether it did, and whether `stage_counts.py` found it.
5. **Between `resumed-a` and `resumed-b`** (prompt §1.3.4), read also, `mode=ro`:
   - the primary's `replication_in_flight` rows (all columns);
   - any `-journal`, `-wal` or `-shm` file beside the primary or a shard;
   - the `efold_value` row count on each shard (a replicated table: equal on every shard, or the
     record explains why not).

   Then read `resumed-b`'s log for §0's reconciliation lines before its first banner, and quote every
   `>>` line between the provenance line and `>> Opened existing sharded datastore …`. If a record
   was left, record what the open did with it; L2 and §4.3 must still hold.
6. **`S`.** RH1's `rows.py` (07's results note, "The scratch scripts") reads a package store
   unchanged (it reads `timestamp`, `validated` and `delta_Nstar_serial`), and the profile labels are
   RH1's (§0). Each grid's minting is now a replicated write with two extra commits on the primary,
   so the window may sit later than RH1's +9.49 … +12.07 s: measure it from `11-reference`, and on a
   loaded machine aim later in it. Every attempt, its `S` and the rows it left are recorded, as 07's.
7. **`--json OUT` takes the next argument as its output file**, in both `stage_counts.py` and
   `compare_stores.py`. ChamPBH's orchestrator once overwrote a build log by passing a log path
   after `--json` (ChamPBH board §5.15). Write `--json .documents/dk-and-rpk-migration/out/11-….json`
   with the output path explicitly, and never a log or store path after `--json`.
8. **The comparisons' file names** are the prompt's (§1.4), each `.txt` and `.json`, under
   `.documents/dk-and-rpk-migration/out/`: `11-compare-reference-resumed`,
   `11-compare-07reference-11reference`, `11-compare-07reference-11resumed`,
   `11-compare-07scalarsbefore-11scalars`, `11-compare-02scalars2-11scalars`,
   `11-compare-02reference-11reference`, `11-compare-reference-copy`; with
   `11-reference-schema.json` and `11-stage-counts.{txt,json}`. Each is run with `--json`, its text
   saved beside it, its exit code recorded.
9. **H1** (prompt §1.4.8), as §0's prototype. Save the audits, the copy's output, the read-back
   (a short script, reproduced in the results note) and `closed_store_files` then `delete_store`'s
   lists as `out/11-h1-*.txt`. `11-reference-profile.sqlite` is not part of the store and is not
   copied; `compare_stores.py`'s shard glob for `11-reference` (`11-reference-shard*`) does not meet
   the copy's `11-reference-copy-shard*`. The copy is made and deleted after the comparisons of
   §1.4.1–§1.4.7 and before the readers.
10. **The readers' outputs kept** are 07's names with `11-`: `out/11-readers-{resumed,scalars}-{status.txt,
    inventory.log,compare_stores.txt,scalar_data.csv}` and `out/11-scalar_data.sha256`. The
    inventory logs may drop the raylet's disk lines only, and say so (with `--inventory` before Ray,
    there may be none). **The CSVs** are ignored by `.git/info/exclude` (`*.csv`), have CRLF endings,
    and the repository's `core.autocrlf` is `input`, so stage them as 07's D5 did,
    `git -c core.autocrlf=false add -f <path>`, and check `git show :<path> | shasum -a 256` gives
    `b0564eec…58a2`.
11. **The inventory against RH1's**, field by field (prompt §2 L3): 10's layout with 10b's counts, so
    the text differs by design. The values and counts to find are 07's results note's (L3, "What
    `--inventory` printed"), with the gradient-coupled class at 0 records and `problems: none`.
12. **The profile database** is not under §4.3. Record its tables and per-method counts beside RH1's
    (`jobs` 1; `profile_data` 803: `object_get` 443, `lease_serials` 135, `commit_serials` 76,
    `release` 59, `object_store` 40, `object_validate_item` 40, `read_largest_store_ids` 10; 07's
    results note). The package's method names and counts may differ; each difference is described,
    not a stop.
13. **G4** (acceptance 6). DatastoreKit's checklist item 9 asks for the layer files deleted and the
    package imported at the pinned tag, both suites passing, and a small grid rebuilt through the
    package; the `v0.5.0` addendum keeps "SI has adopted `v0.3.0` or later". The board's G4 row
    records: the layer deleted at 09 (`f4da58f`), the pin `v0.5.0` installed at 10a (`80d99a7`;
    `v0.4.0` at 08, `1b1ca6d`), the suites at dispatch, and RH2 equal to RH1. The results note's
    "State handed to the next prompt" gives the text of the record for DatastoreKit's board (12's
    draft, the user's commit; P14), as ChamPBH's 10 did for its G3.
14. **`verification.md`**: §3 RH2 is appended after §2.7, in §2's form; the introduction, §1 and §2
    are not touched (README §5 rule 6).
15. **`.documents/OPEN-ISSUES.md`** is touched only if an issue opens; it stands at **59 open, 29
    closed**.
16. **Other sessions.** The orchestrator asked the user at dispatch to hold other sessions' suites
    until RH2 is done, and passes on the answer. The agent still checks at its start (`pgrep -fl`
    for `pytest`, `unittest`, `main.py`, Ray processes; the load), and a foreign suite or Ray job
    **before** the cluster starts is a stop and ask. **Once the cluster is up, a foreign suite is
    recorded, not a stop** (07's ruling, board §5.19), unless it stops a build.
17. **The disk** has 20 GB free (98% used, 2026-10-22 21:14). The raylet's "over 95% full" line is
    expected (07's said 40 GB available). A refusal by Ray for lack of disk is a stop.

**The facts, checked by the orchestrator on 2026-10-22 at `4e0f2fd`, 21:14–21:30 BST.** Pass them
on.
- **The tree.** Branch `dk-and-rpk-migration`, clean, `HEAD` `4e0f2fd` before this note;
  `git diff --cached` empty. Since 10b's `19716cd`, one commit, records only (`.prompts/`,
  `.documents/`). The tooling diff since `5868231` is 0 bytes. The 17 store files of prompt-01.md
  §1 step 5 are in the tree (ignored); none is the agent's.
- **Ray and the lock.** `ray_cluster.sh status`: lock free (`~/ScienceData/.rehearsal-lock`
  absent), no `/tmp/ray-si` process, ports 6390, 6391, 8266 and 52366 free. `pgrep` finds no
  `gcs_server`, `raylet`, `ray::`, `pytest`, `unittest` or `main.py`. `RAY_ADDRESS` unset.
- **The machine.** 10 CPUs. Load 27.9 / 25.6 / 35.8 at 21:14, 10.9 / 17.7 / 29.9 at 21:18; the top
  processes were desktop apps (ChronoSync, WindowServer, VS Code, Tower), no suite or Ray job.
- **The time zone** is BST (UTC+1) until 25 October. Stores and profile databases stamp naive local
  time; `interrupt_when.py` prints UTC. Every cross-comparison says which it uses.
- **The venv.** `pip freeze` 83 lines: `datastorekit @ git+…@f47b9a255e9ad58e0d0eaf85644f53b575884d31`
  and `raypoolkit @ git+…@eaef0ce60e2fc354bb32f0ad576010e6a83c1976`; `pip check` clean; `ray`
  2.55.1. 11 installs nothing.
- **DatastoreKit** `2900d82`, **RayPoolKit** `17029d9`, both clean. Read only.
- **RH1's baseline is intact.** `compare_stores.py $R/07-reference.sqlite
  $R/07-readers/resumed/before/07-resumed.sqlite` and `compare_stores.py
  $R/07-readers/scalars/before/07-scalars.sqlite $R/02-scalars-2.sqlite`: both `RESULT: equal`,
  exit 0. `07-reference`, both `before/` copies, `02-reference` and `02-scalars-2` each have a
  primary and ten shards.
- **`$REHEARSAL_ROOT`** holds RH0's and RH1's stores, `02-reference-profile.sqlite`,
  `07-reference-profile.sqlite`, `02-attempt-1-aborted/`, `02-attempt-2-reader-defect/`,
  `02-readers/`, `07-readers/` and `logs/` (ten `02-*` and ten `07-*` files). **No `11-*` file
  exists.**
- **Expected**, from RH1 (07's results note): `reference` about 36 s (stages 5.5, 12.1, 8.8, 1.6 s);
  each dense store 1 trajectory (5,713 value rows on each of 10 shards), 10 each of `FullInstanton`
  (16,564 value rows), `SlowRollInstanton` (16,564) and `CompactionFunction` (33,128 samples),
  `efold_value` 7,521, `delta_Nstar` 10, no gradient row; the scalars-only store the same with the
  three value/sample tables empty. `scalar_data.csv` `b0564eec…58a2`, 11 lines, 3,592 bytes. A
  `SIGTERM`ed driver may exit 134, 15 or 1. `ray_cluster.sh` start 7 s, stop 18 s.
- **What is not a failure:** Ray's start-up `FutureWarning`s; `(raylet) … have not registered within
  the timeout` under load; the raylet's disk warning; its `16 PYTHON worker processes …` advisory in
  `scalars`; the plot logs' `slow-roll instanton is compensated` physics warnings; the package's
  reconciliation lines of §0 when a record was left. Any other `Traceback`, `Error` or `WARNING`
  line is read in full and recorded; `!! WARNING: … did not validate` is a finding.

**What the review exists to establish.**
- **(E1) The builds.** Each log has the provenance line of correction 3 once, its banners and
  summaries, and `** driver exit status`, as the prompt's §2 L1 says. `resumed-a` died by the signal
  inside its window, and its actors were gone before `resumed-b`.
- **(E2) The resume.** By the stage counts and by the stores' rows and timestamps: `resumed-b`
  computed exactly what `resumed-a` had not kept validated, pruned only unvalidated rows, and did
  with any record left in flight what §0 says.
- **(E3) §4.3.** All six comparisons of §1.4.1–§1.4.4, re-run, give the agent's results; each RH2
  store equals RH1's (and RH0's) of its mode bit for bit, confirmed by a per-δN★ digest independent
  of the tool, with its control shown able to fail.
- **(E4) The readers.** Steps 0–2 exit 0 for each store; each before/after comparison holds only the
  `2026.3.0` `version` row and bookkeeping; both `scalar_data.csv` hash to `b0564eec…58a2`;
  `--inventory` reports no problem and RH1's values and counts.
- **(E5) L4.** `reference`'s and `scalars`' parsed stage counts equal RH1's, less `packages`; the
  resume's pattern holds.
- **(E6) H1.** The three audits OK; the copy read back and compared equal; deleted, nothing left.
- **(E7) Hygiene.** No code changed; no store opened but the agent's own, its copy, its readers'
  copies and RH1's and RH0's read-only; RH0's and RH1's files untouched; no SI cluster, the lock
  free; the venv as it was.
- **(E8) The records.** `verification.md` §3, the results note, `out/11-*`, the board (gate RH2
  added, G4 marked only if 1–5 hold).

## 1. Before you dispatch

1. **The tree.** `git status --short` clean, `git diff --cached` empty, the tooling diff empty.
2. **Ray and the lock.** `ray_cluster.sh status` clean; no Ray process.
3. **The venv.** `pip freeze` saved; `pip check` clean; the provenance line.
4. **The load and the disk.** `uptime`, `df -h ~`, the top processes.
5. **Mtimes**, for check 11: the 17 store files in the tree, and every entry under `~/ScienceData/`,
   by `/usr/bin/stat -f '%m %z %N'`. DatastoreKit's and RayPoolKit's `HEAD` and
   `git status --porcelain`.
6. **RH1's baseline**, both comparisons; no `11-*` file; the measurements of §0 (the package's prune,
   record and repair paths, the profile labels, H1 on a prototype, the schema).

**Done 2026-10-22, 21:14–21:30 BST,** at `4e0f2fd`: all six hold, step 6 as §0 records. In `orch11/`
in the session scratchpad: `pip-freeze.txt` (83), `mtimes-stores.txt` (17), `mtimes-sciencedata.txt`
(835 entries, 661 of them SI's rehearsal root; the same count as 10b's), `base-dense.txt`,
`base-scalars.txt`; `h1/` (the prototype store, `build.py`, `h1read.py`); and, copied from 07's
review scratchpad, `indep.py` (per-parent digests by stored bits; run with each primary's `.sqlite`
path; re-run on `02-reference` against `07-reference`: 0 differing digests over 1 / 10 / 10 / 10
parents, 57,130 / 16,564 / 16,564 / 33,128 child rows each side), `rows.py` and `l4cmp.py`.

## 2. Dispatch

**First, ask the user** to have other sessions hold their suites, builds and Ray jobs until RH2 is
done (prompt gate; board §5.19), and record the answer in the agent's brief.

Then one fresh-context subagent, on **Opus**, in the background. Give it:
- the prompt;
- the campaign README and the board;
- 07's results note and `verification.md` §2; 09's, 10's, 10a's and 10b's results notes ("State
  handed to the next prompt", and 09's account of the package's printed lines);
  `rehearsal-lock-brief.md` §2–§3;
- `HEAD`, the load, the user's answer, and §0 of this note, up to "## 1. Before you dispatch" only,
  as a copy in the session scratchpad. It does not read `orchestrator/`. It may read `orch11/h1/`.

Tell it plainly:
- **One commit, at the end, made once**, unless a comparison misses (then none: the records stay
  uncommitted, the cluster stopped, and it reports). Its results note is
  `.documents/dk-and-rpk-migration/11-rehearse-through-both-packages.md`, in README §5.1's form,
  with the prompt's §6 additions. Stage by explicit path, and show `git diff --cached --name-only`
  before committing.
- **The files it may add or change** are the prompt's §5 list (`verification.md` §3, `out/11-*`, the
  results note, the board) and `.documents/OPEN-ISSUES.md` if an issue opens. **No code, no
  rehearsal script, no tool, no test, not the README, not `.prompts/INDEX.md`, nothing in the venv,
  nothing in DatastoreKit, RayPoolKit, ChamPBH or SGK.** No push, no tag.
- **It runs the protocol** with §0's corrections: the suites before the cluster, each build as a
  background task waited on by notification (or `Monitor` on `** driver exit status`), never a loop
  of `sleep`. **Never `ray stop`.**
- **Stop and ask** on any of the prompt's §4 conditions, and on a refusal by the package: stop the
  cluster first, then reply with its state, the lock's state and the logs' paths. The orchestrator
  takes it to the user, and the agent resumes by `SendMessage`.
- **It replies with:**
  - the results note's path and the commit (or why there is none);
  - RH1's baseline check;
  - the load at each build's start, the address, the actor line, and each build's start, end, wall
    time and exit status, every `resumed-a` attempt included;
  - `S`, and the timestamps it was chosen from;
  - the rows `resumed-a` left, by table, validated and not, the `replication_in_flight` rows, any
    journal file, and the actor check;
  - every `>>` and `!!` line of `resumed-b`'s open, verbatim;
  - the stage counts, the L4 comparison with RH1's records, and each prune report with where it was
    read;
  - all six comparisons' `RESULT:` lines and exit codes, table by table with row counts beside RH1's,
    and the full text of any that is not 0;
  - the schema checks;
  - H1: the three audits' verdicts, the copy, its read-back, its comparison, the deleted paths;
  - the profile database's tables and counts beside RH1's;
  - the readers' statuses, the two `scalar_data.csv` SHA-256s, and the inventory beside RH1's;
  - the provenance line as each log printed it;
  - every line the package printed that RH1's layer did not, named;
  - the two suites, with the load;
  - the G4 record's text, and the board's §2 rows for RH2 and G4;
  - every deviation with its class;
  - the "State handed to the next prompt" section, verbatim.

## 3. The review — twelve checks

1. **Scope.** `git show --stat <commit>` touches only `verification.md`, `out/11-*`, the results note,
   the board and, if an issue opened, `OPEN-ISSUES.md`. Every `out/11-*` file is text and under about
   1 MB. `git status --short` clean; one commit of the agent's since this note, no amend in the
   reflog; no tag made; nothing pushed; no scratch file in the repository. `verification.md`'s diff
   only appends.
2. **Ray and the lock.** `ray_cluster.sh status` clean; no `/tmp/ray-si` process; ports free. The note
   shows `start`, its address and actor line, the actor check before `resumed-b`, and `stop` with the
   lock released. `ray stop` appears only as "never run".
3. **E1, the logs**, all in `$REHEARSAL_ROOT/logs/11-*`, read whole. The provenance line of correction
   3 once each. `reference`, `resumed-b`, `scalars` end `** driver exit status 0` with 4, 4, 2
   `ALL WORK ITEMS COMPLETE`; each `resumed-a` attempt shows `SIGTERM received` inside the `STAGE 2`
   pool. No `STAGE G` banner. `grep -n 'Traceback\|Error\|WARNING'` gives only §0's known lines.
   `interrupt_when.py`'s output: banner seen, `S` waited, `SIGTERM` to the pidfile's pid at a time
   matching the log.
4. **E2 and E5, the counts.** `stage_counts.py` re-run on the logs, its `--json` into the scratchpad
   (correction 7), equals the committed text and JSON. `orch11/l4cmp.py` compares `reference`'s and
   `scalars`' records with `out/07-stage-counts.json`'s (`entries`, `complete_lines`, `integrity`,
   `exit_status`), with its control. Then `mode=ro`: every row of the three stores validated, the
   counts of §0; in `11-resumed`, the rows per table timestamped before the signal (in BST) equal
   `resumed-b`'s "already computed", and those after equal its compute counts; no orphan value row.
5. **E2, the prune and the reconciliation.** Every report read in full; the total pruned in
   `resumed-b` equals the unvalidated count recorded between builds; no other build pruned; no
   trajectory pruned. If a `replication_in_flight` row was recorded after `resumed-a`, `resumed-b`'s
   open printed its repair or clearing, and the primary's table is empty now.
6. **E6, H1.** `shard_key_audit` re-run on the three RH2 stores: `VERDICT: OK`, exit 0. No
   `11-reference-copy*` file exists; `out/11-h1-*` shows `closed_store_files` and `delete_store` the
   same 11 paths, each `11-reference-copy*`; the read-back's counts are `11-reference`'s.
7. **E3, §4.3, re-run.** The six comparisons into the scratchpad. The readers have since written their
   `version` row into `11-resumed` and `11-scalars`, so re-run those against the readers' `before/`
   copies (the stores as the builds left them): `RESULT:` line, exit code and JSON equal the
   committed ones but for paths. All 30 tables with §0's counts; bookkeeping that differs only
   timestamps, `serial`, the two NULL-able labels and the timing keys.
8. **E3, independently of the tool.** `orch11/indep.py`: `07-reference` against `11-reference`, and
   against `11-readers/resumed/before/11-resumed`; `07-readers/scalars/before/07-scalars` against
   `11-readers/scalars/before/11-scalars`; `02-reference` against `11-reference`: 0 differing
   digests, equal child-row counts. Control: `11-reference` against `11-scalars`, every instanton
   digest differs; and a scratch copy of `11-reference` with one `FullInstantonValue` float moved one
   ulp, caught by both the script and `compare_stores` (then deleted). (`indep.py` folds a
   `GradientCoupledInstanton` child into a trajectory's digest, so it reads a replicated trajectory's
   copies as different where gradient rows exist; RH2's stores have none.)
9. **E4, the readers.** `status.txt` on both stores; each `4-compare_stores.log` finds only
   `version{label='2026.3.0'}`; plot logs read `n_collocation_points: 1 value = [ 5 ]`; `shasum -a
   256` of both `scalar_data.csv`, on disk and as committed blobs, is `b0564eec…58a2`; `main.py
   --inventory` re-run on both RH2 stores (`--ray-address 127.0.0.1:9`, before Ray): exit 0, the
   committed inventory logs' report, `problems: none`, RH1's values and counts.
10. **E5 and E8, the schema and the profile database.** `--snapshot` of `11-reference` (to the
    scratchpad) is byte-identical to the committed `out/11-reference-schema.json`, which differs from
    07's only in `source`; `--schema` of `11-reference` and `11-scalars` against 07's: "the schemas
    agree". The profile database, `mode=ro`, as recorded.
11. **E7, hygiene.** The 17 store files and every entry under `~/ScienceData/` outside the files 11
    created have their §1 mtimes and sizes (RH0's and RH1's stores, `before/` copies, logs, profile
    databases and the two attempt directories included). `$REHEARSAL_ROOT` gains only `11-*` stores,
    `11-reference-profile.sqlite`, `11-readers/` and `logs/11-*`; any retry deleted only its own
    `11-resumed` files. `pip freeze` equals §1's; `pip check` clean. DatastoreKit and RayPoolKit as at
    §1 (another session may move them; nothing of theirs may be the agent's).
12. **E8, the records and the suites.** The results note in README §5.1's form with the prompt's §6
    list; `verification.md` §3 with the commands verbatim and the plain statement whether RH2 equals
    RH1; the board's §1 row (✅, "this commit"), L1–L4 (RH2, its tree corrected), V3, H1, the new RH2
    gate row, the G4 row (marked only if acceptance 1–5 hold), `### 5.28`. The orchestrator re-runs
    both suites at `<commit>`: 732 and 67.

## 4. After the review

- **Record it on the board** as an *Orchestrator review of prompt 11* paragraph in §5.28: what each
  check found, the re-run comparisons and the independent check, and anything handed on. Fix small
  residue in a follow-up commit of its own:
  - "this commit" → the SHA (board, results note, `verification.md`, the G4 record's text);
  - this note added to the board's list of orchestrator notes, marked "used for 11";
  - `.prompts/INDEX.md`: the campaign's line (11 landed and reviewed; RH2 holds; DatastoreKit G4).
- Anything the review finds that is not residue is opened on the board's §3 and in the index, in the
  same commit.
- **Report to the user:**
  - §4.3's answer for each mode, in one sentence each;
  - the builds' times under the measured load, and `S`;
  - the resume: what `resumed-a` left (and any record in flight), what was pruned or repaired, what
    `resumed-b` recomputed;
  - the readers, the inventory and the two SHA-256s; H1;
  - G4, and that recording it on DatastoreKit's and RayPoolKit's boards is 12's draft and the user's
    commit (P14);
  - anything opened.
- **Then 12 is written** (README §2.1), at the reviewed tree.
