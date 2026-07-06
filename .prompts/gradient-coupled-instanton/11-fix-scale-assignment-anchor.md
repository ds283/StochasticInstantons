# Prompt 11 — Fix scale-assignment anchor (arithmetic e-folds, not downflow, from a consistent outer anchor)

## Context

This corrects a real bug in prompt 09's `scale_assignment.py`, found through
extended discussion, and brings `CompactionFunction`'s own Step C onto the
same footing so the two compute targets assign consistent scales. Read
`./.documents/onion_model_planning.md` and `./.documents/onion_notes.tex`
(§"Physical (present-day) scale", §"Equivalence check") before starting.

**The bug**: `assign_scales` anchored $r_{\rm phys,out}$ using the outer
edge's own downflow-from-endpoint (`N_end_downflow[0]`), which assigns the
scale of the horizon at the **end** of the transition, not the **start**.
$r_{\rm out}$ is $(1+\alpha)$ times the horizon at $N_{\rm init}$, not at
$N_{\rm final}$.

**The fix, settled in discussion**: since $y=-1$ sits exactly on the
noiseless trajectory throughout (Dirichlet-pinned), its "downflow from the
endpoint" is guaranteed to just be the remaining noiseless trajectory — no
integration needed. The number of e-folds from the transition's start to
the true end of inflation is $N_{\rm init}$ itself (arithmetic, already
known), with the noiseless trajectory's own local $V,\epsilon$ at the start
and its own true endpoint $V$ for $V_{\rm end}$:

```python
V_start = potential.V(trajectory.phi_at(N_offset))
epsilon_start = potential.epsilon(trajectory.phi_at(N_offset), trajectory.pi_at(N_offset))
V_end_bg = potential.V(trajectory.phi_at(trajectory.N_end))
lnk_outer = ln_k_phys_Mpc(N_init, V_start, epsilon_start, V_end_bg, units, cosmo)
r_phys_out = (1.0 + alpha) * 2.0 * PI / exp(lnk_outer)
```

The $(1+\alpha)$ factor is required because $r_{\rm out}$ is deliberately
$(1+\alpha)$ larger than the true horizon at $N_{\rm init}$ (that's the
whole point of the regularization) — without it, $r_{\rm phys,out}$ would
drift as $\alpha$ is varied rather than staying stable, which is the
property this construction is supposed to have.

**Why this generalizes correctly to `CompactionFunction`, and what stays
different (genuinely, not a bug)**: "work forward from the anchor, using
Leach–Liddle with each sample's own local $(V,\epsilon)$" means
$N_{\rm before,end,i} = N_{\rm init} - N_{\rm inst,i}$ — plain e-fold
arithmetic from a fixed anchor, **not** a re-integrated downflow at every
sample. This replaces the per-sample downflow-based scale assignment
`CompactionFunction` currently does (`N_end_downflow + (N_total -
N_inst_arr)`), which was only needed to guard against isocurvature at the
*single* endpoint that scheme downflows from — a concern that doesn't
apply once every sample's scale comes from simple arithmetic relative to
a background anchor. `CompactionFunction` has no `alpha` (no coordinate
singularity to regularize — it has no continuous shell structure), so its
own anchor is just $N_{\rm init}$, no $(1+\alpha)$ factor — meaning its
outer sample and `GradientCoupledInstanton`'s $y=-1$ will differ by
$\mathcal O(\alpha)$, not exactly — expected and acceptable, not something
to paper over by inventing an artificial `alpha` for `CompactionFunction`.

**What does NOT change**: $\zeta(y)$ extraction (`extraction.py`) keeps its
real per-shell downflow exactly as built in prompt 08 — that's the
genuinely isocurvature-sensitive calculation and is unaffected by any of
this. `FullInstanton`/`CompactionFunction`'s existing $\zeta$ computation
(Step B) also keeps its simpler, no-downflow, single-field-only approximation
unchanged — only Step C (scale assignment) is being fixed here.

## Task

### Part A — `ComputeTargets/GradientCoupledInstanton/scale_assignment.py`

- Remove `N_end_downflow`/`phi_end_downflow` from `assign_scales`'s
  signature entirely (confirm they're not used anywhere else in this file
  before removing — they shouldn't be, per the code as read, but check).
- Add `trajectory`, `N_init`, `N_offset`, `alpha` as new required
  parameters.
- Replace the anchor computation with the fixed version above — no
  downflow integration anywhere in this function.
- Update the module docstring's "Three distinct notions of scale" panel to
  describe the corrected anchor mechanism.

### Part B — `ComputeTargets/CompactionFunction.py`, Step C

- Replace `N_before_end_arr = N_end_downflow + (N_total - N_inst_arr)`
  with `N_before_end_arr = N_init_val - N_inst_arr`.
- **Before removing Step A's downflow computation** (`sol_down`,
  `N_end_downflow`, `V_end_downflow`), check whether `N_end_downflow`/
  `V_end_downflow` are consumed anywhere outside this function — they are
  currently part of the returned result dict's public keys. If anything
  else in the codebase reads those keys, keep computing and returning them
  (Step A's downflow just stops being *used* for Step C's own scale
  assignment) rather than removing them and silently breaking a
  consumer. If nothing reads them, they can be removed along with the
  downflow computation itself — check, don't assume either way.
- The "latest-exit rule" monotonicity enforcement (`N_be_mono`) — check
  whether it's still meaningful/needed once `N_before_end_arr` is pure
  arithmetic (monotonically related to `N_inst_arr` by construction, so
  the loop may now be a no-op) — simplify if it genuinely no longer does
  anything, but confirm with a test rather than removing on inspection
  alone.

### Part C — test fixes

**Remove** `test_r_phys_ln_k_linearity_self_consistency` (from prompt 10) —
it checked internal consistency of the now-removed downflow-based anchor
formula; the mechanism it was testing no longer exists, and there's nothing
meaningful left to rename it to.

**Rework** `test_r_phys_matches_independent_core_downflow` into a test that
matches the corrected mechanism, using realistic (prompt-06-scale, not
artificially shrunk) `N_total` — the shrunk-`N_total` workaround was
fitting the test to the bug and should not survive this fix:

- Confirm the corrected `r_phys[-1]` (core) matches a **direct, independent**
  call to `ln_k_phys_Mpc(N_init - N_total, V_core_local, epsilon_core_local,
  V_end_bg, ...)` — using the core's genuine local $(V,\epsilon)$ at
  $N_{\rm final}$ (from the converged `solve_picard` state) and the
  background's true endpoint $V$ — computed independently in the test, not
  by re-deriving `assign_scales`'s own arithmetic. This should now be
  **exact** to numerical tolerance, for any `alpha` — not an $\mathcal
  O(\alpha)$-tolerant approximation like the previous (incorrect) version
  needed.
- **New consistency check**: the outer edge's own downflow duration, as
  computed independently by `extract_zeta_profile` (`N_end_downflow[0]`,
  unrelated to the new anchor mechanism, which doesn't use it), should
  match `N_init` to numerical tolerance — confirms the "guaranteed to be
  the same, no need to recompute" claim underlying this whole fix, using
  machinery (`extraction.py`'s downflow) that's otherwise unrelated to
  `scale_assignment.py`'s own arithmetic.
- **New cross-target check**: with `CompactionFunction` also fixed (Part
  B), compare `GradientCoupledInstanton`'s core `r_phys` against
  `CompactionFunction`'s own `r` at its outermost valid sample, for the
  same underlying trajectory/potential — expect agreement up to a small,
  genuinely $\mathcal O(\alpha)$ residual now (from the $(1+\alpha)$
  anchor difference alone, not from any deeper mechanism mismatch), and
  say so explicitly in the test's docstring so the tolerance choice is
  traceable to a specific, named cause rather than "small enough."

## Acceptance criteria

- [ ] `assign_scales` no longer takes or uses `N_end_downflow`/
      `phi_end_downflow`; anchors via `trajectory`/`N_init`/`N_offset`/
      `alpha` with no downflow integration.
- [ ] `CompactionFunction`'s Step C uses `N_init_val - N_inst_arr`
      directly; Step A's downflow output preserved or removed based on an
      actual check of downstream consumers, not assumption.
- [ ] Obsolete self-consistency test removed; core-reduction test reworked
      to be exact (not $\alpha$-tolerant) using realistic `N_total`.
- [ ] New outer-edge-downflow-equals-`N_init` consistency check added.
- [ ] New cross-target (`GradientCoupledInstanton` vs `CompactionFunction`)
      check added, with its expected residual traced explicitly to the
      $(1+\alpha)$ anchor difference.
- [ ] $\zeta$-extraction (`extraction.py`) and `CompactionFunction`'s own
      Step B are untouched.
- [ ] All tests pass; no regressions in `test_picard.py`/`test_extraction.py`.

## Commit

Single commit, message along the lines of:
`Fix scale-assignment anchor to use arithmetic e-folds from a consistent (1+alpha)-adjusted outer anchor, in both GradientCoupledInstanton and CompactionFunction`
