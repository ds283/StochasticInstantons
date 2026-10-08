# Reconstruction of the June–July 2026 analysis from chat transcripts

**Date:** 2026-10-08. **Prepared by:** Claude (Fable 5.1) from the claude.ai
export of the personal-account Project "Stochastic instanton code" (window
1 July – 1 August 2026), the Claude Code transcripts that survive on disk,
and the repository documents. **Status:** a *record*, not a design decision.
Every claim below is attributed to a dated conversation; where a later
conversation reversed an earlier one, both are given and the later one is
marked as the position in force on 20 July 2026.

**Why this document exists.** Between 10 and 20 July 2026 the analytic
understanding of the gradient-coupled instanton (the "onion model") moved a
long way, almost entirely in chat. None of it reached `onion_model.tex`, the
design notes, or the code, and the three handoff notes in
`.documents/handoff-notes/2026-07-10/` were written on 10 July, *before* most of
it. Several of their conclusions were later overturned. This document is the
bridge: it says what was concluded, where, what it supersedes, and what is
still open, so that the LaTeX notes and the code can be brought into line in
the plan that accompanies it.

**Window edges.** The export covers conversations *created* 1 July or later.
The Project's own listing shows about 25 earlier instanton conversations
between 15 June and 30 June (the FullInstanton boundary-condition work, the
first-passage/backward-Kolmogorov thread, the Ito-isometry and Euclidean-vs-
real-time threads, the DOE/Latin-hypercube sampling work, the Halliwell–Hawking
reading). (The first-passage and Euclidean-vs-real-time threads in fact date
from 27–28 April and 7 May; their 30 June last-activity stamps placed them in
this range of the listing. See Part A0.) The 12 July SBP thread cites the 18 June conversation
"StochasticInstanton codebase and FullInstanton boundary conditions" for the
stalled Gaussian-expansion argument. **The window should be extended back to
14 June (the Project's creation date).** At the far end the last relevant
conversation was last active on 20 July, so 1 August is a safe upper bound.

**Errata (8 October 2026).** Three statements below were found to be wrong
while the derivations were redone for the rewrite of
`notes/onion-model/onion_model.tex` (`e511f74`). They are left in place,
because this document records what the threads concluded, and are marked
**[Erratum E1–E3]** where they occur. Where they disagree, the tex is right.

- **E1 (B.9, chain-rule `Δ̇s`).** The second term of `K` has a *plus* sign,
  `K = (1/Δs)[(V'/V)(∂_yφ)_core + π_core (∂_yπ)_core / (3−ε_core)]`, and the
  numerator also carries the `φ`-row forcing,
  `Δ̇s = [1 − ε_core + (V'/2V) 𝓕^φ_core + π_core 𝓕^π_core / (2(3−ε_core))] / (1 − K)`,
  where `𝓕^φ`, `𝓕^π` are the non-advective core forcings (noise in both rows,
  gradient in the `π` row). Tex eq. `Deltas-dot-closed`.
- **E2 (B.9 and Part C, the incoming invariant).** The incoming Riemann
  invariant is the left eigenvector `w_in = π_core + (2/Δs)(∂_yφ)_core`.
  `(2/Δs)(1 + Δ̇s) ≈ (2/Δs)(2 − ε_core)` is the coefficient of `w_in²` in the
  boundary flux, not a weight inside `w_in`. The relative weighting of the two
  terms is set by `Δs` alone: `w_in` is gradient-dominated at early times
  (`Δs ∼ ln(1+α)`) and `π`-dominated only at late times (`Δs ∼ 10`), and a
  penalty on either term alone is the characteristic projection in neither
  limit. The "`π`-dominated near de Sitter" reading, and the remark that a
  penalty on `(Dφ)_core` alone is the projection only if `ε_core ≈ 2`, are
  wrong. Tex eqs. `riemann-variables`, `core-flux`, `w-in`.
- **E3 (B.1, response boundary condition).** With the `L(g π̃)` ordering of
  B.4 the natural response condition at the core is `∂_y(g π̃) = 0`, which
  reduces to `∂_y π̃ = 0` only where `g` is `y`-independent at the core. The
  count in B.1 (one condition) stands; the form changes. Tex
  `sec:no-data`, response-sector paragraph.

---

## Part A0 — June 2026: foundations, pipeline, and the first science campaign

Added on 8 October 2026 from a second export covering 1 June to 1 July
(`summary-D-june-physics.md`, `summary-E-june-pipeline.md`,
`summary-F-june-science.md`, kept beside this file). Three conversations listed in
the Project — "First passage probabilities and backward Kolmogorov equations",
"Real time vs Euclidean instantons", "Spacetime interpretation of stochastic
δN noise" — are absent from both exports because they predate 1 June: the
third was read directly from the browser pane on 8 October and is dated
**29 April 2026** (captured, in condensed form, under
`.documents/transcripts/2026-04-browser-capture/`). It is the origin of the
onion-model programme: David's reading of Briaud et al. (2509.05124) as a
reference-volume-plus-shell scheme, his point that noise differences between
patches arise at spacelike separation and cannot be a single-patch history
integral, and the two agreed limitations of Briaud et al. for the PBH
problem (typical rather than conditioned neighbours; no slope–peak coupling
in the rare-event geometry), with the conclusion that a gradient-corrected
formalism conditioned on the rare event is "a natural next step".

The other two were captured verbatim on 8 October through the conversation
API from the same browser pane (same directory; SHA-256 checked against the
source) and change nothing below:

- **"First passage probabilities and backward Kolmogorov equations"
  (27–28 April).** The origin of three ideas that A0.1 and A0.3 take as
  given. (i) The density character of a BKE solution is fixed by its
  boundary/initial data, not by the PDE: Ezquiaga–García-Bellido–Vennin's
  `P_Φ(𝒩) = δ(𝒩)` on `𝒞_end` makes `P` a density in `𝒩` and a scalar in
  `Φ`. The survival-probability conditions of 2510.04707 Eqs. (2.10a,b),
  built from a transition density in both `x` and `x₀`, give a density in
  `x₀`. Their construction is correct but differs from the standard one, and
  neither the choice nor the reading of `Φ` as the scale/mass label is
  stated in their paper ("may have to ask Vincent"). This is the
  background to the 24 June `δ(φ − φ₀)` proposal in A0.3. (ii) **Olympus
  Mons versus Cerro Torre:** in the rare limit the eigenmode result reports
  the least-suppressed channel (slow accumulation, broad base). PBH
  formation needs the rapid-accumulation channel, so
  `P_CerroTorre ≤ P_OlympusMons ≈ P_Φ(𝒩)`, and the instanton can select
  that channel through its boundary conditions. (iii) A transition is the
  triple (initial field, final field, `N★`), with `δN = N★ − N_det`. The
  mass depends on all three, and `P(M)` integrates over the initial and
  final configurations with a prior, which needs density character in
  both. This is the motivation for the `δN★` / `φ_final` parametrisation
  in A0.1.
- **"Real time vs Euclidean instantons" (7 May).** General background, not
  specific to the project: an instanton is a saddle of the complexified
  path integral, and the Euclidean contour only makes that saddle real (an
  "accident" of the saddle, not a property of the framework). It continues
  into a digression on the geometric reading of GR. It bears loosely on the
  A0.1 brainstorm about ending a Euclidean segment at `Im π → 0`, but
  records no decision.

### A0.1 Physics foundations (from `summary-D-june-physics.md`)

- **The `ρ_final` boundary-condition question is a false premise (18 June).**
  The repo still carries it as open: `handoff_instanton_boundary_conditions.md`
  §3–4 presents Interpretations A/B for "the next conversation", and the
  three `grid-sampling/handoff-*.md` files say it failed on "a
  degrees-of-freedom counting issue". The 18 June conversation (which *was*
  that next conversation) concluded: the failure is geometric, not counting
  (the one-parameter `λ`-family of endpoints need not meet the constant-`ρ`
  level set); and more fundamentally the terminal condition is *"just a
  label that divides the trajectory"* into the noise-active and noiseless
  phases; enforcing `ρ(T) = ρ_noiseless` assumed the volume rejoins the
  background, which is wrong for the interesting cases (permanent
  dislocation). `δN★` and `φ_final` are parallel proxies (amplitude and
  smallest affected scale); neither is privileged; the `δN★` shard key
  stands. **Both repo documents need correcting.**
- **The Vennin comparison (18 June), in full.** The apples-to-apples
  instanton has `N_final = 0` and no downflow. David's central objection to
  the eigenvalue formalism is that the Kolmogorov average is over *all*
  noise realisations, so it is unknown *where it puts the noise* and hence
  what collapse criterion its tail probability describes. The attempted
  diagonalisation `S = Σ λ_i c_i²` stalled because the cross integral's
  weight `w/A` is not the Sturm–Liouville weight. The linear law
  `S = λ₀ δN★` was retracted twice: the Gaussian constraint integral gives a
  *quadratic* `S = λ₀ (δN★/α₀)²`, and the linear form is the
  Donsker–Varadhan long-time regime, which David rejected because it would
  force exponential tails always; the right framework is
  Freidlin–Wentzell with `λ₀ ∼ 1/D` and case-by-case `δN★` scaling. David's
  closing conjecture: per-instanton scaling may *"collapse to something
  simpler in the sum-over-instantons framework"*. The grid-sampling
  handoffs' "exponent → 1?" programme rests on the identification this
  thread showed to be unfounded.
- **Picard versus shooting (15 June).** Shooting is a `2N`-dimensional
  root-find on `(P₁(0), P₂(0))` with an ill-conditioned dense Jacobian over
  long `N_total`; the Lagrange-multiplier/Picard scheme is a root-find in
  `N_constrained ≤ N` multipliers; cost `≈ 2 k_outer k_inner + 2 N_constrained k_outer`.
  The inner convergence norm is over the whole trajectory, not the endpoint.
  The sensitivity `∂φ₁(T)/∂λ` needs one linear backward *and* one linear
  forward pass (David caught the hidden second pass). Only the conditioning
  half is in `NUMERICAL_SCHEMES.md` §2.2.
- **Level 1 / Level 2 (29 June), the conceptual frame for everything
  since.** The MSR action does not compute the horizon-exit fluctuation; that
  is a Level-1 calculation (Mukhanov–Sasaki at low amplitude, a Euclidean
  tunnelling instanton at large amplitude). The MSR instanton (Level 2)
  stitches copies of Level-1 kicks. The Fokker–Planck equation is the
  Schrödinger equation of the MSR action, so one approximates the path
  integral rather than solving the (pseudo-differential, for non-Gaussian
  kicks) FPE; the Kramers–Moyal series cannot be truncated in the tail. If
  the Level-1 action grows slower than `η²`, the Level-2 saddle may collapse
  to a single dressed kick. **Nowhere in the repo.**
- **Halliwell–Hawking (30 June).** HH is strictly quadratic in the modes, so
  `δρ/ρ ∼ O(1)` cannot be read from it; δN cannot give the horizon-exit
  fluctuation either. There is no Level-1 calculation at all. The one
  constructive idea: keep `π` as an independent variable of the Euclidean
  instanton, end the Euclidean segment at the turning point `Im π → 0`
  (the field-space analogue of HH's equator), take `ρ = V/(1 − ε/3)` there,
  and `ζ ≈ −H δφ/π` with the *local* `π(φ)`; the reference trajectory for
  `δφ` was left undecided. **Nowhere in the repo.**
- **Origin of the onion model (30 June – 1 July).** The tex records the
  motivation, the conditioning argument, CLT suppression, nearest-neighbour
  correlations and the mean-field `V'` correction. Unrecorded: David's
  acceptance that CLT validity fails for the innermost layers (*"inevitable
  in a mean-field approximation. I don't mind this"*); the discrete
  three-region windowing scheme (`M₁` stochastic shells, `M₁ < i ≤ M₂`
  deterministic gradient-coupled, beyond `M₂` pinned, outermost frozen at
  its accumulated value, with a transfer-matrix "semi-infinite lead" for the
  linearised tail); David's governing principle *"I only actually want to
  solve the instanton equations"*, which dismissed the seam/continuation
  worry; the Eulerian-versus-Lagrangian detour and the three-scales
  confusion that produced the first coordinate `y = 1 − r (aH)₀`; the June
  argument that fixed sinc truncation needs exponentially many modes because
  the horizon locus `y_H → 1` cancels the `e^{−2N}` prefactor (the reason the
  exterior-only coordinate was later adopted); the caveat that a shell
  reheating before the core ends inflation is *"a genuinely problematic
  physical situation"*; and the quiet change of justification for Neumann at
  the core from "regularity at `r = 0`" (June) to "a physical smoothness
  assumption" (tex).
- Minor, unrecorded, open: which Picard–Lefschetz method avoids
  constructing the upflow trajectory (9 June, never answered); the BVP
  solver survey (11 June, no decision); the 1D `N_turn > N_final`
  insensitivity test in the tex `todo` was apparently never run.

### A0.2 Pipeline and compaction-function design (from `summary-E-june-pipeline.md`)

The infrastructure decisions of 14–22 June are well recorded in the rules
files, `INFRASTRUCTURE.md` and the base-implementation prompts. The physics
rationale behind several code choices is not:

- **The `g*` correction in the scale-matching equation is mis-stated.**
  The 17 June discussion found the degrees-of-freedom shift to be about
  `−1.1` in `ln k` for `g*_reh = 106.75`; the figure of `0.2` is only the
  uncertainty from not integrating `g*(T)`. `handoff_instanton_boundary_conditions.md`
  §2.1 records "~0.2 … omitted", which entered through a mis-recollection;
  David never explicitly agreed to drop a shift of order one e-fold.
  `ln_k_phys_Mpc` therefore carries an undocumented offset in scale
  assignment of about one e-fold.
- **Local instanton time on `[0, N_total]`** was chosen over absolute time
  because `δN★` moves the end of inflation while `k_end` is the fixed
  physical anchor; `N_inflaton = N_end − N_init + N_local`. The convention
  is in the code, the reasoning is not.
- **The diffusion model is a function of field-space position**, not of
  `ν` as a parameter, because metric mixing moves `ν` off `3/2` and the
  stochastic state may leave the background trajectory; Markov assumed for
  now. The `epsilon_end` helper was rejected for Jordan-frame generality.
  `H² = V/(3M_p² − π²/2)` was a correction found by Claude Code on 15 June
  and is recorded only in the `AbstractPotential.H_sq` docstring.
- **Origin of the Picard/shooting algorithm**: Bröcker et al. 1812.00681
  §III.A, adopted after David's counting argument that direct shooting is a
  two-dimensional root find on `(P₁(0), P₂(0))`; `solve_bvp` with `δN★`
  continuation, `diffrax` ("JIT compilation … extremely fragile", 15 June)
  and Julia were considered and set aside. (Decision 5 of 8 October
  re-admits `diffrax`.)
- **The `ζ = δN` peel-off construction is original** (no reference
  implementation to check against); ζ conservation is assumed in the
  growing mode away from features; first-crossing and non-monotone-`ρ`
  cases are unhandled (`brentq` assumes a bracket).
- David attributed the `ρ_final` non-convergence to field–momentum noise
  correlations in the diffusion model (17 June) before the 18 June
  resolution (A0.1).
- The flat-`ζ` prescription for the unresolved interior of `C̄(r)` and its
  proof as a no-op; the decision to audit rather than regenerate
  `CompactionFunction` rows after the ordering bug (outcome unknown).
- The Tomberg mass prefactor is unverified ("I'd need to check that
  formula"); the C-versus-C̄ criterion comparison was never written up.
- The `SamplesPerN` store tag agreed on 16 June does not exist; whether
  sampling density is part of `InflatonTrajectory` identity should be
  checked.
- Minor: multi-field rationale for list-valued `fields_json`; the
  provenance principle behind the `CosmologicalParams` table; seaborn
  theme must be set inside each Ray worker; the Ray `EMFILE` crash and its
  `ulimit` mitigation; "DOE" means design of experiments and is defined
  nowhere.

### A0.3 The June science campaign (from `summary-F-june-science.md`)

The repo records the campaign's *design* (sparse-sampling prompts, three
grid-sampling handoffs) and the Goal-1 scaling result up to 23 June. Almost
everything decisive from 23–25 June exists only in chat, and **every
`S_MSR`-bearing number was computed with the defective FullInstanton
response sector** (B.10), so must be re-run once the Hamiltonian module
lands. Summary F's §2 table classifies all 32 claims.

- **A recorded conclusion is wrong.** `handoff-large-grid.md` and
  `handoff-goal2.md` state that the minimum-action pathway at fixed mass is
  the broadest perturbation that still collapses ("analogous to a critical
  bubble"). The 24 June fixed-`K` grids (`K = N_final + ΔN + δN★ ∈ {23, 33,
  43, 53}`) showed this to be a fixed-`N_final` artefact: `S` increases
  monotonically with `ΔN`, and the minimum-action pathway is the *smallest*
  `(ΔN, δN★)` that still collapses, with no floor found down to
  `ΔN ≈ 0.05`. The threshold is `δN★_th ≈ 0.55 ΔN` at small `δN★` and
  `≈ 1.0 ΔN^0.68` at large, independent of `K` over 25 decades of mass.
- Mass law `log₁₀(M/M☉) ≈ 0.86 (N_init + δN★) − 36.5` with 0.02–0.04 dex
  residual; `N_final` alone is uninformative. Expected to survive
  recomputation (kinematic).
- The exponent of `S` in `δN★` saturates at about 1.2–1.4 rather than
  Vennin's 1; this is recorded but is now doubly suspect (A0.1 and B.10).
- `r_max ≠ r_peak` in 289 of 841 Phase-A rows, confined to `ΔN ≲ 0.45 δN★`
  (a tall narrow spike on a broad base): the first quantitative instance of
  the "Olympus Mons versus Cerro Torre" distinction, which itself dates from
  the 28 April first-passage conversation (Part A0). The mass estimate to use
  when they diverge is unresolved ("talk to Sam Young").
- David's self-consistency doubt at large `δN★`: the per-step kick is far
  out on the Gaussian tail, so the saddle point probably *underestimates*
  the probability; a Euclidean tunnelling amplitude per step was mooted and
  is the Level-1 question of A0.1. The `σ_φ1` noise-amplitude columns were
  built to track this; the ratio `δN★/(σ ΔN)` was never plotted.
- The Vennin comparison restated (24 June): the instanton is the most
  likely route to a PBH of *fixed mass*; Vennin's `Q_φ(N★)` marginalises
  over masses; David's proposal to solve the backward Kolmogorov equation
  with `δ(φ − φ₀)` at `K = 0` so that `Q` becomes a density on `φ` with `K`
  a parameter, "the object comparable to our sum over instantons". Posed,
  not attempted.
- The 25 June email to collaborators asserts a maximum `δN★` for collapse;
  the data showed the no-collapse island at large `(ΔN, δN★)` in the fixed-`K`
  grids is a mixture of the `N_final > 3` squeeze and Picard failures, so
  the sentence is unsupported as written.
- Two documents written in chat only, `session_summary.md` and
  `analysis_protocol.md` (portability to quartic and USR-like potentials),
  are not in the repo. `regression_InstantonOutputs.py` still lists
  pre-prompt-14 column names and cannot ingest any `scalar_data.csv` written
  after 23 June.
- Compute-time statistics on the 1024-point grid: FullInstanton median
  0.86 s, SlowRollInstanton median 43 ms, Picard failures from `δN★ ≈ 7`.

---

## Part A — 1 to 11 July: derivation and implementation threads

Summarised by three reading passes, kept beside this file as
`summary-A-derivation.md`, `summary-B-implementation.md` and
`summary-C-boundary-handoff.md`. The repository already records most of this
period in `onion_model.tex`, `onion_model_planning.md`,
`onion_model_implementation_review.md`, the design notes 21–28, and the three
10 July handoff notes. Part A lists only what the passes found to be
*unrecorded* or *contradicted*.

### A.1 Unrecorded or contradicted items from 1–11 July

### A.1 Derivation and design threads, 1–7 July (from `summary-A-derivation.md`)

The tex, `onion_model_planning.md` and the implementation review record this
period well: the switch from a spectral mode expansion to collocation, the
exterior-only logarithmic coordinate, the self-adjoint measure, the
`φ̂ = iφ̃` rotation, the response-equation sign fix with the measure-friction
term, the `Δs(N_init) = 0` singularity and the `α` regularisation, the
outer-edge scale anchor. Items that exist only in the chats:

- **The slicing tilt.** The tilt between constant-`N` and constant-proper-time
  hypersurfaces (a shift-vector-type term) was identified as the same order
  as the `∂D_ij/∂φ` feedback and dropped; the tex's "What is not corrected"
  panel lists only `∂H²/∂φ`, `∂D/∂φ`, `∂A/∂φ`. (Relevant to B.9's finding
  that `A` is a shift vector in the optical metric.)
- **Decoupled limit ≠ FullInstanton at the core.** With the gradient and
  advection switched off, the non-core response fields vanish identically but
  the core equations still carry the `(3/2)Δs` dilution and `c(N)`; the
  δ-function reduction `φ̃ = δ(y−1) φ̃_core/μ(1,N)` (David, 7 July) was
  argued but the action-value agreement was left as an empirical diagnostic
  that was then **blocked by a degeneracy**: Neumann elimination from
  background neighbours with zero-row-sum `D` pins `φ_core` to the background
  for any `λ`, so the fully decoupled shooting problem is degenerate. No
  prompt 16 file exists; the tex has no note.
- **Possible factor of 2** between `½ D_φ φ̃²` and FullInstanton's
  `D₁₁ P₁²` — raised twice (6 and 7 July), never followed up. (B.1's
  1D reduction, `H_FP` with `D_φ = 2D₁₁`, Legendre-checks to `D₁₁ P₁²`, which
  settles it in favour of consistency, but that check is itself unrecorded.)
- **Frobenius analysis** of the forward sector at `Δs → 0`: the explicit
  leading-order relation `4(aH)₀² h″ + (y+1)(1−ε_core) p₀′ = 0`; the
  response sector was never analysed (tex records only the qualitative
  statement). The padded-domain and late-start alternatives to `α` are not
  recorded anywhere.
- **ε = 1 is a fixed-π surface, not a fixed-density surface** (David); the
  downflow-then-match recipe survives because `ε = 1` is used only as "late
  enough to trust adiabaticity". Why the downflow must be done per shell
  rather than shortcut (the response fields can compensate for decaying
  noise through the non-local shooting constraint) is unrecorded.
- **Scale assignment history**: the `ln_k_phys_Mpc` production bug (the old
  `0.25·log(V_k/(V_end(1−ε_k/3)))` form predicted `r_phys ∝ H^{1/2}` at
  fixed `N`, contradicting `k = aH`), its rewrite in `H`, the `(1+α)` factor
  and the anchor at `N_init`, and the forward re-anchoring of
  `CompactionFunction` with `N_before_end = N_init − N_inst` all live in
  prompts 11–12 and code comments; the tex still says `CompactionFunction`
  uses "the same construction". The outer-layer scale discrepancy
  `≈ e^{δN★}/(1+α)` between the two pipelines was attributed by David to the
  separate-universe approximation being "on the verge of breaking down" and
  is unquantified. The tex `todo` in §scale-assignment (equivalence check)
  was answered in discussion — the discrete code uses the local trajectory —
  but the tex was not updated.
- **Two identical shells get the same radius** paradox (peeling scheme defines
  radius via trajectory position; the continuum has independent comoving
  `r(y,N)`) — only the resolution is recorded.
- Prompt-17 stiffness sweep (7 July): stiffness concentrated at small `Δs`
  near `N_init`, `O(n⁴)`, benign at wide `Δs`; `α` buys about a factor ten;
  Radau/BDF to be tried before SBP-SAT. Superseded within the day (A.2).
- Minor: `k_σ` never enters any computed quantity; no covariance
  symmetrisation needed at this order; grid-stretching options considered
  and deferred; `NUMERICAL_SCHEMES.md` does not carry the old `ln_k`
  formula (checked 8 October).

### A.2 Implementation and stiffness threads, 6–9 July (from `summary-B-implementation.md`)

The repository records this period well (tex §response-rotation and the
corrected response equations; design notes 21, 21a, 22, 22b, 22c, 23, 24,
24a, 24b; the 9 July handoff brief). Items that exist only in the chats:

- **Compensated-delta reduction to FullInstanton** (6 July): the onion
  response field reduces to the 1D one as `φ̃ = δ(y−1) φ̃_core(N)/μ(1,N)`;
  the factor-of-2 convention between the onion noise covariance and
  FullInstanton's forcing was flagged for a cross-check that was never done.
- **Prompt-17 stiffness analysis** (7 July): spectral radius
  `≈ 0.130 n²/Δs`, `Im/Re ≈ 3.55` independent of `n`, `Δs`, `α`,
  non-normality `∼ n²`, pseudospectra and frozen-`H²` caveats. Superseded the
  same day by the discovery that the metric had discarded the sign and the
  real problem was a right-half-plane spectrum (recorded), but the law and
  the IMEX/ETD recommendation are unrecorded.
- **Prompt 18a**: the gradient operator's non-adjointness is entirely
  boundary-localised while the advection mismatch is bulk and flat; an
  `adjoint-full` diagnostic mode was proposed and apparently never run.
- **The SAT-target argument** (7 July): David's objection that `g_π = 0`
  would freeze `φ_core` and make the BVP unsatisfiable; the
  `g_π = background π` option and its rejection; the finding that
  derivative-type closures cannot cancel a value-type energy defect; the
  `sat="regularity"` test (value-type penalty towards `neumann_boundary_value(π)`)
  that did *not* flatten the abscissa but on an incomplete closure, so it
  should not be cited either way; David's "heat bar" framing and his remark
  that a missing well-posed formulation "is telling us something structural".
- "`n_rhp` is not a good metric"; acceptance is "abscissa bounded in `n`".
- Claude's mechanism hypothesis for the Anderson `1e-4` floor
  (`τ ∼ 1/Δs` leaves `g` weakly determined away from `N_init`).
- **The basin-of-attraction argument** (8 July): the forward seed was the
  unstretched background while `g_π` was seeded from the stretched
  FullInstanton profile; the 21a retry band-aid is an artefact of Finding 1.
- **Why backward-growing modes are benign** when their rate is bounded in
  `n`; the proposed mode-rate-versus-`n` plot.
- David's **loop-correction caveat**: `r = λ r̃` linearity is guaranteed by
  the MSR construction at tree level and is lost with loop corrections
  (Schwinger–Keldysh effective action); a "valid at tree level" comment was
  to be added.
- The **24a→24b shift** in `S` (about 8 % at `δN★ = 0.3`) and
  `d ln S / d ln λ ≈ 2`, which are the quantitative basis for the handoff
  brief's "trap 4".
- Open items raised and never resolved in scope: the factor-of-2
  normalisation; the tex `todo` on the largest-time equation; the
  `O(1/τ)` boundary layer of the live-Neumann `g_φ` at high `n`; a
  bias-free closure replacing both lagged and fixed targets; `OUTER_TOL = 1e-2`
  being loose for a stationary quantity; a `--no-store-values` plus
  `--targets homogeneous gradient` crash in `main.py`.

### A.3 The synthesis thread, 10–11 July (from `summary-C-boundary-handoff.md`) **[unrecorded]**

This is the "fresh context" session that read the three 10 July notes. It
overturned several of them within a day and reached a plan David largely
agreed to; none of it reached the repository.

- **C1.** `w_core · D[-1,-1] = 1/2` exactly (checked at `n = 5, 7, 9, 17, 33`),
  so the production `g_φ` penalty is `−2τ (Dφ)_core`: a *derivative-type*
  condition after all. The penalised-quantity/target-value table in
  `SAT-CLOSURE-STATUS.md` §3.1 is wrong, and a live-Neumann `g_π` target would
  swap the one negative-definite term for an indefinite one; predicted to
  bring back the `n^1.6` abscissa. §4.4 of that note should be retired.
- **C2.** With advection on both fields, `π = ∂_N φ − A ∂_y φ`, so
  `∂_y π|_core = −A_core (∂²_y φ)_core ≠ 0`. Test A2's `O(1)` ratio is
  *expected*; the φ-control proposed in §4.1 is the wrong control (the right
  one compares `(Dπ)_core` with `−A_core (D²φ)_core`). Live-Neumann-π is
  dead on two independent grounds.
- **C3.** Two forward penalties on a one-incoming-characteristic boundary is
  over-determination, growing as `n²`. Root cause: the SAT was derived in the
  wrong energy norm (`Σ w (φ² + π²)` rather than `Σ w μ (π² + c² (∂_y φ)²)`).
  Fix: a single rank-one penalty along the incoming eigenvector with
  coefficient `(2/Δs)(2 − ε_core)`. Both options in `SAT-CLOSURE-STATUS.md`
  §6 and the "reconciliation" paragraph of `HFP-STRUCTURE-STATUS.md` are
  rejected. (This is the same conclusion B.3 and B.9 reach later by a
  different route; B.9 adds that the penalised variable is
  `π`-dominated.)
- **Four omitted terms in `FullInstanton.bwd_rhs`**, found here first:
  `−P₂ V'²/(V H²)`, `−2ε P₂`, `−(V'/V) π P₂`, and the diffusion terms
  `∝ D₁₁ P₁²` (quadratic, Riccati). For `V ∝ φ^p` the exact `P₁'` drift term
  is `−1/(p−1)` times the coded one: quadratic is a sign flip of equal
  magnitude, quartic is `−1/3`, USR is a null test. Claude retracted "your
  FullInstanton physics is probably fine" and the `O(R²)` claim: the
  minimum-action locus, `δN★_th(ΔN)`, and the 1.2–1.4 exponent are all
  suspect, and the Vennin exponent-1 comparison is a live suspect.
- **David's physics position (10 July 10:23–10:45):** `H(φ)` and `ε(φ)` are
  not present in the original Langevin equations; they come from the Einstein
  constraint. Final agreed statement: the derivative terms appear **only** in
  the response-sector equations; the Langevin equations are unchanged; the
  MSR action is the action of the reduced SDE; the tangent-map argument needs
  no variational principle. The onion's `H_sq_loc` (a truncated constraint)
  was flagged as a residual caution for differentiating it, and deferred.
- **Q2/Q3.** A transpose cannot be stiffer than its operator (same spectrum
  and numerical abscissa); prompt 23 built a *different* matrix, and its
  response state vector is one DOF short; do not transpose the current
  over-determined operator. MAM as a global minimiser rejected (degenerate
  `D₁₂ = D₂₂ = 0`); discrete adjoint consistency inside Picard endorsed,
  preceded by the boundary-term redesign.
- **Six-step plan agreed (10 July, confirmed 11 July):** (0) frozen-state
  Jacobian checks on FullInstanton by complex-step, record the `H_FP` drift
  baseline; (1) restore `∂f/∂u` only, so the residual drift isolates
  `∂D/∂u`; (2) decide on `∂D/∂u` from that number; (3) the class-3 checks
  (`H_FP = −∂S/∂δN★`, exponent, three-potential falsification set), re-run the
  FullInstanton grids; (4) port to the onion's interior response terms;
  (5) C3, then transpose for the response boundary rows. The 10 July notes'
  "instrument `H_FP` first" ordering was explicitly demoted ("worthless on the
  current grids").
- **David's decision, 11 July 08:35:** analytic adjoint operator for
  production and publication ("this is how 99% of physics is done"), with
  complex-step/AD as a one-time oracle. Adjointness is a correctness issue.
  `∂D/∂u` is empirical; if retained, rebuild the `λ` loop and use the Riccati
  `P = M₂ M₁⁻¹` form. The `λ` magnitude is unknowable until the adjoint is
  rebuilt; `r̃ = r/λ` is contingent on linearity and should be flagged so in
  the tex. **Note the later evolution:** on 15–17 July (B.7, B.9) the
  state-dependent scaffold made David lean the other way ("maybe actually
  simpler" to obtain the adjoint numerically), and on 20 July (B.10) he posed
  the single-source versus analytic question without answering it. The
  11 July decision is therefore the last *explicit* ruling, but it was made
  before the scaffold's state dependence was understood.
- Also unrecorded from the 9 July thread: the τ-shape-in-`N` lever
  (`A_core = 2/Δs` diverges at `N → 0`), Radau in `N`, and the explicit
  rejection of the finer τ sweep that the committed `28-*.md` still
  recommends as the "immediate next step".

---

## Part B — 10 to 20 July: the analysis threads

Eleven conversations. Listed chronologically with the conclusions that matter,
each tagged **[recorded]** (where in the repo), **[partly]**, or
**[unrecorded]**.

### B.1 "Fokker–Planck Hamiltonian conservation in instanton equations" (10–16 July)

Opening question (David, 10 July): derive `H_FP`; is it related to the SBP
energy; is `H_FP = 0` an unenforced constraint; does SBP substitute for a
symplectic integrator.

Conclusions on 10 July, all **[recorded]** in `HFP-CALCULATION.md` and
`HFP-STRUCTURE-STATUS.md` (untracked):

- `H_FP = ⟨r̃ b_φ + π̃ b_π + ½D_φ r̃² + D_φπ r̃π̃ + ½D_π π̃²⟩_μ`, the
  Freidlin–Wentzell Hamiltonian; canonical pair is `(φ, μ r̃)`, which is where
  the `−μ̇/μ` term comes from.
- Not conserved in the onion for three reasons: explicit `N`-dependence
  through `a(N)`; boundary flux at both ends; the variational truncation.
  Exact balance law `dH/dN = ∂_N H|_expl + Φ + ⟨φ̇ R_φ + π̇ R_π⟩_μ`.
- `H_FP ≠ 0`; Maupertuis `H_FP = −∂S/∂δN★|_{N_final,ΔN}` (1D), a free test
  on existing grids.
- Forward and response discretisations are not adjoint; fix is `−M_SAT^T`
  from the variational boundary term `τ[r̃(φ−g_φ) + π̃(π−g_π)]_{y=+1}`.
- Core boundary is subsonic inflow with one incoming characteristic;
  `A(1)/c = 1 − ε_core` exactly. (On 10 July this was read as "`g_π` is a
  model closure supplying incoming data". **Superseded on 11 July, see B.3.**)
- SBP is spatial, symplecticity temporal; neither is the right worry; the
  discrete variational principle (Marsden–West / MAM) subsumes both, but MAM
  struggles with degenerate forcing (`D12 = D22 = 0`).

Follow-ups on 14 and 16 July, **[unrecorded]**:

- Why characteristics apply at all: the forward sector is hyperbolic, not
  parabolic. Eliminating `π` gives `φ_NN − 2A φ_Ny + (A² − c²) φ_yy = 0`,
  discriminant `4c² > 0`, characteristics `dy/dN = −A ± c`. The `D_ij` terms
  carry no `y`-derivative and are invisible to the principal symbol. The
  tex's elliptic argument (Cauchy problem for `L` ill-posed) and the
  hyperbolic count are consistent: one governs the fixed-`N` spatial BVP, the
  other the `(y,N)` evolution.
- Sub/supersonic means `|A|` versus `c`; the sign pattern of `−A ± c` is the
  invariant statement; slow roll is barely subsonic with the outgoing mode
  nearly tangent to the core (speed `2ε_core/Δs`).
- **Response sector (16 July).** Same principal symbol (adjoint of a
  hyperbolic operator), same characteristics traversed backward; in backward
  time the roles swap, so again exactly one incoming characteristic at the
  core and the current `∂_y π̃ = 0` has the right count **[Erratum E3]**. The response's
  incoming mode is the slow, nearly sonic one. `φ̃(−1) = 0` is an identity
  given `π̃(−1) = 0` and `A(−1) = 0`, mirroring the forward sector. The
  response sector needs **no data**: the variational boundary term is affine
  in `(φ,π)` with coefficients linear in the response fields, so varying it
  with respect to `(φ,π)` gives homogeneous terms and the `g`'s differentiate
  away. Prompt 23's negative is therefore a strong-versus-weak mismatch, not
  a count or character error; the fix is `−M_SAT^T`, which carries the same
  `τ/w_core ∼ n²` prefactor. David asked for both handoff notes to be amended
  with this; **that was never done.**

### B.2 "SBP discretization and characteristic norms" (11–12 July) **[unrecorded]**

A tutorial thread driven by David's insistence on a logically complete
account. Settled content:

- `HD + (HD)^T = B` is discrete integration by parts; the "H-energy"
  `E = uᵀHu` is a *control functional*, not a physical energy and not
  `H_FP`. David's terminology ("H-kernel", "H-energy", "H-characteristic
  flux") was adopted; "physical energy" was retracted.
- Three logical steps: (1) choose `H` so the interior of `dE/dN` is
  sign-definite (zero for first-order skew operators, `−uᵀMu ≤ 0` for the
  second-order dissipative piece; "total derivative" is only the first-order
  case); (2) read the boundary flux in Riemann variables; (3) impose exactly
  the incoming data. Well-posedness *is* the existence of such an `H` and BC
  set; the method engineers `E` rather than discovering a conserved quantity.
- `H ≻ 0` is load-bearing: norm equivalence makes bounded `E` control `‖u‖`
  and makes every admissible norm agree on the bounded/unbounded dichotomy,
  so there is no `E₁`-bounded/`E₂`-unbounded paradox. `κ(H_μ)` is large near
  `N_init` where `μ` is sharply graded, so the bound is loose exactly in the
  stiff stretch.
- Only `H_μ = diag(w_j μ_j)` makes the interior sign-definite for this
  operator; the flat LGL norm fails step (1) outright. The μ in the
  characteristic flux `(μ/4)[(c+A)w₊² + (A−c)w₋²]` is the same μ.
- `H_FP` is indefinite and can never be a control functional, but it is a
  bounded form, so `|H_FP| ≤ (M/c) E` once `E` is bounded on the **joint**
  forward-plus-response state. The response sector currently has no energy
  estimate (hard elimination), so `H_FP` is not dominated by anything; this is
  the adjoint-inconsistency gap seen from the other side.
- Literature placement: response field as costate/adjoint sensitivity is
  standard optimal control (Pontryagin, Errico, Cacuci); the response-sector
  Riccati is the Schorlepp–Grafke–Grauer and Bouchet–Reygner prefactor Riccati,
  cited in David's own paper arXiv:2510.04707; the SBP-energy +
  characteristic + `H_FP`-domination crossover is not found in the literature
  and may be publishable on its own.
- `∂D/∂u ≠ 0` (D ∼ H²) ⇔ field-dependent prefactor ⇔ Riccati term ⇔ loss of
  `r = λ r̃` rescaling: one fact in four costumes. Mukhanov-equation memory
  in `D` would be non-Markovian and change `H_FP`'s phase space, not just its
  coefficients.
- **Withdrawn:** the claim `H_FP → −Λ₀` (spectral gap). The envelope relation
  only translates between two things that must be known independently. The
  June Gaussian-expansion sketch (18 June conversation) gives
  `S_min = δN★² / Σ b_i²/λ_i`, *quadratic* in `δN★`, and stalled on the
  diagonalisation step (weight function versus Sturm–Liouville measure).
  Vennin's linear `Λ₀ δN★` is a property of the marginalised first-passage
  object; the fixed-profile instanton is one channel of that sum. The
  adjoint backward-Kolmogorov eigenproblem is the missing scaffold for both
  questions. The measured exponent 1.21–1.37 is not yet evidence of anything
  because the noise sector is wrong.

### B.3 "Fokker–Planck core boundary conditions and π behaviour" (11 July) **[unrecorded; supersedes 10 July]**

David's framing, accepted: there is **no inflow of data from the core**;
perturbations are seeded at the horizon by the noise. Neumann `∂_y φ = 0` is
the correct, data-free (reflecting) use of the single incoming
characteristic; `π_core` is slaved to the interior by reflection,
`π_core = w_out`. Consequences:

- The piston flux `½ μ A(1) π_core² > 0` is physical bounded growth, not
  something to cancel.
- The `π_core` SAT penalty exists precisely to cancel that flux. It arose from
  the flat-norm strict-decay demand; under `H_μ` and a flux-matching
  philosophy there is nothing to cancel. Two penalties on a one-characteristic
  boundary is over-determination (the "C3 defect"), with `n²` stiffness.
- Dropping the `π_core` penalty is correct **only together with the norm
  fix**; dropped-penalty plus flat norm may be unstable.
- The `n ≥ 9` failure is attributed to the closure (ill-posedness, nothing to
  converge to) rather than to interior `D2` stiffness (large but stable,
  Radau-tractable). Discriminator proposed: eigenvector of the blocking mode
  (core-supported versus smeared near `N_init`), and the falsifiable test
  "drop the `π_core` penalty with the norm fix and rerun `n=9`".
- One check left open: whether the old `π` penalty was cancelling the
  advective `A π²` piston term (keep) or a flat-norm `D2` cross-term
  (artefact); their `A`-dependence separates them.

**This reverses `HFP-STRUCTURE-STATUS.md` §2(d)** ("`g_π` is a model closure
supplying incoming data") and settles the "single most important thing to
settle" flagged there: no data is supplied at the core.

### B.4 "Missing Δs factor in physical volume element" (13–15 July) **[unrecorded]**

- The physical volume element is `V'(y,N) dy = 2π r_out³ Δs(N) e^{−(3/2)(y+1)Δs} dy`.
  Self-adjointness fixes `μ` only up to a `y`-independent `C(N) = Δs e^{−(3/2)Δs}`.
- Noise normalisation (derived by angle-averaging white noise over a shell):
  the angle-averaged noise is white with respect to `V' dy` with amplitude
  `2D11/n_count` and a flat `δ(y−y')`. The tex's §8 amplitude is exactly
  right; the noise selects `V'` as the measure.
- Eq. `msr-action` as written is a **splice**: the linear term carries `μ`,
  the quadratic term carries the flat-convention diffusion. Three
  self-consistent triples exist (flat / `μ` / `V'`), related by
  `r → r/λ`, `D → λD`, all with the same forward numerics and the same `S`.
- In the `V'` convention the multiplicative-on-response coefficient
  `Z[ρ] = −∂_N ln ρ + A' + A ∂_y ln ρ` vanishes identically, because
  `∂_N V' = ∂_y(V' A)` is Liouville transport of the shell volume under the
  coordinate flow. The mechanism is three-way: the exponential part pairs with
  the advection-measure IBP; the `Δs` prefactor pairs with `∂_y A`. In the `μ`
  convention `Z = (1−ε_core)[1/Δs − 3/2]`, the bracket in the current tex and
  code. **The bracket is a convention artefact and should go.**
- `α` regularisation is **not** removed: the geometric `1/Δs` (advection),
  `1/Δs²` (Laplacian) and `1/Δs` (noise dilution) singularities are
  measure-independent. The `V'` convention does restore forward/response
  parity in the singular limit, which is the precondition for the deferred
  indicial (Frobenius) analysis of the response sector; that analysis has not
  been done and a back-of-envelope attempt did not obviously close.
- Operator ordering (15 July): the response gradient term must be
  `L(g π̃)` with `g = e^{−2Δs_loc(y,N)}` **inside** the operator, not `g L π̃`.
  Code (`response_rhs.py` line ~287) and tex both have the prefactor outside.
  The missing pieces `2κp g' ∂_y π̃ + κ(p g'' + q g') π̃` are the same gradient
  order as the retained term, so this is an inconsistency, not a truncation.
  `g' = (∂g/∂φ) ∂_y φ + (∂g/∂π) ∂_y π`, so `∂H²/∂φ` is needed for a second,
  independent reason. The adjoint residual `E` cannot vanish while this
  stands, whatever is done about the measure or the variational terms.

### B.5 "Noise normalisation in MSR action formalism" (14 July) **[unrecorded]**

Precision versus covariance conventions; `ξ(x)` as a noise *density* paired
with `dV`; `D(x,y) = D δ(x−y)/V'` as the covariant delta; the operator inverse
keeps the delta, so `Var(ξ dV in a shell) = D₀⁻¹ dV`, first order in the shell
volume. The `1/n_count` dilution (per-patch → per-shell-mean) and the `μ`
quadrature measure are distinct volume factors, both legitimate. The
"redefinition leaves the measure invariant" step is leading-order only; for
field-dependent `D` its Jacobian is the one-loop determinant.

### B.6 "Adjoint tangent map with volume element measure" (14 July) **[unrecorded]**

- After two wrong turns (recorded in the thread and retracted), the
  convention-covariant statement: `Z[V'] = 0`, `Z[μ] = (1−ε)[1/Δs − 3/2]`.
- Response equations in the `V'` convention, with no bracket:
  `φ̃̇ = A ∂_y φ̃ + (V''/H²) π̃ − e^{−2Δs_loc} L π̃` and
  `π̃̇ = A ∂_y π̃ − φ̃ + (3−ε) π̃` (before the B.4 ordering correction), plus a
  five-item truncation ledger: `∂H²/∂φ,∂π`; `∂ε/∂φ,∂π`; `∂A/∂u` through the
  core values; `∂(aH)_loc/∂φ` in the gradient prefactor; `∂D_ij/∂u` (the
  Riccati term).
- **Coordinate anchor, first decision (14 July):** the `ε` in `A` and in
  `Δs` should be `ε_nl(N)` from the noiseless background, because `r, s, y`
  are comoving labels of the unperturbed metric; all other `ε`'s stay
  shell-local. Consequence: `∂A/∂u = 0`, ledger item 3 disappears. Scale
  assignment's `Δs(N_final)` would move to the background too. **Reversed on
  16–17 July, see B.9.**
- Scale assignment recap (prompt 11 scheme) and the observation that GCI
  assigns the core the *unperturbed* horizon scale at `N_final` whereas
  `FullInstanton`+`CompactionFunction` assigns a `δN★`-dependent perturbed
  scale: a mass-attribution difference, not a threshold difference. Both are
  internally consistent separate-universe bookkeepings. (Under the 16–17 July
  reversal to a core anchor this comparison needs redoing.)
- David stated he was doing a **pen-and-paper validation** of the whole
  calculation and asked that the tex not be rewritten yet.

### B.7 "Adjoint tangent map in ODEs and applications" (15 July) **[unrecorded]**

- Literature: Pontryagin/Bryson–Ho; Cacuci (adjoint transport, boundary
  complementarity); Cao–Li–Petzold–Serban, CVODES; Griewank–Walther; Errico;
  Grafke–Vanden-Eijnden §III.D–E (mutually adjoint integrators, checkpointing).
- Dual consistency (Del Rey Fernández–Hicken–Zingg review) is the discrete
  version of Cacuci's surface-term cancellation. Table of continuous versus
  discrete adjoint: discrete gives exact `H_FP = −∂S/∂δN★`, exact gradients,
  not publishable; continuous is publishable, needed for indicial analysis,
  consistent only up to boundary terms.
- Both are wanted, with a division of labour: derive the continuum adjoint
  for the paper; generate the code's response sector by differentiating the
  **discrete action**, which makes dual consistency automatic. The SAT must
  then be a term in `S_h`, not an RHS modification, and `τ` from a
  frozen-coefficient energy argument in the wrong norm is generally not
  variational: "is the closure derivable from a boundary term in `S_h`?" is a
  design constraint.
- Discrete action recipe: integrate by parts in the continuum first so only
  first `y`-derivatives appear (SBP mirrors IBP at first-derivative level;
  there is no clean identity for `D2`); restrict fields to node values;
  `∫μ dy → Σ w_j μ_j`; `∂_y → D`; do not over-integrate (aliasing is part of
  the variational object; the `−diag(D@A)` split-form correction *is* the
  aliasing residual). State-dependent weights `μ(y, Δs[u_core])` give a dense
  column in the response Jacobian from one node, and force the anchor
  decision (B.9) to be made explicitly.

### B.8 "Variational principle for Δs in instanton dynamics" (17 July) **[unrecorded]**

- Pointwise terms of the discrete `H_FP` are diagonal in the node index;
  coupling comes only from `D`/`D2` and from the `Δs` dependence (rank-one at
  the core).
- `Δs` is algebraic in the current core state (the ODE
  `dΔs/dN = 1 + d ln H_core/dN` integrates exactly to `delta_s()`'s closed
  form), so **no Lagrange multiplier is needed**: differentiate with the
  chain rule and do not freeze `Δs` inside the differentiated block. The
  multiplier formulation is shown equivalent (`P_elim = P_ext + P_Δ h`;
  second-class constraint; `Λ = ∂H/∂Δs` pointwise).
- **Defect:** `delta_s_derivative() = 1 − ε_core` is a *background identity*
  (it uses the homogeneous `π̇`); along the instanton `Δ̇s` picks up the
  gradient, advection and noise terms at the core, and since `A(1) = 2Δ̇s/Δs`
  it is an implicit (linear) scalar equation. `delta_s()` and
  `delta_s_derivative()` are inconsistent as written. This changes `A` in the
  forward sector and hence every `n=5` solve.
- Because `A` then depends on the response fields, the `y`-frame `H_FP` is
  not of standard MSR form; the `s`-frame is a genuine MSR problem on a
  moving domain and the `y`-map is a state-dependent relabelling.
- Measure mismatch flagged: the code's `measure()` is `e^{−1.5Δs y}`,
  differing from `V'` by a `Δs`-dependent prefactor; `∂H_FP/∂Δs` must see the
  same measure the action uses.
- Sequencing proposed: adjoint-residual check with `Δs` frozen versus live;
  reconcile `delta_s()`/`delta_s_derivative()`; then the SAT.

### B.9 "Principal symbol of wave operators" (16–17 July) **[unrecorded; the anchor decision in force]**

- Principal symbol as the quadratic form `M^{ab} ξ_a ξ_b`; `M^{ab}` is an
  inverse optical metric; characteristics are its null covectors; raising
  with the same `M` gives the tangent direction (self-orthogonality of null
  covectors); conformal factors such as `e^{−2Δs_loc}` move affine
  parameters, not cones; incoming iff `v^y < 0` at `y=+1`, `v^y > 0` at
  `y=−1`, no metric needed.
- After correcting the symbol to `M = {{1, −A}, {−A, A² − C²}}` (advection
  migrates onto the diagonal), `dy/dN = −A ± C`, hyperbolic unconditionally,
  but the count is conditional: one incoming at the core iff `|A| < C`.
- With a **background anchor** (`e^{Δs} = r_out/r_H^{bg}`, `ε_nl` in `A`),
  `C(+1) = (2/Δs) ρ` with `ρ = r_core/r_H < 1` for an overdensity, and the
  count is: 2 incoming if `ε_nl < 1−ρ`; 1 if `1−ρ < ε_nl < 1+ρ`; 0 if
  `ε_nl > 1+ρ`. Two small quantities compete (`ε ∼ 0.009` versus
  `δH/H ∼ 0.002` at `δN★ = 0.2`), the margin shrinks with `δN★`, and a
  zero-crossing mid-solve would change the admissible-BC count. David
  identified `ρ → 1` as a grid-mismatch: the domain excludes shells that are
  already super-horizon.
- **Reversal (David, 16 July):** go back to the core anchor,
  `Δs = ln(r_out / r_core(N))`, so `ρ ≡ 1` by construction and the window is
  `(0, 2)` unconditionally. Independent check: in exact de Sitter the
  outgoing rate `2ε_core/Δs → 0` (horizon marginally trapped) and the
  incoming rate `→ 4/Δs` (relative rate 2 in `ln r`); the background anchor
  passes neither. The near-tangency of the outgoing mode as `ε_core → 0` is
  physical for any horizon-anchored grid and `α`-independent (both speeds
  scale as `1/Δs`); the stiffness ratio `2/ε_core` is geometric.
- **Then (17 July):** `ρ ≡ 1` is the definition, so `Δ̇s` is *derived*, not
  posited. `ε = π²/2` is exact in FRW but its proof consumes the homogeneous
  `π̇` equation; the core row is not homogeneous. Hence **[Erratum E1]**
  `Δ̇s = [1 − ε_core + π_core 𝓛_core / (2(3−ε_core))] / (1 − K)`,
  `K = (1/Δs)[(V'/V)(Dφ)_core − π_core (Dπ)_core / (3−ε_core)]`, with
  `𝓛_core` the non-advective core forcing; closed form, linear, no extra
  state. `K → 0` at convergence (regularity) but the `𝓛_core` numerator
  survives (the Laplacian is maximal at a density peak). `K = 1` is a real
  singularity to guard. Whether the SAT belongs in `𝓛_core` was left open
  (argued no: it is a stabiliser, keeps the closed form clean, vanishes at
  convergence). David's final position: *"this is a self-consistent choice
  that is not right or wrong but simply 'this is the model'"*; the
  augmented-state (ODE for `Δs`) alternative was rejected.
- Consequence: `A`, `μ`, `Δs`, `n_count` are all state-dependent, so hand
  derivation of the adjoint is long and error-prone (the error "treat `Δs` as
  a coordinate" was made three times in the thread). This is the strongest
  argument for obtaining the response sector numerically.
- **Characteristic variable for the single penalty [Erratum E2]:** the incoming null
  covector is `(A + C, 1)`, so `w_in = (2(2−ε_core)/Δs) π_core + (Dφ)_core`,
  which is `π`-dominated in the near-de-Sitter limit (coefficient `≈ 4/Δs`,
  about 400 at `α = 0.01`). A rank-one penalty on `(Dφ)_core` alone is the
  characteristic projection only if `ε_core ≈ 2`. Called *"the single most
  actionable output of this thread."*
- Discrete action versus numerical Jacobian: both give adjoint consistency;
  the response equations are the variation of the same discrete action with
  respect to `(φ_i, π_i)` and the transpose appears automatically because `P`
  is a covector; **norm for stability, transpose for adjointness, never
  mixed.** `S` is linear in `P` but nonlinear in `u`, so vary with respect to
  `P` by hand (forward flow, SAT included) and obtain `−∂H/∂u` numerically.
- **Factor-of-two trap:** with `f = b + D(u)P`, `−(∂f/∂u)ᵀP` is *not* the
  response equation; the variational result has `½ P (∂D/∂u) P`. The object
  to implement is the scalar `𝓗(u,P) = P·b(u) + ½ P·D(u)·P`; both sectors are
  Hamilton's equations; the full Jacobian is `Ω Hess 𝓗` and the structural
  check is that `(Ω J_full)` is symmetric (three block identities), which
  replaces `E = J_resp + J_fwdᵀ` (valid only when `∂D/∂u = 0`, and then only
  against the full forward Jacobian including `∂_u(DP)`). "Response fields
  transport as the adjoint tangent map" holds iff `∂D/∂u = 0`; otherwise they
  are conjugate momenta of `𝓗`, and the paper should say so.
- Complex-step differentiation: `∂_j 𝓗 = Im 𝓗(u + ih e_j)/h` to machine
  precision; `2n+1` evaluations per RHS call; obstructions are `abs()` in
  `τ = |A_core|`, `min/max/clip`, and scipy splines (lagged Picard data,
  arguably constants under differentiation, which is a decision about whether
  the adjoint is of the lagged or the fully coupled operator). Second
  derivatives for Radau need hyper-dual/AD. Recommendation: keep the SAT
  **out** of `𝓗` (stabiliser, vanishes at convergence, preserves analyticity)
  and add it to the assembled RHS; this is in tension with B.7's "SAT as a
  term in `S_h`" and is **unresolved**.

### B.10 "Fixing FullInstanton response sector equations" (17–20 July) **[unrecorded]**

- With `H_FP = P₁f₁ + P₂f₂ + D₁₁P₁² + 2D₁₂P₁P₂ + D₂₂P₂²`, `fwd_rhs` is
  already exactly `∂H/∂p`; `bwd_rhs` keeps only the leading terms of
  `−∂H/∂u`. Full equations:
  `P₁' = P₂[V''/H² − ε_φ π − V' H²_φ/H⁴] − [D₁₁,φ P₁² + 2D₁₂,φ P₁P₂ + D₂₂,φ P₂²]`,
  `P₂' = −P₁ + (3−ε)P₂ − P₂[ε_π π + V' H²_π/H⁴] − [D₁₁,π P₁² + ⋯]`.
- **Not small:** the missing `P₁'` term is `−P₂ (V')²/(V H²) ≈ −6ε P₂`
  against the retained `V''/H² ≈ 3η_V P₂`; for a quadratic potential these
  cancel to a sign flip (`V'' − V'²/V = V (ln V)''`). The stored
  `S_MSR ∝ δN★^1.74 ΔN^{−0.72}` fit is contaminated at that order.
- FullInstanton's `H_FP` is autonomous and exactly conserved, with the
  terminal conditions pinning it in closed form:
  `H_FP = λ φ₂(N_total) + D₁₁(N_total) λ²`, hence
  `∂S/∂δN★ = −[λ φ₂(N_total) + D₁₁(N_total) λ²]`, every term already in the
  database (`final_lambda`, `phi2` at `N_total`, `D₁₁ = H²/8π²`). Proposed as
  prompt "25-00", a zero-compute measurement to run before any code change.
- Where derivatives should live if done analytically: `AbstractPotential`
  gains `depsilon_dphi/dpi`, `dH_sq_dphi/dpi`; `AbstractDiffusionModel` gains
  `dD_matrix_dphi/dpi`; a new `InflationConcepts/fokker_planck_hamiltonian.py`
  exposing `H_FP`, `dH_dp`, `dH_du` with the drift from
  `noiseless_equations`. Five prompts sketched: 25-00 identity audit on stored
  grids; 25-01 potential and diffusion partials with complex-step conformance
  tests; 25-02 Hamiltonian module; 25-03 `∂f/∂u` restoration with `H_FP` drift
  in `diagnostics_json`; 25-04 the `∂D/∂u` decision.
- **Open design fork (David, 20 July):** single source of truth (implement
  `H_FP` once, complex-step `bwd` at runtime, no helper partials) versus
  analytic response equations in production with helper partials and
  complex-step as a conformance test, versus the hybrid (helpers as interface
  objects pinned from below by complex-step and from above by conservation).
  Not decided. The earlier correction: complex-step *is* feasible through the
  production path for the shipped models (no logs, no `abs`).
- **Riccati (20 July):** restoring `∂D/∂u` makes the backward pass quadratic
  in `P`; the per-field `P = M₁/M₂` substitution does **not** linearise it
  because the `g(N)P₂` coupling defeats an independent ratio ansatz; the
  correct object is the matrix Riccati linearised by the `4×4` fundamental
  matrix of the `(φ,P)` Hamiltonian system (symplectic block solver).
  Exact `λ`-scaling breaks, the dynamic-range problem returns, and
  finite-`N` caustics (`M₂ → 0`) become a new failure mode distinct from
  `H²_local < 0`. The terminal condition must be mapped into the linearised
  variables. Forward sector, Picard structure, action form and both
  conservation identities are unchanged. FullInstanton is the right pilot.

---

## Part C0 — Repository documents contradicted by the June threads

| Document | Problem | Source |
|---|---|---|
| `handoff-notes/handoff_instanton_boundary_conditions.md` §3–4 | Presents the `ρ_final` boundary condition as the open question for "the next conversation"; that conversation (18 June) dismissed it as a false premise. | A0.1 |
| same, §2.1 | Records the `g*` correction as "~0.2 … omitted"; the shift is about `−1.1` in `ln k`, never agreed to be dropped. | A0.2 |
| `grid-sampling/handoff-{sparse-sampling,large-grid,goal2}.md` | Attribute the `ρ_final` failure to "a degrees-of-freedom counting issue", explicitly rejected on 18 June. | A0.1 |
| `grid-sampling/handoff-large-grid.md`, `handoff-goal2.md` | State the minimum-action pathway is the broadest collapsing perturbation ("critical bubble"); reversed by the 24 June fixed-`K` grids. | A0.3 |
| same, "Vennin exponent → 1?" | Rests on the `S = λ₀ δN★` identification retracted on 18 June. | A0.1 |
| `onion_model.tex` §scale-assignment | Says `CompactionFunction` uses "the same construction"; its `todo` was answered in discussion. | A.1 |
| `gradient-coupled-instanton/28-tau-study-diagnostics-8t-and-13.md` | Recommends a finer τ sweep that the 9 July discussion rejected. | A.3 |
| `regression_InstantonOutputs.py` | Column list predates prompt 14; cannot ingest current `scalar_data.csv`. | A0.3 |

All June and July `S_MSR`-bearing results (scaling fits, thresholds,
minimum-action locus, `r_max`/`r_peak` divergence, compute-time trends)
were produced with the defective FullInstanton response sector and must be
re-run after the Hamiltonian module lands; summary F §2 lists them claim by
claim.

## Part C — What the 10 July handoff notes get wrong or incomplete, in light of Part B

| Note / section | Status after 20 July |
|---|---|
| `HFP-STRUCTURE-STATUS.md` §1 (non-adjointness, `−M_SAT^T`) | Stands; extend with the response-sector characteristic analysis (B.1, 16 July). |
| `HFP-STRUCTURE-STATUS.md` §2(d) (`g_π` is a model closure supplying data) | **Reversed** (B.3): no data enters at the core; Neumann is the correct data-free closure; the `π_core` penalty is a flat-norm artefact. The single penalty should act on `w_in` (B.9), which is `π`-dominated, so the practical conclusion partly survives in a different form. **[Erratum E2]:** `w_in` is not `π`-dominated in general; the weighting is set by `Δs`. |
| `HFP-STRUCTURE-STATUS.md` §3 (Maupertuis test) | Stands; sharpened by the closed form `H_FP = λφ₂ + D₁₁λ²` (B.10). |
| `HFP-STRUCTURE-STATUS.md` §4 (dropped terms "understated") | Stands and is now quantified: leading order, sign flip for quadratic `V` (B.10). |
| `HFP-CALCULATION.md` §7 (tex plan) | Still the right skeleton, but written for the `μ` measure with the bracket; must be redone in the `V'` convention with `Z = 0`, `L(gπ̃)` ordering, core anchor and chain-rule `Δ̇s`. |
| `SAT-CLOSURE-STATUS.md` §6 (live-Neumann `g_π` versus model closure) | Both options are superseded: the answer is one characteristic penalty on `w_in`, derived variationally, in the `H_μ` norm, with the response sector obtained by transposition/differentiation. |
| `SAT-CLOSURE-STATUS.md` §4.1–4.5 (tests) | 4.5 (`H_FP = −∂S/∂δN★`) stands and is now cheap; 4.4 (abscissa sweep for live-Neumann-π) is moot; 4.1–4.3 are still informative as diagnostics of the *current* code but no longer gate a decision. |
| `onion_model.tex` eq. `inst-rphi`/`inst-rpi` | Bracket is a convention artefact (B.4/B.6); gradient term has the wrong operator ordering (B.4); variation is truncated at leading order (B.10). |
| `onion_model.tex` §coordinate (`ε_core = π²/2` in `A`, `Δs` from `H_core`) | Inconsistent pairing: algebraic `Δs` with a background `Δ̇s` (B.8, B.9). Needs the chain-rule `Δ̇s`. |
| `onion_model.tex` §msr-action "Choice of measure" | Self-adjointness does not fix the measure; the noise does, and selects `V'` (B.4). |
| `onion_model.tex` §bcs | Add: identity at `y=−1`; characteristic count at `y=+1` for both sectors; no data at the core; `w_in` as the penalised variable. |
| `onion_model.tex` §collocation-basis "Boundary conditions" | Describes hard elimination as production; must describe the single-characteristic SAT in `H_μ`, derived from a boundary term in `S_h`. |

---

## Part D0 — Decisions taken on 8 October 2026 (David, on reading this reconstruction)

1. **Single Hamiltonian module, differentiated at runtime, for both
   `FullInstanton` and `GradientCoupledInstanton`.** This closes Open 1
   below in favour of the single-source option, and resolves the 11 July
   versus 17 July tension (D.4a) in favour of the later position. The
   analytic adjoint equations for `FullInstanton` are still to be presented
   in the paper, as intuition-building material, but they are not the
   production implementation.
2. The LaTeX rewrite is **not** to wait for a pen-and-paper validation; none
   exists. The rewrite is itself the re-orientation tool. The by-hand check
   of the onion adjoint sector is unnecessary under decision 1.
3. The raw transcript dumps are kept in the working tree under
   `.documents/transcripts/` (git-ignored) so they are not lost, but are not
   committed to the public repository. Only distilled documents are
   committed.
4. The export window is to be extended back to 1 June 2026 and the June
   threads reconstructed in the same way. (Done the same day; see Part A0.)
5. **Automatic differentiation via JAX** is the method for the runtime
   differentiation of decision 1, in preference to complex-step, on cost
   (one reverse-mode pass versus `2n+1` complex evaluations), on the need
   for second derivatives in any implicit `N`-integrator, and on the
   non-analytic operations (`abs`, `min`/`max`, splines) that break
   complex-step silently. Complex-step remains the independent conformance
   test. The `N`-integration need not stay on `scipy.integrate.solve_ivp`;
   `diffrax` is acceptable to remain inside the JAX ecosystem.

## Part D — Decisions recorded as taken (by David) and decisions still open

**Taken:**

1. The model's coordinate scaffold is anchored to the core: `ρ ≡ 1`,
   `Δs = ln(r_out a H_core[φ_core, π_core])`, `Δ̇s` by the chain rule through
   the actual core row (17 July). Not "right or wrong but the model".
2. The core carries no incoming data; Neumann is the single, reflecting,
   data-free closure (11 July).
3. The measure is the physical volume element `V'`; the noise is white with
   respect to it with amplitude `2D11/n_count` (13–14 July).
4. Norm for stability, transpose for adjointness, never mixed (17 July). The
   response sector must be the exact discrete adjoint of the implemented
   forward sector; the current pair is not, and the current over-determined
   forward operator must not simply be transposed (11 July, Q2).
4a. **How** to obtain the adjoint is *not* settled: 11 July ruled "analytic
   for production and publication, numerical as oracle"; 15–17 July leaned
   to numerical differentiation of a single discrete Hamiltonian because the
   scaffold (`Δs`, `A`, `μ`, `n`) is state-dependent; 20 July left the
   FullInstanton version of the question open (see Open 1).
5. The LaTeX notes are not to be rewritten until the pen-and-paper
   validation is done (14 July). *Whether that validation exists on paper is
   unknown to this reconstruction.*

**Open:**

1. FullInstanton: single-source complex-step `bwd`, analytic with helper
   partials, or hybrid (20 July question, unanswered).
2. Whether the SAT is a term in the discrete action (dual consistency by
   construction; B.7) or kept out of `𝓗` (analyticity; B.9).
3. Whether the SAT belongs in `𝓛_core` when computing `Δ̇s` (B.9).
4. Whether to restore `∂D/∂u` (Riccati) and if so by direct integration or
   the symplectic block linearisation; the FullInstanton pilot is meant to
   decide this (B.10).
5. The indicial analysis of the response sector in the `V'` convention near
   `Δs → 0`, and hence whether `α` can be reduced (B.4).
6. Scale assignment: `Δs(N_final)` in the comoving ratio under the core
   anchor, and the GCI-versus-FullInstanton mass attribution (B.6).
7. The MSR↔spectral bridge via the adjoint backward-Kolmogorov eigenproblem
   (B.2) — a research item, not a code item.
