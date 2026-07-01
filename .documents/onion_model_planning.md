# Onion model — implementation planning notes

**Status:** design complete for a first implementation; two theoretical
issues remain open (see below). Physics derivation lives in
`onion_model.tex` / `onion_model.pdf` — this document only translates that
derivation into implementation terms and should not duplicate any
derivation detail. All equation/section numbers below refer to that
document (as compiled; renumber if it is edited).

## What this is

A gradient-corrected extension of the existing single-trajectory instanton
(`FullInstanton` / `SlowRollInstanton`), replacing the noiseless-detachment
assumption for surrounding Hubble volumes with a mean-field "onion" of
concentric comoving shells, coupled via the leading gradient term
identified by Briaud et al. The saddle point of the resulting 2D
(radius × e-fold) MSR action gives a gradient-corrected core trajectory
and a full ζ(y) profile, in place of the single ζ value the current
pipeline produces from `CompactionFunction`.

## Relationship to existing code

- Consumes an `InflatonTrajectory` for the noiseless background (needed for
  $\phi_{\rm nl}(N)$, $\pi_{\rm nl}(N)$, and the lift used in the mode
  expansion — see §12.1 of the notes). This is the same noiseless-background
  machinery already used by `FullInstanton`.
- Does **not** need the repeated Leach–Liddle scale-matching calls that
  `FullInstanton`/`SlowRollInstanton` use to anchor each layer to a physical
  scale — the $y$ coordinate (§4, eq. 4.2) is anchored once, via
  $(aH)_0 = a(N_{\rm init})H(N_{\rm init})$, fixed at the start of the
  transition. This is a genuine simplification relative to the existing
  per-layer scale-matching pattern.
- Physics equations (the potential $V$, $V'$, $V''$, and the noiseless
  background ODE) should be pulled from the single existing source of
  truth, `InflationConcepts/noiseless_equations.py`, exactly as for
  `FullInstanton` — no duplication.
- Proposed new compute target: `GradientCoupledInstanton` (working name).
  Takes the same `(N_init, N_final, delta_Nstar)`-style inputs as
  `FullInstanton`, plus a mode-truncation parameter (below), and produces:
  mode coefficient trajectories $a_n(N), b_n(N)$ (and response-field modes,
  possibly not persisted — see storage note below), the reconstructed core
  trajectory $\phi(y{=}1, N)$, and the profile $\zeta(y)$ (eq. 10.1).

## New persisted quantities / convergence parameters

- `n_max`: sinc-mode truncation (§11–12). This is the primary convergence
  parameter, analogous to how `delta_Nstar` grids are currently explored —
  expect to need convergence scans in `n_max` before trusting output.
  **Note the resolution warning in §4.4 (open issue box, "Numerical
  consequence"): required mode count grows like $e^{N-N_{\rm init}}$, not
  logarithmically. For $\delta N^\star$ of a few e-folds this may already
  need `n_max` in the tens to hundreds.** This should be checked
  empirically before committing to the spectral route for production runs.
- Shooting parameter $\lambda$ (§12.5, eq. 12.5): single scalar, root-found
  per trajectory, playing a role analogous to the existing shooting
  parameter in `FullInstanton`.
- $\zeta(y)$ profile: the new physics output. Needs a decision on how it's
  persisted/consumed downstream — presumably `CompactionFunction` should be
  extended (or a variant added) to accept a $\zeta(y)$ profile directly
  rather than the single-trajectory $\zeta(r)$ construction it currently
  builds by peeling shells off `FullInstanton`.

## Numerical scheme (§12)

Picard iteration, structurally close to the existing `FullInstanton`
solver, with mode index $n$ replacing the (absent) spatial index there:

1. Forward pass: integrate $(a_n, b_n)$ from $N_{\rm init}$ with
   $\tilde a_n = \tilde b_n = 0$ (eq. 12.4).
2. Backward pass: integrate $(\tilde a_n, \tilde b_n)$ from $N_{\rm final}$
   (eq. 12.5), using the current forward solution for the nonlinear
   $V''(\phi)$ coupling.
3. Forward pass: re-integrate $(a_n, b_n)$ with updated response-field
   sources.
4. Iterate to convergence; outer scalar root-find on $\lambda$.

Nonlinear terms ($V'$, $V''$ projected onto modes) need a pseudospectral
step: reconstruct $\phi(y,N)$ on a $y$-collocation grid, evaluate
pointwise, project back via quadrature in the $u^2\,du$ measure (§7, §11).
No FFT is required at the mode counts anticipated for a first
implementation; direct quadrature should suffice unless `n_max` turns out
to need to be very large (see resolution warning above).

**No explicit freezing** (§10): integrate the full rectangle
$y\in[0,1]$, $N\in[N_{\rm init}, N_{\rm final}]$ unconditionally; extract
$\zeta(y)$ as a post-processing crossing-time scan of the reconstructed
$\phi(y,\cdot)$ against $\phi_{\rm end}$, exactly analogous to the existing
1D $\zeta$ extraction, applied pointwise in $y$.

## Cross-checks

- **Reduction limit:** with gradient coupling artificially switched off
  (or `n_max` truncated so aggressively that only the $y$-independent mode
  survives), the core trajectory $\phi(1,N)$ should reduce to the existing
  `FullInstanton` output. This is the most important first acceptance test.
- **Discrete/finite-shell cross-check** (§3, panel): a finite-difference
  implementation on a discrete, non-uniformly spaced shell grid (§3) is a
  physically equivalent, independently-coded numerical scheme for the same
  action, and is flagged in the notes as possibly *more* practical than the
  spectral route given the exponential mode-resolution requirement. Worth
  prototyping in parallel rather than only as a follow-up — see the note in
  §14 (Summary) of the LaTeX document.
- **Terminal-condition placement check** (relates to the second open issue
  below): before relying on $\tilde\phi(y,N_{\rm final})=0$, run the
  *existing* 1D `FullInstanton` solver with its terminal condition placed
  at several $N_{\rm turn} > N_{\rm final}$ and confirm the solution for
  $N \le N_{\rm final}$ is insensitive to the choice. Cheap to do now, and
  informs confidence in the analogous assumption for the 2D system.

## Open theoretical issues (§13) — do not present as settled

1. **Probability interpretation of $S_{\rm MSR}$ for the 2D configuration.**
   It is not yet resolved how to compare the 2D action to the existing 1D
   instanton action, given that the outer shells genuinely participate in
   the collapse/compaction-function calculation rather than being a
   for-free addendum. Do not report a "corrected PBH formation probability"
   from this pipeline until this is resolved.
2. **Largest-time-equation justification for the terminal boundary
   condition.** The heuristic argument (response fields killed by
   homogeneous equations in the noiseless post-transition region) is
   plausible but not rigorously established for the stochastic (MSR) path
   integral. See the cross-check above; if the 1D numerical test shows
   sensitivity to $N_{\rm turn}$ placement, this needs to be revisited
   before trusting the 2D terminal condition.

## Suggested prompt sequence (draft, for discussion before writing actual `.prompts/` files)

1. `noiseless-lift-utilities` — helper to evaluate $\phi_{\rm nl}(N)$,
   $\pi_{\rm nl}(N)$ and their derivatives from an `InflatonTrajectory`,
   reusable for the mode-expansion lift (§12.1).
2. `sinc-basis-and-projection` — implement $f_n(u)$, eigenvalues, and
   quadrature-based forward/inverse projection in the $u^2\,du$ measure;
   unit-test orthogonality numerically.
3. `mode-ode-system` — implement the RHS of eq. 12.3 (forward sector only,
   response fields fixed at zero), i.e. the "zeroth Picard iterate" —
   should reduce to `FullInstanton`'s RHS at $n_{\rm max}=0$/no coupling.
4. `response-mode-ode-system` — implement the backward-sector RHS,
   with the shared terminal condition eq. 12.5.
5. `picard-iteration-driver` — wire up the outer iteration and the
   $\lambda$ shooting root-find.
6. `zeta-profile-extraction` — post-processing crossing-time scan (§10),
   producing $\zeta(y)$.
7. `GradientCoupledInstanton-datastore-object` — persistence, FK
   references, following the existing `DatastoreObject` factory pattern.

This sequencing follows the existing single-commit-per-prompt,
acceptance-criteria-checkbox pattern; each should be checked against the
reduction-limit cross-check above before moving to the next.
