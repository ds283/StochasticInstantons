# Prompt 12 — Fix `ln_k_phys_Mpc` to take `H` directly (not `V`,`epsilon`); update call sites; restore exact reduction tests

## Context

Extended hand-derivation (by the project owner, pen and paper, checked
against Leach & Liddle directly — treat the corrected formula below as
validated, not something to re-derive or second-guess) found a real bug in
`ln_k_phys_Mpc` (`ComputeTargets/CompactionFunction.py`), not in anything
built during this prompt sequence. This is `CompactionFunction`'s existing,
already-used physical scale/mass assignment — the bug predates this
sequence entirely; it was only surfaced by the new equivalence-check tests
added in prompt 11.

**The bug**: the formula computes $k=a_kH_k$ by splitting
$a_k/a_0=(a_k/a_{\rm end})\cdot(a_{\rm end}/a_0)$, with the second factor
from entropy conservation ($T_{\rm reh}\propto\rho_{\rm end}^{1/4}$,
$\rho_{\rm end}=\tfrac32V_{\rm end}$ since $\epsilon_{\rm end}\equiv1$ by
definition of end-of-inflation). The existing code merges the
$V_{\rm end}$-dependent piece and the $V_k$-dependent piece (from $H_k$)
into a single log term with one shared $0.25$ coefficient — but they enter
at genuinely different powers ($V_{\rm end}$ at $-1/4$, $V_k$ at $+1/2$,
via $H_k^2=V_k/[3M_p^2(1-\epsilon_k/3)]$).

**Bigger issue behind the same bug, caught in discussion**: fixing this in
terms of $V,\epsilon$ would mean `ln_k_phys_Mpc` reimplements the canonical
Friedmann relation inline — but `AbstractPotential.H_sq` already exists
specifically so this relation lives in exactly one place, with proper
override support for non-canonical kinetics or modified gravity (its own
docstring says so). `ln_k_phys_Mpc` already takes a `units` argument,
implying every call site already has a potential object and field/momentum
state in hand *before* calling it — there's no reason for this function to
ever touch $V,\epsilon$ directly. **Fix: change the signature to take $H$
values directly, computed by the caller via `potential.H_sq`, not $V,
\epsilon$.**

## Task

### 1. `ln_k_phys_Mpc` — new signature, corrected formula

```python
def ln_k_phys_Mpc(N_before_end: float, H_k: float, H_end: float, units, cosmo) -> float:
    """
    Log of the physical wavenumber k in working_units^-1 for a mode that
    exits the Hubble radius N_before_end e-folds before the end of
    inflation.

    Takes H_k (Hubble rate at horizon crossing) and H_end (Hubble rate at
    the true end of inflation, epsilon=1) directly, rather than V/epsilon
    -- the Friedmann relation connecting those is AbstractPotential.H_sq's
    responsibility alone (it has proper override support for non-canonical
    kinetics/modified gravity; this function must not reimplement it).
    Callers already have a potential object and field/momentum state in
    hand at the point they'd call this, so computing H_sq once there costs
    nothing extra.

    Implements Leach & Liddle (astro-ph/0305263) Eq. (2) with instantaneous
    reheating, re-expressed directly in terms of H (H_end enters via
    rho_end = 3*Mp^2*H_end^2, from epsilon_end=1 by definition of end of
    inflation; H_k enters directly from H_k^2 = rho_k/(3Mp^2) at horizon
    crossing).
    """
    Mp = units.PlanckMass
    Mpc = units.Mpc
    T_CMB = cosmo.T_CMB_Kelvin * units.Kelvin

    return (
        -N_before_end
        + log(Mpc * Mp)
        + log(T_CMB / Mp)
        + 0.25 * log(PI**2 / 135.0)
        - 0.25 * log(3.0 * H_end**2 / Mp**2)
        + 0.5 * log(3.0 * H_k**2 / Mp**2)
        - log(Mpc)
    )
```

### 2. Update call sites — mechanical, small changes at each

Both current call sites already compute `potential.V(...)` and
`potential.epsilon(...)` immediately before calling `ln_k_phys_Mpc` —
replace those two calls with one `potential.H_sq(phi, pi)` call at the
same point, and pass the result directly:

- `ComputeTargets/CompactionFunction.py`, Step C (both the per-sample
  `V_k`/`epsilon_k` call and the `V_end_downflow` construction from Step
  A's downflow endpoint).
- `ComputeTargets/GradientCoupledInstanton/scale_assignment.py`'s
  outer-edge anchor call.

Check for any other call sites beyond these two before assuming the list
is complete — search, don't rely on memory of what this sequence has
touched so far.

### 3. Check for golden-value regression baselines

This changes `CompactionFunction`'s actual numerical output (correctly —
the previous values were wrong). Check whether any existing test (in
particular anything resembling a "full fidelity regression" test) pins
specific numerical $r$/mass values against a stored baseline. If so, that
baseline needs regenerating against the corrected formula, not preserved —
a new failure there is the fix working, not a regression this prompt
introduced. Report what you find either way; don't silently update a
baseline without noting that's what happened.

### 4. Restore `test_r_phys_matches_independent_core_downflow` to realistic parameters, exact tolerance

Remove the shrunk-`N_total` workaround from prompt 10 entirely — use
prompt 06's own realistic fixture parameters (`N_total ~ 4`, not `~1.5e-3`).
With the formula fixed, this should now match to **numerical precision**
(the tautology closes exactly — verified independently, term by term, in
the discussion that produced this fix), not an $\mathcal O(\alpha)$-tolerant
approximation. Update the test's docstring to remove the now-obsolete
"why $N_{\rm total}$ was shrunk" rationale, state plainly that agreement is
now exact, and update its construction to compute/pass `H_k`/`H_end`
directly per the new signature.

### 5. Tighten the cross-target check's tolerance

The `GradientCoupledInstanton`-vs-`CompactionFunction` cross-check (prompt
11) compares two different numerical methods (LGL collocation vs.
`solve_ivp` shooting) solving the same underlying problem — with the
formula bug fixed, any remaining discrepancy should be at the scale of
`atol`/`rtol` (numerical integration/discretization error), not a
documented physical residual. Tighten the tolerance accordingly and update
the docstring to say why (numerical, not physical, in origin).

## Acceptance criteria

- [ ] `ln_k_phys_Mpc` takes `H_k`, `H_end` directly; no `V`, `epsilon`
      parameters; no Friedmann-relation arithmetic inside this function.
- [ ] All call sites updated to compute `H_sq` via `potential.H_sq` and
      pass it directly — searched for, not assumed to be only the two
      listed above.
- [ ] Regression-baseline check performed and reported explicitly, with
      any golden values regenerated if needed.
- [ ] `test_r_phys_matches_independent_core_downflow` restored to
      realistic `N_total`, asserting exact (numerical-precision) agreement,
      updated for the new signature.
- [ ] Cross-target check's tolerance tightened to reflect numerical
      solver/discretization error only.
- [ ] Full test suite passes (excluding any pre-existing, genuinely
      unrelated Ray-dependent failures already known from earlier prompts).

## Commit

Single commit, message along the lines of:
`Change ln_k_phys_Mpc to take H directly (not V/epsilon), fixing its V_k/V_end power bug; update call sites; restore exact reduction tests`
