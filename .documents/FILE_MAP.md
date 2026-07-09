# FILE_MAP — claude-context flat layout

Each file in this directory is a verbatim copy of a source file from the
repository. The filename uses `_` to replace path separators. The table below
maps each flat name back to its original path and gives a one-line description
of what it contains.

Files are grouped by architectural layer to make it easy to find related pieces.

---

## 1. Orchestrator and configuration

| Flat filename                 | Original path                 | Purpose                                                                                                                                                       |
|--------------------------------|--------------------------------|-----------------------------------------------------------------------------------------------------------------------------------------------------------|
| `main.py`                     | `main.py`                     | Top-level entry point; drives the pipeline stages (trajectory → full/slow-roll/gradient-coupled instanton → compaction function); owns the two-pass dispatch pattern and custom store handlers |
| `config_sharding.py`          | `config/sharding.py`          | `ShardedPool` configuration: shard-key type (`delta_Nstar`), `replicated_tables`, `sharded_tables` dict, `read_table_config`, `inventory_config` — includes `GradientCoupledInstanton` (sharded) and `n_collocation_points`/`alpha_regularization` (replicated) |
| `config_argument_parser.py`   | `config/argument_parser.py`   | CLI + YAML argument parsing via `configargparse`; defines all grid, tolerance, potential, sampling, and database arguments                                  |
| `config_model_list.py`        | `config/model_list.py`        | `build_model_list()` helper: constructs the list of inflationary-model parameter dicts passed into the pipeline                                             |
| `config_grid_builder.py`      | `config/grid_builder.py`      | `build_instanton_grid()`: builds the N_init × N_final × delta_Nstar parameter grid from parsed CLI/YAML args; supports both Cartesian and CSV-specified grids |
| `config_pipeline_setup.py`    | `config/pipeline_setup.py`    | `build_pipeline_inputs()`: mints the datastore objects (trajectory, N_init, N_final, delta_Nstar) needed to run the compute pipeline or plotting scripts    |
| `config_generate_lhc_grid.py` | `config/generate_lhc_grid.py` | Standalone script to generate a Latin hypercube sample (LHC) CSV grid over (delta_Nstar, ΔN, N_final) for DOE runs; produces `--sample-grid-csv`-compatible output |
| `quadratic-minimal.yaml`      | `quadratic-minimal.yaml`      | Exemplar minimal parameter file: single quadratic-potential model, 10 shards, tight tolerances, `phi0=15 Mp`; the smallest complete `--database ... ` run configuration |

---

## 2. Distributed work-queue

| Flat filename             | Original path             | Purpose                                                                                                                                                                                                                                                                        |
|---------------------------|---------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `RayTools_RayWorkPool.py` | `RayTools/RayWorkPool.py` | `RayWorkPool` class: the core distributed work-queue abstraction; manages the **lookup → compute → store → persist → validate** state machine over a list of compute targets using `ray.wait()`; provides `create_batch_size`, `process_batch_size`, `max_task_queue` controls |

---

## 3. Datastore core

| Flat filename                  | Original path                  | Purpose                                                                                                                                                                                                                                                                |
|---------------------------------|---------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `Datastore_object.py`          | `Datastore/object.py`          | `DatastoreObject` base class: provides `store_id` property and `available` boolean used everywhere to test persistence state                                                                                                                                           |
| `Datastore_SQL_ShardedPool.py` | `Datastore/SQL/ShardedPool.py` | `ShardedPool` — the primary datastore API seen by `main.py`; coordinates multiple `Datastore` Ray actors across shards; implements `object_get`, `object_get_vectorized`, `object_store`, `object_validate`, `read_table`, `inventory`                                 |
| `Datastore_SQL_Datastore.py`   | `Datastore/SQL/Datastore.py`   | `@ray.remote class Datastore` — a single shard actor wrapping a SQLite connection; owns the factory registry and delegates to factories for every get/store/validate call                                                                                              |

---

## 4. ObjectFactory pattern

The base protocol plus a progression from simplest to most complex factory,
ending with the two multi-table factories (`CompactionFunction`,
`GradientCoupledInstanton`) that own child value/sample tables.

| Flat filename                                                        | Original path                                                        | Purpose                                                                                                                                                                     |
|------------------------------------------------------------------------|------------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `Datastore_SQL_ObjectFactories_base.py`                              | `Datastore/SQL/ObjectFactories/base.py`                              | `SQLAFactoryBase` — the abstract base class for all factories; documents the four-method protocol: `register()`, `build()`, `store()`, `validate()`                       |
| `Datastore_SQL_ObjectFactories_tolerance.py`                         | `Datastore/SQL/ObjectFactories/tolerance.py`                         | Simplest factory: single-column table, fuzzy float match in `build()`, no value list in `store()`                                                                          |
| `Datastore_SQL_ObjectFactories_DimensionlessQuantity.py`             | `Datastore/SQL/ObjectFactories/DimensionlessQuantity.py`             | Generic factory for dimensionless quantity subclasses (`delta_Nstar`, `quartic_coupling`); uses a `classname → column_name` dispatch table                                 |
| `Datastore_SQL_ObjectFactories_DimensionfulQuantity.py`              | `Datastore/SQL/ObjectFactories/DimensionfulQuantity.py`              | Generic factory for dimensional quantity subclasses (`phi_value`, `pi_value`, `inflaton_mass`); same dispatch-table pattern, and the reference example for the unit-conversion discipline in `INFRASTRUCTURE.md` §3                                                     |
| `Datastore_SQL_ObjectFactories_delta_Nstar.py`                       | `Datastore/SQL/ObjectFactories/delta_Nstar.py`                       | Factory for `delta_Nstar` — the shard key type; illustrates how the shard-key object is registered and looked up                                                           |
| `Datastore_SQL_ObjectFactories_efold.py`                             | `Datastore/SQL/ObjectFactories/efold.py`                             | Factory for `efold_value` sample coordinates; used whenever the pipeline mints an N-grid                                                                                   |
| `Datastore_SQL_ObjectFactories_n_collocation_points.py`              | `Datastore/SQL/ObjectFactories/n_collocation_points.py`              | Factory for `n_collocation_points` — the LGL node-count convergence parameter for `GradientCoupledInstanton`; same "shared numerical-parameter" pattern as `tolerance`     |
| `Datastore_SQL_ObjectFactories_alpha_regularization.py`              | `Datastore/SQL/ObjectFactories/alpha_regularization.py`              | Factory for `alpha_regularization` — the onion-coordinate regularization parameter α; same shared-parameter pattern as `n_collocation_points`                              |
| `Datastore_SQL_ObjectFactories_QuadraticPotential.py`                | `Datastore/SQL/ObjectFactories/QuadraticPotential.py`                | Factory for the `QuadraticPotential` model object; illustrates how a potential object is persisted and restored                                                            |
| `Datastore_SQL_ObjectFactories_InflatonTrajectory.py`                | `Datastore/SQL/ObjectFactories/InflatonTrajectory.py`                | Factory for `InflatonTrajectory`; `store()` serialises the full `_values` list (N, φ, π) to a JSON blob; `validate()` checks row-count consistency                         |
| `Datastore_SQL_ObjectFactories_FullInstanton.py`                     | `Datastore/SQL/ObjectFactories/FullInstanton.py`                     | Factory for `FullInstanton`; sharded table, `store()` serialises (N, φ₁, φ₂, P₁, P₂, MSR action) per sample, `validate()` marks the row validated                         |
| `Datastore_SQL_ObjectFactories_SlowRollInstanton.py`                 | `Datastore/SQL/ObjectFactories/SlowRollInstanton.py`                 | Factory for `SlowRollInstanton`; same sharded pattern as `FullInstanton` with the slow-roll field subset                                                                   |
| `Datastore_SQL_ObjectFactories_CompactionFunction.py`                | `Datastore/SQL/ObjectFactories/CompactionFunction.py`                | Factory for `CompactionFunction`; owns the `CompactionFunctionSamples` child table (r-ordered); illustrates the `ORDER BY` + cascade-delete rules for a value/sample table |
| `Datastore_SQL_ObjectFactories_GradientCoupledInstanton.py`          | `Datastore/SQL/ObjectFactories/GradientCoupledInstanton.py`          | Factory for `GradientCoupledInstanton`; owns two child tables (`GradientCoupledInstantonValue`, N-ordered; `GradientCoupledInstantonProfile`, node-index-ordered); also persists the eleven-scalar "parity" set (`C_peak`, `r_max_Mpc`, `M_max_SolarMass`, …) that mirrors `CompactionFunction`'s own exposed scalars, unconditionally rehydrated even on the cheap fetch tier; the most complex factory in the codebase |
| `Datastore_SQL_ObjectFactories_MasslessDecoupledDiffusion.py`        | `Datastore/SQL/ObjectFactories/MasslessDecoupledDiffusion.py`        | Factory for `MasslessDecoupledDiffusion`; singleton table (no parameters); registers the type in `DIFFUSION_MODEL_REGISTRY` on build                                       |
| `Datastore_SQL_ObjectFactories_CosmologicalParams.py`                | `Datastore/SQL/ObjectFactories/CosmologicalParams.py`                | Factory for `CosmologicalParams`; stores cosmological parameter bundles (Planck2013/2015/2018) as named rows; looked up by name on build                                   |

---

## 5. Compute targets

Each single-file target follows the four-part pattern: `@ray.remote` function
→ `FooValue` class → `Foo` class (plain Python, no decorator) → `FooProxy`
class. `GradientCoupledInstanton` is large enough to be split across several
files under `ComputeTargets/GradientCoupledInstanton/`; the compute-target
class itself still lives in the file mapped to `..._main.py` below and follows
the same four-part shape, but delegates the numerical work to the other
modules in this section rather than inlining it in the `@ray.remote` function.

| Flat filename                                              | Original path                                              | Purpose                                                                                                                                                                                             |
|--------------------------------------------------------------|--------------------------------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `ComputeTargets_InflatonTrajectory.py`                      | `ComputeTargets/InflatonTrajectory.py`                      | Background ODE integration; internally-built sample grid (Approach B); custom `store_handler` required in `main.py` to mint `efold_value` objects after the ODE endpoint is known                    |
| `ComputeTargets_FullInstanton.py`                           | `ComputeTargets/FullInstanton.py`                           | Full MSR instanton BVP; Picard inner loop + outer shooting loop on λ (now delegated to the shared `Numerics_ShootingSolver.py`, §6); pre-minted sample grid (Approach A); `store()` populates `_values` directly |
| `ComputeTargets_SlowRollInstanton.py`                       | `ComputeTargets/SlowRollInstanton.py`                       | Slow-roll-approximated instanton BVP; same Approach A pattern as `FullInstanton`                                                                                                                     |
| `ComputeTargets_CompactionFunction.py`                      | `ComputeTargets/CompactionFunction.py`                      | Single-trajectory radial density profile ζ(r) and compaction function C(r)/C̄(r); PBH-formation threshold check; PBH mass and physical-scale (Leach–Liddle) assignment; peels shells off `FullInstanton`; the dense-grid C̄/classification/PBH-mass arithmetic itself now lives in `ComputeTargets_compaction_scalars.py` |
| `ComputeTargets_compaction_scalars.py`                      | `ComputeTargets/compaction_scalars.py`                      | Shared, physics-free numerical core factored out of `CompactionFunction` (prompt U1): `classify_radii`, `densify_zeta_profile`, `compute_C_bar`, `classify_C_min`, `pbh_mass` — pure numpy/scipy helpers over already-evaluated arrays, reused verbatim by both `CompactionFunction` and `GradientCoupledInstanton/scale_assignment.py` so the two schemes' C̄/threshold/mass arithmetic cannot drift apart |
| `ComputeTargets_pipeline.py`                                | `ComputeTargets/pipeline.py`                                | Pipeline helper: `_run_scalar_only_compaction_path()` for the scalar-only (no `_values`) populate path; handles integrity checks for pre-existing scalar-only rows before triggering a full recompute |
| `ComputeTargets_GradientCoupledInstanton_main.py`           | `ComputeTargets/GradientCoupledInstanton/GradientCoupledInstanton.py` | The `GradientCoupledInstanton`/`Value`/`Profile`/`Proxy` datastore compute target; ties the modules below into the Ray-dispatch pattern; owns `msr_action` population and, since prompts U2b/U3, the full eleven-scalar `CompactionFunction`-parity set (`C_peak`, `C_bar_peak`, `C_min`, `compensated`, `type_II`, `r_max`, `r_peak`, `M_max`, `M_peak`, `V_end_downflow`, `N_end_downflow`), computed via `ComputeTargets_compaction_scalars.py` and persisted alongside the profile |
| `ComputeTargets_GradientCoupledInstanton_forward_rhs.py`    | `ComputeTargets/GradientCoupledInstanton/forward_rhs.py`    | Forward-sector (φ, π grid) collocation RHS; SBP-SAT boundary closure at the core node (y=+1); state-packing/unpacking                                                                               |
| `ComputeTargets_GradientCoupledInstanton_response_rhs.py`   | `ComputeTargets/GradientCoupledInstanton/response_rhs.py`   | Response-sector (rfield, rmom grid) collocation RHS and terminal-condition construction; still uses the older strong (Neumann-elimination) boundary closure — deliberately not yet ported to SBP-SAT |
| `ComputeTargets_GradientCoupledInstanton_picard.py`         | `ComputeTargets/GradientCoupledInstanton/picard.py`         | Picard/shooting driver: inner fixed-point iteration between forward and response sectors, outer shooting loop on λ via the shared `Numerics_ShootingSolver.py`; the lagged-target SAT bookkeeping for `pi_core`; optional `FullInstanton`-seeded bootstrap of the first shooting step |
| `ComputeTargets_GradientCoupledInstanton_extraction.py`     | `ComputeTargets/GradientCoupledInstanton/extraction.py`     | Per-shell ζ(y) extraction: noiseless downflow to ε=1 + density matching against the background trajectory, reusing `CompactionFunction`'s Steps A/B construction node-by-node                       |
| `ComputeTargets_GradientCoupledInstanton_scale_assignment.py` | `ComputeTargets/GradientCoupledInstanton/scale_assignment.py` | Comoving radius, compaction function C(y) via chain-ruled ζ′(r), C̄(y) and densified-grid r_max/r_peak classification (prompt U2a, via `compaction_scalars.densify_zeta_profile`/`compute_C_bar`/`classify_radii`), and physical (present-day) scale r_phys(y) via a single Leach–Liddle anchor propagated by a fixed ratio |
| `ComputeTargets_GradientCoupledInstanton_msr_action.py`     | `ComputeTargets/GradientCoupledInstanton/msr_action.py`     | On-shell MSR action: full three-term quadratic form in (rfield, rmom), y-integrated against the self-adjoint measure μ(y,N), N-integrated by trapezoid                                              |

---

## 6. Numerics — collocation, coordinate, and shooting machinery

The physics-free numerical core that `GradientCoupledInstanton` (and, for the
shooting solver, `FullInstanton` too) is built on top of. Each module is
deliberately standalone (plain numpy, no `AbstractPotential`, no
`DatastoreObject`, no Ray).

| Flat filename                        | Original path                        | Purpose                                                                                                                                                                    |
|----------------------------------------|----------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `Numerics_LGLCollocation.py`          | `Numerics/LGLCollocation.py`          | `LGLCollocationGrid`: Legendre–Gauss–Lobatto nodes (via Jacobi-matrix eigenvalues), quadrature weights, and first-/second-derivative differentiation matrices `D`, `D2` on `[-1,1]` |
| `Numerics_DiscretizedOperators.py`    | `Numerics/DiscretizedOperators.py`    | `L_operator` (discretized Laplacian in the onion coordinate), plain-product and skew-symmetric-split advection operators, Neumann hard-elimination, and the SBP-SAT split-form advection used by the production forward RHS |
| `Numerics_OnionCoordinate.py`         | `Numerics/OnionCoordinate.py`         | Coordinate-map scalars: `delta_s(N)`, its N-derivative, the advection coefficient `A(y,N)`, the self-adjoint measure `μ(y,N)`, and the comoving-radius ratio              |
| `Numerics_ShootingSolver.py`          | `Numerics/ShootingSolver.py`          | `solve_shooting`: generic scalar secant solver with Armijo backtracking and a trust-region step cap (prompts 22c/24b), factored out of `picard.py`'s outer loop so `FullInstanton`'s own outer loop can share the same hardening rather than duplicating it; physics-free — knows only that it is rooting a scalar `evaluate(λ) → residual` callback |

---

## 7. Quadrature

| Flat filename                        | Original path                        | Purpose                                                                                                        |
|----------------------------------------|----------------------------------------|----------------------------------------------------------------------------------------------------------------|
| `Quadrature_simple_quadrature.py`     | `Quadrature/simple_quadrature.py`     | Plain trapezoid/Simpson-style quadrature helpers used for the N-direction integral of the MSR action and elsewhere |
| `Quadrature_integration_metadata.py`  | `Quadrature/integration_metadata.py`  | ODE-solver metadata record (protected infrastructure — included read-only, for reference only; do not propose edits to the original) |

---

## 8. Interpolation

| Flat filename                     | Original path                     | Purpose                                                                                                                                                                        |
|--------------------------------------|--------------------------------------|----------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `Interpolation_spline_wrapper.py` | `Interpolation/spline_wrapper.py` | `SplineWrapper`: thin wrapper around `make_interp_spline` that applies optional `linear`/`log`/`sinh` coordinate transforms before fitting; exposes `derivative()` with full chain-rule correction; root-finding API works in transformed space |

---

## 9. Domain concepts — CosmologyConcepts

These provide the base classes for all physics quantities.

| Flat filename                                       | Original path                                       | Purpose                                                                                                                                               |
|---------------------------------------------------------|---------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------|
| `CosmologyConcepts_DimensionlessQuantity.py`        | `CosmologyConcepts/DimensionlessQuantity.py`        | `DimensionlessQuantity` base class: wraps a `float` value with `store_id`; base for `delta_Nstar`, `N_init`, `N_final`, `quartic_coupling`            |
| `CosmologyConcepts_DimensionfulQuantity.py`         | `CosmologyConcepts/DimensionfulQuantity.py`         | `DimensionfulQuantity` base class: wraps a `float` value (in reduced Planck units) with `store_id`; base for `phi_value`, `pi_value`, `inflaton_mass` |
| `CosmologyConcepts_Potentials_AbstractPotential.py` | `CosmologyConcepts/Potentials/AbstractPotential.py` | `AbstractPotential` interface: declares `H²`, `ε`, `dV/dφ`, `d²V/dφ²`, and `D_matrix`; all inflationary models must implement this                    |

---

## 10. Domain concepts — InflationConcepts

Inflation-specific domain objects that implement or specialise the cosmology
base classes, including the two solver-convergence parameter concepts
introduced for `GradientCoupledInstanton`.

| Flat filename                                      | Original path                                      | Purpose                                                                                                                                    |
|----------------------------------------------------|-----------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------|
| `InflationConcepts_delta_Nstar.py`                 | `InflationConcepts/delta_Nstar.py`                 | `delta_Nstar` — excess transition e-fold count; the shard key of the entire database                                                       |
| `InflationConcepts_efold_value.py`                 | `InflationConcepts/efold_value.py`                 | `efold_value` — a single e-fold sample coordinate N; also defines `efold_array` container                                                  |
| `InflationConcepts_N_init.py`                      | `InflationConcepts/N_init.py`                      | `N_init` — initial e-fold count; one axis of the instanton parameter grid                                                                  |
| `InflationConcepts_N_final.py`                     | `InflationConcepts/N_final.py`                     | `N_final` — final e-fold count; the other axis of the instanton parameter grid                                                             |
| `InflationConcepts_alpha_regularization.py`        | `InflationConcepts/alpha_regularization.py`        | `alpha_regularization` — the onion-coordinate regularization parameter α (rejects α ≤ 0); a numerical-implementation, not physical, parameter |
| `InflationConcepts_n_collocation_points.py`        | `InflationConcepts/n_collocation_points.py`        | `n_collocation_points` — the LGL node-count convergence parameter fed to `LGLCollocationGrid`; deliberately has no `.n_max` property        |
| `InflationConcepts_noiseless_equations.py`         | `InflationConcepts/noiseless_equations.py`         | Shared ODE RHS `noiseless_rhs()` and `end_of_inflation_event()` for the noiseless background; used by `InflatonTrajectory`, `CompactionFunction`, and per-shell downflow in `GradientCoupledInstanton/extraction.py` |
| `InflationConcepts_QuadraticPotential.py`          | `InflationConcepts/QuadraticPotential.py`          | `QuadraticPotential` concrete implementation: V(φ) = ½m²φ²                                                                                 |
| `InflationConcepts_QuarticPotential.py`            | `InflationConcepts/QuarticPotential.py`            | `QuarticPotential` concrete implementation: V(φ) = λφ⁴                                                                                     |
| `InflationConcepts_DiffusionModel.py`              | `InflationConcepts/DiffusionModel/__init__.py`     | `AbstractDiffusionModel` and `MasslessDecoupledDiffusion`; provides the 2×2 diffusion matrix D_{ij}(φ, π) used in the stochastic equations |
| `InflationConcepts_DiffusionModel_model_ids.py`    | `InflationConcepts/DiffusionModel/model_ids.py`    | Integer type-ID constants for `AbstractDiffusionModel` subclasses; `MASSLESS_DECOUPLED_DIFFUSION = 1`                                     |
| `InflationConcepts_DiffusionModel_registry.py`     | `InflationConcepts/DiffusionModel/registry.py`     | `DIFFUSION_MODEL_REGISTRY` dict populated by each concrete subclass factory on import; used to route `build()` calls by `type_id`          |

---

## 11. Domain concepts — CosmologyModels

Persistable wrappers around cosmological parameter bundles used to convert
instanton scales to physical PBH masses and radii.

| Flat filename                     | Original path                     | Purpose                                                                                                                                    |
|--------------------------------------|--------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------|
| `CosmologyModels_cosmo_params.py` | `CosmologyModels/cosmo_params.py` | `CosmologicalParams` — persistable `DatastoreObject` wrapping a parameter bundle; exposes `omega_cc`, `omega_m`, `h`, `T_CMB_Kelvin`, etc. |
| `CosmologyModels_params.py`       | `CosmologyModels/params.py`       | Bare dataclasses `Planck2013`, `Planck2015`, `Planck2018` holding best-fit cosmological constants; passed into `CosmologicalParams`        |

---

## 12. Metadata concepts

| Flat filename                   | Original path                   | Purpose                                                                                                     |
|------------------------------------|------------------------------------|------------------------------------------------------------------------------------------------------------|
| `MetadataConcepts_store_tag.py` | `MetadataConcepts/store_tag.py` | `store_tag` — a string label that can be attached to any stored object to mark membership in a run or group |

---

## 13. Units

| Flat filename           | Original path           | Purpose                                                                                                                          |
|-----------------------------|-----------------------------|----------------------------------------------------------------------------------------------------------------------------------|
| `Units_base.py`         | `Units/base.py`         | `UnitsLike` abstract base class: declares abstract properties for every unit used in the code (`PlanckMass`, `Metre`, `eV`, `c`, `Mpc`, …); see `NUMERICAL_SCHEMES.md` §0 for the natural-units discipline this implements |
| `Units_Planck_units.py` | `Units/Planck_units.py` | `Planck_units` concrete implementation: sets all constants relative to reduced Planck units (Mₚ = 1, 8πG = 1); the `UnitsLike` instance used throughout this project                    |

---

## 14. Plotting and analysis driver scripts

Prompt P1 extracted most of `plot_InstantonSolutions.py`'s reusable machinery
into the `plotting/` package (data fetch, solver-agnostic adapters, figure
functions, annotation/provenance/sampling helpers); prompt P2/P2b then
converted the figure functions to consume `InstantonAdapter` instances
instead of raw `FullInstanton`/`SlowRollInstanton`/`CompactionFunction`
objects, so a figure function never branches on which solver produced its
data. `plot_InstantonSolutions.py` itself is now primarily orchestration:
argument parsing, the background/epsilon plots that have no adapter (they
plot `InflatonTrajectory` directly), the `@ray.remote` per-figure dispatch
wrappers, the sweep/DOE data-collection loops, and `run_plots()`.

| Flat filename                          | Original path                          | Purpose                                                                                                                                                                                   |
|-----------------------------------------|-----------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `plot_InstantonSolutions.py`           | `plot_InstantonSolutions.py`           | Plotting driver: reads the database via `ShardedPool`; produces background-trajectory, instanton-field, noise-profile, MSR-action-sweep, compaction-profile, and DOE-scalar-summary figures using Ray-dispatched worker tasks; now delegates fetch/adapter/figure logic to `plotting/` |
| `plotting_adapters_base.py`            | `plotting/adapters/base.py`            | `InstantonAdapter` — the solver-agnostic ABC every figure function is written against (`available`, `failure`, `time_history()`, `radial_profile()`, `scalars()`, `channel_label()`, …); design doc `.documents/gradient-coupled-plotting/DESIGN_gradient_coupled_plotting.md` §3.1-3.2 |
| `plotting_adapters_full.py`            | `plotting/adapters/full.py`            | `FullInstantonAdapter` — concrete adapter wrapping a `FullInstanton` (+ paired `CompactionFunction`) onto the `InstantonAdapter` protocol; `SlowRollInstantonAdapter` in `slow_roll.py` follows the same shape (omitted as near-identical) |
| `plotting_fetch.py`                    | `plotting/fetch.py`                    | Vectorized-availability grid fetch (`fetch_over_grid`) plus the P2b `ClassFetchSpec`/`fetch_adapters_over_grid` retrofit that fetches several solver classes over one grid and returns ready-built `InstantonAdapter` lists, so adding a new solver kind (e.g. GCI) means adding one `ClassFetchSpec`, not touching figure code |
| `plotting_figures_time_history.py`     | `plotting/figures/time_history.py`     | Representative figure function: 2×2 grid of instanton field components vs N, consuming a flat list of `InstantonAdapter`; overlaying more solvers is just passing a longer list |
| `regression_InstantonOutputs.py`       | `regression_InstantonOutputs.py`       | GP regression driver: reads `scalar_data.csv` from the plot script; fits independent single-output GPs (C_bar_max, C_max, log S_MSR, log M_PBH, log r_PBH); writes diagnostic plots and serialised `.joblib` model bundles |

---

## 15. Diagnostic tools — `tools/diagnostics/GradientCoupledInstanton`

Standalone, Ray/Datastore-bypassing diagnostic suite for the
`GradientCoupledInstanton` compute target; a consumer of the production API
(`solve_picard`, `_compute_full_instanton`, `LGLCollocationGrid`, …), never
the other way — nothing here is imported by `main.py`/`ComputeTargets/`/
`Datastore/`. `DIAGNOSTICS_SUITE.md` is this package's own map (mirrors
`FILE_MAP.md`'s per-file-purpose convention) and is included verbatim so the
online session can navigate the rest of the sample without guessing at the
CLI or the harness/module dependency direction.

| Flat filename                                                            | Original path                                                  | Purpose                                                                                                                                                                    |
|----------------------------------------------------------------------------|-------------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `tools_diagnostics_GradientCoupledInstanton_DIAGNOSTICS_SUITE.md`        | `tools/diagnostics/GradientCoupledInstanton/DIAGNOSTICS_SUITE.md` | The package's own map: layout, CLI quick reference, diagnostic-to-provenance table, and known gaps (e.g. Diagnostic 8t requires a small production change first)         |
| `tools_diagnostics_GradientCoupledInstanton_cli.py`                      | `tools/diagnostics/GradientCoupledInstanton/cli.py`               | Unified argparse dispatcher across all subcommands; each module also remains independently runnable as `python -m tools.diagnostics.GradientCoupledInstanton.<module>`   |
| `tools_diagnostics_GradientCoupledInstanton_harness.py`                  | `tools/diagnostics/GradientCoupledInstanton/harness.py`           | Shared setup/fetch/IO/monkeypatch helpers factored out of three predecessor scripts (`_PotentialHolder`/`_TrajProxyStub`, `production_phi_end`, `fetch_full_instanton`, `MonkeypatchGuard`, `.npz` grid schema); every other diagnostic module imports from here, never the reverse |
| `tools_diagnostics_GradientCoupledInstanton_convergence_floor.py`        | `tools/diagnostics/GradientCoupledInstanton/convergence_floor.py` | Diagnostics 1–8: the `delta_Nstar`/mass/`n_collocation_points`/`OUTER_TOL`/`alpha_regularization` convergence-floor campaign; the suite's main data-generating module     |
| `tools_diagnostics_GradientCoupledInstanton_seed_screen.py`              | `tools/diagnostics/GradientCoupledInstanton/seed_screen.py`       | Cheap `alpha_regularization` vs `n_collocation_points` zeroth-Picard-iterate pre-screen, before spending a full solve budget on an untested corner                        |
| `tools_diagnostics_GradientCoupledInstanton_trajectory_plots.py`         | `tools/diagnostics/GradientCoupledInstanton/trajectory_plots.py`  | Trajectory-validation plots (phi/pi(N) vs `FullInstanton`, epsilon(N), y-profile, action-ratio-vs-sweep-variable) for any converged-solve JSON+`.npz` record produced by `convergence_floor.py` |

---

## 16. Tests

A representative sample illustrating the numerics core, the SBP-SAT closure,
the U1/U2a compaction-scalar sharing, and the U2b/U3 GCI/CompactionFunction
parity cross-check and its persistence round trip.

| Flat filename                                            | Original path                                            | Purpose                                                                                                                                                            |
|-------------------------------------------------------------|---------------------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `tests_test_lgl_collocation.py`                          | `tests/test_lgl_collocation.py`                          | `LGLCollocationGrid` node/weight/differentiation-matrix correctness (exact-polynomial differentiation, quadrature exactness)                                     |
| `tests_test_onion_coordinate.py`                          | `tests/test_onion_coordinate.py`                          | `Numerics/OnionCoordinate.py` coordinate-map scalars: `delta_s(N)`, advection coefficient, self-adjoint measure                                                    |
| `tests_test_sbp_sat_boundary_closure.py`                 | `tests/test_sbp_sat_boundary_closure.py`                 | The discrete SBP energy identity and the split-form advection operator that motivate the SBP-SAT closure (`NUMERICAL_SCHEMES.md` §3.5)                            |
| `tests_test_scale_assignment_densification.py`           | `tests/test_scale_assignment_densification.py`           | Prompt U2a: `assign_scales`'s densified-grid C̄ and r_max/r_peak classification, including the "consistent with pre-densification within `O(1/n)`" regression check |
| `tests_test_gci_parity_scalars.py`                        | `tests/test_gci_parity_scalars.py`                        | Prompt U2b: the eleven-scalar parity set returned by `_compute_gradient_coupled_instanton`, cross-checked against `CompactionFunction`'s own scalars at a matching grid point |
| `tests_test_gci_parity_persistence_roundtrip.py`          | `tests/test_gci_parity_persistence_roundtrip.py`          | Prompt U3: store → rehydrate round trip for the parity scalar columns, including the cheap (`_do_not_populate=True`) fetch tier                                    |
| `tests_test_compaction_scalars_refactor_golden.py`        | `tests/test_compaction_scalars_refactor_golden.py`        | Prompt U1: golden-value regression proving `compaction_scalars.py`'s extracted helpers are bit-for-bit identical to the pre-refactor inlined `CompactionFunction` code |
| `tests_test_plot_adapters_golden.py`                      | `tests/test_plot_adapters_golden.py`                      | Prompt P2: golden regression proving `FullInstantonAdapter`/`SlowRollInstantonAdapter` reproduce the pre-refactor plotting values bit-for-bit across `available`/`failure`/`time_history`/`radial_profile`/`scalars` |

---

## Files not included

The following project files were deliberately omitted to keep the context
focused on design patterns. They are protected infrastructure, near-identical
to files already included, peripheral to the patterns described above, or
covered adequately by `NUMERICAL_SCHEMES.md`/`INFRASTRUCTURE.md`'s narrative
text rather than by including the source directly.

| Original path                                           | Reason omitted                                                              |
|-----------------------------------------------------------|--------------------------------------------------------------------------|
| `Datastore/SQL/ClientPool.py`                           | Protected infrastructure; internal to `ShardedPool`                         |
| `Datastore/SQL/SerialPoolBroker.py`                     | Protected infrastructure; monotone serial-number actor                      |
| `Datastore/SQL/ProfileAgent.py`                         | Optional query-profiling actor; not core to the patterns                    |
| `Datastore/SQL/ObjectFactories/version.py`              | Trivial single-row factory; `tolerance.py` is a better illustrative example |
| `Datastore/SQL/ObjectFactories/store_tag.py`            | Same; `tolerance.py` illustrates the pattern                                |
| `Datastore/SQL/ObjectFactories/N_init.py`, `N_final.py` | Dedicated factories, but the pattern they illustrate does not differ from `tolerance.py`/`DimensionlessQuantity.py` already included |
| `Datastore/SQL/ObjectFactories/integration_metadata.py` | Protected infrastructure; ODE-solver metadata only                          |
| `Datastore/SQL/ObjectFactories/redshift.py`             | Protected infrastructure; legacy cosmology concept, unused in this project  |
| `Datastore/SQL/ObjectFactories/QuarticPotential.py`     | Near-identical to `QuadraticPotential` factory                              |
| `CosmologyConcepts/FieldValues.py`                      | Thin wrapper; `DimensionfulQuantity` already illustrates the pattern        |
| `CosmologyConcepts/redshift.py`, `temperature.py`       | Legacy cosmology concepts, unused in this project                          |
| `CosmologyConcepts/Potentials/registry.py`, `model_ids.py` | Internal model-ID dispatch table; not core                               |
| `InflationConcepts/inflaton_mass.py`, `quartic_coupling.py` | Thin `Dimension{ful,less}Quantity` subclasses; no new pattern           |
| `MetadataConcepts/tolerance.py`                         | Already represented by `Datastore_SQL_ObjectFactories_tolerance.py`         |
| `Quadrature/supervisors/base.py`                        | Protected infrastructure; supervisor base class, not exercised directly by the modules included here |
| `RayTools/` (other files)                               | Only `RayWorkPool.py` is directly relevant                                  |
| `config/defaults.py`                                    | Small constants file; values visible in `argument_parser.py`                |
| `ComputeTargets/exceptions.py`                          | Small; exception class definitions only                                     |
| `ComputeTargets/GradientCoupledInstanton/__init__.py`   | Trivial re-export module                                                    |
| `Caching/ExtractionCache.py`                             | Memoisation helper for repeated ζ-extraction calls; an optimisation, not part of the core numerical scheme |
| `constants.py`                                           | Only defines `RadiationConstant` and `StefanBoltzmannConstant`; peripheral  |
| `utilities.py`                                           | General-purpose utilities (timing, grouper, etc.); not needed for patterns  |
| `plotting/adapters/slow_roll.py`                         | Near-identical to `plotting_adapters_full.py`; same `InstantonAdapter` shape with the slow-roll channel subset |
| `plotting/dispatch.py`                                   | Generic `@ray.remote` render wrapper; not yet wired into any driver (figures still dispatch directly), a P2b scaffold |
| `plotting/annotations.py`, `plotting/provenance.py`, `plotting/sampling.py` | Small presentation helpers (CF annotation text, provenance footer, even-sampling); not core to the adapter/fetch pattern illustrated by §14's selection |
| `plotting/figures/compaction.py`, `noise.py`, `sweeps.py`, `doe.py` | Further figure functions of the same adapter-consuming shape as `plotting_figures_time_history.py`; `doe.py` is the one figure not yet converted to adapters (still `data_points` dicts) |
| `tools/diagnostics/GradientCoupledInstanton/spectrum.py` | Assembled-operator eigenvalue-sweep diagnostic (prompts 17/18/18a/20/21/21a/23); large (~1800 lines) and self-contained (no `harness.py` dependency) — omitted from the representative sample in favour of `cli.py`/`harness.py`/`convergence_floor.py`/`seed_screen.py`/`trajectory_plots.py`, which better illustrate the package's shared-harness design |
| `tools/diagnostics/GradientCoupledInstanton/explore_onion_stiffness.py` | Predates the harness refactor; relocated into the package so it has no external scratch-directory dependency, but not one of the consolidated diagnostics |
| `tools/diagnostics/GradientCoupledInstanton/archive/prompt22_validation.py` | Frozen historical replay of prompt 22's own (pre-22a, deliberately degenerate) validation harness; kept for provenance only, not part of the active CLI |
| `tools/diagnostics/GradientCoupledInstanton/__init__.py`, `__main__.py` | Package docstring/version and `python -m` entry point; no logic beyond what `DIAGNOSTICS_SUITE.md` §1 already documents |
| `tests/` (remaining ~35 files)                           | Section 16 above is a deliberately small representative sample; the rest cover the same patterns at other grid points, seeds, or failure modes |
| `.documents/gradient-coupled-instanton/onion_model.tex`  | Not copied into this bundle — the online session is assumed to have access to it directly per the source prompt; `NUMERICAL_SCHEMES.md` cites its section/equation numbers rather than reproducing them |
