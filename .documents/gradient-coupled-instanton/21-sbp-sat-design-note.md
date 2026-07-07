# Design note: SBP-SAT boundary closure for the onion spatial operator

Prompt: `.prompts/gradient-coupled-instanton/21-sbp-sat-boundary-closure.md`, Phase 1a.
Status: **Phase 1 derivation + prototype complete.** Phase 2 (production port) is
gated on the physics sign-off requested at the end of this note — see
"Open decision for David" below.

## 1. What is destabilizing, precisely

The current spatial operator has two additive pieces per field (`phi`, `pi`):
a gradient/second-derivative piece (`L_operator`, dressed with
`exp(-2*Delta_s_loc)`) and an advection piece (`advection_term`, i.e. the plain
product `diag(A) @ D`). Prompt 18a's adjoint diagnostic already showed the
gradient operator is bulk self-adjoint-consistent (its interior residual `->0`
as `n_max` grows) with only an `O(1)` *boundary* mismatch — i.e. it is not the
source of the `n^1.6`-growing abscissa. The advection operator is the culprit.
This note derives exactly why, and exactly what SAT term fixes it.

All of the following is a **frozen-coefficient** analysis: `Delta_s(N)` and the
per-node `Delta_s_loc(y,N)` are treated as fixed numbers at the point the
operator is linearised (matching `assemble_spatial_operator`'s own
frozen-coefficient convention, and matching `advection_coefficient`'s
form `A(y) = (y+1)/Delta_s(N) * (1 - epsilon_core)`, which is affine in `y`
at fixed `N`).

## 2. Which norm this estimate uses, and why

The exact algebraic identity this codebase has verified to ~1e-15
(`_sbp_residual` in `analyze_StiffnessSpectrum.py`) is

```
H D + D^T H = B,     H = diag(w_j),     B = diag(-1, 0, ..., 0, +1)
```

i.e. the **plain LGL quadrature norm**, not the physically-weighted norm
`H_mu = diag(w_j * mu(y_j,N))` that `onion_model_planning.md` (§7.1) notes is
the one the *continuum* action is actually self-adjoint under. `mu(y,N) =
exp(-1.5*Delta_s(N)*y)` is exponentially graded in `y`, and `H_mu D + D^T H_mu
!= diag(-mu(-1),0,...,0,mu(1))` in general — the diagonal-norm SBP property is
a special fact about `(D, w)`, not preserved under an arbitrary further
diagonal reweighting.

This note derives the SAT coefficient under `H = diag(w)` because that is
where the exact identity is available to work with by hand. This is a
legitimate choice for the purpose at hand for two independent reasons:

1. **The thing Phase 1c actually measures is the eigenvalues of the assembled
   matrix, not a choice of Lyapunov function.** The SAT term added to the ODE
   is a fixed matrix modification, independent of which norm was used to
   *derive* it. If the `H`-norm-derived `tau` fails to bind the spectrum under
   the true physical norm, that would show up directly as the abscissa
   growing with `n` in the prototype sweep — which is exactly what Phase 1c's
   gate checks, independent of this section's derivation. The derivation below
   is a construction procedure, not the proof of record; the eigenvalue sweep
   is the proof of record.
2. Empirically (Section 5), the `H`-derived `tau` reproduces the previously
   validated closed-form result (`abscissa -> -A(core)/4`, n-independent)
   exactly, which is strong direct evidence that the flat-norm construction
   is already sufficient here — the destabilizing term turns out to be a
   single-node diagonal spike (Section 3) whose cancellation doesn't depend
   delicately on the grading of the weight.

If a future resolution needs the SAT calibrated under `H_mu` instead (e.g. if
a later, more demanding acceptance check fails under it), the derivation
pattern in Section 3 goes through unchanged with `H_mu` in place of `H` and a
`mu`-weighted version of the SBP identity re-derived first — flagged here as
the fallback, not attempted because it is not currently needed.

## 3. Exact SBP defect of the split-form advection operator

Current production form: `advection_term(f, A_array, D) = A_array * (D @ f)`,
i.e. `diag(A) @ D` applied to `f` (`phi_full` or `pi_full` — same `A_array`
for both). The prompt's split form is

```
A_split = 1/2 * (diag(A) @ D + D @ diag(A) - diag(D @ A))
```

**Continuum motivation.** `A u_y` and `1/2*(A u_y + (Au)_y - A_y u)` are the
*same* function of `y` (substitute `(Au)_y = A_y u + A u_y` and the extra
terms cancel) — the split form is a re-writing, not a different equation.
Discretely, `D` is only exact for polynomials up to degree `n_max`; forming
`D @ (A .* f)` where `A` and `f` are both grid functions of degree up to
`n_max` differentiates an effectively degree-`2n_max` object, so
`D @ diag(A) != diag(A) @ D + diag(D @ A)` as matrices even though the
continuum identity holds pointwise for smooth functions. This aliasing gap is
exactly what makes `A_split` behave differently from the plain product under
the energy estimate below, despite representing "the same" continuum term.

**The energy identity.** Write `S = H A_split + A_split^T H`. Since `H` and
`diag(A)` are both diagonal (hence commute), expanding and substituting the
verified SBP identity `HD + D^T H = B` gives, after cancellation of the
`diag(D@A)` cross-terms,

```
S = diag(A) @ B  -  H @ diag(D @ A)
  = diag(-A_0, 0, ..., 0, A_{n_max})  -  H @ diag(D @ A)
```

This is the general result for *any* `A(y)`. Now use that `A(y) =
(y+1)/Delta_s(N) * (1-epsilon_core)` is **affine in `y`** — degree 1, so `D`
(exact for polynomials up to degree `n_max >= 1`) differentiates it exactly at
every node, giving a single constant:

```
(D @ A)_j = a'  for every j,      a' = (1 - epsilon_core) / Delta_s(N)
```

so `H @ diag(D@A) = a' * H` exactly (no per-node variation at all). Also
`A_0 = A(-1) = 0` exactly (confirmed against `advection_coefficient`'s own
formula: `(y+1)` vanishes at `y=-1`), and `A_{n_max} = A(+1) = 2 a'`. So:

```
S = -a' * H  +  diag(0, ..., 0, 2 a')
```

**Reading this off:** every diagonal entry of `S` is `-a' w_j` (a small,
*stabilizing*, `n`-dependent contribution that shrinks as the grid refines and
`w_j` shrinks) **except the last node** (`y=+1`, the core), where the entry is

```
S_{n_max,n_max} = 2 a' - a' w_{n_max} = a' (2 - w_{n_max})
```

`w_{n_max} = 2/[n_max(n_max+1)] -> 0` as `n_max` grows, so this entry
approaches `2 a' = A(core)` and **stays `O(1)` in `n_max`** — it does not
shrink with resolution the way every other diagonal entry does. This is
exactly the mechanism: a single, `n`-independent, positive (destabilizing,
since `a' = (1-epsilon_core)/Delta_s(N) > 0` for `epsilon_core < 1`,
`Delta_s(N) > 0`) energy source concentrated at the core node, that grows in
*relative* importance as the rest of the spectrum's stabilizing weights shrink
with `n` — reproducing the observed `spectral_abscissa ~ n^1.6` growth
qualitatively (a single fixed-size destabilizing term becoming an
ever-larger fraction of what an ever-finer grid can numerically resolve/damp
elsewhere).

**Which boundary, and does the production sign agree?** The destabilizing
term sits at `y=+1`, the **core** — confirmed, matching the reconstruction in
the prompt's Background section, not the outer edge. `A_0 = 0` identically
(not "small" — exactly zero, because `advection_coefficient`'s `(y+1)` factor
is exactly zero at `y=-1` for every `N`, `alpha`, `epsilon_core`), so **the
outer edge carries no energy defect at all and needs no SAT** — the existing
strong Dirichlet imposition there is left completely unchanged; this is a
deliberate no-op documented here so the asymmetry (SAT only at the core, none
at the outer edge) is not mistaken for an oversight in Phase 2.

This is identical for `phi` and `pi`: `advection_term` uses the same
`A_array` for both fields (`forward_rhs.py` calls it twice, once per field),
so the same `S`, same core-node defect, same `tau` applies independently to
each field's own energy `E_phi = 1/2 phi^T H phi`, `E_pi = 1/2 pi^T H pi`.

## 4. The SAT penalty and the admissible range of `tau`

Add, to the `du/dN` for whichever field `u` (`phi_full` or `pi_full`), a
penalty acting only at the core node:

```
du/dN  +=  - (1/H_{n_max,n_max}) * tau * e_core * (u_core - g)
```

(`e_core` is the unit vector at the core index; `H_{n_max,n_max} = w_{n_max}`.)
Energy balance, using the `S` computed above:

```
dE/dN = u^T H (A_split u)  +  u^T H (SAT term)
      = 1/2 u^T S u  -  tau * u_core * (u_core - g)
      = -a' E  +  1/2 A(core) u_core^2  -  tau u_core^2  +  tau u_core g
```

The `u_core^2` coefficient is `1/2 A(core) - tau`. Choosing

```
tau = 1/2 * A(core)          (A(core) = 2 a' = 2(1-epsilon_core)/Delta_s(N))
```

cancels it **exactly** (not just bounds it), leaving

```
dE/dN = -a' E + tau * u_core * g
```

— a linear, bounded forcing term (for any bounded `g`) added to pure
exponential decay at rate `a'`. Any `tau >= A(core)/2` is admissible (the
`u_core^2` coefficient becomes `<= 0`); `tau = A(core)/2` is the minimal
value that removes the instability without over-damping, and is the value
used in Section 5's prototype and recommended for Phase 2. There is no
"margin" beyond exact cancellation being asked for here since the resulting
bulk rate `-a'` is itself already the entire physical damping available in
this term — adding extra `tau` above the minimal value would just add more
core-localized damping on top, changing the model further than necessary.

**Reproducing the validated recipe.** For the standalone advection-only,
full-node case (no gradient, no couplings): treating the whole system as
approximately a single decaying mode gives `dE/dN = -2*lambda*E` for a
scalar-like decay rate `lambda`, so `-a' E = -2 lambda E => lambda = -a'/2 =
-A(core)/4`. This exactly reproduces the previously-validated number quoted
in the prompt's Background section (`-A(core)/4`, n-independent) — see
Section 5 for the direct numerical confirmation via the assembled operator's
actual eigenvalues (not just this heuristic single-mode argument).

## 5. Numerical validation (Phase 1b/1c)

Implemented in `analyze_StiffnessSpectrum.py`:
`assemble_spatial_operator_sbp_sat()` (mirrors `assemble_spatial_operator`,
adds `A_split` in place of the plain product and the two core SAT rows) plus
`--closure {strong,sbp-sat}` on the existing `--mode spectrum` CLI, so the two
closures are compared with the same sweep machinery
(`spectral_stability_metrics`, unchanged from prompt 20).

Results (see `stiffness_spectrum_sbp_sat.csv` / test output for the full
sweep; summary here):

- SBP self-check (`_sbp_residual`) unchanged, ~1e-15: asserted in the new
  tests as a regression guard, not re-derived.
- **Advection-only** SBP-SAT operator: `spectral_abscissa` is constant at
  `-A(core)/4` to machine precision across `n_max = 7...191`, at every
  `Delta_s` tried — the closed-form Section 4 prediction confirmed exactly,
  not just qualitatively.
- **Full SBP-SAT operator** (split-form advection + SAT, gradient term
  unchanged/strong-Neumann as before): `spectral_abscissa` is bounded and
  `n`-independent (flat within a few percent) across the same `n_max` range,
  at every `Delta_s` tried, in sharp contrast to the strong-BC baseline's
  `~n^1.6` growth at the same points.
- Adding the gradient term on top of the SAT-stabilized advection does not
  reintroduce growth: the gradient term's own contribution is confirmed
  non-positive-dominant (matches prompt 18a's finding that it is already
  bulk-stable), so it acts as a guard, not a fix, exactly as anticipated.
- `growth_efold_time` at small `Delta_s` (near `N_init`, the regime that
  previously blew up) is no longer `<< N_total`: the SBP-SAT abscissa is
  negative there (pure decay, `growth_efold_time = inf`), where the
  strong-BC baseline's abscissa was large and positive.

**Phase 1 gate: PASSED.** All checkboxes in the prompt's Phase 1c list are
satisfied; see the accompanying test file
(`tests/test_sbp_sat_boundary_closure.py`) for the executable form of each
one.

## 6. Open decision for David: the SAT target `g`

This is a physics-design choice, not a free numerical parameter, and is
**not settled by this note** — sign-off needed before Phase 2 touches
production code.

The SAT penalty needs one target value `g` per field at the core node
(`g_phi`, `g_pi`). Two constraints on any valid choice: (a) `g` must be a
value that does **not** depend algebraically on the instantaneous `u_core`
itself (a self-referential `g` — e.g. "whatever `u_core` currently is" —
makes `u_core - g` identically zero and the entire SAT term, including the
stabilizing `-tau u_core^2` piece, vanishes identically; it would be a no-op,
not a weaker version of the penalty); (b) `g` should encode whatever
condition, if any, the production model already imposes at that node, so
switching from strong to weak imposition changes the *character* of the
condition (exact -> relaxed-at-rate-`tau`) but not its *target*.

- **`g_phi` (field, core).** Currently Neumann-eliminated: `d(phi)/dy = 0` at
  the core (`neumann_boundary_value(phi_full, D, boundary_index=-1)`,
  computed from the *other* nodes). **Recommendation:** set `g_phi` to that
  same `neumann_boundary_value(...)` formula, evaluated each RHS call from
  the current interior nodes. This makes the SAT the direct weak analogue of
  the existing strong condition — same target, now relaxed at rate
  `tau = A(core)/2` instead of enforced exactly every step. Trade-off to
  flag: the Neumann condition is no longer satisfied exactly at every
  instant, only relaxed toward it with an O(1/tau) transient/boundary-layer
  timescale in `N` — needs the Phase-2 regression check (`n=5,7` vs
  `FullInstanton`) to confirm this residual doesn't move the converged
  answer beyond the existing ~1e-6 tolerance.
- **`g_pi` (momentum, core).** Currently **completely free** — no boundary
  condition is imposed on `pi_core` at all; it is dynamically integrated
  with no constraint, presumably representing unconstrained outflow at the
  coordinate center. There is no existing condition to weakly reproduce.
  **Recommendation:** `g_pi = 0` (a fixed constant, not self-referential) —
  the minimal-content choice, converting the previously totally-unconstrained
  core momentum into one weakly damped toward zero at rate `A(core)/2`. This
  *does* change the model (a genuinely free DOF acquires a damping term it
  didn't have before), which is exactly why the prompt asks for this to be
  flagged rather than silently picked. Alternative considered and rejected:
  there is no way to make this SAT literally inert (see constraint (a)
  above) while still cancelling the destabilizing `u_core^2` term, so "leave
  `pi_core` exactly as free as before" and "stabilize the advection operator"
  are not simultaneously achievable — some damping at the core is the
  unavoidable cost of the fix for this field. `g_pi = 0` is the smallest
  version of that cost (no bias toward any particular nonzero momentum), but
  a nonzero `g_pi` derived from e.g. the neighbouring interior nodes'
  extrapolated value is the alternative if a bias-free damping-only
  intervention is not acceptable and some other target is preferred instead.

**Requested sign-off:** confirm (or amend) the `g_phi`/`g_pi` choices above
before Phase 2 changes the production state layout and RHS assembly.
