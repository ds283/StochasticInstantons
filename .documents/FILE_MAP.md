# FILE_MAP — claude-context flat layout

Each file in this directory is a verbatim copy of a source file from the
repository. The filename uses `_` to replace path separators. The table below
maps each flat name back to its original path and gives a one-line description
of what it contains.

Files are grouped by architectural layer to make it easy to find related pieces.
 
---

## 1. Orchestrator and configuration

| Flat filename               | Original path               | Purpose                                                                                                                                                                                           |
|-----------------------------|-----------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `main.py`                   | `main.py`                   | Top-level entry point; drives the three-stage pipeline (trajectory → full instanton → slow-roll instanton); owns the two-pass dispatch pattern and the custom `inflaton_trajectory_store_handler` |
| `config_sharding.py`        | `config/sharding.py`        | Defines the `ShardedPool` configuration: shard-key type (`delta_Nstar`), `replicated_tables`, `sharded_tables` dict, `read_table_config`, `inventory_config`                                      |
| `config_argument_parser.py` | `config/argument_parser.py` | CLI + YAML argument parsing via `configargparse`; defines all grid, tolerance, potential, sampling, and database arguments                                                                        |
| `config_model_list.py`      | `config/model_list.py`      | `build_model_list()` helper: constructs the list of inflationary-model parameter dicts passed into the pipeline                                                                                   |
| `config_grid_builder.py`    | `config/grid_builder.py`    | `build_instanton_grid()`: builds the N_init × N_final × delta_Nstar parameter grid from parsed CLI/YAML args; supports both Cartesian and CSV-specified grids                                    |
| `config_pipeline_setup.py`  | `config/pipeline_setup.py`  | `build_pipeline_inputs()`: mints the datastore objects (trajectory, N_init, N_final, delta_Nstar) needed to run the compute pipeline or plotting scripts                                          |
| `config_generate_lhc_grid.py` | `config/generate_lhc_grid.py` | Standalone script to generate a Latin hypercube sample (LHC) CSV grid over (delta_Nstar, ΔN, N_final) for DOE runs; produces `--sample-grid-csv`-compatible output                           |

 
---

## 2. Distributed work-queue

| Flat filename             | Original path             | Purpose                                                                                                                                                                                                                                                                        |
|---------------------------|---------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `RayTools_RayWorkPool.py` | `RayTools/RayWorkPool.py` | `RayWorkPool` class: the core distributed work-queue abstraction; manages the **lookup → compute → store → persist → validate** state machine over a list of compute targets using `ray.wait()`; provides `create_batch_size`, `process_batch_size`, `max_task_queue` controls |

 
---

## 3. Datastore core

| Flat filename                  | Original path                  | Purpose                                                                                                                                                                                                                                                                |
|--------------------------------|--------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `Datastore_object.py`          | `Datastore/object.py`          | `DatastoreObject` base class: provides `store_id` property and `available` boolean used everywhere to test persistence state                                                                                                                                           |
| `Datastore_SQL_ShardedPool.py` | `Datastore/SQL/ShardedPool.py` | `ShardedPool` — the primary datastore API seen by `main.py`; coordinates multiple `Datastore` Ray actors across shards; implements `object_get`, `object_get_vectorized`, `object_store`, `object_validate`, `read_table`, `inventory`                                 |
| `Datastore_SQL_Datastore.py`   | `Datastore/SQL/Datastore.py`   | `@ray.remote class Datastore` — a single shard actor wrapping a SQLite connection; owns the factory registry and delegates to factories for every get/store/validate call                                                                                              |

 
---

## 4. ObjectFactory pattern

The base protocol plus a progression from simplest to most complex factory.

| Flat filename                                                    | Original path                                                    | Purpose                                                                                                                                                             |
|------------------------------------------------------------------|------------------------------------------------------------------|---------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `Datastore_SQL_ObjectFactories_base.py`                          | `Datastore/SQL/ObjectFactories/base.py`                          | `SQLAFactoryBase` — the abstract base class for all factories; documents the four-method protocol: `register()`, `build()`, `store()`, `validate()`                 |
| `Datastore_SQL_ObjectFactories_tolerance.py`                     | `Datastore/SQL/ObjectFactories/tolerance.py`                     | Simplest factory: single-column table, fuzzy float match in `build()`, no value list in `store()`                                                                   |
| `Datastore_SQL_ObjectFactories_DimensionlessQuantity.py`         | `Datastore/SQL/ObjectFactories/DimensionlessQuantity.py`         | Generic factory for all dimensionless quantity subclasses (`delta_Nstar`, `N_init`, `N_final`, `quartic_coupling`); uses a `classname → column_name` dispatch table |
| `Datastore_SQL_ObjectFactories_DimensionfulQuantity.py`          | `Datastore/SQL/ObjectFactories/DimensionfulQuantity.py`          | Generic factory for all dimensional quantity subclasses (`phi_value`, `pi_value`, `inflaton_mass`); same dispatch-table pattern                                     |
| `Datastore_SQL_ObjectFactories_delta_Nstar.py`                   | `Datastore/SQL/ObjectFactories/delta_Nstar.py`                   | Factory for `delta_Nstar` — the shard key type; illustrates how the shard-key object is registered and looked up                                                    |
| `Datastore_SQL_ObjectFactories_efold.py`                         | `Datastore/SQL/ObjectFactories/efold.py`                         | Factory for `efold_value` sample coordinates; used whenever the pipeline mints an N-grid                                                                            |
| `Datastore_SQL_ObjectFactories_QuadraticPotential.py`            | `Datastore/SQL/ObjectFactories/QuadraticPotential.py`            | Factory for the `QuadraticPotential` model object; illustrates how a potential object is persisted and restored                                                     |
| `Datastore_SQL_ObjectFactories_InflatonTrajectory.py`            | `Datastore/SQL/ObjectFactories/InflatonTrajectory.py`            | Factory for `InflatonTrajectory`; `store()` serialises the full `_values` list (N, φ, π) to a JSON blob; `validate()` checks row-count consistency                  |
| `Datastore_SQL_ObjectFactories_FullInstanton.py`                 | `Datastore/SQL/ObjectFactories/FullInstanton.py`                 | Factory for `FullInstanton`; most complex: sharded table, `store()` serialises (N, φ₁, φ₂, P₁, P₂, MSR action) per sample, `validate()` marks the row validated     |
| `Datastore_SQL_ObjectFactories_SlowRollInstanton.py`             | `Datastore/SQL/ObjectFactories/SlowRollInstanton.py`             | Factory for `SlowRollInstanton`; same sharded pattern as `FullInstanton` with the slow-roll field subset                                                            |
| `Datastore_SQL_ObjectFactories_CompactionFunction.py`            | `Datastore/SQL/ObjectFactories/CompactionFunction.py`            | Factory for `CompactionFunction` compute target                                                                                                                     |
| `Datastore_SQL_ObjectFactories_MasslessDecoupledDiffusion.py`    | `Datastore/SQL/ObjectFactories/MasslessDecoupledDiffusion.py`    | Factory for `MasslessDecoupledDiffusion`; singleton table (no parameters); registers the type in `DIFFUSION_MODEL_REGISTRY` on build                                |
| `Datastore_SQL_ObjectFactories_CosmologicalParams.py`            | `Datastore/SQL/ObjectFactories/CosmologicalParams.py`            | Factory for `CosmologicalParams`; stores cosmological parameter bundles (Planck2013/2015/2018) as named rows; looked up by name on build                             |

 
---

## 5. Compute targets

Each file follows the four-part pattern: `@ray.remote` function → `FooValue`
class → `Foo` class (plain Python, no decorator) → `FooProxy` class.

| Flat filename                          | Original path                          | Purpose                                                                                                                                                                                              |
|----------------------------------------|----------------------------------------|------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `ComputeTargets_InflatonTrajectory.py` | `ComputeTargets/InflatonTrajectory.py` | Background ODE integration; internally-built sample grid (Approach B); custom `store_handler` required in `main.py` to mint `efold_value` objects after the ODE endpoint is known                    |
| `ComputeTargets_FullInstanton.py`      | `ComputeTargets/FullInstanton.py`      | Full MSR instanton BVP; Picard inner loop + Newton outer loop; pre-minted sample grid (Approach A); `store()` populates `_values` directly                                                           |
| `ComputeTargets_SlowRollInstanton.py`  | `ComputeTargets/SlowRollInstanton.py`  | Slow-roll-approximated instanton BVP; same Approach A pattern as `FullInstanton`                                                                                                                     |
| `ComputeTargets_CompactionFunction.py` | `ComputeTargets/CompactionFunction.py` | Compute radial density profile `zeta(r)` and compaction function `C(r)`; derive averaged compaction function `C_bar(r)`; determine if PBH forms from threshold on `C(r)` or `C_bar(r)`; PBH mass    |
| `ComputeTargets_pipeline.py`           | `ComputeTargets/pipeline.py`           | Pipeline helper: `_run_scalar_only_compaction_path()` for the scalar-only (no `_values`) populate path; handles integrity checks for pre-existing scalar-only rows before triggering a full recompute |

 
---

## 6. Interpolation

| Flat filename                   | Original path                   | Purpose                                                                                                                                                                        |
|---------------------------------|---------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `Interpolation_spline_wrapper.py` | `Interpolation/spline_wrapper.py` | `SplineWrapper`: thin wrapper around `make_interp_spline` that applies optional `linear`/`log`/`sinh` coordinate transforms before fitting; exposes `derivative()` with full chain-rule correction; root-finding API works in transformed space |

 
---

## 7. Domain concepts — CosmologyConcepts

These provide the base classes for all physics quantities.

| Flat filename                                       | Original path                                       | Purpose                                                                                                                                               |
|-----------------------------------------------------|-----------------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------|
| `CosmologyConcepts_DimensionlessQuantity.py`        | `CosmologyConcepts/DimensionlessQuantity.py`        | `DimensionlessQuantity` base class: wraps a `float` value with `store_id`; base for `delta_Nstar`, `N_init`, `N_final`, `quartic_coupling`            |
| `CosmologyConcepts_DimensionfulQuantity.py`         | `CosmologyConcepts/DimensionfulQuantity.py`         | `DimensionfulQuantity` base class: wraps a `float` value (in reduced Planck units) with `store_id`; base for `phi_value`, `pi_value`, `inflaton_mass` |
| `CosmologyConcepts_Potentials_AbstractPotential.py` | `CosmologyConcepts/Potentials/AbstractPotential.py` | `AbstractPotential` interface: declares `H²`, `ε`, `dV/dφ`, `d²V/dφ²`, and `D_matrix`; all inflationary models must implement this                    |

 
---

## 8. Domain concepts — InflationConcepts

Inflation-specific domain objects that implement or specialise the cosmology
base classes.

| Flat filename                                      | Original path                                      | Purpose                                                                                                                                    |
|----------------------------------------------------|----------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------|
| `InflationConcepts_delta_Nstar.py`                 | `InflationConcepts/delta_Nstar.py`                 | `delta_Nstar` — excess transition e-fold count; the shard key of the entire database                                                       |
| `InflationConcepts_efold_value.py`                 | `InflationConcepts/efold_value.py`                 | `efold_value` — a single e-fold sample coordinate N; also defines `efold_array` container                                                  |
| `InflationConcepts_N_init.py`                      | `InflationConcepts/N_init.py`                      | `N_init` — initial e-fold count; one axis of the instanton parameter grid                                                                  |
| `InflationConcepts_N_final.py`                     | `InflationConcepts/N_final.py`                     | `N_final` — final e-fold count; the other axis of the instanton parameter grid                                                             |
| `InflationConcepts_DiffusionModel.py`              | `InflationConcepts/DiffusionModel/__init__.py`     | `AbstractDiffusionModel` and `MasslessDecoupledDiffusion`; provides the 2×2 diffusion matrix D_{ij}(φ, π) used in the stochastic equations |
| `InflationConcepts_DiffusionModel_model_ids.py`    | `InflationConcepts/DiffusionModel/model_ids.py`    | Integer type-ID constants for `AbstractDiffusionModel` subclasses; `MASSLESS_DECOUPLED_DIFFUSION = 1`                                     |
| `InflationConcepts_DiffusionModel_registry.py`     | `InflationConcepts/DiffusionModel/registry.py`     | `DIFFUSION_MODEL_REGISTRY` dict populated by each concrete subclass factory on import; used to route `build()` calls by `type_id`          |
| `InflationConcepts_noiseless_equations.py`         | `InflationConcepts/noiseless_equations.py`         | Shared ODE RHS `noiseless_rhs()` and `end_of_inflation_event()` for the noiseless background; used by `InflatonTrajectory` and `CompactionFunction` |
| `InflationConcepts_QuadraticPotential.py`          | `InflationConcepts/QuadraticPotential.py`          | `QuadraticPotential` concrete implementation: V(φ) = ½m²φ²                                                                                 |
| `InflationConcepts_QuarticPotential.py`            | `InflationConcepts/QuarticPotential.py`            | `QuarticPotential` concrete implementation: V(φ) = λφ⁴                                                                                     |

 
---

## 9. Domain concepts — CosmologyModels

Persistable wrappers around cosmological parameter bundles used to convert
instanton scales to physical PBH masses and radii.

| Flat filename                  | Original path                  | Purpose                                                                                                                                    |
|--------------------------------|--------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------|
| `CosmologyModels_cosmo_params.py` | `CosmologyModels/cosmo_params.py` | `CosmologicalParams` — persistable `DatastoreObject` wrapping a parameter bundle; exposes `omega_cc`, `omega_m`, `h`, `T_CMB_Kelvin`, etc. |
| `CosmologyModels_params.py`    | `CosmologyModels/params.py`    | Bare dataclasses `Planck2013`, `Planck2015`, `Planck2018` holding best-fit cosmological constants; passed into `CosmologicalParams`        |

 
---

## 10. Metadata concepts

| Flat filename                   | Original path                   | Purpose                                                                                                     |
|---------------------------------|---------------------------------|-------------------------------------------------------------------------------------------------------------|
| `MetadataConcepts_store_tag.py` | `MetadataConcepts/store_tag.py` | `store_tag` — a string label that can be attached to any stored object to mark membership in a run or group |

 
---

## 11. Units

| Flat filename           | Original path           | Purpose                                                                                                                          |
|-------------------------|-------------------------|----------------------------------------------------------------------------------------------------------------------------------|
| `Units_base.py`         | `Units/base.py`         | `UnitsLike` abstract base class: declares abstract properties for every unit used in the code (PlanckMass, Metre, eV, c, Mpc, …) |
| `Units_Planck_units.py` | `Units/Planck_units.py` | `Planck_units` concrete implementation: sets all constants relative to reduced Planck units (Mₚ = 1, 8πG = 1)                    |

 
---

## 12. Plotting and analysis driver scripts

| Flat filename                    | Original path                    | Purpose                                                                                                                                                                                   |
|----------------------------------|----------------------------------|-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| `plot_InstantonSolutions.py`     | `plot_InstantonSolutions.py`     | Plotting driver: reads the database via `ShardedPool`; produces background-trajectory, instanton-field, noise-profile, MSR-action-sweep, compaction-profile, and DOE-scalar-summary figures using Ray-dispatched worker tasks |
| `regression_InstantonOutputs.py` | `regression_InstantonOutputs.py` | GP regression driver: reads `scalar_data.csv` from the plot script; fits 5 independent single-output GPs (C_bar_max, C_max, log S_MSR, log M_PBH, log r_PBH); writes diagnostic plots and serialised `.joblib` model bundles |

 
---

## Files not included

The following project files were deliberately omitted to keep the context
focused on design patterns. They are protected infrastructure, near-identical
to files already included, or peripheral to the patterns described above.

| Original path                                           | Reason omitted                                                              |
|---------------------------------------------------------|-----------------------------------------------------------------------------|
| `Datastore/SQL/ClientPool.py`                           | Protected infrastructure; internal to `ShardedPool`                         |
| `Datastore/SQL/SerialPoolBroker.py`                     | Protected infrastructure; monotone serial-number actor                      |
| `Datastore/SQL/ProfileAgent.py`                         | Optional query-profiling actor; not core to the patterns                    |
| `Datastore/SQL/ObjectFactories/version.py`              | Trivial single-row factory; `tolerance.py` is a better illustrative example |
| `Datastore/SQL/ObjectFactories/store_tag.py`            | Same; `tolerance.py` illustrates the pattern                                |
| `Datastore/SQL/ObjectFactories/N_init.py`               | Delegated to the generic `DimensionlessQuantity` factory                    |
| `Datastore/SQL/ObjectFactories/N_final.py`              | Same as `N_init`                                                            |
| `Datastore/SQL/ObjectFactories/integration_metadata.py` | Protected infrastructure; ODE-solver metadata only                          |
| `Datastore/SQL/ObjectFactories/redshift.py`             | Protected infrastructure; legacy cosmology concept, unused in this project  |
| `Datastore/SQL/ObjectFactories/QuarticPotential.py`     | Near-identical to `QuadraticPotential` factory                              |
| `CosmologyConcepts/FieldValues.py`                      | Thin wrapper; `DimensionfulQuantity` already illustrates the pattern        |
| `CosmologyConcepts/redshift.py`                         | Legacy cosmology concept, unused in this project                            |
| `CosmologyConcepts/temperature.py`                      | Legacy cosmology concept, unused in this project                            |
| `CosmologyConcepts/Potentials/registry.py`              | Internal model-ID dispatch table; not core                                  |
| `CosmologyConcepts/Potentials/model_ids.py`             | Same                                                                        |
| `InflationConcepts/inflaton_mass.py`                    | Thin `DimensionfulQuantity` subclass; no new pattern                        |
| `InflationConcepts/quartic_coupling.py`                 | Thin `DimensionlessQuantity` subclass; no new pattern                       |
| `MetadataConcepts/tolerance.py`                         | Already represented by the factory; covered in `architecture-summary.md`    |
| `Quadrature/`                                           | Protected infrastructure; not needed to understand the main pipeline        |
| `RayTools/` (other files)                               | Only `RayWorkPool.py` is directly relevant                                  |
| `config/defaults.py`                                    | Small constants file; values visible in `argument_parser.py`                |
| `ComputeTargets/exceptions.py`                          | Small; exception class definitions only                                     |
| `constants.py`                                          | Only defines `RadiationConstant` and `StefanBoltzmannConstant`; peripheral  |
| `utilities.py`                                          | General-purpose utilities (timing, grouper, etc.); not needed for patterns  |
