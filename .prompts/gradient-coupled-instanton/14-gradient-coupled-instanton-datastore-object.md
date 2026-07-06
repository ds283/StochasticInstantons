# Prompt 14 — `GradientCoupledInstanton` compute target and persistence

## Context

This is the final prompt tying together prompts 01–13: the actual
`ComputeTarget`/`DatastoreObject` class, its SQL persistence, and
orchestration of the full pipeline (`solve_picard` →
`extract_zeta_profile` → `assign_scales`). Read
`./.documents/onion_model_planning.md` and `./.documents/onion_notes.tex`
again in full before starting — this prompt draws on nearly every piece
built so far.

**Scope boundary, agreed explicitly**: $S_{\rm MSR}$ (the numerical MSR
action value) is **out of scope** — `FullInstanton`'s analogous
`msr_action` column exists here too, `nullable=True`, but stays
unpopulated; it's deferred to a dedicated follow-up prompt, since nothing
in prompts 01–13 derived or built the action-functional evaluation. Don't
attempt to compute it here.

**Single class, unlike `FullInstanton`+`CompactionFunction`'s split**: that
split exists because `CompactionFunction` serves two different producers
(`FullInstanton` and `SlowRollInstanton`). `GradientCoupledInstanton` has
no such multiple-producer scenario — one class produces both the raw
solution and the physical $\zeta(y)$/$C(y)$/$r_{\rm phys}(y)$ profile.
Don't split this into two compute targets.

## Task

### Part A — expose noise-source terms as a small reusable helper

`forward_rhs.py` already computes the diluted noise-source terms
(`D_phi*rfield + D_phipi*rmom`, `D_pi*rmom + D_phipi*rfield`) internally
at every RHS evaluation but doesn't expose them separately — needed now
for the noise summary-statistics columns
(`noise_field_min/mean/max`, `noise_mom_min/mean/max`, generalizing
`FullInstanton`'s `noise_phi1_*`/`noise_phi2_*` naming to this model's
field/mom vocabulary). Factor the noise-source-term computation (steps 2–3
of `forward_rhs`'s assembly: $n_{\rm count}$, per-node `D_matrix` loop,
diluted coefficients, the two source terms) out into a small function
`noise_source_terms(phi_full, pi_full, rfield_full, rmom_full, delta_s_N,
delta_s_loc_array, grid, potential, diffusion_model) -> (noise_field_array,
noise_mom_array)`, and have `forward_rhs` call it internally rather than
duplicate the logic. Purely a refactor — `forward_rhs`'s own behavior and
tests must be unchanged; only its internals are reorganized to expose a
reusable piece. Update `tests/test_forward_rhs.py` only if the refactor
requires it (it shouldn't require new test cases, just confirm existing
ones still pass against the reorganized internals).

### Part B — validation guard

On the driver, before dispatch (matching `FullInstanton`'s own
`N_end is None` check — cheap, `trajectory.N_end` only, no `.get()`):

```python
N_offset = trajectory.N_end - N_init
N_total = N_init - N_final + delta_Nstar
if N_offset < 0:
    raise ValueError(...)  # N_init > trajectory's own N_end -- configuration error
if N_offset + N_total > trajectory.N_end:
    raise ValueError(...)  # delta_Nstar > N_final -- runs past end of inflation
```

Both are configuration errors (`ValueError`, not a `failure: True` result),
same category distinction established for the original trajectory-range
guard earlier in this sequence.

### Part C — `ComputeTargets/GradientCoupledInstanton/GradientCoupledInstanton.py`

The compute target class. Constructor parameters, mirroring `FullInstanton`
closely: `trajectory`, `N_init`, `N_final`, `delta_Nstar`,
`n_collocation_points`, `alpha_regularization`, `atol`, `rtol`,
`diffusion_model`, `N_sample` (an `efold_array`, exactly as `FullInstanton`
already uses for its own output grid — reuse directly, don't reinvent),
`label`.

`compute()`: Part B's guard, then dispatch to a Ray remote function that:

1. `trajectory = self._trajectory.get()` (once).
2. `grid = LGLCollocationGrid(n_collocation_points)`.
3. `H_sq_nl_init = potential.H_sq(trajectory.phi_at(N_offset), trajectory.pi_at(N_offset))`.
4. `result = solve_picard(...)` — the full pipeline from prompt 06, now
   with mandatory response-field sourcing (prompt 06's Part A) and the
   corrected $N$-convention (prompt 07). Returns dense
   `phi_grid`/`pi_grid`/`rfield_grid`/`rmom_grid` over `solve_picard`'s own
   internal $N$-grid, plus convergence diagnostics.
5. If not converged: return a `failure: True` result, matching
   `FullInstanton`'s convention — no further pipeline steps.
6. `extraction = extract_zeta_profile(...)` on the final (`N_total`) row.
7. `scales = assign_scales(...)` using `extraction`'s output.
8. Noise summary stats: call Part A's `noise_source_terms` at **every**
   row of the dense solver grid (not just the final row), take
   min/mean/max across the whole $(N,\,{\rm node})$ array for each of
   `noise_field`/`noise_mom`.
9. If `store_full_values`: interpolate `phi_grid`/`pi_grid`/`rfield_grid`/
   `rmom_grid` from the dense solver grid onto `N_sample` — one
   `SplineWrapper` per node (mirroring prompt 05's
   `phi_splines`/`pi_splines` construction pattern), evaluated at each
   `N_sample` point.
10. Package everything needed for `store()`.

Expose a reconstruction method (name suggestion:
`zeta_C_r_at_time(N_query: efold_value) -> dict`) for time-resolved
$\zeta(y,N)$/$C(y,N)$/$r_{\rm phys}(y,N)$ at arbitrary $N$ — **only valid
when `store_full_values` was `True`** (needs the dense $(\phi,\pi)$ rows;
document this limitation explicitly, raise a clear error if called on an
instance stored without full values, don't silently return garbage or
`None`). Reconstructs $(\phi,\pi)$ at the query $N$ from the stored
`GradientCoupledInstantonValue` rows (interpolating between adjacent
`efold_value` rows, or exact if `N_query` matches one), then re-runs
`extract_zeta_profile`+`assign_scales` at that point. Cache via
`ExtractionCache` (prompt 03), keyed on `(self.store_id, N_query.store_id)`
— identity-based, per the design already settled for this cache. Flag
performance as untested/to-be-measured in a comment — this is a new,
unoptimized code path and its cost profile isn't known yet.

### Part D — SQL persistence, three factories

**`sqla_GradientCoupledInstantonFactory`**: mirror
`sqla_FullInstantonFactory`'s registration exactly in shape — same FK
columns (`trajectory_serial`, `N_init_serial`, `N_final_serial`,
`delta_Nstar_serial`, `atol_serial`, `rtol_serial`, `diffusion_serial`/
`diffusion_type` with no FK constraint), replacing `tolerance`-style FKs
with this model's own (`n_collocation_points_serial` FK to
`n_collocation_points.serial`, `alpha_regularization_serial` FK to
`alpha_regularization.serial`), plus `n_fields` (default 1), `N_total`,
`msr_action` (`nullable=True`, unpopulated per the scope boundary above),
`noise_field_min/mean/max`, `noise_mom_min/mean/max`, `label`,
`diagnostics_json`, `validated`. `store()`/`build()` mirroring
`FullInstanton`'s `store_full_values` gating pattern exactly.

**`sqla_GradientCoupledInstantonValue_factory`**: mirror
`sqla_FullInstantonValue_factory` — FK to the parent, FK to `efold_value`,
one JSON blob column containing `phi_j[]`, `pi_j[]`, `rfield_j[]`,
`rmom_j[]` (all `n_collocation_points`-length arrays) per row. Gated by
`store_full_values`, same as `FullInstanton`'s equivalent table.

**A new profile table** (`GradientCoupledInstantonProfile`, or propose a
better name if this one reads awkwardly) — **unconditionally** persisted
(no `store_full_values` gate — this is the actual science output, matching
`CompactionFunctionSamples`'s own precedent): FK to the parent, plain
integer `node_index` column (`0..n_collocation_points-1` — no FK to a
`y_value`-style concept, since $y$ is fully determined by
`n_collocation_points` alone), `zeta`, `r_ratio`, `C`, `r_phys` — all
values at the **final** ($N_{\rm total}$) row only, per the design settled
earlier in this sequence.

Wire all three into **all four registration points** (per the standing
instruction): `Datastore/SQL/Datastore.py`'s `_factories`,
`ClientPool.py`'s `_default_serial_batch_size`, `config/sharding.py`'s
`sharded_tables` (these are genuinely per-instanton physics results,
sharded by `delta_Nstar` like `FullInstanton`/`FullInstantonValue` — not
replicated, unlike the concept objects from prompts 01–13) and
`read_table_config` as appropriate.

### Part E — `--no-store-values` CLI wiring

Add the equivalent of `FullInstanton`'s existing `--no-store-values` flag
for this compute target, following the same
`config/argument_parser.py` pattern already in place.

## Tests

- Part A: confirm `noise_source_terms` extracted correctly, `forward_rhs`
  behavior/tests unchanged.
- Part B: guard raises for both conditions, with informative messages.
- End-to-end: construct a small scenario, run `compute()`, confirm
  `store()` populates all three tables correctly, `store_full_values=False`
  skips `GradientCoupledInstantonValue` rows but still populates the
  profile table, `zeta_C_r_at_time` raises clearly when called on a
  not-fully-stored instance and reconstructs correctly (checked against
  the stored final-row values, as a consistency check) when fully stored.
- Reduction-limit sanity check at this integration level, if feasible
  without excessive new fixture-building — reuse prompt 06's own fixture
  scenario if practical, rather than construct a new one from scratch.

## Acceptance criteria

- [ ] Part A: noise-source terms factored out, `forward_rhs` behavior
      unchanged.
- [ ] Part B: guard in place, both conditions, `ValueError`.
- [ ] `GradientCoupledInstanton` class built with the described
      constructor/`compute()`/`zeta_C_r_at_time` methods.
- [ ] Three SQL factories built; all four registration points completed
      for each (sharded, not replicated, per the reasoning above).
- [ ] `--no-store-values` wired.
- [ ] All tests pass.
- [ ] `msr_action` column present, `nullable=True`, left unpopulated.

## Commit

Single commit, message along the lines of:
`Add GradientCoupledInstanton compute target and persistence (three tables); expose noise-source-term helper; trajectory-range guard`
