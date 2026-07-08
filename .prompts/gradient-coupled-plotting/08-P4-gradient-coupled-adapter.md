### Prompt P4 — `GradientCoupledAdapter` / `SpatialAdapter`, as pure reads

- **Implements:** design §3.2 (base protocol, GCI mapping column of the
  §3.1 table), §3.3 (spatial extension), §7.5 (adapter consequence of
  upstream parity).
- **Track / step:** P4
- **Depends on:** U3, P2, P3
- **Files (real paths):**
  - add:  `plotting/adapters/gradient.py`
- **Context to read first:** `plotting/adapters/base.py` and
  `plotting/adapters/full.py` (from P2 — this adapter implements the same
  `InstantonAdapter` protocol); `ComputeTargets/GradientCoupledInstanton/GradientCoupledInstanton.py`
  in full post-U3 (the class now exposes `C_peak`/`C_bar_peak`/`C_min`/
  `compensated`/`type_II`/`r_max`/`r_peak`/`M_max`/`M_peak`/
  `V_end_downflow`/`N_end_downflow` properties, plus the pre-existing
  `msr_action`/`noise_field_*`/`noise_mom_*`/`profile`/`values`/
  `zeta_C_r_at_time()`); `GradientCoupledInstantonProfileValue`'s properties
  (`node_index`, `zeta`, `r_ratio`, `C`, `C_bar` (U2a), `r_phys`); the §4.1
  fetch-mode contract table from P3 (this adapter's `fidelity` tag is
  derived from which mode the object was fetched with).
- **Assumable interfaces:**
  - Post-U3: `GradientCoupledInstanton.C_peak`, `.C_bar_peak`, `.C_min`,
    `.compensated`, `.type_II`, `.r_max`, `.r_peak`, `.M_max`, `.M_peak`,
    `.V_end_downflow`, `.N_end_downflow` are plain reads (`Optional[float]`/
    `Optional[bool]`), identical-by-construction to `CompactionFunction`'s
    `_full`-suffixed set — **no physics, no reconstruction, no fallback
    computation in this adapter**; if a value is `None`, the adapter reports
    `None`, it does not compute a substitute.
  - `GradientCoupledInstanton.profile -> List[GradientCoupledInstantonProfileValue]`,
    each with `.node_index`, `.zeta`, `.r_ratio`, `.C`, `.C_bar`, `.r_phys`
    — populated whenever the object was fetched with `do_not_populate=False`
    OR `profile_only=True` (P3); empty otherwise.
  - `GradientCoupledInstanton.values -> List[GradientCoupledInstantonValue]`,
    each with `.N`, `.phi`, `.pi`, `.rfield`, `.rmom` (each a `List[float]`
    of length `n_collocation_points`) — populated only on a full,
    dense-stored fetch; empty otherwise (P3).
  - `GradientCoupledInstanton.zeta_C_r_at_time(N_query: efold_value) -> dict`
    with keys `N`, `zeta`, `r_ratio`, `C`, `r_phys`, `failure_mask` — raises
    `RuntimeError` if `self._values` is empty (the existing guard, P3
    invariant 3; do not add a second check for this in the adapter).
  - `GradientCoupledInstanton.n_collocation_points_value`,
    `.alpha_regularization_value` — for populating `coords`.
- **Task:**
  1. In `plotting/adapters/gradient.py`, implement `GradientCoupledAdapter(InstantonAdapter)`:
     - `kind = "gradient-coupled"`; `display_label` includes `n` and `α`,
       e.g. `f"GCI (n={n_collocation_points}, α={alpha:.3g})"`.
     - `coords` includes `N_init`, `N_final`, `delta_Nstar`, **and** `alpha`,
       `n_collocation_points` (design §3.2's GCI-specific coords), all
       supplied at construction from the query context (the caller's
       `N_init`/`N_final`/`delta_Nstar`/`alpha`/`n_collocation_points`
       objects), never scraped off the wrapped `GradientCoupledInstanton`.
     - `time_history(channel)`: reads the **core node** — the last entry
       (`y=+1`) of each per-sample row — for `channel in {"phi", "velocity", "rfield", "rmom"}`,
       mapping to `.values[i].phi[-1]`/`.pi[-1]`/`.rfield[-1]`/`.rmom[-1]`
       across `i`, paired with `.values[i].N.N`. Returns `None` if
       `.values` is empty (i.e. `fidelity != "dense"`) — this is a capability
       gap, not a failure, so it must not raise.
     - `noise_history()`: build from `noise_field_min/mean/max` and
       `noise_mom_min/mean/max` — these are already scalar summary stats,
       not a full array, so this method's return shape is necessarily
       thinner than `FullInstantonAdapter`'s (which has a real per-N array
       via `noise_profile_arrays()`); document this asymmetry in a
       docstring rather than papering over it, and return the three
       summary stats under the same dict keys the base protocol expects
       where they exist, `None` elsewhere.
     - `radial_profile()`: a **pure read** off `.profile` — `{"r_Mpc": [p.r_phys/Mpc for p in profile], "zeta": [...], "C": [...], "C_bar": [...]}`.
       Returns `None` if `.profile` is empty (only possible if fetched with
       `do_not_populate=True` and neither other mode).
     - `scalars()`: a **pure read** off the eleven parity properties (P3/U3),
       using the exact unsuffixed key vocabulary from design §3.2's
       `scalars()` docstring (`msr_action`, `C_peak`, `C_bar_peak`, `C_min`,
       `compensated`, `type_II`, `r_max_Mpc`, `r_peak_Mpc`, `M_max_solar`,
       `M_peak_solar`, `V_end_downflow`, `N_end_downflow`,
       `noise_field_mean`, …) so DOE/sweep figures never need a per-kind
       branch — the whole point of §7.5.
     - `diagnostics()`: a pure read off `.diagnostics`.
     - `is_spatial()`: `True` only when `self._fidelity == "dense"`.
  2. Implement `SpatialAdapter(GradientCoupledAdapter)` (or fold directly
     into `GradientCoupledAdapter` with the spatial methods simply raising
     when not dense — pick whichever is cleaner given how P5 will use it,
     but document the choice) adding:
     - `y_nodes` — from an `LGLCollocationGrid(n_collocation_points).nodes`
       constructed fresh (cheap, deterministic given the integer) — do not
       require a dense fetch just to expose the node coordinates.
     - `N_grid` — `[v.N.N for v in self.values]`.
     - `field_2d(name)` — `(y_nodes, N_grid, Z[N,y])` for
       `name in {"phi", "pi", "rfield", "rmom"}`, built from `.values`.
       **Must raise (not return `None`)** when `.values` is empty — mirroring
       `GradientCoupledInstanton.field_2d`'s... note there is no existing
       `field_2d` method on the compute-target class itself; this method is
       new, adapter-level, built from `.values` directly. Raise
       `RuntimeError` with a message naming the required fidelity tier.
     - `derived_at_time(N_query)` — thin wrapper over
       `GradientCoupledInstanton.zeta_C_r_at_time(N_query)`; let that
       method's own `RuntimeError` propagate unchanged (don't catch and
       re-raise, don't swallow).
  3. Set `self._fidelity` at construction (from a constructor parameter the
     caller supplies, reflecting which of the three P3 fetch modes was
     used — the adapter cannot infer this reliably from object state alone,
     since an empty `.profile` is ambiguous between "not fetched" and
     "genuinely empty," so the caller must tell it) to one of `"scalars"` /
     `"profile"` / `"dense"`.
- **Constraints:** follow the conventions checklist; plus: every method in
  this file is a pure read of already-persisted parity data — if you find
  yourself computing `C_bar`, a mass, or a classification inline here, stop:
  that is exactly the anti-pattern design §7.5 and brief §5 rule out
  ("Upstream-vs-downstream compute... If a prompt about the adapter starts
  computing C̄ or a mass, it's wrong").
- **Must NOT:** recompute or approximate any of `C_peak`/`C_bar_peak`/
  `M_max`/`M_peak`/`r_max`/`r_peak`/`C_min`/`compensated`/`type_II` — read
  them off the object; must NOT call `field_2d`/`derived_at_time` internally
  from a non-dense adapter instance (`is_spatial()` must gate this at the
  call site in figure code, not inside these methods via a silent `None`
  return — they must raise, per design §3.3's own guard pattern).
- **Acceptance test:** (a) the homogeneous figure functions from P2
  (`time_history`, `noise`, `compaction`, `sweeps`, `doe`), unchanged,
  produce a correctly-overlaid figure when passed
  `[gci_adapter, full_adapter, sr_adapter]` — a named smoke test renders
  each figure family with a `GradientCoupledAdapter` in the list without
  error or exception, for at least one converged GCI test fixture at each
  of the three fidelity tiers. (b) a unit test asserting `field_2d`/
  `derived_at_time` raise `RuntimeError` (not return `None`, not silently
  no-op) when called on a `scalars`- or `profile`-fidelity adapter instance.
- **Decision point:** none new here — the `field_2d`/`derived_at_time`
  raise-not-`None` behaviour is a settled decision (brief §4 P4 "Trap"), not
  open.
