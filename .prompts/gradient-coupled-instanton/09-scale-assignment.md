# Prompt 09 — Scale assignment: comoving/areal radius, compaction function, physical scale

## Context

Read `./.documents/onion_model_planning.md` and `./.documents/onion_notes.tex`
before starting — §"Physical and comoving scale assignment"
(`eq:compaction-yoo`, `eq:rphys-ratio`), §"Equivalence check against the
discrete (peeling) scheme". That equivalence check's own `\todo` (whether
the existing discrete scheme uses the instanton's local trajectory or the
background for its `r_i` assignment) has already been confirmed — checked
directly against `CompactionFunction`'s `ln_k_phys_Mpc` call site, which
uses the instanton's own local `phi1_arr[i]`/`phi2_arr[i]`, not
`traj.phi_at`/`.pi_at`. Nothing to re-verify here; just don't be surprised
the `\todo` in the tex hasn't been updated yet (that's a documentation
change outside this codebase, not part of this prompt).

This prompt has two parts.

## Part A — extend `extract_zeta_profile`'s return value

`extract_zeta_profile` (prompt 08) doesn't currently return the downflow's
terminal field value, needed here for $V_{\rm end,downflow}$. Add
`phi_end_downflow: np.ndarray` (the downflow's terminal $\phi$ value per
node, from the same `sol.y_events[0][0][0]` already being read for
`rho_end`) to its returned dict. Purely additive — one more array
alongside what's already there, no existing field changed, no signature
change. Update `tests/test_extraction.py` only as needed to check the new
field's presence/correctness (e.g. the outer-edge node's
`phi_end_downflow` should be consistent with continuing the noiseless
trajectory, same spirit as the existing exact-zero $\zeta$ check for that
node).

## Part B — `ComputeTargets/GradientCoupledInstanton/scale_assignment.py`

**Comoving radius** — already fully available, no new calculation:
`comoving_radius_ratio(y_j, delta_s_N_final)` from
`Numerics/OnionCoordinate.py` gives $r(y_j,N_{\rm final})/r_{\rm out}$ for
every node at once (vectorized over `grid.nodes`). As established
throughout this sequence, an absolute $r_{\rm out}$ is never needed — work
in this ratio throughout.

**Compaction function** (`eq:compaction-yoo`): needs $\rho\,\zeta'(\rho)$
where $\rho\equiv r/r_{\rm out}$ (dimensionless — confirm this product is
scale-invariant, i.e. doesn't actually need $r_{\rm out}$'s absolute value,
before implementing; it doesn't, by the same chain-rule argument as
`onion_notes.tex` gives for $r\zeta'(r)$ directly). Chain rule:
$$\zeta'(\rho)\big|_{\text{times }\rho} = \rho_j\cdot\frac{(\text{grid.D} @ \zeta)_j}{d\rho/dy\big|_j}, \qquad \frac{d\rho}{dy}\Big|_j = -\tfrac12\Delta s(N_{\rm final})\,\rho_j$$
(analytic denominator, no numerical differentiation needed there — only
the numerator uses `grid.D`). Then
$C(y_j) = \tfrac23\left[1-(1+\rho_j\zeta'(\rho_j))^2\right]$ node-wise.

**$r_{\rm max}$/$r_{\rm peak}$**: `CompactionFunction.py` already has a
standalone node-finding helper (the function ending in `return r_max,
r_peak, r_max_at_grid_edge, r_peak_at_grid_edge` near the top of that
file) — locate its actual name and reuse it directly against this
module's $C(y_j)$ array, rather than reimplementing peak-finding logic.
Confirm it's genuinely a module-level, importable function (not a private
closure) before relying on this — check rather than assume.

**Physical (present-day) scale** (`eq:rphys-ratio`): a single anchor solve
at the outer edge ($y=-1$, node 0), reusing `ln_k_phys_Mpc` (imported
directly from `ComputeTargets/CompactionFunction.py`, module-level,
already confirmed reusable elsewhere in this sequence — not
reimplemented):

```python
lnk_outer = ln_k_phys_Mpc(
    N_end_downflow[0],                       # relative duration, outer-edge node — no absolute conversion needed, see above
    potential.V(phi_final[0]),
    potential.epsilon(phi_final[0], pi_final[0]),
    potential.V(phi_end_downflow[0]),        # V_end_downflow, from Part A's new field
    units, cosmo,
)
r_phys_out = 2.0 * PI / exp(lnk_outer)       # same formula CompactionFunction's Step C uses
```

Then $r_{\rm phys}(y_j) = \rho_j \cdot r_{\rm phys,out}$ for every node —
`eq:rphys-ratio` directly, no per-shell Leach–Liddle solve.

Top-level function:
`assign_scales(phi_final, pi_final, zeta, N_end_downflow, phi_end_downflow, delta_s_N_final, grid, potential, units, cosmo) -> dict`
returning at least: `r_ratio` (comoving, dimensionless), `C` (compaction
function array), `r_phys` (physical present-day scale array), `r_max`,
`r_peak` (in whatever units the reused helper naturally returns —
`r_phys`-like, confirm which), diagnostics as needed.

## Tests

`tests/test_scale_assignment.py`:

- **`comoving_radius_ratio` reuse sanity check**: `r_ratio[0]` (outer edge)
  equals `1.0` exactly and `r_ratio[-1]` (core) equals
  `exp(-delta_s_N_final)` — both already established as exact structural
  properties back when `comoving_radius_ratio` itself was built; this test
  just confirms this module is actually calling that function correctly,
  not re-deriving the property.
- **Compaction function chain rule**: construct a synthetic $\zeta(y)$
  with a known analytic form (e.g. a low-degree polynomial in $y$, exact
  for the LGL differentiation matrix per prompt 01's own exactness
  guarantees) and confirm $C(y_j)$ matches the hand-computed closed form
  using the exact analytic $\zeta'(y)$, not just "looks reasonable."
- **$r_{\rm max}$/$r_{\rm peak}$ reuse**: confirm the reused helper is
  actually being called (not reimplemented) — e.g. via a a shared test
  fixture/scenario checked against both this module's call and a direct
  call to the helper with the same $C(y_j)$ array, confirming identical
  output.
- **Physical scale reduction check**: at the core ($y=+1$), confirm
  `r_phys[-1]` is consistent with what `CompactionFunction`'s own Step C
  would produce for the same core trajectory in the gradient-coupling-off
  limit — same spirit as the picard.py reduction test, and this one
  *should* be exact (not approximate like prompt 08's core check), since
  scale assignment doesn't involve the downflow-before-matching
  refinement that made prompt 08's core check approximate.

## Acceptance criteria

- [ ] `extract_zeta_profile` gains `phi_end_downflow` in its return dict,
      purely additive.
- [ ] `ComputeTargets/GradientCoupledInstanton/scale_assignment.py`
      created with `assign_scales`.
- [ ] No absolute $r_{\rm out}$ value used anywhere in this module —
      confirmed by the compaction-function derivation and the
      `eq:rphys-ratio` implementation both working in ratios only.
- [ ] $r_{\rm max}$/$r_{\rm peak}$ genuinely reuse `CompactionFunction`'s
      existing helper — not reimplemented.
- [ ] `ln_k_phys_Mpc` reused directly, called once (outer edge only), not
      per-node.
- [ ] All tests above pass, including the exact (not approximate) core
      physical-scale reduction check.
- [ ] No other files touched beyond `extraction.py`'s additive extension.

## Commit

Single commit, message along the lines of:
`Add scale assignment (comoving/areal radius, compaction function, physical scale); extend extraction.py with phi_end_downflow`
