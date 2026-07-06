# Prompt 08 — Zeta-profile extraction (per-shell downflow and density match)

## Context

Read `./.documents/onion_model_planning.md` and `./.documents/onion_notes.tex`
before starting — §"No explicit freezing; extraction of $\zprofile(\yco)$"
(`eq:zeta-extraction`).

**Precision note on the tex's equivalence claim, for the record** (not
something to act on in this prompt, beyond the comment task below):
`CompactionFunction`'s existing Step B does **not** downflow before density
matching — it matches $\rho$ directly at the instanton's own sample point,
and only downflows (`integrate_noiseless_trajectory`, Step A) for the
separate scale-assignment step. What this prompt builds — downflow to
$\varepsilon=1$ *before* matching — is a deliberate refinement beyond that,
confirmed in discussion as negligible in a single-field model but necessary
in a model with genuine isocurvature/multiple fields. Add a short
documentation-only comment near `CompactionFunction`'s Step B (in
`ComputeTargets/CompactionFunction.py`) noting this — that its direct
match-without-downflow is a single-field simplification that would need
revisiting if the model ever gains isocurvature degrees of freedom. No
logic change to `CompactionFunction` itself.

**The $N$-offset handling — get this right, we've hit this exact class of
bug twice already in this sequence.** `integrate_noiseless_trajectory`
integrates from its own fresh $N=0$; its returned `N_end_downflow` is a
duration **relative to the downflow's own start**, not absolute. Every
shell's downflow starts from the same shared final time (local $N_{\rm
total}$, same for every $y$ per the extraction procedure's own step 1), so:

$$N_{\rm end}^{\rm abs}(y_j) = N_{\rm offset} + N_{\rm total} + N_{\rm end,downflow}(y_j)$$

**`N_offset` must be accepted as a parameter, passed through from
`picard.py`'s already-computed value — do not recompute it from
`trajectory.N_end - N_init` independently inside this module.** That's
exactly the redundant-computation pattern that caused the two bugs fixed
in prompt 07; threading the single already-correct value through closes
off a third occurrence. `trajectory.N_end` itself may still be read
directly where `CompactionFunction`'s own Step B pattern already does so —
specifically, only for the `brentq` search bracket's upper bound — since
that's an existing, unproblematic use, not the redundant one.

## Task

### `ComputeTargets/GradientCoupledInstanton/extraction.py`

```python
def extract_zeta_profile(
    phi_final: np.ndarray,      # phi_j(N_total) for every grid node j
    pi_final: np.ndarray,       # pi_j(N_total)
    N_offset: float,            # from picard.py, NOT recomputed here
    N_total: float,
    trajectory: InflatonTrajectory,
    potential: AbstractPotential,
    atol: float,
    rtol: float,
    units,                      # for Mp, matching CompactionFunction's own signature shape
) -> dict:
    """
    Returns a dict with (at least): zeta (array, nan where extraction
    failed for a node), rho_end (array), N_end_downflow (array, the raw
    relative durations, kept for diagnostics), failure_mask (bool array).
    """
```

Per node $j$:

1. Downflow: `integrate_noiseless_trajectory(phi_final[j], pi_final[j], potential, atol, rtol)` — same function `CompactionFunction` already imports from `InflationConcepts/noiseless_equations.py`, not reimplemented. Handle failure (no `sol`, or no terminal event) the same way `CompactionFunction`'s Step A does — mark this node's `zeta` as `nan`, don't raise, continue to the next node.
2. $\rho_{\rm end}(y_j) = 3M_p^2\,\text{potential.H\_sq}(\phi_{\downarrow},\pi_{\downarrow})$ at the downflow's terminal event state.
3. $N_{\rm end}^{\rm abs}(y_j) = N_{\rm offset} + N_{\rm total} + N_{\rm end,downflow}(y_j)$ (the formula above — this is the one place in this module where getting the offset arithmetic wrong would silently corrupt every node's $\zeta$, so this line deserves its own direct unit test, not just an end-to-end one).
4. Density-match against the background: `brentq` over absolute $N\in(0, \text{trajectory.N\_end})$ finding where $3M_p^2\,\text{potential.H\_sq}(\text{trajectory.phi\_at}(N),\text{trajectory.pi\_at}(N)) = \rho_{\rm end}(y_j)$ — mirror `CompactionFunction`'s Step B `brentq` call shape (bracket, `xtol`/`rtol` from `atol`/`rtol`), including its density-bracket sanity check (`rho_end_traj <= rho_target <= rho_start_traj`, skip/`nan` if outside range) before attempting the root-find.
5. $\zeta(y_j) = N_{\rm end}^{\rm abs}(y_j) - N_{\rm nl}(\rho_{\rm end}(y_j))$.

## Tests

`tests/test_extraction.py`:

- **Direct unit test of the offset formula** (item 3 above): with a stub
  downflow result (mock or a trivial potential where the downflow duration
  is analytically known) and hand-chosen `N_offset`/`N_total`, confirm
  `N_end_abs` matches the formula exactly — isolated from the rest of the
  pipeline, so a future refactor that touches this arithmetic gets caught
  immediately.
- **Outer-edge sanity check**: for the $y=-1$ node (Dirichlet-pinned to
  the noiseless trajectory throughout, so its downflow is just a
  continuation of the noiseless trajectory it's already sitting on),
  $\zeta(-1)$ should come out at (or extremely close to, within downflow
  integration tolerance) exactly zero — a strong, cheap, physically
  meaningful test, not just a numerical coincidence to shrug off if it's
  slightly off.
- **Core reduction check — approximate, not exact, and say why in the
  test's own comment.** Unlike every previous reduction test in this
  sequence (prompts 04–06, all exact to floating-point precision), this
  one should only be **approximately** consistent with what
  `CompactionFunction`+`FullInstanton` would give for the same core
  trajectory, because — per the precision note above — `CompactionFunction`
  doesn't downflow before matching and this module does; they're
  expected to differ by the same small, single-field-negligible amount
  discussed when this design was settled. Pick a tolerance that reflects
  "small isocurvature correction," not "should be identical," and say so
  in a comment so nobody later tightens it into a spurious failure.
- **Failure handling**: construct a scenario where the downflow can't
  reach $\varepsilon=1$ (or density-matching fails, out-of-bracket), confirm
  the corresponding node's `zeta` is `nan` and `failure_mask` reflects it,
  without raising or corrupting other nodes' results.

## Acceptance criteria

- [ ] `ComputeTargets/GradientCoupledInstanton/extraction.py` created with
      `extract_zeta_profile`.
- [ ] `N_offset` is a required parameter, never recomputed from
      `trajectory.N_end - N_init` inside this module.
- [ ] `integrate_noiseless_trajectory` reused directly (imported from
      `InflationConcepts/noiseless_equations.py`), not reimplemented.
- [ ] Documentation-only comment added near `CompactionFunction`'s Step B
      noting the single-field-vs-isocurvature distinction — no logic
      change to `CompactionFunction.py`.
- [ ] All tests above pass, including the outer-edge exact-zero check and
      the explicitly-approximate (with commented rationale) core check.
- [ ] No other files touched.

## Commit

Single commit, message along the lines of:
`Add per-shell zeta-profile extraction (downflow + density match); note single-field simplification in CompactionFunction`
