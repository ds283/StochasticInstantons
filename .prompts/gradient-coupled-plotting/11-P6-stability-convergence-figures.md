### Prompt P6 — Stability / convergence figures (α / n_collocation overlays)

- **Implements:** design §6.4 in full, §3.4 (overlay mechanism it reuses).
  **Note:** this prompt's Task departs from design §7.4/§10's literal text
  on how the swept α/n_colloc axes are obtained — see the correction in this
  prompt set's `00-README.md` ("Correction 1"). The figures and their
  scientific content are unchanged from the design; only where the axis
  *values* come from is corrected.
- **Track / step:** P6
- **Depends on:** P4
- **Files (real paths):**
  - add:  `plotting/figures/stability.py`
- **Context to read first:** `config/pipeline_setup.py::build_pipeline_inputs`
  in full — **read this before writing anything**, since its actual current
  return dict already contains `n_collocation_points_array` and
  `alpha_regularization_array`, built from the existing
  `--n-collocation-points`/`--alpha-regularization` CLI flags
  (`config/argument_parser.py`); `plotting/fetch.py::fetch_over_grid` (P1);
  `plotting/adapters/gradient.py::GradientCoupledAdapter.scalars()` (P4).
- **Assumable interfaces:**
  - `build_pipeline_inputs(pool, units, args)["n_collocation_points_array"]`
    — list of persisted `n_collocation_points` objects, exactly the values
    the compute pipeline (`main.py`) actually used to populate the
    database for this run's `--config`.
  - `build_pipeline_inputs(pool, units, args)["alpha_regularization_array"]`
    — likewise for `alpha_regularization`.
  - `GradientCoupledAdapter.scalars()` (P4) — a pure-read flat dict
    including `C_peak`, `msr_action`, `r_max_Mpc`, `M_max_solar`, etc.
  - `plotting/fetch.py::fetch_over_grid(pool, class_name, shard_key_of, key_payload_of, items, do_not_populate=True)`
    (P1) — the generic vectorized-fetch helper; use it (not a new hand-rolled
    fetch loop) to pull `GradientCoupledInstanton` records across the
    n_colloc/α axis at fixed `(N_init, N_final, delta_Nstar)`.
- **Task:**
  1. **n_collocation convergence overlay.** Fix `(N_init, N_final, delta_Nstar, alpha)`,
     sweep `n_collocation_points` over every value in
     `inputs["n_collocation_points_array"]` (i.e. exactly what was actually
     computed for this database — do not introduce any new CLI flag or
     grid-generation helper to produce a different set of values; see
     Constraints below). Fetch the matching `GradientCoupledInstanton`
     record at each `n`, wrap each as a `GradientCoupledAdapter`, and:
     - overlay ζ(r)/C(r) (via `radial_profile()`) and the core-node history
       (via `time_history("phi")`) across the swept `n` values on one axis
       each, reusing the exact `for a in adapters: ...` overlay loop pattern
       from P2/P4 (design §3.4) — no new overlay mechanism.
     - report `max|Δ|` between successive resolutions (sorted by `n`) as an
       inset/annotation, as spectral-convergence evidence.
  2. **α overlay.** Identical structure, fixing `(N_init, N_final, delta_Nstar, n_collocation_points)`
     and sweeping `alpha` over `inputs["alpha_regularization_array"]`, showing
     the persisted scalars (`C_peak`, `r_max`, `M_max`, …) and the profile
     are insensitive across the α range actually computed.
  3. **Plateau panel.** A scalar-vs-axis panel (`C_peak`, `msr_action`,
     `r_max`, `M_max` vs. `n_collocation_points`, and the same vs. `alpha`,
     other axes fixed) reading `.scalars()` directly off each fetched
     adapter — these are cheap-tier reads (design §4's cost table), so this
     panel costs nothing beyond `_do_not_populate=True` fetches already
     needed for items 1–2's scalar overlays (the ζ(r)/C(r) profile overlays
     additionally need a `profile_only` fetch, per P3 — use that mode for
     those, and `do_not_populate=True` for the plateau panel alone).
  4. If, for a given `(N_init, N_final, delta_Nstar)` grid point, fewer than
     two `n_collocation_points`/`alpha_regularization` values were actually
     computed (e.g. a config that only ran one resolution), skip that
     overlay/plateau figure for that grid point rather than rendering a
     single-point "sweep" — check `len(inputs["n_collocation_points_array"]) >= 2`
     (respectively `alpha_regularization_array`) before dispatching the
     corresponding figure's work item.
- **Constraints:** follow the conventions checklist; plus (**the corrected
  requirement, see `00-README.md`**): do **not** add any new CLI flag
  (`--n-collocation-low/high/samples/values` or `--alpha-low/high/samples/values`),
  and do **not** add a `build_gci_inputs` function or any other new
  input-minting helper. The swept axis values are read directly from
  `build_pipeline_inputs`'s existing, already-shared return dict — this is
  what guarantees the plotted sweep always matches what was actually
  computed and persisted for this `--config`, with zero risk of the
  plot-only axis silently drifting from the compute-time axis. `delta_Nstar`
  remains the shard key throughout; α and n_colloc are ordinary (non-shard)
  axes in every `fetch_over_grid` call.
- **Must NOT:** add any new CLI argument to `config/argument_parser.py`;
  must NOT add a `build_gci_inputs`/`gci_pipeline_setup.py`-style new
  minting function; must NOT make `delta_Nstar` a swept axis in this
  prompt's figures (it is the shard key — every call here fixes it); must
  NOT recompute any scalar shown on the plateau panel — read `.scalars()`.
- **Acceptance test:** a named smoke test that, given a fixture database
  with at least two `n_collocation_points` values and at least two `alpha`
  values computed at a shared `(N_init, N_final, delta_Nstar)`, renders the
  n_colloc overlay, the α overlay, and both plateau panels without error,
  and asserts the reported `max|Δ|` inset is present and finite; and asserts
  all four figures are silently skipped (no exception, no file) when only
  one value of the relevant axis exists for a grid point.
- **Decision point:** none — the axis-sourcing question resolved above is a
  correction to a factual premise, not an open design choice (see
  `00-README.md` "Correction 1").
