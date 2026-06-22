# Prompt 9 — DOE scalar-summary plots and CSV export

## Context and scope

This prompt makes three related changes to `plot_InstantonSolutions.py`:

1. **Corrects an over-aggressive skip from Prompt 3**: the three axis-sweep
   calls (`_sweep_Ninit_or_Nfinal` ×2, `_sweep_delta_Nstar`) are currently
   skipped entirely when `--sample-grid-csv` is active. They should not be —
   they fetch with `_do_not_populate=True` and extract only scalar columns,
   so they work fine with sparse or scalar-only data. Even a DOE run where
   each (fixed_other, dns) pair has only one or two values along the swept
   axis produces useful plots. Restoring them costs nothing and gives
   the marginal-effect view that's complementary to the global scatter plots
   below.

2. **Adds `--no-store-values` awareness**: when `--no-store-values` is set,
   `_generate_instanton_samples` must be skipped (its fetch calls do not use
   `_do_not_populate=True` for the field-profile and zeta/C-shape plots, so
   they would hit the factory build-time guard from Prompt 4/5 and raise
   `RuntimeError`). Everything else — trajectory plots and sweep plots —
   continues to run unaffected.

3. **Adds DOE scalar-summary output**: when `--no-store-values` is set, add
   a complementary global view of the full parameter space: scatter plots of
   `C̄_max`, `S_MSR`, `M_PBH`, `r_PBH` in `(delta_Nstar, N_init − N_final)`
   space, plus a flat CSV file of all scalar data for downstream GP
   regression / Sobol sensitivity analysis.

**Before writing anything**, read these sections of
`plot_InstantonSolutions.py` in full:

- The Prompt 3 implementation in `run_plots` — specifically: how `csv_grid`
  is built before the trajectory loop, how `traj_combos` is derived per
  trajectory, and the exact guard that currently skips the three sweep calls
  in CSV mode. The project files show a pre-Prompt-3 snapshot; the actual
  repo has the CSV branching. Run `git diff HEAD~N -- plot_InstantonSolutions.py`
  to see the Prompt 3 changes if needed.
- `_sweep_Ninit_or_Nfinal` and `_sweep_delta_Nstar` — confirm they only use
  `_do_not_populate=True` in their fetch calls (no value-row access).
- `_generate_instanton_samples` — confirm the fetch calls that do NOT use
  `_do_not_populate=True` (lines ~1429, ~1457 in the pre-Prompt-3 snapshot;
  exact lines may differ after Prompt 3 edits).
- `_qualifying_action`, `_extract_cf_summary`, `_cf_vectorized_fetch` —
  existing scalar extractors; reuse them, do not reimplement.
- `_instanton_key_payload`, `_cf_key_payload` — payload builders; reuse.
- `_dispatch_plot_work`, `_safe_name`, `_safe_num` — helpers.
- `create_plot_parser` — confirm `--no-store-values` is present (added via
  the shared `create_argument_parser()` in Prompt 8).

## Task

### 1. Restore sweep plots in CSV mode

In `run_plots`, remove the guard that skips the three sweep calls when
`csv_grid` is set. They should always be called.

When `csv_grid` is active, the existing `N_init_array`, `N_final_array`,
`dns_array` from `build_pipeline_inputs` may be empty (if the user supplied
no axis arguments alongside `--sample-grid-csv`). In that case, derive
effective axis arrays from `traj_combos` for the sweep functions only:

```python
if csv_grid is not None:
    eff_N_init  = sorted(set(float(t[0]) for t in traj_combos), key=float)
    eff_N_final = sorted(set(float(t[1]) for t in traj_combos), key=float)
    eff_dns     = sorted(set(float(t[2]) for t in traj_combos), key=float)
    # Re-fetch domain objects by value so the sweep functions have the
    # right typed objects, not raw floats.  Use the same pool.object_get
    # pattern as build_pipeline_inputs.
else:
    eff_N_init  = N_init_array
    eff_N_final = N_final_array
    eff_dns     = dns_array
```

Pass `eff_N_init`, `eff_N_final`, `eff_dns` to the three sweep calls
instead of `N_init_array`, `N_final_array`, `dns_array`. In Cartesian mode
the effective arrays are identical to the originals — no behaviour change.

**Important**: the `if not dns_array:` early-exit guard near the top of
`run_plots` must also become CSV-aware: in CSV mode, exit early only if
`traj_combos` is empty, not if `dns_array` is empty (which may legitimately
be the case when no axis arguments were provided alongside
`--sample-grid-csv`).

Print a one-line note before each sweep call when `csv_grid` is active,
e.g.:
```
   >> --sample-grid-csv active: sweep plots will reflect sparse DOE coverage
```
(Once, before the first sweep call per trajectory, not three times.)

### 2. Gate `_generate_instanton_samples` on `--no-store-values`

In the per-trajectory loop:

```python
if args.no_store_values:
    print(
        "   >> --no-store-values active: skipping per-instanton field and "
        "compaction-profile plots (value rows were not stored)."
    )
else:
    _generate_instanton_samples(
        pool, traj_proxy, potential,
        traj_dir / "instantons", fmt,
        N_init_array=N_init_array,
        N_final_array=N_final_array,
        dns_array=dns_array,
        atol=atol, rtol=rtol,
        max_instanton_samples=max_instanton_samples,
        work_items=work_items,
        cosmo=cosmo, units=units,
    )
```

No changes to `_generate_instanton_samples` itself.

### 3. New function: `_collect_doe_scalar_data`

A driver-side function (not `@ray.remote`) that collects scalar summaries
for every available grid point using vectorized fetches with
`_do_not_populate=True` throughout:

```python
def _collect_doe_scalar_data(
    pool,
    traj_proxy,
    grid_combos,   # list of (N_init_obj, N_final_obj, dns_obj) triples
    cosmo,
    atol,
    rtol,
    units,
) -> list[dict]:
    """
    Returns a list of dicts (one per available grid point) with keys:
        N_init, N_final, delta_Nstar, delta_N   (all float)
        msr_action_full, msr_action_sr           (float or None)
        C_max_full, C_bar_max_full               (float or None)
        M_C_full_solar, M_C_bar_full_solar       (float or None, solar masses)
        r_max_C_full_Mpc, r_max_C_bar_full_Mpc  (float or None, Mpc)
        C_max_sr, C_bar_max_sr                   (float or None)
        M_C_sr_solar, M_C_bar_sr_solar           (float or None)
        r_max_C_sr_Mpc, r_max_C_bar_sr_Mpc      (float or None)

    Grid points where neither FullInstanton nor SlowRollInstanton is
    available are omitted entirely (not included with None values).
    """
```

Implementation: bin by `dns_obj` (the shard key), issue one
`pool.object_get_vectorized("FullInstanton", dns_val, payload_data=[{...,
"_do_not_populate": True}])` per distinct shard key, same for
`"SlowRollInstanton"`. Resolve all refs in a single `ray.get([...])`.
Fetch CF scalars via `_cf_vectorized_fetch` (already uses
`_do_not_populate=True`). Extract scalars via `_qualifying_action` and
`_extract_cf_summary`. Build and return the list of dicts. Note:
`_extract_cf_summary` returns a 12-tuple — see its docstring for the
mapping from tuple indices to physical quantities; match the dict keys
above to those indices precisely.

### 4. New function: `plot_doe_scalar_summary`

A pure plotting function (no Ray decorator) called from within a worker:

```python
def plot_doe_scalar_summary(
    data_points,       # list[dict] from _collect_doe_scalar_data
    potential_name: str,
    output_dir,        # Path
    fmt: str,
    threshold: float = 0.4,
):
```

Produces two figures saved to `output_dir`:

**Figure 1 — `doe_compaction_action.{fmt}`** (2×2, figsize=(12, 10)):

- `[0,0]` — `C̄_max`: scatter of `C_bar_max_full` (circles) and
  `C_bar_max_sr` (triangles), axes `x=delta_Nstar`, `y=delta_N`, colour
  = value. Draw a horizontal line (or iso-value contour if the scatter
  is dense enough) at `threshold`. Points above threshold: red edge;
  below: no edge.
- `[0,1]` — `C_max`: same layout, using `C_max_full` and `C_max_sr`.
- `[1,0]` — `S_MSR`: scatter of `msr_action_full`, log colorbar.
  Include `msr_action_sr` with different marker if any sr values differ
  from full by more than 1%.
- `[1,1]` — threshold boundary: `C_bar_max_full > threshold` → green
  filled circle; else → grey. Overlay sr in matching colours with
  triangle marker. Add legend.

x-axis label: `r"$\delta N_\star$"`.
y-axis label: `r"$\Delta N = N_{\rm init} - N_{\rm final}$"`.
Colourbar labels: `r"$\max \bar{C}$"`, `r"$\max C$"`,
`r"$S_{\rm MSR}$"`.

**Figure 2 — `doe_mass_collapse.{fmt}`** (1×2, figsize=(12, 5)):

- Left — `M_PBH` (solar masses): scatter of `M_C_bar_full_solar`
  (circles) and `M_C_bar_sr_solar` (triangles), x=`delta_Nstar`,
  y=`M_PBH` (log scale), colour = `delta_N`.
- Right — `r_PBH` (Mpc): same structure, using `r_max_C_bar_full_Mpc`
  and `r_max_C_bar_sr_Mpc`.

x-axis: `r"$\delta N_\star$"`.
y-axis labels: `r"$M_{\rm PBH}\,/\,M_\odot$"`,
`r"$r_{\rm PBH}\,/\,{\rm Mpc}$"`.
Colour by `delta_N`, colourbar label
`r"$\Delta N = N_{\rm init} - N_{\rm final}$"`.

For both figures:
- Call `sns.set_theme()` in the worker (not here).
- Call `_provenance_footer(fig)` before `fig.savefig(...)`.
- Call `plt.close(fig)` after saving.
- Skip a figure entirely (no file written, no error) if all data values
  for its panels are `None`.

### 5. New Ray remote worker: `_plot_doe_summary_item`

```python
@ray.remote
def _plot_doe_summary_item(
    data_points, potential_name, output_dir_str, fmt, threshold
):
    sns.set_theme()
    output_dir = Path(output_dir_str)
    plot_doe_scalar_summary(
        data_points, potential_name, output_dir, fmt, threshold
    )
```

### 6. New driver function: `_run_doe_summary_plots`

```python
def _run_doe_summary_plots(
    pool,
    traj_proxy,
    potential,
    traj_dir,        # Path — per-trajectory output directory
    fmt: str,
    grid_combos,     # list of (N_init_obj, N_final_obj, dns_obj)
    cosmo,
    atol,
    rtol,
    units,
    work_items: list,
    threshold: float = 0.4,
):
    print(
        f"   >> Collecting scalar summaries for {len(grid_combos)} "
        f"grid point(s)..."
    )
    data_points = _collect_doe_scalar_data(
        pool, traj_proxy, grid_combos, cosmo, atol, rtol, units
    )
    if not data_points:
        print("   >> No data found — skipping DOE summary plots and CSV.")
        return

    print(
        f"   >> {len(data_points)} point(s) with data; "
        f"queuing DOE summary plots."
    )
    doe_dir = traj_dir / "doe_summary"
    doe_dir.mkdir(parents=True, exist_ok=True)

    # ── Scatter plots ──────────────────────────────────────────────────
    work_items.append((
        _plot_doe_summary_item,
        (data_points, potential.name, str(doe_dir), fmt, threshold),
    ))

    # ── CSV export ────────────────────────────────────────────────────
    import csv
    csv_path = doe_dir / "scalar_data.csv"
    if data_points:
        fieldnames = list(data_points[0].keys())
        with open(csv_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data_points)
        print(f"   >> Scalar data written to {csv_path}")
```

### 7. Wire `_run_doe_summary_plots` into `run_plots`

In the per-trajectory loop, after the `_generate_instanton_samples` gate
from Step 2:

```python
if args.no_store_values:
    grid_combos = traj_combos if csv_grid is not None else list(
        itertools.product(N_init_array, N_final_array, dns_array)
    )
    _run_doe_summary_plots(
        pool=pool,
        traj_proxy=traj_proxy,
        potential=potential,
        traj_dir=traj_dir,
        fmt=fmt,
        grid_combos=grid_combos,
        cosmo=cosmo,
        atol=atol,
        rtol=rtol,
        units=units,
        work_items=work_items,
        threshold=0.4,
    )
```

Use `traj_combos` when `csv_grid is not None`, otherwise fall back to the
full Cartesian product. In normal (Cartesian, full-fidelity) mode this
block is never entered — no change to existing behaviour.

## Acceptance criteria

- [ ] Running with `--sample-grid-csv` and without `--no-store-values`
      against a full-fidelity database: all three sweep-plot functions are
      now called (N-init/, N-final/, delta-Nstar/ sub-folders are created);
      the single "sparse DOE coverage" note is printed once per trajectory.
      `_generate_instanton_samples` runs as before. No DOE scatter or CSV
      produced.
- [ ] Running with `--sample-grid-csv` and without `--no-store-values`
      against a full-fidelity database where some (fixed_other, dns) pairs
      have only one swept value: sweep plots are produced (single-point
      sweeps are valid — `plot_msr_action_sweep` already returns early on
      empty data).
- [ ] Running with `--no-store-values` (with or without `--sample-grid-csv`)
      against a scalar-only database: `_generate_instanton_samples` is
      skipped with the printed note; sweep plots run; DOE scatter plots and
      `scalar_data.csv` are produced under `doe_summary/`.
- [ ] Running without either flag (production mode): byte-for-byte identical
      to the pre-Prompt-9 behaviour. The sweep plots are called with the
      original `N_init_array`, `N_final_array`, `dns_array` — no change.
- [ ] `_collect_doe_scalar_data` returns an empty list (no error) when the
      pool has no data for the requested combos — verified by unit test
      with mock pool returning all-unavailable objects.
- [ ] `plot_doe_scalar_summary` writes no files and raises no exception
      when all data values are `None` (total-failure scenario).
- [ ] The CSV `scalar_data.csv` contains one row per entry in `data_points`,
      with all keys as column headers, and `None` written as the empty
      string (default `csv.DictWriter` behaviour).
- [ ] The two scatter-plot figures are saved under
      `<traj_dir>/doe_summary/`, not at the top-level `--output-dir`.
- [ ] `git diff` touches only `plot_InstantonSolutions.py` and test files.

## Out of scope (do not attempt in this prompt)

- Any changes to `main.py`, factory files, or compute-target files.
- GP fitting or Sobol sensitivity analysis — separate scripts.
- Producing one CSV per model/trajectory rather than per run — the
  per-trajectory structure already handles this via `traj_dir`.

## Commit

One commit, message along the lines of:
`plot_InstantonSolutions: restore sweep plots in CSV mode; add DOE scatter plots and CSV export`
