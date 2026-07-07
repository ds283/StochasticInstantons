# Onion-model implementation review

**Reviewer:** Claude (Opus 4.8), Claude Code session
**Date:** 2026-07-07
**Scope:** code introduced from commit `b29ae33` onward, i.e. the
`GradientCoupledInstanton` compute target and its supporting `Numerics/`
modules, checked against the prompt sequence in
`.prompts/gradient-coupled-instanton/` and the physics in
`.documents/onion_model.tex` / `.documents/onion_model_planning.md`.

This report is written to be read cold in a fresh session. Section 1 is a
verdict summary; Sections 2–3 answer the two headline questions (prompt
fidelity, physics fidelity); Sections 4–5 answer the two specific numerical
questions about the collocation/ODE interleaving and the matrix-conditioning
step; Section 6 lists concrete findings ranked by importance.

---

## 1. Verdict summary

- **The code is a faithful, literal implementation of the equations in
  `onion_model.tex`.** Every equation of motion, coefficient, boundary
  condition, terminal condition, and the shooting/Picard structure maps
  term-for-term onto the tex. I found no physics transcription error in the
  core solver. This is high-quality work.

- **It implements the prompt sequence faithfully, with exactly the two
  deviations you already flagged** (noise summary statistics evaluated at the
  core node only rather than over all shells; stored in dimensionless
  Hawking-σ units). Both are confirmed against the literal prompt text
  (prompt 14 step 8 explicitly says "at **every** node… min/mean/max across
  the whole (N, node) array"). I found **no third undocumented deviation** in
  the solver itself.

- **The numerical *strategy* is not the classical collocation-BVP-with-
  matrix-inversion you may be expecting.** It is a **method-of-lines** scheme:
  the y-collocation supplies *explicit* differentiation matrices `D`, `D2`
  that are applied as matrix–vector products, and the resulting large ODE
  system is marched in `N` by an explicit adaptive Runge–Kutta integrator
  (`scipy.solve_ivp`, `RK45`). **There is no linear solve, and hence no matrix
  inversion of the differential operator anywhere in the pipeline.** This is a
  deliberate and defensible choice, but it means the ill-conditioning question
  has a different answer than usual (Section 5): the conditioning problem
  reappears as **stiffness** of the N-integration, and the mitigations the
  planning document explicitly asked for (eigenvalue-spectrum check; SBP+SAT
  fallback; stiff-aware integrator near `N_init`) are **not implemented**.

- **Several cross-checks the planning document called for were not built.**
  The reduction-limit and quadrature checks *are* present and pass; the
  eigenvalue-spectrum check, the α-sensitivity scan, and the
  scale-assignment-equivalence check are absent (Section 6).

- Test status: the 262 unit tests over `Numerics/` and the two RHS modules
  pass; the Picard reduction-limit and convergence tests pass.

---

## 2. Fidelity to the prompt sequence

The prompts (`01`–`15`) were followed in order, one commit each, and the
resulting modules match what each prompt asked for. Spot-checks:

| Prompt | Deliverable | Status |
|---|---|---|
| 01 | LGL nodes/weights/`D`/`D2` via Jacobi eigenvalue construction | ✅ `Numerics/LGLCollocation.py`, matches closed forms; 262 tests pass |
| 02 | onion-coordinate utilities (`delta_s`, `measure`, advection, radius ratio) | ✅ `Numerics/OnionCoordinate.py`; `Δs(N_init)=ln(1+α)` guard present |
| 03 | discretized `L`, advection term, Neumann hard elimination | ✅ `Numerics/DiscretizedOperators.py` |
| 04 | forward-sector RHS + `disable_spatial_coupling` reduction hook | ✅ `forward_rhs.py`; reduction test present and passing |
| 05 | response-sector RHS + terminal condition | ✅ `response_rhs.py` |
| 06/07 | Picard/shooting driver; N-convention fix | ✅ `picard.py` |
| 08 | per-shell ζ extraction (downflow + density match) | ✅ `extraction.py` |
| 09/11/12 | scale assignment; anchor fix; `ln_k_phys_Mpc` fix | ✅ `scale_assignment.py` |
| 13/14 | convergence-param concepts; datastore object (3 tables) | ✅ `GradientCoupledInstanton.py` |
| 15 | MSR action (full 3-term quadratic form) | ✅ `msr_action.py` |

### 2.1 The two known deviations (confirmed)

Both are in `GradientCoupledInstanton.py` Step 8 (lines ~204–256), not in the
solver:

1. **Core-only noise statistics.** Prompt 14 step 8 demands
   `noise_source_terms` evaluated "at **every** node… min/mean/max across the
   whole (N, node) array." The code instead slices the **core node only**
   (`rfield_grid[:, -1]`, `rmom_grid[:, -1]`, `D_*_core[i] = D_*_i[-1]`) and
   takes min/mean/max over the N-axis alone. The in-code comment documents
   this as an intentional analogue of `FullInstanton`'s single reported
   trajectory. **This is the deviation you flagged.**

2. **Dimensionless Hawking-σ units.** Rather than reporting the sourced noise
   magnitude `noise_source_terms` returns, the code reports
   `σ_field = √(2 D_φ)·|rfield| + (2 D_φπ/√(2 D_φ))·|rmom|` (and the momentum
   analogue) — i.e. number of Hawking standard deviations, mirroring
   `FullInstanton.noise_phi1_*`. **This is your second flagged deviation.**

Consequence worth noting for downstream analysis: because both the scope
(core-only) *and* the quantity (σ-units) differ from the prompt, the stored
`noise_field_*`/`noise_mom_*` columns are **not** the shell-resolved noise
amplitude the tex's `D_noise(y,N)` describes. They are a core-trajectory
diagnostic. If shell-resolved noise is later wanted, `noise_source_terms`
(the correct object, over all nodes) is already factored out and callable —
only Step 8's driver loop would need changing.

### 2.2 Test-suite adaptations

The reduction-limit checks were narrowed to configurations where the reduction
is *exact*. In `test_msr_action.py` the reduction test uses a trivial
zero-response scenario (both actions identically zero) rather than a nonzero
match, with an in-code note that the shell-dilution factor `n_count(y=+1,N)`
differs from `FullInstanton`'s undiluted normalisation, so only the
zero-response configuration is an exact cross-check. This is a legitimate
scoping of the test to what is actually mathematically equal, not a masking of
a bug — but it does mean the MSR-action magnitude is **not** cross-validated
against an independent computation in the nonzero-response regime.

---

## 3. Fidelity to the onion-model physics (`onion_model.tex`)

I checked each solver term against its tex equation. Everything matches. The
important correspondences:

**Coordinate/operator layer** (`Numerics/`):
- `delta_s` = `ln(1+α) + (N−N_init) + ½ln(H²_loc/H²_nl,init)` — eq:Deltas-init
  / §4.1. ✅
- `measure` = `exp(−1.5 Δs y)` — eq:self-adjoint-measure. ✅
- `advection_coefficient` = `(y+1)/Δs·(1−ε_core)` — eq:advection-operator. ✅
- `L_operator` = `exp(Δs)exp(Δs·y)[4/Δs² D2 − 2/Δs D]` — eq:Lop-definition,
  **without** the `1/r_out²` prefactor, exactly as the tex demands. ✅
- The `1/(r_out² aH_loc²)` prefactor is applied at point of use as
  `exp(−2·Δs_loc)`, the "local-Δs" identity of the §4.3 panel. ✅ Applied
  **exactly once** — I verified the prefactor is not doubled (the specific bug
  the notes warned about).
- `n_count` = `1.5 Δs · exp(3 Δs_loc) · exp(−1.5(y+1)Δs)` = eq:ncount, since
  `exp(3 Δs_loc) = (r_out aH_loc)³`. ✅

**Forward EOM** (`forward_rhs.py`, eq:inst-phi/inst-pi):
- `dφ = π + A∂_yφ + D_φ·rfield + D_φπ·rmom` ✅
- `dπ = −(3−ε)π − V'/H² + exp(−2Δs_loc)·Lφ + A∂_yπ + D_π·rmom + D_φπ·rfield` ✅
- Diluted coefficients `D_φ=2D11/n_count`, `D_π=2D22/n_count`,
  `D_φπ=2D12/n_count` — eq:Dnoise-diag/cross. ✅

**Response EOM** (`response_rhs.py`, eq:inst-rphi/inst-rpi):
- `drfield = A∂_y rfield + c(N)·rfield + V''/H²·rmom − exp(−2Δs_loc)·L(rmom)` ✅
  — note **L acts on rmom**, correctly reflecting the self-adjoint transfer of
  the operator onto the *other* response field.
- `drmom = A∂_y rmom + c(N)·rmom − rfield + (3−ε)rmom` ✅
- `c(N) = (1−ε_core)(1/Δs − 3/2)` — the exact scalar simplification of §8's
  calculation panel (the y-dependence cancels between advective-adjoint and
  measure-friction terms). ✅ The code applies it identically to every node,
  as the tex requires.

**Boundary/terminal/shooting** (§9, §12):
- y=−1: φ,π Dirichlet-pinned to noiseless background; rfield,rmom pinned to 0. ✅
- y=+1: Neumann hard elimination of φ (forward) and rmom (response) via
  `neumann_boundary_value`; π free (forward), rfield free (response). ✅ The
  free/eliminated roles are correctly *swapped* between sectors.
- Terminal: `rfield_{n_max}(N_final) = −λ/(w_{n_max}·μ(1,N_final))`,
  rfield_j=0 otherwise — eq:terminal-colloc. ✅
- Shooting: single scalar λ root-found so `φ(y=+1,N_final)=φ_end`, via outer
  finite-difference Newton with a fallback nudge. ✅

**ζ extraction** (`extraction.py`, §10): per-node noiseless downflow to ε=1,
ρ_end, density-match against the background via `brentq`,
`ζ = N_end_abs − N_nl(ρ_end)`. This reuses `CompactionFunction`'s Steps A/B
construction per shell, as specified. ✅

**Scale assignment** (`scale_assignment.py`, §11): comoving ratio from the
coordinate map; `C(y) = (2/3)[1−(1+ρζ'(ρ))²]` with `ρζ'` formed scale-free
from `grid.D @ ζ` over the analytic `dρ/dy`; single Leach–Liddle anchor at
y=−1 with the `(1+α)` correction and the ratio-propagation to other nodes. All
match eq:compaction-yoo / eq:rphys-ratio. ✅

**MSR action** (`msr_action.py`, §6 eq:msr-action): the full on-shell
three-term quadratic `+[D_φ/2 rfield² + D_φπ rfield rmom + D_π/2 rmom²]`,
y-integrated with `w_j·μ(y_j,N)` and N-integrated by trapezoid. ✅ The sign
derivation in the module docstring is correct and consistent with
`FullInstanton`'s tested convention.

**Bottom line on physics:** the saddle-point/instanton equations of the onion
model are implemented correctly and completely. The *evolving, active* nature
of the instanton — `Δs(N)`, `r_H(N)`, and all local coefficients recomputed
from the current core/shell state at every RHS evaluation — is faithfully
realised; nothing is frozen to an initial or final value that the tex intends
to evolve.

---

## 4. How the y-collocation and the N-ODE interleave

This is a **method-of-lines** discretisation. The two coordinates play
completely different roles:

- **y (onion coordinate): discretised, never integrated.** The field is
  represented by its values on the `n_collocation_points` LGL nodes. Spatial
  derivatives `∂_y`, `∂_y²` are *algebraic*: matrix–vector products `D @ f`,
  `D2 @ f`. The operators `L`, advection, and the Neumann elimination are all
  built from `D`/`D2` (Section 5). There is no time-stepping in y.

- **N (e-folds): integrated by an ODE solver.** After the y-derivatives are
  replaced by matrix products, each of the `2·n_max − 1` free node-values
  becomes an ODE in N. `scipy.integrate.solve_ivp(..., method="RK45")` marches
  this coupled system.

So the "collocation solve in y" and the "ODE solve in N" do **not** alternate
step-by-step. The y-discretisation is baked once into the RHS function; the
N-integration then runs continuously with that RHS. Concretely, one call to
`forward_rhs(N, state, …)` does, in order (`forward_rhs.py:231`):

1. `unpack_state` → reconstruct the full length-`(n_max+1)` node vectors
   `φ_full`, `π_full`, applying the y=−1 Dirichlet pin (trajectory lookup) and
   the y=+1 Neumann elimination (`neumann_boundary_value`, a single dot
   product over `D`'s last row).
2. Evaluate the coordinate scalars `Δs(N)`, `Δs_loc(y_j,N)` and the pointwise
   physics coefficients `H²_loc`, `ε_loc`, `V'`, `D_matrix` at every node.
3. Apply the **spatial** operators: `L_operator(φ_full, …)` = one `D2 @ φ` and
   one `D @ φ`; `advection_term` = one `D @ φ` and one `D @ π`.
4. Assemble `dφ/dN`, `dπ/dN` per node, `pack_state` back to the free-DOF
   vector, and return it to `solve_ivp`.

`solve_ivp` calls this dozens–hundreds of times per e-fold as RK45 chooses
steps. The differentiation matrices are fixed; only the scalar coefficients
multiplying them change between calls.

### 4.1 The three nested loops (where the BVP structure lives)

The boundary-value structure in N (initial data at N=0, a core condition at
N=N_total) is resolved *outside* the ODE integration, by three nested layers
in `picard.py`:

1. **Innermost — the RHS** (above): pure method-of-lines evaluation.

2. **Middle — Picard iteration** (`picard_inner`, `picard.py:225`): the
   forward (φ,π) and response (rfield,rmom) sectors are coupled
   bidirectionally, so they are solved by fixed-point iteration for a *fixed*
   λ. Each Picard sweep is:
   - a **backward** N-integration of the response sector from `N_total`→`0`
     (`solve_ivp` over `N_grid_rev`), seeded by the terminal condition and
     using the *current* forward solution (passed in as one `SplineWrapper`
     per node, evaluated at each N the backward integrator lands on);
   - then a **forward** N-integration of (φ,π) from `0`→`N_total`, now sourced
     by the *just-computed* response fields (again reconstructed via one
     spline per node).
   Iterated until `max|Δφ_grid| < INNER_TOL` (`MAX_INNER=30`).

   **This is the crucial interleaving detail:** the two sectors communicate
   across N through **per-node SplineWrappers built over the shared 300-point
   `N_grid`** (`_build_node_splines`). The forward pass does not see the
   response ODE directly; it sees a spline reconstruction of the response
   solution from the previous half-sweep, sampled at whatever N the forward
   RK45 requests. y-node coupling is *inside* each RHS (via `D`/`D2`);
   sector-to-sector and N-history coupling is *through the splines*.

3. **Outermost — shooting Newton** (`picard.py:304`): a scalar
   finite-difference Newton on λ drives the core-node terminal residual
   `φ(y=+1, N_total) − φ_end → 0` (`MAX_OUTER=50`). Each Newton evaluation is
   a full converged Picard solve; the derivative dresidual/dλ is estimated by
   a second Picard solve at `λ+dλ`.

The zeroth Picard iterate is a single forward pass with response fields set to
all-zero splines (`picard.py:211`), matching §12's "zeroth iterate" exactly.

### 4.2 N-convention note

The N actually integrated is **local and zero-based** (`0 → N_total`), while
`InflatonTrajectory` lookups use its own absolute N; the two are bridged by
`N_offset = trajectory.N_end − N_init`, threaded into every `forward_rhs`
call. `delta_s()` is always called with a literal `N_init=0.0`. This is
documented at length in `picard.py`'s module docstring and is internally
consistent. It was the subject of prompt 07's fix and looks correct.

---

## 5. The matrix-inversion / conditioning question

**Short answer: there is no matrix inversion, and there is no explicit
condition-number mitigation — because the scheme is designed to avoid the
linear solve entirely.**

### 5.1 Where a classical scheme would invert, and what this code does instead

A classical collocation solver for a BVP forms a global operator (space, or
space×time) and **solves a linear system** `M x = b` — that is where the ill-
conditioning of the second-derivative collocation matrix bites, and where one
would precondition, regularise, or use an SBP/SAT-stabilised operator.

This implementation never forms such a system. The second-derivative operator
`D2` appears **only** on the right-hand side, applied *forward* as `D2 @ f`
inside `L_operator` (`Numerics/DiscretizedOperators.py:54`). The only place a
per-row solve of a `D`-row happens is the Neumann **hard elimination**
(`neumann_boundary_value`), and even that is a closed-form scalar
`f_b = −(Σ_{k≠b} D[b,k] f[k]) / D[b,b]` — one division, not a matrix inverse.
The terminal condition and shooting are likewise scalar. **No
`np.linalg.solve`, `inv`, `lstsq`, or factorisation appears anywhere in the
onion-model code** (verified by grep across `Numerics/` and
`ComputeTargets/GradientCoupledInstanton/`).

So the classical conditioning problem has been **traded, not solved**: instead
of an ill-conditioned linear solve, the code has a **stiff explicit ODE
integration**. The large eigenvalues of `D2` that would wreck a linear solve
instead set the RK45 stability-limited step size in N.

### 5.2 How bad is the conditioning, empirically

The LGL `D2` operator norm grows like O(n⁴) and its spectrum acquires large
imaginary parts — exactly the "spurious/complex eigenvalues under explicit
time-stepping" failure mode the planning document (and §12's hard-elimination
panel) flagged as the specific risk of this approach. Measured directly:

| n_colloc | ‖D‖₂ | ‖D2‖₂ | cond(interior D2) | max\|Re λ(D2)\| | max\|Im λ(D2)\| |
|---|---|---|---|---|---|
| 8  | 2.8e1 | 4.3e2 | 3.8e1 | 4.6e−3 | 4.6e−3 |
| 16 | 1.1e2 | 7.4e3 | 6.2e2 | 2.8e0 | 2.7e0 |
| 32 | 4.6e2 | 1.2e5 | 1.0e4 | 1.4e2 | 1.1e2 |
| 64 | 1.9e3 | 2.0e6 | 1.7e5 | 3.7e3 | 2.8e3 |

The imaginary parts are comparable in magnitude to the real parts, so the
discretised gradient operator is genuinely oscillatory-stiff, not merely
dissipative-stiff. Under RK45 this forces `dt ≲ 3/|λ_max|`: at `n=64` the bare
operator implies steps `~10⁻³` e-folds, and the physics prefactors
(`4/Δs²·exp(...)`) rescale but do not remove this. In practice this means the
node count is limited by integrator cost/stability well before it is limited
by spatial accuracy — the opposite of the usual spectral-accuracy expectation,
and the thing the planning doc said to check empirically.

### 5.3 What mitigations are present

- **Neumann hard elimination** (built) — avoids adding constraint rows to the
  operator; the cheapest boundary treatment, as §12 recommends starting with.
- **α-regularisation** (built) — `Δs(N_init)=ln(1+α)>0` removes the genuine
  `1/Δs → ∞` coordinate singularity at N_init that would otherwise make the
  operator coefficients diverge. This is a real conditioning mitigation, at
  the coefficient level rather than the matrix level.
- **`sinh` y-transform on the response splines** (`picard.py:212,267`) — keeps
  the *spline reconstruction* of exponentially-growing response modes
  well-scaled. This conditions the sector-coupling channel (Section 4.1), not
  the differential operator.
- **Adaptive RK45** — the only thing actually absorbing the operator stiffness,
  by shrinking the step. `atol`/`rtol` are threaded from the tolerance
  concepts.

### 5.4 What mitigations are **absent** (planning doc asked for them)

- **No eigenvalue-spectrum check.** `onion_model_planning.md` ("LGL/SBP
  eigenvalue check") and §12's panel both call for explicitly inspecting the
  spectrum of the discretised `L`+advection operator for spurious growth /
  large imaginary parts before trusting production runs. Not implemented; no
  test computes it. Given the numbers in 5.2, this is the most material gap.
- **No SBP+SAT fallback.** The planned fallback for when hard elimination
  shows instability (weighted-norm summation-by-parts with simultaneous
  approximation terms) is not built. This is acceptable *if* hard elimination
  is empirically stable at the node counts actually used — but that empirical
  check (5.2) has not been done, so there is no evidence either way on the
  production grids.
- **No stiff/implicit integrator near N_init.** The planning doc warned that
  small α makes coefficients stiff near N_init and "may need a stiff-aware
  integrator for the first stretch of N." The code uses `RK45` (explicit,
  non-stiff) throughout. No `Radau`/`BDF` option is wired.

### 5.5 Practical implication

For modest node counts (the `n≈8–24` range the tests exercise) the explicit
scheme is fine and the tests pass. The **untested** regime is production-scale
`n_max` with the wide-transition `Δs∼20` profiles: there the O(n⁴) operator
norm and the complex spectrum mean RK45 may either become very slow (tiny
steps) or silently lose accuracy. I would not trust a convergence scan in
`n_max` (the planning doc's primary convergence parameter) without first
adding the eigenvalue-spectrum diagnostic of 5.4 — otherwise a divergent run
will look like a physics result rather than an integrator-stability artefact.

---

## 6. Findings, ranked

**F1 (most material) — Operator-stiffness diagnostics called for by the
planning document are not implemented.** No eigenvalue-spectrum check, no
SBP+SAT fallback, no stiff integrator. The empirical D2 spectrum (Section 5.2)
shows the exact complex-eigenvalue growth the plan warned about. This does not
mean the current results are wrong; it means the scheme's stability envelope in
`n_max` is uncharacterised, and the planned safety check for exactly this is
missing. *Recommend building the eigenvalue diagnostic before any `n_max`
convergence scan.*

**F2 — Noise summary statistics are core-only and in σ-units (both already
known to you).** Confirmed as deviations from prompt 14 step 8's literal text.
The correct all-node object (`noise_source_terms`) is factored out and
available; only Step 8's driver loop restricts to the core. Flagged so a
future "shell-resolved noise" request knows the plumbing already exists.

**F3 — MSR-action magnitude is not independently cross-validated.** The
reduction-limit tests only check the *zero-response* case (both actions
identically 0). In the nonzero regime the three-term action is exercised but
never compared against an independent computation. The sign/derivation is
argued correctly in-code, but a numerical second opinion is absent. Note also
the open theoretical issue (§14 / planning): the 2D action's probability
interpretation is unresolved, so `msr_action` should not yet be read as a
corrected PBH-formation probability. The code correctly stores it as a raw
number and makes no such claim.

**F4 — ζ→C(y) is fragile to a single failed extraction node.** `C(y)` is built
from `grid.D @ ζ` (dense spectral first derivative). I verified that a single
NaN in `ζ` (one node whose downflow/density-match failed — a masked,
non-raising failure in `extraction.py`) poisons the **entire** `C(y)` profile
to NaN, not just that node. `extraction.py` correctly isolates per-node
failures, but `assign_scales` then destroys that isolation. Worth a guard
(e.g. mask/interpolate failed nodes before differentiating, or at least
surface how many nodes are NaN in the persisted diagnostics — currently the
`extraction_failure_mask` is stored, so the information survives, but `C` is
silently all-NaN).

**F5 — Cross-checks in `onion_model_planning.md` not built:** α-sensitivity
scan; scale-assignment equivalence vs the discrete/peeling scheme (which the
plan itself flags as depending on an unverified `a,H` convention in the
existing discrete code); terminal-condition-placement insensitivity check on
the 1D `FullInstanton`. These are validation studies rather than solver code,
but they were the plan's stated gates on trusting output.

**F6 (minor, positive) — no third solver deviation found.** Beyond F2, the RHS
assembly, coordinate utilities, boundary/terminal/shooting logic, extraction,
scale assignment, and MSR action all match both the prompts and the tex. The
`disable_spatial_coupling` reduction hook, the once-only `1/r_out²` prefactor,
the swapped free/eliminated boundary roles between sectors, and the scalar
`c(N)` simplification are all correct — these were the specifically
error-prone points the notes called out, and each is right.

---

## 7. Suggested next steps (for the online session)

1. **Add the eigenvalue-spectrum diagnostic** (F1) — compute the spectrum of
   the assembled `L`+advection operator (with the physics prefactors and
   Neumann elimination folded in) at representative `(N, n_max, Δs)` and log
   max real/imag parts. This is the gate the plan set and the cheapest way to
   know whether the explicit RK45 scheme is safe on production grids.
2. **Decide the noise-statistics contract** (F2) — if shell-resolved noise is
   wanted, switch Step 8 to loop `noise_source_terms` over all nodes; the
   helper already returns the full-node arrays.
3. **Harden ζ→C** (F4) — mask failed-extraction nodes before `grid.D @ ζ`.
4. **Independent MSR-action check** (F3) before treating the number
   quantitatively; and keep the §14 probability-interpretation caveat attached
   to any use of it.
5. Run the plan's α-sensitivity and scale-equivalence cross-checks (F5) once
   the stiffness envelope (step 1) is understood.
