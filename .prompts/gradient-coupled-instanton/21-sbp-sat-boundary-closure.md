# Prompt 21 — SBP-SAT boundary closure for the GradientCoupledInstanton spatial operator

**Goal:** remove the spurious right-half-plane instability that makes the
`GradientCoupledInstanton` solve blow up for `n_collocation_points ≳ 9`, by
replacing the current *strong* (node-overwriting) imposition of boundary
conditions with a *weak* SAT (Simultaneous-Approximation-Term) penalty
closure, and by writing the variable-coefficient advection in skew-symmetric
split form. The differentiation matrix `D` already satisfies the diagonal-norm
summation-by-parts (SBP) property, so the SBP half of "SBP-SAT" is free; this
prompt is about the SAT half plus the split form.

**Audience for the code:** this module will be audited by inflation physicists
who are expert numerical *consumers*, not SBP-SAT specialists. Every non-obvious
numerical construct MUST carry a comment block that (a) states in plain terms
what it is, (b) says why it is there / what physical or stability role it plays,
(c) states what a *wrong* version would look like (the failure signature), and
(d) points to the energy-estimate step it comes from. Terseness here is a defect,
not a virtue. Treat the documentation as a deliverable equal to the code.

**Process discipline (matches how this investigation has been run):** derive on
paper, validate on a standalone prototype against the existing diagnostics, and
only then touch production. Phase 1 is a hard gate: do not start Phase 2 until
Phase 1's abscissa criterion passes.

---

## Background: what is wrong and why (write a condensed version of this into the
## module docstring)

The onion spatial operator is advection-dominated. Discretised with a *centered*
spectral collocation derivative and *strong* boundary conditions (the current
`unpack_state` overwrites the outer-edge nodes with the background trajectory and
Neumann-eliminates the core `phi` node), it produces eigenvalues in the right
half-plane whose real part grows with resolution (`spectral_abscissa ~ n^1.6` at
every `Delta_s`; see `stiffness_spectrum.csv`, `--mode spectrum`). A right-half-
plane semi-discrete spectrum is a genuine exponential instability of the ODE the
integrator is handed — which is why it is integrator-independent (RK45, Radau,
BDF all fail; LSODA returns NaN with `success=True`).

The root cause is a lost energy estimate. Continuously, for the advection piece
`d u/dN = A(y) d u/dy`, the energy `E = 1/2 ∫ u^2 dy` obeys
`dE/dN = 1/2 [A u^2]` (boundary only), so stability is entirely controlled by the
boundary term. Discretely, with `H = diag(w_j)` (the LGL quadrature weights) the
SBP identity `H D + D^T H = B`, `B = diag(-1,0,...,0,+1)`, is the exact mirror of
that integration by parts (verified to ~1e-15 on this grid). But:

1. The **plain** product form `diag(A) @ D` is not skew under `H` in the interior;
   the **split** form `A_split = 1/2 (diag(A) @ D + D @ diag(A) - diag(D @ A))`
   is, up to the boundary term. (This is the discrete product rule; it is what
   makes the interior energy-neutral.)
2. Even with the split form, `H A_split + A_split^T H` reduces to a single boundary
   term localised at the core node, of magnitude `~ A(core)` and *destabilising
   sign* (the outer edge contributes nothing because `A(-1) = 0` there). Strong BC
   imposition does not cancel this term; it is the energy injection that drives the
   right-half-plane eigenvalues.

The SAT fix adds a penalty at the offending boundary whose coefficient is chosen,
via the discrete energy estimate, to cancel that injection and leave
`dE/dN ≤ (physical)`. That bounds the spectrum by construction, independent of `n`.

**Validated recipe (isolated advection, full-node, standalone):** split form plus
a dissipative core SAT `-H^{-1} τ e_core (u - g)_core` with `τ = (1/2) A(core)`
drives the advection abscissa from `+4.1e3` (n=191, plain) to a constant `-A(core)/4`,
*identical across n=7…191* and negative. This is the target behaviour; the Phase-1
prototype must reproduce it and then show it survives adding the (already-stable)
gradient term and the physical couplings.

---

## Phase 1 — Derivation + standalone prototype (NO production code changes)

### 1a. Energy-estimate derivation (written up as a Markdown design note + code comments)

Work out, for the **actual** production operator (real signs, real coefficients,
the measure weighting `μ`, and the *real* boundary conditions of the onion model —
outer edge tracks background, core is the free integrated momentum for `pi` and
Neumann for `phi`):

- Which boundary carries the destabilising energy term (the reconstruction here
  finds the **core**, but confirm the sign against the production `advection_term`;
  if the code's advection sign is opposite to the reconstruction, it is the outer
  edge instead, and everything below moves there).
- The exact SBP boundary term for the split-form advection under the relevant norm
  (`diag(w)` for the SBP identity; note and handle the additional `μ` weighting if
  the physical inner product is `diag(w μ)` — state explicitly which norm the
  estimate uses and why).
- The SAT penalty form and the admissible range of `τ`, with the chosen value and
  the margin above the stability threshold documented.
- **The penalty target `g`.** This is a physics-design decision, NOT a free
  numerical parameter: the SAT weakly imposes *some* condition at the boundary, and
  it must be the physically-correct onion-model condition (e.g. for the outer edge,
  the background value; for the core, whatever the model actually requires — the
  current scheme leaves `pi_core` free, so imposing a condition there changes the
  model and must be justified or the penalty must be structured to preserve the
  intended free-outflow behaviour). Flag this explicitly for the physics author
  (David) to sign off; do not silently pick a target.

### 1b. Standalone prototype

Extend the existing standalone harness (`scripts/explore_onion_stiffness.py` /
`analyze_StiffnessSpectrum.py`) with an assembled **SBP-SAT forward operator**:
split-form advection + gradient + couplings + SAT penalties, frozen-coefficient,
in the same style as the existing assembled operator. Reuse the prompt-20
`spectral_stability_metrics()` to report `spectral_abscissa` / `n_rhp` per
`(n_max, alpha, N)`.

### 1c. Phase-1 acceptance (the gate)

- [ ] SBP self-check: `‖H D + D^T H − B‖ / ‖H D‖ < 1e-12` (asserts the norm/grid
      wiring the whole estimate rests on). Already known to hold; assert it in the
      prototype so a regression is caught.
- [ ] **Abscissa bounded in `n`.** For the SBP-SAT operator, `spectral_abscissa` is
      constant-in-`n_max` to within a few percent at each `Delta_s` (contrast the
      current `~n^1.6` growth). This — not `abscissa ≤ 0`, and not `n_rhp = 0` — is
      the primary criterion. If genuine physical growing modes exist they will show
      as a small, `n`-independent positive abscissa; that is acceptable and expected.
- [ ] Advection-only sub-check reproduces the validated `−A(core)/4` constant.
- [ ] The gradient term, added on top, does not reintroduce `n`-growth (it is
      already dissipative/stable; this is a guard, not a fix).
- [ ] `growth_efold_time` (prompt 20) is no longer `≪ N_total` at production
      `n_max` and small `Delta_s`.
- [ ] Optionally, re-run the 18a adjoint diagnostic on the SBP-SAT operator and
      show the boundary block-mismatch collapses relative to the strong-BC baseline
      (mechanism confirmation, complementary to the abscissa/effect confirmation).

Write the Phase-1 findings (abscissa-vs-n before/after, chosen `τ`, chosen `g`,
which boundary) into a short design note before proceeding.

---

## Phase 2 — Production port (only after Phase 1 gate passes)

Refactor the production spatial operator to the validated closure. Expected touch
points (verify against the actual code):

- `unpack_state` (`forward_rhs.py`) and its response-sector analogue: **stop**
  overwriting/eliminating boundary nodes. The boundary nodes become integrated
  DOF; the state vector grows from `2·n_max − 1` to `2·(n_max + 1)`. Every place
  that assumes the old length (`pack_state`, the datastore serialisation, the
  Picard/Newton state handling, extraction, scale assignment) must be updated —
  grep for `n_max - 1`, `n_phi_interior`, and the packed-length arithmetic and fix
  each, with a comment at each site noting the layout change.
- The advection assembly switches from `diag(A) @ D` to the split form.
- The SAT penalty terms are added at the boundary node(s), with the `τ` and `g`
  from Phase 1. Each penalty term gets the full audit comment block.
- The gradient/Neumann-core boundary treatment: convert to the corresponding weak
  SAT for the second-derivative operator *if Phase 1 shows it is needed*; if the
  gradient is confirmed stable as-is, document that it is deliberately left in its
  current form and why, so the asymmetry (advection weak, gradient strong) is not
  mistaken for an oversight.

### Phase-2 acceptance

- [ ] `n_collocation_points` sweep: the solve now **converges and stays bounded**
      through `n = 9, 11, 13, 17, 33` (the values that previously blew up), with the
      core trajectory converging as `n` increases rather than diverging.
- [ ] Physics regression: at low `n` (5, 7) the result still matches `FullInstanton`
      to the previously-observed tolerance (~1e-6 at n=5) — the fix must not move
      the converged answer, only stabilise the approach to it. Reuse
      `scripts/compare_gradient_full.py`.
- [ ] The `n=7` growing `pi` oscillation (`compare_gradient_full` output) is gone —
      the core trajectory is smooth and monotone like `FullInstanton`.
- [ ] Full existing test suite passes; add tests for: the split-form skew property,
      the SAT energy cancellation (assert the boundary energy term is ≤ 0 after the
      penalty), the new state layout round-trip (`pack`∘`unpack` = identity on the
      enlarged state), and an abscissa-bounded-in-n regression at one small `Delta_s`.
- [ ] Re-run the original failing production case
      (`quadratic-asteroid-small.yaml`, `n_collocation_points ∈ {17, 33}`) end to
      end and confirm `msr_action` is now non-NULL and finite.

---

## Documentation standard (the user's explicit requirement — apply throughout)

For each of: the split form, the SBP identity/`H` norm, the SAT penalty, the `τ`
choice, and the `g` target — include a comment block covering what/why/failure-
signature/energy-estimate-reference as described at the top. In addition:

- A module-level docstring giving the plain-language version of the Background
  section above (lost energy estimate → RHP spectrum → SAT restores it), so a
  reader who has never seen SBP-SAT understands the *purpose* before the mechanics.
- A one-paragraph "how to verify this is still correct" note pointing at the
  prompt-20 abscissa diagnostic and the energy-cancellation test, so a future
  auditor knows the two checks that must stay green.
- Inline references to the design note from Phase 1a for the derivation details.

## Out of scope

- Any change to the physics equations themselves (this is purely the discrete
  boundary closure; the interior operators and the continuum equations are
  unchanged and already validated by the n=5 agreement with `FullInstanton`).
- Integrator changes. With the abscissa bounded and the spectrum returned to the
  left half-plane, the existing explicit RK45 should suffice; revisit only if a
  residual (genuine, `n`-independent) stiffness shows up, which is a separate
  question.
- The alpha-regularization scan and any production-grid re-tuning (a downstream
  task once the scheme is stable).
