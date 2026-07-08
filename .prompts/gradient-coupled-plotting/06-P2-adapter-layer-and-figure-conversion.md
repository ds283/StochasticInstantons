### Prompt P2 — Introduce `InstantonAdapter`, convert figure functions to consume it

- **Implements:** design §3.1–§3.2 (base adapter), §3.4 (why overlay is
  free), §6.1 (the reused-as-is figure family).
- **Track / step:** P2
- **Depends on:** P1
- **Files (real paths):**
  - add:  `plotting/adapters/__init__.py`
  - add:  `plotting/adapters/base.py`
  - add:  `plotting/adapters/full.py`
  - add:  `plotting/adapters/slow_roll.py`
  - edit: `plotting/figures/` — this directory does not exist yet; create it
    and move the figure functions listed below into it as part of this
    prompt (design's §2 layout puts figure functions here; P1 deliberately
    left them in `plot_InstantonSolutions.py`, so P2 is where they both move
    *and* get converted, in one step, since moving them unconverted first
    would just be churn with no independent acceptance test).
    - add:  `plotting/figures/time_history.py` (from `plot_instanton_fields`)
    - add:  `plotting/figures/noise.py` (from `plot_noise_profile`)
    - add:  `plotting/figures/compaction.py` (from `plot_zeta_and_compaction`)
    - add:  `plotting/figures/sweeps.py` (from `plot_msr_action_sweep`,
      `plot_compaction_summary`)
    - add:  `plotting/figures/doe.py` (from `plot_doe_scalar_summary`)
  - edit: `plot_InstantonSolutions.py` (re-point at the new figure modules;
    build `FullInstantonAdapter`/`SlowRollInstantonAdapter` instances at the
    call sites instead of passing raw `FullInstanton`/`SlowRollInstanton`/
    `CompactionFunction` objects)
- **Context to read first:** `plot_InstantonSolutions.py`'s
  `plot_instanton_fields`, `plot_noise_profile`, `plot_zeta_and_compaction`,
  `plot_compaction_summary`, `plot_msr_action_sweep`,
  `plot_doe_scalar_summary` in full (these are the functions being
  converted — read every line, since the conversion must preserve the exact
  plotted content, just sourced through the adapter instead of direct
  attribute access); `ComputeTargets/FullInstanton.py`'s `FullInstantonValue`
  class (`phi1`, `phi2`, `P1`, `P2` properties) and `noise_profile_arrays()`;
  `ComputeTargets/SlowRollInstanton.py`'s `SlowRollInstantonValue` class
  (`phi`, `P1` properties — no `phi2`/`P2`, the slow-roll velocity is
  slaved) and its own `noise_profile_arrays()`;
  `ComputeTargets/CompactionFunction.py`'s `_full`/`_slow_roll`-suffixed
  property pairs (`C_peak_full`/`C_peak_slow_roll`, etc.) plus `full_values`/
  `slow_roll_values`; `plotting/provenance.py::_provenance_footer` (from P1)
  — note its exact `getattr(obj, "atol", None)`/`getattr(obj, "rtol", None)`
  introspection (two flat scalar attributes, not a tuple).
- **Assumable interfaces:** the exact attribute vocabulary each solver
  exposes, verified directly against source (design §3.1's table, confirmed
  correct):

  | Concept | `FullInstantonValue` | `SlowRollInstantonValue` |
  |---|---|---|
  | field vs N | `.phi1` | `.phi` |
  | field velocity vs N | `.phi2` | *(absent — slaved)* |
  | response fields | `.P1`, `.P2` | `.P1` |
  | noise σ vs N | `FullInstanton.noise_profile_arrays()` | `SlowRollInstanton.noise_profile_arrays()` |
  | MSR action | `FullInstanton.msr_action` | `SlowRollInstanton.msr_action` |
  | radial ζ/C/C̄ profile | `CompactionFunction.full_values` (list of `CompactionFunctionValue(r, zeta, C, C_bar)`) | `CompactionFunction.slow_roll_values` |
  | scalar summaries | `CompactionFunction.C_peak_full`, `.C_bar_peak_full`, `.r_max_full`, `.r_peak_full`, `.M_max_full`, `.M_peak_full`, `.C_min_full`, `.compensated_full`, `.type_II_full`, `.V_end_downflow_full`, `.N_end_downflow_full` | same names with `_slow_roll` suffix |

  `CompactionFunctionProxy` and `FullInstantonProxy`/`SlowRollInstantonProxy`
  already exist with `.store_id`/`.available`/`.get()` — adapters wrap the
  materialised object, not the proxy.
- **Task:**
  1. In `plotting/adapters/base.py`, implement `InstantonAdapter` per design
     §3.2: `kind`, `display_label`, `line_style`, `available`, `failure`,
     `store_id`, `timestamp`, `coords` (a dict — **populated at
     construction from the query context** — `N_init`, `N_final`,
     `delta_Nstar`, and for GCI `alpha`, `n_collocation_points` — never
     scraped off the wrapped object, so it works for `_do_not_populate`
     fetches per design §3.2's own note), `tolerances -> tuple`, **and, in
     addition to the design's own spec, flat `atol`/`rtol` scalar
     properties** (`self.tolerances[0]`/`[1]`) — added specifically so
     `plotting/provenance.py::_provenance_footer`'s existing
     `getattr(obj, "atol", None)` introspection keeps working unchanged when
     called with an adapter instead of a raw compute-target object (see
     README "Correction 2" — the design's `.tolerances` tuple alone would
     silently degrade every adapter-driven figure's provenance footer, with
     no exception raised to catch the omission). `has_channel(name)`,
     `is_spatial() -> False` (base default; only GCI overrides in P4),
     `time_history(channel)`, `noise_history()`, `radial_profile()`,
     `scalars()`, `diagnostics()`.
  2. In `plotting/adapters/full.py`, implement `FullInstantonAdapter`
     wrapping a `FullInstanton` + (optionally) its paired
     `CompactionFunction`, mapping the table above onto the base protocol —
     `time_history("phi")` reads `.phi1`, `time_history("velocity")` reads
     `.phi2`, `radial_profile()`/`scalars()` read the `_full`-suffixed
     `CompactionFunction` properties/`full_values`.
  3. In `plotting/adapters/slow_roll.py`, implement `SlowRollInstantonAdapter`
     analogously, with `time_history("velocity")` returning `None` (the
     channel is absent — see `has_channel`) and `radial_profile()`/`scalars()`
     reading the `_slow_roll`-suffixed properties/`slow_roll_values`.
  4. Move the five figure functions into `plotting/figures/` as listed above,
     and convert each to accept `adapters: list[InstantonAdapter]` in place
     of its current `(fi, sri)`-shaped parameters, looping per design §3.4:
     `for a in adapters: if not (a.available and not a.failure): continue; ...`.
     Preserve the exact visual output for the two-adapter case (a `FullInstantonAdapter`
     + `SlowRollInstantonAdapter` list must draw the same lines/markers/labels
     the current `(fi, sri)`-parameter version draws) — this is what the
     re-diff in Acceptance test checks.
  5. Update `plot_InstantonSolutions.py`'s call sites to construct
     `FullInstantonAdapter(fi, cf)`/`SlowRollInstantonAdapter(sri, cf)`
     instead of passing `fi`/`sri`/`cf` directly, and pass `[full_adapter, sr_adapter]`
     into the (now-adapter-consuming) figure functions.
- **Constraints:** follow the conventions checklist; plus: no figure function
  may branch on `kind` — only on `has_channel(...)`/whether a `scalars()` key
  is `None` (this is design's settled decision #2, do not reopen it, and it
  is exactly what makes P4's gradient adapter free downstream).
- **Must NOT:** change `plotting/provenance.py` or `plotting/annotations.py`
  in this prompt (P1 already landed them; if the annotation helpers need
  generalising to loop over `adapters` instead of a hard-coded "Full"/"SR"
  pair, that is explicitly deferred — do not do it here, since none of the
  five figures in this prompt's scope call `_add_cf_annotation`/
  `_cf_annotation_text` directly; check this against the actual call graph
  before assuming otherwise); must NOT add a `GradientCoupledAdapter` or
  `SpatialAdapter` (P4's job — depends on U3 landing first); must NOT change
  any numeric formula anywhere.
- **Acceptance test:** re-run the same golden-run comparison from P1
  (`tests/test_plot_extraction_golden.py`'s database + config), and assert
  the newly-adapter-fed figures are byte-identical to the P1 golden output.
  Also add a unit test asserting `InstantonAdapter.coords` is populated
  correctly when constructed against a `_do_not_populate=True`-fetched
  `FullInstanton` (no dense `_values`, but `coords` must still report
  `N_init`/`N_final`/`delta_Nstar` correctly, since it's taken from the
  query context, not scraped off the object).
- **Decision point:** none — the adapter's exact grid-`coords`-from-query-
  context requirement is a settled decision (design §3.2, brief §3 item 2's
  "Trap"), not open.
