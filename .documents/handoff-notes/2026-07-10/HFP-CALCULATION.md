# Derivation of the Fokker–Planck Hamiltonian `H_FP` for the onion model

**Purpose.** Enough detail for another agent to write this up as a new section of
`onion_model.tex` (suggested placement: immediately after
`sec:instanton-eqs`, before `sec:bcs`, since the boundary-condition discussion
depends on it). Notation follows the tex's macro set:
`\field` = φ, `\mom` = π, `\rfield` = φ̃, `\rmom` = π̃, `\measure` = μ,
`\advcoef` = A, `\Lop` = L, `\Deltas` = Δs, `\Ny` = N.

Nothing here is new physics. It is a rewriting of eq. `msr-action` in
Hamiltonian form, plus the consequences.

---

## 1. Reading the MSR action as `p q̇ - H`

Write `<·>_μ ≡ ∫_{-1}^{1} μ(y,N) dy (·)`. Group eq. `msr-action` by whether a
term multiplies an N-derivative:

```
S = ∫_{N_init}^{N_final} dN [ < rfield * phi_dot + rmom * pi_dot >_mu  -  H_FP ]
```

with everything else absorbed into `H_FP`. Reading off directly from
eq. `msr-action`:

```
H_FP[phi, pi, rfield, rmom; N]
  = < rfield * b_phi
    + rmom   * b_pi
    + (1/2) * D_phi   * rfield^2
    +         D_phipi * rfield * rmom
    + (1/2) * D_pi    * rmom^2 >_mu
```

where `b_phi`, `b_pi` are the **noiseless drift** terms of the Langevin system,
eq. `langevin-y`, i.e. eq. `inst-phi`/`inst-pi` stripped of their `D`-sourcing:

```
b_phi = pi + A * d_y phi
b_pi  = -(3 - eps_1) * pi  -  V'(phi)/H^2  +  exp(-2 Delta_s_loc) * L phi  +  A * d_y pi
```

Note the sign bookkeeping: in `msr-action` the `rmom` bracket carries
`+(3-eps)pi + V'/H^2 - exp(-2Δs_loc) L phi - A d_y pi`, i.e. `-b_pi`, and it
enters `S` with a `+`; and the quadratic `D` terms enter `S` with a `-`. Both
flip on passing to `-H_FP`. The result is the standard Freidlin–Wentzell /
large-deviation Hamiltonian

```
H(phi, theta) = <theta, b(phi)> + (1/2) <theta, a theta>
```

with `theta = (rfield, rmom)` and `a = D_ij`. Cite Grafke & Vanden-Eijnden
(`1812_00681v1.pdf`), eq. (16)–(19), for the identification and for the fact
that in the standard setting `H` is conserved along the minimizer.

---

## 2. The canonical pair is `(phi, mu * rfield)`, not `(phi, rfield)`

This is the one subtlety worth a `\begin{panel}` in the tex, because it is
exactly what produces the otherwise-mysterious `-mu_dot/mu` term in
eq. `inst-rphi`/`inst-rpi`.

The symplectic form is `∫ dy (mu * rfield) delta(phi)`, so the momentum density
conjugate to `phi` **with respect to the flat measure `dy`** is

```
p_phi = mu * rfield          p_pi = mu * rmom
```

Rewrite `H_FP` as a functional of `(phi, pi, p_phi, p_pi; N)` over flat `dy`.
The drift terms are linear in `theta`, so `mu` cancels there; the quadratic
terms pick up `1/mu`:

```
H_FP = ∫ dy [ p_phi * b_phi + p_pi * b_pi
              + (1/(2 mu)) * ( D_phi * p_phi^2 + 2 D_phipi * p_phi * p_pi + D_pi * p_pi^2 ) ]
```

### Verification that this generates eq. `instanton-eqs`

**Forward.**
```
dH/dp_phi = b_phi + (1/mu)(D_phi p_phi + D_phipi p_pi)
          = pi + A d_y phi + D_phi rfield + D_phipi rmom
```
which is eq. `inst-phi`. Likewise `dH/dp_pi` gives eq. `inst-pi`. Exact, no
truncation.

**Backward.** `p_phi_dot = -delta H / delta phi`. Term by term:

- `∫ p_phi A d_y phi` contributes `-d_y(A p_phi)` — note the sign, from one
  integration by parts in `y`;
- `∫ p_pi * (-V'/H^2)` contributes `- p_pi V''(phi)/H^2` (freezing `H^2`);
- `∫ p_pi * exp(-2 Δs_loc) L phi` contributes, by self-adjointness of `L` with
  respect to `mu dy`, `- mu * exp(-2 Δs_loc) * L rmom` (freezing the prefactor).

So
```
p_phi_dot = d_y(A p_phi) + p_pi V''/H^2 - mu exp(-2 Δs_loc) L rmom
```
Substitute `p_phi = mu rfield`, expand `p_phi_dot = mu_dot rfield + mu rfield_dot`,
divide through by `mu`:

```
rfield_dot = -(mu_dot/mu) rfield + (1/mu) d_y( mu A rfield )
             + (V''/H^2) rmom - exp(-2 Δs_loc) L rmom
```

which is **exactly** the tex's unsimplified response equation (the displayed
equation immediately preceding the `\begin{calculation}` block's "Expanding the
adjoint term" step). The subsequent scalar simplification
`(1 - eps_core)(1/Δs - 3/2)` then goes through unchanged. Same for `rmom`.

This is a clean independent confirmation of the corrected signs recorded in the
tex, obtained by a completely different route (Hamiltonian structure rather than
direct variation), and is worth saying so.

---

## 3. Two cheap evaluation forms

**Form A (drift + diffusion).** Straight from §1. Every ingredient is already
computed inside `forward_rhs.py`.

**Form B (Legendre).** Since `S = ∫ dN [ <rfield phi_dot + rmom pi_dot>_mu - H_FP ]`,
and the on-shell Lagrangian density is (substituting eq. `inst-phi`/`inst-pi`
into eq. `msr-action`) exactly the quadratic form that `msr_action.py` already
integrates:

```
H_FP(N) = < rfield * phi_dot + rmom * pi_dot >_mu
        - < (1/2) D_phi rfield^2 + D_phipi rfield rmom + (1/2) D_pi rmom^2 >_mu
```

The second bracket is `msr_action.py`'s integrand verbatim. The first needs only
the RHS arrays. Both forms must agree; their agreement is itself a check on the
solution being on-shell.

**1D reduction, for the tex's `FullInstanton` cross-check panel.** With
`A = 0`, `L = 0`, `mu = 1`, and `FullInstanton`'s `D_phi = 2 D11` convention:

```
H_FP = P1 * pi + P2 * ( -(3-eps) pi - V'(phi)/Hsq )
       + D11 P1^2 + 2 D12 P1 P2 + D22 P2^2
```

Legendre check: `P1 phi_dot + P2 pi_dot - H_FP = D11 P1^2`, which is exactly
`S = ∫ D11 P1^2 dN` as recorded in `NUMERICAL_SCHEMES.md` §2.3. Include this
check in the write-up; it fixes every sign at once.

---

## 4. Why `H_FP` is *not* conserved for the onion

Three independent obstructions. Each deserves a sentence in the tex; together
they correct a natural but wrong expectation.

### (a) Explicit `N`-dependence

`H_FP` is not autonomous. `mu`, `A`, `L` all depend on `Delta_s(N) =
ln(r_out a(N) H_core)`; `exp(-2 Delta_s_loc)` and `n_count(y,N)` — hence
`D_phi = 2 D11 / n_count` — depend on `a(N)`.

Holding the *fields* fixed, `Delta_s`'s explicit derivative is
`∂Delta_s/∂N|_expl = d ln a / dN = 1`, and the field-dependent remainder
reproduces the total `dDelta_s/dN = 1 - eps_core` of eq. `Deltas-derivative`.
Same for `Delta_s_loc`. So `∂H_FP/∂N|_expl != 0` structurally: **the expansion
is an explicit clock.** In the 1D limit every trace of `a(N)` drops out and the
system *is* autonomous.

### (b) Boundary flux

For a field Hamiltonian, the bulk cancellation in `dH/dN` leaves the same
bilinear boundary form that the variational derivation had to discard, evaluated
with `delta(phi) -> phi_dot` etc.:

```
Phi = [  mu * A * ( rfield * phi_dot + rmom * pi_dot )
       + C * varpi * kappa * ( rmom * d_y phi_dot  -  phi_dot * d_y rmom ) ]  from y=-1 to y=+1
```

with `varpi(y) = exp(-Delta_s y / 2)` (the tex's `\weightfn`),
`kappa = exp(-2 Delta_s_loc)`, and `C` the y-independent constant
`r_out^{-2} exp(Delta_s) * 4/Delta_s^2` factored out of `L`.

Derivation sketch for the second piece: the contribution of the `L`-term to
`dH_FP/dN` is `< rmom_dot * kappa * L phi + rmom * kappa * L phi_dot >_mu`. Move
`L` off `phi_dot` by the same integration by parts used in the tex's
self-adjointness panel; the bulk remainder cancels against the response
equation's own contribution, leaving the bracketed boundary term. The first
piece comes identically from `∫ A p_phi d_y phi_dot = [A p_phi phi_dot] - ∫ d_y(A p_phi) phi_dot`.

Evaluate:

- **`y = +1`.** The gradient piece vanishes: `d_y phi = 0` for all `N` implies
  `d_y phi_dot = 0`, and `d_y rmom = 0` by eq. `bc-core`. **This is precisely
  what the Neumann pair buys, and it is the same pair the self-adjointness panel
  needs — the two facts are one fact.** But the advective piece survives:
  `A(1) = 2(1-eps_core)/Delta_s != 0`, `phi_dot(1) != 0`, `rfield(1) != 0`
  (it is where the lambda source lives).
- **`y = -1`.** `A(-1) = 0` kills the advective piece. `rmom(-1) = 0` kills the
  first gradient term. The second, `- C varpi kappa * phi_dot_nl * d_y rmom(-1)`,
  **survives**, because the Dirichlet datum `phi_nl(N)` is time-dependent and
  `d_y rmom(-1)` is unconstrained.

Interpretation, worth stating plainly: the outer edge is a **driven** boundary —
the pinned noiseless shell does work on the system; the core is a **moving**
boundary — a piston sweeping into the shrinking horizon. Both fluxes are physical
and unavoidable. No choice of boundary condition removes either. (`Phi = 0` at
`y=+1` would require `A(1) = 0`, i.e. `eps_core = 1`, which holds only at the
terminal time.)

### (c) The variational truncation

Per the tex's "What is *not* corrected here" panel, `eps_1`, `H^2`, `D_ij`, `A`,
`Delta_s_loc` are **frozen** when varying with respect to `phi`, `pi`. Hence the
coded response equations are `-delta H/delta phi + R_phi` for a nonzero residual
`R`. Explicitly, `R_phi` collects `+ P2 V' d(H^-2)/dphi`, `- P2 pi d(eps)/dphi`,
`+ (1/2) d(D_ij)/dphi * theta_i theta_j`, and the analogous `A`-derivative term;
`R_pi` the same with `d/dpi`.

Consequence: with the truncation the system is **not Hamiltonian**, so there is
no exactly conserved `H_FP` even in the autonomous 1D limit. Worse: the
trajectory does not extremize `S`, so the on-shell action carries an error
*linear* in `R`, not quadratic. The tex's panel should be amended to say this;
"a higher-order effect in the same sense as other terms already truncated"
understates it. The missing derivatives are closed-form (`eps = pi^2/2`,
`H^2 = V/(3 - pi^2/2)`, `D_ij ∝ H^2` in reduced Planck units) and should be
restored.

---

## 5. The balance law (the object to actually want)

Combining §4(a)–(c):

```
dH_FP/dN  =  ∂H_FP/∂N |_expl  +  Phi  +  < phi_dot * R_phi + pi_dot * R_pi >_mu
```

Exact. This, not `dH_FP/dN = 0`, is the correct conservation statement for the
onion. It is a strong, cheap, pointwise-in-`N` consistency test on the whole
discretization, and it separates three failure modes that would otherwise be
conflated. Its discrete analogue at `y=+1` is precisely the quantity SBP-SAT
exists to reproduce faithfully.

In the 1D limit `∂H_FP/∂N|_expl = 0` and `Phi = 0`, and the law degenerates to
`dH_FP/dN = <phi_dot R_phi + pi_dot R_pi>` — i.e. **`H_FP` is conserved exactly
once the truncation of §4(c) is removed.**

---

## 6. `H_FP` is not zero, and the Maupertuis relation

A natural expectation, which should be addressed explicitly in the tex because
it is wrong in an instructive way: in the noiseless phase every term of `H_FP`
carries at least one response field, so `H_FP = 0`; if the instanton continues
smoothly from a noiseless phase, `H_FP = 0` throughout, and this is an
unenforced constraint.

**Why it fails.** `H = 0` requires the trajectory to emanate from a **fixed point
of the noiseless flow** with `theta = 0`, which forces the transition time
`T -> infinity` (Grafke & Vanden-Eijnden, discussion below their eq. (19)).
Neither holds here:

- `(phi_init, pi_SR,init)` is *not* a fixed point — the background rolls, `b != 0`;
- `T = N_total = ΔN + δN★` is finite and **prescribed**.

The response fields therefore do **not** grow smoothly from zero at `N_init`.
They jump: `rfield = 0` for `N < N_init`, `rfield(N_init^+) != 0`, determined by
backward integration from the terminal `lambda` source. This discontinuity is not
a defect. It is the shadow of the modelling choice that noise acts only on
`[N_init, N_final]`, with noiseless evolution asserted before; `H_FP` is the
**shadow price of that constraint**. It is the same structural fact as the
largest-time-equation issue already flagged in `sec:open-issues`, seen from the
other end of the interval.

**Maupertuis / envelope relation.** With `H` constant (1D limit),
`S = ∫ <theta, dphi> - H T`, and for fixed endpoints
`∂S/∂T = -H`. In the `(N_final, ΔN, δN★)` parameterization, varying `δN★` at
fixed `(N_final, ΔN)` holds *both* endpoints fixed — `phi_init = phi_nl(N_init)`
with `N_init = N_final - ΔN`, and `phi_end` — and varies only `T = ΔN + δN★`.
Hence, for `FullInstanton`:

```
H_FP  =  - ∂S_MSR / ∂δN★  |_{N_final, ΔN}
```

Since `S` grows with `δN★` (a longer delay is a rarer event), `H_FP < 0`.
Demonstrably nonzero. This is an over-determined numerical check: compute
`H_FP` directly along the trajectory (it should be constant in `N`) and compare
to `-∂S/∂δN★` from the existing grids. The *same* residual `R` of §4(c) controls
the failure of both, so a consistent pair of deviations calibrates `R` while an
inconsistent pair indicates a separate bug.

**Finally**, `H_FP = 0` is not a constraint being missed. It is the condition
that would *determine* the transition duration if `δN★` were free — the
stationarity of `S` over transition times. The existing grids already show no
such interior stationary point (the minimum-action locus runs to the smallest
`(ΔN, δN★)` corner), which is another way of saying `H_FP` never vanishes on the
sampled family. Imposing `H_FP = 0` on top of the current BVP would
over-determine it.

---

## 7. Suggested `onion_model.tex` structure

- **New section `sec:hfp`**, after `sec:instanton-eqs`.
  - §1–§2 above as the derivation, with the canonical-pair subtlety in a
    `\begin{panel}` ("The measure is part of the symplectic form").
  - §3's 1D reduction as a `\semibold{Cross-check against \texttt{FullInstanton}}`
    paragraph, mirroring the existing one in the `\begin{calculation}` block.
  - §4 as three short subsections, or a `\begin{panel}`
    ("Why `H_FP` is not conserved, and why that is not a problem").
  - §5 as the displayed balance law.
  - §6 as a `\begin{panel}` ("The vanishing-Hamiltonian expectation, and why it
    fails"), cross-referenced from `sec:open-issues`'s largest-time discussion.
- **Amend** the "What is *not* corrected here" panel in `sec:instanton-eqs` to
  state that the truncation breaks the Hamiltonian structure and makes the
  on-shell-action error linear rather than quadratic.
- **Amend** `sec:bcs` to record (i) that `phi(-1)=phi_nl` and `pi(-1)=pi_nl` are
  one condition plus an identity, since `A(-1)=0` and `rfield=rmom=0` there make
  `phi_dot(-1) = pi(-1)` automatic; and (ii) the characteristic analysis of
  `y=+1` (see `HFP-STRUCTURE-STATUS.md` §2), from which `A(1)/c = 1 - eps_core`
  exactly, one incoming characteristic, and the reclassification of `g_pi` as a
  model closure.
