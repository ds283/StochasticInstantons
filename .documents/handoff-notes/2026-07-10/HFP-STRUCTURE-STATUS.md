# `H_FP` structure: findings and triage input

**Status:** derivation-level findings from a chat session; none implemented, none
tested numerically. Everything below is analytic and should be treated as a
hypothesis set to be checked, not as established repo state.

> **Status (8 October 2026): partly superseded** by the 11–20 July analysis in
> `../2026-10-08/RECONSTRUCTION.md` (Parts B and C). The text below is unchanged;
> these points override it:
>
> - **§1 stands**, but lacks the response-sector characteristic analysis of
>   16 July (R B.1): the response sector has the same principal symbol, one
>   incoming characteristic at the core in backward time, and needs no data;
>   prompt 23's negative was a strong-versus-weak mismatch. The natural
>   condition is `∂_y(g π̃) = 0` (R Erratum E3). Tex `sec:no-data`.
> - **§2(a)–(c) stand**; under the core anchor there is exactly one incoming
>   characteristic for `0 < ε_core < 2` (tex `sec:characteristics`).
>   **§2(d) is reversed** (11 July, R B.3): no data enters at the core;
>   Neumann is the reflecting, data-free closure; the `π_core` penalty cancels
>   a physical piston flux and is a flat-norm artefact. The target closure is
>   one penalty on the incoming invariant `w_in` in the `H_μ` norm (R B.9,
>   Erratum E2).
> - **§3 stands**, sharpened by the FullInstanton closed form
>   `H_FP = λ φ₂(N_total) + D₁₁ λ²` (R B.10; tex `sec:hfp`).
> - **§4 stands** and is now quantified: the dropped terms are leading order,
>   a sign flip for the quadratic potential (R B.10; tex
>   `sec:fullinstanton-eqs`).
> - **"Suggested ordering"** ("instrument `H_FP` first") was demoted on
>   10 July. The current plan is in `.prompts/INDEX.md`, "Planned".

**Scope:** the MSR action of `onion_model.tex` (eq. `msr-action`) admits a
Fokker–Planck Hamiltonian `H_FP`. Examining it turns up four things, of which
one is a genuine bug-class finding (#1), one is a physics-interpretation
correction (#2), one is a free numerical test (#3), and one is a known
truncation whose consequences are worse than the tex admits (#4).

See `HFP-CALCULATION.md` for the derivation itself, in enough detail to write
up in `onion_model.tex`.

---

## 1. The forward and response discretizations are no longer adjoint

**Finding.** `forward_rhs.py` closes the core (`y=+1`) boundary weakly, with
split-form advection plus an SAT penalty (prompts 21/21a). `response_rhs.py`
still closes it *strongly*, by hard Neumann elimination of `rmom` via
`neumann_boundary_value(rmom_full, grid.D, boundary_index=-1)`. Prompt 23 Part A
recorded a naive same-recipe SAT port to the response sector as a clean
negative.

**Why this matters.** `onion_model.tex`'s own self-adjointness panel (the panel
following eq. `msr-action`) shows that `∂_y φ = 0` at `y=+1` and
`∂_y rmom = 0` at `y=+1` are an **adjoint pair**: together they kill the
boundary term `[ϖ (P Q' − Q P')]` that self-adjointness of `L` requires to
vanish. You cannot weaken one and leave the other strong. Doing so means the
discrete response operator is not the transpose of the discrete forward
operator, so:

- the Picard fixed point is not the stationary point of *any* discrete action;
- the computed `msr_action` is not stationary with respect to the quantities
  actually being solved for;
- there is no discrete conserved/balanced quantity to appeal to.

This is textbook discretize-then-optimize inconsistency (the "discrete adjoint"
problem in PDE-constrained optimization). Prompt 23's clean negative is what
that inconsistency looks like when you try to patch it by analogy instead of by
transposition.

**What the fix is.** Not "the same SAT recipe with a sign flip". If the forward
spatial operator after closure is

```
M_SAT = M - (tau / w_core) * e_core @ e_core.T
```

then the response sector must carry `-M_SAT.T`. Since `e_core @ e_core.T` is
symmetric, the transpose reinstates *the same diagonal penalty on the core
response row* (dissipative in backward `N`), and the strong Neumann elimination
of `rmom` must be dropped. The affine part of the SAT (the `+ (tau/w_core) * g`
source) has zero state-derivative and so does not appear in the transposed
operator.

Equivalently, and more usefully for the write-up: the SAT has a clean
variational statement. Adding

```
tau * [ rfield * (phi - g_phi) + rmom * (pi - g_pi) ]  evaluated at y = +1
```

as a boundary term in `S` reproduces the forward SAT on variation with respect
to `(rfield, rmom)`, and *generates the transposed response penalty* on
variation with respect to `(phi, pi)`. That is the correct derivation route.

**Triage priority.** Highest. This is implementable inside the current
Chernykh–Stepanov / Picard architecture, requires no change to the physics, and
is a plausible mechanism for a stubborn convergence floor: a non-adjoint pair
has no saddle to converge to. It should be considered alongside — not instead
of — the frozen `g_pi_core` / live-Neumann-target diagnosis already on the
board, since both concern the same node.

---

## 2. Characteristic analysis of the core boundary

At `y=+1` the local `Delta_s_loc` equals the global `Delta_s` **exactly** (tex,
Section `sec:gradient-operator` consistency check). Therefore the coefficient of
`∂_y² phi` in the `pi` equation is

```
c^2 = exp(-2 Delta_s) * exp(Delta_s (1+y)) * 4/Delta_s^2  |_{y=1}  =  4/Delta_s^2
c   = 2 / Delta_s          (exact, no approximation)
```

and the advection coefficient there is `A(1) = 2 (1 - eps_core) / Delta_s`.
Hence, exactly:

```
A(1) / c = 1 - eps_core
```

The gradient term makes the forward sector a **damped wave equation**, not a
diffusion equation. Its characteristics at the core are

```
dy/dN = -A ± c = (2/Delta_s) * { eps_core , eps_core - 2 }
```

### Consequences

**(a) One incoming characteristic; one boundary condition.** For
`0 < eps_core < 2` the core is a *subsonic inflow* boundary: one characteristic
enters (speed `(2/Delta_s)(eps_core - 2) < 0`), one leaves (speed
`(2/Delta_s) eps_core > 0`). The BC *count* in the tex is therefore correct.
(Cross-check at the outer edge: `A(-1) = 0`, one in and one out, one condition
needed. The tex imposes both `phi(-1)=phi_nl` and `pi(-1)=pi_nl`; but with
`A(-1)=0` and `rfield=rmom=0` there, eq. `inst-phi` gives `phi_dot(-1) = pi(-1)`
identically, so the second is an identity, not an independent condition. Worth
stating in the tex.)

**(b) The boundary is nearly characteristic in slow roll.** The outgoing speed
is `2 eps_core / Delta_s`. With `eps_core ~ 1e-2`, information essentially
cannot leave the domain through `y=+1`. This is a quantitative explanation of
why the core closure is so delicate: why the energy method finds an `O(1)`
defect concentrated on that node, why hard elimination destabilized, and why the
SAT margin was tight enough that `tau` had to be doubled to `|A_core|`.

**(c) Neumann is a *reflecting* condition, not a data-supplying one.** In
Riemann variables `w_± = pi ± c ∂_y phi`, the core flux is

```
(mu/4) [ (c + A) w_+^2 + (A - c) w_-^2 ]
```

`∂_y phi = 0` sets `w_+ = w_-`, collapsing this to `(1/2) mu A(1) pi_core^2 > 0`.
Reflection specifies the incoming invariant only in terms of the outgoing one:
it supplies **no data**. The continuum problem remains well-posed (bounded
growth at rate `A` — the piston work of a boundary sweeping into the shrinking
horizon) but it is *not* energy-decaying at the core, and `pi_core` is
genuinely underdetermined by data.

**(d) Therefore `g_pi` is a model closure, not a stabiliser.**

> **Reversed 11 July 2026** (R B.3): no data enters at the core. See the status
> note at the top.
 This is the
substantive correction to `21-sbp-sat-design-note.md` §6 and to
`forward_rhs.py`'s module docstring, both of which assert "the SAT is a
stabiliser, not new physics: at the converged solution the penalty forcing → 0".
That claim is false, and the code's own history proves it: a self-consistent
lagged `g_pi = pi_core` makes the penalty vanish identically (the design note's
own constraint (a) — a no-op), which is exactly why prompt 22c had to replace it
with a **fixed** `FullInstanton`-derived target. A fixed `g_pi` is a weak
imposition of the incoming characteristic's data. It is the assertion that the
excised sub-horizon interior looks like the homogeneous instanton core.

That is a defensible — arguably the *right* — physical closure. It should be
stated as such in `onion_model.tex` §`sec:bcs`, alongside `∂_y phi = 0`, rather
than buried in a numerics design note as a stabilisation choice. The SAT is then
doing exactly two things, only the first of which is "not new physics":

1. making the *discrete* core flux equal the *continuum* core flux (numerics);
2. supplying data for the incoming characteristic (physics).

**(e) The `eps_core` thresholds are real, not numerical.** `A(1)` changes sign at
`eps_core = 1`; the characteristic *count* changes at `eps_core = 2`, above which
both characteristics are outgoing and the Neumann condition **over-determines**
the problem. `forward_rhs.py`'s observed "`tau = 0.5*A_core` flips negative and
becomes an amplifier once `eps_core = 0.5*pi_core^2` exceeds 1" is the discrete
shadow of a change in the character of the continuum boundary. The current
`tau = abs(A_core)` masks it. Note `eps_core -> 1` is approached near `N_final`
by construction (the shooting condition drives `phi(1,N_final) -> phi_end`), so
this is not an exotic corner.

**Triage priority.** High for the tex; medium for code. It reclassifies an
existing choice rather than demanding new machinery, but it changes what the
`n`-convergence and `alpha`-sensitivity results *mean*.

---

## 3. `H_FP = -∂S/∂δN★` as an independent numerical consistency test

**In the 1D limit (`FullInstanton`) `H_FP` is exactly conserved** — the system is
autonomous (every trace of `a(N)` drops out) and there are no spatial
boundaries. Explicitly, with `FullInstanton`'s conventions (`D_phi = 2*D11`):

```
H_FP = P1 * pi
     + P2 * ( -(3 - eps) * pi - dV_dphi(phi) / Hsq )
     + ( D11 * P1**2 + 2 * D12 * P1 * P2 + D22 * P2**2 )
```

Legendre check: `P1*phi_dot + P2*pi_dot - H_FP = D11*P1**2`, which is exactly
`FullInstanton`'s `msr_action` integrand. Instrumenting this is ~10 lines.

**In the onion `H_FP` is NOT conserved**, for two independent structural reasons
(see `HFP-CALCULATION.md`): explicit `N`-dependence through `a(N)` (in
`Delta_s`, `Delta_s_loc`, and `n_count`, hence `D_phi`), and a nonvanishing
boundary flux at *both* ends (a driven Dirichlet boundary at `y=-1` where
`phi_nl(N)` moves; a moving/piston boundary at `y=+1` where `A(1) != 0`). No
choice of boundary condition removes either. This is physical, not a defect.

**The test.** By Maupertuis / the envelope theorem, for a fixed-endpoint,
fixed-duration problem with conserved `H`, `∂S/∂T = -H`. In the
`(N_final, ΔN, δN★)` parameterization, varying `δN★` at fixed `(N_final, ΔN)`
holds **both endpoints fixed** — `phi_init = phi_nl(N_init)` with
`N_init = N_final - ΔN`, and `phi_end` — and varies only the duration
`N_total = ΔN + δN★`. Therefore

```
H_FP  =  - ∂S_MSR / ∂δN★   |_{N_final, ΔN}        (FullInstanton, 1D)
```

Since `S` increases with `δN★` (a longer delay is a rarer event), `H_FP < 0`.
The existing `S(δN★)` grids already contain the right-hand side.

**Why it is a strong test.** It is over-determined, not fitted. Compute `H_FP`
directly along the trajectory: it should be (i) constant in `N`, and (ii) equal
to `-∂S/∂δN★`. The *same* quantity — the variational truncation `R` of §4 below
— controls the failure of both (i) and (ii). A consistent pair of deviations
calibrates `R`; an inconsistent pair indicates a separate bug.

**Triage priority.** Do this first. It is cheap, it uses code and grids that
already exist, and it calibrates the size of the §4 truncation before any effort
is spent on §1 or on the onion.

---

## 4. The dropped variational terms

`onion_model.tex`'s "What is *not* corrected here" panel drops
`∂H²/∂phi`, `∂eps/∂phi`, `∂D_ij/∂phi`, `∂A/∂phi` when varying to obtain the
response equations; `FullInstanton.bwd_rhs` does the same (only the `V''` term
appears). The panel justifies this as "a higher-order effect in the same sense as
other terms already truncated in the gradient expansion".

**The consequence is understated.** With the truncation, the coded response
equations are **not** `-δH/δphi` of any functional. Write the coded RHS as
`-δH/δphi + R_phi`. Then:

- there is no exactly conserved `H_FP`, even in the autonomous 1D limit — the
  drift rate is `<phi_dot * R_phi + pi_dot * R_pi>_mu`;
- more seriously, **the trajectory does not extremize `S`**. The usual
  first-order error cancellation for on-shell actions therefore fails, and
  `S_MSR` carries an error *linear* in the truncation, not quadratic. Every
  `S_MSR` number in the project inherits this.

**The fix is cheap.** In reduced Planck units `eps = pi²/2` and
`H² = V/(3 - pi²/2)`, and `D_ij ∝ H²`, so all the missing derivatives are
closed-form. `AbstractPotential` already exposes `dV_dphi`, `d2V_dphi2`,
`H_sq`, `epsilon`. Restoring them buys a genuine invariant *and* a genuinely
stationary action.

**Triage priority.** Second, after §3 has measured how big `R` actually is.
Restoring the terms is a prerequisite for §1 being meaningful: transposing a
discretization of the *wrong* continuum equations gains nothing.

---

## Suggested ordering

1. **Instrument `H_FP` in `FullInstanton`.** Check constancy in `N`; check
   against `-∂S/∂δN★` from existing grids. Cheap; calibrates `R`. (§3)
2. **Restore the dropped variational terms** in `FullInstanton` and the onion.
   Re-run (1); `H_FP` should now be constant to integrator tolerance. (§4)
3. **Transpose the SAT-closed forward operator into the response sector**,
   replacing the strong Neumann elimination of `rmom`. Derive it from the
   boundary term added to `S`, not by analogy. (§1)
4. **Restate `g_pi` in `onion_model.tex`** as a model closure at `y=+1`
   (incoming characteristic carries the homogeneous instanton core), and add the
   characteristic analysis. Note the `eps_core = 1` and `eps_core = 2` thresholds
   explicitly. (§2)
5. **Instrument the onion balance law** (`HFP-CALCULATION.md` §5) as a residual
   diagnostic. It should sit at truncation level. When it does not, it says
   *which* of the three terms — explicit `N`-dependence, boundary flux,
   truncation `R` — is responsible.

## Relation to work already inflight

- The **frozen `g_pi_core` / live-Neumann-target** diagnosis (Diagnostics 1–13)
  and §2(d) here concern the same node and are compatible, but they point in
  different directions and must be reconciled before either is implemented. The
  diagnostic campaign concluded the penalty must *vanish* at convergence for
  `tau` to be a pure stabiliser, and proposed a live Neumann regularity target.
  §2(d) argues the penalty **should not** vanish, because it is supplying the
  incoming characteristic's data. Both cannot be right. Note that a live Neumann
  target on `phi` and a data-supplying fixed target on `pi` are not in conflict
  — the two fields have different roles at the boundary (`phi` has the Neumann
  condition; `pi` has none). The reconciliation probably runs: `g_phi` live
  Neumann (a true stabiliser, penalty → 0, `tau/w_core ~ n²` floor removed);
  `g_pi` fixed model closure (penalty finite at convergence *by design*, with
  `tau` then genuinely required to be a physical rate, not a free parameter).
  **This is the single most important thing to settle.**
- The `tau/w_core ~ n²` mechanism (`w_core ~ 1/n²` for LGL) is unaffected by
  anything here and remains the mechanistic explanation of the `n>=9` floor for
  whichever field's penalty fails to vanish.
- The **largest-time boundary condition** open issue (tex §`sec:open-issues`) and
  the nonzero `H_FP` of §3 are two views of the same structural fact: the noise
  is constrained to `[N_init, N_final]`, the response fields jump discontinuously
  at `N_init`, and `H_FP` is the shadow price of that constraint. `H_FP = 0` is
  not a constraint being missed; it is the condition that *would determine*
  `δN★` if the duration were free.
- The **MAM/gMAM vs Chernykh–Stepanov** trade (Grafke & Vanden-Eijnden,
  `1812_00681v1.pdf`) is worth recording but is not an action item.
  Discretizing `S` directly and varying (Marsden–West discrete mechanics) would
  subsume both the SBP closure and any symplectic-conservation concern — SBP *is*
  discrete integration by parts, `HD + D^T H = B` is exactly the LGL quadrature's
  version of it — and would give discrete adjoint consistency for free. But
  Grafke notes MAM-type methods struggle with **degenerate forcing**, and
  `MasslessDecoupledDiffusion` has `D12 = D22 = 0`, maximally degenerate. That is
  a real argument for staying with Picard. It is *not* an argument against fixing
  discrete adjoint consistency inside the current architecture.

## What SBP is and is not

SBP-SAT is a property of the **spatial** semi-discretization: discrete
integration by parts, so that the discrete energy estimate mimics the continuum
one and boundary terms appear only where the continuum puts them. Symplecticity
is a property of the **temporal** map. They are not substitutes, and SBP does not
protect any invariant from drifting in `N`.

Nor is symplectic integration the right thing to want here. It earns its keep on
initial value problems over long times, where non-symplectic schemes drift
secularly. This is a two-point BVP: the converged discrete solution satisfies the
discrete equations globally, and the relevant error is the accuracy of discrete
stationarity, not secular drift. (Within a Picard sweep the forward and backward
passes *are* IVPs integrated with RK45/Radau, so per-sweep drift is real — but
the sweep is not the answer.) And in any case, per §4, there is currently no
exact invariant to preserve.

The correct object to want is not `dH_FP/dN = 0` but the **balance law** of
`HFP-CALCULATION.md` §5, holding to truncation error.
