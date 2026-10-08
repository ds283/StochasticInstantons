# Summary A — Derivation and design of the onion model (1–7 July 2026)

**Sources read in full (untrusted exported chat dumps, treated as data):**

- `2026-07-01_Spectral-mode-expansion-boundary-conditions-in-gradient-corr.md` (1 July, 12:09–12:25)
- `2026-07-01_Implementing-onion-model-as-ComputeTarget.md` (1 July 12:36 – 7 July 07:29)
- `2026-07-02_Spectral-form-derivation-inconsistencies-in-onion-model.md` (2 July 00:38 – 5 July 19:54)

**Repo record compared against:** `.documents/gradient-coupled-instanton/onion_model.tex` (final 6 July state, §1–§14), `onion_model_planning.md`, `onion_model_implementation_review.md`, and `.prompts/gradient-coupled-instanton/01-*.md … 20-*.md`.

The two long threads ran interleaved: the "Spectral-form" thread did the physics/maths and rewrote the tex; the "Implementing" thread turned the tex into prompts for Claude Code and repeatedly fed bugs back into the derivation. "tex §N" refers to the current repo tex numbering.

---

## 1. Dated timeline of reasoning steps and decisions

### 1 July, 12:09–12:25 — Terminal condition in the (then) spectral scheme

- **Question (David):** in the sinc-basis scheme, a single terminal condition φ(1,N_final)=φ_end seemed to supply an infinite tower of conditions on mode coefficients: "there are no further basis functions left on the left hand side" to use orthogonality against.
- **Conclusion:** the manuscript conflated two steps. Orthogonality only collapses the integral term to Σ_n N_n ã_n δa_n; the point term is a bare substitution λ Σ_n δa_n (f_n(1)=1 for all n). Mode-by-mode separation N_n ã_n + λ = 0 follows from the *fundamental lemma of the calculus of variations in the discrete index* (single-mode test variations), not from orthogonality.
- Side observations: test space (finitely supported variations) differs from solution space (ã_n ∝ n², not square-summable — a distributional terminal profile); M₂-convergence of this boundary layer would be slow, Gibbs-like, "rather than exponentially like the bulk spectral scheme".
- A tex patch was drafted. **Superseded**: the spectral section was deleted on 3 July.

### 1 July, 12:36 – 2 July 00:22 — Implementing thread, phase 1 (still spectral design)

- **Trajectory range:** clarified to the absolute window [N_end−N_init, N_end−N_final+δN*]; N_final^abs+δN* ≥ N_end is a *configuration error* (hard abort), "not even wrong", not a convergence failure.
- **Naming/storage decisions:** class `GradientCoupledInstanton` (David will say "onion model" in the write-up but wanted something descriptive in code). Same notation as `FullInstanton`: phi1=φ, phi2=π, P1, P2, CTP condition P2(y,N_end)=0. Response fields must be persisted "so that we can check the amplitude of the noise realization… in Hawking units". `y` grid as a shared persisted concept (`y_value`, ascending 0→1: "it just poses the question why we didn't define y' = 1 − y"). No persisted time-resolved ζ(y,N); "the final zeta(r) and the C(r) are what's needed for science results".
- **ζ extraction — fixed-energy-density matching.** David: compare at fixed ρ, "zeta = N − N_noiseless". Gap: at fixed y there is a whole column in N; which N? Candidates: crossing of φ_end vs. downflow to ε=1.
- **ε=1 is not a fixed-density surface** (18:27–18:29). David: "is the end-of-inflation hypersurface always a surface of fixed energy density? it doesn't seem to be". Checked against `AbstractPotential`: ε = π²/2M_p² depends only on π, so ε=1 is a fixed-momentum surface and ρ|_{ε=1} = (3/2)V(φ_end) varies. Conclusion: the recipe survives because it never needs ε=1 to be iso-density — each shell's ε=1 point is used only as "sufficiently late that we trust adiabaticity", then density-matched against the background at a general N (standard δN-conservation argument).
- **Do not take the optimization.** David: noise decays outside the horizon but "the response fields can compensate for that by becoming large", being non-locally constrained by the core's shooting condition; compute the full per-shell downflow unconditionally; the shortcut discrepancy becomes an empirical check later.
- **Scale assignment, Options (1) vs (2)** (18:55–19:08). Option 1: geometric map r=(1−y)/(aH)_0 (flat-gauge-like). Option 2: Step-C-style per-shell horizon-crossing scale from the shell's own downflow (uniform-density slicing). David: "This has the flavour of a gauge issue… it's the Option (2) measurement that sets the physical distance measured in the late universe." Monotonicity condition is 1 + rζ′ > 0 (not monotonicity of ζ) — the type-I/II boundary already in C(r)=(2/3)[1−(1+rζ′)²]. Decision then: "we don't need to map from y to r at all" at solver level. **Reversed on 5 July** (single outer anchor + comoving ratio).
- **Time-resolved access:** one primitive extract(φ,π,N_abs)→(ζ,r); APIs `zeta_r_at_time`/`zeta_C_r_at_time`; a fixed-N<N_final slice is "an artificial, illustrative freeze… not a physical construction". Identity-keyed in-process cache behind an `ExtractionCache` wrapper (Ray object store/Redis later). David rejected the "validation/talk-prep tool" framing: "We're building a tool that will do the job."
- **Prompts 0001–0005** (y_value, mode_truncation, ExtractionCache, noiseless lift, sinc basis). Basis written in y not u ("Do we have to use u?"); modes start at n=1 (sinc(0)=1 is degenerate with the pinned exterior; N_n undefined at n=0). Concern that the 1/N_n ∝ n² projection factor amplifies quadrature error beyond n_max≈128 — "That may not be easy to fix." **All reverted 4 July** (repo reset; `ExtractionCache` cherry-picked).
- **2 July 00:22 — two issues raised:** (i) H, ε bare background symbols while V(φ) local; (ii) missing lift-residual term in ḃ_n, [1]_n ≡ (1/N_n)∫(1−y)² f_n dy = 2(−1)^{n+1}, O(1) and alternating. David: "I think both of these are problems."

### 2 July, 00:38 – 15:28 — Spectral-form thread, phase 1: locality fixes

- **Local H², ε in the dynamics** (David): "It's not consistent to keep the y variation of V, but ignore the y variation of H (because V is in H)." Friction becomes −[(3−ε(φ,π))π]_n, no longer diagonal. The suggestion that (1−ε) in the noise normalization could stay background was rejected: "Just use the local value of phi on the trajectory."
- **Covariance symmetrization:** David asked whether a two-point covariance between shells with different fields needs symmetrizing. Conclusion: at the retained order only same-shell pairs are correlated (sinc range ≪ shell width); the cross-shell piece is the N_i^{−1/3}-suppressed term already dropped; nothing to symmetrize.
- **Cross-diffusion D₁₂** (David): the note was diagonal-only; `FullInstanton` already uses `2*D12`. Added D_{φπ} with coefficient 1 (not ½) in the action, and to instanton/mode equations. D_φ ≡ 2D₁₁/n etc. Zero for `MasslessDecoupledDiffusion`.
- **Local D_ij:** David suggested y-dependence was already covered by n(y,N); conclusion: no — geometric dilution and local single-patch amplitude are two independent sources.
- **[1]_n term folded in** with the a_n/b_n asymmetry explanation (kinematic identity vs dynamical background EOM). David: it "couples the b_n mode equation to the absolute difference between the shell trajectory and the noiseless trajectory… Somewhere, we need to absorb the difference." Sharpened: the term is what makes a_n=b_n=0 a fixed point (otherwise ḃ_n = −[1]_n F(φ_nl,π_nl) ≠ 0 with no coupling). **Moot** after the rewrite but it is the ancestor of the reduction-limit test.
- **aH in the Laplacian** (07:49–15:15). Assistant first argued background-only (Briaud's linear treatment; one comoving metric). David: "This is just using the local metric in the shell to evaluate the derivative with respect to physical length… one should also use the local value of N". Reversal: a local *coefficient* does not touch the operator/eigenbasis; Briaud's excuse (δφ small) fails at O(1) deviations. Settled: **a(N) is a pure function of the grid N** ("We shouldn't relate the time coordinate back to the noiseless trajectory"), **H local** (`\aHloc`). Remaining dropped effect: the **tilt between constant-N and constant-proper-time slices** across shells (shift-vector-type), same order as dropped ∂D_ij/∂φ feedback.
- Flagged, never checked: whether the lift residual touches the Lagrange-multiplier terminal derivation (moot).

### 3 July, 06:29 – 09:52 — n(y,N), k_σ, and the sub-horizon noise crisis

- **k_σ never enters a computed quantity** — derivation scaffolding only.
- **n(y,N)** derived by David as V_shell/V_horizon with the *local* horizon volume, fixing the constant; assistant: n must be a density dN_patches/dy because D_φ = P/n feeds δ(y−y′).
- **Sub-horizon noise (David):** with y covering the interior, "I don't think there should be any noise interior to the horizon… it allows trajectories to diverge on subhorizon scales." Options: (a) noise off for y>y_H(N) — core never noisy, final BC impossible; (b) same realization for y>y_H(N) — P1, P2 constant there; (c) exterior-only y — time-dependent eigenfunctions. Assistant: (a) also fails the reduction limit; proposed a noiseless-background proxy for y_H — **rejected** ("I also don't think using the noiseless background horizon scale is adequate"). David: "I don't think the fact we have rejected options in the past should be given any weight… We can only choose among options that actually exist." Written into the tex as *blocking*; a rank-1 shared-noise-channel action term drafted as "leading candidate" (**retired the same day**).
- **ζ extraction section stale** (still the φ_end crossing scan); replaced with downflow + density match recovered from the 1 July thread.

### 3 July, 10:46 – 19:08 — Option (c) wins; collocation; the logarithmic coordinate

- **Exterior-only linear coordinate** y=1−(r−r_H)/Δr: operator shape N-dependent (r² intercept), advection −y (r_H/Δr)(1−ε_core)∂_y; r_H→0 recovers the old scheme.
- **David:** "We're not forced to use exact eigenfunctions… they're just especially convenient" — Galerkin on a fixed basis, or genuine collocation. Assistant: collocation cleaner (point values; only scalar coefficients update), Chebyshev D² non-normal so SBP needed for structure.
- **"The actual core is now outside the domain… what represents it?"** David: "The horizon-scale fields are still those evaluated at y=1… nothing changes." Reframing: Neumann at y=+1 is a *physical smoothness-of-attachment assumption* (no independent sub-horizon structure), not spherical symmetry; mixed BCs remain well-posed; the sub-horizon problem becomes a boundary condition. Caveats: Δr→0 if r_H→r_out; domain extent fixed from its own boundary data.
- **Node allocation:** CGL over-invests at the outer edge; stretching maps (tanh, Kosloff–Tal-Ezer) or two-domain elements discussed; David: standard nodes "until we know whether we need more resolution/efficiency".
- **Neumann in collocation:** hard elimination φ_N = −(1/D_NN)Σ_{k≠N}D_Nk φ_k; SBP+SAT as the structure-preserving alternative.
- **Three meanings of "self-adjointness"** (David): Picard/RK solver stability; response equations as adjoints ("doesn't happen in our case"); self-adjointness of the y-Laplacian, whose diagonalization payoff vanishes under collocation. Assistant: (3) was meant, and there is a separate numerical reason (Chebyshev D² non-normality with explicit stepping; SBP gives real non-positive spectra); a self-adjoint form "is close to automatic for radial operators".
- **Logarithmic coordinate** (David, with the δN*=13 plot): profile ≈ power law in r, so y logarithmic in r — structural fix for exponential resolution. Domain [−1,1].
- **SBP/SAT explained; CGL→LGL** ("there is no cost to switching from Chebyshev to Legendre"); caveats: Jacobi-eigenvalue node generation (FastGaussQuadrature.jl, sphglltools), no fast transform.
- **Decision (17:22):** "exterior only + log transform + LGL + SBP/SAT" inside Lagrange multiplier + shooting + Picard, "a highly sophisticated numerical setup, but we know already that Lagrange multiplier + shooting + Picard iteration works well."
- **Composed Laplacian:** s=ln(r/r_out), y=−2s/Δs−1, Δs=ln(r_out/r_H); ∇²φ = r^{−2}[(4/Δs²)∂_y² − (2/Δs)∂_y]φ; A=(y+1)(1−ε_core)/Δs; dln r_H/dN=−(1−ε_core), no extra ODE. Measure ∝ r³ ∝ e^{−(3/2)Δs y}.
- **"Two different things called self-adjointness"** (David: "for the LGL/SBP discussion I can't see that this ever knows about the existence of the exponential"): continuum self-adjointness is spent capital; standard LGL/SBP assumes the flat measure, which our drift operator is not self-adjoint under. Coherent pairings: "plain D² + hard elimination" or "transformed operator + SBP/SAT".
- **Sturm–Liouville reduction verified:** (q−p′)/p = −(3/2)Δs constant; μ = e^{−(3/2)Δs y}; μ = physical volume (Green's theorem).
- **Flat-measure Schrödinger form rejected** (Δs≈20.7 for δN*=13, ≈9.2 for δN*≈1.5): x(y)=(2/Δs)(1−e^{−Δs y/2}), zero residual potential, but x-domain width ~3×10³ / ~22 — reintroduces the exponential compression. **Decision: weighted measure on y; hard elimination first, SBP+SAT swappable fallback.** "If it works, we stop."
- 18:29–19:08: full tex rewrite §4–§13 and planning rewrite; response-field advection-adjoint terms derived fresh, flagged as not independently cross-checked.

### 3 July 21:51 – 4 July 09:35 — Implementing thread catches up

- Repo reset to before prompt 0001; `ExtractionCache` cherry-picked.
- **Noiseless-lift utilities not needed** (David): the Dirichlet row sets φ_0=φ_nl(N).
- **Both φ and π pinned at y=−1** (David): "It seems impossible that the y=−1 exterior shell can be noiseless, have phi… match… and yet have pi… not match." Tex already said both plus P1=P2=0 there; kinematic and MSR arguments agree.
- `InflatonTrajectory.phi_at/pi_at/rho_at` already dense — "That's really the right place for these to go."

### 4 July 09:42 – 5 July 13:20 — Δs(N_init)=0 singularity, α, and scale assignment

- **Singularity (David):** Δs=0 at N_init so 4/Δs², 2/Δs, A∝1/Δs diverge; also n∝Δs→0 so D_noise∝1/Δs. Same failure as the originally rejected horizon-anchored coordinate.
- **Frobenius expansion:** with δφ=Δs·h(y), δπ→p_0(y), the O(1/Δs) second-derivative gradient and advection pieces must cancel: 4(aH)_0² h″ + (y+1)(1−ε_core)p_0′ = 0 — a consistent forward-sector leading order. **Response sector not checked.** Reframing: in s the problem is regular on [−Δs,0]; "The entire singularity is manufactured by insisting on a fixed collocation domain". David: "The underlying problem itself is perfectly regular."
- Alternatives: integrate in s (moving boundary), padded domain (interior moving condition; could revive rank-1 as a masked node sum), start 0.1 e-fold late (coarse-graining transient near the centre). David: "minimum violence to the underlying model".
- **α-regularization (David, 5 July 08:41):** r_out=(1+α)r_H(N_init) ⇒ Δs_α=Δs_0+ln(1+α), a constant shift regularizing everything; a thin shell asserted noiseless; late-time insensitivity (Δs_0(N_final)~9–21); stiffness trade-off for small α; scan and extrapolate. Shells between r_H(N_init) and r_out "will still have the option to experience stochastic evolution… I don't think that is necessarily a problem."
- **Two identical shells get the same radius** (David, 09:09) under a downflow-duration assignment. Diagnosis: in the peeling scheme r_i=1/[a(i)H(i)] *defines* radius via trajectory position; the continuum model has an independent comoving r(y,N).
- **Anchor choice:** core anchor circular; **outer-edge anchor = noiseless background**. Three radii: comoving r, areal R=a r e^{ζ}, Leach–Liddle r_phys. David: C(r) "is phrased in terms of the ordinary comoving coordinate r… we seem to need to know zeta(r), not zeta(R)" — agreed. R(r) is "well defined… but… a bit unclear what is the operational significance"; answer: NR-calibration input, not an observable.
- **Per-shell N(k) inversion retracted.** David: "r_phys = (r/r_out) · r_phys_out. Then we're done." Comoving-ness makes today's conversion one universal constant.
- **Equivalence check:** r_phys,core = r_phys,H(N_final) matches the peeling scheme's innermost shell *provided* the discrete code uses the instanton's local a,H — todo; O(α) corrections.
- Tex/planning updated; the **r_out·(aH)_0=1 identity** found silently assumed in the Laplacian prefactor, instanton equations, discretized L (double-counted prefactor) and n(y,N); fixed to r_out^{−2} and r_out·aH_loc. Lift prompt removed.
- **5 July 19:52:** David caught "w = 1/μ"; corrected to w = μp, μ = w³; the integration-by-parts steps were unaffected.

### 5 July 13:56 – 6 July 02:30 — Prompts 01–06 and the response-sector sign fix

- `n_max` is the degree; grid has n_max+1 points; persist `n_collocation_points`, one named property does the subtraction. Default degree 16 as a named constant.
- **No absolute r_H or r_out anywhere** (David): Δs(N)=ln(1+α)+(N−N_init)+½ln(H²_core/H²_nl,init); ratios only until the final anchor.
- (aH)_loc prefactor per node = e^{−2Δs_loc}. David: "Most occurrences are shell-local".
- **Reduction limit must zero advection too** — "the previous framing came from a time when there was no advection term."
- **Response-sector sign error** (6 July): tex had −(3−ε)π̃ vs `bwd_rhs` +(3−ε)P2; no ±relabeling fixes self-friction. David's tex fix: every term flipped and a **missing measure-friction term −(μ̇/μ)X**; the y-dependence cancels, leaving c(N)=(1−ε_core)[1/Δs−3/2]. David asked whether forward sourcing should change too; re-derivation from the action: an algebra slip in the harder variation, not a change of the response rotation φ̂=iφ̃, so the forward sector is untouched.
- Factor 2 convention already in tex; `D_matrix` scalar-only. David on optional sourcing in `forward_rhs`: "the tail wagging the dog" — made mandatory.

### 6 July 03:25 – 10:00 — N convention; ζ extraction; prompts 07–10

- Claude Code flagged `delta_s` vs `phi_before_end` conventions. David: "N for the instanton starts at zero and increases… N_init and N_final are measured positively backwards from the end of inflation." N_total=N_init−N_final+δN*, N_offset=N_end−N_init once, Δs(0)=ln(1+α) exactly, guard in `delta_s`.
- **ζ extraction is a refinement beyond `CompactionFunction` Step B** (which matches without downflowing); tex's "same construction" is overstated. David: negligible in single-field; `FullInstanton` "would need to be changed" for isocurvature. Code comment added.
- **N_offset is an absolute e-fold** (David corrected the assistant's description).
- Prompt 09's reduction test was an `ln_k` linearity tautology; prompt 10's independent core downflow pinned at e^{−Δs}; the assistant first wrongly recommended removing it.

### 6 July 10:58 – 18:10 — Anchor bug, slicing ambiguity, `ln_k_phys_Mpc` bug

- **David's reading of `CompactionFunction`:** downflow from the endpoint, then work backwards assigning N_before_end. Outer layer: N_downflow+(N_init−N_final+δN*) there vs N_downflow,noiseless+(N_init−N_final) in GCI; r_out vs r_H(N_init) differ by (1+α), which "should be reflected in the test".
- **Anchor bug:** `assign_scales` anchored r_phys,out via the outer edge's downflow from the *end* of the transition (horizon at N_final), off by ~e^{N_total}(1+α). Fix: feed `ln_k_phys_Mpc` N_init with the noiseless start-state and true V_end; multiply by (1+α).
- **Physics ambiguity:** outer-layer scales differ by ≈e^{δN*}/(1+α). David: "a genuine physics ambiguity… we're using a separate universe calculation in a physical situation where it's on the verge of breaking down"; the discrepancy "amounts to saying that the separate universe framework can't handle the distortion between spatially flat and uniform energy density hypersurfaces". **Decision:** re-anchor `CompactionFunction` at the outer edge, work *forward*, keep per-sample Leach–Liddle with local (V_i,ε_i) (option (a)); N_before_end,i = N_init − N_inst,i by arithmetic; endpoint downflow dropped for scale assignment (kept for ζ in GCI).
- **0.5 vs 0.25 trail:** Claude Code found ~42% α-independent core discrepancy. David: "Your general claim was correct… The problem must be somewhere else", then asked whether `0.5*log(H_sq_local/H_sq_nl_init)` was the culprit and whether 0.25 would close it. It would — hence "The error must be in the matching equation implemented in `ln_k_phys_Mpc`", which "predicts that the physical scale varies with H (at fixed N) like H^(1/2), which directly contradicts… k = aH." The old `0.25*log(V_k/(V_end*(1−eps_k/3)))` merged two pieces: V_k at power ½ (from H_k) with (1−ε_k/3), V_end at −¼ with the fixed 3/2 (ε_end≡1). The assistant mis-stated the coefficient, then the sign ("You have the sign of the log(V_end) term the wrong way round"); David validated by hand. **Pre-existing bug in the production mass/scale assignment**, surfaced by the equivalence test.
- **Rewrite in terms of H** (David): "we're not supposed to assume a form for the Friedmann equation outside `AbstractPotential`… I'm reluctant to bake in forms of the Friedmann equation that don't generalize." Final: `ln_k_phys_Mpc(N_before_end, H_k, H_end, units, cosmo)` with −¼log(3H_end²/M_p²)+½log(3H_k²/M_p²); two call sites; agreement 1e−15 (same method), 2e−10 (collocation vs solve_ivp). Cross-target check at the innermost sample; intermediate scales cannot be compared ("we don't know which y value corresponds to which intermediate point").

### 6 July 18:10 – 23:59 — Persistence, noise statistics, MSR action

- Prompt 13: `n_collocation_points` (exact lookup) and `alpha_regularization` (tolerance-banded), replicated.
- Prompt 14 (David): parent table parallel to `FullInstanton` incl. noise stats and `msr_action`; `GradientCoupledInstantonValue` keyed by `efold_value` with φ, π, rfield, rmom node arrays; ζ(y,N), C(y,N), r_phys(y,N) on the fly via `ExtractionCache` ("No option here but to build it and see"); small unconditional profile table; guard N_offset ≥ 0, δN* ≤ N_final; MSR action deferred.
- **Noise stats:** Hawking-σ units as `FullInstanton`; intentional: core node only, *diluted* coefficients in σ, `np.any` guard.
- **MSR quadrature:** LGL weights × μ in y, trapezoid in N, full three-term form (not `FullInstanton`'s D₁₁P₁² special case).
- **n_count(core)=(3/2)Δs ≠ 1** so the core stays diluted and c(N) survives even decoupled; the existing reduction test matched only by algebraic construction; hand-computed test added (prompt 15 Part A).
- **On-shell sign:** +½D_φφ̃²+D_{φπ}φ̃π̃+½D_ππ̃², since the linear bracket is the noiseless drift which on shell equals the noise source. Confirmed by re-derivation. (A possible factor-of-2 vs `FullInstanton`'s `D11*P1²` was raised in the assistant's interrupted reasoning and not followed up.)

### 7 July — Decoupled limit, review, stiffness

- **Delta-function reduction (David):** noise "proportional to the covariant delta function delta(y−1)/measure" should reduce the 2D action to the 1D one. Assistant: provable that decoupled non-core response fields vanish identically; but the core's equations still carry (3/2)Δs dilution and c(N); the action-value agreement left as an empirical diagnostic (David: "If it does not agree perfectly I will want to understand why, but I don't think this should be regarded as a bug").
- **Degenerate shooting under full decoupling** (Claude Code; confirmed): Neumann elimination from background neighbours with zero-row-sum D pins φ_core to the background for any λ; "the core's own sourced derivative… is structurally discarded". David: "the field value is determined by the zero derivative condition there." Prompt 16 Part 2 blocked.
- **Review** read: method of lines, conditioning traded for RK45 stiffness; F4 (one NaN node poisons all of C(y)) up-ranked; plan: assembled-operator eigenvalue sweep + per-solve instrumentation into `diagnostics_json` (David: "I dislike scraping terminal output"), `instrument_stiffness=True` switch with bitwise-identical physics; try Radau/BDF before SBP+SAT.
- **Sweep (7 July 07:29):** assembled operator vs FD Jacobian 1.3e−10; stiffness concentrated at small Δs near N_init, O(n⁴) (steps/e-fold 268→153 694 for n_max 8→192), wide-Δs benign — the review's worry inverted; α buys ~10×. Recommendation: selectable Radau/BDF, measure first; analytic Jacobian and hybrid integrator left as questions.

---

## 2. Is each substantive conclusion recorded in the repo?

Legend: **REC** recorded; **PART** partial/indirect; **NOT** absent from tex/planning/review (may exist only in a prompt file or code).

**Physics / coordinate / action**
- Local H², ε; a(N) pure grid function; H local; shell-local default — **REC** tex §2.2 panel, §4.3 panel, §5, §6, §8.
- D₁₂ cross term; D_φ=2D₁₁/n — **REC** tex §5, §7.
- Local D_ij vs geometric n(y,N) — **REC** tex §5 panel.
- No symmetrization needed for the two-point covariance — **NOT**.
- k_σ never enters a computed quantity — **NOT**.
- Slicing tilt (constant-N vs constant-proper-time) dropped at the same order — **NOT** (§8 panel lists dropped feedback terms only).
- n(y,N) density; n(1,N)=(3/2)Δs — **REC** tex §5.
- Sub-horizon noise problem, options, rank-1 retired — **REC** tex §13.1 (summary; detailed rank-1 term gone).
- Exterior-only coordinate "previously rejected, now viable" — **REC** §4.1 panel.
- Linear-r exterior intermediate — **NOT** (superseded).
- Neumann at y=+1 as smoothness assumption; Cauchy ill-posedness — **REC** §9.1.
- Log coordinate motivation — **REC** §4.1, §4.3.
- Composed Laplacian, advection, dln r_H/dN — **REC** §4.2–4.3; planning.
- SL reduction, μ = physical volume — **REC** §4.3.1.
- Flat-measure form rejected with Δs numbers — **REC** §4.3.1 panel.
- Two meanings of self-adjointness; LGL/SBP assumes flat measure — **REC** §11 + panel; planning. David's three-way taxonomy — **NOT**.
- Chebyshev non-normality rationale; LGL diagonal norm — **REC** §11, review §5.2.
- w = μp, μ = w³ — **REC** §7 panel.
- Response sign fix, measure-friction term, c(N) — **REC** §8 calculation panel.
- Forward sector unchanged by the response fix — **PART** (implicit).
- Response rotation φ̂=iφ̃ — **REC** §7.2.
- Δs=0 singularity, Frobenius forward cancellation, s-reframing, response sector unverified — **REC** §4.1 panel (qualitative). Explicit relation 4(aH)_0²h″+(y+1)(1−ε)p_0′=0 — **NOT**.
- Padded-domain/masked-rank-1 and late-start alternatives — **NOT** (no "padded"/"0.1 e-fold" in tex or planning despite the checklist).
- α regularization — **REC** §4.1 panel; planning.
- Interior-of-r_out shells remain stochastic by choice — **PART**.
- r_out·(aH)_0 ≠ 1 fixes — **REC** §4.3, §5; planning.

**ζ extraction and scale assignment**
- Downflow-then-match; uniform-density vs flat slicing — **REC** §10; planning.
- ε=1 is fixed-π not fixed-ρ; adiabaticity argument — **NOT**.
- Rationale for the mandatory downflow (response fields compensate decaying noise) — **NOT**.
- Type II / 1+rζ′>0 — **REC** §11.2.
- Two-identical-shells paradox — **NOT** (only its resolution).
- Outer anchor; single Leach–Liddle solve; ratio propagation; inversion rejected — **REC** §11.3 + panel; planning.
- Areal radius role; C(r) needs ζ(r) — **REC** §11.2.
- Equivalence check todo — **REC** as todo §11.4. **Resolved in discussion** (code uses local `phi1_arr`) — resolution **NOT** recorded; tex still open.
- (1+α) on r_phys,out; anchor at N_init not N_final — **NOT** in tex/planning (prompt 11, code only).
- `CompactionFunction` re-anchored forward with N_before_end=N_init−N_inst; e^{δN*}/(1+α) outer-layer discrepancy; separate-universe interpretation — **NOT** in tex/planning (mechanics in prompt 11 only).
- Tex §10 "same construction CompactionFunction already uses" is overstated — **NOT** corrected (code comment only).
- `ln_k_phys_Mpc` bug and H-based rewrite — **NOT** in tex/planning (prompt 12, code). `.documents/NUMERICAL_SCHEMES.md` mentions ln_k; not checked for the old formula.

**Numerical scheme / implementation**
- LGL refs, D once, hard elimination first, SBP+SAT fallback — **REC** §11; planning.
- Terminal condition on boundary node — **REC** §12.3; planning.
- Grid stretching / node allocation options — **NOT**.
- Galerkin-on-non-eigenbasis alternative — **PART**.
- n_max = degree; single subtraction property — **REC** §11.1; prompt 01. Planning uses `n_max` loosely.
- No absolute radii; Δs closed form — **PART** (review §3).
- N convention / N_offset — **PART** (review §4.2; prompt 07). Tex formal; planning silent.
- `disable_spatial_coupling` zeroes advection too — **PART** (planning still says "L term zeroed").
- Decoupled limit ≠ `FullInstanton` at the core (dilution, c(N)); δ(y−1)/μ picture — **NOT**.
- Degenerate shooting under full decoupling (zero row sums) — **NOT** anywhere; no prompt 16 file exists.
- On-shell action sign — **PART** (review §3, `msr_action.py`); **NOT** in tex.
- Quadrature strategy; trapezoid O(h²) confirmed — **PART** (review; prompt 15).
- n_count test cancellation; hand test — prompt 15 only.
- Noise stats conventions — **REC** review §2.1.
- Storage design; "artificial freeze" caveat; cache escalation plan — **PART**/**NOT**.
- Stiffness sweep findings and Radau-before-SBP recommendation — **NOT** in the three compared docs (later notes 21–24 postdate scope).

---

## 3. Open questions, doubts and "check later" items never resolved in these threads

1. **Response-field sector at Δs→0** — cancellation never analysed; left to the α scan (open in tex §4.1).
2. **Does the 2D on-shell action equal the 1D action in the decoupled limit?** David expects yes; dilution and c(N) survive decoupling; the empirical check was blocked by the shooting degeneracy. (A separate 6 July "MSR-action-normalization" thread addresses the δ-function limit; not in scope.)
3. **Possible factor of 2** between ½D_φφ̃² and `FullInstanton`'s `D11*P1**2` — raised, not followed up.
4. **The decoupled-limit degeneracy** — how to build any non-trivial reduction test; whether partial decoupling helps; whether Neumann elimination is right in that limit. Left at Claude Code's three options.
5. **Interior-shell scale ambiguity** between `CompactionFunction` and GCI (agree at both ends, not between) — attributed to separate-universe breakdown; unquantified.
6. **ζ shortcut vs full downflow** discrepancy — to be measured on a batch of solved instantons; not done.
7. **Tex §11.4 todo** answered in discussion, tex not updated.
8. **1/N_n amplification** — moot after the rewrite; never revisited.
9. **Lift residual vs terminal derivation** — flagged, never checked; moot.
10. **Slicing tilt and ∂H²/∂φ, ∂D_ij/∂φ, ∂A/∂φ feedback** — dropped by order counting; validity at O(1) deviations unexamined.
11. **Operational meaning of R(r)** — David remained "a bit unclear"; accepted as well defined.
12. **Coarse-graining transient near N_init** — raised with the late-start option; not resolved by α.
13. **Analytic Jacobian for Radau; global implicit vs hybrid** — the final open questions of the thread.
14. **Performance of on-the-fly ζ(y,N), C(y,N), r_phys(y,N)** — "build it and see".
15. Whether `NUMERICAL_SCHEMES.md` still carries the old `ln_k_phys_Mpc` formula — not checked.
16. The two theoretical issues (probability interpretation of S_MSR; largest-time equation) — recorded in tex §13.2–13.3, untouched here.
17. Review F3 (msr_action never cross-validated non-trivially), F4 (NaN poisoning), F5 (α-scan, scale-equivalence, terminal-placement checks) — acknowledged, not done.

---

## 4. Explicit plans and intentions for future work

- **Hard elimination first**; "If it works, we stop (until we find a problem where it fails). If it does fail, we keep it as a backup/cross-check and build the SBP+SAT version", swappable via the `CollocationGrid` ABC.
- **α-sensitivity scan** (geometric spacing, extrapolate to 0); **n_max convergence scan**; verify `n_quad`-type assumptions empirically.
- **Stiffness:** wire selectable Radau/BDF; measure with the per-solve instrumentation before building SBP+SAT; hybrid only if implicit-everywhere is too slow; decide on an analytic Jacobian. Write an **analysis script for `diagnostics_json`** (out of scope for prompt 17).
- **Prompt 16 Part 2** as a non-asserting diagnostic once a non-degenerate decoupled configuration exists — "the answer will be illuminating".
- **Update the tex:** remove the resolved §11.4 todo; record the (1+α) anchor, the `CompactionFunction` forward-anchoring change, the `ln_k_phys_Mpc` correction (currently only in prompts/code); note the degeneracy finding in docstrings and "worth a note in onion_notes.tex too".
- **Deferred pipeline work:** grid-builder/argparse/sharding wiring for sweeps over n_collocation_points and α; heatmap/movie plotting via `zeta_C_r_at_time`; harden ζ→C against NaN nodes; independent MSR-action cross-check.
- **Consolidation:** refactor `CompactionFunction` onto the shared extraction primitive eventually; `FullInstanton`'s match-without-downflow "would need to be changed" for multi-field/isocurvature models.
- Cache backend upgrade (Ray object store / Redis) behind `ExtractionCache` if ever needed.
- Discrete finite-shell implementation kept as an independent cross-check (tex §3 panel).
- Write-up will use the term "onion model".
