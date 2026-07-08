### Prompt P8 — `plot_GradientCoupledSolutions.py`: new driver + `--compare-with`

- **Implements:** design §10 in full, with the CLI-flag list corrected per
  this prompt set's `00-README.md` ("Correction 1" — no new α/n_colloc
  low/high/samples/values quartet, no `build_gci_inputs`).
- **Track / step:** P8
- **Depends on:** P4 (minimum). Wires in whichever of P5a/P5b/P6/P7 have
  already landed; does not require all of them first — a driver that only
  dispatches the figure families that exist so far is a legitimate
  incremental state. Do not wire a `--movies` flag whose figure functions
  don't exist yet (P5b).
- **Files (real paths):**
  - add:  `plot_GradientCoupledSolutions.py`
- **Context to read first:** `plot_InstantonSolutions.py`'s `create_plot_parser`
  and `run_plots` in full (this new file mirrors that structure closely —
  read both completely, not just the signatures); `config/pipeline_setup.py::build_pipeline_inputs`
  (already returns `n_collocation_points_array`/`alpha_regularization_array`
  — see Constraints); `plotting/adapters/gradient.py` (P4);
  `plotting/figures/*.py` (whichever of P5a/P5b/P6/P7/the P2-converted
  homogeneous figures have landed at the time this prompt is executed —
  check the actual file tree, don't assume the full set exists).
- **Assumable interfaces:**
  - `build_pipeline_inputs(pool, units, args)` returns
    `n_collocation_points_array`/`alpha_regularization_array` already (no
    new function needed to obtain these — see Constraints).
  - `plotting/fetch.py::fetch_over_grid` and the `_render_item` generic
    dispatcher (P1).
  - `GradientCoupledAdapter`/`SpatialAdapter` (P4), `FullInstantonAdapter`/
    `SlowRollInstantonAdapter` (P2).
- **Task:**
  1. `create_plot_parser()`-equivalent for this driver: reuse
     `config.argument_parser.create_argument_parser()` exactly as
     `plot_InstantonSolutions.py` does (same rationale — same `--config`
     YAML, same reconstructed grid), then add a driver-local argument group
     with:
     - `--output-dir`, `--format`, `--max-trajectories`,
       `--max-combinations`, `--max-instanton-samples` (mirroring the
       existing homogeneous driver's flags, same defaults/semantics).
     - `--movies` (`action="store_true"`, default off) — only meaningful
       once P5b exists; if it doesn't yet, still add the flag (inert) so
       P5b's later landing doesn't need a second CLI-surface prompt, but
       do not dispatch any work item for it yet.
     - `--movie-format {mp4,gif}` (default `gif`, per P5b's decision).
     - `--compare-with` (`nargs="*"`, `choices=["full","slow-roll"]`,
       default `[]`) — when non-empty, the detailed and sweep passes
       additionally fetch the matching `FullInstanton`/`SlowRollInstanton`
       (+`CompactionFunction`) at each sampled grid point, wrap as adapters,
       and pass the combined list into the shared figure functions.
     - `--spatial-samples` (int, default some small number, e.g. 5) — how
       many grid points get the heavy `(y,N)` treatment (heatmaps/slices/
       movies) out of the full sampled set.
     - `--time-resolved-derived` (`action="store_true"`, default off) —
       enables the ζ(r)/C(r)-at-selected-N and movie-through-N figures
       (design §6.3), since these are recompute-heavy even with the
       `ExtractionCache`.
     **Do not** add `--n-collocation-low/high/samples/values` or
     `--alpha-low/high/samples/values` — the existing
     `--n-collocation-points`/`--alpha-regularization` list flags (already
     parsed by `create_argument_parser()`) are what both `main.py` and this
     driver consume; adding a second, independent way to specify these axes
     for plotting only would let the plotted sweep silently diverge from
     what was actually computed (see `00-README.md`).
  2. `run_plots`-equivalent, mirroring the homogeneous driver's structure:
     - `build_pipeline_inputs` (+ read the already-present
       `n_collocation_points_array`/`alpha_regularization_array` — no new
       minting call), fetch trajectories, cosmo, diffusion model — same
       calls as the homogeneous driver, since these are shared concepts.
     - **Scalar+diagnostics pass** (cheap tier) over the full
       `(N_init, N_final, delta_Nstar, alpha, n_collocation_points)` grid →
       DOE figures (P2-converted `doe.py`, fed `GradientCoupledAdapter`
       instances), diagnostics figures (P7, if landed), `scalar_data.csv`,
       `diagnostics_data.csv`.
     - **Sweep passes** over each axis
       (`N_init`, `N_final`, `delta_Nstar`, `alpha`, `n_collocation_points`)
       → msr/compaction summaries (P2's `sweeps.py`, GCI now included as a
       pure read per U3/P4) + the stability overlays (P6, if landed).
     - **Detailed-sample pass** (`--max-instanton-samples`, evenly sampled
       via `plotting/sampling.py::_evenly_sample`) → `time_history`, `noise`,
       `compaction` (P2's figures, GCI-fed), and — for up to
       `--spatial-samples` of that sampled subset — the spatial heatmaps/
       slices (P5a, if landed); movies only if `--movies` **and** P5b has
       landed (check for the movie functions' existence rather than
       assuming).
     - Drain the work queue exactly as `run_plots` does today: the same
       `(remote_fn, args)` work-item convention and terminal
       `RayWorkPool(..., store_results=False)` drain (P1).
  3. `--compare-with` wiring: when non-empty, for each sampled grid point in
     the detailed and sweep passes, additionally fetch the matching
     `FullInstanton`/`SlowRollInstanton` (+`CompactionFunction`) via
     `plotting/fetch.py::fetch_over_grid`, wrap as adapters, and extend the
     adapter list passed into the shared figure functions — no new
     plotting code, per design §10's own framing ("producing the overlaid
     figures with zero new plotting code").
- **Constraints:** follow the conventions checklist; plus: this driver's
  `run_label` construction should mirror the homogeneous driver's (db
  filename, config, mode flags), extended with the fidelity tier
  (`[scalars-only]`/`[full-fidelity]`/`[with-movies]`) per design §9.
- **Must NOT:** modify `plot_InstantonSolutions.py` in this prompt (it stays
  the homogeneous-only driver, byte-identical to its P1/P2 golden runs);
  must NOT add any new CLI flag or helper for minting the α/n_colloc sweep
  values (see Task item 1); must NOT dispatch a figure family whose
  functions don't exist yet in the current tree.
- **Acceptance test:** an end-to-end run on `quadratic-minimal.yaml`
  (extended with a small `--n-collocation-points`/`--alpha-regularization`
  list and `--targets gradient`) produces the full output tree without
  error; a second run with `--compare-with full,slow-roll` produces
  overlaid figures (assert, e.g., that the resulting `time_history` PNG/PDF
  for a compared grid point contains more than one line-style/label in its
  legend, or — preferably — assert on the adapter list length passed into
  the figure function via a unit test on the wiring code itself, rather than
  parsing rendered image content).
- **Decision point:** none new — the CLI-flag correction is documented above
  and in `00-README.md`, not an open question.
