# Open issues — project-wide index

**Last updated:** 2026-10-08 · **41 open**, 23 closed. Seeded from
[`RECONSTRUCTION.md`](handoff-notes/2026-10-08/RECONSTRUCTION.md) Parts A0–D
and D0, the open-issue `todo`s of
[`onion_model.tex`](../notes/onion-model/onion_model.tex) as rewritten in
`e511f74`, the 10 July status notes, and the prompt-28 results note.

This file exists so that an issue raised in one place is not lost when work
moves on. It is an **index, not a record**: one line per issue, pointing at
the document that holds the argument, the measurements and the next step.
Do not put issue content here. If this file and its source disagree, the
source is right.

**No campaign has a status board yet; every future campaign will.** Until a
campaign opens one, the source column points at the reconstruction, a tex
`todo`, or a results note under `.documents/<campaign>/`. When a campaign
opens an `IMPLEMENTATION_STATE.md` board and adopts a row, re-point the row at
the board in the same commit. The campaign index is
[`.prompts/INDEX.md`](../.prompts/INDEX.md).

> **Maintenance rule.** Whenever an issue is opened, narrowed or closed (in a
> board, a results note, a tex `todo`, or by a decision), update this file
> **in the same commit**: add the line, move it between sections, or move it
> to §7, and correct the count and the date above.

**Source abbreviations.**
**R** = [`handoff-notes/2026-10-08/RECONSTRUCTION.md`](handoff-notes/2026-10-08/RECONSTRUCTION.md) (section or "Open n");
**tex** = [`notes/onion-model/onion_model.tex`](../notes/onion-model/onion_model.tex) (by `\label`);
**SCS** = [`handoff-notes/2026-07-10/SAT-CLOSURE-STATUS.md`](handoff-notes/2026-07-10/SAT-CLOSURE-STATUS.md);
**HSS** = [`handoff-notes/2026-07-10/HFP-STRUCTURE-STATUS.md`](handoff-notes/2026-07-10/HFP-STRUCTURE-STATUS.md);
**HCalc** = [`handoff-notes/2026-07-10/HFP-CALCULATION.md`](handoff-notes/2026-07-10/HFP-CALCULATION.md);
**HB** = [`handoff-notes/HANDOFF-gradient-coupled-instanton.md`](handoff-notes/HANDOFF-gradient-coupled-instanton.md);
**P28** = [`gradient-coupled-instanton/28-tau-study-diagnostics-8t-and-13.md`](gradient-coupled-instanton/28-tau-study-diagnostics-8t-and-13.md);
**sumF** = [`handoff-notes/2026-10-08/summary-F-june-science.md`](handoff-notes/2026-10-08/summary-F-june-science.md).

**Owners** are phases of the plan of 8 October 2026 (see `.prompts/INDEX.md`,
"Planned"): **P0** record and tidy (done 8 October 2026); **P2** FullInstanton Hamiltonian module;
**P3** onion rebuild; **P4** tex numerics brought to the final scheme. Also
**David** (a decision that is the user's), **research** (no code owner;
belongs to the paper or later work) and **unowned**.

---

## 1. Model and physics questions

Decisions and research questions about the model itself. The tex states the
20 July position and carries most of these as `todo`s.

| Issue | Source | Owner | Hook |
|---|---|---|---|
| `[sat-inside-discrete-hamiltonian]` | R Open 2, B.7, B.9; tex `sec:discrete-hamiltonian` todo | P3, decide first | Whether the core penalty is a term of the discrete Hamiltonian `H_h` (dual consistency by construction) or is added to the assembled RHS outside it (keeps `H_h` free of `abs`, Hamiltonian check exact). Either way the penalty must be derivable from a boundary term of the discrete action. |
| `[sat-in-core-forcing-for-delta-s-rate]` | R Open 3, B.9; tex `sec:coordinate` todo | P3 | Whether the penalty belongs in the core forcing when `Δ̇s` is evaluated. Argued no: a stabiliser that vanishes at convergence and would add a second linear loop. |
| `[dD-du-riccati-decision]` | R Open 4, B.10; tex `sec:onion-eqs` and `sec:open-issues` todos | P2 | Whether to retain `∂D/∂u`. If retained, the backward pass is a matrix Riccati flow, `r = λr̃` linearity is lost, and caustics `M₂ → 0` are a new failure mode; direct integration versus the `4×4` symplectic block linearisation. FullInstanton decides it. |
| `[response-indicial-analysis]` | R Open 5, B.4; tex `sec:open-issues` todo | research | Frobenius analysis of the response sector at `Δs → 0` in the `V'` convention. A first attempt did not close. Until it does, `α` cannot be reduced on analytic grounds. |
| `[core-scale-mass-attribution]` | R Open 6, B.6; tex `sec:core-scale` todo | David | GCI gives the core the unperturbed horizon scale at `N_final`; FullInstanton + `CompactionFunction` give a `δN★`-dependent perturbed one. A mass-attribution difference, not a threshold one. The 14 July comparison used the background anchor and must be redone under the core anchor. |
| `[msr-spectral-bridge]` | R Open 7, B.2, A0.1; tex `sec:open-issues` todo | research | How the fixed-profile instanton action relates to the first-passage `Λ₀ δN★`. `H_FP → −Λ₀` was withdrawn; the Gaussian expansion gives a quadratic action and stalled on the diagonalisation. The scaffold is the adjoint backward-Kolmogorov eigenproblem. |
| `[bke-density-on-phi-comparator]` | R A0.3, A0.1 | research | David's 24 June proposal: solve the backward Kolmogorov equation with `δ(φ − φ₀)` at `K = 0`, so that `Q` is a density on `φ`, "the object comparable to our sum over instantons". Posed, not attempted. Same family as the row above. |
| `[smsr-2d-probability-interpretation]` | tex `sec:open-issues` todo; R A0.1 | research | `S_MSR` (2D) and `S_MSR` (1D) are probabilities of different events. The right comparison once the gradient is on is unresolved, and blocks presenting "the corrected PBH formation probability". |
| `[largest-time-equation-stochastic]` | tex `sec:open-issues` todo | research | The factorisation at `N_final` (a functional delta tying forward and backward fields) is not derived for the MSR path integral with nonlinear noise and gradient coupling. The numerical check is `[n-turn-insensitivity-test-never-run]` in §2. |
| `[no-level-1-calculation]` | R A0.1, A0.3 | research | The MSR instanton (Level 2) stitches Level-1 horizon-exit kicks, but no Level-1 calculation at `O(1)` amplitude exists. At large `δN★` the per-step kick is far out on the Gaussian tail and the saddle probably underestimates the probability; `δN★/(σ ΔN)` was never plotted. The Euclidean "end at `Im π → 0`" idea is recorded only in R. |
| `[non-markovian-noise]` | tex `sec:open-issues` todo; R B.2 | research | A diffusion model with memory (Mukhanov–Sasaki mode functions) is non-Markovian and changes the phase space of `H_FP`, not only its coefficients. The present construction is the truncated Markovian problem. |
| `[shell-ends-inflation-before-core]` | R A0.1 | research | A shell reaching the end of inflation before the core is "a genuinely problematic physical situation" (30 June). The model does not handle it and the tex does not mention it. |

## 2. FullInstanton — the Hamiltonian-module pilot (P2)

| Issue | Source | Owner | Hook |
|---|---|---|---|
| `[fullinstanton-bwd-rhs-drops-leading-terms]` | R B.10, A.3; tex `sec:fullinstanton-eqs` | P2 | `bwd_rhs` in `ComputeTargets/FullInstanton.py:151` keeps only `P₂ V''/H²` and `−P₁ + (3−ε)P₂`. The omitted `∂H²/∂φ`, `∂ε/∂u` terms are leading order: for quadratic `V` the only coupling has the wrong sign, and for `V ∝ φ^p` the correct term is `−1/(p−1)` times the coded one. Present in the tree on 8 October. |
| `[hfp-closed-form-audit-not-run]` | R B.10 ("25-00"); SCS §4.5; HSS §3 | P2, first prompt | Zero-compute check on the stored grids: `∂S/∂δN★ = −[λ φ₂(N_total) + D₁₁(N_total) λ²]` against finite differences of `S`. It measures how wrong the June numbers are before any code changes. |
| `[june-smsr-results-provisional]` | R A0.3, C0; sumF §2 | P2, re-run | Every `S_MSR`-bearing June or July number was produced with the defective response sector: the `δN★^1.74 ΔN^−0.72` fit, the 1.2–1.4 exponent, `δN★_th(ΔN)`, the minimum-action locus, the `r_max ≠ r_peak` region, the no-collapse island and the Picard failures from `δN★ ≈ 7`. The kinematic mass law is expected to survive. sumF §2 classifies all 32 claims. |
| `[n-turn-insensitivity-test-never-run]` | tex `sec:open-issues` todo; R A0.1 | P2 | Solve the 1D instanton with the terminal condition at several `N_turn > N_final` and check that the solution on `N ≤ N_final` is unchanged. Cheap; apparently never run. |

## 3. GradientCoupledInstanton — code against the model in the tex (P3)

The tex now states the target scheme. The code still implements the 6–10 July
one, so every row here stays open until the onion rebuild lands.

| Issue | Source | Owner | Hook |
|---|---|---|---|
| `[gci-response-bracket-is-mu-artefact]` | R B.4, B.6; tex `sec:onion-eqs` | P3 | `ComputeTargets/GradientCoupledInstanton/response_rhs.py:183–192` applies `(1−ε_core)[1/Δs − 3/2]`. In the `V'` convention `Z = 0`; the bracket is a convention artefact. |
| `[gci-response-gradient-operator-ordering]` | R B.4; tex `sec:onion-eqs` | P3 | `response_rhs.py:287` computes `e^{−2Δs_loc} L(π̃)`; the variation gives `L(g π̃)`. Two terms of the same order are missing, and the adjoint residual cannot vanish while this stands. |
| `[gci-delta-s-rate-is-background-identity]` | R B.8, B.9; tex `sec:coordinate` | P3 | `delta_s_derivative()` at `Numerics/OnionCoordinate.py:81` returns `1 − ε_core`, a background identity inconsistent with `delta_s()`. The target is the chain-rule `Δ̇s` through the actual core row. It changes `A` in the forward sector and so every `n = 5` solve; `K = 1` is a singularity to guard. Use the tex, not R, for the sign of `K` (R Erratum E1). |
| `[gci-measure-is-not-volume-element]` | R B.8; tex `sec:noise-measure` | P3 | `measure()` at `Numerics/OnionCoordinate.py:91` is `e^{−1.5 Δs y}`, which differs from `V'` by a `Δs`-dependent prefactor that `∂H/∂Δs` must see. |
| `[gci-variation-truncated]` | R B.6 ledger, B.10; tex `sec:onion-eqs` | P3 | The state dependence of `Δs`, `A`, `μ`, `n_count` through the core node, and `∂H²/∂u`, `∂ε/∂u`, `∂(aH)_loc/∂φ`, are absent from the response sector. The target is to differentiate `H_h` with JAX (D0.1, D0.5). |
| `[gci-sectors-not-adjoint]` | HSS §1; R B.1, A.3 (Q2) | P3 | Forward sector SAT-closed with a free core node; response sector hard-eliminates `∂_y π̃ = 0`. The Picard fixed point is the stationary point of no discrete action. Do not transpose the current over-determined operator. |
| `[gci-core-closure-over-determined]` | SCS §2, §5; R A.3 (C1, C3), B.3, B.9; tex `sec:colloc-bcs` todo | P3 | Two core penalties in the flat norm: `φ` toward a live target (derivative-type, since `w D = ½` exactly) and `π` toward a target frozen at the FullInstanton `φ₂` seed. `τ/w ∝ n²`; the forcing at convergence is 2–19× the background terms (Test A). The target is one penalty on `w_in` in the `H_μ` norm. |
| `[gci-n5-n7-solutions-provisional]` | P28; SCS §5; HB §4 | P3, acceptance | All `n = 5` and `n = 7` solutions depend materially on `τ`; no `n ≥ 9` solve converges, so there is no `n`-convergence evidence. The core oscillation in the 24b trajectories (under-resolution or physics) is unexplained. Acceptance after the rebuild: `τ`-independence, then `n`-convergence. |
| `[gci-decoupled-limit-degenerate]` | R A.1; tex `sec:open-issues` todo | P3 | No non-trivial reduction test to FullInstanton exists: with the core eliminated through a Neumann row from background neighbours, `φ_core` is pinned for every `λ`. The rebuild needs a non-degenerate decoupled-limit test against the P2 module. |
| `[gci-extraction-never-run-on-non-flat-profile]` | HB §4 | P3 | `extraction.py` and `scale_assignment.py` have never run on a non-flat profile. |
| `[gci-outer-tol-floor-loose]` | R A.2 | P3 | `OUTER_TOL_FLOOR = 1.0e-2` (`picard.py:359`) is loose for a stationary quantity. |
| `[gci-main-no-store-values-crash]` | R A.2 | unowned | `main.py` crashes with `--no-store-values` together with `--targets homogeneous gradient`. Not reproduced on 8 October. |

## 4. Pipeline, compaction function and scale assignment

Code and physics choices from `base-implementation` and `sparse-sampling`,
outside the instanton solvers.

| Issue | Source | Owner | Hook |
|---|---|---|---|
| `[gstar-offset-in-scale-matching]` | R A0.2, C0 | David | The degrees-of-freedom shift in the scale-matching equation is about `−1.1` in `ln k` for `g*_reh = 106.75`, not "~0.2", and was never agreed to be dropped. `ln_k_phys_Mpc` carries an undocumented offset of about one e-fold. Not in tex `sec:scale-assignment` either. |
| `[r-max-vs-r-peak-mass-estimate]` | R A0.3 | David | When `r_max ≠ r_peak` (289 of 841 Phase-A rows, a narrow spike on a broad base) it is unresolved which radius sets the mass ("talk to Sam Young"). |
| `[tomberg-prefactor-and-c-vs-cbar]` | R A0.2; sumF | unowned | The Tomberg mass prefactor is unverified, and the `C` versus `C̄` criterion comparison was never written up. |
| `[zeta-peel-off-first-crossing]` | R A0.2 | unowned | The `ζ = δN` peel-off construction is original. First-crossing and non-monotone-`ρ` cases are unhandled: `brentq` assumes a bracket. |
| `[compaction-ordering-audit-outcome-unknown]` | R A0.2 | unowned | After the ordering bug, the decision was to audit rather than regenerate `CompactionFunction` rows. The outcome is not recorded. |
| `[samples-per-n-store-tag-missing]` | R A0.2 | unowned | The `SamplesPerN` store tag agreed on 16 June does not exist. Check whether sampling density is part of `InflatonTrajectory` identity (the June rule was that the grid is not). |
| `[regression-script-stale-columns]` | R A0.3, C0 | unowned | `regression_InstantonOutputs.py` lists pre-prompt-14 column names and cannot read any `scalar_data.csv` written after 23 June. |

## 5. Documents that contradict the current position

Each should be corrected or marked superseded with a pointer to its
replacement. Dated records get a status note and inline markers, not an
in-place rewrite. Phase 0 (8 October 2026) dealt with all but the one below.

| Issue | Source | Owner | Hook |
|---|---|---|---|
| `[doc-collaborator-email-max-delta-nstar]` | R A0.3 | David | The 25 June email to collaborators asserts a maximum `δN★` for collapse. The data do not support this as written. |

## 6. Minor and parked

| Issue | Source | Owner | Hook |
|---|---|---|---|
| `[picard-lefschetz-upflow]` | R A0.1 | research | Which Picard–Lefschetz method avoids constructing the upflow trajectory (9 June). Never answered. |
| `[bvp-solver-survey]` | R A0.1 | unowned | The 11 June BVP-solver survey reached no decision. D0.5 re-admits `diffrax`. |
| `[numerical-schemes-picard-rationale-half]` | R A0.1 | P4 | `NUMERICAL_SCHEMES.md` §2.2 records only the conditioning half of the Picard-versus-shooting argument, not the cost model or the hidden second pass in `∂φ₁(T)/∂λ`. |
| `[k-sigma-unused]` | R A.1 | unowned | `k_σ` enters no computed quantity. |
| `[doe-undefined]` | R A0.2 | unowned | "DOE" (design of experiments) is used throughout and defined nowhere. |

## 7. Closed

| Issue | Closed | By |
|---|---|---|
| FullInstanton single-source versus analytic adjoint (R Open 1, D.4a) | 2026-10-08 | Decision D0.1: one Hamiltonian module differentiated at runtime for both solvers; analytic FullInstanton equations in the paper only. D0.5: JAX, with complex-step as the conformance test. |
| Tex must wait for a pen-and-paper validation (R D "Taken" 5) | 2026-10-08 | Decision D0.2; the tex was rewritten in `e511f74`. |
| Export window too short (R window edges) | 2026-10-08 | Decision D0.4; June threads reconstructed in Part A0. |
| Tex rows of R Part C: response bracket, operator ordering and truncation; `Δs`/`Δ̇s` pairing; choice of measure; `sec:bcs`; collocation boundary conditions | 2026-10-08 | `e511f74`. The tex now states the target; the code rows are §3. |
| Tex `sec:scale-assignment` "same construction" and its `todo` (R A.1, C0) | 2026-10-08 | `e511f74`, `sec:scale-anchor`. |
| Factor of two between `½ D_φ φ̃²` and `D₁₁ P₁²` (R A.1, A.2) | 2026-10-08 | Legendre check, tex `sec:hfp-1d`. |
| Slicing tilt unrecorded (R A.1) | 2026-10-08 | Recorded as dropped, tex `sec:fullinstanton-eqs` panel. |
| Differentiating the truncated `H_sq_loc` (R A.3) | 2026-10-08 | Adopted as the model's convention, same panel. |
| Live-Neumann `g_π` target and its abscissa sweep (SCS §4.4, §6) | 2026-07-11 | Dead on two grounds (R A.3 C1, C2; B.3); recorded here on 2026-10-08. |
| `adjoint-full` mode of the prompt-18a diagnostic, never run (R A.2) | 2026-10-08 | Superseded by the Hamiltonian-structure check, tex `sec:discrete-hamiltonian`. |
| `DIAGNOSTICS_SUITE.md` §5 said Diagnostic 8t raises `NotImplementedError` | 2026-10-08 | Corrected in the prompt-28 commit `3ea27e0`. |
| `[gci-stale-g-pi-documentation]`: `forward_rhs.py` and `NUMERICAL_SCHEMES.md` §3.5 described the `g_π` target as lagged with a vanishing forcing; `picard.py` called the bias small (SCS §1.2) | 2026-10-08 | Docstrings, the inline comment and §3.5 corrected to the frozen target and Test A's measured forcing, with pointers to the target closure; `picard.py` corrected too. Docstring-only change (AST-identical). |
| `[doc-reconstruction-errata]`: three statements in R wrong (the sign in `K`, the form of `w_in`, the natural response condition) | 2026-10-08 | Errata E1–E3 added at the head of R, with markers at each occurrence; status note on `LATEX-REWRITE-BRIEF.md`. |
| `[doc-bc-handoff-rho-final-false-premise]` and `[doc-bc-handoff-gstar-recorded-as-0.2]`: `handoff_instanton_boundary_conditions.md` §3–4 and §2.1 | 2026-10-08 | Status note and inline markers. The `g*` physics stays open as `[gstar-offset-in-scale-matching]` (§4). |
| `[doc-grid-sampling-dof-counting]`, `[doc-grid-sampling-critical-bubble]`, `[doc-grid-sampling-vennin-exponent]`: the three `grid-sampling/handoff-*.md` | 2026-10-08 | Status notes (all `S_MSR` numbers provisional; minimum-action pathway reversed; `ρ_final` a false premise; Vennin identification retracted) and inline markers. |
| `[doc-tau-study-recommends-finer-sweep]`: P28's "Combined recommendation" | 2026-10-08 | Status note: superseded, the closure is to be replaced, not tuned. Correction to the earlier hook: the argument against the sweep was made on 10 July (summary C), not 9 July, and David did not rule. |
| `[doc-hfp-structure-status]`, `[doc-sat-closure-status]`, `[doc-hfp-calculation-mu-convention]`: the three 10 July notes | 2026-10-08 | Status notes saying which sections stand and which are superseded, with inline markers at HSS §2(d), SCS §3.1, §4.4, §6 and HCalc §7. |
| `[doc-chat-only-documents]`: `session_summary.md`, `analysis_protocol.md` (24–25 June) | 2026-10-08 | Recovered verbatim from the claude.ai export into `grid-sampling/2026-06-24-session-summary.md` and `2026-06-25-analysis-protocol.md`, with provenance and status headers. |
