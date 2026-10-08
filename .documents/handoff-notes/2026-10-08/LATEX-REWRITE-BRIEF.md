# Brief: rewriting `onion_model.tex` to the 20 July 2026 position

**Purpose.** Instructions for a fresh session to rewrite
`.documents/gradient-coupled-instanton/onion_model.tex` so that it states the
model as it was understood on 20 July 2026 and as decided on 8 October 2026,
rather than as it was on 6 July. The source of truth for every change is
`RECONSTRUCTION.md` in this directory (section references below are to it);
the three `summary-*.md` files and, where a derivation must be reproduced in
full, the raw transcripts under `.documents/transcripts/` (local only).

**Ground rules.**

- The tex builds cleanly with `latexmk -pdf` (checked 8 October; `jcappub.sty`
  is installed). Keep it building after every section.
- Keep the existing macro set and the `panel` / `calculation` / `todo`
  environments. Use `calculation` for derivations, `panel` for remarks, `todo`
  for genuinely open items.
- Do not delete superseded material silently: where the 6 July text recorded
  a choice that is now reversed, keep a short `panel` saying what was
  believed, why it was wrong, and where the correction came from. The
  response-equation sign-fix panel in the current §instanton-eqs is the house
  style for this.
- The numerics sections (§collocation-basis onward) describe a scheme that
  will be replaced (Phase 3 of the plan). Rewrite them only to the extent of
  stating the *target* scheme; mark anything not yet implemented with a
  `todo`.
- The paper will present the analytic `FullInstanton` adjoint equations in
  full, as intuition-building material (decision D0.1). The onion response
  equations are to be presented as Hamilton's equations of `H_FP` generated
  by differentiation; the continuum form may be displayed where it is short,
  but the text must say that the implementation differentiates the discrete
  Hamiltonian and does not transcribe these equations.

---

## 1. §coordinate — the onion coordinate

- **Anchor (B.9):** `Δs(N) = ln(r_out / r_core(N))` with
  `r_core = 1/(a H_core[φ(1,N), π(1,N)])`, so `ρ ≡ r_core/r_H ≡ 1` by
  construction. State explicitly that this is the model's definition, not a
  derived fact, and that the alternative (background anchor, `ε_nl` in `A`)
  was considered on 14 July and rejected on 16 July because it produces two
  incoming characteristics at the core when `ε_nl < 1 − ρ`.
- **`dΔs/dN` is derived, not posited (B.8, B.9):** replace eq.
  `Deltas-derivative`'s `1 − ε_core` with the chain-rule expression through
  the actual core row,
  `Δ̇s = [1 − ε_core + π_core 𝓛_core/(2(3−ε_core))] / (1 − K)`,
  `K = Δs⁻¹[(V'/V)(∂_yφ)_core − π_core(∂_yπ)_core/(3−ε_core)]`,
  with `𝓛_core` the non-advective core forcing. Show in a `calculation`
  that substituting the homogeneous equations collapses this to `1 − π²/2`,
  and say in a `panel` why that collapse is not available (the core row is
  not homogeneous; `ε = π²/2` is a consequence of an equation of motion, not
  a constitutive identity). Note `K → 0` at convergence by regularity, that
  the `𝓛_core` term survives, and that `K = 1` is a singularity of the map.
- Whether the SAT belongs in `𝓛_core` is open (Open 3); say so.
- Keep the `α` panel, but add (B.4): the measure fix does not remove the
  geometric singularities; the response-sector indicial analysis at
  `Δs → 0` has not been done; `α` is retained for domain-degeneracy and
  conditioning reasons regardless.

## 2. §noise-y and §msr-action — noise normalisation and measure

- **Replace "Choice of measure" (B.4, B.5, B.6).** Self-adjointness fixes
  `μ` only up to a `y`-independent `C(N)`. The noise fixes the rest: derive
  the angle-averaged noise correlator and show it is white with respect to
  the physical volume element `V'(y,N) dy = 2π r_out³ Δs e^{−(3/2)(y+1)Δs} dy`
  with amplitude `2D₁₁/n_count` and flat `δ(y−y')`. Confirm the existing
  §noise-y amplitude is correct. State the three self-consistent triples
  (flat / `μ` / `V'`) and the gauge relation between them, and that the
  current eq. `msr-action` is a splice of two of them.
- Rewrite eq. `msr-action` with the `V'` measure. Keep the `φ̂ = iφ̃`
  rotation subsection as is.
- Add a short `panel` on noise density versus covariance and on the two
  distinct volume factors (`1/n_count` dilution versus the quadrature
  measure) that must not be cancelled against each other (B.5).
- Keep the self-adjointness panel but correct its last paragraph: the
  Neumann pair is the right count, but the response condition supplies no
  data (B.1, 16 July).

## 3. New §hfp — the Fokker–Planck Hamiltonian (after §msr-action, before the instanton equations)

Follow `2026-07-10/HFP-CALCULATION.md` §7 for structure, redone in the `V'`
convention:

- `S = ∫dN [⟨r̃φ̇ + π̃π̇⟩ − H_FP]`; `H_FP` as the Freidlin–Wentzell
  Hamiltonian; canonical pair `(φ, V' r̃)` in a `panel` ("the measure is part
  of the symplectic form").
- Verification that `∂H/∂p` gives the forward equations exactly, and that
  `−δH/δφ` gives the response equations (now with `Z = 0`, see §4).
- The 1D reduction and the Legendre check `P₁φ̇ + P₂π̇ − H_FP = D₁₁P₁²`,
  which settles the factor-of-two question of A.1.
- Non-conservation in the onion (explicit `N`-dependence, boundary flux,
  truncation) and the balance law; the Maupertuis relation
  `H_FP = −∂S/∂δN★` in 1D; why `H_FP ≠ 0` (B.1).
- **FullInstanton closed form (B.10):** `H_FP = λφ₂(N_total) + D₁₁(N_total)λ²`,
  hence `∂S/∂δN★ = −[λφ₂ + D₁₁λ²]`.
- A `panel` (B.9) on why the response fields are conjugate momenta of
  `H_FP` and transport as the adjoint tangent map only when `∂D/∂u = 0`;
  the factor-of-two trap in `−(∂f/∂u)ᵀP`; and that the implementation
  obtains both sectors by differentiating a single discrete `H_FP`
  (decision D0.1).

## 4. §instanton-eqs — the response equations

- Present the **FullInstanton** response equations in full (B.10), with the
  `∂H²/∂φ`, `∂ε/∂π`, `∂H²/∂π` and `∂D/∂u` terms, and the worked quadratic
  check: `∂b_π/∂φ = −(3−ε)(ln V)''`, equal and opposite to the retained
  `−V''/H²`. Replace the "What is *not* corrected here" panel with a
  "Terms previously dropped" panel giving this, and the `V ∝ φ^p` factor
  `−1/(p−1)` (A.3).
- Present the **onion** response equations in the `V'` convention: no
  `(1−ε_core)[1/Δs − 3/2]` bracket (`Z[V'] = 0`, with the three-way
  cancellation shown in a `calculation`, B.6); gradient term `L(gπ̃)` with
  `g = e^{−2Δs_loc}` inside the operator (B.4), with the two missing terms
  displayed; then the statement that the full variation, including the
  state dependence of `Δs`, `A`, `μ`, `n_count` through the core node, is
  generated numerically and is not written out.
- Keep the measure-friction / sign-fix `calculation` as a historical panel
  but mark its final bracket as a `μ`-convention artefact.
- Add David's physics position (A.3): the `H(φ)`, `ε(φ)` derivative terms
  arise only in the response sector; the Langevin equations are unchanged;
  the MSR action is that of the reduced SDE.
- Riccati (B.10): with `∂D/∂u ≠ 0` the backward pass is a matrix Riccati
  flow, `r = λr̃` linearity is lost (and was tree-level only, A.2), and the
  symplectic block linearisation is the robust representation; mark as
  `todo` pending the FullInstanton pilot.

## 5. §bcs — boundary conditions

- `y = −1`: pinning both `φ` and `π` is one condition plus an identity
  (`A(−1) = 0`); likewise `φ̃(−1) = 0` follows from `π̃(−1) = 0` (B.1).
- `y = +1`: the hyperbolic reduction `φ_NN − 2Aφ_Ny + (A²−c²)φ_yy = 0`,
  the optical metric `M = {{1,−A},{−A,A²−C²}}`, characteristics
  `dy/dN = −A ± C`, and with the core anchor `C(+1) = 2/Δs`,
  `A(+1) = 2(1−ε_core)/Δs`, so exactly one incoming characteristic for
  `0 < ε_core < 2`; the outgoing mode is nearly tangent in slow roll
  (`2ε_core/Δs`), which is physical (marginally trapped horizon) and
  `α`-independent (B.9). Same for the response sector in backward time (B.1).
- **No data enters at the core** (B.3): Neumann is the reflecting, data-free
  use of the one incoming characteristic; the piston flux `½ V' A(1) π_core²`
  is physical bounded growth. Record that the 10 July reading (`g_π` as a
  model closure) was reversed on 11 July.
- The penalised characteristic variable is the incoming Riemann invariant
  `w_in = (2(2−ε_core)/Δs) π_core + (∂_yφ)_core` (B.9), `π`-dominated near de
  Sitter.
- Keep the temporal conditions subsection; add the tree-level caveat on
  `λ`-linearity.

## 6. New or rewritten numerics sections

- A new short section on the H-energy method (B.2): the H-kernel and
  H-energy as a control functional distinct from `H_FP`; the three steps;
  positive-definiteness and norm equivalence; why `H_μ = diag(w_j V'_j)` is
  the norm in which the interior is sign-definite; `|H_FP| ≤ (M/c)E` on the
  joint state; norm for stability, transpose for adjointness.
- §collocation-basis "Boundary conditions": replace the hard-elimination
  text with the target scheme: single SAT on `w_in` in the `H_μ` norm,
  derived as a boundary term of the discrete action; response boundary rows
  by differentiation/transposition; the previous two-penalty closure
  described as the over-determination that produced the `n²` stiffness
  (A.3, C3). Everything not yet implemented is a `todo`.
- §collocation-scheme: state that the forward flow is `∂H_h/∂P` and the
  response flow `−∂H_h/∂u` of one discrete Hamiltonian `H_h` built from the
  LGL quadrature of the `V'`-weighted density (first-order form after
  integration by parts, B.7), with the open choice of whether the SAT is a
  term in `H_h` (Open 2). Describe the Hamiltonian-structure check
  `(Ω J_full)ᵀ = Ω J_full` as the acceptance test replacing
  `E = J_resp + J_fwdᵀ`.

## 7. §scale-assignment

- Record the `(1+α)` anchor at `N_init`, the `ln_k_phys_Mpc` rewrite in
  `H`, and the forward re-anchoring of `CompactionFunction` (A.1); close the
  §11.4 `todo` (the discrete code uses the local trajectory).
- Note the GCI-versus-FullInstanton core-scale difference (B.6) and that
  under the core anchor the comoving ratio `Δs(N_final)` is the core one;
  mark the mass-attribution question as open (Open 6).

## 8. §open-issues

Keep the two existing `todo`s. Add, each as a `todo` with a pointer to
`RECONSTRUCTION.md`: the response-sector indicial analysis at `Δs → 0`;
the `∂D/∂u` (Riccati) decision; the decoupled-limit degeneracy and the
missing non-trivial reduction test (A.1); the MSR↔spectral bridge via the
adjoint backward-Kolmogorov eigenproblem and the withdrawal of
`H_FP → −Λ₀` (B.2); the Mukhanov-memory (non-Markovian `D`) caveat.

## 9. Not in scope of the tex rewrite

The SBP-energy literature placement and the Cacuci analogy (B.2, B.7) are
background for the paper's methods section, not for these notes. The
scale-assignment physics ambiguity between pipelines is noted, not resolved.
