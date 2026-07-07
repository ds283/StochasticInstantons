# Prompt 18 — Discrete adjoint-consistency diagnostic (onion-model spatial operators)

**Scope:** one commit. Extends `analyze_StiffnessSpectrum.py` (prompt 17,
Part A) with a second standalone diagnostic. **Measurement only** — no
integrator change, no SBP operator construction, no change to any solver
module. Sibling in character to the eigenvalue sweep: assemble the frozen-
coefficient operators the solver actually applies, and report a property of
them.

## Motivation

The stiffness sweep (prompt 17) established that the assembled spatial
operator's eigenvalues sit at a fixed ~74° off the real axis
(`|Im|/|Re| ≈ 3.55`), i.e. the stiffness is advection-dominated and
oscillatory. The natural follow-up — flagged in `onion_model_planning.md`'s
cross-checks ("confirm … the expected adjoint relationship between the
forward and backward passes"; "LGL/SBP eigenvalue check … before trusting
long production runs") — is whether the **discretised** forward and response
spatial operators preserve the continuum adjoint structure the MSR action's
stationarity relies on, or only approximately.

A hand reconstruction of the real operators (verbatim `D`, `D2=D@D`,
`L_operator`, `measure`; frozen uniform-H², Δs=3, ε=0.01) shows the answer is
operator-specific and must be measured, not assumed:

- The first-derivative matrix `D` satisfies the diagonal-norm SBP identity
  `H D + Dᵀ H = B` (with `H = diag(w_j)`, `B = diag(-1,0,…,0,+1)`) to machine
  precision (~1e-15). So the **advection** operator *can* be discretely
  adjoint-consistent, and its forward/response block mismatch is already
  converging with `n_max` (≈0.99 → 0.40 over n=7→63).
- `D2 = D@D` is **not** the SBP second-derivative operator: `H·(D@D)` is
  non-symmetric (~1.0) and does **not** converge with `n_max`. Consequently
  the **gradient** operator `L`, built from `D@D`, is not discretely self-
  adjoint under the weighted norm `diag(w_j μ(y_j,N))` — the residual plateaus
  (~1.6), it is structural, not truncation error.

**This diagnostic is NOT a bug detector.** A perfectly correct continuum
derivation still produces these discrete mismatches, because strong-form
collocation gets its accuracy from small nodal residuals, not from discrete
adjointness. What the diagnostic delivers is the quantitative, n-resolved,
per-operator evidence for the one decision the planning doc reserved: *if*
discrete adjoint-consistency turns out to matter (action stationarity;
backward pass being the true discrete adjoint of the forward; long-run
stability), it says the weighted-SBP reconstruction is needed for the `D@D`
gradient term specifically, and probably not for the advection term.

## Deliverable

New functionality in `analyze_StiffnessSpectrum.py` (keep it in the same
file — it shares the entire frozen-coefficient assembly, grid, coordinate,
and CLI scaffold), reachable via a new `--mode adjoint` (default remains the
existing eigenvalue sweep, `--mode spectrum`, so prompt 17's behaviour is
unchanged when the flag is absent).

### Operators to assemble

Reuse `assemble_spatial_operator`'s frozen-coefficient conventions exactly
(same `delta_s`, `advection_coefficient`, `measure`, `L_operator`,
`advection_term`, `neumann_boundary_value`, uniform `H²_local/H²_nl_init = 1`,
fixed `epsilon_core`). Add a **response-sector** assembly mirroring it:

- Import `pack_response_state` / `unpack_response_state` and the `c(N)` scalar
  helper (`_c_of_N`) from `response_rhs`, and respect the **role-swapped**
  Neumann elimination (in the response sector `rmom` is Neumann-eliminated at
  the core `y=+1` and `rfield` is free — the mirror of the forward sector's
  `φ` eliminated / `π` free).
- The response spatial operator's blocks (excluding potential/noise/damping,
  exactly as the forward assembly excludes them):
  `drfield ⊃ A ∂_y rfield + c(N)·rfield − exp(−2Δs_loc)·L(rmom)`;
  `drmom  ⊃ A ∂_y rmom  + c(N)·rmom`.
  (Note `L` acts on the **other** response field, and the gradient term
  carries a **minus** sign relative to the forward sector — this is the
  self-adjoint transfer, and getting the sign/placement right is the whole
  point of the exercise.)

Assemble each operator in **two representations**, because the difference
localises the boundary contribution to any mismatch:
1. **full-node** (pre-elimination, `(n_max+1)`-length fields, Dirichlet node
   included), and
2. **eliminated** (the reduced `2·n_max−1` free-DOF operator the solver
   actually integrates — i.e. what `assemble_spatial_operator` already
   produces for the forward sector).

### Quantities to report (one CSV row per `(n_max, alpha, N)`)

With `W = diag(w_j μ(y_j, N))` (the block weight is `blkdiag(W, W)`):

1. **SBP control** — `sbp_residual = ‖H D + Dᵀ H − B‖ / ‖H D‖` with
   `H = diag(w_j)`. Acceptance anchor: ~1e-14. This is a sanity check that the
   grid/norm are wired correctly; if it isn't ~machine-zero, stop — something
   about the weight or `D` is wrong and every other number is meaningless.
2. **Gradient self-adjointness residual** —
   `L_selfadj = ‖W⁻¹ Lᵀ W − L‖ / ‖L‖` for the assembled gradient operator
   (with the `exp(−2Δs_loc)` prefactor folded in, full-node). Expected: O(1),
   ~1.5–1.6 at Δs≈3, and **non-converging** in `n_max`.
3. **Forward/response block adjoint mismatch** —
   `block_mismatch = ‖W_b R + Fᵀ W_b‖ / ‖W_b R‖`, where `F` is the forward
   spatial block on `(φ,π)` and `R` the response spatial block on
   `(rφ,rπ)`, reported for: **full** block; **advection-only** (gradient
   zeroed, `c(N)` kept); **gradient-only** (advection and `c(N)` zeroed).
   Report for **both** the full-node and eliminated representations.
   Expected: advection-only converging with `n_max`; gradient-only plateauing
   (~1.0); full dominated by the gradient part.

CSV fieldnames (extend, don't rename existing ones):
`n_max, alpha, N, delta_s_N, sbp_residual, L_selfadj,
block_mismatch_full, block_mismatch_advection, block_mismatch_gradient,
block_mismatch_full_eliminated, block_mismatch_advection_eliminated,
block_mismatch_gradient_eliminated`.

Default sweep: reuse prompt 17's default `n_max`/`alpha`/`N` lists.
Optional `--plot`: `block_mismatch_{full,advection,gradient}` vs `n_max` at
one representative `(alpha, N)`, log-y, to show convergence-vs-plateau in one
figure.

## Acceptance criteria

- [ ] `--mode adjoint` produces the CSV above; `--mode spectrum` (default)
      reproduces prompt 17's output byte-for-byte (no regression).
- [ ] `sbp_residual` < 1e-12 at every sweep point (SBP identity for `D` holds;
      this validates the weight/grid wiring).
- [ ] `L_selfadj` is O(1) and does **not** decrease by more than ~2× across
      the full `n_max` range at fixed `(alpha, N)` — i.e. demonstrably a
      plateau, not spectral convergence. (Documents that `D@D` is not
      SBP-symmetric; this is expected, and the test asserts the plateau
      rather than treating it as a failure.)
- [ ] `block_mismatch_advection` **decreases** monotonically-ish with `n_max`
      while `block_mismatch_gradient` does **not** — the decomposition
      cleanly separates the SBP-curable operator (advection / `D`) from the
      structurally non-adjoint one (gradient / `D@D`).
- [ ] The eliminated-vs-full-node difference is reported so the boundary
      (SAT) contribution to the mismatch is visible separately from the bulk.
- [ ] A short module-docstring paragraph states plainly that this measures
      **discrete variational consistency**, that a nonzero mismatch is
      **expected for strong-form collocation and is not evidence of a
      derivation error**, and that its purpose is to inform the weighted-SBP
      decision — not to gate correctness.
- [ ] Reuse `assemble_spatial_operator`; the new response assembly is the only
      genuinely new operator construction. No solver module is imported for
      its RHS-in-a-loop (assemble the frozen operators directly, as prompt 17
      does — do not finite-difference `response_rhs`, which would drag in the
      splines/potential; the response sector has no `disable_spatial_coupling`
      flag anyway).

## Notes / subtleties

- **Frozen uniform-H² is inherited** from prompt 17: this characterises the
  discretisation's adjoint structure, not any particular potential's
  `H_sq(φ,π)` profile. Fine for the SBP question, which is a property of the
  operators. (A real, feature-rich USR/quartic trajectory could add
  N-local prefactor variation; out of scope here, note it in the docstring.)
- **Continuous ≠ discrete adjointness.** The continuum forward/response
  operators are adjoint under `μ dy` by construction; this diagnostic is
  specifically about whether the *strong-form collocation matrices* inherit
  that. They partially do (advection) and partially don't (gradient).
- **Sign/placement of the response gradient term** (`−L` acting on `rmom`)
  and the **role-swapped elimination** are the two places a transcription
  slip would show up as an anomalous `block_mismatch_gradient` pattern; the
  diagnostic is, incidentally, a reasonable guard on those, even though its
  primary purpose is the SBP characterisation.

## Out of scope (do not build here)

- The weighted-SBP second-derivative operator itself, or any SAT boundary
  treatment. This diagnostic tells you *whether* that fallback is warranted;
  building it is a separate prompt, gated on this diagnostic plus a
  demonstrated stationarity/stability problem in an actual solve.
- Any integrator change (Radau/BDF/IMEX). Separate decision, separate prompt.
- Consuming this CSV in a downstream analysis script.
