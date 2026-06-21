# Prompt 3 — `--sample-grid-csv` in `plot_InstantonSolutions.py`

## Context

`plot_InstantonSolutions.py` reuses `config.argument_parser.create_argument_parser()`
(see `create_plot_parser()`), so it **already accepts** `--sample-grid-csv`
as a CLI flag after Prompt 2 — but it does nothing with it yet. The script
currently gets its axis arrays from `build_pipeline_inputs(pool, units, args)`
and uses them in two structurally different ways:

1. **`_generate_instanton_samples`** (per-trajectory): builds
   `all_combos = list(itertools.product(N_init_array, N_final_array, dns_array))`,
   evenly samples down to `--max-instanton-samples`, and emits one
   per-combination plot sub-folder under `instantons/`. This generalises
   cleanly to an explicit list of triples — it already just wants "some
   list of `(N_init, N_final, delta_Nstar)` combinations to plot," and
   currently builds that list via Cartesian product only because that's
   the only grid shape that's existed until now.

2. **`_sweep_Ninit_or_Nfinal`** and **`_sweep_delta_Nstar`**: these sweep
   *one* axis while holding the other two fixed at specific shared values
   (`combos = list(itertools.product(fixed_other_array, dns_array))`, then
   for each `(other_val, dns_val)` pair, fetch **every** value of the swept
   array at that fixed point). This fundamentally requires dense axis
   coverage — for a given `(other_val, dns_val)`, every point along the
   swept axis must actually exist in the database. A sparse / space-filling
   CSV design (e.g. Latin hypercube over `(N_init, N_final, delta_Nstar)`)
   will essentially never produce two points sharing two fixed coordinates
   with the third varying densely, so these sweep plots **do not
   generalise** to CSV-grid mode and should be skipped outright when it's
   active, with a clear message explaining why — not silently produce
   near-empty or misleading plots.

**Read both sweep functions and `_generate_instanton_samples` in full
before starting** (lines ~1006–1430 in the current file) to confirm this
characterisation is accurate and to find anything not captured above.

## Task

### 1. Grid construction in `run_plots`

Where `run_plots` currently does:

```python
inputs = build_pipeline_inputs(pool, units, args)
atol, rtol = inputs["atol"], inputs["rtol"]
N_init_array = inputs["N_init_array"]
N_final_array = inputs["N_final_array"]
dns_array = inputs["dns_array"]
```

Branch on whether `args.sample_grid_csv` is set (mirror whatever
precedence/validation logic Prompt 2 implemented in
`config.grid_builder.build_instanton_grid` for `main.py` — reuse that
function or its CSV-parsing helper directly rather than re-deriving the
precedence rules here; if `build_instanton_grid` is structured in a way
that's awkward to reuse from the plot script, say so and propose the
smallest refactor that lets both call sites share it, rather than
duplicating the validation logic a second time).

- **Cartesian mode (default, no `--sample-grid-csv`)**: behaviour is
  unchanged — `N_init_array`/`N_final_array`/`dns_array` as today, fed into
  `_generate_instanton_samples`, `_sweep_Ninit_or_Nfinal` (×2),
  `_sweep_delta_Nstar` exactly as now.
- **CSV mode**: obtain the explicit `(model_idx, N_init, N_final,
  delta_Nstar)` tuples via `config.grid_builder.build_grid_from_csv` (the
  same function `main.py` uses), filtered to the tuples matching the
  current trajectory's `model_idx` inside the existing `for traj in
  traj_list:` loop (each trajectory in this script corresponds to one
  entry in `model_list` — confirm the index correspondence by inspection of
  how `traj_list`/`selected_models` are built earlier in `run_plots`, don't
  assume).

### 2. `_generate_instanton_samples`: accept pre-built combos

Add an optional parameter (e.g. `combos: Optional[list] = None`) so that
when explicit triples are available (CSV mode), the function uses them
directly instead of recomputing `itertools.product(N_init_array,
N_final_array, dns_array)`. When `combos` is `None` (default / Cartesian
mode), behaviour is exactly as today. Don't fork this into two separate
functions — the rest of the function body (vectorized fetch, evenly
sampling down to `max_instanton_samples`, per-combination plot emission) is
identical either way and should stay that way.

### 3. Skip the axis-sweep plots in CSV mode

In `run_plots`, when `args.sample_grid_csv` is set, do not call
`_sweep_Ninit_or_Nfinal` or `_sweep_delta_Nstar` at all. Print a one-line
explanation per trajectory (or once, before the trajectory loop — your
call) along the lines of:

```
>> --sample-grid-csv active: skipping N-init/N-final/delta-Nstar axis
   sweep plots (require dense axis coverage); only instantons/ will be
   generated.
```

Do not attempt to make these functions "work" against a sparse grid by,
e.g., only sweeping over whatever subset of the swept axis happens to be
present — that would silently produce sweep plots with arbitrary, possibly
single-point "sweeps," which is worse than not producing them.

### 4. `--output-dir` / file naming

No change needed here unless you find a collision risk — `instantons/`
sub-folder naming is already keyed on the actual `(N_init, N_final,
delta_Nstar)` float values (`Ninit=..._Nfinal=..._dNstar=...`), which
works identically whether those values came from an axis grid or a CSV.

## Acceptance criteria

- [ ] Running `plot_InstantonSolutions.py` with no `--sample-grid-csv`
      produces byte-identical output file lists (not necessarily byte-
      identical plot *contents*, but identical sets of generated files
      and folder structure) to the current `main` branch, for an existing
      database. Verify this against the same database used for Prompt 2's
      "identical grid" check if practical, or a small synthetic one.
- [ ] Running with `--sample-grid-csv` produces an `instantons/` folder
      with one sub-folder per CSV triple (up to `--max-instanton-samples`,
      evenly sampled as before), correctly attributed to the right
      trajectory/model.
- [ ] Running with `--sample-grid-csv` does **not** create `N-init/`,
      `N-final/`, or `delta-Nstar/` sweep sub-folders, and prints a clear
      explanatory message instead.
- [ ] `_generate_instanton_samples`'s existing Cartesian-mode behaviour
      (no `combos` argument passed) is unit-tested or otherwise verified
      unchanged — in particular the evenly-sampling-by-index logic and the
      vectorized fetch grouping by `dns_val`.
- [ ] The CSV-mode triple-filtering-by-`model_idx` is correct — verify with
      a small multi-model synthetic case (≥2 models, CSV triples for both)
      that each trajectory only receives its own triples.
- [ ] `git diff` is limited to `plot_InstantonSolutions.py` and, only if
      genuinely necessary to make `build_instanton_grid`/
      `build_grid_from_csv` cleanly reusable from both call sites, a small
      refactor inside `config/grid_builder.py` (state explicitly in the
      commit message if you touch it, and why).

## Out of scope (do not attempt in this prompt)

- The scalars-only storage mode / `_do_not_populate` build-time guard for
  `FullInstanton`, `SlowRollInstanton`, `CompactionFunction`.
- Any attempt to make the axis-sweep plots work against sparse designs —
  explicitly rejected above.
- Generating sample-grid CSVs themselves.

## Commit

One commit, message along the lines of:
`plot_InstantonSolutions: support --sample-grid-csv (instantons/ only, sweeps skipped)`
