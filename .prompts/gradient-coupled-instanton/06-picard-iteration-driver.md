# Prompt 06 — Picard iteration and shooting driver

## Context

Read `./.documents/onion_model_planning.md` and `./.documents/onion_notes.tex`
before starting — §"Noise statistics in $y$ coordinates" (`eq:ncount`,
`eq:Dnoise-diag`, `eq:Dnoise-cross`, and the panel confirming the factor-of-2
convention matches `FullInstanton`'s existing
`dphi = pi + 2*D11*rfield + 2*D12*rmom`), §"Picard iteration",
§"Shooting problem". Also re-read `ComputeTargets/FullInstanton.py`'s
`picard_inner` / outer Newton loop in full (`_Dij`, `bg_rhs`, `bwd_rhs`,
`fwd_rhs`, the outer loop from `MAX_OUTER`/`OUTER_TOL` down to the Newton
update and fallback nudge) — this prompt mirrors that structure as closely
as the grid-valued generalization allows, not just its overall shape.

This prompt has two parts.

## Part A — `forward_rhs` gains mandatory response-field sourcing

**This is a genuine signature change, not a backward-compatible
extension.** `forward_rhs` (prompt 04) was scoped as "response fields
fixed at zero," meaning the equation as coded simply omits the sourcing
terms — there was never a real use case for calling it without response
fields; that was only ever a special input value for one test. Don't add
`Optional`/default-`None` parameters to preserve old call sites unchanged
— add `rfield_splines: list[SplineWrapper]`, `rmom_splines: list[SplineWrapper]`,
and `diffusion_model: AbstractDiffusionModel` as **required** parameters,
always assemble the full equation, and update every existing call site
(including in `tests/test_forward_rhs.py`) to pass explicit values.

New terms to add, per node $j$:

1. **Shell-dilution factor**:
   $$n_{\rm count}(y_j,N) = \tfrac32\Delta s(N)\,e^{3\Delta s_{\rm loc}(y_j,N)}\,e^{-\frac32(y_j+1)\Delta s(N)}$$
   Both $\Delta s(N)$ (core) and $\Delta s_{\rm loc}(y_j,N)$ (per-node) are
   already computed by the existing gradient-term assembly in
   `forward_rhs` — reuse those values, don't recompute `delta_s()` a third
   time.
2. **Diffusion matrix, per node — do not vectorize `D_matrix`.**
   `AbstractDiffusionModel.D_matrix(phi, pi, potential)` is scalar-only
   (confirmed: `MasslessDecoupledDiffusion`'s implementation returns bare
   Python floats for the off-diagonal zeros, which would not broadcast
   correctly over an array `phi`). Mirror `FullInstanton`'s own `_Dij`
   convention exactly — a Python-level loop over the $n_{\rm max}+1$ grid
   nodes calling `diffusion_model.D_matrix(phi_full[j], pi_full[j],
   potential)` — building `D11_arr`, `D12_arr`, `D22_arr` via list
   comprehension, not a vectorized call.
3. **Sourced noise coefficients**: $D_\phi=2D_{11}/n_{\rm count}$,
   $D_\pi=2D_{22}/n_{\rm count}$, $D_{\phi\pi}=2D_{12}/n_{\rm count}$,
   elementwise arrays.
4. Add `D_phi_arr*rfield_full + D_phipi_arr*rmom_full` to `dphi_full`, and
   `D_pi_arr*rmom_full + D_phipi_arr*rfield_full` to `dpi_full`.

**Strengthen the existing reduction-limit test** rather than just patch it
to keep passing: with `rfield_splines`/`rmom_splines` now mandatory, the
natural (and more rigorous) version of this test uses **constant, nonzero**
response-field splines (e.g. `SplineWrapper` over a trivial constant
array) and a real `diffusion_model` instance, compared against
`FullInstanton`'s actual `fwd_rhs` with **matching nonzero** $P_1,P_2$
values (not $P_1=P_2=0$, which only exercised the local-physics terms and
never touched the sourcing terms at all) — to floating-point precision,
with `disable_spatial_coupling=True` so the gradient/advection terms stay
out of the comparison. This is a materially better test than what prompt
04 had, not just a compatibility patch.

## Part B — the Picard/shooting driver

`ComputeTargets/GradientCoupledInstanton/picard.py`:

Mirror `FullInstanton`'s structure directly — same constants
(`MAX_OUTER`, `MAX_INNER`, `OUTER_TOL = max(atol*100, 1e-6)`,
`INNER_TOL = atol*10`), same overall shape, generalized from scalar
$(\phi,\pi,P_1,P_2)$ arrays-over-$N$ to grid-valued arrays-over-$(N,y)$
(shape `(len(N_grid), n_collocation_points)`):

- **Background/zeroth-iterate pass**: integrate `forward_rhs` with
  response splines built from all-zero arrays (this is now just a
  particular input to the mandatory-sourcing equation, matching Part A's
  reframing — not a special code path).
- **`picard_inner(lam, phi_grid_in, pi_grid_in)`**: for up to `MAX_INNER`
  iterations — build `phi_splines`/`pi_splines` (one `SplineWrapper` per
  grid node) from the current `(phi_grid, pi_grid)`; backward pass via
  `response_rhs` from `N_final` to `N_init` with
  `terminal_response_state(lam, grid, delta_s_N_final)`, `t_eval` on the
  reversed grid then reversed back (exactly `FullInstanton`'s
  `[::-1]`/`N_grid_rev` pattern); build `rfield_splines`/`rmom_splines`
  from that result; forward pass via the now-sourced `forward_rhs`; measure
  convergence as the max absolute change in `phi_grid` across the whole
  grid (generalizing `FullInstanton`'s `np.max(np.abs(phi1_new - p1_arr))`
  to `np.max(np.abs(phi_grid_new - phi_grid_in))` over the full 2D array);
  break early if below `INNER_TOL`.
- **Outer Newton loop on $\lambda$**: shooting residual is
  $\phi_{n_{\rm max}}(N_{\rm final}) - \phi_{\rm end}$ (core node, final
  row — direct generalization of `FullInstanton`'s `p1[-1] - phi_final`).
  Same finite-difference-derivative Newton step
  (`dlam = max(abs(lam)*1e-4, 1e-6)`, re-run `picard_inner` at `lam+dlam`,
  `dres_dlam = (residual_perturbed - residual)/dlam`, Newton update if
  `abs(dres_dlam) > 1e-14`), same fallback nudge otherwise
  (`lam += (phi_end - phi_core_final) * 0.1`).
- Track the same diagnostics `FullInstanton` does (`converged`,
  `final_residual`, `total_ode_solves`, `outer_iterations`,
  `newton_fallback_count`, `final_lambda`, `picard_iterations_per_outer`,
  min/max/mean picard iterations, mean time per iteration) — same names,
  same shape, so downstream code (and future eyes comparing the two
  compute targets) doesn't have to learn a second diagnostic vocabulary.

Top-level function:
`solve_picard(N_init, N_final, delta_Nstar, alpha, H_sq_nl_init, grid, trajectory, potential, diffusion_model, atol, rtol, phi_end) -> dict`
(or similar — match `FullInstanton`'s own return-dict shape where it makes
sense, including the `failure: True` pattern on non-convergence, rather
than raising).

## Tests

`tests/test_picard.py`:

- **Reduction-limit, end to end**: with gradient coupling structurally
  disabled (matching how prompt 04/05's own reduction tests worked), the
  core node's full `solve_picard` output should match what `FullInstanton`
  itself produces for the same `(N_init, N_final, delta_Nstar, potential,
  diffusion_model, phi_end)` — this is the integration-level version of
  the unit-level reduction tests already passing in prompts 04–05, and is
  the single most important acceptance test in this whole sequence so far.
  Use a small `n_collocation_points` (not the full default) to keep this
  fast, since it's a genuine multi-outer-iteration solve, not a single RHS
  evaluation.
- **Convergence diagnostics** populate correctly and match
  `FullInstanton`'s dict shape/keys.
- **Non-convergence returns a failure dict**, doesn't raise, mirroring
  `FullInstanton`'s convention (construct a scenario likely to fail, e.g.
  an absurdly tight `OUTER_TOL`-equivalent or too few `MAX_OUTER`
  iterations if that's exposed as a parameter — check how `FullInstanton`
  itself tests this, if it does, before inventing a new approach).

Also update `tests/test_forward_rhs.py` for Part A's signature change and
the strengthened reduction test, per above.

## Acceptance criteria

- [ ] `forward_rhs` requires `rfield_splines`, `rmom_splines`,
      `diffusion_model` — no optional/default-`None` parameters added for
      backward compatibility.
- [ ] `n_count` reuses the already-computed `delta_s_N`/`delta_s_loc_array`
      from the existing gradient-term assembly, not recomputed separately.
- [ ] `D_matrix` called per-node via a Python loop, never vectorized.
- [ ] Reduction-limit test in `test_forward_rhs.py` strengthened to use
      nonzero response-field splines and a real diffusion model.
- [ ] `ComputeTargets/GradientCoupledInstanton/picard.py` created,
      mirroring `FullInstanton`'s constants, convergence logic, Newton
      step, fallback nudge, and diagnostics dict shape.
- [ ] End-to-end reduction test passes against `FullInstanton`'s actual
      output for matching parameters.
- [ ] No other files touched beyond what's listed above.

## Commit

Single commit, message along the lines of:
`Add mandatory response-field sourcing to forward_rhs; add Picard/shooting driver`
