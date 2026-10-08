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
`.documents/grid-sampling/`). None of the five has an `IMPLEMENTATION_STATE.md`
board. Every campaign from now on opens one in its prompt folder (see
`CLAUDE.md`).

**Last updated:** 2026-10-08 · 5 campaigns: 1 halted, 4 complete; 2 planned.
Open-issue counts taken from `OPEN-ISSUES.md` on 2026-10-08.

| Campaign | Status | Opened → last activity | Owns | Results and records | Open issues (§ of `OPEN-ISSUES.md`; rows) |
|---|---|---|---|---|---|
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
`9f39645`, `f4080f5` and the document-corrections commit that follows them.
Phase 1 (the LaTeX rewrite to the 20 July position) is done: `e511f74`, moved
to `notes/onion-model/` in `4c47faf`. The names below are working names; no
folder exists yet.

| Phase | Working name | Scope | Starts from | Open issues |
|---|---|---|---|---|
| 2 | `fullinstanton-hamiltonian` | One Fokker–Planck Hamiltonian module, differentiated at runtime with JAX (complex-step as the conformance test), driving FullInstanton's response sector; the `∂D/∂u` (Riccati) decision; re-run the June grids | `RECONSTRUCTION.md` B.10 (prompts "25-00" to "25-04", to be renumbered from 00), decisions D0.1 and D0.5; tex `sec:hfp`, `sec:fullinstanton-eqs` | §2 (4); §1 `[dD-du-riccati-decision]` |
| 3 | `onion-rebuild` | Discrete Hamiltonian `H_h` for the onion in the `V'` measure, core anchor and chain-rule `Δ̇s`, `L(gπ̃)` ordering, response sector by differentiation, single SAT on `w_in` in the `H_μ` norm, Hamiltonian-structure check. Acceptance: `τ`-independence, then `n`-convergence | tex `sec:coordinate` to `sec:collocation-scheme`; `RECONSTRUCTION.md` Parts B–D | §3 (11 of 12); §1 rows owned by P3 |

Phase 4 (bringing the tex numerics sections to the scheme actually built) has
no campaign of its own; it closes the `todo`s P3 leaves behind.

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
