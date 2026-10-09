# Open issues in the onion-model calculation

**Last updated:** 2026-10-09 · **12 open**, 1 closed.

This board tracks issues with the *calculation* recorded in
[`onion-model/onion_model.tex`](onion-model/onion_model.tex): the physics,
the derivation, and the numerical scheme as specified there. It is the
record for those issues; the project-wide index
[`.documents/OPEN-ISSUES.md`](../.documents/OPEN-ISSUES.md) carries one
pointer line per row here and must be updated in the same commit whenever a
row is added, narrowed or closed. Issues with the *code* (the implementation
of the scheme) belong on the relevant campaign board, not here.

Each row names the review that raised it, in
[`reviews/INDEX.md`](reviews/INDEX.md). Slugs in square brackets are the
stable handles used by the project-wide index.

**Maintenance rule.** When a row is opened, narrowed or closed, update the
count and date above, move the row to §5 on closure with the date and the
resolving commit or decision, and mirror the change in
`.documents/OPEN-ISSUES.md` in the same commit.

---

## 1. Significant problems (block trusting any result)

| Issue | Raised by | Owner | Status | Content |
|---|---|---|---|---|
| `[noise-correlation-inverted-inequality]` | [R1](reviews/2026-10-08-onion-model-calculation-review.md) §1 | David | open; 2026-10-09: transcription error agreed; full inter-shell covariance to be kept (no nearest-neighbour truncation); a kernel that goes negative is unphysical, so a smooth window is preferred; dilution by number of coarse-graining volumes accepted as the CLT limit; `σ` to be the smallest that freeze-out allows, results reported at that `σ`. Remaining: fix `sec:shell-averaging`, choose the window | `sec:shell-averaging` (tex line ≈ 436) argues inter-shell noise correlation is subleading because the Hubble radius is "parametrically larger than `k_σ⁻¹` because `σ ≪ 1`". The inequality is inverted: `1/(σaH)` is `1/σ` Hubble radii, so Hubble-thickness shells lie inside one correlation length and the CLT argument does not apply to them. For the sharp-`k` (sinc) window the angle-averaged noise is exactly rank one, `ξ̄(r,N) = j₀(k_σ r) ξ(0,N)`, by the addition theorem `⟨j₀(k|x−x'|)⟩_Ω = j₀(kr) j₀(kr')`; for a Gaussian window it is banded with width `R_σ = 1/(σaH)` and closed form `C̄(r,r') = (R²/2rr')[e^{−(r−r')²/2R²} − e^{−(r+r')²/2R²}]`. The `δ(y−y')/𝒱` covariance of `eq:noise-angle-averaged` is reached only by assuming the noise is white at the Hubble scale, i.e. `σ ≈ 1`, which the tex nowhere states. Since the instanton action depends on the covariance operator and not only its diagonal, the diagonal model and the kernel models give qualitatively different answers. The "rank-1 shared channel" retired in `sec:open-issues` is the exact monopole statistics, not a modification. **Next:** fix `sec:shell-averaging`; adopt a window; carry the kernel (`[noise-kernel-in-discrete-hamiltonian]`). |
| `[point-constraint-uv-divergence]` | R1 §1 | David / rebuild | open | With noise white in `y`, a point terminal constraint `φ(1,N_final) = φ_end`, and hyperbolic `y`-dynamics (no smoothing), the variance of `φ` at a point is a line integral of 2D white noise along the characteristics and diverges; the optimal response is a delta sheet and the continuum cost of the constraint is zero. Discretely the core node's effective diffusion is `2𝖣/(w_c n_c)`, with `w_c n_c` the number of patches in the last LGL cell (≈ 0.03 at `n_max = 30`, `Δs = 10`), and the action of a core excursion scales with that number, hence falls with `n_max`. Evidence already on record: `λ_GCI ≈ −λ_FI w_core μ E` ([summary-B-implementation.md:61](../.documents/handoff-notes/2026-10-08/summary-B-implementation.md)). The "sub-horizon noise: resolved" claim is only half true: the problem moved from the excised interior to the sub-patch scales the grid resolves near the core; and at `N_init` the whole domain holds about `3α` patches. **Decisive test:** sweep the on-shell action against `n_max` at fixed `τ`; expect roughly `1/n_max²`. **Cure:** same as the row above. |
| `[advection-noise-dependence-breaks-canonical-structure]` | R1 §1 | rebuild | open | `eq:Deltas-dot-closed` puts the core noise sourcing into `F`, so `A` depends on the response fields. Then `b` in `H_FP = ⟨P,b⟩ + ½⟨P,ΣP⟩` is not `P`-independent, and the statement at `sec:discrete-hamiltonian` that the forward flow is linear in `P` does not hold for the Freidlin–Wentzell Hamiltonian of the actual Langevin system. At the Langevin level the core noise is broadcast to every shell through the coordinate map: the noise matrix is `G = I + v ⊗ λ` with `v ∝ (y+1) ∂_y u / Δs`, and the correct quadratic term is `½⟨P, GΣGᵀP⟩`. Equivalently, with `Δ̇s` written in the raw core velocities the one-form is `P·M(u)·du`, the canonical momentum is `MᵀP`, and the terminal condition is on the shifted momentum. Evaluating `A` with deterministic forcing only avoids this but lets the inner edge drift off the horizon, which `sec:advection` rightly forbids. Quantitatively of relative order `(V'/V)(∂_yφ)_c/Δs`, small in slow roll; structurally it invalidates the exact-variational claim, and the Hamiltonian check `eq:hamiltonian-check` cannot see it. **Cure:** `[newton-on-hamiltonian-bvp]` row's Lagrangian construction, or build `GΣGᵀ`. Moot if the inner edge is made fixed (`[inner-edge-coarse-graining-radius-or-fixed]`). |

## 2. Model choices to decide

| Issue | Raised by | Owner | Status | Content |
|---|---|---|---|---|
| `[gradient-term-order-sigma-squared]` | R1 follow-up 2026-10-09 | David | open, narrowed 2026-10-09: size undecided; diagnostic specified | At the innermost shell the gradient forcing is `σ²(φ_ss + φ_s)` with `s = ln r`, and for a shell detached `ΔN` e-folds earlier it carries `σ² e^{−2ΔN}`, so the coupling is between the core and its nearest shell in time. Against generic slow-roll drifts (`≈ 0.3`) it is `≈ 10⁻³` at `σ = 0.1`, but that is the wrong comparison for a large-`δN★` core stalled where `V'/H²` is itself tiny: there the kink between the stalled core and the rolling neighbour can rival the local drift and the noise holding the core. David (2026-10-09): not obviously negligible in the late stages; decide from existing embeddings. **Diagnostic (no new physics):** from stored FullInstanton solutions and their noiseless-detachment profiles, map detachment e-fold to `s`, evaluate `σ²(φ_ss + φ_s)` at the core along `N`, and plot against `(3−ε)π_core`, `V'/H²` and `2𝖣₁₁P₁`; the same plot separates gradient smoothing from noise-coherence smoothing. `σ` policy decided: smallest that freeze-out allows, reported at that value with a factor-two check. The `ln σ` shift in scale assignment stands (cf. `[core-scale-mass-attribution]`). |
| `[terminal-constraint-on-patch-average]` | R1 §2 | rebuild | open | Replace the point constraint on `φ_{n_max}(N_final)` by the innermost-patch average `∫K(1,y) φ(y,N_final) 𝒱 dy = φ_end`. It is the physical observable, gives a smooth terminal source that a spectral representation can carry without Gibbs oscillations, and removes the `w_c` dependence of `eq:terminal-colloc`. |
| `[alpha-order-one]` | R1 §2 | rebuild | open | With a kernel the early-time singularity loses most of its content, and the shells between `R_σ(N_init)` and `r_out` sit on the background by the flat-slicing argument. Take `α = O(1)` to remove the stiffest stretch (`c ≈ 2/ln(1+α)` with edge spacing `≈ 5/n_max²`). Moot under a fixed inner edge. |

## 3. Numerical scheme

| Issue | Raised by | Owner | Status | Content |
|---|---|---|---|---|
| `[noise-kernel-in-discrete-hamiltonian]` | R1 §2 | rebuild | agreed 2026-10-09; response sector to be obtained by automatic differentiation of `H_FP`, since `∂K/∂u` (through `𝖣_i`, `k_σ(N)` and `r_i(y,N)`) is not to be done by hand | Carry `K_ij = √(2𝖣_i 2𝖣_j) C̄(r_i,r_j;N)` in `H_h` in place of the diagonal `Σ_ij/(w_j𝒱_j)`. Rank one for the sinc window (`C̄ = j₀(k_σ r) j₀(k_σ r')`, noise enters the response sector through one scalar `⟨j₀,P⟩` per e-fold per field component); banded for a Gaussian window (closed form in `[noise-correlation-inverted-inequality]`). One symmetric PSD matrix per `N`, fully compatible with differentiating `H_h`. Cures the UV divergence, the early-time `n < 1` problem, and makes the decoupled-limit reduction test trivial (core receives the undiluted single-patch noise). `σ` and the window shape become explicit inputs. |
| `[newton-on-hamiltonian-bvp]` | R1 §2 | rebuild | open | Build `H_h` from a discrete Lagrangian with `Δ̇s` in the raw core velocities (if the edge still moves), so `(1−K)⁻¹` emerges as the velocity solve and autodiff produces the shifted momenta. Solve the full `(u,P)` two-point BVP by Newton (gMAM-style) with `λ` as an augmented unknown, rather than Picard alternation plus an outer root-find. The degenerate-noise objection in `sec:collocation-scheme` applies to the original MAM, not to Hamiltonian methods. Picard's contraction is not guaranteed once the response sector is Riccati. |
| `[discrete-gcl-moving-grid]` | R1 §2 | rebuild | open | The map is an ALE map and `∂_N𝒱 = ∂_y(𝒱A)` is its geometric conservation law. With the physical measure the advective energy is exactly a boundary flux in the continuum, but discretely only if `V̇_j = (D(𝒱A))_j`. Evolve node measures by that ODE, or use split-form advection, so aliasing does not inject interior sources. Moot under a fixed inner edge. |
| `[grid-core-resolution]` | R1 §2 | rebuild | open | LGL spends half its clustering at `y = −1`, where the wave speed is exponentially small. Use a Radau grid, a one-sided mapping, or multi-element SBP-SAT to concentrate resolution at the core, where the scales are the patch width `1/n(1) = 2/(3Δs)` and the caustic layer `δ*` (next row). Also relaxes the `n_max²` time-step limit. |
| `[response-caustic-layer-at-core]` | R1 §2 | rebuild | open | The slow characteristic family at the core, speed `(2/Δs)[−(1−ε)(1−δ/2) + e^{−Δsδ/2}]` at `y = 1−δ`, changes sign at `δ* ≈ 2ε/(Δs−1) ≈ 10⁻³`. In backward time the response field accumulates in that layer, which no practical grid resolves and which holds about `3ε` patches. Harmless once the noise term is `ΣKφ̃` with a smooth `K`, provided the quadrature `φ̃ᵀΣKφ̃` converges; a hazard otherwise. |
| `[neumann-as-natural-bc]` | R1 §2 | rebuild | open | In the integrated-by-parts (symmetric first-order) form of the gradient term, Neumann at the core is the natural boundary condition: no penalty is needed for it and it is dual-consistent by construction. The only remaining SAT question is the advective flux, and that penalty should be a boundary term of the discrete action (cf. `[sat-inside-discrete-hamiltonian]`). |

## 4. Checked in R1 and found correct

Not issues; recorded so the review's coverage is known. Closed form for
`Δs` and its chain-rule rate; the advection operator; the log-radial
Laplacian and its self-adjoint measure; the three-way cancellation
`𝒵[𝒱] = 0` and the continuity equation behind it; the characteristic speeds
and the one-incoming-characteristic count at the core; the dropped-terms
calculation for `V ∝ φ^p`; the collocation terminal condition; the Maupertuis
relation and the `H_FP ≠ 0` argument; the `ζ` extraction on constant-`N`
slices (flat in the local-e-fold sense).

## 5. Closed

| Issue | Closed | By |
|---|---|---|
| `[inner-edge-coarse-graining-radius-or-fixed]`: inner edge of the resolved exterior at the horizon or at the coarse-graining scale; moving or fixed | 2026-10-09 | David's decision: the inner edge lives at the current coarse-graining scale `R_σ(N) = 1/(σ a H_c)`, "just a change of definition" (`Δs → Δs + ln σ`, `r_out = (1+α)/(σ aH_0)`, `n` counts coarse-graining volumes). The fixed-comoving-edge simplification raised in R1 (removes advection, `(1−K)⁻¹`, GCL, `α`) was not taken up and may be reopened if the moving-edge response sector proves costly. |
