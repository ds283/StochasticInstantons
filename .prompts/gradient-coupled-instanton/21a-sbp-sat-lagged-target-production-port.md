# Prompt 21a — Production port of the SBP-SAT closure with lagged self-consistent core targets

**Replaces Phase 2 of prompt 21.** Prompt 21 Phase 1 is complete, validated, and
(now) committed: the split-form advection + core SAT (τ = A_core/2) makes the
assembled operator's `spectral_abscissa` flat in `n_max` (versus the ~160×
growth of the strong-BC baseline), verified in `analyze_StiffnessSpectrum.py`.
This prompt ports that closure into production, and resolves the one open design
point — the SAT target value — using a **lagged self-consistent** target rather
than any fixed external value.

Same documentation standard as prompt 21: this will be audited by inflation
physicists who are expert numerical *consumers*, not SBP-SAT specialists. Every
non-obvious construct carries a comment block: what it is, why it is there / what
role it plays, what a wrong version looks like (the failure signature), and which
step of the energy estimate it comes from. The documentation is a deliverable.

---

## Physics framing (put a plain-language version in the module docstring)

The continuous problem is **well-posed**: it is advection–diffusion with a
regularity (natural) condition at the coordinate centre `y=+1` — analogous to a
driven heat bar where one end is specified and the far-end value is an *output* of
the dynamics plus regularity, not imposed data. The core field values are the
things we solve for, not boundary data we supply.

What fails is purely the **discretisation**: centred spectral collocation of the
advection-dominated operator, with the boundary conditions imposed *strongly*
(node elimination / pinning), loses the discrete energy estimate that mirrors the
continuous well-posedness, producing right-half-plane eigenvalues that grow with
resolution (`spectral_abscissa ~ n^1.6`; the `n_collocation ≳ 9` blow-ups).

The SAT closure restores the discrete energy estimate. It does **not** add a
physical boundary condition. To make that literally true at the solution, the SAT
target is **lagged and self-consistent**: the penalty provides stabilising
dissipation every sweep, but its target converges to the core value itself, so the
penalty *forcing* vanishes at the Picard fixed point and the converged trajectory
satisfies the unpenalised dynamics — with regularity emerging on its own
(`π = dφ/dN`, `φ` regular ⇒ `π` regular). The stabiliser never biases the answer.

---

## The closure

For each core boundary term that Phase 1 identified as needing a **value-type**
SAT (confirm from the Phase 1 design note which fields this is — the reconstruction
indicates at least `pi_core`; check whether `phi_core`'s advection term also needs
a value-type closure or whether its existing regularity treatment suffices, and
document the decision):

```
d u_core/dN  +=  -(τ / w_core) · (u_core - g_u(N))          # SAT penalty
```

- `τ = A(core)/2` (validated in Phase 1). Document the admissible range and the
  margin.
- `g_u(N)` is the **lagged self-consistent target**:
  - Sweep 0: seed from the FullInstanton profile (below).
  - Sweep k+1: `g_u(N) = u_core(N)` from sweep k, as a spline over `N_grid`.
  - At Picard convergence `g_u → u_core`, so the penalty forcing → 0.

The `-τ/w_core · u_core` part (the dissipation) is present every sweep regardless of
`g`, so per-sweep linear stability is *identical* to Phase 1's fixed-target result
(same Jacobian; only the constant forcing differs). No new stability derivation is
needed for the lagged variant; only its *iteration convergence* is new (below).

### FullInstanton seed

Compute (or fetch) a FullInstanton profile for the same
`(phi_init, pi_init, phi_end, N_total)` and use its `phi(N)`, `pi(N)` as the
sweep-0 core targets.

- **Prefer fetching** the already-computed FullInstanton result from the datastore
  — the pipeline computes `FullInstanton` upstream of `GradientCoupledInstanton`
  for the same parameters (the homogeneous stages complete before the gradient
  stage), so it should be available without recompute. Wire the FK/lookup.
- **Fallback**: compute via the FullInstanton delegate directly (the pattern in
  `scripts/compare_gradient_full.py`, `_compute_full_instanton._function(...)`,
  bypassing Ray). This code is well-tested.
- The seed only sets iterate 0; lagging takes over immediately, so seed *quality*
  affects iteration count, not the converged answer. Document that.

---

## Implementation

1. **State layout.** Stop eliminating/pinning the core node(s). The boundary
   node(s) become integrated DOF; the state length grows accordingly. Grep for and
   fix every site assuming the old length (`pack_state`/`unpack_state`,
   `n_phi_interior`, datastore serialisation, Picard/Newton state handling,
   `extraction.py`, `scale_assignment.py`). Comment each site with the layout change.
2. **Advection.** Switch to the split form
   `A_split = ½(diag(A)·D + D·diag(A) - diag(D·A))` for every advected field.
3. **SAT terms.** Add the penalty above at the core for the field(s) requiring it,
   threading the target splines `g_phi(N)`, `g_pi(N)` into `forward_rhs` the same
   way the response-field splines are already passed. Full audit comment block on
   each penalty (τ, the energy term it cancels, the target's provenance).
4. **Lagged-target loop.** In `solve_picard`: initialise the target splines from
   the FullInstanton seed; after each sweep rebuild them from that sweep's core
   `phi`/`pi`; feed them to the next sweep's `forward_rhs`. Store the final target
   alongside the result so the closure is auditable post hoc.
5. **Under-relaxation hook.** Provide an optional relaxation factor `θ ∈ (0,1]` on
   the target update `g ← (1-θ)·g_prev + θ·u_core_new`, defaulting to `θ=1`. If the
   lagged iteration does not converge at `θ=1` (see acceptance), this is the knob.
6. **φ_core regularity.** If Phase 1 shows `phi_core` needs only its
   regularity/Neumann closure (not a value-type SAT), keep that but impose it
   weakly (SAT) for consistency of the enlarged state, and document why `phi` and
   `pi` are treated differently. If it needs a value-type SAT, lag it the same way.
7. **Gradient/outer edge.** The gradient operator is dissipative/stable (Phase 1);
   leave its treatment unless Phase 1 shows otherwise, and document that the
   asymmetry (advection weak-SAT, gradient as-is) is deliberate. The outer edge
   (`A(-1)=0`) needs no advection SAT; keep its background Dirichlet, imposed
   weakly if the enlarged state requires it.

---

## Acceptance

- [ ] **Per-sweep stability inherited.** With the lagged target, the assembled
      per-sweep operator's `spectral_abscissa` is flat in `n_max` (identical to
      Phase 1's fixed-target result — assert they match, since the Jacobians are
      the same).
- [ ] **Iteration convergence.** The lagged Picard/Newton solve converges to the
      target tolerance for the previously-failing `n_collocation_points`
      (9, 11, 13, 17, 33) on the original failing case
      (`N_init=19.5, N_final=16, delta_Nstar=0.1, alpha=0.1`). If `θ=1` oscillates
      or diverges, find a `θ<1` that converges and record it. Report iteration
      counts vs `n`.
- [ ] **Closure-independence of the answer (the key correctness check).** At
      convergence the SAT penalty forcing `|τ(u_core - g_u)|` is at the level of
      the Picard residual (i.e. → 0), demonstrably. Show that the converged core
      trajectory and `msr_action` do not depend on the seed (FullInstanton vs
      background seed give the same converged answer to tolerance) — this is the
      concrete proof that the stabiliser does not bias the result.
- [ ] **Physics regression.** At low `n` (5, 7) the result still matches
      FullInstanton to the previously-observed tolerance (~1e-6 at n=5); the `n=7`
      growing-`pi` oscillation is gone; and the core trajectory now *converges* as
      `n` increases through 9…33 rather than diverging.
- [ ] **Regularity emerges, not imposed.** Check `(D·pi)_core → 0` at convergence
      without it having been enforced as a value — confirming `pi` inherits `phi`'s
      regularity through the dynamics, consistent with the physics framing.
- [ ] **Production case.** Re-run `quadratic-asteroid-small.yaml`,
      `n_collocation_points ∈ {17, 33}`, end to end; `msr_action` is non-NULL and
      finite for the cells that previously failed 100%.
- [ ] Full existing suite passes; add tests for the split-form skew property, the
      SAT energy cancellation (boundary energy term ≤ 0 after penalty), the enlarged
      `pack`∘`unpack` round-trip, the lagged-target update logic, and a
      closure-independence regression (two seeds → same converged action).

---

## Documentation (the explicit requirement — apply throughout)

- Module docstring: the plain-language physics framing above (well-posed continuum
  → discretisation instability → SAT restores the discrete estimate → lagged target
  so the closure vanishes at the solution).
- Per-construct comment blocks (what/why/failure-signature/energy-step) on: the
  split form, the SAT penalty and `τ`, the lagged-target update, the FullInstanton
  seed, and the enlarged-state layout.
- A "how to verify this is still correct" note pointing at (a) the prompt-20
  abscissa diagnostic, (b) the SAT energy-cancellation test, and (c) the
  closure-independence (two-seed) regression — the three checks that must stay green.

## Out of scope

- Changes to the physics equations or interior operators (unchanged; validated by
  the low-`n` FullInstanton agreement).
- Integrator changes (with the abscissa bounded, explicit RK45 should suffice).
- Response-sector core closure beyond what symmetry with the forward sector
  requires — if the response sector needs the analogous lagged SAT, note it and
  scope it as a short follow-on rather than expanding this prompt.
- The alpha scan / production-grid re-tuning (downstream, once stable).
