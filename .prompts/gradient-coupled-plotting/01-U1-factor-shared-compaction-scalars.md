### Prompt U1 — Factor shared compaction scalars into a standalone module

- **Implements:** design §7.2 (bullet 1), the shared-helper requirement behind
  the §7.1 scalar table.
- **Track / step:** U1
- **Depends on:** none
- **Files (real paths):**
  - add:  `ComputeTargets/compaction_scalars.py`
  - edit: `ComputeTargets/CompactionFunction.py`
- **Context to read first:** `ComputeTargets/CompactionFunction.py` in full,
  especially `_classify_radii` (module-level function) and
  `_compute_instanton_path`'s Step D/E/F block (the C̄ running-integral, the
  `C_min`/`compensated`/`type_II` classification, and the PBH-mass formula);
  `NUMERICAL_SCHEMES.md` §2 for background on why this function exists.
- **Assumable interfaces:** none beyond what already exists in the repo (this
  is the first prompt in the chain). State the exact current signatures you
  are extracting, verbatim, so nothing is re-derived differently:
  - `_classify_radii(r_v, C_v, C_threshold) -> (r_max, r_peak, r_max_at_grid_edge, r_peak_at_grid_edge)`
    — already a free-standing module-level function in
    `ComputeTargets/CompactionFunction.py`. `ComputeTargets/GradientCoupledInstanton/scale_assignment.py`
    already does `from ComputeTargets.CompactionFunction import _classify_radii, ln_k_phys_Mpc` —
    that import path **must keep working** after this refactor (re-export
    from `CompactionFunction.py`, don't just move it and leave that import
    broken).
  - The C̄ integration block: builds a log-uniform dense grid via
    `np.geomspace`, a `SplineWrapper(r_v, zeta_v, x_transform='log', k=3)`,
    `np.gradient` in log-r with a two-point forward-difference override at
    the left endpoint, then a trapezoid-accumulated cumulative integral of
    `r_dense**2 * exp(3*zeta_dense) * (2*rz + 3*rz**2 + rz**3)` (where
    `rz = r_dense * zeta_prime_dense`), interpolated back to the sample
    points and divided by `r_v**3 * exp(3*zeta_v)`.
  - The classification block: `C_min = nanmin(C_v)`, `type_II = C_min < -1.0`,
    `compensated = C_min < 0.0`.
  - The mass formula: `M = (1.0 + C_max) * 5.6e15 * (k_star * r) ** 2 * units.SolarMass`,
    with `k_star = 0.05 / units.Mpc`, called once for `r_max`→`M_max` and once
    for `r_peak`→`M_peak`, both gated on `C_max >= C_threshold`.
- **Task:** Create `ComputeTargets/compaction_scalars.py` containing:
  1. `classify_radii(r_v, C_v, C_threshold)` — move `_classify_radii`'s body
     here verbatim (rename without the leading underscore now that it's a
     shared public helper; keep a thin `_classify_radii = classify_radii`
     alias, or a re-export import, in `CompactionFunction.py` so the existing
     `scale_assignment.py` import keeps working unchanged).
  2. `densify_zeta_profile(r_v, zeta_v) -> (r_dense, zeta_dense, zeta_prime_dense)`
     — factor out CompactionFunction's Step D dense-grid-plus-gradient-plus-
     left-endpoint-pin block (the `N_dense = max(10*len(r_v), 500)`,
     `np.geomspace`, spline, `np.gradient`, and the
     `dzeta_dlogr[0] = (zeta_dense[1] - zeta_v[0]) / (log_r_dense[1] - log_r_dense[0])`
     override), unchanged in behaviour.
  3. `compute_C_bar(r_dense, zeta_dense, zeta_prime_dense, r_v, zeta_v) -> np.ndarray`
     — factor out the C̄ cumulative-integral-and-interpolate-back block.
  4. `classify_C_min(C_v) -> dict` with keys `C_min`, `compensated`, `type_II`.
  5. `pbh_mass(C_max, r, C_threshold, k_star, SolarMass) -> Optional[float]`
     — factor out the mass formula, preserving the `C_max >= C_threshold`
     gate and returning `None` when it fails (mirror the two call sites'
     current `if r_max is not None and C_max >= C_threshold:` guard inside
     the helper, so both callers get the gate for free instead of
     re-implementing it).
  Then edit `ComputeTargets/CompactionFunction.py`'s `_compute_instanton_path`
  to call these five helpers at the same points in the pipeline (Steps D/E/F)
  instead of inlining the logic, with no change to any other step.
- **Constraints:** follow the conventions checklist; plus: this file is pure
  numpy/scipy, no `DatastoreObject`, no Ray, no `AbstractPotential` — mirror
  `Numerics/OnionCoordinate.py`'s "physics-free numerical core" style. Carry
  the Apache-2.0 / University of Sussex header on the new file, copied from
  `ComputeTargets/CompactionFunction.py`.
- **Must NOT:** change any numeric formula, constant, or the order of
  operations in a way that could shift floating-point results (this is a
  pure refactor, not a correction); must NOT change
  `_compute_compaction_function`'s Ray-remote signature, its returned dict's
  key set, or any persisted column; must NOT touch anything under
  `ComputeTargets/GradientCoupledInstanton/` — U2a is where these new
  helpers get their second caller.
- **Acceptance test:** run the existing driver against a fixed small config
  (`quadratic-minimal.yaml`) before and after this change, and diff every
  persisted `CompactionFunction` scalar column
  (`C_peak_full`/`C_bar_peak_full`/`r_max_full_Mpc`/`M_max_full_SolarMass`/
  `C_min_full`/`compensated_full`/`type_II_full`/`V_end_downflow_full_PlanckMass4`/
  `N_end_downflow_full`, and the `_slow_roll` counterparts) row-for-row —
  bit-identical float64 values, not "close." Name this
  `tests/test_compaction_scalars_refactor_golden.py`, comparing two SQLite
  databases produced by the same config before/after the change. This is a
  refactor: "equivalent" is not an acceptable substitute for "identical" (see
  brief §5, "Golden-run equality for refactors").
- **Decision point:** none — this step has no open question in design §12.
