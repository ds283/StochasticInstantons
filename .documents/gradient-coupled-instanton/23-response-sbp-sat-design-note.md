# Design note: response-sector SBP-SAT closure + lambda-scaling (prompt 23)

Prompt: `.prompts/gradient-coupled-instanton/23-response-sector-sbp-sat-closure.md`.
Status: **Phase 1 complete for both parts.** Part A is a clean negative (not
ported, with full supporting evidence below). Part B is confirmed necessary
and implemented in Phase 2.

## Part A — SBP-SAT closure: clean negative

### The question

`response_rhs.py`'s pre-prompt-23 docstring flagged its `advection_term` call
as a "known, symmetric follow-on candidate" for the forward sector's SBP-SAT
port (prompts 21/21a): it uses the *same* `A_array` construction as the
forward sector's advection term, and `rmom_full` is *also* Neumann-eliminated
at the core (mirroring the forward sector's pre-port `phi_core`). The
hypothesis was that this would produce the same `n_max^1.6`-growing spectral
defect forward_rhs.py had before its own port.

### Why the naive symmetry argument is wrong

`response_rhs` is integrated **backward** in `N` (`picard.py`'s
`solve_ivp` call uses a decreasing `t_span`, `(N_stop, N_start)`). For a
linear mode `dy/dN = M y` integrated with RK45 using a *negative* step `h`
(backward), the quantity that governs numerical stability is `z = h*lambda`,
not `lambda` itself. This flips which **sign** of `Re(lambda)` is
catastrophic:

- **Forward integration (`h>0`, the forward sector's own case):**
  `Re(lambda) >> 0` growing with `n_max` is catastrophic — `z = h*lambda > 0`
  falls outside RK45's (bounded) stability region for *any* step size. This
  is exactly prompt 21's disease (`spectral_abscissa = max(Re(eig))` growing
  with `n_max`).
- **Backward integration (`h<0`, the response sector's actual case):**
  `Re(lambda) >> 0` growing with `n_max` is merely **stiffness**
  (`z = h*lambda < 0`, deep in the left half-plane; conditionally stable —
  forces a smaller step, does not blow up). It is `Re(lambda) << 0` growing
  *more negative* with `n_max` that is catastrophic (`z = h*lambda > 0` for
  any `h<0`, unconditionally unstable).

So the response sector's own "spectral abscissa" — the quantity that must
stay bounded in `n_max` for the *actual* backward solve to be safe — is
`max(Re(-eig)) = -min(Re(eig))` of the assembled matrix (`dy/dN = M y`
convention, built exactly like the forward sector's `assemble_spatial_operator`
for direct comparability), **not** `max(Re(eig))` itself.
`analyze_StiffnessSpectrum.response_spectral_stability_metrics` encodes this
by feeding `spectral_stability_metrics` the *negated* eigenvalues.

### Empirical findings (Phase 1)

Implemented in `analyze_StiffnessSpectrum.py`:
`assemble_response_operator_strong` (pre-port, plain-product advection,
`rmom_core` Neumann-eliminated — mirrors `response_rhs.py`'s own layout
exactly, validated to `~1e-15` against a finite-difference Jacobian of the
real `response_rhs`, see `self_check_response_assembled_operator`) and
`assemble_response_operator_sbp_sat` (split-form advection on both fields,
`rmom_core` promoted to a free/integrated DOF with a SAT toward the *live
Neumann target* — mirrors forward's `g_phi_core` role — and `rfield_core`
SAT'd toward a fixed `g=0` — mirrors forward's `g_pi_core` role, but with a
trivial zero target since the terminal condition already supplies rfield's
"data", per the prompt's own suggestion to try dissipation-only first).

**1. Confirm the disease — NOT confirmed.** Across the full default sweep
grid (`DEFAULT_ALPHA_VALUES x DEFAULT_N_VALUES`, `n_max = 8..192`), the
pre-port strong closure's *backward-relevant* abscissa
(`response_spectral_stability_metrics`) is already bounded/`n_max`-independent
(worst last/first ratio ≈ 1.87 across the whole grid; typical points show
essentially flat behaviour, e.g. `-1.42 → -1.41` at `alpha=0.1, N=0.1`,
`n_max=8→192`). This is a direct, formal contradiction of the "same
destabilising core-node mechanism by symmetry" hypothesis, once the
backward-integration sign flip is correctly accounted for — the mechanism
*is* the same defective matrix, but its **consequence** for the direction
this sector is actually integrated in is different (bounded, not
catastrophic).

Meanwhile `max(Re(eig))` (the *safe-direction* quantity for backward
integration — stiffness only) *does* grow sharply with `n_max`
(e.g. `44 → 6541` at `alpha=0.1, N=0.1`, `n_max=8→192`) — qualitatively
similar to the forward sector's own pre-port growth, but in the direction
that costs step count, not correctness.

**2. Confirm Part A cures it — N/A (nothing to cure); does it help anyway? No.**
Tested a same-recipe SBP-SAT port with the theoretically-required sign flip
on the live-Neumann-target field (confirmed empirically necessary: the
*forward*-sign SAT on `rmom_core`, i.e. copying `g_phi_core`'s exact
convention unchanged, makes the backward-catastrophic direction *dramatically
worse* — `min(Re)` diverging to `-1.2e5` by `n_max=192` at
`alpha=0.1, N=0.1`, versus the unmodified strong closure's already-bounded
`~7.9`). With the correct sign flip and the *exact* cancellation
`tau = A(core)/2` (not forward's own empirically-doubled `tau = |A(core)|`
— doubling was tested and found to overshoot the cancellation, reintroducing
exactly the kind of `n_max`-growing catastrophic mode this closure is meant
to remove), the backward-relevant abscissa stays bounded — but *so does the
unmodified strong closure*, so there is no defect being cured. And the
safe-direction stiffness (`max(Re)`) is markedly **worse** with the SAT than
without it at every point tested (e.g. `6541 → 149500` at
`alpha=0.1, N=0.1`, `n_max=192`, roughly 23x worse).

**3. Adjoint-consistency — confirmed unaffected.**
`analyze_StiffnessSpectrum.compute_forward_sat_vs_response_adjoint_mismatch`
pairs the CURRENT PRODUCTION forward operator (prompt 21a's split-form
advection) against the UNCHANGED response operator (plain advection, as it
remains after this prompt) and checks the 18a boundary block-mismatch
diagnostic. The mismatch stays `O(1)` and bounded across `n_max=8..192`
(worst growth ratio ≈ 1.03 across the default grid), closely matching the
pre-existing (both-sectors-plain) 18a baseline. Porting the forward sector
alone (already done, prompt 21a) did not introduce a new, growing
forward/response adjoint asymmetry.

**4. Part B — confirmed necessary (see below).**

### Decision

**Part A is NOT ported.** `response_rhs.py`'s advection remains the plain
`advection_term`, and `rmom_full` remains Neumann-eliminated at the core.
This is the prompt's own "clean-negative is valid... report it and scope it
rather than forcing the port" outcome, backed by:

- `tests/test_response_spectrum_prompt23.py::test_strong_closure_backward_abscissa_bounded_across_default_grid`
  — the strong closure's backward-relevant abscissa is bounded (regression guard).
- `tests/test_response_spectrum_prompt23.py::test_naive_sbp_sat_port_does_not_improve_safe_direction_stiffness`
  — documents the negative result (regression guard against silently
  believing the port would help without re-checking).
- `tests/test_response_spectrum_prompt23.py::test_sat_forward_vs_unchanged_response_mismatch_bounded_in_n`
  — adjoint-consistency preserved.

If a genuinely new `n_max`-dependent failure is found in this sector in the
future, re-run this diagnostic first (it is a permanent regression fixture)
rather than assuming the forward sector's recipe transfers unchanged — this
note is the record of why it does not, as derived.

---

## Part B — lambda-scaling: confirmed necessary, implemented

### The mechanism

`response_rhs` is **exactly linear and homogeneous** in `(rfield, rmom)`:
every term in its right-hand side is linear in the response fields, with
coefficients frozen from the forward background. `lambda` enters the model
*only* through the terminal condition
(`response_rhs.terminal_response_state`), never through `response_rhs`'s own
right-hand side (confirmed directly:
`self_check_response_assembled_operator`'s own finite-difference baseline
check asserts `response_rhs(state=0) == 0` exactly). By linearity,

```
r(N) = lambda * r_tilde(N)
```

where `r_tilde` solves the *identical* backward-pass ODE from the
`lambda`-independent, `O(1)`-ish terminal condition
`terminal_response_state_rescaled(grid, delta_s_N_final)` (==
`terminal_response_state(1.0, grid, delta_s_N_final)`).

At the resolved-regime scale (`delta_Nstar in {1,2,3}`, quadratic
`m/Mp=1e-5`), `lambda ~ lambda_FI ~ 1e9-4e9` (a rare-event diffusion
coefficient's reciprocal, `D_11 ~ H^2/(8 pi^2) ~ 1.6e-11`). The *physical*
terminal `rfield_core` is `-lambda / (w_core * mu(1, delta_s_N_final))`; even
before `lambda` is applied, `1/(w_core * mu(1,.))` is itself `O(1e4-1e6)`
(not literally `O(1)` — `w_core ~ 1e-2` for production `n_max`, and
`mu(1, delta_s_N) = exp(-1.5*delta_s_N)` is `O(1e-3)` to `O(1e-5)` at
production `Delta_s`), so the physical terminal condition reaches
`O(1e13-1e15)` in magnitude.

### Why this matters (and why it is *not* a single-operation precision issue)

IEEE double arithmetic is safe at these magnitudes — no individual
multiplication involving `D ~ 1e-11` and `lambda*r_tilde ~ 1e13` loses
precision or overflows (doubles handle magnitudes up to `~1e308`). The
mechanism is instead:

1. **ODE state-vector conditioning.** The backward-pass state vector mixes
   an `O(1e13+)` component (`rfield_core`) with `O(1)` components (every
   other node) under a *single* adaptive step-size controller (shared
   `atol`/`rtol`). This is a genuinely harder-conditioned problem for the
   integrator, independent of any single floating-point operation's own
   precision.
2. **Nonlinear feedback.** The huge response state feeds back into the
   forward sector via `noise_source_terms` (`D * rfield + D_phipi * rmom`),
   perturbing `phi`/`pi` — and if that perturbation is not exactly the
   intended `O(1)` physical magnitude (which the un-rescaled, direct
   `D * (astronomic rfield)` computation is *at risk of*, given the compound
   effect of (1) across the whole nonlinear Picard/shooting iteration, not
   just one ODE solve), it can drive `epsilon = 0.5*pi^2` past 1, giving
   `H_sq < 0` — prompt 22c's own Finding 4.

### Implementation

- `response_rhs.terminal_response_state_rescaled(grid, delta_s_N_final)` —
  thin wrapper for `terminal_response_state(1.0, grid, delta_s_N_final)`,
  self-documenting the rescaled convention at the call site.
- `forward_rhs.noise_source_terms` gains a `lam: float = 1.0` parameter
  (default is an exact no-op, preserving every pre-prompt-23 call/test
  bit-for-bit). When `lam != 1.0`, `rfield_full`/`rmom_full` are read as the
  rescaled `r_tilde`, and the physical sourcing term is reconstructed as
  `(D*lam)*r_tilde` — `D*lam` computed first, as its own array, before
  multiplying by the field (documented discipline against ever mixing the
  scaled/unscaled convention at a call site, not because the reverse
  grouping loses precision at this magnitude).
- `forward_rhs` gains a matching `lam: float = 1.0` parameter, threaded
  straight through.
- `picard.py`'s `picard_inner`: the backward pass now starts from
  `terminal_response_state_rescaled` (lambda-independent); the resulting
  loop-local grids are named `rfield_tilde_grid`/`rmom_tilde_grid` and feed
  the forward-sourcing splines directly (still `sinh`-transformed — still
  appropriate, just a smaller dynamic range); `_fwd_rhs` threads the current
  outer-loop `lam` through to `forward_rhs`. `picard_inner`'s own return
  statement reconstructs the **physical** `rfield_grid`/`rmom_grid`
  (`lam * rfield_tilde_grid`) exactly once, so every caller (msr_action,
  datastore storage, noise diagnostics, `zeta_C_r_at_time`) sees physical
  values unchanged from pre-prompt-23 behaviour. The one exception is
  `solve_picard`'s own `"response_dense_solution"` (a raw `OdeSolution`),
  which stays `r_tilde`-valued — documented at that key.
- `lambda=0.0` (the outer loop's own trivial starting point) degenerates
  correctly with no special-casing: the rescaled terminal condition is
  `lambda`-independent (never degenerate), and the final `* lam`
  reconstruction gives exactly zero physical response fields at `lambda=0`,
  matching prompt 22's own Finding 1 (`lambda=0` is an exact fixed point).

### Validation (Phase 1 acceptance)

`tests/test_response_lambda_scaling_prompt23.py`:

- **Linearity** (`test_response_solution_scales_exactly_with_lambda`):
  the physical and rescaled backward-pass solutions agree to `rtol=1e-6`
  after multiplying the rescaled one by `lambda`, at several `lambda`
  including a negative value.
- **Feasibility at astronomic lambda**
  (`test_rescaled_backward_pass_feasible_at_astronomic_lambda`): the
  rescaled backward pass succeeds with a bounded step/function-evaluation
  count, essentially independent of `lambda`, at `n_max=33` (the production
  ceiling) for `lambda in {1, 1e5, 1e9, 4e9}` — the resolved-regime
  magnitude. This is the concrete "stays feasible... at astronomic lambda"
  acceptance check.
- **Reconstruction to precision**
  (`test_noise_source_terms_lam_reconstructs_physical_sourcing`): the
  `(D*lam)*r_tilde` grouping reproduces the direct `D*(lam*r_tilde)`
  computation to `rtol=1e-12` at `lam` up to `1e6`.

**Caveat, honestly reported:** an *isolated* response-sector backward pass
(no forward feedback, no Picard/shooting coupling) does not itself fail at
astronomic `lambda` even *without* Part B's rescaling — it simply
materializes very large finite numbers and completes. Reproducing Finding
4's actual `H_sq_local<0`/step-death failure requires the full nonlinear
Picard/shooting loop at genuinely resolved-regime parameters
(`m/Mp=1e-5`-scale potential, `delta_Nstar in {1,2,3}`), which is a
substantially more expensive validation than a fast unit test — deferred to
the Phase 2 resolved-regime acceptance run (prompt's own Phase 2 checklist),
not re-derived here from a toy potential. Part B is implemented and unit-
tested on its own well-defined algebraic/numerical merits (linearity,
feasibility, reconstruction-to-precision) independent of that larger,
slower confirmation.

---

## Summary for Phase 2

- Part A: no production code change to `response_rhs.py`'s advection/state
  layout. Diagnostic infrastructure only (`analyze_StiffnessSpectrum.py`,
  permanent regression tests).
- Part B: implemented in `response_rhs.py`, `forward_rhs.py`, `picard.py` as
  described above. No response state-vector length change (`2*n_max-1`,
  unchanged) — Part B is a scaling convention, not a DOF promotion, so none
  of the `pack_response_state`/`unpack_response_state`/datastore
  serialization/Picard state-handling touch points prompt 23's own
  "Implementation" section anticipated (in case Part A had been ported) are
  actually needed.
