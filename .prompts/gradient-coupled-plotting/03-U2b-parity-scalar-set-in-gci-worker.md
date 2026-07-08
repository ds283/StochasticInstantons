### Prompt U2b — Compute the full parity scalar set inside the GCI worker

- **Implements:** design §7.1 (the exact scalar table), §7.2 (bullet 2),
  §7.3 (bullet 2: `V_end_downflow`/`N_end_downflow` representative).
- **Track / step:** U2b
- **Depends on:** U1, U2a
- **Files (real paths):**
  - edit: `ComputeTargets/GradientCoupledInstanton/GradientCoupledInstanton.py`
    — only the `_compute_gradient_coupled_instanton` `@ray.remote` function
    (Steps 7–10, i.e. everything from the `assign_scales(...)` call through
    the final `return {...}` dict) and its `_failure_result` helper. Do not
    touch the `GradientCoupledInstanton`/`GradientCoupledInstantonValue`/
    `GradientCoupledInstantonProfileValue`/`GradientCoupledInstantonProxy`
    classes in this same file — that is U3's job.
- **Context to read first:** `ComputeTargets/GradientCoupledInstanton/GradientCoupledInstanton.py`'s
  `_compute_gradient_coupled_instanton` function in full (Steps 1–10);
  `ComputeTargets/GradientCoupledInstanton/extraction.py`'s
  `extract_zeta_profile` (return dict: `zeta`, `rho_end`, `N_end_downflow`,
  `phi_end_downflow`, `failure_mask`, all per-node arrays); `ComputeTargets/GradientCoupledInstanton/scale_assignment.py`
  post-U2a (`assign_scales`'s return dict now includes `C_bar`);
  `ComputeTargets/compaction_scalars.py` post-U1.
- **Assumable interfaces:**
  - `extraction["phi_end_downflow"]` and `extraction["N_end_downflow"]` are
    per-node `np.ndarray`s (NaN where that node's own downflow failed),
    already computed at Step 6, before this prompt's insertion point.
  - `scales["C"]`, `scales["r_phys"]`, `scales["C_bar"]` (post-U2a) are
    per-node arrays in the **same node order** as `extraction["zeta"]` — the
    grid order (y=-1 outer edge → y=+1 core), *not* the ascending-by-r sort
    `assign_scales` uses internally only for its own `classify_radii` call.
    Confirm this against the actual U2a code before relying on it: `assign_scales`
    must return `C_bar`/`C`/`r_phys` in the original grid order (per U2a's
    Task item 4), with the sort/densify/classify machinery entirely internal.
  - `scales["r_max"]`, `scales["r_peak"]` are now the **densified**-grid
    values from U2a — read them off `scales` directly; do not recompute or
    re-derive them here.
  - `compaction_scalars.classify_C_min(C_v) -> {"C_min", "compensated", "type_II"}`,
    `compaction_scalars.pbh_mass(C_max, r, C_threshold, k_star, SolarMass) -> Optional[float]`
    (exact names as landed in U1 — if this prompt is executed out of order
    relative to U1, grep `ComputeTargets/compaction_scalars.py` for the
    actual names before writing the import).
- **Task:** immediately after Step 7 (`scales = assign_scales(...)` and its
  failure check) and before Step 8 (noise summary), in
  `_compute_gradient_coupled_instanton`:
  1. `C_max = float(np.nanmax(scales["C"]))`; `C_bar_max = float(np.nanmax(scales["C_bar"]))`.
  2. `classification = compaction_scalars.classify_C_min(scales["C"])` →
     unpack `C_min`, `compensated`, `type_II`.
  3. `r_peak_node = int(np.nanargmax(scales["C"]))` — the node of maximum `C`
     in the **raw, grid-ordered** array (this is a different index space
     from `classify_radii`'s own internal densified-grid argmax computed
     inside `assign_scales`; see the Decision point below for why the raw
     node index, not a dense-grid index, is what you want here).
  4. `V_end_downflow = potential.V(extraction["phi_end_downflow"][r_peak_node])`;
     `N_end_downflow = float(extraction["N_end_downflow"][r_peak_node])` — a
     single scalar each, not the per-node array.
  5. `k_star = 0.05 / units.Mpc`; `M_max = compaction_scalars.pbh_mass(C_max, scales["r_max"], _C_THRESHOLD, k_star, units.SolarMass)`;
     `M_peak = compaction_scalars.pbh_mass(C_max, scales["r_peak"], _C_THRESHOLD, k_star, units.SolarMass)`
     (note: both use `C_max`, never `C_bar_max` — see design §7.1 correction
     1, "there is no barred M_PBH/r_PBH").
  6. Add the unsuffixed key set from design §7.1 to the Step-10 result dict
     (after the existing `msr_action`/`noise_*` keys, before `diagnostics`):
     `C_peak`, `C_bar_peak`, `C_min`, `compensated`, `type_II`, `r_max`,
     `r_peak`, `M_max`, `M_peak`, `V_end_downflow`, `N_end_downflow`. Use
     `scales["r_max"]`/`scales["r_peak"]` directly for the `r_max`/`r_peak`
     keys — do not recompute them.
  7. Update `_failure_result` (the early-return helper at the top of the
     function) to also include every one of these new keys set to `None`,
     matching the existing pattern for `msr_action`/`noise_field_min`/etc.,
     so a failed compute still returns the full new key set.
- **Constraints:** follow the conventions checklist; plus: this prompt only
  changes the Ray-remote function's **returned dict** — it must not add any
  new attribute or property to the `GradientCoupledInstanton` class itself,
  and must not touch the factory. Those are U3's job; keeping this prompt
  scoped to the pure-function return value makes it independently testable
  without a database.
- **Must NOT:** touch `extraction.py` or `scale_assignment.py` in this
  prompt (already landed in U2a) except by reading their outputs; must NOT
  add attributes/properties to `GradientCoupledInstanton`/
  `GradientCoupledInstantonValue`/`GradientCoupledInstantonProfileValue`, and
  must NOT touch `Datastore/SQL/ObjectFactories/GradientCoupledInstanton.py`
  — persistence is U3's job; must NOT re-derive `r_max`/`r_peak`
  independently of `scales`.
- **Acceptance test:** a unit test (`tests/test_gci_parity_scalars.py`) that
  calls `_compute_gradient_coupled_instanton` (directly, or via
  `ray.get(GradientCoupledInstanton(...).compute())`, bypassing the
  datastore) at a grid point where `FullInstanton` + `CompactionFunction`
  are also run against the same `(trajectory, N_init, N_final, delta_Nstar)`
  in a regime expected to agree (small `alpha`, large `n_collocation_points`,
  a `delta_Nstar` where the onion model approaches the homogeneous limit),
  and asserts `abs(gci_result["C_peak"] - cf.C_peak_full) < tol` and
  similarly for `M_max`, `r_max`, `C_min`, `compensated`, `type_II`, within a
  documented tolerance (not exact equality — the numerics genuinely differ:
  LGL-densified classification vs. `CompactionFunction`'s own dense-grid
  classification from a different sampling).
- **Decision point:** `V_end_downflow`/`N_end_downflow` representative
  (design §12, §4 "Per-step guidance" U2b). **Recommended default: the
  `r_peak`-node value** — chosen to be consistent with the mass
  classification, since both `M_max` and `M_peak` derive from `C_max`, and
  `r_peak` is defined as the node/location where `C` is maximised. GCI
  downflows per node (`extraction.py`); `CompactionFunction` has exactly one
  downflow per path; a single representative must be chosen, and it must be
  the *raw node* whose `C` is largest, not an index into the densified
  classification grid (there is no single node corresponding to an
  arbitrary point on that dense grid). Leave a comment at the
  `r_peak_node = ...` line:
  `# DESIGN-DECISION: V_end_downflow/N_end_downflow are reported at the raw-grid node of maximum C (argmax on the un-densified node array), consistent with the C_max-based mass classification — not an index into assign_scales' internal densified classification grid, which has no single corresponding node. See design doc §7.3.`
