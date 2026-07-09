# NUMERICAL_SCHEMES — how `SlowRollInstanton`, `FullInstanton`, `CompactionFunction`, and `GradientCoupledInstanton` work

This document explains the numerical machinery behind the instanton compute
targets, in increasing order of complexity. It assumes the reader has
`.documents/gradient-coupled-instanton/onion_model.tex` available for the full
derivation of the gradient-coupled ("onion") model; this document cites its
section/equation labels (`§4.1`, `eq:Lop-definition`, …) rather than
reproducing the algebra. Physics notation follows the tex: `φ` (field), `π`
(velocity, `dφ/dN`), `N` (e-folds), `H²` (Hubble rate squared), `ε` (slow-roll
parameter), `y` (onion radial coordinate).

All the instanton solvers share one structural idea: they are **saddle-point
(instanton) solutions of a Martin–Siggia–Rose (MSR) action**, obtained by
introducing a "response field" conjugate to each dynamical field and
extremising. The response fields play the role of the noise in the original
stochastic (Langevin) equations, but the saddle-point equations for them are
purely deterministic ODEs/PDEs.

---

## 0. Units and the natural-units convention

Every physics quantity in this codebase is expressed in **natural units**,
`c = ħ = 1`. In natural units mass, energy, inverse length, and inverse time
all carry the same dimension, so every dimensionful quantity in the code has
dimension `(mass)^n` for some integer or half-integer `n` — an energy, a
field value, a rate, all reduce to a power of mass. A second convention is
layered on top for gravity specifically: reduced Planck units, `M_p = 1`
(equivalently `8πG = 1`), so field values, Hubble rates, and potentials are
naturally expressed as numbers times a power of the Planck mass. This is the
"reduced Planck units" convention referenced throughout `CLAUDE.md` and
`.claude/rules/datastore-units.md`.

### `UnitsLike` — one abstract unit system, several concrete realisations

Because "mass" is the only dimension in natural units, a complete unit system
is fixed by picking *one* concrete conversion factor — e.g. how many metres
correspond to one unit of inverse mass. `Units/base.py`'s `UnitsLike` abstract
base class declares this conversion contract as a set of abstract properties
(`Metre`, `Kilogram`, `Second`, `Kelvin`, `PlanckMass`, `eV`, `c`, `Mpc`, …),
each returning "how many of *my* working units correspond to one SI/physical
unit of that quantity". `Units/Planck_units.py`'s `Planck_units` is the one
concrete implementation used throughout this project: it fixes `PlanckMass =
1.0` and derives every other property (`Metre`, `Mpc`, `SolarMass`, `eV`, …)
from the standard SI value of the Planck mass, so that a quantity's numeric
value *in the code* is always "value ÷ (that quantity's natural-unit scale in
the current `UnitsLike` instance)".

A second `UnitsLike` implementation (e.g. one fixing `GeV = 1.0` instead of
`PlanckMass = 1.0`) is a legitimate, drop-in alternative: nothing in the
compute layer hard-codes `Planck_units`' specific numbers — every place a
conversion is needed, code holds a `units: UnitsLike` reference and asks it
for the relevant property. This is what makes the persistence discipline in
`INFRASTRUCTURE.md` §3 possible: the database stores a value in a *named*
unit (e.g. `_PlanckMass`, `_Mpc`), and rehydration multiplies by
`units.PlanckMass` or `units.Mpc` from whichever `UnitsLike` instance the
*current* session is using — the stored number's meaning never depends on
which unit system happened to be active when it was written.

### Dimensionless vs. dimensionful quantities

`CosmologyConcepts/DimensionlessQuantity.py` and
`CosmologyConcepts/DimensionfulQuantity.py` are the two base classes every
persisted scalar physics quantity derives from:

- **Dimensionless** (`delta_Nstar`, `N_init`, `N_final`, `quartic_coupling`,
  the compaction function `C`/`C̄`, e-fold counts, the shooting parameter's
  own bookkeeping): a bare `float`, no unit conversion needed anywhere.
- **Dimensionful** (`phi_value`, `pi_value`, `inflaton_mass`, and — inline,
  not via this class hierarchy, but under the identical convention — φ₁, φ₂,
  P₁, P₂, V, r, M): carries a mass-dimension and must always be paired with a
  `UnitsLike` instance to be meaningful. A dimensionful value is stored
  in code as a plain Python `float`, but that float is *implicitly* "in units
  of `units.PlanckMass^n`" for whatever power `n` its physical dimension
  requires — never a raw SI number. See `.claude/rules/datastore-units.md`'s
  conversion table for the concrete factors (`PlanckMass`, `1/PlanckMass`,
  `PlanckMass⁴`, `Mpc`, `SolarMass`, …) used across the codebase, and
  `INFRASTRUCTURE.md` §3 for how this is enforced at the database boundary.

**Why this matters for the numerics below:** every spline, every ODE state
vector, and every collocation array in this document is implicitly a
"reduced-Planck-units" array. The Picard/shooting loops, the LGL collocation
machinery, and the SBP-SAT closure never touch `UnitsLike` directly — they
operate purely on dimensionless-in-code-units floats — but the moment a
result crosses into or out of the database (or is converted to a physical PBH
mass or comoving Mpc radius for `CompactionFunction`/`GradientCoupledInstanton`'s
scale-assignment step, §3.7 below), a `units` object is required and the
appropriate power of `units.PlanckMass` (or `units.Mpc`, `units.SolarMass`)
must be applied.

---

## 1. `SlowRollInstanton` — the simplest case

Solves the instanton in the slow-roll approximation, where the field velocity
`π` is slaved algebraically to `φ` (`π ≈ -V'/(3H²)`, or the model's own
slow-roll relation) rather than integrated as an independent dynamical
variable. This removes one of the two forward fields and one of the two
response fields relative to `FullInstanton`, leaving a smaller BVP with the
same qualitative shape: a shooting parameter `P1(N_total)` adjusted by an
outer loop so that `φ1(N_total)` hits the target `phi_final`. See
`ComputeTargets_SlowRollInstanton.py` for the full RHS; its structure mirrors
`FullInstanton`'s (Section 2 below) with the reduced field content.

---

## 2. `FullInstanton` — the single-trajectory MSR instanton

### 2.1 The boundary-value problem

`FullInstanton` solves for four functions of `N` over a fixed interval
`[0, N_total]`: the forward fields `φ1(N), φ2(N)` (field and velocity) and
the response fields `P1(N), P2(N)` (conjugate to φ1, φ2 respectively).
Boundary conditions:

```
φ1(0) = phi_init,      φ2(0) = pi_init          (initial data, forward fields)
φ1(N_total) = phi_final                          (shooting target)
P2(N_total) = 0                                  (terminal condition)
```

`phi_final` is fixed, but nothing fixes `P1(N_total)` a priori — it is a free
**shooting parameter** `λ`, adjusted so that the resulting `φ1(N_total)`
matches `phi_final`.

### 2.2 Why Picard iteration, not a direct BVP solve

The forward equations for `(φ1, φ2)` are damped/stable when integrated
**forward** in `N` (the physical direction of the background dynamics). The
response equations for `(P1, P2)` are the *adjoint* of the forward system:
they carry the same physics run in reverse, and their homogeneous solutions
include an **exponentially growing mode when integrated forward** in `N`
(this is why the spline-interpolation catalogue records `P1_sp`, `P2_sp` with
a `sinh` y-transform — they can span many orders of magnitude and either
sign). Integrated **backward** from the terminal condition at `N_total`, that
same mode decays, which is the numerically stable direction for this sector.

So the two sectors cannot be integrated in the same pass: `φ` is stable
forward, `P` is stable backward. The algorithm decouples them via **Picard
(fixed-point) iteration**, nested inside an **outer shooting loop** on the
shooting parameter `λ = P1(N_total)`:

```
1. Background guess: integrate (φ1, φ2) forward with P1 = P2 = 0 (no response
   sourcing yet) — the "zeroth iterate".
2. Backward pass: integrate (P1, P2) backward from N_total to 0, using
   λ = P1(N_total) as the terminal value and the CURRENT forward-pass
   solution (accessed via a SplineWrapper) to evaluate the nonlinear
   coupling terms (∝ V''(φ1), local H², ε).
3. Forward pass: re-integrate (φ1, φ2) forward from 0, now sourced by the
   just-computed response fields via the diffusion matrix D_ij(φ1, φ2).
4. Repeat 2–3 until the forward-field grid stops changing (Picard
   convergence).
5. Outer shooting step: adjust λ using the residual φ1(N_total) − phi_final,
   via `Numerics/ShootingSolver.solve_shooting` (§2.4 below); repeat until
   the residual is within tolerance.
```

This is exactly the adjoint/costate structure familiar from optimal control:
the state equation (forward fields) is integrated forward, the costate
equation (response fields) is integrated backward, and the two are coupled by
outer fixed-point/shooting iteration rather than a single simultaneous solve
— because integrating the costate forward (or the state backward) would hit
the unstable direction of one sector or the other.

### 2.3 MSR action and units

The on-shell action, `S = ∫ D11(φ1,φ2) P1² dN`, is stored as `msr_action`.
Splines: `phi1_sp`, `phi2_sp` use `linear`/`linear` (modest dynamic range);
`P1_sp`, `P2_sp` use `linear`/`sinh` (growing mode, either sign) — see
`.claude/rules/spline-interpolation.md`'s transform catalogue. `msr_action`
itself is dimensionless (it is an action in natural units, ħ=1); φ, π, V,
P are all dimensionful and pass through the `units`-conversion discipline of
§0/`INFRASTRUCTURE.md` §3 whenever they cross the database boundary.

### 2.4 The outer loop: `Numerics/ShootingSolver.py`

The finite-difference-probe outer loop originally used to adjust `λ` was
found to be poorly conditioned once the shooting residual itself is the
output of a nonlinear (Picard) inner solve rather than a smooth closed-form
function — a small probe step `dλ` is dominated by inner-loop noise. Both
`FullInstanton` and `GradientCoupledInstanton` (§3.3 below) now delegate the
outer loop to a single shared, physics-free module, `Numerics/ShootingSolver.py`
(`solve_shooting`):

- A **secant step** between the last two real evaluated `(λ, residual)`
  points — not a finite-difference derivative probe — estimates the local
  slope from genuine solver output.
- The secant step is **trust-region capped** (bounded step size) and
  **Armijo-backtracked**: halve the step until a probe both succeeds and
  strictly reduces `|residual|`, or exhaust a maximum backtrack count and
  take the smallest step tried regardless.
- A **bootstrap** phase handles the very first step, before any secant slope
  is available, optionally aimed directly at an independently-computed seed
  (see §3.3's `FullInstanton`-seeding discussion for `GradientCoupledInstanton`).

`solve_shooting` knows nothing about `φ`/`π`/`λ`'s physical meaning: it only
knows it is rooting a scalar `evaluate(λ) -> (residual, success, aux)`
callback, with `aux` an opaque payload the caller can use to warm-start its
*own* next `evaluate()` call (e.g. carrying forward the current Picard
core-field grids) via `commit(aux)`. Factoring this into one module means
`FullInstanton`'s and `GradientCoupledInstanton`'s outer loops share exactly
the same hardening rather than maintaining two independently-tuned
implementations.

---

## 3. `GradientCoupledInstanton` — the "onion model"

### 3.1 Motivation

`FullInstanton` treats everything outside the current Hubble volume as
already detached and noiseless — a single trajectory. The onion model
relaxes this: it resolves a **mean-field shell structure exterior to the
current horizon**, coupled to the core trajectory through the leading
gradient (Laplacian) term of the stochastic equations (Briaud et al.). The
saddle point of the resulting 2D action — one dimension in `N`, one in a
radial coordinate — gives both a gradient-corrected core trajectory (read off
at the domain's inner edge) and a full density profile `ζ(y)`, replacing the
single ζ value `CompactionFunction` produces from peeling shells off
`FullInstanton`.

### 3.2 The onion coordinate `y`

The domain is the region between a fixed outer comoving radius and the
*current* horizon — genuinely solution-dependent, recomputed at every `N`
from the core's own field values, not anchored once and fixed
(`onion_model.tex` §4.1):

```
r_H(N)   = 1 / [a(N) H(φ(1,N), π(1,N))]        current horizon (inner edge)
r_out    = (1+α) / (aH)_0                       fixed outer edge, eq. 4.1a
Δs(N)    = ln(r_out / r_H(N))                   log-radial domain half-width
y        = -2 ln(r/r_out) / Δs(N) - 1           the onion coordinate, eq. 4.3
```

so `y=-1` is the fixed outer edge `r_out` (Dirichlet: pinned to the
noiseless background trajectory) and `y=+1` is the current horizon — the
**core** (a regularity/Neumann-type condition, not Dirichlet). The domain is
`y ∈ [-1,1]` for every `N`, and there is **no sub-horizon region inside it at
all** — this is what resolves, by construction rather than patch, an earlier
concern about spurious independent noise sourced inside the horizon.

**Why logarithmic, not linear, in `r`:** the gradient-free density profile is
close to a power law in `r`, hence close to linear in `s = ln(r/r_out)`. This
turns the exponentially-compressed near-horizon structure (in linear `r`)
into `O(1)` structure in `y` — the reason there is no structural expectation
that the collocation node count needs to scale with the elapsed number of
e-folds, unlike an earlier spectral-mode design that was retired for exactly
that reason.

**The regularization parameter `α`.** With `α=0`, `Δs(N_init)=0` exactly and
every coefficient built from `1/Δs` (the Laplacian, the advection term, the
noise-dilution factor) diverges there — an artefact of rescaling a
shrinking physical domain onto the fixed range `[-1,1]`, not a genuine
physical divergence (though this has only been checked rigorously for the
forward sector, not the response sector). `α>0` decouples `r_out` from
`r_H(N_init)` by a small controlled amount, giving `Δs(N_init)=ln(1+α)>0` and
regularizing every coefficient identically (an additive shift that becomes
negligible almost immediately, since `Δs(N_final)` typically reaches `~9–21`).
Smaller `α` adds less spurious physical content but makes the coefficients
near `N_init` stiffer — the recommended practice is a convergence/sensitivity
scan over a geometrically-spaced set of small `α`, not a single a priori
choice. `α` is persisted as its own datastore concept,
`alpha_regularization` (`InflationConcepts_alpha_regularization.py`), the
same way `tolerance` and `delta_Nstar` are shared numerical parameters.

**The gradient operator.** The radial Laplacian becomes, in `y`,

```
∇²φ = r_out⁻² L[φ],   L[φ] = e^{Δs} e^{Δs·y} [ (4/Δs²) ∂_y²φ − (2/Δs) ∂_yφ ]
```

(`eq:Lop-definition`) — carrying an explicit first-derivative (drift) term,
and depending on `N` through `Δs(N)` at every point, not just via an overall
`y`-independent prefactor. `L` itself does **not** carry the `1/r_out²`
prefactor; that, together with the local `1/(aH)_loc²` factor, is applied
separately at the point of use as `exp(−2·Δs_loc(y,N))`, the "local-Δs"
identity of the design notes — a place where the codebase has a specific
regression test to confirm the prefactor is applied *exactly once* (it was
briefly doubled during the design phase).

`L` is self-adjoint with respect to the **weighted measure**
`μ(y,N) = exp(−1.5·Δs(N)·y)` (`eq:self-adjoint-measure`), which is, up to
normalization, exactly the physical comoving volume element `r³` in this
coordinate — a consistency check on the Sturm–Liouville reduction, not new
input. A further substitution to a *flat* measure was explored and set aside:
it succeeds algebraically but maps `y∈[-1,1]` onto a badly asymmetric
interval whose width grows like `e^{Δs/2}` (up to `~3×10³` for the widest
profiles computed so far), reintroducing exactly the exponential compression
the log-radial coordinate was adopted to avoid.

**The advection term.** Because the coordinate map itself moves with `N` (at
fixed physical `r`, `y` drifts), there is an extra advective piece,

```
∂/∂N|_r = ∂/∂N|_y − A(y,N) ∂_y,     A(y,N) = (y+1)/Δs(N) · (1−ε_core(N))
```

(`eq:advection-operator`). `A` vanishes at `y=-1` (the fixed outer edge is
undisturbed) and is largest at `y=+1` (the moving horizon).

### 3.3 The response fields, and why Picard iteration reappears

The same MSR construction as `FullInstanton` is applied here, now over the
2D domain `(y,N)`. The instanton equations extremizing the action
(`eq:instanton-eqs`) again split into a **forward sector**
`(φ,π)` — stable integrated forward in `N` — and a **response sector**
`(rfield, rmom)`, conjugate to `(φ,π)`, carrying exactly the same
forward-unstable/backward-stable structure that motivated `FullInstanton`'s
Picard loop (§2.2 above; confirmed directly: the response equations reduce
exactly to `FullInstanton`'s `bwd_rhs` in the 1D limit `A→0`). The response
fields source the forward equations through the diffusion coefficients
`D_φ, D_π, D_φπ` (diluted by a shell-population factor `n_count(y,N)`, since
each `y`-shell represents a different number of coarse-grained Hubble
patches), exactly as `P1, P2` source `FullInstanton`'s forward fields.

So `GradientCoupledInstanton`'s `picard.py` mirrors `FullInstanton`'s
adjoint/Picard/outer-shooting structure as closely as the grid-valued
generalization allows — same overall shape (background pass → Picard inner
loop → outer shooting loop on `λ`, via the same shared `Numerics/ShootingSolver.py`
of §2.4), generalized from scalar arrays over `N` to grid-valued arrays over
`(N, y-node)`. **The key new coupling channel is sector-to-sector
communication across `N`**: because the two sectors are now systems of ODEs
(one per collocation node) rather than single scalar ODEs, each Picard sweep
reconstructs the *other* sector's solution via one `SplineWrapper` per node,
built over a shared dense `N`-grid, rather than holding the whole coupled
system in memory simultaneously.

`picard.py`'s bootstrap logic aims the very first shooting-solver step
directly at an optional, independently-computed `FullInstanton` seed when one
is available (fetched from the datastore by `main.py`'s `_run_gradient_branch`
dispatch, or computed inline, or — failing both — falling back to the
noiseless background's own trajectory). This seed can only ever change how
many Picard/shooting iterations a solve takes to converge, never what it
converges to, which is why it is deliberately excluded from the object's
persisted identity (`INFRASTRUCTURE.md` §10): two rows differing only in
which `FullInstanton` (if any) was available to seed them are the same
physical object.

The terminal condition (`eq:terminal-colloc`) is a Lagrange-multiplier
construction exactly analogous to `FullInstanton`'s `P1(N_total)=λ`, but now
distributed only onto the boundary collocation node: `rfield_j(N_final)=0`
for every interior node, `rfield_{n_max}(N_final) = −λ/(w_{n_max}·μ(1,N_final))`
at the core node, with `w_{n_max}` the known closed-form LGL quadrature
weight. Because LGL nodes include both endpoints by construction, this is an
ordinary finite-dimensional condition — no Gibbs-phenomenon or
distributional subtlety of the kind an earlier spectral-mode design would
have needed to worry about.

### 3.4 The collocation scheme

**y is discretised, N is integrated — a method-of-lines scheme, not a
classical BVP-with-matrix-inversion solve.** The fields are represented by
their values at a fixed grid of `n_collocation_points` Legendre–Gauss–Lobatto
(LGL) nodes `{y_j} ⊂ [-1,1]` (`Numerics/LGLCollocation.py`), generated as the
eigenvalues of a symmetric tridiagonal Jacobi matrix (Golub–Welsch
construction — no closed form exists, unlike Chebyshev's `cos(jπ/n)`).
LGL was chosen over Chebyshev collocation specifically so that a
summation-by-parts (SBP) structure with a diagonal norm matrix is available
(§3.5 below).

Differentiation matrices `D`, `D2` are built **once** from the grid alone —
they don't depend on `Δs(N)` or any physics — and reused at every `N`; the
spatial operator `L` is just `D`, `D2` multiplied by node-dependent scalar
coefficients recomputed at each `N`, the same pattern as every other
solution-dependent coefficient (`H²`, `ε`, `D_ij`) evaluated pointwise
elsewhere in the codebase.

There is **no mode expansion and no lift against the noiseless trajectory
structurally required**: in collocation, the outer Dirichlet condition is
simply the boundary-row assignment `φ_0(N) = φ_nl(N)`, not something a
vanishing-basis construction has to work around (contrast the retired
spectral/sinc design). Tracking the deviation `φ_j − φ_nl` instead of `φ_j`
directly remains an available conditioning choice but is not structurally
required.

Once the `y`-derivatives are replaced by `D`/`D2` matrix products, each of
the resulting per-node ODEs in `N` is marched by `scipy.integrate.solve_ivp`
(`RK45`, adaptive). Concretely, one RHS evaluation (`forward_rhs.py`):

```
1. unpack_state → reconstruct full-length node vectors (Dirichlet pin at
   y=-1; core-node value resolved per §3.5 below)
2. evaluate the coordinate scalars Δs(N), Δs_loc(y_j,N) and the pointwise
   physics coefficients H², ε, V', D_ij at every node
3. apply the spatial operators: one D2@φ + D@φ for L, one D@φ (or the
   split form, §3.5) for advection
4. assemble dφ/dN, dπ/dN per node, pack back to the free-DOF vector
```

The "collocation solve in y" and "ODE solve in N" therefore do not
alternate step by step — the y-discretisation is baked once into the RHS
function, and `solve_ivp` calls that RHS dozens-to-hundreds of times per
e-fold as RK45 chooses its own steps. There is no linear system assembled
and inverted anywhere in the pipeline: the classical conditioning problem of
collocation BVPs (an ill-conditioned matrix `Mx=b`) is traded for **stiffness
of the explicit N-integration** instead — the large eigenvalues of `D2` that
would wreck a linear solve instead set RK45's stability-limited step size.

### 3.5 Boundary treatment: from hard elimination to an SBP-SAT closure

The original design called for **hard elimination** at both boundaries: a
plain Dirichlet row at `y=-1`, and Neumann rows (`∂_yφ=0`, `∂_yπ̃=0`) at
`y=+1` solved by substituting a single dot-product formula for the boundary
node value into the interior rows (`neumann_boundary_value` in
`Numerics/DiscretizedOperators.py`) — cheap, and the natural thing to try
first. This is still exactly what `response_rhs.py` does today: `rmom` is
Neumann-eliminated at the core, `rfield` is free.

**For the forward sector, hard elimination was found to be unstable at
production node counts.** Discretising the advection term as the plain
product `diag(A) @ D` and eliminating `φ_core` by the Neumann formula loses
the discrete mirror of the continuum energy estimate: the semi-discrete
spectrum acquires a spurious growing mode whose real part scales like
`n_max^1.6` — integrator-independent (RK45, Radau, BDF all fail; LSODA
returns NaN silently) — and this is exactly what made
`GradientCoupledInstanton` blow up for `n_collocation_points ≥ 9` before the
fix described below (`.documents/gradient-coupled-instanton/
21-sbp-sat-design-note.md`).

**Root cause.** `A(y) = (y+1)/Δs(N)·(1−ε_core)` is affine in `y`, so `D`
differentiates it exactly, and an exact SBP energy identity
(`H D + Dᵀ H = diag(-1,0,…,0,+1)`, `H = diag(w_j)` the LGL quadrature norm)
shows the plain-product advection operator carries a single, `n`-independent,
non-decaying destabilizing energy term concentrated at the **core node only**
(`y=-1`'s own coefficient is exactly zero, so the outer edge needs no fix at
all). As the grid refines, every other diagonal energy contribution shrinks
with the quadrature weights `w_j`, but this one core-node term does not —
its relative importance grows without bound, reproducing the observed
`n^1.6` abscissa growth.

**The fix — SBP-SAT (summation-by-parts, simultaneous approximation term),
now in production for the forward sector:**

1. **Split-form advection.** Replace the plain product `diag(A) @ D` with the
   skew-symmetric split form
   `A_split = ½(diag(A)@D + D@diag(A) − diag(D@A))`
   (`Numerics.DiscretizedOperators.advection_split_term`) — continuum-identical
   to the plain product for smooth functions, but not identical as a matrix
   (`D` is only exact up to degree `n_max`, so `D@diag(A)` applied to a
   degree-`n_max` grid function picks up an aliasing residual the explicit
   `− diag(D@A)` term corrects for). This restores the discrete energy
   identity up to a single boundary term.
2. **Promote `φ_core` from eliminated to a free, integrated DOF** — hard
   elimination is itself what breaks the discrete energy estimate,
   independent of which field is eliminated, so the state vector grows from
   `2·n_max−1` to `2·n_max`: `(φ_1,…,φ_{n_max}, π_1,…,π_{n_max})`.
3. **Add a dissipative SAT penalty at the core row** for each field,
   `du/dN += −(1/w_{n_max})·τ·(u_core − g)`, with `τ` chosen so the leftover
   boundary energy term cancels exactly (`τ = ½A(core)` from the frozen-
   coefficient linear analysis).

The SAT is a **stabiliser, not new physics**: at the converged solution the
penalty forcing vanishes and the model reduces to the unpenalised dynamics,
provided the target `g` is chosen correctly. Two different kinds of target
are needed, since the two fields' cores have different pre-existing
conditions:

- **`g_φ`** (field, core): the *same* Neumann/regularity value the old strong
  elimination imposed, `neumann_boundary_value(φ_full, D, -1)`, recomputed
  live from the other interior nodes at every RHS call — it is a function of
  the *other* nodes, never of `φ_core` itself, so it can never be
  self-cancelling, and needs no Picard-sweep lagging.
- **`g_π`** (momentum, core): `π_core` previously had **no boundary condition
  at all** — a totally free DOF — so there is no live formula to reuse.
  Instead its target is the **lagged, self-consistent core `π(N)` trajectory
  from the previous Picard sweep** (`g_pi_core_spline`, rebuilt every sweep
  in `picard.solve_picard`), seeded at sweep 0 from an independent
  `FullInstanton` profile (fetched from the datastore when available, else
  computed inline, else falling back to the noiseless background's own
  `π(N)` — seed quality only ever affects iteration count, never the
  converged answer, verified directly by a dedicated regression test).

Two empirical hardenings beyond the frozen-coefficient derivation were
required to make the actual *nonlinear* Picard/shooting iteration converge on
production cases (`.documents/gradient-coupled-instanton/
21a-production-port-notes.md`): production code uses `τ = |A(core)|`
(not `½A(core)`) — the `abs()` keeps the SAT dissipative even when a poor
mid-iteration trial state transiently pushes `ε_core` above 1 (flipping the
sign of the frozen-coefficient `A(core)`), and the doubled magnitude (rather
than the Phase-1 minimum) was needed to suppress a persistent O(1)
Picard-sweep oscillation that appeared once `φ_core` was promoted to a free
DOF with genuine dynamical memory it never had under elimination.

**The response sector (`response_rhs.py`) has deliberately not been ported**
to this closure — it shares the identical destabilizing mechanism in
principle (`rmom_core` is still Neumann-eliminated with the same
`advection_coefficient` formula), and is flagged explicitly in its own module
docstring as a known follow-on rather than a silent gap. It was specifically
ruled out as the cause of the oscillation described above (confirmed by
zeroing its gradient/advection terms and reproducing an identical failure
from the forward sector alone).

### 3.6 ζ(y) extraction: density matching, not a crossing scan

Unlike `FullInstanton`, "end of inflation" is not a single event here —
different `y` reach `φ_end` at different absolute times. Rather than treat
that stopping time as a free boundary (which would curve the integration
domain), the system is integrated over the **full fixed rectangle**
`y∈[-1,1]`, `N∈[N_init,N_final]`, with the single terminal condition of
§3.3, and `ζ(y)` is read off as a **post-processing** step
(`eq:zeta-extraction`, implemented in `ComputeTargets_GradientCoupledInstanton_extraction.py`):

```
for each y_j:
    1. take (φ(y_j,N_final), π(y_j,N_final)) at the shared final time
       (same N for every shell — no per-shell crossing search)
    2. continue THAT shell's own trajectory noiselessly forward to ε=1,
       giving N_end(y_j) and terminal energy density ρ_end(y_j)
    3. density-match against the noiseless background: find N_nl(ρ) such
       that the background itself has density ρ_end(y_j) at N_nl
    4. ζ(y_j) = N_end(y_j) − N_nl(ρ_end(y_j))
```

This is the *same* downflow-then-density-match construction
`CompactionFunction` already uses for the single-trajectory case (its own
Steps A/B), applied per shell rather than once. Density matching (not a
fixed-`N` field-value comparison) is used because surfaces of fixed field
value and fixed energy density differ once `ζ` is `O(1)`, the same
distinction between uniform-density and flat-time slicings familiar from the
standard `δN` formalism.

### 3.7 Scale assignment: three distinct notions of "scale", and the shared `compaction_scalars` core

The single-trajectory pipeline gets away with one comoving radius playing
three different roles at once; the profile case must separate them
(`onion_model.tex` §11, `ComputeTargets_GradientCoupledInstanton_scale_assignment.py`):

1. **Comoving radius** `r(y_j, N_final)` — read directly off the coordinate
   map, eq. 4.3, using the already-solved `Δs(N_final)`. No separate
   calculation.
2. **Areal radius** `R(r) = a·r·e^{ζ(r)}` — the input the standard
   compaction-function formula (Yoo 2022) actually wants:
   `C(r) = (2/3)[1 − (1+r·ζ'(r))²]`. This formula takes `ζ(r)` and `ζ'(r)` —
   *comoving* derivatives — as input, **not** `ζ(R)`; passing the areal
   coordinate here would be a genuine mismatch, not an equivalent
   relabelling. `ζ'(r)` follows by the chain rule from the collocation
   derivative `dζ/dy` (`grid.D @ ζ`) and the analytic
   `dr/dy = -½Δs(N_final)·r(y,N_final)` — no new derivative machinery. `R`
   itself is not an observable; its role is translating the profile into the
   areal-radius language numerical-relativity collapse-threshold
   calibrations (Musco, Escrivá, Young et al.) are phrased in.
3. **Physical (present-day) scale** `r_phys(y)` — the existing Leach–Liddle
   scale-matching machinery, solved **once**, anchored at the fixed outer
   edge `r_out` (since `y=-1` sits exactly on the noiseless background by
   construction), then propagated to every other node by the fixed ratio
   `r_phys(y) = [r(y,N_final)/r_out]·r_phys,out` — no per-shell Leach–Liddle
   solve, and no per-shell inversion of the background expansion history:
   comoving-ness already fixes the today's-scale conversion to a single
   constant common to every mode. (A candidate refinement that would assign
   each shell its own horizon-crossing e-fold by inverting the background
   expansion history was considered and rejected as unnecessary — the single
   global ratio already contains everything that inversion would supply.)

**The averaged compaction function `C̄(y)` and the densified classification
grid (prompt U2a).** `C(y_j)` above is evaluated pointwise at the raw
`n_collocation_points` LGL nodes, but `C̄` — the volume-averaged compaction
function that actually controls PBH formation in the Musco/Escrivá threshold
literature — and the `r_max`/`r_peak` classification derived from it are, as
of prompt U2a, evaluated on a **densified log-r grid** instead of the raw
node set: `assign_scales` re-sorts `(r_phys, ζ)` ascending, builds a
log-uniform dense grid of ~10× the node count via
`compaction_scalars.densify_zeta_profile` (a `SplineWrapper` fit in log-r
space, evaluated on `np.geomspace`), integrates the `C̄` cumulative integral
on that dense grid via `compaction_scalars.compute_C_bar` (trapezoid, then
interpolated back to the original sample points), and classifies
`r_max`/`r_peak` on the dense grid via `compaction_scalars.classify_radii`.
This deliberately matches `CompactionFunction`'s own fidelity (§ below) and
removes a node-count-dependence artefact `r_max`/`r_peak` previously had when
classified directly on the coarse `n_collocation_points` set — a handful of
LGL nodes is not enough points to resolve a compaction-function peak
reliably, whereas the underlying `ζ(y)` profile itself, from which the dense
grid is built, is already fully resolved by the collocation solve.

**`ComputeTargets/compaction_scalars.py` — one shared numerical core for two
different schemes (prompt U1).** The dense-grid `C̄` integration, the
`r_max`/`r_peak` classification, the `C_min`/`compensated`/`type_II`
minimum-classification, and the PBH-mass formula were originally implemented
inline inside `CompactionFunction`'s own Step D/E/F block. They are now
factored into `ComputeTargets/compaction_scalars.py` as five standalone,
physics-free numpy/scipy functions (`densify_zeta_profile`, `compute_C_bar`,
`classify_radii`, `classify_C_min`, `pbh_mass`) that both `CompactionFunction`
and `GradientCoupledInstanton/scale_assignment.py` call directly — a pure
refactor, verified bit-for-bit identical against the pre-refactor inlined
code (`tests/test_compaction_scalars_refactor_golden.py`). This makes the
"two different numerical schemes for the same underlying mean-field action"
relationship described below tighter than "the same formulas, reimplemented
twice": the scalar-summary arithmetic downstream of `ζ(r)`/`C(r)` is now
*literally* the same code for both schemes, so they cannot silently drift
apart.

**The CompactionFunction-parity scalar set (prompts U2b/U3).** Every
`GradientCoupledInstanton` row now computes and persists the same eleven
summary scalars `CompactionFunction` itself exposes — `C_peak` (`nanmax(C)`),
`C_bar_peak` (`nanmax(C̄)`), `C_min`/`compensated`/`type_II`
(`compaction_scalars.classify_C_min`), `r_max`, `r_peak`, `M_max`, `M_peak`
(via `compaction_scalars.pbh_mass`, gated on `C_max ≥ C_threshold`), and
`V_end_downflow`/`N_end_downflow` (the per-shell downflow values, §3.6, at
the raw-grid node of maximum `C` — a deliberate choice of the un-densified
node array, matching the `C_max`-based mass classification rather than an
index into the densified grid, which has no single corresponding node). This
gives `GradientCoupledInstanton` rows the same at-a-glance summary
`CompactionFunction` rows have, computed via the identical
`compaction_scalars` helpers, and rehydrated unconditionally in `build()` —
available even on the cheap `_do_not_populate=True` fetch tier, exactly like
`msr_action` (`INFRASTRUCTURE.md` §7).

**Relation to `FullInstanton` + `CompactionFunction`'s discrete scheme.**
`CompactionFunction` builds its profile by *peeling shells* off a single
`FullInstanton` trajectory: shell `i` detaches at integration step `i`, with
comoving outer radius `r_i = 1/[a(i)H(i)]` fixed for all time once the shell
forms (§ "Comoving shell geometry" in the tex) — a genuinely different
numerical scheme (finite-difference on a discrete, non-uniformly-spaced shell
grid) for the *same* underlying mean-field action, not a different physical
model. The two are expected to agree at the core: applying the
`r_phys(y)` ratio at `y=+1` gives `r_phys,core = r_phys,H(N_final)` directly,
since `r(1,N) ≡ r_H(N)` by definition of the coordinate's inner edge, and the
discrete scheme's innermost shell uses the *same* defining formula — the same
geometric object, playing the same role, so the two schemes assign the core
the same physical scale by construction (exactly as `α→0`, with `O(α)`
corrections at finite `α`). This equivalence assumes the discrete/peeling
code's own `r_i = 1/[a(i)H(i)]` uses the instanton's own local trajectory
(matching how `r_H(N)` is defined here) rather than the noiseless background —
flagged in the tex as unverified against the actual `CompactionFunction`
implementation; check this before relying on the equivalence in a specific
downstream calculation. The parity scalar set above (prompts U2b/U3) gives a
direct, per-grid-point way to check this equivalence numerically —
`tests/test_gci_parity_scalars.py` cross-checks the two schemes' scalars at a
matching `(trajectory, N_init, N_final, delta_Nstar)` grid point.

### 3.8 Open issues (do not present as settled)

Two theoretical questions remain open per `onion_model.tex` §14 and are not
resolved by the numerical scheme above: (1) how to compare the 2D onion
action's magnitude to the existing 1D `FullInstanton` action's probability
interpretation, given that outer shells genuinely participate in the
compaction-function calculation rather than being a for-free addendum — do
not report a "corrected PBH formation probability" from this pipeline until
this is resolved; (2) the heuristic justification for the terminal boundary
condition (response fields killed by homogeneous post-transition equations)
has not been rigorously established for the stochastic path-integral case.
