# Onion model — implementation planning notes

**Status:** numerical scheme settled (collocation on a logarithmic,
horizon-excising coordinate, replacing an earlier spectral/sinc-basis
design); one previously-blocking issue (sub-horizon noise) is resolved by
the coordinate choice itself. Two theoretical issues remain open (see
below). Physics derivation lives in `onion_model.tex` / `onion_model.pdf`
— this document only translates that derivation into implementation
terms and should not duplicate any derivation detail. All equation/section
numbers below refer to that document (as compiled; renumber if it is
edited).

## What this is

A gradient-corrected extension of the existing single-trajectory instanton
(`FullInstanton` / `SlowRollInstanton`), replacing the noiseless-detachment
assumption for surrounding Hubble volumes with a mean-field "onion"
covering the region **exterior to the current horizon only**, coupled via
the leading gradient term identified by Briaud et al. The saddle point of
the resulting 2D (radius × e-fold) MSR action gives a gradient-corrected
core trajectory (read off at the domain's inner edge, the current
horizon) and a full ζ(y) profile, in place of the single ζ value the
current pipeline produces from `CompactionFunction`.

## Relationship to existing code

- Consumes an `InflatonTrajectory` for the noiseless background (needed
  for $\phi_{\rm nl}(N)$, $\pi_{\rm nl}(N)$, used both as outer boundary
  data and as an optional numerical-conditioning reference — see
  "Grid representation" below). Same noiseless-background machinery
  already used by `FullInstanton`.
- The comoving coordinate is **not** anchored once and fixed, unlike an
  earlier design: the domain's inner edge is the *current* horizon,
  $r_H(N) = 1/[a(N)H(\phi(1,N),\pi(1,N))]$ (§4.1, eq. 4.1) — genuinely
  solution-dependent, recomputed from the current core state at every RHS
  evaluation, the same way $H^2,\epsilon_1$ already are elsewhere. This
  needs no separate ODE (it's algebraic from the current mode/grid state),
  but it does mean the coordinate map itself changes at every step —
  see "Numerical scheme" below for what that costs in practice (nothing
  beyond recomputing scalar coefficients).
- Physics equations (the potential $V$, $V'$, $V''$, and the noiseless
  background ODE) should be pulled from the single existing source of
  truth, `InflationConcepts/noiseless_equations.py`, exactly as for
  `FullInstanton` — no duplication.
- Proposed new compute target: `GradientCoupledInstanton` (working name).
  Takes the same `(N_init, N_final, delta_Nstar)`-style inputs as
  `FullInstanton`, plus a collocation-point-count parameter (below), and
  produces: grid-point trajectories $\phi_j(N), \pi_j(N)$ (and
  response-field grid values, possibly not persisted — see storage note
  below), the reconstructed core/horizon trajectory $\phi(y{=}1, N)$, and
  the profile $\zeta(y)$ (eq. 10.1, §10).

## New persisted quantities / convergence parameters

- `n_max`: LGL collocation point count (§11). Primary convergence
  parameter, analogous to how `delta_Nstar` grids are currently explored —
  expect to need convergence scans in `n_max` before trusting output.
  **Unlike the earlier spectral design, there is no known reason to expect
  this to need to scale exponentially with $N_{\rm final}-N_{\rm init}$**:
  the logarithmic radial coordinate was adopted specifically to turn the
  exponentially-compressed near-horizon structure into $\Or(1)$ structure
  in $y$ (§4.3, discussion after eq. 4.8). This should still be checked
  empirically once a first implementation exists, but there's no
  structural reason to budget for the tens-to-hundreds mode counts the
  earlier design anticipated.
- Shooting parameter $\lambda$ (§12.4, eq. 12.4): single scalar,
  root-found per trajectory, playing a role analogous to the existing
  shooting parameter in `FullInstanton`.
- $\zeta(y)$ profile: the physics output. Needs a decision on how it's
  persisted/consumed downstream — presumably `CompactionFunction` should
  be extended (or a variant added) to accept a $\zeta(y)$ profile directly
  rather than the single-trajectory $\zeta(r)$ construction it currently
  builds by peeling shells off `FullInstanton`. Extraction uses per-shell
  noiseless downflow + density matching (§10, eq. 10.1) — **not** a
  crossing-time scan; see "ζ extraction" below.

## Numerical scheme (§11–12)

**Coordinate:** logarithmic radial variable, horizon-excising (§4). Domain
is $y\in[-1,1]$ at every $N$: $y=-1$ the fixed outer edge $r_{\rm out}$,
$y=+1$ the current horizon $r_H(N)$. There is **no sub-horizon region
inside the domain** — this is what resolves the previously-blocking
sub-horizon-noise issue, by construction rather than by a numerical patch
(§13.1). Two solution-dependent scalars feed into the discretized
operator at every $N$: $\Delta s(N) = \ln(r_{\rm out}/r_H(N))$ and
$\epsilon_1^{\rm core}(N)=\epsilon_1[\phi(1,N),\pi(1,N)]$, both algebraic
from the current core grid value — no new integrated state variable, and
$\d\Delta s/\d N = 1-\epsilon_1^{\rm core}(N)$ if the derivative is ever
needed directly rather than recomputed from consecutive $N$ values.

**Discretization: LGL collocation, not a spectral mode expansion.**
Represent $\phi,\pi,\tilde\phi,\tilde\pi$ by their values on a fixed grid
of Legendre–Gauss–Lobatto (LGL) nodes $\{y_j\}\subset[-1,1]$ (§11.1), not
mode coefficients in a sinc/eigenfunction basis (the earlier design). This
was chosen over Chebyshev collocation so a summation-by-parts (SBP)
structure with a *diagonal* norm matrix is available essentially for free
if needed (see below).

- **Node/weight generation:** no closed form (unlike Chebyshev's
  $\cos(j\pi/n)$); use the eigenvalues of a symmetric tridiagonal Jacobi
  matrix (Golub–Welsch-type construction). Reference implementations:
  [`FastGaussQuadrature.jl`](https://juliaapproximation.github.io/FastGaussQuadrature.jl/stable/gaussquadrature/)
  (Julia, would need translating) or the Python notebook at
  [`sphglltools`](https://colab.research.google.com/github/caiociardelli/sphglltools/blob/main/doc/L3_Gauss_Lobatto_Legendre_quadrature.ipynb).
  Standard, tabulated technique — not a research risk, but genuinely more
  code than the Chebyshev cosine formula, budget for it as its own small
  utility.
- **Differentiation matrices** $D,D^{(2)}$: built once from the grid
  alone (they don't depend on $\Delta s(N)$ or anything physics-related),
  reused at every $N$. $\Lop$ itself is then just $D,D^{(2)}$ multiplied
  by node-dependent scalar coefficients recomputed each $N$ (eq. 11.2) —
  same pattern as every other solution-dependent coefficient in this
  scheme ($H^2,\epsilon_1,D_{ij}$ evaluated pointwise). No fast transform
  (no Legendre analogue of the Chebyshev DCT) — irrelevant at anticipated
  node counts ($\Or(n^2)$ direct application is fine at $n\sim100$; only
  matters if `n_max` ever needs to reach the thousands).
- **No lift required** (contrast the earlier design, §12.1 discussion):
  the outer Dirichlet condition is just a boundary-row assignment
  $\phi_0(N)=\phi_{\rm nl}(N)$, not something a sinc basis vanishing at
  the boundary forced onto the construction. Tracking the deviation
  $\phi_j-\phi_{\rm nl}$ instead of $\phi_j$ directly is still worth
  considering purely for numerical conditioning (staying near a
  well-scaled reference rather than raw field values spanning many
  orders of magnitude) — an implementation choice, not decided here;
  prototype without it first and add only if conditioning problems show
  up.

**Boundary conditions: hard elimination first.**
- $y=-1$ ($j=0$): plain Dirichlet rows, trivial.
- $y=+1$ ($j=n_{\rm max}$): Neumann rows for $\phi,\tilde\pi$
  ($\partial_y\phi=0$, $\partial_y\tilde\pi=0$), via **hard elimination**
  — solve the Neumann row for the boundary node value and substitute it
  into the dense interior rows of $D^{(2)}$ (eq. 11.3). Cheap, one dot
  product per RHS evaluation. **Build this first.** It carries no
  stability guarantee, but is the thing to try before reaching for more
  machinery — check empirically for stiff/spurious/complex eigenvalues
  under the RK integrator before assuming a problem exists.
- **Fallback, only if hard elimination shows instability:** weighted SBP
  + simultaneous-approximation-term (SAT) boundary treatment. Note this
  is *not* the free upgrade plain LGL/SBP usually is: our operator is
  self-adjoint w.r.t.\ the *weighted*, $N$-dependent measure $\mu(y,N)\,dy$
  (§7.1), not the flat measure standard LGL/SBP assumes, so the norm
  matrix $H=\mathrm{diag}(w_j\mu(y_j,N))$ is itself $N$-dependent and the
  SBP property needs re-verifying (or the weighted operator re-derived)
  at every $N$ — more work than a naive port of standard LGL/SBP tables.
  Still standard technique (weighted/generalized SBP is documented in the
  literature), just budget for it as real work if it turns out to be
  needed, not a drop-in swap.

**Terminal condition (§12.3): substantially simpler than the earlier
spectral design.** With LGL nodes including both endpoints by
construction, the Lagrange-multiplier condition is an ordinary
finite-dimensional stationarity condition — no distributional subtlety, no
$n^2$-growing terminal coefficients, no Gibbs-phenomenon convergence
caveat (contrast the mode-expansion scheme's eq. 12.12/12.13, now
retired). $\tilde\phi_j(N_{\rm final})=0$ for every interior node, and
$\tilde\phi_{n_{\rm max}}(N_{\rm final}) = -\lambda/[w_{n_{\rm max}}\mu(1,N_{\rm final})]$
at the boundary node, with $w_{n_{\rm max}}=2/[n_{\rm max}(n_{\rm max}+1)]$
a known closed form (eq. 11.1). This is a genuine implementation
simplification relative to the earlier design, not just a change of
notation.

**ζ extraction (§10, eq. 10.1): density matching via per-shell downflow,
not a crossing-time scan.** For each $y_j$: take the state
$(\phi_j(N_{\rm final}),\pi_j(N_{\rm final}))$ at the shared final time
(no per-shell crossing search), continue *that shell's own* trajectory
noiselessly forward to $\epsilon_1=1$, evaluate $\rho$ there, density-match
against the noiseless background trajectory to find $N_{\rm nl}(\rho)$,
and set $\zeta(y_j) = N_{\rm end}(y_j) - N_{\rm nl}(\rho_{\rm end}(y_j))$.
This is the *same* Steps-A/B/C construction `CompactionFunction` already
uses for the single-trajectory case (downflow to $\epsilon_1=1$, then
match against background) — reuse that machinery per-shell rather than
re-deriving it; there is no separate "flat-gauge" extraction path to
choose between.

## Cross-checks

- **Reduction limit:** with gradient coupling artificially switched off
  (the $\aHo^2/\aHloc^2\Lop$ term zeroed), the core trajectory
  $\phi(1,N)$ should reduce to the existing `FullInstanton` output. Most
  important first acceptance test, unchanged in character from the
  earlier design.
- **Discrete/finite-shell cross-check** (§3, panel): a finite-difference
  implementation on a discrete, non-uniformly spaced shell grid is a
  physically equivalent, independently-coded numerical scheme for the
  same action. Worth keeping in mind as an independent check, though with
  the sub-horizon-noise issue now resolved by the coordinate choice
  itself, this is a lower priority than it was — see §14 (Summary) of
  the LaTeX document.
- **Terminal-condition placement check** (relates to the second open
  issue below): before relying on $\tilde\phi(y,N_{\rm final})=0$, run the
  *existing* 1D `FullInstanton` solver with its terminal condition placed
  at several $N_{\rm turn} > N_{\rm final}$ and confirm the solution for
  $N \le N_{\rm final}$ is insensitive to the choice. Cheap to do now, and
  informs confidence in the analogous assumption for the 2D system.
- **New: advection/response-field coupling.** The response-field
  equations' advective-adjoint term (§8, eq. 8.1c–d) was derived fresh in
  this design pass and flagged in the notes as not yet independently
  cross-checked to the same standard as the rest of the derivation.
  Before trusting it numerically, worth an isolated unit test: e.g.\
  confirm energy/norm-conservation-type behaviour of the discretized
  advection operator alone (zero potential, zero noise, zero gradient
  coupling) matches the expected adjoint relationship between the forward
  and backward passes.
- **New: LGL/SBP eigenvalue check.** If hard elimination is adopted per
  above, explicitly check the eigenvalue spectrum of the discretized
  $\Lop$ (plus advection) operator for spurious growth or large imaginary
  parts before trusting long production runs — this is the specific,
  known failure mode motivating the SBP+SAT fallback.

## Open theoretical issues (§13) — do not present as settled

1. **Probability interpretation of $S_{\rm MSR}$ for the 2D
   configuration.** It is not yet resolved how to compare the 2D action
   to the existing 1D instanton action, given that the outer shells
   genuinely participate in the collapse/compaction-function calculation
   rather than being a for-free addendum. Do not report a "corrected PBH
   formation probability" from this pipeline until this is resolved.
2. **Largest-time-equation justification for the terminal boundary
   condition.** The heuristic argument (response fields killed by
   homogeneous equations in the noiseless post-transition region) is
   plausible but not rigorously established for the stochastic (MSR) path
   integral. See the cross-check above; if the 1D numerical test shows
   sensitivity to $N_{\rm turn}$ placement, this needs to be revisited
   before trusting the 2D terminal condition.

(The sub-horizon-noise issue that previously sat here, and blocked
proceeding to implementation, is resolved by the coordinate choice itself
— §13.1 of the notes records this explicitly, including why the earlier
candidate fixes were retired rather than built.)

## Suggested prompt sequence (draft, for discussion before writing actual `.prompts/` files)

1. `noiseless-lift-utilities` — helper to evaluate $\phi_{\rm nl}(N)$,
   $\pi_{\rm nl}(N)$ and their derivatives from an `InflatonTrajectory`;
   also exposes $\rho(\phi,\pi)$ for the ζ-extraction density match.
2. `lgl-nodes-and-differentiation` — Jacobi-eigenvalue node/weight
   generation, $D,D^{(2)}$ construction; unit-test against known LGL
   tables for small $n_{\rm max}$, and confirm $D,D^{(2)}$ reproduce exact
   derivatives on low-degree polynomials.
3. `onion-coordinate-utilities` — $r_H(N)$, $\Delta s(N)$, $\mu(y,N)$,
   $A(y,N)$ evaluation from a current core state; unit-test
   $\Delta s(N_{\rm init})=0$ and the $y=\pm1$ endpoint limits called out
   in §4–5 of the notes.
4. `discretized-Lop-and-advection` — build the $N$-dependent scalar
   coefficients multiplying $D,D^{(2)}$ (eq. 11.2) and the advection term;
   Neumann hard-elimination at $y=+1$ (eq. 11.3).
5. `colloc-ode-system` — implement the RHS of eq. 12.1 (forward sector
   only, response fields fixed at zero), i.e.\ the "zeroth Picard
   iterate" — should reduce to `FullInstanton`'s RHS when gradient
   coupling is switched off (reduction-limit cross-check).
6. `response-colloc-ode-system` — implement the backward-sector RHS
   (eq. 12.1c–d), with the terminal condition eq. 12.3. Include the
   advection-adjoint unit test flagged above.
7. `picard-iteration-driver` — wire up the outer iteration and the
   $\lambda$ shooting root-find (eq. 12.4).
8. `zeta-profile-extraction` — per-shell noiseless downflow + density
   match (§10, eq. 10.1), reusing `CompactionFunction`'s existing
   Steps-A/B/C machinery rather than re-deriving it, producing $\zeta(y)$.
9. `GradientCoupledInstanton-datastore-object` — persistence, FK
   references, following the existing `DatastoreObject` factory pattern.

This sequencing follows the existing single-commit-per-prompt,
acceptance-criteria-checkbox pattern; each should be checked against the
reduction-limit cross-check above before moving to the next. Prompts 2–4
are new relative to the earlier (spectral) sequencing and have no direct
analogue there; prompts 5–9 replace what was previously a 7-prompt
sequence built around mode coefficients.
