# Prompt 19 — Wire `GradientCoupledInstanton` into the `main.py` driver

**Feature:** `main-driver-integration`
**Depends on:** the completed `GradientCoupledInstanton` compute target
(`ComputeTargets/GradientCoupledInstanton/*`) and its factory
(`Datastore/SQL/ObjectFactories/GradientCoupledInstanton.py`), both already
implemented and validated.
**Scope:** driver/configuration layer only. No changes to solver physics,
`Numerics/`, or the compute-target internals themselves.

## Context

`main.py` currently drives a single pipeline: `InflatonTrajectory` →
`FullInstanton` + `SlowRollInstanton` → `CompactionFunction`. We call this the
**homogeneous** branch (matches the terminology in `NUMERICAL_SCHEMES.md` §4.1).
`GradientCoupledInstanton` — the **gradient** branch (§4.2) — is fully
implemented but not dispatched from `main.py` anywhere.

The two branches are *siblings*, not sequential stages: `GradientCoupledInstanton`
depends only on `InflatonTrajectory` (Stage 1), and internally performs the
work that the homogeneous branch splits across `FullInstanton`/
`SlowRollInstanton` + `CompactionFunction` — including the ζ(r)/C(r) radial
profile extraction. It shares the same `(N_init, N_final, delta_Nstar)` grid
axes as the homogeneous branch, but needs two additional solver parameters
(`n_collocation_points`, `alpha_regularization`) that the homogeneous branch
does not.

Users need to be able to run the homogeneous branch alone (today's default,
unchanged), the gradient branch alone, or both together on the same grid (for
computing the corrections the gradient-coupled model induces relative to the
homogeneous approximation).

## Required changes

### 1. `InflationConcepts/alpha_regularization.py` — tighten the validity constraint

`alpha = 0` produces `Delta_s = 0` at the initial step, which is a
singularity of `Numerics/OnionCoordinate.py`'s coordinate map. This was
previously (incorrectly) treated as a valid, well-defined value. Fix:

- Change the guard from `if alpha < 0` to `if alpha <= 0`, with an updated
  `ValueError` message, e.g. `f"alpha_regularization: alpha must be > 0 "
  f"(alpha == 0 is a singularity of Delta_s at N_init), got {alpha!r}"`.
- Update the class docstring: remove the paragraph claiming `alpha == 0` is
  valid; replace with a short note that `alpha == 0` is rejected because it
  makes `Delta_s(N_init) = 0`, singular in the onion coordinate map (cross-
  reference `Numerics/OnionCoordinate.py`'s `delta_s()`).
- Search the codebase for any other place that constructs `alpha_regularization`
  directly (tests, example scripts, other prompts) and confirm none pass
  `alpha=0.0`; flag any that do rather than silently changing them.

### 2. `config/argument_parser.py` — CLI surface

**Remove** `--no-store-gradient-instanton-values` entirely (currently defined,
unused). Its behaviour is folded into the existing `--no-store-values` flag
(point 4 below); update that flag's `help=` text to describe both branches:
homogeneous → unified single-task pipeline, scalar-only FI/SRI/CF; gradient →
`GradientCoupledInstanton.set_store_full_values(False)`, no task-merging
needed since extraction/scale-assignment already run inside the one Ray task
per grid point.

**Add**, in a new argument group `"Branch selection"`:
```python
branch = parser.add_argument_group("Branch selection")
branch.add_argument(
    "--targets",
    nargs="*",
    default=["homogeneous"],
    choices=["homogeneous", "gradient"],
    help=(
        "Which instanton branch(es) to compute for each grid point. "
        "'homogeneous' runs FullInstanton + SlowRollInstanton (+ "
        "CompactionFunction, unless cut short by --stop-after). "
        "'gradient' runs GradientCoupledInstanton (onion model). Give both "
        "to run them on the same parameter grid, e.g. for comparing the "
        "corrections the gradient-coupled model induces relative to the "
        "homogeneous approximation. Default: homogeneous only (preserves "
        "existing behaviour)."
    ),
)
```

**Add**, in a new argument group `"Gradient-coupled instanton"`:
```python
def _positive_float(x):
    v = float(x)
    if v <= 0:
        raise configargparse.ArgumentTypeError(
            f"--alpha-regularization values must be > 0 "
            f"(alpha == 0 is a singularity of Delta_s at N_init), got {v!r}"
        )
    return v

gci = parser.add_argument_group("Gradient-coupled instanton")
gci.add_argument(
    "--n-collocation-points",
    nargs="*",
    type=int,
    default=[33],
    help=(
        "Number of LGL collocation points for the onion-model spatial grid. "
        "Accepts multiple values to sweep several n_max in one run (crossed "
        "against the N_init/N_final/delta_Nstar grid and against "
        "--alpha-regularization). Default: [33]."
    ),
)
gci.add_argument(
    "--alpha-regularization",
    nargs="*",
    type=_positive_float,
    default=[0.01],
    help=(
        "Onion-coordinate horizon-regularization parameter alpha (must be "
        "> 0; alpha == 0 is a singularity of Delta_s at N_init). Accepts "
        "multiple values to sweep in one run (crossed against the grid and "
        "--n-collocation-points). Default: [0.01]."
    ),
)
```
Confirm `configargparse.ArgumentTypeError` is the right exception type for
this parser (fall back to `argparse.ArgumentTypeError` if not re-exported —
check what `configargparse` actually re-exports before assuming).

**Extend** `--drop`'s `choices` list (used in two places: this file and
wherever else the same literal choices list is duplicated — search for it)
to include `"gradient-coupled-instanton"`.

**Leave `--stop-after` unchanged** (same choices, same semantics) — it only
ever gates the homogeneous branch's internal stages. In `main.py`, if
`--stop-after` is given and `"homogeneous"` is not in `args.targets`, print a
warning that it will have no effect (don't error).

### 3. `Datastore/SQL/Datastore.py` — cascade-drop support

Add to `_drop_actions`:
```python
"gradient-coupled-instanton": [
    "GradientCoupledInstantonValue",
    "GradientCoupledInstantonProfile",
    "GradientCoupledInstanton",
],
```
Insert `"gradient-coupled-instanton"` into `_drop_order` **before**
`"inflaton-trajectory"** (it has a FK on `trajectory_serial`, so must be
dropped before the trajectory table it depends on) — position relative to
`compaction-function`/`slow-roll-instanton`/`full-instanton` doesn't matter
since there's no FK relationship between those tables and
`GradientCoupledInstanton`. Suggested:
```python
_drop_order = [
    "compaction-function", "slow-roll-instanton", "full-instanton",
    "gradient-coupled-instanton", "inflaton-trajectory",
]
```

### 4. `config/pipeline_setup.py` — mint the new solver-parameter objects

In `build_pipeline_inputs()`, mint `n_collocation_points` and
`alpha_regularization` objects the same way `N_init_array`/`N_final_array`/
`dns_array` are minted (one `pool.object_get(...)` call per list, using
`payload_data=[{"n_collocation_points": v} for v in args.n_collocation_points]`
and `payload_data=[{"alpha": v} for v in args.alpha_regularization]` — check
the exact constructor kwarg names against
`InflationConcepts/n_collocation_points.py` and
`InflationConcepts/alpha_regularization.py` before writing this). Add these
as `ray.get([...])` entries alongside the existing ones, and add two new keys
to the returned dict: `"n_collocation_points_array"`, `"alpha_regularization_array"`.
Print a summary line for each (reuse the existing `_build_grid`-style
formatting helper if it fits, or a simpler one-liner — these are short
explicit lists, not `low/high/samples` continuous grids, so `_build_grid`
itself doesn't apply directly).

### 5. `config/grid_builder.py` — gradient-branch grid

Add:
```python
def build_gradient_grid(base_grid, n_collocation_points_array, alpha_regularization_array) -> list:
    """
    Cross the shared (model_idx, N_init, N_final, delta_Nstar) grid against
    the n_collocation_points and alpha_regularization axes, for the gradient
    branch only. Returns a list of
    (base_item, n_collocation_points_obj, alpha_regularization_obj) tuples,
    where base_item is one of base_grid's own (model_idx, N_init, N_final,
    delta_Nstar) tuples -- unchanged, so existing key_fields/full_payload/
    shard_key_of closures over base_item continue to work unmodified.
    """
    return [
        (item, ncp, alpha)
        for item in base_grid
        for ncp in n_collocation_points_array
        for alpha in alpha_regularization_array
    ]
```

### 6. `main.py` — branch dispatch

**a. Generalize `_run_instanton_queue`** to accept an optional
`no_store_values: bool = False` parameter. When `True`, wrap the persist
handler so it calls `obj.set_store_full_values(False)` before
`pool.object_store(obj)`. All three compute targets (`FullInstanton`,
`SlowRollInstanton`, `GradientCoupledInstanton`) already implement
`set_store_full_values`, so this generalization is safe across all callers.
Existing calls for `FullInstanton`/`SlowRollInstanton` keep their current
(implicit `no_store_values=False`) behaviour unchanged — don't wire
`args.no_store_values` into those two calls; they're only ever reached
today when the homogeneous branch is *not* running in unified mode, and
changing that is out of scope for this prompt.

**b. Restructure `run_all_pipelines()`** so Stage 1 (trajectory) remains
unconditional and shared, and Stages 2–4 (homogeneous) and the new Stage G
(gradient) become independent, conditionally-executed blocks:

```python
if "homogeneous" in targets:
    # existing Stage 2/3/4 logic, completely unchanged, including the
    # existing --no-store-values unified-pipeline branch and --stop-after
    # handling
    ...
else:
    print("\n** Skipping homogeneous branch (--targets excludes 'homogeneous')")

if "gradient" in targets:
    _run_gradient_branch(
        pool=pool, base_grid=grid,
        n_collocation_points_array=n_collocation_points_array,
        alpha_regularization_array=alpha_regularization_array,
        traj_proxies=traj_proxies, cosmo=cosmo, atol=atol, rtol=rtol, dm=dm,
        samples_per_N=samples_per_N, no_store_values=no_store_values,
    )
else:
    print("\n** Skipping gradient branch (--targets excludes 'gradient')")
```
Thread `targets: List[str]` through as a new parameter of
`run_all_pipelines()` (from `args.targets`), alongside the existing
`no_store_values` parameter — note `no_store_values` now applies to
*whichever* branches are selected, per the CLI redesign in point 2.

**c. New helper `_run_gradient_branch(...)`**, structured like
`_run_instanton_queue` but with GCI-specific key construction:

```python
def _run_gradient_branch(
    pool, base_grid, n_collocation_points_array, alpha_regularization_array,
    traj_proxies, cosmo, atol, rtol, dm, samples_per_N, no_store_values,
):
    gradient_grid = build_gradient_grid(
        base_grid, n_collocation_points_array, alpha_regularization_array
    )
    n_base = len(base_grid)
    n_ncp = len(n_collocation_points_array)
    n_alpha = len(alpha_regularization_array)
    print(
        f"\n   >> gradient branch: {n_base} base grid point(s) x "
        f"{n_ncp} n_collocation_points value(s) x {n_alpha} alpha_regularization "
        f"value(s) = {len(gradient_grid)} gradient instanton combination(s)"
    )

    def key_fields(item) -> dict:
        base_item, ncp_obj, alpha_obj = item
        model_idx, N_init_obj, N_final_obj, dns_obj = base_item
        return dict(
            trajectory=traj_proxies[model_idx],
            N_init=N_init_obj, N_final=N_final_obj, delta_Nstar=dns_obj,
            n_collocation_points=ncp_obj, alpha_regularization=alpha_obj,
            atol=atol, rtol=rtol, cosmo=cosmo, diffusion_model=dm, tags=[],
        )

    def full_payload(item) -> dict:
        # Reuse the SAME N-grid construction as the homogeneous branch's own
        # full_payload() (shared rational grid at 1/samples_per_N, plus the
        # exact N_total endpoint) -- factor this out into a shared helper
        # rather than duplicating the stepping logic; both branches must use
        # an identical N_sample convention for any downstream comparison to
        # be meaningful.
        ...

    def shard_key_of(item):
        base_item, _, _ = item
        return base_item[3]  # delta_Nstar

    _run_instanton_queue(
        pool=pool, cls_name="GradientCoupledInstanton", task_list=gradient_grid,
        key_fields=key_fields, full_payload=full_payload, shard_key_of=shard_key_of,
        label_builder=lambda obj: (
            f"GradientCoupledInstanton(dNstar={float(obj.delta_Nstar):.4g}, "
            f"Ninit={float(obj.N_init_value):.4g}, Nfinal={float(obj.N_final_value):.4g}, "
            f"n_colloc={int(obj.n_collocation_points_value)}, "
            f"alpha={float(obj.alpha_regularization_value):.4g})"
        ),
        store_handler=_default_store_handler,
        title="STAGE G: GRADIENT-COUPLED (ONION MODEL) INSTANTONS",
        no_store_values=no_store_values,
    )
```
**Factor out the shared N-grid construction** from the homogeneous branch's
existing `full_payload()` closure (the `step = 1.0 / samples_per_N` /
`shared_points` / exact-endpoint logic) into a standalone helper function,
e.g. `_build_N_sample(N_total, samples_per_N, pool) -> efold_array`, called
from *both* branches' `full_payload`. Don't duplicate that logic — it's
subtle (the exact-endpoint append) and the two branches must agree on it for
any homogeneous-vs-gradient comparison at the same grid point to be
apples-to-apples.

**d. `execute()`**: pass `args.targets` through to `run_all_pipelines()`, and
add the same `--stop-after`-vs-`--targets` warning described in point 2
before the call.

**e. `inventory()`**: add
`_inventory_object(pool, "GradientCoupledInstanton", "Gradient-coupled (onion model) instantons")`.

## Non-goals (explicitly out of scope for this prompt)

- No changes to `ComputeTargets/GradientCoupledInstanton/*` internals.
- No CLI exposure of `instrument_stiffness` (stays at its current internal
  default inside the Ray remote function).
- No change to the homogeneous branch's own `--no-store-values` unified-task
  mechanics (`_run_pipeline_queue`) beyond the help-text wording update.
- No change to how `--stop-after` behaves for the homogeneous branch.

## Acceptance criteria

1. `python main.py --config quadratic-minimal.yaml --database test.sqlite`
   (no `--targets` given) behaves identically to today: homogeneous branch
   only, no `GradientCoupledInstanton` rows created.
2. `--targets gradient` runs *only* the gradient branch (trajectory + GCI);
   no `FullInstanton`/`SlowRollInstanton`/`CompactionFunction` rows created;
   prints the gradient-branch combinatorics summary line.
3. `--targets homogeneous gradient` runs both branches against the same
   base grid; both sets of rows are created; the trajectory is computed
   once and reused by both.
4. `--n-collocation-points 21 33 --alpha-regularization 0.01 0.05` produces
   `2 x 2 = 4`-fold gradient combinatorics per base grid point, correctly
   reflected in the printed summary and in the number of `GradientCoupledInstanton`
   rows created.
5. `--alpha-regularization 0` (or any `<= 0` value) is rejected at argument-parse
   time with a clear error, before `ray.init()` / database connection.
6. Constructing `alpha_regularization(store_id=..., alpha=0.0)` directly
   raises `ValueError`.
7. `--no-store-values --targets gradient` produces `GradientCoupledInstanton`
   rows with scalar columns and profile rows populated, but zero
   `GradientCoupledInstantonValue` rows; `--no-store-gradient-instanton-values`
   no longer exists as a CLI flag (removed, not just deprecated) and is not
   referenced anywhere in `main.py` or `config/argument_parser.py`.
8. `--drop gradient-coupled-instanton` on a database containing GCI rows
   removes `GradientCoupledInstantonValue`, `GradientCoupledInstantonProfile`,
   and `GradientCoupledInstanton` rows, in that order, without FK errors, and
   leaves `InflatonTrajectory` and the homogeneous-branch tables untouched.
9. `--stop-after full-instanton --targets gradient` prints a warning
   (`--stop-after` has no effect since `homogeneous` is not selected) and
   still runs the gradient branch to completion.
10. `--inventory` output includes a `GradientCoupledInstanton` section.
11. Existing homogeneous-branch tests / acceptance criteria from prior
    prompts (`--stop-after`, `--no-store-values` in homogeneous-only mode,
    `--sample-grid-csv`) remain unaffected — run the existing test suite,
    don't just eyeball the diff.

## Suggested commit scope

This is large enough to justify at least two commits:
1. `alpha_regularization` validity fix + CLI parsing changes + drop-table
   cascade (points 1–3) — no behavioural change to `main.py`'s dispatch yet.
2. `config/pipeline_setup.py` + `config/grid_builder.py` + `main.py`
   dispatch restructuring (points 4–6) — the actual wiring.

Validate in a fresh Claude Code session per the project's existing
convention (avoid anchoring bias from the implementing session).
