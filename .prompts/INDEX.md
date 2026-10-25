# Campaign index

One line per campaign under `.prompts/`. It says which campaigns are live,
when each opened and was last touched, what it owns, where its results are
recorded, and where its open issues are indexed. It is an index: the prompts
and results notes hold the substance, and if this file and
[`.documents/OPEN-ISSUES.md`](../.documents/OPEN-ISSUES.md) disagree, the
issues file is right. Add a line when a campaign folder is created and change
its status when the campaign closes. The open-issue column is a snapshot of
`OPEN-ISSUES.md` on the date below; the section pointer is the durable part.

Campaigns here keep their prompts in `.prompts/<campaign>/` and their results
notes in `.documents/<campaign>/` (the June science campaign's are in
`.documents/grid-sampling/`). None of the five campaigns before October has an
`IMPLEMENTATION_STATE.md` board. Every campaign from then on opens one in its
prompt folder (see `CLAUDE.md`); `dk-and-rpk-migration` is the first.

**Last updated:** 2026-10-25 · 8 campaigns: 0 ready, 0 live, 1 halted, 7 complete; 2 more
planned without a folder.
Open-issue counts taken from `OPEN-ISSUES.md` on 2026-10-08, on 2026-10-23 for
`dk-and-rpk-migration`, and on 2026-10-25 for `rrk-adoption`.

| Campaign | Status | Opened → last activity | Owns | Results and records | Open issues (§ of `OPEN-ISSUES.md`; rows) |
|---|---|---|---|---|---|
| [`rpk-v030-adoption`](rpk-v030-adoption/README.md) | complete 1 / 1 on 2026-10-25, closed at the review of 01: the pin at `v0.3.0` (`3d6328e`), then `ray_cluster.sh` on `raypoolkit.rehearsal_lock` (`6c60b81`), checked against a scratch `HOME` and by one start and stop under the real lock; reviewed (board §5.2, residue `ea17836`); no issue opened. README §4's merges made at the user's instruction (2026-10-25): `main` fast-forwarded to `bb2d953`, then merged into `rrk-adoption` before its 02 (board §5.3); nothing pushed; SI's part of RayPoolKit's G2 is drafted in the results note. Planned 2026-10-25: RayPoolKit `v0.3.0` evaluated at `7071bb8` and found a small change (README §0.3): `RayWorkPool` unchanged, the shared rehearsal lock now the package's `raypoolkit.rehearsal_lock` at `~/.raypoolkit/rehearsal-lock`. SGK moved alone the same day at the user's ruling (its U2), so SI moves soon, and until 01 lands its cluster starts only once the new lock is checked absent (README §0.2). No ruling needed; C1–C10 proposed. Branch `rpk-v030-adoption` cut from `main` at `1c223e8`; after review `main` is fast-forwarded to it and merged into `rrk-adoption` before that campaign's 02 (C1). Board: [`IMPLEMENTATION_STATE.md`](rpk-v030-adoption/IMPLEMENTATION_STATE.md) | 2026-10-25 | the `raypoolkit` pin, the lock half of `ray_cluster.sh` | [`.documents/rpk-v030-adoption/`](../.documents/rpk-v030-adoption/) | —; 0 |
| [`rrk-adoption`](rrk-adoption/README.md) | complete 5 / 5 (01–05; R1–R7, U1, U2, P1–P14) on 2026-10-25, after being live from 2026-10-23: RunRegistryKit `v0.2.0` evaluated at `8b4f615` and found adoptable, core and store layer (README §0.3); R1–R7 ruled by the user (a wrapper driver, `main.py` unchanged and the provenance helper kept; sidecars by a person, as ChamPBH and SGK; no plot script or `--inventory` registered; stores in `var/datastores/`; cut from `main` after `dk-and-rpk-migration` was merged); U1 (a `SessionStart` discovery hook) and U2 (the hard-kill route rehearsed) ruled as recommended; P1–P14 stand. `main` fast-forwarded to `1c223e8` (not pushed); branch `rrk-adoption` cut from it; prompts 01–05 written. 01 landed (`60687f0`, `7071bb8`): the pin, config, rules and hook. 02 landed (`0fcaf7c`) and reviewed: the fingerprinter, its format guard and the golden fingerprint `e3437a9b…7c78`. 03 landed (`16e1cc1`) and reviewed: the wrapper `RunDrivers/registered_run.py` and its 106 tests, 104 in the default selection and 2 `integration`; `[default-suite-starts-ray-in-process]` opened at the review. 04 landed (`29705f2`) and reviewed: the rehearsal on SI's isolated cluster, four registered builds `done`, `killed`/143, `lost` by `end` after a `SIGKILL`, and `done`; the resumed store and RH2's `11-reference` equal to the reference bit for bit, fingerprint `a9f716fb…1ea7`; gate R held; record `.documents/rrk-adoption/verification.md` §1. 05 landed (`5bd486d`) and reviewed: the three descriptive documents describe the registry (`INFRASTRUCTURE.md` §13), `CLAUDE.md` and `test-selection.md` carry the final counts, the stale prose (P12) is present tense with `utilities.py`'s docstring `ast`-equal, RunRegistryKit's two gate records (`extraction` G4, `interrupted-runs` G3) are drafted for the user to commit there (`verification.md` §2), and the handover to Phase 2 is `verification.md` §3. Final suites: default 848 (847 passed, 1 skipped), `integration` 72 (71 passed, 1 skipped), `slow` 69 (not run: no prompt touched its paths). Adopts `runregistrykit[stores]` `v0.2.0`, with `datastorekit` `v0.5.0` and `raypoolkit` `v0.3.0` unmoved. Not yet merged into `main` (R7: the user's). Board: [`IMPLEMENTATION_STATE.md`](rrk-adoption/IMPLEMENTATION_STATE.md) | 2026-10-23 → 2026-10-25 | the `runregistrykit` pin, `runregistrykit.toml`, `var/`, `.claude/settings.json`, `config/fingerprint.py`, `RunDrivers/`, the run-registry rules | [`.documents/rrk-adoption/`](../.documents/rrk-adoption/) | §6b; 1 |
| [`dk-and-rpk-migration`](dk-and-rpk-migration/README.md) | complete 15 / 15 (01–12, 01a, 10a, 10b; U1–U12, P1–P19) on 2026-10-23, after being live from 2026-10-12: plan reviewed, U1–U8 ruled, prompts 01–04 and 01a written, 01 and 01a landed (`84a5cfc`, `3556148`) and reviewed; U9 (2026-10-12): an isolated Ray cluster and a rehearsal lock shared with ChamPBH and SGK; U10 (2026-10-19): pin DatastoreKit `v0.4.0`. U11 (2026-10-20): 02's first attempt stopped after its gradient solves ran over five hours unconverged; no rehearsal builds the gradient branch. 02 landed at its third attempt (`5868231`) and was reviewed: RH0 is bitwise reproducible in both modes, so RH1 and RH2 are held to bitwise equality. Prompts 05–07 written (2026-10-20). 03 landed (`5396a3d`) and was reviewed: `raypoolkit` `v0.2.0` pinned and installed, one distribution added. 04 landed (`ef13445`) and was reviewed: `RayTools/` deleted, the drivers import `raypoolkit`, RayPoolKit G4 holds; one issue opened for 12. 05 landed (`875cf41`) and was reviewed: SI's registry, drop groups and batch sizes are `config/datastore.py`, the 15 vectorized gets pass the mapping; one issue opened for 09. 06 landed (`5e41ce8`) and was reviewed: `InflatonTrajectory`'s prune deletes its value rows, every hook takes `prune`, and the factories declare `owner_column`, `validated_column` and `revalidate` for DatastoreKit; `[inflaton-trajectory-prune-orphans-value-rows]` closed. 07 landed (`0527480`) and was reviewed (2026-10-21): RH1, at 06's tree through `raypoolkit`, equals RH0 bit for bit in both modes, and that commit is tagged `pre-datastorekit` (annotated; pushed by the user 2026-10-21). Prompts 08–11 written (2026-10-21). 08 landed (`1b1ca6d`) and was reviewed: `datastorekit` `v0.4.0` pinned and installed, one distribution added; SI's 30 registry entries instantiate on the installed base. 09 landed (`f4da58f`) and was reviewed: SI's datastore layer deleted, every pool the package's, unclosed `--drop` groups and `--inventory` refused before Ray; `[config-datastore-cannot-be-imported-before-the-layer]` closed. 10 landed (`e2c7b22`) and was reviewed: the inventory is `read_inventory` over 24 `inventory_spec`s, printed by `tools/inventory_report.py` before Ray; every registered class covered (U8); `[show-all-flag-unused]` closed, `[gci-value-table-outside-the-inventory]` opened. At SI's request DatastoreKit released `v0.5.0` (a second value table per spec); U12 (2026-10-22): 10a pins it and 10b declares the table, both before 11, which is amended to rehearse `v0.5.0`. 10a landed (`80d99a7`) and was reviewed: `datastorekit` `v0.5.0` pinned and installed in place of `v0.4.0`, the one distribution replaced; only `store_inventory.py` and `store_fingerprint.py` differ, and the new field behaves as the release says on the installed package. 10b landed (`19716cd`) and was reviewed: `GradientCoupledInstanton`'s spec counts `GradientCoupledInstantonValue` as a further value table (`extra_values`), every registered class covered and none excluded, the report prints the count; `[gci-value-table-outside-the-inventory]` closed. 11 landed (`2179854`) and was reviewed: RH2, at 10b's tree through both packages, equals RH1 (and so RH0) bit for bit in both modes; the resume pruned only unvalidated rows; `shard_key_audit`, `sharded_store copy` and `delete_store` behave; DatastoreKit G4 holds for SI. 12 landed (2026-10-23): `CLAUDE.md`, the rules and the three architecture documents describe the packages, the prose in code is corrected (`ast`-equal), the two G4 records are drafted for the packages' boards, the handover to Phase 2 is `verification.md` §4.5, and `[test-counts-stale-in-claude-md]` and `[pool-prose-stale-after-raypoolkit-adoption]` are closed. Final suites: default 732 (731 passed, 1 skipped), `integration` 67 (66 passed, 1 skipped), `slow` 69. Adopts `raypoolkit` `v0.2.0` and `datastorekit` `v0.4.0` (U10, 2026-10-19), then `v0.5.0` (U12, 2026-10-22), which carry `v0.3.0` (released 2026-10-12 at the campaign's request); ran before Phase 2 (U7). Merged into `main` 2026-10-23 (P15): a fast-forward to `1c223e8`, not pushed (board §5.31). Board: [`IMPLEMENTATION_STATE.md`](dk-and-rpk-migration/IMPLEMENTATION_STATE.md) | 2026-10-11 → 2026-10-23 | `RayTools/` and the layer files of `Datastore/` (deleted), `config/datastore.py`, the pool constructions, `tools/compare_stores.py`, `tools/inventory_report.py` | `.documents/dk-and-rpk-migration/` (created by its prompt 01) | §6a; 4 |
| [`gradient-coupled-instanton`](gradient-coupled-instanton/) | **halted** 2026-07-10 after prompt 28. The code implements the 6–10 July scheme, which the 10–20 July analysis superseded; the model in force is the one in `notes/onion-model/onion_model.tex`. To be replaced by the planned onion rebuild. | 2026-07-04 → 2026-07-10 (prompt 28 committed 2026-10-08) | `ComputeTargets/GradientCoupledInstanton/`, `Numerics/` (LGL collocation, onion coordinate), `tools/diagnostics/GradientCoupledInstanton/` | [`.documents/gradient-coupled-instanton/`](../.documents/gradient-coupled-instanton/) (notes 21–28, planning, implementation review); [`HANDOFF-gradient-coupled-instanton.md`](../.documents/handoff-notes/HANDOFF-gradient-coupled-instanton.md) (9 July); [`handoff-notes/2026-07-10/`](../.documents/handoff-notes/2026-07-10/) | §1, §3; 12 in §3 |
| [`gradient-coupled-plotting`](gradient-coupled-plotting/00-README.md) | complete 13 / 13 (U1–U3, P1–P8, plus P2b) | 2026-07-07 → 2026-07-09 | `plotting/`, `plot_GradientCoupledSolutions.py`, the GCI parity scalar columns | [`.documents/gradient-coupled-plotting/`](../.documents/gradient-coupled-plotting/) (design and authoring brief) | —; 0 |
| [`sparse-sampling`](sparse-sampling/) | complete 16 / 16 (01–14, 02b, 12b). Its science results are provisional: every `S_MSR` number used the defective FullInstanton response sector. | 2026-06-21 → 2026-06-23 (analysis in chat to 2026-06-25) | DOE / Latin-hypercube sampling pipeline, scalars-only instanton and compaction targets, GP regression, noise-amplitude scalars, `r_max`/`r_peak` split | [`.documents/grid-sampling/`](../.documents/grid-sampling/) (three handoffs, marked where superseded; the recovered 24 June session summary and 25 June analysis protocol); [`summary-F-june-science.md`](../.documents/handoff-notes/2026-10-08/summary-F-june-science.md) | §2, §4, §5; 1 in §2, 2 in §4, 1 in §5 |
| [`metadata-annotations`](metadata-annotations/) | complete 2 / 2 | 2026-06-21 | provenance footers and MSR-action annotations on plots | — | —; 0 |
| [`base-implementation`](base-implementation/) | complete: prompts 01–04 and 02a, plus seven ad hoc `prompt_*` fixes | 2026-06-15 → 2026-06-24 | `InflatonTrajectory`, `FullInstanton`, `SlowRollInstanton`, `CompactionFunction`, the datastore and Ray pipeline | [`architecture-summary.md`](../.documents/architecture-summary.md), [`INFRASTRUCTURE.md`](../.documents/INFRASTRUCTURE.md), [`NUMERICAL_SCHEMES.md`](../.documents/NUMERICAL_SCHEMES.md), [`handoff_instanton_boundary_conditions.md`](../.documents/handoff-notes/handoff_instanton_boundary_conditions.md) (marked where superseded); [`summary-E-june-pipeline.md`](../.documents/handoff-notes/2026-10-08/summary-E-june-pipeline.md) | §2, §4; 3 in §2, 5 in §4 |

Numbering notes for `gradient-coupled-instanton`: prompt 16 (decoupling
structural test, issued 7 July) has no file; there are two prompt-24 files (the
original and the revised deep-dive); prompt 28's file is named `…-8t-and-11`
but its results note is `…-8t-and-13` (the note explains the renumbering);
`OLD-0003-extraction-cache-interface.md` is retired.

## Planned

The plan agreed on 8 October 2026, in order. Phase 0 (record and tidy) is done:
`9f39645`, `f4080f5` and `416d1e0`.
Phase 1 (the LaTeX rewrite to the 20 July position) is done: `e511f74`, moved
to `notes/onion-model/` in `4c47faf`. The names below are working names; no
folder exists yet.

| Phase | Working name | Scope | Starts from | Open issues |
|---|---|---|---|---|
| 2 | `fullinstanton-hamiltonian` | One Fokker–Planck Hamiltonian module, differentiated at runtime with JAX (complex-step as the conformance test), driving FullInstanton's response sector; the `∂D/∂u` (Riccati) decision; re-run the June grids | `RECONSTRUCTION.md` B.10 (prompts "25-00" to "25-04", to be renumbered from 00), decisions D0.1 and D0.5; tex `sec:hfp`, `sec:fullinstanton-eqs` | §2 (4); §1 `[dD-du-riccati-decision]` |
| 3 | `onion-rebuild` | Discrete Hamiltonian `H_h` for the onion in the `V'` measure, core anchor and chain-rule `Δ̇s`, `L(gπ̃)` ordering, response sector by differentiation, single SAT on `w_in` in the `H_μ` norm, Hamiltonian-structure check. Acceptance: `τ`-independence, then `n`-convergence | tex `sec:coordinate` to `sec:collocation-scheme`; `RECONSTRUCTION.md` Parts B–D | §3 (11 of 12); §1 rows owned by P3 |

Phase 4 (bringing the tex numerics sections to the scheme actually built) has
no campaign of its own; it closes the `todo`s P3 leaves behind.

`dk-and-rpk-migration` (above, planned 2026-10-11) ran before Phase 2 (its
README §0.3, U7, ruled 2026-10-12), so that Phase 2 builds its stores through
the packages. Phase 2's first prompt reads the June and July stores at the tag
`pre-datastorekit` (made on `0527480`, pushed by the user 2026-10-21), from a
worktree that uses the main checkout's venv: the handover is
`.documents/dk-and-rpk-migration/verification.md` §4.5.

`rrk-adoption` (above, planned 2026-10-23, complete 2026-10-25) was the next
infrastructure campaign (`dk-and-rpk-migration` README §7). It came before
Phase 2's first build, so that Phase 2's rebuilds are registered runs: the
handover is `.documents/rrk-adoption/verification.md` §3. Phase 2's first
prompt reads the June stores at the tag and does not need it.

## Records outside any campaign

- [`notes/onion-model/onion_model.tex`](../notes/onion-model/onion_model.tex) —
  the reference for how the calculation should be performed (20 July position,
  8 October decisions).
- [`.documents/handoff-notes/2026-10-08/`](../.documents/handoff-notes/2026-10-08/) —
  `RECONSTRUCTION.md` of the April–July chat threads, its six summaries, and
  the LaTeX rewrite brief. Raw transcripts are under `.documents/transcripts/`
  (git-ignored, local only).
- [`assemble-context.md`](assemble-context.md) — the standing prompt that
  builds the `claude-context/` bundle, its file map (`FILE_MAP.md`) and the
  narrative `NUMERICAL_SCHEMES.md` for a claude.ai conversation.
