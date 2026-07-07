# Prompt 18a — Amendment to the adjoint-consistency diagnostic (metric fixes)

**Scope:** one commit, amending the `--mode adjoint` path added in prompt 18.
No change to `--mode spectrum`. Two columns produced by prompt 18 are metric
artifacts and must be corrected; one new decomposition (interior vs boundary)
replaces the invalid one and is where the real signal lives.

## Why

Running prompt 18 on the default sweep surfaced two flaws, both in the metric
definitions I specified, not in the assembled operators:

1. **`L_selfadj` is corrupted beyond Δs≈5.** The specified form
   `‖W⁻¹ Lᵀ W − L‖ / ‖L‖` inverts the exponentially graded weight
   `W = diag(w_j μ(y_j,N))`, `μ = exp(−1.5 Δs y)`, whose condition number is
   `exp(3Δs)` (≈10³² at Δs=25). The column reads ~1.59 up to Δs≈5 and then
   blows up to ~10⁷–10⁹ as pure roundoff. It tracks the weight grading, not the
   operator.

2. **The `*_eliminated` columns are invalid.** `block_mismatch_gradient_eliminated`
   is exactly `√2` (1.41421356…) for **all 240 rows**, independent of
   `n_max`, `alpha`, `N` — the tell of an artifact. The role-swapped Neumann
   elimination puts the forward state (`φ`: n−1 free, core eliminated; `π`: n)
   and the response state (`rφ`: n; `rπ`: n−1 free) in mismatched index
   layouts, so `Fᵀ` and `R` are compared in incompatible bases and the
   gradient blocks fall out Frobenius-orthogonal with equal norm. A correct
   eliminated comparison needs an explicit forward↔response DOF pairing that
   also handles the **adjoint-BC swap** at the core (a Neumann-constrained
   forward field pairs with a free response field) — which is essentially the
   SAT construction this whole diagnostic is meant to *inform*, so requiring it
   as a diagnostic input is circular. Drop the eliminated representation.

The full-node columns from prompt 18 are unaffected and correct.

## Changes

### Fix 1 — inversion-free `L_selfadj`

Replace the metric with the inversion-free self-adjointness residual:

```
L_selfadj = ‖ W L − (W L)ᵀ ‖ / ‖ W L ‖          # W = diag(w_j μ(y_j,N))
```

Never form `W⁻¹`. This is well conditioned at all Δs (verified: 1.005 → 1.10
as Δs goes 1→25 at n=64). Same qualitative conclusion (`L` is O(1) non-self-
adjoint *including the boundary*), correctly conditioned.

### Fix 2 — drop `*_eliminated`, add interior/boundary decomposition

Remove `block_mismatch_{full,advection,gradient}_eliminated` and the
eliminated-operator assembly. In their place, for **each** of the three
full-node block mismatches (`full`, `advection`, `gradient`) **and** for
`L_selfadj`, additionally report an **interior-only** variant computed by
masking the two boundary nodes (`y = ±1`, i.e. indices `0` and `n_max`) from
**each field block** before taking the Frobenius norms of both numerator and
denominator. Concretely, with `keep = [1..n_max−1]` per field and
`keep2 = concat(keep, keep)` for the 2-field blocks:

```
metric_interior = ‖ M[keep2, keep2] ‖ / ‖ nrm[keep2, keep2] ‖
```

New/renamed CSV columns (drop the four `*_eliminated`; keep the six full-node
metrics; add five interior-only):

```
n_max, alpha, N, delta_s_N, sbp_residual,
L_selfadj, L_selfadj_interior,
block_mismatch_full, block_mismatch_full_interior,
block_mismatch_advection, block_mismatch_advection_interior,
block_mismatch_gradient, block_mismatch_gradient_interior
```

The interior-vs-full gap is the unambiguous boundary contribution — the thing
the eliminated representation was supposed to give but couldn't.

## Expected behaviour (acceptance anchors, verified by reconstruction)

- [ ] `sbp_residual` unchanged, < 1e-12 everywhere.
- [ ] `L_selfadj` (fixed) stays O(1) at all Δs (≈1.0–1.4, no 10⁷ blowups);
      `L_selfadj_interior` **→ 0 spectrally** in `n_max` at every Δs
      (e.g. Δs=25: ~7.7e-2 → ~3.2e-4 over n=16→192). This is the key result:
      the μ-weighted bulk gradient operator **is** discretely self-adjoint;
      its O(1) mismatch is entirely at `y=±1`.
- [ ] `block_mismatch_gradient_interior` **→ 0 spectrally** (gradient
      non-adjointness is boundary-localized).
- [ ] `block_mismatch_advection_interior` ≈ `block_mismatch_advection`
      (advection mismatch is **bulk**, not boundary): at Δs=1 both ~0.3→0.08
      (algebraic ~1/n decay), at Δs=25 both flat ~1.0. This is the residual to
      interpret (see below), and the diagnostic's job here is to report it
      cleanly, not to drive it to zero.
- [ ] No `*_eliminated` columns remain; `--mode spectrum` still byte-identical
      to prompt 17.
- [ ] `--plot` updated: overlay full vs interior-only for the three block
      metrics at one `(alpha, N)`, so the boundary-vs-bulk split is visible.

## Interpretation note (put a short version in the module docstring)

The interior/boundary split cleanly separates two different situations:

- **Gradient**: bulk spectrally adjoint-consistent under μ; O(1) mismatch is
  pure boundary. *If* it needs fixing, the instrument is a SAT boundary
  penalty, not a bulk operator replacement.
- **Advection**: O(1) **bulk** mismatch at production Δs, converging only
  algebraically at small Δs. This is a genuine operator-level discrepancy in
  the isolated `advection` vs `advection + c(N)` comparison. It has two
  candidate explanations that this diagnostic cannot distinguish: (i) a
  missing y-dependent measure-derivative term in the response advection
  relative to the true μ-weighted adjoint of the forward advection, or (ii)
  ill-posed isolation — advection's adjoint partner (the measure-friction) is
  distributed across non-spatial couplings (the `π` identity term, the
  `−rfield`/`(3−ε)` damping), so advection-alone is not expected to be adjoint
  and only the **full linearized operator** is.

## Recommended follow-up (out of scope for 18a — separate prompt if pursued)

To disambiguate (i) vs (ii): add a `--mode adjoint-full` that assembles the
**full linearized** forward/response operators (spatial terms *plus* the
identity/friction/`V''` couplings, still frozen-coefficient), and reports the
same full/interior block mismatch. If `..._interior → 0` spectrally at
production Δs, the advection-only bulk residual was ill-posed isolation and
the discretisation is adjoint-consistent in the interior; if it stays O(1),
there is a genuine term to chase in the response-sector derivation. This is a
derivation-level question — assemble and report the number; the physics call
is the author's.

## Out of scope

- The SAT boundary penalty / weighted-SBP construction itself (a fix, gated on
  this diagnostic plus a demonstrated stationarity problem in a real solve).
- Any integrator change.
- The `adjoint-full` mode above (noted as follow-up, not built here).
