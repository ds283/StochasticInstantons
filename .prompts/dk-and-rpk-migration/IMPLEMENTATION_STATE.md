# dk-and-rpk-migration campaign — implementation state

**Last updated:** 2026-10-20 · **Status: LIVE — 8 of 13 prompts written (01–07, 01a), 01 and 01a
landed and reviewed, 03 landed (§5.15, awaiting review); 02 landed at its third attempt (§5.12, §5.13): RH0 holds and is bitwise
reproducible in both modes; 05–07 written after 02's review (§5.14). U1–U9 ruled (2026-10-12),
U10 (2026-10-19), U11 (2026-10-20); P1–P19 stand as proposed. The
DatastoreKit release requested by [`datastorekit-v0.2.4-brief.md`](datastorekit-v0.2.4-brief.md) is
out, as `v0.3.0` (README §0.4), and is carried unchanged into `v0.4.0`, which the campaign pins
(U10; README §0.5).**
The plan is [`README.md`](README.md), written on 2026-10-11 at `7bb3efd` and reviewed on
2026-10-12. Prompts 01–04 were written once the user had ruled (README §2.1).

The campaign adopts `raypoolkit` `v0.2.0` and then `datastorekit` `v0.4.0` (U10), which carries
`v0.3.0`, released for it (U3). A rehearsal by value
comes before any change (RH0), before the DatastoreKit swap (RH1) and after it (RH2). Each
package's gate G4 is recorded here when it holds.

**Campaign:** [`README.md`](README.md) ·
**Checklists:** DatastoreKit's and RayPoolKit's `docs/adoption/stochasticinstantons.md` (read, never
edited) ·
**Code:** `utilities.py`, `tools/`, `requirements.txt`, `RayTools/`, `Datastore/`, `config/`,
`main.py`, `plot_InstantonSolutions.py`, `plot_GradientCoupledSolutions.py`, `plotting/fetch.py`,
`tests/` ·
**Results:** `.documents/dk-and-rpk-migration/` (results notes; `verification.md`, created by
02) ·
**Index:** [`.documents/OPEN-ISSUES.md`](../../.documents/OPEN-ISSUES.md) §6a

> **Maintenance rule.** Whenever an entry is added to, narrowed in, or closed out of §3 or §4
> below, [`.documents/OPEN-ISSUES.md`](../../.documents/OPEN-ISSUES.md) is updated **in the same
> commit**: the row is added, moved or deleted, and the count and date in its header are
> corrected. See `CLAUDE.md`.

### Decisions

**Ruled by the user (README §6.1), U1–U9 on 2026-10-12, U10 on 2026-10-19 and U11 on 2026-10-20.** U1, U2 and U4–U7
were ruled as the planner recommended:

| Decision | Decided |
|---|---|
| **U1** — the order | RayPoolKit first, then DatastoreKit |
| **U2** — the rehearsals | the agent runs them (README §4.1) at RH0, RH1 and RH2: reference, killed-and-resumed, scalars-only, readers |
| **U3** — `DatastoreObject.timestamp` | **ruled 2026-10-12: fix the package.** DatastoreKit's `DatastoreObject` takes and exposes the row's timestamp, released as `v0.3.0` (README §0.4) and carried unchanged into `v0.4.0`, which 08 pins (U10) |
| **U4** — `InflatonTrajectory` under the replicated protocol | the cascade (orphan fix), `owner_column`, `validated_column` with `revalidate`, and the `prune` keyword, all before the swap (06) |
| **U5** — a drop that leaves references | refused before Ray starts, naming the groups to add (09) |
| **U6** — the inventory | ported to `inventory_spec` and `read_inventory` (10) |
| **U7** — relative to P2 | before P2; the tag `pre-datastorekit` on 07's commit; P2's audit reads the June and July stores at the tag |
| **U8** — spec coverage, for the fingerprint | **ruled 2026-10-12:** 10 proves every registered class is covered by a spec, read through one, or excluded with a reason (10's acceptance item 5); it settles `redshift`, `IntegrationSolver` and `GradientCoupledInstanton`'s second child table (README §6.1) |
| **U9** — other projects' Ray clusters | **ruled 2026-10-12, after 01's review:** isolate and lock. SI's cluster runs on `/tmp/ray-si` and its own ports and stops only itself, never by `ray stop`; one lock, `~/ScienceData/.rehearsal-lock`, shared with ChamPBH and SGK, lets one rehearsal run at a time. ChamPBH adopts the targeted stop; SGK takes the lock. Contract: [`rehearsal-lock-brief.md`](rehearsal-lock-brief.md); SI's side is 01a (README §6.1) |
| **U10** — which DatastoreKit release | **ruled 2026-10-19:** pin **`v0.4.0`** (tag object `8e7c1d7`, commit `c8570e8`) in place of `v0.3.0`. It adds `store_fingerprint.py`, which SI does not call, and carries `v0.3.0` unchanged; RunRegistryKit's `[stores]` extra requires `datastorekit>=0.4.0`. Only 08's pin and commit change (README §0.5, §6.1) |
| **U11** — the gradient branch in the rehearsals | **ruled 2026-10-20, after 02's first attempt:** drop it from every build. Its gradient solves did not finish in over five hours (`[gci-picard-inner-fails-on-rehearsal-grid]`). `build.sh`'s `dense` mode is `--targets homogeneous`, the interrupt moves to `STAGE 2`, and `run_readers.sh` no longer runs `plot_GradientCoupledSolutions.py`; the gradient tables are left to the suites (README §6.1, §5.12) |

**Proposed by the planner (README §6.2):** P1–P19, accepted as proposed: the user gave no ruling
on any of them.

---

## 1. Prompts

| # | Prompt | Covers | Model | Written? | Landed? | Commit | Results note |
|---|---|---|---|---|---|---|---|
| 01 | [Rehearsal tooling and run provenance](01-rehearsal-tooling-and-run-provenance.md) | P3, P5; README §4.1–§4.2 | Opus | ✍️ 2026-10-12 | ✅ 2026-10-12 | `84a5cfc` | [`01-rehearsal-tooling-and-run-provenance.md`](../../.documents/dk-and-rpk-migration/01-rehearsal-tooling-and-run-provenance.md) |
| 01a | [Isolate the rehearsal cluster](01a-isolate-the-rehearsal-cluster.md) | **U9**; `ray_cluster.sh`, the shared rehearsal lock | Sonnet | ✍️ 2026-10-12 | ✅ 2026-10-12 | `3556148` | [`01a-isolate-the-rehearsal-cluster.md`](../../.documents/dk-and-rpk-migration/01a-isolate-the-rehearsal-cluster.md) |
| 02 | [Rehearse the start tree (RH0)](02-rehearse-the-start-tree.md) | **RH0**; §4.3's measurement for both modes; the `slow` baseline | Opus | ✍️ 2026-10-12; amended 2026-10-20 (U11, and after the second attempt) | ✅ 2026-10-20, third attempt (§5.12, §5.13) | `5868231` | [`02-rehearse-the-start-tree.md`](../../.documents/dk-and-rpk-migration/02-rehearse-the-start-tree.md) |
| 03 | [Pin `raypoolkit` `v0.2.0`](03-pin-raypoolkit-v0.2.0.md) | the RayPoolKit pin | Sonnet | ✍️ 2026-10-12 | ✅ 2026-10-20 | this commit | [`03-pin-raypoolkit-v0.2.0.md`](../../.documents/dk-and-rpk-migration/03-pin-raypoolkit-v0.2.0.md) |
| 04 | [Adopt `raypoolkit`](04-adopt-raypoolkit.md) | the RayPoolKit swap; `_default_store_handler`; **RayPoolKit G4** | Sonnet | ✍️ 2026-10-12 | ⬜ | — | — |
| 05 | [Move SI's data out of the layer](05-move-si-data-out-of-the-layer.md) | `config/datastore.py`; the vectorized gets (P8) | Sonnet | ✍️ 2026-10-20 | ⬜ | — | — |
| 06 | [Prepare the `InflatonTrajectory` factories](06-prepare-the-inflaton-trajectory-factories.md) | **U4**, P17; closes `[inflaton-trajectory-prune-orphans-value-rows]` | Opus | ✍️ 2026-10-20 | ⬜ | — | — |
| 07 | [Rehearse before the DatastoreKit swap (RH1)](07-rehearse-before-the-datastore-swap.md) | **RH1**, bitwise against RH0; the tag (**U7**) | Opus | ✍️ 2026-10-20 | ⬜ | — | — |
| 08 | Pin `datastorekit` `v0.4.0` | the DatastoreKit pin (**U10**, carrying **U3**; `c8570e8`) | Sonnet | ⬜ | ⬜ | — | — |
| 09 | Adopt `datastorekit` | the DatastoreKit swap; **U5** | Opus | ⬜ | ⬜ | — | — |
| 10 | Port the inventory | **U6**; `inventory_spec`, `tools/inventory_report.py` | Opus | ⬜ | ⬜ | — | — |
| 11 | Rehearse through both packages (RH2) | **RH2**; **DatastoreKit G4** | Opus | ⬜ | ⬜ | — | — |
| 12 | Close the migration | `CLAUDE.md`, rules, documents, handover to P2, close | Sonnet | ⬜ | ⬜ | — | — |

**Legend.** ✍️ written · ⏸ held, with what it waits on · ⬜ not yet · ✅ landed.

**Held, by design (README §2.1).**
- **01–04** are written after the user's review of the plan. *Written 2026-10-12.*
- **01a** is written after 01's review, for U9. *Written 2026-10-12.* 02 waits on it.
- **05–07** are written after 02's review: RH0's reproducibility sets RH1's criterion. *Written
  2026-10-20 (§5.14):* RH0 is bitwise reproducible, so RH1 is held to bitwise equality.
- **08–11** are written after 07's review (`v0.4.0`, which 08 pins, is released).
- **12** is written after 11's review.

Orchestrator notes are written one prompt at a time, in [`orchestrator/`](orchestrator/), just
before each dispatch:
- [`prompt-01.md`](orchestrator/prompt-01.md) — used for 01 (`b4088d1`).
- [`prompt-01a.md`](orchestrator/prompt-01a.md) — used for 01a (`37126a2`).
- [`prompt-02.md`](orchestrator/prompt-02.md) — used for 02 (`0ff3609`; revised for U11 in `9caeea3` and for the reader fix in `b218760`, §5.12).

### 1.1 Items

| Item | Prompt | What | State |
|---|---|---|---|
| **T1** | 01 | `utilities.installed_package_provenance()` and `format_package_provenance()`; one line in each of the three drivers, before `ray.init(`; `tests/test_package_provenance.py` | ✅ 20 tests; today `>> packages: datastorekit not installed; raypoolkit not installed` |
| **T2** | 01 | `tools/compare_stores.py`: comparison by value, with the polymorphic references, the JSON columns and their timing keys, and the schema snapshot; `tests/test_compare_stores.py` | ✅ 24 tests; four polymorphic pairs, nine JSON columns, six timing keys |
| **T3** | 01 | `.documents/dk-and-rpk-migration/rehearsal/`: `build.sh`, `interrupt_when.py`, `stage_counts.py` (with `tests/test_rehearsal_stage_counts.py`), `run_readers.sh` | ✅ 5 tests; usage checked; never run on a build |
| **C1** | 01a | `ray_cluster.sh start\|stop\|status` in `.documents/dk-and-rpk-migration/rehearsal/`: SI's cluster on `/tmp/ray-si`, ports 6390/6391/8266/52366; the targeted stop | ✅ `bash` 3.2 and 5.3; the stop also matches the Ray client server by its `--address` (D1) |
| **C2** | 01a | the shared rehearsal lock, by [`rehearsal-lock-brief.md`](rehearsal-lock-brief.md) §2: acquire, refuse when held, owner file, checked release | ✅ refusal exit 3, owner printed; stop refuses another's lock (exit 1) |
| **C3** | 01a | the proof on a real cluster, no build: second acquire refused, a decoy on Ray's defaults survives SI's stop, SI's actors listed alone, another project's lock left alone | ✅ nine steps; decoy 19 processes before and after SI's stop; the actor line `ray list actors --address 127.0.0.1:6390` lists SI's actor alone; three breakages caught |
| **L1**–**L4** (RH0) | 02 | README §4.1 at 01's tree; §4.3's reproducibility measured for the dense and the scalars-only mode; L4 recorded as the baseline | ✅ L1–L3 hold; `resumed-a` left 6 validated and 2 unvalidated `FullInstanton`, `resumed-b` pruned the 2 and computed 4; **§4.3: bitwise reproducible in both modes** (only the readers' `version` row differs; against the readers' `before/` copies `RESULT: equal`); L4's counts in `out/02-stage-counts.txt` |
| **V1** | 02 | `.documents/dk-and-rpk-migration/verification.md` created, with §1 RH0; the two schema snapshots | ✅ [`verification.md`](../../.documents/dk-and-rpk-migration/verification.md) §1; `out/02-reference-schema.json`, `out/02-scalars-schema.json` (30 tables; they agree) |
| **S1** | 02 | the `slow` block's result at the start tree, the baseline for 09 | ✅ 69 passed of 69 (no failure, error or skip), 390 s; 11 `RuntimeWarning`s from `Numerics/OnionCoordinate.py:77`. 09's criterion: the same |
| **K1** | 03 | the `raypoolkit` pin in `requirements.txt` | ✅ one line at `:58`, between `ray==2.55.1` and `referencing==0.37.0` |
| **K2** | 03 | the venv installed from it | ✅ dry run and install each added `raypoolkit-0.2.0` alone |
| **K3** | 03 | the proof: one distribution added, at `eaef0ce6…`, the tag's files, not editable | ✅ freeze differs by one line; `pip check` clean; `direct_url.json` VCS at `eaef0ce6…`, `v0.2.0`, no `dir_info`; 4 of 4 modules byte-equal, no `tests/`; import starts no Ray |
| **W1** | 04 | `RayTools/` deleted | ⬜ |
| **W2** | 04 | the 3 imports rewritten to `from raypoolkit import RayWorkPool` | ⬜ |
| **W3** | 04 | `_default_store_handler` dropped: 7 lines of `main.py` | ⬜ |
| **W4** | 04 | no other pool site changed (P7) | ⬜ |
| **W5** | 04 | the prose naming the copy made true: `CLAUDE.md:95`, `ray-dispatch.md:99-106`, `FILE_MAP.md`, `INFRASTRUCTURE.md`, `architecture-summary.md` (P13) | ⬜ |

| **M1** | 05 | `config/datastore.py`: `factories` (30), `drop_groups` (5), `serial_batch_sizes` (29), moved verbatim with their imports | ⬜ |
| **M2** | 05 | the old layer imports them under its old names (`Datastore.py`, `ClientPool.py`); `_drop_order` and SI's fallback of 5 stay | ⬜ |
| **M3** | 05 | `config.sharding.vectorized_shard_key`; the 15 vectorized gets pass its mapping (P8) | ⬜ |
| **M4** | 05 | the four test stubs take the mapping (`test_plot_adapters_golden.py:1010`; `test_plot_extraction_golden.py:381`, `:450`, `:477`) | ⬜ |
| **M5** | 05 | `tests/test_config_datastore.py` (the data, captured literally; the layer reads it) and `tests/test_vectorized_shard_key.py` (the helper; the `ast` count of 15) | ⬜ |
| **M6** | 05 | `.documents/FILE_MAP.md`: the `Datastore.py` row, and a row for `config/datastore.py` (P13) | ⬜ |
| **I1** | 06 | `InflatonTrajectory`'s prune deletes its value rows first; the cascade map of `validate-on-startup.md` gains the row | ⬜ |
| **I2** | 06 | the hook parameter `prune` in all 12 hooks (P17), and in the examples of `validate-on-startup.md` and `datastore-factories.md` | ⬜ |
| **I3** | 06 | `register()`: `owner_column: "trajectory_serial"` on the value table, `validated_column: "validated"` on the trajectory | ⬜ |
| **I4** | 06 | `revalidate(serial, conn, table, tables)`, by `validate`'s rule as stored; its two premises checked against `store` and `object_store` | ⬜ |
| **I5** | 06 | `tests/test_inflaton_trajectory_prune.py`, without Ray: the cascade, `revalidate`, `prune` by signature, the keys | ⬜ |
| **I6** | 06 | an integration test: an unvalidated trajectory pruned at reopen on two shards, no orphan | ⬜ |
| **L1**–**L4** (RH1) | 07 | README §4.1 at 06's tree; bitwise equality with `02-reference.sqlite` and with `02-scalars-2.sqlite` / the readers' `before/` copy of `02-scalars.sqlite`, compared before the readers; `scalar_data.csv` `b0564eec…58a2`; L4 against RH0's pattern | ⬜ |
| **V2** | 07 | `verification.md` §2 RH1; `out/07-*` | ⬜ |
| **Z1** | 07 | the annotated tag `pre-datastorekit` on 07's commit (U7), not pushed | ⬜ |

Items of 08–12 are added when they are written.

The measurement the plan was written against is [`measure/out/`](measure/out/). It holds:
- both packages' scripts at `7bb3efd`, each equal to its checklist's appendix byte for byte;
- the suites' counts (default 631 of 761, 630 passed and 1 skipped; integration 61, 60 passed and
  1 skipped);
- the venv's `pip freeze` (README §0.2).

## 2. The gates

| Gate | Holds when | Prompt | State |
|---|---|---|---|
| RH0 | the start tree builds the grid, resumes it, builds it scalars-only, and its readers run (README §4.1); its reproducibility is measured (§4.3) | 02 | ✅ 2026-10-20 (§5.13): bitwise reproducible, dense and scalars-only |
| RayPoolKit G4 | `RayTools/` is gone; 0 imports of it and of `_default_store_handler`; the pin is installed; the suites pass; all 16 sites construct (RayPoolKit checklist item 8) | 04 (RH1, 07, adds the run under real Ray) | ⬜ |
| RH1 | 06's tree equals RH0 bit for bit, timings and timestamps aside (§5.13), dense and scalars-only; `pre-datastorekit` tagged | 07 | ⬜ |
| DatastoreKit `v0.2.3` | tagged on DatastoreKit's remote, with `store`, `validate` and `validate_on_startup` defaulted | — (carried into `v0.3.0`) | ✅ **released** 2026-10-11 for CPBH: tag object `8dac562`, commit `0de2b16`. Checked on the remote at planning |
| DatastoreKit `v0.3.0` | tagged on DatastoreKit's remote, its `DatastoreObject` taking and exposing `timestamp` (U3; made in DatastoreKit from the brief, not here) | — (carried into `v0.4.0`) | ✅ **released** 2026-10-12 by DatastoreKit's `object-timestamp` campaign: tag object `bf0a3b2`, commit `2f5417e`; checked on the remote and by `git show` of `object.py` (README §0.4) |
| DatastoreKit `v0.4.0` | tagged on DatastoreKit's remote, carrying `v0.3.0` unchanged (U10) | — (08 pins it) | ✅ **released** 2026-10-14 by DatastoreKit's `fingerprint` campaign: tag object `8e7c1d7`, commit `c8570e8`; checked on the remote 2026-10-19, and by `git diff --stat v0.3.0 v0.4.0`: `store_fingerprint.py`, its tests and golden data, the version, nothing else (README §0.5) |
| DatastoreKit G4 | the 9 layer files are gone (two emptied, P6), the pin (`v0.3.0` or later; SI `v0.4.0`) is installed, the default and integration suites pass, and a small grid rebuilt through the package (RH2) equals RH1 by value | 09, 10, 11 | ⬜ |

Recording each gate on its package's own extraction board is a commit in that repository, not
here (README P14).

## 3. Active and unresolved issues

Opened at planning, 2026-10-11, unless the row says otherwise.

| Issue | What | Owner |
|---|---|---|
| `[inflaton-trajectory-prune-orphans-value-rows]` | `InflatonTrajectory.validate_on_startup` (`Datastore/SQL/ObjectFactories/InflatonTrajectory.py:256-266`) deletes unvalidated trajectories and leaves their `InflatonTrajectoryValue` rows. This is the orphaning `.claude/rules/validate-on-startup.md` forbids, but its cascade map omits the class. A reused serial then meets its own orphans (a UNIQUE violation, as in the rule's recorded `SlowRollInstantonValue` incident). Under the package the fix also needs `owner_column` on the value table (README §0.1 item 9) | 06 (U4) |
| `[plot-scripts-stale-version-label]` | Both plot scripts open **read-write** under `plotting/provenance.py:18`'s `"2026.3.0"`, while `main.py:49` writes `"2026.6.1"`. So each plot run adds a `version` row to the store it reads, and the figure footers say `v2026.3.0`. Read-only plot pools are the goal (README P9, P10) | unowned; P2 when it bumps the label |
| `[redshift-registered-in-neither-table-list]` | `redshift` is registered (`Datastore/SQL/Datastore.py:99`) and has a batch size, but is in neither `replicated_tables` nor `sharded_tables`, and no SI code uses it: a ChamPBH leftover. `IntegrationSolver` is registered and replicated, but likewise unwritten by any driver (README P12) | unowned |
| `[test-counts-stale-in-claude-md]` | `CLAUDE.md:21` and `.claude/rules/test-selection.md:10`, `:26` say "464 of 571"; at `7bb3efd` the default run selects 631 of 761 | 12 |
| `[show-all-flag-unused]` | `--show-all` is parsed (`config/argument_parser.py`) but read by nothing: `main.py`'s inventory truncates at 20 values regardless | 10 (`verbose`) |
| `[unified-pipeline-stores-null-instanton-labels]` | *Opened 2026-10-12 at 01's review, from its Observation 2.* The unified pipeline (`--no-store-values`) constructs `FullInstanton` and `SlowRollInstanton` with no label (`ComputeTargets/pipeline.py:288-298`, `:304-314`), so they are stored with `label` NULL, where the per-stage queues store the factory's default (`Datastore/SQL/ObjectFactories/FullInstanton.py:149-155`, `SlowRollInstanton.py:148-154`). No science value differs and no reader fails, but the provenance footers read `label` (`plotting/provenance.py:46`), so a scalars-only store's figures lack it. `tools/compare_stores.py` treats the two columns as bookkeeping for this reason | unowned |
| `[gci-picard-inner-fails-on-rehearsal-grid]` | *Opened 2026-10-20 at 02's first attempt (§5.12).* At the rehearsal grid (`quadratic-minimal.yaml`, `m = 10⁻⁵ M_P`, `n = 5`, `α = 0.01`, no wall-clock budget) none of the four `GradientCoupledInstanton` solves of the first wave (`δN★` = 0.1, 0.4222, 0.7444, 1.711) finished in 5 h 24 min at full CPU. Each worker's log shows only `Picard inner failed at lambda=…`, 85–105 times, with λ halved after each failure and the sign alternating between outer attempts. July's 315 s a solve at `δN★ = 1.0` (`.documents/gradient-coupled-instanton/24-phase-a-deep-dive.md:43`) was measured at an older tree. Not investigated here: the gradient code is P3's, and the rehearsals no longer build it (U11). The workers' logs are kept in the orchestrator's scratchpad of 2026-10-20 only; the first attempt's store and log are under `$REHEARSAL_ROOT/02-attempt-1-aborted/` | P3 |

## 4. Resolved issues

| Issue | Resolved | How |
|---|---|---|
| `[ray-address-auto-attaches-to-foreign-cluster]` | 2026-10-12 (opened and closed the same day, §5.9, §5.10) | Every project's drivers defaulted to `--ray-address auto`, which attaches to any running cluster once the clusters are isolated (`ray_current_cluster` is no longer in `/tmp/ray`). The brief's §3 "Address it explicitly" now covers every run that takes the lock and forbids leaving a driver at `auto`; §5 asks SGK to pass `local` to its long builds. The user ruled SI's default: `--ray-address` is now required (`config/argument_parser.py`), for `main.py` and both plot scripts; `CLAUDE.md`'s run instructions say so. ChamPBH's and SGK's defaults are theirs to change |

## 5. Dispatch record

### 5.0 Planning (2026-10-11)

- Read both packages' SI checklists, with their addenda, the adoption READMEs and the client
  contract, and the CPBH and SGK campaign plans of the same name.
- Re-measured at `7bb3efd`:
  - both checklists' appendices reproduced byte for byte;
  - the default run 631 of 761 (630 passed, 1 skipped); integration 61 (60 passed, 1 skipped);
  - neither package installed; both tags on their remotes (README §0.2).
- Found in planning, beyond the checklists:
  - the `InflatonTrajectory` orphan bug and its interaction with the package's unit check (§3;
    README §0.1 item 9);
  - the hashing test stub that the mapping-form shard key breaks (README §0.1 item 3);
  - the polymorphic references and the timings inside JSON that a comparison by value must handle
    (README §0.1 item 11, §4.2);
  - the two version labels (§3).

### 5.1 U3 ruled (2026-10-12)

- The user asked whether the row's timestamp should be implemented in DatastoreKit rather than on a
  class of SI's own (the planner's first recommendation), and ruled that it should.
- Found while checking it: all three clients' factories write the `timestamp` column (SGK 19
  files, CPBH 16, SI 21 of 22), and only SI reads it back. No client class assigns a `timestamp`
  attribute that a read-only base property would break. The package inspects no object attribute
  that a new one would change. And no DatastoreKit decision chose to leave the timestamp out: its
  `object.py` is SGK's, verbatim.
- The plan was revised: 06 loses its timestamp half, and is the `InflatonTrajectory` work alone; 08
  pins the requested release; 09 rewrites the 18 `DatastoreObject` imports and changes no class.
  The request is [`datastorekit-v0.2.4-brief.md`](datastorekit-v0.2.4-brief.md).

### 5.2 U8 ruled (2026-10-12)

- Ruled in SGK, while planning the extraction of its run registry into RunRegistryKit
  (`docs/runregistry-extraction-audit.md`): RunRegistryKit's store layer requires a fingerprinter,
  and a client earns one by covering its registry with `inventory_spec()`, in its own DatastoreKit
  migration. ChamPBH's prompt 09 took the same acceptance the same day.
- Measured read-only at `7bb3efd`: 30 registered entries, 24 owners and 6 child tables; item 1's
  list misses `redshift` and `IntegrationSolver`; `GradientCoupledInstantonProfile` and
  `GradientCoupledInstantonValue` compete for one `values` slot.
- The plan was revised: 10 gains acceptance item 5 (README §2.2), U8 is added to §6.1 and a
  question for the user to §6.3. No other charter changes.

### 5.3 DatastoreKit `v0.3.0` (2026-10-12)

- DatastoreKit's `object-timestamp` campaign (closed at `5f972be`) released the brief's change as
  **`v0.3.0`**: tag object `bf0a3b2`, commit `2f5417e`. It is a minor release because it adds API.
  Checked here on the remote (`git ls-remote`), by `git show v0.3.0:datastorekit/object.py`, and
  by `git diff --stat v0.2.3 v0.3.0`: `object.py`, the version and tests, nothing else.
- The implementing agent relayed five points (README §0.4). The two that bear on SI:
  - `timestamp` is keyword-only, which all 24 SI sites satisfy;
  - a DatastoreKit test of `vars()` gained `_timestamp`, and no SI file calls `vars(`.
- The plan was revised: the pin is `v0.3.0` throughout. 08's hold on the release is lifted, and
  its acceptance gains the keyword-only check. U3's fallback is retired. The brief keeps its file
  name, as the record of the request.

### 5.4 The rulings, and prompts 01–04 written (2026-10-12)

- **The user ruled U1, U2 and U4–U7 as recommended**, and gave no ruling on P1–P19, which stand as
  proposed. With U3 and U8 (§5.1, §5.2), all eight decisions are ruled.
- **Prompts 01–04 written**, following ChamPBH's 01–04, which were dispatched and reviewed the same
  day. Its records gave these prompts six points:
  - a `SIGTERM`ed driver exits 134, not 143;
  - `ray stop` is run as a command of its own;
  - the throwaway commit is made with `commit-tree`, on no branch;
  - the recorded VCS URL has no `git+`;
  - the builds need a machine no other session is loading;
  - `ray start` may print no address, which is then in `/tmp/ray/ray_current_cluster`.
- **Beyond the README, found while writing:**
  - 01 models SI's tool and scripts on ChamPBH's (landed at ChamPBH `d7791c5`), and adds what
    ChamPBH's lacks: the structural comparison of JSON columns with their timing keys set aside.
  - **RH0 builds a second scalars-only store**, `02-scalars-2.sqlite`, so that the scalars-only
    mode's reproducibility is measured too. README §3, §4.1 and §4.3 amended.
  - 06's diff touches no `ComputeTargets/` file (the 12 prune hooks are all factories), so only 09
    runs the `slow` block. 02 records its baseline (S1).
- **Before 01 is dispatched:** the branch `dk-and-rpk-migration` is cut from `main` and carries the
  planning commit (P15). Each prompt's gate names it.

### 5.5 After prompt 01 (2026-10-12)

- **Landed:** `84a5cfc`, results note
  [`01-rehearsal-tooling-and-run-provenance.md`](../../.documents/dk-and-rpk-migration/01-rehearsal-tooling-and-run-provenance.md).
  **COMPLETE**: T1–T3; no §4 stop met; nothing opened.
- **T1.** `utilities.installed_package_provenance()` / `format_package_provenance()`; each driver
  prints one line, before `ray.init(` and its `ShardedPool(`, in the scope where it calls
  `ray.init` (the plot scripts' `__main__` block, not `run_plots`). Today:
  `>> packages: datastorekit not installed; raypoolkit not installed`.
- **T2.** `tools/compare_stores.py`, reading every file `mode=ro` through `sqlite3`, shards by glob,
  never a recorded path. Bookkeeping: `serial`, `timestamp`; `FullInstanton.label` and
  `SlowRollInstanton.label` (the unified pipeline stores them NULL, `ComputeTargets/pipeline.py:288`,
  `:304`); the JSON timing keys `compute_time`, `compute_time_total`,
  `mean_time_per_picard_iteration`, `picard_sweep_wallclock_min`/`_mean`/`_max`, at any depth.
  `GradientCoupledInstanton.label` is compared. Nine JSON columns compared structurally.
  **Four** polymorphic pairs (the README names two): `InflatonTrajectory.potential_*` and
  `diffusion_*` on `FullInstanton`, `SlowRollInstanton` and `GradientCoupledInstanton`. An SI
  primary holds the five layer tables and no client table (from the code). `redshift` is noted and
  compared as sharded.
- **T3.** The four rehearsal scripts; usage checked; `interrupt_when.py` tried on a scratch
  `sleep`; never run on a build.
- **Suites:** default 631 → **680** (679 passed, 1 skipped; +24 `test_compare_stores`, +20
  `test_package_provenance`, +5 `test_rehearsal_stage_counts`); integration 61 (60 passed, 1
  skipped), unchanged.
- **Breakages:** all six of prompt §3.6 caught, each recorded in the results note as a diff that
  `git apply` replays.
- **For 02:** `run_readers.sh` exits 1 when its step 4 finds the expected `2026.3.0` `version` row
  (read `status.txt`); `diagnostics_data.csv`'s timing columns are `diag_compute_time_<kind>`
  (results note, Observation 6). **For 04:** `main.py`'s lines after `:47` have moved by one or two
  (Observation 7).

**Orchestrator review of prompt 01 (2026-10-12)**, by orchestrator note
[`prompt-01.md`](orchestrator/prompt-01.md), at `84a5cfc`. All ten checks pass. Residue is fixed in
this follow-up, and one issue is opened from Observation 2.
- **(1) Scope.** 14 files, all on the prompt's §5 list; `OPEN-ISSUES.md` untouched. The tree is
  clean.
- **(2–3) T1.** Each field is read from its PEP 610 place. Eleven odd `direct_url.json` cases (a
  list, a string, not JSON, not UTF-8, `vcs_info` a list, `dir_info` a string, `editable` the
  string `"true"` or `false`, absent) and a `read_text` raising `PermissionError` all return
  without raising. With a stand-in `datastorekit-0.3.0.dist-info` first on `sys.path` and no mock,
  a VCS install reads
  `>> packages: datastorekit 0.3.0 (https://github.com/ds283/DatastoreKit@2f5417ea76cdcd0d15d64d80d9085429bfacad21, requested v0.3.0); raypoolkit not installed`;
  an editable one reads `(editable, file:///…)`, one with no `direct_url.json`
  `(no recorded origin)`.
- **(4) Drivers, by `ast` against `0209137`.** `main.py` differs by one import and one module-level
  print, directly before `ray.init(` and well before the `with ShardedPool(`. Each plot script
  differs by one import and one statement in its `__main__` block, directly before `ray.init(`
  and its `with`. `utilities.py` only gains two imports, the constant and the two functions.
- **(5) Opens.** On two copies of `test-gradient.sqlite` and its ten shards, under a logger around
  `sqlite3.connect`: 22 opens, all `file:…?mode=ro` with `uri=True`, all inside the copies, none
  of the originals that the copies' `shards` tables name. The tool imports the standard library
  only, and has no `ATTACH`.
- **(6) The real store.** A against B: exit 0, `RESULT: equal`, 30 tables (≈ 250,000 rows on the
  sharded side), 26 s at load average ≈ 100, `redshift` noted. Each perturbation applied to B
  only:
  - one ulp in a `FullInstantonValue.fields_json` float: exit 1, paired as a near miss with both
    hex values (relative difference 2.0e-16);
  - `GradientCoupledInstanton`'s `compute_time` and `mean_time_per_picard_iteration`, and one
    `FullInstanton.timestamp`, changed: exit 0, all three reported as bookkeeping;
  - one ulp in `FullInstanton.diagnostics_json["final_lambda"]`: exit 1, a near miss (1.6e-16);
    its 196 value rows and its `CompactionFunction` and 392 samples reported as "paired rows
    differing only through" their parent, which is better than ChamPBH's tool;
  - `FullInstanton.diffusion_type = 99`: exit 1, "unknown type value", no traceback;
  - `InflatonTrajectory.potential_type = 2` on every shard: exit 1, "unresolved reference …
    QuarticPotential" on each shard;
  - one shard's `tolerance` moved one ulp: exit 1, "replicated copies differ" for `tolerance` and
    for the two replicated tables that reference it;
  - one `CompactionFunction` and its 1,008 samples deleted: exit 1, A-only rows;
  - one shard file removed: exit 2, the count mismatch named;
  - the schema snapshot round-trips; a dropped `FullInstanton` index is reported.

  The copies were deleted afterwards. No store in the tree holds a gradient child row, so those
  two tables are exercised for real first by RH0.
- **(7) The maps.** Every bookkeeping entry, JSON column and timing key carries its `path:line` in
  the tool, and each was confirmed. No physics column is set aside. **The `label` ruling is
  accepted:** a per-stage row stores the factory's `.4g` rendering of values its foreign keys
  already compare, and the unified pipeline constructs the object with no label
  (`ComputeTargets/pipeline.py:288-298`), so the column carries no physics the comparison would
  miss. `GradientCoupledInstanton.label` is compared. The four polymorphic pairs are declared and
  test 12 checks both registries, non-empty, in both directions.
- **(8) Scripts and breakages.**
  - `build.sh`'s command matches README §4.1 token for token in both modes, under macOS
    `/bin/bash` 3.2 (the empty `EXTRA` array is safe under `set -u`), and it refuses an existing
    log.
  - `interrupt_when.py` on a `sleep 600`: it waited for the banner and then 2 s, sent `SIGTERM` to
    that pid only (exit 143; a second `sleep` was left alone). When the process exited first, it
    said so and returned 1.
  - `stage_counts.py` on a synthetic log keeps the two `STAGE 4` lines apart.
  - All six breakage diffs pass `git apply --check` and, replayed in bash, each fails exactly its
    named test(s); the tree is clean after `git apply -R`.
- **(9) Stores.** The 17 store files in the tree have unchanged mtimes and sizes.
  `~/ScienceData/StochasticInstantons-rehearsals/` does not exist.
- **(10) Records and suites.** The results note has README §5.1's sections and the prompt's §6
  additions. At `84a5cfc`: default **680** (679 passed, 1 skipped; 45 s), integration **61** (60
  passed, 1 skipped; 57 s, `RAY_ADDRESS=local`). Every new file has the licence header.
  - *Residue, fixed here:* "this commit" → `84a5cfc` (board and results note); this note added to
    the list of orchestrator notes; README §0.1 item 11, §2.2 (10's charter) and §4.2 now say
    four polymorphic references; the campaign's line in `.prompts/INDEX.md`.
- **Deviations D1–D10 are accepted.** D1–D3 are the brief's corrections.
- **Observations.** *Opened:* Observation 2, as §3
  `[unified-pipeline-stores-null-instanton-labels]`. *Not opened:* 1 is fixed here; 3, 5 and 6
  are recorded for the notes that use them; 4 and 7 are handed on.
- **Handed on.**
  - *To 02's note:* `run_readers.sh` exits 1 when step 4 finds the expected `2026.3.0` `version`
    row, so L3 reads `status.txt`; a `SIGTERM`ed driver exits 134, not 143; the
    `diagnostics_data.csv` timing columns are `diag_compute_time_<kind>`; the integration suite
    runs under `RAY_ADDRESS=local`, and `ray stop` stops every Ray process on the machine.
  - *To 04's note:* `main.py`'s lines after `:47` have moved by one or two (results note,
    Observation 7); 04's citations of `:410`, `:497`, `:664`, `:824`, `:848`, `:1097` need the
    new numbers.

### 5.6 U9 ruled, and prompt 01a written (2026-10-12)

- **Why.** At 01's dispatch, SGK's `runregistry-extraction` rehearsal was running on this machine
  (an in-process Ray instance, load average up to ≈ 500). Reading Ray 2.55.1 showed that `ray stop`
  takes no address and stops every Ray process on the machine, and that ChamPBH's protocol runs it
  after every rehearsal; two default `ray start --head` clusters also collide on 6379, 10001, 8265,
  52365 and `/tmp/ray/ray_current_cluster`. ChamPBH's BBN wall-clock limit makes its results
  sensitive to load.
- **The user ruled U9:** stay on this machine; isolate SI's cluster and stop it by a targeted stop;
  ChamPBH adopts the same stop; one lock shared by SI, ChamPBH and SGK keeps rehearsals apart. The
  alternative considered was moving the campaign to another machine (a rebuilt venv, two unpushed
  branches, the sibling repositories at the same paths, and all of RH0–RH2 there).
- **Written:** [`rehearsal-lock-brief.md`](rehearsal-lock-brief.md), the shared contract, for the
  user to hand to ChamPBH's and SGK's sessions; prompt **01a**; README §2, §2.1, §2.2, §4, §4.1,
  §5 (rules 17–18) and §6.1 (U9) amended; prompt 02 amended to use `ray_cluster.sh`, with its
  board entry renumbered to §5.8 (01a's is §5.7).
- **Prompts 03 and 04** run only the suites, so rule 17 covers them: their orchestrator notes give
  the `RAY_ADDRESS=local` form. Their text is unchanged.

### 5.7 After prompt 01a (2026-10-12)

- **Landed:** `3556148`; [results note](../../.documents/dk-and-rpk-migration/01a-isolate-the-rehearsal-cluster.md).
  `.documents/dk-and-rpk-migration/rehearsal/ray_cluster.sh start|stop|status`, items C1–C3. No
  Python changed; the suites are as at `84a5cfc` (680 and 61). No issue opened;
  `.documents/OPEN-ISSUES.md` unchanged.
- **The proof** (nine steps, on a real cluster, no build) passed under `/bin/bash` 3.2. A decoy on
  Ray's defaults and `/tmp/ray-decoy` ran beside SI's cluster; SI's stop left its 19 processes
  running and the decoy was then stopped by the same function. Another project's lock was refused
  by `start` (exit 3) and left by `stop` (exit 1). A start takes 6 to 18 s, a stop about 19 s
  (`gcs_server` ignores SIGTERM, so the 15 s grace always runs).
- **The actor line** is `./venv/bin/ray list actors --address 127.0.0.1:6390`. The bare form
  fails with two clusters up. `ray start --temp-dir /tmp/ray-si` writes `ray_current_cluster` into
  `/tmp/ray-si`; nothing is written to `/tmp/ray`; the file survives the stop.
- **A finding for the shared contract (D1).** Brief §3's stop (temp-dir match and descendants)
  leaves Ray's client server (`python -m ray.util.client.server --address=127.0.0.1:<GCS>
  --port=<client port>`) running: it has parent pid 1 and no temp dir. SI's stop adds it as a
  second seed. **ChamPBH's stop needs the same;** the brief is the orchestrator's to amend.
- **Breakages** B1–B3 caught (B2 by the start's stale-process guard, exit 4, not by the lock
  alone; B3 needs both owner checks removed).
- **To 02:** use `ray_cluster.sh start|stop` as README §4.1 says; exit 3 means stop and ask.

**Orchestrator review of prompt 01a (2026-10-12)**, by orchestrator note
[`prompt-01a.md`](orchestrator/prompt-01a.md), at `3556148`. All six checks pass. Residue fixed in
this follow-up, and the shared brief amended with D1.
- **(1) Scope.** Three files: the script, the results note, the board. The tree is clean.
- **(2) Reading.** No `ray stop` command in the script. The lock: `mkdir` without `-p` on
  `$HOME/ScienceData/.rehearsal-lock`, the seven owner keys in the brief's order, written through
  `owner.tmp`, released only after the owner's `project` and `ray_temp_dir` are checked (in `stop`
  before anything is signalled, and again in the release). The stop: the temp dir as a whole path
  component in both spellings, the client-server seed, descendants captured before signalling,
  the script and its ancestors exempt, `SIGTERM`, grace, `SIGKILL`, and the GCS port confirmed free.
- **(3) The proof, re-run by the orchestrator** under `/bin/bash` 3.2, with no other Ray process on
  the machine: `start` in 8 s with the owner file as specified; a second `start` exit 3 with the
  owner printed; a decoy on Ray's defaults with `/tmp/ray-decoy`; a detached actor on each cluster,
  each listed by its own `--address` and not by the other's. SI's set was 19 processes (the
  actor's worker included), the decoy's 19, disjoint, and together every Ray process running.
  `stop` took 18 s (`gcs_server` and the raylet `SIGKILL`ed after the grace); every SI pid gone;
  6390, 6391, 8266 and 52366 free; the lock released; the decoy's set identical and its actor still
  answering. The decoy then stopped by the same function; nothing left; all eight ports free.
- **(4) Breakages**, replayed without signalling anything: B1 widens SI's targets from 0 to 3 of a
  running decoy's processes; B2 makes `acquire_lock` succeed on a held lock (the start's
  stale-process guard, D3, is then the only defence, as the agent found); B3 lets `stop` remove a
  stand-in ChamPBH lock. Each reverted; the tree clean.
- **(5) Suites.** No Python changed since `84a5cfc` (`git diff --stat 84a5cfc 3556148 -- '*.py'`
  is empty); the agent's runs, before any cluster, gave 680 and 61.
- **(6) Records and leftovers.** Results note (README §5.1) and board §1 row, C1–C3, §5.7 present.
  No Ray process, no lock; the 17 store files unchanged.
- **D1 is accepted and carried into the brief** (§3 now names the client-server seed, the four
  ports, the measured actor command and where `ray_current_cluster` goes, and the hazard to a user
  shell that names the temp dir). D2–D8 are accepted.
- *Residue fixed here:* "this commit" → `3556148` (board and results note); "(not yet reviewed)"
  removed; this note added to the list of orchestrator notes.
- **Handed to 02's note:** the stop takes about 19 s; nothing else may name `/tmp/ray-si` during a
  stop; 01a's `ray_current_cluster` is in `/tmp/ray-si`, so `ray` CLI calls without `--address`
  still go wrong with two clusters up. ChamPBH and SGK must carry out the amended brief before
  their next rehearsal; until ChamPBH does, its `ray stop` can still kill SI's cluster, so 02
  runs only when the user confirms ChamPBH is not about to rehearse.

### 5.8 ChamPBH's port fixes taken into `ray_cluster.sh` (2026-10-12)

Made directly at the user's request, not by a prompt. ChamPBH's prompt 05a adapted SI's script
(ChamPBH `babd9d5`, reviewed in `ca2779d`) and added two fixes that SI's lacked; both are taken
here, with one addition.
- **The stop confirms all four ports free** (6390, 6391, 8266, 52366), as brief §3 asks, not the
  GCS port alone; the orchestrator's by-hand check in §5.7 (3) is now the script's own. `status`
  reports all four.
- **`start` refuses a held port**: after the lock and the stale-process guard, if any of the four
  is held it prints the listener, releases the lock and exits 4. Without this, a `ray start` that
  fails on a foreign listener leaves a stop whose port check cannot pass, and the lock held.
- **Addition (not in ChamPBH's):** `stop_cluster` requires all five arguments (temp dir and four
  ports) and returns 2 otherwise, so a two-argument call, as recorded in 01a's results note,
  cannot silently check one port.
- **Checked:** `bash -n` under 3.2 and 5.3; `--help` 0, no arguments 2; a two-argument
  `stop_cluster` exits 2; with `nc` on 6391, `start` exits 4 and starts nothing; a real cycle
  (lock free, no other Ray) started in 16 s, showed 18 processes and the four ports held, and
  stopped in 35 s (`gcs_server` and one other `SIGKILL`ed after the grace), leaving the four ports
  free and the lock released. 01a's decoy proof and breakages were not re-run. No Python changed;
  no issue opened; `.documents/OPEN-ISSUES.md` unchanged.
- **For 02's note:** ChamPBH has now carried out the amended brief (its 05a), so §5.7's caveat
  that ChamPBH's `ray stop` could kill SI's cluster no longer holds for ChamPBH's rehearsals; the
  lock still decides who runs.

### 5.9 SGK's review of the lock brief; `[ray-address-auto-attaches-to-foreign-cluster]` opened (2026-10-12)

SecondaryGWKit's agent raised two objections, handed over by the user.
- **"SI's script hard-wires the lock to SI"** (owner file, release check). True, and intended: the
  script is SI's tool for SI's cluster, and brief §5 asks SGK for a few protocol lines, not a
  script. SI's script handles an SGK in-process owner correctly: `start` exits 3, `stop` and
  `release_lock` refuse on the project mismatch and touch nothing, `status` checks the driver's
  pid. No change.
- **"`--ray-address auto` can attach SGK to another project's cluster."** The mechanism is
  confirmed in both Ray versions; the consequence is, today, a loud failure at `ray.init` (version
  mismatch), not work in the wrong cluster. The gap is the brief's and applies to all three
  projects. Opened as `[ray-address-auto-attaches-to-foreign-cluster]` (§3). The brief amendment
  (§3 "Address it explicitly", §5) is drafted for the user's review.

### 5.10 The brief amended; SI's `--ray-address` made required (2026-10-12)

At the user's request, not by a prompt.
- **The brief** (`rehearsal-lock-brief.md`): a second revision note; §3 "Address it explicitly"
  covers every run that takes the lock, long builds included, forbids leaving a driver at
  `auto` and says why; §5 asks SGK to give its long builds' drivers `--ray-address local`.
- **The user ruled SI's default:** `--ray-address` is required (`config/argument_parser.py`), so
  `main.py`, `plot_InstantonSolutions.py` and `plot_GradientCoupledSolutions.py` exit 2 without
  it. A value from a `--config` YAML file (`ray-address: local`) satisfies it. SI's rehearsal
  tooling (`build.sh`, `run_readers.sh`) already passes an address; no test parses the shared
  arguments. `CLAUDE.md`'s "Build and test" gives the flag, `local`, `ray_cluster.sh` and the
  ban on `ray stop`.
- **Checked:** the parser accepts the flag on the command line and from YAML and exits 2 without
  it; `main.py` without it exits with "the following arguments are required: --ray-address". The
  default suite gives 679 passed, 1 skipped (680, as at `84a5cfc`).
- `[ray-address-auto-attaches-to-foreign-cluster]` is closed (§4). ChamPBH and SGK receive the
  amended brief from the user; their defaults are theirs.

### 5.11 DatastoreKit `v0.4.0`; U10 ruled (2026-10-19)

At the user's request, not by a prompt. Read-only in DatastoreKit, RayPoolKit and RunRegistryKit.
- **DatastoreKit `v0.4.0`**, released 2026-10-14 by its `fingerprint` campaign: tag object
  `8e7c1d7`, commit `c8570e8`, checked by `git ls-remote`. `git diff --stat v0.3.0 v0.4.0 --
  datastorekit pyproject.toml` gives `store_fingerprint.py` (new, 351 lines), its tests and one
  golden data file under `datastorekit/tests/data/`, and the version line; `requires-python` and
  the dependencies are unchanged, and so are `object.py` and `store_inventory.py`. SI's checklist
  addendum for `v0.4.0` says "Nothing changes for SI": SI's pin is `v0.3.0` or `v0.4.0`, as SI
  chooses, and G4 reads "SI has adopted `v0.3.0` or later". SGK has adopted `v0.4.0`; CPBH stays
  on `v0.3.0`.
- **RayPoolKit has made no release since `v0.2.0`**: its remote has `v0.1.0` and `v0.2.0` only,
  and nothing under `raypoolkit/`, nor `pyproject.toml`, has changed since the tag (`main` at
  `17029d9`; documents and records only). Its SI checklist was last changed on 2026-10-10. 03 and
  04 stand.
- **RunRegistryKit**'s `[stores]` extra requires `datastorekit>=0.4.0`, and its SI checklist (with a
  `v0.2.0` note) has SI adopt the store layer after this campaign.
- **The user ruled U10: pin `v0.4.0`.** The plan was revised (README revision note of 2026-10-19,
  §0, new §0.5, §2, §2.1, §2.2's 08, §4, §6.1, §6.3, §7): 08 becomes "Pin `datastorekit`
  `v0.4.0`", checking commit `c8570e849334…` and `git archive v0.4.0`; its U3 and factory-base
  checks are unchanged. No prompt already written (01–04, 01a) cites the pin, so none changes; the
  `0.3.0` stand-in values in `tests/test_package_provenance.py` are fictitious and stay. No issue
  is opened or closed, so `.documents/OPEN-ISSUES.md` is unchanged.

### 5.12 02's first attempt stopped; U11 ruled (2026-10-20)

- **Dispatched** at 01:28 BST by orchestrator note [`prompt-02.md`](orchestrator/prompt-02.md)
  (`0ff3609`), on Opus. Before its cluster the agent ran both suites: 680 (679 passed, 1 skipped)
  and 61 (60 passed, 1 skipped). `ray_cluster.sh start` at 01:31:54 took the lock.
- **`reference`** (`build.sh 02 reference reference 127.0.0.1:6390 dense --profile-db`, then
  `--targets homogeneous gradient`) started at 01:32:04. The homogeneous branch was stored by
  01:32:37: the trajectory, then 10 `FullInstanton` (12.5 s), 10 `SlowRollInstanton` (8.7 s) and 10
  `CompactionFunction` (1.8 s), every pool complete and every row validated; the provenance line
  read `>> packages: datastorekit not installed; raypoolkit not installed`. `STAGE G` found 10
  `FullInstanton` seeds and started four solves. **None finished.** At 07:06, after 5 h 24 min at
  ~95–100% CPU each, every worker's own log showed only `Picard inner failed at lambda=…`
  (`δN★` 0.1 and 0.7444 and 1.711: 105 lines each; 0.4222: 85), λ halved after each failure; the
  driver's log had only Ray's raylet warning that `/tmp/ray-si` was "over 95% full" (40 GB free).
  No `GradientCoupledInstanton` row was stored.
- **The agent was cut off** by the usage limit while it waited on the build, so the stop
  condition (README P1, 45 minutes) was taken to the user by the orchestrator. The user ruled to
  stop the build. The orchestrator saved the four workers' logs to its scratchpad, sent `SIGTERM`
  to the driver (pid 93103) at 07:08:15 BST (exit 134, as expected; no actor left alive, no
  journal file), and ran `ray_cluster.sh stop` (19 s; `gcs_server` `SIGKILL`ed after the grace;
  the four ports free; the lock released). The 17 store files in the tree are unchanged.
- **The first attempt's files are kept**, moved intact to
  `$REHEARSAL_ROOT/02-attempt-1-aborted/` (the primary, ten shards, the profile database, and
  `logs/02-reference.log` and `.pid`), so that 02 can start afresh on its own names. Its
  primary's `shards` table records the old paths. Nothing was deleted.
- **The user ruled U11:** no rehearsal builds the gradient branch ("if the gradient solves don't
  converge, then they don't"). The alternatives were a wall-clock budget, which would make where a
  solve stops depend on load and so void §4.3's bitwise criterion, and finding a converging
  configuration, which is P3's physics work.
- **Made, at the user's ruling:**
  - `build.sh`: `dense` → `--targets homogeneous`; the usage and header say why. The gradient
    flags stay, since the driver mints their replicated rows whatever the targets
    (`config/pipeline_setup.py:95`), so the two modes differ by `--no-store-values` alone.
  - `run_readers.sh`: step 3 (`plot_GradientCoupledSolutions.py`) is no longer run on any store;
    it prints that it is not run.
  - README: a revision note; §0.2, §1, §4.1 (the grid, the interrupt in `STAGE 2`, L3), §4.3,
    §6.1 (U11) and §6.2 (P1) amended.
  - Prompt 02: an amendment note; the read-first list, §1.2, §1.3 (choosing `S` from the
    homogeneous timestamps, the `STAGE 2` banner with `--poll 0.2`, a wider window, the retry's
    build name, the rows to count), §2 and §6 amended; its board section is `### 5.13`.
  - Orchestrator note `prompt-02.md`, rewritten for the amended protocol.
  - `[gci-picard-inner-fails-on-rehearsal-grid]` opened (§3), with `.documents/OPEN-ISSUES.md`.
- **Checked:** `bash -n` under 3.2 and 5.3 for both scripts; both `--help` texts. No Python
  changed, so the suites stand at 680 and 61.
- **Known gap (U11):** no rehearsal writes `GradientCoupledInstanton` or its two child tables,
  so `compare_stores` meets them only in its imitation tests, and RH1 and RH2 check them only
  through the suites.
- **Next:** 02 is dispatched afresh on the amended protocol.

**The second attempt (2026-10-20, 07:37–07:46 BST), stopped at a reader.** Dispatched at
`9caeea3`. The suites before the cluster gave 680 and 61. All five builds ended as expected, in
24–35 s each: `resumed-a` (`S` = 10.5 s after the `STAGE 2` banner) left 3 validated
`FullInstanton` rows and nothing unvalidated; `resumed-b` computed the other 7 and every later
stage; no build pruned anything. `resumed-a` exited **15**, not 134 (its log shows Ray's
`SIGTERM received` and the absl stack dump). Then `run_readers.sh 02 resumed` added **two** rows
to `02-resumed.sqlite`, not one: the expected `version` `2026.3.0`, and
`n_collocation_points=33`. Step 2 ran `plot_InstantonSolutions.py` without the build's
`--n-collocation-points 5`, so the parser's default (`config/argument_parser.py:331-341`) reached
`config/pipeline_setup.py:95-106`, which gets-or-inserts it whatever the targets. A defect of 01's
script, older than U11 (only the removed step 3 passed the flag); the orchestrator's U11 commit
noted the same minting for `build.sh` and missed it here. The agent stopped (prompt §4), stopped
the cluster (lock released) and did not patch. Its preliminary comparisons: `scalars` against
`scalars-2` `RESULT: equal`; `reference` against the readers' `before/` copy of `resumed`
`RESULT: equal`.
- **The user ruled: fix and re-run all.** `run_readers.sh` step 2 now passes
  `--n-collocation-points 5 --alpha-regularization 0.01` on both branches (checked: the plot
  parser takes them, `[5] [0.01]`). `interrupt_when.py`'s docstring names the `STAGE 2` banner
  (agent's finding 4).
- **The second attempt's files are kept**, moved intact to
  `$REHEARSAL_ROOT/02-attempt-2-reader-defect/`: the four stores and the profile database, the
  ten logs and pidfiles, `02-readers/`, and the agent's four untracked `out/02-*` files
  (`repo-out-untracked/`). Nothing was deleted.
- **Next:** the same agent re-runs RH0 from the start on the standard names. Its other findings
  (the raylet's worker-count warning in `scalars`, the `PIPELINE LOOKUP` wording) go to its
  results note.

### 5.13 After prompt 02 (2026-10-20)

- **Landed:** `5868231`, results note
  [`02-rehearse-the-start-tree.md`](../../.documents/dk-and-rpk-migration/02-rehearse-the-start-tree.md),
  record [`verification.md`](../../.documents/dk-and-rpk-migration/verification.md) §1. **COMPLETE
  at the third attempt** (§5.12 records the first two): L1–L4 (RH0), V1 and S1; gate RH0 holds; no
  code changed; no issue opened, so `.documents/OPEN-ISSUES.md` is unchanged.
- **Cluster and load.** `ray_cluster.sh start` at 08:11 BST took 7 s, at a load of 4.5 on 10 CPUs
  with nothing foreign running; the address was `127.0.0.1:6390`. `stop` took 18 s, freed the
  four ports and released the lock.
- **Builds**, each 23–37 s:
  - `reference` 37 s, exit 0;
  - `resumed-a`, `S` = 11.0 s after the `STAGE 2` banner: exit 1, by `SIGTERM` (the log shows Ray's
    `SIGTERM received` and the absl stack; 134 and 15 at the earlier attempts). It left 6
    validated and 2 unvalidated `FullInstanton` rows, with 3,474 value rows. All 11 of its actors
    were dead 12 s after the signal;
  - `resumed-b` exit 0. Its open printed `Pruned 1 unvalidated FullInstanton records` on
    `shard0005` and on `shard0007` (2 = 2), and no orphan is left. It computed STAGE 2 "6
    already computed, 4 to compute", then 10 / 10;
  - `scalars` and `scalars-2`, exit 0.
- **Readers** (with `b218760`'s fix): steps 0–2 exit 0 on both stores, and each before/after
  comparison finds only `version{label='2026.3.0'}`. `scalar_data.csv` SHA-256 is
  `b0564eec…58a2` on both stores, byte-identical.
- **§4.3: RH0 is bitwise reproducible, dense and scalars-only.**
  - The prescribed comparisons exit 1 on the readers' `version` row alone, since prompt §1.4 runs
    the readers first.
  - `reference` against the readers' `before/` copy of `resumed`, and `before/` `scalars` against
    `scalars-2`, give `RESULT: equal`, exit 0. Every row of all 30 tables matched, and only
    timestamps and the JSON timing keys differ.
  - An independent per-δN★ hash of the value and sample tables agrees, and its control fails as
    it should.
  - **RH1 and RH2 are held to bitwise equality** with `02-reference.sqlite` and
    `02-scalars.sqlite`. The latter now carries the readers' `version` row; use its `before/` copy,
    or `02-scalars-2.sqlite`.
- **S1:** 69 passed of 69, 390 s, 11 `RuntimeWarning`s (`Numerics/OnionCoordinate.py:77`).
- **Suites:** cited from 07:39 BST, before the second attempt's cluster: 680 (679 passed, 1
  skipped) and 61 (60 passed, 1 skipped). Python has changed since only in `interrupt_when.py`'s
  docstring.
- **Deviations D1–D6:**
  - D1: the suites cited;
  - D2: `S` re-chosen;
  - D3: the comparisons' readers' row, and the `before/` comparisons added;
  - D4: exit 1;
  - D5: the independent check;
  - D6: the two CSVs staged byte-exact.
- **Observations, not opened:** the varying exit status; the population code's "slow-roll
  instanton is compensated" warnings in the plot logs; the raylet's worker-count warning in
  `scalars`; the `PIPELINE LOOKUP` wording; the 10 s `efold_value` minting before the first
  `FullInstanton` row.

**Orchestrator review of prompt 02 (2026-10-20)**, by orchestrator note
[`prompt-02.md`](orchestrator/prompt-02.md), at `5868231`. All eleven checks pass. Residue is fixed
in this follow-up; nothing is opened.
- **(1) Scope.** 24 files: the results note, `verification.md`, the board and 21 `out/02-*` files,
  all text, the largest 40 KB (the schema snapshots). No code. `git status` clean.
- **(2) Ray and the lock.** `ray_cluster.sh status`: lock free, no `/tmp/ray-si` process, the four
  ports free; no Ray process on the machine.
- **(3) The logs**, all five read. The provenance line once each, both packages not installed; no
  `STAGE G` banner and no `Traceback` anywhere. `reference`, `resumed-b`, `scalars`, `scalars-2`
  end `** driver exit status 0` with 4, 4, 2, 2 `ALL WORK ITEMS COMPLETE`. `resumed-a` shows
  `SIGTERM received` at 08:12:46.364 inside the `STAGE 2` pool and ends with status 1. The only
  `WARNING`/`Error` lines are the two prune headers, the raylet's disk warning and, in `scalars`,
  its worker-count warning.
- **(4) The counts.** `stage_counts.py` re-run on the five logs gives the committed text and JSON
  exactly. The orchestrator's own `mode=ro` read: every row of all four stores validated; 10
  `FullInstanton`, `SlowRollInstanton`, `CompactionFunction` and 1 trajectory (10 replicas) each;
  no `GradientCoupledInstanton`. In `02-resumed`, 6 `FullInstanton` rows predate the signal and 4
  follow it, and every `SlowRollInstanton` and `CompactionFunction` follows it: `resumed-b`'s "6
  already computed, 4 to compute", then 10 and 10. No `FullInstantonValue` orphan.
- **(5) The prune.** Two reports, both in `resumed-b`'s log, `shard0005-store` and
  `shard0007-store`, each `Pruned 1 unvalidated FullInstanton records`: the 2 unvalidated rows the
  agent read between builds. No other build pruned.
- **(6) §4.3, re-run.** All four comparisons re-run into the scratchpad give the committed
  `RESULT:` lines, exit codes, text and JSON exactly. The prescribed pairs differ only by the
  readers' `version{label='2026.3.0'}` row; the pairs against the readers' `before/` copies are
  `RESULT: equal`. All 30 tables listed, with the counts of §0; the bookkeeping that differs is
  only timestamps and the `compute_time` / `mean_time_per_picard_iteration` keys.
- **(7) Independently of the tool.** A scratchpad script hashed each trajectory, `FullInstanton`,
  `SlowRollInstanton` and `CompactionFunction` with its child rows by stored bits (references
  resolved recursively, the polymorphic pairs by type, JSON timing keys dropped, the two
  NULL-able labels skipped). `02-reference` against itself: 0 differing. `02-reference` against
  `02-resumed`: 0 differing, over 57,130 / 16,564 / 16,564 / 33,128 child rows each. `02-scalars`
  against `02-scalars-2`: 0 differing. Control `02-reference` against `02-scalars`: all 30
  instanton digests differ, as they must. On a scratch copy of `02-resumed` with one
  `FullInstantonValue` `P1_invPlanckMass` moved one ulp, it reported one `FullInstanton` differing,
  and `compare_stores` paired it as a near miss (relative difference 1.3e-16); the copy was
  deleted. **RH0 is bitwise reproducible in both modes, confirmed.**
- **(8) The readers.** `status.txt` on both stores: steps 0–2 exit 0, step 4 exit 1; each
  `4-compare_stores.log` finds only the `version` row; both plot logs read
  `n_collocation_points: 1 value = [ 5 ]`. Both `scalar_data.csv` hash to `b0564eec…58a2`, on disk
  and as committed blobs. The committed inventory logs are the readers' own with Ray's raylet disk
  warning removed (abridged, as the prompt allows).
- **(9) The baseline.** `--snapshot` of `02-reference` and `02-scalars` is byte-identical to the
  committed snapshots. The profile database holds `jobs` (1 row) and `profile_data` (807).
- **(10) Hygiene.** The 17 store files in the tree unchanged; everything under `~/ScienceData/`
  outside the SI root unchanged (only the directory's own mtime moved, with the lock); no file in
  either earlier attempt's directory touched. The root holds the four stores (45 files with the
  profile database), the two attempt directories, `logs/` (10 files) and `02-readers/`.
  `pip freeze` equals `measure/out/7bb3efd-pip-freeze.txt`. No scratch file in the repository.
- **(11) S1 and the records.** S1: 69 passed of 69, 390 s, nothing to re-run. The results note
  has README §5.1's sections, the three attempts and the prompt's §6 additions; `verification.md`
  has its introduction and §1 (§§1.0–1.7, the commands verbatim). The board has the §1 row, L1–L4,
  V1, S1, gate RH0 and §5.13. The orchestrator re-ran both suites at `5868231`: default 680 (679
  passed, 1 skipped), integration 61 (60 passed, 1 skipped).
  - *Residue, fixed here:* "this commit" → `5868231` (board ×2, results note); this note marked
    "used for 02"; the campaign's line in `.prompts/INDEX.md`.
- **Deviations D1–D6 are accepted.** D3 is right: the prompt runs the readers before the
  comparisons, and SI's plot scripts write a `version` row (`[plot-scripts-stale-version-label]`),
  so the prescribed comparisons cannot be empty; the `before/` comparisons measure what §4.3
  asks. D4 (exit 1) joins 134 and 15: Ray's handler varies, the log's `SIGTERM received` is the
  evidence.
- **Observations** are recorded and not opened: none affects a stored value or a later prompt's
  criterion.
- **Handed on.**
  - *To 05–07's writing:* **RH1 and RH2 are held to bitwise equality** with `02-reference.sqlite`
    (untouched by the readers) and, for the scalars-only mode, `02-scalars-2.sqlite` or
    `02-readers/scalars/before/02-scalars.sqlite` (`02-scalars.sqlite` carries the readers'
    `version` row). 07 and 11 should run their comparisons **before** their readers, which removes
    D3's detour.
  - *To 07's and 11's notes:* `S` from `reference`'s stored timestamps and its profile database's
    `object_get FullInstanton` call; the `FullInstanton` rows fall at banner +9.8 to +12.8 s; the
    signal's exit status may be 134, 15 or 1; `scalar_data.csv` `b0564eec…58a2` on both stores.
  - *To 09:* S1's baseline is 69 of 69 passed.
  - *U11's gap stands:* no rehearsal writes the gradient tables.

### 5.14 Prompts 05–07 written (2026-10-20)

Written at `7ceb089`, after 02's review, from README §2.2's charters and the review's "Handed on"
list. Nothing dispatched; no orchestrator note written (each is written just before its
dispatch). Nothing opened or closed, so `.documents/OPEN-ISSUES.md` is unchanged.
- **[05](05-move-si-data-out-of-the-layer.md)** (Sonnet), items M1–M6. Beyond the charter:
  - the layer imports the moved objects under its old names (`factories as _factories`,
    `drop_groups as _drop_actions`, `serial_batch_sizes as _default_serial_batch_size`), so that no
    line that reads them changes in the two protected files;
  - the registry is captured at the gate and written into the test literally, and the test also
    checks the layer's names are the same objects;
  - measured at `7ceb089`: the 15 calls (`main.py` 10, `plot_InstantonSolutions.py` 3,
    `plotting/fetch.py` 2) and the four stubs; registered with no batch size, `version` and
    `InflatonTrajectoryValue` (`"serial": False`); a size with no table, `temperature`. 05 records
    which of them lease serials, for 09;
  - P13: only `.documents/FILE_MAP.md` names the moved data; `CLAUDE.md` and `.claude/rules/` do
    not.
- **[06](06-prepare-the-inflaton-trajectory-factories.md)** (Opus), items I1–I6; closes
  `[inflaton-trajectory-prune-orphans-value-rows]`. Beyond the charter:
  - P13 also covers `.claude/rules/datastore-factories.md:205`, `:209`, whose example takes
    `prune_unvalidated`;
  - only the hook's parameter is renamed; the pool's, actor's and driver's `prune_unvalidated`
    stays (the package's `ShardedPool` takes it too);
  - `revalidate`'s rule rests on two premises the prompt checks: `object_store` runs `store` in
    one transaction with its value rows, and only a failed row has `N_end` NULL;
  - the integration test uses its own two-shard store and synthetic trajectories (no solve, so not
    `slow`), since `live_pool` is session-scoped and opened without the prune;
  - two breakages added to the charter's: a hook's parameter renamed back, and `owner_column`
    removed.
- **[07](07-rehearse-before-the-datastore-swap.md)** (Opus), items L1–L4 (RH1), V2, Z1. As the
  review handed on:
  - **bitwise equality** with `02-reference.sqlite` (dense) and with both `02-scalars-2.sqlite`
    and `02-readers/scalars/before/02-scalars.sqlite` (scalars-only), never `02-scalars.sqlite`,
    which carries the readers' `version` row;
  - **the comparisons run before the readers**, which removes 02's D3;
  - `scalar_data.csv` against `b0564eec…58a2`; L4 against RH0's resume pattern, and `reference`'s
    and `scalars`' stage counts line for line against RH0's;
  - a `SIGTERM`ed driver may exit 134, 15 or 1; `S` measured afresh, since the pool is now
    `raypoolkit`'s.

  Beyond it: the gate requires the rehearsal scripts and the tool unchanged since `5868231`, and
  RH0's `before/` comparisons re-run as a check that its stores are intact. An L4 difference holds
  the tag back for the user; on a miss the prompt commits nothing and tags nothing. The tag is
  annotated and not pushed (README §6.3).
- **For 03's and 04's orchestrator notes:** their prompts name their board sections
  `### 5.7 After prompt 03` and `### 5.8 After prompt 04`. Both numbers are taken (§5.7 is 01a's,
  §5.8 ChamPBH's port fixes), so each takes the next free number, as 05–07 say.

### 5.15 After prompt 03 (2026-10-20)

- **Landed:** this commit, results note
  [`03-pin-raypoolkit-v0.2.0.md`](../../.documents/dk-and-rpk-migration/03-pin-raypoolkit-v0.2.0.md).
  **COMPLETE:** K1–K3 hold; no code or test changed; no issue opened, so
  `.documents/OPEN-ISSUES.md` is unchanged. (The prompt names this section §5.7; that number is
  taken.)
- **K1.** `requirements.txt` gains `raypoolkit @ git+https://github.com/ds283/RayPoolKit@v0.2.0` at
  `:58`, nothing else.
- **K2.** The dry run reported `raypoolkit-0.2.0` alone; the install, run once, installed it alone.
  pip's `Resolved … to commit 4e7eb153…` names the tag object; the commit is `eaef0ce6…`. pip itself
  was not upgraded.
- **K3.** `pip freeze` differs from `measure/out/7bb3efd-pip-freeze.txt` by the one line
  `raypoolkit @ git+https://github.com/ds283/RayPoolKit@eaef0ce60e2fc354bb32f0ad576010e6a83c1976`;
  `pip check` is clean; `direct_url.json` is a VCS record at that commit, requested `v0.2.0`, no
  `dir_info`; the four modules equal `git archive v0.2.0`'s byte for byte and `tests/` is not
  installed; `import ray, raypoolkit` leaves `ray.is_initialized()` `False`. The provenance line is
  `>> packages: datastorekit not installed; raypoolkit 0.2.0 (https://github.com/ds283/RayPoolKit@eaef0ce60e2fc354bb32f0ad576010e6a83c1976, requested v0.2.0)`.
- **Suites:** 680 (679 passed, 1 skipped) and 61 (60 passed, 1 skipped), unchanged.
- **Rollback:** `git revert` of this commit **plus** `./venv/bin/pip uninstall -y raypoolkit`
  (README §4.4). The venv is outside git, so the revert alone leaves the package installed (inert
  until 04 imports it).
- **Deviations:** the board section number, and the suites' commands, both as the orchestrator's brief
  corrected; none unintended.
