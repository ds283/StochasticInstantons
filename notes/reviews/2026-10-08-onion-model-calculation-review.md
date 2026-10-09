# Review of the onion-model calculation and numerical scheme

**Review date:** 2026-10-08 (written up 2026-10-09) · **Reviewer:** Claude Fable 5.1, at David Seery's request
**Object reviewed:** [`notes/onion-model/onion_model.tex`](../onion-model/onion_model.tex) at commit `00d254e` (the 8 October rewrite `e511f74` plus the Phase 0 bookkeeping commits)
**Circumstances:** David asked for a careful, critical evaluation of the calculation and of the proposed numerical scheme, with any significant error reported and improvements proposed. The review was done by reading the tex in full and re-deriving the algebra independently, with two look-ups in the repository: the handoff notes for evidence on resolution dependence, and `forward_rhs.py` to confirm that the implemented dilution is the tex's `2𝖣/n`.
**Issues raised:** recorded on [`notes/OPEN-ISSUES.md`](../OPEN-ISSUES.md); slugs below refer to that board.

## Verdict

The derivation is internally consistent in most places (§4 of the board lists what was checked and found correct). Three things are significant errors or inconsistencies. The first two share a cause and a cure: the model's treatment of the spatial correlation of the noise.

## 1. Significant problems

**Noise correlation structure** `[noise-correlation-inverted-inequality]`. Section 2 argues inter-shell noise correlation is subleading because the Hubble radius is parametrically larger than `k_σ⁻¹` for `σ ≪ 1`. The inequality is inverted: the coarse-graining length `1/(σaH)` is `1/σ` Hubble radii. For the sinc window the angle-averaged noise is exactly rank one, `ξ̄(r,N) = j₀(k_σ r) ξ(0,N)`, by the addition theorem; for a smooth window it is banded with width `R_σ`. The `δ(y−y')/𝒱` covariance holds only for `σ ≈ 1`, unstated. The rank-one shared channel retired in the open-issues section is the exact monopole statistics. With coherent noise over `1/σ` Hubble radii, sharp profiles are not generated in the first place, and the gradient term is the `O(σ²)` correction the tex itself calls it.

**UV divergence of the point constraint** `[point-constraint-uv-divergence]`. Noise white in `y`, a point terminal constraint and hyperbolic `y`-dynamics make the pointwise variance of `φ` a line integral of 2D white noise, which diverges; the continuum cost of the constraint is zero and the discrete cost scales with the number of patches in the last quadrature cell, `w_c n_c ≈ 0.03` at `n_max = 30`, `Δs = 10`. The 9 July finding `λ_GCI ≈ −λ_FI w_core μ E` is this scaling. No sweep of the on-shell action against `n_max` exists; it is the decisive test. The slow characteristic family changes sign at `δ* ≈ 2ε/(Δs−1) ≈ 10⁻³` from the core, so the response field piles up in a layer no grid resolves `[response-caustic-layer-at-core]`.

**Velocity dependence of the advection coefficient** `[advection-noise-dependence-breaks-canonical-structure]`. `eq:Deltas-dot-closed` puts the core noise sourcing into `A`, so `b` depends on `P` and the forward flow is not linear in `P` for the true Freidlin–Wentzell Hamiltonian, whose quadratic term is `½⟨P, GΣGᵀP⟩` with `G = I + v⊗λ`. Equivalently the canonical momentum is `MᵀP` and the terminal condition sits on the shifted momentum. Small in slow roll; structurally it breaks the exact-variational claim, and the Hamiltonian check cannot detect it.

## 2. Proposed adjustments to the numerical scheme

- Carry the covariance kernel `K(y,y';N)` in `H_h` instead of `δ(y−y')` `[noise-kernel-in-discrete-hamiltonian]`.
- Constrain the innermost-patch average, not the point value `[terminal-constraint-on-patch-average]`.
- Build `H_h` from a discrete Lagrangian with `Δ̇s` in the raw core velocities, and solve the full Hamiltonian BVP by Newton with `λ` augmented `[newton-on-hamiltonian-bvp]`.
- Enforce a discrete geometric conservation law on the moving grid `[discrete-gcl-moving-grid]`.
- Concentrate resolution at the core (Radau, mapped or multi-element grid) `[grid-core-resolution]`.
- Treat Neumann as the natural boundary condition of the symmetric-form gradient term `[neumann-as-natural-bc]`.
- Take `α = O(1)` `[alpha-order-one]`.

Smaller points: the Maupertuis relation and the `H_FP ≠ 0` discussion are correct; the `ζ` extraction on constant-`N` slices is consistent because those slices are flat in the local-e-fold sense; the explicit CFL limit at early times, `c ≈ 2/ln(1+α)` against edge spacing `≈ 5/n_max²`, is why small `α` is expensive.

## 3. Follow-up on 2026-10-09

David agreed the `1/(σaH)` inequality is a transcription error, affirmed that the core is the coarse-graining patch and that `σ` should be as small as makes sense (about `0.1`), and asked whether a nearest-neighbour shell-correlation model with dilution for distant shells is the right first approximation. The answer given in conversation is summarised in two new board rows, `[inner-edge-coarse-graining-radius-or-fixed]` and `[gradient-term-order-sigma-squared]`, and in the content of `[noise-correlation-inverted-inequality]`: the kernel is fixed by the window function and has a closed form, so it should be carried whole rather than truncated to nearest neighbours; the dilution of distant shells emerges from the same formula with "patch" meaning a coarse-graining volume; and with a kernel in place the inner edge need not move with the horizon at all.

Later the same day David decided: the inner edge lives at the current coarse-graining scale (row closed on the board); the full inter-shell covariance is kept, with a non-negative kernel preferred; the dilution by number of coarse-graining volumes is accepted as the CLT limit; `σ` is the smallest that makes sense, with results reported at that value; the response sector is to be obtained by automatic differentiation of `H_FP`. He questioned the claim that the gradient term is negligible at `σ = 0.1`, pointing to the late-stage wind-up of gradients at the core; the reviewer conceded that the comparison must be with the local drift of a stalled core, not with generic slow-roll drifts, and the row `[gradient-term-order-sigma-squared]` was narrowed to a diagnostic on existing embeddings.
