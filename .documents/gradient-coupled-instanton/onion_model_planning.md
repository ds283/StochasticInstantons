# Onion model — implementation planning notes

**Status:** numerical scheme settled (collocation on a logarithmic,
horizon-excising coordinate, replacing an earlier spectral/sinc-basis
design); one previously-blocking issue (sub-horizon noise) is resolved by
the coordinate choice itself. A second, initially-blocking issue (a
coordinate singularity at $N_{\rm init}$) is resolved by a small
regularization parameter $\alpha$ (below), pending an empirical
sensitivity check. Scale/radius assignment for the profile is now settled
in detail. Two theoretical issues remain open (see below). Physics
derivation lives in `onion_model.tex` / `onion_model.pdf` — this document
only translates that derivation into implementation terms and should not
duplicate any derivation detail. All equation/section numbers below refer
to that document (as compiled; renumber if it is edited).

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
  needs no separate ODE (it's algebraic from the current grid state), but
  it does mean the coordinate map itself changes at every step — see
  "Numerical scheme" below for what that costs in practice (nothing
  beyond recomputing scalar coefficients).
- The outer edge $r_{\rm out}=(1+\alpha)/(aH)_0$ (§4.1, eq. 4.1a) is
  **not** simply $1/(aH)_0$ — see the regularization parameter $\alpha$
  below. This also means $r_{\rm out}\cdot(aH)_0 \ne 1$ in general:
  anywhere a derivation step implicitly assumed that identity (an easy
  mistake — it bit the notes themselves during this design pass, see the
  "why $r_{\rm out}$, not $(aH)_0$" remarks at eq. 4.8/5.1), double check
  against the compiled notes rather than re-deriving from memory.
- Physics equations (the potential $V$, $V'$, $V''$, and the noiseless
  background ODE) should be pulled from the single existing source of
  truth, `InflationConcepts/noiseless_equations.py`, exactly as for
  `FullInstanton` — no duplication.
- Proposed new compute target: `GradientCoupledInstanton` (working name).
  Takes the same `(N_init, N_final, delta_Nstar)`-style inputs as
  `FullInstanton`, plus a collocation-point-count parameter and the
  regularization parameter $\alpha$ (below), and produces: grid-point
  trajectories $\phi_j(N), \pi_j(N)$ (and response-field grid values,
  possibly not persisted — see storage note below), the reconstructed
  core/horizon trajectory $\phi(y{=}1, N)$, the profile $\zeta(y)$
  (§10, eq. 10.1), and the scale-assignment outputs (§11, below).

## New persisted quantities / convergence parameters

- `n_max`: LGL collocation point count (§12). Primary convergence
  parameter, analogous to how `delta_Nstar` grids are currently explored —
  expect to need convergence scans in `n_max` before trusting output.
  **Unlike the earlier spectral design, there is no known reason to expect
  this to need to scale exponentially with $N_{\rm final}-N_{\rm init}$**:
  the logarithmic radial coordinate was adopted specifically to turn the
  exponentially-compressed near-horizon structure into $\Or(1)$ structure
  in $y$ (§4.3). This should still be checked empirically once a first
  implementation exists, but there's no structural reason to budget for
  the tens-to-hundreds mode counts the earlier design anticipated.
- **`alpha` ($\alpha$): coordinate-singularity regularization (§4.1).**
  New parameter, not present in earlier designs. With $\alpha=0$,
  $\Delta s(N_{\rm init})=0$ exactly, and the Laplacian, advection, and
  noise-dilution coefficients all diverge at $N_{\rm init}$ (traced to
  rescaling a domain that starts with zero physical width onto the fixed
  range $[-1,1]$ — see the notes for why this is believed to be a
  coordinate artefact, not a physical divergence, though the response-field
  sector has not been checked with the same rigor as the forward sector).
  $\alpha>0$ regularizes this by starting the resolved domain with small
  but finite extent. **Treat as a numerical parameter requiring a
  convergence/sensitivity scan**, the same way `n_max` is: run at a
  geometrically-spaced set of small $\alpha$ values, confirm the expected
  negligible late-time sensitivity, and extrapolate to $\alpha\to0$ if any
  residual dependence remains. Smaller $\alpha$ trades reduced physical
  content added (good) against larger, stiffer coefficients near
  $N_{\rm init}$ (bad, may need a stiff-aware integrator for the first
  stretch of $N$) — don't default to the smallest value tried without
  checking the integration actually behaves there.
- Shooting parameter $\lambda$ (§13.4, eq. 13.4): single scalar,
  root-found per trajectory, playing a role analogous to the existing
  shooting parameter in `FullInstanton`.
- $\zeta(y)$ profile: the physics output. Needs a decision on how it's
  persisted/consumed downstream — presumably `CompactionFunction` should
  be extended (or a variant added) to accept a $\zeta(y)$ profile directly
  rather than the single-trajectory $\zeta(r)$ construction it currently
  builds by peeling shells off `FullInstanton`. Extraction uses per-shell
  noiseless downflow + density matching (§10, eq. 10.1) — **not** a
  crossing-time scan; see "ζ extraction" below.
- Scale-assignment outputs (§11, new): comoving $r(y_j,N_{\rm final})$,
  areal radius $R(r)$, and physical (present-day) scale $r_{\rm phys}(y_j)$
  for every collocation node — see "Scale assignment" below for how each
  is computed and what each feeds into downstream.

## Numerical scheme (§12–13)

**Coordinate:** logarithmic radial variable, horizon-excising (§4). Domain
is $y\in[-1,1]$ at every $N$: $y=-1$ the fixed outer edge $r_{\rm out}$,
$y=+1$ the current horizon $r_H(N)$. There is **no sub-horizon region
inside the domain** — this is what resolves the previously-blocking
sub-horizon-noise issue, by construction rather than by a numerical patch
(§14.1). Solution-dependent scalars feeding into the discretized operator
at every $N$: $\Delta s(N) = \ln(r_{\rm out}/r_H(N))$ and
$\epsilon_1^{\rm core}(N)=\epsilon_1[\phi(1,N),\pi(1,N)]$, both algebraic
from the current core grid value — no new integrated state variable, and
$\d\Delta s/\d N = 1-\epsilon_1^{\rm core}(N)$ if the derivative is ever
needed directly rather than recomputed from consecutive $N$ values.

**Discretization: LGL collocation, not a spectral mode expansion.**
Represent $\phi,\pi,\tilde\phi,\tilde\pi$ by their values on a fixed grid
of Legendre–Gauss–Lobatto (LGL) nodes $\{y_j\}\subset[-1,1]$ (§12.1), not
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
  by node-dependent scalar coefficients recomputed each $N$ (eq. 12.2) —
  same pattern as every other solution-dependent coefficient in this
  scheme ($H^2,\epsilon_1,D_{ij}$ evaluated pointwise). $\Lop$ itself does
  **not** carry the $1/r_{\rm out}^2$ prefactor — that's applied
  separately, alongside $1/a(N)H(\phi,\pi)^2$, at each point of use (an
  easy place to double an already-applied factor by accident; the notes
  had this bug at one point during the design pass, now fixed — worth a
  unit test that checks the prefactor is applied exactly once). No fast
  transform (no Legendre analogue of the Chebyshev DCT) — irrelevant at
  anticipated node counts ($\Or(n^2)$ direct application is fine at
  $n\sim100$; only matters if `n_max` ever needs to reach the thousands).
- **No lift required** (contrast the earlier design, §13.1 discussion):
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
  into the dense interior rows of $D^{(2)}$ (eq. 12.3). Cheap, one dot
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
  SBP property needs re-verifying (or the operator re-derived in weighted
  form) at every $N$ — more work than a naive port of standard LGL/SBP
  tables. Still standard technique (weighted/generalized SBP is
  documented in the literature), just budget for it as real work if it
  turns out to be needed, not a drop-in swap.

**Terminal condition (§13.3): substantially simpler than the earlier
spectral design.** With LGL nodes including both endpoints by
construction, the Lagrange-multiplier condition is an ordinary
finite-dimensional stationarity condition — no distributional subtlety, no
$n^2$-growing terminal coefficients, no Gibbs-phenomenon convergence
caveat (contrast the mode-expansion scheme's eq. 12.12/12.13 in the
retired design). $\tilde\phi_j(N_{\rm final})=0$ for every interior node,
and $\tilde\phi_{n_{\rm max}}(N_{\rm final}) = -\lambda/[w_{n_{\rm max}}\mu(1,N_{\rm final})]$
at the boundary node, with $w_{n_{\rm max}}=2/[n_{\rm max}(n_{\rm max}+1)]$
a known closed form (eq. 12.1). Genuine implementation simplification
relative to the earlier design, not just a change of notation.

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

**Scale assignment (§11): three distinct quantities, do not conflate.**
New relative to earlier designs, and worth particular care since a subtle
version of this was gotten wrong twice during the design pass before
settling.

1. **Comoving $r(y_j,N_{\rm final})$** — read directly off the coordinate
   map (eq. 4.3), using the already-solved $\Delta s(N_{\rm final})$. No
   separate calculation.
2. **Areal radius** $R(r)=a\,r\,e^{\zeta(r)}$ — the input to the standard
   compaction-function formula (§11.2, eq. 11.1),
   $C(r)=\tfrac23[1-(1+r\zeta'(r))^2]$. **This formula wants $\zeta$ and
   $\zeta'$ as functions of comoving $r$, not areal $R$** — do not pass
   $\zeta(R)$ to it. $\zeta'(r)$ via chain rule from the collocation
   derivative $\d\zeta/\d y$ (already available) and the analytic
   $\d r/\d y$ from the coordinate map — no new derivative machinery.
   $R$ itself is not an observable; it exists to translate the profile
   into the language NR collapse-threshold calibrations
   (Musco/Escrivá/Young et al.) are phrased in.
3. **Physical (present-day) scale** $r_{\rm phys}(y)$ — solve the
   existing Leach–Liddle scale-matching formula **once**, anchored at
   $r_{\rm out}$ (since $y=-1$ sits exactly on the noiseless background),
   then propagate to every other node by the fixed ratio
   $r_{\rm phys}(y) = [r(y,N_{\rm final})/r_{\rm out}]\,r_{\rm phys,out}$
   (eq. 11.2 in §11). **Do not** repeat the full Leach–Liddle solve per
   shell, and do not try to assign each shell its own horizon-crossing
   $e$-fold by inverting the background expansion history against
   $k(y)$ — this was tried during the design pass and is unnecessary,
   since comoving-ness already fixes the today's-scale conversion to a
   single constant common to every mode (§11.3, the "candidate refinement,
   considered and rejected" panel). The genuinely per-shell part of the
   existing Leach–Liddle machinery — $V_{\rm end,\,downflow}$ from each
   shell's own downflow — is unaffected and still needed; only the "which
   comoving scale is this" piece changes from a trajectory-position
   lookup (valid only in the single-trajectory construction, where
   comoving radius was *defined* via trajectory position) to the direct
   ratio above.

## Cross-checks

- **Reduction limit:** with gradient coupling artificially switched off
  (the $\Lop$ term zeroed), the core trajectory $\phi(1,N)$ should reduce
  to the existing `FullInstanton` output. Most important first acceptance
  test, unchanged in character from the earlier design.
- **Discrete/finite-shell cross-check** (§3, panel): a finite-difference
  implementation on a discrete, non-uniformly spaced shell grid is a
  physically equivalent, independently-coded numerical scheme for the
  same action. With the sub-horizon-noise issue now resolved by the
  coordinate choice itself, this is a lower priority than it was — see
  §15 (Summary) of the LaTeX document.
- **New: scale-assignment equivalence.** The core's assigned physical
  scale under the continuum scheme should exactly match the innermost
  shell's assigned scale under the discrete/peeling scheme, up to
  $\Or(\alpha)$ (§11.4). **This check depends on an unverified assumption
  about the existing discrete-scheme code**: it needs $r_i=1/[a(i)H(i)]$
  there to use the instanton's own local trajectory, not the background.
  Check this in the actual implementation before relying on the
  equivalence — if the existing code in fact uses background $a,H$, the
  two schemes only agree in the noiseless limit, and this needs
  revisiting (§11.4, todo box).
- **New: $\alpha$-sensitivity scan.** Run at a spread of small $\alpha$
  values (geometrically spaced) and confirm the expected negligible
  late-time sensitivity; extrapolate to $\alpha\to0$ if residual
  dependence remains. See the `alpha` entry above for the stiffness
  trade-off to watch for at the small end of the range.
- **Terminal-condition placement check** (relates to the second open
  issue below): before relying on $\tilde\phi(y,N_{\rm final})=0$, run the
  *existing* 1D `FullInstanton` solver with its terminal condition placed
  at several $N_{\rm turn} > N_{\rm final}$ and confirm the solution for
  $N \le N_{\rm final}$ is insensitive to the choice. Cheap to do now, and
  informs confidence in the analogous assumption for the 2D system.
- **Advection/response-field coupling.** The response-field equations'
  advective-adjoint term (§8, eq. 8.1c–d) was derived fresh during this
  design pass and flagged in the notes as not yet independently
  cross-checked to the same standard as the rest of the derivation.
  Before trusting it numerically, worth an isolated unit test: e.g.\
  confirm energy/norm-conservation-type behaviour of the discretized
  advection operator alone (zero potential, zero noise, zero gradient
  coupling) matches the expected adjoint relationship between the forward
  and backward passes.
- **LGL/SBP eigenvalue check.** If hard elimination is adopted per above,
  explicitly check the eigenvalue spectrum of the discretized $\Lop$
  (plus advection) operator for spurious growth or large imaginary parts
  before trusting long production runs — this is the specific, known
  failure mode motivating the SBP+SAT fallback.

## Open theoretical issues (§14) — do not present as settled

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
— §14.1 of the notes records this explicitly, including why the earlier
candidate fixes were retired rather than built. The $N_{\rm init}$
coordinate-singularity issue is resolved pending the $\alpha$-sensitivity
check above, not left open in the notes.)

## Suggested prompt sequence (draft, for discussion before writing actual `.prompts/` files)

1. `lgl-nodes-and-differentiation` — Jacobi-eigenvalue node/weight
   generation, $D,D^{(2)}$ construction; unit-test against known LGL
   tables for small $n_{\rm max}$, and confirm $D,D^{(2)}$ reproduce exact
   derivatives on low-degree polynomials.
2. `onion-coordinate-utilities` — $r_H(N)$, $\Delta s(N)$, $\mu(y,N)$,
   $A(y,N)$ evaluation from a current core state, including the $\alpha$
   parameter in $r_{\rm out}=(1+\alpha)/(aH)_0$; unit-test
   $\Delta s(N_{\rm init})=\ln(1+\alpha)$ and the $y=\pm1$ endpoint limits
   called out in §4–5 of the notes. Consumes $\phi_{\rm nl}(N),\pi_{\rm nl}(N)$
   (and $\rho$, for the density match in prompt 7) directly from
   `InflatonTrajectory`'s existing dense output — no separate lift/utility
   layer needed.
3. `discretized-Lop-and-advection` — build the $N$-dependent scalar
   coefficients multiplying $D,D^{(2)}$ (eq. 12.2) and the advection term;
   Neumann hard-elimination at $y=+1$ (eq. 12.3). Unit-test that the
   $1/r_{\rm out}^2$ prefactor is applied exactly once (see the note under
   "Differentiation matrices" above).
4. `colloc-ode-system` — implement the RHS of eq. 8.1a–b (forward sector
   only, response fields fixed at zero), i.e.\ the "zeroth Picard
   iterate" — should reduce to `FullInstanton`'s RHS when gradient
   coupling is switched off (reduction-limit cross-check).
5. `response-colloc-ode-system` — implement the backward-sector RHS
   (eq. 8.1c–d), with the terminal condition eq. 13.3. Include the
   advection-adjoint unit test flagged above.
6. `picard-iteration-driver` — wire up the outer iteration and the
   $\lambda$ shooting root-find (eq. 13.4).
7. `zeta-profile-extraction` — per-shell noiseless downflow + density
   match (§10, eq. 10.1), reusing `CompactionFunction`'s existing
   Steps-A/B/C machinery rather than re-deriving it, producing $\zeta(y)$.
8. `scale-assignment` — comoving $r(y_j,N_{\rm final})$, areal radius
   $R(r)$ via $\zeta(r)$ (not $\zeta(R)$ — see the note above), and
   physical scale $r_{\rm phys}(y)$ via the single-anchor Leach–Liddle
   ratio (§11, eq. 11.2). Include the scale-assignment equivalence
   cross-check against the discrete scheme (verify its $a,H$ convention
   first, per the cross-check above).
9. `GradientCoupledInstanton-datastore-object` — persistence, FK
   references, following the existing `DatastoreObject` factory pattern.

This sequencing follows the existing single-commit-per-prompt,
acceptance-criteria-checkbox pattern; each should be checked against the
reduction-limit cross-check above before moving to the next. Prompts 1–3
are new relative to the earlier (spectral) sequencing and have no direct
analogue there; prompts 4–7 replace what was previously a 7-prompt
sequence built around mode coefficients; prompt 8 (scale assignment) is
new in this revision.
