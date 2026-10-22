# dk-and-rpk-migration campaign — implementation state

**Last updated:** 2026-10-22 · **Status: LIVE — 14 of 15 prompts written (01–11, 01a, 10a, 10b), 01 and 01a
landed and reviewed; 02 landed at its third attempt (§5.12, §5.13): RH0 holds and is bitwise
reproducible in both modes; 05–07 written after 02's review (§5.14); 03 landed and reviewed
(§5.15): `raypoolkit` `v0.2.0` pinned and installed; 04 landed and reviewed (§5.16): `RayTools/` deleted,
the pool is the package's, RayPoolKit G4 holds; 05 landed and reviewed (§5.17): SI's data is `config/datastore.py`, the 15 vectorized gets pass the mapping; 06 landed and reviewed (§5.18): `InflatonTrajectory`'s prune cascades to its value rows, the 12 hooks take `prune`, and the factories carry `owner_column`, `validated_column` and `revalidate`; 07 landed and reviewed (§5.19): RH1 equals RH0 bit for bit in both modes, and `pre-datastorekit` is tagged (annotated; pushed by the user 2026-10-21); 08–11 written (§5.20); 08 landed and reviewed (§5.21): `datastorekit` `v0.4.0` pinned and installed, one distribution added, K7 holds on the installed package; 09 landed and reviewed (§5.22): SI's layer deleted, every pool the package's, U5's drop policy before Ray, `--inventory` refused until 10, `[config-datastore-cannot-be-imported-before-the-layer]` closed; 10 landed and reviewed (§5.23): the inventory is `read_inventory` over 24 `inventory_spec`s (22 definitions), `tools/inventory_report.py` prints it before Ray, every registered class is covered (U8), `[show-all-flag-unused]` closed and `[gci-value-table-outside-the-inventory]` opened; DatastoreKit `v0.5.0` released at SI's request and evaluated (§5.24, §5.25), 10a and 10b written to adopt it before 11 (U12); 10a landed and reviewed (§5.26): `datastorekit` `v0.5.0` pinned and installed, the distribution replaced, K11 holds on the installed package; 10b landed (§5.27): `GradientCoupledInstanton`'s spec counts `GradientCoupledInstantonValue` as a further value table, every registered class is covered and none excluded (24 specs, 6 read through), the report prints the count, `[gci-value-table-outside-the-inventory]` closed. U1–U9 ruled (2026-10-12),
U10 (2026-10-19), U11 (2026-10-20), U12 (2026-10-22); P1–P19 stand as proposed. The
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

**Ruled by the user (README §6.1), U1–U9 on 2026-10-12, U10 on 2026-10-19, U11 on 2026-10-20 and U12 on 2026-10-22.** U1, U2 and U4–U7
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
| **U12** — DatastoreKit `v0.5.0` (a second value table), and where | **ruled 2026-10-22, as recommended:** adopt it **before 11**. 10a pins `v0.5.0` (tag object `6a6809d`, commit `f47b9a2`) in a commit of its own; 10b declares `GradientCoupledInstantonValue` in `GradientCoupledInstanton`'s spec as a further value table and closes `[gci-value-table-outside-the-inventory]`; 11 rehearses `v0.5.0` at 10b's tree (README §0.6, §6.1) |

**Proposed by the planner (README §6.2):** P1–P19, accepted as proposed: the user gave no ruling
on any of them.

---

## 1. Prompts

| # | Prompt | Covers | Model | Written? | Landed? | Commit | Results note |
|---|---|---|---|---|---|---|---|
| 01 | [Rehearsal tooling and run provenance](01-rehearsal-tooling-and-run-provenance.md) | P3, P5; README §4.1–§4.2 | Opus | ✍️ 2026-10-12 | ✅ 2026-10-12 | `84a5cfc` | [`01-rehearsal-tooling-and-run-provenance.md`](../../.documents/dk-and-rpk-migration/01-rehearsal-tooling-and-run-provenance.md) |
| 01a | [Isolate the rehearsal cluster](01a-isolate-the-rehearsal-cluster.md) | **U9**; `ray_cluster.sh`, the shared rehearsal lock | Sonnet | ✍️ 2026-10-12 | ✅ 2026-10-12 | `3556148` | [`01a-isolate-the-rehearsal-cluster.md`](../../.documents/dk-and-rpk-migration/01a-isolate-the-rehearsal-cluster.md) |
| 02 | [Rehearse the start tree (RH0)](02-rehearse-the-start-tree.md) | **RH0**; §4.3's measurement for both modes; the `slow` baseline | Opus | ✍️ 2026-10-12; amended 2026-10-20 (U11, and after the second attempt) | ✅ 2026-10-20, third attempt (§5.12, §5.13) | `5868231` | [`02-rehearse-the-start-tree.md`](../../.documents/dk-and-rpk-migration/02-rehearse-the-start-tree.md) |
| 03 | [Pin `raypoolkit` `v0.2.0`](03-pin-raypoolkit-v0.2.0.md) | the RayPoolKit pin | Sonnet | ✍️ 2026-10-12 | ✅ 2026-10-20 | `5396a3d` | [`03-pin-raypoolkit-v0.2.0.md`](../../.documents/dk-and-rpk-migration/03-pin-raypoolkit-v0.2.0.md) |
| 04 | [Adopt `raypoolkit`](04-adopt-raypoolkit.md) | the RayPoolKit swap; `_default_store_handler`; **RayPoolKit G4** | Sonnet | ✍️ 2026-10-12 | ✅ 2026-10-20 | `ef13445` | [`04-adopt-raypoolkit.md`](../../.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md) |
| 05 | [Move SI's data out of the layer](05-move-si-data-out-of-the-layer.md) | `config/datastore.py`; the vectorized gets (P8) | Sonnet | ✍️ 2026-10-20 | ✅ 2026-10-20 | `875cf41` | [`05-move-si-data-out-of-the-layer.md`](../../.documents/dk-and-rpk-migration/05-move-si-data-out-of-the-layer.md) |
| 06 | [Prepare the `InflatonTrajectory` factories](06-prepare-the-inflaton-trajectory-factories.md) | **U4**, P17; closes `[inflaton-trajectory-prune-orphans-value-rows]` | Opus | ✍️ 2026-10-20 | ✅ 2026-10-20 | `5e41ce8` | [`06-prepare-the-inflaton-trajectory-factories.md`](../../.documents/dk-and-rpk-migration/06-prepare-the-inflaton-trajectory-factories.md) |
| 07 | [Rehearse before the DatastoreKit swap (RH1)](07-rehearse-before-the-datastore-swap.md) | **RH1**, bitwise against RH0; the tag (**U7**) | Opus | ✍️ 2026-10-20 | ✅ 2026-10-21 (§5.19) | `0527480`, tagged `pre-datastorekit` | [`07-rehearse-before-the-datastore-swap.md`](../../.documents/dk-and-rpk-migration/07-rehearse-before-the-datastore-swap.md) |
| 08 | [Pin `datastorekit` `v0.4.0`](08-pin-datastorekit-v0.4.0.md) | the DatastoreKit pin (**U10**, carrying **U3**; `c8570e8`) | Sonnet | ✍️ 2026-10-21 | ✅ 2026-10-21 (§5.21) | `1b1ca6d` | [`08-pin-datastorekit-v0.4.0.md`](../../.documents/dk-and-rpk-migration/08-pin-datastorekit-v0.4.0.md) |
| 09 | [Adopt `datastorekit`](09-adopt-datastorekit.md) | the DatastoreKit swap; **U5**; closes `[config-datastore-cannot-be-imported-before-the-layer]` | Opus | ✍️ 2026-10-21 | ✅ 2026-10-21 (§5.22) | `f4da58f` | [`09-adopt-datastorekit.md`](../../.documents/dk-and-rpk-migration/09-adopt-datastorekit.md) |
| 10 | [Port the inventory](10-port-the-inventory.md) | **U6**, **U8**; `inventory_spec`, `tools/inventory_report.py`; closes `[show-all-flag-unused]` | Opus | ✍️ 2026-10-21 | ✅ 2026-10-21 (§5.23) | `e2c7b22` | [`10-port-the-inventory.md`](../../.documents/dk-and-rpk-migration/10-port-the-inventory.md) |
| 10a | [Pin `datastorekit` `v0.5.0`](10a-pin-datastorekit-v0.5.0.md) | the DatastoreKit pin moved to `v0.5.0` (**U12**; `f47b9a2`) | Sonnet | ✍️ 2026-10-22 | ✅ 2026-10-22 (§5.26) | `80d99a7` | [`10a-pin-datastorekit-v0.5.0.md`](../../.documents/dk-and-rpk-migration/10a-pin-datastorekit-v0.5.0.md) |
| 10b | [Count the gradient value table](10b-count-the-gradient-value-table.md) | **U12**; `extra_values` on `GradientCoupledInstanton`; closes `[gci-value-table-outside-the-inventory]` | Opus | ✍️ 2026-10-22 | ✅ 2026-10-22 (§5.27) | this commit | [`10b-count-the-gradient-value-table.md`](../../.documents/dk-and-rpk-migration/10b-count-the-gradient-value-table.md) |
| 11 | [Rehearse through both packages (RH2)](11-rehearse-through-both-packages.md) | **RH2**, bitwise against RH1; **DatastoreKit G4** | Opus | ✍️ 2026-10-21; amended 2026-10-22 (U12: at 10b's tree, on `v0.5.0`) | ⬜ | — | — |
| 12 | Close the migration | `CLAUDE.md`, rules, documents, handover to P2, close | Sonnet | ⬜ | ⬜ | — | — |

**Legend.** ✍️ written · ⏸ held, with what it waits on · ⬜ not yet · ✅ landed.

**Held, by design (README §2.1).**
- **01–04** are written after the user's review of the plan. *Written 2026-10-12.*
- **01a** is written after 01's review, for U9. *Written 2026-10-12.* 02 waits on it.
- **05–07** are written after 02's review: RH0's reproducibility sets RH1's criterion. *Written
  2026-10-20 (§5.14):* RH0 is bitwise reproducible, so RH1 is held to bitwise equality.
- **08–11** are written after 07's review (`v0.4.0`, which 08 pins, is released). *Written
  2026-10-21 (§5.20).*
- **10a**, **10b** are written after 10's review and the ruling U12. *Written 2026-10-22 (§5.25).*
- **12** is written after 11's review.

Orchestrator notes are written one prompt at a time, in [`orchestrator/`](orchestrator/), just
before each dispatch:
- [`prompt-01.md`](orchestrator/prompt-01.md) — used for 01 (`b4088d1`).
- [`prompt-01a.md`](orchestrator/prompt-01a.md) — used for 01a (`37126a2`).
- [`prompt-02.md`](orchestrator/prompt-02.md) — used for 02 (`0ff3609`; revised for U11 in `9caeea3` and for the reader fix in `b218760`, §5.12).
- [`prompt-03.md`](orchestrator/prompt-03.md) — used for 03 (`b1ab501`).
- [`prompt-04.md`](orchestrator/prompt-04.md) — used for 04 (`9a7cb50`).
- [`prompt-05.md`](orchestrator/prompt-05.md) — used for 05 (`818f8fa`; one claim corrected by the agent, §5.17).
- [`prompt-06.md`](orchestrator/prompt-06.md) — used for 06 (`a8cb166`).
- [`prompt-07.md`](orchestrator/prompt-07.md) — used for 07 (`9214c9b`).
- [`prompt-08.md`](orchestrator/prompt-08.md) — used for 08 (`7ef06ad`).
- [`prompt-09.md`](orchestrator/prompt-09.md) — used for 09 (`597730f`).
- [`prompt-10.md`](orchestrator/prompt-10.md) — used for 10 (`62cdca5`).
- [`prompt-10a.md`](orchestrator/prompt-10a.md) — used for 10a (`3fd8778`).

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
| **W1** | 04 | `RayTools/` deleted | ✅ `git ls-tree` of the commit is empty; no `RayTools` directory in the tree (the ignored `__pycache__` removed with it) |
| **W2** | 04 | the 3 imports rewritten to `from raypoolkit import RayWorkPool` | ✅ `main.py:45`, `plot_GradientCoupledSolutions.py:100`, `plot_InstantonSolutions.py:72`; 159 imports of the drivers resolve by `ast`, no private `raypoolkit` name |
| **W3** | 04 | `_default_store_handler` dropped: 7 lines of `main.py` | ✅ one line modified (`:45`), six deleted (`:412`, `:499`, `:666`, `:826`, `:850`, `:1099` at `0c3d4b6`); the two compute sites that pass SI's own handlers (`:385`, `:720`) untouched |
| **W4** | 04 | no other pool site changed (P7) | ✅ the plot scripts' diff is one import line each; the script gives 16 calls, all `constructs` |
| **W5** | 04 | the prose naming the copy made true: `CLAUDE.md:95`, `ray-dispatch.md:99-106`, `FILE_MAP.md`, `INFRASTRUCTURE.md`, `architecture-summary.md` (P13) | ✅ `CLAUDE.md:101`, `ray-dispatch.md:101-105` (now `:101-112`), `FILE_MAP.md:31` and `:287`, `INFRASTRUCTURE.md:353`, `architecture-summary.md:27-28` and `:321`; the package's lines read at `v0.2.0`. Residue opened: `[pool-prose-stale-after-raypoolkit-adoption]` |

| **M1** | 05 | `config/datastore.py`: `factories` (30), `drop_groups` (5), `serial_batch_sizes` (29), moved verbatim with their imports | ✅ `config/datastore.py`: `factories` 30, `drop_groups` 5, `serial_batch_sizes` 29, `ast`-equal to the removed definitions; not formatted, so the blocks move verbatim |
| **M2** | 05 | the old layer imports them under its old names (`Datastore.py`, `ClientPool.py`); `_drop_order` and SI's fallback of 5 stay | ✅ both layer files import them under the old names; each diff is the removed definitions and imports plus one added line; lint: the one baseline `F401` (`CosmologicalParams`), no new finding; `_drop_order` and the fallback of 5 stay |
| **M3** | 05 | `config.sharding.vectorized_shard_key`; the 15 vectorized gets pass its mapping (P8) | ✅ `config.sharding.vectorized_shard_key`; 15 calls (`main.py` 10, plot script 3, `fetch.py` 2), one import line each; the `ast` test pins the 15 |
| **M4** | 05 | the four test stubs take the mapping (`test_plot_adapters_golden.py:1010`; `test_plot_extraction_golden.py:381`, `:450`, `:477`) | ✅ five lines, not four stubs (`test_plot_adapters_golden.py:1012`, `:1047`, `:1103`; `test_plot_extraction_golden.py:414`, `:467`); the stubs at `:381`, `:450`, `:477` unchanged |
| **M5** | 05 | `tests/test_config_datastore.py` (the data, captured literally; the layer reads it) and `tests/test_vectorized_shard_key.py` (the helper; the `ast` count of 15) | ✅ `tests/test_config_datastore.py` 7 tests, `tests/test_vectorized_shard_key.py` 3; the data is written from the capture, the layer's identity is asserted; breakages 1–5 caught |
| **M6** | 05 | `.documents/FILE_MAP.md`: the `Datastore.py` row, and a row for `config/datastore.py` (P13) | ✅ `FILE_MAP.md`: the `Datastore.py` row, a `config/datastore.py` row, and `config/sharding.py`'s row naming `vectorized_shard_key` |
| **I1** | 06 | `InflatonTrajectory`'s prune deletes its value rows first; the cascade map of `validate-on-startup.md` gains the row | ✅ `tables.get("InflatonTrajectoryValue")`, delete by `trajectory_serial` before the parent's, in the actor's one transaction; messages unchanged, no count line added; the map's row and one sentence on `owner_column` |
| **I2** | 06 | the hook parameter `prune` in all 12 hooks (P17), and in the examples of `validate-on-startup.md` and `datastore-factories.md` | ✅ 12 definitions and the 5 uses in bodies; the 5 rule lines (`validate-on-startup.md:38`, `:43`, `:83`; `datastore-factories.md:205`, `:209`); the 11 other `prune_unvalidated`s untouched (33 lines before, 11 after) |
| **I3** | 06 | `register()`: `owner_column: "trajectory_serial"` on the value table, `validated_column: "validated"` on the trajectory | ✅ one key and one comment line each; the schema of a two-shard store agrees with `05-temp-schema.json` and `02-reference-schema.json` |
| **I4** | 06 | `revalidate(serial, conn, table, tables)`, by `validate`'s rule as stored; its two premises checked against `store` and `object_store` | ✅ `N_end` NULL → `True`, else `True` iff ≥ 1 value row; writes the flag with `conn`, returns a Python `bool`, raises for a missing serial. Premises hold: `Datastore.py:478`, `:495-504`, `:509` (one transaction per store call); `InflatonTrajectory.py:208-211` (`N_end` NULL only on failure), `:215`, `:220-228` |
| **I5** | 06 | `tests/test_inflaton_trajectory_prune.py`, without Ray: the cascade, `revalidate`, `prune` by signature, the keys | ✅ 6 tests on a `tempfile` store of all 30 tables, rows written by the factories' own `build`/`store`/`validate`; the signature test counts 12 by each class's own `__dict__` |
| **I6** | 06 | an integration test: an unvalidated trajectory pruned at reopen on two shards, no orphan | ✅ SI's `ShardedPool` in two subprocesses (store, reopen with the prune), each its own `ray.init(address="local")`; both shards read with `sqlite3` `mode=ro` before and after; 3 orphans per shard with the cascade removed, none with it |
| **L1**–**L4** (RH1) | 07 | README §4.1 at 06's tree; bitwise equality with `02-reference.sqlite` and with `02-scalars-2.sqlite` / the readers' `before/` copy of `02-scalars.sqlite`, compared before the readers; `scalar_data.csv` `b0564eec…58a2`; L4 against RH0's pattern | ✅ L1–L3 hold; `resumed-a2` (second attempt, `S` = 12.0 s) left 8 validated and 1 unvalidated `FullInstanton`, `resumed-b` pruned the 1 and computed 2; **§4.3: all five comparisons `RESULT: equal`, exit 0, against RH0 and within RH1, dense and scalars-only**; both `scalar_data.csv` `b0564eec…58a2`; L4: `reference`'s and `scalars`' parsed records equal RH0's but for the provenance line |
| **V2** | 07 | `verification.md` §2 RH1; `out/07-*` | ✅ [`verification.md`](../../.documents/dk-and-rpk-migration/verification.md) §2; `out/07-*` (5 comparisons, schema snapshot, stage counts, readers' outputs) |
| **Z1** | 07 | the annotated tag `pre-datastorekit` on 07's commit (U7), not pushed | ✅ annotated, on 07's commit `0527480`; pushed by the user 2026-10-21 |
| **K4** | 08 | the `datastorekit` pin in `requirements.txt` | ✅ one line at `:16`, between `cycler==0.12.1` and `distlib==0.4.3`; 73 lines |
| **K5** | 08 | the venv installed from it; one distribution added | ✅ dry run and install each added `datastorekit-0.4.0` alone |
| **K6** | 08 | the proof: `c8570e849334…`, the tag's 21 modules, no `tests/`, not editable | ✅ freeze differs by one line; `pip check` clean; `direct_url.json` VCS at `c8570e84…`, `v0.4.0`, no `dir_info`; 21 of 21 modules byte-equal, no `tests/`; `raypoolkit` mtimes unchanged; import starts no Ray; `sharded_store --help` exits 0 |
| **K7** | 08 | on the installed package: U3's `timestamp`; the factory base; SI's 30 entries instantiate | ✅ run from `site-packages`; `timestamp` round-trips, `None` by default, read-only, keyword-only; `build` abstract; 30 of 30 entries instantiate (28 classes; 12 define all three hooks, 16 none, 0 some) |
| **A1** | 09 | the 7 layer modules deleted; the two `__init__.py` emptied (P6) | ✅ 2,546 lines in 7 modules deleted (`git rm`), their 9 ignored `.pyc` removed; `Datastore/__init__.py` and `Datastore/SQL/__init__.py` 0 bytes; DatastoreKit's script at the dangling commit: the 7 absent, 0 imports, 0 literals, 0 `import_module` |
| **A2** | 09 | the 48 layer imports rewritten by the module map | ✅ 47 statements by the module map (24 `SQLAFactoryBase`, 12 + 6 `DatastoreObject`, 4 `ShardedPool`, 1 `ProfileAgent`), the 48th (`test_compare_stores.py:944`'s fallback) removed; I6's subprocess script's import rewritten too |
| **A3** | 09 | each factory's diff its import line alone | ✅ by `ast`, the module path normalised: 42 of the 48 files of README §1.2 identical (the 22 factories, the 2 registries, 18 concept and compute-target modules); the 6 others are the drivers, `conftest.py` and the 2 tests §1.6 names |
| **A4** | 09 | the four pools take `factories=` and `serial_batch_sizes=`; no `drop_actions=`, no `inventory_config=` | ✅ `main.py`, both plot scripts and `live_pool`, by keyword from `config.datastore`; `main.py`'s `drop_tables=tables_to_drop(args.drop)`; every other argument unchanged; no driver imports `inventory_config`; pinned by an `ast` test |
| **A5** | 09 | **U5**: unclosed `--drop` groups refused before Ray, naming the groups to add | ✅ `config.datastore.tables_to_drop`, by `dependent_tables`; `main.py` refuses on stderr, exit 2, before `ray.init`; 10 of 31 sets closed, 21 refused, as measured; `tests/test_tables_to_drop.py` 9 |
| **A6** | 09 | the harness rebuilt; the named tests changed (charter, and §5.20's additions) | ✅ `live_pool` the package's pool; `test_grid_builder_integration.py` by `sqlite3` `mode=ro`; `test_config_datastore.py` (2 layer tests → 1 `ast` test); `test_inflaton_trajectory_prune.py` (I6 on the package's pool); `test_compare_stores.py`'s fallback gone; new: `test_tables_to_drop.py` 9, `test_main_refusals.py` 3, `test_datastorekit_timestamp.py` 1 (integration) |
| **A7** | 09 | `--inventory` refuses before Ray (P11); the prose this commit makes false (P13) | ✅ exit 2 before `ray.init`, nothing created; the 5 helpers, 2 printers and 4 `pool.inventory` calls deleted; `CLAUDE.md`, `pool-read-apis.md`, `datastore-factories.md`, the two shard-key notes, `FILE_MAP.md`, `config/datastore.py` corrected; what stays stale listed for 12 |
| **A8** | 09 | `[config-datastore-cannot-be-imported-before-the-layer]` closed | ✅ §4; `import config.datastore` alone exits 0 in a fresh process (30 entries on the package's base, no Ray) |
| **A9** | 09 | the verification: the script, the schema, the suites with `slow`, acceptance 4 (the package's replicated prune) and 5 (U3 through the package) | ✅ schema: "the schemas agree" with the gate's and `07-reference-schema.json` (`out/09-temp-schema.json`); default 707 (706 passed, 1 skipped), integration 63 (62 passed, 1 skipped), `slow` 69 passed (S1's); I6 passes on the package's prune; U3's test passes; six breakages caught |
| **N1** | 10 | `inventory_spec()` on every covered factory and every class a spec depends on | ✅ 22 definitions in 22 modules serve 24 entries; each the identity its `build` matches (the results note's table, pinned by `tests/test_inventory_specs.py`); four polymorphic parents by SI's registries, two nullable (`CompactionFunction`'s instantons), none `cross_shard`, `version` no parent |
| **N2** | 10 | `tools/inventory_report.py`, at least what today's report shows (P18), every problem in full | ✅ `format_inventory_report(inventory, db_name, verbose=False) -> str`; reads nothing but the registry's column types; today's fields kept but the per-group timestamps (one range per class) and the serial labels (physical labels now); `tests/test_inventory_report.py` 10 |
| **N3** | 10 | `main.py --inventory` by `read_inventory`, before Ray; `--show-all` is `verbose` | ✅ before `ray.init`; exit 0 with the report, 1 on the reader's `RuntimeError` (an absent store, or one the package refuses), 2 with `--drop`; creates and changes nothing; `--show-all`'s help made true |
| **N4** | 10 | the 17 `inventory()` hooks and `inventory_config` deleted; U5 re-checked against the specs | ✅ 17 hooks and the 11 `datetime` imports only they used; `inventory_config`, `_instanton_merge` and their comment; U5: 31 of 31 sets unmoved, decisions, messages and `dependent_tables` alike (10 closed) |
| **N5** | 10 | **U8**: every registered class covered, read through, or excluded with a reason; the GCI table left out opened as an issue | ✅ 30 entries: 24 specs, 5 read through (`values`), 1 excluded (`GradientCoupledInstantonValue`); `[gci-value-table-outside-the-inventory]` opened (§3) |
| **N6** | 10 | the prose this commit makes false | ✅ `pool-read-apis.md` §1; `FILE_MAP.md` (`config/sharding.py`'s row, the `ShardedPool` row, a row for `tools/inventory_report.py`); `tests/test_tables_to_drop.py`'s docstring; a spec rule for every new factory, and the `INFRASTRUCTURE.md` and `architecture-summary.md` lines, left for 12 |
| **K8** | 10a | the `datastorekit` pin moved to `v0.5.0` in `requirements.txt` | ✅ `requirements.txt:16` replaced in place (`@v0.4.0` to `@v0.5.0`); 73 lines |
| **K9** | 10a | the venv installed from it; `datastorekit` replaced, nothing else | ✅ dry run `Would install datastorekit-0.5.0` alone; the install uninstalled 0.4.0 and installed 0.5.0, nothing else; `pip freeze` differs by the one line; `pip check` clean; `raypoolkit`'s 16 files keep their mtimes |
| **K10** | 10a | the proof: `f47b9a255e9a…`, the tag's 21 modules (two differ from `v0.4.0`'s), not editable | ✅ `direct_url.json` VCS at `f47b9a25…`, requested `v0.5.0`, no `dir_info`; 21 of 21 modules equal the tag's; exactly `store_inventory.py` and `store_fingerprint.py` differ from the saved `v0.4.0` ones; no `tests/`; no 0.4.0 dist-info; import starts no Ray |
| **K11** | 10a | on the installed package: `extra_values`, `extra_value_counts`, the refusal, `ENCODING_FORMAT` 1; U5 unmoved; the suites at 10's counts | ✅ from `site-packages`; 24 classes in 10's order; the refusal names the class and the table; `tests/test_tables_to_drop.py` 9 passed; suites 730 (729 passed, 1 skipped) and 67 (66 passed, 1 skipped) |
| **X1** | 10b | `GradientCoupledInstanton`'s spec declares `extra_values={"GradientCoupledInstantonValue": "instanton_serial"}` | ✅ one keyword beside `values=` (`Datastore/SQL/ObjectFactories/GradientCoupledInstanton.py:181`) and the spec's comment made true (`:148-155`); nothing else in the factory changes |
| **X2** | 10b | the spec, column and coverage tests see it: 24 specs, 6 read through, 0 excluded | ✅ `EXPECTED_SPECS` carries `extra_values` for all 24 (`{}` for 23); the column test checks the table, its column and its foreign key, and that it met every extra table; `_slot_tables` reads a mapping's keys; coverage places the 30 as 24 / 6 / 0, `EXCLUDED` empty; the stale-exclusion case takes the class out of `READ_THROUGH`; breakages 1, 2, 3 and 5 caught |
| **X3** | 10b | the report prints each further table's count | ✅ `\| 5 value rows; 3 GradientCoupledInstantonValue rows` on each record line and `…; 10 value rows; 3 GradientCoupledInstantonValue rows; …` in the class summary, 0 printed as 0; a class with none prints as 10's; `tests/test_inventory_report.py` 10 → 12; breakage 4 caught |
| **X4** | 10b | the integration store's three gradient records, with and without full values, read back with their counts and no problem | ✅ a third gradient instanton at δN★ 1.5, stored by `set_store_full_values(False)` with `_values` populated; read back `(True, 5, {…: 3})`, `(True, 5, {…: 0})`, `(True, 0, {…: 0})`, `problems == ()`; `test_inventory_store.py` 4, in place. Only `GradientCoupledInstanton`'s fingerprint digest moves (1 of 24); U5 unmoved (31 of 31) |
| **X5** | 10b | `[gci-value-table-outside-the-inventory]` closed | ✅ §4; `.documents/OPEN-ISSUES.md` §7, 59 open, 29 closed |
| **L1**–**L4** (RH2) | 11 | README §4.1 at 10's tree, through both packages; bitwise equality with RH1's stores, compared before the readers; `scalar_data.csv` `b0564eec…58a2`; `--inventory` with no problem; L4 against RH1 | ⬜ |
| **V3** | 11 | `verification.md` §3 RH2; `out/11-*` | ⬜ |
| **H1** | 11 | `shard_key_audit` on each store; a `sharded_store copy` read and compared, then `delete_store` | ⬜ |

Items of 12 are added when it is written.

The measurement the plan was written against is [`measure/out/`](measure/out/). It holds:
- both packages' scripts at `7bb3efd`, each equal to its checklist's appendix byte for byte;
- the suites' counts (default 631 of 761, 630 passed and 1 skipped; integration 61, 60 passed and
  1 skipped);
- the venv's `pip freeze` (README §0.2).

## 2. The gates

| Gate | Holds when | Prompt | State |
|---|---|---|---|
| RH0 | the start tree builds the grid, resumes it, builds it scalars-only, and its readers run (README §4.1); its reproducibility is measured (§4.3) | 02 | ✅ 2026-10-20 (§5.13): bitwise reproducible, dense and scalars-only |
| RayPoolKit G4 | `RayTools/` is gone; 0 imports of it and of `_default_store_handler`; the pin is installed; the suites pass; all 16 sites construct (RayPoolKit checklist item 8) | 04 (RH1, 07, adds the run under real Ray) | ✅ 2026-10-20 (§5.16), items 1–5: `git ls-tree` empty; 0 imports, 0 private names, 0 `import_module` (2 string literals, both dated module docstrings, unedited); the pin installed (03); 680 and 61; 16 calls, all `constructs`. Item 6 (the record on RayPoolKit's board) is 12's draft (P14); RH1 (07) adds the run under real Ray. **2026-10-21 (§5.19): RH1 ran the grid under real Ray through the package**: every pool built, completed and printed its lines as the copy did (`stage_counts.py` parsed them unchanged), and the stores equal RH0's bit for bit |
| RH1 | 06's tree equals RH0 bit for bit, timings and timestamps aside (§5.13), dense and scalars-only; `pre-datastorekit` tagged | 07 | ✅ 2026-10-21 (§5.19): five comparisons `RESULT: equal`, exit 0; schema RH0's; `pre-datastorekit` tagged on 07's commit `0527480`, not pushed |
| DatastoreKit `v0.2.3` | tagged on DatastoreKit's remote, with `store`, `validate` and `validate_on_startup` defaulted | — (carried into `v0.3.0`) | ✅ **released** 2026-10-11 for CPBH: tag object `8dac562`, commit `0de2b16`. Checked on the remote at planning |
| DatastoreKit `v0.3.0` | tagged on DatastoreKit's remote, its `DatastoreObject` taking and exposing `timestamp` (U3; made in DatastoreKit from the brief, not here) | — (carried into `v0.4.0`) | ✅ **released** 2026-10-12 by DatastoreKit's `object-timestamp` campaign: tag object `bf0a3b2`, commit `2f5417e`; checked on the remote and by `git show` of `object.py` (README §0.4) |
| DatastoreKit `v0.4.0` | tagged on DatastoreKit's remote, carrying `v0.3.0` unchanged (U10) | — (08 pins it) | ✅ **released** 2026-10-14 by DatastoreKit's `fingerprint` campaign: tag object `8e7c1d7`, commit `c8570e8`; checked on the remote 2026-10-19, and by `git diff --stat v0.3.0 v0.4.0`: `store_fingerprint.py`, its tests and golden data, the version, nothing else (README §0.5) |
| DatastoreKit G4 | the 9 layer files are gone (two emptied, P6), the pin (`v0.3.0` or later; SI `v0.5.0`, U12) is installed, the default and integration suites pass, and a small grid rebuilt through the package (RH2) equals RH1 by value | 09, 10, 10a, 10b, 11 | ⬜ |

Recording each gate on its package's own extraction board is a commit in that repository, not
here (README P14).

## 3. Active and unresolved issues

Opened at planning, 2026-10-11, unless the row says otherwise.

| Issue | What | Owner |
|---|---|---|
| `[plot-scripts-stale-version-label]` | Both plot scripts open **read-write** under `plotting/provenance.py:18`'s `"2026.3.0"`, while `main.py:49` writes `"2026.6.1"`. So each plot run adds a `version` row to the store it reads, and the figure footers say `v2026.3.0`. Read-only plot pools are the goal (README P9, P10) | unowned; P2 when it bumps the label |
| `[redshift-registered-in-neither-table-list]` | `redshift` is registered (`Datastore/SQL/Datastore.py:99`) and has a batch size, but is in neither `replicated_tables` nor `sharded_tables`, and no SI code uses it: a ChamPBH leftover. `IntegrationSolver` is registered and replicated, but likewise unwritten by any driver (README P12). *Found at 10 (§5.23), not acted on:* `sqla_redshift_factory.build`'s query for `z = 0` reads `sqla.func.abs((table.c.z - z) < DEFAULT_REDSHIFT_PRECISION)`, the comparison inside the `abs`, so it matches every row with `z` below the precision (negative ones too), and `one_or_none()` raises when two do; ChamPBH's inherited factory has the same line. Unreachable while nothing writes `redshift`; the spec (`leaves=("z",)`) reads the stored value, not the lookup | unowned |
| `[test-counts-stale-in-claude-md]` | `CLAUDE.md:21` and `.claude/rules/test-selection.md:10`, `:26` say "464 of 571"; at `7bb3efd` the default run selects 631 of 761 | 12 |
| `[unified-pipeline-stores-null-instanton-labels]` | *Opened 2026-10-12 at 01's review, from its Observation 2.* The unified pipeline (`--no-store-values`) constructs `FullInstanton` and `SlowRollInstanton` with no label (`ComputeTargets/pipeline.py:288-298`, `:304-314`), so they are stored with `label` NULL, where the per-stage queues store the factory's default (`Datastore/SQL/ObjectFactories/FullInstanton.py:149-155`, `SlowRollInstanton.py:148-154`). No science value differs and no reader fails, but the provenance footers read `label` (`plotting/provenance.py:46`), so a scalars-only store's figures lack it. `tools/compare_stores.py` treats the two columns as bookkeeping for this reason | unowned |
| `[gci-picard-inner-fails-on-rehearsal-grid]` | *Opened 2026-10-20 at 02's first attempt (§5.12).* At the rehearsal grid (`quadratic-minimal.yaml`, `m = 10⁻⁵ M_P`, `n = 5`, `α = 0.01`, no wall-clock budget) none of the four `GradientCoupledInstanton` solves of the first wave (`δN★` = 0.1, 0.4222, 0.7444, 1.711) finished in 5 h 24 min at full CPU. Each worker's log shows only `Picard inner failed at lambda=…`, 85–105 times, with λ halved after each failure and the sign alternating between outer attempts. July's 315 s a solve at `δN★ = 1.0` (`.documents/gradient-coupled-instanton/24-phase-a-deep-dive.md:43`) was measured at an older tree. Not investigated here: the gradient code is P3's, and the rehearsals no longer build it (U11). The workers' logs are kept in the orchestrator's scratchpad of 2026-10-20 only; the first attempt's store and log are under `$REHEARSAL_ROOT/02-attempt-1-aborted/` | P3 |
| `[pool-prose-stale-after-raypoolkit-adoption]` | *Opened 2026-10-20 at 04 (§5.16).* Two statements 04 leaves, both outside its §5 list: (1) `ComputeTargets/GradientCoupledInstanton/picard.py:450-456`, a July comment (`b5a3a9f`), says `RayTools/RayWorkPool.py` is protected infrastructure (`CLAUDE.md`) and has no per-task timeout hook; the path is gone and the pool is no longer SI's to protect, though the substance holds (no `timeout` or `cancel` in `raypoolkit/RayWorkPool.py` at `v0.2.0`); a `ComputeTargets/` edit would also widen the suites to the `slow` block. (2) The constructor sketches at `.documents/INFRASTRUCTURE.md:357-373` and `.documents/architecture-summary.md:328-344` give `create_batch_size=10`, `process_batch_size=10`, `max_task_queue=50` as defaults; the defaults of the copy and of the package are both 5, 1 and 200 (`DEFAULT_*`, `:26-29`). Wrong before 04, not made false by it | 12 |

## 4. Resolved issues

| Issue | Resolved | How |
|---|---|---|
| `[ray-address-auto-attaches-to-foreign-cluster]` | 2026-10-12 (opened and closed the same day, §5.9, §5.10) | Every project's drivers defaulted to `--ray-address auto`, which attaches to any running cluster once the clusters are isolated (`ray_current_cluster` is no longer in `/tmp/ray`). The brief's §3 "Address it explicitly" now covers every run that takes the lock and forbids leaving a driver at `auto`; §5 asks SGK to pass `local` to its long builds. The user ruled SI's default: `--ray-address` is now required (`config/argument_parser.py`), for `main.py` and both plot scripts; `CLAUDE.md`'s run instructions say so. ChamPBH's and SGK's defaults are theirs to change |
| `[inflaton-trajectory-prune-orphans-value-rows]` | 2026-10-20 (06, §5.18; opened at planning) | `sqla_InflatonTrajectory_factory.validate_on_startup` now deletes the unvalidated trajectories' `InflatonTrajectoryValue` rows, by `trajectory_serial`, before the trajectories, in the same transaction (`tables.get`, the pattern of `FullInstanton`'s hook); `.claude/rules/validate-on-startup.md`'s cascade map has the row. For DatastoreKit's prune, the value table declares `owner_column: "trajectory_serial"`. Shown by `tests/test_inflaton_trajectory_prune.py`: on a store the factory wrote, the prune deletes the trajectory and its 3 value rows and no other table loses a row; through SI's `ShardedPool` on two shards, a pruning reopen leaves no orphan, where without the cascade it left 3 on each shard |
| `[config-datastore-cannot-be-imported-before-the-layer]` | 2026-10-21 (09, §5.22; opened at 05) | 09 deleted SI's layer and emptied `Datastore/__init__.py` and `Datastore/SQL/__init__.py` (P6), so nothing imports the layer and the cycle through it is gone. `import config.datastore` alone, in a fresh process, exits 0: 30 entries, every one an instance of the package's `SQLAFactoryBase`, `ray.is_initialized()` `False` (run with the root put on `sys.path` by `PYTHONPATH`, and by `-I` with the root inserted by the code, since `-I` ignores `PYTHONPATH`). `tests/test_config_datastore.py`'s two `import_module` calls of the layer are gone and its subprocess test imports `config.datastore` alone; `tests/test_compare_stores.py`'s `_registry()` imports it directly, its `ImportError` fallback gone |
| `[show-all-flag-unused]` | 2026-10-21 (10, §5.23; opened at planning) | `main.py --inventory` passes `verbose=args.show_all` to `tools/inventory_report.py`'s `format_inventory_report`: without it a list of more than 20 values shows its first and last 10, and a group of more than 10 records its first and last 5, as today's report did; with it nothing is truncated. The flag's help says so (`config/argument_parser.py`). Shown by `tests/test_inventory_report.py` (truncation and `verbose`) and `tests/test_inventory_store.py` (`main.py --inventory --show-all` prints the verbose report) |
| `[gci-value-table-outside-the-inventory]` | 2026-10-22 (10b, §5.27; opened at 10, §5.23) | DatastoreKit `v0.5.0` (pinned by 10a, U12) gives a spec further value tables, `extra_values`. `GradientCoupledInstanton`'s spec now declares `extra_values={"GradientCoupledInstantonValue": "instanton_serial"}` beside `values=("GradientCoupledInstantonProfile", "parent_serial")`, so `read_inventory` counts the table per record into `extra_value_counts` (0 for a row stored without full values) and names its orphans, and a fingerprint taken through it sees it. `tests/test_inventory_specs.py` reads the table through its owner's `extra_values` slot: 24 specs, 6 read through, none excluded; `tools/inventory_report.py` prints the count by the table's name. Shown by `tests/test_inventory_store.py`: a two-shard store with a gradient instanton with full values, one stored without, and a failed one reads back `3`, `0` and `0` rows, with no named problem |

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

- **Landed:** `5396a3d`, results note
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
- **Rollback:** `git revert` of `5396a3d` **plus** `./venv/bin/pip uninstall -y raypoolkit`
  (README §4.4). The venv is outside git, so the revert alone leaves the package installed (inert
  until 04 imports it).
- **Deviations:** the board section number, and the suites' commands, both as the orchestrator's brief
  corrected; none unintended.

**Orchestrator review of prompt 03 (2026-10-20)**, by orchestrator note
[`prompt-03.md`](orchestrator/prompt-03.md), at `5396a3d`. All ten checks pass, read from the venv
itself. Residue is fixed in this follow-up; nothing is opened.
- **(1) Scope.** 3 files: `requirements.txt`, the results note and the board. One commit of the
  agent's on `b1ab501`; `git status` clean. No other file in either repository is newer than the
  note.
- **(2) K1.** One added line at `:58`, between `ray==2.55.1` and `referencing==0.37.0`; the file
  has 72 lines.
- **(3) The freeze.** `pip freeze` now differs from the **committed**
  `measure/out/7bb3efd-pip-freeze.txt` by exactly
  `raypoolkit @ git+https://github.com/ds283/RayPoolKit@eaef0ce60e2fc354bb32f0ad576010e6a83c1976`
  (`64a65`), and from the orchestrator's pre-dispatch copy by the same line. `pip check` clean; pip
  still 26.0.1.
- **(4) The origin.** `direct_url.json`, read in site-packages: `url`
  `https://github.com/ds283/RayPoolKit`, `vcs` `git`, `commit_id` `eaef0ce6…`,
  `requested_revision` `v0.2.0`, no `dir_info`. `INSTALLER` is `pip`. No `__editable__` or
  `.egg-link`; the only `.pth` is `_virtualenv.pth`, which does not name RayPoolKit.
- **(5) The files.** The tag's archive, extracted afresh into the scratchpad: the same four `.py`
  files, each identical under `cmp`; no `tests/`; nothing else. The dist-info's `RECORD` lists
  the four modules and their `.pyc` files under `raypoolkit/`, and every hash it gives (the four
  modules and the dist-info files) matches, with sizes.
- **(6) Import and helper.** The import one-liner prints `False`. The helper gives `0.2.0`, the
  URL, commit and revision, `editable: False`, and `datastorekit` `None`; the line is
  `>> packages: datastorekit not installed; raypoolkit 0.2.0 (https://github.com/ds283/RayPoolKit@eaef0ce60e2fc354bb32f0ad576010e6a83c1976, requested v0.2.0)`.
  `pip show` gives `Requires: ray`.
- **(7) The pip account.** The dry run shows `Would install raypoolkit-0.2.0` alone and the install
  `Successfully installed raypoolkit-0.2.0` alone; the `Resolved … 4e7eb153…` line is quoted and
  named as the tag object. It agrees with the orchestrator's own dry run before dispatch.
- **(8) Hygiene.** RayPoolKit's working tree clean, `HEAD` still `17029d9`. The 17 store files in
  the tree and all 607 entries under `~/ScienceData/` have their pre-dispatch mtimes and sizes. No
  Ray process; the lock free. No scratch file in either repository.
- **(9) The suites**, re-run by the orchestrator at `5396a3d` (load 9.1): default 680 (679 passed,
  1 skipped), 24.6 s; integration 61 (60 passed, 1 skipped), 11.6 s. The agent's agree.
- **(10) The records.** The results note has README §5.1's sections and every §2 check's command
  and output; the board has the §1 row, K1–K3 and §5.15 with the rollback.
  - *Residue, fixed here:* "this commit" → `5396a3d` (board ×3, results note ×3); the header's
    "awaiting review" reworded; this note added to the list of orchestrator notes; the campaign's
    line in `.prompts/INDEX.md`.
- **Correction to the note.** Its §0 says the archive holds 9 `.py` files under `tests/` (carried
  from ChamPBH's note). It holds 10, `tests/__init__.py` included, as the results note says. Nothing
  turned on the figure.
- **Deviations D1–D2 are accepted.** Both are the note's corrections.
- **Handed to 04's note.**
  - The provenance line above is what every driver now prints; 07 expects it in every RH1 log.
  - `raypoolkit` imports cleanly with no Ray started; nothing imports it yet.
  - 04's suites start from 680 and 61.

### 5.16 After prompt 04 (2026-10-20)

- **Landed:** `ef13445`, results note
  [`04-adopt-raypoolkit.md`](../../.documents/dk-and-rpk-migration/04-adopt-raypoolkit.md).
  **COMPLETE:** W1–W5 hold; **RayPoolKit G4 holds** by its checklist item 8, items 1–5. (The prompt
  names this section §5.8; that number is taken, and the board ran to §5.15.)
- **W1.** `RayTools/RayWorkPool.py` and `RayTools/__init__.py` are deleted with `git rm`; the ignored
  `RayTools/__pycache__/` and the empty directory were then removed, so that no `RayTools`
  directory is left. The copy's import of `Datastore.SQL.ShardedPool` goes with it.
- **W2, W3, W4.** `main.py:45`, `plot_GradientCoupledSolutions.py:100` and
  `plot_InstantonSolutions.py:72` import `RayWorkPool` from `raypoolkit`. `main.py` loses seven
  lines' worth of `_default_store_handler`: the import's second name, `_run_instanton_queue`'s
  parameter (`:412`) and its forward (`:499`), the three callers' arguments (`:666`, `:826`, `:850`)
  and the construction's (`:1099`). No other pool site moved.
- **The measure** (RayPoolKit's script, at a throwaway commit of the staged tree on no branch):
  0 imports, 0 private names, 0 `import_module` calls, 16 calls, `constructs` 16, `RayTools/`
  empty. 2 string literals remain: the module docstrings 01 added to `stage_counts.py` and
  `tests/test_rehearsal_stage_counts.py`, dated statements, unedited. The five flags (four calls)
  are non-literal sizes and are checked by hand in the results note.
- **W5.** `CLAUDE.md:101`; `ray-dispatch.md` (the rule's three behaviours at the package's lines
  at `v0.2.0`: `:385`, `:424-426`, `:471`); `FILE_MAP.md:31` (a row naming the package) and `:287`
  (the row deleted); `INFRASTRUCTURE.md:353`; `architecture-summary.md:27-28` and `:321`.
- **Opened:** `[pool-prose-stale-after-raypoolkit-adoption]` (§3, owner 12; `OPEN-ISSUES.md` 60 to
  61).
- **Suites:** 680 (679 passed, 1 skipped) and 61 (60 passed, 1 skipped), as at 03. No Ray was
  started by the agent; no driver ran; no store was opened. The run under real Ray is 07's (RH1).
- **Rollback:** `git revert` of `ef13445`. The venv is untouched (`raypoolkit` stays installed,
  inert once nothing imports it).
- **Deviations:** the board section number, the suites' commands, the 2 docstring literals and the
  `picard.py` comment (not stops), as the orchestrator's brief corrected; see the results note.

**Orchestrator review of prompt 04 (2026-10-20)**, by orchestrator note
[`prompt-04.md`](orchestrator/prompt-04.md), at `ef13445`. All eleven checks pass. Residue is fixed
in this follow-up; nothing more is opened.
- **(1) Scope.** 13 files: the two deletions, the three drivers, `CLAUDE.md`, `ray-dispatch.md`,
  `FILE_MAP.md`, `INFRASTRUCTURE.md`, `architecture-summary.md`, `OPEN-ISSUES.md`, the results note
  and the board. One commit of the agent's on `9a7cb50`; `git status` clean; `ls RayTools` fails; no
  leftover branch. The stray `main.py-e` the agent's D-list names is gone, and no file of either
  repository outside the commit is newer than the note.
- **(2) The diff.** `git ls-tree ef13445 RayTools` is empty. The plot scripts change one line each
  (`:100`, `:72`); `main.py` the import at `:45` and six deletions at `:412`, `:499`, `:666`, `:826`,
  `:850`, `:1099` (`0c3d4b6`'s numbers), nothing else. No other line of a `RayWorkPool(` call moved.
- **(3) The script at the real commit**, run by the orchestrator at `--commit ef13445`: 0 imports,
  0 private names, 2 string literals (the two docstrings), 0 `import_module` calls, 16 calls,
  `constructs` 16, 5 flags on 4 calls. Against the orchestrator's pre-dispatch throwaway `bc04d68`
  only the header, `Files:` (418 → 420: the results note and this note) and the non-`.py` lines
  (256 → 387, the documents and records) differ; every call row is equal. The verdicts equal the
  agent's throwaway measure.
- **(4) Imports.** The results note's `import_check.py`, extracted from the note (byte-equal to the
  agent's scratch copy) and re-run with `python -I`: 159 imports in 3 drivers, 0 unresolved, 0
  private `raypoolkit` names, `raypoolkit` from the venv's `site-packages`, `ray.is_initialized()`
  `False`. `py_compile` of the three drivers succeeds. `w3_check.py` reads its base as `HEAD`, so
  after the commit it must be pointed at `9a7cb50`; so pointed, it passes: 12 `None` sites, SI's own
  handlers at `:385` and `:717`, absent at `:493` and `:1089`, and `_run_instanton_queue`'s
  parameters those of `9a7cb50` less `store_handler`.
- **(5) Breakages**, replayed in `bash` from the note's diffs; each passes `git apply --check` and
  then `-R --check`, and the tree was clean after each.
  - 1 fails the import check on `main.py:45` (`No module named 'RayTools'`). At an orchestrator
    throwaway commit (`b760ea6`, from a copy of the index) the script reports 1 import.
  - 2 fails it on `plot_InstantonSolutions.py:72` (`'RayWorkPoool' is not an attribute`).
  - 3 resolves, and is caught by the private-name count (1, `main.py:46`) and by `git grep`; the
    script's verdict is the note's (`dd64b29`: 0 imports, 0 private names).
  - 4, `--block raypoolkit`: three failures, exit 1.
- **(6) The venv.** `pip freeze` equals the pre-dispatch copy; `pip check` clean.
- **(7) W5, line by line.** `CLAUDE.md` changes `:101` alone, to `Datastore/SQL/ShardedPool.py`.
  `ray-dispatch.md` changes only within the section (`:101-112` now): it names
  `raypoolkit.RayWorkPool` and its pin, and cites `:385` (`if obj.available:`), `:424-426` (the
  compute handler, default `obj.compute(**kwargs)` at `:75-76`) and `:471` (the store handler,
  default `obj.store()` at `:79-80`; persist at `:481`), each as the tag reads; the argument is
  unchanged. `FILE_MAP.md:31` names the package; `:287` is deleted (D-list, accepted).
  `INFRASTRUCTURE.md:353` and `architecture-summary.md:321` name the package and its pin;
  `architecture-summary.md:27-28` are a parenthetical layout line (accepted, as ChamPBH's). Nothing
  claims a feature the package lacks.
- **(8) The note's measurements.** The re-measure's account matches §0 of the note (+2 / +1; the
  docstrings), its `Files:` 421 and non-`.py` 292 being the note's own commit's. The agent's
  throwaway `db29b7f` has parent `9a7cb50`, and `git diff --name-only db29b7f ef13445` lists only
  `OPEN-ISSUES.md`, the results note and the board, so its code is the commit's.
- **(9) Hygiene.** RayPoolKit clean, `HEAD` `17029d9`. The 17 store files and all 607 entries under
  `~/ScienceData/` have their pre-dispatch mtimes and sizes. No Ray process; the lock free. No
  scratch file in either repository.
- **(10) The suites**, re-run by the orchestrator at `ef13445`: default 680 (679 passed, 1
  skipped), 61.3 s, load 7–14; integration 61 (60 passed, 1 skipped), 27.5 s. The agent's agree.
  This is the first tree at which the plot-driver tests import `raypoolkit`.
- **(11) The records.** The results note has README §5.1's sections, every check's command and
  output, and the G4 text for 12; the board has the §1 row, W1–W5, the G4 row and §5.16 with the
  rollback; the §3 issue has its index row, count and date.
  - *Residue, fixed here:* "this commit" → `ef13445` (board ×3, results note ×6); the G4 row now
    gives the 2 docstring literals and 0 private names; the header's "landed" reads "landed and
    reviewed"; this note added to the list of orchestrator notes; the campaign's line in
    `.prompts/INDEX.md`, whose count of open rows is corrected from 6 to 8 (it missed
    `[gci-picard-inner-fails-on-rehearsal-grid]`, opened at 02, as well as 04's).
- **The twelve deviations are accepted** (the results note's item 13 says none is drift). Six are
  the note's corrections; five are choices it allowed (the suites' flags, the `FILE_MAP.md:287`
  deletion, the layout line, imports in place, the import check's namespace rule). Item 11, the
  stray `main.py-e` from BSD `sed`, is a slip rather than a choice, but it was deleted before staging
  and nothing of it is in the commit.
- **Handed on to 05.**
  - The pool is the package's; the 16 call sites are at the throwaway's lines (`main.py:223` …
    `:1089`; compute sites `:385`, `:493`, `:717`, `:1089`), and 04 moved none but by deletion.
  - RH1 (07) is the first run of `raypoolkit` under real Ray, held to bitwise equality with RH0.
  - The suites start from 680 and 61.

### 5.17 After prompt 05 (2026-10-20)

- **Landed:** `875cf41`, results note
  [`05-move-si-data-out-of-the-layer.md`](../../.documents/dk-and-rpk-migration/05-move-si-data-out-of-the-layer.md).
  **COMPLETE:** M1–M6 hold; no stop condition of the prompt's §4 was met. (The prompt does not name this section; it is
  the next free number after §5.16.)
- **M1, M2.** `config/datastore.py` holds `factories` (30, in order), `drop_groups` (5) and `serial_batch_sizes` (29, `redshift`
  and `temperature` included). The three literals are `ast`-equal to the definitions removed from the layer, and every removed
  line but the three binding lines is verbatim in the new file. `Datastore/SQL/Datastore.py` loses 101 lines and gains one
  (`from config.datastore import factories as _factories, drop_groups as _drop_actions`); `ClientPool.py` loses 32 and gains one.
  `_drop_order`, SI's fallback of 5, `register_factories(_factories)` and the method `_drop_actions` are unchanged. The lint
  (`F401,F811,F821`) is the one baseline finding before and after, `CosmologicalParams` unused (`Datastore.py:35`, now `:29`), which
  stays.
- **The data, captured** (the gate's `HEAD`, from the layer): 30 registry entries with the four quantity entries' held classes,
  five drop groups, `_drop_order`, 29 sizes. `tests/test_config_datastore.py` is written from that output literally.
- **M3, M4.** `config.sharding.vectorized_shard_key`; the 15 calls pass `vectorized_shard_key(<key>)`; an `ast` test finds 15.
  M4 was five test lines (one stub's lookup, four assertions), as the orchestrator's brief measured.
- **§2.1.3 (for 09).** Registered with no size: `version`, `InflatonTrajectoryValue`; a size and no table: `temperature`. No table
  leases a serial under SI's fallback of 5 (not even `version`, which the lease guard excludes). Three tables carry a size of 500
  and register `"serial": False` (`FullInstantonValue`, `SlowRollInstantonValue`, `GradientCoupledInstantonValue`), so their sizes
  are never read. All move verbatim.
- **The schema** of a store built at the staged tree with SI's `ShardedPool` (two shards, nothing stored) agrees with RH0's
  `reference`: `RESULT: the schemas agree`, exit 0. The snapshot is `out/05-temp-schema.json`.
- **The import cycle.** A fresh `import config.datastore` fails; imported after any `Datastore.SQL.*` module it works. Measured
  in `python -I` processes; bare `import Datastore` and `import plotting.fetch` do not load the layer and do not serve (a refinement of
  the brief). Opened: `[config-datastore-cannot-be-imported-before-the-layer]` (§3, owner 09; `OPEN-ISSUES.md` 61 to 62).
- **Breakages** (README §5 rule 8), all caught and recorded as diffs: a vectorized get on the bare key (the `ast` test, naming
  `plotting/fetch.py:167`); a batch size 500 to 400 (two tests, one naming `FullInstantonValue`); `inflaton_mass` given `phi_value`
  (the registry test); the layer given a copy of the registry (the identity test alone, the data tests passing); a stub's lookup on
  the bare key (`TypeError: unhashable type: 'dict'`, three tests).
- **Suites:** 690 (689 passed, 1 skipped) and 61 (60 passed, 1 skipped): 04's 680 plus the 10 new tests, and 04's 61. The `slow`
  block is not run (the diff touches none of its paths). No driver ran; the only Ray was the schema build's private instance and
  the integration suite's.
- **Rollback:** `git revert` of `875cf41`. The venv is untouched.
- **Deviations:** the import cycle (structurally required, not a stop), the filesystem walk and subprocess forms the brief allowed,
  the unformatted new module, three extra tests, the long lines; see the results note. None is drift.

**Orchestrator review of prompt 05 (2026-10-20)**, by orchestrator note
[`prompt-05.md`](orchestrator/prompt-05.md), at `875cf41`. All twelve checks pass. Residue is fixed in `5dbcd22` (a test
docstring) and in this follow-up (records); nothing more is opened.
- **(1) Scope.** 16 files, exactly the prompt's §5 list and `OPEN-ISSUES.md`. One commit of the agent's on `818f8fa`, made
  once (the reflog shows no amend); `git status` clean; no untracked file; no leftover branch.
- **(2) The layer.** By `ast` against `818f8fa`: every non-import statement of `Datastore.py` and `ClientPool.py` dumps
  identically once the three definitions are removed. `Datastore.py` loses 25 import statements and gains the one
  `from config.datastore import …`; it keeps `ClientPool`, `CosmologicalParams`, `base`, `ProfileAgent` and `utilities`.
  `ClientPool.py` gains its one import, in the import block, and loses the dict with the blank line that separated it. The lint
  over the two files and `config/datastore.py` is the one baseline `F401` (`CosmologicalParams`, `Datastore.py:29`).
- **(3) Verbatim.** The three literals of `config/datastore.py` dump by `ast` identically to `_factories`, `_drop_actions` and
  `_default_serial_batch_size` at `818f8fa`. Its 25 imports are exactly those removed from `Datastore.py`, in order; it binds
  nothing but the three names. The docstring names each object, the layer as reader until 09, and the import-order hazard.
- **(4) The call sites.** With each `vectorized_shard_key(x)` unwrapped and the name dropped from its import, the `ast` of
  `main.py` (10 wrapped), `plot_InstantonSolutions.py` (3) and `plotting/fetch.py` (2) equals `818f8fa`'s. `config/sharding.py`
  differs by the function alone. `git grep` lists the same 22 entries as before dispatch, the calls at +1.
- **(5) The captured data.** The test's `_REGISTRY`, `_DROP_GROUPS` and `_BATCH_SIZES`, read by `ast.literal_eval`, equal a fresh
  capture from a `git archive` of `818f8fa` (30, 5, 29), entry by entry and in order, with the four quantity classes.
- **(6) The tests and the breakages.** Both new modules carry the licence header; `test_config_datastore.py` imports the layer
  first by `importlib`, with the reason. The five diffs, extracted from the note, pass `git apply --check`, and `-R --check` once
  applied; replayed in `bash`, each fails what the prompt names: 1, the `ast` test (`plotting/fetch.py:167`) and the four plot tests
  that reach `fetch_over_grid`; 2, the two batch-size tests; 3, the registry test (index 10, `phi_value` for `inflaton_mass`); 4, the
  identity test alone; 5, `_MultiClassStubPool`'s three tests (`TypeError: unhashable type: 'dict'`). The tree was clean after each.
- **(7) The schema.** The note's `schema_build.py`, extracted and re-run at `875cf41` (two shards, private Ray, in the scratchpad):
  `RESULT: the schemas agree` against `02-reference-schema.json` and against the orchestrator's pre-dispatch snapshot. The committed
  `out/05-temp-schema.json` differs from the reference only in `source`. No Ray process after.
- **(8) The cycle and the issue.** In fresh `python -I` processes: `import config.datastore` fails with the partially-initialised
  `ImportError`; after `Datastore.SQL.Datastore` or a factory module it works; `tests/test_compare_stores.py` alone passes 24. **The
  agent corrected the orchestrator's brief**, rightly: `import Datastore` and `import plotting.fetch` do not load the layer, so
  `config.datastore` imported after either still fails (measured; the brief's correction 1 and its facts claimed both served). The
  module's docstring and the §3 entry say so. The §3 entry gives what, impact (`_registry()`'s fallback, and that it would hide a real
  `ImportError`) and next step (09, P6, a fresh `import config.datastore` in its acceptance); the index row is under §6a, 62 open.
- **(9) The venv.** `pip freeze` equals the pre-dispatch copy; `pip check` clean.
- **(10) Hygiene.** The 17 store files and all 607 entries under `~/ScienceData/` have their pre-dispatch mtimes and sizes.
  DatastoreKit at `38ebb9f`, clean. No Ray process; the lock free.
- **(11) The suites**, re-run by the orchestrator at `875cf41`: default 690 (689 passed, 1 skipped), 29.5 s, load 7–22;
  integration 61 (60 passed, 1 skipped), 14.0 s. `py_compile` of the three drivers and `plotting/fetch.py` succeeds.
- **(12) The records.** The results note has README §5.1's sections, every check's command and output, the capture, the import
  orders and the breakages as diffs; the board has the §1 row, M1–M6, the §3 issue and this section with the rollback.
  `FILE_MAP.md` changes `:17` (naming `vectorized_shard_key`), adds the `config/datastore.py` row and changes `:41`.
  - *Residue, fixed:* "this commit" → `875cf41` (board ×3, results note ×5); the header's "landed" reads "landed and reviewed";
    this note added to the list of orchestrator notes; the campaign's line in `.prompts/INDEX.md` (open rows 8 → 9). In `5dbcd22`:
    `tests/test_config_datastore.py`'s docstring opened with `config/datastore.py:`, the module under test, not the test.
- **The deviations are accepted.** None is drift; the agent's correction of the brief is recorded above.
- **Handed on to 06.**
  - SI's data is `config.datastore`; the layer reads it by alias, and `import config.datastore` must follow a `Datastore.SQL.*`
    import until 09.
  - The vectorized gets are at `main.py:227` … `:1042`, `plot_InstantonSolutions.py:699`, `:702`, `:735`, `plotting/fetch.py:128`,
    `:167`. 06 touches none of them.
  - The suites start from 690 and 61.

### 5.18 After prompt 06 (2026-10-20)

- **Landed:** `5e41ce8`, results note
  [`06-prepare-the-inflaton-trajectory-factories.md`](../../.documents/dk-and-rpk-migration/06-prepare-the-inflaton-trajectory-factories.md).
  **COMPLETE:** I1–I6 hold; no stop condition of the prompt's §4 was met. Dispatched with the orchestrator's brief (fourteen
  corrections), applied as stated.
- **I1.** `sqla_InflatonTrajectory_factory.validate_on_startup` deletes the unvalidated trajectories' `InflatonTrajectoryValue`
  rows by `trajectory_serial` (`tables.get`, the pattern of `FullInstanton`'s hook) before the trajectories, on the actor's one
  `conn`. The messages are unchanged; no count line was added. `validate-on-startup.md`'s cascade map has the row, with one
  sentence on `owner_column`.
- **I2.** The 12 hooks take `prune`, with their 5 uses in bodies; the 5 rule lines follow. `git grep prune_unvalidated` (outside
  `.prompts/`, `.documents/`): 33 lines before, the 11 pool, actor, driver and fixture lines after. `base.py:29` already said
  `prune` and is untouched.
- **I3.** `validated_column: "validated"` and `owner_column: "trajectory_serial"`, one key and one comment each. The schema of a
  two-shard store built with SI's pool agrees with `05-temp-schema.json` and `02-reference-schema.json` (`RESULT: the schemas
  agree`, exit 0, both).
- **I4.** `revalidate(serial, conn, table, tables)`: `N_end` NULL → `True`, else `True` iff at least one value row; writes the
  flag with `conn`, returns a Python `bool`, raises for a missing serial. Its premises, checked and recorded with their lines:
  `object_store` runs the factory's `store` and every value insert in one `engine.begin()` (`Datastore.py:478`, `:495-504`,
  `:509`), and `store` writes `N_end` NULL exactly on failure (`InflatonTrajectory.py:208-211`; otherwise `obj._N_end`, a float
  from the solve).
- **I5.** `tests/test_inflaton_trajectory_prune.py`, 6 tests without Ray on a `tempfile` store of all 30 tables whose parent rows
  are minted by their factories and whose trajectories are written by the factory's own `store`/`validate`: the cascade (only
  the two tables lose rows, 1 and 3), without `prune`, `revalidate` against `validate` (complete, failed, stripped, empty rows),
  the missing serial, `prune` by signature (12 by own `__dict__`), the keys.
- **I6.** One `integration` test: SI's `ShardedPool` in two subprocesses (store with one trajectory validated and one withheld;
  reopen with the prune), each under its own `ray.init(address="local")`; both shards read with `sqlite3` `mode=ro` before and
  after. It cannot share `live_pool`'s Ray (fixed actor names; brief 6). With the cascade removed it finds 3 orphans on a shard.
- **Breakages** (README §5 rule 8), all caught and recorded as diffs: the cascade removed (the cascade test; the integration test,
  `3 orphaned value rows`); the failure branch inverted (the failed-row case); `CosmologicalParams.py:82` renamed back (the
  signature test, naming the factory); `owner_column` removed (the keys test); `revalidate` measured against every `efold_value`
  (the complete-row case).
- **Suites:** 696 (695 passed, 1 skipped) and 62 (61 passed, 1 skipped): 05's 690 and 61 plus the 6 and 1 new tests. The `slow`
  block is not run. No driver ran; the only Ray was the schema build's, the test's subprocesses' and the integration suite's,
  all private.
- **Closed:** `[inflaton-trajectory-prune-orphans-value-rows]` (§3 → §4; `OPEN-ISSUES.md` §6a → §7, 62 → 61 open, 25 → 26
  closed). Nothing opened.
- **Rollback:** `git revert` of `5e41ce8` alone. The venv is untouched.
- **Deviations:** the subprocesses (structurally required), two processes, no count line, parent rows minted, the inserter, extra
  `revalidate` cases, `tables[...]` in `revalidate`, breakage 5's form, the formatted new module, and a throwaway copy written to
  `/tmp` and deleted (drift, no effect); see the results note.

**Orchestrator review of prompt 06 (2026-10-20)**, by orchestrator note
[`prompt-06.md`](orchestrator/prompt-06.md), at `5e41ce8`. All twelve checks pass. The residue is fixed in this follow-up
(records only); nothing is opened.
- **(1) Scope.** 12 files, exactly the prompt's §5 list. One commit of the agent's on `a8cb166`, made once (the reflog shows
  no amend); `git status` clean; no leftover branch; no scratch file in the repository. The `/tmp` copy the agent recorded as
  drift is gone.
- **(2) The name.** By `ast`, with `prune` renamed back in each `validate_on_startup`: `CompactionFunction.py`,
  `CosmologicalParams.py`, `FullInstanton.py`, `GradientCoupledInstanton.py` and `SlowRollInstanton.py` dump identically to
  `a8cb166`'s; `InflatonTrajectory.py` differs only in the two `register`s, the new `revalidate` and the trajectory's hook. The
  five rule lines change the name alone. `git grep prune_unvalidated` gives the 11 pool, actor, driver and fixture lines, plus
  one new one, the integration test's own `ShardedPool(prune_unvalidated=…)` (`tests/test_inflaton_trajectory_prune.py:471`),
  which is that argument, not a hook's. The hook grep gives the 12 and `base.py:29`.
- **(3) The cascade, by reading.** `tables.get("InflatonTrajectoryValue")`, the delete by `trajectory_serial.in_(serials)` before
  the parent's, on the one `conn`; both messages as they were, no count line. The rule's map has the row and one sentence.
- **(4) The keys.** `register()` called at `a8cb166` (a `git archive` copy) and at `5e41ce8`: the same columns with the same
  foreign keys; the only difference is `validated_column = 'validated'` and `owner_column = 'trajectory_serial'`.
- **(5) `revalidate`.** The orchestrator's own Ray-free check, from the scratchpad, on a store of all 30 tables written by the
  factory's `store`: complete row `True` (written), failed row `True`, value rows removed `False` (written), each of type `bool`;
  serial 999 raises `RuntimeError` naming it. The prune there: `prune=True` deleted 2 trajectories and 3 value rows and nothing
  else, the second call reported nothing, no orphan. The note's I4 check cites the lines of the brief's correction 8.
- **(6) The tests and the breakages.** The module has the licence header and imports the layer first; the signature test asserts
  the 12 by the class's own `__dict__`; the integration test runs two subprocesses and reads both shards before and after. The
  five diffs, extracted from the committed note, pass `git apply --check` and, once applied, `-R --check`; replayed in `bash`,
  each fails what the prompt names: 1, the cascade test (`{1: 3, 2: 3} == {1: 3}`) and, run alone under `RAY_ADDRESS=local`,
  the integration test (`prune-shard0000.sqlite: 3 orphaned value rows`); 2, the failed-row case; 3, the signature test naming
  `CosmologicalParams (sqla_cosmological_params_factory)`; 4, the keys test (`KeyError: 'owner_column'`); 5, the complete-row
  case. The tree was clean after each.
- **(7) The schema.** The note's `schema_build.py`, re-run at `5e41ce8`: `RESULT: the schemas agree` against
  `05-temp-schema.json` and against `02-reference-schema.json`. Ray not initialised before; no Ray process after.
- **(8) The orchestrator's scenario** (`orch06/probe_pools.py`'s third part, its own process): each shard holds trajectory 1 and
  its 3 value rows, **no orphan**, where at `436fc8d` each held 3. Only one of the two actors' "Pruned 1 unvalidated
  InflatonTrajectory records" lines reached stdout this time, which is why the test reads the database rather than the logs.
- **(9) The venv.** `pip freeze` equals the pre-dispatch copy; `pip check` clean.
- **(10) Hygiene.** The 17 store files and all 607 entries under `~/ScienceData/` have their pre-dispatch mtimes and sizes.
  DatastoreKit at `38ebb9f`, clean. No Ray process; the lock free.
- **(11) The suites**, re-run by the orchestrator at `5e41ce8`: default 696 (695 passed, 1 skipped), 30.4 s; integration 62
  (61 passed, 1 skipped), 34.5 s; load 17–18 (another session's work). `ruff check --select F401,F811,F821` over the factory
  modules gives the same findings at `a8cb166` and `5e41ce8`, and none in the new test module.
- **(12) The records.** The results note has README §5.1's sections, §2.1.1's lists, I4's check, the schema checks, the
  package's properties set against the tests, the breakages as diffs and the suites beside 05's counts. The board has the §1
  row, I1–I6, the issue moved from §3 to §4 with how, and this section with the rollback; `OPEN-ISSUES.md` moves the row from
  §6a to §7, 61 open, 26 closed.
  - *Residue, fixed:* "this commit" → `5e41ce8` (board ×3, results note ×5); the header's "06 landed" reads "landed and
    reviewed"; this note added to the list of orchestrator notes; the campaign's line in `.prompts/INDEX.md` (open rows 9 → 8).
- **The deviations are accepted.** Minting the parent rows is stronger than the brief's recommendation, and the drift (a lint
  copy in `/tmp`, deleted) had no effect.
- **Handed on to 07.**
  - The only behaviour of the old layer that changed is which rows a pruning open deletes; the messages are as they were, so
    07 reads them from the logs as before. A rehearsal that prunes no trajectory is unaffected.
  - The suites start from 696 and 62.

### 5.19 After prompt 07 (2026-10-21)

- **Landed:** `0527480`, the commit tagged **`pre-datastorekit`** (annotated, local, not pushed; the user
  pushes it, README §6.3). Results note
  [`07-rehearse-before-the-datastore-swap.md`](../../.documents/dk-and-rpk-migration/07-rehearse-before-the-datastore-swap.md);
  record [`verification.md`](../../.documents/dk-and-rpk-migration/verification.md) §2.
  **COMPLETE:** L1–L4 (RH1), V2 and Z1 hold, and gate RH1 holds. No code changed. No issue was
  opened, so `.documents/OPEN-ISSUES.md` is unchanged. Dispatched with the orchestrator's brief
  (thirteen corrections), applied as stated.
- **Two stops before the cluster.**
  - On 2026-10-20 at 21:13, a ChamPBH test suite was running, another session's. The gate and the
    suites had already passed.
  - The session was then paused overnight by a quota limit.
  - On 2026-10-21 at 10:01 a second ChamPBH suite loop started (pid 91493, to 10:08:36).
  - The orchestrator ruled to wait for the loop to end and then five minutes. The cluster started
    at 10:13:54, at a load of 48 from desktop processes alone. No foreign suite ran while it was up.
- **Cluster.** `ray_cluster.sh start` took 7 s, at `127.0.0.1:6390`; `stop` took 18 s, freed the
  four ports and released the lock.
- **Builds**, 24–36 s each:
  - `reference` 36 s, exit 0;
  - `resumed-a`, `S` = 10.5 s: exit 15. The signal fell **before** the window. Under a load of
    37–108 the driver was still minting the tenth `efold_value` grid, so no `FullInstanton` was
    stored. Its store was deleted;
  - `resumed-a2`, `S` = 12.0 s on a fresh store: exit 1, by `SIGTERM`. It left 8 validated and 1
    unvalidated `FullInstanton` (δN★ 1.7111, `shard0004`, 1,673 value rows). Its 11 actors were
    `DEAD` 3 s after the signal;
  - `resumed-b` exit 0. Its open printed one `Pruned 1 unvalidated FullInstanton records`
    (`shard0004`; 1 = 1). STAGE 2 read "8 already computed, 2 to compute", then STAGES 3 and 4
    computed 10 and 10. No orphan is left;
  - `scalars` exit 0.
- **The provenance line**, once in each log:
  `>> packages: datastorekit not installed; raypoolkit 0.2.0 (https://github.com/ds283/RayPoolKit@eaef0ce60e2fc354bb32f0ad576010e6a83c1976, requested v0.2.0)`.
- **§4.3: RH1 equals RH0 bit for bit.** The comparisons ran before the readers.
  - `07-reference` against `07-resumed`, `02-reference` against `07-reference` and against
    `07-resumed`, `02-scalars-2` against `07-scalars`, and the readers' `before/` `02-scalars`
    against `07-scalars`: all five `RESULT: equal`, exit 0.
  - In each, all 30 tables were matched with RH0's row counts, and only timestamps and the JSON
    timing keys differ.
  - The schema is RH0's (`out/07-reference-schema.json`; "the schemas agree" for `07-reference`
    and `07-scalars`).
- **Readers:** steps 0–2 exit 0 on both stores. Each before/after comparison finds only
  `version{label='2026.3.0'}`. Both `scalar_data.csv` hash to `b0564eec…58a2`. The inventory is
  RH0's but for its dates and the provenance line.
- **L4.** `stage_counts.py` parsed the `raypoolkit` logs unchanged. `reference`'s and `scalars`'
  `entries`, `complete_lines`, `integrity` and `exit_status` equal 02's (a scratch script,
  reproduced in the results note). The resume's pattern is RH0's: 8 + 2 against 6 + 4, as the
  signal fell.
- **Profile database:** `jobs` 1, `profile_data` 803 against RH0's 807. There are two fewer
  `lease_serials` and two fewer `release` events, because `efold_value`'s serials were leased
  through 6 actors rather than 8. Which actor serves a replicated request varies; every
  `object_*` count is RH0's.
- **Suites**, cited from 2026-10-20 at 21:11–21:13 at `9214c9b`: 696 (695 passed, 1 skipped) and
  62 (61 passed, 1 skipped).
- **Deviations D1–D6:**
  - D1: the suites cited (IMPLEMENTATION CHOICE);
  - D2: the two stops and the pause (UNINTENDED DRIFT, external);
  - D3: a read-only `shasum` of RH0's earlier attempts' directories and of `02-resumed` and
    `02-scalars` at the gate (UNINTENDED DRIFT; accepted);
  - D4: the second `resumed-a` attempt (UNINTENDED DRIFT, external: the load);
  - D5: the CSVs staged byte-exact (IMPLEMENTATION CHOICE);
  - D6: `02-reference-profile` read `mode=ro` (IMPLEMENTATION CHOICE).
- **Observations, not opened:**
  - the narrow window moves with the machine's load;
  - the exit statuses 15 and 1;
  - the profile count is not a reproducibility measure;
  - foreign suites around the gate.
- **Handed on.**
  - *To 08–11:* RH1's stores are RH2's baseline. `07-reference.sqlite` carries no readers' row;
    for the scalars-only mode use `07-readers/scalars/before/07-scalars.sqlite`.
    `scalar_data.csv` stays `b0564eec…58a2`.
  - *To 11:* compare L4's records less `packages`; measure `S` afresh, and aim later on a loaded
    machine.
  - *To 09:* RayPoolKit G4's run under real Ray is done; S1 stays 69 of 69.
  - The tag waits for the user to push it.

**Orchestrator review of prompt 07 (2026-10-21)**, by orchestrator note
[`prompt-07.md`](orchestrator/prompt-07.md), at `0527480`. All twelve checks pass. The residue is fixed in this follow-up
(records only; the tag stays on `0527480`); nothing is opened.
- **The two stops** were the orchestrator's calls under the note's gate, not the user's. On 2026-10-21 the orchestrator found
  no foreign suite at 10:01 and resumed the agent; a ChamPBH suite loop then started, and the orchestrator ruled to wait for it
  (bounded, by `Monitor`), not to run beside it.
- **(1) Scope.** 25 files: the results note, `verification.md` (§2 appended, no line removed), the board and 22 `out/07-*` files,
  all text, the largest the 2,482-line schema snapshot. One commit of the agent's on `9214c9b`, no amend in the reflog; `git
  status` clean; no leftover branch; no scratch file in the repository.
- **(2) The tag.** `git cat-file -t pre-datastorekit` is `tag`; `pre-datastorekit^{commit}` is `0527480`; the message is the
  prompt's; `git ls-remote --tags origin pre-datastorekit` empty; nothing pushed. The agent made a second `ls-remote`, after the
  tag, for its reply's check, where the note said "not run again": corrected here.
- **(3) Ray and the lock.** `ray_cluster.sh status`: lock free, no `/tmp/ray-si` process, the four ports free.
- **(4) The logs**, all five read (`reference`, `resumed-a`, `resumed-a2`, `resumed-b`, `scalars`). The provenance line once
  each, naming `raypoolkit` 0.2.0 at `eaef0ce6…`, requested `v0.2.0`; no `STAGE G`, no `Traceback`, no `did not validate`.
  `reference`, `resumed-b`, `scalars` end `** driver exit status 0` with 4, 4, 2 `ALL WORK ITEMS COMPLETE`; `resumed-a` (15)
  and `resumed-a2` (1) show `SIGTERM received` in the `STAGE 2` pool. The only other `WARNING` lines are the prune header and
  the raylet's worker-count advisory in `scalars`. `interrupt_when.py`'s output: banner at 09:19:43 UTC, `SIGTERM` to pid 7676
  (the pidfile's) at 09:19:55 UTC; the log's `SIGTERM received` at 10:19:56.035 BST.
- **(5) The counts.** `stage_counts.py` re-run on the five logs gives the committed text and JSON byte for byte. The
  orchestrator's own script (`l4cmp.py`) finds `reference`'s and `scalars`' `entries`, `complete_lines`, `integrity` and
  `exit_status` equal to `out/02-stage-counts.json`'s; only `packages` differs, as it must. `mode=ro`: every row of the three
  stores validated, 10 / 10 / 10 / 1 (10 replicas) each, no gradient row, no orphan in any of the four value/sample tables. In
  `07-resumed`, 8 `FullInstanton` rows predate the signal and 2 follow it, and every `SlowRollInstanton` and
  `CompactionFunction` follows it: `resumed-b`'s "8 already computed, 2 to compute", then 10 and 10.
- **(6) The prune.** One report, in `resumed-b`'s log, `shard0004-store`, `Pruned 1 unvalidated FullInstanton records`: the 1
  unvalidated row recorded between builds. No other build pruned; no trajectory pruned.
- **(7) §4.3, re-run.** The readers have since written their `version` row into `07-resumed` and `07-scalars`, so the four
  comparisons that name those stores now exit 1 on that row alone, as expected. Re-run against the readers' `before/` copies
  (the stores as the builds left them), all five give `RESULT: equal`, exit 0, with text and JSON equal to the committed ones
  but for paths. 30 tables each; the bookkeeping that differs is only timestamps and the `compute_time` /
  `mean_time_per_picard_iteration` keys.
- **(8) Independently of the tool.** 02's review script (`indep.py`), by stored bits: `02-reference` against `07-reference` and
  against `07-resumed`, and `02-scalars-2` against `07-scalars`: 0 differing digests over 1 / 10 / 10 / 10 parents, with
  57,130 / 16,564 / 16,564 / 33,128 child rows (scalars-only: 57,130 and none) on each side. Control `07-reference` against
  `07-scalars`: all 30 instanton digests differ. On a scratch copy of `07-resumed` with one `FullInstantonValue`
  `P1_invPlanckMass` moved one ulp, both the script (1 `FullInstanton` differing) and `compare_stores` (a near miss, relative
  difference 1.3e-16, exit 1) caught it; the copy was deleted. **RH1 equals RH0 bit for bit, confirmed.**
- **(9) The readers.** `status.txt` on both stores as RH0's (steps 0–2 exit 0, step 4 exit 1); each `4-compare_stores.log`
  finds only `version{label='2026.3.0'}`; both plot logs read `n_collocation_points: 1 value = [ 5 ]`. Both `scalar_data.csv`
  hash to `b0564eec…58a2` on disk and as committed blobs. The inventory equals RH0's but for the provenance line, Ray's two
  connection lines and the four validated-at times.
- **(10) Hygiene.** The 17 store files in the tree, and every entry under `~/ScienceData/` (RH0's stores, `before/` copies,
  logs, both earlier attempts' directories, ChamPBH's rehearsal root) have their pre-dispatch mtimes and sizes; only the
  rehearsal root and its `logs/` directory moved, by the `07-*` files added. `pip freeze` equals the pre-dispatch copy; `pip
  check` clean. DatastoreKit `38ebb9f` and RayPoolKit `17029d9`, both clean.
- **(11) The schema and the profile database.** `--snapshot` of `07-reference` is byte-identical to `out/07-reference-schema.json`,
  which differs from 02's only in `source`; `--schema` of `07-reference` and `07-scalars` against 02's: "the schemas agree".
  The profile database: `jobs` 1, `profile_data` 803. The 4 fewer than RH0's are all `efold_value` leases (`lease_serials`
  22 over 8 actors at RH0, 20 over 6 at RH1) and their releases, as the agent said; every other method's count is RH0's.
- **(12) The records and the suites.** The results note has README §5.1's sections and the prompt's §6 list, the thirteen
  corrections, the stops and D1–D6; `verification.md` §2 has the commands verbatim and says RH1 equals RH0. The board has the
  §1 row, L1–L4 (RH1), V2, Z1, gate RH1, the G4 row's note and this section. The orchestrator re-ran both suites at `0527480`
  (10:35 BST, load 32–114, a ChamPBH suite running alongside): default 696 (695 passed, 1 skipped), 29.4 s; integration 62 (61
  passed, 1 skipped), 36.0 s.
  - *Residue, fixed:* `0527480` beside the tag (board ×4, results note ×2, `verification.md`); the results note's
    `ls-remote` lines; the header's "07 landed" reads "landed and reviewed"; this note added to the list of orchestrator
    notes; the campaign's line in `.prompts/INDEX.md`.
- **The deviations are accepted.** D3's `shasum` read opened no database and wrote nothing, and check 10 finds every file it
  read unchanged. D4's retry is within the prompt's allowance; at `S` = 10.5 s the load put the signal before the first row.
- **Handed on.**
  - *To 08–11's writing:* the tree at `pre-datastorekit` is rehearsed. RH2 is held to bitwise equality with RH1's stores (and
    so RH0's): dense `07-reference.sqlite`, scalars-only `07-readers/scalars/before/07-scalars.sqlite` or
    `02-scalars-2.sqlite`; the read `07-resumed` and `07-scalars` carry the readers' row.
  - *To 11's note:* the window moves with load (`efold_value` minting slowed by ≥ 1.1 s at a load near 100); aim later on a
    loaded machine, and ask other sessions to hold their suites before the cluster starts.
  - *To the user:* push the tag (`git push origin pre-datastorekit`) when ready (README §6.3).
- **The tag pushed** (2026-10-21), by the user: `git push origin pre-datastorekit`. `git ls-remote` gives tag object
  `9234839` on `origin`, peeling to `0527480`. The branch `dk-and-rpk-migration` itself is not pushed; the tag carried its
  commits up to `0527480` to the remote as objects only.

### 5.20 Prompts 08–11 written (2026-10-21)

Written at `91e6f31`, after 07's review, from README §2.2's charters and §5.19's "Handed on".
Measured read-only at `91e6f31`: SI's layer imports with DatastoreKit's own script
(`docs/extraction/measure_client_imports.py si --commit 91e6f31`, from its root and venv); the
package at `v0.4.0` (`ShardedPool.__init__`, `schema.dependent_tables`, `store_inventory`, the two
tools); and ChamPBH's 07–10 as done (its board §5.12–§5.15), which ran the same three steps first.
Nothing dispatched; no orchestrator note written (each is written just before its dispatch).
Nothing opened or closed, so `.documents/OPEN-ISSUES.md` is unchanged.
- **[08](08-pin-datastorekit-v0.4.0.md)** (Sonnet), items K4–K7. As 03, for
  `datastorekit @ …@v0.4.0` between `cycler==0.12.1` and `distlib==0.4.3`. Beyond the charter:
  the freeze before is 03's (82 lines); `raypoolkit` must not be reinstalled; the tag's archive
  holds **21** non-test modules; K7 also rebuilds SI's 30 registry entries (28 classes) on the
  installed base, as ChamPBH's K7 did.
- **[09](09-adopt-datastorekit.md)** (Opus), items A1–A9; closes
  `[config-datastore-cannot-be-imported-before-the-layer]` (its owner). Beyond the charter,
  **measured**:
  - **48 layer import statements in 47 files**, 2 nested, not the charter's 47: 04 removed
    `RayTools/RayWorkPool.py:23`, and 05 added the fallback at `tests/test_compare_stores.py:944`;
  - **3 `import_module` calls** of the layer (`tests/test_config_datastore.py:38`, `:39`;
    `tests/test_inflaton_trajectory_prune.py:53`), and **one import inside a subprocess script**
    the script cannot see (`tests/test_inflaton_trajectory_prune.py:459`, whose pool passes
    `drop_actions=` and `inventory_config=`);
  - so **README §5 rule 7's named exceptions for 09 grow** from `live_pool` and
    `test_grid_builder_integration.py` to also `test_config_datastore.py` (the layer's identity
    tests replaced by an `ast` test of the four pool constructions; the no-Ray test imports
    `config.datastore` alone, which is the closed issue's test), `test_inflaton_trajectory_prune.py`
    (06's I6 rebuilt on the package's pool, which is the charter's acceptance 4), and
    `test_compare_stores.py`'s fallback (which the issue said could go). README §2.2 and §5 rule 7
    are amended in this commit;
  - `main.py`'s inventory helpers are seven, not five: the two printers only they call go too;
  - U5's function sits in `config/datastore.py`, as ChamPBH's `tables_to_drop`; refusals exit 2
    before `ray.init`, as do `--inventory`'s;
  - the prose of P13 adds `.documents/FILE_MAP.md` and `config/datastore.py`'s docstring;
  - the inherited DatastoreKit hazard of dropping a replicated table (`inflaton-trajectory`'s
    closed set) is recorded, not fixed;
  - `slow` runs once (69 passed, S1).
- **[10](10-port-the-inventory.md)** (Opus), items N1–N6; closes `[show-all-flag-unused]`; opens
  the issue for `GradientCoupledInstanton`'s child table that no spec reaches (U8). Beyond the
  charter: the recommendation that `GradientCoupledInstantonProfile` (written for every row) takes
  the `values` slot and `GradientCoupledInstantonValue` is excluded; the polymorphic maps taken
  from SI's registries and checked against `tools/compare_stores.py`; the expected coverage, 24
  specs, 5 read through, 1 excluded; U5 re-run with and without the specs (ChamPBH's 08 review:
  `dependent_tables` reads spec parents); exit codes 0 / 1 / 2 as ChamPBH's; a field-by-field table
  against RH1's inventory log (P18); the store tests built through the package in a subprocess,
  `integration`-marked.
- **[11](11-rehearse-through-both-packages.md)** (Opus), items L1–L4 (RH2), V3, H1; gate RH2 and
  DatastoreKit G4. As 07, held to **RH1**: dense `07-reference.sqlite`, scalars-only
  `07-readers/scalars/before/07-scalars.sqlite` and `02-scalars-2.sqlite`, plus one dense
  comparison straight to RH0. Beyond the charter:
  - the agent asks the user to have other sessions hold their suites before it starts (§5.19);
  - `S` measured afresh, aiming later on a loaded machine;
  - L4 compared less the provenance line;
  - `--inventory` compared with RH1's field by field, since its layout is 10's;
  - H1 runs before the readers;
  - a miss marks no gate and commits nothing; an L4 difference alone holds back G4 for the user.

### 5.21 After prompt 08 (2026-10-21)

- **Landed:** `1b1ca6d`, results note
  [`08-pin-datastorekit-v0.4.0.md`](../../.documents/dk-and-rpk-migration/08-pin-datastorekit-v0.4.0.md).
  **COMPLETE:** K4–K7 hold; no code or test changed; no issue opened, so
  `.documents/OPEN-ISSUES.md` is unchanged.
- **K4.** `requirements.txt` gains `datastorekit @ git+https://github.com/ds283/DatastoreKit@v0.4.0` at
  `:16`, nothing else (73 lines). `ray==2.55.1` is now `:58`, `raypoolkit` `:59`, `SQLAlchemy` `:67`.
- **K5.** The dry run reported `datastorekit-0.4.0` alone; the install, run once, installed it alone.
  pip's `Resolved … to commit 8e7c1d77…` names the tag object; the commit is `c8570e84…`.
  `raypoolkit` was re-resolved, not reinstalled (its 16 files keep their mtimes). pip itself was not
  upgraded.
- **K6.** `pip freeze` differs from the saved one by the one line
  `datastorekit @ git+https://github.com/ds283/DatastoreKit@c8570e849334d09085bbd84876095fc9e22bd005`;
  `pip check` is clean; `direct_url.json` is a VCS record at that commit, requested `v0.4.0`, no
  `dir_info`; the 21 modules equal `git archive v0.4.0`'s byte for byte, `tests/` and its data are not
  installed; the import starts no Ray; `sharded_store --help` exits 0. The provenance line is
  `>> packages: datastorekit 0.4.0 (https://github.com/ds283/DatastoreKit@c8570e849334d09085bbd84876095fc9e22bd005, requested v0.4.0); raypoolkit 0.2.0 (https://github.com/ds283/RayPoolKit@eaef0ce60e2fc354bb32f0ad576010e6a83c1976, requested v0.2.0)`.
- **K7.** On the installed package (imported from the venv's `site-packages`): U3's `timestamp` behaves as
  required; `SQLAFactoryBase` refuses a subclass without `build`; SI's 30 registry entries (28 classes)
  instantiate on it; 12 classes define all of `store`, `validate`, `validate_on_startup`, 16 none, 0
  some.
- **Suites:** 696 (695 passed, 1 skipped) and 62 (61 passed, 1 skipped), unchanged from 07.
- **Rollback:** `git revert` of `1b1ca6d` **plus** `./venv/bin/pip uninstall -y datastorekit`
  (README §4.4). The venv is outside git, so the revert alone leaves the package installed (inert
  until 09 imports it).
- **Deviations:** the board section number, the pin's line number and the suites' commands, as the
  orchestrator's brief corrected; none unintended.

**Orchestrator review of prompt 08 (2026-10-21)**, by orchestrator note
[`prompt-08.md`](orchestrator/prompt-08.md), at `1b1ca6d`. All ten checks pass. The residue is fixed in this follow-up
(records only); nothing is opened.
- **(1) Scope.** 3 files: `requirements.txt`, the results note and the board. One commit of the agent's on `7ef06ad`, no amend
  in the reflog; `git status` clean; no untracked file.
- **(2) K4.** One added line at `:16`, between `cycler==0.12.1` and `distlib==0.4.3`; 73 lines.
- **(3) The freeze, read from the venv.** Against the committed `measure/out/7bb3efd-pip-freeze.txt`: exactly two added lines,
  03's `raypoolkit` and `datastorekit @ git+https://github.com/ds283/DatastoreKit@c8570e849334d09085bbd84876095fc9e22bd005`;
  against the pre-dispatch copy, the `datastorekit` line alone. `pip check` clean. `raypoolkit`'s 16 files keep their
  pre-dispatch mtimes and sizes (re-resolved, not reinstalled). site-packages differs from the pre-dispatch listing by
  `datastorekit/` and `datastorekit-0.4.0.dist-info/` only. pip is still 26.0.1.
- **(4) The origin.** `direct_url.json`, read in site-packages: `url` `https://github.com/ds283/DatastoreKit`, `commit_id`
  `c8570e849334…`, `requested_revision` `v0.4.0`, `vcs` `git`, no `dir_info`. `INSTALLER` is `pip`; the only `.pth` is
  `_virtualenv.pth`; no `__editable__` or `.egg-link`.
- **(5) The files.** The tag's archive against the installed package, `__pycache__` aside: the same 21 `.py` files, none
  different byte for byte; no `tests/`, no data file, nothing else. `RECORD` has 42 `datastorekit/` entries (the 21 modules
  and their `.pyc`), none under `tests`, every hash matching.
- **(6) Import and helper.** The import one-liner prints `False`; `sharded_store --help` exits 0. The helper gives
  `datastorekit` `0.4.0`, the URL, `c8570e849334…`, `v0.4.0`, `editable: False`, and `raypoolkit` unchanged;
  `format_package_provenance` prints the prompt's line. `pip show datastorekit`: `Requires: ray, sqlalchemy`.
- **(7) K7 replayed.** The orchestrator's prototype, run with the archive off `sys.path`, imported `datastorekit` from the
  venv's `site-packages` and printed the pre-dispatch figures exactly: U3's four behaviours, the base refusing a class
  without `build`, **30 of 30 entries, 28 classes, 12 / 16 / 0**, no Ray. The agent's `k7_installed.py` asserts its import
  is from `site-packages` and gives the same output.
- **(8) The pip account.** The note quotes `Would install datastorekit-0.4.0` and `Successfully installed
  datastorekit-0.4.0`, both `Resolved …` lines (DatastoreKit `8e7c1d77…`, RayPoolKit `4e7eb153…`), and says each is a tag
  object and that `raypoolkit` was re-resolved.
- **(9) Hygiene.** DatastoreKit `38ebb9f` and RayPoolKit `17029d9`, clean. The 17 store files and all 834 entries under
  `~/ScienceData/` keep their pre-dispatch mtimes and sizes. No Ray process; the lock free.
- **(10) The suites and the records.** The agent's 696 and 62, at loads of 25–60. The orchestrator re-ran both at `1b1ca6d`
  (17:16 BST, load 18–23): default 696 (695 passed, 1 skipped), 27.6 s; integration 62 (61 passed, 1 skipped), 31.2 s. The
  results note follows README §5.1, with every §2 check's command and output and K7's script whole; the board has the §1 row,
  K4–K7, the header and this section with the rollback.
  - *Residue, fixed here:* "the commit that adds the note" → `1b1ca6d` (board ×3, results note ×2); the header's "08 landed"
    reads "landed and reviewed"; this note added to the list of orchestrator notes; the campaign's line in `.prompts/INDEX.md`.
- **The deviations are accepted.** D7 (mtimes by a Python `os.stat` walk, since the agent's `stat` on `PATH` was GNU's) is
  sound: the orchestrator's `/usr/bin/stat` comparison agrees.
- **Handed on to 09.**
  - Every driver now prints `>> packages: datastorekit 0.4.0 (…@c8570e849334…, requested v0.4.0); raypoolkit 0.2.0
    (…@eaef0ce6…, requested v0.2.0)`.
  - SI's 30 registry entries instantiate on the installed base as they stand, so 09's factories change only their import.
  - `requirements.txt`'s lines after `:15` moved down by one.
  - 09's suites start from 696 and 62; `slow` from S1's 69.

### 5.22 After prompt 09 (2026-10-21)

- **Landed:** `f4da58f`, results note
  [`09-adopt-datastorekit.md`](../../.documents/dk-and-rpk-migration/09-adopt-datastorekit.md).
  **COMPLETE:** A1–A9 hold; no stop condition met; `[config-datastore-cannot-be-imported-before-the-layer]`
  closed (§4); nothing opened.
- **A1.** The 7 layer modules deleted (2,546 lines) and their `.pyc`; `Datastore/__init__.py` and
  `Datastore/SQL/__init__.py` 0 bytes. DatastoreKit's script: **48** statements in 47 files (2 nested), 0
  literals, **3** `import_module` at `597730f`; at a dangling commit of the staged tree the 7 absent and **0**,
  **0**, **0**.
- **A2–A3.** 47 imports rewritten by the module map, the 48th (the fallback) removed. By `ast`, the module path
  normalised: 42 of the 48 files of §1.2 identical to the gate (every factory, concept and compute-target
  module); the 6 others are `main.py`, the plot scripts, `conftest.py` and the two tests §1.6 names.
- **A4.** The four constructions pass `factories=` and `serial_batch_sizes=` from `config.datastore`, no
  `drop_actions=`, no `inventory_config=`; `main.py`'s `drop_tables=`. The package's default lease is 500 and it
  ignores `temperature`; neither matters to SI.
- **A5 (U5).** `config.datastore.tables_to_drop`, by `dependent_tables`, called before `ray.init`; exit 2 on
  stderr. Over the 31 sets: 10 closed, 21 refused, equal to the orchestrator's measurement. Messages: see the
  results note.
- **A6.** `live_pool` is the package's; `test_grid_builder_integration.py` counts by `sqlite3` `mode=ro`;
  `test_config_datastore.py` loses its 2 layer tests for 1 `ast` test of the four pools;
  `test_inflaton_trajectory_prune.py`'s I6 runs the package's pool; `test_compare_stores.py`'s fallback gone. New:
  `test_tables_to_drop.py` (9), `test_main_refusals.py` (3), `test_datastorekit_timestamp.py` (1, integration).
- **A7.** `--inventory` refuses before Ray; the 7 inventory functions deleted. Prose corrected: `CLAUDE.md`'s
  protected list and the sentence after it, `pool-read-apis.md`, `datastore-factories.md`'s replication account,
  the two shard-key notes, `FILE_MAP.md`, `config/datastore.py`'s docstring. Stale for 12:
  `INFRASTRUCTURE.md`, `architecture-summary.md`, `tools/compare_stores.py:39`, `:94`, `:115-116`,
  `tests/test_rehearsal_stage_counts.py:26`, three comments in `ObjectFactories/InflatonTrajectory.py` (listed in
  the results note).
- **A8.** `import config.datastore` alone exits 0: 30 entries on the package's base, no Ray.
- **A9.** Schema: "the schemas agree" with the gate's snapshot and `07-reference-schema.json`
  (`out/09-temp-schema.json`); no difference. Suites: default 707 (706 passed, 1 skipped), integration 63 (62
  passed, 1 skipped), `slow` 69 passed (397 s). Acceptance 4: I6 on the package's replicated prune, both shards,
  no orphan, no refusal. Acceptance 5: U3's test passes for a `delta_Nstar` and a `FullInstanton`. Breakages
  1–6 caught (the factory import, `timestamp=`, `owner_column` — the package's `_prune_shard` refusal —, the
  closure check, `factories=` in `live_pool`, the refusal's order).
- **Inherited hazard, recorded:** the only closed set with `inflaton-trajectory` (all five) drops a replicated
  table: DatastoreKit's `[00-a-drop-action-drops-a-replicated-table-outside-the-in-flight-record]`.
- **Rollback:** `git revert` of `f4da58f` alone; nothing in the venv (README §4.4).
- **Deviations:** the board section and greps as the brief corrected; the grid-builder test by `sqlite3`
  (correction 3); §1.8's `-I` command cannot see the root, so the import was run with `PYTHONPATH` and with `-I`
  plus an explicit `sys.path` entry; the pools import the two objects by name; U3's test is one test of both
  objects; one new test fixed before the suites were recorded. None unintended.

**Orchestrator review of prompt 09 (2026-10-21)**, by orchestrator note
[`prompt-09.md`](orchestrator/prompt-09.md), at `f4da58f`. All twelve checks pass. The residue is fixed in this
follow-up (records only); nothing is opened.
- **(1) Scope.** 73 files: the 7 layer modules deleted and the two `__init__.py` emptied, the 42 one-line import
  rewrites, the drivers, `config/datastore.py`, `conftest.py` and the four named test modules, three new test
  modules, the prose of §1.7, `out/09-temp-schema.json`, the results note, the board and `OPEN-ISSUES.md`;
  nothing else. One commit of the agent's on `597730f`, no amend in the reflog, no leftover branch; `git status`
  clean; no ignored `.pyc` of a deleted module; no file in the tree newer than the note but the commit's own and
  `ruff`'s cache. (The agent's session hit an API limit before its suites and was resumed by message; its tree
  was intact, and it ran the suites, the breakages and the commit after.)
- **(2) DatastoreKit's script at `f4da58f`**, from its root: the 7 layer files absent, **0** imports, **0**
  literals, **0** `import_module`, 25 factory-module imports, 197 files read (194 + the 3 new tests); both
  `__init__.py` 0 bytes. `git grep` for the dotted layer names outside `.prompts/` and `.documents/`: no hit at
  all.
- **(3) By `ast`**, every `ImportFrom` mapped by the module map: the 42 files of §1.2 other than the drivers,
  `conftest.py` and `test_compare_stores.py` are identical to `597730f`'s, docstrings included. The factory
  package's diff is the 22 import lines and `base.py`'s deletion, nothing else. (The note's "42 of the 48 files"
  counts the 47 files of §1.2's statements and `test_inflaton_trajectory_prune.py`, whose layer use was an
  `import_module`.)
- **(4) The drivers.** `main.py`'s top level, by `ast` with the seven inventory functions set aside: one import
  added, two changed (the package's `ProfileAgent` and `ShardedPool`), the `--inventory` `If` and the `--drop`
  `Try` inserted after the provenance print and before `ray.init`, and the `With` changed (`drop_tables=`,
  `factories=`, `serial_batch_sizes=`; `drop_actions=`, `inventory_config=` and the `if args.inventory` branch
  gone); nothing else. Each plot script: the `config.datastore` import, `inventory_config` out, the package's
  `ShardedPool`, and its pool's arguments.
- **(5) U5, replayed.** `tables_to_drop` over all 31 subsets: its decisions equal the pre-dispatch measurement
  with `dependent_tables` on 31 of 31 (10 closed); for every refusal, the groups it names are not among those
  requested, and adding them closes the set. `main.py` with `--inventory`, `--drop full-instanton` and `--drop
  inflaton-trajectory`, address `127.0.0.1:9`: the provenance line, the refusal on stderr, exit 2, no file. With
  `--drop compaction-function` it passes the check and waits on Ray until the timeout, creating nothing. No Ray
  process after.
- **(6) The changed tests**, by `ast` with docstrings stripped, against `597730f`: `conftest.py` the imports and
  `live_pool`'s arguments; `test_config_datastore.py` the two `import_module` lines and two layer tests gone,
  the `ast` pool test and its helpers added, the no-Ray test's code string; `test_inflaton_trajectory_prune.py`
  the `:53` import and I6's script alone (I6's body unchanged); `test_compare_stores.py` `_registry` alone;
  `test_grid_builder_integration.py` `test_no_duplicate_rows_created` alone, plus a shard-reading helper. No
  other existing test module changed.
- **(7) The new tests**, read. Licence headers. `test_tables_to_drop.py` decides all 31 sets and pins the three
  messages, its no-Ray check in a fresh process; `test_main_refusals.py` runs `main.py` with a dead address and
  `RAY_ADDRESS` set to it, a 120 s timeout, and checks the order by `ast`; `test_datastorekit_timestamp.py` is
  `integration`-marked, says why, and compares each fetched `timestamp` with the `timestamp` column of the row
  whose `serial` is the object's `store_id`, read `mode=ro` from the shard files (every shard for the
  `delta_Nstar`, the one holding it for the `FullInstanton`). The `ast` pool test accepts a bare imported name
  or `config.datastore.<name>`, and refuses `**kwargs`.
- **(8) The breakages**, extracted from the results note and replayed in `bash`: each `--check`s, applies,
  `-R --check`s and reverts. 1: `ModuleNotFoundError: … 'Datastore.SQL.ObjectFactories.base'` loading the
  conftest; 2: the U3 test, `timestamp` `None` on the `FullInstanton`; 3: I6's reopen fails with the package's
  "the prune of "InflatonTrajectory" on shard 0 … did not take"; 4: the three singleton tests and the 31-set test;
  5: `TypeError … missing … 'factories'` at `live_pool`'s setup, and the `ast` test names `tests/conftest.py:60: no
  factories=`; 6: "the --inventory refusal (line 113) must precede ray.init (line 109)". Tree clean after.
- **(9) Without Ray and the schema.** `config.datastore` imported alone from outside the root (`PYTHONPATH`):
  30 entries, 28 classes, every one an instance of the package's `SQLAFactoryBase`, no layer module loaded, no
  Ray. `sharded_store --help` exits 0; the three drivers byte-compile. A two-shard store rebuilt through the
  package's pool at `f4da58f`: "the schemas agree" against `out/09-temp-schema.json`, `07-reference-schema.json`
  and the pre-dispatch prototype's store.
- **(10) The suites.** The agent's 707, 63 and `slow` 69, at loads 6–20. The orchestrator re-ran at `f4da58f`
  (18:56 BST, load 18–23): default **707 (706 passed, 1 skipped)**, 31.1 s; integration **63 (62 passed, 1
  skipped)**, 31.5 s. `slow` was not re-run: the agent's 69 and the pre-dispatch prototype's 69 agree, and S1's
  bar is met. `ruff check --select F401,F811,F821` on the 56 Python files the commit adds or modifies: 33 at the
  gate, 31 now, none new; the two gone are the emptied `__init__.py`.
- **(11) Hygiene.** `pip freeze` equals the dispatch copy; `pip check` clean. DatastoreKit `38ebb9f` and
  RayPoolKit `17029d9`, clean. The 17 store files and the 835 `~/ScienceData/` entries keep their mtimes and
  sizes. No Ray process; the lock free.
- **(12) The records.** `CLAUDE.md`'s protected list loses its six layer files and the `Datastore.py` sentence
  becomes the package's; `pool-read-apis.md` says there is no `pool.inventory()` and names `read_inventory` from
  10; `datastore-factories.md` describes the package's recorded replicated write and its check at open, the rule
  kept; both shard-key notes carry a status line (`_assign_shard_keys` at `ShardedPool.py:3618`, `:3626`,
  `:3674` at `v0.4.0`, checked); `FILE_MAP.md`'s rows; `config/datastore.py`'s docstring. The results note
  follows README §5.1 with the prompt's §6 additions and the stale list for 12. The board and `OPEN-ISSUES.md`
  (60 open, 27 closed, 2026-10-21) as the prompt asks.
  - *Residue, fixed here:* "this commit" → `f4da58f` (board ×3, results note ×5); the header's "09 landed" reads
    "landed and reviewed"; this note added to the list of orchestrator notes; the campaign's line in
    `.prompts/INDEX.md` (09 landed and reviewed; the issue closed; 8 → 7 open).
- **The deviations are accepted.** The agent's account of §1.8 is right: `python -I` ignores `PYTHONPATH`, so the
  prompt's literal command cannot see the root; the import was shown both with `PYTHONPATH` and with `-I` and the
  root inserted in code.
- **Handed on.**
  - **To 10:** the suites start from 707 and 63. U5's table is pinned by `tests/test_tables_to_drop.py` and may move
    when `inventory_spec`s add parents (`dependent_tables` reads them); re-measure and change the test with a
    named reason. `--inventory`'s refusal and its two tests in `tests/test_main_refusals.py` are 10's to replace.
    `config/sharding.py:78` and `:97` and the 17 `inventory()` hooks are still there.
  - **To 11:** a pruning reopen now prints the package's `!! INTEGRITY WARNING … pruned by the pool under a
    "prune" record` and `>> Pruned the unvalidated rows of …` lines beside the factories' own; a new primary holds
    `replication_in_flight`; the provenance line is 08's.
  - **To 12:** the stale list of the results note (`INFRASTRUCTURE.md`, `architecture-summary.md`,
    `tools/compare_stores.py:39`, `:94`, `:115`, `:116`, `tests/test_rehearsal_stage_counts.py:26`, three comments in
    `ObjectFactories/InflatonTrajectory.py`), and `pool-read-apis.md`'s claim that `config/sharding.py` is on
    `CLAUDE.md`'s protected list, which it never was.

### 5.23 After prompt 10 (2026-10-21)

- **Landed:** `e2c7b22`, results note
  [`10-port-the-inventory.md`](../../.documents/dk-and-rpk-migration/10-port-the-inventory.md).
  **COMPLETE:** N1–N6 hold; no stop condition met; `[show-all-flag-unused]` closed (§4);
  `[gci-value-table-outside-the-inventory]` opened (§3).
- **N1.** 22 `def inventory_spec(self)` in 22 factory modules, serving **24** registry entries (the dimensionful
  factory serves `inflaton_mass`, `phi_value`, `pi_value`), each the identity its `build` matches: the results
  note's table, written out in `tests/test_inventory_specs.py`'s `EXPECTED_SPECS`. Four polymorphic parents
  (`potential` by `potential_type`; `diffusion_model` by `diffusion_type` on the three instantons), maps from SI's
  registries, equal to `tools/compare_stores.py`'s; `CompactionFunction`'s two instantons `nullable`; no
  `cross_shard`; `version` no parent; `MasslessDecoupledDiffusion` `InventorySpec()`; `IntegrationSolver`
  `label`, `stepping` (a minimum); `CosmologicalParams` `name`. Key fields are named after `build`'s payload keys.
  `inventory_classes` accepts the registry (24); every column resolves against `build_schema`.
- **N2.** `tools/inventory_report.py`: `format_inventory_report(inventory, db_name, verbose=False) -> str` (no
  `units`: the unit is the column's suffix; deviation 5). Reads nothing but the registry's column types, in memory.
  Today's 13 sections, titles and order kept, 11 classes added; values `.6g` with units; more than 20 values → the
  first and last 10, more than 10 records → 5 and 5, as today; compute targets by validated group, records by
  physical labels, one timestamp range per class (the inventory has no per-group range); every problem whole.
  Version labels struck (brief correction 3); the field table is in the results note.
- **N3.** `main.py --inventory` before `ray.init`: exit 0 with the report, 1 on the reader's `RuntimeError` (the
  only exception caught), 2 with `--drop`; nothing created or changed; `--show-all` → `verbose`, its help true.
- **N4.** The 17 hooks deleted with the 11 `datetime` imports only they used; `config/sharding.py`'s
  `inventory_config`, `_instanton_merge` and comment. **U5 unmoved:** 31 of 31 sets, decision, message and
  `dependent_tables` equal with 0 and 24 specs (10 closed); the specs' only new edges (trajectory → potentials,
  instantons → diffusion model) reach no drop group. `tests/test_tables_to_drop.py`: docstring only.
- **N5.** 30 entries: 24 specs, 5 read through (`values`), 1 excluded (`GradientCoupledInstantonValue`, with its
  reason); the test names a class in none or two places, a stale or unexplained exclusion, a wrong slot or owner.
- **N6.** `pool-read-apis.md` §1; `FILE_MAP.md` (`:17`, `:41`, new `:42`); the `--show-all` help. Stale for 12: a
  spec rule for new factories; `INFRASTRUCTURE.md` `:183`, `:228`, `:232`, `:498`; `architecture-summary.md` `:194`,
  `:227`, `:394`, `:403`, `:494-500`, `:580`; `FILE_MAP.md:54`; 09's list.
- **Verification.** Suites: default **730 (729 passed, 1 skipped)**, integration **67 (66 passed, 1 skipped)**: the
  gate's 707 and 63, + `test_inventory_specs.py` 12, `test_inventory_report.py` 10, `test_main_refusals.py` 3 → 4,
  + `test_inventory_store.py` 4 (integration: a two-shard store through the pool in a subprocess under a private Ray;
  read back with every class at its count and no named problem; `main.py --inventory` exit 0 with that report,
  every file unchanged; `--show-all` verbose). No `slow` run (no `ComputeTargets/` change). `ruff` F401/F811/F821:
  18 at the gate, 18 now, none new. Breakages 1–6 caught (the spec table; a column and the table; the package's
  `inventory_classes` refusal; the `ast` order test; coverage names the owner and its profile table; coverage names
  `ScratchValue`).
- **Found, not acted on:** `redshift`'s `z = 0` lookup has its comparison inside the `abs` (added to
  `[redshift-registered-in-neither-table-list]`); a failed and a successful compute target under one key would be a
  `duplicate` to the package (SI's drivers write neither).
- **Rollback:** `git revert` of `e2c7b22` alone; nothing in the venv (README §4.4).
- **Deviations:** the board section and the counts (correction 1); version labels struck (3); nullable parents (4);
  today's truncation thresholds (13); no `units` parameter (an implementation choice); one timestamp range per
  class; key fields named by payload keys; the new `--inventory` tests in `test_main_refusals.py` (correction 10);
  the docstring and `FILE_MAP.md` rows (9, 12); the redshift finding added to its open row; one new test corrected
  before the suites were recorded. One `UNINTENDED DRIFT`, that test, caught by the suite.

**Orchestrator review of prompt 10 (2026-10-21)**, by orchestrator note
[`prompt-10.md`](orchestrator/prompt-10.md), at `e2c7b22`. All twelve checks pass. The residue is fixed in this
follow-up (records only); nothing is opened.
- **(1) Scope.** 36 files: the 22 factory modules, `config/sharding.py`, `config/argument_parser.py`, `main.py`,
  `tools/inventory_report.py`, three new test modules, `test_main_refusals.py`, `test_tables_to_drop.py`,
  `pool-read-apis.md`, `FILE_MAP.md`, the results note, the board and `OPEN-ISSUES.md`; nothing else. One commit of
  the agent's on `62cdca5`, no amend in the reflog, no leftover branch; `git status` clean; nothing untracked.
- **(2) The specs against the lookups.** Compared column by column (field names aside) with the pre-dispatch
  prototype, which was read against each `build`: **24 of 24 equal**, leaves, parents (with `of`, type map, type
  column, `nullable`, `cross_shard`), `values` and `validated`; `inventory_classes` gives the prototype's order. 22
  `def inventory_spec`; no `cross_shard`; no `version` parent; `CompactionFunction`'s two instantons `nullable`; the
  maps built in the method from `POTENTIAL_REGISTRY` and `DIFFUSION_MODEL_REGISTRY`.
- **(3) The factory diffs.** By `ast`, each of the 22 modules at `e2c7b22~1` equals `e2c7b22`'s with `inventory_spec`,
  `inventory()` and the imports set aside, docstrings included (22 of 22). Imports: one `datastorekit.store_inventory`
  line added to each, `from datetime import datetime` removed from 11 (used by the hooks alone). Added lines are the
  specs, their comments and the two registry imports inside them; no comment removed outside a hook.
  `config/sharding.py` loses `:78-102` alone (`inventory_config`, `_instanton_merge`, their comment).
- **(4) `main.py`.** Two imports, and the refusal replaced by the `--inventory` branch (`:103-121`), still before the
  `--drop` `try` and `ray.init`: `--drop` → exit 2; `read_inventory(args.database, factories)`, `RuntimeError` →
  `!! --inventory: …` exit 1; the report with `verbose=args.show_all`, exit 0. Nothing else changed.
- **(5) By running it**, address `127.0.0.1:9`, `RAY_ADDRESS` the same: an absent store exit 1 with the reader's
  message, no file; `--drop full-instanton` exit 2, no file; copies of the prototype's `store-a`, exit 0 (107 lines,
  stderr empty, the three files' SHA-1 unchanged) and with `--show-all`; `store-b`, exit 0 with `problems: 2` and
  both problems printed whole under their classes. Records render by physical labels; the NULL slow-roll side as
  `none`. No Ray process after.
- **(6) The report.** By `ast`, no `open`, `sqlite3`, `create_engine`, `connect`, `read_inventory`,
  `open_read_only` or `execute` in `tools/inventory_report.py`; it imports `build_schema` and the registry (column
  types, in memory). One public function. The field table accounts for every field of today's report (note
  correction 13); version labels and `N_end` not kept, with reasons; one timestamp range per class, since
  `ClassInventory` has no per-group range. The `units` parameter is dropped (deviation 5): accepted, the unit is the
  column's suffix.
- **(7) The tests, read.** Licence headers. `test_inventory_store.py` builds its own two-shard store in a subprocess
  under `ray.init(address="local")`, not `live_pool`'s, every parent real, failed rows under keys of their own; its
  four tests are `integration`-marked and say why. `test_inventory_report.py` asserts decimal text the test chose and
  a problem over 600 characters on one line. `test_inventory_specs.py`'s `EXPECTED_SPECS`, `READ_THROUGH` and
  `EXCLUDED` are literal; the `ast` order test counts one branch.
- **(8) The breakages**, extracted from the results note and replayed in `bash`: each `--check`s, applies,
  `-R --check`s and reverts. 1 and 2: `test_each_spec_is_the_identity_its_build_matches` (`FullInstanton`,
  `N_init`); 3: the package's `ValueError` from `inventory_classes`, naming `potential_type`; 4: "the --inventory
  branch (line 117) must precede ray.init (line 111)"; 5: the order test, and the coverage test naming
  `GradientCoupledInstanton` (and its profile table); 6: the coverage test naming `ScratchValue`. Tree clean after.
  Breakage 1 is caught only by the literal spec table (the foreign key keeps U5's table whole), which is why that
  table is in the test.
- **(9) U5, replayed** at `e2c7b22` over all 31 subsets, with the 24 specs and with every spec hidden: 10 closed in
  both, no decision or message differs. `test_tables_to_drop.py`'s bodies equal `e2c7b22~1`'s by `ast`, docstrings
  stripped. `test_main_refusals.py`: the `drop-full-instanton` case and the `--drop` half of the order test unchanged;
  the inventory case now `--inventory --drop` (exit 2), one test added (absent store, exit 1).
- **(10) The suites.** The agent's 730 and 67. The orchestrator re-ran at `e2c7b22` (19:48 BST, load 10–32):
  default **730 (729 passed, 1 skipped)**, 32.1 s; integration **67 (66 passed, 1 skipped)**, 55.2 s. `slow` not
  run: no `ComputeTargets/`, `Numerics/` or `Interpolation/` change. `ruff check --select F401,F811,F821`, per file,
  each at the gate by stdin: 18 at the gate (`main.py` 16, `CompactionFunction.py` 1, `FullInstanton.py` 1), 18 now,
  the four new files clean.
- **(11) Hygiene.** `pip freeze` equals the dispatch copy; `pip check` clean. DatastoreKit `38ebb9f` and RayPoolKit
  `17029d9`, clean. The 17 store files and the 835 `~/ScienceData/` entries keep their mtimes and sizes. No Ray
  process; the lock free.
- **(12) The records.** `pool-read-apis.md` says the inventory is `read_inventory` through `main.py --inventory`,
  before Ray; `FILE_MAP.md` `:17`, `:41`, `:42`; the `--show-all` help true. The results note follows README §5.1
  with the prompt's §6 additions. The board: §1 row, N1–N6, the header, this section with the rollback, the issue
  moved §3 → §4, the GCI issue in §3, the `redshift` row widened by the `z = 0` finding (checked: the comparison is
  inside `sqla.func.abs`). `OPEN-ISSUES.md`: the closed row in §7, the new row in §6a, 60 open, 28 closed,
  2026-10-21.
  - *Residue, fixed here:* "this commit" → `e2c7b22` (board ×3, results note ×6); the header's "10 landed" reads
    "landed and reviewed"; this note added to the list of orchestrator notes; the campaign's line in
    `.prompts/INDEX.md` (10 landed and reviewed; one issue closed, one opened; 7 open, unchanged).
- **The deviations are accepted.** Deviation 12 (a `ray.is_initialized()` assertion that failed in the suite, where
  another module had started Ray) was fixed before the recorded runs; the Ray-free claim is shown instead by
  `main.py --inventory` in a subprocess with a dead address.
- **Handed on.**
  - **To 11:** `main.py --inventory` reads before Ray and prints the report of the results note's samples; its layout
    differs from RH1's by design, and nothing parses it. A clean RH2 store should print `problems: none`. RH0's and
    RH1's stores would be refused (exit 1), so `compare_stores` stays the comparison. The suites start from 730 and 67.
  - **To 12:** the stale list of the results note (a spec rule for new factories; `INFRASTRUCTURE.md`,
    `architecture-summary.md`, `FILE_MAP.md:54`; 09's list).
  - **To the user:** `[gci-value-table-outside-the-inventory]`, whether to ask DatastoreKit for a second value table
    per spec (README §6.3).

### 5.24 The second value table requested of DatastoreKit (2026-10-21)

At the user's request, after 10's review: a brief for DatastoreKit,
[`datastorekit-second-value-table-brief.md`](datastorekit-second-value-table-brief.md), asking for an
`InventorySpec` that counts more than one value table, so that `read_inventory`, and every fingerprint
taken through it, sees `GradientCoupledInstantonValue` (`[gci-value-table-outside-the-inventory]`, §3).
This is the request README §6.3 left to the user at 10, and the one DatastoreKit's `fingerprint` campaign
held back "until SI's prompt 10 settles it and the user asks". Measured at DatastoreKit `38ebb9f`, SI
`d0ce59c`, ChamPBH `7055532` and SGK `031bcb4`:
- only `store_inventory.py` reads `values` in the package; a value table names its owner by foreign key,
  so `dependent_tables` does not move;
- ChamPBH and SGK need nothing (one value table per class; ChamPBH's coverage test excludes nothing);
- the brief's advice keeps `values` and `value_count` as they are and adds a defaulted field beside each,
  emitted in a record only when a class declares it, so that every existing record, and every recorded
  fingerprint, is unchanged; whether `ENCODING_FORMAT` moves, and the version, are DatastoreKit's.

SI's prompts 11 and 12 do not wait for the release. SI adopts it in a pin prompt of its own, before it
adopts RunRegistryKit, so that no fingerprint SI records lacks the table; that prompt closes the issue.
The issue stays open, its row in §3 and in `.documents/OPEN-ISSUES.md` pointing at the brief.

### 5.25 DatastoreKit `v0.5.0` evaluated; U12 ruled; 10a and 10b written (2026-10-22)

DatastoreKit's `extra-values` campaign answered the brief of §5.24 with **`v0.5.0`** (tag object
`6a6809d`, commit `f47b9a2`, tagged 2026-10-22 after CI at both ends; the campaign closed at
`2900d82`). Evaluated read-only in DatastoreKit and without touching SI's venv (README §0.6 holds the
measurements):
- **The change** is two of the wheel's 21 modules, `store_inventory.py` and `store_fingerprint.py`
  (a comment); the other 19 are byte-identical to `v0.4.0`'s, and `pyproject.toml` changes only its
  version. `InventorySpec.extra_values` (table → column) is counted per record into
  `Record.extra_value_counts`, carried in `as_json` only where not empty; its orphans are
  `orphan-value` problems; `inventory_classes` refuses a `values` table named again in
  `extra_values`; `ENCODING_FORMAT` stays 1.
- **It meets the brief.** Its departures (keyed by table name; the neutral registry declares the
  field; the refusal in `inventory_classes`) cost SI nothing.
- **On SI:** the suites, unchanged, on the tag's package: 730 (729 passed, 1 skipped) and 67 (66
  passed, 1 skipped); on a two-shard SI store, the same fingerprint (overall, per class, per record)
  under `v0.4.0` and `v0.5.0` with SI's specs unchanged; with the declaration, only
  `GradientCoupledInstanton`'s digest moves and its record carries the count; an orphan row is
  named; `pip install --dry-run` of the pin would install `datastorekit-0.5.0` alone.

**U12, ruled by the user as recommended: adopt it before 11.** Written at `f5f395b`:
- **[10a](10a-pin-datastorekit-v0.5.0.md)** (Sonnet), items K8–K11: 08 again, the line replaced, the
  distribution replaced, the two changed modules named, the new field checked on the installed package.
- **[10b](10b-count-the-gradient-value-table.md)** (Opus), items X1–X5: the declaration, 10's spec,
  coverage and store tests extended (a named exception to README §5 rule 7), a scalars-only gradient
  instanton added to the integration store, the report's counts; closes the issue, now assigned to it.
- **[11](11-rehearse-through-both-packages.md)** amended: its gate (10a and 10b reviewed; `v0.5.0` in
  the venv), its provenance line, G4's record and its counts follow; nothing else.
- README: §0.6 (new), §2, §2.1, §2.2 (10a, 10b, 11), §4.4, §5 rule 7, §6.1 (U12), §6.3 and §7.

`[gci-value-table-outside-the-inventory]` is assigned to 10b (its §3 row and its index row), and
stays open until 10b lands; `.documents/OPEN-ISSUES.md` follows in this commit (60 open, 28 closed,
unchanged).

### 5.26 After prompt 10a (2026-10-22)

- **Landed:** `80d99a7`, results note
  [`10a-pin-datastorekit-v0.5.0.md`](../../.documents/dk-and-rpk-migration/10a-pin-datastorekit-v0.5.0.md).
  **COMPLETE:** K8-K11 hold; no code or test changed; no issue opened, so
  `.documents/OPEN-ISSUES.md` is unchanged (60 open, 28 closed).
- **K8.** `requirements.txt:16` is `datastorekit @ git+https://github.com/ds283/DatastoreKit@v0.5.0`, replaced
  in place; no other line changed (73 lines).
- **K9.** The dry run reported `datastorekit-0.5.0` alone; the install, run once, uninstalled
  `datastorekit-0.4.0` and installed `datastorekit-0.5.0`, and touched nothing else. pip's `Resolved … to
  commit 6a6809d5…` names the tag object; the commit is `f47b9a25…`. `raypoolkit` was re-resolved, not
  reinstalled. pip itself was not upgraded.
- **K10.** `pip freeze` differs from the saved one by the one `datastorekit` line (`c8570e84…` to
  `f47b9a255e9ad58e0d0eaf85644f53b575884d31`); `pip check` is clean; `direct_url.json` is a VCS record at that
  commit, requested `v0.5.0`, no `dir_info`; the 21 modules equal `git archive v0.5.0`'s byte for byte, and
  exactly two, `store_inventory.py` and `store_fingerprint.py`, differ from the saved `v0.4.0` files (all 21 have
  new mtimes: the replacement rewrote them); `tests/` is not installed. The provenance line is
  `>> packages: datastorekit 0.5.0 (https://github.com/ds283/DatastoreKit@f47b9a255e9ad58e0d0eaf85644f53b575884d31, requested v0.5.0); raypoolkit 0.2.0 (https://github.com/ds283/RayPoolKit@eaef0ce60e2fc354bb32f0ad576010e6a83c1976, requested v0.2.0)`.
- **K11.** On the installed package (imported from the venv's `site-packages`): `InventorySpec.extra_values`
  and `Record.extra_value_counts` default empty, `ENCODING_FORMAT` is 1, `as_json` carries
  `extra_value_counts` only when not empty; SI's 24 classes come in 10's order and no SI spec declares the field;
  a registry copy naming `GradientCoupledInstantonProfile` in both `values` and `extra_values` is refused by
  `inventory_classes`, naming the class and the table; `tests/test_tables_to_drop.py` 9 passed (U5 unmoved).
- **Suites:** 730 (729 passed, 1 skipped) and 67 (66 passed, 1 skipped), as 10's.
- **Rollback:** `git revert` of `80d99a7` **plus** `./venv/bin/pip install -r requirements.txt` after the
  revert, which pip resolves to `v0.4.0` (`c8570e84…`) (README §4.4). The revert alone leaves `v0.5.0` in the venv.

**Orchestrator review of prompt 10a (2026-10-22)**, by orchestrator note
[`prompt-10a.md`](orchestrator/prompt-10a.md), at `80d99a7`. All ten checks pass, read from the venv. The residue is
fixed in this follow-up (records only); nothing is opened.
- **(1) Scope.** 3 files: `requirements.txt`, the results note and the board. One commit of the agent's on `3fd8778`, no
  amend in the reflog, no other branch; `git status` clean; no scratch file in the repository.
- **(2) K8.** One line replaced at `:16`, `@v0.4.0` → `@v0.5.0`; 73 lines.
- **(3) The freeze.** Against the pre-dispatch copy: the `datastorekit` line alone, `c8570e849334…` → `f47b9a255e9a…`;
  83 lines. `pip check` clean; pip still 26.0.1. `raypoolkit`'s 16 files keep their pre-dispatch mtimes and sizes.
  site-packages differs from the pre-dispatch listing by `datastorekit-0.4.0.dist-info` → `datastorekit-0.5.0.dist-info`
  only.
- **(4) The origin.** `direct_url.json`: `url` `https://github.com/ds283/DatastoreKit`, `commit_id` `f47b9a255e9a…`,
  `requested_revision` `v0.5.0`, `vcs` `git`, no `dir_info`. `INSTALLER` `pip`; the only `.pth` is `_virtualenv.pth`; no
  `__editable__` or `.egg-link`.
- **(5) The files.** The same 21 `.py` files as `git archive v0.5.0`'s, none different under `cmp`; no `tests/`, no data
  file. `RECORD`: 42 `datastorekit/` entries (21 modules, 21 `.pyc`), every hash matching. Against the SHA-256 of the
  `v0.4.0` modules taken before dispatch: **exactly `store_fingerprint.py` and `store_inventory.py` differ**, the other 19
  hash the same.
- **(6) Import and helper.** The import one-liner prints `False`; `sharded_store --help` exits 0. The helper gives
  `datastorekit` `0.5.0`, `f47b9a255e9a…`, `v0.5.0`, `editable: False`, `raypoolkit` unchanged, and prints the prompt's line.
  `pip show`: `Version: 0.5.0`, `Requires: ray, sqlalchemy`.
- **(7) K11 replayed.** The orchestrator's `k11_proto.py`, run against `site-packages`, prints the same as it did on the
  tag's archive before dispatch (the import path aside); `tests/test_tables_to_drop.py` 9 passed. The agent's
  `k11_10a.py`, read: run under `python -I`, it asserts its import is from `site-packages`, appends SI's root itself, edits
  nothing, wraps the GCI entry with `dataclasses.replace`, and asserts the class order and the error's text.
- **(8) The pip account.** The note quotes `Would install datastorekit-0.5.0`, the uninstall of `datastorekit-0.4.0` and
  `Successfully installed datastorekit-0.5.0`, nothing else (the agent's `install.txt` agrees), both `Resolved …` lines
  (`6a6809d5…`, `4e7eb153…`) as tag objects, and `raypoolkit` re-resolved.
- **(9) Hygiene.** DatastoreKit `2900d82` and RayPoolKit `17029d9`, clean. The 17 store files and all 835 entries under
  `~/ScienceData/` keep their pre-dispatch mtimes and sizes. No Ray process after the suites; the lock free.
  - *An incident, harmless.* The agent's first write of the results note was `python3 - <<E`, an unquoted heredoc, so the
    shell tried 17 backticked spans as commands; by its account all were bare names or paths (`datastorekit`, `tests/`,
    `requirements.txt:16`) and failed with "command not found" or "permission denied". The evidence agrees: no command
    span in the committed note begins a command that could have changed anything (`ray` is not on `PATH`), the reflog has
    only the one commit, and the venv, the stores and the other repositories are as above. The note was rewritten from a
    quoted template.
- **(10) The suites and the records.** The agent's 730 and 67. The orchestrator re-ran both at `80d99a7` (19:28 BST, load
  16–60): default **730 (729 passed, 1 skipped)**, 39.2 s; integration **67 (66 passed, 1 skipped)**, 59.9 s. The results
  note follows README §5.1, every §2 check with its command and output and K11's script whole; the board has the §1 row,
  K8–K11, the header and this section with the rollback.
  - *Residue, fixed here:* "the commit that adds the (results) note" → `80d99a7` (board ×3, results note ×2); the header's
    "10a landed" reads "landed and reviewed"; this note added to the list of orchestrator notes; the campaign's line in
    `.prompts/INDEX.md`.
- **The deviations are accepted:** D1–D4 are the brief's corrections, D5–D7 sound choices (D7's `python -I` is a stronger
  guard than the brief asked for).
- **Handed on to 10b.**
  - Every driver now prints `>> packages: datastorekit 0.5.0 (…@f47b9a255e9a…, requested v0.5.0); raypoolkit 0.2.0
    (…@eaef0ce6…, requested v0.2.0)`.
  - On the installed package SI declares no `extra_values`, `inventory_classes` gives the 24 classes in 10's order, and it
    refuses the profile named in both slots with `ValueError: inventory_classes(): GradientCoupledInstanton names
    GradientCoupledInstantonProfile both as its value table and in its extra_values`: the message 10b's third breakage
    should meet.
  - 10b's suites start from 730 and 67; `slow` from S1's 69.

### 5.27 After prompt 10b (2026-10-22)

- **Landed:** this commit, results note
  [`10b-count-the-gradient-value-table.md`](../../.documents/dk-and-rpk-migration/10b-count-the-gradient-value-table.md).
  **COMPLETE:** X1–X5 hold; no stop condition met; `[gci-value-table-outside-the-inventory]` closed (§4); nothing
  opened.
- **X1.** `GradientCoupledInstanton`'s spec gains `extra_values={"GradientCoupledInstantonValue": "instanton_serial"}`
  (`Datastore/SQL/ObjectFactories/GradientCoupledInstanton.py:181`), beside `values=`; its comment (`:148-155`) says
  the table is counted as a further value table, 0 for a row stored without full values. Nothing else in the factory.
- **X2.** `tests/test_inventory_specs.py` (12, in place): `EXPECTED_SPECS` and `_as_table` carry `extra_values` for
  all 24 (`{}` for 23); the column test checks the extra table, its column and its foreign key, and that it met every
  extra table the spec table names; `_slot_tables` reads a mapping's keys; `GradientCoupledInstantonValue` moves from
  `EXCLUDED` (now empty) to `READ_THROUGH` by `extra_values`, which `SLOTS` names; the placement is **(24, 6, 0)**; the
  stale-exclusion case takes the class out of `READ_THROUGH` for itself, so its assertion is unchanged.
- **X3.** `tools/inventory_report.py` prints each further table's rows by its name after the value rows, on every
  record line and the class summary (`| 5 value rows; 3 GradientCoupledInstantonValue rows`), 0 as 0; a class with
  none prints as 10's. `tests/test_inventory_report.py` 10 → 12 (`test_a_further_value_table_is_counted_by_its_name`,
  `test_a_class_with_no_further_value_table_prints_as_before`); its ten tests and `_rec` unchanged by `ast`.
- **X4.** `tests/test_inventory_store.py` (4, in place): a third gradient instanton at δN★ 1.5, made scalars-only by
  `set_store_full_values(False)` before `object_store` with `_values` populated; read back, keyed by δN★, `(True, 5,
  {…: 3})`, `(True, 5, {…: 0})`, `(True, 0, {…: 0})`, `problems == ()`; `GradientCoupledInstanton` 2 → 3 records,
  no other count moves; the report's two gradient literals in the new format and the `1.5` line added; each
  `main.py --inventory` test asserts a printed count.
- **Fingerprint and U5.** On the test's store, built by its own script in the scratch directory: with the declaration
  and without it (the instance's spec wrapped in a scratch script), only `GradientCoupledInstanton`'s class digest
  differs (1 of 24); overall `ffac9333…8658` → `e3437a9b…7c78`, class `5b88f64c…ef74` → `e342c0aa…12ec`, the
  prototype's four digests. Recorded nowhere but the results note. U5: 31 of 31 sets equal in `dependent_tables`,
  decision and message, before and after (10 closed).
- **Verification.** Suites: default **732 (731 passed, 1 skipped)**, integration **67 (66 passed, 1 skipped)**: 10a's
  730 and 67, + the two report tests. No `slow` run (no `ComputeTargets/` change). `ruff` F401/F811/F821: 0 at the gate
  and 0 now in each of the five files. `main.py --inventory` and `--show-all` on the scratch store: exit 0, stderr
  empty, the store's files unchanged; both outputs whole in the results note. Breakages 1–5 caught (the identity,
  column and coverage tests; the column test; the package's `inventory_classes` refusal; the new report tests;
  coverage's "in more than one place").
- **Found, not acted on:** a store with no gradient rows prints and fingerprints as before (read from the code); a spec
  with `extra_values` and no `values` would print the extra counts alone (SI has none); DatastoreKit's spec-guard
  advice (leave out an empty `extra_values`) is for the RunRegistryKit adoption.
- **Rollback:** `git revert` of this commit alone; nothing in the venv (README §4.4).
- **Deviations:** the board section (correction 1); the grep's 51 lines (3); the report literals (4); the report's
  format (5); the column test's own non-vacuity check; the stale-exclusion literal (8); two report tests (7, 11); the
  gradient read-back keyed by δN★; one assertion in each `main.py` test; `ruff format` on the three test modules (only
  added lines reflowed); breakage 4 removes both prints; the docstrings and comments (6). No `UNINTENDED DRIFT`.
